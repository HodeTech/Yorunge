"""Actual controller lifecycle, retained logs and current-run CI binding."""

import copy
import json
import os
import runpy
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.fixtures.upload_report import report as report_vector

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.usefixtures("evidence_publication_context")


@pytest.fixture(scope="module")
def helper():
    return runpy.run_path(str(ROOT / "scripts/upload_ci.py"))


def test_real_controller_timeout_kills_and_reaps_owned_group_with_original_logs(
    tmp_path, helper, monkeypatch
):
    namespace = helper["execute"].__globals__
    monkeypatch.setitem(namespace, "SCHEDULING_SECONDS", 0.5)
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
    assert len(processes) == 1
    assert processes[0].returncode == -9
    assert int(stdout.read_text().strip()) != processes[0].pid
    assert stderr.read_bytes() == b""
    with pytest.raises(ChildProcessError):
        os.waitpid(processes[0].pid, os.WNOHANG)


def stopped(identity):
    result = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(identity)], capture_output=True, text=True, timeout=5
    )
    return result.returncode == 1 or result.stdout.strip().startswith("Z")


def eventually_stopped(identity):
    end = time.monotonic() + 3
    while not stopped(identity):
        if time.monotonic() >= end:
            return False
        time.sleep(0.01)
    return True


def test_reaped_process_cannot_be_used_to_signal_a_reused_group(helper, monkeypatch):
    def unexpected(*args):
        pytest.fail("reaped process must not signal any group")

    monkeypatch.setattr(os, "killpg", unexpected)
    process = SimpleNamespace(returncode=0, pid=os.getpid())
    with pytest.raises(ValueError, match="ownership ended"):
        helper["stop_group"](process)


def test_nondefault_child_reaping_is_rejected_before_spawn(tmp_path, helper, monkeypatch):
    original = signal.getsignal
    monkeypatch.setattr(
        signal,
        "getsignal",
        lambda name: signal.SIG_IGN if name == signal.SIGCHLD else original(name),
    )
    stdout, stderr = tmp_path / "stdout", tmp_path / "stderr"
    with pytest.raises(ValueError, match="child reaping ownership"):
        helper["execute"]([sys.executable, "-I", "-c", "raise SystemExit(0)"], stdout, stderr)
    assert not stdout.exists()
    assert not stderr.exists()


def test_abrupt_controller_exit_cannot_leave_owned_descendant_writing(tmp_path, helper):
    stdout, stderr = tmp_path / "stdout", tmp_path / "stderr"
    code = (
        "import json,os,subprocess,sys;"
        "child=subprocess.Popen([sys.executable,'-I','-c','import time;time.sleep(5)']);"
        "print(json.dumps({'pid':child.pid,'group':os.getpgrp()}),flush=True);"
        "raise SystemExit(7)"
    )
    assert helper["execute"]([sys.executable, "-I", "-c", code], stdout, stderr) == 7
    child = json.loads(stdout.read_bytes())
    try:
        assert eventually_stopped(child["pid"])
    finally:
        if not stopped(child["pid"]) and os.getpgid(child["pid"]) == child["group"]:
            os.killpg(child["group"], signal.SIGKILL)


def test_parent_control_eof_stops_supervisor_group_before_reap(tmp_path):
    control, child = socket.socketpair()
    stdout, stderr = tmp_path / "stdout", tmp_path / "stderr"
    with stdout.open("xb") as out, stderr.open("xb") as err, control, child:
        process = subprocess.Popen(
            [
                sys.executable,
                "-I",
                str(ROOT / "tests/fixtures/upload_supervisor.py"),
                "--control-fd",
                str(child.fileno()),
                "--",
                sys.executable,
                "-I",
                "-c",
                "import os,time;print(os.getpid(),flush=True);time.sleep(5)",
            ],
            stdout=out,
            stderr=err,
            start_new_session=True,
            pass_fds=(child.fileno(),),
        )
        child.close()
        try:
            end = time.monotonic() + 5
            while not stdout.stat().st_size:
                assert time.monotonic() < end
                time.sleep(0.01)
            control.close()  # Same EOF the supervisor sees when its owner dies.
            process.wait(timeout=5)
            assert process.returncode == -9
            assert eventually_stopped(int(stdout.read_text().strip()))
        finally:
            if process.returncode is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)


@pytest.mark.parametrize("boundary", ["running", "child_close"])
def test_actual_sigterm_runs_check_cleanup_retention_and_handler_restore(tmp_path, boundary):
    root = tmp_path.resolve()
    (root / "docs/research").mkdir(parents=True)
    (root / "dist").mkdir()
    (root / "wheels").mkdir()
    (root / "wheels/package.whl").write_bytes(b"synthetic unused artifact")
    supervisor = root / "tests/fixtures/upload_supervisor.py"
    supervisor.parent.mkdir(parents=True)
    supervisor.write_bytes((ROOT / "tests/fixtures/upload_supervisor.py").read_bytes())
    (root / "environment.json").write_text(
        json.dumps({"source_sha": "a" * 40, "cpu": "synthetic", "disk_type": "unknown"})
    )
    code = """
import json,os,runpy,signal,socket,subprocess,sys,time
from pathlib import Path
from types import SimpleNamespace
helper=runpy.run_path(sys.argv[1]); root=Path(sys.argv[2])
namespace=helper['check'].__globals__; namespace['ROOT']=root
subprocess.run=lambda *args,**kwargs: SimpleNamespace(stdout='a'*40)
execute=namespace['execute']; previous=signal.getsignal(signal.SIGTERM)
namespace['execute']=lambda command,out,err: execute([sys.executable,'-I','-c',
    'import os,time;print(os.getpid(),flush=True);time.sleep(5)'],out,err)
if sys.argv[3] == 'child_close':
    pair=socket.socketpair
    class Child:
        def __init__(self,inner): self.inner,self.first=inner,True
        def fileno(self): return self.inner.fileno()
        def __enter__(self): return self
        def __exit__(self,*args): self.inner.close()
        def close(self):
            self.inner.close()
            if self.first:
                self.first=False
                end=time.monotonic()+5
                marker=root/'upload-check-controller-stdout.txt'
                while not marker.exists() or not marker.stat().st_size:
                    if time.monotonic()>=end: raise RuntimeError('fixture not ready')
                    time.sleep(0.01)
                os.kill(os.getpid(),signal.SIGTERM)
    def socketpair():
        control,child=pair()
        return control,Child(child)
    socket.socketpair=socketpair
args=SimpleNamespace(environment=root/'environment.json',wheel_dir=root/'wheels',
    python=Path(sys.executable),workspace=root/'upload-check',output=root/'dist/upload.json',
    run_url='https://github.com/HodeTech/Yorunge/actions/runs/123')
try:
    helper['check'](args)
except SystemExit:
    (root/'restored.json').write_text(json.dumps({'restored':signal.getsignal(signal.SIGTERM)==previous}))
    raise
"""
    process = subprocess.Popen(
        [sys.executable, "-I", "-c", code, str(ROOT / "scripts/upload_ci.py"), str(root), boundary],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        end = time.monotonic() + 10
        marker = root / "upload-check-controller-stdout.txt"
        while not marker.exists() or not marker.stat().st_size:
            assert process.poll() is None
            assert time.monotonic() < end
            time.sleep(0.01)
        if boundary == "running":
            process.send_signal(signal.SIGTERM)
        output, error = process.communicate(timeout=10)
        assert process.returncode == 143
        assert not output
        assert not error
        assert json.loads((root / "restored.json").read_bytes()) == {"restored": True}
        assert eventually_stopped(int(marker.read_text().strip()))
        checks = runpy.run_path(str(ROOT / "scripts/research_evidence.py"))
        assert checks["verify"](root) == 1
        assert checks["catalog"](root / "docs/research")[0]["summary"]["accepted"] is False
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)


def test_real_controller_nonzero_preserves_non_utf8_and_stderr(tmp_path, helper):
    stdout, stderr = tmp_path / "stdout", tmp_path / "stderr"
    command = [
        sys.executable,
        "-I",
        "-c",
        "import os;os.write(1,b'\\xffbad');os.write(2,b'failure');raise SystemExit(7)",
    ]
    assert helper["execute"](command, stdout, stderr) == 7
    assert stdout.read_bytes() == b"\xffbad"
    assert stderr.read_bytes() == b"failure"


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
def test_malformed_controller_output_stays_private_and_is_never_accepted(
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
    assert not any((root / "docs/research").iterdir())


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
