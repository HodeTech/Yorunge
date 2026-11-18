"""The narrow catalog reader: strict JSON, a secret scan of the whole answer, consumed fields.

ADR-0035 Karar 8 and ADR-0022’s observer pattern. The answer is parsed under the shared JSON
budget, the whole tree is scanned for the selected key (used or dropped), and then only the fields
``domain.catalog`` consumes are picked and validated strictly. Unconsumed provider fields are
ignored and never reach a result. No I/O: the transport supplies bytes and the headers.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Final, TypeVar

from pydantic import BaseModel

from yorunge.application.response_json import JSON_LIMIT, parse_json, scan_for_secret
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
_WEIGHT_FLAGS: Final = {
    "has_weights": "weights_url",
    "has_onnx": "onnx_url",
    "has_tflite": "tflite_url",
}


def read(data: bytes, secret: SecretValue) -> object:
    """Strict JSON under the shared budget, then the literal-secret scan of every key and string."""
    value = parse_json(data, max_bytes=JSON_LIMIT)
    scan_for_secret(value, secret)
    return value


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
    """Only mapped fields survive; a required one missing is ``invalid_response``, an optional one
    missing is ``None`` (the model then sees null, which a nullable field admits)."""
    out: dict[str, object] = {}
    for target, source in mapping.items():
        if source in raw:
            out[target] = raw[source]
        elif target in required:
            raise YorungeError("invalid_response")
        else:
            out[target] = None
    return out


# Display fields are cleaned as they are read; identifiers are never cleaned, because a cleaned
# identifier could name a different model than the one the provider sent (zero-width characters).
_SHOWN_LLM: Final = {
    "precision": catalog.NAME_LIMIT,
    "currency": catalog.NAME_LIMIT,
    "free_until": catalog.NAME_LIMIT,
}
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


def _shown(projected: dict[str, object], limits: Mapping[str, int]) -> dict[str, object]:
    for field, limit in limits.items():
        value = projected.get(field)
        if isinstance(value, str):
            projected[field] = catalog.text(value, limit)
    return projected


def _validate(kind: type[T], data: object) -> T:
    """Strict JSON validation of a projected record: a wrong type is ``invalid_response``."""
    try:
        return kind.model_validate_json(
            json.dumps(data, ensure_ascii=False, allow_nan=False), strict=True
        )
    except ValueError:
        raise YorungeError("invalid_response") from None


def _llm_model(raw: object) -> catalog.LlmModel:
    item = _object(raw)
    projected = _project(item, _LLM_MODEL, _LLM_MODEL_REQUIRED)
    if isinstance(projected["modalities"], list):
        projected["modalities"] = [
            catalog.text(value, catalog.NAME_LIMIT) if isinstance(value, str) else value
            for value in projected["modalities"]
        ]
    pricing = projected["pricing"]
    if pricing is not None:
        priced = _shown(_project(_object(pricing), _LLM_PRICING, _LLM_PRICING_REQUIRED), _SHOWN_LLM)
        projected["pricing"] = _validate(catalog.LlmPricing, priced).model_dump()
    _shown(projected, {"precision": catalog.NAME_LIMIT})
    return _validate(catalog.LlmModel, projected)


def llm_listing(raw: object) -> catalog.LlmListing:
    root = _object(raw)
    items = _array(root.get("data"), catalog.LLM_MAX_RECORDS)
    return _validate(
        catalog.LlmListing, {"models": [_llm_model(item).model_dump() for item in items]}
    )


def llm_model(raw: object) -> catalog.LlmModel:
    return _llm_model(raw)


def _platform_model(raw: object) -> catalog.PlatformModel:
    item = _object(raw)
    projected = _shown(
        _project(item, _PLATFORM_MODEL, _PLATFORM_MODEL_REQUIRED), _SHOWN_PLATFORM_MODEL
    )
    return _validate(catalog.PlatformModel, projected)


def platform_models(raw: object, page: int, page_size: int) -> catalog.PlatformModelPage:
    catalog.page_arguments(page, page_size)
    root = _object(raw)
    items = _array(root.get("items"), page_size)
    total = root.get("total")
    completeness = catalog.platform_page(page, page_size, total, len(items))
    return _validate(
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


def platform_model(raw: object) -> catalog.PlatformModel:
    return _platform_model(raw)


def _platform_version(raw: object) -> catalog.PlatformVersion:
    item = _object(raw)
    data = _shown(_project(item, _PLATFORM_VERSION, _PLATFORM_VERSION_REQUIRED), _SHOWN_VERSION)
    for flag, source in _WEIGHT_FLAGS.items():
        data[flag] = source in item and item[source] is not None
    return _validate(catalog.PlatformVersion, data)


def platform_versions(raw: object, versions_count: int) -> catalog.VersionListing:
    items = _array(raw, catalog.MAX_VERSION_ROWS)
    listed = [_platform_version(item).model_dump() for item in items]
    return _validate(
        catalog.VersionListing,
        {
            "versions": listed,
            "completeness": catalog.versions_listing(versions_count, len(listed)),
        },
    )


def platform_datasets(
    raw: object,
    page: int,
    page_size: int,
    headers: Mapping[str, str],
) -> catalog.DatasetPage:
    catalog.page_arguments(page, page_size)
    items = _array(raw, page_size)
    has_next_header = _header(headers, "x-has-next")
    total_header = _header(headers, "x-total-count")
    completeness = catalog.dataset_page(page, page_size, len(items), has_next_header, total_header)
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
    return _validate(
        catalog.DatasetPage,
        {
            "page": page,
            "page_size": page_size,
            "returned": len(items),
            "completeness": completeness,
            "datasets": datasets,
        },
    )


def _header(headers: Mapping[str, str], name: str) -> str | None:
    """Header names are case-insensitive; a repeated header is unclear, hence ``None``."""
    found = [value for key, value in headers.items() if key.lower() == name]
    if len(found) != 1:
        return None
    return found[0].strip()
