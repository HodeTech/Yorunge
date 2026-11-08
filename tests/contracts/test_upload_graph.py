"""The stage graph specification equals frozen copies of the formulas it replaced."""

from types import SimpleNamespace
from typing import get_args

import pytest

from yorunge.adapters.upload_schema import TRANSFER_SQL
from yorunge.domain.dataset_transfer import StageIntent, operation_reservation
from yorunge.domain.dataset_upload import MAX_EFFECT_INTENTS, MAX_UPLOAD_FILES
from yorunge.domain.upload_graph import (
    CONTINUATION_PLAN_VERSION,
    FILE_STAGE_KINDS,
    ORIGINAL_PLAN_VERSION,
    STAGE_KINDS,
    SUPPORTED_PLAN_VERSIONS,
    StageGraphSpec,
    StageKind,
    file_index_matches,
)
from yorunge.domain.upload_versions import graph_of

VERSIONS = (1, 2)
# The oracle range is literal: the upload file limit is 128 and must not follow the constant.
COUNTS = range(1, 129)


# --- frozen copies of the pre-specification formulas (independent oracle) -----------------------
def frozen_required_stages(file_count):
    result = {("create", None), ("project_link", None)}
    per_file = ("presign", "put", "confirm")
    result.update((kind, i) for i in range(file_count) for kind in per_file)
    return frozenset(result)


def frozen_intent_count(file_count):
    return 2 + 3 * file_count


def frozen_predecessor(kind, index):
    if kind == "create":
        return None
    if kind == "project_link":
        return "create", None
    if kind == "presign":
        return "project_link", None
    return ("presign" if kind == "put" else "put"), index


def frozen_reservation(file_count):
    return 16 * 1024 + (2 + 3 * file_count) * 4096 + 20 * 1024 + file_count * 512


def frozen_limits(file_count):
    return {
        "create": 1,
        "project_link": 1,
        "presign": file_count,
        "put": file_count,
        "confirm": file_count,
    }


def frozen_batches(count):
    return [tuple(range(start, min(count, start + 2))) for start in range(0, count, 2)]


@pytest.mark.parametrize("version", VERSIONS)
def test_every_derived_fact_matches_the_frozen_formulas_for_all_file_counts(version):
    for count in COUNTS:
        spec = StageGraphSpec(version, count)
        assert spec.required_stages() == frozen_required_stages(count)
        assert spec.intent_count == frozen_intent_count(count) == len(spec.required_stages())
        assert spec.operation_reservation() == frozen_reservation(count)
        counts = spec.request_counts()
        seen_counts = {
            "create": counts.create,
            "project_link": counts.project_link,
            "presign": counts.presign,
            "put": counts.put,
            "confirm": counts.confirm,
        }
        assert seen_counts == frozen_limits(count)
        assert counts.total == spec.intent_count
        # Tuples, not ranges: later graphs name file subsets that a range cannot express.
        assert spec.files == tuple(range(count))
        assert list(spec.put_batches()) == frozen_batches(count)
        assert all(type(batch) is tuple for batch in spec.put_batches())


@pytest.mark.parametrize("version", VERSIONS)
def test_predecessor_matches_the_frozen_rule_for_every_stage(version):
    spec = StageGraphSpec(version, MAX_UPLOAD_FILES)
    for kind in STAGE_KINDS:
        for index in (None, *range(MAX_UPLOAD_FILES)):
            assert spec.predecessor(kind, index) == frozen_predecessor(kind, index)
    # Every required stage except create has an accepted predecessor inside the same graph.
    stages = spec.required_stages()
    for kind, index in stages:
        required = spec.predecessor(kind, index)
        assert (required is None) == (kind == "create")
        assert required is None or required in stages


@pytest.mark.parametrize("count", [1, 2, 3, 127, 128])
def test_put_batches_cover_each_file_once_in_order_with_at_most_two_workers(count):
    batches = StageGraphSpec(2, count).put_batches()
    assert [i for batch in batches for i in batch] == list(range(count))
    assert all(1 <= len(batch) <= 2 for batch in batches)
    assert all(len(batch) == 2 for batch in batches[:-1])


@pytest.mark.parametrize("kind", STAGE_KINDS)
@pytest.mark.parametrize("index", [None, 0, 5, 127])
def test_file_index_pairing_equals_the_frozen_rule(kind, index):
    frozen_valid = (kind in {"presign", "put", "confirm"}) == (index is not None)
    assert file_index_matches(kind, index) is frozen_valid


def test_request_dependencies_name_the_same_sources_as_before():
    spec = StageGraphSpec(2, 3)
    assert [k for k in STAGE_KINDS if spec.takes_created_dataset(k)] == [
        "project_link",
        "presign",
        "put",
        "confirm",
    ]
    assert [k for k in STAGE_KINDS if spec.takes_presign_key(k)] == ["put", "confirm"]
    assert FILE_STAGE_KINDS == ("presign", "put", "confirm")


@pytest.mark.parametrize("version", [0, 4, 99, -1, True, False, 1.0, "2", None, (2,)])
def test_unknown_plan_versions_are_rejected_not_treated_like_known_ones(version):
    with pytest.raises(ValueError, match="unsupported upload plan version"):
        StageGraphSpec(version, 1)
    fake = SimpleNamespace(schema_version=version, manifest=SimpleNamespace(file_count=1))
    with pytest.raises(ValueError, match="unsupported upload plan version"):
        graph_of(fake)


@pytest.mark.parametrize("count", [0, -1, 129, 10**9, True, False, 1.0, "1", None])
def test_out_of_range_file_counts_are_rejected(count):
    with pytest.raises(ValueError, match="unsupported upload file count"):
        StageGraphSpec(2, count)


def test_stage_kind_vocabulary_has_one_closed_order():
    assert get_args(StageKind) == STAGE_KINDS
    assert STAGE_KINDS[:2] == ("create", "project_link")
    assert STAGE_KINDS[2:] == FILE_STAGE_KINDS


def test_supported_versions_are_exactly_the_stored_plan_versions():
    assert SUPPORTED_PLAN_VERSIONS == (*VERSIONS, 3)
    assert CONTINUATION_PLAN_VERSION == 3
    assert ORIGINAL_PLAN_VERSION in SUPPORTED_PLAN_VERSIONS


@pytest.mark.parametrize("count", [0, 129, -1])
def test_reservation_wrapper_rejects_counts_outside_the_original_graph(count):
    # Plan manifests are limited to 1..128 files, so no stored plan reaches this error.
    with pytest.raises(ValueError, match="unsupported upload file count"):
        operation_reservation(count)


def test_derived_capacity_constants_agree_with_the_specification():
    largest = StageGraphSpec(2, MAX_UPLOAD_FILES)
    assert largest.intent_count == MAX_EFFECT_INTENTS == 386
    ddl = "\n".join(TRANSFER_SQL)
    assert f"CHECK(sequence BETWEEN 1 AND {largest.intent_count})" in ddl
    sequence = StageIntent.model_fields["sequence"]
    assert any(getattr(item, "le", None) == largest.intent_count for item in sequence.metadata)
    assert MAX_UPLOAD_FILES == 128
    for count in COUNTS:
        assert operation_reservation(count) == frozen_reservation(count)


# --- the continuation graph (plan version 3): independent frozen formulas ----------------------
def frozen_continuation_stages(selection):
    return frozenset((kind, i) for i in selection for kind in ("presign", "put", "confirm"))


def frozen_continuation_reservation(selected, file_count):
    # The same bytes per intent as an original upload; the proof still reads every manifest file.
    return 16 * 1024 + 3 * selected * 4096 + 20 * 1024 + file_count * 512


def selections(count):
    """Empty, full, ends, alternating and a fixed pseudo-random pick of one manifest."""
    every = tuple(range(count))
    picked = tuple(i for i in every if (i * 2654435761) % 7 < 3)
    yield ()
    yield every
    yield every[:1]
    yield every[-1:]
    yield every[::2]
    yield every[1::2]
    yield picked


@pytest.mark.parametrize("count", [1, 2, 3, 5, 64, 127, 128])
def test_a_continuation_matches_the_frozen_formulas_for_every_kind_of_selection(count):
    for selection in selections(count):
        spec = StageGraphSpec(3, count, selection)
        sent = len(selection)
        assert spec.continuation
        assert spec.dataset_from_plan
        assert spec.files == selection
        assert type(spec.files) is tuple
        assert spec.required_stages() == frozen_continuation_stages(selection)
        assert spec.intent_count == 3 * sent == len(spec.required_stages())
        assert spec.operation_reservation() == frozen_continuation_reservation(sent, count)
        counts = spec.request_counts()
        assert (counts.create, counts.project_link) == (0, 0)
        assert (counts.presign, counts.put, counts.confirm) == (sent, sent, sent)
        assert counts.total == spec.intent_count
        batches = spec.put_batches()
        assert [i for batch in batches for i in batch] == list(selection)
        assert all(1 <= len(batch) <= 2 for batch in batches)
        assert all(len(batch) == 2 for batch in batches[:-1])


@pytest.mark.parametrize("count", [1, 3, 128])
def test_a_continuation_of_every_file_saves_exactly_the_create_and_link_intents(count):
    original = StageGraphSpec(2, count)
    everything = StageGraphSpec(3, count, tuple(range(count)))
    assert original.intent_count - everything.intent_count == 2
    assert original.operation_reservation() - everything.operation_reservation() == 2 * 4096
    assert original.files == everything.files
    assert not original.continuation
    assert not original.dataset_from_plan


def test_a_continuation_has_no_create_or_link_and_nothing_before_a_presign():
    spec = StageGraphSpec(3, 3, (0, 2))
    for kind in ("create", "project_link"):
        with pytest.raises(ValueError, match="no create or link stage"):
            spec.predecessor(kind, None)
    assert spec.predecessor("presign", 0) is None
    assert spec.predecessor("put", 2) == ("presign", 2)
    assert spec.predecessor("confirm", 2) == ("put", 2)
    stages = spec.required_stages()
    for kind, index in stages:
        required = spec.predecessor(kind, index)
        assert (required is None) == (kind == "presign")
        assert required is None or required in stages
    assert ("create", None) not in stages
    assert ("project_link", None) not in stages


def test_the_dataset_of_a_stage_comes_from_the_plan_only_in_a_continuation():
    original, continuation = StageGraphSpec(2, 3), StageGraphSpec(3, 3, (0,))
    for spec in (original, continuation):  # every stage but create still binds a dataset id
        assert [k for k in STAGE_KINDS if spec.takes_created_dataset(k)] == [
            "project_link",
            "presign",
            "put",
            "confirm",
        ]
        assert [k for k in STAGE_KINDS if spec.takes_presign_key(k)] == ["put", "confirm"]
    assert (original.dataset_from_plan, continuation.dataset_from_plan) == (False, True)


class ChosenFiles(tuple):
    """Looks like the right selection in every comparison, but is not exactly a tuple."""


@pytest.mark.parametrize(
    "selection",
    [
        None,  # a continuation always names its selection, even an empty one
        ChosenFiles((0, 2)),
        [0],
        {0},
        range(1),
        (1, 0),
        (0, 0),
        (-1,),
        (3,),
        (True,),
        (0.0,),
        ("0",),
        (None,),
        (0, 1, 2, 3),
    ],
)
def test_a_continuation_needs_an_ordered_distinct_selection_inside_the_manifest(selection):
    with pytest.raises(ValueError, match="ordered distinct file selection"):
        StageGraphSpec(3, 3, selection)


@pytest.mark.parametrize("version", VERSIONS)
def test_an_original_graph_takes_no_selection(version):
    StageGraphSpec(version, 3, None)  # the whole manifest, as always
    for selection in ((), (0,), (0, 1, 2)):
        with pytest.raises(ValueError, match="no file selection"):
            StageGraphSpec(version, 3, selection)


def test_the_empty_selection_is_a_graph_with_nothing_to_send_but_a_manifest_to_read():
    spec = StageGraphSpec(3, 128, ())
    assert (spec.intent_count, spec.required_stages(), spec.put_batches()) == (0, frozenset(), ())
    assert spec.request_counts().total == 0
    assert spec.operation_reservation() == 16 * 1024 + 20 * 1024 + 128 * 512


def test_a_manifest_of_zero_or_too_many_files_is_refused_for_a_continuation_too():
    for count in (0, 129):
        with pytest.raises(ValueError, match="unsupported upload file count"):
            StageGraphSpec(3, count, ())
