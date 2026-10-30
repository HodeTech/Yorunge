"""A synchronous owner for complete exchanges on one private async HTTP session."""

from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import Awaitable, Callable, Coroutine, Generator
from types import TracebackType
from typing import Any, TypeVar

from yorunge.adapters.http_transport import HttpxTransport
from yorunge.application.http_transport import HttpTransport
from yorunge.domain.errors import YorungeError

T = TypeVar("T")


def _active_loop() -> bool:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


class HttpSession:
    """Own a Runner and pool; each call must finish its response in its own task.

    The factory is a trusted composition seam, never a user configuration option.
    Construction does not create a client, loop, thread, or network connection.
    """

    def __init__(self, *, transport_factory: Callable[[], HttpxTransport] = HttpxTransport) -> None:
        self._factory = transport_factory
        self._thread, self._pid = threading.get_ident(), os.getpid()
        self._runner: asyncio.Runner | None = None
        self._transport: HttpxTransport | None = None
        self._entered, self._closed, self._busy = False, False, False
        self._loop_failed = False
        self._tasks: set[asyncio.Task[Any]] = set()

    def _owner(self) -> None:
        if (
            self._thread != threading.get_ident()
            or self._pid != os.getpid()
            or self._busy
            or _active_loop()
        ):
            raise YorungeError("invalid_request")

    def _available(self) -> None:
        self._owner()
        if not self._entered or self._closed:
            raise YorungeError("invalid_request")

    def _check_loop(self) -> None:
        if self._loop_failed:
            raise YorungeError("transport_failed")

    def _loop_failure(self, loop: asyncio.AbstractEventLoop, context: object) -> None:
        # The default handler logs raw callback/task exceptions and their repr.
        # Keep no private context; this handler belongs only to this owned loop.
        self._loop_failed = True

    def _task_factory(
        self,
        loop: asyncio.AbstractEventLoop,
        coroutine: Coroutine[Any, Any, T] | Generator[Any, None, T],
        **kwargs: Any,
    ) -> asyncio.Task[T]:
        # asyncio itself keeps only weak task references. Retain pending tasks so
        # GC cannot close an orphan coroutine outside the private loop handler.
        # Forward runtime keywords (including context/name on newer Python).
        task = asyncio.Task(coroutine, loop=loop, **kwargs)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def preflight(self) -> None:
        """Reject unusable composition before its caller resolves credentials/state."""
        self._available()
        self._check_loop()

    def __enter__(self) -> HttpSession:
        self._owner()
        if self._entered or self._closed:
            raise YorungeError("invalid_request")
        self._busy = True
        try:
            self._runner = asyncio.Runner()
            loop = self._runner.get_loop()
            loop.set_exception_handler(self._loop_failure)
            loop.set_task_factory(self._task_factory)
            self._transport = self._factory()
            self._runner.run(self._transport.__aenter__())
            self._check_loop()
        except BaseException as error:
            self._closed = True
            self._close(type(error), error, error.__traceback__)
            raise
        finally:
            self._busy = False
        self._entered = True
        return self

    def call(self, consumer: Callable[[HttpTransport], Awaitable[T]]) -> T:
        """Run one entire exchange; create no consumer awaitable on gate rejection."""
        self.preflight()
        runner, transport = self._runner, self._transport
        assert runner is not None and transport is not None

        async def consume() -> T:
            return await consumer(transport)

        self._busy = True
        try:
            result = runner.run(consume())
        finally:
            self._busy = False
        self._check_loop()
        return result

    def _close(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        runner, transport = self._runner, self._transport
        if runner is None:
            return
        failure: BaseException | None = None
        try:
            if transport is not None:
                runner.run(transport.__aexit__(exc_type, exc, traceback))
        except BaseException as error:
            failure = error
        finally:
            try:
                runner.close()
            except BaseException as error:
                if failure is None:
                    failure = error
            finally:
                self._tasks.clear()
                self._runner, self._transport = None, None
        # Neither cleanup phase replaces a prior operation/commit uncertainty;
        # absent one, retain the first close failure while still closing the loop.
        if exc is None:
            self._check_loop()
            if failure is not None:
                raise failure

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._available()
        self._entered, self._closed, self._busy = False, True, True
        try:
            self._close(exc_type, exc, traceback)
        finally:
            self._busy = False
