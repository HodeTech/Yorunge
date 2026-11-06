"""The v3 summary and the resume report: goldens, closed relationships and no private content."""

import hashlib
import itertools
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from yorunge.application.continuation_policy import (
    ContinuationPreparation,
    continuation_binding,
    continuation_limits,
    prepare_continuation_v3,
)
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.dataset_manifest import DatasetManifest, canonical_manifest
from yorunge.domain.upload_costs import ContinuationCostWork
from yorunge.domain.upload_public import DatasetUploadSummary, DatasetUploadSummaryV3
from yorunge.domain.upload_resume import (
    BLOCKERS,
    FILE_CLASSES,
    ChainSummary,
    RemoteInventory,
    RemoteItem,
    classify,
    recommended_action,
)
from yorunge.domain.upload_resume_report import (
    MAX_EXAMPLES,
    PROBLEM_CLASSES,
    DatasetUploadResumeReport,
    QuotaCounters,
    ResumeClassCounts,
    ResumeExamples,
    ResumeObservation,
    resume_report,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"
PLAN_ID = "00000000-0000-4000-8000-000000000006"
OPERATION = "00000000-0000-4000-8000-000000000009"
OTHER = "00000000-0000-4000-8000-0000000000aa"
CONTINUATION = "00000000-0000-4000-8000-00000000000c"
DATASET = "00000000-0000-4000-8000-000000000909"


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
        {"continuation_files": 0, "remote_present_files": 0, "uncertain_files": 0},  # no manifest
        {"operation_id": "00000000-0000-4000-8000-000000000009"},  # its own source
        {"approval_expires_at": "yesterday"},
        {"dataset_id": None},
        {"dataset_id": "x"},
        {"continuation_of": "x"},
        {"extra": 1},
    ],
)
def test_a_malformed_summary_is_rejected(changes):
    with pytest.raises((ValidationError, ValueError)):
        DatasetUploadSummaryV3.model_validate_json(canon(summary_of(**changes)))


def test_a_malformed_approval_expiry_is_refused_by_every_summary_version_alike():
    v2 = data("dataset-upload-summary-v2.json")
    assert DatasetUploadSummary.model_validate_json(canon(v2)).approval_expires_at is not None
    with pytest.raises((ValidationError, ValueError)):
        DatasetUploadSummary.model_validate_json(canon({**v2, "approval_expires_at": "yesterday"}))
    assert DatasetUploadSummaryV3.model_validate_json(canon(summary_of())).approval_status


def test_the_summary_wire_holds_exactly_its_limit_and_not_a_byte_more():
    limit = DatasetUploadSummaryV3.max_wire_bytes
    assert limit == 16 * 1024
    raw = fixture(SUMMARY)
    DatasetUploadSummaryV3.model_validate_json(raw + b" " * (limit - len(raw)))
    with pytest.raises(ValueError, match="bounded upload wire"):
        DatasetUploadSummaryV3.model_validate_json(raw + b" " * (limit - len(raw) + 1))


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
UNOBSERVED = "dataset-continuation-resume-report-v1-unobserved.json"
MANIFEST = DatasetManifest.model_validate_json(fixture("dataset-manifest-v1.json"))
PLAN = DatasetContinuationPlanV3.model_validate_json(fixture("dataset-continuation-plan-v3.json"))
QUOTA = QuotaCounters(plans=2, operations=1, files=6, payload_bytes=98304)
INVENTORY = {
    "drift_missing",
    "conflict",
    "extra_remote",
    "inventory_unreliable",
    "inventory_too_large",
}
JOURNAL = {
    "source_active",
    "source_ineligible",
    "source_superseded",
    "source_terminal",
    "reconcile_available",
    "create_unknown",
    "known_negative",
}
WAITING = ("source_superseded", "source_active")


def report_of(name=BLOCKED, **changes):
    return {**data(name), **changes}


def counts(**changes):
    value = {name: 0 for name in FILE_CLASSES}
    value.update(changes)
    return value


def accepts(value):
    return DatasetUploadResumeReport.model_validate_json(canon(value))


def rejects(value):
    with pytest.raises((ValidationError, ValueError)):
        DatasetUploadResumeReport.model_validate_json(canon(value))


def action_for(blockers):
    """The reference action, or none for a blocker name the closed set does not hold."""
    closed = all(name in BLOCKERS for name in blockers)
    return recommended_action(tuple(blockers)) if closed else "none"


def observed(blockers=(), classes=None, **changes):
    """An observed report whose counts, send fields, examples and action agree with the blockers."""
    base = data(ELIGIBLE)
    observation = {
        **base["observation"],
        "class_counts": classes or counts(confirmed=3),
        "send_files": 0,
        "send_bytes": 0,
        "unconfirmed_ack_required": False,
        "examples": [],
    }
    value = {
        **base,
        "blockers": list(blockers),
        "eligible": not blockers,
        "recommended_action": action_for(blockers),
        "plan_id": None,
        "plan_digest": None,
        "observation": observation,
    }
    return {**value, **changes}


def inside(value, **changes):
    """The same report with some of its observation replaced."""
    return {**value, "observation": {**value["observation"], **changes}}


def unobserved(blockers=("create_unknown",), **changes):
    """A report of a source nothing could be observed of: no inventory, so no observation."""
    value = {
        **data(UNOBSERVED),
        "blockers": list(blockers),
        "eligible": not blockers,
        "recommended_action": recommended_action(tuple(blockers)),
        "dataset_id": None if "create_unknown" in blockers else DATASET,
    }
    return {**value, **changes}


def quota(which, **changes):
    return {**data(BLOCKED)[which], **changes}


MISSING = counts(confirmed=2, drift_missing=1)
LISTED = {"file_class": "drift_missing", "paths": ["a.txt"]}


def listed(*examples, classes=MISSING):
    value = observed(["drift_missing"], classes)
    return inside(value, examples=list(examples))


@pytest.mark.parametrize("name", [BLOCKED, ELIGIBLE, UNOBSERVED])
def test_report_goldens_round_trip(name):
    raw = fixture(name)
    report = DatasetUploadResumeReport.model_validate_json(raw)
    assert report.encoded() == raw and len(raw) < DatasetUploadResumeReport.max_wire_bytes


def test_the_goldens_name_blockers_a_plan_and_a_source_nothing_was_observed_of():
    blocked = DatasetUploadResumeReport.model_validate_json(fixture(BLOCKED))
    assert blocked.blockers == ("drift_missing",) and not blocked.eligible
    assert blocked.recommended_action == "none" and blocked.plan_id is None
    assert [e.file_class for e in blocked.observation.examples] == ["drift_missing"]
    eligible = DatasetUploadResumeReport.model_validate_json(fixture(ELIGIBLE))
    assert eligible.blockers == () and eligible.eligible
    assert eligible.recommended_action == "prepare"
    assert eligible.observation.unconfirmed_ack_required
    assert eligible.plan_id is None and eligible.observation.send_files == 2
    assert eligible.observation.class_counts.total() == eligible.file_count == 3
    nothing = DatasetUploadResumeReport.model_validate_json(fixture(UNOBSERVED))
    assert nothing.observation is None and nothing.dataset_id is None
    assert nothing.blockers == ("create_unknown",) and nothing.recommended_action == "none"
    assert (nothing.quota_added.plans, nothing.quota_added.files) == (1, 3)


NEGATIVES = {
    # blockers, eligibility and the action
    "unknown blocker": observed(["bogus"]),
    "blockers out of order": observed(
        ["conflict", "drift_missing"], counts(confirmed=1, conflict=1, drift_missing=1)
    ),
    "repeated blocker": observed(["drift_missing", "drift_missing"], MISSING),
    "eligible with a blocker": observed(["drift_missing"], MISSING, eligible=True),
    "blocked without the flag": observed([], eligible=False),
    "action that ignores the blockers": observed([], recommended_action="none"),
    "wait where none applies": observed(["drift_missing"], MISSING, recommended_action="wait"),
    "too large without unreliable": observed(["inventory_too_large"]),
    # the dataset and its unknown create
    "unknown create that names a dataset": unobserved(dataset_id=DATASET),
    "no unknown create yet no dataset": observed([], dataset_id=None),
    # no observation
    "no observation and no blocker": unobserved([], dataset_id=DATASET),
    "no observation behind a drift blocker": unobserved(["drift_missing"]),
    "no observation behind an unreliable listing": unobserved(["inventory_unreliable"]),
    # class counts and blocking classes
    "counts short of the manifest": observed([], counts(confirmed=2)),
    "counts beyond the manifest": observed([], counts(confirmed=4)),
    "drift class without its blocker": observed([], counts(drift_missing=3)),
    "conflict class without its blocker": observed([], counts(conflict=3)),
    "unreliable class without its blocker": observed([], counts(inventory_unreliable=3)),
    "unreliable listing beside confirmed files": observed(
        ["inventory_unreliable"], counts(confirmed=2, inventory_unreliable=1)
    ),
    "unreliable listing beside observed files": observed(
        ["inventory_unreliable"], counts(observed=1, inventory_unreliable=2)
    ),
    "unreliable listing beside unsent files": inside(
        observed(["inventory_unreliable"], counts(pending_clean=1, inventory_unreliable=2)),
        send_files=1,
        send_bytes=3,
    ),
    "unreliable listing beside unconfirmed files": inside(
        observed(["inventory_unreliable"], counts(pending_uncertain=1, inventory_unreliable=2)),
        send_files=1,
        send_bytes=3,
        unconfirmed_ack_required=True,
    ),
    "unreliable listing beside missing files": observed(
        ["drift_missing", "inventory_unreliable"], counts(drift_missing=1, inventory_unreliable=2)
    ),
    # the send selection
    "send count differs from the classes": inside(observed(), send_files=1),
    "acknowledgement without unconfirmed files": inside(observed(), unconfirmed_ack_required=True),
    "unconfirmed files without acknowledgement": inside(
        observed([], counts(confirmed=2, pending_uncertain=1)), send_files=1, send_bytes=3
    ),
    "bytes without files": inside(observed(), send_bytes=5),
    "bytes over the upload limit": inside(
        observed([], counts(confirmed=2, pending_clean=1)), send_files=1, send_bytes=1024**3 + 1
    ),
    "bool as a count": inside(observed([], counts(confirmed=2, pending_clean=1)), send_files=True),
    # examples
    "paths of a class nobody is in": listed(
        {"file_class": "conflict", "paths": ["a.txt"]}, classes=MISSING
    ),
    "more examples than files in the class": listed(
        {"file_class": "drift_missing", "paths": ["a.txt", "empty.bin"]}
    ),
    "example classes out of order": inside(
        observed(["drift_missing", "conflict"], counts(confirmed=1, drift_missing=1, conflict=1)),
        examples=[
            {"file_class": "conflict", "paths": ["a.txt"]},
            {"file_class": "drift_missing", "paths": ["a.txt"]},
        ],
    ),
    "example class repeated": inside(
        observed(["drift_missing"], counts(drift_missing=3)),
        examples=[
            {"file_class": "drift_missing", "paths": ["a.txt"]},
            {"file_class": "drift_missing", "paths": ["empty.bin"]},
        ],
    ),
    "example class that is no problem": listed({"file_class": "observed", "paths": ["a.txt"]}),
    "an example class without a path": listed({"file_class": "drift_missing", "paths": []}),
    # the quota
    "an attempt that adds two plans": observed([], quota_added=quota("quota_added", plans=2)),
    "an attempt that adds no operation": observed(
        [], quota_added=quota("quota_added", operations=0)
    ),
    "an attempt that adds another file count": observed(
        [], quota_added=quota("quota_added", files=2)
    ),
    "plans beyond the store limit": observed([], quota_used=quota("quota_used", plans=129)),
    "operations beyond the store limit": observed(
        [], quota_used=quota("quota_used", operations=129)
    ),
    "files beyond the store limit": observed([], quota_used=quota("quota_used", files=4097)),
    "payload beyond the store limit": observed(
        [], quota_used=quota("quota_used", payload_bytes=16 * 1024 * 1024 + 1)
    ),
    "added payload beyond the store limit": observed(
        [], quota_added=quota("quota_added", payload_bytes=16 * 1024 * 1024 + 1)
    ),
    "a negative count": observed([], quota_used=quota("quota_used", files=-1)),
    "unknown field inside the quota": observed([], quota_used=quota("quota_used", extra=1)),
    # the plan
    "plan id without digest": observed([], plan_id=PLAN_ID),
    "plan digest without id": observed([], plan_digest="a" * 64),
    "plan while blocked": observed(
        ["drift_missing"], MISSING, plan_id=PLAN_ID, plan_digest="a" * 64
    ),
    # the related operation
    "related operation without a descendant blocker": observed([], related_operation_id=OTHER),
    "superseded without its successor": unobserved(["source_superseded"]),
    "a source that succeeds itself": unobserved(
        ["source_superseded"], related_operation_id=OPERATION
    ),
    "a payload below the per-plan allowance": observed(
        [], quota_added=quota("quota_added", payload_bytes=16 * 1024 - 1)
    ),
    "an unreliable listing beside confirmed files without the class": observed(
        ["inventory_unreliable"], counts(confirmed=3)
    ),
    "an unreliable and too large listing beside confirmed files": observed(
        ["inventory_unreliable", "inventory_too_large"], counts(confirmed=3)
    ),
    # plain fields
    "malformed observation instant": observed([], observed_at="yesterday"),
    "uppercase digest": inside(observed(), classification_digest="C" * 64),
    "short digest": inside(observed(), inventory_digest="d" * 63),
    "bad source id": observed([], source_operation_id="x"),
    "bad dataset id": observed([], dataset_id="x"),
    "empty manifest": observed([], file_count=0),
    "more files than an upload holds": observed([], file_count=129),
    "wrong version": observed([], schema_version=2),
    "wrong kind": observed([], kind="dataset_upload_summary"),
    "unknown field": observed([], extra=1),
    "unknown field inside the observation": inside(observed(), extra=1),
}


@pytest.mark.parametrize("name", NEGATIVES)
def test_every_closed_report_negative_is_rejected(name):
    rejects(NEGATIVES[name])


def test_the_isolated_negatives_differ_from_valid_reports_by_the_one_rule_they_pin():
    accepts(observed([]))
    accepts(observed([], dataset_id=DATASET))
    accepts(observed(["inventory_unreliable"], counts(inventory_unreliable=3)))
    accepts(
        observed(["inventory_unreliable", "inventory_too_large"], counts(inventory_unreliable=3))
    )
    accepts(
        observed(["conflict", "inventory_unreliable"], counts(conflict=1, inventory_unreliable=2))
    )
    accepts(
        observed(["drift_missing", "conflict"], counts(confirmed=1, drift_missing=1, conflict=1))
    )
    accepts(observed(["drift_missing"], counts(drift_missing=3)))
    accepts(observed(["conflict"], counts(conflict=3)))
    accepts(observed(["membership_unobserved", "local_changed"]))
    accepts(observed([], quota_added=quota("quota_added", payload_bytes=16 * 1024)))
    accepts(unobserved())
    accepts(unobserved(["source_terminal"]))
    accepts(unobserved(["source_superseded"], related_operation_id=OTHER))
    accepts(unobserved(["create_unknown", "known_negative"]))
    accepts(
        inside(
            observed([], counts(confirmed=2, pending_uncertain=1)),
            send_files=1,
            send_bytes=3,
            unconfirmed_ack_required=True,
        )
    )
    accepts(inside(observed([], counts(confirmed=2, pending_clean=1)), send_files=1, send_bytes=3))
    accepts(listed(LISTED))
    accepts(
        inside(
            observed(
                ["drift_missing", "conflict"], counts(confirmed=1, drift_missing=1, conflict=1)
            ),
            examples=[
                {"file_class": "drift_missing", "paths": ["a.txt"]},
                {"file_class": "conflict", "paths": ["a.txt"]},
            ],
        )
    )
    accepts(
        inside(
            observed(["drift_missing"], counts(drift_missing=3)),
            examples=[{"file_class": "drift_missing", "paths": ["a.txt", "empty.bin"]}],
        )
    )


def test_nothing_observed_is_a_report_too_for_every_blocker_that_needs_no_inventory():
    for blocker in BLOCKERS:
        related = OTHER if blocker in WAITING else None
        value = unobserved([blocker], related_operation_id=related)
        if blocker in INVENTORY:
            rejects(value)
        else:
            assert accepts(value).observation is None


@pytest.mark.parametrize(
    "path", ["/abs.txt", "../up.txt", "a\\b.txt", "a/../b.txt", "x" * 2000, ""]
)
def test_example_paths_must_be_portable_relative_paths(path):
    rejects(listed({"file_class": "drift_missing", "paths": [path]}))


def test_example_paths_are_ordered_distinct_and_at_most_eight():
    def many(paths):
        value = observed(["drift_missing"], counts(drift_missing=12), file_count=12)
        value["quota_added"] = quota("quota_added", files=12)
        return inside(value, examples=[{"file_class": "drift_missing", "paths": paths}])

    eight = [f"f{n}.bin" for n in range(8)]
    assert len(accepts(many(eight)).observation.examples[0].paths) == MAX_EXAMPLES == 8
    for paths in ([*eight, "f8.bin"], ["b.bin", "a.bin"], ["a.bin", "a.bin"]):
        rejects(many(paths))


def test_the_four_problem_classes_are_the_ones_a_user_must_act_on():
    assert PROBLEM_CLASSES == (
        "pending_uncertain",
        "drift_missing",
        "conflict",
        "inventory_unreliable",
    )


@pytest.mark.parametrize("blocker", BLOCKERS)
def test_every_single_blocker_yields_the_reference_action(blocker):
    names = (
        ["inventory_unreliable", "inventory_too_large"]
        if blocker == "inventory_too_large"
        else [blocker]
    )
    classes = {
        "drift_missing": counts(confirmed=2, drift_missing=1),
        "conflict": counts(confirmed=2, conflict=1),
        "inventory_unreliable": counts(inventory_unreliable=3),
        "inventory_too_large": counts(inventory_unreliable=3),
    }.get(blocker, counts(confirmed=3))
    related = OTHER if blocker in WAITING else None
    if blocker in JOURNAL:  # nothing is read for these, so there is nothing to observe
        value = unobserved(names, related_operation_id=related)
    else:
        value = observed(names, classes, related_operation_id=related, dataset_id=DATASET)
    report = accepts(value)
    assert report.recommended_action == recommended_action(tuple(names)) and not report.eligible


def test_the_worst_legal_report_fits_the_wire_limit_that_the_old_one_would_not():
    # Three problem classes stand together (an unreliable listing excludes the others). Each lists
    # eight paths of the longest legal form: four 255-byte components of two-byte characters, a
    # path that escapes to three times its size in canonical JSON.
    def path(k):
        first = chr(0xE0 + k) * 127 + "a"
        return "/".join([first] + ["é" * 127 + "a"] * 3)

    paths = [path(k) for k in range(24)]
    assert max(len(p.encode()) for p in paths) <= 1024
    classes = ("pending_uncertain", "drift_missing", "conflict")
    value = observed(
        ["drift_missing", "conflict"],
        counts(pending_uncertain=8, drift_missing=8, conflict=8),
        file_count=24,
    )
    value["quota_added"] = quota("quota_added", files=24)
    value["observation"].update(
        send_files=8,
        send_bytes=8,
        unconfirmed_ack_required=True,
        examples=[
            {"file_class": name, "paths": paths[8 * i : 8 * i + 8]}
            for i, name in enumerate(classes)
        ],
    )
    report = accepts(value)
    size = len(report.encoded())
    assert 64 * 1024 < size < DatasetUploadResumeReport.max_wire_bytes
    assert len(json.dumps(value, ensure_ascii=False).encode()) < size  # canonical form is larger


def test_the_report_wire_limit_holds_at_the_byte():
    limit = DatasetUploadResumeReport.max_wire_bytes
    assert limit == 128 * 1024
    raw = fixture(ELIGIBLE)
    DatasetUploadResumeReport.model_validate_json(raw + b" " * (limit - len(raw)))
    with pytest.raises(ValueError, match="bounded upload wire"):
        DatasetUploadResumeReport.model_validate_json(raw + b" " * (limit - len(raw) + 1))


# --- the report built from real evidence ---------------------------------------------------------
def classified(*, states, present=(), faults=()):
    chain = ChainSummary(states, False, False, MANIFEST.digest)
    items = tuple(
        RemoteItem(f.path, f.size, f.sha256, f"item-{i}")
        for i, f in enumerate(MANIFEST.files)
        if i in present
    )
    return classify(MANIFEST, chain, RemoteInventory(items, frozenset(faults)))


def build(classification, **changes):
    values = {
        "source_operation_id": OPERATION,
        "dataset_id": DATASET,
        "manifest": MANIFEST,
        "classification": classification,
        "quota_used": QUOTA,
        "added_payload_bytes": 82000,
        "observed_at": "2026-11-02T11:00:00.000000Z",
    }
    return resume_report(**{**values, **changes})


SCENARIOS = [
    (states, present, faults)
    for states in itertools.product(("none", "intent", "accepted"), repeat=3)
    for present in itertools.chain.from_iterable(
        itertools.combinations(range(3), r) for r in range(4)
    )
    for faults in ((), ("cursor_loop",))
]


def test_a_report_can_be_built_from_every_classification_the_classifier_can_give():
    eligible = 0
    for states, present, faults in SCENARIOS:
        classification = classified(states=states, present=present, faults=faults)
        report = build(classification)
        observation = report.observation
        assert report.blockers == classification.blockers
        assert report.eligible == classification.plannable
        assert report.recommended_action == recommended_action(classification.blockers)
        assert observation.class_counts.model_dump() == {
            name: classification.count(name) for name in FILE_CLASSES
        }
        assert observation.classification_digest == classification.classification_digest
        assert observation.inventory_digest == classification.inventory_digest
        sending = [
            i
            for i, name in enumerate(classification.classes)
            if name in ("pending_clean", "pending_uncertain")
        ]
        assert observation.send_files == len(sending)
        assert observation.send_bytes == sum(MANIFEST.files[i].size for i in sending)
        assert observation.unconfirmed_ack_required == bool(
            classification.count("pending_uncertain")
        )
        for example in observation.examples:
            wanted = [MANIFEST.files[i].path for i in classification.indices(example.file_class)]
            assert list(example.paths) == wanted[:MAX_EXAMPLES]
        assert accepts(json.loads(report.encoded())).encoded() == report.encoded()
        selection = classification.selection()
        if selection is not None:
            eligible += 1
            assert observation.send_files == len(selection.file_indices)
    assert (len(SCENARIOS), eligible) == (432, 125)


def test_blockers_the_caller_merged_in_are_reported_and_withdraw_the_plan():
    classification = classified(states=("none", "none", "intent"), present=(1,))
    assert build(classification).eligible
    merged = classification.with_blockers(("local_changed", "membership_unobserved"))
    report = build(merged)
    assert report.blockers == ("membership_unobserved", "local_changed") == merged.blockers
    assert not report.eligible and report.recommended_action == recommended_action(merged.blockers)
    assert report.observation.send_files == 2  # informational while blocked
    # A blocker the journal alone establishes means nothing was read: it cannot ride on evidence.
    for blocker in sorted(JOURNAL):
        held = classification.with_blockers((blocker,))
        with pytest.raises(ValueError, match="journal-level blocker"):
            build(
                held,
                related_operation_id=OTHER if blocker in WAITING else None,
                dataset_id=None if blocker == "create_unknown" else DATASET,
            )


def test_a_report_of_nothing_observed_is_the_golden_and_cannot_hide_remote_blockers():
    report = resume_report(
        source_operation_id=OPERATION,
        dataset_id=None,
        manifest=MANIFEST,
        classification=None,
        blockers=("create_unknown",),
        quota_used=QUOTA,
        added_payload_bytes=82000,
        observed_at="2026-11-02T11:00:00.000000Z",
    )
    assert report.encoded() == fixture(UNOBSERVED)
    for blockers in ((), ("drift_missing",), ("conflict", "extra_remote")):
        with pytest.raises((ValidationError, ValueError)):
            resume_report(
                source_operation_id=OPERATION,
                dataset_id=DATASET,
                manifest=MANIFEST,
                classification=None,
                blockers=blockers,
                quota_used=QUOTA,
                added_payload_bytes=1,
                observed_at="2026-11-02T11:00:00.000000Z",
            )


class Imitation(DatasetContinuationPlanV3):
    pass


def changed_manifest():
    data_ = json.loads(fixture("dataset-manifest-v1.json"))
    del data_["digest"]
    data_["files"][0]["size"] += 1  # file 0 is unsent in the scenario, so evidence stays equal
    data_["total_bytes"] += 1
    digest = hashlib.sha256(canonical_manifest(data_)).hexdigest()
    return DatasetManifest.model_validate_json(canon({**data_, "digest": digest}))


def prepared_from(classification):
    binding = continuation_binding(
        classification,
        source_operation_id=OPERATION,
        baseline_operation_id=OPERATION,
        dataset_id=DATASET,
        baseline_digest="b" * 64,
        intent_digest=PLAN.intent_digest(),
        observed_at="2026-11-02T11:00:00.000000Z",
    )
    work = ContinuationCostWork(
        scope=PLAN.scope,
        root=PLAN.root,
        manifest=PLAN.manifest,
        parameters=PLAN.parameters,
        storage=PLAN.storage,
        request_limits=continuation_limits(MANIFEST, binding.file_indices),
        execution_window=PLAN.execution_window,
    )
    return prepare_continuation_v3(
        ContinuationPreparation(
            plan_id=PLAN.plan_id,
            work=work,
            manifest=MANIFEST,
            binding=binding,
            admission_policy=PLAN.admission_policy,
            cost_policy=PLAN.cost_policy,
            budget_micros=PLAN.budget_micros,
            inputs_verified=True,
            grant=None,
            cost_bound=None,
            prepared_at=PLAN.prepared_at,
        )
    )


def test_the_plan_a_report_names_is_the_one_prepared_from_that_very_observation():
    classification = classified(states=("none", "none", "intent"), present=(1,))
    plan = prepared_from(classification)
    report = build(classification, plan=plan)
    assert (report.plan_id, report.plan_digest) == (plan.plan_id, plan.digest)
    assert report.observation.send_files == plan.request_limits.files
    other = classified(states=("none", "none", "none"))
    for changes in (
        {"plan": prepared_from(other)},  # prepared from another observation
        {"source_operation_id": OTHER},
        {"dataset_id": "00000000-0000-4000-8000-0000000009aa"},
        # Nothing observed, yet a plan: the dataset and the source agree, only the plan is foreign.
        {"classification": None, "blockers": ("source_terminal",)},
        {"manifest": changed_manifest()},  # same file count, another manifest
        {"plan": PLAN.model_dump(mode="json")},
        {"plan": Imitation.model_construct(**dict(plan))},
        {"classification": classification.with_blockers(("local_changed",))},
        {"plan": PLAN},  # the golden plan binds placeholder digests, not this evidence
    ):
        values = {"classification": classification, "plan": plan, **changes}
        with pytest.raises((ValidationError, ValueError)):
            build(values.pop("classification"), **values)


def test_examples_are_the_first_eight_paths_of_each_problem_class():
    data_ = json.loads(fixture("dataset-manifest-v1.json"))
    del data_["digest"]
    data_["files"] = [
        {"path": f"f{n:02d}.bin", "sha256": hashlib.sha256(b"%d" % n).hexdigest(), "size": 2}
        for n in range(12)
    ]
    data_["file_count"], data_["total_bytes"] = 12, 24
    digest = hashlib.sha256(canonical_manifest(data_)).hexdigest()
    manifest = DatasetManifest.model_validate_json(canon({**data_, "digest": digest}))
    chain = ChainSummary(("intent",) * 12, False, False, manifest.digest)
    classification = classify(manifest, chain, RemoteInventory((), frozenset()))
    assert classification.count("pending_uncertain") == 12
    report = build(classification, manifest=manifest)
    (example,) = report.observation.examples
    assert example.file_class == "pending_uncertain"
    assert list(example.paths) == [f"f{n:02d}.bin" for n in range(8)]
    assert report.observation.send_files == 12 and report.observation.send_bytes == 24
    assert report.file_count == report.quota_added.files == 12


def test_a_report_builder_refuses_evidence_that_does_not_belong_together():
    classification = classified(states=("none", "none", "intent"), present=(1,))
    with pytest.raises(ValueError, match="already carries every blocker"):
        build(classification, blockers=("source_terminal",))
    shorter = MANIFEST.model_copy(update={"files": MANIFEST.files[:2]})
    with pytest.raises(ValueError, match="does not cover"):
        build(classification, manifest=shorter)


def test_the_report_wire_carries_no_private_field():
    names = (
        set(DatasetUploadResumeReport.model_fields)
        | set(ResumeObservation.model_fields)
        | set(ResumeClassCounts.model_fields)
        | set(ResumeExamples.model_fields)
        | set(QuotaCounters.model_fields)
    )
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
            "baseline_digest",
            "extra_paths",
            "item_ids",
        }
    )
    text = (fixture(BLOCKED) + fixture(ELIGIBLE) + fixture(UNOBSERVED)).decode()
    for needle in ("created_dataset", "object_key", "receipt", "http", "owner"):
        assert needle not in text


# --- the shape: every key is required, every bound is a bound ------------------------------------
def deletions(value, path=()):
    """Every way to drop one key of one object, anywhere inside a JSON value."""
    if isinstance(value, dict):
        for key in value:
            yield (*path, key)
            yield from deletions(value[key], (*path, key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from deletions(item, (*path, index))


def without(value, path):
    copy = json.loads(json.dumps(value))
    node = copy
    for key in path[:-1]:
        node = node[key]
    del node[path[-1]]
    return copy


@pytest.mark.parametrize("name", [BLOCKED, ELIGIBLE, UNOBSERVED])
def test_no_key_of_a_report_may_be_left_out_not_even_a_nullable_one(name):
    value = data(name)
    paths = list(deletions(value))
    assert len(paths) >= 20  # a nothing-observed report has the fewest keys
    for path in paths:
        rejects(without(value, path))


def test_no_key_of_the_summary_may_be_left_out_not_even_a_nullable_one():
    value = data(SUMMARY)
    for path in deletions(value):
        with pytest.raises((ValidationError, ValueError)):
            DatasetUploadSummaryV3.model_validate_json(canon(without(value, path)))


def test_a_summary_may_leave_every_sent_file_uncertain_and_names_its_own_plan_schema():
    summary = DatasetUploadSummaryV3.model_validate_json(
        canon(summary_of(continuation_files=2, uncertain_files=2))
    )
    assert summary.uncertain_files == summary.continuation_files == 2
    with pytest.raises((ValidationError, ValueError)):
        DatasetUploadSummaryV3.model_validate_json(canon(summary_of(source_plan_schema=1)))


def test_every_count_of_the_report_starts_at_zero_and_never_goes_below():
    for which in ("quota_used", "quota_added"):
        for field in ("plans", "operations", "files", "payload_bytes"):
            low = {**data(BLOCKED)[which], field: -1}
            rejects(observed([], **{which: low}))
    zero = {"plans": 0, "operations": 0, "files": 0, "payload_bytes": 0}
    accepts(observed([], quota_used=zero))
    for name in FILE_CLASSES:
        rejects(observed([], {**counts(confirmed=3), name: -1}))
    rejects(inside(observed(), send_bytes=-1))
    rejects(inside(observed(), send_files=-1))


def test_the_send_selection_is_exactly_the_unsent_and_the_unconfirmed():
    unsent = counts(confirmed=2, pending_clean=1)
    accepts(inside(observed([], unsent), send_files=1, send_bytes=1))
    rejects(inside(observed([], unsent), send_files=0, send_bytes=0))  # one file is not counted
    rejects(inside(observed([], unsent), send_files=2, send_bytes=1))
    rejects(inside(observed(), send_bytes=1))  # a byte with no file to carry it
    rejects(inside(observed([], unsent), send_files=1, send_bytes=1, unconfirmed_ack_required=True))


def test_the_manifest_size_of_a_report_is_one_to_one_hundred_and_twenty_eight_files():
    def sized(count, classes):
        value = observed([], classes, file_count=count)
        value["quota_added"] = quota("quota_added", files=count)
        return value

    accepts(sized(1, counts(confirmed=1)))
    accepts(sized(128, counts(confirmed=128)))
    rejects(sized(0, counts()))  # every other rule holds for an empty manifest
    rejects(sized(129, counts(confirmed=128, observed=1)))


def test_identifiers_digests_and_the_nothing_observed_blocker_are_checked_on_their_own():
    rejects(
        observed(["source_superseded"], related_operation_id=OTHER.upper()) | {"observation": None}
    )
    rejects(observed([], plan_id=OTHER.upper(), plan_digest="a" * 64))
    rejects(observed([], plan_id=PLAN_ID, plan_digest="X" * 64))
    rejects(observed([], plan_id=PLAN_ID, plan_digest="a" * 63))
    rejects(unobserved(["extra_remote"], dataset_id=DATASET))  # extra remote items need a listing
    rejects(unobserved(["inventory_too_large"]))


def test_the_instant_a_report_is_built_at_passes_through():
    classification = classified(states=("none", "none", "intent"), present=(1,))
    moment = "2026-11-02T11:00:01.000000Z"
    assert build(classification, observed_at=moment).observed_at == moment
    assert build(classification, quota_used=QUOTA).quota_used == QUOTA
    assert build(classification, added_payload_bytes=20000).quota_added.payload_bytes == 20000


# --- the golden reports are what the builder gives for their scenarios ---------------------------
def test_the_observed_goldens_are_what_the_builder_gives_for_their_scenarios():
    # The goldens carry digests the independent generator computed from the reference's preimages.
    scenarios = {
        BLOCKED: dict(states=("accepted", "accepted", "none"), present=(1,)),
        ELIGIBLE: dict(states=("none", "none", "intent"), present=(1,)),
    }
    for name, scenario in scenarios.items():
        classification = classified(**scenario)
        assert build(classification).encoded() == fixture(name)
        digests = data(name)["observation"]
        assert digests["classification_digest"] == classification.classification_digest
        assert digests["inventory_digest"] == classification.inventory_digest


def test_remote_names_ids_and_hashes_never_reach_the_report():
    foreign = RemoteItem("SECRET/EXTRA.bin", 987654321, "ab" * 32, "SECRETITEM-1")
    first = MANIFEST.files[0]
    clash = RemoteItem(first.path, first.size + 1, first.sha256, "SECRETITEM-2")
    chain = ChainSummary(("none", "none", "none"), False, False, MANIFEST.digest)
    classification = classify(MANIFEST, chain, RemoteInventory((foreign, clash), frozenset()))
    assert {"conflict", "extra_remote"} <= set(classification.blockers)
    text = build(classification).encoded().decode()
    for needle in ("SECRET", "987654321", "ab" * 32, "item-", "ITEM"):
        assert needle not in text
    assert "extra_remote" in text  # the blocker's name is all a foreign item leaves behind


def test_the_builder_refuses_what_is_not_the_evidence_it_asks_for():
    classification = classified(states=("none", "none", "intent"), present=(1,))
    for changes in (
        {"manifest": None},
        {"manifest": {}},
        {"classification": {}},
        {"blockers": None},
        {"blockers": "create_unknown"},
    ):
        values = {"classification": classification, **changes}
        with pytest.raises(ValueError, match="manifest, a classification or none"):
            build(values.pop("classification"), **values)
    # Same file count, another manifest: only the identity inside the classification can tell.
    other = changed_manifest()
    assert len(other.files) == len(MANIFEST.files) and other.digest != MANIFEST.digest
    with pytest.raises(ValueError, match="another manifest"):
        build(classification, manifest=other)


def test_a_plan_is_named_only_by_the_report_of_the_very_instant_it_was_prepared_from():
    classification = classified(states=("none", "none", "intent"), present=(1,))
    plan = prepared_from(classification)
    assert plan.continuation.observed_at == "2026-11-02T11:00:00.000000Z"
    assert build(classification, plan=plan).plan_id == plan.plan_id
    with pytest.raises(ValueError, match="not prepared from this observation"):
        build(classification, plan=plan, observed_at="2026-11-02T11:00:01.000000Z")


@pytest.mark.parametrize("blocker", sorted(JOURNAL))
def test_a_journal_level_blocker_means_nothing_was_read(blocker):
    related = OTHER if blocker in WAITING else None
    dataset = None if blocker == "create_unknown" else DATASET
    accepts(unobserved([blocker], related_operation_id=related))
    rejects(observed([blocker], related_operation_id=related, dataset_id=dataset))
