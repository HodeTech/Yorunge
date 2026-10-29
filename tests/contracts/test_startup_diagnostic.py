"""Only a valid Linux budget overrun may keep the remaining mandatory gates running."""

import argparse
import copy
import hashlib
import json
import runpy
from pathlib import Path

import pytest

from tests.fixtures.startup_receipt import receipt

ROOT = Path(__file__).resolve().parents[2]
HELPERS = runpy.run_path(str(ROOT / "scripts/startup_diagnostic.py"))


def linux_report(*, passed=False):
    report = receipt()
    raw = report["measurement"]
    raw.update(platform="Linux-7.0-arm64", cpu="synthetic Linux host", disk_type="unknown")
    for point in ("before", "after"):
        for side in ("candidate", "baseline"):
            report["snapshots"][point][side]["installed"]["platform"] = raw["platform"]
    if not passed:
        raw["measurements"]["cache"].update(
            warm_samples_ms=[2000.0] * 30, warm_median_ms=2000.0, warm_p95_ms=2000.0, passed=False
        )
        raw["comparison"]["paired_comparisons"]["cache"].update(
            paired_wall_ratios=[200.0] * 30, median_paired_wall_ratio=200.0
        )
        report["output_checks"]["candidate"]["cache"]["wall_ms"][4:] = [2000.0] * 30
        report.update(measurement_exit=1, passed=False)
    return report


@pytest.fixture
def pinned_inputs(monkeypatch):
    report = linux_report()
    startup = HELPERS["STARTUP"]
    # Pure classification fixture: real complete-current-map rejection is tested separately.
    monkeypatch.setitem(startup, "current_sources", lambda *args: None)
    monkeypatch.setitem(
        startup,
        "source",
        lambda root: copy.deepcopy(report["snapshots"]["before"]["baseline"]["source"]),
    )
    monkeypatch.setitem(startup["JOBS"], "locked_runtime", lambda root: {"yorunge": "0.1.0.dev0"})
    return report


def diagnostic_receipt(report):
    raw = json.dumps(report, indent=2).encode()
    summary = HELPERS["STARTUP"]["validate"](report)
    return {
        "schema_version": 1,
        "report_kind": "startup_ci_diagnostic_v1",
        "source_commit": "a" * 40,
        "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/123",
        "report_name": "startup.json",
        "report_sha256": hashlib.sha256(raw).hexdigest(),
        "producer_exit": report["measurement_exit"],
        "outcome": summary["outcome"],
        "reason": "validated",
        "p95_ms": {key: row["p95_ms"] for key, row in summary["measurements"].items()},
    }


def test_linux_two_second_regression_is_explicit_diagnostic_not_performance_pass(pinned_inputs):
    result = HELPERS["classify"](ROOT, ROOT, pinned_inputs, 1)
    assert result["outcome"] == "diagnostic_budget_exceeded"
    assert result["passed"] is False
    retained = HELPERS["receipt_summary"](diagnostic_receipt(pinned_inputs))
    assert retained["diagnostic_only"] is True
    assert retained["ci_classification_accepted"] is True
    assert retained["passed"] is False


@pytest.mark.parametrize(
    "damage",
    [
        "exit",
        "missing_sample",
        "p95",
        "typed",
        "source",
        "fixture",
        "version",
        "float_counter",
        "not_linux",
        "baseline",
    ],
)
def test_bad_measurement_cannot_be_downgraded_to_nonblocking_budget_overrun(pinned_inputs, damage):
    report = copy.deepcopy(pinned_inputs)
    code = 1
    if damage == "exit":
        code = 2
    elif damage == "missing_sample":
        report["measurement"]["measurements"]["cache"]["warm_samples_ms"].pop()
    elif damage == "p95":
        report["measurement"]["measurements"]["cache"]["warm_p95_ms"] = 10
    elif damage == "typed":
        report["output_checks"]["candidate"]["cache"]["typed_stdout_verified"] = False
    elif damage == "source":
        report["snapshots"]["after"]["candidate"]["source"]["source_sha256"]["new.py"] = "b" * 64
    elif damage == "fixture":
        report["snapshots"]["after"]["candidate"]["fixture"]["cache_sha256"] = "b" * 64
    elif damage == "version":
        report["schema_version"] = True
    elif damage == "float_counter":
        report["measurement"]["comparison"]["baseline_cache_dataset"]["records"] = 1024.0
    elif damage == "not_linux":
        report = receipt()
        code = 0
    else:
        for point in ("before", "after"):
            report["snapshots"][point]["baseline"]["source"]["commit"] = "9" * 40
    with pytest.raises(ValueError):
        HELPERS["classify"](ROOT, ROOT, report, code)


def test_summary_warning_and_receipt_make_green_aggregate_overrun_visible(
    pinned_inputs, tmp_path, monkeypatch, capsys
):
    summary, output = tmp_path / "summary", tmp_path / "outputs"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    value = diagnostic_receipt(pinned_inputs)
    HELPERS["publish"](value)
    assert "::warning title=Linux startup diagnostic_budget_exceeded::" in capsys.readouterr().out
    text = summary.read_text()
    for expected in (
        "2000.000000",
        "10.000000",
        "diagnostic_budget_exceeded",
        "archive original",
        value["run_url"],
        value["source_commit"],
        value["report_sha256"],
    ):
        assert expected in text
    assert output.read_text() == "outcome=diagnostic_budget_exceeded\n"


def test_upload_guard_rechecks_original_report_bytes_and_requires_both_files(
    pinned_inputs, tmp_path
):
    report, receipt_path = tmp_path / "startup.json", tmp_path / "receipt.json"
    report.write_text(json.dumps(pinned_inputs, indent=2))
    receipt_path.write_text(json.dumps(diagnostic_receipt(pinned_inputs)))
    assert (
        HELPERS["verify_files"](ROOT, ROOT, report, receipt_path)["outcome"]
        == "diagnostic_budget_exceeded"
    )
    report.write_text(report.read_text() + "\n")
    with pytest.raises(ValueError, match="original report bytes"):
        HELPERS["verify_files"](ROOT, ROOT, report, receipt_path)
    receipt_path.unlink()
    with pytest.raises(ValueError, match="regular evidence"):
        HELPERS["verify_files"](ROOT, ROOT, report, receipt_path)


@pytest.mark.parametrize(
    "failure", ["missing", "invalid", "raised_after_report", "unexpected_exit"]
)
def test_producer_failures_remain_blocking_and_have_explicit_failure_receipt(
    pinned_inputs, tmp_path, monkeypatch, failure
):
    report, receipt_path = tmp_path / "startup.json", tmp_path / "receipt.json"

    def producer(*args, **kwargs):
        if failure != "missing":
            report.write_text("invalid" if failure == "invalid" else json.dumps(pinned_inputs))
        if failure in ("missing", "raised_after_report"):
            raise ValueError("controlled fake failure")
        return 2 if failure == "unexpected_exit" else 1

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
        receipt=receipt_path,
        report=report,
        baseline_project=ROOT,
        workspace=tmp_path / "workspace",
        uv=Path("unused"),
        run_url="https://github.com/HodeTech/Yorunge/actions/runs/123",
    )
    assert HELPERS["run"](args) == 1
    value = json.loads(receipt_path.read_text())
    assert value["outcome"] == "error"
    assert value["p95_ms"] == {}
    assert HELPERS["receipt_summary"](value)["ci_classification_accepted"] is False


def test_reference_receipt_cannot_hide_missing_startup_archive(tmp_path):
    with pytest.raises(ValueError):
        HELPERS["STARTUP"]["CHECKS"]["verify_startup_reference"](ROOT, "missing-startup.json")
