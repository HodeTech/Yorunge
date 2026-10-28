"""Frozen capability-expiries-v1 algorithm. Only change by a new migration identity."""

import json
import re
from datetime import datetime
from typing import Any


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise ValueError(value)


def expiry(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z", value, flags=re.ASCII
    ):
        raise ValueError("canonical expiry required")
    datetime.fromisoformat(value)
    return value


def record_expiries(payload: object) -> list[str]:
    if not isinstance(payload, str) or len(payload.encode("utf-8")) > 32768:
        raise ValueError("bounded source required")
    raw = json.loads(payload, object_pairs_hook=unique_object, parse_constant=reject_constant)
    if not isinstance(raw, dict) or type(raw.get("schema_version")) is not int:
        raise ValueError("explicit record version required")
    if raw["schema_version"] != 2:
        raise ValueError("record version unsupported")
    evidence = raw.get("evidence")
    if not isinstance(evidence, list) or len(evidence) > 8:
        raise ValueError("bounded evidence required")
    dates = {expiry(raw.get("expires_at"))}
    for proof in evidence:
        if not isinstance(proof, dict):
            raise ValueError("proof required")
        dates.add(expiry(proof.get("expires_at")))
    marker = raw.get("conflict_until")
    if marker is not None:
        dates.add(expiry(marker))
    return sorted(dates)


def apply(connection: Any) -> None:
    count = 0
    for cache_key, payload in connection.source_rows():
        count += 1
        if count > 1024:
            raise ValueError("bounded source required")
        for date in record_expiries(payload):
            connection.insert_expiry(cache_key, date)
