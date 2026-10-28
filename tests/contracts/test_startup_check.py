"""Offline safety and failure propagation of the isolated startup orchestrator."""

import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check-startup.py"


def test_runtime_environment_removes_ambient_python_options_without_mutating_parent(monkeypatch):
    monkeypatch.setenv("PYTHONPATH", "untrusted-source")
    monkeypatch.setenv("PYTHONOPTIMIZE", "2")
    monkeypatch.setenv("PYTHONPYCACHEPREFIX", "elsewhere")
    monkeypatch.setenv("VIRTUAL_ENV", "development")
    helpers = runpy.run_path(str(SCRIPT))
    env = helpers["environment"]()
    assert env["PYTHONHASHSEED"] == "0"
    assert env["PYTHONNOUSERSITE"] == "1"
    for key in ("PYTHONPATH", "PYTHONOPTIMIZE", "PYTHONPYCACHEPREFIX", "VIRTUAL_ENV"):
        assert key not in env
    assert os.environ["PYTHONPATH"] == "untrusted-source"
    assert os.environ["PYTHONOPTIMIZE"] == "2"


def test_existing_evidence_and_workspaces_are_not_overwritten(tmp_path):
    helpers = runpy.run_path(str(SCRIPT))
    output = tmp_path / "existing.json"
    output.write_text("previous evidence")
    work = tmp_path / "workspace"
    uv = Path("unused")
    with pytest.raises(ValueError, match="previous evidence"):
        helpers["check"](ROOT, None, work, output, uv, cpu=None, disk="unknown")
    assert output.read_text() == "previous evidence"
    assert not work.exists()
    work.mkdir()
    marker = work / "user-data"
    marker.write_text("preserved")
    new_output = tmp_path / "new.json"
    with pytest.raises(FileExistsError):
        helpers["check"](ROOT, None, work, new_output, uv, cpu=None, disk="unknown")
    assert marker.read_text() == "preserved"
    assert not new_output.exists()


def test_missing_baseline_is_not_silently_treated_as_an_initial_release(tmp_path):
    helpers = runpy.run_path(str(SCRIPT))
    baseline, work, output = tmp_path / "missing", tmp_path / "work", tmp_path / "out"
    uv = Path("unused")
    with pytest.raises(ValueError, match="baseline checkout is missing"):
        helpers["check"](ROOT, baseline, work, output, uv, cpu=None, disk="unknown")
    assert not work.exists()


def test_process_failure_is_propagated(tmp_path):
    helpers = runpy.run_path(str(SCRIPT))
    command = [sys.executable, "-c", "raise SystemExit(7)"]
    with pytest.raises(subprocess.CalledProcessError) as error:
        helpers["run"](command, cwd=tmp_path)
    assert error.value.returncode == 7


@pytest.mark.parametrize("changed,measured_code", [(False, 0), (False, 1), (True, 0)])
def test_source_changes_and_absolute_budget_failures_cannot_become_success(
    tmp_path, monkeypatch, changed, measured_code
):
    helpers = runpy.run_path(str(SCRIPT))
    check = helpers["check"]
    work, output = tmp_path / "workspace", tmp_path / "report.json"
    samples = iter(
        [
            {"commit": "base", "source_sha256": {"src/a.py": "before"}},
            {"commit": "base", "source_sha256": {"src/a.py": "after" if changed else "before"}},
        ]
    )
    monkeypatch.setitem(check.__globals__, "source", lambda project: next(samples))
    prepared = helpers["Prepared"](ROOT, Path(sys.executable), Path("unused"), "a" * 64, {})
    monkeypatch.setitem(check.__globals__, "prepare", lambda *args: prepared)
    monkeypatch.setitem(check.__globals__, "seed", lambda *args: None)

    def measure(command, *, cwd, accepted=(0,)):
        (work / "measurement.json").write_text(json.dumps({"schema_version": 2}))
        return subprocess.CompletedProcess(command, measured_code, "", "")

    monkeypatch.setitem(check.__globals__, "run", measure)
    result = check(ROOT, None, work, output, Path("unused"), cpu=None, disk="unknown")
    assert result == (1 if changed else measured_code)
    value = json.loads(output.read_text())
    assert value["provenance"]["source_unchanged_during_measurement"] is (not changed)
    assert value["provenance"]["baseline_status"] == "not_requested"


def test_source_snapshot_does_not_attribute_an_archive_to_its_enclosing_repository(tmp_path):
    helpers = runpy.run_path(str(SCRIPT))
    parent = tmp_path / "parent"
    subprocess.run(["git", "init", "-q", str(parent)], check=True, capture_output=True)
    archive = parent / "archive"
    archive.mkdir()
    # git can discover the enclosing checkout; it is not the archive's source revision.
    assert helpers["revision"](archive) is None
