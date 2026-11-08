"""One download, from the local state to the published file (ADR-0032).

The engine joins the three layers that were built apart. The local state decides first, before any
request (the JSON call included): a complete stage of this download is published without a
network. Otherwise the signed address is resolved (the consumer's one JSON call), at most TWO
GETs go to it (the first, conditional if a verified prefix is held; and, when the provider's answer
does not fit that request, exactly one without a range), the body is written as it arrives, the
expectation is compared and the file is published. A deadline or an interrupt stops the download
cleanly: what can be resumed is kept. The publication is local I/O and is not timed.

Time. One absolute download deadline starts with the run and covers the local state (the prefix is
re-hashed under it) and the GET. The JSON call has a control budget of its own, 30 seconds, which is
not taken from the download's: the deadline is moved on by what the call took. A deadline that is
reached after the body is whole is no failure: the transport stops timing a whole body, and the
checkpoint, the comparison and the publication that follow are exempt by the protocol.

The consumer (P02-3n) supplies what is its own: the target path, the identity of what is
downloaded, the resolution of the signed address, the key, the expectation and the progress sink.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from yorunge.adapters.download_sink import DownloadSink, Published, SinkPlan, open_sink
from yorunge.adapters.storage_transport import TransferSession
from yorunge.application.download_transport import (
    DownloadRequest,
    DownloadTarget,
    DownloadTransport,
    DownloadView,
)
from yorunge.domain.credentials import SecretValue
from yorunge.domain.download import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_DOWNLOAD_BYTES,
    DownloadSource,
    DownloadSummary,
    parse_sha256,
    parse_timeout,
)
from yorunge.domain.errors import YorungeError

JSON_BUDGET_SECONDS: Final = 30.0  # the control call that yields the signed address
PROGRESS_SECONDS: Final = 0.1  # at most ten reports a second (the first and the last always)

Resolver = Callable[[DownloadTransport, float], Awaitable[DownloadTarget]]
Progress = Callable[[int, int | None], None]


@dataclass(frozen=True, slots=True, repr=False)
class DownloadJob:
    """What one download is: where it goes, what it is, how its address is found, how it is checked.

    ``resolve`` makes the one JSON call that yields the signed address; it is given the open
    transport and the absolute deadline of the call (its 30-second budget), and is called once per
    run and only if the network is needed. ``identity_key`` is the stable key of what is downloaded
    (``domain.download.identity_key``): a stage left by another service, version, format or fold is
    never resumed or published. ``progress`` receives (bytes held, total or None) and never a name,
    path, address or tag. ``max_bytes`` is the most one answer's body may carry (the contract's
    limit unless a caller asks for less; with a resume ask keep it at the contract's).
    """

    target: Path
    source: DownloadSource
    identity_key: str
    resolve: Resolver = field(repr=False)
    secret: SecretValue = field(repr=False)
    expected_sha256: str | None = None
    no_resume: bool = False
    timeout: int = DEFAULT_TIMEOUT_SECONDS
    progress: Progress | None = field(default=None, repr=False)
    max_bytes: int = MAX_DOWNLOAD_BYTES

    def __post_init__(self) -> None:
        if (
            not isinstance(self.target, Path)
            or type(self.source) is not DownloadSource
            or type(self.secret) is not SecretValue
            or type(self.no_resume) is not bool
            or not callable(self.resolve)
            or (self.progress is not None and not callable(self.progress))
            or type(self.max_bytes) is not int
            or not 1 <= self.max_bytes <= MAX_DOWNLOAD_BYTES
        ):
            raise YorungeError("invalid_request")
        parse_timeout(self.timeout)
        parse_sha256(self.identity_key)
        if self.expected_sha256 is not None:
            parse_sha256(self.expected_sha256)

    def __repr__(self) -> str:
        return "<DownloadJob private>"


class _Limit:
    """The download deadline: absolute, started with the run, moved on by the JSON call's time."""

    def __init__(self, deadline: float) -> None:
        self.deadline = deadline

    def guard(self) -> None:
        if time.monotonic() >= self.deadline:
            raise YorungeError("transport_timeout")

    def refund(self, seconds: float) -> None:
        self.deadline += max(0.0, seconds)


class _Progress:
    """Reports at most ten a second, never backwards; the first and the last are always made."""

    def __init__(
        self, report: Progress | None, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._report, self._clock = report, clock
        self._last: float | None = None
        self._held = -1

    def update(self, held: int, total: int | None) -> None:
        """A report if one is due (the first is due at once)."""
        if self._report is None:
            return
        now = self._clock()
        if self._last is not None and now - self._last < PROGRESS_SECONDS:
            return
        self._emit(held, total, now)

    def finish(self, held: int, total: int | None) -> None:
        """The last report, whatever the clock says (unless nothing moved since the previous)."""
        if self._report is None or held == self._held:
            return
        self._emit(held, total, self._clock())

    def _emit(self, held: int, total: int | None, now: float) -> None:
        assert self._report is not None
        self._last, self._held = now, max(held, self._held)
        self._report(held, total)


def run_download(
    job: DownloadJob, session: TransferSession, *, deadline: float | None = None
) -> DownloadSummary:
    """Download ``job`` through the entered ``session``; the summary of the published file.

    ``deadline`` is the caller's own absolute deadline (``time.monotonic()`` instants, as every
    transport deadline); by default it is ``job.timeout`` seconds from now.
    """
    limit = _Limit(time.monotonic() + job.timeout if deadline is None else deadline)
    progress = _Progress(job.progress)
    with open_sink(
        job.target, identity_key=job.identity_key, no_resume=job.no_resume, guard=limit.guard
    ) as (sink, plan):
        if plan.action == "download":
            session.download(
                lambda transport: _network(job, plan, sink, transport, limit, progress)
            )
            sink.complete(terminated=True)  # the loop above ended at the framing's own end
        published = sink.publish(job.expected_sha256)
    return _summary(job, published, plan)


async def _network(
    job: DownloadJob,
    plan: SinkPlan,
    sink: DownloadSink,
    transport: DownloadTransport,
    limit: _Limit,
    progress: _Progress,
) -> None:
    limit.guard()  # a deadline already gone is no reason to ask for an address
    began = time.monotonic()
    address = await job.resolve(transport, began + JSON_BUDGET_SECONDS)
    limit.refund(time.monotonic() - began)  # the control call has its own budget
    ask = plan.ask
    # One conditional request if a verified prefix is held, and, if the answer does not fit it,
    # exactly one more without a range: there is no third.
    for _ in range(2):
        request = DownloadRequest(address, job.secret, ask, max_bytes=job.max_bytes)
        async with transport.open_download(request, deadline=limit.deadline) as view:
            if view.disposition != "discard_and_retry":
                await _receive(sink, view, progress)
                return
        sink.discard()  # the stage goes, then the sidecar, before the second request
        ask = None
    raise YorungeError("invalid_response")  # pragma: no cover (a plain request cannot be retried)


async def _receive(sink: DownloadSink, view: DownloadView, progress: _Progress) -> None:
    sink.begin(view.response, view.disposition)
    total = view.response.content_length if view.response.framing == "length" else None
    if view.disposition == "continue" and total is not None:
        total += sink.written  # the answer is the rest of the object; the total is all of it
    progress.update(sink.written, total)
    async for chunk in view.chunks():  # to its end: only the last read disarms the deadline
        sink.write(chunk)  # every byte received is written before the next await
        progress.update(sink.written, total)
    progress.finish(sink.written, total)


def _summary(job: DownloadJob, published: Published, plan: SinkPlan) -> DownloadSummary:
    verification = published.verification
    return DownloadSummary(
        schema_version=1,
        kind="download_summary",
        output_path=str(job.target),
        bytes=published.bytes,
        sha256=published.sha256,
        verification_level=verification.level,
        expectation_source=verification.expectation_source,
        resumed=published.resumed,
        resumed_from_bytes=published.resumed_from_bytes,
        source=job.source,
    )
