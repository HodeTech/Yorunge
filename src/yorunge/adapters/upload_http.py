"""A budgeted transfer facade; service and storage share one owned client/pool."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import TypeVar

import httpx

from yorunge.adapters.guarded_http import GuardedHttpTransport
from yorunge.adapters.http_session import HttpSession
from yorunge.adapters.http_transport import _remaining, _Response, _ResponseContext
from yorunge.adapters.storage_transport import TransferHttpxTransport, _StorageResponse
from yorunge.adapters.upload_wire_meter import CURRENT_CALL, MeteredWireTransport, WireCall
from yorunge.application.http_transport import HttpCredential, HttpRequest, HttpTransport
from yorunge.application.operations import DispatchPermit
from yorunge.application.storage import StorageRequest
from yorunge.application.upload_budget import CallKind, UploadBudget, UploadReservation
from yorunge.domain.errors import YorungeError

T = TypeVar("T")
_SERVICE_EFFECTS: dict[str, CallKind] = {
    "create": "create",
    "project_link": "project_link",
    "presign": "presign",
    "confirm": "confirm",
}


def _permit(kind: CallKind, permit: DispatchPermit | None) -> None:
    if (kind == "read" and permit is not None) or (
        kind != "read" and type(permit) is not DispatchPermit
    ):
        raise YorungeError("invalid_request")


class UploadHttpxTransport(TransferHttpxTransport):
    def __init__(
        self,
        credential: HttpCredential,
        budget: UploadBudget,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if type(budget) is not UploadBudget:
            raise YorungeError("invalid_request")
        _ = budget.end
        self._budget = budget
        super().__init__(
            credential, transport=MeteredWireTransport(transport or GuardedHttpTransport(), budget)
        )

    @asynccontextmanager
    async def _call(
        self,
        request: HttpRequest | StorageRequest,
        reservation: UploadReservation,
        kind: CallKind,
        permit: DispatchPermit | None,
    ) -> AsyncIterator[None]:
        self._owner()
        if type(reservation) is not UploadReservation or CURRENT_CALL.get() is not None:
            raise YorungeError("invalid_request")
        _permit(kind, permit)
        reservation.require(
            self._budget,
            kind,
            request_bytes=len(request.content) if isinstance(request, HttpRequest) else 0,
            upload_bytes=request.size if isinstance(request, StorageRequest) else 0,
            response_bytes=request.max_bytes,
        )
        reservation.begin()
        token = CURRENT_CALL.set(WireCall(request, reservation, permit))
        try:
            yield
        finally:
            CURRENT_CALL.reset(token)
            reservation.finish()

    def open_budgeted(
        self,
        request: HttpRequest,
        reservation: UploadReservation,
        *,
        deadline: float,
        permit: DispatchPermit | None = None,
    ) -> _ResponseContext[_Response]:
        return _ResponseContext(self._service(request, reservation, deadline, permit))

    @asynccontextmanager
    async def _service(
        self,
        request: HttpRequest,
        reservation: UploadReservation,
        deadline: float,
        permit: DispatchPermit | None,
    ) -> AsyncIterator[_Response]:
        if type(request) is not HttpRequest or request.upload_endpoint is None:
            raise YorungeError("invalid_request")
        kind: CallKind
        if request.read_only:
            kind = "read"
        else:
            effect = _SERVICE_EFFECTS.get(request.upload_endpoint)
            if effect is None:
                raise YorungeError("invalid_request")
            kind = effect
        async with self._call(request, reservation, kind, permit):
            async with super().open(request, deadline=self._deadline(deadline)) as response:
                yield response

    def open_storage_budgeted(
        self,
        request: StorageRequest,
        reservation: UploadReservation,
        *,
        deadline: float,
        permit: DispatchPermit,
    ) -> _ResponseContext[_StorageResponse]:
        return _ResponseContext(self._storage(request, reservation, deadline, permit))

    @asynccontextmanager
    async def _storage(
        self,
        request: StorageRequest,
        reservation: UploadReservation,
        deadline: float,
        permit: DispatchPermit,
    ) -> AsyncIterator[_StorageResponse]:
        if type(request) is not StorageRequest:
            raise YorungeError("invalid_request")
        delegated = False
        try:
            async with self._call(request, reservation, "put", permit):
                end = self._deadline(deadline)
                context = super().open_storage(request, deadline=end)
                delegated = True
                async with context as response:
                    yield response
        finally:
            # The base facade owns source cleanup once entered. Before that,
            # close even a rejected lazy source in this same calling task.
            if not delegated:
                await request.source.aclose()

    def _deadline(self, deadline: float) -> float:
        # Validate the caller's value before min() can hide NaN or a bool.
        _remaining(deadline)
        return min(deadline, self._budget.end, time.monotonic() + 900.0)


class UploadSession(HttpSession):
    def __init__(
        self,
        credential: HttpCredential,
        budget: UploadBudget,
        *,
        transport_factory: Callable[[], UploadHttpxTransport] | None = None,
    ) -> None:
        self._budget = budget
        super().__init__(
            transport_factory=transport_factory
            or (lambda: UploadHttpxTransport(credential, budget))
        )

    def exchange(self, consumer: Callable[[UploadHttpxTransport], Awaitable[T]]) -> T:
        def consume(transport: HttpTransport) -> Awaitable[T]:
            if type(transport) is not UploadHttpxTransport or transport._budget is not self._budget:
                raise YorungeError("invalid_request")
            return consumer(transport)

        return self.call(consume)
