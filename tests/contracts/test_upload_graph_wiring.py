"""Call sites that now read the stage graph specification equal their pre-refactor formulas."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from yorunge.adapters import upload_original
from yorunge.adapters.upload_original import _Environment
from yorunge.adapters.upload_preparation import _limits
from yorunge.adapters.upload_repository import _arm_input
from yorunge.adapters.upload_store import (
    _receipt,
    _receipt_key,
    acknowledged_stages,
    request_digest,
)
from yorunge.domain.capabilities import canonical
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_transfer import StageIntent, StageReceipt
from yorunge.domain.dataset_upload import DatasetUploadPlan
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_costs import UploadRequestLimits
from yorunge.domain.upload_graph import STAGE_KINDS, StageGraphSpec
from yorunge.domain.upload_requests import upload_request_digest
from yorunge.domain.upload_versions import graph_of

FIXTURES = Path(__file__).parents[1] / "fixtures"
V1_PLAN = DatasetUploadPlan.model_validate_json(
    canonical(json.loads((FIXTURES / "dataset-upload-approved-v1.json").read_bytes())["plan"])
)
V2_PLAN = DatasetUploadPlanV2.model_validate_json(
    (FIXTURES / "dataset-upload-plan-v2.json").read_bytes()
)
MANIFEST = DatasetManifest.model_validate_json((FIXTURES / "dataset-manifest-v1.json").read_bytes())
INTENT = json.loads((FIXTURES / "dataset-transfer-journal-v1.json").read_bytes())["intent"]


@pytest.mark.parametrize("plan,version", [(V1_PLAN, 1), (V2_PLAN, 2)])
def test_graph_of_real_stored_plans_reads_their_version_and_file_count(plan, version):
    graph = graph_of(plan)
    assert graph == StageGraphSpec(version, plan.manifest.file_count)
    assert graph.plan_version == plan.schema_version == version
    assert graph.intent_count == 2 + 3 * plan.manifest.file_count


# --- frozen pre-refactor predicates ------------------------------------------------------------
def frozen_arm_input_invalid(kind, index):
    return (
        type(kind) is not str
        or kind not in {"create", "project_link", "presign", "put", "confirm"}
        or (kind in {"create", "project_link"}) != (index is None)
    )


@pytest.mark.parametrize("kind", [*STAGE_KINDS, "bogus", "", None, 3, ["put"]])
@pytest.mark.parametrize("index", [None, 0, 127, -1, 128, True, "0"])
def test_arm_input_kind_and_index_pairing_equals_the_frozen_predicate(kind, index):
    if frozen_arm_input_invalid(kind, index):
        with pytest.raises(YorungeError) as raised:
            _arm_input(kind, index, 100.0)
        assert raised.value.code == "invalid_request"
    else:
        _arm_input(kind, index, 100.0)


@pytest.mark.parametrize("kind", STAGE_KINDS)
@pytest.mark.parametrize("index", [None, 0, 5])
def test_stage_intent_file_index_pairing_equals_the_frozen_predicate(kind, index):
    old_invalid = (kind in {"create", "project_link"}) != (index is None)
    body = {**INTENT, "kind": kind, "file_index": index}
    if old_invalid:
        with pytest.raises(ValueError, match="stage file index mismatch"):
            StageIntent.model_validate(body)
    else:
        assert StageIntent.model_validate(body).kind == kind


def frozen_limits(file_count, total_bytes):
    return UploadRequestLimits(
        max_create=1,
        max_project_link=1,
        max_presign=file_count,
        max_put=file_count,
        max_confirm=file_count,
        max_read_requests=512,
        max_read_attempts=1024,
        max_control_request_bytes=4194304,
        max_control_response_bytes=16777216,
        max_upload_bytes=total_bytes,
    )


def test_prepared_request_limits_equal_the_frozen_construction_for_all_file_counts():
    for count in range(1, 129):
        manifest = SimpleNamespace(file_count=count, total_bytes=count * 7)
        assert _limits(manifest) == frozen_limits(count, count * 7)


def frozen_request_digest(plan, manifest, kind, index, receipts):
    create = receipts.get(("create", None))
    previous = receipts.get(("presign", index)) if index is not None else None
    return upload_request_digest(
        plan.digest,
        kind,
        index,
        manifest.files[index] if index is not None else None,
        create.dataset_id if kind != "create" and create else None,
        previous.object_key if kind in {"put", "confirm"} and previous else None,
    )


@pytest.mark.parametrize("plan", [V1_PLAN, V2_PLAN])
def test_request_digest_binding_sources_equal_the_frozen_formula(plan):
    create = SimpleNamespace(dataset_id="00000000-0000-4000-8000-000000000909", object_key=None)
    presign = SimpleNamespace(dataset_id=create.dataset_id, object_key="objects/blob-1")
    for receipts in (
        {},
        {("create", None): create},
        {("create", None): create, ("presign", 0): presign},
    ):
        for kind in STAGE_KINDS:
            index = None if kind in {"create", "project_link"} else 0
            assert request_digest(plan, MANIFEST, kind, index, receipts) == frozen_request_digest(
                plan, MANIFEST, kind, index, receipts
            )


def frozen_receipt_key(kind, index, receipt, accepted):
    expected_key = accepted[("presign", index)].object_key if kind in {"put", "confirm"} else None
    if kind in {"presign", "put", "confirm"}:
        if receipt.object_key is None or (
            expected_key is not None and receipt.object_key != expected_key
        ):
            raise ValueError("receipt object key mismatch")
    elif receipt.object_key is not None:
        raise ValueError("unexpected receipt key")


@pytest.mark.parametrize("kind", STAGE_KINDS)
@pytest.mark.parametrize("key", [None, "objects/blob-1", "objects/other"])
def test_receipt_object_key_binding_equals_the_frozen_rule(kind, key):
    index = None if kind in {"create", "project_link"} else 0
    accepted = {("presign", 0): SimpleNamespace(object_key="objects/blob-1")}
    receipt = SimpleNamespace(object_key=key)
    graph = graph_of(V2_PLAN)
    try:
        frozen_receipt_key(kind, index, receipt, accepted)
    except ValueError as expected:
        with pytest.raises(ValueError, match=str(expected)):
            _receipt_key(graph, kind, index, receipt, accepted)
    else:
        _receipt_key(graph, kind, index, receipt, accepted)


# --- receipt dataset binding and journal completeness ------------------------------------------
DATASET = "00000000-0000-4000-8000-000000000909"
OTHER_DATASET = "00000000-0000-4000-8000-000000000808"
OBJECT_KEY = "objects/blob-1"


def stage_receipt(intent, dataset_id):
    file = MANIFEST.files[0] if intent.kind == "put" else None
    return StageReceipt(
        schema_version=1,
        intent_id=intent.intent_id,
        recorded_at=intent.intended_at,
        result="accepted",
        dataset_id=dataset_id,
        object_key=OBJECT_KEY if intent.kind in {"presign", "put", "confirm"} else None,
        sent_bytes=file.size if file else None,
        sent_sha256=file.sha256 if file else None,
    )


@pytest.mark.parametrize("plan", [V1_PLAN, V2_PLAN])
@pytest.mark.parametrize("kind", STAGE_KINDS)
def test_receipt_dataset_binding_equals_the_frozen_rule(plan, kind):
    index = None if kind in {"create", "project_link"} else 0
    intent = StageIntent.model_validate({**INTENT, "kind": kind, "file_index": index})
    accepted = {
        ("create", None): SimpleNamespace(dataset_id=DATASET),
        ("presign", 0): SimpleNamespace(object_key=OBJECT_KEY),
    }
    _receipt(plan, MANIFEST, intent, stage_receipt(intent, DATASET), accepted)
    mismatch = stage_receipt(intent, OTHER_DATASET)
    if kind == "create":
        # The create receipt defines the dataset id; there is no earlier receipt to compare with.
        _receipt(plan, MANIFEST, intent, mismatch, {})
    else:
        with pytest.raises(ValueError, match="receipt dataset mismatch"):
            _receipt(plan, MANIFEST, intent, mismatch, accepted)


def frozen_acknowledged(plan, view):
    count = plan.manifest.file_count
    return (
        {(i.kind, i.file_index) for i in view.intents} == frozen_required_stages(count)
        and len(view.intents) == 2 + 3 * count
        and len(view.receipts) == len(view.intents)
        and all(r.result == "accepted" for r in view.receipts)
    )


def frozen_required_stages(count):
    stages = {("create", None), ("project_link", None)}
    stages.update((kind, i) for i in range(count) for kind in ("presign", "put", "confirm"))
    return stages


def journal_view(plan, stages, results=None):
    results = results or {}
    return SimpleNamespace(
        plan=plan,
        intents=[SimpleNamespace(kind=kind, file_index=index) for kind, index in stages],
        receipts=[
            SimpleNamespace(result=results.get(position, "accepted"))
            for position in range(len(stages))
        ],
    )


@pytest.mark.parametrize("plan", [V1_PLAN, V2_PLAN])
def test_acknowledged_stages_needs_exactly_the_required_set_with_every_receipt_accepted(plan):
    count = plan.manifest.file_count
    full = [
        ("create", None),
        ("project_link", None),
        *[(kind, i) for i in range(count) for kind in ("presign", "put", "confirm")],
    ]
    duplicate_replaces_stage = [*full[:-1], full[-2]]
    unknown_file_replaces_stage = [*full[:-1], ("confirm", count)]
    cases = [
        (journal_view(plan, full), True),
        (journal_view(plan, full[:-1]), False),
        # Same intent count, different stage set: only the set comparison can tell them apart.
        (journal_view(plan, duplicate_replaces_stage), False),
        (journal_view(plan, unknown_file_replaces_stage), False),
        # Same stage set, one intent too many: only the intent count can tell them apart.
        (journal_view(plan, [*full, full[-1]]), False),
        (
            SimpleNamespace(
                plan=plan,
                intents=journal_view(plan, full).intents,
                receipts=journal_view(plan, full).receipts[:-1],
            ),
            False,
        ),
        (journal_view(plan, full, {3: "rejected"}), False),
    ]
    for view, expected in cases:
        assert acknowledged_stages(view) is expected
        assert frozen_acknowledged(plan, view) is expected


# --- upload environment index guards -----------------------------------------------------------
def environment(uploads=None):
    env = _Environment(None, V2_PLAN, None, None, None, None, None, 0.0)
    env.record = SimpleNamespace(operation_id="op", dataset_id=DATASET)
    env.contexts = ("file-0", "file-1", "file-2")
    env.uploads = uploads or {}
    return env


def test_environment_context_only_serves_indices_of_the_plan():
    env = environment()
    assert V2_PLAN.manifest.file_count == 3
    assert [env._context(i) for i in range(3)] == ["file-0", "file-1", "file-2"]
    for index in (None, 3, 127, -1, True, "0"):
        with pytest.raises(YorungeError) as raised:
            env._context(index)
        assert raised.value.code == "invalid_request"


def test_environment_requires_exactly_one_presigned_upload_per_plan_file(monkeypatch):
    seen = []
    monkeypatch.setattr(
        upload_original.descriptors, "distinct_uploads", lambda *args: seen.append(args)
    )
    environment({0: "a", 1: "b", 2: "c"}).validate_uploads()
    assert len(seen) == 1
    for uploads in ({0: "a", 1: "b"}, {0: "a", 1: "b", 2: "c", 3: "d"}, {1: "a", 2: "b", 3: "c"}):
        with pytest.raises(YorungeError) as raised:
            environment(uploads).validate_uploads()
        assert raised.value.code == "invalid_response"
    assert len(seen) == 1
