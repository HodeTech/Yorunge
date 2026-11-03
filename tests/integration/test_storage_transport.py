"""Actual two-origin TLS upload, shared service pool and private wire boundaries."""

import asyncio
import hashlib
import logging
import socket
import time
from datetime import UTC, datetime, timedelta
from functools import partial

import httpcore
import pytest

from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from yorunge.adapters.guarded_http import GuardedHttpTransport
from yorunge.adapters.guarded_network import GuardedBackend
from yorunge.adapters.storage_source import DescriptorByteSource
from yorunge.adapters.storage_transport import TransferHttpxTransport, TransferSession
from yorunge.application.http_transport import HttpCredential, HttpRequest
from yorunge.application.storage import StorageRequest, StorageTarget
from yorunge.domain.capabilities import timestamp
from yorunge.domain.credentials import SecretValue, normalize_target
from yorunge.domain.dataset_manifest import DatasetFile
from yorunge.domain.dataset_upload import UploadRoot
from yorunge.domain.errors import YorungeError

CONNECT, CONNECT_EX, GETADDRINFO = (
    socket.socket.connect,
    socket.socket.connect_ex,
    socket.getaddrinfo,
)
NOW = datetime(2026, 11, 2, 11, tzinfo=UTC)
API = normalize_target("https://api.localhost/v1")
DATASET = "00000000-0000-4000-8000-000000000001"
PROXY_PREFIX = f"/v1/datasets/{DATASET}/upload/"
SIGNED_QUERY = "?X-Amz-Credential=scope%2Fpart&signature=PRIVATE-URL-CANARY%2B%3D&x=1&x=2"
SECRET = "private-platform-wire-key-DO-NOT-PUBLISH"


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(
        tmp_path_factory.mktemp("storage-ca"),
        names=("localhost", "api.localhost", "storage.localhost"),
    )


@pytest.fixture(autouse=True)
def loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


class FixtureNetwork(GuardedBackend):
    """Only this test maps verified loopback peers to named ephemeral TLS origins."""

    def __init__(self, routes):
        self.routes, self.connections = routes, []

        async def resolver(host, port, timeout):
            assert host in routes
            return ("127.0.0.1",)

        super().__init__(resolver=resolver, allowed=lambda value: value == "127.0.0.1")

    async def _connect(self, pinned, port, timeout, options, original_host):
        assert pinned == "127.0.0.1"
        assert port == 443
        self.connections.append((pinned, port, original_host))
        return await httpcore.AnyIOBackend().connect_tcp(
            pinned, self.routes[original_host].port, timeout=timeout, socket_options=options
        )


def credential():
    return HttpCredential("X-API-Key", SecretValue(SECRET), target=API, service_id="evren-platform")


def source(tmp_path, data=b"synthetic-image-content"):
    root = tmp_path.resolve() / "data"
    root.mkdir(exist_ok=True)
    path = root / "fixture.bin"
    path.write_bytes(data)
    info = root.stat()
    return DescriptorByteSource(
        UploadRoot(anchor=str(root), device=info.st_dev, inode=info.st_ino),
        DatasetFile(path=path.name, size=len(data), sha256=hashlib.sha256(data).hexdigest()),
        deadline=time.monotonic() + 120,
    )


def direct(body, key, *, expiry=None, query=SIGNED_QUERY):
    target = StorageTarget(
        "https://storage.localhost/bucket/object" + query,
        mode="direct",
        origin="https://storage.localhost",
        prefix="/bucket/",
        expires_at=expiry or timestamp(NOW + timedelta(seconds=60)),
        service=None,
        dataset_id=None,
    )
    return StorageRequest(target, body, key.secret, "application/octet-stream")


def proxy(body, key):
    target = StorageTarget(
        API.service_origin + PROXY_PREFIX + "put?key=objects%2Ffixture",
        mode="proxy",
        origin=API.service_origin,
        prefix=PROXY_PREFIX,
        expires_at=None,
        service=API,
        dataset_id=DATASET,
    )
    return StorageRequest(target, body, key.secret, "application/octet-stream", credential=key)


def session(
    key, certificates, routes, *, clock=lambda: NOW, origins=("https://storage.localhost",)
):
    network, instances = FixtureNetwork(routes), []

    def factory():
        low = GuardedHttpTransport(
            backend=network, verify=next(iter(routes.values())).client_context()
        )
        value = TransferHttpxTransport(key, transport=low, utc_clock=clock, storage_origins=origins)
        instances.append(value)
        return value

    return (
        TransferSession(key, transport_factory=factory, storage_origins=origins),
        network,
        instances,
    )


async def put(transport, request, *, seconds=3):
    async with transport.open_storage(request, deadline=time.monotonic() + seconds) as response:
        body = b"".join([part async for part in response.chunks()])
        return body, response.sent_bytes, response.sent_sha256


def test_actual_proxy_and_direct_share_client_but_never_auth_cookie_or_url_logs(
    tmp_path, certificates, caplog
):
    key, payload = credential(), b"one small real TLS upload"
    storage_path = "/bucket/object" + SIGNED_QUERY
    proxy_path = PROXY_PREFIX + "put?key=objects%2Ffixture"
    with (
        TlsServer(
            certificates,
            {
                "/v1/check": Reply(headers=(("Set-Cookie", "session=must-not-replay"),)),
                proxy_path: Reply(),
            },
        ) as api,
        TlsServer(certificates, {storage_path: Reply()}) as storage,
    ):
        owned, network, instances = session(
            key, certificates, {"api.localhost": api, "storage.localhost": storage}
        )
        first, second = source(tmp_path, payload), source(tmp_path, payload)

        async def run(transport):
            request = HttpRequest(
                API, "GET", "check", credential=key, read_only=True, service_id="evren-platform"
            )
            async with transport.open(request, deadline=time.monotonic() + 3) as response:
                assert b"accepted" in b"".join([part async for part in response.chunks()])
            a = await put(transport, direct(first, key))
            b = await put(transport, proxy(second, key))
            return a, b

        with caplog.at_level(logging.DEBUG), owned:
            first_result, second_result = owned.exchange(run)
            assert len(instances) == 1
            assert len(instances[0]._responses) == 0
        assert [r.method for r in api.requests] == ["GET", "PUT"]
        assert len(storage.requests) == 1
        assert storage.requests[0].path == storage_path
        assert all(r.header("X-API-Key") == SECRET for r in api.requests)
        assert storage.requests[0].header("X-API-Key") is None
        assert all(
            r.header("Cookie") is None and r.header("Authorization") is None
            for r in [*api.requests, *storage.requests]
        )
        assert api.requests[-1].body == storage.requests[0].body == payload
        assert all(
            result[1:] == (len(payload), hashlib.sha256(payload).hexdigest())
            for result in [first_result, second_result]
        )
        assert {item[2] for item in network.connections} == {"api.localhost", "storage.localhost"}
    assert "PRIVATE-URL-CANARY" not in caplog.text
    assert SECRET not in caplog.text
    assert first.complete
    assert second.complete
    assert first._file_fd is second._file_fd is None


@pytest.mark.parametrize("seconds", [-1, 0, 4, 5])
def test_expired_or_insufficient_url_expiry_has_zero_tcp_and_http(tmp_path, certificates, seconds):
    key = credential()
    with TlsServer(certificates, {}) as server:
        owned, network, _ = session(key, certificates, {"storage.localhost": server})
        body = source(tmp_path)
        request = direct(body, key, expiry=timestamp(NOW + timedelta(seconds=seconds)))
        rejected_call = partial(owned.exchange, lambda transport: put(transport, request))
        with owned, pytest.raises(YorungeError) as failure:
            rejected_call()
        assert failure.value.code == "transport_timeout"
        assert not network.connections
        assert not server.requests
        assert body._file_fd is None
        assert body.sent_bytes == 0


@pytest.mark.parametrize("status", [302, 307, 401, 403, 404, 429, 500, 503])
def test_effect_http_failure_never_retries_redirects_or_proxy_fallback(
    tmp_path, certificates, status
):
    key = credential()
    path = "/bucket/object" + SIGNED_QUERY
    reply = Reply(
        status=status,
        body=b"PRIVATE-ERROR-BODY",
        headers=(("Location", "https://elsewhere.example/canary"),),
    )
    with TlsServer(certificates, {path: reply}) as server:
        owned, network, _ = session(key, certificates, {"storage.localhost": server})
        body = source(tmp_path)
        rejected_call = partial(owned.exchange, lambda transport: put(transport, direct(body, key)))
        with owned, pytest.raises(YorungeError) as failure:
            rejected_call()
        assert failure.value.code in {
            "remote_failed",
            "remote_rate_limited",
            "remote_access_denied",
        }
        assert len(server.requests) == len(network.connections) == 1
        assert "PRIVATE" not in str(failure.value)
        assert "PRIVATE" not in repr(failure.value)
        assert failure.value.__cause__ is failure.value.__context__ is None
        assert body._file_fd is None


@pytest.mark.parametrize(
    "reply",
    [
        Reply(body=b"x" * 65537),
        Reply(headers=(("Content-Encoding", "gzip"),)),
        Reply(body=b"truncated", truncate_at=3),
    ],
)
def test_raw_response_guards_and_cleanup(tmp_path, certificates, reply):
    key = credential()
    with TlsServer(certificates, {"/bucket/object" + SIGNED_QUERY: reply}) as server:
        owned, _, instances = session(key, certificates, {"storage.localhost": server})
        body = source(tmp_path)
        rejected_call = partial(owned.exchange, lambda transport: put(transport, direct(body, key)))
        with owned, pytest.raises(YorungeError) as failure:
            rejected_call()
        assert failure.value.code in {"invalid_response", "transport_failed"}
        assert body._file_fd is None
        assert len(instances[0]._responses) == 0
        assert instances[0]._slots._value == 2
        assert len(server.requests) == 1


@pytest.mark.parametrize("change", ["url", "host", "content-length", "content-type", "auth-header"])
def test_prepared_wire_changes_fail_before_dns_or_source_read(
    tmp_path, certificates, monkeypatch, change
):
    import httpx

    from yorunge.adapters import storage_transport

    key = credential()
    body = source(tmp_path)
    request = direct(body, key)
    original = httpx.Request

    def changed(*args, **kwargs):
        value = original(*args, **kwargs)
        if change == "url":
            value.url = httpx.URL("https://storage.localhost/bucket/other?signature=changed")
        elif change == "host":
            value.headers["Host"] = "other.example"
        elif change == "content-length":
            value.headers["Content-Length"] = "9999"
        elif change == "content-type":
            value.headers["Content-Type"] = "image/png"
        else:
            value.headers["X-API-Key"] = SECRET
        return value

    with TlsServer(certificates, {}) as server:
        owned, network, _ = session(key, certificates, {"storage.localhost": server})
        monkeypatch.setattr(storage_transport.httpx, "Request", changed)
        rejected_call = partial(owned.exchange, lambda transport: put(transport, request))
        with owned, pytest.raises(YorungeError) as failure:
            rejected_call()
        assert failure.value.code == "invalid_service_target"
        assert not server.requests
        assert not network.connections
        assert body.sent_bytes == 0
        assert body._file_fd is None


def test_presign_response_cannot_add_storage_origin_to_owned_session(tmp_path, certificates):
    key = credential()
    with TlsServer(certificates, {}) as server:
        owned, network, _ = session(key, certificates, {"storage.localhost": server}, origins=())
        body = source(tmp_path)
        rejected_call = partial(owned.exchange, lambda transport: put(transport, direct(body, key)))
        with owned, pytest.raises(YorungeError) as failure:
            rejected_call()
        assert failure.value.code == "invalid_service_target"
        assert not server.requests
        assert not network.connections
        assert body.sent_bytes == 0


def test_same_origin_direct_request_does_not_inherit_prior_platform_auth(tmp_path, certificates):
    key = credential()
    path = "/bucket/object" + SIGNED_QUERY
    with TlsServer(certificates, {"/v1/check": Reply(), path: Reply()}) as server:
        owned, network, _ = session(
            key, certificates, {"api.localhost": server}, origins=(API.service_origin,)
        )
        body = source(tmp_path)
        target = StorageTarget(
            API.service_origin + path,
            mode="direct",
            origin=API.service_origin,
            prefix="/bucket/",
            expires_at=timestamp(NOW + timedelta(seconds=60)),
            service=None,
            dataset_id=None,
        )

        async def run(transport):
            request = HttpRequest(
                API, "GET", "check", credential=key, read_only=True, service_id="evren-platform"
            )
            async with transport.open(request, deadline=time.monotonic() + 2) as response:
                assert [part async for part in response.chunks()]
            await put(
                transport, StorageRequest(target, body, key.secret, "application/octet-stream")
            )

        with owned:
            owned.exchange(run)
        assert server.requests[0].header("X-API-Key") == SECRET
        assert server.requests[1].header("X-API-Key") is None
        assert len(network.connections) == 1


def test_two_storage_calls_and_service_call_share_two_slots(tmp_path, certificates):

    key = credential()
    path = "/bucket/object" + SIGNED_QUERY
    with (
        TlsServer(certificates, {path: Reply()}) as server,
        TlsServer(certificates, {"/v1/check": Reply()}) as api,
    ):
        owned, network, instances = session(
            key, certificates, {"storage.localhost": server, "api.localhost": api}
        )
        bodies = [source(tmp_path) for _ in range(2)]

        async def run(transport):
            gates, entered = (
                [asyncio.Event() for _ in range(2)],
                [asyncio.Event() for _ in range(2)],
            )
            for index, body in enumerate(bodies):
                original = body.__anext__

                async def gated_next(original=original, index=index):
                    entered[index].set()
                    await gates[index].wait()
                    return await original()

                # Special methods are resolved on the type, so a tiny trusted
                # wrapper below gates the real descriptor iterator, not setattr.
                body._test_next = gated_next

            class GatedSource:
                def __init__(self, wrapped):
                    self.wrapped = wrapped

                @property
                def size(self):
                    return self.wrapped.size

                @property
                def sha256(self):
                    return self.wrapped.sha256

                @property
                def sent_bytes(self):
                    return self.wrapped.sent_bytes

                @property
                def sent_sha256(self):
                    return self.wrapped.sent_sha256

                @property
                def complete(self):
                    return self.wrapped.complete

                def chunks(self):
                    self.wrapped.chunks()
                    return self

                def __aiter__(self):
                    return self

                async def __anext__(self):
                    return await self.wrapped._test_next()

                async def aclose(self):
                    await self.wrapped.aclose()

            tasks = [
                asyncio.create_task(put(transport, direct(GatedSource(body), key), seconds=4))
                for body in bodies
            ]
            try:
                await asyncio.wait_for(asyncio.gather(*(event.wait() for event in entered)), 2)
                request = HttpRequest(
                    API, "GET", "check", credential=key, read_only=True, service_id="evren-platform"
                )
                deadline = time.monotonic() + 3

                async def acquire_third_slot():
                    async with transport.open(request, deadline=deadline):
                        pytest.fail("third request acquired a separate slot")

                with pytest.raises(YorungeError) as failure:
                    await acquire_third_slot()
                assert failure.value.code == "transport_timeout"
                assert api.requests == []
                assert len(network.connections) == 2
            finally:
                for gate in gates:
                    gate.set()
            await asyncio.gather(*tasks)

        with owned:
            owned.exchange(run)
            assert instances[0]._slots._value == 2
        assert len(server.requests) == 2
        assert all(body.complete for body in bodies)


def test_normal_early_response_close_releases_pool_and_source(tmp_path, certificates):
    key = credential()
    path = "/bucket/object" + SIGNED_QUERY
    with (
        TlsServer(
            certificates, {path: Reply(body=b"x" * 131072, chunk_size=1024, chunk_delay=0.001)}
        ) as storage,
        TlsServer(certificates, {"/v1/check": Reply()}) as api,
    ):
        owned, _, instances = session(
            key, certificates, {"api.localhost": api, "storage.localhost": storage}
        )
        body = source(tmp_path)

        async def run(transport):
            async with transport.open_storage(
                direct(body, key), deadline=time.monotonic() + 3
            ) as response:
                iterator = response.chunks()
                assert len(await anext(iterator)) <= 32768
            request = HttpRequest(
                API, "GET", "check", credential=key, read_only=True, service_id="evren-platform"
            )
            async with transport.open(request, deadline=time.monotonic() + 3) as response:
                assert [chunk async for chunk in response.chunks()]

        with owned:
            owned.exchange(run)
            assert instances[0]._slots._value == 2
            assert not instances[0]._responses
        assert body.complete
        assert body._file_fd is None


def test_cancel_mid_source_closes_on_owner_task_and_session_still_works(tmp_path, certificates):
    key = credential()
    path = "/bucket/object" + SIGNED_QUERY
    with (
        TlsServer(certificates, {path: Reply()}) as storage,
        TlsServer(certificates, {"/v1/check": Reply()}) as api,
    ):
        owned, _, instances = session(
            key, certificates, {"api.localhost": api, "storage.localhost": storage}
        )
        base = source(tmp_path, b"x" * (2 * 1024 * 1024))

        async def run(transport):
            reached, gate = asyncio.Event(), asyncio.Event()

            class PausedSource:
                def __getattr__(self, name):
                    return getattr(base, name)

                def chunks(self):
                    base.chunks()
                    return self

                def __aiter__(self):
                    return self

                async def __anext__(self):
                    if base.sent_bytes:
                        reached.set()
                        await gate.wait()
                    return await anext(base)

                async def aclose(self):
                    await base.aclose()

            task = asyncio.create_task(put(transport, direct(PausedSource(), key)))
            await asyncio.wait_for(reached.wait(), 2)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert base._file_fd is None
            assert not base.complete
            request = HttpRequest(
                API, "GET", "check", credential=key, read_only=True, service_id="evren-platform"
            )
            async with transport.open(request, deadline=time.monotonic() + 2) as response:
                assert [chunk async for chunk in response.chunks()]

        with owned:
            owned.exchange(run)
            assert instances[0]._slots._value == 2
            assert not instances[0]._responses
        assert base.sent_bytes == 1024 * 1024
        assert base.sent_sha256 is None


def test_empty_source_still_has_verified_eof_before_accepting_response(tmp_path, certificates):
    key = credential()
    with TlsServer(certificates, {"/bucket/object" + SIGNED_QUERY: Reply()}) as server:
        owned, _, _ = session(key, certificates, {"storage.localhost": server})
        body = source(tmp_path, b"")
        with owned:
            result = owned.exchange(lambda transport: put(transport, direct(body, key)))
        assert result[1:] == (0, hashlib.sha256(b"").hexdigest())
        assert body.complete
        assert server.requests[0].body == b""


def test_source_change_has_no_confirm_or_automatic_retry(tmp_path, certificates, monkeypatch):
    from yorunge.adapters import storage_source

    key = credential()
    payload = b"a" * (2 * 1024 * 1024 + 3)
    body = source(tmp_path, payload)
    original = storage_source.os.read
    changed = False

    def edit_after_first_read(descriptor, size):
        nonlocal changed
        value = original(descriptor, size)
        if descriptor == body._file_fd and not changed:
            changed = True
            with (tmp_path / "data/fixture.bin").open("r+b") as file:
                file.seek(1024 * 1024)
                file.write(b"b")
        return value

    monkeypatch.setattr(storage_source.os, "read", edit_after_first_read)
    with TlsServer(certificates, {"/bucket/object" + SIGNED_QUERY: Reply()}) as server:
        owned, network, _ = session(key, certificates, {"storage.localhost": server})
        rejected_call = partial(owned.exchange, lambda transport: put(transport, direct(body, key)))
        with owned, pytest.raises(YorungeError) as failure:
            rejected_call()
        assert failure.value.code == "input_changed"
        assert body._file_fd is None
        assert not body.complete
        assert len(network.connections) == 1
        assert all(r.method == "PUT" for r in server.requests)


@pytest.mark.parametrize("operation", ["service", "storage"])
@pytest.mark.parametrize("addresses", [("127.0.0.1",), ("8.8.8.8", "10.0.0.1")])
def test_production_address_policy_applies_to_both_request_types(tmp_path, operation, addresses):
    calls = []

    async def resolver(host, port, timeout):
        calls.append((host, port))
        return addresses

    key, body = credential(), source(tmp_path)
    guarded = GuardedBackend(resolver=resolver)

    def factory():
        return TransferHttpxTransport(
            key,
            transport=GuardedHttpTransport(backend=guarded),
            storage_origins=("https://storage.localhost",),
            utc_clock=lambda: NOW,
        )

    async def run(transport):
        if operation == "storage":
            return await put(transport, direct(body, key))
        request = HttpRequest(
            API, "GET", "check", credential=key, read_only=True, service_id="evren-platform"
        )
        async with transport.open(request, deadline=time.monotonic() + 2):
            pytest.fail("private DNS reached an HTTP response")

    with (
        TransferSession(
            key, transport_factory=factory, storage_origins=("https://storage.localhost",)
        ) as owned,
        pytest.raises(YorungeError) as failure,
    ):
        owned.exchange(run)
    assert failure.value.code == "invalid_service_target"
    assert len(calls) == 1
    assert calls[0][1] == 443
    assert body.sent_bytes == 0
    assert body._file_fd is None


@pytest.mark.parametrize("operation", ["service", "storage"])
def test_untrusted_certificate_never_sends_http_or_source_bytes(tmp_path, certificates, operation):
    key, body = credential(), source(tmp_path)
    with TlsServer(certificates, {}) as server:
        network = FixtureNetwork({"api.localhost": server, "storage.localhost": server})

        def factory():
            return TransferHttpxTransport(
                key,
                transport=GuardedHttpTransport(backend=network),  # Real public CA store.
                storage_origins=("https://storage.localhost",),
                utc_clock=lambda: NOW,
            )

        async def run(transport):
            if operation == "storage":
                return await put(transport, direct(body, key))
            request = HttpRequest(
                API, "GET", "check", credential=key, read_only=True, service_id="evren-platform"
            )
            async with transport.open(request, deadline=time.monotonic() + 3):
                pytest.fail("untrusted certificate accepted")

        with (
            TransferSession(
                key, transport_factory=factory, storage_origins=("https://storage.localhost",)
            ) as owned,
            pytest.raises(YorungeError) as failure,
        ):
            owned.exchange(run)
        assert failure.value.code == "transport_failed"
        assert failure.value.__cause__ is failure.value.__context__ is None
        assert len(network.connections) == 1
        assert not server.requests
        assert body.sent_bytes == 0
        assert body._file_fd is None


def test_mutated_source_metadata_cannot_change_prepared_content_length(tmp_path, certificates):
    key, base = credential(), source(tmp_path)

    class MutableMetadata:
        size, sha256 = base.size, base.sha256

        def __getattr__(self, name):
            return getattr(base, name)

    wrapped = MutableMetadata()
    request = direct(wrapped, key)
    wrapped.size += 1
    with TlsServer(certificates, {}) as server:
        owned, network, _ = session(key, certificates, {"storage.localhost": server})
        rejected_call = partial(owned.exchange, lambda transport: put(transport, request))
        with owned, pytest.raises(YorungeError) as failure:
            rejected_call()
        assert failure.value.code == "input_changed"
        assert dict(request.public_headers())["Content-Length"] == str(base.size)
        assert not network.connections
        assert not server.requests
        assert base.sent_bytes == 0


def test_shortened_expiry_window_interrupts_body_instead_of_waiting_for_context_exit(
    tmp_path, certificates
):
    key, consumed = credential(), []
    ticks = iter((NOW, NOW + timedelta(seconds=54.8)))
    path = "/bucket/object" + SIGNED_QUERY
    with TlsServer(
        certificates, {path: Reply(body=b"x" * 80, chunk_size=1, chunk_delay=0.01)}
    ) as server:
        owned, _, instances = session(
            key, certificates, {"storage.localhost": server}, clock=lambda: next(ticks)
        )
        body = source(tmp_path)

        async def run(transport):
            async with transport.open_storage(
                direct(body, key), deadline=time.monotonic() + 3
            ) as response:
                async for chunk in response.chunks():
                    consumed.append(chunk)

        with owned, pytest.raises(YorungeError) as failure:
            owned.exchange(run)
        assert failure.value.code == "transport_timeout"
        # The old timer read all 80 bytes, then rejected only on context exit.
        assert len(b"".join(consumed)) < 80
        assert instances[0]._slots._value == 2
        assert not instances[0]._responses
        assert body._file_fd is None
        assert len(server.requests) == 1
