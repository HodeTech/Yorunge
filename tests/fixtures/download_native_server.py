"""Separate-process TLS object server for the download measurement; keeps bounded metadata only.

One process stands in for both parties the product talks to: the Platform's JSON call (it needs the
key) and the object store behind the signed address (it must see no credential at all). The signed
object is generated block by block (never held, never larger than 64 KiB in memory); it answers
``Range: bytes=N-`` with a ``206`` and an exact ``Content-Range`` when ``If-Range`` carries its
strong ``ETag``, answers a stale ``If-Range`` with the whole object and an out-of-range start with
``416``.

For a fixture with a ``cut_at`` the FIRST signed GET sends its status line and headers with the full
``Content-Length``, then closes the connection after ``cut_at`` body bytes; every later GET is
served normally. Everything it counts goes into one closed JSON object on stdout at exit.
"""

from __future__ import annotations

import argparse
import os
import re
import signal
import ssl
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from socketserver import TCPServer
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.fixtures.download_native_data import (  # noqa: E402
    FILENAME,
    JSON_TARGET,
    KEY,
    ORIGIN,
    ROTATION,
    SIGNED_TARGET,
    canonical,
    fixture,
)
from tests.fixtures.stream_budget import publish_ready  # noqa: E402

SERVER_BLOCK = 65_536  # the largest buffer this process ever hands to the socket
REQUEST_CAP = 64  # a measurement makes at most four requests: more is a runaway client
CYCLE = bytes(range(256))
CREDENTIAL_HEADERS = frozenset({"x-api-key", "authorization", "cookie", "proxy-authorization"})
# The product's closed wire request to a signed address: the HTTP layer's Host and the three
# headers of its own list (docs/reference/download-engine.md, "Motor sınırı").
SIGNED_HEADERS = frozenset({"host", "accept-encoding", "range", "if-range"})
RANGE = re.compile(r"bytes=(0|[1-9][0-9]{0,18})-", re.ASCII)


def block_of(index: int) -> bytes:
    """Block ``index`` of the object: the 256-byte cycle rotated by ``37 * index``, repeated."""
    shift = (ROTATION * index) % 256
    return (CYCLE[shift:] + CYCLE[:shift]) * (SERVER_BLOCK // 256)


def body_blocks(start: int, stop: int) -> Iterator[memoryview]:
    """Bytes ``start`` to ``stop`` of the object, one view of at most one block at a time."""
    position = start
    while position < stop:
        index, offset = divmod(position, SERVER_BLOCK)
        end = min(SERVER_BLOCK, offset + stop - position)
        yield memoryview(block_of(index))[offset:end]
        position += end - offset


class Provider:
    """The routes, the scripted cut and the counters; it never retains a body."""

    def __init__(self, label: str) -> None:
        self.fixture = fixture(label)
        self.lock = threading.Lock()
        self.requests = {"json": 0, "signed": 0, "unexpected": 0}
        self.signed: list[dict[str, Any]] = []
        self.connections = 0
        self.active = self.peak = 0
        self.bytes_sent = 0
        self.max_block_bytes = 0
        self.credential_violations = self.header_violations = 0
        self.json_key_failures = self.errors = 0
        self.json_names: set[str] = set()
        self.signed_names: set[str] = set()

    # --- one request ------------------------------------------------------------------------------

    def respond(self, handler: Any) -> None:
        with self.lock:
            if sum(self.requests.values()) >= REQUEST_CAP:
                self.errors += 1
                handler.close_connection = True
                return
            self.active += 1
            self.peak = max(self.peak, self.active)
        try:
            self.route(handler)
        except (ValueError, KeyError, OSError):
            with self.lock:
                self.errors += 1
            handler.close_connection = True
        finally:
            with self.lock:
                self.active -= 1

    def route(self, handler: Any) -> None:
        headers = handler.headers
        lengths = headers.get_all("Content-Length") or ["0"]
        if handler.command != "GET":
            self.unexpected(handler, 405)
        elif headers.get_all("Transfer-Encoding") or lengths != ["0"]:
            self.unexpected(handler, 400)
        elif handler.path == JSON_TARGET:
            self.json_call(handler)
        elif handler.path == SIGNED_TARGET:
            self.signed_get(handler)
        else:
            self.unexpected(handler, 404)

    def unexpected(self, handler: Any, status: int) -> None:
        with self.lock:
            self.requests["unexpected"] += 1
        self.reply(handler, status, b'{"detail":"refused"}')

    def reply(
        self, handler: Any, status: int, body: bytes, extra: tuple[tuple[str, str], ...] = ()
    ) -> None:
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(body)))
        for name, value in extra:
            handler.send_header(name, value)
        handler.end_headers()
        if body and handler.command != "HEAD":
            handler.wfile.write(body)
        handler.wfile.flush()

    # --- the Platform's JSON call -----------------------------------------------------------------

    def json_call(self, handler: Any) -> None:
        with self.lock:
            self.requests["json"] += 1
            self.json_names.update(name.lower() for name in handler.headers)
        if handler.headers.get_all("X-API-Key") != [KEY]:
            with self.lock:
                self.json_key_failures += 1
            self.reply(handler, 401, b'{"detail":"unauthorized"}')
            return
        answer = {"download_url": ORIGIN + SIGNED_TARGET, "filename": FILENAME}
        self.reply(handler, 200, canonical(answer))

    # --- the object store behind the signed address -----------------------------------------------

    def signed_get(self, handler: Any) -> None:
        names = {name.lower() for name in handler.headers}
        ranges = handler.headers.get_all("Range") or []
        conditions = handler.headers.get_all("If-Range") or []
        record: dict[str, Any] = {
            "range": ranges[0] if ranges else None,
            "if_range": conditions[0] if conditions else None,
            "status": 0,
            "content_length": None,
            "content_range": None,
            "bytes_sent": 0,
            "completed": False,
            "cut": False,
        }
        with self.lock:
            self.requests["signed"] += 1
            ordinal = self.requests["signed"]
            self.signed_names.update(names)
            self.signed.append(record)
        # A signed address is the credential: any other one is a violation, and it is refused.
        if names & CREDENTIAL_HEADERS:
            self.violate(handler, record, "credential_violations", 403)
            return
        if names - SIGNED_HEADERS or len(ranges) > 1 or len(conditions) > 1:
            self.violate(handler, record, "header_violations", 400)
            return
        item = self.fixture
        start, status = 0, 200
        if ranges:
            match = RANGE.fullmatch(ranges[0])
            if match is None:
                self.violate(handler, record, "header_violations", 400)
                return
            first = int(match.group(1))
            if first >= item.size:
                record["status"] = 416
                record["content_range"] = f"bytes */{item.size}"
                self.reply(handler, 416, b"", (("Content-Range", record["content_range"]),))
                return
            if not conditions or conditions[0] == item.etag:
                start, status = first, 206
        length = item.size - start
        extra = [("ETag", item.etag), ("Accept-Ranges", "bytes")]
        if status == 206:
            record["content_range"] = f"bytes {start}-{item.size - 1}/{item.size}"
            extra.append(("Content-Range", record["content_range"]))
        limit = length
        if item.cut_at is not None and ordinal == 1 and item.cut_at < length:
            limit = item.cut_at
            record["cut"] = True
        record["status"], record["content_length"] = status, length
        handler.send_response(status)
        handler.send_header("Content-Type", "application/octet-stream")
        handler.send_header("Content-Length", str(length))
        for name, value in extra:
            handler.send_header(name, value)
        handler.end_headers()
        self.stream(handler, record, start, limit, length)

    def violate(self, handler: Any, record: dict[str, Any], counter: str, status: int) -> None:
        with self.lock:
            setattr(self, counter, getattr(self, counter) + 1)
        record["status"] = status
        self.reply(handler, status, b'{"detail":"refused"}')

    def stream(
        self, handler: Any, record: dict[str, Any], start: int, limit: int, length: int
    ) -> None:
        sent, largest = 0, 0
        try:
            for block in body_blocks(start, start + limit):
                handler.wfile.write(block)
                sent += len(block)
                largest = max(largest, len(block))
            handler.wfile.flush()
        except (BrokenPipeError, ConnectionError, ssl.SSLError, TimeoutError):
            handler.close_connection = True
            with self.lock:
                self.errors += 1
        finally:
            with self.lock:
                record["bytes_sent"] = sent
                record["completed"] = sent == length
                self.bytes_sent += sent
                self.max_block_bytes = max(self.max_block_bytes, largest)
        if record["cut"]:
            # A body shorter than its Content-Length ends only with the connection.
            handler.close_connection = True

    # --- the closed account -----------------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        with self.lock:
            item = self.fixture
            return {
                "pid": os.getpid(),
                "label": item.label,
                "size": item.size,
                "cut_at": item.cut_at,
                "etag": item.etag,
                "requests": dict(self.requests),
                "signed": [dict(record) for record in self.signed],
                "bytes_sent": self.bytes_sent,
                "connection_count": self.connections,
                "active_requests": self.active,
                "peak_active_requests": self.peak,
                "credential_violations": self.credential_violations,
                "header_violations": self.header_violations,
                "json_key_failures": self.json_key_failures,
                "errors": self.errors,
                "max_block_bytes": self.max_block_bytes,
                "json_header_names": sorted(self.json_names),
                "signed_header_names": sorted(self.signed_names),
            }


def serve(args: argparse.Namespace) -> int:
    provider = Provider(args.label)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    # A client that closes a kept-alive connection without a TLS goodbye is no server error.
    context.options |= getattr(ssl, "OP_IGNORE_UNEXPECTED_EOF", 0)
    context.load_cert_chain(str(args.ca), str(args.key))

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        timeout = 120
        disable_nagle_algorithm = True

        def log_message(self, format: str, *values: object) -> None:
            pass

        def respond(self) -> None:
            provider.respond(self)

        do_GET = do_HEAD = do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = respond

    class Server(ThreadingHTTPServer):
        daemon_threads = True

        def server_bind(self) -> None:
            TCPServer.server_bind(self)
            self.server_name, self.server_port = "localhost", int(self.server_address[1])

        def get_request(self) -> Any:
            connection, address = super().get_request()
            try:
                wrapped = context.wrap_socket(
                    connection, server_side=True, do_handshake_on_connect=False
                )
            except BaseException:
                connection.close()
                raise
            return wrapped, address

        def finish_request(self, request: Any, client_address: Any) -> None:
            # The handshake belongs to the request's own thread, never to the listening one.
            try:
                request.settimeout(5)
                request.do_handshake()
                request.settimeout(None)
            except (OSError, ValueError):
                return
            with provider.lock:
                provider.connections += 1
            super().finish_request(request, client_address)

        def handle_error(self, request: Any, client_address: Any) -> None:
            if isinstance(sys.exc_info()[1], (ConnectionError, ssl.SSLError, TimeoutError)):
                return  # a peer that went away is its own business, not an error of this server
            with provider.lock:
                provider.errors += 1

    server = Server(("127.0.0.1", 0), Handler)

    def stop(signum: int, frame: object) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        publish_ready(args.ready, {"port": server.server_address[1], "pid": os.getpid()})
        server.serve_forever(poll_interval=0.05)
    finally:
        server.server_close()
    sys.stdout.write(canonical(provider.summary()).decode("utf-8") + "\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ca", required=True, type=Path)
    parser.add_argument("--key", required=True, type=Path)
    parser.add_argument("--ready", required=True, type=Path)
    parser.add_argument(
        "--label", required=True, choices=("warm", "warm-resume", "16", "256", "1024", "resume")
    )
    return serve(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
