"""Round-2 killers: each test passes on the sink as it is and fails on a named mutant of it.

They pin what the first two files leave open: the uid half of the created-file check, a stat that
fails for a reason other than absence, a descriptor that must not outlive a refusal or an
interrupt, the identity under a refused creation, an unlink that fails (the stage-first order must
hold), the best effort of the lock's release, the error code of each place that opens, creates or
closes, the lock taken away while a second run looks, the closed errors carrying nothing of the OS
error, and a whole stage that an I/O error right after the completion checkpoint must not drop.
The mutant ids in the comments are those of the review's ``mutants.json`` (B_work).
"""

import errno
import os
import stat
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from tests.integration.test_download_sink import (
    DATA,
    IDENTITY,
    NAME,
    NAMES,
    TAG,
    code_of,
    download,
    full,
    left,
    sidecar_of,
    stopped_after,
    target,
)
from tests.integration.test_download_sink import place as place
from tests.integration.test_download_sink_edges import Spy, run_with_deadline
from yorunge.adapters import artifact_publisher, download_files, download_sink
from yorunge.adapters.download_sink import open_sink
from yorunge.domain.download_response import ContentRange, DownloadResponse
from yorunge.domain.errors import MESSAGES, YorungeError


@pytest.fixture(autouse=True)
def keep_checkpoint_interval(monkeypatch):
    """The driver's ``prepare`` lowers ``CHECKPOINT_BYTES`` in this process: restored per test."""
    monkeypatch.setattr(download_sink, "CHECKPOINT_BYTES", download_sink.CHECKPOINT_BYTES)


def descriptors():
    return len(os.listdir("/dev/fd"))


def enter(place):
    return lambda: open_sink(target(place), identity_key=IDENTITY).__enter__()


def enter_bounded(place):
    """The same, but a run that waits for the lock fails the test instead of hanging the run."""

    def attempt():
        result = run_with_deadline(enter(place), 10)
        assert result is not None, "the second run waited for the first"
        kind, value = result
        if kind == "raised":
            raise value
        return value

    return attempt


# --- the created file is checked for its owner as well as its mode (M0100) -----------------------
def test_a_filesystem_that_gives_a_new_file_to_another_user_is_refused_before_a_byte(
    place, monkeypatch
):
    real_chmod, real_fstat = os.fchmod, os.fstat
    armed = []

    def fchmod(descriptor, mode):
        armed.append(1)
        return real_chmod(descriptor, mode)

    def fstat(descriptor):
        info = real_fstat(descriptor)
        if armed:
            armed.clear()
            values = list(info)[:10]
            values[4] = info.st_uid + 1  # st_uid: the file came out as somebody else's
            return os.stat_result(values)
        return info

    monkeypatch.setattr(download_files.os, "fchmod", fchmod)
    monkeypatch.setattr(download_files.os, "fstat", fstat)
    assert code_of(enter(place)) == "download_write_failed"
    monkeypatch.undo()
    assert left(place) == []  # and nothing of it is left behind


# --- a refused or failed creation closes its descriptor (M0115, M0116, M0118) --------------------
@pytest.mark.parametrize("how", ["no permissions kept", "fchmod fails"])
def test_a_new_file_that_cannot_be_made_private_does_not_leak_its_descriptor(
    place, monkeypatch, how
):
    real = os.fchmod

    def refusing(descriptor, mode):
        if how == "fchmod fails":
            raise OSError(errno.EPERM, "no chmod here")
        return real(descriptor, 0o700)

    monkeypatch.setattr(download_files.os, "fchmod", refusing)
    code_of(enter(place))
    before = descriptors()
    code_of(enter(place))
    code_of(enter(place))
    monkeypatch.undo()
    assert descriptors() == before


def test_an_interrupt_between_the_creation_and_the_chmod_does_not_leak_its_descriptor(
    place, monkeypatch
):
    def interrupt(name):
        if name == "lock:created":
            raise KeyboardInterrupt

    monkeypatch.setattr(download_files, "_marker", interrupt)
    before = descriptors()
    enter_value = enter(place)
    with pytest.raises(KeyboardInterrupt):
        enter_value()
    monkeypatch.undo()
    assert descriptors() == before


# --- what a refused creation removes is the file it made, by identity (M0125) ---------------------
def test_a_refused_creation_never_removes_a_file_that_replaced_its_name(place, monkeypatch):
    real = os.fchmod

    def swap(name):
        if name == "lock:created":
            lock = place / NAMES.lock
            os.rename(lock, place / "aside")
            lock.write_bytes(b"FOREIGN")
            os.chmod(lock, 0o600)

    monkeypatch.setattr(download_files, "_marker", swap)
    monkeypatch.setattr(
        download_files.os, "fchmod", lambda descriptor, mode: real(descriptor, 0o700)
    )
    assert code_of(enter(place)) == "download_write_failed"
    monkeypatch.undo()
    assert (place / NAMES.lock).read_bytes() == b"FOREIGN"


# --- a stat that fails is not "nothing is there" (M0033) ------------------------------------------
def test_a_stat_that_fails_is_a_write_failure_and_not_an_absent_file(place, monkeypatch):
    stopped_after(place, 100_000)
    real = os.stat

    def failing(path, *arguments, **keywords):
        if path == NAMES.sidecar:
            raise PermissionError(errno.EACCES, "no")
        return real(path, *arguments, **keywords)

    monkeypatch.setattr(download_files.os, "stat", failing)
    assert code_of(enter(place)) == "download_write_failed"
    monkeypatch.undo()
    assert sorted(left(place)) == sorted([NAMES.stage, NAMES.sidecar])
    assert sidecar_of(place).committed_bytes == 100_000


# --- an unlink that fails leaves the next name alone: the stage goes first or nothing goes (M0153)
@pytest.mark.parametrize("failure", [errno.EIO, errno.EPERM])
def test_a_stage_that_cannot_be_removed_keeps_its_sidecar(place, monkeypatch, failure):
    stopped_after(place, 100_000)
    real = os.unlink

    def failing(path, *, dir_fd=None):
        if path == NAMES.stage:
            raise OSError(failure, "cannot remove")
        return real(path, dir_fd=dir_fd)

    monkeypatch.setattr(download_files.os, "unlink", failing)
    assert code_of(lambda: download(place, no_resume=True)) == "download_write_failed"
    monkeypatch.undo()
    assert sorted(left(place)) == sorted([NAMES.stage, NAMES.sidecar])  # the pair is as it was
    published, plan = download(place)  # and the next run still resumes it
    assert plan.resumed_from == 100_000


# --- a write of a single byte is a write (M0175) --------------------------------------------------
def test_a_sidecar_written_one_byte_at_a_time_is_whole(place, monkeypatch):
    real = os.write
    monkeypatch.setattr(download_files.os, "write", lambda d, data: real(d, bytes(data[:1])))
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        monkeypatch.undo()
        assert sidecar_of(place).committed_bytes == 0  # whole and canonical: it decodes
        sink.stop()


# --- an interrupt inside the helpers leaves no file and no descriptor (M0186, M0288, M0067) -------
@pytest.mark.parametrize("at", ["sidecar_tmp:written", "lock:opened", "lock:held"])
def test_an_interrupt_in_the_middle_of_a_helper_closes_what_it_opened(place, monkeypatch, at):
    def interrupt(name):
        if name == at:
            raise KeyboardInterrupt

    if at == "lock:held":
        stopped_after(place, 100_000)
    if at == "lock:opened":  # a lock object a killed run left behind
        (place / NAMES.lock).write_bytes(b"")
        (place / NAMES.lock).chmod(0o600)
    before = descriptors()
    monkeypatch.setattr(download_files, "_marker", interrupt)
    open_sink_value = open_sink(target(place), identity_key=IDENTITY)
    full_value = full()
    with pytest.raises(KeyboardInterrupt):
        with open_sink_value as (sink, plan):
            sink.begin(full_value, "restart" if plan.ask else "full")
    monkeypatch.undo()
    assert descriptors() == before
    assert NAMES.sidecar_tmp not in left(place)


def test_an_interrupt_while_a_stage_is_opened_for_resume_closes_it(place, monkeypatch):
    stopped_after(place, 100_000)
    real = os.fstat
    calls = []

    def interrupting(descriptor):
        found = real(descriptor)
        if stat.S_ISREG(found.st_mode) and found.st_size == 100_000 and not calls:
            calls.append(1)
            raise KeyboardInterrupt
        return found

    before = descriptors()
    monkeypatch.setattr(download_files.os, "fstat", interrupting)
    enter_value = enter(place)
    with pytest.raises(KeyboardInterrupt):
        enter_value()
    monkeypatch.undo()
    assert descriptors() == before


# --- the release of the lock object never hides how the download ended (M0216, M0218) -------------
def test_a_lock_object_that_cannot_be_removed_does_not_turn_a_published_download_into_an_error(
    place, monkeypatch
):
    real = os.unlink

    def failing(path, *, dir_fd=None):
        if path == NAMES.lock:
            raise OSError(errno.EIO, "cannot remove the lock")
        return real(path, dir_fd=dir_fd)

    monkeypatch.setattr(download_files.os, "unlink", failing)
    published, _ = download(place)
    monkeypatch.undo()
    assert published.bytes == len(DATA)
    assert target(place).read_bytes() == DATA
    assert sorted(left(place)) == sorted([NAME, NAMES.lock])  # an empty file the next run reuses


def test_a_lock_descriptor_that_will_not_close_does_not_turn_a_published_download_into_an_error(
    place, monkeypatch
):
    real = os.close
    lock_descriptors = []
    real_open = os.open

    def opening(path, flags, mode=0o777, *, dir_fd=None):
        descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        if path == NAMES.lock:
            lock_descriptors.append(descriptor)
        return descriptor

    def closing(descriptor):
        real(descriptor)
        if descriptor in lock_descriptors:
            lock_descriptors.remove(descriptor)
            raise OSError(errno.EIO, "close failed")

    monkeypatch.setattr(download_files.os, "open", opening)
    monkeypatch.setattr(download_files.os, "close", closing)
    published, _ = download(place)
    monkeypatch.undo()
    assert published.bytes == len(DATA)
    assert target(place).read_bytes() == DATA


# --- the error code of each place that opens or creates (M0245, M0250, M0481) ---------------------
def test_a_lock_object_that_cannot_be_opened_is_a_write_failure_not_a_vanished_one(
    place, monkeypatch
):
    (place / NAMES.lock).write_bytes(b"")
    (place / NAMES.lock).chmod(0o600)
    real = os.open

    def refusing(path, flags, mode=0o777, *, dir_fd=None):
        if path == NAMES.lock:
            raise PermissionError(errno.EACCES, "no")
        return real(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(download_files.os, "open", refusing)
    assert code_of(enter(place)) == "download_write_failed"
    monkeypatch.undo()


def test_a_lock_object_swapped_for_another_file_while_it_is_opened_is_not_ours(place, monkeypatch):
    lock, hold = place / NAMES.lock, place / "hold"
    lock.write_bytes(b"")
    lock.chmod(0o600)
    real, swapped = os.open, []

    def swapping(path, flags, mode=0o777, *, dir_fd=None):
        if path == NAMES.lock and not swapped:
            swapped.append(1)
            os.rename(lock, hold)
            lock.write_bytes(b"FOREIGN")
            lock.chmod(0o600)
            descriptor = real(path, flags, mode, dir_fd=dir_fd)
            os.rename(lock, place / "foreign.kept")
            os.rename(hold, lock)
            return descriptor
        return real(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(download_files.os, "open", swapping)
    assert code_of(enter(place)) == "download_partial_unverified"
    monkeypatch.undo()


def test_a_stage_that_cannot_be_created_is_a_write_failure_not_an_unverified_trace(
    place, monkeypatch
):
    real = download_sink.create_exclusive

    def refusing(directory, name, *, label):
        if name == NAMES.stage:
            raise OSError(errno.ENOSPC, "full")
        return real(directory, name, label=label)

    monkeypatch.setattr(download_sink, "create_exclusive", refusing)
    assert code_of(enter(place)) == "download_write_failed"
    monkeypatch.undo()
    assert left(place) == []


# --- the number of looks at a directory in which a stage appears after the look (M0463) ----------
def test_a_stage_that_appears_after_the_look_twice_in_a_row_is_not_ours_after_the_second_look(
    place, monkeypatch
):
    stage = place / NAMES.stage
    planted = []
    real_stat = os.stat

    def stat(path, *arguments, **keywords):
        if path == NAMES.stage and planted and stage.exists():
            stage.unlink()  # gone again by the next look: the next decision is a clean start again
        return real_stat(path, *arguments, **keywords)

    def marker(name):
        if name == "decided" and len(planted) < 2:
            planted.append(1)
            stage.write_bytes(b"")
            stage.chmod(0o600)

    monkeypatch.setattr(download_files.os, "stat", stat)
    monkeypatch.setattr(download_files, "_marker", marker)
    # one look again is allowed, a third would let it through: the second miss is the answer
    assert code_of(lambda: download(place)) == "download_partial_unverified"
    assert len(planted) == 2


# --- a failed recheck of the directory chain is a write failure (M0311..M0315) --------------------
def test_a_directory_that_vanished_before_the_link_is_a_write_failure_and_the_stage_stays(
    place, monkeypatch
):
    holder = place / "holder"
    holder.mkdir()
    inner = holder / "inner"
    inner.mkdir()
    goal = inner / NAME
    moved = place / "moved"

    def vanish(name):
        if name == "publish:synced":
            holder.rename(moved)

    with open_sink(goal, identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        monkeypatch.setattr(download_files, "_marker", vanish)
        assert code_of(lambda: sink.publish(None)) == "download_write_failed"
        monkeypatch.undo()
    assert (moved / "inner" / NAMES.stage).read_bytes() == DATA
    assert not (moved / "inner" / NAME).exists()


# --- the codes of a stage that changed before the link, and of a failure before it (M0348..M0355) -
def test_a_stage_that_grew_before_the_link_is_a_write_failure_and_is_kept(place, monkeypatch):
    def grow(name):
        if name == "publish:synced":
            with (place / NAMES.stage).open("ab") as handle:
                handle.write(b"more")

    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        monkeypatch.setattr(download_files, "_marker", grow)
        assert code_of(lambda: sink.publish(None)) == "download_write_failed"
        monkeypatch.undo()
    assert not target(place).exists()
    assert sorted(left(place)) == sorted([NAMES.stage, NAMES.sidecar])


def test_a_stage_that_lost_its_privacy_before_the_link_is_a_write_failure_and_is_kept(
    place, monkeypatch
):
    def loosen(name):
        if name == "publish:synced":
            os.chmod(place / NAMES.stage, 0o644)

    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        monkeypatch.setattr(download_files, "_marker", loosen)
        assert code_of(lambda: sink.publish(None)) == "download_write_failed"
        monkeypatch.undo()
    assert not target(place).exists()


def test_an_os_error_before_the_link_is_a_write_failure_and_the_stage_is_kept(place, monkeypatch):
    real = os.stat

    def failing(path, *arguments, **keywords):
        if path == NAMES.stage:
            raise OSError(errno.EIO, "no")
        return real(path, *arguments, **keywords)

    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        monkeypatch.setattr(os, "stat", failing)
        assert code_of(lambda: sink.publish(None)) == "download_write_failed"
        monkeypatch.undo()
    assert not target(place).exists()


# --- a stop before the answer of a FRESH start leaves nothing (M0435) -----------------------------
def test_a_stop_before_the_answer_of_a_fresh_start_leaves_nothing_behind(place):
    with pytest.raises(KeyError):
        with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
            assert plan.ask is None
            raise KeyError("the request failed before any answer")
    assert left(place) == []


# --- every open of a protocol name refuses a link by its flags (M0002, M0081) ---------------------
def test_every_open_of_a_protocol_name_refuses_a_symlink_and_never_blocks_on_a_fifo(
    place, monkeypatch
):
    stopped_after(place, 100_000)
    seen = []
    real = os.open

    def spy(path, flags, mode=0o777, *, dir_fd=None):
        if isinstance(path, str) and path.startswith(".yorunge-download-"):
            seen.append((path, flags))
        return real(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(download_files.os, "open", spy)
    download(place)
    monkeypatch.undo()
    assert seen
    for path, flags in seen:
        assert flags & os.O_NOFOLLOW, (path, flags)
        if not flags & os.O_CREAT:
            assert flags & os.O_NONBLOCK, (path, flags)


# --- the lock object goes while the lock is still held, and nobody else can take the target in
# --- the cleanup after the link or while a stage is dropped and made again (X06, X03, X04) --------
def test_the_lock_object_is_removed_while_the_lock_is_still_held(place, monkeypatch):
    import fcntl

    real = os.unlink
    probes = []

    def unlinking(path, *, dir_fd=None):
        if path == NAMES.lock:
            probe = os.open(path, os.O_RDWR | os.O_NONBLOCK, dir_fd=dir_fd)
            try:
                try:
                    fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    probes.append("free")  # somebody could have taken the target by now
                except OSError:
                    probes.append("held")
            finally:
                os.close(probe)
        return real(path, dir_fd=dir_fd)

    monkeypatch.setattr(download_files.os, "unlink", unlinking)
    download(place)
    monkeypatch.undo()
    assert probes == ["held"]


def test_a_second_run_cannot_take_the_target_during_the_cleanup_after_the_link(place, monkeypatch):
    answers = []

    def marker(name):
        if name in (
            "publish:after_link",
            "cleanup:stage",
            "removed:sidecar",
            "cleanup:all_removed",
        ):
            answers.append(code_of(enter_bounded(place)))

    monkeypatch.setattr(download_files, "_marker", marker)
    download(place)
    monkeypatch.undo()
    assert answers == ["download_busy"] * 4


def test_a_second_run_cannot_take_the_target_while_a_stage_is_dropped_and_made_again(
    place, monkeypatch
):
    stopped_after(place, 100_000)
    answers = []

    def marker(name):
        if name in ("directory:synced", "stage:created", "stage:private"):
            answers.append(code_of(enter_bounded(place)))

    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        monkeypatch.setattr(download_files, "_marker", marker)
        sink.discard()
        monkeypatch.undo()
    assert answers == ["download_busy"] * 3


# --- an interrupt while a helper cleans up after itself is not hidden by a failure of the cleanup
def test_an_interrupt_is_not_replaced_by_the_failure_of_the_cleanup_of_the_temporary_copy(
    place, monkeypatch
):
    real = os.unlink

    def failing(path, *, dir_fd=None):
        if path == NAMES.sidecar_tmp:
            raise OSError(errno.EIO, "cannot remove")
        return real(path, dir_fd=dir_fd)

    def interrupt(name):
        if name == "sidecar_tmp:written":
            raise KeyboardInterrupt

    monkeypatch.setattr(download_files.os, "unlink", failing)
    monkeypatch.setattr(download_files, "_marker", interrupt)
    open_sink_value = open_sink(target(place), identity_key=IDENTITY)
    full_value = full()
    with pytest.raises(KeyboardInterrupt):
        with open_sink_value as (sink, plan):
            sink.begin(full_value, "full")
    monkeypatch.undo()


# --- the prefix hash: what it opened it closes, what it cannot position or read is discarded ------
@pytest.mark.parametrize(
    "raised",
    [YorungeError("transport_timeout"), KeyboardInterrupt()],
    ids=["deadline", "interrupt"],
)
def test_a_stopped_prefix_hash_closes_the_stage_it_opened(place, raised):
    stopped_after(place, 100_000)

    def guard():
        raise raised

    before = descriptors()
    open_sink_value = open_sink(target(place), identity_key=IDENTITY, guard=guard)
    with pytest.raises(type(raised)):
        open_sink_value.__enter__()
    assert descriptors() == before


def test_a_stopped_prefix_hash_whose_stage_will_not_close_adds_the_note_of_its_family(
    place, monkeypatch
):
    stopped_after(place, 100_000)
    real_open, real_close = os.open, os.close
    stage_descriptors = []

    def opening(path, flags, mode=0o777, *, dir_fd=None):
        descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        if path == NAMES.stage:
            stage_descriptors.append(descriptor)
        return descriptor

    def closing(descriptor):
        real_close(descriptor)
        if descriptor in stage_descriptors:
            stage_descriptors.remove(descriptor)
            raise OSError(errno.EIO, "close failed")

    def guard():
        raise YorungeError("transport_timeout")

    monkeypatch.setattr(download_files.os, "open", opening)
    monkeypatch.setattr(download_files.os, "close", closing)
    open_sink_value = open_sink(target(place), identity_key=IDENTITY, guard=guard)
    with pytest.raises(YorungeError) as caught:
        open_sink_value.__enter__()
    monkeypatch.undo()
    assert caught.value.code == "transport_timeout"
    assert caught.value.__notes__ == [MESSAGES["download_write_failed"]]


def test_a_stage_that_will_not_close_after_a_prefix_mismatch_is_a_write_failure(place, monkeypatch):
    stopped_after(place, 100_000)
    with (place / NAMES.stage).open("r+b") as stage:
        stage.seek(500)
        stage.write(bytes([DATA[500] ^ 0xFF]))  # local corruption inside the committed prefix
    real_open, real_close = os.open, os.close
    stage_descriptors = []

    def opening(path, flags, mode=0o777, *, dir_fd=None):
        descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        if path == NAMES.stage:
            stage_descriptors.append(descriptor)
        return descriptor

    def closing(descriptor):
        real_close(descriptor)
        if descriptor in stage_descriptors:
            stage_descriptors.remove(descriptor)
            raise OSError(errno.EIO, "close failed")

    monkeypatch.setattr(download_files.os, "open", opening)
    monkeypatch.setattr(download_files.os, "close", closing)
    assert code_of(enter(place)) == "download_write_failed"
    monkeypatch.undo()


def test_a_stage_cut_short_after_the_look_is_no_endless_read(place, monkeypatch):
    stopped_after(place, 100_000)
    calls = []

    def marker(name):
        if name == "decided":  # after the look at the directory, before the prefix is read
            os.truncate(place / NAMES.stage, 10)

    def guard():
        calls.append(1)
        if len(calls) > 50:
            raise YorungeError("transport_timeout")  # an endless read would end here, wrongly

    monkeypatch.setattr(download_files, "_marker", marker)
    with open_sink(target(place), identity_key=IDENTITY, guard=guard) as (sink, plan):
        monkeypatch.undo()
        assert plan.ask is None  # the prefix could not be read: a clean start
        sink.stop()


def test_a_prefix_that_cannot_be_positioned_is_discarded_like_one_that_cannot_be_read(
    place, monkeypatch
):
    stopped_after(place, 100_000)
    real = os.lseek
    failed = []

    def failing(descriptor, offset, whence):
        if not failed:
            failed.append(1)
            raise OSError(errno.EIO, "no seek")
        return real(descriptor, offset, whence)

    monkeypatch.setattr(download_sink.os, "lseek", failing)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        monkeypatch.undo()
        assert plan.ask is None
        assert failed
        sink.stop()


# --- the plan of a reused empty stage, and a restart to an empty object ---------------------------
def test_the_plan_of_a_reused_empty_stage_resumes_from_nothing(place):
    stage = place / NAMES.stage
    stage.write_bytes(b"")
    os.chmod(stage, 0o600)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        assert (plan.action, plan.ask, plan.resumed_from) == ("download", None, 0)
        sink.begin(full(), "full")
        sink.stop()


def test_a_provider_that_restarts_with_an_empty_object_leaves_an_empty_file(place):
    stopped_after(place, 100_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        assert plan.ask is not None
        sink.begin(DownloadResponse(200, None, '"v2"', "length", 0), "restart")
        sink.complete(terminated=True)
        published = sink.publish(None)
    assert published.bytes == 0
    assert target(place).read_bytes() == b""


# --- a request that fails right after a discard leaves nothing: a discarded stage is not "kept" --
def test_a_stop_after_a_discard_leaves_nothing_behind(place):
    stopped_after(place, 100_000)
    with pytest.raises(KeyError):
        with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
            assert plan.ask is not None
            sink.discard()
            raise KeyError("the second request failed")
    assert left(place) == []


# --- the matrix kills where the sink announces a boundary: every boundary the reference names is
# --- announced by some scenario (a deleted or renamed ``step`` would silently shrink it) ---
DOCUMENTED_BOUNDARIES = {
    "lock:created",
    "lock:private",
    "lock:opened",
    "lock:held",
    "decided",
    "stage:confirmed",
    "stage:created",
    "stage:private",
    "stage:truncated",
    "removed:stage",
    "removed:sidecar",
    "removed:sidecar_tmp",
    "removed:lock",
    "directory:synced",
    "sidecar_tmp:created",
    "sidecar_tmp:private",
    "sidecar_tmp:written",
    "sidecar_tmp:synced",
    "sidecar:replaced",
    "header_checkpoint",
    "body:written",
    "checkpoint:stage_synced",
    "checkpoint",
    "complete:stage_synced",
    "completion_checkpoint",
    "compared",
    "publish:synced",
    "publish:before_link",
    "publish:after_link",
    "cleanup:stage",
    "cleanup:all_removed",
    "publish:directory_synced",
}


def test_every_boundary_the_reference_names_is_announced_by_some_scenario(tmp_path):
    from tests.integration.test_download_sink_kill import SCENARIOS, child, prepared

    seen = set()
    for number, (name, (scenario, preparation, extra)) in enumerate(SCENARIOS.items()):
        record = tmp_path / f"steps-{number}.txt"
        directory = prepared(tmp_path, f"run-{number}", preparation)
        if name == "resume":  # a temporary copy a killed checkpoint left behind
            leftover = directory / NAMES.sidecar_tmp
            leftover.write_bytes(b"{")
            os.chmod(leftover, 0o600)
        assert child(directory, scenario, extra, record=record).returncode == 0
        seen |= {label.split("#")[0] for label in record.read_text().split()}
    assert DOCUMENTED_BOUNDARIES <= seen, sorted(DOCUMENTED_BOUNDARIES - seen)


# --- B-2: a closed error of the sink carries nothing of the OS error, wherever it is raised -------
@pytest.mark.parametrize("where", ["sidecar replace", "link", "checkpoint fsync", "body write"])
def test_a_closed_error_of_the_sink_carries_no_context_and_no_cause(place, monkeypatch, where):
    def refuse(*arguments, **keywords):
        raise OSError(errno.EIO, "PRIVATE", ".yorunge-download-PRIVATE.part")

    big = os.urandom(9 * 1024 * 1024)
    with pytest.raises(YorungeError) as caught:
        with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
            if where == "sidecar replace":
                monkeypatch.setattr(os, "replace", refuse)
                sink.begin(full(), "full")
            elif where == "link":
                sink.begin(full(), "full")
                sink.write(DATA)
                sink.complete(terminated=True)
                monkeypatch.setattr(os, "link", refuse)
                sink.publish(None)
            elif where == "checkpoint fsync":
                sink.begin(full(len(big)), "full")
                monkeypatch.setattr(download_sink.os, "fsync", refuse)
                sink.write(big)
            else:
                sink.begin(full(), "full")
                monkeypatch.setattr(download_sink.os, "write", refuse)
                sink.write(DATA)
    monkeypatch.undo()
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None


# --- B-1: an I/O error right after the completion checkpoint was replaced never drops the stage ---
@pytest.mark.parametrize(
    "response",
    [
        DownloadResponse(200, None, None, "chunked", None),
        DownloadResponse(200, None, None, "length", len(DATA)),
        full(),
    ],
    ids=["chunked, no tag", "length, no tag", "length, strong tag"],
)
def test_a_failure_right_after_the_completion_checkpoint_never_drops_a_whole_stage(
    place, monkeypatch, response
):
    state = {"in_completion": False, "fail": False}
    real_sync = download_files.sync_directory

    def marker(name):
        if name == "sidecar:replaced" and state["in_completion"]:
            state["fail"] = True  # the replace took place; the directory sync that follows fails

    def sync(descriptor):
        if state["fail"]:
            state["fail"] = False
            raise OSError(errno.EIO, "directory sync")
        return real_sync(descriptor)

    monkeypatch.setattr(download_files, "_marker", marker)
    monkeypatch.setattr(download_files, "sync_directory", sync)
    with pytest.raises(YorungeError) as caught:  # leaving the block with the error: the stop runs
        with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
            sink.begin(response, "full")
            sink.write(DATA)
            state["in_completion"] = True
            sink.complete(terminated=True)
    monkeypatch.undo()
    assert caught.value.code == "download_write_failed"
    assert sorted(left(place)) == sorted(
        [NAMES.stage, NAMES.sidecar]
    )  # the body is whole: it stays
    published, plan = download(place)
    assert plan.action == "publish"
    assert target(place).read_bytes() == DATA


# --- write(): its own closed errors, the buffers it takes and the total it was promised ----------
def test_a_guard_that_raises_an_os_error_between_the_blocks_of_a_write_is_a_write_failure(place):
    asked = []

    def guard():
        asked.append(1)
        if len(asked) == 2:
            raise TimeoutError("a deadline that is no closed error")

    with open_sink(target(place), identity_key=IDENTITY, guard=guard) as (sink, _):
        sink.begin(full(3 * 1024 * 1024), "full")
        assert code_of(lambda: sink.write(os.urandom(3 * 1024 * 1024))) == "download_write_failed"
        sink.stop()


def test_a_buffer_of_two_dimensions_is_written_as_its_bytes(place):
    raw = bytes(range(256)) * 4
    grid = memoryview(raw).cast("B", shape=[16, 64])
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(DownloadResponse(200, None, '"t"', "length", len(raw)), "full")
        sink.write(grid)
        sink.complete(terminated=True)
        assert sink.publish(None).bytes == len(raw)
    assert target(place).read_bytes() == raw


def test_a_buffer_that_cannot_be_cast_to_bytes_is_an_invalid_request(place):
    import array

    strided = memoryview(array.array("I", range(10)))[::2]
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(DownloadResponse(200, None, '"t"', "length", 40), "full")
        assert code_of(lambda: sink.write(strided)) == "invalid_request"
        sink.stop()


def test_a_second_write_that_overshoots_the_promised_total_is_refused_at_once(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(DownloadResponse(200, None, '"t"', "length", 1000), "full")
        sink.write(b"x" * 600)
        assert code_of(lambda: sink.write(b"x" * 600)) == "invalid_response"
        assert sink.written == 600  # nothing of the refused piece was written
        sink.stop()


# --- a lock check whose stat fails is a write failure in every method that makes it ---------------
@pytest.mark.parametrize("method", ["begin", "discard", "checkpoint", "complete", "publish"])
def test_a_lock_check_that_fails_is_a_write_failure_in_every_method_that_makes_it(
    place, monkeypatch, method
):
    real = os.stat
    failing = []

    def stat(path, *arguments, **keywords):
        if failing and path == NAMES.lock:
            raise OSError(errno.EIO, "no")
        return real(path, *arguments, **keywords)

    monkeypatch.setattr(download_files.os, "stat", stat)
    if method == "discard":
        stopped_after(place, 100_000)
    if method == "checkpoint":
        monkeypatch.setattr(download_sink, "CHECKPOINT_BYTES", 1000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        if method == "begin":
            failing.append(1)
            assert code_of(lambda: sink.begin(full(), "full")) == "download_write_failed"
        elif method == "discard":
            failing.append(1)
            assert code_of(sink.discard) == "download_write_failed"
        else:
            sink.begin(full(), "full")
            if method == "checkpoint":
                failing.append(1)
                assert code_of(lambda: sink.write(DATA[:2000])) == "download_write_failed"
            else:
                sink.write(DATA)
                if method == "complete":
                    failing.append(1)
                    assert (
                        code_of(lambda: sink.complete(terminated=True)) == "download_write_failed"
                    )
                else:
                    sink.complete(terminated=True)
                    failing.append(1)
                    assert code_of(lambda: sink.publish(None)) == "download_write_failed"
        failing.clear()
        sink.stop()


# --- acceptance 3: a full stage without a sidecar (and what --no-resume does with it) -------------
def test_a_full_stage_without_its_sidecar_is_unverified_and_no_resume_removes_it(place):
    stopped_after(place, 100_000)
    (place / NAMES.sidecar).unlink()
    before = (place / NAMES.stage).read_bytes()
    assert code_of(lambda: download(place)) == "download_partial_unverified"
    assert left(place) == [NAMES.stage]
    assert (place / NAMES.stage).read_bytes() == before
    published, plan = download(place, no_resume=True)
    assert plan.ask is None
    assert published.resumed_from_bytes == 0
    assert target(place).read_bytes() == DATA
    assert left(place) == [NAME]


# --- acceptance 7: Unicode and long target names are safe -----------------------------------------
@pytest.mark.parametrize(
    "name",
    ["a" * 251 + ".bin", "日" * 85, "ağırlık-é.onnx", "model-🙂.pt", "my model v1.onnx", ".hidden"],
    ids=["255 bytes", "255 bytes of CJK", "latin", "emoji", "space", "dot file"],
)
def test_a_long_or_non_ascii_target_name_is_downloaded_and_leaves_nothing(place, name):
    with open_sink(place / name, identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        assert sink.publish(None).bytes == len(DATA)
    assert [p.name for p in place.iterdir()] == [name]
    assert (place / name).read_bytes() == DATA


# --- the end of the body, the report of a resume, and the cleanup after a wrong digest ------------
def test_a_stage_sync_that_fails_at_the_end_of_the_body_records_no_completion(place, monkeypatch):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        sink.write(DATA)

        real, failed = os.fsync, []

        def refuse_once(descriptor):  # the sync of the stage only: the sidecar's own syncs work
            if not failed:
                failed.append(1)
                raise OSError(errno.EIO, "no")
            return real(descriptor)

        monkeypatch.setattr(download_sink.os, "fsync", refuse_once)
        assert code_of(lambda: sink.complete(terminated=True)) == "download_write_failed"
        monkeypatch.undo()
        assert sidecar_of(place).committed_bytes == 0  # still the header record: not "complete"
        sink.stop()


def test_a_resume_from_a_single_byte_is_reported_as_a_resume(place):
    stopped_after(place, 1)
    published, plan = download(place)
    assert plan.resumed_from == 1
    assert published.resumed_from_bytes == 1
    assert published.resumed is True


def test_a_discard_that_meets_a_stage_that_stopped_being_ours_leaves_it_alone(place):
    stopped_after(place, 100_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        assert plan.ask is not None
        os.chmod(place / NAMES.stage, 0o644)
        assert code_of(sink.discard) == "download_partial_unverified"
    assert (place / NAMES.stage).read_bytes() == DATA[:100_000]
    assert (place / NAMES.sidecar).exists()


def test_the_cleanup_after_a_wrong_digest_syncs_the_directory_after_the_removals(
    place, monkeypatch
):
    spy = Spy(monkeypatch)  # before the directory is opened: it names the descriptors it sees
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        mark = len(spy.events)
        assert code_of(lambda: sink.publish("00" * 32)) == "download_integrity_mismatch"
        during = spy.since(mark)
    removals = [event for event in during if event.startswith(("unlink:", "fsync:dir"))]
    assert removals[:3] == ["unlink:stage", "unlink:sidecar", "fsync:dir"], during


def test_a_cleanup_that_fails_after_a_wrong_digest_does_not_hide_the_verdict(place, monkeypatch):
    real = os.unlink

    def failing(path, *, dir_fd=None):
        if path == NAMES.stage:
            raise OSError(errno.EIO, "cannot remove")
        return real(path, dir_fd=dir_fd)

    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        monkeypatch.setattr(download_files.os, "unlink", failing)
        assert code_of(lambda: sink.publish("00" * 32)) == "download_integrity_mismatch"
        monkeypatch.undo()


def test_a_name_swapped_during_the_cleanup_after_a_wrong_digest_does_not_hide_the_verdict(
    place, monkeypatch
):
    real = download_files.entry_of
    armed = []

    def lying(directory, name):
        found = real(directory, name)
        if armed and name == NAMES.sidecar and found is not None:
            return replace(found, inode=found.inode + 1)  # the name now leads to another file
        return found

    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        monkeypatch.setattr(download_files, "entry_of", lying)
        armed.append(1)
        assert code_of(lambda: sink.publish("00" * 32)) == "download_integrity_mismatch"
        monkeypatch.undo()


# --- a checkpoint claims only what was synced; stop never hides a second interrupt; the clock ----
def test_a_stage_sync_that_fails_at_a_checkpoint_claims_nothing(place, monkeypatch):
    monkeypatch.setattr(download_sink, "CHECKPOINT_BYTES", 1000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        real, failed = os.fsync, []

        def refuse_once(descriptor):  # the sync of the stage only: the sidecar's own syncs work
            if not failed:
                failed.append(1)
                raise OSError(errno.EIO, "no")
            return real(descriptor)

        monkeypatch.setattr(download_sink.os, "fsync", refuse_once)
        assert code_of(lambda: sink.write(DATA[:2000])) == "download_write_failed"
        monkeypatch.undo()
        assert sidecar_of(place).committed_bytes == 0  # nothing is claimed that was not synced
        sink.stop()


def test_a_second_interrupt_during_the_stop_is_not_swallowed(place, monkeypatch):
    def interrupted(self):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):  # the user presses Ctrl-C again while it stops
        with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
            sink.begin(full(), "full")
            sink.write(DATA[:5000])
            monkeypatch.setattr(download_sink.DownloadSink, "_checkpoint", interrupted)
            raise KeyError("the first reason to stop")
    monkeypatch.undo()


def test_the_clock_that_is_given_is_the_clock_that_is_used(place):
    from yorunge.domain.capabilities import timestamp

    moment = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    with open_sink(target(place), identity_key=IDENTITY, clock=lambda: moment) as (sink, _):
        sink.begin(full(), "full")
        record = sidecar_of(place)
        assert record.created_at == record.updated_at == timestamp(moment)
        sink.stop()


# --- the start: an interrupt releases what it took; a half-reset sink only stops ------------------
def test_an_interrupt_during_the_start_releases_the_lock_and_the_descriptors(place, monkeypatch):
    def interrupt(name):
        if name == "decided":
            raise KeyboardInterrupt

    before = descriptors()
    monkeypatch.setattr(download_files, "_marker", interrupt)
    enter_value = enter(place)
    with pytest.raises(KeyboardInterrupt):
        enter_value()
    monkeypatch.undo()
    assert descriptors() == before
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):  # not busy
        assert plan.action == "download"
        sink.stop()


def test_a_sink_whose_discard_failed_is_not_driven_any_further(place, monkeypatch):
    stopped_after(place, 100_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):

        def full_disk(*arguments, **keywords):
            raise OSError(errno.ENOSPC, "full")

        monkeypatch.setattr(download_sink, "create_exclusive", full_disk)
        assert code_of(sink.discard) == "download_write_failed"
        monkeypatch.undo()
        assert code_of(lambda: sink.begin(full(), "full")) == "invalid_request"  # no stage is open
        assert code_of(lambda: sink.write(b"x")) == "invalid_request"


def test_a_stage_that_will_not_close_during_a_discard_is_a_write_failure(place, monkeypatch):
    stopped_after(place, 100_000)
    real_open, real_close = os.open, os.close
    stage_descriptors = []

    def opening(path, flags, mode=0o777, *, dir_fd=None):
        descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        if path == NAMES.stage:
            stage_descriptors.append(descriptor)
        return descriptor

    def closing(descriptor):
        real_close(descriptor)
        if descriptor in stage_descriptors:
            stage_descriptors.remove(descriptor)
            raise OSError(errno.EIO, "close failed")

    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        monkeypatch.setattr(download_files.os, "open", opening)
        monkeypatch.setattr(download_files.os, "close", closing)
        stage_descriptors.append(sink._stage)  # the descriptor the start opened
        assert code_of(sink.discard) == "download_write_failed"
        monkeypatch.undo()


# --- a regression in a loop or a lock must fail a test, not hang the run (M0875, M0877, M0259)
def test_a_write_that_writes_nothing_is_a_write_failure_and_never_loops(place, monkeypatch):
    calls = []

    def stalled(descriptor, data):
        calls.append(1)
        if len(calls) > 50:
            raise AssertionError("the writer keeps asking a descriptor that takes nothing")
        return 0

    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        monkeypatch.setattr(download_sink.os, "write", stalled)
        assert code_of(lambda: sink.write(DATA)) == "download_write_failed"
        monkeypatch.undo()
        sink.stop()


def test_a_sidecar_is_written_in_one_call_and_not_in_a_loop_that_does_not_advance(
    place, monkeypatch
):
    real, calls = os.write, []

    def counting(descriptor, data):
        calls.append(1)
        if len(calls) > 20:
            raise AssertionError("an endless write loop")
        return real(descriptor, data)

    monkeypatch.setattr(download_files.os, "write", counting)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        monkeypatch.undo()
        sink.stop()
    assert 1 <= len(calls) <= 3  # one call for the whole record


def test_a_second_download_of_the_same_target_is_busy_and_never_waits(place):
    with open_sink(target(place), identity_key=IDENTITY) as (first, _):
        first.begin(full(), "full")
        first.write(DATA[:1000])
        result = run_with_deadline(lambda: code_of(lambda: download(place)), 10)
        assert result is not None, "the second run waited for the first"
        assert result == ("ok", "download_busy")
        first.stop()


# --- the retry of the lock closes what it let go; the target is synced after the link -------------
def test_a_lock_object_that_was_found_removed_leaks_no_descriptor_on_the_retry(place, monkeypatch):
    lock = place / NAMES.lock
    lock.write_bytes(b"")
    os.chmod(lock, 0o600)
    opened = []

    def marker(name):
        if name == "lock:opened" and not opened:
            opened.append(1)
            lock.unlink()  # the finisher removed it between this run's open and its flock

    download(place)  # warm-up
    target(place).unlink()
    lock.write_bytes(b"")
    os.chmod(lock, 0o600)
    before = descriptors()
    monkeypatch.setattr(download_files, "_marker", marker)
    download(place)
    monkeypatch.undo()
    assert opened
    assert descriptors() == before


def test_the_published_target_is_synced_after_the_link_and_the_cleanup(place, monkeypatch):
    events = []
    real_link, real_unlink, real_sync = os.link, os.unlink, artifact_publisher.full_sync

    def link(*arguments, **keywords):
        events.append("link")
        return real_link(*arguments, **keywords)

    def unlink(path, *, dir_fd=None):
        if path == NAMES.stage:
            events.append("unlink:stage")
        return real_unlink(path, dir_fd=dir_fd)

    def sync(descriptor):
        events.append("full_sync")
        return real_sync(descriptor)

    monkeypatch.setattr(os, "link", link)
    monkeypatch.setattr(download_files.os, "unlink", unlink)
    monkeypatch.setattr(artifact_publisher, "full_sync", sync)
    download(place)
    monkeypatch.undo()
    assert events == ["link", "unlink:stage", "full_sync"]


# --- a lock object that was removed is noticed by begin, discard and stop (M0685, M0769, X07) --
def test_a_lock_object_removed_before_the_answer_stops_the_begin(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        (place / NAMES.lock).unlink()
        assert code_of(lambda: sink.begin(full(), "full")) == "download_busy"
        assert NAMES.sidecar not in left(place)  # no header checkpoint was written


def test_a_lock_object_removed_before_a_discard_leaves_the_pair_alone(place):
    stopped_after(place, 100_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        assert plan.ask is not None
        (place / NAMES.lock).unlink()
        assert code_of(sink.discard) == "download_busy"
    assert sorted(left(place)) == sorted([NAMES.stage, NAMES.sidecar])
    assert sidecar_of(place).committed_bytes == 100_000


def test_a_stop_without_the_lock_object_removes_nothing(place):
    with pytest.raises(KeyError):
        with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
            sink.begin(full(), "full")
            (place / NAMES.lock).unlink()
            raise KeyError(
                "a failure of the engine: the stop must not drop what may be another run's"
            )
    assert sorted(left(place)) == sorted([NAMES.stage, NAMES.sidecar])


# --- a restart begins a new account: digest, time, descriptors ------------------------------------
def test_a_restart_hashes_only_the_new_body_and_dates_its_record_anew(place):
    import hashlib

    from yorunge.domain.capabilities import timestamp

    first = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    second = datetime(2026, 1, 3, 3, 4, 5, tzinfo=UTC)
    with open_sink(target(place), identity_key=IDENTITY, clock=lambda: first) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA[:100_000])
        sink.stop()
    with open_sink(target(place), identity_key=IDENTITY, clock=lambda: second) as (sink, plan):
        assert plan.ask is not None
        sink.begin(full(), "restart")  # the provider ignored the range
        assert sidecar_of(place).created_at == timestamp(second)
        sink.write(DATA)
        sink.complete(terminated=True)
        published = sink.publish(hashlib.sha256(DATA).hexdigest())
    assert published.verification.level == "sha256_matched"
    assert published.sha256 == hashlib.sha256(DATA).hexdigest()


def test_a_discard_closes_the_stage_it_drops(place):
    stopped_after(place, 100_000)
    before = None
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        before = descriptors()
        sink.discard()
        assert descriptors() == before  # one stage closed, one opened
        sink.stop()


# --- a boundary is announced AFTER the effect it names (the matrix kills where it is announced) --
def test_each_boundary_is_announced_after_the_effect_it_names(place, monkeypatch):
    import fcntl

    spy = Spy(monkeypatch)
    problems = []

    def exists(name):
        return (place / name).exists()

    def lock_is_held():
        probe = os.open(place / NAMES.lock, os.O_RDWR | os.O_NONBLOCK)
        try:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return False  # the probe could take it: nobody held it
        except OSError:
            return True
        finally:
            os.close(probe)

    checks = {
        "lock:created": lambda: exists(NAMES.lock),
        "directory:synced": lambda: spy.events[-1] == "fsync:dir",
        "header_checkpoint": lambda: exists(NAMES.sidecar),
        "lock:held": lock_is_held,
        "stage:created": lambda: exists(NAMES.stage),
        "sidecar_tmp:created": lambda: exists(NAMES.sidecar_tmp),
        "sidecar_tmp:written": lambda: (place / NAMES.sidecar_tmp).stat().st_size > 0,
        "sidecar_tmp:synced": lambda: spy.events[-1] == "fsync:tmp",
        "sidecar:replaced": lambda: exists(NAMES.sidecar) and not exists(NAMES.sidecar_tmp),
        "checkpoint:stage_synced": lambda: spy.events[-1] == "fsync:stage",
        "complete:stage_synced": lambda: spy.events[-1] == "fsync:stage",
        "publish:before_link": lambda: not exists(NAME),
        "publish:after_link": lambda: exists(NAME),
        "cleanup:stage": lambda: not exists(NAMES.stage) and exists(NAMES.sidecar),
        "removed:stage": lambda: not exists(NAMES.stage),
        "removed:sidecar": lambda: not exists(NAMES.sidecar),
        "removed:lock": lambda: not exists(NAMES.lock),
        "cleanup:all_removed": lambda: not exists(NAMES.sidecar) and not exists(NAMES.sidecar_tmp),
    }
    seen = set()

    def marker(name):
        if name in checks:
            seen.add(name)
            if not checks[name]():
                problems.append(name)

    monkeypatch.setattr(download_sink, "CHECKPOINT_BYTES", 1000)
    stopped_after(place, 3000)  # a stopped download: the next run removes its pair (--no-resume)
    monkeypatch.setattr(download_files, "_marker", marker)
    download(place, no_resume=True)  # removed:stage/sidecar, a fresh download with checkpoints
    monkeypatch.undo()
    assert not problems, problems
    assert seen == set(checks), sorted(set(checks) - seen)


# --- a descriptor that was closed is not kept as the stage: nothing is closed twice (M0560) ------
def test_a_prefix_mismatch_followed_by_a_failed_removal_closes_each_descriptor_once(
    place, monkeypatch
):
    stopped_after(place, 100_000)
    with (place / NAMES.stage).open("r+b") as stage:
        stage.seek(500)
        stage.write(bytes([DATA[500] ^ 0xFF]))  # local corruption inside the committed prefix
    real_open, real_close, real_unlink = os.open, os.close, os.unlink
    live, wrong = set(), []

    def opening(path, flags, mode=0o777, *, dir_fd=None):
        descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        live.add(descriptor)
        return descriptor

    def closing(descriptor):
        if descriptor not in live:
            wrong.append(descriptor)  # closed twice, or not opened by the sink at all
        live.discard(descriptor)
        return real_close(descriptor)

    def failing(path, *, dir_fd=None):
        if path == NAMES.stage:
            raise OSError(errno.EIO, "cannot remove")
        return real_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(download_files.os, "open", opening)
    monkeypatch.setattr(download_files.os, "close", closing)
    monkeypatch.setattr(download_files.os, "unlink", failing)
    assert code_of(enter(place)) == "download_write_failed"
    monkeypatch.undo()
    assert not wrong, (wrong, live)
    assert not live, (wrong, live)


# --- a restart marks the record stale only once the stage was cut (M0725); a verdict needs no clean
def test_a_truncation_that_fails_on_a_restart_keeps_the_progress_of_the_earlier_run(
    place, monkeypatch
):
    stopped_after(place, 100_000)

    def failing(descriptor, length):
        raise OSError(errno.EIO, "no truncate")

    with pytest.raises(YorungeError) as caught:  # leaving the block with the error: the stop runs
        with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
            assert plan.ask is not None
            monkeypatch.setattr(download_sink.os, "ftruncate", failing)
            sink.begin(full(), "restart")
    monkeypatch.undo()
    assert caught.value.code == "download_write_failed"
    assert sorted(left(place)) == sorted([NAMES.stage, NAMES.sidecar])  # the pair is as it was
    assert sidecar_of(place).committed_bytes == 100_000
    assert (place / NAMES.stage).stat().st_size == 100_000


def test_a_wrong_digest_with_nothing_left_to_clean_still_gives_the_verdict(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        (place / NAMES.sidecar).unlink()
        stage = place / NAMES.stage
        stage.rename(place / "aside")
        stage.write_bytes(b"ANOTHER FILE OF OURS")  # not the stage that was written
        stage.chmod(0o600)
        assert code_of(lambda: sink.publish("00" * 32)) == "download_integrity_mismatch"
    assert stage.read_bytes() == b"ANOTHER FILE OF OURS"


# --- a stop before the answer, an interrupt at the completion boundary, the timed full sync ------
def test_a_stop_before_the_answer_without_the_lock_object_removes_nothing(place):
    with pytest.raises(KeyError):
        with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
            assert plan.ask is None
            (place / NAMES.lock).unlink()
            raise KeyError("the request failed; the lock object is gone")
    assert left(place) == [NAMES.stage]  # the empty stage may be another run's: it stays


@pytest.mark.parametrize("tag", [None, TAG], ids=["no tag", "strong tag"])
def test_an_interrupt_at_the_completion_boundary_keeps_the_whole_stage(place, monkeypatch, tag):
    def interrupt(name):
        if name == "completion_checkpoint":
            raise KeyboardInterrupt

    monkeypatch.setattr(download_files, "_marker", interrupt)
    with pytest.raises(KeyboardInterrupt):
        with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
            sink.begin(full(etag=tag), "full")
            sink.write(DATA)
            sink.complete(terminated=True)
    monkeypatch.undo()
    assert sorted(left(place)) == sorted([NAMES.stage, NAMES.sidecar])
    published, plan = download(place)
    assert plan.action == "publish"
    assert target(place).read_bytes() == DATA


def test_the_full_sync_happens_between_the_compared_and_the_published_boundaries(
    place, monkeypatch
):
    events = []
    real = download_sink.full_sync

    def marker(name):
        if name in ("compared", "publish:synced"):
            events.append(name)

    def synced(handle):
        events.append("full_sync")
        return real(handle)

    monkeypatch.setattr(download_files, "_marker", marker)
    monkeypatch.setattr(download_sink, "full_sync", synced)
    download(place)
    monkeypatch.undo()
    assert events == ["compared", "full_sync", "publish:synced"]


def test_the_stage_truncated_boundary_is_announced_after_the_cut(place, monkeypatch):
    stopped_after(place, 100_000)
    with (place / NAMES.stage).open("ab") as stage:
        stage.write(b"bytes written after the last checkpoint, then the process was killed")
    sizes = []

    def marker(name):
        if name == "stage:truncated":
            sizes.append((place / NAMES.stage).stat().st_size)

    monkeypatch.setattr(download_files, "_marker", marker)
    download(place)
    monkeypatch.undo()
    assert sizes == [100_000]


def test_the_compared_boundary_is_announced_only_when_the_digest_was_accepted(place, monkeypatch):
    names = []
    monkeypatch.setattr(download_files, "_marker", names.append)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        names.clear()
        assert code_of(lambda: sink.publish("00" * 32)) == "download_integrity_mismatch"
    monkeypatch.undo()
    assert "compared" not in names
    assert "publish:before_link" not in names


# --- the lock is checked on the continue branch too; a refused byte is not written (M0754, M0891) -
def test_a_lock_object_removed_before_a_continue_stops_the_begin(place):
    stopped_after(place, 100_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        assert plan.ask is not None
        (place / NAMES.lock).unlink()
        answer = DownloadResponse(
            206, ContentRange(100_000, len(DATA) - 1, len(DATA)), TAG, "length", len(DATA) - 100_000
        )
        assert code_of(lambda: sink.begin(answer, "continue")) == "download_busy"


def test_a_byte_past_the_limit_is_refused_before_it_is_written(place, monkeypatch):
    monkeypatch.setattr(download_sink, "MAX_DOWNLOAD_BYTES", 1000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, _):
        sink.begin(DownloadResponse(200, None, TAG, "chunked", None), "full")
        sink.write(DATA[:1000])
        assert code_of(lambda: sink.write(b"x")) == "download_limit_exceeded"
        assert (
            place / NAMES.stage
        ).stat().st_size == 1000  # the refused byte never reached the file
        sink.stop()


# --- the body is whole once complete() accepts it: nothing later in it drops the stage -----------
@pytest.mark.parametrize(
    "response",
    [
        DownloadResponse(200, None, None, "chunked", None),
        DownloadResponse(200, None, None, "length", len(DATA)),
        full(),
    ],
    ids=["chunked, no tag", "length, no tag", "length, strong tag"],
)
@pytest.mark.parametrize("failure", [KeyboardInterrupt, OSError], ids=["interrupt", "io error"])
def test_a_failure_inside_complete_never_drops_a_body_that_is_whole(
    place, monkeypatch, response, failure
):
    state = {"in_completion": False}

    def marker(name):
        if name == "complete:stage_synced" and state["in_completion"]:
            raise failure(errno.EIO, "after the stage sync") if failure is OSError else failure()

    monkeypatch.setattr(download_files, "_marker", marker)
    with pytest.raises((YorungeError, KeyboardInterrupt)):  # the stop runs when the block is left
        with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
            sink.begin(response, "full")
            sink.write(DATA)
            state["in_completion"] = True
            sink.complete(terminated=True)
    monkeypatch.undo()
    assert sorted(left(place)) == sorted([NAMES.stage, NAMES.sidecar])  # not dropped: whole
    assert (place / NAMES.stage).read_bytes() == DATA
    published, _ = download(place)  # and the next run finishes without anyone deleting anything
    assert target(place).read_bytes() == DATA
    assert left(place) == [NAME]
