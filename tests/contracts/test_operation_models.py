"""Independent closed lifecycle oracle, not provider success inference."""

import json
from itertools import product
from uuid import uuid4

import pytest
from pydantic import ValidationError

from yorunge.domain.errors import OperationError
from yorunge.domain.operations import AdmissionAuthority, operation_status, validate_progress_reason

PAIRS = {
    ("not_started", "pending"): "admitted",
    ("not_started", "not_required"): "admitted",
    ("submitted", "pending"): "submitted",
    ("submitted", "not_required"): "submitted",
    ("running", "pending"): "running",
    ("running", "not_required"): "running",
    ("unknown", "pending"): "unknown",
    ("unknown", "unknown"): "unknown",
    ("unknown", "not_required"): "unknown",
    ("succeeded", "pending"): "running",
    ("succeeded", "unknown"): "unknown",
    ("succeeded", "failed"): "failed",
    ("succeeded", "complete"): "succeeded",
    ("succeeded", "not_required"): "succeeded",
    ("failed", "pending"): "failed",
    ("failed", "not_required"): "failed",
    ("cancelled", "pending"): "cancelled",
    ("cancelled", "not_required"): "cancelled",
}


@pytest.mark.parametrize(
    "execution,delivery",
    list(
        product(
            ["not_started", "submitted", "running", "unknown", "succeeded", "failed", "cancelled"],
            ["pending", "not_required", "unknown", "failed", "complete"],
        )
    ),
)
def test_exhaustive_execution_delivery_oracle(execution, delivery):
    if (execution, delivery) in PAIRS:
        assert (
            operation_status(execution, delivery, delivery_required=delivery != "not_required")
            == PAIRS[execution, delivery]
        )
    else:
        with pytest.raises(ValueError):
            operation_status(execution, delivery, delivery_required=delivery != "not_required")


def test_delivery_requirement_and_local_terminal_are_not_provider_override_flags():
    with pytest.raises(ValueError):
        operation_status("succeeded", "not_required", delivery_required=True)
    with pytest.raises(ValueError):
        operation_status("succeeded", "complete", delivery_required=False)
    with pytest.raises(ValueError):
        operation_status("submitted", "pending", delivery_required=True, local_terminal="failed")
    assert (
        operation_status(
            "not_started", "pending", delivery_required=True, local_terminal="cancelled"
        )
        == "cancelled"
    )


@pytest.mark.parametrize(
    "code,exit_code,capacity",
    [
        ("operation_not_found", 2, None),
        ("operation_conflict", 2, None),
        ("operation_lease_lost", 2, None),
        ("operation_fence_exhausted", 2, None),
        ("operation_capacity_exceeded", 2, "transition"),
        ("operation_uncertain", 5, None),
        ("plan_in_use", 2, None),
    ],
)
def test_coordination_error_envelope_is_closed_and_preserves_identity(code, exit_code, capacity):
    identifier = str(uuid4())
    failure = OperationError(
        code, identifier, reason_code="state_write_failed", capacity_kind=capacity
    )
    assert failure.exit_code == exit_code
    envelope = failure.envelope()
    assert envelope["operation_id"] == identifier
    assert envelope["retryable"] is False
    assert envelope["details"] == {"reason_code": "state_write_failed", "capacity_kind": capacity}
    assert set(envelope) == {
        "schema_version",
        "code",
        "message",
        "operation_id",
        "retryable",
        "details",
    }


def test_admission_allowlist_preserves_local_context_but_rejects_secret_fields():
    authority = {
        "service_id": "local",
        "service_origin": None,
        "api_base_path": None,
        "account_id": "account",
        "project_id": "project",
        "credential_id": None,
        "credential_revision": None,
        "authorization_scope": None,
    }
    assert AdmissionAuthority.model_validate_json(json.dumps(authority)).account_id == "account"
    for field in ("tag", "key_check", "reference_name", "secret", "K", "profile"):
        body = dict(authority, **{field: "SYNTHETIC_PRIVATE_MARKER"})
        with pytest.raises(ValidationError):
            AdmissionAuthority.model_validate_json(json.dumps(body))
    with pytest.raises(ValueError):
        AdmissionAuthority.model_validate_json(
            json.dumps(authority)[:-1] + ',"service_id":"local"}'
        )


@pytest.mark.parametrize(
    "status,reason,execution,delivery,dispatched",
    [
        ("failed", "approval_revoked", "failed", "not_required", True),
        ("cancelled", "identity_reset", "cancelled", "not_required", True),
        ("cancelled", "provider_cancelled", "not_started", "not_required", False),
        ("running", None, "succeeded", "pending", True),
        ("running", "delivery_pending", "running", "pending", True),
    ],
)
def test_reason_requires_dispatch_and_delivery_evidence(
    status, reason, execution, delivery, dispatched
):
    with pytest.raises(ValueError):
        validate_progress_reason(status, reason, execution, delivery, dispatched=dispatched)
    validate_progress_reason("running", "delivery_pending", "succeeded", "pending", dispatched=True)
