"""What the first review of the engine found unpinned or open.

Each test fails on a changed engine: a check of the job taken out, the default deadline, the
deadline's reach into the local read, the exactness of the JSON call's refund, the live and exact
progress reports, an empty object and a fold in the summary, the durable mark that a body is whole
(before any report of the consumer's runs), the budget of the resolver and the arguments judged
before the local state is touched.
"""

import asyncio
import dataclasses
import json
import os
import signal
import time

import pytest

from tests.fixtures.http_server import Reply
from tests.integration.test_download_engine import (
    CUT,
    DATA,
    JSON_PATH,
    NAME,
    ORIGIN,
    PREFIX,
    SIGNED,
    TAG,
    assert_whole,
    code_of,
    cut_off,
    source,
)
from tests.integration.test_download_engine import (
    world as world,
)
from tests.integration.test_storage_transport import (
    certificates as certificates,
)
from tests.integration.test_storage_transport import (
    loopback_only as loopback_only,
)
from yorunge.adapters import download_sink
from yorunge.adapters.download_engine import DownloadJob, run_download
from yorunge.adapters.storage_transport import TransferHttpxTransport
from yorunge.application.download_transport import DownloadTarget
from yorunge.domain.download import MAX_DOWNLOAD_BYTES
from yorunge.domain.errors import YorungeError

# --- DownloadJob: each value is refused on its own (V1, V2, V3, V7, V8) --------------------------


@pytest.mark.parametrize(
    "changes",
    [
        {"target": "a-str-is-not-a-path"},  # V1: alone (the existing test breaks the key too)
        {"source": {"kind": "model_version"}},  # V2
        {"max_bytes": True},  # V7: a bool is not an int here
        {"max_bytes": 1.5},  # V7
        {"max_bytes": MAX_DOWNLOAD_BYTES + 1},  # V8: above the contract's own limit
    ],
    ids=["target-str", "source-dict", "max-bool", "max-float", "max-over-limit"],
)
def test_each_value_of_a_job_is_refused_on_its_own(world, changes):
    assert code_of(lambda: world.job(**changes)) == "invalid_request"
    assert world.server.requests == [] and world.names() == []


def test_a_job_is_frozen_and_its_defaults_are_the_contracts(world):
    job = world.job()
    with pytest.raises(dataclasses.FrozenInstanceError):  # V15
        job.timeout = 31  # type: ignore[misc]
    bare = DownloadJob(
        target=world.target,
        source=source(),
        identity_key=job.identity_key,
        resolve=job.resolve,
    )
    assert (bare.timeout, bare.max_bytes) == (900, MAX_DOWNLOAD_BYTES)  # V16, V17
    assert (bare.no_resume, bare.expected_sha256, bare.progress) == (False, None, None)


# --- the default deadline: job.timeout seconds from the start (R1, R1b, R1d) ---------------------


def test_without_a_caller_deadline_the_get_gets_the_jobs_timeout_from_now(world, monkeypatch):
    handed = []
    real = TransferHttpxTransport.open_download

    def spy(self, request, *, deadline):
        handed.append(deadline - time.monotonic())
        return real(self, request, deadline=deadline)

    monkeypatch.setattr(TransferHttpxTransport, "open_download", spy)
    summary = run_download(world.job(timeout=77), world.owned)  # no deadline= : the default
    assert_whole(world, summary)
    assert len(handed) == 1 and 74 <= handed[0] <= 77.5


# --- the JSON call's time is given back exactly (N4, N4b, N4c, N4d) ------------------------------


def test_the_get_deadline_is_the_callers_moved_on_by_exactly_the_json_calls_time(
    world, monkeypatch
):
    world.server.routes[JSON_PATH] = lambda record, count: Reply(
        body=json.dumps({"download_url": ORIGIN + SIGNED}).encode(), header_delay=1.0
    )
    handed = []
    real = TransferHttpxTransport.open_download

    def spy(self, request, *, deadline):
        handed.append(deadline)
        return real(self, request, deadline=deadline)

    monkeypatch.setattr(TransferHttpxTransport, "open_download", spy)
    given = time.monotonic() + 20
    assert_whole(world, run_download(world.job(), world.owned, deadline=given))
    assert 1.0 <= handed[0] - given <= 1.7  # the call took about a second, no more, no less


# --- the deadline reaches the local read of the held prefix (R5) ---------------------------------


def test_a_deadline_that_strikes_while_the_held_prefix_is_hashed_stops_the_read(world, monkeypatch):
    cut_off(world)  # CUT bytes: three blocks of at most 1 MiB
    reads = []
    real = os.read

    def slow(descriptor, count):
        if count > 4200:  # the blocks of the prefix, not the sidecar
            reads.append(count)
            time.sleep(0.2)
        return real(descriptor, count)

    with monkeypatch.context() as patch:
        patch.setattr(download_sink.os, "read", slow)
        requests = len(world.server.requests)
        assert code_of(lambda: world.run(seconds=0.25)) == "transport_timeout"
    assert len(reads) < 3  # the guard ended the hashing; reading the whole prefix is no answer
    assert len(world.server.requests) == requests  # and nothing was asked of the network
    assert world.names() == sorted([world.stage().name, world.sidecar().name])
    # untouched: the next call continues from what was held
    assert_whole(world, world.run(), resumed=True, resumed_from=CUT)


# --- progress: the first report is the start, and it is live (Q4, Q5) ----------------------------


def test_the_first_report_is_the_start_and_reports_follow_while_the_body_arrives(world):
    world.provider.script = [
        Reply(body=DATA, headers=(("ETag", TAG),), chunk_size=65536, chunk_delay=0.02)
    ]
    summary = world.run()
    assert_whole(world, summary)
    assert world.reports[0] == (0, len(DATA))  # Q4: before the first byte
    held = [pair[0] for pair in world.reports]
    assert len(held) >= 4 and held == sorted(set(held))  # Q5: live, strictly forward
    assert any(0 < value < len(DATA) for value in held)
    assert world.reports[-1] == (len(DATA), len(DATA))


def test_a_resumed_download_reports_held_bytes_from_the_prefix_on(world):
    cut_off(world)
    world.reports.clear()
    tail = Reply(
        status=206,
        body=DATA[CUT:],
        headers=(
            ("ETag", TAG),
            ("Content-Range", f"bytes {CUT}-{len(DATA) - 1}/{len(DATA)}"),
        ),
        chunk_size=65536,
        chunk_delay=0.02,
    )
    world.provider.script = [tail]
    assert_whole(world, world.run(), resumed=True, resumed_from=CUT)
    assert world.reports[0] == (CUT, len(DATA))  # Q4: the start is where the prefix ends
    assert len(world.reports) >= 3
    assert all(held >= CUT for held, _ in world.reports)  # Q7: held bytes, not bytes received
    assert all(total == len(DATA) for _, total in world.reports)


# --- the interrupt test must interrupt in the middle of the body --------------------------------


def test_an_interrupt_in_the_middle_of_the_body_is_continued_by_a_ranged_request(world):
    world.provider.script = [  # slow enough that reports are due while the body is still arriving
        Reply(body=DATA, headers=(("ETag", TAG),), chunk_size=65536, chunk_delay=0.01)
    ]
    fired = []

    def interrupt(held, total):
        if held >= 1024 * 1024 and not fired:
            fired.append(held)
            signal.raise_signal(signal.SIGINT)

    with pytest.raises(KeyboardInterrupt):
        world.run(progress=interrupt)
    kept = world.stage().stat().st_size
    assert 1024 * 1024 <= kept < len(DATA)  # Q5: it was the body that was interrupted, not its end
    assert_whole(world, world.run(), resumed=True, resumed_from=kept)
    assert world.provider.seen[-1] == (f"bytes={kept}-", TAG)  # and the next call asks for the rest


# --- F-1: a path the summary cannot hold is refused before the network, not after the publication -


def deep_directory(root, *, longer_than=4100):
    """A real directory chain whose absolute path is longer than the summary's 4096 limit."""
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    parts, total = [], len(str(root))
    try:
        while total <= longer_than:
            part = f"d{len(parts):03d}".ljust(250, "x")
            os.mkdir(part, 0o700, dir_fd=descriptor)
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            parts.append(part)
            total += 251
    finally:
        os.close(descriptor)
    return root.joinpath(*parts)


def test_a_target_the_summary_cannot_hold_is_refused_before_any_request(world):
    target = deep_directory(world.directory) / NAME  # legal for the filesystem, 4300+ characters
    with pytest.raises(YorungeError) as error:
        run_download(world.job(target=target), world.owned, deadline=time.monotonic() + 20)
    assert error.value.code == "download_target_invalid"
    assert world.server.requests == []  # the download did not happen only to fail at its summary


# --- an empty object, a fold, and the summary of a whole stage (S2, S7) --------------------------


def test_an_empty_object_is_published_and_a_whole_empty_stage_needs_no_request(world, monkeypatch):
    world.provider.data = b""
    from tests.integration.test_download_engine import broken_publication

    with monkeypatch.context() as patch:
        broken_publication(patch)
        assert (
            code_of(world.run) == "download_write_failed"
        )  # the stage is whole (0 bytes) and kept
    requests = len(world.server.requests)
    summary = world.run()
    assert (summary.bytes, summary.resumed, summary.resumed_from_bytes) == (0, True, 0)  # S2
    assert world.target.read_bytes() == b"" and world.names() == [NAME]
    assert len(world.server.requests) == requests  # no request at all


def test_the_summary_names_the_fold_of_what_was_downloaded(world):
    from tests.integration.test_download_engine import identity

    summary = world.run(source=source(fold=3), identity_key=identity(fold=3))
    assert summary.source == source(fold=3)  # S7


# --- the privacy scan must also look at the chunked and the resumed paths (LK3) ------------------


@pytest.mark.parametrize("path", ["chunked", "resumed"])
def test_a_successful_chunked_or_resumed_download_leaks_nothing_to_reports_or_logs(
    world, caplog, path
):
    from tests.integration.test_download_engine import PRIVATE, framed

    if path == "chunked":
        chunked = (("Transfer-Encoding", "chunked"), ("ETag", TAG))
        world.provider.script = [Reply(body=framed(DATA), headers=chunked)]
    else:
        cut_off(world)
    with caplog.at_level("DEBUG"):
        summary = world.run()
    assert summary.bytes == len(DATA)
    shown = repr(world.reports) + caplog.text
    for text in [*PRIVATE, "provider-name"]:
        assert text not in shown, text
    for name in world.names():  # nothing but the target is left, and it holds the object only
        assert name == NAME


# --- the body is whole the moment the framing ends: a report that raises costs nothing ------------


def _framings(world, framing):
    if framing == "length without a tag":
        world.provider.etag = None  # a body that is kept only once it is complete
    elif framing == "chunked":
        chunked = (("Transfer-Encoding", "chunked"), ("ETag", TAG))
        world.provider.script = [Reply(body=framed_body(world), headers=chunked)]


def framed_body(world):
    from tests.integration.test_download_engine import framed

    return framed(world.provider.data)


class Boom(Exception):
    pass


@pytest.mark.parametrize("framing", ["length with a tag", "length without a tag", "chunked"])
@pytest.mark.parametrize("raising", [Boom, BrokenPipeError, KeyboardInterrupt])
def test_a_report_that_raises_after_the_last_byte_keeps_a_whole_stage_and_the_next_call_publishes(
    world, framing, raising
):
    _framings(world, framing)

    def last_report_fails(held, total):
        if held == len(DATA):
            raise raising

    with pytest.raises(raising):
        world.run(progress=last_report_fails)
    assert world.names() == sorted([world.stage().name, world.sidecar().name])
    assert download_sink_partial(world).complete  # the whole body is recorded as whole
    requests = len(world.server.requests)
    summary = world.run()
    assert_whole(world, summary, resumed=True, resumed_from=len(DATA))
    assert len(world.server.requests) == requests  # offline: nothing is asked again


def download_sink_partial(world):
    from yorunge.domain.download import DownloadPartial

    return DownloadPartial.decode(world.sidecar().read_bytes())


# --- the deadline reaches the local state, a whole stage and a kept prefix included ---------------


@pytest.mark.parametrize("held", ["a prefix", "a whole stage"])
def test_a_deadline_already_gone_is_no_reason_to_touch_the_held_state_or_the_network(
    world, monkeypatch, held
):
    if held == "a prefix":
        cut_off(world)
    else:
        from tests.integration.test_download_engine import whole_stage

        whole_stage(world, monkeypatch)
    before, requests = world.names(), len(world.server.requests)
    size = world.stage().stat().st_size
    assert code_of(lambda: world.run(seconds=-1)) == "transport_timeout"
    assert world.names() == before and len(world.server.requests) == requests
    # untouched: the next call continues from, or publishes, what was held
    assert_whole(world, world.run(), resumed=True, resumed_from=size)


def test_reports_are_coalesced_to_the_first_and_the_last_when_the_interval_is_long(
    world, monkeypatch
):
    from yorunge.adapters import download_engine

    monkeypatch.setattr(download_engine, "PROGRESS_SECONDS", 3600.0)
    assert_whole(world, world.run())
    assert world.reports == [(0, len(DATA)), (len(DATA), len(DATA))]


def test_a_report_never_goes_backwards_and_never_repeats():
    from yorunge.adapters.download_engine import _Progress

    seen, now = [], [0.0]
    progress = _Progress(lambda held, total: seen.append(held), clock=lambda: now[0])
    for held, at in [(0, 0.0), (10, 1.0), (4, 2.0), (10, 3.0), (11, 4.0)]:
        now[0] = at
        progress.update(held, 100)
    progress.finish(11, 100)
    progress.finish(4, 100)
    assert seen == [0, 10, 11]


# --- the arguments and the session are judged before the local state is touched -------------------


@pytest.mark.parametrize(
    "deadline",
    [float("inf"), float("nan"), "soon", True, [1.0], 10**400],
    ids=["inf", "nan", "str", "bool", "list", "huge-int"],
)
def test_a_deadline_that_is_not_a_finite_number_is_refused_before_anything_is_touched(
    world, deadline
):
    cut_off(world)  # a held prefix that must survive the refusal
    before, requests = world.names(), len(world.server.requests)
    assert code_of(lambda: run_download(world.job(), world.owned, deadline=deadline)) == (
        "invalid_request"
    )
    assert world.names() == before and len(world.server.requests) == requests


def test_a_session_that_cannot_serve_the_call_is_refused_before_a_stale_partial_is_dropped(world):
    cut_off(world)  # a prefix of THIS download...
    from tests.integration.test_download_engine import identity

    other = identity(fold=9)  # ...and a call for another one, which would drop it

    async def inside():
        return run_download(world.job(identity_key=other), world.owned)

    before = world.names()
    with pytest.raises(YorungeError) as error:
        asyncio.run(inside())  # the loop of the call is running: no session serves it
    assert error.value.code == "invalid_request"
    assert world.names() == before  # the stale partial is still there
    assert code_of(lambda: run_download(world.job(), object())) == "invalid_request"  # type: ignore[arg-type]
    assert code_of(lambda: run_download(object(), world.owned)) == "invalid_request"  # type: ignore[arg-type]


# --- the resolver is held to its budget -----------------------------------------------------------


def test_a_resolver_that_never_answers_is_ended_at_its_budget_not_by_a_signal(world, monkeypatch):
    from yorunge.adapters import download_engine

    monkeypatch.setattr(download_engine, "JSON_BUDGET_SECONDS", 0.5)
    monkeypatch.setattr(download_engine, "RESOLVE_GRACE_SECONDS", 0.2)

    async def hangs(transport, deadline):
        await asyncio.sleep(30)

    began = time.monotonic()
    assert code_of(lambda: world.run(resolve=hangs)) == "transport_timeout"
    assert time.monotonic() - began < 3
    assert world.names() == [] and world.server.requests == []
    assert_whole(world, world.run())  # and the session serves the next call


def test_the_json_calls_refund_is_its_budget_at_most_whatever_the_resolver_took(world, monkeypatch):
    from yorunge.adapters import download_engine

    monkeypatch.setattr(download_engine, "JSON_BUDGET_SECONDS", 0.5)
    monkeypatch.setattr(download_engine, "RESOLVE_GRACE_SECONDS", 1.0)
    handed, real = [], TransferHttpxTransport.open_download

    def spy(self, request, *, deadline):
        handed.append(deadline)
        return real(self, request, deadline=deadline)

    monkeypatch.setattr(TransferHttpxTransport, "open_download", spy)

    async def slowly(transport, deadline):
        await asyncio.sleep(0.9)  # beyond its 0.5 s, within the grace: the call stands
        return DownloadTarget(ORIGIN + SIGNED, origin=ORIGIN, prefix=PREFIX)

    given = time.monotonic() + 20
    assert_whole(world, run_download(world.job(resolve=slowly), world.owned, deadline=given))
    assert 0.49 <= handed[0] - given <= 0.62  # moved on by the budget (0.5 s), not by 0.9 s


# --- a wrong expectation costs the held state, whatever state it was; another service's is dropped


def test_a_wrong_digest_after_a_resume_removes_the_stage_and_the_next_call_downloads_afresh(world):
    cut_off(world)
    wrong = "00" * 32
    with pytest.raises(YorungeError) as error:
        world.run(expected_sha256=wrong)
    assert error.value.code == "download_integrity_mismatch" and error.value.exit_code == 7
    assert world.names() == []  # no target, no stage, no sidecar: no offline loop of the mismatch
    matched = world.run(expected_sha256=sha_of_data())  # the right digest this time
    assert (matched.bytes, matched.verification_level) == (len(DATA), "sha256_matched")
    assert world.target.read_bytes() == DATA and world.names() == [NAME]
    assert world.provider.seen[-1] == (None, None)  # and it started from the first byte


def test_a_wrong_digest_of_a_whole_stage_is_found_without_the_network_and_removes_it(
    world, monkeypatch
):
    from tests.integration.test_download_engine import whole_stage

    whole_stage(world, monkeypatch)
    requests = len(world.server.requests)
    with pytest.raises(YorungeError) as error:
        world.run(expected_sha256="00" * 32)
    assert error.value.code == "download_integrity_mismatch"
    assert world.names() == [] and len(world.server.requests) == requests
    assert_whole(world, world.run())  # downloaded afresh


def test_a_partial_stage_of_another_service_is_dropped_and_the_download_starts_from_the_first_byte(
    world,
):
    from tests.integration.test_download_engine import identity

    cut_off(world)  # held: a prefix of this service's object
    other = identity(origin="https://other.localhost")
    summary = world.run(identity_key=other)
    assert_whole(world, summary)  # not resumed from a prefix that another service left
    assert world.provider.seen[-1] == (None, None)


def sha_of_data():
    from tests.integration.test_download_engine import sha

    return sha(DATA)
