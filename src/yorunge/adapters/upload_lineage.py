"""Read-only lineage of a stored continuation: its sources, back to the root that made the dataset.

A continuation is chained to its source (another continuation, or the root) and bound to the
immutable baseline of that root: the dataset its create receipt recorded. Nothing here reads rows
itself. The caller hands in a reader that returns an operation's own validated view, so this
module is pure logic over views; it writes nothing and grants nothing.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from yorunge.domain.dataset_continuation import (
    ContinuationBinding,
    DatasetContinuationPlanV3,
    baseline_digest,
)
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_upload import MAX_TRANSFER_OPERATIONS, DatasetUploadPlan
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.platform_upload import ProviderDataset
from yorunge.domain.upload_resume import (
    ChainState,
    OperationJournal,
    StageFact,
    chain_blockers,
    merge_chain,
)

if TYPE_CHECKING:
    from yorunge.adapters.upload_store import VersionedTransferView

# An operation appears once in a lineage and the store holds at most this many.
MAX_LINEAGE = MAX_TRANSFER_OPERATIONS

OperationViewReader = Callable[[str], "VersionedTransferView"]
CreatedDataset = Callable[["VersionedTransferView"], ProviderDataset | None]
GraphComplete = Callable[["VersionedTransferView"], bool]


@dataclass(frozen=True, slots=True)
class Lineage:
    """The validated sources of a continuation, root first, and the dataset the root created."""

    sources: tuple[VersionedTransferView, ...]
    baseline: ProviderDataset


def _source_is_consistent(view: VersionedTransferView, plan: DatasetContinuationPlanV3) -> None:
    record = view.operation
    if record is None:
        raise ValueError("a source is an operation, not a plan")
    binding, source = plan.continuation, view.plan
    if (
        # A source has sent something: an admitted, cancelled or check-only operation never
        # becomes eligible, and what it never did cannot be continued.
        not record.workflow_latched
        or source.intent_digest() != binding.intent_digest
        or record.dataset_id != binding.dataset_id
        # The plan copies the root, the manifest and the parameters of its source as they are and
        # inherits its policy; a v1 plan has no policy, so it is never a source.
        or (source.root, source.manifest, source.parameters)
        != (plan.root, plan.manifest, plan.parameters)
        or (getattr(source, "admission_policy", None), getattr(source, "cost_policy", None))
        != (plan.admission_policy, plan.cost_policy)
    ):
        raise ValueError("source does not belong to this continuation")


def resolve_lineage(
    plan: DatasetContinuationPlanV3,
    read: OperationViewReader,
    created: CreatedDataset,
) -> Lineage:
    """Walk ``plan``'s sources to the root and check each link and the baseline.

    ``read`` returns the validated view of one operation (a missing operation is its error);
    ``created`` returns the dataset a root's create receipt recorded. Every disagreement is a
    ``ValueError``: a broken lineage is a corrupt history, never a partial answer.
    """
    binding = plan.continuation
    sources: list[VersionedTransferView] = []
    seen: set[str] = set()
    source_id = binding.source_operation_id
    while True:
        if source_id in seen or len(sources) >= MAX_LINEAGE:
            raise ValueError("lineage loops or is longer than the store can hold")
        seen.add(source_id)
        view = read(source_id)
        _source_is_consistent(view, plan)
        sources.append(view)
        parent = view.plan
        if isinstance(parent, DatasetContinuationPlanV3):
            other = parent.continuation
            if (other.baseline_operation_id, other.baseline_digest, other.dataset_id) != (
                binding.baseline_operation_id,
                binding.baseline_digest,
                binding.dataset_id,
            ):
                raise ValueError("lineage disagrees about its baseline")
            source_id = other.source_operation_id
            continue
        if not isinstance(parent, DatasetUploadPlan | DatasetUploadPlanV2):
            raise ValueError("unsupported root plan")
        break
    root = sources[-1]
    dataset = created(root)
    assert root.operation is not None
    if (
        root.operation.operation_id != binding.baseline_operation_id
        or dataset is None
        or dataset.id != binding.dataset_id
        or baseline_digest(dataset) != binding.baseline_digest
    ):
        raise ValueError("the root is not the baseline this continuation was prepared from")
    return Lineage(tuple(reversed(sources)), dataset)


def journal_of(view: VersionedTransferView, *, complete: bool) -> OperationJournal:
    """Stage facts of one stored operation: what the classifier takes of a lineage member.

    v1/v2 operations are chain roots. A continuation's parent is its source. A plan of any other
    type is refused instead of being read as a root: its ancestors' intents would silently drop out
    of the union and unconfirmed files would look clean. ``complete`` is the caller's verdict on
    whether every stage the graph needs has an accepted receipt.
    """
    record = view.operation
    if record is None:
        raise ValueError("an operation is needed for its journal")
    plan = view.plan
    if isinstance(plan, DatasetContinuationPlanV3):
        parent: str | None = plan.continuation.source_operation_id
    elif isinstance(plan, DatasetUploadPlan | DatasetUploadPlanV2):
        parent = None
    else:
        raise ValueError("unsupported plan")
    results = {receipt.intent_id: receipt.result for receipt in view.receipts}
    return OperationJournal(
        operation_id=record.operation_id,
        parent_operation_id=parent,
        dataset_id=record.dataset_id,
        manifest_digest=plan.manifest.digest,
        stages=tuple(
            StageFact(intent.kind, intent.file_index, results.get(intent.intent_id, "none"))
            for intent in view.intents
        ),
        graph_complete=complete,
    )


def check_selection(binding: ContinuationBinding, states: tuple[ChainState, ...]) -> None:
    """A continuation sends exactly the files its lineage has not confirmed.

    ``states`` is the lineage's combined confirm state per file. A file an accepted confirm
    already covers is never sent again, and a selected file is uncertain exactly when some member
    wrote a confirm intent for it that no accepted receipt answers.
    """
    if any(states[index] == "accepted" for index in binding.file_indices):
        raise ValueError("a file the lineage already confirmed is not sent again")
    if binding.uncertain_indices != tuple(
        index for index in binding.file_indices if states[index] == "intent"
    ):
        raise ValueError("uncertain files are the selected ones with an unanswered confirm")


def validate_selection(
    plan: DatasetContinuationPlanV3,
    lineage: Lineage,
    manifest: DatasetManifest,
    complete: GraphComplete,
) -> None:
    """The plan's file selection and the lineage's own blockers, as the lineage's journals say.

    A continuation is never prepared past a known rejection or a source whose graph is already
    complete (that is a reconcile), so neither can stand in a stored history.
    """
    last = len(lineage.sources) - 1
    summary = merge_chain(
        [
            journal_of(view, complete=index == last and complete(view))
            for index, view in enumerate(lineage.sources)
        ],
        manifest,
    )
    if chain_blockers(summary):
        raise ValueError("a lineage with a known rejection or a finished graph is not continued")
    check_selection(plan.continuation, summary.states)
