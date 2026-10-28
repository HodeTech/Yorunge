"""Bounded, operation-scoped reuse of pure row decoding; DB relationships stay live."""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TypeVar, cast

T = TypeVar("T")
MAX_ENTRIES = 4096


@dataclass
class Memo:
    entries: OrderedDict[tuple[type[object], bytes], object] = field(default_factory=OrderedDict)


ACTIVE: ContextVar[Memo | None] = ContextVar("yorunge_validation_memo", default=None)


@contextmanager
def validation_session() -> Iterator[None]:
    if ACTIVE.get() is not None:
        yield
        return
    memo = Memo()
    token = ACTIVE.set(memo)
    try:
        yield
    finally:
        ACTIVE.reset(token)
        memo.entries.clear()


def fingerprint(row: tuple[object, ...]) -> bytes | None:
    digest = hashlib.sha256()
    try:
        for value in row:
            if value is None:
                digest.update(b"n")
                continue
            if type(value) is str:
                data, tag = value.encode("utf-8"), b"s"
            elif type(value) is int:
                data, tag = str(value).encode("ascii"), b"i"
            elif type(value) is bytes:
                data, tag = value, b"b"
            else:
                return None
            digest.update(tag)
            digest.update(len(data).to_bytes(8, "big"))
            digest.update(data)
    except UnicodeError:
        return None
    return digest.digest()


def validated(tag: type[T], row: tuple[object, ...], build: Callable[[], T]) -> T:
    memo = ACTIVE.get()
    if memo is None:
        return build()
    identity = fingerprint(row)
    if identity is None:
        return build()
    key = (tag, identity)
    if key in memo.entries:
        memo.entries.move_to_end(key)
        return cast(T, memo.entries[key])
    result = build()
    memo.entries[key] = result
    if len(memo.entries) > MAX_ENTRIES:
        memo.entries.popitem(last=False)
    return result
