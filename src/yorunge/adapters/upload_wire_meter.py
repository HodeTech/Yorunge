"""Physical attempt/raw byte accounting inside the existing single HTTP pool."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextvars import ContextVar
from types import TracebackType

import httpx

from yorunge.adapters.storage_transport import _StorageBody
from yorunge.application.http_transport import HttpRequest
from yorunge.application.operations import DispatchPermit
from yorunge.application.storage import StorageRequest
from yorunge.application.upload_budget import UploadBudget, UploadReservation
from yorunge.domain.errors import YorungeError


class WireCall:
    def __init__(
        self,
        request: HttpRequest | StorageRequest,
        reservation: UploadReservation,
        permit: DispatchPermit | None,
    ) -> None:
        self.request, self.reservation, self.permit = request, reservation, permit

    def owner(self) -> None:
        self.reservation._owner()

    def accept(self, wire: httpx.Request) -> bool:
        self.reservation._current()
        request = self.request
        if type(request) not in (HttpRequest, StorageRequest):
            raise YorungeError("invalid_request")
        storage = type(request) is StorageRequest
        effect = storage or (isinstance(request, HttpRequest) and not request.read_only)
        if (effect and type(self.permit) is not DispatchPermit) or (
            not effect and self.permit is not None
        ):
            raise YorungeError("invalid_request")
        if isinstance(request, StorageRequest):
            expected = httpx.Request("PUT", request.target.wire_url, headers=request.wire_headers())
            valid_body = type(wire.stream) is _StorageBody and wire.stream.request is request
        else:
            expected = httpx.Request(
                request.method, request.url, headers=request.wire_headers(), content=request.content
            )
            try:
                valid_body = wire.content == request.content
            except httpx.RequestNotRead:
                valid_body = False
        if (
            wire.method != expected.method
            or str(wire.url) != str(expected.url)
            or wire.headers != expected.headers
            or not valid_body
        ):
            raise YorungeError("invalid_request")
        if self.permit is not None:
            self.permit.consume()
        self.reservation.attempt()
        return storage

    def __repr__(self) -> str:
        return "<upload wire call private>"


CURRENT_CALL: ContextVar[WireCall | None] = ContextVar("yorunge_upload_wire_call", default=None)


class _CountedStream(httpx.AsyncByteStream):
    def __init__(self, source: httpx.AsyncByteStream, call: WireCall, *, upload: bool) -> None:
        self._source, self._call, self._upload = source, call, upload
        self._iterator: AsyncIterator[bytes] | None = None

    def __aiter__(self) -> AsyncIterator[bytes]:
        self._call.owner()
        if self._iterator is not None:
            raise YorungeError("invalid_request")
        self._iterator = self._source.__aiter__()
        return self

    async def __anext__(self) -> bytes:
        self._call.owner()
        if self._iterator is None:
            raise YorungeError("invalid_request")
        chunk = await anext(self._iterator)
        if type(chunk) is not bytes:
            raise YorungeError("invalid_response")
        if self._upload:
            self._call.reservation.upload(len(chunk))
        else:
            self._call.reservation.response(len(chunk))
        return chunk

    async def aclose(self) -> None:
        self._call.owner()
        await self._source.aclose()


class MeteredWireTransport(httpx.AsyncBaseTransport):
    def __init__(self, delegate: httpx.AsyncBaseTransport, budget: UploadBudget) -> None:
        self._delegate, self._budget = delegate, budget

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        call = CURRENT_CALL.get()
        if type(call) is not WireCall or call.reservation._budget is not self._budget:
            raise YorungeError("invalid_request")
        storage = call.accept(request)
        if storage:
            if not isinstance(request.stream, httpx.AsyncByteStream):
                raise YorungeError("invalid_request")
            request.stream = _CountedStream(request.stream, call, upload=True)
        response = await self._delegate.handle_async_request(request)
        if not isinstance(response.stream, httpx.AsyncByteStream):
            raise YorungeError("invalid_response")
        response.stream = _CountedStream(response.stream, call, upload=False)
        return response

    async def __aenter__(self) -> MeteredWireTransport:
        await self._delegate.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        await self._delegate.__aexit__(exc_type, exc, traceback)

    async def aclose(self) -> None:
        await self._delegate.aclose()
