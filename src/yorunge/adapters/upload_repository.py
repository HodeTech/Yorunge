"""Atomic local upload admission and one-shot stage authorization, without network I/O."""

from __future__ import annotations

import hashlib
import math
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
from yorunge.adapters.upload_admission import continuation_admission
from yorunge.adapters.upload_chain import ChainSnapshot
from yorunge.adapters.upload_chain import chain_snapshot as stored_snapshot
from yorunge.adapters.upload_chain import operation_journal as stored_journal
from yorunge.adapters.upload_lineage import Lineage
from yorunge.adapters.upload_read_access import ReadAccess, authorize_read, initial_read_consent
from yorunge.adapters.upload_store import (
    VersionedTransferView,
    acknowledged_stages,
    created_dataset,
    decode,
    decode_versioned,
    legacy_create_without_baseline,
    namespace,
    read_manifest,
    read_plan,
    read_view_and_lineage,
    request_digest,
    require_capacity,
    verification_after,
    write_record,
)
from yorunge.adapters.upload_store import (
    read_any_record as read_record,
)
from yorunge.adapters.upload_store import (
    read_any_view as read_view,
)
from yorunge.adapters.validation_memo import validation_session
from yorunge.application.continuation_policy import approve_upload_v3
from yorunge.application.response_json import check_response_secrets
from yorunge.application.transfer_access import TransferWriteAccess
from yorunge.application.upload_arms import UploadArm, _issue_upload_arm
from yorunge.application.upload_inputs import revalidate_input
from yorunge.application.upload_policy import approve_upload_v2
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.create_receipt import CreateReceiptV2
from yorunge.domain.credentials import BoundCredential
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3, DatasetUploadApprovalV3
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
from yorunge.domain.dataset_upload import (
    COMMIT_MARGIN_SECONDS,
    PUT_SECONDS,
    TRANSFER_LEASE_SECONDS,
    DatasetUploadApproval,
    DatasetUploadPlan,
    UploadGrant,
    UploadPermission,
    UploadScope,
    UploadWire,
    manifest_reference,
    upload_namespace,
)
from yorunge.domain.dataset_upload_v2 import DatasetUploadApprovalV2, DatasetUploadPlanV2
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.platform_upload import ProviderDataset
from yorunge.domain.state import canonical_uuid
from yorunge.domain.upload_checks import AuthorizationCheck, UploadCurrentCheck, require_fresh
from yorunge.domain.upload_graph import STAGE_KINDS, file_index_matches
from yorunge.domain.upload_resume import OperationJournal
from yorunge.domain.upload_versions import (
    UploadApproval,
    UploadPlan,
    UploadReceipt,
    UploadRecord,
    UploadVerification,
    graph_of,
    validate_create_receipt,
    verification_scope,
)
from yorunge.domain.upload_versions import (
    proof_digest as verification_digest,
)


def continuation_action(plan: DatasetContinuationPlanV3) -> tuple[UploadPermission, str]:
    """What a continuation needs first: to upload into its dataset, or (sending nothing) to read."""
    binding = plan.continuation
    action: UploadPermission = (
        "upload_created_dataset" if binding.file_indices else "read_created_dataset"
    )
    return action, binding.dataset_id


def _arm_input(kind: StageKind, file_index: int | None, total_end: float) -> None:
    if type(kind) is not str or kind not in STAGE_KINDS or not file_index_matches(kind, file_index):
        raise YorungeError("invalid_request")
    finite = False
    if type(total_end) in (int, float):
        try:
            finite = math.isfinite(total_end)
        except OverflowError:
            pass
    if not finite:
        raise YorungeError("invalid_request")


def _arm_permission(kind: StageKind) -> UploadPermission:
    if kind == "create":
        return "create_private_dataset"
    if kind == "project_link":
        return "link_project"
    return "upload_created_dataset"


def _arm_predecessors(
    view: VersionedTransferView, kind: StageKind, file_index: int | None
) -> dict[tuple[StageKind, int | None], UploadReceipt]:
    receipt_map = {i.intent_id: i for i in view.intents}
    accepted = {
        (receipt_map[r.intent_id].kind, receipt_map[r.intent_id].file_index): r
        for r in view.receipts
        if r.result == "accepted"
    }
    if any((i.kind, i.file_index) == (kind, file_index) for i in view.intents):
        raise YorungeError("operation_conflict")
    graph = graph_of(view.plan)
    required = graph.predecessor(kind, file_index)
    if required is not None and required not in accepted:
        raise YorungeError("operation_conflict")
    if file_index is not None and (type(file_index) is not int or file_index not in graph.files):
        raise YorungeError("invalid_request")
    return accepted


def _typed_receipt(receipt: UploadReceipt) -> UploadReceipt:
    if type(receipt) is CreateReceiptV2:
        return revalidate_input(CreateReceiptV2, receipt)
    if type(receipt) is StageReceipt:
        return revalidate_input(StageReceipt, receipt)
    raise YorungeError("invalid_request")


def _receipt_record(
    record: UploadRecord,
    intent: StageIntent,
    receipt: UploadReceipt,
    receipts: tuple[UploadReceipt, ...],
    owner: TransferLease,
    intent_count: int,
) -> UploadRecord:
    dataset_id = (
        receipt.dataset_id
        if intent.kind == "create" and receipt.result == "accepted"
        else record.dataset_id
    )
    rejected = receipt.result == "rejected" or any(r.result == "rejected" for r in receipts)
    unresolved = intent_count > len(receipts) + 1
    # A late receipt settles its own intent; it cannot restore the write path.
    status = "running"
    reason: str | None = None
    if record.status == "unknown":
        status, reason = record.status, record.reason
    if rejected:
        status = "unknown" if unresolved else "failed"
        reason = "provider_rejected"
    return record.model_copy(
        update={
            "dataset_id": dataset_id,
            "status": status,
            "lease": None if status == "failed" else owner,
            "reason": reason,
        }
    )


@dataclass(frozen=True)
class UploadListEntry:
    plan_id: str
    digest: str
    prepared_at: str
    status: str
    operation_id: str | None
    operation_status: str | None


def list_entry(view: VersionedTransferView) -> UploadListEntry:
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
        self,
        store: Store,
        credential: BoundCredential | None = None,
        *,
        clock: Clock | None = None,
        write_access: TransferWriteAccess | None = None,
    ) -> None:
        self.store, self.connection = store, store.connection
        self.credential, self.write_access = credential, write_access
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
        self,
        plan: UploadPlan,
        fresh: UploadCurrentCheck | UploadPlan,
        stamp: Stamp,
        gate: TimeGate,
        *,
        action: UploadPermission = "create_private_dataset",
        dataset_id: str | None = None,
    ) -> tuple[str, ...]:
        if (
            not isinstance(plan, DatasetUploadPlanV2 | DatasetContinuationPlanV3)
            or not isinstance(fresh, UploadCurrentCheck)
            or plan.status == "draft"
        ):
            raise YorungeError("upload_plan_not_valid")
        self._credential(plan.scope, stamp)
        fresh = decode(UploadCurrentCheck, fresh.encoded().decode("ascii"))
        gate.require_range(
            instant(plan.prepared_at), instant(plan.expires_at), error="upload_plan_not_valid"
        )
        terms = fresh.require_current(
            plan, now=timestamp(stamp.now), action=action, dataset_id=dataset_id
        )
        self._current_ranges(plan, fresh, gate, action=action)
        gate.require_clock(stamp, error="state_changed")
        return terms

    @staticmethod
    def _current_ranges(
        plan: DatasetUploadPlanV2 | DatasetContinuationPlanV3,
        fresh: UploadCurrentCheck,
        gate: TimeGate,
        *,
        action: UploadPermission,
    ) -> None:
        evidence = (
            plan.grant,
            plan.cost_bound,
            fresh.baseline_grant,
            fresh.baseline_cost_bound,
            fresh.supplemental_grant,
            fresh.supplemental_cost_bound,
            fresh.authorization.grant,
        )
        for value in evidence:
            if value is not None:
                gate.require_range(
                    instant(value.checked_at),
                    instant(value.expires_at),
                    error="upload_plan_not_valid",
                )
        observed = [fresh.checked_at, fresh.authorization.checked_at]
        if action == "upload_created_dataset" and fresh.upload_observation is not None:
            observed.append(fresh.upload_observation.checked_at)
        for checked_at in observed:
            # UTC wire precision is one microsecond; age exactly 30 s is permitted.
            checked = instant(checked_at)
            gate.require_range(
                checked,
                checked + timedelta(seconds=30, microseconds=1),
                error="upload_plan_not_valid",
            )

    def _approved(self, view: VersionedTransferView, gate: TimeGate) -> UploadApproval:
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
        final, within = self.cache._finish(
            stamp,
            expires=tuple(end for _, end, _ in gate.intervals),
            checkpoint=gate.checkpoint,
        )
        self._credential(scope, final)
        gate.check_clock(final)
        gate.check(final.now)
        if not within:
            raise YorungeError("state_busy")

    def _namespace_available(self, digest: str) -> None:
        active = self.connection.execute(
            "SELECT create_operation_id FROM upload_namespaces WHERE "
            "intent_digest=? AND create_operation_id IS NOT NULL",
            (digest,),
        ).fetchone()
        if active is not None:
            raise OperationError("operation_conflict", active[0])

    def check_scope(self, scope: UploadScope, *, name: str | None = None) -> None:
        """Short current-state phase; never holds a transaction across file/network I/O."""
        with self.phase():
            scope = decode(UploadScope, scope.encoded().decode("ascii"))
            self._secret(scope)
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="state_changed") as gate:
                self._credential(scope, stamp)
                gate.require_clock(stamp, error="state_changed")
                if name is not None:
                    digest = hashlib.sha256(upload_namespace(scope, name)).hexdigest()
                    self._namespace_available(digest)
            self._finish(stamp, gate, scope=scope)

    @staticmethod
    def _preparation_check(
        plan: UploadPlan, check: AuthorizationCheck, stamp: Stamp, gate: TimeGate
    ) -> None:
        if not isinstance(plan, DatasetUploadPlanV2):
            raise YorungeError("upload_plan_not_valid")
        check.require_current(plan.scope, "create_private_dataset", None, timestamp(stamp.now))
        if (
            check.consumer_profile != "evren-platform-observed-upload-v2"
            or check.outcome != "not_exposed"
            or plan.grant is not None
            or plan.cost_bound is not None
        ):
            raise YorungeError("upload_plan_not_valid")
        checked = instant(check.checked_at)
        gate.require_range(
            checked, checked + timedelta(seconds=30, microseconds=1), error="upload_plan_not_valid"
        )

    def save(
        self,
        plan: UploadPlan,
        manifest: DatasetManifest,
        *,
        authorization: AuthorizationCheck | None = None,
    ) -> VersionedTransferView:
        with self.phase():
            plan = decode_versioned(
                DatasetUploadPlan,
                DatasetUploadPlanV2,
                plan.encoded().decode("ascii"),
                DatasetContinuationPlanV3,
            )
            if manifest_reference(manifest) != plan.manifest:
                raise YorungeError("input_changed")
            self._secret(plan)
            self._secret(manifest)
            if authorization is not None:
                authorization = decode(AuthorizationCheck, authorization.encoded().decode("ascii"))
                self._secret(authorization)
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="state_changed") as gate:
                self._credential(plan.scope, stamp)
                if authorization is not None:
                    self._preparation_check(plan, authorization, stamp, gate)
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
                    if not isinstance(plan, DatasetContinuationPlanV3):
                        # A continuation shares its root's namespace and makes no create right.
                        self._namespace_available(plan.intent_digest())
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

    def show(
        self, *, plan_id: str | None = None, operation_id: str | None = None
    ) -> VersionedTransferView:
        return self._show(plan_id, operation_id)[0]

    def _show(
        self, plan_id: str | None, operation_id: str | None
    ) -> tuple[VersionedTransferView, Lineage | None]:
        """A stored view and, for a continuation, the lineage it was validated with.

        Both come from one read transaction, so a caller that needs the baseline does not walk the
        lineage a second time, nor from another state than the one its status was read in.
        """
        if (plan_id is None) == (operation_id is None):
            raise YorungeError("invalid_request")
        with self.phase(operation_id), read_snapshot(self.connection):
            if operation_id is not None:
                plan_id = read_record(self.connection, operation_id).plan_id
            assert plan_id is not None
            return read_view_and_lineage(self.connection, plan_id)

    def operation_journal(self, operation_id: str) -> OperationJournal:
        """Read-only stage facts for the resume classifier; writes nothing and grants nothing."""
        with self.phase(operation_id):
            return stored_journal(self.show(operation_id=operation_id))

    def chain_snapshot(self, operation_id: str, stamp: Stamp) -> ChainSnapshot:
        """The journals of a source's lineage, its facts and its descendants, from one snapshot.

        Separate reads would let a continuation appear between the journals and the descendants.
        ``stamp`` is the caller's clock point for lease activity; nothing is written or granted.
        """
        with self.phase(operation_id), read_snapshot(self.connection):
            return stored_snapshot(self.connection, operation_id, stamp)

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
            views: dict[str, VersionedTransferView] = {}  # a source is read once for the page
            return tuple(
                list_entry(read_view(self.connection, r[1], views)) for r in rows[:limit]
            ), encode_cursor(*rows[limit - 1]) if len(rows) > limit else None

    def approve(
        self,
        plan_id: str,
        digest: str,
        fresh: UploadCurrentCheck | UploadPlan,
        *,
        acknowledge_unverified_authority: bool = False,
        acknowledge_unpriced_cost: bool = False,
    ) -> DatasetUploadApprovalV2:
        with self.phase():
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="state_changed") as gate:
                view = read_view(self.connection, plan_id)
                if not isinstance(view.plan, DatasetUploadPlanV2):
                    raise YorungeError("upload_plan_not_valid")  # a continuation has its own
                self._current(view.plan, fresh, stamp, gate)
                if view.operation is not None or view.approval is not None:
                    raise YorungeError("operation_conflict")
                approval = approve_upload_v2(
                    view.plan,
                    approval_id=str(uuid4()),
                    confirmed_digest=digest,
                    approved_at=timestamp(stamp.now),
                    acknowledge_unverified_authority=acknowledge_unverified_authority,
                    acknowledge_unpriced_cost=acknowledge_unpriced_cost,
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

    def approve_continuation(
        self,
        plan_id: str,
        digest: str,
        fresh: UploadCurrentCheck | UploadPlan,
        *,
        acknowledge_unverified_authority: bool = False,
        acknowledge_unpriced_cost: bool = False,
        acknowledge_unconfirmed_effects: bool = False,
    ) -> DatasetUploadApprovalV3:
        """Approve a saved continuation plan: the v2 rules and one more acknowledgement."""
        with self.phase():
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="state_changed") as gate:
                view = read_view(self.connection, plan_id)
                if not isinstance(view.plan, DatasetContinuationPlanV3):
                    raise YorungeError("upload_plan_not_valid")
                # The fresh check must show what the continuation does first.
                action, dataset_id = continuation_action(view.plan)
                self._current(view.plan, fresh, stamp, gate, action=action, dataset_id=dataset_id)
                if view.operation is not None or view.approval is not None:
                    raise YorungeError("operation_conflict")
                approval = approve_upload_v3(
                    view.plan,
                    approval_id=str(uuid4()),
                    confirmed_digest=digest,
                    approved_at=timestamp(stamp.now),
                    acknowledge_unverified_authority=acknowledge_unverified_authority,
                    acknowledge_unpriced_cost=acknowledge_unpriced_cost,
                    acknowledge_unconfirmed_effects=acknowledge_unconfirmed_effects,
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

    def revoke(self, plan_id: str, digest: str) -> VersionedTransferView:
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
                    changed = decode_versioned(
                        DatasetUploadApproval,
                        DatasetUploadApprovalV2,
                        changed.encoded().decode("ascii"),
                        DatasetUploadApprovalV3,
                    )
                    self.connection.execute(
                        "UPDATE upload_approvals SET payload=? WHERE plan_id=?",
                        (changed.encoded().decode("ascii"), plan_id),
                    )
            return read_view(self.connection, plan_id)

    def admit(self, plan_id: str, fresh: UploadCurrentCheck | UploadPlan) -> UploadRecord:
        before = self.clock.monotonic()
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
                plan = view.plan
                if isinstance(plan, DatasetContinuationPlanV3):
                    action, dataset_id = continuation_action(plan)
                    self._current(plan, fresh, stamp, gate, action=action, dataset_id=dataset_id)
                else:
                    self._current(plan, fresh, stamp, gate)
                approval = self._approved(view, gate)
                lease = self._lease(stamp, fence=1, mode="write")
                operation_id = str(uuid4())
                access = TransferWriteAccess(
                    operation_id,
                    lease.owner_id,
                    before
                    + (
                        min(instant(plan.expires_at), instant(approval.expires_at)) - stamp.now
                    ).total_seconds(),
                )
                record: UploadRecord
                if isinstance(plan, DatasetContinuationPlanV3):
                    record = self._continuation_record(
                        plan, approval, operation_id, lease, access, stamp
                    )
                else:
                    if not isinstance(approval, DatasetUploadApprovalV2):
                        raise YorungeError("upload_plan_not_valid")
                    self._namespace_available(plan.intent_digest())
                    record = TransferRecordV2(
                        schema_version=2,
                        operation_id=operation_id,
                        plan_id=plan_id,
                        plan_digest=plan.digest,
                        intent_digest=plan.intent_digest(),
                        approval=approval,
                        write_owner_id=lease.owner_id,
                        write_access_digest=access.digest,
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
                self._finish(stamp, gate, scope=plan.scope)
            self.write_access = access
            return record

    def _continuation_record(
        self,
        plan: DatasetContinuationPlanV3,
        approval: UploadApproval,
        operation_id: str,
        lease: TransferLease,
        access: TransferWriteAccess,
        stamp: Stamp,
    ) -> TransferRecordV3:
        """The admitted record of a continuation, once the chain it extends allows one more link.

        The source must be frozen and alone at the end of its chain; a descendant of it that was
        admitted but let its lease lapse is cancelled here, in the same transaction, because the
        store never holds two descendants of one source that are not cancelled. The approval is
        bound to the plan when the view is read and the record is bound to both when it is written.
        """
        if not isinstance(approval, DatasetUploadApprovalV3):
            raise YorungeError("upload_plan_not_valid")
        for lapsed in continuation_admission(self.connection, plan, stamp):
            self._cancel_unlatched(read_record(self.connection, lapsed), stamp)
        return TransferRecordV3(
            schema_version=3,
            operation_id=operation_id,
            plan_id=plan.plan_id,
            plan_digest=plan.digest,
            intent_digest=plan.intent_digest(),
            approval=approval,
            write_owner_id=lease.owner_id,
            write_access_digest=access.digest,
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
            verification_only=not plan.continuation.file_indices,
            dataset_id=plan.continuation.dataset_id,
            reason=None,
        )

    def _cancel_unlatched(self, record: UploadRecord, stamp: Stamp) -> UploadRecord:
        """Close an admitted operation that sent nothing: its approval and its lease say why."""
        view = read_view(self.connection, record.plan_id)
        reason: TransferReason = "lease_expired"
        if view.approval is not None and view.approval.status == "revoked":
            reason = "approval_revoked"
        elif stamp.now >= instant(record.approval.expires_at):
            reason = "approval_expired"
        changed = self._change(
            record,
            stamp,
            lease=None,
            fence=record.fence + 1,
            status="cancelled",
            reason=reason,
        )
        self._control(changed, stamp, terminal=True)
        return changed

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
        self, record: UploadRecord, owner: TransferLease, stamp: Stamp, gate: TimeGate
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
        if current.mode == "write":
            if type(self.write_access) is not TransferWriteAccess:
                raise YorungeError("operation_lease_lost")
            self.write_access.require(record, self.clock.monotonic())
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

    def _change(self, record: UploadRecord, stamp: Stamp, **changes: object) -> UploadRecord:
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
        updated = decode_versioned(
            TransferRecord, TransferRecordV2, updated.encoded().decode("ascii"), TransferRecordV3
        )
        write_record(self.connection, updated, record.revision)
        return updated

    def _control(
        self,
        record: UploadRecord,
        stamp: Stamp,
        *,
        terminal: bool,
        proof: UploadVerification | None = None,
    ) -> None:
        assert record.reason is not None
        body = {
            "schema_version": record.schema_version,
            "kind": "terminal" if terminal else "recovery",
            "operation_id": record.operation_id,
            "revision": record.revision,
            "observed_at": record.updated_at,
            "identity_epoch": stamp.identity_epoch,
            "clock_generation": stamp.generation,
            "reason": record.reason,
            "verification_digest": verification_digest(proof) if proof else None,
        }
        from yorunge.domain.capabilities import canonical

        value = decode_versioned(
            TransferControl,
            TransferControlV2,
            canonical(body).decode("ascii"),
            TransferControlV3,
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
        self,
        operation_id: str,
        owner: TransferLease,
        *,
        grant: UploadGrant | None = None,
        authorization: AuthorizationCheck | None = None,
        accept_unverified_read: bool = False,
    ) -> TransferLease:
        with self.phase(operation_id):
            self._nonterminal(operation_id)
            self.require_created_baseline(operation_id, owner)
            if type(accept_unverified_read) is not bool:
                raise YorungeError("invalid_request")
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="operation_lease_lost") as gate:
                view = self.show(operation_id=operation_id)
                record = view.operation
                assert record is not None
                self._baseline_in_view(view)
                owner = self._owner(record, owner, stamp, gate)
                if owner.mode == "read":
                    access = authorize_read(
                        self,
                        view,
                        stamp,
                        gate,
                        grant=grant,
                        authorization=authorization,
                        accept_unverified_read=accept_unverified_read,
                        initial_owner=False,
                    )
                    scope = access.scope
                else:
                    if grant is not None or authorization is not None or accept_unverified_read:
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
        fresh: UploadCurrentCheck | UploadPlan,
        kind: StageKind,
        file_index: int | None,
        *,
        total_end: float,
    ) -> UploadArm:
        with self.phase(operation_id):
            _arm_input(kind, file_index, total_end)
            before = self.clock.monotonic()
            if total_end <= before:
                raise YorungeError("execution_timeout")
            self.require_created_baseline(operation_id, owner)
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="operation_lease_lost") as gate:
                view = self.show(operation_id=operation_id)
                if not isinstance(view.plan, DatasetUploadPlanV2 | DatasetContinuationPlanV3):
                    raise YorungeError("upload_plan_not_valid")
                record = view.operation
                assert record is not None
                if isinstance(view.plan, DatasetContinuationPlanV3) and kind in {
                    "create",
                    "project_link",
                }:
                    # The dataset exists: a continuation has no create and no link to arm.
                    raise YorungeError("invalid_request")
                self._baseline_in_view(view)
                owner = self._owner(record, owner, stamp, gate)
                if owner.mode != "write" or record.status not in {"admitted", "running"}:
                    raise YorungeError("operation_conflict")
                if isinstance(record, TransferRecordV3) and record.verification_only:
                    # A check-only continuation sends nothing, so it has no stage to arm.
                    raise YorungeError("operation_conflict")
                assert self.write_access is not None
                total_end = min(total_end, self.write_access.end)
                action = _arm_permission(kind)
                terms = self._current(
                    view.plan, fresh, stamp, gate, action=action, dataset_id=record.dataset_id
                )
                if self._approved(view, gate) != record.approval:
                    raise YorungeError("state_changed")
                accepted = _arm_predecessors(view, kind, file_index)
                owner = self._renewed(owner, stamp)
                record = record.model_copy(update={"lease": owner})
                end = min(
                    instant(owner.expires_at),
                    instant(record.approval.expires_at),
                    instant(view.plan.expires_at),
                    *(instant(term) for term in terms),
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
                # An elapsed dispatch deadline keeps its error precedence when
                # current evidence also ages out during the same transaction.
                gate.intervals.insert(
                    0,
                    (
                        stamp.now,
                        end - timedelta(seconds=COMMIT_MARGIN_SECONDS),
                        "execution_timeout",
                    ),
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
                issued = _issue_upload_arm(intent, deadline, self.clock.monotonic)
            except YorungeError as error:
                raise OperationError(
                    "operation_uncertain", operation_id, reason_code=error.code
                ) from None
            return issued

    def receipt(
        self, operation_id: str, owner: TransferLease, receipt: UploadReceipt
    ) -> VersionedTransferView:
        with self.phase(operation_id):
            receipt = _typed_receipt(receipt)
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
                self._baseline_in_view(view)
                if isinstance(view.plan, DatasetContinuationPlanV3):
                    if isinstance(receipt, CreateReceiptV2):  # it makes no dataset to receipt
                        raise YorungeError("invalid_request")
                elif (
                    isinstance(view.plan, DatasetUploadPlanV2)
                    and intent.kind == "create"
                    and receipt.result == "accepted"
                    and not isinstance(receipt, CreateReceiptV2)
                ):
                    raise YorungeError("state_invalid")
                if isinstance(receipt, CreateReceiptV2):
                    validate_create_receipt(view.plan, intent, receipt)
                changed = _receipt_record(
                    record, intent, receipt, view.receipts, owner, len(view.intents)
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
    ) -> VersionedTransferView:
        with self.phase(operation_id):
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="operation_lease_lost") as gate:
                view = self.show(operation_id=operation_id)
                record = view.operation
                assert record is not None
                owner = self._owner(record, owner, stamp, gate)
                if reason not in {"request_uncertain", "local_cancelled"}:
                    raise YorungeError("invalid_request")
                if isinstance(record, TransferRecordV3) and not record.workflow_latched:
                    # Before its first intent nothing is uncertain: the operation is cancelled.
                    reason = "local_cancelled"
                changed = self._change(
                    record,
                    stamp,
                    lease=None,
                    status="unknown" if record.workflow_latched else "cancelled",
                    reason=reason,
                )
                self._control(changed, stamp, terminal=not record.workflow_latched)
            return self.show(operation_id=operation_id)

    def acquire_read(
        self,
        operation_id: str,
        grant: UploadGrant | None = None,
        *,
        authorization: AuthorizationCheck | None = None,
        accept_unverified_read: bool = False,
    ) -> TransferLease:
        with self.phase(operation_id):
            existing = self._nonterminal(operation_id)
            self.require_created_baseline(operation_id)
            assert existing.operation is not None
            if not existing.operation.workflow_latched or existing.operation.dataset_id is None:
                cleaned = self.cleanup_expired(operation_id)
                assert cleaned.operation is not None
                raise YorungeError(
                    "operation_uncertain"
                    if cleaned.operation.workflow_latched
                    else "operation_conflict"
                )
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="operation_lease_lost") as gate:
                view = self.show(operation_id=operation_id)
                record = view.operation
                assert record is not None
                self._baseline_in_view(view)
                if record.status in TERMINAL:
                    raise YorungeError("operation_conflict")
                if record.workflow_latched and record.dataset_id is None:
                    raise YorungeError("operation_uncertain")
                access = authorize_read(
                    self,
                    view,
                    stamp,
                    gate,
                    grant=grant,
                    authorization=authorization,
                    accept_unverified_read=accept_unverified_read,
                    initial_owner=False,
                )
                self._takeover_allowed(record, stamp)
                if not record.workflow_latched:
                    raise YorungeError("operation_conflict")
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
            self._finish(stamp, gate, scope=access.scope)
            return lease

    @staticmethod
    def _takeover_allowed(record: UploadRecord, stamp: Stamp) -> None:
        if timestamp(stamp.now) < record.updated_at:
            raise YorungeError("operation_conflict")
        lease = record.lease
        if lease is not None and (
            (lease.identity_epoch, lease.clock_generation)
            == (stamp.identity_epoch, stamp.generation)
            and instant(lease.expires_at) > stamp.now
        ):
            raise YorungeError("operation_conflict")
        if record.fence >= 2**63 - 1:
            raise YorungeError("operation_fence_exhausted")

    def cleanup_expired(self, operation_id: str) -> VersionedTransferView:
        """Non-executing local cleanup; no grant, remote lookup or permit is produced."""
        with self.phase(operation_id):
            self._nonterminal(operation_id)
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="operation_lease_lost") as gate:
                view = self._nonterminal(operation_id)
                record = view.operation
                assert record is not None
                self._takeover_allowed(record, stamp)
                if (
                    legacy_create_without_baseline(view)
                    and record.status == "unknown"
                    and record.reason == "request_uncertain"
                    and record.lease is None
                ):
                    # A concurrent local cleanup already closed the same legacy
                    # state; no new fence/revision is required for inspection.
                    return view
                reason: TransferReason = "request_uncertain"
                if not record.workflow_latched:
                    reason = "lease_expired"
                    if view.approval is not None and view.approval.status == "revoked":
                        reason = "approval_revoked"
                    elif stamp.now >= instant(record.approval.expires_at):
                        reason = "approval_expired"
                changed = self._change(
                    record,
                    stamp,
                    lease=None,
                    fence=record.fence + 1,
                    status="unknown" if record.workflow_latched else "cancelled",
                    reason=reason,
                )
                self._control(changed, stamp, terminal=not record.workflow_latched)
            final, within = self.cache._finish(
                stamp,
                expires=tuple(end for _, end, _ in gate.intervals),
                checkpoint=gate.checkpoint,
            )
            gate.check_clock(final)
            gate.check(final.now)
            if not within:
                raise YorungeError("state_busy")
            return self.show(operation_id=operation_id)

    def freeze_source(self, operation_id: str) -> VersionedTransferView:
        """Freeze the source a continuation is prepared from: what ``--prepare`` writes first.

        A source that was running when its lease lapsed becomes unknown, exactly as the cleanup of
        an expired operation does; a source that is already unknown is left as it is (its reason
        and its fence stay, so two processes preparing at once freeze it once); a source with a live
        lease is active and nothing is changed. Descendants that were admitted, sent nothing and let
        their lease lapse are cancelled in the same transaction.
        """
        with self.phase(operation_id):
            self._nonterminal(operation_id)
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="operation_lease_lost") as gate:
                view = self._nonterminal(operation_id)
                record = view.operation
                assert record is not None
                if not record.workflow_latched:
                    raise YorungeError("operation_conflict")  # nothing was sent: not a source
                for descendant in stored_snapshot(self.connection, operation_id, stamp).descendants:
                    if descendant.status == "admitted" and not descendant.lease_active:
                        self._cancel_unlatched(
                            read_record(self.connection, descendant.operation_id), stamp
                        )
                if record.status != "unknown":
                    self._takeover_allowed(record, stamp)  # a live lease is someone else's
                    changed = self._change(
                        record,
                        stamp,
                        lease=None,
                        fence=record.fence + 1,
                        status="unknown",
                        reason="request_uncertain",
                    )
                    self._control(changed, stamp, terminal=False)
            # Like the cleanup of an expired operation, freezing needs no credential: a source is
            # frozen after a rotation too, and never reports an error for what it has committed.
            final, within = self.cache._finish(
                stamp,
                expires=tuple(end for _, end, _ in gate.intervals),
                checkpoint=gate.checkpoint,
            )
            gate.check_clock(final)
            gate.check(final.now)
            if not within:
                raise YorungeError("state_busy")
            return self.show(operation_id=operation_id)

    def _read_grant(
        self, view: VersionedTransferView, grant: UploadGrant, stamp: Stamp, gate: TimeGate
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

    def _nonterminal(self, operation_id: str) -> VersionedTransferView:
        return self._nonterminal_with_lineage(operation_id)[0]

    def _nonterminal_with_lineage(
        self, operation_id: str
    ) -> tuple[VersionedTransferView, Lineage | None]:
        view, lineage = self._show(None, operation_id)
        assert view.operation is not None
        if view.operation.status in TERMINAL:
            raise YorungeError("operation_conflict")
        return view, lineage

    @staticmethod
    def _baseline_in_view(view: VersionedTransferView) -> None:
        """Repeat inside mutation savepoints; a preflight observation is not a lock."""
        if legacy_create_without_baseline(view):
            assert view.operation is not None
            raise OperationError("operation_uncertain", view.operation.operation_id)

    def require_created_baseline(
        self, operation_id: str, owner: TransferLease | None = None
    ) -> ProviderDataset | None:
        """Local pre-HTTP gate; an unsuccessful marker never claims a new permission."""
        with self.phase(operation_id):
            view, lineage = self._nonterminal_with_lineage(operation_id)
            if lineage is not None:
                # A continuation's baseline is its root's, found as its lineage was validated.
                return lineage.baseline
            if not legacy_create_without_baseline(view):
                return created_dataset(view)
            record = view.operation
            assert record is not None
            if record.status == "unknown" and record.reason == "request_uncertain":
                raise OperationError("operation_uncertain", operation_id)
            try:
                if (
                    owner is not None
                    and record.lease is not None
                    and instant(record.lease.expires_at) > self.clock.now()
                ):
                    self._uncertain_verification(operation_id, owner)
                else:
                    self.cleanup_expired(operation_id)
            except YorungeError as error:
                raise OperationError(
                    "operation_uncertain", operation_id, reason_code=error.code
                ) from None
            raise OperationError("operation_uncertain", operation_id)

    def read_failed(
        self,
        operation_id: str,
        owner: TransferLease | None,
        authorization: AuthorizationCheck,
    ) -> None:
        """Record a failed read without claiming failed execution or a new permission."""
        with self.phase(operation_id):
            self._nonterminal(operation_id)
            self.require_created_baseline(operation_id, owner)
            check = decode(AuthorizationCheck, authorization.encoded().decode("ascii"))
            code = check.error_code
            if (
                code is None
                or code
                not in {
                    "remote_access_denied",
                    "remote_rate_limited",
                    "remote_failed",
                    "transport_timeout",
                    "transport_failed",
                    "invalid_response",
                }
                or check.action != "read_created_dataset"
            ):
                raise YorungeError("invalid_request")
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="operation_lease_lost") as gate:
                view = self._nonterminal(operation_id)
                record = view.operation
                assert record is not None
                self._baseline_in_view(view)
                check_only = isinstance(record, TransferRecordV3) and record.verification_only
                if (
                    isinstance(record, TransferRecordV3)
                    and not record.workflow_latched
                    and not check_only
                ):
                    # Nothing was sent and nothing is read yet: there is nothing to be uncertain
                    # about, and nothing for this call to report.
                    raise YorungeError("operation_conflict")
                if not check_only and (not record.workflow_latched or record.dataset_id is None):
                    raise YorungeError("operation_uncertain")
                self._credential(check.scope, stamp)
                if (
                    scope_target(check.scope) != scope_target(view.plan.scope)
                    or check.dataset_id != record.dataset_id
                    or instant(check.checked_at) > stamp.now
                ):
                    raise YorungeError("state_changed")
                require_fresh(check.checked_at, timestamp(stamp.now))
                checked = instant(check.checked_at)
                gate.require_range(
                    checked,
                    checked + timedelta(seconds=30, microseconds=1),
                    error="upload_plan_not_valid",
                )
                active_write = False
                fence = record.fence
                if check_only:
                    # Nothing was sent, so nothing is uncertain: it is cancelled, and the caller
                    # gets the read's own error rather than "operation_uncertain".
                    if owner is None:
                        raise YorungeError("operation_conflict")
                    self._owner(record, owner, stamp, gate)
                    changed = self._change(
                        record, stamp, lease=None, status="cancelled", reason="local_cancelled"
                    )
                    self._control(changed, stamp, terminal=True)
                else:
                    if owner is None:
                        self._takeover_allowed(record, stamp)
                        fence += 1
                    else:
                        current = self._owner(record, owner, stamp, gate)
                        active_write = current.mode == "write"
                    changed = self._change(
                        record,
                        stamp,
                        lease=None,
                        fence=fence,
                        status="unknown",
                        reason="read_unavailable"
                        if record.schema_version in (2, 3)
                        else "request_uncertain",
                    )
                    self._control(changed, stamp, terminal=False)
            self._finish(stamp, gate, scope=check.scope)
            if active_write:
                raise OperationError("operation_uncertain", operation_id, reason_code=code)
            raise OperationError(code, operation_id, reason_code=code)

    def prepare_initial_read(
        self,
        operation_id: str,
        owner: TransferLease,
        *,
        authorization: AuthorizationCheck | None = None,
    ) -> ReadAccess | None:
        """Short local gate, before the read probe and again before item metadata."""
        with self.phase(operation_id):
            self.require_created_baseline(operation_id, owner)
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="operation_lease_lost") as gate:
                view = self._nonterminal(operation_id)
                record = view.operation
                assert record is not None
                self._baseline_in_view(view)
                current = self._owner(record, owner, stamp, gate)
                # A check-only continuation never sends, so it never runs: it reads as admitted.
                check_only = isinstance(record, TransferRecordV3) and record.verification_only
                if current.mode != "write" or record.status != (
                    "admitted" if check_only else "running"
                ):
                    raise YorungeError("operation_conflict")
                self._credential(view.plan.scope, stamp)
                if self._approved(view, gate) != record.approval:
                    raise YorungeError("state_changed")
                if not acknowledged_stages(view):
                    raise YorungeError("operation_uncertain")
                initial_read_consent(view, stamp, gate)
                access = None
                if authorization is not None:
                    self._secret(authorization)
                    access = authorize_read(
                        self,
                        view,
                        stamp,
                        gate,
                        grant=authorization.grant,
                        authorization=authorization,
                        accept_unverified_read=False,
                        initial_owner=True,
                    )
            self._finish(stamp, gate, scope=view.plan.scope)
            return access

    def prepare_recovery_read(
        self,
        operation_id: str,
        owner: TransferLease,
        authorization: AuthorizationCheck,
        *,
        accept_unverified_read: bool = False,
    ) -> ReadAccess:
        """Recheck an acquired read owner before items, without renewing its lease."""
        with self.phase(operation_id):
            self.require_created_baseline(operation_id, owner)
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="operation_lease_lost") as gate:
                view = self._nonterminal(operation_id)
                record = view.operation
                assert record is not None
                self._baseline_in_view(view)
                current = self._owner(record, owner, stamp, gate)
                if current.mode != "read" or record.status != "unknown":
                    raise YorungeError("operation_conflict")
                if not acknowledged_stages(view):
                    raise YorungeError("operation_uncertain")
                authorization = revalidate_input(AuthorizationCheck, authorization)
                self._secret(authorization)
                access = authorize_read(
                    self,
                    view,
                    stamp,
                    gate,
                    grant=authorization.grant,
                    authorization=authorization,
                    accept_unverified_read=accept_unverified_read,
                    initial_owner=False,
                )
            self._finish(stamp, gate, scope=access.scope)
            return access

    def verified(
        self,
        operation_id: str,
        owner: TransferLease,
        proof: UploadVerification,
        *,
        authorization: AuthorizationCheck | None = None,
        accept_unverified_read: bool = False,
        deadline: float | None = None,
    ) -> VersionedTransferView:
        try:
            return self._verified(
                operation_id,
                owner,
                proof,
                authorization=authorization,
                accept_unverified_read=accept_unverified_read,
                deadline=deadline,
            )
        except OperationError as error:
            if error.code == "operation_uncertain":
                try:
                    cancelled = self._uncertain_verification(operation_id, owner)
                except YorungeError as marker_error:
                    if self._sent_nothing(operation_id):
                        # Nothing is uncertain: the marker did not land (the lease is gone) and
                        # the lease cleanup will cancel the operation. This was a late proof.
                        raise OperationError(
                            "execution_timeout", operation_id, reason_code=marker_error.code
                        ) from None
                    raise OperationError(
                        "operation_uncertain", operation_id, reason_code=marker_error.code
                    ) from None
                if cancelled:
                    # A check-only continuation sent nothing: the proof came too late, no more.
                    raise OperationError("execution_timeout", operation_id) from None
            raise

    def _sent_nothing(self, operation_id: str) -> bool:
        """Whether this is a continuation record that never wrote an intent."""
        try:
            record = self.show(operation_id=operation_id).operation
        except YorungeError:
            return False
        return isinstance(record, TransferRecordV3) and not record.workflow_latched

    def _proof_deadline(self, deadline: float | None) -> None:
        if deadline is None:
            return
        valid = type(deadline) in (int, float)
        try:
            valid = valid and math.isfinite(deadline)
        except OverflowError:
            valid = False
        if not valid:
            raise YorungeError("invalid_request")
        if self.clock.monotonic() >= deadline:
            raise YorungeError("execution_timeout")

    def _uncertain_verification(self, operation_id: str, owner: TransferLease) -> bool:
        """Mark a verification whose outcome is unknown; whether it was a plain local cancel."""
        with self.phase(operation_id):
            view = self.show(operation_id=operation_id)
            assert view.operation is not None
            if view.operation.status in TERMINAL or (
                view.operation.status == "unknown" and view.operation.reason == "request_uncertain"
            ):
                return False
            stamp = self.cache.stamp()
            cancelled = False
            with self.cache.transaction(stamp, clock_error="operation_lease_lost") as gate:
                view = self.show(operation_id=operation_id)
                record = view.operation
                assert record is not None
                if record.status in TERMINAL or (
                    record.status == "unknown" and record.reason == "request_uncertain"
                ):
                    return False
                current = self._owner(record, owner, stamp, gate)
                if isinstance(record, TransferRecordV3) and not record.workflow_latched:
                    # No intent was ever written: nothing is uncertain, the operation is cancelled.
                    cancelled = True
                    changed = self._change(
                        record, stamp, status="cancelled", lease=None, reason="local_cancelled"
                    )
                    self._control(changed, stamp, terminal=True)
                else:
                    changed = self._change(
                        record, stamp, status="unknown", lease=current, reason="request_uncertain"
                    )
                    self._control(changed, stamp, terminal=False)
            # This local marker grants no new read or write authority.
            final, within = self.cache._finish(
                stamp,
                expires=tuple(end for _, end, _ in gate.intervals),
                checkpoint=gate.checkpoint,
            )
            gate.check_clock(final)
            gate.check(final.now)
            if not within:
                raise YorungeError("state_busy")
            return cancelled

    def _verified(
        self,
        operation_id: str,
        owner: TransferLease,
        proof: UploadVerification,
        *,
        authorization: AuthorizationCheck | None = None,
        accept_unverified_read: bool = False,
        deadline: float | None = None,
    ) -> VersionedTransferView:
        with self.phase(operation_id):
            self._proof_deadline(deadline)
            self._nonterminal(operation_id)
            self.require_created_baseline(operation_id, owner)
            proof = decode_versioned(
                TransferVerification,
                TransferVerificationV2,
                proof.encoded().decode("ascii"),
                TransferVerificationV3,
            )
            self._secret(proof)
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp, clock_error="operation_lease_lost") as gate:
                view = self.show(operation_id=operation_id)
                record = view.operation
                assert record is not None
                self._baseline_in_view(view)
                if record.status in TERMINAL:
                    raise YorungeError("operation_conflict")
                owner = self._owner(record, owner, stamp, gate)
                if (
                    isinstance(record, TransferRecordV3)
                    and not record.workflow_latched
                    and not record.verification_only
                ):
                    # It has sent nothing yet, so there is nothing to close: the proof is early.
                    raise YorungeError("operation_conflict")
                if proof.schema_version != record.schema_version:
                    raise YorungeError("upload_plan_not_valid")
                access = authorize_read(
                    self,
                    view,
                    stamp,
                    gate,
                    grant=proof.grant,
                    authorization=authorization,
                    accept_unverified_read=accept_unverified_read,
                    initial_owner=owner.mode == "write",
                )
                if verification_scope(proof) != access.scope or (
                    isinstance(proof, TransferVerificationV2 | TransferVerificationV3)
                    and proof.authorization_policy != access.policy
                ):
                    raise YorungeError("upload_plan_not_valid")
                if (
                    record.dataset_id is None
                    or proof.dataset_id != record.dataset_id
                    or instant(proof.observed_at) > stamp.now
                ):
                    raise YorungeError("operation_conflict")
                if proof.schema_version in (2, 3):
                    observed = instant(proof.observed_at)
                    gate.require_range(
                        observed,
                        observed + timedelta(seconds=30, microseconds=1),
                        error="operation_uncertain",
                    )
                    gate.check(stamp.now)
                # All normal write stages must be acknowledged. Recovery without
                # this evidence remains unknown until an exact provider oracle
                # is implemented; an ID/name match cannot manufacture success.
                if not acknowledged_stages(view):
                    raise YorungeError("operation_uncertain")
                try:
                    verification_after(view, proof)
                except ValueError:
                    if isinstance(record, TransferRecordV3) and not record.workflow_latched:
                        # An observation that precedes the operation proves nothing about it, and
                        # one that sent nothing has nothing uncertain: the proof is refused.
                        raise YorungeError("operation_conflict") from None
                    raise YorungeError("operation_uncertain") from None
                changed = self._change(
                    record,
                    stamp,
                    lease=None,
                    status="succeeded",
                    reason="verified" if record.schema_version == 1 else "metadata_verified",
                )
                self.connection.execute(
                    "INSERT INTO upload_verifications VALUES(?,?)",
                    (operation_id, proof.encoded().decode("ascii")),
                )
                self._control(changed, stamp, terminal=True, proof=proof)
                candidate = read_view(self.connection, view.plan.plan_id)
                self._proof_deadline(deadline)
            self._finish(stamp, gate, scope=verification_scope(proof))
            self._proof_deadline(deadline)
            return candidate
