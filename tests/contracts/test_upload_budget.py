"""Original-invocation quota conservation, ownership and no replay after a failed attempt."""

import asyncio
import copy
import pickle
import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

import pytest

from yorunge.application import upload_budget as module
from yorunge.application.upload_budget import UploadBudget, UploadReservation
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.upload_costs import UploadRequestLimits

MIB = 1_048_576


def limits(n=4, size=1_073_741_824):
    return UploadRequestLimits(
        max_create=1,
        max_project_link=1,
        max_presign=n,
        max_put=n,
        max_confirm=n,
        max_read_requests=512,
        max_read_attempts=1024,
        max_control_request_bytes=4 * MIB,
        max_control_response_bytes=16 * MIB,
        max_upload_bytes=size,
    )


@pytest.fixture
def clock(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(module.time, "monotonic", lambda: now[0])
    return now


def budget(*, read_only=False, end=1900.0, values=None):
    return UploadBudget(limits() if values is None else values, end=end, read_only=read_only)


def error(code, callback):
    with pytest.raises(YorungeError) as captured:
        callback()
    assert captured.value.code == code
    return captured.value


@pytest.mark.parametrize(
    "end", [True, None, "1100", float("nan"), float("inf"), -float("inf"), 1000, 1900.001, 10**1000]
)
def test_total_deadline_is_finite_strict_and_at_most_900_seconds(clock, end):
    error("invalid_request", lambda: budget(end=end))


@pytest.mark.parametrize("value", [None, {}, True, 0, 1, "false"])
def test_saved_limits_and_readonly_policy_are_not_coerced(clock, value):
    error("invalid_request", lambda: UploadBudget(value, end=1900, read_only=False))
    if value is not True:
        error("invalid_request", lambda: UploadBudget(limits(), end=1900, read_only=value))


@pytest.mark.parametrize(
    "change",
    [
        {"max_create": True},
        {"max_presign": 129},
        {"max_read_requests": 513},
        {"max_upload_bytes": -1},
        {"max_control_response_bytes": 16.0 * MIB},
    ],
)
def test_constructed_or_copied_limits_are_revalidated(clock, change):
    bad = limits().model_copy(update=change)
    error("invalid_request", lambda: budget(values=bad))


@pytest.mark.parametrize("kind", ["create", "project_link", "presign", "put", "confirm"])
def test_read_only_budget_cannot_claim_an_effect(clock, kind):
    value = budget(read_only=True)
    before = value.snapshot()
    error("invalid_request", lambda: value.reserve(kind, response_bytes=0))
    assert value.snapshot() == before


@pytest.mark.parametrize(
    "kwargs",
    [
        {"kind": "READ"},
        {"kind": None},
        {"kind": []},
        {"kind": "read", "request_bytes": 1},
        {"kind": "read", "upload_bytes": 1},
        {"kind": "create", "upload_bytes": 1},
        {"kind": "put", "request_bytes": 1},
        {"kind": "read", "response_bytes": True},
        {"kind": "read", "response_bytes": -1},
        {"kind": "read", "response_bytes": MIB + 1},
        {"kind": "put", "response_bytes": 65_537},
        {"kind": "put", "upload_bytes": 500_000_001},
        {"kind": "create", "request_bytes": 1.0},
        {"kind": "create", "request_bytes": MIB + 1},
    ],
)
def test_bad_claim_is_atomic(clock, kwargs):
    value = budget()
    before = value.snapshot()
    error("invalid_request", lambda: value.reserve(**kwargs))
    assert value.snapshot() == before


def test_unstarted_claim_can_be_returned_once_even_after_deadline(clock):
    value = budget(end=1001)
    empty = value.snapshot()
    claim = value.reserve("create", request_bytes=MIB, response_bytes=MIB)
    assert value.snapshot().create_requests == 1
    clock[0] = 1002
    claim.finish()
    assert value.snapshot() == empty
    error("invalid_request", claim.finish)
    error("execution_timeout", lambda: value.reserve("read"))


def test_begin_without_physical_attempt_is_also_provably_unspent(clock):
    value = budget()
    empty = value.snapshot()
    claim = value.reserve("put", upload_bytes=10, response_bytes=64)

    async def run():
        claim.begin()
        claim.finish()

    asyncio.run(run())
    assert value.snapshot() == empty


def test_request_bytes_and_effect_slot_never_return_after_delegate_failure(clock):
    value = budget()
    claim = value.reserve("create", request_bytes=31, response_bytes=MIB)

    async def run():
        claim.begin()
        claim.attempt()  # Socket/delegate can fail immediately after this point.
        error("invalid_request", claim.attempt)
        claim.finish()
        error("invalid_request", claim.begin)

    asyncio.run(run())
    snapshot = value.snapshot()
    assert snapshot.create_requests == snapshot.effect_attempts == 1
    assert snapshot.control_request_reserved == snapshot.control_request_bytes == 31
    assert snapshot.response_pending == snapshot.response_bytes == 0
    error("upload_limit_exceeded", lambda: value.reserve("create", response_bytes=0))


def test_global_read_request_and_retry_limits_include_failures(clock):
    value = budget(read_only=True)

    async def run():
        for _ in range(512):
            claim = value.reserve("read", response_bytes=0)
            claim.begin()
            claim.attempt()
            claim.attempt()
            error("invalid_request", claim.attempt)
            claim.finish()
        error("upload_limit_exceeded", lambda: value.reserve("read", response_bytes=0))

    asyncio.run(run())
    assert value.snapshot().read_requests == 512
    assert value.snapshot().read_attempts == 1024
    assert value.snapshot().effect_attempts == 0


def test_control_request_limit_is_reserved_before_any_intent_or_wire(clock):
    value = budget()
    claims = [
        value.reserve(kind, request_bytes=MIB, response_bytes=0)
        for kind in ("create", "project_link", "presign", "presign")
    ]
    assert value.snapshot().control_request_reserved == 4 * MIB
    before = value.snapshot()
    error(
        "upload_limit_exceeded", lambda: value.reserve("confirm", request_bytes=1, response_bytes=0)
    )
    assert value.snapshot() == before
    claims[-1].finish()
    claim = value.reserve("confirm", request_bytes=MIB, response_bytes=0)
    assert value.snapshot().control_request_reserved == 4 * MIB
    claim.finish()
    for item in claims[:-1]:
        item.finish()
    assert value.snapshot().control_request_reserved == 0


def test_put_total_declared_bytes_cannot_exceed_manifest_work(clock):
    value = budget()
    claims = [
        value.reserve("put", upload_bytes=size, response_bytes=0)
        for size in (500_000_000, 500_000_000, 73_741_824)
    ]
    assert value.snapshot().upload_reserved == 1_073_741_824
    before = value.snapshot()
    error("upload_limit_exceeded", lambda: value.reserve("put", upload_bytes=1, response_bytes=0))
    assert value.snapshot() == before
    claims[-1].finish()
    value.reserve("put", upload_bytes=73_741_824, response_bytes=0)


def test_response_pending_plus_consumed_conserves_the_aggregate_limit(clock):
    value = budget()
    claims = [value.reserve("read", response_bytes=MIB) for _ in range(16)]
    before = value.snapshot()
    assert before.response_pending == 16 * MIB
    error("upload_limit_exceeded", lambda: value.reserve("read", response_bytes=1))
    assert value.snapshot() == before

    async def run():
        for claim in claims:
            claim.begin()
            claim.attempt()
            claim.response(MIB)
            claim.finish()

    asyncio.run(run())
    assert value.snapshot().response_bytes == 16 * MIB
    assert value.snapshot().response_pending == 0
    error("upload_limit_exceeded", lambda: value.reserve("read", response_bytes=1))
    value.reserve("read", response_bytes=0).finish()


def test_partial_response_only_releases_unused_capacity_and_oversize_is_atomic(clock):
    value = budget()
    claim = value.reserve("read", response_bytes=10)

    async def run():
        claim.begin()
        error("invalid_request", lambda: claim.response(1))
        claim.attempt()
        claim.response(6)
        before = value.snapshot()
        error("invalid_response", lambda: claim.response(5))
        assert value.snapshot() == before
        claim.finish()

    asyncio.run(run())
    assert value.snapshot().response_bytes == 6
    assert value.snapshot().response_pending == 0
    assert value.snapshot().read_requests == 1


def test_two_workers_share_quota_and_partial_upload_stays_spent(clock):
    value = budget(values=limits(n=2, size=10))
    claims = [value.reserve("put", upload_bytes=5, response_bytes=4) for _ in range(2)]

    async def run():
        async def worker(claim):
            claim.begin()
            try:
                claim.attempt()
                claim.upload(3)
                await asyncio.sleep(0)
                claim.response(1)
                error("input_changed", lambda: claim.upload(3))
            finally:
                claim.finish()

        await asyncio.gather(*(worker(claim) for claim in claims))

    asyncio.run(run())
    snapshot = value.snapshot()
    assert snapshot.upload_reserved == 10 and snapshot.upload_bytes == 6
    assert snapshot.put_requests == snapshot.effect_attempts == 2
    assert snapshot.response_bytes == 2 and snapshot.response_pending == 0
    error("upload_limit_exceeded", lambda: value.reserve("put", upload_bytes=0, response_bytes=0))
    assert all(type(number) is int for number in asdict(snapshot).values())


def test_cancellation_cleanup_preserves_attempt_and_partial_counters(clock):
    value = budget()
    claim = value.reserve("put", upload_bytes=2, response_bytes=4)

    async def run():
        ready = asyncio.Event()

        async def worker():
            claim.begin()
            try:
                claim.attempt()
                claim.upload(1)
                ready.set()
                await asyncio.Event().wait()
            finally:
                claim.finish()

        task = asyncio.create_task(worker())
        await ready.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())
    assert value.snapshot().upload_bytes == 1
    assert value.snapshot().upload_reserved == 2
    assert value.snapshot().effect_attempts == 1
    assert value.snapshot().response_pending == 0


def test_wrong_task_cannot_consume_or_close_an_active_claim(clock):
    value = budget()
    claim = value.reserve("read", response_bytes=2)

    async def run():
        claim.begin()

        async def other():
            for callback in (claim.begin, claim.attempt, lambda: claim.response(1), claim.finish):
                error("invalid_request", callback)

        await asyncio.create_task(other())
        claim.attempt()
        claim.response(2)
        claim.finish()

    asyncio.run(run())
    assert value.snapshot().read_attempts == 1
    assert value.snapshot().response_bytes == 2


def test_pid_thread_and_loop_owner_reject_before_mutation(clock, monkeypatch):
    value = budget()
    claim = value.reserve("read", response_bytes=0)
    original_pid = module.os.getpid()
    monkeypatch.setattr(module.os, "getpid", lambda: original_pid + 1)
    error("invalid_request", claim.finish)
    monkeypatch.setattr(module.os, "getpid", lambda: original_pid)
    with ThreadPoolExecutor(max_workers=1) as pool:
        failure = pool.submit(error, "invalid_request", value.snapshot).result()
    assert failure.code == "invalid_request"

    async def first():
        claim.begin()
        claim.attempt()
        claim.finish()

    asyncio.run(first())
    second = value.reserve("read", response_bytes=0)

    async def other_loop():
        error("invalid_request", second.begin)

    asyncio.run(other_loop())
    second.finish()
    assert value.snapshot().read_attempts == 1


def test_deadline_does_not_prevent_cleanup_or_inspection(clock):
    value = budget(end=1001)
    claim = value.reserve("read", response_bytes=10)

    async def run():
        claim.begin()
        claim.attempt()
        claim.response(2)
        clock[0] = 1001
        for callback in (claim.attempt, lambda: claim.response(1), lambda: value.end):
            error("execution_timeout", callback)
        claim.finish()

    asyncio.run(run())
    assert value.snapshot().response_bytes == 2
    assert value.snapshot().response_pending == 0


def test_unissued_reservation_cannot_decrement_or_consume_quota(clock):
    value = budget()
    forged = UploadReservation(value, "create", 1, 0, 1)
    before = value.snapshot()
    error("invalid_request", forged.finish)

    async def run():
        error("invalid_request", forged.begin)

    asyncio.run(run())
    assert value.snapshot() == before


def test_private_state_cannot_be_cloned_or_serialized_and_public_error_is_closed(clock):
    value = budget()
    claim = value.reserve("read", response_bytes=0)
    for instance in (value, claim):
        for callback in (
            lambda instance=instance: copy.copy(instance),
            lambda instance=instance: copy.deepcopy(instance),
            lambda instance=instance: pickle.dumps(instance),
        ):
            with pytest.raises(TypeError):
                callback()
        assert repr(instance) == "<upload quota private>"
    failure = YorungeError("upload_limit_exceeded")
    assert failure.exit_code == 2 and failure.envelope()["retryable"] is False
    bound = OperationError(
        "operation_uncertain",
        "11111111-1111-4111-8111-111111111111",
        reason_code="upload_limit_exceeded",
    )
    assert bound.exit_code == 5
    assert bound.envelope()["details"] == {
        "reason_code": "upload_limit_exceeded",
        "capacity_kind": None,
    }


@pytest.mark.parametrize("field", list(UploadRequestLimits.model_fields))
@pytest.mark.parametrize("value", ["QUOTA-REJECTED-INPUT-CANARY", object()])
def test_revalidation_never_serializes_rejected_values_or_emits_warnings(
    clock, capsys, field, value
):
    bad = limits().model_copy(update={field: value})
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("error")
        failure = error("invalid_request", lambda: budget(values=bad))
    assert observed == []
    assert capsys.readouterr() == ("", "")
    assert failure.__context__ is None and failure.__cause__ is None
    assert "QUOTA-REJECTED-INPUT-CANARY" not in str(failure.envelope())


def test_constructed_missing_and_extra_fields_reject_without_dumping_input(clock, capsys):
    incomplete = UploadRequestLimits.model_construct()
    extra = limits().model_copy(update={"unexpected": "QUOTA-EXTRA-CANARY"})
    for bad in (incomplete, extra):
        with warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter("error")
            failure = error("invalid_request", lambda bad=bad: budget(values=bad))
        assert observed == []
        assert failure.__context__ is None
    assert capsys.readouterr() == ("", "")
