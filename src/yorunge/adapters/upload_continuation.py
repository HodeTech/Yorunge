"""Private real continuation stages: the selected files of an admitted continuation.

Nothing here decides whether a continuation may start: its plan, its gates, the fresh look at the
dataset, the admission and the closing read are composed above this module. What is here runs the
stages of the files the plan selected. An environment owns one admitted operation, takes a fresh
check before each stage, commits the stage's intent and permit in the store before anything is
sent, and turns whatever goes wrong into the operation's own error. It is kept apart from the
original upload's environment so that the verified path of that upload stays byte-identical: the
two differ in what they may send (no create, no link, a subset of the files), in where the dataset
comes from (the plan, whose baseline is the lineage's) and in what a confirm counts.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from datetime import timedelta
from typing import Literal, TypeVar

from yorunge.adapters.platform_upload_port import ObservedUploadPort
from yorunge.adapters.platform_upload_reader import ObservedUploadReader
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_http import UploadHttpxTransport
from yorunge.adapters.upload_input_files import UploadInputObservation
from yorunge.adapters.upload_original import (
    _Call,
    _confirmed_indices,
    _failure_identity,
    _source_code,
)
from yorunge.adapters.upload_preparation import UploadPreparationRuntime
from yorunge.adapters.upload_repository import StateUploads
from yorunge.application import upload_descriptors as descriptors
from yorunge.application.http_transport import HttpCredential
from yorunge.application.transfer_access import TransferWriteAccess
from yorunge.application.upload_arms import UploadArm
from yorunge.application.upload_budget import UploadBudget
from yorunge.application.upload_progress import UploadCounter, count_upload
from yorunge.application.upload_workflow import EffectOutcome, PreparedEffect
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.credentials import BoundCredential
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.dataset_transfer import StageKind
from yorunge.domain.dataset_transfer_v3 import TransferRecordV3
from yorunge.domain.dataset_upload import COMMIT_MARGIN_SECONDS, UploadPermission
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.platform_upload import ProviderDataset
from yorunge.domain.upload_checks import UploadCurrentCheck
from yorunge.domain.upload_versions import graph_of

_Outcome = TypeVar("_Outcome")


class ContinuationStages:
    """The stage environment of one continuation: ``plan``, its baseline and, once admitted, the
    operation. ``baseline`` is the dataset the continuation extends (its root's); the repository
    refuses an arm whose fresh check names another dataset than the operation's."""

    def __init__(
        self,
        runtime: UploadPreparationRuntime,
        plan: DatasetContinuationPlanV3,
        bound: BoundCredential,
        inputs: UploadInputObservation,
        reader: ObservedUploadReader,
        port: ObservedUploadPort,
        client: UploadHttpxTransport,
        end: float,
        baseline: ProviderDataset,
        progress: UploadCounter | None = None,
    ) -> None:
        self.progress = progress  # counts the M selected files (the CLI's terminal line; cosmetic)
        self.runtime, self.plan, self.bound, self.inputs = runtime, plan, bound, inputs
        self.reader, self.port, self.client, self.end = reader, port, client, end
        self.baseline = baseline
        self.record: TransferRecordV3 | None = None
        self.access: TransferWriteAccess | None = None
        self.memo: UploadCurrentCheck | None = None
        self.contexts: dict[int, descriptors.FileContext] = {}
        self.uploads: dict[int, descriptors.PresignedUpload] = {}
        self.confirmed_count = 0

    @property
    def write_owned(self) -> bool:
        return self.access is not None

    @contextmanager
    def repository(self) -> Iterator[StateUploads]:
        with open_existing_store(self.runtime.state_dir) as store:
            yield StateUploads(
                store, self.bound, clock=self.runtime.clock, write_access=self.access
            )

    def scope(self) -> None:
        with self.repository() as repository:
            repository.check_scope(self.plan.scope)

    async def current(self, kind: StageKind) -> UploadCurrentCheck:
        """A fresh check that the key may still upload to the baseline (reused for 25 s)."""
        if kind not in ("presign", "put", "confirm"):
            raise YorungeError("invalid_request")  # a continuation has neither create nor link
        # A cancellation asked for so far is taken here, before a permit is armed: asyncio delivers
        # it at the next real suspension, and nothing between the admission and the first send
        # suspends.
        await asyncio.sleep(0)
        self.scope()
        action: UploadPermission = "upload_created_dataset"
        dataset_id = self.baseline.id
        cached = self.memo
        now = self.runtime.clock.now()
        if cached is not None and timedelta(0) <= now - instant(cached.checked_at) < timedelta(
            seconds=30 - COMMIT_MARGIN_SECONDS
        ):
            self.inputs.recheck()
            cached.require_current(
                self.plan,
                now=timestamp(self.runtime.clock.now()),
                action=action,
                dataset_id=dataset_id,
            )
            return cached
        self._renew_for_probe()
        check = await self.reader.current(
            self.client, self.plan, self.inputs, action=action, expected_dataset=self.baseline
        )
        self.scope()
        check.require_current(
            self.plan, now=timestamp(self.runtime.clock.now()), action=action, dataset_id=dataset_id
        )
        self.memo = check
        return check

    async def admission(self) -> UploadCurrentCheck:
        """The fresh check a continuation is admitted on: the permission to upload when it sends
        files, the permission to read the dataset when it sends none and only checks it."""
        if graph_of(self.plan).files:
            return await self.current("presign")
        self.scope()
        check = await self.reader.current(
            self.client,
            self.plan,
            self.inputs,
            action="read_created_dataset",
            expected_dataset=self.baseline,
        )
        self.scope()
        check.require_current(
            self.plan,
            now=timestamp(self.runtime.clock.now()),
            action="read_created_dataset",
            dataset_id=self.baseline.id,
        )
        return check

    def admit(self, check: UploadCurrentCheck) -> bool:
        with self.repository() as repository:
            record = repository.admit(self.plan.plan_id, check)
            if type(record) is not TransferRecordV3:
                raise YorungeError("upload_plan_not_valid")
            self.record, self.access = record, repository.write_access
        if self.progress is not None:
            self.progress.bind(record.operation_id)
        # Another process may have won between the initial lookup and admission. Its durable
        # owner IDs cannot manufacture this process's write access.
        return self.access is not None

    def _renew_for_probe(self) -> None:
        record = self.record
        if record is None or record.lease is None or self.access is None:
            return
        if instant(record.lease.expires_at) - self.runtime.clock.now() > timedelta(seconds=35):
            return
        with self.repository() as repository:
            repository.renew(record.operation_id, record.lease)
            current = repository.show(operation_id=record.operation_id).operation
            assert type(current) is TransferRecordV3
            self.record = current

    def _context(self, index: int | None) -> descriptors.FileContext:
        assert self.record is not None and self.record.dataset_id is not None
        if type(index) is not int or index not in graph_of(self.plan).files:
            raise YorungeError("invalid_request")
        if not self.contexts:
            self.contexts = {
                context.file_index: context
                for context in self.port.files(self.record.operation_id, self.record.dataset_id)
            }
        return self.contexts[index]

    def prepare(self, kind: StageKind, index: int | None = None) -> PreparedEffect:
        assert self.record is not None
        if kind == "presign":
            return _Call(self.port.prepare_presign(self._context(index)), self.client)
        if kind not in ("put", "confirm"):
            raise YorungeError("invalid_request")
        context = self._context(index)
        upload = self.uploads.get(context.file_index)
        if upload is None:
            raise YorungeError("invalid_response")
        if kind == "put":
            return _Call(self.port.prepare_put(upload), self.client)
        return _Call(
            self.port.prepare_confirm(upload, confirmed_count=self.confirmed_count + 1),
            self.client,
        )

    def validate_uploads(self) -> None:
        selection = graph_of(self.plan).files
        if set(self.uploads) != set(selection):
            raise YorungeError("invalid_response")
        descriptors.distinct_uploads(
            tuple(self.uploads[index] for index in selection),
            tuple(self._context(index) for index in selection),
            selection,
        )

    def arm(
        self, check: UploadCurrentCheck, kind: StageKind, index: int | None = None
    ) -> UploadArm:
        assert self.record is not None and self.record.lease is not None
        self.inputs.recheck()
        with self.repository() as repository:
            arm = repository.arm(
                self.record.operation_id, self.record.lease, check, kind, index, total_end=self.end
            )
            record = repository.show(operation_id=self.record.operation_id).operation
            assert type(record) is TransferRecordV3
            self.record = record
            return arm

    def publish(self, outcome: EffectOutcome) -> None:
        assert self.record is not None and self.record.lease is not None
        with self.repository() as repository:
            view = repository.receipt(self.record.operation_id, self.record.lease, outcome.receipt)
            assert type(view.operation) is TransferRecordV3
            self.record = view.operation
            kinds = {intent.intent_id: intent.kind for intent in view.intents}
            # What this operation's own journal accepted: the count a confirm reports builds on it.
            self.confirmed_count = sum(
                receipt.result == "accepted" and kinds[receipt.intent_id] == "confirm"
                for receipt in view.receipts
            )
            if outcome.upload is not None:
                self.uploads[outcome.upload.context.file_index] = outcome.upload
            confirmed = _confirmed_indices(view) if self.progress is not None else ()
        # Cosmetic I/O runs after the durable receipt transaction and its store are closed.
        if self.progress is not None:
            selection = graph_of(self.plan).files
            for index in confirmed:
                assert index is not None
                self.progress.confirm(selection.index(index))

    async def verify(self) -> TransferRecordV3:
        """The closing read: the proof of the whole dataset (N files), sent or already there."""
        from yorunge.adapters.upload_continuation_read import verify_continuation

        return await verify_continuation(self)

    def _stop(self, operation_id: str) -> Literal["terminal", "latched", "unlatched"] | None:
        with self.repository() as repository:
            view = repository.show(operation_id=operation_id)
            if view.plan.plan_id != self.plan.plan_id:
                return None
            record = view.operation
            assert record is not None
            if record.status in {"succeeded", "failed", "cancelled"}:
                return "terminal"
            if (
                self.access is not None
                and record.lease is not None
                and record.status in {"admitted", "running"}
            ):
                repository.stop_local(
                    operation_id,
                    record.lease,
                    "request_uncertain" if record.workflow_latched else "local_cancelled",
                )
            return "latched" if record.workflow_latched else "unlatched"

    def _sent_nothing(self, operation_id: str) -> bool:
        """Whether the stored record never wrote an intent (the latch is set with the first one).

        Read-only: no lease is needed to look. If the store cannot be read there is no answer, and
        what cannot be shown to be unsent is treated as sent.
        """
        try:
            with self.repository() as repository:
                record = repository.show(operation_id=operation_id).operation
        except YorungeError:
            return False
        return record is not None and not record.workflow_latched

    def failure(self, error: BaseException) -> OperationError | None:
        """What a failed stage leaves and says: a send that may have happened is uncertain (the
        operation stops, never replays); one that provably did not is a local cancellation."""
        operation_id = _failure_identity(self.record, error)
        if operation_id is None:
            return None
        code = _source_code(error)
        reason = error.reason_code if isinstance(error, OperationError) else None
        uncertain = isinstance(error, OperationError) and error.code == "operation_uncertain"
        try:
            latched = self._stop(operation_id)
        except YorungeError as marker_error:
            if not graph_of(self.plan).files or self._sent_nothing(operation_id):
                # A check-only continuation has sent nothing and never will, and one that fails
                # before its first intent has sent nothing yet: whatever stopped it, and whether or
                # not its stop could be written, nothing is uncertain (the lease cleanup cancels
                # the record).
                return OperationError(code, operation_id, reason_code=reason)
            return OperationError(
                "operation_uncertain", operation_id, reason_code=marker_error.code
            )
        if latched is None:
            return error if isinstance(error, OperationError) else None
        if latched == "terminal":
            return OperationError(
                "operation_conflict" if code == "operation_uncertain" else code,
                operation_id,
                reason_code=reason,
            )
        uncertain = uncertain or latched == "latched"
        if uncertain:
            return OperationError("operation_uncertain", operation_id, reason_code=reason or code)
        return OperationError(code, operation_id, reason_code=reason)

    def __repr__(self) -> str:
        return "<continuation stages environment private>"


def run_stages(
    runtime: UploadPreparationRuntime,
    plan: DatasetContinuationPlanV3,
    bound: BoundCredential,
    inputs: UploadInputObservation,
    baseline: ProviderDataset,
    end: float,
    algorithm: Callable[[ContinuationStages], Awaitable[_Outcome]],
) -> _Outcome:
    """One session with the continuation's own budget (no create, no link, M files), one
    environment and ``algorithm`` over it; a failure is the operation's own error.

    The algorithm gets the whole environment (its reader, port and client too), as the start of a
    continuation needs them for the fresh look before admission and the closing read after the
    stages; the stages themselves ask only what ``ContinuationEnvironment`` names."""
    if baseline.id != plan.continuation.dataset_id:
        raise YorungeError("invalid_request")  # what is extended is the plan's dataset, no other
    key = HttpCredential(
        "X-API-Key",
        bound.credential.secret,
        target=bound.credential.target,
        service_id="evren-platform",
    )
    budget = UploadBudget(
        plan.request_limits, end=min(end, time.monotonic() + 900), read_only=False
    )
    reader = ObservedUploadReader(plan.scope, key, budget, utc_clock=runtime.clock.now)
    port = ObservedUploadPort(
        plan, inputs.manifest, plan.scope, bound, key, budget, utc_clock=runtime.clock.now
    )
    environment: ContinuationStages | None = None

    sizes = tuple(inputs.manifest.files[index].size for index in graph_of(plan).files)

    async def consume(client: UploadHttpxTransport) -> _Outcome:
        nonlocal environment
        # A check-only continuation (M=0) sends no byte: there is nothing to count.
        counting: AbstractContextManager[UploadCounter | None] = (
            count_upload(sizes) if sizes else nullcontext(None)
        )
        with counting as progress:
            environment = ContinuationStages(
                runtime, plan, bound, inputs, reader, port, client, end, baseline, progress
            )
            return await algorithm(environment)

    failure = None
    record: _Outcome | None = None
    try:
        session = runtime._session(key, budget)
        with session:
            record = session.exchange(consume)
    except BaseException as error:
        failure = None if environment is None else environment.failure(error)
        if isinstance(error, asyncio.CancelledError):
            raise
        if failure is None:
            raise
    if failure is not None:
        failure.__context__ = failure.__cause__ = None
        raise failure
    assert record is not None
    return record
