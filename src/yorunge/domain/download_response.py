"""The signed GET's answer, typed, and what the closed response table does with it.

ADR-0032 §2 and "Yanıt işleme (kapalı tablo)" of ``docs/reference/download-engine.md``. Pure: the
transport hands over a status and the raw header fields; nothing here reads a socket, a clock or
a file. Every wire event falls on exactly one row and one closed code; there is no answer outside
the table, no retry, no identity sent, no silent merge.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, Literal

from yorunge.domain.download import MAX_DOWNLOAD_BYTES, StrongEtag
from yorunge.domain.errors import ErrorCode, YorungeError

Headers = Sequence[tuple[str, str]]
Framing = Literal["length", "chunked"]
Disposition = Literal["full", "restart", "continue", "discard_and_retry"]

_MAX_NUMBER: Final = 2**63 - 1
_DIGITS = r"(0|[1-9]\d{0,18})"  # always compiled with re.ASCII below
_RANGE = re.compile(rf"bytes ({_DIGITS})-({_DIGITS})/({_DIGITS})", re.ASCII | re.IGNORECASE)
_LENGTH = re.compile(r"(0|[1-9][0-9]{0,63})", re.ASCII)  # any length, however absurd, is a number
_STRONG_ETAG = re.compile(r'"[\x21\x23-\x7e]{1,126}"', re.ASCII)


@dataclass(frozen=True, slots=True)
class ContentRange:
    """``bytes first-last/total``: ``0 <= first <= last < total``."""

    first: int
    last: int
    total: int


@dataclass(frozen=True, slots=True)
class DownloadResponse:
    """What the engine is allowed to know of an answer; it never touches a raw header.

    A ``200`` that carries a ``Content-Range`` is typed as the partial answer it is (status 206, no
    usable range, no framing): after a ranged request it is not an exact continuation, and to a
    Range-less request a partial answer is not in the protocol.
    """

    status: Literal[200, 206, 416]
    content_range: ContentRange | None  # 206 only; None when absent, unusable or of another form
    etag: StrongEtag | None  # a strong tag, or None (absent, weak, empty, ambiguous)
    # None for a 416 (its body is not read) and for a 206 whose body cannot be framed (it is
    # not an exact continuation: the stage is dropped and one Range-less request follows).
    framing: Framing | None
    content_length: int | None  # the length, when framing == "length"


@dataclass(frozen=True, slots=True)
class ResumeAsk:
    """The one conditional request: the committed prefix of an object seen with a strong tag."""

    prefix_bytes: int
    total_size: int
    etag: StrongEtag

    def __post_init__(self) -> None:
        if (
            type(self.prefix_bytes) is not int
            or type(self.total_size) is not int
            or not 0 < self.prefix_bytes < self.total_size <= MAX_DOWNLOAD_BYTES
            or type(self.etag) is not str
            or _STRONG_ETAG.fullmatch(self.etag) is None
        ):
            raise ValueError("a resumable prefix of a known total with a strong tag required")


def request_headers(ask: ResumeAsk | None) -> tuple[tuple[str, str], ...]:
    """The headers the application adds, and no others (the transport adds Host and identity)."""
    headers: list[tuple[str, str]] = []
    if ask is not None:
        headers += [("Range", f"bytes={ask.prefix_bytes}-"), ("If-Range", ask.etag)]
    return tuple(headers)


# --- field parsers --------------------------------------------------------------------------------


def parse_content_range(value: object) -> ContentRange | None:
    """A single ``bytes first-last/total`` with a known total, or None.

    Unusable forms give None, never a guess: another unit, a missing or unknown total, several
    ranges, signs, spaces other than the one separator, a start after the end, an end at or past
    the total, a number past the signed 64-bit range.
    """
    if type(value) is not str:
        return None
    match = _RANGE.fullmatch(value.strip(" \t"))
    if match is None:
        return None
    first, last, total = int(match.group(1)), int(match.group(3)), int(match.group(5))
    if max(first, last, total) > _MAX_NUMBER or first > last or last >= total:
        return None
    return ContentRange(first, last, total)


def parse_etag(values: Sequence[str]) -> StrongEtag | None:
    """The strong entity tag of an answer, or None.

    Weak (``W/``), empty, unquoted, over-long and ambiguous (several fields or a list) tags are
    not resumable identities. A tag is never a digest of the content.
    """
    if len(values) != 1 or type(values[0]) is not str:
        return None
    candidate = values[0].strip(" \t")
    return candidate if _STRONG_ETAG.fullmatch(candidate) is not None else None


def _fields(headers: object) -> tuple[tuple[str, str], ...]:
    """The raw header fields as pairs of text; anything else is not an answer."""
    if not isinstance(headers, (list, tuple)):
        raise YorungeError("invalid_response")
    fields = tuple(headers)
    for item in fields:
        if (
            not isinstance(item, tuple)
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) is not str
        ):
            raise YorungeError("invalid_response")
    return fields


def _values(headers: Headers, name: str) -> list[str]:
    return [value for key, value in headers if key.lower() == name]


def _framing(headers: Headers) -> tuple[Framing, int | None]:
    """``Content-Length`` or chunked termination; both, neither or anything odd is refused."""
    lengths, codings = _values(headers, "content-length"), _values(headers, "transfer-encoding")
    if codings:
        if len(codings) != 1 or codings[0].strip(" \t").lower() != "chunked" or lengths:
            raise YorungeError("invalid_response")
        return "chunked", None
    if len(lengths) != 1 or _LENGTH.fullmatch(lengths[0].strip(" \t")) is None:
        raise YorungeError("invalid_response")  # a body closed by the connection is refused
    length = int(lengths[0].strip(" \t"))
    if length > MAX_DOWNLOAD_BYTES:
        raise YorungeError("download_limit_exceeded")  # refused before one byte is written
    return "length", length


def parse_response(status: object, headers: Headers) -> DownloadResponse:
    """The typed answer for 200, 206 and 416; any other answer raises its closed code.

    Rows of the table: 3xx ``remote_failed`` (a redirect is never followed); 401 and 403
    ``remote_access_denied``; 429 ``remote_rate_limited``; 404 and every other 4xx, and 5xx,
    ``remote_failed``; any other 2xx, a ``Content-Encoding`` other than identity, an
    informational status and a ``200`` body without a length or chunked end ``invalid_response``;
    a ``200`` that carries a ``Content-Range`` is typed as a partial answer that is not an exact
    continuation; a ``Content-Length`` over the limit ``download_limit_exceeded``.
    """
    if type(status) is not int or not 100 <= status <= 599:
        raise YorungeError("invalid_response")
    headers = _fields(headers)
    if status in (401, 403):
        raise YorungeError("remote_access_denied")
    if status == 429:
        raise YorungeError("remote_rate_limited")
    if 300 <= status <= 599 and status != 416:
        raise YorungeError("remote_failed")
    if status == 416:
        return DownloadResponse(416, None, None, None, None)
    if status not in (200, 206):
        raise YorungeError("invalid_response")
    encodings = _values(headers, "content-encoding")
    if any(value.strip(" \t").lower() not in ("", "identity") for value in encodings):
        raise YorungeError("invalid_response")
    ranges = _values(headers, "content-range")
    if status == 200 and ranges:
        # Content-Range belongs to partial answers (RFC 9110 14.4). On a "full" one it is the mark
        # of a server that applied the range and labelled the tail 200: written as the whole
        # object it would be a complete transfer of the wrong bytes. It is typed as the partial
        # answer it is, whose body is never read (whatever its framing): after a ranged request
        # the stage is dropped and one Range-less request follows; to a Range-less request it is
        # invalid_response (see disposition). A refusal here would repeat on every rerun.
        return DownloadResponse(206, None, parse_etag(_values(headers, "etag")), None, None)
    framing: Framing | None
    length: int | None
    try:
        framing, length = _framing(headers)
    except YorungeError as error:
        if status != 206 or error.code != "invalid_response":
            raise
        # A partial answer that cannot be framed is not an exact continuation ("Content-Length
        # uyumsuz veya eksik"): it is dropped like any other, and one Range-less request follows.
        framing, length = None, None
    content_range = parse_content_range(ranges[0]) if status == 206 and len(ranges) == 1 else None
    return DownloadResponse(
        200 if status == 200 else 206,
        content_range,
        parse_etag(_values(headers, "etag")),
        framing,
        length,
    )


# --- what to do with it ---------------------------------------------------------------------------


def disposition(response: DownloadResponse, ask: ResumeAsk | None) -> Disposition:
    """The one action an answer calls for, given what the request asked.

    ``full``: write the whole body. ``restart``: the provider ignored the range, so the stage is
    truncated and written from the start of this answer (no further request). ``continue``: an
    exact continuation. ``discard_and_retry``: the stage and the sidecar are dropped (stage first)
    and exactly one Range-less request follows. A partial answer, or a 416, to a request that
    asked for no range is not in the protocol.

    A ``200`` whose length is exactly the tail that was asked for (the total less the prefix) is
    not the whole object that ignoring the range would send: it is the tail labelled ``200``, and
    is treated as the partial answer that is not an exact continuation. (A 200 of the same
    length for an object that changed costs one more request inside the same two.)
    """
    if ask is None:
        if response.status != 200:
            raise YorungeError("invalid_response")
        return "full"
    if response.status == 200:
        if (
            response.framing == "length"
            and response.content_length == ask.total_size - ask.prefix_bytes
        ):
            return "discard_and_retry"
        return "restart"
    if response.status == 416:
        return "discard_and_retry"
    content_range = response.content_range
    exact = (
        content_range is not None
        and content_range.first == ask.prefix_bytes
        and content_range.last == ask.total_size - 1
        and content_range.total == ask.total_size
        and response.etag is not None
        and response.etag == ask.etag
        and response.framing == "length"
        and response.content_length == ask.total_size - ask.prefix_bytes
    )
    return "continue" if exact else "discard_and_retry"


# --- the body -------------------------------------------------------------------------------------


def check_written(written: int) -> None:
    """The running counter of the body: over the limit is refused before the next write."""
    if type(written) is not int or written < 0:
        raise ValueError("a byte count required")
    if written > MAX_DOWNLOAD_BYTES:
        raise YorungeError("download_limit_exceeded")


def check_body_end(
    framing: Framing, content_length: int | None, written: int, *, terminated: bool
) -> None:
    """The body ended: the bytes written must be the whole of what the framing promised."""
    check_written(written)
    if framing == "length":
        if content_length is None or written > content_length:
            raise YorungeError("invalid_response")
        if written < content_length:
            raise YorungeError("download_incomplete")
    elif framing == "chunked":
        if not terminated:
            raise YorungeError("download_incomplete")
    else:
        raise ValueError("a body has a length or is chunked")


def body_failure(code: ErrorCode) -> ErrorCode:
    """The code of a failure in the body phase, as the download sees it.

    For the errors the transport raises while it reads a body; not for ``check_body_end``'s own
    (a body longer than its framing promised is ``invalid_response`` and stays one).

    A cut connection is ``download_incomplete``; the common transport's body-phase
    ``invalid_response`` is its size cap, which the download calls ``download_limit_exceeded``;
    a timeout keeps its own code (``transport_timeout`` keeps its priority) and so does every
    other closed code (a cancellation, an earlier download code).
    """
    if code in ("transport_failed", "stream_interrupted"):
        return "download_incomplete"
    if code == "invalid_response":
        return "download_limit_exceeded"
    return code
