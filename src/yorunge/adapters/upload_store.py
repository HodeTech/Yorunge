"""Strict bounded transfer reads and graph validation on real SQLite rows."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from typing import Generic, TypeVar, overload

from yorunge.adapters.state import metadata
from yorunge.adapters.validation_memo import validated
from yorunge.domain.capabilities import instant
from yorunge.domain.create_receipt import CreateReceiptV2
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3, DatasetUploadApprovalV3
from yorunge.domain.dataset_manifest import DatasetManifest, decode_manifest_json
from yorunge.domain.dataset_transfer import (
    TERMINAL,
    StageIntent,
    StageKind,
    StageReceipt,
    TransferControl,
    TransferRecord,
    TransferVerification,
    scope_target,
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
    validate_record_binding_v3,
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
    upload_namespace,
)
from yorunge.domain.dataset_upload_v2 import DatasetUploadApprovalV2, DatasetUploadPlanV2
from yorunge.domain.errors import YorungeError
from yorunge.domain.platform_upload import ProviderDataset
from yorunge.domain.state import canonical_uuid
from yorunge.domain.upload_graph import FILE_STAGE_KINDS, StageGraphSpec
from yorunge.domain.upload_requests import upload_request_digest
from yorunge.domain.upload_versions import (
    UploadApproval,
    UploadControl,
    UploadPlan,
    UploadReceipt,
    UploadRecord,
    UploadVerification,
    graph_of,
    validate_create_receipt,
    validate_versioned_approval,
    verification_scope,
)
from yorunge.domain.upload_versions import (
    proof_digest as verification_digest,
)

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


U = TypeVar("U", bound=UploadWire)
W = TypeVar("W", bound=UploadWire)


@overload
def decode_versioned(v1: type[T], v2: type[U], payload: object) -> T | U: ...
@overload
def decode_versioned(v1: type[T], v2: type[U], payload: object, v3: type[W]) -> T | U | W: ...
def decode_versioned(
    v1: type[T], v2: type[U], payload: object, v3: type[W] | None = None
) -> T | U | W:
    """Decode a stored payload by its own version; a version the caller did not list is invalid.

    A caller that names no v3 type still reads v1/v2 and rejects a continuation payload, which
    is how a path that cannot yet handle a continuation fails closed instead of misreading it.
    """
    limit = max(v1.max_wire_bytes, v2.max_wire_bytes, v3.max_wire_bytes if v3 else 0)
    try:
        if not isinstance(payload, str) or len(payload) > limit:
            raise ValueError("bounded versioned payload required")
        raw = payload.encode("utf-8")
        if len(raw) > limit:
            raise ValueError("bounded versioned payload required")
        body = decode_manifest_json(raw)
        if not isinstance(body, dict) or type(body.get("schema_version")) is not int:
            raise ValueError("integer payload version required")
        if body["schema_version"] == 1:
            return decode(v1, payload)
        if body["schema_version"] == 2:
            return decode(v2, payload)
        if body["schema_version"] == 3 and v3 is not None:
            return decode(v3, payload)
        raise ValueError("closed payload version required")
    except (ValueError, TypeError, RecursionError):
        raise YorungeError("state_invalid") from None


def namespace(plan: UploadPlan) -> bytes:
    return upload_namespace(plan.scope, plan.parameters.name)


def read_plan(connection: sqlite3.Connection, identifier: str) -> UploadPlan:
    canonical_uuid(identifier)
    row = connection.execute("SELECT * FROM upload_plans WHERE plan_id=?", (identifier,)).fetchone()
    if row is None:
        raise YorungeError("upload_plan_not_found")
    plan = decode_versioned(
        DatasetUploadPlan, DatasetUploadPlanV2, row[5], DatasetContinuationPlanV3
    )
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


def read_manifest(connection: sqlite3.Connection, plan: UploadPlan) -> DatasetManifest:
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


def read_approval(connection: sqlite3.Connection, plan: UploadPlan) -> UploadApproval | None:
    row = connection.execute(
        "SELECT approval_id,expires_at,payload FROM upload_approvals WHERE plan_id=?",
        (plan.plan_id,),
    ).fetchone()
    if row is None:
        return None
    value = decode_versioned(
        DatasetUploadApproval, DatasetUploadApprovalV2, row[2], DatasetUploadApprovalV3
    )
    try:
        validate_versioned_approval(plan, value)
        if row[:2] != (value.approval_id, value.expires_at):
            raise ValueError("approval index mismatch")
    except ValueError:
        raise YorungeError("state_invalid") from None
    return value


def read_any_record(connection: sqlite3.Connection, identifier: str) -> UploadRecord:
    canonical_uuid(identifier)
    row = connection.execute(
        f"SELECT {OP_COLUMNS} FROM upload_operations WHERE operation_id=?", (identifier,)
    ).fetchone()
    if row is None:
        raise YorungeError("operation_not_found")
    record = decode_versioned(TransferRecord, TransferRecordV2, row[-1], TransferRecordV3)
    plan = read_plan(connection, record.plan_id)
    if record.schema_version != plan.schema_version or row[:-1] != (
        record.operation_id,
        record.plan_id,
        record.intent_digest,
        record.revision,
        record.lease.expires_at if record.lease else None,
        graph_of(plan).operation_reservation(),
    ):
        raise YorungeError("state_invalid")
    try:
        bind_continuation_record(plan, record)
    except ValueError:
        raise YorungeError("state_invalid") from None
    return record


def bind_continuation_record(plan: UploadPlan, record: UploadRecord) -> None:
    """A continuation's record is that plan's own admission; the older pairs are validate_graph's.

    The two families never mix: a record of one family under a plan of the other is refused.
    """
    if not isinstance(plan, DatasetContinuationPlanV3) and not isinstance(record, TransferRecordV3):
        return
    if not isinstance(plan, DatasetContinuationPlanV3) or not isinstance(record, TransferRecordV3):
        raise ValueError("mixed continuation plan/record versions")
    validate_record_binding_v3(plan, record)


def namespace_owner(plan: UploadPlan, record: UploadRecord) -> str:
    """The operation that holds the namespace's one create right.

    An original upload holds it itself. A continuation never gets a new one: its dataset, and so
    the namespace, belongs to the baseline operation it continues.
    """
    if isinstance(plan, DatasetContinuationPlanV3):
        return plan.continuation.baseline_operation_id
    return record.operation_id


P = TypeVar("P", bound=UploadWire, covariant=True)
A = TypeVar("A", bound=UploadWire, covariant=True)
R = TypeVar("R", bound=UploadWire, covariant=True)
C = TypeVar("C", bound=UploadWire, covariant=True)
V = TypeVar("V", bound=UploadWire, covariant=True)
S = TypeVar("S", bound=UploadWire, covariant=True)


@dataclass(frozen=True)
class _TransferView(Generic[P, A, R, C, V, S]):
    plan: P
    approval: A | None
    operation: R | None
    intents: tuple[StageIntent, ...] = ()
    receipts: tuple[S, ...] = ()
    controls: tuple[C, ...] = ()
    verification: V | None = None


TransferView = _TransferView[
    DatasetUploadPlan,
    DatasetUploadApproval,
    TransferRecord,
    TransferControl,
    TransferVerification,
    StageReceipt,
]
VersionedTransferView = _TransferView[
    UploadPlan, UploadApproval, UploadRecord, UploadControl, UploadVerification, UploadReceipt
]


def created_dataset(view: VersionedTransferView) -> ProviderDataset | None:
    """Read only the immutable strict receipt, never infer it from current remote data."""
    for receipt in view.receipts:
        if isinstance(receipt, CreateReceiptV2):
            return receipt.created_dataset
    return None


def legacy_create_without_baseline(view: VersionedTransferView) -> bool:
    record = view.operation
    if not isinstance(record, TransferRecordV2) or record.status in TERMINAL:
        return False
    create_ids = {intent.intent_id for intent in view.intents if intent.kind == "create"}
    return any(
        isinstance(receipt, StageReceipt)
        and receipt.intent_id in create_ids
        and receipt.result == "accepted"
        for receipt in view.receipts
    )


def read_record(connection: sqlite3.Connection, identifier: str) -> TransferRecord:
    record = read_any_record(connection, identifier)
    if not isinstance(record, TransferRecord):
        raise YorungeError("state_invalid")
    return record


def request_digest(
    plan: UploadPlan,
    manifest: DatasetManifest,
    kind: StageKind,
    index: int | None,
    receipts: dict[tuple[StageKind, int | None], UploadReceipt],
) -> str:
    """Secret-free semantic request binding; never hashes a signed URL/header."""
    graph = graph_of(plan)
    create = receipts.get(("create", None))
    previous = receipts.get(("presign", index)) if index is not None else None
    dataset: str | None = None
    if graph.takes_created_dataset(kind):
        if isinstance(plan, DatasetContinuationPlanV3):
            # A continuation has no create receipt: its requests bind the plan's own dataset.
            dataset = plan.continuation.dataset_id
        elif create is not None:
            dataset = create.dataset_id
    return upload_request_digest(
        plan.digest,
        kind,
        index,
        manifest.files[index] if index is not None else None,
        dataset,
        previous.object_key if graph.takes_presign_key(kind) and previous else None,
    )


def _receipt_key(
    graph: StageGraphSpec,
    kind: StageKind,
    index: int | None,
    receipt: UploadReceipt,
    accepted: dict[tuple[StageKind, int | None], UploadReceipt],
) -> None:
    expected_key = (
        accepted[("presign", index)].object_key if graph.takes_presign_key(kind) else None
    )
    if kind in FILE_STAGE_KINDS:
        if receipt.object_key is None or (
            expected_key is not None and receipt.object_key != expected_key
        ):
            raise ValueError("receipt object key mismatch")
    elif receipt.object_key is not None:
        raise ValueError("unexpected receipt key")


def _receipt(
    plan: UploadPlan,
    manifest: DatasetManifest,
    intent: StageIntent,
    receipt: UploadReceipt,
    accepted: dict[tuple[StageKind, int | None], UploadReceipt],
) -> None:
    if isinstance(receipt, CreateReceiptV2):
        validate_create_receipt(plan, intent, receipt)
    if not instant(intent.intended_at) <= instant(receipt.recorded_at) < instant(intent.expires_at):
        raise ValueError("receipt outside issuing authority")
    if receipt.result == "rejected":
        return
    graph = graph_of(plan)
    kind, index = intent.kind, intent.file_index
    if (
        graph.takes_created_dataset(kind)
        and receipt.dataset_id != accepted[("create", None)].dataset_id
    ):
        raise ValueError("receipt dataset mismatch")
    _receipt_key(graph, kind, index, receipt, accepted)
    if kind == "put":
        assert index is not None
        file = manifest.files[index]
        if (receipt.sent_bytes, receipt.sent_sha256) != (file.size, file.sha256):
            raise ValueError("streamed bytes differ from approved manifest")
    elif receipt.sent_bytes is not None:
        raise ValueError("only PUT has sent counters")


def verification_after(view: VersionedTransferView, proof: UploadVerification) -> None:
    """Compare UTC only within one clock epoch/generation; reset has a new floor."""
    record = view.operation
    assert record is not None
    scope = verification_scope(proof)
    clock = scope.identity_epoch, scope.clock_generation
    original = view.plan.scope.identity_epoch, view.plan.scope.clock_generation
    if clock == original:
        kinds = {item.intent_id: item.kind for item in view.intents}
        floor = max(
            [record.created_at]
            + [r.recorded_at for r in view.receipts if kinds[r.intent_id] == "confirm"]
        )
    else:
        controls = [
            c
            for c in view.controls
            if c.kind == "recovery" and (c.identity_epoch, c.clock_generation) == clock
        ]
        if not controls:
            raise ValueError("new clock requires current recovery observation")
        floor = max(c.observed_at for c in controls)
    if proof.observed_at < floor:
        raise ValueError("metadata observation precedes confirmation or recovery")


def acknowledged_stages(view: VersionedTransferView) -> bool:
    graph = graph_of(view.plan)
    return (
        {(i.kind, i.file_index) for i in view.intents} == graph.required_stages()
        and len(view.intents) == graph.intent_count
        and len(view.receipts) == len(view.intents)
        and all(r.result == "accepted" for r in view.receipts)
    )


def _verify(view: VersionedTransferView, manifest: DatasetManifest) -> None:
    record, proof = view.operation, view.verification
    assert record is not None
    if proof is None:
        if record.status == "succeeded":
            raise ValueError("success without read evidence")
        return
    if (
        record.status != "succeeded"
        or proof.schema_version != record.schema_version
        or record.dataset_id != proof.dataset_id
        or scope_target(verification_scope(proof)) != scope_target(view.plan.scope)
        or proof.project_id != view.plan.scope.project_id
        or len(proof.files) != manifest.file_count
        or (verification_scope(proof).identity_epoch, verification_scope(proof).clock_generation)
        != (record.observed_identity_epoch, record.observed_clock_generation)
    ):
        raise ValueError("verification target mismatch")
    if not acknowledged_stages(view) or instant(proof.observed_at) > instant(record.updated_at):
        raise ValueError("success requires acknowledged stages and current read evidence")
    if (
        isinstance(proof, TransferVerificationV2)
        and proof.authorization_policy == "explicit_read_attempt"
        and (
            not isinstance(view.plan, DatasetUploadPlanV2)
            or view.plan.admission_policy != "explicit_attempt"
        )
    ):
        raise ValueError("explicit read proof requires explicit v2 plan")
    verification_after(view, proof)
    for expected, actual in zip(manifest.files, proof.files, strict=True):
        if (
            hashlib.sha256(expected.path.encode("utf-8")).hexdigest(),
            expected.size,
            expected.sha256,
        ) != (actual.path_digest, actual.size_bytes, actual.sha256):
            raise ValueError("read evidence differs from approved content")
    if len(proof.encoded()) > 16 * 1024 + 512 * manifest.file_count:
        raise ValueError("verification reservation exceeded")


def _operation_header(view: VersionedTransferView) -> None:
    record, plan = view.operation, view.plan
    assert record is not None
    validate_versioned_approval(plan, record.approval)
    if (record.plan_id, record.plan_digest, record.intent_digest) != (
        plan.plan_id,
        plan.digest,
        plan.intent_digest(),
    ):
        raise ValueError("operation plan mismatch")
    if view.approval is None or view.approval.model_dump(
        exclude={"status", "revoked_at"}
    ) != record.approval.model_dump(exclude={"status", "revoked_at"}):
        raise ValueError("admission approval history mismatch")
    if record.approval.status != "approved" or not instant(record.approval.approved_at) <= instant(
        record.created_at
    ) < instant(record.approval.expires_at):
        raise ValueError("admission without effective approval")
    if bool(view.intents) != record.workflow_latched:
        raise ValueError("workflow latch mismatch")


def _intent_binding(
    view: VersionedTransferView,
    manifest: DatasetManifest,
    intent: StageIntent,
    sequence: int,
    keys: set[tuple[StageKind, int | None]],
    accepted: dict[tuple[StageKind, int | None], UploadReceipt],
) -> None:
    record, plan = view.operation, view.plan
    graph = graph_of(plan)
    assert record is not None
    if (
        (intent.kind, intent.file_index) in keys
        or intent.sequence != sequence
        or intent.operation_id != record.operation_id
        or (intent.file_index is not None and intent.file_index not in graph.files)
        or intent.owner.identity_epoch != plan.scope.identity_epoch
        or intent.owner.clock_generation != plan.scope.clock_generation
        or intent.owner.fence != 1
        or intent.owner.owner_id != record.write_owner_id
        or instant(intent.intended_at) < instant(record.created_at)
        or instant(intent.expires_at) > instant(record.approval.expires_at)
    ):
        raise ValueError("invalid stage binding")
    required = graph.predecessor(intent.kind, intent.file_index)
    if required is not None:
        if required not in accepted:
            raise ValueError("stage predecessor not accepted")
        if intent.intended_at < accepted[required].recorded_at:
            raise ValueError("stage precedes predecessor acknowledgement")
    if intent.request_digest != request_digest(
        plan, manifest, intent.kind, intent.file_index, accepted
    ):
        raise ValueError("stage request digest mismatch")


def _stages(view: VersionedTransferView, manifest: DatasetManifest) -> None:
    record = view.operation
    assert record is not None
    accepted: dict[tuple[StageKind, int | None], UploadReceipt] = {}
    receipts = {r.intent_id: r for r in view.receipts}
    keys: set[tuple[StageKind, int | None]] = set()
    rejected = False
    for sequence, intent in enumerate(view.intents, 1):
        key = intent.kind, intent.file_index
        _intent_binding(view, manifest, intent, sequence, keys, accepted)
        receipt = receipts.get(intent.intent_id)
        if receipt is not None:
            _receipt(view.plan, manifest, intent, receipt, accepted)
            if receipt.result == "accepted":
                accepted[key] = receipt
            else:
                rejected = True
        keys.add(key)
    _stage_outcome(view, record, receipts, accepted, rejected)


def _stage_outcome(
    view: VersionedTransferView,
    record: UploadRecord,
    receipts: dict[str, UploadReceipt],
    accepted: dict[tuple[StageKind, int | None], UploadReceipt],
    rejected: bool,
) -> None:
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


def _current_control(record: UploadRecord, control: UploadControl) -> None:
    if (
        control.revision,
        control.reason,
        control.observed_at,
        control.identity_epoch,
        control.clock_generation,
    ) != (
        record.revision,
        record.reason,
        record.updated_at,
        record.observed_identity_epoch,
        record.observed_clock_generation,
    ):
        raise ValueError("current control evidence mismatch")


def _terminal_control(view: VersionedTransferView, terminal: UploadControl | None) -> None:
    record = view.operation
    assert record is not None
    if (terminal is not None) != (record.status in TERMINAL):
        raise ValueError("terminal control mismatch")
    if terminal is None:
        return
    _current_control(record, terminal)
    if terminal.verification_digest != (
        verification_digest(view.verification) if view.verification else None
    ):
        raise ValueError("terminal verification digest mismatch")


def _controls(view: VersionedTransferView) -> None:
    record = view.operation
    assert record is not None
    controls = {c.kind: c for c in view.controls}
    if len(controls) != len(view.controls):
        raise ValueError("control slot collision")
    for control in view.controls:
        if (
            control.operation_id != record.operation_id
            or control.revision > record.revision
            or control.schema_version != record.schema_version
        ):
            raise ValueError("control revision mismatch")
    _terminal_control(view, controls.get("terminal"))
    if record.status == "unknown":
        recovery = controls.get("recovery")
        if recovery is None:
            raise ValueError("unknown requires reserved recovery marker")
        _current_control(record, recovery)


def validate_graph(view: VersionedTransferView, manifest: DatasetManifest) -> None:
    if view.operation is None:
        return
    if graph_of(view.plan).continuation:
        # The v3 graph (no create, a file subset, a baseline from the chain) is validated by
        # P02-3u. Until then a continuation's history is unreadable, never half-validated.
        raise YorungeError("state_invalid")
    try:
        _operation_header(view)
        _stages(view, manifest)
        _controls(view)
        _verify(view, manifest)
    except (ValueError, KeyError, IndexError, TypeError):
        raise YorungeError("state_invalid") from None


def read_any_view(connection: sqlite3.Connection, plan_id: str) -> VersionedTransferView:
    plan = read_plan(connection, plan_id)
    manifest = read_manifest(connection, plan)
    approval = read_approval(connection, plan)
    row = connection.execute(
        "SELECT operation_id FROM upload_operations WHERE plan_id=?", (plan_id,)
    ).fetchone()
    if row is None:
        return VersionedTransferView(plan, approval, None)
    record = read_any_record(connection, row[0])
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
    receipts = tuple(decode_versioned(StageReceipt, CreateReceiptV2, r[1]) for r in receipt_rows)
    if any(
        row[0] != receipt.intent_id for row, receipt in zip(receipt_rows, receipts, strict=True)
    ):
        raise YorungeError("state_invalid")
    control_rows = connection.execute(
        "SELECT kind,payload FROM upload_controls WHERE operation_id=? ORDER BY kind",
        (record.operation_id,),
    ).fetchall()
    controls = tuple(
        decode_versioned(TransferControl, TransferControlV2, r[1], TransferControlV3)
        for r in control_rows
    )
    if any(row[0] != control.kind for row, control in zip(control_rows, controls, strict=True)):
        raise YorungeError("state_invalid")
    proof = connection.execute(
        "SELECT payload FROM upload_verifications WHERE operation_id=?", (record.operation_id,)
    ).fetchone()
    view = VersionedTransferView(
        plan,
        approval,
        record,
        tuple(intents),
        receipts,
        controls,
        decode_versioned(
            TransferVerification, TransferVerificationV2, proof[0], TransferVerificationV3
        )
        if proof
        else None,
    )
    if record.workflow_latched and connection.execute(
        "SELECT create_operation_id FROM upload_namespaces WHERE intent_digest=?",
        (record.intent_digest,),
    ).fetchone() != (namespace_owner(plan, record),):
        raise YorungeError("state_invalid")
    validate_graph(view, manifest)
    return view


def read_view(connection: sqlite3.Connection, plan_id: str) -> TransferView:
    return require_legacy_view(read_any_view(connection, plan_id))


def require_legacy_view(view: VersionedTransferView) -> TransferView:
    if (
        not isinstance(view.plan, DatasetUploadPlan)
        or (view.approval is not None and not isinstance(view.approval, DatasetUploadApproval))
        or (view.operation is not None and not isinstance(view.operation, TransferRecord))
        or any(not isinstance(c, TransferControl) for c in view.controls)
        or any(not isinstance(receipt, StageReceipt) for receipt in view.receipts)
        or (
            view.verification is not None
            and not isinstance(view.verification, TransferVerification)
        )
    ):
        raise YorungeError("state_invalid")
    # Pair validation above established the exact v1 family; no payload is rewritten.
    from typing import cast

    return cast(TransferView, view)


def capacity(connection: sqlite3.Connection) -> tuple[int, int, int, int]:
    # The plan decode below deliberately names only the original families: a stored continuation
    # makes it fail closed (state_invalid) until P02-3v counts continuations, rather than being
    # skipped or read as an original plan.
    plans = connection.execute("SELECT count(*) FROM upload_plans").fetchone()[0]
    operations, reserved = connection.execute(
        "SELECT count(*),coalesce(sum(reservation),0) FROM upload_operations"
    ).fetchone()
    files = sum(
        decode_versioned(DatasetUploadPlan, DatasetUploadPlanV2, r[0]).manifest.file_count
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
            )
        )
        + reserved
        + plans * 16 * 1024
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
        view = read_any_view(connection, row[0])
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
        record = read_any_record(connection, operation_id)
        if record.intent_digest != intent_digest or not record.workflow_latched:
            raise YorungeError("state_invalid")
    # FK integrity is also checked by Store.verify; warm graph reads compare all
    # payload/index identities rather than trusting SQL constraints alone.


def write_record(
    connection: sqlite3.Connection, record: UploadRecord, expected: int | None
) -> None:
    value = decode_versioned(
        TransferRecord, TransferRecordV2, record.encoded().decode("ascii"), TransferRecordV3
    )
    lease = value.lease.expires_at if value.lease else None
    if expected is None:
        plan = read_plan(connection, value.plan_id)
        try:
            bind_continuation_record(plan, value)
        except ValueError:
            raise YorungeError("state_invalid") from None
        connection.execute(
            "INSERT INTO upload_operations VALUES(?,?,?,?,?,?,?)",
            (
                value.operation_id,
                value.plan_id,
                value.intent_digest,
                value.revision,
                lease,
                graph_of(plan).operation_reservation(),
                value.encoded().decode("ascii"),
            ),
        )
    else:
        old = read_any_record(connection, value.operation_id)
        fixed: tuple[str, ...] = (
            "schema_version",
            "operation_id",
            "plan_id",
            "plan_digest",
            "intent_digest",
            "approval",
            "created_at",
            "write_owner_id",
            "write_access_digest",
        )
        if value.schema_version == 3:
            # Fixed at admission and bound to the plan: the dataset it sends into and its mode.
            fixed += ("dataset_id", "verification_only")
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
