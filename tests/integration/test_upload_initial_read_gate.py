"""No new lease or permission: initial metadata reads use an active original owner."""

from datetime import timedelta
from uuid import uuid4

import pytest

from tests.integration.test_create_receipt_writes import historical_running
from tests.integration.test_upload_journal import journal as journal
from tests.integration.test_upload_recovery_v2 import complete, read_check
from yorunge.adapters.state import open_existing_store
from yorunge.domain.capabilities import timestamp
from yorunge.domain.errors import OperationError


def test_initial_read_gate_returns_only_current_access_without_mutation(journal):
    record, _ = complete(journal)
    with open_existing_store(journal.root) as store:
        repo = journal.repository(store)
        before = repo.show(operation_id=record.operation_id)
        assert repo.prepare_initial_read(record.operation_id, record.lease) is None
        access = repo.prepare_initial_read(
            record.operation_id, record.lease, authorization=read_check(journal)
        )
        assert access.policy == "explicit_read_attempt"
        assert access.grant is None
        assert access.scope == journal.plan.scope
        assert repo.show(operation_id=record.operation_id) == before
        assert store.verify().store_schema_version == 7


@pytest.mark.parametrize(
    "failure,code",
    [
        ("incomplete", "operation_uncertain"),
        ("legacy", "operation_uncertain"),
        ("revoked", "approval_required"),
        ("wrong_owner", "operation_lease_lost"),
        ("expired", "operation_lease_lost"),
        ("terminal", "operation_conflict"),
        ("denied", "remote_access_denied"),
        ("stale", "upload_plan_not_valid"),
        ("foreign", "state_changed"),
    ],
)
def test_initial_read_gate_closes_before_network(journal, failure, code):
    if failure == "legacy":
        record, _ = historical_running(journal)
    else:
        record, proof = complete(journal, skip_last=failure == "incomplete")
    owner, check = record.lease, None
    with open_existing_store(journal.root) as store:
        repo = journal.repository(store)
        if failure == "revoked":
            repo.revoke(journal.plan.plan_id, journal.plan.digest)
        elif failure == "terminal":
            repo.verified(record.operation_id, owner, proof, authorization=read_check(journal))
        elif failure == "wrong_owner":
            owner = owner.model_copy(update={"owner_id": str(uuid4())})
        elif failure == "expired":
            journal.clock.value += timedelta(seconds=151)
        elif failure == "denied":
            check = read_check(journal, outcome="denied", code="remote_access_denied")
        elif failure == "stale":
            check = read_check(journal).model_copy(
                update={"checked_at": timestamp(journal.clock.value - timedelta(seconds=31))}
            )
        elif failure == "foreign":
            check = read_check(journal).model_copy(update={"dataset_id": str(uuid4())})
        with pytest.raises(OperationError) as raised:
            repo.prepare_initial_read(record.operation_id, owner, authorization=check)
        assert raised.value.code == code
        assert raised.value.operation_id == record.operation_id
        assert (
            repo.show(operation_id=record.operation_id).verification is None
            or failure == "terminal"
        )
        assert store.verify().store_schema_version == 7
