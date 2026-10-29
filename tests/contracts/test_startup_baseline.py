"""Initial-release controls must never disguise a missing or modified runtime baseline."""

import argparse
import copy
import hashlib
import json
import runpy
import subprocess
from pathlib import Path

import pytest

from tests.contracts.test_startup_diagnostic import linux_report

ROOT = Path(__file__).resolve().parents[2]
BASELINE = runpy.run_path(str(ROOT / "scripts/startup_baseline.py"))
DIAGNOSTIC = runpy.run_path(str(ROOT / "scripts/startup_diagnostic.py"))


@pytest.fixture
def documentation_base(tmp_path):
    baseline = tmp_path / "documentation-base"
    baseline.mkdir()
    (baseline / "README.md").write_text("Initial documentation\n")
    for command in (
        ["git", "init", "--quiet"],
        ["git", "add", "README.md"],
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.test",
            "commit",
            "--quiet",
            "-m",
            "Initial documentation",
        ],
    ):
        subprocess.run(command, cwd=baseline, check=True, capture_output=True, timeout=5)
    return baseline


def test_first_runtime_control_records_real_pinned_base_and_same_source_runtime(documentation_base):
    effective, value = BASELINE["select"](ROOT, documentation_base)
    assert effective == ROOT
    assert value["mode"] == "initial_runtime_same_source_control"
    assert value["effective_baseline_commit"] == value["source_commit"]
    pinned = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=documentation_base, text=True, timeout=5
    ).strip()
    assert value["pinned_baseline_commit"] == pinned
    assert BASELINE["summarize"](value)["complete"] is False
    assert BASELINE["CHECKS"]["summarize"](value)["diagnostic_only"] is True


def test_normal_runtime_baseline_never_uses_initial_control():
    effective, value = BASELINE["select"](ROOT, ROOT)
    assert effective == ROOT
    assert value["mode"] == "pinned_runtime"
    assert value["effective_baseline_commit"] == value["pinned_baseline_commit"]


@pytest.mark.parametrize("damage", ["missing", "nested", "symlink", "dirty", "runtime", "deleted"])
def test_invalid_or_changed_checkout_cannot_become_same_source_control(
    documentation_base, tmp_path, damage
):
    baseline = documentation_base
    if damage == "missing":
        baseline = tmp_path / "missing"
    elif damage == "nested":
        baseline = documentation_base / "nested"
        baseline.mkdir()
    elif damage == "symlink":
        baseline = tmp_path / "linked-base"
        baseline.symlink_to(documentation_base)
    elif damage == "dirty":
        (baseline / "README.md").write_text("Modified documentation")
    else:
        (baseline / "pyproject.toml").write_text("[project]\nname='fixture'\n")
        if damage == "runtime":
            (baseline / "pyproject.toml").unlink()
            (baseline / "src").mkdir()
        else:
            subprocess.run(["git", "add", "pyproject.toml"], cwd=baseline, check=True, timeout=5)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Fixture",
                    "-c",
                    "user.email=fixture@example.test",
                    "commit",
                    "--quiet",
                    "-m",
                    "Runtime project",
                ],
                cwd=baseline,
                check=True,
                timeout=5,
            )
            (baseline / "pyproject.toml").unlink()
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        BASELINE["select"](ROOT, baseline)


@pytest.mark.parametrize("damage", ["version", "mode", "effective", "pinned", "extra", "hash"])
def test_selection_has_closed_types_hashes_and_mode_semantics(documentation_base, damage):
    _, value = BASELINE["select"](ROOT, documentation_base)
    if damage == "version":
        value["schema_version"] = True
    elif damage == "mode":
        value["mode"] = "fallback"
    elif damage == "effective":
        value["effective_baseline_commit"] = "f" * 40
    elif damage == "pinned":
        value["pinned_baseline_commit"] = value["source_commit"]
    elif damage == "extra":
        value["unknown"] = True
    else:
        value["report_sha256"] = "bad"
    with pytest.raises(ValueError):
        BASELINE["summarize"](value)


@pytest.fixture
def initial_report(documentation_base, monkeypatch):
    report = linux_report()
    source = report["snapshots"]["before"]["baseline"]["source"]
    for startup in (DIAGNOSTIC["STARTUP"], DIAGNOSTIC["BASELINE"]["STARTUP"]):
        monkeypatch.setitem(startup, "source", lambda root: copy.deepcopy(source))
        monkeypatch.setitem(startup, "current_sources", lambda *args: None)
        monkeypatch.setitem(
            startup["JOBS"], "locked_runtime", lambda root: {"yorunge": "0.1.0.dev0"}
        )
    return report


def test_initial_control_forwards_effective_checkout_and_displays_selection(
    documentation_base, initial_report, tmp_path, monkeypatch, capsys
):
    report, receipt = tmp_path / "startup.json", tmp_path / "receipt.json"
    summary, outputs = tmp_path / "summary", tmp_path / "outputs"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("GITHUB_OUTPUT", str(outputs))

    def producer(project, baseline, *args, **kwargs):
        assert project == ROOT
        assert baseline == ROOT
        report.write_text(json.dumps(initial_report, indent=2))
        return 1

    original = runpy.run_path
    monkeypatch.setattr(
        runpy,
        "run_path",
        lambda path: (
            {"check": producer}
            if str(path).endswith("check-startup-evidence.py")
            else original(path)
        ),
    )
    args = argparse.Namespace(
        receipt=receipt,
        report=report,
        baseline_project=documentation_base,
        workspace=tmp_path / "workspace",
        uv=Path("unused"),
        run_url="https://github.com/HodeTech/Yorunge/actions/runs/123",
    )
    assert DIAGNOSTIC["run"](args) == 0
    assert (
        DIAGNOSTIC["verify_files"](ROOT, documentation_base, report, receipt)["outcome"]
        == "diagnostic_budget_exceeded"
    )
    text = summary.read_text()
    assert "initial_runtime_same_source_control" in text
    assert "does not measure improvement" in text
    assert "baseline_mode=initial_runtime_same_source_control" in outputs.read_text()
    assert "::warning" in capsys.readouterr().out
    selection_path = tmp_path / "startup-baseline-selection.json"
    selection = json.loads(selection_path.read_text())
    assert selection["report_sha256"] == hashlib.sha256(report.read_bytes()).hexdigest()
    selection["pinned_baseline_commit"] = "b" * 40
    selection_path.write_text(json.dumps(selection))
    with pytest.raises(ValueError, match="pinned checkout"):
        DIAGNOSTIC["verify_files"](ROOT, documentation_base, report, receipt)
    selection_path.unlink()
    with pytest.raises(ValueError, match="regular evidence"):
        DIAGNOSTIC["verify_files"](ROOT, documentation_base, report, receipt)


def test_initial_control_does_not_relax_raw_source_validation(documentation_base, initial_report):
    initial_report["snapshots"]["before"]["baseline"]["source"]["commit"] = "f" * 40
    with pytest.raises(ValueError):
        DIAGNOSTIC["classify"](ROOT, documentation_base, initial_report, 1)
