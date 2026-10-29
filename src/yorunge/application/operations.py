"""Trusted internal coordination; no public execution backend or replay surface."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import NoReturn, Protocol

from yorunge.application.execution import ExecutionBudget
from yorunge.application.operation_observations import (
    OperationObservation,
    ReadAccess,
    ReadContext,
    ReadPort,
    ReadRequest,
)
from yorunge.domain.capabilities import canonical
from yorunge.domain.credentials import BoundCredential
from yorunge.domain.errors import ErrorCode, OperationError, YorungeError
from yorunge.domain.execution import ExecutionPlan, ExecutionValidity
from yorunge.domain.operations import (
    TERMINAL,
    AdmissionAuthority,
    JobView,
    OperationAdmission,
    OperationLease,
    OperationModel,
    OperationReason,
    OperationRecord,
    ProviderId,
    ProviderStatus,
)
from yorunge.domain.state import canonical_uuid


@dataclass(frozen=True)
class OperationClaim:
    job: JobView
    ownership: OperationLease | None = field(repr=False)


@dataclass(frozen=True)
class DispatchWindow:
    record: OperationRecord
    deadline: float


@dataclass(frozen=True)
class DispatchRequest:
    plan: ExecutionPlan
    admission: OperationAdmission
    attempt_id: str
    credentials: tuple[BoundCredential, ...] = field(repr=False)


class Submission(OperationModel):
    correlation: str
    authority: AdmissionAuthority
    provider_run_id: ProviderId
    provider_status: ProviderStatus | None
    running: bool


class StartPort(Protocol):
    def start(self, request: DispatchRequest, *, deadline: float) -> Submission:
        """Use only the captured target/credential; honor the monotonic deadline."""
        ...


class OperationRepository(Protocol):
    def plan(self, plan_id: str) -> ExecutionPlan: ...
    def existing(self, plan_id: str) -> JobView | None: ...
    def operation(self, operation_id: str) -> OperationRecord: ...
    def admit(self, plan: ExecutionPlan, validity: ExecutionValidity) -> OperationClaim: ...
    def renew(self, operation_id: str, owner: OperationLease) -> OperationLease: ...
    def takeover(
        self, operation_id: str, validity: ExecutionValidity | None
    ) -> OperationClaim | None: ...
    def arm(
        self, operation_id: str, owner: OperationLease, validity: ExecutionValidity
    ) -> OperationRecord: ...
    def owned(
        self, operation_id: str, owner: OperationLease, *, execution: bool = False
    ) -> OperationRecord: ...
    def dispatch_window(self, operation_id: str, owner: OperationLease) -> DispatchWindow: ...
    def read_window(
        self,
        operation_id: str,
        owner: OperationLease,
        request: ReadRequest,
        access: ReadAccess | None = None,
    ) -> DispatchWindow: ...
    def reconcile(
        self,
        operation_id: str,
        owner: OperationLease,
        request: ReadRequest,
        access: ReadAccess,
        observation: OperationObservation,
    ) -> JobView: ...
    def reconciliation_uncertain(
        self, operation_id: str, owner: OperationLease, reason: OperationReason
    ) -> JobView: ...
    def job(self, operation_id: str) -> JobView: ...
    def submitted(
        self, operation_id: str, owner: OperationLease, receipt: Submission
    ) -> JobView: ...
    def uncertain(self, operation_id: str, owner: OperationLease) -> None: ...


class DispatchPermit:
    """An in-process one-shot capability; forked/copy/pickled permits are unusable."""

    def __init__(self, process_id: Callable[[], int]) -> None:
        self._process_id, self._issuer = process_id, process_id()
        self._lock, self._used = Lock(), False

    def consume(self) -> None:
        if self._process_id() != self._issuer:
            raise OperationError("operation_conflict")
        with self._lock:
            if self._used or self._process_id() != self._issuer:
                raise OperationError("operation_conflict")
            self._used = True

    def __copy__(self) -> NoReturn:
        raise TypeError("dispatch permits cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        raise TypeError("dispatch permits cannot be copied")

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("dispatch permits cannot be serialized")


class OperationCoordinator:
    def __init__(
        self,
        repository: OperationRepository,
        validate: Callable[[ExecutionPlan], ExecutionValidity],
        backend: StartPort,
        credentials: tuple[BoundCredential, ...],
        budget: ExecutionBudget,
        process_id: Callable[[], int],
        observer: ReadPort | None = None,
        resolve_read: Callable[[ExecutionPlan], ReadContext] | None = None,
    ) -> None:
        self.repository, self.validate, self.backend = repository, validate, backend
        self.credentials, self.budget, self.process_id = credentials, budget, process_id
        self._issuer = process_id()
        self.observer, self.resolve_read = observer, resolve_read

    def _same_process(self, operation_id: str | None = None) -> None:
        if self.process_id() != self._issuer:
            raise OperationError("operation_conflict", operation_id)

    @contextmanager
    def _identified(self, operation_id: str) -> Iterator[None]:
        try:
            canonical_uuid(operation_id)
        except (ValueError, TypeError, AttributeError):
            raise YorungeError("invalid_request") from None
        try:
            yield
        except OperationError as error:
            if error.operation_id is not None:
                raise
            raise OperationError(
                error.code,
                operation_id,
                reason_code=error.reason_code,
                capacity_kind=error.capacity_kind,
            ) from None
        except YorungeError as error:
            raise OperationError(error.code, operation_id) from None

    def admit(self, plan_id: str) -> OperationClaim:
        self._same_process()
        self.budget.check()
        existing = self.repository.existing(plan_id)
        if existing is not None:
            return OperationClaim(existing, None)
        plan = self.repository.plan(plan_id)
        validity = self.validate(plan)
        self.budget.check()
        return self.repository.admit(plan, validity)

    def renew(self, operation_id: str, owner: OperationLease) -> OperationLease:
        with self._identified(operation_id):
            self._same_process(operation_id)
            self.budget.check()
            return self.repository.renew(operation_id, owner)

    def takeover(self, operation_id: str) -> OperationClaim:
        with self._identified(operation_id):
            return self._takeover(operation_id)

    def _takeover(self, operation_id: str) -> OperationClaim:
        self._same_process(operation_id)
        self.budget.check()
        claim = self.repository.takeover(operation_id, None)
        if claim is not None:
            return claim
        record = self.repository.operation(operation_id)
        validity = self.validate(self.repository.plan(record.admission.plan_id))
        self.budget.check()
        claim = self.repository.takeover(operation_id, validity)
        if claim is None:
            raise OperationError("operation_conflict", operation_id)
        return claim

    def dispatch(self, operation_id: str, owner: OperationLease) -> JobView:
        with self._identified(operation_id):
            return self._dispatch(operation_id, owner)

    def _dispatch(self, operation_id: str, owner: OperationLease) -> JobView:
        self._same_process(operation_id)
        permit = DispatchPermit(self.process_id)
        before = self.repository.operation(operation_id)
        if before.dispatch_attempt_id is not None:
            raise OperationError("operation_conflict", operation_id)
        plan = self.repository.plan(before.admission.plan_id)
        validity = self.validate(plan)
        self.budget.check()
        armed = self.repository.arm(operation_id, owner, validity)
        self._same_process(operation_id)
        port_called = False
        try:
            window = self.repository.dispatch_window(operation_id, owner)
            request = DispatchRequest(
                plan, armed.admission, str(armed.dispatch_attempt_id), self.credentials
            )
            permit.consume()
            port_called = True
            receipt = self.backend.start(request, deadline=window.deadline)
            self._same_process(operation_id)
            self.budget.check()
            receipt = Submission.model_validate_json(canonical(receipt.model_dump(mode="json")))
            provider_fields = (receipt.provider_run_id, receipt.provider_status or "")
            if any(
                bound.credential.secret.reveal() in value
                for bound in self.credentials
                for value in provider_fields
            ):
                raise YorungeError("state_changed")
            if (
                receipt.correlation != armed.admission.correlation
                or receipt.authority not in armed.admission.authorities
            ):
                raise YorungeError("state_changed")
            return self.repository.submitted(operation_id, owner, receipt)
        except BaseException as error:
            self._same_process(operation_id)
            try:
                self.repository.uncertain(operation_id, owner)
            except (YorungeError, OSError):
                # The durable submitted latch remains even if uncertainty cannot be saved.
                pass
            if not isinstance(error, Exception):
                raise
            if not port_called and isinstance(error, YorungeError):
                raise OperationError(error.code, operation_id) from None
            reason: ErrorCode = (
                error.code if isinstance(error, YorungeError) else "operation_uncertain"
            )
            raise OperationError("operation_uncertain", operation_id, reason_code=reason) from None

    def reconcile(self, operation_id: str, owner: OperationLease) -> JobView:
        with self._identified(operation_id):
            self._same_process(operation_id)
            self.budget.check()
            record = self.repository.operation(operation_id)
            if record.summary.status in TERMINAL:
                return self.repository.job(operation_id)
            observer, resolve = self.observer, self.resolve_read
            if record.dispatch_attempt_id is None or observer is None or resolve is None:
                raise OperationError("operation_conflict", operation_id)
            job = self.repository.job(operation_id)
            context = resolve(job.plan)
            request = ReadRequest(
                job.plan,
                record.admission,
                record.dispatch_attempt_id,
                job.attempts[-1].provider_run_id,
                context.authorities,
                context.credentials,
            )
            result = self._read_observation(operation_id, owner, request, observer)
            if isinstance(result, str):
                return self.repository.reconciliation_uncertain(operation_id, owner, result)
            access, observation = result
            self.budget.check()
            return self._persist_observation(operation_id, owner, request, access, observation)

    def _read_observation(
        self,
        operation_id: str,
        owner: OperationLease,
        request: ReadRequest,
        observer: ReadPort,
    ) -> tuple[ReadAccess, OperationObservation] | OperationReason:
        window = self.repository.read_window(operation_id, owner, request)
        try:
            access = observer.authorize(request, deadline=window.deadline)
            self._same_process(operation_id)
            access = ReadAccess.model_validate_json(canonical(access.model_dump(mode="json")))
            window = self.repository.read_window(operation_id, owner, request, access)
            observation = observer.observe(request, access, deadline=window.deadline)
            self._same_process(operation_id)
            observation = OperationObservation.model_validate_json(
                canonical(observation.model_dump(mode="json"))
            )
            if any(
                bound.credential.secret.reveal() in value
                for bound in request.credentials
                for value in (observation.provider_run_id or "", observation.provider_status or "")
            ):
                raise ValueError("private observation")
            return access, observation
        except (ValueError, TypeError, AttributeError):
            self._same_process(operation_id)
            return "evidence_mismatch"
        except PermissionError:
            self._same_process(operation_id)
            return "provider_unauthorized"
        except YorungeError:
            raise
        except Exception:
            self._same_process(operation_id)
            return "provider_unavailable"

    def _persist_observation(
        self,
        operation_id: str,
        owner: OperationLease,
        request: ReadRequest,
        access: ReadAccess,
        observation: OperationObservation,
    ) -> JobView:
        try:
            return self.repository.reconcile(operation_id, owner, request, access, observation)
        except OperationError as error:
            if error.code not in {"state_write_failed", "state_busy", "execution_timeout"}:
                raise
            try:
                self.repository.reconciliation_uncertain(
                    operation_id, owner, "outcome_write_failed"
                )
            except YorungeError:
                pass
            raise OperationError(
                "operation_uncertain", operation_id, reason_code=error.code
            ) from None
