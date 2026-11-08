"""The strict codecs of the provider's version answers: what is accepted, refused, and leaks.

A page of versions, one version and its split counts are parsed from bytes; the selected key is
looked for in every string and key (including the fields that are dropped), the fields are checked
one by one and the answers are reduced to the domain types. Nothing here touches a network.
"""

import copy
import json

import pytest

from yorunge.application.dataset_version_codec import (
    observation,
    provider_time,
    version_detail,
    version_page,
    version_splits,
)
from yorunge.domain.credentials import SecretValue
from yorunge.domain.dataset_version import SplitCounts, class_labels_sha256
from yorunge.domain.errors import YorungeError

DATASET = "11111111-1111-4111-8111-111111111111"
VERSION = "22222222-2222-4222-8222-222222222222"
SECRET = "synthetic-platform-key-9f3a1c77"
KEY = SecretValue(SECRET)
OBSERVED = "2026-11-08T12:00:00.000000Z"
CANARY = "PRIVATE-DESCRIPTION-CANARY"
LABELS = [
    {"id": 11, "name": "kedi", "sort_order": 1, "annotation_count": 7, "color": "#ff0000"},
    {"id": 2, "name": "köpek", "sort_order": 0, "annotation_count": 4, "shortcut": "k"},
]


def row(**changes):
    value = {
        "id": VERSION,
        "version_tag": "v1.0-final",
        "is_frozen": True,
        "is_partial": False,
        "is_export_ready": False,
        "item_count": 10,
        "split_config": {"train": 6, "val": 2, "test": 1, "unassigned": 1},
        "annotated_item_count": 9,
        "total_annotation_count": 21,
        "created_at": "2026-11-04T10:11:12.123456Z",
        "description": CANARY,
        "created_by": "someone@example.test",
        "export_zip_url": "https://files.example.test/private.zip?signature=PRIVATE",
        **changes,
    }
    return value


def page_body(rows=None, **meta):
    rows = [row()] if rows is None else rows
    return {
        "success": True,
        "data": rows,
        "meta": {"page": 1, "page_size": 20, "total": len(rows), "has_next": False, **meta},
    }


def detail_body(**changes):
    return {
        "success": True,
        "data": {
            **row(),
            "dataset_id": DATASET,
            "class_labels_snapshot": copy.deepcopy(LABELS),
            **changes,
        },
    }


def splits_body(**counts):
    return {"success": True, "data": {"train": 6, "val": 2, "test": 1, "unassigned": 1, **counts}}


def raw(value):
    return value if isinstance(value, bytes) else json.dumps(value).encode()


def page(body, **options):
    return version_page(
        raw(body),
        dataset_id=options.get("dataset_id", DATASET),
        page=options.get("page", 1),
        secret=KEY,
        observed_at=OBSERVED,
    )


def detail(body, **options):
    return version_detail(
        raw(body),
        dataset_id=options.get("dataset_id", DATASET),
        version_tag=options.get("version_tag", "v1.0-final"),
        secret=KEY,
    )


def code_of(action):
    with pytest.raises(YorungeError) as error:
        action()
    return error.value.code


# --- a page of versions --------------------------------------------------------------------------


def test_a_page_is_the_versions_asked_for_and_what_the_provider_says_about_the_paging():
    shown = page(
        page_body([row(), row(id="33333333-3333-4333-8333-333333333333", version_tag="v2")])
    )
    assert (shown.page, shown.page_size, shown.total, shown.has_next) == (1, 20, 2, False)
    first, second = shown.items
    assert (first.version_id, first.version_tag, first.dataset_id) == (
        VERSION,
        "v1.0-final",
        DATASET,
    )
    assert first.split_counts == SplitCounts(train=6, val=2, test=1, unassigned=1)
    assert first.split_total_matches_item_count is True and first.observed_at == OBSERVED
    assert second.version_tag == "v2"


def test_what_a_page_does_not_need_never_leaves_it():
    dumped = repr(page(page_body()).items) + repr(page(page_body()).items[0].model_dump())
    for secret in (CANARY, "someone@example.test", "files.example.test", "PRIVATE"):
        assert secret not in dumped


def test_a_page_counts_a_total_that_differs_from_the_item_count_as_a_fact_not_an_error():
    odd = page(page_body([row(item_count=11)]))
    assert odd.items[0].split_total_matches_item_count is False


def test_a_second_page_is_a_page_asked_for_by_number():
    second = page(page_body([row()], page=2, page_size=1, total=2, has_next=False), page=2)
    assert second.page == 2


@pytest.mark.parametrize(
    "body,options",
    [
        (page_body(page=2), {"page": 1}),  # the page that came is not the page that was asked for
        (page_body(page_size=0), {}),
        (page_body(page_size=101), {}),
        (page_body([row()] * 2, page_size=1, total=2), {}),  # more rows than the page holds
        (page_body([row(), row(version_tag="v3")]), {}),  # a repeated identifier
        (
            page_body([row(), row(id="33333333-3333-4333-8333-333333333333")], total=2),
            {},
        ),  # a repeated tag
        (page_body(total=0), {}),  # fewer in total than shown
        (page_body(page=2, page_size=20, total=5, has_next=False), {"page": 2}),  # past the total
        (page_body(total=100, has_next=False), {}),  # more to come, and it says not
        (page_body(total=1, has_next=True), {}),  # nothing to come, and it says so
        (page_body(total=True), {}),
        (page_body(has_next="false"), {}),
        (page_body(total=2**63), {}),
        ({"success": False, "data": [], "meta": page_body()["meta"]}, {}),
        ({"data": [], "meta": page_body()["meta"]}, {}),
        ({"success": True, "data": {}, "meta": page_body()["meta"]}, {}),
        ({"success": True, "data": []}, {}),
        ({"success": True, "data": [], "meta": []}, {}),
        ([], {}),
        (b"", {}),
        (b"not json", {}),
        (b'{"success":true,"success":true,"data":[],"meta":{}}', {}),
        (b'{"success":true,"data":[],"meta":{"page":NaN}}', {}),
        (page_body([row(id="not-a-uuid")]), {}),
        (page_body([row(id=VERSION.upper().replace("-", ""))]), {}),
        (page_body([row(version_tag="a/b")]), {}),
        (page_body([row(version_tag="..")]), {}),
        (page_body([row(is_frozen=1)]), {}),
        (page_body([row(is_partial=None)]), {}),
        (page_body([row(item_count=True)]), {}),
        (page_body([row(item_count=-1)]), {}),
        (page_body([row(item_count=1.0)]), {}),
        (page_body([row(item_count="10")]), {}),
        (page_body([row(split_config={"train": 1})]), {}),
        (page_body([row(split_config={"train": True, "val": 0, "test": 0, "unassigned": 0})]), {}),
        (page_body([row(created_at="yesterday")]), {}),
        (page_body([row(created_at="2026-11-04T10:11:12")]), {}),
        (page_body([{key: v for key, v in row().items() if key != "id"}]), {}),
        (page_body([{key: v for key, v in row().items() if key != "split_config"}]), {}),
        (page_body([{key: v for key, v in row().items() if key != "is_export_ready"}]), {}),
        (page_body(["not an object"]), {}),
        (page_body([row()] * 101, page_size=100, total=101), {}),
    ],
    ids=lambda value: str(value)[:48] if not isinstance(value, dict) else "",
)
def test_a_page_that_is_not_exactly_a_page_of_distinct_versions_is_not_an_answer(body, options):
    assert code_of(lambda: page(body, **options)) == "invalid_response"


def test_a_page_of_another_dataset_is_not_asked_for_here_the_reader_binds_the_dataset():
    shown = page(page_body(), dataset_id="44444444-4444-4444-8444-444444444444")
    assert shown.items[0].dataset_id == "44444444-4444-4444-8444-444444444444"


# --- the key in the answer ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "where",
    ["description", "created_by", "unknown_field", "nested", "key", "tag", "label_name", "meta"],
)
def test_the_selected_key_in_any_string_or_key_of_the_answer_even_a_dropped_one_is_refused(where):
    body = detail_body()
    if where == "description":
        body["data"]["description"] = SECRET
    elif where == "created_by":
        body["data"]["created_by"] = f"owner {SECRET} suffix"
    elif where == "unknown_field":
        body["data"]["extra"] = {"deep": [{"x": SECRET}]}
    elif where == "nested":
        body["data"]["class_labels_snapshot"][0]["color"] = SECRET
    elif where == "key":
        body["data"][SECRET] = "x"
    elif where == "tag":
        body["data"]["version_tag"] = SECRET
    elif where == "label_name":
        body["data"]["class_labels_snapshot"][0]["name"] = SECRET
    else:
        body["meta"] = {SECRET: 1}
    assert code_of(lambda: detail(body)) == "invalid_response"
    listing = page_body()
    listing["data"][0]["description"] = SECRET
    assert code_of(lambda: page(listing)) == "invalid_response"
    assert code_of(lambda: version_splits(raw({**splits_body(), "note": SECRET}), secret=KEY)) == (
        "invalid_response"
    )


def test_a_short_key_is_matched_only_when_it_is_the_whole_string():
    short = SecretValue("abc")
    body = detail_body()
    body["data"]["description"] = "abcdef"
    version_detail(raw(body), dataset_id=DATASET, version_tag="v1.0-final", secret=short)
    body["data"]["description"] = "abc"
    assert (
        code_of(
            lambda: version_detail(
                raw(body), dataset_id=DATASET, version_tag="v1.0-final", secret=short
            )
        )
        == "invalid_response"
    )


def test_the_codec_needs_the_key_it_looks_for():
    assert (
        code_of(
            lambda: version_detail(
                raw(detail_body()),
                dataset_id=DATASET,
                version_tag="v1.0-final",
                secret="x",  # type: ignore[arg-type]
            )
        )
        == "invalid_request"
    )


# --- one version ----------------------------------------------------------------------------------


def test_a_version_detail_is_the_facts_the_class_count_and_the_digest_of_the_labels():
    shown = detail(detail_body())
    assert (shown.dataset_id, shown.version_id, shown.version_tag) == (
        DATASET,
        VERSION,
        "v1.0-final",
    )
    assert (shown.item_count, shown.annotated_item_count, shown.total_annotation_count) == (
        10,
        9,
        21,
    )
    assert shown.class_count == 2
    assert shown.class_labels_sha256 == class_labels_sha256(
        [
            {key: v for key, v in label.items() if key not in {"color", "shortcut"}}
            for label in LABELS
        ]
    )
    assert (shown.is_frozen, shown.is_partial, shown.is_export_ready) == (True, False, False)
    assert shown.created_at == "2026-11-04T10:11:12.123456Z"
    assert CANARY not in repr(shown) and "köpek" not in repr(shown)


def test_the_class_labels_digest_does_not_depend_on_colours_shortcuts_or_the_order():
    first = detail(detail_body())
    reordered = detail(detail_body(class_labels_snapshot=list(reversed(LABELS))))
    recoloured = detail(
        detail_body(class_labels_snapshot=[{**label, "color": "#000000"} for label in LABELS])
    )
    assert (
        first.class_labels_sha256 == reordered.class_labels_sha256 == recoloured.class_labels_sha256
    )
    renamed = detail(detail_body(class_labels_snapshot=[{**LABELS[0], "name": "kuş"}, LABELS[1]]))
    assert renamed.class_labels_sha256 != first.class_labels_sha256


@pytest.mark.parametrize(
    "changes",
    [
        {"dataset_id": "44444444-4444-4444-8444-444444444444"},  # another dataset's version
        {"version_tag": "v2"},  # another tag than the one asked for
        {"dataset_id": 5},
        {"id": None},
        {"class_labels_snapshot": {}},
        {"class_labels_snapshot": [{**LABELS[0], "id": "11"}, LABELS[1]]},  # mixed id types
        {"class_labels_snapshot": [LABELS[0], LABELS[0]]},  # a repeated id
        {"class_labels_snapshot": [{"id": 1, "name": "x"}]},
        {"class_labels_snapshot": [{**LABELS[0], "annotation_count": True}]},
        {"class_labels_snapshot": [{**LABELS[0], "name": 5}]},
        {"class_labels_snapshot": ["x"]},
        {"is_frozen": "true"},
        {"split_config": None},
    ],
    ids=lambda changes: "+".join(changes) + str(list(changes.values()))[:20],
)
def test_a_version_detail_that_is_not_the_one_asked_for_or_not_well_formed_is_not_an_answer(
    changes,
):
    assert code_of(lambda: detail(detail_body(**changes))) == "invalid_response"


def test_a_missing_field_is_never_an_implicit_default():
    for name in (
        "id",
        "dataset_id",
        "version_tag",
        "is_frozen",
        "is_partial",
        "is_export_ready",
        "item_count",
        "split_config",
        "annotated_item_count",
        "total_annotation_count",
        "class_labels_snapshot",
        "created_at",
    ):
        body = detail_body()
        del body["data"][name]
        assert code_of(lambda body=body: detail(body)) == "invalid_response", name


def test_the_answer_may_carry_fields_this_project_does_not_know_and_they_are_dropped():
    body = detail_body(future_field={"a": [1, 2, 3]}, description=CANARY)
    shown = detail(body)
    assert CANARY not in repr(shown) and not hasattr(shown, "future_field")


# --- the two reads together -----------------------------------------------------------------------


def test_the_two_reads_that_agree_are_one_observation():
    both = observation(
        detail(detail_body()), version_splits(raw(splits_body()), secret=KEY), observed_at=OBSERVED
    )
    assert both.split_counts == SplitCounts(train=6, val=2, test=1, unassigned=1)
    assert both.split_total_matches_item_count is True and both.observed_at == OBSERVED
    assert both.kind == "dataset_version_observation" and both.class_count == 2


def test_the_two_reads_that_disagree_are_not_an_observation_the_state_moved_between_them():
    shown = detail(detail_body())
    for moved in (splits_body(train=7), splits_body(unassigned=0), splits_body(val=3, test=0)):
        assert (
            code_of(
                lambda moved=moved: observation(
                    shown, version_splits(raw(moved), secret=KEY), observed_at=OBSERVED
                )
            )
            == "invalid_response"
        )


def test_the_split_counts_are_four_strict_counts():
    assert version_splits(raw(splits_body()), secret=KEY) == SplitCounts(
        train=6, val=2, test=1, unassigned=1
    )
    for bad in (
        {"success": True, "data": {"train": 1, "val": 1, "test": 1}},
        {"success": True, "data": {"train": True, "val": 1, "test": 1, "unassigned": 1}},
        {"success": True, "data": {"train": -1, "val": 1, "test": 1, "unassigned": 1}},
        {"success": True, "data": {"train": 1.5, "val": 1, "test": 1, "unassigned": 1}},
        {"success": True, "data": []},
        {"success": False, "data": splits_body()["data"]},
    ):
        assert code_of(lambda bad=bad: version_splits(raw(bad), secret=KEY)) == "invalid_response"


def test_a_total_that_is_not_the_item_count_is_recorded_in_the_observation():
    shown = detail(detail_body(item_count=11))
    both = observation(shown, version_splits(raw(splits_body()), secret=KEY), observed_at=OBSERVED)
    assert both.item_count == 11 and both.split_total_matches_item_count is False


# --- the provider's times -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "given,canonical",
    [
        ("2026-11-04T10:11:12Z", "2026-11-04T10:11:12.000000Z"),
        ("2026-11-04T10:11:12.5Z", "2026-11-04T10:11:12.500000Z"),
        ("2026-11-04T10:11:12.123456789Z", "2026-11-04T10:11:12.123456Z"),
        ("2026-11-04T13:11:12+03:00", "2026-11-04T10:11:12.000000Z"),
        ("2026-11-04T10:11:12-05:30", "2026-11-04T15:41:12.000000Z"),
        ("2026-11-04T23:30:00-02:00", "2026-11-05T01:30:00.000000Z"),
        ("2026-02-28T23:59:59.999999Z", "2026-02-28T23:59:59.999999Z"),
    ],
)
def test_a_provider_time_with_a_zone_is_the_canonical_utc_time_it_names(given, canonical):
    assert provider_time(given) == canonical


@pytest.mark.parametrize(
    "bad",
    [
        "2026-11-04T10:11:12",  # no zone
        "2026-11-04 10:11:12Z",
        "2026-02-30T10:11:12Z",
        "2026-11-04T25:11:12Z",
        "2026-11-04T10:11:12+24:00",
        "2026-11-04T10:11:12+0300",
        "2026-11-04T10:11:12.Z",
        "2026-11-04T10:11:12.1234567890Z",
        "0000-01-01T00:00:00Z",
        "２０２６-11-04T10:11:12Z",
        "",
        None,
        1730715072,
        b"2026-11-04T10:11:12Z",
    ],
)
def test_anything_else_is_not_a_time(bad):
    assert code_of(lambda: provider_time(bad)) == "invalid_response"
