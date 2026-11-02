"""Lazy same-task descriptor streaming, bounded reads and final identity/hash checks."""

from __future__ import annotations

import asyncio
import errno
import hashlib
import math
import os
import stat
import sys
import threading
import time
from collections.abc import AsyncIterator
from types import TracebackType
from typing import NoReturn, Self

from yorunge.adapters.input_files import (
    close_input_descriptor,
    directory_chain,
    identity,
    relative_file,
    require_input_files,
    signature,
)
from yorunge.application.storage import STORAGE_CHUNK_BYTES
from yorunge.domain.capabilities import canonical
from yorunge.domain.dataset_manifest import DatasetFile
from yorunge.domain.dataset_upload import UploadRoot
from yorunge.domain.errors import YorungeError


class DescriptorByteSource(AsyncIterator[bytes]):
    """One iteration, no source I/O during construction, no executor or producer task."""

    def __init__(self, root: UploadRoot, file: DatasetFile, *, deadline: float) -> None:
        require_input_files()
        finite = False
        if type(deadline) in (int, float):
            try:
                finite = math.isfinite(deadline)
            except OverflowError:
                pass
        if not finite:
            raise YorungeError("invalid_request")
        try:
            self._root = UploadRoot.model_validate_json(root.encoded())
            self._file = DatasetFile.model_validate_json(canonical(file.model_dump(mode="json")))
        except (ValueError, TypeError, AttributeError):
            raise YorungeError("input_invalid") from None
        self._end = deadline
        self._task: asyncio.Task[object] | None = None
        self._pid, self._thread = os.getpid(), threading.get_ident()
        self._root_fd: int | None = None
        self._file_fd: int | None = None
        self._absolute: tuple[tuple[int, int], ...] = ()
        self._relative: tuple[tuple[int, int], ...] = ()
        self._signature: tuple[int, ...] = ()
        self._used, self._closed, self._complete = False, False, False
        self._started = False
        self._sent = 0
        self._digest = hashlib.sha256()

    @property
    def size(self) -> int:
        return self._file.size

    @property
    def sha256(self) -> str:
        return self._file.sha256

    @property
    def sent_bytes(self) -> int:
        return self._sent

    @property
    def complete(self) -> bool:
        return self._complete

    @property
    def sent_sha256(self) -> str | None:
        return self._digest.hexdigest() if self._complete else None

    def _owner(self) -> None:
        try:
            current = asyncio.current_task()
        except RuntimeError:
            current = None
        if (
            current is None
            or self._pid != os.getpid()
            or self._thread != threading.get_ident()
            or (self._task is not None and self._task is not current)
        ):
            raise YorungeError("invalid_request")
        self._task = current

    def _check(self) -> None:
        self._owner()
        if self._closed:
            raise YorungeError("invalid_request")
        if time.monotonic() >= self._end:
            raise YorungeError("execution_timeout")

    def chunks(self) -> AsyncIterator[bytes]:
        self._check()
        if self._used:
            raise YorungeError("invalid_request")
        self._used = True
        return self

    def _open(self) -> None:
        self._check()
        self._started = True
        self._used = True
        root, chain = directory_chain(self._root.anchor)
        self._root_fd, self._absolute = root, chain
        if identity(os.fstat(root)) != (self._root.device, self._root.inode):
            raise YorungeError("input_changed")
        leaf, chain = relative_file(root, self._file.path)
        self._file_fd, self._relative = leaf, chain
        info = os.fstat(leaf)
        if not stat.S_ISREG(info.st_mode) or info.st_size != self.size:
            raise YorungeError("input_changed")
        self._signature = signature(info)

    def _recheck(self) -> None:
        self._check()
        assert self._root_fd is not None and self._file_fd is not None
        if signature(os.fstat(self._file_fd)) != self._signature:
            raise YorungeError("input_changed")
        leaf, chain = relative_file(self._root_fd, self._file.path)
        try:
            if chain != self._relative or signature(os.fstat(leaf)) != self._signature:
                raise YorungeError("input_changed")
        finally:
            close_input_descriptor(leaf, sys.exc_info()[1])
        root, chain = directory_chain(self._root.anchor)
        try:
            if chain != self._absolute:
                raise YorungeError("input_changed")
        finally:
            close_input_descriptor(root, sys.exc_info()[1])
        if self._digest.hexdigest() != self.sha256:
            raise YorungeError("input_changed")
        self._check()

    async def __anext__(self) -> bytes:
        self._owner()
        if self._complete:
            raise StopAsyncIteration
        try:
            self._check()
            if not self._started:
                self._open()
            assert self._file_fd is not None
            await asyncio.sleep(0)
            self._check()
            if self._sent < self.size:
                chunk = os.read(self._file_fd, min(STORAGE_CHUNK_BYTES, self.size - self._sent))
                self._check()
                if not chunk:
                    raise YorungeError("input_changed")
                self._digest.update(chunk)
                self._sent += len(chunk)
                return chunk
            self._recheck()
            self._complete = True
        except OSError as error:
            await self.aclose()
            changed = error.errno in (errno.ENOENT, errno.ENOTDIR, errno.ELOOP)
            raise YorungeError("input_changed" if changed else "input_invalid") from None
        except BaseException:
            await self.aclose()
            raise
        await self.aclose()
        raise StopAsyncIteration

    async def __aenter__(self) -> Self:
        self._check()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        self._owner()
        if self._closed:
            return
        self._closed = True
        descriptors = self._file_fd, self._root_fd
        self._file_fd = self._root_fd = None
        primary, failure = sys.exc_info()[1], None
        for descriptor in descriptors:
            if descriptor is not None:
                try:
                    close_input_descriptor(descriptor, primary)
                except OSError:
                    failure = YorungeError("input_invalid")
        if primary is None and failure is not None:
            raise failure

    def __repr__(self) -> str:
        return "<DescriptorByteSource redacted>"

    def __copy__(self) -> NoReturn:
        raise TypeError("storage sources cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        raise TypeError("storage sources cannot be copied")

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("storage sources cannot be serialized")
