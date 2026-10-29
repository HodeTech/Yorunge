"""Operation consent fingerprint and atomic identity-reset invalidation."""

import hashlib
import sqlite3
from datetime import datetime

from yorunge.adapters.local_files import Deadline
from yorunge.adapters.operation_store import (
    OPERATION_COLUMNS,
    append_event,
    decode_operation,
    read_attempts,
    read_outcome,
    write_attempt,
    write_outcome,
    write_record,
)
from yorunge.domain.capabilities import canonical, timestamp
from yorunge.domain.operations import TERMINAL, OperationEvent, OperationOutcome, OperationRecord


def operation_snapshot(connection: sqlite3.Connection, deadline: Deadline) -> dict[str, int | str]:
    digest = hashlib.sha256()
    count = attempts = nonterminal = unknown = 0
    exists = connection.execute(
        "SELECT 1 FROM sqlite_schema WHERE type='table' AND name='operations'"
    ).fetchone()
    if exists:
        for row in connection.execute(
            f"SELECT {OPERATION_COLUMNS} FROM operations ORDER BY operation_id"
        ):
            deadline.remaining()
            record = decode_operation(row)
            summary, lease = record.summary, record.lease
            current = read_attempts(connection, summary.operation_id)[-1]
            outcome = read_outcome(connection, summary.operation_id)
            outcome_digest = (
                hashlib.sha256(canonical(outcome.model_dump(mode="json"))).hexdigest()
                if outcome
                else None
            )
            digest.update(
                canonical(
                    (
                        summary.operation_id,
                        summary.revision,
                        summary.status,
                        current.attempt_id,
                        record.dispatch_attempt_id,
                        lease.owner_id if lease else None,
                        record.fence,
                        lease.ownership_identity_epoch if lease else None,
                        lease.ownership_clock_generation if lease else None,
                        record.recovery_reason is not None,
                        record.recovery_reason,
                        outcome_digest,
                    )
                )
                + b"\n"
            )
            count += 1
            attempts += summary.attempt_count
            nonterminal += summary.status not in TERMINAL
            unknown += summary.status == "unknown"
    return {
        "operation_count": count,
        "attempt_count": attempts,
        "nonterminal_operation_count": nonterminal,
        "unknown_operation_count": unknown,
        "operation_fingerprint": digest.hexdigest(),
    }


def invalidate_operations(
    connection: sqlite3.Connection, epoch: str, now: datetime, deadline: Deadline
) -> None:
    if not connection.in_transaction:
        raise ValueError("reset transaction required")
    moment = timestamp(now)
    connection.execute(
        "UPDATE cache_clock SET high_watermark=? WHERE identity_epoch=?", (moment, epoch)
    )
    rows = connection.execute(
        f"SELECT {OPERATION_COLUMNS} FROM operations WHERE status NOT IN "
        "('succeeded','failed','cancelled') ORDER BY operation_id"
    ).fetchall()
    for row in rows:
        deadline.remaining()
        record = decode_operation(row)
        _invalidate_operation(connection, record, epoch, moment)


def _invalidate_operation(
    connection: sqlite3.Connection, record: OperationRecord, epoch: str, moment: str
) -> None:
    summary = record.summary
    current = read_attempts(connection, summary.operation_id)[-1]
    armed = record.dispatch_attempt_id is not None
    execution = "not_started"
    if armed:
        execution = "succeeded" if summary.execution_status == "succeeded" else "unknown"
    delivery = (
        "unknown"
        if execution == "succeeded" and record.admission.delivery_required
        else summary.delivery_status
    )
    changed = record.model_copy(
        update={
            "summary": summary.model_copy(
                update={
                    "status": "unknown" if armed else "cancelled",
                    "execution_status": execution,
                    "delivery_status": delivery,
                    "updated_at": moment,
                    "revision": summary.revision + 1,
                    "clock_anomaly": summary.clock_anomaly or moment < summary.updated_at,
                }
            ),
            "lease": None,
            "event_count": record.event_count + (not armed),
            "recovery_reason": "identity_reset" if armed else None,
            "observed_identity_epoch": epoch,
            "observed_clock_generation": 1,
        }
    )
    attempt = current.model_copy(
        update={
            "status": changed.summary.status,
            "updated_at": moment,
            "reason_code": "identity_reset",
        }
    )
    write_record(connection, changed, expected_revision=summary.revision)
    write_attempt(connection, summary.operation_id, attempt)
    if not armed:
        append_event(
            connection,
            summary.operation_id,
            OperationEvent(
                sequence=changed.event_count,
                revision=changed.summary.revision,
                fence=changed.fence,
                attempt_id=attempt.attempt_id,
                observed_at=moment,
                identity_epoch=epoch,
                clock_generation=1,
                status="cancelled",
                execution_status="not_started",
                delivery_status=summary.delivery_status,
                reason_code="identity_reset",
            ),
        )
        write_outcome(
            connection,
            summary.operation_id,
            OperationOutcome(
                recorded_at=moment,
                execution_status="not_started",
                delivery_status=summary.delivery_status,
                provider_exit_code=None,
                reason_code="identity_reset",
            ),
        )
