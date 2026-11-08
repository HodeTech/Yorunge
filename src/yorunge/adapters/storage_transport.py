"""Transfer facade: one existing owned HTTP client/pool for service and storage."""

from __future__ import annotations

import asyncio
import hashlib
import sys
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TypeVar

import httpx

from yorunge.adapters.guarded_http import GuardedHttpTransport
from yorunge.adapters.http_session import HttpSession
from yorunge.adapters.http_transport import (
    HttpxTransport,
    _private_logs,
    _remaining,
    _Response,
    _ResponseContext,
)
from yorunge.application.download_transport import DownloadRequest, DownloadTransport
from yorunge.application.http_transport import HttpCredential, HttpRequest, HttpTransport
from yorunge.application.storage import (
    STORAGE_CHUNK_BYTES,
    StorageRequest,
    StorageTransport,
)
from yorunge.application.upload_progress import source_chunk
from yorunge.domain.capabilities import instant
from yorunge.domain.credentials import normalize_target
from yorunge.domain.download_response import (
    Disposition,
    DownloadResponse,
    body_failure,
    check_body_end,
    disposition,
    parse_response,
)
from yorunge.domain.errors import ErrorCode, YorungeError

T = TypeVar("T")


def _origins(values: tuple[str, ...]) -> tuple[str, ...]:
    if type(values) is not tuple or len(values) > 1:
        raise YorungeError("invalid_service_target")
    for value in values:
        target = normalize_target(value)
        if target.service_origin != value or target.api_base_path != "/":
            raise YorungeError("invalid_service_target")
    return values


class _StorageBody(httpx.AsyncByteStream):
    def __init__(self, request: StorageRequest, deadline: float) -> None:
        self.request, self.deadline = request, deadline
        self.iterator: AsyncIterator[bytes] | None = None
        self.count, self.digest, self.complete = 0, hashlib.sha256(), False
        self.task: asyncio.Task[object] | None = None

    def __aiter__(self) -> AsyncIterator[bytes]:
        if self.iterator is not None:
            raise YorungeError("invalid_request")
        self.task = asyncio.current_task()
        self.iterator = self.request.source.chunks()
        return self

    async def __anext__(self) -> bytes:
        if self.iterator is None or self.task is not asyncio.current_task():
            raise YorungeError("invalid_request")
        _remaining(self.deadline)
        try:
            chunk = await anext(self.iterator)
        except StopAsyncIteration:
            source = self.request.source
            if (
                self.count != self.request.size
                or self.digest.hexdigest() != self.request.sha256
                or source.complete is not True
                or source.sent_bytes != self.count
                or source.sent_sha256 != self.request.sha256
            ):
                raise YorungeError("input_changed") from None
            self.complete = True
            raise
        _remaining(self.deadline)
        if type(chunk) is not bytes or not 1 <= len(chunk) <= STORAGE_CHUNK_BYTES:
            raise YorungeError("input_invalid")
        self.count += len(chunk)
        if self.count > self.request.size:
            raise YorungeError("input_changed")
        self.digest.update(chunk)
        source_chunk(len(chunk))
        return chunk

    async def aclose(self) -> None:
        if self.task is not None and self.task is not asyncio.current_task():
            raise YorungeError("invalid_request")
        await self.request.source.aclose()


class _StorageResponse(_Response):
    def __init__(
        self, response: httpx.Response, request: StorageRequest, body: _StorageBody
    ) -> None:
        super().__init__(response, request)
        self.sent_bytes, self.sent_sha256 = body.count, body.digest.hexdigest()


def _disarm(window: asyncio.Timeout) -> None:
    """A whole body ends the transport's deadline: the caller's completion work is not timed."""
    try:
        window.reschedule(None)
    except RuntimeError:
        pass  # the deadline struck in the same instant: the cancellation reports it as it is


class _DownloadChunks(AsyncIterator[bytes]):
    """The body of an accepted answer, by the closed rules of the download.

    A cut connection is ``download_incomplete``, the body-phase size cap is
    ``download_limit_exceeded`` and a timeout keeps its code; the end of the body must be the whole
    of what the framing promised (``Content-Length`` reached, or the chunked terminator seen).
    """

    def __init__(self, view: _DownloadView, inner: AsyncIterator[bytes]) -> None:
        self._view, self._inner = view, inner

    async def __anext__(self) -> bytes:
        view = self._view
        try:
            chunk = await anext(self._inner)
        except StopAsyncIteration:
            response = view.response
            assert response.framing is not None
            check_body_end(
                response.framing, response.content_length, view.received, terminated=True
            )
            view.finish()  # the body is whole: what follows is not the transport's to time out
            raise
        except YorungeError as error:
            raise YorungeError(body_failure(error.code)) from None
        view.received += len(chunk)
        return chunk


class _DownloadView(_Response):
    def __init__(
        self,
        response: httpx.Response,
        request: DownloadRequest,
        typed: DownloadResponse,
        action: Disposition,
    ) -> None:
        super().__init__(response, request)
        self.response, self.disposition, self.received = typed, action, 0
        self.complete = False
        self._disarm: Callable[[], None] | None = None

    def finish(self) -> None:
        """The body was read to its end and checked: the deadline is over for the caller's tail."""
        self.complete = True
        if self._disarm is not None:
            self._disarm()

    def chunks(self) -> AsyncIterator[bytes]:
        if self.response.framing is None:  # a 416 has no body the engine may read
            raise YorungeError("invalid_request")
        return _DownloadChunks(self, super().chunks())


class TransferHttpxTransport(HttpxTransport):
    def __init__(
        self,
        credential: HttpCredential,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        utc_clock: Callable[[], datetime] | None = None,
        storage_origins: tuple[str, ...] = (),
    ) -> None:
        if (
            type(credential) is not HttpCredential
            or credential.service_id != "evren-platform"
            or credential.header_name.lower() != "x-api-key"
            or credential.prefix != ""
        ):
            raise YorungeError("invalid_credential")
        self._credential = credential
        self._storage_origins = _origins(storage_origins)
        self._utc_clock = utc_clock or (lambda: datetime.now(UTC))
        super().__init__(transport=transport or GuardedHttpTransport())

    def open(self, request: HttpRequest, *, deadline: float) -> _ResponseContext[_Response]:
        if (
            type(request) is not HttpRequest
            or request.service_id != "evren-platform"
            or request.target != self._credential.target
            or request.credential is not self._credential
        ):
            raise YorungeError("invalid_service_target")
        return super().open(request, deadline=deadline)

    def open_storage(
        self, request: StorageRequest, *, deadline: float
    ) -> _ResponseContext[_StorageResponse]:
        return _ResponseContext(self._open_storage(request, deadline=deadline))

    def open_download(
        self, request: DownloadRequest, *, deadline: float
    ) -> _ResponseContext[_DownloadView]:
        return _ResponseContext(self._open_download(request, deadline=deadline))

    def _download_window(self, request: DownloadRequest, deadline: float) -> float:
        """The GET's own window: the caller's whole deadline, not the PUT's 120 s."""
        remaining = _remaining(deadline)
        if (
            type(request) is not DownloadRequest
            or request.selected_secret is not self._credential.secret
            or request.target.origin not in self._storage_origins
        ):
            raise YorungeError("invalid_service_target")
        return time.monotonic() + remaining

    @staticmethod
    def _wire_download(request: DownloadRequest, deadline: float) -> httpx.Request:
        remaining = _remaining(deadline)
        wire = httpx.Request(
            "GET",
            request.target.wire_url,
            headers=request.wire_headers(),
            extensions={
                "timeout": httpx.Timeout(min(5.0, remaining), pool=min(1.0, remaining)).as_dict()
            },
        )
        if str(wire.url) != request.target.wire_url:
            raise YorungeError("invalid_service_target")
        # The wire must be the described request and nothing more: a signed address is sent no
        # credential, so what is described and what is sent are one list.
        expected = {name.lower(): value for name, value in request.public_headers()}
        actual = {
            name.lower(): value
            for name, value in wire.headers.multi_items()
            if name.lower() != "host"
        }
        if (
            expected != actual
            or len(wire.headers) != len(expected) + 1
            or wire.headers.get_list("host") != [request.target.origin[8:]]
        ):
            raise YorungeError("invalid_service_target")
        return wire

    @staticmethod
    def _download_headers(response: httpx.Response) -> None:
        if (
            len(response.headers) > 64
            or sum(len(k) + len(v) for k, v in response.headers.raw) > 65536
            or any(len(k) > 128 or len(v) > 16384 for k, v in response.headers.raw)
        ):
            raise YorungeError("invalid_response")

    @asynccontextmanager
    async def _open_download(
        self, request: DownloadRequest, *, deadline: float
    ) -> AsyncIterator[_DownloadView]:
        self._owner()
        if self._closed or self._client is None or type(request) is not DownloadRequest:
            raise YorungeError("invalid_request")
        response: httpx.Response | None = None
        view: _DownloadView | None = None
        acquired = False
        failure: ErrorCode | None = None
        public_error: YorungeError | None = None
        with _private_logs():
            try:
                deadline = self._download_window(request, deadline)
                async with asyncio.timeout(_remaining(deadline)) as window:
                    async with asyncio.timeout(min(1.0, _remaining(deadline))):
                        await self._slots.acquire()
                    acquired = True
                    deadline = min(deadline, self._download_window(request, deadline))
                    window.reschedule(asyncio.get_running_loop().time() + _remaining(deadline))
                    wire = self._wire_download(request, deadline)
                    # One physical GET: no retry, no redirect, no credential, whatever the answer.
                    response = await self._client.send(
                        wire, stream=True, auth=None, follow_redirects=False
                    )
                    self._responses.add(response)
                    self._download_headers(response)
                    typed = parse_response(response.status_code, response.headers.multi_items())
                    view = _DownloadView(response, request, typed, disposition(typed, request.ask))
                    view._disarm = lambda: _disarm(window)
                    yield view
                    if not view.complete:
                        _remaining(deadline)
            except (TimeoutError, httpx.TimeoutException):
                failure = "transport_timeout"
            except httpx.InvalidURL:
                failure = "invalid_request"
            except httpx.HTTPError:
                failure = "transport_failed"
            except YorungeError as error:
                public_error = error
            finally:
                pending = sys.exc_info()[0] is not None
                close_failed = await self._release(response, view, acquired)
                if close_failed and not pending and failure is None and public_error is None:
                    failure = "transport_failed"
        if public_error is not None:
            public_error.__context__ = public_error.__cause__ = None
            raise public_error
        if failure is not None:
            raise YorungeError(failure)

    def _window(self, request: StorageRequest, deadline: float) -> float:
        remaining = _remaining(deadline)
        if (
            type(request) is not StorageRequest
            or request.selected_secret is not self._credential.secret
            or (request.target.mode == "proxy" and request.credential is not self._credential)
            or (
                request.target.mode == "direct"
                and request.target.origin not in self._storage_origins
            )
        ):
            raise YorungeError("invalid_service_target")
        if (request.source.size, request.source.sha256) != (request.size, request.sha256):
            raise YorungeError("input_changed")
        end = time.monotonic() + min(120.0, remaining)
        if request.target.expires_at is not None:
            now = self._utc_clock()
            if now.tzinfo is None or now.utcoffset() is None:
                raise YorungeError("invalid_request")
            end = min(
                end,
                time.monotonic() + (instant(request.target.expires_at) - now).total_seconds() - 5.0,
            )
        _remaining(end)
        return end

    @staticmethod
    def _wire_storage(
        request: StorageRequest, body: _StorageBody, deadline: float
    ) -> httpx.Request:
        remaining = _remaining(deadline)
        wire = httpx.Request(
            "PUT",
            request.target.wire_url,
            headers=request.wire_headers(),
            content=body,
            extensions={
                "timeout": httpx.Timeout(min(5.0, remaining), pool=min(1.0, remaining)).as_dict()
            },
        )
        # Keep HTTPX's prepared headers, but expose our public AsyncByteStream
        # directly instead of its content= convenience iterator wrapper.
        wire.stream = body
        if str(wire.url) != request.target.wire_url:
            raise YorungeError("invalid_service_target")
        expected = {name.lower(): value for name, value in request.wire_headers()}
        actual = {
            name.lower(): value
            for name, value in wire.headers.multi_items()
            if name.lower() != "host"
        }
        if (
            expected != actual
            or len(wire.headers) != len(expected) + 1
            or wire.headers.get_list("host") != [request.target.origin[8:]]
        ):
            raise YorungeError("invalid_service_target")
        return wire

    @asynccontextmanager
    async def _open_storage(
        self, request: StorageRequest, *, deadline: float
    ) -> AsyncIterator[_StorageResponse]:
        self._owner()
        if self._closed or self._client is None or type(request) is not StorageRequest:
            raise YorungeError("invalid_request")
        response: httpx.Response | None = None
        view: _StorageResponse | None = None
        body = _StorageBody(request, deadline)
        acquired = False
        failure: ErrorCode | None = None
        public_error: YorungeError | None = None
        with _private_logs():
            try:
                deadline = self._window(request, deadline)
                body.deadline = deadline
                async with asyncio.timeout(_remaining(deadline)) as window:
                    async with asyncio.timeout(min(1.0, _remaining(deadline))):
                        await self._slots.acquire()
                    acquired = True
                    deadline = min(deadline, self._window(request, deadline))
                    body.deadline = deadline
                    window.reschedule(asyncio.get_running_loop().time() + _remaining(deadline))
                    wire = self._wire_storage(request, body, deadline)
                    # Unlike service GETs, even connection refusal/429/5xx never
                    # starts another physical PUT or refreshes a signed URL.
                    response = await self._client.send(
                        wire, stream=True, auth=None, follow_redirects=False
                    )
                    self._responses.add(response)
                    self._view(response, request)
                    if not body.complete:
                        raise YorungeError("invalid_response")
                    view = _StorageResponse(response, request, body)
                    yield view
                    _remaining(deadline)
            except (TimeoutError, httpx.TimeoutException):
                failure = "transport_timeout"
            except httpx.InvalidURL:
                failure = "invalid_request"
            except httpx.HTTPError:
                failure = "transport_failed"
            except YorungeError as error:
                public_error = error
            finally:
                pending = sys.exc_info()[0] is not None
                close_failed = await self._release(response, view, acquired)
                try:
                    await body.aclose()
                except (OSError, httpx.HTTPError, YorungeError):
                    close_failed = True
                if close_failed and not pending and failure is None and public_error is None:
                    failure = "transport_failed"
        if public_error is not None:
            public_error.__context__ = public_error.__cause__ = None
            raise public_error
        if failure is not None:
            raise YorungeError(failure)


class TransferSession(HttpSession):
    """Typed facade over the inherited one Runner/client; no second owned loop."""

    def __init__(
        self,
        credential: HttpCredential,
        *,
        transport_factory: Callable[[], TransferHttpxTransport] | None = None,
        storage_origins: tuple[str, ...] = (),
    ) -> None:
        self._storage_origins = _origins(storage_origins)
        super().__init__(
            transport_factory=transport_factory
            or (lambda: TransferHttpxTransport(credential, storage_origins=self._storage_origins))
        )

    def exchange(self, consumer: Callable[[StorageTransport], Awaitable[T]]) -> T:
        def consume(transport: HttpTransport) -> Awaitable[T]:
            if (
                not isinstance(transport, TransferHttpxTransport)
                or transport._storage_origins != self._storage_origins
            ):
                raise YorungeError("invalid_request")
            return consumer(transport)

        return self.call(consume)

    def download(self, consumer: Callable[[DownloadTransport], Awaitable[T]]) -> T:
        """The same one client and pool, for the signed GET."""

        def consume(transport: HttpTransport) -> Awaitable[T]:
            if (
                not isinstance(transport, TransferHttpxTransport)
                or transport._storage_origins != self._storage_origins
            ):
                raise YorungeError("invalid_request")
            return consumer(transport)

        return self.call(consume)
