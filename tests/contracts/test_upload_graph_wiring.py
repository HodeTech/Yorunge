"""Call sites that now read the stage graph specification equal their pre-refactor formulas."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from yorunge.adapters.upload_preparation import _limits
from yorunge.adapters.upload_repository import _arm_input
from yorunge.adapters.upload_store import _receipt_key, request_digest
from yorunge.domain.capabilities import canonical
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_transfer import StageIntent
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
