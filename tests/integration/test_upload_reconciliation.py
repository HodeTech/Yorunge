"""Complete real read-only reconciliation, including current scope and error evidence."""

import asyncio
import time
from datetime import timedelta
from functools import partial

import pytest

from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.http_server import Reply, TlsServer
from tests.fixtures.upload_provider import DATASET, UploadProvider, reply
from tests.integration.test_upload_file_workflow import certificates as certificates
from tests.integration.test_upload_file_workflow import loopback_only as loopback_only
from tests.integration.test_upload_file_workflow import many
from tests.integration.test_upload_original import denied, factory, loader
from tests.integration.test_upload_preparation import ENV, SECRET
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_reconcile_probe import ready
from yorunge import api
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_reconciliation import reconcile_upload
from yorunge.adapters.upload_repository import StateUploads
from yorunge.domain.errors import OperationError


def call(data, server, clock, operation_id, *, accepted=True, budgets=None):
    return partial(
        reconcile_upload,
        operation_id,
        data[0],
        loader(data),
        accept_unverified_read=accepted,
        session_factory=factory(server, budgets),
        clock=clock,
    )


@pytest.mark.parametrize("current_scope", ["same", "rotated", "reset", "profile"])
def test_same_operation_becomes_durable_metadata_success_without_files_or_writes(
    prepared_input, certificates, execution_clock, monkeypatch, current_scope
):
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    budgets, locks = [], []
    data = many(prepared_input) if current_scope == "same" else prepared_input
    with TlsServer(certificates, provider.routes()) as server:
        plan, operation_id = ready(data, server, execution_clock)
        for file in data[2].files:
            (prepared_input[1] / file.path).unlink()
        prepared_input[1].rmdir()
        with open_existing_store(prepared_input[0]) as store:
            before = StateUploads(store).show(operation_id=operation_id)
        if current_scope == "rotated":
            monkeypatch.setenv(ENV, "replacement-read-key")
        elif current_scope == "reset":
            execution_clock.value += timedelta(seconds=901)
            execution_clock.elapsed += 901
            preview = api.preview_identity_reset(state_dir=prepared_input[0]).data
            api.reset_identity(preview.digest, state_dir=prepared_input[0])
        elif current_scope == "profile":
            data = (*data[:3], data[3].model_copy(update={"profile": "readonly"}), data[4])
        provider.upload_allowed = False

        def unlocked():
            with open_existing_store(prepared_input[0]) as store:
                store.connection.execute("BEGIN IMMEDIATE")
                store.connection.rollback()
                locks.append(True)

        provider.on_request = unlocked
        count = len(server.requests)
        phase = call(data, server, execution_clock, operation_id, budgets=budgets)()
        assert phase.record.status == "succeeded" and phase.record.reason == "metadata_verified"
        assert phase.record.operation_id == operation_id and phase.record.lease is None
        assert phase.record.write_owner_id == before.operation.write_owner_id
        assert phase.record.write_access_digest == before.operation.write_access_digest
        assert phase.record.fence > before.operation.fence
        requests = server.requests[count:]
        assert len(requests) == len(locks) == 6 and all(r.method == "GET" for r in requests)
        assert requests[-1].path == f"/api/v1/datasets/{DATASET}/items?limit=128"
        counters = budgets[0].snapshot()
        assert counters.read_requests == counters.read_attempts == 6
        assert counters.effect_attempts == counters.upload_bytes == counters.response_pending == 0
        with open_existing_store(prepared_input[0]) as store:
            view = StateUploads(store).show(operation_id=operation_id)
            assert view.plan == plan and view.receipts == before.receipts
            assert view.intents == before.intents
            assert len(view.receipts) == 2 + 3 * data[2].file_count
            proof = view.verification
            assert proof.grant is None and proof.authorization_policy == "explicit_read_attempt"
            assert len(proof.files) == data[2].file_count
            assert all(
                (actual.size_bytes, actual.sha256) == (expected.size, expected.sha256)
                for actual, expected in zip(proof.files, data[2].files, strict=True)
            )
            if current_scope == "rotated":
                assert proof.scope.credential_revision > plan.scope.credential_revision
            if current_scope == "profile":
                assert proof.scope.profile == "readonly" and plan.scope.profile == "test"
            if current_scope == "reset":
                assert proof.scope.identity_epoch != plan.scope.identity_epoch
            assert store.verify().store_schema_version == 7
        invoke = partial(
            reconcile_upload,
            operation_id,
            prepared_input[0],
            denied,
            accept_unverified_read=True,
            session_factory=denied,
            clock=execution_clock,
        )
        with pytest.raises(OperationError) as terminal:
            invoke()
        assert terminal.value.code == "operation_conflict" and len(server.requests) == count + 6


@pytest.mark.parametrize(
    "failure", ["401", "403", "404", "405", "429", "503", "hash", "total", "secret"]
)
def test_items_failure_keeps_source_error_and_cannot_downgrade_to_execution_failed(
    prepared_input, certificates, execution_clock, failure
):
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    routes = provider.routes()
    with TlsServer(certificates, routes) as server:
        _, operation_id = ready(prepared_input, server, execution_clock)
        path = f"/api/v1/datasets/{DATASET}/items?limit=128"
        if failure.isdigit():
            routes[path] = Reply(status=int(failure), body=b"{}")
        else:
            values = [dict(value) for value in provider.confirmed.values()]
            if failure == "hash":
                values[0]["sha256_hash"] = "0" * 64
            body = {"items": values, "total": 2 if failure == "total" else 1, "next_cursor": None}
            if failure == "secret":
                body["unused"] = SECRET
            routes[path] = reply(body)
        invoke = call(prepared_input, server, execution_clock, operation_id)
        count = len(server.requests)
        with pytest.raises(OperationError) as raised:
            invoke()
        expected = {
            "401": "remote_access_denied",
            "403": "remote_access_denied",
            "429": "remote_rate_limited",
            "503": "remote_failed",
        }.get(failure, "invalid_response")
        assert raised.value.code == expected and raised.value.operation_id == operation_id
        assert raised.value.exit_code == (3 if failure in {"401", "403"} else 1)
        assert raised.value.__cause__ is raised.value.__context__ is None
        assert SECRET not in str(raised.value) and SECRET not in repr(raised.value.envelope())
        assert all(r.method == "GET" for r in server.requests[count:])
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store).show(operation_id=operation_id)
        assert view.operation.status == "unknown" and view.operation.reason == "read_unavailable"
        assert view.operation.lease is None and len(view.receipts) == 5
        assert view.verification is None and store.verify().store_schema_version == 7


def test_real_cancel_after_read_acquire_releases_lease_and_propagates(
    prepared_input, certificates, execution_clock, monkeypatch
):
    from yorunge.adapters.platform_upload_port import ObservedUploadPort

    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    original = ObservedUploadPort.items

    async def items(port, *args, **kwargs):
        asyncio.current_task().cancel()
        return await original(port, *args, **kwargs)

    with TlsServer(certificates, provider.routes()) as server:
        _, operation_id = ready(prepared_input, server, execution_clock)
        monkeypatch.setattr(ObservedUploadPort, "items", items)
        invoke = call(prepared_input, server, execution_clock, operation_id)
        with pytest.raises(asyncio.CancelledError):
            invoke()
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store).show(operation_id=operation_id)
        assert view.operation.status == "unknown" and view.operation.lease is None
        assert view.operation.reason == "request_uncertain" and view.verification is None
        assert len(view.receipts) == 5 and store.verify().store_schema_version == 7


@pytest.mark.parametrize("changed", ["owner", "scope", "authorization"])
def test_post_acquire_change_closes_before_items_and_proof(
    prepared_input, certificates, execution_clock, monkeypatch, changed
):
    from uuid import uuid4

    from yorunge.adapters.upload_reconciliation import _ReadEnvironment

    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    original, counts = _ReadEnvironment.acquire, []

    def acquire(environment, check):
        original(environment, check)
        counts.append(len(server.requests))
        if changed == "owner":
            environment.owner = environment.owner.model_copy(update={"owner_id": str(uuid4())})
        elif changed == "scope":
            preview = api.preview_identity_reset(state_dir=prepared_input[0]).data
            result = api.reset_identity(preview.digest, state_dir=prepared_input[0])
            assert result.data.identity_epoch != environment.scope.identity_epoch
        else:
            execution_clock.value += timedelta(seconds=31)
            execution_clock.elapsed += 31

    with TlsServer(certificates, provider.routes()) as server:
        _, operation_id = ready(prepared_input, server, execution_clock)
        monkeypatch.setattr(_ReadEnvironment, "acquire", acquire)
        invoke = call(prepared_input, server, execution_clock, operation_id)
        with pytest.raises(OperationError) as raised:
            invoke()
        assert raised.value.exit_code == 2 and raised.value.operation_id == operation_id
        expected = "upload_plan_not_valid" if changed == "authorization" else "operation_lease_lost"
        assert raised.value.code == expected
        assert counts == [len(server.requests)]
        assert raised.value.__cause__ is raised.value.__context__ is None
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store).show(operation_id=operation_id)
        assert view.operation.status == "unknown" and view.verification is None
        assert len(view.receipts) == 5 and store.verify().store_schema_version == 7


def test_items_age_cannot_refresh_authorization_or_create_stale_proof(
    prepared_input, certificates, execution_clock
):
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    routes = provider.routes()

    def delayed(request, count):
        execution_clock.value += timedelta(seconds=31)
        execution_clock.elapsed += 31
        return provider.items(request, count)

    with TlsServer(certificates, routes) as server:
        _, operation_id = ready(prepared_input, server, execution_clock)
        routes[f"/api/v1/datasets/{DATASET}/items?limit=128"] = delayed
        invoke = call(prepared_input, server, execution_clock, operation_id)
        with pytest.raises(OperationError) as raised:
            invoke()
        assert raised.value.code == "upload_plan_not_valid" and raised.value.exit_code == 2
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store).show(operation_id=operation_id)
        assert view.verification is None and view.operation.lease is None
        assert store.verify().store_schema_version == 7


@pytest.mark.parametrize("committed", [False, True])
def test_read_proof_commit_and_reply_windows_preserve_same_record(
    prepared_input, certificates, execution_clock, monkeypatch, committed
):
    from yorunge.domain.errors import YorungeError

    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    if committed:
        original = StateUploads.verified

        def after(repository, *args, **kwargs):
            original(repository, *args, **kwargs)
            raise OSError("read proof reply lost")

        monkeypatch.setattr(StateUploads, "verified", after)
    else:
        original = StateUploads._control

        def before(repository, *args, **kwargs):
            original(repository, *args, **kwargs)
            if kwargs.get("proof") is not None:
                raise YorungeError("state_write_failed")

        monkeypatch.setattr(StateUploads, "_control", before)
    with TlsServer(certificates, provider.routes()) as server:
        _, operation_id = ready(prepared_input, server, execution_clock)
        invoke = call(prepared_input, server, execution_clock, operation_id)
        with pytest.raises(OperationError) as raised:
            invoke()
        assert raised.value.code == "state_write_failed" and raised.value.exit_code == 2
        assert raised.value.operation_id == operation_id
        assert raised.value.__cause__ is raised.value.__context__ is None
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store).show(operation_id=operation_id)
        assert view.operation.status == ("succeeded" if committed else "unknown")
        assert (view.verification is not None) == committed
        assert len(view.receipts) == 5 and view.operation.lease is None
        assert store.verify().store_schema_version == 7


@pytest.mark.parametrize("window", ["before_store", "before_commit", "after_commit"])
def test_total_read_budget_is_enforced_through_proof_publication(
    prepared_input, certificates, execution_clock, monkeypatch, window
):
    from yorunge.adapters.upload_reconciliation import _ReadEnvironment

    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    if window == "before_store":
        original = _ReadEnvironment.commit

        def commit(environment, proof):
            environment.reader._budget._end = time.monotonic() - 1
            return original(environment, proof)

        monkeypatch.setattr(_ReadEnvironment, "commit", commit)
    elif window == "before_commit":
        original = StateUploads._control

        def control(repository, *args, **kwargs):
            original(repository, *args, **kwargs)
            if kwargs.get("proof") is not None:
                execution_clock.elapsed += 31

        monkeypatch.setattr(StateUploads, "_control", control)
    else:
        original = StateUploads._finish

        def finish(repository, *args, **kwargs):
            original(repository, *args, **kwargs)
            if repository.connection.execute(
                "SELECT count(*) FROM upload_verifications"
            ).fetchone()[0]:
                execution_clock.elapsed += 31

        monkeypatch.setattr(StateUploads, "_finish", finish)
    with TlsServer(certificates, provider.routes()) as server:
        _, operation_id = ready(prepared_input, server, execution_clock)
        invoke = call(prepared_input, server, execution_clock, operation_id)
        with pytest.raises(OperationError) as raised:
            invoke()
        assert raised.value.code == "execution_timeout" and raised.value.exit_code == 2
        assert raised.value.operation_id == operation_id
        assert raised.value.__cause__ is raised.value.__context__ is None
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store).show(operation_id=operation_id)
        assert (view.verification is not None) == (window == "after_commit")
        assert view.operation.status == ("succeeded" if window == "after_commit" else "unknown")
        assert len(view.receipts) == 5 and store.verify().store_schema_version == 7


def test_read_acquisition_loser_cannot_release_the_winners_lease(
    prepared_input, certificates, execution_clock, monkeypatch
):
    from yorunge.adapters.upload_reconciliation import _ReadEnvironment

    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    original, winner = _ReadEnvironment.acquire, []

    def raced(environment, check):
        with environment.repository() as repository:
            winner.append(
                repository.acquire_read(
                    environment.record.operation_id,
                    authorization=check,
                    accept_unverified_read=True,
                )
            )
        original(environment, check)

    with TlsServer(certificates, provider.routes()) as server:
        _, operation_id = ready(prepared_input, server, execution_clock)
        monkeypatch.setattr(_ReadEnvironment, "acquire", raced)
        invoke = call(prepared_input, server, execution_clock, operation_id)
        count = len(server.requests)
        with pytest.raises(OperationError) as raised:
            invoke()
        assert (
            raised.value.code == "operation_conflict" and raised.value.operation_id == operation_id
        )
        assert len(server.requests) == count + 5
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store).show(operation_id=operation_id)
        assert len(winner) == 1 and view.operation.lease == winner[0]
        assert view.verification is None and view.operation.status == "unknown"
        assert store.verify().store_schema_version == 7
