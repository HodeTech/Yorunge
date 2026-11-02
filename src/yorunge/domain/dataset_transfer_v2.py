"""Version-two journal evidence; metadata success is separate from remote authority."""

from __future__ import annotations

from typing import Annotated, ClassVar, Literal, Self

from pydantic import Field, field_validator, model_validator

from yorunge.domain.capabilities import PositiveInt64, instant
from yorunge.domain.dataset_manifest import Sha256
from yorunge.domain.dataset_transfer import TERMINAL, TransferLease, VerifiedFile
from yorunge.domain.dataset_upload import UploadGrant, UploadScope, UploadWire, provider_uuid
from yorunge.domain.dataset_upload_v2 import DatasetUploadApprovalV2
from yorunge.domain.state import canonical_uuid

TransferReasonV2 = Literal[
    "identity_reset",
    "lease_expired",
    "clock_changed",
    "request_uncertain",
    "approval_revoked",
    "approval_expired",
    "provider_rejected",
    "local_cancelled",
    "metadata_verified",
    "read_unavailable",
]


class TransferRecordV2(UploadWire):
    schema_version: Literal[2]
    operation_id: str
    plan_id: str
    plan_digest: Sha256
    intent_digest: Sha256
    approval: DatasetUploadApprovalV2
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
    dataset_id: str | None
    reason: TransferReasonV2 | None

    @field_validator("operation_id", "plan_id", "observed_identity_epoch", "write_owner_id")
    @classmethod
    def identifier(cls, value: str) -> str:
        return canonical_uuid(value)

    @field_validator("dataset_id")
    @classmethod
    def dataset(cls, value: str | None) -> str | None:
        return None if value is None else provider_uuid(value)

    @model_validator(mode="after")
    def state(self) -> Self:
        if instant(self.updated_at) < instant(self.created_at) and not self.clock_anomaly:
            raise ValueError("backward business time requires clock marker")
        self._lease_binding()
        self._status_binding()
        self.encoded()
        return self

    def _lease_binding(self) -> None:
        lease = self.lease
        if lease is None:
            return
        if (
            self.status in TERMINAL
            or lease.fence != self.fence
            or lease.identity_epoch != self.observed_identity_epoch
            or lease.clock_generation != self.observed_clock_generation
        ):
            raise ValueError("lease ownership mismatch")
        if lease.mode == "write" and (lease.owner_id != self.write_owner_id or self.fence != 1):
            raise ValueError("write ownership cannot be reacquired")
        if lease.mode == "read" and self.status != "unknown":
            raise ValueError("read takeover cannot dispatch")

    def _status_binding(self) -> None:
        if self.status == "admitted" and (
            self.lease is None
            or self.lease.mode != "write"
            or self.workflow_latched
            or self.dataset_id is not None
            or self.reason is not None
        ):
            raise ValueError("admission cannot contain an effect")
        if (
            self.status in {"running", "unknown", "succeeded", "failed"}
            and not self.workflow_latched
        ):
            raise ValueError("effect state requires permanent workflow latch")
        if self.status == "cancelled" and self.workflow_latched:
            raise ValueError("local cancellation cannot undo an intent")
        self._outcome_binding()

    def _outcome_binding(self) -> None:
        if self.status in {"unknown", "failed", "cancelled", "succeeded"} and self.reason is None:
            raise ValueError("stopped state requires reason")
        if (self.status == "succeeded") != (self.reason == "metadata_verified") or (
            self.status == "succeeded" and self.dataset_id is None
        ):
            raise ValueError("success requires metadata verification")
        if self.status == "failed" and self.reason != "provider_rejected":
            raise ValueError("only definitive rejection is failure")
        if self.status == "running" and (self.lease is None or self.reason is not None):
            raise ValueError("running requires an owner")
        if self.reason == "read_unavailable" and self.status != "unknown":
            raise ValueError("read failure is not a terminal result")


class TransferControlV2(UploadWire):
    max_wire_bytes: ClassVar[int] = 2048
    schema_version: Literal[2]
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
        instant(self.observed_at)
        if (self.verification_digest is not None) != (self.reason == "metadata_verified"):
            raise ValueError("verification digest mismatch")
        if self.reason == "metadata_verified" and self.kind != "terminal":
            raise ValueError("metadata success is terminal")
        if self.reason == "read_unavailable" and self.kind != "recovery":
            raise ValueError("read failure is recovery")
        self.encoded()
        return self


class TransferVerificationV2(UploadWire):
    max_wire_bytes: ClassVar[int] = 128 * 1024
    schema_version: Literal[2]
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
        observed = instant(self.observed_at)
        if (
            tuple(f.file_index for f in self.files) != tuple(range(len(self.files)))
            or len({f.item_id for f in self.files}) != len(self.files)
            or self.project_id != self.scope.project_id
        ):
            raise ValueError("complete ordered read evidence required")
        if self.authorization_policy == "verified_read":
            if (
                self.grant is None
                or self.grant.scope != self.scope
                or "read_created_dataset" not in self.grant.permissions
                or not instant(self.grant.checked_at) <= observed < instant(self.grant.expires_at)
            ):
                raise ValueError("verified read requires actual current grant")
        elif self.grant is not None:
            raise ValueError("explicit read cannot manufacture a grant")
        self.encoded()
        return self
