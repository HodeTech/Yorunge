"""Strict local query and store/filter-bound keyset cursor; never authority."""

import base64
from typing import Annotated, Literal

from pydantic import Field, field_validator

from yorunge.domain.capabilities import canonical
from yorunge.domain.errors import YorungeError
from yorunge.domain.operations import OperationModel, OperationStatus


class JobsQuery(OperationModel):
    status: OperationStatus | None = None
    plan_id: str | None = None
    limit: Annotated[int, Field(ge=1, le=100)] = 50
    cursor: Annotated[str, Field(min_length=1, max_length=1024)] | None = None


class JobsCursor(OperationModel):
    version: Literal[1]
    store_id: str
    status: OperationStatus | None
    plan_id: str | None
    created_at: str
    operation_id: str

    @field_validator("version", mode="before")
    @classmethod
    def integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("integer cursor version required")
        return value

    def encoded(self) -> str:
        return base64.urlsafe_b64encode(canonical(self.model_dump(mode="json"))).decode("ascii")

    @classmethod
    def decode(cls, text: str) -> "JobsCursor":
        try:
            if not isinstance(text, str) or not 1 <= len(text) <= 1024:
                raise ValueError("bounded cursor required")
            value = cls.model_validate_json(base64.b64decode(text, altchars=b"-_", validate=True))
            if value.encoded() != text:
                raise ValueError("canonical cursor required")
            return value
        except (ValueError, TypeError, RecursionError):
            raise YorungeError("invalid_request") from None

    def matches(self, store_id: str, query: JobsQuery) -> bool:
        return (self.store_id, self.status, self.plan_id) == (
            store_id,
            query.status,
            query.plan_id,
        )
