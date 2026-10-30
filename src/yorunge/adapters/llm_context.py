"""One real LLM terms endpoint on the shared, owned HTTP boundary."""

from __future__ import annotations

from types import TracebackType
from typing import Annotated, Self

from pydantic import Field, field_validator

from yorunge.adapters.http_session import HttpSession
from yorunge.application.context_discovery import (
    DiscoveryClock,
    DiscoverySnapshot,
    TermsReply,
    remaining,
)
from yorunge.application.http_transport import (
    HttpCredential,
    HttpRequest,
    HttpStatusFailure,
    HttpTransport,
)
from yorunge.application.response_json import JSON_LIMIT, decode_response
from yorunge.domain.capabilities import timestamp
from yorunge.domain.credentials import normalize_target
from yorunge.domain.discovery import TermsObservation
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import has_control_characters


class RawTermsStatus(TermsObservation):
    doc_path: Annotated[str, Field(min_length=1, max_length=2048)]

    @field_validator("doc_path")
    @classmethod
    def private_path(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 8192 or has_control_characters(value):
            raise ValueError("invalid terms metadata")
        return value


class LlmTermsReader:
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

    def observe(self, snapshot: DiscoverySnapshot, *, deadline: float) -> TermsReply:
        self.session.preflight()
        remaining(deadline, self.clock)
        started = timestamp(self.clock.now())
        raw = self.session.call(lambda transport: self._read(transport, snapshot, deadline))
        remaining(deadline, self.clock)
        return TermsReply(
            TermsObservation(
                accepted=raw.accepted,
                current_version=raw.current_version,
                is_material=raw.is_material,
            ),
            started_at=started,
            completed_at=timestamp(self.clock.now()),
        )

    @staticmethod
    async def _read(
        transport: HttpTransport, snapshot: DiscoverySnapshot, deadline: float
    ) -> RawTermsStatus:
        credential = snapshot.credential
        if (
            credential.reference.service_id != "evren-llm"
            or normalize_target(snapshot.context.llm_url) != credential.target
        ):
            raise YorungeError("invalid_service_target")
        request = HttpRequest(
            credential.target,
            "GET",
            "terms/status",
            service_id="evren-llm",
            credential=HttpCredential(
                "Authorization",
                credential.secret,
                prefix="Bearer ",
                target=credential.target,
                service_id="evren-llm",
            ),
            read_only=True,
            max_bytes=JSON_LIMIT,
        )
        missing = False
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
            missing = True
        if missing:
            raise YorungeError("invalid_response")
        return decode_response(bytes(data), RawTermsStatus, secrets=(credential.secret,))
