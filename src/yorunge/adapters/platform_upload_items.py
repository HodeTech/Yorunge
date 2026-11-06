"""Bounded item pages reduced to exact ordered manifest metadata, never a grant."""

from __future__ import annotations

import hashlib

from yorunge.adapters.http_transport import _remaining
from yorunge.adapters.platform_upload_port import ObservedUploadPort
from yorunge.adapters.upload_http import UploadHttpxTransport
from yorunge.application import platform_upload_codec as codec
from yorunge.application import upload_metadata_codec as metadata
from yorunge.application.http_transport import HttpRequest, HttpStatusFailure
from yorunge.domain.dataset_manifest import DatasetFile
from yorunge.domain.dataset_transfer import VerifiedFile
from yorunge.domain.errors import ErrorCode, YorungeError
from yorunge.domain.platform_upload_items import ProviderItems
from yorunge.domain.upload_checks import mandatory_http_failure
from yorunge.domain.upload_resume import InventoryFold, RemoteInventory, RemoteItem


async def _page(
    port: ObservedUploadPort,
    client: UploadHttpxTransport,
    dataset_id: str,
    cursor: str | None,
    deadline: float,
) -> bytes:
    request = HttpRequest(
        port._credential.target,
        "GET",
        f"datasets/{dataset_id}/items",
        query=metadata.item_query(cursor, port._credential.secret),
        credential=port._credential,
        read_only=True,
        service_id="evren-platform",
        upload_endpoint="items",
    )
    reserved = port._budget.reserve("read", response_bytes=request.max_bytes)
    failure: ErrorCode | None = None
    try:
        async with client.open_budgeted(request, reserved, deadline=deadline) as response:
            return b"".join([part async for part in response.chunks()])
    except HttpStatusFailure as error:
        _, failure = mandatory_http_failure(error.status_code)
    finally:
        if not reserved._closed:
            reserved.finish()
    assert failure is not None
    raise YorungeError(failure)


def _collect(
    page: ProviderItems,
    expected: dict[str, tuple[int, DatasetFile]],
    found: dict[str, VerifiedFile],
    ids: set[str],
) -> None:
    if page.total != len(expected):
        raise YorungeError("invalid_response")
    for item in page.items:
        match = expected.get(item.original_filename)
        if match is None or item.id in ids or item.original_filename in found:
            raise YorungeError("invalid_response")
        index, file = match
        if (item.file_size_bytes, item.sha256_hash) != (file.size, file.sha256):
            raise YorungeError("invalid_response")
        ids.add(item.id)
        found[file.path] = VerifiedFile(
            file_index=index,
            item_id=item.id,
            path_digest=hashlib.sha256(file.path.encode("utf-8")).hexdigest(),
            size_bytes=item.file_size_bytes,
            sha256=file.sha256,
        )


async def read_items(
    port: ObservedUploadPort, client: UploadHttpxTransport, dataset_id: str, *, deadline: float
) -> tuple[VerifiedFile, ...]:
    port._client(client)
    dataset_id = codec.segment(dataset_id, port._credential.secret)
    _remaining(deadline)
    deadline = min(deadline, port._budget.end)
    expected = {file.path: (index, file) for index, file in enumerate(port._manifest.files)}
    found: dict[str, VerifiedFile] = {}
    ids: set[str] = set()
    cursors: set[str] = set()
    cursor = None
    for _ in range(128):
        page = metadata.items(
            await _page(port, client, dataset_id, cursor, deadline),
            dataset_id,
            port._credential.secret,
        )
        _remaining(min(deadline, port._budget.end))
        _collect(page, expected, found, ids)
        if page.next_cursor is None:
            if len(found) != len(expected):
                raise YorungeError("invalid_response")
            result = tuple(found[file.path] for file in port._manifest.files)
            _remaining(min(deadline, port._budget.end))
            return result
        if page.next_cursor in cursors:
            raise YorungeError("invalid_response")
        cursor = page.next_cursor
        cursors.add(cursor)
    raise YorungeError("invalid_response")


async def read_inventory(
    port: ObservedUploadPort, client: UploadHttpxTransport, dataset_id: str, *, deadline: float
) -> RemoteInventory:
    """The dataset's item listing as observed, for the resume classifier.

    Unlike ``read_items`` this never compares against the manifest and does not raise when the
    listing is internally inconsistent: duplicate identities, a moving total, a repeated cursor,
    too many pages or items are recorded for ``classify`` to turn into blocking classes. Malformed
    pages, items of another dataset and transport failures still raise.
    """
    port._client(client)
    dataset_id = codec.segment(dataset_id, port._credential.secret)
    _remaining(deadline)
    deadline = min(deadline, port._budget.end)
    fold = InventoryFold()
    cursor: str | None = None
    while True:
        page = metadata.item_page(
            await _page(port, client, dataset_id, cursor, deadline),
            dataset_id,
            port._credential.secret,
        )
        _remaining(min(deadline, port._budget.end))
        cursor = fold.add(
            [
                RemoteItem(item.original_filename, item.file_size_bytes, item.sha256_hash, item.id)
                for item in page.items
            ],
            page.total,
            page.next_cursor,
        )
        if cursor is None:
            return fold.result()
