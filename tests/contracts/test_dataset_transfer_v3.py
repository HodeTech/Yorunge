"""V3 continuation record, control and verification: goldens, lifecycle rules and plan bindings."""

import hashlib
import json
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from yorunge.domain.capabilities import instant, timestamp
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
    **{
        f"cancelled by {reason}": dict(
            status="cancelled", lease=None, workflow_latched=False, reason=reason
        )
        for reason in (
            "identity_reset",
            "lease_expired",
            "clock_changed",
            "approval_revoked",
            "approval_expired",
        )
    },
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
    "check-only cancelled by a reset": dict(
        status="cancelled",
        lease=None,
        workflow_latched=False,
        reason="identity_reset",
        verification_only=True,
    ),
}


@pytest.mark.parametrize("name", VALID)
def test_every_allowed_lifecycle_shape_is_accepted(name):
    assert accepts(record_of(**VALID[name])).status == VALID[name]["status"]


REJECTED = {
    "no dataset": dict(dataset_id=None),
    "check-only latched": {**VALID["check-only admitted"], "workflow_latched": True},
    "check-only latched success": {**VALID["check-only succeeded"], "workflow_latched": True},
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
    "success by another reason": {**VALID["succeeded after sending"], "reason": "local_cancelled"},
    "unknown without a reason": {**VALID["unknown, no owner"], "reason": None},
    "no-send cancellation by an uncertain request": {
        **VALID["cancelled before any intent"],
        "reason": "request_uncertain",
    },
    "no-send cancellation by a provider rejection": {
        **VALID["cancelled before any intent"],
        "reason": "provider_rejected",
    },
    "check-only cancellation by an uncertain request": {
        **VALID["check-only cancelled"],
        "reason": "request_uncertain",
    },
    "dataset that is no provider id": dict(dataset_id="x"),
    "dataset id in capitals": dict(dataset_id="00000000-0000-4000-8000-0000000009AB"),
    "proof reason without success": {**VALID["unknown, no owner"], "reason": "metadata_verified"},
    "failure by something else": {**VALID["failed"], "reason": "request_uncertain"},
    "running with a reason": {**VALID["running"], "reason": "request_uncertain"},
    "running without an owner": {**VALID["running"], "lease": None},
    "failure by a failed read": {**VALID["failed"], "reason": "read_unavailable"},
    "cancellation by a failed read": {
        **VALID["cancelled before any intent"],
        "reason": "read_unavailable",
    },
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


def test_the_mode_of_a_record_must_be_the_mode_of_its_plan_and_that_alone():
    sending = data("dataset-continuation-record-v3-admitted.json")
    validate_record_binding_v3(PLAN, accepts(sending))  # control: nothing else is wrong
    with pytest.raises(ValueError, match="does not belong"):
        validate_record_binding_v3(PLAN, accepts({**sending, "verification_only": True}))
    check_only = {
        **sending,
        "plan_id": CHECK_ONLY.plan_id,
        "plan_digest": CHECK_ONLY.digest,
        "intent_digest": CHECK_ONLY.intent_digest(),
        "dataset_id": CHECK_ONLY.continuation.dataset_id,
        "approval": data("dataset-continuation-approval-v3-verification-only.json"),
    }
    validate_record_binding_v3(CHECK_ONLY, accepts({**check_only, "verification_only": True}))
    with pytest.raises(ValueError, match="does not belong"):
        validate_record_binding_v3(CHECK_ONLY, accepts({**check_only, "verification_only": False}))


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


def entries(count):
    """Well-formed ordered proof entries of any number: the count is the only thing that varies."""
    template = data("dataset-continuation-verification-v3.json")["files"][0]
    return [
        {**template, "file_index": n, "item_id": f"00000000-0000-4000-8000-{n + 0x100:012x}"}
        for n in range(count)
    ]


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
        {"files": entries(129)},  # one more than a proof may hold
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


def test_an_explicit_read_cannot_carry_a_grant_while_a_verified_read_needs_a_current_one():
    grant = data("dataset-continuation-plan-v3-evidenced.json")["grant"]
    with pytest.raises(ValueError, match="manufacture a grant"):
        TransferVerificationV3.model_validate_json(canon(proof_of(grant=grant)))
    verified = proof_of(authorization_policy="verified_read", grant=grant)
    assert TransferVerificationV3.model_validate_json(canon(verified)).grant is not None
    stale = {**grant, "expires_at": "2026-11-02T11:00:00.000000Z"}  # not current at observed_at
    with pytest.raises(ValueError, match="actual current grant"):
        TransferVerificationV3.model_validate_json(
            canon(proof_of(authorization_policy="verified_read", grant=stale))
        )


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


def test_a_proof_holds_up_to_one_hundred_and_twenty_eight_entries_and_the_plan_wants_exactly_n():
    big = TransferVerificationV3.model_validate_json(canon(proof_of(files=entries(128))))
    assert len(big.files) == 128
    four = TransferVerificationV3.model_validate_json(canon(proof_of(files=entries(4))))
    for proof in (big, four):  # more than the plan's three files is as foreign as fewer
        with pytest.raises(ValueError, match="does not belong"):
            validate_verification_binding_v3(PLAN, proof)
    three = TransferVerificationV3.model_validate_json(canon(proof_of(files=entries(3))))
    validate_verification_binding_v3(PLAN, three)


def test_an_explicit_read_proof_needs_a_plan_that_allows_an_explicit_attempt():
    proof = TransferVerificationV3.model_validate_json(
        fixture("dataset-continuation-verification-v3.json")
    )
    assert proof.authorization_policy == "explicit_read_attempt"
    validate_verification_binding_v3(PLAN, proof)
    strict = PLAN.model_copy(update={"admission_policy": "verified_only"})
    with pytest.raises(ValueError, match="does not belong"):
        validate_verification_binding_v3(strict, proof)


# --- the grant rules every proof version shares ---------------------------------------------------
GRANT = data("dataset-continuation-plan-v3-evidenced.json")["grant"]
PROOFS = [
    pytest.param(
        TransferVerificationV3, data("dataset-continuation-verification-v3.json"), id="v3"
    ),
    pytest.param(
        TransferVerificationV2, data("dataset-transfer-graph-v2.json")["verification"], id="v2"
    ),
]


def verified(proof, **grant_changes):
    """The proof read under a verified policy with a grant for its own scope and instant."""
    grant = {**GRANT, "scope": proof["scope"], **grant_changes}
    return {**proof, "authorization_policy": "verified_read", "grant": grant}


def around(proof, delta_seconds=0, micro=0):
    moment = instant(proof["observed_at"]) + timedelta(seconds=delta_seconds, microseconds=micro)
    return timestamp(moment)


@pytest.mark.parametrize("model,proof", PROOFS)
def test_a_verified_read_needs_a_grant_for_its_scope_with_the_read_permission_current_now(
    model, proof
):
    model.model_validate_json(canon(verified(proof)))  # the control: every rule holds
    permissions = ["create_private_dataset", "link_project", "upload_created_dataset"]
    other_scope = {**proof["scope"], "profile": "somebody-else"}
    for changes in (
        {"scope": other_scope},
        {"permissions": permissions},
        {"checked_at": around(proof, micro=1), "expires_at": around(proof, 60)},
        {"checked_at": around(proof, -60), "expires_at": around(proof)},
    ):
        with pytest.raises(ValueError, match="actual current grant"):
            model.model_validate_json(canon(verified(proof, **changes)))
    edge = {"checked_at": around(proof), "expires_at": around(proof, micro=1)}
    model.model_validate_json(canon(verified(proof, **edge)))  # from now until the next microsecond


@pytest.mark.parametrize("model,proof", PROOFS)
def test_an_explicit_read_never_manufactures_a_grant(model, proof):
    model.model_validate_json(canon(proof))
    with pytest.raises(ValueError, match="manufacture a grant"):
        model.model_validate_json(canon({**proof, "grant": {**GRANT, "scope": proof["scope"]}}))


def test_the_binding_validators_accept_only_genuine_values():
    class ImitationRecord(TransferRecordV3):
        pass

    class ImitationProof(TransferVerificationV3):
        pass

    record = TransferRecordV3.model_validate_json(
        fixture("dataset-continuation-record-v3-admitted.json")
    )
    proof = TransferVerificationV3.model_validate_json(
        fixture("dataset-continuation-verification-v3.json")
    )
    v2 = data("dataset-transfer-graph-v2.json")
    foreign = {
        "record": [
            ImitationRecord.model_construct(**dict(record)),
            TransferRecordV2.model_validate_json(canon(v2["record"])),
            None,
            {"plan_id": record.plan_id},
            object(),
        ],
        "proof": [
            ImitationProof.model_construct(**dict(proof)),
            TransferVerificationV2.model_validate_json(canon(v2["verification"])),
            None,
            {"dataset_id": proof.dataset_id},
            object(),
        ],
    }
    for impostor in foreign["record"]:
        with pytest.raises(ValueError, match="mixed continuation plan/record versions"):
            validate_record_binding_v3(PLAN, impostor)
    for impostor in foreign["proof"]:
        with pytest.raises(ValueError, match="mixed continuation plan/proof versions"):
            validate_verification_binding_v3(PLAN, impostor)
    for impostor in (PLAN.model_dump(mode="json"), None, record):
        with pytest.raises(ValueError, match="mixed continuation plan/record versions"):
            validate_record_binding_v3(impostor, record)
        with pytest.raises(ValueError, match="mixed continuation plan/proof versions"):
            validate_verification_binding_v3(impostor, proof)


def test_a_continuation_is_never_its_own_source_or_baseline():
    admitted = data("dataset-continuation-record-v3-admitted.json")
    source = PLAN.continuation.source_operation_id
    assert accepts(admitted).operation_id not in {source, PLAN.continuation.baseline_operation_id}
    validate_record_binding_v3(PLAN, accepts(admitted))
    with pytest.raises(ValueError, match="own source"):
        validate_record_binding_v3(PLAN, accepts({**admitted, "operation_id": source}))
    other_baseline = "00000000-0000-4000-8000-0000000000b1"
    rebased = PLAN.model_copy(
        update={
            "continuation": PLAN.continuation.model_copy(
                update={"baseline_operation_id": other_baseline}
            )
        }
    )
    with pytest.raises(ValueError, match="own source"):
        validate_record_binding_v3(rebased, accepts({**admitted, "operation_id": other_baseline}))
    # In a chain the source (the previous continuation) is not the baseline root.
    other_source = "00000000-0000-4000-8000-0000000000b2"
    chained = PLAN.model_copy(
        update={
            "continuation": PLAN.continuation.model_copy(
                update={"source_operation_id": other_source}
            )
        }
    )
    with pytest.raises(ValueError, match="own source"):
        validate_record_binding_v3(chained, accepts({**admitted, "operation_id": other_source}))


@pytest.mark.parametrize(
    "model,name,limit",
    [
        (TransferRecordV3, "dataset-continuation-record-v3-running.json", 16 * 1024),
        (TransferControlV3, "dataset-continuation-control-v3.json", 2048),
        (TransferVerificationV3, "dataset-continuation-verification-v3.json", 128 * 1024),
    ],
)
def test_each_wire_type_holds_exactly_its_limit_and_not_a_byte_more(model, name, limit):
    assert model.max_wire_bytes == limit
    raw = fixture(name)
    model.model_validate_json(raw + b" " * (limit - len(raw)))
    with pytest.raises(ValueError, match="bounded upload wire"):
        model.model_validate_json(raw + b" " * (limit - len(raw) + 1))
