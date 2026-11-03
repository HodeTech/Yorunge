"""Separate-process TLS upload sink; retains bounded metadata, never file bodies."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import ssl
import sys
import threading
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from socketserver import TCPServer
from urllib.parse import parse_qsl, urlsplit

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.fixtures.http_server import RequestRecord  # noqa: E402
from tests.fixtures.stream_budget import publish_ready  # noqa: E402
from tests.fixtures.upload_native_data import KEY, NAME, OWNER, PROJECT, fixture  # noqa: E402
from tests.fixtures.upload_provider import DATASET, UploadProvider, reply  # noqa: E402

SINK_CHUNK = 65_536


class StreamingProvider(UploadProvider):
    def __init__(self, expected):
        super().__init__(OWNER, PROJECT, name=NAME)
        self.expected = {file["path"]: file for file in expected["files"]}
        self.received = {}
        self.max_read_bytes = 0

    def presign(self, request, count):
        rows = json.loads(request.body)["files"]
        assert len(rows) == 1
        row = rows[0]
        expected = self.expected[row["filename"]]
        assert row["file_size"] == expected["size"]
        assert row["sha256_hash"] == expected["sha256"]
        return super().presign(request, count)

    def receive(self, handler, size):
        query = parse_qsl(urlsplit(handler.path).query, strict_parsing=True)
        assert len(query) == 1 and query[0][0] == "key"
        key = query[0][1]
        row = next(value for value in self.presigns.values() if value["object_key"] == key)
        expected = self.expected[row["filename"]]
        assert size == expected["size"] and key not in self.objects
        digest, received = hashlib.sha256(), 0
        while received < size:
            chunk = handler.rfile.read(min(SINK_CHUNK, size - received))
            if not chunk:
                raise ValueError("incomplete upload fixture body")
            digest.update(chunk)
            received += len(chunk)
            with self.lock:
                self.max_read_bytes = max(self.max_read_bytes, len(chunk))
        record = {"path": row["filename"], "size": received, "sha256": digest.hexdigest()}
        assert record == expected
        with self.lock:
            assert key not in self.objects
            self.objects[key] = True  # Membership only; no retained payload.
            self.received[record["path"]] = record
            self.put_calls += 1
            self.events.append("put")
        return reply({"success": True})

    def summary(self):
        return {
            "received": [self.received[name] for name in sorted(self.received)],
            "items": [self.confirmed[name] for name in sorted(self.confirmed)],
            "max_read_bytes": self.max_read_bytes,
            "create_calls": self.create_calls,
            "link_calls": self.link_calls,
            "presign_calls": self.presign_calls,
            "put_calls": self.put_calls,
            "confirm_calls": self.confirm_calls,
        }


class Sink:
    def __init__(self, expected):
        self.provider = StreamingProvider(expected)
        self.routes = self.provider.routes()
        self.lock = threading.Lock()
        self.requests = Counter()
        self.statuses = Counter()
        self.connections = set()
        self.errors = 0
        self.active = self.peak = 0
        self.control_bytes = 0

    def route(self, handler, size):
        if handler.command == "PUT":
            assert urlsplit(handler.path).path == f"/api/v1/datasets/{DATASET}/upload/put"
            return self.provider.receive(handler, size)
        assert 0 <= size <= 1_048_576
        body = handler.rfile.read(size)
        assert len(body) == size
        with self.lock:
            self.control_bytes += len(body)
        record = RequestRecord(
            handler.command,
            handler.path,
            tuple(handler.headers.items()),
            body,
            handler.client_address,
        )
        route = self.routes.get(handler.path)
        assert callable(route)
        return route(record, 1)

    def begin(self, handler):
        with self.lock:
            if sum(self.requests.values()) >= 2048:
                raise ValueError("native fixture request cap")
            self.requests[handler.command] += 1
            self.connections.add(handler.client_address)
            self.active += 1
            self.peak = max(self.peak, self.active)

    def respond(self, handler):
        self.begin(handler)
        try:
            assert handler.command in {"GET", "POST", "PUT"}
            assert handler.headers.get_all("X-API-Key") == [KEY]
            assert not handler.headers.get_all("Transfer-Encoding")
            lengths = handler.headers.get_all("Content-Length") or ["0"]
            assert len(lengths) == 1 and lengths[0].isascii() and lengths[0].isdigit()
            size = int(lengths[0])
            assert 0 <= size <= 500_000_000
            response = self.route(handler, size)
            with self.lock:
                self.statuses[str(response.status)] += 1
            handler.send_response(response.status)
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Content-Length", str(len(response.body)))
            handler.end_headers()
            handler.wfile.write(response.body)
            handler.wfile.flush()
        except (AssertionError, ValueError, KeyError, StopIteration, OSError):
            with self.lock:
                self.errors += 1
            handler.close_connection = True
        finally:
            with self.lock:
                self.active -= 1

    def summary(self):
        return {
            **self.provider.summary(),
            "pid": os.getpid(),
            "requests": dict(self.requests),
            "statuses": dict(self.statuses),
            "connection_count": len(self.connections),
            "active_requests": self.active,
            "peak_active_requests": self.peak,
            "control_bytes": self.control_bytes,
            "errors": self.errors,
        }


def serve(args):
    sink = Sink(fixture(args.label))

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format, *values):
            pass

        def do_GET(self):
            sink.respond(self)

        def do_POST(self):
            sink.respond(self)

        def do_PUT(self):
            sink.respond(self)

    class Server(ThreadingHTTPServer):
        def server_bind(self):
            TCPServer.server_bind(self)
            self.server_name, self.server_port = "localhost", int(self.server_address[1])

        def handle_error(self, request, client_address):
            with sink.lock:
                sink.errors += 1

    server = Server(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(str(args.ca), str(args.key))
    server.socket = context.wrap_socket(server.socket, server_side=True)

    def stop(signum, frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        publish_ready(args.ready, {"port": server.server_address[1], "pid": os.getpid()})
        server.serve_forever(poll_interval=0.05)
    finally:
        server.server_close()
    print(json.dumps(sink.summary(), allow_nan=False))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ca", required=True, type=Path)
    parser.add_argument("--key", required=True, type=Path)
    parser.add_argument("--ready", required=True, type=Path)
    parser.add_argument("--label", required=True, choices=("warm", "16", "256", "1024", "capacity"))
    return serve(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
