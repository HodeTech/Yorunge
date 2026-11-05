"""Actual spawned original workflow dies before its first returned operation ID."""

import multiprocessing
import os
import signal
import ssl
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.http_server import TlsServer
from tests.fixtures.upload_provider import DATASET, UploadProvider
from tests.integration.test_upload_file_workflow import certificates as certificates
from tests.integration.test_upload_file_workflow import loopback_only as loopback_only
from tests.integration.test_upload_original import approved, denied, factory
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_original import run_upload_original
from yorunge.adapters.upload_repository import StateUploads


def _child(state, plan_id, context, profile, port, certificate, boundary, connection):
    from yorunge.adapters.upload_original import _Environment
    from yorunge.domain.create_receipt import CreateReceiptV2
    from yorunge.domain.models import Context, Profile

    endpoint = SimpleNamespace(
        port=port, client_context=lambda: ssl.create_default_context(cafile=certificate)
    )
    original_admit, original_publish = _Environment.admit, _Environment.publish
    original_arm = _Environment.arm
    original_verified = StateUploads.verified
    original_control = StateUploads._control

    def pause():
        connection.send("paused")
        connection.recv()
        raise AssertionError("killed child resumed")

    def admit(environment, check):
        result = original_admit(environment, check)
        if boundary == "admission":
            pause()
        return result

    def publish(environment, outcome):
        create = isinstance(outcome.receipt, CreateReceiptV2)
        if (boundary == "create_response" and create) or (
            boundary == "put_response" and outcome.receipt.sent_bytes is not None
        ):
            pause()
        original_publish(environment, outcome)
        if (boundary == "create_commit" and create) or (
            boundary == "confirm_commit" and environment.confirmed_count == 1
        ):
            pause()

    def arm(environment, check, kind, index=None):
        result = original_arm(environment, check, kind, index)
        if boundary == "create_intent" and kind == "create":
            pause()
        return result

    def control(repository, *args, **kwargs):
        original_control(repository, *args, **kwargs)
        if boundary == "proof_before_commit" and kwargs.get("proof") is not None:
            pause()

    def verified(repository, *args, **kwargs):
        result = original_verified(repository, *args, **kwargs)
        if boundary == "proof_commit":
            pause()
        return result

    _Environment.admit, _Environment.publish, StateUploads.verified = admit, publish, verified
    _Environment.arm, StateUploads._control = arm, control
    run_upload_original(
        plan_id,
        Path(state),
        lambda plan: (Context.model_validate(context), Profile.model_validate(profile)),
        session_factory=factory(endpoint),
    )
    connection.send("unexpected return")


@pytest.mark.parametrize(
    "boundary,intents,receipts,writes,terminal",
    [
        ("admission", 0, 0, 0, False),
        ("create_intent", 1, 0, 0, False),
        ("create_response", 1, 0, 1, False),
        ("create_commit", 1, 1, 1, False),
        ("put_response", 4, 3, 4, False),
        ("confirm_commit", 5, 5, 5, False),
        ("proof_before_commit", 5, 5, 5, False),
        ("proof_commit", 5, 5, 5, True),
    ],
)
def test_sigkill_original_is_found_by_plan_without_any_restart_write(
    prepared_input, certificates, monkeypatch, boundary, intents, receipts, writes, terminal
):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved(prepared_input, server)
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe()
        process = context.Process(
            target=_child,
            args=(
                str(prepared_input[0]),
                plan.plan_id,
                prepared_input[3].model_dump(mode="json"),
                prepared_input[4].model_dump(mode="json"),
                server.port,
                str(certificates[0]),
                boundary,
                child,
            ),
        )
        process.start()
        child.close()
        try:
            assert parent.poll(20), "original child did not reach crash boundary"
            assert parent.recv() == "paused"
            os.kill(process.pid, signal.SIGKILL)
            process.join(5)
            assert process.exitcode == -signal.SIGKILL
        finally:
            if process.is_alive():
                process.kill()
                process.join(5)
            parent.close()
        count = len(server.requests)
        result = run_upload_original(
            plan.plan_id, prepared_input[0], denied, session_factory=denied
        )
        assert result.existing
        assert len(server.requests) == count
        expected_status = "running" if intents else "admitted"
        if terminal:
            expected_status = "succeeded"
        assert result.record.status == expected_status
        assert sum(r.method in {"POST", "PUT"} for r in server.requests) == writes
        with open_existing_store(prepared_input[0]) as store:
            repository = StateUploads(store)
            view = repository.show(plan_id=plan.plan_id)
            assert len(view.intents) == intents
            assert len(view.receipts) == receipts
            assert (view.operation.dataset_id == DATASET) == (receipts > 0)
            assert (view.verification is not None) == terminal
            assert view.operation.operation_id == result.record.operation_id
            assert store.verify().store_schema_version == 7
        if not terminal:

            class Later:
                def now(self):
                    return datetime.now(UTC) + timedelta(seconds=151)

                def monotonic(self):
                    return time.monotonic() + 151

            with open_existing_store(prepared_input[0]) as store:
                stopped = StateUploads(store, clock=Later()).cleanup_expired(
                    result.record.operation_id
                )
                assert stopped.operation.status == ("unknown" if intents else "cancelled")
                assert stopped.operation.lease is None
                assert store.verify().store_schema_version == 7
            again = run_upload_original(
                plan.plan_id, prepared_input[0], denied, session_factory=denied
            )
            assert again.record.operation_id == result.record.operation_id
            assert len(server.requests) == count
