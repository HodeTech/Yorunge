"""Closed user projections; private create receipts and credential scopes stay private."""

from __future__ import annotations

from typing import Annotated, ClassVar, Literal, Self

from pydantic import Field, field_validator, model_validator

from yorunge.domain.capabilities import instant
from yorunge.domain.credentials import normalize_target
from yorunge.domain.dataset_manifest import Sha256, validate_anchor
from yorunge.domain.dataset_transfer import TransferStatus
from yorunge.domain.dataset_upload import (
    NonnegativeInt64,
    UploadBlocker,
    UploadManifestRef,
    UploadOwner,
    UploadParameters,
    UploadStoragePolicy,
    UploadWire,
    provider_uuid,
)
from yorunge.domain.dataset_upload_v2 import (
    AdmissionPolicy,
    CostPolicy,
    UploadPlanStatus,
    UploadRisk,
)
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Identifier
from yorunge.domain.state import canonical_uuid
from yorunge.domain.upload_costs import ChargeCategory, UploadRequestLimits
from yorunge.domain.upload_graph import CURRENT_PLAN_VERSION, StageGraphSpec


class UploadCostSummary(UploadWire):
    schema_version: Literal[1]
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
    def periods(self) -> Self:
        if self.charge_categories != tuple(sorted(set(self.charge_categories))):
            raise ValueError("canonical charge categories required")
        if instant(self.charge_period_start) >= instant(self.charge_period_end):
            raise ValueError("positive charge period required")
        if instant(self.checked_at) >= instant(self.expires_at):
            raise ValueError("positive cost evidence lifetime required")
        return self


class DatasetUploadSummary(UploadWire):
    schema_version: Literal[2]
    kind: Literal["dataset_upload_summary"]
    source_plan_schema: Literal[1, 2]
    legacy_history_only: bool
    plan_id: str
    plan_digest: Sha256
    plan_status: UploadPlanStatus
    admission_policy: AdmissionPolicy
    cost_policy: CostPolicy
    risks: tuple[UploadRisk, ...]
    blockers: tuple[UploadBlocker, ...]
    approval_status: Literal["approved", "revoked"] | None
    approval_expires_at: str | None
    operation_id: str | None
    operation_status: TransferStatus | None
    dataset_id: str | None
    verification_level: Literal["none", "metadata"]
    remote_bytes_verified: Literal[False]
    authority_verified: bool
    cost_bound: UploadCostSummary | None
    budget_micros: NonnegativeInt64 | None
    cost_scope: Literal["original_start_invocation", "legacy_unknown"]

    @field_validator("source_plan_schema", mode="before")
    @classmethod
    def source_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("integer source version required")
        return value

    @field_validator("remote_bytes_verified", mode="before")
    @classmethod
    def remote_flag(cls, value: object) -> object:
        if type(value) is not bool:
            raise ValueError("boolean verification flag required")
        return value

    @field_validator("plan_id", "operation_id")
    @classmethod
    def identifiers(cls, value: str | None) -> str | None:
        return canonical_uuid(value) if value is not None else None

    @field_validator("dataset_id")
    @classmethod
    def dataset(cls, value: str | None) -> str | None:
        return provider_uuid(value) if value is not None else None

    @model_validator(mode="after")
    def relationships(self) -> Self:
        self._source_binding()
        self._operation_binding()
        self._approval_binding()
        self._evidence_binding()
        self.encoded()
        return self

    def _source_binding(self) -> None:
        legacy = self.source_plan_schema == 1
        if self.legacy_history_only != legacy or self.cost_scope != (
            "legacy_unknown" if legacy else "original_start_invocation"
        ):
            raise ValueError("historical source family mismatch")
        if legacy and (self.cost_bound is not None or self.plan_status == "attempt_ready"):
            raise ValueError("legacy quote cannot become current pricing evidence")

    def _operation_binding(self) -> None:
        if (self.operation_id is None) != (self.operation_status is None):
            raise ValueError("operation identity and state must be paired")
        if self.operation_status == "succeeded" and self.dataset_id is None:
            raise ValueError("success requires a dataset identity")
        if self.operation_id is None and self.dataset_id is not None:
            raise ValueError("dataset identity requires an operation")

    def _approval_binding(self) -> None:
        if (self.approval_status is None) != (self.approval_expires_at is None):
            raise ValueError("approval state and expiry must be paired")
        if self.approval_expires_at is not None:
            instant(self.approval_expires_at)

    def _evidence_binding(self) -> None:
        succeeded = self.operation_status == "succeeded"
        if (self.verification_level == "metadata") != succeeded or (
            self.authority_verified and not succeeded
        ):
            raise ValueError("success evidence required")
        if self.risks != tuple(sorted(set(self.risks))) or self.blockers != tuple(
            sorted(set(self.blockers))
        ):
            raise ValueError("canonical risk and blocker sets required")
        if (self.cost_policy == "bounded_required") != (self.budget_micros is not None):
            raise ValueError("cost policy and budget mismatch")


class UploadReviewTarget(UploadWire):
    service_origin: str
    api_base_path: str
    profile: Identifier

    @model_validator(mode="after")
    def canonical_target(self) -> Self:
        try:
            target = normalize_target(self.service_origin + self.api_base_path)
        except YorungeError:
            raise ValueError("canonical target required") from None
        if (target.service_origin, target.api_base_path) != (
            self.service_origin,
            self.api_base_path,
        ):
            raise ValueError("canonical target required")
        return self


class UploadIntentReview(UploadWire):
    max_wire_bytes: ClassVar[int] = 32 * 1024
    schema_version: Literal[1]
    kind: Literal["dataset_upload_intent_review"]
    summary: DatasetUploadSummary
    target: UploadReviewTarget
    selected_owner: UploadOwner
    selected_project_id: str
    root: str
    manifest: UploadManifestRef
    parameters: UploadParameters
    storage: UploadStoragePolicy
    request_limits: UploadRequestLimits | None
    prepared_at: str
    expires_at: str

    @field_validator("selected_project_id")
    @classmethod
    def project(cls, value: str) -> str:
        return provider_uuid(value)

    @field_validator("root")
    @classmethod
    def anchor(cls, value: str) -> str:
        return validate_anchor(value)

    @model_validator(mode="after")
    def family(self) -> Self:
        if self.summary.legacy_history_only != (self.request_limits is None):
            raise ValueError("request limits must match source family")
        if instant(self.prepared_at) >= instant(self.expires_at):
            raise ValueError("positive plan interval required")
        limits = self.request_limits
        if limits is not None:
            counts = StageGraphSpec(CURRENT_PLAN_VERSION, self.manifest.file_count).request_counts()
            if (limits.max_presign, limits.max_put, limits.max_confirm) != (
                counts.presign,
                counts.put,
                counts.confirm,
            ) or limits.max_upload_bytes != self.manifest.total_bytes:
                raise ValueError("request quantities must match manifest")
        self.encoded()
        return self


class DatasetUploadsPage(UploadWire):
    max_wire_bytes: ClassVar[int] = 1024 * 1024
    schema_version: Literal[1]
    uploads: Annotated[tuple[DatasetUploadSummary, ...], Field(max_length=100)]
    next_cursor: Annotated[str, Field(max_length=256)] | None
