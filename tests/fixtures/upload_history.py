"""The schema-7 v2 history every upload test starts from, installed as real SQLite rows.

``install_fixture`` writes ``dataset-transfer-graph-v2.json`` (plan, approval, operation, eleven
stage intents with their receipts, a control and a proof) into an open store, re-addressed to that
store's identity, with every request digest recomputed. Shared by the history, create-receipt,
public-surface and continuation tests.
"""

import hashlib
import json
from pathlib import Path

from yorunge.adapters.state import metadata
from yorunge.domain.dataset_transfer import TransferRecord, operation_reservation
from yorunge.domain.dataset_upload import DatasetUploadPlan, upload_namespace

FIXTURES = Path(__file__).parent


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def install_fixture(store, *, terminal=True, scope=None):
    """Install the history re-addressed to ``store``; ``scope`` re-addresses it further.

    ``scope`` overrides fields of the plan's scope (the credential a real repository will check, the
    clock generation of the store's stamp) before anything is sealed; the stage owners and the
    record follow the scope's clock generation.
    """
    data = json.loads((FIXTURES / "dataset-transfer-graph-v2.json").read_bytes())
    meta = metadata(store.connection)
    plan, approval, record, proof = (
        data[key] for key in ("plan", "approval", "record", "verification")
    )
    plan["scope"].update(store_id=meta.store_id, identity_epoch=meta.identity_epoch)
    plan["scope"].update(scope or {})
    generation = plan["scope"]["clock_generation"]
    record["observed_clock_generation"] = generation
    body = {k: v for k, v in plan.items() if k != "digest"}
    plan["digest"] = digest(body)
    binding = {
        k: v for k, v in plan.items() if k not in ("plan_id", "digest", "prepared_at", "expires_at")
    }
    approval.update(
        store_id=meta.store_id,
        identity_epoch=meta.identity_epoch,
        clock_generation=generation,
        plan_digest=plan["digest"],
        binding_digest=digest(binding),
    )
    record.update(
        approval=approval, plan_digest=plan["digest"], observed_identity_epoch=meta.identity_epoch
    )
    proof["scope"] = plan["scope"]
    for intent in data["intents"]:
        intent["owner"]["identity_epoch"] = meta.identity_epoch
        intent["owner"]["clock_generation"] = generation
        kind, index = intent["kind"], intent["file_index"]
        mf = json.loads((FIXTURES / "dataset-manifest-v1.json").read_bytes())
        request = {
            "plan_digest": plan["digest"],
            "kind": kind,
            "file_index": index,
            "file": mf["files"][index] if index is not None else None,
            "dataset_id": proof["dataset_id"] if kind != "create" else None,
            "object_key": f"objects/{index}" if kind in ("put", "confirm") else None,
        }
        intent["request_digest"] = digest(request)
    control = data["controls"][0]
    control.update(
        identity_epoch=meta.identity_epoch,
        clock_generation=generation,
        verification_digest=digest(proof),
    )
    if not terminal:
        record.update(status="unknown", reason="request_uncertain")
        control.update(kind="recovery", reason="request_uncertain", verification_digest=None)
        data["verification"] = None
    c = store.connection
    namespace = {
        k: plan["scope"][k] for k in ("service_origin", "api_base_path", "owner", "project_id")
    }
    namespace["name"] = plan["parameters"]["name"]
    manifest = (FIXTURES / "dataset-manifest-v1.json").read_bytes()
    c.execute(
        "INSERT INTO upload_namespaces VALUES(?,?,NULL)",
        (record["intent_digest"], encode(namespace).decode()),
    )
    c.execute(
        "INSERT INTO upload_manifests VALUES(?,?)", (plan["manifest"]["digest"], manifest.decode())
    )
    c.execute(
        "INSERT INTO upload_plans VALUES(?,?,?,?,?,?)",
        (
            plan["plan_id"],
            record["intent_digest"],
            plan["manifest"]["digest"],
            plan["prepared_at"],
            plan["expires_at"],
            encode(plan).decode(),
        ),
    )
    c.execute(
        "INSERT INTO upload_approvals VALUES(?,?,?,?)",
        (
            plan["plan_id"],
            approval["approval_id"],
            approval["expires_at"],
            encode(approval).decode(),
        ),
    )
    c.execute(
        "INSERT INTO upload_operations VALUES(?,?,?,?,?,?,?)",
        (
            record["operation_id"],
            plan["plan_id"],
            record["intent_digest"],
            record["revision"],
            None,
            operation_reservation(3),
            encode(record).decode(),
        ),
    )
    c.execute(
        "UPDATE upload_namespaces SET create_operation_id=? WHERE intent_digest=?",
        (record["operation_id"], record["intent_digest"]),
    )
    for intent, receipt in zip(data["intents"], data["receipts"], strict=True):
        c.execute(
            "INSERT INTO upload_stage_intents VALUES(?,?,?,?,?,?)",
            (
                intent["intent_id"],
                intent["operation_id"],
                intent["sequence"],
                intent["kind"],
                intent["file_index"] if intent["file_index"] is not None else -1,
                encode(intent).decode(),
            ),
        )
        c.execute(
            "INSERT INTO upload_stage_receipts VALUES(?,?)",
            (receipt["intent_id"], encode(receipt).decode()),
        )
    c.execute(
        "INSERT INTO upload_controls VALUES(?,?,?)",
        (record["operation_id"], control["kind"], encode(control).decode()),
    )
    if terminal:
        c.execute(
            "INSERT INTO upload_verifications VALUES(?,?)",
            (record["operation_id"], encode(proof).decode()),
        )
    return data


def legacy_record(**changes):
    """The golden running v1 record, re-addressed with ``changes`` (it is valid on its own)."""
    data = json.loads((FIXTURES / "dataset-transfer-journal-v1.json").read_bytes())["record"]
    return TransferRecord.model_validate_json(encode({**data, **changes}))


def install_legacy_running(store, *, history=False):
    """A v1 plan with the golden running v1 record: the oldest family, on real rows.

    ``history`` completes it into a history that reads back: its approval and the create intent
    the record's latch stands on (nothing answered it, so the operation made no dataset).
    """
    pair = json.loads((FIXTURES / "dataset-upload-approved-v1.json").read_bytes())
    plan = DatasetUploadPlan.model_validate_json(encode(pair["plan"]))
    changes = {"approval": pair["approval"]} if history else {}
    record = legacy_record(
        plan_id=plan.plan_id,
        plan_digest=plan.digest,
        intent_digest=plan.intent_digest(),
        **changes,
    )
    c = store.connection
    c.execute(
        "INSERT INTO upload_namespaces VALUES(?,?,NULL)",
        (plan.intent_digest(), upload_namespace(plan.scope, plan.parameters.name).decode()),
    )
    c.execute(
        "INSERT INTO upload_manifests VALUES(?,?)",
        (plan.manifest.digest, (FIXTURES / "dataset-manifest-v1.json").read_text()),
    )
    c.execute(
        "INSERT INTO upload_plans VALUES(?,?,?,?,?,?)",
        (
            plan.plan_id,
            plan.intent_digest(),
            plan.manifest.digest,
            plan.prepared_at,
            plan.expires_at,
            plan.encoded().decode(),
        ),
    )
    if history:
        approval = pair["approval"]
        c.execute(
            "INSERT INTO upload_approvals VALUES(?,?,?,?)",
            (
                plan.plan_id,
                approval["approval_id"],
                approval["expires_at"],
                encode(approval).decode(),
            ),
        )
    c.execute(
        "INSERT INTO upload_operations VALUES(?,?,?,?,?,?,?)",
        (
            record.operation_id,
            record.plan_id,
            record.intent_digest,
            record.revision,
            record.lease.expires_at if record.lease else None,
            operation_reservation(3),
            record.encoded().decode(),
        ),
    )
    if history:
        c.execute(
            "UPDATE upload_namespaces SET create_operation_id=? WHERE intent_digest=?",
            (record.operation_id, record.intent_digest),
        )
        create = json.loads((FIXTURES / "dataset-transfer-journal-v1.json").read_bytes())["intent"]
        create["request_digest"] = digest(
            {
                "plan_digest": plan.digest,
                "kind": "create",
                "file_index": None,
                "file": None,
                "dataset_id": None,
                "object_key": None,
            }
        )
        c.execute(
            "INSERT INTO upload_stage_intents VALUES(?,?,?,?,?,?)",
            (
                create["intent_id"],
                create["operation_id"],
                create["sequence"],
                "create",
                -1,
                encode(create).decode(),
            ),
        )
    return plan, record
