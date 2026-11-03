"""Run the native upload controller with retained logs and fail-closed CI decisions."""

from __future__ import annotations

import argparse
import os
import runpy
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DRIVER = runpy.run_path(str(ROOT / "scripts/benchmark-upload.py"))
CHECKS = DRIVER["CHECKS"]
SCHEDULING_SECONDS = 2700


def stop_group(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=10)


def execute(command: list[str], stdout: Path, stderr: Path) -> int:
    with stdout.open("xb") as out, stderr.open("xb") as err:
        with subprocess.Popen(
            command,
            cwd=ROOT,
            env=DRIVER["CONTROL"]["environment"](),
            stdout=out,
            stderr=err,
            start_new_session=True,
        ) as process:
            try:
                return process.wait(timeout=SCHEDULING_SECONDS)
            except BaseException:
                stop_group(process)
                raise


def copy_logs(workspace: Path, stdout: Path, stderr: Path) -> None:
    if not workspace.exists():
        workspace.mkdir(mode=0o700)
    if workspace.is_symlink() or any(parent.is_symlink() for parent in workspace.parents):
        raise ValueError("upload CI workspace must not use symlinks")
    copies = []
    for source, name in ((stdout, "stdout.json"), (stderr, "stderr.txt")):
        content = CHECKS["read_bounded"](source, DRIVER["DIAGNOSTIC"]["MAX_FILE"])
        copies.append((workspace / name, content))
    for destination, content in copies:
        if destination.exists():
            if CHECKS["read_bounded"](destination, DRIVER["DIAGNOSTIC"]["MAX_FILE"]) != content:
                raise ValueError("existing upload CI log differs; original preserved")
        else:
            with destination.open("xb") as target:
                target.write(content)


def arguments(args: argparse.Namespace, environment: dict[str, Any]) -> list[str]:
    wheels = sorted(args.wheel_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError("upload CI requires the single installed candidate wheel")
    return [
        sys.executable,
        str(ROOT / "scripts/benchmark-upload.py"),
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
    if not DRIVER["EVIDENCE"]["summarize_report"](report)["passed"]:
        raise ValueError("upload CI native budget did not pass")
    if report["source_commit"] != environment.get("source_sha") or report["environment"] != {
        name: environment.get(name) for name in ("cpu", "disk_type")
    }:
        raise ValueError("upload CI report differs from this run environment")
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
            raise ValueError("upload CI runtime differs from compatibility cell")
    current = DRIVER["EVIDENCE"]["source"](root)["source_sha256"]
    if any(
        report["provenance"][field]["source_sha256"] != current
        for field in ("source_before", "source_after")
    ):
        raise ValueError("upload CI report differs from current source/oracle bytes")
    if report["provenance"]["locked_runtime"] != DRIVER["STREAM"]["locked_runtime"](root):
        raise ValueError("upload CI report differs from frozen runtime")


def check(args: argparse.Namespace) -> int:
    if sys.platform not in {"linux", "darwin"}:
        raise ValueError("native upload CI requires Linux or macOS")
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
        raise ValueError("upload CI environment source differs from checkout")
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
            raise ValueError("upload CI controller failed; original diagnostics retained")
        validate_output(args.output, ROOT, environment)
    except BaseException:
        copy_logs(workspace, stdout, stderr)
        DRIVER["DIAGNOSTIC"]["retain"](
            ROOT,
            workspace,
            args.output.stem + "-ci-rejected.json",
            commit,
            "unverified_measurement",
            args.run_url,
        )
        raise
    print("Validated twelve native upload processes and current source bytes.")
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
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Upload CI failed: {error}; retained files are not acceptance.\n")


if __name__ == "__main__":
    raise SystemExit(main())
