"""Real CLI against the TLS fixture; no test target/CA option exists in the product."""

import socket
import ssl
import sys

from tests.fixtures.http_server import LoopbackTransport, loopback_sockets
from yorunge.adapters import llm_context
from yorunge.adapters.http_session import HttpSession
from yorunge.adapters.http_transport import HttpxTransport
from yorunge.cli import main


def run() -> int:
    port, cert = int(sys.argv[1]), sys.argv[2]

    def session():
        return HttpSession(
            transport_factory=lambda: HttpxTransport(
                transport=LoopbackTransport(port, ssl.create_default_context(cafile=cert))
            )
        )

    llm_context.HttpSession = session
    with loopback_sockets(socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo):
        return main(sys.argv[3:])


if __name__ == "__main__":
    raise SystemExit(run())
