import copy
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from yorunge.application.capabilities import combine
from yorunge.domain.capabilities import (
    AuthorizationScope,
    CapabilityKey,
    CapabilityRecord,
    CapabilityScopeV2,
    Evidence,
    canonical,
    instant,
    timestamp,
)


def scope_data():
    return {
        "schema_version": 2,
        "store_id": str(uuid4()),
        "identity_epoch": str(uuid4()),
        "clock_generation": 1,
        "service_id": "local",
        "service_origin": None,
        "api_base_path": None,
        "account_id": None,
        "project_id": None,
        "credential_id": None,
        "credential_revision": None,
        "authorization_scope": None,
        "model": None,
        "tool": None,
        "execution": {
            "backend": "local",
            "runtime_id": None,
            "runtime_revision": None,
            "environment_digest": None,
        },
    }


def parse(data):
    return CapabilityScopeV2.model_validate_json(json.dumps(data))


def evidence(now, support="supported", producer="fixture", *, constraints=(), ttl=300):
    return Evidence(
        kind="local_policy",
        producer_id=producer,
        producer_version="1",
        provenance="fixture-only",
        support=support,
        reason_code="fixture_policy",
        checked_at=timestamp(now),
        expires_at=timestamp(now + timedelta(seconds=ttl)),
        constraints=constraints,
    )


@pytest.mark.parametrize("field", list(scope_data()))
def test_scope_wire_requires_every_field_even_nullable(field):
    value = scope_data()
    del value[field]
    with pytest.raises(ValidationError):
        parse(value)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("schema_version", True),
        ("schema_version", 2.0),
        ("schema_version", "2"),
        ("clock_generation", True),
        ("clock_generation", 0),
        ("clock_generation", 2**63),
        ("store_id", "not-an-id"),
        ("store_id", str(uuid4()).upper()),
        ("account_id", ""),
        ("project_id", "space forbidden"),
        ("unexpected", None),
        ("service_origin", "https://example.test"),
        ("api_base_path", "/v1"),
        ("credential_id", str(uuid4())),
        ("authorization_scope", {"permissions": [], "resources": []}),
        ("execution", {"backend": "local"}),
        (
            "execution",
            {
                "backend": "local",
                "runtime_id": "a",
                "runtime_revision": None,
                "environment_digest": None,
            },
        ),
    ],
)
def test_scope_rejects_type_pair_and_local_authority_claims(field, bad):
    value = scope_data()
    value[field] = bad
    with pytest.raises(ValidationError):
        parse(value)


def test_two_independent_producers_match_canonical_key_and_unicode_is_not_normalized():
    data = scope_data()
    data["model"] = {
        "source": "huggingface",
        "id": "org/\u00e9",
        "revision": "main",
        "content_digest": None,
    }
    other = dict(reversed(list(copy.deepcopy(data).items())))
    first = CapabilityKey(capability_id="planning.offline", task="llm.train", scope=parse(data))
    second = CapabilityKey(capability_id="planning.offline", task="llm.train", scope=parse(other))
    assert first.encoded() == second.encoded()
    assert first.digest() == second.digest()
    other["model"]["id"] = "org/e\u0301"
    third = CapabilityKey(capability_id="planning.offline", task="llm.train", scope=parse(other))
    assert third.digest() != first.digest()


@pytest.mark.parametrize("permissions", [["z", "a"], ["a", "a"], ["*"], ["a\n"], ["a" * 129]])
def test_permission_wire_is_ordered_unique_bounded_and_not_wildcard(permissions):
    with pytest.raises(ValidationError):
        AuthorizationScope.model_validate_json(
            json.dumps({"permissions": permissions, "resources": []})
        )


def test_total_resource_limit_and_nested_extra_keys_are_enforced():
    resource = {
        "namespace": "service",
        "resource_type": "project",
        "resource_id": "p",
        "permissions": ["read"],
    }
    values = [
        {"permissions": ["read"], "resources": [dict(resource, extra="no")]},
        {"permissions": [], "resources": [resource, resource]},
        {"permissions": ["a" + str(i).zfill(3) for i in range(128)], "resources": [resource]},
    ]
    for value in values:
        with pytest.raises(ValidationError):
            AuthorizationScope.model_validate_json(json.dumps(value))


@pytest.mark.parametrize(
    "bad",
    ["2026-10-27T00:00:00Z", "2026-10-27T00:00:00.000000+00:00", "2026-02-30T00:00:00.000000Z"],
)
def test_canonical_utc_rejects_ambiguous_or_invalid_representation(bad):
    with pytest.raises(ValueError):
        instant(bad)


def test_conflict_proofs_outlive_aggregate_ttl_and_other_producer_refresh():
    now = datetime(2026, 10, 27, tzinfo=UTC)
    key = CapabilityKey(capability_id="fixture.policy", task="llm.train", scope=parse(scope_data()))
    first = combine(key, None, (evidence(now, "unsupported", "first"),), now, replace_own=True)
    second = combine(key, first, (evidence(now, "supported", "second"),), now, replace_own=False)
    assert second.support == "unknown"
    assert instant(second.expires_at) == now + timedelta(seconds=30)
    assert instant(second.pinned_until()) == now + timedelta(seconds=300)
    later = now + timedelta(seconds=31)
    third = combine(key, second, (evidence(later, "supported", "second"),), later, replace_own=True)
    assert third.support == "unknown"
    assert {e.producer_id for e in third.evidence} == {"first", "second"}


def test_overflow_blocker_survives_own_snapshot_and_unknown_expiry():
    now = datetime(2026, 10, 27, tzinfo=UTC)
    key = CapabilityKey(capability_id="fixture.policy", task="llm.train", scope=parse(scope_data()))
    proofs = tuple(evidence(now, producer="p" + str(i)) for i in range(9))
    record = combine(key, None, proofs, now, replace_own=False)
    assert record.support == "unknown"
    assert record.reason_code == "evidence_overflow"
    assert record.evidence == ()
    later = now + timedelta(seconds=31)
    updated = combine(key, record, (evidence(later),), later, replace_own=True)
    assert updated.support == "unknown"
    assert updated.conflict_until == timestamp(now + timedelta(seconds=300))
    assert len(canonical(updated.model_dump(mode="json"))) <= 32768


@pytest.mark.parametrize("kind", ["documentation", "synthetic_test", "not_verified"])
def test_record_cannot_promote_unverified_evidence_to_supported(kind):
    now = datetime(2026, 10, 27, tzinfo=UTC)
    key = CapabilityKey(capability_id="fixture.policy", task="llm.train", scope=parse(scope_data()))
    proof = evidence(now).model_copy(update={"kind": kind})
    with pytest.raises(ValidationError):
        CapabilityRecord(
            key=key,
            support="supported",
            reason_code="fixture_policy",
            message="Fixture policy",
            evidence=(proof,),
            checked_at=proof.checked_at,
            expires_at=proof.expires_at,
        )


@pytest.mark.parametrize("nested", [False, True])
def test_scope_wire_rejects_duplicate_json_keys_at_every_level(nested):
    encoded = json.dumps(scope_data())
    duplicate = (
        encoded.replace('"backend": "local"', '"backend": "local", "backend": "local"')
        if nested
        else '{"schema_version": 2,' + encoded[1:]
    )
    with pytest.raises(ValueError, match="duplicate wire key"):
        CapabilityScopeV2.model_validate_json(duplicate)


@pytest.mark.parametrize("encoding", ["utf-16", "utf-32"])
def test_scope_wire_rejects_non_utf8_json_bytes(encoding):
    payload = json.dumps(scope_data()).encode(encoding)
    with pytest.raises(ValueError):
        CapabilityScopeV2.model_validate_json(payload)
