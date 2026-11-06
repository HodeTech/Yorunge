"""Closed stage-graph specification of one upload plan version.

This module is the only place that derives the stage set, the predecessor rule, the journal
reservation and the request-count ceilings of a transfer from its plan version and file count.
Callers must not re-derive the ``create -> project_link -> presign -> put -> confirm`` arithmetic;
an unsupported plan version is rejected instead of being silently treated like a known one.
It performs no I/O and never grants remote authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from yorunge.domain.dataset_upload import MAX_UPLOAD_FILES

StageKind = Literal["create", "project_link", "presign", "put", "confirm"]
StageKey = tuple[StageKind, int | None]

# Plan versions whose graph is "create, project_link, then presign/put/confirm for every file".
SUPPORTED_PLAN_VERSIONS: Final[tuple[int, ...]] = (1, 2)
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

    create: Literal[1]
    project_link: Literal[1]
    presign: int
    put: int
    confirm: int

    @property
    def total(self) -> int:
        return self.create + self.project_link + self.presign + self.put + self.confirm


@dataclass(frozen=True, slots=True)
class StageGraphSpec:
    """Stage graph of a v1/v2 upload plan with ``file_count`` files."""

    plan_version: int
    file_count: int

    def __post_init__(self) -> None:
        if type(self.plan_version) is not int or self.plan_version not in SUPPORTED_PLAN_VERSIONS:
            raise ValueError("unsupported upload plan version")
        if type(self.file_count) is not int or not 1 <= self.file_count <= MAX_UPLOAD_FILES:
            raise ValueError("unsupported upload file count")

    @property
    def files(self) -> tuple[int, ...]:
        """File indices of this graph, in upload order (a tuple: later graphs name subsets)."""
        return tuple(range(self.file_count))

    @property
    def intent_count(self) -> int:
        """One intent per stage: create, project_link and three per file."""
        return 2 + 3 * self.file_count

    def required_stages(self) -> frozenset[StageKey]:
        result: set[StageKey] = {("create", None), ("project_link", None)}
        result.update((kind, index) for index in self.files for kind in FILE_STAGE_KINDS)
        return frozenset(result)

    def predecessor(self, kind: StageKind, index: int | None) -> StageKey | None:
        """The accepted stage that must precede ``(kind, index)``."""
        if kind == "create":
            return None
        if kind == "project_link":
            return "create", None
        if kind == "presign":
            return "project_link", None
        return ("presign" if kind == "put" else "put"), index

    def operation_reservation(self) -> int:
        """Reserve the worst future journal before admitting any remote intent."""
        return 16 * 1024 + self.intent_count * 4096 + 20 * 1024 + self.file_count * 512

    def request_counts(self) -> RequestCounts:
        return RequestCounts(
            create=1,
            project_link=1,
            presign=self.file_count,
            put=self.file_count,
            confirm=self.file_count,
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
        """Whether a stage's request binds the dataset id of the accepted create receipt."""
        return kind != "create"
