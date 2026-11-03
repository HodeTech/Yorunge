"""Real TLS descriptor PUT and bounded exact metadata; no provider account."""

import asyncio
import hashlib
import json
import logging
import socket
import time
from dataclasses import replace
from uuid import uuid4

import pytest

from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from tests.integration.test_platform_upload_port import presign_response, setup
from tests.integration.test_upload_http_budget import session
from tests.integration.test_upload_journal import DATASET, seal
from tests.integration.test_upload_journal import journal as journal
from yorunge.adapters import storage_source
from yorunge.adapters.dataset_files import open_dataset
from yorunge.adapters.state import open_store
from yorunge.application.datasets import DatasetBudget
from yorunge.application.upload_descriptors import distinct_uploads, presigned
from yorunge.domain.capabilities import timestamp
from yorunge.domain.credentials import SecretValue
from yorunge.domain.dataset_transfer import StageReceipt
from yorunge.domain.dataset_upload import manifest_reference
from yorunge.domain.errors import YorungeError

CONNECT, CONNECT_EX, GETADDRINFO = (
    socket.socket.connect,
    socket.socket.connect_ex,
    socket.getaddrinfo,
)
ITEMS = f"/api/v1/datasets/{DATASET}/items?limit=128"


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(
        tmp_path_factory.mktemp("upload-data-tls"), names=("localhost", "api.ssyz.org.tr")
    )


@pytest.fixture(autouse=True)
def loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


def actual_files(journal, tmp_path, data=None):
    root = tmp_path.resolve() / "content"
    root.mkdir()
    data = data or {"a.txt": b"abc", "empty.bin": b"", "ölçüm.txt": b"hello"}
    for name, content in data.items():
        (root / name).write_bytes(content)
    body = journal.plan.model_dump(mode="json")
    with open_dataset(root, DatasetBudget()) as tree:
        journal.manifest = tree.scan()
    body["manifest"] = manifest_reference(journal.manifest).model_dump(mode="json")
    info = root.stat()
    body["root"] = {"anchor": str(root), "device": info.st_dev, "inode": info.st_ino}
    journal.plan = seal(body)
    return root, data


def prepared_uploads(journal):
    record = journal.approved()
    for kind in ("create", "project_link"):
        arm = journal.arm(record, kind)
        arm[1].consume()
        record = journal.accept(record, arm.intent).operation
    port, key, value = setup(journal)
    contexts = port.files(record.operation_id, DATASET)
    uploads = []
    for index, context in enumerate(contexts):
        raw_key = f"objects/private-provider-key-{index}"
        upload = presigned(
            json.dumps(
                presign_response(
                    context,
                    object_key=raw_key,
                    upload_url=f"/datasets/{DATASET}/upload/put?key=objects%2Fprivate-provider-key-{index}",
                )
            ).encode(),
            context,
            key.secret,
        )
        uploads.append(upload)
        arm = journal.arm(record, "presign", index)
        arm[1].consume()
        receipt = StageReceipt(
            schema_version=1,
            intent_id=arm.intent.intent_id,
            recorded_at=timestamp(journal.clock.value),
            result="accepted",
            dataset_id=DATASET,
            object_key=context.local_binding,
            sent_bytes=None,
            sent_sha256=None,
        )
        with open_store(journal.root) as store:
            record = (
                journal.repository(store)
                .receipt(record.operation_id, record.lease, receipt)
                .operation
            )
    uploads = tuple(uploads)
    distinct_uploads(uploads, contexts)
    return record, port, key, value, uploads


def test_actual_three_puts_preserve_empty_unicode_bytes_hashes_and_private_bindings(
    journal, tmp_path, certificates, caplog
):
    _, data = actual_files(journal, tmp_path)
    record, port, key, value, uploads = prepared_uploads(journal)
    paths = [
        f"/api/v1/datasets/{DATASET}/upload/put?key=objects%2Fprivate-provider-key-{i}"
        for i in range(3)
    ]
    calls = []
    with TlsServer(certificates, {path: Reply(body=b"") for path in paths}) as server:
        owned, instances = session(server, key, value)
        with caplog.at_level(logging.DEBUG), owned:
            for index, upload in enumerate(uploads):
                call = port.prepare_put(upload)
                calls.append(call)
                assert call._source._file_fd is call._source._root_fd is None
                arm = journal.arm(record, "put", index)
                outcome = owned.exchange(
                    lambda client, call=call, arm=arm: call.execute(client, arm)
                )
                assert call._source._end <= arm.deadline and call._source.complete
                assert call._source._file_fd is call._source._root_fd is None
                assert (outcome.receipt.sent_bytes, outcome.receipt.sent_sha256) == (
                    upload.context.file.size,
                    upload.context.file.sha256,
                )
                with open_store(journal.root) as store:
                    record = (
                        journal.repository(store)
                        .receipt(record.operation_id, record.lease, outcome.receipt)
                        .operation
                    )
            assert not instances[0]._responses and instances[0]._slots._value == 2
        assert [r.path for r in server.requests] == paths
        for request, upload in zip(server.requests, uploads, strict=True):
            assert request.method == "PUT" and request.body == data[upload.context.file.path]
            assert hashlib.sha256(request.body).hexdigest() == upload.context.file.sha256
            assert request.header("X-API-Key") == key.secret.reveal()
            assert upload.context.local_binding not in request.path + request.body.decode()
    assert value.snapshot().upload_bytes == sum(map(len, data.values()))
    assert value.snapshot().effect_attempts == value.snapshot().put_requests == 3
    assert value.snapshot().response_pending == 0
    assert "private-provider-key" not in caplog.text and key.secret.reveal() not in caplog.text
    with open_store(journal.root) as store:
        view = journal.repository(store).show(operation_id=record.operation_id)
        assert "private-provider-key" not in b"".join(r.encoded() for r in view.receipts).decode()
        assert store.verify().store_schema_version == 7
    assert all(call._closed for call in calls)


@pytest.mark.parametrize("failure", ["wrong_arm", "changed_file", "bad_ack", "status", "cancel"])
def test_put_failure_never_accepts_or_replays_and_closes_source(
    journal, tmp_path, certificates, failure
):
    root, _ = actual_files(journal, tmp_path)
    record, port, key, value, uploads = prepared_uploads(journal)
    call = port.prepare_put(uploads[0])
    arm = journal.arm(record, "put", 0 if failure != "wrong_arm" else 1)
    if failure == "changed_file":
        (root / "a.txt").write_bytes(b"xyz")
    reply = Reply(
        body=b'{"success":false}' if failure == "bad_ack" else b"",
        status=503 if failure == "status" else 200,
        header_delay=0.2 if failure == "cancel" else 0,
    )
    path = "/api/v1/datasets/" + DATASET + "/upload/put?key=objects%2Fprivate-provider-key-0"
    with TlsServer(certificates, {path: reply}) as server:
        owned, instances = session(server, key, value)
        with owned:
            if failure == "cancel":

                async def cancelled(client):
                    task = asyncio.create_task(call.execute(client, arm))
                    async with asyncio.timeout(2):
                        while not server.requests:
                            await asyncio.sleep(0.005)
                    task.cancel()
                    with pytest.raises(asyncio.CancelledError):
                        await task

                owned.exchange(cancelled)
            else:
                with pytest.raises(YorungeError):
                    owned.exchange(lambda client: call.execute(client, arm))
            assert not instances[0]._responses and instances[0]._slots._value == 2
        assert len(server.requests) <= int(failure != "wrong_arm")
    assert call._closed and call._source._file_fd is call._source._root_fd is None
    assert value.snapshot().effect_attempts <= 1 and value.snapshot().response_pending == 0
    with open_store(journal.root) as store:
        view = journal.repository(store).show(operation_id=record.operation_id)
        assert arm.intent.intent_id not in {r.intent_id for r in view.receipts}


def test_unused_put_source_closes_and_returns_pre_intent_quota(journal, tmp_path):
    actual_files(journal, tmp_path)
    record, port, key, value, uploads = prepared_uploads(journal)
    call = port.prepare_put(uploads[0])
    assert value.snapshot().put_requests == 1
    asyncio.run(call.aclose())
    assert value.snapshot().put_requests == value.snapshot().upload_reserved == 0
    assert call._closed and call._source._closed
    assert value.snapshot().effect_attempts == value.snapshot().response_pending == 0


def item_rows(journal):
    return [
        {
            "id": str(uuid4()),
            "dataset_id": DATASET,
            "original_filename": f.path,
            "file_size_bytes": f.size,
            "sha256_hash": f.sha256,
        }
        for f in journal.manifest.files
    ]


def page(rows, *, total=3, cursor=None):
    return Reply(
        body=json.dumps(
            {"items": rows, "total": total, "next_cursor": cursor}, ensure_ascii=False
        ).encode()
    )


def test_metadata_is_read_only_paginated_ordered_and_requires_no_source_files(
    journal, certificates, monkeypatch
):
    port, key, value = setup(journal, readonly=True)
    rows = item_rows(journal)
    cursor_path = ITEMS + "&cursor=next%2Fpage%2B%C3%B6"

    def no_source(*args, **kwargs):
        pytest.fail("read-only metadata opened a source")

    monkeypatch.setattr(storage_source, "directory_chain", no_source)
    with TlsServer(
        certificates,
        {ITEMS: page([rows[2]], cursor="next/page+ö"), cursor_path: page([rows[1], rows[0]])},
    ) as server:
        owned, instances = session(server, key, value)
        with owned:
            result = owned.exchange(
                lambda client: port.items(client, DATASET, deadline=time.monotonic() + 10)
            )
            assert not instances[0]._responses and instances[0]._slots._value == 2
        assert [r.path for r in server.requests] == [ITEMS, cursor_path]
        assert all(r.method == "GET" for r in server.requests)
    assert [r.file_index for r in result] == [0, 1, 2]
    assert [r.item_id for r in result] == [r["id"] for r in rows]
    assert [r.path_digest for r in result] == [
        hashlib.sha256(f.path.encode()).hexdigest() for f in journal.manifest.files
    ]
    assert value.snapshot().read_requests == value.snapshot().read_attempts == 2
    assert value.snapshot().effect_attempts == value.snapshot().response_pending == 0


@pytest.mark.parametrize(
    "bad",
    [
        "extra",
        "missing",
        "total",
        "duplicate_id",
        "duplicate_name",
        "null_hash",
        "wrong_hash",
        "wrong_size",
        "wrong_dataset",
        "cursor_repeat",
        "changed_total",
    ],
)
def test_metadata_mismatch_never_becomes_complete(journal, certificates, bad):
    port, key, value = setup(journal, readonly=True)
    rows = item_rows(journal)
    first, second = page(rows), None
    if bad == "extra":
        extra = {**rows[0], "id": str(uuid4()), "original_filename": "extra.txt"}
        first = page([*rows, extra], total=4)
    elif bad == "missing":
        first = page(rows[:2])
    elif bad == "total":
        first = page(rows, total=4)
    elif bad == "duplicate_id":
        rows[1]["id"] = rows[0]["id"]
        first = page(rows)
    elif bad == "duplicate_name":
        first = page([rows[0]], cursor="later")
        second = page([rows[0], rows[1]])
    elif bad == "cursor_repeat":
        first = page([], cursor="later")
        second = page([], cursor="later")
    elif bad == "changed_total":
        first = page(rows[:1], cursor="later")
        second = page(rows[1:], total=4)
    else:
        field, changed = {
            "null_hash": ("sha256_hash", None),
            "wrong_hash": ("sha256_hash", "0" * 64),
            "wrong_size": ("file_size_bytes", rows[0]["file_size_bytes"] + 1),
            "wrong_dataset": ("dataset_id", str(uuid4())),
        }[bad]
        rows[0][field] = changed
        first = page(rows)
    routes = {ITEMS: first}
    if second is not None:
        routes[ITEMS + "&cursor=later"] = second
    with TlsServer(certificates, routes) as server:
        owned, instances = session(server, key, value)
        with owned:
            with pytest.raises(YorungeError) as raised:
                owned.exchange(
                    lambda client: port.items(client, DATASET, deadline=time.monotonic() + 10)
                )
            assert raised.value.code == "invalid_response"
            assert not instances[0]._responses and instances[0]._slots._value == 2
        assert all(r.method == "GET" for r in server.requests)
    assert value.snapshot().effect_attempts == value.snapshot().response_pending == 0


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "remote_access_denied"),
        (403, "remote_access_denied"),
        (404, "invalid_response"),
        (405, "invalid_response"),
        (429, "remote_rate_limited"),
        (503, "remote_failed"),
    ],
)
def test_metadata_status_uses_mandatory_read_error_without_effect(
    journal, certificates, status, code
):
    port, key, value = setup(journal, readonly=True)
    with TlsServer(certificates, {ITEMS: Reply(status=status, body=b"private-error")}) as server:
        owned, _ = session(server, key, value)
        with owned:
            with pytest.raises(YorungeError) as raised:
                owned.exchange(
                    lambda client: port.items(client, DATASET, deadline=time.monotonic() + 5)
                )
            assert raised.value.code == code
            assert raised.value.__cause__ is raised.value.__context__ is None
        assert 1 <= len(server.requests) <= 2
    assert value.snapshot().effect_attempts == value.snapshot().response_pending == 0


def test_metadata_page_cap_stops_before_request_129(journal, certificates):
    port, key, value = setup(journal, readonly=True)
    routes = {ITEMS: page([], cursor="page-1")}
    for index in range(1, 128):
        routes[ITEMS + f"&cursor=page-{index}"] = page([], cursor=f"page-{index + 1}")
    with TlsServer(certificates, routes) as server:
        owned, instances = session(server, key, value)
        with owned:
            with pytest.raises(YorungeError) as raised:
                owned.exchange(
                    lambda client: port.items(client, DATASET, deadline=time.monotonic() + 20)
                )
            assert raised.value.code == "invalid_response"
            assert not instances[0]._responses and instances[0]._slots._value == 2
        assert len(server.requests) == 128
    assert value.snapshot().read_requests == value.snapshot().read_attempts == 128
    assert value.snapshot().effect_attempts == value.snapshot().response_pending == 0


def test_metadata_transient_retry_is_one_logical_read_and_never_a_write(journal, certificates):
    port, key, value = setup(journal, readonly=True)
    rows = item_rows(journal)

    def transient(request, count):
        return Reply(status=503, body=b"transient-private-error") if count == 1 else page(rows)

    with TlsServer(certificates, {ITEMS: transient}) as server:
        owned, _ = session(server, key, value)
        with owned:
            result = owned.exchange(
                lambda client: port.items(client, DATASET, deadline=time.monotonic() + 10)
            )
        assert len(server.requests) == 2 and len(result) == len(rows)
    assert value.snapshot().read_requests == 1 and value.snapshot().read_attempts == 2
    assert value.snapshot().effect_attempts == value.snapshot().response_pending == 0


def test_context_target_mutation_is_rejected_before_put_reservation(journal, tmp_path):
    actual_files(journal, tmp_path)
    record, port, key, value, uploads = prepared_uploads(journal)
    uploads[0].context.target.__dict__["service_origin"] = "https://other.example"
    with pytest.raises(YorungeError) as raised:
        port.prepare_put(uploads[0])
    assert raised.value.code == "invalid_request"
    assert value.snapshot().put_requests == value.snapshot().effect_attempts == 0


def test_partial_actual_put_cancel_counts_delivered_bytes_and_closes_fds(
    journal, tmp_path, certificates, monkeypatch
):
    block = 1_048_576
    actual_files(journal, tmp_path, {"a.txt": b"a" * (3 * block + 7)})
    record, port, key, value, uploads = prepared_uploads(journal)
    call = port.prepare_put(uploads[0])
    arm = journal.arm(record, "put", 0)
    original = storage_source.DescriptorByteSource.__anext__
    ready = asyncio.Event()

    async def pause_second_chunk(source):
        chunk = await original(source)
        if source is call._source and source.sent_bytes > block:
            ready.set()
            await asyncio.Future()
        return chunk

    monkeypatch.setattr(storage_source.DescriptorByteSource, "__anext__", pause_second_chunk)
    path = f"/api/v1/datasets/{DATASET}/upload/put?key=objects%2Fprivate-provider-key-0"
    with TlsServer(certificates, {path: Reply(body=b"")}) as server:
        owned, instances = session(server, key, value)

        async def cancel_partial(client):
            task = asyncio.create_task(call.execute(client, arm))
            await asyncio.wait_for(ready.wait(), 2)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert not instances[0]._responses and instances[0]._slots._value == 2

        with owned:
            owned.exchange(cancel_partial)
    assert call._closed and not call._source.complete
    assert call._source._file_fd is call._source._root_fd is None
    assert value.snapshot().upload_bytes == block
    assert value.snapshot().effect_attempts == 1 and value.snapshot().response_pending == 0
    assert sum(len(r.body) for r in server.requests) <= block
    with open_store(journal.root) as store:
        view = journal.repository(store).show(operation_id=record.operation_id)
        assert arm.intent.intent_id not in {r.intent_id for r in view.receipts}


def test_rotated_current_scope_can_read_exact_resource_but_cannot_arm_writes(journal, certificates):
    identity = journal.bound.identity.model_copy(
        update={
            "identity_epoch": str(uuid4()),
            "credential_id": str(uuid4()),
            "credential_revision": 2,
        }
    )
    bound = replace(
        journal.bound,
        identity=identity,
        credential=replace(
            journal.bound.credential, secret=SecretValue("rotated-current-key-canary")
        ),
    )
    scope = journal.plan.scope.model_copy(
        update={
            "identity_epoch": identity.identity_epoch,
            "credential_id": identity.credential_id,
            "credential_revision": identity.credential_revision,
            "clock_generation": 2,
        }
    )
    port, key, value = setup(journal, readonly=True, bound=bound, scope=scope)
    with pytest.raises(YorungeError) as raised:
        port.prepare_create(str(uuid4()))
    assert raised.value.code == "upload_plan_not_valid"
    with TlsServer(certificates, {ITEMS: page(item_rows(journal))}) as server:
        owned, _ = session(server, key, value)
        with owned:
            result = owned.exchange(
                lambda client: port.items(client, DATASET, deadline=time.monotonic() + 5)
            )
        assert len(result) == 3 and len(server.requests) == 1
        assert server.requests[0].header("X-API-Key") == bound.credential.secret.reveal()
    assert value.snapshot().effect_attempts == value.snapshot().response_pending == 0
    assert journal.plan.scope.credential_id != identity.credential_id


def test_unused_metadata_secret_is_rejected_after_raw_scan(journal, certificates):
    port, key, value = setup(journal, readonly=True)
    response = json.dumps(
        {
            "items": item_rows(journal),
            "total": 3,
            "next_cursor": None,
            "unused": {"private": key.secret.reveal()},
        }
    ).encode()
    with TlsServer(certificates, {ITEMS: Reply(body=response)}) as server:
        owned, _ = session(server, key, value)
        with owned:
            with pytest.raises(YorungeError) as raised:
                owned.exchange(
                    lambda client: port.items(client, DATASET, deadline=time.monotonic() + 5)
                )
            assert raised.value.code == "invalid_response"
            assert key.secret.reveal() not in str(raised.value)
        assert len(server.requests) == 1
    assert value.snapshot().effect_attempts == value.snapshot().response_pending == 0


def test_two_put_workers_own_their_sources_and_share_the_same_bounded_pool(
    journal, tmp_path, certificates
):
    actual_files(journal, tmp_path)
    record, port, key, value, uploads = prepared_uploads(journal)
    calls = [port.prepare_put(upload) for upload in uploads[:2]]
    arms = [journal.arm(record, "put", index) for index in range(2)]
    paths = [
        f"/api/v1/datasets/{DATASET}/upload/put?key=objects%2Fprivate-provider-key-{i}"
        for i in range(2)
    ]
    with TlsServer(
        certificates, {path: Reply(body=b"", header_delay=0.05) for path in paths}
    ) as server:
        owned, instances = session(server, key, value)

        async def workers(client):
            results = await asyncio.gather(
                *(call.execute(client, arm) for call, arm in zip(calls, arms, strict=True))
            )
            with pytest.raises(YorungeError) as raised:
                await calls[0].execute(client, arms[0])
            assert raised.value.code == "invalid_request"
            assert all(call._source._file_fd is call._source._root_fd is None for call in calls)
            return results

        with owned:
            results = owned.exchange(workers)
            assert not instances[0]._responses and instances[0]._slots._value == 2
        assert {r.path for r in server.requests} == set(paths) and len(server.requests) == 2
        assert len({r.connection for r in server.requests}) <= 2
    assert [result.receipt.object_key for result in results] == [
        upload.context.local_binding for upload in uploads[:2]
    ]
    assert value.snapshot().effect_attempts == value.snapshot().put_requests == 2
    assert value.snapshot().upload_bytes == 3 and value.snapshot().response_pending == 0
    for result in results:
        with open_store(journal.root) as store:
            record = (
                journal.repository(store)
                .receipt(record.operation_id, record.lease, result.receipt)
                .operation
            )
