"""Closed upload plan identities and approvals; structure never grants remote authority."""

from __future__ import annotations

import hashlib
import uuid
from datetime import timedelta
from typing import Annotated, Any, ClassVar, Literal, Self

from pydantic import Field, ValidationInfo, field_validator, model_validator
from pydantic.config import ExtraValues

from yorunge.domain.capabilities import JsonWireModel, PositiveInt64, canonical, instant
from yorunge.domain.credentials import normalize_target
from yorunge.domain.dataset_manifest import (
    DatasetManifest,
    Sha256,
    decode_manifest_json,
    safe_text,
    validate_anchor,
)
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Identifier
from yorunge.domain.state import canonical_uuid

MAX_UPLOAD_FILES = 128
MAX_UPLOAD_FILE_BYTES = 500_000_000
MAX_UPLOAD_BYTES = 1024**3
MAX_UPLOAD_MANIFEST_BYTES = 256 * 1024
MAX_UPLOAD_PLAN_BYTES = 16 * 1024
UPLOAD_SECONDS = 900
TRANSFER_LEASE_SECONDS = 150
PUT_SECONDS = 120
COMMIT_MARGIN_SECONDS = 5
MAX_TRANSFER_PLANS = 128
MAX_TRANSFER_OPERATIONS = 128
MAX_TRANSFER_FILES = 4096
MAX_TRANSFER_PAYLOAD_BYTES = 16 * 1024**2
MAX_EFFECT_INTENTS = 386
RECOVERY_CONTROL_SLOTS = 2

NonnegativeInt64 = Annotated[int, Field(ge=0, le=2**63 - 1)]
UploadPermission = Literal[
    "create_private_dataset", "link_project", "read_created_dataset", "upload_created_dataset"
]
REQUIRED_PERMISSIONS: tuple[UploadPermission, ...] = (
    "create_private_dataset",
    "link_project",
    "read_created_dataset",
    "upload_created_dataset",
)
UploadBlocker = Literal[
    "authority_unverified", "cost_exceeds_budget", "cost_unverified", "inputs_unverified"
]


def provider_uuid(value: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except ValueError:
        raise ValueError("canonical provider UUID required") from None
    if str(parsed) != value:
        raise ValueError("canonical provider UUID required")
    return value


class UploadWire(JsonWireModel):
    max_wire_bytes: ClassVar[int] = MAX_UPLOAD_PLAN_BYTES

    @field_validator("policy_version", mode="before", check_fields=False)
    @classmethod
    def integer_policy(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("integer policy required")
        return value

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        if type(json_data) not in (str, bytes, bytearray) or len(json_data) > cls.max_wire_bytes:
            raise ValueError("bounded upload wire required")
        content = json_data.encode("utf-8") if isinstance(json_data, str) else bytes(json_data)
        if len(content) > cls.max_wire_bytes:
            raise ValueError("bounded upload wire required")
        decode_manifest_json(content)
        return super().model_validate_json(
            content,
            strict=True,
            extra="forbid",
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )

    def encoded(self) -> bytes:
        content = canonical(self.model_dump(mode="json"))
        if len(content) > self.max_wire_bytes:
            raise ValueError("upload wire byte limit exceeded")
        return content


class UploadOwner(UploadWire):
    kind: Literal["user", "organization"]
    id: str

    @field_validator("id")
    @classmethod
    def owner_id(cls, value: str) -> str:
        return provider_uuid(value)


class UploadScope(UploadWire):
    store_id: str
    identity_epoch: str
    clock_generation: PositiveInt64
    service_id: Literal["evren-platform"]
    service_origin: str
    api_base_path: str
    profile: Identifier
    owner: UploadOwner
    project_id: str
    credential_id: str
    credential_revision: PositiveInt64

    @field_validator("store_id", "identity_epoch", "credential_id")
    @classmethod
    def internal_id(cls, value: str) -> str:
        return canonical_uuid(value)

    @field_validator("project_id")
    @classmethod
    def project(cls, value: str) -> str:
        return provider_uuid(value)

    @model_validator(mode="after")
    def target(self) -> Self:
        try:
            target = normalize_target(self.service_origin + self.api_base_path)
        except YorungeError:
            raise ValueError("canonical service target required") from None
        if (target.service_origin, target.api_base_path) != (
            self.service_origin,
            self.api_base_path,
        ):
            raise ValueError("canonical service target required")
        return self


class UploadRoot(UploadWire):
    anchor: str
    device: NonnegativeInt64
    inode: PositiveInt64

    @field_validator("anchor")
    @classmethod
    def absolute(cls, value: str) -> str:
        return validate_anchor(value)


class UploadParameters(UploadWire):
    name: Annotated[str, Field(min_length=2, max_length=128)]
    modality: Literal["VISION", "AUDIO", "NLP", "MULTIMODAL", "MEDICAL"]
    visibility: Literal["private"]
    contributions_enabled: Literal[False]
    license: str | None
    tags: Annotated[tuple[Identifier, ...], Field(max_length=10)]

    @field_validator("name", "license")
    @classmethod
    def text(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is not None:
            maximum = 256 if info.field_name == "name" else 128
            if not value or value != value.strip() or len(safe_text(value)) > maximum:
                raise ValueError("bounded unmodified upload text required")
        return value

    @field_validator("contributions_enabled", mode="before")
    @classmethod
    def strict_false(cls, value: object) -> object:
        if type(value) is not bool:
            raise ValueError("boolean contribution policy required")
        return value

    @field_validator("tags")
    @classmethod
    def ordered(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))):
            raise ValueError("canonical tags required")
        return value


class UploadManifestRef(UploadWire):
    digest: Sha256
    content_sha256: Sha256
    file_count: Annotated[int, Field(ge=1, le=MAX_UPLOAD_FILES)]
    total_bytes: Annotated[int, Field(ge=0, le=MAX_UPLOAD_BYTES)]


def manifest_reference(manifest: DatasetManifest) -> UploadManifestRef:
    if type(manifest) is not DatasetManifest or not 1 <= len(manifest.files) <= MAX_UPLOAD_FILES:
        raise ValueError("bounded nonempty upload manifest required")
    if any(file.size > MAX_UPLOAD_FILE_BYTES for file in manifest.files):
        raise ValueError("upload file byte limit exceeded")
    content = manifest.encoded()
    if len(content) > MAX_UPLOAD_MANIFEST_BYTES:
        raise ValueError("upload manifest byte limit exceeded")
    checked = DatasetManifest.model_validate_json(content)
    return UploadManifestRef(
        digest=checked.digest,
        content_sha256=hashlib.sha256(content).hexdigest(),
        file_count=checked.file_count,
        total_bytes=checked.total_bytes,
    )


class UploadStoragePolicy(UploadWire):
    mode: Literal["proxy", "direct"]
    origin: str | None

    @model_validator(mode="after")
    def target(self) -> Self:
        if self.mode == "proxy":
            if self.origin is not None:
                raise ValueError("proxy policy has no storage origin")
            return self
        if self.origin is None:
            raise ValueError("explicit direct storage origin required")
        try:
            target = normalize_target(self.origin)
        except YorungeError:
            raise ValueError("canonical direct origin required") from None
        if target.service_origin != self.origin or target.api_base_path != "/":
            raise ValueError("canonical direct origin required")
        return self


class UploadGrant(UploadWire):
    schema_version: Literal[1]
    scope: UploadScope
    permissions: Annotated[tuple[UploadPermission, ...], Field(max_length=4)]
    producer_id: Identifier
    producer_version: Identifier
    checked_at: str
    expires_at: str

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.permissions != tuple(sorted(set(self.permissions))):
            raise ValueError("canonical upload grants required")
        if instant(self.checked_at) >= instant(self.expires_at):
            raise ValueError("positive upload grant lifetime required")
        return self


class UploadCostBound(UploadWire):
    schema_version: Literal[1]
    scope: UploadScope
    maximum_micros: NonnegativeInt64
    source_id: Identifier
    source_version: Identifier
    checked_at: str
    expires_at: str

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if instant(self.checked_at) >= instant(self.expires_at):
            raise ValueError("positive upload price lifetime required")
        return self


def upload_blockers(
    inputs_verified: bool,
    grant: UploadGrant | None,
    cost_bound: UploadCostBound | None,
    budget_micros: int,
) -> tuple[UploadBlocker, ...]:
    result: list[UploadBlocker] = []
    if grant is None or grant.permissions != REQUIRED_PERMISSIONS:
        result.append("authority_unverified")
    if cost_bound is None:
        result.append("cost_unverified")
    elif cost_bound.maximum_micros > budget_micros:
        result.append("cost_exceeds_budget")
    if not inputs_verified:
        result.append("inputs_unverified")
    return tuple(sorted(result))


class DatasetUploadPlan(UploadWire):
    schema_version: Literal[1]
    policy_version: Literal[1]
    kind: Literal["dataset_upload_plan"]
    plan_id: str
    scope: UploadScope
    root: UploadRoot
    manifest: UploadManifestRef
    parameters: UploadParameters
    storage: UploadStoragePolicy
    budget_micros: NonnegativeInt64
    inputs_verified: bool
    grant: UploadGrant | None
    cost_bound: UploadCostBound | None
    blockers: Annotated[tuple[UploadBlocker, ...], Field(max_length=4)]
    prepared_at: str
    expires_at: str
    status: Literal["draft", "prepared"]
    executable: Literal[False]
    digest: Sha256

    @field_validator("plan_id")
    @classmethod
    def internal_id(cls, value: str) -> str:
        return canonical_uuid(value)

    @model_validator(mode="after")
    def consistent(self) -> Self:
        start, end = instant(self.prepared_at), instant(self.expires_at)
        if not timedelta(0) < end - start <= timedelta(seconds=UPLOAD_SECONDS):
            raise ValueError("bounded upload plan lifetime required")
        for observation in (self.grant, self.cost_bound):
            if observation is not None and (
                observation.scope != self.scope
                or instant(observation.checked_at) > start
                or end > instant(observation.expires_at)
            ):
                raise ValueError("upload evidence scope or time mismatch")
        blockers = upload_blockers(
            self.inputs_verified, self.grant, self.cost_bound, self.budget_micros
        )
        if self.blockers != blockers or (self.status == "prepared") != (not blockers):
            raise ValueError("upload preparation mismatch")
        if self.digest != self.computed_digest():
            raise ValueError("upload plan digest mismatch")
        self.encoded()
        return self

    def computed_digest(self) -> str:
        return hashlib.sha256(
            canonical(self.model_dump(mode="json", exclude={"digest"}))
        ).hexdigest()

    def intent_digest(self) -> str:
        return hashlib.sha256(
            canonical(
                {
                    "service_origin": self.scope.service_origin,
                    "api_base_path": self.scope.api_base_path,
                    "owner": self.scope.owner.model_dump(mode="json"),
                    "project_id": self.scope.project_id,
                    "name": self.parameters.name,
                }
            )
        ).hexdigest()

    def binding_digest(self) -> str:
        value = self.model_dump(
            mode="json", exclude={"plan_id", "digest", "prepared_at", "expires_at"}
        )
        for field in ("grant", "cost_bound"):
            if value[field] is not None:
                del value[field]["checked_at"], value[field]["expires_at"]
        return hashlib.sha256(canonical(value)).hexdigest()


class DatasetUploadApproval(UploadWire):
    schema_version: Literal[1]
    approval_id: str
    plan_id: str
    plan_digest: Sha256
    binding_digest: Sha256
    store_id: str
    identity_epoch: str
    clock_generation: PositiveInt64
    approved_at: str
    expires_at: str
    status: Literal["approved", "revoked"]
    revoked_at: str | None

    @field_validator("approval_id", "plan_id", "store_id", "identity_epoch")
    @classmethod
    def internal_id(cls, value: str) -> str:
        return canonical_uuid(value)

    @model_validator(mode="after")
    def consistent(self) -> Self:
        start, end = instant(self.approved_at), instant(self.expires_at)
        if not timedelta(0) < end - start <= timedelta(seconds=UPLOAD_SECONDS):
            raise ValueError("bounded upload approval lifetime required")
        if (self.status == "revoked") != (self.revoked_at is not None):
            raise ValueError("upload revocation mismatch")
        if self.revoked_at is not None and instant(self.revoked_at) < start:
            raise ValueError("upload revocation precedes approval")
        self.encoded()
        return self


def validate_approval_binding(plan: DatasetUploadPlan, approval: DatasetUploadApproval) -> None:
    if (
        plan.status != "prepared"
        or (
            approval.plan_id,
            approval.plan_digest,
            approval.binding_digest,
            approval.store_id,
            approval.identity_epoch,
            approval.clock_generation,
        )
        != (
            plan.plan_id,
            plan.digest,
            plan.binding_digest(),
            plan.scope.store_id,
            plan.scope.identity_epoch,
            plan.scope.clock_generation,
        )
        or instant(approval.approved_at) < instant(plan.prepared_at)
        or instant(approval.expires_at) > instant(plan.expires_at)
    ):
        raise ValueError("upload approval plan binding mismatch")
