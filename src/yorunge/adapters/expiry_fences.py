"""Derived, bounded expiry indexes for the shared durable clock."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from yorunge.domain.capabilities import CapabilityRecord, instant
from yorunge.domain.errors import YorungeError

MAX_CACHE_EXPIRIES = 10
MAX_STATE_EXPIRIES = 1024 * (MAX_CACHE_EXPIRIES + 3)
NEXT_EXPIRIES = (
    "SELECT expires_at FROM capability_expiries WHERE expires_at>? "
    "ORDER BY expires_at,cache_key LIMIT 1",
    "SELECT expires_at FROM execution_plans WHERE expires_at>? ORDER BY expires_at,plan_id LIMIT 1",
    "SELECT expires_at FROM execution_approvals WHERE expires_at>? "
    "ORDER BY expires_at,plan_id LIMIT 1",
    "SELECT lease_expires_at FROM operations WHERE lease_expires_at>? "
    "ORDER BY lease_expires_at,operation_id LIMIT 1",
)


def cache_expiries(record: CapabilityRecord) -> tuple[str, ...]:
    dates = {record.expires_at, *(proof.expires_at for proof in record.evidence)}
    if record.conflict_until is not None:
        dates.add(record.conflict_until)
    return tuple(sorted(dates))


def save_expiries(connection: sqlite3.Connection, record: CapabilityRecord) -> None:
    digest = record.key.digest()
    connection.execute("DELETE FROM capability_expiries WHERE cache_key=?", (digest,))
    connection.executemany(
        "INSERT INTO capability_expiries VALUES(?,?)",
        ((digest, date) for date in cache_expiries(record)),
    )


def check_expiries(connection: sqlite3.Connection, record: CapabilityRecord) -> None:
    check_expiry_dates(connection, record.key.digest(), cache_expiries(record))


def check_expiry_dates(connection: sqlite3.Connection, key: str, dates: tuple[str, ...]) -> None:
    found = connection.execute(
        "SELECT expires_at FROM capability_expiries WHERE cache_key=? ORDER BY expires_at LIMIT ?",
        (key, MAX_CACHE_EXPIRIES + 1),
    ).fetchall()
    if found != [(date,) for date in dates]:
        raise YorungeError("state_invalid")


def next_expiry(connection: sqlite3.Connection, high: str) -> datetime | None:
    try:
        dates = []
        for query in NEXT_EXPIRIES:
            # Historical schema-2..5 migration validation precedes the consumer.
            if (
                "FROM operations " in query
                and connection.execute(
                    "SELECT 1 FROM sqlite_schema WHERE type='table' AND name='operations'"
                ).fetchone()
                is None
            ):
                continue
            row = connection.execute(query, (high,)).fetchone()
            if row is not None:
                dates.append(instant(row[0]))
        return min(dates, default=None)
    except (ValueError, TypeError):
        raise YorungeError("state_invalid") from None
