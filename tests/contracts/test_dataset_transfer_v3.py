"""V3 continuation record, control and verification: goldens, lifecycle rules and plan bindings."""

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.dataset_transfer import TransferControl, TransferRecord, TransferVerification
from yorunge.domain.dataset_transfer_v2 import (
    TransferControlV2,
    TransferRecordV2,
    TransferVerificationV2,
)
from yorunge.domain.dataset_transfer_v3 import (
    TransferControlV3,
    TransferRecordV3,
    TransferVerificationV3,
    validate_record_binding_v3,
    validate_verification_binding_v3,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"
PROOF_DIGEST = "e228dbd459bb90a15fa141ed490ab85c5651c6ae43e997be026c7c43871a82c1"


def canon(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode()


def fixture(name):
    return (FIXTURES / name).read_bytes()


def data(name):
    return json.loads(fixture(name))


PLAN = DatasetContinuationPlanV3.model_validate_json(fixture("dataset-continuation-plan-v3.json"))
CHECK_ONLY = DatasetContinuationPlanV3.model_validate_json(
    fixture("dataset-continuation-plan-v3-verification-only.json")
)
OWNER = "00000000-0000-4000-8000-000000000008"
EPOCH = "00000000-0000-4000-8000-000000000002"


def record_of(**changes):
    value = data("dataset-continuation-record-v3-running.json")
    value.update(changes)
    return value


def accepts(value):
    return TransferRecordV3.model_validate_json(canon(value))


def rejects(value):
    with pytest.raises((ValidationError, ValueError)):
        TransferRecordV3.model_validate_json(canon(value))


def lease(**changes):
    return {
        "owner_id": OWNER,
        "fence": 1,
        "identity_epoch": EPOCH,
        "clock_generation": 1,
        "mode": "write",
        "renewed_at": "2026-11-02T11:00:02.000000Z",
        "expires_at": "2026-11-02T11:02:32.000000Z",
        **changes,
    }


def read_lease(**changes):
    return lease(mode="read", fence=2, **changes)


# --- goldens -----------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "name",
    ["admitted", "running"],
)
def test_record_goldens_round_trip_and_belong_to_the_plan(name):
    raw = fixture(f"dataset-continuation-record-v3-{name}.json")
    record = TransferRecordV3.model_validate_json(raw)
    assert record.encoded() == raw and record.schema_version == 3
    validate_record_binding_v3(PLAN, record)
    assert record.verification_only is False
    assert record.dataset_id == PLAN.continuation.dataset_id


def test_the_check_only_record_golden_succeeds_unlatched_and_belongs_to_its_plan():
    raw = fixture("dataset-continuation-record-v3-verification-only-succeeded.json")
    record = TransferRecordV3.model_validate_json(raw)
    assert record.encoded() == raw
    assert (record.verification_only, record.workflow_latched, record.status) == (
        True,
        False,
        "succeeded",
    )
    validate_record_binding_v3(CHECK_ONLY, record)


def test_control_and_verification_goldens_and_the_digest_between_them():
    proof_raw = fixture("dataset-continuation-verification-v3.json")
    control_raw = fixture("dataset-continuation-control-v3.json")
    proof = TransferVerificationV3.model_validate_json(proof_raw)
    control = TransferControlV3.model_validate_json(control_raw)
    assert proof.encoded() == proof_raw and control.encoded() == control_raw
    assert hashlib.sha256(proof_raw).hexdigest() == PROOF_DIGEST == control.verification_digest
    assert (proof.schema_version, control.schema_version) == (3, 3)
    assert len(proof.files) == PLAN.manifest.file_count == 3
    validate_verification_binding_v3(PLAN, proof)


# --- lifecycle: every status and flag combination the contract allows --------------------------
VALID = {
    "admitted": dict(status="admitted", lease=lease(), workflow_latched=False, reason=None),
    "running": dict(status="running", lease=lease(), workflow_latched=True, reason=None),
    "unknown, no owner": dict(
        status="unknown", lease=None, workflow_latched=True, reason="request_uncertain"
    ),
    "unknown, read owner": dict(
        status="unknown",
        lease=read_lease(),
        workflow_latched=True,
        reason="request_uncertain",
        fence=2,
    ),
    "unknown after a failed read": dict(
        status="unknown", lease=None, workflow_latched=True, reason="read_unavailable"
    ),
    "succeeded after sending": dict(
        status="succeeded", lease=None, workflow_latched=True, reason="metadata_verified"
    ),
    "failed": dict(status="failed", lease=None, workflow_latched=True, reason="provider_rejected"),
    "cancelled before any intent": dict(
        status="cancelled", lease=None, workflow_latched=False, reason="local_cancelled"
    ),
    "check-only admitted": dict(
        status="admitted",
        lease=lease(),
        workflow_latched=False,
        reason=None,
        verification_only=True,
    ),
    "check-only succeeded": dict(
        status="succeeded",
        lease=None,
        workflow_latched=False,
        reason="metadata_verified",
        verification_only=True,
    ),
    "check-only cancelled": dict(
        status="cancelled",
        lease=None,
        workflow_latched=False,
        reason="lease_expired",
        verification_only=True,
    ),
}


@pytest.mark.parametrize("name", VALID)
def test_every_allowed_lifecycle_shape_is_accepted(name):
    assert accepts(record_of(**VALID[name])).status == VALID[name]["status"]


REJECTED = {
    "no dataset": dict(dataset_id=None),
    "check-only latched": {**VALID["check-only admitted"], "workflow_latched": True},
    "check-only running": dict(verification_only=True, status="running"),
    "check-only unknown": {**VALID["unknown, no owner"], "verification_only": True},
    "check-only failed": {**VALID["failed"], "verification_only": True},
    "unlatched success after sending": {
        **VALID["succeeded after sending"],
        "workflow_latched": False,
    },
    "admission with a latch": {**VALID["admitted"], "workflow_latched": True},
    "admission without an owner": {**VALID["admitted"], "lease": None},
    "admission with a read owner": {**VALID["admitted"], "lease": read_lease(), "fence": 2},
    "admission with a reason": {**VALID["admitted"], "reason": "local_cancelled"},
    "unlatched running": {**VALID["running"], "workflow_latched": False},
    "unlatched unknown": {**VALID["unknown, no owner"], "workflow_latched": False},
    "unlatched failure": {**VALID["failed"], "workflow_latched": False},
    "latched cancellation": {**VALID["cancelled before any intent"], "workflow_latched": True},
    "stopped without a reason": {**VALID["cancelled before any intent"], "reason": None},
    "success without the proof reason": {**VALID["succeeded after sending"], "reason": "verified"},
    "proof reason without success": {**VALID["unknown, no owner"], "reason": "metadata_verified"},
    "failure by something else": {**VALID["failed"], "reason": "request_uncertain"},
    "running with a reason": {**VALID["running"], "reason": "request_uncertain"},
    "running without an owner": {**VALID["running"], "lease": None},
    "read failure that is final": {**VALID["failed"], "reason": "read_unavailable"},
    "owner on a terminal record": {**VALID["succeeded after sending"], "lease": lease()},
    "owner fence differs": {**VALID["running"], "lease": lease(fence=2)},
    "owner epoch differs": {
        **VALID["running"],
        "lease": lease(identity_epoch="00000000-0000-4000-8000-0000000000aa"),
    },
    "owner generation differs": {**VALID["running"], "lease": lease(clock_generation=2)},
    "other write owner": {
        **VALID["running"],
        "lease": lease(owner_id="00000000-0000-4000-8000-0000000000bb"),
    },
    "write owner with a later fence": {**VALID["running"], "lease": lease(fence=2), "fence": 2},
    "read owner on a running record": {
        **VALID["running"],
        "lease": read_lease(),
        "fence": 2,
    },
    "time runs backwards": dict(updated_at="2026-11-02T10:00:00.000000Z"),
    "bool as revision": dict(revision=True),
    "bool as the latch": dict(workflow_latched=1),
    "missing mode flag": dict(verification_only=None),
    "old version": dict(schema_version=2),
    "extra field": dict(extra=1),
}


@pytest.mark.parametrize("name", REJECTED)
def test_every_forbidden_lifecycle_shape_is_rejected(name):
    rejects(record_of(**REJECTED[name]))


def test_a_check_only_record_that_sends_cannot_have_been_admitted_from_a_sending_plan():
    sending = TransferRecordV3.model_validate_json(
        fixture("dataset-continuation-record-v3-verification-only-succeeded.json")
    )
    with pytest.raises(ValueError, match="does not belong"):
        validate_record_binding_v3(PLAN, sending)
    running = TransferRecordV3.model_validate_json(
        fixture("dataset-continuation-record-v3-running.json")
    )
    with pytest.raises(ValueError, match="does not belong"):
        validate_record_binding_v3(CHECK_ONLY, running)


@pytest.mark.parametrize(
    "changes",
    [
        {"plan_id": "00000000-0000-4000-8000-0000000000cc"},
        {"plan_digest": "0" * 64},
        {"intent_digest": "0" * 64},
        {"dataset_id": "00000000-0000-4000-8000-0000000000dd"},
        {"approval": {**data("dataset-continuation-approval-v3.json"), "binding_digest": "0" * 64}},
        {
            "approval": {
                **data("dataset-continuation-approval-v3.json"),
                "acknowledge_unconfirmed_effects": False,
            }
        },
    ],
)
def test_a_record_that_does_not_name_its_plan_is_refused(changes):
    with pytest.raises(ValueError):
        validate_record_binding_v3(PLAN, accepts(record_of(**changes)))


def test_versions_never_mix_between_plan_record_and_proof():
    v2_record = TransferRecordV2.model_validate_json(
        canon(
            {
                **{k: v for k, v in data("dataset-transfer-graph-v2.json")["record"].items()},
            }
        )
    )
    with pytest.raises(ValueError, match="mixed continuation plan/record versions"):
        validate_record_binding_v3(PLAN, v2_record)
    record = TransferRecordV3.model_validate_json(
        fixture("dataset-continuation-record-v3-running.json")
    )
    with pytest.raises(ValueError, match="mixed continuation plan/record versions"):
        validate_record_binding_v3(object(), record)
    with pytest.raises(ValueError, match="mixed continuation plan/proof versions"):
        validate_verification_binding_v3(PLAN, object())


def test_v3_wire_is_refused_by_the_older_types_and_older_wire_by_the_v3_types():
    v3 = {
        "record": fixture("dataset-continuation-record-v3-running.json"),
        "control": fixture("dataset-continuation-control-v3.json"),
        "proof": fixture("dataset-continuation-verification-v3.json"),
    }
    graph = data("dataset-transfer-graph-v2.json")
    for older, raw in (
        (TransferRecord, v3["record"]),
        (TransferRecordV2, v3["record"]),
        (TransferControl, v3["control"]),
        (TransferControlV2, v3["control"]),
        (TransferVerification, v3["proof"]),
        (TransferVerificationV2, v3["proof"]),
    ):
        with pytest.raises((ValidationError, ValueError)):
            older.model_validate_json(raw)
    for newer, value in (
        (TransferRecordV3, graph["record"]),
        (TransferControlV3, graph["controls"][0]),
        (TransferVerificationV3, graph["verification"]),
    ):
        with pytest.raises((ValidationError, ValueError)):
            newer.model_validate_json(canon(value))


# --- control ------------------------------------------------------------------------------------
def control_of(**changes):
    return {**data("dataset-continuation-control-v3.json"), **changes}


@pytest.mark.parametrize(
    "changes",
    [
        {"verification_digest": None},  # success without its proof digest
        {"reason": "request_uncertain"},  # a digest without success
        {"kind": "recovery"},  # metadata success is terminal
        {"reason": "read_unavailable", "verification_digest": None},  # read failure is recovery
        {"verification_digest": "E" * 64},
        {"observed_at": "yesterday"},
        {"revision": True},
        {"schema_version": 2},
        {"extra": 1},
        {"operation_id": "x"},
    ],
)
def test_a_malformed_control_is_rejected(changes):
    with pytest.raises((ValidationError, ValueError)):
        TransferControlV3.model_validate_json(canon(control_of(**changes)))


def test_a_read_failure_control_is_recovery_without_a_digest():
    control = TransferControlV3.model_validate_json(
        canon(control_of(kind="recovery", reason="read_unavailable", verification_digest=None))
    )
    assert control.kind == "recovery" and control.verification_digest is None


# --- verification --------------------------------------------------------------------------------
def proof_of(**changes):
    return {**data("dataset-continuation-verification-v3.json"), **changes}


def broken_files(mutate):
    files = data("dataset-continuation-verification-v3.json")["files"]
    mutate(files)
    return files


@pytest.mark.parametrize(
    "changes",
    [
        {"files": []},
        {"files": list(reversed(data("dataset-continuation-verification-v3.json")["files"]))},
        {"files": broken_files(lambda f: f[1].update(item_id=f[0]["item_id"]))},
        {"files": broken_files(lambda f: f[1].update(file_index=5))},
        {"files": data("dataset-continuation-verification-v3.json")["files"] * 43},
        {"project_id": "00000000-0000-4000-8000-0000000000ee"},
        {"authorization_policy": "verified_read"},  # no grant
        {"grant": {"unexpected": 1}},
        {"observed_at": "yesterday"},
        {"dataset_id": "x"},
        {"schema_version": 2},
        {"extra": 1},
    ],
)
def test_a_malformed_proof_is_rejected(changes):
    with pytest.raises((ValidationError, ValueError)):
        TransferVerificationV3.model_validate_json(canon(proof_of(**changes)))


def test_a_proof_short_of_the_manifest_is_well_formed_but_does_not_belong_to_the_plan():
    short = TransferVerificationV3.model_validate_json(
        canon(proof_of(files=broken_files(lambda files: files.pop())))
    )
    assert len(short.files) == 2
    with pytest.raises(ValueError, match="does not belong"):
        validate_verification_binding_v3(PLAN, short)


@pytest.mark.parametrize(
    "changes",
    [
        {"dataset_id": "00000000-0000-4000-8000-0000000000ee"},
        {"project_id": "00000000-0000-4000-8000-0000000000ef"},
    ],
)
def test_a_proof_for_another_dataset_or_project_does_not_belong_to_the_plan(changes):
    scope = data("dataset-continuation-verification-v3.json")["scope"]
    if "project_id" in changes:
        changes = {**changes, "scope": {**scope, "project_id": changes["project_id"]}}
    proof = TransferVerificationV3.model_validate_json(canon(proof_of(**changes)))
    with pytest.raises(ValueError, match="does not belong"):
        validate_verification_binding_v3(PLAN, proof)


def test_a_proof_from_another_target_does_not_belong_to_the_plan():
    scope = {
        **data("dataset-continuation-verification-v3.json")["scope"],
        "service_origin": "https://other.example",
    }
    proof = TransferVerificationV3.model_validate_json(canon(proof_of(scope=scope)))
    with pytest.raises(ValueError, match="does not belong"):
        validate_verification_binding_v3(PLAN, proof)
