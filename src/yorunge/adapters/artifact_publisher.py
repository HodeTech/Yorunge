"""Staged, exclusive publication of one local artifact: never an overwrite, honest about doubt.

The principle is the manifest's, written once for every artifact that must reach a place the
user named without ever replacing what is there: a private stage is created in the target's own
directory with ``O_CREAT|O_EXCL|O_NOFOLLOW`` (mode 0600), filled and synced; what was staged is
verified; the stage is hard-linked to the target (``link()`` is exclusive: a taken name is a
definite failure, nothing of the caller's is published); the link, the stage's removal and the
target are verified again by identity; the directory and the file are synced. From the moment the
link is attempted a failure is *uncertain* (the target may or may not exist); before it, a failure
is definite and the stage is removed again by identity, whatever else happens.

What an artifact answers with is its own: the error family (:class:`ArtifactCodes`) is the
caller's, as is the stage name prefix. The steps that the families' tests inject faults into stay
overridable methods of the publisher (``_check_stage``, ``_publish_link``, ``_check_target``,
``_sync``), so that a caller can keep its own seams.

Two entries: :meth:`ArtifactPublisher.publish_bytes` for content held in memory, and
:meth:`ArtifactPublisher.publish_stage` for a stage the caller opened, wrote (a stream) and synced
itself: the publisher then owns only the order *verify, link, clean up, sync* and the identity
checks around it.
"""

from __future__ import annotations

import asyncio
import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from typing import NoReturn, Protocol
from uuid import uuid4

from yorunge.adapters.dataset_files import owned_descriptor
from yorunge.adapters.input_files import identity, signature
from yorunge.adapters.local_files import full_sync
from yorunge.domain.errors import MESSAGES, ErrorCode, YorungeError


@dataclass(frozen=True)
class ArtifactCodes:
    """The error family of one kind of artifact."""

    failed: ErrorCode  # nothing was published: a definite failure before the link
    exists: ErrorCode  # the target is taken: nothing of the caller's was published
    uncertain: ErrorCode  # the link was attempted: the target may or may not exist
    changed: ErrorCode  # the stage, the target or the place is not what was written
    unreadable: ErrorCode  # the operating system refused something before the link


class PublishBudget(Protocol):
    def check(self) -> None: ...


class PublishLocation(Protocol):
    """Where the artifact goes: an open, verified directory and the target's name in it."""

    @property
    def descriptor(self) -> int: ...

    @property
    def name(self) -> str: ...

    @property
    def budget(self) -> PublishBudget: ...

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
        check_source: Callable[[], None],
        *,
        prefix: str,
    ) -> None:
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

        The stage is ``stage`` in the target's directory and ``descriptor`` is open on it. Until
        this returns or fails it is the publisher's to remove again, by identity; the caller does
        not touch it. Everything after the write is the publisher's: verify, link, clean up, sync.
        """
        self.stage = stage
        self.stage_identity = identity(os.fstat(descriptor))
        self._guarded(lambda: self._finalize(descriptor, size, os.fstat(descriptor)))

    def _guarded(self, action: Callable[[], None]) -> None:
        try:
            action()
        except BaseException as error:
            try:
                self._remove_stage()
            except (OSError, YorungeError):
                BaseException.add_note(error, MESSAGES[self.codes.failed])
            if isinstance(error, OSError) and not self.state.attempted:
                raise YorungeError(self.codes.failed) from None
            self.state.reraise(error)

    def _publish_staged(self, descriptor: int, content: bytes) -> None:
        self.stage_identity = identity(os.fstat(descriptor))
        os.fchmod(descriptor, 0o600)
        self._write(descriptor, content)
        self._sync(descriptor)
        self._finalize(descriptor, len(content), os.fstat(descriptor))

    def _finalize(self, descriptor: int, size: int, written: os.stat_result) -> None:
        if written.st_size != size:
            raise YorungeError(self.codes.changed)  # not the bytes the caller says it wrote
        self.check_source()
        self.location.recheck()
        self._check_stage(written)
        self.location.budget.check()
        self._publish_link()
        self._check_target(descriptor, size, written.st_mtime_ns)
        self._remove_stage()
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
        if self.stage is None or self.stage_identity is None:
            return
        try:
            info = os.stat(self.stage, dir_fd=self.location.descriptor, follow_symlinks=False)
        except FileNotFoundError:
            self.stage = None
            return
        if identity(info) != self.stage_identity:
            raise YorungeError(self.codes.changed)
        os.unlink(self.stage, dir_fd=self.location.descriptor)
        self.stage = None
