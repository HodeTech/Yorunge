"""Independent consumed-field, request and literal-secret boundaries; no live account."""

import json
from functools import partial
from pathlib import Path

import pytest
from pydantic import ValidationError

from yorunge.application import platform_upload_codec as codec
from yorunge.domain.credentials import SecretValue
from yorunge.domain.dataset_upload import UploadOwner
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import YorungeError
from yorunge.domain.platform_upload import LocatedDataset

PLAN = DatasetUploadPlanV2.model_validate_json(
    (Path(__file__).parents[1] / "fixtures/dataset-upload-plan-v2.json").read_bytes()
)
SCOPE = PLAN.scope
PARAMETERS = PLAN.parameters
DATASET = "00000000-0000-4000-8000-000000000009"
OTHER = "00000000-0000-4000-8000-000000000099"
SECRET = SecretValue("synthetic-platform-secret")


def encoded(value):
    return json.dumps(value, ensure_ascii=False).encode()


def project(**updates):
    return {
        "id": SCOPE.project_id,
        "owner_id": SCOPE.owner.id,
        "org_id": None,
        "visibility": "private",
        **updates,
    }


def dataset(**updates):
    return {
        **project(id=DATASET),
        "name": "sample",
        "modality": "VISION",
        "contributions_enabled": False,
        **updates,
    }


def located(**updates):
    return {**dataset(), "owner_username": "sample-user", "slug": "sample-dataset", **updates}


def test_literal_create_and_separate_link_request_never_embed_project_or_grant():
    assert codec.create_content(SCOPE, PARAMETERS, SECRET) == (
        b'{"contributions_enabled":false,"modality":"VISION","name":"sample",'
        b'"tags":[],"visibility":"private"}'
    )
    assert codec.link_content(DATASET, SECRET) == (
        b'{"dataset_id":"00000000-0000-4000-8000-000000000009"}'
    )
    scope = SCOPE.model_copy(update={"owner": UploadOwner(kind="organization", id=OTHER)})
    body = json.loads(codec.create_content(scope, PARAMETERS, SECRET))
    assert body["org_id"] == OTHER
    assert "project_id" not in body
    assert "grant" not in body
    assert "owner_id" not in body


@pytest.mark.parametrize(
    "value", ["bad-id", True, 123, None, "ABCDEF00-0000-4000-8000-000000000009"]
)
def test_invalid_local_link_id_is_request_error_not_provider_error(value):
    with pytest.raises(YorungeError) as error:
        codec.link_content(value, SECRET)
    assert error.value.code == "invalid_request"
    assert error.value.exit_code == 2


@pytest.mark.parametrize(
    "updates",
    [
        {"visibility": "public", "contributions_enabled": True},
        {"visibility": "public"},
        {"contributions_enabled": True},
        {"contributions_enabled": 0},
        {"name": "x"},
        {"name": " trailing "},
        {"name": "a\nb"},
        {"modality": "OTHER"},
        {"tags": ("duplicate", "duplicate")},
        {"license": "x" * 129},
    ],
)
def test_unvalidated_parameter_copy_never_weakens_private_request_contract(updates):
    forged = PARAMETERS.model_copy(update=updates)
    with pytest.raises(YorungeError) as error:
        codec.create_content(SCOPE, forged, SECRET)
    assert error.value.code == "invalid_request"


@pytest.mark.parametrize("updates", [{"project_id": "bad-id"}, {"credential_revision": True}])
def test_unvalidated_scope_copy_is_rejected_before_create_serialization(updates):
    forged = SCOPE.model_copy(update=updates)
    with pytest.raises(YorungeError) as error:
        codec.create_content(forged, PARAMETERS, SECRET)
    assert error.value.code == "invalid_request"


@pytest.mark.parametrize("wrapped", [False, True])
def test_reported_context_create_and_exact_detail_preserve_private_owner(wrapped):
    envelope = (lambda value: {"success": True, "data": value}) if wrapped else (lambda x: x)
    selected = codec.project(encoded(envelope(project())), SCOPE, SECRET)
    me = codec.identity(encoded({"success": True, "data": {"id": SCOPE.owner.id}}), SECRET)
    codec.context(me, selected, SCOPE)
    created = codec.created(encoded(envelope(dataset())), SCOPE, PARAMETERS, SECRET)
    assert created.id == DATASET
    assert created.org_id is None
    assert codec.detail(encoded(envelope(dataset())), created, SCOPE, PARAMETERS, SECRET) == created
    assert "grant" not in created.model_dump()
    assert "permissions" not in selected.model_dump()


@pytest.mark.parametrize("kind", ["project", "dataset", "role", "link", "identity"])
@pytest.mark.parametrize("success", [False, 0, 1, "true", None])
def test_success_is_strict_control_field_even_when_metadata_would_otherwise_be_discarded(
    kind, success
):
    data = encoded({"success": success, "data": dataset()})
    with pytest.raises(YorungeError) as error:
        codec.raw(data, kind, SECRET)
    assert error.value.code == "invalid_response"


@pytest.mark.parametrize(
    "field,value", [("id", OTHER), ("owner_id", OTHER), ("visibility", "public")]
)
def test_wrong_project_binding_cannot_become_not_exposed(field, value):
    raw = encoded(project(**{field: value}))
    with pytest.raises(YorungeError) as error:
        codec.project(raw, SCOPE, SECRET)
    assert error.value.code == "invalid_response"


@pytest.mark.parametrize("field", ["id", "owner_id", "org_id", "visibility"])
def test_missing_project_control_is_not_implicit_null(field):
    value = project()
    del value[field]
    raw = encoded(value)
    with pytest.raises(YorungeError) as error:
        codec.project(raw, SCOPE, SECRET)
    assert error.value.code == "invalid_response"


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", False),
        ("id", "not-a-uuid"),
        ("owner_id", OTHER),
        ("org_id", "not-a-uuid"),
        ("name", "different"),
        ("modality", "AUDIO"),
        ("visibility", "public"),
        ("contributions_enabled", 0),
        ("contributions_enabled", True),
    ],
)
def test_create_response_requires_full_typed_private_context(field, value):
    raw = encoded(dataset(**{field: value}))
    with pytest.raises(YorungeError) as error:
        codec.created(raw, SCOPE, PARAMETERS, SECRET)
    assert error.value.code == "invalid_response"


def test_organization_owner_and_personal_org_are_reported_without_permission_inference():
    scope = SCOPE.model_copy(update={"owner": UploadOwner(kind="organization", id=OTHER)})
    raw = encoded(project(org_id=OTHER))
    selected = codec.project(raw, scope, SECRET)
    codec.context(SCOPE.owner.id, selected, scope)
    result = codec.created(encoded(dataset(org_id=OTHER)), scope, PARAMETERS, SECRET)
    assert result.org_id == OTHER
    # Personal datasets may also report a nonnull personal organization.
    assert codec.created(encoded(dataset(org_id=OTHER)), SCOPE, PARAMETERS, SECRET).org_id == OTHER
    different = encoded(dataset(org_id=None))
    with pytest.raises(YorungeError) as error:
        codec.detail(different, result, scope, PARAMETERS, SECRET)
    assert error.value.code == "invalid_response"


@pytest.mark.parametrize("secret", ["a", "id", "data", "permissions", "synthetic-long-secret"])
@pytest.mark.parametrize("location", ["metadata_key", "metadata_value", "nested_value"])
def test_discarded_metadata_still_scans_selected_literal_secret(secret, location):
    value = dataset()
    if location == "metadata_key":
        if secret in value:
            value["extra"] = {secret: "unused"}
        else:
            value[secret] = "unused"
    elif location == "metadata_value":
        value["unused"] = secret
    else:
        value["unused"] = [{"unused": secret}]
    raw = encoded(value)
    captured = SecretValue(secret)
    with pytest.raises(YorungeError) as error:
        codec.created(raw, SCOPE, PARAMETERS, captured)
    assert error.value.code == "invalid_response"


@pytest.mark.parametrize("secret", ["a", "id", "data", "name", "success"])
def test_short_protocol_key_and_substring_are_not_false_positives(secret):
    result = codec.created(encoded(dataset()), SCOPE, PARAMETERS, SecretValue(secret))
    assert result.name == "sample"
    assert codec.owned_match(encoded([located()]), DATASET, SCOPE, PARAMETERS, SecretValue(secret))


def test_nonselected_owned_metadata_keys_do_not_inherit_selected_schema_exemptions():
    raw = encoded([located(), {"id": OTHER, "name": "unused"}])
    captured = SecretValue("name")
    with pytest.raises(YorungeError) as error:
        codec.owned_match(raw, DATASET, SCOPE, PARAMETERS, captured)
    assert error.value.code == "invalid_response"


@pytest.mark.parametrize("secret", ["sample", "prefix-very-long-secret"])
def test_local_request_body_is_scanned_before_any_intent(secret):
    parameters = PARAMETERS.model_copy(update={"name": secret})
    captured = SecretValue(secret)
    with pytest.raises(YorungeError) as error:
        codec.create_content(SCOPE, parameters, captured)
    assert error.value.code == "invalid_request"


@pytest.mark.parametrize("secret", ["abc123", "eight-byte-secret"])
def test_dynamic_segment_is_scanned_before_fixed_url_prefix_hides_short_secret(secret):
    captured = SecretValue(secret)
    with pytest.raises(YorungeError) as error:
        codec.segment(secret, captured)
    assert error.value.code == "invalid_request"
    if len(secret) >= 8:
        value = "prefix-" + secret
        with pytest.raises(YorungeError) as error:
            codec.segment(value, captured)
        assert error.value.code == "invalid_request"


@pytest.mark.parametrize("value", ["", "a/b", "..", "%2f", "a?b", "a#b", "a\n", "ü", "a" * 129])
def test_provider_route_segment_rejects_encoding_and_path_escape(value):
    with pytest.raises(YorungeError) as error:
        codec.segment(value, SECRET)
    assert error.value.code == "invalid_request"


def test_owned_lookup_uses_exact_id_and_bounded_unchanged_segments():
    raw = encoded([{"id": OTHER, "name": "sample"}, located()])
    found = codec.owned_match(raw, DATASET, SCOPE, PARAMETERS, SECRET)
    assert found is not None
    assert codec.detail_path(found, SECRET) == "datasets/sample-user/sample-dataset"
    assert codec.owned_match(encoded([{"id": OTHER}]), DATASET, SCOPE, PARAMETERS, SECRET) is None
    invalid = {**found.model_dump(), "slug": "../wrong"}
    rejected_call = partial(LocatedDataset.model_validate_json, encoded(invalid))
    with pytest.raises(ValidationError):
        rejected_call()


@pytest.mark.parametrize("kind", ["owned", "membership"])
@pytest.mark.parametrize("rows", [[{"id": DATASET}, {"id": DATASET}], [{"id": OTHER}] * 129])
def test_duplicate_or_oversize_list_does_not_select_first_match(kind, rows):
    raw = encoded(rows)
    call = (
        (lambda: codec.owned_match(raw, DATASET, SCOPE, PARAMETERS, SECRET))
        if kind == "owned"
        else (lambda: codec.membership(raw, DATASET, SECRET))
    )
    with pytest.raises(YorungeError) as error:
        call()
    assert error.value.code == "invalid_response"


def test_project_link_ack_and_exact_membership_are_separate_oracles():
    codec.link_ack(b"", SECRET)
    codec.link_ack(b'{"success":true}', SECRET)
    assert codec.membership(encoded([{"id": DATASET}]), DATASET, SECRET)
    assert not codec.membership(encoded([{"id": OTHER}]), DATASET, SECRET)
    raw = b'{"success":false}'
    with pytest.raises(YorungeError) as error:
        codec.link_ack(raw, SECRET)
    assert error.value.code == "invalid_response"


def test_context_rejects_another_reported_user_and_identity_requires_wrapped_uuid():
    selected = codec.project(encoded(project()), SCOPE, SECRET)
    with pytest.raises(YorungeError) as error:
        codec.context(OTHER, selected, SCOPE)
    assert error.value.code == "invalid_response"
    raw = encoded({"id": SCOPE.owner.id})
    with pytest.raises(YorungeError) as error:
        codec.identity(raw, SECRET)
    assert error.value.code == "invalid_response"


@pytest.mark.parametrize("key", ["license", "tags"])
@pytest.mark.parametrize("secret", ["abc123", "long-selected-secret"])
def test_non_name_local_body_fields_receive_the_same_literal_guard(key, secret):
    value = secret if key == "license" else (secret,)
    parameters = PARAMETERS.model_copy(update={key: value})
    captured = SecretValue(secret)
    with pytest.raises(YorungeError) as error:
        codec.create_content(SCOPE, parameters, captured)
    assert error.value.code == "invalid_request"


def test_wrapped_lists_and_unrelated_name_match_do_not_change_exact_selection():
    rows = [{"id": OTHER, "name": "sample"}, located()]
    found = codec.owned_match(
        encoded({"success": True, "data": rows}), DATASET, SCOPE, PARAMETERS, SECRET
    )
    assert found is not None
    assert found.id == DATASET
    assert codec.membership(encoded({"success": True, "data": [{"id": DATASET}]}), DATASET, SECRET)


@pytest.mark.parametrize(
    "permissions,expected",
    [
        (["upload", "edit", "unrecognized"], None),
        (["edit"], "remote_access_denied"),
        (["upload", "upload"], "invalid_response"),
        ([True], "invalid_response"),
        (None, "invalid_response"),
        (["upload", "x" * 65], "invalid_response"),
        (["upload", "ü"], "invalid_response"),
    ],
)
def test_my_role_label_is_typed_prerequisite_without_grant(permissions, expected):
    raw = encoded({"role": "owner", "permissions": permissions})
    if expected:
        with pytest.raises(YorungeError) as error:
            codec.role(raw, SECRET)
        assert error.value.code == expected
    else:
        observed = codec.role(raw, SECRET)
        assert "upload" in observed.permissions
        assert "grant" not in observed.model_dump()


@pytest.mark.parametrize(
    "raw",
    [
        b'{"success":true,"success":true,"data":{"id":"x"}}',
        b'{"unused":NaN}',
        b'{"unused":Infinity}',
        b"\xff",
        b"\xef\xbb\xbf{}",
        b"{} trailing",
        b" " * (1024 * 1024) + b"{}",
    ],
)
def test_entire_wire_json_guards_run_before_projection(raw):
    with pytest.raises(YorungeError) as error:
        codec.raw(raw, "dataset", SECRET)
    assert error.value.code == "invalid_response"
