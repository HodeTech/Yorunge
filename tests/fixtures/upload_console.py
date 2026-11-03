"""Test-only real CLI/TLS wiring; never a production flag or selectable backend."""

from __future__ import annotations

import argparse
import socket
import ssl
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpcore  # noqa: E402

from tests.fixtures.http_server import loopback_sockets  # noqa: E402
from yorunge.adapters.guarded_http import GuardedHttpTransport  # noqa: E402
from yorunge.adapters.guarded_network import GuardedBackend  # noqa: E402
from yorunge.adapters.upload_http import UploadHttpxTransport, UploadSession  # noqa: E402
from yorunge.cli import main  # noqa: E402


def install_checkpoint(boundary: str, ready: Path) -> None:
    """Pause only this fixture process after a committed production boundary."""
    from yorunge.adapters.upload_original import _Environment

    admit, arm = _Environment.admit, _Environment.arm

    def pause():
        with ready.open("xb") as marker:
            marker.write(b"paused\n")  # Never return the operation ID to the parent.
        threading.Event().wait(60)
        raise AssertionError("killed fixture resumed")

    def admitted(self, check):
        result = admit(self, check)
        if boundary == "admission":
            pause()
        return result

    def armed(self, check, kind, index=None):
        result = arm(self, check, kind, index)
        if boundary == "create-intent" and kind == "create":
            pause()
        return result

    _Environment.admit, _Environment.arm = admitted, armed


def run() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ca", required=True, type=Path)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--checkpoint", choices=("admission", "create-intent"))
    parser.add_argument("--ready", type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if (args.checkpoint is None) != (args.ready is None):
        parser.error("checkpoint and ready must be selected together")
    if args.checkpoint is not None:
        install_checkpoint(args.checkpoint, args.ready)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    context = ssl.create_default_context(cafile=str(args.ca))

    class FixtureNetwork(GuardedBackend):
        def __init__(self):
            async def resolver(host, port, timeout):
                assert host == "api.ssyz.org.tr" and port == 443
                return ("127.0.0.1",)

            super().__init__(resolver=resolver, allowed=lambda address: address == "127.0.0.1")

        async def _connect(self, pinned, port, timeout, options, original_host):
            assert pinned == "127.0.0.1" and port == 443 and original_host == "api.ssyz.org.tr"
            return await httpcore.AnyIOBackend().connect_tcp(
                pinned, args.port, timeout=timeout, socket_options=options
            )

    original = UploadSession.__init__

    def initialize(self, credential, budget, **kwargs):
        assert not kwargs, "unexpected composition override"
        original(
            self,
            credential,
            budget,
            transport_factory=lambda: UploadHttpxTransport(
                credential,
                budget,
                transport=GuardedHttpTransport(backend=FixtureNetwork(), verify=context),
            ),
        )

    UploadSession.__init__ = initialize
    with loopback_sockets(socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo):
        return main(command)


if __name__ == "__main__":
    raise SystemExit(run())
