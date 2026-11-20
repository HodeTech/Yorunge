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
from datetime import datetime
from typing import Annotated, Final, Generic, Literal, Protocol, TypeVar

from pydantic import AfterValidator, Field

from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Identifier, Model, has_control_characters

# --- limits (ADR-0035 Karar 2) --------------------------------------------------------------------

PLATFORM_DEFAULT_PAGE_SIZE: Final = 20  # the client default the upload path already uses
PLATFORM_MAX_PAGE_SIZE: Final = 100  # provisional until the live reading (K4) confirms it
LLM_MAX_RECORDS: Final = 500
MAX_VERSION_ROWS: Final = 500  # a version list has no paging; bounded by the answer budget
MAX_CANDIDATES: Final = 5
MODALITY_LIMIT: Final = 32  # an LLM record names a handful of modalities, never thousands
NAME_LIMIT: Final = 128  # display characters for names, slugs and short labels
TEXT_LIMIT: Final = 512  # display characters for descriptions
IDENTITY_LIMIT: Final = 256  # raw identifiers the provider sends; addresses are narrower
VERSION_TAG_LIMIT: Final = IDENTITY_LIMIT  # a listed tag must be selectable: the same bound
ELLIPSIS: Final = "…"

Completeness = Literal["complete", "partial", "last_page", "unknown"]

_SEGMENT: Final = re.compile(r"\A[A-Za-z0-9._-]{1,128}\Z")
_DIGITS: Final = re.compile(r"\A\d{1,18}\Z", re.ASCII)
# Bidirectional controls and the other format characters a terminal may act on.
_FORMAT_CATEGORIES: Final = frozenset({"Cc", "Cf"})
# Line and paragraph separators: some terminals and log viewers treat them as line ends.
_LINE_CATEGORIES: Final = frozenset({"Zl", "Zp"})


class VersionRef(Protocol):
    """What version resolution reads: the identity, the tag and the creation time."""

    version_id: str
    version_tag: str
    created_at: str


# --- addresses ------------------------------------------------------------------------------------


def segment(value: str) -> str:
    """An address segment (owner, slug, model id, version id) in one allowed alphabet.

    The dot segments ``.`` and ``..`` are refused: a URL reads them as navigation. ``...`` is an
    ordinary name in this alphabet. Refused before any request is made.
    """
    if type(value) is not str or _SEGMENT.fullmatch(value) is None or value in (".", ".."):
        raise YorungeError("invalid_request")
    return value


def version_tag(value: str) -> str:
    """A tag the user names: the provider's own rule (a plain identifier), within its bound.

    A tag is compared on the client and never placed in a URL. It is judged by the same rule as a
    tag the provider lists: a tag the user can type is a tag that can be listed, and a format or
    line-separator character would be a tag no listing shows as itself.
    """
    if type(value) is not str or not 1 <= len(value) <= VERSION_TAG_LIMIT:
        raise YorungeError("invalid_request")
    try:
        return plain_identifier(value)
    except ValueError:
        raise YorungeError("invalid_request") from None


def provider_segment(value: object) -> str:
    """A segment the provider named and the path now needs: a provider fault, not a user one.

    A value outside the alphabet from the answer is an invalid answer; it is never reported as a
    mistake in what the user typed.
    """
    if type(value) is not str or _SEGMENT.fullmatch(value) is None or value in (".", ".."):
        raise YorungeError("invalid_response")
    return value


def task_argument(value: object) -> str:
    """An LLM task named by the user: a plain identifier of 1 to 64 characters, checked first.

    Edge whitespace is refused, not trimmed: a trimmed task would filter for a different name.
    """
    if type(value) is not str:
        raise YorungeError("invalid_request")
    text: str = value
    if not 1 <= len(text) <= 64 or text != text.strip():
        raise YorungeError("invalid_request")
    if any(unicodedata.category(char) in _UNPLAIN_CATEGORIES for char in text):
        raise YorungeError("invalid_request")
    if has_control_characters(text):
        raise YorungeError("invalid_request")
    return text


def flag_argument(value: object) -> bool:
    """A switch the caller gives as a real boolean; a truthy string is not one."""
    if type(value) is not bool:
        raise YorungeError("invalid_request")
    return value


def owner_address(owner_username: str | None) -> str:
    """A model without a stored owner name cannot be addressed as ``owner/slug`` (Karar 5).

    The name comes from the provider's answer, so a name outside the alphabet is a provider fault.
    """
    if owner_username is None:
        raise YorungeError("model_not_addressable")
    return provider_segment(owner_username)


def require_address(owner: str, slug: str) -> tuple[str, str]:
    """Both segments of an ``owner/slug`` argument, validated before a request."""
    return segment(owner), segment(slug)


# --- pages ----------------------------------------------------------------------------------------


def page_arguments(page: int, page_size: int) -> None:
    """Request arguments are integers in range, checked before any request is made.

    The page number is bounded by the exact JSON integer range the answer may echo, so an
    absurd number is a refused argument and never reaches the wire or the integer-to-text limit.
    """
    if (
        type(page) is not int
        or type(page_size) is not int
        or not 1 <= page <= MAX_COUNT
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


def _count(value: object) -> int:
    """A count from the answer: an integer from 0 to ``MAX_COUNT``, never a bool or a float."""
    if type(value) is not int or not 0 <= value <= MAX_COUNT:
        raise YorungeError("invalid_response")
    return value


def platform_page(page: int, page_size: int, total: object, returned: int) -> Completeness:
    """A Platform model page is judged by its total and by the rows it actually holds (Karar 2)."""
    total_count = _count(total)
    if returned != expected_rows(page, page_size, total_count):
        # A server that quietly returns another page size is not a page we can trust.
        raise YorungeError("invalid_response")
    return _label(page, has_next(page, page_size, total_count))


def dataset_page(
    page: int,
    page_size: int,
    returned: int,
    has_next_values: Sequence[str],
    total_values: Sequence[str],
) -> Completeness:
    """Dataset paging is in headers. Anything unclear makes the page ``unknown``, never complete.

    The has-next header must appear exactly once, as the integer ``0`` or ``1`` the provider sends
    (observed on the live catalog, K4). The total header may
    appear at most once; when it is present it must be a plain decimal number and must agree with
    the rows and the has-next header, or the answer is invalid.
    """
    if len(has_next_values) != 1 or has_next_values[0] not in ("0", "1"):
        return "unknown"
    if len(total_values) > 1:
        return "unknown"
    more = has_next_values[0] == "1"
    if more and returned != page_size:
        # A short page that announces more pages: the server changed the size under us.
        raise YorungeError("invalid_response")
    if len(total_values) == 1:
        if _DIGITS.fullmatch(total_values[0]) is None:
            return "unknown"
        total = int(total_values[0])
        if total > MAX_COUNT:  # beyond what a JSON reader keeps exactly: no such total exists
            raise YorungeError("invalid_response")
        if returned != expected_rows(page, page_size, total):
            raise YorungeError("invalid_response")
        if more != has_next(page, page_size, total):
            raise YorungeError("invalid_response")
    return _label(page, more)


def versions_listing(versions_count: object, listed: int) -> Completeness:
    """A version list has no paging: complete only when its rows equal the detail count."""
    if versions_count is None:
        return "unknown"
    return "complete" if listed == _count(versions_count) else "unknown"


def checked_versions(versions_count: object, listed: int) -> None:
    """Resolution refuses a version list that disagrees with the detail it was read with."""
    if listed != _count(versions_count):
        raise YorungeError("invalid_response")


def detail_identity(owner_username: str | None, slug: str, owner: str, asked_slug: str) -> None:
    """The detail answer must be the model the address named; anything else is not that model."""
    if owner_username != owner or slug != asked_slug:
        raise YorungeError("invalid_response")


# --- resolution -----------------------------------------------------------------------------------


VersionT = TypeVar("VersionT", bound=VersionRef)


class VersionAmbiguous(YorungeError):
    """More than one version carries the tag: the few candidates are shown, none is chosen.

    Each candidate is ``(identity, tag, creation time)``; there are at most ``MAX_CANDIDATES``.
    ``total`` is how many versions carry the tag, so that a reader knows how many were not shown.
    """

    def __init__(self, found: tuple[tuple[str, str, str], ...], total: int) -> None:
        super().__init__("model_ambiguous")
        self.candidates = found
        self.total = total

    def envelope(self) -> dict[str, object]:
        # The machine reader needs the candidates too, not only the text hint.
        value = super().envelope()
        value["details"] = {
            "total": self.total,
            "candidates": [
                {"version_id": identity, "version_tag": tag, "created_at": created}
                for identity, tag, created in self.candidates
            ],
        }
        return value


def resolve_version(versions: Sequence[VersionT], tag: str) -> VersionT:
    """Exactly one version carries the tag; none is not-visible, more than one is ambiguous."""
    version_tag(tag)
    matches = [item for item in versions if item.version_tag == tag]
    if not matches:
        raise YorungeError("model_not_visible")
    if len(matches) > 1:
        raise VersionAmbiguous(
            tuple(
                (item.version_id, item.version_tag, item.created_at)
                for item in candidates(versions, tag)
            ),
            len(matches),
        )
    return matches[0]


def candidates(versions: Sequence[VersionT], tag: str) -> tuple[VersionT, ...]:
    """The few candidates an ambiguity shows: enough to choose by identity, never a pick."""
    return tuple(item for item in versions if item.version_tag == tag)[:MAX_CANDIDATES]


def task_matches(expected: str, observed: str) -> None:
    """An expected LLM task must equal the observed one; unknown task names are not refused here."""
    if expected != observed:
        raise YorungeError("model_task_mismatch")


# --- display --------------------------------------------------------------------------------------


def text(value: str | None, limit: int) -> str | None:
    """Untrusted provider text as it may be shown: no format or control characters, bounded length.

    Line breaks, tabs, the vertical tab, form feed, NEL and the Unicode line and paragraph
    separators become spaces; every other control and bidirectional override is dropped. A cut text
    ends with an ellipsis, so that it is never silently shortened.
    """
    if type(limit) is not int or limit < 2:
        raise YorungeError("invalid_response")
    if value is None:
        return None
    if type(value) is not str:
        raise YorungeError("invalid_response")
    pieces: list[str] = []
    for char in value:
        category = unicodedata.category(char)
        if char in "\t\n\r\v\f\x85" or category in _LINE_CATEGORIES:
            pieces.append(" ")
        elif category in _FORMAT_CATEGORIES:
            continue
        else:
            pieces.append(char)
    cleaned = "".join(pieces).strip()
    if len(cleaned) > limit:
        return cleaned[: limit - 1] + ELLIPSIS
    return cleaned


# --- consumed records (ADR-0035 Karar 8) ----------------------------------------------------------

MAX_COUNT: Final = 2**53 - 1  # the largest integer every JSON reader keeps exactly
_STAMP: Final = re.compile(
    r"\A[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])"
    r"T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{1,6})?"
    r"(Z|[+-](0[0-9]|1[0-9]|2[0-3]):[0-5][0-9])\Z"
)
# Surrogates (``Cs``) cannot be encoded as UTF-8, so no identifier may carry one.
_UNPLAIN_CATEGORIES: Final = frozenset({"Cc", "Cf", "Cs", "Zl", "Zp"})


def plain_identifier(value: str) -> str:
    """An identifier is opaque: no control, format or line-separator character, no edge whitespace.

    Such a character is never part of a legitimate identifier, and a cleaned identifier could name
    another model or rebuild a secret, so the answer is refused instead of cleaned. Edge whitespace
    is refused too, because a trimmed identifier would be shown as a different one.
    """
    if (
        value != value.strip()
        or has_control_characters(value)
        or any(unicodedata.category(char) in _UNPLAIN_CATEGORIES for char in value)
    ):
        raise ValueError("plain identifier required")
    return value


def _stamp(value: str) -> str:
    """RFC 3339 date-time with an offset, and a real calendar date and time."""
    if _STAMP.fullmatch(value) is None:
        raise ValueError("RFC 3339 date-time required")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("RFC 3339 date-time required") from None
    return value


Identity = Annotated[
    str,
    AfterValidator(plain_identifier),
    Field(min_length=1, max_length=IDENTITY_LIMIT),
]
Count = Annotated[int, Field(ge=0, le=MAX_COUNT)]
Price = Annotated[int | float, Field(ge=0, le=MAX_COUNT, allow_inf_nan=False)]
Stamp = Annotated[str, AfterValidator(_stamp), Field(max_length=40)]


class _Consumed(Model):
    """Closed records: only the fields the reader consumes exist; everything else was dropped."""


class LlmPricing(_Consumed):
    prompt_token_price: Price
    completion_token_price: Price
    currency: str | None
    free_until: str | None


class LlmModel(_Consumed):
    model_id: Identity
    task: Annotated[str, AfterValidator(plain_identifier), Field(min_length=1, max_length=64)]
    created: Count
    modalities: tuple[str, ...] | None = Field(default=None, max_length=MODALITY_LIMIT)
    context_length: Count | None = None
    default_max_output_tokens: Count | None = None
    precision: str | None = None
    pricing: LlmPricing | None = None


class LlmListing(_Consumed):
    models: tuple[LlmModel, ...] = Field(max_length=LLM_MAX_RECORDS)
    completeness: Literal["unknown"] = "unknown"
    # Set only by the client-side task filter of the command line; the provider never sends it.
    task_filter: str | None = None


class PlatformModel(_Consumed):
    model_id: Identity
    owner_username: Identity | None
    slug: Identity
    name: str
    description: str | None
    license: str | None
    modality: str
    stage: str
    visibility: str
    versions_count: Count
    architecture: str | None
    created_at: Stamp
    updated_at: Stamp


class PlatformModelPage(_Consumed):
    page: Annotated[int, Field(ge=1, le=MAX_COUNT)]
    page_size: Annotated[int, Field(ge=1, le=PLATFORM_MAX_PAGE_SIZE)]
    total: Count
    returned: Count
    completeness: Completeness
    models: tuple[PlatformModel, ...]


class PlatformVersion(_Consumed):
    version_id: Identity
    version_tag: Identity
    framework: str | None
    file_size_bytes: Count | None
    created_at: Stamp
    has_weights: bool
    has_onnx: bool
    has_tflite: bool


class VersionListing(_Consumed):
    versions: tuple[PlatformVersion, ...] = Field(max_length=MAX_VERSION_ROWS)
    completeness: Completeness


class PlatformDataset(_Consumed):
    dataset_id: Identity
    name: str
    slug: Identity
    modality: str
    item_count: Count
    visibility: str
    updated_at: Stamp
    owner_username: Identity | None


class DatasetPage(_Consumed):
    page: Annotated[int, Field(ge=1, le=MAX_COUNT)]
    page_size: Annotated[int, Field(ge=1, le=PLATFORM_MAX_PAGE_SIZE)]
    returned: Count
    completeness: Completeness
    scope: Literal["unknown"] = "unknown"  # the filter's effect is unproven until K4 (Karar 2)
    datasets: tuple[PlatformDataset, ...]


class PlatformModelDetail(_Consumed):
    """One model, and its version list when the caller asked for it."""

    model: PlatformModel
    versions: VersionListing | None


class PlatformVersionResolution(_Consumed):
    """A tag resolved to exactly one version of one model."""

    model: PlatformModel
    version: PlatformVersion


T = TypeVar("T")


class CatalogReading(Model, Generic[T]):
    """What one command read, with the window and the profile whose account it was read with
    (ADR-0035 Karar 3)."""

    observed_from: Stamp
    observed_until: Stamp
    profile: Identifier
    data: T
