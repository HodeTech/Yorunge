"""Independent receipt wire, bounded raw projection, and structural history gates."""

import hashlib
import json
from dataclasses import replace
from functools import partial
from pathlib import Path

import pytest

from tests.contracts.test_upload_versions import graph, manifest
from yorunge.adapters.upload_store import (
    VersionedTransferView,
    decode,
    decode_versioned,
    require_legacy_view,
    validate_graph,
)
from yorunge.application import platform_upload_codec as codec
from yorunge.domain.capabilities import canonical
from yorunge.domain.create_receipt import CreateReceiptV2
from yorunge.domain.credentials import SecretValue
from yorunge.domain.dataset_transfer import StageReceipt
from yorunge.domain.dataset_upload import DatasetUploadPlan, UploadOwner
from yorunge.domain.errors import YorungeError
from yorunge.domain.platform_upload import ProviderDataset
from yorunge.domain.upload_versions import validate_create_receipt

FIXTURES = Path(__file__).parents[1] / "fixtures"
GOLDEN = (FIXTURES / "dataset-create-receipt-v2.json").read_bytes()
OTHER = "00000000-0000-4000-8000-000000000098"
SECRET = SecretValue("private-create-receipt-canary")


def receipt(**changes):
    body = json.loads(GOLDEN)
    body.update(changes)
    return CreateReceiptV2.model_validate_json(canonical(body))


def test_literal_receipt_separate_closed_model_and_canonical_union():
    value = receipt()
    assert value.encoded() == GOLDEN
    assert not isinstance(value, StageReceipt)
    assert value.created_dataset.name not in repr(value)
    assert value.created_dataset.owner_id not in repr(value)
    assert value.created_dataset.id == value.dataset_id
    assert decode_versioned(StageReceipt, CreateReceiptV2, GOLDEN.decode()) == value
    assert len(value.encoded()) == 459
    # The canonical original fixture byte sequence is not rewritten.
    legacy = graph().receipts[0]
    assert decode_versioned(StageReceipt, CreateReceiptV2, legacy.encoded().decode()) == legacy
    rejected_call = partial(decode, StageReceipt, GOLDEN.decode())
    with pytest.raises(YorungeError) as raised:
        rejected_call()
    assert raised.value.code == "state_invalid"


@pytest.mark.parametrize("version", [None, True, False, 1.0, "2", 0, 3])
def test_union_closed_schema_version(version):
    body = json.loads(GOLDEN)
    body["schema_version"] = version
    payload = canonical(body).decode()
    with pytest.raises(YorungeError) as raised:
        decode_versioned(StageReceipt, CreateReceiptV2, payload)
    assert raised.value.code == "state_invalid"


@pytest.mark.parametrize(
    "field,value",
    [
        ("result", "rejected"),
        ("dataset_id", OTHER),
        ("dataset_id", None),
        ("object_key", "objects/one"),
        ("sent_bytes", 0),
        ("sent_sha256", "f" * 64),
        ("recorded_at", "yesterday"),
        ("intent_id", "not-a-uuid"),
        ("unknown", True),
    ],
)
def test_receipt_invalid_fields_and_identity(field, value):
    with pytest.raises(ValueError):
        receipt(**{field: value})


@pytest.mark.parametrize(
    "field",
    [
        "schema_version",
        "intent_id",
        "recorded_at",
        "result",
        "dataset_id",
        "object_key",
        "sent_bytes",
        "sent_sha256",
        "created_dataset",
    ],
)
def test_no_implicit_defaults_for_nullable_or_required_fields(field):
    body = json.loads(GOLDEN)
    del body[field]
    rejected_call = partial(CreateReceiptV2.model_validate_json, canonical(body))
    with pytest.raises(ValueError):
        rejected_call()


@pytest.mark.parametrize(
    "owner_kind,org",
    [
        ("user", None),
        ("user", OTHER),
        ("organization", OTHER),
    ],
)
def test_selected_owner_by_kind_preserves_other_owner(owner_kind, org):
    view = graph()
    owner_id = view.plan.scope.owner.id
    plan = view.plan.model_copy(
        update={
            "scope": view.plan.scope.model_copy(
                update={
                    "owner": UploadOwner(
                        kind=owner_kind, id=owner_id if owner_kind == "user" else org
                    )
                }
            )
        }
    )
    body = receipt().created_dataset.model_dump(mode="json")
    body["org_id"] = org
    value = receipt(created_dataset=body)
    validate_create_receipt(plan, view.intents[0], value)
    assert value.created_dataset.owner_id == owner_id and value.created_dataset.org_id == org


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "different"),
        ("modality", "AUDIO"),
        ("owner_id", OTHER),
    ],
)
def test_structural_plan_and_selected_owner_binding(field, value):
    view = graph()
    body = receipt().created_dataset.model_dump(mode="json")
    body[field] = value
    changed = receipt(created_dataset=body)
    with pytest.raises(ValueError):
        validate_create_receipt(view.plan, view.intents[0], changed)
    candidate = replace(view, receipts=(changed, *view.receipts[1:]))
    rejected_call = partial(validate_graph, candidate, manifest())
    with pytest.raises(YorungeError) as raised:
        rejected_call()
    assert raised.value.code == "state_invalid"


def test_nonselected_owner_is_not_inferred_or_stripped():
    view = graph()
    body = receipt().created_dataset.model_dump(mode="json")
    body["org_id"] = OTHER
    value = receipt(created_dataset=body)
    validate_create_receipt(view.plan, view.intents[0], value)
    assert value.created_dataset.org_id == OTHER


def test_wrong_intent_kind_and_legacy_family_rejected():
    view = graph()
    legacy_plan = DatasetUploadPlan.model_validate_json(
        (FIXTURES / "dataset-upload-plan-v1.json").read_bytes()
    )
    for plan, intent in [(view.plan, view.intents[1]), (legacy_plan, view.intents[0])]:
        rejected_call = partial(validate_create_receipt, plan, intent, receipt())
        with pytest.raises(ValueError):
            rejected_call()
    rejected_call = partial(
        require_legacy_view, VersionedTransferView(legacy_plan, None, None, receipts=(receipt(),))
    )
    with pytest.raises(YorungeError) as raised:
        rejected_call()
    assert raised.value.code == "state_invalid"


def test_new_receipt_terminal_graph_and_legacy_terminal_are_both_valid():
    view = graph()
    validate_graph(view, manifest())
    validate_graph(replace(view, receipts=(receipt(), *view.receipts[1:])), manifest())
    assert hashlib.sha256(view.verification.encoded()).hexdigest() == (
        "cb5d7b1a55712f5b0e2afdd897a76daf39a13bcbd5dcb2648cfb6834fd05b2bb"
    )


def test_receipt_for_another_canonical_intent_is_orphan_in_graph():
    view = graph()
    changed = receipt(intent_id=OTHER)
    rejected_call = partial(
        validate_graph, replace(view, receipts=(changed, *view.receipts[1:])), manifest()
    )
    with pytest.raises(YorungeError) as raised:
        rejected_call()
    assert raised.value.code == "state_invalid"


@pytest.mark.parametrize("name", ["é" * 128, "😀" * 64, '"' * 128, "\\" * 128])
@pytest.mark.parametrize("org_id", [None, OTHER])
def test_actual_maximum_name_escape_receipt_fits_existing_slot(name, org_id):
    view = graph()
    body = receipt().created_dataset.model_dump(mode="json")
    body.update(name=name, org_id=org_id)
    value = receipt(created_dataset=body)
    parameters = view.plan.parameters.model_copy(update={"name": name})
    plan = view.plan.model_copy(update={"parameters": parameters})
    validate_create_receipt(plan, view.intents[0], value)
    assert len(value.encoded()) <= 1259 < value.max_wire_bytes


@pytest.mark.parametrize("size", [2047, 2048, 2049])
def test_receipt_wire_decoder_limit_and_canonical_storage(size):
    raw = GOLDEN + b" " * (size - len(GOLDEN))
    if size <= 2048:
        assert CreateReceiptV2.model_validate_json(raw) == receipt()
    else:
        with pytest.raises(ValueError):
            CreateReceiptV2.model_validate_json(raw)
    rejected_call = partial(decode_versioned, StageReceipt, CreateReceiptV2, raw.decode())
    with pytest.raises(YorungeError) as raised:
        rejected_call()
    assert raised.value.code == "state_invalid"


def test_large_clean_raw_response_projects_into_small_receipt():
    view = graph()
    body = receipt().created_dataset.model_dump(mode="json")
    body["unused_metadata"] = "clean" * 1600
    raw = canonical(body)
    assert 2048 < len(raw) < 1048576
    typed = codec.created(raw, view.plan.scope, view.plan.parameters, SECRET)
    assert typed == receipt().created_dataset and type(typed) is ProviderDataset
    assert receipt(created_dataset=typed.model_dump(mode="json")).encoded() == GOLDEN


def test_unused_metadata_never_bypasses_raw_secret_check():
    view = graph()
    body = receipt().created_dataset.model_dump(mode="json")
    body["unused_metadata"] = "clean" * 1600 + SECRET.reveal()
    raw = canonical(body)
    with pytest.raises(YorungeError) as raised:
        codec.created(raw, view.plan.scope, view.plan.parameters, SECRET)
    assert raised.value.code == "invalid_response"
