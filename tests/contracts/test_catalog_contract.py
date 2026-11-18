"""The catalog contract (P02-4c, ADR-0035): consumed shapes, page rules, completeness, addresses.

Every fixture here is synthetic: no real identifier, key or person. The provider answers are
written from the public schema summary, so the tests say what a *consumed* field must look like and
what a silently changed page or an unexpected secret must do.
"""

import json
from dataclasses import dataclass

import pytest

from yorunge.application import catalog as codec
from yorunge.domain import catalog
from yorunge.domain.credentials import SecretValue
from yorunge.domain.errors import YorungeError

KEY = SecretValue("synthetic-catalog-canary-0001")


def raise_code(callable_, *args, **kwargs) -> str:
    with pytest.raises(YorungeError) as info:
        callable_(*args, **kwargs)
    return info.value.code


def jbytes(value: object) -> bytes:
    return json.dumps(value).encode("utf-8")


# --- addresses ------------------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["owner-1", "a.b_c-9", "x" * 128])
def test_segment_accepts_the_allowed_alphabet(value: str) -> None:
    assert catalog.segment(value) == value


@pytest.mark.parametrize(
    "value",
    ["", ".", "..", "a/b", "a%2e", "a?b", "a#b", "a b", "a\nb", "x" * 129, "ö", None],
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
    ],
)
def test_platform_page_labels(page, size, total, returned, expected) -> None:
    assert catalog.platform_page(page, size, total, returned) == expected


def test_a_silently_smaller_page_is_invalid_not_complete() -> None:
    # Asked for 100, received 20 of 45: the old formula would call this complete.
    assert raise_code(catalog.platform_page, 1, 100, 45, 20) == "invalid_response"


@pytest.mark.parametrize("total", [-1, True, "45", None])
def test_platform_total_must_be_a_non_negative_integer(total) -> None:
    assert raise_code(catalog.platform_page, 1, 20, total, 0) == "invalid_response"


@pytest.mark.parametrize(
    "has_next,expected",
    [
        (None, "unknown"),
        ("maybe", "unknown"),
        ("TRUE", "unknown"),
        ("true", "partial"),
        ("false", "complete"),
    ],
)
def test_dataset_header_labels_are_exact_or_unknown(has_next, expected) -> None:
    assert catalog.dataset_page(1, 20, 20, has_next, None) == expected


def test_dataset_last_page_is_not_complete() -> None:
    assert catalog.dataset_page(3, 20, 5, "false", None) == "last_page"


def test_dataset_total_header_must_agree_with_rows_and_has_next() -> None:
    assert catalog.dataset_page(1, 20, 20, "true", "45") == "partial"
    assert raise_code(catalog.dataset_page, 1, 20, 19, "true", "45") == "invalid_response"
    assert raise_code(catalog.dataset_page, 1, 20, 20, "false", "45") == "invalid_response"
    # An unreadable total is ignored; the has-next header alone decides the label.
    assert catalog.dataset_page(1, 20, 20, "true", "many") == "partial"


def test_version_list_is_complete_only_when_it_matches_the_detail() -> None:
    assert catalog.versions_listing(3, 3) == "complete"
    assert catalog.versions_listing(3, 2) == "unknown"
    assert raise_code(catalog.checked_versions, 3, 2) == "invalid_response"


# --- resolution (ADR-0035 Karar 5) ----------------------------------------------------------------


@dataclass(frozen=True)
class Version:
    version_id: str
    version_tag: str
    created_at: str


VERSIONS = (
    Version("v-1", "1.0", "2026-01-01T00:00:00Z"),
    Version("v-2", "1.1", "2026-02-01T00:00:00Z"),
    Version("v-3", "1.1", "2026-03-01T00:00:00Z"),
)


def test_one_tag_selects_one_version() -> None:
    assert catalog.resolve_version(VERSIONS, "1.0").version_id == "v-1"


def test_no_matching_tag_is_not_a_proof_of_absence() -> None:
    assert raise_code(catalog.resolve_version, VERSIONS, "9.9") == "model_not_visible"


def test_two_versions_with_one_tag_are_ambiguous_never_picked() -> None:
    assert raise_code(catalog.resolve_version, VERSIONS, "1.1") == "model_ambiguous"
    assert [item.version_id for item in catalog.candidates(VERSIONS, "1.1")] == ["v-2", "v-3"]


def test_candidates_are_capped_at_five() -> None:
    many = tuple(Version(f"v-{n}", "dup", "2026-01-01T00:00:00Z") for n in range(9))
    assert len(catalog.candidates(many, "dup")) == catalog.MAX_CANDIDATES


def test_tag_is_checked_before_comparison() -> None:
    assert raise_code(catalog.resolve_version, VERSIONS, "") == "invalid_request"


def test_llm_task_mismatch_is_refused_unknown_names_are_not() -> None:
    catalog.task_matches("embedding", "embedding")
    assert raise_code(catalog.task_matches, "embedding", "chat") == "model_task_mismatch"


# --- display (untrusted text) ---------------------------------------------------------------------


def test_display_text_drops_controls_and_bidi_overrides_and_flattens_breaks() -> None:
    assert catalog.text("a\x07b‮c\nd\te", 100) == "abc d e"


def test_display_text_is_bounded_and_says_so() -> None:
    cut = catalog.text("x" * 300, 10)
    assert len(cut) == 10 and cut.endswith(catalog.ELLIPSIS)


def test_display_text_keeps_none_and_refuses_a_useless_limit() -> None:
    assert catalog.text(None, 10) is None
    assert raise_code(catalog.text, "x", 1) == "invalid_response"


# --- reading an answer (ADR-0035 Karar 8) ---------------------------------------------------------


def test_the_secret_is_refused_wherever_it_sits_even_in_a_dropped_field() -> None:
    answer = jbytes({"data": [], "debug": KEY.reveal()})
    assert raise_code(codec.read, answer, KEY) == "invalid_response"


def test_the_secret_as_a_key_is_refused_too() -> None:
    answer = jbytes({"data": [], KEY.reveal(): 1})
    assert raise_code(codec.read, answer, KEY) == "invalid_response"


def test_duplicate_keys_and_nonfinite_numbers_are_refused_by_the_strict_parser() -> None:
    assert raise_code(codec.read, b'{"data": [], "data": []}', KEY) == "invalid_response"
    assert raise_code(codec.read, b'{"data": [NaN]}', KEY) == "invalid_response"


def test_an_answer_over_the_shared_budget_is_refused() -> None:
    assert raise_code(codec.read, b"x" * (codec.JSON_LIMIT + 1), KEY) == "invalid_response"


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
    listing = codec.llm_listing(codec.read(jbytes({"object": "list", "data": [llm_item()]}), KEY))
    model = listing.models[0]
    dumped = model.model_dump()
    assert dumped["model_id"] == "model-a" and dumped["task"] == "embedding"
    assert "owned_by" not in dumped and "capabilities" not in dumped and "object" not in dumped
    assert listing.completeness == "unknown"


def test_llm_missing_required_field_is_invalid() -> None:
    item = llm_item()
    del item["task"]
    assert raise_code(codec.llm_listing, {"data": [item]}) == "invalid_response"


def test_llm_wrong_type_is_invalid_even_for_a_bool_number() -> None:
    assert raise_code(codec.llm_listing, {"data": [llm_item(created=True)]}) == "invalid_response"
    assert raise_code(codec.llm_listing, {"data": [llm_item(task=3)]}) == "invalid_response"


def test_llm_pricing_null_is_accepted_and_wrong_pricing_is_not() -> None:
    assert codec.llm_model(llm_item(pricing=None)).pricing is None
    bad = llm_item(pricing={"prompt_token_price": "cheap", "completion_token_price": 1})
    assert raise_code(codec.llm_model, bad) == "invalid_response"


def test_llm_listing_over_five_hundred_records_is_refused() -> None:
    items = [llm_item(id=f"m-{n}") for n in range(catalog.LLM_MAX_RECORDS + 1)]
    assert raise_code(codec.llm_listing, {"data": items}) == "invalid_response"


def test_llm_missing_data_is_invalid() -> None:
    assert raise_code(codec.llm_listing, {"object": "list"}) == "invalid_response"


def test_llm_display_fields_are_cleaned_but_identifiers_are_not() -> None:
    model = codec.llm_model(llm_item(precision="bf‮16", id="model​a"))
    assert model.precision == "bf16"
    assert model.model_id == "model​a"  # a cleaned identifier could name another model


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
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
        "model_card": "x" * 10,
        "demo_config": {"anything": ["goes"]},
        "tags": [],
    }
    model.update(overrides)
    return model


def test_platform_page_projects_items_and_labels_the_page() -> None:
    page = codec.platform_models(
        codec.read(jbytes({"items": [platform_model()] * 20, "total": 45}), KEY), 1, 20
    )
    assert page.completeness == "partial" and page.returned == 20 and page.total == 45
    assert page.models[0].owner_username == "owner-1"
    assert "model_card" not in page.models[0].model_dump()


def test_platform_null_owner_is_kept_as_null_not_invented() -> None:
    page = codec.platform_models(
        {"items": [platform_model(owner_username=None)], "total": 1}, 1, 20
    )
    assert page.models[0].owner_username is None


def test_platform_page_with_a_silently_changed_size_is_invalid() -> None:
    body = {"items": [platform_model()] * 20, "total": 45}
    assert raise_code(codec.platform_models, body, 1, 100) == "invalid_response"


def test_platform_page_items_over_the_asked_size_are_invalid() -> None:
    body = {"items": [platform_model()] * 21, "total": 45}
    assert raise_code(codec.platform_models, body, 1, 20) == "invalid_response"


def test_platform_missing_required_field_is_invalid() -> None:
    model = platform_model()
    del model["slug"]
    assert raise_code(codec.platform_model, model) == "invalid_response"


def test_platform_display_text_is_cleaned_identifier_is_not() -> None:
    model = codec.platform_model(platform_model(name="A‮B", slug="model​a"))
    assert model.name == "AB" and model.slug == "model​a"


# --- Platform versions and datasets ---------------------------------------------------------------


def platform_version(**overrides):
    version = {
        "id": "version-1",
        "version_tag": "1.0",
        "framework": "pytorch",
        "file_size_bytes": 1024,
        "created_at": "2026-01-01T00:00:00Z",
        "weights_url": "https://example.invalid/private/signed?sig=synthetic",
        "onnx_url": None,
        "tflite_url": None,
        "hyperparams": {"batch": 1, "cache": "ram", "epochs": 1, "imgsz": 32},
    }
    version.update(overrides)
    return version


def test_version_urls_become_presence_flags_and_never_values() -> None:
    listing = codec.platform_versions([platform_version()], versions_count=1)
    version = listing.versions[0].model_dump()
    assert version["has_weights"] is True
    assert version["has_onnx"] is False and version["has_tflite"] is False
    assert "weights_url" not in version and "signed" not in json.dumps(version)
    assert listing.completeness == "complete"


def test_version_list_count_mismatch_is_unknown_for_listing() -> None:
    assert codec.platform_versions([platform_version()], versions_count=3).completeness == "unknown"


def test_version_list_over_the_row_bound_is_invalid() -> None:
    rows = [
        platform_version(id=f"c{n}", version_tag=str(n))
        for n in range(catalog.MAX_VERSION_ROWS + 1)
    ]
    assert raise_code(codec.platform_versions, rows, 1) == "invalid_response"


def dataset_row(**overrides):
    row = {
        "id": "00000000-0000-4000-8000-0000000000d1",
        "name": "Dataset A",
        "slug": "dataset-a",
        "modality": "VISION",
        "item_count": 12,
        "visibility": "PRIVATE",
        "updated_at": "2026-01-01T00:00:00Z",
        "owner_username": "owner-1",
        "annotation_count": 3,
        "health_score": 0.5,
    }
    row.update(overrides)
    return row


def test_dataset_page_reads_paging_from_headers_case_insensitively() -> None:
    page = codec.platform_datasets(
        [dataset_row()] * 20, 1, 20, {"X-Has-Next": "true", "x-total-count": "45"}
    )
    assert page.completeness == "partial" and page.scope == "unknown"
    assert page.datasets[0].dataset_id == "00000000-0000-4000-8000-0000000000d1"


def test_a_repeated_paging_header_is_unclear_hence_unknown() -> None:
    headers = {"X-Has-Next": "false", "x-has-next": "false"}
    assert codec.platform_datasets([dataset_row()], 1, 20, headers).completeness == "unknown"


def test_dataset_page_without_headers_is_unknown_not_complete() -> None:
    assert codec.platform_datasets([dataset_row()], 1, 20, {}).completeness == "unknown"


def test_dataset_rows_over_the_asked_size_are_invalid() -> None:
    rows = [dataset_row()] * 21
    assert (
        raise_code(codec.platform_datasets, rows, 1, 20, {"X-Has-Next": "false"})
        == "invalid_response"
    )


def test_dataset_missing_item_count_is_invalid() -> None:
    row = dataset_row()
    del row["item_count"]
    assert raise_code(codec.platform_datasets, [row], 1, 20, {}) == "invalid_response"
