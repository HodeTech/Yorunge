"""Bounded operation history; stored progress is never execution authority."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from yorunge.domain.capabilities import (
    AuthorizationScope,
    Digest,
    PositiveInt64,
    WireModel,
    canonical,
    instant,
)
from yorunge.domain.credentials import normalize_target
from yorunge.domain.execution import ExecutionApproval, ExecutionPlan
from yorunge.domain.models import Execution, Identifier, Task
from yorunge.domain.state import canonical_uuid

MAX_OPERATIONS = 1024
MAX_ATTEMPTS = 16
MAX_EVENTS = 256
MAX_ADMISSION_BYTES = 8192
MAX_OPERATION_BYTES = 16384
MAX_ATTEMPT_BYTES = 4096
MAX_OUTCOME_BYTES = 4096
MAX_EVENT_BYTES = 1024
MAX_JOB_BYTES = 262144

OperationStatus = Literal[
    "admitted", "submitted", "running", "unknown", "succeeded", "failed", "cancelled"
]
AttemptStatus = Literal[
    "claimed", "abandoned", "submitted", "running", "unknown", "succeeded", "failed", "cancelled"
]
ExecutionStatus = Literal[
    "not_started", "submitted", "running", "unknown", "succeeded", "failed", "cancelled"
]
DeliveryStatus = Literal["not_required", "pending", "complete", "failed", "unknown"]
OperationReason = Literal[
    "identity_reset",
    "local_cancelled",
    "approval_revoked",
    "approval_expired",
    "approval_changed",
    "plan_invalid",
    "credential_changed",
    "lease_expired",
    "clock_changed",
    "owner_changed",
    "dispatch_interrupted",
    "provider_unavailable",
    "provider_not_found",
    "provider_unauthorized",
    "provider_rejected",
    "provider_failed",
    "provider_cancelled",
    "delivery_pending",
    "delivery_failed",
    "evidence_mismatch",
    "outcome_write_failed",
    "capacity_exceeded",
]
TERMINAL = frozenset({"succeeded", "failed", "cancelled"})
ProviderId = Annotated[str, Field(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9._:-]+$")]
ProviderStatus = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")]
ProviderExit = Annotated[int, Field(ge=-(2**31), le=2**31 - 1)]
AttemptNumber = Annotated[int, Field(ge=1, le=MAX_ATTEMPTS)]
EventNumber = Annotated[int, Field(ge=1, le=MAX_EVENTS)]
Fence = Annotated[int, Field(ge=0, le=2**63 - 1)]


def operation_status(
    execution: ExecutionStatus,
    delivery: DeliveryStatus,
    *,
    delivery_required: bool,
    local_terminal: Literal["failed", "cancelled"] | None = None,
) -> OperationStatus:
    """One reducer for every permitted execution/delivery pair."""
    if type(delivery_required) is not bool or (delivery == "not_required") == delivery_required:
        raise ValueError("delivery policy mismatch")
    allowed: dict[ExecutionStatus, frozenset[str]] = {
        "not_started": frozenset({"pending", "not_required"}),
        "submitted": frozenset({"pending", "not_required"}),
        "running": frozenset({"pending", "not_required"}),
        "unknown": frozenset({"pending", "unknown", "not_required"}),
        "succeeded": frozenset({"pending", "unknown", "failed", "complete", "not_required"}),
        "failed": frozenset({"pending", "not_required"}),
        "cancelled": frozenset({"pending", "not_required"}),
    }
    if delivery not in allowed[execution] or (
        local_terminal is not None and execution != "not_started"
    ):
        raise ValueError("invalid execution/delivery pair")
    if execution == "not_started":
        return local_terminal or "admitted"
    if execution == "succeeded":
        if delivery == "pending":
            return "running"
        if delivery == "unknown":
            return "unknown"
        return "failed" if delivery == "failed" else "succeeded"
    return execution


class OperationModel(WireModel):
    @field_validator(
        "operation_id",
        "plan_id",
        "store_id",
        "attempt_id",
        "owner_id",
        "identity_epoch",
        "admission_identity_epoch",
        "ownership_identity_epoch",
        "correlation",
        "observed_identity_epoch",
        "dispatch_attempt_id",
        "credential_id",
        check_fields=False,
    )
    @classmethod
    def uuid_field(cls, value: str | None) -> str | None:
        return None if value is None else canonical_uuid(value)

    @field_validator(
        "created_at", "updated_at", "recorded_at", "expires_at", "observed_at", check_fields=False
    )
    @classmethod
    def time_field(cls, value: str) -> str:
        instant(value)
        return value


class AdmissionAuthority(OperationModel):
    service_id: Literal["local", "evren-platform", "evren-llm"]
    service_origin: str | None
    api_base_path: str | None
    account_id: Identifier | None
    project_id: Identifier | None
    credential_id: str | None
    credential_revision: PositiveInt64 | None
    authorization_scope: AuthorizationScope | None

    @model_validator(mode="after")
    def authority(self) -> AdmissionAuthority:
        remote = (
            self.service_origin,
            self.api_base_path,
            self.credential_id,
            self.credential_revision,
        )
        if self.service_id == "local":
            if any(value is not None for value in (*remote, self.authorization_scope)):
                raise ValueError("local authority cannot carry remote credentials")
        elif any(value is None for value in remote):
            raise ValueError("remote authority requires target and credential")
        else:
            target = normalize_target(str(self.service_origin) + str(self.api_base_path))
            if (target.service_origin, target.api_base_path) != (
                self.service_origin,
                self.api_base_path,
            ):
                raise ValueError("canonical target required")
        return self


class OperationAdmission(OperationModel):
    schema_version: Literal[1] = 1
    operation_id: str
    plan_id: str
    plan_digest: Digest
    store_id: str
    admission_identity_epoch: str
    admission_clock_generation: PositiveInt64
    approval: ExecutionApproval
    authorities: Annotated[tuple[AdmissionAuthority, ...], Field(min_length=1, max_length=3)]
    correlation: str
    delivery_required: bool

    @model_validator(mode="after")
    def evidence(self) -> OperationAdmission:
        record = self.approval
        if record.status != "approved" or (
            record.plan_id,
            record.plan_digest,
            record.store_id,
            record.identity_epoch,
            record.clock_generation,
        ) != (
            self.plan_id,
            self.plan_digest,
            self.store_id,
            self.admission_identity_epoch,
            self.admission_clock_generation,
        ):
            raise ValueError("admission approval mismatch")
        keys = tuple(canonical(authority.model_dump(mode="json")) for authority in self.authorities)
        if (
            keys != tuple(sorted(set(keys)))
            or len(canonical(self.model_dump(mode="json"))) > MAX_ADMISSION_BYTES
        ):
            raise ValueError("bounded canonical admission required")
        return self


class JobSummary(OperationModel):
    operation_id: str
    plan_id: str
    plan_digest: Digest
    task: Task
    tool: Identifier | None
    execution: Execution
    created_at: str
    updated_at: str
    status: OperationStatus
    execution_status: ExecutionStatus
    delivery_status: DeliveryStatus
    attempt_count: AttemptNumber
    revision: PositiveInt64
    clock_anomaly: bool


def validate_reason(status: str, reason: OperationReason | None) -> None:
    reasons: dict[str, set[str | None]] = {
        "claimed": {None},
        "submitted": {None},
        "succeeded": {None},
        "running": {None, "delivery_pending"},
        "abandoned": {"owner_changed", "lease_expired", "clock_changed"},
        "unknown": {
            "identity_reset",
            "lease_expired",
            "clock_changed",
            "owner_changed",
            "dispatch_interrupted",
            "provider_unavailable",
            "provider_not_found",
            "provider_unauthorized",
            "evidence_mismatch",
            "outcome_write_failed",
            "delivery_pending",
            "capacity_exceeded",
        },
        "failed": {
            "plan_invalid",
            "provider_rejected",
            "provider_failed",
            "delivery_failed",
            "approval_revoked",
            "approval_expired",
            "approval_changed",
            "credential_changed",
            "capacity_exceeded",
        },
        "cancelled": {"identity_reset", "local_cancelled", "provider_cancelled"},
    }
    if status not in reasons or reason not in reasons[status]:
        raise ValueError("status reason mismatch")


def validate_progress_reason(
    status: OperationStatus,
    reason: OperationReason | None,
    execution: ExecutionStatus,
    delivery: DeliveryStatus,
    *,
    dispatched: bool,
) -> None:
    validate_reason("claimed" if status == "admitted" else status, reason)
    if status == "running":
        expected = (
            "delivery_pending" if execution == "succeeded" and delivery == "pending" else None
        )
        if reason != expected:
            raise ValueError("running reason must reflect delivery")
    if status == "failed":
        allowed = (
            {"provider_failed", "provider_rejected"}
            if dispatched
            else {
                "plan_invalid",
                "approval_revoked",
                "approval_expired",
                "approval_changed",
                "credential_changed",
                "capacity_exceeded",
            }
        )
        if execution == "succeeded" and delivery == "failed" and dispatched:
            allowed = {"delivery_failed"}
        if reason not in allowed:
            raise ValueError("failure reason must reflect dispatch")
    if status == "cancelled" and reason not in (
        {"provider_cancelled"} if dispatched else {"identity_reset", "local_cancelled"}
    ):
        raise ValueError("cancellation requires phase-specific proof")


class AttemptView(OperationModel):
    attempt_id: str
    number: AttemptNumber
    created_at: str
    updated_at: str
    status: AttemptStatus
    provider_run_id: ProviderId | None
    provider_status: ProviderStatus | None
    provider_exit_code: ProviderExit | None
    reason_code: OperationReason | None

    @model_validator(mode="after")
    def reason(self) -> AttemptView:
        validate_reason(self.status, self.reason_code)
        if self.status in ("claimed", "abandoned") and any(
            value is not None
            for value in (
                self.provider_run_id,
                self.provider_status,
                self.provider_exit_code,
            )
        ):
            raise ValueError("unsubmitted attempts cannot claim provider progress")
        if len(canonical(self.model_dump(mode="json"))) > MAX_ATTEMPT_BYTES:
            raise ValueError("bounded attempt required")
        return self


class OperationOutcome(OperationModel):
    schema_version: Literal[1] = 1
    recorded_at: str
    execution_status: ExecutionStatus
    delivery_status: DeliveryStatus
    provider_exit_code: ProviderExit | None
    reason_code: OperationReason | None


class OperationLease(OperationModel):
    owner_id: str
    fence: PositiveInt64
    ownership_identity_epoch: str
    ownership_clock_generation: PositiveInt64
    expires_at: str

    def token(self) -> tuple[str, int, str, int]:
        return (
            self.owner_id,
            self.fence,
            self.ownership_identity_epoch,
            self.ownership_clock_generation,
        )


class OperationRecord(OperationModel):
    schema_version: Literal[1] = 1
    admission: OperationAdmission
    summary: JobSummary
    lease: OperationLease | None
    fence: PositiveInt64
    dispatch_attempt_id: str | None
    event_count: EventNumber
    recovery_reason: OperationReason | None
    observed_identity_epoch: str
    observed_clock_generation: PositiveInt64

    @model_validator(mode="after")
    def consistent(self) -> OperationRecord:
        a, s = self.admission, self.summary
        if (a.operation_id, a.plan_id, a.plan_digest) != (s.operation_id, s.plan_id, s.plan_digest):
            raise ValueError("operation projection mismatch")
        local = (
            s.status
            if s.execution_status == "not_started" and s.status in ("failed", "cancelled")
            else None
        )
        if s.status != operation_status(
            s.execution_status,
            s.delivery_status,
            delivery_required=a.delivery_required,
            local_terminal=local,
        ):
            raise ValueError("operation reducer mismatch")
        if self.dispatch_attempt_id is None and s.status not in ("admitted", "failed", "cancelled"):
            raise ValueError("dispatch intent required")
        if self.dispatch_attempt_id is None and s.execution_status != "not_started":
            raise ValueError("unarmed execution cannot have started")
        if self.dispatch_attempt_id is not None and s.execution_status == "not_started":
            raise ValueError("dispatch cannot be unstarted")
        if self.lease is not None and (self.lease.fence != self.fence or s.status in TERMINAL):
            raise ValueError("lease projection mismatch")
        if self.recovery_reason is not None and s.status != "unknown":
            raise ValueError("recovery marker requires unknown")
        if self.event_count == MAX_EVENTS and s.status not in TERMINAL:
            raise ValueError("terminal slot reserved")
        if len(canonical(self.model_dump(mode="json"))) > MAX_OPERATION_BYTES:
            raise ValueError("bounded operation required")
        return self


class OperationEvent(OperationModel):
    sequence: EventNumber
    revision: PositiveInt64
    fence: PositiveInt64
    attempt_id: str
    observed_at: str
    identity_epoch: str
    clock_generation: PositiveInt64
    status: OperationStatus
    execution_status: ExecutionStatus
    delivery_status: DeliveryStatus
    reason_code: OperationReason | None


class JobsPage(OperationModel):
    schema_version: Literal[1] = 1
    jobs: Annotated[tuple[JobSummary, ...], Field(max_length=100)]
    next_cursor: Annotated[str, Field(max_length=1024)] | None


class JobView(OperationModel):
    schema_version: Literal[1] = 1
    operation: JobSummary
    plan: ExecutionPlan
    attempts: Annotated[tuple[AttemptView, ...], Field(min_length=1, max_length=MAX_ATTEMPTS)]
    outcome: OperationOutcome | None

    @model_validator(mode="after")
    def relationships(self) -> JobView:
        s, p = self.operation, self.plan
        if (s.plan_id, s.plan_digest, s.task, s.tool, s.execution) != (
            p.plan_id,
            p.digest,
            p.selection.task,
            p.selection.tool,
            p.selection.execution,
        ):
            raise ValueError("job plan mismatch")
        if len(self.attempts) != s.attempt_count or tuple(a.number for a in self.attempts) != tuple(
            range(1, len(self.attempts) + 1)
        ):
            raise ValueError("attempt sequence mismatch")
        if len({a.attempt_id for a in self.attempts}) != len(self.attempts) or any(
            a.status != "abandoned" for a in self.attempts[:-1]
        ):
            raise ValueError("historical attempts must be abandoned")
        current = self.attempts[-1]
        if current.status != ("claimed" if s.status == "admitted" else s.status):
            raise ValueError("current attempt mismatch")
        validate_progress_reason(
            s.status,
            current.reason_code,
            s.execution_status,
            s.delivery_status,
            dispatched=s.execution_status != "not_started",
        )
        if self.attempts[0].created_at != s.created_at or current.updated_at != s.updated_at:
            raise ValueError("attempt observation time mismatch")
        for old, new in zip(self.attempts[:-1], self.attempts[1:], strict=True):
            if old.updated_at != new.created_at:
                raise ValueError("abandonment must match the next attempt")
        if not s.clock_anomaly and any(
            not s.created_at <= a.created_at <= a.updated_at <= s.updated_at for a in self.attempts
        ):
            raise ValueError("attempt observation time outside operation")
        if (self.outcome is not None) != (s.status in TERMINAL):
            raise ValueError("terminal outcome required")
        if self.outcome is not None:
            o = self.outcome
            if o.recorded_at != s.updated_at:
                raise ValueError("terminal observation time mismatch")
            if (o.execution_status, o.delivery_status, o.provider_exit_code, o.reason_code) != (
                s.execution_status,
                s.delivery_status,
                current.provider_exit_code,
                current.reason_code,
            ):
                raise ValueError("outcome projection mismatch")
            if len(canonical(o.model_dump(mode="json"))) > MAX_OUTCOME_BYTES:
                raise ValueError("bounded outcome required")
        if len(canonical(self.model_dump(mode="json"))) > MAX_JOB_BYTES:
            raise ValueError("bounded job required")
        return self
