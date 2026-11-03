"""Full original write graph over actual TLS; metadata success remains a later phase."""

import asyncio
import hashlib
import socket
from datetime import timedelta
from functools import partial

import pytest

from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.http_server import TlsServer, certificate, loopback_sockets
from tests.fixtures.upload_provider import UploadProvider
from tests.integration.test_upload_original import approved, denied, factory, loader
from tests.integration.test_upload_preparation import approve, prepare, runtime
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from yorunge.adapters.dataset_files import open_dataset
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_original import upload_files_original
from yorunge.adapters.upload_repository import StateUploads
from yorunge.application.datasets import DatasetBudget
from yorunge.domain.errors import OperationError

CONNECT, CONNECT_EX, GETADDRINFO = (
    socket.socket.connect,
    socket.socket.connect_ex,
    socket.getaddrinfo,
)


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(
        tmp_path_factory.mktemp("upload-files-tls"), names=("localhost", "api.ssyz.org.tr")
    )


@pytest.fixture(autouse=True)
def loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


def many(data):
    (data[1] / "two.bin").write_bytes(b"original")
    (data[1] / "ölçüm.bin").write_bytes(b"different")
    with open_dataset(data[1], DatasetBudget()) as tree:
        manifest = tree.scan()
    return (*data[:2], manifest, *data[3:])


def test_all_presigns_before_two_workers_and_serial_exact_confirm(prepared_input, certificates):
    data = many(prepared_input)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    budgets = []
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(data, server)
        before = len(server.requests)
        result = upload_files_original(
            plan.plan_id, data[0], loader(data), session_factory=factory(server, budgets)
        )
        assert result.record.status == "running"
        assert not result.existing
        assert provider.presign_calls == provider.put_calls == provider.confirm_calls == 3
        assert provider.events == [
            "create",
            "project_link",
            "presign",
            "presign",
            "presign",
            "put",
            "put",
            "confirm",
            "confirm",
            "put",
            "confirm",
        ]
        assert set(provider.confirmed) == {f.path for f in data[2].files}
        for file in data[2].files:
            row = provider.presigns[file.path]
            content = provider.objects[row["object_key"]]
            assert len(content) == file.size
            assert hashlib.sha256(content).hexdigest() == file.sha256
        assert (
            provider.presigns["one.bin"]["sha256_hash"]
            == provider.presigns["two.bin"]["sha256_hash"]
        )
        assert (
            provider.presigns["one.bin"]["object_key"] != provider.presigns["two.bin"]["object_key"]
        )
        assert not any("/items?" in request.path for request in server.requests[before:])
        counts = budgets[0].snapshot()
        assert counts.read_requests == counts.read_attempts == 12
        assert counts.effect_attempts == 11
        assert counts.upload_bytes == data[2].total_bytes
        assert counts.response_pending == 0
        count = len(server.requests)
        again = upload_files_original(plan.plan_id, data[0], denied, session_factory=denied)
        assert again.existing
        assert again.record == result.record
        assert len(server.requests) == count
    with open_existing_store(data[0]) as store:
        view = StateUploads(store).show(plan_id=plan.plan_id)
        assert len(view.intents) == len(view.receipts) == 11
        assert view.verification is None
        assert all(receipt.result == "accepted" for receipt in view.receipts)
        assert "objects/blob" not in b"".join(r.encoded() for r in view.receipts).decode()
        assert store.verify().store_schema_version == 7


@pytest.mark.parametrize("failure", ["role", "duplicate", "put", "confirm", "input"])
def test_file_stage_failure_stops_without_new_writes_or_replay(
    prepared_input, certificates, failure
):
    data = many(prepared_input)
    provider = UploadProvider(
        SCOPE.owner.id,
        SCOPE.project_id,
        duplicate_keys=failure == "duplicate",
        upload_allowed=failure != "role",
        fail_put_name="one.bin" if failure == "put" else None,
        wrong_confirm_count=failure == "confirm",
    )
    if failure == "input":

        def changed(name):
            if provider.presign_calls == 3:
                (data[1] / "one.bin").write_bytes(b"mutated!")

        provider.after_presign = changed
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(data, server)
        rejected_call = partial(
            upload_files_original,
            plan.plan_id,
            data[0],
            loader(data),
            session_factory=factory(server),
        )
        with pytest.raises(OperationError) as raised:
            rejected_call()
        assert raised.value.code == "operation_uncertain"
        assert raised.value.exit_code == 5
        assert raised.value.operation_id is not None
        assert raised.value.reason_code is not None
        assert raised.value.__cause__ is raised.value.__context__ is None
        assert provider.create_calls == provider.link_calls == 1
        if failure == "role":
            assert provider.presign_calls == provider.put_calls == provider.confirm_calls == 0
        elif failure in {"duplicate", "input"}:
            assert provider.presign_calls == 3
            assert provider.put_calls == provider.confirm_calls == 0
        elif failure == "put":
            assert provider.presign_calls == 3
            assert 1 <= provider.put_calls <= 2
            assert provider.confirm_calls == 0
        else:
            assert provider.put_calls == 2
            assert provider.confirm_calls == 1
        count = len(server.requests)
        found = upload_files_original(plan.plan_id, data[0], denied, session_factory=denied)
        assert found.record.operation_id == raised.value.operation_id
        assert found.existing
        assert found.record.status == "unknown"
        assert len(server.requests) == count
    with open_existing_store(data[0]) as store:
        view = StateUploads(store).show(plan_id=plan.plan_id)
        assert view.operation.status == "unknown"
        assert view.operation.lease is None
        assert view.verification is None
        assert store.verify().store_schema_version == 7


def test_long_put_renews_only_original_lease_before_fresh_probe(
    prepared_input, certificates, execution_clock, monkeypatch
):
    from yorunge.adapters import upload_original

    clock = execution_clock
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)

    def advance(seconds):
        clock.value += timedelta(seconds=seconds)
        clock.elapsed += seconds

    provider.after_put = lambda name: advance(119)
    original_publish = upload_original._Environment.publish

    def published(environment, outcome):
        original_publish(environment, outcome)
        if outcome.receipt.sent_bytes is not None:
            advance(2)

    monkeypatch.setattr(upload_original._Environment, "publish", published)
    renewals = []
    original_renew = StateUploads.renew

    def renewed(repository, *args, **kwargs):
        lease = original_renew(repository, *args, **kwargs)
        renewals.append(lease)
        return lease

    monkeypatch.setattr(StateUploads, "renew", renewed)

    def probe_delay():
        if provider.objects:
            advance(4.9)

    provider.on_request = probe_delay
    with TlsServer(certificates, provider.routes()) as server:
        preparation = runtime(prepared_input, server, clock=clock)
        plan = prepare(preparation, prepared_input)
        approve(preparation, plan)
        result = upload_files_original(
            plan.plan_id,
            prepared_input[0],
            loader(prepared_input),
            session_factory=factory(server),
            clock=clock,
        )
        assert result.record.status == "running"
        assert provider.confirm_calls == 1
        assert len(renewals) == 1
        assert renewals[0].mode == "write"
        assert result.record.write_owner_id == renewals[0].owner_id
        assert result.record.fence == 1
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store, clock=clock).show(plan_id=plan.plan_id)
        assert len(view.intents) == len(view.receipts) == 5
        assert view.operation.status == "running"
        assert view.verification is None


def test_cancel_original_during_put_drains_workers_before_same_id_unknown(
    prepared_input, certificates, monkeypatch
):
    from yorunge.adapters import upload_original
    from yorunge.application import upload_workflow

    data = many(prepared_input)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    owner, children = [], []
    original_batch = upload_workflow._put_batch
    original_execute = upload_original._Call.execute

    async def batch(environment, indices):
        owner.append(asyncio.current_task())
        return await original_batch(environment, indices)

    async def execute(call, arm):
        if arm.intent.kind == "put":
            children.append(asyncio.current_task())
        return await original_execute(call, arm)

    monkeypatch.setattr(upload_workflow, "_put_batch", batch)
    monkeypatch.setattr(upload_original._Call, "execute", execute)
    provider.after_put = lambda name: owner[0].get_loop().call_soon_threadsafe(owner[0].cancel)
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(data, server)
        rejected_call = partial(
            upload_files_original,
            plan.plan_id,
            data[0],
            loader(data),
            session_factory=factory(server),
        )
        with pytest.raises(asyncio.CancelledError):
            rejected_call()
        assert children
        assert all(task.done() for task in children)
        assert provider.confirm_calls == 0
        assert 1 <= provider.put_calls <= 2
        count = len(server.requests)
        result = upload_files_original(plan.plan_id, data[0], denied, session_factory=denied)
        assert result.existing
        assert result.record.status == "unknown"
        assert len(server.requests) == count
    with open_existing_store(data[0]) as store:
        view = StateUploads(store).show(plan_id=plan.plan_id)
        assert view.operation.lease is None
        assert view.verification is None
        assert store.verify().store_schema_version == 7


def test_stale_second_current_never_arms_after_first_real_put_failed(
    prepared_input, certificates, execution_clock, monkeypatch
):
    from yorunge.adapters import upload_original

    clock, failed = execution_clock, asyncio.Event()
    data = many(prepared_input)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id, fail_put_name="one.bin")
    original_arm = upload_original._Environment.arm
    original_current = upload_original._Environment.current
    original_execute = upload_original._Call.execute
    put_checks = []

    def advance(seconds):
        clock.value += timedelta(seconds=seconds)
        clock.elapsed += seconds

    provider.after_presign = lambda name: advance(29) if provider.presign_calls == 3 else None

    def arm(environment, check, kind, index=None):
        result = original_arm(environment, check, kind, index)
        if kind == "put" and index == 0:
            advance(26)  # Cross the refresh boundary after the first worker is armed.
        return result

    async def current(environment, kind):
        result = await original_current(environment, kind)
        if kind == "put":
            put_checks.append(result)
            if len(put_checks) == 2:
                await failed.wait()
        return result

    async def execute(call, issued):
        try:
            return await original_execute(call, issued)
        except BaseException:
            if issued.intent.kind == "put":
                failed.set()
            raise

    monkeypatch.setattr(upload_original._Environment, "arm", arm)
    monkeypatch.setattr(upload_original._Environment, "current", current)
    monkeypatch.setattr(upload_original._Call, "execute", execute)
    with TlsServer(certificates, provider.routes()) as server:
        preparation = runtime(data, server, clock=clock)
        plan = prepare(preparation, data)
        approve(preparation, plan)
        rejected_call = partial(
            upload_files_original,
            plan.plan_id,
            data[0],
            loader(data),
            session_factory=factory(server),
            clock=clock,
        )
        with pytest.raises(OperationError) as raised:
            rejected_call()
        assert raised.value.code == "operation_uncertain"
        assert raised.value.exit_code == 5
        assert len(put_checks) == 2
        assert put_checks[0].checked_at < put_checks[1].checked_at
        assert provider.put_calls == 1
        assert provider.confirm_calls == 0
    with open_existing_store(data[0]) as store:
        view = StateUploads(store, clock=clock).show(plan_id=plan.plan_id)
        assert sum(intent.kind == "put" for intent in view.intents) == 1
        assert view.operation.status == "unknown"
        assert store.verify().store_schema_version == 7


def test_nearly_expired_current_is_refreshed_before_local_arm_work(
    prepared_input, certificates, execution_clock, monkeypatch
):
    from yorunge.adapters import upload_original

    clock = execution_clock
    data = many(prepared_input)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    original_arm = upload_original._Environment.arm
    checks = []

    def advance(seconds):
        clock.value += timedelta(seconds=seconds)
        clock.elapsed += seconds

    provider.after_presign = lambda name: advance(29) if provider.presign_calls == 3 else None

    def arm(environment, check, kind, index=None):
        if kind == "put" and index == 0:
            # Current evidence must leave time for local descriptor/transaction work.
            advance(2)
            checks.append(check)
        return original_arm(environment, check, kind, index)

    monkeypatch.setattr(upload_original._Environment, "arm", arm)
    budgets = []
    with TlsServer(certificates, provider.routes()) as server:
        preparation = runtime(data, server, clock=clock)
        plan = prepare(preparation, data)
        approve(preparation, plan)
        result = upload_files_original(
            plan.plan_id,
            data[0],
            loader(data),
            session_factory=factory(server, budgets),
            clock=clock,
        )
        assert result.record.status == "running"
        assert provider.confirm_calls == 3
        assert len(checks) == 1
        assert budgets[0].snapshot().read_requests == 18  # Six fresh mandatory upload reads.
        assert provider.put_calls == 3
        assert provider.presign_calls == 3
    with open_existing_store(data[0]) as store:
        view = StateUploads(store, clock=clock).show(plan_id=plan.plan_id)
        assert len(view.intents) == len(view.receipts) == 11
        assert all(receipt.result == "accepted" for receipt in view.receipts)
        assert store.verify().store_schema_version == 7
