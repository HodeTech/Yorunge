"""Closed control-response predicates; never retain raw provider fields or values."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from yorunge.application.response_json import parse_json
from yorunge.domain.errors import YorungeError

FIELDS = (
    "success",
    "data",
    "message",
    "detail",
    "status",
    "id",
    "dataset_id",
    "project_id",
    "name",
    "modality",
    "visibility",
    "contributions_enabled",
    "owner_id",
    "org_id",
    "created",
    "actual_count",
    "batch_duplicates",
    "presigned_urls",
    "duplicates",
    "filename",
    "sha256_hash",
    "file_size",
    "client_uid",
    "object_key",
    "upload_url",
    "content_type",
    "headers",
    "checksum",
    "ok",
    "linked",
    "added",
    "already_linked",
)
LITERALS = {
    "status_ok": ("status", "ok"),
    "status_success": ("status", "success"),
    "status_linked": ("status", "linked"),
    "message_operation_successful": ("message", "Operation successful"),
    "message_dataset_linked": ("message", "Dataset linked to project"),
    "message_dataset_added": ("message", "Dataset added to project"),
    "message_dataset_linked_successfully": ("message", "Dataset linked to project successfully"),
    "message_dataset_added_successfully": ("message", "Dataset added to project successfully"),
}
TYPES = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    dict: "object",
    list: "array",
    type(None): "null",
}


def facts(value: object, expected: Mapping[str, object]) -> dict[str, Any]:
    result: dict[str, Any] = {"type": TYPES[type(value)]}
    if type(value) is not dict:
        return result
    result["key_count"] = len(value)
    result["fields"] = {key: TYPES[type(value[key])] for key in FIELDS if key in value}
    result["boolean_true"] = {
        key: value[key] is True for key in FIELDS if type(value.get(key)) is bool
    }
    result["literal_predicates"] = {
        label: type(value.get(key)) is str and value[key] == literal
        for label, (key, literal) in LITERALS.items()
    }
    result["matches_expected"] = {
        key: type(value[key]) is type(wanted) and value[key] == wanted
        for key, wanted in expected.items()
        if key in FIELDS and key in value
    }
    if "success" in value:
        result["success_true"] = value["success"] is True
        result["success_false"] = value["success"] is False
    for key in ("presigned_urls", "duplicates"):
        if type(value.get(key)) is list:
            result[key + "_count"] = len(value[key])
    return result


def body_shape(data: bytes, expected: Mapping[str, object]) -> dict[str, Any]:
    try:
        value = parse_json(data, max_bytes=1_048_576)
    except YorungeError as error:
        return {"json_valid": False, "error_code": error.code, "empty": not data}
    result = {"json_valid": True, "root": facts(value, expected)}
    if type(value) is dict and "data" in value:
        result["data"] = facts(value["data"], expected)
    payload = value.get("data", value) if type(value) is dict else value
    if type(payload) is dict and type(payload.get("presigned_urls")) is list:
        rows = payload["presigned_urls"]
        if len(rows) == 1:
            result["presigned_item"] = facts(rows[0], expected)
    return result
