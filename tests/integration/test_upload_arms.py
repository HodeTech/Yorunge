"""Actual committed arm identity/deadline and private issuance lifecycle."""

import copy
import multiprocessing
import pickle
import threading

import pytest

from tests.integration.test_upload_journal import journal as journal
from yorunge.adapters import upload_repository
from yorunge.adapters.state import open_store
from yorunge.application.operations import DispatchPermit
from yorunge.application.upload_arms import UploadArm
from yorunge.domain.errors import OperationError, YorungeError


def issued(journal):
    record = journal.approved()
    return record, journal.arm(record)


def test_repository_issues_one_immutable_arm_with_legacy_tuple_view(journal):
    record, arm = issued(journal)
    assert type(arm) is UploadArm and len(arm) == 3
    intent, permit, deadline = arm
    assert type(permit) is DispatchPermit
    assert arm[0] == intent and arm[1] is permit and arm[-1] == deadline
    assert arm[:] == (intent, permit, deadline)
    assert arm.deadline == deadline and arm.intent == intent
    with open_store(journal.root) as store:
        stored = journal.repository(store).show(operation_id=record.operation_id)
        assert stored.intents == (intent,) and stored.operation.workflow_latched
    claimed = arm.claim()
    assert claimed == (intent, permit, deadline)
    # The generic permit is consumed only at the actual HTTP boundary.
    permit.consume()
    with pytest.raises(OperationError) as raised:
        permit.consume()
    assert raised.value.code == "operation_conflict"
    with pytest.raises(OperationError) as raised:
        arm.claim()
    assert raised.value.operation_id == record.operation_id


def test_callers_cannot_construct_or_mutate_or_reencode_issued_parts(journal):
    _, arm = issued(journal)
    with pytest.raises(YorungeError) as raised:
        UploadArm(None, arm.intent, arm.deadline, journal.clock.monotonic)
    assert raised.value.code == "invalid_request"
    for attribute, value in [("deadline", arm.deadline + 100), ("_deadline", arm.deadline + 100)]:
        with pytest.raises(AttributeError):
            setattr(arm, attribute, value)
    observed = arm.intent
    observed.__dict__["request_digest"] = "0" * 64
    assert arm.intent.request_digest != observed.request_digest
    observed.owner.__dict__["expires_at"] = "2099-01-01T00:00:00.000000Z"
    assert arm.intent.owner.expires_at != observed.owner.expires_at
    assert "operation_id" not in repr(arm) and arm.intent.operation_id not in repr(arm)
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(TypeError):
            operation(arm)
    assert arm.claim()[2] == arm.deadline


def test_claim_expiry_does_not_extend_the_issued_deadline(journal):
    record, arm = issued(journal)
    original = arm.deadline
    journal.clock.elapsed += 1000
    with pytest.raises(OperationError) as raised:
        arm.claim()
    assert (
        raised.value.code == "execution_timeout"
        and raised.value.operation_id == record.operation_id
    )
    assert arm.deadline == original


def test_other_thread_cannot_claim_but_original_owner_can(journal):
    _, arm = issued(journal)
    failures = []

    def other():
        try:
            arm.claim()
        except OperationError as error:
            failures.append(error.code)

    worker = threading.Thread(target=other)
    worker.start()
    worker.join(5)
    assert not worker.is_alive() and failures == ["operation_conflict"]
    assert arm.claim()[0] == arm.intent


def test_forked_child_cannot_claim_parent_arm(journal):
    _, arm = issued(journal)
    context = multiprocessing.get_context("fork")
    parent, child = context.Pipe()

    def worker():
        try:
            arm.claim()
        except OperationError as error:
            child.send(error.code)

    process = context.Process(target=worker)
    process.start()
    child.close()
    try:
        assert parent.poll(5) and parent.recv() == "operation_conflict"
        process.join(5)
        assert process.exitcode == 0
        assert arm.claim()[0] == arm.intent
    finally:
        if process.is_alive():
            process.kill()
            process.join(5)
        parent.close()


@pytest.mark.parametrize("failure", ["transaction", "finish", "issuance"])
def test_no_arm_escapes_failed_transaction_or_final_gate(journal, monkeypatch, failure):
    record = journal.approved()
    issued_calls = []
    original = upload_repository._issue_upload_arm

    def mint(*args):
        issued_calls.append(True)
        if failure == "issuance":
            raise YorungeError("execution_timeout")
        return original(*args)

    monkeypatch.setattr(upload_repository, "_issue_upload_arm", mint)

    def fail(*args, **kwargs):
        raise YorungeError("state_changed")

    with open_store(journal.root) as store:
        repo = journal.repository(store)
        if failure == "transaction":
            monkeypatch.setattr(repo, "_change", fail)
        elif failure == "finish":
            monkeypatch.setattr(repo, "_finish", fail)
        with pytest.raises(OperationError) as raised:
            repo.arm(
                record.operation_id,
                record.lease,
                journal.plan,
                "create",
                None,
                total_end=journal.clock.monotonic() + 900,
            )
        assert raised.value.code == (
            "state_changed" if failure == "transaction" else "operation_uncertain"
        )
        assert raised.value.operation_id == record.operation_id
        assert len(issued_calls) == int(failure == "issuance")
        view = repo.show(operation_id=record.operation_id)
        assert len(view.intents) == int(failure != "transaction")
        assert not view.receipts
