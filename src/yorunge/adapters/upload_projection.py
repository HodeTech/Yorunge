"""Project validated history explicitly; never serialize private repository views."""

from yorunge.adapters.upload_store import VersionedTransferView
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.dataset_upload import REQUIRED_PERMISSIONS
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2, UploadRisk
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_public import (
    DatasetUploadSummary,
    UploadCostSummary,
    UploadIntentReview,
    UploadReviewTarget,
)
from yorunge.domain.upload_versions import UploadPlan


def _cost(plan: UploadPlan) -> UploadCostSummary | None:
    if not isinstance(plan, DatasetUploadPlanV2) or plan.cost_bound is None:
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
    if isinstance(plan, DatasetUploadPlanV2):
        return plan.risks
    if grant_complete:
        return ("cost_unverified",)
    return ("authority_unverified", "cost_unverified")


def summary(view: VersionedTransferView) -> DatasetUploadSummary:
    plan, record, approval = view.plan, view.operation, view.approval
    if isinstance(plan, DatasetContinuationPlanV3):
        # A continuation is not "legacy history": its projection is P02-3v's, until then it fails.
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


def review(view: VersionedTransferView) -> UploadIntentReview:
    plan = view.plan
    return UploadIntentReview(
        schema_version=1,
        kind="dataset_upload_intent_review",
        summary=summary(view),
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
