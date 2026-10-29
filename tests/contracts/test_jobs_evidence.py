"""Modern jobs receipts retain failed provenance and reject misleading summaries."""

import copy
import runpy
from pathlib import Path

import pytest

CHECKS = runpy.run_path(str(Path(__file__).parents[2] / "scripts/research_evidence.py"))


def receipt():
    source = {"commit": "a" * 40, "source_sha256": {"src/yorunge/__init__.py": "b" * 64}}
    installed = {
        "python": "3.14.0",
        "executable": "/runtime/bin/python",
        "prefix": "/runtime",
        "platform": "Linux-6.1",
        "machine": "arm64",
        "sqlite": "3.50.4",
        "packages": {"yorunge": "0.1.0.dev0", "httpx": "0.28.1"},
        "product_origin": "/runtime/lib/yorunge",
        "product_version": "0.1.0.dev0",
        "console": "/runtime/bin/yorunge",
        "console_sha256": "c" * 64,
        "installed_source_sha256": {"yorunge/__init__.py": "b" * 64},
    }
    rows = []
    for layout in ("normal", "dense"):
        for action in ("list", "show"):
            rows.append(
                {
                    "layout": layout,
                    "action": action,
                    "command": [
                        "/runtime/bin/python",
                        "-I",
                        "/runtime/bin/yorunge",
                        "jobs",
                        action,
                        "--limit" if action == "list" else "--operation-id",
                        "50" if action == "list" else "test-operation",
                        "--state-dir",
                        "/fixtures/" + layout,
                        "--output",
                        "json",
                    ],
                    "first_process_ms": 12.0,
                    "warmups_ms": [11.0, 12.0, 10.0],
                    "samples_ms": [10.0] * 30,
                    "median_ms": 10.0,
                    "p95_ms": 10.0,
                    "budget_ms": 200,
                    "passed": True,
                    "typed_stdout_verified": True,
                    "verified_processes": 34,
                    "stdout_sha256": ["d" * 64] * 34,
                    "expected_list_rows": (1 if layout == "normal" else 50)
                    if action == "list"
                    else None,
                    "expected_operation_id": None if action == "list" else "test-operation",
                    "expected_plan_digest": None if action == "list" else "e" * 64,
                }
            )
    return {
        "schema_version": 1,
        "kind": "jobs",
        "source_commit": "a" * 40,
        "samples_per_command": 30,
        "method": "three warmups and all nearest-rank samples",
        "cold_method": "first process with uncontrolled caches",
        "validation_method": "fixture expectations and installed typed Result",
        "environment": {"runtime": installed, "cpu": "synthetic", "disk_type": "synthetic"},
        "fixtures": {"normal": {}, "dense": {}},
        "runs": rows,
        "provenance": {
            "source_before": source,
            "source_after": copy.deepcopy(source),
            "installed_before": installed,
            "installed_after": copy.deepcopy(installed),
            "wheel_sha256": "f" * 64,
            "wheel_path": "/artifacts/yorunge.whl",
            "source_unchanged_during_measurement": True,
            "installed_unchanged_during_measurement": True,
            "fixtures_unchanged_during_measurement": True,
            "unchanged": True,
            "isolated_python": True,
            "fixture_preparation_python": "/dev/bin/python",
            "fixture_preparation": "checkout fixture preparation outside measured processes",
        },
        "passed": True,
    }


def test_modern_jobs_summary_includes_complete_p95_and_provenance_flags():
    summary = CHECKS["summarize"](receipt())
    assert summary["kind"] == "jobs"
    assert summary["source_commit"] == "a" * 40
    assert summary["passed"] is True
    assert summary["unchanged"] is True
    assert summary["isolated_python"] is True
    assert set(summary["measurements"]) == {
        "normal/list",
        "normal/show",
        "dense/list",
        "dense/show",
    }
    assert all(metric["samples"] == 30 for metric in summary["measurements"].values())


@pytest.mark.parametrize(
    "failure", ["budget", "source", "installed", "fixture", "transient_wheel", "typed", "isolated"]
)
def test_modern_jobs_truthful_failure_cannot_be_hidden_by_fast_remaining_rows(failure):
    report = receipt()
    provenance = report["provenance"]
    if failure == "budget":
        report["runs"][0].update(samples_ms=[201] * 30, median_ms=201, p95_ms=201, passed=False)
    elif failure == "source":
        provenance["source_after"]["source_sha256"]["scripts/new.py"] = "e" * 64
        provenance["source_unchanged_during_measurement"] = False
        provenance["unchanged"] = False
    elif failure == "installed":
        provenance["installed_after"]["installed_source_sha256"]["yorunge/__init__.py"] = "e" * 64
        provenance["installed_unchanged_during_measurement"] = False
        provenance["unchanged"] = False
    elif failure == "fixture":
        provenance["fixtures_unchanged_during_measurement"] = False
        provenance["unchanged"] = False
    elif failure == "transient_wheel":
        provenance["unchanged"] = False
    elif failure == "typed":
        report["runs"][0]["typed_stdout_verified"] = False
    else:
        provenance["isolated_python"] = False
    report["passed"] = False
    assert CHECKS["summarize"](report)["passed"] is False
    report["passed"] = True
    with pytest.raises(ValueError, match="flag"):
        CHECKS["summarize"](report)


@pytest.mark.parametrize(
    "damage",
    [
        "p95",
        "forged_source_flag",
        "forged_installed_flag",
        "forged_unchanged",
        "bool_samples",
        "bool_counter",
        "median",
        "missing_process",
        "missing_case",
        "duplicate_case",
        "budget",
        "version",
        "bool_version",
        "wrong_source",
        "wrong_bytes",
    ],
)
def test_modern_jobs_does_not_accept_forged_percentile_or_provenance(damage):
    report = receipt()
    run, provenance = report["runs"][0], report["provenance"]
    if damage == "p95":
        run["samples_ms"][-2:] = [201, 205]
    elif damage == "forged_source_flag":
        provenance["source_after"]["commit"] = "b" * 40
    elif damage == "forged_installed_flag":
        provenance["installed_after"]["console_sha256"] = "e" * 64
    elif damage == "forged_unchanged":
        provenance["fixtures_unchanged_during_measurement"] = False
    elif damage == "bool_samples":
        run["samples_ms"][0] = True
    elif damage == "bool_counter":
        run["verified_processes"] = True
    elif damage == "median":
        run["median_ms"] = 9
    elif damage == "missing_process":
        run["stdout_sha256"].pop()
    elif damage == "missing_case":
        report["runs"].pop()
    elif damage == "duplicate_case":
        report["runs"][1] = copy.deepcopy(run)
    elif damage == "budget":
        run["budget_ms"] = 201
    elif damage == "version":
        report["schema_version"] = 2
    elif damage == "bool_version":
        report["schema_version"] = True
    elif damage == "wrong_source":
        report["source_commit"] = "b" * 40
    else:
        for snapshot in ("installed_before", "installed_after"):
            provenance[snapshot]["installed_source_sha256"]["yorunge/__init__.py"] = "e" * 64
    with pytest.raises(ValueError):
        CHECKS["summarize"](report)


def test_legacy_jobs_summary_does_not_gain_modern_fields():
    row = {
        "layout": "old",
        "action": "list",
        "samples_ms": [10] * 30,
        "p95_ms": 10,
        "budget_ms": 200,
        "passed": True,
    }
    assert CHECKS["summarize"]({"runs": [row]}) == {
        "source_commit": None,
        "diagnostic_only": False,
        "kind": "jobs",
        "measurements": {
            "old/list": {"samples": 30, "p95_ms": 10.0, "budget_ms": 200.0, "passed": True},
        },
    }


def test_modern_jobs_cannot_downgrade_to_legacy_by_removing_provenance():
    report = receipt()
    report["provenance"]["isolated_python"] = False
    report["passed"] = False
    assert CHECKS["summarize"](report)["passed"] is False
    del report["provenance"]
    report["passed"] = True
    with pytest.raises(ValueError, match="jobs report"):
        CHECKS["summarize"](report)


@pytest.mark.parametrize(
    "damage", ["foreign", "not_isolated", "console", "action", "help", "format", "id"]
)
def test_modern_jobs_command_must_match_its_installed_runtime_and_measurement(damage):
    report = receipt()
    command = report["runs"][0]["command"]
    if damage == "foreign":
        command[:] = ["/other/bin/python", "/other/bin/yorunge", "--help"]
    elif damage == "not_isolated":
        command[1] = "-B"
    elif damage == "console":
        command[2] = "/other/bin/yorunge"
    elif damage == "action":
        command[4] = "show"
    elif damage == "help":
        command.append("--help")
    elif damage == "format":
        command[-1] = "text"
    else:
        report["runs"][1]["command"][6] = "different-operation"
    with pytest.raises(ValueError, match="jobs command"):
        CHECKS["summarize"](report)


def test_macos_jobs_runtime_aliases_are_portable_and_do_not_access_historical_paths(monkeypatch):
    report = receipt()
    for key in ("installed_before", "installed_after"):
        report["provenance"][key].update(
            prefix="/private/var/absent-runtime",
            executable="/var/absent-runtime/bin/python",
            product_origin="/private/var/absent-runtime/lib/yorunge",
            console="/var/absent-runtime/bin/yorunge",
            platform="macOS-15.0",
        )
    for run in report["runs"]:
        run["command"][0] = "/var/absent-runtime/bin/python"
        run["command"][2] = "/var/absent-runtime/bin/yorunge"

    def forbidden(*args, **kwargs):
        raise AssertionError("archival verification must not resolve recorded runtime paths")

    monkeypatch.setattr(Path, "resolve", forbidden)
    monkeypatch.setattr(Path, "exists", forbidden)
    assert CHECKS["summarize"](report)["passed"] is True
