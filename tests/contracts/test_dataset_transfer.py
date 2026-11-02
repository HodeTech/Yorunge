"""Independent literal journal wire and hostile decoder vectors."""

import json
from pathlib import Path

import pytest

from yorunge.adapters.upload_store import request_digest
from yorunge.domain.capabilities import canonical
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_transfer import (
    StageIntent,
    StageReceipt,
    TransferControl,
    TransferLease,
    TransferRecord,
    operation_reservation,
)
from yorunge.domain.dataset_upload import DatasetUploadPlan
from yorunge.domain.errors import MESSAGES, OperationError, YorungeError

FIXTURES = Path(__file__).parents[1] / "fixtures"
GOLDEN = json.loads((FIXTURES / "dataset-transfer-journal-v1.json").read_bytes())


def vectors():
    record, intent = GOLDEN["record"], GOLDEN["intent"]
    return [
        (TransferLease, record["lease"]),
        (TransferRecord, record),
        (StageIntent, intent),
        (
            StageReceipt,
            {
                "schema_version": 1,
                "intent_id": intent["intent_id"],
                "recorded_at": intent["intended_at"],
                "result": "accepted",
                "dataset_id": "00000000-0000-4000-8000-000000000099",
                "object_key": None,
                "sent_bytes": None,
                "sent_sha256": None,
            },
        ),
        (
            TransferControl,
            {
                "schema_version": 1,
                "kind": "recovery",
                "operation_id": record["operation_id"],
                "revision": 3,
                "observed_at": record["updated_at"],
                "identity_epoch": record["observed_identity_epoch"],
                "clock_generation": 1,
                "reason": "request_uncertain",
                "verification_digest": None,
            },
        ),
    ]


@pytest.mark.parametrize("cls,body", vectors())
def test_explicit_canonical_wire_roundtrips(cls, body):
    wire = canonical(body)
    assert cls.model_validate_json(wire).encoded() == wire


@pytest.mark.parametrize("cls,body", vectors())
@pytest.mark.parametrize(
    "damage", ["unknown", "missing", "bool", "float", "duplicate", "utf8", "oversize"]
)
def test_journal_never_weakens_closed_decoding(cls, body, damage):
    body = dict(body)
    key = next(iter(body))
    if damage == "unknown":
        body["untrusted"] = True
    elif damage == "missing":
        body.pop(key)
    elif damage == "bool":
        numeric = next(k for k, v in body.items() if type(v) is int)
        body[numeric] = True
    elif damage == "float":
        numeric = next(k for k, v in body.items() if type(v) is int)
        body[numeric] = float(body[numeric])
    content = canonical(body)
    if damage == "duplicate":
        content = content[:-1] + b',"' + key.encode() + b'":null}'
    elif damage == "utf8":
        content = b"\xff" + content
    elif damage == "oversize":
        content = b" " * cls.max_wire_bytes + content
    with pytest.raises(ValueError):
        cls.model_validate_json(content, strict=False, extra="allow")


def test_literal_request_digest_and_quota_reserve_have_independent_oracles():
    plan = DatasetUploadPlan.model_validate_json(
        canonical(json.loads((FIXTURES / "dataset-upload-approved-v1.json").read_bytes())["plan"])
    )
    manifest = DatasetManifest.model_validate_json(
        (FIXTURES / "dataset-manifest-v1.json").read_bytes()
    )
    assert request_digest(plan, manifest, "create", None, {}) == GOLDEN["intent"]["request_digest"]
    # Explicit arithmetic checks prevent the implementation from proving its own
    # capacity equation. Two controls and terminal evidence have reserved space.
    assert operation_reservation(1) == 36 * 1024 + 5 * 4096 + 512
    assert operation_reservation(128) == 36 * 1024 + 386 * 4096 + 128 * 512


@pytest.mark.parametrize(
    "code", ["upload_plan_not_found", "upload_plan_not_valid", "upload_capacity_exceeded"]
)
def test_upload_errors_preserve_closed_envelope_and_useful_next_step(code):
    error = OperationError(code, GOLDEN["record"]["operation_id"])
    assert error.exit_code == 2 and error.message == MESSAGES[code]
    assert "plan execution" not in error.message
    assert error.envelope()["operation_id"] == GOLDEN["record"]["operation_id"]
    assert YorungeError(code).exit_code == 2
