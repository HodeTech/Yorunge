"""What the reconcile of a continuation relies on, pinned one rule at a time (P02-3x review).

The rule that a source with a successor is history is enforced by the repository inside the write
transaction (a pre-check is not a lock), it does not count a successor whose lease has lapsed in
``admitted``, and the store's own gate refuses whatever a failing authorization would also refuse.
A continuation killed with every receipt but without its proof is reconciled after the lease of the
dead owner has lapsed, a failing probe or listing leaves it ``unknown`` and retried, and a chain of
continuations is proved at its tip without touching its ancestors.
"""

from contextlib import contextmanager
from pathlib import Path

import pytest

from tests.fixtures.http_server import Reply, TlsServer
from tests.integration.test_upload_continuation_reconcile import (
    left_unproved,
    reconcile,
    source_record,
    store_is_valid,
)
from tests.integration.test_upload_continuation_stages import (
    CONFIRM,
    Skewed,
    five_of_eight,
    journal,
    operation_of,
    planned,
    start,
)
from tests.integration.test_upload_continuation_start import ITEMS, admit_only, approve, go
from tests.integration.test_upload_continuation_start_gaps import lose_confirm
from tests.integration.test_upload_continuation_start_kill import kill_at
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_resume_observation import (
    certificates as certificates,
)
from tests.integration.test_upload_resume_observation import (
    loopback_only as loopback_only,
)
from tests.integration.test_upload_resume_observation import world as three_files
from tests.integration.test_upload_resume_prepare import prepared
from yorunge import api
from yorunge.adapters import upload_repository as repository_module
from yorunge.adapters.capability_cache import StateCache
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_read_access import ReadAccess
from yorunge.adapters.upload_repository import StateUploads
from yorunge.domain.errors import OperationError


def stub_authorization(monkeypatch):
    """The read is authorised whatever the check says: what refuses is the gate, nothing else."""

    def authorize(repository, view, stamp, gate, **_):
        return ReadAccess(view.plan.scope, "explicit_read_attempt", None)

    monkeypatch.setattr(repository_module, "authorize_read", authorize)


def test_a_source_whose_continuation_lapsed_in_admitted_is_reconciled_as_it_always_was(
    prepared_input, certificates
):
    """An admitted continuation whose lease lapsed, and that nobody cancelled, is no successor."""
    data, provider = three_files(prepared_input)
    clock = Skewed()
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        start(data, server, report.plan_id, algorithm=admit_only, clock=clock)
        source = journal(data, report.plan_id).plan.continuation.source_operation_id
        assert operation_of(data, report.plan_id).status == "admitted"
        clock.skew += 200  # the lease lapses; nobody cancels it
        before = source_record(data, source)

        with pytest.raises(OperationError) as uncertain:
            reconcile(data, server, source, clock=clock)

        assert (uncertain.value.code, uncertain.value.operation_id) == (
            "operation_uncertain",
            source,
        )
        after = source_record(data, source)
        assert after.status == "unknown"
        assert after.fence > before.fence
        assert operation_of(data, report.plan_id).status == "admitted"  # left for the next prepare
        store_is_valid(data)


@pytest.mark.parametrize("how", ["live", "done"])
def test_acquire_read_alone_refuses_a_source_with_a_continuation_whatever_the_check_says(
    prepared_input, certificates, monkeypatch, how
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        if how == "live":
            start(data, server, report.plan_id, algorithm=admit_only)
        else:
            go(data, server, report.plan_id)
        source = journal(data, report.plan_id).plan.continuation.source_operation_id
        successor = operation_of(data, report.plan_id)
        before = source_record(data, source)
        stub_authorization(monkeypatch)
        with open_existing_store(data[0]) as store:
            with pytest.raises(OperationError) as refused:
                StateUploads(store).acquire_read(source, accept_unverified_read=True)
        assert refused.value.code == "operation_conflict"
        assert refused.value.operation_id == successor.operation_id
        assert source_record(data, source) == before  # no lease, no fence, no reason
        store_is_valid(data)


@contextmanager
def admission_before_the_write_transaction(monkeypatch, admit):
    """Another process admits the continuation just before the repository opens its write
    transaction: after every pre-check of the call, before ``BEGIN IMMEDIATE``."""
    original = StateCache.transaction
    fired = []

    @contextmanager
    def transaction(cache, *args, **kwargs):
        if not fired:
            fired.append(True)
            admit()
        with original(cache, *args, **kwargs) as gate:
            yield gate

    monkeypatch.setattr(StateCache, "transaction", transaction)
    try:
        yield fired
    finally:
        monkeypatch.setattr(StateCache, "transaction", original)


@pytest.mark.parametrize("call", ["cleanup_expired", "acquire_read"])
def test_a_continuation_admitted_between_the_prechecks_and_the_transaction_still_stops_the_call(
    prepared_input, certificates, monkeypatch, call
):
    """The gate runs INSIDE the write transaction: a pre-check is not a lock."""
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)  # approved, not admitted
        source = journal(data, report.plan_id).plan.continuation.source_operation_id
        before = source_record(data, source)
        stub_authorization(monkeypatch)

        def admit():
            start(data, server, report.plan_id, algorithm=admit_only)

        with open_existing_store(data[0]) as store:
            repository = StateUploads(store)
            with admission_before_the_write_transaction(monkeypatch, admit) as fired:
                with pytest.raises(OperationError) as refused:
                    if call == "cleanup_expired":
                        repository.cleanup_expired(source)
                    else:
                        repository.acquire_read(source, accept_unverified_read=True)
            assert fired
        successor = operation_of(data, report.plan_id)
        assert successor is not None
        assert successor.status == "admitted"
        assert refused.value.code == "operation_conflict"
        assert refused.value.operation_id == successor.operation_id
        assert source_record(data, source) == before
        store_is_valid(data)


@pytest.mark.parametrize("boundary", ["proof_gate", "proof_look", "proof_listing"])
def test_a_continuation_killed_in_running_with_every_receipt_is_reconciled_after_its_lease_lapses(
    prepared_input, certificates, monkeypatch, boundary
):
    """The natural crash window of the start: ``running``, 3M receipts, the closing read undone."""
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        kill_at(data, server, provider, report.plan_id, boundary, certificates)
        view = journal(data, report.plan_id)
        operation = view.operation
        assert (operation.status, operation.lease is not None) == ("running", True)
        assert len(view.intents) == len(view.receipts) == 3
        assert view.verification is None
        requests = len(server.requests)
        with pytest.raises(OperationError) as live:  # the dead owner's lease still stands
            reconcile(data, server, operation.operation_id)
        assert live.value.code == "operation_conflict"
        assert len(server.requests) == requests
        clock = Skewed()
        clock.skew = 200
        phase = reconcile(data, server, operation.operation_id, clock=clock)
        record = phase.record
        assert (record.status, record.reason) == ("succeeded", "metadata_verified")
        assert record.operation_id == operation.operation_id
        assert record.lease is None
        after = journal(data, report.plan_id)
        assert len(after.verification.files) == 3
        assert after.intents == view.intents
        assert after.receipts == view.receipts
        store_is_valid(data)


@pytest.mark.parametrize("failing", ["me", "items"])
def test_a_running_complete_continuation_that_meets_a_failing_read_ends_unknown_and_is_retried(
    prepared_input, certificates, monkeypatch, failing
):
    """``running``, 3M receipts and a lapsed write lease: the probe or the listing answers 403."""
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        kill_at(data, server, provider, report.plan_id, "proof_gate", certificates)
        operation = operation_of(data, report.plan_id)
        assert operation.status == "running"
        path = "/api/v1/auth/me" if failing == "me" else ITEMS
        real = provider.route_table[path]
        provider.route_table[path] = lambda request, count: Reply(status=403, body=b"{}")
        clock = Skewed()
        clock.skew = 200
        with pytest.raises(OperationError) as raised:
            reconcile(data, server, operation.operation_id, clock=clock)
        assert raised.value.code == "remote_access_denied"
        assert raised.value.operation_id == operation.operation_id
        view = journal(data, report.plan_id)
        assert (view.operation.status, view.operation.reason) == ("unknown", "read_unavailable")
        assert view.operation.lease is None
        assert view.verification is None
        assert len(view.intents) == len(view.receipts) == 3
        store_is_valid(data)
        provider.route_table[path] = real
        phase = reconcile(data, server, operation.operation_id, clock=clock)
        assert (phase.record.status, phase.record.reason) == ("succeeded", "metadata_verified")
        store_is_valid(data)


def test_a_continuation_of_a_continuation_is_proved_and_neither_ancestor_is_touched(
    prepared_input, certificates, monkeypatch
):
    """Depth 2: S (root) -> C1 (cut short) -> C2 (all stages done, proof missing)."""
    data, provider = five_of_eight(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report1 = planned(data, server, provider)
        approve(data, server, report1.plan_id)
        original = lose_confirm(provider, "f06.bin", remembered=False)
        with pytest.raises(OperationError) as stopped:
            go(data, server, report1.plan_id)
        assert stopped.value.code == "operation_uncertain"
        provider.route_table[CONFIRM] = original
        c1 = operation_of(data, report1.plan_id)
        root = report1.source_operation_id
        report2 = prepared(data, server, c1.operation_id, accept_unconfirmed_effects=True)
        approve(data, server, report2.plan_id)
        c2 = left_unproved(data, provider, server, report2.plan_id, monkeypatch)
        before = {name: source_record(data, name) for name in (root, c1.operation_id)}
        requests = len(server.requests)

        phase = reconcile(data, server, c2)

        assert (phase.record.operation_id, phase.record.status, phase.record.reason) == (
            c2,
            "succeeded",
            "metadata_verified",
        )
        assert all(r.method == "GET" for r in server.requests[requests:])
        # the ancestors are history: untouched by the reconcile of their descendant
        assert {name: source_record(data, name) for name in before} == before
        store_is_valid(data)
        # and each ancestor names its own successor, not the tip of the chain
        for ancestor, successor in ((root, c1.operation_id), (c1.operation_id, c2)):
            with pytest.raises(OperationError) as refused:
                reconcile(data, server, ancestor)
            assert (refused.value.code, refused.value.operation_id) == (
                "operation_conflict",
                successor,
            )
        assert {name: source_record(data, name) for name in before} == before


def test_a_continuations_reconcile_makes_six_reads_and_holds_no_lock_while_it_waits(
    prepared_input, certificates, monkeypatch
):
    """The v2 reconcile's cost and manners, kept: six GETs, and the store is free in between."""
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        operation = left_unproved(data, provider, server, report.plan_id, monkeypatch)
        locks = []

        def unlocked():
            with open_existing_store(data[0]) as store:
                store.connection.execute("BEGIN IMMEDIATE")
                store.connection.rollback()
            locks.append(True)

        provider.on_request = unlocked
        count = len(server.requests)
        phase = reconcile(data, server, operation)
        requests = server.requests[count:]
        assert len(requests) == len(locks) == 6
        assert all(r.method == "GET" for r in requests)
        assert (phase.record.status, phase.record.reason) == ("succeeded", "metadata_verified")
        store_is_valid(data)


def test_the_local_form_of_the_gate_binds_a_failing_store_to_the_source_it_was_asked_about(
    tmp_path, monkeypatch
):
    """A store that cannot take the clock's trace is a closed error of that operation, not raw."""
    import sqlite3

    state = tmp_path / "state"
    api.initialize_state(state_dir=state)
    source = "00000000-0000-4000-8000-0000000000f1"

    def busy(self, *args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(StateCache, "stamp", busy)
    with open_existing_store(state) as store:
        with pytest.raises(OperationError) as refused:
            StateUploads(store).require_no_successor(source)
    assert refused.value.code in {"state_busy", "state_invalid"}
    assert refused.value.operation_id == source
