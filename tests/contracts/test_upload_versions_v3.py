"""A continuation is a family of its own: helpers name it, decoders list it, nothing guesses."""

import json
from itertools import product
from pathlib import Path
from types import SimpleNamespace
from typing import get_args

import pytest

from yorunge.adapters.upload_store import VersionedTransferView, decode_versioned, validate_graph
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3, DatasetUploadApprovalV3
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_transfer import (
    StageIntent,
    TransferControl,
    TransferRecord,
    TransferVerification,
)
from yorunge.domain.dataset_transfer_v2 import (
    TransferControlV2,
    TransferRecordV2,
    TransferVerificationV2,
)
from yorunge.domain.dataset_transfer_v3 import (
    TransferControlV3,
    TransferRecordV3,
    TransferVerificationV3,
)
from yorunge.domain.dataset_upload import DatasetUploadApproval, DatasetUploadPlan
from yorunge.domain.dataset_upload_v2 import DatasetUploadApprovalV2, DatasetUploadPlanV2
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_graph import StageGraphSpec
from yorunge.domain.upload_versions import (
    UploadApproval,
    UploadControl,
    UploadPlan,
    UploadRecord,
    UploadVerification,
    graph_of,
    validate_create_receipt,
    validate_versioned_approval,
    verification_scope,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"


def fixture(name):
    return (FIXTURES / name).read_bytes()


def canon(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode()


V1_PAIR = json.loads(fixture("dataset-upload-approved-v1.json"))
V2_PAIR = json.loads(fixture("dataset-upload-approved-v2.json"))
PLANS = {
    1: DatasetUploadPlan.model_validate_json(canon(V1_PAIR["plan"])),
    2: DatasetUploadPlanV2.model_validate_json(canon(V2_PAIR["plan"])),
    3: DatasetContinuationPlanV3.model_validate_json(fixture("dataset-continuation-plan-v3.json")),
}
APPROVALS = {
    1: DatasetUploadApproval.model_validate_json(canon(V1_PAIR["approval"])),
    2: DatasetUploadApprovalV2.model_validate_json(canon(V2_PAIR["approval"])),
    3: DatasetUploadApprovalV3.model_validate_json(
        fixture("dataset-continuation-approval-v3.json")
    ),
}
GRAPH = json.loads(fixture("dataset-transfer-graph-v2.json"))
MANIFEST = DatasetManifest.model_validate_json(fixture("dataset-manifest-v1.json"))


def test_each_union_names_exactly_its_three_families_in_order():
    assert get_args(UploadPlan) == (
        DatasetUploadPlan,
        DatasetUploadPlanV2,
        DatasetContinuationPlanV3,
    )
    assert get_args(UploadApproval) == (
        DatasetUploadApproval,
        DatasetUploadApprovalV2,
        DatasetUploadApprovalV3,
    )
    assert get_args(UploadRecord) == (TransferRecord, TransferRecordV2, TransferRecordV3)
    assert get_args(UploadControl) == (TransferControl, TransferControlV2, TransferControlV3)
    assert get_args(UploadVerification) == (
        TransferVerification,
        TransferVerificationV2,
        TransferVerificationV3,
    )


@pytest.mark.parametrize("plan_version,approval_version", list(product((1, 2, 3), repeat=2)))
def test_an_approval_belongs_only_to_the_plan_of_its_own_family(plan_version, approval_version):
    plan, approval = PLANS[plan_version], APPROVALS[approval_version]
    if plan_version == approval_version:
        validate_versioned_approval(plan, approval)
    else:
        with pytest.raises(ValueError, match="mixed upload plan/approval versions"):
            validate_versioned_approval(plan, approval)


def test_a_family_never_validates_against_a_stranger_even_with_matching_fields():
    class Imitation(DatasetContinuationPlanV3):
        pass

    imitation = Imitation.model_construct(**dict(PLANS[3]))
    # A subclass of the genuine plan is still a plan of the continuation family, and the exact
    # type rule of the binding validator refuses it.
    with pytest.raises(ValueError):
        validate_versioned_approval(imitation, APPROVALS[3])
    for plan, approval in ((None, APPROVALS[3]), (PLANS[3], None), (object(), object())):
        with pytest.raises(ValueError, match="mixed upload plan/approval versions"):
            validate_versioned_approval(plan, approval)


def test_the_scope_of_a_proof_comes_from_the_family_that_wrote_it_never_by_elimination():
    v2 = TransferVerificationV2.model_validate_json(canon(GRAPH["verification"]))
    v3 = TransferVerificationV3.model_validate_json(
        fixture("dataset-continuation-verification-v3.json")
    )
    assert verification_scope(v2) == v2.scope
    assert verification_scope(v3) == v3.scope  # not v1's grant.scope, which a v3 proof has none of
    assert v3.grant is None
    v1 = SimpleNamespace(grant=SimpleNamespace(scope="legacy"))
    # Anything that is not one of the three families is refused, not read as the oldest.
    for stranger in (None, {}, object(), v1):
        with pytest.raises(ValueError, match="unsupported verification version"):
            verification_scope(stranger)


def test_the_graph_of_a_continuation_is_its_own_selection():
    plan = PLANS[3]
    spec = graph_of(plan)
    assert spec == StageGraphSpec(3, plan.manifest.file_count, plan.continuation.file_indices)
    assert spec.files == plan.continuation.file_indices == (0, 2)
    assert spec.continuation and spec.intent_count == 6
    for version in (1, 2):  # the original graphs are unchanged and cover the whole manifest
        original = graph_of(PLANS[version])
        assert original == StageGraphSpec(version, PLANS[version].manifest.file_count)
        assert original.files == tuple(range(PLANS[version].manifest.file_count))
        assert not original.continuation


def test_the_graph_of_a_check_only_continuation_is_empty():
    plan = DatasetContinuationPlanV3.model_validate_json(
        fixture("dataset-continuation-plan-v3-verification-only.json")
    )
    spec = graph_of(plan)
    assert spec.files == () and spec.intent_count == 0 and spec.required_stages() == frozenset()


def test_a_continuation_never_has_a_create_receipt():
    intent = StageIntent.model_validate_json(canon(GRAPH["intents"][0]))
    assert intent.kind == "create"
    with pytest.raises(ValueError, match="v2 create receipt requires v2 plan"):
        validate_create_receipt(PLANS[3], intent, SimpleNamespace())


PAYLOADS = [
    ("plan", DatasetUploadPlan, DatasetUploadPlanV2, DatasetContinuationPlanV3),
    ("approval", DatasetUploadApproval, DatasetUploadApprovalV2, DatasetUploadApprovalV3),
    ("record", TransferRecord, TransferRecordV2, TransferRecordV3),
    ("control", TransferControl, TransferControlV2, TransferControlV3),
    ("verification", TransferVerification, TransferVerificationV2, TransferVerificationV3),
]
V3_FIXTURES = {
    "plan": "dataset-continuation-plan-v3.json",
    "approval": "dataset-continuation-approval-v3.json",
    "record": "dataset-continuation-record-v3-running.json",
    "control": "dataset-continuation-control-v3.json",
    "verification": "dataset-continuation-verification-v3.json",
}


OLDER = {
    "plan": canon(V2_PAIR["plan"]),
    "approval": canon(V2_PAIR["approval"]),
    "record": canon(GRAPH["record"]),
    "control": canon(GRAPH["controls"][0]),
    "verification": canon(GRAPH["verification"]),
}


@pytest.mark.parametrize("field,v1,v2,v3", PAYLOADS)
def test_the_decoder_reads_a_third_family_only_where_the_caller_lists_it(field, v1, v2, v3):
    raw = fixture(V3_FIXTURES[field]).decode()
    assert type(decode_versioned(v1, v2, raw, v3)) is v3
    # A path that does not list the continuation type fails closed on its payload, unchanged.
    with pytest.raises(YorungeError) as error:
        decode_versioned(v1, v2, raw)
    assert error.value.code == "state_invalid"
    older = OLDER[field].decode()
    assert type(decode_versioned(v1, v2, older, v3)) is v2
    assert type(decode_versioned(v1, v2, older)) is v2


@pytest.mark.parametrize("field,v1,v2,v3", PAYLOADS)
def test_the_decoder_keeps_its_closed_version_and_size_rules_with_three_types(field, v1, v2, v3):
    value = json.loads(fixture(V3_FIXTURES[field]))
    for version in (True, 0, 4, 2.0, "3", None):
        bad = canon({**value, "schema_version": version}).decode()
        with pytest.raises(YorungeError) as error:
            decode_versioned(v1, v2, bad, v3)
        assert error.value.code == "state_invalid"
    for payload in (None, b"{}", 3, "", "[]", "{", canon(value) + b" "):
        with pytest.raises(YorungeError):
            decode_versioned(v1, v2, payload, v3)
    # The version tag chooses the type. A control or proof of v3 has v2's very fields, so only the
    # tag tells them apart, and the pairing with the record (same version) is the store's rule;
    # the other three carry fields no older type accepts.
    if field in ("plan", "approval", "record"):
        with pytest.raises(YorungeError):
            decode_versioned(v1, v2, canon({**value, "schema_version": 2}).decode(), v3)
    limit = max(v1.max_wire_bytes, v2.max_wire_bytes, v3.max_wire_bytes)
    with pytest.raises(YorungeError):
        decode_versioned(v1, v2, canon(value).decode() + " " * (limit + 1), v3)


def test_a_continuations_history_is_unreadable_until_its_graph_is_validated():
    plan, approval = PLANS[3], APPROVALS[3]
    record = TransferRecordV3.model_validate_json(
        fixture("dataset-continuation-record-v3-admitted.json")
    )
    view = VersionedTransferView(plan, approval, record)
    with pytest.raises(YorungeError) as error:
        validate_graph(view, MANIFEST)
    assert error.value.code == "state_invalid"
    # A plan with no operation has no graph to validate, as before.
    validate_graph(VersionedTransferView(plan, approval, None), MANIFEST)
