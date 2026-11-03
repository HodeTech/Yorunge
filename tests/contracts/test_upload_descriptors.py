"""Ephemeral raw keys, exact proxy descriptors and local-only file bindings."""

import copy
import hashlib
import json
import pickle
from functools import partial
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

import pytest

from yorunge.application import upload_descriptors as codec
from yorunge.application import upload_metadata_codec as metadata
from yorunge.domain.credentials import SecretValue
from yorunge.domain.dataset_manifest import DatasetFile, DatasetManifest, build_manifest
from yorunge.domain.dataset_upload import UploadStoragePolicy, manifest_reference
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import YorungeError

FIXTURES = Path(__file__).parents[1] / "fixtures"
PLAN = DatasetUploadPlanV2.model_validate_json(
    (FIXTURES / "dataset-upload-plan-v2.json").read_bytes()
)
MANIFEST = DatasetManifest.model_validate_json((FIXTURES / "dataset-manifest-v1.json").read_bytes())
DATASET = "00000000-0000-4000-8000-000000000009"
OPERATION = "00000000-0000-4000-8000-000000000010"
SECRET = SecretValue("synthetic-platform-secret")
KEY = "possible-capability-key-never-persisted"


def encoded(value):
    return json.dumps(value, ensure_ascii=False).encode()


def contexts(plan=PLAN, manifest=MANIFEST, secret=SECRET):
    return codec.contexts(plan, manifest, OPERATION, DATASET, secret)


def response(context, key=KEY, **updates):
    return {
        "presigned_urls": [
            {
                "filename": context.file.path,
                "sha256_hash": context.file.sha256,
                "file_size": context.file.size,
                "client_uid": context.client_uid,
                "object_key": key,
                "upload_url": f"/datasets/{DATASET}/upload/put?key={quote(key, safe='')}",
                **updates,
            }
        ],
        "duplicates": [],
    }


def test_local_binding_is_independent_of_network_uid_and_private_provider_key():
    context = contexts()[0]
    request = json.loads(codec.presign_content(context, SECRET))
    assert request == {
        "files": [
            {
                "filename": "a.txt",
                "file_size": 3,
                "sha256_hash": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
                "client_uid": context.client_uid,
            }
        ]
    }
    assert context.local_binding not in json.dumps(request)
    assert context.local_binding != context.client_uid
    descriptor = codec.presigned(encoded(response(context)), context, SECRET)
    confirm = codec.confirm_content(descriptor, context, SECRET)
    assert json.loads(confirm) == {
        "items": [
            {
                "filename": "a.txt",
                "file_size": 3,
                "sha256_hash": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
                "object_key": KEY,
            }
        ],
        "skip_dedup": True,
    }
    assert context.local_binding.encode() not in confirm
    assert context.client_uid.encode() not in confirm
    assert descriptor.content_type == "text/plain"
    assert descriptor.target.wire_url == (
        f"https://api.ssyz.org.tr/api/v1/datasets/{DATASET}/upload/put?key={KEY}"
    )


def test_generated_local_bindings_and_network_uids_are_disjoint_for_entire_batch(monkeypatch):
    one, two, three = uuid4(), uuid4(), uuid4()
    minted = iter((one, two, three, one))
    monkeypatch.setattr(codec, "uuid4", lambda: next(minted))
    with pytest.raises(YorungeError) as error:
        contexts()
    assert error.value.code == "invalid_request"


@pytest.mark.parametrize("secret", ["key", "put", "datasets"])
@pytest.mark.parametrize("wrapped", [False, True])
def test_fixed_proxy_uri_parts_do_not_reject_valid_selected_short_credentials(secret, wrapped):
    captured = SecretValue(secret)
    context = contexts(secret=captured)[0]
    value = response(context)
    if wrapped:
        value = {"success": True, "data": value}
    descriptor = codec.presigned(encoded(value), context, captured)
    assert descriptor.target.literal_policy == "platform_proxy_v2"
    assert descriptor.provider_key.reveal() == KEY


def test_checked_proxy_url_exception_does_not_exempt_discarded_metadata_url():
    captured = SecretValue("datasets")
    context = contexts(secret=captured)[0]
    value = response(context)
    value["metadata"] = {"upload_url": value["presigned_urls"][0]["upload_url"]}
    raw = encoded(value)
    with pytest.raises(YorungeError) as error:
        codec.presigned(raw, context, captured)
    assert error.value.code == "invalid_response"


@pytest.mark.parametrize("wrapped", [False, True])
@pytest.mark.parametrize("form", ["relative", "api_root", "absolute"])
def test_exact_proxy_target_keeps_raw_percent_encoding(form, wrapped):
    context = contexts()[0]
    key = "objects/file-key.txt"
    url = f"/datasets/{DATASET}/upload/put?key=objects%2ffile-key.txt"
    if form == "api_root":
        url = "/api/v1" + url
    elif form == "absolute":
        url = "https://api.ssyz.org.tr/api/v1" + url
    value = response(context, key, upload_url=url)
    data = encoded({"success": True, "data": value} if wrapped else value)
    result = codec.presigned(data, context, SECRET)
    assert result.target.wire_url.endswith("?key=objects%2ffile-key.txt")


@pytest.mark.parametrize(
    "field,value",
    [
        ("filename", "other.txt"),
        ("sha256_hash", "0" * 64),
        ("client_uid", "wrong"),
        ("file_size", True),
        ("file_size", 4),
        ("file_size", "3"),
        ("content_type", None),
        ("content_type", "text/plain\n"),
        ("content_type", "x" * 129),
        ("headers", {"Authorization": "unknown"}),
        ("headers", []),
        ("checksum", "md5"),
    ],
)
def test_descriptor_control_mismatch_never_yields_put_target(field, value):
    context = contexts()[0]
    raw = encoded(response(context, **{field: value}))
    with pytest.raises(YorungeError) as error:
        codec.presigned(raw, context, SECRET)
    assert error.value.code == "invalid_response"


@pytest.mark.parametrize(
    "value", ["", "../key", "/key", "a//b", "a/./b", "a%2fb", "key?token=x", "é", "x" * 513]
)
def test_provider_key_is_bounded_but_never_declared_safe_to_persist(value):
    context = contexts()[0]
    raw = encoded(response(context, value))
    with pytest.raises(YorungeError) as error:
        codec.presigned(raw, context, SECRET)
    assert error.value.code == "invalid_response"


@pytest.mark.parametrize(
    "url",
    [
        f"https://evil.example/api/v1/datasets/{DATASET}/upload/put?key={KEY}",
        f"https://api.ssyz.org.tr:444/api/v1/datasets/{DATASET}/upload/put?key={KEY}",
        f"//api.ssyz.org.tr/api/v1/datasets/{DATASET}/upload/put?key={KEY}",
        f"/datasets/{DATASET}/upload/other?key={KEY}",
        f"/datasets/{DATASET}/upload/put?key={KEY}&signature=secret",
        f"/datasets/{DATASET}/upload/put?key={KEY}&key={KEY}",
        f"/datasets/{DATASET}/upload/put?key=other",
        f"/datasets/{DATASET}/upload/%2e%2e/put?key={KEY}",
        f"/datasets/{DATASET}/upload/put?key={KEY}#fragment",
    ],
)
def test_proxy_path_query_authority_is_exact_without_fallback(url):
    context = contexts()[0]
    raw = encoded(response(context, upload_url=url))
    with pytest.raises(YorungeError) as error:
        codec.presigned(raw, context, SECRET)
    assert error.value.code == "invalid_response"
    assert KEY not in str(error.value)


@pytest.mark.parametrize("change", ["missing", "zero", "two", "duplicates", "logical_false"])
def test_presign_cardinality_and_duplicate_shortcut_are_closed(change):
    context = contexts()[0]
    value = response(context)
    if change == "missing":
        del value["presigned_urls"]
    elif change == "zero":
        value["presigned_urls"] = []
    elif change == "two":
        value["presigned_urls"] *= 2
    elif change == "duplicates":
        value["duplicates"] = [context.file.sha256]
    else:
        value = {"success": False, "data": value}
    raw = encoded(value)
    with pytest.raises(YorungeError) as error:
        codec.presigned(raw, context, SECRET)
    assert error.value.code == "invalid_response"


def test_context_and_descriptor_cannot_be_mutated_serialized_or_copied():
    context = contexts()[0]
    descriptor = codec.presigned(encoded(response(context)), context, SECRET)
    assert KEY not in repr(descriptor)
    assert "upload/put" not in repr(descriptor)
    for value in (context, descriptor):
        with pytest.raises(AttributeError):
            value.file_index = 1
        for call in (
            lambda value=value: copy.copy(value),
            lambda value=value: pickle.dumps(value),
            lambda value=value: json.dumps(value),
        ):
            with pytest.raises(TypeError):
                call()


def test_descriptor_cannot_be_swapped_to_another_manifest_file():
    expected = contexts()
    descriptor = codec.presigned(encoded(response(expected[0])), expected[0], SECRET)
    with pytest.raises(YorungeError) as error:
        codec.confirm_content(descriptor, expected[1], SECRET)
    assert error.value.code == "invalid_request"


@pytest.mark.parametrize("shared", [True, False])
def test_independent_local_bindings_do_not_hide_shared_provider_keys(shared):
    expected = contexts()
    uploads = tuple(
        codec.presigned(
            encoded(response(context, KEY if shared else f"object-{i}")), context, SECRET
        )
        for i, context in enumerate(expected)
    )
    if shared:
        with pytest.raises(YorungeError) as error:
            codec.distinct_uploads(uploads, expected)
        assert error.value.code == "invalid_response"
    else:
        codec.distinct_uploads(uploads, expected)


@pytest.mark.parametrize("secret", ["abc123", "selected-long-secret"])
@pytest.mark.parametrize("where", ["key", "metadata", "encoded_query"])
def test_selected_credential_is_rejected_even_in_discarded_or_encoded_descriptor_fields(
    secret, where
):
    context = contexts(secret=SecretValue(secret))[0]
    value = response(context)
    if where == "key":
        value["presigned_urls"][0]["object_key"] = secret
    elif where == "metadata":
        value["unused"] = {secret: "ignored"}
    else:
        escaped = "".join(f"%{ord(char):02x}" for char in secret)
        value["presigned_urls"][0]["object_key"] = secret
        value["presigned_urls"][0]["upload_url"] = f"/datasets/{DATASET}/upload/put?key={escaped}"
    raw = encoded(value)
    captured = SecretValue(secret)
    with pytest.raises(YorungeError) as error:
        codec.presigned(raw, context, captured)
    assert error.value.code == "invalid_response"


def reseal(body):
    value = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return DatasetUploadPlanV2.model_validate_json(
        encoded({**body, "digest": hashlib.sha256(value).hexdigest()})
    )


def test_real_provider_direct_policy_is_rejected_before_presign_content():
    body = PLAN.model_dump(mode="json", exclude={"digest"})
    body["storage"] = UploadStoragePolicy(
        mode="direct", origin="https://storage.example"
    ).model_dump()
    plan = reseal(body)
    with pytest.raises(YorungeError) as error:
        contexts(plan)
    assert error.value.code == "unsupported_combination"


@pytest.mark.parametrize(
    "field,value", [("file_index", True), ("local_binding", "bad"), ("plan_digest", "bad")]
)
def test_constructed_file_context_still_enforces_private_scalar_identity(field, value):
    context = contexts()[0]
    values = {name: getattr(context, name) for name in codec.FileContext.__slots__}
    values[field] = value
    with pytest.raises(YorungeError) as error:
        codec.FileContext(**values)
    assert error.value.code == "invalid_request"


@pytest.mark.parametrize("created", [None, True, 0, 2, "1"])
def test_confirm_requires_exact_created_integer(created):
    raw = encoded({"created": created})
    with pytest.raises(YorungeError) as error:
        metadata.confirm_ack(raw, 1, SECRET)
    assert error.value.code == "invalid_response"


@pytest.mark.parametrize(
    "field,value",
    [
        ("actual_count", True),
        ("actual_count", 2),
        ("actual_count", None),
        ("batch_duplicates", 1),
        ("batch_duplicates", False),
    ],
)
def test_confirm_optional_counters_are_strict_when_present(field, value):
    raw = encoded({"created": 1, field: value})
    with pytest.raises(YorungeError) as error:
        metadata.confirm_ack(raw, 1, SECRET)
    assert error.value.code == "invalid_response"


def item(**updates):
    return {
        "id": str(uuid4()),
        "dataset_id": DATASET,
        "original_filename": "a.txt",
        "file_size_bytes": 3,
        "sha256_hash": MANIFEST.files[0].sha256,
        **updates,
    }


def page(items, **updates):
    return {"items": items, "next_cursor": None, "total": len(items), **updates}


def test_null_remote_hash_stays_unknown_and_cursor_is_opaque():
    value = metadata.items(
        encoded(page([item(sha256_hash=None)], next_cursor="a%2F+b=")), DATASET, SECRET
    )
    assert value.items[0].sha256_hash is None
    assert metadata.item_query(value.next_cursor, SECRET) == (
        ("limit", "128"),
        ("cursor", "a%2F+b="),
    )
    assert metadata.item_query(None, SECRET) == (("limit", "128"),)
    metadata.confirm_ack(b'{"created":1,"actual_count":3,"batch_duplicates":0}', 3, SECRET)
    metadata.put_ack(b"", SECRET)
    metadata.put_ack(b'{"success":true}', SECRET)


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "bad"),
        ("dataset_id", str(uuid4())),
        ("original_filename", "../x"),
        ("file_size_bytes", True),
        ("file_size_bytes", 500_000_001),
        ("sha256_hash", "bad"),
    ],
)
def test_item_projection_is_strict_and_exact_dataset(field, value):
    raw = encoded(page([item(**{field: value})]))
    with pytest.raises(YorungeError) as error:
        metadata.items(raw, DATASET, SECRET)
    assert error.value.code == "invalid_response"


@pytest.mark.parametrize(
    "field,value",
    [
        ("total", True),
        ("total", 0),
        ("total", 2**63),
        ("next_cursor", ""),
        ("next_cursor", "a\n"),
        ("next_cursor", "x" * 1025),
    ],
)
def test_item_page_control_fields_are_bounded(field, value):
    raw = encoded(page([item()], **{field: value}))
    with pytest.raises(YorungeError) as error:
        metadata.items(raw, DATASET, SECRET)
    assert error.value.code == "invalid_response"


def test_put_ack_does_not_expand_storage_response_limit():
    raw = b'{"success":true}' + b" " * (64 * 1024)
    with pytest.raises(YorungeError) as error:
        metadata.put_ack(raw, SECRET)
    assert error.value.code == "invalid_response"


def plan_for(manifest):
    body = PLAN.model_dump(mode="json", exclude={"digest"})
    body["manifest"] = manifest_reference(manifest).model_dump(mode="json")
    body["request_limits"].update(
        max_presign=manifest.file_count,
        max_put=manifest.file_count,
        max_confirm=manifest.file_count,
        max_upload_bytes=manifest.total_bytes,
    )
    return reseal(body)


def test_same_hash_different_names_keep_distinct_network_and_local_identities():
    manifest = build_manifest(
        tuple(
            DatasetFile(path=name, size=3, sha256=MANIFEST.files[0].sha256)
            for name in ("first.txt", "second.txt")
        )
    )
    expected = contexts(plan_for(manifest), manifest)
    uploads = tuple(
        codec.presigned(encoded(response(context, f"object-{i}")), context, SECRET)
        for i, context in enumerate(expected)
    )
    codec.distinct_uploads(uploads, expected)
    assert uploads[0].context.local_binding != uploads[1].context.local_binding
    assert uploads[0].context.file.sha256 == uploads[1].context.file.sha256
    assert [
        json.loads(codec.confirm_content(u, c, SECRET))["items"][0]["filename"]
        for u, c in zip(uploads, expected, strict=True)
    ] == ["first.txt", "second.txt"]


def test_128_descriptor_and_item_fixture_remains_bounded_and_bijective():
    manifest = build_manifest(
        tuple(
            DatasetFile(path=f"file-{i:03}.txt", size=3, sha256=MANIFEST.files[0].sha256)
            for i in range(128)
        )
    )
    expected = contexts(plan_for(manifest), manifest)
    uploads = tuple(
        codec.presigned(encoded(response(context, f"objects/key-{i}")), context, SECRET)
        for i, context in enumerate(expected)
    )
    codec.distinct_uploads(uploads, expected)
    assert len({u.context.local_binding for u in uploads}) == 128
    raw = encoded(page([item(original_filename=f.path) for f in manifest.files]))
    result = metadata.items(raw, DATASET, SECRET)
    assert len(result.items) == result.total == 128


@pytest.mark.parametrize("change", ["missing", "reorder", "mixed_operation"])
def test_complete_descriptor_set_cannot_be_replaced_by_partial_or_mixed_batch(change):
    expected = contexts()
    if change == "missing":
        expected = expected[:1]
    elif change == "reorder":
        expected = expected[::-1]
    else:
        other = codec.contexts(PLAN, MANIFEST, str(uuid4()), DATASET, SECRET)
        expected = (other[0], *expected[1:])
    uploads = tuple(
        codec.presigned(encoded(response(context, f"object-{i}")), context, SECRET)
        for i, context in enumerate(expected)
    )
    with pytest.raises(YorungeError) as error:
        codec.distinct_uploads(uploads, expected)
    assert error.value.code == "invalid_response"


@pytest.mark.parametrize("field", ["next_cursor", "total", "sha256_hash"])
def test_missing_nullable_or_required_item_control_is_not_defaulted(field):
    value = page([item()])
    if field == "sha256_hash":
        del value["items"][0][field]
    else:
        del value[field]
    raw = encoded(value)
    with pytest.raises(YorungeError) as error:
        metadata.items(raw, DATASET, SECRET)
    assert error.value.code == "invalid_response"


@pytest.mark.parametrize("duplicate", ["id", "name"])
def test_duplicate_remote_identity_is_not_a_second_manifest_file(duplicate):
    first = item()
    second = item(original_filename="other.txt")
    second["id" if duplicate == "id" else "original_filename"] = first[
        "id" if duplicate == "id" else "original_filename"
    ]
    raw = encoded(page([first, second]))
    with pytest.raises(YorungeError) as error:
        metadata.items(raw, DATASET, SECRET)
    assert error.value.code == "invalid_response"


@pytest.mark.parametrize(
    "kind,secret", [("presign", "object_key"), ("confirm", "created"), ("items", "items")]
)
def test_only_consumed_protocol_keys_are_exempt_in_each_new_raw_shape(kind, secret):
    captured = SecretValue(secret)
    context = contexts(secret=captured)[0]
    if kind == "presign":
        value = response(context)
    elif kind == "confirm":
        value = {"created": 1}
    else:
        value = page([item()])

    def call(raw):
        if kind == "presign":
            return codec.presigned(raw, context, captured)
        if kind == "confirm":
            return metadata.confirm_ack(raw, 1, captured)
        return metadata.items(raw, DATASET, captured)

    call(encoded(value))
    value["discarded"] = {secret: "unused"}
    raw = encoded(value)
    with pytest.raises(YorungeError) as error:
        call(raw)
    assert error.value.code == "invalid_response"


@pytest.mark.parametrize(
    "case",
    [
        "context",
        "secret",
        "response_context",
        "response_secret",
        "descriptor",
        "confirm_secret",
        "confirm_ack_secret",
        "batch",
        "batch_context",
    ],
)
def test_invalid_private_codec_inputs_have_closed_errors(case):
    context = contexts()[0]
    raw = encoded(response(context))
    descriptor = codec.presigned(raw, context, SECRET)
    calls = {
        "context": partial(codec.presign_content, None, SECRET),
        "secret": partial(codec.presign_content, context, None),
        "response_context": partial(codec.presigned, raw, None, SECRET),
        "response_secret": partial(codec.presigned, raw, context, None),
        "descriptor": partial(codec.confirm_content, None, context, SECRET),
        "confirm_secret": partial(codec.confirm_content, descriptor, context, None),
        "confirm_ack_secret": partial(metadata.confirm_ack, b'{"created":1}', 1, None),
        "batch": partial(codec.distinct_uploads, None, (context,)),
        "batch_context": partial(codec.distinct_uploads, (), (None,)),
    }
    invoke = calls[case]
    with pytest.raises(YorungeError) as error:
        invoke()
    assert error.value.code == "invalid_request"
