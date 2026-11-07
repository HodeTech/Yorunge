"""Read-only chain facts of stored upload operations; never a write, lease or permit."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from yorunge.adapters.capability_cache import Stamp
from yorunge.adapters.upload_lineage import journal_of
from yorunge.adapters.upload_store import (
    VersionedTransferView,
    acknowledged_stages,
    created_dataset,
    read_any_record,
    read_plan,
    read_view_and_lineage,
)
from yorunge.domain.capabilities import instant
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.dataset_transfer_v3 import TransferRecordV3
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_resume import DescendantFact, OperationJournal, SourceFacts
from yorunge.domain.upload_versions import UploadRecord


def operation_journal(view: VersionedTransferView) -> OperationJournal:
    """Stage facts of a stored operation, without any receipt, key or created-dataset content.

    v1/v2 operations are chain roots. A continuation's parent is its source. A plan of any other
    type is refused instead of being read as a root: its ancestors' intents would silently drop out
    of the union and unconfirmed files would look clean. Completeness is the verifier's own
    ``acknowledged_stages`` rule, except that an operation which sent nothing is not "complete": a
    graph with no stages is vacuously acknowledged, and no reconcile can finish what never began.
    """
    if view.operation is None:
        raise YorungeError("operation_not_found")
    try:
        return journal_of(view, complete=bool(view.intents) and acknowledged_stages(view))
    except ValueError:
        raise YorungeError("state_invalid") from None


@dataclass(frozen=True, slots=True)
class ChainSnapshot:
    """What a resume report needs of one source operation, read in one database snapshot.

    ``journals`` run from the root that created the dataset to the source itself, the order
    ``merge_chain`` takes; ``descendants`` are the continuations whose source is this operation.
    Reading them separately would let a continuation appear between the journals and the
    descendants, so the caller holds one read transaction around :func:`chain_snapshot`.
    """

    journals: tuple[OperationJournal, ...]
    source: SourceFacts
    descendants: tuple[DescendantFact, ...]


def _lease_active(record: UploadRecord, stamp: Stamp) -> bool:
    lease = record.lease
    return (
        lease is not None
        and (lease.identity_epoch, lease.clock_generation)
        == (stamp.identity_epoch, stamp.generation)
        and instant(lease.expires_at) > stamp.now
    )


def _descendants(
    connection: sqlite3.Connection, source_operation_id: str, stamp: Stamp
) -> tuple[DescendantFact, ...]:
    found = []
    for (operation_id,) in connection.execute(
        "SELECT operation_id FROM upload_operations ORDER BY operation_id"
    ).fetchall():
        record = read_any_record(connection, operation_id)
        if not isinstance(record, TransferRecordV3):
            continue
        plan = read_plan(connection, record.plan_id)
        if (
            isinstance(plan, DatasetContinuationPlanV3)
            and plan.continuation.source_operation_id == source_operation_id
        ):
            found.append(
                DescendantFact(record.operation_id, record.status, _lease_active(record, stamp))
            )
    return tuple(found)


def chain_snapshot(
    connection: sqlite3.Connection, operation_id: str, stamp: Stamp
) -> ChainSnapshot:
    """Journals, source facts and descendants of one stored operation.

    The caller owns the read transaction and the clock point ``stamp``; nothing is written.
    A broken lineage (missing source, loop, another manifest or baseline) is ``state_invalid``.
    """
    record = read_any_record(connection, operation_id)
    view, lineage = read_view_and_lineage(connection, record.plan_id)
    chain = (*lineage.sources, view) if lineage is not None else (view,)
    root = chain[0]
    plan = view.plan
    return ChainSnapshot(
        journals=tuple(operation_journal(item) for item in chain),
        source=SourceFacts(
            status=record.status,
            lease_active=_lease_active(record, stamp),
            policy=(
                plan.admission_policy
                if isinstance(plan, DatasetUploadPlanV2 | DatasetContinuationPlanV3)
                else "verified_only"
            ),
            has_created_dataset=lineage is not None or created_dataset(root) is not None,
        ),
        descendants=_descendants(connection, operation_id, stamp),
    )
