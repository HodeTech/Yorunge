"""Original-invocation algorithm; concrete IO remains in private outer composition."""

from __future__ import annotations

import asyncio
from typing import Literal, Protocol

from yorunge.application.upload_arms import UploadArm
from yorunge.application.upload_descriptors import PresignedUpload
from yorunge.domain.dataset_transfer_v2 import TransferRecordV2
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import OperationError
from yorunge.domain.upload_checks import UploadCurrentCheck
from yorunge.domain.upload_versions import UploadReceipt

CreateStage = Literal["create", "project_link"]


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

    async def current(self, kind: CreateStage) -> UploadCurrentCheck: ...
    def admit(self, check: UploadCurrentCheck) -> bool: ...
    def prepare(self, kind: CreateStage) -> PreparedEffect: ...
    def arm(self, check: UploadCurrentCheck, kind: CreateStage) -> UploadArm: ...
    def publish(self, outcome: EffectOutcome) -> None: ...
    def failure(self, error: BaseException) -> OperationError | None: ...


async def create_and_link(environment: OriginalEnvironment) -> TransferRecordV2:
    """A private phase, never a public successful-delivery result."""
    failure: OperationError | None = None
    try:
        current = await environment.current("create")
        if environment.admit(current):
            for kind in ("create", "project_link"):
                stage: CreateStage = kind
                check = await environment.current(stage)
                call = environment.prepare(stage)
                try:
                    arm = environment.arm(check, stage)
                    outcome = await call.execute(arm)
                    environment.publish(outcome)
                finally:
                    await call.aclose()
        record = environment.record
        assert record is not None
        return record
    except BaseException as error:
        # Cleanup may record uncertainty, but an actual Task cancellation must
        # still propagate. The outer sync bridge binds SIGINT separately.
        failure = environment.failure(error)
        if isinstance(error, asyncio.CancelledError):
            raise
        if failure is None:
            raise
    # Raise outside the rejected exception's active context, not merely with
    # suppress_context: even private source exception chains must be released.
    failure.__context__ = failure.__cause__ = None
    raise failure
