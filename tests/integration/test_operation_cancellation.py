"""A local interruption after arm cannot lose the durable uncertainty envelope."""

from asyncio import CancelledError

import pytest

from yorunge import api
from yorunge.domain.errors import OperationError


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, CancelledError])
@pytest.mark.parametrize("cleanup_interrupted", [False, True])
def test_post_arm_cancellation_has_safe_id_exit_and_cannot_be_replayed(
    operation_setup, monkeypatch, interruption, cleanup_interrupted
):
    state, plan, backend = operation_setup
    calls = []

    def cancelled(request, *, deadline):
        calls.append(request.attempt_id)
        raise interruption("private-cancellation-input")

    def cleanup_cancelled(*args):
        raise KeyboardInterrupt

    monkeypatch.setattr(backend, "start", cancelled)
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        if cleanup_interrupted:
            monkeypatch.setattr(coordinator.repository, "uncertain", cleanup_cancelled)
        with pytest.raises(OperationError) as caught:
            coordinator.dispatch(identifier, claim.ownership)
        assert caught.value.code == "operation_uncertain"
        assert caught.value.reason_code == "request_cancelled"
        assert caught.value.operation_id == identifier
        assert caught.value.exit_code == 5
        assert caught.value.__context__ is None
        assert caught.value.__cause__ is None
        assert "private-cancellation-input" not in str(caught.value.envelope())
        record = coordinator.repository.operation(identifier)
        assert record.dispatch_attempt_id is not None
        if not cleanup_interrupted:
            assert record.summary.status == "unknown"
        assert coordinator.admit(plan.plan_id).ownership is None
        with pytest.raises(OperationError) as repeated:
            coordinator.dispatch(identifier, claim.ownership)
        assert repeated.value.code == "operation_conflict"
    assert len(calls) == 1
    assert backend.effects() == []
