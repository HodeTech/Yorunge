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
from pathlib import Path

import pytest

from yorunge.adapters.artifact_publisher import ArtifactCodes, ArtifactPublisher, PublicationState
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

    def recheck(self):
        self.rechecks += 1
        if self.changed:
            raise YorungeError("input_changed")

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
    pub, _ = publisher(place)
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.failed
    assert not place.target.exists() and place.leftovers() == []


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


def test_a_stage_with_another_mode_or_link_count_is_changed(place):
    pub, _ = publisher(place)
    original = pub._check_stage

    def chmod(written):
        os.chmod(place.directory / pub.stage, 0o644)
        original(written)

    pub._check_stage = chmod
    assert failure(lambda: pub.publish_bytes(CONTENT)).code == CODES.changed
    assert not place.target.exists() and place.leftovers() == []


def test_a_place_that_changed_is_the_error_of_its_own_and_creates_nothing(place):
    pub, _ = publisher(place)
    original = pub._check_stage

    def moved(written):
        place.changed = True
        original(written)

    pub._check_stage = moved
    # The place's own check ran after the stage was verified: the next look sees the change.
    pub._publish_link = lambda: place.recheck()
    error = failure(lambda: pub.publish_bytes(CONTENT))
    assert error.code == "input_changed" and not place.target.exists() and place.leftovers() == []


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
    environment = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
    run = subprocess.run(
        [sys.executable, "-c", KILL, point, entry, str(directory)],
        env=environment,
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
