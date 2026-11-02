"""Strict bounded transfer reads and graph validation on real SQLite rows."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from typing import TypeVar

from yorunge.adapters.state import metadata
from yorunge.adapters.validation_memo import validated
from yorunge.domain.capabilities import canonical, instant
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_transfer import (
    TERMINAL,
    StageIntent,
    StageKind,
    StageReceipt,
    TransferControl,
    TransferRecord,
    TransferVerification,
    operation_reservation,
    scope_target,
    verification_digest,
)
from yorunge.domain.dataset_upload import (
    MAX_TRANSFER_FILES,
    MAX_TRANSFER_OPERATIONS,
    MAX_TRANSFER_PAYLOAD_BYTES,
    MAX_TRANSFER_PLANS,
    DatasetUploadApproval,
    DatasetUploadPlan,
    UploadWire,
    manifest_reference,
    validate_approval_binding,
)
from yorunge.domain.errors import YorungeError
from yorunge.domain.state import canonical_uuid

T = TypeVar("T", bound=UploadWire)
OP_COLUMNS = "operation_id,plan_id,intent_digest,revision,lease_expires_at,reservation,payload"


def decode(cls: type[T], payload: object) -> T:
    return validated(cls, (payload,), lambda: _decode(cls, payload))


def _decode(cls: type[T], payload: object) -> T:
    try:
        if not isinstance(payload, str):
            raise ValueError("text payload required")
        value = cls.model_validate_json(payload)
        if value.encoded() != payload.encode("ascii"):
            raise ValueError("canonical journal payload required")
        return value
    except (ValueError, TypeError, RecursionError):
        raise YorungeError("state_invalid") from None


def namespace(plan: DatasetUploadPlan) -> bytes:
    scope = plan.scope
    return canonical(
        {
            "service_origin": scope.service_origin,
            "api_base_path": scope.api_base_path,
            "owner": scope.owner.model_dump(mode="json"),
            "project_id": scope.project_id,
            "name": plan.parameters.name,
        }
    )


def read_plan(connection: sqlite3.Connection, identifier: str) -> DatasetUploadPlan:
    canonical_uuid(identifier)
    row = connection.execute("SELECT * FROM upload_plans WHERE plan_id=?", (identifier,)).fetchone()
    if row is None:
        raise YorungeError("upload_plan_not_found")
    plan = decode(DatasetUploadPlan, row[5])
    if row[:5] != (
        plan.plan_id,
        plan.intent_digest(),
        plan.manifest.digest,
        plan.prepared_at,
        plan.expires_at,
    ):
        raise YorungeError("state_invalid")
    found = connection.execute(
        "SELECT payload FROM upload_namespaces WHERE intent_digest=?", (row[1],)
    ).fetchone()
    if found != (namespace(plan).decode("ascii"),):
        raise YorungeError("state_invalid")
    return plan


def read_manifest(connection: sqlite3.Connection, plan: DatasetUploadPlan) -> DatasetManifest:
    row = connection.execute(
        "SELECT payload FROM upload_manifests WHERE digest=?", (plan.manifest.digest,)
    ).fetchone()
    try:
        if row is None or not isinstance(row[0], str) or len(row[0].encode("utf-8")) > 262144:
            raise ValueError("bounded manifest required")
        value = DatasetManifest.model_validate_json(row[0])
        if value.encoded() != row[0].encode("utf-8") or manifest_reference(value) != plan.manifest:
            raise ValueError("manifest byte identity mismatch")
        return value
    except (ValueError, TypeError, RecursionError):
        raise YorungeError("state_invalid") from None


def read_approval(
    connection: sqlite3.Connection, plan: DatasetUploadPlan
) -> DatasetUploadApproval | None:
    row = connection.execute(
        "SELECT approval_id,expires_at,payload FROM upload_approvals WHERE plan_id=?",
        (plan.plan_id,),
    ).fetchone()
    if row is None:
        return None
    value = decode(DatasetUploadApproval, row[2])
    try:
        validate_approval_binding(plan, value)
        if row[:2] != (value.approval_id, value.expires_at):
            raise ValueError("approval index mismatch")
    except ValueError:
        raise YorungeError("state_invalid") from None
    return value


def read_record(connection: sqlite3.Connection, identifier: str) -> TransferRecord:
    canonical_uuid(identifier)
    row = connection.execute(
        f"SELECT {OP_COLUMNS} FROM upload_operations WHERE operation_id=?", (identifier,)
    ).fetchone()
    if row is None:
        raise YorungeError("operation_not_found")
    record = decode(TransferRecord, row[-1])
    plan = read_plan(connection, record.plan_id)
    if row[:-1] != (
        record.operation_id,
        record.plan_id,
        record.intent_digest,
        record.revision,
        record.lease.expires_at if record.lease else None,
        operation_reservation(plan.manifest.file_count),
    ):
        raise YorungeError("state_invalid")
    return record


@dataclass(frozen=True)
class TransferView:
    plan: DatasetUploadPlan
    approval: DatasetUploadApproval | None
    operation: TransferRecord | None
    intents: tuple[StageIntent, ...] = ()
    receipts: tuple[StageReceipt, ...] = ()
    controls: tuple[TransferControl, ...] = ()
    verification: TransferVerification | None = None


def request_digest(
    plan: DatasetUploadPlan,
    manifest: DatasetManifest,
    kind: StageKind,
    index: int | None,
    receipts: dict[tuple[StageKind, int | None], StageReceipt],
) -> str:
    """Secret-free semantic request binding; never hashes a signed URL/header."""
    create = receipts.get(("create", None))
    previous = receipts.get(("presign", index)) if index is not None else None
    file = manifest.files[index].model_dump(mode="json") if index is not None else None
    payload = {
        "plan_digest": plan.digest,
        "kind": kind,
        "file_index": index,
        "file": file,
        "dataset_id": create.dataset_id if kind != "create" and create else None,
        "object_key": previous.object_key if kind in {"put", "confirm"} and previous else None,
    }
    return hashlib.sha256(canonical(payload)).hexdigest()


def predecessor(kind: StageKind, index: int | None) -> tuple[StageKind, int | None] | None:
    if kind == "create":
        return None
    if kind == "project_link":
        return "create", None
    if kind == "presign":
        return "project_link", None
    return ("presign" if kind == "put" else "put"), index


def _receipt(
    plan: DatasetUploadPlan,
    manifest: DatasetManifest,
    intent: StageIntent,
    receipt: StageReceipt,
    accepted: dict[tuple[StageKind, int | None], StageReceipt],
) -> None:
    if not instant(intent.intended_at) <= instant(receipt.recorded_at) < instant(intent.expires_at):
        raise ValueError("receipt outside issuing authority")
    if receipt.result == "rejected":
        return
    kind, index = intent.kind, intent.file_index
    if kind != "create" and receipt.dataset_id != accepted[("create", None)].dataset_id:
        raise ValueError("receipt dataset mismatch")
    expected_key = accepted[("presign", index)].object_key if kind in {"put", "confirm"} else None
    if kind in {"presign", "put", "confirm"}:
        if receipt.object_key is None or (
            expected_key is not None and receipt.object_key != expected_key
        ):
            raise ValueError("receipt object key mismatch")
    elif receipt.object_key is not None:
        raise ValueError("unexpected receipt key")
    if kind == "put":
        assert index is not None
        file = manifest.files[index]
        if (receipt.sent_bytes, receipt.sent_sha256) != (file.size, file.sha256):
            raise ValueError("streamed bytes differ from approved manifest")
    elif receipt.sent_bytes is not None:
        raise ValueError("only PUT has sent counters")


def _verify(view: TransferView, manifest: DatasetManifest) -> None:
    record, proof = view.operation, view.verification
    assert record is not None
    if proof is None:
        if record.status == "succeeded":
            raise ValueError("success without read evidence")
        return
    if (
        record.status != "succeeded"
        or record.dataset_id != proof.dataset_id
        or scope_target(proof.grant.scope) != scope_target(view.plan.scope)
        or proof.project_id != view.plan.scope.project_id
        or len(proof.files) != manifest.file_count
    ):
        raise ValueError("verification target mismatch")
    if (
        len(view.intents) != 2 + 3 * manifest.file_count
        or len(view.receipts) != len(view.intents)
        or any(r.result != "accepted" for r in view.receipts)
        or instant(proof.observed_at) > instant(record.updated_at)
    ):
        raise ValueError("success requires acknowledged stages and current read evidence")
    for expected, actual in zip(manifest.files, proof.files, strict=True):
        if (
            hashlib.sha256(expected.path.encode("utf-8")).hexdigest(),
            expected.size,
            expected.sha256,
        ) != (actual.path_digest, actual.size_bytes, actual.sha256):
            raise ValueError("read evidence differs from approved content")
    if len(proof.encoded()) > 16 * 1024 + 512 * manifest.file_count:
        raise ValueError("verification reservation exceeded")


def validate_graph(view: TransferView, manifest: DatasetManifest) -> None:
    record, plan = view.operation, view.plan
    if record is None:
        return
    try:
        validate_approval_binding(plan, record.approval)
        if (record.plan_digest, record.intent_digest) != (plan.digest, plan.intent_digest()):
            raise ValueError("operation plan mismatch")
        if view.approval is None or view.approval.model_dump(
            exclude={"status", "revoked_at"}
        ) != record.approval.model_dump(exclude={"status", "revoked_at"}):
            raise ValueError("admission approval history mismatch")
        if record.approval.status != "approved" or not instant(
            record.approval.approved_at
        ) <= instant(record.created_at) < instant(record.approval.expires_at):
            raise ValueError("admission without effective approval")
        if bool(view.intents) != record.workflow_latched:
            raise ValueError("workflow latch mismatch")
        accepted: dict[tuple[StageKind, int | None], StageReceipt] = {}
        receipts = {r.intent_id: r for r in view.receipts}
        keys: set[tuple[StageKind, int | None]] = set()
        rejected = False
        for sequence, intent in enumerate(view.intents, 1):
            key = intent.kind, intent.file_index
            if (
                key in keys
                or intent.sequence != sequence
                or intent.operation_id != record.operation_id
                or (intent.file_index is not None and intent.file_index >= manifest.file_count)
                or intent.owner.identity_epoch != plan.scope.identity_epoch
                or intent.owner.clock_generation != plan.scope.clock_generation
                or intent.owner.fence != 1
                or intent.owner.owner_id != record.write_owner_id
                or instant(intent.intended_at) < instant(record.created_at)
                or instant(intent.expires_at) > instant(record.approval.expires_at)
            ):
                raise ValueError("invalid stage binding")
            required = predecessor(intent.kind, intent.file_index)
            if required is not None and required not in accepted:
                raise ValueError("stage predecessor not accepted")
            if intent.request_digest != request_digest(
                plan, manifest, intent.kind, intent.file_index, accepted
            ):
                raise ValueError("stage request digest mismatch")
            receipt = receipts.get(intent.intent_id)
            if receipt is not None:
                _receipt(plan, manifest, intent, receipt, accepted)
                if receipt.result == "accepted":
                    accepted[key] = receipt
                else:
                    rejected = True
            keys.add(key)
        if len(receipts) != len(view.receipts) or not set(receipts) <= {
            i.intent_id for i in view.intents
        }:
            raise ValueError("orphan receipt")
        created = accepted.get(("create", None))
        if record.dataset_id != (created.dataset_id if created else None):
            raise ValueError("dataset receipt mismatch; no name-based ID recovery")
        if rejected and record.status not in {"unknown", "failed"}:
            raise ValueError("definitive rejection mismatch")
        if record.status == "failed" and (not rejected or len(view.receipts) != len(view.intents)):
            raise ValueError("failure cannot hide pending intent ambiguity")
        controls = {c.kind: c for c in view.controls}
        if len(controls) != len(view.controls):
            raise ValueError("control slot collision")
        for control in view.controls:
            if control.operation_id != record.operation_id or control.revision > record.revision:
                raise ValueError("control revision mismatch")
        terminal = controls.get("terminal")
        if (terminal is not None) != (record.status in TERMINAL):
            raise ValueError("terminal control mismatch")
        if terminal is not None and (terminal.revision, terminal.reason, terminal.observed_at) != (
            record.revision,
            record.reason,
            record.updated_at,
        ):
            raise ValueError("terminal evidence mismatch")
        if record.status == "unknown" and "recovery" not in controls:
            raise ValueError("unknown requires reserved recovery marker")
        if terminal is not None and terminal.verification_digest != (
            verification_digest(view.verification) if view.verification else None
        ):
            raise ValueError("terminal verification digest mismatch")
        _verify(view, manifest)
    except (ValueError, KeyError, IndexError, TypeError):
        raise YorungeError("state_invalid") from None


def read_view(connection: sqlite3.Connection, plan_id: str) -> TransferView:
    plan = read_plan(connection, plan_id)
    manifest = read_manifest(connection, plan)
    approval = read_approval(connection, plan)
    row = connection.execute(
        "SELECT operation_id FROM upload_operations WHERE plan_id=?", (plan_id,)
    ).fetchone()
    if row is None:
        return TransferView(plan, approval, None)
    record = read_record(connection, row[0])
    intents = []
    for item in connection.execute(
        "SELECT intent_id,sequence,kind,file_index,payload FROM "
        "upload_stage_intents WHERE operation_id=? ORDER BY sequence LIMIT 387",
        (record.operation_id,),
    ):
        intent = decode(StageIntent, item[-1])
        if item[:-1] != (
            intent.intent_id,
            intent.sequence,
            intent.kind,
            intent.file_index if intent.file_index is not None else -1,
        ):
            raise YorungeError("state_invalid")
        intents.append(intent)
    receipt_rows = connection.execute(
        "SELECT r.intent_id,r.payload FROM upload_stage_receipts r JOIN "
        "upload_stage_intents i USING(intent_id) WHERE i.operation_id=? ORDER BY i.sequence",
        (record.operation_id,),
    ).fetchall()
    receipts = tuple(decode(StageReceipt, r[1]) for r in receipt_rows)
    if any(
        row[0] != receipt.intent_id for row, receipt in zip(receipt_rows, receipts, strict=True)
    ):
        raise YorungeError("state_invalid")
    control_rows = connection.execute(
        "SELECT kind,payload FROM upload_controls WHERE operation_id=? ORDER BY kind",
        (record.operation_id,),
    ).fetchall()
    controls = tuple(decode(TransferControl, r[1]) for r in control_rows)
    if any(row[0] != control.kind for row, control in zip(control_rows, controls, strict=True)):
        raise YorungeError("state_invalid")
    proof = connection.execute(
        "SELECT payload FROM upload_verifications WHERE operation_id=?", (record.operation_id,)
    ).fetchone()
    view = TransferView(
        plan,
        approval,
        record,
        tuple(intents),
        receipts,
        controls,
        decode(TransferVerification, proof[0]) if proof else None,
    )
    if record.workflow_latched and connection.execute(
        "SELECT create_operation_id FROM upload_namespaces WHERE intent_digest=?",
        (record.intent_digest,),
    ).fetchone() != (record.operation_id,):
        raise YorungeError("state_invalid")
    validate_graph(view, manifest)
    return view


def capacity(connection: sqlite3.Connection) -> tuple[int, int, int, int]:
    plans = connection.execute("SELECT count(*) FROM upload_plans").fetchone()[0]
    operations, reserved = connection.execute(
        "SELECT count(*),coalesce(sum(reservation),0) FROM upload_operations"
    ).fetchone()
    files = sum(
        decode(DatasetUploadPlan, r[0]).manifest.file_count
        for r in connection.execute("SELECT payload FROM upload_plans")
    )
    used = (
        sum(
            connection.execute(
                f"SELECT coalesce(sum(length(CAST(payload AS BLOB))),0) FROM {table}"
            ).fetchone()[0]
            for table in (
                "upload_namespaces",
                "upload_manifests",
                "upload_plans",
                "upload_approvals",
            )
        )
        + reserved
    )
    return plans, operations, files, used


def require_capacity(connection: sqlite3.Connection, *, corrupt: bool = False) -> None:
    found = capacity(connection)
    if any(
        n > maximum
        for n, maximum in zip(
            found,
            (
                MAX_TRANSFER_PLANS,
                MAX_TRANSFER_OPERATIONS,
                MAX_TRANSFER_FILES,
                MAX_TRANSFER_PAYLOAD_BYTES,
            ),
            strict=True,
        )
    ):
        raise YorungeError("state_invalid" if corrupt else "upload_capacity_exceeded")


def validate_uploads(connection: sqlite3.Connection) -> None:
    require_capacity(connection, corrupt=True)
    store = metadata(connection)
    for row in connection.execute("SELECT plan_id FROM upload_plans ORDER BY plan_id"):
        view = read_view(connection, row[0])
        record = view.operation
        if (
            record is not None
            and record.lease is not None
            and record.lease.identity_epoch != store.identity_epoch
        ):
            raise YorungeError("state_invalid")
        if view.plan.scope.store_id != store.store_id:
            raise YorungeError("state_invalid")
    for table, key, child, foreign in (
        ("upload_namespaces", "intent_digest", "upload_plans", "intent_digest"),
        ("upload_manifests", "digest", "upload_plans", "manifest_digest"),
    ):
        if connection.execute(
            f"SELECT 1 FROM {table} p WHERE NOT EXISTS(SELECT 1 FROM {child} c "
            f"WHERE c.{foreign}=p.{key}) LIMIT 1"
        ).fetchone():
            raise YorungeError("state_invalid")
    for intent_digest, operation_id in connection.execute(
        "SELECT intent_digest,create_operation_id FROM "
        "upload_namespaces WHERE create_operation_id IS NOT NULL"
    ):
        record = read_record(connection, operation_id)
        if record.intent_digest != intent_digest or not record.workflow_latched:
            raise YorungeError("state_invalid")
    # FK integrity is also checked by Store.verify; warm graph reads compare all
    # payload/index identities rather than trusting SQL constraints alone.


def write_record(
    connection: sqlite3.Connection, record: TransferRecord, expected: int | None
) -> None:
    value = decode(TransferRecord, record.encoded().decode("ascii"))
    lease = value.lease.expires_at if value.lease else None
    if expected is None:
        plan = read_plan(connection, value.plan_id)
        connection.execute(
            "INSERT INTO upload_operations VALUES(?,?,?,?,?,?,?)",
            (
                value.operation_id,
                value.plan_id,
                value.intent_digest,
                value.revision,
                lease,
                operation_reservation(plan.manifest.file_count),
                value.encoded().decode("ascii"),
            ),
        )
    else:
        old = read_record(connection, value.operation_id)
        fixed = (
            "operation_id",
            "plan_id",
            "plan_digest",
            "intent_digest",
            "approval",
            "created_at",
            "write_owner_id",
        )
        if (
            old.revision != expected
            or old.status in TERMINAL
            or any(getattr(old, key) != getattr(value, key) for key in fixed)
            or (old.workflow_latched and not value.workflow_latched)
            or value.fence < old.fence
            or value.revision not in (old.revision, old.revision + 1)
        ):
            raise YorungeError("operation_conflict")
        if value.revision == old.revision and value.model_dump(exclude={"lease"}) != old.model_dump(
            exclude={"lease"}
        ):
            raise YorungeError("operation_conflict")
        changed = connection.execute(
            "UPDATE upload_operations SET "
            "revision=?,lease_expires_at=?,payload=? WHERE operation_id=? AND revision=?",
            (value.revision, lease, value.encoded().decode("ascii"), value.operation_id, expected),
        )
        if changed.rowcount != 1:
            raise YorungeError("operation_conflict")
