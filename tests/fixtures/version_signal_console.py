"""Test-only: ``datasets versions`` over loopback TLS, with a SIGINT sent to itself at a boundary.

Like ``version_console.py`` plus one named point at which the process interrupts itself with a
real signal: after the provider reads, at the stage check, right before the link, right after it,
in the stage's cleanup, when the publication scope ends, or when the result is being written. The
point is a test input; the production code has no such flag.
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.fixtures.version_network import loopback_versions  # noqa: E402
from yorunge.cli import main  # noqa: E402

POINTS = (
    "none",
    "after_reads",
    "stage_checked",
    "before_link",
    "after_link",
    "in_cleanup",
    "after_publish",
    "writing_result",
)


def interrupt() -> None:
    os.kill(os.getpid(), signal.SIGINT)


def install(point: str) -> None:
    from yorunge.adapters import artifact_publisher, dataset_version_api
    from yorunge.cli import output

    publisher = artifact_publisher.ArtifactPublisher
    if point == "after_reads":
        real_summary = dataset_version_api.bound_summary

        def after_reads(*args, **keywords):  # type: ignore[no-untyped-def]
            result = real_summary(*args, **keywords)
            interrupt()
            return result

        dataset_version_api.bound_summary = after_reads  # type: ignore[assignment]
    elif point == "stage_checked":
        real_check = publisher._check_stage

        def stage_checked(self, *args, **keywords):  # type: ignore[no-untyped-def]
            interrupt()
            return real_check(self, *args, **keywords)

        publisher._check_stage = stage_checked  # type: ignore[method-assign]
    elif point == "before_link":
        real_link = os.link

        def before_link(*args, **keywords):  # type: ignore[no-untyped-def]
            interrupt()
            return real_link(*args, **keywords)

        os.link = before_link
    elif point == "after_link":
        real_target = publisher._check_target

        def after_link(self, *args, **keywords):  # type: ignore[no-untyped-def]
            interrupt()
            return real_target(self, *args, **keywords)

        publisher._check_target = after_link  # type: ignore[method-assign]
    elif point == "in_cleanup":
        real_remove = publisher._remove_stage

        def in_cleanup(self, *args, **keywords):  # type: ignore[no-untyped-def]
            result = real_remove(self, *args, **keywords)
            interrupt()
            return result

        publisher._remove_stage = in_cleanup  # type: ignore[method-assign]
    elif point == "after_publish":
        real_scope = dataset_version_api.binding_target

        @contextmanager
        def after_publish(target):  # type: ignore[no-untyped-def]
            with real_scope(target) as held:
                yield held
            interrupt()

        dataset_version_api.binding_target = after_publish  # type: ignore[assignment]
    elif point == "writing_result":
        real_write = output.write_utf8

        def writing_result(message, stream):  # type: ignore[no-untyped-def]
            if stream is sys.stdout:
                interrupt()
            return real_write(message, stream)

        output.write_utf8 = writing_result
    elif point != "none":
        raise SystemExit(f"unknown point {point}")


def run() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ca", required=True, type=Path)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--point", required=True, choices=POINTS)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    with loopback_versions(args.ca, args.port):
        install(args.point)
        return main(command)


if __name__ == "__main__":
    raise SystemExit(run())
