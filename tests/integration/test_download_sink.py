"""The local side of a download on a real filesystem: lock, stage, sidecar, publication.

The sink is driven the way the engine will drive it: ``open_sink`` takes the target and says what
the directory calls for, ``begin`` receives the accepted answer, ``write`` the body,
``complete`` the end of it, ``publish`` the finished stage. Each test names a row of the start
table, a boundary of the closed order or a hostile thing a directory can hold; the
killed-at-every-step matrix is in
``test_download_sink_kill.py``.
"""

import errno
import hashlib
import os
import stat
import threading
from dataclasses import replace
from pathlib import Path

import pytest

from yorunge.adapters import download_files, download_sink
from yorunge.adapters.artifact_publisher import LINK_REFUSED
from yorunge.adapters.download_sink import open_sink
from yorunge.adapters.target_directory import open_target_directory
from yorunge.domain.download import EMPTY_SHA256, DownloadPartial, download_names
from yorunge.domain.download_response import ContentRange, DownloadResponse
from yorunge.domain.errors import DownloadIntegrityMismatch, YorungeError

IDENTITY = "ab" * 32
TAG = '"v1-3f9c"'
NAME = "weights.onnx"
DATA = os.urandom(300_000)
NAMES = download_names(NAME)


@pytest.fixture
def place(tmp_path):
    return tmp_path.resolve()  # the project refuses a path that goes through a symlink


def target(place):
    return place / NAME


def left(place):
    return sorted(p.name for p in place.iterdir())


def full(length=None, etag=TAG):
    return DownloadResponse(200, None, etag, "length", len(DATA) if length is None else length)


def chunked(etag=TAG):
    return DownloadResponse(200, None, etag, "chunked", None)


def partial_answer(start, total=None, etag=TAG):
    total = len(DATA) if total is None else total
    return DownloadResponse(
        206, ContentRange(start, total - 1, total), etag, "length", total - start
    )


def download(place, data=DATA, *, response=None, expected=None, **options):
    """A whole download of ``data``: the plan is followed as a conforming server would answer."""
    with open_sink(target(place), identity_key=IDENTITY, **options) as (sink, plan):
        if plan.action == "publish":
            return sink.publish(expected), plan
        if plan.ask is not None:
            sink.begin(partial_answer(plan.ask.prefix_bytes, len(data)), "continue")
            sink.write(data[plan.ask.prefix_bytes :])
        else:
            sink.begin(response or full(len(data)), "full")
            sink.write(data)
        sink.complete(terminated=True)
        return sink.publish(expected), plan


def stopped_after(place, count, *, response=None, data=DATA):
    """A run that wrote ``count`` bytes and was stopped cleanly (an interrupt, a timeout)."""
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(response or full(len(data)), "full")
        sink.write(data[:count])
        sink.stop()


def sidecar_of(place):
    return DownloadPartial.decode((place / NAMES.sidecar).read_bytes())


def code_of(action):
    with pytest.raises(YorungeError) as error:
        action()
    return error.value.code


# --- a fresh download ----------------------------------------------------------------------------


def test_a_fresh_download_is_published_whole_and_private_and_leaves_nothing(place):
    published, plan = download(place)
    assert (plan.action, plan.ask, plan.resumed_from) == ("download", None, 0)
    assert published.bytes == len(DATA) and published.resumed_from_bytes == 0
    assert published.sha256 == hashlib.sha256(DATA).hexdigest()
    assert (published.verification.level, published.verification.expectation_source) == (
        "transfer_complete",
        "none",
    )
    info = target(place).lstat()
    assert target(place).read_bytes() == DATA
    assert stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1
    assert left(place) == [NAME]  # no lock object, no stage, no sidecar, no temporary copy


def test_an_expectation_that_matches_earns_the_level(place):
    published, _ = download(place, expected=hashlib.sha256(DATA).hexdigest())
    assert (published.verification.level, published.verification.expectation_source) == (
        "sha256_matched",
        "user_supplied",
    )


def test_an_expectation_that_does_not_match_publishes_nothing_and_keeps_nothing(place):
    with pytest.raises(DownloadIntegrityMismatch) as mismatch:
        download(place, expected="00" * 32)
    assert mismatch.value.details == {
        "computed_sha256": hashlib.sha256(DATA).hexdigest(),
        "bytes": len(DATA),
    }
    assert left(place) == []  # not the target, not the stage, not the sidecar, not the lock object


def test_an_empty_body_is_a_download(place):
    published, _ = download(place, b"")
    assert (published.bytes, published.sha256) == (0, EMPTY_SHA256)
    assert target(place).read_bytes() == b"" and left(place) == [NAME]


def test_a_body_may_arrive_in_pieces_of_any_size(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        for offset in range(0, len(DATA), 7_001):
            sink.write(DATA[offset : offset + 7_001])
        sink.write(b"")
        sink.complete(terminated=True)
        assert sink.publish(None).bytes == len(DATA)
    assert target(place).read_bytes() == DATA


def test_a_chunked_body_fixes_its_total_at_the_completion_checkpoint(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(chunked(), "full")
        sink.write(DATA[:1000])
        header = sidecar_of(place)
        assert (header.total_size, header.committed_bytes) == (None, 0)
        sink.write(DATA[1000:])
        sink.complete(terminated=True)
        finished = sidecar_of(place)
        assert (finished.total_size, finished.committed_bytes) == (len(DATA), len(DATA))
        assert finished.prefix_sha256 == hashlib.sha256(DATA).hexdigest()
        assert sink.publish(None).bytes == len(DATA)


def test_the_header_checkpoint_says_what_the_answer_said_before_the_first_byte(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        record = sidecar_of(place)
        stage = (place / NAMES.stage).stat()
        assert (record.identity_key, record.etag, record.total_size) == (IDENTITY, TAG, len(DATA))
        assert (record.committed_bytes, record.prefix_sha256) == (0, EMPTY_SHA256)
        assert (record.stage_device, record.stage_inode) == (
            stage.st_dev & (2**64 - 1),
            stage.st_ino,
        )
        assert stat.S_IMODE((place / NAMES.sidecar).stat().st_mode) == 0o600
        sink.stop()


# --- a stop, and a resume -------------------------------------------------------------------------


def test_a_clean_stop_with_a_strong_tag_and_a_known_total_keeps_what_was_written(place):
    stopped_after(place, 100_000)
    assert left(place) == sorted([NAMES.stage, NAMES.sidecar])  # and the lock object is gone
    record = sidecar_of(place)
    assert record.committed_bytes == 100_000
    assert record.prefix_sha256 == hashlib.sha256(DATA[:100_000]).hexdigest()
    assert (place / NAMES.stage).read_bytes() == DATA[:100_000]


def test_the_next_run_resumes_from_the_committed_prefix_and_reports_it(place):
    stopped_after(place, 100_000)
    published, plan = download(place)
    assert (plan.action, plan.resumed_from) == ("download", 100_000)
    assert (plan.ask.prefix_bytes, plan.ask.total_size, plan.ask.etag) == (100_000, len(DATA), TAG)
    assert published.resumed_from_bytes == 100_000 and published.bytes == len(DATA)
    assert target(place).read_bytes() == DATA and left(place) == [NAME]


@pytest.mark.parametrize(
    "answer",
    [full(etag=None), chunked()],
    ids=["no strong tag", "no total (chunked)"],
)
def test_a_clean_stop_without_a_tag_or_a_total_drops_everything(place, answer):
    stopped_after(place, 100_000, response=answer)
    assert left(place) == []


def test_a_stop_after_every_byte_of_a_body_of_known_length_keeps_it_even_without_a_tag(place):
    # the engine can be cancelled in the one loop turn between the last record and ``complete``
    stopped_after(place, len(DATA), response=full(etag=None))
    assert left(place) == sorted([NAMES.stage, NAMES.sidecar])
    record = sidecar_of(place)
    assert (record.committed_bytes, record.total_size, record.etag) == (len(DATA), len(DATA), None)
    published, plan = download(place)
    assert plan.action == "publish" and published.resumed_from_bytes == len(DATA)
    assert target(place).read_bytes() == DATA and left(place) == [NAME]


def test_a_stop_after_every_byte_of_a_chunked_body_drops_it_the_end_was_not_seen(place):
    stopped_after(place, len(DATA), response=chunked())
    assert left(place) == []


def test_a_clean_stop_before_any_byte_drops_the_empty_stage(place):
    stopped_after(place, 0)
    assert left(place) == []


def test_even_one_byte_of_progress_resumes(place):
    stopped_after(place, 1)
    assert sidecar_of(place).committed_bytes == 1
    published, plan = download(place)
    assert plan.resumed_from == 1 and target(place).read_bytes() == DATA


def test_a_stage_longer_than_its_last_checkpoint_is_cut_back_and_resumed(place):
    stopped_after(place, 100_000)
    with (place / NAMES.stage).open("ab") as stage:
        stage.write(b"bytes written after the last checkpoint, then the process was killed")
    published, plan = download(place)
    assert plan.resumed_from == 100_000 and target(place).read_bytes() == DATA


def test_a_complete_stage_with_bytes_after_its_total_is_cut_back_before_it_is_published(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
    with (place / NAMES.stage).open("ab") as stage:
        stage.write(b"garbage that was written after the completion checkpoint")
    published, plan = download(place)
    assert plan.action == "publish" and published.bytes == len(DATA)
    assert target(place).read_bytes() == DATA  # exactly the total: nothing trails it


def test_a_provider_that_restarts_with_a_shorter_object_leaves_nothing_of_the_old_tail(place):
    stopped_after(place, 100_000)
    smaller = os.urandom(50_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(len(smaller), etag='"v2"'), "restart")  # the object changed
        sink.write(smaller)
        sink.complete(terminated=True)
        published = sink.publish(None)
    assert published.bytes == 50_000 and target(place).read_bytes() == smaller


def test_a_stage_whose_committed_prefix_is_not_what_was_hashed_starts_clean(place):
    stopped_after(place, 100_000)
    with (place / NAMES.stage).open("r+b") as stage:
        stage.seek(500)
        stage.write(
            bytes([DATA[500] ^ 0xFF])
        )  # corruption inside the committed prefix: always a change
    published, plan = download(place)
    assert (plan.ask, plan.resumed_from) == (None, 0) and published.resumed_from_bytes == 0
    assert target(place).read_bytes() == DATA and left(place) == [NAME]


def test_a_stage_shorter_than_what_the_sidecar_commits_starts_clean(place):
    stopped_after(place, 100_000)
    os.truncate(place / NAMES.stage, 50_000)
    _, plan = download(place)
    assert plan.ask is None and target(place).read_bytes() == DATA


def test_a_sidecar_of_another_download_is_not_resumed(place):
    stopped_after(place, 100_000)
    with open_sink(target(place), identity_key="12" * 32) as (sink, plan):
        assert (plan.action, plan.ask) == ("download", None)  # another identity: a clean start
        sink.begin(full(), "full")
        sink.stop()
    assert left(place) == []


def test_a_provider_that_ignores_the_range_restarts_from_the_first_byte(place):
    stopped_after(place, 100_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        assert plan.ask is not None
        sink.begin(full(), "restart")  # a 200 to a ranged request: the whole body again
        sink.write(DATA)
        sink.complete(terminated=True)
        published = sink.publish(None)
    assert (published.bytes, published.resumed_from_bytes) == (len(DATA), 0)
    assert target(place).read_bytes() == DATA and left(place) == [NAME]


def test_an_answer_that_does_not_fit_drops_the_stage_and_the_sidecar_and_starts_fresh(place):
    stopped_after(place, 100_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        assert plan.ask is not None
        sink.discard()  # a 206 that does not fit, or a 416: stage first, then the sidecar
        assert left(place) == sorted([NAMES.lock, NAMES.stage])  # a fresh, empty stage
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        published = sink.publish(None)
    assert published.resumed_from_bytes == 0 and target(place).read_bytes() == DATA


def test_a_complete_stage_is_published_without_a_request_and_reports_the_resume(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(
            terminated=True
        )  # the completion checkpoint; the process ends before publishing
    assert left(place) == sorted([NAMES.stage, NAMES.sidecar])
    published, plan = download(place)
    assert (plan.action, plan.ask) == ("publish", None)
    assert published.resumed_from_bytes == len(DATA) and target(place).read_bytes() == DATA
    assert left(place) == [NAME]


def test_a_complete_stage_that_does_not_match_the_expectation_is_dropped(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
    with pytest.raises(DownloadIntegrityMismatch):
        download(place, expected="00" * 32)
    assert left(place) == []  # a kept stage would make every rerun the same offline mismatch


def test_no_resume_drops_what_is_ours_and_starts_clean(place):
    stopped_after(place, 100_000)
    published, plan = download(place, no_resume=True)
    assert (plan.ask, plan.resumed_from) == (None, 0) and published.resumed_from_bytes == 0
    assert target(place).read_bytes() == DATA


def test_a_checkpoint_is_written_every_eight_mebibytes_with_the_digest_of_the_synced_bytes(
    place,
):
    big = os.urandom(9 * 1024 * 1024 + 123)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(len(big)), "full")
        sink.write(big[: 7 * 1024 * 1024])
        assert sidecar_of(place).committed_bytes == 0  # not yet
        sink.write(big[7 * 1024 * 1024 :])
        record = sidecar_of(place)
        assert record.committed_bytes == 8 * 1024 * 1024
        assert record.prefix_sha256 == hashlib.sha256(big[: 8 * 1024 * 1024]).hexdigest()
        sink.complete(terminated=True)
        assert sink.publish(None).bytes == len(big)
    assert target(place).read_bytes() == big


def test_a_body_past_the_limit_is_refused_before_it_is_written(place, monkeypatch):
    monkeypatch.setattr(download_sink, "MAX_DOWNLOAD_BYTES", 1000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(chunked(), "full")
        sink.write(DATA[:1000])
        assert code_of(lambda: sink.write(b"x")) == "download_limit_exceeded"
        sink.stop()


def test_an_error_that_leaves_the_block_stops_cleanly_and_keeps_what_can_be_resumed(place):
    for error in (RuntimeError("an engine bug"), KeyboardInterrupt()):
        with pytest.raises(type(error)):
            with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
                sink.begin(full(), "full")
                sink.write(DATA[:100_000])
                raise error
        assert left(place) == sorted([NAMES.stage, NAMES.sidecar])  # and the lock object is gone
        assert sidecar_of(place).committed_bytes == 100_000
        (place / NAMES.stage).unlink()
        (place / NAMES.sidecar).unlink()


def test_a_sidecar_write_that_fails_is_a_write_failure_and_leaves_no_temporary_copy(
    place, monkeypatch
):
    def failing(name):
        if name == "sidecar_tmp:written":
            raise OSError(errno.ENOSPC, "PRIVATE-PATH")

    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        monkeypatch.setattr(download_files, "_marker", failing)
        error = None
        try:
            sink.begin(full(), "full")
        except YorungeError as caught:
            error = caught
        assert error is not None and error.code == "download_write_failed"
        assert "PRIVATE-PATH" not in str(error.envelope())
        assert NAMES.sidecar_tmp not in left(place)
        monkeypatch.undo()


def test_a_deadline_during_the_prefix_hash_propagates_and_discards_nothing(place):
    stopped_after(place, 100_000)
    ticks = []

    def guard():
        ticks.append(1)
        raise YorungeError("transport_timeout")  # the engine's deadline reaches the local read

    with pytest.raises(YorungeError) as error:
        with open_sink(target(place), identity_key=IDENTITY, guard=guard):
            pytest.fail("the sink was handed over although its prefix was never checked")
    assert error.value.code == "transport_timeout" and ticks
    assert left(place) == sorted([NAMES.stage, NAMES.sidecar])  # a deadline is not a verdict
    assert (place / NAMES.stage).read_bytes() == DATA[:100_000]


def test_the_guard_is_asked_between_the_blocks_of_a_long_write(place):
    asked = []
    with open_sink(target(place), identity_key=IDENTITY, guard=lambda: asked.append(1)) as (
        sink,
        _,
    ):
        sink.begin(full(3 * 1024 * 1024), "full")
        sink.write(os.urandom(3 * 1024 * 1024))
        assert len(asked) == 3  # one per block of at most a mebibyte
        sink.stop()


def test_a_clock_that_goes_backwards_never_makes_a_record_older_than_its_start(place):
    from datetime import UTC, datetime, timedelta

    times = iter(datetime(2026, 11, 8, 12, tzinfo=UTC) - timedelta(minutes=n) for n in range(50))
    with open_sink(target(place), identity_key=IDENTITY, clock=lambda: next(times)) as (sink, _):
        sink.begin(full(), "full")
        sink.write(DATA[:1000])
        sink.stop()
    record = sidecar_of(place)
    assert record.updated_at >= record.created_at and record.committed_bytes == 1000


def test_a_resume_keeps_the_time_the_download_began(place):
    stopped_after(place, 100_000)
    began = sidecar_of(place).created_at
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(partial_answer(plan.ask.prefix_bytes), "continue")
        sink.write(DATA[100_000:150_000])
        sink.stop()
    record = sidecar_of(place)
    assert record.created_at == began and record.committed_bytes == 150_000


def test_the_sink_is_driven_in_order_and_anything_else_is_refused(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        assert code_of(lambda: sink.write(b"x")) == "invalid_request"  # no answer yet
        assert code_of(sink.complete) == "invalid_request"
        assert code_of(lambda: sink.publish(None)) == "invalid_request"
        assert code_of(lambda: sink.begin(full(), "continue")) == "invalid_request"  # nothing held
        assert code_of(lambda: sink.begin(full(), "discard_and_retry")) == "invalid_request"
        sink.begin(full(), "full")
        assert code_of(lambda: sink.begin(full(), "full")) == "invalid_request"  # once
        assert code_of(sink.discard) == "invalid_request"  # only before an answer is accepted
        sink.stop()
        assert code_of(lambda: sink.write(b"x")) == "invalid_request"  # stopped


def test_a_stop_before_the_answer_leaves_the_stage_of_an_earlier_run_as_it_was(place):
    stopped_after(place, 100_000)
    before = (place / NAMES.stage).read_bytes(), (place / NAMES.sidecar).read_bytes()
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        assert plan.ask is not None
        sink.stop()  # the request failed before any answer: nothing changed this run
    assert ((place / NAMES.stage).read_bytes(), (place / NAMES.sidecar).read_bytes()) == before
    assert left(place) == sorted([NAMES.stage, NAMES.sidecar])
    assert download(place)[1].resumed_from == 100_000


def test_the_stage_is_made_durable_with_a_full_sync_before_the_link(place, monkeypatch):
    synced = []
    real = download_sink.full_sync
    monkeypatch.setattr(
        download_sink, "full_sync", lambda handle: (synced.append(handle), real(handle))
    )
    download(place)
    assert len(synced) == 1


def test_a_stage_that_appears_between_the_decision_and_its_creation_is_looked_at_again(
    place, monkeypatch
):
    appeared = []

    def marker(name):
        if name == "decided" and not appeared:
            appeared.append(1)
            stage = place / NAMES.stage
            stage.write_bytes(b"")
            os.chmod(stage, 0o600)

    monkeypatch.setattr(download_files, "_marker", marker)
    published, plan = download(place)
    assert appeared and plan.action == "download" and target(place).read_bytes() == DATA


def test_a_stage_that_keeps_appearing_is_not_ours(place, monkeypatch):
    def marker(name):
        if name == "decided":
            stage = place / NAMES.stage
            if not stage.exists():
                stage.write_bytes(b"")
                os.chmod(stage, 0o600)
            else:  # the foreign file is replaced again and again, so that creation never wins
                stage.unlink()
                stage.write_bytes(b"")
                os.chmod(stage, 0o600)

    monkeypatch.setattr(download_files, "_marker", marker)
    assert code_of(lambda: download(place)) in {"download_partial_unverified"}


# --- what is already there ------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["file", "directory", "dangling symlink"])
def test_an_existing_target_is_reported_and_never_touched(place, kind):
    if kind == "file":
        target(place).write_bytes(b"someone else's")
    elif kind == "directory":
        target(place).mkdir()
    else:
        target(place).symlink_to("nowhere")
    before = left(place)
    assert code_of(lambda: download(place)) == "download_output_exists"
    assert left(place) == before  # the lock object was taken and given back; nothing else moved


def test_the_trace_of_an_interrupted_publication_is_cleaned_before_the_report(place):
    stopped_after(place, 100_000)
    stage = place / NAMES.stage
    os.link(stage, target(place))  # the link took place; the stage was not yet removed
    os.truncate(target(place), 100_000)
    assert code_of(lambda: download(place)) == "download_output_exists"
    assert left(place) == [NAME]  # stage and sidecar went (stage first); the target stands
    assert target(place).stat().st_nlink == 1


def test_a_lock_object_that_a_killed_process_left_behind_is_taken_up_again(place):
    lock = place / NAMES.lock
    lock.write_bytes(b"")
    os.chmod(lock, 0o600)
    published, _ = download(place)
    assert published.bytes == len(DATA) and left(place) == [NAME]


def test_a_leftover_temporary_sidecar_of_ours_is_removed(place):
    stopped_after(place, 100_000)
    tmp = place / NAMES.sidecar_tmp
    tmp.write_bytes(b"{")
    os.chmod(tmp, 0o600)
    published, plan = download(place)
    assert plan.resumed_from == 100_000 and left(place) == [NAME]


def test_a_stage_without_its_sidecar_that_was_never_filled_is_reused(place):
    stage = place / NAMES.stage
    stage.write_bytes(b"")
    os.chmod(stage, 0o600)
    inode = stage.stat().st_ino
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        assert (plan.action, plan.ask) == ("download", None)
        assert stage.stat().st_ino == inode  # the very file, not a new one
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        sink.publish(None)
    assert target(place).read_bytes() == DATA


def test_an_orphan_sidecar_is_discarded_and_the_download_starts_clean(place):
    stopped_after(place, 100_000)
    (place / NAMES.stage).unlink()  # the interrupted run's worst trace: no stage, a sidecar
    published, plan = download(place)
    assert plan.ask is None and target(place).read_bytes() == DATA and left(place) == [NAME]


def test_no_resume_gets_out_of_an_unreadable_sidecar_without_a_stage(place):
    sidecar = place / NAMES.sidecar
    sidecar.write_bytes(b"not a record")
    os.chmod(sidecar, 0o600)
    assert code_of(lambda: download(place)) == "download_partial_unverified"
    assert sidecar.read_bytes() == b"not a record"  # nothing was touched
    published, _ = download(place, no_resume=True)
    assert published.bytes == len(DATA) and left(place) == [NAME]


# --- what is not ours is never touched -----------------------------------------------------------


def make_fifo(path):
    os.mkfifo(path, 0o600)


def make_symlink(path):
    path.symlink_to("nowhere")


def make_readable(path):
    path.write_bytes(b"x")
    os.chmod(path, 0o644)


def make_linked(path):
    path.write_bytes(b"x")
    os.chmod(path, 0o600)
    os.link(path, path.with_name(path.name + ".other"))


def make_directory(path):
    path.mkdir()


KINDS = [make_fifo, make_symlink, make_readable, make_linked, make_directory]


@pytest.mark.parametrize("kind", KINDS, ids=lambda kind: kind.__name__)
@pytest.mark.parametrize("slot", ["stage", "sidecar", "sidecar_tmp", "lock"])
@pytest.mark.parametrize("no_resume", [False, True])
def test_a_trace_that_is_not_provably_ours_stops_the_command_and_nothing_is_changed(
    place, kind, slot, no_resume
):
    foreign = place / getattr(NAMES, slot)
    kind(foreign)
    before = {p.name: p.lstat().st_mode for p in place.iterdir()}
    outcome = []
    runner = threading.Thread(
        target=lambda: outcome.append(code_of(lambda: download(place, no_resume=no_resume))),
        daemon=True,  # a regression that blocks must not keep the interpreter from exiting
    )
    runner.start()
    runner.join(10)  # a FIFO must not block the command
    assert not runner.is_alive(), "the command blocked"
    assert outcome == ["download_partial_unverified"]
    assert {p.name: p.lstat().st_mode for p in place.iterdir()} == before
    if kind is make_fifo or kind is make_symlink:
        assert foreign.is_fifo() or foreign.is_symlink()


def test_a_name_that_is_swapped_after_the_look_is_not_removed(place, monkeypatch):
    stopped_after(place, 100_000)

    def swap(name):
        if name == "decided":  # between the look at the directory and the removals it ordered
            foreign = place / "foreign"
            foreign.write_bytes(b"FOREIGN")
            os.chmod(foreign, 0o600)
            os.replace(foreign, place / NAMES.stage)

    monkeypatch.setattr(download_files, "_marker", swap)
    assert code_of(lambda: download(place, no_resume=True)) == "download_partial_unverified"
    assert (place / NAMES.stage).read_bytes() == b"FOREIGN"  # it is not the stage that was seen


def test_a_file_that_is_swapped_while_it_is_being_opened_is_not_ours(place, monkeypatch):
    stopped_after(place, 100_000)
    stage, hold, foreign = place / NAMES.stage, place / "hold", place / "foreign"
    real = os.open
    swapped = []

    def swapping_open(path, flags, mode=0o777, *, dir_fd=None):
        if path == NAMES.stage and not swapped:
            swapped.append(1)
            foreign.write_bytes(b"FOREIGN")
            os.chmod(foreign, 0o600)
            os.rename(stage, hold)
            os.replace(foreign, stage)  # the open gets the foreign file...
            descriptor = real(path, flags, mode, dir_fd=dir_fd)
            os.unlink(stage)
            os.rename(hold, stage)  # ...and the name leads to the file that was seen again
            return descriptor
        return real(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(download_files.os, "open", swapping_open)
    assert code_of(lambda: download(place)) == "download_partial_unverified"
    monkeypatch.undo()
    assert stage.read_bytes() == DATA[:100_000]  # the stage was left as it was


def test_a_file_of_another_user_is_not_ours(place, monkeypatch):
    stopped_after(place, 100_000)
    stage_inode = (place / NAMES.stage).stat().st_ino
    real = download_files.describe

    def as_seen_by_someone_else(info):
        found = real(info)
        return replace(found, ours=False) if info.st_ino == stage_inode else found

    monkeypatch.setattr(download_files, "describe", as_seen_by_someone_else)
    assert code_of(lambda: download(place)) == "download_partial_unverified"
    assert (place / NAMES.stage).read_bytes() == DATA[:100_000]


def test_the_files_are_private_and_accepted_by_the_next_run_whatever_the_umask(place):
    previous = os.umask(0o277)
    try:
        stopped_after(place, 100_000)
        for name in (NAMES.stage, NAMES.sidecar):
            assert stat.S_IMODE((place / name).stat().st_mode) == 0o600
        published, plan = download(place)
    finally:
        os.umask(previous)
    assert plan.resumed_from == 100_000 and target(place).read_bytes() == DATA


# --- one writer at a time -------------------------------------------------------------------------


def test_a_second_download_of_the_same_target_is_busy_and_touches_nothing(place):
    with open_sink(target(place), identity_key=IDENTITY) as (first, _):
        first.begin(full(), "full")
        first.write(DATA[:1000])
        before = left(place)
        assert code_of(lambda: download(place)) == "download_busy"
        assert left(place) == before
        assert (place / NAMES.stage).read_bytes() == DATA[:1000]
        first.stop()


def test_another_target_in_the_same_directory_is_not_busy(place):
    other = place / "other.onnx"
    with open_sink(target(place), identity_key=IDENTITY) as (first, _):
        with open_sink(other, identity_key=IDENTITY) as (second, plan):
            assert plan.action == "download"
        first.stop()


def test_a_lock_that_was_waited_for_on_a_removed_object_is_taken_again(place, monkeypatch):
    # The process that held the lock finishes between this one's open and its flock: the object it
    # removed is the one this process locked, and the name now leads nowhere.
    lock = place / NAMES.lock
    lock.write_bytes(b"")
    os.chmod(lock, 0o600)
    opened = []

    def marker(name):
        if name == "lock:opened" and not opened:
            opened.append(1)
            lock.unlink()

    monkeypatch.setattr(download_files, "_marker", marker)
    published, _ = download(place)
    assert opened and published.bytes == len(DATA) and left(place) == [NAME]


def test_a_lock_object_that_keeps_vanishing_is_busy_after_three_attempts(place, monkeypatch):
    lock = place / NAMES.lock
    lock.write_bytes(b"")
    os.chmod(lock, 0o600)

    def marker(name):
        if name == "lock:opened":
            lock.unlink()
            lock.write_bytes(b"")
            os.chmod(lock, 0o600)

    monkeypatch.setattr(download_files, "_marker", marker)
    assert code_of(lambda: download(place)) == "download_busy"


# --- the target and its directory -----------------------------------------------------------------


def test_a_directory_that_does_not_exist_is_not_a_target(place):
    assert code_of(
        lambda: open_sink(place / "missing" / NAME, identity_key=IDENTITY).__enter__()
    ) == ("download_target_invalid")


def test_a_directory_reached_through_a_link_is_not_a_target(place):
    real = place / "real"
    real.mkdir()
    (place / "link").symlink_to(real)
    assert code_of(lambda: open_sink(place / "link" / NAME, identity_key=IDENTITY).__enter__()) == (
        "download_target_invalid"
    )


@pytest.mark.parametrize(
    "name",
    [
        ".yorunge-download-" + "0" * 32 + ".part",
        ".YORUNGE-DOWNLOAD-" + "0" * 32 + ".PART",
        "a\nb",
        "x" * 300,
    ],
)
def test_a_name_that_is_not_one_ordinary_name_is_not_a_target(place, name):
    assert code_of(lambda: open_sink(place / name, identity_key=IDENTITY).__enter__()) == (
        "download_target_invalid"
    )


def test_a_relative_path_is_not_a_target():
    assert code_of(lambda: open_sink(Path("weights.onnx"), identity_key=IDENTITY).__enter__()) == (
        "download_target_invalid"
    )


# --- failures of the disk -------------------------------------------------------------------------


def test_a_disk_that_fills_is_a_write_failure_and_the_next_run_goes_through(place, monkeypatch):
    real = os.write
    calls = []

    def full_disk(descriptor, data):
        calls.append(1)
        if len(calls) > 3:
            raise OSError(errno.ENOSPC, "PRIVATE-PATH")
        return real(descriptor, data)

    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        monkeypatch.setattr(download_sink.os, "write", full_disk)
        error = None
        try:
            for offset in range(0, len(DATA), 50_000):
                sink.write(DATA[offset : offset + 50_000])
        except YorungeError as caught:
            error = caught
        assert error is not None and error.code == "download_write_failed"
        assert "PRIVATE-PATH" not in str(error.envelope())
        sink.stop()
    monkeypatch.undo()
    published, _ = download(place)
    assert published.bytes == len(DATA) and target(place).read_bytes() == DATA


def test_short_writes_still_complete_the_file(place, monkeypatch):
    real = os.write
    monkeypatch.setattr(download_sink.os, "write", lambda d, data: real(d, data[:7]))
    published, _ = download(place)
    assert published.bytes == len(DATA)
    monkeypatch.undo()
    assert target(place).read_bytes() == DATA


def test_a_write_that_writes_nothing_is_a_write_failure(place, monkeypatch):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        monkeypatch.setattr(download_sink.os, "write", lambda d, data: 0)
        assert code_of(lambda: sink.write(DATA)) == "download_write_failed"
        monkeypatch.undo()
        sink.stop()


def test_a_sync_that_fails_at_a_checkpoint_is_a_write_failure(place, monkeypatch):
    big = os.urandom(9 * 1024 * 1024)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(len(big)), "full")

        def refuse(descriptor):
            raise OSError(errno.EIO, "PRIVATE-PATH")

        monkeypatch.setattr(download_sink.os, "fsync", refuse)
        assert code_of(lambda: sink.write(big)) == "download_write_failed"
        monkeypatch.undo()
        sink.stop()


def test_a_body_shorter_than_the_total_is_incomplete(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        sink.write(DATA[:-1])
        assert code_of(sink.complete) == "download_incomplete"
        sink.stop()


# --- the publication ------------------------------------------------------------------------------


def test_a_link_the_filesystem_refuses_is_uncertain_and_the_complete_stage_is_kept(
    place, monkeypatch
):
    def refuse(*arguments, **keywords):
        raise OSError(errno.EIO, "PRIVATE-PATH")

    monkeypatch.setattr(os, "link", refuse)
    assert code_of(lambda: download(place)) == "download_write_uncertain"
    monkeypatch.undo()
    assert not target(place).exists()
    assert left(place) == sorted([NAMES.stage, NAMES.sidecar])  # the only copy of the download
    published, plan = download(place)  # the next run finds a complete stage and publishes it
    assert plan.action == "publish" and target(place).read_bytes() == DATA


@pytest.mark.parametrize("number", sorted(LINK_REFUSED))
def test_a_link_the_kernel_refuses_is_a_failure_and_keeps_the_complete_stage_for_the_next_run(
    place, monkeypatch, number
):
    real = os.link

    def refuse(*arguments, **keywords):
        raise OSError(number, "PRIVATE-PATH")

    monkeypatch.setattr(os, "link", refuse)
    assert code_of(lambda: download(place)) == "download_write_failed"  # nothing was linked
    monkeypatch.setattr(os, "link", real)
    assert not target(place).exists()
    assert left(place) == sorted([NAMES.stage, NAMES.sidecar])  # a refusal drops nothing
    published, plan = download(place)  # the same stage is published once the link works
    assert plan.action == "publish" and target(place).read_bytes() == DATA
    assert left(place) == [NAME]


def test_an_interrupt_before_the_link_keeps_the_complete_stage(place, monkeypatch):
    def interrupted(*arguments, **keywords):
        raise KeyboardInterrupt

    monkeypatch.setattr(download_sink.DownloadPublisher, "_check_stage", interrupted)
    with pytest.raises(KeyboardInterrupt):  # not the link's doubt: nothing was linked
        download(place)
    monkeypatch.undo()
    assert left(place) == sorted([NAMES.stage, NAMES.sidecar])
    download(place)
    assert target(place).read_bytes() == DATA and left(place) == [NAME]


def test_an_interrupt_that_the_link_itself_raises_is_the_links_doubt(place, monkeypatch):
    def interrupted(*arguments, **keywords):
        raise KeyboardInterrupt

    monkeypatch.setattr(os, "link", interrupted)
    assert code_of(lambda: download(place)) == "download_write_uncertain"
    monkeypatch.undo()
    assert left(place) == sorted([NAMES.stage, NAMES.sidecar])  # and the stage is still whole


def test_a_target_that_appears_before_the_link_is_the_definite_refusal_and_the_stage_goes(
    place, monkeypatch
):
    real = os.link

    def racing(*arguments, **keywords):
        target(place).write_bytes(b"the other owner")
        return real(*arguments, **keywords)

    monkeypatch.setattr(os, "link", racing)
    assert code_of(lambda: download(place)) == "download_output_exists"
    monkeypatch.undo()
    assert target(place).read_bytes() == b"the other owner"
    assert left(place) == [NAME]  # stage and sidecar removed, stage first; the lock object last


def test_a_directory_that_was_replaced_before_the_link_is_a_write_failure_and_nothing_is_lost(
    place, monkeypatch
):
    holder = place / "holder"
    holder.mkdir()
    moved = place / "moved"
    inner = holder / "inner"
    inner.mkdir()
    goal = inner / NAME
    original = open_target_directory(goal)

    def swap(name):
        if name == "publish:synced":
            inner.rename(moved)
            inner.mkdir()

    try:
        with open_sink(goal, identity_key=IDENTITY) as (sink, _):
            sink.begin(full(), "full")
            sink.write(DATA)
            sink.complete(terminated=True)
            monkeypatch.setattr(download_files, "_marker", swap)
            assert code_of(lambda: sink.publish(None)) == "download_write_failed"
            monkeypatch.undo()
    finally:
        original.close()
    assert not goal.exists()
    assert (moved / NAMES.stage).read_bytes() == DATA  # the bytes are where they were written


# --- the identities a record holds ----------------------------------------------------------------


def test_a_negative_device_number_is_one_unsigned_value_on_both_sides():
    assert download_files.file_id(-1673356274) == 2**64 - 1673356274
    assert download_files.file_id(16777230) == 16777230
    info = os.stat_result((0o100600, 7, -5, 1, os.getuid(), 0, 12, 0, 0, 0))
    entry = download_files.describe(info)
    assert (entry.device, entry.inode, entry.size, entry.owned) == (2**64 - 5, 7, 12, True)
