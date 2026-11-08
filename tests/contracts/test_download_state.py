"""The start table: what a download does first, row by row, and the rules that hold in every row.

The directory is described by the types of ``download_state``; these tests are the table's
independent vectors, and a seeded random sweep that checks what no row may ever do.
"""

import random
from dataclasses import replace

import pytest

from yorunge.domain.download import EMPTY_SHA256, MAX_SIDECAR_BYTES, DownloadPartial
from yorunge.domain.download_state import (
    ERRORS,
    REMOVAL_ORDER,
    REMOVE_AFTER_EXISTING_TARGET,
    REMOVE_AFTER_MISMATCH,
    Entry,
    SidecarState,
    StartDecision,
    confirm_prefix,
    decide_start,
)

IDENTITY, TARGET = "ab" * 32, "cd" * 32
TAG = '"v1-3f9c"'
DEVICE, INODE = 16777230, 4001


def entry(**changes):
    value = {
        "regular": True,
        "ours": True,
        "private": True,
        "nlink": 1,
        "device": DEVICE,
        "inode": INODE,
        "size": 0,
        **changes,
    }
    return Entry(**value)


def record(**changes):
    value = {
        "schema_version": 1,
        "kind": "download_partial",
        "identity_key": IDENTITY,
        "target_hash": TARGET,
        "etag": TAG,
        "total_size": 1000,
        "committed_bytes": 400,
        "prefix_sha256": "ef" * 32,
        "stage_device": DEVICE,
        "stage_inode": INODE,
        "created_at": "2026-11-08T00:00:00.000000Z",
        "updated_at": "2026-11-08T00:05:00.000000Z",
        **changes,
    }
    return DownloadPartial.model_validate(value)


def sidecar(rec="valid", **changes):
    held = record() if rec == "valid" else rec
    return SidecarState(entry(inode=7, size=300, **changes), held)


def decide(**overrides):
    inputs = {
        "lock": "held",
        "target": None,
        "stage": None,
        "sidecar": None,
        "sidecar_tmp": None,
        "identity_key": IDENTITY,
        "target_hash": TARGET,
        "no_resume": False,
        **overrides,
    }
    return decide_start(**inputs)


def stage(size=400, **changes):
    return entry(size=size, **changes)


# --- the lock comes first -------------------------------------------------------------------------


@pytest.mark.parametrize("no_resume", [False, True])
def test_a_busy_lock_touches_nothing_whatever_else_the_directory_holds(no_resume):
    found = decide(
        lock="busy",
        target=entry(),
        stage=stage(),
        sidecar=sidecar(),
        sidecar_tmp=entry(),
        no_resume=no_resume,
    )
    assert (found.action, found.remove, found.error) == ("busy", (), "download_busy")


def test_a_lock_object_that_is_not_provably_ours_is_an_unverified_trace_and_touches_nothing():
    found = decide(lock="unowned", stage=stage(), sidecar=sidecar(), no_resume=True)
    assert (found.action, found.remove, found.error) == (
        "unverified",
        (),
        "download_partial_unverified",
    )


# --- a target that is there -----------------------------------------------------------------------


def test_an_existing_target_is_reported_and_nothing_is_removed():
    found = decide(target=entry(inode=9), stage=stage(), sidecar=sidecar())
    assert (found.action, found.remove, found.error) == (
        "output_exists",
        (),
        "download_output_exists",
    )


def test_the_trace_of_our_own_interrupted_publication_is_cleaned_before_the_report():
    linked = stage(nlink=2, inode=9)
    found = decide(
        target=entry(inode=9, nlink=2), stage=linked, sidecar=sidecar(), sidecar_tmp=entry()
    )
    assert (found.action, found.remove) == ("output_exists", ("stage", "sidecar", "sidecar_tmp"))
    only_stage = decide(target=entry(inode=9, nlink=2), stage=linked)
    assert only_stage.remove == ("stage",)


@pytest.mark.parametrize(
    "linked",
    [
        stage(nlink=2, inode=8),  # two links, but not the target's file
        stage(nlink=1, inode=9),  # the target's inode with one link: not the trace
        stage(nlink=3, inode=9),
        stage(nlink=2, inode=9, device=DEVICE + 1),
        stage(nlink=2, inode=9, ours=False),
        stage(nlink=2, inode=9, private=False),
        stage(nlink=2, inode=9, regular=False),
    ],
)
def test_a_stage_that_is_not_provably_the_trace_of_our_publication_is_never_removed(linked):
    found = decide(target=entry(inode=9, nlink=2), stage=linked, sidecar=sidecar())
    assert (found.action, found.remove) == ("output_exists", ())


def test_only_the_provably_ours_part_of_the_trace_is_removed():
    linked = stage(nlink=2, inode=9)
    foreign_sidecar = sidecar(ours=False)
    found = decide(
        target=entry(inode=9, nlink=2),
        stage=linked,
        sidecar=foreign_sidecar,
        sidecar_tmp=entry(private=False),
    )
    assert found.remove == ("stage",)


# --- nothing in the way ---------------------------------------------------------------------------


def test_an_empty_directory_starts_clean():
    assert decide() == StartDecision("start_clean")


def test_a_sidecar_without_its_stage_is_discarded_and_the_download_starts_clean():
    found = decide(sidecar=sidecar())
    assert (found.action, found.remove) == ("start_clean", ("sidecar",))


def test_a_leftover_temporary_copy_of_ours_is_removed_in_every_clean_start():
    assert decide(sidecar_tmp=entry()).remove == ("sidecar_tmp",)
    assert decide(sidecar=sidecar(), sidecar_tmp=entry()).remove == ("sidecar", "sidecar_tmp")


def test_a_sidecar_without_a_stage_that_cannot_be_read_is_not_discarded():
    unreadable = sidecar(rec=None)
    assert decide(sidecar=unreadable).action == "unverified"


def test_an_empty_stage_of_ours_without_a_sidecar_is_reused():
    found = decide(stage=stage(size=0))
    assert (found.action, found.remove) == ("reuse_empty_stage", ())
    assert decide(stage=stage(size=0), sidecar_tmp=entry()).remove == ("sidecar_tmp",)


def test_a_full_stage_without_a_sidecar_or_with_one_that_cannot_be_read_is_unverified():
    assert decide(stage=stage()).action == "unverified"
    assert decide(stage=stage(), sidecar=sidecar(rec=None)).action == "unverified"


def test_no_resume_removes_what_is_provably_ours_and_starts_clean():
    assert decide(stage=stage(), no_resume=True).remove == ("stage",)
    assert decide(stage=stage(), sidecar=sidecar(rec=None), no_resume=True).remove == (
        "stage",
        "sidecar",
    )
    both = decide(stage=stage(), sidecar=sidecar(), sidecar_tmp=entry(), no_resume=True)
    assert (both.action, both.remove) == ("start_clean", ("stage", "sidecar", "sidecar_tmp"))
    assert decide(stage=stage(size=0), no_resume=True).remove == ("stage",)


@pytest.mark.parametrize("no_resume", [False, True])
@pytest.mark.parametrize(
    "kind",
    [
        {"regular": False},  # a FIFO, a device, a symlink, a directory
        {"ours": False},
        {"private": False},
        {"nlink": 2},
        {"nlink": 0},
    ],
)
def test_a_name_that_is_not_provably_ours_stops_the_command_and_nothing_is_deleted(kind, no_resume):
    for slot in ("stage", "sidecar", "sidecar_tmp"):
        foreign = {
            "stage": {"stage": stage(**kind)},
            "sidecar": {"sidecar": sidecar(**kind)},
            "sidecar_tmp": {"sidecar_tmp": entry(**kind)},
        }[slot]
        rest = {"stage": stage(), "sidecar": sidecar()} if slot == "sidecar_tmp" else {}
        found = decide(no_resume=no_resume, **{**rest, **foreign})
        assert (found.action, found.remove) == ("unverified", ()), slot


def test_a_sidecar_over_its_size_limit_is_not_ours():
    assert (
        decide(
            stage=stage(), sidecar=SidecarState(entry(size=MAX_SIDECAR_BYTES + 1), record())
        ).action
        == "unverified"
    )
    ok = SidecarState(entry(size=MAX_SIDECAR_BYTES), record())
    assert decide(stage=stage(), sidecar=ok).action == "resume"


# --- a stage and a sidecar that agree -------------------------------------------------------------


def test_a_stage_and_a_sidecar_that_fit_resume_from_the_committed_prefix():
    found = decide(stage=stage(), sidecar=sidecar())
    assert (found.action, found.remove, found.truncate_to) == ("resume", (), None)
    assert (found.ask.prefix_bytes, found.ask.total_size, found.ask.etag) == (400, 1000, TAG)
    assert found.record == record() and found.error is None


def test_a_stage_longer_than_its_last_checkpoint_is_cut_back_to_it():
    found = decide(stage=stage(size=9000), sidecar=sidecar())
    assert (found.action, found.truncate_to, found.ask.prefix_bytes) == ("resume", 400, 400)


def test_a_leftover_temporary_copy_goes_whether_the_download_resumes_or_not():
    assert decide(stage=stage(), sidecar=sidecar(), sidecar_tmp=entry()).remove == ("sidecar_tmp",)


@pytest.mark.parametrize(
    "changes",
    [
        {"identity_key": "12" * 32},  # another service target, thing, format or fold
        {"target_hash": "34" * 32},
        {"committed_bytes": 500},  # the stage (400) is shorter than what the sidecar commits
        {"etag": None},  # a partial is kept only while a strong tag is known
        {"total_size": None},  # and only while the total is known
        {"etag": None, "total_size": None},
        {
            "committed_bytes": 0,
            "prefix_sha256": EMPTY_SHA256,
        },  # nothing committed: nothing to resume
    ],
)
def test_a_stage_that_does_not_fit_its_sidecar_is_discarded_stage_first_and_starts_clean(
    changes,
):
    found = decide(stage=stage(), sidecar=sidecar(rec=record(**changes)))
    assert (found.action, found.remove) == ("start_clean", ("stage", "sidecar")), changes


def test_a_sidecar_written_for_another_file_is_unverified_and_removes_nothing():
    other = record(stage_inode=INODE + 1)
    assert decide(stage=stage(), sidecar=sidecar(rec=other)).action == "unverified"
    assert decide(stage=stage(), sidecar=sidecar(rec=other)).remove == ()
    other_device = record(stage_device=DEVICE + 1)
    assert decide(stage=stage(), sidecar=sidecar(rec=other_device)).action == "unverified"
    # ...and --no-resume, which removes what is provably ours, removes both
    assert decide(stage=stage(), sidecar=sidecar(rec=other), no_resume=True).remove == (
        "stage",
        "sidecar",
    )


def test_no_resume_never_resumes_what_would_have_resumed():
    found = decide(stage=stage(), sidecar=sidecar(), no_resume=True)
    assert (found.action, found.remove, found.ask, found.record) == (
        "start_clean",
        ("stage", "sidecar"),
        None,
        None,
    )


# --- a complete stage: no network -----------------------------------------------------------------


def test_a_complete_stage_that_fits_is_published_without_a_request():
    complete = record(committed_bytes=1000, prefix_sha256="12" * 32)
    found = decide(stage=stage(size=1000), sidecar=sidecar(rec=complete))
    assert (found.action, found.ask, found.truncate_to) == ("publish_complete", None, None)
    assert found.record == complete


def test_a_complete_stage_needs_neither_a_tag_nor_a_known_length_from_the_provider():
    chunked = record(etag=None, total_size=2000, committed_bytes=2000, prefix_sha256="12" * 32)
    assert decide(stage=stage(size=2000), sidecar=sidecar(rec=chunked)).action == "publish_complete"


def test_a_complete_stage_of_no_bytes_is_published_too():
    empty = record(etag=None, total_size=0, committed_bytes=0, prefix_sha256=EMPTY_SHA256)
    assert decide(stage=stage(size=0), sidecar=sidecar(rec=empty)).action == "publish_complete"


def test_a_complete_stage_longer_than_its_total_is_cut_back_and_published():
    complete = record(committed_bytes=1000, prefix_sha256="12" * 32)
    found = decide(stage=stage(size=1500), sidecar=sidecar(rec=complete))
    assert (found.action, found.truncate_to) == ("publish_complete", 1000)


@pytest.mark.parametrize("changes", [{"identity_key": "12" * 32}, {"target_hash": "34" * 32}])
def test_a_complete_stage_of_another_identity_is_never_published(changes):
    complete = record(committed_bytes=1000, prefix_sha256="12" * 32, **changes)
    found = decide(stage=stage(size=1000), sidecar=sidecar(rec=complete))
    assert (found.action, found.remove) == ("start_clean", ("stage", "sidecar"))


def test_a_stage_shorter_than_a_complete_sidecar_is_discarded():
    complete = record(committed_bytes=1000, prefix_sha256="12" * 32)
    found = decide(stage=stage(size=999), sidecar=sidecar(rec=complete))
    assert (found.action, found.remove) == ("start_clean", ("stage", "sidecar"))


# --- the prefix, once it was hashed ---------------------------------------------------------------


def test_a_prefix_that_hashes_as_recorded_confirms_the_decision():
    found = decide(stage=stage(), sidecar=sidecar())
    assert confirm_prefix(found, "ef" * 32) is found
    complete = record(committed_bytes=1000, prefix_sha256="12" * 32)
    publish = decide(stage=stage(size=1000), sidecar=sidecar(rec=complete))
    assert confirm_prefix(publish, "12" * 32) is publish


@pytest.mark.parametrize("observed", ["00" * 32, "EF" * 32, "", None])
def test_a_prefix_that_does_not_hash_as_recorded_discards_stage_first_and_starts_clean(observed):
    for found in (
        decide(stage=stage(), sidecar=sidecar()),
        decide(
            stage=stage(size=1000),
            sidecar=sidecar(rec=record(committed_bytes=1000, prefix_sha256="12" * 32)),
        ),
    ):
        again = confirm_prefix(found, observed)
        assert (again.action, again.remove, again.ask, again.record) == (
            "start_clean",
            ("stage", "sidecar"),
            None,
            None,
        )


def test_a_decision_that_resumes_nothing_is_not_changed_by_a_prefix():
    clean = decide()
    assert confirm_prefix(clean, "00" * 32) is clean
    busy = decide(lock="busy")
    assert confirm_prefix(busy, None) is busy


def test_the_cleanup_after_a_refused_publication_or_a_wrong_digest_is_fixed_and_ordered():
    assert REMOVE_AFTER_EXISTING_TARGET == ("stage", "sidecar")
    assert REMOVE_AFTER_MISMATCH == ("stage", "sidecar", "sidecar_tmp")
    assert REMOVAL_ORDER == ("stage", "sidecar", "sidecar_tmp")
    assert ERRORS == {
        "busy": "download_busy",
        "output_exists": "download_output_exists",
        "unverified": "download_partial_unverified",
    }


# --- what no row may ever do ----------------------------------------------------------------------


def random_entry(rng, *, size=None):
    return Entry(
        regular=rng.random() > 0.1,
        ours=rng.random() > 0.1,
        private=rng.random() > 0.1,
        nlink=rng.choice([1, 1, 1, 1, 2, 0]),
        device=rng.choice([DEVICE, DEVICE, DEVICE + 1]),
        inode=rng.choice([INODE, INODE, INODE + 1, 9]),
        size=rng.choice([0, 100, 400, 1000, 5000]) if size is None else size,
    )


def random_record(rng):
    total = rng.choice([None, 1000, 1000, 0])
    committed = rng.choice([0, 400, 1000]) if total is None or total >= 1000 else 0
    if total is not None and committed > total:
        committed = total
    return record(
        identity_key=rng.choice([IDENTITY, IDENTITY, "12" * 32]),
        target_hash=rng.choice([TARGET, TARGET, "34" * 32]),
        etag=rng.choice([TAG, TAG, None]),
        total_size=total,
        committed_bytes=committed,
        prefix_sha256=EMPTY_SHA256 if committed == 0 else "ef" * 32,
        stage_device=rng.choice([DEVICE, DEVICE, DEVICE + 1]),
        stage_inode=rng.choice([INODE, INODE, INODE + 1]),
    )


def random_directory(rng):
    sidecar_state = None
    if rng.random() < 0.6:
        sidecar_state = SidecarState(
            random_entry(rng, size=rng.choice([300, 300, MAX_SIDECAR_BYTES + 1])),
            None if rng.random() < 0.2 else random_record(rng),
        )
    return {
        "lock": rng.choice(["held", "held", "held", "busy", "unowned"]),
        "target": None if rng.random() < 0.7 else random_entry(rng),
        "stage": None if rng.random() < 0.25 else random_entry(rng),
        "sidecar": sidecar_state,
        "sidecar_tmp": None if rng.random() < 0.7 else random_entry(rng),
        "identity_key": IDENTITY,
        "target_hash": TARGET,
        "no_resume": rng.random() < 0.3,
    }


def provably_ours_to_remove(found, directory):
    """Whether each removal names something present and provably ours."""
    stage_entry, side, tmp = directory["stage"], directory["sidecar"], directory["sidecar_tmp"]
    linked = (
        directory["target"] is not None
        and stage_entry is not None
        and stage_entry.nlink == 2
        and (stage_entry.device, stage_entry.inode)
        == (directory["target"].device, directory["target"].inode)
        and stage_entry.regular
        and stage_entry.ours
        and stage_entry.private
    )
    for item in found.remove:
        if item == "stage" and not (stage_entry is not None and (stage_entry.owned or linked)):
            return False
        if item == "sidecar" and not (side is not None and side.file_owned):
            return False
        if item == "sidecar_tmp" and not (tmp is not None and tmp.owned):
            return False
    return True


def test_a_seeded_sweep_of_directories_never_breaks_the_rules_of_the_table():
    rng = random.Random(20261108)
    actions = set()
    for _ in range(6000):
        directory = random_directory(rng)
        found = decide_start(**directory)
        assert found == decide_start(**directory)  # a decision is a function of what was seen
        actions.add(found.action)
        # The lock comes first: unless it is held, nothing is removed or rewritten.
        if directory["lock"] != "held":
            assert found.remove == () and found.action in {"busy", "unverified"}
        # Only what is present and provably ours is ever removed, always in the fixed order.
        assert provably_ours_to_remove(found, directory), (directory, found)
        assert list(found.remove) == [name for name in REMOVAL_ORDER if name in found.remove]
        # With no target, a trace that is not provably ours stops everything, --no-resume included.
        present = [directory["stage"], directory["sidecar_tmp"]]
        foreign = any(item is not None and not item.owned for item in present)
        side = directory["sidecar"]
        foreign = foreign or (side is not None and not side.file_owned)
        if directory["lock"] == "held" and directory["target"] is None and foreign:
            assert (found.action, found.remove) == ("unverified", ())
        # --no-resume never resumes or publishes a stage.
        if directory["no_resume"]:
            assert found.action not in {"resume", "publish_complete"}
        # A resume or a publication happens only for our own identity, on a stage that fits.
        if found.action in {"resume", "publish_complete"}:
            rec = found.record
            assert rec is not None and directory["lock"] == "held" and directory["target"] is None
            assert (rec.identity_key, rec.target_hash) == (IDENTITY, TARGET)
            assert directory["stage"].owned and directory["stage"].size >= rec.committed_bytes
            assert (directory["stage"].device, directory["stage"].inode) == (
                rec.stage_device,
                rec.stage_inode,
            )
            assert (found.truncate_to is not None) == (
                directory["stage"].size > rec.committed_bytes
            )
        if found.action == "resume":
            assert found.ask is not None and 0 < found.ask.prefix_bytes < found.ask.total_size
            assert (
                found.ask.prefix_bytes == found.record.committed_bytes
                and found.ask.etag == found.record.etag
            )
        if found.action == "publish_complete":
            assert found.ask is None and found.record.complete
        if found.action not in {"resume", "publish_complete"}:
            assert found.ask is None and found.record is None and found.truncate_to is None
        # The decision names an error exactly when the command stops.
        assert (found.error is not None) == (found.action in ERRORS)
        # An existing target is never reported as anything else, and never touched.
        if directory["lock"] == "held" and directory["target"] is not None:
            assert found.action == "output_exists"
    assert actions == {
        "busy",
        "output_exists",
        "unverified",
        "start_clean",
        "reuse_empty_stage",
        "resume",
        "publish_complete",
    }  # the sweep reached every row


def test_a_decision_is_a_frozen_value():
    found = decide()
    with pytest.raises(AttributeError):
        found.action = "busy"  # type: ignore[misc]
    assert replace(found, remove=("stage",)).remove == ("stage",)
