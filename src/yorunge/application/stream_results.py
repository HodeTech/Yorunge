"""Bounded typed NDJSON events and a task-owned HTTP message reader."""

from __future__ import annotations

import asyncio
import json
import math
import os
import threading
import time
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager
from types import TracebackType
from typing import TypeVar, cast

from pydantic import BaseModel

from yorunge.application.http_transport import CHUNK_SIZE, HttpRequest, HttpResponse, HttpTransport
from yorunge.application.response_json import check_response_secrets, parse_json
from yorunge.domain.credentials import SecretValue
from yorunge.domain.errors import ErrorCode, OperationError, YorungeError
from yorunge.domain.streams import (
    ErrorEvent,
    EventMeta,
    ProgressEvent,
    ResultEvent,
    StreamEvent,
    _result_model_type,
)
from yorunge.domain.wire_limits import FRAME_LIMIT, JSON_LIMIT

T = TypeVar("T", bound=BaseModel)
_META_KEYS = frozenset({"schema_version", "stream_id", "sequence", "event", "operation_id"})
_JSON_DECODER = json.JSONDecoder()


def _compact(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode(
        "utf-8", "strict"
    )


def _failure(code: ErrorCode, operation_id: str | None) -> YorungeError:
    return OperationError(code, operation_id) if operation_id is not None else YorungeError(code)


def _bound(error: YorungeError, operation_id: str | None) -> YorungeError:
    if isinstance(error, OperationError):
        return OperationError(
            error.code,
            operation_id or error.operation_id,
            reason_code=error.reason_code,
            capacity_kind=error.capacity_kind,
        )
    return _failure(error.code, operation_id)


def _payload_bytes(data: bytes) -> bytes:
    """Measure the actual encoded payload span, including its interior whitespace.

    The whole frame has already passed the strict parser. This second, bounded
    scan locates top-level members without guessing at escaped key/string bytes.
    """
    text = data.decode("utf-8", "strict")
    offset = len(text) - len(text.lstrip()) + 1  # the validated opening object brace
    while True:
        while text[offset].isspace():
            offset += 1
        key, offset = _JSON_DECODER.raw_decode(text, offset)
        while text[offset].isspace():
            offset += 1
        offset += 1  # colon
        while text[offset].isspace():
            offset += 1
        start = offset
        _, offset = _JSON_DECODER.raw_decode(text, offset)
        if key == "payload":
            return text[start:offset].encode("utf-8", "strict")
        while text[offset].isspace():
            offset += 1
        offset += 1  # comma; the validated frame contains the required payload member


def _validated_event(
    data: bytes,
    model: type[T],
    *,
    stream_id: str,
    sequence: int,
    operation_id: str | None,
    secrets: tuple[SecretValue, ...],
) -> StreamEvent[T]:
    raw = parse_json(data, max_bytes=FRAME_LIMIT)
    if not isinstance(raw, dict) or set(raw) != _META_KEYS | {"payload"}:
        raise ValueError("closed event object required")
    meta = EventMeta.model_validate({key: raw[key] for key in _META_KEYS}, strict=True)
    if (
        meta.stream_id != stream_id
        or meta.sequence != sequence
        or meta.operation_id != operation_id
    ):
        raise ValueError("stream identity and sequence must remain bound")
    if meta.event == "progress":
        progress = ProgressEvent.model_validate_json(data, strict=True)
        check_response_secrets(progress.payload, secrets)
        return progress
    if meta.event == "error":
        error = ErrorEvent.model_validate_json(data, strict=True)
        # ErrorEnvelope has rebuilt the local message. It is a protocol constant,
        # while provider-derived approval identifiers still need provenance checks.
        check_response_secrets(error.payload.details, secrets)
        return error
    if len(_payload_bytes(data)) > JSON_LIMIT:
        raise ValueError("result payload byte limit")
    event_type = cast(type[ResultEvent[T]], ResultEvent.__class_getitem__(model))
    result = event_type.model_validate_json(data, strict=True)
    check_response_secrets(result.payload, secrets)
    return result


def decode_event(
    data: bytes,
    model: type[T],
    *,
    stream_id: str,
    sequence: int,
    operation_id: str | None = None,
    secrets: tuple[SecretValue, ...] = (),
) -> StreamEvent[T]:
    """Validate one record (without its line terminator), without retaining raw failures."""
    value: StreamEvent[T] | None = None
    try:
        value = _validated_event(
            data,
            model,
            stream_id=stream_id,
            sequence=sequence,
            operation_id=operation_id,
            secrets=secrets,
        )
    except Exception:
        pass
    if value is None:
        raise _failure("invalid_response", operation_id)
    return value


def encode_event(event: StreamEvent[T], *, secrets: tuple[SecretValue, ...] = ()) -> bytes:
    """Validate the complete compact event before delivering any UTF-8/LF bytes."""
    encoded: bytes | None = None
    operation_id: str | None = None
    try:
        if not isinstance(event, (ProgressEvent, ResultEvent, ErrorEvent)):
            raise ValueError("typed stream event required")
        meta = EventMeta.model_validate(
            {key: getattr(event, key) for key in _META_KEYS}, strict=True
        )
        operation_id = meta.operation_id
        model: type[BaseModel] = BaseModel
        if isinstance(event, ResultEvent):
            model = _result_model_type(type(event))
        raw = _compact(event.model_dump(mode="json", warnings="error"))
        normalized = _validated_event(
            raw,
            model,
            stream_id=meta.stream_id,
            sequence=meta.sequence,
            operation_id=operation_id,
            secrets=secrets,
        )
        # In particular, an ErrorEvent constructed without validation may carry
        # a private message. Only the validated, locally rebuilt envelope is emitted.
        candidate = _compact(normalized.model_dump(mode="json", warnings="error"))
        parse_json(candidate, max_bytes=FRAME_LIMIT)
        if isinstance(normalized, ResultEvent) and len(_payload_bytes(candidate)) > JSON_LIMIT:
            raise ValueError("normalized result payload byte limit")
        encoded = candidate
    except Exception:
        pass
    if encoded is None:
        raise _failure("output_write_failed", operation_id)
    return encoded + b"\n"


def _remaining(deadline: float) -> None:
    valid = type(deadline) in (int, float)
    try:
        valid = valid and math.isfinite(deadline)
    except OverflowError:
        valid = False
    if not valid:
        raise YorungeError("invalid_request")
    if deadline <= time.monotonic():
        raise YorungeError("transport_timeout")


class OwnedStream(AbstractAsyncContextManager["OwnedStream[T]"], AsyncIterator["StreamEvent[T]"]):
    """One consumer, bounded pending line and terminal, no producer/background task."""

    def __init__(
        self,
        transport: HttpTransport,
        request: HttpRequest,
        model: type[T],
        *,
        deadline: float,
        stream_id: str,
        operation_id: str | None,
        secrets: tuple[SecretValue, ...],
    ) -> None:
        valid = False
        try:
            EventMeta(
                schema_version=1,
                stream_id=stream_id,
                sequence=1,
                event="progress",
                operation_id=operation_id,
            )
            valid = (
                isinstance(model, type)
                and issubclass(model, BaseModel)
                and model is not BaseModel
                and type(secrets) is tuple
                and all(isinstance(secret, SecretValue) for secret in secrets)
            )
        except Exception:
            pass
        if not valid:
            raise YorungeError("invalid_request")
        self._transport, self._request, self._model = transport, request, model
        self._deadline, self._stream_id, self._operation_id = deadline, stream_id, operation_id
        # A request's selected credential is already known to this consumer;
        # callers need only supply any additional captured credentials.
        self._secrets = secrets + ((request.credential.secret,) if request.credential else ())
        self._context: AbstractAsyncContextManager[HttpResponse] | None = None
        self._chunks: AsyncIterator[bytes] | None = None
        self._task: asyncio.Task[object] | None = None
        self._pid, self._thread = os.getpid(), threading.get_ident()
        self._entered, self._closed, self._exited = False, False, False
        self._delivered = False
        self._sequence = 1
        self._buffer = bytearray()
        self._terminal: StreamEvent[T] | None = None

    def _owner(self) -> None:
        if (
            not self._entered
            or os.getpid() != self._pid
            or threading.get_ident() != self._thread
            or asyncio.current_task() is not self._task
        ):
            raise YorungeError("invalid_request")

    async def __aenter__(self) -> OwnedStream[T]:
        if (
            self._entered
            or self._closed
            or os.getpid() != self._pid
            or threading.get_ident() != self._thread
        ):
            raise YorungeError("invalid_request")
        self._entered, self._task = True, asyncio.current_task()
        failure: YorungeError | None = None
        try:
            _remaining(self._deadline)
            self._context = self._transport.open(self._request, deadline=self._deadline)
            response = await self._context.__aenter__()
            try:
                self._chunks = response.chunks()
            except BaseException as error:
                await self._context.__aexit__(type(error), error, error.__traceback__)
                raise
        except YorungeError as error:
            failure = _bound(error, self._operation_id)
            self._closed = True
        except BaseException:
            self._closed = True
            raise
        if failure is not None:
            raise failure
        return self

    async def _finish(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._closed:
            return
        self._closed = True
        self._buffer.clear()
        self._terminal = None
        assert self._context is not None
        failure: YorungeError | None = None
        try:
            await self._context.__aexit__(exc_type, exc, traceback)
        except YorungeError as error:
            failure = _bound(error, self._operation_id)
        if failure is not None:
            raise failure

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        # Reject a foreign task before it can resume the HTTP timeout/context.
        self._owner()
        if self._exited:
            raise YorungeError("invalid_request")
        self._exited = True
        try:
            await self._finish(exc_type, exc, traceback)
        except YorungeError as error:
            # A timeout can replace the cancellation injected by the HTTP context.
            error.__context__, error.__cause__ = None, None
            raise

    async def aclose(self) -> None:
        """Normal early close is resource cleanup, not cancellation or a terminal event."""
        self._owner()
        try:
            await self._finish(None, None, None)
        except YorungeError as error:
            error.__context__, error.__cause__ = None, None
            raise

    def __aiter__(self) -> OwnedStream[T]:
        return self

    def _record(self, data: bytes) -> StreamEvent[T]:
        if data.endswith(b"\r"):
            data = data[:-1]
        if not data or b"\r" in data:
            raise _failure("invalid_response", self._operation_id)
        event = decode_event(
            data,
            self._model,
            stream_id=self._stream_id,
            sequence=self._sequence,
            operation_id=self._operation_id,
            secrets=self._secrets,
        )
        self._sequence += 1
        _remaining(self._deadline)
        return event

    def _buffered(self) -> StreamEvent[T] | None:
        if self._terminal is not None and self._buffer:
            raise _failure("invalid_response", self._operation_id)
        end = self._buffer.find(b"\n")
        if end >= 0:
            record = bytes(self._buffer[:end])
            del self._buffer[: end + 1]
            event = self._record(record)
            if isinstance(event, ProgressEvent):
                return event
            self._terminal = event
            if self._buffer:
                raise _failure("invalid_response", self._operation_id)
        # Permit one pending CR only as the potential CRLF terminator.
        if len(self._buffer) > FRAME_LIMIT + int(self._buffer.endswith(b"\r")):
            raise _failure("invalid_response", self._operation_id)
        return None

    def _read_failure(self, code: ErrorCode) -> ErrorCode:
        if code != "transport_failed":
            return code
        if self._buffer:
            return "invalid_response"
        if self._sequence > 1:
            return "stream_interrupted"
        return code

    async def _read_chunk(self) -> bool:
        assert self._chunks is not None
        chunk: bytes | None = None
        failure: ErrorCode | None = None
        try:
            chunk = await anext(self._chunks)
        except StopAsyncIteration:
            return True
        except YorungeError as error:
            failure = self._read_failure(error.code)
        if failure is not None:
            raise _failure(failure, self._operation_id)
        if type(chunk) is not bytes or len(chunk) > CHUNK_SIZE:
            raise _failure("invalid_response", self._operation_id)
        self._buffer.extend(chunk)
        return False

    async def _message_end(self) -> StreamEvent[T]:
        if self._buffer:
            raise _failure("invalid_response", self._operation_id)
        if self._terminal is None:
            raise _failure("stream_interrupted", self._operation_id)
        terminal = self._terminal
        await self._finish(None, None, None)
        self._delivered = True
        return terminal

    async def _next(self) -> StreamEvent[T]:
        while True:
            _remaining(self._deadline)
            event = self._buffered()
            if event is not None:
                return event
            if await self._read_chunk():
                return await self._message_end()

    async def __anext__(self) -> StreamEvent[T]:
        self._owner()
        if self._delivered:
            raise StopAsyncIteration
        if self._closed:
            raise YorungeError("invalid_request")
        failure: YorungeError | None = None
        try:
            return await self._next()
        except YorungeError as error:
            failure = _bound(error, self._operation_id)
        except asyncio.CancelledError as error:
            try:
                await self._finish(type(error), error, error.__traceback__)
            except YorungeError as mapped:
                mapped.__context__, mapped.__cause__ = None, None
                raise
            raise
        assert failure is not None
        await self._finish(type(failure), failure, None)
        raise failure


def open_stream(
    transport: HttpTransport,
    request: HttpRequest,
    model: type[T],
    *,
    deadline: float,
    stream_id: str,
    operation_id: str | None = None,
    secrets: tuple[SecretValue, ...] = (),
) -> OwnedStream[T]:
    """Consume the common event wire in trusted composition, without an EVREN codec claim."""
    return OwnedStream(
        transport,
        request,
        model,
        deadline=deadline,
        stream_id=stream_id,
        operation_id=operation_id,
        secrets=secrets,
    )
