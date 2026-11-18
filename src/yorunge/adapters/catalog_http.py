"""Read-only catalog calls on the shared HTTP boundary (P02-4d, ADR-0035 Karar 1, 2, 5 and 10).

Each public function is one command: it resolves the selected profile's credential once, runs
the GET requests of that command on one session under one 30 s window, and hands the bytes and
headers to ``application.catalog`` together with the selected secret. Model-scoped answers map
404 to ``model_not_visible`` and 422 to ``invalid_request``; every other status keeps the
transport's own closed code. No state is opened or written.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Final, Generic, TypeVar

from yorunge.adapters.capability_cache import SystemClock
from yorunge.adapters.http_session import HttpSession
from yorunge.adapters.secrets import EnvSecretReader
from yorunge.application import catalog as codec
from yorunge.application.credentials import resolve_credential
from yorunge.application.http_transport import (
    HttpCredential,
    HttpRequest,
    HttpStatusFailure,
    HttpTransport,
)
from yorunge.application.response_json import JSON_LIMIT
from yorunge.domain import catalog
from yorunge.domain.capabilities import timestamp
from yorunge.domain.catalog import (
    LlmListing,
    LlmModel,
    PlatformModel,
    PlatformVersion,
    VersionListing,
)
from yorunge.domain.credentials import ResolvedCredential
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Context, Profile, ServiceId

T = TypeVar("T")

PLATFORM: Final[ServiceId] = "evren-platform"
LLM: Final[ServiceId] = "evren-llm"
WINDOW_SECONDS: Final = 30.0  # one catalog command, all of its requests

ContextLoader = Callable[[], tuple[Context, Profile]]


@dataclass(frozen=True)
class Observed(Generic[T]):
    """What a command read, with the window it was read in (``observed_from`` to ``until``)."""

    value: T
    observed_from: str
    observed_until: str


@dataclass(frozen=True)
class _Bytes:
    body: bytes
    headers: tuple[tuple[str, str], ...]


def _credential(loader: ContextLoader, service_id: ServiceId) -> ResolvedCredential:
    _context, profile = loader()
    return resolve_credential(profile, service_id, EnvSecretReader())


def _request(
    resolved: ResolvedCredential,
    service_id: ServiceId,
    endpoint: str,
    query: tuple[tuple[str, str], ...] = (),
) -> HttpRequest:
    if service_id == PLATFORM:
        header = HttpCredential(
            "X-API-Key", resolved.secret, target=resolved.target, service_id=service_id
        )
    else:
        header = HttpCredential(
            "Authorization",
            resolved.secret,
            prefix="Bearer ",
            target=resolved.target,
            service_id=service_id,
        )
    return HttpRequest(
        resolved.target,
        "GET",
        endpoint,
        query=query,
        service_id=service_id,
        credential=header,
        read_only=True,
        max_bytes=JSON_LIMIT,
    )


async def _get(transport: HttpTransport, request: HttpRequest, deadline: float) -> _Bytes:
    data = bytearray()
    async with transport.open(request, deadline=deadline) as response:
        async for part in response.chunks():
            if len(data) + len(part) > JSON_LIMIT:
                raise YorungeError("invalid_response")
            data.extend(part)
        headers = tuple((str(key), str(value)) for key, value in response.headers)
    return _Bytes(bytes(data), headers)


async def _model_scoped(transport: HttpTransport, request: HttpRequest, deadline: float) -> _Bytes:
    """A model-scoped answer: 404 is "not visible to this key", 422 a refused request."""
    try:
        return await _get(transport, request, deadline)
    except HttpStatusFailure as error:
        if error.status_code == 404:
            raise YorungeError("model_not_visible") from None
        if error.status_code == 422:
            raise YorungeError("invalid_request") from None
        raise


def _run(
    loader: ContextLoader,
    service_id: ServiceId,
    steps: Callable[[HttpTransport, ResolvedCredential, float], Awaitable[T]],
) -> Observed[T]:
    """One command: one credential, one session, one window, one deadline."""
    resolved = _credential(loader, service_id)
    clock = SystemClock()
    started = timestamp(clock.now())
    deadline = time.monotonic() + WINDOW_SECONDS

    async def exchange(transport: HttpTransport) -> T:
        return await steps(transport, resolved, deadline)

    with HttpSession() as session:
        value = session.call(exchange)
    return Observed(value, started, timestamp(clock.now()))


def _page_query(page: int, page_size: int) -> tuple[tuple[str, str], ...]:
    return (("page", str(page)), ("page_size", str(page_size)))


# --- Platform -----------------------------------------------------------------------------------


def list_platform_models(
    loader: ContextLoader, page: int, page_size: int
) -> Observed[catalog.PlatformModelPage]:
    catalog.page_arguments(page, page_size)

    async def steps(
        transport: HttpTransport, resolved: ResolvedCredential, deadline: float
    ) -> catalog.PlatformModelPage:
        request = _request(resolved, PLATFORM, "models", _page_query(page, page_size))
        got = await _get(transport, request, deadline)
        return codec.platform_models(got.body, resolved.secret, page, page_size)

    return _run(loader, PLATFORM, steps)


def show_platform_model(
    loader: ContextLoader, owner: str, slug: str, *, versions: bool
) -> Observed[tuple[PlatformModel, VersionListing | None]]:
    owner, slug = catalog.require_address(owner, slug)

    async def steps(
        transport: HttpTransport, resolved: ResolvedCredential, deadline: float
    ) -> tuple[PlatformModel, VersionListing | None]:
        detail = await _model_scoped(
            transport, _request(resolved, PLATFORM, f"models/{owner}/{slug}"), deadline
        )
        model = codec.platform_model(detail.body, resolved.secret)
        catalog.detail_identity(model.owner_username, model.slug, owner, slug)
        if not versions:
            return model, None
        listed = await _model_scoped(
            transport,
            _request(resolved, PLATFORM, f"models/{catalog.segment(model.model_id)}/versions"),
            deadline,
        )
        return model, codec.platform_versions(listed.body, resolved.secret, model.versions_count)

    return _run(loader, PLATFORM, steps)


def list_platform_versions(loader: ContextLoader, model_id: str) -> Observed[VersionListing]:
    """The version list of a model addressed by its identifier (the owner-less route)."""
    model_id = catalog.segment(model_id)

    async def steps(
        transport: HttpTransport, resolved: ResolvedCredential, deadline: float
    ) -> VersionListing:
        listed = await _model_scoped(
            transport, _request(resolved, PLATFORM, f"models/{model_id}/versions"), deadline
        )
        return codec.platform_versions(listed.body, resolved.secret, None)

    return _run(loader, PLATFORM, steps)


def resolve_platform_version(
    loader: ContextLoader, owner: str, slug: str, version_tag: str
) -> Observed[tuple[PlatformModel, PlatformVersion]]:
    """The one version of ``owner/slug`` that carries ``version_tag``: two GETs, nothing guessed."""
    owner, slug = catalog.require_address(owner, slug)
    version_tag = catalog.version_tag(version_tag)

    async def steps(
        transport: HttpTransport, resolved: ResolvedCredential, deadline: float
    ) -> tuple[PlatformModel, PlatformVersion]:
        detail = await _model_scoped(
            transport, _request(resolved, PLATFORM, f"models/{owner}/{slug}"), deadline
        )
        model = codec.platform_model(detail.body, resolved.secret)
        catalog.detail_identity(model.owner_username, model.slug, owner, slug)
        listed = await _model_scoped(
            transport,
            _request(resolved, PLATFORM, f"models/{catalog.segment(model.model_id)}/versions"),
            deadline,
        )
        versions = codec.platform_versions(listed.body, resolved.secret, model.versions_count)
        catalog.checked_versions(model.versions_count, len(versions.versions))
        return model, catalog.resolve_version(versions.versions, version_tag)

    return _run(loader, PLATFORM, steps)


def list_platform_datasets(
    loader: ContextLoader, page: int, page_size: int
) -> Observed[catalog.DatasetPage]:
    catalog.page_arguments(page, page_size)

    async def steps(
        transport: HttpTransport, resolved: ResolvedCredential, deadline: float
    ) -> catalog.DatasetPage:
        query = (*_page_query(page, page_size), ("scope", "owned"))
        got = await _get(transport, _request(resolved, PLATFORM, "datasets", query), deadline)
        return codec.platform_datasets(got.body, resolved.secret, page, page_size, got.headers)

    return _run(loader, PLATFORM, steps)


# --- LLM ----------------------------------------------------------------------------------------


def list_llm_models(loader: ContextLoader) -> Observed[LlmListing]:
    async def steps(
        transport: HttpTransport, resolved: ResolvedCredential, deadline: float
    ) -> LlmListing:
        got = await _get(transport, _request(resolved, LLM, "models"), deadline)
        return codec.llm_listing(got.body, resolved.secret)

    return _run(loader, LLM, steps)


def show_llm_model(loader: ContextLoader, model_id: str, *, task: str | None) -> Observed[LlmModel]:
    model_id = catalog.segment(model_id)

    async def steps(
        transport: HttpTransport, resolved: ResolvedCredential, deadline: float
    ) -> LlmModel:
        got = await _model_scoped(
            transport, _request(resolved, LLM, f"models/{model_id}"), deadline
        )
        model = codec.llm_model(got.body, resolved.secret)
        if task is not None:
            catalog.task_matches(task, model.task)
        return model

    return _run(loader, LLM, steps)
