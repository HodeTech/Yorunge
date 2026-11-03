"""Original-invocation algorithm; concrete IO remains in private outer composition."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol

from yorunge.application.upload_arms import UploadArm
from yorunge.application.upload_descriptors import PresignedUpload
from yorunge.domain.dataset_transfer import StageKind
from yorunge.domain.dataset_transfer_v2 import TransferRecordV2
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import OperationError
from yorunge.domain.upload_checks import UploadCurrentCheck
from yorunge.domain.upload_versions import UploadReceipt

class EffectOutcome(Protocol):
    @property
    def receipt(self) -> UploadReceipt: ...

    @property
    def upload(self) -> PresignedUpload | None: ...


class PreparedEffect(Protocol):
    async def execute(self, arm: UploadArm) -> EffectOutcome: ...
    async def aclose(self) -> None: ...


class OriginalEnvironment(Protocol):
    @property
    def plan(self) -> DatasetUploadPlanV2: ...

    @property
    def record(self) -> TransferRecordV2 | None: ...

    @property
    def write_owned(self) -> bool: ...

    async def current(self, kind: StageKind) -> UploadCurrentCheck: ...
    def admit(self, check: UploadCurrentCheck) -> bool: ...
    def prepare(self, kind: StageKind, index: int | None = None) -> PreparedEffect: ...
    def arm(
        self, check: UploadCurrentCheck, kind: StageKind, index: int | None = None
    ) -> UploadArm: ...
    def publish(self, outcome: EffectOutcome) -> None: ...
    def validate_uploads(self) -> None: ...
    async def verify(self) -> TransferRecordV2: ...
    def failure(self, error: BaseException) -> OperationError | None: ...


async def _guarded(
    environment: OriginalEnvironment,
    steps: Callable[[], Awaitable[TransferRecordV2]],
) -> TransferRecordV2:
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


async def _effect(
    environment: OriginalEnvironment, kind: StageKind, index: int | None = None
) -> None:
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


async def _drain(
    environment: OriginalEnvironment, tasks: list[asyncio.Task[EffectOutcome]]
) -> None:
    pending = set(tasks)
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        ordered = [task for task in tasks if task in done]
        _check_workers(ordered)
        for task in ordered:
            environment.publish(task.result())


async def _put_batch(environment: OriginalEnvironment, indices: range) -> None:
    calls: list[PreparedEffect] = []
    tasks: list[asyncio.Task[EffectOutcome]] = []
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
        await _drain(environment, tasks)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        for call in calls:
            await call.aclose()


async def _upload_files(environment: OriginalEnvironment) -> TransferRecordV2:
    record = await _create_link(environment)
    if not environment.write_owned:
        return record
    count = environment.plan.manifest.file_count
    for index in range(count):
        await _effect(environment, "presign", index)
    environment.validate_uploads()
    for start in range(0, count, 2):
        indices = range(start, min(count, start + 2))
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
