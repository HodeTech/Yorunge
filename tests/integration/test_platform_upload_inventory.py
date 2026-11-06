"""Real TLS listing of a dataset's items, reduced without raising on untrustworthy content."""

import hashlib
import json
import time
from functools import partial
from uuid import uuid4

import pytest

from tests.fixtures.http_server import Reply, TlsServer
from tests.integration.test_platform_upload_data import (
    ITEMS,
    item_rows,
    page,
)
from tests.integration.test_platform_upload_data import certificates as certificates
from tests.integration.test_platform_upload_data import loopback_only as loopback_only
from tests.integration.test_platform_upload_port import setup
from tests.integration.test_upload_http_budget import session
from tests.integration.test_upload_journal import DATASET
from tests.integration.test_upload_journal import journal as journal
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_resume import (
    MAX_INVENTORY_ITEMS,
    MAX_INVENTORY_PAGES,
    ChainSummary,
    classify,
)

CURSOR = ITEMS + "&cursor=later"


def list_inventory(journal, certificates, routes, *, seconds=10):
    port, key, value = setup(journal, readonly=True)
    with TlsServer(certificates, routes) as server:
        owned, instances = session(server, key, value)
        with owned:
            result = owned.exchange(
                lambda client: port.inventory(client, DATASET, deadline=time.monotonic() + seconds)
            )
            assert not instances[0]._responses
            assert instances[0]._slots._value == 2
        assert all(r.method == "GET" for r in server.requests)
        paths = [r.path for r in server.requests]
    return result, paths, value


def classes_of(journal, inventory):
    chain = ChainSummary(("none", "none", "none"), False, False, ("op",))
    return classify(journal.manifest.files, chain, inventory)


def test_a_complete_two_page_listing_is_returned_in_listing_order_with_no_fault(
    journal, certificates
):
    rows = item_rows(journal)
    cursor_path = ITEMS + "&cursor=next%2Fpage%2B%C3%B6"
    inventory, paths, value = list_inventory(
        journal,
        certificates,
        {ITEMS: page([rows[2]], cursor="next/page+ö"), cursor_path: page([rows[1], rows[0]])},
    )
    assert paths == [ITEMS, cursor_path]
    assert [i.item_id for i in inventory.items] == [rows[2]["id"], rows[1]["id"], rows[0]["id"]]
    assert [(i.path, i.size, i.sha256) for i in inventory.items] == [
        (r["original_filename"], r["file_size_bytes"], r["sha256_hash"])
        for r in (rows[2], rows[1], rows[0])
    ]
    assert inventory.faults == frozenset()
    assert value.snapshot().read_requests == value.snapshot().read_attempts == 2
    assert value.snapshot().effect_attempts == value.snapshot().response_pending == 0
    assert classes_of(journal, inventory).classes == ("observed",) * 3


def other_item(rows, name):
    """An item whose name and content match no manifest file."""
    return {
        **rows[0],
        "id": str(uuid4()),
        "original_filename": name,
        "sha256_hash": hashlib.sha256(name.encode()).hexdigest(),
    }


def mutate(rows, index, **changes):
    rows[index].update(changes)
    return rows


# name -> (routes from fresh rows, expected faults, expected classes for a never-attempted journal)
def scenarios():
    def extra(rows):
        return other_item(rows, "extra.txt")

    def ghost(rows):
        return other_item(rows, "ghost.bin")

    return {
        "missing item is absence": (
            lambda rows: {ITEMS: page(rows[:2], total=2)},
            (),
            ("observed", "observed", "pending_clean"),
        ),
        "extra item is returned, not rejected": (
            lambda rows: {ITEMS: page([*rows, extra(rows)], total=4)},
            (),
            ("observed",) * 3,
        ),
        "total larger than listed": (
            lambda rows: {ITEMS: page(rows, total=4)},
            ("total_mismatch",),
            ("inventory_unreliable",) * 3,
        ),
        "total moves between pages": (
            lambda rows: {
                ITEMS: page(rows[:1], total=3, cursor="later"),
                CURSOR: page(rows[1:], total=4),
            },
            ("total_mismatch",),
            ("inventory_unreliable",) * 3,
        ),
        "cursor repeats": (
            lambda rows: {
                ITEMS: page([], total=0, cursor="later"),
                CURSOR: page([], total=0, cursor="later"),
            },
            ("cursor_loop",),
            ("inventory_unreliable",) * 3,
        ),
        "same id listed twice": (
            lambda rows: {ITEMS: page([rows[0], {**rows[1], "id": rows[0]["id"]}, rows[2]])},
            (),
            ("inventory_unreliable",) * 3,
        ),
        "same item on two pages": (
            lambda rows: {
                ITEMS: page([rows[0]], cursor="later"),
                CURSOR: page([rows[0], rows[1]]),
            },
            (),
            ("inventory_unreliable",) * 3,
        ),
        "null hash": (
            lambda rows: {ITEMS: page(mutate(rows, 0, sha256_hash=None))},
            (),
            ("inventory_unreliable",) * 3,
        ),
        "wrong hash": (
            lambda rows: {ITEMS: page(mutate(rows, 0, sha256_hash="0" * 64))},
            (),
            ("conflict", "observed", "observed"),
        ),
        "wrong size": (
            lambda rows: {
                ITEMS: page(mutate(rows, 1, file_size_bytes=rows[1]["file_size_bytes"] + 1))
            },
            (),
            ("observed", "conflict", "observed"),
        ),
        "same content under another name": (
            lambda rows: {
                ITEMS: page(
                    [*rows, {**rows[0], "id": str(uuid4()), "original_filename": "copy.txt"}],
                    total=4,
                )
            },
            (),
            ("conflict", "observed", "observed"),
        ),
        "an item named like no manifest file": (
            lambda rows: {ITEMS: page([*rows, ghost(rows)], total=4)},
            (),
            ("observed",) * 3,
        ),
    }


@pytest.mark.parametrize("name", list(scenarios()))
def test_untrustworthy_listings_become_faults_or_blocking_classes_never_errors(
    journal, certificates, name
):
    build, faults, classes = scenarios()[name]
    inventory, _, value = list_inventory(journal, certificates, build(item_rows(journal)))
    assert inventory.faults == frozenset(faults)
    result = classes_of(journal, inventory)
    assert result.classes == classes
    # Only a clean listing that is merely missing a file the journal never attempted may plan.
    assert result.plannable == (name == "missing item is absence")
    assert value.snapshot().effect_attempts == value.snapshot().response_pending == 0


def test_an_extra_item_blocks_through_the_extra_remote_blocker(journal, certificates):
    rows = item_rows(journal)
    extra = other_item(rows, "extra.txt")
    inventory, _, _ = list_inventory(journal, certificates, {ITEMS: page([*rows, extra], total=4)})
    result = classes_of(journal, inventory)
    assert result.classes == ("observed",) * 3
    assert result.blockers == ("extra_remote",)


def inventory_rows(count, start=0):
    return [
        {
            "id": str(uuid4()),
            "dataset_id": DATASET,
            "original_filename": f"remote-{start + n}.bin",
            "file_size_bytes": 1,
            "sha256_hash": hashlib.sha256(str(start + n).encode()).hexdigest(),
        }
        for n in range(count)
    ]


def test_the_item_cap_stops_listing_at_the_first_page_over_it(journal, certificates):
    routes = {ITEMS: page(inventory_rows(128), total=1025, cursor="p1")}
    for number in range(1, MAX_INVENTORY_ITEMS // 128):
        routes[ITEMS + f"&cursor=p{number}"] = page(
            inventory_rows(128, number * 128), total=1025, cursor=f"p{number + 1}"
        )
    last = MAX_INVENTORY_ITEMS // 128
    routes[ITEMS + f"&cursor=p{last}"] = page(
        inventory_rows(1, MAX_INVENTORY_ITEMS), total=1025, cursor="never-fetched"
    )
    inventory, paths, value = list_inventory(journal, certificates, routes, seconds=20)
    assert inventory.faults == frozenset({"too_large"})
    assert len(inventory.items) == MAX_INVENTORY_ITEMS + 1
    assert len(paths) == last + 1  # one request past the cap, then silence
    result = classes_of(journal, inventory)
    assert result.blockers == ("extra_remote", "inventory_unreliable", "inventory_too_large")
    assert result.classes == ("inventory_unreliable",) * 3
    assert value.snapshot().read_requests == last + 1


def test_endless_distinct_cursors_stop_at_the_page_limit(journal, certificates):
    routes = {ITEMS: page([], total=0, cursor="page-1")}
    for index in range(1, MAX_INVENTORY_PAGES):
        routes[ITEMS + f"&cursor=page-{index}"] = page([], total=0, cursor=f"page-{index + 1}")
    inventory, paths, _ = list_inventory(journal, certificates, routes, seconds=20)
    assert inventory.faults == frozenset({"page_limit"})
    assert len(paths) == MAX_INVENTORY_PAGES


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        json.dumps({"items": "x", "total": 0, "next_cursor": None}).encode(),
        json.dumps({"items": [], "total": -1, "next_cursor": None}).encode(),
        json.dumps({"items": [], "total": 0}).encode(),
    ],
)
def test_malformed_pages_are_errors_not_inventories(journal, certificates, body):
    port, key, value = setup(journal, readonly=True)
    with TlsServer(certificates, {ITEMS: Reply(body=body)}) as server:
        owned, _ = session(server, key, value)
        with owned:
            call = partial(
                owned.exchange,
                lambda client: port.inventory(client, DATASET, deadline=time.monotonic() + 5),
            )
            with pytest.raises(YorungeError) as raised:
                call()
            assert raised.value.code == "invalid_response"
    assert value.snapshot().effect_attempts == value.snapshot().response_pending == 0


def test_an_item_of_another_dataset_is_an_error_not_an_inventory(journal, certificates):
    rows = mutate(item_rows(journal), 0, dataset_id=str(uuid4()))
    port, key, value = setup(journal, readonly=True)
    with TlsServer(certificates, {ITEMS: page(rows)}) as server:
        owned, _ = session(server, key, value)
        with owned:
            call = partial(
                owned.exchange,
                lambda client: port.inventory(client, DATASET, deadline=time.monotonic() + 5),
            )
            with pytest.raises(YorungeError) as raised:
                call()
            assert raised.value.code == "invalid_response"


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "remote_access_denied"),
        (403, "remote_access_denied"),
        (404, "invalid_response"),
        (429, "remote_rate_limited"),
        (503, "remote_failed"),
    ],
)
def test_status_failures_keep_the_mandatory_read_error_without_effect(
    journal, certificates, status, code
):
    port, key, value = setup(journal, readonly=True)
    with TlsServer(certificates, {ITEMS: Reply(status=status, body=b"private-error")}) as server:
        owned, _ = session(server, key, value)
        with owned:
            call = partial(
                owned.exchange,
                lambda client: port.inventory(client, DATASET, deadline=time.monotonic() + 5),
            )
            with pytest.raises(YorungeError) as raised:
                call()
            assert raised.value.code == code
            assert raised.value.__cause__ is raised.value.__context__ is None
    assert value.snapshot().effect_attempts == value.snapshot().response_pending == 0
