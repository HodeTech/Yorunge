"""Exercise the real HTTPX adapter through actual loopback TLS connections."""

import asyncio
import gzip
import hashlib
import logging
import socket
import ssl
import time

import httpx
import pytest

from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from yorunge.adapters.http_transport import HttpxTransport
from yorunge.application.http_transport import HttpCredential, HttpRequest
from yorunge.domain.credentials import SecretValue, normalize_target
from yorunge.domain.errors import YorungeError

CONNECT = socket.socket.connect
CONNECT_EX = socket.socket.connect_ex
GETADDRINFO = socket.getaddrinfo
SECRET = "tls-private-credential-canary-718252"
TARGET = normalize_target("https://localhost/v1")


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(tmp_path_factory.mktemp("tls-certificate"))


@pytest.fixture(autouse=True)
def actual_loopback_only():
    # The repository's autouse guard still forbids any non-loopback connection.
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


def request(endpoint="data", *, method="GET", authenticated=False, **kwargs):
    credential = (
        HttpCredential(
            "Authorization",
            SecretValue(SECRET),
            prefix="Bearer ",
            target=TARGET,
            service_id="evren-platform",
        )
        if authenticated
        else None
    )
    return HttpRequest(
        TARGET, method, endpoint, credential=credential, service_id="evren-platform", **kwargs
    )


async def consume(client, wanted, *, timeout=2.0):
    async with client.open(wanted, deadline=time.monotonic() + timeout) as response:
        chunks = [chunk async for chunk in response.chunks()]
        return response.status_code, response.headers, chunks


def collect(server, wanted, *, timeout=2.0, transport=None):
    async def run():
        async with HttpxTransport(transport=transport or server.transport()) as client:
            return await consume(client, wanted, timeout=timeout)

    return asyncio.run(run())


def test_real_tls_request_response_and_explicit_auth_snapshot(certificates):
    with TlsServer(certificates, {"/v1/data": Reply(body=b'{"value":"accepted"}')}) as server:
        status, headers, chunks = collect(
            server,
            request(
                method="POST",
                authenticated=True,
                headers=(("Content-Type", "application/json"),),
                content=b'{"question":"test"}',
            ),
        )
        assert status == 200
        assert ("content-type", "application/json") in tuple(
            (key.lower(), value) for key, value in headers
        )
        assert b"".join(chunks) == b'{"value":"accepted"}'
        assert len(server.requests) == 1
        received = server.requests[0]
        assert received.method == "POST"
        assert received.path == "/v1/data"
        assert received.header("Host") == "localhost"
        assert received.header("Authorization") == "Bearer " + SECRET
        assert received.header("Accept-Encoding") == "identity"
        assert received.body == b'{"question":"test"}'


@pytest.mark.parametrize("failure", ["ca", "hostname"])
def test_tls_ca_and_hostname_verification_are_real(certificates, failure):
    with TlsServer(certificates, {"/v1/data": Reply()}) as server:
        transport = (
            server.transport(context=ssl.create_default_context())
            if failure == "ca"
            else server.transport(hostname="127.0.0.1")
        )
        wanted = request(authenticated=True, read_only=True)
        with pytest.raises(YorungeError) as caught:
            collect(server, wanted, transport=transport)
        assert caught.value.code == "transport_failed"
        assert SECRET not in str(caught.value)
        assert "localhost" not in str(caught.value.envelope())
        assert server.requests == []


def test_redirect_never_contacts_second_tls_server_or_replays_auth(certificates):
    with TlsServer(certificates, {"/capture": Reply()}) as other:
        location = f"https://other.invalid:{other.port}/capture"
        with TlsServer(
            certificates,
            {"/v1/data": Reply(status=307, headers=(("Location", location),))},
        ) as server:
            wanted = request(method="POST", authenticated=True)
            with pytest.raises(YorungeError) as caught:
                collect(server, wanted)
            assert caught.value.code == "remote_failed"
            assert len(server.requests) == 1
            assert other.requests == []
            assert location not in str(caught.value.envelope())


def test_cookie_is_not_replayed_between_same_origin_paths_or_retry(certificates):
    def retry(record, count):
        return Reply(
            status=503 if count == 1 else 200,
            headers=(("Set-Cookie", "private_session=forbidden; Path=/"),),
        )

    with TlsServer(
        certificates,
        {
            "/v1/platform": Reply(headers=(("Set-Cookie", "session=forbidden; Path=/"),)),
            "/v1/llm": Reply(),
            "/v1/retry": retry,
        },
    ) as server:

        async def run():
            async with HttpxTransport(transport=server.transport()) as client:
                for endpoint in ("platform", "llm", "retry"):
                    await consume(client, request(endpoint, read_only=True))

        asyncio.run(run())
        assert [item.path for item in server.requests] == [
            "/v1/platform",
            "/v1/llm",
            "/v1/retry",
            "/v1/retry",
        ]
        assert all(item.header("Cookie") is None for item in server.requests)


@pytest.mark.parametrize("status", [408, 429, 502, 503, 504])
def test_explicit_read_only_get_has_at_most_two_attempts(certificates, status):
    def retry(record, count):
        return Reply(status=status if count == 1 else 200)

    with TlsServer(certificates, {"/v1/data": retry}) as server:
        result = collect(server, request(read_only=True))
        assert result[0] == 200
        assert len(server.requests) == 2


@pytest.mark.parametrize("method,read_only", [("GET", False), ("POST", False)])
def test_default_read_and_effectful_calls_never_retry(certificates, method, read_only):
    with TlsServer(certificates, {"/v1/data": Reply(status=503)}) as server:
        wanted = request(method=method, read_only=read_only)
        with pytest.raises(YorungeError) as caught:
            collect(server, wanted)
        assert caught.value.code == "remote_failed"
        assert len(server.requests) == 1


@pytest.mark.parametrize("status", [401, 403])
def test_auth_failure_is_controlled_and_not_retried(certificates, status):
    with TlsServer(certificates, {"/v1/data": Reply(status=status)}) as server:
        wanted = request(authenticated=True, read_only=True)
        with pytest.raises(YorungeError) as caught:
            collect(server, wanted)
        assert caught.value.code == "remote_access_denied"
        assert caught.value.exit_code == 3
        assert len(server.requests) == 1
        assert SECRET not in str(caught.value.envelope())


def test_retry_after_that_does_not_fit_total_is_not_shortened(certificates):
    with TlsServer(
        certificates,
        {"/v1/data": Reply(status=429, headers=(("Retry-After", "60"),))},
    ) as server:
        started = time.monotonic()
        wanted = request(read_only=True)
        with pytest.raises(YorungeError) as caught:
            collect(server, wanted, timeout=0.4)
        assert caught.value.code == "remote_rate_limited"
        assert len(server.requests) == 1
        assert time.monotonic() - started < 1.0


def test_retry_after_minimum_is_honored_inside_shared_total(certificates):
    timestamps = []

    def retry(record, count):
        timestamps.append(time.monotonic())
        return Reply(
            status=429 if count == 1 else 200,
            headers=(("Retry-After", "1"),),
        )

    with TlsServer(certificates, {"/v1/data": retry}) as server:
        assert collect(server, request(read_only=True), timeout=3)[0] == 200
        assert len(server.requests) == 2
        assert timestamps[1] - timestamps[0] >= 1.0


@pytest.mark.parametrize(
    "reply",
    [
        Reply(header_delay=0.6),
        Reply(header_drip=0.005),
        Reply(body=b"x" * 65_536, chunk_size=1024, chunk_delay=0.02),
    ],
    ids=["silent-headers", "trickle-headers", "trickle-body"],
)
def test_total_deadline_covers_real_header_and_body_wait(certificates, reply):
    with TlsServer(certificates, {"/v1/data": reply}) as server:
        started = time.monotonic()
        wanted = request(read_only=True)
        with pytest.raises(YorungeError) as caught:
            collect(server, wanted, timeout=0.15)
        assert caught.value.code == "transport_timeout"
        assert time.monotonic() - started < 1.0
        assert len(server.requests) == 1


def test_deadline_also_covers_consumer_work_inside_response_context(certificates):
    with TlsServer(certificates, {"/v1/data": Reply()}) as server:

        async def run():
            async with HttpxTransport(transport=server.transport()) as client:
                async with client.open(request(), deadline=time.monotonic() + 0.15):
                    await asyncio.sleep(0.6)

        running = run()
        with pytest.raises(YorungeError) as caught:
            asyncio.run(running)
        assert caught.value.code == "transport_timeout"
        assert len(server.requests) == 1


def test_past_deadline_is_rejected_before_any_request(certificates):
    with TlsServer(certificates, {"/v1/data": Reply()}) as server:

        async def run():
            async with HttpxTransport(transport=server.transport()) as client:
                async with client.open(request(), deadline=time.monotonic() - 1):
                    pytest.fail("expired request reached the consumer")

        running = run()
        with pytest.raises(YorungeError) as caught:
            asyncio.run(running)
        assert caught.value.code == "transport_timeout"
        assert server.requests == []


def test_default_client_ignores_proxy_ca_and_netrc_environment(tmp_path, monkeypatch):
    missing = str(tmp_path / "does-not-exist")
    for name, value in (
        ("HTTPS_PROXY", "unsupported-proxy-scheme://environment.invalid"),
        ("ALL_PROXY", "unsupported-proxy-scheme://environment.invalid"),
        ("SSL_CERT_FILE", missing),
        ("SSL_CERT_DIR", missing),
        ("NETRC", missing),
    ):
        monkeypatch.setenv(name, value)

    async def run():
        # Construction with HTTPX's ambient defaults would read the missing CA
        # or reject the proxy scheme. No endpoint or DNS lookup is performed.
        async with HttpxTransport():
            pass

    asyncio.run(run())


def test_raw_chunks_are_bounded_and_convenience_decoders_are_not_used(certificates, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("HTTPX convenience decoding bypassed the bounded raw path")

    for name in ("aread", "json", "aiter_bytes", "aiter_lines"):
        monkeypatch.setattr(httpx.Response, name, forbidden)
    monkeypatch.setattr(httpx.Response, "text", property(forbidden))
    data = bytes(range(256)) * 384
    with TlsServer(certificates, {"/v1/data": Reply(body=data)}) as server:
        status, headers, chunks = collect(server, request(max_bytes=len(data)))
        assert status == 200
        assert all(0 < len(chunk) <= 32_768 for chunk in chunks)
        assert hashlib.sha256(b"".join(chunks)).digest() == hashlib.sha256(data).digest()


@pytest.mark.parametrize("bomb", [False, True])
def test_content_encoding_is_rejected_before_decompression(certificates, bomb):
    body = gzip.compress(b"x" * (2 * 1024 * 1024 if bomb else 20))
    with TlsServer(
        certificates,
        {"/v1/data": Reply(body=body, headers=(("Content-Encoding", "gzip"),))},
    ) as server:
        wanted = request(read_only=True)
        with pytest.raises(YorungeError) as caught:
            collect(server, wanted)
        assert caught.value.code == "invalid_response"
        assert len(server.requests) == 1


def test_total_byte_limit_is_enforced_without_retry(certificates):
    with TlsServer(certificates, {"/v1/data": Reply(body=b"123456789")}) as server:
        wanted = request(max_bytes=8, read_only=True)
        with pytest.raises(YorungeError) as caught:
            collect(server, wanted)
        assert caught.value.code == "invalid_response"
        assert len(server.requests) == 1


def test_truncated_raw_body_is_not_replayed(certificates):
    with TlsServer(
        certificates,
        {"/v1/data": Reply(body=b"x" * 65_536, truncate_at=32_768)},
    ) as server:
        wanted = request(read_only=True)
        with pytest.raises(YorungeError) as caught:
            collect(server, wanted)
        assert caught.value.code == "transport_failed"
        assert len(server.requests) == 1


def test_task_cancellation_closes_connection_and_propagates(certificates):
    with TlsServer(
        certificates,
        {"/v1/data": Reply(body=b"x" * 65_536, chunk_size=1024, chunk_delay=0.05)},
    ) as server:

        async def run():
            async def reading():
                async with HttpxTransport(transport=server.transport()) as client:
                    await consume(client, request(read_only=True))

            task = asyncio.create_task(reading())
            end = time.monotonic() + 2
            while not server.requests:
                assert time.monotonic() < end
                await asyncio.sleep(0.005)
            await asyncio.sleep(0.02)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert task.cancelled()

        asyncio.run(run())
        assert len(server.requests) == 1
        assert server.disconnected.wait(1), "cancelled client kept its TLS connection open"


def test_normal_early_context_close_does_not_manufacture_cancellation(certificates):
    with TlsServer(
        certificates,
        {"/v1/data": Reply(body=b"x" * 65_536, chunk_size=1024, chunk_delay=0.03)},
    ) as server:

        async def run():
            async with HttpxTransport(transport=server.transport()) as client:
                async with client.open(request(), deadline=time.monotonic() + 2):
                    pass
            assert asyncio.current_task().cancelling() == 0

        asyncio.run(run())
        assert len(server.requests) == 1
        assert server.disconnected.wait(1)


def test_same_owned_session_reuses_its_tls_connection(certificates):
    with TlsServer(certificates, {"/v1/data": Reply()}) as server:

        async def run():
            async with HttpxTransport(transport=server.transport()) as client:
                for _ in range(3):
                    await consume(client, request())

        asyncio.run(run())
        assert len(server.requests) == 3
        assert len({record.connection for record in server.requests}) == 1


def test_third_response_waits_for_bounded_pool_and_times_out_without_request(certificates):
    with TlsServer(certificates, {"/v1/data": Reply()}) as server:

        async def run():
            release = asyncio.Event()
            ready = []
            async with HttpxTransport(transport=server.transport()) as client:

                async def hold():
                    async with client.open(request(), deadline=time.monotonic() + 3):
                        ready.append(True)
                        await release.wait()

                holders = [asyncio.create_task(hold()) for _ in range(2)]
                try:
                    end = time.monotonic() + 2
                    while len(ready) != 2:
                        assert time.monotonic() < end
                        await asyncio.sleep(0.005)
                    wanted = request()
                    with pytest.raises(YorungeError) as caught:
                        await consume(client, wanted, timeout=1.5)
                    assert caught.value.code == "transport_timeout"
                    assert len(server.requests) == 2
                finally:
                    release.set()
                    await asyncio.gather(*holders)

        asyncio.run(run())


def test_response_cannot_be_consumed_by_another_task_or_after_close(certificates):
    with TlsServer(certificates, {"/v1/data": Reply()}) as server:

        async def run():
            async with HttpxTransport(transport=server.transport()) as client:
                async with client.open(request(), deadline=time.monotonic() + 2) as response:

                    async def foreign_reader():
                        return [chunk async for chunk in response.chunks()]

                    foreign = asyncio.create_task(foreign_reader())
                    with pytest.raises(YorungeError) as caught:
                        await foreign
                    assert caught.value.code == "invalid_request"
                    assert b"".join([chunk async for chunk in response.chunks()])
                with pytest.raises(YorungeError) as caught:
                    response.chunks()
                assert caught.value.code == "invalid_request"

        asyncio.run(run())
        assert len(server.requests) == 1


def test_owned_library_info_debug_logs_hide_url_and_preserve_unrelated_logging(
    certificates, caplog
):
    marker = "private-path-query-canary-802625"
    endpoint = "sensitive-" + marker
    route = "/v1/" + endpoint + "?search=" + marker
    with TlsServer(certificates, {route: Reply(headers=(("X-Remote-Private", SECRET),))}) as server:
        with caplog.at_level(logging.DEBUG):

            async def run():
                async with HttpxTransport(transport=server.transport()) as client:
                    await consume(
                        client,
                        request(endpoint, authenticated=True, query=(("search", marker),)),
                    )
                logging.getLogger("httpx").info("unrelated-httpx-log-is-visible")
                logging.getLogger("example.application").debug("unrelated-debug-is-visible")

            asyncio.run(run())
        assert marker not in caplog.text
        assert SECRET not in caplog.text
        assert "unrelated-httpx-log-is-visible" in caplog.text
        assert "unrelated-debug-is-visible" in caplog.text


@pytest.mark.parametrize("prior", [None, "state_changed", "cancelled"])
def test_session_close_io_failure_is_safe_and_does_not_replace_prior_failure(certificates, prior):
    with TlsServer(certificates, {"/v1/data": Reply()}) as server:
        actual = server.transport()

        class FailingClose(httpx.AsyncBaseTransport):
            async def handle_async_request(self, wanted):
                return await actual.handle_async_request(wanted)

            async def aclose(self):
                await actual.aclose()
                raise OSError(SECRET)

        async def run():
            async with HttpxTransport(transport=FailingClose()) as client:
                await consume(client, request())
                if prior == "cancelled":
                    raise asyncio.CancelledError
                if prior is not None:
                    raise YorungeError(prior)

        if prior == "cancelled":
            running = run()
            with pytest.raises(asyncio.CancelledError):
                asyncio.run(running)
        else:
            running = run()
            with pytest.raises(YorungeError) as caught:
                asyncio.run(running)
            assert caught.value.code == (prior or "transport_failed")
            assert SECRET not in str(caught.value.envelope())
