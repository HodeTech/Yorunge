"""Interim raw-tree safety checks and narrow, closed Platform projections."""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel

from yorunge.application.response_json import literal_secret_match, parse_json
from yorunge.domain.credentials import SecretValue
from yorunge.domain.errors import YorungeError
from yorunge.domain.platform_discovery import (
    OrganizationListing,
    OrganizationRef,
    ProjectRef,
    ReportedIdentity,
    ReportedState,
)

T = TypeVar("T", bound=BaseModel)


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise YorungeError("invalid_response")
    return value


def _validate(kind: type[T], value: object) -> T:
    # JSON validation admits wire arrays as tuples while retaining strict scalar types.
    try:
        return kind.model_validate_json(
            json.dumps(value, ensure_ascii=False, allow_nan=False), strict=True
        )
    except ValueError:
        raise YorungeError("invalid_response") from None


def _keys(endpoint: str, path: tuple[str, ...]) -> frozenset[str]:
    if path == ():
        if endpoint == "me":
            return frozenset({"success", "data"})
        if endpoint == "organizations":
            return frozenset({"success", "items", "total"})
        if endpoint == "detail":
            return frozenset({"success", "data", "id", "org_id"})
    if endpoint == "me" and path == ("data",):
        return frozenset({"id", "organization_id", "personal_org_id"})
    if endpoint == "organizations" and path == ("items", "[]"):
        return frozenset({"id"})
    if (endpoint == "projects" and path == ("[]",)) or (endpoint == "detail" and path == ("data",)):
        return frozenset({"id", "org_id"})
    return frozenset()


def safe_raw(data: bytes, endpoint: str, secret: SecretValue) -> object:
    value = parse_json(data)
    captured = secret.reveal()
    pending: list[tuple[object, tuple[str, ...]]] = [(value, ())]
    while pending:
        item, path = pending.pop()
        if isinstance(item, str) and literal_secret_match(item, captured):
            raise YorungeError("invalid_response")
        if isinstance(item, dict):
            fixed = _keys(endpoint, path)
            for key, child in item.items():
                if key not in fixed and literal_secret_match(key, captured):
                    raise YorungeError("invalid_response")
                pending.append((child, (*path, key)))
        elif isinstance(item, list):
            pending.extend((child, (*path, "[]")) for child in item)
    if isinstance(value, dict) and "success" in value and value["success"] is not True:
        raise YorungeError("invalid_response")
    return value


def _parent(raw: dict[str, object], key: str) -> tuple[object, ReportedState]:
    if key not in raw:
        return None, "not_exposed"
    value = raw[key]
    return value, "reported_null" if value is None else "reported_id"


def identity(value: object) -> ReportedIdentity:
    root = _object(value)
    if root.get("success") is not True:
        raise YorungeError("invalid_response")
    data = _object(root.get("data"))
    org, org_state = _parent(data, "organization_id")
    personal, personal_state = _parent(data, "personal_org_id")
    return _validate(
        ReportedIdentity,
        {
            "me_id": data.get("id"),
            "organization_id": org,
            "organization_id_state": org_state,
            "personal_organization_id": personal,
            "personal_organization_id_state": personal_state,
        },
    )


def _items(value: object) -> list[object]:
    if not isinstance(value, list) or len(value) > 128:
        raise YorungeError("invalid_response")
    return value


def organizations(value: object) -> OrganizationListing:
    root = _object(value)
    items = tuple(
        _validate(OrganizationRef, {"id": _object(v).get("id")}) for v in _items(root.get("items"))
    )
    return _validate(
        OrganizationListing,
        {"items": [v.model_dump() for v in items], "reported_total": root.get("total")},
    )


def project(value: object) -> ProjectRef:
    raw = _object(value)
    org, state = _parent(raw, "org_id")
    return _validate(
        ProjectRef, {"id": raw.get("id"), "organization_id": org, "organization_id_state": state}
    )


def projects(value: object) -> tuple[ProjectRef, ...]:
    items = tuple(project(v) for v in _items(value))
    if len({v.id for v in items}) != len(items):
        raise YorungeError("invalid_response")
    return items


def detail(value: object, selected: str) -> ProjectRef:
    root = _object(value)
    result = project(root.get("data") if "success" in root else root)
    if result.id != selected:
        raise YorungeError("invalid_response")
    return result
