"""What changes under the sink between its own steps: the stage's bytes and the sidecar's name.

The lock keeps this tool's own processes apart; another process of the same user (a cleanup tool,
an editor, a second library) is not asked to take it. Two things must hold whatever it does:

* a ``sha256_matched`` (or any digest) is never reported for bytes other than the ones that are
  published: the stage is read back through the descriptor that is held before anything is compared
  or linked, and the link is bound to the state it was read in, before and after the link;
* a file that is not the sidecar this download wrote is never replaced or removed by it.
"""

import errno
import hashlib
import os
import stat

import pytest

from tests.integration.test_download_sink import (
    DATA,
    IDENTITY,
    NAMES,
    code_of,
    download,
    full,
    left,
    stopped_after,
    target,
)
from tests.integration.test_download_sink import place as place
from yorunge.adapters import artifact_publisher, download_files, download_sink
from yorunge.adapters.download_sink import open_sink
from yorunge.domain.errors import YorungeError

FOREIGN = b"somebody else's file, not a record of this download"
LONG_AGO = 1_000_000_000_000_000_000  # an mtime far from now: a later write cannot share it


def overwrite_in_place(path, content, *, at=0):
    """What another process does: write into the file that stands at the name (same size)."""
    with open(path, "r+b") as handle:
        handle.seek(at)
        handle.write(content)


def age(path):
    """Set the mtime back, so that a later in-place write cannot fall in the same clock tick."""
    os.utime(path, ns=(LONG_AGO, LONG_AGO))


def at_boundary(monkeypatch, name, action):
    """Run ``action`` once, when the engine announces ``name`` (``download_files.step``)."""
    done = []

    def marker(seen):
        if seen == name and not done:
            done.append(seen)
            action()

    monkeypatch.setattr(download_files, "_marker", marker)
    return done


# --- the stage's bytes are the ones that were hashed --------------------------------------------


def test_a_stage_written_into_after_the_download_is_never_published_nor_reported(place):
    wrong = bytes(byte ^ 0xFF for byte in DATA[:64])
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        overwrite_in_place(place / NAMES.stage, wrong)  # the same size, other bytes
        assert code_of(lambda: sink.publish(hashlib.sha256(DATA).hexdigest())) == (
            "download_write_failed"
        )
    assert not target(place).exists()  # nothing is linked, so nothing is claimed
    assert (place / NAMES.stage).read_bytes() == wrong + DATA[64:]  # and the stage is not touched
    published, plan = download(
        place
    )  # the next run reads the prefix again, finds it wrong, restarts
    assert plan.action == "download"
    assert plan.resumed_from == 0
    assert target(place).read_bytes() == DATA
    assert left(place) == [target(place).name]


@pytest.mark.parametrize("how", ["longer", "shorter"])
def test_a_stage_that_changed_length_is_not_published(place, how):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        path = place / NAMES.stage
        if how == "longer":
            with open(path, "ab") as handle:
                handle.write(b"x")
        else:
            os.truncate(path, len(DATA) - 1)
        assert code_of(lambda: sink.publish(None)) == "download_write_failed"
    assert not target(place).exists()


def test_a_stage_written_between_the_read_back_and_the_link_is_not_reported_as_published(
    place, monkeypatch
):
    """After the last look and before the link nothing can tell a write from the file's own: the
    check after the link finds it (the times moved), and the answer is *uncertain*, never a
    success."""
    done = at_boundary(
        monkeypatch,
        "publish:before_link",
        lambda: overwrite_in_place(place / NAMES.stage, b"\x00" * 8, at=10),
    )
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        age(place / NAMES.stage)  # the read-back sees this state; a later write moves the mtime
        assert code_of(lambda: sink.publish(None)) == "download_write_uncertain"
    assert done  # the write took place


def test_a_stage_written_while_it_is_synced_is_not_published(place, monkeypatch):
    done = at_boundary(
        monkeypatch,
        "compared",
        lambda: overwrite_in_place(place / NAMES.stage, b"\x00" * 8, at=10),
    )
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        age(place / NAMES.stage)
        assert code_of(lambda: sink.publish(None)) == "download_write_failed"
    assert done
    assert not target(place).exists()


def test_an_untouched_stage_is_published_as_before(place):
    published, _ = download(place, expected=hashlib.sha256(DATA).hexdigest())
    assert published.sha256 == hashlib.sha256(DATA).hexdigest()
    assert target(place).read_bytes() == DATA


# --- the sidecar's name is only replaced or removed by the file this download wrote ------------


def plant_foreign_sidecar(place, mode=0o644):
    """Put somebody else's file at the sidecar's name.

    The file this download wrote is moved out of the directory, not unlinked: a freed inode number
    is handed out again at once on Linux (ext4, tmpfs, overlayfs), and a "foreign" file that got the
    number back would be the same ``(device, inode)`` as the one that was held (see the file-system
    paragraph of ``docs/reference/download-engine.md``). Keeping the old file alive makes the
    foreign one a different file on every kernel, which is what this test is about.
    """
    sidecar = place / NAMES.sidecar
    sidecar.rename(place.parent / (place.name + ".replaced-sidecar"))
    sidecar.write_bytes(FOREIGN)
    os.chmod(sidecar, mode)
    return sidecar


def assert_untouched(sidecar, mode):
    assert sidecar.read_bytes() == FOREIGN
    assert stat.S_IMODE(sidecar.lstat().st_mode) == mode


@pytest.mark.parametrize("mode", [0o644, 0o600])
def test_a_checkpoint_never_replaces_a_sidecar_that_is_not_the_one_it_wrote(
    place, monkeypatch, mode
):
    monkeypatch.setattr(download_sink, "CHECKPOINT_BYTES", 100_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA[:50_000])
        sidecar = plant_foreign_sidecar(place, mode)
        with pytest.raises(download_sink.YorungeError) as refused:
            sink.write(DATA[50_000:150_000])  # crosses the checkpoint
        assert refused.value.code == "download_partial_unverified"
    assert_untouched(sidecar, mode)  # the stop that follows does not take it either
    assert (place / NAMES.stage).exists()


def test_the_completion_checkpoint_never_replaces_a_foreign_sidecar(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sidecar = plant_foreign_sidecar(place)
        assert code_of(lambda: sink.complete(terminated=True)) == "download_partial_unverified"
    assert_untouched(sidecar, 0o644)
    assert not target(place).exists()


def test_a_resumed_download_replaces_the_record_it_kept_and_nothing_else(place, monkeypatch):
    stopped_after(place, 100_000)
    monkeypatch.setattr(download_sink, "CHECKPOINT_BYTES", 100_000)
    published, plan = download(place)
    assert plan.resumed_from == 100_000
    assert target(place).read_bytes() == DATA
    assert left(place) == [target(place).name]


def test_a_resumed_download_does_not_replace_a_sidecar_swapped_after_the_start(place, monkeypatch):
    stopped_after(place, 100_000)
    monkeypatch.setattr(download_sink, "CHECKPOINT_BYTES", 100_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        assert plan.resumed_from == 100_000
        sidecar = plant_foreign_sidecar(place)
        sink.begin(*_continue(plan))
        with pytest.raises(download_sink.YorungeError) as refused:
            sink.write(DATA[100_000:])
        assert refused.value.code == "download_partial_unverified"
    assert_untouched(sidecar, 0o644)


def _continue(plan):
    from tests.integration.test_download_sink import partial_answer

    return partial_answer(plan.ask.prefix_bytes), "continue"


def test_the_cleanup_after_the_link_does_not_remove_a_sidecar_that_is_not_the_one_it_wrote(place):
    """The target is linked by then: the answer is *uncertain* (cleanup did not finish), the
    foreign file stays where it is."""
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        sidecar = plant_foreign_sidecar(place, 0o600)
        assert code_of(lambda: sink.publish(None)) == "download_write_uncertain"
    assert_untouched(sidecar, 0o600)
    assert target(place).read_bytes() == DATA  # what was said is what is there: it exists


def test_a_digest_mismatch_does_not_drop_a_sidecar_that_is_not_the_one_it_wrote(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        sidecar = plant_foreign_sidecar(place, 0o600)
        with pytest.raises(download_sink.DownloadIntegrityMismatch):
            sink.publish("00" * 32)
    assert_untouched(sidecar, 0o600)
    assert not (place / NAMES.stage).exists()  # the stage that was written is dropped as before


def test_a_sidecar_swapped_while_the_temporary_copy_is_written_is_not_replaced(place, monkeypatch):
    """The check just before the rename: the foreign file appears after the first look, while the
    temporary copy is made, written and synced."""
    monkeypatch.setattr(download_sink, "CHECKPOINT_BYTES", 100_000)
    planted, armed = [], []

    def marker(name):
        if name == "sidecar_tmp:synced" and armed and not planted:
            planted.append(plant_foreign_sidecar(place))

    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        monkeypatch.setattr(download_files, "_marker", marker)
        armed.append(True)  # the body's first checkpoint, not the header one
        sink.write(DATA[:50_000])
        assert code_of(lambda: sink.write(DATA[50_000:150_000])) == "download_partial_unverified"
    assert planted
    assert planted[0].read_bytes() == FOREIGN
    assert not (place / NAMES.sidecar_tmp).exists()  # the copy this call made is not left behind


def test_a_foreign_sidecar_is_found_before_a_temporary_copy_is_made(place, monkeypatch):
    monkeypatch.setattr(download_sink, "CHECKPOINT_BYTES", 100_000)
    announced = []
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA[:50_000])
        sidecar = plant_foreign_sidecar(place)
        monkeypatch.setattr(download_files, "_marker", announced.append)
        assert code_of(lambda: sink.write(DATA[50_000:150_000])) == "download_partial_unverified"
    assert "sidecar_tmp:created" not in announced, announced  # nothing is made for a foreign name
    assert_untouched(sidecar, 0o644)


def test_the_header_checkpoint_never_replaces_a_sidecar_that_appeared_after_the_start(place):
    """A fresh download holds no sidecar, so a file at its name is somebody else's."""
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        assert plan.action == "download"
        assert plan.ask is None
        sidecar = place / NAMES.sidecar
        sidecar.write_bytes(FOREIGN)
        os.chmod(sidecar, 0o600)
        assert code_of(lambda: sink.begin(full(), "full")) == "download_partial_unverified"
    assert_untouched(sidecar, 0o600)
    assert not (place / NAMES.sidecar_tmp).exists()


def test_discard_does_not_remove_a_sidecar_that_appeared_after_a_fresh_start(place):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sidecar = place / NAMES.sidecar
        sidecar.write_bytes(FOREIGN)
        os.chmod(sidecar, 0o600)
        assert code_of(sink.discard) == "download_partial_unverified"
    assert_untouched(sidecar, 0o600)


def test_after_a_discard_the_next_checkpoint_expects_no_sidecar(place):
    stopped_after(place, 100_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        assert plan.ask is not None
        sink.discard()
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        sink.publish(None)
    assert target(place).read_bytes() == DATA
    assert left(place) == [target(place).name]


def test_a_write_between_the_last_look_and_the_hand_over_to_the_publisher_is_found(
    place, monkeypatch
):
    """Only the state the sink verified catches it: the publisher's own state, read when it starts,
    would already include the write."""
    original = artifact_publisher.ArtifactPublisher.publish_stage
    hits = []

    def late(self, *arguments, **keywords):
        hits.append(True)
        overwrite_in_place(place / NAMES.stage, b"\x00" * 8, at=10)
        return original(self, *arguments, **keywords)

    monkeypatch.setattr(artifact_publisher.ArtifactPublisher, "publish_stage", late)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        age(place / NAMES.stage)
        assert code_of(lambda: sink.publish(None)) == "download_write_failed"
    assert hits
    assert not target(place).exists()


def test_a_sidecar_whose_directory_sync_failed_is_still_the_one_this_download_holds(
    place, monkeypatch
):
    """The rename took place and the sync after it failed: the name leads to the new file, which
    is the one the stop must remove (not a trace left behind with the stage gone)."""
    armed, real = [], download_files.sync_directory

    def failing_sync(descriptor):
        if armed:
            armed.clear()
            raise OSError(errno.EIO, "directory sync")
        return real(descriptor)

    def marker(name):
        if name == "sidecar:replaced":
            armed.append(True)  # the next directory sync is the one after the rename

    monkeypatch.setattr(download_files, "_marker", marker)
    monkeypatch.setattr(download_files, "sync_directory", failing_sync)
    with pytest.raises(YorungeError) as failed:  # leaving the block with the error: the stop runs
        with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
            sink.begin(full(), "full")
    monkeypatch.undo()
    assert failed.value.code == "download_write_failed"
    assert left(place) == []  # no orphan sidecar, no stage, no lock object


def test_a_lock_object_lost_while_the_stage_is_read_back_and_synced_stops_before_the_hand_over(
    place, monkeypatch
):
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        at_boundary(monkeypatch, "publish:synced", lambda: (place / NAMES.lock).unlink())
        assert code_of(lambda: sink.publish(None)) == "download_busy"
    assert not target(place).exists()  # nothing was linked
    assert sorted(left(place)) == sorted([NAMES.stage, NAMES.sidecar])  # the finished stage stays


def test_after_a_discard_of_a_sidecar_that_is_already_gone_the_next_checkpoint_expects_none(place):
    stopped_after(place, 100_000)
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        assert plan.ask is not None
        (place / NAMES.sidecar).unlink()  # a hand, a cleanup tool: gone before the discard
        sink.discard()
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        sink.publish(None)
    assert target(place).read_bytes() == DATA
    assert left(place) == [target(place).name]


def test_a_write_that_puts_the_modification_time_back_is_still_found_by_the_change_time(
    place, monkeypatch
):
    """Only the change time cannot be set by a writer: same size, same mtime, other bytes."""
    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        stage = place / NAMES.stage
        age(stage)

        def forge():
            overwrite_in_place(stage, b"\x00" * 8, at=10)
            os.utime(stage, ns=(LONG_AGO, LONG_AGO))  # the mtime is back; the ctime is not

        at_boundary(monkeypatch, "publish:synced", forge)
        assert code_of(lambda: sink.publish(None)) == "download_write_failed"
    assert not target(place).exists()


def test_a_stage_touched_while_it_is_read_back_is_a_write_failure_not_a_verdict(place, monkeypatch):
    """The read-back's own look at the state: without it a wrong expectation drops the stage."""
    real, touched = os.pread, []

    def racing(descriptor, count, offset):
        if not touched:
            touched.append(True)
            os.utime(place / NAMES.stage, ns=(1, 1))  # someone touched it in the middle of the read
        return real(descriptor, count, offset)

    with open_sink(target(place), identity_key=IDENTITY) as (sink, plan):
        sink.begin(full(), "full")
        sink.write(DATA)
        sink.complete(terminated=True)
        monkeypatch.setattr(os, "pread", racing)
        assert code_of(lambda: sink.publish("00" * 32)) == "download_write_failed"
        monkeypatch.undo()
    assert sorted(left(place)) == sorted([NAMES.stage, NAMES.sidecar])  # kept for the next run
