"""The places that look at the lock object, the closed-error wrapper and the lock's own races.

``LockObject.verify()`` is called before a block is written, at every checkpoint, at ``begin``,
``discard`` and ``stop``, at the completion and before the publication: each call site is pinned
here by removing the lock object and watching that nothing more is written or removed. The
``@_closed`` wrapper is pinned for ``write``, ``complete`` and ``publish``; a write that claims more
than it was given is a failed write; a lock object that is replaced or is being unlinked while
another run looks at it or opens it is taken again (never reported as a foreign trace); and a
close that fails never replaces what is already decided (a published target, an interrupt, a
wrong digest).
"""

import errno
import os
from dataclasses import replace

import pytest

from tests.integration.test_download_sink import (
    DATA,
    IDENTITY,
    NAMES,
    chunked,
    code_of,
    download,
    full,
    left,
    stopped_after,
    target,
)
from tests.integration.test_download_sink import place as place
from yorunge.adapters import download_files, download_sink
from yorunge.adapters.download_sink import open_sink
from yorunge.domain.errors import DownloadIntegrityMismatch


def lost_lock(place):
    (place / NAMES.lock).unlink()


def test_begin_after_the_lock_object_was_removed_writes_nothing(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        lost_lock(place)
        assert code_of(lambda: sink.begin(full(), "full")) == "download_busy"
        assert left(place) == [NAMES.stage]  # no header checkpoint was written


def test_begin_restart_after_the_lock_object_was_removed_truncates_nothing(place):
    stopped_after(place, 100_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        lost_lock(place)
        assert code_of(lambda: sink.begin(full(), "restart")) == "download_busy"
    assert (place / NAMES.stage).stat().st_size == 100_000


def test_discard_after_the_lock_object_was_removed_removes_nothing(place):
    stopped_after(place, 100_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        lost_lock(place)
        assert code_of(sink.discard) == "download_busy"
        assert left(place) == sorted([NAMES.stage, NAMES.sidecar])
    assert left(place) == sorted([NAMES.stage, NAMES.sidecar])


def test_stop_after_the_lock_object_was_removed_drops_nothing(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(chunked(), "full")  # no total: a stop would drop the stage ...
        sink.write(b"x" * 10)
        lost_lock(place)
        sink.stop()  # ... but without the lock what stands there may be another run's
    assert (place / NAMES.stage).exists()
    assert (place / NAMES.sidecar).exists()


# --- the closed-error wrapper on write, complete and publish --------------------------------------
def test_write_turns_a_guard_that_raises_a_timeout_into_a_write_failure(place):
    armed = []

    def guard():
        if armed:
            raise TimeoutError("the engine's deadline")

    with open_sink(target(place), identity_key=IDENTITY, guard=guard) as (sink, plan):
        sink.begin(full(), "full")
        armed.append(1)
        assert code_of(lambda: sink.write(b"x" * 10)) == "download_write_failed"


@pytest.mark.parametrize("method", ["complete", "publish"])
def test_complete_and_publish_turn_an_os_error_of_the_lock_look_into_a_write_failure(
    place, monkeypatch, method
):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(100), "full")
        sink.write(b"x" * 100)
        if method == "publish":
            sink.complete(terminated=True)

        def failing(directory, name):
            raise OSError(errno.EIO, "PRIVATE")

        monkeypatch.setattr(download_files, "entry_of", failing)
        call = (
            (lambda: sink.complete(terminated=True))
            if method == "complete"
            else (lambda: sink.publish(None))
        )
        assert code_of(call) == "download_write_failed"
        monkeypatch.undo()
        sink.stop()


# --- a write that claims more than it was given ---------------------------------------------------
def test_a_body_write_that_claims_more_than_it_was_given_is_a_write_failure(place, monkeypatch):
    real = os.write
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        monkeypatch.setattr(
            download_sink.os, "write", lambda descriptor, data: real(descriptor, data) + 1
        )
        assert code_of(lambda: sink.write(DATA)) == "download_write_failed"
        monkeypatch.undo()
        sink.stop()


def test_a_sidecar_write_that_claims_more_than_it_was_given_is_a_write_failure(place, monkeypatch):
    real = os.write
    monkeypatch.setattr(
        download_files.os,
        "write",
        lambda descriptor, data: real(descriptor, data) + (1 if bytes(data[:1]) == b"{" else 0),
    )
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        assert code_of(lambda: sink.begin(full(), "full")) == "download_write_failed"
        monkeypatch.undo()


# --- the lock object of a finishing run is replaced or unlinked while another run opens it ------
def test_a_lock_object_replaced_by_a_newer_one_between_the_look_and_the_open_is_taken_again(
    place, monkeypatch
):
    lock = place / NAMES.lock
    lock.write_bytes(b"")
    lock.chmod(0o600)
    real, raced = os.open, []

    def racing_open(path, flags, mode=0o777, *, dir_fd=None):
        if path == NAMES.lock and not raced:
            raced.append(1)
            lock.unlink()  # the finishing run removed its lock object ...
            lock.write_bytes(b"")  # ... and a third run made a new one under the same name
            lock.chmod(0o600)
        return real(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(download_files.os, "open", racing_open)
    published, _ = download(place)
    assert raced
    assert published.bytes == len(DATA)


def test_a_lock_object_replaced_after_the_open_is_taken_again(place, monkeypatch):
    lock = place / NAMES.lock
    lock.write_bytes(b"")
    lock.chmod(0o600)
    real, raced = os.fstat, []

    def racing_fstat(descriptor):
        found = real(descriptor)
        if not raced and found.st_size == 0 and lock.exists():
            raced.append(1)
            lock.unlink()
            lock.write_bytes(b"")
            lock.chmod(0o600)
        return found

    monkeypatch.setattr(download_files.os, "fstat", racing_fstat)
    published, _ = download(place)
    assert raced
    assert published.bytes == len(DATA)


def test_a_lock_object_that_lstat_shows_with_no_links_is_being_removed_not_foreign(
    place, monkeypatch
):
    lock = place / NAMES.lock
    lock.write_bytes(b"")
    lock.chmod(0o600)
    real, shown = download_files.entry_of, []

    def unlinking_look(directory, name):
        found = real(directory, name)
        if name == NAMES.lock and found is not None and not shown:
            shown.append(1)
            return replace(found, nlink=0)  # what APFS shows for a name that is being unlinked
        return found

    monkeypatch.setattr(download_files, "entry_of", unlinking_look)
    published, _ = download(place)
    assert shown
    assert published.bytes == len(DATA)


# --- a close that fails must not replace what is already decided ----------------------------------
def failing_stage_close(monkeypatch, sink):
    real, stage = os.close, sink._stage

    def closing(descriptor):
        real(descriptor)
        if descriptor == stage:
            raise OSError(errno.EIO, "PRIVATE")

    monkeypatch.setattr(os, "close", closing)


def test_a_close_that_fails_after_the_publication_is_not_a_failed_download(place, monkeypatch):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        failing_stage_close(monkeypatch, sink)
        sink.publish(None)
    monkeypatch.undo()
    assert target(place).read_bytes() == DATA


def test_a_close_that_fails_does_not_replace_the_error_that_ended_the_download(place, monkeypatch):
    with pytest.raises(KeyboardInterrupt):
        with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
            sink.begin(full(), "full")
            sink.write(DATA[:5000])
            failing_stage_close(monkeypatch, sink)
            raise KeyboardInterrupt
    monkeypatch.undo()


def test_a_wrong_digest_is_still_the_verdict_when_the_stage_will_not_close(place, monkeypatch):
    with pytest.raises(DownloadIntegrityMismatch):
        with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
            sink.begin(full(), "full")
            sink.write(DATA)
            sink.complete(terminated=True)
            failing_stage_close(monkeypatch, sink)
            sink.publish("00" * 32)
    monkeypatch.undo()
    assert left(place) == []
