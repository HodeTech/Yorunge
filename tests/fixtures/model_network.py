"""Test-only TLS mapping of the provider hosts for ``models download``; never a production flag.

The weights download runs on a ``TransferSession`` (one client and pool for the JSON call and the
signed GET). Every session made by the product reaches one of ``HOSTS`` on a loopback port, with
the product's own guarded transport on top of a fixture backend, so the wire behaviour under test
is the real one.
"""

from __future__ import annotations

import socket
import ssl
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path

import httpcore

from tests.fixtures.http_server import loopback_sockets
from yorunge.adapters.guarded_http import GuardedHttpTransport
from yorunge.adapters.guarded_network import GuardedBackend
from yorunge.adapters.storage_transport import TransferHttpxTransport, TransferSession
from yorunge.application.http_transport import HttpCredential

HOSTS = ("api.ssyz.org.tr", "other.ssyz.org.tr")  # the canonical host and a second provider


@contextmanager
def loopback_models(ca: Path, port: int):
    """Every ``TransferSession`` made by the product reaches one of ``HOSTS`` on ``port``."""
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

    original = TransferSession.__init__

    def initialize(
        session: TransferSession,
        credential: HttpCredential,
        *,
        transport_factory: Callable[[], TransferHttpxTransport] | None = None,
        storage_origins: tuple[str, ...] = (),
    ) -> None:
        assert transport_factory is None, "unexpected composition override"
        original(
            session,
            credential,
            transport_factory=lambda: TransferHttpxTransport(
                credential,
                transport=GuardedHttpTransport(backend=FixtureNetwork(), verify=context),
                storage_origins=storage_origins,
            ),
            storage_origins=storage_origins,
        )

    TransferSession.__init__ = initialize  # type: ignore[method-assign]
    try:
        with loopback_sockets(socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo):
            yield
    finally:
        TransferSession.__init__ = original  # type: ignore[method-assign]
