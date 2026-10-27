"""Disposable ADR review experiments and synthetic byte vectors; no product implementation."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import hmac
import json
import os
import platform
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path


def connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, isolation_level=None, timeout=0.1)
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def migration_chain(root: Path) -> dict[str, object]:
    path = root / "chain.db"
    with closing(connect(path)) as connection:
        connection.execute("CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY)")
        connection.execute("CREATE TABLE records(id INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO schema_migrations VALUES(1)")
        connection.execute("PRAGMA user_version=1")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("CREATE TABLE version_two(id INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO records VALUES(2)")
        connection.execute("INSERT INTO schema_migrations VALUES(2)")
        connection.execute("PRAGMA user_version=2")
        connection.execute("COMMIT")
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute("CREATE TABLE version_three(id INTEGER PRIMARY KEY)")
            connection.execute("INSERT INTO schema_migrations VALUES(3)")
            connection.execute("PRAGMA user_version=3")
            connection.execute("INSERT INTO records VALUES(2)")
        except sqlite3.IntegrityError:
            connection.execute("ROLLBACK")
        else:
            raise AssertionError("second migration step must fail")
    with closing(connect(path)) as connection:
        after_failure = connection.execute("PRAGMA user_version").fetchone()[0]
        history = [row[0] for row in connection.execute("SELECT version FROM schema_migrations")]
        assert after_failure == 2
        assert history == [1, 2]
        assert (
            connection.execute(
                "SELECT name FROM sqlite_schema WHERE name='version_three'"
            ).fetchall()
            == []
        )
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("CREATE TABLE version_three(id INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO schema_migrations VALUES(3)")
        connection.execute("PRAGMA user_version=3")
        connection.execute("COMMIT")
        after_retry = connection.execute("PRAGMA user_version").fetchone()[0]
        assert after_retry == 3
        assert connection.execute("SELECT count(*) FROM records WHERE id=2").fetchone()[0] == 1
    return {
        "reopened_version_after_second_step_failure": after_failure,
        "history_after_failure": history,
        "version_after_retry": after_retry,
    }


def foreign_key_gap(root: Path) -> dict[str, object]:
    with closing(connect(root / "foreign-key.db")) as connection:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("CREATE TABLE parent(id INTEGER PRIMARY KEY)")
        connection.execute("CREATE TABLE child(parent_id INTEGER REFERENCES parent(id))")
        connection.execute("INSERT INTO child VALUES(42)")
        connection.execute("PRAGMA foreign_keys=ON")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        assert integrity == "ok"
        assert len(violations) == 1
    return {"integrity_check": integrity, "foreign_key_check_violation_count": len(violations)}


def backup_gaps(root: Path) -> dict[str, object]:
    source = root / "source.db"
    target = root / "existing-target.db"
    with closing(connect(source)) as writer:
        writer.execute("CREATE TABLE operations(id INTEGER PRIMARY KEY, state TEXT)")
        writer.execute("INSERT INTO operations VALUES(1, 'unknown')")
        with closing(connect(target)) as destination:
            destination.execute("CREATE TABLE previous_target_content(id INTEGER)")
        before = hashlib.sha256(target.read_bytes()).hexdigest()
        try:
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(descriptor)
            raise AssertionError("no-clobber must reject existing target")
        assert hashlib.sha256(target.read_bytes()).hexdigest() == before
        writer.execute("BEGIN IMMEDIATE")
        try:
            with closing(connect(source)) as reader, closing(connect(target)) as destination:
                # Deliberately overwrite only our own disposable fixture to verify the API risk.
                reader.backup(destination)
                replaced = destination.execute(
                    "SELECT name FROM sqlite_schema WHERE name='previous_target_content'"
                ).fetchall()
                assert replaced == []
        finally:
            writer.execute("ROLLBACK")
        writer.execute("INSERT INTO operations VALUES(2, 'unknown')")
        live_ids = [row[0] for row in writer.execute("SELECT id FROM operations ORDER BY id")]
    with closing(connect(target)) as snapshot:
        snapshot_ids = [row[0] for row in snapshot.execute("SELECT id FROM operations ORDER BY id")]
    assert live_ids == [1, 2]
    assert snapshot_ids == [1]
    return {
        "no_clobber_rejected_existing_target_without_change": True,
        "backup_api_overwrote_existing_disposable_target": True,
        "separate_reader_backup_while_writer_reserved": True,
        "live_operation_ids": live_ids,
        "snapshot_operation_ids": snapshot_ids,
        "post_snapshot_unknown_operation_missing": True,
    }


def directory_sync_calls(root: Path) -> dict[str, object]:
    trace = []
    state = root / "state"
    keys = state / "keys"
    for directory in (state, keys):
        directory.mkdir(mode=0o700)
        for synced in (directory, directory.parent):
            descriptor = os.open(synced, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(descriptor)
                trace.append(str(synced.relative_to(root)))
            finally:
                os.close(descriptor)
    descriptor = os.open(
        keys / "synthetic.key", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "wb") as output:
        output.write(bytes(range(32)))
        output.flush()
        os.fsync(output.fileno())
        directory_descriptor = os.open(keys, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory_descriptor)
            trace.append("state/keys")
        finally:
            os.close(directory_descriptor)
        if sys.platform == "darwin":
            fcntl.fcntl(output.fileno(), fcntl.F_FULLFSYNC)
    return {
        "directory_fsync_trace": trace,
        "regular_file_fullfsync_completed": sys.platform == "darwin",
        "power_loss_verified": False,
    }


def canonical_json(value: dict[str, str]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def byte_vectors() -> dict[str, object]:
    assert hmac.digest(b"\x0b" * 20, b"Hi There", "sha256").hex() == (
        "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"
    )
    key = bytes(range(32))  # Published synthetic fixture, never a user's key.
    binding = {
        "identity_epoch": "00000000-0000-4000-8000-000000000001",
        "service_id": "evren-platform",
        "service_origin": "https://api.example.test",
        "api_base_path": "/api/v1",
        "reference_type": "env",
        "reference_name": "EVREN_PLATFORM_API_KEY",
    }
    encoded = canonical_json(binding)
    vectors = []
    for secret in ("synthetic-A", "örnek-anahtar"):
        raw = secret.encode("utf-8")
        message = (
            b"yorunge:credential-observation:v1\x00"
            + len(encoded).to_bytes(8, "big")
            + encoded
            + len(raw).to_bytes(8, "big")
            + raw
        )
        vectors.append(
            {
                "synthetic_secret": secret,
                "secret_utf8_hex": raw.hex(),
                "secret_byte_length": len(raw),
                "message_hex": message.hex(),
                "tag_hex": hmac.digest(key, message, "sha256").hex(),
            }
        )
    check = canonical_json(
        {
            "active_key_id": "00000000-0000-4000-8000-000000000003",
            "identity_epoch": binding["identity_epoch"],
            "store_id": "00000000-0000-4000-8000-000000000002",
        }
    )
    check_message = b"yorunge:key-check:v1\x00" + check
    return {
        "synthetic_only": True,
        "synthetic_key_hex": key.hex(),
        "binding": binding,
        "binding_json": encoded.decode("ascii"),
        "binding_byte_length": len(encoded),
        "credential_vectors": vectors,
        "key_check_json": check.decode("ascii"),
        "key_check_message_hex": check_message.hex(),
        "key_check_tag_hex": hmac.digest(key, check_message, "sha256").hex(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="yorunge-adr-review-") as directory:
        root = Path(directory)
        report = {
            "status": "research_only_not_product_acceptance",
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "sqlite": sqlite3.sqlite_version,
            "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "migration_chain": migration_chain(root),
            "relational_integrity_gap": foreign_key_gap(root),
            "backup_and_restore_gaps": backup_gaps(root),
            "directory_sync_calls": directory_sync_calls(root),
            "binding_v1_byte_vectors": byte_vectors(),
            "limits": [
                "Synthetic fixtures only; no user config, credentials, state or network.",
                "No target normalizer, product migration, backup, reset or restore implementation.",
                "No disk-full/sync-failure injection, concurrent migration or power-cut proof.",
                "No product restore gate; only the missing history risk is demonstrated.",
            ],
        }
    arguments.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    print("ADR review experiments completed; research only, not product acceptance.")


if __name__ == "__main__":
    main()
