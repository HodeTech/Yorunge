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
from yorunge.domain.dataset_transfer import operation_reservation

FIXTURES = Path(__file__).parent


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def install_fixture(store, *, terminal=True):
    data = json.loads((FIXTURES / "dataset-transfer-graph-v2.json").read_bytes())
    meta = metadata(store.connection)
    plan, approval, record, proof = (
        data[key] for key in ("plan", "approval", "record", "verification")
    )
    plan["scope"].update(store_id=meta.store_id, identity_epoch=meta.identity_epoch)
    body = {k: v for k, v in plan.items() if k != "digest"}
    plan["digest"] = digest(body)
    binding = {
        k: v for k, v in plan.items() if k not in ("plan_id", "digest", "prepared_at", "expires_at")
    }
    approval.update(
        store_id=meta.store_id,
        identity_epoch=meta.identity_epoch,
        plan_digest=plan["digest"],
        binding_digest=digest(binding),
    )
    record.update(
        approval=approval, plan_digest=plan["digest"], observed_identity_epoch=meta.identity_epoch
    )
    proof["scope"] = plan["scope"]
    for intent in data["intents"]:
        intent["owner"]["identity_epoch"] = meta.identity_epoch
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
    control.update(identity_epoch=meta.identity_epoch, verification_digest=digest(proof))
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
