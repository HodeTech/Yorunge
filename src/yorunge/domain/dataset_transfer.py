"""Closed durable transfer journal; typed evidence never substitutes for a provider port."""

from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Annotated, ClassVar, Literal, Self

from pydantic import Field, field_validator, model_validator

from yorunge.domain.capabilities import PositiveInt64, canonical, instant
from yorunge.domain.dataset_manifest import Sha256
from yorunge.domain.dataset_upload import (
    TRANSFER_LEASE_SECONDS,
    DatasetUploadApproval,
    UploadGrant,
    UploadScope,
    UploadWire,
    provider_uuid,
)
from yorunge.domain.state import canonical_uuid
from yorunge.domain.upload_graph import ORIGINAL_PLAN_VERSION, StageGraphSpec, file_index_matches
from yorunge.domain.upload_graph import StageKind as StageKind

TransferStatus = Literal["admitted", "running", "unknown", "succeeded", "failed", "cancelled"]
TransferReason = Literal[
    "identity_reset",
    "lease_expired",
    "clock_changed",
    "request_uncertain",
    "approval_revoked",
    "approval_expired",
    "provider_rejected",
    "local_cancelled",
    "verified",
]
TERMINAL = frozenset({"succeeded", "failed", "cancelled"})
FileIndex = Annotated[int, Field(ge=0, le=127)]


class TransferLease(UploadWire):
    owner_id: str
    fence: PositiveInt64
    identity_epoch: str
    clock_generation: PositiveInt64
    mode: Literal["write", "read"]
    renewed_at: str
    expires_at: str

    @field_validator("owner_id", "identity_epoch")
    @classmethod
    def identifier(cls, value: str) -> str:
        return canonical_uuid(value)

    @model_validator(mode="after")
    def interval(self) -> Self:
        length = instant(self.expires_at) - instant(self.renewed_at)
        if not timedelta(0) < length <= timedelta(seconds=TRANSFER_LEASE_SECONDS):
            raise ValueError("bounded transfer lease required")
        return self


class TransferRecord(UploadWire):
    schema_version: Literal[1]
    operation_id: str
    plan_id: str
    plan_digest: Sha256
    intent_digest: Sha256
    approval: DatasetUploadApproval
    write_owner_id: str
    write_access_digest: Sha256
    created_at: str
    updated_at: str
    status: TransferStatus
    revision: PositiveInt64
    fence: PositiveInt64
    observed_identity_epoch: str
    observed_clock_generation: PositiveInt64
    clock_anomaly: bool
    lease: TransferLease | None
    workflow_latched: bool
    dataset_id: str | None
    reason: TransferReason | None

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
        created, updated = instant(self.created_at), instant(self.updated_at)
        if updated < created and not self.clock_anomaly:
            raise ValueError("backward business time requires clock marker")
        self._lease_identity()
        self._effect_state()
        self._outcome_state()
        self._dispatch_ownership()
        return self

    def _lease_identity(self) -> None:
        if self.lease is not None and (
            self.status in TERMINAL
            or self.lease.fence != self.fence
            or self.lease.identity_epoch != self.observed_identity_epoch
            or self.lease.clock_generation != self.observed_clock_generation
        ):
            raise ValueError("lease ownership mismatch")

    def _effect_state(self) -> None:
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

    def _outcome_state(self) -> None:
        if self.status in {"unknown", "failed", "cancelled", "succeeded"} and self.reason is None:
            raise ValueError("stopped state requires reason")
        if self.status == "succeeded" and (self.dataset_id is None or self.reason != "verified"):
            raise ValueError("success requires verification")
        if self.status == "failed" and self.reason != "provider_rejected":
            raise ValueError("only definitive rejection is failure")
        if self.status == "running" and (self.lease is None or self.reason is not None):
            raise ValueError("running requires an owner")

    def _dispatch_ownership(self) -> None:
        if (
            self.lease is not None
            and self.lease.mode == "write"
            and (self.lease.owner_id != self.write_owner_id or self.fence != 1)
        ):
            raise ValueError("write ownership cannot be reacquired")
        if self.lease is not None and self.lease.mode == "read" and self.status != "unknown":
            raise ValueError("read takeover cannot dispatch")


class StageIntent(UploadWire):
    max_wire_bytes: ClassVar[int] = 2048
    schema_version: Literal[1]
    intent_id: str
    operation_id: str
    sequence: Annotated[int, Field(ge=1, le=386)]
    kind: StageKind
    file_index: FileIndex | None
    request_digest: Sha256
    owner: TransferLease
    intended_at: str
    expires_at: str

    @field_validator("intent_id", "operation_id")
    @classmethod
    def identifier(cls, value: str) -> str:
        return canonical_uuid(value)

    @model_validator(mode="after")
    def binding(self) -> Self:
        if not file_index_matches(self.kind, self.file_index):
            raise ValueError("stage file index mismatch")
        if self.owner.mode != "write" or not (
            instant(self.owner.renewed_at)
            <= instant(self.intended_at)
            < instant(self.expires_at)
            <= instant(self.owner.expires_at)
        ):
            raise ValueError("stage authority interval mismatch")
        return self


class StageReceipt(UploadWire):
    max_wire_bytes: ClassVar[int] = 2048
    schema_version: Literal[1]
    intent_id: str
    recorded_at: str
    result: Literal["accepted", "rejected"]
    dataset_id: str | None
    object_key: str | None
    sent_bytes: Annotated[int, Field(ge=0, le=500_000_000)] | None
    sent_sha256: Sha256 | None

    @field_validator("intent_id")
    @classmethod
    def identifier(cls, value: str) -> str:
        return canonical_uuid(value)

    @field_validator("dataset_id")
    @classmethod
    def dataset(cls, value: str | None) -> str | None:
        return None if value is None else provider_uuid(value)

    @field_validator("object_key")
    @classmethod
    def key(cls, value: str | None) -> str | None:
        # Structural policy only: persisted provider handles require separate
        # non-authorizing evidence. The observed-v2 producer instead uses an
        # independent local file binding here; raw provider keys/URLs stay private.
        if value is not None and (
            not 1 <= len(value) <= 512
            or any(
                c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/_.-"
                for c in value
            )
            or any(p in {"", ".", ".."} for p in value.split("/"))
        ):
            raise ValueError("opaque non-authorizing object key required")
        return value

    @model_validator(mode="after")
    def content(self) -> Self:
        instant(self.recorded_at)
        if (self.sent_bytes is None) != (self.sent_sha256 is None):
            raise ValueError("sent counters require a digest")
        if self.result == "accepted" and self.dataset_id is None:
            raise ValueError("accepted stage requires dataset identity")
        if self.result == "rejected" and any(
            v is not None for v in (self.dataset_id, self.object_key, self.sent_bytes)
        ):
            raise ValueError("rejection contains no guessed receipt")
        return self


class VerifiedFile(UploadWire):
    file_index: FileIndex
    item_id: str
    path_digest: Sha256
    size_bytes: Annotated[int, Field(ge=0, le=500_000_000)]
    sha256: Sha256

    @field_validator("item_id")
    @classmethod
    def identifier(cls, value: str) -> str:
        return provider_uuid(value)


class TransferVerification(UploadWire):
    max_wire_bytes: ClassVar[int] = 128 * 1024
    schema_version: Literal[1]
    dataset_id: str
    project_id: str
    grant: UploadGrant
    observed_at: str
    files: Annotated[tuple[VerifiedFile, ...], Field(min_length=1, max_length=128)]

    @field_validator("dataset_id", "project_id")
    @classmethod
    def identifier(cls, value: str) -> str:
        return provider_uuid(value)

    @model_validator(mode="after")
    def observation(self) -> Self:
        if (
            tuple(f.file_index for f in self.files) != tuple(range(len(self.files)))
            or len({f.item_id for f in self.files}) != len(self.files)
            or "read_created_dataset" not in self.grant.permissions
            or not instant(self.grant.checked_at)
            <= instant(self.observed_at)
            < instant(self.grant.expires_at)
        ):
            raise ValueError("complete ordered read evidence required")
        return self


class TransferControl(UploadWire):
    max_wire_bytes: ClassVar[int] = 2048
    schema_version: Literal[1]
    kind: Literal["recovery", "terminal"]
    operation_id: str
    revision: PositiveInt64
    observed_at: str
    identity_epoch: str
    clock_generation: PositiveInt64
    reason: TransferReason
    verification_digest: Sha256 | None

    @field_validator("operation_id", "identity_epoch")
    @classmethod
    def identifier(cls, value: str) -> str:
        return canonical_uuid(value)

    @model_validator(mode="after")
    def outcome(self) -> Self:
        instant(self.observed_at)
        if (self.verification_digest is not None) != (self.reason == "verified"):
            raise ValueError("verification digest mismatch")
        if self.kind == "recovery" and self.reason == "verified":
            raise ValueError("recovery is not a result")
        return self


def scope_target(scope: UploadScope) -> bytes:
    """Stable target/owner/project; current read credentials may rotate after reset."""
    return canonical(
        {
            k: v
            for k, v in scope.model_dump(mode="json").items()
            if k
            in {
                "store_id",
                "service_id",
                "service_origin",
                "api_base_path",
                "owner",
                "project_id",
            }
        }
    )


def verification_digest(value: TransferVerification) -> str:
    return hashlib.sha256(value.encoded()).hexdigest()


def operation_reservation(file_count: int) -> int:
    """Reserve the worst future journal before admitting any remote intent.

    The v1/v2 graphs share one reservation; the stage graph specification owns the arithmetic.
    """
    return StageGraphSpec(ORIGINAL_PLAN_VERSION, file_count).operation_reservation()
