"""Strict operation persistence and bounded snapshots; no external effects."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Literal, TypeVar

from yorunge.adapters.execution_store import (
    PLAN_COLUMNS,
    PlanValidation,
    describe_plan,
    plan_validation,
    read_plan,
)
from yorunge.adapters.state import metadata
from yorunge.domain.capabilities import JsonWireModel, canonical
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.execution import ExecutionPlan
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
    OperationStatus,
    operation_status,
    validate_job_relationships,
    validate_progress_reason,
)
from yorunge.domain.state import canonical_uuid

OPERATION_COLUMNS = (
    "operation_id,plan_id,plan_digest,task,tool,execution,created_at,updated_at,status,"
    "revision,lease_expires_at,dispatch_attempt_id,payload"
)
ATTEMPT_COLUMNS = "attempt_id,operation_id,number,status,payload"
EVENT_COLUMNS = "operation_id,sequence,attempt_id,payload"
T = TypeVar("T", bound=JsonWireModel)


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
    except (ValueError, TypeError, RecursionError, YorungeError):
        raise YorungeError("state_invalid") from None


def _operation_projection(record: OperationRecord) -> tuple[object, ...]:
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
    )


def operation_row(record: OperationRecord) -> tuple[object, ...]:
    return (
        *_operation_projection(record),
        canonical(record.model_dump(mode="json")).decode("ascii"),
    )


def decode_operation(row: tuple[object, ...]) -> OperationRecord:
    if len(row) != 13:
        raise YorungeError("state_invalid")
    record = decode(OperationRecord, row[-1], MAX_OPERATION_BYTES)
    if row[:-1] != _operation_projection(record):
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


@dataclass(frozen=True)
class AttemptSet:
    items: tuple[AttemptView, ...]


def read_attempts(connection: sqlite3.Connection, operation_id: str) -> tuple[AttemptView, ...]:
    rows = connection.execute(
        f"SELECT {ATTEMPT_COLUMNS} FROM operation_attempts WHERE operation_id=? "
        "ORDER BY number LIMIT ?",
        (operation_id, MAX_ATTEMPTS + 1),
    ).fetchall()
    return decode_attempts(operation_id, rows)


def decode_attempts(operation_id: str, rows: list[tuple[object, ...]]) -> tuple[AttemptView, ...]:
    from yorunge.adapters.validation_memo import validated

    def build() -> AttemptSet:
        result = []
        for identifier, owner, number, status, payload in rows:
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
        return AttemptSet(tuple(result))

    identity = (operation_id, *(part for row in rows for part in row))
    return validated(AttemptSet, identity, build).items


def read_outcome(connection: sqlite3.Connection, operation_id: str) -> OperationOutcome | None:
    row = connection.execute(
        "SELECT payload FROM operation_outcomes WHERE operation_id=?", (operation_id,)
    ).fetchone()
    return None if row is None else decode(OperationOutcome, row[0], MAX_OUTCOME_BYTES)


EVENT_TRANSITIONS: dict[OperationStatus, frozenset[OperationStatus]] = {
    "admitted": frozenset({"submitted", "failed", "cancelled"}),
    "submitted": frozenset({"submitted", "running", "unknown", "succeeded", "failed", "cancelled"}),
    "running": frozenset({"running", "unknown", "succeeded", "failed", "cancelled"}),
    "unknown": frozenset({"unknown", "submitted", "running", "succeeded", "failed", "cancelled"}),
    "succeeded": frozenset(),
    "failed": frozenset(),
    "cancelled": frozenset(),
}


def _dispatch_authority(record: OperationRecord, item: OperationEvent) -> None:
    if item.status != "submitted":
        raise ValueError("submitted intent must precede external progress")
    if (
        (item.identity_epoch, item.clock_generation)
        != (
            record.admission.admission_identity_epoch,
            record.admission.admission_clock_generation,
        )
        or not record.admission.approval.approved_at
        <= item.observed_at
        < record.admission.approval.expires_at
    ):
        raise ValueError("dispatch must retain admission authority")


def _validate_admission_event(
    record: OperationRecord, item: OperationEvent, numbers: dict[str, int]
) -> None:
    if (item.status, item.attempt_id, item.observed_at, item.revision, item.fence) != (
        "admitted",
        min(numbers, key=numbers.__getitem__),
        record.summary.created_at,
        1,
        1,
    ):
        raise ValueError("admission history required")
    if (item.identity_epoch, item.clock_generation) != (
        record.admission.admission_identity_epoch,
        record.admission.admission_clock_generation,
    ):
        raise ValueError("admission clock mismatch")


def _validate_candidate_transition(
    item: OperationEvent, previous: OperationEvent, numbers: dict[str, int]
) -> None:
    if numbers[item.attempt_id] < numbers[previous.attempt_id]:
        raise ValueError("candidate sequence cannot regress")
    if item.attempt_id != previous.attempt_id and item.fence <= previous.fence:
        raise ValueError("new candidate must have a new owner")


def _event_progress(
    record: OperationRecord,
    item: OperationEvent,
    previous: OperationEvent | None,
    numbers: dict[str, int],
    armed: bool,
) -> bool:
    sending = item.execution_status != "not_started"
    if sending:
        if not armed:
            _dispatch_authority(record, item)
    elif armed:
        raise ValueError("dispatched history cannot return to admission")
    if previous is None:
        _validate_admission_event(record, item, numbers)
        return sending
    recovered = (
        previous.status == "running"
        and item.status == "submitted"
        and (item.fence > previous.fence or item.revision > previous.revision + 1)
    )
    if item.status not in EVENT_TRANSITIONS[previous.status] and not recovered:
        raise ValueError("invalid lifecycle transition")
    if previous.status == "admitted":
        _validate_candidate_transition(item, previous, numbers)
    elif item.attempt_id != previous.attempt_id:
        raise ValueError("attempt may change only before dispatch")
    return armed or sending


def _event_observation(
    record: OperationRecord, item: OperationEvent, previous: OperationEvent | None
) -> bool:
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
        raise ValueError("event reducer mismatch")
    validate_progress_reason(
        item.status,
        item.reason_code,
        item.execution_status,
        item.delivery_status,
        dispatched=item.execution_status != "not_started",
    )
    if previous is None:
        return False
    if previous.execution_status == "succeeded" and item.execution_status != "succeeded":
        raise ValueError("confirmed execution success cannot be lost")
    if (
        previous.identity_epoch == item.identity_epoch
        and item.clock_generation < previous.clock_generation
    ):
        raise ValueError("clock generation cannot regress within an identity epoch")
    same_clock = (previous.identity_epoch, previous.clock_generation) == (
        item.identity_epoch,
        item.clock_generation,
    )
    regressed = item.observed_at < previous.observed_at
    if regressed and same_clock:
        raise ValueError("invalid clock regression")
    if item.revision <= previous.revision or item.fence < previous.fence:
        raise ValueError("event counters must increase")
    return regressed


def _validate_history_recovery(record: OperationRecord, previous: OperationEvent) -> None:
    s = record.summary
    if previous.execution_status == "succeeded" and s.execution_status != "succeeded":
        raise ValueError("recovery must preserve confirmed execution")
    if record.recovery_reason is not None:
        expected_execution = "succeeded" if previous.execution_status == "succeeded" else "unknown"
        allowed_delivery = {previous.delivery_status}
        if record.admission.delivery_required:
            allowed_delivery.add("unknown")
        if s.execution_status != expected_execution or s.delivery_status not in allowed_delivery:
            raise ValueError("recovery cannot invent execution or delivery progress")
    if previous.status in TERMINAL and (
        record.recovery_reason is not None or s.status != previous.status
    ):
        raise ValueError("terminal history cannot be reopened")


def _validate_history_current(
    record: OperationRecord, previous: OperationEvent, attempts: tuple[AttemptView, ...]
) -> None:
    s = record.summary
    predispatch_control = (
        previous.status == s.status == "admitted" and record.dispatch_attempt_id is None
    )
    if (
        record.recovery_reason is None
        and not predispatch_control
        and (
            record.observed_identity_epoch,
            record.observed_clock_generation,
        )
        != (previous.identity_epoch, previous.clock_generation)
    ):
        raise ValueError("normal projection clock must match its event")
    expected_attempt = previous.attempt_id if predispatch_control else attempts[-1].attempt_id
    if predispatch_control and (record.fence < s.attempt_count or s.revision < record.fence):
        raise ValueError("candidate ownership counters mismatch")
    if record.recovery_reason is None and (
        previous.status,
        previous.execution_status,
        previous.delivery_status,
        previous.attempt_id,
        previous.reason_code,
    ) != (
        s.status,
        s.execution_status,
        s.delivery_status,
        expected_attempt,
        attempts[-1].reason_code,
    ):
        raise ValueError("latest history projection mismatch")


def _validate_history_observation(record: OperationRecord, previous: OperationEvent) -> None:
    s = record.summary
    if s.status in TERMINAL and (
        previous.observed_at,
        previous.revision,
        previous.fence,
    ) != (s.updated_at, s.revision, record.fence):
        raise ValueError("terminal history is immutable")
    if s.updated_at < previous.observed_at:
        if not s.clock_anomaly or (
            record.observed_identity_epoch,
            record.observed_clock_generation,
        ) == (previous.identity_epoch, previous.clock_generation):
            raise ValueError("control clock regression must be explicit")


def _history_end(
    record: OperationRecord, previous: OperationEvent, attempts: tuple[AttemptView, ...]
) -> None:
    _validate_history_recovery(record, previous)
    _validate_history_current(record, previous, attempts)
    _validate_history_observation(record, previous)


@dataclass(frozen=True)
class HistoryProof:
    last: OperationEvent
    count: int
    armed: bool
    clock_regressed: bool


def _event_candidate(
    record: OperationRecord, item: OperationEvent, number: int, created_at: str
) -> None:
    if item.revision < item.sequence:
        raise ValueError("normal event revision cannot precede its sequence")
    if item.fence < number:
        raise ValueError("event fence predates its candidate claims")
    if (item.identity_epoch, item.clock_generation) == (
        record.admission.admission_identity_epoch,
        record.admission.admission_clock_generation,
    ) and item.observed_at < created_at:
        raise ValueError("event predates its candidate")
    if item.execution_status != "not_started" and item.attempt_id != record.dispatch_attempt_id:
        raise ValueError("dispatch history cannot be rebound or cleared")


def _history_proof(
    record: OperationRecord, attempts: tuple[AttemptView, ...], rows: list[tuple[object, ...]]
) -> HistoryProof:
    from yorunge.adapters.validation_memo import validated

    numbers = {attempt.attempt_id: attempt.number for attempt in attempts}
    created = {attempt.attempt_id: attempt.created_at for attempt in attempts}
    identity: tuple[object, ...] = (
        canonical(record.admission.model_dump(mode="json")),
        record.summary.created_at,
        record.dispatch_attempt_id,
        *(
            part
            for attempt in attempts
            for part in (attempt.attempt_id, attempt.number, attempt.created_at)
        ),
        *(part for row in rows for part in row),
    )

    def build() -> HistoryProof:
        previous: OperationEvent | None = None
        count, armed, regressed = 0, False, False
        for owner, sequence, attempt_id, payload in rows:
            item = decode(OperationEvent, payload, MAX_EVENT_BYTES)
            count += 1
            if (
                (owner, sequence, attempt_id)
                != (record.summary.operation_id, count, item.attempt_id)
                or sequence != item.sequence
                or attempt_id not in numbers
            ):
                raise YorungeError("state_invalid")
            _event_candidate(record, item, numbers[item.attempt_id], created[item.attempt_id])
            armed = _event_progress(record, item, previous, numbers, armed)
            regressed = _event_observation(record, item, previous) or regressed
            previous = item
        if previous is None or count > MAX_EVENTS:
            raise ValueError("bounded non-empty history required")
        return HistoryProof(previous, count, armed, regressed)

    return validated(HistoryProof, identity, build)


def validate_events(
    connection: sqlite3.Connection, record: OperationRecord, attempts: tuple[AttemptView, ...]
) -> None:
    # At most 257 small rows are resident. Every read fingerprints all exact rows;
    # only pure immutable history facts are reused inside one validation session.
    rows = connection.execute(
        f"SELECT {EVENT_COLUMNS} FROM operation_events WHERE operation_id=? "
        "ORDER BY sequence LIMIT ?",
        (record.summary.operation_id, MAX_EVENTS + 1),
    ).fetchall()
    try:
        proof = _history_proof(record, attempts, rows)
        if (
            proof.count != record.event_count
            or proof.armed != (record.dispatch_attempt_id is not None)
            or proof.last.fence > record.fence
            or proof.last.revision > record.summary.revision
            or (proof.clock_regressed and not record.summary.clock_anomaly)
        ):
            raise ValueError("dispatch history/counters/clock mismatch")
        _history_end(record, proof.last, attempts)
    except (ValueError, TypeError):
        raise YorungeError("state_invalid") from None


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


@dataclass(frozen=True)
class OperationClock:
    store_id: str
    identity_epoch: str
    generation: int


def operation_clock(connection: sqlite3.Connection) -> OperationClock:
    value = metadata(connection)
    clock = connection.execute(
        "SELECT identity_epoch,clock_generation FROM cache_clock WHERE singleton=1"
    ).fetchone()
    if (
        clock is None
        or clock[0] != value.identity_epoch
        or type(clock[1]) is not int
        or not 1 <= clock[1] <= 2**63 - 1
    ):
        raise ValueError("invalid operation clock")
    return OperationClock(value.store_id, value.identity_epoch, clock[1])


def validate_operation_clock(
    record: OperationRecord, plan: PlanValidation, clock: OperationClock
) -> None:
    if record.admission.store_id != clock.store_id or plan.store_id != clock.store_id:
        raise ValueError("operation store mismatch")
    scopes = [
        (plan.identity_epoch, plan.clock_generation),
        (record.observed_identity_epoch, record.observed_clock_generation),
    ]
    if record.lease is not None:
        scopes.append(
            (record.lease.ownership_identity_epoch, record.lease.ownership_clock_generation)
        )
    if any(
        epoch == clock.identity_epoch and generation > clock.generation
        for epoch, generation in scopes
    ):
        raise ValueError("future operation clock generation")


def _validate_view(
    connection: sqlite3.Connection,
    record: OperationRecord,
    plan: PlanValidation,
    attempts: tuple[AttemptView, ...],
    outcome: OperationOutcome | None,
) -> None:
    validate_operation_clock(record, plan, operation_clock(connection))
    validate_job_facts(record, plan, attempts, outcome)
    validate_events(connection, record, attempts)


def _validate_admission_plan(record: OperationRecord, plan: PlanValidation) -> None:
    a, s = record.admission, record.summary
    if (s.plan_id, s.plan_digest, s.task, s.tool, s.execution) != (
        plan.plan_id,
        plan.digest,
        *plan.selection,
    ):
        raise ValueError("job plan mismatch")
    if plan.status != "prepared" or a.delivery_required != plan.delivery_required:
        raise ValueError("prepared plan and its delivery policy required")
    if a.approval.binding_digest != plan.bound_digest or a.authorities != plan.authorities:
        raise ValueError("operation authority mismatch")
    if (a.admission_identity_epoch, a.admission_clock_generation) != (
        plan.identity_epoch,
        plan.clock_generation,
    ):
        raise ValueError("operation plan identity mismatch")


def validate_job_facts(
    record: OperationRecord,
    plan: PlanValidation,
    attempts: tuple[AttemptView, ...],
    outcome: OperationOutcome | None,
) -> None:
    _validate_admission_plan(record, plan)
    a, s = record.admission, record.summary
    if (
        record.dispatch_attempt_id is not None
        and record.dispatch_attempt_id != attempts[-1].attempt_id
    ):
        raise ValueError("dispatch must bind final attempt")
    if record.dispatch_attempt_id is None and record.event_count != (
        1 if s.status == "admitted" else 2
    ):
        raise ValueError("predispatch controls cannot create extra normal events")
    if record.recovery_reason is not None and attempts[-1].reason_code != record.recovery_reason:
        raise ValueError("recovery reason projection mismatch")
    if s.updated_at < s.created_at and (
        not s.clock_anomaly
        or (
            record.observed_identity_epoch,
            record.observed_clock_generation,
        )
        == (a.admission_identity_epoch, a.admission_clock_generation)
    ):
        raise ValueError("same-clock snapshot regressed or missing anomaly flag")
    if (
        not plan.prepared_at
        <= a.approval.approved_at
        <= s.created_at
        < a.approval.expires_at
        <= plan.expires_at
    ):
        raise ValueError("admission lifetime mismatch")
    validate_job_relationships(s, attempts, outcome)


def validate_history_projection(
    record: OperationRecord,
    attempts: tuple[AttemptView, ...],
    count: object,
    first: object,
    row: tuple[object, ...],
) -> None:
    """List checks count/latest projection, without reading the whole history payload."""
    owner, sequence, attempt_id, payload = row
    last = decode(OperationEvent, payload, MAX_EVENT_BYTES)
    if (
        (count, first, sequence) != (record.event_count, 1, record.event_count)
        or (owner, sequence, attempt_id)
        != (record.summary.operation_id, last.sequence, last.attempt_id)
        or last.attempt_id not in {a.attempt_id for a in attempts}
        or last.fence > record.fence
        or last.revision > record.summary.revision
        or (last.execution_status != "not_started") != (record.dispatch_attempt_id is not None)
    ):
        raise ValueError("history projection mismatch")
    if count == 1:
        _event_progress(record, last, None, {a.attempt_id: a.number for a in attempts}, False)
    elif count == 2 and record.dispatch_attempt_id is not None:
        _dispatch_authority(record, last)
    candidate = next(a for a in attempts if a.attempt_id == last.attempt_id)
    _event_candidate(record, last, candidate.number, candidate.created_at)
    _event_observation(record, last, None)
    _history_end(record, last, attempts)


def read_job(
    connection: sqlite3.Connection, operation_id: str, *, record: OperationRecord | None = None
) -> JobView:
    with read_snapshot(connection):
        record = record or read_operation(connection, operation_id)
        try:
            plan = read_plan(connection, record.summary.plan_id)
            attempts = read_attempts(connection, operation_id)
            outcome = read_outcome(connection, operation_id)
            _validate_view(connection, record, describe_plan(plan), attempts, outcome)
            return JobView(operation=record.summary, plan=plan, attempts=attempts, outcome=outcome)
        except YorungeError as error:
            if error.code == "plan_not_found":
                raise YorungeError("state_invalid") from None
            raise
        except (ValueError, TypeError, RecursionError):
            raise YorungeError("state_invalid") from None


def validate_operations(connection: sqlite3.Connection) -> None:
    # Validated plan facts reuse the preceding full plan pass, without retaining
    # mutable plan objects or reserializing up to 64 MiB of public show payloads.
    # The independent public quotas compose below MAX_JOB_BYTES; read_job also
    # validates the actual encoded JobView on every public show.
    with read_snapshot(connection):
        count = 0
        try:
            for row in connection.execute(f"SELECT {OPERATION_COLUMNS} FROM operations"):
                count += 1
                if count > MAX_OPERATIONS:
                    raise YorungeError("state_invalid")
                record = decode_operation(row)
                identifier = record.summary.operation_id
                saved = connection.execute(
                    f"SELECT {PLAN_COLUMNS} FROM execution_plans WHERE plan_id=?",
                    (record.summary.plan_id,),
                ).fetchone()
                if saved is None:
                    raise YorungeError("state_invalid")
                _validate_view(
                    connection,
                    record,
                    plan_validation(saved),
                    read_attempts(connection, identifier),
                    read_outcome(connection, identifier),
                )
        except (ValueError, TypeError, RecursionError):
            raise YorungeError("state_invalid") from None


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


def _validate_record_change(
    current: OperationRecord, record: OperationRecord, expected_revision: int
) -> None:
    old, new = current.summary, record.summary
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
    old = current.summary
    if old.revision != expected_revision:
        raise OperationError("operation_lease_lost", old.operation_id)
    if old.status in TERMINAL:
        if current == record:
            return
        raise OperationError("operation_conflict", old.operation_id)
    _validate_record_change(current, record, expected_revision)
    row = operation_row(record)
    result = connection.execute(
        "UPDATE operations SET plan_id=?,plan_digest=?,task=?,tool=?,execution=?,created_at=?,"
        "updated_at=?,status=?,revision=?,lease_expires_at=?,dispatch_attempt_id=?,payload=? "
        "WHERE operation_id=? AND revision=?",
        (*row[1:], row[0], expected_revision),
    )
    if result.rowcount != 1:
        raise OperationError("operation_lease_lost", record.summary.operation_id)


def _existing_attempt_needs_write(
    operation_id: str, item: AttemptView, saved: tuple[object, ...]
) -> bool:
    old = decode(AttemptView, saved[1], MAX_ATTEMPT_BYTES)
    if saved[0] != operation_id or (old.number, old.created_at) != (
        item.number,
        item.created_at,
    ):
        raise OperationError("operation_conflict", operation_id)
    if old.provider_run_id is not None and old.provider_run_id != item.provider_run_id:
        raise OperationError("operation_conflict", operation_id)
    if old.status in TERMINAL or old.status == "abandoned":
        if old != item:
            raise OperationError("operation_conflict", operation_id)
        return False
    return True


def write_attempt(connection: sqlite3.Connection, operation_id: str, attempt: AttemptView) -> None:
    if not connection.in_transaction:
        raise YorungeError("state_invalid")
    item = decode(
        AttemptView, canonical(attempt.model_dump(mode="json")).decode("ascii"), MAX_ATTEMPT_BYTES
    )
    record = read_operation(connection, operation_id)
    saved = connection.execute(
        "SELECT operation_id,payload FROM operation_attempts WHERE attempt_id=?",
        (item.attempt_id,),
    ).fetchone()
    if saved is None:
        if record.dispatch_attempt_id is not None or record.summary.status in TERMINAL:
            raise OperationError("operation_conflict", operation_id)
    elif not _existing_attempt_needs_write(operation_id, item, saved):
        return
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
