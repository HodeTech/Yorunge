"""Closed service URI provenance; this is neither a body codec nor authorization."""

from __future__ import annotations

import re
from typing import Literal

from yorunge.domain.credentials import ServiceId, ServiceTarget
from yorunge.domain.errors import YorungeError

OWNED_PAGE_SIZE = 20
OWNED_MAX_PAGES = 128

UploadEndpoint = Literal[
    "me",
    "project",
    "create",
    "project_link",
    "membership",
    "owned",
    "detail",
    "role",
    "presign",
    "confirm",
    "items",
]
_METHODS: dict[UploadEndpoint, str] = {
    "me": "GET",
    "project": "GET",
    "create": "POST",
    "project_link": "POST",
    "membership": "GET",
    "owned": "GET",
    "detail": "GET",
    "role": "GET",
    "presign": "POST",
    "confirm": "POST",
    "items": "GET",
}
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.ASCII)
_SEGMENT = re.compile(r"[A-Za-z0-9_-]{1,128}", re.ASCII)


def _identifier(value: str) -> str:
    # Provider UUID versions are unrestricted; canonical spelling is still exact.
    if _UUID.fullmatch(value) is None:
        raise YorungeError("invalid_service_target")
    return value


def _route(kind: UploadEndpoint, endpoint: str) -> tuple[str, ...]:
    if kind in {"me", "create", "owned"}:
        fixed = "auth/me" if kind == "me" else "datasets"
        if endpoint != fixed:
            raise YorungeError("invalid_service_target")
        return ()
    parts = endpoint.split("/")
    if kind == "detail":
        if (
            len(parts) != 3
            or parts[0] != "datasets"
            or any(_SEGMENT.fullmatch(part) is None for part in parts[1:])
        ):
            raise YorungeError("invalid_service_target")
        return tuple(parts[1:])
    prefix = "projects" if kind in {"project", "project_link", "membership"} else "datasets"
    suffixes: dict[UploadEndpoint, tuple[str, ...]] = {
        "project": (),
        "project_link": ("datasets",),
        "membership": ("datasets",),
        "role": ("my-role",),
        "presign": ("upload", "presign"),
        "confirm": ("upload", "confirm"),
        "items": ("items",),
    }
    if len(parts) < 2 or parts[0] != prefix or tuple(parts[2:]) != suffixes[kind]:
        raise YorungeError("invalid_service_target")
    return (_identifier(parts[1]),)


def _owned_query(values: dict[str, str]) -> tuple[str, ...]:
    page = values.get("page", "")
    if (
        set(values) != {"page", "page_size", "scope"}
        or values["page_size"] != str(OWNED_PAGE_SIZE)
        or values["scope"] != "owned"
        or re.fullmatch(r"[1-9]\d{0,2}", page, flags=re.ASCII) is None
        or int(page) > OWNED_MAX_PAGES
    ):
        raise YorungeError("invalid_service_target")
    return ()


def _items_query(values: dict[str, str]) -> tuple[str, ...]:
    if values.get("limit") != "128" or set(values) - {"limit", "cursor"}:
        raise YorungeError("invalid_service_target")
    if "cursor" not in values:
        return ()
    cursor = values["cursor"]
    from yorunge.domain.dataset_manifest import safe_text

    try:
        size = len(safe_text(cursor))
    except ValueError:
        raise YorungeError("invalid_service_target") from None
    if not 1 <= size <= 1024:
        raise YorungeError("invalid_service_target")
    return (cursor,)


def _query(kind: UploadEndpoint, query: tuple[tuple[str, str], ...]) -> tuple[str, ...]:
    values = dict(query)
    if len(values) != len(query):
        raise YorungeError("invalid_service_target")
    if kind == "owned":
        return _owned_query(values)
    if kind == "items":
        return _items_query(values)
    if values:
        raise YorungeError("invalid_service_target")
    return ()


def upload_uri_values(
    kind: UploadEndpoint,
    *,
    service_id: ServiceId,
    target: ServiceTarget,
    method: str,
    endpoint: str,
    query: tuple[tuple[str, str], ...],
    read_only: bool,
) -> tuple[str, ...]:
    if type(kind) is not str or kind not in _METHODS:
        raise YorungeError("invalid_request")
    if (
        service_id != "evren-platform"
        or target.service_origin != "https://api.ssyz.org.tr"
        or target.api_base_path != "/api/v1"
        or method != _METHODS[kind]
        or read_only != (method == "GET")
    ):
        raise YorungeError("invalid_service_target")
    return (*_route(kind, endpoint), *_query(kind, query))
