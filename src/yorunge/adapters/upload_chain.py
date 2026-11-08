"""Read-only chain facts of stored upload operations; never a write, lease or permit."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from yorunge.adapters.capability_cache import Stamp
from yorunge.adapters.upload_lineage import Lineage, journal_of
from yorunge.adapters.upload_store import (
    VersionedTransferView,
    acknowledged_stages,
    created_dataset,
    quota_used,
    read_any_record,
    read_manifest,
    read_plan,
    read_view_and_lineage,
)
from yorunge.domain.capabilities import instant
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3, baseline_digest
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_upload import DatasetUploadPlan
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.platform_upload import ProviderDataset
from yorunge.domain.upload_resume import (
    BLOCKERS,
    Blocker,
    ChainSummary,
    DescendantFact,
    OperationJournal,
    SourceFacts,
    chain_blockers,
    descendant_verdict,
    merge_chain,
    source_blockers,
)
from yorunge.domain.upload_resume_report import QuotaCounters
from yorunge.domain.upload_versions import UploadPlan, UploadRecord


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
    if not isinstance(
        view.plan, DatasetUploadPlan | DatasetUploadPlanV2 | DatasetContinuationPlanV3
    ):
        raise YorungeError("state_invalid")  # refused before anything of it is read
    return journal_of(view, complete=bool(view.intents) and acknowledged_stages(view))


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
        try:
            record = read_any_record(connection, operation_id)
            plan = read_plan(connection, record.plan_id)
        except (YorungeError, ValueError, TypeError):
            # The row may be a descendant, so the scan cannot go on; and a row whose plan is gone is
            # no "missing plan" of the operation that was asked about: the answer is the row's.
            raise OperationError("state_invalid", operation_id) from None
        if (
            isinstance(plan, DatasetContinuationPlanV3)
            and plan.continuation.source_operation_id == source_operation_id
        ):
            found.append(
                DescendantFact(record.operation_id, record.status, _lease_active(record, stamp))
            )
    return tuple(found)


def _snapshot(
    connection: sqlite3.Connection,
    record: UploadRecord,
    view: VersionedTransferView,
    lineage: Lineage | None,
    stamp: Stamp,
) -> ChainSnapshot:
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
            has_created_dataset=created_dataset(root) is not None,  # the root: never a continuation
        ),
        descendants=_descendants(connection, record.operation_id, stamp),
    )


def chain_snapshot(
    connection: sqlite3.Connection, operation_id: str, stamp: Stamp
) -> ChainSnapshot:
    """Journals, source facts and descendants of one stored operation.

    The caller owns the read transaction and the clock point ``stamp``; nothing is written.
    A broken lineage (missing source, loop, another manifest or baseline) is ``state_invalid``.
    """
    record = read_any_record(connection, operation_id)
    view, lineage = read_view_and_lineage(connection, record.plan_id)
    return _snapshot(connection, record, view, lineage, stamp)


@dataclass(frozen=True, slots=True)
class ResumeSource:
    """What a resume report and a continuation plan need of one source operation.

    ``chain`` is what changes (status, leases, descendants); the rest is immutable once stored: the
    source's own plan and manifest, and the root that made the dataset (``baseline`` is None while
    that create is unknown). ``quota`` is what the store holds, as its bounds count it. All of it
    is read in the one database snapshot that ``chain`` is.
    """

    chain: ChainSnapshot
    plan: UploadPlan
    manifest: DatasetManifest
    baseline: ProviderDataset | None
    baseline_operation_id: str
    baseline_digest: str | None
    intent_digest: str
    quota: QuotaCounters


def resume_source(connection: sqlite3.Connection, operation_id: str, stamp: Stamp) -> ResumeSource:
    """The chain facts and the immutable facts of one source, from one snapshot (read only)."""
    record = read_any_record(connection, operation_id)
    view, lineage = read_view_and_lineage(connection, record.plan_id)
    root = lineage.sources[0] if lineage is not None else view
    assert root.operation is not None
    baseline = lineage.baseline if lineage is not None else created_dataset(view)
    return ResumeSource(
        chain=_snapshot(connection, record, view, lineage, stamp),
        plan=view.plan,
        manifest=read_manifest(connection, view.plan),
        baseline=baseline,
        baseline_operation_id=root.operation.operation_id,
        baseline_digest=None if baseline is None else baseline_digest(baseline),
        intent_digest=root.operation.intent_digest,
        quota=quota_used(connection),
    )


def source_journal(source: ResumeSource) -> tuple[ChainSummary, tuple[Blocker, ...], str | None]:
    """What the journal alone says: the lineage, what rules the source out, the successor.

    Nothing is asked of the folder or the provider: the facts are those of one database snapshot.
    """
    try:
        chain = merge_chain(source.chain.journals, source.manifest)
    except ValueError:
        raise YorungeError("state_invalid") from None
    verdict = descendant_verdict(source.chain.descendants)
    held = {*source_blockers(source.chain.source, verdict), *chain_blockers(chain)}
    return (
        chain,
        tuple(blocker for blocker in BLOCKERS if blocker in held),
        verdict.related_operation_id,
    )
