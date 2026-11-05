"""Seal trusted v2 snapshots and approvals without changing historical plan evidence."""

import hashlib
import re
from dataclasses import dataclass

from yorunge.domain.capabilities import canonical, instant, timestamp
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_upload import UploadGrant, manifest_reference
from yorunge.domain.dataset_upload_v2 import (
    AdmissionPolicy,
    CostPolicy,
    DatasetUploadApprovalV2,
    DatasetUploadPlanV2,
    reduce_upload_policy,
    require_acknowledgements,
    validate_approval_binding_v2,
)
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_costs import UploadCostBoundV2, UploadCostWork


def parse_budget_cr(value: str) -> int:
    """Exact decimal CR to microcredits; no float, exponent, rounding or overflow."""
    if (
        type(value) is not str
        or len(value) > 32
        or re.fullmatch(r"\d+(?:\.\d{1,6})?", value, re.ASCII) is None
    ):
        raise YorungeError("invalid_request")
    whole, _, fraction = value.partition(".")
    result = int(whole) * 1_000_000 + int(fraction.ljust(6, "0"))
    if result >= 2**63:
        raise YorungeError("invalid_request")
    return result


@dataclass(frozen=True, kw_only=True)
class UploadPreparationV2:
    plan_id: str
    work: UploadCostWork
    manifest: DatasetManifest
    admission_policy: AdmissionPolicy
    cost_policy: CostPolicy
    budget_micros: int | None
    inputs_verified: bool
    grant: UploadGrant | None
    cost_bound: UploadCostBoundV2 | None
    prepared_at: str


def prepare_upload_v2(request: UploadPreparationV2) -> DatasetUploadPlanV2:
    work = request.work
    if manifest_reference(request.manifest) != work.manifest:
        raise YorungeError("input_changed")
    state = reduce_upload_policy(
        work,
        admission_policy=request.admission_policy,
        cost_policy=request.cost_policy,
        budget_micros=request.budget_micros,
        inputs_verified=request.inputs_verified,
        grant=request.grant,
        cost_bound=request.cost_bound,
    )
    end = instant(work.execution_window.not_after)
    for evidence in (request.grant, request.cost_bound):
        if evidence is not None:
            end = min(end, instant(evidence.expires_at))
    body = {
        **work.model_dump(mode="json"),
        "schema_version": 2,
        "policy_version": 2,
        "kind": "dataset_upload_plan",
        "plan_id": request.plan_id,
        "admission_policy": request.admission_policy,
        "cost_policy": request.cost_policy,
        "budget_micros": request.budget_micros,
        "inputs_verified": request.inputs_verified,
        "grant": request.grant.model_dump(mode="json") if request.grant is not None else None,
        "cost_bound": request.cost_bound.model_dump(mode="json")
        if request.cost_bound is not None
        else None,
        "risks": list(state.risks),
        "blockers": list(state.blockers),
        "prepared_at": request.prepared_at,
        "expires_at": timestamp(end),
        "status": state.status,
        "executable": False,
    }
    return DatasetUploadPlanV2.model_validate_json(
        canonical({**body, "digest": hashlib.sha256(canonical(body)).hexdigest()})
    )


def approve_upload_v2(
    plan: DatasetUploadPlanV2,
    *,
    approval_id: str,
    confirmed_digest: str,
    approved_at: str,
    acknowledge_unverified_authority: bool,
    acknowledge_unpriced_cost: bool,
) -> DatasetUploadApprovalV2:
    if plan.status == "draft" or not (
        instant(plan.prepared_at) <= instant(approved_at) < instant(plan.expires_at)
    ):
        raise YorungeError("upload_plan_not_valid")
    if confirmed_digest != plan.digest:
        raise YorungeError("upload_plan_not_valid")
    require_acknowledgements(
        plan,
        authority=acknowledge_unverified_authority,
        unpriced=acknowledge_unpriced_cost,
    )
    approval = DatasetUploadApprovalV2(
        schema_version=2,
        approval_id=approval_id,
        plan_id=plan.plan_id,
        plan_digest=plan.digest,
        binding_digest=plan.binding_digest(),
        store_id=plan.scope.store_id,
        identity_epoch=plan.scope.identity_epoch,
        clock_generation=plan.scope.clock_generation,
        admission_policy=plan.admission_policy,
        cost_policy=plan.cost_policy,
        acknowledge_unverified_authority=acknowledge_unverified_authority,
        acknowledge_unpriced_cost=acknowledge_unpriced_cost,
        approved_at=approved_at,
        expires_at=plan.expires_at,
        status="approved",
        revoked_at=None,
    )
    validate_approval_binding_v2(plan, approval)
    return approval
