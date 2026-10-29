"""Independent event byte/structure budgets, strict wire faults and provenance."""

from __future__ import annotations

import json
import warnings

import pytest
from pydantic import computed_field, field_serializer, field_validator

from yorunge.application.stream_results import decode_event, encode_event
from yorunge.domain.credentials import SecretValue
from yorunge.domain.errors import MESSAGES, ApprovalNotEffective, OperationError, YorungeError
from yorunge.domain.models import Model, Result
from yorunge.domain.streams import (
    EmptyErrorDetails,
    ErrorEnvelope,
    ErrorEvent,
    ProgressEvent,
    ProgressPayload,
    ResultEvent,
    error_payload,
    result_event,
)
from yorunge.domain.wire_limits import FRAME_LIMIT, JSON_LIMIT

STREAM_ID = "36ae6001-6b91-410b-bd9a-f933ffbf145e"
OPERATION_ID = "5ef3875f-a4a0-4ee7-b288-d16919cd299b"
OTHER_ID = "f4142880-e411-477c-91d9-0e512a44543d"
CANARY = "private-codec-canary-ğ-48291"


class Text(Model):
    text: str


class Tree(Model):
    tree: object


class Numbers(Model):
    values: list[int]


def compact(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode(
        "utf-8"
    )


def wire(value: object, *, event: str = "result", **overrides: object) -> bytes:
    return compact(
        {
            "schema_version": 1,
            "stream_id": STREAM_ID,
            "sequence": 1,
            "event": event,
            "operation_id": None,
            "payload": value,
            **overrides,
        }
    )


def text_result(value: str = "ordinary response") -> Result[Text]:
    return Result[Text](data=Text(text=value))


def sized_result(size: int) -> Result[Text]:
    baseline = len(compact(text_result("").model_dump(mode="json")))
    result = text_result("x" * (size - baseline))
    assert len(compact(result.model_dump(mode="json"))) == size
    return result


def decode(data: bytes, *, operation_id: str | None = None, secrets=()):
    return decode_event(
        data, Text, stream_id=STREAM_ID, sequence=1, operation_id=operation_id, secrets=secrets
    )


def assert_safe_failure(caught, code: str, operation_id: str | None = None) -> None:
    assert caught.value.code == code
    assert caught.value.envelope()["operation_id"] == operation_id
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None
    assert CANARY not in str(caught.value)


@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_exact_result_payload_byte_boundary_is_separate_from_frame_budget(delta: int) -> None:
    result = sized_result(JSON_LIMIT + delta)
    data = wire(result.model_dump(mode="json"))
    assert len(data) < FRAME_LIMIT
    event = result_event(result, stream_id=STREAM_ID)
    if delta > 0:
        with pytest.raises(YorungeError) as caught:
            decode(data)
        assert_safe_failure(caught, "invalid_response")
        with pytest.raises(YorungeError) as caught:
            encode_event(event)
        assert_safe_failure(caught, "output_write_failed")
    else:
        assert decode(data).payload == result
        encoded = encode_event(event)
        assert encoded.endswith(b"\n")
        assert json.loads(encoded)["payload"] == result.model_dump(mode="json")


@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_encoder_rechecks_payload_limit_after_model_normalization(delta: int) -> None:
    class Normalized(Model):
        text: str

        @field_validator("text")
        @classmethod
        def append_suffix(cls, value: str) -> str:
            return value + "x"

    base = Result[Normalized](data=Normalized(text=""))
    baseline = len(compact(base.model_dump(mode="json")))
    initial_size = JSON_LIMIT + delta - 1
    result = Result[Normalized](data=Normalized(text="x" * (initial_size - baseline)))
    assert len(compact(result.model_dump(mode="json"))) == initial_size
    event = result_event(result, stream_id=STREAM_ID)
    if delta > 0:
        with pytest.raises(YorungeError) as caught:
            encode_event(event)
        assert_safe_failure(caught, "output_write_failed")
    else:
        encoded = encode_event(event)
        assert len(compact(json.loads(encoded)["payload"])) == JSON_LIMIT + delta


@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_exact_encoded_frame_budget_includes_json_whitespace(delta: int) -> None:
    base = wire(text_result().model_dump(mode="json"))
    # The small valid payload is unchanged; only the raw frame grows.
    data = base + b" " * (FRAME_LIMIT + delta - len(base))
    assert len(data) == FRAME_LIMIT + delta
    if delta > 0:
        with pytest.raises(YorungeError) as caught:
            decode(data)
        assert_safe_failure(caught, "invalid_response")
    else:
        assert decode(data).payload.data.text == "ordinary response"


def test_result_limit_counts_raw_payload_whitespace_and_utf8_bytes() -> None:
    small = compact(text_result().model_dump(mode="json"))
    expanded = small[:1] + b" " * (JSON_LIMIT + 1 - len(small)) + small[1:]
    assert len(expanded) == JSON_LIMIT + 1
    frame = wire(None).replace(b'"payload":null', b'"payload":' + expanded)
    assert len(frame) < FRAME_LIMIT
    with pytest.raises(YorungeError) as caught:
        decode(frame)
    assert_safe_failure(caught, "invalid_response")
    unicode_result = text_result("ğ" * (JSON_LIMIT // 2))
    assert len(unicode_result.data.text) < JSON_LIMIT
    event = result_event(unicode_result, stream_id=STREAM_ID)
    with pytest.raises(YorungeError) as caught:
        encode_event(event)
    assert_safe_failure(caught, "output_write_failed")


@pytest.mark.parametrize("depth", [31, 32, 33])
def test_complete_frame_depth_includes_result_and_event_wrappers(depth: int) -> None:
    nested: object = 0
    # Event object + Result object + Tree object add three container levels.
    for _ in range(depth - 3):
        nested = [nested]
    result = Result[Tree](data=Tree(tree=nested))
    data = wire(result.model_dump(mode="json"))
    event = result_event(result, stream_id=STREAM_ID)
    if depth > 32:
        with pytest.raises(YorungeError) as caught:
            decode_event(data, Tree, stream_id=STREAM_ID, sequence=1)
        assert_safe_failure(caught, "invalid_response")
        with pytest.raises(YorungeError) as caught:
            encode_event(event)
        assert_safe_failure(caught, "output_write_failed")
    else:
        assert decode_event(data, Tree, stream_id=STREAM_ID, sequence=1).payload == result
        assert encode_event(event).endswith(b"\n")


@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_complete_frame_node_budget_includes_keys_arrays_and_wrappers(delta: int) -> None:
    # Event: object + six keys + five scalar values = 12 nodes, excluding payload.
    # Result: object + five keys + three scalars + empty warnings array = 10.
    # Numbers: object + values key + array = 3. Each integer adds one node.
    count = 65_536 - 25 + delta
    result = Result[Numbers](data=Numbers(values=[0] * count))
    data = wire(result.model_dump(mode="json"))
    event = result_event(result, stream_id=STREAM_ID)
    assert len(data) < JSON_LIMIT
    if delta > 0:
        with pytest.raises(YorungeError) as caught:
            decode_event(data, Numbers, stream_id=STREAM_ID, sequence=1)
        assert_safe_failure(caught, "invalid_response")
        with pytest.raises(YorungeError) as caught:
            encode_event(event)
        assert_safe_failure(caught, "output_write_failed")
    else:
        decoded = decode_event(data, Numbers, stream_id=STREAM_ID, sequence=1)
        assert len(decoded.payload.data.values) == count
        assert encode_event(event).endswith(b"\n")


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"\xff",
        b'\xef\xbb\xbf{"schema_version":1}',
        b"[]",
        b"{}",
        b'{"schema_version":1,"schema_version":1}',
        b'{"payload":NaN}',
        b'{"payload":Infinity}',
        b'{"payload":1e999}',
        b'{"payload":"\\ud800"}',
        b'{"payload":"' + CANARY.encode() + b'"',
    ],
)
@pytest.mark.parametrize("operation_id", [None, OPERATION_ID])
def test_strict_raw_failures_preserve_bound_context_without_parser_input(
    data: bytes, operation_id: str | None
) -> None:
    with pytest.raises(YorungeError) as caught:
        decode(data, operation_id=operation_id)
    assert_safe_failure(caught, "invalid_response", operation_id)


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": True},
        {"schema_version": 1.0},
        {"schema_version": 2},
        {"sequence": True},
        {"sequence": 1.0},
        {"sequence": 0},
        {"sequence": 2},
        {"stream_id": OTHER_ID},
        {"operation_id": OPERATION_ID},
        {"event": "completed"},
        {"unknown": CANARY},
        {"payload": {"status": "completed", "data": {"text": 1}}},
    ],
)
def test_closed_event_fields_and_expected_context_are_enforced(changes: dict[str, object]) -> None:
    data = wire(text_result().model_dump(mode="json"), **changes)
    with pytest.raises(YorungeError) as caught:
        decode(data)
    assert_safe_failure(caught, "invalid_response")


def test_duplicate_nested_keys_are_rejected_before_typed_validation() -> None:
    data = wire(text_result().model_dump(mode="json"))
    data = data.replace(b'"text":"ordinary response"', b'"text":"first","text":"second"')
    with pytest.raises(YorungeError) as caught:
        decode(data)
    assert_safe_failure(caught, "invalid_response")


@pytest.mark.parametrize("value", ["a", "text", "invalid_response"])
def test_short_secret_coincidences_in_fixed_protocol_fields_are_allowed(value: str) -> None:
    secrets = (SecretValue(value),)
    result = text_result("safe standard content")
    event = result_event(result, stream_id=STREAM_ID)
    assert decode(encode_event(event, secrets=secrets)[:-1], secrets=secrets).payload == result
    error = ErrorEvent(
        schema_version=1,
        stream_id=STREAM_ID,
        sequence=1,
        event="error",
        operation_id=None,
        payload=error_payload(YorungeError("invalid_response")),
    )
    assert decode(encode_event(error, secrets=secrets)[:-1], secrets=secrets).payload.code == (
        "invalid_response"
    )


@pytest.mark.parametrize("value", ["a", "short", CANARY, "prefix " + CANARY + " suffix"])
def test_exact_short_or_contained_long_dynamic_secret_is_never_published(value: str) -> None:
    secret = CANARY if CANARY in value else value
    secrets = (SecretValue(secret),)
    result = text_result(value)
    data = wire(result.model_dump(mode="json"))
    with pytest.raises(YorungeError) as caught:
        decode(data, secrets=secrets)
    assert_safe_failure(caught, "invalid_response")
    event = result_event(result, stream_id=STREAM_ID)
    with pytest.raises(YorungeError) as caught:
        encode_event(event, secrets=secrets)
    assert_safe_failure(caught, "output_write_failed")


def test_escaped_unicode_secret_is_checked_after_json_decoding() -> None:
    data = json.dumps(json.loads(wire(text_result(CANARY).model_dump(mode="json"))))
    assert "\\u011f" in data
    raw = data.encode()
    secrets = (SecretValue(CANARY),)
    with pytest.raises(YorungeError) as caught:
        decode(raw, secrets=secrets)
    assert_safe_failure(caught, "invalid_response")


def test_dynamic_mapping_keys_cannot_use_a_known_secret() -> None:
    class Mapping(Model):
        values: dict[str, str]

    result = Result[Mapping](data=Mapping(values={"a": "ordinary"}))
    data = wire(result.model_dump(mode="json"))
    secrets = (SecretValue("a"),)
    with pytest.raises(YorungeError) as caught:
        decode_event(data, Mapping, stream_id=STREAM_ID, sequence=1, secrets=secrets)
    assert_safe_failure(caught, "invalid_response")


def test_error_provider_message_is_discarded_but_approval_ids_still_have_provenance() -> None:
    raw = {**YorungeError("invalid_response").envelope(), "message": CANARY}
    decoded = decode(wire(raw, event="error"), secrets=(SecretValue(CANARY),))
    assert decoded.payload.message == MESSAGES["invalid_response"]
    assert CANARY not in encode_event(decoded, secrets=(SecretValue(CANARY),)).decode()
    approval = ApprovalNotEffective(OPERATION_ID, OTHER_ID)
    raw = wire(approval.envelope(), event="error")
    secrets = (SecretValue(OPERATION_ID),)
    with pytest.raises(YorungeError) as caught:
        decode(raw, secrets=secrets)
    assert_safe_failure(caught, "invalid_response")


def test_constructed_error_message_is_rebuilt_before_encoding() -> None:
    payload = ErrorEnvelope.model_construct(
        **{
            **YorungeError("remote_failed").envelope(),
            "message": CANARY,
            "details": EmptyErrorDetails(),
        }
    )
    event = ErrorEvent.model_construct(
        schema_version=1,
        stream_id=STREAM_ID,
        sequence=1,
        event="error",
        operation_id=None,
        payload=payload,
    )
    encoded = encode_event(event, secrets=(SecretValue(CANARY),))
    assert CANARY.encode() not in encoded
    assert json.loads(encoded)["payload"]["message"] == MESSAGES["remote_failed"]


def test_constructed_invalid_event_is_rejected_without_partial_bytes() -> None:
    event = ProgressEvent.model_construct(
        schema_version=True,
        stream_id=STREAM_ID,
        sequence=1,
        event="progress",
        operation_id=OPERATION_ID,
        payload=ProgressPayload(stage="connecting", completed=0, total=None),
    )
    with pytest.raises(YorungeError) as caught:
        encode_event(event)
    assert caught.value.code == "output_write_failed"


def test_constructed_field_cannot_leak_input_through_pydantic_serializer_warnings() -> None:
    invalid = Text.model_construct(text={CANARY: "provider value"})
    result = Result[Text].model_construct(data=invalid)
    event = ResultEvent[Text].model_construct(
        schema_version=1,
        stream_id=STREAM_ID,
        sequence=1,
        event="result",
        operation_id=None,
        payload=result,
    )
    with warnings.catch_warnings(record=True) as emitted:
        warnings.simplefilter("always")
        secrets = (SecretValue(CANARY),)
        with pytest.raises(YorungeError) as caught:
            encode_event(event, secrets=secrets)
    assert_safe_failure(caught, "output_write_failed")
    assert all(CANARY not in str(item.message) for item in emitted)


def test_custom_validator_output_is_secret_checked_after_validation() -> None:
    class Rewritten(Model):
        text: str

        @field_validator("text")
        @classmethod
        def rewrite(cls, value: str) -> str:
            return CANARY if value == "trigger" else value

    payload = text_result("trigger").model_dump(mode="json")
    raw = wire(payload)
    secrets = (SecretValue(CANARY),)
    with pytest.raises(YorungeError) as caught:
        decode_event(
            raw,
            Rewritten,
            stream_id=STREAM_ID,
            sequence=1,
            secrets=secrets,
        )
    assert_safe_failure(caught, "invalid_response")


def test_custom_serializer_cannot_bypass_known_secret_provenance() -> None:
    class Serialized(Model):
        text: str

        @field_serializer("text")
        def private_text(self, value: str) -> str:
            return CANARY

    result = Result[Serialized](data=Serialized(text="ordinary"))
    event = result_event(result, stream_id=STREAM_ID)
    secrets = (SecretValue(CANARY),)
    with pytest.raises(YorungeError) as caught:
        encode_event(event, secrets=secrets)
    assert_safe_failure(caught, "output_write_failed")


def test_computed_field_cannot_publish_outside_the_closed_model() -> None:
    class Computed(Model):
        text: str

        @computed_field
        @property
        def private(self) -> str:
            return CANARY

    result = Result[Computed](data=Computed(text="ordinary"))
    event = result_event(result, stream_id=STREAM_ID)
    secrets = (SecretValue(CANARY),)
    with pytest.raises(YorungeError) as caught:
        encode_event(event, secrets=secrets)
    assert_safe_failure(caught, "output_write_failed")


def test_closed_progress_literal_is_not_a_dynamic_secret_echo() -> None:
    progress = ProgressEvent(
        schema_version=1,
        stream_id=STREAM_ID,
        sequence=1,
        event="progress",
        operation_id=None,
        payload=ProgressPayload(stage="connecting", completed=0, total=None),
    )
    encoded = encode_event(progress, secrets=(SecretValue("connecting"),))
    assert decode(encoded[:-1], secrets=(SecretValue("connecting"),)).payload.stage == "connecting"


def test_bound_error_envelope_must_keep_inner_and_outer_operation_ids() -> None:
    payload = OperationError("stream_interrupted", OTHER_ID).envelope()
    raw = wire(payload, event="error", operation_id=OPERATION_ID)
    with pytest.raises(YorungeError) as caught:
        decode(raw, operation_id=OPERATION_ID)
    assert_safe_failure(caught, "invalid_response", OPERATION_ID)
