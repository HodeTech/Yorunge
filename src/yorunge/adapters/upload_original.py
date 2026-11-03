"""Private real original invocation; no public producer/client/proof injection."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import NoReturn

from yorunge.adapters.capability_cache import Clock, SystemClock
from yorunge.adapters.platform_upload_port import ObservedUploadPort, PreparedUploadCall
from yorunge.adapters.platform_upload_reader import ObservedUploadReader
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_http import UploadHttpxTransport, UploadSession
from yorunge.adapters.upload_input_files import UploadInputObservation, capture_upload_input
from yorunge.adapters.upload_preparation import (
    SessionFactory,
    UploadPreparationRuntime,
    require_upload_sync_context,
)
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import created_dataset, read_manifest
from yorunge.application.http_transport import HttpCredential
from yorunge.application.transfer_access import TransferWriteAccess
from yorunge.application.upload_arms import UploadArm
from yorunge.application.upload_budget import UploadBudget
from yorunge.application.upload_workflow import (
    CreateStage,
    EffectOutcome,
    PreparedEffect,
    create_and_link,
)
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.credentials import BoundCredential
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_transfer_v2 import TransferRecordV2
from yorunge.domain.dataset_upload import UploadPermission
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import ErrorCode, OperationError, YorungeError
from yorunge.domain.models import Context, Profile
from yorunge.domain.platform_upload import ProviderDataset
from yorunge.domain.state import canonical_uuid
from yorunge.domain.upload_checks import UploadCurrentCheck
from yorunge.domain.upload_versions import UploadPlan, UploadRecord

ContextLoader = Callable[[DatasetUploadPlanV2], tuple[Context, Profile]]


@dataclass(frozen=True, slots=True, repr=False)
class OriginalPhase:
    plan: UploadPlan
    record: UploadRecord
    existing: bool

    def __repr__(self) -> str:
        return "<original upload phase private>"

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("private upload phase cannot be serialized")


class _Call:
    def __init__(self, call: PreparedUploadCall, client: UploadHttpxTransport) -> None:
        self.call, self.client = call, client

    async def execute(self, arm: UploadArm) -> EffectOutcome:
        return await self.call.execute(self.client, arm)

    async def aclose(self) -> None:
        self.call.close()

    def __repr__(self) -> str:
        return "<bound upload call private>"


class _Environment:
    def __init__(
        self,
        runtime: UploadPreparationRuntime,
        plan: DatasetUploadPlanV2,
        bound: BoundCredential,
        inputs: UploadInputObservation,
        reader: ObservedUploadReader,
        port: ObservedUploadPort,
        client: UploadHttpxTransport,
        end: float,
    ) -> None:
        self.runtime, self.plan, self.bound, self.inputs = runtime, plan, bound, inputs
        self.reader, self.port, self.client, self.end = reader, port, client, end
        self.record: TransferRecordV2 | None = None
        self.access: TransferWriteAccess | None = None
        self.baseline: ProviderDataset | None = None
        self.memo: dict[tuple[UploadPermission, str | None], UploadCurrentCheck] = {}

    @contextmanager
    def repository(self) -> Iterator[StateUploads]:
        with open_existing_store(self.runtime.state_dir) as store:
            yield StateUploads(
                store, self.bound, clock=self.runtime.clock, write_access=self.access
            )

    def scope(self) -> None:
        with self.repository() as repository:
            repository.check_scope(self.plan.scope)

    async def current(self, kind: CreateStage) -> UploadCurrentCheck:
        self.scope()
        action: UploadPermission = "create_private_dataset" if kind == "create" else "link_project"
        expected = None if kind == "create" else self.baseline
        if kind != "create" and expected is None:
            raise YorungeError("operation_conflict")
        dataset_id = None if expected is None else expected.id
        key = action, dataset_id
        cached = self.memo.get(key)
        now = self.runtime.clock.now()
        if cached is not None and timedelta(0) <= now - instant(cached.checked_at) <= timedelta(
            seconds=30
        ):
            self.inputs.recheck()
            cached.require_current(
                self.plan,
                now=timestamp(self.runtime.clock.now()),
                action=action,
                dataset_id=dataset_id,
            )
            return cached
        check = await self.reader.current(
            self.client, self.plan, self.inputs, action=action, expected_dataset=expected
        )
        self.scope()
        check.require_current(
            self.plan, now=timestamp(self.runtime.clock.now()), action=action, dataset_id=dataset_id
        )
        self.memo[key] = check
        return check

    def admit(self, check: UploadCurrentCheck) -> bool:
        with self.repository() as repository:
            record = repository.admit(self.plan.plan_id, check)
            if type(record) is not TransferRecordV2:
                raise YorungeError("upload_plan_not_valid")
            self.record, self.access = record, repository.write_access
        # Another process may have won between the initial lookup and admission.
        # Its durable owner IDs cannot manufacture this process's write access.
        return self.access is not None

    def prepare(self, kind: CreateStage) -> PreparedEffect:
        assert self.record is not None
        if kind == "create":
            call = self.port.prepare_create(self.record.operation_id)
        else:
            assert self.record.dataset_id is not None
            call = self.port.prepare_link(self.record.operation_id, self.record.dataset_id)
        return _Call(call, self.client)

    def arm(self, check: UploadCurrentCheck, kind: CreateStage) -> UploadArm:
        assert self.record is not None and self.record.lease is not None
        self.inputs.recheck()
        with self.repository() as repository:
            arm = repository.arm(
                self.record.operation_id, self.record.lease, check, kind, None, total_end=self.end
            )
            record = repository.show(operation_id=self.record.operation_id).operation
            assert type(record) is TransferRecordV2
            self.record = record
            return arm

    def publish(self, outcome: EffectOutcome) -> None:
        assert self.record is not None and self.record.lease is not None
        with self.repository() as repository:
            view = repository.receipt(self.record.operation_id, self.record.lease, outcome.receipt)
            assert type(view.operation) is TransferRecordV2
            self.record = view.operation
            self.baseline = created_dataset(view)

    def _stop(self, operation_id: str) -> bool | None:
        with self.repository() as repository:
            view = repository.show(operation_id=operation_id)
            if view.plan.plan_id != self.plan.plan_id:
                return None
            record = view.operation
            assert record is not None
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
            return record.workflow_latched

    def failure(self, error: BaseException) -> OperationError | None:
        operation_id = self.record.operation_id if self.record is not None else None
        if isinstance(error, OperationError) and error.operation_id is not None:
            operation_id = error.operation_id
        if operation_id is None:
            return None
        code = _source_code(error)
        reason = error.reason_code if isinstance(error, OperationError) else None
        uncertain = isinstance(error, OperationError) and error.code == "operation_uncertain"
        try:
            latched = self._stop(operation_id)
        except YorungeError as marker_error:
            reason, uncertain = marker_error.code, True
        else:
            if latched is None:
                return error if isinstance(error, OperationError) else None
            uncertain = uncertain or latched
        if uncertain:
            return OperationError("operation_uncertain", operation_id, reason_code=reason or code)
        return OperationError(code, operation_id, reason_code=reason)

    def __repr__(self) -> str:
        return "<original upload environment private>"


def _plan_id(value: str) -> None:
    valid = False
    try:
        canonical_uuid(value)
        valid = True
    except (ValueError, TypeError, AttributeError):
        pass
    if not valid:
        raise YorungeError("invalid_request")


def _source_code(error: BaseException) -> ErrorCode:
    if isinstance(error, YorungeError):
        return error.code
    if isinstance(error, (asyncio.CancelledError, KeyboardInterrupt)):
        return "request_cancelled"
    return "transport_failed"


def _initial(
    plan_id: str, state_dir: Path | None, clock: Clock
) -> OriginalPhase | tuple[DatasetUploadPlanV2, DatasetManifest]:
    with open_existing_store(state_dir) as store:
        repository = StateUploads(store, clock=clock)
        view = repository.show(plan_id=plan_id)
        if view.operation is not None:
            return OriginalPhase(view.plan, view.operation, True)
        plan, approval = view.plan, view.approval
        if type(plan) is not DatasetUploadPlanV2 or plan.status == "draft":
            raise YorungeError("upload_plan_not_valid")
        if approval is None or approval.status != "approved":
            raise YorungeError("approval_required")
        now = clock.now()
        if not (instant(plan.prepared_at) <= now < instant(plan.expires_at)) or not (
            instant(approval.approved_at) <= now < instant(approval.expires_at)
        ):
            raise YorungeError("upload_plan_not_valid")
        return plan, read_manifest(store.connection, plan)


def _execute_create_link(
    runtime: UploadPreparationRuntime,
    plan: DatasetUploadPlanV2,
    bound: BoundCredential,
    inputs: UploadInputObservation,
    end: float,
) -> OriginalPhase:
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
    environment: _Environment | None = None

    async def consume(client: UploadHttpxTransport) -> TransferRecordV2:
        nonlocal environment
        environment = _Environment(runtime, plan, bound, inputs, reader, port, client, end)
        return await create_and_link(environment)

    failure = None
    record: TransferRecordV2 | None = None
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
    return OriginalPhase(plan, record, environment is not None and environment.access is None)


def create_link_original(
    plan_id: str,
    state_dir: Path | None,
    load_context: ContextLoader,
    *,
    session_factory: SessionFactory = UploadSession,
    clock: Clock | None = None,
) -> OriginalPhase:
    """Private r.1 phase; public start will bind the complete workflow later."""
    started = time.monotonic()
    require_upload_sync_context()
    _plan_id(plan_id)
    if state_dir is not None and not isinstance(state_dir, Path):
        raise YorungeError("invalid_request")
    clock = clock or SystemClock()
    loaded = _initial(plan_id, state_dir, clock)
    if isinstance(loaded, OriginalPhase):
        return loaded
    plan, manifest = loaded
    context, profile = load_context(plan)
    runtime = UploadPreparationRuntime(
        context, profile, state_dir, session_factory=session_factory, clock=clock
    )
    with runtime._invocation() as invocation_end:
        end = min(started + 900, invocation_end)
        bound, scope = runtime._bind(plan.scope.owner)
        if scope != plan.scope:
            raise YorungeError("state_changed")
        runtime._local_values(bound, runtime.context, plan.parameters, plan.storage)
        runtime._scope(bound, scope, plan.parameters.name)
        inputs = capture_upload_input(
            Path(plan.root.anchor),
            manifest,
            bound.credential.secret,
            end=end,
            expected_root=plan.root,
        )
        runtime._scope(bound, scope, plan.parameters.name)
        return _execute_create_link(runtime, plan, bound, inputs, end)
