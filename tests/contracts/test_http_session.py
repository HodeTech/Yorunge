"""The synchronous bridge rejects unsafe owners before making a consumer awaitable."""

import asyncio
import contextvars
import gc
import json
import logging
import os
import subprocess
import sys
import threading
import time
import weakref
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from uuid import uuid4

import httpx
import pytest

from yorunge.adapters.http_session import HttpSession
from yorunge.adapters.http_transport import HttpxTransport
from yorunge.application.http_transport import HttpRequest
from yorunge.domain.credentials import normalize_target
from yorunge.domain.errors import OperationError, YorungeError

TARGET = normalize_target("https://example.test/v1")
PRIVATE_CALLBACK = "private-callback-canary-872941"


class Body(httpx.AsyncByteStream):
    def __init__(self, closed):
        self.closed = closed

    async def __aiter__(self):
        yield b"response"

    async def aclose(self):
        self.closed.append(True)


def session_fixture():
    factories, requests, closed = [], [], []

    async def handler(wire):
        requests.append(wire)
        return httpx.Response(200, stream=Body(closed))

    def factory():
        factories.append(True)
        return HttpxTransport(transport=httpx.MockTransport(handler))

    return HttpSession(transport_factory=factory), factories, requests, closed


async def consume(transport):
    request = HttpRequest(TARGET, "GET", "data", service_id="evren-platform")
    async with transport.open(request, deadline=time.monotonic() + 2) as response:
        return b"".join([part async for part in response.chunks()])


def test_construction_has_no_client_or_loop_and_closed_session_is_single_use():
    session, factories, requests, _ = session_fixture()
    assert factories == []
    assert requests == []
    with pytest.raises(YorungeError) as caught:
        session.preflight()
    assert caught.value.code == "invalid_request"
    with session:
        assert factories == [True]
        assert session.call(consume) == b"response"
    with pytest.raises(YorungeError) as caught:
        session.__enter__()
    assert caught.value.code == "invalid_request"
    assert factories == [True]


def test_sequential_calls_share_transport_loop_and_thread_but_not_response_task():
    session, factories, requests, closed = session_fixture()
    owners = []

    async def record(transport):
        owners.append(
            (
                id(transport),
                asyncio.get_running_loop(),
                asyncio.current_task(),
                threading.get_ident(),
            )
        )
        return await consume(transport)

    with session:
        session.preflight()
        assert session.call(record) == b"response"
        assert session.call(record) == b"response"
    first, second = owners
    assert first[0] == second[0]
    assert first[1] is second[1]
    assert first[2] is not second[2]
    assert first[3] == threading.get_ident()
    assert first[1].is_closed()
    assert factories == [True]
    assert len(requests) == 2
    assert closed == [True, True]


@pytest.mark.parametrize("state", ["not-entered", "closed"])
def test_rejected_call_does_not_invoke_or_create_consumer(state):
    session, factories, requests, _ = session_fixture()
    if state == "closed":
        with session:
            pass
    invoked = []

    def consumer(transport):
        invoked.append(True)
        return consume(transport)

    with pytest.raises(YorungeError) as caught:
        session.call(consumer)
    assert caught.value.code == "invalid_request"
    assert caught.value.__context__ is None
    assert invoked == []
    assert requests == []
    assert len(factories) == (state == "closed")


def test_active_loop_rejects_entry_before_factory_without_damaging_session():
    session, factories, requests, _ = session_fixture()

    async def attempt():
        with pytest.raises(YorungeError) as caught:
            session.__enter__()
        assert caught.value.code == "invalid_request"

    asyncio.run(attempt())
    assert factories == []
    assert requests == []
    with session:
        assert session.call(consume) == b"response"


def test_active_loop_rejects_call_and_exit_before_factory_or_coroutine():
    session, _, requests, _ = session_fixture()
    invoked = []

    def consumer(transport):
        invoked.append(True)
        return consume(transport)

    async def attempt():
        for action in (
            session.preflight,
            lambda: session.call(consumer),
            lambda: session.__exit__(None, None, None),
        ):
            with pytest.raises(YorungeError) as caught:
                action()
            assert caught.value.code == "invalid_request"

    with session:
        asyncio.run(attempt())
        assert invoked == []
        assert requests == []
        assert session.call(consume) == b"response"


def test_reentry_rejects_entry_and_call_without_creating_consumer_or_response():
    session, factories, requests, _ = session_fixture()
    invoked = []

    def nested(transport):
        invoked.append(True)
        return consume(transport)

    async def attempt(transport):
        for action in (
            session.preflight,
            session.__enter__,
            lambda: session.call(nested),
            lambda: session.__exit__(None, None, None),
        ):
            with pytest.raises(YorungeError) as caught:
                action()
            assert caught.value.code == "invalid_request"
        return await consume(transport)

    with session:
        with pytest.raises(YorungeError) as caught:
            session.__enter__()
        assert caught.value.code == "invalid_request"
        assert session.call(attempt) == b"response"
    assert invoked == []
    assert factories == [True]
    assert len(requests) == 1


@pytest.mark.parametrize("entered", [False, True])
def test_foreign_thread_cannot_enter_call_or_close_and_owner_remains_usable(entered):
    session, factories, requests, _ = session_fixture()
    invoked = []

    def consumer(transport):
        invoked.append(True)
        return consume(transport)

    def foreign():
        actions = (
            session.preflight,
            session.__enter__,
            lambda: session.call(consumer),
            lambda: session.__exit__(None, None, None),
        )
        for action in actions:
            with pytest.raises(YorungeError) as caught:
                action()
            assert caught.value.code == "invalid_request"

    if entered:
        session.__enter__()
    try:
        with ThreadPoolExecutor(max_workers=1) as worker:
            worker.submit(foreign).result(timeout=2)
        assert invoked == []
        assert requests == []
        assert len(factories) == entered
        if entered:
            assert session.call(consume) == b"response"
    finally:
        if entered:
            session.__exit__(None, None, None)


def test_foreign_pid_gate_runs_before_entry_factory_or_consumer(monkeypatch):
    session, factories, requests, _ = session_fixture()
    invoked = []

    def consumer(transport):
        invoked.append(True)
        return consume(transport)

    original = os.getpid()
    monkeypatch.setattr("yorunge.adapters.http_session.os.getpid", lambda: original + 1)
    for action in (session.__enter__, session.preflight, lambda: session.call(consumer)):
        with pytest.raises(YorungeError) as caught:
            action()
        assert caught.value.code == "invalid_request"
    assert factories == []
    assert requests == []
    assert invoked == []


@pytest.mark.skipif(not hasattr(os, "fork"), reason="fork is not provided by this runtime")
def test_forked_child_cannot_reuse_or_close_parent_session():
    session, _, requests, _ = session_fixture()
    read_fd, write_fd = os.pipe()
    with session:
        child = os.fork()
        if child == 0:
            os.close(read_fd)
            try:
                for action in (
                    session.preflight,
                    lambda: session.call(consume),
                    lambda: session.__exit__(None, None, None),
                ):
                    try:
                        action()
                    except YorungeError as error:
                        if error.code != "invalid_request":
                            os._exit(2)
                    else:
                        os._exit(3)
                os.write(write_fd, b"rejected")
                os._exit(0)
            except BaseException:
                os._exit(4)
        os.close(write_fd)
        try:
            _, status = os.waitpid(child, 0)
            assert status == 0
            assert os.read(read_fd, 32) == b"rejected"
            assert requests == []
            assert session.call(consume) == b"response"
        finally:
            os.close(read_fd)


def test_real_task_cancellation_closes_response_and_preserves_cancelled_error():
    session, _, requests, closed = session_fixture()

    async def cancel(transport):
        request = HttpRequest(TARGET, "GET", "data", service_id="evren-platform")
        async with transport.open(request, deadline=time.monotonic() + 2):
            asyncio.current_task().cancel()
            await asyncio.sleep(0)

    with session:
        with pytest.raises(asyncio.CancelledError):
            session.call(cancel)
        assert closed == [True]
        assert session.call(consume) == b"response"
    assert len(requests) == 2
    assert closed == [True, True]


def test_normal_early_response_exit_closes_without_cancellation_or_terminal_result():
    session, _, _, closed = session_fixture()

    async def early(transport):
        request = HttpRequest(TARGET, "GET", "data", service_id="evren-platform")
        async with transport.open(request, deadline=time.monotonic() + 2):
            return "closed-early"

    with session:
        assert session.call(early) == "closed-early"
        assert closed == [True]
        assert session.call(consume) == b"response"


@pytest.mark.parametrize("failure", [KeyboardInterrupt(), SystemExit(17), RuntimeError("consumer")])
def test_consumer_failure_preserves_identity_closes_response_and_runner(failure):
    session, _, _, closed = session_fixture()
    loops = []

    async def fail(transport):
        loops.append(asyncio.get_running_loop())
        request = HttpRequest(TARGET, "GET", "data", service_id="evren-platform")
        async with transport.open(request, deadline=time.monotonic() + 2):
            raise failure

    with pytest.raises(type(failure)) as caught, session:
        session.call(fail)
    assert caught.value is failure
    assert closed == [True]
    assert loops[0].is_closed()


@pytest.mark.parametrize("runner_close_failure", [False, True])
def test_close_error_is_reported_after_runner_is_closed(monkeypatch, runner_close_failure):
    loops = []
    close = asyncio.Runner.close

    def broken_close(runner):
        close(runner)
        if runner_close_failure:
            raise RuntimeError("secondary cleanup failure")

    monkeypatch.setattr(asyncio.Runner, "close", broken_close)

    class FailingClose(HttpxTransport):
        async def __aexit__(self, *args):
            loops.append(asyncio.get_running_loop())
            await super().__aexit__(*args)
            raise YorungeError("transport_failed")

    session = HttpSession(transport_factory=FailingClose)
    with pytest.raises(YorungeError) as caught, session:
        pass
    assert caught.value.code == "transport_failed"
    assert loops[0].is_closed()
    with pytest.raises(YorungeError) as caught:
        session.preflight()
    assert caught.value.code == "invalid_request"


@pytest.mark.parametrize("runner_close_failure", [False, True])
def test_close_failure_does_not_replace_known_operation_uncertainty(
    monkeypatch, runner_close_failure
):
    loops = []
    close = asyncio.Runner.close

    def broken_close(runner):
        close(runner)
        if runner_close_failure:
            raise RuntimeError("secondary cleanup failure")

    monkeypatch.setattr(asyncio.Runner, "close", broken_close)

    class FailingClose(HttpxTransport):
        async def __aexit__(self, *args):
            loops.append(asyncio.get_running_loop())
            await super().__aexit__(*args)
            raise YorungeError("transport_failed")

    failure = OperationError("operation_uncertain", str(uuid4()), reason_code="request_cancelled")
    session = HttpSession(transport_factory=FailingClose)
    with pytest.raises(OperationError) as caught, session:
        raise failure
    assert caught.value is failure
    assert caught.value.exit_code == 5
    assert loops[0].is_closed()


def test_failed_entry_closes_runner_and_transport_without_replacing_primary_error():
    loops, closures = [], []
    failure = YorungeError("transport_failed")

    class FailingEnter(HttpxTransport):
        async def __aenter__(self):
            loops.append(asyncio.get_running_loop())
            await super().__aenter__()
            raise failure

        async def __aexit__(self, *args):
            closures.append(True)
            await super().__aexit__(*args)
            raise YorungeError("invalid_response")

    session = HttpSession(transport_factory=FailingEnter)
    with pytest.raises(YorungeError) as caught:
        session.__enter__()
    assert caught.value is failure
    assert closures == [True]
    assert loops[0].is_closed()
    with pytest.raises(YorungeError) as caught:
        session.__enter__()
    assert caught.value.code == "invalid_request"


def test_runner_exit_finishes_pending_task_and_async_generator_cleanup():
    session, _, _, _ = session_fixture()
    cleanup, loops = [], []

    async def worker():
        try:
            await asyncio.Future()
        finally:
            cleanup.append("task")

    async def records():
        try:
            yield "one"
        finally:
            cleanup.append("generator")

    async def consume_with_pending_cleanup(transport):
        loop = asyncio.get_running_loop()
        loops.append(loop)
        task = asyncio.create_task(worker())
        stream = records()
        assert await anext(stream) == "one"
        await asyncio.sleep(0)
        return task, stream

    with session:
        task, stream = session.call(consume_with_pending_cleanup)
        assert cleanup == []
    assert task.cancelled()
    assert sorted(cleanup) == ["generator", "task"]
    assert loops[0].is_closed()


def test_real_sigint_cleans_up_then_becomes_keyboard_interrupt_in_sync_caller():
    source = """
import asyncio
import json
import signal
from yorunge.adapters.http_session import HttpSession

cleanup = []
loops = []
async def interrupt(transport):
    loops.append(asyncio.get_running_loop())
    try:
        signal.raise_signal(signal.SIGINT)
        await asyncio.sleep(0)
    finally:
        cleanup.append('consumer')

try:
    with HttpSession() as session:
        session.call(interrupt)
except KeyboardInterrupt:
    print(json.dumps({'cleanup': cleanup, 'loop_closed': loops[0].is_closed()}))
else:
    raise AssertionError('SIGINT was swallowed')
"""
    result = subprocess.run(
        [sys.executable, "-c", source], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == {"cleanup": ["consumer"], "loop_closed": True}


def test_shutdown_task_failure_is_private_and_becomes_controlled_transport_failure(caplog):
    session, _, _, _ = session_fixture()
    tasks, cleanup = [], []

    async def orphan():
        try:
            await asyncio.Future()
        finally:
            cleanup.append(True)
            raise RuntimeError(PRIVATE_CALLBACK)

    async def start(transport):
        tasks.append(asyncio.create_task(orphan()))
        await asyncio.sleep(0)

    with caplog.at_level(logging.DEBUG), pytest.raises(YorungeError) as caught, session:
        session.call(start)
    assert caught.value.code == "transport_failed"
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None
    assert cleanup == [True]
    assert tasks[0].done()
    assert PRIVATE_CALLBACK not in caplog.text
    assert PRIVATE_CALLBACK not in str(caught.value.envelope())


def test_callback_failure_closes_gate_before_next_consumer_and_keeps_logs_private(caplog):
    session, _, requests, _ = session_fixture()
    invoked = []

    def callback():
        raise RuntimeError(PRIVATE_CALLBACK)

    async def start(transport):
        asyncio.get_running_loop().call_soon(callback)
        await asyncio.sleep(0)
        return "not-published"

    def consumer(transport):
        invoked.append(True)
        return consume(transport)

    with caplog.at_level(logging.DEBUG):
        session.__enter__()
        try:
            with pytest.raises(YorungeError) as call_error:
                session.call(start)
            assert call_error.value.code == "transport_failed"
            assert call_error.value.__context__ is None
            for action in (session.preflight, lambda: session.call(consumer)):
                with pytest.raises(YorungeError) as caught:
                    action()
                assert caught.value.code == "transport_failed"
        finally:
            with pytest.raises(YorungeError) as close_error:
                session.__exit__(None, None, None)
    assert close_error.value.code == "transport_failed"
    assert invoked == []
    assert requests == []
    assert PRIVATE_CALLBACK not in caplog.text


def test_shutdown_callback_failure_preserves_known_operation_uncertainty(caplog):
    session, _, _, _ = session_fixture()
    tasks = []
    failure = OperationError("operation_uncertain", str(uuid4()), reason_code="request_cancelled")

    async def orphan():
        try:
            await asyncio.Future()
        finally:
            raise RuntimeError(PRIVATE_CALLBACK)

    async def start(transport):
        tasks.append(asyncio.create_task(orphan()))
        await asyncio.sleep(0)

    with caplog.at_level(logging.DEBUG), pytest.raises(OperationError) as caught, session:
        session.call(start)
        raise failure
    assert caught.value is failure
    assert caught.value.exit_code == 5
    assert tasks[0].done()
    assert PRIVATE_CALLBACK not in caplog.text


@pytest.mark.parametrize("custom_handler", [False, True])
def test_unrelated_loop_exception_handler_and_logging_are_unchanged(caplog, custom_handler):
    session, _, _, _ = session_fixture()
    unrelated = "unrelated-loop-failure-731294"
    handlers = []

    def callback():
        raise RuntimeError(unrelated)

    def original_handler(loop, context):
        handlers.append(loop)
        logging.getLogger("unrelated-loop").error(unrelated)

    async def other_loop():
        loop = asyncio.get_running_loop()
        if custom_handler:
            loop.set_exception_handler(original_handler)
        loop.call_soon(callback)
        await asyncio.sleep(0)
        assert loop.get_exception_handler() is (original_handler if custom_handler else None)

    with caplog.at_level(logging.ERROR), session:
        asyncio.run(other_loop())
        assert session.call(consume) == b"response"
    assert len(handlers) == custom_handler
    assert unrelated in caplog.text


@pytest.mark.parametrize("primary_uncertainty", [False, True])
def test_unreferenced_pending_task_survives_gc_for_private_shutdown(
    caplog, capsys, primary_uncertainty
):
    session, _, _, _ = session_fixture()
    cleanup = []
    failure = OperationError("operation_uncertain", str(uuid4()), reason_code="request_cancelled")

    async def orphan():
        try:
            await asyncio.Event().wait()
        finally:
            cleanup.append(True)
            raise RuntimeError(PRIVATE_CALLBACK)

    async def start(transport):
        # Deliberately retain no task, event, or future outside the task itself.
        asyncio.create_task(orphan())
        await asyncio.sleep(0)
        gc.collect()
        assert cleanup == []

    with caplog.at_level(logging.DEBUG), ExitStack() as lifetime:
        lifetime.enter_context(session)
        session.call(start)
        gc.collect()
        assert cleanup == []
        # Preparation errors are outside the assertion; target only shutdown.
        lifetime.pop_all()
        if primary_uncertainty:
            assert session.__exit__(type(failure), failure, None) is None
            observed = failure
        else:
            with pytest.raises(YorungeError) as caught:
                session.__exit__(None, None, None)
            observed = caught.value
    assert observed.code == ("operation_uncertain" if primary_uncertainty else "transport_failed")
    if primary_uncertainty:
        assert observed is failure
        assert observed.exit_code == 5
    assert cleanup == [True]
    gc.collect()
    captured = capsys.readouterr()
    assert PRIVATE_CALLBACK not in captured.err
    assert PRIVATE_CALLBACK not in captured.out
    assert PRIVATE_CALLBACK not in caplog.text


@pytest.mark.parametrize("prior_uncertainty", [False, True])
def test_base_exception_in_both_shutdown_phases_keeps_priority_and_closes_loop(
    monkeypatch, prior_uncertainty
):
    first, secondary = SystemExit(17), KeyboardInterrupt("secondary cleanup")
    primary = OperationError("operation_uncertain", str(uuid4()))
    closed = []
    original = asyncio.Runner.close

    def interrupted_close(runner):
        original(runner)
        closed.append(True)
        raise secondary

    class InterruptedTransport(HttpxTransport):
        async def __aexit__(self, *args):
            await super().__aexit__(*args)
            raise first

    monkeypatch.setattr(asyncio.Runner, "close", interrupted_close)
    session = HttpSession(transport_factory=InterruptedTransport)
    session.__enter__()
    loop = session._runner.get_loop()
    if prior_uncertainty:
        assert session.__exit__(type(primary), primary, None) is None
        assert primary.code == "operation_uncertain"
        assert primary.exit_code == 5
    else:
        with pytest.raises(SystemExit) as caught:
            session.__exit__(None, None, None)
        assert caught.value is first
    assert closed == [True]
    assert loop.is_closed()


def test_owned_task_factory_forwards_context_and_names():
    session, _, _, _ = session_fixture()
    value = contextvars.ContextVar("session-context", default="default")
    context = contextvars.copy_context()
    context.run(value.set, "explicit-context")

    async def child():
        return value.get(), asyncio.current_task().get_name()

    async def start(transport):
        task = asyncio.create_task(child(), name="explicit-name", context=context)
        return await task

    with session:
        assert session.call(start) == ("explicit-context", "explicit-name")


def test_completed_tasks_are_released_during_session_lifetime():
    session, _, _, _ = session_fixture()

    async def child():
        return "complete"

    async def start(transport):
        task = asyncio.create_task(child())
        reference = weakref.ref(task)
        assert await task == "complete"
        del task
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        gc.collect()
        assert reference() is None

    with session:
        session.call(start)
        assert session.call(consume) == b"response"
