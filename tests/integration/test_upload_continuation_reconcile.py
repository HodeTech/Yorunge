"""A continuation left without its proof is reconciled in its own operation (P02-3x).

Real files, a real SQLite store, a real TLS provider and the product's own interrupted upload,
continuation plan and start. The closing read of a continuation is made to fail, so that every one
of its stages is acknowledged and only the metadata proof is missing; ``reconcile_upload`` (the
private composition the public ``reconcile`` will call for a v3 record) then reads the whole dataset
with a read lease, in the same operation. A source that already has a continuation is history and is
left as it is.
"""

import asyncio
from pathlib import Path

import pytest

from tests.fixtures.http_server import Reply, TlsServer
from tests.fixtures.upload_provider import reply
from tests.integration.test_upload_continuation_stages import (
    Skewed,
    journal,
    operation_of,
    planned,
    start,
)
from tests.integration.test_upload_continuation_start import (
    ITEMS,
    admit_only,
    approve,
    check_only_world,
    go,
    the_check_goes_stale,
)
from tests.integration.test_upload_http_budget import SECRET
from tests.integration.test_upload_original import approved as approved_original
from tests.integration.test_upload_original import factory
from tests.integration.test_upload_preparation import ENV
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_resume_observation import (
    certificates as certificates,
)
from tests.integration.test_upload_resume_observation import (
    interrupted,
    lose_confirm_of,
)
from tests.integration.test_upload_resume_observation import (
    loopback_only as loopback_only,
)
from tests.integration.test_upload_resume_observation import world as three_files
from yorunge import api
from yorunge.adapters.platform_upload_port import ObservedUploadPort
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_api import recover_upload
from yorunge.adapters.upload_continuation import ContinuationStages
from yorunge.adapters.upload_reconciliation import reconcile_upload
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import validate_uploads
from yorunge.domain.dataset_transfer_v3 import TransferVerificationV3
from yorunge.domain.errors import OperationError, YorungeError


def reconcile(data, server, operation_id, *, accepted=True, budgets=None, clock=None):
    return reconcile_upload(
        operation_id,
        Path(data[0]),
        lambda plan: (data[3], data[4]),
        accept_unverified_read=accepted,
        session_factory=factory(server, budgets),
        clock=clock,
    )


def left_unproved(data, provider, server, plan_id, monkeypatch):
    """Run the approved continuation and let its closing read fail: no proof, every stage done."""
    real = provider.route_table[ITEMS]
    original = ContinuationStages.verify

    async def verify(environment):
        provider.route_table[ITEMS] = lambda request, count: Reply(status=500, body=b"")
        return await original(environment)

    with monkeypatch.context() as patch:
        patch.setattr(ContinuationStages, "verify", verify)
        with pytest.raises(OperationError) as failed:
            go(data, server, plan_id)
    provider.route_table[ITEMS] = real  # the provider is well again
    assert failed.value.code == "operation_uncertain"
    return failed.value.operation_id


def store_is_valid(data):
    with open_existing_store(data[0]) as store:
        validate_uploads(store.connection)


# --- an unproved continuation becomes verified in the same operation ------------------------------


@pytest.mark.parametrize("current", ["same", "rotated", "reset", "profile"])
def test_a_continuation_left_without_its_proof_is_proved_in_the_same_operation(
    prepared_input, certificates, monkeypatch, current
):
    data, provider = three_files(prepared_input)
    budgets = []
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        operation_id = left_unproved(data, provider, server, report.plan_id, monkeypatch)
        before = journal(data, report.plan_id)
        assert (before.operation.status, before.operation.reason) == ("unknown", "read_unavailable")
        assert before.verification is None
        assert len(before.receipts) == len(before.intents) == 3
        if current == "rotated":
            monkeypatch.setenv(ENV, "replacement-read-key")
        elif current == "reset":
            preview = api.preview_identity_reset(state_dir=data[0]).data
            api.reset_identity(preview.digest, state_dir=data[0])
        elif current == "profile":
            data = (*data[:3], data[3].model_copy(update={"profile": "readonly"}), data[4])
        events, requests = len(provider.events), len(server.requests)

        phase = reconcile(data, server, operation_id, budgets=budgets)

        record = phase.record
        assert (record.operation_id, record.status, record.reason) == (
            operation_id,
            "succeeded",
            "metadata_verified",
        )
        assert record.lease is None
        assert record.fence > before.operation.fence
        # No new write owner: the continuation's own write access is what it was.
        assert record.write_owner_id == before.operation.write_owner_id
        assert record.write_access_digest == before.operation.write_access_digest
        assert provider.events[events:] == []  # nothing is created, linked, presigned or put
        assert all(r.method == "GET" for r in server.requests[requests:])
        counters = budgets[0].snapshot()
        assert counters.effect_attempts == counters.upload_bytes == counters.response_pending == 0
        after = journal(data, report.plan_id)
        assert after.operation == record
        assert after.intents == before.intents
        assert after.receipts == before.receipts
        proof = after.verification
        assert type(proof) is TransferVerificationV3
        assert proof.grant is None
        assert proof.authorization_policy == "explicit_read_attempt"
        # The whole dataset, though one file was sent: the three of the manifest, in its order.
        assert [(f.file_index, f.size_bytes, f.sha256) for f in proof.files] == [
            (index, f.size, f.sha256) for index, f in enumerate(data[2].files)
        ]
        assert len({f.item_id for f in proof.files}) == 3  # three distinct provider items
        if current == "rotated":
            assert proof.scope.credential_revision > after.plan.scope.credential_revision
        if current == "reset":
            assert proof.scope.identity_epoch != after.plan.scope.identity_epoch
        if current == "profile":
            assert (proof.scope.profile, after.plan.scope.profile) == ("readonly", "test")
        store_is_valid(data)
        with pytest.raises(OperationError) as finished:  # a verified record is history
            reconcile(data, server, operation_id)
        assert finished.value.code == "operation_conflict"


def test_a_continuation_that_stopped_between_its_stages_stays_uncertain_and_is_not_proved(
    prepared_input, certificates
):
    data, provider = three_files(prepared_input)
    lose_confirm_of(provider, "ölçüm.bin")  # the file the continuation sends: kept, never said
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        with pytest.raises(OperationError) as stopped:
            go(data, server, report.plan_id)
        operation_id = stopped.value.operation_id
        before = journal(data, report.plan_id)
        assert before.operation.status == "unknown"
        assert before.verification is None
        assert len(before.receipts) < len(before.intents) + 1
        assert len(before.receipts) == 2
        requests = len(server.requests)

        with pytest.raises(OperationError) as refused:
            reconcile(data, server, operation_id)

        # The file is on the provider, yet its confirm was never acknowledged: a graph that is not
        # whole is never proved by reading, and the operation is not replayed either.
        assert (refused.value.code, refused.value.operation_id) == (
            "operation_uncertain",
            operation_id,
        )
        assert len(server.requests) == requests  # not even a read
        after = journal(data, report.plan_id)
        assert after.operation.status == "unknown"
        assert after.verification is None
        assert after.intents == before.intents
        assert after.receipts == before.receipts
        store_is_valid(data)


@pytest.mark.parametrize("failure", ["403", "404", "429", "503", "hash", "total", "secret"])
def test_a_read_that_goes_wrong_keeps_its_own_error_and_the_unknown_record(
    prepared_input, certificates, monkeypatch, failure
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        operation_id = left_unproved(data, provider, server, report.plan_id, monkeypatch)
        if failure.isdigit():
            provider.route_table[ITEMS] = lambda request, count: Reply(
                status=int(failure), body=b"{}"
            )
        else:
            values = [dict(value) for value in provider.confirmed.values()]
            if failure == "hash":
                values[0]["sha256_hash"] = "0" * 64
            body = {"items": values, "total": 2 if failure == "total" else 3, "next_cursor": None}
            if failure == "secret":
                body["unused"] = SECRET
            provider.route_table[ITEMS] = lambda request, count: reply(body)
        count = len(server.requests)

        with pytest.raises(OperationError) as raised:
            reconcile(data, server, operation_id)

        expected = {
            "403": "remote_access_denied",
            "404": "invalid_response",
            "429": "remote_rate_limited",
            "503": "remote_failed",
        }.get(failure, "invalid_response")
        assert raised.value.code == expected
        assert raised.value.operation_id == operation_id
        assert raised.value.__cause__ is raised.value.__context__ is None
        assert SECRET not in str(raised.value)
        assert SECRET not in repr(raised.value.envelope())
        assert all(r.method == "GET" for r in server.requests[count:])
        after = journal(data, report.plan_id)
        assert (after.operation.status, after.operation.reason) == ("unknown", "read_unavailable")
        assert after.operation.lease is None
        assert after.verification is None
        assert len(after.receipts) == 3
        store_is_valid(data)


@pytest.mark.parametrize("mutation", ["another owner", "dataset gone"])
def test_a_dataset_that_is_not_the_baseline_is_a_failed_read_and_the_record_stays_unknown(
    prepared_input, certificates, monkeypatch, mutation
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        operation_id = left_unproved(data, provider, server, report.plan_id, monkeypatch)
        before = operation_of(data, report.plan_id)
        if mutation == "another owner":
            provider.wrong_detail_owner = True
        else:
            provider.created = False  # the detail answers 404
        count = len(server.requests)
        with pytest.raises(OperationError) as raised:
            reconcile(data, server, operation_id)
        after = operation_of(data, report.plan_id)
        assert (raised.value.code, raised.value.operation_id) == ("invalid_response", operation_id)
        assert (after.status, after.reason) == ("unknown", "read_unavailable")
        assert after.fence == before.fence + 1
        assert after.lease is None  # as the v2 read does
        assert journal(data, report.plan_id).verification is None
        assert all(r.method == "GET" for r in server.requests[count:])
        provider.wrong_detail_owner, provider.created = False, True  # the provider is right again
        phase = reconcile(data, server, operation_id)
        assert (phase.record.status, phase.record.reason) == ("succeeded", "metadata_verified")
        store_is_valid(data)


def test_a_cancel_after_the_read_lease_releases_it_and_leaves_the_record_unknown(
    prepared_input, certificates, monkeypatch
):
    data, provider = three_files(prepared_input)
    original = ObservedUploadPort.items

    async def items(port, *args, **kwargs):
        asyncio.current_task().cancel()
        return await original(port, *args, **kwargs)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        operation_id = left_unproved(data, provider, server, report.plan_id, monkeypatch)
        with monkeypatch.context() as patch:
            patch.setattr(ObservedUploadPort, "items", items)
            with pytest.raises(asyncio.CancelledError):
                reconcile(data, server, operation_id)
        after = journal(data, report.plan_id)
        assert (after.operation.status, after.operation.reason) == ("unknown", "request_uncertain")
        assert after.operation.lease is None
        assert after.verification is None
        assert len(after.receipts) == 3
        store_is_valid(data)
        # The next read is a clean one: the same record is still reconcilable.
        phase = reconcile(data, server, operation_id)
        assert (phase.record.status, phase.record.reason) == ("succeeded", "metadata_verified")


def test_the_consent_to_an_unverified_read_is_asked_for_a_continuation_too(
    prepared_input, certificates, monkeypatch
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        operation_id = left_unproved(data, provider, server, report.plan_id, monkeypatch)
        before, requests = journal(data, report.plan_id), len(server.requests)
        with pytest.raises(OperationError) as refused:
            reconcile(data, server, operation_id, accepted=False)
        assert refused.value.code == "approval_required"
        assert len(server.requests) == requests
        assert journal(data, report.plan_id) == before


# --- a continuation that sent nothing -------------------------------------------------------------


def test_a_continuation_that_sent_nothing_and_lost_its_lease_is_cancelled_by_the_reconcile(
    prepared_input, certificates, monkeypatch
):
    data, provider = check_only_world(prepared_input)
    clock = Skewed()
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        the_check_goes_stale(monkeypatch, clock, 200)
        with pytest.raises(OperationError) as stopped:
            go(data, server, report.plan_id, clock=clock)
        operation_id = stopped.value.operation_id
        record = operation_of(data, report.plan_id)
        assert (record.status, record.workflow_latched) == ("admitted", False)
        requests = len(server.requests)

        phase = reconcile(data, server, operation_id, clock=clock)

        assert (phase.record.status, phase.record.reason) == ("cancelled", "lease_expired")
        assert len(server.requests) == requests  # nothing local needs the provider
        assert journal(data, report.plan_id).verification is None
        store_is_valid(data)


# --- a source that already has a continuation -----------------------------------------------------


def a_source_with_a_continuation(data, provider, server, how):
    """The interrupted upload, and the continuation that was started from it."""
    report = planned(data, server, provider)
    approve(data, server, report.plan_id)
    if how == "live":
        start(data, server, report.plan_id, algorithm=admit_only)  # admitted, nothing sent
    else:
        go(data, server, report.plan_id)  # sent and proved
    source = journal(data, report.plan_id).plan.continuation.source_operation_id
    return report.plan_id, source, operation_of(data, report.plan_id)


def source_record(data, operation_id):
    with open_existing_store(data[0]) as store:
        return StateUploads(store).show(operation_id=operation_id).operation


@pytest.mark.parametrize("how", ["live", "done"])
def test_a_source_that_has_a_continuation_is_history_and_is_not_touched(
    prepared_input, certificates, how
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        plan_id, source, successor = a_source_with_a_continuation(data, provider, server, how)
        before, requests = source_record(data, source), len(server.requests)

        with pytest.raises(OperationError) as refused:
            reconcile(data, server, source)

        # The continuation is named, and neither a read nor a write was made for the source.
        assert refused.value.code == "operation_conflict"
        assert refused.value.operation_id == successor.operation_id
        assert source_record(data, source) == before
        assert len(server.requests) == requests
        # Without the consent too: a source with a continuation has nothing left to reconcile.
        with pytest.raises(OperationError) as unasked:
            reconcile(data, server, source, accepted=False)
        assert unasked.value.operation_id == successor.operation_id
        assert source_record(data, source) == before
        store_is_valid(data)


@pytest.mark.parametrize("how", ["live", "done"])
def test_the_store_itself_refuses_to_read_or_clean_a_source_that_has_a_continuation(
    prepared_input, certificates, how
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        plan_id, source, successor = a_source_with_a_continuation(data, provider, server, how)
        before = source_record(data, source)
        with open_existing_store(data[0]) as store:
            repository = StateUploads(store)
            for gate in (
                lambda: repository.acquire_read(source, accept_unverified_read=True),
                lambda: repository.cleanup_expired(source),
                lambda: repository.require_no_successor(source),
            ):
                with pytest.raises(OperationError) as refused:
                    gate()
                assert refused.value.code == "operation_conflict"
                assert refused.value.operation_id == successor.operation_id
        assert source_record(data, source) == before
        store_is_valid(data)


def test_a_continuation_whose_lease_lapsed_without_sending_is_no_successor_yet(
    prepared_input, certificates
):
    # Admitted, nothing sent, and its lease lapsed: it is not cancelled yet (the next prepare or
    # admission does that), but it no longer stands in the source's way.
    data, provider = three_files(prepared_input)
    clock = Skewed()
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        start(data, server, report.plan_id, algorithm=admit_only, clock=clock)
        source = journal(data, report.plan_id).plan.continuation.source_operation_id
        clock.skew += 200
        before = source_record(data, source)
        with pytest.raises(OperationError) as uncertain:
            reconcile(data, server, source, clock=clock)
        assert (uncertain.value.code, uncertain.value.operation_id) == (
            "operation_uncertain",
            source,
        )
        assert source_record(data, source).fence == before.fence + 1
        assert operation_of(data, report.plan_id).status == "admitted"  # the cleanup is not ours
        store_is_valid(data)


def test_a_source_whose_continuation_was_cancelled_is_reconciled_as_it_always_was(
    prepared_input, certificates
):
    data, provider = three_files(prepared_input)
    clock = Skewed()
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        start(data, server, report.plan_id, algorithm=admit_only, clock=clock)
        source = journal(data, report.plan_id).plan.continuation.source_operation_id
        successor = operation_of(data, report.plan_id)
        assert successor.status == "admitted"
        clock.skew += 200  # the lease lapses, the continuation sent nothing
        with open_existing_store(data[0]) as store:
            cancelled = StateUploads(store, clock=clock).cleanup_expired(successor.operation_id)
        assert (cancelled.operation.status, cancelled.operation.reason) == (
            "cancelled",
            "lease_expired",
        )
        before = source_record(data, source)

        # A continuation that ran nothing does not stand in the way: the source is read as before
        # (its graph is not whole, so the answer is the uncertainty it has always been).
        with pytest.raises(OperationError) as uncertain:
            reconcile(data, server, source, clock=clock)

        assert (uncertain.value.code, uncertain.value.operation_id) == (
            "operation_uncertain",
            source,
        )
        after = source_record(data, source)
        assert after.status == "unknown"
        assert after.fence > before.fence
        store_is_valid(data)


def test_a_successor_found_inside_the_session_is_named_too(
    prepared_input, certificates, monkeypatch
):
    from yorunge.domain.upload_resume import SourceHasSuccessor

    data, provider = three_files(prepared_input)
    other = "00000000-0000-4000-8000-0000000000bb"
    real = StateUploads.require_no_successor
    calls = []

    def second_time_is_the_session(repository, operation_id):
        calls.append(operation_id)
        if len(calls) == 2:  # the check the session makes of its own record before it acquires
            raise SourceHasSuccessor(other)
        return real(repository, operation_id)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        operation_id = left_unproved(data, provider, server, report.plan_id, monkeypatch)
        before = source_record(data, operation_id)
        monkeypatch.setattr(StateUploads, "require_no_successor", second_time_is_the_session)
        with pytest.raises(OperationError) as refused:
            reconcile(data, server, operation_id)
        assert (refused.value.code, refused.value.operation_id) == ("operation_conflict", other)
        assert source_record(data, operation_id) == before


# --- the public reconcile reaches a continuation like any other upload ----------------------------


def test_the_public_reconcile_asks_a_continuation_for_the_choice_before_it_reads_or_writes(
    prepared_input, certificates, monkeypatch
):
    """P02-3i removed the guard that refused a continuation: it is an upload like any other, so the
    missing consent is the same `approval_required` (naming the operation), before any request.
    The closing itself is pinned through the public API in test_upload_continuation_public."""
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        operation_id = left_unproved(data, provider, server, report.plan_id, monkeypatch)
        before, requests = journal(data, report.plan_id), len(server.requests)

        with pytest.raises(OperationError) as refused:
            recover_upload(
                operation_id, lambda plan: (data[3], data[4]), Path(data[0]), accepted=False
            )

        assert (refused.value.code, refused.value.operation_id) == (
            "approval_required",
            operation_id,
        )
        assert len(server.requests) == requests
        assert journal(data, report.plan_id) == before


def test_the_public_reconcile_of_original_uploads_answers_as_it_did_before_the_step(
    prepared_input, certificates, tmp_path
):
    """The guard that refuses a continuation is one more local look at the operation: for a v1/v2
    state it changes no code, no identity and no order (the answers pinned here are those of the
    tree before this step, which the review compared run for run)."""
    data, provider = three_files(prepared_input)
    load = lambda plan: (data[3], data[4])  # noqa: E731
    missing = "00000000-0000-4000-8000-0000000000aa"
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved_original(data, server)

        def answer(call):
            with pytest.raises(YorungeError) as error:
                call()
            return (
                type(error.value).__name__,
                error.value.code,
                getattr(error.value, "operation_id", None),
            )

        state = data[0]
        assert answer(lambda: recover_upload(missing, load, state, accepted=True)) == (
            "OperationError",
            "operation_not_found",
            missing,
        )
        assert answer(lambda: recover_upload(plan.plan_id, load, state, accepted=True)) == (
            "OperationError",
            "operation_not_found",
            plan.plan_id,
        )
        assert answer(
            lambda: recover_upload(missing, load, tmp_path / "no-store", accepted=True)
        ) == ("OperationError", "state_invalid", missing)
        for bad in (
            lambda: recover_upload("not-a-uuid", load, state, accepted=True),
            lambda: recover_upload(None, load, state, accepted=True),
            lambda: recover_upload(missing, load, state, accepted="yes"),
            lambda: recover_upload(missing, load, "a-str-is-not-a-path", accepted=True),
        ):
            assert answer(bad) == ("YorungeError", "invalid_request", None)
        source = interrupted(data, server)  # an original upload that stopped uncertain
        before = source_record(data, source)
        assert answer(lambda: recover_upload(source, load, state, accepted=False)) == (
            "OperationError",
            "approval_required",
            source,
        )
        assert source_record(data, source) == before  # no consent: nothing is touched
        assert answer(lambda: recover_upload(source, load, state, accepted=True)) == (
            "OperationError",
            "operation_uncertain",
            source,
        )
        after = source_record(data, source)  # the graph is not whole: the old local cleanup
        assert (after.status, after.reason) == ("unknown", "request_uncertain")
        assert (after.fence, after.revision) == (before.fence + 1, before.revision + 1)
