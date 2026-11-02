"""Atomic local upload admission and one-shot stage authorization, without network I/O."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from yorunge.adapters.capability_cache import Clock, Stamp, StateCache, SystemClock, TimeGate
from yorunge.adapters.execution_store import decode_cursor, encode_cursor
from yorunge.adapters.identity import credential_matches
from yorunge.adapters.operation_store import read_snapshot
from yorunge.adapters.state import Store, sqlite_error_code
from yorunge.adapters.upload_store import (
    TransferView,
    decode,
    namespace,
    predecessor,
    read_manifest,
    read_plan,
    read_record,
    read_view,
    request_digest,
    require_capacity,
    write_record,
)
from yorunge.adapters.validation_memo import validation_session
from yorunge.application.operations import DispatchPermit
from yorunge.application.response_json import check_response_secrets
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.credentials import BoundCredential
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_transfer import (
    TERMINAL,
    StageIntent,
    StageKind,
    StageReceipt,
    TransferControl,
    TransferLease,
    TransferReason,
    TransferRecord,
    TransferVerification,
    scope_target,
    verification_digest,
)
from yorunge.domain.dataset_upload import (
    COMMIT_MARGIN_SECONDS,
    PUT_SECONDS,
    TRANSFER_LEASE_SECONDS,
    DatasetUploadApproval,
    DatasetUploadPlan,
    UploadGrant,
    UploadScope,
    UploadWire,
    manifest_reference,
)
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.state import canonical_uuid


@dataclass(frozen=True)
class UploadListEntry:
    plan_id: str
    digest: str
    prepared_at: str
    status: str
    operation_id: str | None
    operation_status: str | None


def list_entry(view: TransferView) -> UploadListEntry:
    return UploadListEntry(
        view.plan.plan_id,
        view.plan.digest,
        view.plan.prepared_at,
        view.plan.status,
        view.operation.operation_id if view.operation else None,
        view.operation.status if view.operation else None,
    )


class StateUploads:
    """Internal repository. Production authority comes from a separately gated producer."""

    def __init__(
        self, store: Store, credential: BoundCredential | None = None, *, clock: Clock | None = None
    ) -> None:
        self.store, self.connection = store, store.connection
        self.credential = credential
        self.clock = clock or SystemClock()
        self.cache = StateCache(store, self.clock)

    @contextmanager
    def phase(self, operation_id: str | None = None) -> Iterator[None]:
        if operation_id is not None:
            try:
                canonical_uuid(operation_id)
            except (ValueError, TypeError, AttributeError):
                raise YorungeError("invalid_request") from None
        try:
            with validation_session():
                self.store.deadline.remaining()
                yield
                self.store.deadline.remaining()
        except OperationError:
            raise
        except YorungeError as error:
            raise OperationError(error.code, operation_id) from None
        except sqlite3.Error as error:
            raise OperationError(sqlite_error_code(error), operation_id) from None
        except OSError:
            raise OperationError("state_write_failed", operation_id) from None
        except (ValueError, TypeError):
            raise OperationError("state_invalid", operation_id) from None

    def _credential(self, scope: UploadScope, stamp: Stamp) -> None:
        bound = self.credential
        if bound is None:
            raise YorungeError("credential_unavailable")
        identity, credential = bound.identity, bound.credential
        if (scope.store_id, scope.identity_epoch, scope.clock_generation) != (
            stamp.store_id,
            stamp.identity_epoch,
            stamp.generation,
        ) or stamp.anomaly:
            raise YorungeError("state_changed")
        if (
            (
                scope.credential_id,
                scope.credential_revision,
                scope.service_id,
                scope.service_origin,
                scope.api_base_path,
            )
            != (
                identity.credential_id,
                identity.credential_revision,
                credential.reference.service_id,
                credential.target.service_origin,
                credential.target.api_base_path,
            )
            or identity.identity_epoch != stamp.identity_epoch
            or not credential_matches(
                self.connection,
                identity.credential_id,
                stamp.identity_epoch,
                identity.credential_revision,
                service=scope.service_id,
                origin=scope.service_origin,
                base=scope.api_base_path,
            )
        ):
            raise YorungeError("state_changed")

    def _secret(self, value: UploadWire | DatasetManifest) -> None:
        if self.credential is None:
            raise YorungeError("credential_unavailable")
        check_response_secrets(value, (self.credential.credential.secret,))

    def _current(
        self, plan: DatasetUploadPlan, fresh: DatasetUploadPlan, stamp: Stamp, gate: TimeGate
    ) -> None:
        self._credential(plan.scope, stamp)
        fresh = decode(DatasetUploadPlan, fresh.encoded().decode("ascii"))
        if (
            plan.status != "prepared"
            or fresh.status != "prepared"
            or plan.binding_digest() != fresh.binding_digest()
        ):
            raise YorungeError("upload_plan_not_valid")
        for value in (plan, fresh):
            gate.require_range(
                instant(value.prepared_at), instant(value.expires_at), error="upload_plan_not_valid"
            )
            for observation in (value.grant, value.cost_bound):
                if observation is None:
                    raise YorungeError("upload_plan_not_valid")
                gate.require_range(
                    instant(observation.checked_at),
                    instant(observation.expires_at),
                    error="upload_plan_not_valid",
                )
        gate.require_clock(stamp, error="state_changed")

    def _approved(self, view: TransferView, gate: TimeGate) -> DatasetUploadApproval:
        approval = view.approval
        if approval is None or approval.status != "approved":
            raise YorungeError("approval_required")
        gate.require_range(
            instant(approval.approved_at),
            instant(approval.expires_at),
            error="upload_plan_not_valid",
        )
        return approval

    def _finish(self, stamp: Stamp, gate: TimeGate, *, scope: UploadScope) -> None:
        final, within = self.cache._finish(stamp, checkpoint=gate.checkpoint)
        self._credential(scope, final)
        gate.check_clock(final)
        gate.check(final.now)
        if not within:
            raise YorungeError("state_busy")

    def save(self, plan: DatasetUploadPlan, manifest: DatasetManifest) -> TransferView:
        with self.phase():
            plan = decode(DatasetUploadPlan, plan.encoded().decode("ascii"))
            if manifest_reference(manifest) != plan.manifest:
                raise YorungeError("input_changed")
            self._secret(plan)
            self._secret(manifest)
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="state_changed") as gate:
                self._credential(plan.scope, stamp)
                gate.require_range(
                    instant(plan.prepared_at),
                    instant(plan.expires_at),
                    error="upload_plan_not_valid",
                )
                if self.connection.execute(
                    "SELECT 1 FROM upload_plans WHERE plan_id=?", (plan.plan_id,)
                ).fetchone():
                    if read_plan(self.connection, plan.plan_id) != plan:
                        raise YorungeError("operation_conflict")
                else:
                    active = self.connection.execute(
                        "SELECT create_operation_id FROM upload_namespaces WHERE "
                        "intent_digest=? AND create_operation_id IS NOT NULL",
                        (plan.intent_digest(),),
                    ).fetchone()
                    if active is not None:
                        raise OperationError("operation_conflict", active[0])
                    self.connection.execute(
                        "INSERT OR IGNORE INTO upload_namespaces VALUES(?,?,NULL)",
                        (plan.intent_digest(), namespace(plan).decode("ascii")),
                    )
                    self.connection.execute(
                        "INSERT OR IGNORE INTO upload_manifests VALUES(?,?)",
                        (manifest.digest, manifest.encoded().decode("utf-8")),
                    )
                    self.connection.execute(
                        "INSERT INTO upload_plans VALUES(?,?,?,?,?,?)",
                        (
                            plan.plan_id,
                            plan.intent_digest(),
                            manifest.digest,
                            plan.prepared_at,
                            plan.expires_at,
                            plan.encoded().decode("ascii"),
                        ),
                    )
                    require_capacity(self.connection)
                view = read_view(self.connection, plan.plan_id)
            self._finish(stamp, gate, scope=plan.scope)
            return view

    def show(self, *, plan_id: str | None = None, operation_id: str | None = None) -> TransferView:
        if (plan_id is None) == (operation_id is None):
            raise YorungeError("invalid_request")
        with self.phase(operation_id), read_snapshot(self.connection):
            if operation_id is not None:
                plan_id = read_record(self.connection, operation_id).plan_id
            assert plan_id is not None
            return read_view(self.connection, plan_id)

    def list(
        self, *, limit: int = 50, cursor: str | None = None
    ) -> tuple[tuple[UploadListEntry, ...], str | None]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise YorungeError("invalid_request")
        after = decode_cursor(cursor) if cursor is not None else ("", "")
        with self.phase(), read_snapshot(self.connection):
            rows = self.connection.execute(
                "SELECT prepared_at,plan_id FROM upload_plans WHERE "
                "(prepared_at,plan_id)>(?,?) ORDER BY prepared_at,plan_id LIMIT ?",
                (*after, limit + 1),
            ).fetchall()
            return tuple(
                list_entry(read_view(self.connection, r[1])) for r in rows[:limit]
            ), encode_cursor(*rows[limit - 1]) if len(rows) > limit else None

    def approve(self, plan_id: str, digest: str, fresh: DatasetUploadPlan) -> DatasetUploadApproval:
        with self.phase():
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="state_changed") as gate:
                view = read_view(self.connection, plan_id)
                self._current(view.plan, fresh, stamp, gate)
                if view.plan.digest != digest or view.operation is not None:
                    raise YorungeError("operation_conflict")
                if view.approval is not None:
                    raise YorungeError("operation_conflict")
                approval = DatasetUploadApproval(
                    schema_version=1,
                    approval_id=str(uuid4()),
                    plan_id=plan_id,
                    plan_digest=digest,
                    binding_digest=view.plan.binding_digest(),
                    store_id=stamp.store_id,
                    identity_epoch=stamp.identity_epoch,
                    clock_generation=stamp.generation,
                    approved_at=timestamp(stamp.now),
                    expires_at=view.plan.expires_at,
                    status="approved",
                    revoked_at=None,
                )
                self.connection.execute(
                    "INSERT INTO upload_approvals VALUES(?,?,?,?)",
                    (
                        plan_id,
                        approval.approval_id,
                        approval.expires_at,
                        approval.encoded().decode("ascii"),
                    ),
                )
                require_capacity(self.connection)
            self._finish(stamp, gate, scope=view.plan.scope)
            return approval

    def revoke(self, plan_id: str, digest: str) -> TransferView:
        with self.phase():
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp):
                view = read_view(self.connection, plan_id)
                if view.plan.digest != digest:
                    raise YorungeError("state_changed")
                if view.approval is not None and view.approval.status == "approved":
                    changed = view.approval.model_copy(
                        update={"status": "revoked", "revoked_at": timestamp(stamp.now)}
                    )
                    changed = decode(DatasetUploadApproval, changed.encoded().decode("ascii"))
                    self.connection.execute(
                        "UPDATE upload_approvals SET payload=? WHERE plan_id=?",
                        (changed.encoded().decode("ascii"), plan_id),
                    )
            return read_view(self.connection, plan_id)

    def admit(self, plan_id: str, fresh: DatasetUploadPlan) -> TransferRecord:
        with self.phase():
            # Exact existing lookup is idempotent, local and independent of an
            # expired/revoked plan. It never renews ownership or creates a permit.
            view = self.show(plan_id=plan_id)
            if view.operation is not None:
                return view.operation
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="state_changed") as gate:
                view = read_view(self.connection, plan_id)
                if view.operation is not None:
                    return view.operation
                self._current(view.plan, fresh, stamp, gate)
                approval = self._approved(view, gate)
                previous = self.connection.execute(
                    "SELECT create_operation_id FROM upload_namespaces WHERE "
                    "intent_digest=? AND create_operation_id IS NOT NULL",
                    (view.plan.intent_digest(),),
                ).fetchone()
                if previous is not None:
                    raise OperationError("operation_conflict", previous[0])
                lease = self._lease(stamp, fence=1, mode="write")
                record = TransferRecord(
                    schema_version=1,
                    operation_id=str(uuid4()),
                    plan_id=plan_id,
                    plan_digest=view.plan.digest,
                    intent_digest=view.plan.intent_digest(),
                    approval=approval,
                    write_owner_id=lease.owner_id,
                    created_at=timestamp(stamp.now),
                    updated_at=timestamp(stamp.now),
                    status="admitted",
                    revision=1,
                    fence=1,
                    observed_identity_epoch=stamp.identity_epoch,
                    observed_clock_generation=stamp.generation,
                    clock_anomaly=False,
                    lease=lease,
                    workflow_latched=False,
                    dataset_id=None,
                    reason=None,
                )
                write_record(self.connection, record, None)
                require_capacity(self.connection)
            with self.phase(record.operation_id):
                self._finish(stamp, gate, scope=view.plan.scope)
            return record

    def _lease(self, stamp: Stamp, *, fence: int, mode: str) -> TransferLease:
        return TransferLease.model_validate(
            {
                "owner_id": str(uuid4()),
                "fence": fence,
                "identity_epoch": stamp.identity_epoch,
                "clock_generation": stamp.generation,
                "mode": mode,
                "renewed_at": timestamp(stamp.now),
                "expires_at": timestamp(stamp.now + timedelta(seconds=TRANSFER_LEASE_SECONDS)),
            }
        )

    def _owner(
        self, record: TransferRecord, owner: TransferLease, stamp: Stamp, gate: TimeGate
    ) -> TransferLease:
        current = record.lease
        fields = ("owner_id", "fence", "identity_epoch", "clock_generation", "mode")
        if (
            current is None
            or record.status in TERMINAL
            or any(getattr(current, name) != getattr(owner, name) for name in fields)
        ):
            raise YorungeError("operation_lease_lost")
        if (current.identity_epoch, current.clock_generation) != (
            stamp.identity_epoch,
            stamp.generation,
        ) or stamp.anomaly:
            raise YorungeError("operation_lease_lost")
        if timestamp(stamp.now) < record.updated_at:
            raise YorungeError("state_changed")
        gate.require_clock(stamp, error="operation_lease_lost")
        gate.require_range(
            instant(current.renewed_at), instant(current.expires_at), error="operation_lease_lost"
        )
        return current

    @staticmethod
    def _renewed(owner: TransferLease, stamp: Stamp) -> TransferLease:
        return owner.model_copy(
            update={
                "renewed_at": timestamp(stamp.now),
                "expires_at": timestamp(stamp.now + timedelta(seconds=TRANSFER_LEASE_SECONDS)),
            }
        )

    def _change(self, record: TransferRecord, stamp: Stamp, **changes: object) -> TransferRecord:
        updated = record.model_copy(
            update={
                "updated_at": timestamp(stamp.now),
                "revision": record.revision + 1,
                "clock_anomaly": record.clock_anomaly or timestamp(stamp.now) < record.updated_at,
                "observed_identity_epoch": stamp.identity_epoch,
                "observed_clock_generation": stamp.generation,
                **changes,
            }
        )
        updated = decode(TransferRecord, updated.encoded().decode("ascii"))
        write_record(self.connection, updated, record.revision)
        return updated

    def _control(
        self,
        record: TransferRecord,
        stamp: Stamp,
        *,
        terminal: bool,
        proof: TransferVerification | None = None,
    ) -> None:
        assert record.reason is not None
        value = TransferControl(
            schema_version=1,
            kind="terminal" if terminal else "recovery",
            operation_id=record.operation_id,
            revision=record.revision,
            observed_at=record.updated_at,
            identity_epoch=stamp.identity_epoch,
            clock_generation=stamp.generation,
            reason=record.reason,
            verification_digest=verification_digest(proof) if proof else None,
        )
        if terminal:
            self.connection.execute(
                "INSERT INTO upload_controls VALUES(?,?,?)",
                (record.operation_id, value.kind, value.encoded().decode("ascii")),
            )
        else:
            self.connection.execute(
                "INSERT INTO upload_controls VALUES(?,?,?) ON "
                "CONFLICT(operation_id,kind) DO UPDATE SET payload=excluded.payload",
                (record.operation_id, value.kind, value.encoded().decode("ascii")),
            )

    def renew(
        self, operation_id: str, owner: TransferLease, *, grant: UploadGrant | None = None
    ) -> TransferLease:
        with self.phase(operation_id):
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="operation_lease_lost") as gate:
                view = self.show(operation_id=operation_id)
                record = view.operation
                assert record is not None
                owner = self._owner(record, owner, stamp, gate)
                if owner.mode == "read":
                    if grant is None:
                        raise YorungeError("upload_plan_not_valid")
                    self._read_grant(view, grant, stamp, gate)
                    scope = grant.scope
                else:
                    if grant is not None:
                        raise YorungeError("invalid_request")
                    self._credential(view.plan.scope, stamp)
                    scope = view.plan.scope
                lease = self._renewed(owner, stamp)
                write_record(
                    self.connection, record.model_copy(update={"lease": lease}), record.revision
                )
            self._finish(stamp, gate, scope=scope)
            return lease

    def arm(
        self,
        operation_id: str,
        owner: TransferLease,
        fresh: DatasetUploadPlan,
        kind: StageKind,
        file_index: int | None,
        *,
        total_end: float,
    ) -> tuple[StageIntent, DispatchPermit, float]:
        with self.phase(operation_id):
            before = self.clock.monotonic()
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="operation_lease_lost") as gate:
                view = self.show(operation_id=operation_id)
                record = view.operation
                assert record is not None
                owner = self._owner(record, owner, stamp, gate)
                if owner.mode != "write" or record.status not in {"admitted", "running"}:
                    raise YorungeError("operation_conflict")
                self._current(view.plan, fresh, stamp, gate)
                if self._approved(view, gate) != record.approval:
                    raise YorungeError("state_changed")
                receipt_map = {i.intent_id: i for i in view.intents}
                accepted = {
                    (receipt_map[r.intent_id].kind, receipt_map[r.intent_id].file_index): r
                    for r in view.receipts
                    if r.result == "accepted"
                }
                if any((i.kind, i.file_index) == (kind, file_index) for i in view.intents):
                    raise YorungeError("operation_conflict")
                required = predecessor(kind, file_index)
                if required is not None and required not in accepted:
                    raise YorungeError("operation_conflict")
                if file_index is not None and (
                    type(file_index) is not int
                    or not 0 <= file_index < view.plan.manifest.file_count
                ):
                    raise YorungeError("invalid_request")
                owner = self._renewed(owner, stamp)
                record = record.model_copy(update={"lease": owner})
                assert fresh.grant is not None and fresh.cost_bound is not None
                end = min(
                    instant(owner.expires_at),
                    instant(record.approval.expires_at),
                    instant(fresh.expires_at),
                    instant(fresh.grant.expires_at),
                    instant(fresh.cost_bound.expires_at),
                    stamp.now
                    + timedelta(
                        seconds=min(PUT_SECONDS if kind == "put" else 30, total_end - before)
                    ),
                )
                deadline = (
                    min(total_end, before + (end - stamp.now).total_seconds())
                    - COMMIT_MARGIN_SECONDS
                )
                if self.clock.monotonic() >= deadline:
                    raise YorungeError("execution_timeout")
                gate.require_range(
                    stamp.now,
                    end - timedelta(seconds=COMMIT_MARGIN_SECONDS),
                    error="execution_timeout",
                )
                if kind == "create":
                    claimed = self.connection.execute(
                        "UPDATE upload_namespaces SET create_operation_id=? WHERE "
                        "intent_digest=? AND create_operation_id IS NULL",
                        (operation_id, view.plan.intent_digest()),
                    )
                    if claimed.rowcount != 1:
                        previous = self.connection.execute(
                            "SELECT create_operation_id FROM upload_namespaces WHERE "
                            "intent_digest=?",
                            (view.plan.intent_digest(),),
                        ).fetchone()
                        raise OperationError("operation_conflict", previous[0])
                intent = StageIntent(
                    schema_version=1,
                    intent_id=str(uuid4()),
                    operation_id=operation_id,
                    sequence=len(view.intents) + 1,
                    kind=kind,
                    file_index=file_index,
                    request_digest=request_digest(
                        view.plan,
                        read_manifest(self.connection, view.plan),
                        kind,
                        file_index,
                        accepted,
                    ),
                    owner=owner,
                    intended_at=timestamp(stamp.now),
                    expires_at=timestamp(end),
                )
                self.connection.execute(
                    "INSERT INTO upload_stage_intents VALUES(?,?,?,?,?,?)",
                    (
                        intent.intent_id,
                        operation_id,
                        intent.sequence,
                        kind,
                        file_index if file_index is not None else -1,
                        intent.encoded().decode("ascii"),
                    ),
                )
                self._change(record, stamp, workflow_latched=True, status="running")
                read_view(self.connection, record.plan_id)
            # COMMIT is the authorization linearization. The following gate can
            # suppress issuance but cannot recall a permit already returned.
            try:
                self._finish(stamp, gate, scope=view.plan.scope)
                if self.clock.monotonic() >= deadline:
                    raise YorungeError("execution_timeout")
            except YorungeError as error:
                raise OperationError(
                    "operation_uncertain", operation_id, reason_code=error.code
                ) from None
            return intent, DispatchPermit(os.getpid), deadline

    def receipt(
        self, operation_id: str, owner: TransferLease, receipt: StageReceipt
    ) -> TransferView:
        with self.phase(operation_id):
            receipt = decode(StageReceipt, receipt.encoded().decode("ascii"))
            self._secret(receipt)
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="operation_lease_lost") as gate:
                view = self.show(operation_id=operation_id)
                record = view.operation
                assert record is not None
                owner = self._owner(record, owner, stamp, gate)
                self._credential(view.plan.scope, stamp)
                if owner.mode != "write":
                    raise YorungeError("operation_conflict")
                intent = next((i for i in view.intents if i.intent_id == receipt.intent_id), None)
                if intent is None or intent.owner.fence != owner.fence:
                    raise YorungeError("operation_conflict")
                gate.require_range(
                    instant(intent.intended_at),
                    instant(intent.expires_at),
                    error="operation_uncertain",
                )
                if instant(receipt.recorded_at) > stamp.now:
                    raise YorungeError("state_changed")
                existing = next(
                    (r for r in view.receipts if r.intent_id == receipt.intent_id), None
                )
                if existing is not None:
                    if existing != receipt:
                        raise YorungeError("operation_conflict")
                    return view
                dataset_id = (
                    receipt.dataset_id
                    if intent.kind == "create" and receipt.result == "accepted"
                    else record.dataset_id
                )
                rejected = receipt.result == "rejected" or any(
                    r.result == "rejected" for r in view.receipts
                )
                unresolved = len(view.intents) > len(view.receipts) + 1
                status = (
                    "unknown" if rejected and unresolved else "failed" if rejected else "running"
                )
                reason = "provider_rejected" if rejected else None
                changed = record.model_copy(
                    update={
                        "dataset_id": dataset_id,
                        "status": status,
                        "lease": None if status == "failed" else owner,
                        "reason": reason,
                    }
                )
                # Persist and validate in the same savepoint; malformed receipts
                # roll back without losing the permanent stage intent.
                self.connection.execute(
                    "INSERT INTO upload_stage_receipts VALUES(?,?)",
                    (receipt.intent_id, receipt.encoded().decode("ascii")),
                )
                changed = self._change(changed, stamp)
                if changed.status in {"failed", "unknown"}:
                    self._control(changed, stamp, terminal=changed.status == "failed")
                candidate = read_view(self.connection, record.plan_id)
            return candidate

    def stop_local(
        self, operation_id: str, owner: TransferLease, reason: TransferReason = "request_uncertain"
    ) -> TransferView:
        with self.phase(operation_id):
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="operation_lease_lost") as gate:
                view = self.show(operation_id=operation_id)
                record = view.operation
                assert record is not None
                owner = self._owner(record, owner, stamp, gate)
                if reason not in {"request_uncertain", "local_cancelled"}:
                    raise YorungeError("invalid_request")
                changed = self._change(
                    record,
                    stamp,
                    lease=None,
                    status="unknown" if record.workflow_latched else "cancelled",
                    reason=reason,
                )
                self._control(changed, stamp, terminal=not record.workflow_latched)
            return self.show(operation_id=operation_id)

    def acquire_read(self, operation_id: str, grant: UploadGrant) -> TransferLease:
        with self.phase(operation_id):
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="operation_lease_lost") as gate:
                view = self.show(operation_id=operation_id)
                record = view.operation
                assert record is not None
                self._read_grant(view, grant, stamp, gate)
                if record.status in TERMINAL or timestamp(stamp.now) < record.updated_at:
                    raise YorungeError("operation_conflict")
                previous = record.lease
                if (
                    previous is not None
                    and (previous.identity_epoch, previous.clock_generation)
                    == (stamp.identity_epoch, stamp.generation)
                    and instant(previous.expires_at) > stamp.now
                ):
                    raise YorungeError("operation_conflict")
                if record.fence >= 2**63 - 1:
                    raise YorungeError("operation_fence_exhausted")
                if not record.workflow_latched:
                    reason = (
                        "approval_revoked"
                        if view.approval is not None and view.approval.status == "revoked"
                        else "approval_expired"
                        if stamp.now >= instant(record.approval.expires_at)
                        else "lease_expired"
                    )
                    changed = self._change(
                        record, stamp, lease=None, status="cancelled", reason=reason
                    )
                    self._control(changed, stamp, terminal=True)
                    raise_after = True
                    lease = self._lease(stamp, fence=record.fence + 1, mode="read")
                else:
                    lease = self._lease(stamp, fence=record.fence + 1, mode="read")
                    changed = self._change(
                        record,
                        stamp,
                        lease=lease,
                        fence=lease.fence,
                        status="unknown",
                        reason="lease_expired",
                    )
                    self._control(changed, stamp, terminal=False)
                    raise_after = False
            if raise_after:
                raise YorungeError("operation_conflict")
            self._finish(stamp, gate, scope=grant.scope)
            return lease

    def _read_grant(
        self, view: TransferView, grant: UploadGrant, stamp: Stamp, gate: TimeGate
    ) -> None:
        grant = decode(UploadGrant, grant.encoded().decode("ascii"))
        self._credential(grant.scope, stamp)
        if (
            scope_target(grant.scope) != scope_target(view.plan.scope)
            or "read_created_dataset" not in grant.permissions
        ):
            raise YorungeError("state_changed")
        gate.require_range(
            instant(grant.checked_at), instant(grant.expires_at), error="upload_plan_not_valid"
        )

    def verified(
        self, operation_id: str, owner: TransferLease, proof: TransferVerification
    ) -> TransferView:
        with self.phase(operation_id):
            proof = decode(TransferVerification, proof.encoded().decode("ascii"))
            self._secret(proof)
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="operation_lease_lost") as gate:
                view = self.show(operation_id=operation_id)
                record = view.operation
                assert record is not None
                owner = self._owner(record, owner, stamp, gate)
                self._read_grant(view, proof.grant, stamp, gate)
                if (
                    record.dataset_id is None
                    or proof.dataset_id != record.dataset_id
                    or instant(proof.observed_at) > stamp.now
                ):
                    raise YorungeError("operation_conflict")
                # All normal write stages must be acknowledged. Recovery without
                # this evidence remains unknown until an exact provider oracle
                # is implemented; an ID/name match cannot manufacture success.
                accepted = {r.intent_id for r in view.receipts if r.result == "accepted"}
                if len(view.intents) != 2 + 3 * view.plan.manifest.file_count or any(
                    i.intent_id not in accepted for i in view.intents
                ):
                    raise YorungeError("operation_uncertain")
                changed = self._change(
                    record, stamp, lease=None, status="succeeded", reason="verified"
                )
                self.connection.execute(
                    "INSERT INTO upload_verifications VALUES(?,?)",
                    (operation_id, proof.encoded().decode("ascii")),
                )
                self._control(changed, stamp, terminal=True, proof=proof)
                candidate = read_view(self.connection, view.plan.plan_id)
            self._finish(stamp, gate, scope=proof.grant.scope)
            return candidate
