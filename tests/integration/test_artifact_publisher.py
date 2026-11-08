"""The common artifact publisher, under an error family of its own (not the manifest's).

The principle is the manifest's: a private stage next to the target, verified, hard-linked
exclusively, cleaned up by identity, synced; a failure before the link is definite, one after it is
honest doubt. These tests give the publisher a family that is not the manifest's (stand-in codes,
so that nothing can pass by accident on the manifest's) and a directory of its own, and exercise
both entries: content held in memory, and a stage a stream wrote itself.
"""

import asyncio
import errno
import os
import signal
import stat
import subprocess
import sys
import textwrap
import traceback
import uuid
from pathlib import Path

import pytest

from yorunge.adapters import artifact_publisher
from yorunge.adapters.artifact_publisher import (
    LINK_REFUSED,
    ArtifactCodes,
    ArtifactPublisher,
    PublicationState,
)
from yorunge.adapters.local_files import full_sync
from yorunge.domain.errors import MESSAGES, YorungeError

CODES = ArtifactCodes(
    failed="transport_failed",
    exists="operation_conflict",
    uncertain="operation_uncertain",
    changed="state_changed",
    unreadable="input_invalid",
)
CONTENT = b"the artifact " * 1000
NAME = "artifact.bin"
PREFIX = ".artifact-"


class Budget:
    def __init__(self):
        self.checks, self.fail_after = 0, None

    def check(self):
        self.checks += 1
        if self.fail_after is not None and self.checks > self.fail_after:
            raise YorungeError("execution_timeout")


class Place:
    """A directory held open, the target's name in it, a budget and a place that can change."""

    def __init__(self, directory):
        self.directory, self.name = Path(directory), NAME
        self.descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        self.budget, self.rechecks, self.changed = Budget(), 0, False
        self.recheck_hook = None

    def recheck(self):
        self.rechecks += 1
        if self.recheck_hook is not None:
            self.recheck_hook()
        if self.changed:
            raise YorungeError("input_changed")

    def names(self):
        return sorted(p.name for p in self.directory.iterdir())

    def close(self):
        os.close(self.descriptor)

    @property
    def target(self):
        return self.directory / NAME

    def leftovers(self):
        return sorted(p.name for p in self.directory.iterdir() if p.name != NAME)


@pytest.fixture
def place(tmp_path):
    held = Place(tmp_path)
    yield held
    held.close()


def publisher(place, check_source=lambda: None):
    state = PublicationState(CODES)
    return ArtifactPublisher(place, state, check_source, prefix=PREFIX), state


def failure(action):
    with pytest.raises(BaseException) as error:
        action()
    return error.value


def staged(place, content=CONTENT, name=".stream-0.tmp"):
    """What a stream does before the publisher: its own stage, filled and synced."""
    descriptor = os.open(
        name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=place.descriptor
    )
    os.write(descriptor, content)
    full_sync(descriptor)
    return name, descriptor


def publish_stage(place, pub, content=CONTENT):
    name, descriptor = staged(place, content)
    try:
        pub.publish_stage(name, descriptor, len(content))
    finally:
        os.close(descriptor)


# --- content in memory ---------------------------------------------------------------------------


def test_content_is_published_as_a_private_regular_file_with_nothing_left_behind(place):
    pub, state = publisher(place)
    pub.publish_bytes(CONTENT)
    info = place.target.stat()
    assert place.target.read_bytes() == CONTENT
    assert stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1
    assert place.leftovers() == [] and state.attempted is True
    assert place.rechecks >= 3 and place.budget.checks >= 5  # the place and the budget were watched


def test_a_taken_name_is_the_familys_exists_and_nothing_is_replaced(place):
    place.target.write_bytes(b"someone else's")
    pub, state = publisher(place)
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert isinstance(error, YorungeError) and error.code == CODES.exists
    assert place.target.read_bytes() == b"someone else's" and place.leftovers() == []
    assert state.attempted is False


def test_a_dangling_symlink_is_a_taken_name(place):
    place.target.symlink_to("nowhere")
    pub, _ = publisher(place)
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.exists
    assert place.target.is_symlink() and place.leftovers() == []


def test_a_name_taken_after_the_first_look_is_exists_and_not_uncertain(place):
    pub, state = publisher(place)
    original = pub._publish_link

    def race():
        place.target.write_bytes(b"the other owner")
        original()

    pub._publish_link = race
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.code == CODES.exists and state.attempted is False  # definite: not created
    assert place.target.read_bytes() == b"the other owner" and place.leftovers() == []


@pytest.mark.parametrize("entry", ["bytes", "stage"])
@pytest.mark.parametrize(
    "number",
    sorted(LINK_REFUSED),
    ids=[errno.errorcode[number] for number in sorted(LINK_REFUSED)],
)
def test_a_link_the_kernel_refused_made_no_entry_and_is_the_familys_failed(
    place, monkeypatch, number, entry
):
    # No hard links on the volume, no permission, no room, another volume: ``link`` either made an
    # entry or failed, so the target certainly does not exist and nothing is uncertain.
    def refuse(*arguments, **keywords):
        raise OSError(number, "PRIVATE-PATH-NEVER-PRINT")

    monkeypatch.setattr(os, "link", refuse)
    pub, state = publisher(place)
    error = failure(lambda: entry_publish(place, pub, entry))
    assert error.code == CODES.failed and state.attempted is False
    assert "PRIVATE-PATH" not in str(error.envelope()) and error.__context__ is None
    assert not place.target.exists()


@pytest.mark.parametrize("step", ["_sync", "_write", "_check_stage"])
def test_a_failure_before_the_link_is_the_familys_failed_and_creates_no_target(place, step):
    pub, state = publisher(place)

    def denied(*arguments):
        raise OSError(errno.ENOSPC, "PRIVATE-PATH-NEVER-PRINT")

    setattr(pub, step, denied)
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.code == CODES.failed and "PRIVATE-PATH" not in str(error.envelope())
    assert not place.target.exists() and place.leftovers() == [] and state.attempted is False


def test_a_zero_length_write_is_failed(place, monkeypatch):
    monkeypatch.setattr(os, "write", lambda *a: 0)
    place.budget.fail_after = 50  # a regression fails here, it does not spin
    pub, _ = publisher(place)
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.failed
    assert not place.target.exists() and place.leftovers() == []
    assert place.budget.checks < 50  # it was the guard that stopped it


def test_short_writes_still_complete_the_file(place, monkeypatch):
    original, sizes = os.write, []

    def short(descriptor, data):
        sizes.append(original(descriptor, data[:7]))
        return sizes[-1]

    monkeypatch.setattr(os, "write", short)
    pub, _ = publisher(place)
    pub.publish_bytes(CONTENT)
    assert len(sizes) > 100 and place.target.read_bytes() == CONTENT


@pytest.mark.parametrize("step", ["_sync", "_check_target"])
def test_a_failure_after_the_link_is_the_familys_uncertain_and_the_target_stays(place, step):
    pub, state = publisher(place)
    original, calls = getattr(pub, step), []

    def late(*arguments):
        calls.append(arguments)
        if state.attempted:  # only once the link was attempted
            raise OSError(errno.EIO, "PRIVATE-PATH-NEVER-PRINT")
        return original(*arguments)

    setattr(pub, step, late)
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.code == CODES.uncertain and "PRIVATE-PATH" not in str(error.envelope())
    assert state.attempted is True and place.target.read_bytes() == CONTENT


def test_an_identity_failure_after_the_link_is_uncertain_not_changed(place):
    pub, _ = publisher(place)
    original = pub._publish_link

    def swap():
        original()
        place.target.unlink()  # the target is replaced by something else after the link
        place.target.write_bytes(b"replaced")

    pub._publish_link = swap
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.uncertain
    assert place.target.read_bytes() == b"replaced"  # never overwritten by the publisher


def test_a_cancelled_task_after_the_link_carries_the_uncertainty_note(place):
    pub, state = publisher(place)
    original = pub._check_target

    def cancelled(*arguments):
        if state.attempted:
            raise asyncio.CancelledError()
        return original(*arguments)

    pub._check_target = cancelled
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert isinstance(error, asyncio.CancelledError)
    assert MESSAGES[CODES.uncertain] in error.__notes__
    assert place.target.read_bytes() == CONTENT


def test_a_cancelled_task_before_the_link_has_no_note_and_leaves_no_stage(place):
    pub, state = publisher(place)

    def cancelled():
        raise asyncio.CancelledError()

    pub._publish_link = cancelled
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert isinstance(error, asyncio.CancelledError) and not getattr(error, "__notes__", ())
    assert state.attempted is False and not place.target.exists() and place.leftovers() == []


def test_an_interrupt_before_the_link_is_passed_on_and_removes_the_stage(place):
    pub, _ = publisher(place)
    pub._check_stage = lambda written: (_ for _ in ()).throw(KeyboardInterrupt())
    assert isinstance(failure(lambda: pub.publish_bytes(CONTENT)), KeyboardInterrupt)
    assert not place.target.exists() and place.leftovers() == []


def test_a_unicode_error_before_the_link_is_the_familys_unreadable(place):
    pub, _ = publisher(place)
    pub._check_stage = lambda written: (_ for _ in ()).throw(UnicodeError("PRIVATE"))
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.code == CODES.unreadable and not place.target.exists()


def test_a_stage_that_was_substituted_is_changed_and_the_foreign_file_is_not_removed(place):
    pub, _ = publisher(place)
    original = pub._check_stage

    def substitute(written):
        stage = place.directory / pub.stage
        stage.unlink()
        stage.write_bytes(b"a foreign file under the stage's name")
        os.chmod(stage, 0o600)
        original(written)

    pub._check_stage = substitute
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.code == CODES.changed and not place.target.exists()
    (kept,) = place.leftovers()  # not the publisher's to remove: its identity is not ours
    assert (place.directory / kept).read_bytes() == b"a foreign file under the stage's name"
    assert MESSAGES[CODES.failed] in error.__notes__


def test_a_stage_with_another_mode_is_changed(place):
    pub, _ = publisher(place)
    original = pub._check_stage

    def chmod(written):
        os.chmod(place.directory / pub.stage, 0o644)
        original(written)

    pub._check_stage = chmod
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.changed
    assert not place.target.exists() and place.leftovers() == []


def test_a_file_system_that_names_the_inode_with_the_first_byte_still_lets_a_refused_stage_go(
    place, monkeypatch
):
    # FAT and exFAT: the inode number of an empty file is a placeholder that changes once a byte is
    # written, so an identity learned before the write would never match the stage again.
    real_identity, real_write = artifact_publisher.identity, ArtifactPublisher._write
    written = []

    def identity(info):
        device, inode = real_identity(info)
        return (device, inode) if written else (device, 2**64 - 25)

    def write(self, descriptor, content):
        real_write(self, descriptor, content)
        written.append(True)

    monkeypatch.setattr(artifact_publisher, "identity", identity)
    monkeypatch.setattr(ArtifactPublisher, "_write", write)
    pub, _ = publisher(place)
    original = pub._check_stage

    def chmod(info):
        os.chmod(place.directory / pub.stage, 0o644)  # the mode a FAT volume would have shown
        original(info)

    pub._check_stage = chmod
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.changed
    assert not place.target.exists() and place.leftovers() == []


def test_a_write_that_fails_on_a_volume_whose_inode_drifts_still_lets_the_stage_go(
    place, monkeypatch
):
    # A real FAT16 volume names the empty file with one placeholder inode at creation and another
    # once a write was attempted (even one that stored no byte, such as a full volume's ENOSPC):
    # the identity learned at creation no longer names the stage, and the stage would be stranded.
    real_identity = artifact_publisher.identity
    attempted = []

    def identity(info):
        device, inode = real_identity(info)
        return (device, inode) if attempted else (device, 2**64 - 57)

    def write(self, descriptor, content):
        attempted.append(True)
        raise OSError(errno.ENOSPC, "PRIVATE-PATH")

    monkeypatch.setattr(artifact_publisher, "identity", identity)
    monkeypatch.setattr(ArtifactPublisher, "_write", write)
    pub, state = publisher(place)
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.failed
    assert not place.target.exists() and place.leftovers() == [] and state.attempted is False


def test_an_interrupt_that_lands_while_the_stage_is_being_created_does_not_strand_it(
    place, monkeypatch
):
    """The kernel made the file, then the signal handler raised KeyboardInterrupt from the very
    call that returns the descriptor: without the hold, the name is not yet the publisher's."""
    real = artifact_publisher.os.open

    def created_then_signalled(path, flags, *arguments, **keywords):
        descriptor = real(path, flags, *arguments, **keywords)
        if str(path).startswith(PREFIX):
            try:
                signal.raise_signal(signal.SIGINT)  # the handler runs before this call returns
            except BaseException:
                os.close(descriptor)
                raise
        return descriptor

    monkeypatch.setattr(artifact_publisher.os, "open", created_then_signalled)
    pub, state = publisher(place)
    with pytest.raises(KeyboardInterrupt):
        pub.publish_bytes(CONTENT)
    assert place.leftovers() == [] and not place.target.exists() and state.attempted is False


def test_the_signal_held_back_while_the_stage_is_made_is_delivered_once_it_is_ours(
    place, monkeypatch
):
    # A SIGINT that arrives between the create and the end of the hold is raised when the hold is
    # lifted, with the stage recorded (so cleaned up) and the descriptor closed (no leak).
    real_mask = artifact_publisher.signal.pthread_sigmask
    before = len(os.listdir("/dev/fd"))

    def mask(how, signals):
        previous = real_mask(how, signals)
        if how == signal.SIG_SETMASK:  # the lift of the hold: the pending signal arrives here
            raise KeyboardInterrupt
        return previous

    monkeypatch.setattr(artifact_publisher.signal, "pthread_sigmask", mask)
    pub, _ = publisher(place)
    with pytest.raises(KeyboardInterrupt):
        pub.publish_bytes(CONTENT)
    monkeypatch.undo()
    assert place.leftovers() == [] and len(os.listdir("/dev/fd")) == before


def test_a_stage_with_a_second_link_is_changed_and_the_foreign_link_stays(place):
    pub, _ = publisher(place)
    original = pub._check_stage

    def link(written):
        os.link(place.directory / pub.stage, place.directory / "second-name")
        original(written)

    pub._check_stage = link
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.changed
    assert not place.target.exists() and place.leftovers() == ["second-name"]


@pytest.mark.parametrize("entry", ["bytes", "stage"])
def test_a_place_that_changed_before_the_link_is_the_error_of_its_own_and_creates_nothing(
    place, entry
):
    # The source look comes right before the place's: it is where the place moves.
    pub, state = publisher(place, check_source=lambda: setattr(place, "changed", True))
    error = failure(
        lambda: publish_stage(place, pub) if entry == "stage" else pub.publish_bytes(CONTENT)
    )
    assert error.code == "input_changed" and state.attempted is False
    assert not place.target.exists() and place.leftovers() == []


@pytest.mark.parametrize("entry", ["bytes", "stage"])
def test_a_place_that_changed_after_the_link_is_uncertain_and_the_target_stays(place, entry):
    pub, state = publisher(place)
    place.recheck_hook = lambda: setattr(place, "changed", state.attempted)
    error = failure(
        lambda: publish_stage(place, pub) if entry == "stage" else pub.publish_bytes(CONTENT)
    )
    assert error.code == CODES.uncertain and place.target.read_bytes() == CONTENT


def test_a_source_that_changed_stops_before_the_link(place):
    def changed():
        raise YorungeError("input_changed")

    pub, state = publisher(place, check_source=changed)
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == "input_changed"
    assert not place.target.exists() and place.leftovers() == [] and state.attempted is False


def test_an_exhausted_budget_stops_the_publication_and_removes_the_stage(place):
    place.budget.fail_after = 3
    pub, _ = publisher(place)
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == "execution_timeout"
    assert not place.target.exists() and place.leftovers() == []


# --- the seams are really called -----------------------------------------------------------------


@pytest.mark.parametrize("entry", ["bytes", "stage"])
def test_every_seam_is_called_on_the_common_path_in_order(place, entry):
    pub, _ = publisher(place)
    calls = []
    for name in ("_check_stage", "_publish_link", "_check_target", "_remove_stage", "_sync"):
        original = getattr(pub, name)

        def traced(*arguments, original=original, name=name):
            calls.append(name)
            return original(*arguments)

        setattr(pub, name, traced)
    if entry == "bytes":
        pub.publish_bytes(CONTENT)
        expected = ["_sync", "_check_stage", "_publish_link", "_check_target"]
        expected += ["_remove_stage", "_sync", "_check_target"]
    else:
        publish_stage(place, pub)
        expected = ["_check_stage", "_publish_link", "_check_target", "_remove_stage"]
        expected += ["_sync", "_check_target"]
    assert calls == expected  # a seam that is not called on this path is a hollow green


# --- a stage the stream wrote itself --------------------------------------------------------------


def test_a_staged_stream_is_published_exclusively_and_its_stage_is_removed(place):
    pub, state = publisher(place)
    publish_stage(place, pub)
    info = place.target.stat()
    assert place.target.read_bytes() == CONTENT and place.leftovers() == []
    assert stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1 and state.attempted


def test_a_staged_stream_never_replaces_a_taken_name_and_the_stage_goes(place):
    place.target.write_bytes(b"someone else's")
    pub, state = publisher(place)
    assert failure(lambda: publish_stage(place, pub)).code == CODES.exists
    assert place.target.read_bytes() == b"someone else's" and place.leftovers() == []
    assert state.attempted is False


def test_a_staged_stream_that_is_not_the_size_it_was_said_to_be_is_changed_before_the_link(place):
    pub, state = publisher(place)
    name, descriptor = staged(place)
    try:
        os.write(descriptor, b"more after the sync")  # the stage is not what the stream said
        error = failure(lambda: pub.publish_stage(name, descriptor, len(CONTENT)))
    finally:
        os.close(descriptor)
    assert error.code == CODES.changed and state.attempted is False  # definite: not linked
    assert not place.target.exists() and place.leftovers() == []


def test_a_staged_stream_with_a_second_link_is_changed(place):
    pub, _ = publisher(place)
    name, descriptor = staged(place)
    try:
        os.link(name, "other-name", src_dir_fd=place.descriptor, dst_dir_fd=place.descriptor)
        error = failure(lambda: pub.publish_stage(name, descriptor, len(CONTENT)))
    finally:
        os.close(descriptor)
    assert error.code == CODES.changed and not place.target.exists()
    assert place.leftovers() == ["other-name"]  # the stage went, the foreign link stays


def test_a_staged_stream_failing_after_the_link_is_uncertain_and_the_target_stays(place):
    pub, state = publisher(place)
    original = pub._remove_stage

    def failing_cleanup():
        if state.attempted:
            raise OSError(errno.EIO, "PRIVATE")
        original()

    pub._remove_stage = failing_cleanup
    assert failure(lambda: publish_stage(place, pub)).code == CODES.uncertain
    assert place.target.read_bytes() == CONTENT


# --- what becomes of a finished stage (the sink's policy) ---------------------------------------


class Keeping(ArtifactPublisher):
    """What a streaming sink does: a finished stage may be the only copy of a long download.

    Only a definite refusal discards it (the name is taken, or the stage is not what was written);
    an I/O error, a deadline or an interrupt says nothing against it, and the next run publishes it.
    """

    def _discard(self, error):
        # A refusal is definite only before the link: after it the target may exist.
        definite = isinstance(error, YorungeError) and error.code in (
            self.codes.exists,
            self.codes.changed,
        )
        if definite and not self.state.attempted:
            self._remove_stage()


def eio(*arguments, **keywords):
    raise OSError(errno.EIO, "PRIVATE")


def deadline(place, pub, monkeypatch):
    place.budget.fail_after = 0


def interrupt(place, pub, monkeypatch):
    pub._check_stage = lambda written: (_ for _ in ()).throw(KeyboardInterrupt())


def cancellation(place, pub, monkeypatch):
    pub._check_stage = lambda written: (_ for _ in ()).throw(asyncio.CancelledError())


def io_error(place, pub, monkeypatch):
    pub._check_stage = eio


def link_io_error(place, pub, monkeypatch):
    monkeypatch.setattr(os, "link", eio)  # the entry is not created, but nobody can tell


FAULTS = [
    (io_error, CODES.failed, False),
    (deadline, "execution_timeout", False),
    (interrupt, KeyboardInterrupt, False),
    (cancellation, asyncio.CancelledError, False),
    (link_io_error, CODES.uncertain, True),
]


def fault_outcome(error, expected):
    if isinstance(expected, str):
        return isinstance(error, YorungeError) and error.code == expected
    return isinstance(error, expected)


@pytest.mark.parametrize(
    "fault,expected,attempted", FAULTS, ids=lambda item: getattr(item, "__name__", None)
)
def test_a_publisher_removes_a_finished_stage_by_default_for_any_failure(
    place, monkeypatch, fault, expected, attempted
):
    pub, state = publisher(place)
    fault(place, pub, monkeypatch)
    assert fault_outcome(failure(lambda: publish_stage(place, pub)), expected)
    assert state.attempted is attempted and not place.target.exists()
    assert place.leftovers() == []


@pytest.mark.parametrize(
    "fault,expected,attempted", FAULTS, ids=lambda item: getattr(item, "__name__", None)
)
def test_a_keeping_publisher_keeps_a_finished_stage_that_nothing_speaks_against(
    place, monkeypatch, fault, expected, attempted
):
    state = PublicationState(CODES)
    pub = Keeping(place, state, prefix=PREFIX)
    fault(place, pub, monkeypatch)
    assert fault_outcome(failure(lambda: publish_stage(place, pub)), expected)
    assert state.attempted is attempted and not place.target.exists()
    (kept,) = place.leftovers()  # the only copy is still whole
    assert (place.directory / kept).read_bytes() == CONTENT
    monkeypatch.undo()
    # The next run publishes the very stage it finds, without the bytes being written again.
    descriptor = os.open(kept, os.O_RDWR | os.O_NOFOLLOW, dir_fd=place.descriptor)
    again = Place(place.directory)
    try:
        Keeping(again, PublicationState(CODES)).publish_stage(kept, descriptor, len(CONTENT))
    finally:
        os.close(descriptor)
        again.close()
    assert place.target.read_bytes() == CONTENT and place.leftovers() == []


def test_a_keeping_publisher_keeps_the_stage_when_the_target_was_replaced_after_the_link(place):
    pub = Keeping(place, PublicationState(CODES), prefix=PREFIX)

    def replaced():
        place.target.unlink()
        place.target.write_bytes(b"FOREIGN")

    after_link(pub, replaced)
    error = failure(lambda: publish_stage(place, pub))
    assert error.code == CODES.uncertain  # the target may or may not be ours
    (kept,) = place.leftovers()  # and what was downloaded is not dropped on that doubt
    assert (place.directory / kept).read_bytes() == CONTENT
    assert place.target.read_bytes() == b"FOREIGN"


def test_an_override_of_the_removal_need_not_clear_the_publishers_bookkeeping(place):
    class Forgetful(ArtifactPublisher):
        def _remove_stage(self):
            os.unlink(self.stage, dir_fd=self.location.descriptor)  # and forgets ``self.stage``

    pub = Forgetful(place, PublicationState(CODES), prefix=PREFIX)
    publish_stage(place, pub)
    assert place.target.read_bytes() == CONTENT and place.leftovers() == []


def test_the_size_that_is_wrong_comes_after_a_source_or_a_place_that_changed(place):
    def moved():
        raise YorungeError("input_changed")

    pub, state = publisher(place, check_source=moved)
    name, descriptor = staged(place)
    try:
        error = failure(lambda: pub.publish_stage(name, descriptor, len(CONTENT) + 5))
    finally:
        os.close(descriptor)
    assert error.code == "input_changed" and state.attempted is False  # not the size's verdict


@pytest.mark.parametrize("member", ["failed", "exists", "uncertain", "changed", "unreadable"])
def test_every_member_of_a_family_must_be_a_closed_code(member):
    with pytest.raises(ValueError):
        ArtifactCodes(**{**CODES.__dict__, member: "no_such_code"})
    with pytest.raises(ValueError):
        ArtifactCodes(**{**CODES.__dict__, member: None})


def test_the_note_that_the_stage_may_be_left_is_on_the_error_once_and_only_before_the_link(
    place, monkeypatch
):
    def unlink_fails(*arguments, **keywords):
        raise OSError(errno.EIO, "")

    def refuse(written):
        raise YorungeError("execution_timeout")

    pub, _ = publisher(place)
    pub._check_stage = refuse
    monkeypatch.setattr(os, "unlink", unlink_fails)
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.code == "execution_timeout"
    assert error.__notes__.count(MESSAGES[CODES.failed]) == 1  # the same error: once
    monkeypatch.undo()
    # After the link the target may exist: the error says so, and carries no note to the contrary.
    for leftover in place.directory.iterdir():
        leftover.unlink()
    pub, state = publisher(place)
    pub._remove_stage = lambda: (_ for _ in ()).throw(OSError(errno.EIO, ""))
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.code == CODES.uncertain and state.attempted is True
    assert MESSAGES[CODES.failed] not in getattr(error, "__notes__", ())


def test_a_keeping_publisher_still_removes_the_stage_of_a_definite_refusal(place):
    place.target.write_bytes(b"someone else's")
    pub = Keeping(place, PublicationState(CODES))
    assert failure(lambda: publish_stage(place, pub)).code == CODES.exists
    assert place.target.read_bytes() == b"someone else's" and place.leftovers() == []


def test_a_keeping_publisher_removes_a_stage_that_is_not_what_was_written(place):
    pub = Keeping(place, PublicationState(CODES))
    name, descriptor = staged(place)
    try:
        os.write(descriptor, b"more after the sync")
        error = failure(lambda: pub.publish_stage(name, descriptor, len(CONTENT)))
    finally:
        os.close(descriptor)
    assert error.code == CODES.changed and place.leftovers() == []


@pytest.mark.parametrize("stage", ["", ".", "..", "a/b", "/elsewhere/stage", "a\0b"])
def test_a_stage_is_one_name_in_the_targets_directory(place, stage):
    pub, state = publisher(place)
    with pytest.raises(ValueError):
        pub.publish_stage(stage, 0, 1)
    assert state.attempted is False and place.leftovers() == []


def test_a_stage_whose_identity_cannot_be_read_is_the_familys_failed_and_is_left_alone(place):
    pub, state = publisher(place)
    name, descriptor = staged(place)
    os.close(descriptor)  # the stream's descriptor is gone
    error = failure(lambda: pub.publish_stage(name, descriptor, len(CONTENT)))
    assert error.code == CODES.failed and state.attempted is False
    assert place.leftovers() == [name]  # its identity is unknown: not the publisher's to remove


def test_bytes_cannot_be_published_without_a_stage_name_prefix(place):
    pub = ArtifactPublisher(place, PublicationState(CODES))
    with pytest.raises(ValueError):
        pub.publish_bytes(CONTENT)
    assert not place.target.exists() and place.leftovers() == []


@pytest.mark.parametrize(
    "changes",
    [{"uncertain": "transport_failed"}, {"failed": "no_such_code"}],
    ids=["uncertain does not exit 5", "unknown code"],
)
def test_a_family_must_be_closed_and_its_doubt_must_exit_5(changes):
    fields = {**CODES.__dict__, **changes}
    with pytest.raises((ValueError, KeyError)):
        ArtifactCodes(**fields)


# --- the manifest path keeps its behaviour, except for one safer case ---------------------------


def test_a_manifest_stage_that_a_racer_truncates_after_the_sync_is_not_published(
    tmp_path, monkeypatch
):
    from yorunge import api
    from yorunge.adapters import dataset_reports

    root = tmp_path / "source"
    root.mkdir()
    (root / "a.txt").write_bytes(b"abc")
    out = tmp_path / "reports"
    out.mkdir()
    target = out / "manifest.json"
    real, calls = dataset_reports.full_sync, []

    def racing(descriptor):
        real(descriptor)
        calls.append(1)
        if len(calls) == 1:
            os.ftruncate(descriptor, 0)  # a racer of the same user, between the sync and the look

    monkeypatch.setattr(dataset_reports, "full_sync", racing)
    with pytest.raises(YorungeError) as error:
        api.inspect_dataset(root, manifest_out=target)
    # Not the bytes that were written: a definite failure before the link, nothing published. (A
    # damaged manifest was once linked and then reported as uncertain.)
    assert error.value.code == "input_changed" and error.value.exit_code == 2
    assert not target.exists() and sorted(p.name for p in out.iterdir()) == []


def test_the_manifests_publication_state_keeps_the_base_positional_order():
    from yorunge.adapters.dataset_reports import MANIFEST_CODES
    from yorunge.adapters.dataset_reports import PublicationState as Manifest

    state = Manifest(True)
    assert state.attempted is True and state.codes == MANIFEST_CODES
    assert Manifest().attempted is False and Manifest(codes=MANIFEST_CODES).attempted is False


# --- what independent mutation found the first tests did not pin ---------------------------------


def entry_publish(place, pub, entry, content=CONTENT):
    if entry == "bytes":
        return pub.publish_bytes(content)
    name, descriptor = staged(place, content)
    try:
        return pub.publish_stage(name, descriptor, len(content))
    finally:
        os.close(descriptor)


def test_the_uncertainty_note_is_added_only_once():
    state = PublicationState(CODES)
    state.attempted = True
    error = asyncio.CancelledError()
    for _ in range(2):  # the publisher's guard, then the caller's own outer handler
        with pytest.raises(asyncio.CancelledError):
            state.reraise(error)
    assert error.__notes__.count(MESSAGES[CODES.uncertain]) == 1


def test_a_failing_close_of_the_stage_descriptor_after_the_link_is_uncertain(place, monkeypatch):
    stage_descriptors, real_open, real_close = set(), os.open, os.close

    def opening(path, *arguments, **keywords):
        descriptor = real_open(path, *arguments, **keywords)
        if isinstance(path, str) and path.startswith(PREFIX):
            stage_descriptors.add(descriptor)
        return descriptor

    def closing(descriptor):
        real_close(descriptor)
        if descriptor in stage_descriptors:
            raise OSError(errno.EIO, "PRIVATE-PATH")

    monkeypatch.setattr(os, "open", opening)
    monkeypatch.setattr(os, "close", closing)
    pub, _ = publisher(place)
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert isinstance(error, YorungeError) and error.code == CODES.uncertain
    assert place.target.read_bytes() == CONTENT


def test_an_oserror_the_caller_hands_to_reraise_is_the_familys_unreadable():
    with pytest.raises(YorungeError) as caught:
        PublicationState(CODES).reraise(OSError(errno.EIO, "PRIVATE"))
    assert caught.value.code == CODES.unreadable


def test_a_programming_error_before_the_link_propagates_unchanged_and_cleans_up(place):
    pub, _ = publisher(place)

    def bug(written):
        raise RuntimeError("bug")

    pub._check_stage = bug
    assert type(failure(lambda: pub.publish_bytes(CONTENT))) is RuntimeError
    assert place.names() == []


def test_a_stat_failure_on_the_target_is_the_familys_failed(place, monkeypatch):
    real = os.stat

    def refused(path, *arguments, **keywords):
        if path == NAME:
            raise PermissionError(errno.EACCES, "PRIVATE-PATH")
        return real(path, *arguments, **keywords)

    monkeypatch.setattr(os, "stat", refused)
    pub, state = publisher(place)
    assert failure(lambda: pub.ensure_absent()).code == CODES.failed
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.failed
    assert place.names() == [] and state.attempted is False


@pytest.mark.parametrize("planted", ["file", "dangling-symlink", "symlink-to-victim"])
def test_a_stage_name_that_is_already_taken_is_never_written_through(place, monkeypatch, planted):
    fixed = uuid.UUID(int=1)
    monkeypatch.setattr("yorunge.adapters.artifact_publisher.uuid4", lambda: fixed)
    stage = place.directory / f"{PREFIX}{fixed.hex}.tmp"
    victim = place.directory / "victim.txt"
    victim.write_bytes(b"VICTIM")
    if planted == "file":
        stage.write_bytes(b"FOREIGN")
    elif planted == "dangling-symlink":
        stage.symlink_to("nowhere")
    else:
        stage.symlink_to(victim)
    pub, state = publisher(place)
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.failed
    assert victim.read_bytes() == b"VICTIM"
    if planted == "file":
        assert stage.read_bytes() == b"FOREIGN"
    assert not place.target.exists() and state.attempted is False


def test_the_stage_is_private_whatever_the_umask(place):
    old = os.umask(0o277)
    try:
        pub, _ = publisher(place)
        pub.publish_bytes(CONTENT)
    finally:
        os.umask(old)
    assert (
        stat.S_IMODE(place.target.stat().st_mode) == 0o600 and place.target.read_bytes() == CONTENT
    )


def test_the_stage_is_created_private_before_any_fchmod(place, monkeypatch):
    old = os.umask(0)
    monkeypatch.setattr(os, "fchmod", lambda *arguments: None)
    try:
        pub, _ = publisher(place)
        pub.publish_bytes(CONTENT)
    finally:
        os.umask(old)
    assert stat.S_IMODE(place.target.stat().st_mode) == 0o600


def test_a_source_that_changes_only_after_the_link_is_uncertain(place):
    calls = []

    def check_source():
        calls.append(1)
        if len(calls) == 2:  # the second look is the one after the link
            raise YorungeError("input_changed")

    pub, state = publisher(place, check_source=check_source)
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.code == CODES.uncertain and state.attempted is True
    assert place.target.read_bytes() == CONTENT


@pytest.mark.parametrize("entry", ["bytes", "stage"])
def test_the_last_budget_check_after_the_link_is_uncertain(place, tmp_path, entry):
    (tmp_path / "count").mkdir()
    counting = Place(tmp_path / "count")
    try:
        pub, _ = publisher(counting)
        entry_publish(counting, pub, entry)
        total = counting.budget.checks
    finally:
        counting.close()
    (tmp_path / "limited").mkdir()
    limited = Place(tmp_path / "limited")
    try:
        limited.budget.fail_after = total - 1  # runs out at the very last check
        pub, _ = publisher(limited)
        error = failure(lambda: entry_publish(limited, pub, entry))
        assert error.code == CODES.uncertain
        assert (tmp_path / "limited" / NAME).read_bytes() == CONTENT
    finally:
        limited.close()


@pytest.mark.parametrize("entry", ["bytes", "stage"])
def test_the_directory_is_synced_after_the_unlink_and_before_the_file_sync(
    place, monkeypatch, entry
):
    events, real_unlink, real_fsync, real_link = [], os.unlink, os.fsync, os.link
    directory = place.descriptor
    pub, _ = publisher(place)
    name, descriptor = staged(place, CONTENT) if entry == "stage" else (None, None)

    def unlink(path, *arguments, **keywords):
        events.append("unlink")
        return real_unlink(path, *arguments, **keywords)

    def link(*arguments, **keywords):
        events.append("link")
        return real_link(*arguments, **keywords)

    def fsync(handle):
        events.append("fsync-directory" if handle == directory else "fsync-file")
        return real_fsync(handle)

    monkeypatch.setattr(os, "unlink", unlink)
    monkeypatch.setattr(os, "link", link)
    monkeypatch.setattr(os, "fsync", fsync)
    if entry == "bytes":
        pub.publish_bytes(CONTENT)
    else:
        pub.publish_stage(name, descriptor, len(CONTENT))
        os.close(descriptor)
    tail = events[events.index("link") :]
    assert tail[:3] == ["link", "unlink", "fsync-directory"] and "fsync-file" in tail[3:]


@pytest.mark.skipif(sys.platform != "darwin", reason="F_FULLFSYNC is a macOS barrier")
def test_the_default_sync_is_a_full_sync_on_macos(place, monkeypatch):
    import fcntl

    seen, real = [], fcntl.fcntl

    def spy(descriptor, command, *rest):
        seen.append(command)
        return real(descriptor, command, *rest)

    monkeypatch.setattr(fcntl, "fcntl", spy)
    pub, _ = publisher(place)
    pub.publish_bytes(CONTENT)
    assert seen.count(fcntl.F_FULLFSYNC) == 2  # once before the link, once after


def test_writes_are_bounded_to_one_mebibyte_and_a_long_write_is_failed(
    place, tmp_path, monkeypatch
):
    sizes, real = [], os.write
    big = b"x" * (3 * 1024 * 1024 + 5)

    def write(descriptor, data):
        sizes.append(len(data))
        return real(descriptor, data)

    monkeypatch.setattr(os, "write", write)
    pub, _ = publisher(place)
    pub.publish_bytes(big)
    assert max(sizes) == 1024 * 1024 and len(sizes) == 4

    monkeypatch.setattr(os, "write", lambda descriptor, data: len(data) + 1)  # more than offered
    (tmp_path / "again").mkdir()
    again = Place(tmp_path / "again")
    try:
        pub, _ = publisher(again)
        assert failure(lambda: pub.publish_bytes(b"abc")).code == CODES.failed
    finally:
        again.close()


@pytest.mark.parametrize("entry", ["bytes", "stage"])
def test_the_place_and_the_source_are_looked_at_before_the_link(place, entry):
    log = []
    pub, state = publisher(place, check_source=lambda: log.append(("source", state.attempted)))
    place.recheck_hook = lambda: log.append(("place", state.attempted))
    entry_publish(place, pub, entry)
    assert ("source", False) in log and ("place", False) in log


def test_a_failing_first_fstat_of_a_stream_stage_is_the_familys_failed(place, monkeypatch):
    pub, state = publisher(place)
    name, descriptor = staged(place, CONTENT)
    real, calls = os.fstat, []

    def fstat(handle):
        calls.append(handle)
        if len(calls) == 1:
            raise OSError(errno.EIO, "PRIVATE-PATH-NEVER-PRINT")
        return real(handle)

    monkeypatch.setattr(os, "fstat", fstat)
    error = failure(lambda: pub.publish_stage(name, descriptor, len(CONTENT)))
    os.close(descriptor)
    assert error.code == CODES.failed and "PRIVATE-PATH" not in str(error.envelope())


def test_a_stage_name_turned_into_a_symlink_to_the_real_stage_is_changed_before_the_link(place):
    pub, state = publisher(place)
    original = pub._check_stage

    def swap(written):
        stage, moved = place.directory / pub.stage, place.directory / "moved"
        stage.rename(moved)
        stage.symlink_to(moved)
        original(written)

    pub._check_stage = swap
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.code == CODES.changed and state.attempted is False
    assert not place.target.exists() and not place.target.is_symlink()


def test_a_stage_modified_after_the_last_look_and_before_the_stage_check_is_changed(place):
    pub, state = publisher(place)
    original = pub._check_stage

    def append(written):
        with open(place.directory / pub.stage, "ab") as handle:
            handle.write(b"+")
        original(written)

    pub._check_stage = append
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.changed
    assert state.attempted is False and not place.target.exists()


@pytest.mark.parametrize("mode", [0o644, 0o400, 0o700])
def test_a_streams_stage_with_another_mode_is_changed_before_the_link(place, mode):
    pub, state = publisher(place)
    name, descriptor = staged(place, CONTENT)
    os.fchmod(descriptor, mode)
    error = failure(lambda: pub.publish_stage(name, descriptor, len(CONTENT)))
    os.close(descriptor)
    assert error.code == CODES.changed and state.attempted is False
    assert not place.target.exists() and place.names() == []


def test_a_stage_owned_by_somebody_else_is_changed_before_the_link(place, monkeypatch):
    pub, state = publisher(place)
    name, descriptor = staged(place, CONTENT)
    owner = os.fstat(descriptor).st_uid
    monkeypatch.setattr(os, "getuid", lambda: owner + 1)
    error = failure(lambda: pub.publish_stage(name, descriptor, len(CONTENT)))
    os.close(descriptor)
    assert error.code == CODES.changed and state.attempted is False and not place.target.exists()


def test_the_stage_carries_the_callers_prefix_and_suffix(place):
    pub, _ = publisher(place)
    seen, original = [], pub._check_stage

    def look(written):
        seen.append(pub.stage)
        original(written)

    pub._check_stage = look
    pub.publish_bytes(CONTENT)
    (stage,) = seen
    assert stage.startswith(PREFIX) and stage.endswith(".tmp") and "/" not in stage


def after_link(pub, action):
    original = pub._publish_link

    def link_then_act():
        original()
        action()

    pub._publish_link = link_then_act


def test_a_target_whose_mode_changed_after_the_link_is_uncertain(place):
    pub, _ = publisher(place)
    after_link(pub, lambda: os.chmod(place.target, 0o644))
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.uncertain


@pytest.mark.parametrize("entry", ["bytes", "stage"])
def test_a_target_with_a_second_name_after_the_link_is_uncertain(place, entry):
    pub, _ = publisher(place)
    after_link(pub, lambda: os.link(place.target, place.directory / "second"))
    assert failure(lambda: entry_publish(place, pub, entry)).code == CODES.uncertain


def test_a_target_replaced_by_a_symlink_to_the_same_file_is_uncertain(place):
    pub, _ = publisher(place)

    def swap():
        os.link(place.target, place.directory / "elsewhere")
        place.target.unlink()
        place.target.symlink_to("elsewhere")

    after_link(pub, swap)
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.uncertain


def test_a_target_truncated_after_the_link_with_its_mtime_restored_is_uncertain(place):
    pub, _ = publisher(place)

    def truncate():
        before = place.target.stat()
        os.truncate(place.target, len(CONTENT) - 1)
        os.utime(place.target, ns=(before.st_atime_ns, before.st_mtime_ns))

    after_link(pub, truncate)
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.uncertain


def test_a_target_owned_by_somebody_else_after_the_link_is_uncertain(place, monkeypatch):
    pub, state = publisher(place)
    real = os.getuid
    monkeypatch.setattr(os, "getuid", lambda: real() + 1 if state.attempted else real())
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.uncertain


def test_a_same_size_overwrite_of_the_target_after_the_link_is_uncertain(place):
    pub, _ = publisher(place)

    def overwrite():
        descriptor = os.open(place.target, os.O_WRONLY)
        os.pwrite(descriptor, b"Z", 0)  # same size, other byte, new mtime
        os.close(descriptor)

    after_link(pub, overwrite)
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.uncertain


@pytest.mark.parametrize("entry", ["bytes", "stage"])
def test_a_stage_that_somebody_else_removed_before_our_cleanup_is_not_an_error(place, entry):
    pub, _ = publisher(place)
    original, calls = pub._check_target, []

    def check(*arguments):
        original(*arguments)
        calls.append(1)
        if len(calls) == 1:  # after the first look at the target, before our own cleanup
            (place.directory / pub.stage).unlink()

    pub._check_target = check
    entry_publish(place, pub, entry)
    assert place.target.read_bytes() == CONTENT and place.names() == [NAME]


@pytest.mark.parametrize("entry", ["bytes", "stage"])
def test_a_link_that_fails_for_another_reason_than_a_taken_name_is_uncertain(
    place, monkeypatch, entry
):
    def refuse(*arguments, **keywords):
        raise OSError(errno.EIO, "PRIVATE-PATH")

    monkeypatch.setattr(os, "link", refuse)
    pub, state = publisher(place)
    error = failure(lambda: entry_publish(place, pub, entry))
    assert error.code == CODES.uncertain and state.attempted is True
    assert "PRIVATE-PATH" not in str(error.envelope())


def test_a_dangling_symlink_target_is_exists_from_the_first_look_and_no_stage_is_made(
    place, monkeypatch
):
    place.target.symlink_to("nowhere")
    opened, real = [], os.open

    def spy(path, *arguments, **keywords):
        opened.append(path)
        return real(path, *arguments, **keywords)

    monkeypatch.setattr(os, "open", spy)
    pub, _ = publisher(place)
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.exists
    assert opened == []  # refused at the first look, before anything was created


def test_a_stage_shorter_than_the_size_it_was_said_to_be_is_changed_before_the_link(place):
    pub, state = publisher(place)
    name, descriptor = staged(place, CONTENT)
    error = failure(lambda: pub.publish_stage(name, descriptor, len(CONTENT) + 1))
    os.close(descriptor)
    assert error.code == CODES.changed and state.attempted is False
    assert not place.target.exists() and place.names() == []


def test_a_stage_modified_while_the_source_is_looked_at_is_changed_before_the_link(place):
    holder, first = {}, []

    def check_source():
        if not first:
            first.append(1)  # the look takes long: somebody appends to the stage meanwhile
            with open(place.directory / holder["pub"].stage, "ab") as handle:
                handle.write(b"+")

    pub, state = publisher(place, check_source=check_source)
    holder["pub"] = pub
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.changed
    assert state.attempted is False and not place.target.exists()


def test_a_symlink_put_at_the_stage_name_after_the_link_is_not_ours_to_remove(place):
    pub, _ = publisher(place)
    original, calls, kept = pub._check_target, [], {}

    def check(*arguments):
        original(*arguments)
        calls.append(1)
        if len(calls) == 1:  # the target was verified; now the stage name becomes a symlink
            stage, moved = place.directory / pub.stage, place.directory / "moved"
            kept["stage"] = stage
            stage.rename(moved)
            stage.symlink_to(moved)

    pub._check_target = check
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.uncertain
    assert kept["stage"].is_symlink()  # the foreign symlink was left alone


def traceback_text(error):
    return "".join(traceback.format_exception(type(error), error, error.__traceback__))


def test_mapped_errors_carry_no_os_error_text_in_their_traceback(place, monkeypatch):
    secret = "PRIVATE-PATH-NEVER-PRINT"
    pub, _ = publisher(place)

    def disk_full(*arguments):
        raise OSError(errno.ENOSPC, secret)

    pub._sync = disk_full
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.code == CODES.failed and secret not in traceback_text(error)

    pub, state = publisher(place)
    original = pub._check_target

    def late(*arguments):
        if state.attempted:
            raise OSError(errno.EIO, secret)
        return original(*arguments)

    pub._check_target = late
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.code == CODES.uncertain and secret not in traceback_text(error)
    place.target.unlink()

    real = os.stat

    def refused(path, *arguments, **keywords):
        if path == NAME:
            raise PermissionError(errno.EACCES, secret)
        return real(path, *arguments, **keywords)

    monkeypatch.setattr(os, "stat", refused)
    pub, _ = publisher(place)
    error = failure(lambda: pub.ensure_absent())
    assert error.code == CODES.failed and secret not in traceback_text(error)
    monkeypatch.setattr(os, "stat", real)

    pub, _ = publisher(place)
    original_link = pub._publish_link

    def taken_then_link():
        place.target.write_bytes(b"other")
        original_link()

    pub._publish_link = taken_then_link
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.code == CODES.exists and "File exists" not in traceback_text(error)

    try:
        raise OSError(errno.EIO, secret)
    except OSError as os_error:
        with pytest.raises(YorungeError) as caught:
            PublicationState(CODES).reraise(os_error)
    assert secret not in traceback_text(caught.value)


def test_the_manifest_family_maps_an_os_or_unicode_error_to_file_unreadable():
    from yorunge.adapters.dataset_reports import PublicationState as ManifestState

    for error in (OSError(errno.EIO, "PRIVATE"), UnicodeError("PRIVATE")):
        with pytest.raises(YorungeError) as caught:
            ManifestState().reraise(error)
        assert caught.value.code == "file_unreadable"


def test_the_manifest_writer_keeps_its_prefix_and_hands_its_source_check_on(place):
    from yorunge.adapters.dataset_reports import DatasetManifestWriter
    from yorunge.adapters.dataset_reports import PublicationState as ManifestState

    calls, seen = [], []
    writer = DatasetManifestWriter(place, ManifestState(), lambda: calls.append(1))
    original = writer._check_stage
    writer._check_stage = lambda written: (seen.append(writer.stage), original(written))
    writer.publish_bytes(b"{}")
    assert len(calls) == 2  # before and after the link
    assert seen[0].startswith(".yorunge-manifest-") and seen[0].endswith(".tmp")


# --- a stage that cannot be removed, and the error that replaces the one raised -------------


def test_a_failed_cleanup_leaves_its_note_on_the_error_that_is_raised(place, monkeypatch):
    pub, state = publisher(place)

    def disk_full(*arguments):
        raise OSError(errno.ENOSPC, "PRIVATE")

    pub._sync = disk_full
    monkeypatch.setattr(os, "unlink", lambda *a, **k: (_ for _ in ()).throw(OSError(errno.EIO, "")))
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.code == CODES.failed and state.attempted is False
    assert MESSAGES[CODES.failed] in error.__notes__  # the stage may still be there
    monkeypatch.undo()
    assert len(place.leftovers()) == 1


def test_a_close_that_fails_while_another_error_is_raised_leaves_the_familys_note(
    place, monkeypatch
):
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
    pub, _ = publisher(place)
    pub._check_stage = lambda written: (_ for _ in ()).throw(YorungeError("execution_timeout"))
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.code == "execution_timeout"
    assert MESSAGES[CODES.failed] in error.__notes__  # the family's, not the manifest's
    assert MESSAGES["file_unreadable"] not in error.__notes__


# --- the entry's arguments ---------------------------------------------------------------


def test_a_stage_cannot_be_named_like_the_target(place):
    pub, state = publisher(place)
    with pytest.raises(ValueError):
        pub.publish_stage(NAME, 0, 1)
    assert state.attempted is False and place.leftovers() == []


def test_a_stage_name_prefix_is_part_of_one_name(place):
    with pytest.raises(ValueError):
        ArtifactPublisher(place, PublicationState(CODES), prefix="dir/.artifact-")


# --- real SIGKILL at each step ------------------------------------------------------------------

KILL = textwrap.dedent(
    """
    import os, signal, sys
    from pathlib import Path
    from tests.integration.test_artifact_publisher import (
        CONTENT, Place, publish_stage, publisher,
    )

    point, entry, directory = sys.argv[1], sys.argv[2], sys.argv[3]
    place = Place(directory)
    pub, state = publisher(place)

    def kill():
        os.kill(os.getpid(), signal.SIGKILL)

    link, remove, sync = pub._publish_link, pub._remove_stage, pub._sync

    def hooked_link():
        if point == "before_link":
            kill()
        link()
        if point == "after_link":
            kill()

    def hooked_remove():
        was_linked = state.attempted
        remove()
        if point == "after_cleanup" and was_linked:
            kill()

    def hooked_sync(descriptor):
        # The directory is synced before the file is, once the link is made.
        if point == "after_directory_sync" and state.attempted:
            kill()
        sync(descriptor)

    pub._publish_link, pub._remove_stage, pub._sync = hooked_link, hooked_remove, hooked_sync
    if entry == "bytes":
        pub.publish_bytes(CONTENT)
    else:
        publish_stage(place, pub)
    sys.exit(7)  # reached only if nothing was killed
    """
)


@pytest.mark.parametrize("entry", ["bytes", "stage"])
@pytest.mark.parametrize(
    "point,published,second_link",
    [
        ("before_link", False, False),
        ("after_link", True, True),
        ("after_cleanup", True, False),
        ("after_directory_sync", True, False),
    ],
)
def test_a_kill_at_every_step_leaves_the_target_absent_or_whole(
    tmp_path, point, published, second_link, entry
):
    directory = tmp_path / "place"
    directory.mkdir()
    repository = str(Path(__file__).resolve().parents[2])
    environment = {**os.environ, "PYTHONPATH": os.pathsep.join([repository, *sys.path])}
    run = subprocess.run(
        [sys.executable, "-c", KILL, point, entry, str(directory)],
        env=environment,
        cwd=repository,
        capture_output=True,
        timeout=60,
    )
    assert run.returncode == -signal.SIGKILL, run.stderr.decode()[-400:]
    target = directory / NAME
    others = sorted(p.name for p in directory.iterdir() if p.name != NAME)
    if published:
        # The target is whole and private; it is never a partial file.
        assert target.read_bytes() == CONTENT and stat.S_IMODE(target.stat().st_mode) == 0o600
        assert target.stat().st_nlink == (2 if second_link else 1)
        assert len(others) == (1 if second_link else 0)
    else:
        assert not target.exists()  # not a byte of it is visible before the link
        assert len(others) == 1  # the stage is left; the next run does not trip on it
    # The next publication, in the same place, goes through whatever the kill left behind.
    again = Place(directory)
    try:
        pub, _ = publisher(again)
        if published:
            assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.exists
            assert target.read_bytes() == CONTENT  # never replaced
        else:
            pub.publish_bytes(CONTENT)
            assert target.read_bytes() == CONTENT and stat.S_IMODE(target.stat().st_mode) == 0o600
    finally:
        again.close()
