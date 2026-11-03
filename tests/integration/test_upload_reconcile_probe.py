"""Real readonly probe with deferred credentials and no source/lease/proof creation."""

import asyncio
import pickle
from datetime import timedelta
from uuid import uuid4

import pytest

from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.http_server import Reply, TlsServer
from tests.fixtures.upload_provider import DATASET, UploadProvider
from tests.integration.test_upload_file_workflow import certificates as certificates
from tests.integration.test_upload_file_workflow import loopback_only as loopback_only
from tests.integration.test_upload_original import denied, factory, loader
from tests.integration.test_upload_preparation import ENV, SECRET, approve, prepare, runtime
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from yorunge import api
from yorunge.adapters.secrets import EnvSecretReader
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_original import upload_files_original
from yorunge.adapters.upload_reconciliation import probe_reconciliation
from yorunge.adapters.upload_repository import StateUploads
from yorunge.domain.errors import OperationError, YorungeError


def ready(data, server, clock):
    preparation = runtime(data, server, clock=clock)
    plan = prepare(preparation, data)
    approve(preparation, plan)
    result = upload_files_original(
        plan.plan_id, data[0], loader(data), session_factory=factory(server), clock=clock
    )
    clock.value += timedelta(seconds=151)
    clock.elapsed += 151
    with open_existing_store(data[0]) as store:
        StateUploads(store, clock=clock).cleanup_expired(result.record.operation_id)
    return plan, result.record.operation_id


def test_real_probe_has_one_secret_five_reads_and_no_source_or_ownership_mutation(
    prepared_input, certificates, execution_clock, monkeypatch
):
    provider, budgets, secrets, locks = UploadProvider(SCOPE.owner.id, SCOPE.project_id), [], [], []
    with TlsServer(certificates, provider.routes()) as server:
        plan, operation_id = ready(prepared_input, server, execution_clock)
        (prepared_input[1] / "one.bin").unlink()
        prepared_input[1].rmdir()
        provider.upload_allowed = False
        before = len(server.requests)
        original_read = EnvSecretReader.read

        def secret(reader, reference):
            secrets.append(reference)
            return original_read(reader, reference)

        def unlocked():
            with open_existing_store(prepared_input[0]) as store:
                store.connection.execute("BEGIN IMMEDIATE")
                store.connection.rollback()
                locks.append(True)

        monkeypatch.setattr(EnvSecretReader, "read", secret)
        provider.on_request = unlocked
        with open_existing_store(prepared_input[0]) as store:
            previous = StateUploads(store).show(operation_id=operation_id)
        phase = probe_reconciliation(
            operation_id,
            prepared_input[0],
            loader(prepared_input),
            accept_unverified_read=True,
            session_factory=factory(server, budgets),
            clock=execution_clock,
        )
        assert phase.plan == plan and phase.record == previous.operation
        assert phase.authorization.outcome == "not_exposed" and phase.authorization.grant is None
        assert phase.authorization.dataset_id == DATASET and len(secrets) == 1
        requests = server.requests[before:]
        assert len(requests) == len(locks) == 5 and all(r.method == "GET" for r in requests)
        assert not any("/items?" in r.path or r.path.endswith("/my-role") for r in requests)
        counts = budgets[0].snapshot()
        assert counts.read_requests == counts.read_attempts == 5
        assert counts.effect_attempts == counts.upload_bytes == counts.response_pending == 0
        with open_existing_store(prepared_input[0]) as store:
            assert StateUploads(store).show(operation_id=operation_id) == previous
            assert store.verify().store_schema_version == 7
    assert provider.owner_id not in repr(phase) and DATASET not in repr(phase)
    with pytest.raises(TypeError):
        pickle.dumps(phase)


def test_full_id_flag_false_skips_loader_and_leaves_operation_unchanged(
    prepared_input, certificates, execution_clock, monkeypatch
):
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        _, operation_id = ready(prepared_input, server, execution_clock)
        count = len(server.requests)
        monkeypatch.setattr(EnvSecretReader, "read", denied)
        with open_existing_store(prepared_input[0]) as store:
            previous = StateUploads(store).show(operation_id=operation_id)
        with pytest.raises(OperationError) as raised:
            probe_reconciliation(
                operation_id,
                prepared_input[0],
                denied,
                session_factory=denied,
                clock=execution_clock,
            )
        assert raised.value.code == "approval_required" and raised.value.exit_code == 4
        assert raised.value.__cause__ is raised.value.__context__ is None
        assert len(server.requests) == count
        with open_existing_store(prepared_input[0]) as store:
            assert StateUploads(store).show(operation_id=operation_id) == previous


@pytest.mark.parametrize("changed_profile", [False, True])
def test_current_key_and_explicit_profile_can_change_without_rewriting_history(
    prepared_input, certificates, execution_clock, monkeypatch, changed_profile
):
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        plan, operation_id = ready(prepared_input, server, execution_clock)
        monkeypatch.setenv(ENV, "new-read-credential-canary")
        data = prepared_input
        if changed_profile:
            data = (*data[:3], data[3].model_copy(update={"profile": "readonly"}), data[4])
        count = len(server.requests)
        result = probe_reconciliation(
            operation_id,
            data[0],
            loader(data),
            accept_unverified_read=True,
            session_factory=factory(server),
            clock=execution_clock,
        )
        scope = result.authorization.scope
        assert scope.credential_revision > plan.scope.credential_revision
        assert scope.profile == ("readonly" if changed_profile else plan.scope.profile)
        assert all(
            r.header("x-api-key") == "new-read-credential-canary" for r in server.requests[count:]
        )
        with open_existing_store(data[0]) as store:
            view = StateUploads(store).show(operation_id=operation_id)
            assert (
                view.plan == plan and view.operation.write_owner_id == result.record.write_owner_id
            )
            assert view.verification is None and view.operation.lease is None
            assert store.verify().store_schema_version == 7


@pytest.mark.parametrize("status", [401, 403, 404, 405, 429, 503])
def test_mandatory_read_source_error_keeps_its_code_and_read_unavailable_marker(
    prepared_input, certificates, execution_clock, status
):
    codes = {
        401: "remote_access_denied",
        403: "remote_access_denied",
        404: "invalid_response",
        405: "invalid_response",
        429: "remote_rate_limited",
        503: "remote_failed",
    }
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    routes = provider.routes()
    with TlsServer(certificates, routes) as server:
        _, operation_id = ready(prepared_input, server, execution_clock)
        before = len(server.requests)
        routes["/api/v1/datasets/test-user/test-dataset"] = Reply(status=status, body=b"{}")
        with pytest.raises(OperationError) as raised:
            probe_reconciliation(
                operation_id,
                prepared_input[0],
                loader(prepared_input),
                accept_unverified_read=True,
                session_factory=factory(server),
                clock=execution_clock,
            )
        assert raised.value.code == codes[status] and raised.value.exit_code == (
            3 if status < 404 else 1
        )
        assert raised.value.operation_id == operation_id
        assert raised.value.__cause__ is raised.value.__context__ is None
        assert all(r.method == "GET" for r in server.requests[before:])
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store).show(operation_id=operation_id)
        assert view.operation.status == "unknown" and view.operation.reason == "read_unavailable"
        assert view.operation.lease is None and len(view.receipts) == 5
        assert view.verification is None and store.verify().store_schema_version == 7


def test_active_loop_fails_before_local_store_or_loader(prepared_input):
    async def run():
        with pytest.raises(YorungeError) as raised:
            probe_reconciliation("bad", prepared_input[0], denied)
        assert raised.value.code == "invalid_request"

    asyncio.run(run())


def test_reset_and_expired_write_approval_do_not_rewrite_baseline_or_block_explicit_read(
    prepared_input, certificates, execution_clock
):
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        plan, operation_id = ready(prepared_input, server, execution_clock)
        execution_clock.value += timedelta(seconds=901)
        execution_clock.elapsed += 901
        with open_existing_store(prepared_input[0]) as store:
            before = StateUploads(store).show(operation_id=operation_id)
        preview = api.preview_identity_reset(state_dir=prepared_input[0]).data
        api.reset_identity(preview.digest, state_dir=prepared_input[0])
        phase = probe_reconciliation(
            operation_id,
            prepared_input[0],
            loader(prepared_input),
            accept_unverified_read=True,
            session_factory=factory(server),
            clock=execution_clock,
        )
        assert phase.authorization.scope.identity_epoch != plan.scope.identity_epoch
        assert phase.authorization.grant is None and phase.plan == plan
        with open_existing_store(prepared_input[0]) as store:
            view = StateUploads(store).show(operation_id=operation_id)
            assert view.receipts == before.receipts and view.plan == before.plan
            assert view.operation.lease is None and view.verification is None
            assert store.verify().store_schema_version == 7


def test_current_target_mismatch_is_state_changed_before_secret_or_network(
    prepared_input, certificates, execution_clock, monkeypatch
):
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        _, operation_id = ready(prepared_input, server, execution_clock)
        data = prepared_input
        context = data[3].model_copy(update={"platform_url": "https://other.example/api/v1"})
        profile = data[4].model_copy(update={"platform_url": "https://other.example/api/v1"})
        count = len(server.requests)
        monkeypatch.setattr(EnvSecretReader, "read", denied)
        with pytest.raises(OperationError) as raised:
            probe_reconciliation(
                operation_id,
                data[0],
                lambda plan: (context, profile),
                accept_unverified_read=True,
                session_factory=denied,
                clock=execution_clock,
            )
        assert raised.value.code == "state_changed" and raised.value.operation_id == operation_id
        assert raised.value.__cause__ is raised.value.__context__ is None
        assert len(server.requests) == count


def test_actual_cancel_during_probe_closes_session_without_changing_execution_state(
    prepared_input, certificates, execution_clock, monkeypatch
):
    from yorunge.adapters.upload_reconciliation import _ReadEnvironment

    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    original = _ReadEnvironment.observe

    async def observe(environment):
        task = asyncio.current_task()
        provider.on_request = lambda: task.get_loop().call_soon_threadsafe(task.cancel)
        return await original(environment)

    with TlsServer(certificates, provider.routes()) as server:
        _, operation_id = ready(prepared_input, server, execution_clock)
        with open_existing_store(prepared_input[0]) as store:
            before = StateUploads(store).show(operation_id=operation_id)
        count = len(server.requests)
        monkeypatch.setattr(_ReadEnvironment, "observe", observe)
        with pytest.raises(asyncio.CancelledError):
            probe_reconciliation(
                operation_id,
                prepared_input[0],
                loader(prepared_input),
                accept_unverified_read=True,
                session_factory=factory(server),
                clock=execution_clock,
            )
        assert len(server.requests) == count + 1
        assert server.requests[-1].method == "GET"
    with open_existing_store(prepared_input[0]) as store:
        assert StateUploads(store).show(operation_id=operation_id) == before
        assert store.verify().store_schema_version == 7


def test_missing_store_never_initializes_or_loads_context(tmp_path, monkeypatch):
    missing = tmp_path / "missing"
    monkeypatch.setattr(EnvSecretReader, "read", denied)
    with pytest.raises(OperationError) as raised:
        probe_reconciliation(
            str(uuid4()), missing, denied, accept_unverified_read=True, session_factory=denied
        )
    assert raised.value.code == "state_invalid" and not missing.exists()
    assert raised.value.__cause__ is raised.value.__context__ is None


def test_discarded_provider_metadata_secret_never_reaches_error_chain_or_repr(
    prepared_input, certificates, execution_clock
):
    from tests.fixtures.upload_provider import reply

    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    routes = provider.routes()
    with TlsServer(certificates, routes) as server:
        _, operation_id = ready(prepared_input, server, execution_clock)
        routes["/api/v1/datasets/test-user/test-dataset"] = lambda request, count: reply(
            {**provider.dataset(), "unused": {"nested": SECRET}}
        )
        with pytest.raises(OperationError) as raised:
            probe_reconciliation(
                operation_id,
                prepared_input[0],
                loader(prepared_input),
                accept_unverified_read=True,
                session_factory=factory(server),
                clock=execution_clock,
            )
        assert raised.value.code == "invalid_response" and raised.value.exit_code == 1
        assert SECRET not in str(raised.value) and SECRET not in repr(raised.value.envelope())
        assert raised.value.__cause__ is raised.value.__context__ is None
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store).show(operation_id=operation_id)
        assert view.operation.reason == "read_unavailable" and view.operation.lease is None
        assert len(view.receipts) == 5 and view.verification is None
        assert store.verify().store_schema_version == 7
