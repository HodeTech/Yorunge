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
    Migration(
        1,
        2,
        (
            """CREATE TABLE cache_clock (
singleton INTEGER PRIMARY KEY CHECK(singleton=1),
identity_epoch TEXT NOT NULL CHECK(length(identity_epoch)=36),
clock_generation INTEGER NOT NULL CHECK(clock_generation>0),
high_watermark TEXT NOT NULL CHECK(length(high_watermark)=27),
anomaly_active INTEGER NOT NULL CHECK(anomaly_active IN (0,1)),
mutation_revision INTEGER NOT NULL CHECK(mutation_revision>=0)
) STRICT""",
            """INSERT INTO cache_clock SELECT 1,identity_epoch,1,
'0001-01-01T00:00:00.000000Z',0,0 FROM state_meta WHERE singleton=1""",
            """CREATE TABLE capability_cache (
cache_key TEXT PRIMARY KEY CHECK(length(cache_key)=64),
key_json TEXT NOT NULL CHECK(length(key_json)<=18432),
projection_key TEXT NOT NULL CHECK(length(projection_key)<=18432),
group_key TEXT NOT NULL CHECK(length(group_key)<=128),
payload TEXT NOT NULL CHECK(length(payload)<=32768),
mutation_revision INTEGER NOT NULL CHECK(mutation_revision>0),
checked_at TEXT NOT NULL CHECK(length(checked_at)=27),
pinned_until TEXT CHECK(pinned_until IS NULL OR length(pinned_until)=27)
) STRICT""",
            "CREATE INDEX capability_projection ON capability_cache"
            "(projection_key,checked_at DESC,cache_key)",
            "CREATE INDEX capability_groups ON capability_cache(group_key,checked_at,cache_key)",
        ),
    ),
    Migration(
        2,
        3,
        (
            """CREATE TABLE execution_plans (
plan_id TEXT PRIMARY KEY CHECK(length(plan_id)=36),
digest TEXT NOT NULL CHECK(length(digest)=64),
task TEXT NOT NULL,
prepared_at TEXT NOT NULL CHECK(length(prepared_at)=27),
expires_at TEXT NOT NULL CHECK(length(expires_at)=27),
status TEXT NOT NULL CHECK(status IN ('draft','prepared')),
payload TEXT NOT NULL CHECK(length(payload)<=65536)
) STRICT""",
            "CREATE INDEX execution_plan_order ON execution_plans(prepared_at,plan_id)",
        ),
    ),
)


def schema_signature(connection: sqlite3.Connection) -> tuple[tuple[str, str, str, str], ...]:
    return tuple(
        connection.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_schema "
            "WHERE substr(name,1,7) != 'sqlite_' ORDER BY type,name"
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
