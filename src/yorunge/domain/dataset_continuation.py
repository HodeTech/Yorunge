"""V3 continuation plans and approvals: a new, human-approved send of what a source left open.

A continuation never revives its source. It is a separate plan, approval and operation that names
the source and the lineage root, binds the dataset and the immutable baseline the root created, and
carries exactly the files that still need a transfer. Everything here is a closed, strict value; it
performs no I/O and never grants authority.
"""

from __future__ import annotations

import hashlib
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from yorunge.domain.capabilities import PositiveInt64, canonical, instant
from yorunge.domain.dataset_manifest import DatasetManifest, Sha256
from yorunge.domain.dataset_transfer import FileIndex
from yorunge.domain.dataset_upload import (
    MAX_UPLOAD_FILES,
    NonnegativeInt64,
    UploadBlocker,
    UploadGrant,
    UploadManifestRef,
    UploadParameters,
    UploadRoot,
    UploadScope,
    UploadStoragePolicy,
    UploadWire,
    manifest_reference,
    provider_uuid,
    upload_namespace,
)
from yorunge.domain.dataset_upload_v2 import (
    AdmissionPolicy,
    CostPolicy,
    UploadPlanStatus,
    UploadRisk,
    check_acknowledgements,
    validate_approval_facts,
    validate_plan_facts,
)
from yorunge.domain.errors import YorungeError
from yorunge.domain.platform_upload import ProviderDataset
from yorunge.domain.state import canonical_uuid
from yorunge.domain.upload_costs import (
    ContinuationCostWork,
    ContinuationRequestLimits,
    UploadCostBoundV2,
    UploadExecutionWindow,
)
from yorunge.domain.upload_resume import Classification


def baseline_digest(created: ProviderDataset) -> str:
    """Digest of the immutable dataset the root operation created (the DTO itself stays private)."""
    return hashlib.sha256(
        canonical({"kind": "upload_baseline", "dataset": created.model_dump(mode="json")})
    ).hexdigest()


class ContinuationBinding(UploadWire):
    source_operation_id: str
    baseline_operation_id: str
    dataset_id: str
    baseline_digest: Sha256
    intent_digest: Sha256
    file_indices: Annotated[tuple[FileIndex, ...], Field(max_length=MAX_UPLOAD_FILES)]
    uncertain_indices: Annotated[tuple[FileIndex, ...], Field(max_length=MAX_UPLOAD_FILES)]
    remote_present_count: Annotated[int, Field(ge=0, le=MAX_UPLOAD_FILES)]
    classification_digest: Sha256
    inventory_digest: Sha256
    observed_at: str

    @field_validator("source_operation_id", "baseline_operation_id")
    @classmethod
    def operation(cls, value: str) -> str:
        return canonical_uuid(value)

    @field_validator("dataset_id")
    @classmethod
    def dataset(cls, value: str) -> str:
        return provider_uuid(value)

    @model_validator(mode="after")
    def selection(self) -> Self:
        instant(self.observed_at)
        files, uncertain = self.file_indices, self.uncertain_indices
        if list(files) != sorted(set(files)):
            raise ValueError("ordered distinct file indices required")
        if list(uncertain) != sorted(set(uncertain)) or not set(uncertain) <= set(files):
            raise ValueError("uncertain files must be an ordered subset of the selection")
        return self


class DatasetContinuationPlanV3(UploadWire):
    schema_version: Literal[3]
    policy_version: Literal[3]
    kind: Literal["dataset_upload_continuation_plan"]
    plan_id: str
    scope: UploadScope
    root: UploadRoot
    manifest: UploadManifestRef
    parameters: UploadParameters
    storage: UploadStoragePolicy
    admission_policy: AdmissionPolicy
    cost_policy: CostPolicy
    request_limits: ContinuationRequestLimits
    execution_window: UploadExecutionWindow
    budget_micros: NonnegativeInt64 | None
    inputs_verified: bool
    grant: UploadGrant | None
    cost_bound: UploadCostBoundV2 | None
    continuation: ContinuationBinding
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

    def cost_work(self) -> ContinuationCostWork:
        return ContinuationCostWork(
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
        binding, limits = self.continuation, self.request_limits
        count = self.manifest.file_count
        if (
            len(binding.file_indices) != limits.files
            or any(index >= count for index in binding.file_indices)
            or binding.remote_present_count != count - limits.files
            or binding.intent_digest != self.intent_digest()
        ):
            raise ValueError("continuation binding must match the plan manifest and limits")
        validate_plan_facts(self)
        return self

    def computed_digest(self) -> str:
        return hashlib.sha256(
            canonical(self.model_dump(mode="json", exclude={"digest"}))
        ).hexdigest()

    def intent_digest(self) -> str:
        return hashlib.sha256(upload_namespace(self.scope, self.parameters.name)).hexdigest()

    def binding_digest(self) -> str:
        """Everything the approval commits to; observation instants may move without a new plan."""
        value = self.model_dump(
            mode="json", exclude={"plan_id", "digest", "prepared_at", "expires_at"}
        )
        for field in ("grant", "cost_bound"):
            if value[field] is not None:
                del value[field]["checked_at"], value[field]["expires_at"]
        del value["continuation"]["observed_at"]
        return hashlib.sha256(canonical(value)).hexdigest()


def validate_continuation_selection(
    plan: DatasetContinuationPlanV3, manifest: DatasetManifest
) -> None:
    """The check that needs the full manifest: the plan carries only its reference."""
    if manifest_reference(manifest) != plan.manifest:
        raise ValueError("manifest does not match the continuation plan")
    selected = sum(manifest.files[i].size for i in plan.continuation.file_indices)
    if selected != plan.request_limits.max_upload_bytes:
        raise ValueError("selected file bytes differ from the continuation limit")


class DatasetUploadApprovalV3(UploadWire):
    schema_version: Literal[3]
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
    acknowledge_unconfirmed_effects: bool
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


def require_continuation_acknowledgements(
    plan: DatasetContinuationPlanV3, *, authority: bool, unpriced: bool, unconfirmed: bool
) -> None:
    """The v2 acknowledgements, plus one for files whose last confirm may or may not have landed."""
    check_acknowledgements(
        plan.status,
        (authority, unpriced, unconfirmed),
        (
            "authority_unverified" in plan.risks,
            plan.cost_policy == "unpriced_accepted",
            bool(plan.continuation.uncertain_indices),
        ),
    )


def validate_approval_binding_v3(
    plan: DatasetContinuationPlanV3, approval: DatasetUploadApprovalV3
) -> None:
    if type(plan) is not DatasetContinuationPlanV3 or type(approval) is not DatasetUploadApprovalV3:
        raise ValueError("mixed upload plan/approval versions")
    try:
        require_continuation_acknowledgements(
            plan,
            authority=approval.acknowledge_unverified_authority,
            unpriced=approval.acknowledge_unpriced_cost,
            unconfirmed=approval.acknowledge_unconfirmed_effects,
        )
    except YorungeError:
        raise ValueError("continuation approval risk mismatch") from None
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
        raise ValueError("continuation approval binding mismatch")


def binding_matches(binding: ContinuationBinding, classification: Classification) -> bool:
    """Whether a fresh classification still says what an approved plan bound.

    A plan carries indices and digests, never the class vector, so this is where the selection and
    both digests are checked against the evidence: producer and admission call it, and any blocker
    in the fresh classification makes it false.
    """
    selection = classification.selection()
    return (
        selection is not None
        and binding.file_indices == selection.file_indices
        and binding.uncertain_indices == selection.uncertain_indices
        and binding.remote_present_count == selection.remote_present_count
        and binding.classification_digest == classification.classification_digest
        and binding.inventory_digest == classification.inventory_digest
    )
