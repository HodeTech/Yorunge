"""The v3 summary and the resume report: goldens, closed relationships and no private content."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from yorunge.domain.upload_public import DatasetUploadSummary, DatasetUploadSummaryV3
from yorunge.domain.upload_resume import BLOCKERS, recommended_action
from yorunge.domain.upload_resume_report import (
    MAX_EXAMPLES,
    PROBLEM_CLASSES,
    DatasetUploadResumeReport,
    ResumeClassCounts,
    ResumeExamples,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"
PLAN_ID = "00000000-0000-4000-8000-000000000006"
OPERATION = "00000000-0000-4000-8000-000000000009"
OTHER = "00000000-0000-4000-8000-0000000000aa"


def canon(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode()


def fixture(name):
    return (FIXTURES / name).read_bytes()


def data(name):
    return json.loads(fixture(name))


# --- the summary ---------------------------------------------------------------------------------
SUMMARY = "dataset-continuation-summary-v3.json"


def summary_of(**changes):
    return {**data(SUMMARY), **changes}


def test_the_summary_golden_round_trips_and_keeps_the_constants_closed():
    raw = fixture(SUMMARY)
    summary = DatasetUploadSummaryV3.model_validate_json(raw)
    assert summary.encoded() == raw
    assert (summary.schema_version, summary.source_plan_schema) == (3, 3)
    assert summary.legacy_history_only is False and summary.remote_bytes_verified is False
    assert (summary.continuation_files, summary.remote_present_files, summary.uncertain_files) == (
        2,
        1,
        1,
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": 2},
        {"source_plan_schema": 2},
        {"source_plan_schema": True},
        {"legacy_history_only": True},
        {"legacy_history_only": 0},
        {"remote_bytes_verified": True},
        {"cost_scope": "original_start_invocation"},
        {"operation_status": None},  # a state needs its operation
        {"operation_id": None},
        {"approval_expires_at": None},
        {"approval_status": None},
        {"operation_status": "succeeded"},  # success needs metadata evidence
        {"verification_level": "metadata"},
        {"authority_verified": True},
        {"risks": ["cost_unverified", "authority_unverified"]},
        {"blockers": ["inputs_unverified", "inputs_unverified"]},
        {"cost_policy": "bounded_required"},  # needs a budget
        {"budget_micros": 5},  # a budget needs the bounded policy
        {"continuation_files": 1, "uncertain_files": 2},
        {"continuation_files": 100, "remote_present_files": 29},
        {"continuation_files": 129},
        {"dataset_id": None},
        {"dataset_id": "x"},
        {"continuation_of": "x"},
        {"extra": 1},
    ],
)
def test_a_malformed_summary_is_rejected(changes):
    with pytest.raises((ValidationError, ValueError)):
        DatasetUploadSummaryV3.model_validate_json(canon(summary_of(**changes)))


def test_summary_versions_never_cross():
    v3 = fixture(SUMMARY)
    with pytest.raises((ValidationError, ValueError)):
        DatasetUploadSummary.model_validate_json(v3)
    v2 = {**data(SUMMARY), "schema_version": 2}
    with pytest.raises((ValidationError, ValueError)):
        DatasetUploadSummaryV3.model_validate_json(canon(v2))


def test_a_finished_summary_carries_metadata_evidence_and_no_other_private_field():
    done = summary_of(operation_status="succeeded", verification_level="metadata")
    assert DatasetUploadSummaryV3.model_validate_json(canon(done)).verification_level == "metadata"
    assert set(DatasetUploadSummaryV3.model_fields).isdisjoint(
        {
            "created_dataset",
            "owner",
            "owner_id",
            "org_id",
            "name",
            "path",
            "paths",
            "receipt",
            "object_key",
            "root",
            "manifest",
            "baseline_digest",
            "baseline_operation_id",
        }
    )


# --- the report ----------------------------------------------------------------------------------
BLOCKED = "dataset-continuation-resume-report-v1-blocked.json"
ELIGIBLE = "dataset-continuation-resume-report-v1-eligible.json"


def report_of(name=BLOCKED, **changes):
    return {**data(name), **changes}


def counts(**changes):
    value = {
        "confirmed": 0,
        "observed": 0,
        "pending_clean": 0,
        "pending_uncertain": 0,
        "drift_missing": 0,
        "conflict": 0,
        "inventory_unreliable": 0,
    }
    value.update(changes)
    return value


def rejects(value):
    with pytest.raises((ValidationError, ValueError)):
        DatasetUploadResumeReport.model_validate_json(canon(value))


def accepts(value):
    return DatasetUploadResumeReport.model_validate_json(canon(value))


def quiet(blockers, **changes):
    """A report whose counts, examples and action agree with the blockers, so one rule can fail."""
    values = {
        "blockers": list(blockers),
        "eligible": not blockers,
        "class_counts": counts(confirmed=3),
        "send_files": 0,
        "send_bytes": 0,
        "unconfirmed_ack_required": False,
        "recommended_action": recommended_action(tuple(blockers)),
        "related_operation_id": None,
        "plan_id": None,
        "plan_digest": None,
        "examples": [],
    }
    return report_of(**{**values, **changes})


@pytest.mark.parametrize("name", [BLOCKED, ELIGIBLE])
def test_report_goldens_round_trip(name):
    raw = fixture(name)
    report = DatasetUploadResumeReport.model_validate_json(raw)
    assert report.encoded() == raw and len(raw) < DatasetUploadResumeReport.max_wire_bytes


def test_the_blocked_golden_names_blockers_and_the_eligible_one_a_plan():
    blocked = DatasetUploadResumeReport.model_validate_json(fixture(BLOCKED))
    assert blocked.blockers == ("drift_missing",) and not blocked.eligible
    assert blocked.recommended_action == "none" and blocked.plan_id is None
    assert [e.file_class for e in blocked.examples] == ["drift_missing"]
    eligible = DatasetUploadResumeReport.model_validate_json(fixture(ELIGIBLE))
    assert eligible.blockers == () and eligible.eligible
    assert eligible.recommended_action == "prepare" and eligible.unconfirmed_ack_required
    assert eligible.plan_id == PLAN_ID and eligible.send_files == 2
    assert eligible.class_counts.total() == eligible.file_count == 3


NEGATIVES = {
    "unknown blocker": report_of(blockers=["bogus"]),
    "blockers out of order": report_of(
        blockers=["conflict", "drift_missing"],
        class_counts=counts(confirmed=1, conflict=1, drift_missing=1),
    ),
    "repeated blocker": report_of(blockers=["drift_missing", "drift_missing"]),
    "eligible with a blocker": report_of(eligible=True),
    "blocked without the flag": report_of(ELIGIBLE, eligible=False),
    "action that ignores the blockers": report_of(recommended_action="prepare"),
    "wait where none applies": report_of(recommended_action="wait"),
    "too large without unreliable": quiet(["inventory_too_large"]),
    "drift class without its blocker": quiet([], class_counts=counts(drift_missing=3)),
    "conflict class without its blocker": quiet([], class_counts=counts(conflict=3)),
    "unreliable class without its blocker": quiet([], class_counts=counts(inventory_unreliable=3)),
    "counts short of the manifest": report_of(class_counts=counts(confirmed=1, pending_clean=1)),
    "counts beyond the manifest": report_of(file_count=2),
    "quota differs from the manifest": report_of(quota_files=2),
    "send count differs from the classes": report_of(send_files=2),
    "acknowledgement without unconfirmed files": report_of(unconfirmed_ack_required=True),
    "unconfirmed files without acknowledgement": report_of(
        ELIGIBLE, unconfirmed_ack_required=False
    ),
    "bytes without files": report_of(
        class_counts=counts(confirmed=2, drift_missing=1), send_files=0, send_bytes=5
    ),
    "plan id without digest": report_of(ELIGIBLE, plan_digest=None),
    "plan digest without id": report_of(ELIGIBLE, plan_id=None),
    "plan while blocked": report_of(plan_id=PLAN_ID, plan_digest="a" * 64),
    "related operation without a descendant blocker": report_of(related_operation_id=OTHER),
    "superseded without its successor": quiet(["source_superseded"]),
    "paths of an unlisted class": report_of(
        examples=[{"file_class": "conflict", "paths": ["a.txt"]}]
    ),
    "more examples than files in the class": report_of(
        examples=[{"file_class": "drift_missing", "paths": ["a.txt", "empty.bin"]}]
    ),
    "example classes out of order": report_of(
        blockers=["drift_missing", "conflict"],
        class_counts=counts(confirmed=1, drift_missing=1, conflict=1),
        examples=[
            {"file_class": "conflict", "paths": ["a.txt"]},
            {"file_class": "drift_missing", "paths": ["a.txt"]},
        ],
    ),
    "example class repeated": report_of(
        examples=[
            {"file_class": "drift_missing", "paths": ["a.txt"]},
            {"file_class": "drift_missing", "paths": ["empty.bin"]},
        ]
    ),
    "example class that is no problem": report_of(
        examples=[{"file_class": "observed", "paths": ["a.txt"]}]
    ),
    "malformed observation instant": report_of(observed_at="yesterday"),
    "uppercase digest": report_of(classification_digest="C" * 64),
    "short digest": report_of(inventory_digest="d" * 63),
    "bad source id": report_of(source_operation_id="x"),
    "bad dataset id": report_of(dataset_id="x"),
    "empty manifest": report_of(file_count=0, quota_files=0),
    "more files than an upload holds": report_of(file_count=129, quota_files=129),
    "bool as a count": report_of(send_files=True),
    "bytes over the upload limit": report_of(send_bytes=1024**3 + 1),
    "payload over the quota": report_of(quota_payload_bytes=16 * 1024 * 1024 + 1),
    "wrong version": report_of(schema_version=2),
    "wrong kind": report_of(kind="dataset_upload_summary"),
    "unknown field": report_of(extra=1),
}


@pytest.mark.parametrize("name", NEGATIVES)
def test_every_closed_report_negative_is_rejected(name):
    rejects(NEGATIVES[name])


def test_the_isolated_negatives_differ_from_valid_reports_by_the_one_rule_they_pin():
    accepts(quiet([]))
    accepts(quiet(["inventory_unreliable"], class_counts=counts(inventory_unreliable=3)))
    accepts(
        quiet(
            ["inventory_unreliable", "inventory_too_large"],
            class_counts=counts(inventory_unreliable=3),
        )
    )
    for blocker in ("drift_missing", "conflict"):
        accepts(quiet([blocker], class_counts=counts(**{blocker: 3})))
    accepts(quiet(["source_superseded"], related_operation_id=OTHER))


@pytest.mark.parametrize(
    "path", ["/abs.txt", "../up.txt", "a\\b.txt", "a/../b.txt", "x" * 2000, ""]
)
def test_example_paths_must_be_portable_relative_paths(path):
    rejects(report_of(examples=[{"file_class": "drift_missing", "paths": [path]}]))


def test_example_paths_are_ordered_distinct_and_at_most_eight():
    ok = [f"f{n}.bin" for n in range(8)]
    seven_missing = report_of(
        blockers=["drift_missing"],
        class_counts=counts(confirmed=120, drift_missing=8),
        file_count=128,
        quota_files=128,
        send_files=0,
        send_bytes=0,
        examples=[{"file_class": "drift_missing", "paths": ok}],
    )
    assert len(accepts(seven_missing).examples[0].paths) == MAX_EXAMPLES == 8
    nine = [f"f{n}.bin" for n in range(9)]
    for paths in (nine, ["b.bin", "a.bin"], ["a.bin", "a.bin"]):
        rejects({**seven_missing, "examples": [{"file_class": "drift_missing", "paths": paths}]})


def test_the_four_problem_classes_are_the_ones_a_user_must_act_on():
    assert PROBLEM_CLASSES == (
        "pending_uncertain",
        "drift_missing",
        "conflict",
        "inventory_unreliable",
    )
    assert ResumeExamples.model_fields["file_class"].annotation is not None


@pytest.mark.parametrize("blockers", [(b,) for b in BLOCKERS])
def test_every_single_blocker_yields_the_reference_action(blockers):
    # Class counts that agree with the blocker, so only the action rule is under test.
    needs = {
        "drift_missing": counts(confirmed=2, drift_missing=1),
        "conflict": counts(confirmed=2, conflict=1),
        "inventory_unreliable": counts(inventory_unreliable=3),
        "inventory_too_large": counts(inventory_unreliable=3),
    }
    names = list(blockers)
    if names == ["inventory_too_large"]:
        names = ["inventory_unreliable", "inventory_too_large"]
    cls = needs.get(blockers[0], counts(confirmed=2, observed=1))
    related = OTHER if blockers[0] in ("source_superseded", "source_active") else None
    value = report_of(
        blockers=names,
        class_counts=cls,
        send_files=0,
        send_bytes=0,
        recommended_action=recommended_action(names),
        related_operation_id=related,
        examples=[],
    )
    report = accepts(value)
    assert report.recommended_action == recommended_action(names) and not report.eligible


def test_a_source_whose_dataset_is_unknown_still_has_a_report():
    value = report_of(
        dataset_id=None,
        blockers=["create_unknown"],
        class_counts=counts(pending_clean=3),
        send_files=3,
        send_bytes=8,
        unconfirmed_ack_required=False,
        recommended_action="none",
        examples=[],
    )
    assert accepts(value).dataset_id is None


def test_the_report_wire_carries_no_private_field():
    names = set(DatasetUploadResumeReport.model_fields) | set(ResumeClassCounts.model_fields)
    assert names.isdisjoint(
        {
            "created_dataset",
            "owner",
            "owner_id",
            "org_id",
            "name",
            "receipt",
            "object_key",
            "url",
            "paths",
            "baseline_digest",
            "extra_paths",
            "item_ids",
        }
    )
    text = (fixture(BLOCKED) + fixture(ELIGIBLE)).decode()
    for needle in ("created_dataset", "object_key", "receipt", "http", "owner"):
        assert needle not in text
