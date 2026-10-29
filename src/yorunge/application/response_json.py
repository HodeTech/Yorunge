"""Bounded JSON and typed provider data validation before public publication."""

from __future__ import annotations

import json
import math
from enum import Enum
from types import UnionType
from typing import Annotated, Literal, TypeVar, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError

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


def _structure(value: object) -> None:
    count, pending = 0, [(value, 0)]
    while pending:
        item, depth = pending.pop()
        count += 1
        if count > JSON_NODES:
            raise ValueError("JSON node limit")
        if isinstance(item, str):
            item.encode("utf-8", errors="strict")
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError("finite JSON number required")
        elif isinstance(item, (dict, list)):
            depth += 1
            if depth > JSON_DEPTH:
                raise ValueError("JSON nesting limit")
            if isinstance(item, dict):
                for key, child in item.items():
                    if key == "schema_version" and type(child) is not int:
                        raise ValueError("integer schema version required")
                    pending.append((key, depth))
                    pending.append((child, depth))
            else:
                pending.extend((child, depth) for child in item)


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
    args = get_args(annotation)
    return origin in (Union, UnionType) and all(
        arg is type(None) or _fixed_annotation(arg) for arg in args
    )


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
    pending: list[tuple[object, object]] = [(model, None)]
    while pending:
        item, annotation = pending.pop()
        if _fixed_annotation(annotation) or isinstance(item, Enum):
            continue
        if isinstance(item, BaseModel):
            for name, field in type(item).model_fields.items():
                pending.append((getattr(item, name), field.annotation))
        elif isinstance(item, str):
            if any(literal_secret_match(item, secret) for secret in captured):
                raise YorungeError("invalid_response")
        elif isinstance(item, dict):
            args = get_args(_container_annotation(annotation))
            key_annotation, value_annotation = args if len(args) == 2 else (None, None)
            for key, value in item.items():
                pending.append((key, key_annotation))
                pending.append((value, value_annotation))
        elif isinstance(item, (tuple, list, set, frozenset)):
            args = get_args(_container_annotation(annotation))
            for index, child in enumerate(item):
                child_annotation = args[0] if args else None
                if isinstance(item, tuple) and len(args) > 1 and args[-1] is not Ellipsis:
                    child_annotation = args[index] if index < len(args) else None
                pending.append((child, child_annotation))
        elif isinstance(item, float) and not math.isfinite(item):
            raise YorungeError("invalid_response")
        elif item is not None and type(item) not in (bool, int, float):
            # Unknown typed scalars/serializers must not silently skip reflection checks.
            raise YorungeError("invalid_response")


def decode_response(data: bytes, model: type[T], *, secrets: tuple[SecretValue, ...] = ()) -> T:
    """Keep strict raw validation and expected model validation separate from HTTP status."""
    parse_json(data)
    value: T | None = None
    try:
        value = model.model_validate_json(data, strict=True)
    except (ValidationError, ValueError, TypeError, AttributeError):
        pass
    if value is None:
        raise YorungeError("invalid_response")
    check_response_secrets(value, secrets)
    return value
