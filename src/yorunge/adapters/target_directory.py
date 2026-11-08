"""The directory of a file that is to be published: held open, reached without following a link.

One definition for every artifact that is published next to its name (a download, a binding): the
parent must exist and be reached through no symlink, the whole chain of ancestors is looked at again
before the artifact is linked, and the publication itself is local I/O with no deadline of its own.
The codes are the artifact family's: a path that cannot be a target, and a directory that changed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from yorunge.adapters.input_files import (
    Budget,
    close_descriptor,
    directory_chain,
    owned_descriptor,
)
from yorunge.domain.errors import ErrorCode, YorungeError
from yorunge.domain.models import is_reportable_path

Chain = tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class NoBudget:
    """The publication is local I/O and is exempt from any deadline."""

    def check(self) -> None:
        return None


@dataclass(frozen=True)
class TargetDirectory:
    """The directory of the target, held open, with the chain it was reached through."""

    anchor: Path
    descriptor: int
    chain: Chain
    budget: Budget = NoBudget()
    failed: ErrorCode = "download_write_failed"

    @property
    def name(self) -> str:
        return self.anchor.name

    def recheck(self) -> None:
        """The directory is still the one that was opened (every ancestor, by identity)."""
        try:
            descriptor, chain = directory_chain(str(self.anchor.parent))
            with owned_descriptor(descriptor, close_code=self.failed):
                if chain != self.chain:
                    raise YorungeError(self.failed)
        except OSError:
            raise YorungeError(self.failed) from None

    def close(self, primary: BaseException | None = None) -> None:
        """Close the handle; with an error in flight a failing close is a note on it."""
        close_descriptor(self.descriptor, primary, code=self.failed)


def open_target_directory(
    target: Path,
    *,
    invalid: ErrorCode = "download_target_invalid",
    failed: ErrorCode = "download_write_failed",
) -> TargetDirectory:
    """The target's directory exists and is reached without following a link (else ``invalid``).

    The target is also a path the result of the command can report (no control character, strict
    UTF-8, bounded): it is judged here, before anything is asked of the network, because the
    report is made after the artifact is linked and a report that is refused then would leave a
    file the command says nothing of.
    """
    if (
        not isinstance(target, Path)
        or not target.is_absolute()
        or not target.name
        or not is_reportable_path(str(target))
    ):
        raise YorungeError(invalid)
    try:
        descriptor, chain = directory_chain(str(target.parent))
    except (YorungeError, OSError):
        raise YorungeError(invalid) from None
    return TargetDirectory(target, descriptor, chain, failed=failed)
