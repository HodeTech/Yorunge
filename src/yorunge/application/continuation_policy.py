"""Derive, seal and approve continuation snapshots from values the caller already holds.

Everything here is a pure function of its arguments: no store, clock or network. The producer
builds the limits, the binding and the plan with these functions and the approval gate builds the
approval with ``approve_upload_v3``. A plan never authorises a send (``executable`` stays false);
the approval is a separate value bound to the plan's digests and acknowledgements.
"""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

from yorunge.domain.capabilities import canonical, instant, timestamp
from yorunge.domain.dataset_continuation import (
    ContinuationBinding,
    DatasetContinuationPlanV3,
    DatasetUploadApprovalV3,
    require_continuation_acknowledgements,
    validate_approval_binding_v3,
    validate_continuation_selection,
)
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_upload import UploadGrant, manifest_reference
from yorunge.domain.dataset_upload_v2 import AdmissionPolicy, CostPolicy, reduce_upload_policy
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_costs import (
    ContinuationCostWork,
    ContinuationRequestLimits,
    UploadCostBoundV2,
)
from yorunge.domain.upload_resume import Classification


def continuation_limits(
    manifest: DatasetManifest, file_indices: Sequence[int]
) -> ContinuationRequestLimits:
    """Request ceilings of a continuation that sends exactly these manifest files (M may be 0)."""
    indices = tuple(file_indices)
    if (
        any(type(i) is not int for i in indices)
        or list(indices) != sorted(set(indices))
        or any(not 0 <= i < len(manifest.files) for i in indices)
    ):
        raise ValueError("ordered distinct manifest file indices required")
    return ContinuationRequestLimits(
        max_create=0,
        max_project_link=0,
        max_presign=len(indices),
        max_put=len(indices),
        max_confirm=len(indices),
        max_read_requests=512,
        max_read_attempts=1024,
        max_control_request_bytes=4194304,
        max_control_response_bytes=16777216,
        max_upload_bytes=sum(manifest.files[i].size for i in indices),
    )


def continuation_binding(
    classification: Classification,
    *,
    source_operation_id: str,
    baseline_operation_id: str,
    dataset_id: str,
    baseline_digest: str,
    intent_digest: str,
    observed_at: str,
) -> ContinuationBinding:
    """The binding of exactly what ``classification`` says; any blocker refuses it.

    The selection and both digests come from the classification and nowhere else, so
    ``binding_matches`` holds for the classification a binding was built from.
    """
    selection = classification.selection()
    if selection is None:
        raise ValueError("a classification with blockers cannot be bound")
    return ContinuationBinding(
        source_operation_id=source_operation_id,
        baseline_operation_id=baseline_operation_id,
        dataset_id=dataset_id,
        baseline_digest=baseline_digest,
        intent_digest=intent_digest,
        file_indices=selection.file_indices,
        uncertain_indices=selection.uncertain_indices,
        remote_present_count=selection.remote_present_count,
        classification_digest=classification.classification_digest,
        inventory_digest=classification.inventory_digest,
        observed_at=observed_at,
    )


@dataclass(frozen=True, kw_only=True)
class ContinuationPreparation:
    """The trusted producer's captured input; a public caller never supplies this snapshot."""

    plan_id: str
    work: ContinuationCostWork
    manifest: DatasetManifest
    binding: ContinuationBinding
    admission_policy: AdmissionPolicy
    cost_policy: CostPolicy
    budget_micros: int | None
    inputs_verified: bool
    grant: UploadGrant | None
    cost_bound: UploadCostBoundV2 | None
    prepared_at: str


def prepare_continuation_v3(request: ContinuationPreparation) -> DatasetContinuationPlanV3:
    """Seal the plan: the longest lifetime its window and its evidence allow, a computed digest."""
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
        "schema_version": 3,
        "policy_version": 3,
        "kind": "dataset_upload_continuation_plan",
        "plan_id": request.plan_id,
        "admission_policy": request.admission_policy,
        "cost_policy": request.cost_policy,
        "budget_micros": request.budget_micros,
        "inputs_verified": request.inputs_verified,
        "grant": request.grant.model_dump(mode="json") if request.grant is not None else None,
        "cost_bound": request.cost_bound.model_dump(mode="json")
        if request.cost_bound is not None
        else None,
        "continuation": request.binding.model_dump(mode="json"),
        "risks": list(state.risks),
        "blockers": list(state.blockers),
        "prepared_at": request.prepared_at,
        "expires_at": timestamp(end),
        "status": state.status,
        "executable": False,
    }
    plan = DatasetContinuationPlanV3.model_validate_json(
        canonical({**body, "digest": hashlib.sha256(canonical(body)).hexdigest()})
    )
    validate_continuation_selection(plan, request.manifest)
    return plan


def approve_upload_v3(
    plan: DatasetContinuationPlanV3,
    *,
    approval_id: str,
    confirmed_digest: str,
    approved_at: str,
    acknowledge_unverified_authority: bool,
    acknowledge_unpriced_cost: bool,
    acknowledge_unconfirmed_effects: bool,
) -> DatasetUploadApprovalV3:
    """Approve exactly the plan whose digest the user confirmed, with exactly the needed flags."""
    if type(plan) is not DatasetContinuationPlanV3:
        raise YorungeError("upload_plan_not_valid")
    if plan.status == "draft" or not (
        instant(plan.prepared_at) <= instant(approved_at) < instant(plan.expires_at)
    ):
        raise YorungeError("upload_plan_not_valid")
    if confirmed_digest != plan.digest:
        raise YorungeError("upload_plan_not_valid")
    require_continuation_acknowledgements(
        plan,
        authority=acknowledge_unverified_authority,
        unpriced=acknowledge_unpriced_cost,
        unconfirmed=acknowledge_unconfirmed_effects,
    )
    approval = DatasetUploadApprovalV3(
        schema_version=3,
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
        acknowledge_unconfirmed_effects=acknowledge_unconfirmed_effects,
        approved_at=approved_at,
        expires_at=plan.expires_at,
        status="approved",
        revoked_at=None,
    )
    validate_approval_binding_v3(plan, approval)
    return approval
