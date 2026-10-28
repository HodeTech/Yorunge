"""Owned SQLite state, migrations and durable snapshots. Imported only on explicit use."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import stat
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal
from uuid import uuid4

from pydantic import ConfigDict, Field, field_validator

from yorunge.adapters import state_schema as schema
from yorunge.adapters.files import reject_constant, unique_object
from yorunge.adapters.local_files import (
    Deadline,
    create_private_directory,
    durable_private_chain,
    file_lock,
    open_private,
    private_directory,
    private_stat,
    read_private,
    require_local_files,
    safe_ancestors,
    sync_private,
    write_new,
)
from yorunge.domain.credentials import EnvReference, normalize_target
from yorunge.domain.errors import ErrorCode, YorungeError
from yorunge.domain.models import Model
from yorunge.domain.state import StateInfo, canonical_uuid, check_utc

if TYPE_CHECKING:
    from yorunge.adapters.data_migrations import VerifiedTransform

DB_NAME = "state.sqlite3"
LOCK_NAME = "store.lock"
INTENT_NAME = "restore-intent.json"


def sqlite_error_code(error: sqlite3.Error) -> ErrorCode:
    number = getattr(error, "sqlite_errorcode", 0)
    primary = number & 255 if isinstance(number, int) else 0
    if primary in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED, sqlite3.SQLITE_INTERRUPT):
        return "state_busy"
    if primary in (sqlite3.SQLITE_FULL, sqlite3.SQLITE_IOERR):
        return "state_write_failed"
    return "state_invalid"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def key_check(key: bytes, store_id: str, epoch: str, key_id: str) -> bytes:
    value = {"store_id": store_id, "identity_epoch": epoch, "active_key_id": key_id}
    message = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")
    return hmac.digest(key, b"yorunge:key-check:v1\x00" + message, "sha256")


@dataclass(frozen=True)
class Metadata:
    store_id: str
    identity_epoch: str
    active_key_id: str
    key_check: bytes = field(repr=False)


class BackupManifest(Model):
    model_config = ConfigDict(defer_build=True)

    format_version: Literal[1] = 1
    source_store_id: str
    source_version: Annotated[int, Field(ge=1)]
    snapshot_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    purpose: Literal["migration", "pre_restore"]
    created_at: str

    @field_validator("format_version", mode="before")
    @classmethod
    def integer_format(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("integer format required")
        return value


def state_directory(path: Path | None) -> Path:
    require_local_files()
    if sqlite3.sqlite_version_info < (3, 37, 0):
        raise YorungeError("state_unsupported")
    try:
        return _state_directory(path)
    except OSError:
        raise YorungeError("state_write_failed") from None


def _state_directory(path: Path | None) -> Path:
    if path is not None and not isinstance(path, Path):
        raise YorungeError("invalid_request")
    chosen = (path if path is not None else Path.home() / ".local/state/yorunge").absolute()
    if "\x00" in str(chosen):
        raise YorungeError("invalid_request")
    try:
        os.fsencode(chosen)
    except UnicodeError:
        raise YorungeError("invalid_request") from None
    safe_ancestors(chosen)
    return Path(os.path.normpath(chosen))


def connect(path: Path, deadline: Deadline) -> sqlite3.Connection:
    connection = sqlite3.connect(path, isolation_level=None, timeout=min(1.0, deadline.remaining()))
    connection.set_progress_handler(lambda: int(time.monotonic() >= deadline.end), 1000)
    try:
        if connection.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
            raise YorungeError("state_invalid")
        settings = {"foreign_keys": 1, "trusted_schema": 0, "synchronous": 3}
        if sys.platform == "darwin":
            settings["fullfsync"] = 1
        for name, expected in settings.items():
            connection.execute(f"PRAGMA {name}={expected}")
            if connection.execute(f"PRAGMA {name}").fetchone() != (expected,):
                raise YorungeError("state_unsupported")
        return connection
    except BaseException:
        connection.close()
        raise


def check_header(path: Path) -> None:
    descriptor = open_private(path)
    with os.fdopen(descriptor, "rb") as source:
        header = source.read(100)
    if not header:
        raise YorungeError("state_repair_required")
    if (
        len(header) != 100
        or header[:16] != b"SQLite format 3\x00"
        or header[18:20] != b"\x01\x01"
        or int.from_bytes(header[68:72], "big") != schema.APPLICATION_ID
    ):
        raise YorungeError("state_invalid")
    for suffix in ("-journal", "-wal", "-shm"):
        candidate = path.with_name(path.name + suffix)
        if candidate.exists() or candidate.is_symlink():
            private_stat(candidate)
            if suffix != "-journal":
                raise YorungeError("state_invalid")


def metadata(connection: sqlite3.Connection) -> Metadata:
    rows = connection.execute(
        "SELECT store_id,identity_epoch,active_key_id,key_check,format_version "
        "FROM state_meta LIMIT 2"
    ).fetchall()
    if len(rows) != 1:
        raise YorungeError("state_invalid")
    store, epoch, key, check, version = rows[0]
    try:
        for value in (store, epoch, key):
            canonical_uuid(value)
        if (
            not isinstance(check, bytes)
            or len(check) != 32
            or type(version) is not int
            or version != 1
        ):
            raise ValueError("invalid metadata")
    except (ValueError, TypeError, AttributeError):
        raise YorungeError("state_invalid") from None
    return Metadata(store, epoch, key, check)


def validate(
    connection: sqlite3.Connection, migrations: tuple[schema.Migration, ...], *, full: bool
) -> tuple[int, Metadata]:
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if (
        connection.execute("PRAGMA application_id").fetchone()[0] != schema.APPLICATION_ID
        or type(version) is not int
        or not 1 <= version <= len(migrations)
    ):
        raise YorungeError("state_invalid")
    if schema.schema_signature(connection) != schema.expected_schema(migrations[:version]):
        raise YorungeError("state_invalid")
    history = connection.execute(
        "SELECT version,checksum,applied_at FROM schema_migrations ORDER BY version LIMIT ?",
        (len(migrations) + 1,),
    ).fetchall()
    if len(history) != version:
        raise YorungeError("state_invalid")
    try:
        for number, (applied, checksum, timestamp) in enumerate(history, 1):
            if applied != number or checksum != migrations[number - 1].checksum:
                raise ValueError("invalid migration history")
            check_utc(timestamp)
    except (ValueError, TypeError):
        raise YorungeError("state_invalid") from None
    result = metadata(connection)
    if full:
        validate_contents(connection)
    return version, result


def validate_contents(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA integrity_check(1)").fetchall() != [("ok",)]:
        raise YorungeError("state_invalid")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise YorungeError("state_invalid")
    rows = connection.execute(
        "SELECT identity_epoch,service_id,service_origin,api_base_path,reference_type,"
        "reference_name,credential_id,revision,tag_format,tag,observed_at "
        "FROM credential_bindings"
    )
    for row in rows:
        validate_binding_row(row)
    if connection.execute(
        "SELECT 1 FROM sqlite_schema WHERE type='table' AND name='cache_clock'"
    ).fetchone():
        from yorunge.adapters.capability_cache import validate_cache

        validate_cache(connection)
    if connection.execute(
        "SELECT 1 FROM sqlite_schema WHERE type='table' AND name='execution_plans'"
    ).fetchone():
        from yorunge.adapters.execution_store import validate_plans

        validate_plans(connection)
    if connection.execute(
        "SELECT 1 FROM sqlite_schema WHERE type='table' AND name='execution_approvals'"
    ).fetchone():
        from yorunge.adapters.execution_store import validate_approvals

        validate_approvals(connection)


def validate_binding_row(row: tuple[Any, ...]) -> None:
    epoch, service, origin, base, kind, name, identifier, revision, fmt, tag, when = row
    try:
        canonical_uuid(epoch)
        canonical_uuid(identifier)
        EnvReference(service_id=service, kind=kind, name=name)
        normalized = normalize_target(origin + base)
        if (
            normalized.service_origin != origin
            or normalized.api_base_path != base
            or type(revision) is not int
            or not 1 <= revision <= 2**63 - 1
            or fmt != "hmac-sha256-v1"
            or not isinstance(tag, bytes)
            or len(tag) != 32
        ):
            raise ValueError("invalid binding")
        check_utc(when)
    except (ValueError, TypeError, YorungeError):
        raise YorungeError("state_invalid") from None


def new_key(root: Path) -> tuple[str, bytes]:
    private_directory(root / "keys")
    if (root / "keys").stat().st_dev != root.stat().st_dev:
        raise YorungeError("state_invalid")
    durable_private_chain(root / "keys")
    identifier, key = str(uuid4()), secrets.token_bytes(32)
    write_new(root / "keys" / (identifier + ".key"), key)
    return identifier, key


def load_key(root: Path, value: Metadata) -> bytes:
    try:
        info = (root / "keys").lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700
            or info.st_dev != root.stat().st_dev
        ):
            raise YorungeError("state_invalid")
        key = read_private(root / "keys" / (value.active_key_id + ".key"), 32)
    except FileNotFoundError:
        raise YorungeError("state_repair_required") from None
    if len(key) != 32 or not hmac.compare_digest(
        key_check(key, value.store_id, value.identity_epoch, value.active_key_id), value.key_check
    ):
        raise YorungeError("state_repair_required")
    return key


def prepare_migration(step: schema.Migration, deadline: Deadline) -> VerifiedTransform | None:
    if not isinstance(step, schema.MigrationV2) or step.data_transform is None:
        return None
    from yorunge.adapters.data_migrations import prepare

    return prepare(step, deadline)


def apply_migration(
    connection: sqlite3.Connection,
    step: schema.Migration,
    deadline: Deadline,
    transform: VerifiedTransform | None = None,
) -> None:
    expected = step.data_transform if isinstance(step, schema.MigrationV2) else None
    if (transform.descriptor if transform is not None else None) != expected:
        raise YorungeError("state_invalid")
    if connection.execute("PRAGMA user_version").fetchone()[0] != step.from_version:
        raise YorungeError("state_invalid")
    for statement in step.statements:
        deadline.remaining()
        connection.execute(statement)
    if transform is not None:
        transform.run(connection, deadline)
    connection.execute(
        "INSERT INTO schema_migrations VALUES(?,?,?)", (step.to_version, step.checksum, utc_now())
    )
    connection.execute(f"PRAGMA user_version={step.to_version}")


def bootstrap(root: Path, deadline: Deadline, migrations: tuple[schema.Migration, ...]) -> None:
    with os.scandir(root) as entries:
        if any(entry.name != LOCK_NAME for entry in entries):
            raise YorungeError("state_repair_required")
    identifier, key = new_key(root)
    store_id, epoch = str(uuid4()), str(uuid4())
    write_new(root / DB_NAME, b"")
    connection = connect(root / DB_NAME, deadline)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(f"PRAGMA application_id={schema.APPLICATION_ID}")
        apply_migration(connection, migrations[0], deadline)
        connection.execute(
            "INSERT INTO state_meta VALUES(1,?,?,?,?,1)",
            (store_id, epoch, identifier, key_check(key, store_id, epoch, identifier)),
        )
        validate(connection, migrations, full=True)
        deadline.remaining()
        connection.execute("COMMIT")
    finally:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        connection.close()
    sync_private(root / DB_NAME)


def file_sha256(path: Path, deadline: Deadline) -> str:
    digest = hashlib.sha256()
    descriptor = open_private(path)
    with os.fdopen(descriptor, "rb") as source:
        while chunk := source.read(65536):
            deadline.remaining()
            digest.update(chunk)
    return digest.hexdigest()


def backup(
    root: Path,
    source: Path,
    deadline: Deadline,
    migrations: tuple[schema.Migration, ...],
    *,
    purpose: Literal["migration", "pre_restore"] = "migration",
) -> Path:
    private_directory(root / "backups")
    durable_private_chain(root / "backups")
    destination = root / "backups" / str(uuid4())
    create_private_directory(destination)
    if destination.stat().st_dev != root.stat().st_dev:
        raise YorungeError("state_invalid")
    target = destination / "snapshot.sqlite3"
    write_new(target, b"")
    original, created = private_stat(source), private_stat(target)
    if (original.st_dev, original.st_ino) == (created.st_dev, created.st_ino):
        raise YorungeError("state_invalid")
    reader, output = connect(source, deadline), None
    try:
        output = connect(target, deadline)
        reader.backup(
            output,
            pages=64,
            sleep=0.01,
            progress=lambda status, remaining, total: deadline.remaining(),
        )
        version, value = validate(output, migrations, full=True)
    finally:
        reader.close()
        if output is not None:
            output.close()
    sync_private(target)
    record = BackupManifest(
        source_store_id=value.store_id,
        source_version=version,
        snapshot_sha256=file_sha256(target, deadline),
        purpose=purpose,
        created_at=utc_now(),
    )
    write_new(destination / "complete.json", record.model_dump_json().encode("utf-8"))
    deadline.remaining()
    return destination


def read_backup(
    path: Path, deadline: Deadline, migrations: tuple[schema.Migration, ...]
) -> BackupManifest:
    path = path.absolute()
    safe_ancestors(path)
    info = path.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o700
        or info.st_uid != os.getuid()
    ):
        raise YorungeError("state_invalid")
    try:
        value = json.loads(
            read_private(path / "complete.json", 4096).decode("utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
        record = BackupManifest.model_validate(value)
        canonical_uuid(record.source_store_id)
        check_utc(record.created_at)
    except (ValueError, RecursionError, FileNotFoundError):
        raise YorungeError("state_invalid") from None
    target = path / "snapshot.sqlite3"
    if file_sha256(target, deadline) != record.snapshot_sha256:
        raise YorungeError("state_invalid")
    check_header(target)
    for suffix in ("-journal", "-wal", "-shm"):
        if target.with_name(target.name + suffix).exists():
            raise YorungeError("state_invalid")
    connection = connect_readonly(target, deadline)
    try:
        version, found = validate(connection, migrations, full=True)
    finally:
        connection.close()
    if found.store_id != record.source_store_id or version != record.source_version:
        raise YorungeError("state_invalid")
    return record


def connect_readonly(path: Path, deadline: Deadline) -> sqlite3.Connection:
    connection = sqlite3.connect(
        path.as_uri() + "?mode=ro&immutable=1",
        uri=True,
        isolation_level=None,
        timeout=min(1.0, deadline.remaining()),
    )
    connection.set_progress_handler(lambda: int(time.monotonic() >= deadline.end), 1000)
    try:
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA query_only=ON")
        return connection
    except BaseException:
        connection.close()
        raise


def maintain(
    root: Path, deadline: Deadline, migrations: tuple[schema.Migration, ...], *, check_key: bool
) -> None:
    with file_lock(root / LOCK_NAME, deadline, exclusive=True, create=False):
        if (root / INTENT_NAME).exists() or (root / INTENT_NAME).is_symlink():
            raise YorungeError("state_repair_required")
        if not (root / DB_NAME).exists():
            bootstrap(root, deadline, migrations)
        check_header(root / DB_NAME)
        connection = connect(root / DB_NAME, deadline)
        try:
            while True:
                version, value = validate(connection, migrations, full=True)
                if check_key:
                    load_key(root, value)
                if version == len(migrations):
                    break
                step = migrations[version]
                transform = prepare_migration(step, deadline)
                backup(root, root / DB_NAME, deadline, migrations)
                connection.execute("BEGIN IMMEDIATE")
                try:
                    if validate(connection, migrations, full=True)[0] != version:
                        raise YorungeError("state_invalid")
                    apply_migration(connection, step, deadline, transform)
                    _, updated = validate(connection, migrations, full=True)
                    if check_key:
                        load_key(root, updated)
                    deadline.remaining()
                    connection.execute("COMMIT")
                finally:
                    if connection.in_transaction:
                        connection.execute("ROLLBACK")
        finally:
            connection.close()


@dataclass
class Store:
    root: Path
    connection: sqlite3.Connection = field(repr=False)
    deadline: Deadline = field(repr=False)
    migrations: tuple[schema.Migration, ...] = field(repr=False)

    @property
    def info(self) -> StateInfo:
        version, value = validate(self.connection, self.migrations, full=False)
        return StateInfo(
            store_schema_version=version,
            store_id=value.store_id,
            identity_epoch=value.identity_epoch,
        )

    def verify(self) -> StateInfo:
        validate(self.connection, self.migrations, full=True)
        self.deadline.remaining()
        return self.info


def require_no_intent(root: Path) -> None:
    marker = root / INTENT_NAME
    if marker.exists() or marker.is_symlink():
        raise YorungeError("state_repair_required")


def prepare_root(path: Path | None, migrations: tuple[schema.Migration, ...]) -> Path:
    root = state_directory(path)
    if not migrations or any(
        step.from_version != number or step.to_version != number + 1
        for number, step in enumerate(migrations)
    ):
        raise YorungeError("state_invalid")
    private_directory(root)
    durable_private_chain(root)
    lock = root / LOCK_NAME
    if not lock.exists():
        with os.scandir(root) as entries:
            if any(entry.name != LOCK_NAME for entry in entries) and not lock.exists():
                raise YorungeError("state_repair_required")
    return root


@contextmanager
def verified_connection(
    root: Path,
    deadline: Deadline,
    migrations: tuple[schema.Migration, ...],
    *,
    check_key: bool,
) -> Iterator[tuple[sqlite3.Connection, int]]:
    check_header(root / DB_NAME)
    connection = connect(root / DB_NAME, deadline)
    try:
        version, value = validate(connection, migrations, full=False)
        if check_key:
            load_key(root, value)
        yield connection, version
    finally:
        connection.close()


@contextmanager
def open_store(
    path: Path | None = None,
    *,
    check_key: bool = True,
    timeout: float = 5.0,
) -> Iterator[Store]:
    require_local_files()
    if sqlite3.sqlite_version_info < (3, 37, 0):
        raise YorungeError("state_unsupported")
    try:
        deadline, migrations = Deadline(timeout), schema.MIGRATIONS
        root = prepare_root(path, migrations)
        lock, db = root / LOCK_NAME, root / DB_NAME
        with file_lock(lock, deadline, exclusive=False, create=not db.exists()):
            require_no_intent(root)
            if db.exists():
                with verified_connection(root, deadline, migrations, check_key=check_key) as opened:
                    connection, version = opened
                    if version == len(migrations):
                        yield Store(root, connection, deadline, migrations)
                        return
        from yorunge.adapters.validation_memo import validation_session

        with validation_session():
            maintain(root, deadline, migrations, check_key=check_key)
            with file_lock(lock, deadline, exclusive=False, create=False):
                require_no_intent(root)
                with verified_connection(root, deadline, migrations, check_key=check_key) as opened:
                    connection, version = opened
                    if version != len(migrations):
                        raise YorungeError("state_invalid")
                    yield Store(root, connection, deadline, migrations)
    except OSError:
        raise YorungeError("state_write_failed") from None
    except sqlite3.Error as error:
        raise YorungeError(sqlite_error_code(error)) from None
