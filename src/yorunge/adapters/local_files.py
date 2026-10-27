"""Private local files, durability barriers and cooperative bounded locks."""

from __future__ import annotations

import os
import stat
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Literal

from yorunge.domain.errors import YorungeError

fcntl_module: ModuleType | None
try:
    import fcntl
except ImportError:
    fcntl_module = None
else:
    fcntl_module = fcntl


def require_local_files(
    code: Literal["state_unsupported", "config_unsupported"] = "state_unsupported",
) -> ModuleType:
    if sys.platform not in ("darwin", "linux") or fcntl_module is None:
        raise YorungeError(code)
    return fcntl_module


class Deadline:
    def __init__(self, seconds: float = 5.0) -> None:
        self.end = time.monotonic() + seconds

    def remaining(self) -> float:
        remaining = self.end - time.monotonic()
        if remaining <= 0:
            raise YorungeError("state_busy")
        return remaining


def safe_ancestors(path: Path) -> None:
    for ancestor in path.absolute().parents:
        try:
            info = ancestor.lstat()
        except FileNotFoundError:
            continue
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid not in (0, os.getuid())
            or (info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX)
        ):
            raise YorungeError("state_invalid")


def sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def full_sync(descriptor: int) -> None:
    locking = require_local_files()
    os.fsync(descriptor)
    if sys.platform == "darwin":
        locking.fcntl(descriptor, locking.F_FULLFSYNC)


def private_directory(path: Path) -> None:
    safe_ancestors(path)
    try:
        info = path.lstat()
    except FileNotFoundError:
        if not path.parent.exists():
            private_directory(path.parent)
        try:
            path.mkdir(mode=0o700)
        except FileExistsError:
            pass
        else:
            os.chmod(path, 0o700, follow_symlinks=False)
            sync_directory(path)
            sync_directory(path.parent)
        info = path.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise YorungeError("state_invalid")


def create_private_directory(path: Path) -> None:
    safe_ancestors(path)
    path.mkdir(mode=0o700)
    os.chmod(path, 0o700, follow_symlinks=False)
    sync_directory(path)
    sync_directory(path.parent)


def durable_private_chain(path: Path) -> None:
    """Also retry directory-entry barriers after an interrupted earlier mkdir."""
    current = path
    while True:
        info = current.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700
        ):
            break
        sync_directory(current)
        sync_directory(current.parent)
        if current == current.parent:
            break
        current = current.parent


def private_stat(path: Path) -> os.stat_result:
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_nlink != 1
    ):
        raise YorungeError("state_invalid")
    return info


def open_private(path: Path, *, writable: bool = False) -> int:
    before = private_stat(path)
    flags = (os.O_RDWR if writable else os.O_RDONLY) | os.O_NOFOLLOW | os.O_NONBLOCK
    descriptor = os.open(path, flags)
    try:
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise YorungeError("state_invalid")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def read_private(path: Path, limit: int) -> bytes:
    descriptor = open_private(path)
    with os.fdopen(descriptor, "rb") as source:
        data = source.read(limit + 1)
    if len(data) > limit:
        raise YorungeError("state_invalid")
    return data


def write_new(path: Path, content: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        os.fchmod(output.fileno(), 0o600)
        output.write(content)
        output.flush()
        os.fsync(output.fileno())
        sync_directory(path.parent)
        full_sync(output.fileno())


def sync_private(path: Path) -> None:
    descriptor = open_private(path)
    try:
        os.fsync(descriptor)
        sync_directory(path.parent)
        full_sync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def file_lock(path: Path, deadline: Deadline, *, exclusive: bool, create: bool) -> Iterator[None]:
    locking = require_local_files()
    if create:
        try:
            write_new(path, b"")
        except FileExistsError:
            sync_private(path)
    descriptor = open_private(path)
    try:
        end = time.monotonic() + min(1.0, deadline.remaining())
        operation = locking.LOCK_EX if exclusive else locking.LOCK_SH
        while True:
            try:
                locking.flock(descriptor, operation | locking.LOCK_NB)
                break
            except BlockingIOError:
                remaining = min(end - time.monotonic(), deadline.remaining())
                if remaining <= 0:
                    raise YorungeError("state_busy") from None
                time.sleep(min(0.01, remaining))
        actual = private_stat(path)
        held = os.fstat(descriptor)
        if (actual.st_dev, actual.st_ino) != (held.st_dev, held.st_ino):
            raise YorungeError("state_invalid")
        yield
    finally:
        os.close(descriptor)
