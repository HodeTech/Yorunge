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
import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from types import ModuleType
from typing import Final

from yorunge.adapters.input_files import close_descriptor
from yorunge.adapters.local_files import require_local_files
from yorunge.domain.download import MAX_SIDECAR_BYTES
from yorunge.domain.download_state import Entry
from yorunge.domain.errors import ErrorCode, YorungeError

OPEN_FLAGS = os.O_NOFOLLOW | os.O_NONBLOCK
CLOSE_CODE: Final[ErrorCode] = "download_write_failed"
LOCK_ATTEMPTS = 3
_UNSIGNED_64 = 2**64 - 1

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
        close_descriptor(descriptor, error, code=CLOSE_CODE)
        raise


def create_exclusive(directory: int, name: str, *, label: str) -> int:
    """A new private file that did not exist (``O_EXCL``), mode 0600 whatever the umask.

    The process umask is never touched: it belongs to the whole process, and a library that
    borrowed it for the length of a call would change the files other threads create meanwhile (or
    restore a value another thread had just set). The file is requested as 0600, which the umask
    can only narrow (0022 and 0077 leave it as it is); ``fchmod`` then makes it exactly 0600 for the
    rare umask that clears owner bits too. A process killed between the two calls under such a
    umask leaves a file the next run does not call ours (``download_partial_unverified``, nothing
    is touched): the one trace of this kind, and it asks for a hostile umask and a kill in a window
    of two system calls.
    """
    descriptor = os.open(
        name,
        os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=directory,
    )
    try:
        step(f"{label}:created")
        os.fchmod(descriptor, 0o600)
        made = os.fstat(descriptor)
        if stat.S_IMODE(made.st_mode) != 0o600 or made.st_uid != os.getuid():
            # A filesystem that keeps no permissions (FAT, exFAT) cannot hold a file that is
            # provably ours: refused here, before a byte is downloaded, and nothing is left.
            _discard_just_made(directory, name, made)
            raise YorungeError("download_write_failed")
        step(f"{label}:private")
        return descriptor
    except BaseException as error:
        close_descriptor(descriptor, error, code=CLOSE_CODE)
        raise


def _discard_just_made(directory: int, name: str, made: os.stat_result) -> None:
    """Unlink the file this call created, if the name still leads to it."""
    try:
        current = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if (current.st_dev, current.st_ino) == (made.st_dev, made.st_ino):
            os.unlink(name, dir_fd=directory)
    except OSError:
        pass


def read_small(directory: int, name: str, seen: Entry) -> bytes:
    """The content of an owned file no longer than a sidecar may be (one byte more is read)."""
    descriptor = open_checked(directory, name, seen, os.O_RDONLY)
    try:
        return os.read(descriptor, MAX_SIDECAR_BYTES + 1)
    finally:
        close_descriptor(descriptor, code=CLOSE_CODE)


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


def require_standing(directory: int, name: str, expected: Entry | None) -> None:
    """``name`` is what this download left there: nothing (``None``) or the very file ``expected``.

    Anything else is a trace of somebody else's, which is reported and never touched. POSIX has no
    replacement by identity: the look and the call that follows are an observed interval, not a
    sandbox (the lock keeps this tool's own processes out of it).
    """
    current = entry_of(directory, name)
    if expected is None:
        if current is not None:
            raise YorungeError("download_partial_unverified")
    elif not same_file(expected, current):
        raise YorungeError("download_partial_unverified")


def replace_atomically(
    directory: int,
    tmp: str,
    final: str,
    content: bytes,
    *,
    label: str,
    expected: Entry | None,
    on_replaced: Callable[[Entry], None],
) -> None:
    """Write ``content`` as ``final`` so that a reader sees the old file or the whole new one.

    ``expected`` is what the name leads to now, as this download left it (``None``: nothing); a
    name that leads to anything else is not replaced (``download_partial_unverified``), before the
    temporary file is made and again just before the rename. A new temporary file (``O_EXCL``,
    0600), written and synced; then renamed over ``final``; then the directory is synced. A
    temporary file in the way is a foreign file: the write fails. ``on_replaced`` is told the
    identity of the file that now stands at ``final``, the moment it does (before the directory is
    synced: a failing sync must not leave the caller holding the identity of the file it replaced).
    """
    require_standing(directory, final, expected)
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
        made = describe(os.fstat(descriptor))
        require_standing(directory, final, expected)
    except BaseException as error:
        close_descriptor(descriptor, error, code=CLOSE_CODE)
        try:
            os.unlink(tmp, dir_fd=directory)  # the copy this call just made: not left to the next
        except OSError:
            pass
        raise
    close_descriptor(descriptor, code=CLOSE_CODE)
    os.replace(tmp, final, src_dir_fd=directory, dst_dir_fd=directory)
    on_replaced(made)
    step(f"{label}:replaced")
    sync_directory(directory)


@dataclass(slots=True)
class LockObject:
    """The held lock of one target: the descriptor on the stable lock file and its identity."""

    directory: int
    name: str
    descriptor: int
    seen: Entry

    def verify(self) -> None:
        """The name still leads to the locked file; else the exclusion this download holds is gone.

        Somebody removed the hidden lock file (a cleanup tool, a hand): another run may have taken
        a lock on a new one and be using the very same stage. Nothing more is written or removed.
        """
        if not same_file(self.seen, entry_of(self.directory, self.name)):
            raise YorungeError("download_busy")

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
                close_descriptor(self.descriptor, code=CLOSE_CODE)
            except YorungeError:
                pass


def acquire_lock(directory: int, name: str) -> LockObject:
    """Steps 2-3 of the protocol: the lock file, and ``flock`` on it.

    A missing file is created exclusively (a lost race takes the present branch); a present one
    must be provably ours. After the lock is taken the name must still lead to the locked file: a
    process finishing a download removes its lock file, so a waiter that was handed the lock of a
    removed file starts again; so does one whose look or open met the removal. Three attempts in
    all, whatever sent them round again.
    """
    fcntl = require_local_files()
    for _ in range(LOCK_ATTEMPTS):
        descriptor = _open_lock_object(directory, name)
        if descriptor is None:
            continue
        try:
            lock = _flock_named(fcntl, directory, name, descriptor)
        except BaseException as error:
            close_descriptor(descriptor, error, code=CLOSE_CODE)
            raise
        if lock is not None:
            return lock
        close_descriptor(
            descriptor, code=CLOSE_CODE
        )  # the name leads elsewhere now: from the start
    raise YorungeError("download_busy")


def _open_lock_object(directory: int, name: str) -> int | None:
    """Step 2: look at the lock file, create it if missing, else open the one that is there.

    The open descriptor, which the caller closes; ``None`` when the attempt starts again from the
    look (a lost creation race, or a lock file the run that finished is removing).
    """
    seen = entry_of(directory, name)
    if seen is None:
        try:
            return create_exclusive(directory, name, label="lock")
        except FileExistsError:
            return None
    return _open_present_lock(directory, name, seen)


def _open_present_lock(directory: int, name: str, seen: Entry) -> int | None:
    """Open a lock file that was seen to be there; it must be provably ours.

    The open descriptor, or ``None`` when the run that finished has removed (or is removing) it.
    """
    if seen.nlink == 0:
        return None  # unlinked right now by the run that finished: not a foreign file
    if not seen.owned:
        raise YorungeError("download_partial_unverified")
    try:
        return open_checked(directory, name, seen, os.O_RDWR)
    except FileNotFoundError:
        return None  # the process that finished removed it between the look and the open
    except YorungeError:
        now = entry_of(directory, name)
        if now is None or now.nlink == 0 or (now.owned and not same_file(seen, now)):
            return None  # ... or removed (perhaps made anew) between the open and the look
        raise


def _flock_named(
    fcntl: ModuleType, directory: int, name: str, descriptor: int
) -> LockObject | None:
    """Step 3: ``flock`` the open lock file; the name must still lead to the file that is locked.

    The held lock object, or ``None`` when the name leads elsewhere now. The caller owns the
    descriptor and closes it on every error and on ``None``.
    """
    step("lock:opened")
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as error:
        if error.errno in (errno.EWOULDBLOCK, errno.EAGAIN, errno.EACCES):
            raise YorungeError("download_busy") from None
        raise YorungeError("download_write_failed") from None  # ENOLCK, no locks here
    step("lock:held")
    held = describe(os.fstat(descriptor))
    if same_file(held, entry_of(directory, name)):
        return LockObject(directory, name, descriptor, held)
    return None
