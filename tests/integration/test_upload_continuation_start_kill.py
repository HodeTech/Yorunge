"""A continuation killed at every boundary of its start leaves a store that explains itself.

A child process starts an approved continuation and pauses at one boundary: just after the
admission, after the first gate of the closing read, after the permission was looked at, after the
listing and after the proof is written. The parent kills it with SIGKILL and checks the store (what
the operation is, the intents and receipts it holds, whether a proof exists), the provider (no
request that nothing explains) and that another process finds the operation by its plan and sends
nothing. A check-only continuation never runs: it stays admitted until the proof is written, and a
lapsed lease cancels it.
"""

import multiprocessing
import os
import signal
import ssl
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.fixtures.http_server import TlsServer
from tests.fixtures.upload_provider import DATASET
from tests.integration.test_upload_continuation_stages import Skewed, journal, planned
from tests.integration.test_upload_continuation_start import (
    approve,
    check_only_world,
    no_context,
)
from tests.integration.test_upload_original import factory
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_resume_observation import (
    certificates as certificates,
)
from tests.integration.test_upload_resume_observation import (
    loopback_only as loopback_only,
)
from tests.integration.test_upload_resume_observation import world as three_files
from tests.integration.test_upload_workflow_kill import _settle
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_continuation_start import run_upload_continuation
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import validate_uploads
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Context, Profile

BOUNDARIES = ("admission", "proof_gate", "proof_look", "proof_listing", "proof_commit")
BUSY_RETRIES = 6


def _child(state, plan_id, context, profile, port, certificate, boundary, connection):
    from tests.integration.test_upload_continuation_start import go as child_go
    from yorunge.adapters.platform_upload_port import ObservedUploadPort
    from yorunge.adapters.upload_continuation import ContinuationStages
    from yorunge.adapters.upload_repository import StateUploads as Repository

    endpoint = SimpleNamespace(
        port=port, client_context=lambda: ssl.create_default_context(cafile=certificate)
    )

    def pause():
        connection.send("paused")
        connection.recv()
        raise AssertionError("killed child resumed")

    original_admit = ContinuationStages.admit
    original_prepare = Repository.prepare_initial_read
    original_items = ObservedUploadPort.items
    original_verified = Repository.verified

    def admit(environment, check):
        result = original_admit(environment, check)
        if boundary == "admission":
            pause()
        return result

    def prepare(repository, operation_id, owner, *, authorization=None):
        result = original_prepare(repository, operation_id, owner, authorization=authorization)
        if (boundary, authorization is None) in {("proof_gate", True), ("proof_look", False)}:
            pause()
        return result

    async def items(port, client, dataset_id, *, deadline):
        found = await original_items(port, client, dataset_id, deadline=deadline)
        if boundary == "proof_listing":
            pause()
        return found

    def verified(repository, *arguments, **keywords):
        result = original_verified(repository, *arguments, **keywords)
        if boundary == "proof_commit":
            pause()
        return result

    ContinuationStages.admit = admit
    Repository.prepare_initial_read = prepare
    ObservedUploadPort.items = items
    Repository.verified = verified
    data = (
        Path(state),
        None,
        None,
        Context.model_validate(context),
        Profile.model_validate(profile),
    )
    child_go(data, endpoint, plan_id)
    connection.send("unexpected return")


def kill_at(data, server, provider, plan_id, boundary, certificates):
    """Start the plan in a child, kill it at ``boundary``; the effects the provider saw after it."""
    sent_before = len(provider.events)
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe()
    process = context.Process(
        target=_child,
        args=(
            str(data[0]),
            plan_id,
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
        assert parent.poll(60), "the start did not reach the crash boundary"
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
    return tuple(provider.events[sent_before:])


STAGES = ("presign", "put", "confirm")


@pytest.mark.parametrize("boundary", BOUNDARIES)
@pytest.mark.parametrize("world", ["files", "check_only"])
def test_sigkill_of_a_start_leaves_the_operation_found_by_its_plan_and_nothing_to_replay(
    prepared_input, certificates, monkeypatch, world, boundary
):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    data, provider = (
        three_files(prepared_input) if world == "files" else check_only_world(prepared_input)
    )
    sends_files = world == "files"
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        requests = len(server.requests)
        events = kill_at(data, server, provider, report.plan_id, boundary, certificates)
        view = journal(data, report.plan_id)
        operation = view.operation
        done = boundary == "proof_commit"
        # What the provider saw: the stages of a continuation that sends files, nothing else.
        assert events == (STAGES if sends_files and boundary != "admission" else ())
        effects = [r for r in server.requests[requests:] if r.method in {"POST", "PUT"}]
        assert len(effects) == len(events)
        assert provider.create_calls == 1
        # A check-only continuation never runs: admitted until the proof is written.
        if done:
            assert (operation.status, operation.reason) == ("succeeded", "metadata_verified")
            assert view.verification is not None and len(view.verification.files) >= 2
        else:
            running = sends_files and boundary != "admission"
            assert operation.status == ("running" if running else "admitted")
            assert view.verification is None
            assert operation.lease is not None  # a killed owner's lease runs out by itself
        assert operation.workflow_latched is (sends_files and boundary != "admission")
        stages = 3 if sends_files and boundary != "admission" else 0
        assert len(view.intents) == len(view.receipts) == stages
        assert operation.dataset_id == DATASET
        with open_existing_store(data[0]) as store:
            validate_uploads(store.connection)
        # Another process finds the operation by its plan: it asks for nothing and sends nothing.
        again_requests = len(server.requests)
        again = run_upload_continuation(
            report.plan_id, Path(data[0]), no_context, session_factory=factory(server)
        )
        assert again.existing is True and again.record == operation
        assert len(server.requests) == again_requests


@pytest.mark.parametrize("boundary", ["admission", "proof_gate", "proof_look", "proof_listing"])
def test_a_killed_check_only_continuation_is_cancelled_when_its_lease_runs_out(
    prepared_input, certificates, monkeypatch, boundary
):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    data, provider = check_only_world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        kill_at(data, server, provider, report.plan_id, boundary, certificates)
        operation = journal(data, report.plan_id).operation
        assert operation.status == "admitted" and operation.workflow_latched is False
        clock = Skewed()
        clock.skew = 400  # far past the lease of the owner that was killed
        with open_existing_store(data[0]) as store:
            cleaned = StateUploads(store, clock=clock).cleanup_expired(operation.operation_id)
            assert cleaned.operation.status == "cancelled"
            assert cleaned.operation.reason == "lease_expired"
            validate_uploads(store.connection)
        # Nothing was ever sent and nothing is uncertain: the plan's operation is simply over.
        assert journal(data, report.plan_id).intents == ()


def _racer(state, plan_id, context, profile, port, certificate, barrier, results):
    from tests.integration.test_upload_continuation_start import go as child_go

    endpoint = SimpleNamespace(
        port=port, client_context=lambda: ssl.create_default_context(cafile=certificate)
    )
    data = (
        Path(state),
        None,
        None,
        Context.model_validate(context),
        Profile.model_validate(profile),
    )
    barrier.wait(60)
    try:
        for attempt in range(BUSY_RETRIES):
            try:
                phase = child_go(data, endpoint, plan_id)
                break
            except YorungeError as error:
                # A store held for more than its second (a loaded machine) is the one answer a user
                # retries; any other error is the answer, and is reported at once.
                if error.code != "state_busy" or attempt == BUSY_RETRIES - 1:
                    raise
                time.sleep(0.5)
    except BaseException as error:
        results.put(("raised", type(error).__name__, getattr(error, "code", None)))
        raise
    results.put(("returned", phase.existing, phase.record.status))


def test_two_processes_starting_the_same_plan_send_its_files_once(
    prepared_input, certificates, monkeypatch
):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        sends = len(provider.events)
        context = multiprocessing.get_context("spawn")
        barrier, results = context.Barrier(2), context.Queue()
        processes = [
            context.Process(
                target=_racer,
                args=(
                    str(data[0]),
                    report.plan_id,
                    data[3].model_dump(mode="json"),
                    data[4].model_dump(mode="json"),
                    server.port,
                    str(certificates[0]),
                    barrier,
                    results,
                ),
            )
            for _ in range(2)
        ]
        for process in processes:
            process.start()
        try:
            answers = [results.get(timeout=120) for _ in processes]
        finally:
            for process in processes:
                process.join(30)
                if process.is_alive():
                    process.kill()
        assert all(answer[0] == "returned" for answer in answers), answers
        assert all(process.exitcode == 0 for process in processes)
        # One of them owned the operation; the other only found it, whatever state it saw.
        assert sorted(answer[1] for answer in answers) == [False, True]
        assert provider.events[sends:] == list(STAGES)
        view = journal(data, report.plan_id)
        assert (view.operation.status, view.operation.reason) == ("succeeded", "metadata_verified")
        assert len(view.intents) == len(view.receipts) == 3
        with open_existing_store(data[0]) as store:
            validate_uploads(store.connection)
