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

from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3, baseline_digest
from yorunge.domain.dataset_upload import MAX_TRANSFER_OPERATIONS, DatasetUploadPlan
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.platform_upload import ProviderDataset

if TYPE_CHECKING:
    from yorunge.adapters.upload_store import VersionedTransferView

# An operation appears once in a lineage and the store holds at most this many.
MAX_LINEAGE = MAX_TRANSFER_OPERATIONS

OperationViewReader = Callable[[str], "VersionedTransferView"]
CreatedDataset = Callable[["VersionedTransferView"], ProviderDataset | None]


@dataclass(frozen=True, slots=True)
class Lineage:
    """The validated sources of a continuation, root first, and the dataset the root created."""

    sources: tuple[VersionedTransferView, ...]
    baseline: ProviderDataset


def _source_is_consistent(view: VersionedTransferView, plan: DatasetContinuationPlanV3) -> None:
    record = view.operation
    if record is None:
        raise ValueError("a source is an operation, not a plan")
    binding = plan.continuation
    if (
        # A source has sent something: an admitted, cancelled or check-only operation never
        # becomes eligible, and what it never did cannot be continued.
        not record.workflow_latched
        or view.plan.manifest.digest != plan.manifest.digest
        or view.plan.intent_digest() != binding.intent_digest
        or record.dataset_id != binding.dataset_id
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
