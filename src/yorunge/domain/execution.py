"""Immutable execution snapshots; structural integrity is not current authority."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from yorunge.domain.capabilities import (
    CapabilityRecord,
    Digest,
    PositiveInt64,
    WireModel,
    canonical,
    instant,
)
from yorunge.domain.credentials import normalize_target
from yorunge.domain.models import LLM_TASKS, Context, Identifier, Recipe, Selection, Task
from yorunge.domain.state import canonical_uuid

NonnegativeInt64 = Annotated[int, Field(ge=0, le=2**63 - 1)]


class InputRoot(WireModel):
    anchor: Annotated[str, Field(min_length=1, max_length=2048)]
    device: NonnegativeInt64
    inode: PositiveInt64

    @field_validator("anchor")
    @classmethod
    def absolute_anchor(cls, value: str) -> str:
        if not value.startswith("/") or (
            value != "/" and any(p in ("", ".", "..") for p in value[1:].split("/"))
        ):
            raise ValueError("absolute canonical anchor required")
        return value


class InputBinding(WireModel):
    role: Identifier
    path: Annotated[str, Field(min_length=1, max_length=1024)]
    size: NonnegativeInt64
    digest: Digest

    @field_validator("path")
    @classmethod
    def relative_file(cls, value: str) -> str:
        if any(p in ("", ".", "..") for p in value.split("/")) or "\\" in value or ":" in value:
            raise ValueError("relative canonical file required")
        return value


class Effect(WireModel):
    kind: Literal["local_read", "remote_write", "execution"]
    service_id: Literal["local", "evren-platform", "evren-llm"]
    description_code: Identifier


class ParameterMapping(WireModel):
    source: Identifier
    destination: Identifier


class CostEstimate(WireModel):
    units: NonnegativeInt64
    unit: Identifier
    source: Identifier
    checked_at: str
    expires_at: str

    @model_validator(mode="after")
    def valid_time(self) -> CostEstimate:
        if instant(self.expires_at) <= instant(self.checked_at):
            raise ValueError("positive estimate lifetime required")
        return self


class ExecutionAssessment(WireModel):
    capabilities: Annotated[tuple[CapabilityRecord, ...], Field(max_length=128)]
    inputs_verified: bool
    blockers: Annotated[tuple[Identifier, ...], Field(max_length=128)]
    effects: Annotated[tuple[Effect, ...], Field(max_length=128)]
    parameter_mapping: Annotated[tuple[ParameterMapping, ...], Field(max_length=128)]
    parameter_losses: Annotated[tuple[Identifier, ...], Field(max_length=128)]
    cost: CostEstimate | None

    def ready(self) -> bool:
        return (
            bool(self.capabilities)
            and self.inputs_verified
            and not (self.blockers or self.parameter_losses)
            and all(c.support == "supported" for c in self.capabilities)
        )

    def semantic(self) -> bytes:
        value = self.model_dump(mode="json")
        for record in value["capabilities"]:
            for field in ("checked_at", "expires_at"):
                del record[field]
            for proof in record["evidence"]:
                del proof["checked_at"], proof["expires_at"]
        if value["cost"] is not None:
            del value["cost"]["checked_at"], value["cost"]["expires_at"]
        return canonical(value)

    def expiry(self) -> datetime:
        dates = [instant(c.expires_at) for c in self.capabilities]
        if self.cost is not None:
            dates.append(instant(self.cost.expires_at))
        if not dates:
            raise ValueError("capability evidence required")
        return min(dates)


def execution_service(selection: Selection) -> Literal["local", "evren-llm", "evren-platform"]:
    if selection.task in LLM_TASKS and selection.execution == "local":
        return "local"
    if selection.task == "llm.chat":
        return "evren-llm"
    return "evren-platform"


def validate_assessment_scope(
    assessment: ExecutionAssessment,
    context: Context,
    selection: Selection,
    recipe: Recipe,
) -> None:
    required = execution_service(selection)
    if assessment.ready() and not any(
        c.key.capability_id != "planning.offline" and c.key.scope.service_id == required
        for c in assessment.capabilities
    ):
        raise ValueError("task execution authority required")
    for capability in assessment.capabilities:
        _validate_capability_scope(capability, context, selection, recipe, required)


def _validate_capability_scope(
    capability: CapabilityRecord,
    context: Context,
    selection: Selection,
    recipe: Recipe,
    required: str,
) -> None:
    scope = capability.key.scope
    if (scope.account_id, scope.project_id) != (context.account_id, context.project_id):
        raise ValueError("account/project scope mismatch")
    if scope.service_id not in ("local", required):
        raise ValueError("task service mismatch")
    if scope.service_id != "local":
        target = normalize_target(
            context.llm_url if required == "evren-llm" else context.platform_url
        )
        if (scope.service_origin, scope.api_base_path) != (
            target.service_origin,
            target.api_base_path,
        ):
            raise ValueError("service target mismatch")
    if (
        scope.execution.backend != selection.execution
        or (scope.tool.id if scope.tool else None) != selection.tool
    ):
        raise ValueError("selected tool/backend mismatch")
    expected_model = (
        (recipe.model.source, recipe.model.id, recipe.model.revision) if recipe.model else None
    )
    observed_model = (
        (scope.model.source, scope.model.id, scope.model.revision) if scope.model else None
    )
    if observed_model != expected_model:
        raise ValueError("selected model mismatch")


class ExecutionBody(WireModel):
    schema_version: Literal[2] = 2
    policy_version: Literal[1] = 1
    mode: Literal["execution"] = "execution"
    plan_id: str
    store_id: str
    identity_epoch: str
    clock_generation: PositiveInt64
    context: Context
    selection: Selection
    recipe: Recipe
    input_root: InputRoot | None
    inputs: Annotated[tuple[InputBinding, ...], Field(max_length=128)]
    assessment: ExecutionAssessment
    prepared_at: str
    expires_at: str
    status: Literal["draft", "prepared"]
    executable: Literal[False] = False

    @field_validator("plan_id", "store_id", "identity_epoch")
    @classmethod
    def uuid(cls, value: str) -> str:
        return canonical_uuid(value)

    @field_validator("policy_version", mode="before")
    @classmethod
    def strict_policy(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("integer policy version required")
        return value

    @model_validator(mode="after")
    def consistent(self) -> ExecutionBody:
        start, end = instant(self.prepared_at), instant(self.expires_at)
        if not timedelta(0) < end - start <= timedelta(seconds=300):
            raise ValueError("bounded plan lifetime required")
        validate_assessment_scope(self.assessment, self.context, self.selection, self.recipe)
        if self.selection.task != self.recipe.task:
            raise ValueError("saved task mismatch")
        if (self.status == "prepared") != self.assessment.ready():
            raise ValueError("preparation status mismatch")
        paths = tuple((i.role, i.path) for i in self.inputs)
        if tuple(sorted(set(paths))) != paths or (self.inputs and self.input_root is None):
            raise ValueError("canonical input bindings required")
        if self.recipe.data is not None and not any(
            i.role == "data.manifest" and i.path == self.recipe.data.manifest for i in self.inputs
        ):
            raise ValueError("manifest binding required")
        if not self.assessment.capabilities or end > self.assessment.expiry():
            raise ValueError("plan cannot outlive authority")
        self._validate_capabilities(start)
        return self

    def _validate_capabilities(self, start: datetime) -> None:
        for capability in self.assessment.capabilities:
            scope = capability.key.scope
            if self.status == "prepared" and capability.key.capability_id != "planning.offline":
                self._validate_prepared_capability(capability)
            if (
                scope.store_id,
                scope.identity_epoch,
                scope.clock_generation,
                capability.key.task,
            ) != (
                self.store_id,
                self.identity_epoch,
                self.clock_generation,
                self.selection.task,
            ) or instant(capability.checked_at) > start:
                raise ValueError("plan evidence binding mismatch")
        if self.assessment.cost and instant(self.assessment.cost.checked_at) > start:
            raise ValueError("future estimate")

    def _validate_prepared_capability(self, capability: CapabilityRecord) -> None:
        scope = capability.key.scope
        if (
            scope.execution.backend != self.selection.execution
            or scope.execution.environment_digest is None
        ):
            raise ValueError("verified execution environment required")
        if self.selection.tool is not None and (
            scope.tool is None
            or scope.tool.id != self.selection.tool
            or scope.tool.version is None
            or scope.tool.executable_digest is None
            or scope.tool.environment_digest is None
        ):
            raise ValueError("verified selected tool required")
        if self.recipe.model is not None and (
            scope.model is None
            or scope.model.source != self.recipe.model.source
            or scope.model.id != self.recipe.model.id
            or scope.model.revision != self.recipe.model.revision
            or scope.model.content_digest is None
        ):
            raise ValueError("verified selected model required")
        if self.selection.execution != "local" and (
            scope.execution.runtime_id is None or scope.execution.runtime_revision is None
        ):
            raise ValueError("verified runtime required")


_PLAN_DIGEST_FIELD = "digest"


class ExecutionPlan(ExecutionBody):
    digest: Digest

    def computed_digest(self) -> str:
        return hashlib.sha256(
            canonical(self.model_dump(mode="json", exclude={_PLAN_DIGEST_FIELD}))
        ).hexdigest()

    @model_validator(mode="after")
    def integrity(self) -> ExecutionPlan:
        body = canonical(self.model_dump(mode="json", exclude={_PLAN_DIGEST_FIELD}))
        # Merging two nonempty compact objects removes two braces and adds one comma.
        # Derive the actual digest field's size; do not reserialize the large body.
        size = len(body) + len(canonical({_PLAN_DIGEST_FIELD: self.digest})) - 1
        if self.digest != hashlib.sha256(body).hexdigest() or size > 65536:
            raise ValueError("plan digest or size invalid")
        return self


class ExecutionApproval(WireModel):
    schema_version: Literal[1] = 1
    approval_id: str
    plan_id: str
    plan_schema_version: Literal[2] = 2
    plan_digest: Digest
    binding_digest: Digest
    store_id: str
    identity_epoch: str
    clock_generation: PositiveInt64
    approved_at: str
    expires_at: str
    status: Literal["approved", "revoked"]
    revoked_at: str | None

    @field_validator("approval_id", "plan_id", "store_id", "identity_epoch")
    @classmethod
    def uuid(cls, value: str) -> str:
        return canonical_uuid(value)

    @field_validator("plan_schema_version", mode="before")
    @classmethod
    def strict_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("integer plan version required")
        return value

    @model_validator(mode="after")
    def consistent(self) -> ExecutionApproval:
        if (
            not timedelta(0)
            < instant(self.expires_at) - instant(self.approved_at)
            <= timedelta(seconds=300)
        ):
            raise ValueError("bounded approval lifetime required")
        if (self.status == "revoked") != (self.revoked_at is not None):
            raise ValueError("revocation status mismatch")
        if self.revoked_at is not None:
            instant(self.revoked_at)
        return self


class ExecutionApprovalState(WireModel):
    plan_id: str
    plan_digest: Digest
    record: ExecutionApproval | None
    effective: bool | None
    checked_at: str | None
    valid_until: str | None
    reasons: tuple[Identifier, ...]


class ForgottenExecutionPlan(WireModel):
    plan_id: str
    digest: Digest
    forgotten: Literal[True] = True
    local_only: Literal[True] = True
    approval_removed: bool


def binding_digest(plan: ExecutionPlan) -> str:
    return hashlib.sha256(
        canonical(
            {
                "context": plan.context.model_dump(mode="json"),
                "selection": plan.selection.model_dump(mode="json"),
                "recipe": plan.recipe.model_dump(mode="json"),
                "input_root": plan.input_root.model_dump(mode="json") if plan.input_root else None,
                "inputs": [i.model_dump(mode="json") for i in plan.inputs],
                "assessment": json.loads(plan.assessment.semantic()),
            }
        )
    ).hexdigest()


class ExecutionValidity(WireModel):
    plan_id: str
    digest: Digest
    valid: bool
    checked_at: str
    valid_until: str | None
    reasons: tuple[Identifier, ...]
    approval: ExecutionApprovalState | None = None


class ExecutionPlanView(WireModel):
    plan: ExecutionPlan
    validity: ExecutionValidity | None = None
    approval: ExecutionApprovalState | None = None


class ExecutionSummary(WireModel):
    approval_status: Literal["none", "approved", "revoked"] = "none"
    plan_id: str
    digest: Digest
    task: Task
    prepared_at: str
    expires_at: str
    status: Literal["draft", "prepared"]


class ExecutionPlans(WireModel):
    plans: tuple[ExecutionSummary, ...]
    next_cursor: str | None


@dataclass(frozen=True)
class ExecutionMoment:
    store_id: str
    identity_epoch: str
    generation: int
    now: datetime
    anomaly: bool
