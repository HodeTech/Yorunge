"""Remote dataset versions and the immutable reference to one (ADR-0033).

``docs/reference/dataset-versions.md``. Pure: no I/O, clock or randomness. A version is observed as
facts (counts, flags, a digest of its class labels), a frozen one can be bound into a closed,
canonical, self-digested record, and a bound record can be compared with a later observation. A
class name, a description, an author or a URL never enters any of these types: names are only
hashed.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Annotated, Final, Literal, Self

from pydantic import Field, field_validator, model_validator

from yorunge.domain.capabilities import JsonWireModel, instant
from yorunge.domain.credentials import ServiceTarget, normalize_target
from yorunge.domain.dataset_manifest import canonical_manifest
from yorunge.domain.dataset_upload import provider_uuid
from yorunge.domain.errors import (
    VERSION_ANNOTATION_FIELDS,
    VERSION_IDENTITY_FIELDS,
    DatasetVersionChanged,
    YorungeError,
)
from yorunge.domain.models import Model, is_reportable_path

MAX_COUNT: Final = 2**63 - 1
Absent = Literal["dataset_version_not_found", "dataset_version_missing"]
MAX_BINDING_BYTES: Final = 16 * 1024
MIN_PAGE: Final = 1
MAX_PAGE: Final = 10_000
MAX_LIST_ITEMS: Final = 100
MAX_CLASS_LABELS: Final = 4096

Count = Annotated[int, Field(ge=0, le=MAX_COUNT)]
Sha256 = Annotated[str, Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")]

_TAG = re.compile(r"[A-Za-z0-9._-]{1,128}", re.ASCII)
_SHA256 = re.compile(r"[a-f0-9]{64}", re.ASCII)


def validate_version_tag(value: object) -> str:
    """One path component of 1-128 characters of ``[A-Za-z0-9._-]``; ``.`` and ``..`` never."""
    if type(value) is not str or value in (".", "..") or _TAG.fullmatch(value) is None:
        raise ValueError("a version tag is 1-128 characters of [A-Za-z0-9._-], not . or ..")
    return value


def _canonical_time(value: str) -> str:
    instant(value)
    return value


class SplitCounts(Model):
    train: Count
    val: Count
    test: Count
    unassigned: Count

    @property
    def total(self) -> int:
        return self.train + self.val + self.test + self.unassigned


class _VersionFacts(Model):
    """What a version list and a version detail both say; never a class name, text or URL."""

    schema_version: Literal[1]
    dataset_id: str
    version_id: str
    version_tag: str
    is_frozen: bool
    is_partial: bool
    is_export_ready: bool
    item_count: Count
    split_counts: SplitCounts
    split_total_matches_item_count: bool
    annotated_item_count: Count
    total_annotation_count: Count
    created_at: str
    observed_at: str

    @field_validator("dataset_id", "version_id")
    @classmethod
    def canonical_identifier(cls, value: str) -> str:
        return provider_uuid(value)

    @field_validator("version_tag")
    @classmethod
    def closed_tag(cls, value: str) -> str:
        return validate_version_tag(value)

    @field_validator("created_at", "observed_at")
    @classmethod
    def canonical_instant(cls, value: str) -> str:
        return _canonical_time(value)

    @model_validator(mode="after")
    def honest_total(self) -> Self:
        if self.split_total_matches_item_count != (self.item_count == self.split_counts.total):
            raise ValueError("the split total flag says what the counts say")
        return self


class DatasetVersionListItem(_VersionFacts):
    """A version as a list shows it: without class labels (the list carries none)."""

    kind: Literal["dataset_version_list_item"]


class DatasetVersionObservation(_VersionFacts):
    """One version, observed: the facts of the list and the digest of its class labels."""

    kind: Literal["dataset_version_observation"]
    class_count: Count
    class_labels_sha256: Sha256


def page_rows(page: int, page_size: int, total: int) -> int:
    """How many rows page ``page`` of ``total`` rows holds: all of its slice, none past the last.

    A page that shows fewer rows than the total says it covers would hide versions without a word
    (the next page starts where this one should have ended), and one that shows more has rows the
    total does not count: neither is a page of this list.
    """
    return max(0, min(page_size, total - (page - 1) * page_size))


class DatasetVersionList(Model):
    """One page of a dataset's versions; completeness is never claimed."""

    schema_version: Literal[1]
    kind: Literal["dataset_version_list"]
    dataset_id: str
    page: Annotated[int, Field(ge=MIN_PAGE, le=MAX_PAGE)]
    page_size: Annotated[int, Field(ge=1, le=MAX_LIST_ITEMS)]
    total: Count
    has_next: bool
    items: Annotated[tuple[DatasetVersionListItem, ...], Field(max_length=MAX_LIST_ITEMS)]
    observed_at: str

    @field_validator("dataset_id")
    @classmethod
    def canonical_identifier(cls, value: str) -> str:
        return provider_uuid(value)

    @field_validator("observed_at")
    @classmethod
    def canonical_instant(cls, value: str) -> str:
        return _canonical_time(value)

    @model_validator(mode="after")
    def honest_page(self) -> Self:
        if self.has_next != (self.page * self.page_size < self.total):
            raise ValueError(
                "a next page exists exactly when the pages so far fall short of the total"
            )
        if len(self.items) != page_rows(self.page, self.page_size, self.total):
            raise ValueError("a page shows every row it covers: neither fewer nor more")
        if any(item.dataset_id != self.dataset_id for item in self.items):
            raise ValueError("the rows are the dataset's own")
        if len({item.version_id for item in self.items}) != len(self.items) or len(
            {item.version_tag for item in self.items}
        ) != len(self.items):
            raise ValueError("a page of distinct versions")
        return self


class LocalManifestRelation(Model):
    """The local Manifest v1 the binding was made against, and how its file count relates."""

    digest: Sha256
    file_count: Count
    relation: Literal["count_matches", "count_differs"]


class DatasetVersionCheck(Model):
    """The only success of ``check``: the binding still names what the provider shows."""

    schema_version: Literal[1]
    kind: Literal["dataset_version_check"]
    result: Literal["unchanged"]
    dataset_id: str
    version_id: str
    version_tag: str
    binding_digest: Sha256
    observed_at: str

    @field_validator("dataset_id", "version_id")
    @classmethod
    def canonical_identifier(cls, value: str) -> str:
        return provider_uuid(value)

    @field_validator("version_tag")
    @classmethod
    def closed_tag(cls, value: str) -> str:
        return validate_version_tag(value)

    @field_validator("observed_at")
    @classmethod
    def canonical_instant(cls, value: str) -> str:
        return _canonical_time(value)


class DatasetVersionBound(Model):
    """What ``bind`` reports of the binding it wrote: its digest and where it is, not the file."""

    schema_version: Literal[1]
    kind: Literal["dataset_version_bound"]
    dataset_id: str
    version_id: str
    version_tag: str
    binding_digest: Sha256
    binding_path: Annotated[str, Field(min_length=1, max_length=4096)]
    local_manifest: LocalManifestRelation | None
    split_total_matches_item_count: bool
    is_partial: bool
    observed_at: str

    @field_validator("dataset_id", "version_id")
    @classmethod
    def canonical_identifier(cls, value: str) -> str:
        return provider_uuid(value)

    @field_validator("version_tag")
    @classmethod
    def closed_tag(cls, value: str) -> str:
        return validate_version_tag(value)

    @field_validator("observed_at")
    @classmethod
    def canonical_instant(cls, value: str) -> str:
        return _canonical_time(value)

    @field_validator("binding_path")
    @classmethod
    def printable_path(cls, value: str) -> str:
        if not is_reportable_path(value):
            raise ValueError("a bounded printable path is required")
        return value


class DatasetVersionBinding(JsonWireModel):
    """The immutable reference to one frozen version (ADR-0033 §2): closed, canonical, digested.

    The digest covers every field except ``digest`` and ``observed_at`` and is the SHA-256 of the
    Manifest v1 encoder's bytes: observing the same provider state again, against the same local
    manifest, gives the same digest. It is a checksum of itself, not a signature.
    """

    schema_version: Literal[1]
    policy_version: Literal[1]
    kind: Literal["dataset_version_binding"]
    service: ServiceTarget
    dataset_id: str
    version_id: str
    version_tag: str
    created_at: str
    is_frozen: Literal[True]
    is_partial: bool
    item_count: Count
    split_counts: SplitCounts
    split_total_matches_item_count: bool
    annotated_item_count: Count
    total_annotation_count: Count
    class_count: Count
    class_labels_sha256: Sha256
    local_manifest: LocalManifestRelation | None
    observed_at: str
    digest: Sha256

    @field_validator("policy_version", mode="before")
    @classmethod
    def integer_policy(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("integer policy version required")
        return value

    @field_validator("service")
    @classmethod
    def canonical_service(cls, value: ServiceTarget) -> ServiceTarget:
        """The target as ``normalize_target`` writes it (it is compared by equality)."""
        try:
            canonical = normalize_target(value.service_origin + value.api_base_path)
        except YorungeError:
            raise ValueError("a canonical service target is required") from None
        if canonical != value:
            raise ValueError("a canonical service target is required")
        return value

    @field_validator("dataset_id", "version_id")
    @classmethod
    def canonical_identifier(cls, value: str) -> str:
        return provider_uuid(value)

    @field_validator("version_tag")
    @classmethod
    def closed_tag(cls, value: str) -> str:
        return validate_version_tag(value)

    @field_validator("created_at", "observed_at")
    @classmethod
    def canonical_instant(cls, value: str) -> str:
        return _canonical_time(value)

    @model_validator(mode="after")
    def integrity(self) -> Self:
        if self.split_total_matches_item_count != (self.item_count == self.split_counts.total):
            raise ValueError("the split total flag says what the counts say")
        if self.local_manifest is not None:
            matches = self.local_manifest.file_count == self.item_count
            if self.local_manifest.relation != ("count_matches" if matches else "count_differs"):
                raise ValueError("the manifest relation says what the counts say")
        if self.digest != self.computed_digest():
            raise ValueError("binding digest mismatch")
        return self

    def computed_digest(self) -> str:
        body = self.model_dump(mode="json", exclude={"digest", "observed_at"})
        return hashlib.sha256(canonical_manifest(body)).hexdigest()

    def encoded(self) -> bytes:
        """The artifact: the same encoding, with the digest and ``observed_at``, and one LF."""
        content = canonical_manifest(self.model_dump(mode="json")) + b"\n"
        if len(content) > MAX_BINDING_BYTES:
            raise ValueError("binding byte limit exceeded")
        return content

    def check(
        self, observation: DatasetVersionObservation, *, active: ServiceTarget
    ) -> DatasetVersionCheck:
        """``unchanged`` if the observation differs in nothing the binding holds, else the error.

        ``active`` is the provider the active profile targets: a binding for another provider is
        ``state_changed`` before any field is compared. The observation must be of this dataset
        (``dataset_id`` is not a compared field: another dataset is not a change of this version but
        a caller's mistake); it is stamped with its own ``observed_at``.
        """
        if type(observation) is not DatasetVersionObservation:
            raise YorungeError("invalid_request")
        require_same_service(self, active)
        if observation.dataset_id != self.dataset_id:
            raise YorungeError("invalid_request")
        differences = changed_fields(self, observation)
        if differences:
            raise DatasetVersionChanged(differences)
        return DatasetVersionCheck(
            schema_version=1,
            kind="dataset_version_check",
            result="unchanged",
            dataset_id=self.dataset_id,
            version_id=self.version_id,
            version_tag=self.version_tag,
            binding_digest=self.digest,
            observed_at=observation.observed_at,
        )


def bound_summary(binding: DatasetVersionBinding, path: str) -> DatasetVersionBound:
    """The report of a binding that was written to ``path``."""
    return DatasetVersionBound(
        schema_version=1,
        kind="dataset_version_bound",
        dataset_id=binding.dataset_id,
        version_id=binding.version_id,
        version_tag=binding.version_tag,
        binding_digest=binding.digest,
        binding_path=path,
        local_manifest=binding.local_manifest,
        split_total_matches_item_count=binding.split_total_matches_item_count,
        is_partial=binding.is_partial,
        observed_at=binding.observed_at,
    )


def bind(
    observation: DatasetVersionObservation,
    service: ServiceTarget,
    *,
    manifest_digest: str | None = None,
    manifest_file_count: int | None = None,
) -> DatasetVersionBinding:
    """The binding of a frozen version, optionally against a local Manifest v1."""
    if type(observation) is not DatasetVersionObservation or type(service) is not ServiceTarget:
        raise YorungeError("invalid_request")
    if not observation.is_frozen:
        raise YorungeError("dataset_version_not_frozen")
    if (manifest_digest is None) != (manifest_file_count is None):
        raise YorungeError("invalid_request")
    local: LocalManifestRelation | None = None
    if manifest_digest is not None and manifest_file_count is not None:
        if (
            type(manifest_file_count) is not int
            or not 0 <= manifest_file_count <= MAX_COUNT
            or type(manifest_digest) is not str
            or _SHA256.fullmatch(manifest_digest) is None
        ):
            raise YorungeError("invalid_request")
        local = LocalManifestRelation(
            digest=manifest_digest,
            file_count=manifest_file_count,
            relation="count_matches"
            if manifest_file_count == observation.item_count
            else "count_differs",
        )
    fields = {
        "schema_version": 1,
        "policy_version": 1,
        "kind": "dataset_version_binding",
        "service": service.model_dump(mode="json"),
        "dataset_id": observation.dataset_id,
        "version_id": observation.version_id,
        "version_tag": observation.version_tag,
        "created_at": observation.created_at,
        "is_frozen": True,
        "is_partial": observation.is_partial,
        "item_count": observation.item_count,
        "split_counts": observation.split_counts.model_dump(mode="json"),
        "split_total_matches_item_count": observation.split_total_matches_item_count,
        "annotated_item_count": observation.annotated_item_count,
        "total_annotation_count": observation.total_annotation_count,
        "class_count": observation.class_count,
        "class_labels_sha256": observation.class_labels_sha256,
        "local_manifest": None if local is None else local.model_dump(mode="json"),
        "observed_at": observation.observed_at,
    }
    made: DatasetVersionBinding | None = None
    try:
        digest = hashlib.sha256(
            canonical_manifest({k: v for k, v in fields.items() if k != "observed_at"})
        ).hexdigest()
        made = DatasetVersionBinding.model_validate({**fields, "digest": digest})
    except ValueError:
        pass  # e.g. a service that is not canonical or does not encode
    if made is None:
        raise YorungeError("invalid_request")  # raised outside the handler: no cause is kept
    return made


def decode_binding(data: object) -> DatasetVersionBinding:
    """A stored binding: exactly the canonical bytes of a valid one, or ``binding_invalid``."""
    binding: DatasetVersionBinding | None = None
    try:
        if type(data) is not bytes or not 0 < len(data) <= MAX_BINDING_BYTES:
            raise ValueError("bounded binding required")
        binding = DatasetVersionBinding.model_validate_json(data)
        if binding.encoded() != data:
            raise ValueError("canonical binding required")
    except (ValueError, RecursionError):  # UnicodeError is a ValueError
        binding = None  # the parser's error holds the text of the file: none of it is kept
    if binding is None:
        raise YorungeError("binding_invalid")
    return binding


def require_same_service(binding: DatasetVersionBinding, active: ServiceTarget) -> None:
    """The binding names the provider the active profile targets; else ``state_changed``.

    Two targets are compared; anything else is the caller's mistake (``invalid_request``), never a
    changed provider.
    """
    if type(binding) is not DatasetVersionBinding or type(active) is not ServiceTarget:
        raise YorungeError("invalid_request")
    if binding.service != active:
        raise YorungeError("state_changed")


def changed_fields(
    binding: DatasetVersionBinding, observation: DatasetVersionObservation
) -> tuple[str, ...]:
    """The sorted closed names in which the observation differs from what the binding holds.

    ``observed_at``, ``is_export_ready`` (a flag that changes with export preparation and defines
    nothing about the content), the provider target and the local manifest relation are not
    compared. A version that was unfrozen is ``is_frozen``, never unchanged.
    """
    if type(binding) is not DatasetVersionBinding or type(observation) is not (
        DatasetVersionObservation
    ):
        raise YorungeError("invalid_request")
    differences = [
        name
        for name in (*VERSION_IDENTITY_FIELDS, *VERSION_ANNOTATION_FIELDS)
        if getattr(binding, name) != getattr(observation, name)
    ]
    return tuple(sorted(differences))


def _class_label_row(label: Mapping[str, object]) -> dict[str, object]:
    """One class label as a plain row, or ``invalid_response`` unless it is exactly the four fields.

    The ``id`` is an integer or a string, the ``name`` a string, the ``annotation_count`` an integer
    from 0 to ``MAX_COUNT``, the ``sort_order`` (and an integer ``id``) an integer within
    ``MAX_COUNT`` either way. The types are exact: a bool or an ``int`` subclass is none of these.
    """
    if not isinstance(label, Mapping) or set(label) != {
        "annotation_count",
        "id",
        "name",
        "sort_order",
    }:
        raise YorungeError("invalid_response")
    identifier, name = label["id"], label["name"]
    annotations, order = label["annotation_count"], label["sort_order"]
    if (
        type(identifier) not in (int, str)
        or type(name) is not str
        or type(annotations) is not int
        or not 0 <= annotations <= MAX_COUNT
        or type(order) is not int
        or not -MAX_COUNT <= order <= MAX_COUNT
        or (type(identifier) is int and not -MAX_COUNT <= identifier <= MAX_COUNT)
    ):
        raise YorungeError("invalid_response")
    return dict(label)


def class_labels_sha256(labels: Sequence[Mapping[str, object]]) -> str:
    """The digest of a version's class labels, which are never shown (ADR-0033, reference).

    The objects ``{annotation_count, id, name, sort_order}`` sorted by ``id`` (integers numerically,
    strings by their UTF-8 bytes), encoded by the Manifest v1 encoder. The ``id`` keeps the type
    the provider gave it; mixed types or a repeated ``id`` make the order ambiguous, so the
    answer is not one (``invalid_response``). At most ``MAX_CLASS_LABELS`` (4096) labels: a longer
    list is not an answer. The cap is this reader's own limit (the response size and node budgets
    alone would let about seven thousand short labels through), kept so that the work and the
    digest input stay small.
    """
    if not isinstance(labels, Sequence) or isinstance(labels, (str, bytes)):
        raise YorungeError("invalid_response")
    if len(labels) > MAX_CLASS_LABELS:
        raise YorungeError("invalid_response")
    rows = [_class_label_row(label) for label in labels]
    kinds = {type(row["id"]) for row in rows}
    if len(kinds) > 1 or len({row["id"] for row in rows}) != len(rows):
        raise YorungeError("invalid_response")
    encoded: bytes | None = None
    try:
        if kinds == {str}:
            rows.sort(key=lambda row: str(row["id"]).encode("utf-8"))
        else:
            rows.sort(key=lambda row: int(str(row["id"])))
        encoded = canonical_manifest(rows)  # a lone surrogate does not encode
    except ValueError:  # a UnicodeError is one
        encoded = None  # the encoder's error holds the class names: none of them is kept
    if encoded is None:
        raise YorungeError("invalid_response")
    return hashlib.sha256(encoded).hexdigest()
