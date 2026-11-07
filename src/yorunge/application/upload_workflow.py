"""Original-invocation algorithm; concrete IO remains in private outer composition."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from typing import Protocol, TypeVar

from yorunge.application.upload_arms import UploadArm
from yorunge.application.upload_descriptors import PresignedUpload
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.dataset_transfer import StageKind
from yorunge.domain.dataset_transfer_v2 import TransferRecordV2
from yorunge.domain.dataset_transfer_v3 import TransferRecordV3
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.upload_checks import UploadCurrentCheck
from yorunge.domain.upload_versions import UploadReceipt, graph_of


class EffectOutcome(Protocol):
    @property
    def receipt(self) -> UploadReceipt: ...

    @property
    def upload(self) -> PresignedUpload | None: ...


class PreparedEffect(Protocol):
    async def execute(self, arm: UploadArm) -> EffectOutcome: ...
    async def aclose(self) -> None: ...


class StageEnvironment(Protocol):
    """What one effectful stage needs, whichever family of plan it belongs to."""

    async def current(self, kind: StageKind) -> UploadCurrentCheck: ...
    def prepare(self, kind: StageKind, index: int | None = None) -> PreparedEffect: ...
    def arm(
        self, check: UploadCurrentCheck, kind: StageKind, index: int | None = None
    ) -> UploadArm: ...
    def publish(self, outcome: EffectOutcome) -> None: ...
    def failure(self, error: BaseException) -> OperationError | None: ...


class OriginalEnvironment(StageEnvironment, Protocol):
    @property
    def plan(self) -> DatasetUploadPlanV2: ...

    @property
    def record(self) -> TransferRecordV2 | None: ...

    @property
    def write_owned(self) -> bool: ...

    def admit(self, check: UploadCurrentCheck) -> bool: ...
    def validate_uploads(self) -> None: ...
    async def verify(self) -> TransferRecordV2: ...


class ContinuationEnvironment(StageEnvironment, Protocol):
    """An admitted continuation: its selected files only, never a create or a link."""

    @property
    def plan(self) -> DatasetContinuationPlanV3: ...

    @property
    def record(self) -> TransferRecordV3 | None: ...

    @property
    def write_owned(self) -> bool: ...

    def admit(self, check: UploadCurrentCheck) -> bool: ...
    def validate_uploads(self) -> None: ...


Record = TypeVar("Record", TransferRecordV2, TransferRecordV3)


async def _guarded(
    environment: StageEnvironment,
    steps: Callable[[], Awaitable[Record]],
) -> Record:
    failure: OperationError | None = None
    try:
        return await steps()
    except BaseException as error:
        # Cleanup may record uncertainty, but an actual Task cancellation must
        # still propagate. The outer sync bridge binds SIGINT separately.
        failure = environment.failure(error)
        if isinstance(error, asyncio.CancelledError):
            raise
        if failure is None:
            raise
    failure.__context__ = failure.__cause__ = None
    raise failure


async def _effect(environment: StageEnvironment, kind: StageKind, index: int | None = None) -> None:
    check = await environment.current(kind)
    call = environment.prepare(kind, index)
    try:
        arm = environment.arm(check, kind, index)
        outcome = await call.execute(arm)
        environment.publish(outcome)
    finally:
        await call.aclose()


async def _create_link(environment: OriginalEnvironment) -> TransferRecordV2:
    current = await environment.current("create")
    if environment.admit(current):
        await _effect(environment, "create")
        await _effect(environment, "project_link")
    record = environment.record
    assert record is not None
    return record


async def create_and_link(environment: OriginalEnvironment) -> TransferRecordV2:
    """A private phase, never a public successful-delivery result."""
    return await _guarded(environment, lambda: _create_link(environment))


def _completed_error(tasks: list[asyncio.Task[EffectOutcome]]) -> BaseException | None:
    for task in tasks:
        if task.cancelled():
            try:
                task.result()
            except asyncio.CancelledError as cancelled:
                return cancelled
        error = task.exception()
        if error is not None:
            return error
    return None


def _check_workers(tasks: list[asyncio.Task[EffectOutcome]]) -> None:
    error = _completed_error([task for task in tasks if task.done()])
    if error is not None:
        raise error


def _prefer_failure(
    first: BaseException | None, later: BaseException | None
) -> BaseException | None:
    if first is None:
        return later
    if isinstance(later, asyncio.CancelledError) and not isinstance(first, asyncio.CancelledError):
        return later
    return first


def _publish_completed(
    environment: StageEnvironment,
    tasks: list[asyncio.Task[EffectOutcome]],
    attempted: set[asyncio.Task[EffectOutcome]],
) -> BaseException | None:
    failure: BaseException | None = None
    for task in tasks:
        if task in attempted or not task.done() or task.cancelled() or task.exception() is not None:
            continue
        # Publication itself can commit and then fail. Mark before entering it:
        # neither drain nor cancellation cleanup may submit this receipt twice.
        attempted.add(task)
        try:
            environment.publish(task.result())
        except BaseException as error:
            failure = _prefer_failure(failure, error)
    return failure


async def _drain(
    environment: StageEnvironment,
    tasks: list[asyncio.Task[EffectOutcome]],
    attempted: set[asyncio.Task[EffectOutcome]] | None = None,
) -> None:
    if attempted is None:
        attempted = set()
    pending = set(tasks)
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        ordered = [task for task in tasks if task in done]
        failure = _completed_error(ordered)
        failure = _prefer_failure(failure, _publish_completed(environment, ordered, attempted))
        if failure is not None:
            raise failure


async def _cleanup_batch(
    environment: StageEnvironment,
    calls: list[PreparedEffect],
    tasks: list[asyncio.Task[EffectOutcome]],
    attempted: set[asyncio.Task[EffectOutcome]],
    failure: BaseException | None,
) -> BaseException | None:
    for task in tasks:
        if not task.done():
            task.cancel()
    if tasks:
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except BaseException as error:
            failure = _prefer_failure(failure, error)
    # A cancelled worker may still have received and validated a response.
    # Intentional cleanup cancellations are not new primary worker failures.
    failure = _prefer_failure(failure, _publish_completed(environment, tasks, attempted))
    for call in calls:
        try:
            await call.aclose()
        except BaseException as error:
            failure = _prefer_failure(failure, error)
    return failure


async def _put_batch(environment: StageEnvironment, indices: Sequence[int]) -> None:
    calls: list[PreparedEffect] = []
    tasks: list[asyncio.Task[EffectOutcome]] = []
    attempted: set[asyncio.Task[EffectOutcome]] = set()
    failure: BaseException | None = None
    try:
        for index in indices:
            _check_workers(tasks)
            check = await environment.current("put")
            # A stale current probe yields to already armed workers. A failed
            # worker must stop the batch before another permit is committed.
            _check_workers(tasks)
            call = environment.prepare("put", index)
            calls.append(call)
            arm = environment.arm(check, "put", index)
            tasks.append(asyncio.create_task(call.execute(arm)))
        await _drain(environment, tasks, attempted)
    except BaseException as error:
        failure = error
    failure = await _cleanup_batch(environment, calls, tasks, attempted, failure)
    if failure is not None:
        raise failure


async def _upload_files(environment: OriginalEnvironment) -> TransferRecordV2:
    record = await _create_link(environment)
    if not environment.write_owned:
        return record
    graph = graph_of(environment.plan)
    for index in graph.files:
        await _effect(environment, "presign", index)
    environment.validate_uploads()
    for indices in graph.put_batches():
        await _put_batch(environment, indices)
        for index in indices:
            await _effect(environment, "confirm", index)
    assert environment.record is not None
    return environment.record


async def create_link_and_upload(environment: OriginalEnvironment) -> TransferRecordV2:
    """Complete all write receipts; metadata proof is a separate private phase."""
    return await _guarded(environment, lambda: _upload_files(environment))


async def complete_original(environment: OriginalEnvironment) -> TransferRecordV2:
    async def steps() -> TransferRecordV2:
        record = await _upload_files(environment)
        return await environment.verify() if environment.write_owned else record

    return await _guarded(environment, steps)


async def _send_selected(environment: ContinuationEnvironment) -> TransferRecordV3:
    record = environment.record
    if record is None:
        raise YorungeError("operation_conflict")  # nothing was admitted: nothing to send for
    if not environment.write_owned:
        return record
    graph = graph_of(environment.plan)
    for index in graph.files:
        await _effect(environment, "presign", index)
    if graph.files:  # a continuation that sends nothing has nothing to validate
        environment.validate_uploads()
    for indices in graph.put_batches():
        await _put_batch(environment, indices)
        for index in indices:
            await _effect(environment, "confirm", index)
    assert environment.record is not None
    return environment.record


async def continue_files(environment: ContinuationEnvironment) -> TransferRecordV3:
    """Send what an admitted continuation selected, the way an original upload sends its files.

    Every selected file is presigned, then put two at a time and confirmed one by one, each stage
    once and under its own committed permit; nothing is created or linked, and a continuation that
    selected no file sends nothing. Admission and the closing read belong to the caller.
    """
    return await _guarded(environment, lambda: _send_selected(environment))
