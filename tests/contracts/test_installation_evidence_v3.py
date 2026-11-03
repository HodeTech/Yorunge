"""Mandatory installed upload evidence cannot be omitted or folded into historical v2."""

import copy
import runpy
from pathlib import Path

import pytest

from tests.contracts.test_installation_evidence import receipt as receipt_v2

ROOT = Path(__file__).resolve().parents[2]
CHECKS = runpy.run_path(str(ROOT / "scripts/research_evidence.py"))


def receipt():
    value = receipt_v2()
    value.update(schema_version=3, report_kind="installation_v3")
    for row in value["results"]:
        row["upload_smoke"] = "passed"
    return value


def test_new_installation_has_nine_mandatory_checks_and_archives_losslessly(tmp_path):
    value = receipt()
    found = CHECKS["summarize"](value)
    assert found["kind"] == "installation_v3"
    assert found["passed"] is True
    assert set(found["checks"]) == {*CHECKS["INSTALL_CHECKS"], "upload_smoke"}
    assert found["checks"]["upload_smoke"] == {"passed": 2}
    (tmp_path / "docs/research").mkdir(parents=True)
    (tmp_path / "dist").mkdir()
    source = tmp_path / "dist/installation.json"
    source.write_bytes(CHECKS["encode"](value))
    CHECKS["archive_report"](tmp_path, source, None)
    assert CHECKS["verify"](tmp_path) == 1
    assert CHECKS["catalog"](tmp_path / "docs/research")[0]["summary"]["kind"] == "installation_v3"


@pytest.mark.parametrize("status", ["failed", "not_run_unsupported_platform"])
def test_uncompleted_upload_smoke_is_explicitly_failed(status):
    value = receipt()
    value["results"][0]["upload_smoke"] = status
    value["passed"] = False
    found = CHECKS["summarize"](value)
    assert found["passed"] is False
    assert found["checks"]["upload_smoke"] == {status: 1, "passed": 1}
    value["passed"] = True
    with pytest.raises(ValueError):
        CHECKS["summarize"](value)


@pytest.mark.parametrize(
    "damage", ["missing", "bool", "unknown", "extra", "schema", "mixed", "duplicate"]
)
def test_v3_closed_rows_reject_missing_or_ambiguous_upload_acceptance(damage):
    value = receipt()
    if damage == "missing":
        del value["results"][0]["upload_smoke"]
    elif damage == "bool":
        value["results"][0]["upload_smoke"] = True
    elif damage == "unknown":
        value["results"][0]["upload_smoke"] = "not_recorded"
    elif damage == "extra":
        value["results"][0]["ignored"] = True
    elif damage == "schema":
        value["schema_version"] = True
    elif damage == "mixed":
        value["results"][1] = receipt_v2()["results"][1]
    else:
        value["results"][1] = copy.deepcopy(value["results"][0])
    with pytest.raises(ValueError):
        CHECKS["summarize"](value)


def test_historical_v2_stays_closed_and_keeps_exact_old_summary():
    old = receipt_v2()
    summary = CHECKS["summarize"](old)
    assert summary["kind"] == "installation_v2"
    assert summary["passed"] is True
    assert "upload_smoke" not in summary["checks"]
    old["results"][0]["upload_smoke"] = "passed"
    with pytest.raises(ValueError):
        CHECKS["summarize"](old)
