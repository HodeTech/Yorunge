"""Test-only TLS reader/CLI renderer composition, never a product command."""

from __future__ import annotations

import argparse
import asyncio
import socket
import ssl
import sys
import time
from collections.abc import Sequence
from pathlib import Path

# Only test helpers need the checkout. Product imports resolve from the active
# installation; adding src here would hide a broken installed artifact.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.fixtures.http_server import LoopbackTransport, loopback_sockets  # noqa: E402
from yorunge.adapters.http_transport import HttpxTransport  # noqa: E402
from yorunge.application.http_transport import RAW_LIMIT, HttpRequest  # noqa: E402
from yorunge.application.stream_results import open_stream  # noqa: E402
from yorunge.cli.output import OutputRenderer  # noqa: E402
from yorunge.domain.credentials import normalize_target  # noqa: E402
from yorunge.domain.errors import YorungeError  # noqa: E402
from yorunge.domain.models import Model  # noqa: E402


class Value(Model):
    text: str


async def consume(
    renderer: OutputRenderer, ca: Path, port: int, stream_id: str, operation_id: str
) -> int:
    context = ssl.create_default_context(cafile=str(ca))
    request = HttpRequest(
        normalize_target("https://localhost/v1"),
        "GET",
        "events",
        service_id="evren-platform",
        max_bytes=RAW_LIMIT,
    )
    async with HttpxTransport(transport=LoopbackTransport(port, context)) as transport:
        async with open_stream(
            transport,
            request,
            Value,
            deadline=time.monotonic() + 5,
            stream_id=stream_id,
            operation_id=operation_id,
        ) as stream:
            async for event in stream:
                renderer.event(event)
    return renderer.finish()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ca", required=True, type=Path)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--stream-id", required=True)
    parser.add_argument("--operation-id", required=True)
    args = parser.parse_args(argv)
    renderer = OutputRenderer("ndjson", stream_id=args.stream_id, operation_id=args.operation_id)
    try:
        with loopback_sockets(socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo):
            return asyncio.run(
                consume(renderer, args.ca, args.port, args.stream_id, args.operation_id)
            )
    except YorungeError as error:
        return renderer.error(error)
    except KeyboardInterrupt:
        return renderer.error(YorungeError("request_cancelled"))


if __name__ == "__main__":
    raise SystemExit(main())
