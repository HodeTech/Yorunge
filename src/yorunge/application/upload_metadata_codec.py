"""Closed acknowledgements and item pages; no write replay or remote-byte claims."""

from yorunge.application import platform_upload_codec as control
from yorunge.domain.credentials import SecretValue
from yorunge.domain.dataset_manifest import safe_text
from yorunge.domain.errors import YorungeError
from yorunge.domain.platform_upload_items import ProviderItems

_ITEM_FIELDS = frozenset(
    {"id", "dataset_id", "original_filename", "file_size_bytes", "sha256_hash"}
)


def put_ack(data: bytes, secret: SecretValue) -> None:
    if len(data) > 64 * 1024:
        raise YorungeError("invalid_response")
    control.link_ack(data, secret)


def _count(root: dict[str, object], key: str, expected: int, *, required: bool = False) -> None:
    if key not in root and not required:
        return
    value = root.get(key)
    if type(value) is not int or value != expected:
        raise YorungeError("invalid_response")


def confirm_ack(data: bytes, confirmed_count: int, secret: SecretValue) -> None:
    if type(confirmed_count) is not int or not 1 <= confirmed_count <= 128:
        raise YorungeError("invalid_request")
    root = control._object(control.raw(data, "confirm", secret))
    _count(root, "created", 1, required=True)
    _count(root, "actual_count", confirmed_count)
    _count(root, "batch_duplicates", 0)


def items(data: bytes, dataset_id: str, secret: SecretValue) -> ProviderItems:
    root = control._object(control.raw(data, "items", secret))
    value = control._projection(root, frozenset({"items", "next_cursor", "total"}))
    rows = value["items"]
    if not isinstance(rows, list):
        raise YorungeError("invalid_response")
    value["items"] = [control._projection(row, _ITEM_FIELDS) for row in rows]
    result = control._validate(ProviderItems, value)
    if any(item.dataset_id != dataset_id for item in result.items):
        raise YorungeError("invalid_response")
    return result


def item_query(cursor: str | None, secret: SecretValue) -> tuple[tuple[str, str], ...]:
    if cursor is None:
        return (("limit", "128"),)
    try:
        if type(cursor) is not str or not 1 <= len(safe_text(cursor)) <= 1024:
            raise ValueError("bounded cursor required")
    except (ValueError, UnicodeError):
        raise YorungeError("invalid_request") from None
    control._scan(cursor, secret, {}, error="invalid_request")
    return (("limit", "128"), ("cursor", cursor))
