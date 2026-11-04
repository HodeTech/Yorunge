"""SQL-only 6→7 preserves real populated execution/operation history bytes."""

from tests.fixtures.operation_backend import ProcessBackend, ReadObserver
from yorunge import api
from yorunge.adapters import state_schema
from yorunge.adapters.state import open_store

TABLES = (
    "schema_migrations",
    "execution_plans",
    "execution_approvals",
    "operations",
    "operation_attempts",
    "operation_events",
    "operation_outcomes",
)


def rows(connection):
    # All columns, including the original canonical payload bytes and FK IDs.
    return {
        table: connection.execute(f"SELECT * FROM {table} ORDER BY 1,2").fetchall()
        for table in TABLES
    }


def test_populated_schema6_to7_preserves_payloads_identity_and_constraints(
    tmp_path, monkeypatch, execution_fixture, execution_clock
):
    root = tmp_path / "state"
    backend = ProcessBackend(tmp_path / "effects")
    with monkeypatch.context() as historical:
        historical.setattr(state_schema, "MIGRATIONS", state_schema.MIGRATIONS[:6])
        plan = api.prepare_execution_plan(task="llm.train", state_dir=root).data.plan
        assert api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=root).data.effective
        with api._operation_session(plan.plan_id, backend, state_dir=root) as coordinator:
            claim = coordinator.admit(plan.plan_id)
            job = coordinator.dispatch(claim.job.operation.operation_id, claim.ownership)
            assert job.operation.status == "submitted"
        observer = ReadObserver(execution_clock)
        with api._operation_session(
            plan.plan_id, backend, observer=observer, state_dir=root
        ) as coordinator:
            job = coordinator.reconcile(job.operation.operation_id, claim.ownership)
            assert job.operation.status == "succeeded"
            assert job.outcome is not None
        with open_store(root) as store:
            before = rows(store.connection)
            identity = store.info
            assert all(before.values())
            assert store.verify().store_schema_version == 6
    with open_store(root) as store:
        assert store.verify().store_schema_version == 7
        after = rows(store.connection)
        after["schema_migrations"] = [row for row in after["schema_migrations"] if row[0] <= 6]
        assert after == before
        assert store.info.store_id == identity.store_id
        assert store.info.identity_epoch == identity.identity_epoch
        assert store.connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert store.connection.execute("SELECT count(*) FROM upload_operations").fetchone() == (0,)
    assert backend.calls == len(backend.effects()) == 1
