"""Trusted internal coordination; no public execution backend or replay surface."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import NoReturn, Protocol

from yorunge.application.execution import ExecutionBudget
from yorunge.domain.capabilities import canonical
from yorunge.domain.credentials import BoundCredential
from yorunge.domain.errors import ErrorCode, OperationError, YorungeError
from yorunge.domain.execution import ExecutionPlan, ExecutionValidity
from yorunge.domain.operations import (
    AdmissionAuthority,
    JobView,
    OperationAdmission,
    OperationLease,
    OperationModel,
    OperationRecord,
    ProviderId,
    ProviderStatus,
)


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
    ) -> None:
        self.repository, self.validate, self.backend = repository, validate, backend
        self.credentials, self.budget, self.process_id = credentials, budget, process_id

    def admit(self, plan_id: str) -> OperationClaim:
        self.budget.check()
        existing = self.repository.existing(plan_id)
        if existing is not None:
            return OperationClaim(existing, None)
        plan = self.repository.plan(plan_id)
        validity = self.validate(plan)
        self.budget.check()
        return self.repository.admit(plan, validity)

    def renew(self, operation_id: str, owner: OperationLease) -> OperationLease:
        self.budget.check()
        return self.repository.renew(operation_id, owner)

    def takeover(self, operation_id: str) -> OperationClaim:
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
        before = self.repository.operation(operation_id)
        if before.dispatch_attempt_id is not None:
            raise OperationError("operation_conflict", operation_id)
        plan = self.repository.plan(before.admission.plan_id)
        validity = self.validate(plan)
        self.budget.check()
        armed = self.repository.arm(operation_id, owner, validity)
        permit = DispatchPermit(self.process_id)
        port_called = False
        try:
            window = self.repository.dispatch_window(operation_id, owner)
            request = DispatchRequest(
                plan, armed.admission, str(armed.dispatch_attempt_id), self.credentials
            )
            permit.consume()
            port_called = True
            receipt = self.backend.start(request, deadline=window.deadline)
            self.budget.check()
            receipt = Submission.model_validate_json(canonical(receipt.model_dump(mode="json")))
            if (
                receipt.correlation != armed.admission.correlation
                or receipt.authority not in armed.admission.authorities
            ):
                raise YorungeError("state_changed")
            return self.repository.submitted(operation_id, owner, receipt)
        except BaseException as error:
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
