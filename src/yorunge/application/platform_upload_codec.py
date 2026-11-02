"""Strict control-plane projection and request codecs, with no network or grants."""

from __future__ import annotations

import re
from typing import Literal, TypeVar

from pydantic import BaseModel

from yorunge.application.response_json import literal_secret_match, parse_json
from yorunge.domain.capabilities import canonical
from yorunge.domain.credentials import SecretValue
from yorunge.domain.dataset_upload import UploadParameters, UploadScope, provider_uuid
from yorunge.domain.errors import YorungeError
from yorunge.domain.platform_upload import (
    LocatedDataset,
    ProviderDataset,
    ProviderProject,
    ProviderRole,
)

Kind = Literal["identity", "project", "dataset", "owned", "membership", "role", "link"]
T = TypeVar("T", bound=BaseModel)
_PROJECT = frozenset({"id", "owner_id", "org_id", "visibility"})
_DATASET = _PROJECT | {"name", "modality", "contributions_enabled"}
_LOCATED = _DATASET | {"owner_username", "slug"}
_FIELDS: dict[Kind, frozenset[str]] = {
    "identity": frozenset({"id"}),
    "project": _PROJECT,
    "dataset": _DATASET,
    "owned": _LOCATED,
    "membership": frozenset({"id"}),
    "role": frozenset({"role", "permissions"}),
    "link": frozenset(),
}


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise YorungeError("invalid_response")
    return value


def _validate(kind: type[T], value: object) -> T:
    try:
        return kind.model_validate_json(canonical(value), strict=True)
    except ValueError:
        raise YorungeError("invalid_response") from None


def _identifier(
    value: object, *, error: Literal["invalid_response", "invalid_request"] = "invalid_response"
) -> str:
    if type(value) is not str:
        raise YorungeError(error)
    try:
        return provider_uuid(value)
    except ValueError:
        raise YorungeError(error) from None


def _children(
    item: object,
    path: tuple[str, ...],
    fixed: dict[tuple[str, ...], frozenset[str]],
    captured: str,
    error: Literal["invalid_response", "invalid_request"],
) -> list[tuple[object, tuple[str, ...]]]:
    if isinstance(item, dict):
        children = []
        for key, child in item.items():
            if key not in fixed.get(path, frozenset()) and literal_secret_match(key, captured):
                raise YorungeError(error)
            children.append((child, (*path, key)))
        return children
    if isinstance(item, list):
        return [(child, (*path, str(index))) for index, child in enumerate(item)]
    return []


def _scan(
    value: object,
    secret: SecretValue,
    fixed: dict[tuple[str, ...], frozenset[str]],
    *,
    error: Literal["invalid_response", "invalid_request"],
) -> None:
    captured = secret.reveal()
    pending: list[tuple[object, tuple[str, ...]]] = [(value, ())]
    while pending:
        item, path = pending.pop()
        if isinstance(item, str) and literal_secret_match(item, captured):
            raise YorungeError(error)
        pending.extend(_children(item, path, fixed, captured, error))


def _fixed_keys(
    value: object, kind: Kind, wrapped: bool, selected_id: str | None
) -> dict[tuple[str, ...], frozenset[str]]:
    prefix = ("data",) if wrapped else ()
    fixed: dict[tuple[str, ...], frozenset[str]] = {prefix: _FIELDS[kind]}
    if kind in {"owned", "membership"}:
        payload = _object(value).get("data") if wrapped else value
        if not isinstance(payload, list) or len(payload) > 128:
            raise YorungeError("invalid_response")
        fixed = {}
        for index, row in enumerate(payload):
            consumed = kind == "owned" and isinstance(row, dict) and row.get("id") == selected_id
            fixed[(*prefix, str(index))] = _LOCATED if consumed else frozenset({"id"})
    if wrapped:
        fixed[()] = frozenset({"success"}) if kind == "link" else frozenset({"success", "data"})
    return fixed


def raw(data: bytes, kind: Kind, secret: SecretValue, *, selected_id: str | None = None) -> object:
    value = parse_json(data)
    wrapped = isinstance(value, dict) and "success" in value
    _scan(value, secret, _fixed_keys(value, kind, wrapped, selected_id), error="invalid_response")
    if wrapped:
        root = _object(value)
        if root["success"] is not True:
            raise YorungeError("invalid_response")
        return root if kind == "link" else root.get("data")
    if kind == "identity":
        raise YorungeError("invalid_response")
    return value


def _projection(value: object, fields: frozenset[str]) -> dict[str, object]:
    source = _object(value)
    # Missing nullable fields must not become implicit nulls.
    if not fields <= source.keys():
        raise YorungeError("invalid_response")
    return {name: source[name] for name in fields}


def identity(data: bytes, secret: SecretValue) -> str:
    return _identifier(_object(raw(data, "identity", secret)).get("id"))


def project(data: bytes, scope: UploadScope, secret: SecretValue) -> ProviderProject:
    result = _validate(ProviderProject, _projection(raw(data, "project", secret), _PROJECT))
    owner = result.owner_id if scope.owner.kind == "user" else result.org_id
    if result.id != scope.project_id or owner != scope.owner.id:
        raise YorungeError("invalid_response")
    return result


def context(me_id: str, selected: ProviderProject, scope: UploadScope) -> None:
    _identifier(me_id)
    if selected.id != scope.project_id:
        raise YorungeError("invalid_response")
    owner = selected.owner_id if scope.owner.kind == "user" else selected.org_id
    if owner != scope.owner.id or (scope.owner.kind == "user" and me_id != scope.owner.id):
        raise YorungeError("invalid_response")


def _owner(result: ProviderDataset, scope: UploadScope, parameters: UploadParameters) -> None:
    owner = result.owner_id if scope.owner.kind == "user" else result.org_id
    if (
        owner != scope.owner.id
        or result.name != parameters.name
        or result.modality != parameters.modality
    ):
        raise YorungeError("invalid_response")


def created(
    data: bytes, scope: UploadScope, parameters: UploadParameters, secret: SecretValue
) -> ProviderDataset:
    result = _validate(ProviderDataset, _projection(raw(data, "dataset", secret), _DATASET))
    _owner(result, scope, parameters)
    return result


def detail(
    data: bytes,
    expected: ProviderDataset,
    scope: UploadScope,
    parameters: UploadParameters,
    secret: SecretValue,
) -> ProviderDataset:
    result = created(data, scope, parameters, secret)
    if result != expected:
        raise YorungeError("invalid_response")
    return result


def _rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or len(value) > 128:
        raise YorungeError("invalid_response")
    result = [_object(row) for row in value]
    ids = [_identifier(row.get("id")) for row in result]
    if len(ids) != len(set(ids)):
        raise YorungeError("invalid_response")
    return result


def owned_match(
    data: bytes,
    dataset_id: str,
    scope: UploadScope,
    parameters: UploadParameters,
    secret: SecretValue,
) -> LocatedDataset | None:
    rows = _rows(raw(data, "owned", secret, selected_id=dataset_id))
    selected = next((row for row in rows if row["id"] == dataset_id), None)
    if selected is None:
        return None
    result = _validate(LocatedDataset, _projection(selected, _LOCATED))
    _owner(result, scope, parameters)
    return result


def membership(data: bytes, dataset_id: str, secret: SecretValue) -> bool:
    return any(row["id"] == dataset_id for row in _rows(raw(data, "membership", secret)))


def role(data: bytes, secret: SecretValue) -> ProviderRole:
    result = _validate(ProviderRole, _projection(raw(data, "role", secret), _FIELDS["role"]))
    if "upload" not in result.permissions:
        raise YorungeError("remote_access_denied")
    return result


def link_ack(data: bytes, secret: SecretValue) -> None:
    if data and _object(raw(data, "link", secret)).get("success") is not True:
        raise YorungeError("invalid_response")


def _request(value: dict[str, object], secret: SecretValue) -> bytes:
    _scan(value, secret, {(): frozenset(value)}, error="invalid_request")
    return canonical(value)


def _request_input(kind: type[T], value: T) -> T:
    # Frozen models can still be copied/constructed without validation. Never
    # serialize such an object into an effectful provider request unchecked.
    if type(value) is not kind:
        raise YorungeError("invalid_request")
    try:
        # Validate Python scalars first: JSON serialization may normalize an
        # unvalidated bool in an integer field to 0/1 before a JSON validator.
        checked = kind.model_validate(value.model_dump(mode="python"), strict=True)
        return kind.model_validate_json(canonical(checked.model_dump(mode="json")), strict=True)
    except (ValueError, YorungeError):
        raise YorungeError("invalid_request") from None


def create_content(scope: UploadScope, parameters: UploadParameters, secret: SecretValue) -> bytes:
    scope = _request_input(UploadScope, scope)
    parameters = _request_input(UploadParameters, parameters)
    value: dict[str, object] = {
        "name": parameters.name,
        "modality": parameters.modality,
        "visibility": parameters.visibility,
        "contributions_enabled": parameters.contributions_enabled,
        "tags": list(parameters.tags),
    }
    if parameters.license is not None:
        value["license"] = parameters.license
    if scope.owner.kind == "organization":
        value["org_id"] = scope.owner.id
    return _request(value, secret)


def link_content(dataset_id: str, secret: SecretValue) -> bytes:
    return _request({"dataset_id": _identifier(dataset_id, error="invalid_request")}, secret)


def segment(value: str, secret: SecretValue) -> str:
    # Validate each dynamic segment before the fixed prefix can hide a short secret.
    if (
        type(value) is not str
        or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value, flags=re.ASCII) is None
    ):
        raise YorungeError("invalid_request")
    _scan(value, secret, {}, error="invalid_request")
    return value


def detail_path(value: LocatedDataset, secret: SecretValue) -> str:
    return f"datasets/{segment(value.owner_username, secret)}/{segment(value.slug, secret)}"
