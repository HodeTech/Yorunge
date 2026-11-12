"""Listing pages: the strict reader keeps its rules, the lenient page leaves them to the reducer."""

import json
from uuid import uuid4

import pytest

from yorunge.application import upload_metadata_codec as metadata
from yorunge.domain.credentials import SecretValue
from yorunge.domain.errors import YorungeError

DATASET = str(uuid4())
SECRET = SecretValue("synthetic-listing-secret-123456")
HASH = "a" * 64


def row(name, identity=None, **changes):
    return {
        "id": identity or str(uuid4()),
        "dataset_id": DATASET,
        "original_filename": name,
        "file_size_bytes": 1,
        "sha256_hash": HASH,
        **changes,
    }


def body(rows, total, **changes):
    return json.dumps({"items": rows, "total": total, "next_cursor": None, **changes}).encode()


SAME_ID = str(uuid4())
INCONSISTENT = {
    "same id on two names": body([row("a", SAME_ID), row("b", SAME_ID)], 2),
    "same name twice": body([row("a"), row("a")], 2),
    "total below the count": body([row("a"), row("b")], 1),
}


@pytest.mark.parametrize("name", INCONSISTENT)
def test_the_strict_page_rejects_what_the_lenient_page_keeps_for_the_reducer(name):
    with pytest.raises(YorungeError) as raised:
        metadata.items(INCONSISTENT[name], DATASET, SECRET)
    assert raised.value.code == "invalid_response"
    assert len(metadata.item_page(INCONSISTENT[name], DATASET, SECRET).items) == 2


@pytest.mark.parametrize("reader", [metadata.items, metadata.item_page])
def test_unknown_provider_fields_are_projected_away_not_rejected(reader):
    rows = [{**row("a"), "created_at": "2026-01-01", "uploader": {"id": 1}}]
    page = reader(body(rows, 1, meta={"x": 1}), DATASET, SECRET)
    assert [item.original_filename for item in page.items] == ["a"]
    assert page.total == 1


@pytest.mark.parametrize("reader", [metadata.items, metadata.item_page])
@pytest.mark.parametrize(
    "raw",
    [
        body([row(f"f{n}") for n in range(129)], 129),
        body([], 0, next_cursor=""),
        body([], 0, next_cursor="c" * 1025),
        body([], 0, next_cursor="a\u0000b"),
        body([], 0, pad="p" * (1024 * 1024)),
    ],
    ids=["129 items", "empty cursor", "cursor of 1025", "control character cursor", "over 1 MiB"],
)
def test_page_bounds_are_enforced_by_both_readers(reader, raw):
    with pytest.raises(YorungeError) as raised:
        reader(raw, DATASET, SECRET)
    assert raised.value.code == "invalid_response"


@pytest.mark.parametrize("reader", [metadata.items, metadata.item_page])
@pytest.mark.parametrize(
    "change",
    [
        {"original_filename": "a:b"},
        {"original_filename": "a\\b"},
        {"original_filename": "x" * 300},
        {"sha256_hash": "A" * 64},
        {"file_size_bytes": 600_000_000},
        {"id": "not-a-uuid"},
        {"dataset_id": "not-a-uuid"},
    ],
    ids=["colon", "backslash", "long name", "uppercase hash", "over 500 MB", "id", "dataset id"],
)
def test_an_item_outside_the_local_grammar_makes_the_listing_an_error(reader, change):
    # Documented contract: a remote item that cannot be read under the local name, size, hash and
    # identifier grammar is a malformed provider response, not a plan-level extra item.
    body_value = body([row("a", **change)], 1)
    with pytest.raises(YorungeError) as raised:
        reader(body_value, DATASET, SECRET)
    assert raised.value.code == "invalid_response"


@pytest.mark.parametrize("reader", [metadata.items, metadata.item_page])
def test_items_of_another_dataset_are_an_error(reader):
    body_value = body([row("a", dataset_id=str(uuid4()))], 1)
    with pytest.raises(YorungeError) as raised:
        reader(body_value, DATASET, SECRET)
    assert raised.value.code == "invalid_response"


@pytest.mark.parametrize("reader", [metadata.items, metadata.item_page])
@pytest.mark.parametrize("place", ["filename", "unknown item field", "unknown top field", "cursor"])
def test_a_literal_secret_anywhere_in_a_listing_is_an_error_without_echo(reader, place):
    secret = SECRET.reveal()
    rows = [row("a")]
    top = {}
    if place == "filename":
        rows = [row(f"x{secret}.bin")]
    elif place == "unknown item field":
        rows = [{**row("a"), "note": secret}]
    elif place == "unknown top field":
        top = {"meta": secret}
    else:
        top = {"next_cursor": secret}
    body_value = body(rows, 1, **top)
    with pytest.raises(YorungeError) as raised:
        reader(body_value, DATASET, SECRET)
    assert raised.value.code == "invalid_response"
    assert secret not in repr(raised.value) + str(raised.value)
    assert raised.value.__cause__ is None
