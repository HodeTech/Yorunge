"""Test-only typed operation endpoints over the real bounded HTTP transport.

These adapters are deliberately absent from the product registry. The remote
fixture verifies captured authorization and job scope before producing evidence.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from datetime import timedelta
from typing import TypeVar
from urllib.parse import parse_qs, urlsplit

from pydantic import BaseModel

from tests.fixtures.http_server import Reply, RequestRecord
from yorunge.application.http_transport import (
    HttpCredential,
    HttpRequest,
    HttpStatusFailure,
    HttpTransport,
)
from yorunge.application.operation_observations import (
    OperationObservation,
    ReadAccess,
    ReadRequest,
)
from yorunge.application.operations import DispatchRequest, Submission
from yorunge.application.response_json import decode_response
from yorunge.domain.capabilities import timestamp
from yorunge.domain.credentials import BoundCredential
from yorunge.domain.errors import YorungeError
from yorunge.domain.execution import execution_service
from yorunge.domain.operations import AdmissionAuthority

T = TypeVar("T", bound=BaseModel)


def encoded(model: BaseModel) -> bytes:
    return model.model_dump_json().encode("utf-8")


class NetworkBackend:
    """StartPort/ReadPort fixture using captured credentials without env lookups."""

    def __init__(self, session):
        self.session = session
        self.before_start: Callable[[], None] | None = None
        self.start_timeout: float | None = None
        self.cancel_after_headers = False
        self.cancel_read_stage: str | None = None
        self.calls = 0

    def preflight(self):
        self.session.preflight()

    @staticmethod
    def _bound(request: DispatchRequest | ReadRequest) -> BoundCredential:
        service = execution_service(request.plan.selection)
        authorities = (
            request.admission.authorities
            if isinstance(request, DispatchRequest)
            else request.authorities
        )
        authority = next(a for a in authorities if a.service_id == service)
        bound = next(
            item
            for item in request.credentials
            if (
                item.credential.reference.service_id,
                item.credential.target.service_origin,
                item.credential.target.api_base_path,
                item.context.account_id,
                item.context.project_id,
                item.identity.credential_id,
                item.identity.credential_revision,
            )
            == (
                authority.service_id,
                authority.service_origin,
                authority.api_base_path,
                authority.account_id,
                authority.project_id,
                authority.credential_id,
                authority.credential_revision,
            )
        )
        return bound

    def _request(self, request, endpoint, *, start=False):
        bound = self._bound(request)
        credential = HttpCredential(
            "Authorization",
            bound.credential.secret,
            prefix="Bearer ",
            target=bound.credential.target,
            service_id=bound.credential.reference.service_id,
        )
        scope = (
            ("correlation", request.admission.correlation),
            ("attempt_id", request.attempt_id),
            ("account_id", bound.context.account_id or ""),
            ("project_id", bound.context.project_id or ""),
        )
        if not start:
            scope += (("provider_run_id", request.provider_run_id or ""),)
        return HttpRequest(
            bound.credential.target,
            "POST" if start else "GET",
            endpoint,
            query=scope,
            headers=(("Content-Type", "application/json"),) if start else (),
            content=encoded(request.admission) if start else b"",
            credential=credential,
            read_only=not start,
            service_id=bound.credential.reference.service_id,
        )

    def _consume(self, request, model: type[T], *, deadline, secrets, cancel=False) -> T:
        async def consume(client: HttpTransport):
            async with client.open(request, deadline=deadline) as response:
                if cancel:
                    task = asyncio.current_task()
                    assert task is not None
                    task.cancel()
                    await asyncio.sleep(0)
                body = b"".join([chunk async for chunk in response.chunks()])
                return decode_response(body, model, secrets=secrets)

        return self.session.call(consume)

    def start(self, request: DispatchRequest, *, deadline: float) -> Submission:
        import time

        self.calls += 1
        if self.before_start is not None:
            self.before_start()
        wanted = self._request(request, "fixture/start", start=True)
        if self.start_timeout is not None:
            deadline = min(deadline, time.monotonic() + self.start_timeout)
        return self._consume(
            wanted,
            Submission,
            deadline=deadline,
            secrets=tuple(c.credential.secret for c in request.credentials),
            cancel=self.cancel_after_headers,
        )

    def authorize(self, request: ReadRequest, *, deadline: float) -> ReadAccess:
        wanted = self._request(request, "fixture/access")
        try:
            return self._consume(
                wanted,
                ReadAccess,
                deadline=deadline,
                secrets=tuple(c.credential.secret for c in request.credentials),
                cancel=self.cancel_read_stage == "access",
            )
        except HttpStatusFailure as error:
            if error.status_code in (401, 403):
                raise PermissionError("fixture access denied") from None
            raise ConnectionError("fixture authorization unavailable") from None
        except YorungeError as error:
            if error.code == "invalid_response":
                raise ValueError("fixture malformed authorization") from None
            if error.code in {"transport_failed", "transport_timeout"}:
                raise ConnectionError("fixture authorization unavailable") from None
            raise

    def observe(
        self, request: ReadRequest, access: ReadAccess, *, deadline: float
    ) -> OperationObservation:
        wanted = self._request(request, "fixture/observe")
        kind = "unavailable"
        try:
            return self._consume(
                wanted,
                OperationObservation,
                deadline=deadline,
                secrets=tuple(c.credential.secret for c in request.credentials),
                cancel=self.cancel_read_stage == "observe",
            )
        except HttpStatusFailure as error:
            if error.status_code == 404:
                kind = "not_found"
            elif error.status_code in (401, 403):
                kind = "unauthorized"
        except YorungeError as error:
            if error.code == "invalid_response":
                raise ValueError("fixture malformed observation") from None
            if error.code not in {"transport_failed", "transport_timeout"}:
                raise
        return OperationObservation(
            kind=kind,
            correlation=request.admission.correlation,
            authority=access.authorities[0],
            provider_run_id=request.provider_run_id,
            provider_status=None,
            provider_exit_code=None,
            execution_status="unknown",
            delivery_status="pending",
        )


class OperationEndpoint:
    """Synthetic remote effect/evidence; a generic 2xx is never success proof."""

    def __init__(self, clock, secret: str):
        self.clock, self.secret = clock, secret
        self.effects: list[str] = []
        self.authority: AdmissionAuthority | None = None
        self.correlation: str | None = None
        self.provider_run_id = "tls-fixture-run-1"
        self.start_reply: Callable[[bytes], Reply] = lambda body: Reply(body=body)
        self.access_reply: Callable[[bytes], Reply] = lambda body: Reply(body=body)
        self.observe_reply: Callable[[bytes], Reply] = lambda body: Reply(body=body)
        self.observation_change: Callable[[OperationObservation], OperationObservation] | None = (
            None
        )

    def scope(self, request: RequestRecord):
        assert request.header("Authorization") == "Bearer " + self.secret
        scope = {key: values[0] for key, values in parse_qs(urlsplit(request.path).query).items()}
        assert scope["account_id"] == "fixture-account"
        assert scope["project_id"] == "fixture-project"
        if self.correlation is not None:
            assert scope["correlation"] == self.correlation
            assert scope["attempt_id"] == self.effects[0]
            assert scope.get("provider_run_id", self.provider_run_id) == self.provider_run_id
        return scope

    def start(self, request: RequestRecord, count: int) -> Reply:
        scope = self.scope(request)
        assert request.method == "POST"
        data = json.loads(request.body)
        self.authority = AdmissionAuthority.model_validate_json(json.dumps(data["authorities"][0]))
        assert self.authority.service_id == "evren-platform"
        assert self.authority.service_origin == "https://localhost"
        assert self.authority.api_base_path == "/v1"
        assert self.authority.account_id == scope["account_id"]
        assert self.authority.project_id == scope["project_id"]
        assert data["correlation"] == scope["correlation"]
        self.correlation = data["correlation"]
        self.effects.append(scope["attempt_id"])
        receipt = Submission(
            correlation=self.correlation,
            authority=self.authority,
            provider_run_id=self.provider_run_id,
            provider_status="queued",
            running=False,
        )
        return self.start_reply(encoded(receipt))

    def access(self, request: RequestRecord, count: int) -> Reply:
        self.scope(request)
        assert request.method == "GET"
        assert self.authority is not None
        access = ReadAccess(
            authorities=(self.authority,),
            checked_at=timestamp(self.clock.now()),
            expires_at=timestamp(self.clock.now() + timedelta(seconds=60)),
        )
        return self.access_reply(encoded(access))

    def observe(self, request: RequestRecord, count: int) -> Reply:
        self.scope(request)
        assert request.method == "GET"
        assert self.correlation is not None
        assert self.authority is not None
        observation = OperationObservation(
            kind="observed",
            correlation=self.correlation,
            authority=self.authority,
            provider_run_id=self.provider_run_id,
            provider_status="complete",
            provider_exit_code=0,
            execution_status="succeeded",
            delivery_status="complete",
        )
        if self.observation_change is not None:
            observation = self.observation_change(observation)
        return self.observe_reply(encoded(observation))

    def route(self, request: RequestRecord, count: int) -> Reply:
        path = urlsplit(request.path).path
        return {
            "/v1/fixture/start": self.start,
            "/v1/fixture/access": self.access,
            "/v1/fixture/observe": self.observe,
        }[path](request, count)

    def routes(self):
        endpoint = self

        class Routes(dict):
            def get(self, key, default=None):
                if urlsplit(key).path in {
                    "/v1/fixture/start",
                    "/v1/fixture/access",
                    "/v1/fixture/observe",
                }:
                    return endpoint.route
                return default

        return Routes()
