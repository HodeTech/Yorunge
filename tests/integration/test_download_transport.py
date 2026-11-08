"""The signed GET over real loopback TLS: no credential, a closed request, one physical attempt.

The answer is typed by the download contract (P02-3j); these tests drive the transport with a real
TLS server and the guarded network of the PUT tests, and check what crosses the wire and what the
engine is allowed to see of it.
"""

import asyncio
import logging
import ssl
import time
from types import SimpleNamespace

import pytest

from tests.contracts.test_guarded_network import Connector, Stream
from tests.fixtures.http_server import Reply, TlsServer
from tests.integration.test_storage_transport import (
    API,
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
from yorunge.adapters.storage_transport import (
    TransferHttpxTransport,
    TransferSession,
    _DownloadChunks,
)
from yorunge.application.download_transport import DownloadRequest, DownloadTarget
from yorunge.application.http_transport import HttpRequest
from yorunge.domain.credentials import SecretValue
from yorunge.domain.download import MAX_DOWNLOAD_BYTES
from yorunge.domain.download_response import ContentRange, DownloadResponse, ResumeAsk
from yorunge.domain.errors import YorungeError

ORIGIN = "https://api.localhost"
PREFIX = "/v1/files/evren-models/"
PATH = PREFIX + "weights.onnx"
QUERY = "?X-Amz-Credential=scope%2Fpart&signature=PRIVATE-URL-CANARY%2B%3D&x=1&x=2"
TAG = '"v1-3f9c"'
CONTENT = bytes(range(256)) * 8  # 2048 bytes


def target(path=PATH, query=QUERY, *, origin=ORIGIN, prefix=PREFIX):
    return DownloadTarget(origin + path + query, origin=origin, prefix=prefix)


def request(key, *, ask=None, path=PATH, query=QUERY, max_bytes=MAX_DOWNLOAD_BYTES):
    return DownloadRequest(target(path, query), key.secret, ask, max_bytes=max_bytes)


def serve(certificates, reply, *, path=PATH, query=QUERY, extra=None):
    routes = {path + query: reply, **(extra or {})}
    return TlsServer(certificates, routes)


def fetch(owned, wanted, *, seconds=3, read=True):
    """One download through the owned session: the view, and the body when it is read."""

    async def run(transport):
        async with transport.open_download(wanted, deadline=time.monotonic() + seconds) as view:
            body = b"".join([chunk async for chunk in view.chunks()]) if read else b""
            return view.response, view.disposition, body, view.received

    return owned.download(run)


def failure(action):
    with pytest.raises(YorungeError) as error:
        action()
    return error.value.code


# --- what crosses the wire ------------------------------------------------------------------------


def test_a_download_carries_no_credential_even_beside_a_service_call_on_the_same_origin(
    certificates,
):
    key = credential()
    routes = {
        "/v1/check": Reply(headers=(("Set-Cookie", "session=must-not-replay"),)),
        PATH + QUERY: Reply(body=CONTENT, headers=(("ETag", TAG),)),
    }
    with TlsServer(certificates, routes) as api:
        owned, network, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def run(transport):
            service = HttpRequest(
                API, "GET", "check", credential=key, read_only=True, service_id="evren-platform"
            )
            async with transport.open(service, deadline=time.monotonic() + 3) as response:
                b"".join([part async for part in response.chunks()])
            async with transport.open_download(request(key), deadline=time.monotonic() + 3) as view:
                return b"".join([chunk async for chunk in view.chunks()])

        with owned:
            assert owned.download(run) == CONTENT
        get = [r for r in api.requests if r.path == PATH + QUERY][0]
        names = {name.lower() for name, _ in get.headers}
        assert names == {"host", "accept-encoding"}  # nothing else, in particular no credential
        assert get.header("Accept-Encoding") == "identity" and get.header("Host") == "api.localhost"
        service_call = [r for r in api.requests if r.path == "/v1/check"][0]
        assert service_call.header("X-API-Key") == SECRET  # the service call kept its own
        assert "cookie" not in names
        assert len(network.connections) == 1  # one connection served both: reuse is what is tested


def test_a_resume_adds_exactly_range_and_if_range(certificates):
    key = credential()
    ask = ResumeAsk(400, 2048, TAG)
    reply = Reply(
        status=206,
        body=CONTENT[400:],
        headers=(("Content-Range", "bytes 400-2047/2048"), ("ETag", TAG)),
    )
    with serve(certificates, reply) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            response, action, body, received = fetch(owned, request(key, ask=ask))
        assert (response.status, action, body, received) == (206, "continue", CONTENT[400:], 1648)
        assert response.content_range == ContentRange(400, 2047, 2048) and response.etag == TAG
        sent = api.requests[0]
        assert {name.lower(): value for name, value in sent.headers} == {
            "host": "api.localhost",
            "accept-encoding": "identity",
            "range": "bytes=400-",
            "if-range": TAG,
        }


# --- the answers, by the closed table -------------------------------------------------------------


def test_a_full_answer_is_typed_and_its_body_arrives_whole(certificates):
    key = credential()
    with serve(certificates, Reply(body=CONTENT, headers=(("ETag", TAG),))) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            response, action, body, received = fetch(owned, request(key))
    assert (response.status, response.framing, response.content_length) == (200, "length", 2048)
    assert (response.etag, action, body, received) == (TAG, "full", CONTENT, 2048)


def test_a_chunked_answer_is_typed_without_a_length(certificates):
    key = credential()
    framed = b"400\r\n" + CONTENT[:1024] + b"\r\n400\r\n" + CONTENT[1024:] + b"\r\n0\r\n\r\n"
    reply = Reply(body=framed, headers=(("Transfer-Encoding", "chunked"),))
    with serve(certificates, reply) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            response, action, body, _ = fetch(owned, request(key))
    assert (response.framing, response.content_length, action, body) == (
        "chunked",
        None,
        "full",
        CONTENT,
    )


@pytest.mark.parametrize(
    "reply,action",
    [
        (Reply(body=CONTENT, headers=(("ETag", TAG),)), "restart"),  # the range was ignored
        (
            Reply(
                status=206,
                body=CONTENT[400:],
                headers=(("Content-Range", "bytes 0-1647/2048"), ("ETag", TAG)),
            ),
            "discard_and_retry",
        ),
        (
            Reply(
                status=206,
                body=CONTENT[400:],
                headers=(("Content-Range", "bytes 400-2047/2048"), ("ETag", '"other"')),
            ),
            "discard_and_retry",
        ),
        (
            Reply(status=416, body=b"", headers=(("Content-Range", "bytes */2048"),)),
            "discard_and_retry",
        ),
    ],
    ids=["range ignored", "other range", "other tag", "unsatisfiable"],
)
def test_an_answer_to_a_resume_that_does_not_fit_calls_for_the_closed_action(
    certificates, reply, action
):
    key = credential()
    with serve(certificates, reply) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            response, found, _, _ = fetch(
                owned, request(key, ask=ResumeAsk(400, 2048, TAG)), read=False
            )
    assert found == action and len(api.requests) == 1


def test_a_sixteen_four_one_six_has_no_body_the_engine_may_read(certificates):
    key = credential()
    reply = Reply(status=416, body=b"", headers=(("Content-Range", "bytes */2048"),))
    with serve(certificates, reply) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            assert (
                failure(lambda: fetch(owned, request(key, ask=ResumeAsk(400, 2048, TAG))))
                == "invalid_request"
            )


@pytest.mark.parametrize(
    "reply,code",
    [
        (
            Reply(status=301, body=b"", headers=(("Location", PATH + "?elsewhere=1"),)),
            "remote_failed",
        ),
        (
            Reply(status=302, body=b"", headers=(("Location", PATH + "?elsewhere=1"),)),
            "remote_failed",
        ),
        (
            Reply(status=307, body=b"", headers=(("Location", PATH + "?elsewhere=1"),)),
            "remote_failed",
        ),
        (Reply(status=401, body=b"{}"), "remote_access_denied"),
        (Reply(status=403, body=b"{}"), "remote_access_denied"),
        (Reply(status=429, body=b"{}", headers=(("Retry-After", "1"),)), "remote_rate_limited"),
        (Reply(status=404, body=b"{}"), "remote_failed"),
        (Reply(status=410, body=b"{}"), "remote_failed"),
        (Reply(status=500, body=b"{}"), "remote_failed"),
        (Reply(status=503, body=b"{}", headers=(("Retry-After", "1"),)), "remote_failed"),
        (Reply(status=201, body=CONTENT), "invalid_response"),
        (Reply(status=204, body=b""), "invalid_response"),
        (Reply(body=CONTENT, headers=(("Content-Encoding", "gzip"),)), "invalid_response"),
        (
            Reply(status=206, body=CONTENT, headers=(("Content-Range", "bytes 0-2047/2048"),)),
            "invalid_response",
        ),
        (Reply(body=CONTENT, omit_length=True), "invalid_response"),  # closed by the connection
        (
            # Refused by the HTTP stack itself before the answer is typed: still one closed code.
            Reply(body=CONTENT, omit_length=True, headers=(("Transfer-Encoding", "identity"),)),
            "transport_failed",
        ),
        (
            Reply(
                body=b"",
                omit_length=True,
                headers=(("Content-Length", str(MAX_DOWNLOAD_BYTES + 1)),),
            ),
            "download_limit_exceeded",
        ),
    ],
    ids=[
        "301",
        "302",
        "307",
        "401",
        "403",
        "429",
        "404",
        "410",
        "500",
        "503",
        "201",
        "204",
        "gzip",
        "partial to a plain request",
        "no framing",
        "identity coding",
        "length over the limit",
    ],
)
def test_every_other_answer_is_one_closed_code_after_exactly_one_request(certificates, reply, code):
    key = credential()
    with serve(certificates, reply) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            assert failure(lambda: fetch(owned, request(key))) == code
        # A redirect is never followed, a throttle or a failure never retried, nothing else asked.
        assert len(api.requests) == 1 and api.requests[0].path == PATH + QUERY


# --- the body -------------------------------------------------------------------------------------


def test_a_body_cut_short_is_incomplete(certificates):
    key = credential()
    cut = Reply(body=CONTENT, truncate_at=600)  # Content-Length says 2048, 600 arrive
    with serve(certificates, cut) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            assert failure(lambda: fetch(owned, request(key))) == "download_incomplete"


def test_a_chunked_body_without_its_terminator_is_incomplete(certificates):
    key = credential()
    unterminated = b"400\r\n" + CONTENT[:1024] + b"\r\n"
    reply = Reply(
        body=unterminated,
        headers=(("Transfer-Encoding", "chunked"),),
        truncate_at=len(unterminated),
    )
    with serve(certificates, reply) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            assert failure(lambda: fetch(owned, request(key))) == "download_incomplete"


def test_a_connection_reset_in_the_body_is_incomplete(certificates):
    key = credential()
    reply = Reply(body=CONTENT * 64, reset_after_body=True, truncate_at=5000)
    with serve(certificates, reply) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            assert failure(lambda: fetch(owned, request(key))) == "download_incomplete"


def test_the_running_counter_stops_a_body_past_the_limit_with_the_download_code(certificates):
    key = credential()
    with serve(certificates, Reply(body=b"x" * 5000)) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            # 5000 bytes are declared and sent; this caller allows 1000.
            assert (
                failure(lambda: fetch(owned, request(key, max_bytes=1000)))
                == "download_limit_exceeded"
            )


def test_a_stalled_body_stops_at_the_deadline_with_a_timeout(certificates):
    key = credential()
    reply = Reply(body=b"y" * 4096, chunk_size=1024, chunk_delay=2.0)
    with serve(certificates, reply) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        started = time.monotonic()
        with owned:
            assert failure(lambda: fetch(owned, request(key), seconds=1.5)) == "transport_timeout"
        assert time.monotonic() - started < 6


def test_the_get_window_is_the_callers_not_the_puts_120_seconds(certificates):
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, _, instances = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            fetch(owned, request(key))
        transport = instances[0]
        window = transport._download_window(request(key), time.monotonic() + 3000)
        assert window - time.monotonic() > 2900  # not cut to the 120 s a PUT is given


def test_a_cancelled_download_closes_the_connection_and_the_session_still_works(certificates):
    key = credential()
    slow = Reply(body=b"z" * 200_000, chunk_size=1024, chunk_delay=0.05)
    other = "/v1/files/evren-models/other.onnx"
    routes = {PATH + QUERY: slow, other + QUERY: Reply(body=CONTENT)}
    with TlsServer(certificates, routes) as api:
        owned, _, instances = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def interrupted(transport):
            async def read():
                async with transport.open_download(
                    request(key), deadline=time.monotonic() + 30
                ) as view:
                    async for _ in view.chunks():
                        pass

            task = asyncio.create_task(read())
            await asyncio.sleep(0.5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            async with transport.open_download(
                request(key, path=other), deadline=time.monotonic() + 3
            ) as view:
                return b"".join([chunk async for chunk in view.chunks()])

        with owned:
            assert owned.download(interrupted) == CONTENT
        assert instances[0]._responses == set()
        assert api.disconnected.wait(3)


# --- what is allowed to be asked ------------------------------------------------------------------


def test_a_target_outside_the_owned_origin_or_with_another_key_is_refused_before_the_network(
    certificates,
):
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, network, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        stranger = DownloadRequest(
            DownloadTarget(
                "https://storage.localhost" + PATH + QUERY,
                origin="https://storage.localhost",
                prefix=PREFIX,
            ),
            key.secret,
        )
        other_key = DownloadRequest(target(), SecretValue("another-platform-key"))
        with owned:
            assert failure(lambda: fetch(owned, stranger)) == "invalid_service_target"
            assert failure(lambda: fetch(owned, other_key)) == "invalid_service_target"
        assert api.requests == [] and network.connections == []


def test_a_wire_header_that_is_not_the_described_one_is_refused_before_the_network(
    certificates, monkeypatch
):
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, network, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        wanted = request(key)
        monkeypatch.setattr(
            DownloadRequest,
            "wire_headers",
            lambda self: self.public_headers() + (("X-Extra", "1"),),
        )
        with owned:
            assert failure(lambda: fetch(owned, wanted)) == "invalid_service_target"
        assert api.requests == [] and network.connections == []


def test_a_request_is_closed_by_construction(certificates):
    key = credential()
    with pytest.raises(ValueError):
        ResumeAsk(0, 100, TAG)  # nothing to resume from
    with pytest.raises(ValueError):
        ResumeAsk(10, 100, 'W/"weak"')  # a weak tag is no identity
    for kwargs in ({"max_bytes": 0}, {"max_bytes": MAX_DOWNLOAD_BYTES + 1}, {"max_bytes": True}):
        assert (
            failure(lambda kwargs=kwargs: DownloadRequest(target(), key.secret, None, **kwargs))
            == "invalid_request"
        )
    assert failure(lambda: DownloadRequest(target(), "not a secret")) == "invalid_request"
    assert failure(lambda: DownloadRequest(target(), key.secret, "bytes=0-")) == "invalid_request"


# --- the address ----------------------------------------------------------------------------------


def test_the_signed_address_reaches_the_server_byte_for_byte(certificates):
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        with owned:
            fetch(owned, request(key))
    assert api.requests[0].path == PATH + QUERY  # %2F, %2B, %3D and repeated keys untouched


@pytest.mark.parametrize(
    "url,origin,prefix",
    [
        (ORIGIN + PREFIX + "..%2Fsecret" + QUERY, ORIGIN, PREFIX),  # an encoded slash in the path
        (ORIGIN + PREFIX + "a%2Fb" + QUERY, ORIGIN, PREFIX),
        (ORIGIN + PREFIX + "%2e%2e/x" + QUERY, ORIGIN, PREFIX),  # an encoded dot segment
        (ORIGIN + PREFIX + "../x", ORIGIN, PREFIX),
        (ORIGIN + "/v1/files/other/x" + QUERY, ORIGIN, PREFIX),  # outside the consumer's prefix
        (ORIGIN + "/v1/files/evren-models" + QUERY, ORIGIN, PREFIX),
        ("http://api.localhost" + PATH + QUERY, ORIGIN, PREFIX),
        (ORIGIN + ":8443" + PATH + QUERY, ORIGIN, PREFIX),
        ("https://user:pass@api.localhost" + PATH, ORIGIN, PREFIX),
        (ORIGIN + PATH + QUERY + "#fragment", ORIGIN, PREFIX),
        (
            "https://storage.localhost" + PATH + QUERY,
            ORIGIN,
            PREFIX,
        ),  # another origin than the owned one
        (ORIGIN + PATH + "?" + "a=" + "b" * 17000, ORIGIN, PREFIX),  # past 16 KiB
        (ORIGIN + PREFIX + "ağırlık" + QUERY, ORIGIN, PREFIX),  # not ASCII
        (ORIGIN + PREFIX + "a%00b" + QUERY, ORIGIN, PREFIX),
    ],
)
def test_an_address_outside_the_contract_is_not_a_target(url, origin, prefix):
    with pytest.raises(YorungeError) as error:
        DownloadTarget(url, origin=origin, prefix=prefix)
    assert error.value.code == "invalid_service_target"


def test_an_address_holding_the_selected_key_is_refused(certificates):
    key = credential()
    for url in (
        ORIGIN + PREFIX + SECRET + "/x",
        ORIGIN + PATH + "?token=" + SECRET,
        ORIGIN + PATH + "?token=" + SECRET.replace("-", "%2D"),
    ):
        wanted = DownloadTarget(url, origin=ORIGIN, prefix=PREFIX)
        with pytest.raises(YorungeError) as error:
            DownloadRequest(wanted, key.secret)
        assert error.value.code == "invalid_service_target"


def test_neither_the_address_nor_the_key_is_in_a_repr_an_error_or_a_log(certificates, caplog):
    key = credential()
    with serve(
        certificates, Reply(status=503, body=b'{"detail":"PRIVATE-PROVIDER-ANSWER"}')
    ) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        wanted = request(key)
        with caplog.at_level(logging.DEBUG), owned:
            with pytest.raises(YorungeError) as error:
                fetch(owned, wanted)
        shown = (
            repr(wanted)
            + repr(wanted.target)
            + str(error.value)
            + repr(error.value.envelope())
            + caplog.text
        )
        for canary in (
            "PRIVATE-URL-CANARY",
            "X-Amz-Credential",
            "PRIVATE-PROVIDER-ANSWER",
            SECRET,
            "weights.onnx",
        ):
            assert canary not in shown
        assert error.value.__cause__ is None and error.value.__context__ is None
    with pytest.raises(AttributeError):
        wanted.target._url = "x"  # type: ignore[misc]
    import pickle

    with pytest.raises(TypeError):
        pickle.dumps(wanted.target)


# --- the address policy and the certificate apply to a download too -------------------------------


@pytest.mark.parametrize(
    "addresses", [("127.0.0.1",), ("8.8.8.8", "10.0.0.1"), ("169.254.169.254",)]
)
def test_a_private_or_mixed_dns_answer_is_refused_before_any_connection(addresses):
    calls = []

    async def resolver(host, port, timeout):
        calls.append((host, port))
        return addresses

    key = credential()
    guarded = GuardedBackend(resolver=resolver)

    def factory():
        return TransferHttpxTransport(
            key, transport=GuardedHttpTransport(backend=guarded), storage_origins=(ORIGIN,)
        )

    async def run(transport):
        async with transport.open_download(request(key), deadline=time.monotonic() + 2):
            pytest.fail("a private address reached an HTTP response")

    with (
        TransferSession(key, transport_factory=factory, storage_origins=(ORIGIN,)) as owned,
        pytest.raises(YorungeError) as error,
    ):
        owned.download(run)
    assert error.value.code == "invalid_service_target"
    assert calls == [("api.localhost", 443)]


def test_an_untrusted_certificate_never_sends_a_byte_of_http(certificates):
    key = credential()
    with TlsServer(certificates, {}) as server:
        network = FixtureNetwork({"api.localhost": server})

        def factory():
            return TransferHttpxTransport(
                key,
                transport=GuardedHttpTransport(backend=network),  # the real public CA store
                storage_origins=(ORIGIN,),
            )

        async def run(transport):
            async with transport.open_download(request(key), deadline=time.monotonic() + 3):
                pytest.fail("an untrusted certificate was accepted")

        with (
            TransferSession(key, transport_factory=factory, storage_origins=(ORIGIN,)) as owned,
            pytest.raises(YorungeError) as error,
        ):
            owned.download(run)
        assert error.value.code == "transport_failed"
        assert error.value.__cause__ is error.value.__context__ is None
        assert len(network.connections) == 1 and not server.requests


# --- the wire is exactly the described request, whatever else changed it --------------------------


@pytest.mark.parametrize("change", ["url", "host", "cookie", "credential"])
def test_a_prepared_wire_that_changed_is_refused_before_the_network(
    certificates, monkeypatch, change
):
    import httpx

    key = credential()
    original = httpx.Request

    def changed(*args, **kwargs):
        value = original(*args, **kwargs)
        if change == "url":
            value.url = httpx.URL("https://api.localhost/v1/files/evren-models/other?x=1")
        elif change == "host":
            value.headers["Host"] = "other.example"
        elif change == "cookie":
            value.headers["Cookie"] = "session=1"
        else:
            value.headers["X-API-Key"] = SECRET
        return value

    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, network, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        monkeypatch.setattr(storage_transport.httpx, "Request", changed)
        with owned:
            assert failure(lambda: fetch(owned, request(key))) == "invalid_service_target"
        assert api.requests == [] and network.connections == []


@pytest.mark.parametrize("owned_origins", [(), ("https://storage.localhost",)])
def test_a_session_that_owns_other_origins_refuses_a_target_on_this_one(
    certificates, owned_origins
):
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, network, _ = session(
            key, certificates, {"api.localhost": api}, origins=owned_origins
        )
        with owned:
            assert failure(lambda: fetch(owned, request(key))) == "invalid_service_target"
        assert api.requests == [] and network.connections == []


# --- the answer's size and the time each phase may take -------------------------------------------


def test_a_header_stall_ends_at_the_phase_budget_not_at_the_callers_deadline(certificates):
    key = credential()
    with serve(certificates, Reply(body=CONTENT, header_delay=8.0)) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))
        started = time.monotonic()
        with owned:
            assert failure(lambda: fetch(owned, request(key), seconds=60)) == "transport_timeout"
        assert 4.0 < time.monotonic() - started < 7.5  # five seconds, not sixty


def test_the_get_window_reaches_the_connection_whole(certificates, monkeypatch):
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
            fetch(owned, request(key), seconds=3000)
    assert max(delays) > 2900  # not cut to the 120 s a PUT is given, where the clock is armed


# --- the deadline, and the end of the body -------------------------------------------------------


def test_a_deadline_that_strikes_in_the_body_arrives_inside_as_a_cancellation(certificates):
    key = credential()
    reply = Reply(body=b"y" * 4096, chunk_size=1024, chunk_delay=2.0)
    seen = []
    with serve(certificates, reply) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def run(transport):
            async with transport.open_download(
                request(key), deadline=time.monotonic() + 1.0
            ) as view:
                try:
                    async for _ in view.chunks():
                        pass
                except asyncio.CancelledError:
                    seen.append(view.received)  # a clean stop checkpoints here, then re-raises
                    raise

        with owned:
            assert failure(lambda: owned.download(run)) == "transport_timeout"
    assert len(seen) == 1 and seen[0] < 4096


def test_a_whole_body_ends_the_deadline_for_what_the_caller_does_next(certificates):
    key = credential()
    with serve(certificates, Reply(body=CONTENT, headers=(("ETag", TAG),))) as api:
        owned, _, instances = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def run(transport):
            async with transport.open_download(
                request(key), deadline=time.monotonic() + 1.0
            ) as view:
                assert view.complete is False
                body = b"".join([chunk async for chunk in view.chunks()])
                assert view.complete is True and view.received == len(CONTENT)
                await asyncio.sleep(1.4)  # the completion checkpoint and the publication
                return body

        with owned:
            assert owned.download(run) == CONTENT
        assert instances[0]._responses == set()


def test_a_body_that_was_not_read_to_its_end_is_still_timed_to_the_deadline(certificates):
    key = credential()
    with serve(certificates, Reply(body=CONTENT)) as api:
        owned, _, _ = session(key, certificates, {"api.localhost": api}, origins=(ORIGIN,))

        async def run(transport):
            async with transport.open_download(
                request(key), deadline=time.monotonic() + 1.0
            ) as view:
                chunks = view.chunks()
                await anext(chunks)  # one chunk, and the rest is never read
                assert view.complete is False
                await asyncio.sleep(1.4)

        with owned:
            assert failure(lambda: owned.download(run)) == "transport_timeout"


def view_of(framing, length, parts, *, terminated=True):
    typed = DownloadResponse(200, None, None, framing, length)
    finished = []
    view = SimpleNamespace(response=typed, received=0, finish=lambda: finished.append(True))

    async def inner():
        for part in parts:
            yield part

    return view, _DownloadChunks(view, inner()), finished


def test_the_end_of_a_body_is_checked_against_what_its_framing_promised():
    async def read(chunks):
        return [chunk async for chunk in chunks]

    view, chunks, finished = view_of("length", 10, [b"12345", b"67890"])
    assert asyncio.run(read(chunks)) == [b"12345", b"67890"] and finished == [True]
    view, chunks, finished = view_of("length", 10, [b"12345", b"678"])
    assert failure(lambda: asyncio.run(read(chunks))) == "download_incomplete"
    assert finished == []  # a short body is not a whole one
    view, chunks, finished = view_of("chunked", None, [b"abc"])
    assert asyncio.run(read(chunks)) == [b"abc"] and finished == [True]


# --- the peer: no HTTP byte before it is the address that was approved ---------------------------


class AfterTls(Stream):
    """A peer that is fine at connect time and another after the handshake."""

    def __init__(self):
        super().__init__(("1.1.1.1", 443))

    async def start_tls(self, context, server_hostname=None, timeout=None):
        self.peer = ("10.0.0.5", 443)
        self.sni = server_hostname
        return self


@pytest.mark.parametrize(
    "stream",
    [Stream(("10.0.0.5", 443)), Stream(("8.8.8.8", 443)), AfterTls(), Stream(None)],
    ids=["private peer", "other public peer", "private after the handshake", "no peer address"],
)
def test_a_peer_that_is_not_the_approved_address_is_sent_no_http_byte(stream):
    key = credential()
    connector = Connector(stream)

    async def resolver(host, port, timeout):
        return ("1.1.1.1",)

    guarded = GuardedBackend(resolver=resolver, backend=connector)

    def factory():
        low = GuardedHttpTransport(backend=guarded, verify=ssl.create_default_context())
        return TransferHttpxTransport(key, transport=low, storage_origins=(ORIGIN,))

    async def go(transport):
        async with transport.open_download(request(key), deadline=time.monotonic() + 3):
            return "opened"

    owned = TransferSession(key, transport_factory=factory, storage_origins=(ORIGIN,))
    with owned:
        assert failure(lambda: owned.download(go)) == "invalid_service_target"
    assert stream.writes == [] and stream.closed  # the connection was dropped unspoken-to


# --- the signed address is checked for the key as the service address is --------------------------

SECRET_PLACES = [
    ("a path segment", "https://api.localhost{prefix}{secret}.onnx?x=1", True),
    ("a path segment, percent-encoded", "https://api.localhost{prefix}{part}.onnx?x=1", True),
    ("a query key", "https://api.localhost{prefix}w.onnx?{secret}=1", True),
    ("a query value", "https://api.localhost{prefix}w.onnx?x={secret}", True),
    ("inside a query value", "https://api.localhost{prefix}w.onnx?x=a{secret}b", True),
    ("a query value, percent-encoded", "https://api.localhost{prefix}w.onnx?x={part}", True),
    ("a part of the key only", "https://api.localhost{prefix}w.onnx?x={short}", False),
    ("nowhere", "https://api.localhost{prefix}w.onnx?x=1", False),
]


@pytest.mark.parametrize(
    "place,pattern,found", SECRET_PLACES, ids=[row[0] for row in SECRET_PLACES]
)
def test_the_key_is_refused_in_a_signed_address_exactly_where_it_is_in_a_storage_one(
    place, pattern, found
):
    from datetime import UTC, datetime, timedelta

    from yorunge.application.storage import StorageTarget
    from yorunge.domain.capabilities import timestamp

    secret = SecretValue(SECRET)
    url = pattern.format(
        prefix=PREFIX,
        secret=SECRET,
        part="%" + format(ord(SECRET[0]), "02X") + SECRET[1:],
        short=SECRET[:12],
    )

    def refused(build):
        try:
            build().check_secret(secret)
        except YorungeError as error:
            return error.code
        return None

    signed = refused(lambda: DownloadTarget(url, origin=ORIGIN, prefix=PREFIX))
    stored = refused(
        lambda: StorageTarget(
            url,
            mode="direct",
            origin=ORIGIN,
            prefix=PREFIX,
            expires_at=timestamp(datetime.now(UTC) + timedelta(seconds=60)),
            service=None,
            dataset_id=None,
        )
    )
    assert signed == stored  # one rule, two places
    assert (signed is not None) is found


def test_a_target_cannot_lose_a_part():
    held = target()
    with pytest.raises(AttributeError):
        del held.origin
    with pytest.raises(AttributeError):
        held.origin = "https://elsewhere.localhost"
    assert held.origin == ORIGIN
