import hashlib
import json
import os
import py_compile
import sqlite3
import sys
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest

from yorunge.adapters import data_migrations as dm
from yorunge.adapters import state, state_schema
from yorunge.adapters.capability_cache import StateCache, decode_entry
from yorunge.adapters.expiry_fences import next_expiry
from yorunge.adapters.local_files import Deadline
from yorunge.domain.errors import YorungeError

VECTORS = json.loads(
    (Path(__file__).parents[2] / "docs/research/p01-3-expiry-migration-vectors.json").read_text()
)["vectors"]
EXPECTED = sorted(tuple(row) for v in VECTORS for row in v["expected_expiries"])


class Clock:
    def now(self):
        return datetime(2026, 10, 28, tzinfo=UTC)

    def monotonic(self):
        return 0.0


def schema4(root, monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(state_schema, "MIGRATIONS", state_schema.MIGRATIONS[:4])
        with state.open_store(root) as store:
            old = state.metadata(store.connection)
            key = state.load_key(root, old)
            scope = json.loads(VECTORS[0]["source_row"][1])["scope"]
            store.connection.execute(
                "UPDATE state_meta SET store_id=?,identity_epoch=?,key_check=?",
                (
                    scope["store_id"],
                    scope["identity_epoch"],
                    state.key_check(
                        key, scope["store_id"], scope["identity_epoch"], old.active_key_id
                    ),
                ),
            )
            store.connection.execute(
                "UPDATE cache_clock SET identity_epoch=?,high_watermark=?,mutation_revision=6",
                (scope["identity_epoch"], "2026-10-28T00:00:00.000000Z"),
            )
            store.connection.executemany(
                "INSERT INTO capability_cache VALUES(?,?,?,?,?,?,?,?)",
                [v["source_row"] for v in VECTORS],
            )
            store.verify()


def unchanged_failure(root, code):
    before = (root / state.DB_NAME).read_bytes()
    with pytest.raises(YorungeError) as failure:
        with state.open_store(root):
            pass
    assert failure.value.code == code
    assert (root / state.DB_NAME).read_bytes() == before
    with closing(sqlite3.connect(root / state.DB_NAME)) as conn:
        assert conn.execute("PRAGMA user_version").fetchone() == (4,)
        assert conn.execute("SELECT max(version) FROM schema_migrations").fetchone() == (4,)
        assert (
            conn.execute("SELECT 1 FROM sqlite_schema WHERE name='capability_expiries'").fetchone()
            is None
        )


def assert_literal_rows(root):
    with state.open_store(root) as store:
        assert (
            store.connection.execute(
                "SELECT cache_key,expires_at FROM capability_expiries ORDER BY cache_key,expires_at"
            ).fetchall()
            == EXPECTED
        )
        assert store.connection.execute(
            "SELECT payload FROM capability_cache ORDER BY cache_key"
        ).fetchall() == [
            (v["source_row"][4],) for v in sorted(VECTORS, key=lambda v: v["source_row"][0])
        ]
        cache = StateCache(store, Clock())
        stamp = cache.stamp()
        for vector in VECTORS:
            record, _ = decode_entry(tuple(vector["source_row"]))
            result = cache.query(record.key, stamp)
            assert result.hit is True
            assert result.freshness == "fresh"
            assert result.effective_support == record.support
        for observed, expected in [
            ("00:00:00", "00:00:30"),
            ("00:00:30", "00:01:00"),
            ("00:01:00", "00:01:30"),
            ("00:04:00", "00:04:30"),
            ("00:04:30", "00:05:00"),
        ]:
            assert next_expiry(store.connection, f"2026-10-28T{observed}.000000Z") == (
                datetime.fromisoformat(f"2026-10-28T{expected}+00:00")
            )
        assert next_expiry(store.connection, "2026-10-28T00:05:00.000000Z") is None
        store.verify()


def test_literal_previous_schema_vectors_survive_migration_warm_read_and_restart(
    tmp_path, monkeypatch
):
    root = tmp_path / "state"
    schema4(root, monkeypatch)
    assert_literal_rows(root)
    assert_literal_rows(root)


def test_stale_timestamp_pyc_and_preloaded_module_cannot_select_handler(tmp_path, monkeypatch):
    root = tmp_path / "state"
    schema4(root, monkeypatch)
    current = dm.SOURCE.read_bytes()
    old = current.replace(b'raw.get("conflict_until")', b'raw.get("conflict_untim")')
    assert len(current) == len(old)
    assert current != old
    path = tmp_path / "handler.py"
    path.write_bytes(old)
    os.utime(path, (1700000000, 1700000000))
    py_compile.compile(
        str(path), doraise=True, invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP
    )
    path.write_bytes(current)
    os.utime(path, (1700000000, 1700000000))
    fake = ModuleType("yorunge.adapters.migration_capability_expiries_v1")

    def fail(_connection):
        raise AssertionError("preloaded handler must never execute")

    fake.apply = fail
    monkeypatch.setitem(sys.modules, fake.__name__, fake)
    monkeypatch.setattr(dm, "SOURCE", path)
    assert_literal_rows(root)


def test_source_change_after_verification_uses_same_buffer_and_current_open_skips_source(
    tmp_path, monkeypatch
):
    root = tmp_path / "state"
    schema4(root, monkeypatch)
    path = tmp_path / "handler.py"
    path.write_bytes(dm.SOURCE.read_bytes())
    monkeypatch.setattr(dm, "SOURCE", path)
    original = dm._check_source
    calls = []

    def change_after_read(buffer):
        original(buffer)
        calls.append(hashlib.sha256(buffer).hexdigest())
        path.write_bytes(b"not the verified source")

    monkeypatch.setattr(dm, "_check_source", change_after_read)
    assert_literal_rows(root)
    path.unlink()
    assert_literal_rows(root)
    assert calls == [state_schema.MIGRATIONS[-1].data_transform.code_sha256]


@pytest.mark.parametrize(
    "kind,code",
    [
        ("missing", "state_invalid"),
        ("directory", "state_write_failed"),
        ("different", "state_invalid"),
        ("oversized", "state_invalid"),
    ],
)
def test_source_failure_is_controlled_before_snapshot_or_ddl(tmp_path, monkeypatch, kind, code):
    root = tmp_path / "state"
    schema4(root, monkeypatch)
    path = tmp_path / "handler.py"
    if kind == "directory":
        path.mkdir()
    elif kind == "different":
        path.write_bytes(b"def apply(connection):\n    return None\n")
    elif kind == "oversized":
        path.write_bytes(b" " * (dm.MAX_SOURCE_BYTES + 1))
    backups = set((root / "backups").iterdir())
    monkeypatch.setattr(dm, "SOURCE", path)
    unchanged_failure(root, code)
    assert set((root / "backups").iterdir()) == backups


@pytest.mark.parametrize(
    "source",
    [
        b'import os\ndef apply(connection):\n    os.environ.get("X")\n',
        b"from datetime import datetime\ndef apply(connection):\n    datetime.now()\n",
        b'import sqlite3\ndef apply(connection):\n    sqlite3.connect(":memory:")\n',
        b'def apply(connection):\n    connection.execute("COMMIT")\n',
        b'def apply(connection):\n    connection.execute("ROLLBACK")\n',
        b'def apply(connection):\n    connection.execute("PRAGMA user_version=99")\n',
        b'def apply(connection):\n    open("file")\n',
        b"STATE=[]\ndef apply(connection):\n    return None\n",
        b"def apply(connection):\n    apply(connection)\n",
        b"def apply(connection):\n    while True:\n        return None\n",
        b"from . import expiry_fences\ndef apply(connection):\n    return None\n",
        b"def apply(connection):\r\n    return None\r\n",
        b"def apply(connection):\n    return None\n\xff",
    ],
)
def test_forbidden_handler_constructs_rejected_even_with_matching_hash(
    tmp_path, monkeypatch, source
):
    root = tmp_path / "state"
    schema4(root, monkeypatch)
    path = tmp_path / "handler.py"
    path.write_bytes(source)
    monkeypatch.setattr(dm, "SOURCE", path)
    step = state_schema.MIGRATIONS[-1]
    altered = replace(
        step,
        data_transform=replace(step.data_transform, code_sha256=hashlib.sha256(source).hexdigest()),
    )
    monkeypatch.setattr(state_schema, "MIGRATIONS", (*state_schema.MIGRATIONS[:4], altered))
    unchanged_failure(root, "state_invalid")


@pytest.mark.parametrize(
    "primary,code",
    [
        (sqlite3.SQLITE_FULL, "state_write_failed"),
        (sqlite3.SQLITE_IOERR | (3 << 8), "state_write_failed"),
        (sqlite3.SQLITE_INTERRUPT, "state_busy"),
    ],
)
def test_backfill_sql_failure_rolls_back_data_ddl_history_and_version(
    tmp_path, monkeypatch, primary, code
):
    root = tmp_path / "state"
    schema4(root, monkeypatch)
    original = dm.MigrationConnection.insert_expiry

    def fail_after_insert(self, key, date):
        original(self, key, date)
        error = sqlite3.OperationalError("private injected failure")
        error.sqlite_errorcode = primary
        raise error

    monkeypatch.setattr(dm.MigrationConnection, "insert_expiry", fail_after_insert)
    unchanged_failure(root, code)


def test_old_prototype_schema5_checksum_is_rejected_without_relabeling(tmp_path, monkeypatch):
    root = tmp_path / "state"
    schema4(root, monkeypatch)
    assert_literal_rows(root)
    manifest = state_schema.MIGRATIONS[-1].manifest()
    del manifest["manifest_version"]
    del manifest["data_transform"]
    legacy = hashlib.sha256(
        json.dumps(
            manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode()
    ).hexdigest()
    with closing(sqlite3.connect(root / state.DB_NAME, isolation_level=None)) as conn:
        conn.execute("UPDATE schema_migrations SET checksum=? WHERE version=5", (legacy,))
    before = (root / state.DB_NAME).read_bytes()
    with pytest.raises(YorungeError) as failure:
        with state.open_store(root):
            pass
    assert failure.value.code == "state_invalid"
    assert (root / state.DB_NAME).read_bytes() == before


@pytest.mark.parametrize(
    "statement",
    [
        "COMMIT",
        "ROLLBACK",
        "SAVEPOINT bad",
        "CREATE TABLE bad(value TEXT)",
        "PRAGMA user_version=99",
        "ATTACH ':memory:' AS bad",
        "UPDATE capability_cache SET mutation_revision=99",
        "DELETE FROM capability_cache",
        "SELECT random()",
        "SELECT * FROM state_meta",
    ],
)
def test_authorizer_denies_transaction_schema_and_source_mutation(tmp_path, monkeypatch, statement):
    root = tmp_path / "state"
    schema4(root, monkeypatch)
    original = dm.MigrationConnection.insert_expiry

    def violate(self, key, date):
        original(self, key, date)
        self._connection.execute(statement)

    monkeypatch.setattr(dm.MigrationConnection, "insert_expiry", violate)
    unchanged_failure(root, "state_invalid")


def test_deadline_failure_removes_authorizer_and_rolls_back(tmp_path, monkeypatch):
    root = tmp_path / "state"
    schema4(root, monkeypatch)
    original = dm.MigrationConnection.insert_expiry

    def expire(self, key, date):
        original(self, key, date)
        self._deadline.end = 0
        self._deadline.remaining()

    monkeypatch.setattr(dm.MigrationConnection, "insert_expiry", expire)
    unchanged_failure(root, "state_busy")


@pytest.mark.parametrize("kind", ["duplicate", "nonfinite", "oversized", "nine-proofs"])
def test_current_canonical_decoder_rejects_invalid_source_before_backfill(
    tmp_path, monkeypatch, kind
):
    root = tmp_path / "state"
    schema4(root, monkeypatch)
    row = VECTORS[-1]["source_row"]
    raw = json.loads(row[4])
    if kind == "duplicate":
        payload = row[4].replace('"schema_version":2', '"schema_version":2,"schema_version":2', 1)
    else:
        if kind == "nonfinite":
            raw["message"] = float("nan")
        elif kind == "oversized":
            raw["message"] = "ş" * 17000
        else:
            raw["evidence"].append(raw["evidence"][0])
        payload = json.dumps(raw, ensure_ascii=False)
    with closing(sqlite3.connect(root / state.DB_NAME, isolation_level=None)) as conn:
        conn.execute("UPDATE capability_cache SET payload=? WHERE cache_key=?", (payload, row[0]))
    unchanged_failure(root, "state_invalid")


def test_no_environment_or_wall_clock_input_changes_derived_set(tmp_path, monkeypatch):
    for name, timezone, when in [
        ("first", "UTC", "2026-10-28T12:00:00.000000+00:00"),
        ("second", "Pacific/Auckland", "2027-01-01T00:00:00.000000+00:00"),
    ]:
        root = tmp_path / name
        schema4(root, monkeypatch)
        monkeypatch.setenv("TZ", timezone)
        monkeypatch.setenv("YORUNGE_MIGRATION_PROBE", name)
        monkeypatch.setattr(state, "utc_now", lambda when=when: when)
        assert_literal_rows(root)


def test_verified_transform_requires_caller_owned_transaction(tmp_path, monkeypatch):
    root = tmp_path / "state"
    schema4(root, monkeypatch)
    prepared = dm.prepare(state_schema.MIGRATIONS[-1], Deadline())
    with closing(sqlite3.connect(root / state.DB_NAME, isolation_level=None)) as conn:
        with pytest.raises(YorungeError) as failure:
            prepared.run(conn, Deadline())
        assert failure.value.code == "state_invalid"
        assert conn.in_transaction is False


@pytest.mark.parametrize("point", ["validation", "commit"])
def test_post_backfill_failure_cannot_leave_half_schema(tmp_path, monkeypatch, point):
    root = tmp_path / "state"
    schema4(root, monkeypatch)
    if point == "validation":
        original_validate = state.validate

        def fail_validation(connection, migrations, *, full):
            if connection.execute("PRAGMA user_version").fetchone()[0] == 5:
                raise YorungeError("state_invalid")
            return original_validate(connection, migrations, full=full)

        monkeypatch.setattr(state, "validate", fail_validation)
        code = "state_invalid"
    else:
        original_connect = sqlite3.connect

        class FailCommit(sqlite3.Connection):
            def execute(self, sql, parameters=()):
                if sql == "COMMIT" and super().execute("PRAGMA user_version").fetchone() == (5,):
                    error = sqlite3.OperationalError("injected pre-commit I/O")
                    error.sqlite_errorcode = sqlite3.SQLITE_IOERR
                    raise error
                return super().execute(sql, parameters)

        def connect(*args, **kwargs):
            return original_connect(*args, **kwargs, factory=FailCommit)

        monkeypatch.setattr(sqlite3, "connect", connect)
        code = "state_write_failed"
    unchanged_failure(root, code)
