"""Test-only real CLI/TLS wiring for ``models download``; never a production flag."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.fixtures.model_network import loopback_models  # noqa: E402
from yorunge.cli import main  # noqa: E402


def run() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ca", required=True, type=Path)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    with loopback_models(args.ca, args.port):
        return main(command)


if __name__ == "__main__":
    raise SystemExit(run())
