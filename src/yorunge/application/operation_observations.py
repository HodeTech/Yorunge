"""Trusted read-only operation observation port, independent of execution approval."""

from dataclasses import dataclass, field
from typing import Annotated, Literal, Protocol

from pydantic import Field, model_validator

from yorunge.domain.capabilities import instant
from yorunge.domain.credentials import BoundCredential
from yorunge.domain.execution import ExecutionPlan
from yorunge.domain.operations import (
    AdmissionAuthority,
    DeliveryStatus,
    ExecutionStatus,
    OperationAdmission,
    OperationModel,
    OperationReason,
    OperationRecord,
    OperationStatus,
    ProviderExit,
    ProviderId,
    ProviderStatus,
    operation_status,
)


def authority_target(authority: AdmissionAuthority) -> tuple[object, ...]:
    return (
        authority.service_id,
        authority.service_origin,
        authority.api_base_path,
        authority.account_id,
        authority.project_id,
    )


@dataclass(frozen=True)
class ReadContext:
    authorities: tuple[AdmissionAuthority, ...]
    credentials: tuple[BoundCredential, ...] = field(repr=False)


@dataclass(frozen=True)
class ReadRequest:
    plan: ExecutionPlan
    admission: OperationAdmission
    attempt_id: str
    provider_run_id: str | None
    authorities: tuple[AdmissionAuthority, ...]
    credentials: tuple[BoundCredential, ...] = field(repr=False)


class ReadAccess(OperationModel):
    authorities: Annotated[tuple[AdmissionAuthority, ...], Field(min_length=1, max_length=3)]
    checked_at: str
    expires_at: str

    @model_validator(mode="after")
    def interval(self) -> "ReadAccess":
        if instant(self.checked_at) >= instant(self.expires_at):
            raise ValueError("read authorization interval required")
        return self


class OperationObservation(OperationModel):
    kind: Literal["observed", "not_found", "unauthorized", "cancel_accepted", "unavailable"]
    correlation: str
    authority: AdmissionAuthority
    provider_run_id: ProviderId | None
    provider_status: ProviderStatus | None
    provider_exit_code: ProviderExit | None
    execution_status: ExecutionStatus
    delivery_status: DeliveryStatus


class ReadPort(Protocol):
    def authorize(self, request: ReadRequest, *, deadline: float) -> ReadAccess:
        """Prove current read permission for the exact requested target/job scope."""
        ...

    def observe(
        self, request: ReadRequest, access: ReadAccess, *, deadline: float
    ) -> OperationObservation:
        """Read the same job; this port must not start, cancel, or fetch artifacts."""
        ...


def observed_status(record: OperationRecord, observation: OperationObservation) -> OperationStatus:
    if observation.execution_status == "not_started":
        raise ValueError("dispatch cannot become unstarted")
    if (
        record.summary.execution_status == "succeeded"
        and observation.execution_status != "succeeded"
    ):
        raise ValueError("confirmed execution cannot regress")
    if observation.execution_status == "succeeded" and observation.provider_exit_code not in (
        None,
        0,
    ):
        raise ValueError("contradictory success and exit code")
    return operation_status(
        observation.execution_status,
        observation.delivery_status,
        delivery_required=record.admission.delivery_required,
    )


def observed_reason(status: OperationStatus, execution: ExecutionStatus) -> OperationReason | None:
    if status == "failed":
        return "delivery_failed" if execution == "succeeded" else "provider_failed"
    if status == "cancelled":
        return "provider_cancelled"
    if status == "unknown":
        return "delivery_pending" if execution == "succeeded" else "provider_unavailable"
    if status == "running" and execution == "succeeded":
        return "delivery_pending"
    return None
