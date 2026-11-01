"""Strict consumed-field checks and closed projections for the limited Platform observer."""

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


_PROJECT_KEYS = frozenset({"id", "org_id"})
_FIXED_KEYS = {
    ("me", ()): frozenset({"success", "data"}),
    ("organizations", ()): frozenset({"success", "items", "total"}),
    ("detail-envelope", ()): frozenset({"success", "data"}),
    ("detail", ()): _PROJECT_KEYS,
    ("me", ("data",)): frozenset({"id", "organization_id", "personal_org_id"}),
    ("organizations", ("items", "[]")): frozenset({"id"}),
    ("projects", ("[]",)): _PROJECT_KEYS,
    ("detail-envelope", ("data",)): _PROJECT_KEYS,
}


def _raw_children(
    item: object, path: tuple[str, ...], endpoint: str, captured: str
) -> list[tuple[object, tuple[str, ...]]]:
    if isinstance(item, str) and literal_secret_match(item, captured):
        raise YorungeError("invalid_response")
    if isinstance(item, dict):
        fixed = _FIXED_KEYS.get((endpoint, path), frozenset())
        children = []
        for key, child in item.items():
            if key not in fixed and literal_secret_match(key, captured):
                raise YorungeError("invalid_response")
            children.append((child, (*path, key)))
        return children
    if isinstance(item, list):
        return [(child, (*path, "[]")) for child in item]
    return []


def safe_raw(data: bytes, endpoint: str, secret: SecretValue) -> object:
    value = parse_json(data)
    # Only the selected raw shape defines fixed protocol keys. A wrapper root
    # id/org_id or a bare object data subtree is discarded, untrusted metadata.
    if endpoint == "detail" and isinstance(value, dict) and "success" in value:
        endpoint = "detail-envelope"
    captured = secret.reveal()
    pending: list[tuple[object, tuple[str, ...]]] = [(value, ())]
    while pending:
        item, path = pending.pop()
        pending.extend(_raw_children(item, path, endpoint, captured))
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
