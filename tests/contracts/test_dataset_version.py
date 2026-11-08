"""The dataset-version contract: observations, the immutable binding, the comparison, the errors.

The golden binding is computed by hand (``tests/fixtures/dataset-version-binding-v1.json``: the
Manifest v1 encoding spelled out once more, the class-label digest of two labels sorted by their
numeric ids) and is not made by the encoder under test.
"""

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from yorunge.domain.credentials import ServiceTarget, normalize_target
from yorunge.domain.dataset_manifest import canonical_manifest
from yorunge.domain.dataset_version import (
    DatasetVersionBinding,
    DatasetVersionList,
    DatasetVersionListItem,
    DatasetVersionObservation,
    SplitCounts,
    bind,
    bound_summary,
    changed_fields,
    class_labels_sha256,
    decode_binding,
    require_same_service,
    validate_version_tag,
)
from yorunge.domain.errors import (
    MESSAGES,
    VERSION_ANNOTATION_FIELDS,
    VERSION_FIELDS,
    VERSION_IDENTITY_FIELDS,
    DatasetVersionChanged,
    YorungeError,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "dataset-version-binding-v1.json"
DATASET = "11111111-1111-4111-8111-111111111111"
VERSION = "22222222-2222-4222-8222-222222222222"
SERVICE = ServiceTarget(service_origin="https://api.example.org", api_base_path="/api/v1")
LABELS = [
    {"id": 11, "name": "kedi", "sort_order": 1, "annotation_count": 7},
    {"id": 2, "name": "köpek", "sort_order": 0, "annotation_count": 4},
]
LABELS_DIGEST = "bbb830c6da4ece693adbc3ef5ced052764f68e3d65eb198ee44c7911be8b824f"
MANIFEST_DIGEST = "ab" * 32


def observation(**changes):
    value = {
        "schema_version": 1,
        "kind": "dataset_version_observation",
        "dataset_id": DATASET,
        "version_id": VERSION,
        "version_tag": "v1.0-final",
        "is_frozen": True,
        "is_partial": False,
        "is_export_ready": False,
        "item_count": 10,
        "split_counts": {"train": 6, "val": 2, "test": 1, "unassigned": 1},
        "split_total_matches_item_count": True,
        "annotated_item_count": 9,
        "total_annotation_count": 21,
        "class_count": 2,
        "class_labels_sha256": LABELS_DIGEST,
        "created_at": "2026-11-04T10:11:12.123456Z",
        "observed_at": "2026-11-08T12:00:00.000000Z",
        **changes,
    }
    return DatasetVersionObservation.model_validate(value)


def binding(**changes):
    return bind(
        observation(**changes), SERVICE, manifest_digest=MANIFEST_DIGEST, manifest_file_count=10
    )


def code_of(action):
    with pytest.raises(YorungeError) as error:
        action()
    return error.value.code


# --- the golden binding ---------------------------------------------------------------------------


def test_the_binding_is_the_hand_computed_golden_to_the_byte_and_to_the_digest():
    golden = FIXTURE.read_bytes()
    made = binding()
    assert made.encoded() == golden
    assert made.digest == "a6691786960ed3fed3ce9addeb831315156b518201e7ccd5b83c70f3d15cd58c"
    assert decode_binding(golden) == made and golden.endswith(b"}\n")
    # The digest is the SHA-256 of every field but ``digest`` and ``observed_at``.
    body = json.loads(golden)
    del body["digest"], body["observed_at"]
    spelled = json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    assert hashlib.sha256(spelled.encode("utf-8")).hexdigest() == made.digest


def test_the_class_labels_digest_is_the_hand_computed_one_whatever_the_order_they_came_in():
    assert class_labels_sha256(LABELS) == LABELS_DIGEST
    assert class_labels_sha256(list(reversed(LABELS))) == LABELS_DIGEST


def test_observing_again_gives_the_same_digest_and_the_time_is_not_part_of_it():
    first = binding()
    later = binding(observed_at="2026-12-01T00:00:00.000000Z")
    assert first.digest == later.digest and first.encoded() != later.encoded()


@pytest.mark.parametrize(
    "changes",
    [
        {"version_id": "33333333-3333-4333-8333-333333333333"},
        {"version_tag": "v2"},
        {"created_at": "2026-11-05T10:11:12.123456Z"},
        {"is_partial": True},
        {"item_count": 11, "split_total_matches_item_count": False},
        {"split_counts": {"train": 5, "val": 3, "test": 1, "unassigned": 1}},
        {"annotated_item_count": 8},
        {"total_annotation_count": 22},
        {"class_count": 3},
        {"class_labels_sha256": "cd" * 32},
        {"dataset_id": "44444444-4444-4444-8444-444444444444"},
    ],
    ids=lambda changes: "+".join(changes),
)
def test_every_bound_field_changes_the_digest(changes):
    assert binding(**changes).digest != binding().digest


def test_the_service_and_the_local_manifest_are_bound_and_the_export_flag_is_not():
    other_service = ServiceTarget(
        service_origin="https://other.example.org", api_base_path="/api/v1"
    )
    assert (
        bind(
            observation(), other_service, manifest_digest=MANIFEST_DIGEST, manifest_file_count=10
        ).digest
        != binding().digest
    )
    assert bind(observation(), SERVICE).digest != binding().digest  # no manifest
    assert (
        bind(observation(), SERVICE, manifest_digest="cd" * 32, manifest_file_count=10).digest
        != binding().digest
    )
    assert (
        bind(observation(), SERVICE, manifest_digest=MANIFEST_DIGEST, manifest_file_count=9).digest
        != binding().digest
    )
    assert binding(is_export_ready=True).digest == binding().digest  # not content, not bound


def test_the_manifest_relation_says_whether_the_counts_agree():
    same = bind(observation(), SERVICE, manifest_digest=MANIFEST_DIGEST, manifest_file_count=10)
    other = bind(observation(), SERVICE, manifest_digest=MANIFEST_DIGEST, manifest_file_count=9)
    assert same.local_manifest.relation == "count_matches"
    assert other.local_manifest.relation == "count_differs"
    assert bind(observation(), SERVICE).local_manifest is None
    assert code_of(lambda: bind(observation(), SERVICE, manifest_digest=MANIFEST_DIGEST)) == (
        "invalid_request"
    )
    assert code_of(lambda: bind(observation(), SERVICE, manifest_file_count=3)) == "invalid_request"
    assert (
        code_of(lambda: bind(observation(), SERVICE, manifest_digest="XY", manifest_file_count=3))
        == "invalid_request"
    )


def test_only_a_frozen_version_is_bound_and_a_partial_one_is_with_its_flag():
    assert code_of(lambda: bind(observation(is_frozen=False), SERVICE)) == (
        "dataset_version_not_frozen"
    )
    partial = bind(observation(is_partial=True), SERVICE)
    assert partial.is_partial is True and partial.is_frozen is True


def test_a_total_that_differs_from_the_item_count_is_recorded_and_does_not_stop_the_binding():
    odd = observation(
        item_count=11,
        split_counts={"train": 6, "val": 2, "test": 1, "unassigned": 1},
        split_total_matches_item_count=False,
    )
    made = bind(odd, SERVICE)
    assert made.split_total_matches_item_count is False and decode_binding(made.encoded()) == made


# --- the observation ------------------------------------------------------------------------------


def test_the_flag_that_says_the_split_total_matches_must_say_what_the_counts_say():
    with pytest.raises(ValidationError):
        observation(split_total_matches_item_count=False)  # 10 == 6+2+1+1
    with pytest.raises(ValidationError):
        observation(item_count=11)  # flag still True


@pytest.mark.parametrize(
    "changes",
    [
        {"dataset_id": "not-a-uuid"},
        {"version_id": "ABCDEF01-2222-4222-8222-222222222222"},
        {"version_tag": ""},
        {"version_tag": "a/b"},
        {"created_at": "2026-11-04T10:11:12Z"},
        {"observed_at": "2026-11-04 10:11:12.000000"},
        {"item_count": -1},
        {"item_count": True},
        {"item_count": 2**63},
        {"is_frozen": 1},
        {"class_labels_sha256": "AB" * 32},
        {"split_counts": {"train": True, "val": 2, "test": 1, "unassigned": 1}},
        {"split_counts": {"train": 6, "val": 2, "test": 1}},
        {"kind": "dataset_version_binding"},
        {"schema_version": 2},
        {"schema_version": True},
        {"description": "extra fields are refused"},
    ],
    ids=lambda changes: "+".join(changes),
)
def test_an_observation_is_closed_strict_and_canonical(changes):
    with pytest.raises(ValidationError):
        observation(**changes)


def test_a_list_item_is_an_observation_without_the_class_labels():
    item = DatasetVersionListItem.model_validate(
        {
            key: value
            for key, value in observation().model_dump(mode="json").items()
            if key not in {"class_count", "class_labels_sha256"}
        }
        | {"kind": "dataset_version_list_item"}
    )
    assert "class_labels_sha256" not in item.model_dump()
    assert item.split_counts.total == 10


@pytest.mark.parametrize("tag", ["v1", "a.b-c_d", "A" * 128, "1", "-", "_", "..a", "a..", ".a"])
def test_a_version_tag_is_one_closed_path_component(tag):
    assert validate_version_tag(tag) == tag


@pytest.mark.parametrize(
    "tag",
    ["", ".", "..", "A" * 129, "a/b", "a\\b", "a b", " a", "a\n", "é", "a%2fb", None, 5, b"a"],
)
def test_anything_else_is_not_a_version_tag(tag):
    with pytest.raises(ValueError):
        validate_version_tag(tag)


def test_split_counts_are_strict_counts():
    assert SplitCounts(train=0, val=0, test=0, unassigned=2**63 - 1).total == 2**63 - 1
    for bad in (True, -1, 2**63, 1.0, "1"):
        with pytest.raises(ValidationError):
            SplitCounts(train=bad, val=0, test=0, unassigned=0)


# --- class labels ---------------------------------------------------------------------------------


def label(identifier, name="x", order=0, annotations=0):
    return {"id": identifier, "name": name, "sort_order": order, "annotation_count": annotations}


def test_integer_ids_sort_as_numbers_and_string_ids_by_their_utf8_bytes():
    assert class_labels_sha256([label(10), label(9)]) == class_labels_sha256([label(9), label(10)])
    ints = class_labels_sha256([label(2), label(10)])
    assert ints != class_labels_sha256([label("2"), label("10")])  # the provider's type is kept
    text = [label("b"), label("a"), label("é")]
    assert class_labels_sha256(text) == class_labels_sha256(list(reversed(text)))
    # "é" (U+00E9) sorts after "z" by bytes; a locale-aware sort would put it before.
    expected = [label("a"), label("b"), label("é")]
    assert class_labels_sha256(text) == class_labels_sha256(expected)


@pytest.mark.parametrize(
    "labels",
    [
        [label(1), label("1")],  # mixed types
        [label(1), label(1)],  # a repeated id
        [label(True)],
        [label(1.5)],
        [label(None)],
        [label(1, name=5)],
        [label(1, order=True)],
        [label(1, annotations=-1)],
        [label(1, annotations=2**63)],
        [{"id": 1, "name": "x", "sort_order": 0}],  # a field missing
        [{**label(1), "color": "#fff"}],  # a field too many
        [label(1, name="\ud800")],  # a lone surrogate does not encode
        "ab",
        [None],
        [[]],
    ],
    ids=lambda labels: repr(labels)[:30],
)
def test_ambiguous_or_malformed_labels_are_not_an_answer(labels):
    assert code_of(lambda: class_labels_sha256(labels)) == "invalid_response"


def test_a_signed_sort_order_is_accepted_and_no_labels_have_a_digest_of_their_own():
    assert class_labels_sha256([label(1, order=-1)])
    assert class_labels_sha256([]) == hashlib.sha256(b"[]").hexdigest()


# --- the comparison -------------------------------------------------------------------------------


def test_the_closed_vocabulary_is_the_reference_s_and_nothing_else():
    assert set(VERSION_IDENTITY_FIELDS) == {
        "version_id",
        "version_tag",
        "created_at",
        "is_frozen",
        "item_count",
        "split_counts",
        "split_total_matches_item_count",
    }
    assert set(VERSION_ANNOTATION_FIELDS) == {
        "is_partial",
        "annotated_item_count",
        "total_annotation_count",
        "class_count",
        "class_labels_sha256",
    }
    assert VERSION_FIELDS == tuple(sorted(VERSION_FIELDS)) and len(VERSION_FIELDS) == 12


@pytest.mark.parametrize(
    "changes,fields",
    [
        ({}, ()),
        ({"observed_at": "2026-12-01T00:00:00.000000Z"}, ()),
        ({"is_export_ready": True}, ()),
        ({"version_id": "33333333-3333-4333-8333-333333333333"}, ("version_id",)),
        ({"version_tag": "v2"}, ("version_tag",)),
        ({"created_at": "2026-11-05T10:11:12.123456Z"}, ("created_at",)),
        ({"is_frozen": False}, ("is_frozen",)),
        ({"is_partial": True}, ("is_partial",)),
        (
            {"item_count": 11, "split_total_matches_item_count": False},
            ("item_count", "split_total_matches_item_count"),
        ),
        ({"split_counts": {"train": 5, "val": 3, "test": 1, "unassigned": 1}}, ("split_counts",)),
        ({"annotated_item_count": 8}, ("annotated_item_count",)),
        ({"total_annotation_count": 1}, ("total_annotation_count",)),
        ({"class_count": 3}, ("class_count",)),
        ({"class_labels_sha256": "cd" * 32}, ("class_labels_sha256",)),
    ],
    ids=lambda value: "+".join(value) if isinstance(value, tuple) else "+".join(value) or "same",
)
def test_the_comparison_names_exactly_the_fields_that_differ(changes, fields):
    assert changed_fields(binding(), observation(**changes)) == fields


def test_a_check_that_finds_nothing_changed_is_the_only_success():
    checked = binding().check(observation(), active=SERVICE)
    assert (checked.result, checked.binding_digest) == ("unchanged", binding().digest)
    assert (checked.dataset_id, checked.version_id, checked.version_tag) == (
        DATASET,
        VERSION,
        "v1.0-final",
    )
    assert checked.observed_at == observation().observed_at  # the observation's own time


def test_a_check_that_finds_a_difference_is_the_error_with_the_closed_detail():
    with pytest.raises(DatasetVersionChanged) as error:
        binding().check(observation(is_frozen=False), active=SERVICE)
    assert error.value.code == "dataset_version_changed" and error.value.exit_code == 7
    assert error.value.envelope()["details"] == {
        "changed_field_count": 1,
        "changed_fields": ["is_frozen"],
        "annotation_only": False,
    }
    with pytest.raises(DatasetVersionChanged) as annotation:
        binding().check(
            observation(annotated_item_count=1, total_annotation_count=2), active=SERVICE
        )
    details = annotation.value.envelope()["details"]
    assert details["annotation_only"] is True and details["changed_field_count"] == 2
    with pytest.raises(DatasetVersionChanged) as mixed:
        binding().check(observation(annotated_item_count=1, version_tag="v2"), active=SERVICE)
    assert mixed.value.annotation_only is False
    assert mixed.value.envelope()["details"]["changed_fields"] == [
        "annotated_item_count",
        "version_tag",
    ]


def test_the_plain_error_keeps_the_empty_details_and_the_subclass_refuses_unclosed_names():
    assert YorungeError("dataset_version_changed").envelope()["details"] == {}
    for bad in (
        (),
        ("version_tag", "created_at"),
        ("nope",),
        ["version_tag"],
        ("version_tag",) * 2,
    ):
        with pytest.raises(ValueError):
            DatasetVersionChanged(bad)  # type: ignore[arg-type]


def test_a_binding_for_another_provider_is_a_changed_state_before_any_field_is_compared():
    require_same_service(binding(), SERVICE)
    other = ServiceTarget(service_origin="https://api.example.org", api_base_path="/api/v2")
    assert code_of(lambda: require_same_service(binding(), other)) == "state_changed"


# --- the stored binding ---------------------------------------------------------------------------


def test_a_stored_binding_is_exactly_the_canonical_bytes_of_a_valid_one():
    golden = FIXTURE.read_bytes()
    assert (
        decode_binding(golden).digest
        == "a6691786960ed3fed3ce9addeb831315156b518201e7ccd5b83c70f3d15cd58c"
    )
    text = golden.decode()
    broken = {
        "empty": b"",
        "no final LF": golden[:-1],
        "two LF": golden + b"\n",
        "trailing space": golden[:-1] + b" \n",
        "pretty": json.dumps(json.loads(golden), indent=1).encode() + b"\n",
        "reordered keys": json.dumps(
            dict(reversed(list(json.loads(golden).items()))), separators=(",", ":")
        ).encode()
        + b"\n",
        "wrong digest": text.replace("a6691786", "b6691786").encode(),
        "changed field": text.replace('"item_count":10', '"item_count":11').encode(),
        "extra field": text.replace('"kind"', '"description":"x","kind"').encode(),
        "missing field": text.replace('"is_partial":false,', "").encode(),
        "duplicate key": text.replace(
            '"kind":', '"kind":"dataset_version_binding","kind":'
        ).encode(),
        "bool as int": text.replace('"item_count":10', '"item_count":true').encode(),
        "float": text.replace('"item_count":10', '"item_count":10.0').encode(),
        "NaN": text.replace('"item_count":10', '"item_count":NaN').encode(),
        "unfrozen": text.replace('"is_frozen":true', '"is_frozen":false').encode(),
        "BOM": b"\xef\xbb\xbf" + golden,
        "not UTF-8": golden[:10] + b"\xff" + golden[11:],
        "too long": golden + b" " * 20_000,
        "deep": b"[" * 5000,
        "list": b"[]\n",
        "not json": b"binding",
    }
    for name, data in broken.items():
        assert code_of(lambda data=data: decode_binding(data)) == "binding_invalid", name
    for not_bytes in (None, "text", bytearray(golden), 5):
        assert code_of(lambda value=not_bytes: decode_binding(value)) == "binding_invalid"


def test_the_binding_carries_no_class_name_description_author_or_url():
    text = FIXTURE.read_text()
    assert (
        "kedi" not in text
        and "köpek" not in text
        and "http" not in text.replace("https://api.example.org", "")
    )
    assert set(json.loads(text)) == set(DatasetVersionBinding.model_fields)


# --- the error catalogue --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code,exit_code",
    [
        ("dataset_version_not_found", 2),
        ("dataset_version_not_frozen", 2),
        ("dataset_version_changed", 7),
        ("dataset_version_missing", 7),
        ("binding_invalid", 2),
        ("binding_output_exists", 2),
        ("binding_write_failed", 2),
        ("binding_write_uncertain", 5),
    ],
)
def test_the_version_codes_have_a_fixed_message_and_the_reference_s_exit(code, exit_code):
    error = YorungeError(code)
    assert error.exit_code == exit_code and error.message == MESSAGES[code]
    assert error.envelope()["details"] == {} or code == "dataset_version_changed"
    assert "/" not in error.message and "http" not in error.message


# --- the service the binding names is the target as the project writes it -------------------------


def forged(**changes):
    """The golden binding with some fields changed and a digest that is right for the result."""
    body = json.loads(FIXTURE.read_bytes())
    for key, value in changes.items():
        if "." in key:
            outer, inner = key.split(".")
            body[outer][inner] = value
        else:
            body[key] = value
    unsigned = {k: v for k, v in body.items() if k not in ("digest", "observed_at")}
    body["digest"] = hashlib.sha256(canonical_manifest(unsigned)).hexdigest()
    return canonical_manifest(body) + b"\n"


@pytest.mark.parametrize(
    "service",
    [
        {"service_origin": "https://API.example.org", "api_base_path": "/api/v1"},
        {"service_origin": "https://api.example.org:443", "api_base_path": "/api/v1"},
        {"service_origin": "https://api.example.org", "api_base_path": "/api/v1/"},
        {"service_origin": "http://api.example.org", "api_base_path": "/api/v1"},
        {"service_origin": "javascript:alert(1)", "api_base_path": ""},
        {"service_origin": "not a url at all", "api_base_path": ""},
        {"service_origin": "", "api_base_path": ""},
        {"service_origin": "https://x\u0000\n.example", "api_base_path": "/a"},
        {"service_origin": "https://api.example.org", "api_base_path": "/" + "a" * 12_000},
    ],
)
def test_a_binding_file_whose_service_is_not_a_canonical_target_is_invalid(service):
    assert code_of(lambda: decode_binding(forged(service=service))) == "binding_invalid"


def test_a_service_that_is_not_canonical_cannot_be_bound_either():
    odd = ServiceTarget(service_origin="https://API.example.org", api_base_path="/api/v1/")
    assert code_of(lambda: bind(observation(), odd)) == "invalid_request"


def test_the_canonical_form_of_every_spelling_of_the_target_is_a_fixed_point():
    for spelling in (
        "https://api.example.org/api/v1",
        "https://API.EXAMPLE.ORG:443/api/v1/",
        "https://api.example.org/api/v1/",
    ):
        target = normalize_target(spelling)
        assert normalize_target(target.service_origin + target.api_base_path) == target
        assert bind(observation(), target).service == target


# --- bind refuses what it cannot bind with a closed code, never a library exception ---------------


@pytest.mark.parametrize(
    "arguments",
    [
        {"manifest_digest": "ab" * 32, "manifest_file_count": -1},
        {"manifest_digest": "ab" * 32, "manifest_file_count": 2**63},
        {"manifest_digest": "ab" * 32, "manifest_file_count": True},
        {"manifest_digest": "ab" * 32, "manifest_file_count": 1.5},
        {"manifest_digest": 5, "manifest_file_count": 1},
        {"manifest_digest": b"ab" * 32, "manifest_file_count": 1},
        {"manifest_digest": "AB" * 32, "manifest_file_count": 1},
        {"manifest_digest": "ab" * 32},
        {"manifest_file_count": 1},
    ],
)
def test_bind_refuses_a_manifest_it_cannot_describe_with_a_closed_code(arguments):
    assert code_of(lambda: bind(observation(), SERVICE, **arguments)) == "invalid_request"


@pytest.mark.parametrize(
    "who",
    [
        ("service", None),
        ("service", "https://api.example.org/api/v1"),
        ("observation", None),
        ("observation", {"dataset_id": DATASET}),
    ],
)
def test_bind_refuses_arguments_of_the_wrong_type_with_a_closed_code(who):
    name, value = who
    arguments = {"observation": observation(), "service": SERVICE}
    arguments[name] = value
    assert code_of(lambda: bind(arguments["observation"], arguments["service"])) == (
        "invalid_request"
    )


# --- check: the service first, the dataset, its own time ------------------------------------------


def test_a_binding_for_another_provider_is_state_changed_before_any_field_is_compared():
    other = ServiceTarget(service_origin="https://other.example.org", api_base_path="/api/v1")
    assert code_of(lambda: binding().check(observation(is_frozen=False), active=other)) == (
        "state_changed"
    )


def test_an_observation_of_another_dataset_is_a_mistake_not_a_change():
    other = observation(dataset_id="33333333-3333-4333-8333-333333333333")
    assert code_of(lambda: binding().check(other, active=SERVICE)) == "invalid_request"


def test_the_check_is_stamped_with_the_observations_own_time_and_never_a_later_one():
    seen = observation(observed_at="2026-11-09T10:00:00.000000Z")
    assert binding().check(seen, active=SERVICE).observed_at == "2026-11-09T10:00:00.000000Z"


# --- a binding whose digest is right but whose own flags contradict its counts is invalid ---------


@pytest.mark.parametrize(
    "changes",
    [
        {"split_total_matches_item_count": False},  # the counts match, the flag denies it
        {"local_manifest.relation": "count_differs"},  # 10 == 10, the relation denies it
        {"local_manifest.file_count": 9},  # 10 != 9, the relation (count_matches) affirms it
    ],
    ids=["flag", "relation-denies", "relation-affirms"],
)
def test_a_binding_with_a_right_digest_and_contradicting_flags_is_invalid(changes):
    assert code_of(lambda: decode_binding(forged(**changes))) == "binding_invalid"


def test_the_relation_to_the_manifest_is_about_the_items_not_the_splits():
    # 11 items, a split total of 10 (flag false), a manifest of 10 files: files and items differ
    skewed = observation(item_count=11, split_total_matches_item_count=False)
    made = bind(skewed, SERVICE, manifest_digest=MANIFEST_DIGEST, manifest_file_count=10)
    assert made.local_manifest is not None and made.local_manifest.relation == "count_differs"
    same = bind(skewed, SERVICE, manifest_digest=MANIFEST_DIGEST, manifest_file_count=11)
    assert same.local_manifest is not None and same.local_manifest.relation == "count_matches"


# --- the page model -------------------------------------------------------------------------------


def listed(**changes):
    item = DatasetVersionListItem.model_validate(
        {
            k: v
            for k, v in observation().model_dump(mode="json").items()
            if k not in ("class_count", "class_labels_sha256")
        }
        | {"kind": "dataset_version_list_item"}
    )
    return item.model_copy(update=changes)


def test_a_list_of_versions_is_a_closed_frozen_page():
    page = DatasetVersionList(
        schema_version=1,
        kind="dataset_version_list",
        dataset_id=DATASET,
        page=1,
        page_size=20,
        total=1,
        has_next=False,
        items=(listed(),),
        observed_at="2026-11-08T12:00:00.000000Z",
    )
    assert json.loads(page.model_dump_json())["kind"] == "dataset_version_list"
    with pytest.raises(ValidationError):
        page.total = 2  # type: ignore[misc]


@pytest.mark.parametrize(
    "changes",
    [
        {"has_next": True},  # 1 * 20 < 1 is false
        {"total": 0},  # one row is shown, the total says none
        {"page_size": 0},
        {"page_size": 101},
        {"page": 0},
        {"page": 10_001},
        {"kind": "dataset_version_observation"},
        {"dataset_id": "33333333-3333-4333-8333-333333333333"},  # not the rows' dataset
        {"items": ()},  # fine: an empty page; see the accepting test below
    ],
)
def test_a_page_that_contradicts_itself_is_not_a_page(changes):
    values = {
        "schema_version": 1,
        "kind": "dataset_version_list",
        "dataset_id": DATASET,
        "page": 1,
        "page_size": 20,
        "total": 1,
        "has_next": False,
        "items": (listed(),),
        "observed_at": "2026-11-08T12:00:00.000000Z",
        **changes,
    }
    if changes == {"items": ()}:
        assert DatasetVersionList(**values).items == ()  # total 1, no rows shown: past the end
        return
    with pytest.raises(ValueError):
        DatasetVersionList(**values)


@pytest.mark.parametrize("path", ["/tmp/a\nb.json", "/tmp/\udcff.json", "/" + "x" * 4096, ""])
def test_the_report_of_a_binding_carries_only_a_path_it_can_report(path):
    with pytest.raises(ValidationError):
        bound_summary(bind(observation(), SERVICE), path)


def test_the_report_of_a_binding_is_its_digest_and_where_it_is_not_the_file():
    held = bind(observation(), SERVICE)
    report = bound_summary(held, "/tmp/Yörünge/binding.json")
    assert (report.binding_digest, report.binding_path) == (
        held.digest,
        "/tmp/Yörünge/binding.json",
    )
    assert report.version_tag == held.version_tag and report.local_manifest is None
