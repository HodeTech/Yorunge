from __future__ import annotations

from types import UnionType
from typing import (
    Annotated,
    Generic,
    Literal,
    TypeAlias,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

from pydantic import BaseModel, Field, field_validator, model_validator

from yorunge.domain.errors import (
    MESSAGES,
    ApprovalNotEffective,
    ErrorCode,
    OperationError,
    YorungeError,
)
from yorunge.domain.models import Model, Result
from yorunge.domain.state import canonical_uuid
from yorunge.domain.wire_limits import JSON_LIMIT

MAX_SEQUENCE = 2**63 - 1
Sequence = Annotated[int, Field(ge=1, le=MAX_SEQUENCE)]
Counter = Annotated[int, Field(ge=0, le=MAX_SEQUENCE)]
CapacityKind = Literal["store", "attempt", "transition"]
T = TypeVar("T", bound=BaseModel)


class EventMeta(Model):
    schema_version: Literal[1]
    stream_id: str
    sequence: Sequence
    event: Literal["progress", "result", "error"]
    operation_id: str | None

    @field_validator("stream_id", "operation_id")
    @classmethod
    def uuid_value(cls, value: str | None) -> str | None:
        return canonical_uuid(value) if value is not None else None


class ProgressPayload(Model):
    stage: Literal["connecting", "receiving", "validating"]
    completed: Counter
    total: Counter | None

    @model_validator(mode="after")
    def bounded_progress(self) -> ProgressPayload:
        if self.total is not None and self.completed > self.total:
            raise ValueError("completed must not exceed total")
        return self


class EmptyErrorDetails(Model):
    pass


class OperationErrorDetails(Model):
    reason_code: ErrorCode
    capacity_kind: CapacityKind | None


class ApprovalErrorDetails(Model):
    plan_id: str
    approval_id: str
    recorded: Literal[True]
    reason_code: ErrorCode

    @field_validator("plan_id", "approval_id")
    @classmethod
    def uuid_value(cls, value: str) -> str:
        return canonical_uuid(value)

    @field_validator("recorded", mode="before")
    @classmethod
    def boolean_recorded(cls, value: object) -> object:
        if type(value) is not bool:
            raise ValueError("boolean recorded flag required")
        return value


ErrorDetails: TypeAlias = EmptyErrorDetails | OperationErrorDetails | ApprovalErrorDetails


class ErrorEnvelope(Model):
    """Closed error wire with a message rebuilt from trusted local definitions."""

    schema_version: Literal[1]
    code: ErrorCode
    message: Annotated[str, Field(max_length=JSON_LIMIT)]
    operation_id: str | None
    retryable: Literal[False]
    details: ErrorDetails

    @field_validator("operation_id")
    @classmethod
    def uuid_value(cls, value: str | None) -> str | None:
        return canonical_uuid(value) if value is not None else None

    @field_validator("retryable", mode="before")
    @classmethod
    def boolean_retryable(cls, value: object) -> object:
        if type(value) is not bool:
            raise ValueError("boolean retryable flag required")
        return value

    @field_validator("message")
    @classmethod
    def utf8_message(cls, value: str) -> str:
        try:
            encoded = value.encode("utf-8", "strict")
        except UnicodeError:
            raise ValueError("UTF-8 message required") from None
        if len(encoded) > JSON_LIMIT:
            raise ValueError("bounded message required")
        return value

    @model_validator(mode="after")
    def local_error(self) -> ErrorEnvelope:
        message = MESSAGES[self.code]
        if isinstance(self.details, OperationErrorDetails):
            if (self.details.capacity_kind is not None) != (
                self.code == "operation_capacity_exceeded"
            ):
                raise ValueError("capacity kind required only for capacity errors")
        elif isinstance(self.details, ApprovalErrorDetails):
            if self.code != "plan_not_valid" or self.operation_id is not None:
                raise ValueError("approval details require an unbound approval error")
            message = ApprovalNotEffective(
                self.details.plan_id, self.details.approval_id, self.details.reason_code
            ).message
        elif self.operation_id is not None:
            raise ValueError("bound error requires operation details")
        object.__setattr__(self, "message", message)
        return self


class ProgressEvent(EventMeta):
    event: Literal["progress"]
    payload: ProgressPayload


class ResultEvent(EventMeta, Generic[T]):
    event: Literal["result"]
    payload: Result[T]

    @model_validator(mode="after")
    def concrete_result_type(self) -> ResultEvent[T]:
        _result_model_type(type(self))
        return self


class ErrorEvent(EventMeta):
    event: Literal["error"]
    payload: ErrorEnvelope

    @model_validator(mode="after")
    def consistent_operation(self) -> ErrorEvent:
        if self.operation_id != self.payload.operation_id:
            raise ValueError("event and error operation identities must match")
        return self


StreamEvent: TypeAlias = ProgressEvent | ResultEvent[T] | ErrorEvent


def _concrete_data_type(annotation: object) -> bool:
    if get_origin(annotation) in (Union, UnionType):
        return all(_concrete_data_type(member) for member in get_args(annotation))
    return (
        isinstance(annotation, type)
        and issubclass(annotation, BaseModel)
        and annotation is not BaseModel
    )


def _result_model_type(model: type[BaseModel]) -> type[BaseModel]:
    arguments = model.__pydantic_generic_metadata__["args"]
    if len(arguments) != 1 or not _concrete_data_type(arguments[0]):
        raise ValueError("concrete result data model required")
    # Pydantic's generic schema parameter also accepts a union of model types.
    # Keep it intact; inferring type(result.data) would widen serialization.
    return cast(type[BaseModel], arguments[0])


def result_event(
    result: Result[T],
    *,
    stream_id: str,
    sequence: int = 1,
    operation_id: str | None = None,
) -> ResultEvent[T]:
    """Preserve the original Result specialization, including its serialization scope."""
    model = _result_model_type(type(result))
    event_type = cast(type[ResultEvent[T]], ResultEvent.__class_getitem__(model))
    return event_type(
        schema_version=1,
        stream_id=stream_id,
        sequence=sequence,
        event="result",
        operation_id=operation_id,
        payload=result,
    )


def error_payload(error: YorungeError, *, operation_id: str | None = None) -> ErrorEnvelope:
    """Keep known context without accepting a provider message or relabeling a job."""
    details: ErrorDetails
    if isinstance(error, OperationError):
        if error.operation_id is not None:
            if operation_id is not None and error.operation_id != operation_id:
                raise ValueError("conflicting operation identities")
            operation_id = error.operation_id
        details = OperationErrorDetails(
            reason_code=error.reason_code, capacity_kind=error.capacity_kind
        )
    elif isinstance(error, ApprovalNotEffective) and operation_id is None:
        details = ApprovalErrorDetails(
            plan_id=error.plan_id,
            approval_id=error.approval_id,
            recorded=True,
            reason_code=error.reason,
        )
    elif operation_id is None:
        details = EmptyErrorDetails()
    else:
        details = OperationErrorDetails(reason_code=error.code, capacity_kind=None)
    return ErrorEnvelope(
        schema_version=1,
        code=error.code,
        message=MESSAGES[error.code],
        operation_id=operation_id,
        retryable=False,
        details=details,
    )
