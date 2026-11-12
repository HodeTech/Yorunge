"""What the store must show, in the admitting transaction, before one more continuation starts.

The plan was prepared from a source that was frozen then; by the time it is admitted the source may
have moved on. Everything here is read inside the transaction that writes the new operation, so no
other writer can change it between the check and the write. Nothing is written here: the caller
cancels the stale admitted descendants this returns.
"""

from __future__ import annotations

import sqlite3

from yorunge.adapters.capability_cache import Stamp
from yorunge.adapters.upload_chain import chain_snapshot
from yorunge.adapters.upload_store import read_any_record
from yorunge.domain.capabilities import timestamp
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.dataset_transfer import TERMINAL
from yorunge.domain.errors import OperationError
from yorunge.domain.upload_resume import descendant_verdict, source_blockers


def continuation_admission(
    connection: sqlite3.Connection, plan: DatasetContinuationPlanV3, stamp: Stamp
) -> tuple[str, ...]:
    """Refuse the admission unless the chain ends at a frozen source with no other work in it.

    Returns the operations of descendants of the source that are admitted but whose lease has
    lapsed: they sent nothing and never will, they do not block, and the caller cancels them in the
    same transaction so that the source never holds two descendants that are not cancelled.
    Every refusal is ``operation_conflict`` naming the operation that stands in the way.
    """
    source_id = plan.continuation.source_operation_id
    snapshot = chain_snapshot(connection, source_id, stamp)
    source = read_any_record(connection, source_id)
    # The new operation is born after the last thing the source did, never before it.
    if timestamp(stamp.now) < source.updated_at:
        raise OperationError("operation_conflict", source_id)
    verdict = descendant_verdict(snapshot.descendants)
    # A source that is active, superseded or ended is not continued now; a frozen one is
    # ``unknown``: a ``running`` source whose lease lapsed has not been frozen yet.
    if source_blockers(snapshot.source, verdict) or snapshot.source.status != "unknown":
        raise OperationError("operation_conflict", verdict.related_operation_id or source_id)
    chain = {journal.operation_id for journal in snapshot.journals}
    chain.update(descendant.operation_id for descendant in snapshot.descendants)
    for (operation_id,) in connection.execute(
        "SELECT operation_id FROM upload_operations ORDER BY operation_id"
    ).fetchall():
        if operation_id in chain:
            continue
        record = read_any_record(connection, operation_id)
        # One dataset has one chain of work: nothing else may be running against it.
        if record.dataset_id == plan.continuation.dataset_id and record.status not in TERMINAL:
            raise OperationError("operation_conflict", operation_id)
    return tuple(
        descendant.operation_id
        for descendant in snapshot.descendants
        if descendant.status == "admitted" and not descendant.lease_active
    )
