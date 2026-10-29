"""Independent JSON boundary and provider-reflection examples."""

import json
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

import pytest

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
    with pytest.raises(YorungeError) as failure:
        parse_json(json.dumps({str(i): 0 for i in range(32_768)}).encode())
    assert failure.value.code == "invalid_response"


@pytest.mark.parametrize("version", [True, 1.0, "1", None, 2])
def test_schema_version_is_strict_before_model_validation(version):
    payload = provider().model_dump(mode="json")
    payload["schema_version"] = version
    with pytest.raises(YorungeError) as failure:
        decode_response(json.dumps(payload).encode(), ProviderResponse)
    assert failure.value.code == "invalid_response"


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
    with pytest.raises(YorungeError) as failure:
        decode_response(
            value.model_dump_json().encode(), ProviderResponse, secrets=(SecretValue(secret),)
        )
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
    with pytest.raises(YorungeError) as failure:
        decode_response(b'{"text":"a"}', TextResponse, secrets=(SecretValue("a"),))
    assert failure.value.code == "invalid_response"
    assert "a" in failure.value.code
    assert failure.value.envelope()["details"] == {}


def test_unknown_rich_scalar_is_not_a_silent_reflection_bypass():
    class RichResponse(Model):
        value: UUID

    secret = "56f2851a-a276-4bd3-b07b-0472e888db42"
    with pytest.raises(YorungeError) as failure:
        decode_response(
            json.dumps({"value": secret}).encode(), RichResponse, secrets=(SecretValue(secret),)
        )
    assert failure.value.code == "invalid_response"


def test_bare_datetime_and_bytes_cannot_skip_dynamic_secret_validation():
    class DateResponse(Model):
        value: datetime

    class BytesResponse(Model):
        value: bytes

    for model, secret in ((DateResponse, "2026-10-29T12:00:00Z"), (BytesResponse, "bytes-canary")):
        with pytest.raises(YorungeError) as failure:
            decode_response(
                json.dumps({"value": secret}).encode(), model, secrets=(SecretValue(secret),)
            )
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
    with pytest.raises(YorungeError) as failure:
        decode_response(raw, model, secrets=(SecretValue(secret),))
    assert failure.value.code == "invalid_response"


def test_nullable_fixed_container_preserves_its_unambiguous_literal_exemption():
    class FixedResponse(Model):
        records: list[Literal["fixed"]] | None

    value = decode_response(
        b'{"records":["fixed"]}', FixedResponse, secrets=(SecretValue("fixed"),)
    )
    assert value.records == ["fixed"]
