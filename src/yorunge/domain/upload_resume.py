"""Closed resume evidence classification of an interrupted upload (ADR-0031 section 3).

The union of the source lineage's journals and one complete remote inventory are reduced to a
closed class for every manifest file, closed plan-level blockers and two canonical digests.
Everything here is pure: it performs no I/O, reads no receipt body and never grants authority.
Contradictory or unverifiable evidence can only produce a blocking class, never a safe one.

This module derives the blockers that follow from journals, inventory and descendants. The caller
that holds the source record, its lease, project membership and the local folder adds
``source_active``/``source_ineligible``/``source_terminal``/``create_unknown``/
``membership_unobserved``/``local_changed``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final, Literal

from yorunge.domain.capabilities import canonical
from yorunge.domain.dataset_manifest import DatasetFile
from yorunge.domain.dataset_upload import MAX_UPLOAD_FILES
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_graph import (
    FILE_STAGE_KINDS,
    STAGE_KINDS,
    StageKind,
    file_index_matches,
)

FileClass = Literal[
    "confirmed",
    "observed",
    "pending_clean",
    "pending_uncertain",
    "drift_missing",
    "conflict",
    "inventory_unreliable",
]
FILE_CLASSES: Final[tuple[FileClass, ...]] = (
    "confirmed",
    "observed",
    "pending_clean",
    "pending_uncertain",
    "drift_missing",
    "conflict",
    "inventory_unreliable",
)
# Classes that need a new file transfer (the members of ``file_indices``).
SEND_CLASSES: Final[frozenset[FileClass]] = frozenset({"pending_clean", "pending_uncertain"})
# Classes whose item already exists remotely (``remote_present_count``).
PRESENT_CLASSES: Final[frozenset[FileClass]] = frozenset({"confirmed", "observed"})

Blocker = Literal[
    "source_active",
    "source_ineligible",
    "source_superseded",
    "source_terminal",
    "reconcile_available",
    "create_unknown",
    "membership_unobserved",
    "known_negative",
    "drift_missing",
    "conflict",
    "extra_remote",
    "inventory_unreliable",
    "inventory_too_large",
    "local_changed",
]
# The closed order in which blockers are reported.
BLOCKERS: Final[tuple[Blocker, ...]] = (
    "source_active",
    "source_ineligible",
    "source_superseded",
    "source_terminal",
    "reconcile_available",
    "create_unknown",
    "membership_unobserved",
    "known_negative",
    "drift_missing",
    "conflict",
    "extra_remote",
    "inventory_unreliable",
    "inventory_too_large",
    "local_changed",
)

# Limits of one remote listing: the manifest holds at most 128 files, so a larger dataset holds
# many items that are not ours and continuation is not supported for it.
MAX_INVENTORY_ITEMS: Final = 1024
MAX_INVENTORY_PAGES: Final = 128

ReceiptState = Literal["none", "accepted", "rejected"]
ChainState = Literal["none", "intent", "accepted"]
CHAIN_STATES: Final[tuple[ChainState, ...]] = ("none", "intent", "accepted")


# --- journal facts and their chain union ---------------------------------------------------------
@dataclass(frozen=True, slots=True)
class StageFact:
    """One stored stage intent and what became of its receipt; no receipt content."""

    kind: StageKind
    file_index: int | None
    receipt: ReceiptState


@dataclass(frozen=True, slots=True)
class OperationJournal:
    """Facts of one stored operation. ``parent_operation_id`` is None for a chain root.

    The facts come from validated stored records: a cancelled operation holds no intent and a
    failed one holds some, so the descendant and chain rules do not re-derive that.
    """

    operation_id: str
    parent_operation_id: str | None
    dataset_id: str | None
    manifest_digest: str
    stages: tuple[StageFact, ...]
    graph_complete: bool


@dataclass(frozen=True, slots=True)
class ChainSummary:
    """Per file: any accepted confirm receipt, else any confirm intent, over the whole lineage."""

    states: tuple[ChainState, ...]
    rejected_receipt: bool
    source_graph_complete: bool
    operation_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        # ``merge_chain`` is the producer; a state outside the closed set must never read as
        # "no intent", because that would offer an unconfirmed file for a silent resend.
        if (
            type(self.states) is not tuple
            or any(state not in CHAIN_STATES for state in self.states)
            or type(self.rejected_receipt) is not bool
            or type(self.source_graph_complete) is not bool
        ):
            raise ValueError("invalid chain summary")


def _chain_is_consistent(journals: Sequence[OperationJournal]) -> bool:
    root = journals[0]
    ids = [journal.operation_id for journal in journals]
    return (
        len(set(ids)) == len(ids)
        and root.parent_operation_id is None
        and all(
            later.parent_operation_id == earlier.operation_id
            for earlier, later in zip(journals, journals[1:], strict=False)
        )
        # A continuation exists only for a created dataset, and the whole lineage shares it and
        # the manifest whose file indices the union is taken over.
        and all(journal.dataset_id == root.dataset_id for journal in journals[1:])
        and (root.dataset_id is not None or len(journals) == 1)
        and all(journal.manifest_digest == root.manifest_digest for journal in journals[1:])
    )


def _stage_is_valid(stage: StageFact, file_count: int) -> bool:
    index = stage.file_index
    if stage.kind not in STAGE_KINDS or stage.receipt not in ("none", "accepted", "rejected"):
        return False
    if not file_index_matches(stage.kind, index):
        return False
    return index is None or (type(index) is int and 0 <= index < file_count)


def _journal_is_valid(journal: OperationJournal, file_count: int, *, root: bool) -> bool:
    keys = [(stage.kind, stage.file_index) for stage in journal.stages]
    return (
        len(set(keys)) == len(keys)
        and all(_stage_is_valid(stage, file_count) for stage in journal.stages)
        # Only the root creates and links; a continuation works inside the existing dataset.
        and (root or all(stage.kind in FILE_STAGE_KINDS for stage in journal.stages))
    )


def merge_chain(journals: Sequence[OperationJournal], file_count: int) -> ChainSummary:
    """Union of a lineage's journals, root first. A malformed chain is ``state_invalid``."""
    if type(file_count) is not int or not 1 <= file_count <= MAX_UPLOAD_FILES:
        raise ValueError("unsupported upload file count")
    if not journals:
        raise ValueError("a chain holds at least its source")
    if not _chain_is_consistent(journals) or not all(
        _journal_is_valid(journal, file_count, root=position == 0)
        for position, journal in enumerate(journals)
    ):
        raise YorungeError("state_invalid")
    states: list[ChainState] = ["none"] * file_count
    for journal in journals:
        for stage in journal.stages:
            if stage.kind != "confirm" or stage.file_index is None:
                continue
            if stage.receipt == "accepted":
                states[stage.file_index] = "accepted"
            elif states[stage.file_index] == "none":
                states[stage.file_index] = "intent"
    return ChainSummary(
        states=tuple(states),
        rejected_receipt=any(
            stage.receipt == "rejected" for journal in journals for stage in journal.stages
        ),
        source_graph_complete=journals[-1].graph_complete,
        operation_ids=tuple(journal.operation_id for journal in journals),
    )


# --- remote inventory ----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class RemoteItem:
    """One listed remote item. ``repr`` hides name and identity: remote data stays out of logs."""

    path: str = field(repr=False)
    size: int
    sha256: str | None
    item_id: str = field(repr=False)


ListingFault = Literal["total_mismatch", "cursor_loop", "page_limit", "too_large"]


@dataclass(frozen=True, slots=True)
class RemoteInventory:
    """Items observed while listing, and the reasons the listing itself cannot be trusted."""

    items: tuple[RemoteItem, ...] = field(repr=False)
    faults: frozenset[ListingFault] = frozenset()


class InventoryFold:
    """Folds listing pages and stops at the first sign the listing cannot be trusted."""

    def __init__(self) -> None:
        self._items: list[RemoteItem] = []
        self._cursors: set[str] = set()
        self._totals: set[int] = set()
        self._faults: set[ListingFault] = set()
        self._pages = 0
        self._finished = False

    def _stop(self, fault: ListingFault) -> None:
        self._faults.add(fault)
        self._finished = True

    def add(self, items: Sequence[RemoteItem], total: int, next_cursor: str | None) -> str | None:
        """Fold one page; return the next page's cursor, or None when the listing is over."""
        if self._finished:
            raise ValueError("listing already finished")
        self._pages += 1
        self._items.extend(items)
        self._totals.add(total)
        if len(self._items) > MAX_INVENTORY_ITEMS:
            self._stop("too_large")
        elif next_cursor is None:
            if self._totals != {len(self._items)}:
                self._faults.add("total_mismatch")
            self._finished = True
        elif next_cursor in self._cursors:
            self._stop("cursor_loop")
        elif self._pages >= MAX_INVENTORY_PAGES:
            self._stop("page_limit")
        else:
            self._cursors.add(next_cursor)
            return next_cursor
        return None

    def result(self) -> RemoteInventory:
        if not self._finished:
            raise ValueError("listing not finished")
        return RemoteInventory(tuple(self._items), frozenset(self._faults))


# --- classification ------------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Selection:
    """What a continuation plan would carry: every file that needs a transfer, never a subset."""

    file_indices: tuple[int, ...]
    uncertain_indices: tuple[int, ...]
    remote_present_count: int


@dataclass(frozen=True, slots=True)
class Classification:
    classes: tuple[FileClass, ...]
    blockers: tuple[Blocker, ...]
    classification_digest: str
    inventory_digest: str

    def count(self, file_class: FileClass) -> int:
        return self.classes.count(file_class)

    @property
    def plannable(self) -> bool:
        """No blocker derived from journals, inventory or the source graph stands.

        The caller that holds the source record, its lease, project membership and the local
        folder adds its own blockers before a plan is prepared.
        """
        return not self.blockers

    def selection(self) -> Selection | None:
        """The transfer selection, or None while any blocker stands (it must not be read then)."""
        if self.blockers:
            return None
        return Selection(
            file_indices=tuple(i for i, c in enumerate(self.classes) if c in SEND_CLASSES),
            uncertain_indices=tuple(
                i for i, c in enumerate(self.classes) if c == "pending_uncertain"
            ),
            remote_present_count=sum(c in PRESENT_CLASSES for c in self.classes),
        )


def inventory_digest(items: Sequence[RemoteItem]) -> str:
    """Digest of the sorted (path, size, sha256) set; item identity and provider time stay out."""
    ordered = sorted(items, key=lambda i: (i.path, i.size, i.sha256 or ""))
    rows = [[i.path, i.size, i.sha256] for i in ordered]
    return hashlib.sha256(canonical({"kind": "upload_inventory", "items": rows})).hexdigest()


def classification_digest(classes: Sequence[FileClass], chain: ChainSummary) -> str:
    """Digest of the class vector and the lineage's combined confirm state per file."""
    return hashlib.sha256(
        canonical(
            {
                "kind": "upload_classification",
                "files": [[index, name] for index, name in enumerate(classes)],
                "chain": {"states": list(chain.states), "rejected": chain.rejected_receipt},
            }
        )
    ).hexdigest()


def _conflicts(file: DatasetFile, same_name: Sequence[RemoteItem], other_sha: bool) -> bool:
    """Positive evidence that the remote holds a different thing under this file's name or hash."""
    return (
        len({item.item_id for item in same_name}) > 1
        or any(item.size != file.size for item in same_name)
        or any(item.sha256 not in (None, file.sha256) for item in same_name)
        or other_sha
    )


def _by_chain_state(state: ChainState, exact: bool) -> FileClass:
    if state == "accepted":
        return "confirmed" if exact else "drift_missing"
    if exact:
        return "observed"
    if state == "intent":
        return "pending_uncertain"
    if state == "none":
        return "pending_clean"
    raise ValueError("invalid chain state")


def classify(
    files: Sequence[DatasetFile], chain: ChainSummary, inventory: RemoteInventory
) -> Classification:
    """Closed class per manifest file, blockers and digests.

    Names are compared exactly (no case or Unicode folding). A manifest that repeats a path or a
    hash cannot come from a v2 plan (duplicate content is refused at preparation) and is
    ``state_invalid``.
    """
    if len(chain.states) != len(files):
        raise ValueError("chain summary does not cover the manifest")
    if len({file.path for file in files}) != len(files) or len(
        {file.sha256 for file in files}
    ) != len(files):
        raise YorungeError("state_invalid")
    items = inventory.items
    by_name: dict[str, list[RemoteItem]] = {}
    by_sha: dict[str, list[RemoteItem]] = {}
    for item in items:
        by_name.setdefault(item.path, []).append(item)
        if item.sha256 is not None:
            by_sha.setdefault(item.sha256, []).append(item)
    # Without a trustworthy listing neither absence nor uniqueness can be claimed.
    unreliable = (
        bool(inventory.faults)
        or any(item.sha256 is None for item in items)
        or len({item.item_id for item in items}) != len(items)
    )
    classes: list[FileClass] = []
    for file, state in zip(files, chain.states, strict=True):
        same_name = by_name.get(file.path, [])
        other_sha = any(item.path != file.path for item in by_sha.get(file.sha256, []))
        if _conflicts(file, same_name, other_sha):
            classes.append("conflict")
        elif unreliable:
            classes.append("inventory_unreliable")
        else:
            classes.append(_by_chain_state(state, bool(same_name)))
    names = {file.path for file in files}
    raised: set[Blocker] = set()
    if chain.source_graph_complete:
        raised.add("reconcile_available")
    if chain.rejected_receipt:
        raised.add("known_negative")
    if "drift_missing" in classes:
        raised.add("drift_missing")
    if "conflict" in classes:
        raised.add("conflict")
    if unreliable:
        raised.add("inventory_unreliable")
    if any(item.path not in names for item in items):
        raised.add("extra_remote")
    if "too_large" in inventory.faults:
        raised.add("inventory_too_large")
    return Classification(
        classes=tuple(classes),
        blockers=tuple(b for b in BLOCKERS if b in raised),
        classification_digest=classification_digest(classes, chain),
        inventory_digest=inventory_digest(items),
    )


# --- descendants of the source -------------------------------------------------------------------
DescendantStatus = Literal["admitted", "running", "unknown", "succeeded", "failed", "cancelled"]


@dataclass(frozen=True, slots=True)
class DescendantFact:
    operation_id: str
    status: DescendantStatus
    lease_active: bool


@dataclass(frozen=True, slots=True)
class DescendantVerdict:
    blocker: Literal["source_active", "source_superseded"] | None
    related_operation_id: str | None


def descendant_verdict(descendants: Sequence[DescendantFact]) -> DescendantVerdict:
    """Whether a descendant makes the source inactive (wait) or superseded (use the descendant)."""
    relevant = [
        d
        for d in descendants
        # A cancelled descendant ran nothing; an admitted one whose lease lapsed is cancelled by
        # the next prepare. Neither blocks the source.
        if d.status != "cancelled" and not (d.status == "admitted" and not d.lease_active)
    ]
    if len(relevant) > 1:
        raise YorungeError("state_invalid")
    if not relevant:
        return DescendantVerdict(None, None)
    descendant = relevant[0]
    live = descendant.lease_active and descendant.status in {"admitted", "running", "unknown"}
    return DescendantVerdict(
        "source_active" if live else "source_superseded", descendant.operation_id
    )
