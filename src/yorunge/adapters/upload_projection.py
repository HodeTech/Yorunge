"""Project validated history explicitly; never serialize private repository views."""

from yorunge.adapters.upload_store import VersionedTransferView
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.dataset_upload import REQUIRED_PERMISSIONS
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2, UploadRisk
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_public import (
    DatasetUploadSummary,
    DatasetUploadSummaryV3,
    UploadCostSummary,
    UploadIntentReview,
    UploadReviewTarget,
)
from yorunge.domain.upload_versions import UploadPlan


def _cost(plan: UploadPlan) -> UploadCostSummary | None:
    if not isinstance(plan, DatasetUploadPlanV2 | DatasetContinuationPlanV3) or (
        plan.cost_bound is None
    ):
        return None
    cost = plan.cost_bound
    return UploadCostSummary(
        schema_version=1,
        work_digest=cost.work_digest,
        maximum_micros=cost.maximum_micros,
        charge_categories=cost.charge_categories,
        charge_period_start=cost.charge_period_start,
        charge_period_end=cost.charge_period_end,
        post_period_storage=cost.post_period_storage,
        source_id=cost.source_id,
        source_version=cost.source_version,
        checked_at=cost.checked_at,
        expires_at=cost.expires_at,
    )


def _risks(plan: UploadPlan, grant_complete: bool) -> tuple[UploadRisk, ...]:
    if isinstance(plan, DatasetUploadPlanV2 | DatasetContinuationPlanV3):
        return plan.risks
    if grant_complete:
        return ("cost_unverified",)
    return ("authority_unverified", "cost_unverified")


def _continuation_summary(
    view: VersionedTransferView, plan: DatasetContinuationPlanV3
) -> DatasetUploadSummaryV3:
    record, approval = view.operation, view.approval
    succeeded = record is not None and record.status == "succeeded"
    grant_complete = plan.grant is not None and plan.grant.permissions == REQUIRED_PERMISSIONS
    binding = plan.continuation
    return DatasetUploadSummaryV3(
        schema_version=3,
        kind="dataset_upload_summary",
        source_plan_schema=3,
        legacy_history_only=False,
        plan_id=plan.plan_id,
        plan_digest=plan.digest,
        plan_status=plan.status,
        admission_policy=plan.admission_policy,
        cost_policy=plan.cost_policy,
        risks=plan.risks,
        blockers=plan.blockers,
        approval_status=approval.status if approval is not None else None,
        approval_expires_at=approval.expires_at if approval is not None else None,
        operation_id=record.operation_id if record is not None else None,
        operation_status=record.status if record is not None else None,
        dataset_id=binding.dataset_id,  # the plan names it, whatever the operation is
        verification_level="metadata" if succeeded else "none",
        remote_bytes_verified=False,
        authority_verified=succeeded and grant_complete,
        cost_bound=_cost(plan),
        budget_micros=plan.budget_micros,
        cost_scope="continuation_start_invocation",
        continuation_of=binding.source_operation_id,
        continuation_files=len(binding.file_indices),
        remote_present_files=binding.remote_present_count,
        uncertain_files=len(binding.uncertain_indices),
    )


def original_summary(view: VersionedTransferView) -> DatasetUploadSummary:
    """The summary of a v1/v2 upload; a continuation is refused, never called "legacy history".

    The public result types name no continuation yet: they call this one, so a stored continuation
    fails closed there until P02-3i widens them to :func:`summary`.
    """
    plan, record, approval = view.plan, view.operation, view.approval
    if isinstance(plan, DatasetContinuationPlanV3):
        raise YorungeError("state_invalid")
    modern = plan if isinstance(plan, DatasetUploadPlanV2) else None
    current = modern is not None
    succeeded = record is not None and record.status == "succeeded"
    grant_complete = plan.grant is not None and plan.grant.permissions == REQUIRED_PERMISSIONS
    return DatasetUploadSummary(
        schema_version=2,
        kind="dataset_upload_summary",
        source_plan_schema=plan.schema_version,
        legacy_history_only=not current,
        plan_id=plan.plan_id,
        plan_digest=plan.digest,
        plan_status=plan.status,
        admission_policy=modern.admission_policy if modern is not None else "verified_only",
        cost_policy=modern.cost_policy if modern is not None else "bounded_required",
        risks=_risks(plan, grant_complete),
        blockers=plan.blockers,
        approval_status=approval.status if approval is not None else None,
        approval_expires_at=approval.expires_at if approval is not None else None,
        operation_id=record.operation_id if record is not None else None,
        operation_status=record.status if record is not None else None,
        dataset_id=record.dataset_id if record is not None else None,
        verification_level="metadata" if succeeded else "none",
        remote_bytes_verified=False,
        authority_verified=succeeded and grant_complete,
        cost_bound=_cost(plan),
        budget_micros=plan.budget_micros,
        cost_scope="original_start_invocation" if current else "legacy_unknown",
    )


def summary(view: VersionedTransferView) -> DatasetUploadSummary | DatasetUploadSummaryV3:
    """The user view of a stored upload of any family: counts and identities, no paths or payloads.

    A continuation names the operation it continues and how many files it sends; it carries limits
    and cost like a v2 plan, so it is never "legacy history".
    """
    if isinstance(view.plan, DatasetContinuationPlanV3):
        return _continuation_summary(view, view.plan)
    return original_summary(view)


def review(view: VersionedTransferView) -> UploadIntentReview:
    """The review of a v1/v2 upload; the continuation's own review type is P02-3i's."""
    plan = view.plan
    return UploadIntentReview(
        schema_version=1,
        kind="dataset_upload_intent_review",
        summary=original_summary(view),
        target=UploadReviewTarget(
            service_origin=plan.scope.service_origin,
            api_base_path=plan.scope.api_base_path,
            profile=plan.scope.profile,
        ),
        selected_owner=plan.scope.owner,
        selected_project_id=plan.scope.project_id,
        root=plan.root.anchor,
        manifest=plan.manifest,
        parameters=plan.parameters,
        storage=plan.storage,
        request_limits=plan.request_limits if isinstance(plan, DatasetUploadPlanV2) else None,
        prepared_at=plan.prepared_at,
        expires_at=plan.expires_at,
    )
