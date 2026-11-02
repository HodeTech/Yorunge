"""The real journal records logical bindings while provider keys stay ephemeral."""

import json

from tests.integration.test_upload_journal import DATASET
from tests.integration.test_upload_journal import journal as journal
from yorunge.adapters.state import open_store
from yorunge.application import upload_descriptors as codec
from yorunge.domain.capabilities import timestamp
from yorunge.domain.dataset_transfer import StageReceipt


def test_logical_receipt_graph_never_persists_provider_key_url_or_network_uid(journal):
    record = journal.approved()
    for kind in ("create", "project_link"):
        intent, _, _ = journal.arm(record, kind)
        record = journal.accept(record, intent).operation
    secret = journal.bound.credential.secret
    expected = codec.contexts(journal.plan, journal.manifest, record.operation_id, DATASET, secret)
    descriptors = []

    def accept_binding(intent, context, *, sent=False):
        receipt = StageReceipt(
            schema_version=1,
            intent_id=intent.intent_id,
            recorded_at=timestamp(journal.clock.value),
            result="accepted",
            dataset_id=DATASET,
            object_key=context.local_binding,
            sent_bytes=context.file.size if sent else None,
            sent_sha256=context.file.sha256 if sent else None,
        )
        with open_store(journal.root) as store:
            return (
                journal.repository(store)
                .receipt(record.operation_id, record.lease, receipt)
                .operation
            )

    for index, context in enumerate(expected):
        intent, _, _ = journal.arm(record, "presign", index)
        key = f"unproven-provider-capability-{index}"
        raw = json.dumps(
            {
                "presigned_urls": [
                    {
                        "filename": context.file.path,
                        "sha256_hash": context.file.sha256,
                        "object_key": key,
                        "upload_url": f"/datasets/{DATASET}/upload/put?key={key}",
                    }
                ]
            }
        ).encode()
        descriptors.append(codec.presigned(raw, context, secret))
        record = accept_binding(intent, context)
    codec.distinct_uploads(tuple(descriptors), expected)
    for index, (descriptor, context) in enumerate(zip(descriptors, expected, strict=True)):
        descriptor.require(context)
        confirm = codec.confirm_content(descriptor, context, secret)
        assert context.local_binding.encode() not in confirm
        for kind in ("put", "confirm"):
            intent, _, _ = journal.arm(record, kind, index)
            record = accept_binding(intent, context, sent=kind == "put")
    with open_store(journal.root) as store:
        view = journal.repository(store).show(operation_id=record.operation_id)
        assert len(view.intents) == len(view.receipts) == 11
        dump = "\n".join(store.connection.iterdump())
        assert "unproven-provider-capability" not in dump
        assert "upload/put?key=" not in dump
        for context in expected:
            assert context.local_binding in dump
            assert context.client_uid not in dump
        store.verify()
