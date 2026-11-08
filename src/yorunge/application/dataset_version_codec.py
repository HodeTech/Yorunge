"""Strict codecs for the provider's dataset-version answers (ADR-0033), with no network.

Three answers are consumed: a page of versions, one version, and its four split counts. Each is
parsed strictly (bounded JSON, no duplicate key, no non-finite number), scanned for the selected
key in EVERY string and key (including the fields that are then dropped), checked field by field
(``bool`` is not an ``int``, identifiers are canonical UUIDs, a tag is the closed set) and reduced
to the types of ``domain.dataset_version``. Anything else is ``invalid_response``. A description,
an author, a URL, a colour or a shortcut never leaves this module; a class name is only hashed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import Final

from yorunge.application.response_json import literal_secret_match, parse_json
from yorunge.domain.capabilities import timestamp
from yorunge.domain.credentials import SecretValue
from yorunge.domain.dataset_upload import provider_uuid
from yorunge.domain.dataset_version import (
    MAX_COUNT,
    MAX_LIST_ITEMS,
    DatasetVersionList,
    DatasetVersionListItem,
    DatasetVersionObservation,
    SplitCounts,
    class_labels_sha256,
    validate_version_tag,
)
from yorunge.domain.errors import YorungeError

_PROVIDER_TIME = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))?(Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)",
    re.ASCII,
)
_SPLITS: Final = ("train", "val", "test", "unassigned")
_ROW_FIELDS: Final = (
    "id",
    "version_tag",
    "is_frozen",
    "is_partial",
    "is_export_ready",
    "item_count",
    "split_config",
    "annotated_item_count",
    "total_annotation_count",
    "created_at",
)


def _invalid() -> YorungeError:
    return YorungeError("invalid_response")


@dataclass(frozen=True, slots=True)
class VersionDetail:
    """One version as its detail route shows it (the split route still has to agree)."""

    dataset_id: str
    version_id: str
    version_tag: str
    is_frozen: bool
    is_partial: bool
    is_export_ready: bool
    item_count: int
    split_config: SplitCounts
    annotated_item_count: int
    total_annotation_count: int
    class_count: int
    class_labels_sha256: str
    created_at: str


# --- the document --------------------------------------------------------------------------------


def _scan(value: object, secret: SecretValue) -> None:
    """The selected key is in no string or key of the answer, wherever in it, used or dropped."""
    if type(secret) is not SecretValue:
        raise YorungeError("invalid_request")
    captured = secret.reveal()
    pending: list[object] = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            if literal_secret_match(item, captured):
                raise _invalid()
        elif isinstance(item, dict):
            for key, child in item.items():
                if literal_secret_match(key, captured):
                    raise _invalid()
                pending.append(child)
        elif isinstance(item, list):
            pending.extend(item)


def _envelope(data: bytes, secret: SecretValue) -> dict[str, object]:
    document = parse_json(data)
    _scan(document, secret)
    if not isinstance(document, dict) or document.get("success") is not True:
        raise _invalid()
    return document


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _invalid()
    return value


def _field(source: dict[str, object], name: str) -> object:
    if name not in source:
        raise _invalid()
    return source[name]


def _count(value: object) -> int:
    if type(value) is not int or not 0 <= value <= MAX_COUNT:
        raise _invalid()
    return value


def _flag(value: object) -> bool:
    if type(value) is not bool:
        raise _invalid()
    return value


def _identifier(value: object) -> str:
    if type(value) is not str:
        raise _invalid()
    try:
        return provider_uuid(value)
    except ValueError:
        raise _invalid() from None


def _tag(value: object) -> str:
    try:
        return validate_version_tag(value)
    except ValueError:
        raise _invalid() from None


def provider_time(value: object) -> str:
    """A provider timestamp (ISO 8601 with a zone) as the canonical six-digit UTC form.

    Digits past the microsecond are dropped, so that the same provider state always gives the same
    canonical time (and the same binding digest). A time without a zone is not a time.
    """
    if type(value) is not str:
        raise _invalid()
    match = _PROVIDER_TIME.fullmatch(value)
    if match is None:
        raise _invalid()
    year, month, day, hour, minute, second, fraction, zone = match.groups()
    micro = int((fraction or "0").ljust(6, "0")[:6])
    sign = -1 if zone.startswith("-") else 1
    try:
        offset = (
            timedelta()
            if zone == "Z"
            else sign * timedelta(hours=int(zone[1:3]), minutes=int(zone[4:6]))
        )
        local = datetime(
            int(year),
            int(month),
            int(day),
            int(hour),
            int(minute),
            int(second),
            micro,
            tzinfo=timezone(offset),
        )
        return timestamp(local.astimezone(UTC))
    except (ValueError, OverflowError):
        raise _invalid() from None


def _splits(value: object) -> SplitCounts:
    source = _object(value)
    return SplitCounts(**{name: _count(_field(source, name)) for name in _SPLITS})


# --- the list -------------------------------------------------------------------------------------


def version_page(
    data: bytes, *, dataset_id: str, page: int, secret: SecretValue, observed_at: str
) -> DatasetVersionList:
    """One page of the list, for the dataset and the page that were asked for.

    A page past the last one is an honest, empty page (the provider answers it with 200 and no
    rows); only a page that shows rows has to be covered by the total.
    """
    document = _envelope(data, secret)
    rows, meta = _field(document, "data"), _object(_field(document, "meta"))
    if not isinstance(rows, list) or len(rows) > MAX_LIST_ITEMS:
        raise _invalid()
    size, total = _count(_field(meta, "page_size")), _count(_field(meta, "total"))
    shown, more = _count(_field(meta, "page")), _flag(_field(meta, "has_next"))
    if (
        shown != page
        or not 1 <= size <= MAX_LIST_ITEMS
        or len(rows) > size
        or (total < (page - 1) * size + len(rows) if rows else (page - 1) * size < total)
        or more != (page * size < total)
    ):
        raise _invalid()
    items = tuple(_list_item(row, dataset_id, observed_at) for row in rows)
    try:
        return DatasetVersionList(
            schema_version=1,
            kind="dataset_version_list",
            dataset_id=dataset_id,
            page=shown,
            page_size=size,
            total=total,
            has_next=more,
            items=items,
            observed_at=observed_at,
        )
    except ValueError:
        raise _invalid() from None  # e.g. a repeated identifier or tag: not distinct versions


def _list_item(row: object, dataset_id: str, observed_at: str) -> DatasetVersionListItem:
    source = _object(row)
    values = {name: _field(source, name) for name in _ROW_FIELDS}
    splits = _splits(values["split_config"])
    items = _count(values["item_count"])
    try:
        return DatasetVersionListItem(
            schema_version=1,
            kind="dataset_version_list_item",
            dataset_id=dataset_id,
            version_id=_identifier(values["id"]),
            version_tag=_tag(values["version_tag"]),
            is_frozen=_flag(values["is_frozen"]),
            is_partial=_flag(values["is_partial"]),
            is_export_ready=_flag(values["is_export_ready"]),
            item_count=items,
            split_counts=splits,
            split_total_matches_item_count=items == splits.total,
            annotated_item_count=_count(values["annotated_item_count"]),
            total_annotation_count=_count(values["total_annotation_count"]),
            created_at=provider_time(values["created_at"]),
            observed_at=observed_at,
        )
    except ValueError:
        raise _invalid() from None


# --- one version ----------------------------------------------------------------------------------


def version_detail(
    data: bytes, *, dataset_id: str, version_tag: str, secret: SecretValue
) -> VersionDetail:
    """The detail of the version that was asked for (this dataset, this tag), or not an answer."""
    source = _object(_field(_envelope(data, secret), "data"))
    if _identifier(_field(source, "dataset_id")) != dataset_id:
        raise _invalid()
    if _tag(_field(source, "version_tag")) != version_tag:
        raise _invalid()
    values = {name: _field(source, name) for name in _ROW_FIELDS}
    labels = _field(source, "class_labels_snapshot")
    if not isinstance(labels, list):
        raise _invalid()
    projected = []
    for label in labels:
        row = _object(label)
        projected.append({name: _field(row, name) for name in _label_fields()})
    try:
        return VersionDetail(
            dataset_id=dataset_id,
            version_id=_identifier(values["id"]),
            version_tag=version_tag,
            is_frozen=_flag(values["is_frozen"]),
            is_partial=_flag(values["is_partial"]),
            is_export_ready=_flag(values["is_export_ready"]),
            item_count=_count(values["item_count"]),
            split_config=_splits(values["split_config"]),
            annotated_item_count=_count(values["annotated_item_count"]),
            total_annotation_count=_count(values["total_annotation_count"]),
            class_count=len(projected),
            class_labels_sha256=class_labels_sha256(projected),
            created_at=provider_time(values["created_at"]),
        )
    except ValueError:
        raise _invalid() from None


def _label_fields() -> tuple[str, ...]:
    return ("annotation_count", "id", "name", "sort_order")


def version_splits(data: bytes, *, secret: SecretValue) -> SplitCounts:
    """The four split counts of the split route."""
    try:
        return _splits(_field(_envelope(data, secret), "data"))
    except ValueError:
        raise _invalid() from None


def observation(
    detail: VersionDetail, splits: SplitCounts, *, observed_at: str
) -> DatasetVersionObservation:
    """The two reads together: they must say the same four numbers, or the state moved between."""
    if detail.split_config != splits:
        raise _invalid()
    try:
        return DatasetVersionObservation(
            schema_version=1,
            kind="dataset_version_observation",
            dataset_id=detail.dataset_id,
            version_id=detail.version_id,
            version_tag=detail.version_tag,
            is_frozen=detail.is_frozen,
            is_partial=detail.is_partial,
            is_export_ready=detail.is_export_ready,
            item_count=detail.item_count,
            split_counts=splits,
            split_total_matches_item_count=detail.item_count == splits.total,
            annotated_item_count=detail.annotated_item_count,
            total_annotation_count=detail.total_annotation_count,
            class_count=detail.class_count,
            class_labels_sha256=detail.class_labels_sha256,
            created_at=detail.created_at,
            observed_at=observed_at,
        )
    except ValueError:
        raise _invalid() from None
