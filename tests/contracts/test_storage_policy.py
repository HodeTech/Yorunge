"""Fixed storage target/auth/wire oracles; no HTTP client or provider assumptions."""

import base64
import hashlib
import pickle
from dataclasses import dataclass
from functools import partial

import pytest

from yorunge.application.http_transport import HttpCredential
from yorunge.application.storage import StorageRequest, StorageTarget
from yorunge.domain.credentials import SecretValue, normalize_target
from yorunge.domain.errors import YorungeError

ORIGIN = "https://storage.example"
API = normalize_target("https://api.example/v1")
DATASET = "00000000-0000-4000-8000-000000000001"
PREFIX = f"/v1/datasets/{DATASET}/upload/"
EXPIRY = "2026-11-02T23:59:59.000000Z"
SECRET = "synthetic-storage-selected-key-unsafe-to-publish"


@dataclass
class MetadataSource:
    size: int = 0
    sha256: str = hashlib.sha256(b"").hexdigest()
    sent_bytes: int = 0
    sent_sha256: str | None = None
    complete: bool = False

    def chunks(self):
        raise AssertionError("policy construction must not consume bytes")

    async def aclose(self):
        raise AssertionError("policy construction must not close bytes")


def direct(url=None, **changes):
    args = dict(
        mode="direct",
        origin=ORIGIN,
        prefix="/bucket/",
        expires_at=EXPIRY,
        service=None,
        dataset_id=None,
    )
    args.update(changes)
    return StorageTarget(url or ORIGIN + "/bucket/object?signature=signed-value", **args)


def proxy(url=None, **changes):
    args = dict(
        mode="proxy",
        origin=API.service_origin,
        prefix=PREFIX,
        expires_at=None,
        service=API,
        dataset_id=DATASET,
    )
    args.update(changes)
    return StorageTarget(url or API.service_origin + PREFIX + "object", **args)


def request(target=None, *, secret=SECRET, **changes):
    key = SecretValue(secret)
    args = dict(
        target=target or direct(),
        source=MetadataSource(),
        selected_secret=key,
        content_type="application/octet-stream",
    )
    args.update(changes)
    return StorageRequest(**args)


def test_signed_query_and_percent_encoding_remain_opaque_and_ordered():
    url = ORIGIN + "/bucket/file%20one?X-Amz-Credential=prefix%2Fscope%2Fend&x=%2B%3D&x=two"
    target = direct(url)
    assert target.wire_url == url
    assert request(target).max_bytes == 65536
    assert "prefix" not in repr(target) and "signed" not in repr(request(target))
    with pytest.raises(TypeError):
        pickle.dumps(target)
    with pytest.raises(AttributeError):
        target._url = ORIGIN + "/bucket/other"


@pytest.mark.parametrize(
    "suffix",
    [
        "../file",
        "%2e%2e/file",
        "%252e%252e/file",
        "%2Fother",
        "%252fother",
        "%5cother",
        "a//b",
        "a\\b",
        "a%00",
        "a%0d%0a",
        "a%",
        "a%XZ",
        "a%ff",
        "a%C2%85",
        "a%E2%80%AE",
        "file#",
        "file#fragment",
    ],
)
def test_path_or_fragment_escape_is_rejected(suffix):
    with pytest.raises(YorungeError) as failure:
        direct(ORIGIN + "/bucket/" + suffix)
    assert failure.value.code == "invalid_service_target"


@pytest.mark.parametrize("query", ["a=%", "a=%XY", "a=%00", "a=%0d%0a", "a=raw\ncontrol", "a=%ff"])
def test_invalid_or_unsupported_query_encoding_is_rejected(query):
    with pytest.raises(YorungeError):
        direct(ORIGIN + "/bucket/file?" + query)


@pytest.mark.parametrize(
    "url",
    [
        "http://storage.example/bucket/file",
        "//storage.example/bucket/file",
        "https://user:pass@storage.example/bucket/file",
        "https://storage.example.evil/bucket/file",
        "https://storage.example:444/bucket/file",
        "https://storage.example:443/bucket/file",
        "https://storage.example/other/file",
    ],
)
def test_exact_origin_and_prefix_precede_provider_url(url):
    with pytest.raises(YorungeError):
        direct(url)


@pytest.mark.parametrize(
    "field,value",
    [
        ("origin", None),
        ("prefix", None),
        ("prefix", "/bucket/../"),
        ("expires_at", None),
        ("expires_at", "tomorrow"),
        ("expires_at", True),
        ("dataset_id", DATASET),
        ("service", API),
        ("mode", "automatic"),
    ],
)
def test_direct_descriptor_is_closed_and_requires_expiry(field, value):
    with pytest.raises(YorungeError):
        direct(**{field: value})


def test_url_length_limit_minus_boundary_plus():
    prefix = ORIGIN + "/bucket/object?signature="
    assert len(direct(prefix + "x" * (16384 - len(prefix))).wire_url) == 16384
    rejected_call = partial(direct, prefix + "x" * (16385 - len(prefix)))
    with pytest.raises(YorungeError):
        rejected_call()


@pytest.mark.parametrize(
    "secret,url",
    [
        ("a", ORIGIN + "/bucket/a"),
        ("a", ORIGIN + "/bucket/f?signature=a"),
        ("long-secret-value", ORIGIN + "/bucket/f?signature=before-long-secret-value-after"),
        ("long-secret-value", ORIGIN + "/bucket/f?signature=long%2Dsecret%2Dvalue"),
    ],
)
def test_dynamic_url_fields_use_selected_literal_rule(secret, url):
    rejected_call = partial(request, direct(url), secret=secret)
    with pytest.raises(YorungeError):
        rejected_call()


@pytest.mark.parametrize("secret", ["a", "0", "identity", "X-API-Key"])
def test_short_or_protocol_collision_secret_does_not_reject_fixed_headers(secret):
    assert request(secret=secret).public_headers() == (
        ("Content-Type", "application/octet-stream"),
        ("Content-Length", "0"),
        ("Accept-Encoding", "identity"),
    )


def test_proxy_has_one_exact_platform_header_and_direct_has_none():
    key = SecretValue(SECRET)
    credential = HttpCredential("X-API-Key", key, target=API, service_id="evren-platform")
    value = StorageRequest(proxy(), MetadataSource(), key, "image/png", credential=credential)
    assert value.wire_headers()[-1] == ("X-API-Key", SECRET)
    assert not any(
        name.lower() in {"authorization", "cookie", "x-api-key"}
        for name, _ in request().wire_headers()
    )
    assert SECRET not in repr(value)
    rejected_call = partial(
        StorageRequest, direct(), MetadataSource(), key, "image/png", credential=credential
    )
    with pytest.raises(YorungeError):
        rejected_call()


@pytest.mark.parametrize("change", ["llm", "wrong-target", "prefix", "wrong-snapshot", "missing"])
def test_proxy_never_accepts_other_auth_source(change):
    key = SecretValue(SECRET)
    args = dict(header_name="X-API-Key", secret=key, target=API, service_id="evren-platform")
    if change == "llm":
        args["service_id"] = "evren-llm"
    elif change == "wrong-target":
        args["target"] = normalize_target("https://elsewhere.example/v1")
    elif change == "prefix":
        args["prefix"] = "Bearer "
    elif change == "wrong-snapshot":
        args["secret"] = SecretValue(SECRET)
    credential = None if change == "missing" else HttpCredential(**args)
    rejected_call = partial(
        StorageRequest, proxy(), MetadataSource(), key, "image/png", credential=credential
    )
    with pytest.raises(YorungeError):
        rejected_call()


@pytest.mark.parametrize(
    "checksum,header,value",
    [
        ("sha256_hex", "X-Content-SHA256", hashlib.sha256(b"").hexdigest()),
        (
            "sha256_base64",
            "X-Amz-Checksum-Sha256",
            base64.b64encode(hashlib.sha256(b"").digest()).decode(),
        ),
    ],
)
def test_only_ready_sha256_header_mapping_is_generated(checksum, header, value):
    assert request(checksum=checksum).public_headers()[-1] == (header, value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("checksum", "md5"),
        ("checksum", None),
        ("checksum", []),
        ("content_type", "image/png\r\nX-Header: bad"),
        ("content_type", "application/json; charset=utf-8"),
        ("content_type", "bad mime"),
        ("source", None),
        ("source", MetadataSource(size=True)),
        ("source", MetadataSource(size=1024**3 + 1)),
        ("source", MetadataSource(sha256="G" * 64)),
    ],
)
def test_invalid_body_or_header_metadata_fails_before_io(field, value):
    with pytest.raises(YorungeError):
        request(**{field: value})


@pytest.mark.parametrize("secret", ["a", "eight-byte-secret"])
@pytest.mark.parametrize("layers", [1, 2, 3, 4])
def test_every_accepted_path_decode_layer_uses_the_literal_secret_rule(secret, layers):
    from urllib.parse import unquote

    encoded = "".join(f"%{byte:02X}" for byte in secret.encode())
    for _ in range(layers - 1):
        encoded = encoded.replace("%", "%25")
    decoded = encoded
    for _ in range(layers):
        decoded = unquote(decoded)
    assert decoded == secret  # Independent oracle, not the implementation parser.
    rejected_call = partial(request, direct(ORIGIN + "/bucket/" + encoded), secret=secret)
    with pytest.raises(YorungeError) as failure:
        rejected_call()
    assert failure.value.code == "invalid_service_target"
    different = "%62"
    for _ in range(layers - 1):
        different = different.replace("%", "%25")
    assert request(direct(ORIGIN + "/bucket/" + different), secret=secret)


def registered_proxy(query="key=object-handle", **changes):
    service = normalize_target("https://api.ssyz.org.tr/api/v1")
    args = dict(
        mode="proxy",
        origin=service.service_origin,
        prefix=f"/api/v1/datasets/{DATASET}/upload/",
        expires_at=None,
        service=service,
        dataset_id=DATASET,
        literal_policy="platform_proxy_v2",
    )
    args.update(changes)
    return StorageTarget(
        service.service_origin + f"/api/v1/datasets/{DATASET}/upload/put?{query}", **args
    )


@pytest.mark.parametrize("secret", ["key", "put", "datasets"])
def test_registered_proxy_exempts_fixed_protocol_but_checks_dynamic_resources(secret):
    target = registered_proxy()
    captured = SecretValue(secret)
    credential = HttpCredential(
        "X-API-Key", captured, target=target.service, service_id="evren-platform"
    )
    result = StorageRequest(target, MetadataSource(), captured, "image/png", credential=credential)
    assert result.target.literal_policy == "platform_proxy_v2"
    assert result.wire_headers()[-1] == ("X-API-Key", secret)


@pytest.mark.parametrize(
    "secret,query",
    [
        ("key", "key=key"),
        ("put", "key=put"),
        ("datasets", "key=prefix-datasets-value"),
        ("key", "key=%6b%65%79"),
        ("%6b%65%79", "key=%6b%65%79"),
    ],
)
def test_registered_proxy_still_rejects_raw_and_decoded_dynamic_secret(secret, query):
    target = registered_proxy(query)
    captured = SecretValue(secret)
    with pytest.raises(YorungeError) as error:
        target.check_secret(captured)
    assert error.value.code == "invalid_service_target"


@pytest.mark.parametrize("query", ["key=x&token=y", "other=x", "key=x&key=y", "key"])
def test_registered_literal_policy_cannot_exempt_unregistered_query_shapes(query):
    with pytest.raises(YorungeError) as error:
        registered_proxy(query)
    assert error.value.code == "invalid_service_target"


def test_registered_literal_policy_does_not_apply_to_other_targets_or_direct():
    with pytest.raises(YorungeError) as error:
        direct(literal_policy="platform_proxy_v2")
    assert error.value.code == "invalid_service_target"
    with pytest.raises(YorungeError) as error:
        proxy(literal_policy="platform_proxy_v2")
    assert error.value.code == "invalid_service_target"


@pytest.mark.parametrize(
    "query",
    [
        "key=",
        "key=../x",
        "key=objects/../x",
        "key=objects//x",
        "key=%2e%2e%2fx",
        "key=%C3%A9",
        "key=" + "x" * 513,
    ],
)
def test_registered_proxy_rejects_invalid_key_at_target_construction(query):
    with pytest.raises(YorungeError) as error:
        registered_proxy(query)
    assert error.value.code == "invalid_service_target"


@pytest.mark.parametrize("size", [511, 512])
def test_registered_proxy_accepts_actual_maximum_key_boundary(size):
    target = registered_proxy("key=" + "x" * size)
    target.check_secret(SecretValue("unrelated-secret"))
