"""Closed version pairs for transfer history; never upgrade stored payloads."""

import hashlib

from yorunge.domain.dataset_transfer import (
    StageKind,
    TransferControl,
    TransferRecord,
    TransferVerification,
)
from yorunge.domain.dataset_transfer_v2 import (
    TransferControlV2,
    TransferRecordV2,
    TransferVerificationV2,
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

UploadPlan = DatasetUploadPlan | DatasetUploadPlanV2
UploadApproval = DatasetUploadApproval | DatasetUploadApprovalV2
UploadRecord = TransferRecord | TransferRecordV2
UploadControl = TransferControl | TransferControlV2
UploadVerification = TransferVerification | TransferVerificationV2


def validate_versioned_approval(plan: UploadPlan, approval: UploadApproval) -> None:
    if isinstance(plan, DatasetUploadPlan) and isinstance(approval, DatasetUploadApproval):
        validate_approval_binding(plan, approval)
    elif isinstance(plan, DatasetUploadPlanV2) and isinstance(approval, DatasetUploadApprovalV2):
        validate_approval_binding_v2(plan, approval)
    else:
        raise ValueError("mixed upload plan/approval versions")


def verification_scope(proof: UploadVerification) -> UploadScope:
    return proof.scope if isinstance(proof, TransferVerificationV2) else proof.grant.scope


def proof_digest(proof: UploadVerification) -> str:
    return hashlib.sha256(proof.encoded()).hexdigest()


def required_stages(file_count: int) -> frozenset[tuple[StageKind, int | None]]:
    result: set[tuple[StageKind, int | None]] = {("create", None), ("project_link", None)}
    per_file: tuple[StageKind, ...] = ("presign", "put", "confirm")
    result.update((kind, i) for i in range(file_count) for kind in per_file)
    return frozenset(result)
