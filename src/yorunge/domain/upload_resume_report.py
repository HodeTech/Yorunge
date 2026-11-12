"""The read-only resume report: what an interrupted upload still needs and why it is blocked.

The report carries counts, closed blocker names, digests and a few relative example paths of
problematic files. It never carries owner, name, created-dataset or receipt content, keys, URLs or
the paths of extra remote items. Report mode answers with it whatever the classification is, even
when nothing could be observed (an unknown create, a source that may not be read): everything that
comes from the remote observation then sits in ``observation``, which is absent. Preparing a plan is
a separate step that happens only without blockers.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, ClassVar, Final, Literal, Self

from pydantic import Field, field_validator, model_validator

from yorunge.domain.capabilities import instant
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3, binding_matches
from yorunge.domain.dataset_manifest import DatasetManifest, Sha256, file_parts
from yorunge.domain.dataset_upload import (
    MAX_TRANSFER_FILES,
    MAX_TRANSFER_OPERATIONS,
    MAX_TRANSFER_PAYLOAD_BYTES,
    MAX_TRANSFER_PLANS,
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_FILES,
    MAX_UPLOAD_PLAN_BYTES,
    PLAN_ALLOWANCE_BYTES,
    UploadWire,
    manifest_reference,
    provider_uuid,
)
from yorunge.domain.state import canonical_uuid
from yorunge.domain.upload_graph import CONTINUATION_PLAN_VERSION, StageGraphSpec
from yorunge.domain.upload_resume import (
    BLOCKERS,
    FILE_CLASSES,
    SEND_CLASSES,
    Action,
    Blocker,
    Classification,
    recommended_action,
)

# Classes a user has to act on; their relative paths may be listed (never more than a handful).
ProblemClass = Literal["pending_uncertain", "drift_missing", "conflict", "inventory_unreliable"]
PROBLEM_CLASSES: Final[tuple[ProblemClass, ...]] = (
    "pending_uncertain",
    "drift_missing",
    "conflict",
    "inventory_unreliable",
)
MAX_EXAMPLES = 8
# Blockers the local journal alone establishes. While one holds nothing remote is read, so the
# report has no observation (and no dataset to read when the create itself is unknown).
JOURNAL_BLOCKERS = frozenset(
    {
        "source_active",
        "source_ineligible",
        "source_superseded",
        "source_terminal",
        "reconcile_available",
        "create_unknown",
        "known_negative",
    }
)
# Blockers only a remote inventory read can establish; without an observation they cannot stand.
INVENTORY_BLOCKERS = frozenset(
    {"drift_missing", "conflict", "extra_remote", "inventory_unreliable", "inventory_too_large"}
)


def continuation_added_payload_bytes(
    file_count: int, selected: int | None = None, plan_bytes: int | None = None
) -> int:
    """Upper bound of the payload bytes one continuation attempt adds to the store's quota.

    The capacity check counts a plan's stored bytes, the journal reservation of its operation and
    the flat allowance per plan. The root's namespace and manifest rows are shared, so they add
    nothing. ``selected`` is the number of files the attempt sends (every file while it is not
    known) and ``plan_bytes`` the size of a plan that already exists (the wire ceiling otherwise).
    The closing proof reads the whole manifest, so the reservation grows with ``file_count``.
    """
    if (
        type(file_count) is not int
        or not 1 <= file_count <= MAX_UPLOAD_FILES
        or (selected is not None and (type(selected) is not int or not 0 <= selected <= file_count))
        or (
            plan_bytes is not None
            and (type(plan_bytes) is not int or not 1 <= plan_bytes <= MAX_UPLOAD_PLAN_BYTES)
        )
    ):
        raise ValueError("a manifest size, a selection within it and a plan within its ceiling")
    sending = file_count if selected is None else selected
    reservation = StageGraphSpec(
        CONTINUATION_PLAN_VERSION, file_count, tuple(range(sending))
    ).operation_reservation()
    return (
        PLAN_ALLOWANCE_BYTES
        + (MAX_UPLOAD_PLAN_BYTES if plan_bytes is None else plan_bytes)
        + reservation
    )


Count = Annotated[int, Field(ge=0, le=MAX_UPLOAD_FILES)]


class ResumeClassCounts(UploadWire):
    confirmed: Count
    observed: Count
    pending_clean: Count
    pending_uncertain: Count
    drift_missing: Count
    conflict: Count
    inventory_unreliable: Count

    def total(self) -> int:
        return (
            self.confirmed
            + self.observed
            + self.pending_clean
            + self.pending_uncertain
            + self.drift_missing
            + self.conflict
            + self.inventory_unreliable
        )


class ResumeExamples(UploadWire):
    file_class: ProblemClass
    paths: Annotated[tuple[str, ...], Field(min_length=1, max_length=MAX_EXAMPLES)]

    @field_validator("paths")
    @classmethod
    def relative_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for path in value:
            file_parts(path)
        encoded = [path.encode("utf-8") for path in value]
        if encoded != sorted(set(encoded)):
            raise ValueError("ordered distinct example paths required")
        return value


class QuotaCounters(UploadWire):
    """The four store-wide counters the capacity check bounds: plans, operations, files, payload."""

    plans: Annotated[int, Field(ge=0, le=MAX_TRANSFER_PLANS)]
    operations: Annotated[int, Field(ge=0, le=MAX_TRANSFER_OPERATIONS)]
    files: Annotated[int, Field(ge=0, le=MAX_TRANSFER_FILES)]
    payload_bytes: Annotated[int, Field(ge=0, le=MAX_TRANSFER_PAYLOAD_BYTES)]


class ResumeObservation(UploadWire):
    """What one remote observation established: classes, the send selection and the examples."""

    class_counts: ResumeClassCounts
    send_files: Count
    send_bytes: Annotated[int, Field(ge=0, le=MAX_UPLOAD_BYTES)]
    unconfirmed_ack_required: bool
    classification_digest: Sha256
    inventory_digest: Sha256
    examples: Annotated[tuple[ResumeExamples, ...], Field(max_length=len(PROBLEM_CLASSES))]

    @model_validator(mode="after")
    def consistent(self) -> Self:
        counts = self.class_counts
        if self.send_files != counts.pending_clean + counts.pending_uncertain:
            raise ValueError("files to send are the unsent and unconfirmed ones")
        if self.unconfirmed_ack_required != bool(counts.pending_uncertain):
            raise ValueError("acknowledgement is needed exactly for unconfirmed files")
        if not self.send_files and self.send_bytes:
            raise ValueError("no files to send, no bytes to send")
        if counts.inventory_unreliable and (
            counts.confirmed
            or counts.observed
            or counts.pending_clean
            or counts.pending_uncertain
            or counts.drift_missing
        ):
            raise ValueError("an unreliable listing leaves no other non-conflicting class")
        classes = [example.file_class for example in self.examples]
        if classes != [name for name in PROBLEM_CLASSES if name in classes]:
            raise ValueError("ordered distinct example classes required")
        for example in self.examples:
            if len(example.paths) > getattr(counts, example.file_class):
                raise ValueError("examples cannot outnumber their class")
        return self


class DatasetUploadResumeReport(UploadWire):
    # At most three problem classes stand together (an unreliable listing excludes two of them),
    # each listing eight paths; a path is at most 1 KiB and escapes to at most three times that,
    # so the worst case is near 75 KiB and the limit leaves room for the rest.
    max_wire_bytes: ClassVar[int] = 128 * 1024
    schema_version: Literal[1]
    kind: Literal["dataset_upload_resume_report"]
    source_operation_id: str
    dataset_id: str | None
    eligible: bool
    blockers: tuple[Blocker, ...]
    recommended_action: Action
    related_operation_id: str | None
    file_count: Annotated[int, Field(ge=1, le=MAX_UPLOAD_FILES)]
    observation: ResumeObservation | None
    quota_used: QuotaCounters
    quota_added: QuotaCounters
    observed_at: str
    plan_id: str | None
    plan_digest: Sha256 | None

    @field_validator("source_operation_id", "related_operation_id", "plan_id")
    @classmethod
    def identifiers(cls, value: str | None) -> str | None:
        return canonical_uuid(value) if value is not None else None

    @field_validator("dataset_id")
    @classmethod
    def dataset(cls, value: str | None) -> str | None:
        return provider_uuid(value) if value is not None else None

    @model_validator(mode="after")
    def consistent(self) -> Self:
        instant(self.observed_at)
        self._blockers_and_action()
        self._observation()
        self._quota()
        self._plan_and_related()
        self.encoded()
        return self

    def _blockers_and_action(self) -> None:
        if tuple(b for b in BLOCKERS if b in self.blockers) != self.blockers:
            raise ValueError("closed, ordered, distinct blockers required")
        if self.eligible != (not self.blockers) or self.recommended_action != recommended_action(
            self.blockers
        ):
            raise ValueError("eligibility and action must follow the blockers")
        if "inventory_too_large" in self.blockers and "inventory_unreliable" not in self.blockers:
            raise ValueError("a too large listing is also an unreliable one")
        if (self.dataset_id is None) != ("create_unknown" in self.blockers):
            raise ValueError("a dataset is unknown exactly when its create is")

    def _observation(self) -> None:
        observation = self.observation
        held = set(self.blockers)
        if observation is None:
            if not held or INVENTORY_BLOCKERS & held:
                raise ValueError("without an observation the blockers must come from the journal")
            return
        if JOURNAL_BLOCKERS & held:
            raise ValueError("a journal-level blocker means nothing was read")
        counts = observation.class_counts
        if counts.total() != self.file_count:
            raise ValueError("class counts must cover the manifest")
        for name in ("drift_missing", "conflict", "inventory_unreliable"):
            if getattr(counts, name) and name not in self.blockers:
                raise ValueError("a blocking class needs its blocker")
        if "inventory_unreliable" in held and (
            counts.confirmed
            or counts.observed
            or counts.pending_clean
            or counts.pending_uncertain
            or counts.drift_missing
        ):
            raise ValueError("an unreliable listing leaves no other non-conflicting class")

    def _quota(self) -> None:
        added = self.quota_added
        if (added.plans, added.operations, added.files) != (1, 1, self.file_count):
            raise ValueError("an attempt adds one plan, one operation and the manifest's files")
        if added.payload_bytes < PLAN_ALLOWANCE_BYTES:
            raise ValueError("an attempt adds at least the per-plan allowance")

    def _plan_and_related(self) -> None:
        if (self.plan_id is None) != (self.plan_digest is None):
            raise ValueError("plan identity and digest must be paired")
        if self.plan_id is not None and not self.eligible:
            raise ValueError("a plan exists only without blockers")
        waiting = {"source_superseded", "source_active"} & set(self.blockers)
        if self.related_operation_id is not None and not waiting:
            raise ValueError("a related operation needs a descendant blocker")
        if "source_superseded" in self.blockers and self.related_operation_id is None:
            raise ValueError("a superseded source names its successor")
        if self.related_operation_id == self.source_operation_id:
            raise ValueError("a source is not its own successor")


def _observation_of(
    manifest: DatasetManifest, classification: Classification, blockers: Sequence[Blocker]
) -> ResumeObservation:
    """What a classification of exactly this manifest established (it carries every blocker)."""
    if blockers:
        raise ValueError("a classification already carries every blocker")
    if classification.manifest_digest != manifest.digest:
        raise ValueError("the classification belongs to another manifest")
    if len(classification.classes) != len(manifest.files):
        raise ValueError("the classification does not cover the manifest")
    counts = ResumeClassCounts(**{name: classification.count(name) for name in FILE_CLASSES})
    sending = [i for i, name in enumerate(classification.classes) if name in SEND_CLASSES]
    return ResumeObservation(
        class_counts=counts,
        send_files=len(sending),
        send_bytes=sum(manifest.files[i].size for i in sending),
        unconfirmed_ack_required=bool(counts.pending_uncertain),
        classification_digest=classification.classification_digest,
        inventory_digest=classification.inventory_digest,
        examples=tuple(
            ResumeExamples(
                file_class=name,
                # A manifest lists its paths in UTF-8 byte order, so these already are.
                paths=tuple(
                    manifest.files[i].path for i in classification.indices(name)[:MAX_EXAMPLES]
                ),
            )
            for name in PROBLEM_CLASSES
            if classification.count(name)
        ),
    )


def resume_report(
    *,
    source_operation_id: str,
    dataset_id: str | None,
    manifest: DatasetManifest,
    classification: Classification | None,
    blockers: Sequence[Blocker] = (),
    related_operation_id: str | None = None,
    quota_used: QuotaCounters,
    added_payload_bytes: int,
    observed_at: str,
    plan: DatasetContinuationPlanV3 | None = None,
) -> DatasetUploadResumeReport:
    """The report of one observation, or of none; every derived field comes from the evidence.

    ``classification`` already carries every blocker (source and caller ones merged with
    ``with_blockers``); without one, ``blockers`` are the source-level reasons nothing was observed.
    A ``plan`` is the continuation prepared from exactly this observation.
    """
    if (
        type(manifest) is not DatasetManifest
        or (classification is not None and type(classification) is not Classification)
        or type(blockers) not in (tuple, list)
    ):
        raise ValueError("a manifest, a classification or none, and listed blockers are required")
    count = len(manifest.files)
    observation: ResumeObservation | None = None
    if classification is None:
        merged = tuple(blockers)
    else:
        observation = _observation_of(manifest, classification, blockers)
        merged = classification.blockers
    if plan is not None and (
        type(plan) is not DatasetContinuationPlanV3
        or classification is None
        or manifest_reference(manifest) != plan.manifest
        or plan.continuation.source_operation_id != source_operation_id
        or plan.continuation.dataset_id != dataset_id
        or plan.continuation.observed_at != observed_at
        or not binding_matches(plan.continuation, classification)
    ):
        raise ValueError("the plan was not prepared from this observation")
    return DatasetUploadResumeReport(
        schema_version=1,
        kind="dataset_upload_resume_report",
        source_operation_id=source_operation_id,
        dataset_id=dataset_id,
        eligible=not merged,
        blockers=merged,
        recommended_action=recommended_action(merged),
        related_operation_id=related_operation_id,
        file_count=count,
        observation=observation,
        quota_used=quota_used,
        quota_added=QuotaCounters(
            plans=1, operations=1, files=count, payload_bytes=added_payload_bytes
        ),
        observed_at=observed_at,
        plan_id=plan.plan_id if plan is not None else None,
        plan_digest=plan.digest if plan is not None else None,
    )
