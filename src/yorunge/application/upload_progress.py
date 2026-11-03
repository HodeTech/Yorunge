"""Private in-process transport counters; never durable evidence or public callbacks."""

from __future__ import annotations

import os
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from yorunge.domain.errors import YorungeError
from yorunge.domain.state import canonical_uuid


@dataclass(frozen=True, slots=True)
class UploadProgress:
    operation_id: str
    source_bytes: int
    total_bytes: int
    confirmed_bytes: int
    confirmed_files: int
    total_files: int


Sink = Callable[[UploadProgress], None]
_SINK: ContextVar[Sink | None] = ContextVar("upload_progress_sink", default=None)
_COUNTER: ContextVar[UploadCounter | None] = ContextVar("upload_progress_counter", default=None)


@contextmanager
def observe_upload(sink: Sink | None) -> Iterator[None]:
    """CLI composition only; Python public API exposes no observer parameter."""
    token = _SINK.set(sink)
    try:
        yield
    finally:
        _SINK.reset(token)


class UploadCounter:
    def __init__(self, sizes: tuple[int, ...], sink: Sink) -> None:
        if not 1 <= len(sizes) <= 128 or any(type(n) is not int or n < 0 for n in sizes):
            raise YorungeError("invalid_request")
        self._sizes, self._sink, self._total = sizes, sink, sum(sizes)
        self._pid, self._thread = os.getpid(), threading.current_thread()
        self._operation: str | None = None
        self._source = self._confirmed_bytes = 0
        self._confirmed: set[int] = set()

    def _owner(self) -> None:
        if os.getpid() != self._pid or threading.current_thread() is not self._thread:
            raise YorungeError("invalid_request")

    def _emit(self) -> None:
        assert self._operation is not None
        self._sink(
            UploadProgress(
                self._operation,
                self._source,
                self._total,
                self._confirmed_bytes,
                len(self._confirmed),
                len(self._sizes),
            )
        )

    def bind(self, operation_id: str) -> None:
        self._owner()
        canonical_uuid(operation_id)
        if self._operation not in (None, operation_id):
            raise YorungeError("invalid_request")
        self._operation = operation_id
        self._emit()

    def source(self, count: int) -> None:
        self._owner()
        if self._operation is None or type(count) is not int or count <= 0:
            raise YorungeError("invalid_request")
        if self._source + count > self._total:
            raise YorungeError("input_changed")
        self._source += count
        self._emit()

    def confirm(self, index: int) -> None:
        self._owner()
        if self._operation is None or type(index) is not int or not 0 <= index < len(self._sizes):
            raise YorungeError("invalid_request")
        if index in self._confirmed:
            return
        self._confirmed.add(index)
        self._confirmed_bytes += self._sizes[index]
        self._emit()


@contextmanager
def count_upload(sizes: tuple[int, ...]) -> Iterator[UploadCounter | None]:
    sink = _SINK.get()
    counter = UploadCounter(sizes, sink) if sink is not None else None
    token = _COUNTER.set(counter)
    try:
        yield counter
    finally:
        _COUNTER.reset(token)


def source_chunk(count: int) -> None:
    counter = _COUNTER.get()
    if counter is not None:
        counter.source(count)
