"""Run the native download controller with retained logs and fail-closed CI decisions."""

from __future__ import annotations

import argparse
import os
import re
import runpy
import select
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Any

ROOT = Path(__file__).resolve().parents[1]
DRIVER = runpy.run_path(str(ROOT / "scripts/benchmark-download.py"))
DIAGNOSTIC = runpy.run_path(str(ROOT / "scripts/download_diagnostic.py"))
CHECKS = DRIVER["CHECKS"]
SCHEDULING_SECONDS = 2700
_termination_depth = 0


@contextmanager
def termination_signals() -> Iterator[None]:
    global _termination_depth
    previous = signal.getsignal(signal.SIGTERM)

    def interrupted(signum: int, frame: object) -> None:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        raise SystemExit(128 + signum)

    first = _termination_depth == 0
    if first:
        signal.signal(signal.SIGTERM, interrupted)
    _termination_depth += 1
    try:
        yield
    finally:
        _termination_depth -= 1
        if first:
            signal.signal(signal.SIGTERM, previous)


def stop_group(process: subprocess.Popen[bytes]) -> None:
    if process.returncode is not None:
        raise ValueError("download supervisor ownership ended before group cleanup")
    # No poll()/wait() has reaped this session leader yet. Its PID cannot have
    # been reassigned to an unrelated group, even if the supervisor crashed.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=10)


def execute(command: list[str], stdout: Path, stderr: Path) -> int:
    if signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL:
        raise ValueError("download CI requires default child reaping ownership")
    with termination_signals(), stdout.open("xb") as out, stderr.open("xb") as err:
        control, child = socket.socketpair()
        with control, child:
            return owned_controller(command, control, child, out, err)


def wait_status(control: socket.socket, command: list[str]) -> int:
    end = time.monotonic() + SCHEDULING_SECONDS
    data = bytearray()
    while b"\n" not in data:
        remaining = end - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(command, SCHEDULING_SECONDS)
        ready, _, _ = select.select([control], [], [], min(remaining, 1.0))
        if not ready:
            continue
        chunk = control.recv(32 - len(data))
        if not chunk:
            raise ValueError("download supervisor closed before controller status")
        data.extend(chunk)
        if len(data) >= 32:
            raise ValueError("download supervisor status exceeded bound")
    if re.fullmatch(rb"-?\d{1,3}\n", data, flags=re.ASCII) is None:
        raise ValueError("invalid download supervisor status")
    code = int(data)
    if not -128 <= code <= 255:
        raise ValueError("invalid download controller exit code")
    return code


def owned_controller(
    command: list[str],
    control: socket.socket,
    child: socket.socket,
    out: IO[bytes],
    err: IO[bytes],
) -> int:
    supervisor = [
        sys.executable,
        "-I",
        str(ROOT / "tests/fixtures/upload_supervisor.py"),
        "--control-fd",
        str(child.fileno()),
        "--",
        *command,
    ]
    process = None
    try:
        process = subprocess.Popen(
            supervisor,
            cwd=ROOT,
            env=DRIVER["CONTROL"]["environment"](),
            stdout=out,
            stderr=err,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            pass_fds=(child.fileno(),),
        )
        child.close()
        return wait_status(control, command)
    finally:
        if process is not None:
            stop_group(process)


def copy_logs(workspace: Path, stdout: Path, stderr: Path) -> None:
    if not workspace.exists():
        workspace.mkdir(mode=0o700)
    if workspace.is_symlink() or any(parent.is_symlink() for parent in workspace.parents):
        raise ValueError("download CI workspace must not use symlinks")
    copies = []
    for source, name in ((stdout, "stdout.json"), (stderr, "stderr.txt")):
        content = CHECKS["read_bounded"](source, DIAGNOSTIC["MAX_FILE"])
        copies.append((workspace / name, content))
    for destination, content in copies:
        if destination.exists():
            if CHECKS["read_bounded"](destination, DIAGNOSTIC["MAX_FILE"]) != content:
                raise ValueError("existing download CI log differs; original preserved")
        else:
            with destination.open("xb") as target:
                target.write(content)


def arguments(args: argparse.Namespace, environment: dict[str, Any]) -> list[str]:
    wheels = sorted(args.wheel_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError("download CI requires the single installed candidate wheel")
    return [
        sys.executable,
        str(ROOT / "scripts/benchmark-download.py"),
        "--python",
        str(args.python.absolute()),
        "--wheel",
        str(wheels[0].absolute()),
        "--workspace",
        str(args.workspace.absolute()),
        "--output",
        str(args.output.absolute()),
        "--cpu",
        CHECKS["text_value"](environment["cpu"]),
        "--disk-type",
        CHECKS["text_value"](environment["disk_type"]),
        "--run-url",
        args.run_url,
    ]


def validate_output(path: Path, root: Path, environment: dict[str, Any]) -> None:
    report = CHECKS["decode"](CHECKS["read_bounded"](path, CHECKS["MAX_REPORT_BYTES"]))
    # A smoke subset can pass every rule it has: only the complete twelve-run report is acceptance.
    if not DRIVER["EVIDENCE"]["summarize_report"](report)["accepted"]:
        raise ValueError("download CI native budget was not accepted")
    if report["source_commit"] != environment.get("source_sha") or report["environment"] != {
        name: environment.get(name) for name in ("cpu", "disk_type")
    }:
        raise ValueError("download CI report differs from this run environment")
    for row in report["runs"]:
        runtime = row["client"]["runtime"]
        if any(
            runtime[name] != environment.get(key)
            for name, key in (
                ("os", "platform"),
                ("python", "python"),
                ("sqlite", "sqlite"),
                ("machine", "architecture"),
            )
        ):
            raise ValueError("download CI runtime differs from compatibility cell")
    current = DRIVER["EVIDENCE"]["source"](root)["source_sha256"]
    if any(
        report["provenance"][field]["source_sha256"] != current
        for field in ("source_before", "source_after")
    ):
        raise ValueError("download CI report differs from current source bytes")
    if report["provenance"]["locked_runtime"] != DRIVER["STREAM"]["locked_runtime"](root):
        raise ValueError("download CI report differs from frozen runtime")


def check(args: argparse.Namespace) -> int:
    with termination_signals():
        return _check(args)


def _check(args: argparse.Namespace) -> int:
    if sys.platform not in {"linux", "darwin"}:
        raise ValueError("native download CI requires Linux or macOS")
    CHECKS["pattern_value"](args.run_url, CHECKS["CI_RUN_URL"])
    environment = CHECKS["decode"](CHECKS["read_bounded"](args.environment, 1_048_576))
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    ).stdout.strip()
    if environment.get("source_sha") != commit:
        raise ValueError("download CI environment source differs from checkout")
    command = arguments(args, environment)
    workspace = DRIVER["STREAM"]["new_path"](args.workspace)
    stdout = DRIVER["STREAM"]["new_path"](
        workspace.with_name(workspace.name + "-controller-stdout.txt")
    )
    stderr = DRIVER["STREAM"]["new_path"](
        workspace.with_name(workspace.name + "-controller-stderr.txt")
    )
    try:
        code = execute(command, stdout, stderr)
        copy_logs(workspace, stdout, stderr)
        if code != 0:
            raise ValueError("download CI controller failed; original diagnostics retained")
        validate_output(args.output, ROOT, environment)
    except BaseException:
        copy_logs(workspace, stdout, stderr)
        DIAGNOSTIC["retain"](
            ROOT,
            workspace,
            args.output.stem + "-ci-rejected.json",
            commit,
            "unverified_measurement",
            args.run_url,
        )
        raise
    print("Validated twelve native download processes and current source bytes.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True, type=Path)
    parser.add_argument("--wheel-dir", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--environment", required=True, type=Path)
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()
    try:
        return check(args)
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        RecursionError,
        subprocess.SubprocessError,
    ) as error:
        parser.exit(1, f"Download CI failed: {error}; retained files are not acceptance.\n")


if __name__ == "__main__":
    raise SystemExit(main())
