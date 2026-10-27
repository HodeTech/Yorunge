import errno
import hashlib
import json
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path
from uuid import UUID

import pytest

from yorunge import api
from yorunge.adapters import local_files, state, state_schema
from yorunge.adapters.local_files import Deadline, file_lock
from yorunge.adapters.state import DB_NAME, open_store
from yorunge.adapters.state_schema import Migration
from yorunge.domain.errors import YorungeError


def modify(root, statement, arguments=()):
    with closing(sqlite3.connect(root / DB_NAME, isolation_level=None)) as connection:
        connection.execute(statement, arguments)


def query(root, statement):
    with closing(sqlite3.connect(root / DB_NAME)) as connection:
        return connection.execute(statement).fetchall()


def test_real_state_reopen_cli_and_pragmas(tmp_path, cli):
    root = tmp_path / "state"
    first = api.initialize_state(state_dir=root)
    assert api.initialize_state(state_dir=root) == first
    with open_store(root) as store:
        assert store.connection.execute("PRAGMA journal_mode").fetchone() == ("delete",)
        assert store.connection.execute("PRAGMA synchronous").fetchone() == (3,)
        assert store.connection.execute("PRAGMA foreign_keys").fetchone() == (1,)
        assert store.connection.execute("PRAGMA trusted_schema").fetchone() == (0,)
        assert store.connection.execute("PRAGMA user_version").fetchone() == (1,)
        assert store.connection.execute("PRAGMA application_id").fetchone() == (0x594F5255,)
        assert {
            row[0]
            for row in store.connection.execute("SELECT name FROM sqlite_schema WHERE type='table'")
        } == {"state_meta", "schema_migrations", "credential_bindings"}
    result = cli("state", "init", "--state-dir", str(root), "--output", "json", state=True)
    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == first.model_dump(mode="json")
    assert (root.stat().st_mode & 0o777) == 0o700
    for path in root.rglob("*"):
        assert (path.stat().st_mode & 0o777) == (0o700 if path.is_dir() else 0o600)


@pytest.mark.parametrize(
    "option,value", [("--profile", "work"), ("--project", "chosen"), ("--config", "missing.toml")]
)
def test_unrelated_state_options_fail_before_creating_files(tmp_path, cli, option, value):
    root = tmp_path / "state"
    result = cli(
        option, value, "state", "init", "--state-dir", str(root), "--output", "json", state=True
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert json.loads(result.stderr)["code"] == "invalid_request"
    assert not root.exists()


@pytest.mark.parametrize("target", ["directory", "database", "key", "lock", "symlink"])
def test_unsafe_permissions_and_links_rejected_without_repair(tmp_path, target):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    selected = {
        "directory": root,
        "database": root / DB_NAME,
        "key": next((root / "keys").glob("*.key")),
        "lock": root / "store.lock",
    }.get(target)
    if target == "symlink":
        saved = root / "preserved.sqlite3"
        (root / DB_NAME).rename(saved)
        (root / DB_NAME).symlink_to(saved)
    else:
        selected.chmod(0o755 if target == "directory" else 0o644)
    before = {path.name for path in (root / "keys").iterdir()}
    with pytest.raises(YorungeError) as failure:
        api.initialize_state(state_dir=root)
    assert failure.value.code == "state_invalid"
    assert {path.name for path in (root / "keys").iterdir()} == before
    if selected is not None:
        assert selected.stat().st_mode & 0o777 == (0o755 if target == "directory" else 0o644)


@pytest.mark.parametrize("kind", ["missing", "wrong", "short"])
def test_missing_wrong_key_never_regenerated(tmp_path, kind):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    key = next((root / "keys").glob("*.key"))
    before = key.name
    if kind == "missing":
        key.unlink()
    else:
        key.write_bytes(b"x" * (32 if kind == "wrong" else 1))
    with pytest.raises(YorungeError) as failure:
        api.initialize_state(state_dir=root)
    assert failure.value.code == "state_repair_required"
    assert [path.name for path in (root / "keys").iterdir()] == (
        [] if kind == "missing" else [before]
    )


@pytest.mark.parametrize(
    "sql",
    [
        "PRAGMA user_version=2",
        "UPDATE schema_migrations SET checksum='" + "0" * 64 + "'",
        "DELETE FROM schema_migrations",
        "UPDATE schema_migrations SET applied_at='2026-10-27T00:00:00+02:00'",
        "UPDATE state_meta SET store_id='zzzzzzzz-zzzz-4zzz-8zzz-zzzzzzzzzzzz'",
        "CREATE TABLE unexpected(value TEXT)",
    ],
)
def test_foreign_future_inconsistent_state_not_recreated(tmp_path, sql):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    modify(root, sql)
    before = (root / DB_NAME).read_bytes()
    with pytest.raises(YorungeError) as failure:
        api.initialize_state(state_dir=root)
    assert failure.value.code == "state_invalid"
    assert (root / DB_NAME).read_bytes() == before


@pytest.mark.parametrize(
    "content,expected", [(b"", "state_repair_required"), (b"unrelated-user-data", "state_invalid")]
)
def test_existing_empty_or_non_sqlite_file_is_not_adopted(tmp_path, content, expected):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    (root / DB_NAME).write_bytes(content)
    with pytest.raises(YorungeError) as failure:
        api.initialize_state(state_dir=root)
    assert failure.value.code == expected
    assert (root / DB_NAME).read_bytes() == content


def test_two_step_migration_failure_preserves_last_committed_version(tmp_path, monkeypatch):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    original = state_schema.MIGRATIONS
    second = Migration(1, 2, ("CREATE TABLE second_step(id INTEGER PRIMARY KEY) STRICT",))
    bad_third = Migration(
        2,
        3,
        (
            "CREATE TABLE third_step(id INTEGER PRIMARY KEY) STRICT",
            "INSERT INTO schema_migrations VALUES(2,'duplicate','bad')",
        ),
    )
    monkeypatch.setattr(state_schema, "MIGRATIONS", original + (second, bad_third))
    with pytest.raises(YorungeError):
        api.initialize_state(state_dir=root)
    assert query(root, "PRAGMA user_version") == [(2,)]
    assert query(root, "SELECT version FROM schema_migrations ORDER BY version") == [(1,), (2,)]
    assert query(root, "SELECT name FROM sqlite_schema WHERE name='third_step'") == []
    snapshots = list((root / "backups").iterdir())
    assert len(snapshots) == 2
    assert sorted(
        state.read_backup(p, Deadline(), state_schema.MIGRATIONS).source_version for p in snapshots
    ) == [1, 2]
    good_third = Migration(2, 3, ("CREATE TABLE third_step(id INTEGER PRIMARY KEY) STRICT",))
    monkeypatch.setattr(state_schema, "MIGRATIONS", original + (second, good_third))
    assert api.initialize_state(state_dir=root).data.store_schema_version == 3
    assert query(root, "SELECT version FROM schema_migrations ORDER BY version") == [
        (1,),
        (2,),
        (3,),
    ]


def test_backup_collision_does_not_overwrite_user_data_or_start_ddl(tmp_path, monkeypatch):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    identifier = "00000000-0000-4000-8000-000000000001"
    existing = root / "backups" / identifier
    existing.mkdir(parents=True, mode=0o700)
    (root / "backups").chmod(0o700)
    (existing / "sentinel").write_bytes(b"keep")
    monkeypatch.setattr(state, "uuid4", lambda: UUID(identifier))
    monkeypatch.setattr(
        state_schema,
        "MIGRATIONS",
        state_schema.MIGRATIONS
        + (Migration(1, 2, ("CREATE TABLE second_step(id INTEGER) STRICT",)),),
    )
    with pytest.raises(YorungeError) as failure:
        api.initialize_state(state_dir=root)
    assert failure.value.code == "state_write_failed"
    assert (existing / "sentinel").read_bytes() == b"keep"
    assert query(root, "PRAGMA user_version") == [(1,)]
    assert query(root, "SELECT name FROM sqlite_schema WHERE name='second_step'") == []


def test_backup_disk_full_does_not_change_live_schema(tmp_path, monkeypatch):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    original = state.write_new

    def failing(path, content):
        if path.name == "snapshot.sqlite3":
            raise OSError(errno.ENOSPC, "synthetic disk full")
        original(path, content)

    monkeypatch.setattr(state, "write_new", failing)
    monkeypatch.setattr(
        state_schema,
        "MIGRATIONS",
        state_schema.MIGRATIONS
        + (Migration(1, 2, ("CREATE TABLE second_step(id INTEGER) STRICT",)),),
    )
    with pytest.raises(YorungeError):
        api.initialize_state(state_dir=root)
    assert query(root, "PRAGMA user_version") == [(1,)]
    assert not list((root / "backups").glob("*/complete.json"))
    partial = next((root / "backups").iterdir())
    with pytest.raises(YorungeError):
        state.read_backup(partial, Deadline(), state_schema.MIGRATIONS)


def test_key_directory_parent_sync_failure_prevents_pointer_commit(tmp_path, monkeypatch):
    root = tmp_path / "state"
    original = local_files.sync_directory

    def failing(path):
        if path == root and (root / "keys").exists():
            raise OSError(errno.EIO, "synthetic directory sync failure")
        original(path)

    monkeypatch.setattr(local_files, "sync_directory", failing)
    with pytest.raises(YorungeError) as failure:
        api.initialize_state(state_dir=root)
    assert failure.value.code == "state_write_failed"
    assert not (root / DB_NAME).exists()
    monkeypatch.setattr(local_files, "sync_directory", original)
    with pytest.raises(YorungeError) as failure:
        api.initialize_state(state_dir=root)
    assert failure.value.code == "state_repair_required"


def test_bounded_file_and_sqlite_lock_wait(tmp_path):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    start = time.monotonic()
    with file_lock(root / "store.lock", Deadline(), exclusive=True, create=False):
        with pytest.raises(YorungeError) as failure:
            with open_store(root, timeout=0.05):
                pytest.fail("locked store unexpectedly opened")
    assert failure.value.code == "state_busy"
    assert time.monotonic() - start < 1.0
    with closing(sqlite3.connect(root / DB_NAME, isolation_level=None)) as writer:
        writer.execute("BEGIN IMMEDIATE")
        with pytest.raises(YorungeError) as failure:
            with open_store(root, timeout=0.05) as store:
                store.connection.execute("BEGIN IMMEDIATE")
        assert failure.value.code == "state_busy"
        writer.execute("ROLLBACK")


def test_two_migration_processes_apply_step_once(tmp_path):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    code = """from pathlib import Path
import sys
from yorunge import api
from yorunge.adapters import state_schema as s
s.MIGRATIONS += (s.Migration(1,2,('CREATE TABLE second_step(id INTEGER) STRICT',)),)
assert api.initialize_state(state_dir=Path(sys.argv[1])).data.store_schema_version == 2
"""
    processes = [subprocess.Popen([sys.executable, "-c", code, str(root)]) for _ in range(2)]
    for process in processes:
        assert process.wait(timeout=10) == 0
    assert query(root, "SELECT version FROM schema_migrations ORDER BY version") == [(1,), (2,)]


def test_backup_completion_and_hash_are_required(tmp_path):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    with file_lock(root / "store.lock", Deadline(), exclusive=True, create=False):
        saved = state.backup(root, root / DB_NAME, Deadline(), state_schema.MIGRATIONS)
    manifest = state.read_backup(saved, Deadline(), state_schema.MIGRATIONS)
    assert (
        manifest.snapshot_sha256
        == hashlib.sha256((saved / "snapshot.sqlite3").read_bytes()).hexdigest()
    )
    with (saved / "snapshot.sqlite3").open("ab") as output:
        output.write(b"corrupt")
    with pytest.raises(YorungeError) as failure:
        state.read_backup(saved, Deadline(), state_schema.MIGRATIONS)
    assert failure.value.code == "state_invalid"


def test_restore_intent_blocks_open_without_removal(tmp_path):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    marker = root / "restore-intent.json"
    marker.write_bytes(b"incomplete")
    with pytest.raises(YorungeError) as failure:
        api.initialize_state(state_dir=root)
    assert failure.value.code == "state_repair_required"
    assert marker.read_bytes() == b"incomplete"


def test_default_offline_commands_never_create_state(tmp_path, cli):
    for arguments in (
        ("--help",),
        ("--version",),
        ("context", "show"),
        ("capabilities", "--task", "llm.train"),
        ("plan", "prepare", "--task", "llm.train"),
    ):
        result = cli(*arguments, metadata=arguments[0].startswith("--"))
        assert result.returncode == 0
    assert not (tmp_path / ".local/state/yorunge").exists()


@pytest.mark.parametrize("path", ["not-a-path", Path("\x00")])
def test_invalid_api_state_path_is_controlled(path):
    with pytest.raises(YorungeError) as failure:
        api.initialize_state(state_dir=path)
    assert failure.value.code == "invalid_request"


@pytest.mark.parametrize("committed", [False, True])
def test_process_exit_and_native_hot_journal_recovery(tmp_path, committed):
    root = tmp_path / "state"
    original = api.initialize_state(state_dir=root)
    timestamp = query(root, "SELECT applied_at FROM schema_migrations")[0][0]
    code = """import os, sys
from pathlib import Path
from yorunge.adapters.state import open_store
with open_store(Path(sys.argv[1])) as store:
    c = store.connection
    c.execute('PRAGMA cache_size=1')
    c.execute('BEGIN IMMEDIATE')
    c.execute('CREATE TABLE transient_probe(payload BLOB) STRICT')
    c.executemany('INSERT INTO transient_probe VALUES(?)', [(b'x'*1024,)]*500)
    c.execute("UPDATE schema_migrations SET applied_at='2026-10-27T00:00:00+00:00'")
    if sys.argv[2] == 'commit':
        c.execute('DROP TABLE transient_probe')
        c.execute('COMMIT')
    os._exit(23)
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(root), "commit" if committed else "exit"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 23, result.stderr
    if not committed:
        journal = root / (DB_NAME + "-journal")
        assert journal.stat().st_size > 512
        assert journal.read_bytes()[:8] == bytes.fromhex("d9d505f920a163d7")
    assert api.initialize_state(state_dir=root) == original
    expected = "2026-10-27T00:00:00+00:00" if committed else timestamp
    assert query(root, "SELECT applied_at FROM schema_migrations") == [(expected,)]
    assert query(root, "SELECT name FROM sqlite_schema WHERE name='transient_probe'") == []


def test_relational_violation_fails_full_state_validation(tmp_path, monkeypatch):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    second = Migration(
        1,
        2,
        (
            "CREATE TABLE parents(id INTEGER PRIMARY KEY) STRICT",
            "CREATE TABLE children(id INTEGER PRIMARY KEY,"
            "parent_id INTEGER REFERENCES parents(id)) STRICT",
        ),
    )
    monkeypatch.setattr(state_schema, "MIGRATIONS", state_schema.MIGRATIONS + (second,))
    api.initialize_state(state_dir=root)
    modify(root, "INSERT INTO children VALUES(1,42)")
    assert query(root, "PRAGMA integrity_check") == [("ok",)]
    with pytest.raises(YorungeError) as failure:
        api.initialize_state(state_dir=root)
    assert failure.value.code == "state_invalid"


def test_key_check_matches_independent_accepted_byte_vector():
    vectors = json.loads(
        (Path(__file__).parents[2] / "docs/research/p01-2-review-probe.json").read_text()
    )["binding_v1_byte_vectors"]
    fields = json.loads(vectors["key_check_json"])
    actual = state.key_check(
        bytes.fromhex(vectors["synthetic_key_hex"]),
        fields["store_id"],
        fields["identity_epoch"],
        fields["active_key_id"],
    )
    assert actual.hex() == vectors["key_check_tag_hex"]


@pytest.mark.parametrize("kind", ["bool-format", "duplicate", "depth", "missing"])
def test_invalid_backup_metadata_does_not_modify_snapshot(tmp_path, kind):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    with file_lock(root / "store.lock", Deadline(), exclusive=True, create=False):
        saved = state.backup(root, root / DB_NAME, Deadline(), state_schema.MIGRATIONS)
    record = saved / "complete.json"
    original = record.read_text()
    if kind == "bool-format":
        data = json.loads(original)
        data["format_version"] = True
        record.write_text(json.dumps(data))
    elif kind == "duplicate":
        record.write_text(
            original.replace('"format_version":1', '"format_version":1,"format_version":1')
        )
    elif kind == "depth":
        record.write_text("[" * 1200 + "0" + "]" * 1200)
    else:
        record.unlink()
    snapshot = (saved / "snapshot.sqlite3").read_bytes()
    with pytest.raises(YorungeError) as failure:
        state.read_backup(saved, Deadline(), state_schema.MIGRATIONS)
    assert failure.value.code == "state_invalid"
    assert (saved / "snapshot.sqlite3").read_bytes() == snapshot
