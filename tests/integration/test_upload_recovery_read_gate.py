"""Recovery gate and optional proof deadline on real state; synthetic journal evidence."""

from datetime import timedelta
from uuid import uuid4

import pytest

from tests.integration.test_upload_journal import journal as journal
from tests.integration.test_upload_recovery_v2 import complete, read_check
from yorunge.adapters.state import open_existing_store
from yorunge.domain.errors import OperationError


def acquired(journal):
    record, proof = complete(journal)
    journal.clock.value += timedelta(seconds=151)
    journal.clock.elapsed += 151
    check = read_check(journal)
    with open_existing_store(journal.root) as store:
        owner = journal.repository(store).acquire_read(
            record.operation_id, authorization=check, accept_unverified_read=True
        )
    return record.operation_id, owner, check, proof


def test_pre_items_gate_checks_current_read_without_renewing_or_rewriting(journal):
    operation_id, owner, check, _ = acquired(journal)
    with open_existing_store(journal.root) as store:
        repository = journal.repository(store)
        before = repository.show(operation_id=operation_id)
        access = repository.prepare_recovery_read(
            operation_id, owner, check, accept_unverified_read=True
        )
        assert access.policy == "explicit_read_attempt" and access.grant is None
        assert access.scope == check.scope
        assert repository.show(operation_id=operation_id) == before
        assert store.verify().store_schema_version == 7


@pytest.mark.parametrize(
    "failure,code",
    [
        ("owner", "operation_lease_lost"),
        ("expired", "operation_lease_lost"),
        ("consent", "approval_required"),
        ("scope", "state_changed"),
        ("invalid", "invalid_request"),
    ],
)
def test_recovery_gate_rejects_without_new_ownership(journal, failure, code):
    operation_id, owner, check, _ = acquired(journal)
    if failure == "owner":
        owner = owner.model_copy(update={"owner_id": str(uuid4())})
    elif failure == "expired":
        journal.clock.value += timedelta(seconds=151)
        journal.clock.elapsed += 151
        check = read_check(journal)
    elif failure == "scope":
        check = check.model_copy(update={"dataset_id": str(uuid4())})
    elif failure == "invalid":
        check = check.model_copy(update={"policy_version": "2"})
    with open_existing_store(journal.root) as store:
        repository = journal.repository(store)
        before = repository.show(operation_id=operation_id)
        with pytest.raises(OperationError) as raised:
            repository.prepare_recovery_read(
                operation_id, owner, check, accept_unverified_read=failure != "consent"
            )
        assert raised.value.code == code and raised.value.operation_id == operation_id
        assert repository.show(operation_id=operation_id) == before
        assert store.verify().store_schema_version == 7


@pytest.mark.parametrize("deadline", [True, "30", float("nan"), float("inf"), 10**1000])
def test_invalid_proof_deadline_cannot_disable_the_budget_or_mutate_history(journal, deadline):
    operation_id, owner, _, _ = acquired(journal)
    with open_existing_store(journal.root) as store:
        repository = journal.repository(store)
        before = repository.show(operation_id=operation_id)
        with pytest.raises(OperationError) as raised:
            repository.verified(operation_id, owner, None, deadline=deadline)
        assert raised.value.code == "invalid_request" and raised.value.operation_id == operation_id
        assert repository.show(operation_id=operation_id) == before
        assert store.verify().store_schema_version == 7
