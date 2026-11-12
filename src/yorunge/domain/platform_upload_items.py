"""Bounded reported item metadata; nullable remote hash is never invented."""

from typing import Annotated, ClassVar, Self

from pydantic import Field, field_validator, model_validator

from yorunge.domain.dataset_manifest import Sha256, file_parts, safe_text
from yorunge.domain.dataset_upload import NonnegativeInt64, UploadWire, provider_uuid


class ProviderItem(UploadWire):
    id: str
    dataset_id: str
    original_filename: str
    file_size_bytes: Annotated[int, Field(ge=0, le=500_000_000)]
    sha256_hash: Sha256 | None

    @field_validator("id", "dataset_id")
    @classmethod
    def identifier(cls, value: str) -> str:
        return provider_uuid(value)

    @field_validator("original_filename")
    @classmethod
    def path(cls, value: str) -> str:
        file_parts(value)
        return value


class ProviderItemsPage(UploadWire):
    """One listing page whose cross-item consistency is judged by the inventory reducer."""

    max_wire_bytes: ClassVar[int] = 1024 * 1024
    items: Annotated[tuple[ProviderItem, ...], Field(max_length=128)]
    next_cursor: str | None
    total: NonnegativeInt64

    @field_validator("next_cursor")
    @classmethod
    def cursor(cls, value: str | None) -> str | None:
        if value is not None and not 1 <= len(safe_text(value)) <= 1024:
            raise ValueError("bounded opaque cursor required")
        return value


class ProviderItems(ProviderItemsPage):
    @model_validator(mode="after")
    def distinct(self) -> Self:
        if (
            self.total < len(self.items)
            or len({item.id for item in self.items}) != len(self.items)
            or len({item.original_filename for item in self.items}) != len(self.items)
        ):
            raise ValueError("distinct consistent item page required")
        return self
