"""Ephemeral provider keys and targets, bound to independent local file identities."""

from __future__ import annotations

import re
from typing import NoReturn
from urllib.parse import parse_qsl, urlsplit
from uuid import uuid4

from yorunge.application import platform_upload_codec as control
from yorunge.application.response_json import parse_json
from yorunge.application.storage import StorageTarget, validate_object_key
from yorunge.domain.capabilities import canonical
from yorunge.domain.credentials import SecretValue, ServiceTarget, normalize_target
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.dataset_manifest import DatasetFile, DatasetManifest
from yorunge.domain.dataset_upload import manifest_reference
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import YorungeError
from yorunge.domain.state import canonical_uuid
from yorunge.domain.upload_versions import graph_of

_PROXY_TARGET = normalize_target("https://api.ssyz.org.tr/api/v1")
_MEDIA = re.compile(r"[\w!#$&^.+-]+/[\w!#$&^.+-]+", flags=re.ASCII)
_MISSING = object()
_MIMES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".txt": "text/plain",
    ".json": "application/json",
    ".jsonl": "application/x-ndjson",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
}


class _Ephemeral:
    __slots__ = ()

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("upload descriptors are immutable")

    def __repr__(self) -> str:
        return f"<{type(self).__name__} redacted>"

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("upload descriptor serialization is not supported")


class FileContext(_Ephemeral):
    __slots__ = (
        "plan_id",
        "plan_digest",
        "operation_id",
        "dataset_id",
        "file_index",
        "file",
        "target",
        "local_binding",
        "client_uid",
        "file_count",
    )
    plan_id: str
    plan_digest: str
    operation_id: str
    dataset_id: str
    file_index: int
    file: DatasetFile
    target: ServiceTarget
    local_binding: str
    client_uid: str
    file_count: int

    def __init__(
        self,
        plan_id: str,
        plan_digest: str,
        operation_id: str,
        dataset_id: str,
        file_index: int,
        file: DatasetFile,
        target: ServiceTarget,
        local_binding: str,
        client_uid: str,
        file_count: int,
    ) -> None:
        try:
            for identifier in (plan_id, operation_id, local_binding, client_uid):
                canonical_uuid(identifier)
            control._identifier(dataset_id, error="invalid_request")
            if (
                type(file_index) is not int
                or type(file_count) is not int
                or not 1 <= file_count <= 128
                or not 0 <= file_index < file_count
                or type(plan_digest) is not str
                or re.fullmatch(r"[0-9a-f]{64}", plan_digest, flags=re.ASCII) is None
                or target != _PROXY_TARGET
                or local_binding == client_uid
            ):
                raise ValueError("closed file context required")
            file = control._request_input(DatasetFile, file)
            if file.size > 500_000_000:
                raise ValueError("consumer file limit exceeded")
        except (ValueError, TypeError, AttributeError):
            raise YorungeError("invalid_request") from None
        values: tuple[tuple[str, object], ...] = (
            ("plan_id", plan_id),
            ("plan_digest", plan_digest),
            ("operation_id", operation_id),
            ("dataset_id", dataset_id),
            ("file_index", file_index),
            ("file", file),
            ("target", target),
            ("local_binding", local_binding),
            ("client_uid", client_uid),
            ("file_count", file_count),
        )
        for name, value in values:
            object.__setattr__(self, name, value)


class PresignedUpload(_Ephemeral):
    __slots__ = ("context", "provider_key", "target", "content_type")
    context: FileContext
    provider_key: SecretValue
    target: StorageTarget
    content_type: str

    def __init__(
        self,
        context: FileContext,
        provider_key: SecretValue,
        target: StorageTarget,
        content_type: str,
    ) -> None:
        if (
            type(context) is not FileContext
            or type(provider_key) is not SecretValue
            or type(target) is not StorageTarget
            or target.mode != "proxy"
            or target.service != context.target
            or target.dataset_id != context.dataset_id
            or target.expires_at is not None
            or target.literal_policy != "platform_proxy_v2"
        ):
            raise YorungeError("invalid_request")
        key = _key(provider_key.reveal())
        _target(target.wire_url, key, context)
        _mime(content_type, context.file.path)
        values: tuple[tuple[str, object], ...] = (
            ("context", context),
            ("provider_key", provider_key),
            ("target", target),
            ("content_type", content_type),
        )
        for name, value in values:
            object.__setattr__(self, name, value)

    def require(self, expected: FileContext) -> None:
        if self.context is not expected:
            raise YorungeError("invalid_request")


def contexts(
    plan: DatasetUploadPlanV2 | DatasetContinuationPlanV3,
    manifest: DatasetManifest,
    operation_id: str,
    dataset_id: str,
    secret: SecretValue,
) -> tuple[FileContext, ...]:
    """The file contexts of a plan, in index order: every file of an original upload, and only
    the selected ones (possibly none) of a continuation, whose dataset is the plan's own."""
    dataset_id = control._identifier(dataset_id, error="invalid_request")
    if isinstance(plan, DatasetContinuationPlanV3):
        plan = control._request_input(DatasetContinuationPlanV3, plan)
        if dataset_id != plan.continuation.dataset_id:
            raise YorungeError("invalid_request")
    else:
        plan = control._request_input(DatasetUploadPlanV2, plan)
    manifest = control._request_input(DatasetManifest, manifest)
    try:
        canonical_uuid(operation_id)
        if manifest_reference(manifest) != plan.manifest:
            raise ValueError("manifest binding mismatch")
    except (ValueError, TypeError, AttributeError):
        raise YorungeError("invalid_request") from None
    target = normalize_target(plan.scope.service_origin + plan.scope.api_base_path)
    if plan.storage.mode != "proxy" or target != _PROXY_TARGET:
        raise YorungeError("unsupported_combination")
    control.segment(dataset_id, secret)
    result = []
    minted: set[str] = set()
    for index in graph_of(plan).files:
        file = manifest.files[index]
        binding, client_uid = str(uuid4()), str(uuid4())
        if binding == client_uid or binding in minted or client_uid in minted:
            raise YorungeError("invalid_request")
        minted.update((binding, client_uid))
        for value in (binding, client_uid, file.path):
            control._scan(value, secret, {}, error="invalid_request")
        result.append(
            FileContext(
                plan.plan_id,
                plan.digest,
                operation_id,
                dataset_id,
                index,
                file,
                target,
                binding,
                client_uid,
                plan.manifest.file_count,
            )
        )
    return tuple(result)


def presign_content(context: FileContext, secret: SecretValue) -> bytes:
    _require_context(context)
    values: dict[str, object] = {
        "filename": context.file.path,
        "sha256_hash": context.file.sha256,
        "file_size": context.file.size,
        "client_uid": context.client_uid,
    }
    # local_binding is deliberately absent; it is never sent to the provider.
    control._scan(values, secret, {(): frozenset(values)}, error="invalid_request")
    return canonical({"files": [values]})


def _key(value: object) -> str:
    try:
        return validate_object_key(value)
    except YorungeError:
        raise YorungeError("invalid_response") from None


def _mime(value: object, filename: str) -> str:
    if value is _MISSING:
        return _MIMES.get("." + filename.rsplit(".", 1)[-1].lower(), "application/octet-stream")
    if type(value) is not str or len(value) > 128 or _MEDIA.fullmatch(value) is None:
        raise YorungeError("invalid_response")
    return value


def _target(
    url: object, key: str, context: FileContext, secret: SecretValue | None = None
) -> StorageTarget:
    if type(url) is not str:
        raise YorungeError("invalid_response")
    service = context.target
    relative = f"/datasets/{context.dataset_id}/upload/"
    if url.startswith(relative):
        url = service.service_origin + service.api_base_path.rstrip("/") + url
    elif url.startswith("/") and not url.startswith("//"):
        url = service.service_origin + url
    route = service.api_base_path.rstrip("/") + relative
    try:
        target = StorageTarget(
            url,
            mode="proxy",
            origin=service.service_origin,
            prefix=route,
            expires_at=None,
            service=service,
            dataset_id=context.dataset_id,
            literal_policy="platform_proxy_v2",
        )
        parsed = urlsplit(url)
        query = parse_qsl(
            parsed.query,
            keep_blank_values=True,
            strict_parsing=True,
            encoding="utf-8",
            errors="strict",
        )
        if parsed.path != route + "put" or query != [("key", key)]:
            raise ValueError("exact proxy resource required")
        if secret is not None:
            target.check_secret(secret)
    except (ValueError, YorungeError):
        raise YorungeError("invalid_response") from None
    return target


def presigned(data: bytes, context: FileContext, secret: SecretValue) -> PresignedUpload:
    _require_context(context)
    control._require_secret(secret)
    value = parse_json(data)
    root = control._object(value)
    if "success" in root:
        if root["success"] is not True:
            raise YorungeError("invalid_response")
        root = control._object(root.get("data"))
    rows = root.get("presigned_urls")
    if not isinstance(rows, list) or len(rows) != 1 or root.get("duplicates", []) != []:
        raise YorungeError("invalid_response")
    row = control._object(rows[0])
    _file_match(row, context)
    key = _key(row.get("object_key"))
    if row.get("headers", {}) != {} or row.get("checksum") is not None:
        raise YorungeError("invalid_response")
    url = row.get("upload_url")
    if type(url) is not str:
        raise YorungeError("invalid_response")
    target = _target(url, key, context, secret)
    control._checked_raw(value, "presign", secret, checked_presign_url=url)
    return PresignedUpload(
        context,
        SecretValue(key),
        target,
        _mime(row.get("content_type", _MISSING), context.file.path),
    )


def _file_match(row: dict[str, object], context: FileContext) -> None:
    if (
        row.get("filename") != context.file.path
        or row.get("sha256_hash") != context.file.sha256
        or ("client_uid" in row and row["client_uid"] != context.client_uid)
    ):
        raise YorungeError("invalid_response")
    if "file_size" in row and (
        type(row["file_size"]) is not int or row["file_size"] != context.file.size
    ):
        raise YorungeError("invalid_response")


def distinct_uploads(
    uploads: tuple[PresignedUpload, ...],
    expected: tuple[FileContext, ...],
    selection: tuple[int, ...] | None = None,
) -> None:
    """The presigned uploads are one per expected file and share nothing between files.

    ``expected`` is every file of an original upload; a continuation names the ``selection`` of
    files it sends, and the uploads are those files' alone.
    """
    if type(uploads) is not tuple or type(expected) is not tuple:
        raise YorungeError("invalid_request")
    if any(type(u) is not PresignedUpload for u in uploads):
        raise YorungeError("invalid_request")
    for context in expected:
        _require_context(context)
    if not expected or len(uploads) != len(expected):
        raise YorungeError("invalid_response")
    if selection is None:
        indices, whole = tuple(range(len(expected))), len(expected) == expected[0].file_count
    else:
        indices, whole = selection, len(expected) <= expected[0].file_count
    first = expected[0]
    if (
        not whole
        or tuple(c.file_index for c in expected) != indices
        or any(_batch_identity(c) != _batch_identity(first) for c in expected)
    ):
        raise YorungeError("invalid_response")
    for upload, context in zip(uploads, expected, strict=True):
        upload.require(context)
    if (
        len({u.provider_key.reveal() for u in uploads}) != len(uploads)
        or len({u.target.wire_url for u in uploads}) != len(uploads)
        or len({c.local_binding for c in expected}) != len(expected)
    ):
        raise YorungeError("invalid_response")


def _batch_identity(context: FileContext) -> tuple[str, str, str, str, str, str, int]:
    return (
        context.plan_id,
        context.plan_digest,
        context.operation_id,
        context.dataset_id,
        context.target.service_origin,
        context.target.api_base_path,
        context.file_count,
    )


def _require_context(context: FileContext) -> None:
    if type(context) is not FileContext:
        raise YorungeError("invalid_request")


def confirm_content(upload: PresignedUpload, expected: FileContext, secret: SecretValue) -> bytes:
    if type(upload) is not PresignedUpload:
        raise YorungeError("invalid_request")
    upload.require(expected)
    value: dict[str, object] = {
        "object_key": upload.provider_key.reveal(),
        "filename": expected.file.path,
        "file_size": expected.file.size,
        "sha256_hash": expected.file.sha256,
    }
    control._scan(value, secret, {(): frozenset(value)}, error="invalid_request")
    return canonical({"items": [value], "skip_dedup": True})
