"""The sink's edges: what a hostile directory can do, what the filesystem refuses, the order of
durability, descriptors, and the exclusion of the lock.

Each test pins a choice that a plausible slip would undo: a check after an open, the order of an
fsync, the code of an OS error, a lock that is no longer the name's, a guard that raises an OSError.
The protocol itself is in ``test_download_sink.py``; the killed-at-every-step matrix is in
``test_download_sink_kill.py``.
"""

import array
import errno
import fcntl
import hashlib
import os
import threading
from dataclasses import replace

import pytest

from tests.integration.test_download_sink import (
    DATA,
    IDENTITY,
    NAME,
    NAMES,
    TAG,
    chunked,
    code_of,
    download,
    full,
    left,
    partial_answer,
    sidecar_of,
    stopped_after,
    target,
)
from tests.integration.test_download_sink import place as place
from yorunge.adapters import download_files, download_sink
from yorunge.adapters.download_sink import open_sink
from yorunge.domain.download import DownloadPartial
from yorunge.domain.download_response import ContentRange, DownloadResponse
from yorunge.domain.download_state import Entry
from yorunge.domain.errors import YorungeError


def run_with_deadline(action, seconds=10):
    outcome = []

    def runner():
        try:
            outcome.append(("ok", action()))
        except BaseException as error:  # noqa: BLE001
            outcome.append(("raised", error))

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join(seconds)
    return None if thread.is_alive() else outcome[0]


def descriptors():
    return len(os.listdir("/dev/fd"))


def sidecar_bytes(place):
    return (place / NAMES.sidecar).read_bytes()


# --- O_NONBLOCK is what keeps a FIFO swapped in the open window from blocking ---------------
def test_a_sidecar_swapped_for_a_fifo_between_the_look_and_the_open_does_not_block(
    place, monkeypatch
):
    stopped_after(place, 100_000)
    sidecar = place / NAMES.sidecar
    real, swapped = os.open, []

    def swapping_open(path, flags, mode=0o777, *, dir_fd=None):
        if path == NAMES.sidecar and not swapped:
            swapped.append(1)
            os.rename(sidecar, place / "aside")
            os.mkfifo(sidecar, 0o600)
        return real(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(download_files.os, "open", swapping_open)
    result = run_with_deadline(lambda: download(place))
    if result is None:  # blocked: let the reader go so that the process can end
        fd = real(sidecar, os.O_WRONLY | os.O_NONBLOCK)
        os.close(fd)
    assert result is not None, "the command blocked on a FIFO"
    assert result[0] == "raised"
    assert result[1].code == "download_partial_unverified"
    assert sidecar.is_fifo()


# --- the lock object is taken at most three times ---------------------------------------
def test_a_lock_object_that_keeps_vanishing_is_tried_exactly_three_times(place, monkeypatch):
    lock = place / NAMES.lock
    lock.write_bytes(b"")
    os.chmod(lock, 0o600)
    opened = []

    def marker(name):
        if name == "lock:opened":
            opened.append(1)
            lock.unlink()
            lock.write_bytes(b"")
            os.chmod(lock, 0o600)

    monkeypatch.setattr(download_files, "_marker", marker)
    assert code_of(lambda: download(place)) == "download_busy"
    assert len(opened) == download_files.LOCK_ATTEMPTS == 3


# --- identity is (device, inode) and a vanished name is nobody ---------------------------
def test_identity_is_the_device_and_the_inode_and_a_name_that_vanished_is_no_file():
    first = Entry(regular=True, ours=True, private=True, nlink=1, device=1, inode=5, size=0)
    assert download_files.same_file(first, replace(first, size=9))
    assert not download_files.same_file(
        first, replace(first, device=2)
    )  # one inode number, two filesystems
    assert not download_files.same_file(first, replace(first, inode=6))
    assert not download_files.same_file(first, None)


# --- after a retry the lock that is held is on the name that stands ----------------------
def test_after_the_lock_object_was_found_removed_the_lock_held_is_on_the_name_that_stands(
    place, monkeypatch
):
    lock = place / NAMES.lock
    lock.write_bytes(b"")
    os.chmod(lock, 0o600)
    opened = []

    def marker(name):
        if name == "lock:opened" and not opened:
            opened.append(1)
            lock.unlink()  # the process that held it finished between this one's open and its flock

    monkeypatch.setattr(download_files, "_marker", marker)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        monkeypatch.undo()
        assert opened
        assert lock.exists()  # a lock on a removed file excludes nobody
        assert (
            code_of(lambda: open_sink(target(place), identity_key=IDENTITY).__enter__())
            == "download_busy"
        )
        sink.stop()


# --- the opened file is looked at again: a stage that lost its privacy is not ours -----------
def test_a_stage_that_loses_its_privacy_between_the_look_and_the_open_is_not_ours(
    place, monkeypatch
):
    stopped_after(place, 100_000)
    real, done = os.open, []

    def chmodding_open(path, flags, mode=0o777, *, dir_fd=None):
        if path == NAMES.stage and not done:
            done.append(1)
            os.chmod(place / NAMES.stage, 0o644)  # the very same inode, no longer private
        return real(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(download_files.os, "open", chmodding_open)
    assert code_of(lambda: download(place)) == "download_partial_unverified"
    monkeypatch.undo()
    assert (place / NAMES.stage).read_bytes() == DATA[:100_000]


# --- the opened file must be the very file that was seen (a foreign file that stays alive) -----
def test_a_foreign_file_that_is_opened_in_the_place_of_the_stage_and_lives_on_is_not_ours(
    place, monkeypatch
):
    stopped_after(place, 100_000)
    stage, hold, foreign, kept = (
        place / NAMES.stage,
        place / "hold",
        place / "foreign",
        place / "foreign.kept",
    )
    real, swapped = os.open, []

    def swapping_open(path, flags, mode=0o777, *, dir_fd=None):
        if path == NAMES.stage and not swapped:
            swapped.append(1)
            foreign.write_bytes(b"FOREIGN")
            os.chmod(foreign, 0o600)
            os.rename(stage, hold)
            os.replace(foreign, stage)
            descriptor = real(path, flags, mode, dir_fd=dir_fd)  # the open gets the foreign file...
            os.rename(stage, kept)  # ...which lives on (one link, ours, private)...
            os.rename(hold, stage)  # ...and the name leads to the file that was seen again
            return descriptor
        return real(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(download_files.os, "open", swapping_open)
    assert code_of(lambda: download(place)) == "download_partial_unverified"
    monkeypatch.undo()
    assert stage.read_bytes() == DATA[:100_000]
    assert kept.read_bytes() == b"FOREIGN"


# --- and the name must still lead to it after the open ----------------------------------------
def test_a_stage_whose_name_is_swapped_just_after_the_open_is_not_ours(place, monkeypatch):
    stopped_after(place, 100_000)
    stage, aside = place / NAMES.stage, place / "aside"
    real, swapped = os.open, []

    def swapping_open(path, flags, mode=0o777, *, dir_fd=None):
        descriptor = real(path, flags, mode, dir_fd=dir_fd)
        if path == NAMES.stage and not swapped:
            swapped.append(1)
            os.rename(stage, aside)
            stage.write_bytes(b"FOREIGN")
            os.chmod(stage, 0o600)
        return descriptor

    monkeypatch.setattr(download_files.os, "open", swapping_open)
    assert code_of(lambda: download(place)) == "download_partial_unverified"
    monkeypatch.undo()
    assert stage.read_bytes() == b"FOREIGN"
    assert aside.read_bytes() == DATA[:100_000]


# --- the process umask is only borrowed ---------------------------------------------------------
def test_the_process_umask_is_the_same_after_a_download_as_before(place):
    previous = os.umask(0o022)
    try:
        download(place)
        assert os.umask(0o022) == 0o022
    finally:
        os.umask(previous)


# --- a publish plan says how much of the download it holds -------------------------------------
def test_a_publish_plan_reports_the_bytes_it_holds(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete()
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        assert (plan.action, plan.ask, plan.resumed_from) == ("publish", None, len(DATA))
        sink.publish(None)


# --- a trace that vanishes between the look and its removal is no reason to stop --------
def test_a_trace_that_vanishes_between_the_look_and_its_removal_is_tolerated(place, monkeypatch):
    stopped_after(place, 100_000)

    def vanish(name):
        if name == "decided":
            (
                place / NAMES.sidecar
            ).unlink()  # ENOENT is tolerated: it is gone, which is what was ordered

    monkeypatch.setattr(download_files, "_marker", vanish)
    published, plan = download(place, no_resume=True)
    assert target(place).read_bytes() == DATA


def test_an_unlink_that_finds_the_name_gone_is_tolerated(place, monkeypatch):
    stopped_after(place, 100_000)
    real, raced = os.unlink, []

    def racing_unlink(path, *, dir_fd=None):
        if path == NAMES.sidecar and not raced:
            raced.append(1)
            real(path, dir_fd=dir_fd)
            raise FileNotFoundError(path)
        return real(path, dir_fd=dir_fd)

    monkeypatch.setattr(download_files.os, "unlink", racing_unlink)
    download(place, no_resume=True)
    assert raced
    assert target(place).read_bytes() == DATA


# --- a sidecar write that writes nothing is a failure, not a livelock ---------------------------
def test_a_sidecar_write_that_writes_nothing_is_a_write_failure(place, monkeypatch):
    real = os.write

    def nothing_for_the_sidecar(descriptor, data):
        return 0 if bytes(data[:1]) == b"{" else real(descriptor, data)

    monkeypatch.setattr(download_files.os, "write", nothing_for_the_sidecar)

    def attempt():
        with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
            sink.begin(full(), "full")

    result = run_with_deadline(attempt)
    monkeypatch.undo()
    assert result is not None, "the sidecar write never ended"
    assert result[0] == "raised"
    assert result[1].code == "download_write_failed"


# --- short writes keep the sidecar whole and the digests true -------------------------------
def test_short_writes_keep_the_sidecar_whole_and_the_digests_true(place, monkeypatch):
    real = os.write
    monkeypatch.setattr(
        download_sink.os, "write", lambda descriptor, data: real(descriptor, data[:7])
    )
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        DownloadPartial.decode(sidecar_bytes(place))  # F32: a sidecar cut after its first piece
        sink.write(DATA[:100_000])
        sink.stop()
    monkeypatch.undo()
    record = DownloadPartial.decode(sidecar_bytes(place))
    assert (
        record.prefix_sha256 == hashlib.sha256(DATA[:100_000]).hexdigest()
    )  # S55: hashed what was written
    published, plan = download(place)
    assert published.sha256 == hashlib.sha256(DATA).hexdigest()
    assert plan.resumed_from == 100_000


# --- a lock object that was replaced does not turn a published download into an error ---------
def test_a_lock_object_replaced_during_the_download_is_left_alone_and_the_download_stands(
    place, monkeypatch
):
    lock = place / NAMES.lock

    def replace_the_lock(name):
        if (
            name == "publish:after_link"
        ):  # after the last look at the lock: only the release is left
            lock.unlink()
            lock.write_bytes(b"SOMEONE ELSE")
            os.chmod(lock, 0o600)

    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete()
        monkeypatch.setattr(download_files, "_marker", replace_the_lock)
        sink.publish(None)
        monkeypatch.undo()
    assert lock.read_bytes() == b"SOMEONE ELSE"
    assert target(place).read_bytes() == DATA


# --- the lost race to create the lock object is taken as 'present' --------------------------------
def test_a_lock_object_created_by_another_process_a_moment_earlier_is_taken_up(place, monkeypatch):
    lock = place / NAMES.lock
    real, raced = os.open, []

    def racing_open(path, flags, mode=0o777, *, dir_fd=None):
        if path == NAMES.lock and flags & os.O_CREAT and not raced:
            raced.append(1)
            lock.write_bytes(b"")  # the other process got there first
            os.chmod(lock, 0o600)
        return real(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(download_files.os, "open", racing_open)
    published, plan = download(place)
    assert raced
    assert published.bytes == len(DATA)


# --- published is a phase of its own -------------------------------------------------------------
def test_a_published_download_cannot_be_published_again(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete()
        sink.publish(None)
        assert code_of(lambda: sink.publish(None)) == "invalid_request"


# --- the cleanup after the link does not remove a sidecar that is not provably the download's ---
def test_a_foreign_sidecar_is_not_removed_by_the_cleanup_after_the_link(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete()
        (place / NAMES.sidecar).unlink()
        (place / NAMES.sidecar).write_bytes(b"FOREIGN")
        os.chmod(place / NAMES.sidecar, 0o644)
        assert code_of(lambda: sink.publish(None)) == "download_write_uncertain"
    assert (place / NAMES.sidecar).read_bytes() == b"FOREIGN"


# --- no descriptor outlives a download, a refusal or a stop --------------------------------------
def test_no_descriptor_outlives_the_scenarios(place):
    def descriptors():
        return len(os.listdir("/dev/fd"))

    download(place)  # warm-up
    (place / NAME).unlink()
    before = descriptors()
    stopped_after(place, 100_000)
    download(place)
    (place / NAME).unlink()
    assert (
        code_of(lambda: open_sink(place / "x" / NAME, identity_key=IDENTITY).__enter__())
        == "download_target_invalid"
    )
    target(place).write_bytes(b"in the way")
    assert code_of(lambda: download(place)) == "download_output_exists"
    assert descriptors() == before


# --- the durability order of a checkpoint, a completion and a drop ---------------
class Spy:
    def __init__(self, monkeypatch):
        self.events, self.names = [], {}
        real_open, real_fsync, real_replace, real_unlink = os.open, os.fsync, os.replace, os.unlink
        spy = self

        def opening(path, flags, mode=0o777, *, dir_fd=None):
            descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
            spy.names[descriptor] = "dir" if flags & os.O_DIRECTORY else str(path)
            return descriptor

        def label(descriptor):
            name = spy.names.get(descriptor, "?")
            for key, short in (("part", "stage"), ("json.tmp", "tmp"), ("lock", "lock")):
                if name.endswith(key):
                    return short
            return "dir" if name == "dir" else name

        def fsyncing(descriptor):
            spy.events.append(f"fsync:{label(descriptor)}")
            return real_fsync(descriptor)

        def replacing(src, dst, **keywords):
            spy.events.append("replace:sidecar" if dst.endswith(".json") else f"replace:{dst}")
            return real_replace(src, dst, **keywords)

        def unlinking(path, *, dir_fd=None):
            spy.events.append(
                "unlink:"
                + (
                    "stage"
                    if path.endswith(".part")
                    else "sidecar"
                    if path.endswith(".json")
                    else "other"
                )
            )
            return real_unlink(path, dir_fd=dir_fd)

        for name, function in (
            ("open", opening),
            ("fsync", fsyncing),
            ("replace", replacing),
            ("unlink", unlinking),
        ):
            monkeypatch.setattr(os, name, function)

    def since(self, mark):
        return self.events[mark:]


def test_a_checkpoint_makes_the_bytes_durable_before_the_sidecar_that_claims_them(
    place, monkeypatch
):
    spy = Spy(monkeypatch)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        monkeypatch.setattr(download_sink, "CHECKPOINT_BYTES", 1000)
        mark = len(spy.events)
        sink.write(DATA[:2000])  # one block, then the checkpoint
        assert spy.since(mark) == ["fsync:stage", "fsync:tmp", "replace:sidecar", "fsync:dir"], (
            spy.since(mark)
        )
        mark = len(spy.events)
        sink.write(DATA[2000:])
        sink.complete()  # the completion checkpoint: the same order
        completion = spy.since(mark)
        assert completion[-4:] == ["fsync:stage", "fsync:tmp", "replace:sidecar", "fsync:dir"], (
            completion
        )
        monkeypatch.setattr(download_sink, "CHECKPOINT_BYTES", 8 * 1024 * 1024)
        sink.stop()


def test_a_drop_and_a_discard_sync_the_directory_after_the_removals(place, monkeypatch):
    stopped_after(place, 100_000)
    spy = Spy(monkeypatch)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        mark = len(spy.events)
        sink.discard()
        events = spy.since(mark)
        assert events[:3] == ["unlink:stage", "unlink:sidecar", "fsync:dir"], events  # S45
        sink.begin(full(), "full")
        mark = len(spy.events)
        sink.stop()  # a strong tag, a known total, but no byte: dropped
        assert spy.since(mark) == ["unlink:stage", "unlink:sidecar", "fsync:dir"]  # S67


# --- the error paths close what they opened ----------------------------------------------
def test_the_refusals_and_failures_close_their_descriptors(place, monkeypatch):
    download(place)
    target(place).unlink()
    before = descriptors()
    # a committed prefix that is not what was hashed: the stage is dropped, the download restarts
    stopped_after(place, 100_000)
    with (place / NAMES.stage).open("r+b") as stage:
        stage.seek(500)
        stage.write(b"\xff")
    download(place)
    target(place).unlink()
    assert descriptors() == before
    # S85: a name that is not a target must not hold the directory open
    for _ in range(3):
        code_of(lambda: open_sink(place / ("a\nb"), identity_key=IDENTITY).__enter__())
    assert descriptors() == before

    # F45: a sidecar write that fails
    def failing(name):
        if name == "sidecar_tmp:written":
            raise OSError(5, "boom")

    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        monkeypatch.setattr(download_files, "_marker", failing)
        code_of(lambda: sink.begin(full(), "full"))
        monkeypatch.undo()
    assert descriptors() == before
    # F43: a stage swapped for a foreign file in the open window
    stopped_after(place, 100_000)
    stage, hold, foreign = place / NAMES.stage, place / "hold", place / "foreign"
    real, swapped = os.open, []

    def swapping_open(path, flags, mode=0o777, *, dir_fd=None):
        if path == NAMES.stage and not swapped:
            swapped.append(1)
            foreign.write_bytes(b"FOREIGN")
            os.chmod(foreign, 0o600)
            os.rename(stage, hold)
            os.replace(foreign, stage)
            descriptor = real(path, flags, mode, dir_fd=dir_fd)
            os.rename(stage, place / "foreign.kept")
            os.rename(hold, stage)
            return descriptor
        return real(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(download_files.os, "open", swapping_open)
    code_of(lambda: download(place))
    monkeypatch.undo()
    assert descriptors() == before


# --- after a resume the digest is the digest of the WHOLE file -----------------------------------
def test_a_resumed_download_reports_the_digest_of_the_whole_file_and_earns_the_level(place):
    stopped_after(place, 100_000)
    whole = hashlib.sha256(DATA).hexdigest()
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(
            DownloadResponse(
                206,
                ContentRange(100_000, len(DATA) - 1, len(DATA)),
                TAG,
                "length",
                len(DATA) - 100_000,
            ),
            "continue",
        )
        sink.write(DATA[100_000:150_000])
        sink.stop()
    assert (
        DownloadPartial.decode(sidecar_bytes(place)).prefix_sha256
        == hashlib.sha256(DATA[:150_000]).hexdigest()
    )
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        start = plan.ask.prefix_bytes
        sink.begin(
            DownloadResponse(
                206, ContentRange(start, len(DATA) - 1, len(DATA)), TAG, "length", len(DATA) - start
            ),
            "continue",
        )
        sink.write(DATA[start:])
        sink.complete()
        published = sink.publish(whole)
    assert published.sha256 == whole
    assert published.verification.level == "sha256_matched"


# --- a local read error is a verdict about the trace, not an escaping OSError -----------------
def test_a_sidecar_that_cannot_be_read_is_an_unverified_trace(place, monkeypatch):
    stopped_after(place, 100_000)
    real = os.read

    def failing(descriptor, count):
        if count == 4097:  # the sidecar read (one byte more than a sidecar may hold)
            raise OSError(5, "EIO")
        return real(descriptor, count)

    monkeypatch.setattr(download_files.os, "read", failing)
    assert code_of(lambda: download(place)) == "download_partial_unverified"
    monkeypatch.undo()
    assert (place / NAMES.stage).read_bytes() == DATA[:100_000]


def test_a_prefix_that_cannot_be_read_is_discarded_and_the_download_starts_clean(
    place, monkeypatch
):
    stopped_after(place, 100_000)
    real = os.read

    def failing(descriptor, count):
        if count == 100_000:  # the re-hash of the committed prefix
            raise OSError(5, "EIO")
        return real(descriptor, count)

    monkeypatch.setattr(download_sink.os, "read", failing)
    published, plan = download(place)
    monkeypatch.undo()
    assert plan.ask is None
    assert target(place).read_bytes() == DATA


# --- a file that was not seen to be ours is not even opened --------------------------------------
def test_a_sidecar_that_is_not_ours_is_not_opened(place, monkeypatch):
    stopped_after(place, 100_000)
    os.chmod(place / NAMES.sidecar, 0o644)
    real, opened = os.open, []

    def recording_open(path, flags, mode=0o777, *, dir_fd=None):
        opened.append(path)
        return real(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(download_files.os, "open", recording_open)
    assert code_of(lambda: download(place)) == "download_partial_unverified"
    assert NAMES.sidecar not in opened


# --- the removals of a start are made stage first, then the sidecar, and the directory is synced --
def test_the_removals_of_a_start_are_stage_then_sidecar_then_a_directory_sync(place, monkeypatch):
    stopped_after(place, 100_000)
    spy = Spy(monkeypatch)
    with open_sink(target(place), identity_key=IDENTITY, no_resume=True) as (sink, plan):
        assert spy.events[:3] == ["unlink:stage", "unlink:sidecar", "fsync:dir"], spy.events
        sink.stop()


# --- a temporary copy left behind is removed by the cleanup of a discard and of a publication ----
def test_a_leftover_temporary_copy_goes_with_the_cleanup_after_the_link(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete()
        tmp = place / NAMES.sidecar_tmp
        tmp.write_bytes(b"{")
        os.chmod(tmp, 0o600)
        sink.publish(None)
    assert sorted(p.name for p in place.iterdir()) == [NAME]


def test_a_leftover_temporary_copy_goes_with_the_cleanup_after_a_definite_refusal(
    place, monkeypatch
):
    real = os.link

    def racing(*arguments, **keywords):
        target(place).write_bytes(b"the other owner")
        return real(*arguments, **keywords)

    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete()
        tmp = place / NAMES.sidecar_tmp
        tmp.write_bytes(b"{")
        os.chmod(tmp, 0o600)
        monkeypatch.setattr(os, "link", racing)
        assert code_of(lambda: sink.publish(None)) == "download_output_exists"
        monkeypatch.undo()
    assert sorted(p.name for p in place.iterdir()) == [NAME]


# ==================================================================================================
# What a sink promises of its errors: closed codes, never the OS's, nothing deleted on doubt
# ==================================================================================================


def sha(data):
    return hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize(
    "raised",
    [TimeoutError("deadline"), BrokenPipeError(32, "pipe"), OSError(errno.EIO, "EIO")],
    ids=["timeout", "pipe", "oserror"],
)
def test_a_guard_that_raises_an_os_error_is_no_verdict_about_the_prefix(place, raised):
    # The prefix is re-hashed under the guard: whatever it raises must not read as "unreadable",
    # which would order the verified stage deleted. (An OS error is not a code a guard should
    # raise; it comes out as a write failure and nothing is touched.)
    stopped_after(place, 100_000)

    def guard():
        raise raised

    assert code_of(
        lambda: open_sink(target(place), identity_key=IDENTITY, guard=guard).__enter__()
    ) == ("download_write_failed")
    assert left(place) == sorted([NAMES.stage, NAMES.sidecar])
    assert (place / NAMES.stage).read_bytes() == DATA[:100_000]


def test_a_guard_that_raises_a_closed_error_propagates_it_and_keeps_the_stage(place):
    stopped_after(place, 100_000)

    def guard():
        raise YorungeError("transport_timeout")

    assert code_of(
        lambda: open_sink(target(place), identity_key=IDENTITY, guard=guard).__enter__()
    ) == ("transport_timeout")
    assert left(place) == sorted([NAMES.stage, NAMES.sidecar])


def test_a_directory_that_cannot_be_written_is_a_write_failure_not_the_os_error(place):
    place.chmod(0o500)
    try:
        assert code_of(lambda: open_sink(target(place), identity_key=IDENTITY).__enter__()) == (
            "download_write_failed"
        )
    finally:
        place.chmod(0o700)
    assert left(place) == []


def test_a_failing_truncation_when_the_range_was_ignored_is_a_write_failure(place, monkeypatch):
    stopped_after(place, 100_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        assert plan.ask is not None

        def failing(descriptor, length):
            raise OSError(errno.EIO, "PRIVATE")

        monkeypatch.setattr(download_sink.os, "ftruncate", failing)
        assert code_of(lambda: sink.begin(full(), "restart")) == "download_write_failed"
        monkeypatch.undo()


def test_a_full_disk_when_the_stage_is_made_again_is_a_write_failure(place, monkeypatch):
    stopped_after(place, 100_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):

        def full_disk(*arguments, **keywords):
            raise OSError(errno.ENOSPC, "PRIVATE")

        monkeypatch.setattr(download_sink, "create_exclusive", full_disk)
        assert code_of(sink.discard) == "download_write_failed"
        monkeypatch.undo()


def test_a_foreign_file_where_the_new_stage_goes_is_an_unverified_trace(place, monkeypatch):
    stopped_after(place, 100_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sync = download_sink.sync_directory

        def planting(descriptor):
            sync(descriptor)
            (place / NAMES.stage).write_bytes(
                b"FOREIGN"
            )  # after the removals, before the new stage

        monkeypatch.setattr(download_sink, "sync_directory", planting)
        assert code_of(sink.discard) == "download_partial_unverified"
        monkeypatch.undo()
    assert (place / NAMES.stage).read_bytes() == b"FOREIGN"


def test_a_filesystem_without_locks_is_a_write_failure_and_leaks_no_descriptor(place, monkeypatch):
    from types import SimpleNamespace

    def no_locks(descriptor, operation):
        raise OSError(errno.ENOLCK, "PRIVATE")

    unlocked = SimpleNamespace(flock=no_locks, LOCK_EX=fcntl.LOCK_EX, LOCK_NB=fcntl.LOCK_NB)
    monkeypatch.setattr(download_files, "require_local_files", lambda: unlocked)
    before = descriptors()
    assert code_of(lambda: open_sink(target(place), identity_key=IDENTITY).__enter__()) == (
        "download_write_failed"
    )
    assert descriptors() == before


def test_a_filesystem_that_keeps_no_permissions_is_refused_before_a_byte_and_leaves_nothing(
    place, monkeypatch
):
    real = os.fchmod
    monkeypatch.setattr(
        download_files.os, "fchmod", lambda descriptor, mode: real(descriptor, 0o700)
    )
    assert code_of(lambda: open_sink(target(place), identity_key=IDENTITY).__enter__()) == (
        "download_write_failed"
    )
    monkeypatch.undo()
    assert left(place) == []  # not the lock object it just made, not a stage


def test_a_failing_close_is_a_write_failure_not_a_read_failure(place, monkeypatch):
    stopped_after(place, 100_000)
    real = os.close
    sidecar_reads = []

    def failing_close(descriptor):
        real(descriptor)
        if sidecar_reads:
            raise OSError(errno.EIO, "PRIVATE")

    read = os.read

    def noting_read(descriptor, count):
        if count == 4097:
            sidecar_reads.append(1)
        return read(descriptor, count)

    monkeypatch.setattr(download_files.os, "read", noting_read)
    monkeypatch.setattr(download_files.os, "close", failing_close)
    assert code_of(lambda: download(place)) == "download_write_failed"


def test_an_os_error_carries_nothing_of_itself_into_the_closed_error(place):
    place.chmod(0o500)
    try:
        with pytest.raises(YorungeError) as error:
            open_sink(target(place), identity_key=IDENTITY).__enter__()
    finally:
        place.chmod(0o700)
    assert error.value.__context__ is None
    assert error.value.__cause__ is None


# --- a lock object that was removed during the download: no more exclusion, so no more writes -----


def lost_lock(place, monkeypatch=None):
    (place / NAMES.lock).unlink()


def test_a_download_whose_lock_object_was_removed_stops_at_its_next_checkpoint(place, monkeypatch):
    monkeypatch.setattr(download_sink, "CHECKPOINT_BYTES", 50_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA[:10_000])
        lost_lock(place)
        assert code_of(lambda: sink.write(DATA[10_000:80_000])) == "download_busy"
    assert (place / NAMES.stage).exists()
    assert sidecar_of(place).committed_bytes == 0


def test_a_download_whose_lock_object_was_removed_is_never_completed_or_published(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        lost_lock(place)
        assert code_of(lambda: sink.complete(terminated=True)) == "download_busy"
    assert not target(place).exists()
    assert sorted(left(place)) == sorted([NAMES.stage, NAMES.sidecar])


def test_a_second_run_that_took_the_stage_is_not_overwritten_by_the_first(place):
    # The first run lost its lock object; a second run took a new one, resumed the same stage and
    # cut it back. The first run keeps writing at its own offset: it must stop, not publish a hole.
    with open_sink(target(place), identity_key=IDENTITY) as (first, _):
        first.begin(full(), "full")
        first.write(DATA[:60_000])
        lost_lock(place)
        second = open_sink(target(place), identity_key=IDENTITY)
        sink, plan = second.__enter__()
        try:
            assert plan.action == "download"
            held = (place / NAMES.stage).read_bytes()
            # the lock is looked at before every block: the first run writes nothing more
            assert code_of(lambda: first.write(DATA[60_000:])) == "download_busy"
            assert (place / NAMES.stage).read_bytes() == held
            assert code_of(lambda: first.complete(terminated=True)) == "download_busy"
        finally:
            second.__exit__(None, None, None)
    assert not target(place).exists()


def test_a_download_that_lost_its_lock_does_not_delete_what_the_other_run_holds(place):
    with open_sink(target(place), identity_key=IDENTITY) as (first, _):
        first.begin(full(), "full")
        first.write(DATA[:60_000])
        lost_lock(place)
        # leaving the block with an error: the stop must not drop the stage that is not its own
        with pytest.raises(KeyError):
            raise KeyError("an unrelated failure of the engine")
    assert (place / NAMES.stage).exists()
    assert (place / NAMES.sidecar).exists()


def test_a_wrong_digest_with_a_lost_lock_object_removes_nothing(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        lost_lock(place)
        assert code_of(lambda: sink.publish("00" * 32)) == "download_busy"
    assert sorted(left(place)) == sorted([NAMES.stage, NAMES.sidecar])


# --- the exclusion at the start: the finisher removes the lock object while another run looks -----


def test_a_lock_object_removed_between_the_look_and_the_open_is_taken_again(place, monkeypatch):
    lock = place / NAMES.lock
    lock.write_bytes(b"")
    lock.chmod(0o600)
    real, raced = os.open, []

    def racing_open(path, flags, mode=0o777, *, dir_fd=None):
        if path == NAMES.lock and not raced:
            raced.append(1)
            lock.unlink()  # the process that finished removed it after this one looked
        return real(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(download_files.os, "open", racing_open)
    published, _ = download(place)
    assert raced
    assert published.bytes == len(DATA)


def test_a_lock_object_removed_between_the_open_and_the_second_look_is_taken_again(
    place, monkeypatch
):
    lock = place / NAMES.lock
    lock.write_bytes(b"")
    lock.chmod(0o600)
    real, raced = os.fstat, []

    def racing_fstat(descriptor):
        found = real(descriptor)
        if not raced and found.st_size == 0 and lock.exists():
            raced.append(1)
            lock.unlink()  # after the file was opened and looked at, before the name is looked at
        return found

    monkeypatch.setattr(download_files.os, "fstat", racing_fstat)
    published, _ = download(place)
    assert raced
    assert published.bytes == len(DATA)


# --- what is written must be what is counted ------------------------------------------------------


def test_an_interrupt_between_the_digest_and_the_count_keeps_the_record_that_stood(
    place, monkeypatch
):
    monkeypatch.setattr(download_sink, "CHECKPOINT_BYTES", 100_000)
    with pytest.raises(KeyboardInterrupt):
        with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
            sink.begin(full(), "full")
            sink.write(DATA[:100_000])  # a checkpoint stands at 100_000

            class LateInterrupt:
                """A signal lands when the C call returns: after the update, before the count."""

                def __init__(self, inner):
                    self.inner = inner

                def update(self, data):
                    self.inner.update(data)
                    raise KeyboardInterrupt

                def hexdigest(self):
                    return self.inner.hexdigest()

                def copy(self):
                    return self.inner.copy()

            sink._hasher = LateInterrupt(sink._hasher)
            sink.write(DATA[100_000:150_000])
    record = sidecar_of(place)
    assert (record.committed_bytes, record.prefix_sha256) == (100_000, sha(DATA[:100_000]))
    published, plan = download(place)
    assert plan.resumed_from == 100_000
    assert published.resumed  # progress kept, not thrown away
    assert target(place).read_bytes() == DATA


def test_more_bytes_than_the_answer_promised_are_refused_and_nothing_is_kept(place):
    with pytest.raises(YorungeError) as error:
        with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
            sink.begin(full(1000), "full")
            sink.write(b"x" * 1500)
    assert error.value.code == "invalid_response"
    assert left(place) == []


def test_stopping_never_raises_whatever_it_finds(place, monkeypatch):
    def broken(self):
        raise ValueError("a record that fails its own validation")

    monkeypatch.setattr(download_sink.DownloadSink, "_checkpoint", broken)
    with pytest.raises(KeyError):  # the engine's own failure is the one that comes out
        with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
            sink.begin(full(), "full")
            sink.write(DATA[:5000])
            raise KeyError("the engine failed")


def test_a_buffer_of_wider_items_is_written_as_bytes(place):
    wide = array.array("I", range(1000))
    raw = wide.tobytes()
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(DownloadResponse(200, None, TAG, "length", len(raw)), "full")
        sink.write(wide)
        sink.complete(terminated=True)
        published = sink.publish(None)
    assert target(place).read_bytes() == raw
    assert published.sha256 == sha(raw)


def test_a_failed_header_checkpoint_after_the_range_was_ignored_drops_the_whole_trace(
    place, monkeypatch
):
    stopped_after(place, 100_000)

    def failing(*arguments, **keywords):
        raise OSError(errno.EIO, "PRIVATE")

    with pytest.raises(YorungeError) as error:
        with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
            assert plan.ask is not None
            monkeypatch.setattr(download_sink.DownloadSink, "_write_sidecar", failing)
            sink.begin(full(), "restart")
    assert error.value.code == "download_write_failed"
    assert left(place) == []  # an empty stage beside a record that claims 100,000 bytes is no trace


# --- the API traps: a continuation that is not one, a body that is not whole ----------------------


@pytest.mark.parametrize(
    "response",
    [
        partial_answer(100_001),  # another start
        partial_answer(100_000, etag='"other"'),  # another object
        partial_answer(100_000, total=len(DATA) + 1),  # the object grew
        full(),  # the range was ignored: that is a restart
        DownloadResponse(206, None, TAG, None, None),  # not framed
    ],
    ids=["start", "tag", "total", "full", "unframed"],
)
def test_begin_continue_refuses_an_answer_that_is_not_the_rest_of_this_object(place, response):
    stopped_after(place, 100_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        assert code_of(lambda: sink.begin(response, "continue")) == "invalid_request"


def test_a_chunked_body_is_whole_only_if_the_caller_says_its_end_was_seen(place):
    with pytest.raises(YorungeError) as error:
        with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
            sink.begin(chunked(), "full")
            sink.write(DATA[:120_000])
            assert code_of(sink.complete) == "download_incomplete"
            sink.complete(terminated=False)
    assert error.value.code == "download_incomplete"
    assert left(place) == []  # no total, no resume: stopped, dropped
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(chunked(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        assert sink.publish(None).bytes == len(DATA)


# --- the cleanup after a verdict that is decided: only what is provably the download's ------------


def test_the_cleanup_after_a_wrong_digest_leaves_what_is_not_provably_ours(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        foreign = place / NAMES.sidecar
        foreign.unlink()
        foreign.write_bytes(b"FOREIGN")
        foreign.chmod(0o644)
        assert code_of(lambda: sink.publish("00" * 32)) == "download_integrity_mismatch"
    assert foreign.read_bytes() == b"FOREIGN"
    assert not (place / NAMES.stage).exists()


def test_the_cleanup_after_a_wrong_digest_does_not_remove_a_stage_that_is_not_the_one_written(
    place,
):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        stage = place / NAMES.stage
        stage.rename(place / "aside")
        stage.write_bytes(
            b"ANOTHER FILE OF OURS"
        )  # private, one link, ours: but not what was written
        stage.chmod(0o600)
        assert code_of(lambda: sink.publish("00" * 32)) == "download_integrity_mismatch"
    assert stage.read_bytes() == b"ANOTHER FILE OF OURS"


# --- the plan says what it holds; the result says whether it used an earlier run ------------------


def test_a_whole_stage_of_no_bytes_is_published_as_resumed_from_nothing(place, monkeypatch):
    with monkeypatch.context() as patch:

        def broken(descriptor):
            raise OSError(errno.EIO, "PRIVATE")

        patch.setattr(download_sink, "full_sync", broken)
        with pytest.raises(YorungeError):
            download(place, b"")
    published, plan = download(place, b"")
    assert (plan.action, plan.resumed_from) == ("publish", 0)
    assert (published.bytes, published.resumed_from_bytes, published.resumed) == (0, 0, True)


def test_a_fresh_download_did_not_use_an_earlier_run_and_a_continued_one_did(place):
    fresh, _ = download(place)
    assert fresh.resumed is False
    target(place).unlink()
    stopped_after(place, 100_000)
    continued, plan = download(place)
    assert (plan.resumed_from, continued.resumed_from_bytes, continued.resumed) == (
        100_000,
    ) * 2 + (True,)


def test_a_malformed_identity_is_refused_before_anything_is_created(place):
    for bad in ("x", "AB" * 32, None, 5):
        assert code_of(lambda bad=bad: open_sink(target(place), identity_key=bad).__enter__()) == (
            "invalid_request"
        )
    assert left(place) == []


def test_the_cleanup_after_a_definite_refusal_syncs_the_directory_after_the_removals(
    place, monkeypatch
):
    real = os.link

    def racing(*arguments, **keywords):
        target(place).write_bytes(b"the other owner")
        return real(*arguments, **keywords)

    spy = Spy(monkeypatch)  # before the directory is opened: it names the descriptors it sees
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        monkeypatch.setattr(os, "link", racing)
        mark = len(spy.events)
        assert code_of(lambda: sink.publish(None)) == "download_output_exists"
        during = spy.since(mark)
    removals = [event for event in during if event.startswith(("unlink:", "fsync:dir"))]
    assert removals[-3:] == ["unlink:stage", "unlink:sidecar", "fsync:dir"], during
