"""The shared semantic rule matches independent old V1/V2 wire vectors exactly."""

import json
from pathlib import Path

from tests.contracts.test_upload_versions import graph, manifest
from yorunge.domain.upload_requests import upload_request_digest

FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_shared_request_binding_matches_every_literal_v2_stage():
    view, source = graph(), manifest()
    by_intent = {receipt.intent_id: receipt for receipt in view.receipts}
    presigned = {}
    for intent in view.intents:
        index = intent.file_index
        result = upload_request_digest(
            view.plan.digest,
            intent.kind,
            index,
            source.files[index] if index is not None else None,
            view.operation.dataset_id if intent.kind != "create" else None,
            presigned[index] if intent.kind in {"put", "confirm"} else None,
        )
        assert result == intent.request_digest
        if intent.kind == "presign":
            presigned[index] = by_intent[intent.intent_id].object_key


def test_shared_request_binding_preserves_literal_v1_create_digest():
    body = json.loads((FIXTURES / "dataset-transfer-journal-v1.json").read_bytes())
    intent = body["intent"]
    assert intent["kind"] == "create" and intent["file_index"] is None
    assert (
        upload_request_digest(body["record"]["plan_digest"], "create", None, None, None, None)
        == intent["request_digest"]
    )
