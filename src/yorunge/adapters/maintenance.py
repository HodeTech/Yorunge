"""Explicit, consent-bound identity maintenance under the common exclusive lock."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import field_validator

from yorunge.adapters import state_schema as schema
from yorunge.adapters.files import reject_constant, unique_object
from yorunge.adapters.local_files import (
    Deadline,
    durable_private_chain,
    file_lock,
    open_private,
    private_directory,
    private_stat,
    read_private,
    sync_directory,
    sync_private,
    write_new,
)
from yorunge.adapters.state import (
    DB_NAME,
    Metadata,
    apply_migration,
    backup,
    check_header,
    connect,
    connect_readonly,
    file_sha256,
    key_check,
    load_key,
    metadata,
    new_key,
    read_backup,
    sqlite_error_code,
    state_directory,
    validate,
)
from yorunge.domain.errors import YorungeError
from yorunge.domain.maintenance import IdentitySnapshot, MaintenancePreview
from yorunge.domain.models import Model
from yorunge.domain.state import StateInfo, canonical_uuid

INTENT_NAME = "restore-intent.json"
IDENTITY_TABLES = {"state_meta", "schema_migrations", "credential_bindings"}


class RestoreIntent(Model):
    format_version: Literal[1] = 1
    stage_id: str
    store_id: str
    identity_epoch: str
    key_id: str
    source: str
    source_sha256: str
    key_check_hex: str
    safety_backup_id: str | None

    @field_validator("stage_id", "store_id", "identity_epoch", "key_id", "safety_backup_id")
    @classmethod
    def uuid_value(cls, value: str | None) -> str | None:
        return None if value is None else canonical_uuid(value)

    @field_validator("source_sha256", "key_check_hex")
    @classmethod
    def hash_value(cls, value: str) -> str:
        if not re.fullmatch("[0-9a-f]{64}", value):
            raise ValueError("SHA256 required")
        return value


@contextmanager
def errors() -> Iterator[None]:
    try:
        yield
    except OSError:
        raise YorungeError("state_write_failed") from None
    except sqlite3.Error as error:
        raise YorungeError(sqlite_error_code(error)) from None


def present(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def owned_directory(path: Path) -> None:
    info = path.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise YorungeError("state_invalid")


def no_intent(root: Path) -> None:
    if present(root / INTENT_NAME):
        raise YorungeError("state_repair_required")


def quiescent(path: Path) -> None:
    check_header(path)
    if any(present(path.with_name(path.name + suffix)) for suffix in ("-journal", "-wal", "-shm")):
        raise YorungeError("state_repair_required")


def require_identity_runtime() -> None:
    tables = {
        name for kind, name, _, _ in schema.expected_schema(schema.MIGRATIONS) if kind == "table"
    }
    if tables != IDENTITY_TABLES:
        raise YorungeError("state_restore_unsupported")


def snapshot(connection: sqlite3.Connection, deadline: Deadline) -> IdentitySnapshot:
    version, value = validate(connection, schema.MIGRATIONS, full=True)
    digest = hashlib.sha256()
    count = 0
    for row in connection.execute(
        "SELECT credential_id,revision,identity_epoch,observed_at "
        "FROM credential_bindings ORDER BY credential_id"
    ):
        deadline.remaining()
        digest.update(json.dumps(row, separators=(",", ":"), ensure_ascii=True).encode() + b"\n")
        count += 1
    return IdentitySnapshot(
        store_id=value.store_id,
        identity_epoch=value.identity_epoch,
        store_schema_version=version,
        binding_count=count,
        binding_fingerprint=digest.hexdigest(),
    )


def make_preview(
    action: Literal["reset", "restore", "recover"],
    current: IdentitySnapshot | None,
    source: IdentitySnapshot | None = None,
    announced_epoch: str | None = None,
) -> MaintenancePreview:
    preview = MaintenancePreview(
        action=action,
        current=current,
        source=source,
        history_may_be_lost=action != "reset",
        announced_epoch=announced_epoch,
        digest="",
    )
    digest = hashlib.sha256(
        json.dumps(
            preview.model_dump(exclude={"digest"}),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode()
    ).hexdigest()
    return preview.model_copy(update={"digest": digest})


def validate_confirmation(confirmation: str) -> None:
    if not isinstance(confirmation, str) or not re.fullmatch("[0-9a-f]{64}", confirmation):
        raise YorungeError("invalid_request")


def consent(preview: MaintenancePreview, confirmation: str) -> None:
    validate_confirmation(confirmation)
    if confirmation != preview.digest:
        raise YorungeError("state_changed")


@contextmanager
def target_lock(root: Path, deadline: Deadline, *, create: bool) -> Iterator[None]:
    if create:
        private_directory(root)
        durable_private_chain(root)
    else:
        owned_directory(root)
    lock = root / "store.lock"
    if not present(lock):
        with os.scandir(root) as entries:
            payload = any(entry.name != "store.lock" for entry in entries)
        if payload and not present(lock):
            raise YorungeError("state_repair_required")
    with file_lock(lock, deadline, exclusive=True, create=create and not present(lock)):
        yield


def live_snapshot(root: Path, deadline: Deadline) -> IdentitySnapshot | None:
    no_intent(root)
    path = root / DB_NAME
    if not present(path):
        with os.scandir(root) as entries:
            if any(entry.name != "store.lock" for entry in entries):
                raise YorungeError("state_repair_required")
        return None
    quiescent(path)
    connection = connect_readonly(path, deadline)
    try:
        return snapshot(connection, deadline)
    finally:
        connection.close()


def inspect_target(root: Path, deadline: Deadline) -> IdentitySnapshot | None:
    if not present(root):
        return None
    owned_directory(root)
    if not present(root / "store.lock"):
        with os.scandir(root) as entries:
            if any(True for _ in entries):
                raise YorungeError("state_repair_required")
        return None
    with target_lock(root, deadline, create=False):
        return live_snapshot(root, deadline)


def preview_reset(path: Path | None) -> MaintenancePreview:
    with errors():
        root, deadline = state_directory(path), Deadline()
        with target_lock(root, deadline, create=False):
            current = live_snapshot(root, deadline)
            if current is None:
                raise YorungeError("state_repair_required")
            return make_preview("reset", current)


def reset_connection(
    connection: sqlite3.Connection,
    root: Path,
    deadline: Deadline,
    epoch: str,
    key_id: str,
    key: bytes,
) -> StateInfo:
    connection.execute("BEGIN IMMEDIATE")
    try:
        version, old = validate(connection, schema.MIGRATIONS, full=True)
        connection.execute(
            "UPDATE state_meta SET identity_epoch=?,active_key_id=?,key_check=? WHERE singleton=1",
            (epoch, key_id, key_check(key, old.store_id, epoch, key_id)),
        )
        _, value = validate(connection, schema.MIGRATIONS, full=True)
        load_key(root, value)
        deadline.remaining()
        connection.execute("COMMIT")
        return StateInfo(
            store_schema_version=version,
            store_id=value.store_id,
            identity_epoch=value.identity_epoch,
        )
    finally:
        if connection.in_transaction:
            connection.execute("ROLLBACK")


def upgrade(connection: sqlite3.Connection, root: Path, path: Path, deadline: Deadline) -> None:
    version, _ = validate(connection, schema.MIGRATIONS, full=True)
    for step in schema.MIGRATIONS[version:]:
        backup(root, path, deadline, schema.MIGRATIONS)
        connection.execute("BEGIN IMMEDIATE")
        try:
            apply_migration(connection, step)
            validate(connection, schema.MIGRATIONS, full=True)
            deadline.remaining()
            connection.execute("COMMIT")
        finally:
            if connection.in_transaction:
                connection.execute("ROLLBACK")


def reset(path: Path | None, confirmation: str) -> StateInfo:
    validate_confirmation(confirmation)
    with errors():
        root, deadline = state_directory(path), Deadline()
        with target_lock(root, deadline, create=False):
            current = live_snapshot(root, deadline)
            if current is None:
                raise YorungeError("state_repair_required")
            consent(make_preview("reset", current), confirmation)
            key_id, key = new_key(root)
            connection = connect(root / DB_NAME, deadline)
            try:
                upgrade(connection, root, root / DB_NAME, deadline)
                result = reset_connection(connection, root, deadline, str(uuid4()), key_id, key)
            finally:
                connection.close()
            sync_private(root / DB_NAME)
            return result


def source_snapshot(source: Path, deadline: Deadline) -> IdentitySnapshot:
    record = read_backup(source, deadline, schema.MIGRATIONS)
    if record.purpose != "migration":
        raise YorungeError("state_restore_unsupported")
    connection = connect_readonly(source / "snapshot.sqlite3", deadline)
    try:
        return snapshot(connection, deadline)
    finally:
        connection.close()


def preview_restore(source: Path, path: Path | None) -> MaintenancePreview:
    if not isinstance(source, Path):
        raise YorungeError("invalid_request")
    with errors():
        require_identity_runtime()
        root, deadline = state_directory(path), Deadline()
        source = state_directory(source)
        found = source_snapshot(source, deadline)
        return make_preview("restore", inspect_target(root, deadline), found)


def read_intent(root: Path) -> RestoreIntent:
    try:
        value = json.loads(
            read_private(root / INTENT_NAME, 8192).decode("utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
        if type(value.get("format_version")) is not int:
            raise ValueError("integer version required")
        return RestoreIntent.model_validate(value)
    except (ValueError, RecursionError, AttributeError):
        raise YorungeError("state_invalid") from None


def copy_snapshot(source: Path, target: Path, deadline: Deadline) -> None:
    original = open_private(source)
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "wb") as output, os.fdopen(original, "rb") as reader:
            original = -1
            os.fchmod(output.fileno(), 0o600)
            while chunk := reader.read(65536):
                deadline.remaining()
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
    finally:
        if original != -1:
            os.close(original)
    sync_private(target)


def intended(value: Metadata, intent: RestoreIntent) -> bool:
    return (value.store_id, value.identity_epoch, value.active_key_id) == (
        intent.store_id,
        intent.identity_epoch,
        intent.key_id,
    )


def intent_key(root: Path, intent: RestoreIntent) -> bytes:
    expected = Metadata(
        intent.store_id, intent.identity_epoch, intent.key_id, bytes.fromhex(intent.key_check_hex)
    )
    return load_key(root, expected)


def pair_snapshot(
    root: Path, path: Path, intent: RestoreIntent, deadline: Deadline
) -> IdentitySnapshot | None:
    quiescent(path)
    connection = connect_readonly(path, deadline)
    try:
        value = snapshot(connection, deadline)
        if not intended(metadata(connection), intent):
            return None
        load_key(root, metadata(connection))
        return value
    finally:
        connection.close()


def stage_snapshot(
    root: Path, intent: RestoreIntent, deadline: Deadline
) -> IdentitySnapshot | None:
    stage = root / ("restore-" + intent.stage_id + ".sqlite3")
    if not present(stage):
        return None
    private_stat(stage)
    try:
        return pair_snapshot(root, stage, intent, deadline)
    except YorungeError as error:
        if error.code not in ("state_invalid", "state_repair_required"):
            raise
    except sqlite3.Error as error:
        if getattr(error, "sqlite_errorcode", 0) & 255 not in (
            sqlite3.SQLITE_CORRUPT,
            sqlite3.SQLITE_NOTADB,
        ):
            raise
    return None


def stage_restore(root: Path, intent: RestoreIntent, deadline: Deadline) -> Path:
    key = intent_key(root, intent)
    stage = root / ("restore-" + intent.stage_id + ".sqlite3")
    if present(stage):
        if stage_snapshot(root, intent, deadline) is not None:
            sync_private(stage)
            return stage
    source = state_directory(Path(intent.source))
    record = read_backup(source, deadline, schema.MIGRATIONS)
    if (
        record.purpose != "migration"
        or record.source_store_id != intent.store_id
        or record.snapshot_sha256 != intent.source_sha256
    ):
        raise YorungeError("state_invalid")
    artifacts = [
        candidate
        for candidate in (
            stage,
            *(stage.with_name(stage.name + suffix) for suffix in ("-journal", "-wal", "-shm")),
        )
        if present(candidate)
    ]
    if artifacts:
        # Retain intent-owned partial output, including a sidecar orphaned by a prior cut.
        for candidate in artifacts:
            private_stat(candidate)
        quarantine = root / ("interrupted-" + str(uuid4()) + ".sqlite3")
        for candidate in artifacts:
            suffix = candidate.name[len(stage.name) :]
            os.rename(candidate, quarantine.with_name(quarantine.name + suffix))
        sync_directory(root)
    copy_snapshot(source / "snapshot.sqlite3", stage, deadline)
    if file_sha256(stage, deadline) != intent.source_sha256:
        raise YorungeError("state_invalid")
    connection = connect(stage, deadline)
    try:
        upgrade(connection, root, stage, deadline)
        reset_connection(connection, root, deadline, intent.identity_epoch, intent.key_id, key)
    finally:
        connection.close()
    sync_private(stage)
    return stage


def finish_restore(root: Path, intent: RestoreIntent, deadline: Deadline) -> StateInfo:
    intent_key(root, intent)
    live = root / DB_NAME
    valid_live = False
    if present(live):
        quiescent(live)
        connection = connect_readonly(live, deadline)
        try:
            validate(connection, schema.MIGRATIONS, full=True)
            valid_live = intended(metadata(connection), intent)
            if valid_live:
                load_key(root, metadata(connection))
        finally:
            connection.close()
    if not valid_live:
        stage = stage_restore(root, intent, deadline)
        deadline.remaining()
        os.replace(stage, live)
    sync_private(live)
    connection = connect_readonly(live, deadline)
    try:
        version, value = validate(connection, schema.MIGRATIONS, full=True)
        if not intended(value, intent):
            raise YorungeError("state_invalid")
        load_key(root, value)
    finally:
        connection.close()
    deadline.remaining()
    (root / INTENT_NAME).unlink()
    sync_directory(root)
    sync_private(live)
    return StateInfo(
        store_schema_version=version, store_id=value.store_id, identity_epoch=value.identity_epoch
    )


def restore(source: Path, path: Path | None, confirmation: str) -> StateInfo:
    validate_confirmation(confirmation)
    if not isinstance(source, Path):
        raise YorungeError("invalid_request")
    with errors():
        require_identity_runtime()
        root, deadline = state_directory(path), Deadline()
        source = state_directory(source)
        found = source_snapshot(source, deadline)
        # Reject stale consent before creating any target directory/key/lock.
        consent(make_preview("restore", inspect_target(root, deadline), found), confirmation)
        with target_lock(root, deadline, create=True):
            current = live_snapshot(root, deadline)
            found = source_snapshot(source, deadline)
            consent(make_preview("restore", current, found), confirmation)
            safety = None
            if current is not None:
                safety = backup(
                    root, root / DB_NAME, deadline, schema.MIGRATIONS, purpose="pre_restore"
                ).name
            key_id, key = new_key(root)
            record = read_backup(source, deadline, schema.MIGRATIONS)
            epoch = str(uuid4())
            intent = RestoreIntent(
                stage_id=str(uuid4()),
                store_id=found.store_id,
                identity_epoch=epoch,
                key_id=key_id,
                source=str(source),
                source_sha256=record.snapshot_sha256,
                key_check_hex=key_check(key, found.store_id, epoch, key_id).hex(),
                safety_backup_id=safety,
            )
            write_new(root / INTENT_NAME, intent.model_dump_json().encode("utf-8"))
            return finish_restore(root, intent, deadline)


def recovery_preview(root: Path, intent: RestoreIntent, deadline: Deadline) -> MaintenancePreview:
    intent_key(root, intent)
    live = root / DB_NAME
    current = pair_snapshot(root, live, intent, deadline) if present(live) else None
    if current is not None:
        return make_preview("recover", current, announced_epoch=intent.identity_epoch)
    staged = stage_snapshot(root, intent, deadline)
    if staged is not None:
        return make_preview("recover", None, staged, intent.identity_epoch)
    source = state_directory(Path(intent.source))
    record = read_backup(source, deadline, schema.MIGRATIONS)
    if record.snapshot_sha256 != intent.source_sha256 or record.source_store_id != intent.store_id:
        raise YorungeError("state_invalid")
    return make_preview("recover", None, source_snapshot(source, deadline), intent.identity_epoch)


def preview_recovery(path: Path | None) -> MaintenancePreview:
    with errors():
        require_identity_runtime()
        root, deadline = state_directory(path), Deadline()
        with target_lock(root, deadline, create=False):
            return recovery_preview(root, read_intent(root), deadline)


def recover(path: Path | None, confirmation: str) -> StateInfo:
    validate_confirmation(confirmation)
    with errors():
        require_identity_runtime()
        root, deadline = state_directory(path), Deadline()
        with target_lock(root, deadline, create=False):
            intent = read_intent(root)
            consent(recovery_preview(root, intent, deadline), confirmation)
            return finish_restore(root, intent, deadline)
