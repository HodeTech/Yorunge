"""Strict immutable plan persistence, bounded listing and final state/time gates."""

from __future__ import annotations

import base64
import json
import sqlite3
from datetime import datetime

from yorunge.adapters.capability_cache import Stamp, StateCache
from yorunge.adapters.state import Store, metadata
from yorunge.application.execution import ExecutionBudget
from yorunge.domain.capabilities import canonical, instant
from yorunge.domain.errors import YorungeError
from yorunge.domain.execution import (
    ExecutionMoment,
    ExecutionPlan,
    ExecutionPlans,
    ExecutionSummary,
)
from yorunge.domain.state import canonical_uuid

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


def validate_plans(connection: sqlite3.Connection) -> None:
    value = metadata(connection)
    generation = connection.execute("SELECT clock_generation FROM cache_clock").fetchone()[0]
    count = 0
    for row in connection.execute(f"SELECT {PLAN_COLUMNS} FROM execution_plans"):
        plan = decode_plan(row)
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
        if not isinstance(raw, list) or len(raw) != 2:
            raise ValueError("cursor pair required")
        prepared, identifier = raw
        instant(prepared)
        canonical_uuid(identifier)
        if encode_cursor(prepared, identifier) != cursor:
            raise ValueError("canonical cursor required")
        return prepared, identifier
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise YorungeError("invalid_request") from None


class PlanRepository:
    def __init__(self, store: Store, cache: StateCache, budget: ExecutionBudget) -> None:
        self.store, self.cache, self.budget = store, cache, budget

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

    def read(self, plan_id: str) -> ExecutionPlan:
        return read_plan(self.store.connection, plan_id)

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
        "SELECT plan_id,digest,task,prepared_at,expires_at,status FROM execution_plans "
        "WHERE (prepared_at,plan_id)>(?,?) ORDER BY prepared_at,plan_id LIMIT ?",
        (*after, limit + 1),
    ).fetchall()
    plans = []
    try:
        for identifier, digest, task, prepared, expires, status in rows[:limit]:
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
                )
            )
    except (ValueError, TypeError):
        raise YorungeError("state_invalid") from None
    next_cursor = (
        encode_cursor(plans[-1].prepared_at, plans[-1].plan_id) if len(rows) > limit else None
    )
    return ExecutionPlans(plans=tuple(plans), next_cursor=next_cursor)
