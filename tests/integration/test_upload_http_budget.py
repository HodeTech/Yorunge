"""Real loopback TLS attempts, body counters and same-pool upload cleanup."""

import asyncio
import hashlib
import logging
import os
import socket
import time
from datetime import UTC, datetime, timedelta

import httpcore
import httpx
import pytest

from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from yorunge.adapters.guarded_http import GuardedHttpTransport
from yorunge.adapters.guarded_network import GuardedBackend
from yorunge.adapters.storage_source import DescriptorByteSource
from yorunge.adapters.upload_http import UploadHttpxTransport, UploadSession
from yorunge.adapters.upload_wire_meter import CURRENT_CALL, MeteredWireTransport, WireCall
from yorunge.application.http_transport import HttpCredential, HttpRequest
from yorunge.application.operations import DispatchPermit
from yorunge.application.storage import StorageRequest, StorageTarget
from yorunge.application.upload_budget import UploadBudget
from yorunge.domain.capabilities import timestamp
from yorunge.domain.credentials import SecretValue, normalize_target
from yorunge.domain.dataset_manifest import DatasetFile
from yorunge.domain.dataset_upload import UploadRoot
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_costs import UploadRequestLimits

CONNECT, CONNECT_EX, GETADDRINFO = (
    socket.socket.connect,
    socket.socket.connect_ex,
    socket.getaddrinfo,
)
API = normalize_target("https://api.ssyz.org.tr/api/v1")
ID = "11111111-1111-4111-8111-111111111111"
PREFIX = f"/api/v1/datasets/{ID}/upload/"
SECRET = "private-budgeted-key-canary-718252"
MIB = 1_048_576


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(
        tmp_path_factory.mktemp("upload-budget-tls"),
        names=("localhost", "api.ssyz.org.tr", "storage.localhost"),
    )


@pytest.fixture(autouse=True)
def loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


def budget(*, readonly=False, size=1_073_741_824, seconds=60):
    values = UploadRequestLimits(
        max_create=1,
        max_project_link=1,
        max_presign=128,
        max_put=128,
        max_confirm=128,
        max_read_requests=512,
        max_read_attempts=1024,
        max_control_request_bytes=4 * MIB,
        max_control_response_bytes=16 * MIB,
        max_upload_bytes=size,
    )
    return UploadBudget(values, end=time.monotonic() + seconds, read_only=readonly)


def credential():
    return HttpCredential("X-API-Key", SecretValue(SECRET), target=API, service_id="evren-platform")


def request(key, *, effect=False, body=b"", maximum=MIB):
    return HttpRequest(
        API,
        "POST" if effect else "GET",
        "datasets" if effect else "auth/me",
        content=body,
        credential=key,
        service_id="evren-platform",
        read_only=not effect,
        upload_endpoint="create" if effect else "me",
        max_bytes=maximum,
    )


def claim(value, wanted):
    return value.reserve(
        "create" if wanted.method == "POST" else "read",
        request_bytes=len(wanted.content),
        response_bytes=wanted.max_bytes,
    )


def session(server, key, value, *, storage_server=None, origins=()):
    instances = []
    routes = {"api.ssyz.org.tr": server}
    if storage_server is not None:
        routes["storage.localhost"] = storage_server

    class FixtureNetwork(GuardedBackend):
        # Test-only mapping: the production public-IP policy is unchanged.
        def __init__(self):
            async def resolver(host, port, timeout):
                assert host in routes and port == 443
                return ("127.0.0.1",)

            super().__init__(resolver=resolver, allowed=lambda address: address == "127.0.0.1")

        async def _connect(self, pinned, port, timeout, options, original_host):
            assert pinned == "127.0.0.1" and port == 443
            return await httpcore.AnyIOBackend().connect_tcp(
                pinned, routes[original_host].port, timeout=timeout, socket_options=options
            )

    def factory():
        low = GuardedHttpTransport(backend=FixtureNetwork(), verify=server.client_context())
        instance = UploadHttpxTransport(key, value, transport=low, storage_origins=origins)
        instances.append(instance)
        return instance

    return UploadSession(key, value, transport_factory=factory, storage_origins=origins), instances


async def get(client, wanted, reserved, *, permit=None, deadline=None):
    async with client.open_budgeted(
        wanted,
        reserved,
        deadline=time.monotonic() + 3 if deadline is None else deadline,
        permit=permit,
    ) as response:
        return b"".join([part async for part in response.chunks()])


def source(tmp_path, name, data):
    root = tmp_path / "root"
    root.mkdir(exist_ok=True)
    path = root / name
    path.write_bytes(data)
    info = root.stat()
    return DescriptorByteSource(
        UploadRoot(anchor=str(root.resolve()), device=info.st_dev, inode=info.st_ino),
        DatasetFile(path=name, size=len(data), sha256=hashlib.sha256(data).hexdigest()),
        deadline=time.monotonic() + 30,
    )


def storage(key, body, suffix="sample"):
    target = StorageTarget(
        API.service_origin + PREFIX + "put?key=objects%2F" + suffix,
        mode="proxy",
        origin=API.service_origin,
        prefix=PREFIX,
        expires_at=None,
        service=API,
        dataset_id=ID,
        literal_policy="platform_proxy_v2",
    )
    return StorageRequest(target, body, key.secret, "application/octet-stream", credential=key)


async def put(client, wanted, reserved, permit):
    async with client.open_storage_budgeted(
        wanted, reserved, deadline=time.monotonic() + 3, permit=permit
    ) as response:
        result = b"".join([part async for part in response.chunks()])
        return result, response.sent_bytes, response.sent_sha256


def test_real_read_retry_and_post_single_attempt_share_one_client_pool(certificates, caplog):
    value, key = budget(), credential()

    def transient(record, count):
        return (
            Reply(status=503, body=b"discarded-transient")
            if count == 1
            else Reply(body=b'{"accepted":true}')
        )

    with TlsServer(
        certificates,
        {
            "/api/v1/auth/me": transient,
            "/api/v1/datasets": Reply(status=503, body=b"private-error-canary"),
        },
    ) as server:
        owned, instances = session(server, key, value)
        wanted = request(key)
        with caplog.at_level(logging.DEBUG), owned:
            assert (
                owned.exchange(lambda client: get(client, wanted, claim(value, wanted)))
                == b'{"accepted":true}'
            )
            effect = request(key, effect=True, body=b'{"private":true}')
            permit = DispatchPermit(os.getpid)
            with pytest.raises(YorungeError) as error:
                owned.exchange(
                    lambda client: get(client, effect, claim(value, effect), permit=permit)
                )
            assert error.value.code == "remote_failed"
            assert len(instances) == 1 and not instances[0]._responses
            assert instances[0]._slots._value == 2
        assert [record.method for record in server.requests] == ["GET", "GET", "POST"]
        assert server.requests[-1].body == effect.content
        # Closing the unread transient body may discard its socket; the final
        # GET and the later exchange still reuse the same owned pool/socket.
        assert server.requests[1].connection == server.requests[2].connection
    counts = value.snapshot()
    assert counts.read_requests == 1 and counts.read_attempts == 2
    assert counts.create_requests == counts.effect_attempts == 1
    assert counts.control_request_bytes == len(effect.content)
    assert counts.response_bytes == len(b'{"accepted":true}')
    assert counts.response_pending == 0
    assert all(text not in caplog.text for text in (SECRET, "private-error-canary", "/api/v1"))


@pytest.mark.parametrize("size", [0, 33, MIB + 7])
def test_real_proxy_put_counters_match_server_and_descriptor_eof(tmp_path, certificates, size):
    value, key = budget(size=size), credential()
    data = b"x" * size
    body = source(tmp_path, "file.bin", data)
    wanted = storage(key, body)
    path = PREFIX + "put?key=objects%2Fsample"
    with TlsServer(certificates, {path: Reply(body=b"{}")}) as server:
        owned, instances = session(server, key, value)
        with owned:
            reserved = value.reserve("put", upload_bytes=size, response_bytes=65_536)
            result = owned.exchange(
                lambda client: put(client, wanted, reserved, DispatchPermit(os.getpid))
            )
            assert instances[0]._slots._value == 2 and not instances[0]._responses
        assert len(server.requests) == 1 and server.requests[0].body == data
        assert server.requests[0].header("Content-Length") == str(size)
    assert result == (b"{}", size, hashlib.sha256(data).hexdigest())
    assert body.complete and body._file_fd is None and body._root_fd is None
    counts = value.snapshot()
    assert counts.upload_reserved == counts.upload_bytes == size
    assert counts.effect_attempts == counts.put_requests == 1
    assert counts.response_bytes == 2 and counts.response_pending == 0


@pytest.mark.parametrize(
    "fault",
    [
        "kind",
        "body",
        "response",
        "foreign",
        "no_permit",
        "read_permit",
        "unregistered",
        "unmetered",
    ],
)
def test_wrong_reservation_or_entrypoint_has_zero_socket_attempt(certificates, fault):
    value, key = budget(), credential()
    effect = fault in {"body", "no_permit"}
    wanted = request(key, effect=effect, body=b"{}" if effect else b"")
    reserved = claim(value, wanted)
    permit = DispatchPermit(os.getpid) if effect or fault == "read_permit" else None
    if fault == "kind":
        reserved.finish()
        reserved = value.reserve("create", response_bytes=MIB)
    elif fault == "body":
        reserved.finish()
        reserved = value.reserve("create", request_bytes=1, response_bytes=MIB)
    elif fault == "response":
        reserved.finish()
        reserved = value.reserve("read", response_bytes=1)
    elif fault == "foreign":
        reserved.finish()
        reserved = claim(budget(), wanted)
    elif fault == "no_permit":
        permit = None
    elif fault == "unregistered":
        wanted = HttpRequest(
            API, "GET", "auth/me", credential=key, service_id="evren-platform", read_only=True
        )
    with TlsServer(certificates, {}) as server:
        owned, _ = session(server, key, value)

        async def run(client):
            if fault == "unmetered":
                async with client.open(wanted, deadline=time.monotonic() + 3):
                    pytest.fail("unmetered path must not reach HTTP")
            else:
                await get(client, wanted, reserved, permit=permit)

        with owned, pytest.raises(YorungeError) as error:
            owned.exchange(run)
        assert error.value.code == "invalid_request"
        assert server.requests == []
    reserved.finish()
    assert value.snapshot().read_attempts == value.snapshot().effect_attempts == 0


@pytest.mark.parametrize("deadline", [True, float("nan"), float("inf"), "bad"])
def test_invalid_deadline_cannot_hide_behind_budget_minimum(certificates, deadline):
    value, key = budget(), credential()
    wanted = request(key)
    reserved = claim(value, wanted)
    with TlsServer(certificates, {}) as server:
        owned, _ = session(server, key, value)
        with owned, pytest.raises(YorungeError) as error:
            owned.exchange(lambda client: get(client, wanted, reserved, deadline=deadline))
        assert error.value.code == "invalid_request"
        assert server.requests == []
    assert value.snapshot().read_requests == value.snapshot().response_pending == 0


def test_real_response_overflow_releases_capacity_without_refunding_request(certificates):
    value, key = budget(), credential()
    wanted = request(key, maximum=3)
    with TlsServer(certificates, {"/api/v1/auth/me": Reply(body=b"four")}) as server:
        owned, instances = session(server, key, value)
        with owned, pytest.raises(YorungeError) as error:
            owned.exchange(lambda client: get(client, wanted, claim(value, wanted)))
        assert error.value.code == "invalid_response"
        assert instances[0]._slots._value == 2 and not instances[0]._responses
        assert len(server.requests) == 1
    assert value.snapshot().read_requests == value.snapshot().read_attempts == 1
    assert value.snapshot().response_pending == value.snapshot().response_bytes == 0


def test_real_early_close_counts_delivered_raw_bytes_and_session_can_continue(certificates):
    value, key = budget(), credential()
    with TlsServer(
        certificates,
        {"/api/v1/auth/me": Reply(body=b"a" * 65_536, chunk_size=32_768, chunk_delay=0.02)},
    ) as server:
        owned, instances = session(server, key, value)

        async def run(client):
            wanted = request(key)
            async with client.open_budgeted(
                wanted, claim(value, wanted), deadline=time.monotonic() + 3
            ) as response:
                first = await anext(response.chunks())
            assert value.snapshot().response_pending == 0
            assert CURRENT_CALL.get() is None
            assert instances[0]._slots._value == 2
            return len(first)

        with owned:
            delivered = owned.exchange(run)
        assert 0 < delivered <= 32_768
    assert delivered <= value.snapshot().response_bytes <= 65_536
    assert value.snapshot().read_attempts == 1


def test_real_two_put_workers_share_budget_and_pool(tmp_path, certificates):
    data = b"simultaneous" * 4096
    value, key = budget(size=2 * len(data)), credential()
    bodies = [source(tmp_path, f"file-{i}.bin", data) for i in range(2)]
    wanted = [storage(key, body, f"sample{i}") for i, body in enumerate(bodies)]
    paths = {PREFIX + f"put?key=objects%2Fsample{i}": Reply(body=b"{}") for i in range(2)}
    with TlsServer(certificates, paths) as server:
        owned, instances = session(server, key, value)

        async def run(client):
            reservations = [
                value.reserve("put", upload_bytes=len(data), response_bytes=65_536)
                for _ in range(2)
            ]
            return await asyncio.gather(
                *(
                    put(client, item, reserved, DispatchPermit(os.getpid))
                    for item, reserved in zip(wanted, reservations, strict=True)
                )
            )

        with owned:
            results = owned.exchange(run)
            assert len(instances) == 1 and instances[0]._slots._value == 2
        assert len(server.requests) == 2
        assert all(record.body == data for record in server.requests)
    assert all(result[1] == len(data) for result in results)
    assert value.snapshot().upload_bytes == value.snapshot().upload_reserved == 2 * len(data)
    assert value.snapshot().response_bytes == 4 and value.snapshot().response_pending == 0


def test_cancel_mid_source_keeps_partial_count_and_closes_same_task(tmp_path, certificates):
    value, key = budget(), credential()
    base = source(tmp_path, "cancel.bin", b"x" * (2 * MIB))
    with TlsServer(
        certificates,
        {PREFIX + "put?key=objects%2Fsample": Reply(), "/api/v1/auth/me": Reply(body=b"{}")},
    ) as server:
        owned, instances = session(server, key, value)

        async def run(client):
            ready, gate = asyncio.Event(), asyncio.Event()

            class Paused:
                def __getattr__(self, name):
                    return getattr(base, name)

                def chunks(self):
                    base.chunks()
                    return self

                def __aiter__(self):
                    return self

                async def __anext__(self):
                    if base.sent_bytes:
                        ready.set()
                        await gate.wait()
                    return await anext(base)

                async def aclose(self):
                    await base.aclose()

            wanted = storage(key, Paused())
            reserved = value.reserve("put", upload_bytes=base.size, response_bytes=65_536)
            task = asyncio.create_task(put(client, wanted, reserved, DispatchPermit(os.getpid)))
            await asyncio.wait_for(ready.wait(), 2)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert CURRENT_CALL.get() is None
            assert value.snapshot().upload_bytes == MIB
            assert value.snapshot().response_pending == 0
            assert base._file_fd is None and not base.complete
            wanted = request(key)
            assert await get(client, wanted, claim(value, wanted)) == b"{}"
            assert instances[0]._slots._value == 2 and not instances[0]._responses

        with owned:
            owned.exchange(run)
    assert value.snapshot().effect_attempts == value.snapshot().put_requests == 1


@pytest.mark.parametrize("change", ["url", "method", "body", "headers", "child_task"])
def test_lowlevel_call_context_is_not_a_reusable_bypass(change):
    value, key = budget(), credential()
    wanted = request(key)
    reserved = claim(value, wanted)
    delegated = []

    async def handler(wire):
        delegated.append(wire)
        return httpx.Response(200, content=b"{}")

    async def run():
        reserved.begin()
        call = WireCall(wanted, reserved, None)
        token = CURRENT_CALL.set(call)
        try:
            low = MeteredWireTransport(httpx.MockTransport(handler), value)
            wire = httpx.Request("GET", wanted.url, headers=wanted.wire_headers(), content=b"")
            if change == "url":
                wire.url = httpx.URL(wanted.url + "/other")
            elif change == "method":
                wire.method = "POST"
            elif change == "body":
                wire = httpx.Request("GET", wanted.url, headers=wanted.wire_headers(), content=b"x")
            elif change == "headers":
                wire.headers["X-API-Key"] = "another-key"
            with pytest.raises(YorungeError) as error:
                if change == "child_task":
                    await asyncio.create_task(low.handle_async_request(wire))
                else:
                    await low.handle_async_request(wire)
            assert error.value.code == "invalid_request"
        finally:
            CURRENT_CALL.reset(token)
            reserved.finish()

    asyncio.run(run())
    assert delegated == []
    assert value.snapshot().read_attempts == 0


@pytest.mark.parametrize("fault", ["compressed", "timeout", "truncated"])
def test_raw_response_faults_preserve_attempt_and_cleanup(certificates, fault):
    value, key = budget(), credential()
    replies = {
        "compressed": Reply(
            body=b"compressed-not-decoded", headers=(("Content-Encoding", "gzip"),)
        ),
        "timeout": Reply(body=b"{}", header_delay=0.15),
        "truncated": Reply(body=b"abcdef", truncate_at=3),
    }
    with TlsServer(certificates, {"/api/v1/auth/me": replies[fault]}) as server:
        owned, instances = session(server, key, value)
        wanted = request(key)
        with owned, pytest.raises(YorungeError) as failure:
            owned.exchange(
                lambda client: get(
                    client,
                    wanted,
                    claim(value, wanted),
                    deadline=time.monotonic() + (0.05 if fault == "timeout" else 3),
                )
            )
        expected = {
            "compressed": "invalid_response",
            "timeout": "transport_timeout",
            "truncated": "transport_failed",
        }
        assert failure.value.code == expected[fault]
        assert instances[0]._slots._value == 2 and not instances[0]._responses
        assert len(server.requests) == 1
    assert value.snapshot().read_requests == value.snapshot().read_attempts == 1
    assert value.snapshot().response_pending == 0
    assert value.snapshot().response_bytes <= (3 if fault == "truncated" else 0)


@pytest.mark.parametrize("fault", ["denied", "limited", "failed"])
def test_real_put_failure_has_one_attempt_no_replay_and_closes_source(
    tmp_path, certificates, fault
):
    value, key = budget(), credential()
    base = source(tmp_path, "failed.bin", b"small-upload")
    wanted = storage(key, base)
    statuses = {"denied": 403, "limited": 429, "failed": 503}
    path = PREFIX + "put?key=objects%2Fsample"
    with TlsServer(
        certificates, {path: Reply(status=statuses[fault], body=b"private-storage-error")}
    ) as server:
        owned, instances = session(server, key, value)
        reserved = value.reserve("put", upload_bytes=base.size, response_bytes=65_536)
        with owned, pytest.raises(YorungeError) as failure:
            owned.exchange(lambda client: put(client, wanted, reserved, DispatchPermit(os.getpid)))
        assert (
            failure.value.code
            == {
                "denied": "remote_access_denied",
                "limited": "remote_rate_limited",
                "failed": "remote_failed",
            }[fault]
        )
        assert len(server.requests) == 1 and server.requests[0].body == b"small-upload"
        assert instances[0]._slots._value == 2 and not instances[0]._responses
    assert base._file_fd is None and base._root_fd is None
    assert value.snapshot().upload_bytes == base.size
    assert value.snapshot().put_requests == value.snapshot().effect_attempts == 1
    assert value.snapshot().response_bytes == value.snapshot().response_pending == 0


def test_reused_dispatch_permit_cannot_open_a_second_effect(certificates):
    value, key, permit = budget(), credential(), DispatchPermit(os.getpid)
    with TlsServer(certificates, {"/api/v1/datasets": Reply(body=b"{}")}) as server:
        owned, _ = session(server, key, value)

        async def run(client):
            first = request(key, effect=True, body=b"{}")
            assert await get(client, first, claim(value, first), permit=permit) == b"{}"
            second = HttpRequest(
                API,
                "POST",
                f"datasets/{ID}/upload/presign",
                credential=key,
                service_id="evren-platform",
                content=b"{}",
                upload_endpoint="presign",
            )
            reserved = value.reserve("presign", request_bytes=2, response_bytes=MIB)
            with pytest.raises(YorungeError) as failure:
                await get(client, second, reserved, permit=permit)
            assert failure.value.code == "operation_conflict"

        with owned:
            owned.exchange(run)
        assert len(server.requests) == 1
    assert value.snapshot().effect_attempts == 1
    assert value.snapshot().presign_requests == value.snapshot().response_pending == 0


def test_storage_preflight_rejection_closes_lazy_source_without_socket(tmp_path, certificates):
    value, key = budget(), credential()
    base = source(tmp_path, "rejected.bin", b"private")
    wanted = storage(key, base)
    reserved = value.reserve("put", upload_bytes=base.size - 1, response_bytes=65_536)
    with TlsServer(certificates, {}) as server:
        owned, _ = session(server, key, value)
        with owned, pytest.raises(YorungeError) as failure:
            owned.exchange(lambda client: put(client, wanted, reserved, DispatchPermit(os.getpid)))
        assert failure.value.code == "invalid_request" and server.requests == []
    assert base._closed and base._file_fd is None
    reserved.finish()
    assert value.snapshot().put_requests == value.snapshot().effect_attempts == 0


@pytest.mark.parametrize("effect", [False, True])
def test_connect_failure_counts_physical_attempts_and_erases_private_exception(effect):
    value, key = budget(), credential()
    wanted = request(key, effect=effect, body=b"{}" if effect else b"")
    calls = []

    async def handler(wire):
        calls.append((wire.method, len(wire.content)))
        raise httpx.ConnectError("PRIVATE-CONNECT-EXCEPTION-CANARY", request=wire)

    async def run():
        async with UploadHttpxTransport(
            key, value, transport=httpx.MockTransport(handler)
        ) as client:
            with pytest.raises(YorungeError) as failure:
                await get(
                    client,
                    wanted,
                    claim(value, wanted),
                    permit=DispatchPermit(os.getpid) if effect else None,
                )
            assert failure.value.code == "transport_failed"
            assert failure.value.__context__ is None and failure.value.__cause__ is None
            assert "PRIVATE-CONNECT-EXCEPTION-CANARY" not in str(failure.value.envelope())

    asyncio.run(run())
    assert len(calls) == (1 if effect else 2)
    assert value.snapshot().response_pending == 0
    assert value.snapshot().effect_attempts == (1 if effect else 0)
    assert value.snapshot().read_attempts == (0 if effect else 2)


@pytest.mark.parametrize("effect", [False, True])
def test_lowlevel_cannot_borrow_another_budget_or_omit_effect_permit(effect):
    value, key = budget(), credential()
    wanted = request(key, effect=effect, body=b"{}" if effect else b"")
    reserved = claim(value, wanted)
    delegated = []

    async def handler(wire):
        delegated.append(wire)
        return httpx.Response(200, content=b"{}")

    async def run():
        reserved.begin()
        token = CURRENT_CALL.set(WireCall(wanted, reserved, None))
        try:
            low = MeteredWireTransport(httpx.MockTransport(handler), value if effect else budget())
            wire = httpx.Request(
                wanted.method, wanted.url, headers=wanted.wire_headers(), content=wanted.content
            )
            with pytest.raises(YorungeError) as captured:
                await low.handle_async_request(wire)
            assert captured.value.code == "invalid_request"
        finally:
            CURRENT_CALL.reset(token)
            reserved.finish()

    asyncio.run(run())
    assert delegated == []
    assert value.snapshot().effect_attempts == value.snapshot().read_attempts == 0


def test_nested_unmetered_entrypoints_cannot_borrow_active_read_claim(certificates):
    value, key = budget(), credential()
    wanted = request(key)
    with TlsServer(certificates, {"/api/v1/auth/me": Reply(body=b"{}")}) as server:
        owned, _ = session(server, key, value)

        async def run(client):
            async with client.open_budgeted(
                wanted, claim(value, wanted), deadline=time.monotonic() + 3
            ) as response:
                with pytest.raises(YorungeError) as failure:
                    client.open(wanted, deadline=time.monotonic() + 3)
                assert failure.value.code == "invalid_request"
                with pytest.raises(YorungeError) as failure:
                    client.open_storage(None, deadline=time.monotonic() + 3)
                assert failure.value.code == "invalid_request"
                return b"".join([part async for part in response.chunks()])

        with owned:
            assert owned.exchange(run) == b"{}"
        assert len(server.requests) == 1
    assert value.snapshot().read_requests == value.snapshot().read_attempts == 1


def test_real_wire_stream_mutation_is_rejected_before_permit_and_socket(certificates, monkeypatch):
    from yorunge.adapters.http_transport import HttpxTransport

    value, key, permit = budget(), credential(), DispatchPermit(os.getpid)
    wanted = request(key, effect=True, body=b"{}")
    original = HttpxTransport._wire_request

    def changed(wanted, deadline):
        wire = original(wanted, deadline)
        assert wire.content == b"{}"
        wire.stream = httpx.ByteStream(b"XX")
        assert wire.content == b"{}"  # Cached content is not the physical stream.
        return wire

    monkeypatch.setattr(UploadHttpxTransport, "_wire_request", staticmethod(changed))
    with TlsServer(certificates, {}) as server:
        owned, _ = session(server, key, value)
        with owned, pytest.raises(YorungeError) as failure:
            owned.exchange(lambda client: get(client, wanted, claim(value, wanted), permit=permit))
        assert failure.value.code == "invalid_request" and server.requests == []
    assert value.snapshot().effect_attempts == value.snapshot().create_requests == 0
    permit.consume()  # Guard failure did not consume the effect capability.


@pytest.mark.parametrize("entered", [False, True])
def test_not_entered_or_closed_storage_client_still_closes_source(tmp_path, entered):
    value, key = budget(), credential()
    base = source(tmp_path, "before-enter.bin", b"source")
    wanted = storage(key, base)
    reserved = value.reserve("put", upload_bytes=base.size, response_bytes=65_536)

    async def run():
        client = UploadHttpxTransport(
            key, value, transport=httpx.MockTransport(lambda request: httpx.Response(200))
        )
        if entered:
            async with client:
                pass
        with pytest.raises(YorungeError) as failure:
            await put(client, wanted, reserved, DispatchPermit(os.getpid))
        assert failure.value.code == "invalid_request"

    asyncio.run(run())
    assert base._closed and base._file_fd is None
    assert value.snapshot().effect_attempts == value.snapshot().put_requests == 0
    assert value.snapshot().response_pending == 0


@pytest.mark.parametrize("storage_call", [False, True])
@pytest.mark.parametrize("total_first", [False, True])
def test_total_budget_and_shorter_network_deadline_have_distinct_safe_errors(
    tmp_path, storage_call, total_first
):
    key = credential()
    base = source(tmp_path, "timeout.bin", b"source") if storage_call else None
    value = budget(seconds=0.05 if total_first else 2)
    wanted = storage(key, base) if storage_call else request(key)
    reserved = (
        value.reserve("put", upload_bytes=base.size, response_bytes=65_536)
        if storage_call
        else claim(value, wanted)
    )

    async def handler(wire):
        await asyncio.sleep(0.2)
        return httpx.Response(200, content=b"{}")

    async def run():
        async with UploadHttpxTransport(
            key, value, transport=httpx.MockTransport(handler)
        ) as client:
            deadline = time.monotonic() + (1 if total_first else 0.05)
            with pytest.raises(YorungeError) as failure:
                if storage_call:
                    async with client.open_storage_budgeted(
                        wanted, reserved, deadline=deadline, permit=DispatchPermit(os.getpid)
                    ):
                        pytest.fail("deadline must interrupt response")
                else:
                    await get(client, wanted, reserved, deadline=deadline)
            assert failure.value.code == (
                "execution_timeout" if total_first else "transport_timeout"
            )
            assert failure.value.exit_code == (2 if total_first else 1)
            assert failure.value.__context__ is None and failure.value.__cause__ is None

    asyncio.run(run())
    assert value.snapshot().response_pending == 0
    if storage_call:
        assert base._closed and base._file_fd is None
        assert value.snapshot().effect_attempts == 1
    else:
        assert value.snapshot().read_attempts == 1


@pytest.mark.parametrize("selected", [False, True])
def test_direct_storage_keeps_explicit_origin_policy_and_no_credentials(
    tmp_path, certificates, selected
):
    value, key = budget(), credential()
    base = source(tmp_path, "direct.bin", b"direct-source")
    target = StorageTarget(
        "https://storage.localhost/bucket/object?signature=SIGNED-PRIVATE-CANARY%2Fpart",
        mode="direct",
        origin="https://storage.localhost",
        prefix="/bucket/",
        expires_at=timestamp(datetime.now(UTC) + timedelta(seconds=60)),
        service=None,
        dataset_id=None,
    )
    wanted = StorageRequest(target, base, key.secret, "application/octet-stream")
    path = "/bucket/object?signature=SIGNED-PRIVATE-CANARY%2Fpart"
    with (
        TlsServer(certificates, {"/api/v1/auth/me": Reply(body=b"{}")}) as api,
        TlsServer(certificates, {path: Reply(body=b"{}")}) as remote,
    ):
        origins = ("https://storage.localhost",) if selected else ()
        owned, instances = session(api, key, value, storage_server=remote, origins=origins)
        reserved = value.reserve("put", upload_bytes=base.size, response_bytes=65_536)
        with owned:
            if selected:
                result = owned.exchange(
                    lambda client: put(client, wanted, reserved, DispatchPermit(os.getpid))
                )
                assert result[1] == base.size
                control = request(key)
                assert (
                    owned.exchange(lambda client: get(client, control, claim(value, control)))
                    == b"{}"
                )
            else:
                with pytest.raises(YorungeError) as failure:
                    owned.exchange(
                        lambda client: put(client, wanted, reserved, DispatchPermit(os.getpid))
                    )
                assert failure.value.code == "invalid_service_target"
            assert len(instances) == 1 and instances[0]._slots._value == 2
        assert len(remote.requests) == int(selected)
        if selected:
            assert remote.requests[0].body == b"direct-source"
            assert remote.requests[0].header("X-API-Key") is None
            assert remote.requests[0].header("Authorization") is None
            assert remote.requests[0].header("Cookie") is None
            assert api.requests[0].header("X-API-Key") == SECRET
    assert base._closed and value.snapshot().response_pending == 0
