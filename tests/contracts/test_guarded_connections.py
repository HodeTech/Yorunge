"""One pinned connection: address fallback, lost peer metadata and idle expiry."""

import asyncio
import socket
import ssl
from functools import partial

import httpcore
import httpx
import pytest

from tests.contracts.test_guarded_network import Connector, Stream
from yorunge.adapters.guarded_http import GuardedHttpTransport
from yorunge.adapters.guarded_network import GuardedBackend, GuardedStream, public_address, resolve
from yorunge.adapters.http_transport import HttpxTransport
from yorunge.domain.errors import YorungeError


def test_unreachable_first_address_uses_second_with_one_resolution_and_deadline():
    stream, resolutions, timeouts = Stream(("1.1.1.1", 443)), [], []

    class Addresses(Connector):
        async def connect_tcp(self, host, port, **kwargs):
            self.calls.append((host, port))
            timeouts.append(kwargs["timeout"])
            if host == "8.8.8.8":
                raise httpcore.ConnectError("no route")
            return self.stream

    async def resolver(host, port, timeout):
        resolutions.append((host, port))
        return ("8.8.8.8", "1.1.1.1")

    connector = Addresses(stream)

    async def run():
        raw = await GuardedBackend(resolver=resolver, backend=connector).connect_tcp(
            "storage.example", 443, timeout=0.5
        )
        tls = await raw.start_tls(ssl.create_default_context(), "storage.example")
        await tls.write(b"one HTTP request")
        await tls.aclose()

    asyncio.run(run())
    assert resolutions == [("storage.example", 443)]
    assert connector.calls == [("8.8.8.8", 443), ("1.1.1.1", 443)]
    assert 0 < timeouts[1] < timeouts[0] <= 0.5
    assert stream.sni == "storage.example"
    assert stream.writes == [b"one HTTP request"]
    assert stream.closed


@pytest.mark.parametrize("failure", [httpcore.ConnectError, httpcore.ConnectTimeout])
def test_all_connect_failures_preserve_transport_class_without_http(failure):
    class Unavailable(Connector):
        async def connect_tcp(self, host, port, **kwargs):
            self.calls.append((host, port))
            raise failure("unavailable")

    connector = Unavailable(Stream())

    async def resolver(*args):
        return ("8.8.8.8", "1.1.1.1")

    async def run():
        await GuardedBackend(resolver=resolver, backend=connector).connect_tcp("example", 443)

    coroutine = run()
    with pytest.raises(failure):
        asyncio.run(coroutine)
    assert connector.calls == [("8.8.8.8", 443), ("1.1.1.1", 443)]
    assert connector.stream.writes == []


def test_connect_deadline_never_opens_next_address_after_timeout():
    class Blocked(Connector):
        async def connect_tcp(self, host, port, **kwargs):
            self.calls.append((host, port))
            await asyncio.Event().wait()

    connector = Blocked(Stream())

    async def resolver(*args):
        return ("8.8.8.8", "1.1.1.1")

    async def run():
        await GuardedBackend(resolver=resolver, backend=connector).connect_tcp(
            "example", 443, timeout=0.01
        )

    coroutine = run()
    with pytest.raises(httpcore.ConnectTimeout):
        asyncio.run(coroutine)
    assert connector.calls == [("8.8.8.8", 443)]


def test_cancel_during_first_connect_never_opens_another_address():
    async def run():
        entered = asyncio.Event()

        class Blocked(Connector):
            async def connect_tcp(self, host, port, **kwargs):
                self.calls.append((host, port))
                entered.set()
                await asyncio.Event().wait()

        connector = Blocked(Stream())

        async def resolver(*args):
            return ("8.8.8.8", "1.1.1.1")

        task = asyncio.create_task(
            GuardedBackend(resolver=resolver, backend=connector).connect_tcp("example", 443)
        )
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert connector.calls == [("8.8.8.8", 443)]

    asyncio.run(run())


@pytest.mark.parametrize("missing", [None, OSError("closed socket")])
@pytest.mark.parametrize("operation", ["read", "write"])
def test_validated_tls_stream_keeps_buffered_reply_or_original_network_error(missing, operation):
    class Buffered(Stream):
        lost = False
        reads = 0

        def get_extra_info(self, name):
            if self.lost:
                if isinstance(missing, OSError):
                    raise missing
                return missing
            return super().get_extra_info(name)

        async def read(self, max_bytes, timeout=None):
            self.reads += 1
            return b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"

        async def write(self, buffer, timeout=None):
            raise httpcore.WriteError("connection reset")

    stream = Buffered()

    async def run():
        raw = GuardedStream(stream, "example", frozenset({"8.8.8.8"}), public_address)
        assert raw.peer_valid()
        tls = await raw.start_tls(ssl.create_default_context(), "example")
        stream.lost = True
        if operation == "read":
            assert await tls.read(65536) == b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"
        else:
            with pytest.raises(httpcore.WriteError, match="connection reset"):
                await tls.write(b"request")
        await tls.aclose()

    asyncio.run(run())
    assert stream.reads == (1 if operation == "read" else 0)
    assert stream.closed


def test_lost_peer_metadata_never_bypasses_initial_post_tls_verification():
    class LostAtHandshake(Stream):
        async def start_tls(self, *args, **kwargs):
            self.peer = None
            return self

    stream = LostAtHandshake()
    raw = GuardedStream(stream, "example", frozenset({"8.8.8.8"}), public_address)
    assert raw.peer_valid()
    context = ssl.create_default_context()
    coroutine = raw.start_tls(context, "example")
    with pytest.raises(YorungeError) as failure:
        asyncio.run(coroutine)
    assert failure.value.code == "invalid_service_target"
    assert stream.closed
    assert stream.writes == []


@pytest.mark.parametrize("arguments", [{"port": 80}, {"port": 443, "local_address": "1.1.1.1"}])
def test_invalid_tcp_parameters_reject_before_dns(arguments):
    async def forbidden(*args):
        pytest.fail("invalid target reached resolver")

    call = partial(GuardedBackend(resolver=forbidden).connect_tcp, "example", **arguments)
    coroutine = call()
    with pytest.raises(YorungeError) as failure:
        asyncio.run(coroutine)
    assert failure.value.code == "invalid_service_target"


def test_unix_socket_target_is_never_opened():
    call = partial(GuardedBackend().connect_unix_socket, "/never-opened")
    coroutine = call()
    with pytest.raises(YorungeError) as failure:
        asyncio.run(coroutine)
    assert failure.value.code == "invalid_service_target"


@pytest.mark.parametrize("result", [[], [(0, 0, 0, "", ("8.8.8.8", 443))] * 17, [(0,)]])
def test_real_resolver_rejects_empty_excessive_or_malformed_dns(monkeypatch, result):
    async def run():
        async def getaddrinfo(*args, **kwargs):
            assert kwargs == {"type": socket.SOCK_STREAM, "proto": socket.IPPROTO_TCP}
            return result

        monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", getaddrinfo)
        with pytest.raises(YorungeError) as failure:
            await resolve("example", 443, 1)
        assert failure.value.code == "invalid_service_target"

    asyncio.run(run())


@pytest.mark.parametrize("failure", [OSError("DNS unavailable"), TimeoutError()])
def test_real_resolver_normalizes_dns_failures(monkeypatch, failure):
    async def run():
        async def getaddrinfo(*args, **kwargs):
            raise failure

        monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", getaddrinfo)
        expected = (
            httpcore.ConnectTimeout if isinstance(failure, TimeoutError) else httpcore.ConnectError
        )
        with pytest.raises(expected):
            await resolve("example", 443, 1)

    asyncio.run(run())


def test_real_resolver_deduplicates_addresses_and_literal_skips_dns(monkeypatch):
    async def run():
        calls = []

        async def getaddrinfo(*args, **kwargs):
            calls.append(args)
            return [(0, 0, 0, "", (ip, 443)) for ip in ("8.8.8.8", "8.8.8.8", "1.1.1.1")]

        monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", getaddrinfo)
        assert await resolve("8.8.8.8", 443, 1) == ("8.8.8.8",)
        assert calls == []
        assert await resolve("example", 443, 1) == ("8.8.8.8", "1.1.1.1")
        assert calls == [("example", 443)]

    asyncio.run(run())


def test_guarded_pool_expires_idle_connection_without_replaying_http(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("httpcore._async.http11.time.monotonic", lambda: clock[0])
    streams = []

    class Keepalive(Stream):
        async def read(self, max_bytes, timeout=None):
            return b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"

    class Network(Connector):
        async def connect_tcp(self, host, port, **kwargs):
            stream = Keepalive()
            streams.append(stream)
            return stream

    async def resolver(*args):
        return ("8.8.8.8",)

    async def run():
        low = GuardedHttpTransport(backend=GuardedBackend(resolver=resolver, backend=Network(None)))
        async with httpx.AsyncClient(transport=low) as client:
            assert (await client.get("https://example/")).status_code == 200
            clock[0] += 4.9
            assert (await client.get("https://example/")).status_code == 200
            assert len(streams) == 1
            first_writes = list(streams[0].writes)
            clock[0] += 5.1
            assert (await client.get("https://example/")).status_code == 200
            assert len(streams) == 2
            assert streams[0].closed
            assert streams[0].writes == first_writes
        assert all(stream.closed for stream in streams)

    asyncio.run(run())


def test_owned_tls_contexts_disable_environment_keylogging(tmp_path, monkeypatch):
    log = tmp_path / "tls-keylog"
    monkeypatch.setenv("SSLKEYLOGFILE", str(log))

    async def run():
        guarded = GuardedHttpTransport()
        assert guarded._pool._ssl_context.keylog_filename is None
        assert guarded._pool._ssl_context.verify_mode == ssl.CERT_REQUIRED
        assert guarded._pool._ssl_context.check_hostname
        await guarded.aclose()
        async with HttpxTransport() as owned:
            context = owned._client._transport._pool._ssl_context
            assert context.keylog_filename is None
            assert context.verify_mode == ssl.CERT_REQUIRED
            assert context.check_hostname

    asyncio.run(run())
    # SSLContext construction may create an empty/header-only file. No TLS
    # connection exists here; no filesystem-sandbox guarantee is implied.
