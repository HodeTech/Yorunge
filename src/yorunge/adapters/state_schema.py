"""Immutable, checksummed SQL migration declarations."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from functools import lru_cache

APPLICATION_ID = 0x594F5255


@dataclass(frozen=True)
class Migration:
    from_version: int
    to_version: int
    statements: tuple[str, ...]

    @property
    def checksum(self) -> str:
        payload = {
            "from_version": self.from_version,
            "to_version": self.to_version,
            "statements": list(self.statements),
        }
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


MIGRATIONS = (
    Migration(
        0,
        1,
        (
            """CREATE TABLE state_meta (
singleton INTEGER PRIMARY KEY CHECK(singleton=1),
store_id TEXT NOT NULL UNIQUE CHECK(length(store_id)=36),
identity_epoch TEXT NOT NULL CHECK(length(identity_epoch)=36),
active_key_id TEXT NOT NULL CHECK(length(active_key_id)=36),
key_check BLOB NOT NULL CHECK(length(key_check)=32),
format_version INTEGER NOT NULL CHECK(format_version=1)
) STRICT""",
            """CREATE TABLE schema_migrations (
version INTEGER PRIMARY KEY CHECK(version>0),
checksum TEXT NOT NULL CHECK(length(checksum)=64),
applied_at TEXT NOT NULL CHECK(length(applied_at) BETWEEN 20 AND 40)
) STRICT""",
            """CREATE TABLE credential_bindings (
identity_epoch TEXT NOT NULL CHECK(length(identity_epoch)=36),
service_id TEXT NOT NULL CHECK(service_id IN ('evren-platform','evren-llm')),
service_origin TEXT NOT NULL CHECK(length(service_origin) BETWEEN 1 AND 2048),
api_base_path TEXT NOT NULL CHECK(length(api_base_path) BETWEEN 1 AND 2048),
reference_type TEXT NOT NULL CHECK(reference_type='env'),
reference_name TEXT NOT NULL CHECK(length(reference_name) BETWEEN 1 AND 128),
credential_id TEXT NOT NULL UNIQUE CHECK(length(credential_id)=36),
revision INTEGER NOT NULL CHECK(revision>0),
tag_format TEXT NOT NULL CHECK(tag_format='hmac-sha256-v1'),
tag BLOB NOT NULL CHECK(length(tag)=32),
observed_at TEXT NOT NULL CHECK(length(observed_at) BETWEEN 20 AND 40),
UNIQUE(identity_epoch,service_id,service_origin,api_base_path,reference_type,reference_name)
) STRICT""",
        ),
    ),
)


def schema_signature(connection: sqlite3.Connection) -> tuple[tuple[str, str, str, str], ...]:
    return tuple(
        connection.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_schema "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        ).fetchall()
    )


@lru_cache(maxsize=16)
def expected_schema(migrations: tuple[Migration, ...]) -> tuple[tuple[str, str, str, str], ...]:
    connection = sqlite3.connect(":memory:", isolation_level=None)
    try:
        for step in migrations:
            for statement in step.statements:
                connection.execute(statement)
        return schema_signature(connection)
    finally:
        connection.close()
