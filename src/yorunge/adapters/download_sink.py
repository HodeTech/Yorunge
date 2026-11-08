"""The local side of a download: lock, stage, sidecar and publication, in the closed order.

``docs/reference/download-engine.md`` ("Stage ve sidecar protokolü") and ADR-0032 §3-§4. One
:class:`DownloadSink` is one download's hold on one target: it takes the lock object of the target,
looks at what the directory holds, lets the pure start table (``domain.download_state``) decide,
carries the decision out in the fixed order, receives the body in blocks of at most 1 MiB with an
incremental SHA-256, keeps the sidecar a true account of the fsynced prefix, and publishes the
finished stage with the common no-clobber publisher (``artifact_publisher``).

The sink is synchronous: a write is one ``os.write`` of at most a block, and the engine that drives
it is the one with deadlines and cancellation (a callback is called between blocks, so that its
deadline can reach a long local read). Everything the sink writes is private (0600), nothing it
cannot prove is its own is ever removed or altered, and a failure that is no verdict about a
finished stage never discards it.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from yorunge.adapters.artifact_publisher import ArtifactCodes, ArtifactPublisher, PublicationState
from yorunge.adapters.download_files import (
    LockObject,
    TargetDirectory,
    acquire_lock,
    create_exclusive,
    describe,
    entry_of,
    open_checked,
    open_target_directory,
    read_small,
    remove_seen,
    replace_atomically,
    step,
    sync_directory,
)
from yorunge.adapters.input_files import close_descriptor
from yorunge.adapters.local_files import full_sync
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.download import (
    BLOCK_BYTES,
    CHECKPOINT_BYTES,
    EMPTY_SHA256,
    MAX_DOWNLOAD_BYTES,
    MAX_SIDECAR_BYTES,
    DownloadNames,
    DownloadPartial,
    Verification,
    download_names,
    target_hash,
    validate_target_name,
    verify_expectation,
)
from yorunge.domain.download_response import Disposition, DownloadResponse, ResumeAsk
from yorunge.domain.download_state import (
    REMOVAL_ORDER,
    REMOVE_AFTER_MISMATCH,
    Entry,
    Removal,
    SidecarState,
    StartDecision,
    confirm_prefix,
    decide_start,
    resumable,
)
from yorunge.domain.errors import DownloadIntegrityMismatch, YorungeError

DOWNLOAD_CODES = ArtifactCodes(
    failed="download_write_failed",
    exists="download_output_exists",
    uncertain="download_write_uncertain",
    changed="download_write_failed",
    unreadable="download_write_failed",
)

Phase = Literal["ready", "body", "complete", "published", "stopped"]


@dataclass(frozen=True, slots=True)
class SinkPlan:
    """What the directory calls for: a download (with a conditional request) or a publication."""

    action: Literal["download", "publish"]
    ask: ResumeAsk | None
    resumed_from: int


@dataclass(frozen=True, slots=True)
class Published:
    """The finished download: what was written, what it earns, and how much of it was held."""

    bytes: int
    sha256: str
    verification: Verification
    resumed_from_bytes: int


def _write_failed() -> YorungeError:
    return YorungeError("download_write_failed")


class DownloadPublisher(ArtifactPublisher):
    """The common publisher, with the download's cleanup order and its policy on a kept stage."""

    def __init__(self, sink: DownloadSink) -> None:
        super().__init__(sink.directory, PublicationState(DOWNLOAD_CODES))
        self.sink = sink

    def _publish_link(self) -> None:
        step("publish:before_link")
        super()._publish_link()
        step("publish:after_link")

    def _remove_stage(self) -> None:
        # Stage, then sidecar, then the temporary copy: the worst interruption leaves a trace the
        # next run discards. The base then syncs the directory.
        super()._remove_stage()
        step("cleanup:stage")
        self.sink.remove_present(("sidecar", "sidecar_tmp"))
        step("cleanup:all_removed")

    def _sync(self, descriptor: int) -> None:
        step("publish:directory_synced")
        super()._sync(descriptor)

    def _discard(self, error: BaseException) -> None:
        """Only a definite refusal of the name discards the stage and its sidecar.

        An I/O error, a deadline, an interrupt, a stage that is not what was written or a link the
        filesystem refuses say nothing against a finished stage: it is kept, and the next run
        finds it complete and publishes it (or, after a link that took place, finds the trace of
        this publication and cleans it).
        """
        if (
            isinstance(error, YorungeError)
            and error.code == self.codes.exists
            and not self.state.attempted
        ):
            self.sink.remove_present(("stage", "sidecar", "sidecar_tmp"))


class DownloadSink:
    """One download's hold on one target. Use :func:`open_sink`, which also releases it."""

    def __init__(
        self,
        directory: TargetDirectory,
        *,
        identity_key: str,
        no_resume: bool,
        clock: Callable[[], datetime],
        guard: Callable[[], None],
    ) -> None:
        self.directory = directory
        self.names: DownloadNames = download_names(directory.name)
        self.identity_key = identity_key
        self.target_hash = target_hash(directory.name)
        self.no_resume = no_resume
        self._clock, self._guard = clock, guard
        self._lock: LockObject | None = None
        self._stage: int | None = None
        self._phase: Phase = "ready"
        self._hasher = hashlib.sha256()
        self.written = 0
        self.committed = 0
        self.resumed_from = 0
        self._etag: str | None = None
        self._total: int | None = None
        self._created_at: str | None = None
        self._kept_sidecar = False  # a resume plan: the sidecar of an earlier run stands

    # --- steps 2-6: the lock, the look, the decision, its removals, the stage ---------------------

    def start(self) -> SinkPlan:
        fd = self.directory.descriptor
        self._lock = acquire_lock(fd, self.names.lock)
        for attempt in range(2):
            observed = self._observe()
            decision = decide_start(
                lock="held",
                target=observed.target,
                stage=observed.stage,
                sidecar=observed.sidecar,
                sidecar_tmp=observed.tmp,
                identity_key=self.identity_key,
                target_hash=self.target_hash,
                no_resume=self.no_resume,
            )
            step("decided")
            if decision.action in ("resume", "publish_complete"):
                decision = self._confirm(decision, observed)
            self._remove(decision.remove, observed)
            if decision.error is not None:
                raise YorungeError(decision.error)
            try:
                return self._act(decision, observed)
            except FileExistsError:
                # A foreign name appeared at the stage's: look again, once; then it is not ours.
                if attempt == 1:
                    raise YorungeError("download_partial_unverified") from None
        raise YorungeError("download_partial_unverified")  # pragma: no cover

    def _observe(self) -> _Observed:
        fd = self.directory.descriptor
        target = entry_of(fd, self.directory.name)
        stage = entry_of(fd, self.names.stage)
        tmp = entry_of(fd, self.names.sidecar_tmp)
        sidecar: SidecarState | None = None
        found = entry_of(fd, self.names.sidecar)
        if found is not None:
            record: DownloadPartial | None = None
            if found.owned and found.size <= MAX_SIDECAR_BYTES:
                try:
                    record = DownloadPartial.decode(read_small(fd, self.names.sidecar, found))
                except (ValueError, OSError):
                    record = None  # not a record of ours: the table decides what that means
            sidecar = SidecarState(found, record)
        return _Observed(target, stage, tmp, sidecar)

    def _confirm(self, decision: StartDecision, observed: _Observed) -> StartDecision:
        """Open the stage, hash the prefix the sidecar commits to, and let the table confirm."""
        record, stage = decision.record, observed.stage
        assert record is not None and stage is not None
        descriptor = open_checked(self.directory.descriptor, self.names.stage, stage, os.O_RDWR)
        hasher = hashlib.sha256()
        digest: str | None
        try:
            os.lseek(descriptor, 0, os.SEEK_SET)
            remaining = record.committed_bytes
            while remaining:
                self._guard()  # a deadline or an interrupt is not a verdict: it propagates
                block = os.read(descriptor, min(BLOCK_BYTES, remaining))
                if not block:
                    break
                hasher.update(block)
                remaining -= len(block)
            digest = hasher.hexdigest() if remaining == 0 else None
        except OSError:
            digest = None  # the prefix cannot be read: a local fault, and the table discards it
        except BaseException as error:
            close_descriptor(descriptor, error)
            raise
        confirmed = confirm_prefix(decision, digest)
        if confirmed.action == "start_clean":
            close_descriptor(descriptor)
            return confirmed
        self._stage = descriptor
        self._hasher = hasher
        return confirmed

    def _remove(self, removals: tuple[Removal, ...], observed: _Observed) -> None:
        """The removals of a decision, in the fixed order, then the directory is synced."""
        seen: dict[Removal, Entry | None] = {
            "stage": observed.stage,
            "sidecar": None if observed.sidecar is None else observed.sidecar.entry,
            "sidecar_tmp": observed.tmp,
        }
        done = False
        for name in REMOVAL_ORDER:
            entry = seen[name]
            if name in removals and entry is not None:
                remove_seen(self.directory.descriptor, getattr(self.names, name), entry, label=name)
                done = True
        if done:
            sync_directory(self.directory.descriptor)

    def _act(self, decision: StartDecision, observed: _Observed) -> SinkPlan:
        fd = self.directory.descriptor
        action = decision.action
        if action == "start_clean":
            self._stage = create_exclusive(fd, self.names.stage, label="stage")
            return SinkPlan("download", None, 0)
        if action == "reuse_empty_stage":
            assert observed.stage is not None
            self._stage = open_checked(fd, self.names.stage, observed.stage, os.O_RDWR)
            return SinkPlan("download", None, 0)
        record = decision.record
        assert record is not None and decision.prefix_checked and self._stage is not None
        if decision.truncate_to is not None:
            os.ftruncate(self._stage, decision.truncate_to)
        os.lseek(self._stage, record.committed_bytes, os.SEEK_SET)
        self.written = self.committed = record.committed_bytes
        self._etag, self._total, self._created_at = (
            record.etag,
            record.total_size,
            record.created_at,
        )
        self._kept_sidecar = True
        self.resumed_from = record.committed_bytes
        step("stage:confirmed")
        if action == "publish_complete":
            self._phase = "complete"
            return SinkPlan("publish", None, record.committed_bytes)
        return SinkPlan("download", decision.ask, record.committed_bytes)

    # --- step 8: the accepted answer --------------------------------------------------------------

    def begin(self, response: DownloadResponse, action: Disposition) -> None:
        """The answer was accepted: reset if the provider restarted; the header checkpoint.

        ``continue`` keeps the prefix (the sidecar of the earlier run already says it); ``full`` and
        ``restart`` start from the first byte of this answer. ``discard_and_retry`` is not handled
        here: :meth:`discard` first, then a request without a range.
        """
        self._require("ready")
        if action == "discard_and_retry":
            raise YorungeError("invalid_request")
        stage = self._open_stage()
        if action == "continue":
            if not self._kept_sidecar:
                raise YorungeError("invalid_request")
            self._phase = "body"
            return
        if self.written:
            os.ftruncate(stage, 0)  # the provider ignored the range (or the stage held a prefix)
            step("stage:truncated")
        os.lseek(stage, 0, os.SEEK_SET)
        self._hasher = hashlib.sha256()
        self.written = self.committed = 0
        self.resumed_from = 0
        self._etag = response.etag
        self._total = response.content_length if response.framing == "length" else None
        self._created_at = timestamp(self._now())
        self._write_sidecar()
        step("header_checkpoint")
        self._kept_sidecar = True
        self._phase = "body"

    def discard(self) -> None:
        """Drop the stage and the sidecar (stage first) and start from a fresh stage."""
        self._require("ready")
        self._close_stage()
        self.remove_present(("stage", "sidecar", "sidecar_tmp"))
        sync_directory(self.directory.descriptor)
        self._stage = create_exclusive(self.directory.descriptor, self.names.stage, label="stage")
        self._hasher = hashlib.sha256()
        self.written = self.committed = self.resumed_from = 0
        self._etag = self._total = self._created_at = None
        self._kept_sidecar = False

    # --- step 9: the body -------------------------------------------------------------------------

    def write(self, data: bytes | bytearray | memoryview) -> None:
        """Append ``data`` (any size) to the stage in blocks of at most 1 MiB."""
        self._require("body")
        stage = self._open_stage()
        view = memoryview(data)
        for offset in range(0, len(view), BLOCK_BYTES):
            block = view[offset : offset + BLOCK_BYTES]
            self._guard()
            self._write_block(stage, block)
            if self.written - self.committed >= CHECKPOINT_BYTES:
                self._checkpoint()

    def _write_block(self, stage: int, block: memoryview) -> None:
        pending = block
        while pending:
            if self.written + len(pending) > MAX_DOWNLOAD_BYTES:
                raise YorungeError("download_limit_exceeded")
            try:
                count = os.write(stage, pending)
            except OSError:
                raise _write_failed() from None
            if not 0 < count <= len(pending):
                raise _write_failed()
            self._hasher.update(pending[:count])
            self.written += count
            pending = pending[count:]
            step("body:written")

    def _checkpoint(self) -> None:
        """The bytes are made durable first, then the sidecar says how many (and their digest)."""
        stage = self._open_stage()
        try:
            os.fsync(stage)
        except OSError:
            raise _write_failed() from None
        step("checkpoint:stage_synced")
        self._write_sidecar(committed=self.written)
        self.committed = self.written
        step("checkpoint")

    def stop(self) -> None:
        """A clean stop: keep what can be resumed (a strong tag, a known total), else drop it.

        Called for an interrupt, a cancellation, a transport or deadline error; it never raises (it
        must not hide the reason for stopping). After the completion checkpoint the stage is whole
        and stays.
        """
        if self._phase in ("complete", "published", "stopped") or self._stage is None:
            return
        previous, self._phase = self._phase, "stopped"
        try:
            if previous == "ready":
                if self._kept_sidecar:
                    return  # nothing changed this run: the earlier run's stage and sidecar stand
                self._drop()
            elif resumable(etag=self._etag, total_size=self._total, committed_bytes=self.written):
                self._checkpoint()
            else:
                self._drop()
        except (OSError, YorungeError):
            pass

    def _drop(self) -> None:
        self._close_stage()
        self.remove_present(("stage", "sidecar", "sidecar_tmp"))
        sync_directory(self.directory.descriptor)

    # --- step 10: the body is whole ---------------------------------------------------------------

    def complete(self) -> None:
        """The body ended: sync the bytes and write the completion checkpoint (total fixed)."""
        self._require("body")
        stage = self._open_stage()
        if self._total is not None and self.written != self._total:
            raise YorungeError("download_incomplete")
        try:
            os.fsync(stage)
        except OSError:
            raise _write_failed() from None
        step("complete:stage_synced")
        self._total = self.written
        self._write_sidecar(committed=self.written)
        self.committed = self.written
        self._phase = "complete"
        step("completion_checkpoint")

    # --- steps 11-13: the comparison, the publication, the cleanup --------------------------------

    def publish(self, expected_sha256: str | None) -> Published:
        """Compare with the expectation, then publish: link, clean up, sync (all local I/O)."""
        self._require("complete")
        stage = self._open_stage()
        computed = self._hasher.hexdigest()
        try:
            verification = verify_expectation(computed, self.written, expected_sha256)
        except DownloadIntegrityMismatch:
            # A kept complete stage would make every rerun an offline loop of the same mismatch.
            self._close_stage()
            self._remove(REMOVE_AFTER_MISMATCH, self._observe_present())
            raise
        step("compared")
        try:
            full_sync(stage)
        except OSError:
            raise _write_failed() from None
        step("publish:synced")
        DownloadPublisher(self).publish_stage(self.names.stage, stage, self.written)
        self._phase = "published"
        return Published(self.written, computed, verification, self.resumed_from)

    # --- shared -----------------------------------------------------------------------------------

    def remove_present(self, removals: tuple[Removal, ...]) -> None:
        """Remove what stands there now and is provably ours, in the fixed order."""
        for name in REMOVAL_ORDER:
            if name not in removals:
                continue
            entry = entry_of(self.directory.descriptor, getattr(self.names, name))
            if entry is None:
                continue
            if not entry.owned:
                raise YorungeError("download_partial_unverified")
            remove_seen(self.directory.descriptor, getattr(self.names, name), entry, label=name)

    def _observe_present(self) -> _Observed:
        fd = self.directory.descriptor
        found = entry_of(fd, self.names.sidecar)
        return _Observed(
            None,
            entry_of(fd, self.names.stage),
            entry_of(fd, self.names.sidecar_tmp),
            None if found is None else SidecarState(found, None),
        )

    def _write_sidecar(self, *, committed: int = 0) -> None:
        stage = self._open_stage()
        created = self._created_at or timestamp(self._now())
        updated = max(timestamp(self._now()), created, key=instant)
        info = describe(os.fstat(stage))
        record = DownloadPartial.model_validate(
            {
                "schema_version": 1,
                "kind": "download_partial",
                "identity_key": self.identity_key,
                "target_hash": self.target_hash,
                "etag": self._etag,
                "total_size": self._total,
                "committed_bytes": committed,
                "prefix_sha256": self._hasher.hexdigest() if committed else EMPTY_SHA256,
                "stage_device": info.device,
                "stage_inode": info.inode,
                "created_at": created,
                "updated_at": updated,
            }
        )
        try:
            replace_atomically(
                self.directory.descriptor,
                self.names.sidecar_tmp,
                self.names.sidecar,
                record.encoded(),
                label="sidecar",
            )
        except OSError:
            raise _write_failed() from None
        self._created_at = created

    def _now(self) -> datetime:
        return self._clock()

    def _open_stage(self) -> int:
        if self._stage is None:
            raise YorungeError("invalid_request")
        return self._stage

    def _close_stage(self) -> None:
        if self._stage is not None:
            descriptor, self._stage = self._stage, None
            close_descriptor(descriptor, code="download_write_failed")

    def _require(self, phase: Phase) -> None:
        if self._phase != phase:
            raise YorungeError("invalid_request")

    def close(self) -> None:
        """Let go: the stage's descriptor, then the lock object (removed last), then the lock."""
        try:
            self._close_stage()
        finally:
            lock, self._lock = self._lock, None
            if lock is not None:
                lock.release()


@dataclass(frozen=True, slots=True)
class _Observed:
    target: Entry | None
    stage: Entry | None
    tmp: Entry | None
    sidecar: SidecarState | None


@contextmanager
def open_sink(
    target: Path,
    *,
    identity_key: str,
    no_resume: bool = False,
    clock: Callable[[], datetime] | None = None,
    guard: Callable[[], None] | None = None,
) -> Iterator[tuple[DownloadSink, SinkPlan]]:
    """Take the target: its directory, its lock, and what the directory calls for.

    ``guard`` is called between the blocks of a long local read or write: the engine's deadline.
    Whatever happens, the lock object is removed last and the descriptors are closed.
    """
    validate_target_name(target.name)
    directory = open_target_directory(target)
    sink = DownloadSink(
        directory,
        identity_key=identity_key,
        no_resume=no_resume,
        clock=clock or (lambda: datetime.now(UTC)),
        guard=guard or (lambda: None),
    )
    try:
        try:
            plan = sink.start()
        except BaseException:
            sink.close()
            raise
        try:
            yield sink, plan
        except BaseException:
            sink.stop()  # an interrupt, a cancellation, any error: keep what can be resumed
            raise
        finally:
            sink.close()
    finally:
        directory.close()
