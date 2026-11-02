"""Literal v2 history and exact accepted workflow graphs, including missing-stage attacks."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from yorunge.adapters.upload_store import (
    VersionedTransferView,
    decode_versioned,
    validate_graph,
)
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_transfer import (
    StageIntent,
    StageReceipt,
    TransferControl,
    TransferRecord,
    TransferVerification,
)
from yorunge.domain.dataset_transfer_v2 import (
    TransferControlV2,
    TransferRecordV2,
    TransferVerificationV2,
)
from yorunge.domain.dataset_upload import DatasetUploadApproval, DatasetUploadPlan
from yorunge.domain.dataset_upload_v2 import DatasetUploadApprovalV2, DatasetUploadPlanV2
from yorunge.domain.errors import YorungeError

FIXTURES = Path(__file__).parents[1] / "fixtures"
GOLDEN = FIXTURES / "dataset-transfer-graph-v2.json"


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def graph(data=None):
    data = json.loads(GOLDEN.read_bytes()) if data is None else data
    return VersionedTransferView(
        DatasetUploadPlanV2.model_validate_json(encode(data["plan"])),
        DatasetUploadApprovalV2.model_validate_json(encode(data["approval"])),
        TransferRecordV2.model_validate_json(encode(data["record"])),
        tuple(StageIntent.model_validate_json(encode(x)) for x in data["intents"]),
        tuple(StageReceipt.model_validate_json(encode(x)) for x in data["receipts"]),
        tuple(TransferControlV2.model_validate_json(encode(x)) for x in data["controls"]),
        TransferVerificationV2.model_validate_json(encode(data["verification"])),
    )


def manifest():
    return DatasetManifest.model_validate_json((FIXTURES / "dataset-manifest-v1.json").read_bytes())


def test_literal_v2_graph_proof_digest_and_canonical_family_bytes():
    data = json.loads(GOLDEN.read_bytes())
    value = graph(data)
    validate_graph(value, manifest())
    pairs = [
        (value.plan, "plan"),
        (value.approval, "approval"),
        (value.operation, "record"),
        (value.verification, "verification"),
    ]
    for model, field in pairs:
        assert model.encoded() == encode(data[field])
    assert (
        hashlib.sha256(value.verification.encoded()).hexdigest()
        == "cb5d7b1a55712f5b0e2afdd897a76daf39a13bcbd5dcb2648cfb6834fd05b2bb"
    )
    assert len(value.intents) == len(value.receipts) == 11
    assert value.operation.reason == "metadata_verified"
    assert value.verification.grant is None
    assert len(value.verification.encoded()) <= 16 * 1024 + 512 * 3


@pytest.mark.parametrize("index", range(11))
def test_each_required_intent_cannot_be_replaced_by_metadata_even_if_rest_accepted(index):
    value = graph()
    removed = value.intents[index]
    # Resequence and reseal nothing else: every remaining receipt is still accepted.
    intents = tuple(
        x.model_copy(update={"sequence": i + 1})
        for i, x in enumerate(x for x in value.intents if x.intent_id != removed.intent_id)
    )
    receipts = tuple(x for x in value.receipts if x.intent_id != removed.intent_id)
    incomplete = replace(value, intents=intents, receipts=receipts)
    assert all(x.result == "accepted" for x in incomplete.receipts)
    assert incomplete.verification.files == value.verification.files
    source = manifest()
    with pytest.raises(YorungeError) as error:
        validate_graph(incomplete, source)
    assert error.value.code == "state_invalid"


def test_unknown_partial_graph_remains_valid_history_without_fake_success():
    value = graph()
    record = value.operation.model_copy(update={"status": "unknown", "reason": "request_uncertain"})
    recovery = value.controls[0].model_copy(
        update={"kind": "recovery", "reason": "request_uncertain", "verification_digest": None}
    )
    partial = replace(
        value,
        operation=record,
        intents=value.intents[:-1],
        receipts=value.receipts[:-1],
        controls=(recovery,),
        verification=None,
    )
    validate_graph(partial, manifest())
    assert partial.operation.status == "unknown"


@pytest.mark.parametrize("field", ["approval", "controls", "verification"])
def test_mixed_record_control_approval_proof_family_is_rejected(field):
    value = graph()
    if field == "approval":
        data = json.loads((FIXTURES / "dataset-upload-approved-v1.json").read_bytes())["approval"]
        changed = DatasetUploadApproval.model_validate_json(encode(data))
    elif field == "controls":
        data = value.controls[0].model_dump(mode="json")
        data.update(schema_version=1, reason="verified")
        changed = (TransferControl.model_validate_json(encode(data)),)
    else:
        data = value.verification.model_dump(mode="json")
        data.update(schema_version=1)
        data.pop("scope")
        data.pop("authorization_policy")
        legacy = json.loads((FIXTURES / "dataset-upload-approved-v1.json").read_bytes())["plan"][
            "grant"
        ]
        data["grant"] = legacy
        changed = TransferVerification.model_validate_json(encode(data))
    candidate, source = replace(value, **{field: changed}), manifest()
    with pytest.raises(YorungeError) as error:
        validate_graph(candidate, source)
    assert error.value.code == "state_invalid"


@pytest.mark.parametrize(
    "field,value",
    [
        ("verification_digest", "b" * 64),
        ("identity_epoch", "00000000-0000-4000-8000-000000000099"),
        ("clock_generation", 2),
        ("revision", 23),
    ],
)
def test_terminal_evidence_matches_record_and_canonical_proof(field, value):
    view = graph()
    data = view.controls[0].model_dump(mode="json")
    data[field] = value
    control = TransferControlV2.model_validate_json(encode(data))
    candidate, source = replace(view, controls=(control,)), manifest()
    with pytest.raises(YorungeError):
        validate_graph(candidate, source)


@pytest.mark.parametrize(
    "kind,reason,digest",
    [
        ("recovery", "metadata_verified", "a" * 64),
        ("terminal", "read_unavailable", None),
        ("terminal", "provider_rejected", "a" * 64),
        ("terminal", "metadata_verified", None),
        ("recovery", "verified", None),
    ],
)
def test_closed_control_kind_reason_digest_matrix(kind, reason, digest):
    data = json.loads(GOLDEN.read_bytes())["controls"][0]
    data.update(kind=kind, reason=reason, verification_digest=digest)
    raw = encode(data)
    with pytest.raises(ValueError):
        TransferControlV2.model_validate_json(raw)


@pytest.mark.parametrize(
    "reason,status",
    [("metadata_verified", "unknown"), ("read_unavailable", "failed"), ("verified", "succeeded")],
)
def test_record_reason_cannot_upgrade_or_downgrade_the_result(reason, status):
    data = json.loads(GOLDEN.read_bytes())["record"]
    data.update(reason=reason, status=status)
    raw = encode(data)
    with pytest.raises(ValueError):
        TransferRecordV2.model_validate_json(raw)


@pytest.mark.parametrize(
    "v1,v2,field",
    [
        (DatasetUploadPlan, DatasetUploadPlanV2, "plan"),
        (DatasetUploadApproval, DatasetUploadApprovalV2, "approval"),
        (TransferRecord, TransferRecordV2, "record"),
        (TransferControl, TransferControlV2, "control"),
        (TransferVerification, TransferVerificationV2, "verification"),
    ],
)
def test_closed_decoder_no_mixed_version_or_old_binary_downgrade(v1, v2, field):
    data = json.loads(GOLDEN.read_bytes())
    data = data["controls"][0] if field == "control" else data[field]
    raw = encode(data)
    assert type(decode_versioned(v1, v2, raw.decode())) is v2
    with pytest.raises(ValueError):
        v1.model_validate_json(raw)
    for version in (True, 1, 3, None):
        bad = encode({**data, "schema_version": version}).decode()
        with pytest.raises(YorungeError) as error:
            decode_versioned(v1, v2, bad)
        assert error.value.code == "state_invalid"


def test_historical_success_does_not_expire_during_full_graph_validation():
    value = graph()
    # No wall clock is accepted by this pure validation path. Write-time freshness is k.
    validate_graph(value, manifest())
    assert value.verification.observed_at == "2026-11-02T11:00:14.000000Z"


def test_duplicate_and_oversized_otherwise_valid_versioned_record():
    data = json.loads(GOLDEN.read_bytes())["record"]
    raw = encode(data)
    variants = [raw[:-1] + b',"schema_version":2}', b" " * (16 * 1024) + raw]
    for content in variants:
        assert json.loads(content) == data
        text = content.decode()
        with pytest.raises(YorungeError) as error:
            decode_versioned(TransferRecord, TransferRecordV2, text)
        assert error.value.code == "state_invalid"


def test_maximum_128_file_proof_fits_real_reserved_bytes_and_rejects_129():
    data = json.loads(GOLDEN.read_bytes())["verification"]
    base = data["files"][0]
    data["files"] = [
        {
            **base,
            "file_index": i,
            "item_id": f"00000000-0000-4000-8000-{1000 + i:012d}",
            "size_bytes": 500_000_000,
        }
        for i in range(128)
    ]
    largest = TransferVerificationV2.model_validate_json(encode(data))
    assert len(largest.encoded()) <= 16 * 1024 + 512 * 128 <= largest.max_wire_bytes
    data["files"].append(
        {**base, "file_index": 128, "item_id": "00000000-0000-4000-8000-000000001128"}
    )
    raw = encode(data)
    with pytest.raises(ValueError):
        TransferVerificationV2.model_validate_json(raw)
