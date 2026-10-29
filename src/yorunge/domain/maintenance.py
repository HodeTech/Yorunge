"""Versioned maintenance consent; secrets and private comparison tags stay excluded."""

import hashlib
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from yorunge.domain.capabilities import Digest, WireModel, canonical
from yorunge.domain.models import Model
from yorunge.domain.state import canonical_uuid

Count = Annotated[int, Field(ge=0, le=2**63 - 1)]
Version = Annotated[int, Field(ge=1, le=2**63 - 1)]


class LegacyIdentitySnapshot(Model):
    store_id: str
    identity_epoch: str
    store_schema_version: int
    binding_count: int
    approval_count: int = 0
    approval_fingerprint: str = ""
    plan_count: int = 0
    plan_fingerprint: str = ""
    binding_fingerprint: str


class LegacyMaintenancePreview(Model):
    schema_version: Literal[2] = 2
    cache_invalidated: Literal[True] = True
    action: Literal["reset", "restore", "recover"]
    current: LegacyIdentitySnapshot | None
    source: LegacyIdentitySnapshot | None
    history_may_be_lost: bool
    announced_epoch: str | None = None
    digest: str


class IdentitySnapshot(WireModel):
    store_id: str
    identity_epoch: str
    store_schema_version: Version
    binding_count: Count
    binding_fingerprint: Digest
    plan_count: Count
    plan_fingerprint: Digest
    approval_count: Count
    approval_fingerprint: Digest
    operation_count: Count
    attempt_count: Count
    nonterminal_operation_count: Count
    unknown_operation_count: Count
    operation_fingerprint: Digest

    @field_validator("store_id", "identity_epoch")
    @classmethod
    def identifier(cls, value: str) -> str:
        return canonical_uuid(value)

    @model_validator(mode="after")
    def counts(self) -> "IdentitySnapshot":
        if (
            not self.unknown_operation_count
            <= self.nonterminal_operation_count
            <= self.operation_count
        ):
            raise ValueError("inconsistent operation counts")
        if not self.operation_count <= self.attempt_count <= 16 * self.operation_count:
            raise ValueError("inconsistent attempt count")
        return self


class MaintenancePreview(WireModel):
    schema_version: Literal[3] = 3
    cache_invalidated: Literal[True] = True
    action: Literal["reset", "restore", "recover"]
    current: IdentitySnapshot | None
    source: IdentitySnapshot | None
    history_may_be_lost: bool
    announced_epoch: str | None = None
    digest: Digest

    @field_validator("cache_invalidated", mode="before")
    @classmethod
    def invalidated(cls, value: object) -> object:
        if value is not True:
            raise ValueError("cache invalidation is an explicit boolean")
        return value

    @field_validator("announced_epoch")
    @classmethod
    def announced(cls, value: str | None) -> str | None:
        return canonical_uuid(value) if value is not None else None

    @model_validator(mode="after")
    def reset_effect(self) -> "MaintenancePreview":
        if self.action == "reset" and (
            self.current is None
            or self.source is not None
            or self.announced_epoch is not None
            or self.history_may_be_lost
        ):
            raise ValueError("reset preserves local history")
        if (
            self.digest
            != hashlib.sha256(
                canonical(self.model_dump(mode="json", exclude={"digest"}))
            ).hexdigest()
        ):
            raise ValueError("maintenance consent digest mismatch")
        return self


Snapshot = IdentitySnapshot | LegacyIdentitySnapshot
Preview = MaintenancePreview | LegacyMaintenancePreview
