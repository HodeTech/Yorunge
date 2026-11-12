"""Closed stage-graph specification of one upload plan version.

This module is the only place that derives the stage set, the predecessor rule, the journal
reservation and the request-count ceilings of a transfer from its plan version and file count.
Callers must not re-derive the ``create -> project_link -> presign -> put -> confirm`` arithmetic;
an unsupported plan version is rejected instead of being silently treated like a known one.
A continuation (plan version 3) has no create or link: its graph is presign, put and confirm of the
selected files of an existing dataset, and the dataset comes from the plan, not from a receipt.
It performs no I/O and never grants remote authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from yorunge.domain.dataset_upload import MAX_UPLOAD_FILES

StageKind = Literal["create", "project_link", "presign", "put", "confirm"]
StageKey = tuple[StageKind, int | None]

# Plan versions whose graph is "create, project_link, then presign/put/confirm for every file".
ORIGINAL_PLAN_VERSIONS: Final[tuple[int, ...]] = (1, 2)
# The continuation graph: presign/put/confirm of a file subset, no create, no link.
CONTINUATION_PLAN_VERSION: Final = 3
SUPPORTED_PLAN_VERSIONS: Final[tuple[int, ...]] = (
    *ORIGINAL_PLAN_VERSIONS,
    CONTINUATION_PLAN_VERSION,
)
# Version new original-upload plans are written with. The v1 and v2 graphs are identical, so
# consumers that hold no plan (request limits, cost/review validators, ``operation_reservation``)
# name it explicitly. A continuation plan type has a different graph (a file subset and an existing
# dataset) and must review those call sites instead of inheriting this one.
ORIGINAL_PLAN_VERSION: Final = 2
STAGE_KINDS: Final[tuple[StageKind, ...]] = ("create", "project_link", "presign", "put", "confirm")
# Stages that carry a file index and, once accepted, the provider object key.
FILE_STAGE_KINDS: Final[tuple[StageKind, ...]] = ("presign", "put", "confirm")
# The original workflow runs at most this many PUT streams at once.
PUT_WORKERS: Final = 2


def file_index_matches(kind: StageKind, index: int | None) -> bool:
    """Whether ``index`` is present exactly for the stage kinds that act on one file."""
    return (kind in FILE_STAGE_KINDS) == (index is not None)


@dataclass(frozen=True, slots=True)
class RequestCounts:
    """Effectful request ceilings of one transfer (single attempt per stage)."""

    create: Literal[0, 1]
    project_link: Literal[0, 1]
    presign: int
    put: int
    confirm: int

    @property
    def total(self) -> int:
        return self.create + self.project_link + self.presign + self.put + self.confirm


@dataclass(frozen=True, slots=True)
class StageGraphSpec:
    """Stage graph of an upload plan of one version over a manifest of ``file_count`` files.

    A v1/v2 graph covers every file. A v3 graph covers only ``selection``, the files a
    continuation sends (possibly none); the manifest still has ``file_count`` files because the
    proof that closes the operation reads all of them.
    """

    plan_version: int
    file_count: int
    selection: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        if type(self.plan_version) is not int or self.plan_version not in SUPPORTED_PLAN_VERSIONS:
            raise ValueError("unsupported upload plan version")
        if type(self.file_count) is not int or not 1 <= self.file_count <= MAX_UPLOAD_FILES:
            raise ValueError("unsupported upload file count")
        if self.plan_version in ORIGINAL_PLAN_VERSIONS:
            if self.selection is not None:
                raise ValueError("an original plan has no file selection")
        elif (
            type(self.selection) is not tuple
            or any(type(i) is not int or not 0 <= i < self.file_count for i in self.selection)
            or list(self.selection) != sorted(set(self.selection))
        ):
            raise ValueError("a continuation plan needs an ordered distinct file selection")

    @property
    def continuation(self) -> bool:
        """Whether this graph is a continuation's: no create or link, a file subset."""
        return self.plan_version == CONTINUATION_PLAN_VERSION

    @property
    def files(self) -> tuple[int, ...]:
        """File indices of this graph, in upload order (a tuple: a continuation names a subset)."""
        return self.selection if self.selection is not None else tuple(range(self.file_count))

    @property
    def intent_count(self) -> int:
        """One intent per stage: three per file, plus create and link when the plan has them."""
        return 3 * len(self.files) + (0 if self.continuation else 2)

    @property
    def dataset_from_plan(self) -> bool:
        """Whether the dataset id comes from the plan (a continuation) and not a create receipt."""
        return self.continuation

    def required_stages(self) -> frozenset[StageKey]:
        result: set[StageKey] = (
            set() if self.continuation else {("create", None), ("project_link", None)}
        )
        result.update((kind, index) for index in self.files for kind in FILE_STAGE_KINDS)
        return frozenset(result)

    def predecessor(self, kind: StageKind, index: int | None) -> StageKey | None:
        """The accepted stage that must precede ``(kind, index)``."""
        if self.continuation and kind in ("create", "project_link"):
            raise ValueError("a continuation has no create or link stage")
        if kind == "create":
            return None
        if kind == "project_link":
            return "create", None
        if kind == "presign":
            return None if self.continuation else ("project_link", None)
        return ("presign" if kind == "put" else "put"), index

    def operation_reservation(self) -> int:
        """Reserve the worst future journal before admitting any remote intent.

        The proof term is the manifest's, not the selection's: the closing read covers every file.
        """
        return 16 * 1024 + self.intent_count * 4096 + 20 * 1024 + self.file_count * 512

    def request_counts(self) -> RequestCounts:
        sent = len(self.files)
        return RequestCounts(
            create=0 if self.continuation else 1,
            project_link=0 if self.continuation else 1,
            presign=sent,
            put=sent,
            confirm=sent,
        )

    def put_batches(self) -> tuple[tuple[int, ...], ...]:
        """File indices whose PUT streams run together, each batch followed by its confirms."""
        files = self.files
        return tuple(
            files[start : start + PUT_WORKERS] for start in range(0, len(files), PUT_WORKERS)
        )

    def takes_presign_key(self, kind: StageKind) -> bool:
        """Whether a stage's request binds the object key of the same file's presign receipt."""
        return kind in {"put", "confirm"}

    def takes_created_dataset(self, kind: StageKind) -> bool:
        """Whether a stage's request binds the dataset id (``dataset_from_plan``: its source)."""
        return kind != "create"
