"""What a download does first, given what the directory holds: the start table as one function.

"Stage ve sidecar protokolü" of ``docs/reference/download-engine.md`` and ADR-0032 §3-§4. Pure:
the writer (a later step) observes the directory with ``lstat`` and ``fstat`` and describes what
it found in the types below; this module decides. It never sees a path, a descriptor or a clock.

Three rules hold for every row. The lock is an input: unless it is held, no decision removes,
truncates or rewrites anything. A file that is not provably the download's own (a regular file of
this user, mode 0600, one link, and for the sidecar small and well-formed) is never deleted or
altered, ``--no-resume`` included: the answer is ``download_partial_unverified``. And the order in
which things are removed is always the stage, then the sidecar, then the sidecar's temporary copy,
so that the worst interruption leaves a trace the next run discards.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from yorunge.domain.download import MAX_SIDECAR_BYTES, DownloadPartial
from yorunge.domain.download_response import ResumeAsk
from yorunge.domain.errors import ErrorCode

LockState = Literal["held", "busy", "unowned"]
Removal = Literal["stage", "sidecar", "sidecar_tmp"]
Action = Literal[
    "busy",  # download_busy: another download holds the lock; nothing is touched
    "output_exists",  # download_output_exists: the target is there; it is never touched
    "unverified",  # download_partial_unverified: a trace that cannot be proved ours; untouched
    "start_clean",  # remove what is listed, then create the stage exclusively
    "reuse_empty_stage",  # an empty stage of ours and nothing else: a clean start on it
    "resume",  # stage and sidecar fit: re-hash the prefix, then ask for the rest
    "publish_complete",  # a complete stage that fits: re-hash the prefix, then publish, no network
]
ERRORS: Final[dict[Action, ErrorCode]] = {
    "busy": "download_busy",
    "output_exists": "download_output_exists",
    "unverified": "download_partial_unverified",
}
# The order removals are always carried out in (then the directory is synced).
REMOVAL_ORDER: Final[tuple[Removal, ...]] = ("stage", "sidecar", "sidecar_tmp")
# After an exclusive link met a target that was there: the stage and the sidecar of this download.
REMOVE_AFTER_EXISTING_TARGET: Final[tuple[Removal, ...]] = ("stage", "sidecar")
# After an expected digest did not match: nothing of this download is kept (a kept complete stage
# would make every rerun an offline exit-7 loop).
REMOVE_AFTER_MISMATCH: Final[tuple[Removal, ...]] = ("stage", "sidecar", "sidecar_tmp")


@dataclass(frozen=True, slots=True)
class Entry:
    """One name in the directory, as ``lstat`` found it (and ``fstat`` after a safe open)."""

    regular: bool  # a regular file: not a symlink, FIFO, device or directory
    ours: bool  # owned by the current user
    private: bool  # mode exactly 0600
    nlink: int
    device: int
    inode: int
    size: int

    @property
    def owned(self) -> bool:
        """Provably this download's own kind of file: regular, ours, private, one link."""
        return self.regular and self.ours and self.private and self.nlink == 1


@dataclass(frozen=True, slots=True)
class SidecarState:
    """The sidecar: the file, and the record it holds when it holds a valid one."""

    entry: Entry
    record: DownloadPartial | None  # None: oversize, not canonical, wrong schema or version

    @property
    def file_owned(self) -> bool:
        return self.entry.owned and self.entry.size <= MAX_SIDECAR_BYTES


@dataclass(frozen=True, slots=True)
class StartDecision:
    action: Action
    remove: tuple[Removal, ...] = ()  # in REMOVAL_ORDER, under the lock
    record: DownloadPartial | None = None  # the sidecar's, for resume and publish_complete
    truncate_to: int | None = None  # a stage longer than its last checkpoint is cut back to it
    ask: ResumeAsk | None = None  # the conditional request of a resume

    @property
    def error(self) -> ErrorCode | None:
        return ERRORS.get(self.action)


def _same_file(a: Entry, b: Entry) -> bool:
    return (a.device, a.inode) == (b.device, b.inode)


def _owned_removals(
    stage: Entry | None, sidecar: SidecarState | None, tmp: Entry | None
) -> tuple[Removal, ...]:
    """What may be removed of the three: only what is present and provably ours, in order."""
    removals: list[Removal] = []
    if stage is not None and stage.owned:
        removals.append("stage")
    if sidecar is not None and sidecar.file_owned:
        removals.append("sidecar")
    if tmp is not None and tmp.owned:
        removals.append("sidecar_tmp")
    return tuple(removals)


def decide_start(
    *,
    lock: LockState,
    target: Entry | None,
    stage: Entry | None,
    sidecar: SidecarState | None,
    sidecar_tmp: Entry | None,
    identity_key: str,
    target_hash: str,
    no_resume: bool,
) -> StartDecision:
    """The row of the start table that this directory is in.

    ``target`` is whatever stands at the target's name (``None`` when nothing does);
    ``identity_key`` and ``target_hash`` are the download's own. A decision that resumes or
    publishes a complete stage still has to pass :func:`confirm_prefix` once the caller has
    re-hashed the prefix.
    """
    if lock == "busy":
        return StartDecision("busy")
    if lock != "held":
        return StartDecision("unverified")  # the lock object itself is not provably ours
    if target is not None:
        # Only the trace of our own interrupted publication (a stage hard-linked to the target,
        # two links) is cleaned; nothing else is touched, and the target never is.
        left_over = (
            stage is not None
            and stage.regular
            and stage.ours
            and stage.private
            and stage.nlink == 2
            and _same_file(stage, target)
        )
        if not left_over:
            return StartDecision("output_exists")
        removals: list[Removal] = ["stage"]
        if sidecar is not None and sidecar.file_owned:
            removals.append("sidecar")
        if sidecar_tmp is not None and sidecar_tmp.owned:
            removals.append("sidecar_tmp")
        return StartDecision("output_exists", tuple(removals))
    # A trace that is not provably ours stops the command; nothing is deleted, --no-resume included.
    if (
        (stage is not None and not stage.owned)
        or (sidecar is not None and not sidecar.file_owned)
        or (sidecar_tmp is not None and not sidecar_tmp.owned)
    ):
        return StartDecision("unverified")
    if stage is None:
        if sidecar is None:
            return StartDecision("start_clean", _owned_removals(None, None, sidecar_tmp))
        if sidecar.record is None:
            return StartDecision("unverified")  # a sidecar that cannot be read is not discarded
        return StartDecision("start_clean", _owned_removals(None, sidecar, sidecar_tmp))
    record = None if sidecar is None else sidecar.record
    if no_resume:
        # What is provably ours is removed, whatever the sidecar says; then a clean start.
        return StartDecision("start_clean", _owned_removals(stage, sidecar, sidecar_tmp))
    if sidecar is None or record is None:
        if sidecar is None and stage.size == 0:
            return StartDecision("reuse_empty_stage", _owned_removals(None, None, sidecar_tmp))
        return StartDecision("unverified")  # a full stage without a readable sidecar: not ours
    if (stage.device, stage.inode) != (record.stage_device, record.stage_inode):
        return StartDecision("unverified")  # the sidecar was written for another file
    discard = StartDecision("start_clean", _owned_removals(stage, sidecar, sidecar_tmp))
    if (
        record.identity_key != identity_key
        or record.target_hash != target_hash
        or stage.size < record.committed_bytes
    ):
        return discard
    keep = _owned_removals(None, None, sidecar_tmp)  # a leftover temporary copy goes either way
    cut = record.committed_bytes if stage.size > record.committed_bytes else None
    if record.complete:
        return StartDecision("publish_complete", keep, record, cut)
    if record.etag is None or record.total_size is None or record.committed_bytes == 0:
        # Kept only while a strong tag and the total are both known, and only if something is
        # committed to resume from.
        return discard
    ask = ResumeAsk(record.committed_bytes, record.total_size, record.etag)
    return StartDecision("resume", keep, record, cut, ask)


def confirm_prefix(decision: StartDecision, observed_sha256: str | None) -> StartDecision:
    """The decision once the stage's committed prefix has been re-read and hashed.

    A prefix that is not what the sidecar says (local corruption or tampering) is discarded, stage
    first, and the download starts clean. ``None`` means the prefix could not be read.
    """
    if decision.action not in ("resume", "publish_complete"):
        return decision
    assert decision.record is not None
    if observed_sha256 == decision.record.prefix_sha256:
        return decision
    return StartDecision("start_clean", ("stage", "sidecar"))
