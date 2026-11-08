"""The publisher's edges: closed families, error precedence, notes, hostile spellings and stages.

The main file drives the publisher through its faults; these tests pin the choices a plausible
slip would undo: the order of the looks before the link, what a note says and how often, which
descriptor a helper closes with which code, and the stage that is not what it is named.
"""

import errno
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from tests.integration.test_artifact_publisher import (
    CODES,
    CONTENT,
    KILL,
    NAME,
    PREFIX,
    ArtifactCodes,
    ArtifactPublisher,
    Place,
    PublicationState,
    failure,
    publisher,
    staged,
)
from tests.integration.test_artifact_publisher import place as place
from yorunge.adapters.input_files import close_descriptor, owned_descriptor
from yorunge.domain.errors import MESSAGES, YorungeError

FIELDS = ["failed", "exists", "uncertain", "changed", "unreadable"]


def raising(error):
    def raise_it(*arguments, **keywords):
        raise error

    return raise_it


# --- a family of codes is closed ------------------------------------------------------------------


@pytest.mark.parametrize("field", FIELDS)
def test_every_code_of_a_family_must_be_a_closed_one(field):
    with pytest.raises((ValueError, KeyError)):
        ArtifactCodes(**{**CODES.__dict__, field: "no_such_code"})


@pytest.mark.parametrize(
    "uncertain", ["manifest_mismatch", "request_cancelled", "input_changed", "approval_required"]
)
def test_the_uncertain_code_must_exit_exactly_5(uncertain):
    with pytest.raises(ValueError):
        ArtifactCodes(**{**CODES.__dict__, "uncertain": uncertain})


# --- what is looked at before the link, and in which order ---------------------------------------


def test_a_source_that_changed_wins_over_a_stage_of_the_wrong_size(place):
    def changed():
        raise YorungeError("input_changed")

    pub, state = publisher(place, check_source=changed)
    name, descriptor = staged(place)
    try:
        error = failure(lambda: pub.publish_stage(name, descriptor, len(CONTENT) + 1))
    finally:
        os.close(descriptor)
    assert error.code == "input_changed"
    assert state.attempted is False


def test_a_place_that_changed_wins_over_a_stage_of_the_wrong_size(place):
    place.changed = True
    pub, state = publisher(place)
    name, descriptor = staged(place)
    try:
        error = failure(lambda: pub.publish_stage(name, descriptor, len(CONTENT) + 1))
    finally:
        os.close(descriptor)
    assert error.code == "input_changed"
    assert state.attempted is False
    assert not place.target.exists()
    assert place.leftovers() == []


def test_a_stage_descriptor_that_is_not_a_regular_file_is_changed_before_the_link(place):
    # A FIFO whose name and descriptor agree is still not an artifact.
    name = ".stream-fifo.tmp"
    os.mkfifo(place.directory / name, 0o600)
    descriptor = os.open(name, os.O_RDWR | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=place.descriptor)
    try:
        pub, state = publisher(place)
        error = failure(lambda: pub.publish_stage(name, descriptor, 0))
    finally:
        os.close(descriptor)
    assert error.code == CODES.changed
    assert state.attempted is False
    assert not place.target.exists()
    assert place.leftovers() == []  # it was the publisher's stage: removed by identity


def test_a_write_that_reports_one_byte_too_many_once_is_failed(place, monkeypatch):
    real, calls = os.write, []

    def write(descriptor, data):
        calls.append(1)
        return len(data) + 1 if len(calls) == 1 else real(descriptor, data)

    monkeypatch.setattr(os, "write", write)
    pub, _ = publisher(place)
    assert failure(lambda: pub.publish_bytes(b"x" * (3 * 1024 * 1024))).code == CODES.failed
    assert len(calls) == 1  # stopped at the lie


# --- after the link: the target is looked at again ------------------------------------------------


def test_a_target_replaced_by_an_identical_copy_during_the_final_sync_is_uncertain(place):
    # Same size, mode, owner, mtime and one link, on another inode: only the identity tells.
    pub, state = publisher(place)
    sync, calls = pub._sync, []

    def swapping(descriptor):
        sync(descriptor)
        if state.attempted and not calls:  # the file sync after the link
            calls.append(1)
            before = place.target.stat()
            data = place.target.read_bytes()
            place.target.unlink()
            place.target.write_bytes(data)
            os.chmod(place.target, 0o600)
            os.utime(place.target, ns=(before.st_atime_ns, before.st_mtime_ns))

    pub._sync = swapping
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.uncertain
    assert calls == [1]


def test_a_target_whose_mode_changes_during_the_final_sync_is_uncertain(place):
    pub, state = publisher(place)
    sync, calls = pub._sync, []

    def chmod_after(descriptor):
        sync(descriptor)
        if state.attempted and not calls:
            calls.append(1)
            os.chmod(place.target, 0o644)

    pub._sync = chmod_after
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.uncertain


def test_an_interrupt_after_the_link_is_the_familys_uncertain_not_the_interrupt(place):
    pub, state = publisher(place)
    original = pub._check_target

    def interrupted(*arguments):
        if state.attempted:
            raise KeyboardInterrupt()
        return original(*arguments)

    pub._check_target = interrupted
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert isinstance(error, YorungeError)
    assert error.code == CODES.uncertain
    assert place.target.read_bytes() == CONTENT


def test_a_stage_swapped_for_a_symlink_to_a_foreign_file_just_before_the_link_is_never_linked(
    place,
):
    # link() must not follow the symlink: a foreign file would otherwise get a second name here.
    victim = place.directory / "victim.txt"
    victim.write_bytes(b"VICTIM")
    pub, state = publisher(place)
    original = pub._publish_link

    def swap():
        stage = place.directory / (pub.stage or "")
        stage.unlink()
        stage.symlink_to(victim)
        original()

    pub._publish_link = swap
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.code == CODES.uncertain
    assert state.attempted is True
    assert victim.read_bytes() == b"VICTIM"
    assert victim.stat().st_nlink == 1


# --- notes: said once, said only where they are true ----------------------------------------------


def test_an_error_that_replaces_another_carries_no_cleanup_note_when_the_cleanup_succeeded(place):
    pub, _ = publisher(place)

    def disk_full(*arguments):
        raise OSError(errno.ENOSPC, "PRIVATE")

    pub._sync = disk_full
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.code == CODES.failed
    assert place.leftovers() == []
    assert not getattr(error, "__notes__", ())


def test_a_failed_cleanup_note_is_not_doubled_on_an_error_that_is_raised_unchanged(
    place, monkeypatch
):
    pub, _ = publisher(place)
    pub._check_stage = raising(YorungeError("execution_timeout"))
    monkeypatch.setattr(os, "unlink", raising(OSError(errno.EIO, "")))
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.code == "execution_timeout"
    assert error.__notes__.count(MESSAGES[CODES.failed]) == 1


def test_a_failed_cleanup_note_is_added_once_when_the_close_note_is_already_there(
    place, monkeypatch
):
    # The close note and the cleanup note are the same sentence: it must not be written twice.
    stage_descriptors, real_open, real_close = set(), os.open, os.close

    def opening(path, *arguments, **keywords):
        descriptor = real_open(path, *arguments, **keywords)
        if isinstance(path, str) and path.startswith(PREFIX):
            stage_descriptors.add(descriptor)
        return descriptor

    def closing(descriptor):
        real_close(descriptor)
        if descriptor in stage_descriptors:
            raise OSError(errno.EIO, "PRIVATE")

    monkeypatch.setattr(os, "open", opening)
    monkeypatch.setattr(os, "close", closing)
    monkeypatch.setattr(os, "unlink", raising(OSError(errno.EIO, "")))
    pub, _ = publisher(place)
    pub._check_stage = raising(YorungeError("execution_timeout"))
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.__notes__.count(MESSAGES[CODES.failed]) == 1


def test_a_stage_that_may_remain_is_not_said_to_mean_nothing_was_published_when_it_is_uncertain(
    place, monkeypatch
):
    # The note says "not published"; an uncertain publication says the opposite. A stranded stage
    # beside an uncertain outcome is the outcome's own message to carry.
    pub, state = publisher(place)
    pub._check_target = raising(KeyboardInterrupt())
    real_unlink = os.unlink

    def unlink(path, *arguments, **keywords):
        if isinstance(path, str) and path.startswith(PREFIX):
            raise OSError(errno.EIO, "PRIVATE")
        return real_unlink(path, *arguments, **keywords)

    monkeypatch.setattr(os, "unlink", unlink)
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert state.attempted is True
    assert isinstance(error, YorungeError)
    assert error.code == CODES.uncertain
    assert MESSAGES[CODES.failed] not in getattr(error, "__notes__", ())


def test_a_bug_in_a_sinks_discard_is_not_swallowed(place):
    class Buggy(ArtifactPublisher):
        def _discard(self, error):
            raise RuntimeError("bug in the sink")

    pub = Buggy(place, PublicationState(CODES), prefix=PREFIX)
    pub._check_stage = raising(OSError(errno.EIO, "PRIVATE"))
    with pytest.raises(RuntimeError):
        pub.publish_bytes(CONTENT)


def test_a_stage_that_exists_but_whose_identity_is_unknown_leaves_the_familys_note(
    place, monkeypatch
):
    # The first look at the new stage fails: the name is there, whose file it is was never learned.
    pub, _ = publisher(place)
    real, calls = os.fstat, []

    def fstat(handle):
        calls.append(handle)
        if len(calls) == 1:
            raise OSError(errno.EIO, "PRIVATE")
        return real(handle)

    monkeypatch.setattr(os, "fstat", fstat)
    error = failure(lambda: pub.publish_bytes(CONTENT))
    monkeypatch.undo()
    assert error.code == CODES.failed
    assert len(place.leftovers()) == 1  # the empty stage is still there
    assert MESSAGES[CODES.failed] in error.__notes__


# --- the helpers that moved: the caller's code, without the OS error ------------------------------


def test_the_moved_descriptor_helpers_report_the_callers_code_without_the_os_error(monkeypatch):
    real_close = os.close

    def failing(descriptor):
        real_close(descriptor)
        raise OSError(errno.EIO, "PRIVATE")

    monkeypatch.setattr(os, "close", failing)
    open_value = os.open("/dev/null", os.O_RDONLY)
    with pytest.raises(YorungeError) as caught:
        close_descriptor(open_value, code="manifest_write_failed")
    assert caught.value.code == "manifest_write_failed"
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    with pytest.raises(YorungeError) as caught:
        with owned_descriptor(os.open("/dev/null", os.O_RDONLY), close_code="transport_failed"):
            pass
    assert caught.value.code == "transport_failed"
    assert caught.value.__suppress_context__ is True
    with pytest.raises(RuntimeError) as caught:  # another error in flight keeps its place
        with owned_descriptor(os.open("/dev/null", os.O_RDONLY), close_code="transport_failed"):
            raise RuntimeError("the real one")
    assert caught.value.__notes__ == [MESSAGES["transport_failed"]]
    monkeypatch.undo()


# --- a stage that is not what its name says -------------------------------------------------------


def test_a_stage_that_is_the_target_under_another_spelling_never_deletes_the_target(place):
    # On a case-insensitive volume (the macOS default) the name guard compares spellings only:
    # the cleanup after EEXIST would then unlink the one directory entry both names stand for.
    (place.directory / "probe").write_bytes(b"x")
    if not (place.directory / "PROBE").exists():
        pytest.skip("the filesystem is case-sensitive")
    place.name = "Artifact.bin"
    target = place.directory / "Artifact.bin"
    target.write_bytes(b"PUBLISHED EARLIER")
    os.chmod(target, 0o600)
    descriptor = os.open("artifact.bin", os.O_RDWR | os.O_NOFOLLOW, dir_fd=place.descriptor)
    try:
        pub, _ = publisher(place)
        error = failure(
            lambda: pub.publish_stage("artifact.bin", descriptor, len(b"PUBLISHED EARLIER"))
        )
    finally:
        os.close(descriptor)
    assert target.read_bytes() == b"PUBLISHED EARLIER", "the target was deleted by the cleanup"
    assert isinstance(error, (ValueError, YorungeError))


# --- the kill matrix, from the stream's side: the next run republishes its stage ------------------


def names(directory):
    return sorted(p.name for p in directory.iterdir())


@pytest.mark.parametrize(
    "point,published",
    [
        ("before_link", False),
        ("after_link", True),
        ("after_cleanup", True),
        ("after_directory_sync", True),
    ],
)
def test_after_a_kill_the_streams_stage_is_republished_or_refused_and_the_target_inode_is_kept(
    tmp_path, point, published
):
    directory = tmp_path / "place"
    directory.mkdir()
    repository = str(Path(__file__).resolve().parents[2])
    environment = {**os.environ, "PYTHONPATH": os.pathsep.join([repository, *sys.path])}
    run = subprocess.run(
        [sys.executable, "-c", KILL, point, "stage", str(directory)],
        env=environment,
        cwd=repository,
        capture_output=True,
        timeout=60,
    )
    assert run.returncode == -signal.SIGKILL, run.stderr.decode()[-400:]
    target = directory / NAME
    inode = target.stat().st_ino if published else None
    leftovers = [name for name in names(directory) if name != NAME]
    again = Place(directory)
    try:
        pub, _ = publisher(again)
        if not leftovers:  # the stage was cleaned up before the kill
            assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.exists
        else:
            (stage,) = leftovers
            descriptor = os.open(stage, os.O_RDWR | os.O_NOFOLLOW, dir_fd=again.descriptor)
            try:
                if published:  # target and stage are two names of one file
                    error = failure(lambda: pub.publish_stage(stage, descriptor, len(CONTENT)))
                    assert error.code == CODES.changed
                else:  # the finished stage of a killed stream is published by the next run
                    pub.publish_stage(stage, descriptor, len(CONTENT))
                    assert target.read_bytes() == CONTENT
                    assert names(directory) == [NAME]
            finally:
                os.close(descriptor)
    finally:
        again.close()
    if published:
        assert target.stat().st_ino == inode
        assert target.read_bytes() == CONTENT
