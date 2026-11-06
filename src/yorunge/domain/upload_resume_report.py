"""The read-only resume report: what an interrupted upload still needs and why it is blocked.

The report carries counts, closed blocker names, digests and a few relative example paths of
problematic files. It never carries owner, name, created-dataset or receipt content, keys, URLs or
the paths of extra remote items. Report mode answers with it whatever the classification is;
preparing a plan is a separate step that happens only without blockers.
"""

from __future__ import annotations

from typing import Annotated, ClassVar, Literal, Self

from pydantic import Field, field_validator, model_validator

from yorunge.domain.capabilities import instant
from yorunge.domain.dataset_manifest import Sha256, file_parts
from yorunge.domain.dataset_upload import (
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_FILES,
    UploadWire,
    provider_uuid,
)
from yorunge.domain.state import canonical_uuid
from yorunge.domain.upload_resume import BLOCKERS, Action, Blocker, recommended_action

# Classes a user has to act on; their relative paths may be listed (never more than a handful).
PROBLEM_CLASSES = ("pending_uncertain", "drift_missing", "conflict", "inventory_unreliable")
MAX_EXAMPLES = 8
MAX_QUOTA_PAYLOAD_BYTES = 16 * 1024 * 1024
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
    file_class: Literal["pending_uncertain", "drift_missing", "conflict", "inventory_unreliable"]
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


class DatasetUploadResumeReport(UploadWire):
    max_wire_bytes: ClassVar[int] = 64 * 1024
    schema_version: Literal[1]
    kind: Literal["dataset_upload_resume_report"]
    source_operation_id: str
    dataset_id: str | None
    eligible: bool
    blockers: tuple[Blocker, ...]
    class_counts: ResumeClassCounts
    file_count: Annotated[int, Field(ge=1, le=MAX_UPLOAD_FILES)]
    send_files: Count
    send_bytes: Annotated[int, Field(ge=0, le=MAX_UPLOAD_BYTES)]
    unconfirmed_ack_required: bool
    recommended_action: Action
    related_operation_id: str | None
    quota_files: Annotated[int, Field(ge=1, le=MAX_UPLOAD_FILES)]
    quota_payload_bytes: Annotated[int, Field(ge=0, le=MAX_QUOTA_PAYLOAD_BYTES)]
    classification_digest: Sha256
    inventory_digest: Sha256
    observed_at: str
    plan_id: str | None
    plan_digest: Sha256 | None
    examples: Annotated[tuple[ResumeExamples, ...], Field(max_length=len(PROBLEM_CLASSES))]

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
        self._counts()
        self._plan_and_related()
        self._examples()
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
        counts = self.class_counts
        for name in ("drift_missing", "conflict", "inventory_unreliable"):
            if getattr(counts, name) and name not in self.blockers:
                raise ValueError("a blocking class needs its blocker")

    def _counts(self) -> None:
        counts = self.class_counts
        if counts.total() != self.file_count or self.quota_files != self.file_count:
            raise ValueError("class counts must cover the manifest")
        if self.send_files != counts.pending_clean + counts.pending_uncertain:
            raise ValueError("files to send are the unsent and unconfirmed ones")
        if self.unconfirmed_ack_required != bool(counts.pending_uncertain):
            raise ValueError("acknowledgement is needed exactly for unconfirmed files")
        if not self.send_files and self.send_bytes:
            raise ValueError("no files to send, no bytes to send")

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

    def _examples(self) -> None:
        classes = [example.file_class for example in self.examples]
        if classes != [name for name in PROBLEM_CLASSES if name in classes]:
            raise ValueError("ordered distinct example classes required")
        for example in self.examples:
            if len(example.paths) > getattr(self.class_counts, example.file_class):
                raise ValueError("examples cannot outnumber their class")
