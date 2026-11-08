"""Reviewer B (R2): survivors of a systematic mutation run of scripts/download_ci.py."""

import json
import os
import runpy
import signal
import socket
import stat
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
URL = "https://github.com/HodeTech/Yorunge/actions/runs/123"


@pytest.fixture(scope="module")
def helper():
    return runpy.run_path(str(ROOT / "scripts/download_ci.py"))


# --- the supervisor's status line


def status_pair():
    control, child = socket.socketpair()
    return control, child


@pytest.mark.parametrize(
    ("sent", "code"),
    [(b"0\n", 0), (b"7\n", 7), (b"-9\n", -9), (b"255\n", 255), (b"-128\n", -128), (b"143\n", 143)],
)
def test_a_valid_status_line_is_the_exit_code(helper, sent, code):
    control, child = status_pair()
    with control, child:
        child.sendall(sent)
        assert helper["wait_status"](control, ["x"]) == code  # mutants L89 (<= / bounds)


@pytest.mark.parametrize(
    ("sent", "message"),
    [
        (b"256\n", "invalid download controller exit code"),
        (b"999\n", "invalid download controller exit code"),
        (b"-129\n", "invalid download controller exit code"),
        (b"abc\n", "invalid download supervisor status"),
        (b"1 2\n", "invalid download supervisor status"),
        (b"\n", "invalid download supervisor status"),
        (b"12345\n", "invalid download supervisor status"),
        (b"x" * 40, "status exceeded bound"),
        (b"x" * 32, "status exceeded bound"),
        (b"", "closed before controller status"),
    ],
)
def test_a_damaged_status_line_is_a_closed_failure_with_its_own_message(helper, sent, message):
    control, child = status_pair()
    with control, child:
        if sent:
            child.sendall(sent)
        child.shutdown(socket.SHUT_WR)  # the supervisor is gone: EOF after what it said
        with pytest.raises(ValueError, match=message):  # mutants L81-L90
            helper["wait_status"](control, ["x"])


def test_a_silent_supervisor_times_out_with_the_command_and_the_bound(helper, monkeypatch):
    control, child = status_pair()
    monkeypatch.setitem(helper["wait_status"].__globals__, "SCHEDULING_SECONDS", 0.3)
    with control, child:
        with pytest.raises(subprocess.TimeoutExpired) as raised:
            helper["wait_status"](control, ["controller", "--flag"])
    assert raised.value.cmd == ["controller", "--flag"]
    assert raised.value.timeout == 0.3  # mutant L76


# --- the success path of check()


def arguments(root):
    wheels = root / "wheels"
    wheels.mkdir()
    (wheels / "package.whl").write_bytes(b"unused")
    environment = root / "ci.json"
    environment.write_text(
        json.dumps({"source_sha": "a" * 40, "cpu": "synthetic", "disk_type": "unknown"})
    )
    return SimpleNamespace(
        environment=environment,
        wheel_dir=wheels,
        python=root / "python",
        workspace=root / "download-check",
        output=root / "dist/download.json",
        run_url=URL,
    )


def test_a_controller_that_ends_zero_and_validates_is_a_green_step_with_its_logs_kept(
    tmp_path, helper, monkeypatch, capsys
):
    # mutants of _check: validate_output arguments swapped (L235), the first copy_logs deleted
    # (L232), the closing message deleted (L247), the success value (L248)
    root = tmp_path.resolve()
    (root / "dist").mkdir()
    namespace = helper["check"].__globals__
    monkeypatch.setitem(namespace, "ROOT", root)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="a" * 40))
    args = arguments(root)
    calls = []

    def execute(command, stdout, stderr):
        stdout.write_bytes(b'{"kind":"download-budget"}\n')
        stderr.write_bytes(b"")
        return 0

    monkeypatch.setitem(namespace, "execute", execute)
    monkeypatch.setitem(namespace, "validate_output", lambda *a: calls.append(a))
    assert helper["check"](args) == 0
    assert calls == [(args.output, root, json.loads(args.environment.read_text()))]
    assert "Validated twelve native download processes" in capsys.readouterr().out
    assert (args.workspace / "stdout.json").read_bytes() == b'{"kind":"download-budget"}\n'
    assert (args.workspace / "stderr.txt").read_bytes() == b""
    assert not list((root / "dist").iterdir())  # nothing rejected, nothing archived
    assert stat.S_IMODE(args.workspace.stat().st_mode) == 0o700  # mutant L131 (the mkdir mode)


def test_a_supervisor_that_cannot_start_leaves_the_cause_not_an_attribute_error(
    tmp_path, helper, monkeypatch
):
    # mutant L125 (`if process is not None` forced True)
    namespace = helper["owned_controller"].__globals__

    def refuse(*a, **k):
        raise OSError("synthetic: cannot start")

    monkeypatch.setattr(namespace["subprocess"], "Popen", refuse)
    control, child = socket.socketpair()
    with control, child, (tmp_path / "o").open("xb") as out, (tmp_path / "e").open("xb") as err:
        with pytest.raises(OSError, match="cannot start"):
            helper["owned_controller"](["x"], control, child, out, err)


# --- the SIGTERM context manager


def test_the_context_manager_nests_reuses_and_resets_its_depth(helper):
    names = helper["stop_group"].__globals__
    before = signal.getsignal(signal.SIGTERM)
    with helper["termination_signals"]():
        outer = signal.getsignal(signal.SIGTERM)
        assert callable(outer)
        assert outer != before
        assert names["_termination_depth"] == 1
        with helper["termination_signals"]():
            assert signal.getsignal(signal.SIGTERM) == outer
            assert names["_termination_depth"] == 2
        assert signal.getsignal(signal.SIGTERM) == outer
        assert names["_termination_depth"] == 1
    assert signal.getsignal(signal.SIGTERM) == before
    assert names["_termination_depth"] == 0
    with helper["termination_signals"]():  # a second, sequential use installs the handler again
        assert callable(signal.getsignal(signal.SIGTERM))
        assert names["_termination_depth"] == 1
    assert names["_termination_depth"] == 0  # mutants L37-L45


def test_a_second_sigterm_during_the_cleanup_is_ignored(helper):
    before = signal.getsignal(signal.SIGTERM)
    seen = {}
    with pytest.raises(SystemExit) as stopped:
        with helper["termination_signals"]():
            try:
                os.kill(os.getpid(), signal.SIGTERM)
                time.sleep(1)
            except SystemExit:
                seen["during"] = signal.getsignal(signal.SIGTERM)
                raise
    assert stopped.value.code == 128 + signal.SIGTERM
    assert seen["during"] == signal.SIG_IGN  # L34
    assert signal.getsignal(signal.SIGTERM) == before


# --- main(): every closed failure type


FLAGS = [
    "download_ci.py",
    "--python",
    "p",
    "--wheel-dir",
    "w",
    "--workspace",
    "x",
    "--output",
    "o",
    "--environment",
    "e",
    "--run-url",
    URL,
]


@pytest.mark.parametrize(
    "error",
    [
        OSError("os"),
        ValueError("value"),
        KeyError("key"),
        TypeError("type"),
        RecursionError("deep"),
        subprocess.TimeoutExpired("git", 1),
    ],
    ids=lambda error: type(error).__name__,
)
def test_every_closed_failure_type_ends_with_exit_one_and_no_traceback(
    helper, monkeypatch, capsys, error
):
    # mutants L262: one exception type dropped from the tuple
    def check(args):
        raise error

    monkeypatch.setitem(helper["main"].__globals__, "check", check)
    monkeypatch.setattr(sys, "argv", FLAGS)
    with pytest.raises(SystemExit) as stopped:
        helper["main"]()
    assert stopped.value.code == 1
    assert "Download CI failed" in capsys.readouterr().err
