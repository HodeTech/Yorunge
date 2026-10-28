"""Atomic operation admission/ownership on the shared durable-clock transaction."""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from uuid import uuid4

from yorunge.adapters.capability_cache import Stamp, StateCache, TimeGate
from yorunge.adapters.execution_store import read_approval, read_plan
from yorunge.adapters.identity import credential_matches
from yorunge.adapters.operation_store import (
    append_event,
    insert_record,
    plan_authorities,
    read_job,
    read_operation,
    read_snapshot,
    write_attempt,
    write_outcome,
    write_record,
)
from yorunge.adapters.state import Store, sqlite_error_code
from yorunge.application.execution import ExecutionBudget
from yorunge.application.operations import DispatchWindow, OperationClaim, Submission
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.credentials import BoundCredential
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.execution import ExecutionApproval, ExecutionPlan, ExecutionValidity
from yorunge.domain.operations import (
    MAX_ATTEMPTS,
    MAX_EVENTS,
    TERMINAL,
    AttemptView,
    JobSummary,
    JobView,
    OperationAdmission,
    OperationEvent,
    OperationLease,
    OperationOutcome,
    OperationReason,
    OperationRecord,
)
from yorunge.domain.state import canonical_uuid


class StateOperations:
    def __init__(
        self, store: Store, credentials: tuple[BoundCredential, ...], budget: ExecutionBudget
    ) -> None:
        self.store, self.credentials, self.budget = store, credentials, budget
        self.connection = store.connection
        self.cache = StateCache(store, budget.clock, budget_seconds=budget.remaining())
        self.cache.end = budget.end

    @contextmanager
    def phase(self, operation_id: str | None = None) -> Iterator[None]:
        original = self.store.deadline.end
        self.store.deadline.end = min(
            original, time.monotonic() + min(5.0, self.budget.remaining())
        )
        try:
            yield
            self.budget.check()
            self.store.deadline.remaining()
        except OperationError:
            raise
        except YorungeError as error:
            raise OperationError(error.code, operation_id) from None
        except sqlite3.Error as error:
            raise OperationError(sqlite_error_code(error), operation_id) from None
        except OSError:
            raise OperationError("state_write_failed", operation_id) from None
        finally:
            self.store.deadline.end = original

    def plan(self, plan_id: str) -> ExecutionPlan:
        with self.phase():
            return read_plan(self.connection, plan_id)

    def existing(self, plan_id: str) -> JobView | None:
        try:
            canonical_uuid(plan_id)
        except (ValueError, TypeError, AttributeError):
            raise YorungeError("invalid_request") from None
        with self.phase(), read_snapshot(self.connection):
            row = self.connection.execute(
                "SELECT operation_id FROM operations WHERE plan_id=?", (plan_id,)
            ).fetchone()
            return read_job(self.connection, row[0]) if row is not None else None

    def operation(self, operation_id: str) -> OperationRecord:
        with self.phase(operation_id), read_snapshot(self.connection):
            record = read_operation(self.connection, operation_id)
            read_job(self.connection, operation_id, record=record)
            return record

    def _credentials_current(self, plan: ExecutionPlan, stamp: Stamp) -> None:
        for bound in self.credentials:
            identity, credential = bound.identity, bound.credential
            if identity.identity_epoch != stamp.identity_epoch or not credential_matches(
                self.connection,
                identity.credential_id,
                stamp.identity_epoch,
                identity.credential_revision,
                service=credential.reference.service_id,
                origin=credential.target.service_origin,
                base=credential.target.api_base_path,
            ):
                raise YorungeError("state_changed")
        try:
            authorities = plan_authorities(plan)
        except (ValueError, YorungeError):
            raise YorungeError("plan_not_valid") from None
        for authority in authorities:
            if authority.service_id == "local":
                continue
            if not any(
                (
                    bound.identity.credential_id,
                    bound.identity.credential_revision,
                    bound.credential.reference.service_id,
                    bound.credential.target.service_origin,
                    bound.credential.target.api_base_path,
                )
                == (
                    authority.credential_id,
                    authority.credential_revision,
                    authority.service_id,
                    authority.service_origin,
                    authority.api_base_path,
                )
                for bound in self.credentials
            ):
                raise YorungeError("state_changed")

    def _current(
        self,
        plan: ExecutionPlan,
        validity: ExecutionValidity,
        stamp: Stamp,
        gate: TimeGate,
        expected: ExecutionApproval | None = None,
    ) -> ExecutionApproval:
        if read_plan(self.connection, plan.plan_id) != plan:
            raise YorungeError("state_changed")
        self._credentials_current(plan, stamp)
        if (plan.store_id, plan.identity_epoch, plan.clock_generation) != (
            stamp.store_id,
            stamp.identity_epoch,
            stamp.generation,
        ) or stamp.anomaly:
            raise YorungeError("state_changed")
        if (
            not validity.valid
            or validity.valid_until is None
            or (
                validity.plan_id,
                validity.digest,
            )
            != (plan.plan_id, plan.digest)
        ):
            raise YorungeError("plan_not_valid")
        report = validity.approval
        if report is None or not report.effective or report.record is None:
            raise YorungeError("approval_required")
        approval = read_approval(self.connection, plan)
        if approval != report.record or (expected is not None and approval != expected):
            raise YorungeError("state_changed")
        if approval is None or approval.status != "approved":
            raise YorungeError("approval_required")
        until = min(
            instant(validity.valid_until), instant(approval.expires_at), instant(plan.expires_at)
        )
        now = self.cache.now()
        if not instant(approval.approved_at) <= now < until:
            raise YorungeError("plan_not_valid")
        gate.require_range(instant(approval.approved_at), until)
        return approval

    @staticmethod
    def _lease(stamp: Stamp, fence: int, now: datetime) -> OperationLease:
        if fence > 2**63 - 1:
            raise OperationError("operation_fence_exhausted")
        return OperationLease(
            owner_id=str(uuid4()),
            fence=fence,
            ownership_identity_epoch=stamp.identity_epoch,
            ownership_clock_generation=stamp.generation,
            expires_at=timestamp(now + timedelta(seconds=30)),
        )

    @staticmethod
    def _event(record: OperationRecord, attempt: AttemptView) -> OperationEvent:
        s = record.summary
        return OperationEvent(
            sequence=record.event_count,
            revision=s.revision,
            fence=record.fence,
            attempt_id=attempt.attempt_id,
            observed_at=s.updated_at,
            identity_epoch=record.observed_identity_epoch,
            clock_generation=record.observed_clock_generation,
            status=s.status,
            execution_status=s.execution_status,
            delivery_status=s.delivery_status,
            reason_code=attempt.reason_code,
        )

    def admit(self, plan: ExecutionPlan, validity: ExecutionValidity) -> OperationClaim:
        identifier = str(uuid4())
        with self.phase(identifier):
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp) as gate:
                row = self.connection.execute(
                    "SELECT operation_id FROM operations WHERE plan_id=?", (plan.plan_id,)
                ).fetchone()
                if row is not None:
                    return OperationClaim(read_job(self.connection, row[0]), None)
                approval = self._current(plan, validity, stamp, gate)
                now = self.cache.now()
                lease = self._lease(stamp, 1, now)
                admission = OperationAdmission(
                    operation_id=identifier,
                    plan_id=plan.plan_id,
                    plan_digest=plan.digest,
                    store_id=plan.store_id,
                    admission_identity_epoch=stamp.identity_epoch,
                    admission_clock_generation=stamp.generation,
                    approval=approval,
                    authorities=plan_authorities(plan),
                    correlation=str(uuid4()),
                    delivery_required=any(
                        effect.kind != "local_read" for effect in plan.assessment.effects
                    ),
                )
                s = JobSummary(
                    operation_id=identifier,
                    plan_id=plan.plan_id,
                    plan_digest=plan.digest,
                    task=plan.selection.task,
                    tool=plan.selection.tool,
                    execution=plan.selection.execution,
                    created_at=timestamp(now),
                    updated_at=timestamp(now),
                    status="admitted",
                    execution_status="not_started",
                    delivery_status="pending" if admission.delivery_required else "not_required",
                    attempt_count=1,
                    revision=1,
                    clock_anomaly=False,
                )
                record = OperationRecord(
                    admission=admission,
                    summary=s,
                    lease=lease,
                    fence=1,
                    dispatch_attempt_id=None,
                    event_count=1,
                    recovery_reason=None,
                    observed_identity_epoch=stamp.identity_epoch,
                    observed_clock_generation=stamp.generation,
                )
                attempt = AttemptView(
                    attempt_id=str(uuid4()),
                    number=1,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                    status="claimed",
                    provider_run_id=None,
                    provider_status=None,
                    provider_exit_code=None,
                    reason_code=None,
                )
                insert_record(self.connection, record, attempt, self._event(record, attempt))
                gate.require_range(now, instant(lease.expires_at))
            return OperationClaim(read_job(self.connection, identifier), lease)

    def _owner(
        self, record: OperationRecord, owner: OperationLease, stamp: Stamp, gate: TimeGate
    ) -> None:
        lease = record.lease
        if (
            lease is None
            or lease.token() != owner.token()
            or (
                lease.ownership_identity_epoch,
                lease.ownership_clock_generation,
            )
            != (stamp.identity_epoch, stamp.generation)
            or stamp.anomaly
            or self.cache.now() >= instant(lease.expires_at)
        ):
            raise OperationError("operation_lease_lost", record.summary.operation_id)
        gate.require_range(instant("0001-01-01T00:00:00.000000Z"), instant(lease.expires_at))

    def owned(
        self, operation_id: str, owner: OperationLease, *, execution: bool = False
    ) -> OperationRecord:
        with self.phase(operation_id):
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp) as gate:
                record = read_operation(self.connection, operation_id)
                read_job(self.connection, operation_id, record=record)
                self._owner(record, owner, stamp, gate)
                if execution:
                    self._credentials_current(
                        read_plan(self.connection, record.admission.plan_id), stamp
                    )
            return record

    def renew(self, operation_id: str, owner: OperationLease) -> OperationLease:
        with self.phase(operation_id):
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp) as gate:
                record = read_operation(self.connection, operation_id)
                read_job(self.connection, operation_id, record=record)
                self._owner(record, owner, stamp, gate)
                if record.lease is None:
                    raise OperationError("operation_lease_lost", operation_id)
                lease = record.lease.model_copy(
                    update={"expires_at": timestamp(self.cache.now() + timedelta(seconds=30))}
                )
                write_record(
                    self.connection,
                    record.model_copy(update={"lease": lease}),
                    expected_revision=record.summary.revision,
                )
            return lease

    def dispatch_window(self, operation_id: str, owner: OperationLease) -> DispatchWindow:
        # Associate the durable final UTC observation with an earlier monotonic sample.
        # No UTC observation may bypass the store's global expiry watermark.
        with self.phase(operation_id):
            before = self.budget.clock.monotonic()
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp) as gate:
                record = read_operation(self.connection, operation_id)
                read_job(self.connection, operation_id, record=record)
                self._owner(record, owner, stamp, gate)
                self._credentials_current(
                    read_plan(self.connection, record.admission.plan_id), stamp
                )
            if record.lease is None or gate.checkpoint is None:
                raise OperationError("operation_lease_lost", operation_id)
            remaining = (
                instant(record.lease.expires_at) - gate.checkpoint.stamp.now
            ).total_seconds()
            deadline = min(self.budget.end, before + remaining) - 5.0
            if self.budget.clock.monotonic() >= deadline:
                raise OperationError("execution_timeout", operation_id)
            return DispatchWindow(record, deadline)

    def _local_rejection(self, record: OperationRecord, stamp: Stamp) -> OperationReason | None:
        a = record.admission
        approval = read_approval(self.connection, read_plan(self.connection, a.plan_id))
        if (a.admission_identity_epoch, a.admission_clock_generation) != (
            stamp.identity_epoch,
            stamp.generation,
        ):
            return "plan_invalid"
        if approval is not None and approval.status == "revoked":
            return "approval_revoked"
        if approval != a.approval:
            return "approval_changed"
        if self.cache.now() >= instant(a.approval.expires_at):
            return "approval_expired"
        for authority in a.authorities:
            if authority.service_id != "local" and not credential_matches(
                self.connection,
                str(authority.credential_id),
                a.admission_identity_epoch,
                int(authority.credential_revision or 0),
                service=authority.service_id,
                origin=authority.service_origin,
                base=authority.api_base_path,
            ):
                return "credential_changed"
        if record.summary.attempt_count >= MAX_ATTEMPTS:
            return "capacity_exceeded"
        return None

    def _local_terminal(
        self, record: OperationRecord, job: JobView, stamp: Stamp, reason: OperationReason
    ) -> None:
        now = self.cache.now()
        changed = self._progress(
            record,
            stamp,
            now,
            status="failed",
            execution="not_started",
            delivery=record.summary.delivery_status,
            reason=None,
            normal=True,
        )
        changed = changed.model_copy(update={"lease": None})
        attempt = job.attempts[-1].model_copy(
            update={"status": "failed", "updated_at": timestamp(now), "reason_code": reason}
        )
        write_record(self.connection, changed, expected_revision=record.summary.revision)
        write_attempt(self.connection, record.summary.operation_id, attempt)
        append_event(self.connection, record.summary.operation_id, self._event(changed, attempt))
        write_outcome(
            self.connection,
            record.summary.operation_id,
            OperationOutcome(
                recorded_at=timestamp(now),
                execution_status="not_started",
                delivery_status=record.summary.delivery_status,
                provider_exit_code=None,
                reason_code=reason,
            ),
        )

    def takeover(
        self, operation_id: str, validity: ExecutionValidity | None
    ) -> OperationClaim | None:
        with self.phase(operation_id):
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp) as gate:
                record = read_operation(self.connection, operation_id)
                job = read_job(self.connection, operation_id, record=record)
                if record.summary.status in TERMINAL:
                    return OperationClaim(job, None)
                old = record.lease
                if (
                    old is not None
                    and (old.ownership_identity_epoch, old.ownership_clock_generation)
                    == (
                        stamp.identity_epoch,
                        stamp.generation,
                    )
                    and self.cache.now() < instant(old.expires_at)
                ):
                    raise OperationError("operation_lease_lost", operation_id)
                if record.dispatch_attempt_id is None:
                    rejection = self._local_rejection(record, stamp)
                    if rejection is not None:
                        self._local_terminal(record, job, stamp, rejection)
                        return OperationClaim(read_job(self.connection, operation_id), None)
                    if validity is None:
                        return None
                    self._current(job.plan, validity, stamp, gate, record.admission.approval)
                now = self.cache.now()
                lease = self._lease(stamp, record.fence + 1, now)
                if record.dispatch_attempt_id is None:
                    attempt = AttemptView(
                        attempt_id=str(uuid4()),
                        number=record.summary.attempt_count + 1,
                        created_at=timestamp(now),
                        updated_at=timestamp(now),
                        status="claimed",
                        provider_run_id=None,
                        provider_status=None,
                        provider_exit_code=None,
                        reason_code=None,
                    )
                    changed = self._progress(
                        record,
                        stamp,
                        now,
                        status="admitted",
                        execution="not_started",
                        delivery=record.summary.delivery_status,
                        reason=None,
                        normal=False,
                    )
                    changed = changed.model_copy(
                        update={
                            "summary": changed.summary.model_copy(
                                update={"attempt_count": attempt.number}
                            ),
                            "fence": lease.fence,
                            "lease": lease,
                        }
                    )
                    write_record(
                        self.connection, changed, expected_revision=record.summary.revision
                    )
                    write_attempt(
                        self.connection,
                        operation_id,
                        job.attempts[-1].model_copy(
                            update={
                                "status": "abandoned",
                                "updated_at": timestamp(now),
                                "reason_code": "lease_expired" if old else "owner_changed",
                            }
                        ),
                    )
                    write_attempt(self.connection, operation_id, attempt)
                else:
                    reason: OperationReason = "lease_expired" if old else "owner_changed"
                    changed = self._progress(
                        record,
                        stamp,
                        now,
                        status="unknown",
                        execution="succeeded"
                        if record.summary.execution_status == "succeeded"
                        else "unknown",
                        delivery="unknown"
                        if record.summary.execution_status == "succeeded"
                        else record.summary.delivery_status,
                        reason=reason,
                        normal=False,
                    )
                    changed = changed.model_copy(update={"fence": lease.fence, "lease": lease})
                    write_record(
                        self.connection, changed, expected_revision=record.summary.revision
                    )
                    write_attempt(
                        self.connection,
                        operation_id,
                        job.attempts[-1].model_copy(
                            update={
                                "status": "unknown",
                                "updated_at": timestamp(now),
                                "reason_code": reason,
                            }
                        ),
                    )
                gate.require_range(now, instant(lease.expires_at))
                result = read_job(self.connection, operation_id)
            return OperationClaim(result, lease)

    def arm(
        self, operation_id: str, owner: OperationLease, validity: ExecutionValidity
    ) -> OperationRecord:
        with self.phase(operation_id):
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp) as gate:
                record = read_operation(self.connection, operation_id)
                job = read_job(self.connection, operation_id, record=record)
                self._owner(record, owner, stamp, gate)
                if record.dispatch_attempt_id is not None or record.summary.status != "admitted":
                    raise OperationError("operation_conflict", operation_id)
                self._current(job.plan, validity, stamp, gate, record.admission.approval)
                if record.event_count >= MAX_EVENTS - 2:
                    raise OperationError(
                        "operation_capacity_exceeded", operation_id, capacity_kind="transition"
                    )
                now = self.cache.now()
                lease = record.lease
                if lease is None:
                    raise OperationError("operation_lease_lost", operation_id)
                lease = lease.model_copy(
                    update={"expires_at": timestamp(now + timedelta(seconds=30))}
                )
                attempt = job.attempts[-1].model_copy(
                    update={"status": "submitted", "updated_at": timestamp(now)}
                )
                changed = self._progress(
                    record,
                    stamp,
                    now,
                    status="submitted",
                    execution="submitted",
                    delivery=record.summary.delivery_status,
                    reason=None,
                    normal=True,
                )
                changed = changed.model_copy(
                    update={"dispatch_attempt_id": attempt.attempt_id, "lease": lease}
                )
                write_record(self.connection, changed, expected_revision=record.summary.revision)
                write_attempt(self.connection, operation_id, attempt)
                append_event(self.connection, operation_id, self._event(changed, attempt))
                read_job(self.connection, operation_id)
            return changed

    @staticmethod
    def _progress(
        record: OperationRecord,
        stamp: Stamp,
        now: datetime,
        *,
        status: str,
        execution: str,
        delivery: str,
        reason: OperationReason | None,
        normal: bool,
    ) -> OperationRecord:
        s = record.summary
        return record.model_copy(
            update={
                "summary": s.model_copy(
                    update={
                        "status": status,
                        "execution_status": execution,
                        "delivery_status": delivery,
                        "updated_at": timestamp(now),
                        "revision": s.revision + 1,
                        "clock_anomaly": s.clock_anomaly or timestamp(now) < s.updated_at,
                    }
                ),
                "event_count": record.event_count + int(normal),
                "recovery_reason": reason,
                "observed_identity_epoch": stamp.identity_epoch,
                "observed_clock_generation": stamp.generation,
            }
        )

    def submitted(self, operation_id: str, owner: OperationLease, receipt: Submission) -> JobView:
        with self.phase(operation_id):
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp) as gate:
                record = read_operation(self.connection, operation_id)
                job = read_job(self.connection, operation_id, record=record)
                self._owner(record, owner, stamp, gate)
                if (
                    record.dispatch_attempt_id is None
                    or receipt.correlation != record.admission.correlation
                    or receipt.authority not in record.admission.authorities
                ):
                    raise OperationError("operation_conflict", operation_id)
                if record.event_count >= MAX_EVENTS - 1:
                    raise OperationError(
                        "operation_capacity_exceeded", operation_id, capacity_kind="transition"
                    )
                now = self.cache.now()
                status = "running" if receipt.running else "submitted"
                attempt = job.attempts[-1].model_copy(
                    update={
                        "status": status,
                        "updated_at": timestamp(now),
                        "provider_run_id": receipt.provider_run_id,
                        "provider_status": receipt.provider_status,
                        "reason_code": None,
                    }
                )
                changed = self._progress(
                    record,
                    stamp,
                    now,
                    status=status,
                    execution=status,
                    delivery=record.summary.delivery_status,
                    reason=None,
                    normal=True,
                )
                write_record(self.connection, changed, expected_revision=record.summary.revision)
                write_attempt(self.connection, operation_id, attempt)
                append_event(self.connection, operation_id, self._event(changed, attempt))
                result = read_job(self.connection, operation_id)
            return result

    def uncertain(self, operation_id: str, owner: OperationLease) -> None:
        with self.phase(operation_id):
            stamp = self.cache.stamp()
            with self.cache.transaction(stamp) as gate:
                record = read_operation(self.connection, operation_id)
                job = read_job(self.connection, operation_id, record=record)
                self._owner(record, owner, stamp, gate)
                now = self.cache.now()
                changed = self._progress(
                    record,
                    stamp,
                    now,
                    status="unknown",
                    execution="succeeded"
                    if record.summary.execution_status == "succeeded"
                    else "unknown",
                    delivery="unknown"
                    if record.summary.execution_status == "succeeded"
                    else record.summary.delivery_status,
                    reason="dispatch_interrupted",
                    normal=False,
                )
                attempt = job.attempts[-1].model_copy(
                    update={
                        "status": "unknown",
                        "updated_at": timestamp(now),
                        "reason_code": "dispatch_interrupted",
                    }
                )
                write_record(self.connection, changed, expected_revision=record.summary.revision)
                write_attempt(self.connection, operation_id, attempt)
                read_job(self.connection, operation_id)
