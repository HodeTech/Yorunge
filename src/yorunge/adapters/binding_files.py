"""Publish a dataset-version binding next to its name: new, private, never over an existing file.

The common no-clobber artifact publisher (P02-3s) with the binding family's codes
(``binding_write_failed``, ``binding_output_exists``, ``binding_write_uncertain``): an exclusive
hard link of a private stage, so an existing target of any kind is left as it is. The target's
parent must exist and be reached through no symlink and is held open from before the provider is
asked until the binding is linked (the chain of ancestors is looked at again at the link). The
artifact holds no secret, no raw body and no description, author or address (the binding type has
no such field).
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from yorunge.adapters.artifact_publisher import (
    ArtifactCodes,
    ArtifactPublisher,
    PublicationState,
    PublishLocation,
)
from yorunge.adapters.local_files import full_sync
from yorunge.adapters.target_directory import TargetDirectory, open_target_directory
from yorunge.domain.dataset_version import DatasetVersionBinding
from yorunge.domain.errors import YorungeError

BINDING_CODES = ArtifactCodes(
    failed="binding_write_failed",
    exists="binding_output_exists",
    uncertain="binding_write_uncertain",
    changed="binding_write_failed",
    unreadable="binding_write_failed",
)


class BindingWriter(ArtifactPublisher):
    def __init__(
        self,
        location: PublishLocation,
        state: PublicationState,
        check_source: Callable[[], None],
    ) -> None:
        super().__init__(location, state, check_source, prefix=".yorunge-binding-")

    def publish(self, binding: DatasetVersionBinding) -> None:
        self.publish_bytes(binding.encoded())

    def _sync(self, descriptor: int) -> None:
        full_sync(descriptor)


class BindingTarget:
    """The new file a binding goes to, with its directory held open."""

    def __init__(self, directory: TargetDirectory, state: PublicationState) -> None:
        self.directory, self.state = directory, state

    def require_absent(self) -> None:
        """Say so before the provider is asked if the name is taken (the link decides last)."""
        try:
            os.stat(self.directory.name, dir_fd=self.directory.descriptor, follow_symlinks=False)
        except FileNotFoundError:
            return
        except OSError:
            raise YorungeError("binding_write_failed") from None
        raise YorungeError("binding_output_exists")

    def publish(self, binding: DatasetVersionBinding) -> None:
        BindingWriter(self.directory, self.state, lambda: None).publish(binding)


@contextmanager
def binding_target(target: Path) -> Iterator[BindingTarget]:
    """Hold the directory of ``target`` (absolute); any failure inside the block is a closed code.

    Before the link is attempted an error is what it is (or ``binding_write_failed`` for an OS
    error); after it, the outcome is ``binding_write_uncertain`` and nothing is retried.
    """
    state = PublicationState(BINDING_CODES)
    try:
        directory = open_target_directory(
            target, invalid="binding_write_failed", failed="binding_write_failed"
        )
        primary: BaseException | None = None
        try:
            yield BindingTarget(directory, state)
        except BaseException as error:
            primary = error
            raise
        finally:
            directory.close(primary)
    except BaseException as error:
        state.reraise(error)
