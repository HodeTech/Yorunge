"""Strict immutable plan persistence, bounded listing and final state/time gates."""

from __future__ import annotations

import base64
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from yorunge.adapters.capability_cache import Stamp, StateCache
from yorunge.adapters.state import Store, metadata, sqlite_error_code
from yorunge.application.execution import ExecutionBudget
from yorunge.domain.capabilities import canonical, instant, timestamp
from yorunge.domain.errors import YorungeError
from yorunge.domain.execution import (
    ExecutionApproval,
    ExecutionApprovalState,
    ExecutionMoment,
    ExecutionPlan,
    ExecutionPlans,
    ExecutionSummary,
    ExecutionValidity,
    ForgottenExecutionPlan,
    binding_digest,
)
from yorunge.domain.state import canonical_uuid

if TYPE_CHECKING:
    from yorunge.domain.operations import AdmissionAuthority

PLAN_COLUMNS = "plan_id,digest,task,prepared_at,expires_at,status,payload"


def decode_plan(row: tuple[object, ...]) -> ExecutionPlan:
    try:
        identifier, digest, task, prepared, expires, status, payload = row
        if not isinstance(payload, str) or len(payload.encode("utf-8")) > 65536:
            raise ValueError("bounded plan required")
        plan = ExecutionPlan.model_validate_json(payload)
        if (identifier, digest, task, prepared, expires, status) != (
            plan.plan_id,
            plan.digest,
            plan.selection.task,
            plan.prepared_at,
            plan.expires_at,
            plan.status,
        ):
            raise ValueError("plan index mismatch")
        return plan
    except (ValueError, TypeError, RecursionError):
        raise YorungeError("state_invalid") from None


@dataclass(frozen=True)
class PlanValidation:
    plan_id: str
    digest: str
    store_id: str
    identity_epoch: str
    clock_generation: int
    prepared_at: str
    expires_at: str
    status: str
    bound_digest: str
    selection: tuple[str, str | None, str]
    authorities: tuple[AdmissionAuthority, ...] | None
    delivery_required: bool | None


def describe_plan(plan: ExecutionPlan) -> PlanValidation:
    from yorunge.adapters.operation_store import plan_authorities
    from yorunge.domain.operations import requires_delivery

    return PlanValidation(
        plan.plan_id,
        plan.digest,
        plan.store_id,
        plan.identity_epoch,
        plan.clock_generation,
        plan.prepared_at,
        plan.expires_at,
        plan.status,
        binding_digest(plan),
        (plan.selection.task, plan.selection.tool, plan.selection.execution),
        plan_authorities(plan) if plan.status == "prepared" else None,
        requires_delivery(plan) if plan.status == "prepared" else None,
    )


def plan_validation(row: tuple[object, ...]) -> PlanValidation:
    from yorunge.adapters.validation_memo import validated

    def build() -> PlanValidation:
        return describe_plan(decode_plan(row))

    return validated(PlanValidation, row, build)


def validate_plans(connection: sqlite3.Connection) -> None:
    value = metadata(connection)
    generation = connection.execute("SELECT clock_generation FROM cache_clock").fetchone()[0]
    count = 0
    for row in connection.execute(f"SELECT {PLAN_COLUMNS} FROM execution_plans"):
        plan = plan_validation(row)
        if plan.store_id != value.store_id or (
            plan.identity_epoch == value.identity_epoch and plan.clock_generation > generation
        ):
            raise YorungeError("state_invalid")
        count += 1
        if count > 1024:
            raise YorungeError("state_invalid")


def stamp(moment: ExecutionMoment) -> Stamp:
    return Stamp(
        moment.store_id, moment.identity_epoch, moment.generation, moment.now, moment.anomaly
    )


def encode_cursor(prepared: str, identifier: str) -> str:
    return base64.urlsafe_b64encode(canonical([prepared, identifier])).decode("ascii")


def decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        if not isinstance(cursor, str) or len(cursor) > 256:
            raise ValueError("bounded cursor required")
        raw = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
        if (
            not isinstance(raw, list)
            or len(raw) != 2
            or not all(isinstance(part, str) for part in raw)
        ):
            raise ValueError("cursor string pair required")
        prepared, identifier = raw
        instant(prepared)
        canonical_uuid(identifier)
        if encode_cursor(prepared, identifier) != cursor:
            raise ValueError("canonical cursor required")
        return prepared, identifier
    except (ValueError, TypeError, RecursionError):
        raise YorungeError("invalid_request") from None


class PlanRepository:
    def __init__(self, store: Store, cache: StateCache, budget: ExecutionBudget) -> None:
        self.store, self.cache, self.budget = store, cache, budget
        self.pinned: ExecutionPlan | None = None
        self.latest_approval: ExecutionApproval | None = None
        self.cache.checks = (self._guard_plan,)
        self.cache.additional_expiries = self._expiry_boundaries

    def _expiry_boundaries(self) -> tuple[datetime, ...]:
        dates: tuple[datetime, ...] = (
            (instant(self.pinned.expires_at),) if self.pinned is not None else ()
        )
        if self.latest_approval is not None:
            dates += (instant(self.latest_approval.expires_at),)
        return dates

    def _guard_plan(self) -> None:
        if self.pinned is not None:
            try:
                current = read_plan(self.store.connection, self.pinned.plan_id)
            except YorungeError as error:
                if error.code == "plan_not_found":
                    raise YorungeError("state_changed") from None
                raise
            if current != self.pinned:
                raise YorungeError("state_changed")
            self.latest_approval = read_approval(self.store.connection, current)

    def moment(self) -> ExecutionMoment:
        self.budget.check()
        current = self.cache.stamp()
        self.budget.check()
        return ExecutionMoment(
            current.store_id,
            current.identity_epoch,
            current.generation,
            current.now,
            current.anomaly,
        )

    def finish(
        self, expected: ExecutionMoment, *, valid_until: datetime | None = None
    ) -> ExecutionMoment:
        try:
            current, within_budget = self.cache._finish(
                stamp(expected), (valid_until,) if valid_until is not None else ()
            )
            self.budget.check()
            if not within_budget:
                raise YorungeError("execution_timeout")
            return ExecutionMoment(
                current.store_id,
                current.identity_epoch,
                current.generation,
                current.now,
                current.anomaly,
            )
        except OSError:
            raise YorungeError("state_write_failed") from None
        except sqlite3.Error as error:
            raise YorungeError(sqlite_error_code(error)) from None

    def read(self, plan_id: str) -> ExecutionPlan:
        self.pinned = read_plan(self.store.connection, plan_id)
        self.latest_approval = read_approval(self.store.connection, self.pinned)
        return self.pinned

    def approval(self) -> ExecutionApproval | None:
        return self.latest_approval

    def approve(
        self, plan: ExecutionPlan, validity: ExecutionValidity, expected: ExecutionMoment
    ) -> ExecutionApproval:
        if self.pinned != plan:
            raise YorungeError("state_changed")
        if not validity.valid or validity.valid_until is None:
            raise YorungeError("plan_not_valid")
        until = min(instant(plan.expires_at), instant(validity.valid_until))
        try:
            with self.cache.transaction(stamp(expected)) as gate:
                self.budget.check()
                gate.require_range(instant(plan.prepared_at), until)
                old = self.latest_approval
                now = timestamp(self.cache.now())
                if (
                    old is not None
                    and old.status == "approved"
                    and old.approved_at <= now < old.expires_at
                ):
                    gate.require_range(instant(old.approved_at), instant(old.expires_at))
                    record = old
                else:
                    if not instant(plan.prepared_at) <= instant(now) < until:
                        raise YorungeError("plan_not_valid")
                    record = ExecutionApproval(
                        approval_id=str(uuid4()),
                        plan_id=plan.plan_id,
                        plan_digest=plan.digest,
                        binding_digest=binding_digest(plan),
                        store_id=plan.store_id,
                        identity_epoch=plan.identity_epoch,
                        clock_generation=plan.clock_generation,
                        approved_at=now,
                        expires_at=timestamp(until),
                        status="approved",
                        revoked_at=None,
                    )
                    write_approval(self.store.connection, record)
                self.budget.check()
            return record
        except YorungeError as error:
            if error.code == "capability_expired":
                raise YorungeError("plan_not_valid") from None
            raise

    def save(self, plan: ExecutionPlan, expected: ExecutionMoment) -> None:
        try:
            with self.cache.transaction(stamp(expected)) as gate:
                self.budget.check()
                if plan.status == "prepared":
                    gate.require_range(instant(plan.prepared_at), instant(plan.expires_at))
                if (
                    self.store.connection.execute(
                        "SELECT count(*) FROM execution_plans"
                    ).fetchone()[0]
                    >= 1024
                ):
                    raise YorungeError("plan_capacity_exceeded")
                self.store.connection.execute(
                    "INSERT INTO execution_plans VALUES(?,?,?,?,?,?,?)",
                    (
                        plan.plan_id,
                        plan.digest,
                        plan.selection.task,
                        plan.prepared_at,
                        plan.expires_at,
                        plan.status,
                        canonical(plan.model_dump(mode="json")).decode("ascii"),
                    ),
                )
                self.budget.check()
            self.pinned = plan
        except YorungeError as error:
            if error.code == "capability_expired":
                raise YorungeError("plan_not_valid") from None
            raise


def read_plan(connection: sqlite3.Connection, plan_id: str) -> ExecutionPlan:
    try:
        canonical_uuid(plan_id)
    except (ValueError, TypeError, AttributeError):
        raise YorungeError("invalid_request") from None
    row = connection.execute(
        f"SELECT {PLAN_COLUMNS} FROM execution_plans WHERE plan_id=?", (plan_id,)
    ).fetchone()
    if row is None:
        raise YorungeError("plan_not_found")
    return decode_plan(row)


def list_plans(connection: sqlite3.Connection, limit: int, cursor: str | None) -> ExecutionPlans:
    if type(limit) is not int or not 1 <= limit <= 100:
        raise YorungeError("invalid_request")
    after = decode_cursor(cursor) if cursor is not None else ("", "")
    rows = connection.execute(
        "SELECT p.plan_id,p.digest,p.task,p.prepared_at,p.expires_at,p.status,"
        "coalesce(a.status,'none') FROM execution_plans p LEFT JOIN execution_approvals a "
        "ON p.plan_id=a.plan_id WHERE (p.prepared_at,p.plan_id)>(?,?) "
        "ORDER BY p.prepared_at,p.plan_id LIMIT ?",
        (*after, limit + 1),
    ).fetchall()
    plans = []
    try:
        for identifier, digest, task, prepared, expires, status, approval_status in rows[:limit]:
            canonical_uuid(identifier)
            instant(prepared), instant(expires)
            plans.append(
                ExecutionSummary(
                    plan_id=identifier,
                    digest=digest,
                    task=task,
                    prepared_at=prepared,
                    expires_at=expires,
                    status=status,
                    approval_status=approval_status,
                )
            )
    except (ValueError, TypeError):
        raise YorungeError("state_invalid") from None
    next_cursor = (
        encode_cursor(plans[-1].prepared_at, plans[-1].plan_id) if len(rows) > limit else None
    )
    return ExecutionPlans(plans=tuple(plans), next_cursor=next_cursor)


APPROVAL_COLUMNS = "plan_id,approval_id,status,approved_at,expires_at,revoked_at,payload"


def decode_approval(
    row: tuple[object, ...], plan: ExecutionPlan | PlanValidation
) -> ExecutionApproval:
    try:
        identifier, approval_id, status, approved, expires, revoked, payload = row
        if not isinstance(payload, str) or len(payload.encode("utf-8")) > 4096:
            raise ValueError("bounded approval required")
        record = ExecutionApproval.model_validate_json(payload)
        if (
            (identifier, approval_id, status, approved, expires, revoked)
            != (
                record.plan_id,
                record.approval_id,
                record.status,
                record.approved_at,
                record.expires_at,
                record.revoked_at,
            )
            or (
                record.plan_id,
                record.plan_digest,
                record.binding_digest,
                record.store_id,
                record.identity_epoch,
                record.clock_generation,
            )
            != (
                plan.plan_id,
                plan.digest,
                plan.bound_digest if isinstance(plan, PlanValidation) else binding_digest(plan),
                plan.store_id,
                plan.identity_epoch,
                plan.clock_generation,
            )
            or not plan.prepared_at <= record.approved_at < record.expires_at <= plan.expires_at
            or plan.status != "prepared"
        ):
            raise ValueError("approval relationship mismatch")
        return record
    except (ValueError, TypeError, RecursionError):
        raise YorungeError("state_invalid") from None


def read_approval(connection: sqlite3.Connection, plan: ExecutionPlan) -> ExecutionApproval | None:
    row = connection.execute(
        f"SELECT {APPROVAL_COLUMNS} FROM execution_approvals WHERE plan_id=?", (plan.plan_id,)
    ).fetchone()
    return decode_approval(row, plan) if row is not None else None


def validate_approvals(connection: sqlite3.Connection) -> None:
    for row in connection.execute(f"SELECT {APPROVAL_COLUMNS} FROM execution_approvals"):
        saved = connection.execute(
            f"SELECT {PLAN_COLUMNS} FROM execution_plans WHERE plan_id=?", (row[0],)
        ).fetchone()
        if saved is None:
            raise YorungeError("state_invalid") from None
        plan = plan_validation(saved)
        decode_approval(row, plan)


def write_approval(connection: sqlite3.Connection, record: ExecutionApproval) -> None:
    payload = canonical(record.model_dump(mode="json")).decode("ascii")
    if len(payload) > 4096:
        raise YorungeError("plan_not_valid")
    connection.execute(
        "INSERT OR REPLACE INTO execution_approvals VALUES(?,?,?,?,?,?,?)",
        (
            record.plan_id,
            record.approval_id,
            record.status,
            record.approved_at,
            record.expires_at,
            record.revoked_at,
            payload,
        ),
    )


def forget_plan(store: Store, plan_id: str, confirmation: str | None) -> ForgottenExecutionPlan:
    from yorunge.application.execution import require_confirmation

    plan = read_plan(store.connection, plan_id)
    require_confirmation(plan, confirmation)
    store.connection.execute("BEGIN IMMEDIATE")
    try:
        current = read_plan(store.connection, plan_id)
        if current != plan:
            raise YorungeError("state_changed")
        approval = read_approval(store.connection, current)
        if store.connection.execute(
            "SELECT 1 FROM sqlite_schema WHERE type='table' AND name='operations'"
        ).fetchone():
            linked = store.connection.execute(
                "SELECT operation_id FROM operations WHERE plan_id=?", (plan_id,)
            ).fetchone()
            if linked is not None:
                from yorunge.adapters.operation_store import read_job

                try:
                    read_job(store.connection, linked[0])
                except YorungeError:
                    raise YorungeError("state_invalid") from None
                raise YorungeError("plan_in_use")
        store.deadline.remaining()
        store.connection.execute("DELETE FROM execution_plans WHERE plan_id=?", (plan_id,))
        store.deadline.remaining()
        store.connection.execute("COMMIT")
        return ForgottenExecutionPlan(
            plan_id=plan_id, digest=plan.digest, approval_removed=approval is not None
        )
    finally:
        if store.connection.in_transaction:
            store.connection.execute("ROLLBACK")


def revoke_approval(store: Store, plan_id: str) -> ExecutionApprovalState:
    from yorunge.application.execution import approval_state
    from yorunge.domain.errors import ApprovalNotEffective

    plan = read_plan(store.connection, plan_id)
    cache = StateCache(store)
    repo = PlanRepository(store, cache, ExecutionBudget(cache.clock, cache.clock.monotonic()))
    repo.read(plan_id)
    expected = repo.moment()
    store.connection.execute("BEGIN IMMEDIATE")
    try:
        repo._guard_plan()
        record = repo.latest_approval
        if record is not None and record.status != "revoked":
            record = ExecutionApproval.model_validate_json(
                canonical(
                    record.model_copy(
                        update={"status": "revoked", "revoked_at": timestamp(cache.now())}
                    ).model_dump(mode="json")
                )
            )
            write_approval(store.connection, record)
        store.deadline.remaining()
        store.connection.execute("COMMIT")
    finally:
        if store.connection.in_transaction:
            store.connection.execute("ROLLBACK")
    try:
        final = repo.finish(expected)
    except YorungeError as error:
        if record is None:
            raise
        raise ApprovalNotEffective(plan.plan_id, record.approval_id, error.code) from None
    return approval_state(plan, repo.latest_approval, final, valid=False)
