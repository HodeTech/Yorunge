from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import field_validator

from yorunge.domain.models import Model


def canonical_uuid(value: str) -> str:
    parsed = UUID(value)
    if parsed.version != 4 or str(parsed) != value:
        raise ValueError("canonical UUIDv4 required")
    return value


class StateInfo(Model):
    schema_version: Literal[1] = 1
    store_schema_version: int
    store_id: str
    identity_epoch: str

    @field_validator("store_id", "identity_epoch")
    @classmethod
    def uuid_value(cls, value: str) -> str:
        return canonical_uuid(value)
