"""Actual download controller lifecycle, retained logs and current-run CI binding."""

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

from tests.contracts.test_download_evidence import build

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.usefixtures("evidence_publication_context")


@pytest.fixture(scope="module")
def helper():
    return runpy.run_path(str(ROOT / "scripts/download_ci.py"))


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
                marker=root/'download-check-controller-stdout.txt'
                while not marker.exists() or not marker.stat().st_size:
                    if time.monotonic()>=end: raise RuntimeError('fixture not ready')
                    time.sleep(0.01)
                os.kill(os.getpid(),signal.SIGTERM)
    def socketpair():
        control,child=pair()
        return control,Child(child)
    socket.socketpair=socketpair
args=SimpleNamespace(environment=root/'environment.json',wheel_dir=root/'wheels',
    python=Path(sys.executable),workspace=root/'download-check',output=root/'dist/download.json',
    run_url='https://github.com/HodeTech/Yorunge/actions/runs/123')
try:
    helper['check'](args)
except SystemExit:
    (root/'restored.json').write_text(json.dumps({'restored':signal.getsignal(signal.SIGTERM)==previous}))
    raise
"""
    process = subprocess.Popen(
        [
            sys.executable,
            "-I",
            "-c",
            code,
            str(ROOT / "scripts/download_ci.py"),
            str(root),
            boundary,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        end = time.monotonic() + 10
        marker = root / "download-check-controller-stdout.txt"
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
        stderr.write_bytes(b"x" * (helper["DIAGNOSTIC"]["MAX_FILE"] + 1))
    elif damage == "symlink":
        stderr.symlink_to(stdout)
    with pytest.raises(ValueError):
        helper["copy_logs"](workspace, stdout, stderr)
    assert not (workspace / "stdout.json").exists()
    assert stdout.read_bytes() == b"original"


@pytest.mark.parametrize(
    "exit_code,reason", [(0, "regular evidence file"), (7, "controller failed")]
)
def test_malformed_controller_output_stays_private_and_is_never_accepted(
    tmp_path, helper, monkeypatch, exit_code, reason
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
        workspace=root / "download-check",
        output=root / "dist/download.json",
        run_url="https://github.com/HodeTech/Yorunge/actions/runs/123",
    )
    with pytest.raises(ValueError) as caught:
        helper["check"](args)
    # Retaining unscannable bytes may itself fail: the original failure is then further back.
    messages, error = [], caught.value
    while error is not None:
        messages.append(str(error))
        error = error.__context__
    assert any(reason in message for message in messages), messages
    assert not args.output.exists()
    assert (args.workspace / "stdout.json").read_bytes() == b"\xffpartial controller"
    diagnostic = namespace["CHECKS"]["decode"](
        (root / "dist/download-ci-rejected.json").read_bytes()
    )
    assert namespace["DIAGNOSTIC"]["summarize"](diagnostic)["accepted"] is False
    assert not any((root / "docs/research").iterdir())


def accepted_report():
    """A synthetic accepted twelve-run report, and the compatibility cell it was produced in."""
    evidence = runpy.run_path(str(ROOT / "scripts/download_evidence.py"))
    report = build(evidence)
    runtime = report["runs"][0]["client"]["runtime"]
    environment = {
        **report["environment"],
        "source_sha": report["source_commit"],
        "platform": runtime["os"],
        "python": runtime["python"],
        "sqlite": runtime["sqlite"],
        "architecture": runtime["machine"],
    }
    return evidence, report, environment


def validated(monkeypatch, tmp_path, helper, report, environment, current=None, locked=None):
    namespace = helper["validate_output"].__globals__
    evidence = namespace["DRIVER"]["EVIDENCE"]
    current = current or copy.deepcopy(report["provenance"]["source_before"])
    locked = locked or copy.deepcopy(report["provenance"]["locked_runtime"])
    monkeypatch.setitem(evidence, "source", lambda root: current)
    monkeypatch.setitem(namespace["DRIVER"]["STREAM"], "locked_runtime", lambda root: locked)
    output = tmp_path / "download.json"
    output.write_bytes(namespace["CHECKS"]["encode"](report))
    helper["validate_output"](output, tmp_path, environment)


def test_an_accepted_report_of_this_checkout_and_cell_is_the_only_one_that_validates(
    tmp_path, helper, monkeypatch
):
    _, report, environment = accepted_report()
    validated(monkeypatch, tmp_path, helper, report, environment)


@pytest.mark.parametrize(
    "damage",
    ["source", "vector", "measurement", "lock", "commit", "cpu", "disk", "os", "python", "sqlite"]
    + ["machine"],
)
def test_native_output_matches_actual_checkout_lock_and_compatibility_cell(
    tmp_path, helper, monkeypatch, damage
):
    evidence, report, environment = accepted_report()
    current = copy.deepcopy(report["provenance"]["source_before"])
    locked = copy.deepcopy(report["provenance"]["locked_runtime"])
    if damage in {"source", "vector", "measurement"}:
        key = {
            "source": "src/yorunge/__init__.py",
            "vector": evidence["UPLOAD_VECTOR"],
            "measurement": "scripts/benchmark-download.py",
        }[damage]
        current["source_sha256"][key] = "9" * 64
    elif damage == "lock":
        locked["httpx"] = "0.28.2"
    elif damage == "commit":
        environment["source_sha"] = "b" * 40
    elif damage in {"cpu", "disk"}:
        environment["cpu" if damage == "cpu" else "disk_type"] = "different"
    else:
        environment[{"os": "platform", "machine": "architecture"}.get(damage, damage)] = "other"
    with pytest.raises(ValueError):
        validated(monkeypatch, tmp_path, helper, report, environment, current, locked)


def test_a_passing_smoke_subset_is_not_acceptance(tmp_path, helper, monkeypatch):
    evidence, _, _ = accepted_report()
    report = build(evidence, labels=("16", "256", "1024", "resume"), samples=2)
    runtime = report["runs"][0]["client"]["runtime"]
    environment = {
        **report["environment"],
        "source_sha": report["source_commit"],
        "platform": runtime["os"],
        "python": runtime["python"],
        "sqlite": runtime["sqlite"],
        "architecture": runtime["machine"],
    }
    summary = evidence["summarize_report"](report)
    assert summary["passed"] is True and summary["partial"] is True
    assert summary["accepted"] is False
    with pytest.raises(ValueError, match="not accepted"):
        validated(monkeypatch, tmp_path, helper, report, environment)


def test_a_valid_report_that_failed_a_rule_is_not_acceptance(tmp_path, helper, monkeypatch):
    evidence, report, environment = accepted_report()
    report["runs"][0]["client"]["elapsed_seconds"] = 901.0
    report["runs"][0]["passed"] = False
    report["passed"] = report["accepted"] = False
    summary = evidence["summarize_report"](report)
    assert summary["passed"] is False and summary["accepted"] is False
    with pytest.raises(ValueError, match="not accepted"):
        validated(monkeypatch, tmp_path, helper, report, environment)


def test_a_report_that_contradicts_itself_is_refused_before_any_comparison(
    tmp_path, helper, monkeypatch
):
    _, report, environment = accepted_report()
    report["accepted"] = True
    report["runs"][0]["passed"] = False  # flags that disagree with the recomputed verdicts
    with pytest.raises(ValueError):
        validated(monkeypatch, tmp_path, helper, report, environment)


def test_the_controller_command_names_the_run_the_single_wheel_and_the_cell(tmp_path, helper):
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    (wheels / "yorunge-1-py3-none-any.whl").write_bytes(b"unused")
    args = SimpleNamespace(
        python=tmp_path / "env/bin/python",
        wheel_dir=wheels,
        workspace=tmp_path / "download-check",
        output=tmp_path / "download.json",
        run_url="https://github.com/HodeTech/Yorunge/actions/runs/123",
    )
    command = helper["arguments"](args, {"cpu": "synthetic cpu", "disk_type": "synthetic ssd"})
    assert command[:2] == [sys.executable, str(ROOT / "scripts/benchmark-download.py")]
    options = dict(zip(command[2::2], command[3::2], strict=True))
    assert options == {
        "--python": str(tmp_path / "env/bin/python"),
        "--wheel": str(wheels / "yorunge-1-py3-none-any.whl"),
        "--workspace": str(tmp_path / "download-check"),
        "--output": str(tmp_path / "download.json"),
        "--cpu": "synthetic cpu",
        "--disk-type": "synthetic ssd",
        "--run-url": "https://github.com/HodeTech/Yorunge/actions/runs/123",
    }
    # The controller is the full twelve-run measurement: no smoke subset can be requested here.
    assert "--labels" not in command and "--samples" not in command


@pytest.mark.parametrize("count", [0, 2])
def test_the_candidate_wheel_must_be_exactly_one(tmp_path, helper, count):
    for index in range(count):
        (tmp_path / f"yorunge-{index}-py3-none-any.whl").write_bytes(b"unused")
    args = SimpleNamespace(wheel_dir=tmp_path)
    with pytest.raises(ValueError, match="single installed candidate wheel"):
        helper["arguments"](args, {"cpu": "c", "disk_type": "d"})


def test_the_run_url_is_checked_before_anything_is_read_or_started(tmp_path, helper):
    args = SimpleNamespace(
        environment=tmp_path / "missing.json",
        run_url="https://example.invalid/actions/runs/1",
    )
    with pytest.raises(ValueError) as caught:
        helper["check"](args)
    assert "regular evidence file" not in str(caught.value)  # the environment was not read
    assert not (tmp_path / "download-check").exists()


def test_an_environment_of_another_checkout_stops_everything_before_the_controller(
    tmp_path, helper, monkeypatch
):
    namespace = helper["check"].__globals__
    monkeypatch.setitem(namespace, "ROOT", tmp_path)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout="a" * 40))

    def forbidden(*arguments):
        raise AssertionError("the controller must not start")

    monkeypatch.setitem(namespace, "execute", forbidden)
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    (wheels / "package.whl").write_bytes(b"unused")
    environment = tmp_path / "ci.json"
    environment.write_text(
        json.dumps({"source_sha": "b" * 40, "cpu": "synthetic", "disk_type": "unknown"})
    )
    args = SimpleNamespace(
        environment=environment,
        wheel_dir=wheels,
        python=tmp_path / "python",
        workspace=tmp_path / "download-check",
        output=tmp_path / "dist/download.json",
        run_url="https://github.com/HodeTech/Yorunge/actions/runs/123",
    )
    with pytest.raises(ValueError, match="differs from checkout"):
        helper["check"](args)
    assert not (tmp_path / "download-check").exists()


def test_a_platform_without_the_native_measurement_is_refused_first(tmp_path, helper, monkeypatch):
    namespace = helper["check"].__globals__
    monkeypatch.setitem(namespace, "sys", SimpleNamespace(platform="win32"))
    args = SimpleNamespace(
        environment=tmp_path / "missing.json",
        run_url="https://github.com/HodeTech/Yorunge/actions/runs/123",
    )
    with pytest.raises(ValueError, match="requires Linux or macOS"):
        helper["check"](args)
