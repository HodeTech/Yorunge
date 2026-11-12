"""Closed acknowledgements and item pages; no write replay or remote-byte claims."""

from typing import TypeVar

from yorunge.application import platform_upload_codec as control
from yorunge.application.storage import validate_object_key
from yorunge.domain.credentials import SecretValue
from yorunge.domain.dataset_manifest import safe_text
from yorunge.domain.errors import YorungeError
from yorunge.domain.platform_upload_items import ProviderItems, ProviderItemsPage

_Page = TypeVar("_Page", bound=ProviderItemsPage)
_ITEM_FIELDS = frozenset(
    {"id", "dataset_id", "original_filename", "file_size_bytes", "sha256_hash"}
)


def put_ack(
    data: bytes,
    secret: SecretValue,
    *,
    expected_size: int | None = None,
    expected_key: SecretValue | None = None,
) -> None:
    if len(data) > 64 * 1024:
        raise YorungeError("invalid_response")
    if expected_size is None and expected_key is None:
        control.link_ack(data, secret)
        return
    if (
        type(expected_size) is not int
        or not 0 <= expected_size <= 500_000_000
        or type(expected_key) is not SecretValue
    ):
        raise YorungeError("invalid_request")
    try:
        key = validate_object_key(expected_key.reveal())
    except YorungeError:
        raise YorungeError("invalid_request") from None
    control._require_secret(secret)
    if not data:
        return
    root = control._object(control.raw(data, "put_ack", secret))
    control._ack_controls(root, None)
    _put_controls(root, expected_size, key)
    if root.get("success") is not True and (root.get("ok") is not True or "size" not in root):
        raise YorungeError("invalid_response")


def _put_controls(root: dict[str, object], size: int, key: str) -> None:
    for node in (root, root.get("data")):
        if type(node) is not dict:
            continue
        if "ok" in node and node["ok"] is not True:
            raise YorungeError("invalid_response")
        if "size" in node and (type(node["size"]) is not int or node["size"] != size):
            raise YorungeError("invalid_response")
        if any(
            type(node[field]) is not str or node[field] != key
            for field in ("key", "object_key")
            if field in node
        ):
            raise YorungeError("invalid_response")


def _count(
    root: dict[str, object],
    key: str,
    expected: int,
    *,
    required: bool = False,
    also: tuple[int, ...] = (),
) -> None:
    if key not in root and not required:
        return
    value = root.get(key)
    if type(value) is not int or value not in (expected, *also):
        raise YorungeError("invalid_response")


def confirm_ack(data: bytes, confirmed_count: int, secret: SecretValue, *, base: int = 0) -> None:
    """One confirm took effect, once, and the count it reports is one of the two it may mean.

    ``confirmed_count`` is the confirm's place in its own operation (k + 1). ``actual_count`` is
    that, or, when the dataset already held ``base`` items before the operation (a continuation:
    ``plan.continuation.remote_present_count``), the dataset's own count (``base`` + k + 1): the
    provider's meaning is not documented for a dataset that is not new, so either is accepted and
    nothing else is. Without a base there is a single value, as for an original upload.
    """
    if (
        type(confirmed_count) is not int
        or not 1 <= confirmed_count <= 128
        or type(base) is not int
        or not 0 <= base <= 128 - confirmed_count
    ):
        raise YorungeError("invalid_request")
    root = control._object(control.raw(data, "confirm", secret))
    _count(root, "created", 1, required=True)
    _count(root, "actual_count", confirmed_count, also=(base + confirmed_count,))
    _count(root, "batch_duplicates", 0)


def _items_page(data: bytes, dataset_id: str, secret: SecretValue, model: type[_Page]) -> _Page:
    root = control._object(control.raw(data, "items", secret))
    value = control._projection(root, frozenset({"items", "next_cursor", "total"}))
    rows = value["items"]
    if not isinstance(rows, list):
        raise YorungeError("invalid_response")
    value["items"] = [control._projection(row, _ITEM_FIELDS) for row in rows]
    result = control._validate(model, value)
    if any(item.dataset_id != dataset_id for item in result.items):
        raise YorungeError("invalid_response")
    return result


def items(data: bytes, dataset_id: str, secret: SecretValue) -> ProviderItems:
    """A page whose items are also distinct by identity and name."""
    return _items_page(data, dataset_id, secret, ProviderItems)


def item_page(data: bytes, dataset_id: str, secret: SecretValue) -> ProviderItemsPage:
    """A structurally valid page; duplicate identities and names are left to the reducer."""
    return _items_page(data, dataset_id, secret, ProviderItemsPage)


def item_query(cursor: str | None, secret: SecretValue) -> tuple[tuple[str, str], ...]:
    if cursor is None:
        return (("limit", "128"),)
    try:
        if type(cursor) is not str or not 1 <= len(safe_text(cursor)) <= 1024:
            raise ValueError("bounded cursor required")
    except ValueError:
        raise YorungeError("invalid_request") from None
    control._scan(cursor, secret, {}, error="invalid_request")
    return (("limit", "128"), ("cursor", cursor))
