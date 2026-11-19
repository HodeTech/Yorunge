"""The catalog contract (P02-4c, ADR-0035): consumed shapes, page rules, completeness, addresses.

Every fixture here is synthetic: no real identifier, key or person. The provider answers are
written from the public schema summary, so the tests say what a *consumed* field must look like,
what a silently changed page must do, and what an unexpected secret must do wherever it sits.
"""

import json
from dataclasses import dataclass

import pytest

from yorunge.application import catalog as codec
from yorunge.domain import catalog
from yorunge.domain.credentials import SecretValue
from yorunge.domain.errors import YorungeError

KEY = SecretValue("sk-live-ABCDEFGH12345678")
STAMP = "2026-01-01T00:00:00Z"


def raise_code(callable_, *args, **kwargs) -> str:
    with pytest.raises(YorungeError) as info:
        callable_(*args, **kwargs)
    return info.value.code


def jbytes(value: object) -> bytes:
    return json.dumps(value).encode("utf-8")


# --- addresses ------------------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["owner-1", "a.b_c-9", "x" * 128, "..."])
def test_segment_accepts_the_allowed_alphabet_and_ordinary_dots(value: str) -> None:
    # "..." is an ordinary name in this alphabet; only the dot segments are navigation.
    assert catalog.segment(value) == value


@pytest.mark.parametrize(
    "value",
    ["", ".", "..", "a/b", "a%2e", "a?b", "a#b", "a b", "a\nb", "x" * 129, "ö", None, True],
)
def test_segment_refuses_everything_else_before_any_request(value) -> None:
    assert raise_code(catalog.segment, value) == "invalid_request"


def test_version_tag_is_length_and_control_bounded_only() -> None:
    assert catalog.version_tag("v1.0+build") == "v1.0+build"
    assert raise_code(catalog.version_tag, "") == "invalid_request"
    assert raise_code(catalog.version_tag, "a\tb") == "invalid_request"
    assert raise_code(catalog.version_tag, "x" * 129) == "invalid_request"


def test_owner_without_a_stored_name_is_not_addressable() -> None:
    assert raise_code(catalog.owner_address, None) == "model_not_addressable"
    assert catalog.owner_address("owner-1") == "owner-1"


def test_detail_must_be_the_model_the_address_named() -> None:
    assert raise_code(catalog.detail_identity, "other", "s", "owner", "s") == "invalid_response"
    assert raise_code(catalog.detail_identity, "owner", "other", "owner", "s") == "invalid_response"
    catalog.detail_identity("owner", "s", "owner", "s")


# --- pages and completeness (ADR-0035 Karar 2–3) -------------------------------------------------


@pytest.mark.parametrize("page,size", [(0, 20), (1, 0), (1, 101), (True, 20), ("1", 20)])
def test_page_arguments_are_integers_in_range(page, size) -> None:
    assert raise_code(catalog.page_arguments, page, size) == "invalid_request"


def test_expected_rows_follow_the_asked_page_size() -> None:
    assert catalog.expected_rows(1, 20, 45) == 20
    assert catalog.expected_rows(3, 20, 45) == 5
    assert catalog.expected_rows(4, 20, 45) == 0
    assert catalog.expected_rows(1, 20, 0) == 0


@pytest.mark.parametrize(
    "page,size,total,returned,expected",
    [
        (1, 20, 45, 20, "partial"),
        (3, 20, 45, 5, "last_page"),
        (2, 20, 40, 20, "last_page"),
        (1, 20, 0, 0, "complete"),
        (1, 20, 20, 20, "complete"),
        (5, 20, 10, 0, "last_page"),
    ],
)
def test_platform_page_labels(page, size, total, returned, expected) -> None:
    assert catalog.platform_page(page, size, total, returned) == expected


def test_a_silently_smaller_page_is_invalid_not_complete() -> None:
    # Asked for 100, received 20 of 45: a formula on the total alone would call this complete.
    assert raise_code(catalog.platform_page, 1, 100, 45, 20) == "invalid_response"


@pytest.mark.parametrize("total", [-1, True, 1.0, "45", None])
def test_platform_total_must_be_a_non_negative_integer(total) -> None:
    assert raise_code(catalog.platform_page, 1, 20, total, 0) == "invalid_response"


@pytest.mark.parametrize(
    "has_next,expected",
    [
        ((), "unknown"),
        (("maybe",), "unknown"),
        (("TRUE",), "unknown"),
        (("1",), "partial"),
        (("0",), "complete"),
        (("1", "1"), "unknown"),
        (("0", "0"), "unknown"),
        (("true",), "unknown"),
        (("false",), "unknown"),
    ],
)
def test_dataset_has_next_header_is_exact_and_single_or_unknown(has_next, expected) -> None:
    assert catalog.dataset_page(1, 20, 20, has_next, ()) == expected


@pytest.mark.parametrize("total", [("-5",), ("abc",), ("1.0",), ("45", "45"), ("1" * 19,)])
def test_unreadable_or_repeated_total_header_makes_the_page_unknown_not_complete(total) -> None:
    assert catalog.dataset_page(1, 20, 20, ("0",), total) == "unknown"
    assert catalog.dataset_page(1, 20, 20, ("1",), total) == "unknown"


def test_dataset_last_page_is_not_complete() -> None:
    assert catalog.dataset_page(3, 20, 5, ("0",), ()) == "last_page"


def test_dataset_total_header_must_agree_with_rows_and_has_next() -> None:
    assert catalog.dataset_page(1, 20, 20, ("1",), ("45",)) == "partial"
    assert raise_code(catalog.dataset_page, 1, 20, 19, ("1",), ("45",)) == "invalid_response"
    assert raise_code(catalog.dataset_page, 1, 20, 20, ("0",), ("45",)) == "invalid_response"


def test_version_list_is_complete_only_when_it_matches_the_detail() -> None:
    assert catalog.versions_listing(3, 3) == "complete"
    assert catalog.versions_listing(3, 2) == "unknown"
    assert catalog.versions_listing(None, 2) == "unknown"  # the model_id route has no detail
    assert raise_code(catalog.checked_versions, 3, 2) == "invalid_response"


@pytest.mark.parametrize("count", [True, 1.0, -1, "1"])
def test_version_count_must_be_a_plain_non_negative_integer(count) -> None:
    assert raise_code(catalog.versions_listing, count, 1) == "invalid_response"
    assert raise_code(catalog.checked_versions, count, 1) == "invalid_response"


# --- resolution (ADR-0035 Karar 5) ----------------------------------------------------------------


@dataclass(frozen=True)
class Version:
    version_id: str
    version_tag: str
    created_at: str


VERSIONS = (
    Version("v-1", "1.0", STAMP),
    Version("v-2", "1.1", STAMP),
    Version("v-3", "1.1", STAMP),
)


def test_one_tag_selects_one_version() -> None:
    assert catalog.resolve_version(VERSIONS, "1.0").version_id == "v-1"


def test_no_matching_tag_is_not_a_proof_of_absence() -> None:
    assert raise_code(catalog.resolve_version, VERSIONS, "9.9") == "model_not_visible"


def test_two_versions_with_one_tag_are_ambiguous_never_picked() -> None:
    assert raise_code(catalog.resolve_version, VERSIONS, "1.1") == "model_ambiguous"
    assert [item.version_id for item in catalog.candidates(VERSIONS, "1.1")] == ["v-2", "v-3"]


def test_candidates_are_capped_at_five() -> None:
    many = tuple(Version(f"v-{n}", "dup", STAMP) for n in range(9))
    assert len(catalog.candidates(many, "dup")) == catalog.MAX_CANDIDATES


def test_tag_is_checked_before_comparison() -> None:
    assert raise_code(catalog.resolve_version, VERSIONS, "") == "invalid_request"


def test_llm_task_mismatch_is_refused_unknown_names_are_not() -> None:
    catalog.task_matches("embedding", "embedding")
    assert raise_code(catalog.task_matches, "embedding", "chat") == "model_task_mismatch"


@pytest.mark.parametrize(
    "code,exit_code",
    [
        ("model_not_visible", 1),
        ("model_ambiguous", 2),
        ("model_task_mismatch", 2),
        ("model_not_addressable", 2),
    ],
)
def test_the_four_new_codes_have_their_messages_and_exit_codes(code, exit_code) -> None:
    error = YorungeError(code)
    assert error.exit_code == exit_code
    assert error.message


# --- display (untrusted text) ---------------------------------------------------------------------


def test_display_text_drops_controls_and_bidi_overrides_and_flattens_breaks() -> None:
    assert catalog.text("a\x07b\u202ec\nd\te", 100) == "abc d e"


def test_unicode_line_and_paragraph_separators_become_spaces() -> None:
    assert catalog.text("a b c", 100) == "a b c"


def test_display_text_is_bounded_and_says_so() -> None:
    cut = catalog.text("x" * 300, 10)
    assert len(cut) == 10
    assert cut.endswith(catalog.ELLIPSIS)


def test_display_text_keeps_none_and_refuses_a_useless_limit() -> None:
    assert catalog.text(None, 10) is None
    assert raise_code(catalog.text, "x", 1) == "invalid_response"


# --- reading an answer (ADR-0035 Karar 8) ---------------------------------------------------------


def test_the_secret_is_refused_wherever_it_sits_even_in_a_dropped_field() -> None:
    answer = jbytes({"data": [], "debug": {"deep": [KEY.reveal()]}})
    assert raise_code(codec.llm_listing, answer, KEY) == "invalid_response"


def test_the_secret_as_a_key_is_refused_too() -> None:
    answer = jbytes({"data": [], KEY.reveal(): 1})
    assert raise_code(codec.llm_listing, answer, KEY) == "invalid_response"


def test_duplicate_keys_and_nonfinite_numbers_are_refused_by_the_strict_parser() -> None:
    assert raise_code(codec.llm_listing, b'{"data": [], "data": []}', KEY) == "invalid_response"
    assert raise_code(codec.llm_listing, b'{"data": [NaN]}', KEY) == "invalid_response"


def test_an_answer_over_the_shared_budget_is_refused() -> None:
    assert raise_code(codec.llm_listing, b"x" * (codec.JSON_LIMIT + 1), KEY) == "invalid_response"


def test_a_secret_rebuilt_by_cleaning_is_refused_on_the_output() -> None:
    # Each piece is clean on its own; the display cleaning joins them into the key again.
    name = KEY.reveal()[:5] + "​" + KEY.reveal()[5:]
    answer = jbytes({"items": [platform_model(name=name)], "total": 1})
    assert raise_code(codec.platform_models, answer, KEY, 1, 20) == "invalid_response"


def test_a_secret_rebuilt_in_llm_modalities_or_currency_is_refused() -> None:
    key = KEY.reveal()
    split_modality = key[:4] + "\u2066" + key[4:]
    assert (
        raise_code(
            codec.llm_listing, jbytes({"data": [llm_item(modalities=[split_modality])]}), KEY
        )
        == "invalid_response"
    )
    split_currency = key[:6] + "­" + key[6:]
    pricing = {"prompt_token_price": 1, "completion_token_price": 1, "currency": split_currency}
    assert (
        raise_code(codec.llm_listing, jbytes({"data": [llm_item(pricing=pricing)]}), KEY)
        == "invalid_response"
    )


# --- LLM listing and detail -----------------------------------------------------------------------


def llm_item(**overrides):
    item = {
        "id": "model-a",
        "object": "model",
        "created": 1700000000,
        "owned_by": "unit-owner",
        "task": "embedding",
        "modalities": ["text"],
        "context_length": 8192,
        "default_max_output_tokens": None,
        "precision": "bf16",
        "pricing": {
            "prompt_token_price": 0.1,
            "completion_token_price": 0.2,
            "currency": "USD",
            "free_until": None,
        },
        "capabilities": {"tools": True},
    }
    item.update(overrides)
    return item


def test_llm_listing_projects_consumed_fields_and_drops_the_rest() -> None:
    listing = codec.llm_listing(jbytes({"object": "list", "data": [llm_item()]}), KEY)
    dumped = listing.models[0].model_dump()
    assert dumped["model_id"] == "model-a"
    assert dumped["task"] == "embedding"
    assert "owned_by" not in dumped
    assert "capabilities" not in dumped
    assert "object" not in dumped
    assert listing.completeness == "unknown"


def test_llm_missing_required_field_is_invalid() -> None:
    item = llm_item()
    del item["task"]
    assert raise_code(codec.llm_listing, jbytes({"data": [item]}), KEY) == "invalid_response"


def test_llm_wrong_type_is_invalid_even_for_a_bool_number() -> None:
    assert (
        raise_code(codec.llm_listing, jbytes({"data": [llm_item(created=True)]}), KEY)
        == "invalid_response"
    )
    assert raise_code(codec.llm_listing, jbytes({"data": [llm_item(task=3)]}), KEY) == (
        "invalid_response"
    )


def test_llm_negative_counts_and_prices_are_invalid() -> None:
    assert raise_code(codec.llm_listing, jbytes({"data": [llm_item(created=-1)]}), KEY) == (
        "invalid_response"
    )
    bad = llm_item(pricing={"prompt_token_price": -0.1, "completion_token_price": 1})
    assert raise_code(codec.llm_listing, jbytes({"data": [bad]}), KEY) == "invalid_response"


def test_llm_pricing_null_is_accepted_and_wrong_pricing_is_not() -> None:
    assert codec.llm_model(jbytes(llm_item(pricing=None)), KEY).pricing is None
    bad = llm_item(pricing={"prompt_token_price": "cheap", "completion_token_price": 1})
    assert raise_code(codec.llm_model, jbytes(bad), KEY) == "invalid_response"


def test_llm_listing_over_five_hundred_records_is_refused() -> None:
    items = [llm_item(id=f"m-{n}") for n in range(catalog.LLM_MAX_RECORDS + 1)]
    assert raise_code(codec.llm_listing, jbytes({"data": items}), KEY) == "invalid_response"


def test_llm_missing_data_is_invalid() -> None:
    assert raise_code(codec.llm_listing, jbytes({"object": "list"}), KEY) == "invalid_response"


def test_llm_identifier_longer_than_the_raw_limit_is_invalid() -> None:
    assert raise_code(codec.llm_model, jbytes(llm_item(id="m" * 257)), KEY) == "invalid_response"


# --- Platform models ------------------------------------------------------------------------------


def platform_model(**overrides):
    model = {
        "id": "00000000-0000-4000-8000-000000000001",
        "owner_username": "owner-1",
        "owner_id": "00000000-0000-4000-8000-0000000000aa",
        "org_id": "00000000-0000-4000-8000-0000000000bb",
        "slug": "model-a",
        "name": "Model A",
        "description": "Synthetic description",
        "license": "mit",
        "modality": "VISION",
        "stage": "EXPERIMENTAL",
        "visibility": "PRIVATE",
        "versions_count": 2,
        "architecture": "yolov8n",
        "created_at": STAMP,
        "updated_at": "2026-01-02T00:00:00.123456+03:00",
        "model_card": "x" * 10,
        "demo_config": {"anything": ["goes"]},
        "tags": [],
    }
    model.update(overrides)
    return model


def test_platform_page_projects_items_and_labels_the_page() -> None:
    page = codec.platform_models(
        jbytes({"items": [platform_model()] * 20, "total": 45}), KEY, 1, 20
    )
    assert page.completeness == "partial"
    assert page.returned == 20
    assert page.total == 45
    assert page.models[0].owner_username == "owner-1"
    assert "model_card" not in page.models[0].model_dump()


def test_platform_null_owner_is_kept_as_null_not_invented() -> None:
    body = {"items": [platform_model(owner_username=None)], "total": 1}
    assert codec.platform_models(jbytes(body), KEY, 1, 20).models[0].owner_username is None


def test_platform_page_with_a_silently_changed_size_is_invalid() -> None:
    body = jbytes({"items": [platform_model()] * 20, "total": 45})
    assert raise_code(codec.platform_models, body, KEY, 1, 100) == "invalid_response"


def test_platform_page_items_over_the_asked_size_are_invalid() -> None:
    body = jbytes({"items": [platform_model()] * 21, "total": 45})
    assert raise_code(codec.platform_models, body, KEY, 1, 20) == "invalid_response"


def test_platform_missing_required_field_is_invalid() -> None:
    model = platform_model()
    del model["slug"]
    assert raise_code(codec.platform_model, jbytes(model), KEY) == "invalid_response"


@pytest.mark.parametrize(
    "stamp",
    ["2026-01-01", "yesterday", "2026-01-01T00:00:00Z\x1b[2J", "\u202e" + STAMP, "x" * 5000],
)
def test_timestamps_must_be_rfc3339_date_times(stamp) -> None:
    assert raise_code(codec.platform_model, jbytes(platform_model(created_at=stamp)), KEY) == (
        "invalid_response"
    )


def test_platform_counts_must_be_plain_non_negative_integers() -> None:
    for bad in ({"versions_count": True}, {"versions_count": 1.0}, {"versions_count": -3}):
        assert raise_code(codec.platform_model, jbytes(platform_model(**bad)), KEY) == (
            "invalid_response"
        )


def test_platform_identifier_length_is_bounded_on_the_raw_record() -> None:
    assert (
        raise_code(codec.platform_model, jbytes(platform_model(id="i" * 257)), KEY)
        == "invalid_response"
    )
    assert codec.platform_model(jbytes(platform_model(id="i" * 256)), KEY).model_id == "i" * 256


# --- Platform versions and datasets ---------------------------------------------------------------


def platform_version(**overrides):
    version = {
        "id": "version-1",
        "version_tag": "1.0",
        "framework": "pytorch",
        "file_size_bytes": 1024,
        "created_at": STAMP,
        "weights_url": "https://example.invalid/private/signed?sig=synthetic",
        "onnx_url": None,
        "tflite_url": None,
        "hyperparams": {"batch": 1, "cache": "ram", "epochs": 1, "imgsz": 32},
    }
    version.update(overrides)
    return version


def test_version_urls_become_presence_flags_and_never_values() -> None:
    listing = codec.platform_versions(jbytes([platform_version()]), KEY, 1)
    version = listing.versions[0].model_dump()
    assert version["has_weights"] is True
    assert version["has_onnx"] is False
    assert version["has_tflite"] is False
    assert "weights_url" not in version
    assert "signed" not in json.dumps(version)
    assert listing.completeness == "complete"


def test_an_empty_or_null_url_is_no_location_and_a_non_string_url_is_invalid() -> None:
    listing = codec.platform_versions(
        jbytes([platform_version(weights_url="", onnx_url="   ")]), KEY, 1
    )
    assert listing.versions[0].has_weights is False
    assert listing.versions[0].has_onnx is False
    assert (
        raise_code(codec.platform_versions, jbytes([platform_version(onnx_url=False)]), KEY, 1)
        == "invalid_response"
    )


def test_version_list_count_mismatch_is_unknown_and_absent_count_is_unknown() -> None:
    body = jbytes([platform_version()])
    assert codec.platform_versions(body, KEY, 3).completeness == "unknown"
    assert codec.platform_versions(body, KEY, None).completeness == "unknown"


def test_version_list_over_the_row_bound_is_invalid() -> None:
    rows = [platform_version(id=f"c{n}", version_tag=str(n)) for n in range(501)]
    assert raise_code(codec.platform_versions, jbytes(rows), KEY, 1) == "invalid_response"


def dataset_row(**overrides):
    row = {
        "id": "00000000-0000-4000-8000-0000000000d1",
        "name": "Dataset A",
        "slug": "dataset-a",
        "modality": "VISION",
        "item_count": 12,
        "visibility": "PRIVATE",
        "updated_at": STAMP,
        "owner_username": "owner-1",
        "annotation_count": 3,
        "health_score": 0.5,
    }
    row.update(overrides)
    return row


def test_dataset_page_reads_paging_from_headers_case_insensitively() -> None:
    headers = (("X-Has-Next", "1"), ("x-total-count", "45"))
    page = codec.platform_datasets(jbytes([dataset_row()] * 20), KEY, 1, 20, headers)
    assert page.completeness == "partial"
    assert page.scope == "unknown"
    assert page.datasets[0].dataset_id == "00000000-0000-4000-8000-0000000000d1"


def test_a_repeated_paging_header_is_unclear_hence_unknown() -> None:
    headers = (("X-Has-Next", "0"), ("x-has-next", "0"))
    assert codec.platform_datasets(jbytes([dataset_row()]), KEY, 1, 20, headers).completeness == (
        "unknown"
    )


def test_dataset_page_without_headers_is_unknown_not_complete() -> None:
    assert codec.platform_datasets(jbytes([dataset_row()]), KEY, 1, 20, ()).completeness == (
        "unknown"
    )


def test_dataset_rows_over_the_asked_size_are_invalid() -> None:
    rows = jbytes([dataset_row()] * 21)
    headers = (("X-Has-Next", "0"),)
    assert raise_code(codec.platform_datasets, rows, KEY, 1, 20, headers) == "invalid_response"


def test_dataset_missing_item_count_is_invalid() -> None:
    row = dataset_row()
    del row["item_count"]
    assert raise_code(codec.platform_datasets, jbytes([row]), KEY, 1, 20, ()) == "invalid_response"


def test_dataset_negative_item_count_is_invalid() -> None:
    assert (
        raise_code(codec.platform_datasets, jbytes([dataset_row(item_count=-1)]), KEY, 1, 20, ())
        == "invalid_response"
    )


def test_llm_display_text_is_cleaned_and_an_identifier_with_a_format_character_is_refused() -> None:
    model = codec.llm_model(jbytes(llm_item(precision="bf\u202e16")), KEY)
    assert model.precision == "bf16"
    split = llm_item(id="model\u200ba")
    assert raise_code(codec.llm_model, jbytes(split), KEY) == "invalid_response"


def test_platform_display_text_is_cleaned_and_format_characters_in_ids_are_refused() -> None:
    model = codec.platform_model(jbytes(platform_model(name="A\u202eB")), KEY)
    assert model.name == "AB"
    assert raise_code(codec.platform_model, jbytes(platform_model(slug="model\u200ba")), KEY) == (
        "invalid_response"
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "sk-li\u200bve-x"),
        ("owner_username", "own\u2066er"),
        ("slug", "mo\u00addel"),
        ("id", "line\u2028break"),
    ],
)
def test_platform_identifiers_refuse_format_and_separator_characters(field, value) -> None:
    assert raise_code(codec.platform_model, jbytes(platform_model(**{field: value})), KEY) == (
        "invalid_response"
    )


def test_a_version_tag_with_a_format_character_is_refused() -> None:
    assert (
        raise_code(
            codec.platform_versions, jbytes([platform_version(version_tag="1.\u200b0")]), KEY, 1
        )
        == "invalid_response"
    )


def test_a_dataset_slug_with_a_format_character_is_refused() -> None:
    assert (
        raise_code(
            codec.platform_datasets, jbytes([dataset_row(slug="data\u200bset")]), KEY, 1, 20, ()
        )
        == "invalid_response"
    )


def test_an_llm_task_with_a_format_character_is_refused() -> None:
    assert raise_code(codec.llm_model, jbytes(llm_item(task="emb\u200bedding")), KEY) == (
        "invalid_response"
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", " model-uuid-1"),
        ("owner_username", "owner-1 "),
        ("slug", "\u3000model-a"),
    ],
)
def test_platform_identifiers_with_edge_whitespace_are_refused_not_trimmed(field, value) -> None:
    assert raise_code(codec.platform_model, jbytes(platform_model(**{field: value})), KEY) == (
        "invalid_response"
    )


@pytest.mark.parametrize("value", [" llm-a", "llm-a ", "\u3000llm-a"])
def test_an_llm_identifier_with_edge_whitespace_is_refused_not_trimmed(value) -> None:
    assert raise_code(codec.llm_model, jbytes(llm_item(id=value)), KEY) == "invalid_response"


@pytest.mark.parametrize("value", [" chat", "chat ", "   ", "\u3000chat"])
def test_a_task_argument_with_edge_whitespace_is_refused_not_trimmed(value) -> None:
    assert raise_code(catalog.task_argument, value) == "invalid_request"


@pytest.mark.parametrize(
    "stamp",
    [
        "2026-13-99T99:99:99Z",
        "2026-02-30T00:00:00Z",
        "2026-01-01T00:00:00",
        "2026-01-01T00:00:00+24:00",
        "\u0662\u0660\u0662\u0666-\u0660\u0661-\u0660\u0661"
        "T\u0660\u0660:\u0660\u0660:\u0660\u0660Z",
        "2026-01-01T00:00:00.1234567Z",
        "2026-01-01T00:00:00Z\n",
    ],
)
def test_a_stamp_that_is_not_a_real_rfc_3339_date_time_is_refused(stamp) -> None:
    assert raise_code(codec.platform_model, jbytes(platform_model(created_at=stamp)), KEY) == (
        "invalid_response"
    )


@pytest.mark.parametrize(
    "stamp",
    ["2026-01-01T00:00:00Z", "2026-03-29T12:30:00.5+03:00", "2026-01-01T00:00:00+14:00"],
)
def test_a_real_rfc_3339_stamp_is_kept(stamp) -> None:
    assert codec.platform_model(jbytes(platform_model(created_at=stamp)), KEY).created_at == stamp


def test_a_short_page_that_announces_more_is_refused() -> None:
    # Twenty were asked, five came, and the headers say more pages follow: rows would be skipped.
    assert raise_code(catalog.dataset_page, 1, 20, 5, ("1",), ()) == "invalid_response"
    assert raise_code(catalog.dataset_page, 1, 20, 0, ("1",), ()) == "invalid_response"


def test_a_short_last_page_is_fine() -> None:
    assert catalog.dataset_page(2, 20, 5, ("0",), ()) == "last_page"


def test_a_count_above_the_exact_json_integer_range_is_refused() -> None:
    too_big = catalog.MAX_COUNT + 1
    assert raise_code(
        codec.platform_versions, jbytes([platform_version(file_size_bytes=too_big)]), KEY, 1
    ) == ("invalid_response")


SPLIT_SECRET = "sk-live-ABCDEFGH12345678"


@pytest.mark.parametrize(
    "entry,body,args",
    [
        ("platform_model", lambda s: platform_model(architecture=s), ()),
        ("platform_versions", lambda s: [platform_version(framework=s)], (1,)),
        ("platform_datasets", lambda s: [dataset_row(name=s)], (1, 20, ())),
        ("llm_model", lambda s: llm_item(precision=s), ()),
        (
            "llm_model",
            lambda s: llm_item(
                pricing={"prompt_token_price": 1, "completion_token_price": 1, "currency": s}
            ),
            (),
        ),
    ],
)
def test_every_entry_point_refuses_a_secret_rebuilt_by_cleaning(entry, body, args) -> None:
    split = SPLIT_SECRET[:6] + "\u200b" + SPLIT_SECRET[6:]
    call = getattr(codec, entry)
    assert raise_code(call, jbytes(body(split)), KEY, *args) == "invalid_response"
