"""Actual TLS control effects from real committed repository arms; no live account."""

import asyncio
import copy
import json
import logging
import pickle
import socket
import time
from dataclasses import replace
from functools import partial
from uuid import uuid4

import pytest

from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from tests.integration.test_upload_http_budget import session
from tests.integration.test_upload_journal import DATASET, seal
from tests.integration.test_upload_journal import journal as journal
from yorunge.adapters.platform_upload_port import ObservedUploadPort
from yorunge.adapters.state import open_store
from yorunge.application.http_transport import HttpCredential
from yorunge.application.upload_budget import UploadBudget
from yorunge.domain.capabilities import timestamp
from yorunge.domain.create_receipt import CreateReceiptV2
from yorunge.domain.credentials import SecretValue
from yorunge.domain.dataset_transfer import StageReceipt
from yorunge.domain.errors import YorungeError

CONNECT, CONNECT_EX, GETADDRINFO = (
    socket.socket.connect,
    socket.socket.connect_ex,
    socket.getaddrinfo,
)
RAW_KEY = "objects/provider-resource-canary-17035"


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(
        tmp_path_factory.mktemp("upload-effect-tls"), names=("localhost", "api.ssyz.org.tr")
    )


@pytest.fixture(autouse=True)
def loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


def setup(journal, *, readonly=False, bound=None, key=None, scope=None, value=None):
    bound = journal.bound if bound is None else bound
    key = key or HttpCredential(
        "X-API-Key",
        bound.credential.secret,
        target=bound.credential.target,
        service_id="evren-platform",
    )
    value = value or UploadBudget(
        journal.plan.request_limits, end=time.monotonic() + 60, read_only=readonly
    )
    port = ObservedUploadPort(
        journal.plan,
        journal.manifest,
        journal.plan.scope if scope is None else scope,
        bound,
        key,
        value,
        utc_clock=journal.clock.now,
    )
    return port, key, value


def created(journal, **changes):
    return {
        "id": DATASET,
        "name": journal.plan.parameters.name,
        "modality": journal.plan.parameters.modality,
        "visibility": "private",
        "contributions_enabled": False,
        "owner_id": journal.plan.scope.owner.id,
        "org_id": None,
        **changes,
    }


def encoded(value, **kwargs):
    return Reply(body=json.dumps(value).encode(), **kwargs)


def save(journal, record, outcome):
    with open_store(journal.root) as store:
        return (
            journal.repository(store)
            .receipt(record.operation_id, record.lease, outcome.receipt)
            .operation
        )


def presign_response(context, **changes):
    return {
        "presigned_urls": [
            {
                "filename": context.file.path,
                "sha256_hash": context.file.sha256,
                "file_size": context.file.size,
                "client_uid": context.client_uid,
                "object_key": RAW_KEY,
                "upload_url": f"/datasets/{DATASET}/upload/put?key={RAW_KEY}",
                **changes,
            }
        ]
    }


def test_real_control_chain_is_single_attempt_and_keeps_provider_key_volatile(
    journal, certificates, caplog
):
    record = journal.approved()
    port, key, value = setup(journal)
    context = port.files(record.operation_id, DATASET)[0]
    paths = [
        "/api/v1/datasets",
        f"/api/v1/projects/{journal.plan.scope.project_id}/datasets",
        f"/api/v1/datasets/{DATASET}/upload/presign",
        f"/api/v1/datasets/{DATASET}/upload/confirm",
    ]
    replies = [
        encoded({"success": True, "data": created(journal, unused="x" * 5000)}, status=201),
        Reply(body=b""),
        encoded(presign_response(context)),
        encoded({"created": 1, "actual_count": 1, "batch_duplicates": 0}),
    ]
    with TlsServer(certificates, dict(zip(paths, replies, strict=True))) as server:
        owned, instances = session(server, key, value)
        with caplog.at_level(logging.DEBUG), owned:
            call = port.prepare_create(record.operation_id)
            assert value.snapshot().create_requests == 1
            with open_store(journal.root) as store:
                assert not journal.repository(store).show(operation_id=record.operation_id).intents
            arm = journal.arm(record)
            outcome = owned.exchange(lambda client: call.execute(client, arm))
            assert type(outcome.receipt) is CreateReceiptV2
            assert len(outcome.receipt.encoded()) < 2048
            record = save(journal, record, outcome)
            call = port.prepare_link(record.operation_id, DATASET)
            arm = journal.arm(record, "project_link")
            outcome = owned.exchange(lambda client: call.execute(client, arm))
            record = save(journal, record, outcome)
            call = port.prepare_presign(context)
            arm = journal.arm(record, "presign", 0)
            outcome = owned.exchange(lambda client: call.execute(client, arm))
            upload = outcome.upload
            assert upload is not None
            assert outcome.receipt.object_key == context.local_binding
            record = save(journal, record, outcome)
            # Q.2 owns control effects. A synthetic accepted PUT predecessor is
            # explicit test data; descriptor streaming is the separate q.3 slice.
            put_arm = journal.arm(record, "put", 0)
            put_intent, permit, _ = put_arm
            permit.consume()
            with open_store(journal.root) as store:
                record = (
                    journal.repository(store)
                    .receipt(
                        record.operation_id,
                        record.lease,
                        StageReceipt(
                            schema_version=1,
                            intent_id=put_intent.intent_id,
                            recorded_at=timestamp(journal.clock.value),
                            result="accepted",
                            dataset_id=DATASET,
                            object_key=context.local_binding,
                            sent_bytes=context.file.size,
                            sent_sha256=context.file.sha256,
                        ),
                    )
                    .operation
                )
            call = port.prepare_confirm(upload, confirmed_count=1)
            arm = journal.arm(record, "confirm", 0)
            outcome = owned.exchange(lambda client: call.execute(client, arm))
            record = save(journal, record, outcome)
            assert instances[0]._slots._value == 2
            assert not instances[0]._responses
        assert [r.path for r in server.requests] == paths
        assert all(r.method == "POST" for r in server.requests)
        assert all(r.header("X-API-Key") == key.secret.reveal() for r in server.requests)
        assert all(r.header("Accept-Encoding") == "identity" for r in server.requests)
        assert all(context.local_binding not in r.body.decode() for r in server.requests)
        presign = json.loads(server.requests[2].body)["files"][0]
        assert presign["filename"] == context.file.path
        assert presign["client_uid"] == context.client_uid
        confirm = json.loads(server.requests[3].body)
        assert confirm["skip_dedup"] is True
        assert confirm["items"][0]["object_key"] == RAW_KEY
    with open_store(journal.root) as store:
        view = journal.repository(store).show(operation_id=record.operation_id)
        assert RAW_KEY not in b"".join(r.encoded() for r in view.receipts).decode()
        assert store.verify().store_schema_version == 7
    counts = value.snapshot()
    assert counts.effect_attempts == 4
    assert counts.response_pending == 0
    assert all(x not in caplog.text for x in (RAW_KEY, key.secret.reveal(), "unused"))
    assert all(x not in repr(outcome) + repr(port) + repr(call) for x in (RAW_KEY, DATASET))
    for obj in (outcome, port, call):
        for op in (copy.copy, copy.deepcopy, pickle.dumps):
            with pytest.raises(TypeError):
                op(obj)


@pytest.mark.parametrize(
    "status,code",
    [
        (302, "remote_failed"),
        (401, "remote_access_denied"),
        (403, "remote_access_denied"),
        (429, "remote_rate_limited"),
        (500, "remote_failed"),
        (503, "remote_failed"),
    ],
)
def test_real_effect_status_never_retries_or_manufactures_rejection(
    journal, certificates, status, code
):
    record = journal.approved()
    port, key, value = setup(journal)
    call = port.prepare_create(record.operation_id)
    arm = journal.arm(record)
    with TlsServer(
        certificates, {"/api/v1/datasets": Reply(status=status, body=b"private-error")}
    ) as server:
        owned, instances = session(server, key, value)
        with owned:
            rejected_call = partial(owned.exchange, lambda client: call.execute(client, arm))
            with pytest.raises(YorungeError) as raised:
                rejected_call()
            assert raised.value.code == code
            assert raised.value.__cause__ is raised.value.__context__ is None
            assert not instances[0]._responses
            assert instances[0]._slots._value == 2
        assert len(server.requests) == 1
    assert value.snapshot().effect_attempts == 1
    assert value.snapshot().response_pending == 0
    with open_store(journal.root) as store:
        assert not journal.repository(store).show(operation_id=record.operation_id).receipts


@pytest.mark.parametrize(
    "reply",
    [
        Reply(body=b'{"id":1,"id":2}'),
        Reply(body=b'{"success":false}'),
        Reply(body=b"\xff"),
        Reply(body=b"x" * (1_048_576 + 1)),
        Reply(body=b"{}", headers=(("Content-Encoding", "gzip"),)),
        Reply(body=b'{"ok":true}', truncate_at=3),
    ],
)
def test_real_malformed_compressed_truncated_create_is_no_replay(journal, certificates, reply):
    record = journal.approved()
    port, key, value = setup(journal)
    call = port.prepare_create(record.operation_id)
    arm = journal.arm(record)
    with TlsServer(certificates, {"/api/v1/datasets": reply}) as server:
        owned, instances = session(server, key, value)
        with owned:
            rejected_call = partial(owned.exchange, lambda client: call.execute(client, arm))
            with pytest.raises(YorungeError):
                rejected_call()
            assert not instances[0]._responses
            assert instances[0]._slots._value == 2
        assert len(server.requests) == 1
    assert value.snapshot().effect_attempts == 1
    assert value.snapshot().response_pending == 0


@pytest.mark.parametrize("mismatch", ["tuple", "operation", "stage", "digest", "expired"])
def test_wrong_arm_or_extended_tuple_is_zero_wire_and_does_not_consume_permit(
    journal, certificates, mismatch
):
    record = journal.approved()
    port, key, value = setup(journal)
    operation_id = str(uuid4()) if mismatch == "operation" else record.operation_id
    if mismatch == "stage":
        call = port.prepare_link(operation_id, DATASET)
    elif mismatch == "digest":
        body = journal.plan.model_dump(mode="json")
        body["parameters"]["name"] = "a-different-approved-name"
        other_plan = seal(body)
        other_port = ObservedUploadPort(
            other_plan,
            journal.manifest,
            other_plan.scope,
            journal.bound,
            key,
            value,
            utc_clock=journal.clock.now,
        )
        call = other_port.prepare_create(operation_id)
    else:
        call = port.prepare_create(operation_id)
    arm = journal.arm(record)
    supplied = (*arm[:2], arm.deadline + 999) if mismatch == "tuple" else arm
    if mismatch == "expired":
        journal.clock.elapsed += 1000
    with TlsServer(certificates, {}) as server:
        owned, _ = session(server, key, value)
        with owned:
            rejected_call = partial(owned.exchange, lambda client: call.execute(client, supplied))
            with pytest.raises(YorungeError):
                rejected_call()
        assert not server.requests
    assert value.snapshot().effect_attempts == value.snapshot().create_requests == 0
    assert value.snapshot().project_link_requests == value.snapshot().response_pending == 0
    # Failed pre-wire binding does not consume the generic physical permit.
    arm[1].consume()


def test_unstarted_call_close_refunds_and_call_reuse_cannot_dispatch(journal, certificates):
    record = journal.approved()
    port, key, value = setup(journal)
    abandoned = port.prepare_create(record.operation_id)
    abandoned.close()
    assert value.snapshot().create_requests == 0
    call = port.prepare_create(record.operation_id)
    arm = journal.arm(record)
    with TlsServer(certificates, {"/api/v1/datasets": encoded(created(journal))}) as server:
        owned, _ = session(server, key, value)
        with owned:
            owned.exchange(lambda client: call.execute(client, arm))
            rejected_call = partial(owned.exchange, lambda client: call.execute(client, arm))
            with pytest.raises(YorungeError):
                rejected_call()
        assert len(server.requests) == 1
    assert value.snapshot().create_requests == value.snapshot().effect_attempts == 1


@pytest.mark.parametrize(
    "mismatch", ["secret_object", "revision", "epoch", "limits", "target", "scope"]
)
def test_binding_mismatch_is_rejected_before_quota_or_wire(journal, mismatch):
    key = HttpCredential(
        "X-API-Key",
        journal.bound.credential.secret,
        target=journal.bound.credential.target,
        service_id="evren-platform",
    )
    bound, scope = journal.bound, journal.plan.scope
    value = UploadBudget(journal.plan.request_limits, end=time.monotonic() + 60, read_only=False)
    if mismatch == "secret_object":
        key = replace(key, secret=SecretValue(key.secret.reveal()))
    elif mismatch == "revision":
        bound = replace(
            bound, identity=bound.identity.model_copy(update={"credential_revision": 2})
        )
    elif mismatch == "epoch":
        bound = replace(
            bound, identity=bound.identity.model_copy(update={"identity_epoch": str(uuid4())})
        )
    elif mismatch == "limits":
        limits = journal.plan.request_limits.model_copy(
            update={"max_upload_bytes": journal.plan.request_limits.max_upload_bytes + 1}
        )
        value = UploadBudget(limits, end=time.monotonic() + 60, read_only=False)
    elif mismatch == "target":
        key = replace(key, prefix="Bearer ")
    else:
        scope = scope.model_copy(update={"project_id": str(uuid4())})
    with pytest.raises(YorungeError):
        setup(journal, key=key, bound=bound, scope=scope, value=value)
    assert value.snapshot().effect_attempts == value.snapshot().create_requests == 0


def test_cancelled_real_effect_closes_resources_without_receipt_or_retry(journal, certificates):
    record = journal.approved()
    port, key, value = setup(journal)
    call = port.prepare_create(record.operation_id)
    arm = journal.arm(record)
    with TlsServer(
        certificates, {"/api/v1/datasets": encoded(created(journal), header_delay=0.2)}
    ) as server:
        owned, instances = session(server, key, value)

        async def cancel(client):
            task = asyncio.create_task(call.execute(client, arm))
            while not server.requests:
                await asyncio.sleep(0.005)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert not instances[0]._responses
            assert instances[0]._slots._value == 2

        with owned:
            owned.exchange(cancel)
        assert len(server.requests) == 1
    assert value.snapshot().effect_attempts == 1
    assert value.snapshot().response_pending == 0


def stage_call(journal, kind):
    record = journal.approved()
    port, key, value = setup(journal)
    arm = journal.arm(record)
    record = journal.accept(record, arm.intent).operation
    if kind == "project_link":
        return record, port.prepare_link(record.operation_id, DATASET), port, key, value
    arm = journal.arm(record, "project_link")
    record = journal.accept(record, arm.intent).operation
    context = port.files(record.operation_id, DATASET)[0]
    if kind == "presign":
        return record, port.prepare_presign(context), port, key, value
    from yorunge.application.upload_descriptors import presigned

    upload = presigned(json.dumps(presign_response(context)).encode(), context, key.secret)
    for previous in ("presign", "put"):
        arm = journal.arm(record, previous, 0)
        arm[1].consume()
        receipt = StageReceipt(
            schema_version=1,
            intent_id=arm.intent.intent_id,
            recorded_at=timestamp(journal.clock.value),
            result="accepted",
            dataset_id=DATASET,
            object_key=context.local_binding,
            sent_bytes=context.file.size if previous == "put" else None,
            sent_sha256=context.file.sha256 if previous == "put" else None,
        )
        with open_store(journal.root) as store:
            record = (
                journal.repository(store)
                .receipt(record.operation_id, record.lease, receipt)
                .operation
            )
    return record, port.prepare_confirm(upload, confirmed_count=1), port, key, value


@pytest.mark.parametrize("kind", ["project_link", "presign", "confirm"])
@pytest.mark.parametrize("bad", ["logical", "secret"])
def test_stage_specific_invalid_body_never_produces_an_accepted_receipt(
    journal, certificates, kind, bad
):
    record, call, port, key, value = stage_call(journal, kind)
    raw = b'{"success":false}'
    if bad == "secret":
        raw = json.dumps({"success": True, "unused": key.secret.reveal()}).encode()
    arm = journal.arm(record, kind, None if kind == "project_link" else 0)
    with TlsServer(certificates, {"/api/v1/" + call._request.endpoint: Reply(body=raw)}) as server:
        owned, instances = session(server, key, value)
        with owned:
            rejected_call = partial(owned.exchange, lambda client: call.execute(client, arm))
            with pytest.raises(YorungeError) as raised:
                rejected_call()
            assert raised.value.code == "invalid_response"
            assert key.secret.reveal() not in str(raised.value) + repr(raised.value)
            assert not instances[0]._responses
            assert instances[0]._slots._value == 2
        assert len(server.requests) == 1
    assert value.snapshot().effect_attempts == 1
    assert value.snapshot().response_pending == 0
    with open_store(journal.root) as store:
        view = journal.repository(store).show(operation_id=record.operation_id)
        assert arm.intent.intent_id not in {r.intent_id for r in view.receipts}


def test_quota_failure_precedes_any_intent_and_abandoned_call_is_explicitly_refunded(journal):
    record = journal.approved()
    port, _, value = setup(journal)
    call = port.prepare_create(record.operation_id)
    with pytest.raises(YorungeError) as raised:
        port.prepare_create(record.operation_id)
    assert raised.value.code == "upload_limit_exceeded"
    with open_store(journal.root) as store:
        assert not journal.repository(store).show(operation_id=record.operation_id).intents
    call.close()
    assert value.snapshot().create_requests == value.snapshot().response_pending == 0
    port.prepare_create(record.operation_id).close()


@pytest.mark.parametrize("mismatch", ["credential", "budget"])
def test_other_client_is_zero_wire_and_releases_only_its_own_reservation(
    journal, certificates, mismatch
):
    record = journal.approved()
    port, key, value = setup(journal)
    call = port.prepare_create(record.operation_id)
    arm = journal.arm(record)
    foreign_budget = UploadBudget(
        journal.plan.request_limits, end=time.monotonic() + 60, read_only=False
    )
    other_key = replace(key)
    with TlsServer(certificates, {}) as server:
        owned, _ = session(
            server,
            other_key if mismatch == "credential" else key,
            foreign_budget if mismatch == "budget" else value,
        )
        with owned:
            rejected_call = partial(owned.exchange, lambda client: call.execute(client, arm))
            with pytest.raises(YorungeError) as raised:
                rejected_call()
            assert raised.value.code == "invalid_request"
        assert not server.requests
    assert value.snapshot().create_requests == value.snapshot().effect_attempts == 0
    assert (
        foreign_budget.snapshot().create_requests == foreign_budget.snapshot().effect_attempts == 0
    )
    arm[1].consume()


def test_short_issued_deadline_reaches_actual_network_without_extension(journal, certificates):
    record = journal.approved()
    port, key, value = setup(journal)
    call = port.prepare_create(record.operation_id)
    with open_store(journal.root) as store:
        arm = journal.repository(store).arm(
            record.operation_id,
            record.lease,
            journal.plan,
            "create",
            None,
            total_end=journal.clock.monotonic() + 5.3,
        )
    assert 0 < arm.deadline - time.monotonic() < 0.4
    with TlsServer(
        certificates, {"/api/v1/datasets": encoded(created(journal), header_delay=0.6)}
    ) as server:
        owned, instances = session(server, key, value)
        with owned:
            rejected_call = partial(owned.exchange, lambda client: call.execute(client, arm))
            with pytest.raises(YorungeError) as raised:
                rejected_call()
            assert raised.value.code == "transport_timeout"
            assert not instances[0]._responses
            assert instances[0]._slots._value == 2
        assert len(server.requests) == 1
    assert value.snapshot().effect_attempts == 1
    assert value.snapshot().response_pending == 0


def test_file_batch_is_bounded_and_foreign_or_nested_mutated_context_is_rejected(journal):
    record = journal.approved()
    port, _, value = setup(journal)
    files = port.files(record.operation_id, DATASET)
    assert port.files(record.operation_id, DATASET) is files
    rejected_call = partial(port.files, str(uuid4()), DATASET)
    with pytest.raises(YorungeError):
        rejected_call()
    foreign, _, _ = setup(journal)
    other = foreign.files(record.operation_id, DATASET)[0]
    with pytest.raises(YorungeError):
        port.prepare_presign(other)
    files[0].file.__dict__["size"] = True
    with pytest.raises(YorungeError):
        port.prepare_presign(files[0])
    assert value.snapshot().presign_requests == value.snapshot().effect_attempts == 0


def test_a_confirm_is_numbered_among_the_files_of_the_upload(journal):
    from yorunge.application.upload_descriptors import presigned

    record = journal.approved()
    port, key, value = setup(journal)
    context = port.files(record.operation_id, DATASET)[0]
    upload = presigned(json.dumps(presign_response(context)).encode(), context, key.secret)
    files = len(journal.manifest.files)
    before = value.snapshot()
    for place in (0, -1, files + 1, 128, True, 1.0, "1", None):
        with pytest.raises(YorungeError) as raised:
            port.prepare_confirm(upload, confirmed_count=place)
        assert raised.value.code == "invalid_request", place
    assert value.snapshot() == before
    port.prepare_confirm(upload, confirmed_count=files)  # the last of them is the edge


@pytest.mark.parametrize("field", ["owner", "project", "name"])
def test_selected_literal_in_local_plan_is_rejected_before_reservation(journal, field):
    secret = {
        "owner": journal.plan.scope.owner.id,
        "project": journal.plan.scope.project_id,
        "name": journal.plan.parameters.name,
    }[field]
    bound = replace(
        journal.bound, credential=replace(journal.bound.credential, secret=SecretValue(secret))
    )
    value = UploadBudget(journal.plan.request_limits, end=time.monotonic() + 60, read_only=False)
    with pytest.raises(YorungeError) as raised:
        setup(journal, bound=bound, value=value)
    assert raised.value.code == "invalid_request"
    assert raised.value.__cause__ is raised.value.__context__ is None
    assert value.snapshot().create_requests == value.snapshot().effect_attempts == 0


@pytest.mark.parametrize("timing", ["before_claim", "during_response"])
def test_prepared_presign_cannot_accept_a_mutated_nested_file(journal, certificates, timing):
    record, call, port, key, value = stage_call(journal, "presign")
    context = port.files(record.operation_id, DATASET)[0]
    original_hash = journal.manifest.files[0].sha256
    changed_hash = "0" * 64
    assert original_hash != changed_hash
    if timing == "before_claim":
        context.file.__dict__["sha256"] = changed_hash
    arm = journal.arm(record, "presign", 0)

    def changed_response(request, count):
        assert json.loads(request.body)["files"][0]["sha256_hash"] == original_hash
        context.file.__dict__["sha256"] = changed_hash
        return encoded(presign_response(context))

    path = f"/api/v1/datasets/{DATASET}/upload/presign"
    with TlsServer(certificates, {path: changed_response}) as server:
        owned, instances = session(server, key, value)
        with owned:
            rejected_call = partial(owned.exchange, lambda client: call.execute(client, arm))
            with pytest.raises(YorungeError) as raised:
                rejected_call()
            assert raised.value.code == "invalid_request"
            assert not instances[0]._responses
            assert instances[0]._slots._value == 2
        assert len(server.requests) == int(timing == "during_response")
    assert value.snapshot().effect_attempts == int(timing == "during_response")
    assert value.snapshot().response_pending == 0
    with open_store(journal.root) as store:
        view = journal.repository(store).show(operation_id=record.operation_id)
        assert arm.intent.intent_id not in {r.intent_id for r in view.receipts}
    if timing == "before_claim":
        arm[1].consume()
