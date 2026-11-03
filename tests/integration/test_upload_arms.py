"""Actual committed arm identity/deadline and private issuance lifecycle."""

import copy
import multiprocessing
import pickle
import threading
from functools import partial
from types import SimpleNamespace

import pytest

from tests.integration.test_upload_journal import journal as journal
from yorunge.adapters import upload_repository
from yorunge.adapters.state import open_store
from yorunge.application import upload_arms
from yorunge.application.operations import DispatchPermit
from yorunge.application.upload_arms import UploadArm
from yorunge.domain.errors import OperationError, YorungeError


def issued(journal):
    record = journal.approved()
    return record, journal.arm(record)


def test_repository_issues_one_immutable_arm_with_legacy_tuple_view(journal):
    record, arm = issued(journal)
    assert type(arm) is UploadArm
    assert len(arm) == 3
    intent, permit, deadline = arm
    assert type(permit) is DispatchPermit
    assert arm[0] == intent
    assert arm[1] is permit
    assert arm[-1] == deadline
    assert arm[:] == (intent, permit, deadline)
    assert arm.deadline == deadline
    assert arm.intent == intent
    with open_store(journal.root) as store:
        stored = journal.repository(store).show(operation_id=record.operation_id)
        assert stored.intents == (intent,)
        assert stored.operation.workflow_latched
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
    assert "operation_id" not in repr(arm)
    assert arm.intent.operation_id not in repr(arm)
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
    assert raised.value.code == "execution_timeout"
    assert raised.value.operation_id == record.operation_id
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
    assert not worker.is_alive()
    assert failures == ["operation_conflict"]
    assert arm.claim()[0] == arm.intent


def test_sequential_thread_cannot_claim_after_issuer_exits(journal, monkeypatch):
    arms = []
    failures = []
    # Force a recycled numeric ID on every platform. The actual issuer and
    # claimant remain two separate real Thread objects, with no arm mutation.
    monkeypatch.setattr(
        upload_arms,
        "threading",
        SimpleNamespace(get_ident=lambda: 17, current_thread=threading.current_thread),
    )

    def issue():
        arms.append(issued(journal)[1])

    issuer = threading.Thread(target=issue)
    issuer.start()
    issuer.join(5)
    assert not issuer.is_alive()
    assert len(arms) == 1

    def claim():
        try:
            arms[0].claim()
        except OperationError as error:
            failures.append(error.code)

    claimant = threading.Thread(target=claim)
    claimant.start()
    claimant.join(5)
    assert not claimant.is_alive()
    assert failures == ["operation_conflict"]


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
        assert parent.poll(5)
        assert parent.recv() == "operation_conflict"
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
        rejected_call = partial(
            repo.arm,
            record.operation_id,
            record.lease,
            journal.plan,
            "create",
            None,
            total_end=journal.clock.monotonic() + 900,
        )
        with pytest.raises(OperationError) as raised:
            rejected_call()
        assert raised.value.code == (
            "state_changed" if failure == "transaction" else "operation_uncertain"
        )
        assert raised.value.operation_id == record.operation_id
        assert len(issued_calls) == int(failure == "issuance")
        view = repo.show(operation_id=record.operation_id)
        assert len(view.intents) == int(failure != "transaction")
        assert not view.receipts
