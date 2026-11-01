"""Independent raw/projection oracles for the explicitly unverified Platform slice."""

import json

import pytest
from pydantic import ValidationError

from yorunge.application import platform_projection as projection
from yorunge.domain.credentials import SecretValue
from yorunge.domain.errors import YorungeError
from yorunge.domain.platform_discovery import PlatformContextDiscovery

SECRET = SecretValue("fixture-platform-secret-0918274")


def parse(value, kind="me", secret=SECRET):
    raw = json.dumps(value).encode()
    return projection.safe_raw(raw, kind, secret)


def test_unused_metadata_is_dropped_after_full_tree_checks():
    result = projection.identity(
        parse(
            {
                "success": True,
                "data": {
                    "id": "user-1",
                    "organization_id": None,
                    "personal_org_id": "org-personal",
                    "email": "person@example.test",
                    "role": "admin",
                    "free": {"arbitrary": [1, True]},
                },
            }
        )
    )
    assert result.model_dump() == {
        "me_id": "user-1",
        "organization_id": None,
        "organization_id_state": "reported_null",
        "personal_organization_id": "org-personal",
        "personal_organization_id_state": "reported_id",
    }


@pytest.mark.parametrize("value", [None, False, 0, 1, "true"])
def test_me_requires_strict_true_success(value):
    raw = {"data": {"id": "user-1"}}
    if value is not None:
        raw["success"] = value
    with pytest.raises(YorungeError) as failure:
        projection.identity(raw)
    assert failure.value.code == "invalid_response"


@pytest.mark.parametrize("value", [False, 0, 1, "true"])
@pytest.mark.parametrize("kind", ["organizations", "detail"])
def test_success_is_not_discardable_metadata(value, kind):
    raw = {"items": [], "total": 0} if kind == "organizations" else {"id": "project-1"}
    raw["success"] = value
    with pytest.raises(YorungeError) as failure:
        parse(raw, kind)
    assert failure.value.code == "invalid_response"


@pytest.mark.parametrize("kind", ["me", "organizations", "projects", "detail"])
@pytest.mark.parametrize("location", ["key", "value", "nested"])
def test_unused_metadata_never_bypasses_secret_scan(kind, location):
    raw = {"id": "resource"}
    if location == "key":
        raw["prefix-" + SECRET.reveal()] = "unused"
    elif location == "value":
        raw["unused"] = "prefix-" + SECRET.reveal()
    else:
        raw["unused"] = [{"id": SECRET.reveal()}]
    value = [raw] if kind == "projects" else raw
    with pytest.raises(YorungeError) as failure:
        parse(value, kind)
    assert failure.value.code == "invalid_response"


@pytest.mark.parametrize("secret", ["a", "id", "success", "data"])
def test_short_secret_does_not_reject_protocol_keys_or_unrelated_values(secret):
    result = projection.identity(
        parse({"success": True, "data": {"id": "alpha"}}, secret=SecretValue(secret))
    )
    assert result.me_id == "alpha"
    credential = SecretValue(secret)
    with pytest.raises(YorungeError) as failure:
        parse({"success": True, "data": {"id": secret}}, secret=credential)
    assert failure.value.code == "invalid_response"


@pytest.mark.parametrize("parent,expected", [(None, "reported_null"), ("org-1", "reported_id")])
def test_parent_missing_null_and_id_are_distinct(parent, expected):
    assert projection.project({"id": "p"}).organization_id_state == "not_exposed"
    result = projection.project({"id": "p", "org_id": parent})
    assert result.organization_id == parent
    assert result.organization_id_state == expected


@pytest.mark.parametrize("total", [True, -1, 2**63, 1.0, "1", 0])
def test_invalid_organization_total_is_not_incomplete(total):
    raw = {"items": [{"id": "org-1"}], "total": total}
    parsed = parse(raw, "organizations")
    with pytest.raises(YorungeError) as failure:
        projection.organizations(parsed)
    assert failure.value.code == "invalid_response"


@pytest.mark.parametrize("count", [0, 1, 128])
def test_bounded_lists_preserve_order_and_reported_total(count):
    values = [{"id": f"id-{i}", "org_id": None} for i in range(count)]
    assert [v.id for v in projection.projects(values)] == [v["id"] for v in values]
    result = projection.organizations({"items": values, "total": count + 1})
    assert result.reported_total == count + 1
    assert len(result.items) == count


@pytest.mark.parametrize(
    "values",
    [
        [{"id": "same"}, {"id": "same"}],
        [{"id": f"p-{i}"} for i in range(129)],
        [{"id": "bad/path"}],
        [{"id": 1}],
        [None],
        [{}],
    ],
)
@pytest.mark.parametrize("kind", ["projects", "organizations"])
def test_invalid_lists_never_truncate_or_deduplicate(values, kind):
    if kind == "projects":
        check, payload = projection.projects, values
    else:
        check, payload = projection.organizations, {"items": values, "total": len(values)}
    with pytest.raises(YorungeError) as failure:
        check(payload)
    assert failure.value.code == "invalid_response"


@pytest.mark.parametrize("raw", [{"id": "p"}, {"success": True, "data": {"id": "p"}}])
def test_detail_accepts_only_matching_route_id(raw):
    parsed = parse(raw, "detail")
    assert projection.detail(parsed, "p").id == "p"
    with pytest.raises(YorungeError) as failure:
        projection.detail(parsed, "other")
    assert failure.value.code == "invalid_response"


@pytest.mark.parametrize(
    "raw",
    [
        b'{"success":true,"success":true}',
        b'{"ignored":NaN}',
        b'{"ignored":"\xff"}',
        b'{"ignored":' + b"[" * 40 + b"0" + b"]" * 40 + b"}",
    ],
)
def test_discarded_metadata_still_requires_strict_bounded_json(raw):
    with pytest.raises(YorungeError) as failure:
        projection.safe_raw(raw, "me", SECRET)
    assert failure.value.code == "invalid_response"


def platform_wire():
    t = "2026-11-01T00:00:00.000000Z"
    return {
        "schema_version": 1,
        "service_id": "evren-platform",
        "profile": "work",
        "target": {"service_origin": "https://example.test", "api_base_path": "/api/v1"},
        "binding": {
            "store_id": "c8e385ca-c509-4262-a70f-7f7052093669",
            "identity_epoch": "f2c787a2-58f0-4941-9d8b-f08f66c363dc",
            "clock_generation": 1,
            "credential_id": "54f94ef9-8e28-4b5a-8ef9-a915146b5aee",
            "credential_revision": 1,
        },
        "profile_preference": {
            "account_id": None,
            "project_id": None,
            "service_scope": "not_applicable",
        },
        "selected": {"account_id": None, "project_id": None},
        "provider": {
            "principal_id": None,
            "account_id": None,
            "organization_id": None,
            "project_id": None,
            "identity_status": "unverified",
        },
        "reported_identity": {
            "me_id": "user-1",
            "organization_id": None,
            "organization_id_state": "not_exposed",
            "personal_organization_id": None,
            "personal_organization_id_state": "not_exposed",
        },
        "authorization_scope": None,
        "organizations": {"items": [], "reported_total": 0},
        "projects": {"items": [], "selection": {"state": "not_selected", "project": None}},
        "list_completeness": {"organizations": "unknown", "projects": "unknown"},
        "terms": None,
        "observed_from": t,
        "observed_until": t,
        "validated_at": t,
        "observations": [
            {
                "endpoint_id": e,
                "resource_id": None,
                "started_at": t,
                "completed_at": t,
                "authentication": "unknown",
                "outcome": "observed",
            }
            for e in ("platform_me", "platform_organizations", "platform_projects")
        ],
        "consistency": "not_guaranteed",
        "validation": "unverified",
        "reasons": [
            "account_semantics_unknown",
            "authorization_not_verified",
            "identity_not_verified",
            "list_completeness_unknown",
            "project_selection_required",
            "remote_snapshot_not_guaranteed",
        ],
    }


def test_closed_platform_wire_roundtrip():
    wire = platform_wire()
    model = PlatformContextDiscovery.model_validate_json(json.dumps(wire))
    assert json.loads(model.model_dump_json()) == wire


@pytest.mark.parametrize(
    "origin",
    [
        "http://example.test",
        "https://example.test:444",
        "https://example.test?query=1",
        "HTTPS://EXAMPLE.TEST",
    ],
)
def test_invalid_platform_target_is_a_model_validation_error(origin):
    wire = platform_wire()
    wire["target"]["service_origin"] = origin
    encoded = json.dumps(wire)
    with pytest.raises(ValidationError) as failure:
        PlatformContextDiscovery.model_validate_json(encoded)
    assert failure.value.errors()[0]["loc"] == ()
    assert failure.value.errors()[0]["msg"] == "Value error, canonical target required"


@pytest.mark.parametrize("field", list(platform_wire()))
def test_every_platform_field_including_nulls_is_required(field):
    wire = platform_wire()
    del wire[field]
    encoded = json.dumps(wire)
    with pytest.raises(ValidationError):
        PlatformContextDiscovery.model_validate_json(encoded)


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("validation", "verified"),
        ("consistency", "guaranteed"),
        ("authorization_scope", "read"),
        ("reasons", ["selection_unverified"]),
        ("unknown", None),
    ],
)
def test_platform_dto_cannot_upgrade_observation_or_expand_wire(field, value):
    wire = platform_wire()
    wire[field] = value
    encoded = json.dumps(wire)
    with pytest.raises(ValidationError):
        PlatformContextDiscovery.model_validate_json(encoded)


@pytest.mark.parametrize(
    "raw,secret",
    [
        ({"success": True, "data": {"id": "p"}, "id": "discarded"}, "id"),
        ({"success": True, "data": {"id": "p"}, "org_id": "discarded"}, "org_id"),
        ({"id": "p", "data": {"ignored": "discarded"}}, "data"),
        ({"id": "p", "data": {"id": "discarded"}}, "id"),
    ],
)
def test_detail_shape_never_exempts_discarded_metadata_keys(raw, secret):
    credential = SecretValue(secret)
    with pytest.raises(YorungeError) as failure:
        parse(raw, "detail", credential)
    assert failure.value.code == "invalid_response"


@pytest.mark.parametrize("raw", [{"id": "p"}, {"success": True, "data": {"id": "p"}}])
def test_detail_selected_shape_keeps_consumed_protocol_keys_exempt(raw):
    parsed = parse(raw, "detail", SecretValue("id"))
    assert projection.detail(parsed, "p").id == "p"
