"""Actual controller lifecycle, retained logs and current-run CI binding."""

import copy
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.fixtures.upload_report import report as report_vector

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def helper():
    return runpy.run_path(str(ROOT / "scripts/upload_ci.py"))


def test_real_controller_timeout_kills_and_reaps_owned_group_with_original_logs(
    tmp_path, helper, monkeypatch
):
    namespace = helper["execute"].__globals__
    monkeypatch.setitem(namespace, "SCHEDULING_SECONDS", 0.2)
    original = subprocess.Popen
    processes = []

    def started(*args, **kwargs):
        process = original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(subprocess, "Popen", started)
    stdout, stderr = tmp_path / "stdout", tmp_path / "stderr"
    command = [
        sys.executable,
        "-I",
        "-c",
        "import os,time;print(os.getpid(),flush=True);time.sleep(60)",
    ]
    with pytest.raises(subprocess.TimeoutExpired):
        helper["execute"](command, stdout, stderr)
    assert len(processes) == 1 and processes[0].returncode == -9
    assert stdout.read_text().strip() == str(processes[0].pid)
    assert stderr.read_bytes() == b""
    with pytest.raises(ChildProcessError):
        os.waitpid(processes[0].pid, os.WNOHANG)


def test_real_controller_nonzero_preserves_non_utf8_and_stderr(tmp_path, helper):
    stdout, stderr = tmp_path / "stdout", tmp_path / "stderr"
    command = [
        sys.executable,
        "-I",
        "-c",
        "import os;os.write(1,b'\\xffbad');os.write(2,b'failure');raise SystemExit(7)",
    ]
    assert helper["execute"](command, stdout, stderr) == 7
    assert stdout.read_bytes() == b"\xffbad" and stderr.read_bytes() == b"failure"


def test_log_copy_is_lossless_idempotent_and_never_overwrites_different_bytes(tmp_path, helper):
    root = tmp_path.resolve()
    stdout, stderr, workspace = root / "stdout", root / "stderr", root / "workspace"
    stdout.write_bytes(b"\xfforiginal")
    stderr.write_bytes(b"error")
    helper["copy_logs"](workspace, stdout, stderr)
    helper["copy_logs"](workspace, stdout, stderr)
    assert (workspace / "stdout.json").read_bytes() == b"\xfforiginal"
    stdout.write_bytes(b"changed")
    with pytest.raises(ValueError):
        helper["copy_logs"](workspace, stdout, stderr)
    assert (workspace / "stdout.json").read_bytes() == b"\xfforiginal"


@pytest.mark.parametrize("damage", ["missing", "oversize", "symlink"])
def test_unretainable_controller_logs_fail_before_partial_copy(tmp_path, helper, damage):
    root = tmp_path.resolve()
    stdout, stderr, workspace = root / "stdout", root / "stderr", root / "workspace"
    stdout.write_bytes(b"original")
    if damage == "oversize":
        stderr.write_bytes(b"x" * (helper["DRIVER"]["DIAGNOSTIC"]["MAX_FILE"] + 1))
    elif damage == "symlink":
        stderr.symlink_to(stdout)
    with pytest.raises(ValueError):
        helper["copy_logs"](workspace, stdout, stderr)
    assert not (workspace / "stdout.json").exists()
    assert stdout.read_bytes() == b"original"


@pytest.mark.parametrize("exit_code", [0, 7])
def test_missing_or_failed_native_controller_is_archived_but_never_accepted(
    tmp_path, helper, monkeypatch, exit_code
):
    root = tmp_path.resolve()
    namespace = helper["check"].__globals__
    monkeypatch.setitem(namespace, "ROOT", root)
    (root / "dist").mkdir()
    (root / "docs/research").mkdir(parents=True)
    wheels = root / "wheels"
    wheels.mkdir()
    (wheels / "package.whl").write_bytes(b"unused synthetic")
    environment = root / "ci.json"
    environment.write_text(
        json.dumps({"source_sha": "a" * 40, "cpu": "synthetic", "disk_type": "unknown"})
    )
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout="a" * 40))

    def execute(command, stdout, stderr):
        stdout.write_bytes(b"\xffpartial controller")
        stderr.write_bytes(b"synthetic error")
        return exit_code

    monkeypatch.setitem(namespace, "execute", execute)
    args = SimpleNamespace(
        environment=environment,
        wheel_dir=wheels,
        python=root / "python",
        workspace=root / "upload-check",
        output=root / "dist/upload.json",
        run_url="https://github.com/HodeTech/Yorunge/actions/runs/123",
    )
    with pytest.raises(ValueError):
        helper["check"](args)
    assert not args.output.exists()
    assert (args.workspace / "stdout.json").read_bytes() == b"\xffpartial controller"
    diagnostic = namespace["CHECKS"]["decode"]((root / "dist/upload-ci-rejected.json").read_bytes())
    assert namespace["DRIVER"]["DIAGNOSTIC"]["summarize"](diagnostic)["accepted"] is False
    assert namespace["CHECKS"]["verify"](root) == 1


@pytest.mark.parametrize("damage", [None, "source", "oracle", "lock", "commit", "cpu", "python"])
def test_native_output_matches_actual_checkout_lock_and_compatibility_cell(
    tmp_path, helper, monkeypatch, damage
):
    namespace = helper["validate_output"].__globals__
    evidence = namespace["DRIVER"]["EVIDENCE"]
    report = report_vector(evidence["METHOD"], evidence["LIMITS"])
    current = copy.deepcopy(report["provenance"]["source_before"])
    locked = copy.deepcopy(report["provenance"]["locked_runtime"])
    runtime = report["runs"][0]["client"]["runtime"]
    environment = {
        **report["environment"],
        "source_sha": report["source_commit"],
        "platform": runtime["os"],
        "python": runtime["python"],
        "sqlite": runtime["sqlite"],
        "architecture": runtime["machine"],
    }
    if damage in {"source", "oracle"}:
        key = "src/yorunge/__init__.py" if damage == "source" else evidence["VECTOR_PATH"]
        current["source_sha256"][key] = "9" * 64
    elif damage == "lock":
        locked["httpx"] = "0.28.2"
    elif damage == "commit":
        environment["source_sha"] = "b" * 40
    elif damage == "cpu":
        environment["cpu"] = "different"
    elif damage == "python":
        environment["python"] = "different"
    monkeypatch.setitem(evidence, "source", lambda root: current)
    monkeypatch.setitem(namespace["DRIVER"]["STREAM"], "locked_runtime", lambda root: locked)
    output = tmp_path / "upload.json"
    output.write_bytes(namespace["CHECKS"]["encode"](report))
    if damage is None:
        helper["validate_output"](output, tmp_path, environment)
    else:
        with pytest.raises(ValueError):
            helper["validate_output"](output, tmp_path, environment)
