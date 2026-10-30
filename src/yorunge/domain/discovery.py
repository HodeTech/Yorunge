"""Closed LLM discovery observations; profile preferences never become remote authority."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.credentials import ServiceTarget, normalize_target
from yorunge.domain.models import Identifier, Model
from yorunge.domain.state import canonical_uuid

PositiveInt64 = Annotated[int, Field(ge=1, le=2**63 - 1)]
DiscoveryReason = Literal[
    "authorization_not_verified",
    "identity_not_exposed",
    "profile_scope_unknown",
    "remote_snapshot_not_guaranteed",
    "terms_not_accepted",
]


def canonical_time(value: str) -> str:
    if timestamp(instant(value)) != value:
        raise ValueError("canonical UTC required")
    return value


class DiscoveryBinding(Model):
    store_id: str
    identity_epoch: str
    clock_generation: PositiveInt64
    credential_id: str
    credential_revision: PositiveInt64

    @field_validator("store_id", "identity_epoch", "credential_id")
    @classmethod
    def identifiers(cls, value: str) -> str:
        return canonical_uuid(value)


class ProfilePreference(Model):
    account_id: Identifier | None
    project_id: Identifier | None
    service_scope: Literal["unknown", "not_applicable"]

    @model_validator(mode="after")
    def scoped_preference(self) -> ProfilePreference:
        expected = (
            "unknown"
            if self.account_id is not None or self.project_id is not None
            else "not_applicable"
        )
        if self.service_scope != expected:
            raise ValueError("preference scope mismatch")
        return self


class LlmSelected(Model):
    account_id: None
    project_id: None


class LlmProvider(Model):
    principal_id: None
    account_id: None
    organization_id: None
    project_id: None
    identity_status: Literal["not_exposed"]


class TermsObservation(Model):
    accepted: bool
    current_version: Annotated[int, Field(ge=0, le=2**63 - 1)]
    is_material: bool


class TermsEndpointObservation(Model):
    endpoint_id: Literal["llm_terms_status"]
    started_at: str
    completed_at: str
    authentication: Literal["unknown"]

    @field_validator("started_at", "completed_at")
    @classmethod
    def times(cls, value: str) -> str:
        return canonical_time(value)

    @model_validator(mode="after")
    def ordered(self) -> TermsEndpointObservation:
        if self.started_at > self.completed_at:
            raise ValueError("invalid observation interval")
        return self


def discovery_reasons(
    preference: ProfilePreference, terms: TermsObservation
) -> tuple[DiscoveryReason, ...]:
    reasons: list[DiscoveryReason] = [
        "authorization_not_verified",
        "identity_not_exposed",
        "remote_snapshot_not_guaranteed",
    ]
    if preference.service_scope == "unknown":
        reasons.append("profile_scope_unknown")
    if not terms.accepted:
        reasons.append("terms_not_accepted")
    return tuple(sorted(reasons))


class ContextDiscovery(Model):
    schema_version: Literal[1]
    service_id: Literal["evren-llm"]
    profile: Identifier
    target: ServiceTarget
    binding: DiscoveryBinding
    profile_preference: ProfilePreference
    selected: LlmSelected
    provider: LlmProvider
    authorization_scope: None
    organizations: None
    projects: None
    list_completeness: Literal["not_exposed"]
    terms: TermsObservation
    observed_from: str
    observed_until: str
    validated_at: str
    observations: tuple[TermsEndpointObservation]
    consistency: Literal["not_guaranteed"]
    validation: Literal["unverified"]
    reasons: tuple[DiscoveryReason, ...]

    @field_validator("observed_from", "observed_until", "validated_at")
    @classmethod
    def times(cls, value: str) -> str:
        return canonical_time(value)

    @model_validator(mode="after")
    def closed_observation(self) -> ContextDiscovery:
        if normalize_target(self.target.service_origin + self.target.api_base_path) != self.target:
            raise ValueError("canonical target required")
        endpoint = self.observations[0]
        if not (
            self.observed_from
            <= endpoint.started_at
            <= endpoint.completed_at
            <= self.observed_until
            <= self.validated_at
        ):
            raise ValueError("invalid observation interval")
        if self.reasons != discovery_reasons(self.profile_preference, self.terms):
            raise ValueError("closed discovery reasons required")
        if len(self.model_dump_json().encode("utf-8")) > 262_144:
            raise ValueError("discovery output limit")
        return self
