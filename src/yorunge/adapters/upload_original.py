"""Private real original invocation; no public producer/client/proof injection."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Literal, NoReturn

from yorunge.adapters.capability_cache import Clock, SystemClock
from yorunge.adapters.platform_upload_port import ObservedUploadPort, PreparedUploadCall
from yorunge.adapters.platform_upload_put import PreparedPutCall
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
from yorunge.adapters.upload_store import VersionedTransferView, created_dataset, read_manifest
from yorunge.application import upload_descriptors as descriptors
from yorunge.application.http_transport import HttpCredential
from yorunge.application.transfer_access import TransferWriteAccess
from yorunge.application.upload_arms import UploadArm
from yorunge.application.upload_budget import UploadBudget
from yorunge.application.upload_inputs import require_distinct_upload_content
from yorunge.application.upload_progress import UploadCounter, count_upload
from yorunge.application.upload_workflow import (
    EffectOutcome,
    OriginalEnvironment,
    PreparedEffect,
    complete_original,
    create_and_link,
    create_link_and_upload,
)
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.credentials import BoundCredential
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_transfer import StageKind
from yorunge.domain.dataset_transfer_v2 import TransferRecordV2
from yorunge.domain.dataset_transfer_v3 import TransferRecordV3
from yorunge.domain.dataset_upload import COMMIT_MARGIN_SECONDS, UploadPermission
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import ErrorCode, OperationError, YorungeError
from yorunge.domain.models import Context, Profile
from yorunge.domain.platform_upload import ProviderDataset
from yorunge.domain.state import canonical_uuid
from yorunge.domain.upload_checks import UploadCurrentCheck
from yorunge.domain.upload_versions import UploadPlan, UploadRecord, graph_of

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
    def __init__(
        self, call: PreparedUploadCall | PreparedPutCall, client: UploadHttpxTransport
    ) -> None:
        self.call, self.client = call, client

    async def execute(self, arm: UploadArm) -> EffectOutcome:
        return await self.call.execute(self.client, arm)

    async def aclose(self) -> None:
        if isinstance(self.call, PreparedPutCall):
            await self.call.aclose()
        else:
            self.call.close()

    def __repr__(self) -> str:
        return "<bound upload call private>"


def _confirmed_indices(view: VersionedTransferView) -> tuple[int, ...]:
    accepted = {receipt.intent_id for receipt in view.receipts if receipt.result == "accepted"}
    indices = []
    for intent in view.intents:
        if intent.kind == "confirm" and intent.intent_id in accepted:
            assert intent.file_index is not None
            indices.append(intent.file_index)
    return tuple(indices)


def _failure_identity(
    record: TransferRecordV2 | TransferRecordV3 | None, error: BaseException
) -> str | None:
    operation_id = record.operation_id if record is not None else None
    if isinstance(error, OperationError) and error.operation_id is not None:
        operation_id = error.operation_id
    return operation_id


def _stopped_failure(
    latched: Literal["terminal", "latched", "unlatched"] | None,
    error: BaseException,
    operation_id: str,
    code: ErrorCode,
    reason: ErrorCode | None,
    uncertain: bool,
) -> OperationError | None:
    """What a failed stage says of its operation once the stop of that operation is known.

    Shared by both stage environments, which keep the rest of their failure path in step.
    ``code``, ``reason`` and ``uncertain`` are what ``error`` itself stands for.
    """
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
        progress: UploadCounter | None = None,
    ) -> None:
        self.runtime, self.plan, self.bound, self.inputs = runtime, plan, bound, inputs
        self.reader, self.port, self.client, self.end = reader, port, client, end
        self.record: TransferRecordV2 | None = None
        self.access: TransferWriteAccess | None = None
        self.baseline: ProviderDataset | None = None
        self.memo: dict[tuple[UploadPermission, str | None], UploadCurrentCheck] = {}
        self.contexts: tuple[descriptors.FileContext, ...] = ()
        self.uploads: dict[int, descriptors.PresignedUpload] = {}
        self.confirmed_count = 0
        self.progress = progress

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
        self.scope()
        action: UploadPermission = "upload_created_dataset"
        if kind == "create":
            action = "create_private_dataset"
        elif kind == "project_link":
            action = "link_project"
        expected = None if kind == "create" else self.baseline
        if kind != "create" and expected is None:
            raise YorungeError("operation_conflict")
        dataset_id = None if expected is None else expected.id
        key = action, dataset_id
        cached = self.memo.get(key)
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
            try:
                record = repository.admit(self.plan.plan_id, check)
            finally:
                # An admission whose closing gate failed still left an operation this invocation
                # admitted: that failure is its own to report, not another process's operation.
                self.access = repository.write_access
            if type(record) is not TransferRecordV2:
                raise YorungeError("upload_plan_not_valid")
            self.record = record
        if self.progress is not None:
            self.progress.bind(record.operation_id)
        # Another process may have won between the initial lookup and admission.
        # Its durable owner IDs cannot manufacture this process's write access.
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
            assert type(current) is TransferRecordV2
            self.record = current

    def _context(self, index: int | None) -> descriptors.FileContext:
        assert self.record is not None and self.record.dataset_id is not None
        if type(index) is not int or index not in graph_of(self.plan).files:
            raise YorungeError("invalid_request")
        if not self.contexts:
            self.contexts = self.port.files(self.record.operation_id, self.record.dataset_id)
        return self.contexts[index]

    def prepare(self, kind: StageKind, index: int | None = None) -> PreparedEffect:
        assert self.record is not None
        call: PreparedUploadCall | PreparedPutCall
        if kind == "create":
            call = self.port.prepare_create(self.record.operation_id)
        elif kind == "project_link":
            assert self.record.dataset_id is not None
            call = self.port.prepare_link(self.record.operation_id, self.record.dataset_id)
        elif kind == "presign":
            call = self.port.prepare_presign(self._context(index))
        else:
            context = self._context(index)
            upload = self.uploads.get(context.file_index)
            if upload is None:
                raise YorungeError("invalid_response")
            call = (
                self.port.prepare_put(upload)
                if kind == "put"
                else self.port.prepare_confirm(upload, confirmed_count=self.confirmed_count + 1)
            )
        return _Call(call, self.client)

    def validate_uploads(self) -> None:
        if set(self.uploads) != set(graph_of(self.plan).files):
            raise YorungeError("invalid_response")
        descriptors.distinct_uploads(
            tuple(self.uploads[index] for index in range(len(self.contexts))), self.contexts
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
            kinds = {intent.intent_id: intent.kind for intent in view.intents}
            self.confirmed_count = sum(
                receipt.result == "accepted" and kinds[receipt.intent_id] == "confirm"
                for receipt in view.receipts
            )
            confirmed = _confirmed_indices(view) if self.progress is not None else ()
            if outcome.upload is not None:
                self.uploads[outcome.upload.context.file_index] = outcome.upload
        # Cosmetic I/O runs after closing the durable receipt transaction/store.
        if self.progress is not None:
            for index in confirmed:
                assert index is not None
                self.progress.confirm(index)

    async def verify(self) -> TransferRecordV2:
        from yorunge.adapters.upload_original_read import verify_original

        return await verify_original(self)

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

    def failure(self, error: BaseException) -> OperationError | None:
        operation_id = _failure_identity(self.record, error)
        if operation_id is None:
            return None
        code = _source_code(error)
        reason = error.reason_code if isinstance(error, OperationError) else None
        uncertain = isinstance(error, OperationError) and error.code == "operation_uncertain"
        try:
            latched = self._stop(operation_id)
        except YorungeError as marker_error:
            return OperationError(
                "operation_uncertain", operation_id, reason_code=marker_error.code
            )
        return _stopped_failure(latched, error, operation_id, code, reason, uncertain)

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
        manifest = read_manifest(store.connection, plan)
        require_distinct_upload_content(manifest)
        return plan, manifest


def _execute_phase(
    runtime: UploadPreparationRuntime,
    plan: DatasetUploadPlanV2,
    bound: BoundCredential,
    inputs: UploadInputObservation,
    end: float,
    algorithm: Callable[[OriginalEnvironment], Awaitable[TransferRecordV2]],
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
        with count_upload(tuple(file.size for file in inputs.manifest.files)) as progress:
            environment = _Environment(
                runtime, plan, bound, inputs, reader, port, client, end, progress=progress
            )
            return await algorithm(environment)

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


def _original_phase(
    plan_id: str,
    state_dir: Path | None,
    load_context: ContextLoader,
    algorithm: Callable[[OriginalEnvironment], Awaitable[TransferRecordV2]],
    *,
    session_factory: SessionFactory = UploadSession,
    clock: Clock | None = None,
) -> OriginalPhase:
    """Private original workflow; a separate public layer provides safe summaries."""
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
        return _execute_phase(runtime, plan, bound, inputs, end, algorithm)


def create_link_original(
    plan_id: str,
    state_dir: Path | None,
    load_context: ContextLoader,
    *,
    session_factory: SessionFactory = UploadSession,
    clock: Clock | None = None,
) -> OriginalPhase:
    return _original_phase(
        plan_id,
        state_dir,
        load_context,
        create_and_link,
        session_factory=session_factory,
        clock=clock,
    )


def upload_files_original(
    plan_id: str,
    state_dir: Path | None,
    load_context: ContextLoader,
    *,
    session_factory: SessionFactory = UploadSession,
    clock: Clock | None = None,
) -> OriginalPhase:
    return _original_phase(
        plan_id,
        state_dir,
        load_context,
        create_link_and_upload,
        session_factory=session_factory,
        clock=clock,
    )


def run_upload_original(
    plan_id: str,
    state_dir: Path | None,
    load_context: ContextLoader,
    *,
    session_factory: SessionFactory = UploadSession,
    clock: Clock | None = None,
) -> OriginalPhase:
    return _original_phase(
        plan_id,
        state_dir,
        load_context,
        complete_original,
        session_factory=session_factory,
        clock=clock,
    )
