"""Derived, bounded expiry indexes for the shared durable clock."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from yorunge.domain.capabilities import CapabilityRecord, instant
from yorunge.domain.errors import YorungeError

MAX_CACHE_EXPIRIES = 10
MAX_STATE_EXPIRIES = 1024 * (MAX_CACHE_EXPIRIES + 2)
NEXT_EXPIRIES = (
    "SELECT expires_at FROM capability_expiries WHERE expires_at>? "
    "ORDER BY expires_at,cache_key LIMIT 1",
    "SELECT expires_at FROM execution_plans WHERE expires_at>? ORDER BY expires_at,plan_id LIMIT 1",
    "SELECT expires_at FROM execution_approvals WHERE expires_at>? "
    "ORDER BY expires_at,plan_id LIMIT 1",
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
    found = connection.execute(
        "SELECT expires_at FROM capability_expiries WHERE cache_key=? ORDER BY expires_at LIMIT ?",
        (record.key.digest(), MAX_CACHE_EXPIRIES + 1),
    ).fetchall()
    if found != [(date,) for date in cache_expiries(record)]:
        raise YorungeError("state_invalid")


def next_expiry(connection: sqlite3.Connection, high: str) -> datetime | None:
    try:
        dates = []
        for query in NEXT_EXPIRIES:
            row = connection.execute(query, (high,)).fetchone()
            if row is not None:
                dates.append(instant(row[0]))
        return min(dates, default=None)
    except (ValueError, TypeError):
        raise YorungeError("state_invalid") from None
