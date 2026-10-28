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


def raw_record(connection, record):
    from yorunge.adapters.operation_store import OPERATION_COLUMNS, operation_row

    columns = OPERATION_COLUMNS.split(",")
    row = operation_row(record)
    connection.execute(
        "UPDATE operations SET "
        + ",".join(name + "=?" for name in columns[1:])
        + " WHERE operation_id=?",
        (*row[1:], row[0]),
    )


def raw_attempt(connection, attempt):
    connection.execute(
        "UPDATE operation_attempts SET status=?,payload=? WHERE attempt_id=?",
        (
            attempt.status,
            canonical(attempt.model_dump(mode="json")).decode("ascii"),
            attempt.attempt_id,
        ),
    )


def raw_event(connection, identifier, event):
    connection.execute(
        "INSERT INTO operation_events VALUES(?,?,?,?)",
        (
            identifier,
            event.sequence,
            event.attempt_id,
            canonical(event.model_dump(mode="json")).decode("ascii"),
        ),
    )


def terminal_fixture(connection, record, attempt, event, *, failed=False):
    from yorunge.adapters.operation_store import append_event, write_attempt, write_outcome
    from yorunge.domain.operations import OperationOutcome

    for sequence, status in ((2, "submitted"), (3, "failed" if failed else "succeeded")):
        reason = "provider_failed" if status == "failed" else None
        terminal = sequence == 3
        changed = record.model_copy(
            update={
                "summary": record.summary.model_copy(
                    update={"status": status, "execution_status": status, "revision": sequence}
                ),
                "dispatch_attempt_id": attempt.attempt_id,
                "event_count": sequence,
                "lease": None if terminal else record.lease,
            }
        )
        attempt = attempt.model_copy(
            update={
                "status": status,
                "provider_run_id": "original-run-id",
                "provider_exit_code": 1 if failed and terminal else 0 if terminal else None,
                "reason_code": reason,
            }
        )
        event = event.model_copy(
            update={
                "sequence": sequence,
                "revision": sequence,
                "status": status,
                "execution_status": status,
                "reason_code": reason,
            }
        )
        write_record(connection, changed, expected_revision=record.summary.revision)
        write_attempt(connection, record.summary.operation_id, attempt)
        append_event(connection, record.summary.operation_id, event)
        if terminal:
            write_outcome(
                connection,
                record.summary.operation_id,
                OperationOutcome(
                    recorded_at=record.summary.updated_at,
                    execution_status=status,
                    delivery_status="not_required",
                    provider_exit_code=attempt.provider_exit_code,
                    reason_code=reason,
                ),
            )
        record = changed
    read_job(connection, record.summary.operation_id)
    return record, attempt, event


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


@pytest.mark.parametrize("entry", ["warm", "full"])
@pytest.mark.parametrize(
    "damage",
    [
        "future-approval",
        "attempt-time",
        "outcome-time",
        "terminal-reopen",
        "skipped-submitted",
        "cleared-latch",
        "postdispatch-reason",
        "authority-target",
    ],
)
def test_reviewed_integrity_regressions_fail_closed(admitted_operation, damage, entry):
    root, _, record, attempt, event = admitted_operation
    identifier = record.summary.operation_id
    with open_store(root) as store:
        connection = store.connection
        connection.execute("BEGIN IMMEDIATE")
        if damage in ("outcome-time", "terminal-reopen", "postdispatch-reason"):
            record, attempt, event = terminal_fixture(
                connection, record, attempt, event, failed=damage == "postdispatch-reason"
            )
        if damage == "future-approval":
            from datetime import timedelta

            from yorunge.domain.capabilities import instant, timestamp

            approved = record.admission.approval.model_copy(
                update={
                    "approved_at": timestamp(
                        instant(record.summary.created_at) + timedelta(seconds=20)
                    )
                }
            )
            record = record.model_copy(
                update={"admission": record.admission.model_copy(update={"approval": approved})}
            )
            raw_record(connection, record)
        elif damage == "attempt-time":
            raw_attempt(
                connection,
                attempt.model_copy(
                    update={
                        "created_at": "2099-01-01T00:00:00.000000Z",
                        "updated_at": "2000-01-01T00:00:00.000000Z",
                    }
                ),
            )
        elif damage == "outcome-time":
            body = json.loads(
                connection.execute("SELECT payload FROM operation_outcomes").fetchone()[0]
            )
            body["recorded_at"] = "2099-01-01T00:00:00.000000Z"
            connection.execute("UPDATE operation_outcomes SET payload=?", (json.dumps(body),))
        elif damage == "terminal-reopen":
            raw_record(
                connection,
                record.model_copy(
                    update={
                        "summary": record.summary.model_copy(
                            update={"status": "unknown", "execution_status": "unknown"}
                        ),
                        "recovery_reason": "identity_reset",
                    }
                ),
            )
            raw_attempt(
                connection,
                attempt.model_copy(update={"status": "unknown", "reason_code": "identity_reset"}),
            )
            connection.execute("DELETE FROM operation_outcomes")
        elif damage == "skipped-submitted":
            raw_record(
                connection,
                record.model_copy(
                    update={
                        "summary": record.summary.model_copy(
                            update={
                                "status": "running",
                                "execution_status": "running",
                                "revision": 2,
                            }
                        ),
                        "dispatch_attempt_id": attempt.attempt_id,
                        "event_count": 2,
                    }
                ),
            )
            raw_attempt(connection, attempt.model_copy(update={"status": "running"}))
            raw_event(
                connection,
                identifier,
                event.model_copy(
                    update={
                        "sequence": 2,
                        "revision": 2,
                        "status": "running",
                        "execution_status": "running",
                    }
                ),
            )
        elif damage == "cleared-latch":
            for sequence, status in ((2, "submitted"), (3, "admitted")):
                raw_event(
                    connection,
                    identifier,
                    event.model_copy(
                        update={
                            "sequence": sequence,
                            "revision": sequence,
                            "status": status,
                            "execution_status": "not_started"
                            if status == "admitted"
                            else "submitted",
                        }
                    ),
                )
            raw_record(
                connection,
                record.model_copy(
                    update={
                        "event_count": 3,
                        "summary": record.summary.model_copy(update={"revision": 3}),
                    }
                ),
            )
        elif damage == "postdispatch-reason":
            raw_attempt(connection, attempt.model_copy(update={"reason_code": "approval_expired"}))
            payload = canonical(
                event.model_copy(update={"reason_code": "approval_expired"}).model_dump(mode="json")
            ).decode("ascii")
            connection.execute("UPDATE operation_events SET payload=? WHERE sequence=3", (payload,))
            body = json.loads(
                connection.execute("SELECT payload FROM operation_outcomes").fetchone()[0]
            )
            body["reason_code"] = "approval_expired"
            connection.execute("UPDATE operation_outcomes SET payload=?", (json.dumps(body),))
        else:
            body = record.model_dump(mode="json")
            body["admission"]["authorities"][0].update(
                service_id="evren-platform",
                service_origin="http://example.test",
                api_base_path="/",
                credential_id=str(uuid4()),
                credential_revision=1,
            )
            connection.execute("UPDATE operations SET payload=?", (json.dumps(body),))
        connection.execute("COMMIT")
        with pytest.raises(YorungeError) as failure:
            if entry == "warm":
                read_job(connection, identifier)
            else:
                store.verify()
        assert failure.value.code == "state_invalid"


def test_terminal_attempt_is_immutable_at_write_boundary(admitted_operation):
    from yorunge.adapters.operation_store import write_attempt

    root, _, record, attempt, event = admitted_operation
    with open_store(root) as store:
        connection = store.connection
        connection.execute("BEGIN IMMEDIATE")
        record, attempt, _ = terminal_fixture(connection, record, attempt, event)
        connection.execute("COMMIT")
        connection.execute("BEGIN IMMEDIATE")
        changed = attempt.model_copy(
            update={
                "provider_run_id": "different-run-id",
                "created_at": "2000-01-01T00:00:00.000000Z",
            }
        )
        with pytest.raises(YorungeError) as failure:
            write_attempt(connection, record.summary.operation_id, changed)
        assert failure.value.code == "operation_conflict"
        connection.execute("ROLLBACK")
        assert read_job(connection, record.summary.operation_id).attempts[-1] == attempt


def test_forget_reports_corrupt_operation_as_invalid_state(admitted_operation):
    root, plan, _, _, _ = admitted_operation
    with open_store(root) as store:
        store.connection.execute("UPDATE operations SET payload='{}'")
    with pytest.raises(YorungeError) as failure:
        api.forget_execution_plan(plan.plan_id, plan.digest, state_dir=root)
    assert failure.value.code == "state_invalid"
