"""The download engine over real loopback TLS: the protocol matrix, row by row.

The three layers it joins are tested apart (the pure contract, the signed GET, the local writer);
these tests drive them together against a scriptable object server, and for each row check what the
engine leaves on disk, what it sent over the wire, how many requests it made and what it reports.
Every success is compared with an independent ``hashlib`` oracle of the bytes the server holds.
"""

import errno
import hashlib
import json
import os
import random
import signal
import time
import traceback

import pytest

from tests.fixtures.http_server import Reply, TlsServer
from tests.integration.test_download_transport import (
    ORIGIN,
    PATH,
    PREFIX,
    QUERY,
    TAG,
)
from tests.integration.test_storage_transport import (
    API,
    credential,
    session,
)
from tests.integration.test_storage_transport import (
    certificates as certificates,
)
from tests.integration.test_storage_transport import (
    loopback_only as loopback_only,
)
from yorunge.adapters import download_sink
from yorunge.adapters.download_engine import (
    JSON_BUDGET_SECONDS,
    DownloadJob,
    _Limit,
    _Progress,
    run_download,
)
from yorunge.adapters.download_sink import DownloadSink
from yorunge.application.download_transport import DownloadTarget
from yorunge.application.http_transport import HttpRequest
from yorunge.domain.download import DownloadPartial, DownloadSource, download_names, identity_key
from yorunge.domain.errors import YorungeError

VERSION = "00000000-0000-4000-8000-000000000123"
JSON_PATH = f"/v1/models/versions/{VERSION}/download?format=onnx"
SIGNED = PATH + QUERY
NAME = "weights.onnx"
DATA = random.Random(20261108).randbytes(3 * 1024 * 1024 + 123)  # 3 MiB and a ragged end
OTHER = random.Random(7).randbytes(len(DATA))  # the same size, other bytes
SECONDS = 20


def sha(data):
    return hashlib.sha256(data).hexdigest()


def framed(data, size=8192):
    """The body of a chunked answer, hand framed."""
    pieces = [data[offset : offset + size] for offset in range(0, len(data), size)]
    return b"".join(b"%x\r\n" % len(piece) + piece + b"\r\n" for piece in pieces) + b"0\r\n\r\n"


class Provider:
    """An object server that honours Range and If-Range like a real one unless it is told not to.

    ``script`` holds one entry per signed GET, in order: a ``Reply`` (or a function of the request)
    overrides the honest answer for that request, ``None`` leaves it honest.
    """

    def __init__(self, data=DATA, etag=TAG):
        self.data, self.etag = data, etag
        self.honor_range = True
        self.script = []
        self.seen = []  # (Range, If-Range) of every signed GET, in order

    def headers(self):
        return (("ETag", self.etag),) if self.etag else ()

    def whole(self):
        return Reply(body=self.data, headers=self.headers())

    def __call__(self, record, count):
        self.seen.append((record.header("Range"), record.header("If-Range")))
        if self.script:
            override = self.script.pop(0)
            if override is not None:
                return override(record) if callable(override) else override
        wanted = record.header("Range")
        if wanted and self.honor_range:
            start = int(wanted.removeprefix("bytes=").rstrip("-"))
            condition = record.header("If-Range")
            if condition is not None and condition != self.etag:
                return self.whole()  # the object is not the one the prefix came from
            if start >= len(self.data):
                return Reply(status=416, body=b"", headers=(("Content-Range", "bytes */9"),))
            return Reply(
                status=206,
                body=self.data[start:],
                headers=(
                    *self.headers(),
                    ("Content-Range", f"bytes {start}-{len(self.data) - 1}/{len(self.data)}"),
                ),
            )
        return self.whole()


def json_route(count=None):
    body = json.dumps({"download_url": ORIGIN + SIGNED, "filename": "provider-name.onnx"}).encode()
    return Reply(body=body)


def server(certificates, provider, **extra):
    routes = {SIGNED: provider, JSON_PATH: lambda record, count: json_route(), **extra}
    return TlsServer(certificates, routes)


class Resolver:
    """The consumer's one JSON call: a real GET of the platform's route, counted."""

    def __init__(self, key):
        self.key, self.calls, self.deadlines = key, 0, []

    async def __call__(self, transport, deadline):
        self.calls += 1
        self.deadlines.append(deadline)
        request = HttpRequest(
            API,
            "GET",
            f"models/versions/{VERSION}/download",
            query=(("format", "onnx"),),
            credential=self.key,
            read_only=True,
            service_id="evren-platform",
        )
        async with transport.open(request, deadline=deadline) as response:
            body = b"".join([part async for part in response.chunks()])
        return DownloadTarget(json.loads(body)["download_url"], origin=ORIGIN, prefix=PREFIX)


def source(fold=None):
    return DownloadSource(kind="model_version", version_id=VERSION, format="onnx", fold=fold)


def identity(origin=ORIGIN, fold=None):
    return identity_key(
        origin=origin,
        api_base_path="/v1",
        kind="model_version",
        resource_id=VERSION,
        artifact_format="onnx",
        fold=fold,
    )


class World:
    """A directory, a key, a provider behind a TLS server and the engine's session on it."""

    def __init__(self, certificates, directory, provider=None, **extra):
        self.directory = directory
        self.provider = provider or Provider()
        self.key = credential()
        self.server = server(certificates, self.provider, **extra)
        self.resolver = Resolver(self.key)
        self.reports = []
        self.certificates = certificates

    def __enter__(self):
        self.server.__enter__()
        self.owned, self.network, self.instances = session(
            self.key, self.certificates, {"api.localhost": self.server}, origins=(ORIGIN,)
        )
        self.owned.__enter__()
        return self

    def __exit__(self, *exc):
        self.owned.__exit__(*exc)
        self.server.__exit__(*exc)

    @property
    def target(self):
        return self.directory / NAME

    def job(self, **changes):
        values = {
            "target": self.target,
            "source": source(),
            "identity_key": identity(),
            "resolve": self.resolver,
            "progress": lambda held, total: self.reports.append((held, total)),
        }
        return DownloadJob(**{**values, **changes})

    def run(self, seconds=SECONDS, **changes):
        return run_download(self.job(**changes), self.owned, deadline=time.monotonic() + seconds)

    def signed(self):
        return [r for r in self.server.requests if r.path == SIGNED]

    def service_calls(self):
        return [r for r in self.server.requests if r.path == JSON_PATH]

    def names(self):
        return sorted(p.name for p in self.directory.iterdir())

    def stage(self):
        return self.directory / download_names(NAME).stage

    def sidecar(self):
        return self.directory / download_names(NAME).sidecar


@pytest.fixture
def world(certificates, tmp_path):
    with World(certificates, tmp_path) as held:
        yield held


def code_of(action):
    with pytest.raises(YorungeError) as error:
        action()
    return error.value.code


def assert_whole(world, summary, data=DATA, *, resumed=False, resumed_from=0):
    """What every success shares: the oracle's bytes, a clean directory and a truthful summary."""
    assert world.target.read_bytes() == data
    assert world.names() == [NAME]  # no stage, no sidecar, no lock object, nothing
    assert (summary.bytes, summary.sha256) == (len(data), sha(data))
    assert (summary.resumed, summary.resumed_from_bytes) == (resumed, resumed_from)
    assert summary.verification_level == "transfer_complete"
    assert summary.output_path == str(world.target)
    assert summary.source == source()
    assert oct(world.target.stat().st_mode & 0o777) == "0o600"


# --- a whole download -----------------------------------------------------------------------------


def test_a_whole_download_is_published_with_one_json_call_and_one_get(world):
    summary = world.run()
    assert_whole(world, summary)
    assert world.resolver.calls == 1
    assert len(world.service_calls()) == 1
    assert world.provider.seen == [(None, None)]  # a plain request: nothing but the address


def test_the_json_call_has_its_own_budget_of_thirty_seconds(world):
    before = time.monotonic()
    world.run(timeout=3600)
    (deadline,) = world.resolver.deadlines
    assert before + JSON_BUDGET_SECONDS <= deadline <= time.monotonic() + JSON_BUDGET_SECONDS


def test_progress_ends_at_the_whole_and_never_goes_back(world):
    summary = world.run()
    held = [pair[0] for pair in world.reports]
    assert held == sorted(held)
    assert world.reports[-1] == (len(DATA), len(DATA))
    assert world.reports[0][1] == len(DATA)
    assert summary.bytes == len(DATA)
    assert len(world.reports) < 200  # bounded: not one report per chunk of a 3 MiB body


# --- a cut download and what the next call does with it -------------------------------------------

CUT = 2 * 1024 * 1024 + 4321


def cut_off(world, at=CUT):
    """The first call dies mid-body: the server promises it all and stops after ``at`` bytes."""
    reply = Reply(body=world.provider.data, headers=world.provider.headers(), truncate_at=at)
    world.provider.script = [reply]
    assert code_of(world.run) == "download_incomplete"
    assert world.target.exists() is False


def test_a_cut_download_is_continued_by_the_next_call_from_what_was_kept(world):
    cut_off(world)
    assert world.names() == sorted([world.stage().name, world.sidecar().name])
    assert world.stage().stat().st_size == CUT  # every byte received was written
    summary = world.run()
    assert_whole(world, summary, resumed=True, resumed_from=CUT)
    assert world.provider.seen == [(None, None), (f"bytes={CUT}-", TAG)]  # one GET each
    assert world.reports[-1] == (len(DATA), len(DATA))  # the total is the whole object's
    assert len(world.signed()) == 2
    assert len(world.service_calls()) == 2


def test_the_kept_prefix_is_hashed_again_and_a_flipped_byte_starts_over(world):
    cut_off(world)
    with world.stage().open("r+b") as stage:
        stage.seek(1234)
        stage.write(b"\xff")  # local corruption inside the committed prefix
    summary = world.run()
    assert_whole(world, summary)  # no trust in the prefix: a plain request, from the start
    assert world.provider.seen[-1] == (None, None)


def test_an_object_that_changed_is_downloaded_from_the_start(world):
    cut_off(world)
    world.provider.data, world.provider.etag = OTHER, '"v2-other"'
    summary = world.run()
    assert_whole(world, summary, OTHER)  # If-Range did not match: the whole object, new tag
    assert world.provider.seen[-1] == (f"bytes={CUT}-", TAG)
    assert len(world.signed()) == 2


def test_a_provider_that_ignores_the_range_is_restarted_without_another_request(world):
    cut_off(world)
    world.provider.honor_range = False
    summary = world.run()
    assert_whole(world, summary)
    assert world.provider.seen[1:] == [(f"bytes={CUT}-", TAG)]  # asked once, answered in full


def unfit_partial(world, **changes):
    """A 206 that is not the exact continuation that was asked for."""
    fields = {
        "start": CUT,
        "last": len(DATA) - 1,
        "total": len(DATA),
        "etag": TAG,
        "length": len(DATA) - CUT,
    }
    fields.update(changes)
    headers = (
        ("Content-Range", f"bytes {fields['start']}-{fields['last']}/{fields['total']}"),
        ("Content-Length", str(fields["length"])),
    )
    if fields["etag"]:
        headers += (("ETag", fields["etag"]),)
    start = fields["start"]
    return Reply(status=206, body=DATA[start : start + fields["length"]], headers=headers)


@pytest.mark.parametrize(
    "changes",
    [
        {"start": CUT + 1, "length": len(DATA) - CUT - 1},  # another start
        {"etag": '"other"'},  # another tag
        {"etag": None},  # no tag
        {"total": len(DATA) + 1},  # the object grew
        {"total": len(DATA) - 1},
        {"last": len(DATA) - 2},
        {"length": len(DATA) - CUT - 1},  # only the length is wrong: one byte short of the range
        {"length": 0},  # and short by the whole tail
    ],
    ids=["start", "tag", "no tag", "grew", "shrank", "end", "length-1", "length-0"],
)
def test_a_partial_answer_that_does_not_fit_drops_the_prefix_and_asks_once_without_a_range(
    world, changes
):
    cut_off(world)
    world.provider.script = [Reply(**{**vars(unfit_partial(world, **changes))})]
    summary = world.run()
    assert_whole(world, summary)
    assert world.provider.seen[1:] == [(f"bytes={CUT}-", TAG), (None, None)]  # two GETs, no third


def test_a_range_that_cannot_be_satisfied_drops_the_prefix_and_asks_once_without_a_range(world):
    cut_off(world)
    world.provider.script = [Reply(status=416, body=b"", headers=(("Content-Range", "bytes */9"),))]
    summary = world.run()
    assert_whole(world, summary)
    assert world.provider.seen[1:] == [(f"bytes={CUT}-", TAG), (None, None)]


def test_the_one_protocol_turn_is_not_a_loop(world):
    cut_off(world)
    world.provider.script = [unfit_partial(world, etag='"other"'), unfit_partial(world, start=1)]
    assert code_of(world.run) == "invalid_response"  # a partial answer to a plain request
    assert len(world.provider.seen) == 3  # the cut run, the ranged request, the one plain request
    assert world.names() == []  # and nothing of the dropped prefix is left


def test_a_partial_answer_to_a_plain_request_is_refused_and_nothing_is_kept(world):
    world.provider.script = [unfit_partial(world, start=10, length=len(DATA) - 10)]
    assert code_of(world.run) == "invalid_response"
    assert world.names() == []
    assert len(world.provider.seen) == 1


def test_a_full_answer_that_carries_a_content_range_is_never_written_as_the_whole(world):
    cut_off(world)
    mislabelled = Reply(
        status=200,
        body=DATA[CUT:],
        headers=(("ETag", TAG), ("Content-Range", f"bytes {CUT}-{len(DATA) - 1}/{len(DATA)}")),
    )
    world.provider.script = [mislabelled]
    summary = world.run()
    assert_whole(world, summary)  # the tail was dropped; the plain request brought the whole
    assert world.provider.seen[1:] == [(f"bytes={CUT}-", TAG), (None, None)]


def test_a_full_answer_of_exactly_the_tail_is_never_written_as_the_whole(world):
    cut_off(world)
    tail = Reply(status=200, body=DATA[CUT:], headers=(("ETag", TAG),))  # the tail, called 200
    world.provider.script = [tail]
    summary = world.run()
    assert_whole(world, summary)
    assert world.provider.seen[1:] == [(f"bytes={CUT}-", TAG), (None, None)]


def test_without_a_strong_tag_a_cut_download_keeps_nothing(world):
    world.provider.etag = None
    world.provider.script = [Reply(body=DATA, truncate_at=CUT)]
    assert code_of(world.run) == "download_incomplete"
    assert world.names() == []  # nothing to resume against: not kept
    assert len(world.signed()) == 1
    assert len(world.service_calls()) == 1
    assert_whole(world, world.run())
    assert world.provider.seen[-1] == (None, None)
    assert len(world.signed()) == 2
    assert len(world.service_calls()) == 2  # one GET per run


def test_a_weak_tag_is_no_tag(world):
    world.provider.etag = 'W/"weak"'
    world.provider.script = [Reply(body=DATA, headers=(("ETag", 'W/"weak"'),), truncate_at=CUT)]
    assert code_of(world.run) == "download_incomplete"
    assert world.names() == []
    assert len(world.signed()) == 1
    assert len(world.service_calls()) == 1


def test_a_chunked_answer_is_whole_when_terminated_and_is_not_resumed_when_cut(world):
    chunked = (("Transfer-Encoding", "chunked"), ("ETag", TAG))
    body = framed(DATA)
    world.provider.script = [Reply(body=body, headers=chunked, truncate_at=len(body) // 2)]
    assert code_of(world.run) == "download_incomplete"
    assert world.names() == []  # no total until it ends: not resumable
    assert len(world.signed()) == 1
    assert len(world.service_calls()) == 1
    world.provider.script = [Reply(body=body, headers=chunked)]
    summary = world.run()
    assert_whole(world, summary)
    assert len(world.signed()) == 2
    assert len(world.service_calls()) == 2  # no ranged request
    assert world.provider.seen == [(None, None), (None, None)]
    assert world.reports[-1][1] is None or world.reports[-1] == (len(DATA), len(DATA))
    assert all(total is None for _, total in world.reports[-3:])  # chunked: no total to report


def test_a_body_delimited_by_the_connection_is_refused(world):
    world.provider.script = [Reply(body=DATA, omit_length=True)]
    assert code_of(world.run) == "invalid_response"
    assert world.names() == []
    assert len(world.signed()) == 1
    assert len(world.service_calls()) == 1  # no second try


def test_a_body_longer_than_the_callers_cap_is_refused_before_a_byte_is_written(world):
    assert code_of(lambda: world.run(max_bytes=len(DATA) - 1)) == "download_limit_exceeded"
    assert world.names() == []
    assert len(world.provider.seen) == 1


def test_a_chunked_body_past_the_callers_cap_is_cut_and_not_kept(world):
    chunked = (("Transfer-Encoding", "chunked"), ("ETag", TAG))
    world.provider.script = [Reply(body=framed(DATA), headers=chunked)]
    assert code_of(lambda: world.run(max_bytes=len(DATA) // 2)) == "download_limit_exceeded"
    assert world.names() == []
    assert len(world.signed()) == 1
    assert len(world.service_calls()) == 1


# --- what the directory says before anything is asked of the network ------------------------------


def test_a_target_that_exists_is_refused_before_any_request(world):
    world.target.write_bytes(b"mine")
    assert code_of(world.run) == "download_output_exists"
    assert world.server.requests == []
    assert world.resolver.calls == 0  # the JSON call included
    assert world.target.read_bytes() == b"mine"
    assert world.names() == [NAME]


def test_a_parent_that_is_missing_is_a_target_error_before_any_request(world):
    code = code_of(lambda: world.run(target=world.directory / "missing" / NAME))
    assert code == "download_target_invalid"
    assert world.server.requests == []


@pytest.mark.parametrize("name", ["new\nline.bin", "undecodable-\udcff.bin"])
def test_a_target_the_summary_could_not_report_is_refused_before_any_request(world, name):
    code = code_of(lambda: world.run(target=world.directory / name))
    assert code == "download_target_invalid"
    assert world.server.requests == []
    assert world.resolver.calls == 0
    assert world.names() == []


@pytest.mark.parametrize("parent", ["bidi\u202eevil", "new\nline", "tab\there", "bell\x07"])
def test_a_parent_the_summary_could_not_report_is_refused_before_any_request(world, parent):
    directory = world.directory / parent
    directory.mkdir()
    code = code_of(lambda: world.run(target=directory / NAME))
    assert code == "download_target_invalid"
    assert world.server.requests == []
    assert world.resolver.calls == 0
    assert list(directory.iterdir()) == []  # nothing was made there


def broken_publication(patch):
    def broken(descriptor):
        raise OSError(errno.EIO, "PRIVATE")

    patch.setattr(download_sink, "full_sync", broken)


def whole_stage(world, monkeypatch, **changes):
    """A download whose publication fails at the very end: the stage is whole and is kept."""
    with monkeypatch.context() as patch:
        broken_publication(patch)
        assert code_of(lambda: world.run(**changes)) == "download_write_failed"
    assert world.names() == sorted([world.stage().name, world.sidecar().name])
    record = DownloadPartial.decode(world.sidecar().read_bytes())
    assert record.complete
    assert record.committed_bytes == len(record_data(world))


def record_data(world):
    return world.provider.data


def test_a_whole_stage_is_published_by_the_next_call_without_any_request(world, monkeypatch):
    whole_stage(world, monkeypatch)
    requests, calls = len(world.server.requests), world.resolver.calls
    summary = world.run()
    assert_whole(world, summary, resumed=True, resumed_from=len(DATA))
    assert len(world.server.requests) == requests
    assert world.resolver.calls == calls


def test_a_whole_chunked_stage_is_published_without_any_request_too(world, monkeypatch):
    chunked = (("Transfer-Encoding", "chunked"),)  # no tag, no total: whole only at its end
    world.provider.script = [Reply(body=framed(DATA), headers=chunked)]
    with monkeypatch.context() as patch:
        broken_publication(patch)
        assert code_of(world.run) == "download_write_failed"
    assert DownloadPartial.decode(world.sidecar().read_bytes()).total_size == len(DATA)
    requests = len(world.server.requests)
    summary = world.run()
    assert_whole(world, summary, resumed=True, resumed_from=len(DATA))
    assert len(world.server.requests) == requests


def test_a_revoked_key_does_not_stand_in_the_way_of_a_whole_stage(world, monkeypatch):
    whole_stage(world, monkeypatch)
    world.provider.script = [Reply(status=401, body=b"")] * 3
    json_calls = world.service_calls()
    summary = world.run()
    assert_whole(world, summary, resumed=True, resumed_from=len(DATA))
    assert world.service_calls() == json_calls
    assert world.provider.script == [Reply(status=401, body=b"")] * 3


def test_a_stage_left_by_another_service_is_neither_resumed_nor_published(world, monkeypatch):
    other = identity(origin="https://other.localhost")  # same version, format and name
    whole_stage(world, monkeypatch, identity_key=other)
    world.provider.data, world.provider.etag = OTHER, '"v2-other"'
    summary = world.run()
    assert_whole(world, summary, OTHER)  # the whole stage was not ours: dropped, downloaded afresh
    assert world.provider.seen[-1] == (None, None)


@pytest.mark.parametrize(
    "kind",
    ["origin", "fold"],
)
def test_a_partial_download_of_another_service_or_fold_is_dropped_and_started_over(world, kind):
    other = identity(origin="https://other.localhost") if kind == "origin" else identity(fold=3)
    world.provider.script = [Reply(body=DATA, headers=world.provider.headers(), truncate_at=CUT)]
    assert code_of(lambda: world.run(identity_key=other)) == "download_incomplete"
    assert world.stage().stat().st_size == CUT  # kept, under the other identity
    summary = world.run()
    assert_whole(world, summary)  # same version, format and name: not this download's stage
    assert world.provider.seen[-1] == (None, None)
    assert summary.resumed is False


def test_a_wrong_expected_digest_leaves_nothing_and_the_rerun_downloads_again(world):
    with pytest.raises(YorungeError) as error:
        world.run(expected_sha256="00" * 32)
    assert error.value.code == "download_integrity_mismatch"
    assert error.value.exit_code == 7
    assert error.value.details == {"computed_sha256": sha(DATA), "bytes": len(DATA)}
    assert world.names() == []
    assert len(world.signed()) == 1
    summary = world.run(expected_sha256=sha(DATA))  # no offline loop of the same mismatch
    assert (summary.verification_level, summary.expectation_source) == (
        "sha256_matched",
        "user_supplied",
    )
    assert world.target.read_bytes() == DATA
    assert len(world.signed()) == 2


def test_no_resume_removes_a_partial_that_is_ours_and_downloads_from_the_start(world):
    cut_off(world)
    summary = world.run(no_resume=True)
    assert_whole(world, summary)
    assert world.provider.seen[-1] == (None, None)


@pytest.mark.parametrize("no_resume", [False, True])
def test_a_partial_that_cannot_be_proved_ours_is_never_touched(world, no_resume):
    cut_off(world)
    world.stage().chmod(0o644)  # not the private file this download makes
    requests = len(world.server.requests)
    assert code_of(lambda: world.run(no_resume=no_resume)) == "download_partial_unverified"
    assert world.stage().stat().st_size == CUT
    assert world.sidecar().exists()
    assert len(world.server.requests) == requests


# --- time -----------------------------------------------------------------------------------------


def test_publishing_is_not_timed_by_the_download_deadline(world, monkeypatch):
    # The body is whole and the deadline passes before the checkpoint, the comparison and the
    # link: local I/O is exempt by the protocol, and the file is published.
    deadline = time.monotonic() + 3
    complete = DownloadSink.complete

    def late(sink, **options):
        time.sleep(max(0.0, deadline - time.monotonic()) + 0.3)
        complete(sink, **options)

    monkeypatch.setattr(DownloadSink, "complete", late)
    summary = run_download(world.job(), world.owned, deadline=deadline)
    assert time.monotonic() > deadline
    assert_whole(world, summary)


def test_a_deadline_already_gone_is_a_timeout_before_any_request(world):
    assert code_of(lambda: world.run(seconds=-1)) == "transport_timeout"
    assert world.server.requests == []
    assert world.names() == []


def test_a_stalled_body_ends_at_the_deadline_and_keeps_what_it_can(world):
    # The server sends a prefix and then says nothing: the caller's deadline ends the wait.
    stall = Reply(body=DATA, headers=(("ETag", TAG),), after_first_chunk=lambda: time.sleep(5))
    world.provider.script = [stall]
    started = time.monotonic()
    assert code_of(lambda: world.run(seconds=1.5)) == "transport_timeout"  # not download_incomplete
    assert time.monotonic() - started < 4
    # What arrived is kept, and the next call asks for the rest.
    assert world.names() == sorted([world.stage().name, world.sidecar().name])
    assert 0 < world.stage().stat().st_size <= CUT
    kept = world.stage().stat().st_size
    assert_whole(world, world.run(), resumed=True, resumed_from=kept)
    assert world.provider.seen[-1] == (f"bytes={kept}-", TAG)


def test_the_json_call_is_not_charged_to_the_download_deadline(world):
    # A deadline of 2.5 s, a control call that takes 1.2 s and a body that takes about as long:
    # the whole is over 2.5 s, and still within the deadline moved on by the call's own time.
    world.server.routes[JSON_PATH] = lambda record, count: Reply(
        body=json.dumps({"download_url": ORIGIN + SIGNED}).encode(), header_delay=1.2
    )
    world.provider.script = [
        Reply(body=DATA, headers=(("ETag", TAG),), chunk_size=65536, chunk_delay=0.03)
    ]
    started = time.monotonic()
    summary = world.run(seconds=2.5)
    assert time.monotonic() - started > 2.5
    assert_whole(world, summary)


# --- cancellation and errors ----------------------------------------------------------------------


def test_an_interrupt_keeps_what_can_be_resumed_and_the_next_call_continues(world):
    # Paced, so that the interrupt always lands in the middle of the body: on a fast or idle
    # machine the whole body could be written before the first progress report.
    world.provider.script = [
        Reply(body=DATA, headers=(("ETag", TAG),), chunk_size=65536, chunk_delay=0.02)
    ]
    fired = []

    def interrupt(held, total):
        if held >= 1024 * 1024 and not fired:
            fired.append(held)
            signal.raise_signal(signal.SIGINT)

    with pytest.raises(KeyboardInterrupt):
        world.run(progress=interrupt)
    assert world.names() == sorted([world.stage().name, world.sidecar().name])
    kept = world.stage().stat().st_size
    assert kept >= 1024 * 1024
    assert len(world.signed()) == 1
    assert len(world.service_calls()) == 1
    summary = world.run()
    assert_whole(world, summary, resumed=True, resumed_from=kept)
    assert len(world.signed()) == 2
    assert len(world.service_calls()) == 2
    assert world.provider.seen[-1] == (f"bytes={kept}-", TAG)


def test_a_local_write_failure_is_reported_before_a_remote_one(world, monkeypatch):
    real, calls = os.write, []

    def failing(descriptor, data):
        calls.append(1)
        if len(calls) == 20:
            raise OSError(errno.ENOSPC, "PRIVATE")
        return real(descriptor, data)

    world.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),), truncate_at=CUT)]
    with monkeypatch.context() as patch:
        patch.setattr(download_sink.os, "write", failing)
        # the disk fails first; the cut that would be reported next never gets the chance
        assert code_of(world.run) == "download_write_failed"
    assert world.target.exists() is False
    assert len(world.signed()) == 1
    assert len(world.service_calls()) == 1  # no retry after a disk fault


def test_a_bad_digest_is_refused_before_the_job_exists():
    source_value = source()
    resolver = Resolver(credential())
    with pytest.raises(YorungeError) as error:
        DownloadJob(
            target=None,  # type: ignore[arg-type]
            source=source_value,
            identity_key="x",
            resolve=resolver,
        )
    assert error.value.code == "invalid_request"


@pytest.mark.parametrize(
    "changes",
    [
        {"identity_key": "not-a-digest"},
        {"identity_key": "AB" * 32},
        {"expected_sha256": "AB" * 32},
        {"expected_sha256": "ab"},
        {"timeout": 29},
        {"timeout": 3601},
        {"timeout": True},
        {"no_resume": 1},
        {"max_bytes": 0},
        {"progress": 5},
        {"resolve": None},
    ],
)
def test_a_job_with_a_value_outside_its_contract_is_refused(world, changes):
    assert code_of(lambda: world.job(**changes)) == "invalid_request"
    assert world.server.requests == []
    assert world.names() == []


def test_a_job_shows_nothing_of_what_it_holds(world):
    text = repr(world.job())
    assert text == "<DownloadJob private>"


# --- writes are small, nothing leaks, the reports are bounded -------------------------------------


def test_the_body_is_written_as_it_arrives_never_buffered(world, monkeypatch):
    sizes = []
    write = DownloadSink.write

    def spy(sink, data):
        sizes.append(len(data))
        return write(sink, data)

    monkeypatch.setattr(DownloadSink, "write", spy)
    assert_whole(world, world.run())
    assert max(sizes) <= 16384
    assert sum(sizes) == len(DATA)  # a TLS record at most, whatever the body


PRIVATE = [
    "PRIVATE-URL-CANARY",
    "private-platform-wire-key",
    "X-Amz-Credential",
    "signature=",
    "v1-3f9c",
]


@pytest.mark.parametrize(
    "scenario",
    ["cut", "unframed", "limit", "mismatch", "write", "refused", "interrupted_timeout"],
)
def test_nothing_private_reaches_an_error_a_note_a_file_or_a_log(
    world, monkeypatch, caplog, scenario
):
    secrets = [*PRIVATE, str(world.directory), "provider-name"]
    changes = {}
    if scenario == "cut":
        world.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),), truncate_at=CUT)]
    elif scenario == "unframed":
        world.provider.script = [Reply(body=DATA, omit_length=True)]
    elif scenario == "limit":
        changes["max_bytes"] = 1000
    elif scenario == "mismatch":
        changes["expected_sha256"] = "00" * 32
    elif scenario == "write":
        monkeypatch.setattr(
            download_sink.os,
            "write",
            lambda d, b: (_ for _ in ()).throw(OSError(errno.EIO, "PRIVATE-URL-CANARY")),
        )
    elif scenario == "refused":
        world.provider.script = [Reply(status=403, body=b"PRIVATE-URL-CANARY")]
    else:
        world.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),), header_delay=3)]
        changes["seconds"] = 1
    with caplog.at_level("DEBUG"):
        with pytest.raises(YorungeError) as error:
            world.run(**changes)
    shown = "".join(traceback.format_exception(error.value))
    shown += repr(error.value) + str(error.value) + repr(getattr(error.value, "details", None))
    shown += "".join(getattr(error.value, "__notes__", []))
    shown += caplog.text + repr(world.reports)
    for text in secrets:
        assert text not in shown, text
    # The sidecar is the one file that keeps the tag (it is what a resume is judged by); no
    # address, key or path is in any file the download leaves.
    for name in world.names():
        if name != NAME:
            kept = (world.directory / name).read_bytes().decode("latin-1")
            for text in secrets:
                assert text == "v1-3f9c" or text not in kept, (name, text)


# --- the parts: the deadline and the reports ------------------------------------------------------


def test_the_deadline_is_absolute_and_moves_on_by_what_the_control_call_took():
    limit = _Limit(time.monotonic() + 10)
    before = limit.deadline
    limit.refund(2.5)
    limit.refund(-5)  # a clock that stepped back refunds nothing
    assert limit.deadline == before + 2.5
    limit.guard()
    past = _Limit(time.monotonic() - 0.001)
    with pytest.raises(YorungeError) as error:
        past.guard()
    assert error.value.code == "transport_timeout"


def test_reports_are_at_most_ten_a_second_and_the_first_and_the_last_are_always_made():
    now, seen = [100.0], []
    meter = _Progress(lambda held, total: seen.append((held, total)), clock=lambda: now[0])
    for step in range(1000):  # a thousand updates in one second
        now[0] = 100.0 + step / 1000
        meter.update(step, 5000)
    meter.finish(5000, 5000)
    assert seen[0] == (0, 5000)
    assert seen[-1] == (5000, 5000)
    assert len(seen) <= 12  # the first, ten in the second, the last
    assert [held for held, _ in seen] == sorted(held for held, _ in seen)


def test_the_last_report_is_not_repeated_and_no_sink_means_no_reports():
    seen = []
    meter = _Progress(lambda held, total: seen.append(held), clock=lambda: 0.0)
    meter.update(7, None)
    meter.finish(7, None)
    assert seen == [7]
    quiet = _Progress(None)
    quiet.update(1, 1)
    quiet.finish(1, 1)  # nothing to call, nothing to fail
