"""Bounded local job reads; one snapshot and batch dependencies per page."""

import sqlite3
from collections import defaultdict

from yorunge.adapters.execution_store import PLAN_COLUMNS, plan_validation
from yorunge.adapters.operation_store import (
    ATTEMPT_COLUMNS,
    OPERATION_COLUMNS,
    OperationClock,
    decode,
    decode_attempts,
    decode_operation,
    operation_clock,
    read_snapshot,
    validate_history_projection,
    validate_job_facts,
    validate_operation_clock,
)
from yorunge.adapters.validation_memo import validation_session
from yorunge.domain.errors import YorungeError
from yorunge.domain.jobs import JobsCursor, JobsQuery
from yorunge.domain.operations import MAX_OUTCOME_BYTES, JobsPage, OperationOutcome, OperationRecord


def _columns(alias: str, columns: str) -> str:
    return ",".join(f"{alias}.{name}" for name in columns.split(","))


def list_jobs(connection: sqlite3.Connection, query: JobsQuery) -> JobsPage:
    with read_snapshot(connection), validation_session():
        try:
            clock = operation_clock(connection)
            cursor = JobsCursor.decode(query.cursor) if query.cursor is not None else None
            if cursor is not None and not cursor.matches(clock.store_id, query):
                raise YorungeError("invalid_request")
            where: list[str] = []
            parameters: list[str] = []
            if query.status is not None:
                where.append("o.status=?")
                parameters.append(query.status)
            if query.plan_id is not None:
                where.append("o.plan_id=?")
                parameters.append(query.plan_id)
            if cursor is not None:
                where.append("(o.created_at,o.operation_id)>(?,?)")
                parameters.extend((cursor.created_at, cursor.operation_id))
            clause = " WHERE " + " AND ".join(where) if where else ""
            rows = connection.execute(
                f"SELECT {_columns('o', OPERATION_COLUMNS)},"
                f"{_columns('p', PLAN_COLUMNS)},r.payload "
                "FROM operations o LEFT JOIN execution_plans p ON p.plan_id=o.plan_id "
                "LEFT JOIN operation_outcomes r ON r.operation_id=o.operation_id"
                + clause
                + " ORDER BY o.created_at,o.operation_id LIMIT ?",
                (*parameters, query.limit + 1),
            ).fetchall()
            selected = rows[: query.limit]
            records = [decode_operation(tuple(row[:13])) for row in selected]
            _validate_page(connection, selected, records, clock)
            next_cursor = None
            if len(rows) > query.limit:
                last = records[-1].summary
                next_cursor = JobsCursor(
                    version=1,
                    store_id=clock.store_id,
                    status=query.status,
                    plan_id=query.plan_id,
                    created_at=last.created_at,
                    operation_id=last.operation_id,
                ).encoded()
            return JobsPage(
                jobs=tuple(record.summary for record in records), next_cursor=next_cursor
            )
        except (ValueError, TypeError, RecursionError):
            raise YorungeError("state_invalid") from None


def _validate_page(
    connection: sqlite3.Connection,
    rows: list[tuple[object, ...]],
    records: list[OperationRecord],
    clock: OperationClock,
) -> None:
    if not records:
        return
    identifiers = tuple(record.summary.operation_id for record in records)
    placeholders = ",".join("?" for _ in identifiers)
    attempts: dict[object, list[tuple[object, ...]]] = defaultdict(list)
    for row in connection.execute(
        f"SELECT {ATTEMPT_COLUMNS} FROM operation_attempts "
        f"WHERE operation_id IN ({placeholders}) ORDER BY operation_id,number LIMIT ?",
        (*identifiers, len(records) * 16 + 1),
    ):
        attempts[row[1]].append(tuple(row))
    history = {
        row[0]: tuple(row[1:])
        for row in connection.execute(
            "SELECT h.operation_id,h.n,h.first,e.operation_id,e.sequence,e.attempt_id,e.payload "
            "FROM (SELECT operation_id,count(*) n,min(sequence) first,max(sequence) last "
            f"FROM operation_events WHERE operation_id IN ({placeholders}) "
            "GROUP BY operation_id) h "
            "LEFT JOIN operation_events e ON e.operation_id=h.operation_id AND e.sequence=h.last",
            identifiers,
        )
    }
    for row, record in zip(rows, records, strict=True):
        plan = plan_validation(tuple(row[13:20]))
        current = decode_attempts(
            record.summary.operation_id, attempts[record.summary.operation_id]
        )
        outcome = None if row[20] is None else decode(OperationOutcome, row[20], MAX_OUTCOME_BYTES)
        validate_operation_clock(record, plan, clock)
        validate_job_facts(record, plan, current, outcome)
        latest = history.get(record.summary.operation_id)
        if latest is None:
            raise YorungeError("state_invalid")
        validate_history_projection(record, current, latest[0], latest[1], latest[2:])
