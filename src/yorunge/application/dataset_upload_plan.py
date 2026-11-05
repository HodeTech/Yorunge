"""Seal a captured upload preparation; public callers cannot inject this private snapshot."""

import hashlib
from dataclasses import dataclass
from datetime import timedelta

from yorunge.domain.capabilities import canonical, instant, timestamp
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_upload import (
    UPLOAD_SECONDS,
    DatasetUploadPlan,
    UploadCostBound,
    UploadGrant,
    UploadParameters,
    UploadRoot,
    UploadScope,
    UploadStoragePolicy,
    manifest_reference,
    upload_blockers,
)


@dataclass(frozen=True, kw_only=True)
class UploadPreparation:
    """Trusted composition's captured input, never a public proof/verified flag endpoint."""

    plan_id: str
    scope: UploadScope
    root: UploadRoot
    manifest: DatasetManifest
    parameters: UploadParameters
    storage: UploadStoragePolicy
    budget_micros: int
    inputs_verified: bool
    grant: UploadGrant | None
    cost_bound: UploadCostBound | None
    prepared_at: str


def prepare_upload_snapshot(request: UploadPreparation) -> DatasetUploadPlan:
    """Build an immutable record, deriving blockers/expiry without fabricating evidence."""
    end = instant(request.prepared_at) + timedelta(seconds=UPLOAD_SECONDS)
    for observation in (request.grant, request.cost_bound):
        if observation is not None:
            end = min(end, instant(observation.expires_at))
    blockers = upload_blockers(
        request.inputs_verified, request.grant, request.cost_bound, request.budget_micros
    )
    body = {
        "schema_version": 1,
        "policy_version": 1,
        "kind": "dataset_upload_plan",
        "plan_id": request.plan_id,
        "scope": request.scope.model_dump(mode="json"),
        "root": request.root.model_dump(mode="json"),
        "manifest": manifest_reference(request.manifest).model_dump(mode="json"),
        "parameters": request.parameters.model_dump(mode="json"),
        "storage": request.storage.model_dump(mode="json"),
        "budget_micros": request.budget_micros,
        "inputs_verified": request.inputs_verified,
        "grant": request.grant.model_dump(mode="json") if request.grant is not None else None,
        "cost_bound": request.cost_bound.model_dump(mode="json")
        if request.cost_bound is not None
        else None,
        "blockers": list(blockers),
        "prepared_at": request.prepared_at,
        "expires_at": timestamp(end),
        "status": "draft" if blockers else "prepared",
        "executable": False,
    }
    # Hash canonical bytes independently of model_construct/revalidation shortcuts.
    return DatasetUploadPlan.model_validate_json(
        canonical({**body, "digest": hashlib.sha256(canonical(body)).hexdigest()})
    )
