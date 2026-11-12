"""V3 continuation journal evidence: the dataset is known from admission; check-only sends nothing.

A continuation operation is a separate record that points at the plan it was admitted from. Its
dataset comes from the plan (never from a create receipt), and a record with no file to send
(``verification_only``) never takes the send latch, never becomes uncertain and ends as a metadata
check. Everything here is a closed, strict value; it performs no I/O and never grants authority.
"""

from __future__ import annotations

from typing import Annotated, ClassVar, Literal, Self

from pydantic import Field, field_validator, model_validator

from yorunge.domain.capabilities import PositiveInt64, instant
from yorunge.domain.dataset_continuation import (
    DatasetContinuationPlanV3,
    DatasetUploadApprovalV3,
    validate_approval_binding_v3,
)
from yorunge.domain.dataset_manifest import Sha256
from yorunge.domain.dataset_transfer import TransferLease, VerifiedFile, scope_target
from yorunge.domain.dataset_transfer_v2 import (
    TransferReasonV2,
    validate_control_facts,
    validate_lease_binding,
    validate_verification_facts,
)
from yorunge.domain.dataset_upload import UploadGrant, UploadScope, UploadWire, provider_uuid
from yorunge.domain.state import canonical_uuid


class TransferRecordV3(UploadWire):
    schema_version: Literal[3]
    operation_id: str
    plan_id: str
    plan_digest: Sha256
    intent_digest: Sha256
    approval: DatasetUploadApprovalV3
    write_owner_id: str
    write_access_digest: Sha256
    created_at: str
    updated_at: str
    status: Literal["admitted", "running", "unknown", "succeeded", "failed", "cancelled"]
    revision: PositiveInt64
    fence: PositiveInt64
    observed_identity_epoch: str
    observed_clock_generation: PositiveInt64
    clock_anomaly: bool
    lease: TransferLease | None
    workflow_latched: bool
    verification_only: bool
    dataset_id: str
    reason: TransferReasonV2 | None

    @field_validator("operation_id", "plan_id", "observed_identity_epoch", "write_owner_id")
    @classmethod
    def identifier(cls, value: str) -> str:
        return canonical_uuid(value)

    @field_validator("dataset_id")
    @classmethod
    def dataset(cls, value: str) -> str:
        return provider_uuid(value)

    @model_validator(mode="after")
    def state(self) -> Self:
        if instant(self.updated_at) < instant(self.created_at) and not self.clock_anomaly:
            raise ValueError("backward business time requires clock marker")
        validate_lease_binding(self)
        self._status_binding()
        self._outcome_binding()
        self.encoded()
        return self

    def _status_binding(self) -> None:
        if self.verification_only and (
            self.workflow_latched or self.status in {"running", "unknown", "failed"}
        ):
            raise ValueError("a check-only continuation never sends and never becomes uncertain")
        if self.status == "admitted" and (
            self.lease is None
            or self.lease.mode != "write"
            or self.workflow_latched
            or self.reason is not None
        ):
            raise ValueError("admission cannot contain an effect")
        if self.status in {"running", "unknown", "failed"} and not self.workflow_latched:
            raise ValueError("effect state requires permanent workflow latch")
        if self.status == "succeeded" and not self.workflow_latched and not self.verification_only:
            raise ValueError("success after sending requires the workflow latch")
        if self.status == "cancelled" and self.workflow_latched:
            raise ValueError("local cancellation cannot undo an intent")

    def _outcome_binding(self) -> None:
        if self.status in {"unknown", "failed", "cancelled", "succeeded"} and self.reason is None:
            raise ValueError("stopped state requires reason")
        if (self.status == "succeeded") != (self.reason == "metadata_verified"):
            raise ValueError("success requires metadata verification")
        if self.status == "cancelled" and self.reason in {"request_uncertain", "provider_rejected"}:
            # Nothing was sent, so there is nothing to be uncertain about or to have been refused.
            raise ValueError("an effect-free cancellation cannot be uncertain or rejected")
        if self.status == "failed" and self.reason != "provider_rejected":
            raise ValueError("only definitive rejection is failure")
        if self.status == "running" and (self.lease is None or self.reason is not None):
            raise ValueError("running requires an owner")
        if self.reason == "read_unavailable" and self.status != "unknown":
            raise ValueError("read failure is not a terminal result")


class TransferControlV3(UploadWire):
    max_wire_bytes: ClassVar[int] = 2048
    schema_version: Literal[3]
    kind: Literal["recovery", "terminal"]
    operation_id: str
    revision: PositiveInt64
    observed_at: str
    identity_epoch: str
    clock_generation: PositiveInt64
    reason: TransferReasonV2
    verification_digest: Sha256 | None

    @field_validator("operation_id", "identity_epoch")
    @classmethod
    def identifier(cls, value: str) -> str:
        return canonical_uuid(value)

    @model_validator(mode="after")
    def outcome(self) -> Self:
        validate_control_facts(self)
        return self


class TransferVerificationV3(UploadWire):
    max_wire_bytes: ClassVar[int] = 128 * 1024
    schema_version: Literal[3]
    dataset_id: str
    project_id: str
    scope: UploadScope
    authorization_policy: Literal["verified_read", "explicit_read_attempt"]
    grant: UploadGrant | None
    observed_at: str
    files: Annotated[tuple[VerifiedFile, ...], Field(min_length=1, max_length=128)]

    @field_validator("dataset_id", "project_id")
    @classmethod
    def identifier(cls, value: str) -> str:
        return provider_uuid(value)

    @model_validator(mode="after")
    def observation(self) -> Self:
        validate_verification_facts(self)
        return self


def validate_record_binding_v3(plan: DatasetContinuationPlanV3, record: TransferRecordV3) -> None:
    """The record is this plan's admission: same identity, digests, dataset, mode and approval.

    Both arguments must be genuine, already validated values (this does not re-validate them), and
    the continuation is its own operation: it is neither the source nor the baseline root.
    """
    if type(plan) is not DatasetContinuationPlanV3 or type(record) is not TransferRecordV3:
        raise ValueError("mixed continuation plan/record versions")
    if record.operation_id in {
        plan.continuation.source_operation_id,
        plan.continuation.baseline_operation_id,
    }:
        raise ValueError("a continuation cannot be its own source")
    if (
        record.plan_id,
        record.plan_digest,
        record.intent_digest,
        record.dataset_id,
        record.verification_only,
    ) != (
        plan.plan_id,
        plan.digest,
        plan.intent_digest(),
        plan.continuation.dataset_id,
        not plan.continuation.file_indices,
    ):
        raise ValueError("continuation record does not belong to its plan")
    validate_approval_binding_v3(plan, record.approval)


def validate_verification_binding_v3(
    plan: DatasetContinuationPlanV3, proof: TransferVerificationV3
) -> None:
    """The proof is of this plan's dataset, target and file count, read under a policy it allows.

    The proof covers all N manifest files, not only the sent ones, so the count must be N. Whether
    each entry equals the manifest's is a read-time check (it needs the stored manifest), as is the
    pairing with the record's clock and version. Both arguments must be genuine, validated values.
    """
    if type(plan) is not DatasetContinuationPlanV3 or type(proof) is not TransferVerificationV3:
        raise ValueError("mixed continuation plan/proof versions")
    if (
        proof.dataset_id != plan.continuation.dataset_id
        or proof.project_id != plan.scope.project_id
        or scope_target(proof.scope) != scope_target(plan.scope)
        or len(proof.files) != plan.manifest.file_count
        or (
            proof.authorization_policy == "explicit_read_attempt"
            and plan.admission_policy != "explicit_attempt"
        )
    ):
        raise ValueError("continuation proof does not belong to its plan")
