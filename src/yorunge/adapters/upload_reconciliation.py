"""Private current read composition, independent of source files and write authority."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from yorunge.adapters.capability_cache import Clock, SystemClock
from yorunge.adapters.platform_upload_reader import ObservedUploadReader
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_http import UploadHttpxTransport, UploadSession
from yorunge.adapters.upload_preparation import (
    SessionFactory,
    UploadPreparationRuntime,
    require_upload_sync_context,
)
from yorunge.adapters.upload_reconcile_local import ReadInput, ReadPhase, load_read_input
from yorunge.adapters.upload_repository import StateUploads
from yorunge.application.http_transport import HttpCredential
from yorunge.application.upload_budget import UploadBudget
from yorunge.application.upload_reconciliation import reconcile_read
from yorunge.domain.capabilities import timestamp
from yorunge.domain.credentials import BoundCredential, normalize_target
from yorunge.domain.dataset_transfer import TERMINAL, TransferLease, scope_target
from yorunge.domain.dataset_transfer_v2 import TransferRecordV2, TransferVerificationV2
from yorunge.domain.dataset_upload import UploadScope
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import ErrorCode, OperationError, YorungeError
from yorunge.domain.models import Context, Profile
from yorunge.domain.state import canonical_uuid
from yorunge.domain.upload_checks import (
    READ_FAILURES,
    AuthorizationCheck,
    AuthorizationOutcome,
)

ContextLoader = Callable[[DatasetUploadPlanV2], tuple[Context, Profile]]


def _source_code(error: BaseException) -> ErrorCode:
    if isinstance(error, YorungeError):
        return error.code
    if isinstance(error, (asyncio.CancelledError, KeyboardInterrupt)):
        return "request_cancelled"
    return "transport_failed"


class _ReadEnvironment:
    def __init__(
        self,
        runtime: UploadPreparationRuntime,
        loaded: ReadInput,
        bound: BoundCredential,
        scope: UploadScope,
        reader: ObservedUploadReader,
        client: UploadHttpxTransport,
    ) -> None:
        self.runtime, self.loaded, self.bound, self.scope = runtime, loaded, bound, scope
        self.reader, self.client = reader, client
        self.record = loaded.record
        self.authorization: AuthorizationCheck | None = None
        self.owner: TransferLease | None = None

    @contextmanager
    def repository(self) -> Iterator[StateUploads]:
        with open_existing_store(self.runtime.state_dir) as store:
            # Deliberately no TransferWriteAccess in a restart/read invocation.
            yield StateUploads(store, self.bound, clock=self.runtime.clock)

    def inspect(self) -> None:
        loaded = load_read_input(
            self.record.operation_id, self.runtime.state_dir, True, self.runtime.clock
        )
        if not isinstance(loaded, ReadInput):
            raise YorungeError("operation_conflict")
        self.record = loaded.record
        with self.repository() as repository:
            repository.check_scope(self.scope)

    async def observe(self) -> ReadPhase:
        check = await self.current()
        return ReadPhase(self.loaded.plan, self.record, check)

    async def current(self) -> AuthorizationCheck:
        self.inspect()
        check = await self.reader.read_authorization(
            self.client, self.loaded.baseline, self.loaded.plan.parameters
        )
        self.authorization = check
        self.require_current(check)
        self.inspect()
        self.require_current(check)
        return check

    def require_current(self, check: AuthorizationCheck) -> None:
        # A real source-negative keeps its source code at the deadline. Only a
        # positive observation may proceed, and it must still fit this budget.
        if check.error_code is None:
            self.reader._budget._current()
        check.require_current(
            self.scope,
            "read_created_dataset",
            self.loaded.baseline.id,
            timestamp(self.runtime.clock.now()),
        )
        self.reader._budget._current()

    def _negative(self, code: ErrorCode) -> AuthorizationCheck:
        check = self.authorization
        if check is not None and check.error_code == code:
            return check
        outcome: AuthorizationOutcome = "unavailable"
        if code == "remote_access_denied":
            outcome = "denied"
        elif code == "invalid_response":
            outcome = "invalid"
        return self.reader._check(
            "read_created_dataset",
            self.loaded.baseline.id,
            timestamp(self.runtime.clock.now()),
            outcome,
            code,
        )

    def acquire(self, check: AuthorizationCheck) -> None:
        self.require_current(check)
        with self.repository() as repository:
            self.owner = repository.acquire_read(
                self.record.operation_id, authorization=check, accept_unverified_read=True
            )
            record = repository.show(operation_id=self.record.operation_id).operation
            assert type(record) is TransferRecordV2
            self.record = record

    async def metadata(self) -> TransferVerificationV2:
        from yorunge.adapters.upload_reconcile_metadata import observe_metadata

        return await observe_metadata(self)

    def commit(self, proof: TransferVerificationV2) -> TransferRecordV2:
        assert self.owner is not None and self.authorization is not None
        self.require_current(self.authorization)
        # Convert the remaining network-clock budget once, conservatively,
        # into the repository clock domain; neither deadline is extended.
        before = self.runtime.clock.monotonic()
        deadline = before + self.reader._budget.end - time.monotonic()
        with self.repository() as repository:
            view = repository.verified(
                self.record.operation_id,
                self.owner,
                proof,
                authorization=self.authorization,
                accept_unverified_read=True,
                deadline=deadline,
            )
            assert type(view.operation) is TransferRecordV2
            self.record, self.owner = view.operation, None
        return self.record

    def failure(self, error: BaseException) -> OperationError:
        code, operation_id = _source_code(error), self.record.operation_id
        reason = error.reason_code if isinstance(error, OperationError) else None
        try:
            with self.repository() as repository:
                view = repository.show(operation_id=operation_id)
                assert view.operation is not None
                record = view.operation
                if record.status in TERMINAL:
                    return OperationError(
                        "operation_conflict" if code == "operation_uncertain" else code,
                        operation_id,
                        reason_code=reason,
                    )
                if code in READ_FAILURES:
                    repository.read_failed(operation_id, self.owner, self._negative(code))
                elif self.owner is not None and record.lease is not None:
                    repository.stop_local(operation_id, self.owner, "request_uncertain")
        except YorungeError as marker:
            if code == "request_cancelled":
                return OperationError(code, operation_id, reason_code=marker.code)
            return OperationError(marker.code, operation_id, reason_code=code)
        return OperationError(code, operation_id, reason_code=reason)

    def __repr__(self) -> str:
        return "<readonly upload environment private>"


async def _complete_read(environment: _ReadEnvironment) -> ReadPhase:
    record = await reconcile_read(environment)
    return ReadPhase(environment.loaded.plan, record, None)


def _execute_read(
    runtime: UploadPreparationRuntime,
    loaded: ReadInput,
    bound: BoundCredential,
    scope: UploadScope,
    end: float,
    algorithm: Callable[[_ReadEnvironment], Awaitable[ReadPhase]],
) -> ReadPhase:
    if time.monotonic() >= end:
        raise YorungeError("execution_timeout")
    key = HttpCredential(
        "X-API-Key",
        bound.credential.secret,
        target=bound.credential.target,
        service_id="evren-platform",
    )
    budget = UploadBudget(loaded.plan.request_limits, end=end, read_only=True)
    reader = ObservedUploadReader(scope, key, budget, utc_clock=runtime.clock.now)
    environment: _ReadEnvironment | None = None

    async def consume(client: UploadHttpxTransport) -> ReadPhase:
        nonlocal environment
        environment = _ReadEnvironment(runtime, loaded, bound, scope, reader, client)
        return await algorithm(environment)

    failure = None
    try:
        session = runtime._session(key, budget)
        with session:
            return session.exchange(consume)
    except BaseException as error:
        if environment is not None:
            failure = environment.failure(error)
        else:
            failure = OperationError(_source_code(error), loaded.record.operation_id)
        if isinstance(error, asyncio.CancelledError):
            raise
    failure.__cause__ = failure.__context__ = None
    raise failure


def _validate_request(operation_id: str, state_dir: Path | None, accepted: bool) -> None:
    require_upload_sync_context()
    valid = type(accepted) is bool and (state_dir is None or isinstance(state_dir, Path))
    try:
        canonical_uuid(operation_id)
    except (ValueError, TypeError, AttributeError):
        valid = False
    if not valid:
        raise YorungeError("invalid_request")


def _bind_current(
    runtime: UploadPreparationRuntime, loaded: ReadInput
) -> tuple[BoundCredential, UploadScope]:
    target = normalize_target(runtime.context.platform_url)
    historical = loaded.plan.scope
    if (target.service_origin, target.api_base_path) != (
        historical.service_origin,
        historical.api_base_path,
    ):
        raise YorungeError("state_changed")
    bound, scope = runtime._bind(historical.owner)
    if scope_target(scope) != scope_target(historical):
        raise YorungeError("state_changed")
    runtime._local_values(bound, runtime.context, loaded.plan.parameters, loaded.plan.storage)
    return bound, scope


def _reconcile(
    operation_id: str,
    state_dir: Path | None,
    load_context: ContextLoader,
    algorithm: Callable[[_ReadEnvironment], Awaitable[ReadPhase]],
    *,
    accept_unverified_read: bool = False,
    session_factory: SessionFactory = UploadSession,
    clock: Clock | None = None,
) -> ReadPhase:
    end = time.monotonic() + 30
    _validate_request(operation_id, state_dir, accept_unverified_read)
    clock = clock or SystemClock()
    failure = None
    try:
        loaded = load_read_input(operation_id, state_dir, accept_unverified_read, clock)
        if isinstance(loaded, ReadPhase):
            return loaded
        context, profile = load_context(loaded.plan)
        runtime = UploadPreparationRuntime(
            context, profile, state_dir, session_factory=session_factory, clock=clock
        )
        with runtime._invocation():
            bound, scope = _bind_current(runtime, loaded)
            return _execute_read(runtime, loaded, bound, scope, end, algorithm)
    except BaseException as error:
        if isinstance(error, asyncio.CancelledError):
            raise
        failure = OperationError(
            _source_code(error),
            operation_id,
            reason_code=error.reason_code if isinstance(error, OperationError) else None,
        )
    failure.__cause__ = failure.__context__ = None
    raise failure


def probe_reconciliation(
    operation_id: str,
    state_dir: Path | None,
    load_context: ContextLoader,
    *,
    accept_unverified_read: bool = False,
    session_factory: SessionFactory = UploadSession,
    clock: Clock | None = None,
) -> ReadPhase:
    """Private S.1 observation only, without read lease or metadata proof."""
    return _reconcile(
        operation_id,
        state_dir,
        load_context,
        lambda environment: environment.observe(),
        accept_unverified_read=accept_unverified_read,
        session_factory=session_factory,
        clock=clock,
    )


def reconcile_upload(
    operation_id: str,
    state_dir: Path | None,
    load_context: ContextLoader,
    *,
    accept_unverified_read: bool = False,
    session_factory: SessionFactory = UploadSession,
    clock: Clock | None = None,
) -> ReadPhase:
    return _reconcile(
        operation_id,
        state_dir,
        load_context,
        _complete_read,
        accept_unverified_read=accept_unverified_read,
        session_factory=session_factory,
        clock=clock,
    )
