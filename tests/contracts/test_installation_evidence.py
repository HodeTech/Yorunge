"""Typed installation evidence covers every modern smoke without rewriting history."""

import copy
import json
import runpy
from pathlib import Path

import pytest

CHECKS = runpy.run_path(str(Path(__file__).parents[2] / "scripts/research_evidence.py"))
SMOKES = (
    "smoke",
    "ndjson_smoke",
    "http_smoke",
    "stream_smoke",
    "cache_smoke",
    "execution_smoke",
    "jobs_smoke",
)


def receipt():
    rows = [
        {
            "archive": "yorunge-0.1.0.dev0-py3-none-any.whl",
            "sha256": "b" * 64,
            "members": 30,
            "origin_verified": True,
            **dict.fromkeys(SMOKES, "passed"),
        },
        {
            "archive": "yorunge-0.1.0.dev0.tar.gz",
            "sha256": "c" * 64,
            "members": 100,
            "origin_verified": True,
            **dict.fromkeys(SMOKES, "passed"),
        },
    ]
    return {
        "schema_version": 2,
        "report_kind": "installation_v2",
        "source_commit": "a" * 40,
        "environment": {"os": "Linux", "python": "3.14.0"},
        "results": rows,
        "passed": True,
    }


def test_modern_installation_archive_reports_all_eight_checks(tmp_path):
    root = tmp_path / "repo"
    (root / "dist").mkdir(parents=True)
    (root / "docs/research").mkdir(parents=True)
    source = root / "dist/installation.json"
    source.write_text(json.dumps(receipt()))
    CHECKS["archive_report"](root, source, None)
    assert CHECKS["verify"](root) == 1
    manifest = json.loads((root / "docs/research/evidence-manifest.json").read_bytes())
    summary = manifest["entries"][0]["summary"]
    assert summary["kind"] == "installation_v2"
    assert summary["passed"] is True
    assert summary["source_commit"] == "a" * 40
    assert summary["checks"]["origin_verified"] == {"true": 2}
    assert set(summary["checks"]) == {"origin_verified", *SMOKES}
    assert all(summary["checks"][key] == {"passed": 2} for key in SMOKES)


@pytest.mark.parametrize("check", ["origin_verified", *SMOKES])
def test_failed_check_is_preserved_and_prevents_green_top_level_result(check):
    report = receipt()
    report["results"][0][check] = False if check == "origin_verified" else "failed"
    report["passed"] = False
    summary = CHECKS["summarize"](report)
    assert summary["passed"] is False
    assert summary["checks"][check] == (
        {"false": 1, "true": 1} if check == "origin_verified" else {"failed": 1, "passed": 1}
    )
    report["passed"] = True
    with pytest.raises(ValueError, match="flag"):
        CHECKS["summarize"](report)


@pytest.mark.parametrize("status", ["failed", "not_run_unsupported_platform"])
def test_platform_skip_is_a_known_status_but_does_not_complete_installation(status):
    report = receipt()
    report["results"][1]["stream_smoke"] = status
    report["passed"] = False
    assert CHECKS["summarize"](report)["checks"]["stream_smoke"] == {status: 1, "passed": 1}
    report["passed"] = True
    with pytest.raises(ValueError, match="flag"):
        CHECKS["summarize"](report)


@pytest.mark.parametrize(
    "key,value",
    [
        ("archive", "../escape.whl"),
        ("archive", "/tmp/yorunge.whl"),
        ("archive", "yorunge.zip"),
        ("archive", "yorunge..whl"),
        ("archive", "yorunge\\x.whl"),
        ("sha256", "0" * 63),
        ("sha256", "A" * 64),
        ("members", 0),
        ("members", -1),
        ("members", True),
        ("members", 1.0),
        ("origin_verified", "true"),
        ("origin_verified", 1),
        ("ndjson_smoke", True),
        ("http_smoke", "success"),
        ("stream_smoke", None),
        ("jobs_smoke", []),
    ],
)
def test_modern_installation_rejects_bad_artifact_metadata_or_unrecognized_status(key, value):
    report = receipt()
    report["results"][0][key] = value
    with pytest.raises(ValueError):
        CHECKS["summarize"](report)


@pytest.mark.parametrize(
    "damage",
    [
        "version",
        "bool_version",
        "kind",
        "source",
        "environment",
        "missing_top",
        "extra_top",
        "missing_check",
        "extra_row",
        "duplicate",
        "two_wheels",
        "one_artifact",
        "false_negative",
    ],
)
def test_modern_installation_schema_does_not_implicitly_accept_missing_checks(damage):
    report = receipt()
    if damage == "version":
        report["schema_version"] = 1
    elif damage == "bool_version":
        report["schema_version"] = True
    elif damage == "kind":
        report["report_kind"] = "installation_v3"
    elif damage == "source":
        report["source_commit"] = "HEAD"
    elif damage == "environment":
        report["environment"] = []
    elif damage == "missing_top":
        del report["passed"]
    elif damage == "extra_top":
        report["unchecked"] = True
    elif damage == "missing_check":
        del report["results"][0]["ndjson_smoke"]
    elif damage == "extra_row":
        report["results"][0]["unchecked"] = True
    elif damage == "duplicate":
        report["results"][1] = copy.deepcopy(report["results"][0])
    elif damage == "two_wheels":
        report["results"][1]["archive"] = "yorunge-other.whl"
    elif damage == "one_artifact":
        report["results"].pop()
    else:
        report["passed"] = False
    with pytest.raises(ValueError):
        CHECKS["summarize"](report)


def test_historical_installation_summary_stays_exact_and_missing_checks_are_visible():
    report = {
        "source_commit": "historical source label",
        "results": [
            {
                "archive": "old.whl",
                "origin_verified": True,
                "smoke": "passed",
                "cache_smoke": "failed",
                "execution_smoke": "passed",
            },
        ],
    }
    assert CHECKS["summarize"](report) == {
        "source_commit": "historical source label",
        "diagnostic_only": False,
        "kind": "installation",
        "cases": 1,
        "checks": {
            "origin_verified": {"true": 1},
            "smoke": {"passed": 1},
            "cache_smoke": {"failed": 1},
            "execution_smoke": {"passed": 1},
            "jobs_smoke": {"not_recorded": 1},
        },
    }
