"""P02-3x round two (reviewer B): the successor gate over hostile or busy stores, the public answer
for a source that has a continuation, the stamp of a proof and a check that goes stale.

The gate is local and runs in the write transaction, so the store tests build their histories
directly (``tests/fixtures/continuation_history.py``) and use no provider; the rest run the real
reconcile against the loopback provider of the other 3x files.
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.fixtures.continuation_history import FIRST, UNKNOWN, world
from tests.fixtures.http_server import TlsServer
from tests.integration.test_upload_continuation_reconcile import (
    left_unproved,
    reconcile,
    source_record,
    store_is_valid,
)
from tests.integration.test_upload_continuation_stages import (
    Skewed,
    journal,
    operation_of,
    planned,
    start,
)
from tests.integration.test_upload_continuation_start import admit_only, approve
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_resume_observation import certificates as certificates
from tests.integration.test_upload_resume_observation import loopback_only as loopback_only
from tests.integration.test_upload_resume_observation import world as three_files
from yorunge.adapters.platform_upload_port import ObservedUploadPort
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_api import recover_upload
from yorunge.adapters.upload_repository import StateUploads
from yorunge.domain.capabilities import instant
from yorunge.domain.errors import OperationError


def _rows(state):
    with open_existing_store(state) as store:
        return [
            store.connection.execute(f"SELECT * FROM {table} ORDER BY 1,2").fetchall()
            for table in (
                "upload_plans",
                "upload_approvals",
                "upload_operations",
                "upload_controls",
                "upload_stage_intents",
                "upload_stage_receipts",
                "upload_verifications",
            )
        ]


def _root(state):
    with open_existing_store(state) as store:
        return store.connection.execute(
            "SELECT operation_id FROM upload_operations WHERE operation_id<>? LIMIT 1", (FIRST,)
        ).fetchone()[0]


def _unrelated_garbage_row(state):
    connection = sqlite3.connect(str(Path(state) / "state.sqlite3"), isolation_level=None)
    try:
        plan = connection.execute(
            "SELECT intent_digest,manifest_digest FROM upload_plans LIMIT 1"
        ).fetchone()
        stamp = "2026-11-08T09:00:00.000000Z"
        connection.execute(
            "INSERT INTO upload_plans VALUES(?,?,?,?,?,?)",
            ("11111111-1111-4111-8111-111111111111", plan[0], plan[1], stamp, stamp, "{not json"),
        )
        connection.execute(
            "INSERT INTO upload_operations VALUES(?,?,?,?,?,?,?)",
            (
                "22222222-2222-4222-8222-222222222222",
                "11111111-1111-4111-8111-111111111111",
                plan[0],
                1,
                None,
                1,
                "{not json",
            ),
        )
    finally:
        connection.close()


def _gates(state, operation_id):
    with open_existing_store(state) as store:
        repository = StateUploads(store)
        yield "require_no_successor", lambda: repository.require_no_successor(operation_id)
        yield "cleanup_expired", lambda: repository.cleanup_expired(operation_id)
        yield (
            "acquire_read",
            lambda: repository.acquire_read(operation_id, accept_unverified_read=True),
        )


def test_an_unreadable_unrelated_row_closes_the_gate_as_state_invalid_naming_the_row(tmp_path):
    with world(tmp_path, UNKNOWN):
        pass
    state = tmp_path / "state"
    _unrelated_garbage_row(state)
    before = _rows(state)
    for name, call in _gates(state, FIRST):  # the continuation (a leaf) asks: nothing to find
        with pytest.raises(OperationError) as refused:
            call()
        assert (refused.value.code, refused.value.operation_id) == (
            "state_invalid",
            "22222222-2222-4222-8222-222222222222",
        ), name
    assert _rows(state) == before  # nothing is written


def test_a_row_whose_plan_is_gone_is_state_invalid_not_a_missing_plan(tmp_path):
    with world(tmp_path, UNKNOWN) as (store, root, built):
        source = root["record"]["operation_id"]
        plan_id = built[0].plan["plan_id"]
    state = tmp_path / "state"
    connection = sqlite3.connect(str(state / "state.sqlite3"), isolation_level=None)
    connection.execute("PRAGMA foreign_keys=OFF")
    connection.execute("DELETE FROM upload_approvals WHERE plan_id=?", (plan_id,))
    connection.execute("DELETE FROM upload_controls WHERE operation_id=?", (FIRST,))
    connection.execute(
        "DELETE FROM upload_stage_receipts WHERE intent_id IN "
        "(SELECT intent_id FROM upload_stage_intents WHERE operation_id=?)",
        (FIRST,),
    )
    connection.execute("DELETE FROM upload_stage_intents WHERE operation_id=?", (FIRST,))
    connection.execute("DELETE FROM upload_plans WHERE plan_id=?", (plan_id,))
    connection.close()
    for name, call in _gates(state, source):
        with pytest.raises(OperationError) as refused:
            call()
        assert refused.value.code == "state_invalid", (name, refused.value.code)


def test_the_gate_answers_busy_not_a_raw_sqlite_error_while_another_writer_holds_the_store(
    tmp_path,
):
    with world(tmp_path, UNKNOWN) as (store, root, built):
        source = root["record"]["operation_id"]
    state = tmp_path / "state"
    holder = sqlite3.connect(str(state / "state.sqlite3"), isolation_level=None)
    holder.execute("BEGIN IMMEDIATE")
    try:
        with open_existing_store(state) as store:
            with pytest.raises(OperationError) as busy:
                StateUploads(store).require_no_successor(source)
    finally:
        holder.execute("ROLLBACK")
        holder.close()
    assert busy.value.code == "state_busy"
    assert busy.value.operation_id == source


@pytest.mark.parametrize("accepted", [True, False])
def test_the_public_reconcile_of_a_source_with_a_continuation_names_the_continuation(
    prepared_input, certificates, accepted
):
    """The error is the successor's: the public wrapper must not put the asked id back."""
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        start(data, server, report.plan_id, algorithm=admit_only)  # admitted, nothing sent
        source = journal(data, report.plan_id).plan.continuation.source_operation_id
        successor = operation_of(data, report.plan_id)
        requests = len(server.requests)

        def forbidden(plan):
            pytest.fail("a refused reconcile asks for no context")

        with pytest.raises(OperationError) as refused:
            recover_upload(source, forbidden, Path(data[0]), accepted=accepted)

        assert refused.value.code == "operation_conflict"
        assert refused.value.operation_id == successor.operation_id != source
        assert len(server.requests) == requests


def test_the_proof_of_a_reconcile_is_observed_before_the_listing_starts(
    prepared_input, certificates, monkeypatch
):
    """A proof stamped after its listing would claim a fresher look than the data it holds."""
    data, provider = three_files(prepared_input)
    started = []
    original = ObservedUploadPort.items

    async def items(port, *args, **kwargs):
        started.append(datetime.now(UTC))
        return await original(port, *args, **kwargs)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        operation_id = left_unproved(data, provider, server, report.plan_id, monkeypatch)
        monkeypatch.setattr(ObservedUploadPort, "items", items)
        phase = reconcile(data, server, operation_id)
        proof = journal(data, report.plan_id).verification
        assert phase.record.status == "succeeded"
        assert len(started) == 1
        assert instant(proof.observed_at) <= started[0]


@pytest.mark.parametrize("after", ["acquire_read", "prepare_recovery_read"])
def test_a_check_that_goes_stale_inside_the_session_stops_before_the_listing(
    prepared_input, certificates, monkeypatch, after
):
    """30 s from the probe to the proof is the freshness rule: a jump past it sends no listing."""
    data, provider = three_files(prepared_input)
    clock = Skewed()
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        operation_id = left_unproved(data, provider, server, report.plan_id, monkeypatch)
        original = getattr(StateUploads, after)

        def gate(repository, *args, **kwargs):
            result = original(repository, *args, **kwargs)
            clock.skew += 31
            return result

        monkeypatch.setattr(StateUploads, after, gate)
        requests = len(server.requests)
        with pytest.raises(OperationError) as raised:
            reconcile(data, server, operation_id, clock=clock)
        assert (raised.value.code, raised.value.operation_id) == (
            "upload_plan_not_valid",
            operation_id,
        )
        assert not any("/items" in r.path for r in server.requests[requests:])
        record = source_record(data, operation_id)
        assert (record.status, record.reason, record.lease) == (
            "unknown",
            "request_uncertain",
            None,
        )
        assert journal(data, report.plan_id).verification is None
        store_is_valid(data)
