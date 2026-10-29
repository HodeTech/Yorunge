"""Versioned capability evidence; independent of the frozen offline v1 models."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated, Any, ClassVar, Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic.config import ExtraValues

from yorunge.domain.credentials import normalize_target
from yorunge.domain.models import (
    Execution,
    Identifier,
    Model,
    Support,
    Task,
    has_control_characters,
)
from yorunge.domain.state import canonical_uuid

PositiveInt64 = Annotated[int, Field(ge=1, le=2**63 - 1)]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Permission = Annotated[
    str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:/-]*$")
]
OpaqueText = Annotated[str, Field(min_length=1, max_length=256)]
MAX_RECORD_BYTES = 32768
TTL: dict[Support, int] = {
    "supported": 300,
    "unsupported": 300,
    "requires_access": 60,
    "unknown": 30,
}
Freshness = Literal["fresh", "miss", "stale", "clock_anomaly", "historical_only"]


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("UTC required")
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


@lru_cache(maxsize=4096)
def instant(value: str) -> datetime:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z", value, flags=re.ASCII):
        raise ValueError("canonical UTC required")
    result = datetime.fromisoformat(value)
    if timestamp(result) != value:
        raise ValueError("canonical UTC required")
    return result


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate wire key")
    return result


def _reject_constant(value: str) -> object:
    raise ValueError("finite JSON required")


class JsonWireModel(Model):
    _scalar_json: ClassVar[bool] = False

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        # Pydantic's JSON parser accepts duplicate keys; v2 wire does not.
        text = json_data if isinstance(json_data, str) else json_data.decode("utf-8")
        text.encode("utf-8", errors="strict")
        decoded = json.loads(
            text, object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
        if cls._scalar_json:
            # Scalar-only records have identical strict Python/JSON field types.
            return super().model_validate(
                decoded,
                strict=strict,
                extra=extra,
                context=context,
                by_alias=by_alias,
                by_name=by_name,
            )
        return super().model_validate_json(
            text,
            strict=strict,
            extra=extra,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )


class WireModel(JsonWireModel):
    @field_validator("*", mode="after")
    @classmethod
    def unicode_text(cls, value: object) -> object:
        if isinstance(value, str):
            if has_control_characters(value) or len(value.encode("utf-8", errors="strict")) > 2048:
                raise ValueError("bounded Unicode text required")
        return value


class ResourceGrant(WireModel):
    namespace: Identifier
    resource_type: Identifier
    resource_id: OpaqueText
    permissions: Annotated[tuple[Permission, ...], Field(max_length=128)]

    @field_validator("permissions")
    @classmethod
    def ordered(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if tuple(sorted(set(value))) != value:
            raise ValueError("canonical permission order required")
        return value

    @field_validator("resource_id")
    @classmethod
    def size(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 1024:
            raise ValueError("text too long")
        return value


class AuthorizationScope(WireModel):
    permissions: Annotated[tuple[Permission, ...], Field(max_length=128)]
    resources: Annotated[tuple[ResourceGrant, ...], Field(max_length=128)]

    @model_validator(mode="after")
    def ordered(self) -> AuthorizationScope:
        keys = tuple((r.namespace, r.resource_type, r.resource_id) for r in self.resources)
        if (
            tuple(sorted(set(self.permissions))) != self.permissions
            or tuple(sorted(set(keys))) != keys
        ):
            raise ValueError("canonical grant order required")
        if (
            len(self.permissions)
            + len(self.resources)
            + sum(len(r.permissions) for r in self.resources)
            > 128
        ):
            raise ValueError("too many grants")
        return self


class ModelBinding(WireModel):
    source: Identifier
    id: OpaqueText
    revision: OpaqueText | None
    content_digest: Digest | None


class ToolBinding(WireModel):
    id: Identifier
    version: OpaqueText | None
    executable_digest: Digest | None
    environment_digest: Digest | None


class ExecutionBinding(WireModel):
    backend: Execution
    runtime_id: OpaqueText | None
    runtime_revision: OpaqueText | None
    environment_digest: Digest | None

    @model_validator(mode="after")
    def pair(self) -> ExecutionBinding:
        if (self.runtime_id is None) != (self.runtime_revision is None):
            raise ValueError("runtime pair required")
        return self


class CapabilityScopeV2(WireModel):
    schema_version: Literal[2]
    store_id: str
    identity_epoch: str
    clock_generation: PositiveInt64
    service_id: Literal["local", "evren-platform", "evren-llm"]
    service_origin: str | None
    api_base_path: str | None
    account_id: Identifier | None
    project_id: Identifier | None
    credential_id: str | None
    credential_revision: PositiveInt64 | None
    authorization_scope: AuthorizationScope | None
    model: ModelBinding | None
    tool: ToolBinding | None
    execution: ExecutionBinding

    @field_validator("store_id", "identity_epoch", "credential_id")
    @classmethod
    def uuid(cls, value: str | None) -> str | None:
        return None if value is None else canonical_uuid(value)

    @model_validator(mode="after")
    def consistent(self) -> CapabilityScopeV2:
        if (self.credential_id is None) != (self.credential_revision is None):
            raise ValueError("credential pair required")
        if self.service_id == "local":
            if any(
                v is not None
                for v in (
                    self.service_origin,
                    self.api_base_path,
                    self.credential_id,
                    self.authorization_scope,
                )
            ):
                raise ValueError("local scope cannot claim remote authority")
        else:
            if self.service_origin is None or self.api_base_path is None:
                raise ValueError("target required")
            target = normalize_target(self.service_origin + self.api_base_path)
            if (
                target.service_origin != self.service_origin
                or target.api_base_path != self.api_base_path
            ):
                raise ValueError("canonical target required")
            if self.authorization_scope is not None and self.credential_id is None:
                raise ValueError("authorization requires credential")
        if len(canonical(self.model_dump(mode="json"))) > 16384:
            raise ValueError("scope too large")
        return self


class CapabilityKey(WireModel):
    capability_id: Identifier
    task: Task
    scope: CapabilityScopeV2

    def encoded(self) -> bytes:
        return canonical(self.model_dump(mode="json"))

    def digest(self) -> str:
        return hashlib.sha256(self.encoded()).hexdigest()

    def projection(self) -> str:
        value = self.model_dump(mode="json")
        del value["scope"]["authorization_scope"]
        return canonical(value).decode("ascii")


class Constraint(WireModel):
    name: Identifier
    value: OpaqueText | Annotated[int, Field(ge=0, le=2**63 - 1)] | bool


class Evidence(WireModel):
    kind: Literal["local_policy", "documentation", "synthetic_test", "live_account", "not_verified"]
    producer_id: Identifier
    producer_version: Identifier
    policy_version: Literal[1] = 1
    provenance: OpaqueText
    support: Support
    reason_code: Identifier
    constraints: Annotated[tuple[Constraint, ...], Field(max_length=32)] = ()
    checked_at: str
    expires_at: str

    @field_validator("policy_version", mode="before")
    @classmethod
    def integer_policy(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("integer policy version required")
        return value

    @model_validator(mode="after")
    def time_range(self) -> Evidence:
        checked, expires = instant(self.checked_at), instant(self.expires_at)
        if not timedelta(0) < expires - checked <= timedelta(seconds=TTL[self.support]):
            raise ValueError("evidence TTL outside policy")
        if len(canonical(self.model_dump(mode="json"))) > MAX_RECORD_BYTES:
            raise ValueError("evidence too large")
        return self

    def semantic_key(self) -> bytes:
        return canonical(self.model_dump(mode="json", exclude={"checked_at", "expires_at"}))


class CapabilityRecord(WireModel):
    schema_version: Literal[2] = 2
    key: CapabilityKey
    support: Support
    reason_code: Identifier
    message: OpaqueText
    evidence: Annotated[tuple[Evidence, ...], Field(max_length=8)]
    checked_at: str
    expires_at: str
    conflict_until: str | None = None

    @model_validator(mode="after")
    def valid(self) -> CapabilityRecord:
        start, end = instant(self.checked_at), instant(self.expires_at)
        if not timedelta(0) < end - start <= timedelta(seconds=TTL[self.support]):
            raise ValueError("record TTL outside policy")
        if self.evidence and (
            self.checked_at != max(e.checked_at for e in self.evidence)
            or self.expires_at > min(e.expires_at for e in self.evidence)
        ):
            raise ValueError("record cannot outlive or redate its evidence")
        decisions = {
            (e.support, canonical([c.model_dump(mode="json") for c in e.constraints]))
            for e in self.evidence
        }
        if self.support != "unknown" and (
            len(decisions) != 1 or any(e.support != self.support for e in self.evidence)
        ):
            raise ValueError("conflicting evidence must remain unknown")
        if self.conflict_until is not None:
            instant(self.conflict_until)
            if self.support != "unknown":
                raise ValueError("blocker cannot support execution")
        if self.support == "supported":
            self._validate_support()
        if len(canonical(self.model_dump(mode="json"))) > MAX_RECORD_BYTES:
            raise ValueError("record too large")
        return self

    def _validate_support(self) -> None:
        if not self.evidence or any(e.support != "supported" for e in self.evidence):
            raise ValueError("supported requires consistent evidence")
        if self.key.scope.service_id != "local" and (
            self.key.scope.authorization_scope is None
            or self.key.scope.credential_id is None
            or self.key.scope.account_id is None
            or any(e.kind != "live_account" for e in self.evidence)
        ):
            raise ValueError("remote support requires scoped live authority")
        if any(
            e.kind in ("not_verified", "synthetic_test", "documentation") for e in self.evidence
        ):
            raise ValueError("insufficient support evidence")

    def pinned_until(self, at: str | None = None) -> str | None:
        evidence = tuple(
            e for e in self.evidence if at is None or e.checked_at <= at < e.expires_at
        )
        signatures = {
            (e.support, canonical([c.model_dump(mode="json") for c in e.constraints]))
            for e in evidence
        }
        dates = [e.expires_at for e in evidence] if len(signatures) > 1 else []
        if self.conflict_until and (at is None or self.conflict_until > at):
            dates.append(self.conflict_until)
        return max(dates) if dates else None


class CachedCapability(WireModel):
    key: CapabilityKey
    hit: bool
    freshness: Freshness
    effective_support: Support
    reason_code: Identifier
    message: OpaqueText
    checked_at: str
    valid_until: str | None
    record: CapabilityRecord | None
    historical_candidates: Annotated[tuple[CapabilityRecord, ...], Field(max_length=4)] = ()


class CachedCapabilityView(WireModel):
    records: tuple[CachedCapability, ...]
