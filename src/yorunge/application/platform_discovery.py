"""Platform projection composed only after the shared fresh local state gate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import ValidationError

from yorunge.application.context_discovery import (
    DiscoveryClock,
    DiscoveryReader,
    DiscoveryState,
    exchange,
    remaining,
)
from yorunge.application.response_json import check_response_secrets
from yorunge.domain.errors import YorungeError
from yorunge.domain.platform_discovery import (
    OrganizationListing,
    PlatformCompleteness,
    PlatformContextDiscovery,
    PlatformEndpointObservation,
    PlatformProvider,
    PlatformSelected,
    ProjectListing,
    ProjectRef,
    ProjectSelection,
    ReportedIdentity,
    platform_reasons,
)

Endpoint = Literal[
    "platform_me", "platform_organizations", "platform_projects", "platform_project_detail"
]


@dataclass(frozen=True)
class EndpointReply:
    endpoint_id: Endpoint
    resource_id: str | None
    started_at: str
    completed_at: str
    outcome: Literal["observed", "not_found"]


@dataclass(frozen=True)
class PlatformReply:
    identity: ReportedIdentity
    organizations: OrganizationListing
    projects: tuple[ProjectRef, ...]
    selected: ProjectRef | None
    observations: tuple[EndpointReply, ...]


def discover_platform(
    state: DiscoveryState,
    reader: DiscoveryReader[PlatformReply],
    clock: DiscoveryClock,
    *,
    deadline: float,
) -> PlatformContextDiscovery:
    snapshot, reply, started, until, validated = exchange(state, reader, clock, deadline=deadline)
    context = snapshot.context
    preference = snapshot.preference
    if preference is None:
        raise YorungeError("state_invalid")
    selection_state: Literal["not_selected", "not_found", "observed"] = "not_selected"
    if context.project_id is not None:
        selection_state = "not_found" if reply.selected is None else "observed"
    selection = ProjectSelection(state=selection_state, project=reply.selected)
    completeness = PlatformCompleteness(
        organizations="incomplete"
        if reply.organizations.reported_total > len(reply.organizations.items)
        else "unknown",
        projects="unknown",
    )
    try:
        result = PlatformContextDiscovery(
            schema_version=1,
            service_id="evren-platform",
            profile=context.profile,
            target=snapshot.credential.target,
            binding=snapshot.binding,
            profile_preference=preference,
            selected=PlatformSelected(account_id=context.account_id, project_id=context.project_id),
            provider=PlatformProvider(
                principal_id=None,
                account_id=None,
                organization_id=None,
                project_id=None,
                identity_status="unverified",
            ),
            reported_identity=reply.identity,
            authorization_scope=None,
            organizations=reply.organizations,
            projects=ProjectListing(items=reply.projects, selection=selection),
            list_completeness=completeness,
            terms=None,
            observed_from=started,
            observed_until=until,
            validated_at=validated,
            observations=tuple(
                PlatformEndpointObservation(
                    endpoint_id=v.endpoint_id,
                    resource_id=v.resource_id,
                    started_at=v.started_at,
                    completed_at=v.completed_at,
                    authentication="unknown",
                    outcome=v.outcome,
                )
                for v in reply.observations
            ),
            consistency="not_guaranteed",
            validation="unverified",
            reasons=platform_reasons(preference, selection, completeness),
        )
    except ValidationError:
        raise YorungeError("state_changed") from None
    check_response_secrets(result, (snapshot.credential.secret,))
    remaining(deadline, clock)
    return result
