"""Independent wire oracles for service-scoped, deliberately unverified observations."""

import copy
import json

import pytest
from pydantic import ValidationError

from yorunge.domain.discovery import ContextDiscovery

MOMENT = "2026-10-31T01:00:00.000000Z"
WIRE = {
    "schema_version": 1,
    "service_id": "evren-llm",
    "profile": "work",
    "target": {"service_origin": "https://example.test", "api_base_path": "/v1"},
    "binding": {
        "store_id": "11111111-1111-4111-8111-111111111111",
        "identity_epoch": "22222222-2222-4222-8222-222222222222",
        "clock_generation": 1,
        "credential_id": "33333333-3333-4333-8333-333333333333",
        "credential_revision": 1,
    },
    "profile_preference": {
        "account_id": "platform-account",
        "project_id": "platform-project",
        "service_scope": "unknown",
    },
    "selected": {"account_id": None, "project_id": None},
    "provider": {
        "principal_id": None,
        "account_id": None,
        "organization_id": None,
        "project_id": None,
        "identity_status": "not_exposed",
    },
    "authorization_scope": None,
    "organizations": None,
    "projects": None,
    "list_completeness": "not_exposed",
    "terms": {"accepted": False, "current_version": 2, "is_material": True},
    "observed_from": MOMENT,
    "observed_until": MOMENT,
    "validated_at": MOMENT,
    "observations": [
        {
            "endpoint_id": "llm_terms_status",
            "started_at": MOMENT,
            "completed_at": MOMENT,
            "authentication": "unknown",
        }
    ],
    "consistency": "not_guaranteed",
    "validation": "unverified",
    "reasons": [
        "authorization_not_verified",
        "identity_not_exposed",
        "profile_scope_unknown",
        "remote_snapshot_not_guaranteed",
        "terms_not_accepted",
    ],
}


def test_independent_exact_wire_roundtrip_and_no_service_scope_elevation():
    view = ContextDiscovery.model_validate_json(json.dumps(WIRE))
    assert view.model_dump(mode="json") == WIRE
    assert view.selected.account_id is None
    assert view.selected.project_id is None
    assert view.authorization_scope is None
    assert view.observations[0].authentication == "unknown"
    assert "doc_path" not in view.model_dump_json()


@pytest.mark.parametrize("field", list(WIRE))
def test_all_public_fields_are_required(field):
    value = copy.deepcopy(WIRE)
    del value[field]
    with pytest.raises(ValidationError):
        ContextDiscovery.model_validate_json(json.dumps(value))


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("schema_version",), True),
        (("schema_version",), 1.0),
        (("service_id",), "evren-platform"),
        (("binding", "clock_generation"), True),
        (("binding", "clock_generation"), 0),
        (("binding", "clock_generation"), 2**63),
        (("binding", "credential_revision"), 1.0),
        (("binding", "credential_id"), "not-a-uuid"),
        (("profile_preference", "service_scope"), "not_applicable"),
        (("selected", "account_id"), "platform-account"),
        (("provider", "principal_id"), "fabricated-account"),
        (("authorization_scope",), {}),
        (("projects",), []),
        (("validation",), "verified"),
        (("consistency",), "atomic"),
        (("terms", "accepted"), 1),
        (("terms", "current_version"), True),
        (("terms", "current_version"), -1),
        (("terms", "current_version"), 2**63),
        (("terms", "doc_path"), "private/terms"),
        (("observations",), []),
        (("observations",), WIRE["observations"] * 2),
        (("observations",), WIRE["observations"][0]),
        (("observed_from",), "2026-10-31T02:00:00.000000Z"),
        (("validated_at",), "2026-10-31T00:00:00.000000Z"),
        (("validated_at",), "2026-10-31T01:00:00+00:00"),
        (("reasons",), WIRE["reasons"][:-1]),
        (("reasons",), WIRE["reasons"][::-1]),
        (("reasons",), WIRE["reasons"] + WIRE["reasons"][:1]),
        (("unknown",), "field"),
    ],
)
def test_closed_wire_rejects_false_claims_wrong_types_and_cross_service_preferences(
    path, replacement
):
    value = copy.deepcopy(WIRE)
    parent = value
    for field in path[:-1]:
        parent = parent[field]
    parent[path[-1]] = replacement
    with pytest.raises(ValidationError):
        ContextDiscovery.model_validate_json(json.dumps(value))
