"""The small-file reader, the shared target directory and the binding's no-clobber publication.

Real files in a real directory: what is read must be a plain regular file reached through no
symlink, no longer than the caller's limit and unchanged while it is read; what is published is new,
private and whole or absent, and a name that is taken (before or meanwhile) is never touched.
"""

import asyncio
import errno
import os
import shutil
import stat
from pathlib import Path

import pytest

from tests.contracts.test_dataset_version import SERVICE, bind, observation
from yorunge.adapters import artifact_publisher, small_files
from yorunge.adapters.binding_files import binding_target
from yorunge.adapters.small_files import read_regular_file
from yorunge.adapters.target_directory import open_target_directory
from yorunge.domain.errors import MESSAGES, YorungeError


@pytest.fixture
def place(tmp_path):
    return tmp_path.resolve()  # the project refuses a path that goes through a symlink


def code_of(action):
    with pytest.raises(YorungeError) as error:
        action()
    return error.value.code


def binding():
    return bind(observation(), SERVICE)


# --- reading one small file -----------------------------------------------------------------------


def test_a_regular_file_is_read_whole(place):
    path = place / "a.json"
    path.write_bytes(b'{"a":1}\n')
    assert read_regular_file(path, limit=100, oversize="binding_invalid") == b'{"a":1}\n'


def test_the_limit_is_exact(place):
    path = place / "a.json"
    path.write_bytes(b"x" * 100)
    assert read_regular_file(path, limit=100, oversize="binding_invalid") == b"x" * 100
    path.write_bytes(b"x" * 101)
    assert code_of(lambda: read_regular_file(path, limit=100, oversize="binding_invalid")) == (
        "binding_invalid"
    )
    assert code_of(lambda: read_regular_file(path, limit=100, oversize="manifest_invalid")) == (
        "manifest_invalid"
    )


def test_an_empty_file_is_an_empty_answer_for_the_caller_to_judge(place):
    path = place / "empty"
    path.write_bytes(b"")
    assert read_regular_file(path, limit=10, oversize="binding_invalid") == b""


@pytest.mark.parametrize("kind", ["symlink", "directory", "fifo"])
def test_what_is_not_a_regular_file_is_not_read_and_nothing_blocks(place, kind):
    target = place / "real.json"
    target.write_bytes(b"{}")
    path = place / "thing"
    if kind == "symlink":
        path.symlink_to(target)
    elif kind == "directory":
        path.mkdir()
    else:
        os.mkfifo(path)
    assert code_of(lambda: read_regular_file(path, limit=10, oversize="binding_invalid")) == (
        "input_invalid"
    )


def test_a_parent_that_is_a_symlink_is_not_walked(place):
    real = place / "real"
    real.mkdir()
    (real / "a.json").write_bytes(b"{}")
    (place / "link").symlink_to(real)
    code = code_of(
        lambda: read_regular_file(place / "link" / "a.json", limit=10, oversize="binding_invalid")
    )
    assert code in ("input_invalid", "file_unreadable")


def test_a_file_that_is_not_there_is_unreadable_and_a_relative_path_is_a_mistake(place):
    assert code_of(
        lambda: read_regular_file(place / "absent", limit=10, oversize="binding_invalid")
    ) == ("file_unreadable")
    assert code_of(
        lambda: read_regular_file(Path("relative"), limit=10, oversize="binding_invalid")
    ) == ("invalid_request")


def test_a_file_that_changes_while_it_is_read_is_not_returned(place, monkeypatch):
    path = place / "a.json"
    path.write_bytes(b"x" * 50)
    real = os.read
    calls = []

    def changing(descriptor, count):
        data = real(descriptor, count)
        if not calls:
            calls.append(1)
            with path.open("ab") as handle:  # the file grows after the first block
                handle.write(b"y")
        return data

    monkeypatch.setattr(small_files.os, "read", changing)
    assert code_of(lambda: read_regular_file(path, limit=100, oversize="binding_invalid")) == (
        "input_changed"
    )


def test_a_slow_read_ends_at_its_deadline(place, monkeypatch):
    path = place / "a.json"
    path.write_bytes(b"x" * 50)
    clock = iter([0.0] + [100.0] * 50)
    monkeypatch.setattr(small_files.time, "monotonic", lambda: next(clock))
    assert code_of(
        lambda: read_regular_file(path, limit=100, oversize="binding_invalid", seconds=1.0)
    ) == ("file_unreadable")


# --- the target directory ------------------------------------------------------------------------


def test_the_directory_of_a_target_is_held_and_its_chain_is_looked_at_again(place):
    directory = open_target_directory(
        place / "binding.json", invalid="binding_write_failed", failed="binding_write_failed"
    )
    try:
        assert directory.name == "binding.json"
        directory.recheck()
    finally:
        directory.close()


@pytest.mark.parametrize(
    "build",
    [
        lambda place: Path("relative.json"),
        lambda place: place / "missing" / "x.json",
        lambda place: place / "link" / "x.json",
        lambda place: Path("/"),
        lambda place: place / "new\nline.json",
        lambda place: place / "tab\there.json",
        lambda place: place / "undecodable-\udcff.json",
        lambda place: place / ("x" * 4097),
    ],
    ids=[
        "relative",
        "missing parent",
        "symlink parent",
        "no name",
        "newline",
        "tab",
        "not utf-8",
        "too long",
    ],
)
def test_a_target_that_cannot_be_one_is_the_families_invalid_code(place, build):
    (place / "real").mkdir()
    (place / "link").symlink_to(place / "real")
    codes = {"invalid": "binding_write_failed", "failed": "binding_write_failed"}
    assert code_of(lambda: open_target_directory(build(place), **codes)) == "binding_write_failed"
    assert code_of(lambda: open_target_directory(build(place))) == "download_target_invalid"


def test_a_name_a_result_cannot_report_is_refused_before_anything_is_made(place):
    """The report is made after the link, so a path it would refuse must never become a file."""
    for name in ("new\nline.json", "undecodable-\udcff.json"):
        with pytest.raises(YorungeError) as error:
            with binding_target(place / name):
                raise AssertionError("the block must not be entered")
        assert error.value.code == "binding_write_failed"
    assert list(place.iterdir()) == []


def test_a_directory_that_is_swapped_after_it_was_opened_fails_the_recheck(place):
    inner = place / "inner"
    inner.mkdir()
    directory = open_target_directory(inner / "x.json", failed="binding_write_failed")
    try:
        inner.rename(place / "elsewhere")
        inner.mkdir()  # the same path, another directory
        assert code_of(directory.recheck) == "binding_write_failed"
    finally:
        directory.close()


# --- the binding's publication --------------------------------------------------------------------


def test_a_binding_is_published_new_private_and_whole(place):
    held = binding()
    with binding_target(place / "binding.json") as target:
        target.require_absent()
        target.publish(held)
    written = place / "binding.json"
    info = written.lstat()
    assert written.read_bytes() == held.encoded()
    assert stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1
    assert sorted(p.name for p in place.iterdir()) == ["binding.json"]


def test_a_name_that_is_taken_is_said_so_early_and_left_alone(place):
    (place / "binding.json").write_bytes(b"MINE")
    with binding_target(place / "binding.json") as target:
        assert code_of(target.require_absent) == "binding_output_exists"
    assert (place / "binding.json").read_bytes() == b"MINE"


@pytest.mark.parametrize("kind", ["file", "directory", "dangling symlink"])
def test_a_name_that_is_taken_by_anything_is_never_replaced(place, kind):
    path = place / "binding.json"
    if kind == "file":
        path.write_bytes(b"MINE")
    elif kind == "directory":
        path.mkdir()
    else:
        path.symlink_to(place / "nowhere")
    with pytest.raises(YorungeError) as error:
        with binding_target(path) as target:
            target.publish(binding())
    assert error.value.code == "binding_output_exists"
    assert path.is_symlink() or path.exists()
    assert not list(place.glob(".yorunge-binding-*"))


def test_a_name_taken_after_the_early_look_is_still_never_overwritten(place):
    path = place / "binding.json"
    with pytest.raises(YorungeError) as error:
        with binding_target(path) as target:
            target.require_absent()
            path.write_bytes(b"THEIRS")  # while the provider was being asked
            target.publish(binding())
    assert error.value.code == "binding_output_exists" and path.read_bytes() == b"THEIRS"


def test_an_os_error_before_the_link_is_the_write_failed_code_and_leaves_no_stage(
    place, monkeypatch
):
    def failing(*arguments, **keywords):
        raise OSError(errno.ENOSPC, "PRIVATE")

    monkeypatch.setattr(artifact_publisher.os, "write", failing)
    with pytest.raises(YorungeError) as error:
        with binding_target(place / "binding.json") as target:
            target.publish(binding())
    assert error.value.code == "binding_write_failed"
    assert list(place.iterdir()) == []


def test_a_failure_after_the_link_began_is_uncertain_and_exit_5(place, monkeypatch):
    def failing(*arguments, **keywords):
        raise OSError(errno.EIO, "PRIVATE")

    monkeypatch.setattr(artifact_publisher.os, "link", failing)
    with pytest.raises(YorungeError) as error:
        with binding_target(place / "binding.json") as target:
            target.publish(binding())
    assert error.value.code == "binding_write_uncertain" and error.value.exit_code == 5


@pytest.mark.parametrize("number", [errno.EPERM, errno.ENOTSUP, errno.EMLINK, errno.EXDEV])
def test_a_volume_that_refuses_hard_links_is_a_write_failure_not_an_uncertain_publication(
    place, monkeypatch, number
):
    def refuse(*arguments, **keywords):
        raise OSError(number, "PRIVATE")

    monkeypatch.setattr(artifact_publisher.os, "link", refuse)
    with pytest.raises(YorungeError) as error:
        with binding_target(place / "binding.json") as target:
            target.publish(binding())
    assert (error.value.code, error.value.exit_code) == ("binding_write_failed", 2)
    assert list(place.iterdir()) == []  # no target, no stage: a rerun is a plain retry


def test_an_error_of_the_block_that_is_not_the_publications_passes_through_closed(place):
    with pytest.raises(YorungeError) as error:
        with binding_target(place / "binding.json"):
            raise YorungeError("remote_failed")  # the provider failed: the binding was never made
    assert error.value.code == "remote_failed"
    assert list(place.iterdir()) == []


def test_a_parent_that_is_replaced_before_the_link_is_a_write_failure_and_nothing_is_linked(place):
    inner = place / "inner"
    inner.mkdir()
    with pytest.raises(YorungeError) as error:
        with binding_target(inner / "binding.json") as target:
            target.require_absent()
            inner.rename(place / "elsewhere")
            inner.mkdir()  # the same path, another directory, while the provider was asked
            target.publish(binding())
    assert error.value.code == "binding_write_failed"
    assert list(inner.iterdir()) == [] and not (place / "elsewhere" / "binding.json").exists()


def names_below(place):
    """Every file name under ``place``, symbolic links to directories followed."""
    return sorted(name for _, _, files in os.walk(place, followlinks=True) for name in files)


@pytest.mark.parametrize(
    "how",
    ["symlink in its place", "renamed away", "grandparent swapped for a symlink", "removed"],
)
def test_a_parent_that_changes_in_any_way_after_the_early_look_is_a_write_failure(place, how):
    """The directory is held open from before the provider is asked; whatever happens to the path
    meanwhile, nothing is linked into the directory that is now at it, nor into the old one."""
    outer, inner = place / "outer", place / "outer" / "inner"
    inner.mkdir(parents=True)
    with pytest.raises(YorungeError) as error:
        with binding_target(inner / "binding.json") as target:
            target.require_absent()
            if how == "symlink in its place":
                inner.rename(outer / "moved")
                inner.symlink_to(outer / "moved")
            elif how == "renamed away":
                inner.rename(outer / "moved")
            elif how == "grandparent swapped for a symlink":
                outer.rename(place / "outer-moved")
                outer.symlink_to(place / "outer-moved")
            else:
                shutil.rmtree(inner)
            target.publish(binding())
    assert error.value.code == "binding_write_failed"
    assert names_below(place) == []  # no binding at the name, no stage left anywhere


def test_a_parent_that_is_renamed_away_and_back_is_the_same_directory_and_gets_the_binding(place):
    inner = place / "inner"
    inner.mkdir()
    with binding_target(inner / "binding.json") as target:
        target.require_absent()
        inner.rename(place / "elsewhere")
        (place / "elsewhere").rename(inner)  # the same directory, by identity
        target.publish(binding())
    assert names_below(place) == ["binding.json"]


def test_a_task_cancellation_before_the_link_propagates_as_it_is(place):
    with pytest.raises(asyncio.CancelledError) as cancelled:
        with binding_target(place / "binding.json"):
            raise asyncio.CancelledError
    assert not getattr(cancelled.value, "__notes__", ())  # nothing was linked: nothing is uncertain
    assert list(place.iterdir()) == []


def test_a_task_cancellation_after_the_link_began_carries_the_uncertainty(place, monkeypatch):
    real = os.link

    def linking_then_cancelled(*arguments, **keywords):
        real(*arguments, **keywords)
        raise asyncio.CancelledError

    monkeypatch.setattr(artifact_publisher.os, "link", linking_then_cancelled)
    with pytest.raises(asyncio.CancelledError) as cancelled:
        with binding_target(place / "binding.json") as target:
            target.publish(binding())
    assert MESSAGES["binding_write_uncertain"] in cancelled.value.__notes__
