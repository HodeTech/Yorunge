"""Private consumed Platform fields; reported context never grants authority."""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import Field, field_validator

from yorunge.domain.dataset_manifest import safe_text
from yorunge.domain.dataset_upload import UploadWire, provider_uuid


class ProviderProject(UploadWire):
    id: str
    owner_id: str
    org_id: str | None
    visibility: Literal["private"]

    @field_validator("id", "owner_id", "org_id")
    @classmethod
    def identifier(cls, value: str | None) -> str | None:
        return None if value is None else provider_uuid(value)


class ProviderDatasetMetadata(ProviderProject):
    name: Annotated[str, Field(min_length=2, max_length=128)]
    modality: Literal["VISION", "AUDIO", "NLP", "MULTIMODAL", "MEDICAL"]

    @field_validator("name")
    @classmethod
    def dataset_name(cls, value: str) -> str:
        if value != value.strip() or len(safe_text(value)) > 256:
            raise ValueError("bounded unmodified dataset name required")
        return value


class ProviderDataset(ProviderDatasetMetadata):
    contributions_enabled: Literal[False]

    @field_validator("contributions_enabled", mode="before")
    @classmethod
    def strict_false(cls, value: object) -> object:
        if type(value) is not bool:
            raise ValueError("strict contribution policy required")
        return value


class LocatedDataset(ProviderDatasetMetadata):
    # A list locator does not assert the detail-only contribution policy.
    owner_username: str
    slug: str

    @field_validator("owner_username", "slug")
    @classmethod
    def segment(cls, value: str) -> str:
        if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value, flags=re.ASCII) is None:
            raise ValueError("single bounded provider segment required")
        return value


class ProviderRole(UploadWire):
    role: Annotated[str, Field(min_length=1, max_length=64)]
    permissions: Annotated[tuple[str, ...], Field(max_length=32)]

    @field_validator("role")
    @classmethod
    def role_text(cls, value: str) -> str:
        safe_text(value)
        return value

    @field_validator("permissions")
    @classmethod
    def permission_labels(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("distinct permission labels required")
        for value in values:
            if not value.isascii() or not 1 <= len(value) <= 64:
                raise ValueError("bounded ASCII permission label required")
            safe_text(value)
        return values
