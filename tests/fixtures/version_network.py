"""Test-only TLS mapping of two provider hosts for the version reads; never a production flag."""

from __future__ import annotations

import socket
import ssl
from contextlib import contextmanager
from pathlib import Path

import httpcore

from tests.fixtures.http_server import loopback_sockets
from yorunge.adapters.guarded_http import GuardedHttpTransport
from yorunge.adapters.guarded_network import GuardedBackend
from yorunge.adapters.http_session import HttpSession
from yorunge.adapters.http_transport import HttpxTransport

HOSTS = ("api.ssyz.org.tr", "other.ssyz.org.tr")  # the canonical host and a second provider


@contextmanager
def loopback_versions(ca: Path, port: int):
    """Every ``HttpSession`` made by the product reaches one of ``HOSTS`` on a loopback port."""
    context = ssl.create_default_context(cafile=str(ca))

    class FixtureNetwork(GuardedBackend):
        def __init__(self) -> None:
            async def resolver(host, requested_port, timeout):
                assert host in HOSTS and requested_port == 443
                return ("127.0.0.1",)

            super().__init__(resolver=resolver, allowed=lambda address: address == "127.0.0.1")

        async def _connect(self, pinned, requested_port, timeout, options, original_host):
            assert pinned == "127.0.0.1" and requested_port == 443
            assert original_host in HOSTS
            return await httpcore.AnyIOBackend().connect_tcp(
                pinned, port, timeout=timeout, socket_options=options
            )

    original = HttpSession.__init__

    def initialize(session, *, transport_factory=HttpxTransport):
        assert transport_factory is HttpxTransport, "unexpected composition override"
        original(
            session,
            transport_factory=lambda: HttpxTransport(
                transport=GuardedHttpTransport(backend=FixtureNetwork(), verify=context)
            ),
        )

    HttpSession.__init__ = initialize  # type: ignore[method-assign]
    try:
        with loopback_sockets(socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo):
            yield
    finally:
        HttpSession.__init__ = original  # type: ignore[method-assign]
