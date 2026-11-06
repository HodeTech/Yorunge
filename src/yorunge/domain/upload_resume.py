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
import re
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import Final, Literal

from yorunge.domain.capabilities import canonical
from yorunge.domain.dataset_manifest import DatasetFile, DatasetManifest
from yorunge.domain.dataset_upload import MAX_UPLOAD_FILES
from yorunge.domain.errors import OperationError, YorungeError
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

# "none" differs by vocabulary: a stage without a receipt versus a file without a confirm intent.
ReceiptState = Literal["none", "accepted", "rejected"]
ChainState = Literal["none", "intent", "accepted"]
CHAIN_STATES: Final[tuple[ChainState, ...]] = ("none", "intent", "accepted")
OperationStatus = Literal["admitted", "running", "unknown", "succeeded", "failed", "cancelled"]
TERMINAL_STATUSES: Final[frozenset[OperationStatus]] = frozenset(
    {"succeeded", "failed", "cancelled"}
)
Action = Literal["prepare", "reconcile", "wait", "none"]
_DIGEST = re.compile(r"[0-9a-f]{64}")


def _is_digest(value: object) -> bool:
    return type(value) is str and _DIGEST.fullmatch(value) is not None


# --- journal facts and their chain union -------------------------------------------------------
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
    manifest_digest: str

    def __post_init__(self) -> None:
        # ``merge_chain`` is the producer; a state outside the closed set must never read as
        # "no intent", because that would offer an unconfirmed file for a silent resend.
        if (
            type(self.states) is not tuple
            or not 1 <= len(self.states) <= MAX_UPLOAD_FILES
            or any(state not in CHAIN_STATES for state in self.states)
            or type(self.rejected_receipt) is not bool
            or type(self.source_graph_complete) is not bool
            or not _is_digest(self.manifest_digest)
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
        # A continuation exists only for a created dataset, and the whole lineage shares it.
        and all(journal.dataset_id == root.dataset_id for journal in journals[1:])
        and (root.dataset_id is not None or len(journals) == 1)
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


def merge_chain(journals: Sequence[OperationJournal], manifest: DatasetManifest) -> ChainSummary:
    """Union of a lineage's journals over one manifest, root first.

    Every journal must have been recorded over that manifest, so file indices mean the same file in
    all of them; a malformed or foreign chain is ``state_invalid``.
    """
    file_count = manifest.file_count
    if not 1 <= file_count <= MAX_UPLOAD_FILES:
        raise ValueError("unsupported upload file count")
    if not journals:
        raise ValueError("a chain holds at least its source")
    if (
        not _chain_is_consistent(journals)
        or any(journal.manifest_digest != manifest.digest for journal in journals)
        or not all(
            _journal_is_valid(journal, file_count, root=position == 0)
            for position, journal in enumerate(journals)
        )
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
        manifest_digest=manifest.digest,
    )


# --- remote inventory --------------------------------------------------------------------------
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
    """Folds listing pages and stops at the first sign the listing cannot be trusted.

    The cap is checked per page: the page that crosses it is kept whole as evidence, so a too-large
    listing holds at most one page more than ``MAX_INVENTORY_ITEMS``.
    """

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


# --- classification ----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ContinuationSelection:
    """What a continuation plan would carry: every file that needs a transfer, never a subset."""

    file_indices: tuple[int, ...]
    uncertain_indices: tuple[int, ...]
    remote_present_count: int

    def __post_init__(self) -> None:
        files, uncertain = self.file_indices, self.uncertain_indices
        if (
            type(files) is not tuple
            or type(uncertain) is not tuple
            or any(
                type(i) is not int or not 0 <= i < MAX_UPLOAD_FILES for i in (*files, *uncertain)
            )
            or list(files) != sorted(set(files))
            or list(uncertain) != sorted(set(uncertain))
            or not set(uncertain) <= set(files)
            or type(self.remote_present_count) is not int
            or not 0 <= self.remote_present_count <= MAX_UPLOAD_FILES
        ):
            raise ValueError("invalid continuation selection")


@dataclass(frozen=True, slots=True)
class Classification:
    classes: tuple[FileClass, ...]
    blockers: tuple[Blocker, ...]
    classification_digest: str
    inventory_digest: str

    def __post_init__(self) -> None:
        if (
            type(self.classes) is not tuple
            or not 1 <= len(self.classes) <= MAX_UPLOAD_FILES
            or any(name not in FILE_CLASSES for name in self.classes)
            or type(self.blockers) is not tuple
            or tuple(b for b in BLOCKERS if b in self.blockers) != self.blockers
            or not _is_digest(self.classification_digest)
            or not _is_digest(self.inventory_digest)
            # A blocking class always stands behind its blocker.
            or any(
                name in self.classes and name not in self.blockers
                for name in ("drift_missing", "conflict", "inventory_unreliable")
            )
        ):
            raise ValueError("invalid classification")

    def count(self, file_class: FileClass) -> int:
        return self.classes.count(file_class)

    def indices(self, file_class: FileClass) -> tuple[int, ...]:
        """Manifest indices of one class, for reports; never a plan's selection."""
        return tuple(i for i, name in enumerate(self.classes) if name == file_class)

    def with_blockers(self, extra: Sequence[Blocker]) -> Classification:
        """The same evidence with the blockers a caller derived from the source record merged in.

        Report and ``--prepare`` plan only from the result, so ``plannable`` and ``selection()``
        then answer for every blocker, not just the ones the evidence produced.
        """
        if any(name not in BLOCKERS for name in extra):
            raise ValueError("closed blockers required")
        merged = {*self.blockers, *extra}
        return replace(self, blockers=tuple(b for b in BLOCKERS if b in merged))

    @property
    def plannable(self) -> bool:
        """No blocker is held. Evidence yields some; callers add theirs via ``with_blockers``."""
        return not self.blockers

    def selection(self) -> ContinuationSelection | None:
        """The transfer selection, or None while any blocker stands (it must not be read then)."""
        if self.blockers:
            return None
        return ContinuationSelection(
            file_indices=tuple(i for i, c in enumerate(self.classes) if c in SEND_CLASSES),
            uncertain_indices=self.indices("pending_uncertain"),
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
    """Positive evidence that the remote holds something else under this file's name or hash."""
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
    manifest: DatasetManifest, chain: ChainSummary, inventory: RemoteInventory
) -> Classification:
    """Closed class per manifest file, blockers and digests.

    Names are compared exactly (no case or Unicode folding). The table is applied as written even
    for a manifest that repeats a hash (older history): the file whose content already sits under
    another name is a ``conflict``, and ``--prepare`` refuses such content through the existing
    producer eligibility check before any plan exists.
    """
    files = manifest.files
    if chain.manifest_digest != manifest.digest:
        raise ValueError("chain summary belongs to another manifest")
    if len(chain.states) != len(files):
        raise ValueError("chain summary does not cover the manifest")
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


# --- descendants of the source -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DescendantFact:
    operation_id: str
    status: OperationStatus
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


# --- the source itself and the action to recommend ---------------------------------------------
@dataclass(frozen=True, slots=True)
class SourceFacts:
    """What the stored source record says; callers derive it from a validated record."""

    status: OperationStatus
    lease_active: bool
    policy: Literal["verified_only", "explicit_attempt"]
    has_created_dataset: bool


def source_blockers(source: SourceFacts, descendants: DescendantVerdict) -> tuple[Blocker, ...]:
    """The reference's eligibility table for the source and its descendants, in reporting order.

    Project membership and the local folder need other evidence; they stay with their callers.
    """
    raised: set[Blocker] = set()
    if source.status in TERMINAL_STATUSES:
        raised.add("source_terminal")
    if source.status == "admitted" or source.policy == "verified_only":
        raised.add("source_ineligible")
    if source.lease_active or descendants.blocker == "source_active":
        raised.add("source_active")
    if descendants.blocker == "source_superseded":
        raised.add("source_superseded")
    if not source.has_created_dataset:
        raised.add("create_unknown")
    return tuple(b for b in BLOCKERS if b in raised)


# The single recommended action is the first of these whose blocker stands.
_ACTIONS: Final[tuple[tuple[Blocker, Action], ...]] = (
    ("source_terminal", "none"),
    ("source_active", "wait"),
    ("source_superseded", "none"),
    ("source_ineligible", "none"),
    ("create_unknown", "none"),
    ("membership_unobserved", "none"),
    ("known_negative", "none"),
    ("reconcile_available", "reconcile"),
    ("local_changed", "none"),
    ("drift_missing", "none"),
    ("conflict", "none"),
    ("extra_remote", "none"),
    ("inventory_unreliable", "none"),
    ("inventory_too_large", "none"),
)


def recommended_action(blockers: Sequence[Blocker]) -> Action:
    """``prepare`` only without blockers; otherwise the reference's priority picks one action."""
    if any(name not in BLOCKERS for name in blockers):
        raise ValueError("closed blockers required")
    held = set(blockers)
    for blocker, action in _ACTIONS:
        if blocker in held:
            return action
    return "prepare"


class ContinuationNotPossible(OperationError):
    """``--prepare`` refused: the closed blockers say why; the resume report shows the detail."""

    def __init__(self, blockers: Sequence[Blocker], operation_id: str | None = None) -> None:
        ordered = tuple(blocker for blocker in BLOCKERS if blocker in set(blockers))
        if not ordered or ordered != tuple(blockers) or "source_active" in ordered:
            # An active source or descendant is ``operation_conflict`` with the successor named.
            raise ValueError("closed, ordered, distinct blockers without source_active required")
        super().__init__("continuation_not_possible", operation_id)
        self.blockers = ordered

    def envelope(self) -> dict[str, object]:
        value = super().envelope()
        details = value["details"]
        assert isinstance(details, dict)
        details["blockers"] = list(self.blockers)
        return value
