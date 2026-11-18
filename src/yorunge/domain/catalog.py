"""The catalog contract: consumed shapes, page and completeness rules, addresses (ADR-0035).

Pure: no I/O, clock or secrets. What is here decides what a catalog answer *means* before any code
shows it: which fields the reader consumes, how a page is judged complete, which name can be used
to address a model and which exact version a tag selects. ``docs/reference/catalog.md`` is the
canonical description; this module enforces it.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from typing import Final, Literal, Protocol

from pydantic import Field

from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Model, has_control_characters

# --- limits (ADR-0035 Karar 2) --------------------------------------------------------------------

PLATFORM_DEFAULT_PAGE_SIZE: Final = 20  # the client default the upload path already uses
PLATFORM_MAX_PAGE_SIZE: Final = 100  # provisional until the live reading (K4) confirms it
LLM_MAX_RECORDS: Final = 500
MAX_VERSION_ROWS: Final = (
    500  # a version list has no paging; its size is bounded by the same byte budget
)
MAX_CANDIDATES: Final = 5
NAME_LIMIT: Final = 128  # display characters for names and slugs
TEXT_LIMIT: Final = 512  # display characters for descriptions
VERSION_TAG_LIMIT: Final = 128
ELLIPSIS: Final = "…"

Completeness = Literal["complete", "partial", "last_page", "unknown"]

_SEGMENT: Final = re.compile(r"\A[A-Za-z0-9._-]{1,128}\Z")
_DIGITS: Final = re.compile(r"\A[0-9]{1,18}\Z")
# Bidirectional controls and the other format characters a terminal may act on.
_FORMAT_CATEGORIES: Final = frozenset({"Cc", "Cf"})


class VersionRef(Protocol):
    """What version resolution reads: the identity, the tag and the creation time."""

    version_id: str
    version_tag: str
    created_at: str


# --- addresses ------------------------------------------------------------------------------------


def segment(value: str) -> str:
    """An address segment (owner, slug, model id, version id): one allowed alphabet, no dots-only.

    Refused before any request; the value is never sent with a character that could change the path.
    """
    if type(value) is not str or _SEGMENT.fullmatch(value) is None or value in (".", ".."):
        raise YorungeError("invalid_request")
    return value


def version_tag(value: str) -> str:
    """A tag is compared on the client and never placed in a URL: length and controls only."""
    if (
        type(value) is not str
        or not 1 <= len(value) <= VERSION_TAG_LIMIT
        or has_control_characters(value)
    ):
        raise YorungeError("invalid_request")
    return value


def owner_address(owner_username: str | None) -> str:
    """A model without a stored owner name cannot be addressed as ``owner/slug`` (Karar 5)."""
    if owner_username is None:
        raise YorungeError("model_not_addressable")
    return segment(owner_username)


def require_address(owner: str, slug: str) -> tuple[str, str]:
    """Both segments of an ``owner/slug`` argument, validated before a request."""
    return segment(owner), segment(slug)


# --- pages ----------------------------------------------------------------------------------------


def page_arguments(page: int, page_size: int) -> None:
    """Request arguments are integers in range; the request never carries anything else."""
    if (
        type(page) is not int
        or type(page_size) is not int
        or page < 1
        or not 1 <= page_size <= PLATFORM_MAX_PAGE_SIZE
    ):
        raise YorungeError("invalid_request")


def expected_rows(page: int, page_size: int, total: int) -> int:
    """The number of records page ``page`` must hold if the server kept the asked page size."""
    return max(0, min(page_size, total - (page - 1) * page_size))


def has_next(page: int, page_size: int, total: int) -> bool:
    return page * page_size < total


def _label(page: int, more: bool) -> Completeness:
    if more:
        return "partial"
    return "complete" if page == 1 else "last_page"


def platform_page(page: int, page_size: int, total: object, returned: int) -> Completeness:
    """A Platform model page is judged by its total and by the rows it actually holds (Karar 2)."""
    if type(total) is not int or total < 0:
        raise YorungeError("invalid_response")
    if returned != expected_rows(page, page_size, total):
        # A server that quietly returns another page size is not a page we can trust.
        raise YorungeError("invalid_response")
    return _label(page, has_next(page, page_size, total))


def dataset_page(
    page: int,
    page_size: int,
    returned: int,
    has_next_header: str | None,
    total_header: str | None,
) -> Completeness:
    """Dataset pages carry their paging in headers; a missing or unclear header is ``unknown``."""
    if has_next_header not in ("true", "false"):
        return "unknown"
    more = has_next_header == "true"
    if total_header is not None and _DIGITS.fullmatch(total_header) is not None:
        total = int(total_header)
        if returned != expected_rows(page, page_size, total):
            raise YorungeError("invalid_response")
        if more != has_next(page, page_size, total):
            raise YorungeError("invalid_response")
    return _label(page, more)


def versions_listing(versions_count: int, listed: int) -> Completeness:
    """A version list has no paging: complete only when its rows equal the detail count."""
    return "complete" if listed == versions_count else "unknown"


def checked_versions(versions_count: int, listed: int) -> None:
    """Resolution refuses a version list that disagrees with the detail it was read with."""
    if listed != versions_count:
        raise YorungeError("invalid_response")


def detail_identity(owner_username: str | None, slug: str, owner: str, asked_slug: str) -> None:
    """The detail answer must be the model the address named; anything else is not that model."""
    if owner_username != owner or slug != asked_slug:
        raise YorungeError("invalid_response")


# --- resolution -----------------------------------------------------------------------------------


def resolve_version(versions: Sequence[VersionRef], tag: str) -> VersionRef:
    """Exactly one version carries the tag; none is not-visible, more than one is ambiguous."""
    version_tag(tag)
    matches = [item for item in versions if item.version_tag == tag]
    if not matches:
        raise YorungeError("model_not_visible")
    if len(matches) > 1:
        raise YorungeError("model_ambiguous")
    return matches[0]


def candidates(versions: Sequence[VersionRef], tag: str) -> tuple[VersionRef, ...]:
    """The few candidates an ambiguity shows: enough to choose by identity, never a pick."""
    return tuple(item for item in versions if item.version_tag == tag)[:MAX_CANDIDATES]


def task_matches(expected: str, observed: str) -> None:
    """An expected LLM task must equal the observed one; unknown task names are not refused here."""
    if expected != observed:
        raise YorungeError("model_task_mismatch")


# --- display --------------------------------------------------------------------------------------


def text(value: str | None, limit: int) -> str | None:
    """Untrusted provider text as it may be shown: no format or control characters, bounded length.

    Line breaks and tabs become spaces; every other control and bidirectional override is dropped.
    A cut text ends with an ellipsis so that it is never silently shortened.
    """
    if value is None:
        return None
    if type(value) is not str or type(limit) is not int or limit < 2:
        raise YorungeError("invalid_response")
    pieces: list[str] = []
    for char in value:
        if char in "\t\n\r":
            pieces.append(" ")
        elif unicodedata.category(char) in _FORMAT_CATEGORIES:
            continue
        else:
            pieces.append(char)
    cleaned = "".join(pieces).strip()
    if len(cleaned) > limit:
        return cleaned[: limit - 1] + ELLIPSIS
    return cleaned


# --- consumed records (ADR-0035 Karar 8) ----------------------------------------------------------


class _Consumed(Model):
    """Closed records: only the fields the reader consumes exist; everything else was dropped."""


class LlmPricing(_Consumed):
    prompt_token_price: int | float
    completion_token_price: int | float
    currency: str | None
    free_until: str | None


class LlmModel(_Consumed):
    model_id: str = Field(min_length=1, max_length=256)
    task: str = Field(min_length=1, max_length=64)
    created: int
    modalities: tuple[str, ...] | None = None
    context_length: int | None = None
    default_max_output_tokens: int | None = None
    precision: str | None = None
    pricing: LlmPricing | None = None


class LlmListing(_Consumed):
    models: tuple[LlmModel, ...] = Field(max_length=LLM_MAX_RECORDS)
    completeness: Literal["unknown"] = "unknown"


class PlatformModel(_Consumed):
    model_id: str
    owner_username: str | None
    slug: str
    name: str
    description: str | None
    license: str | None
    modality: str
    stage: str
    visibility: str
    versions_count: int
    architecture: str | None
    created_at: str
    updated_at: str


class PlatformModelPage(_Consumed):
    page: int
    page_size: int
    total: int
    returned: int
    completeness: Completeness
    models: tuple[PlatformModel, ...]


class PlatformVersion(_Consumed):
    version_id: str
    version_tag: str
    framework: str | None
    file_size_bytes: int | None
    created_at: str
    has_weights: bool
    has_onnx: bool
    has_tflite: bool


class VersionListing(_Consumed):
    versions: tuple[PlatformVersion, ...]
    completeness: Completeness


class PlatformDataset(_Consumed):
    dataset_id: str
    name: str
    slug: str
    modality: str
    item_count: int
    visibility: str
    updated_at: str
    owner_username: str | None


class DatasetPage(_Consumed):
    page: int
    page_size: int
    returned: int
    completeness: Completeness
    scope: Literal["unknown"] = "unknown"  # the filter's effect is unproven until K4 (Karar 2)
    datasets: tuple[PlatformDataset, ...]
