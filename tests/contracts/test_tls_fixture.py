"""A silent TCP peer must not block the loopback TLS fixture's accept loop."""

import socket
import ssl
import threading

from tests.fixtures.http_server import TlsServer, certificate, loopback_sockets

CONNECT, CONNECT_EX, GETADDRINFO = (
    socket.socket.connect,
    socket.socket.connect_ex,
    socket.getaddrinfo,
)


def test_tls_fixture_stops_while_an_accepted_peer_has_not_sent_client_hello(tmp_path, monkeypatch):
    entered = threading.Event()
    original = ssl.SSLSocket.do_handshake

    def observe(connection, *args, **kwargs):
        if connection.server_side:
            entered.set()
        return original(connection, *args, **kwargs)

    monkeypatch.setattr(ssl.SSLSocket, "do_handshake", observe)
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        server = TlsServer(certificate(tmp_path), {})
        server.__enter__()
        peer = socket.create_connection(("127.0.0.1", server.port), timeout=2)
        closer = None
        stopped = False
        try:
            assert entered.wait(timeout=3), "the real server handshake must have started"
            closer = threading.Thread(target=server.__exit__, args=(None, None, None))
            closer.start()
            closer.join(timeout=2)
            stopped = not closer.is_alive()
        finally:
            # Even the old blocking implementation is released before the assertion.
            peer.close()
            if closer is None:
                server.__exit__(None, None, None)
            else:
                closer.join(timeout=5)
        assert closer is not None
        assert not closer.is_alive()
        assert stopped, "a silent peer blocked the listening thread's shutdown"
