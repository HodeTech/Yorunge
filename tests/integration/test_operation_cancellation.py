"""A local interruption after arm cannot lose the durable uncertainty envelope."""

from asyncio import CancelledError
from contextlib import ExitStack
from datetime import timedelta

import pytest

from yorunge import api
from yorunge.adapters.http_session import HttpSession
from yorunge.domain.errors import OperationError, YorungeError


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


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, CancelledError])
@pytest.mark.parametrize("boundary", ["post-arm-check", "arm-return", "unreadable-arm-return"])
def test_committed_arm_cancellation_never_escapes_as_local_cancel(
    operation_setup, monkeypatch, interruption, boundary
):
    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        original_arm = coordinator.repository.arm
        original_operation = coordinator.repository.operation
        original_process = coordinator._same_process
        armed = False
        checks = 0

        def interrupted_arm(*args):
            nonlocal armed
            result = original_arm(*args)
            armed = True
            if boundary != "post-arm-check":
                raise interruption
            return result

        def process_check(*args):
            nonlocal checks
            checks += 1
            if checks == 2:
                raise interruption
            original_process(*args)

        def inspected(*args):
            if armed and boundary == "unreadable-arm-return":
                raise YorungeError("state_busy")
            return original_operation(*args)

        monkeypatch.setattr(coordinator.repository, "arm", interrupted_arm)
        monkeypatch.setattr(coordinator.repository, "operation", inspected)
        if boundary == "post-arm-check":
            monkeypatch.setattr(coordinator, "_same_process", process_check)
        with pytest.raises(OperationError) as caught:
            coordinator.dispatch(identifier, claim.ownership)
        assert caught.value.code == "operation_uncertain"
        assert caught.value.reason_code == "request_cancelled"
        assert caught.value.operation_id == identifier
        assert caught.value.exit_code == 5
        assert caught.value.__context__ is None
        assert original_operation(identifier).dispatch_attempt_id is not None
        assert original_operation(identifier).summary.status == "unknown"
        monkeypatch.setattr(coordinator.repository, "operation", original_operation)
        with pytest.raises(OperationError) as repeated:
            coordinator.dispatch(identifier, claim.ownership)
        assert repeated.value.code == "operation_conflict"
    assert backend.calls == 0
    assert backend.effects() == []


@pytest.mark.parametrize("invalid_context", ["closed", "active-loop"])
def test_renew_cannot_mutate_a_lease_through_invalid_owned_context(
    operation_setup, execution_clock, monkeypatch, invalid_context
):
    state, plan, backend = operation_setup
    with ExitStack() as stack:
        http = stack.enter_context(HttpSession())
        monkeypatch.setattr(backend, "preflight", http.preflight, raising=False)
        with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
            claim = coordinator.admit(plan.plan_id)
            identifier = claim.job.operation.operation_id
            before = coordinator.repository.operation(identifier)
            execution_clock.value += timedelta(seconds=1)
            if invalid_context == "closed":
                stack.close()
                with pytest.raises(OperationError) as caught:
                    coordinator.renew(identifier, claim.ownership)
            else:
                import asyncio

                async def renew():
                    coordinator.renew(identifier, claim.ownership)

                running = renew()
                with pytest.raises(OperationError) as caught:
                    asyncio.run(running)
            assert caught.value.code == "invalid_request"
            assert coordinator.repository.operation(identifier) == before
    assert backend.calls == 0


def test_pre_port_capacity_failure_keeps_its_closed_details(operation_setup, monkeypatch):
    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id

        def full(*args):
            raise OperationError(
                "operation_capacity_exceeded", identifier, capacity_kind="transition"
            )

        monkeypatch.setattr(coordinator.repository, "dispatch_window", full)
        with pytest.raises(OperationError) as caught:
            coordinator.dispatch(identifier, claim.ownership)
        assert caught.value.code == "operation_capacity_exceeded"
        assert caught.value.capacity_kind == "transition"
        assert caught.value.operation_id == identifier
        assert caught.value.exit_code == 2
        assert caught.value.__context__ is None
    assert backend.calls == 0


@pytest.mark.parametrize("interruption", [SystemExit, GeneratorExit])
def test_process_exit_after_arm_keeps_exception_identity_and_durable_unknown(
    operation_setup, monkeypatch, interruption
):
    state, plan, backend = operation_setup
    failure = interruption("synthetic process exit")
    calls = []

    def exited(request, *, deadline):
        calls.append(request.attempt_id)
        raise failure

    monkeypatch.setattr(backend, "start", exited)
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        with pytest.raises(interruption) as caught:
            coordinator.dispatch(identifier, claim.ownership)
        assert caught.value is failure
        record = coordinator.repository.operation(identifier)
        assert record.dispatch_attempt_id is not None
        assert record.summary.status == "unknown"
        assert coordinator.admit(plan.plan_id).ownership is None
        with pytest.raises(OperationError) as repeated:
            coordinator.dispatch(identifier, claim.ownership)
        assert repeated.value.code == "operation_conflict"
    assert len(calls) == 1
    assert backend.effects() == []
