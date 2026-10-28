"""Strict operation persistence and bounded snapshots; no external effects."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal, TypeVar

from yorunge.adapters.execution_store import read_plan
from yorunge.adapters.state import metadata
from yorunge.domain.capabilities import WireModel, canonical
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.execution import ExecutionPlan, binding_digest
from yorunge.domain.operations import (
    MAX_ATTEMPT_BYTES,
    MAX_ATTEMPTS,
    MAX_EVENT_BYTES,
    MAX_EVENTS,
    MAX_OPERATION_BYTES,
    MAX_OPERATIONS,
    MAX_OUTCOME_BYTES,
    TERMINAL,
    AdmissionAuthority,
    AttemptView,
    JobView,
    OperationEvent,
    OperationOutcome,
    OperationRecord,
    operation_status,
    validate_reason,
)
from yorunge.domain.state import canonical_uuid

OPERATION_COLUMNS = (
    "operation_id,plan_id,plan_digest,task,tool,execution,created_at,updated_at,status,"
    "revision,lease_expires_at,dispatch_attempt_id,payload"
)
ATTEMPT_COLUMNS = "attempt_id,operation_id,number,status,payload"
EVENT_COLUMNS = "operation_id,sequence,attempt_id,payload"
T = TypeVar("T", bound=WireModel)


def plan_authorities(plan: ExecutionPlan) -> tuple[AdmissionAuthority, ...]:
    values: dict[bytes, AdmissionAuthority] = {}
    for capability in plan.assessment.capabilities:
        scope = capability.key.scope
        item = AdmissionAuthority(
            **{name: getattr(scope, name) for name in AdmissionAuthority.model_fields}
        )
        values[canonical(item.model_dump(mode="json"))] = item
    return tuple(values[key] for key in sorted(values))


def decode(model: type[T], payload: object, maximum: int) -> T:
    try:
        if not isinstance(payload, str) or len(payload.encode("utf-8")) > maximum:
            raise ValueError("bounded payload required")
        return model.model_validate_json(payload)
    except (ValueError, TypeError, RecursionError):
        raise YorungeError("state_invalid") from None


def operation_row(record: OperationRecord) -> tuple[object, ...]:
    s = record.summary
    return (
        s.operation_id,
        s.plan_id,
        s.plan_digest,
        s.task,
        s.tool,
        s.execution,
        s.created_at,
        s.updated_at,
        s.status,
        s.revision,
        record.lease.expires_at if record.lease else None,
        record.dispatch_attempt_id,
        canonical(record.model_dump(mode="json")).decode("ascii"),
    )


def decode_operation(row: tuple[object, ...]) -> OperationRecord:
    if len(row) != 13:
        raise YorungeError("state_invalid")
    record = decode(OperationRecord, row[-1], MAX_OPERATION_BYTES)
    if row[:-1] != operation_row(record)[:-1]:
        raise YorungeError("state_invalid")
    return record


def read_operation(connection: sqlite3.Connection, operation_id: str) -> OperationRecord:
    try:
        canonical_uuid(operation_id)
    except (ValueError, TypeError, AttributeError):
        raise YorungeError("invalid_request") from None
    row = connection.execute(
        f"SELECT {OPERATION_COLUMNS} FROM operations WHERE operation_id=?", (operation_id,)
    ).fetchone()
    if row is None:
        raise OperationError("operation_not_found", operation_id)
    return decode_operation(row)


def read_attempts(connection: sqlite3.Connection, operation_id: str) -> tuple[AttemptView, ...]:
    result = []
    for identifier, owner, number, status, payload in connection.execute(
        f"SELECT {ATTEMPT_COLUMNS} FROM operation_attempts WHERE operation_id=? "
        "ORDER BY number LIMIT ?",
        (operation_id, MAX_ATTEMPTS + 1),
    ):
        item = decode(AttemptView, payload, MAX_ATTEMPT_BYTES)
        if (identifier, owner, number, status) != (
            item.attempt_id,
            operation_id,
            item.number,
            item.status,
        ):
            raise YorungeError("state_invalid")
        result.append(item)
    if not 1 <= len(result) <= MAX_ATTEMPTS:
        raise YorungeError("state_invalid")
    return tuple(result)


def read_outcome(connection: sqlite3.Connection, operation_id: str) -> OperationOutcome | None:
    row = connection.execute(
        "SELECT payload FROM operation_outcomes WHERE operation_id=?", (operation_id,)
    ).fetchone()
    return None if row is None else decode(OperationOutcome, row[0], MAX_OUTCOME_BYTES)


def validate_events(
    connection: sqlite3.Connection, record: OperationRecord, attempts: tuple[AttemptView, ...]
) -> None:
    previous: OperationEvent | None = None
    identifiers = {attempt.attempt_id for attempt in attempts}
    count = 0
    for owner, sequence, attempt_id, payload in connection.execute(
        f"SELECT {EVENT_COLUMNS} FROM operation_events WHERE operation_id=? "
        "ORDER BY sequence LIMIT ?",
        (record.summary.operation_id, MAX_EVENTS + 1),
    ):
        item = decode(OperationEvent, payload, MAX_EVENT_BYTES)
        count += 1
        if (
            (owner, sequence, attempt_id) != (record.summary.operation_id, count, item.attempt_id)
            or sequence != item.sequence
            or attempt_id not in identifiers
        ):
            raise YorungeError("state_invalid")
        try:
            local: Literal["failed", "cancelled"] | None = None
            if item.execution_status == "not_started" and item.status == "failed":
                local = "failed"
            elif item.execution_status == "not_started" and item.status == "cancelled":
                local = "cancelled"
            if (
                operation_status(
                    item.execution_status,
                    item.delivery_status,
                    delivery_required=record.admission.delivery_required,
                    local_terminal=local,
                )
                != item.status
            ):
                raise ValueError("event status mismatch")
            validate_reason(
                "claimed" if item.status == "admitted" else item.status, item.reason_code
            )
            if previous is not None:
                if previous.status in TERMINAL:
                    raise ValueError("terminal history is immutable")
                same_clock = (previous.identity_epoch, previous.clock_generation) == (
                    item.identity_epoch,
                    item.clock_generation,
                )
                if same_clock and item.observed_at < previous.observed_at:
                    raise ValueError("same-clock history regressed")
                if item.observed_at < previous.observed_at and not record.summary.clock_anomaly:
                    raise ValueError("clock regression must be visible")
                if item.revision <= previous.revision or item.fence < previous.fence:
                    raise ValueError("event counters must increase")
            elif item.status != "admitted" or item.observed_at != record.summary.created_at:
                raise ValueError("admission history required")
            if item.revision > record.summary.revision or item.fence > record.fence:
                raise ValueError("event counter exceeds current state")
        except (ValueError, TypeError):
            raise YorungeError("state_invalid") from None
        previous = item
    if count != record.event_count or previous is None:
        raise YorungeError("state_invalid")
    if record.recovery_reason is None and (
        previous.status,
        previous.execution_status,
        previous.delivery_status,
        previous.attempt_id,
        previous.reason_code,
    ) != (
        record.summary.status,
        record.summary.execution_status,
        record.summary.delivery_status,
        attempts[-1].attempt_id,
        attempts[-1].reason_code,
    ):
        raise YorungeError("state_invalid")
    if record.summary.status in TERMINAL and previous.observed_at != record.summary.updated_at:
        raise YorungeError("state_invalid")


@contextmanager
def read_snapshot(connection: sqlite3.Connection) -> Iterator[None]:
    own = not connection.in_transaction
    if own:
        connection.execute("BEGIN")
    try:
        yield
    finally:
        if own and connection.in_transaction:
            connection.execute("ROLLBACK")


def read_job(
    connection: sqlite3.Connection, operation_id: str, *, record: OperationRecord | None = None
) -> JobView:
    with read_snapshot(connection):
        record = record or read_operation(connection, operation_id)
        a, s = record.admission, record.summary
        value = metadata(connection)
        try:
            plan = read_plan(connection, s.plan_id)
            attempts = read_attempts(connection, operation_id)
            outcome = read_outcome(connection, operation_id)
            if plan.status != "prepared":
                raise ValueError("operation requires a prepared plan")
            if (
                a.store_id != value.store_id
                or a.approval.binding_digest != binding_digest(plan)
                or a.authorities != plan_authorities(plan)
            ):
                raise ValueError("operation authority mismatch")
            if (a.admission_identity_epoch, a.admission_clock_generation) != (
                plan.identity_epoch,
                plan.clock_generation,
            ):
                raise ValueError("operation plan identity mismatch")
            if (
                record.dispatch_attempt_id is not None
                and record.dispatch_attempt_id != attempts[-1].attempt_id
            ):
                raise ValueError("dispatch must bind final attempt")
            if (
                record.recovery_reason is not None
                and attempts[-1].reason_code != record.recovery_reason
            ):
                raise ValueError("recovery reason projection mismatch")
            if s.updated_at < s.created_at and not s.clock_anomaly:
                raise ValueError("clock regression must be visible")
            if s.updated_at < s.created_at and (
                record.observed_identity_epoch,
                record.observed_clock_generation,
            ) == (a.admission_identity_epoch, a.admission_clock_generation):
                raise ValueError("same-clock snapshot regressed")
            if not plan.prepared_at <= s.created_at < a.approval.expires_at <= plan.expires_at:
                raise ValueError("admission lifetime mismatch")
            job = JobView(operation=s, plan=plan, attempts=attempts, outcome=outcome)
            validate_events(connection, record, attempts)
            return job
        except YorungeError as error:
            if error.code == "plan_not_found":
                raise YorungeError("state_invalid") from None
            raise
        except (ValueError, TypeError, RecursionError):
            raise YorungeError("state_invalid") from None


def validate_operations(connection: sqlite3.Connection) -> None:
    with read_snapshot(connection):
        count = 0
        for row in connection.execute(f"SELECT {OPERATION_COLUMNS} FROM operations"):
            count += 1
            if count > MAX_OPERATIONS:
                raise YorungeError("state_invalid")
            record = decode_operation(row)
            read_job(connection, record.summary.operation_id, record=record)


def insert_record(
    connection: sqlite3.Connection,
    record: OperationRecord,
    attempt: AttemptView,
    event: OperationEvent,
) -> None:
    """Caller owns transaction and current validation; never a public import port."""
    if not connection.in_transaction:
        raise YorungeError("state_invalid")
    record = decode(
        OperationRecord,
        canonical(record.model_dump(mode="json")).decode("ascii"),
        MAX_OPERATION_BYTES,
    )
    if connection.execute("SELECT count(*) FROM operations").fetchone()[0] >= MAX_OPERATIONS:
        raise OperationError("operation_capacity_exceeded", capacity_kind="store")
    connection.execute(
        f"INSERT INTO operations({OPERATION_COLUMNS}) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        operation_row(record),
    )
    write_attempt(connection, record.summary.operation_id, attempt)
    append_event(connection, record.summary.operation_id, event)
    read_job(connection, record.summary.operation_id)


def write_record(
    connection: sqlite3.Connection, record: OperationRecord, *, expected_revision: int
) -> None:
    if not connection.in_transaction:
        raise YorungeError("state_invalid")
    record = decode(
        OperationRecord,
        canonical(record.model_dump(mode="json")).decode("ascii"),
        MAX_OPERATION_BYTES,
    )
    current = read_operation(connection, record.summary.operation_id)
    old, new = current.summary, record.summary
    if old.revision != expected_revision:
        raise OperationError("operation_lease_lost", old.operation_id)
    if old.status in TERMINAL:
        if current == record:
            return
        raise OperationError("operation_conflict", old.operation_id)
    if (
        current.admission != record.admission
        or (
            old.operation_id,
            old.plan_id,
            old.plan_digest,
            old.task,
            old.tool,
            old.execution,
            old.created_at,
        )
        != (
            new.operation_id,
            new.plan_id,
            new.plan_digest,
            new.task,
            new.tool,
            new.execution,
            new.created_at,
        )
        or (
            current.dispatch_attempt_id is not None
            and current.dispatch_attempt_id != record.dispatch_attempt_id
        )
    ):
        raise OperationError("operation_conflict", old.operation_id)
    if new.revision == expected_revision:
        if (
            current.lease is None
            or record.lease is None
            or current.lease.token() != record.lease.token()
            or current.model_copy(update={"lease": record.lease}) != record
        ):
            raise OperationError("operation_conflict", old.operation_id)
    elif new.revision != expected_revision + 1:
        raise OperationError("operation_conflict", old.operation_id)
    if (
        record.event_count < current.event_count
        or record.event_count > current.event_count + 1
        or (current.dispatch_attempt_id is not None and new.attempt_count != old.attempt_count)
    ):
        raise OperationError("operation_conflict", old.operation_id)
    if (
        not old.attempt_count <= new.attempt_count <= old.attempt_count + 1
        or not current.fence <= record.fence <= current.fence + 1
    ):
        raise OperationError("operation_conflict", old.operation_id)
    row = operation_row(record)
    result = connection.execute(
        "UPDATE operations SET plan_id=?,plan_digest=?,task=?,tool=?,execution=?,created_at=?,"
        "updated_at=?,status=?,revision=?,lease_expires_at=?,dispatch_attempt_id=?,payload=? "
        "WHERE operation_id=? AND revision=?",
        (*row[1:], row[0], expected_revision),
    )
    if result.rowcount != 1:
        raise OperationError("operation_lease_lost", record.summary.operation_id)


def write_attempt(connection: sqlite3.Connection, operation_id: str, attempt: AttemptView) -> None:
    if not connection.in_transaction:
        raise YorungeError("state_invalid")
    item = decode(
        AttemptView, canonical(attempt.model_dump(mode="json")).decode("ascii"), MAX_ATTEMPT_BYTES
    )
    result = connection.execute(
        "INSERT INTO operation_attempts VALUES(?,?,?,?,?) ON CONFLICT(attempt_id) DO UPDATE "
        "SET status=excluded.status,payload=excluded.payload "
        "WHERE operation_attempts.operation_id=excluded.operation_id "
        "AND operation_attempts.number=excluded.number",
        (
            item.attempt_id,
            operation_id,
            item.number,
            item.status,
            canonical(item.model_dump(mode="json")).decode("ascii"),
        ),
    )
    if result.rowcount != 1:
        raise OperationError("operation_conflict", operation_id)


def append_event(connection: sqlite3.Connection, operation_id: str, event: OperationEvent) -> None:
    if not connection.in_transaction:
        raise YorungeError("state_invalid")
    item = decode(
        OperationEvent, canonical(event.model_dump(mode="json")).decode("ascii"), MAX_EVENT_BYTES
    )
    connection.execute(
        "INSERT INTO operation_events VALUES(?,?,?,?)",
        (
            operation_id,
            item.sequence,
            item.attempt_id,
            canonical(item.model_dump(mode="json")).decode("ascii"),
        ),
    )


def write_outcome(
    connection: sqlite3.Connection, operation_id: str, outcome: OperationOutcome
) -> None:
    if not connection.in_transaction:
        raise YorungeError("state_invalid")
    item = decode(
        OperationOutcome,
        canonical(outcome.model_dump(mode="json")).decode("ascii"),
        MAX_OUTCOME_BYTES,
    )
    connection.execute(
        "INSERT INTO operation_outcomes VALUES(?,?)",
        (operation_id, canonical(item.model_dump(mode="json")).decode("ascii")),
    )
