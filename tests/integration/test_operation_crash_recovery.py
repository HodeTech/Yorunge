"""Terminal outcome and identity reset atomicity across real SIGKILL boundaries."""

import signal
import subprocess
import sys
from datetime import timedelta

import pytest

from tests.fixtures.operation_backend import ProcessBackend, ReadObserver
from yorunge import api
from yorunge.adapters.operation_store import read_job, read_operation
from yorunge.adapters.state import metadata, open_store, validate_contents
from yorunge.domain.capabilities import timestamp
from yorunge.domain.errors import YorungeError


@pytest.mark.parametrize(
    "point",
    [
        "outcome_before",
        "outcome_mid",
        "outcome_after",
        "reset_mid",
        "reset_after",
        "reset_unarmed_mid",
        "reset_unarmed_after",
    ],
)
def test_process_death_preserves_atomic_outcome_or_reset_and_never_replays_start(
    tmp_path, execution_fixture, execution_clock, point
):
    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state)
    backend = ProcessBackend(tmp_path / "effects")
    child = subprocess.run(
        [
            sys.executable,
            "-m",
            "tests.fixtures.operation_worker",
            point,
            str(state),
            plan.plan_id,
            str(backend.marker),
            timestamp(execution_clock.value),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert child.returncode == -signal.SIGKILL, child.stderr
    with open_store(state) as store:
        validate_contents(store.connection)
        identifier = store.connection.execute("SELECT operation_id FROM operations").fetchone()[0]
        saved = read_operation(store.connection, identifier)
        job = read_job(store.connection, identifier)
        changed_epoch = metadata(store.connection).identity_epoch != plan.identity_epoch
    assert changed_epoch == (point in {"reset_after", "reset_unarmed_after"})
    if point == "outcome_after":
        assert job.operation.status == "succeeded"
        assert job.outcome is not None
    elif point == "reset_unarmed_after":
        assert job.operation.status == "cancelled"
        assert job.outcome.reason_code == "identity_reset"
    else:
        assert job.outcome is None
    if not point.startswith("reset_unarmed_"):
        assert saved.dispatch_attempt_id is not None
    execution_clock.value += timedelta(seconds=31)
    observer = ReadObserver(execution_clock, marker=backend.marker)
    with api._operation_session(
        plan.plan_id, backend, observer=observer, state_dir=state
    ) as coordinator:
        if point in {"outcome_after", "reset_unarmed_after"}:
            assert coordinator.reconcile(identifier, saved.lease) == job
        else:
            claim = coordinator.takeover(identifier)
            if saved.dispatch_attempt_id is None:
                coordinator.dispatch(identifier, claim.ownership)
            else:
                with pytest.raises(YorungeError) as error:
                    coordinator.dispatch(identifier, claim.ownership)
                assert error.value.code == "operation_conflict"
            assert (
                coordinator.reconcile(identifier, claim.ownership).operation.status == "succeeded"
            )
    assert len(backend.effects()) == (0 if point == "reset_unarmed_after" else 1)
