"""A real TCP peer withholds TLS: cancellation must close the unpooled socket."""

import asyncio
import socket
import ssl

import httpcore
import pytest

from tests.fixtures.http_server import loopback_sockets
from yorunge.adapters.guarded_network import GuardedStream

CONNECT, CONNECT_EX, GETADDRINFO = (
    socket.socket.connect,
    socket.socket.connect_ex,
    socket.getaddrinfo,
)


@pytest.fixture(autouse=True)
def loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


def test_cancel_handshake_delivers_eof_to_real_peer_before_session_close():
    async def run():
        hello, eof, finished = asyncio.Event(), asyncio.Event(), asyncio.Event()
        records = []

        async def peer(reader, writer):
            try:
                records.append(await reader.read(65_536))
                hello.set()
                records.append(await reader.read(65_536))
                eof.set()
            finally:
                writer.close()
                await writer.wait_closed()
                finished.set()

        server = await asyncio.start_server(peer, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        raw = await httpcore.AnyIOBackend().connect_tcp("127.0.0.1", port, timeout=1)
        guarded = GuardedStream(raw, "localhost", frozenset({"127.0.0.1"}), lambda ip: True)
        task = asyncio.create_task(guarded.start_tls(ssl.create_default_context(), "localhost"))
        try:
            await asyncio.wait_for(hello.wait(), 1)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            await asyncio.wait_for(eof.wait(), 1)
            assert records[0].startswith(b"\x16\x03")
            assert records[1] == b""
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await raw.aclose()
            server.close()
            await server.wait_closed()
            await asyncio.wait_for(finished.wait(), 1)

    asyncio.run(run())
