import hashlib
import tracemalloc
from dataclasses import dataclass
from uuid import uuid4

import pytest

from yorunge import api
from yorunge.adapters import data_migrations, state_schema
from yorunge.adapters.state import open_store
from yorunge.adapters.validation_memo import ACTIVE, MAX_ENTRIES, validated, validation_session
from yorunge.domain.capabilities import canonical
from yorunge.domain.errors import YorungeError
from yorunge.domain.execution import ExecutionPlan


def rejected(store):
    with pytest.raises(YorungeError) as failure:
        store.verify()
    assert failure.value.code == "state_invalid"


@pytest.mark.parametrize(
    "column,value",
    [
        ("payload", "{}"),
        ("key_json", "{}"),
        ("projection_key", "{}"),
        ("group_key", "wrong"),
        ("mutation_revision", 99999),
        ("checked_at", "2020-01-01T00:00:00.000000Z"),
        ("pinned_until", "2020-01-01T00:00:00.000000Z"),
    ],
)
def test_every_changed_cache_column_is_revalidated(tmp_path, column, value):
    root = tmp_path / "state"
    api.query_capabilities(task="llm.train", state_dir=root, refresh=True)
    with open_store(root) as store, validation_session():
        store.verify()
        store.connection.execute(f"UPDATE capability_cache SET {column}=?", (value,))
        rejected(store)


@pytest.mark.parametrize(
    "change", ["store", "epoch", "clock-revision", "index-missing", "index-extra"]
)
def test_metadata_clock_and_derived_index_stay_live_for_unchanged_cached_payload(tmp_path, change):
    root = tmp_path / "state"
    api.query_capabilities(task="llm.train", state_dir=root, refresh=True)
    with open_store(root) as store, validation_session():
        store.verify()
        conn = store.connection
        if change == "store":
            conn.execute("UPDATE state_meta SET store_id=?", (str(uuid4()),))
        elif change == "epoch":
            epoch = str(uuid4())
            conn.execute("UPDATE state_meta SET identity_epoch=?", (epoch,))
            conn.execute("UPDATE cache_clock SET identity_epoch=?", (epoch,))
        elif change == "clock-revision":
            conn.execute("UPDATE cache_clock SET mutation_revision=0")
        elif change == "index-missing":
            conn.execute("DELETE FROM capability_expiries")
        else:
            key = conn.execute("SELECT cache_key FROM capability_cache LIMIT 1").fetchone()[0]
            conn.execute(
                "INSERT INTO capability_expiries VALUES(?,?)", (key, "9999-12-31T23:59:59.999999Z")
            )
        rejected(store)


@pytest.mark.parametrize(
    "column,value",
    [
        ("payload", "{}"),
        ("digest", "0" * 64),
        ("task", "llm.chat"),
        ("status", "draft"),
        ("prepared_at", "2020-01-01T00:00:00.000000Z"),
        ("expires_at", "2030-01-01T00:00:00.000000Z"),
    ],
)
def test_every_changed_plan_column_is_revalidated(tmp_path, execution_fixture, column, value):
    root = tmp_path / "state"
    api.prepare_execution_plan(task="llm.train", state_dir=root)
    with open_store(root) as store, validation_session():
        store.verify()
        store.connection.execute(f"UPDATE execution_plans SET {column}=?", (value,))
        rejected(store)


def test_new_valid_plan_payload_cannot_reuse_old_approval_binding(tmp_path, execution_fixture):
    root = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=root).data.plan
    api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=root)
    with open_store(root) as store, validation_session():
        store.verify()
        body = plan.model_dump(mode="json", exclude={"digest"})
        body["context"]["project_id"] = "changed"
        for capability in body["assessment"]["capabilities"]:
            capability["key"]["scope"]["project_id"] = "changed"
        body["digest"] = hashlib.sha256(canonical(body)).hexdigest()
        updated = ExecutionPlan.model_validate_json(canonical(body))
        store.connection.execute(
            "UPDATE execution_plans SET digest=?,payload=? WHERE plan_id=?",
            (
                updated.digest,
                canonical(updated.model_dump(mode="json")).decode("ascii"),
                plan.plan_id,
            ),
        )
        rejected(store)


def test_approval_payload_is_freshly_validated_when_plan_summary_reused(
    tmp_path, execution_fixture
):
    root = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=root).data.plan
    api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=root)
    with open_store(root) as store, validation_session():
        store.verify()
        store.connection.execute("UPDATE execution_approvals SET payload='{}'")
        rejected(store)


def test_migration_error_clears_session_and_current_open_does_not_create_one(tmp_path, monkeypatch):
    root = tmp_path / "state"
    with monkeypatch.context() as old:
        old.setattr(state_schema, "MIGRATIONS", state_schema.MIGRATIONS[:4])
        api.initialize_state(state_dir=root)
    assert ACTIVE.get() is None
    with monkeypatch.context() as bad:
        bad.setattr(data_migrations, "SOURCE", tmp_path / "absent.py")
        with pytest.raises(YorungeError) as failure:
            api.initialize_state(state_dir=root)
        assert failure.value.code == "state_invalid"
    assert ACTIVE.get() is None
    api.initialize_state(state_dir=root)
    assert ACTIVE.get() is None
    with open_store(root) as store:
        assert ACTIVE.get() is None
        store.verify()
    assert ACTIVE.get() is None


def test_memo_bound_nesting_and_lifetime_do_not_retain_payloads_or_cross_operations():
    @dataclass(frozen=True)
    class Summary:
        value: int

    tracing = tracemalloc.is_tracing()
    if not tracing:
        tracemalloc.start()
    baseline = tracemalloc.get_traced_memory()[0]
    try:
        with validation_session():
            outer = ACTIVE.get()
            for index in range(MAX_ENTRIES + 1):
                payload = f"payload-{index:05d}" + "x" * 65536
                validated(Summary, (index, payload), lambda index=index: Summary(index))
            assert len(outer.entries) == MAX_ENTRIES
            assert tracemalloc.get_traced_memory()[0] - baseline < 8 * 1024 * 1024
            with validation_session():
                assert ACTIVE.get() is outer
    finally:
        if not tracing:
            tracemalloc.stop()
    assert ACTIVE.get() is None
    assert not outer.entries
    with validation_session():
        assert ACTIVE.get() is not outer
        assert not ACTIVE.get().entries
    assert ACTIVE.get() is None


def test_foreign_key_validation_is_not_memoized(tmp_path, execution_fixture):
    root = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=root).data.plan
    api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=root)
    with open_store(root) as store, validation_session():
        store.verify()
        store.connection.execute("PRAGMA foreign_keys=OFF")
        store.connection.execute("DELETE FROM execution_plans")
        assert store.connection.execute("PRAGMA foreign_key_check").fetchone() is not None
        rejected(store)
