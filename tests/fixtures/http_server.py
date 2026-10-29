"""Real loopback TLS fixture; it is never a selectable product backend."""

from __future__ import annotations

import socket
import ssl
import struct
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx


@dataclass(frozen=True)
class RequestRecord:
    method: str
    path: str
    headers: tuple[tuple[str, str], ...]
    body: bytes
    connection: tuple[str, int]

    def header(self, name: str) -> str | None:
        return next((value for key, value in self.headers if key.lower() == name.lower()), None)


@dataclass(frozen=True)
class Reply:
    status: int = 200
    body: bytes = b'{"value":"accepted"}'
    headers: tuple[tuple[str, str], ...] = ()
    header_delay: float = 0.0
    header_drip: float = 0.0
    chunk_size: int = 32_768
    chunk_delay: float = 0.0
    truncate_at: int | None = None
    after_first_chunk: Callable[[], None] | None = None
    reset_after_body: bool = False


Route = Reply | Callable[[RequestRecord, int], Reply]


def certificate(directory: Path) -> tuple[Path, Path]:
    """Create an explicitly trusted, short-lived test CA/server certificate."""
    directory.mkdir(parents=True, exist_ok=True)
    config = directory / "openssl.cnf"
    config.write_text(
        "[req]\nprompt=no\ndistinguished_name=subject\nx509_extensions=server\n"
        "[subject]\nCN=localhost\n[server]\nsubjectAltName=DNS:localhost\n"
        "basicConstraints=critical,CA:TRUE\n"
        "keyUsage=critical,digitalSignature,keyEncipherment,keyCertSign\n"
        "extendedKeyUsage=serverAuth\n",
        encoding="ascii",
    )
    cert, key = directory / "certificate.pem", directory / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-config",
            str(config),
            "-keyout",
            str(key),
            "-out",
            str(cert),
        ],
        check=True,
        capture_output=True,
        timeout=15,
    )
    return cert, key


class LoopbackTransport(httpx.AsyncBaseTransport):
    """Connect a canonical HTTPS request to the fixture's ephemeral TLS port.

    This mapping exists only in tests. The real connection still verifies the
    localhost certificate and the original request's Host/header/path are used.
    """

    def __init__(self, port: int, context: ssl.SSLContext, hostname: str = "localhost"):
        self.port, self.hostname = port, hostname
        self.inner = httpx.AsyncHTTPTransport(verify=context, retries=0, trust_env=False)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        mapped = httpx.Request(
            request.method,
            request.url.copy_with(
                host=self.hostname,
                port=self.port if request.url.port in (None, 443) else request.url.port,
            ),
            headers=request.headers,
            stream=request.stream,
            extensions=request.extensions,
        )
        return await self.inner.handle_async_request(mapped)

    async def aclose(self) -> None:
        await self.inner.aclose()


class TlsServer:
    def __init__(self, certificates: tuple[Path, Path], routes: dict[str, Route]):
        self.certificates, self.routes = certificates, routes
        self.requests: list[RequestRecord] = []
        self.disconnected = threading.Event()
        self._lock = threading.Lock()
        self._counts: dict[str, int] = {}
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        assert self._server is not None
        return int(self._server.server_address[1])

    def client_context(self) -> ssl.SSLContext:
        return ssl.create_default_context(cafile=str(self.certificates[0]))

    def transport(
        self, *, context: ssl.SSLContext | None = None, hostname: str = "localhost"
    ) -> LoopbackTransport:
        return LoopbackTransport(self.port, context or self.client_context(), hostname)

    def _reply(self, record: RequestRecord) -> Reply:
        with self._lock:
            self.requests.append(record)
            count = self._counts.get(record.path, 0) + 1
            self._counts[record.path] = count
        route = self.routes.get(record.path, Reply(status=404, body=b""))
        return route(record, count) if callable(route) else route

    def __enter__(self) -> TlsServer:
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, format: str, *args: object) -> None:
                pass

            def do_GET(self) -> None:
                self.respond()

            def do_HEAD(self) -> None:
                self.respond()

            def do_POST(self) -> None:
                self.respond()

            def do_PUT(self) -> None:
                self.respond()

            def respond(self) -> None:
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                record = RequestRecord(
                    self.command, self.path, tuple(self.headers.items()), body, self.client_address
                )
                reply = owner._reply(record)
                length = (
                    ()
                    if any(name.lower() == "transfer-encoding" for name, _ in reply.headers)
                    else (("Content-Length", str(len(reply.body))),)
                )
                fields = (
                    *length,
                    ("Content-Type", "application/json"),
                    *reply.headers,
                )
                headers = (
                    f"HTTP/1.1 {reply.status} {HTTPStatus(reply.status).phrase}\r\n"
                    + "".join(f"{name}: {value}\r\n" for name, value in fields)
                    + "\r\n"
                ).encode("ascii")
                try:
                    time.sleep(reply.header_delay)
                    if reply.header_drip:
                        for value in headers:
                            self.wfile.write(bytes([value]))
                            self.wfile.flush()
                            time.sleep(reply.header_drip)
                    else:
                        self.wfile.write(headers)
                        self.wfile.flush()
                    if self.command != "HEAD":
                        sent = reply.body[: reply.truncate_at]
                        for offset in range(0, len(sent), reply.chunk_size):
                            self.wfile.write(sent[offset : offset + reply.chunk_size])
                            self.wfile.flush()
                            if offset == 0 and reply.after_first_chunk is not None:
                                reply.after_first_chunk()
                            if reply.chunk_delay:
                                time.sleep(reply.chunk_delay)
                    if reply.truncate_at is not None:
                        self.close_connection = True
                    if reply.reset_after_body:
                        self.connection.setsockopt(
                            socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0)
                        )
                        # Abort before TCPServer's later orderly SHUT_WR can
                        # turn this into a plain FIN/truncated-message fixture.
                        socket.close(self.connection.detach())
                        self.close_connection = True
                except (BrokenPipeError, ConnectionError, ssl.SSLError):
                    owner.disconnected.set()
                    self.close_connection = True

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(*(str(path) for path in self.certificates))
        self._server.socket = context.wrap_socket(self._server.socket, server_side=True)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        assert self._server is not None and self._thread is not None
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)
        assert not self._thread.is_alive(), "TLS fixture did not stop"


@contextmanager
def loopback_sockets(
    connect: Callable[..., object],
    connect_ex: Callable[..., object],
    getaddrinfo: Callable[..., object],
) -> Iterator[None]:
    """Unused by product: allow actual loopback sockets inside this fixture only."""
    original = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo

    def permitted(self: socket.socket, address: tuple[str, int]) -> object:
        assert address[0] in ("127.0.0.1", "::1"), "non-loopback connection forbidden"
        return connect(self, address)

    def permitted_ex(self: socket.socket, address: tuple[str, int]) -> object:
        assert address[0] in ("127.0.0.1", "::1"), "non-loopback connection forbidden"
        return connect_ex(self, address)

    def resolve(host: str, *args: object, **kwargs: object) -> object:
        assert host in ("localhost", b"localhost", "127.0.0.1", "::1")
        return getaddrinfo(host, *args, **kwargs)

    socket.socket.connect = permitted  # type: ignore[method-assign,assignment]
    socket.socket.connect_ex = permitted_ex  # type: ignore[method-assign,assignment]
    socket.getaddrinfo = resolve  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = original
