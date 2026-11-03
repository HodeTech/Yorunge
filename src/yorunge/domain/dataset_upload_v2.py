"""V2 upload policy, immutable plans and explicit risk acknowledgements."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from yorunge.domain.capabilities import PositiveInt64, canonical, instant
from yorunge.domain.dataset_manifest import Sha256
from yorunge.domain.dataset_upload import (
    REQUIRED_PERMISSIONS,
    UPLOAD_SECONDS,
    NonnegativeInt64,
    UploadBlocker,
    UploadGrant,
    UploadManifestRef,
    UploadParameters,
    UploadRoot,
    UploadScope,
    UploadStoragePolicy,
    UploadWire,
    upload_namespace,
)
from yorunge.domain.errors import YorungeError
from yorunge.domain.state import canonical_uuid
from yorunge.domain.upload_costs import (
    UploadCostBoundV2,
    UploadCostWork,
    UploadExecutionWindow,
    UploadRequestLimits,
    complete_cost,
)

AdmissionPolicy = Literal["verified_only", "explicit_attempt"]
CostPolicy = Literal["bounded_required", "unpriced_accepted"]
UploadRisk = Literal["authority_unverified", "cost_unverified"]
UploadPlanStatus = Literal["draft", "prepared", "attempt_ready"]


@dataclass(frozen=True)
class UploadPolicyState:
    risks: tuple[UploadRisk, ...]
    blockers: tuple[UploadBlocker, ...]
    status: UploadPlanStatus


def validate_policy_choice(
    admission_policy: AdmissionPolicy, cost_policy: CostPolicy, budget_micros: int | None
) -> None:
    if (
        admission_policy not in ("verified_only", "explicit_attempt")
        or cost_policy not in ("bounded_required", "unpriced_accepted")
        or (cost_policy == "unpriced_accepted" and admission_policy != "explicit_attempt")
        or (cost_policy == "bounded_required") != (budget_micros is not None)
        or (
            budget_micros is not None
            and (type(budget_micros) is not int or not 0 <= budget_micros < 2**63)
        )
    ):
        raise YorungeError("invalid_request")


def _policy_status(
    cost_policy: CostPolicy, risks: list[UploadRisk], blockers: list[UploadBlocker]
) -> UploadPlanStatus:
    if blockers:
        return "draft"
    if cost_policy == "bounded_required" and not risks:
        return "prepared"
    return "attempt_ready"


def reduce_upload_policy(
    work: UploadCostWork,
    *,
    admission_policy: AdmissionPolicy,
    cost_policy: CostPolicy,
    budget_micros: int | None,
    inputs_verified: bool,
    grant: UploadGrant | None,
    cost_bound: UploadCostBoundV2 | None,
) -> UploadPolicyState:
    validate_policy_choice(admission_policy, cost_policy, budget_micros)
    if type(inputs_verified) is not bool:
        raise ValueError("boolean input result required")
    if grant is not None and grant.scope != work.scope:
        raise ValueError("upload grant scope mismatch")
    risks: list[UploadRisk] = []
    blockers: list[UploadBlocker] = []
    if grant is None or grant.permissions != REQUIRED_PERMISSIONS:
        risks.append("authority_unverified")
        if admission_policy == "verified_only":
            blockers.append("authority_unverified")
    if not complete_cost(work, cost_bound):
        risks.append("cost_unverified")
        if cost_policy == "bounded_required":
            blockers.append("cost_unverified")
    if (
        budget_micros is not None
        and cost_bound is not None
        and cost_bound.maximum_micros > budget_micros
    ):
        blockers.append("cost_exceeds_budget")
    if not inputs_verified:
        blockers.append("inputs_unverified")
    status = _policy_status(cost_policy, risks, blockers)
    return UploadPolicyState(tuple(sorted(risks)), tuple(sorted(blockers)), status)


class DatasetUploadPlanV2(UploadWire):
    schema_version: Literal[2]
    policy_version: Literal[2]
    kind: Literal["dataset_upload_plan"]
    plan_id: str
    scope: UploadScope
    root: UploadRoot
    manifest: UploadManifestRef
    parameters: UploadParameters
    storage: UploadStoragePolicy
    admission_policy: AdmissionPolicy
    cost_policy: CostPolicy
    request_limits: UploadRequestLimits
    execution_window: UploadExecutionWindow
    budget_micros: NonnegativeInt64 | None
    inputs_verified: bool
    grant: UploadGrant | None
    cost_bound: UploadCostBoundV2 | None
    risks: Annotated[tuple[UploadRisk, ...], Field(max_length=2)]
    blockers: Annotated[tuple[UploadBlocker, ...], Field(max_length=4)]
    prepared_at: str
    expires_at: str
    status: UploadPlanStatus
    executable: Literal[False]
    digest: Sha256

    @field_validator("plan_id")
    @classmethod
    def identifier(cls, value: str) -> str:
        return canonical_uuid(value)

    def cost_work(self) -> UploadCostWork:
        return UploadCostWork(
            scope=self.scope,
            root=self.root,
            manifest=self.manifest,
            parameters=self.parameters,
            storage=self.storage,
            request_limits=self.request_limits,
            execution_window=self.execution_window,
        )

    @model_validator(mode="after")
    def consistent(self) -> Self:
        start, end = instant(self.prepared_at), instant(self.expires_at)
        if not (
            instant(self.execution_window.not_before)
            <= start
            < end
            <= instant(self.execution_window.not_after)
        ):
            raise ValueError("upload plan must fit fixed execution window")
        for evidence in (self.grant, self.cost_bound):
            if evidence is not None and (
                evidence.scope != self.scope
                or instant(evidence.checked_at) > start
                or end > instant(evidence.expires_at)
            ):
                raise ValueError("upload evidence scope or time mismatch")
        try:
            state = reduce_upload_policy(
                self.cost_work(),
                admission_policy=self.admission_policy,
                cost_policy=self.cost_policy,
                budget_micros=self.budget_micros,
                inputs_verified=self.inputs_verified,
                grant=self.grant,
                cost_bound=self.cost_bound,
            )
        except YorungeError:
            raise ValueError("invalid upload policy choice") from None
        if (self.risks, self.blockers, self.status) != (
            state.risks,
            state.blockers,
            state.status,
        ) or self.digest != self.computed_digest():
            raise ValueError("upload policy or plan digest mismatch")
        self.encoded()
        return self

    def computed_digest(self) -> str:
        return hashlib.sha256(
            canonical(self.model_dump(mode="json", exclude={"digest"}))
        ).hexdigest()

    def intent_digest(self) -> str:
        return hashlib.sha256(upload_namespace(self.scope, self.parameters.name)).hexdigest()

    def binding_digest(self) -> str:
        value = self.model_dump(
            mode="json", exclude={"plan_id", "digest", "prepared_at", "expires_at"}
        )
        for field in ("grant", "cost_bound"):
            if value[field] is not None:
                del value[field]["checked_at"], value[field]["expires_at"]
        return hashlib.sha256(canonical(value)).hexdigest()


class DatasetUploadApprovalV2(UploadWire):
    schema_version: Literal[2]
    approval_id: str
    plan_id: str
    plan_digest: Sha256
    binding_digest: Sha256
    store_id: str
    identity_epoch: str
    clock_generation: PositiveInt64
    admission_policy: AdmissionPolicy
    cost_policy: CostPolicy
    acknowledge_unverified_authority: bool
    acknowledge_unpriced_cost: bool
    approved_at: str
    expires_at: str
    status: Literal["approved", "revoked"]
    revoked_at: str | None

    @field_validator("approval_id", "plan_id", "store_id", "identity_epoch")
    @classmethod
    def identifier(cls, value: str) -> str:
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
        if self.admission_policy == "verified_only" and (
            self.cost_policy != "bounded_required"
            or self.acknowledge_unverified_authority
            or self.acknowledge_unpriced_cost
        ):
            raise ValueError("verified policy cannot acknowledge unknown risks")
        if self.cost_policy == "bounded_required" and self.acknowledge_unpriced_cost:
            raise ValueError("bounded policy cannot acknowledge unpriced cost")
        if (self.cost_policy == "unpriced_accepted") != self.acknowledge_unpriced_cost:
            raise ValueError("explicit unpriced acknowledgement required")
        self.encoded()
        return self


def require_acknowledgements(plan: DatasetUploadPlanV2, *, authority: bool, unpriced: bool) -> None:
    if plan.status == "draft":
        raise YorungeError("upload_plan_not_valid")
    if type(authority) is not bool or type(unpriced) is not bool:
        raise YorungeError("invalid_request")
    required = (
        "authority_unverified" in plan.risks,
        plan.cost_policy == "unpriced_accepted",
    )
    supplied = (authority, unpriced)
    if any(given and not needed for given, needed in zip(supplied, required, strict=True)):
        raise YorungeError("invalid_request")
    if supplied != required:
        raise YorungeError("approval_required")


def validate_approval_binding_v2(
    plan: DatasetUploadPlanV2, approval: DatasetUploadApprovalV2
) -> None:
    try:
        require_acknowledgements(
            plan,
            authority=approval.acknowledge_unverified_authority,
            unpriced=approval.acknowledge_unpriced_cost,
        )
    except YorungeError:
        raise ValueError("upload approval risk mismatch") from None
    if (
        (
            approval.plan_id,
            approval.plan_digest,
            approval.binding_digest,
            approval.store_id,
            approval.identity_epoch,
            approval.clock_generation,
            approval.admission_policy,
            approval.cost_policy,
        )
        != (
            plan.plan_id,
            plan.digest,
            plan.binding_digest(),
            plan.scope.store_id,
            plan.scope.identity_epoch,
            plan.scope.clock_generation,
            plan.admission_policy,
            plan.cost_policy,
        )
        or instant(approval.approved_at) < instant(plan.prepared_at)
        or instant(approval.expires_at) > instant(plan.expires_at)
    ):
        raise ValueError("upload approval binding mismatch")
