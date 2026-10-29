"""Bounded JSON and typed provider data validation before public publication."""

from __future__ import annotations

import json
import math
from collections.abc import Collection
from enum import Enum
from types import UnionType
from typing import Annotated, Literal, TypeVar, Union, get_args, get_origin

from pydantic import BaseModel

from yorunge.domain.credentials import SecretValue
from yorunge.domain.errors import YorungeError

JSON_LIMIT = 1_048_576
JSON_DEPTH = 32
JSON_NODES = 65_536
T = TypeVar("T", bound=BaseModel)


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError("nonfinite JSON constant")


def _structure_children(item: object, depth: int) -> list[tuple[object, int]]:
    if isinstance(item, str):
        item.encode("utf-8", errors="strict")
    elif isinstance(item, float) and not math.isfinite(item):
        raise ValueError("finite JSON number required")
    elif isinstance(item, (dict, list)):
        depth += 1
        if depth > JSON_DEPTH:
            raise ValueError("JSON nesting limit")
        if isinstance(item, dict):
            children = []
            for key, child in item.items():
                children.append((key, depth))
                children.append((child, depth))
            return children
        return [(child, depth) for child in item]
    return []


def _structure(value: object) -> None:
    count, pending = 0, [(value, 0)]
    while pending:
        item, depth = pending.pop()
        count += 1
        if count > JSON_NODES:
            raise ValueError("JSON node limit")
        pending.extend(_structure_children(item, depth))


def parse_json(data: bytes) -> object:
    """Parse one strict JSON value under the shared byte/depth/node budget."""
    if type(data) is not bytes or not data or len(data) > JSON_LIMIT:
        raise YorungeError("invalid_response")
    valid, result = False, None
    try:
        text = data.decode("utf-8", errors="strict")
        result = json.loads(text, object_pairs_hook=_unique, parse_constant=_reject_constant)
        _structure(result)
        valid = True
    except (UnicodeError, ValueError, RecursionError, OverflowError):
        pass
    if not valid:
        raise YorungeError("invalid_response")
    return result


def _fixed_annotation(annotation: object) -> bool:
    origin = get_origin(annotation)
    if origin is Annotated:
        return _fixed_annotation(get_args(annotation)[0])
    if origin is Literal:
        return True
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return True
    args = get_args(annotation)
    return origin in (Union, UnionType) and all(
        arg is type(None) or _fixed_annotation(arg) for arg in args
    )


def _canonical_enum(item: Enum) -> bool:
    value = item.value
    if type(value) not in (str, int, bool, float, type(None)):
        return False
    if isinstance(value, float) and not math.isfinite(value):
        return False
    return any(
        member is item and type(key) is type(value) and key == value
        for key, member in type(item)._value2member_map_.items()
    )


def _fixed_value_matches(item: object, annotation: object) -> bool:
    origin = get_origin(annotation)
    if origin is Annotated:
        return _fixed_value_matches(item, get_args(annotation)[0])
    if annotation is type(None):
        return item is None
    if origin is Literal:
        return any(
            type(item) is type(expected)
            and item == expected
            and (not isinstance(item, Enum) or _canonical_enum(item))
            for expected in get_args(annotation)
        )
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return type(item) is annotation and isinstance(item, Enum) and _canonical_enum(item)
    if origin in (Union, UnionType):
        return any(_fixed_value_matches(item, arg) for arg in get_args(annotation))
    return False


def _protocol_constant(item: object, annotation: object) -> bool:
    if not _fixed_annotation(annotation) and not isinstance(item, Enum):
        return False
    if not _fixed_value_matches(item, annotation):
        raise YorungeError("invalid_response")
    return True


def _container_annotation(annotation: object) -> object:
    origin = get_origin(annotation)
    if origin is Annotated:
        return _container_annotation(get_args(annotation)[0])
    if origin in (Union, UnionType):
        alternatives = tuple(arg for arg in get_args(annotation) if arg is not type(None))
        if len(alternatives) == 1:
            return _container_annotation(alternatives[0])
        # A runtime list/dict does not prove which union branch Pydantic selected.
        # Conservatively check its free leaves instead of guessing Literal exemptions.
        return None
    return annotation


def literal_secret_match(value: str, secret: str) -> bool:
    """Shared provenance rule; this does not classify coincidental fixed protocol fields."""
    return value == secret or (len(secret.encode("utf-8")) >= 8 and secret in value)


def _schema_children(item: object) -> list[object]:
    if isinstance(item, dict):
        # Only schema nodes, not the model's field-name mapping or default JSON data.
        if isinstance(item.get("type"), str) and "serialization" in item:
            raise YorungeError("invalid_response")
        return [value for key, value in item.items() if key not in {"metadata", "default"}]
    if isinstance(item, (list, tuple)):
        return list(item)
    return []


def _closed_codec(model: BaseModel) -> None:
    """Fail closed when typed fields do not describe the complete emitted JSON shape."""
    kind = type(model)
    decorators = kind.__pydantic_decorators__
    if (
        kind.model_config.get("extra") != "forbid"
        or model.model_extra is not None
        or kind.model_computed_fields
        or decorators.field_serializers
        or decorators.model_serializers
        or kind.model_config.get("json_encoders")
        or kind.model_dump is not BaseModel.model_dump
        or kind.model_dump_json is not BaseModel.model_dump_json
    ):
        raise YorungeError("invalid_response")
    schema = kind.__pydantic_core_schema__
    if not isinstance(schema, dict):
        raise YorungeError("invalid_response")
    pending: list[object] = [schema]
    seen: set[int] = set()
    while pending:
        item = pending.pop()
        if id(item) in seen:
            continue
        seen.add(id(item))
        pending.extend(_schema_children(item))


def _model_children(
    model: BaseModel, checked_types: set[type[BaseModel]]
) -> list[tuple[object, object]]:
    if type(model) not in checked_types:
        _closed_codec(model)
        checked_types.add(type(model))
    return [
        (getattr(model, name), field.annotation) for name, field in type(model).model_fields.items()
    ]


def _mapping_children(
    item: dict[object, object], annotation: object
) -> list[tuple[object, object]]:
    args = get_args(_container_annotation(annotation))
    key_annotation, value_annotation = args if len(args) == 2 else (None, None)
    children = []
    for key, value in item.items():
        children.append((key, key_annotation))
        children.append((value, value_annotation))
    return children


def _sequence_children(item: Collection[object], annotation: object) -> list[tuple[object, object]]:
    args = get_args(_container_annotation(annotation))
    children = []
    for index, child in enumerate(item):
        child_annotation = args[0] if args else None
        if isinstance(item, tuple) and len(args) > 1 and args[-1] is not Ellipsis:
            child_annotation = args[index] if index < len(args) else None
        children.append((child, child_annotation))
    return children


def _response_children(
    item: object,
    annotation: object,
    captured: tuple[str, ...],
    checked_types: set[type[BaseModel]],
) -> list[tuple[object, object]]:
    if _protocol_constant(item, annotation):
        return []
    if isinstance(item, BaseModel):
        return _model_children(item, checked_types)
    if isinstance(item, str):
        if any(literal_secret_match(item, secret) for secret in captured):
            raise YorungeError("invalid_response")
        return []
    if isinstance(item, dict):
        return _mapping_children(item, annotation)
    if isinstance(item, (tuple, list, set, frozenset)):
        return _sequence_children(item, annotation)
    if isinstance(item, float) and not math.isfinite(item):
        raise YorungeError("invalid_response")
    if item is not None and type(item) not in (bool, int, float):
        # Unknown typed scalars/serializers must not silently skip reflection checks.
        raise YorungeError("invalid_response")
    return []


def check_response_secrets(model: BaseModel, secrets: tuple[SecretValue, ...]) -> None:
    """Check dynamic provider strings only; fixed fields/Literals/enums are not provenance."""
    if (
        not isinstance(model, BaseModel)
        or type(secrets) is not tuple
        or any(not isinstance(secret, SecretValue) for secret in secrets)
    ):
        raise YorungeError("invalid_response")
    captured = tuple(secret.reveal() for secret in secrets)
    if not captured:
        return
    checked_types: set[type[BaseModel]] = set()
    pending: list[tuple[object, object]] = [(model, None)]
    while pending:
        item, annotation = pending.pop()
        pending.extend(_response_children(item, annotation, captured, checked_types))


def decode_response(data: bytes, model: type[T], *, secrets: tuple[SecretValue, ...] = ()) -> T:
    """Keep strict raw validation and expected model validation separate from HTTP status."""
    parse_json(data)
    value: T | None = None
    try:
        value = model.model_validate_json(data, strict=True)
    except Exception:
        # A validator may raise an ordinary error containing the raw provider value.
        # Cancellation and other BaseException control flow deliberately propagate.
        pass
    if value is None:
        raise YorungeError("invalid_response")
    check_response_secrets(value, secrets)
    return value
