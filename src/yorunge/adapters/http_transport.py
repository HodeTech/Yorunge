"""Owned HTTP/1.1 byte transport; endpoint semantics stay in application adapters."""

from __future__ import annotations

import asyncio
import logging
import math
import os
import random
import ssl
import sys
import threading
import time
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from http.cookiejar import Cookie, CookieJar, DefaultCookiePolicy
from types import TracebackType
from urllib.request import Request

import httpx

from yorunge.application.http_transport import (
    CHUNK_SIZE,
    HttpRequest,
    HttpStatusFailure,
)
from yorunge.domain.errors import YorungeError

_PRIVATE_HTTP: ContextVar[bool] = ContextVar("yorunge_private_http", default=False)
_TRANSIENT = frozenset({408, 429, 502, 503, 504})


class _PrivateLogs(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not _PRIVATE_HTTP.get()


_LOG_FILTER = _PrivateLogs()
_LOG_LOCK = threading.Lock()


@contextmanager
def _private_logs() -> Iterator[None]:
    # Logger filters, rather than global levels/handlers, leave unrelated callers intact.
    names = {"httpx", "httpcore"} | {
        name for name in tuple(logging.Logger.manager.loggerDict) if name.startswith("httpcore.")
    }
    # Keep one inert filter installed: removing filters during another session's
    # logging iteration could skip the remaining filter and expose its record.
    with _LOG_LOCK:
        for name in names:
            logging.getLogger(name).addFilter(_LOG_FILTER)
    token = _PRIVATE_HTTP.set(True)
    try:
        yield
    finally:
        _PRIVATE_HTTP.reset(token)


class _NoCookies(DefaultCookiePolicy):
    def set_ok(self, cookie: Cookie, request: Request) -> bool:
        return False

    def return_ok(self, cookie: Cookie, request: Request) -> bool:
        return False


def _remaining(deadline: float) -> float:
    if type(deadline) not in (int, float) or not math.isfinite(deadline):
        raise YorungeError("invalid_request")
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise YorungeError("transport_timeout")
    return remaining


def _retry_wait(value: str | None) -> float:
    jitter = random.uniform(0.0, 0.25)
    if value is None or len(value) > 128 or not value.isascii():
        return jitter
    if value.isdigit():
        return max(jitter, float(int(value)))
    try:
        when = parsedate_to_datetime(value)
        if when.tzinfo is None or when.utcoffset() is None:
            return jitter
        return max(jitter, (when.astimezone(UTC) - datetime.now(UTC)).total_seconds())
    except (ValueError, TypeError, OverflowError):
        return jitter


def _tls_failure(error: BaseException) -> bool:
    seen: set[int] = set()
    while id(error) not in seen:
        seen.add(id(error))
        if isinstance(error, ssl.SSLError):
            return True
        cause = error.__cause__ or error.__context__
        if cause is None:
            return False
        error = cause
    return False


class _Response:
    def __init__(self, response: httpx.Response, request: HttpRequest) -> None:
        self.status_code = response.status_code
        self.headers = tuple(response.headers.multi_items())
        self._response, self._request = response, request
        self._task = asyncio.current_task()
        self._closed, self._used = False, False

    async def chunks(self) -> AsyncIterator[bytes]:
        if self._closed or self._used or asyncio.current_task() is not self._task:
            raise YorungeError("invalid_request")
        self._used = True
        size = 0
        async for chunk in self._response.aiter_raw(chunk_size=CHUNK_SIZE):
            size += len(chunk)
            if size > self._request.max_bytes:
                raise YorungeError("invalid_response")
            yield chunk


class HttpxTransport:
    """An explicit loop/thread/PID-owned session; each response also owns its task."""

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        # Injection is for trusted composition/tests, never a config/CLI policy bypass.
        self._transport = transport
        self._client: httpx.AsyncClient | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread, self._pid = threading.get_ident(), os.getpid()
        self._closed = False
        self._responses: set[httpx.Response] = set()
        self._slots = asyncio.Semaphore(2)

    async def __aenter__(self) -> HttpxTransport:
        if self._closed or self._client is not None:
            raise YorungeError("invalid_request")
        self._owner()
        try:
            self._client = httpx.AsyncClient(
                transport=self._transport
                or httpx.AsyncHTTPTransport(
                    retries=0,
                    trust_env=False,
                    limits=httpx.Limits(max_connections=2, max_keepalive_connections=2),
                ),
                trust_env=False,
                follow_redirects=False,
                cookies=CookieJar(policy=_NoCookies()),
                auth=None,
                http2=False,
            )
            await self._client.__aenter__()
        except (OSError, httpx.HTTPError):
            self._closed = True
            raise YorungeError("transport_failed") from None
        return self

    def _owner(self) -> None:
        if self._thread != threading.get_ident() or self._pid != os.getpid():
            raise YorungeError("invalid_request")
        loop = asyncio.get_running_loop()
        if self._loop is None:
            self._loop = loop
        elif self._loop is not loop:
            raise YorungeError("invalid_request")

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._owner()
        self._closed = True
        client = self._client
        if client is not None:
            with _private_logs():
                failed = False
                try:
                    for response in tuple(self._responses):
                        try:
                            await response.aclose()
                        except (OSError, httpx.HTTPError):
                            failed = True
                    try:
                        await client.aclose()
                    except (OSError, httpx.HTTPError):
                        failed = True
                finally:
                    client.cookies.clear()
                if failed and exc is None:
                    raise YorungeError("transport_failed") from None

    async def _pause(self, delay: float, deadline: float) -> bool:
        if delay >= _remaining(deadline):
            return False
        await asyncio.sleep(delay)
        return True

    async def _send(self, request: HttpRequest, deadline: float) -> httpx.Response:
        client = self._client
        assert client is not None
        attempts = 2 if request.read_only else 1
        for attempt in range(attempts):
            remaining = _remaining(deadline)
            timeout = httpx.Timeout(
                min(5.0, remaining), connect=min(5.0, remaining), pool=min(1.0, remaining)
            )
            wire = httpx.Request(
                request.method,
                request.url,
                headers=request.wire_headers(),
                content=request.content,
                extensions={"timeout": timeout.as_dict()},
            )
            if str(wire.url) != request.url:
                raise YorungeError("invalid_service_target")
            try:
                response = await client.send(wire, stream=True, auth=None, follow_redirects=False)
            except (httpx.ConnectError, httpx.ConnectTimeout) as error:
                if (
                    attempt + 1 < attempts
                    and not _tls_failure(error)
                    and await self._pause(_retry_wait(None), deadline)
                ):
                    continue
                raise
            finally:
                client.cookies.clear()
            if response.status_code in _TRANSIENT and attempt + 1 < attempts:
                wait = _retry_wait(response.headers.get("retry-after"))
                await response.aclose()
                if await self._pause(wait, deadline):
                    continue
                raise HttpStatusFailure(response.status_code)
            return response
        raise AssertionError("bounded attempts exhausted")

    @asynccontextmanager
    async def open(self, request: HttpRequest, *, deadline: float) -> AsyncIterator[_Response]:
        self._owner()
        if self._closed or self._client is None or not isinstance(request, HttpRequest):
            raise YorungeError("invalid_request")
        remaining = _remaining(deadline)
        # Loop clocks need not share time.monotonic's epoch.
        end = asyncio.get_running_loop().time() + remaining
        response: httpx.Response | None = None
        view: _Response | None = None
        acquired = False
        with _private_logs():
            try:
                async with asyncio.timeout_at(end):
                    async with asyncio.timeout(min(1.0, _remaining(deadline))):
                        await self._slots.acquire()
                    acquired = True
                    response = await self._send(request, deadline)
                    self._responses.add(response)
                    if not 200 <= response.status_code < 300:
                        raise HttpStatusFailure(response.status_code)
                    if (
                        len(response.headers) > 64
                        or sum(len(k) + len(v) for k, v in response.headers.raw) > 65536
                        or any(len(k) > 128 or len(v) > 16384 for k, v in response.headers.raw)
                    ):
                        raise YorungeError("invalid_response")
                    encoding = response.headers.get("content-encoding", "identity")
                    if encoding.lower().strip() != "identity":
                        raise YorungeError("invalid_response")
                    view = _Response(response, request)
                    yield view
                    _remaining(deadline)
            except (TimeoutError, httpx.TimeoutException):
                raise YorungeError("transport_timeout") from None
            except httpx.HTTPError:
                raise YorungeError("transport_failed") from None
            finally:
                pending_error = sys.exc_info()[0] is not None
                close_failed = False
                if view is not None:
                    view._closed = True
                try:
                    if response is not None:
                        try:
                            await response.aclose()
                        except (OSError, httpx.HTTPError):
                            close_failed = True
                        finally:
                            self._responses.discard(response)
                finally:
                    self._client.cookies.clear()
                    if acquired:
                        self._slots.release()
                if close_failed and not pending_error:
                    raise YorungeError("transport_failed") from None
