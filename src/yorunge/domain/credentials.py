"""Service-bound credential values and pure target normalization."""

from __future__ import annotations

import hmac
import ipaddress
import json
import re
from dataclasses import dataclass
from typing import Annotated, Literal, NoReturn
from urllib.parse import SplitResult, quote, unquote_to_bytes, urlsplit

from pydantic import ConfigDict, Field, field_validator, model_validator

from yorunge.domain.errors import YorungeError
from yorunge.domain.models import (
    Context,
    EnvName,
    Identifier,
    Model,
    has_control_characters,
)
from yorunge.domain.models import (
    ServiceId as ServiceId,
)
from yorunge.domain.state import canonical_uuid, check_utc

SECRET_LIMIT = 16_384
TAG_FORMAT = "hmac-sha256-v1"


class ServiceTarget(Model):
    service_origin: str
    api_base_path: str


class EnvReference(Model):
    service_id: ServiceId
    kind: Literal["env"] = "env"
    name: EnvName


class SecretValue:
    """Opaque to ordinary rendering/serialization; explicit adapter access is required."""

    __slots__ = ("__value",)

    def __init__(self, value: str) -> None:
        valid = isinstance(value, str)
        encoded = b""
        if valid:
            try:
                encoded = value.encode("utf-8", errors="strict")
            except UnicodeError:
                valid = False
        if not valid or len(encoded) > SECRET_LIMIT:
            raise YorungeError("invalid_credential")
        if not encoded:
            raise YorungeError("credential_unavailable")
        self.__value = value

    def reveal(self) -> str:
        """For a selected consumer adapter, never for a public result or diagnostic."""
        return self.__value

    def __repr__(self) -> str:
        return "<SecretValue redacted>"

    __str__ = __repr__

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("credential serialization is not supported")

    def __getstate__(self) -> NoReturn:
        raise TypeError("credential serialization is not supported")


@dataclass(frozen=True, slots=True)
class ResolvedCredential:
    reference: EnvReference
    target: ServiceTarget
    secret: SecretValue


class CredentialCheck(Model):
    model_config = ConfigDict(defer_build=True)

    service_id: ServiceId
    service_origin: str
    api_base_path: str
    profile: Identifier
    account_id: Identifier | None
    project_id: Identifier | None
    available: Literal[True] = True
    remote_verified: Literal[False] = False


class CredentialBinding(Model):
    identity_epoch: str
    service_id: ServiceId
    service_origin: str
    api_base_path: str
    reference_type: Literal["env"]
    reference_name: EnvName

    @field_validator("identity_epoch")
    @classmethod
    def epoch_value(cls, value: str) -> str:
        return canonical_uuid(value)

    @model_validator(mode="after")
    def canonical_target(self) -> CredentialBinding:
        target = normalize_target(self.service_origin + self.api_base_path)
        if (
            target.service_origin != self.service_origin
            or target.api_base_path != self.api_base_path
        ):
            raise ValueError("canonical binding target required")
        return self

    def encoded(self) -> bytes:
        return json.dumps(
            self.model_dump(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")

    def as_key(self) -> tuple[str, str, str, str, str, str]:
        return (
            self.identity_epoch,
            self.service_id,
            self.service_origin,
            self.api_base_path,
            self.reference_type,
            self.reference_name,
        )


class CredentialIdentity(Model):
    credential_id: str
    credential_revision: Annotated[int, Field(ge=1, le=2**63 - 1)]
    identity_epoch: str
    observed_at: str

    @field_validator("credential_id", "identity_epoch")
    @classmethod
    def uuid_value(cls, value: str) -> str:
        return canonical_uuid(value)

    @field_validator("observed_at")
    @classmethod
    def timestamp_value(cls, value: str) -> str:
        check_utc(value)
        return value


class CredentialObservation(CredentialCheck):
    identity: CredentialIdentity


@dataclass(frozen=True, slots=True)
class BoundCredential:
    context: Context
    credential: ResolvedCredential
    identity: CredentialIdentity


def observation_tag(binding: CredentialBinding, key: bytes, secret: SecretValue) -> bytes:
    if not isinstance(key, bytes) or len(key) != 32:
        raise ValueError("32-byte comparison key required")
    encoded, value = binding.encoded(), secret.reveal().encode("utf-8")
    message = (
        b"yorunge:credential-observation:v1\x00"
        + len(encoded).to_bytes(8, "big")
        + encoded
        + len(value).to_bytes(8, "big")
        + value
    )
    return hmac.digest(key, message, "sha256")


def _target(value: str) -> ServiceTarget:
    if (
        not isinstance(value, str)
        or len(value) > 2048
        or has_control_characters(value)
        or any(char in value for char in (" ", "\\", "?", "#"))
    ):
        raise ValueError("invalid target")
    parts = urlsplit(value)
    origin, path = _origin(parts), _path(parts.path)
    if len(origin + path) > 2048:
        raise ValueError("canonical target too long")
    return ServiceTarget(service_origin=origin, api_base_path=path)


def _origin(parts: SplitResult) -> str:
    if not parts.netloc.isascii():
        raise ValueError("ASCII authority required")
    host = parts.hostname or ""
    if (
        parts.scheme != "https"
        or not host
        or parts.username is not None
        or parts.password is not None
        or parts.port not in (None, 443)
        or "%" in parts.netloc
    ):
        raise ValueError("invalid authority")
    authority_end = (
        parts.netloc.find("]") + 1
        if parts.netloc.startswith("[")
        else len(parts.netloc.split(":", 1)[0])
    )
    suffix = parts.netloc[authority_end:]
    if suffix and not re.fullmatch(r":\d+", suffix, flags=re.ASCII):
        raise ValueError("invalid authority suffix")
    if parts.netloc.startswith("["):
        host = "[" + ipaddress.IPv6Address(host).compressed + "]"
    elif re.fullmatch(r"[0-9.]+", host):
        host = str(ipaddress.IPv4Address(host))
    else:
        if len(host) > 253 or not all(
            re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
            for label in host.split(".")
        ):
            raise ValueError("ASCII DNS name required")
        host = host.lower()
    return "https://" + host


def _path(path: str) -> str:
    if path.endswith("//") or any(segment in (".", "..") for segment in path.split("/")):
        raise ValueError("ambiguous path")
    if re.search(r"%(?![0-9a-f]{2})|%(?:2f|5c|2e|25)", path, flags=re.IGNORECASE):
        raise ValueError("ambiguous escape")
    allowed = "/%ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~!$&'()*+,;=:@"
    if any(ord(char) < 128 and char not in allowed for char in path):
        raise ValueError("invalid path character")
    decoded = unquote_to_bytes(path).decode("utf-8", errors="strict")
    if has_control_characters(decoded) or " " in decoded:
        raise ValueError("invalid decoded path")
    path = quote(path, safe=allowed).rstrip("/") or "/"
    path = re.sub(r"%[0-9a-fA-F]{2}", lambda match: match[0].upper(), path)
    return path


def normalize_target(value: str) -> ServiceTarget:
    target = None
    try:
        target = _target(value)
    except ValueError:
        pass
    if target is None:
        raise YorungeError("invalid_service_target")
    return target
