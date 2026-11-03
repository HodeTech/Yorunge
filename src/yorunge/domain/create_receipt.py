"""Narrow immutable response baseline; no raw metadata or authority is persisted."""

from typing import ClassVar, Literal, Self

from pydantic import Field, field_validator, model_validator

from yorunge.domain.capabilities import instant
from yorunge.domain.dataset_upload import UploadWire, provider_uuid
from yorunge.domain.platform_upload import ProviderDataset
from yorunge.domain.state import canonical_uuid


class CreateReceiptV2(UploadWire):
    max_wire_bytes: ClassVar[int] = 2048
    schema_version: Literal[2]
    intent_id: str
    recorded_at: str
    result: Literal["accepted"]
    dataset_id: str
    object_key: None
    sent_bytes: None
    sent_sha256: None
    created_dataset: ProviderDataset = Field(repr=False)

    @field_validator("intent_id")
    @classmethod
    def identifier(cls, value: str) -> str:
        return canonical_uuid(value)

    @field_validator("dataset_id")
    @classmethod
    def dataset(cls, value: str) -> str:
        return provider_uuid(value)

    @model_validator(mode="after")
    def response_binding(self) -> Self:
        instant(self.recorded_at)
        if self.dataset_id != self.created_dataset.id:
            raise ValueError("create receipt dataset mismatch")
        self.encoded()
        return self
