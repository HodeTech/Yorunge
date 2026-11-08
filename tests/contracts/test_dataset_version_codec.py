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
    assert first.split_total_matches_item_count is True
    assert first.observed_at == OBSERVED
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
    assert CANARY not in repr(shown)
    assert "köpek" not in repr(shown)


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
    assert CANARY not in repr(shown)
    assert not hasattr(shown, "future_field")


# --- the two reads together -----------------------------------------------------------------------


def test_the_two_reads_that_agree_are_one_observation():
    both = observation(
        detail(detail_body()), version_splits(raw(splits_body()), secret=KEY), observed_at=OBSERVED
    )
    assert both.split_counts == SplitCounts(train=6, val=2, test=1, unassigned=1)
    assert both.split_total_matches_item_count is True
    assert both.observed_at == OBSERVED
    assert both.kind == "dataset_version_observation"
    assert both.class_count == 2


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
    assert both.item_count == 11
    assert both.split_total_matches_item_count is False


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


# --- zero is a count: the most common real value of val, test and unassigned --------------------


def test_zero_counts_are_counts_in_a_detail_a_list_row_and_the_split_route():
    zero = {"train": 0, "val": 0, "test": 0, "unassigned": 0}
    empty = {"item_count": 0, "split_config": zero, "annotated_item_count": 0}
    shown = detail(
        {
            "success": True,
            "data": {
                **row(**empty, total_annotation_count=0),
                "dataset_id": DATASET,
                "class_labels_snapshot": [{**LABELS[0], "annotation_count": 0}],
            },
        }
    )
    assert shown.item_count == 0
    assert shown.split_config == SplitCounts(**zero)
    listed = page(page_body([row(**empty)]))
    assert listed.items[0].split_total_matches_item_count is True
    only_train = {"success": True, "data": {"train": 10, "val": 0, "test": 0, "unassigned": 0}}
    assert version_splits(raw(only_train), secret=KEY).val == 0


def test_the_largest_count_is_accepted_and_one_more_is_not():
    top = 2**63 - 1
    assert version_splits(raw(splits_body(train=top)), secret=KEY).train == top
    assert code_of(lambda: version_splits(raw(splits_body(train=top + 1)), secret=KEY)) == (
        "invalid_response"
    )


# --- the paging arithmetic, its bounds and an honest empty page -----------------------------------


def test_a_dataset_without_versions_is_an_empty_page_not_an_error():
    shown = page(page_body([], total=0))
    assert shown.items == ()
    assert shown.total == 0
    assert shown.has_next is False


@pytest.mark.parametrize(
    "meta",
    [
        {"page": 2, "page_size": 20, "total": 5, "has_next": False},  # past the end of 5 versions
        {"page": 2, "page_size": 20, "total": 0, "has_next": False},
        {"page": 50, "page_size": 20, "total": 0, "has_next": False},
        {"page": 2, "page_size": 20, "total": 20, "has_next": False},  # exactly full before it
    ],
)
def test_a_page_past_the_end_is_an_honest_empty_page(meta):
    shown = page(page_body([], **meta), page=meta["page"])
    assert shown.items == ()
    assert shown.page == meta["page"]


def test_an_empty_page_that_says_more_is_coming_or_that_shows_rows_beyond_the_total_is_refused():
    assert (
        code_of(lambda: page(page_body([], page=2, total=50, has_next=False), page=2))
        == "invalid_response"
    )  # 2 * 20 < 50: there is a next page
    assert code_of(lambda: page(page_body([row()], page=2, total=5), page=2)) == "invalid_response"


@pytest.mark.parametrize(
    "asked,meta",
    [
        (1, {"page": 1, "page_size": 20, "total": 5, "has_next": False}),
        (1, {"page": 1, "page_size": 20, "total": 1000, "has_next": True}),
        (2, {"page": 2, "page_size": 20, "total": 100, "has_next": True}),
        (3, {"page": 3, "page_size": 20, "total": 41, "has_next": False}),
        (2, {"page": 2, "page_size": 20, "total": 21, "has_next": False}),
    ],
    ids=["1-of-5", "1-of-1000", "2-of-100", "3-of-41", "21st-row-hidden"],
)
def test_an_empty_page_that_starts_inside_the_total_hides_rows_and_is_refused(asked, meta):
    # The honest empty page is one past the last row or of a dataset without versions (above).
    assert code_of(lambda: page(page_body([], **meta), page=asked)) == "invalid_response"


def test_the_page_the_provider_shows_must_be_the_page_that_was_asked_for_on_its_own():
    # Page 1 of a hundred versions, answered to a request for page 2: every other rule agrees with
    # it (twenty rows, a total that covers them, more to come), so meta.page is the only witness
    # of a provider that ignores the page parameter.
    rows = [row(id=f"{i:08x}-3333-4333-8333-333333333333", version_tag=f"v{i}") for i in range(20)]
    meta = {"page": 1, "page_size": 20, "total": 100, "has_next": True}
    assert page(page_body(rows, **meta), page=1).page == 1
    assert code_of(lambda: page(page_body(rows, **meta), page=2)) == "invalid_response"


def test_the_largest_legal_page_is_a_hundred_rows():
    rows = [row(id=f"{i:08x}-3333-4333-8333-333333333333", version_tag=f"v{i}") for i in range(100)]
    assert len(page(page_body(rows, page_size=100, total=100)).items) == 100
    assert code_of(lambda: page(page_body(rows[:1], page_size=101, total=1))) == "invalid_response"
    assert code_of(lambda: page(page_body([], page_size=0, total=0))) == "invalid_response"


def test_has_next_is_the_page_times_its_size_below_the_total():
    rows = [row(), row(id="33333333-3333-4333-8333-333333333333", version_tag="v2")]
    # the last page, partial: 3 * 4 = 12 is not below 10 (3 + 4 = 7 would be)
    assert page(page_body(rows, page=3, page_size=4, total=10, has_next=False), page=3)
    assert (
        code_of(lambda: page(page_body(rows, page=3, page_size=4, total=10, has_next=True), page=3))
        == "invalid_response"
    )
    # a middle page: 2 * 2 < 5
    assert page(page_body(rows, page=2, page_size=2, total=5, has_next=True), page=2).has_next


def test_more_distinct_rows_than_the_page_size_is_refused_whatever_else_agrees():
    rows = [row(), row(id="33333333-3333-4333-8333-333333333333", version_tag="v2")]
    assert code_of(lambda: page(page_body(rows, page_size=1, total=2, has_next=True))) == (
        "invalid_response"
    )


def test_the_page_is_a_frozen_wire_model_of_a_closed_kind():
    shown = page(page_body([row()]))
    assert (shown.schema_version, shown.kind, shown.dataset_id) == (
        1,
        "dataset_version_list",
        DATASET,
    )
    assert shown.observed_at == OBSERVED
    assert shown.items[0].kind == "dataset_version_list_item"
    with pytest.raises(ValueError):
        shown.total = 99  # type: ignore[misc]
    assert json.loads(shown.model_dump_json())["items"][0]["version_tag"] == "v1.0-final"


# --- the answers are frozen; the envelope's success is a boolean, not a truthy number -------------


def test_a_detail_is_frozen():
    shown = detail(detail_body())
    with pytest.raises(Exception, match="frozen|assign"):
        shown.item_count = 99  # type: ignore[misc]


@pytest.mark.parametrize("success", [1, "true", None, 0, [True]])
def test_a_success_that_is_not_the_boolean_true_is_refused(success):
    body = {**page_body(), "success": success}
    assert code_of(lambda: page(body)) == "invalid_response"


# --- time: a zone is hours 00-23 and minutes 00-59 (it shifts the time the digest is made of) -----


@pytest.mark.parametrize("zone", ["+00:60", "+05:99", "-01:75", "+24:00", "+99:00", "-24:00"])
def test_an_offset_that_is_not_a_clock_offset_is_not_a_time(zone):
    assert code_of(lambda: provider_time(f"2026-11-04T10:11:12.123456{zone}")) == "invalid_response"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2026-11-04T10:11:12.123456+03:00", "2026-11-04T07:11:12.123456Z"),
        ("2026-11-04T10:11:12.5-05:30", "2026-11-04T15:41:12.500000Z"),
        ("2026-11-04T23:59:59+23:59", "2026-11-04T00:00:59.000000Z"),
        ("2026-11-04T10:11:12Z", "2026-11-04T10:11:12.000000Z"),
        (
            "2026-11-04T10:11:12.1234567891Z".replace("1234567891", "123456789"),
            "2026-11-04T10:11:12.123456Z",
        ),
    ],
)
def test_a_time_with_a_clock_offset_is_the_same_instant_in_utc(value, expected):
    assert provider_time(value) == expected


# --- class labels: bounds, kinds, order -----------------------------------------------------------


def label(identifier, order=0, annotations=0, name="x"):
    return {"id": identifier, "name": name, "sort_order": order, "annotation_count": annotations}


def test_four_thousand_ninety_six_labels_are_the_most_and_one_more_is_not_an_answer():
    assert class_labels_sha256([label(i) for i in range(4096)])
    assert code_of(lambda: class_labels_sha256([label(i) for i in range(4097)])) == (
        "invalid_response"
    )


@pytest.mark.parametrize("not_a_list", ["", b"", {}, None, 0])
def test_only_a_sequence_of_labels_is_labels(not_a_list):
    assert code_of(lambda: class_labels_sha256(not_a_list)) == "invalid_response"


def test_the_int64_bounds_of_sort_order_id_and_annotation_count():
    top = 2**63 - 1
    assert class_labels_sha256([label(1, order=top, annotations=top)])
    assert class_labels_sha256([label(1, order=-top)])
    assert class_labels_sha256([label(top)])
    assert class_labels_sha256([label(-top)])
    for refused in (
        label(1, order=top + 1),
        label(1, order=-top - 1),
        label(top + 1),
        label(-top - 1),
        label(1, annotations=top + 1),
        label(1, annotations=-1),
    ):
        assert code_of(lambda refused=refused: class_labels_sha256([refused])) == "invalid_response"


@pytest.mark.parametrize("odd_id", [[1], {}, (1,), None, 1.5, True, b"x"])
def test_an_id_that_is_neither_an_integer_nor_a_string_is_an_invalid_answer(odd_id):
    assert code_of(lambda: class_labels_sha256([label(odd_id)])) == "invalid_response"


def test_string_ids_sort_by_their_utf8_bytes_and_the_digest_was_computed_outside_python():
    # B (0x42) < a (0x61) < é (0xC3 0xA9): a case-folding or reversed order gives other digests.
    assert class_labels_sha256([label(i) for i in ("a", "é", "B")]) == (
        "4a7eecf0cf9e2ea3634fd8203f62055dcc3b13be6f4a7f5ad4c3fe8e71d25b4d"
    )
    # UTF-8 byte order is not UTF-16 order: z < é < U+FF5E < U+1F600 (UTF-16: U+1F600 first)
    wide = [
        label("\U0001f600", order=-1, annotations=4, name="n4"),
        label("\uff5e", order=2, annotations=3, name="n3"),
        label("z", order=0, annotations=1, name="n1"),
        label("é", order=1, annotations=2, name="n2"),
    ]
    assert class_labels_sha256(wide) == (
        "9b986e63bf3e58743f293daabbf3c587191cb374b0d6a2edec506205b2849ec5"
    )
