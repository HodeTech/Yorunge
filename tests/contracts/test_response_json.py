"""Independent JSON boundary and provider-reflection examples."""

import asyncio
import json
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from urllib.parse import unquote
from uuid import UUID

import pytest
from pydantic import (
    BaseModel,
    ConfigDict,
    PlainSerializer,
    WrapSerializer,
    computed_field,
    create_model,
    field_serializer,
    field_validator,
    model_serializer,
    model_validator,
)

from yorunge.application.response_json import (
    JSON_LIMIT,
    check_response_secrets,
    decode_response,
    parse_json,
)
from yorunge.domain.credentials import SecretValue
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Model


class TextResponse(Model):
    text: str


class Status(StrEnum):
    NORMAL = "normal"


class ProviderResponse(Model):
    schema_version: Literal[1]
    status: Literal["transport_failed"]
    enum: Status
    message: str
    records: dict[str, str]
    constants: tuple[Literal["constant"], ...]
    mapping: dict[str, Literal["constant"]]


def provider(**overrides):
    return ProviderResponse(
        **{
            "schema_version": 1,
            "status": "transport_failed",
            "enum": Status.NORMAL,
            "message": "ordinary safe response",
            "records": {},
            "constants": ("constant",),
            "mapping": {"dynamic-key": "constant"},
            **overrides,
        }
    )


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"\xff",
        b'\xef\xbb\xbf{"text":"value"}',
        b'{"text":"first","text":"second"}',
        b'{"text":NaN}',
        b'{"text":Infinity}',
        b'{"text":-Infinity}',
        b'{"text":1e999}',
        b'{"text":"\\ud800"}',
        b'{"\\udfff":"value"}',
        b'{"text":"value"}{}',
        b'{"text":"value"',
        b'{"text":"value",}',
        b'{"text":true}',
        b'{"text":"value","unknown":1}',
    ],
)
def test_untrusted_json_or_wrong_expected_model_is_rejected_without_parser_input(data):
    with pytest.raises(YorungeError) as failure:
        decode_response(data, TextResponse)
    assert failure.value.code == "invalid_response"
    assert failure.value.__context__ is None
    assert failure.value.__cause__ is None
    assert "first" not in str(failure.value)


def test_utf8_size_is_measured_on_encoded_bytes_not_characters():
    prefix, suffix = b'{"text":"', b'"}'
    content = prefix + b"x" * (JSON_LIMIT - len(prefix) - len(suffix)) + suffix
    result = decode_response(content, TextResponse)
    assert len(result.text) == JSON_LIMIT - 11
    with pytest.raises(YorungeError) as failure:
        decode_response(prefix + b"x" + content[len(prefix) :], TextResponse)
    assert failure.value.code == "invalid_response"
    unicode_data = json.dumps({"text": "ğ" * JSON_LIMIT}, ensure_ascii=False).encode()
    with pytest.raises(YorungeError) as failure:
        decode_response(unicode_data, TextResponse)
    assert failure.value.code == "invalid_response"


def test_nesting_and_node_boundaries_have_independent_known_counts():
    # Scalar depth=0; each array adds exactly one container level.
    assert parse_json(b"[" * 32 + b"0" + b"]" * 32)
    with pytest.raises(YorungeError) as failure:
        parse_json(b"[" * 33 + b"0" + b"]" * 33)
    assert failure.value.code == "invalid_response"
    # One root array + 65,535 scalar values = 65,536 nodes.
    at_limit = b"[" + b",".join([b"0"] * 65_535) + b"]"
    assert len(parse_json(at_limit)) == 65_535
    with pytest.raises(YorungeError) as failure:
        parse_json(at_limit[:-1] + b",0]")
    assert failure.value.code == "invalid_response"
    # Each object entry contributes one key and one scalar value.
    raw = json.dumps({str(i): 0 for i in range(32_768)}).encode()
    with pytest.raises(YorungeError) as failure:
        parse_json(raw)
    assert failure.value.code == "invalid_response"


@pytest.mark.parametrize("version", [True, 1.0, "1", None, 2])
def test_yorunge_model_schema_version_remains_strict(version):
    payload = provider().model_dump(mode="json")
    payload["schema_version"] = version
    raw = json.dumps(payload).encode()
    with pytest.raises(YorungeError) as failure:
        decode_response(raw, ProviderResponse)
    assert failure.value.code == "invalid_response"


def test_generic_json_does_not_impose_yorunge_version_semantics_on_provider_metadata():
    class ExternalResponse(Model):
        metadata: dict[str, str]

    data = b'{"metadata":{"schema_version":"1.0"}}'
    assert parse_json(data) == {"metadata": {"schema_version": "1.0"}}
    assert decode_response(data, ExternalResponse).metadata == {"schema_version": "1.0"}
    assert parse_json(b'{"schema_version":true}') == {"schema_version": True}


@pytest.mark.parametrize(
    "secret", ["a", "transport_failed", "schema_version", "normal", "constant"]
)
def test_fixed_schema_codes_literals_and_enums_do_not_imply_short_secret_leak(secret):
    value = provider()
    check_response_secrets(value, (SecretValue(secret),))
    result = decode_response(
        value.model_dump_json().encode(), ProviderResponse, secrets=(SecretValue(secret),)
    )
    assert result == value


@pytest.mark.parametrize(
    "secret,changes",
    [
        ("a", {"message": "a"}),
        ("field", {"records": {"field": "ordinary"}}),
        ("short", {"records": {"key": "short"}}),
        ("long-secret", {"message": "prefix-long-secret-suffix"}),
        ("long-secret", {"records": {"prefix-long-secret-suffix": "ordinary"}}),
        ("long-secret", {"records": {"key": "prefix-long-secret-suffix"}}),
        ("ğğğğ", {"message": "prefix-ğğğğ-suffix"}),
    ],
)
def test_dynamic_exact_or_long_substring_reflection_is_rejected(secret, changes):
    value = provider(**changes)
    raw = value.model_dump_json().encode()
    secrets = (SecretValue(secret),)
    with pytest.raises(YorungeError) as failure:
        decode_response(raw, ProviderResponse, secrets=secrets)
    assert failure.value.code == "invalid_response"
    assert failure.value.__context__ is None


def test_short_embedded_character_match_is_not_a_global_substring_prohibition():
    value = provider(message="a normal status can contain a")
    assert (
        decode_response(
            value.model_dump_json().encode(), ProviderResponse, secrets=(SecretValue("a"),)
        )
        == value
    )


def test_local_error_catalog_can_coincidentally_contain_the_short_secret():
    # The guarantee concerns private provenance, not the alphabet in fixed public messages.
    secrets = (SecretValue("a"),)
    with pytest.raises(YorungeError) as failure:
        decode_response(b'{"text":"a"}', TextResponse, secrets=secrets)
    assert failure.value.code == "invalid_response"
    assert "a" in failure.value.code
    assert failure.value.envelope()["details"] == {}


def test_unknown_rich_scalar_is_not_a_silent_reflection_bypass():
    class RichResponse(Model):
        value: UUID

    secret = "56f2851a-a276-4bd3-b07b-0472e888db42"
    raw = json.dumps({"value": secret}).encode()
    secrets = (SecretValue(secret),)
    with pytest.raises(YorungeError) as failure:
        decode_response(raw, RichResponse, secrets=secrets)
    assert failure.value.code == "invalid_response"


def test_bare_datetime_and_bytes_cannot_skip_dynamic_secret_validation():
    class DateResponse(Model):
        value: datetime

    class BytesResponse(Model):
        value: bytes

    for model, secret in ((DateResponse, "2026-10-29T12:00:00Z"), (BytesResponse, "bytes-canary")):
        raw = json.dumps({"value": secret}).encode()
        secrets = (SecretValue(secret),)
        with pytest.raises(YorungeError) as failure:
            decode_response(raw, model, secrets=secrets)
        assert failure.value.code == "invalid_response"


@pytest.mark.parametrize("kind", ["list", "dict_value", "dict_key", "object_alternative"])
def test_ambiguous_union_container_does_not_inherit_a_nonselected_literal_exemption(kind):
    class ListResponse(Model):
        records: list[Literal["fixed"]] | list[str]

    class DictValueResponse(Model):
        records: dict[str, Literal["fixed"]] | dict[str, str]

    class DictKeyResponse(Model):
        records: dict[Literal["fixed"], str] | dict[str, str]

    class ObjectResponse(Model):
        records: list[Literal["fixed"]] | object

    secret = "union-reflection-canary"
    variants = {
        "list": (ListResponse, [secret]),
        "dict_value": (DictValueResponse, {"key": secret}),
        "dict_key": (DictKeyResponse, {secret: "value"}),
        "object_alternative": (ObjectResponse, [secret]),
    }
    model, records = variants[kind]
    raw = json.dumps({"records": records}).encode()
    # These are valid model inputs through the free branch, not malformed payload tests.
    assert model.model_validate_json(raw).records == records
    secrets = (SecretValue(secret),)
    with pytest.raises(YorungeError) as failure:
        decode_response(raw, model, secrets=secrets)
    assert failure.value.code == "invalid_response"


def test_nullable_fixed_container_preserves_its_unambiguous_literal_exemption():
    class FixedResponse(Model):
        records: list[Literal["fixed"]] | None

    value = decode_response(
        b'{"records":["fixed"]}', FixedResponse, secrets=(SecretValue("fixed"),)
    )
    assert value.records == ["fixed"]


def custom_codec(kind):
    if kind == "field_string":

        class FieldString(Model):
            value: str

            @field_serializer("value")
            def emit(self, value: str) -> str:
                return unquote(value)

        return FieldString
    if kind == "field_integer":

        class FieldInteger(Model):
            value: int

            @field_serializer("value")
            def emit(self, value: int) -> str:
                return chr(value)

        return FieldInteger
    if kind == "whole_model":

        class WholeModel(Model):
            value: str

            @model_serializer
            def emit(self) -> dict[str, str]:
                return {"value": unquote(self.value)}

        return WholeModel
    if kind == "computed":

        class Computed(Model):
            value: str

            @computed_field
            @property
            def emitted(self) -> str:
                return unquote(self.value)

        return Computed
    if kind == "annotated_plain":

        class AnnotatedPlain(Model):
            value: Annotated[str, PlainSerializer(unquote, return_type=str)]

        return AnnotatedPlain
    if kind == "annotated_wrap":

        class AnnotatedWrap(Model):
            value: Annotated[str, WrapSerializer(lambda value, next_: unquote(next_(value)))]

        return AnnotatedWrap
    if kind == "extra_allow":

        class ExtraAllow(Model):
            model_config = ConfigDict(extra="allow")
            value: str

        return ExtraAllow
    if kind == "extra_ignore":

        class ExtraIgnore(BaseModel):
            value: str

        return ExtraIgnore
    raise AssertionError("unknown codec fixture")


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize(
    "kind",
    [
        "field_string",
        "field_integer",
        "whole_model",
        "computed",
        "annotated_plain",
        "annotated_wrap",
        "extra_allow",
        "extra_ignore",
    ],
)
def test_custom_output_codecs_computed_fields_and_open_models_fail_closed(kind, nested):
    secret = "a" if kind == "field_integer" else "synthetic-serializer-canary"
    inner = custom_codec(kind)
    payload = {"value": 97 if kind == "field_integer" else secret.replace("-", "%2D")}
    if kind in ("extra_allow", "extra_ignore"):
        payload = {"value": "ordinary", "unexpected": secret}
    expected_model, expected_payload = inner, payload
    if nested:
        expected_model = create_model(
            "NestedSerializationResponse", __base__=Model, child=(inner, ...)
        )
        expected_payload = {"child": payload}
    raw = json.dumps(expected_payload).encode()
    unguarded = expected_model.model_validate_json(raw)
    if kind != "extra_ignore":
        # Prove these actual model inputs serialize the synthetic secret, not just a marker flag.
        assert secret in unguarded.model_dump_json()
    secrets = (SecretValue(secret),)
    with pytest.raises(YorungeError) as failure:
        decode_response(raw, expected_model, secrets=secrets)
    assert failure.value.code == "invalid_response"
    assert failure.value.__context__ is None


def test_custom_dump_override_is_not_an_unchecked_output_codec():
    class CustomDump(Model):
        value: str

        def model_dump_json(self, **kwargs):
            return json.dumps({"value": unquote(self.value)})

    secrets = (SecretValue("synthetic-serializer-canary"),)
    with pytest.raises(YorungeError) as failure:
        decode_response(
            b'{"value":"synthetic%2Dserializer%2Dcanary"}',
            CustomDump,
            secrets=secrets,
        )
    assert failure.value.code == "invalid_response"


@pytest.mark.parametrize("nested", [False, True])
def test_literal_schema_word_field_names_do_not_look_like_custom_serializers(nested):
    class NamedFields(Model):
        serialization: str
        type: str

    data = {"serialization": "ordinary", "type": "ordinary"}
    model = NamedFields
    if nested:
        model = create_model("NestedNamedFields", __base__=Model, child=(NamedFields, ...))
        data = {"child": data}
    value = decode_response(
        json.dumps(data).encode(), model, secrets=(SecretValue("unrelated-canary"),)
    )
    assert value.model_dump(mode="json") == data


def test_ordinary_default_json_data_is_not_core_schema_serialization_metadata():
    class WithDefault(Model):
        metadata: dict[str, str] = {"type": "ordinary", "serialization": "ordinary"}

    value = decode_response(b"{}", WithDefault, secrets=(SecretValue("unrelated-canary"),))
    assert value.metadata == {"type": "ordinary", "serialization": "ordinary"}


def literal_drift_model(mode, secret):
    def restored(source):
        return chr(int(source)) if secret == "a" else unquote(source)

    class Source(Model):
        source: str
        state: Literal["ok"]

    if mode == "wrap":

        class Wrap(Source):
            @field_validator("state", mode="wrap")
            @classmethod
            def changed(cls, value, handler):
                return restored(value)

        return Wrap
    if mode == "after":

        class After(Source):
            @field_validator("state", mode="after")
            @classmethod
            def changed(cls, value, info):
                return restored(info.data["source"])

        return After

    class ModelAfter(Source):
        @model_validator(mode="after")
        def changed(self):
            return self.model_copy(update={"state": restored(self.source)})

    return ModelAfter


@pytest.mark.parametrize("mode", ["wrap", "after", "model"])
@pytest.mark.parametrize("secret", ["a", "synthetic-literal-canary"])
@pytest.mark.parametrize("nested", [False, True])
def test_literal_exemption_checks_the_actual_post_validator_value(mode, secret, nested):
    inner = literal_drift_model(mode, secret)
    source = "97" if secret == "a" else secret.replace("-", "%2D")
    payload = {"source": source, "state": source if mode == "wrap" else "ok"}
    expected_model, expected_payload = inner, payload
    if nested:
        expected_model = create_model("NestedLiteralDrift", __base__=Model, child=(inner, ...))
        expected_payload = {"child": payload}
    raw = json.dumps(expected_payload).encode()
    unguarded = expected_model.model_validate_json(raw)
    assert (unguarded.child if nested else unguarded).state == secret
    secrets = (SecretValue(secret),)
    with pytest.raises(YorungeError) as failure:
        decode_response(raw, expected_model, secrets=secrets)
    assert failure.value.code == "invalid_response"


def enum_drift_model(kind, secret):
    class Expected(StrEnum):
        OK = "ok"

    class Different(StrEnum):
        VALUE = secret

    class Response(Model):
        state: Expected

        @field_validator("state", mode="wrap")
        @classmethod
        def changed(cls, value, handler):
            if kind == "wrong_class":
                return Different.VALUE
            if kind == "raw_string":
                return secret
            if kind == "mutated_member":
                Expected.OK._value_ = secret
                return Expected.OK
            forged = str.__new__(Expected, secret)
            forged._name_, forged._value_ = "FORGED", secret
            return forged

    return Response


@pytest.mark.parametrize("kind", ["wrong_class", "raw_string", "mutated_member", "forged"])
@pytest.mark.parametrize("secret", ["a", "synthetic-enum-canary"])
def test_enum_exemption_requires_the_declared_canonical_member(kind, secret):
    expected_model = enum_drift_model(kind, secret)
    raw = b'{"state":"ok"}'
    unguarded = expected_model.model_validate_json(raw).state
    assert getattr(unguarded, "value", unguarded) == secret
    secrets = (SecretValue(secret),)
    with pytest.raises(YorungeError) as failure:
        decode_response(raw, expected_model, secrets=secrets)
    assert failure.value.code == "invalid_response"


def test_literal_numeric_membership_does_not_treat_true_as_integer_one():
    class DriftedVersion(Model):
        schema_version: Literal[1]

        @field_validator("schema_version", mode="after")
        @classmethod
        def changed(cls, value):
            return True

    secrets = (SecretValue("unrelated-canary"),)
    with pytest.raises(YorungeError) as failure:
        decode_response(b'{"schema_version":1}', DriftedVersion, secrets=secrets)
    assert failure.value.code == "invalid_response"


def test_ordinary_validators_that_preserve_protocol_constants_remain_supported():
    class Normal(Model):
        state: Literal["ok"]
        value: str

        @field_validator("state", mode="after")
        @classmethod
        def kept(cls, value):
            return value

        @field_validator("value", mode="after")
        @classmethod
        def normalized(cls, value):
            return value.strip()

    value = decode_response(
        b'{"state":"ok","value":" ordinary "}', Normal, secrets=(SecretValue("ok"),)
    )
    assert value.state == "ok"
    assert value.value == "ordinary"


def raising_model(mode, error_type):
    class FieldFailure(Model):
        value: str

        @field_validator("value", mode="after")
        @classmethod
        def crashed(cls, value):
            raise error_type(value)

    if mode == "field":
        return FieldFailure

    class ModelFailure(Model):
        value: str

        @model_validator(mode="after")
        def crashed(self):
            raise error_type(self.value)

    return ModelFailure


@pytest.mark.parametrize("mode", ["field", "model"])
@pytest.mark.parametrize("error_type", [RuntimeError, KeyError])
def test_ordinary_validator_exceptions_are_sanitized_outside_the_active_exception(mode, error_type):
    secret = "synthetic-validator-exception-canary"
    expected_model = raising_model(mode, error_type)
    raw = json.dumps({"value": secret}).encode()
    with pytest.raises(YorungeError) as failure:
        decode_response(raw, expected_model)
    assert failure.value.code == "invalid_response"
    assert failure.value.__context__ is None
    assert failure.value.__cause__ is None
    assert secret not in str(failure.value)
    assert secret not in json.dumps(failure.value.envelope())


@pytest.mark.parametrize("mode", ["field", "model"])
@pytest.mark.parametrize("error_type", [asyncio.CancelledError, KeyboardInterrupt, SystemExit])
def test_validator_cancellation_and_base_exception_control_flow_is_preserved(mode, error_type):
    expected_model = raising_model(mode, error_type)
    with pytest.raises(error_type):
        decode_response(b'{"value":"ordinary"}', expected_model)
