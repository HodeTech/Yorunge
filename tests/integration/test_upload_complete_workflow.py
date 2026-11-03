"""Real original workflow reaches only a durable metadata-level result."""

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest

from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.http_server import Reply, TlsServer
from tests.fixtures.upload_provider import DATASET, UploadProvider, reply
from tests.integration.test_upload_file_workflow import certificates as certificates
from tests.integration.test_upload_file_workflow import loopback_only as loopback_only
from tests.integration.test_upload_file_workflow import many
from tests.integration.test_upload_original import approved, denied, factory, loader
from tests.integration.test_upload_preparation import approve, prepare, runtime
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_original import run_upload_original
from yorunge.adapters.upload_repository import StateUploads
from yorunge.domain.errors import OperationError, YorungeError


@pytest.mark.parametrize("multiple", [False, True])
def test_complete_original_writes_exact_graph_and_durable_metadata_proof(
    prepared_input, certificates, multiple
):
    data = many(prepared_input) if multiple else prepared_input
    provider, budgets = UploadProvider(SCOPE.owner.id, SCOPE.project_id), []
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(data, server)
        before = len(server.requests)
        result = run_upload_original(
            plan.plan_id, data[0], loader(data), session_factory=factory(server, budgets)
        )
        assert result.record.status == "succeeded" and result.record.reason == "metadata_verified"
        assert result.record.lease is None and not result.existing
        gets = [r for r in server.requests[before:] if r.method == "GET"]
        assert len(gets) == 18 and gets[-1].path == f"/api/v1/datasets/{DATASET}/items?limit=128"
        assert sum(r.path.endswith("/my-role") for r in gets) == 1
        counts = budgets[0].snapshot()
        assert counts.read_requests == counts.read_attempts == 18
        assert counts.effect_attempts == 2 + 3 * data[2].file_count
        assert counts.upload_bytes == data[2].total_bytes and counts.response_pending == 0
        count = len(server.requests)
        found = run_upload_original(plan.plan_id, data[0], denied, session_factory=denied)
        assert found.existing and found.record == result.record and len(server.requests) == count
    with open_existing_store(data[0]) as store:
        view = StateUploads(store).show(plan_id=plan.plan_id)
        assert view.operation == result.record and len(view.intents) == len(view.receipts)
        proof = view.verification
        assert proof.schema_version == 2 and proof.authorization_policy == "explicit_read_attempt"
        assert proof.grant is None and proof.scope == plan.scope
        assert len(proof.files) == data[2].file_count
        assert {f.item_id for f in proof.files} == {f["id"] for f in provider.confirmed.values()}
        assert all(f.sha256 == data[2].files[f.file_index].sha256 for f in proof.files)
        assert view.controls[-1].reason == "metadata_verified"
        assert store.verify().store_schema_version == 7
    assert provider.owner_id not in repr(result) and provider.name not in repr(result)


@pytest.mark.parametrize(
    "failure", ["owner", "org", "private", "membership", "hash", "total", "401", "503"]
)
def test_post_write_read_failures_are_unknown_same_id_and_never_replay(
    prepared_input, certificates, failure
):
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    routes = provider.routes()
    confirm_path = f"/api/v1/datasets/{DATASET}/upload/confirm"
    original_confirm = routes[confirm_path]

    def confirm(request, count):
        outcome = original_confirm(request, count)
        if failure in {"owner", "org", "private"}:
            original_detail = provider.detail

            def detail(record, calls):
                value = provider.dataset()
                field = {"owner": "owner_id", "org": "org_id", "private": "visibility"}[failure]
                value[field] = "public" if failure == "private" else str(uuid4())
                return reply(value)

            assert callable(original_detail)
            routes["/api/v1/datasets/test-user/test-dataset"] = detail
        elif failure == "membership":
            provider.linked = False
        elif failure == "hash":
            provider.confirmed["one.bin"]["sha256_hash"] = "0" * 64
        elif failure == "total":
            routes[f"/api/v1/datasets/{DATASET}/items?limit=128"] = reply(
                {"items": list(provider.confirmed.values()), "total": 2, "next_cursor": None}
            )
        else:
            routes[f"/api/v1/datasets/{DATASET}/items?limit=128"] = Reply(
                status=int(failure), body=b"{}"
            )
        return outcome

    routes[confirm_path] = confirm
    with TlsServer(certificates, routes) as server:
        plan = approved(prepared_input, server)
        with pytest.raises(OperationError) as raised:
            run_upload_original(
                plan.plan_id,
                prepared_input[0],
                loader(prepared_input),
                session_factory=factory(server),
            )
        assert raised.value.code == "operation_uncertain" and raised.value.exit_code == 5
        assert raised.value.operation_id is not None and raised.value.reason_code is not None
        assert raised.value.__context__ is raised.value.__cause__ is None
        assert (
            provider.create_calls
            == provider.link_calls
            == provider.put_calls
            == provider.confirm_calls
            == 1
        )
        count = len(server.requests)
        found = run_upload_original(plan.plan_id, prepared_input[0], denied, session_factory=denied)
        assert found.record.status == "unknown" and len(server.requests) == count
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store).show(plan_id=plan.plan_id)
        assert (
            len(view.receipts) == 5 and view.verification is None and view.operation.lease is None
        )
        assert store.verify().store_schema_version == 7


def test_initial_read_revoked_after_last_confirm_stops_before_any_metadata_get(
    prepared_input, certificates, monkeypatch
):
    from yorunge.adapters import upload_original

    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    original_publish = upload_original._Environment.publish
    counts = []

    def publish(environment, outcome):
        original_publish(environment, outcome)
        if provider.confirm_calls:
            with open_existing_store(prepared_input[0]) as store:
                StateUploads(store).revoke(environment.plan.plan_id, environment.plan.digest)
            counts.append(len(server.requests))

    monkeypatch.setattr(upload_original._Environment, "publish", publish)
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(prepared_input, server)
        with pytest.raises(OperationError) as raised:
            run_upload_original(
                plan.plan_id,
                prepared_input[0],
                loader(prepared_input),
                session_factory=factory(server),
            )
        assert raised.value.code == "operation_uncertain" and counts == [len(server.requests)]
        assert not any("/items?" in r.path for r in server.requests)


def test_initial_read_deadline_does_not_slide_authorization_to_item_completion(
    prepared_input, certificates, execution_clock
):
    clock = execution_clock
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    routes = provider.routes()
    original_items = provider.items

    def items(request, count):
        clock.value += timedelta(seconds=31)
        clock.elapsed += 31
        return original_items(request, count)

    routes[f"/api/v1/datasets/{DATASET}/items?limit=128"] = items
    with TlsServer(certificates, routes) as server:
        preparation = runtime(prepared_input, server, clock=clock)
        plan = prepare(preparation, prepared_input)
        approve(preparation, plan)
        with pytest.raises(OperationError) as raised:
            run_upload_original(
                plan.plan_id,
                prepared_input[0],
                loader(prepared_input),
                session_factory=factory(server),
                clock=clock,
            )
        assert raised.value.code == "operation_uncertain"
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store, clock=clock).show(plan_id=plan.plan_id)
        assert view.operation.status == "unknown" and view.verification is None
        assert store.verify().store_schema_version == 7


def test_actual_cancel_during_metadata_propagates_and_preserves_complete_receipts(
    prepared_input, certificates, monkeypatch
):
    from yorunge.adapters.platform_upload_port import ObservedUploadPort

    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    original = ObservedUploadPort.items

    async def items(port, *args, **kwargs):
        asyncio.current_task().cancel()
        return await original(port, *args, **kwargs)

    monkeypatch.setattr(ObservedUploadPort, "items", items)
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(prepared_input, server)
        with pytest.raises(asyncio.CancelledError):
            run_upload_original(
                plan.plan_id,
                prepared_input[0],
                loader(prepared_input),
                session_factory=factory(server),
            )
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store).show(plan_id=plan.plan_id)
        assert view.operation.status == "unknown" and len(view.receipts) == 5
        assert view.verification is None and store.verify().store_schema_version == 7


@pytest.mark.parametrize("committed", [False, True])
def test_proof_commit_or_reply_failure_never_replays_or_downgrades_terminal(
    prepared_input, certificates, monkeypatch, committed
):
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    if committed:
        original = StateUploads.verified

        def after(repository, *args, **kwargs):
            original(repository, *args, **kwargs)
            raise OSError("proof reply lost")

        monkeypatch.setattr(StateUploads, "verified", after)
    else:
        original = StateUploads._control

        def before(repository, *args, **kwargs):
            original(repository, *args, **kwargs)
            if kwargs.get("proof") is not None:
                raise YorungeError("state_write_failed")

        monkeypatch.setattr(StateUploads, "_control", before)
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(prepared_input, server)
        with pytest.raises(OperationError) as raised:
            run_upload_original(
                plan.plan_id,
                prepared_input[0],
                loader(prepared_input),
                session_factory=factory(server),
            )
        assert raised.value.exit_code == (2 if committed else 5)
        if committed:
            assert raised.value.code == "state_write_failed"
        assert raised.value.operation_id is not None
        assert raised.value.__cause__ is raised.value.__context__ is None
        count = len(server.requests)
        result = run_upload_original(
            plan.plan_id, prepared_input[0], denied, session_factory=denied
        )
        assert len(server.requests) == count
        assert result.record.operation_id == raised.value.operation_id
        assert result.record.status == ("succeeded" if committed else "unknown")
    with open_existing_store(prepared_input[0]) as store:
        view = StateUploads(store).show(plan_id=plan.plan_id)
        assert (view.verification is not None) == committed and len(view.receipts) == 5
        assert store.verify().store_schema_version == 7


def test_metadata_read_does_not_reopen_already_sent_source_files(
    prepared_input, certificates, monkeypatch
):
    from yorunge.adapters import upload_original

    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    original_publish = upload_original._Environment.publish

    def publish(environment, outcome):
        original_publish(environment, outcome)
        if environment.confirmed_count:
            (prepared_input[1] / "one.bin").unlink()

    monkeypatch.setattr(upload_original._Environment, "publish", publish)
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(prepared_input, server)
        result = run_upload_original(
            plan.plan_id,
            prepared_input[0],
            loader(prepared_input),
            session_factory=factory(server),
        )
        assert result.record.status == "succeeded" and not (prepared_input[1] / "one.bin").exists()
    with open_existing_store(prepared_input[0]) as store:
        assert store.verify().store_schema_version == 7
