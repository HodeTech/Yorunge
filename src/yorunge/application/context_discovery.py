"""One owned discovery exchange followed by a fresh local authority gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from types import TracebackType
from typing import Protocol, Self

from pydantic import ValidationError

from yorunge.domain.capabilities import timestamp
from yorunge.domain.credentials import CredentialIdentity, ResolvedCredential
from yorunge.domain.discovery import (
    ContextDiscovery,
    DiscoveryBinding,
    LlmProvider,
    LlmSelected,
    ProfilePreference,
    TermsEndpointObservation,
    TermsObservation,
    discovery_reasons,
)
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Context


class DiscoveryClock(Protocol):
    def now(self) -> datetime: ...
    def monotonic(self) -> float: ...


class ObservationClock:
    """Retain UTC rollback observed between the two short store connections."""

    def __init__(self, source: DiscoveryClock) -> None:
        self.source = source
        self.highest: datetime | None = None
        self.regressed = False

    def now(self) -> datetime:
        value = self.source.now()
        if self.highest is not None and value < self.highest:
            self.regressed = True
        self.highest = value if self.highest is None else max(self.highest, value)
        return value

    def monotonic(self) -> float:
        return self.source.monotonic()


@dataclass(frozen=True, repr=False)
class DiscoverySnapshot:
    context: Context
    binding: DiscoveryBinding
    credential: ResolvedCredential = field(repr=False)
    identity: CredentialIdentity
    captured_at: datetime

    def __repr__(self) -> str:
        return "<DiscoverySnapshot private>"


@dataclass(frozen=True)
class TermsReply:
    terms: TermsObservation
    started_at: str
    completed_at: str


class DiscoveryState(Protocol):
    def capture(self, *, deadline: float) -> DiscoverySnapshot: ...
    def finish(self, snapshot: DiscoverySnapshot, *, deadline: float) -> str: ...


class TermsReader(Protocol):
    def __enter__(self) -> Self: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    def observe(self, snapshot: DiscoverySnapshot, *, deadline: float) -> TermsReply: ...


def remaining(deadline: float, clock: DiscoveryClock) -> float:
    value = deadline - clock.monotonic()
    if value <= 0:
        raise YorungeError("transport_timeout")
    return value


def _finish_failure(
    state: DiscoveryState,
    snapshot: DiscoverySnapshot,
    deadline: float,
    primary: BaseException,
) -> None:
    try:
        state.finish(snapshot, deadline=deadline)
    except YorungeError as error:
        # A changed binding is expected after persisting a witnessed clock rollback.
        # Preserve cancellation/control flow and any pre-existing operation uncertainty.
        if (
            error.code == "state_changed"
            or not isinstance(primary, Exception)
            or (isinstance(primary, YorungeError) and primary.exit_code == 5)
        ):
            return
        # A failed local durability/budget gate outranks an ordinary read failure.
        raise


def discover_context(
    state: DiscoveryState, reader: TermsReader, clock: DiscoveryClock, *, deadline: float
) -> ContextDiscovery:
    """No caller evidence or permission input; an observation never enables execution."""
    available = remaining(deadline, clock)
    # Reserve final-store/clock cleanup within the same total, including failure paths.
    network_deadline = deadline - min(5.0, available / 3)
    started = timestamp(clock.now())
    # Entering the owner rejects event-loop/thread/PID misuse before capture reads env/state.
    snapshot: DiscoverySnapshot | None = None
    try:
        with reader:
            remaining(deadline, clock)
            snapshot = state.capture(deadline=deadline)
            reply = reader.observe(snapshot, deadline=network_deadline)
            remaining(network_deadline, clock)
    except BaseException as primary:
        if snapshot is not None:
            _finish_failure(state, snapshot, deadline, primary)
        raise
    # Close the response/client/Runner before the final store/credential/clock check.
    observed_until = timestamp(clock.now())
    validated_at = state.finish(snapshot, deadline=deadline)
    remaining(deadline, clock)
    context = snapshot.context
    preference = ProfilePreference(
        account_id=context.account_id,
        project_id=context.project_id,
        service_scope="unknown"
        if context.account_id is not None or context.project_id is not None
        else "not_applicable",
    )
    try:
        result = ContextDiscovery(
            schema_version=1,
            service_id="evren-llm",
            profile=context.profile,
            target=snapshot.credential.target,
            binding=snapshot.binding,
            profile_preference=preference,
            selected=LlmSelected(account_id=None, project_id=None),
            provider=LlmProvider(
                principal_id=None,
                account_id=None,
                organization_id=None,
                project_id=None,
                identity_status="not_exposed",
            ),
            authorization_scope=None,
            organizations=None,
            projects=None,
            list_completeness="not_exposed",
            terms=reply.terms,
            observed_from=started,
            observed_until=observed_until,
            validated_at=validated_at,
            observations=(
                TermsEndpointObservation(
                    endpoint_id="llm_terms_status",
                    started_at=reply.started_at,
                    completed_at=reply.completed_at,
                    authentication="unknown",
                ),
            ),
            consistency="not_guaranteed",
            validation="unverified",
            reasons=discovery_reasons(preference, reply.terms),
        )
    except ValidationError:
        raise YorungeError("state_changed") from None
    remaining(deadline, clock)
    return result
