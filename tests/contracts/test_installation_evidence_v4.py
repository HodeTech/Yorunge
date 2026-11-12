"""Mandatory installed resume, versions and download evidence cannot be omitted or hidden in v3."""

import copy
import runpy
from pathlib import Path

import pytest

from tests.contracts.test_installation_evidence import receipt as receipt_v2
from tests.contracts.test_installation_evidence_v3 import receipt as receipt_v3

pytestmark = pytest.mark.usefixtures("evidence_publication_context")

ROOT = Path(__file__).resolve().parents[2]
CHECKS = runpy.run_path(str(ROOT / "scripts/research_evidence.py"))
ADDED = ("resume_smoke", "versions_smoke", "download_smoke")


def receipt():
    value = receipt_v3()
    value.update(schema_version=4, report_kind="installation_v4")
    for row in value["results"]:
        row.update(dict.fromkeys(ADDED, "passed"))
    return value


def test_the_check_names_extend_v3_by_exactly_the_three_new_smokes():
    assert CHECKS["INSTALL_CHECKS_V3"] == (*CHECKS["INSTALL_CHECKS"], "upload_smoke")
    assert CHECKS["INSTALL_CHECKS_V4"] == (*CHECKS["INSTALL_CHECKS_V3"], *ADDED)
    assert len(CHECKS["INSTALL_CHECKS_V4"]) == len(set(CHECKS["INSTALL_CHECKS_V4"])) == 12


def test_new_installation_has_twelve_mandatory_checks_and_archives_losslessly(tmp_path):
    value = receipt()
    found = CHECKS["summarize"](value)
    assert found["kind"] == "installation_v4"
    assert found["cases"] == 2
    assert found["passed"] is True
    assert set(found["checks"]) == {*CHECKS["INSTALL_CHECKS"], "upload_smoke", *ADDED}
    assert found["checks"]["origin_verified"] == {"true": 2}
    for name in ("upload_smoke", *ADDED):
        assert found["checks"][name] == {"passed": 2}
    (tmp_path / "docs/research").mkdir(parents=True)
    (tmp_path / "dist").mkdir()
    source = tmp_path / "dist/installation.json"
    source.write_bytes(CHECKS["encode"](value))
    CHECKS["archive_report"](tmp_path, source, None)
    assert CHECKS["verify"](tmp_path) == 1
    assert CHECKS["catalog"](tmp_path / "docs/research")[0]["summary"]["kind"] == "installation_v4"


@pytest.mark.parametrize("name", ADDED)
@pytest.mark.parametrize("status", ["failed", "not_run_unsupported_platform"])
def test_uncompleted_new_smoke_is_explicitly_failed(name, status):
    value = receipt()
    value["results"][0][name] = status
    value["passed"] = False
    found = CHECKS["summarize"](value)
    assert found["passed"] is False
    assert found["checks"][name] == {status: 1, "passed": 1}
    # Every other check still reads as passed: the failure is attributed to exactly one smoke.
    assert all(
        found["checks"][other] in ({"passed": 2}, {"true": 2})
        for other in found["checks"]
        if other != name
    )
    value["passed"] = True
    with pytest.raises(ValueError):
        CHECKS["summarize"](value)


@pytest.mark.parametrize("name", ADDED)
@pytest.mark.parametrize("damage", ["missing", "bool", "unknown", "empty", "none", "case"])
def test_v4_closed_rows_reject_missing_or_ambiguous_acceptance(name, damage):
    value = receipt()
    if damage == "missing":
        del value["results"][1][name]
    elif damage == "bool":
        value["results"][1][name] = True
    elif damage == "unknown":
        value["results"][1][name] = "not_recorded"
    elif damage == "empty":
        value["results"][1][name] = ""
    elif damage == "none":
        value["results"][1][name] = None
    else:
        value["results"][1][name] = "Passed"
    with pytest.raises(ValueError):
        CHECKS["summarize"](value)


@pytest.mark.parametrize(
    "damage",
    [
        "extra_row",
        "extra_top",
        "missing_top",
        "bool_schema",
        "float_schema",
        "mixed",
        "duplicate",
        "one_artifact",
        "three_artifacts",
        "false_positive",
        "commit",
        "environment",
        "origin",
    ],
)
def test_v4_closed_record_rejects_structural_damage(damage):
    value = receipt()
    if damage == "extra_row":
        value["results"][0]["ignored"] = True
    elif damage == "extra_top":
        value["unchecked"] = True
    elif damage == "missing_top":
        del value["passed"]
    elif damage == "bool_schema":
        value["schema_version"] = True
    elif damage == "float_schema":
        value["schema_version"] = 4.0
    elif damage == "mixed":
        value["results"][1] = receipt_v3()["results"][1]
    elif damage == "duplicate":
        value["results"][1] = copy.deepcopy(value["results"][0])
    elif damage == "one_artifact":
        value["results"].pop()
    elif damage == "three_artifacts":
        value["results"].append(copy.deepcopy(value["results"][0]))
    elif damage == "false_positive":
        value["results"][0]["download_smoke"] = "failed"
    elif damage == "commit":
        value["source_commit"] = "HEAD"
    elif damage == "environment":
        value["environment"] = []
    else:
        value["results"][0]["origin_verified"] = "true"
    with pytest.raises(ValueError):
        CHECKS["summarize"](value)


@pytest.mark.parametrize("version,kind", [(3, "installation_v4"), (4, "installation_v3")])
def test_schema_and_kind_must_agree_to_reach_a_reader(version, kind):
    value = receipt()
    value.update(schema_version=version, report_kind=kind)
    with pytest.raises(ValueError):
        CHECKS["summarize"](value)


def test_historical_v2_and_v3_stay_closed_and_keep_their_exact_summaries():
    v3_checks = {*CHECKS["INSTALL_CHECKS"], "upload_smoke"}
    for old, kind, names in (
        (receipt_v2(), "installation_v2", set(CHECKS["INSTALL_CHECKS"])),
        (receipt_v3(), "installation_v3", v3_checks),
    ):
        summary = CHECKS["summarize"](old)
        assert summary["kind"] == kind
        assert summary["passed"] is True
        assert set(summary["checks"]) == names
        # A record of the older kind that carries a newer field is not a record of that kind.
        old["results"][0]["resume_smoke"] = "passed"
        with pytest.raises(ValueError):
            CHECKS["summarize"](old)


def test_a_v4_record_is_not_accepted_by_the_older_readers():
    value = receipt()
    for reader in ("installation_summary", "installation_summary_v3"):
        with pytest.raises(ValueError):
            CHECKS[reader](value)
