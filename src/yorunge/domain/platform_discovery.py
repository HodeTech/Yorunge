"""Closed, explicitly unverified Platform observations, independent of provider authority."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from yorunge.domain.credentials import ServiceTarget, normalize_target
from yorunge.domain.discovery import DiscoveryBinding, ProfilePreference, canonical_time
from yorunge.domain.models import Identifier, Model

ReportedState = Literal["reported_id", "reported_null", "not_exposed"]
PlatformReason = Literal[
    "account_semantics_unknown",
    "authorization_not_verified",
    "identity_not_verified",
    "list_completeness_unknown",
    "remote_snapshot_not_guaranteed",
    "profile_scope_unknown",
    "project_selection_required",
    "selected_project_not_found",
    "provider_listing_incomplete",
]


def reported(value: str | None, state: ReportedState) -> bool:
    return (value is not None) == (state == "reported_id")


class ReportedIdentity(Model):
    me_id: Identifier
    organization_id: Identifier | None
    organization_id_state: ReportedState
    personal_organization_id: Identifier | None
    personal_organization_id_state: ReportedState

    @model_validator(mode="after")
    def states(self) -> ReportedIdentity:
        if not reported(self.organization_id, self.organization_id_state) or not reported(
            self.personal_organization_id, self.personal_organization_id_state
        ):
            raise ValueError("reported identity state mismatch")
        return self


class PlatformSelected(Model):
    account_id: Identifier | None
    project_id: Identifier | None


class PlatformProvider(Model):
    principal_id: None
    account_id: None
    organization_id: None
    project_id: None
    identity_status: Literal["unverified"]


class OrganizationRef(Model):
    id: Identifier


class ProjectRef(Model):
    id: Identifier
    organization_id: Identifier | None
    organization_id_state: ReportedState

    @model_validator(mode="after")
    def state(self) -> ProjectRef:
        if not reported(self.organization_id, self.organization_id_state):
            raise ValueError("reported parent state mismatch")
        return self


class OrganizationListing(Model):
    items: Annotated[tuple[OrganizationRef, ...], Field(max_length=128)]
    reported_total: Annotated[int, Field(ge=0, le=2**63 - 1)]

    @model_validator(mode="after")
    def listing(self) -> OrganizationListing:
        if self.reported_total < len(self.items) or len({v.id for v in self.items}) != len(
            self.items
        ):
            raise ValueError("invalid organization listing")
        return self


class ProjectSelection(Model):
    state: Literal["not_selected", "observed", "not_found"]
    project: ProjectRef | None

    @model_validator(mode="after")
    def selection(self) -> ProjectSelection:
        if (self.state == "observed") != (self.project is not None):
            raise ValueError("invalid project selection")
        return self


class ProjectListing(Model):
    items: Annotated[tuple[ProjectRef, ...], Field(max_length=128)]
    selection: ProjectSelection

    @model_validator(mode="after")
    def listing(self) -> ProjectListing:
        if len({v.id for v in self.items}) != len(self.items):
            raise ValueError("duplicate project")
        return self


class PlatformCompleteness(Model):
    organizations: Literal["unknown", "incomplete"]
    projects: Literal["unknown"]


class PlatformEndpointObservation(Model):
    endpoint_id: Literal[
        "platform_me", "platform_organizations", "platform_projects", "platform_project_detail"
    ]
    resource_id: Identifier | None
    started_at: str
    completed_at: str
    authentication: Literal["unknown"]
    outcome: Literal["observed", "not_found"]

    @field_validator("started_at", "completed_at")
    @classmethod
    def times(cls, value: str) -> str:
        return canonical_time(value)

    @model_validator(mode="after")
    def endpoint(self) -> PlatformEndpointObservation:
        detail = self.endpoint_id == "platform_project_detail"
        if detail != (self.resource_id is not None) or (not detail and self.outcome != "observed"):
            raise ValueError("endpoint resource mismatch")
        if self.started_at > self.completed_at:
            raise ValueError("invalid endpoint interval")
        return self


def platform_reasons(
    preference: ProfilePreference, projects: ProjectSelection, completeness: PlatformCompleteness
) -> tuple[PlatformReason, ...]:
    reasons: list[PlatformReason] = [
        "account_semantics_unknown",
        "authorization_not_verified",
        "identity_not_verified",
        "list_completeness_unknown",
        "remote_snapshot_not_guaranteed",
    ]
    if preference.service_scope == "unknown":
        reasons.append("profile_scope_unknown")
    if projects.state == "not_selected":
        reasons.append("project_selection_required")
    if projects.state == "not_found":
        reasons.append("selected_project_not_found")
    if completeness.organizations == "incomplete":
        reasons.append("provider_listing_incomplete")
    return tuple(sorted(reasons))


class PlatformContextDiscovery(Model):
    schema_version: Literal[1]
    service_id: Literal["evren-platform"]
    profile: Identifier
    target: ServiceTarget
    binding: DiscoveryBinding
    profile_preference: ProfilePreference
    selected: PlatformSelected
    provider: PlatformProvider
    reported_identity: ReportedIdentity
    authorization_scope: None
    organizations: OrganizationListing
    projects: ProjectListing
    list_completeness: PlatformCompleteness
    terms: None
    observed_from: str
    observed_until: str
    validated_at: str
    observations: Annotated[
        tuple[PlatformEndpointObservation, ...], Field(min_length=3, max_length=4)
    ]
    consistency: Literal["not_guaranteed"]
    validation: Literal["unverified"]
    reasons: tuple[PlatformReason, ...]

    @field_validator("observed_from", "observed_until", "validated_at")
    @classmethod
    def times(cls, value: str) -> str:
        return canonical_time(value)

    @model_validator(mode="after")
    def observation(self) -> PlatformContextDiscovery:
        if normalize_target(self.target.service_origin + self.target.api_base_path) != self.target:
            raise ValueError("canonical target required")
        selected, selection = self.selected.project_id, self.projects.selection
        if (selected is None) != (selection.state == "not_selected"):
            raise ValueError("selection mismatch")
        if selection.project is not None and selection.project.id != selected:
            raise ValueError("selected project mismatch")
        expected = ["platform_me", "platform_organizations", "platform_projects"]
        if selected is not None:
            expected.append("platform_project_detail")
        if [v.endpoint_id for v in self.observations] != expected:
            raise ValueError("endpoint order mismatch")
        last = self.observed_from
        for endpoint in self.observations:
            if not last <= endpoint.started_at <= endpoint.completed_at <= self.observed_until:
                raise ValueError("invalid observation interval")
            last = endpoint.completed_at
        if self.observed_until > self.validated_at:
            raise ValueError("invalid final interval")
        if selected is not None:
            detail = self.observations[-1]
            if detail.resource_id != selected or detail.outcome != (
                "not_found" if selection.state == "not_found" else "observed"
            ):
                raise ValueError("detail outcome mismatch")
        completeness = (
            "incomplete"
            if self.organizations.reported_total > len(self.organizations.items)
            else "unknown"
        )
        if self.list_completeness.organizations != completeness:
            raise ValueError("completeness mismatch")
        if self.selected.account_id != self.profile_preference.account_id:
            raise ValueError("account preference mismatch")
        if self.reasons != platform_reasons(
            self.profile_preference, selection, self.list_completeness
        ):
            raise ValueError("closed discovery reasons required")
        if len(self.model_dump_json().encode("utf-8")) > 262_144:
            raise ValueError("discovery output limit")
        return self
