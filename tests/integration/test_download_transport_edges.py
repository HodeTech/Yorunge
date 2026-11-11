"""The signed GET's edges that the first tests did not pin, found by mutating the transport.

A body larger than one read, the limit at its inclusive edge, the exact bounds of the header block,
the time each phase may take, the two shared slots, the gates of the entry, the release path and
the deadline's contract with the caller. Each case names what a one-line change to the transport
would otherwise leave unnoticed. They share the helpers of ``test_download_transport``.
"""

import asyncio
import dataclasses
import socket
import ssl
import threading
import time

import httpx
import pytest

from tests.fixtures.http_server import Reply, TlsServer
from tests.integration.test_download_transport import (
    CONTENT,
    ORIGIN,
    PATH,
    PREFIX,
    QUERY,
    TAG,
    failure,
    fetch,
    request,
    serve,
    target,
)
from tests.integration.test_storage_transport import (
    SECRET,
    FixtureNetwork,
    credential,
    session,
)
from tests.integration.test_storage_transport import (
    certificates as certificates,
)
from tests.integration.test_storage_transport import (
    loopback_only as loopback_only,
)
from yorunge.adapters import storage_transport
from yorunge.adapters.guarded_http import GuardedHttpTransport
from yorunge.adapters.guarded_network import GuardedBackend
from yorunge.adapters.storage_transport import TransferHttpxTransport, TransferSession
from yorunge.application.download_transport import DownloadRequest, DownloadTarget
from yorunge.domain.credentials import SecretValue
from yorunge.domain.download import MAX_DOWNLOAD_BYTES
from yorunge.domain.download_response import ResumeAsk
from yorunge.domain.errors import YorungeError

BIG = CONTENT * 64  # 131072 bytes: four reads of at most 32 KiB
OTHER = "/v1/files/evren-models/other.onnx"


# --- the body counters: a multi-chunk body is the real-world case ---------------------------------


def test_a_multi_chunk_body_arrives_whole_and_received_counts_every_chunk(certificates):
    key = credential()
    with serve(certificates, Reply(body=BIG, headers=(("ETag", TAG),))) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            response, action, body, received = fetch(owned, request(key), seconds=10)
    assert (response.content_length, action, received) == (len(BIG), "full", len(BIG))
    assert body == BIG


def test_the_running_counter_is_cumulative_across_chunks(certificates):
    # A chunked body promises nothing, so only the running sum can refuse it: each piece is 8 KiB,
    # the cap is 40,000 and the body 131,072.
    key = credential()
    pieces = [BIG[offset : offset + 8192] for offset in range(0, len(BIG), 8192)]
    framed = b"".join(b"2000\r\n" + piece + b"\r\n" for piece in pieces) + b"0\r\n\r\n"
    reply = Reply(body=framed, headers=(("Transfer-Encoding", "chunked"),))
    with serve(certificates, reply) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            code = failure(lambda: fetch(owned, request(key, max_bytes=40_000), seconds=10))
            assert fetch(owned, request(key), seconds=10)[2] == BIG  # and without a cap, whole
    assert code == "download_limit_exceeded"


@pytest.mark.parametrize("cap,code", [(2048, None), (2047, "download_limit_exceeded")])
def test_the_body_limit_is_inclusive(certificates, cap, code):
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            if code is None:
                assert fetch(owned, request(key, max_bytes=cap))[2] == CONTENT
            else:
                assert failure(lambda: fetch(owned, request(key, max_bytes=cap))) == code


def test_a_body_that_promises_more_than_the_callers_cap_is_refused_before_a_byte_is_read(
    certificates,
):
    key = credential()
    with serve(certificates, Reply(body=b"x" * 5000)) as api:
        owned, _, instances = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def run(transport):
            async with transport.open_download(
                request(key, max_bytes=1000), deadline=time.monotonic() + 3
            ):
                pytest.fail("the body was offered to a caller who allows 1000 bytes of it")

        with owned:
            assert failure(lambda: owned.download(run)) == "download_limit_exceeded"
            assert instances[0]._slots._value == 2
            assert instances[0]._responses == set()
        assert len(api.requests) == 1


@pytest.mark.parametrize("cap,entered", [(2048, True), (2047, False)])
def test_the_early_limit_check_is_exact_at_the_promised_length(certificates, cap, entered):
    # Promised 2048: a cap of 2047 refuses before the block is entered, 2048 lets it in. (The
    # running counter would give the same code, but only after reading had begun.)
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, _, instances = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        offered = []

        async def run(transport):
            async with transport.open_download(
                request(key, max_bytes=cap), deadline=time.monotonic() + 3
            ) as view:
                offered.append(view.response.content_length)
                async for _ in view.chunks():
                    pass

        with owned:
            if entered:
                owned.download(run)
            else:
                assert failure(lambda: owned.download(run)) == "download_limit_exceeded"
            assert instances[0]._slots._value == 2
            assert instances[0]._responses == set()
        assert offered == ([2048] if entered else [])


def test_a_ranged_request_judged_by_a_cap_below_the_object_is_the_callers_to_set(certificates):
    # `max_bytes` is checked against THIS answer's body, before the table: a caller that asks for
    # the rest of an object (or whose provider ignores the range and sends all of it) and lets the
    # cap be smaller than the object is refused for it. The engine passes the contract's limit.
    key = credential()
    ask = ResumeAsk(400, 2048, TAG)
    ignored = Reply(body=CONTENT, headers=(("ETag", TAG),))  # a 200 of 2048: the range was ignored
    with serve(certificates, ignored) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            assert failure(lambda: fetch(owned, request(key, ask=ask, max_bytes=1648))) == (
                "download_limit_exceeded"
            )
            response, action, body, _ = fetch(owned, request(key, ask=ask, max_bytes=2048))
        assert (action, len(body)) == ("restart", 2048)


def test_a_partial_answer_that_is_dropped_is_not_judged_by_the_cap_for_a_body_never_read(
    certificates,
):
    # A 206 that does not fit the request calls for `discard_and_retry` and its body is never
    # read: a cap lower than its length is no reason to refuse it, the retry has its own answer.
    key = credential()
    ask = ResumeAsk(400, 2048, TAG)
    unfit = Reply(
        status=206,
        body=CONTENT[400:],
        headers=(("Content-Range", "bytes 401-2047/2048"), ("ETag", TAG)),
    )
    with serve(certificates, unfit) as api:
        owned, _, instances = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            response, action, body, _ = fetch(
                owned, request(key, ask=ask, max_bytes=1000), read=False
            )
            assert instances[0]._slots._value == 2
            assert instances[0]._responses == set()
        assert (response.status, action, body) == (206, "discard_and_retry", b"")


def test_the_default_body_limit_is_the_contract_limit():
    key = credential()
    assert DownloadRequest(target(), key.secret).max_bytes == MAX_DOWNLOAD_BYTES
    assert target().prefix == PREFIX
    assert target().origin == ORIGIN


def test_a_body_is_taken_once_and_the_view_is_dead_after_its_context(certificates):
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def run(transport):
            async with transport.open_download(request(key), deadline=time.monotonic() + 3) as view:
                first = view.chunks()
                with pytest.raises(YorungeError) as twice:
                    view.chunks()
                body = b"".join([chunk async for chunk in first])
            with pytest.raises(YorungeError) as after:
                view.chunks()
            return twice.value.code, after.value.code, body

        with owned:
            assert owned.download(run) == ("invalid_request", "invalid_request", CONTENT)


def test_bytes_a_server_sends_after_the_promised_body_are_never_this_requests_data(certificates):
    # The HTTP layer stops at what the server promised; the surplus belongs to nobody and may cost
    # the NEXT request on that connection (a documented limit of the pooled client), never this.
    key = credential()
    with serve(certificates, Reply(body=CONTENT, trailing=b"EXTRA-BYTES-NOBODY-ASKED-FOR")) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            response, action, body, received = fetch(owned, request(key))
    assert (body, received, action) == (CONTENT, len(CONTENT), "full")


# --- the time each phase may take -----------------------------------------------------------------


def test_a_stalled_body_stops_at_the_deadline_not_seconds_after_it(certificates):
    key = credential()
    reply = Reply(body=b"y" * 4096, chunk_size=2048, chunk_delay=3.0)
    with serve(certificates, reply) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            started = time.monotonic()
            assert failure(lambda: fetch(owned, request(key), seconds=1.0)) == "transport_timeout"
            elapsed = time.monotonic() - started
    assert elapsed < 2.2  # the deadline plus session open/close and a load margin, not +2.5 s


def test_a_download_that_fits_the_deadline_is_not_cut_short(certificates):
    key = credential()
    reply = Reply(body=b"y" * 4096, chunk_size=1024, chunk_delay=0.3)
    with serve(certificates, reply) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            assert len(fetch(owned, request(key), seconds=1.4)[2]) == 4096


def test_a_slow_drip_body_is_stopped_by_the_total_deadline_not_by_a_read_timeout(certificates):
    # One byte every 0.1 s never trips a read phase; only the total window can end this 8 s body.
    key = credential()
    reply = Reply(body=b"d" * 80, chunk_size=1, chunk_delay=0.1)
    with serve(certificates, reply) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            started = time.monotonic()
            assert failure(lambda: fetch(owned, request(key), seconds=1.0)) == "transport_timeout"
            assert time.monotonic() - started < 2.2


def test_a_third_download_waits_one_second_for_a_slot_and_nothing_leaks(certificates):
    key = credential()
    slow = Reply(body=b"h" * 200_000, chunk_size=1000, chunk_delay=0.05)
    routes = {PATH + QUERY: slow, OTHER + QUERY: Reply(body=CONTENT)}
    with TlsServer(certificates, routes) as api:
        owned, _, instances = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def run(transport):
            async def hold():
                async with transport.open_download(
                    request(key), deadline=time.monotonic() + 30
                ) as view:
                    async for _ in view.chunks():
                        pass

            holders = [asyncio.create_task(hold()) for _ in range(2)]
            await asyncio.sleep(0.6)
            assert transport._slots._value == 0
            started = time.monotonic()
            with pytest.raises(YorungeError) as error:
                async with transport.open_download(
                    request(key, path=OTHER), deadline=time.monotonic() + 10
                ):
                    pytest.fail("a third download got a slot")
            waited = time.monotonic() - started
            for holder in holders:
                holder.cancel()
            await asyncio.gather(*holders, return_exceptions=True)
            return error.value.code, waited

        with owned:
            code, waited = owned.download(run)
            assert code == "transport_timeout"
            assert 0.8 < waited < 2.5  # one second
            for _ in range(5):
                assert fetch(owned, request(key, path=OTHER))[2] == CONTENT
            assert instances[0]._slots._value == 2
            assert instances[0]._responses == set()


def test_the_open_response_is_registered_while_the_body_is_read(certificates):
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, _, instances = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def run(transport):
            async with transport.open_download(request(key), deadline=time.monotonic() + 3) as view:
                seen = len(instances[0]._responses)
                async for _ in view.chunks():
                    pass
            return seen

        with owned:
            assert owned.download(run) == 1
            assert instances[0]._responses == set()


# --- the prepared wire ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "change", ["url", "host", "accept-encoding", "duplicate-accept-encoding", "extra-header"]
)
def test_a_prepared_wire_that_is_not_the_described_one_never_reaches_the_network(
    certificates, monkeypatch, change
):
    key = credential()
    original = httpx.Request

    def changed(*args, **kwargs):
        value = original(*args, **kwargs)
        if change == "url":
            value.url = httpx.URL("https://api.localhost/v1/files/evren-models/x?signature=y")
        elif change == "host":
            value.headers["Host"] = "other.example"
        elif change == "accept-encoding":
            value.headers["Accept-Encoding"] = "gzip"
        elif change == "duplicate-accept-encoding":
            value.headers = httpx.Headers(
                [*value.headers.multi_items(), ("Accept-Encoding", "identity")]
            )
        else:
            value.headers["Authorization"] = "Bearer x"
        return value

    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, network, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        monkeypatch.setattr(storage_transport.httpx, "Request", changed)
        with owned:
            assert failure(lambda: fetch(owned, request(key))) == "invalid_service_target"
        assert api.requests == []
        assert network.connections == []


def test_a_url_the_http_layer_cannot_take_is_a_closed_request_error_not_a_raw_one(
    certificates, monkeypatch
):
    key = credential()

    def refused(*args, **kwargs):
        raise httpx.InvalidURL("PRIVATE-URL-CANARY")

    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, network, instances = session(
            key, certificates, {"api.localhost": api}, origins=(ORIGIN,)
        )
        monkeypatch.setattr(storage_transport.httpx, "Request", refused)
        with owned:
            assert failure(lambda: fetch(owned, request(key))) == "invalid_request"
            assert instances[0]._slots._value == 2
        assert network.connections == []


# --- the header block's exact bounds --------------------------------------------------------------


def padded(count):
    return tuple((f"X-{index}", "v") for index in range(count))


def block_of(total):
    """Three 16 KiB fields and a fourth that makes the whole block's names and values ``total``."""
    fixed = 46 + 3 * (3 + 16384)  # the fixture adds Content-Length and Content-Type: 46 bytes
    return (*((f"X-{letter}", "a" * 16384) for letter in "ABC"), ("X-D", "a" * (total - fixed - 3)))


@pytest.mark.parametrize(
    "headers,code",
    [
        (padded(62), None),  # 64 fields with Content-Length and Content-Type
        (padded(63), "invalid_response"),  # 65
        ((("X-A", "a" * 16384),), None),
        ((("X-A", "a" * 16385),), "invalid_response"),
        ((("N" * 128, "v"),), None),
        ((("N" * 129, "v"),), "invalid_response"),
        (tuple((f"X-{i}", "a" * 16384) for i in range(3)), None),
        (tuple((f"X-{i}", "a" * 16384) for i in range(4)), "invalid_response"),
        (block_of(65536), None),
        (block_of(65537), "invalid_response"),
    ],
    ids=[
        "64 fields",
        "65 fields",
        "value 16384",
        "value 16385",
        "name 128",
        "name 129",
        "3x16 KiB",
        "4x16 KiB",
        "sum 65536",
        "sum 65537",
    ],
)
def test_the_header_block_bounds_are_exact(certificates, headers, code):
    key = credential()
    with serve(certificates, Reply(body=CONTENT, headers=headers)) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            if code is None:
                assert fetch(owned, request(key))[2] == CONTENT
            else:
                assert failure(lambda: fetch(owned, request(key))) == code
        assert len(api.requests) == 1


@pytest.mark.parametrize(
    "status,code",
    [
        (302, "remote_failed"),
        (401, "remote_access_denied"),
        (403, "remote_access_denied"),
        (404, "remote_failed"),
        (429, "remote_rate_limited"),
        (503, "remote_failed"),
    ],
)
@pytest.mark.parametrize("ask", [None, ResumeAsk(400, 2048, TAG)], ids=["plain", "ranged"])
def test_a_refusal_by_status_keeps_its_row_whatever_the_size_of_its_header_block(
    certificates, status, code, ask
):
    # The block bound guards what is read of an answer the table accepts; an answer the table
    # refuses by its status is that row's code (a 401 is `remote_access_denied`, exit 3) even
    # with 65 fields: it is not turned into `invalid_response` by the size of its envelope.
    key = credential()
    reply = Reply(status=status, body=b"", headers=padded(63))
    with serve(certificates, reply) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            assert failure(lambda: fetch(owned, request(key, ask=ask))) == code
        assert len(api.requests) == 1


# --- phases the deadline does not cover alone -----------------------------------------------------


def test_a_handshake_that_never_answers_ends_at_the_connect_budget_not_the_deadline(certificates):
    # The peer accepts the connection and says nothing: the 5 s connect/handshake budget ends the
    # attempt, not the caller's 30 s.
    key = credential()
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(4)
    accepted: list[socket.socket] = []
    threading.Thread(target=lambda: accepted.append(listener.accept()[0]), daemon=True).start()

    class Silent:
        port = listener.getsockname()[1]

        def client_context(self):
            return ssl.create_default_context(cafile=str(certificates[0]))

    owned, _, _ = session(key, certificates, {"api.localhost": Silent()}, origins=(ORIGIN,))
    started = time.monotonic()
    try:
        with owned:
            assert failure(lambda: fetch(owned, request(key), seconds=30)) == "transport_timeout"
        assert 4.0 < time.monotonic() - started < 8.5  # five seconds, not the thirty
    finally:
        listener.close()
        for connection in accepted:
            connection.close()


def test_a_caller_that_swallows_the_deadline_strike_and_still_finishes_the_body(certificates):
    # The strike is one-shot and lands in whichever await is pending. A caller that swallows it
    # (the contract says to re-raise) and reads the body to its end completes: disarming a window
    # that already fired must not crash the read.
    # The body is on the wire (and buffered) long before the strike and the caller is slow, so
    # the pending await at the strike is always the caller's own sleep, whatever the runner's speed.
    key = credential()
    reply = Reply(body=b"s" * 40_000, chunk_size=2000, chunk_delay=0.005)
    with serve(certificates, reply) as api:
        owned, _, instances = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        struck: list[int] = []

        async def run(transport):
            async with transport.open_download(
                request(key), deadline=time.monotonic() + 0.4
            ) as view:
                async for _ in view.chunks():
                    try:
                        await asyncio.sleep(0.1)
                    except asyncio.CancelledError:
                        struck.append(view.received)
                return view.complete

        with owned:
            assert owned.download(run) is True
        assert struck
        assert instances[0]._slots._value == 2
        assert not instances[0]._responses


# --- the gates of the entry and of the session ----------------------------------------------------


def test_open_download_refuses_what_is_not_a_download_request(certificates):
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, network, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def run(transport):
            async with transport.open_download(
                "https://api.localhost/x", deadline=time.monotonic() + 3
            ):
                pytest.fail("a string was accepted as a request")

        with owned:
            assert failure(lambda: owned.download(run)) == "invalid_request"
        assert network.connections == []


def test_download_refuses_a_transport_with_other_origins_than_the_session(certificates):
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        network = FixtureNetwork({"api.localhost": api})

        def factory():
            return TransferHttpxTransport(
                key,
                transport=GuardedHttpTransport(backend=network, verify=api.client_context()),
                storage_origins=(),
            )

        async def run(transport):
            pytest.fail("the consumer must not be created")

        with TransferSession(key, transport_factory=factory, storage_origins=(ORIGIN,)) as owned:
            assert failure(lambda: owned.download(run)) == "invalid_request"


def test_a_closed_transport_refuses_a_download(certificates):
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, network, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def run(transport):
            transport._closed = True
            try:
                async with transport.open_download(request(key), deadline=time.monotonic() + 3):
                    pytest.fail("a closed transport accepted a download")
            finally:
                transport._closed = False

        with owned:
            assert failure(lambda: owned.download(run)) == "invalid_request"
        assert network.connections == []


# --- the release path -----------------------------------------------------------------------------


def test_a_failed_close_after_a_clean_exit_is_a_transport_failure(certificates, monkeypatch):
    # The body is left unread: after a full read httpx has closed the response already.
    key = credential()
    real = httpx.Response.aclose

    async def failing(self):
        await real(self)
        raise httpx.ReadError("close failed")

    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, _, instances = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        monkeypatch.setattr(httpx.Response, "aclose", failing)
        with owned:
            assert failure(lambda: fetch(owned, request(key), read=False)) == "transport_failed"
            assert instances[0]._slots._value == 2
            assert instances[0]._responses == set()


def test_a_private_cause_never_survives_on_a_refused_connection():
    key = credential()

    async def resolver(host, port, timeout):
        return ("not-an-ip-ZZZ-private-text",)

    guarded = GuardedBackend(resolver=resolver)

    def factory():
        return TransferHttpxTransport(
            key, transport=GuardedHttpTransport(backend=guarded), storage_origins=(ORIGIN,)
        )

    async def run(transport):
        async with transport.open_download(request(key), deadline=time.monotonic() + 2):
            pytest.fail("reached HTTP")

    with TransferSession(key, transport_factory=factory, storage_origins=(ORIGIN,)) as owned:
        with pytest.raises(YorungeError) as error:
            owned.download(run)
    assert error.value.code == "invalid_service_target"
    assert error.value.__context__ is None
    assert error.value.__cause__ is None


def test_a_download_left_by_cancellation_closes_its_own_connection_while_the_session_is_open(
    certificates,
):
    # The consumer is cancelled in its OWN code, so only the release path can close the
    # connection, and the wait happens while the session is open (a closed session closes it too).
    key = credential()
    slow = Reply(body=b"z" * 400_000, chunk_size=1024, chunk_delay=0.02)
    with serve(certificates, slow) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def interrupted(transport):
            async def consumer():
                async with transport.open_download(request(key), deadline=time.monotonic() + 30):
                    await asyncio.sleep(30)  # the consumer's own code; the body is never touched

            task = asyncio.create_task(consumer())
            await asyncio.sleep(0.5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert transport._slots._value == 2
            assert not transport._responses
            return await asyncio.to_thread(api.disconnected.wait, 3)

        with owned:
            assert owned.download(interrupted) is True


# --- the deadline and the caller's own errors -----------------------------------------------------


def test_a_caller_that_is_busy_after_a_whole_body_is_not_timed_out(certificates):
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def run(transport):
            async with transport.open_download(
                request(key), deadline=time.monotonic() + 0.8
            ) as view:
                [chunk async for chunk in view.chunks()]
                end = time.monotonic() + 1.0
                while time.monotonic() < end:  # the completion checkpoint: CPU, no await
                    pass
                return view.complete

        with owned:
            assert owned.download(run) is True


def test_a_timeout_of_the_callers_own_code_is_the_callers_and_not_a_transport_timeout(certificates):
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, _, instances = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        local = TimeoutError("local disk timeout")

        async def run(transport):
            async with transport.open_download(request(key), deadline=time.monotonic() + 5):
                raise local

        with owned:
            with pytest.raises(TimeoutError) as error:
                owned.download(run)
            assert error.value is local  # the same object, not relabelled
            assert instances[0]._slots._value == 2
            assert instances[0]._responses == set()


def test_the_callers_other_errors_come_back_as_they_were_raised(certificates):
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        raised = [OSError(28, "No space left on device"), ValueError("a bug")]

        with owned:
            for error in raised:

                async def run(transport, error=error):
                    async with transport.open_download(request(key), deadline=time.monotonic() + 5):
                        raise error

                with pytest.raises(type(error)) as caught:
                    owned.download(run)
                assert caught.value is error


# --- the request type -----------------------------------------------------------------------------


def test_a_download_request_is_closed_and_frozen():
    key = credential()
    assert failure(lambda: DownloadRequest("https://api.localhost/x", key.secret)) == (
        "invalid_request"
    )
    wanted = DownloadRequest(target(), key.secret)
    with pytest.raises(dataclasses.FrozenInstanceError):
        wanted.ask = ResumeAsk(400, 2048, TAG)  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        wanted.max_bytes = 1  # type: ignore[misc]


def test_a_resume_tag_that_is_the_selected_key_is_refused():
    key = credential()
    ask = ResumeAsk(400, 2048, '"' + SECRET + '"')
    assert failure(lambda: DownloadRequest(target(), key.secret, ask)) == "invalid_request"


def test_a_key_split_across_query_separators_is_still_refused():
    spread = SecretValue("abc=def&ghi-123456")
    wanted = DownloadTarget(ORIGIN + PATH + "?x=abc=def&ghi-123456", origin=ORIGIN, prefix=PREFIX)
    assert failure(lambda: DownloadRequest(wanted, spread)) == "invalid_service_target"


def test_repeated_identity_content_encoding_fields_are_accepted_as_separate_fields(certificates):
    key = credential()
    reply = Reply(
        body=CONTENT,
        headers=(("Content-Encoding", "identity"), ("Content-Encoding", "identity")),
    )
    with serve(certificates, reply) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            assert fetch(owned, request(key))[2] == CONTENT


# --- the head phase, the release, thread ownership, the slot wait, the short keys ----------------


@pytest.mark.parametrize(
    "raised",
    [
        ssl.SSLError(1, "[SSL] record layer failure PRIVATE-URL-CANARY"),
        ConnectionResetError(54, "Connection reset by peer"),
        OSError(5, "Input/output error"),
    ],
    ids=["record layer", "reset", "oserror"],
)
def test_an_oserror_the_stack_leaves_unmapped_in_the_head_phase_is_transport_failed(
    certificates, monkeypatch, raised
):
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, _, instances = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def raising(self, *args, **kwargs):
            raise raised

        monkeypatch.setattr(httpx.AsyncClient, "send", raising)
        with owned:
            assert failure(lambda: fetch(owned, request(key))) == "transport_failed"
            assert instances[0]._slots._value == 2
            assert instances[0]._responses == set()


def test_a_cancel_inside_the_release_of_an_unfinished_body_leaves_no_pool_connection(certificates):
    key = credential()
    slow = Reply(body=b"z" * 200_000, chunk_size=1024, chunk_delay=0.02)
    with serve(certificates, slow) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def interrupted(transport):
            started = asyncio.Event()

            async def consumer():
                async with transport.open_download(
                    request(key), deadline=time.monotonic() + 30
                ) as view:
                    await anext(view.chunks())
                    started.set()  # leave the block with the body unread

            task = asyncio.create_task(consumer())
            await started.wait()
            task.cancel()  # one cancel, landing in the release
            await asyncio.gather(task, return_exceptions=True)
            pool = transport._client._transport._pool
            for _ in range(60):  # the connection may take a few loop turns to close
                if not pool.connections:
                    break
                await asyncio.sleep(0.05)
            return transport._slots._value, [c.info() for c in pool.connections]

        with owned:
            slots, connections = owned.download(interrupted)
        assert slots == 2
        assert connections == []  # an ACTIVE connection stays in the pool otherwise


def test_open_download_from_another_thread_is_refused_before_anything_happens(certificates):
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, network, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def grab(transport):
            return transport

        with owned:
            transport = owned.download(grab)
            outcome = []

            def elsewhere():
                async def go():
                    try:
                        async with transport.open_download(
                            request(key), deadline=time.monotonic() + 3
                        ):
                            outcome.append("opened")
                    except YorungeError as error:
                        outcome.append(error.code)

                asyncio.run(go())

            worker = threading.Thread(target=elsewhere)
            worker.start()
            worker.join(10)
        assert outcome == ["invalid_request"]
        assert api.requests == []
        assert network.connections == []


def test_a_caller_that_stays_busy_past_the_deadline_with_the_body_unread_is_timed_out(certificates):
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, _, instances = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def run(transport):
            async with transport.open_download(request(key), deadline=time.monotonic() + 0.4):
                end = time.monotonic() + 0.8
                while time.monotonic() < end:  # no await: only the check after the block can see it
                    pass

        with owned:
            assert failure(lambda: owned.download(run)) == "transport_timeout"
            assert instances[0]._slots._value == 2
            assert instances[0]._responses == set()


def test_a_cap_of_one_byte_is_a_valid_request():
    key = credential()
    assert DownloadRequest(target(), key.secret, None, max_bytes=1).max_bytes == 1


def test_a_request_the_gates_refuse_is_refused_at_once_even_when_both_slots_are_busy(certificates):
    key = credential()
    slow = Reply(body=b"h" * 200_000, chunk_size=1000, chunk_delay=0.05)
    with TlsServer(certificates, {PATH + QUERY: slow}) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def run(transport):
            async def hold():
                async with transport.open_download(
                    request(key), deadline=time.monotonic() + 30
                ) as view:
                    async for _ in view.chunks():
                        pass

            holders = [asyncio.create_task(hold()) for _ in range(2)]
            await asyncio.sleep(0.5)
            started = time.monotonic()
            stranger = DownloadRequest(
                DownloadTarget(
                    "https://storage.localhost" + PATH + QUERY,
                    origin="https://storage.localhost",
                    prefix=PREFIX,
                ),
                key.secret,
            )
            try:
                async with transport.open_download(stranger, deadline=time.monotonic() + 10):
                    outcome = "opened"
            except YorungeError as error:
                outcome = error.code
            waited = time.monotonic() - started
            for holder in holders:
                holder.cancel()
            await asyncio.gather(*holders, return_exceptions=True)
            return outcome, waited

        with owned:
            outcome, waited = owned.download(run)
        assert outcome == "invalid_service_target"
        assert waited < 0.5


def test_the_wait_for_a_slot_is_exactly_one_second(certificates, monkeypatch):
    key = credential()
    delays = []
    real = asyncio.timeout

    def spy(delay):
        delays.append(delay)
        return real(delay)

    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        monkeypatch.setattr(asyncio, "timeout", spy)
        with owned:
            fetch(owned, request(key), seconds=30)
    assert 1.0 in delays  # min(1.0, remaining) at a 30 s deadline: the pool wait, not the window


def test_a_body_is_never_handed_over_in_pieces_larger_than_a_tls_record(certificates):
    key = credential()
    with serve(certificates, Reply(body=BIG)) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def sizes(transport):
            async with transport.open_download(
                request(key), deadline=time.monotonic() + 10
            ) as view:
                return [len(chunk) async for chunk in view.chunks()]

        with owned:
            pieces = owned.download(sizes)
    assert sum(pieces) == len(BIG)
    assert max(pieces) <= 16_384  # the reference promises "16 KiB"


@pytest.mark.parametrize(
    "tail",
    [
        "/tok1234/x?s=1",  # a whole path segment
        "/x?tok1234=1",  # a query key
        "/x?a=tok1234&b=2",  # a query value followed by another pair
        "/x?a=1&b=tok1234",  # the last query value
        "/x?a=%74ok1234&b=2",  # percent-encoded
    ],
)
def test_a_short_key_is_refused_where_only_equality_can_find_it(tail):
    # Below eight bytes a key is matched by equality with a whole part, so how the address is cut
    # into parts is the whole check.
    wanted = DownloadTarget(ORIGIN + PREFIX + tail.lstrip("/"), origin=ORIGIN, prefix=PREFIX)
    assert (
        failure(lambda: DownloadRequest(wanted, SecretValue("tok1234"))) == "invalid_service_target"
    )


@pytest.mark.parametrize(
    "url,origin,prefix",
    [
        (b"https://api.localhost/v1/files/evren-models/w", ORIGIN, PREFIX),
        (ORIGIN + PATH, None, PREFIX),
        (ORIGIN + PATH, ORIGIN, b"/v1/files/evren-models/"),
        (None, ORIGIN, PREFIX),
    ],
    ids=["bytes url", "no origin", "bytes prefix", "no url"],
)
def test_an_address_of_the_wrong_type_is_not_a_target(url, origin, prefix):
    assert failure(lambda: DownloadTarget(url, origin=origin, prefix=prefix)) == (
        "invalid_service_target"
    )


def test_a_body_that_failed_does_not_read_as_ended_to_a_caller_that_reads_on(certificates):
    key = credential()
    framed = b"400\r\n" + CONTENT[:1024] + b"\r\n"  # a chunked body cut before its terminator
    reply = Reply(body=framed, headers=(("Transfer-Encoding", "chunked"),), truncate_at=len(framed))
    with serve(certificates, reply) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def run(transport):
            async with transport.open_download(request(key), deadline=time.monotonic() + 3) as view:
                chunks, seen = view.chunks(), []
                for _ in range(5):
                    try:
                        seen.append(len(await anext(chunks)))
                    except YorungeError as error:
                        seen.append(error.code)
                    except StopAsyncIteration:
                        seen.append("END")
                return seen, view.complete

        with owned:
            seen, complete = owned.download(run)
    assert seen[0] == 1024
    assert set(seen[1:]) == {"download_incomplete"}
    assert complete is False  # a cut chunked body must never be published as a whole one
