"""Immutable V1/V2 migration declarations; published SQL identities remain frozen."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from functools import lru_cache

from yorunge.domain.errors import YorungeError

APPLICATION_ID = 0x594F5255


@dataclass(frozen=True)
class Migration:
    from_version: int
    to_version: int
    statements: tuple[str, ...]

    def __post_init__(self) -> None:
        self.check_fields()
        if self.to_version > 4:
            raise YorungeError("state_invalid")

    def check_fields(self) -> None:
        if (
            type(self.from_version) is not int
            or type(self.to_version) is not int
            or self.from_version < 0
            or self.to_version != self.from_version + 1
            or type(self.statements) is not tuple
            or not self.statements
        ):
            raise YorungeError("state_invalid")
        for statement in self.statements:
            if (
                not isinstance(statement, str)
                or not statement
                or any(char in statement for char in ("\r", "\ufeff"))
            ):
                raise YorungeError("state_invalid")
            try:
                statement.encode("utf-8")
            except UnicodeError:
                raise YorungeError("state_invalid") from None

    def manifest(self) -> dict[str, object]:
        return {
            "from_version": self.from_version,
            "to_version": self.to_version,
            "statements": list(self.statements),
        }

    @property
    def checksum(self) -> str:
        encoded = json.dumps(
            self.manifest(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class DataTransform:
    id: str
    code_sha256: str

    def __post_init__(self) -> None:
        if (
            self.id != "capability-expiries-v1"
            or not isinstance(self.code_sha256, str)
            or len(self.code_sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.code_sha256)
        ):
            raise YorungeError("state_invalid")


@dataclass(frozen=True)
class MigrationV2(Migration):
    manifest_version: int = 2
    data_transform: DataTransform | None = None

    def __post_init__(self) -> None:
        self.check_fields()
        if (
            type(self.manifest_version) is not int
            or self.manifest_version != 2
            or self.to_version < 5
            or (self.to_version == 5) != (self.data_transform is not None)
            or (self.data_transform is not None and type(self.data_transform) is not DataTransform)
        ):
            raise YorungeError("state_invalid")

    def manifest(self) -> dict[str, object]:
        value = super().manifest()
        value["manifest_version"] = self.manifest_version
        if self.data_transform is not None:
            value["data_transform"] = {
                "id": self.data_transform.id,
                "code_sha256": self.data_transform.code_sha256,
            }
        return value


def migration_from_manifest(value: object) -> Migration:
    """Closed internal decoder, never a DB/config/CLI manifest import surface."""
    try:
        if not isinstance(value, dict):
            raise ValueError("manifest object required")
        fields = {"from_version", "to_version", "statements"}
        v2 = "manifest_version" in value
        if v2:
            fields.add("manifest_version")
            if value.get("to_version") == 5:
                fields.add("data_transform")
        if set(value) != fields or not isinstance(value["statements"], list):
            raise ValueError("closed manifest required")
        args = (value["from_version"], value["to_version"], tuple(value["statements"]))
        if not v2:
            return Migration(*args)
        descriptor = None
        if "data_transform" in value:
            raw = value["data_transform"]
            if not isinstance(raw, dict) or set(raw) != {"id", "code_sha256"}:
                raise ValueError("closed descriptor required")
            descriptor = DataTransform(raw["id"], raw["code_sha256"])
        return MigrationV2(*args, value["manifest_version"], descriptor)
    except (ValueError, TypeError, KeyError):
        raise YorungeError("state_invalid") from None


def migration_from_json(payload: bytes) -> Migration:
    """Decode internal manifest evidence; this is not exposed through product inputs."""

    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in items:
            if key in value:
                raise ValueError("duplicate key")
            value[key] = item
        return value

    def reject(value: str) -> None:
        raise ValueError(value)

    try:
        return migration_from_manifest(
            json.loads(payload.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject)
        )
    except (ValueError, TypeError, RecursionError):
        raise YorungeError("state_invalid") from None


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
    Migration(
        3,
        4,
        (
            """CREATE TABLE execution_approvals (
plan_id TEXT PRIMARY KEY REFERENCES execution_plans(plan_id) ON DELETE CASCADE,
approval_id TEXT NOT NULL UNIQUE CHECK(length(approval_id)=36),
status TEXT NOT NULL CHECK(status IN ('approved','revoked')),
approved_at TEXT NOT NULL CHECK(length(approved_at)=27),
expires_at TEXT NOT NULL CHECK(length(expires_at)=27),
revoked_at TEXT CHECK(revoked_at IS NULL OR length(revoked_at)=27),
payload TEXT NOT NULL CHECK(length(payload)<=4096)
) STRICT""",
        ),
    ),
    MigrationV2(
        4,
        5,
        (
            """CREATE TABLE capability_expiries (
cache_key TEXT NOT NULL REFERENCES capability_cache(cache_key) ON DELETE CASCADE,
expires_at TEXT NOT NULL CHECK(length(expires_at)=27),
PRIMARY KEY(cache_key,expires_at)
) STRICT""",
            "CREATE INDEX capability_expiry_order ON capability_expiries(expires_at,cache_key)",
            "CREATE INDEX execution_plan_expiry ON execution_plans(expires_at,plan_id)",
            "CREATE INDEX execution_approval_expiry ON execution_approvals(expires_at,plan_id)",
        ),
        data_transform=DataTransform(
            "capability-expiries-v1",
            "b1ffc8e3ce1dc6fc04c2afe4c2aa50ed6cd2e26deaf0b07ef0caab6fc0c83d18",
        ),
    ),
    MigrationV2(
        5,
        6,
        (
            """CREATE TABLE operations (
operation_id TEXT PRIMARY KEY CHECK(length(operation_id)=36),
plan_id TEXT NOT NULL UNIQUE REFERENCES execution_plans(plan_id) ON DELETE RESTRICT,
plan_digest TEXT NOT NULL CHECK(length(plan_digest)=64),
task TEXT NOT NULL,
tool TEXT,
execution TEXT NOT NULL,
created_at TEXT NOT NULL CHECK(length(created_at)=27),
updated_at TEXT NOT NULL CHECK(length(updated_at)=27),
status TEXT NOT NULL CHECK(status IN (
'admitted','submitted','running','unknown','succeeded','failed','cancelled')),
revision INTEGER NOT NULL CHECK(revision>0),
lease_expires_at TEXT CHECK(lease_expires_at IS NULL OR length(lease_expires_at)=27),
dispatch_attempt_id TEXT,
payload TEXT NOT NULL CHECK(length(CAST(payload AS BLOB))<=16384),
FOREIGN KEY(operation_id,dispatch_attempt_id)
REFERENCES operation_attempts(operation_id,attempt_id) DEFERRABLE INITIALLY DEFERRED
) STRICT""",
            """CREATE TABLE operation_attempts (
attempt_id TEXT PRIMARY KEY CHECK(length(attempt_id)=36),
operation_id TEXT NOT NULL REFERENCES operations(operation_id) ON DELETE RESTRICT,
number INTEGER NOT NULL CHECK(number BETWEEN 1 AND 16),
status TEXT NOT NULL CHECK(status IN (
'claimed','abandoned','submitted','running','unknown','succeeded','failed','cancelled')),
payload TEXT NOT NULL CHECK(length(CAST(payload AS BLOB))<=4096),
UNIQUE(operation_id,number),
UNIQUE(operation_id,attempt_id)
) STRICT""",
            """CREATE TABLE operation_events (
operation_id TEXT NOT NULL REFERENCES operations(operation_id) ON DELETE RESTRICT,
sequence INTEGER NOT NULL CHECK(sequence BETWEEN 1 AND 256),
attempt_id TEXT NOT NULL,
payload TEXT NOT NULL CHECK(length(CAST(payload AS BLOB))<=1024),
PRIMARY KEY(operation_id,sequence),
FOREIGN KEY(operation_id,attempt_id)
REFERENCES operation_attempts(operation_id,attempt_id) ON DELETE RESTRICT
) STRICT""",
            """CREATE TABLE operation_outcomes (
operation_id TEXT PRIMARY KEY REFERENCES operations(operation_id) ON DELETE RESTRICT,
payload TEXT NOT NULL CHECK(length(CAST(payload AS BLOB))<=4096)
) STRICT""",
            "CREATE INDEX operation_order ON operations(created_at,operation_id)",
            "CREATE INDEX operation_status_order ON operations(status,created_at,operation_id)",
            "CREATE INDEX operation_lease_expiry ON operations(lease_expires_at,operation_id)",
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
