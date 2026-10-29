"""Lifetime bounds retain history, cleanup and credential-reset recovery."""

from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from tests.fixtures.operation_backend import ProcessBackend
from tests.integration.test_operation_store import raw_attempt, raw_record
from yorunge import api
from yorunge.adapters.operation_store import (
    OPERATION_COLUMNS,
    decode_operation,
    read_job,
    read_operation,
    write_attempt,
)
from yorunge.adapters.state import open_store, validate_contents
from yorunge.domain.errors import YorungeError


def test_sixteen_unarmed_candidates_can_be_cleaned_without_seventeenth_start(
    operation_setup, execution_clock
):
    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
    with open_store(state) as store:
        connection = store.connection
        record, job = read_operation(connection, identifier), read_job(connection, identifier)
        current = job.attempts[-1]
        connection.execute("BEGIN IMMEDIATE")
        for number in range(2, 17):
            raw_attempt(
                connection,
                current.model_copy(update={"status": "abandoned", "reason_code": "owner_changed"}),
            )
            current = current.model_copy(update={"attempt_id": str(uuid4()), "number": number})
            write_attempt(connection, identifier, current)
        changed = record.model_copy(
            update={
                "fence": 16,
                "summary": record.summary.model_copy(update={"attempt_count": 16, "revision": 16}),
                "lease": record.lease.model_copy(update={"fence": 16, "owner_id": str(uuid4())}),
            }
        )
        raw_record(connection, changed)
        connection.execute("COMMIT")
        validate_contents(connection)
    execution_clock.value += timedelta(seconds=31)
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        cleaned = coordinator.takeover(identifier)
        assert cleaned.ownership is None
        assert cleaned.job.operation.status == "failed"
        assert cleaned.job.operation.attempt_count == 16
        assert cleaned.job.outcome.reason_code == "capacity_exceeded"
    assert backend.calls == 0


def test_exhausted_fence_does_not_block_credential_reset(operation_setup, execution_clock):
    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        coordinator.dispatch(identifier, claim.ownership)
    with open_store(state) as store:
        record, job = (
            read_operation(store.connection, identifier),
            read_job(store.connection, identifier),
        )
        changed = record.model_copy(
            update={
                "fence": 2**63 - 1,
                "recovery_reason": "owner_changed",
                "lease": record.lease.model_copy(
                    update={"fence": 2**63 - 1, "owner_id": str(uuid4())}
                ),
                "summary": record.summary.model_copy(
                    update={
                        "status": "unknown",
                        "execution_status": "unknown",
                        "revision": record.summary.revision + 1,
                    }
                ),
            }
        )
        raw_record(store.connection, changed)
        raw_attempt(
            store.connection,
            job.attempts[-1].model_copy(
                update={"status": "unknown", "reason_code": "owner_changed"}
            ),
        )
        validate_contents(store.connection)
    execution_clock.value += timedelta(seconds=31)
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        with pytest.raises(YorungeError) as error:
            coordinator.takeover(identifier)
        assert error.value.code == "operation_fence_exhausted"
    preview = api.preview_identity_reset(state_dir=state).data
    api.reset_identity(preview.digest, state_dir=state)
    with open_store(state) as store:
        record = read_operation(store.connection, identifier)
        assert record.lease is None
        assert record.fence == 2**63 - 1
        assert record.recovery_reason == "identity_reset"
        validate_contents(store.connection)
    assert len(backend.effects()) == 1


def test_all_1024_leases_are_fenced_by_another_stateful_expiry_observation_and_plan_slots_pin(
    tmp_path, execution_fixture, execution_clock
):
    from tests.fixtures.seed_operation_state import seed
    from yorunge.adapters.execution_store import read_plan

    state = tmp_path / "state"
    source_config = Path(__file__).resolve().parents[2] / "examples/profile.toml"
    counts = seed(state, layout="normal", maximum=False)
    assert counts["operations"] == 1024
    with open_store(state) as store:
        records = [
            decode_operation(row)
            for row in store.connection.execute(f"SELECT {OPERATION_COLUMNS} FROM operations")
        ]
        assert all(record.lease is not None for record in records)
    execution_clock.value += timedelta(seconds=31)
    api.query_capabilities(task="llm.train", config=source_config, state_dir=state)
    execution_clock.value -= timedelta(seconds=2)
    backend = ProcessBackend(tmp_path / "effects")
    for record in (records[0], records[-1]):
        with api._operation_session(
            record.summary.plan_id, backend, state_dir=state
        ) as coordinator:
            with pytest.raises(YorungeError) as error:
                coordinator.renew(record.summary.operation_id, record.lease)
            assert error.value.code == "operation_lease_lost"
    with open_store(state) as store:
        generation = store.connection.execute(
            "SELECT clock_generation FROM cache_clock"
        ).fetchone()[0]
        assert all(record.lease.ownership_clock_generation < generation for record in records)
        plan = read_plan(store.connection, records[0].summary.plan_id)
    execution_clock.value += timedelta(seconds=2)
    with pytest.raises(YorungeError) as error:
        api.prepare_execution_plan(task="llm.train", config=source_config, state_dir=state)
    assert error.value.code == "plan_capacity_exceeded"
    with pytest.raises(YorungeError) as error:
        api.forget_execution_plan(plan.plan_id, plan.digest, state_dir=state)
    assert error.value.code == "plan_in_use"
    assert backend.calls == 0
