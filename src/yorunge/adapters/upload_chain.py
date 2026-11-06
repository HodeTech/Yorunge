"""Read-only chain facts of one stored upload operation; never a write, lease or permit."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from yorunge.adapters.upload_store import VersionedTransferView, acknowledged_stages
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_resume import OperationJournal, ReceiptState, StageFact


def _receipt_state(
    results: Mapping[str, Literal["accepted", "rejected"]], intent_id: str
) -> ReceiptState:
    return results[intent_id] if intent_id in results else "none"


def operation_journal(view: VersionedTransferView) -> OperationJournal:
    """Stage facts of a stored operation, without any receipt, key or created-dataset content.

    v1/v2 operations are chain roots; a continuation's parent link joins this once its plan type
    exists. Completeness is the verifier's own ``acknowledged_stages`` rule.
    """
    record = view.operation
    if record is None:
        raise YorungeError("operation_not_found")
    results = {receipt.intent_id: receipt.result for receipt in view.receipts}
    return OperationJournal(
        operation_id=record.operation_id,
        parent_operation_id=None,
        dataset_id=record.dataset_id,
        stages=tuple(
            StageFact(intent.kind, intent.file_index, _receipt_state(results, intent.intent_id))
            for intent in view.intents
        ),
        graph_complete=acknowledged_stages(view),
    )
