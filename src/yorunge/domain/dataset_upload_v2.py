"""V2 upload policy, immutable plans and explicit risk acknowledgements."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated, Literal, Protocol, Self

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
    ContinuationCostWork,
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
    work: UploadCostWork | ContinuationCostWork,
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


class PlanFacts(Protocol):
    """What every upload plan version shares; the version-independent consistency rules read it."""

    @property
    def scope(self) -> UploadScope: ...
    @property
    def execution_window(self) -> UploadExecutionWindow: ...
    @property
    def admission_policy(self) -> AdmissionPolicy: ...
    @property
    def cost_policy(self) -> CostPolicy: ...
    @property
    def budget_micros(self) -> int | None: ...
    @property
    def inputs_verified(self) -> bool: ...
    @property
    def grant(self) -> UploadGrant | None: ...
    @property
    def cost_bound(self) -> UploadCostBoundV2 | None: ...
    @property
    def risks(self) -> tuple[UploadRisk, ...]: ...
    @property
    def blockers(self) -> tuple[UploadBlocker, ...]: ...
    @property
    def prepared_at(self) -> str: ...
    @property
    def expires_at(self) -> str: ...
    @property
    def status(self) -> UploadPlanStatus: ...
    @property
    def digest(self) -> str: ...

    def cost_work(self) -> UploadCostWork | ContinuationCostWork: ...
    def computed_digest(self) -> str: ...
    def encoded(self) -> bytes: ...


def validate_plan_facts(plan: PlanFacts) -> None:
    """Window, evidence, policy and digest rules shared by every plan version."""
    start, end = instant(plan.prepared_at), instant(plan.expires_at)
    if not (
        instant(plan.execution_window.not_before)
        <= start
        < end
        <= instant(plan.execution_window.not_after)
    ):
        raise ValueError("upload plan must fit fixed execution window")
    for evidence in (plan.grant, plan.cost_bound):
        if evidence is not None and (
            evidence.scope != plan.scope
            or instant(evidence.checked_at) > start
            or end > instant(evidence.expires_at)
        ):
            raise ValueError("upload evidence scope or time mismatch")
    try:
        state = reduce_upload_policy(
            plan.cost_work(),
            admission_policy=plan.admission_policy,
            cost_policy=plan.cost_policy,
            budget_micros=plan.budget_micros,
            inputs_verified=plan.inputs_verified,
            grant=plan.grant,
            cost_bound=plan.cost_bound,
        )
    except YorungeError:
        raise ValueError("invalid upload policy choice") from None
    if (plan.risks, plan.blockers, plan.status) != (
        state.risks,
        state.blockers,
        state.status,
    ) or plan.digest != plan.computed_digest():
        raise ValueError("upload policy or plan digest mismatch")
    plan.encoded()


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
        validate_plan_facts(self)
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


class ApprovalFacts(Protocol):
    """What every approval version shares; the version-independent lifetime and policy rules."""

    @property
    def approved_at(self) -> str: ...
    @property
    def expires_at(self) -> str: ...
    @property
    def status(self) -> Literal["approved", "revoked"]: ...
    @property
    def revoked_at(self) -> str | None: ...
    @property
    def admission_policy(self) -> AdmissionPolicy: ...
    @property
    def cost_policy(self) -> CostPolicy: ...
    @property
    def acknowledge_unverified_authority(self) -> bool: ...
    @property
    def acknowledge_unpriced_cost(self) -> bool: ...

    def encoded(self) -> bytes: ...


def validate_approval_facts(approval: ApprovalFacts) -> None:
    """Lifetime, revocation and risk-acknowledgement rules shared by every approval version."""
    start, end = instant(approval.approved_at), instant(approval.expires_at)
    if not timedelta(0) < end - start <= timedelta(seconds=UPLOAD_SECONDS):
        raise ValueError("bounded upload approval lifetime required")
    if (approval.status == "revoked") != (approval.revoked_at is not None):
        raise ValueError("upload revocation mismatch")
    if approval.revoked_at is not None and instant(approval.revoked_at) < start:
        raise ValueError("upload revocation precedes approval")
    if approval.admission_policy == "verified_only" and (
        approval.cost_policy != "bounded_required"
        or approval.acknowledge_unverified_authority
        or approval.acknowledge_unpriced_cost
    ):
        raise ValueError("verified policy cannot acknowledge unknown risks")
    if approval.cost_policy == "bounded_required" and approval.acknowledge_unpriced_cost:
        raise ValueError("bounded policy cannot acknowledge unpriced cost")
    if (approval.cost_policy == "unpriced_accepted") != approval.acknowledge_unpriced_cost:
        raise ValueError("explicit unpriced acknowledgement required")
    approval.encoded()


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
        validate_approval_facts(self)
        return self


def check_acknowledgements(
    status: UploadPlanStatus, supplied: tuple[bool, ...], required: tuple[bool, ...]
) -> None:
    """A draft is never approved; an unneeded flag is invalid, a missing needed one is refused."""
    if status == "draft":
        raise YorungeError("upload_plan_not_valid")
    if any(type(flag) is not bool for flag in supplied):
        raise YorungeError("invalid_request")
    if any(given and not needed for given, needed in zip(supplied, required, strict=True)):
        raise YorungeError("invalid_request")
    if supplied != required:
        raise YorungeError("approval_required")


def require_acknowledgements(plan: DatasetUploadPlanV2, *, authority: bool, unpriced: bool) -> None:
    check_acknowledgements(
        plan.status,
        (authority, unpriced),
        ("authority_unverified" in plan.risks, plan.cost_policy == "unpriced_accepted"),
    )


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
