"""Typed private HTTP boundary, independent of the concrete network library."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import unquote_to_bytes, urlencode

from yorunge.application.response_json import JSON_LIMIT, literal_secret_match, parse_json
from yorunge.domain.credentials import SecretValue, ServiceId, ServiceTarget, normalize_target
from yorunge.domain.errors import ErrorCode, YorungeError
from yorunge.domain.models import has_control_characters

CHUNK_SIZE = 32_768
RAW_LIMIT = 1_073_741_824
PAIR_LIMIT = 64
METADATA_LIMIT = 65_536
URL_LIMIT = 65_536
NAME_LIMIT = 128
VALUE_LIMIT = 16_384
HEADER_NAME = re.compile(r"[!#$%&'*+.^_`|~\da-zA-Z-]+", flags=re.ASCII)
METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})
RESERVED_HEADERS = frozenset(
    {
        "host",
        "content-length",
        "cookie",
        "authorization",
        "proxy-authorization",
        "proxy-connection",
        "connection",
        "transfer-encoding",
        "upgrade",
        "trailer",
        "te",
        "accept-encoding",
    }
)


class HttpStatusFailure(YorungeError):
    """A safe status preserves endpoint semantics without retaining private HTTP objects."""

    def __init__(self, status_code: int) -> None:
        if type(status_code) is not int or not 100 <= status_code <= 599:
            raise YorungeError("invalid_response")
        code: ErrorCode = "remote_failed"
        if status_code in (401, 403):
            code = "remote_access_denied"
        elif status_code == 429:
            code = "remote_rate_limited"
        self.status_code = status_code
        super().__init__(code)


def _ascii_header(name: str, value: str) -> bool:
    return (
        type(name) is str
        and type(value) is str
        and 1 <= len(name) <= NAME_LIMIT
        and bool(HEADER_NAME.fullmatch(name))
        and value.isascii()
        and not has_control_characters(value)
        and value == value.strip(" ")
        and len(value) <= VALUE_LIMIT
    )


@dataclass(frozen=True, slots=True, repr=False)
class HttpCredential:
    """The endpoint adapter chooses the header; only the network adapter reveals it."""

    header_name: str
    secret: SecretValue = field(repr=False)
    prefix: str = field(default="", repr=False)
    target: ServiceTarget = field(kw_only=True, repr=False)
    service_id: ServiceId = field(kw_only=True, repr=False)

    def __post_init__(self) -> None:
        _service(self.service_id)
        _canonical_target(self.target)
        valid = isinstance(self.secret, SecretValue) and type(self.prefix) is str
        if valid:
            value = self.prefix + self.secret.reveal()
            valid = (
                _ascii_header(self.header_name, value)
                and self.header_name.lower() not in RESERVED_HEADERS - {"authorization"}
                and not self.header_name.lower().startswith("proxy-")
            )
        if not valid:
            raise YorungeError("invalid_credential")

    def __repr__(self) -> str:
        return "<HttpCredential redacted>"

    def wire_header(self) -> tuple[str, str]:
        return self.header_name, self.prefix + self.secret.reveal()


def _pair_size(name: str, text: str) -> int:
    if type(name) is not str or type(text) is not str:
        raise YorungeError("invalid_request")
    valid_utf8 = False
    name_size, value_size = 0, 0
    try:
        name_size, value_size = len(name.encode("utf-8")), len(text.encode("utf-8"))
        valid_utf8 = True
    except UnicodeError:
        pass
    if not valid_utf8:
        raise YorungeError("invalid_request")
    if (
        not 1 <= name_size <= NAME_LIMIT
        or value_size > VALUE_LIMIT
        or has_control_characters(name)
        or has_control_characters(text)
    ):
        raise YorungeError("invalid_request")
    return name_size + value_size


def _pairs(value: tuple[tuple[str, str], ...], *, headers: bool) -> int:
    if type(value) is not tuple or len(value) > PAIR_LIMIT:
        raise YorungeError("invalid_request")
    size, seen = 0, set()
    for pair in value:
        if type(pair) is not tuple or len(pair) != 2:
            raise YorungeError("invalid_request")
        name, text = pair
        pair_size = _pair_size(name, text)
        if headers:
            lowered = name.lower()
            if (
                not _ascii_header(name, text)
                or lowered in RESERVED_HEADERS
                or lowered.startswith("proxy-")
                or lowered in seen
            ):
                raise YorungeError("invalid_request")
            seen.add(lowered)
        size += pair_size
    return size


def _canonical_target(target: ServiceTarget) -> None:
    if (
        not isinstance(target, ServiceTarget)
        or type(target.service_origin) is not str
        or type(target.api_base_path) is not str
    ):
        raise YorungeError("invalid_service_target")
    if normalize_target(target.service_origin + target.api_base_path) != target:
        raise YorungeError("invalid_service_target")


def _service(service_id: ServiceId) -> None:
    if type(service_id) is not str or service_id not in ("evren-platform", "evren-llm"):
        raise YorungeError("invalid_service_target")


def _request_url(target: ServiceTarget, endpoint: str) -> str:
    _canonical_target(target)
    if type(endpoint) is not str:
        raise YorungeError("invalid_service_target")
    if (
        not endpoint
        or len(endpoint) > 2048
        or any(char in endpoint for char in ("?", "#", "\\", ":", "@"))
        or any(part in ("", ".", "..") for part in endpoint.split("/"))
        or has_control_characters(endpoint)
    ):
        raise YorungeError("invalid_service_target")
    full = normalize_target(
        target.service_origin + target.api_base_path.rstrip("/") + "/" + endpoint
    )
    prefix = target.api_base_path.rstrip("/") + "/"
    if full.service_origin != target.service_origin or not full.api_base_path.startswith(prefix):
        raise YorungeError("invalid_service_target")
    return full.service_origin + full.api_base_path


@dataclass(frozen=True, slots=True, repr=False)
class HttpRequest:
    """Captured request data; this object never reads config, env or a credential registry."""

    target: ServiceTarget = field(repr=False)
    method: str
    endpoint: str = field(repr=False)
    query: tuple[tuple[str, str], ...] = field(default=(), repr=False)
    headers: tuple[tuple[str, str], ...] = field(default=(), repr=False)
    content: bytes = field(default=b"", repr=False)
    credential: HttpCredential | None = field(default=None, repr=False)
    read_only: bool = False
    max_bytes: int = JSON_LIMIT
    service_id: ServiceId = field(kw_only=True, repr=False)
    _url: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _service(self.service_id)
        url = _request_url(self.target, self.endpoint)
        if (
            type(self.method) is not str
            or self.method not in METHODS
            or type(self.read_only) is not bool
            or (self.read_only and self.method not in {"GET", "HEAD"})
            or type(self.content) is not bytes
            or len(self.content) > JSON_LIMIT
            or type(self.max_bytes) is not int
            or not 1 <= self.max_bytes <= RAW_LIMIT
            or (self.credential is not None and not isinstance(self.credential, HttpCredential))
        ):
            raise YorungeError("invalid_request")
        size = _pairs(self.query, headers=False) + _pairs(self.headers, headers=True)
        count = len(self.query) + len(self.headers)
        credential_size, credential_count = self._credential_metadata()
        size += credential_size
        count += credential_count
        if size > METADATA_LIMIT or count > PAIR_LIMIT:
            raise YorungeError("invalid_request")
        content_type = next(
            (
                value.split(";", 1)[0].strip().lower()
                for name, value in self.headers
                if name.lower() == "content-type"
            ),
            "",
        )
        if self.content and (content_type == "application/json" or content_type.endswith("+json")):
            valid_json = False
            try:
                parse_json(self.content)
                valid_json = True
            except YorungeError:
                pass
            if not valid_json:
                raise YorungeError("invalid_request")
        query = urlencode(self.query)
        wire_url = url + ("?" + query if query else "")
        if len(wire_url.encode("ascii")) > URL_LIMIT:
            raise YorungeError("invalid_request")
        object.__setattr__(self, "_url", wire_url)

    def _credential_metadata(self) -> tuple[int, int]:
        if self.credential is None:
            return 0, 0
        if self.credential.target != self.target or self.credential.service_id != self.service_id:
            raise YorungeError("invalid_service_target")
        secret = self.credential.secret.reveal()
        dynamic_url_values = (
            self.endpoint,
            unquote_to_bytes(self.endpoint).decode("utf-8", errors="strict"),
            *(part for pair in self.query for part in pair),
        )
        if any(literal_secret_match(value, secret) for value in dynamic_url_values):
            raise YorungeError("invalid_request")
        auth_name, auth_value = self.credential.wire_header()
        if any(name.lower() == auth_name.lower() for name, _ in self.headers):
            raise YorungeError("invalid_request")
        return len(auth_name) + len(auth_value), 1

    def __repr__(self) -> str:
        return "<HttpRequest private>"

    @property
    def url(self) -> str:
        return self._url

    def wire_headers(self) -> tuple[tuple[str, str], ...]:
        values = self.headers + (("Accept-Encoding", "identity"),)
        if self.credential is not None:
            values += (self.credential.wire_header(),)
        return values


class HttpResponse(Protocol):
    @property
    def status_code(self) -> int: ...

    @property
    def headers(self) -> tuple[tuple[str, str], ...]: ...

    def chunks(self) -> AsyncIterator[bytes]: ...


class HttpTransport(Protocol):
    def open(
        self, request: HttpRequest, *, deadline: float
    ) -> AbstractAsyncContextManager[HttpResponse]: ...
