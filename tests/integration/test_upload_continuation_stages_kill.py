"""A continuation killed at every boundary of its stages leaves a store that explains itself.

A child process runs the stages of a saved continuation plan and pauses at one boundary: just after
the stage's intent is durable (nothing sent yet), just before its answer is published and just
after. The parent kills it with SIGKILL and checks the store (intents and receipts exactly as
many as the boundary implies, the operation running and latched once something was armed), the
provider (no request the intents do not explain) and that another process finds the operation by
its plan and sends nothing.
"""

import multiprocessing
import os
import signal
import ssl
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.http_server import TlsServer
from tests.fixtures.upload_provider import DATASET, UploadProvider
from tests.integration.test_upload_continuation_stages import (
    eight_files,
    journal,
    planned,
    start,
)
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_resume_observation import (
    certificates as certificates,
)
from tests.integration.test_upload_resume_observation import (
    loopback_only as loopback_only,
)
from tests.integration.test_upload_resume_observation import (
    lose_confirm_of,
)
from tests.integration.test_upload_resume_observation import world as three_files
from tests.integration.test_upload_workflow_kill import _settle
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import validate_uploads
from yorunge.application.upload_workflow import continue_files
from yorunge.domain.models import Context, Profile

# Arm boundaries pause right after the stage intent is durable and before any request is made.
INTENTS = {
    "presign_intent": ("presign", None),
    "put_intent": ("put", None),
    "confirm_intent": ("confirm", None),
    "second_batch_put_intent": ("put", 7),
}


def _child(state, plan_id, context, profile, port, certificate, boundary, connection):
    from tests.integration.test_upload_continuation_stages import (
        approve_admit_continue,
        start,
    )
    from yorunge.adapters.upload_continuation import ContinuationStages

    endpoint = SimpleNamespace(
        port=port, client_context=lambda: ssl.create_default_context(cafile=certificate)
    )
    original_admit, original_publish = ContinuationStages.admit, ContinuationStages.publish
    original_arm = ContinuationStages.arm
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

    def kind_of(outcome):
        if outcome.upload is not None:
            return "presign"
        return "put" if outcome.receipt.sent_bytes is not None else "confirm"

    def publish(environment, outcome):
        kind = kind_of(outcome)
        if boundary == f"{kind}_response":
            pause()
        original_publish(environment, outcome)
        if boundary == f"{kind}_commit":
            pause()

    def arm(environment, check, kind, index=None):
        result = original_arm(environment, check, kind, index)
        last["kind"] = kind
        wanted = INTENTS.get(boundary)
        if wanted is not None and wanted[0] == kind and wanted[1] in (None, index):
            pause()
        return result

    ContinuationStages.admit, ContinuationStages.publish = admit, publish
    ContinuationStages.arm = arm
    data = (
        Path(state),
        None,
        None,
        Context.model_validate(context),
        Profile.model_validate(profile),
    )
    start(data, endpoint, plan_id, algorithm=approve_admit_continue)
    connection.send("unexpected return")


async def only_look(environment):
    """What another process does with a plan whose operation exists: look, never send."""
    check = await environment.current("presign")
    owned = environment.admit(check)
    assert not owned
    return await continue_files(environment)


ONE_PRESIGNED = ("presign",)
ONE_PUT = ("presign", "put")
ONE_CONFIRMED = ("presign", "put", "confirm")
# The second PUT of a batch may or may not be on the wire when the first one is paused.
TWO_PUTS = [("presign", "presign", "put"), ("presign", "presign", "put", "put")]
SECOND_BATCH = (("presign",) * 3 + ("put", "put", "confirm", "confirm"),)


@pytest.mark.parametrize(
    "world,boundary,intents,receipts,alternatives",
    [
        ("one", "admission", 0, 0, [()]),
        ("one", "presign_intent", 1, 0, [()]),
        ("one", "presign_response", 1, 0, [ONE_PRESIGNED]),
        ("one", "presign_commit", 1, 1, [ONE_PRESIGNED]),
        ("one", "put_intent", 2, 1, [ONE_PRESIGNED]),
        ("one", "put_response", 2, 1, [ONE_PUT]),
        ("one", "put_commit", 2, 2, [ONE_PUT]),
        ("one", "confirm_intent", 3, 2, [ONE_PUT]),
        ("one", "confirm_response", 3, 2, [ONE_CONFIRMED]),
        ("one", "confirm_commit", 3, 3, [ONE_CONFIRMED]),
        # Two files arm both PUT intents before either response is published (publication runs
        # only from the batch drain), so the intent count is exact while the second PUT request
        # may or may not be on the wire.
        ("two", "put_response", 4, 2, TWO_PUTS),
        ("two", "put_commit", 4, 3, TWO_PUTS),
        # Three files: the first batch is fully confirmed, the second batch's PUT is armed.
        ("three", "second_batch_put_intent", 8, 7, SECOND_BATCH),
    ],
)
def test_sigkill_of_a_continuation_leaves_the_operation_found_by_its_plan_and_nothing_to_replay(
    prepared_input,
    certificates,
    monkeypatch,
    world,
    boundary,
    intents,
    receipts,
    alternatives,
):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    if world == "one":  # the last of three files is left
        data, provider = three_files(prepared_input)
    elif world == "two":  # the second and the third are left
        data, _ = three_files(prepared_input)
        provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
        lose_confirm_of(provider, "one.bin")
    else:  # files 5, 6 and 7 of eight are left
        data = eight_files(prepared_input)
        provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
        lose_confirm_of(provider, "f05.bin")
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        sent_before = len(provider.events)
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe()
        process = context.Process(
            target=_child,
            args=(
                str(data[0]),
                report.plan_id,
                data[3].model_dump(mode="json"),
                data[4].model_dump(mode="json"),
                server.port,
                str(certificates[0]),
                boundary,
                child,
            ),
        )
        process.start()
        child.close()
        try:
            assert parent.poll(30), "the continuation did not reach the crash boundary"
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
        events = tuple(provider.events[sent_before:])
        assert events in alternatives
        # Every effectful request the server saw is a stage the journal armed: none unexplained.
        effects = [r for r in server.requests if r.method in {"POST", "PUT"}]
        assert len(effects) == len(provider.events)
        assert provider.create_calls == 1
        view = journal(data, report.plan_id)
        assert len(view.intents) == intents
        assert len(view.receipts) == receipts
        assert view.operation.status == ("running" if intents else "admitted")
        assert view.operation.workflow_latched == bool(intents)
        assert view.operation.dataset_id == DATASET
        assert view.verification is None
        with open_existing_store(data[0]) as store:
            validate_uploads(store.connection)
            assert StateUploads(store).show(plan_id=report.plan_id).operation == view.operation
        # Another process finds the operation by its plan: it looks and sends nothing.
        again = len(server.requests)
        record = start(data, server, report.plan_id, algorithm=only_look)
        assert record == view.operation
        assert all(r.method == "GET" for r in server.requests[again:])
        assert tuple(provider.events[sent_before:]) == events
