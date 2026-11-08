"""Staged, exclusive publication of one local artifact: never an overwrite, honest about doubt.

The principle is the manifest's, written once for every artifact that must reach a place the
user named without ever replacing what is there: a private stage is created in the target's own
directory with ``O_CREAT|O_EXCL|O_NOFOLLOW`` (mode 0600), filled and synced; what was staged is
verified; the stage is hard-linked to the target (``link()`` is exclusive: a taken name is a
definite failure, nothing of the caller's is published); the link, the stage's removal and the
target are verified again by identity; the directory and the file are synced. From the moment the
link is attempted a failure is *uncertain* (the target may or may not exist); before it, a failure
is definite and the stage is removed again by identity, unless the caller's ``_discard`` keeps it.

What an artifact answers with is its own: the error family (:class:`ArtifactCodes`) is the
caller's, as is the stage name prefix. The steps that the families' tests inject faults into stay
overridable methods of the publisher (``_check_stage``, ``_publish_link``, ``_check_target``,
``_sync``), so that a caller can keep its own seams.

Two entries: :meth:`ArtifactPublisher.publish_bytes` for content held in memory, and
:meth:`ArtifactPublisher.publish_stage` for a stage the caller opened, wrote (a stream) and synced
itself: the publisher then owns only the order *verify, link, clean up, sync* and the identity
checks around it. What becomes of a stage when publication fails is the one policy a stream must
own (:meth:`ArtifactPublisher._discard`): bytes in memory can be written again, but a finished
stage may be the only copy of what took a long download.
"""

from __future__ import annotations

import asyncio
import errno
import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from typing import NoReturn, Protocol
from uuid import uuid4

from yorunge.adapters.input_files import Budget, identity, owned_descriptor, signature
from yorunge.adapters.local_files import full_sync
from yorunge.domain.errors import MESSAGES, ErrorCode, YorungeError


def _add_note_once(error: BaseException, note: str) -> None:
    """Notes are fixed sentences: the same one is never written twice on one error."""
    if note not in getattr(error, "__notes__", ()):
        BaseException.add_note(error, note)


# The errors of ``link(2)`` that mean the call was refused before any entry was made. Any other
# (an I/O error, a stale or timed-out network volume) leaves the outcome unknown.
LINK_REFUSED = frozenset(
    {
        errno.EPERM,
        errno.EACCES,
        errno.EROFS,
        errno.ENOTSUP,
        errno.EOPNOTSUPP,
        errno.EMLINK,
        errno.EXDEV,
        errno.ENOSPC,
        errno.EDQUOT,
        errno.ENAMETOOLONG,
        errno.ELOOP,
        errno.ENOTDIR,
        errno.ENOENT,
    }
)


@dataclass(frozen=True)
class ArtifactCodes:
    """The error family of one kind of artifact."""

    failed: ErrorCode  # nothing was published: a definite failure before the link
    exists: ErrorCode  # the target is taken: nothing of the caller's was published
    uncertain: ErrorCode  # the link was attempted: the target may or may not exist
    changed: ErrorCode  # the stage, the target or the place is not what was written
    unreadable: ErrorCode  # an OSError or UnicodeError the caller's own handler reports

    def __post_init__(self) -> None:
        # Every code is a closed one, and the doubt after a link exits 5 in every family: it is
        # what a script acts on, and the publisher cannot choose it.
        for code in (self.failed, self.exists, self.uncertain, self.changed, self.unreadable):
            if type(code) is not str or code not in MESSAGES:
                raise ValueError("closed error code required")
        if YorungeError(self.uncertain).exit_code != 5:
            raise ValueError("the uncertain code of a family must exit 5")


class PublishLocation(Protocol):
    """Where the artifact goes: an open, verified directory and the target's name in it."""

    @property
    def descriptor(self) -> int: ...

    @property
    def name(self) -> str: ...

    @property
    def budget(self) -> Budget: ...

    def recheck(self) -> None: ...


@dataclass
class PublicationState:
    """Whether the link was attempted, shared with the caller's cancellation and error paths."""

    codes: ArtifactCodes
    attempted: bool = False

    def reraise(self, error: BaseException) -> NoReturn:
        if isinstance(error, asyncio.CancelledError):
            note = MESSAGES[self.codes.uncertain]
            if self.attempted and note not in getattr(error, "__notes__", ()):
                BaseException.add_note(error, note)
            raise error
        if self.attempted:
            if isinstance(error, YorungeError) and error.code == self.codes.uncertain:
                raise error
            raise YorungeError(self.codes.uncertain) from None
        if isinstance(error, (KeyboardInterrupt, YorungeError)):
            raise error
        if isinstance(error, (OSError, UnicodeError)):
            raise YorungeError(self.codes.unreadable) from None
        raise error


class ArtifactPublisher:
    def __init__(
        self,
        location: PublishLocation,
        state: PublicationState,
        check_source: Callable[[], None] = lambda: None,
        *,
        prefix: str = "",
    ) -> None:
        """``check_source`` re-checks what the artifact was made from (a stream has none);
        ``prefix`` starts the stage names ``publish_bytes`` makes (a stream names its own)."""
        if "/" in prefix:
            raise ValueError("a stage name prefix is part of one name")
        self.location, self.state, self.check_source = location, state, check_source
        self.codes, self.prefix = state.codes, prefix
        self.stage: str | None = None
        self.stage_identity: tuple[int, int] | None = None

    def ensure_absent(self) -> None:
        self.location.budget.check()
        self.location.recheck()
        try:
            os.stat(self.location.name, dir_fd=self.location.descriptor, follow_symlinks=False)
        except FileNotFoundError:
            return
        except OSError:
            raise YorungeError(self.codes.failed) from None
        raise YorungeError(self.codes.exists)

    def publish_bytes(self, content: bytes) -> None:
        """Publish ``content`` as the target, or fail without having replaced anything."""
        if not self.prefix:
            raise ValueError("a stage name prefix is required to publish bytes")
        self.ensure_absent()
        stage = f"{self.prefix}{uuid4().hex}.tmp"

        def staged() -> None:
            descriptor = os.open(
                stage,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=self.location.descriptor,
            )
            self.stage = stage
            with owned_descriptor(descriptor, close_code=self.codes.failed):
                self._publish_staged(descriptor, content)
            self.location.budget.check()

        self._guarded(staged)

    def publish_stage(self, stage: str, descriptor: int, size: int) -> None:
        """Publish a stage the caller opened, filled with ``size`` bytes and synced itself.

        The stage is the one name ``stage`` in the target's directory and ``descriptor`` is open
        on it. Until this returns or fails the stage is the publisher's, which removes it again by
        identity when publication fails, unless ``_discard`` keeps it; the caller does not touch it
        meanwhile. Everything after the write is the publisher's: verify, link, clean up, sync.
        """
        if not stage or "/" in stage or "\0" in stage or stage in (".", "..", self.location.name):
            raise ValueError("a stage is one name in the target's directory, and not the target's")

        def adopted() -> None:
            held = os.fstat(descriptor)
            try:
                named = os.stat(
                    self.location.name, dir_fd=self.location.descriptor, follow_symlinks=False
                )
            except OSError:
                named = None
            if named is not None and identity(named) == identity(held) and held.st_nlink == 1:
                # One directory entry under two spellings (case, normalization): cleaning the
                # "stage" up would delete the target. (A twin with two links is the trace of an
                # earlier publication and is judged as `changed` below.)
                raise ValueError("a stage cannot be the target under another spelling")
            self.stage = stage
            self.stage_identity = identity(held)
            self._finalize(descriptor, size, os.fstat(descriptor))

        self._guarded(adopted)

    def _guarded(self, action: Callable[[], None]) -> None:
        try:
            action()
        except BaseException as error:
            stranded = False
            try:
                self._discard(error)
            except (OSError, YorungeError):
                stranded = True
                _add_note_once(error, MESSAGES[self.codes.failed])
            try:
                if isinstance(error, OSError) and not self.state.attempted:
                    raise YorungeError(self.codes.failed) from None
                self.state.reraise(error)
            except BaseException as final:
                if stranded and final is not error and not self.state.attempted:
                    # Before the link the error was replaced by a closed one: the note that the
                    # stage may still be there goes with it. After the link the stage next to the
                    # target is the expected trace and the error already says the target may exist.
                    _add_note_once(final, MESSAGES[self.codes.failed])
                raise

    def _discard(self, error: BaseException) -> None:
        """What becomes of the stage when publication failed with ``error``.

        By default it is removed again by identity: content in memory can be written again, and
        a caller whose stage is not a resumable copy needs nothing else. A streaming sink, whose
        finished stage can be the only copy of a download, MUST override this: it keeps the stage
        for a failure that says nothing against it (an I/O error, a deadline, an interrupt) and
        removes it only for a definite refusal. ``error`` is the error as it happened, before it is
        mapped to the family's codes, so it cannot tell a refusal before the link from the same
        code after it: a refusal is definite only while ``not self.state.attempted``, because
        after the link the target may exist and a stage that is dropped then can be the last copy.
        The success path removes the stage itself.
        """
        self._remove_stage()

    def _publish_staged(self, descriptor: int, content: bytes) -> None:
        self.stage_identity = identity(os.fstat(descriptor))
        os.fchmod(descriptor, 0o600)
        self._write(descriptor, content)
        # FAT and exFAT give a file its inode number only once it holds a byte: learn it again.
        self.stage_identity = identity(os.fstat(descriptor))
        self._sync(descriptor)
        self._finalize(descriptor, len(content), os.fstat(descriptor))

    def _finalize(self, descriptor: int, size: int, written: os.stat_result) -> None:
        self.check_source()
        self.location.recheck()
        if written.st_size != size:
            raise YorungeError(self.codes.changed)  # not the bytes the caller says it wrote
        self._check_stage(written)
        self.location.budget.check()
        self._publish_link()
        self._check_target(descriptor, size, written.st_mtime_ns)
        self._remove_stage()
        self.stage = None  # the target now has one link, whatever an override of the removal did
        os.fsync(self.location.descriptor)
        self._sync(descriptor)
        self.check_source()
        self.location.recheck()
        self._check_target(descriptor, size, written.st_mtime_ns)
        self.location.budget.check()

    def _sync(self, descriptor: int) -> None:
        full_sync(descriptor)

    def _write(self, descriptor: int, content: bytes) -> None:
        pending = memoryview(content)
        while pending:
            self.location.budget.check()
            count = os.write(descriptor, pending[: 1024 * 1024])
            if not 0 < count <= len(pending[: 1024 * 1024]):
                raise YorungeError(self.codes.failed)
            pending = pending[count:]
        self.location.budget.check()

    def _check_stage(self, written: os.stat_result) -> None:
        if self.stage is None:
            raise YorungeError(self.codes.failed)
        info = os.stat(self.stage, dir_fd=self.location.descriptor, follow_symlinks=False)
        if (
            signature(info) != signature(written)
            or not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1
        ):
            raise YorungeError(self.codes.changed)

    def _publish_link(self) -> None:
        if self.stage is None:
            raise YorungeError(self.codes.failed)
        self.state.attempted = True
        refused = False
        try:
            os.link(
                self.stage,
                self.location.name,
                src_dir_fd=self.location.descriptor,
                dst_dir_fd=self.location.descriptor,
                follow_symlinks=False,
            )
        except FileExistsError:
            # This definite failure did not create the requested target.
            self.state.attempted = False
            raise YorungeError(self.codes.exists) from None
        except OSError as error:
            if error.errno not in LINK_REFUSED:
                raise  # an I/O error, a timeout of a network volume: the outcome cannot be told
            refused = True
        if refused:
            # The kernel rejected the call (no hard links here, no permission, no room, another
            # volume): a link either exists or the call failed, so nothing was published. Raised
            # outside the handler so that the OS error, which names paths, is not kept as context.
            self.state.attempted = False
            raise YorungeError(self.codes.failed)

    def _check_target(self, descriptor: int, size: int, mtime: int) -> None:
        held = os.fstat(descriptor)
        info = os.stat(self.location.name, dir_fd=self.location.descriptor, follow_symlinks=False)
        links = 2 if self.stage is not None else 1
        if (
            identity(info) != self.stage_identity
            or signature(info) != signature(held)
            or not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_uid != os.getuid()
            or info.st_size != size
            or info.st_mtime_ns != mtime
            or info.st_nlink != links
        ):
            raise YorungeError(self.codes.changed)

    def _remove_stage(self) -> None:
        """Remove the stage if the name still leads to the file that was staged.

        The identity is looked at and then the name is unlinked: POSIX offers no removal by
        identity, so a name that is swapped between the two calls is removed in its place. That
        interval is observed, not sandboxed; a stage name that an adversary can predict (a stream's)
        and a directory the adversary can write are what make it matter.
        """
        if self.stage is None:
            return
        if self.stage_identity is None:
            # The name is there, but whose file it is was never learned (the look at it failed):
            # it is not removed by guess, and the caller is told it may remain.
            raise YorungeError(self.codes.changed)
        try:
            info = os.stat(self.stage, dir_fd=self.location.descriptor, follow_symlinks=False)
        except FileNotFoundError:
            self.stage = None
            return
        if identity(info) != self.stage_identity:
            raise YorungeError(self.codes.changed)
        os.unlink(self.stage, dir_fd=self.location.descriptor)
        self.stage = None
