"""What round one found nobody pinning in scripts/download_ci.py: the process contract."""

import runpy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FLAGS = {
    "--python": ".local/startup-check/candidate/env/bin/python",
    "--wheel-dir": ".local/startup-check/candidate/dist",
    "--workspace": ".local/download-check",
    "--output": "dist/download.json",
    "--environment": "dist/ci-environment.json",
    "--run-url": "https://github.com/HodeTech/Yorunge/actions/runs/123",
}


@pytest.fixture(scope="module")
def helper():
    return runpy.run_path(str(ROOT / "scripts/download_ci.py"))


def argv(skip=None):
    line = ["download_ci.py"]
    for flag, value in FLAGS.items():
        if flag != skip:
            line += [flag, value]
    return line


def test_gap_main_parses_exactly_the_workflows_command_line(helper, monkeypatch):
    seen = {}
    monkeypatch.setitem(
        helper["main"].__globals__, "check", lambda args: seen.update(vars(args)) or 0
    )
    monkeypatch.setattr(sys, "argv", argv())
    assert helper["main"]() == 0
    assert set(seen) == {"python", "wheel_dir", "workspace", "output", "environment", "run_url"}
    assert all(isinstance(seen[key], Path) for key in seen if key != "run_url")
    assert seen["run_url"] == FLAGS["--run-url"]


@pytest.mark.parametrize("flag", list(FLAGS))
def test_gap_every_flag_of_the_workflow_command_is_required(helper, monkeypatch, flag):
    monkeypatch.setitem(helper["main"].__globals__, "check", lambda args: 0)
    monkeypatch.setattr(sys, "argv", argv(skip=flag))
    with pytest.raises(SystemExit) as stopped:
        helper["main"]()
    assert stopped.value.code == 2


def test_gap_logs_are_never_copied_through_a_symlinked_workspace(tmp_path, helper):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    out, err = tmp_path / "out.txt", tmp_path / "err.txt"
    out.write_bytes(b"{}\n")
    err.write_bytes(b"")
    with pytest.raises(ValueError):
        helper["copy_logs"](link, out, err)
    assert list(real.iterdir()) == []
    # and through a symlinked ancestor
    holder = tmp_path / "holder"
    holder.symlink_to(real)
    (real / "workspace").mkdir()
    with pytest.raises(ValueError):
        helper["copy_logs"](holder / "workspace", out, err)
    assert list((real / "workspace").iterdir()) == []


def test_gap_a_failed_check_exits_one_with_the_closed_message(helper, monkeypatch, capsys):
    def boom(args):
        raise ValueError("synthetic controller failure")

    monkeypatch.setitem(helper["main"].__globals__, "check", boom)
    monkeypatch.setattr(sys, "argv", argv())
    with pytest.raises(SystemExit) as stopped:
        helper["main"]()
    assert stopped.value.code == 1
    assert (
        "Download CI failed: synthetic controller failure; retained files are not acceptance"
        in (capsys.readouterr().err)
    )


def test_gap_the_script_as_a_process_fails_red_when_the_environment_file_is_missing(tmp_path):
    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(ROOT / "scripts/download_ci.py"),
            "--python",
            "x",
            "--wheel-dir",
            str(tmp_path),
            "--workspace",
            str(tmp_path / "w"),
            "--output",
            str(tmp_path / "o.json"),
            "--environment",
            str(tmp_path / "missing.json"),
            "--run-url",
            "https://github.com/HodeTech/Yorunge/actions/runs/1",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 1
    assert "Download CI failed" in result.stderr and "Traceback" not in result.stderr
