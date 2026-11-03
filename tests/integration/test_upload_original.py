"""Real original create/link composition; same-ID local lookup never resumes writes."""

import asyncio
import socket
from functools import partial
from uuid import uuid4

import pytest

from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from tests.fixtures.upload_provider import DATASET, UploadProvider
from tests.integration.test_upload_http_budget import session
from tests.integration.test_upload_preparation import approve, prepare, runtime
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from yorunge.adapters.secrets import EnvSecretReader
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_original import create_link_original
from yorunge.adapters.upload_repository import StateUploads
from yorunge.domain.create_receipt import CreateReceiptV2
from yorunge.domain.errors import OperationError, YorungeError

CONNECT, CONNECT_EX, GETADDRINFO = (
    socket.socket.connect,
    socket.socket.connect_ex,
    socket.getaddrinfo,
)


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(
        tmp_path_factory.mktemp("upload-original-tls"), names=("localhost", "api.ssyz.org.tr")
    )


@pytest.fixture(autouse=True)
def loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


def loader(data):
    return lambda plan: (data[3], data[4])


def factory(server, budgets=None):
    def build(key, budget):
        if budgets is not None:
            budgets.append(budget)
        return session(server, key, budget)[0]

    return build


def denied(*args, **kwargs):
    pytest.fail("dependency access on an existing/local rejection path")


def approved(data, server):
    value = runtime(data, server)
    plan = prepare(value, data)
    approve(value, plan)
    return plan


def test_original_phase_uses_one_secret_budget_and_short_store_phases(
    prepared_input, certificates, monkeypatch
):
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    budgets, reads, locks = [], [], []
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(prepared_input, server)
        before = len(server.requests)
        original = EnvSecretReader.read

        def count(self, reference):
            reads.append(reference)
            return original(self, reference)

        monkeypatch.setattr(EnvSecretReader, "read", count)

        def unlocked():
            with open_existing_store(prepared_input[0]) as store:
                store.connection.execute("BEGIN IMMEDIATE")
                store.connection.rollback()
                locks.append(True)

        provider.on_request = unlocked
        result = create_link_original(
            plan.plan_id,
            prepared_input[0],
            loader(prepared_input),
            session_factory=factory(server, budgets),
        )
        assert result.plan == plan
        assert not result.existing
        assert result.record.status == "running"
        assert result.record.dataset_id == DATASET
        assert result.record.workflow_latched
        assert len(reads) == len(budgets) == 1
        requests = server.requests[before:]
        assert [r.method for r in requests] == [
            "GET",
            "GET",
            "POST",
            "GET",
            "GET",
            "GET",
            "GET",
            "POST",
        ]
        assert len(locks) == len(requests)
        assert provider.create_calls == provider.link_calls == 1
        assert budgets[0].snapshot().read_requests == 6
        assert budgets[0].snapshot().effect_attempts == 2
        assert budgets[0].snapshot().response_pending == 0
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store).show(plan_id=plan.plan_id)
        assert view.operation == result.record
        assert len(view.intents) == len(view.receipts) == 2
        assert type(view.receipts[0]) is CreateReceiptV2
        assert view.receipts[0].created_dataset.owner_id == SCOPE.owner.id
        assert store.verify().store_schema_version == 7
    assert DATASET not in repr(result)


def test_existing_operation_skips_loader_secret_files_and_http(
    prepared_input, certificates, monkeypatch
):
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(prepared_input, server)
        first = create_link_original(
            plan.plan_id, prepared_input[0], loader(prepared_input), session_factory=factory(server)
        )
        count = len(server.requests)
        (prepared_input[1] / "one.bin").unlink()
        monkeypatch.setattr(EnvSecretReader, "read", denied)
        second = create_link_original(
            plan.plan_id, prepared_input[0], denied, session_factory=denied
        )
        assert second.existing
        assert second.record == first.record
        assert len(server.requests) == count
        assert provider.create_calls == provider.link_calls == 1


@pytest.mark.parametrize("failure", ["approval", "draft", "input", "scope"])
def test_pre_admission_rejection_has_no_write_or_operation(prepared_input, certificates, failure):
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        value = runtime(prepared_input, server)
        plan = prepare(
            value,
            prepared_input,
            **(
                {"cost_policy": "bounded_required", "budget_micros": 200_000_000}
                if failure == "draft"
                else {}
            ),
        )
        if failure not in {"approval", "draft"}:
            approve(value, plan)
        before = len(server.requests)
        data = prepared_input
        if failure == "input":
            (data[1] / "one.bin").write_bytes(b"mutated!")
        elif failure == "scope":
            data = (*data[:3], data[3].model_copy(update={"project_id": str(uuid4())}), data[4])
        expected = {
            "approval": "approval_required",
            "draft": "upload_plan_not_valid",
            "input": "input_changed",
            "scope": "state_changed",
        }[failure]
        rejected_call = partial(
            create_link_original,
            plan.plan_id,
            data[0],
            denied if failure in {"approval", "draft"} else loader(data),
            session_factory=factory(server),
        )
        with pytest.raises(YorungeError) as raised:
            rejected_call()
        assert raised.value.code == expected
        assert len(server.requests) == before
        assert not provider.created
    with open_existing_store(prepared_input[0]) as store:
        assert StateUploads(store).show(plan_id=plan.plan_id).operation is None


@pytest.mark.parametrize(
    "failure", ["create_body", "create_lost", "link_status", "detail_owner", "input_after_create"]
)
def test_post_intent_failure_is_same_id_unknown_and_never_replays(
    prepared_input, certificates, failure
):
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    if failure == "create_body":
        provider.create_reply = Reply(status=201, body=b'{"success":false}')
    elif failure == "create_lost":
        provider.create_reply = Reply(
            status=201, body=b'{"private":"response-lost"}', truncate_at=3
        )
    elif failure == "link_status":
        provider.link_reply = Reply(status=503, body=b"private-failed-link")
    elif failure == "detail_owner":
        provider.wrong_detail_owner = True
    else:
        provider.after_create = lambda: (prepared_input[1] / "one.bin").write_bytes(b"mutated!")
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(prepared_input, server)
        rejected_call = partial(
            create_link_original,
            plan.plan_id,
            prepared_input[0],
            loader(prepared_input),
            session_factory=factory(server),
        )
        with pytest.raises(OperationError) as raised:
            rejected_call()
        assert raised.value.code == "operation_uncertain"
        assert raised.value.exit_code == 5
        assert raised.value.operation_id is not None
        assert raised.value.reason_code is not None
        assert raised.value.__cause__ is raised.value.__context__ is None
        count = len(server.requests)
        found = create_link_original(
            plan.plan_id, prepared_input[0], denied, session_factory=denied
        )
        assert found.existing
        assert found.record.operation_id == raised.value.operation_id
        assert found.record.status == "unknown"
        assert found.record.reason == "request_uncertain"
        assert len(server.requests) == count
        assert provider.create_calls == 1
        assert provider.link_calls == int(failure == "link_status")
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store).show(plan_id=plan.plan_id)
        assert view.operation.status == "unknown"
        assert view.operation.lease is None
        assert len(view.intents) == (2 if failure == "link_status" else 1)
        assert len(view.receipts) == int(failure not in {"create_body", "create_lost"})
        assert store.verify().store_schema_version == 7


def test_active_loop_rejects_before_store_or_loader(prepared_input, monkeypatch):
    from yorunge.adapters import upload_original

    monkeypatch.setattr(upload_original, "open_existing_store", denied)

    async def run():
        rejected_call = partial(
            create_link_original, str(uuid4()), prepared_input[0], denied, session_factory=denied
        )
        with pytest.raises(YorungeError) as raised:
            rejected_call()
        assert raised.value.code == "invalid_request"

    asyncio.run(run())


def test_admission_race_returns_winner_without_manufacturing_write_access(
    prepared_input, certificates, monkeypatch
):
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    original = StateUploads.admit
    winners = []

    def race(repository, plan_id, current):
        with open_existing_store(prepared_input[0]) as store:
            competitor = StateUploads(store, repository.credential, clock=repository.clock)
            winners.append(original(competitor, plan_id, current))
        return original(repository, plan_id, current)

    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(prepared_input, server)
        monkeypatch.setattr(StateUploads, "admit", race)
        result = create_link_original(
            plan.plan_id, prepared_input[0], loader(prepared_input), session_factory=factory(server)
        )
        assert result.existing
        assert result.record == winners[0]
        assert result.record.status == "admitted"
        assert not result.record.workflow_latched
        assert not provider.created
        assert provider.create_calls == provider.link_calls == 0
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store).show(plan_id=plan.plan_id)
        assert not view.intents
        assert not view.receipts
        assert view.operation == winners[0]


def test_failed_marker_preserves_old_state_and_reason_without_claiming_unknown(
    prepared_input, certificates, monkeypatch
):
    provider = UploadProvider(
        SCOPE.owner.id, SCOPE.project_id, create_reply=Reply(status=201, body=b'{"success":false}')
    )

    def unavailable(*args, **kwargs):
        raise YorungeError("state_write_failed")

    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(prepared_input, server)
        monkeypatch.setattr(StateUploads, "stop_local", unavailable)
        rejected_call = partial(
            create_link_original,
            plan.plan_id,
            prepared_input[0],
            loader(prepared_input),
            session_factory=factory(server),
        )
        with pytest.raises(OperationError) as raised:
            rejected_call()
        assert raised.value.code == "operation_uncertain"
        assert raised.value.reason_code == "state_write_failed"
        assert raised.value.__cause__ is raised.value.__context__ is None
        assert provider.create_calls == 1
        assert provider.link_calls == 0
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store).show(plan_id=plan.plan_id)
        assert view.operation.status == "running"
        assert view.operation.reason is None
        assert view.operation.operation_id == raised.value.operation_id
        assert not view.receipts


def test_committed_create_receipt_survives_caller_failure_without_new_link(
    prepared_input, certificates, monkeypatch
):
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    original = StateUploads.receipt

    def lost_reply(repository, *args, **kwargs):
        original(repository, *args, **kwargs)
        raise YorungeError("state_write_failed")

    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(prepared_input, server)
        monkeypatch.setattr(StateUploads, "receipt", lost_reply)
        rejected_call = partial(
            create_link_original,
            plan.plan_id,
            prepared_input[0],
            loader(prepared_input),
            session_factory=factory(server),
        )
        with pytest.raises(OperationError) as raised:
            rejected_call()
        assert raised.value.code == "operation_uncertain"
        assert raised.value.reason_code == "state_write_failed"
        assert provider.create_calls == 1
        assert provider.link_calls == 0
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store).show(plan_id=plan.plan_id)
        assert view.operation.status == "unknown"
        assert view.operation.dataset_id == DATASET
        assert len(view.receipts) == 1
        assert type(view.receipts[0]) is CreateReceiptV2


def test_real_task_cancellation_after_create_propagates_with_local_recovery_record(
    prepared_input, certificates, monkeypatch
):
    from yorunge.adapters import upload_original

    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    original = upload_original._Call.execute

    async def cancel_after_response(call, arm):
        await original(call, arm)
        asyncio.current_task().cancel()
        await asyncio.sleep(0)

    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(prepared_input, server)
        monkeypatch.setattr(upload_original._Call, "execute", cancel_after_response)
        rejected_call = partial(
            create_link_original,
            plan.plan_id,
            prepared_input[0],
            loader(prepared_input),
            session_factory=factory(server),
        )
        with pytest.raises(asyncio.CancelledError):
            rejected_call()
        assert provider.create_calls == 1
        assert provider.link_calls == 0
        found = create_link_original(
            plan.plan_id, prepared_input[0], denied, session_factory=denied
        )
        assert found.existing
        assert found.record.status == "unknown"
        assert found.record.dataset_id is None
        assert found.record.lease is None


def test_full_hash_runs_without_holding_a_store_or_writer_lock(
    prepared_input, certificates, monkeypatch
):
    from yorunge.adapters import upload_original

    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    original = upload_original.capture_upload_input
    held = []

    def under_writer_lock(*args, **kwargs):
        with open_existing_store(prepared_input[0]) as store:
            store.connection.execute("BEGIN IMMEDIATE")
            try:
                result = original(*args, **kwargs)
                held.append(True)
                return result
            finally:
                store.connection.rollback()

    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(prepared_input, server)
        monkeypatch.setattr(upload_original, "capture_upload_input", under_writer_lock)
        result = create_link_original(
            plan.plan_id, prepared_input[0], loader(prepared_input), session_factory=factory(server)
        )
        assert result.record.status == "running"
        assert held == [True]


def test_known_current_denial_is_not_an_explicit_attempt_fallback(prepared_input, certificates):
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    budgets = []
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(prepared_input, server)
        before = len(server.requests)
        server.routes["/api/v1/auth/me"] = Reply(status=403, body=b"private-access-denied")
        rejected_call = partial(
            create_link_original,
            plan.plan_id,
            prepared_input[0],
            loader(prepared_input),
            session_factory=factory(server, budgets),
        )
        with pytest.raises(YorungeError) as raised:
            rejected_call()
        assert raised.value.code == "remote_access_denied"
        assert raised.value.exit_code == 3
        assert len(server.requests) == before + 1
        assert provider.create_calls == 0
        assert budgets[0].snapshot().effect_attempts == 0
    with open_existing_store(prepared_input[0]) as store:
        assert StateUploads(store).show(plan_id=plan.plan_id).operation is None


def test_revoke_after_armed_create_preserves_receipt_but_blocks_new_link(
    prepared_input, certificates
):
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(prepared_input, server)

        def revoke():
            with open_existing_store(prepared_input[0]) as store:
                StateUploads(store).revoke(plan.plan_id, plan.digest)

        provider.after_create = revoke
        rejected_call = partial(
            create_link_original,
            plan.plan_id,
            prepared_input[0],
            loader(prepared_input),
            session_factory=factory(server),
        )
        with pytest.raises(OperationError) as raised:
            rejected_call()
        assert raised.value.code == "operation_uncertain"
        assert provider.create_calls == 1
        assert provider.link_calls == 0
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store).show(plan_id=plan.plan_id)
        assert view.approval.status == "revoked"
        assert len(view.receipts) == 1
        assert view.operation.status == "unknown"
        assert view.operation.dataset_id == DATASET
        assert view.intents[0].kind == "create"
        assert len(view.intents) == 1


def test_namespace_race_does_not_mark_another_operations_state(
    prepared_input, certificates, monkeypatch
):
    from yorunge.adapters.platform_upload_reader import ObservedUploadReader

    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    observed = {}
    read_current = ObservedUploadReader.current

    async def capture(reader, client, plan, *args, **kwargs):
        check = await read_current(reader, client, plan, *args, **kwargs)
        observed[plan.plan_id] = check
        return check

    monkeypatch.setattr(ObservedUploadReader, "current", capture)
    with TlsServer(certificates, provider.routes()) as server:
        first = approved(prepared_input, server)
        second = approved(prepared_input, server)
        original_admit = StateUploads.admit
        winners = []

        def race(repository, plan_id, check):
            with open_existing_store(prepared_input[0]) as store:
                competitor = StateUploads(store, repository.credential, clock=repository.clock)
                winner = original_admit(competitor, first.plan_id, observed[first.plan_id])
                competitor.arm(
                    winner.operation_id,
                    winner.lease,
                    observed[first.plan_id],
                    "create",
                    None,
                    total_end=repository.clock.monotonic() + 900,
                )
                winners.append(winner)
            return original_admit(repository, plan_id, check)

        monkeypatch.setattr(StateUploads, "admit", race)
        rejected_call = partial(
            create_link_original,
            second.plan_id,
            prepared_input[0],
            loader(prepared_input),
            session_factory=factory(server),
        )
        with pytest.raises(OperationError) as raised:
            rejected_call()
        assert raised.value.code == "operation_conflict"
        assert raised.value.exit_code == 2
        assert raised.value.operation_id == winners[0].operation_id
        assert provider.create_calls == provider.link_calls == 0
    with open_existing_store(prepared_input[0]) as store:
        winner_view = StateUploads(store).show(plan_id=first.plan_id)
        assert winner_view.operation.status == "running"
        assert winner_view.operation.reason is None
        assert winner_view.operation.lease is not None
        assert len(winner_view.intents) == 1
        assert StateUploads(store).show(plan_id=second.plan_id).operation is None


def test_missing_store_is_not_initialized_and_loader_is_not_called(tmp_path):
    root = tmp_path / "missing"
    rejected_call = partial(
        create_link_original, str(uuid4()), root, denied, session_factory=denied
    )
    with pytest.raises(YorungeError) as raised:
        rejected_call()
    assert raised.value.code == "state_invalid"
    assert not root.exists()
