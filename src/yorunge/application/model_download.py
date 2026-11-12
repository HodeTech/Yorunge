"""The first consumer of the download engine: a model version's weights (ADR-0032 §1).

Two things are decided here and nowhere else, both without I/O: what the one JSON call asks for
(an exact model version, an explicit format and, if the user gave one, a fold) and what its answer
is allowed to be. The answer names a signed address; the address is trusted for nothing but being
downloaded from, so it must sit below the registered Platform origin and below exactly
``{api_base_path}/files/evren-models/`` (the answer cannot widen the prefix, and the dataset
bucket's ``{api_base_path}/files/`` is not it). The provider's ``filename`` is validated and then
forgotten: it never becomes the name of the output, and nothing the provider says is reflected.
"""

from __future__ import annotations

import re
from typing import Final
from urllib.parse import unquote, urlsplit

from yorunge.application.download_transport import DownloadTarget
from yorunge.application.response_json import parse_json, scan_for_secret
from yorunge.domain.credentials import SecretValue
from yorunge.domain.download import MAX_FOLD, parse_fold
from yorunge.domain.errors import YorungeError

FORMATS: Final = ("onnx", "pt", "tflite")
MODEL_FILES_SEGMENT: Final = "/files/evren-models/"
MAX_FILENAME_BYTES: Final = 255
# What a signed address always is: lowercase ``https``, a plain host and only the characters
# RFC 3986 allows in a path and a query. The HTTP client rewrites some of what lies outside (a
# quote, an angle bracket or a space; a brace or a backtick in the path; the case of the scheme and
# host) on its way to the wire, and the rest is no URI character at all: a signature is made of
# exact bytes, so only the plain set is accepted, whatever a client version does with the others.
_ADDRESS: Final = re.compile(r"https://[A-Za-z0-9.-]+/[A-Za-z0-9._~!$&'()*+,;=:@/%?-]*")


def weights_endpoint(version_id: str) -> str:
    """The route of the JSON call, below the API base (the version id is already canonical)."""
    return f"models/versions/{version_id}/download"


def weights_query(artifact_format: str, fold: int | None) -> tuple[tuple[str, str], ...]:
    """The explicit format, and the fold only if the user gave one (nothing is guessed)."""
    if artifact_format not in FORMATS:
        raise YorungeError("invalid_request")
    query = [("format", artifact_format)]
    if fold is not None:
        query.append(("fold", str(parse_fold(fold))))  # 0..MAX_FOLD, a strict integer
    return tuple(query)


def weights_prefix(api_base_path: str) -> str:
    """The path every signed address of a model's weights must be below."""
    if type(api_base_path) is not str or "//" in api_base_path or not api_base_path.startswith("/"):
        raise YorungeError("invalid_service_target")
    return api_base_path.rstrip("/") + MODEL_FILES_SEGMENT


def parse_weights_answer(
    data: bytes, *, secret: SecretValue, origin: str, api_base_path: str
) -> DownloadTarget:
    """The signed address the JSON call answered, or ``invalid_response``.

    A strict object with a string ``download_url`` and a string ``filename`` (the provider's schema
    requires both); the selected key is in no string or key of the answer; the filename is a plain
    name (no separator, control character, dot name or more than 255 bytes) although it is never
    used; the address passes every rule of a direct signed target below the model prefix and
    names one object there (not the prefix itself, not a directory).
    """
    document = parse_json(data)
    scan_for_secret(document, secret)
    if type(document) is not dict:
        raise YorungeError("invalid_response")
    url, name = document.get("download_url"), document.get("filename")
    if type(url) is not str or type(name) is not str or not _plain_name(name):
        raise YorungeError("invalid_response")
    if _ADDRESS.fullmatch(url) is None:
        raise YorungeError("invalid_response")  # not the bytes a signature can have been made of
    target: DownloadTarget | None = None
    try:
        candidate = DownloadTarget(url, origin=origin, prefix=weights_prefix(api_base_path))
        candidate.check_secret(secret)
        if _names_an_object(candidate):
            target = candidate
    except YorungeError:
        pass  # an address the answer made is the answer's fault, not the local target's
    if target is None:
        raise YorungeError("invalid_response")
    return target


def _names_an_object(target: DownloadTarget) -> bool:
    """The path below the prefix names one object, as a server will read it.

    Not the prefix itself, not a directory, and no segment that is empty or a dot segment once it is
    decoded (also twice) and stripped of its path parameters: ``..;x``, ``%2e%2e;x``, ``;x``.
    """
    path = urlsplit(target.wire_url).path
    if not path.startswith(target.prefix):
        return False
    below = path[len(target.prefix) :]  # the prefix itself ends with "/"
    return bool(below) and all(_names_something(segment) for segment in below.split("/"))


def _names_something(segment: str) -> bool:
    """A path segment a server reads as a name: not empty, not ``.``/``..``, parameters aside."""
    for _ in range(3):  # an encoded encoding (``%252e``) is decoded as often as a server might
        decoded = unquote(segment)
        if decoded == segment:
            break
        segment = decoded
    return segment.split(";", 1)[0] not in ("", ".", "..")


def _plain_name(name: str) -> bool:
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        return False
    try:
        encoded = name.encode("utf-8")
    except UnicodeError:
        return False
    return len(encoded) <= MAX_FILENAME_BYTES and not any(
        ord(char) < 32 or 127 <= ord(char) <= 159 for char in name
    )


__all__ = [
    "FORMATS",
    "MAX_FOLD",
    "parse_weights_answer",
    "weights_endpoint",
    "weights_prefix",
    "weights_query",
]
