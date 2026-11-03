"""Local preflight priority on real SQLite; synthetic journal evidence only."""

from datetime import timedelta

import pytest

from tests.integration.test_create_receipt_writes import historical_running
from tests.integration.test_upload_journal import journal as journal
from tests.integration.test_upload_recovery_v2 import admit, complete, read_check
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_reconcile_local import ReadInput, ReadPhase, load_read_input
from yorunge.domain.errors import OperationError


def later(journal):
    journal.clock.value += timedelta(seconds=151)
    journal.clock.elapsed += 151


@pytest.mark.parametrize(
    "case,accepted,code",
    [
        ("active", True, "operation_conflict"),
        ("active", False, "operation_conflict"),
        ("terminal", True, "operation_conflict"),
        ("legacy", False, "operation_uncertain"),
        ("legacy", True, "operation_uncertain"),
        ("complete", False, "approval_required"),
        ("verified", False, "upload_plan_not_valid"),
        ("verified", True, "invalid_request"),
        ("incomplete", False, "approval_required"),
        ("incomplete", True, "operation_uncertain"),
        ("missing_id", False, "operation_uncertain"),
        ("missing_id_active", True, "operation_conflict"),
        ("unlatched_active", False, "operation_conflict"),
    ],
)
def test_local_rejection_priority_without_loading_credential(journal, case, accepted, code):
    if case.startswith("unlatched") or case.startswith("missing_id"):
        record = admit(journal, unknown=True)
        if case.startswith("missing_id"):
            journal.arm(record)
    elif case == "legacy":
        record, _ = historical_running(journal)
    else:
        record, proof = complete(
            journal, unknown=case != "verified", skip_last=case == "incomplete"
        )
        if case == "terminal":
            with open_existing_store(journal.root) as store:
                journal.repository(store).verified(
                    record.operation_id, record.lease, proof, authorization=read_check(journal)
                )
    if case not in {"active", "missing_id_active", "unlatched_active", "terminal", "legacy"}:
        later(journal)
    with open_existing_store(journal.root) as store:
        previous = journal.repository(store).show(operation_id=record.operation_id)
    with pytest.raises(OperationError) as raised:
        load_read_input(record.operation_id, journal.root, accepted, journal.clock)
    assert raised.value.code == code and raised.value.operation_id == record.operation_id
    with open_existing_store(journal.root) as store:
        view = journal.repository(store).show(operation_id=record.operation_id)
        if code in {"approval_required", "operation_conflict"}:
            assert view == previous
        if case == "missing_id" or (case == "incomplete" and accepted):
            assert view.operation.status == "unknown" and view.operation.lease is None
        assert store.verify().store_schema_version == 7


def test_unlatched_expiry_cleanup_needs_neither_flag_nor_credential(journal):
    record = admit(journal, unknown=True)
    later(journal)
    result = load_read_input(record.operation_id, journal.root, False, journal.clock)
    assert isinstance(result, ReadPhase) and result.authorization is None
    assert result.record.status == "cancelled" and result.record.lease is None
    assert result.record.operation_id == record.operation_id


def test_complete_true_returns_db_manifest_and_original_baseline_without_mutation(journal):
    record, _ = complete(journal)
    later(journal)
    with open_existing_store(journal.root) as store:
        before = journal.repository(store).show(operation_id=record.operation_id)
    result = load_read_input(record.operation_id, journal.root, True, journal.clock)
    assert isinstance(result, ReadInput) and result.manifest == journal.manifest
    assert result.plan == journal.plan and result.record == before.operation
    assert result.baseline.id == record.dataset_id
    with open_existing_store(journal.root) as store:
        assert journal.repository(store).show(operation_id=record.operation_id) == before
        assert store.verify().store_schema_version == 7
