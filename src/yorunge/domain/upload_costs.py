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
from yorunge.domain.upload_graph import ORIGINAL_PLAN_VERSION, StageGraphSpec

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
CONTINUATION_WORK_DOMAIN = b"yorunge-upload-cost-work-v3\0"


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


class ContinuationRequestLimits(UploadWire):
    """Request ceilings of a continuation: no create or link, one selection of files."""

    max_create: Literal[0]
    max_project_link: Literal[0]
    max_presign: Annotated[int, Field(ge=0, le=MAX_UPLOAD_FILES)]
    max_put: Annotated[int, Field(ge=0, le=MAX_UPLOAD_FILES)]
    max_confirm: Annotated[int, Field(ge=0, le=MAX_UPLOAD_FILES)]
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

    @model_validator(mode="after")
    def one_selection(self) -> Self:
        if not self.max_presign == self.max_put == self.max_confirm:
            raise ValueError("one file selection required")
        if self.max_presign == 0 and self.max_upload_bytes != 0:
            raise ValueError("verification-only continuation sends no bytes")
        return self

    @property
    def files(self) -> int:
        """Number of selected files (M)."""
        return self.max_presign


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
        counts = StageGraphSpec(ORIGINAL_PLAN_VERSION, self.manifest.file_count).request_counts()
        if (limits.max_presign, limits.max_put, limits.max_confirm) != (
            counts.presign,
            counts.put,
            counts.confirm,
        ) or limits.max_upload_bytes != self.manifest.total_bytes:
            raise ValueError("request limits must match exact upload manifest")
        self.encoded()
        return self

    def digest(self) -> str:
        return hashlib.sha256(WORK_DOMAIN + self.encoded()).hexdigest()


class ContinuationCostWork(UploadWire):
    """Exact work of a continuation: the upload fields with the continuation request ceilings."""

    scope: UploadScope
    root: UploadRoot
    manifest: UploadManifestRef
    parameters: UploadParameters
    storage: UploadStoragePolicy
    request_limits: ContinuationRequestLimits
    execution_window: UploadExecutionWindow

    @model_validator(mode="after")
    def quantities(self) -> Self:
        limits, manifest = self.request_limits, self.manifest
        sends_everything = limits.files == manifest.file_count
        if (
            limits.files > manifest.file_count
            or limits.max_upload_bytes > manifest.total_bytes
            or (sends_everything and limits.max_upload_bytes != manifest.total_bytes)
        ):
            raise ValueError("continuation limits must fit the upload manifest")
        self.encoded()
        return self

    def digest(self) -> str:
        return hashlib.sha256(CONTINUATION_WORK_DOMAIN + self.encoded()).hexdigest()


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


def validate_cost_binding(
    work: UploadCostWork | ContinuationCostWork, cost: UploadCostBoundV2
) -> None:
    if cost.scope != work.scope or cost.work_digest != work.digest():
        raise ValueError("upload price evidence scope or work mismatch")


def complete_cost(
    work: UploadCostWork | ContinuationCostWork, cost: UploadCostBoundV2 | None
) -> bool:
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
