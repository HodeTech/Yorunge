from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from typing import Literal
from uuid import UUID

from pydantic import ConfigDict, field_validator

from yorunge.domain.models import Model


@lru_cache(maxsize=4096)
def canonical_uuid(value: str) -> str:
    parsed = UUID(value)
    if parsed.version != 4 or str(parsed) != value:
        raise ValueError("canonical UUIDv4 required")
    return value


def check_utc(value: object) -> None:
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError("UTC timestamp required")
    timestamp = datetime.fromisoformat(value)
    if timestamp.utcoffset() != UTC.utcoffset(timestamp):
        raise ValueError("UTC timestamp required")


class StateInfo(Model):
    model_config = ConfigDict(defer_build=True)

    schema_version: Literal[1] = 1
    store_schema_version: int
    store_id: str
    identity_epoch: str

    @field_validator("store_id", "identity_epoch")
    @classmethod
    def uuid_value(cls, value: str) -> str:
        return canonical_uuid(value)
