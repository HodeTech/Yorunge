"""The directory primitives of one download: look, open safely, create, remove by identity.

Every name is relative to an open directory descriptor and every look is ``lstat`` without following
a link; a file is opened only after it was seen to be regular, ours, private and alone, and again
checked through the descriptor it was opened as (``O_NOFOLLOW|O_NONBLOCK``: a FIFO or a device
cannot block or be written). A file is removed only if the name still leads to the identity that was
seen. The lock object is a stable file per target; the lock is on that object, not on the stage.

Every boundary of the closed order (``docs/reference/download-engine.md``) is announced to
:func:`step`, which does nothing: the tests that kill the process at each boundary replace it.
"""

from __future__ import annotations

import errno
import fcntl
import os
import stat
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from yorunge.adapters.input_files import (
    Budget,
    close_descriptor,
    directory_chain,
    owned_descriptor,
)
from yorunge.domain.download import MAX_SIDECAR_BYTES
from yorunge.domain.download_state import Entry
from yorunge.domain.errors import YorungeError

OPEN_FLAGS = os.O_NOFOLLOW | os.O_NONBLOCK
LOCK_ATTEMPTS = 3
_UNSIGNED_64 = 2**64 - 1
Chain = tuple[tuple[int, int], ...]

# The tests replace this to stop the process at a named boundary; in production it is None.
_marker: Callable[[str], None] | None = None


def step(name: str) -> None:
    """A boundary of the closed order, announced by name. Nothing happens unless a test listens."""
    if _marker is not None:
        _marker(name)


def file_id(value: int) -> int:
    """A device or inode number as the unsigned 64-bit value a record can hold.

    ``st_dev`` can be negative (macOS' ``dev_t`` is signed); the sidecar and the table compare the
    same normalised value on both sides.
    """
    return value & _UNSIGNED_64


def describe(info: os.stat_result) -> Entry:
    return Entry(
        regular=stat.S_ISREG(info.st_mode),
        ours=info.st_uid == os.getuid(),
        private=stat.S_IMODE(info.st_mode) == 0o600,
        nlink=info.st_nlink,
        device=file_id(info.st_dev),
        inode=file_id(info.st_ino),
        size=info.st_size,
    )


def entry_of(directory: int, name: str) -> Entry | None:
    """What ``name`` is, without following it; ``None`` when nothing is there."""
    try:
        info = os.stat(name, dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        return None
    return describe(info)


def same_file(entry: Entry, other: Entry | None) -> bool:
    return other is not None and (entry.device, entry.inode) == (other.device, other.inode)


def open_checked(directory: int, name: str, seen: Entry, flags: int) -> int:
    """Open a file that was seen to be ours; it must still be that very file, by descriptor.

    The caller closes the descriptor. Anything else is an untrusted trace, which the command
    reports and never touches.
    """
    descriptor = os.open(name, flags | OPEN_FLAGS, dir_fd=directory)
    try:
        opened = describe(os.fstat(descriptor))
        if not opened.owned or not same_file(seen, opened):
            raise YorungeError("download_partial_unverified")
        if not same_file(seen, entry_of(directory, name)):
            raise YorungeError("download_partial_unverified")
        return descriptor
    except BaseException as error:
        close_descriptor(descriptor, error)
        raise


_umask = threading.Lock()


@contextmanager
def _owner_only_creation() -> Iterator[None]:
    """Files created inside have no group or world access and keep the owner's, whatever the umask.

    A umask that clears owner bits (0277) would make a new file 0400 until its ``fchmod``; a kill
    between the two would leave a file the next run cannot call ours. The process umask is only
    ever made stricter here (never looser), and the lock keeps two threads from restoring each
    other's value.
    """
    with _umask:
        previous = os.umask(0o077)
        try:
            yield
        finally:
            os.umask(previous)


def create_exclusive(directory: int, name: str, *, label: str) -> int:
    """A new private file that did not exist (``O_EXCL``), mode 0600 whatever the umask."""
    with _owner_only_creation():
        descriptor = os.open(
            name,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
    try:
        step(f"{label}:created")
        os.fchmod(descriptor, 0o600)
        step(f"{label}:private")
        return descriptor
    except BaseException as error:
        close_descriptor(descriptor, error)
        raise


def read_small(directory: int, name: str, seen: Entry) -> bytes:
    """The content of an owned file no longer than a sidecar may be (one byte more is read)."""
    descriptor = open_checked(directory, name, seen, os.O_RDONLY)
    try:
        return os.read(descriptor, MAX_SIDECAR_BYTES + 1)
    finally:
        close_descriptor(descriptor)


def remove_seen(directory: int, name: str, seen: Entry, *, label: str) -> None:
    """Remove ``name`` only if it is still the file that was seen (and nothing else).

    The identity is looked at and then the name is unlinked; POSIX has no removal by identity, so
    a name swapped between the two calls is removed in its place (an observed interval, not a
    sandbox).
    """
    current = entry_of(directory, name)
    if current is None:
        return
    if not same_file(seen, current):
        raise YorungeError("download_partial_unverified")
    try:
        os.unlink(name, dir_fd=directory)
    except FileNotFoundError:
        return
    step(f"removed:{label}")


def sync_directory(directory: int) -> None:
    os.fsync(directory)
    step("directory:synced")


def replace_atomically(directory: int, tmp: str, final: str, content: bytes, *, label: str) -> None:
    """Write ``content`` as ``final`` so that a reader sees the old file or the whole new one.

    A new temporary file (``O_EXCL``, 0600), written and synced; then renamed over ``final``; then
    the directory is synced. A temporary file in the way is a foreign file: the write fails.
    """
    descriptor = create_exclusive(directory, tmp, label=f"{label}_tmp")
    try:
        pending = memoryview(content)
        while pending:
            written = os.write(descriptor, pending)
            if not 0 < written <= len(pending):
                raise YorungeError("download_write_failed")
            pending = pending[written:]
        step(f"{label}_tmp:written")
        os.fsync(descriptor)
        step(f"{label}_tmp:synced")
    except BaseException as error:
        close_descriptor(descriptor, error)
        try:
            os.unlink(tmp, dir_fd=directory)  # the copy this call just made: not left to the next
        except OSError:
            pass
        raise
    close_descriptor(descriptor)
    os.replace(tmp, final, src_dir_fd=directory, dst_dir_fd=directory)
    step(f"{label}:replaced")
    sync_directory(directory)


@dataclass(slots=True)
class LockObject:
    """The held lock of one target: the descriptor on the stable lock file and its identity."""

    directory: int
    name: str
    descriptor: int
    seen: Entry

    def release(self) -> None:
        """Remove the lock file, under the lock and last, then let the lock go.

        The removal is best effort and never masks the error that ended the download: a lock
        file left behind is an empty file the next run takes up again.
        """
        try:
            remove_seen(self.directory, self.name, self.seen, label="lock")
        except (OSError, YorungeError):
            pass
        finally:
            try:
                close_descriptor(self.descriptor)
            except YorungeError:
                pass


def acquire_lock(directory: int, name: str) -> LockObject:
    """Steps 2-3 of the protocol: the lock file, and ``flock`` on it.

    A missing file is created exclusively (a lost race takes the present branch); a present one
    must be provably ours. After the lock is taken the name must still lead to the locked file: a
    process finishing a download removes its lock file, so a waiter that was handed the lock of a
    removed file starts again, at most three times.
    """
    for _ in range(LOCK_ATTEMPTS):
        seen = entry_of(directory, name)
        if seen is None:
            try:
                descriptor = create_exclusive(directory, name, label="lock")
            except FileExistsError:
                continue
        else:
            if not seen.owned:
                raise YorungeError("download_partial_unverified")
            descriptor = open_checked(directory, name, seen, os.O_RDWR)
        try:
            step("lock:opened")
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                if error.errno in (errno.EWOULDBLOCK, errno.EAGAIN, errno.EACCES):
                    raise YorungeError("download_busy") from None
                raise
            step("lock:held")
            held = describe(os.fstat(descriptor))
            if same_file(held, entry_of(directory, name)):
                return LockObject(directory, name, descriptor, held)
        except BaseException as error:
            close_descriptor(descriptor, error)
            raise
        close_descriptor(descriptor)  # the name leads elsewhere now: take it from the start
    raise YorungeError("download_busy")


@dataclass(frozen=True)
class NoBudget:
    """The publication is local I/O and is exempt from the download's deadline."""

    def check(self) -> None:
        return None


@dataclass(frozen=True)
class TargetDirectory:
    """The directory of the target, held open, with the chain it was reached through."""

    anchor: Path
    descriptor: int
    chain: Chain
    budget: Budget = NoBudget()

    @property
    def name(self) -> str:
        return self.anchor.name

    def recheck(self) -> None:
        """The directory is still the one that was opened (every ancestor, by identity)."""
        try:
            descriptor, chain = directory_chain(str(self.anchor.parent))
            with owned_descriptor(descriptor, close_code="download_write_failed"):
                if chain != self.chain:
                    raise YorungeError("download_write_failed")
        except OSError:
            raise YorungeError("download_write_failed") from None

    def close(self) -> None:
        close_descriptor(self.descriptor, code="download_write_failed")


def open_target_directory(target: Path) -> TargetDirectory:
    """Step 1: the target's directory exists and is reached without following a link."""
    if not isinstance(target, Path) or not target.is_absolute() or not target.name:
        raise YorungeError("download_target_invalid")
    try:
        descriptor, chain = directory_chain(str(target.parent))
    except (YorungeError, OSError):
        raise YorungeError("download_target_invalid") from None
    return TargetDirectory(target, descriptor, chain)
