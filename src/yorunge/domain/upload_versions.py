"""Closed version families for transfer history; never upgrade stored payloads.

The v3 (continuation) types are not subclasses of the v2 ones, so a dispatch on "is it a v2
type, else v1" would take a v3 value for v1. Every helper here names each family it supports and
refuses any other value.
"""

import hashlib

from yorunge.domain.create_receipt import CreateReceiptV2
from yorunge.domain.dataset_continuation import (
    DatasetContinuationPlanV3,
    DatasetUploadApprovalV3,
    validate_approval_binding_v3,
)
from yorunge.domain.dataset_transfer import (
    StageIntent,
    StageReceipt,
    TransferControl,
    TransferRecord,
    TransferVerification,
)
from yorunge.domain.dataset_transfer_v2 import (
    TransferControlV2,
    TransferRecordV2,
    TransferVerificationV2,
)
from yorunge.domain.dataset_transfer_v3 import (
    TransferControlV3,
    TransferRecordV3,
    TransferVerificationV3,
)
from yorunge.domain.dataset_upload import (
    DatasetUploadApproval,
    DatasetUploadPlan,
    UploadScope,
    validate_approval_binding,
)
from yorunge.domain.dataset_upload_v2 import (
    DatasetUploadApprovalV2,
    DatasetUploadPlanV2,
    validate_approval_binding_v2,
)
from yorunge.domain.upload_graph import StageGraphSpec

UploadPlan = DatasetUploadPlan | DatasetUploadPlanV2 | DatasetContinuationPlanV3
UploadApproval = DatasetUploadApproval | DatasetUploadApprovalV2 | DatasetUploadApprovalV3
UploadRecord = TransferRecord | TransferRecordV2 | TransferRecordV3
UploadControl = TransferControl | TransferControlV2 | TransferControlV3
UploadVerification = TransferVerification | TransferVerificationV2 | TransferVerificationV3
# A continuation sends no create, so its receipts are stage receipts only.
UploadReceipt = StageReceipt | CreateReceiptV2


def validate_create_receipt(
    plan: UploadPlan, intent: StageIntent, receipt: CreateReceiptV2
) -> None:
    """Structural binding only; historical v1 receipts remain readable."""
    if not isinstance(plan, DatasetUploadPlanV2) or intent.kind != "create":
        raise ValueError("v2 create receipt requires v2 plan and create intent")
    dataset, parameters, owner = receipt.created_dataset, plan.parameters, plan.scope.owner
    selected_owner = dataset.owner_id if owner.kind == "user" else dataset.org_id
    if (
        dataset.id != receipt.dataset_id
        or selected_owner != owner.id
        or (dataset.name, dataset.modality, dataset.visibility, dataset.contributions_enabled)
        != (
            parameters.name,
            parameters.modality,
            parameters.visibility,
            parameters.contributions_enabled,
        )
    ):
        raise ValueError("created dataset differs from approved owner or parameters")


def validate_versioned_approval(plan: UploadPlan, approval: UploadApproval) -> None:
    if isinstance(plan, DatasetUploadPlan) and isinstance(approval, DatasetUploadApproval):
        validate_approval_binding(plan, approval)
    elif isinstance(plan, DatasetUploadPlanV2) and isinstance(approval, DatasetUploadApprovalV2):
        validate_approval_binding_v2(plan, approval)
    elif isinstance(plan, DatasetContinuationPlanV3) and isinstance(
        approval, DatasetUploadApprovalV3
    ):
        validate_approval_binding_v3(plan, approval)
    else:
        raise ValueError("mixed upload plan/approval versions")


def verification_scope(proof: UploadVerification) -> UploadScope:
    if isinstance(proof, TransferVerification):
        return proof.grant.scope
    if isinstance(proof, TransferVerificationV2 | TransferVerificationV3):
        return proof.scope
    raise ValueError("unsupported verification version")


def proof_digest(proof: UploadVerification) -> str:
    return hashlib.sha256(proof.encoded()).hexdigest()


def graph_of(plan: UploadPlan) -> StageGraphSpec:
    """The only stage graph of a stored plan; an unsupported version is rejected."""
    if isinstance(plan, DatasetContinuationPlanV3):
        return StageGraphSpec(
            plan.schema_version, plan.manifest.file_count, plan.continuation.file_indices
        )
    return StageGraphSpec(plan.schema_version, plan.manifest.file_count)
