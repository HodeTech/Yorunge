"""Test-only canonical-host TLS mapping and optional bounded native instrumentation."""

from __future__ import annotations

import socket
import ssl
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpcore
import httpx

from tests.fixtures.http_server import loopback_sockets
from yorunge.adapters.guarded_http import GuardedHttpTransport
from yorunge.adapters.guarded_network import GuardedBackend
from yorunge.adapters.storage_source import DescriptorByteSource
from yorunge.adapters.upload_http import UploadHttpxTransport, UploadSession
from yorunge.application.upload_progress import observe_upload


@dataclass
class Metrics:
    sessions: list = field(default_factory=list, repr=False)
    connections: int = 0
    open_connections: int = 0
    peak_connections: int = 0
    active_requests: int = 0
    peak_requests: int = 0
    active_puts: int = 0
    peak_puts: int = 0
    source_bytes: int = 0
    source_chunks: int = 0
    max_source_chunk_bytes: int = 0
    confirmed_files: int = 0
    confirmed_bytes: int = 0
    peak_sources: int = 0
    request_seconds: list[float] = field(default_factory=list, repr=False)
    put_seconds: list[float] = field(default_factory=list, repr=False)
    _sources: set[int] = field(default_factory=set, repr=False)

    def progress(self, value):
        delta = value.source_bytes - self.source_bytes
        if delta < 0:
            raise ValueError("native observation mixed two upload operations")
        if delta:
            self.source_chunks += 1
            self.max_source_chunk_bytes = max(self.max_source_chunk_bytes, delta)
        self.source_bytes = value.source_bytes
        self.confirmed_files, self.confirmed_bytes = value.confirmed_files, value.confirmed_bytes

    def request_started(self, put):
        self.active_requests += 1
        self.active_puts += put
        self.peak_requests = max(self.peak_requests, self.active_requests)
        self.peak_puts = max(self.peak_puts, self.active_puts)

    def request_closed(self, put, started=None):
        self.active_requests -= 1
        self.active_puts -= put
        if started is not None:
            elapsed = time.perf_counter() - started
            self.request_seconds.append(elapsed)
            if put:
                self.put_seconds.append(elapsed)

    def summary(self):
        # Budgets expose numeric dataclasses; never inspect requests or descriptors.
        return {
            "sessions": [asdict(value.snapshot()) for value in self.sessions],
            **{
                name: getattr(self, name)
                for name in self.__dataclass_fields__
                if name not in {"sessions", "_sources"}
            },
            "open_sources": len(self._sources),
        }


class Connection:
    def __init__(self, metrics):
        self.metrics, self.closed = metrics, False
        metrics.connections += 1
        metrics.open_connections += 1
        metrics.peak_connections = max(metrics.peak_connections, metrics.open_connections)

    def close(self):
        if not self.closed:
            self.closed = True
            self.metrics.open_connections -= 1


class CountingStream(httpcore.AsyncNetworkStream):
    def __init__(self, inner, connection):
        self.inner, self.connection = inner, connection

    async def read(self, max_bytes, timeout=None):
        return await self.inner.read(max_bytes, timeout)

    async def write(self, buffer, timeout=None):
        await self.inner.write(buffer, timeout)

    async def aclose(self):
        await self.inner.aclose()
        self.connection.close()

    async def start_tls(self, ssl_context, server_hostname=None, timeout=None):
        updated = await self.inner.start_tls(ssl_context, server_hostname, timeout)
        return CountingStream(updated, self.connection)

    def get_extra_info(self, info):
        return self.inner.get_extra_info(info)


class CountedResponse(httpx.AsyncByteStream):
    def __init__(self, inner, metrics, put, started=None):
        self.inner, self.metrics, self.put, self.closed = inner, metrics, put, False
        self.started = started

    async def __aiter__(self):
        async for chunk in self.inner:
            yield chunk

    async def aclose(self):
        await self.inner.aclose()
        if not self.closed:
            self.closed = True
            self.metrics.request_closed(self.put, self.started)


class CountingTransport(httpx.AsyncBaseTransport):
    def __init__(self, inner, metrics):
        self.inner, self.metrics = inner, metrics

    async def handle_async_request(self, request):
        put = request.method == "PUT"
        started = time.perf_counter()
        self.metrics.request_started(put)
        try:
            response = await self.inner.handle_async_request(request)
        except BaseException:
            self.metrics.request_closed(put, started)
            raise
        response.stream = CountedResponse(response.stream, self.metrics, put, started)
        return response

    async def aclose(self):
        await self.inner.aclose()


@contextmanager
def sources(metrics):
    opened, closed = DescriptorByteSource._open, DescriptorByteSource.aclose

    def observed_open(source):
        try:
            opened(source)
        finally:
            if source._file_fd is not None:
                metrics._sources.add(id(source))
                metrics.peak_sources = max(metrics.peak_sources, len(metrics._sources))

    async def observed_close(source):
        try:
            await closed(source)
        finally:
            if source._file_fd is None:
                metrics._sources.discard(id(source))

    DescriptorByteSource._open, DescriptorByteSource.aclose = observed_open, observed_close
    try:
        with observe_upload(metrics.progress):
            yield
    finally:
        DescriptorByteSource._open, DescriptorByteSource.aclose = opened, closed


@contextmanager
def loopback_upload(ca: Path, port: int, metrics: Metrics | None = None):
    context = ssl.create_default_context(cafile=str(ca))

    class FixtureNetwork(GuardedBackend):
        def __init__(self):
            async def resolver(host, requested_port, timeout):
                assert host == "api.ssyz.org.tr" and requested_port == 443
                return ("127.0.0.1",)

            super().__init__(resolver=resolver, allowed=lambda address: address == "127.0.0.1")

        async def _connect(self, pinned, requested_port, timeout, options, original_host):
            assert (
                pinned == "127.0.0.1"
                and requested_port == 443
                and original_host == "api.ssyz.org.tr"
            )
            stream = await httpcore.AnyIOBackend().connect_tcp(
                pinned, port, timeout=timeout, socket_options=options
            )
            return stream if metrics is None else CountingStream(stream, Connection(metrics))

    original = UploadSession.__init__

    def initialize(session, credential, budget, **kwargs):
        assert not kwargs, "unexpected composition override"
        if metrics is not None:
            metrics.sessions.append(budget)

        def transport():
            inner = GuardedHttpTransport(backend=FixtureNetwork(), verify=context)
            return inner if metrics is None else CountingTransport(inner, metrics)

        original(
            session,
            credential,
            budget,
            transport_factory=lambda: UploadHttpxTransport(
                credential, budget, transport=transport()
            ),
        )

    UploadSession.__init__ = initialize
    try:
        with loopback_sockets(socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo):
            if metrics is None:
                yield
            else:
                with sources(metrics):
                    yield
    finally:
        UploadSession.__init__ = original
