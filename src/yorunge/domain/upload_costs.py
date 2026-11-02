"""Exact-work pricing evidence; a valid shape alone never proves provider pricing."""

from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from yorunge.domain.capabilities import canonical, instant
from yorunge.domain.dataset_manifest import Sha256
from yorunge.domain.dataset_upload import (
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_FILES,
    UPLOAD_SECONDS,
    NonnegativeInt64,
    UploadManifestRef,
    UploadParameters,
    UploadRoot,
    UploadScope,
    UploadStoragePolicy,
    UploadWire,
)
from yorunge.domain.models import Identifier

ChargeCategory = Literal["create", "project_link", "control", "transfer", "confirm", "storage"]
ALL_CHARGE_CATEGORIES: tuple[ChargeCategory, ...] = (
    "confirm",
    "control",
    "create",
    "project_link",
    "storage",
    "transfer",
)
WORK_DOMAIN = b"yorunge-upload-cost-work-v2\0"


class UploadRequestLimits(UploadWire):
    max_create: Literal[1]
    max_project_link: Literal[1]
    max_presign: Annotated[int, Field(ge=1, le=MAX_UPLOAD_FILES)]
    max_put: Annotated[int, Field(ge=1, le=MAX_UPLOAD_FILES)]
    max_confirm: Annotated[int, Field(ge=1, le=MAX_UPLOAD_FILES)]
    max_read_requests: Literal[512]
    max_read_attempts: Literal[1024]
    max_control_request_bytes: Literal[4194304]
    max_control_response_bytes: Literal[16777216]
    max_upload_bytes: Annotated[int, Field(ge=0, le=MAX_UPLOAD_BYTES)]

    @field_validator("*", mode="before")
    @classmethod
    def integer_limit(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("integer request limit required")
        return value


class UploadExecutionWindow(UploadWire):
    not_before: str
    not_after: str

    @model_validator(mode="after")
    def interval(self) -> Self:
        if (
            not timedelta(0)
            < instant(self.not_after) - instant(self.not_before)
            <= timedelta(seconds=UPLOAD_SECONDS)
        ):
            raise ValueError("bounded upload execution window required")
        return self


class UploadCostWork(UploadWire):
    scope: UploadScope
    root: UploadRoot
    manifest: UploadManifestRef
    parameters: UploadParameters
    storage: UploadStoragePolicy
    request_limits: UploadRequestLimits
    execution_window: UploadExecutionWindow

    @model_validator(mode="after")
    def quantities(self) -> Self:
        limits = self.request_limits
        if (limits.max_presign, limits.max_put, limits.max_confirm) != (
            self.manifest.file_count,
        ) * 3 or limits.max_upload_bytes != self.manifest.total_bytes:
            raise ValueError("request limits must match exact upload manifest")
        self.encoded()
        return self

    def digest(self) -> str:
        return hashlib.sha256(WORK_DOMAIN + self.encoded()).hexdigest()


class UploadCostBoundV2(UploadWire):
    schema_version: Literal[2]
    scope: UploadScope
    work_digest: Sha256
    maximum_micros: NonnegativeInt64
    charge_categories: Annotated[tuple[ChargeCategory, ...], Field(min_length=1, max_length=6)]
    charge_period_start: str
    charge_period_end: str
    post_period_storage: Literal["no_further_charge", "unknown"]
    source_id: Identifier
    source_version: Identifier
    checked_at: str
    expires_at: str

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.charge_categories != tuple(sorted(set(self.charge_categories))):
            raise ValueError("canonical charge categories required")
        if instant(self.charge_period_start) >= instant(self.charge_period_end):
            raise ValueError("positive charge period required")
        if instant(self.checked_at) >= instant(self.expires_at):
            raise ValueError("positive price evidence lifetime required")
        self.encoded()
        return self

    def semantic_key(self) -> bytes:
        """Only observation timestamps may refresh without changing approved cost scope."""
        return canonical(self.model_dump(mode="json", exclude={"checked_at", "expires_at"}))


def validate_cost_binding(work: UploadCostWork, cost: UploadCostBoundV2) -> None:
    if cost.scope != work.scope or cost.work_digest != work.digest():
        raise ValueError("upload price evidence scope or work mismatch")


def complete_cost(work: UploadCostWork, cost: UploadCostBoundV2 | None) -> bool:
    """Coverage predicate, independent of quote freshness and the user's CR ceiling."""
    if cost is None:
        return False
    validate_cost_binding(work, cost)
    window = work.execution_window
    return (
        cost.charge_categories == ALL_CHARGE_CATEGORIES
        and instant(cost.charge_period_start) <= instant(window.not_before)
        and instant(cost.charge_period_end) >= instant(window.not_after)
        and cost.post_period_storage == "no_further_charge"
    )
