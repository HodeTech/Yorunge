"""Only a valid Linux budget overrun may keep the remaining mandatory gates running."""

import argparse
import base64
import copy
import gzip
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


@pytest.mark.parametrize("failure", [OSError, KeyboardInterrupt])
def test_after_snapshot_failure_or_interruption_keeps_completed_inner_reports(
    tmp_path, monkeypatch, failure
):
    import subprocess
    from types import SimpleNamespace

    producer = runpy.run_path(str(ROOT / "scripts/check-startup-evidence.py"))
    report = receipt()
    before = report["snapshots"]["before"]
    monkeypatch.setitem(
        producer["EVIDENCE"], "source", lambda root: copy.deepcopy(before["candidate"]["source"])
    )
    monkeypatch.setitem(
        producer["PREPARE"],
        "prepare",
        lambda project, work, uv: SimpleNamespace(
            project=project, python=work / "env/bin/python", console=work / "env/bin/yorunge"
        ),
    )
    monkeypatch.setitem(producer["PREPARE"], "seed", lambda *args: None)
    calls = iter([before["candidate"], before["baseline"]])

    def snapshot(*args):
        try:
            return next(calls)
        except StopIteration:
            raise failure("after-snapshot interruption") from None

    monkeypatch.setitem(producer["check"].__globals__, "snapshot", snapshot)
    workspace = tmp_path / "workspace"

    def measure(args, **kwargs):
        (workspace / "measurement.json").write_text(json.dumps(report["measurement"]))
        (workspace / "stdout-checks.json").write_text(json.dumps(report["output_checks"]))
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", measure)
    final = tmp_path / "final.json"
    with pytest.raises(failure):
        producer["check"](ROOT, ROOT, workspace, final, Path("unused"), cpu=None, disk="unknown")
    assert not final.exists()
    for name in ("measurement.json", "stdout-checks.json", "source-manifest.json"):
        assert (workspace / name).is_file()


@pytest.mark.parametrize(
    "original", [b"", b"not JSON\xff", b'{"duplicate":1,"duplicate":2}', b'{"x":NaN}']
)
def test_rejected_raw_bytes_are_preserved_without_granting_performance_acceptance(original):
    checks = HELPERS["CHECKS"]
    report = {
        "schema_version": 1,
        "report_kind": "rejected_startup_evidence_v1",
        "source_commit": "a" * 40,
        "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/123",
        "original_name": "startup.json",
        "original_sha256": hashlib.sha256(original).hexdigest(),
        "original_bytes": len(original),
        "rejection_reason": "invalid_evidence",
        "content_base64": base64.b64encode(original).decode("ascii"),
    }
    summary = checks["summarize"](report)
    assert summary["accepted"] is False
    assert summary["diagnostic_only"] is True
    assert summary["original_sha256"] == hashlib.sha256(original).hexdigest()
    with pytest.raises(ValueError):
        HELPERS["STARTUP"]["reference"](ROOT, report)
    report["original_bytes"] += 1
    with pytest.raises(ValueError, match="bytes/hash mismatch"):
        checks["summarize"](report)


def test_rejected_provenance_report_is_attached_exactly_instead_of_weakening_validation(tmp_path):
    checks = HELPERS["CHECKS"]
    invalid = receipt()
    invalid["snapshots"]["after"]["candidate"]["fixture"]["cache_sha256"] = "9" * 64
    original = json.dumps(invalid).encode()
    with pytest.raises(ValueError, match="changed during measurement"):
        checks["summarize"](invalid)
    root = tmp_path / "repository"
    (root / "dist").mkdir(parents=True)
    (root / "docs/research/raw").mkdir(parents=True)
    original_path = root / "dist/startup-invalid.json"
    original_path.write_bytes(original)
    checks["archive_rejected_startup"](
        root,
        original_path,
        "startup-rejected.json",
        "a" * 40,
        "https://github.com/HodeTech/Yorunge/actions/runs/123",
        "invalid_evidence",
    )
    assert checks["verify"](root) == 1
    packed = root / "docs/research/raw/startup-rejected.json.gz"
    envelope = checks["decode"](gzip.decompress(packed.read_bytes()))
    assert base64.b64decode(envelope["content_base64"]) == original
    assert original_path.read_bytes() == original
    assert checks["summarize"](envelope)["accepted"] is False


@pytest.mark.parametrize("suffix", ["1٢3", "1１3"])
def test_github_run_ids_remain_ascii_after_concise_digit_regex(suffix):
    value = diagnostic_receipt(linux_report())
    value["run_url"] = "https://github.com/HodeTech/Yorunge/actions/runs/" + suffix
    with pytest.raises(ValueError):
        HELPERS["receipt_summary"](value)
    rejected = {
        "schema_version": 1,
        "report_kind": "rejected_startup_evidence_v1",
        "source_commit": "a" * 40,
        "run_url": value["run_url"],
        "original_name": "startup.json",
        "original_sha256": hashlib.sha256(b"").hexdigest(),
        "original_bytes": 0,
        "rejection_reason": "invalid_evidence",
        "content_base64": "",
    }
    with pytest.raises(ValueError):
        HELPERS["CHECKS"]["summarize"](rejected)


@pytest.mark.parametrize("content", ["!", "YQ", "\u0131"])
def test_redundant_base64_exception_removal_still_rejects_invalid_encoding(content):
    rejected = {
        "schema_version": 1,
        "report_kind": "rejected_startup_evidence_v1",
        "source_commit": "a" * 40,
        "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/123",
        "original_name": "startup.json",
        "original_sha256": hashlib.sha256(b"").hexdigest(),
        "original_bytes": 0,
        "rejection_reason": "invalid_evidence",
        "content_base64": content,
    }
    with pytest.raises(ValueError, match="invalid rejected startup base64"):
        HELPERS["CHECKS"]["summarize"](rejected)
