"""The private HTTP boundary cannot change the captured target, auth or byte budget."""

import dataclasses
import json
import pickle
from uuid import uuid4

import pytest

from yorunge.application.http_transport import (
    JSON_LIMIT,
    RAW_LIMIT,
    URL_LIMIT,
    HttpCredential,
    HttpRequest,
    HttpStatusFailure,
)
from yorunge.domain.credentials import SecretValue, ServiceTarget, normalize_target
from yorunge.domain.errors import MESSAGES, OperationError, YorungeError

TARGET = normalize_target("https://api.example.test/api/v1")
CANARY = "synthetic-private-key-never-render"


def credential(value=CANARY, **overrides):
    return HttpCredential(
        "Authorization",
        SecretValue(value),
        "Bearer ",
        **{"target": TARGET, "service_id": "evren-platform", **overrides},
    )


def request(**overrides):
    return HttpRequest(
        **{
            "target": TARGET,
            "method": "GET",
            "endpoint": "records",
            "service_id": "evren-platform",
            **overrides,
        }
    )


def test_captured_target_query_and_exact_auth_are_not_reselected_or_rendered():
    auth = credential()
    value = request(
        credential=auth,
        endpoint="köken/%31",
        query=(("project", "a b/&=ğ"), ("project", "second")),
        headers=(("X-Correlation", "stable"),),
    )
    assert value.url == (
        "https://api.example.test/api/v1/k%C3%B6ken/%31?project=a+b%2F%26%3D%C4%9F&project=second"
    )
    assert value.wire_headers() == (
        ("X-Correlation", "stable"),
        ("Accept-Encoding", "identity"),
        ("Authorization", "Bearer " + CANARY),
    )
    assert CANARY not in repr(value)
    assert "project" not in repr(value)
    assert "example.test" not in repr(value)
    assert CANARY not in str(auth)
    for convert in (pickle.dumps, dataclasses.asdict, json.dumps):
        with pytest.raises(TypeError) as failure:
            convert(value)
        assert CANARY not in str(failure.value)
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.endpoint = "changed"


@pytest.mark.parametrize(
    "endpoint",
    [
        "",
        "/records",
        "//other.test/records",
        "https://other.test/records",
        "a/../records",
        "./records",
        "a//records",
        "records/",
        "a\\records",
        "a?x=y",
        "a#fragment",
        "a@host",
        "a/%2f/records",
        "a/%5c/records",
        "a/%2E%2E/records",
        "a/%252f/records",
        "bad%escape",
        "a\nrecords",
        "a b",
        "\ud800",
        "x" * 2049,
    ],
)
def test_relative_endpoint_cannot_escape_or_ambiguously_rewrite_the_target(endpoint):
    with pytest.raises(YorungeError) as failure:
        request(endpoint=endpoint)
    assert failure.value.code == "invalid_service_target"
    assert failure.value.__context__ is None


@pytest.mark.parametrize(
    "target",
    [
        ServiceTarget(service_origin="http://api.example.test", api_base_path="/api/v1"),
        ServiceTarget(service_origin="https://api.example.test:444", api_base_path="/api/v1"),
        ServiceTarget(service_origin="https://API.example.test", api_base_path="/api/v1"),
        ServiceTarget(service_origin="https://api.example.test", api_base_path="/api/v1/"),
        ServiceTarget(service_origin="https://user:pass@api.example.test", api_base_path="/api/v1"),
    ],
)
def test_request_and_auth_require_the_exact_canonical_binding(target):
    with pytest.raises(YorungeError) as failure:
        request(target=target, service_id="evren-platform")
    assert failure.value.code == "invalid_service_target"
    with pytest.raises(YorungeError) as failure:
        HttpCredential(
            "Authorization", SecretValue(CANARY), target=target, service_id="evren-platform"
        )
    assert failure.value.code == "invalid_service_target"


def test_auth_for_another_origin_or_api_root_is_rejected_before_any_network():
    for url in ("https://other.example.test/api/v1", "https://api.example.test/other"):
        other = HttpCredential(
            "Authorization",
            SecretValue(CANARY),
            target=normalize_target(url),
            service_id="evren-platform",
        )
        with pytest.raises(YorungeError) as failure:
            request(credential=other)
        assert failure.value.code == "invalid_service_target"


def test_same_target_does_not_make_credentials_interchangeable_between_services():
    auth = credential(service_id="evren-llm")
    with pytest.raises(YorungeError) as failure:
        request(credential=auth)
    assert failure.value.code == "invalid_service_target"
    assert request(service_id="evren-llm", credential=auth).credential is auth


@pytest.mark.parametrize("service_id", [None, True, "platform", "EVREN-LLM", b"evren-llm"])
def test_service_identity_is_required_and_strict_on_both_request_and_auth(service_id):
    with pytest.raises(YorungeError) as failure:
        request(service_id=service_id)
    assert failure.value.code == "invalid_service_target"
    with pytest.raises(YorungeError) as failure:
        credential(service_id=service_id)
    assert failure.value.code == "invalid_service_target"


@pytest.mark.parametrize(
    "changes",
    [
        {"endpoint": CANARY},
        {"endpoint": "prefix-" + CANARY + "-suffix"},
        {"endpoint": "%73ynthetic-private-key-never-render"},
        {"query": (("key", CANARY),)},
        {"query": ((CANARY, "value"),)},
        {"query": (("key", "prefix-" + CANARY + "-suffix"),)},
    ],
)
def test_auth_is_not_allowed_in_plain_or_encoded_dynamic_request_url_parts(changes):
    with pytest.raises(YorungeError) as failure:
        request(credential=credential(), **changes)
    assert failure.value.code == "invalid_request"
    assert failure.value.__context__ is None


def test_short_credential_url_check_is_exact_not_a_global_character_prohibition():
    auth = credential("a")
    assert request(credential=auth, query=(("data", "normal"),)).query == (("data", "normal"),)
    for changes in ({"endpoint": "a"}, {"query": (("key", "a"),)}, {"query": (("a", "value"),)}):
        with pytest.raises(YorungeError) as failure:
            request(credential=auth, **changes)
        assert failure.value.code == "invalid_request"


@pytest.mark.parametrize("secret", ["ğ", "prefix\r\nx: yes", "\x00", "value ", "\tvalue"])
def test_untransportable_auth_is_not_trimmed_encoded_or_sent(secret):
    with pytest.raises(YorungeError) as failure:
        credential(secret)
    assert failure.value.code == "invalid_credential"
    assert failure.value.__context__ is None


@pytest.mark.parametrize("header", ["Host", "Cookie", "Content-Length", "Connection", "Proxy-Auth"])
def test_auth_header_cannot_be_a_different_transport_or_implicit_auth_control(header):
    with pytest.raises(YorungeError) as failure:
        HttpCredential(header, SecretValue(CANARY), target=TARGET, service_id="evren-platform")
    assert failure.value.code == "invalid_credential"


@pytest.mark.parametrize(
    "headers",
    [
        (("Host", "other.test"),),
        (("Authorization", "anything"),),
        (("Cookie", "session=x"),),
        (("Accept-Encoding", "gzip"),),
        (("Content-Length", "10"),),
        (("X-Good", "first"), ("x-good", "second")),
        (("X\nBad", "value"),),
        (("X-Good", "bad\r\nX-Other: value"),),
        (("X-Good", "ğ"),),
        (("X-Good", "leading "),),
        (("Proxy-Any", "value"),),
        (("X-Good", "x" * 16_385),),
        (("X" * 129, "value"),),
    ],
)
def test_caller_headers_cannot_override_auth_or_framing_and_are_bounded(headers):
    with pytest.raises(YorungeError) as failure:
        request(headers=headers)
    assert failure.value.code == "invalid_request"


@pytest.mark.parametrize(
    "changes",
    [
        {"method": "get"},
        {"method": "CONNECT"},
        {"read_only": 1},
        {"method": "POST", "read_only": True},
        {"max_bytes": True},
        {"max_bytes": 1.0},
        {"max_bytes": 0},
        {"max_bytes": RAW_LIMIT + 1},
        {"content": "not-bytes"},
        {"content": b"x" * (JSON_LIMIT + 1)},
        {"query": [("key", "value")]},
        {"query": (("key", "\ud800"),)},
        {"query": (("key", "line\nvalue"),)},
        {"query": tuple((str(i), "value") for i in range(65))},
        {"headers": (("X-Key", "x" * 16_384),) * 5},
    ],
)
def test_invalid_request_does_not_silently_coerce_types_or_expand_resource_budgets(changes):
    with pytest.raises(YorungeError) as failure:
        request(**changes)
    assert failure.value.code == "invalid_request"
    assert failure.value.__context__ is None


def test_explicit_byte_and_pair_limits_accept_the_boundary_and_reject_the_next_value():
    assert request(content=b"x" * JSON_LIMIT, max_bytes=RAW_LIMIT).max_bytes == RAW_LIMIT
    assert len(request(query=tuple((str(i), "value") for i in range(64))).query) == 64
    # Header metadata can reach the 64KiB quota without the separate URL wire quota.
    valid = tuple((f"X{i}", "v" * 16_381) for i in range(4))
    assert request(headers=valid).headers == valid
    with pytest.raises(YorungeError) as failure:
        request(headers=valid + (("extra", "value"),))
    assert failure.value.code == "invalid_request"


def query_at_wire_size(size):
    # Independent fixed target + query framing; only ASCII alphanumeric values follow.
    prefix = "https://api.example.test/api/v1/records?a=&b=&c=&d="
    remaining = size - len(prefix)
    result = []
    for name in ("a", "b", "c", "d"):
        length = min(16_384, remaining)
        result.append((name, "x" * length))
        remaining -= length
    assert remaining == 0
    return tuple(result)


@pytest.mark.parametrize("size", [65_535, 65_536])
def test_url_wire_byte_limit_accepts_the_boundary_without_relaxing_metadata_limits(size):
    value = request(query=query_at_wire_size(size))
    assert len(value.url.encode("ascii")) == size
    assert URL_LIMIT == 65_536


def test_url_wire_byte_limit_rejects_the_next_byte_before_network_preparation():
    with pytest.raises(YorungeError) as failure:
        request(query=query_at_wire_size(65_537))
    assert failure.value.code == "invalid_request"
    assert failure.value.__context__ is None


@pytest.mark.parametrize("value", ["&" * 16_380, "ğ" * 8190])
def test_percent_encoding_cannot_expand_bounded_query_metadata_beyond_the_url_limit(value):
    query = tuple((str(index), value) for index in range(4))
    assert sum(len(key.encode()) + len(text.encode()) for key, text in query) == 65_524
    with pytest.raises(YorungeError) as failure:
        request(query=query)
    assert failure.value.code == "invalid_request"


def test_json_request_body_uses_the_same_strict_parser_without_exposing_input():
    assert (
        request(
            method="POST", content=b'{"value":1}', headers=(("Content-Type", "application/json"),)
        ).content
        == b'{"value":1}'
    )
    for content in (b'{"value":1,"value":2}', b'{"value":NaN}', b'{"value":"\xff"}'):
        with pytest.raises(YorungeError) as failure:
            request(method="POST", content=content, headers=(("Content-Type", "application/json"),))
        assert failure.value.code == "invalid_request"
        assert failure.value.__context__ is None


@pytest.mark.parametrize(
    "code,exit_code",
    [
        ("transport_timeout", 1),
        ("transport_failed", 1),
        ("remote_access_denied", 3),
        ("remote_rate_limited", 1),
        ("remote_failed", 1),
        ("invalid_response", 1),
        ("stream_interrupted", 1),
        ("request_cancelled", 6),
        ("output_closed", 6),
        ("output_write_failed", 1),
    ],
)
def test_closed_error_catalog_exit_and_operation_context_are_consistent(code, exit_code):
    operation_id = str(uuid4())
    ordinary = YorungeError(code)
    assert ordinary.message == MESSAGES[code]
    assert ordinary.exit_code == exit_code
    assert ordinary.envelope()["operation_id"] is None
    assert ordinary.envelope()["details"] == {}
    contextual = OperationError(code, operation_id)
    assert contextual.exit_code == exit_code
    assert contextual.envelope()["operation_id"] == operation_id
    assert contextual.envelope()["details"] == {"reason_code": code, "capacity_kind": None}
    uncertain = OperationError("operation_uncertain", operation_id, reason_code=code)
    assert uncertain.exit_code == 5
    assert uncertain.envelope()["details"]["reason_code"] == code


@pytest.mark.parametrize(
    "status,code,exit_code",
    [
        (404, "remote_failed", 1),
        (401, "remote_access_denied", 3),
        (403, "remote_access_denied", 3),
        (429, "remote_rate_limited", 1),
        (503, "remote_failed", 1),
    ],
)
def test_http_status_failure_preserves_only_the_safe_status(status, code, exit_code):
    error = HttpStatusFailure(status)
    assert error.status_code == status
    assert error.code == code
    assert error.exit_code == exit_code
    assert error.envelope()["details"] == {}


@pytest.mark.parametrize("status", [True, 404.0, 99, 600, "404"])
def test_invalid_status_metadata_is_a_controlled_invalid_response(status):
    with pytest.raises(YorungeError) as failure:
        HttpStatusFailure(status)
    assert failure.value.code == "invalid_response"
