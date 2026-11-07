"""Typed current checks: unavailable authority is never an absent oracle."""

from __future__ import annotations

from datetime import timedelta
from typing import Literal, Self

from pydantic import field_validator, model_validator

from yorunge.domain.capabilities import canonical, instant
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.dataset_manifest import Sha256
from yorunge.domain.dataset_upload import (
    REQUIRED_PERMISSIONS,
    UploadGrant,
    UploadPermission,
    UploadScope,
    UploadWire,
    provider_uuid,
)
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import ErrorCode, YorungeError
from yorunge.domain.models import Identifier
from yorunge.domain.state import canonical_uuid
from yorunge.domain.upload_costs import UploadCostBoundV2, complete_cost, validate_cost_binding

ConsumerProfile = Literal["evren-platform-observed-upload-v2"]
AuthorizationOutcome = Literal["allowed", "not_exposed", "denied", "unavailable", "invalid"]
UNAVAILABLE_CODES = frozenset(
    {"transport_timeout", "transport_failed", "remote_rate_limited", "remote_failed"}
)


def mandatory_http_failure(status: int) -> tuple[AuthorizationOutcome, ErrorCode]:
    """Called for non-2xx mandatory reads, never to infer oracle absence."""
    if type(status) is not int or not 100 <= status <= 599 or 200 <= status <= 299:
        raise ValueError("non-success HTTP status required")
    if status in (401, 403):
        return "denied", "remote_access_denied"
    if status == 429:
        return "unavailable", "remote_rate_limited"
    if status >= 500:
        return "unavailable", "remote_failed"
    return "invalid", "invalid_response"


class AuthorizationCheck(UploadWire):
    consumer_profile: ConsumerProfile
    policy_version: Literal[2]
    action: UploadPermission
    scope: UploadScope
    dataset_id: str | None
    producer_id: Identifier
    producer_version: Identifier
    checked_at: str
    outcome: AuthorizationOutcome
    grant: UploadGrant | None
    error_code: ErrorCode | None

    @field_validator("dataset_id")
    @classmethod
    def identifier(cls, value: str | None) -> str | None:
        return None if value is None else provider_uuid(value)

    @model_validator(mode="after")
    def evidence(self) -> Self:
        instant(self.checked_at)
        if self.outcome == "allowed":
            if (
                self.grant is None
                or self.grant.scope != self.scope
                or self.action not in self.grant.permissions
                or not instant(self.grant.checked_at)
                <= instant(self.checked_at)
                < instant(self.grant.expires_at)
                or self.error_code is not None
            ):
                raise ValueError("allowed action requires actual scoped grant")
        elif self.grant is not None or not self._error_matches():
            raise ValueError("authorization outcome/error mismatch")
        return self

    def _error_matches(self) -> bool:
        if self.outcome == "not_exposed":
            return self.error_code is None
        if self.outcome == "denied":
            return self.error_code == "remote_access_denied"
        if self.outcome == "invalid":
            return self.error_code == "invalid_response"
        return self.error_code in UNAVAILABLE_CODES

    def require_current(
        self, scope: UploadScope, action: UploadPermission, dataset_id: str | None, now: str
    ) -> None:
        if (self.scope, self.action, self.dataset_id) != (scope, action, dataset_id):
            raise YorungeError("state_changed")
        require_fresh(self.checked_at, now)
        if self.error_code is not None:
            raise YorungeError(self.error_code)
        if self.grant is not None:
            require_live_evidence(self.grant, now)


class UploadObservation(UploadWire):
    consumer_profile: ConsumerProfile
    policy_version: Literal[2]
    scope: UploadScope
    dataset_id: str
    checked_at: str
    has_upload: bool

    @field_validator("dataset_id")
    @classmethod
    def identifier(cls, value: str) -> str:
        return provider_uuid(value)

    @model_validator(mode="after")
    def observation(self) -> Self:
        instant(self.checked_at)
        return self

    def require_current(self, scope: UploadScope, dataset_id: str, now: str) -> None:
        if (self.scope, self.dataset_id) != (scope, dataset_id):
            raise YorungeError("state_changed")
        require_fresh(self.checked_at, now)
        if not self.has_upload:
            raise YorungeError("remote_access_denied")


def require_fresh(checked_at: str, now: str) -> None:
    if not timedelta(0) <= instant(now) - instant(checked_at) <= timedelta(seconds=30):
        raise YorungeError("upload_plan_not_valid")


def require_live_evidence(value: UploadGrant | UploadCostBoundV2, now: str) -> None:
    if not instant(value.checked_at) <= instant(now) < instant(value.expires_at):
        raise YorungeError("upload_plan_not_valid")


def grant_semantics(value: UploadGrant) -> bytes:
    return canonical(value.model_dump(mode="json", exclude={"checked_at", "expires_at"}))


def require_same_baseline(
    original: UploadGrant | UploadCostBoundV2 | None,
    current: UploadGrant | UploadCostBoundV2 | None,
) -> None:
    if original is None and current is None:
        return
    if original is None or current is None or type(original) is not type(current):
        raise YorungeError("upload_plan_not_valid")
    old = (
        grant_semantics(original) if isinstance(original, UploadGrant) else original.semantic_key()
    )
    new = grant_semantics(current) if isinstance(current, UploadGrant) else current.semantic_key()
    if old != new:
        raise YorungeError("upload_plan_not_valid")


class UploadCurrentCheck(UploadWire):
    saved_plan_id: str
    saved_plan_digest: Sha256
    saved_binding_digest: Sha256
    work_digest: Sha256
    scope: UploadScope
    checked_at: str
    baseline_grant: UploadGrant | None
    baseline_cost_bound: UploadCostBoundV2 | None
    supplemental_grant: UploadGrant | None
    supplemental_cost_bound: UploadCostBoundV2 | None
    authorization: AuthorizationCheck
    inputs_verified: bool
    upload_observation: UploadObservation | None

    @field_validator("saved_plan_id")
    @classmethod
    def identifier(cls, value: str) -> str:
        return canonical_uuid(value)

    @model_validator(mode="after")
    def check_time(self) -> Self:
        instant(self.checked_at)
        return self

    def require_current(
        self,
        plan: DatasetUploadPlanV2 | DatasetContinuationPlanV3,
        *,
        now: str,
        action: UploadPermission,
        dataset_id: str | None,
    ) -> tuple[str, ...]:
        if self.scope != plan.scope or not self.inputs_verified:
            raise YorungeError("state_changed")
        if (
            self.saved_plan_id,
            self.saved_plan_digest,
            self.saved_binding_digest,
            self.work_digest,
        ) != (plan.plan_id, plan.digest, plan.binding_digest(), plan.cost_work().digest()):
            raise YorungeError("upload_plan_not_valid")
        if plan.status == "draft" or not (
            instant(plan.prepared_at) <= instant(now) < instant(plan.expires_at)
        ):
            raise YorungeError("upload_plan_not_valid")
        require_fresh(self.checked_at, now)
        self.authorization.require_current(plan.scope, action, dataset_id, now)
        if plan.admission_policy == "verified_only" and self.authorization.outcome != "allowed":
            raise YorungeError("upload_plan_not_valid")
        expiries = self._evidence(plan, now)
        if action == "upload_created_dataset":
            if self.upload_observation is None or dataset_id is None:
                raise YorungeError("upload_plan_not_valid")
            self.upload_observation.require_current(plan.scope, dataset_id, now)
        return expiries

    def _evidence(
        self, plan: DatasetUploadPlanV2 | DatasetContinuationPlanV3, now: str
    ) -> tuple[str, ...]:
        saved = (plan.grant, plan.cost_bound)
        baseline = (self.baseline_grant, self.baseline_cost_bound)
        for original, current in zip(saved, baseline, strict=True):
            require_same_baseline(original, current)
        if self.supplemental_grant is not None and (
            (plan.grant is not None and plan.grant.permissions == REQUIRED_PERMISSIONS)
            or self.supplemental_grant.scope != plan.scope
            or self.supplemental_grant.permissions != REQUIRED_PERMISSIONS
        ):
            raise YorungeError("upload_plan_not_valid")
        if self.supplemental_cost_bound is not None:
            try:
                supplement_allowed = not complete_cost(
                    plan.cost_work(), plan.cost_bound
                ) and complete_cost(plan.cost_work(), self.supplemental_cost_bound)
            except ValueError:
                supplement_allowed = False
            if not supplement_allowed:
                raise YorungeError("upload_plan_not_valid")
        if self.baseline_cost_bound is not None:
            validate_cost_binding(plan.cost_work(), self.baseline_cost_bound)
        evidence = (
            *saved,
            *baseline,
            self.supplemental_grant,
            self.supplemental_cost_bound,
            self.authorization.grant,
        )
        for value in evidence:
            if value is not None:
                require_live_evidence(value, now)
        return tuple(value.expires_at for value in evidence if value is not None)
