from __future__ import annotations

import json
from typing import cast

import pytest
from pydantic import TypeAdapter, ValidationError

from yorunge.domain.errors import (
    MESSAGES,
    ApprovalNotEffective,
    ErrorCode,
    OperationError,
    YorungeError,
)
from yorunge.domain.models import Model, Result
from yorunge.domain.streams import (
    MAX_SEQUENCE,
    ApprovalErrorDetails,
    CapacityKind,
    EmptyErrorDetails,
    ErrorEnvelope,
    ErrorEvent,
    EventMeta,
    OperationErrorDetails,
    ProgressEvent,
    ProgressPayload,
    ResultEvent,
    error_payload,
    result_event,
)
from yorunge.domain.wire_limits import JSON_LIMIT

STREAM_ID = "09507038-0ec3-47ca-a6a0-c1ee128cfbdc"
OPERATION_ID = "885cbbda-530b-4f80-b189-93759b0347fe"
OTHER_ID = "9291b0ef-b8cb-4d95-95ac-cb7e9ea45c90"
PRIVATE_MESSAGE = "provider-body-private-canary"


class Item(Model):
    value: str


def metadata(event: str = "progress", operation_id: str | None = None) -> dict[str, object]:
    return {
        "schema_version": 1,
        "stream_id": STREAM_ID,
        "sequence": 1,
        "event": event,
        "operation_id": operation_id,
    }


def progress() -> dict[str, object]:
    return {**metadata(), "payload": {"stage": "receiving", "completed": 1, "total": 2}}


def result() -> dict[str, object]:
    payload = Result[Item](data=Item(value="Türkçe sonuç")).model_dump(mode="json")
    return {**metadata("result"), "payload": payload}


def envelope() -> dict[str, object]:
    return YorungeError("invalid_response").envelope()


@pytest.mark.parametrize("event", ["progress", "result", "error"])
def test_metadata_has_a_closed_required_wire(event: str) -> None:
    data = metadata(event)
    parsed = EventMeta.model_validate(data)
    assert parsed.model_dump(mode="json") == data
    with pytest.raises(ValidationError):
        EventMeta.model_validate({**data, "provider": PRIVATE_MESSAGE})
    for key in data:
        incomplete = {name: value for name, value in data.items() if name != key}
        with pytest.raises(ValidationError):
            EventMeta.model_validate(incomplete)


@pytest.mark.parametrize("value", [True, False, 1.0, "1", None, 0, 2])
def test_metadata_schema_version_is_exact_integer_one(value: object) -> None:
    payload = {**metadata(), "schema_version": value}
    with pytest.raises(ValidationError):
        EventMeta.model_validate(payload)


@pytest.mark.parametrize("value", [True, False, 1.0, "1", None, 0, -1, 2**63])
def test_sequence_is_a_bounded_strict_positive_integer(value: object) -> None:
    payload = {**metadata(), "sequence": value}
    with pytest.raises(ValidationError):
        EventMeta.model_validate(payload)


def test_sequence_accepts_both_closed_boundaries() -> None:
    assert EventMeta.model_validate(metadata()).sequence == 1
    value = EventMeta.model_validate({**metadata(), "sequence": MAX_SEQUENCE})
    assert value.sequence == MAX_SEQUENCE


@pytest.mark.parametrize("field", ["stream_id", "operation_id"])
@pytest.mark.parametrize(
    "value",
    [
        "not-a-uuid",
        "09507038-0ec3-17ca-a6a0-c1ee128cfbdc",
        STREAM_ID.upper(),
        STREAM_ID.replace("-", ""),
        "{" + STREAM_ID + "}",
        1,
        True,
    ],
)
def test_metadata_requires_canonical_uuid_v4(field: str, value: object) -> None:
    payload = {**metadata(), field: value}
    with pytest.raises(ValidationError):
        EventMeta.model_validate(payload)


def test_operation_id_is_nullable_but_stream_id_is_not() -> None:
    assert EventMeta.model_validate(metadata()).operation_id is None
    parsed = EventMeta.model_validate(metadata(operation_id=OPERATION_ID))
    assert parsed.operation_id == OPERATION_ID
    payload = {**metadata(), "stream_id": None}
    with pytest.raises(ValidationError):
        EventMeta.model_validate(payload)


@pytest.mark.parametrize("value", ["message", "completed", "", 1, None])
def test_event_kind_is_closed(value: object) -> None:
    payload = {**metadata(), "event": value}
    with pytest.raises(ValidationError):
        EventMeta.model_validate(payload)


@pytest.mark.parametrize("stage", ["connecting", "receiving", "validating"])
def test_progress_is_bounded_metadata_without_provider_text(stage: str) -> None:
    parsed = ProgressPayload.model_validate({"stage": stage, "completed": 0, "total": None})
    assert parsed.completed == 0
    assert parsed.total is None
    upper = ProgressPayload(stage="receiving", completed=MAX_SEQUENCE, total=MAX_SEQUENCE)
    assert upper.completed == upper.total
    assert ProgressEvent.model_validate(progress()).payload.completed == 1


@pytest.mark.parametrize("field", ["completed", "total"])
@pytest.mark.parametrize("value", [True, False, 1.0, "1", -1, 2**63])
def test_progress_counters_are_strict_and_bounded(field: str, value: object) -> None:
    data = {"stage": "receiving", "completed": 0, "total": MAX_SEQUENCE}
    with pytest.raises(ValidationError):
        ProgressPayload.model_validate({**data, field: value})


@pytest.mark.parametrize(
    "data",
    [
        {"stage": "receiving", "completed": 2, "total": 1},
        {"stage": "provider_message", "completed": 1, "total": 2},
        {"stage": "receiving", "completed": 1},
        {"stage": "receiving", "completed": None, "total": None},
        {"stage": "receiving", "completed": 1, "total": 2, "message": PRIVATE_MESSAGE},
    ],
)
def test_progress_rejects_invalid_shape_or_completion(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ProgressPayload.model_validate(data)


def test_result_keeps_v1_payload_and_distinct_outer_operation_context() -> None:
    data = {**result(), "operation_id": OPERATION_ID}
    event = ResultEvent[Item].model_validate_json(json.dumps(data))
    assert event.operation_id == OPERATION_ID
    assert event.payload.operation_id is None
    assert event.payload.status == "completed"
    assert event.payload.model_dump(mode="json") == data["payload"]
    assert event.payload.model_dump(mode="json") == {
        "schema_version": 1,
        "operation_id": None,
        "status": "completed",
        "data": {"value": "Türkçe sonuç"},
        "warnings": [],
    }


def test_result_factory_preserves_real_context_plan_and_jobs_payloads() -> None:
    from yorunge import api
    from yorunge.domain.operations import JobsPage

    originals = (
        api.show_context(),
        api.prepare_plan(task="llm.train"),
        Result[JobsPage](data=JobsPage(jobs=(), next_cursor=None)),
    )
    for original in originals:
        event = result_event(original, stream_id=STREAM_ID, operation_id=OPERATION_ID)
        assert json.loads(event.model_dump_json())["payload"] == json.loads(
            original.model_dump_json()
        )
        assert event.operation_id == OPERATION_ID
        assert event.sequence == 1


def test_result_factory_preserves_warnings_and_original_declared_serialization_scope() -> None:
    class PrivateItem(Item):
        private: str

    original = Result[Item](
        data=PrivateItem(value="visible", private=PRIVATE_MESSAGE), warnings=("yerel uyarı",)
    )
    event = result_event(original, stream_id=STREAM_ID, sequence=MAX_SEQUENCE)
    encoded = event.model_dump_json()
    assert event.sequence == MAX_SEQUENCE
    assert PRIVATE_MESSAGE not in encoded
    assert json.loads(encoded)["payload"] == json.loads(original.model_dump_json())
    assert event.payload.warnings == ("yerel uyarı",)


def test_result_factory_keeps_declared_model_union_and_subclass_privacy() -> None:
    from yorunge.application.stream_results import encode_event

    class Alternative(Model):
        other: str

    class PrivateItem(Item):
        private: str

    original = Result[Item | Alternative](data=PrivateItem(value="public", private=PRIVATE_MESSAGE))
    event = result_event(original, stream_id=STREAM_ID)
    assert type(event).__pydantic_generic_metadata__["args"] == (Item | Alternative,)
    assert event.payload.model_dump(mode="json") == original.model_dump(mode="json")
    encoded = encode_event(event)
    assert json.loads(encoded)["payload"] == original.model_dump(mode="json")
    assert PRIVATE_MESSAGE not in encoded.decode()


def test_unparameterized_result_cannot_silently_erase_data_fields() -> None:
    from pydantic import BaseModel

    original = Result[Item](data=Item(value="must survive"))
    payload = {**metadata("result"), "payload": original}
    with pytest.raises(ValidationError, match="concrete result data model required"):
        ResultEvent.model_validate(payload)
    payload = {**metadata("result"), "payload": original}
    with pytest.raises(ValidationError, match="concrete result data model required"):
        ResultEvent[BaseModel].model_validate(payload)
    untyped_result = Result(data=original.data)
    with pytest.raises(ValueError, match="concrete result data model required"):
        result_event(untyped_result, stream_id=STREAM_ID)


@pytest.mark.parametrize("alternative", [None, dict])
def test_model_union_cannot_add_an_untyped_payload_branch(alternative: object) -> None:
    annotation = Item | (type(None) if alternative is None else alternative)
    raw = Result[annotation].model_construct(data=Item(value="public"))
    with pytest.raises(ValueError, match="concrete result data model required"):
        result_event(raw, stream_id=STREAM_ID)


@pytest.mark.parametrize(
    "arguments",
    [
        {"stream_id": "not-a-uuid"},
        {"stream_id": STREAM_ID, "sequence": True},
        {"stream_id": STREAM_ID, "sequence": 1.0},
        {"stream_id": STREAM_ID, "sequence": 0},
        {"stream_id": STREAM_ID, "operation_id": "not-a-uuid"},
    ],
)
def test_result_factory_enforces_the_same_metadata_contract(arguments: dict[str, object]) -> None:
    original = Result[Item](data=Item(value="must survive"))
    with pytest.raises(ValidationError):
        result_event(original, **arguments)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("operation_id", OPERATION_ID),
        ("status", "running"),
        ("schema_version", True),
        ("schema_version", 1.0),
        ("data", {"value": 1}),
        ("data", {"value": "ok", "provider": PRIVATE_MESSAGE}),
        ("provider", PRIVATE_MESSAGE),
    ],
)
def test_result_event_requires_existing_typed_result(key: str, value: object) -> None:
    data = result()
    payload = cast(dict[str, object], data["payload"])
    data["payload"] = {**payload, key: value}
    raw = json.dumps(data)
    with pytest.raises(ValidationError):
        ResultEvent[Item].model_validate_json(raw)


@pytest.mark.parametrize(
    ("model", "data"),
    [
        (ProgressEvent, {**progress(), "event": "result"}),
        (ProgressEvent, result()),
        (ResultEvent[Item], progress()),
        (ErrorEvent, {**progress(), "event": "error"}),
    ],
)
def test_tags_cannot_relabel_other_payloads(model: type[Model], data: dict[str, object]) -> None:
    raw = json.dumps(data)
    with pytest.raises(ValidationError):
        model.model_validate_json(raw)


def test_union_selects_only_the_expected_event_variant() -> None:
    adapter = TypeAdapter(ProgressEvent | ResultEvent[Item] | ErrorEvent)
    first = adapter.validate_json(json.dumps(progress()))
    second = adapter.validate_json(json.dumps(result()))
    third = adapter.validate_json(json.dumps({**metadata("error"), "payload": envelope()}))
    assert isinstance(first, ProgressEvent)
    assert isinstance(second, ResultEvent)
    assert isinstance(third, ErrorEvent)


@pytest.mark.parametrize("code", list(MESSAGES))
def test_all_existing_plain_error_envelopes_are_preserved(code: ErrorCode) -> None:
    error = YorungeError(code)
    payload = error_payload(error)
    assert isinstance(payload.details, EmptyErrorDetails)
    assert payload.model_dump(mode="json") == error.envelope()


@pytest.mark.parametrize("capacity_kind", ["store", "attempt", "transition"])
def test_operation_capacity_context_is_preserved(capacity_kind: str) -> None:
    error = OperationError(
        "operation_capacity_exceeded",
        OPERATION_ID,
        capacity_kind=cast(CapacityKind, capacity_kind),
    )
    payload = error_payload(error)
    assert isinstance(payload.details, OperationErrorDetails)
    assert payload.model_dump(mode="json") == error.envelope()


@pytest.mark.parametrize("operation_id", [None, OPERATION_ID])
def test_operation_error_preserves_reason_and_optional_identity(operation_id: str | None) -> None:
    error = OperationError("operation_uncertain", operation_id, reason_code="transport_timeout")
    assert error_payload(error).model_dump(mode="json") == error.envelope()


def test_approval_error_preserves_committed_record_and_custom_local_message() -> None:
    error = ApprovalNotEffective(STREAM_ID, OTHER_ID, "state_changed")
    payload = error_payload(error)
    assert isinstance(payload.details, ApprovalErrorDetails)
    assert payload.model_dump(mode="json") == error.envelope()
    assert payload.message != MESSAGES["plan_not_valid"]


def test_binding_generic_error_uses_operation_shape_without_changing_code_or_exit() -> None:
    error = YorungeError("stream_interrupted")
    payload = error_payload(error, operation_id=OPERATION_ID)
    expected = OperationError("stream_interrupted", OPERATION_ID)
    assert payload.model_dump(mode="json") == expected.envelope()
    assert error.exit_code == expected.exit_code


def test_binding_approval_failure_keeps_the_code_and_uses_operation_context() -> None:
    error = ApprovalNotEffective(STREAM_ID, OTHER_ID, "state_changed")
    payload = error_payload(error, operation_id=OPERATION_ID)
    expected = OperationError("plan_not_valid", OPERATION_ID)
    assert payload.model_dump(mode="json") == expected.envelope()


def test_existing_operation_identity_cannot_be_relabelled() -> None:
    error = OperationError("operation_uncertain", OPERATION_ID)
    assert error_payload(error, operation_id=OPERATION_ID).operation_id == OPERATION_ID
    with pytest.raises(ValueError, match="conflicting operation identities"):
        error_payload(error, operation_id=OTHER_ID)


def test_factory_never_copies_mutated_message_or_calls_an_overridden_envelope() -> None:
    class ProviderError(YorungeError):
        def envelope(self) -> dict[str, object]:
            raise AssertionError("untrusted envelope must not be invoked")

    error = ProviderError("remote_failed")
    error.message = PRIVATE_MESSAGE
    payload = error_payload(error)
    assert payload.message == MESSAGES["remote_failed"]
    assert PRIVATE_MESSAGE not in payload.model_dump_json()


@pytest.mark.parametrize("kind", ["plain", "operation", "approval"])
def test_decoded_error_message_is_rebuilt_locally(kind: str) -> None:
    error: YorungeError
    if kind == "approval":
        error = ApprovalNotEffective(STREAM_ID, OTHER_ID, "state_changed")
    elif kind == "operation":
        error = OperationError("operation_uncertain", OPERATION_ID, reason_code="invalid_response")
    else:
        error = YorungeError("remote_failed")
    data = {**error.envelope(), "message": PRIVATE_MESSAGE}
    payload = ErrorEnvelope.model_validate_json(json.dumps(data))
    assert payload.model_dump(mode="json") == error.envelope()
    assert PRIVATE_MESSAGE not in payload.model_dump_json()


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("schema_version", True),
        ("schema_version", 1.0),
        ("schema_version", 2),
        ("code", "provider_unavailable"),
        ("code", "unknown_remote_code"),
        ("retryable", True),
        ("retryable", 0),
        ("retryable", 1),
        ("message", None),
        ("message", {"provider": PRIVATE_MESSAGE}),
        ("message", "\ud800"),
        ("message", "a" * (JSON_LIMIT + 1)),
        ("message", "ü" * (JSON_LIMIT // 2 + 1)),
        ("operation_id", "not-a-uuid"),
        ("operation_id", OPERATION_ID),
        ("provider", PRIVATE_MESSAGE),
    ],
)
def test_error_envelope_rejects_untrusted_shape_or_types(key: str, value: object) -> None:
    payload = {**envelope(), key: value}
    with pytest.raises(ValidationError):
        ErrorEnvelope.model_validate(payload)


@pytest.mark.parametrize("key", list(envelope()))
def test_error_wire_has_no_optional_omitted_fields(key: str) -> None:
    data = {name: value for name, value in envelope().items() if name != key}
    with pytest.raises(ValidationError):
        ErrorEnvelope.model_validate(data)


@pytest.mark.parametrize(
    "details",
    [
        {"provider": PRIVATE_MESSAGE},
        {"reason_code": "state_changed"},
        {"capacity_kind": None},
        {"reason_code": "provider_unavailable", "capacity_kind": None},
        {"reason_code": "state_changed", "capacity_kind": "slot"},
        {"reason_code": "state_changed", "capacity_kind": None, "provider": PRIVATE_MESSAGE},
        {"reason_code": "state_changed", "capacity_kind": "store"},
        [],
        None,
    ],
)
def test_error_details_are_closed_and_reason_codes_are_not_operation_reasons(
    details: object,
) -> None:
    payload = {**envelope(), "details": details}
    with pytest.raises(ValidationError):
        ErrorEnvelope.model_validate(payload)


def test_capacity_context_requires_a_specific_kind() -> None:
    data = {**envelope(), "code": "operation_capacity_exceeded"}
    with pytest.raises(ValidationError):
        ErrorEnvelope.model_validate(
            {**data, "details": {"reason_code": "state_changed", "capacity_kind": None}}
        )


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("recorded", 1),
        ("recorded", False),
        ("plan_id", "not-a-uuid"),
        ("approval_id", STREAM_ID.upper()),
        ("reason_code", "provider_unavailable"),
        ("provider", PRIVATE_MESSAGE),
    ],
)
def test_approval_details_are_strict_and_closed(key: str, value: object) -> None:
    error = ApprovalNotEffective(STREAM_ID, OTHER_ID)
    data = error.envelope()
    details = cast(dict[str, object], data["details"])
    with pytest.raises(ValidationError):
        ErrorEnvelope.model_validate({**data, "details": {**details, key: value}})


@pytest.mark.parametrize(
    ("code", "operation_id"), [("remote_failed", None), ("plan_not_valid", OPERATION_ID)]
)
def test_approval_details_cannot_be_used_by_a_different_error_kind(
    code: str, operation_id: str | None
) -> None:
    data = ApprovalNotEffective(STREAM_ID, OTHER_ID).envelope()
    with pytest.raises(ValidationError):
        ErrorEnvelope.model_validate({**data, "code": code, "operation_id": operation_id})


@pytest.mark.parametrize(
    ("outer_id", "inner_id"),
    [(None, OPERATION_ID), (OPERATION_ID, None), (OPERATION_ID, OTHER_ID)],
)
def test_error_event_cannot_change_or_drop_operation_context(
    outer_id: str | None, inner_id: str | None
) -> None:
    error = OperationError("invalid_response", inner_id)
    data = {**metadata("error", outer_id), "payload": error.envelope()}
    raw = json.dumps(data)
    with pytest.raises(ValidationError):
        ErrorEvent.model_validate_json(raw)


@pytest.mark.parametrize("operation_id", [None, OPERATION_ID])
def test_error_event_keeps_matching_operation_context(operation_id: str | None) -> None:
    payload = error_payload(YorungeError("invalid_response"), operation_id=operation_id)
    data = {**metadata("error", operation_id), "payload": payload.model_dump(mode="json")}
    event = ErrorEvent.model_validate_json(json.dumps(data))
    assert event.operation_id == operation_id
    assert event.payload.operation_id == operation_id
