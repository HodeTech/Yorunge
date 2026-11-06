"""Actual spawned original workflow is SIGKILLed at the journal boundaries of the v2 path.

These are characterization tests: they record what the shipped path leaves behind so later changes
to the stage graph or to resume classification cannot silently change the journal shapes those
depend on. Every case keeps the same operation ID and sends no request on restart. Before the first
intent the record is an unlatched ``admitted`` one that a lapsed lease cancels; from the first
intent on it is a latched ``running`` one that a lapsed lease turns ``unknown``; once the metadata
proof has committed it is ``succeeded`` and needs no expiry. No case issues a second effect.
"""

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
from yorunge.adapters.dataset_files import open_dataset
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_original import run_upload_original
from yorunge.adapters.upload_repository import StateUploads
from yorunge.application.datasets import DatasetBudget

# Contents are distinct so the distinct-SHA-256 rule holds for every extra file.
EXTRA_FILES = (("two.bin", b"distinct"), ("three.bin", b"different"))


def _files(data, count):
    for name, content in EXTRA_FILES[: count - 1]:
        (data[1] / name).write_bytes(content)
    with open_dataset(data[1], DatasetBudget()) as tree:
        manifest = tree.scan()
    return (*data[:2], manifest, *data[3:])


# Arm boundaries pause right after the stage intent is durable and before any request is made.
ARM_BOUNDARIES = {
    "create_intent": ("create", None),
    "link_intent": ("project_link", None),
    "presign_intent": ("presign", 0),
    "put_intent": ("put", 0),
    "confirm_intent": ("confirm", 0),
    "second_batch_put_intent": ("put", 2),
}


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
    # Serial stages publish right after they are armed, so the last armed kind names them.
    last = {"kind": None}

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
        receipt = outcome.receipt
        create = isinstance(receipt, CreateReceiptV2)
        link = not create and receipt.object_key is None
        put = receipt.sent_bytes is not None  # only PUT receipts carry sent counters
        confirm = last["kind"] == "confirm"
        before = {
            "create_response": create,
            "link_response": link,
            "put_response": put,
            "two_put_response": put,
            "confirm_response": confirm,
        }
        if before.get(boundary):
            pause()
        original_publish(environment, outcome)
        after = {
            "create_commit": create,
            "link_commit": link,
            "put_commit": put,
            # Publication runs only from the batch drain, after both PUT intents were armed.
            "two_put_commit": put,
            "confirm_commit": environment.confirmed_count == 1,
        }
        if after.get(boundary):
            pause()

    def arm(environment, check, kind, index=None):
        result = original_arm(environment, check, kind, index)
        last["kind"] = kind
        if ARM_BOUNDARIES.get(boundary) == (kind, index):
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


def _settle(server, provider):
    """A request the killed child had started may still be read by the loopback server."""
    previous = None
    for _ in range(60):
        current = (len(server.requests), tuple(provider.events))
        if current == previous:
            return
        previous = current
        time.sleep(0.05)


PRESIGNED = ("create", "project_link", "presign")
PUT_SENT = (*PRESIGNED, "put")
CONFIRMED = (*PUT_SENT, "confirm")
# The second PUT of a batch may or may not be on the wire when the first one is paused.
TWO_PUTS = [
    ("create", "project_link", "presign", "presign", "put"),
    ("create", "project_link", "presign", "presign", "put", "put"),
]
THREE_FILES_BATCH = (
    ("create", "project_link", *("presign",) * 3, "put", "put", "confirm", "confirm"),
)


@pytest.mark.parametrize(
    "boundary,files,intents,receipts,alternatives,terminal",
    [
        ("admission", 1, 0, 0, [()], False),
        ("create_intent", 1, 1, 0, [()], False),
        ("create_response", 1, 1, 0, [("create",)], False),
        ("create_commit", 1, 1, 1, [("create",)], False),
        ("link_intent", 1, 2, 1, [("create",)], False),
        ("link_response", 1, 2, 1, [("create", "project_link")], False),
        ("link_commit", 1, 2, 2, [("create", "project_link")], False),
        ("presign_intent", 1, 3, 2, [("create", "project_link")], False),
        ("put_intent", 1, 4, 3, [PRESIGNED], False),
        ("put_response", 1, 4, 3, [PUT_SENT], False),
        ("put_commit", 1, 4, 4, [PUT_SENT], False),
        ("confirm_intent", 1, 5, 4, [PUT_SENT], False),
        ("confirm_response", 1, 5, 4, [CONFIRMED], False),
        ("confirm_commit", 1, 5, 5, [CONFIRMED], False),
        ("proof_before_commit", 1, 5, 5, [CONFIRMED], False),
        ("proof_commit", 1, 5, 5, [CONFIRMED], True),
        # Two files arm both PUT intents before either response is published (publication
        # runs only from the batch drain), so the intent count is exact while the second
        # PUT request may or may not be on the wire.
        ("two_put_response", 2, 6, 4, TWO_PUTS, False),
        ("two_put_commit", 2, 6, 5, TWO_PUTS, False),
        # Three files: the first batch is fully confirmed, the second batch's PUT is armed.
        ("second_batch_put_intent", 3, 10, 9, THREE_FILES_BATCH, False),
    ],
)
def test_sigkill_original_is_found_by_plan_without_any_restart_write(
    prepared_input,
    certificates,
    monkeypatch,
    boundary,
    files,
    intents,
    receipts,
    alternatives,
    terminal,
):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    if files > 1:
        prepared_input = _files(prepared_input, files)
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
        _settle(server, provider)
        count, events = len(server.requests), tuple(provider.events)
        assert events in alternatives
        assert sum(r.method in {"POST", "PUT"} for r in server.requests) == len(events)
        result = run_upload_original(
            plan.plan_id, prepared_input[0], denied, session_factory=denied
        )
        assert result.existing
        assert len(server.requests) == count and tuple(provider.events) == events
        expected_status = "running" if intents else "admitted"
        if terminal:
            expected_status = "succeeded"
        assert result.record.status == expected_status
        with open_existing_store(prepared_input[0]) as store:
            repository = StateUploads(store)
            view = repository.show(plan_id=plan.plan_id)
            assert len(view.intents) == intents
            assert len(view.receipts) == receipts
            assert view.operation.workflow_latched == bool(intents)
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
                assert stopped.operation.operation_id == result.record.operation_id
                assert stopped.operation.status == ("unknown" if intents else "cancelled")
                assert stopped.operation.lease is None
                assert stopped.operation.workflow_latched == bool(intents)
                assert len(stopped.intents) == intents and len(stopped.receipts) == receipts
                assert store.verify().store_schema_version == 7
            again = run_upload_original(
                plan.plan_id, prepared_input[0], denied, session_factory=denied
            )
            assert again.record.operation_id == result.record.operation_id
            assert len(server.requests) == count and tuple(provider.events) == events
