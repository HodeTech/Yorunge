"""What the reviews of the version layer found unpinned: each test fails on a changed check.

The model, the codec and the errors held checks that no other test reached on its own, because
every tamper in the older tests broke an earlier check first (the digest, a type, a count). These
tests isolate them: a forged binding is re-signed so that only one field is wrong, a provider answer
is wrong in exactly one place, a model is built directly. They also pin the closed codes the pure
functions owe their callers for arguments of the wrong type.
"""

from __future__ import annotations

import json
from types import MappingProxyType

import pytest

from tests.contracts.test_dataset_version import (
    DATASET,
    FIXTURE,
    LABELS_DIGEST,
    MANIFEST_DIGEST,
    SERVICE,
    VERSION,
    bind,
    code_of,
    forged,
    listed,
    observation,
)
from tests.contracts.test_dataset_version_codec import (
    KEY,
    OBSERVED,
    detail,
    detail_body,
    page,
    page_body,
    raw,
    splits_body,
)
from yorunge.application.dataset_version_codec import observation as join
from yorunge.application.dataset_version_codec import (
    provider_time,
    version_page,
    version_splits,
)
from yorunge.domain.credentials import ServiceTarget, normalize_target
from yorunge.domain.dataset_version import (
    DatasetVersionBinding,
    DatasetVersionCheck,
    DatasetVersionList,
    changed_fields,
    class_labels_sha256,
    decode_binding,
    require_same_service,
)
from yorunge.domain.errors import MESSAGES, DatasetVersionChanged, YorungeError

OTHER = ServiceTarget(service_origin="https://other.example.org", api_base_path="/api/v1")


def page_values(**changes):
    return {
        "schema_version": 1,
        "kind": "dataset_version_list",
        "dataset_id": DATASET,
        "page": 1,
        "page_size": 20,
        "total": 1,
        "has_next": False,
        "items": (listed(),),
        "observed_at": OBSERVED,
        **changes,
    }


# --- the pure functions owe a closed code for what they cannot compare ----------------------------


def test_bind_refuses_a_service_that_does_not_encode_with_a_closed_code():
    odd = ServiceTarget(service_origin="https://api.example.org", api_base_path="/api/v1\ud800")
    assert code_of(lambda: bind(observation(), odd)) == "invalid_request"


@pytest.mark.parametrize("bad", [None, {}, "v1", 5])
def test_check_refuses_an_observation_of_the_wrong_type_with_a_closed_code(bad):
    made = bind(observation(), SERVICE)
    assert code_of(lambda: made.check(bad, active=SERVICE)) == "invalid_request"
    assert code_of(lambda: changed_fields(made, bad)) == "invalid_request"


@pytest.mark.parametrize("bad", [None, "https://api.example.org/api/v1", 5])
def test_check_and_the_gate_refuse_an_active_target_of_the_wrong_type_not_as_a_changed_state(bad):
    made = bind(observation(), SERVICE)
    assert code_of(lambda: made.check(observation(), active=bad)) == "invalid_request"
    assert code_of(lambda: require_same_service(made, bad)) == "invalid_request"
    assert code_of(lambda: require_same_service(None, SERVICE)) == "invalid_request"


def test_the_provider_gate_comes_before_the_dataset_check():
    made = bind(observation(), SERVICE)
    elsewhere = observation(dataset_id="33333333-3333-4333-8333-333333333333")
    # Wrong on both counts: the provider is what is reported, not the caller's mix-up of datasets.
    assert code_of(lambda: made.check(elsewhere, active=OTHER)) == "state_changed"
    assert code_of(lambda: made.check(elsewhere, active=SERVICE)) == "invalid_request"


# --- a binding file is exactly the canonical bytes of a valid one --------------------------------


def test_the_longest_service_round_trips_through_the_artifact():
    origin = "https://api.example.org"
    target = normalize_target(origin + "/" + "a" * (2048 - len(origin) - 1))
    made = bind(observation(), target, manifest_digest=MANIFEST_DIGEST, manifest_file_count=10)
    data = made.encoded()
    assert len(data) > 2048  # a binding is allowed to be larger than a service alone
    assert decode_binding(data) == made


def test_the_policy_version_of_a_binding_is_an_integer():
    body = json.loads(FIXTURE.read_bytes())
    for bad in (True, 1.0, "1", None):
        with pytest.raises(ValueError):
            DatasetVersionBinding.model_validate({**body, "policy_version": bad})


@pytest.mark.parametrize(
    "changes",
    [
        {"dataset_id": "not-a-uuid"},
        {"dataset_id": "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"},
        {"version_id": "{22222222-2222-4222-8222-222222222222}"},
        {"version_id": "22222222222242228222222222222222"},
        {"version_tag": "a/b"},
        {"version_tag": ".."},
        {"version_tag": "x" * 129},
        {"created_at": "2026-11-04T10:11:12Z"},
        {"created_at": "2026-11-04T10:11:12.123456+00:00"},
        {"observed_at": "2026-11-08 12:00:00.000000"},
        {"observed_at": "yesterday"},
        {"is_frozen": False},  # a version that was never frozen is not bound
    ],
    ids=lambda changes: next(iter(changes)) + "=" + str(next(iter(changes.values())))[:12],
)
def test_a_binding_file_with_one_wrong_field_and_the_right_digest_is_invalid(changes):
    assert code_of(lambda: decode_binding(forged(**changes))) == "binding_invalid"


# --- the models are validated on their own, not only through the codec ----------------------------


def test_a_page_model_validates_its_identity_and_its_time_even_when_it_shows_no_row():
    page_values_value = page_values(dataset_id="not-a-uuid", items=(), total=0)
    with pytest.raises(ValueError):
        DatasetVersionList(**page_values_value)
    for stamp in ("2026-11-08 12:00", "2026-11-08T12:00:00Z"):
        page_values_value = page_values(observed_at=stamp, items=(), total=0)
        with pytest.raises(ValueError):
            DatasetVersionList(**page_values_value)


@pytest.mark.parametrize(
    "changes", [{"page": 0}, {"page": 10_001}, {"page_size": 0}, {"page_size": 101}]
)
def test_the_page_bounds_of_the_model_hold_on_their_own(changes):
    # An empty page of an empty dataset has no row, no total and no earlier page to break first.
    page_values_value = page_values(items=(), total=0, **changes)
    with pytest.raises(ValueError):
        DatasetVersionList(**page_values_value)


def test_the_rows_of_a_page_never_exceed_its_size():
    second = listed().model_copy(
        update={"version_id": "33333333-3333-4333-8333-333333333333", "version_tag": "v2"}
    )
    two = (listed(), second)
    page_values_value = page_values(items=two, page_size=1, total=2, has_next=True)
    with pytest.raises(ValueError):
        DatasetVersionList(**page_values_value)
    DatasetVersionList(**page_values(items=two, page_size=2, total=2, has_next=False))


def test_the_total_of_a_later_page_must_cover_the_row_it_shows():
    # Page 2 of size 20 starts at the 21st row: a total below 21 cannot hold the row it shows.
    for values in (
        {"page": 2, "page_size": 20, "total": 5},
        {"page": 3, "page_size": 2, "total": 4},
        {"page": 2, "page_size": 20, "total": 20},
    ):
        page_values_value = page_values(has_next=False, **values)
        with pytest.raises(ValueError):
            DatasetVersionList(**page_values_value)
    DatasetVersionList(**page_values(page=2, page_size=20, total=21, has_next=False))


def test_a_check_result_is_a_validated_model_of_the_one_success():
    good = {
        "schema_version": 1,
        "kind": "dataset_version_check",
        "result": "unchanged",
        "dataset_id": DATASET,
        "version_id": VERSION,
        "version_tag": "v1",
        "binding_digest": "ab" * 32,
        "observed_at": OBSERVED,
    }
    DatasetVersionCheck.model_validate(good)
    for bad in (
        {"dataset_id": "x"},
        {"version_id": VERSION.upper().replace("-", "")},
        {"version_tag": "a/b"},
        {"observed_at": "2026-11-08"},
        {"result": "changed"},
    ):
        with pytest.raises(ValueError):
            DatasetVersionCheck.model_validate({**good, **bad})


def test_the_manifest_counts_at_their_edges_are_bound_and_beyond_them_are_refused():
    top = 2**63 - 1
    empty = observation(
        item_count=0,
        split_counts={"train": 0, "val": 0, "test": 0, "unassigned": 0},
        annotated_item_count=0,
        total_annotation_count=0,
    )
    made = bind(empty, SERVICE, manifest_digest=MANIFEST_DIGEST, manifest_file_count=0)
    assert made.local_manifest.file_count == 0
    assert made.local_manifest.relation == "count_matches"
    assert decode_binding(made.encoded()) == made
    big = bind(observation(), SERVICE, manifest_digest=MANIFEST_DIGEST, manifest_file_count=top)
    assert big.local_manifest.file_count == top
    assert big.local_manifest.relation == "count_differs"
    assert decode_binding(big.encoded()) == big
    for count in (top + 1, -1):
        assert (
            code_of(
                lambda count=count: bind(
                    observation(),
                    SERVICE,
                    manifest_digest=MANIFEST_DIGEST,
                    manifest_file_count=count,
                )
            )
            == "invalid_request"
        )


def test_class_labels_may_be_any_mapping_not_only_a_dict():
    plain = [
        {"id": 11, "name": "kedi", "sort_order": 1, "annotation_count": 7},
        {"id": 2, "name": "köpek", "sort_order": 0, "annotation_count": 4},
    ]
    proxied = [MappingProxyType(label) for label in plain]
    assert class_labels_sha256(proxied) == LABELS_DIGEST == class_labels_sha256(plain)


def test_a_changed_error_names_only_closed_fields_and_refuses_a_mixed_list():
    DatasetVersionChanged(("created_at", "version_tag"))
    for bad in (("created_at", "zzz"), ("aaa", "created_at"), ("is_partial", "nope")):
        with pytest.raises(ValueError):
            DatasetVersionChanged(bad)


def test_no_message_of_a_drifted_binding_suggests_making_a_new_one():
    # ADR-0033 section 3: a version that changed or is gone is not a reason to re-create anything.
    for code in ("dataset_version_changed", "dataset_version_missing"):
        text = MESSAGES[code].casefold()
        for forbidden in ("yeni bir bağ", "yeniden oluştur", "yeniden bağla", "üretin", "bağ üret"):
            assert forbidden not in text, (code, forbidden)


# --- the codec refuses each wrong field on its own ----------------------------------------------


def test_a_detail_with_a_non_canonical_id_is_not_an_answer():
    for bad in (
        "not-a-uuid",
        "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA",
        "{22222222-2222-4222-8222-222222222222}",
        "22222222222242228222222222222222",
    ):
        assert code_of(lambda bad=bad: detail(detail_body(id=bad))) == "invalid_response", bad


def test_joining_two_reads_with_a_bad_stamp_is_not_an_answer_and_never_none():
    found = detail(detail_body())
    splits = version_splits(raw(splits_body()), secret=KEY)
    assert join(found, splits, observed_at=OBSERVED).observed_at == OBSERVED
    for bad in ("yesterday", "2026-11-08T12:00:00Z", "2026-11-08 12:00:00.000000", None):
        assert code_of(lambda bad=bad: join(found, splits, observed_at=bad)) == "invalid_response"


def test_a_detail_with_a_negative_count_is_not_an_answer():
    for name in ("item_count", "annotated_item_count", "total_annotation_count"):
        assert code_of(lambda name=name: detail(detail_body(**{name: -1}))) == "invalid_response"
    negative_split = {"train": -1, "val": 2, "test": 1, "unassigned": 1}
    assert code_of(lambda: detail(detail_body(split_config=negative_split))) == "invalid_response"
    negative_label = [{"id": 1, "name": "x", "sort_order": 0, "annotation_count": -1}]
    assert (
        code_of(lambda: detail(detail_body(class_labels_snapshot=negative_label)))
        == "invalid_response"
    )


def test_a_page_of_a_bad_dataset_or_with_a_bad_stamp_is_not_an_answer():
    empty = page_body([], total=0)
    assert code_of(lambda: page(empty, dataset_id="not-a-uuid")) == "invalid_response"
    assert (
        code_of(
            lambda: version_page(
                raw(empty), dataset_id=DATASET, page=1, secret=KEY, observed_at="yesterday"
            )
        )
        == "invalid_response"
    )


def test_a_time_whose_utc_conversion_leaves_the_calendar_is_not_a_time():
    for edge in (
        "0001-01-01T00:00:00+23:59",
        "0001-01-01T00:00:00+00:01",
        "9999-12-31T23:59:59-23:59",
        "9999-12-31T23:59:59.999999-00:01",
    ):
        assert code_of(lambda edge=edge: provider_time(edge)) == "invalid_response", edge
    assert provider_time("0001-01-01T00:00:00Z") == "0001-01-01T00:00:00.000000Z"
    assert provider_time("9999-12-31T23:59:59.999999Z") == "9999-12-31T23:59:59.999999Z"


# --- a refused input keeps nothing of its text in the error --------------------------------------


def test_a_file_that_is_not_a_binding_keeps_none_of_its_text_in_the_error():
    secret_looking = b'{"private": "PRIVATE-FILE-CANARY"' + b" " * 40  # truncated JSON
    with pytest.raises(YorungeError) as error:
        decode_binding(secret_looking)
    assert error.value.code == "binding_invalid"
    assert error.value.__context__ is None
    assert error.value.__cause__ is None


def test_class_labels_that_do_not_encode_keep_no_class_name_in_the_error():
    labels = [{"id": "a", "name": "PRIVATE-\ud800-NAME", "sort_order": 0, "annotation_count": 1}]
    with pytest.raises(YorungeError) as error:
        class_labels_sha256(labels)
    assert error.value.code == "invalid_response"
    assert error.value.__context__ is None
    assert error.value.__cause__ is None


def test_a_binding_that_cannot_be_made_keeps_no_cause():
    odd = ServiceTarget(service_origin="https://api.example.org", api_base_path="/api/v1\ud800")
    observation_value = observation()
    with pytest.raises(YorungeError) as error:
        bind(observation_value, odd)
    assert error.value.__context__ is None
    assert error.value.__cause__ is None
