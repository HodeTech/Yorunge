"""``models download``: arguments, the key, the session and the engine, composed (ADR-0032 §1).

The arguments are judged first, before any file, state or secret is touched. Then the local
credential snapshot is captured once (it binds the key to the store, like every Platform command)
and the engine is given a session that holds that key: the engine decides the local state before
any request, makes the one JSON call (with the key) that yields the signed address, and downloads
from that address with no credential at all. The snapshot is not confirmed after the download: a
file that was verified and published does not depend on what the store says a long time later.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from inspect import iscoroutinefunction
from pathlib import Path
from typing import Literal

from yorunge.adapters.capability_cache import SystemClock
from yorunge.adapters.command_arguments import absolute, judge_ground
from yorunge.adapters.context_state import StateDiscovery
from yorunge.adapters.download_engine import DownloadJob, Progress, run_download
from yorunge.adapters.secrets import EnvSecretReader
from yorunge.adapters.storage_transport import TransferSession
from yorunge.application.context_discovery import DiscoverySnapshot, ObservationClock
from yorunge.application.download_transport import DownloadTarget, DownloadTransport
from yorunge.application.http_transport import (
    HttpCredential,
    HttpRequest,
)
from yorunge.application.model_download import (
    parse_weights_answer,
    weights_endpoint,
    weights_query,
)
from yorunge.application.response_json import JSON_LIMIT
from yorunge.domain.dataset_upload import provider_uuid
from yorunge.domain.download import (
    DEFAULT_TIMEOUT_SECONDS,
    DownloadSource,
    DownloadSummary,
    identity_key,
    parse_fold,
    parse_sha256,
    parse_timeout,
)
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Context, Profile, Result, ServiceId

PLATFORM: ServiceId = "evren-platform"
CAPTURE_SECONDS = 30.0  # the local snapshot (store, key) has this much; the download its own time
ContextLoader = Callable[[], tuple[Context, Profile]]


class _Weights:
    """The JSON call of the engine: the signed address of one version's weights."""

    def __init__(
        self, credential: HttpCredential, version_id: str, fmt: str, fold: int | None
    ) -> None:
        self._credential, self._version = credential, version_id
        self._format, self._fold = fmt, fold

    async def __call__(self, transport: DownloadTransport, deadline: float) -> DownloadTarget:
        target = self._credential.target
        request = HttpRequest(
            target,
            "GET",
            weights_endpoint(self._version),
            query=weights_query(self._format, self._fold),
            service_id=PLATFORM,
            credential=self._credential,
            read_only=True,
            max_bytes=JSON_LIMIT,
        )
        data = bytearray()
        async with transport.open(request, deadline=deadline) as response:
            if response.status_code != 200:
                # Any other success (204, 206, ...) is not the answer this endpoint is documented
                # to give: no part of it is read.
                raise YorungeError("invalid_response")
            async for part in response.chunks():
                if len(data) + len(part) > JSON_LIMIT:
                    raise YorungeError("invalid_response")
                data.extend(part)
        return parse_weights_answer(
            bytes(data),
            secret=self._credential.secret,
            origin=target.service_origin,
            api_base_path=target.api_base_path,
        )


def download_model_weights(
    version_id: str,
    artifact_format: str,
    weights_out: Path,
    fold: int | None,
    sha256: str | None,
    timeout: int | None,
    no_resume: bool,
    loader: ContextLoader,
    state_dir: Path | None,
    progress: Progress | None,
) -> Result[DownloadSummary]:
    identifier = _identifier(version_id)
    fmt = _format(artifact_format)
    # The Python API takes the integers its signature names; the parsers also read the CLI's text.
    if any(value is not None and type(value) is not int for value in (fold, timeout)):
        raise YorungeError("invalid_request")
    chosen_fold = None if fold is None else parse_fold(fold)
    expected = None if sha256 is None else parse_sha256(sha256)
    seconds = DEFAULT_TIMEOUT_SECONDS if timeout is None else parse_timeout(timeout)
    if type(no_resume) is not bool or (
        progress is not None and (not callable(progress) or iscoroutinefunction(progress))
    ):
        raise YorungeError("invalid_request")
    judge_ground(state_dir)
    target = absolute(weights_out)
    started = time.monotonic()
    clock = ObservationClock(SystemClock())
    state = StateDiscovery(state_dir, loader, EnvSecretReader(), clock, service_id=PLATFORM)
    snapshot = _captured(state, started + CAPTURE_SECONDS)
    resolved = snapshot.credential
    key = HttpCredential("X-API-Key", resolved.secret, target=resolved.target, service_id=PLATFORM)
    origin, base = resolved.target.service_origin, resolved.target.api_base_path
    job = DownloadJob(
        target=target,
        source=DownloadSource(
            kind="model_version", version_id=identifier, format=fmt, fold=chosen_fold
        ),
        identity_key=identity_key(
            origin=origin,
            api_base_path=base,
            kind="model_version",
            resource_id=identifier,
            artifact_format=fmt,
            fold=chosen_fold,
        ),
        resolve=_Weights(key, identifier, fmt, chosen_fold),
        expected_sha256=expected,
        no_resume=no_resume,
        timeout=seconds,
        progress=progress,
    )
    session = TransferSession(key, storage_origins=(origin,))
    summary: DownloadSummary | None = None
    try:
        with session:
            summary = run_download(job, session)
    except Exception:
        # A failure of the session's own close, after the file was verified and published, does
        # not overwrite the result that was delivered (a rerun would only find the file there).
        if summary is None:
            raise
    return Result[DownloadSummary](data=summary)


def _captured(state: StateDiscovery, end: float) -> DiscoverySnapshot:
    """The local snapshot; a store that other commands hold for a moment is waited for.

    A fan-out of one command per fold (or per version) shares one state directory, and SQLite
    gives each of them about a second: the ones that lose that race have changed nothing yet, so
    they try again with a little jitter until the window of the capture is over.
    """
    while True:
        try:
            return state.capture(deadline=end)
        except YorungeError as error:
            remaining = end - time.monotonic()
            if error.code != "state_busy" or remaining <= 0.3:
                raise
            time.sleep(min(remaining - 0.2, 0.05 + 0.25 * random.random()))


def _format(value: object) -> Literal["onnx", "pt", "tflite"]:
    if value == "onnx" or value == "pt" or value == "tflite":
        return value
    raise YorungeError("invalid_request")


def _identifier(version_id: object) -> str:
    if type(version_id) is not str:
        raise YorungeError("invalid_request")
    try:
        return provider_uuid(version_id)
    except ValueError:
        raise YorungeError("invalid_request") from None


__all__ = ["DEFAULT_TIMEOUT_SECONDS", "download_model_weights"]
