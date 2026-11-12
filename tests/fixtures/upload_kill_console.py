"""Test-only real CLI/TLS wiring: pause at a production boundary to be killed, or a later clock.

Like ``upload_console.py`` plus (a) a pause after any armed stage of an original upload or of a
continuation (``presign-0``, ``put-1``, ``confirm-0``, ``cont-confirm-0`` ...), after which the
parent SIGKILLs the process, and (b) ``--clock-shift SECONDS``: the product's system clock runs that
far ahead, which is how a test makes the lease of a killed process lapse without waiting for it.
Never a production flag or a selectable backend.
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.fixtures.upload_network import loopback_upload  # noqa: E402
from yorunge.cli import main  # noqa: E402


def install_clock_shift(seconds: float) -> None:
    from yorunge.adapters import capability_cache

    def now(self: object) -> datetime:
        return datetime.now(UTC) + timedelta(seconds=seconds)

    def monotonic(self: object) -> float:
        return time.monotonic() + seconds

    capability_cache.SystemClock.now = now  # type: ignore[method-assign]
    capability_cache.SystemClock.monotonic = monotonic  # type: ignore[method-assign]


def install_checkpoint(boundary: str, ready: Path) -> None:
    """Pause only this fixture process after a committed production boundary."""
    from yorunge.adapters.upload_continuation import ContinuationStages
    from yorunge.adapters.upload_original import _Environment

    def pause() -> None:
        with ready.open("xb") as marker:
            marker.write(b"paused\n")  # never hand the operation id to the parent
        threading.Event().wait(120)
        raise AssertionError("killed fixture resumed")

    admit, arm = _Environment.admit, _Environment.arm

    def admitted(self, check):  # type: ignore[no-untyped-def]
        result = admit(self, check)
        if boundary == "admission":
            pause()
        return result

    def armed(self, check, kind, index=None):  # type: ignore[no-untyped-def]
        result = arm(self, check, kind, index)
        if boundary in (kind, kind if index is None else f"{kind}-{index}"):
            pause()
        return result

    _Environment.admit, _Environment.arm = admitted, armed  # type: ignore[method-assign]
    if boundary.startswith("cont-"):
        continued = ContinuationStages.arm

        def cont_armed(self, check, kind, index=None):  # type: ignore[no-untyped-def]
            result = continued(self, check, kind, index)
            name = kind if index is None else f"{kind}-{index}"
            if boundary in (f"cont-{kind}", f"cont-{name}"):
                pause()
            return result

        ContinuationStages.arm = cont_armed  # type: ignore[method-assign]


def run() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ca", required=True, type=Path)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--checkpoint")
    parser.add_argument("--ready", type=Path)
    parser.add_argument("--clock-shift", type=float, default=0.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if (args.checkpoint is None) != (args.ready is None):
        parser.error("checkpoint and ready must be selected together")
    if args.clock_shift:
        install_clock_shift(args.clock_shift)
    if args.checkpoint is not None:
        install_checkpoint(args.checkpoint, args.ready)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    with loopback_upload(args.ca, args.port):
        return main(command)


if __name__ == "__main__":
    raise SystemExit(run())
