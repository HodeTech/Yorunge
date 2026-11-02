"""Volatile original-invocation quotas; neither authority nor a dispatch permit."""

from __future__ import annotations

import asyncio
import math
import os
import threading
import time
from dataclasses import dataclass
from typing import Literal, NoReturn

from pydantic import ValidationError

from yorunge.domain.dataset_transfer import StageKind
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_costs import UploadRequestLimits

CallKind = StageKind | Literal["read"]
_EFFECTS = ("create", "project_link", "presign", "put", "confirm")
_KINDS = (*_EFFECTS, "read")


def _quantity(value: int, maximum: int) -> None:
    if type(value) is not int or not 0 <= value <= maximum:
        raise YorungeError("invalid_request")


def _loop() -> asyncio.AbstractEventLoop | None:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


@dataclass(frozen=True, slots=True)
class UploadCounters:
    """Only numbers; reserved byte totals are not bytes accepted by a server."""

    read_requests: int
    read_attempts: int
    create_requests: int
    project_link_requests: int
    presign_requests: int
    put_requests: int
    confirm_requests: int
    effect_attempts: int
    control_request_reserved: int
    upload_reserved: int
    response_pending: int
    control_request_bytes: int
    upload_bytes: int
    response_bytes: int


class _PrivateQuota:
    def __copy__(self) -> NoReturn:
        raise TypeError("upload quota cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        raise TypeError("upload quota cannot be copied")

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("upload quota cannot be serialized")

    def __repr__(self) -> str:
        return "<upload quota private>"


class UploadBudget(_PrivateQuota):
    def __init__(self, limits: UploadRequestLimits, *, end: float, read_only: bool) -> None:
        valid_limits = None
        if type(limits) is UploadRequestLimits:
            try:
                valid_limits = UploadRequestLimits.model_validate(limits.model_dump())
            except ValidationError:
                pass
        if valid_limits is None or type(read_only) is not bool:
            raise YorungeError("invalid_request")
        now = time.monotonic()
        valid_end = type(end) in (int, float)
        try:
            valid_end = valid_end and math.isfinite(end) and 0 < end - now <= 900.0
        except OverflowError:
            valid_end = False
        if not valid_end:
            raise YorungeError("invalid_request")
        self._limits, self._end, self._readonly = valid_limits, float(end), read_only
        self._pid, self._thread = os.getpid(), threading.get_ident()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._requests = dict.fromkeys(_KINDS, 0)
        self._request_reserved = self._upload_reserved = self._response_pending = 0
        self._read_attempts = self._effect_attempts = 0
        self._request_bytes = self._upload_bytes = self._response_bytes = 0
        self._live: set[UploadReservation] = set()

    def _owner(self) -> None:
        loop = _loop()
        if (
            os.getpid() != self._pid
            or threading.get_ident() != self._thread
            or (loop is not None and self._loop is not None and loop is not self._loop)
        ):
            raise YorungeError("invalid_request")

    def _current(self) -> None:
        self._owner()
        if time.monotonic() >= self._end:
            raise YorungeError("execution_timeout")

    @property
    def end(self) -> float:
        self._current()
        return self._end

    def reserve(
        self,
        kind: CallKind,
        *,
        request_bytes: int = 0,
        upload_bytes: int = 0,
        response_bytes: int = 1_048_576,
    ) -> UploadReservation:
        self._current()
        if type(kind) is not str or kind not in _KINDS:
            raise YorungeError("invalid_request")
        _quantity(request_bytes, 1_048_576)
        _quantity(upload_bytes, 500_000_000)
        _quantity(response_bytes, 65_536 if kind == "put" else 1_048_576)
        if (
            (kind == "read" and (request_bytes != 0 or upload_bytes != 0))
            or (kind != "put" and upload_bytes != 0)
            or (kind == "put" and request_bytes != 0)
            or (self._readonly and kind != "read")
        ):
            raise YorungeError("invalid_request")
        limits = self._limits
        maximum = limits.max_read_requests if kind == "read" else getattr(limits, "max_" + kind)
        if (
            self._requests[kind] >= maximum
            or self._request_reserved + request_bytes > limits.max_control_request_bytes
            or self._upload_reserved + upload_bytes > limits.max_upload_bytes
            or self._response_bytes + self._response_pending + response_bytes
            > limits.max_control_response_bytes
        ):
            raise YorungeError("upload_limit_exceeded")
        self._requests[kind] += 1
        self._request_reserved += request_bytes
        self._upload_reserved += upload_bytes
        self._response_pending += response_bytes
        reservation = UploadReservation(self, kind, request_bytes, upload_bytes, response_bytes)
        self._live.add(reservation)
        return reservation

    def snapshot(self) -> UploadCounters:
        # Inspection and cleanup remain possible after the deadline.
        self._owner()
        return UploadCounters(
            self._requests["read"],
            self._read_attempts,
            self._requests["create"],
            self._requests["project_link"],
            self._requests["presign"],
            self._requests["put"],
            self._requests["confirm"],
            self._effect_attempts,
            self._request_reserved,
            self._upload_reserved,
            self._response_pending,
            self._request_bytes,
            self._upload_bytes,
            self._response_bytes,
        )


class UploadReservation(_PrivateQuota):
    """One logical call, at most two physical reads or one physical effect."""

    def __init__(
        self,
        budget: UploadBudget,
        kind: CallKind,
        request_bytes: int,
        upload_bytes: int,
        response_bytes: int,
    ) -> None:
        self._budget, self._kind = budget, kind
        self._request, self._upload = request_bytes, upload_bytes
        self._pending = response_bytes
        self._sent = self._attempts = 0
        self._started = self._closed = False
        self._task: asyncio.Task[object] | None = None

    def begin(self) -> None:
        self._budget._current()
        loop = _loop()
        if self not in self._budget._live or self._started or self._closed or loop is None:
            raise YorungeError("invalid_request")
        self._task = asyncio.current_task()
        if self._task is None:
            raise YorungeError("invalid_request")
        self._budget._loop, self._started = loop, True

    def _owner(self) -> None:
        self._budget._owner()
        if (
            not self._started
            or self._closed
            or self not in self._budget._live
            or _loop() is None
            or asyncio.current_task() is not self._task
        ):
            raise YorungeError("invalid_request")

    def _current(self) -> None:
        self._owner()
        self._budget._current()

    def attempt(self) -> None:
        self._current()
        budget = self._budget
        if self._attempts >= (2 if self._kind == "read" else 1):
            raise YorungeError("invalid_request")
        if self._kind == "read":
            if budget._read_attempts >= budget._limits.max_read_attempts:
                raise YorungeError("upload_limit_exceeded")
            budget._read_attempts += 1
        else:
            budget._effect_attempts += 1
        self._attempts += 1
        budget._request_bytes += self._request

    def response(self, size: int) -> None:
        self._current()
        _quantity(size, 1_073_741_824)
        if self._attempts == 0:
            raise YorungeError("invalid_request")
        if size > self._pending:
            raise YorungeError("invalid_response")
        self._pending -= size
        self._budget._response_pending -= size
        self._budget._response_bytes += size

    def upload(self, size: int) -> None:
        self._current()
        _quantity(size, 1_048_576)
        if self._kind != "put" or self._attempts != 1:
            raise YorungeError("invalid_request")
        if self._sent + size > self._upload:
            raise YorungeError("input_changed")
        self._sent += size
        self._budget._upload_bytes += size

    def finish(self) -> None:
        self._budget._owner()
        if self._closed or self not in self._budget._live:
            raise YorungeError("invalid_request")
        if self._started:
            self._owner()
        budget = self._budget
        self._closed = True
        budget._live.remove(self)
        budget._response_pending -= self._pending
        self._pending = 0
        if self._attempts == 0:
            # Only a not-yet-delegated call can return its pre-intent claim.
            budget._requests[self._kind] -= 1
            budget._request_reserved -= self._request
            budget._upload_reserved -= self._upload
