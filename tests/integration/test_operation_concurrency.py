"""Independent-process forget/revoke/reset writes around operation linearization."""

import json
import subprocess
import sys
from datetime import timedelta

import pytest

from yorunge import api
from yorunge.adapters.operation_repository import StateOperations
from yorunge.adapters.state import open_store
from yorunge.domain.capabilities import timestamp
from yorunge.domain.errors import YorungeError


def action_process(action, state, plan, backend, clock, confirmation=None):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tests.fixtures.operation_worker",
            action,
            str(state),
            plan.plan_id,
            str(backend.marker),
            timestamp(clock.value),
            confirmation or plan.digest,
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["code"]


def test_forget_committed_before_admission_leaves_no_job_or_effect(
    operation_setup, execution_clock, monkeypatch
):
    state, plan, backend = operation_setup
    original = StateOperations.admit

    def forget_first(self, *args):
        assert action_process("forget", state, plan, backend, execution_clock) == "ok"
        return original(self, *args)

    monkeypatch.setattr(StateOperations, "admit", forget_first)
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        with pytest.raises(YorungeError) as error:
            coordinator.admit(plan.plan_id)
        assert error.value.code == "plan_not_found"
    with open_store(state) as store:
        assert store.connection.execute("SELECT count(*) FROM operations").fetchone()[0] == 0
        assert store.connection.execute("SELECT count(*) FROM execution_plans").fetchone()[0] == 0
    assert backend.calls == 0


def test_admission_committed_before_forget_pins_plan_and_preserves_one_start(
    operation_setup, execution_clock
):
    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        assert action_process("forget", state, plan, backend, execution_clock) == "plan_in_use"
        coordinator.dispatch(claim.job.operation.operation_id, claim.ownership)
    assert len(backend.effects()) == 1


@pytest.mark.parametrize("timing", ["before", "after"])
def test_revoke_on_each_side_of_arm_commit_has_the_declared_boundary(
    operation_setup, execution_clock, monkeypatch, timing
):
    state, plan, backend = operation_setup
    original = StateOperations.arm

    def revoke(self, *args):
        if timing == "before":
            assert action_process("revoke", state, plan, backend, execution_clock) == "ok"
        record = original(self, *args)
        if timing == "after":
            assert action_process("revoke", state, plan, backend, execution_clock) == "ok"
        return record

    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        monkeypatch.setattr(StateOperations, "arm", revoke)
        if timing == "before":
            with pytest.raises(YorungeError) as error:
                coordinator.dispatch(identifier, claim.ownership)
            assert error.value.code == "state_changed"
            assert coordinator.repository.operation(identifier).dispatch_attempt_id is None
        else:
            coordinator.dispatch(identifier, claim.ownership)
            assert coordinator.repository.operation(identifier).dispatch_attempt_id is not None
        assert coordinator.repository.operation(identifier).admission.approval.status == "approved"
    assert len(backend.effects()) == (1 if timing == "after" else 0)
    if timing == "before":
        execution_clock.value += timedelta(seconds=31)
        with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
            cleaned = coordinator.takeover(identifier)
            assert cleaned.ownership is None
            assert cleaned.job.outcome.reason_code == "approval_revoked"


def test_active_composition_blocks_exclusive_reset_without_cancelling_armed_call(
    operation_setup, execution_clock, monkeypatch
):
    state, plan, backend = operation_setup
    preview = api.preview_identity_reset(state_dir=state).data
    original = StateOperations.arm

    def attempt_reset_after_arm(self, *args):
        result = original(self, *args)
        assert (
            action_process("reset", state, plan, backend, execution_clock, preview.digest)
            == "state_busy"
        )
        return result

    monkeypatch.setattr(StateOperations, "arm", attempt_reset_after_arm)
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        coordinator.dispatch(identifier, claim.ownership)
    assert len(backend.effects()) == 1
    preview = api.preview_identity_reset(state_dir=state).data
    api.reset_identity(preview.digest, state_dir=state)
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        assert coordinator.repository.job(identifier).operation.status == "unknown"
    assert len(backend.effects()) == 1
