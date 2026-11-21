"""The narrow catalog reader: strict JSON, a secret scan, consumed fields, a second scan on output.

ADR-0035 Karar 8 and ADR-0022’s observer pattern. Every projection takes the raw bytes and the
selected secret and does the reading itself, so the scan cannot be skipped by a caller. The whole
parsed tree is scanned first (used or dropped). Only the fields ``domain.catalog`` consumes are
picked and validated strictly; display text is cleaned afterwards, so the finished record is
scanned once more, because cleaning may join pieces that the first scan saw apart. No I/O: the
transport supplies bytes and the response headers.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Final, TypeVar

from pydantic import BaseModel

from yorunge.application.response_json import (
    JSON_LIMIT,
    literal_secret_match,
    parse_json,
    scan_for_secret,
)
from yorunge.domain import catalog
from yorunge.domain.credentials import SecretValue
from yorunge.domain.errors import YorungeError

T = TypeVar("T", bound=BaseModel)

# consumed field -> source field in the provider answer; the required set names what must exist
_LLM_MODEL: Final = {
    "model_id": "id",
    "task": "task",
    "created": "created",
    "modalities": "modalities",
    "context_length": "context_length",
    "default_max_output_tokens": "default_max_output_tokens",
    "precision": "precision",
    "pricing": "pricing",
}
_LLM_MODEL_REQUIRED: Final = frozenset({"model_id", "task", "created"})
_LLM_PRICING: Final = {
    "prompt_token_price": "prompt_token_price",
    "completion_token_price": "completion_token_price",
    "currency": "currency",
    "free_until": "free_until",
}
_LLM_PRICING_REQUIRED: Final = frozenset({"prompt_token_price", "completion_token_price"})
_PLATFORM_MODEL: Final = {
    "model_id": "id",
    "owner_username": "owner_username",
    "slug": "slug",
    "name": "name",
    "description": "description",
    "license": "license",
    "modality": "modality",
    "stage": "stage",
    "visibility": "visibility",
    "versions_count": "versions_count",
    "architecture": "architecture",
    "created_at": "created_at",
    "updated_at": "updated_at",
}
_PLATFORM_MODEL_REQUIRED: Final = frozenset(
    {
        "model_id",
        "slug",
        "name",
        "modality",
        "stage",
        "visibility",
        "versions_count",
        "created_at",
        "updated_at",
    }
)
_PLATFORM_VERSION: Final = {
    "version_id": "id",
    "version_tag": "version_tag",
    "framework": "framework",
    "file_size_bytes": "file_size_bytes",
    "created_at": "created_at",
}
_PLATFORM_VERSION_REQUIRED: Final = frozenset({"version_id", "version_tag", "created_at"})
_PLATFORM_DATASET: Final = {
    "dataset_id": "id",
    "name": "name",
    "slug": "slug",
    "modality": "modality",
    "item_count": "item_count",
    "visibility": "visibility",
    "updated_at": "updated_at",
    "owner_username": "owner_username",
}
_PLATFORM_DATASET_REQUIRED: Final = frozenset(
    {"dataset_id", "name", "slug", "modality", "item_count", "visibility", "updated_at"}
)
# Presence flags: the URL value itself never reaches a record (ADR-0035 Karar 7).
_WEIGHT_FLAGS: Final = {
    "has_weights": "weights_url",
    "has_onnx": "onnx_url",
    "has_tflite": "tflite_url",
}

# Display fields are cleaned as they are read. Identifiers are never cleaned: a cleaned identifier
# could name a different model than the one the provider sent (zero-width characters).
_SHOWN_LLM: Final = {"currency": catalog.NAME_LIMIT, "free_until": catalog.NAME_LIMIT}
_SHOWN_LLM_MODEL: Final = {"precision": catalog.NAME_LIMIT}
_SHOWN_PLATFORM_MODEL: Final = {
    "name": catalog.NAME_LIMIT,
    "description": catalog.TEXT_LIMIT,
    "license": catalog.NAME_LIMIT,
    "modality": catalog.NAME_LIMIT,
    "stage": catalog.NAME_LIMIT,
    "visibility": catalog.NAME_LIMIT,
    "architecture": catalog.NAME_LIMIT,
}
_SHOWN_VERSION: Final = {"framework": catalog.NAME_LIMIT}
_SHOWN_DATASET: Final = {
    "name": catalog.NAME_LIMIT,
    "modality": catalog.NAME_LIMIT,
    "visibility": catalog.NAME_LIMIT,
}


def read(data: bytes, secret: SecretValue) -> object:
    """Strict JSON under the shared budget, then the literal-secret scan of every key and string."""
    value = parse_json(data, max_bytes=JSON_LIMIT)
    scan_for_secret(value, secret)
    return value


def _guard(record: BaseModel, secret: SecretValue) -> None:
    """The finished record, as it will be shown, carries no literal of the selected key.

    Display cleaning can join characters that the first scan saw apart; this second scan closes
    that gap. A match is ``invalid_response``, the same as a key found in the raw answer.
    """
    captured = secret.reveal()
    pending: list[object] = [record.model_dump()]
    while pending:
        item = pending.pop()
        if isinstance(item, str) and literal_secret_match(item, captured):
            raise YorungeError("invalid_response")
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            # A numeric field is shown as its digits: a key made of digits must not hide in one.
            if literal_secret_match(str(item), captured):
                raise YorungeError("invalid_response")
        if isinstance(item, Mapping):
            if any(isinstance(key, str) and literal_secret_match(key, captured) for key in item):
                raise YorungeError("invalid_response")
            owner, slug = item.get("owner_username"), item.get("slug")
            # The address is shown as ``owner/slug``: a key split between the two must not show.
            if (
                isinstance(owner, str)
                and isinstance(slug, str)
                and literal_secret_match(f"{owner}/{slug}", captured)
            ):
                raise YorungeError("invalid_response")
            pending.extend(item.values())
        elif isinstance(item, (list, tuple)):
            pending.extend(item)


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise YorungeError("invalid_response")
    return value


def _array(value: object, limit: int) -> list[object]:
    if not isinstance(value, list) or len(value) > limit:
        raise YorungeError("invalid_response")
    return value


def _project(
    raw: dict[str, object], mapping: Mapping[str, str], required: frozenset[str]
) -> dict[str, object]:
    """Only mapped fields survive. A required one that is missing is ``invalid_response``; an
    optional one that is missing becomes ``None``, which a nullable field admits."""
    out: dict[str, object] = {}
    for target, source in mapping.items():
        if source in raw:
            out[target] = raw[source]
        elif target in required:
            raise YorungeError("invalid_response")
        else:
            out[target] = None
    return out


def _shown(projected: dict[str, object], limits: Mapping[str, int]) -> dict[str, object]:
    for field, limit in limits.items():
        value = projected.get(field)
        if isinstance(value, str):
            projected[field] = catalog.text(value, limit)
    return projected


def _flag(item: Mapping[str, object], source: str) -> bool:
    """A URL field tells only whether a location exists: null and empty mean none; any other
    type is not a URL the provider may send."""
    value = item.get(source)
    if value is None:
        return False
    if type(value) is not str:
        raise YorungeError("invalid_response")
    return value.strip() != ""


def _validate(kind: type[T], data: object) -> T:
    """Strict JSON validation of a projected record: a wrong type is ``invalid_response``."""
    try:
        return kind.model_validate_json(
            json.dumps(data, ensure_ascii=False, allow_nan=False), strict=True
        )
    except ValueError:
        raise YorungeError("invalid_response") from None


def _header_values(headers: Sequence[tuple[str, str]], name: str) -> tuple[str, ...]:
    """Every value of one header, names compared without case; the caller decides what a count
    other than one means. Only the HTTP optional whitespace (space and tab) is trimmed: any other
    character stays, so a value that is not exactly the contract's value is not made to match it."""
    return tuple(value.strip(" \t") for key, value in headers if key.lower() == name)


def _llm_model(raw: object) -> catalog.LlmModel:
    item = _object(raw)
    projected = _shown(_project(item, _LLM_MODEL, _LLM_MODEL_REQUIRED), _SHOWN_LLM_MODEL)
    modalities = projected["modalities"]
    if isinstance(modalities, list):
        projected["modalities"] = [
            catalog.text(value, catalog.NAME_LIMIT) if isinstance(value, str) else value
            for value in modalities
        ]
    pricing = projected["pricing"]
    if pricing is not None:
        priced = _shown(_project(_object(pricing), _LLM_PRICING, _LLM_PRICING_REQUIRED), _SHOWN_LLM)
        projected["pricing"] = _validate(catalog.LlmPricing, priced).model_dump()
    return _validate(catalog.LlmModel, projected)


def llm_listing(data: bytes, secret: SecretValue) -> catalog.LlmListing:
    root = _object(read(data, secret))
    items = _array(root.get("data"), catalog.LLM_MAX_RECORDS)
    listing = _validate(
        catalog.LlmListing, {"models": [_llm_model(item).model_dump() for item in items]}
    )
    _guard(listing, secret)
    return listing


def llm_model(data: bytes, secret: SecretValue) -> catalog.LlmModel:
    model = _llm_model(read(data, secret))
    _guard(model, secret)
    return model


def _platform_model(raw: object) -> catalog.PlatformModel:
    item = _object(raw)
    projected = _shown(
        _project(item, _PLATFORM_MODEL, _PLATFORM_MODEL_REQUIRED), _SHOWN_PLATFORM_MODEL
    )
    return _validate(catalog.PlatformModel, projected)


def platform_models(
    data: bytes, secret: SecretValue, page: int, page_size: int
) -> catalog.PlatformModelPage:
    catalog.page_arguments(page, page_size)
    root = _object(read(data, secret))
    items = _array(root.get("items"), page_size)
    total = root.get("total")
    completeness = catalog.platform_page(page, page_size, total, len(items))
    result = _validate(
        catalog.PlatformModelPage,
        {
            "page": page,
            "page_size": page_size,
            "total": total,
            "returned": len(items),
            "completeness": completeness,
            "models": [_platform_model(item).model_dump() for item in items],
        },
    )
    _guard(result, secret)
    return result


def platform_model(data: bytes, secret: SecretValue) -> catalog.PlatformModel:
    model = _platform_model(read(data, secret))
    _guard(model, secret)
    return model


def _platform_version(raw: object) -> catalog.PlatformVersion:
    item = _object(raw)
    data = _shown(_project(item, _PLATFORM_VERSION, _PLATFORM_VERSION_REQUIRED), _SHOWN_VERSION)
    for flag, source in _WEIGHT_FLAGS.items():
        data[flag] = _flag(item, source)
    return _validate(catalog.PlatformVersion, data)


def platform_versions(
    data: bytes, secret: SecretValue, versions_count: object
) -> catalog.VersionListing:
    items = _array(read(data, secret), catalog.MAX_VERSION_ROWS)
    listed = [_platform_version(item).model_dump() for item in items]
    result = _validate(
        catalog.VersionListing,
        {
            "versions": listed,
            "completeness": catalog.versions_listing(versions_count, len(listed)),
        },
    )
    _guard(result, secret)
    return result


def platform_datasets(
    data: bytes,
    secret: SecretValue,
    page: int,
    page_size: int,
    headers: Sequence[tuple[str, str]],
) -> catalog.DatasetPage:
    catalog.page_arguments(page, page_size)
    items = _array(read(data, secret), page_size)
    completeness = catalog.dataset_page(
        page,
        page_size,
        len(items),
        _header_values(headers, "x-has-next"),
        _header_values(headers, "x-total-count"),
    )
    datasets = [
        _validate(
            catalog.PlatformDataset,
            _shown(
                _project(_object(item), _PLATFORM_DATASET, _PLATFORM_DATASET_REQUIRED),
                _SHOWN_DATASET,
            ),
        ).model_dump()
        for item in items
    ]
    result = _validate(
        catalog.DatasetPage,
        {
            "page": page,
            "page_size": page_size,
            "returned": len(items),
            "completeness": completeness,
            "datasets": datasets,
        },
    )
    _guard(result, secret)
    return result
