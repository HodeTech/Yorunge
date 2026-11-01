"""Sequential Platform reads on one owned shared HTTP session; no authority inference."""

from __future__ import annotations

from types import TracebackType
from typing import Self

from yorunge.adapters.http_session import HttpSession
from yorunge.application import platform_projection as projection
from yorunge.application.context_discovery import DiscoveryClock, DiscoverySnapshot, remaining
from yorunge.application.http_transport import (
    HttpCredential,
    HttpRequest,
    HttpStatusFailure,
    HttpTransport,
)
from yorunge.application.platform_discovery import Endpoint, EndpointReply, PlatformReply
from yorunge.application.response_json import JSON_LIMIT
from yorunge.domain.capabilities import timestamp
from yorunge.domain.credentials import normalize_target
from yorunge.domain.errors import YorungeError


class PlatformReader:
    def __init__(self, clock: DiscoveryClock, *, session: HttpSession | None = None) -> None:
        self.clock = clock
        self.session = session if session is not None else HttpSession()

    def __enter__(self) -> Self:
        self.session.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.session.__exit__(exc_type, exc, traceback)

    def observe(self, snapshot: DiscoverySnapshot, *, deadline: float) -> PlatformReply:
        self.session.preflight()
        credential = snapshot.credential
        if (
            credential.reference.service_id != "evren-platform"
            or normalize_target(snapshot.context.platform_url) != credential.target
        ):
            raise YorungeError("invalid_service_target")
        observations: list[EndpointReply] = []

        def read(path: str, endpoint: Endpoint, *, resource: str | None = None) -> bytes | None:
            remaining(deadline, self.clock)
            started = timestamp(self.clock.now())
            data = self.session.call(
                lambda transport: self._read(
                    transport, snapshot, path, deadline, detail=resource is not None
                )
            )
            remaining(deadline, self.clock)
            observations.append(
                EndpointReply(
                    endpoint,
                    resource,
                    started,
                    timestamp(self.clock.now()),
                    "not_found" if data is None else "observed",
                )
            )
            return data

        def raw(path: str, endpoint: Endpoint, kind: str) -> object:
            data = read(path, endpoint)
            if data is None:
                raise YorungeError("invalid_response")
            return projection.safe_raw(data, kind, credential.secret)

        identity = projection.identity(raw("auth/me", "platform_me", "me"))
        organizations = projection.organizations(
            raw("organizations", "platform_organizations", "organizations")
        )
        projects = projection.projects(raw("projects", "platform_projects", "projects"))
        selected = None
        project_id = snapshot.context.project_id
        if project_id is not None:
            data = read(f"projects/{project_id}", "platform_project_detail", resource=project_id)
            if data is not None:
                selected = projection.detail(
                    projection.safe_raw(data, "detail", credential.secret), project_id
                )
        return PlatformReply(identity, organizations, projects, selected, tuple(observations))

    @staticmethod
    async def _read(
        transport: HttpTransport,
        snapshot: DiscoverySnapshot,
        path: str,
        deadline: float,
        *,
        detail: bool,
    ) -> bytes | None:
        credential = snapshot.credential
        request = HttpRequest(
            credential.target,
            "GET",
            path,
            service_id="evren-platform",
            credential=HttpCredential(
                "X-API-Key",
                credential.secret,
                target=credential.target,
                service_id="evren-platform",
            ),
            read_only=True,
            max_bytes=JSON_LIMIT,
        )
        data = bytearray()
        try:
            async with transport.open(request, deadline=deadline) as response:
                async for part in response.chunks():
                    if len(data) + len(part) > JSON_LIMIT:
                        raise YorungeError("invalid_response")
                    data.extend(part)
        except HttpStatusFailure as error:
            if error.status_code != 404:
                raise
            if detail:
                return None
            raise YorungeError("invalid_response") from None
        return bytes(data)
