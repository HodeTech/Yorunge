"""Private storage policy and typed streaming boundary; no provider endpoint guesses."""

from __future__ import annotations

import base64
import re
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Literal, NoReturn, Protocol
from urllib.parse import unquote, urlsplit

from yorunge.application.http_transport import HttpCredential, HttpResponse, HttpTransport
from yorunge.application.response_json import literal_secret_match
from yorunge.domain.capabilities import instant
from yorunge.domain.credentials import SecretValue, ServiceTarget, normalize_target
from yorunge.domain.dataset_manifest import safe_text
from yorunge.domain.dataset_upload import provider_uuid
from yorunge.domain.errors import YorungeError

STORAGE_CHUNK_BYTES = 1024 * 1024
STORAGE_MAX_BYTES = 1024**3
STORAGE_RESPONSE_BYTES = 64 * 1024
SIGNED_URL_BYTES = 16 * 1024
_ESCAPES = re.compile(r"%(?![\da-fA-F]{2})", flags=re.ASCII)
_MEDIA = re.compile(r"[\w!#$&^.+-]+/[\w!#$&^.+-]+", flags=re.ASCII)
_SHA256 = re.compile(r"[\da-f]{64}", flags=re.ASCII)


class ByteSource(Protocol):
    @property
    def size(self) -> int: ...
    @property
    def sha256(self) -> str: ...
    @property
    def sent_bytes(self) -> int: ...
    @property
    def sent_sha256(self) -> str | None: ...
    @property
    def complete(self) -> bool: ...
    def chunks(self) -> AsyncIterator[bytes]: ...
    async def aclose(self) -> None: ...


def _text(value: str) -> None:
    try:
        safe_text(value)
    except (ValueError, UnicodeError):
        raise YorungeError("invalid_service_target") from None


def _decoded(value: str) -> str:
    if _ESCAPES.search(value):
        raise YorungeError("invalid_service_target")
    try:
        text = unquote(value, encoding="utf-8", errors="strict")
    except UnicodeError:
        raise YorungeError("invalid_service_target") from None
    _text(text)
    return text


def _path(value: str) -> tuple[str, ...]:
    if not value.startswith("/") or "\\" in value or "//" in value:
        raise YorungeError("invalid_service_target")
    components = value[1:].split("/")
    interpretations: list[str] = []
    for component in components:
        decoded = component
        interpretations.append(component)
        for _ in range(4):
            decoded = _decoded(decoded)
            interpretations.append(decoded)
            if decoded in {".", ".."} or "/" in decoded or "\\" in decoded:
                raise YorungeError("invalid_service_target")
            if "%" not in decoded:
                break
        else:
            raise YorungeError("invalid_service_target")
    return tuple(interpretations)


class StorageTarget:
    """Non-serializable ephemeral URL; the plan/policy must precede the descriptor."""

    __slots__ = ("_url", "mode", "origin", "prefix", "expires_at", "service", "dataset_id")
    _url: str
    mode: Literal["proxy", "direct"]
    origin: str
    prefix: str
    expires_at: str | None
    service: ServiceTarget | None
    dataset_id: str | None

    def __init__(
        self,
        url: str,
        *,
        mode: Literal["proxy", "direct"],
        origin: str,
        prefix: str,
        expires_at: str | None,
        service: ServiceTarget | None,
        dataset_id: str | None,
    ) -> None:
        self._validate_url(url, origin, prefix)
        if expires_at is not None and type(expires_at) is not str:
            raise YorungeError("invalid_service_target")
        if mode == "direct":
            if expires_at is None or service is not None or dataset_id is not None:
                raise YorungeError("invalid_service_target")
            try:
                instant(expires_at)
            except (ValueError, TypeError):
                raise YorungeError("invalid_service_target") from None
        elif mode == "proxy":
            self._proxy(service, dataset_id, origin, prefix)
            if expires_at is not None:
                try:
                    instant(expires_at)
                except (ValueError, TypeError):
                    raise YorungeError("invalid_service_target") from None
        else:
            raise YorungeError("invalid_service_target")
        attributes: tuple[tuple[str, object], ...] = (
            ("_url", url),
            ("mode", mode),
            ("origin", origin),
            ("prefix", prefix),
            ("expires_at", expires_at),
            ("service", service),
            ("dataset_id", dataset_id),
        )
        for name, item in attributes:
            object.__setattr__(self, name, item)

    @staticmethod
    def _validate_url(url: str, origin: str, prefix: str) -> None:
        try:
            target = normalize_target(origin)
            parsed = urlsplit(url)
            valid = (
                type(url) is str
                and url.isascii()
                and len(url) <= SIGNED_URL_BYTES
                and target.service_origin == origin
                and target.api_base_path == "/"
                and parsed.scheme == "https"
                and parsed.netloc == origin[8:]
                and not parsed.fragment
                and "#" not in url
                and parsed.username is None
                and parsed.password is None
                and parsed.port in (None, 443)
            )
        except (ValueError, TypeError, AttributeError):
            valid = False
        if not valid or type(prefix) is not str:
            raise YorungeError("invalid_service_target")
        _text(url)
        _path(parsed.path)
        _path(prefix)
        if (
            not prefix.endswith("/")
            or "?" in prefix
            or "#" in prefix
            or not parsed.path.startswith(prefix)
        ):
            raise YorungeError("invalid_service_target")
        for component in parsed.query.split("&"):
            for value in component.split("=", 1):
                _decoded(value)

    @staticmethod
    def _proxy(
        service: ServiceTarget | None, dataset_id: str | None, origin: str, prefix: str
    ) -> None:
        if service is None or dataset_id is None:
            raise YorungeError("invalid_service_target")
        try:
            provider_uuid(dataset_id)
            canonical = normalize_target(service.service_origin + service.api_base_path)
        except (ValueError, TypeError, AttributeError):
            raise YorungeError("invalid_service_target") from None
        expected = service.api_base_path.rstrip("/") + "/datasets/" + dataset_id + "/"
        if (
            canonical != service
            or service.service_origin != origin
            or not prefix.startswith(expected)
        ):
            raise YorungeError("invalid_service_target")

    @property
    def wire_url(self) -> str:
        return self._url

    def check_secret(self, secret: SecretValue) -> None:
        parsed = urlsplit(self._url)
        values = [self._url, parsed.hostname or "", *_path(parsed.path)]
        for pair in parsed.query.split("&"):
            values.extend(_decoded(v) for v in pair.split("=", 1))
        if any(literal_secret_match(value, secret.reveal()) for value in values):
            raise YorungeError("invalid_service_target")

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("storage targets are immutable")

    def __repr__(self) -> str:
        return "<StorageTarget redacted>"

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("storage targets cannot be serialized")


@dataclass(frozen=True, slots=True, repr=False)
class StorageRequest:
    target: StorageTarget = field(repr=False)
    source: ByteSource = field(repr=False)
    selected_secret: SecretValue = field(repr=False)
    content_type: str
    checksum: Literal["none", "sha256_hex", "sha256_base64"] = "none"
    credential: HttpCredential | None = field(default=None, repr=False)
    _size: int = field(init=False, repr=False)
    _sha256: str = field(init=False, repr=False)

    def _source_valid(self) -> bool:
        try:
            return (
                type(self.source.size) is int
                and 0 <= self.source.size <= STORAGE_MAX_BYTES
                and type(self.source.sha256) is str
                and bool(_SHA256.fullmatch(self.source.sha256))
            )
        except AttributeError:
            return False

    def __post_init__(self) -> None:
        if (
            type(self.target) is not StorageTarget
            or type(self.selected_secret) is not SecretValue
            or not self._source_valid()
            or type(self.content_type) is not str
            or len(self.content_type) > 128
            or not _MEDIA.fullmatch(self.content_type)
            or type(self.checksum) is not str
            or self.checksum not in {"none", "sha256_hex", "sha256_base64"}
        ):
            raise YorungeError("invalid_request")
        self.target.check_secret(self.selected_secret)
        self._auth()
        object.__setattr__(self, "_size", self.source.size)
        object.__setattr__(self, "_sha256", self.source.sha256)
        # The intentional proxy credential header is excluded from literal scanning.
        if any(
            literal_secret_match(v, self.selected_secret.reveal())
            for name, v in self.public_headers()
            if name not in {"Content-Length", "Accept-Encoding"}
        ):
            raise YorungeError("invalid_request")

    def _auth(self) -> None:
        credential = self.credential
        if self.target.mode == "direct":
            if credential is not None:
                raise YorungeError("invalid_service_target")
            return
        if (
            type(credential) is not HttpCredential
            or credential.service_id != "evren-platform"
            or credential.target != self.target.service
            or credential.prefix != ""
            or credential.header_name.lower() != "x-api-key"
            or credential.secret is not self.selected_secret
        ):
            raise YorungeError("invalid_service_target")

    @property
    def max_bytes(self) -> int:
        return STORAGE_RESPONSE_BYTES

    @property
    def size(self) -> int:
        return self._size

    @property
    def sha256(self) -> str:
        return self._sha256

    def public_headers(self) -> tuple[tuple[str, str], ...]:
        values: tuple[tuple[str, str], ...] = (
            ("Content-Type", self.content_type),
            ("Content-Length", str(self.size)),
            ("Accept-Encoding", "identity"),
        )
        if self.checksum == "sha256_hex":
            values += (("X-Content-SHA256", self.sha256),)
        elif self.checksum == "sha256_base64":
            values += (
                (
                    "X-Amz-Checksum-Sha256",
                    base64.b64encode(bytes.fromhex(self.sha256)).decode("ascii"),
                ),
            )
        return values

    def wire_headers(self) -> tuple[tuple[str, str], ...]:
        return self.public_headers() + ((self.credential.wire_header(),) if self.credential else ())

    def __repr__(self) -> str:
        return "<StorageRequest redacted>"


class StorageResponse(HttpResponse, Protocol):
    @property
    def sent_bytes(self) -> int: ...
    @property
    def sent_sha256(self) -> str: ...


class StorageTransport(HttpTransport, Protocol):
    def open_storage(
        self, request: StorageRequest, *, deadline: float
    ) -> AbstractAsyncContextManager[StorageResponse]: ...
