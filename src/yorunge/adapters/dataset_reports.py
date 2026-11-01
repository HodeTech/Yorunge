"""Private staged manifest publication with an exclusive hardlink, never overwrite."""

from __future__ import annotations

import asyncio
import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from typing import NoReturn
from uuid import uuid4

from yorunge.adapters.dataset_files import DatasetLocation, owned_descriptor
from yorunge.adapters.input_files import identity, signature
from yorunge.adapters.local_files import full_sync
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.errors import MESSAGES, YorungeError


@dataclass
class PublicationState:
    attempted: bool = False

    def reraise(self, error: BaseException) -> NoReturn:
        if isinstance(error, asyncio.CancelledError):
            note = MESSAGES["manifest_write_uncertain"]
            if self.attempted and note not in getattr(error, "__notes__", ()):
                BaseException.add_note(error, note)
            raise error
        if self.attempted:
            if isinstance(error, YorungeError) and error.code == "manifest_write_uncertain":
                raise error
            raise YorungeError("manifest_write_uncertain") from None
        if isinstance(error, (KeyboardInterrupt, YorungeError)):
            raise error
        if isinstance(error, (OSError, UnicodeError)):
            raise YorungeError("file_unreadable") from None
        raise error


class DatasetManifestWriter:
    def __init__(
        self,
        location: DatasetLocation,
        state: PublicationState,
        check_source: Callable[[], None],
    ) -> None:
        self.location, self.state, self.check_source = location, state, check_source
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
            raise YorungeError("manifest_write_failed") from None
        raise YorungeError("manifest_output_exists")

    def publish(self, manifest: DatasetManifest) -> None:
        content = manifest.encoded()
        self.ensure_absent()
        stage = f".yorunge-manifest-{uuid4().hex}.tmp"
        try:
            descriptor = os.open(
                stage,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=self.location.descriptor,
            )
            self.stage = stage
            with owned_descriptor(descriptor, close_code="manifest_write_failed"):
                self._publish_staged(descriptor, content)
            self.location.budget.check()
        except BaseException as error:
            try:
                self._remove_stage()
            except (OSError, YorungeError):
                BaseException.add_note(error, MESSAGES["manifest_write_failed"])
            if isinstance(error, OSError) and not self.state.attempted:
                raise YorungeError("manifest_write_failed") from None
            self.state.reraise(error)

    def _publish_staged(self, descriptor: int, content: bytes) -> None:
        self.stage_identity = identity(os.fstat(descriptor))
        os.fchmod(descriptor, 0o600)
        self._write(descriptor, content)
        full_sync(descriptor)
        written = os.fstat(descriptor)
        self.check_source()
        self.location.recheck()
        self._check_stage(written)
        self.location.budget.check()
        self._publish_link()
        self._check_target(descriptor, len(content), written.st_mtime_ns)
        self._remove_stage()
        os.fsync(self.location.descriptor)
        full_sync(descriptor)
        self.check_source()
        self.location.recheck()
        self._check_target(descriptor, len(content), written.st_mtime_ns)
        self.location.budget.check()

    def _write(self, descriptor: int, content: bytes) -> None:
        pending = memoryview(content)
        while pending:
            self.location.budget.check()
            count = os.write(descriptor, pending[: 1024 * 1024])
            if not 0 < count <= len(pending[: 1024 * 1024]):
                raise YorungeError("manifest_write_failed")
            pending = pending[count:]
        self.location.budget.check()

    def _check_stage(self, written: os.stat_result) -> None:
        if self.stage is None:
            raise YorungeError("manifest_write_failed")
        info = os.stat(self.stage, dir_fd=self.location.descriptor, follow_symlinks=False)
        if (
            signature(info) != signature(written)
            or not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1
        ):
            raise YorungeError("input_changed")

    def _publish_link(self) -> None:
        if self.stage is None:
            raise YorungeError("manifest_write_failed")
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
            raise YorungeError("manifest_output_exists") from None

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
            raise YorungeError("input_changed")

    def _remove_stage(self) -> None:
        if self.stage is None or self.stage_identity is None:
            return
        try:
            info = os.stat(self.stage, dir_fd=self.location.descriptor, follow_symlinks=False)
        except FileNotFoundError:
            self.stage = None
            return
        if identity(info) != self.stage_identity:
            raise YorungeError("input_changed")
        os.unlink(self.stage, dir_fd=self.location.descriptor)
        self.stage = None
