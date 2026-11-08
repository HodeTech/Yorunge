"""The signed GET over real loopback TLS: no credential, a closed request, one physical attempt.

The answer is typed by the download contract (P02-3j); these tests drive the transport with a real
TLS server and the guarded network of the PUT tests, and check what crosses the wire and what the
engine is allowed to see of it.
"""

import asyncio
import logging
import time

import pytest

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
from yorunge.adapters.guarded_http import GuardedHttpTransport
from yorunge.adapters.guarded_network import GuardedBackend
from yorunge.adapters.storage_transport import TransferHttpxTransport, TransferSession
from yorunge.application.download_transport import DownloadRequest, DownloadTarget
from yorunge.application.http_transport import HttpRequest
from yorunge.domain.credentials import SecretValue
from yorunge.domain.download import MAX_DOWNLOAD_BYTES
from yorunge.domain.download_response import ContentRange, ResumeAsk
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


def test_a_body_cut_short_is_incomplete_and_a_complete_one_is_not(certificates):
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
    for ask in (ResumeAsk,):
        with pytest.raises(ValueError):
            ask(0, 100, TAG)  # nothing to resume from
        with pytest.raises(ValueError):
            ask(10, 100, 'W/"weak"')  # a weak tag is no identity
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
