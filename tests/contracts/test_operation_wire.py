"""Scalar history fast path retains independent strict-wire rejection cases."""

import hashlib
import json

import pytest

from yorunge.domain.capabilities import canonical
from yorunge.domain.maintenance import MaintenancePreview
from yorunge.domain.operations import OperationEvent

EVENT = dict(
    sequence=1,
    revision=1,
    fence=1,
    attempt_id="12345678-1234-4234-9234-123456789abc",
    observed_at="2026-10-29T12:34:56.123456Z",
    identity_epoch="87654321-4321-4321-8321-cba987654321",
    clock_generation=1,
    status="admitted",
    execution_status="not_started",
    delivery_status="pending",
    reason_code=None,
)


@pytest.mark.parametrize(
    "field,value",
    [
        ("attempt_id", "12345678-1234-1234-9234-123456789abc"),
        ("identity_epoch", "87654321-4321-4321-c321-cba987654321"),
        ("attempt_id", "12345678-1234-4234-9234-123456789ABC"),
        ("attempt_id", "12345678-1234-4234-9234-123456789abc\n"),
        ("attempt_id", [EVENT["attempt_id"]]),
        ("identity_epoch", 1),
        ("observed_at", "2026-10-29T12:34:56.123456+00:00"),
        ("observed_at", "2026-02-30T12:34:56.123456Z"),
        ("observed_at", "2026-10-29T12:34:56.123456Z\n"),
        ("observed_at", "２０２６-10-29T12:34:56.123456Z"),
        ("sequence", True),
        ("sequence", 1.0),
        ("revision", "1"),
        ("clock_generation", 0),
        ("fence", 2**63),
        ("status", "admitted\u202e"),
        ("execution_status", "not_started\x00"),
        ("delivery_status", "pending\n"),
        ("reason_code", "provider_failed\ud800"),
    ],
)
def test_scalar_event_path_rejects_noncanonical_types_and_text(field, value):
    payload = {**EVENT, field: value}
    encoded = json.dumps(payload)
    with pytest.raises(ValueError):
        OperationEvent.model_validate_json(encoded)


@pytest.mark.parametrize(
    "payload",
    [
        '{"sequence":1,' + json.dumps(EVENT)[1:],
        json.dumps({**EVENT, "extra": "value"}),
        json.dumps({**EVENT, "schema_version": 1}),
        json.dumps(EVENT).replace('"revision": 1', '"revision": NaN'),
        b"\xff",
    ],
)
def test_scalar_event_rejects_duplicate_extra_nonfinite_and_bad_utf8(payload):
    with pytest.raises(ValueError):
        OperationEvent.model_validate_json(payload)


def test_scalar_event_accepts_semantically_identical_json_and_round_trips():
    event = OperationEvent.model_validate(EVENT)
    raw = json.dumps(dict(reversed(tuple(EVENT.items()))), indent=2).encode()
    assert OperationEvent.model_validate_json(raw) == event
    assert OperationEvent.model_validate_json(canonical(event.model_dump(mode="json"))) == event


def preview_payload():
    fingerprint = hashlib.sha256(b"").hexdigest()
    current = dict(
        store_id=EVENT["attempt_id"],
        identity_epoch=EVENT["identity_epoch"],
        store_schema_version=6,
        binding_count=0,
        binding_fingerprint=fingerprint,
        plan_count=0,
        plan_fingerprint=fingerprint,
        approval_count=0,
        approval_fingerprint=fingerprint,
        operation_count=0,
        attempt_count=0,
        nonterminal_operation_count=0,
        unknown_operation_count=0,
        operation_fingerprint=fingerprint,
    )
    raw = dict(
        schema_version=3,
        cache_invalidated=True,
        action="reset",
        current=current,
        source=None,
        history_may_be_lost=False,
        announced_epoch=None,
    )
    raw["digest"] = hashlib.sha256(canonical(raw)).hexdigest()
    return raw


@pytest.mark.parametrize(
    "field,value",
    [
        ("operation_count", True),
        ("attempt_count", -1),
        ("unknown_operation_count", 1),
        ("binding_count", 2**63),
        ("plan_count", 1.0),
        ("operation_fingerprint", "X" * 64),
        ("identity_epoch", "not-a-uuid"),
    ],
)
def test_preview_v3_strict_snapshot_and_count_relationships(field, value):
    raw = preview_payload()
    raw["current"][field] = value
    raw["digest"] = hashlib.sha256(
        canonical({k: v for k, v in raw.items() if k != "digest"})
    ).hexdigest()
    encoded = canonical(raw)
    with pytest.raises(ValueError):
        MaintenancePreview.model_validate_json(encoded)


def test_preview_digest_is_canonical_and_literal_boolean_is_strict():
    raw = preview_payload()
    assert MaintenancePreview.model_validate_json(canonical(raw)).schema_version == 3
    for field, value in (("cache_invalidated", 1), ("digest", "0" * 64), ("schema_version", 3.0)):
        encoded = canonical({**raw, field: value})
        with pytest.raises(ValueError):
            MaintenancePreview.model_validate_json(encoded)
