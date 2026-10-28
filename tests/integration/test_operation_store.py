"""Operation persistence through real SQLite, restart and integrity boundaries."""

import json
import sqlite3
from uuid import uuid4

import pytest

from yorunge import api
from yorunge.adapters import state_schema
from yorunge.adapters.operation_store import read_job, read_operation, write_record
from yorunge.adapters.state import DB_NAME, open_store
from yorunge.domain.capabilities import canonical
from yorunge.domain.errors import YorungeError


def test_operation_restart_snapshot_and_plan_restrict(admitted_operation):
    root, plan, record, attempt, _ = admitted_operation
    with open_store(root) as store:
        assert store.verify().store_schema_version == 6
        result = read_job(store.connection, record.summary.operation_id)
        assert result.plan == plan
        assert result.operation == record.summary
        assert result.attempts == (attempt,)
        assert result.outcome is None
    with pytest.raises(YorungeError) as failure:
        api.forget_execution_plan(plan.plan_id, plan.digest, state_dir=root)
    assert failure.value.code == "plan_in_use"
    assert api.show_execution_plan(plan.plan_id, state_dir=root).data.plan == plan
    with sqlite3.connect(root / DB_NAME) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM execution_plans WHERE plan_id=?", (plan.plan_id,))


@pytest.mark.parametrize("target", ["index", "admission", "attempt", "event", "outcome", "latch"])
def test_full_and_warm_reads_reject_corrupt_operation(admitted_operation, target):
    root, _, record, _, _ = admitted_operation
    identifier = record.summary.operation_id
    with open_store(root) as store:
        connection = store.connection
        if target == "index":
            connection.execute("UPDATE operations SET revision=revision+1")
        elif target == "admission":
            raw = json.loads(connection.execute("SELECT payload FROM operations").fetchone()[0])
            raw["admission"]["approval"]["binding_digest"] = "a" * 64
            connection.execute("UPDATE operations SET payload=?", (json.dumps(raw),))
        elif target == "attempt":
            connection.execute("UPDATE operation_attempts SET number=2")
        elif target == "event":
            connection.execute("DELETE FROM operation_events")
        elif target == "outcome":
            connection.execute("INSERT INTO operation_outcomes VALUES(?,?)", (identifier, "{}"))
        else:
            # Projection/body must agree even before SQLite's deferred FK commit check.
            connection.execute("PRAGMA foreign_keys=OFF")
            connection.execute("UPDATE operations SET dispatch_attempt_id=?", (str(uuid4()),))
        with pytest.raises(YorungeError) as warm:
            read_job(connection, identifier)
        assert warm.value.code == "state_invalid"
        with pytest.raises(YorungeError) as full:
            store.verify()
        assert full.value.code == "state_invalid"


def test_transaction_rollback_preserves_operation_and_immutable_admission(admitted_operation):
    root, _, record, _, _ = admitted_operation
    with open_store(root) as store:
        connection = store.connection
        connection.execute("BEGIN IMMEDIATE")
        changed = record.model_copy(
            update={"summary": record.summary.model_copy(update={"revision": 2})}
        )
        write_record(connection, changed, expected_revision=1)
        connection.execute("ROLLBACK")
        assert read_operation(connection, record.summary.operation_id) == record
        connection.execute("BEGIN IMMEDIATE")
        body = json.loads(canonical(changed.model_dump(mode="json")))
        body["admission"]["correlation"] = str(uuid4())
        from yorunge.domain.operations import OperationRecord

        forged = OperationRecord.model_validate_json(json.dumps(body))
        with pytest.raises(YorungeError) as failure:
            write_record(connection, forged, expected_revision=1)
        assert failure.value.code == "operation_conflict"
        connection.execute("ROLLBACK")
        assert store.verify().store_schema_version == 6


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("action", ["restore-preview", "restore", "recover-preview", "recover"])
def test_operation_runtime_restore_gate_precedes_source_and_target_io(tmp_path, existing, action):
    root = tmp_path / "state"
    if existing:
        api.initialize_state(state_dir=root)
    backup = tmp_path / "missing-backup"
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(YorungeError) as failure:
        if action == "restore-preview":
            api.preview_state_restore(backup, state_dir=root)
        elif action == "restore":
            api.restore_state(backup, "a" * 64, state_dir=root)
        elif action == "recover-preview":
            api.preview_state_recovery(state_dir=root)
        else:
            api.recover_state("a" * 64, state_dir=root)
    assert failure.value.code == "state_restore_unsupported"
    assert {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


def test_schema6_is_sql_only_v2_and_schema5_identity_is_frozen():
    migration = state_schema.MIGRATIONS[5]
    assert migration.from_version == 5
    assert migration.to_version == 6
    assert migration.data_transform is None
    assert migration.checksum == "62ac619e29aaaf2d9c838bde2a0ee795e7496f67107eaf69e26daaf9d4b4b90a"
    assert set(migration.manifest()) == {
        "manifest_version",
        "from_version",
        "to_version",
        "statements",
    }
    assert (
        state_schema.MIGRATIONS[4].checksum
        == "2f627c2b5ae872ca8f36d947e8ecad6e86e73d242dd1e712eb92abf0932b3b33"
    )


def test_schema6_ddl_failure_rolls_back_tables_manifest_and_version(tmp_path, monkeypatch):
    from yorunge.adapters import state

    root = tmp_path / "state"
    with monkeypatch.context() as historical:
        historical.setattr(state_schema, "MIGRATIONS", state_schema.MIGRATIONS[:5])
        api.initialize_state(state_dir=root)
    original = state.apply_migration

    def interrupted(connection, step, deadline, transform=None):
        if step.to_version == 6:
            connection.execute(step.statements[0])
            raise YorungeError("state_write_failed")
        return original(connection, step, deadline, transform)

    with monkeypatch.context() as cut:
        cut.setattr(state, "apply_migration", interrupted)
        with pytest.raises(YorungeError) as failure:
            api.initialize_state(state_dir=root)
        assert failure.value.code == "state_write_failed"
    with sqlite3.connect(root / DB_NAME) as conn:
        assert conn.execute("PRAGMA user_version").fetchone() == (5,)
        assert conn.execute("SELECT max(version) FROM schema_migrations").fetchone() == (5,)
        assert (
            conn.execute("SELECT name FROM sqlite_schema WHERE name='operations'").fetchone()
            is None
        )
    assert api.initialize_state(state_dir=root).data.store_schema_version == 6
