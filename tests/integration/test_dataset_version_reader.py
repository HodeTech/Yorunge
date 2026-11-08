"""The version reader over real loopback TLS: what it asks, what it refuses, what it never exposes.

A version list is one GET, a version is two (its detail, then its split counts); everything is a
read-only GET with the selected key in one header. The 404 of the detail route has a meaning of its
own, the 404 of the split route is a failed read, and a provider that moves between the two reads
gives an answer that is not an answer.
"""

import json
import socket
import time
from datetime import UTC, datetime

import pytest

from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from yorunge.adapters.capability_cache import SystemClock
from yorunge.adapters.dataset_version_reader import VersionReader
from yorunge.adapters.http_session import HttpSession
from yorunge.adapters.http_transport import HttpxTransport
from yorunge.domain.credentials import (
    EnvReference,
    ResolvedCredential,
    SecretValue,
    normalize_target,
)
from yorunge.domain.dataset_version import SplitCounts
from yorunge.domain.errors import YorungeError

CONNECT, CONNECT_EX, GETADDRINFO = (
    socket.socket.connect,
    socket.socket.connect_ex,
    socket.getaddrinfo,
)
SECRET = "synthetic-platform-secret-471920"
DATASET = "11111111-1111-4111-8111-111111111111"
VERSION = "22222222-2222-4222-8222-222222222222"
CANARY = "PRIVATE-DESCRIPTION-CANARY"
NOT_FOUND = "dataset_version_not_found"
BASE = f"/api/v1/datasets/{DATASET}/versions"
LABELS = [
    {"id": 11, "name": "kedi", "sort_order": 1, "annotation_count": 7, "color": "#ff0000"},
    {"id": 2, "name": "köpek", "sort_order": 0, "annotation_count": 4, "shortcut": "k"},
]


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(tmp_path_factory.mktemp("version-tls"))


@pytest.fixture(autouse=True)
def actual_loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


def row(**changes):
    return {
        "id": VERSION,
        "version_tag": "v1",
        "is_frozen": True,
        "is_partial": False,
        "is_export_ready": False,
        "item_count": 10,
        "split_config": {"train": 6, "val": 2, "test": 1, "unassigned": 1},
        "annotated_item_count": 9,
        "total_annotation_count": 21,
        "created_at": "2026-11-04T10:11:12.123456Z",
        "description": CANARY,
        "created_by": "someone@example.test",
        "export_zip_url": "https://files.example.test/private.zip?signature=PRIVATE",
        **changes,
    }


def body(value, status=200, **options):
    return Reply(status=status, body=json.dumps(value).encode(), **options)


def listing(rows=None, **meta):
    rows = [row()] if rows is None else rows
    return {
        "success": True,
        "data": rows,
        "meta": {"page": 1, "page_size": 20, "total": len(rows), "has_next": False, **meta},
    }


def detail(**changes):
    return {
        "success": True,
        "data": {**row(), "dataset_id": DATASET, "class_labels_snapshot": LABELS, **changes},
    }


def splits(**counts):
    return {"success": True, "data": {"train": 6, "val": 2, "test": 1, "unassigned": 1, **counts}}


def routes(**overrides):
    table = {
        BASE + "?page=1": body(listing()),
        BASE + "/v1": body(detail()),
        BASE + "/v1/splits": body(splits()),
    }
    table.update(overrides)
    return table


def credential(secret=SECRET, service="evren-platform"):
    return ResolvedCredential(
        reference=EnvReference(service_id=service, kind="env", name="EVREN_PLATFORM_API_KEY"),
        target=normalize_target("https://localhost/api/v1"),
        secret=SecretValue(secret),
    )


def reader(server, **options):
    session = HttpSession(transport_factory=lambda: HttpxTransport(transport=server.transport()))
    return VersionReader(options.get("credential", credential()), SystemClock(), session=session)


def failure(action):
    with pytest.raises(YorungeError) as error:
        action()
    return error.value


def soon(seconds=5):
    return time.monotonic() + seconds


# --- what is asked --------------------------------------------------------------------------------


def test_a_page_is_one_get_with_the_key_in_one_header_and_nothing_else_asked(certificates):
    with TlsServer(certificates, routes()) as server:
        with reader(server) as versions:
            shown = versions.versions(DATASET, 1, deadline=soon())
    (request,) = server.requests
    assert (request.method, request.path) == ("GET", BASE + "?page=1")
    assert request.header("X-API-Key") == SECRET
    assert request.header("Authorization") is None and request.header("Cookie") is None
    assert [item.version_tag for item in shown.items] == ["v1"] and shown.total == 1
    dumped = repr(shown) + repr([item.model_dump() for item in shown.items])
    for private in (CANARY, "someone@example.test", "files.example.test"):
        assert private not in dumped


def test_a_version_is_its_detail_then_its_splits_and_two_gets_at_most(certificates):
    with TlsServer(certificates, routes()) as server:
        with reader(server) as versions:
            seen = versions.version(DATASET, "v1", deadline=soon(), absent=NOT_FOUND)
    assert [(r.method, r.path) for r in server.requests] == [
        ("GET", BASE + "/v1"),
        ("GET", BASE + "/v1/splits"),
    ]
    assert seen.version_id == VERSION and seen.split_counts == SplitCounts(
        train=6, val=2, test=1, unassigned=1
    )
    assert seen.class_count == 2 and len(seen.class_labels_sha256) == 64
    assert seen.is_frozen and not seen.is_partial and seen.observed_at.endswith("Z")
    assert "kedi" not in repr(seen) and "köpek" not in repr(seen) and CANARY not in repr(seen)


def test_the_observation_is_stamped_after_both_reads(certificates):
    with TlsServer(certificates, routes()) as server:
        with reader(server) as versions:
            before = time.time()
            seen = versions.version(DATASET, "v1", deadline=soon(), absent=NOT_FOUND)
    stamp = time.mktime(time.strptime(seen.observed_at[:19], "%Y-%m-%dT%H:%M:%S"))
    assert abs(stamp - time.time()) < 86_400 and before > 0  # a real, recent time


# --- the arguments are checked before any request -------------------------------------------------


@pytest.mark.parametrize(
    "call",
    [
        lambda v: v.versions("not-a-uuid", 1, deadline=soon()),
        lambda v: v.versions("ABCDEF01-1111-4111-8111-111111111111", 1, deadline=soon()),
        lambda v: v.versions(DATASET, 0, deadline=soon()),
        lambda v: v.versions(DATASET, 10_001, deadline=soon()),
        lambda v: v.versions(DATASET, True, deadline=soon()),
        lambda v: v.versions(DATASET, "1", deadline=soon()),
        lambda v: v.versions(None, 1, deadline=soon()),
        lambda v: v.version(DATASET, "..", deadline=soon(), absent=NOT_FOUND),
        lambda v: v.version(DATASET, "a/b", deadline=soon(), absent=NOT_FOUND),
        lambda v: v.version(DATASET, "", deadline=soon(), absent=NOT_FOUND),
        lambda v: v.version(DATASET, "x" * 129, deadline=soon(), absent=NOT_FOUND),
        lambda v: v.version(DATASET, "é", deadline=soon(), absent=NOT_FOUND),
        lambda v: v.version("not-a-uuid", "v1", deadline=soon(), absent=NOT_FOUND),
    ],
)
def test_a_bad_argument_is_refused_before_anything_is_asked(certificates, call):
    with TlsServer(certificates, routes()) as server:
        with reader(server) as versions:
            assert failure(lambda: call(versions)).code == "invalid_request"
    assert server.requests == []


def test_another_services_credential_is_not_used(certificates):
    with TlsServer(certificates, routes()) as server:
        error = failure(lambda: reader(server, credential=credential(service="evren-llm")))
    assert error.code == "invalid_service_target" and server.requests == []


# --- 404, and the other things a provider says ----------------------------------------------------


def test_the_missing_detail_is_not_found_or_missing_as_the_caller_says_and_costs_one_get(
    certificates,
):
    table = routes(**{BASE + "/v1": body({"success": False}, status=404)})
    with TlsServer(certificates, table) as server:
        with reader(server) as versions:
            assert failure(
                lambda: versions.version(DATASET, "v1", deadline=soon(), absent=NOT_FOUND)
            ).code == ("dataset_version_not_found")
            absent = failure(
                lambda: versions.version(
                    DATASET, "v1", deadline=soon(), absent="dataset_version_missing"
                )
            )
    assert absent.code == "dataset_version_missing" and absent.exit_code == 7
    assert [r.path for r in server.requests] == [BASE + "/v1"] * 2  # never the splits


def test_a_missing_split_route_after_a_found_version_is_a_failed_read_never_missing(certificates):
    table = routes(**{BASE + "/v1/splits": body({"success": False}, status=404)})
    with TlsServer(certificates, table) as server:
        with reader(server) as versions:
            error = failure(
                lambda: versions.version(
                    DATASET, "v1", deadline=soon(), absent="dataset_version_missing"
                )
            )
    assert error.code == "remote_failed"
    assert len(server.requests) == 2


def test_a_missing_list_page_is_a_failed_read(certificates):
    table = routes(**{BASE + "?page=1": body({"success": False}, status=404)})
    with TlsServer(certificates, table) as server:
        with reader(server) as versions:
            assert failure(lambda: versions.versions(DATASET, 1, deadline=soon())).code == (
                "remote_failed"
            )


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "remote_access_denied"),
        (403, "remote_access_denied"),
        (429, "remote_rate_limited"),
        (400, "remote_failed"),
        (500, "remote_failed"),
    ],
)
def test_a_provider_that_refuses_is_the_existing_closed_code(certificates, status, code):
    table = routes(**{BASE + "/v1": body({"error": CANARY}, status=status)})
    with TlsServer(certificates, table) as server:
        with reader(server) as versions:
            error = failure(
                lambda: versions.version(DATASET, "v1", deadline=soon(), absent=NOT_FOUND)
            )
    assert error.code == code
    assert CANARY not in str(error.envelope())


def test_a_read_that_failed_once_is_asked_again_once_and_not_more(certificates):
    calls = []

    def flaky(record, count):
        calls.append(count)
        return body({"error": "busy"}, status=503) if count == 1 else body(detail())

    with TlsServer(certificates, routes(**{BASE + "/v1": flaky})) as server:
        with reader(server) as versions:
            seen = versions.version(DATASET, "v1", deadline=soon(), absent=NOT_FOUND)
    assert seen.version_tag == "v1" and len(calls) == 2
    with TlsServer(certificates, routes(**{BASE + "/v1": body({}, status=503)})) as server:
        with reader(server) as versions:
            assert failure(
                lambda: versions.version(DATASET, "v1", deadline=soon(), absent=NOT_FOUND)
            ).code == ("remote_failed")
    assert [r.path for r in server.requests].count(BASE + "/v1") == 2  # the read-only policy


def test_a_provider_that_moved_between_the_two_reads_gives_no_answer(certificates):
    table = routes(**{BASE + "/v1/splits": body(splits(train=7))})
    with TlsServer(certificates, table) as server:
        with reader(server) as versions:
            assert failure(
                lambda: versions.version(DATASET, "v1", deadline=soon(), absent=NOT_FOUND)
            ).code == ("invalid_response")


def test_the_answer_of_another_version_than_the_one_asked_for_is_refused(certificates):
    table = routes(**{BASE + "/v1": body(detail(version_tag="v2"))})
    with TlsServer(certificates, table) as server:
        with reader(server) as versions:
            assert failure(
                lambda: versions.version(DATASET, "v1", deadline=soon(), absent=NOT_FOUND)
            ).code == ("invalid_response")


def test_a_page_other_than_the_one_asked_for_is_refused(certificates):
    table = routes(**{BASE + "?page=2": body(listing())})  # says page 1 to a request for page 2
    with TlsServer(certificates, table) as server:
        with reader(server) as versions:
            assert failure(lambda: versions.versions(DATASET, 2, deadline=soon())).code == (
                "invalid_response"
            )


def test_the_selected_key_in_an_answer_is_refused_and_never_echoed(certificates):
    table = routes(**{BASE + "/v1": body(detail(description=f"see {SECRET}"))})
    with TlsServer(certificates, table) as server:
        with reader(server) as versions:
            error = failure(
                lambda: versions.version(DATASET, "v1", deadline=soon(), absent=NOT_FOUND)
            )
    assert error.code == "invalid_response"
    assert SECRET not in str(error.envelope()) and SECRET not in repr(error)


def padded_detail(total):
    """A valid detail document of exactly ``total`` bytes (its description is padding)."""
    document = detail()
    document["data"]["description"] = ""
    size = len(json.dumps(document).encode())
    document["data"]["description"] = "x" * (total - size)
    encoded = json.dumps(document).encode()
    assert len(encoded) == total
    return Reply(body=encoded)


@pytest.mark.parametrize("extra,accepted", [(0, True), (1, False)])
def test_an_answer_of_exactly_a_mebibyte_is_read_and_one_byte_more_is_refused(
    certificates, extra, accepted
):
    answer = padded_detail(1024 * 1024 + extra)
    with TlsServer(certificates, routes(**{BASE + "/v1": answer})) as server:
        with reader(server) as versions:
            if accepted:
                seen = versions.version(DATASET, "v1", deadline=soon(10), absent=NOT_FOUND)
                assert seen.version_tag == "v1"
            else:
                error = failure(
                    lambda: versions.version(DATASET, "v1", deadline=soon(10), absent=NOT_FOUND)
                )
                assert error.code == "invalid_response"


def test_an_answer_that_is_valid_json_of_the_wrong_shape_is_refused_whatever_its_size(certificates):
    big = Reply(body=b'{"success":true,"data":"' + b"x" * (1024 * 1024) + b'"}')
    with TlsServer(certificates, routes(**{BASE + "/v1": big})) as server:
        with reader(server) as versions:
            error = failure(
                lambda: versions.version(DATASET, "v1", deadline=soon(10), absent=NOT_FOUND)
            )
    assert error.code == "invalid_response"


def test_a_stalled_provider_ends_at_the_deadline(certificates):
    slow = Reply(body=json.dumps(detail()).encode(), header_delay=3.0)
    with TlsServer(certificates, routes(**{BASE + "/v1": slow})) as server:
        with reader(server) as versions:
            started = time.monotonic()
            error = failure(
                lambda: versions.version(DATASET, "v1", deadline=soon(1), absent=NOT_FOUND)
            )
            assert error.code == "transport_timeout" and time.monotonic() - started < 3


def test_an_expired_deadline_asks_nothing(certificates):
    with TlsServer(certificates, routes()) as server:
        with reader(server) as versions:
            assert failure(
                lambda: versions.version(
                    DATASET, "v1", deadline=time.monotonic() - 1, absent=NOT_FOUND
                )
            )
    assert server.requests == []


# --- the 404 code is the caller's, has no default and is checked before anything is asked ---------


def test_the_code_a_missing_version_means_has_no_default(certificates):
    with TlsServer(certificates, routes()) as server:
        with reader(server) as versions:
            with pytest.raises(TypeError):
                versions.version(DATASET, "v1", deadline=soon())  # type: ignore[call-arg]
    assert server.requests == []


@pytest.mark.parametrize(
    "absent", ["bogus", "", None, 5, "invalid_response", "remote_failed", "DATASET_VERSION_MISSING"]
)
def test_a_code_that_is_not_one_of_the_two_is_refused_before_any_request(certificates, absent):
    with TlsServer(certificates, routes()) as server:
        with reader(server) as versions:
            error = failure(
                lambda: versions.version(DATASET, "v1", deadline=soon(), absent=absent)  # type: ignore[arg-type]
            )
    assert error.code == "invalid_request" and server.requests == []


# --- the observation is stamped after the reads it describes --------------------------------------


class RequestCountClock:
    """now() is second N, N being how many requests the server has received so far."""

    def __init__(self, server):
        self.server = server

    def now(self):
        return datetime(2026, 11, 8, 12, 0, len(self.server.requests), tzinfo=UTC)

    def monotonic(self):
        return time.monotonic()


def counting_reader(server):
    session = HttpSession(transport_factory=lambda: HttpxTransport(transport=server.transport()))
    return VersionReader(credential(), RequestCountClock(server), session=session)


def test_a_version_is_stamped_after_both_reads(certificates):
    with TlsServer(certificates, routes()) as server, counting_reader(server) as versions:
        seen = versions.version(DATASET, "v1", deadline=soon(), absent=NOT_FOUND)
    assert seen.observed_at == "2026-11-08T12:00:02.000000Z"  # both requests had been received


def test_a_page_is_stamped_after_its_read(certificates):
    with TlsServer(certificates, routes()) as server, counting_reader(server) as versions:
        shown = versions.versions(DATASET, 1, deadline=soon())
    assert shown.observed_at == "2026-11-08T12:00:01.000000Z"
    assert shown.items[0].observed_at == shown.observed_at


def test_the_last_page_that_may_be_asked_for_is_asked_and_the_next_is_not(certificates):
    last = listing([], page=10_000, total=0)
    with TlsServer(certificates, routes(**{BASE + "?page=10000": body(last)})) as server:
        with reader(server) as versions:
            shown = versions.versions(DATASET, 10_000, deadline=soon())
            assert shown.items == () and shown.page == 10_000
            for page in (0, 10_001, -1):
                assert failure(
                    lambda page=page: versions.versions(DATASET, page, deadline=soon())
                ).code == ("invalid_request")
    assert [r.path for r in server.requests] == [BASE + "?page=10000"]  # the refused cost nothing
