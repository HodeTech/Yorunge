"""The stage graph specification equals frozen copies of the formulas it replaced."""

from types import SimpleNamespace
from typing import get_args

import pytest

from yorunge.adapters.upload_schema import TRANSFER_SQL
from yorunge.domain.dataset_transfer import StageIntent, operation_reservation
from yorunge.domain.dataset_upload import MAX_EFFECT_INTENTS, MAX_UPLOAD_FILES
from yorunge.domain.upload_graph import (
    FILE_STAGE_KINDS,
    STAGE_KINDS,
    SUPPORTED_PLAN_VERSIONS,
    StageGraphSpec,
    StageKind,
)
from yorunge.domain.upload_versions import graph_of

VERSIONS = (1, 2)
COUNTS = range(1, MAX_UPLOAD_FILES + 1)


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
    return [range(start, min(count, start + 2)) for start in range(0, count, 2)]


@pytest.mark.parametrize("version", VERSIONS)
def test_every_derived_fact_matches_the_frozen_formulas_for_all_file_counts(version):
    for count in COUNTS:
        spec = StageGraphSpec(version, count)
        assert spec.required_stages() == frozen_required_stages(count)
        assert spec.intent_count == frozen_intent_count(count) == len(spec.required_stages())
        assert spec.operation_reservation() == frozen_reservation(count)
        counts = spec.request_counts()
        assert {
            "create": counts.create,
            "project_link": counts.project_link,
            "presign": counts.presign,
            "put": counts.put,
            "confirm": counts.confirm,
        } == frozen_limits(count)
        assert counts.total == spec.intent_count
        assert list(spec.files) == list(range(count))
        assert list(spec.put_batches()) == frozen_batches(count)


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


@pytest.mark.parametrize("version", [0, 3, 4, 99, -1, True, False, 1.0, "2", None, (2,)])
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
    assert SUPPORTED_PLAN_VERSIONS == VERSIONS


def test_derived_capacity_constants_agree_with_the_specification():
    largest = StageGraphSpec(2, MAX_UPLOAD_FILES)
    assert largest.intent_count == MAX_EFFECT_INTENTS == 386
    ddl = "\n".join(TRANSFER_SQL)
    assert f"CHECK(sequence BETWEEN 1 AND {largest.intent_count})" in ddl
    sequence = StageIntent.model_fields["sequence"]
    assert any(getattr(item, "le", None) == largest.intent_count for item in sequence.metadata)
    assert operation_reservation(1) == StageGraphSpec(2, 1).operation_reservation()
    assert operation_reservation(MAX_UPLOAD_FILES) == largest.operation_reservation()
