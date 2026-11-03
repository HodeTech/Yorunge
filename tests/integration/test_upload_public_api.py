"""Public API uses real config/env/state/files/TLS, without caller-supplied proofs or clients."""

import asyncio
import io
from datetime import UTC, datetime
from functools import partial

import pytest

from tests.contracts.test_platform_upload_codec import PARAMETERS, SCOPE
from tests.fixtures.http_server import Reply, TlsServer
from tests.fixtures.upload_provider import DATASET, UploadProvider
from tests.integration.test_upload_file_workflow import many
from tests.integration.test_upload_journal import journal as journal
from tests.integration.test_upload_original import factory
from tests.integration.test_upload_preparation import ENV
from tests.integration.test_upload_preparation import certificates as certificates
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from yorunge import api
from yorunge.adapters import upload_api
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_original import run_upload_original
from yorunge.adapters.upload_preparation import UploadPreparationRuntime
from yorunge.adapters.upload_reconciliation import reconcile_upload
from yorunge.adapters.upload_repository import StateUploads
from yorunge.cli.output import OutputRenderer
from yorunge.domain.errors import OperationError, YorungeError


@pytest.fixture
def public_inputs(prepared_input, execution_clock):
    execution_clock.value = datetime.now(UTC)
    state, root, manifest, _, _ = prepared_input
    artifact, config = root.parent / "manifest.json", root.parent / "upload.toml"
    artifact.write_bytes(manifest.encoded())
    config.write_text(f'''schema_version = 1
active_profile = "other"
[profiles.test]
platform_key_env = "{ENV}"
project_id = "{SCOPE.project_id}"
[profiles.other]
platform_key_env = "DO_NOT_USE_THIS_ENV"
[profiles.current]
platform_key_env = "{ENV}"
''')
    return prepared_input, artifact, config


def seam(monkeypatch, server, clock, budgets):
    build = factory(server, budgets)

    def runtime(context, profile, state_dir):
        return UploadPreparationRuntime(
            context, profile, state_dir, session_factory=build, clock=clock
        )

    monkeypatch.setattr(upload_api, "UploadPreparationRuntime", runtime)
    monkeypatch.setattr(upload_api, "SystemClock", lambda: clock)
    monkeypatch.setattr(
        upload_api,
        "run_upload_original",
        partial(run_upload_original, session_factory=build, clock=clock),
    )
    monkeypatch.setattr(
        upload_api,
        "reconcile_upload",
        partial(reconcile_upload, session_factory=build, clock=clock),
    )


def prepare(inputs, **changes):
    data, artifact, config = inputs
    options = dict(
        manifest=artifact,
        owner=SCOPE.owner,
        parameters=PARAMETERS,
        project=SCOPE.project_id,
        config=config,
        profile="test",
        state_dir=data[0],
        admission_policy="explicit_attempt",
        unpriced=True,
    )
    return api.prepare_dataset_upload(data[1], **(options | changes))


def approve(inputs, plan, **changes):
    options = dict(
        config=inputs[2],
        state_dir=inputs[0][0],
        accept_unverified_authority=True,
        accept_unpriced_cost=True,
    )
    return api.approve_dataset_upload(plan.plan_id, plan.plan_digest, **(options | changes))


def test_public_plan_review_approve_start_complete_flow_and_local_restart(
    public_inputs, certificates, execution_clock, monkeypatch
):
    data, artifact, config = public_inputs
    data = many(data)
    artifact.write_bytes(data[2].encoded())
    inputs = data, artifact, config
    provider, budgets = UploadProvider(SCOPE.owner.id, SCOPE.project_id), []
    with TlsServer(certificates, provider.routes()) as server:
        seam(monkeypatch, server, execution_clock, budgets)
        plan = prepare(inputs).data
        assert plan.plan_status == "attempt_ready"
        assert plan.operation_id is None
        assert plan.risks == ("authority_unverified", "cost_unverified")
        chosen = api.review_dataset_upload(plan.plan_id, state_dir=data[0]).data
        assert chosen.manifest.file_count == 3
        assert chosen.target.profile == "test"
        approved = approve(inputs, plan).data
        assert approved.approval_status == "approved"
        # Saved profile, rather than active_profile=other, selects the credential.
        result = api.start_dataset_upload(plan.plan_id, config=config, state_dir=data[0])
        value = result.data
        assert value.operation_status == "succeeded"
        assert value.dataset_id == DATASET
        assert value.verification_level == "metadata"
        assert not value.authority_verified
        assert not value.remote_bytes_verified
        assert result.operation_id is None
        assert len(budgets) == 3
        assert [b.snapshot().read_requests for b in budgets] == [2, 2, 18]
        assert budgets[-1].snapshot().effect_attempts == 11
        assert budgets[-1].snapshot().upload_bytes == data[2].total_bytes
        count = len(server.requests)
        for file in data[2].files:
            (data[1] / file.path).unlink()
        data[1].rmdir()
        artifact.unlink()
        monkeypatch.delenv(ENV)
        config.unlink()
        found = api.start_dataset_upload(
            plan.plan_id, config=config, profile="missing", state_dir=data[0]
        )
        assert found == result
        assert len(server.requests) == count
        for output in ("json", "ndjson"):
            stdout = io.StringIO()
            renderer = OutputRenderer(output, stdout=stdout, operation_id=value.operation_id)
            renderer.result(result)
            assert DATASET in stdout.getvalue()
            assert "created_dataset" not in stdout.getvalue()
    with open_existing_store(data[0]) as store:
        view = StateUploads(store).show(operation_id=value.operation_id)
        assert len(view.receipts) == len(view.intents) == 11
        assert view.verification.grant is None
        assert store.verify().store_schema_version == 7


def test_public_same_id_read_recovery_after_write_metadata_failure_and_rotation(
    public_inputs, certificates, execution_clock, monkeypatch
):
    data, artifact, config = public_inputs
    provider, budgets = UploadProvider(SCOPE.owner.id, SCOPE.project_id), []
    routes = provider.routes()
    item_path = f"/api/v1/datasets/{DATASET}/items?limit=128"
    original = routes[item_path]
    routes[item_path] = Reply(status=503)
    with TlsServer(certificates, routes) as server:
        seam(monkeypatch, server, execution_clock, budgets)
        plan = prepare(public_inputs).data
        approve(public_inputs, plan)
        start = partial(api.start_dataset_upload, plan.plan_id, config=config, state_dir=data[0])
        with pytest.raises(OperationError) as raised:
            start()
        assert raised.value.code == "operation_uncertain"
        assert raised.value.exit_code == 5
        operation_id = raised.value.operation_id
        assert operation_id is not None
        assert raised.value.__cause__ is raised.value.__context__ is None
        for file in data[2].files:
            (data[1] / file.path).unlink()
        data[1].rmdir()
        artifact.unlink()
        monkeypatch.setenv(ENV, "synthetic-rotated-public-key")
        before = len(server.requests)
        recover = partial(
            api.reconcile_dataset_upload,
            operation_id,
            config=config,
            profile="current",
            state_dir=data[0],
        )
        with pytest.raises(YorungeError) as denied:
            recover()
        assert denied.value.code == "approval_required"
        assert len(server.requests) == before
        with pytest.raises(OperationError) as read_error:
            recover(accept_unverified_read=True)
        assert read_error.value.code == "remote_failed"
        assert read_error.value.exit_code == 1
        assert read_error.value.operation_id == operation_id
        assert read_error.value.__cause__ is read_error.value.__context__ is None
        routes[item_path] = original
        value = recover(accept_unverified_read=True).data
        assert value.operation_id == operation_id
        assert value.operation_status == "succeeded"
        assert value.verification_level == "metadata"
        assert not value.authority_verified
        assert len(server.requests) == before + 13
        assert budgets[-2].snapshot().read_requests == 6
        assert budgets[-2].snapshot().read_attempts == 7
        assert budgets[-1].snapshot().read_requests == budgets[-1].snapshot().read_attempts == 6
        assert all(r.method == "GET" for r in server.requests[before:])
        assert provider.create_calls == provider.link_calls == provider.put_calls == 1
        assert provider.confirm_calls == 1
    with open_existing_store(data[0]) as store:
        view = StateUploads(store).show(operation_id=operation_id)
        assert view.verification.scope.profile == "current"
        assert view.verification.scope.credential_revision > view.plan.scope.credential_revision
        assert len(view.receipts) == 5
        assert store.verify().store_schema_version == 7


@pytest.mark.parametrize(
    "failure,code", [("digest", "upload_plan_not_valid"), ("ack", "approval_required")]
)
def test_public_approval_rejection_precedes_config_env_and_network(
    public_inputs, certificates, execution_clock, monkeypatch, failure, code
):
    data, _, config = public_inputs
    provider, budgets = UploadProvider(SCOPE.owner.id, SCOPE.project_id), []
    with TlsServer(certificates, provider.routes()) as server:
        seam(monkeypatch, server, execution_clock, budgets)
        plan = prepare(public_inputs).data
        count = len(server.requests)
        config.unlink()
        monkeypatch.delenv(ENV)
        digest = "a" * 64 if failure == "digest" else plan.plan_digest
        invoke = partial(
            api.approve_dataset_upload,
            plan.plan_id,
            digest,
            config=config,
            state_dir=data[0],
            accept_unpriced_cost=True,
            accept_unverified_authority=failure != "ack",
        )
        with pytest.raises(YorungeError) as raised:
            invoke()
        assert raised.value.code == code
        assert raised.value.__context__ is None
        assert len(server.requests) == count


@pytest.mark.parametrize(
    "options",
    [
        {"budget_cr": "200", "unpriced": False},
        {"budget_cr": "200", "unpriced": False, "admission_policy": "verified_only"},
    ],
)
def test_default_or_numeric_budget_does_not_fabricate_authority_or_price(
    public_inputs, certificates, execution_clock, monkeypatch, options
):
    provider, budgets = UploadProvider(SCOPE.owner.id, SCOPE.project_id), []
    with TlsServer(certificates, provider.routes()) as server:
        seam(monkeypatch, server, execution_clock, budgets)
        value = prepare(public_inputs, **options).data
        assert value.plan_status == "draft"
        assert value.cost_bound is None
        assert value.budget_micros == 200_000_000
        assert "cost_unverified" in value.blockers
        if value.admission_policy == "verified_only":
            assert "authority_unverified" in value.blockers
        invoke = partial(
            api.start_dataset_upload,
            value.plan_id,
            config=public_inputs[2],
            state_dir=public_inputs[0][0],
        )
        count = len(server.requests)
        with pytest.raises(YorungeError) as raised:
            invoke()
        assert raised.value.code == "upload_plan_not_valid"
        assert len(server.requests) == count


def test_public_local_metadata_secret_is_rejected_before_any_http(
    public_inputs, certificates, execution_clock, monkeypatch
):
    from tests.integration.test_upload_http_budget import SECRET

    provider, budgets = UploadProvider(SCOPE.owner.id, SCOPE.project_id), []
    with TlsServer(certificates, provider.routes()) as server:
        seam(monkeypatch, server, execution_clock, budgets)
        parameters = PARAMETERS.model_copy(update={"name": SECRET})
        invoke = partial(prepare, public_inputs, parameters=parameters)
        with pytest.raises(YorungeError) as raised:
            invoke()
        assert raised.value.code == "invalid_request"
        assert not server.requests
        assert SECRET not in str(raised.value)
        assert raised.value.__cause__ is raised.value.__context__ is None
    with open_existing_store(public_inputs[0][0]) as store:
        assert store.connection.execute("SELECT count(*) FROM upload_plans").fetchone() == (0,)
        assert store.connection.execute("SELECT count(*) FROM upload_operations").fetchone() == (0,)


def test_public_read_propagates_real_task_cancellation_and_releases_only_its_read_lease(
    public_inputs, certificates, execution_clock, monkeypatch
):
    from yorunge.adapters.platform_upload_port import ObservedUploadPort

    data, _, config = public_inputs
    provider, budgets = UploadProvider(SCOPE.owner.id, SCOPE.project_id), []
    routes = provider.routes()
    item_path = f"/api/v1/datasets/{DATASET}/items?limit=128"
    routes[item_path] = Reply(status=503)
    with TlsServer(certificates, routes) as server:
        seam(monkeypatch, server, execution_clock, budgets)
        plan = prepare(public_inputs).data
        approve(public_inputs, plan)
        start = partial(api.start_dataset_upload, plan.plan_id, config=config, state_dir=data[0])
        with pytest.raises(OperationError) as failed:
            start()
        operation_id = failed.value.operation_id

        async def cancel(port, *args, **kwargs):
            asyncio.current_task().cancel()
            await asyncio.sleep(0)

        monkeypatch.setattr(ObservedUploadPort, "items", cancel)
        before = len(server.requests)
        recover = partial(
            api.reconcile_dataset_upload,
            operation_id,
            config=config,
            state_dir=data[0],
            accept_unverified_read=True,
        )
        with pytest.raises(asyncio.CancelledError):
            recover()
        assert len(server.requests) == before + 5
        assert all(r.method == "GET" for r in server.requests[before:])
    with open_existing_store(data[0]) as store:
        view = StateUploads(store).show(operation_id=operation_id)
        assert view.operation.status == "unknown"
        assert view.operation.lease is None
        assert len(view.receipts) == 5
        assert view.verification is None
        assert store.verify().store_schema_version == 7


@pytest.mark.parametrize(
    "state,code",
    [
        ("admitted", "operation_conflict"),
        ("running", "operation_uncertain"),
        ("unknown", "operation_uncertain"),
        ("cancelled", "operation_conflict"),
        ("failed", "operation_conflict"),
    ],
)
def test_public_existing_start_is_local_but_not_a_false_delivery_success(
    journal, tmp_path, state, code
):
    record = journal.approved()
    if state in {"running", "unknown", "failed"}:
        intent, _, _ = journal.arm(record)
    if state == "failed":
        journal.accept(record, intent, rejected=True)
    elif state in {"unknown", "cancelled"}:
        with open_existing_store(journal.root) as store:
            journal.repository(store).stop_local(
                record.operation_id,
                record.lease,
                "request_uncertain" if state == "unknown" else "local_cancelled",
            )
    with open_existing_store(journal.root) as store:
        before = StateUploads(store).show(operation_id=record.operation_id)
    invoke = partial(
        api.start_dataset_upload,
        journal.plan.plan_id,
        state_dir=journal.root,
        config=tmp_path / "missing.toml",
        profile="missing-profile",
    )
    with pytest.raises(OperationError) as raised:
        invoke()
    assert raised.value.code == code
    assert raised.value.operation_id == record.operation_id
    assert raised.value.__cause__ is raised.value.__context__ is None
    with open_existing_store(journal.root) as store:
        assert StateUploads(store).show(operation_id=record.operation_id) == before


def test_actual_sigint_after_coordinator_result_keeps_the_known_operation_id(tmp_path, monkeypatch):
    import signal

    from tests.integration.test_upload_versioned_history import install_fixture
    from yorunge.adapters.state import open_store

    root = tmp_path / "state"
    with open_store(root) as store:
        data = install_fixture(store)
    identity, plan_id = data["record"]["operation_id"], data["plan"]["plan_id"]

    def interrupt(*args, **kwargs):
        signal.raise_signal(signal.SIGINT)
        raise AssertionError("SIGINT was not raised")

    monkeypatch.setattr(upload_api, "show_upload", interrupt)
    invoke = partial(api.start_dataset_upload, plan_id, state_dir=root)
    with pytest.raises(OperationError) as raised:
        invoke()
    assert raised.value.code == "request_cancelled"
    assert raised.value.operation_id == identity
    assert raised.value.__cause__ is raised.value.__context__ is None
    assert api.show_dataset_upload(operation_id=identity, state_dir=root).data.operation_status == (
        "succeeded"
    )
