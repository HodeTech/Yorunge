"""Read-only catalog calls on the shared HTTP boundary (P02-4d, ADR-0035 Karar 1, 2, 5 and 10).

Each public function is one command: it resolves the selected profile's credential once, runs the
GET requests of that command on one session under one 30 s deadline, and hands the bytes and
headers to ``application.catalog`` together with the selected secret. Every catalog GET maps 422 to
``invalid_request``; a model-scoped GET also maps 404 to ``model_not_visible``. Every other status
keeps the transport's own closed code. The observation window starts at the first request and ends
when the last body is read. No state is opened or written.
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
class Captured:
    """What a caller already holds for one profile: the credential its local snapshot bound and the
    profile's name. A command that reads it again is not reading the same account."""

    credential: ResolvedCredential
    profile: str


Source = ContextLoader | Captured


@dataclass(frozen=True)
class Observed(Generic[T]):
    """What a command read, with the window it was read in (``observed_from`` to ``until``) and the
    profile whose account it was read with."""

    value: T
    observed_from: str
    observed_until: str
    profile: str


@dataclass(frozen=True)
class _Bytes:
    body: bytes
    headers: tuple[tuple[str, str], ...]


class _Window:
    """The first request's start and the last body's end; nothing before or after them."""

    def __init__(self, clock: SystemClock) -> None:
        self._clock = clock
        self.started: str | None = None
        self.finished: str | None = None

    def begin(self) -> None:
        if self.started is None:
            self.started = timestamp(self._clock.now())

    def end(self) -> None:
        self.finished = timestamp(self._clock.now())


@dataclass(frozen=True)
class _Call:
    """What one command's steps may use: the transport, the credential, the deadline, the window."""

    transport: HttpTransport
    resolved: ResolvedCredential
    deadline: float
    window: _Window


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


async def _get(call: _Call, request: HttpRequest) -> _Bytes:
    """One GET of a catalog command. A refused request (422) is an invalid request on every
    catalog endpoint; every other status is left to the transport's closed mapping."""
    data = bytearray()
    call.window.begin()
    try:
        async with call.transport.open(request, deadline=call.deadline) as response:
            if response.status_code != 200:  # a 2xx that is not 200 is not the answer asked for
                raise YorungeError("invalid_response")
            async for part in response.chunks():
                if len(data) + len(part) > JSON_LIMIT:
                    raise YorungeError("invalid_response")
                data.extend(part)
            call.window.end()  # the last body byte is read here; teardown is not observation
            headers = tuple((str(key), str(value)) for key, value in response.headers)
    except HttpStatusFailure as error:
        if error.status_code == 422:
            raise YorungeError("invalid_request") from None
        raise
    return _Bytes(bytes(data), headers)


async def _model_scoped(call: _Call, request: HttpRequest) -> _Bytes:
    """A model-scoped GET: 404 means the model is not visible to this key, not that it is absent."""
    try:
        return await _get(call, request)
    except HttpStatusFailure as error:
        if error.status_code == 404:
            raise YorungeError("model_not_visible") from None
        raise


def _run(
    source: Source,
    service_id: ServiceId,
    steps: Callable[[_Call], Awaitable[T]],
) -> Observed[T]:
    """One command: one credential, one session, one deadline, one window.

    A ``Captured`` source is used as it is, never read again, and only for the service it was bound
    to: a key of another service is refused before any request. A loader is read once, here.
    """
    if isinstance(source, Captured):
        if source.credential.reference.service_id != service_id:
            raise YorungeError("invalid_request")  # a programming fault: refused before a request
        resolved, name = source.credential, source.profile
    else:
        context, profile = source()
        resolved = resolve_credential(profile, service_id, EnvSecretReader())
        name = context.profile
    clock = SystemClock()
    window = _Window(clock)
    deadline = time.monotonic() + WINDOW_SECONDS

    async def exchange(transport: HttpTransport) -> T:
        return await steps(_Call(transport, resolved, deadline, window))

    with HttpSession() as session:
        value = session.call(exchange)
    started, finished = window.started, window.finished
    # A step only returns after its request read a body: the window has both ends by then. A
    # window without both ends is not an observation, and it is never shown as one.
    if started is None or finished is None:
        raise YorungeError("invalid_response")
    return Observed(value, started, finished, name)


def _page_query(page: int, page_size: int) -> tuple[tuple[str, str], ...]:
    return (("page", str(page)), ("page_size", str(page_size)))


# --- Platform -----------------------------------------------------------------------------------


def list_platform_models(
    loader: ContextLoader, page: int, page_size: int
) -> Observed[catalog.PlatformModelPage]:
    catalog.page_arguments(page, page_size)

    async def steps(call: _Call) -> catalog.PlatformModelPage:
        request = _request(call.resolved, PLATFORM, "models", _page_query(page, page_size))
        got = await _get(call, request)
        return codec.platform_models(got.body, call.resolved.secret, page, page_size)

    return _run(loader, PLATFORM, steps)


def show_platform_model(
    loader: ContextLoader, owner: str, slug: str, *, versions: bool
) -> Observed[tuple[PlatformModel, VersionListing | None]]:
    owner, slug = catalog.require_address(owner, slug)
    versions = catalog.flag_argument(versions)

    async def steps(call: _Call) -> tuple[PlatformModel, VersionListing | None]:
        detail = await _model_scoped(
            call, _request(call.resolved, PLATFORM, f"models/{owner}/{slug}")
        )
        model = codec.platform_model(detail.body, call.resolved.secret)
        catalog.owner_address(model.owner_username)  # no owner name: owner/slug cannot address it
        catalog.detail_identity(model.owner_username, model.slug, owner, slug)
        if not versions:
            return model, None
        listed = await _model_scoped(
            call,
            _request(
                call.resolved,
                PLATFORM,
                f"models/{catalog.provider_segment(model.model_id)}/versions",
            ),
        )
        return model, codec.platform_versions(
            listed.body, call.resolved.secret, model.versions_count
        )

    return _run(loader, PLATFORM, steps)


def list_platform_versions(loader: ContextLoader, model_id: str) -> Observed[VersionListing]:
    """The version list of a model addressed by its identifier (the owner-less route)."""
    model_id = catalog.segment(model_id)

    async def steps(call: _Call) -> VersionListing:
        listed = await _model_scoped(
            call, _request(call.resolved, PLATFORM, f"models/{model_id}/versions")
        )
        return codec.platform_versions(listed.body, call.resolved.secret, None)

    return _run(loader, PLATFORM, steps)


def resolve_platform_version(
    source: Source,
    owner: str,
    slug: str,
    version_tag: str,
) -> Observed[tuple[PlatformModel, PlatformVersion]]:
    """The one version of ``owner/slug`` that carries ``version_tag``: two GETs, nothing guessed."""
    owner, slug = catalog.require_address(owner, slug)
    version_tag = catalog.version_tag(version_tag)

    async def steps(call: _Call) -> tuple[PlatformModel, PlatformVersion]:
        detail = await _model_scoped(
            call, _request(call.resolved, PLATFORM, f"models/{owner}/{slug}")
        )
        model = codec.platform_model(detail.body, call.resolved.secret)
        catalog.owner_address(model.owner_username)  # no owner name: owner/slug cannot address it
        catalog.detail_identity(model.owner_username, model.slug, owner, slug)
        listed = await _model_scoped(
            call,
            _request(
                call.resolved,
                PLATFORM,
                f"models/{catalog.provider_segment(model.model_id)}/versions",
            ),
        )
        versions = codec.platform_versions(listed.body, call.resolved.secret, model.versions_count)
        catalog.checked_versions(model.versions_count, len(versions.versions))
        return model, catalog.resolve_version(versions.versions, version_tag)

    return _run(source, PLATFORM, steps)


def list_platform_datasets(
    loader: ContextLoader, page: int, page_size: int
) -> Observed[catalog.DatasetPage]:
    catalog.page_arguments(page, page_size)

    async def steps(call: _Call) -> catalog.DatasetPage:
        query = (*_page_query(page, page_size), ("scope", "owned"))
        got = await _get(call, _request(call.resolved, PLATFORM, "datasets", query))
        return codec.platform_datasets(got.body, call.resolved.secret, page, page_size, got.headers)

    return _run(loader, PLATFORM, steps)


# --- LLM ----------------------------------------------------------------------------------------


def list_llm_models(loader: ContextLoader) -> Observed[LlmListing]:
    async def steps(call: _Call) -> LlmListing:
        got = await _get(call, _request(call.resolved, LLM, "models"))
        return codec.llm_listing(got.body, call.resolved.secret)

    return _run(loader, LLM, steps)


def show_llm_model(loader: ContextLoader, model_id: str, *, task: str | None) -> Observed[LlmModel]:
    model_id = catalog.segment(model_id)
    if task is not None:
        task = catalog.task_argument(task)

    async def steps(call: _Call) -> LlmModel:
        got = await _model_scoped(call, _request(call.resolved, LLM, f"models/{model_id}"))
        model = codec.llm_model(got.body, call.resolved.secret)
        if model.model_id != model_id:
            raise YorungeError("invalid_response")  # another model than the one asked for
        if task is not None:
            catalog.task_matches(task, model.task)
        return model

    return _run(loader, LLM, steps)
