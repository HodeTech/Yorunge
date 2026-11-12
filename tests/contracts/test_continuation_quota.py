"""What one continuation attempt adds to the store's quota, from arithmetic of the test's own.

The capacity check counts the stored bytes of a plan, the journal reservation of its operation
and a flat 16 KiB per plan; a continuation shares its root's namespace and manifest rows, so those
add nothing. Every figure below is written out here, not taken from the product.
"""

import pytest

from yorunge.domain.dataset_upload import MAX_TRANSFER_PAYLOAD_BYTES, MAX_UPLOAD_PLAN_BYTES
from yorunge.domain.upload_resume_report import (
    PLAN_ALLOWANCE_BYTES,
    QuotaCounters,
    continuation_added_payload_bytes,
)

KIB = 1024


def reservation(files, sent):
    # 16 KiB fixed, three intents of 4 KiB per file sent, 20 KiB for the closing proof and 512
    # bytes per manifest file (the proof reads the whole manifest, not the selection).
    return 16 * KIB + 3 * sent * 4 * KIB + 20 * KIB + files * 512


def added(files, sent, plan=16 * KIB):
    return 16 * KIB + plan + reservation(files, sent)


@pytest.mark.parametrize(
    "files,sent",
    [(1, 0), (1, 1), (3, 0), (3, 2), (3, 3), (64, 10), (128, 0), (128, 1), (128, 127), (128, 128)],
)
def test_an_attempt_adds_its_plan_row_its_journal_reservation_and_the_flat_allowance(files, sent):
    assert continuation_added_payload_bytes(files, sent) == added(files, sent)


def test_an_unknown_selection_is_every_file_and_a_written_plan_is_its_own_size():
    assert continuation_added_payload_bytes(3) == continuation_added_payload_bytes(3, 3)
    assert continuation_added_payload_bytes(3) == added(3, 3)
    assert continuation_added_payload_bytes(3, 1, 9_000) == added(3, 1, 9_000)
    # A smaller plan frees exactly the bytes it does not take; the rest is the same.
    wide, narrow = (continuation_added_payload_bytes(5, 2, size) for size in (16 * KIB, 1))
    assert wide - narrow == 16 * KIB - 1


def test_the_bound_grows_with_what_is_sent_and_with_the_manifest_the_proof_reads():
    base = continuation_added_payload_bytes(10, 4)
    assert continuation_added_payload_bytes(10, 5) - base == 3 * 4 * KIB
    assert continuation_added_payload_bytes(11, 4) - base == 512


def test_the_bound_is_at_least_the_allowance_and_always_fits_the_quota():
    for files in (1, 2, 64, 128):
        for sent in (0, files):
            value = continuation_added_payload_bytes(files, sent)
            assert PLAN_ALLOWANCE_BYTES <= value <= MAX_TRANSFER_PAYLOAD_BYTES
            # What a report states about an attempt is a valid counter set.
            QuotaCounters(plans=1, operations=1, files=files, payload_bytes=value)


def test_the_plan_ceiling_is_the_wire_ceiling_of_a_plan():
    assert MAX_UPLOAD_PLAN_BYTES == 16 * KIB
    assert continuation_added_payload_bytes(2, 1) == continuation_added_payload_bytes(
        2, 1, MAX_UPLOAD_PLAN_BYTES
    )


@pytest.mark.parametrize(
    "arguments",
    [
        (0,),  # a manifest holds at least one file
        (129,),  # and at most 128
        (-1,),
        (3, 4),  # no more files sent than the manifest has
        (3, -1),
        (3, None, 0),  # a stored plan has bytes
        (3, None, MAX_UPLOAD_PLAN_BYTES + 1),  # and fits the wire ceiling
        (True,),  # a boolean is not a count
        (3, True),
        (3, None, True),
        ("3",),
        (3.0,),
    ],
)
def test_what_is_not_a_manifest_a_selection_within_it_or_a_plan_within_its_ceiling_is_refused(
    arguments,
):
    with pytest.raises(ValueError, match="a manifest size, a selection within it"):
        continuation_added_payload_bytes(*arguments)
