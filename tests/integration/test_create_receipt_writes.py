"""Atomic new receipt writes and no new rights from legacy missing baselines."""

import multiprocessing
import time
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
from functools import partial
from pathlib import Path
from uuid import uuid4

import pytest

from tests.contracts.test_upload_versions import graph
from tests.fixtures.upload_receipts import accepted_create
from tests.integration.test_upload_journal import DATASET
from tests.integration.test_upload_journal import journal as journal
from tests.integration.test_upload_versioned_history import install_fixture
from yorunge.adapters.capability_cache import StateCache
from yorunge.adapters.state import open_store
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import created_dataset, legacy_create_without_baseline
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.create_receipt import CreateReceiptV2
from yorunge.domain.dataset_transfer import StageReceipt
from yorunge.domain.errors import OperationError, YorungeError


def legacy_receipt(intent, at):
    return StageReceipt(
        schema_version=1,
        intent_id=intent.intent_id,
        recorded_at=at,
        result="accepted",
        dataset_id=DATASET,
        object_key=None,
        sent_bytes=None,
        sent_sha256=None,
    )


def armed(journal):
    record = journal.approved()
    intent, permit, _ = journal.arm(record)
    return record, intent, permit


def historical_running(journal):
    """Emulate an already persisted old-binary row, never a new receipt writer."""
    record, intent, _ = armed(journal)
    view = journal.accept(record, intent)
    old = legacy_receipt(intent, timestamp(journal.clock.value))
    with open_store(journal.root) as store:
        store.connection.execute(
            "UPDATE upload_stage_receipts SET payload=? WHERE intent_id=?",
            (old.encoded().decode(), intent.intent_id),
        )
        store.verify()
        assert legacy_create_without_baseline(
            journal.repository(store).show(operation_id=record.operation_id)
        )
    return view.operation, intent


def test_new_v2_cannot_insert_new_v1_accepted_create(journal):
    record, intent, _ = armed(journal)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        before = repo.show(operation_id=record.operation_id).operation.encoded()
        rejected_call = partial(
            repo.receipt,
            record.operation_id,
            record.lease,
            legacy_receipt(intent, record.created_at),
        )
        with pytest.raises(OperationError) as raised:
            rejected_call()
        assert (
            raised.value.code == "state_invalid"
            and raised.value.operation_id == record.operation_id
        )
        view = repo.show(operation_id=record.operation_id)
        assert view.operation.encoded() == before and not view.receipts
        assert len(view.intents) == 1 and view.operation.dataset_id is None


def test_full_receipt_atomically_binds_id_and_is_idempotent(journal):
    record, intent, _ = armed(journal)
    value = accepted_create(journal.plan, intent, timestamp(journal.clock.value), DATASET)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        view = repo.receipt(record.operation_id, record.lease, value)
        assert view.operation.dataset_id == view.receipts[0].created_dataset.id == DATASET
        revision = view.operation.revision
        assert (
            repo.require_created_baseline(record.operation_id, record.lease)
            == value.created_dataset
        )
        assert repo.receipt(record.operation_id, record.lease, value) == view
        assert repo.show(operation_id=record.operation_id).operation.revision == revision
        store.verify()


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "wrong"),
        ("owner_id", "00000000-0000-4000-8000-000000000778"),
        ("modality", "AUDIO"),
    ],
)
def test_wrong_baseline_has_no_receipt_or_id_commit(journal, field, value):
    record, intent, _ = armed(journal)
    good = accepted_create(journal.plan, intent, timestamp(journal.clock.value), DATASET)
    bad = good.model_copy(
        update={"created_dataset": good.created_dataset.model_copy(update={field: value})}
    )
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        with pytest.raises(OperationError) as raised:
            repo.receipt(record.operation_id, record.lease, bad)
        assert raised.value.code == "state_invalid"
        found = repo.show(operation_id=record.operation_id)
        assert found.operation.dataset_id is None and not found.receipts and len(found.intents) == 1


def test_insert_and_operation_id_rollback_together(journal, monkeypatch):
    record, intent, _ = armed(journal)
    good = accepted_create(journal.plan, intent, timestamp(journal.clock.value), DATASET)
    original = StateUploads._change

    def fail(self, *args, **kwargs):
        assert (
            self.connection.execute("SELECT count(*) FROM upload_stage_receipts").fetchone()[0] == 1
        )
        raise YorungeError("state_write_failed")

    monkeypatch.setattr(StateUploads, "_change", fail)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        with pytest.raises(OperationError) as raised:
            repo.receipt(record.operation_id, record.lease, good)
        assert raised.value.code == "state_write_failed"
        view = repo.show(operation_id=record.operation_id)
        assert not view.receipts and view.operation.dataset_id is None
    monkeypatch.setattr(StateUploads, "_change", original)
    with open_store(journal.root) as store:
        assert (
            journal.repository(store)
            .receipt(record.operation_id, record.lease, good)
            .operation.dataset_id
            == DATASET
        )


@pytest.mark.parametrize(
    "seconds,code", [(31, "operation_uncertain"), (151, "operation_lease_lost")]
)
def test_late_response_cannot_extend_intent_or_lease(journal, seconds, code):
    record, intent, _ = armed(journal)
    value = accepted_create(journal.plan, intent, timestamp(journal.clock.value), DATASET)
    journal.clock.value += timedelta(seconds=seconds)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        with pytest.raises(OperationError) as raised:
            repo.receipt(record.operation_id, record.lease, value)
        assert raised.value.code == code and raised.value.operation_id == record.operation_id
        view = repo.show(operation_id=record.operation_id)
        assert not view.receipts and view.operation.dataset_id is None


@pytest.mark.parametrize(
    "phase",
    [
        "preflight",
        "renew",
        "create",
        "project_link",
        "presign",
        "put",
        "confirm",
        "read",
        "proof",
        "read_failed",
    ],
)
def test_legacy_nonterminal_cannot_obtain_new_rights(journal, phase):
    record, _ = historical_running(journal)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        if phase == "preflight":
            rejected_call = partial(
                repo.require_created_baseline, record.operation_id, record.lease
            )
        elif phase == "renew":
            rejected_call = partial(repo.renew, record.operation_id, record.lease)
        elif phase == "read":
            rejected_call = partial(
                repo.acquire_read, record.operation_id, accept_unverified_read=True
            )
        elif phase == "proof":
            rejected_call = partial(repo.verified, record.operation_id, record.lease, None)
        elif phase == "read_failed":
            rejected_call = partial(repo.read_failed, record.operation_id, record.lease, None)
        else:
            index = 0 if phase in {"presign", "put", "confirm"} else None
            rejected_call = partial(
                repo.arm,
                record.operation_id,
                record.lease,
                journal.plan,
                phase,
                index,
                total_end=journal.clock.monotonic() + 900,
            )
        with pytest.raises(OperationError) as raised:
            rejected_call()
        assert (
            raised.value.code == "operation_uncertain"
            and raised.value.operation_id == record.operation_id
        )
        view = repo.show(operation_id=record.operation_id)
        assert len(view.intents) == len(view.receipts) == 1
        assert view.operation.fence == record.fence
        assert view.operation.lease == record.lease  # No renewal/takeover.
        if phase != "read":
            assert (
                view.operation.status == "unknown" and view.operation.reason == "request_uncertain"
            )
            before = view.operation.encoded()
            with pytest.raises(OperationError):
                repo.require_created_baseline(record.operation_id, record.lease)
            assert repo.show(operation_id=record.operation_id).operation.encoded() == before
        else:
            assert view.operation.encoded() == record.encoded()  # Other active owner stays intact.
        store.verify()


def test_legacy_expired_lease_cleanup_marks_unknown_without_new_lease(journal):
    record, _ = historical_running(journal)
    journal.clock.value += timedelta(seconds=151)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        with pytest.raises(OperationError) as raised:
            repo.require_created_baseline(record.operation_id)
        assert raised.value.code == "operation_uncertain"
        view = repo.show(operation_id=record.operation_id)
        assert view.operation.status == "unknown" and view.operation.reason == "request_uncertain"
        assert view.operation.lease is None and view.operation.fence == record.fence + 1
        assert len(view.intents) == len(view.receipts) == 1
        store.verify()


@pytest.mark.parametrize("failure", ["state_busy", "state_changed", "operation_lease_lost"])
def test_marker_failure_does_not_claim_unknown_or_mutate_operation(journal, monkeypatch, failure):
    record, _ = historical_running(journal)

    def fail(*args, **kwargs):
        raise YorungeError(failure)

    monkeypatch.setattr(StateUploads, "_uncertain_verification", fail)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        with pytest.raises(OperationError) as raised:
            repo.require_created_baseline(record.operation_id, record.lease)
        assert raised.value.code == "operation_uncertain"
        assert raised.value.reason_code == failure
        assert repo.show(operation_id=record.operation_id).operation == record


def test_legacy_active_other_owner_is_never_taken_over(journal):
    record, _ = historical_running(journal)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        with pytest.raises(OperationError) as raised:
            repo.require_created_baseline(record.operation_id)
        assert raised.value.reason_code == "operation_conflict"
        assert repo.show(operation_id=record.operation_id).operation == record
        wrong = record.lease.model_copy(update={"owner_id": str(uuid4())})
        with pytest.raises(OperationError) as raised:
            repo.require_created_baseline(record.operation_id, wrong)
        assert raised.value.reason_code == "operation_lease_lost"
        assert repo.show(operation_id=record.operation_id).operation == record


@pytest.mark.parametrize("boundary", ["before_commit", "after_commit"])
def test_real_kill_preserves_atomic_receipt_baseline_and_no_replay(journal, boundary):
    context = multiprocessing.get_context("fork")
    parent, child = context.Pipe()

    def worker():
        try:
            record = journal.approved()  # Admission and permit belong to CHILD PID.
            intent, _, _ = journal.arm(record)
            if boundary == "before_commit":

                def stopped(self, *args, **kwargs):
                    child.send(record.operation_id)
                    child.recv()

                StateUploads._change = stopped
            else:
                original = StateCache.transaction

                @contextmanager
                def stopped(self, *args, **kwargs):
                    with original(self, *args, **kwargs) as gate:
                        yield gate
                    child.send(record.operation_id)  # COMMIT done, caller has no receipt reply.
                    child.recv()

                StateCache.transaction = stopped
            journal.accept(record, intent)
        except BaseException as error:
            child.send(("error", type(error).__name__))

    process = context.Process(target=worker)
    process.start()
    child.close()
    try:
        assert parent.poll(15), "child did not reach receipt boundary"
        identifier = parent.recv()
        assert isinstance(identifier, str), identifier
        process.kill()
        process.join(5)
        assert process.exitcode is not None
        with open_store(journal.root) as store:
            repo = journal.repository(store)
            view = repo.show(operation_id=identifier)
            assert len(view.intents) == 1
            if boundary == "before_commit":
                assert not view.receipts and view.operation.dataset_id is None
            else:
                assert isinstance(view.receipts[0], CreateReceiptV2)
                assert created_dataset(view).id == view.operation.dataset_id == DATASET
            # Existing admit is local lookup, never a second operation/claim/permit.
            assert repo.admit(view.plan.plan_id, view.plan).operation_id == identifier
            store.verify()
    finally:
        if process.is_alive():
            process.kill()
            process.join(5)
        parent.close()


@pytest.mark.parametrize("phase", ["arm", "renew", "read", "proof", "read_failed"])
def test_legacy_state_appearing_after_preflight_is_blocked_in_savepoint(
    journal, monkeypatch, phase
):
    record, intent, _ = armed(journal)
    record = journal.accept(record, intent).operation
    original = StateUploads.require_created_baseline

    def raced(self, *args, **kwargs):
        baseline = original(self, *args, **kwargs)
        self.connection.execute(
            "UPDATE upload_stage_receipts SET payload=? WHERE intent_id=?",
            (legacy_receipt(intent, record.created_at).encoded().decode(), intent.intent_id),
        )
        return baseline

    monkeypatch.setattr(StateUploads, "require_created_baseline", raced)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        if phase == "arm":
            rejected_call = partial(
                repo.arm,
                record.operation_id,
                record.lease,
                journal.plan,
                "project_link",
                None,
                total_end=journal.clock.monotonic() + 900,
            )
        elif phase == "renew":
            rejected_call = partial(repo.renew, record.operation_id, record.lease)
        elif phase == "read":
            rejected_call = partial(repo.acquire_read, record.operation_id)
        elif phase == "proof":
            rejected_call = partial(
                repo.verified, record.operation_id, record.lease, graph().verification
            )
        else:
            # A well-formed negative read check; the legacy gate precedes it.
            from yorunge.domain.upload_checks import AuthorizationCheck

            check = AuthorizationCheck(
                consumer_profile="evren-platform-observed-upload-v2",
                policy_version=2,
                action="read_created_dataset",
                scope=journal.plan.scope,
                dataset_id=DATASET,
                producer_id="fixture",
                producer_version="2",
                checked_at=timestamp(journal.clock.value),
                outcome="denied",
                grant=None,
                error_code="remote_access_denied",
            )
            rejected_call = partial(repo.read_failed, record.operation_id, record.lease, check)
        with pytest.raises(OperationError) as raised:
            rejected_call()
        assert raised.value.code == "operation_uncertain"
        found = repo.show(operation_id=record.operation_id)
        assert len(found.intents) == len(found.receipts) == 1
        assert found.operation.fence == record.fence and found.operation.lease == record.lease


def _cleanup_worker(root, identifier, cutoff, ready, start):
    class Clock:
        def now(self):
            return instant(cutoff)

        def monotonic(self):
            return time.monotonic()

    ready.send(True)
    start.wait(10)
    with open_store(Path(root)) as store:
        try:
            StateUploads(store, clock=Clock()).require_created_baseline(identifier)
        except OperationError as error:
            ready.send((error.code, error.operation_id))
    ready.close()


def test_two_process_expired_cleanup_coalesces_without_new_read_lease(journal, monkeypatch):
    # pytest's console entrypoint with importlib collection does not place the
    # repository on sys.path. Spawn copies this explicit temporary import root.
    monkeypatch.syspath_prepend(str(Path(__file__).parents[2]))
    record, _ = historical_running(journal)
    # Deterministic UTC after the lease, without a real wall-clock assumption.
    # No child receives an execution capability; these are local cleanup actors.
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    pairs = [context.Pipe() for _ in range(2)]
    workers = [
        context.Process(
            target=_cleanup_worker,
            args=(
                str(journal.root),
                record.operation_id,
                timestamp(instant(record.lease.expires_at) + timedelta(seconds=1)),
                pair[1],
                start,
            ),
        )
        for pair in pairs
    ]
    for worker in workers:
        worker.start()
    for _, child in pairs:
        child.close()
    try:
        for parent, _ in pairs:
            assert parent.poll(15) and parent.recv() is True
        start.set()
        for parent, _ in pairs:
            assert parent.poll(15)
            assert parent.recv() == ("operation_uncertain", record.operation_id)
        for worker in workers:
            worker.join(5)
            assert worker.exitcode == 0
        with open_store(journal.root) as store:
            view = journal.repository(store).show(operation_id=record.operation_id)
            assert view.operation.status == "unknown" and view.operation.lease is None
            assert view.operation.fence == record.fence + 1
            assert view.operation.revision == record.revision + 1
            assert len(view.controls) == 1 and len(view.receipts) == len(view.intents) == 1
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.kill()
                worker.join(5)
        for parent, _ in pairs:
            parent.close()


@pytest.mark.filterwarnings("error")
@pytest.mark.parametrize("bad", ["copied_type", "oversize", "selected_literal"])
def test_untrusted_nested_receipt_never_serializes_warning_or_secret(journal, bad, caplog, capsys):
    record, intent, _ = armed(journal)
    good = accepted_create(journal.plan, intent, timestamp(journal.clock.value), DATASET)
    secret = journal.bound.credential.secret.reveal()
    name = (
        {"private": secret} if bad == "copied_type" else "x" * 5000 if bad == "oversize" else secret
    )
    value = good.model_copy(
        update={"created_dataset": good.created_dataset.model_copy(update={"name": name})}
    )
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        with pytest.raises(OperationError) as raised:
            repo.receipt(record.operation_id, record.lease, value)
        assert raised.value.code == (
            "invalid_response" if bad == "selected_literal" else "invalid_request"
        )
        assert secret not in str(raised.value.envelope()) + str(raised.value.__context__) + str(
            raised.value.__cause__
        )
        assert secret not in caplog.text + str(capsys.readouterr())
        view = repo.show(operation_id=record.operation_id)
        assert view.operation.dataset_id is None and not view.receipts


def test_normal_precreate_and_lost_response_are_not_misclassified_as_legacy(journal):
    record = journal.approved()
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        assert repo.require_created_baseline(record.operation_id, record.lease) is None
        assert repo.show(operation_id=record.operation_id).operation == record
    intent, _, _ = journal.arm(record)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        assert repo.require_created_baseline(record.operation_id, record.lease) is None
        view = repo.show(operation_id=record.operation_id)
        assert not legacy_create_without_baseline(view) and not view.receipts
        assert view.intents[0] == intent and view.operation.workflow_latched


def test_existing_exact_legacy_receipt_is_not_new_write_or_backfill(journal):
    record, intent = historical_running(journal)
    old = legacy_receipt(intent, record.created_at)
    new = accepted_create(journal.plan, intent, record.created_at, DATASET)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        before = repo.show(operation_id=record.operation_id)
        assert repo.receipt(record.operation_id, record.lease, old) == before
        with pytest.raises(OperationError) as raised:
            repo.receipt(record.operation_id, record.lease, new)
        assert raised.value.code == "operation_conflict"
        assert repo.show(operation_id=record.operation_id) == before


def test_terminal_entry_and_terminal_race_never_downgrade_history(tmp_path, monkeypatch):
    with open_store(tmp_path / "state") as store:
        data = install_fixture(store, terminal=True)  # Historical v2+v1 terminal.
        repo = StateUploads(store)
        identifier = data["record"]["operation_id"]
        actual = repo.show(operation_id=identifier)
        with pytest.raises(OperationError) as raised:
            repo.require_created_baseline(identifier)
        assert raised.value.code == "operation_conflict"
        # Deterministically emulate a stale local observation just before a
        # different owner committed the terminal result.
        stale = replace(
            actual,
            operation=actual.operation.model_copy(
                update={"status": "unknown", "reason": "lease_expired"}
            ),
            controls=(
                actual.controls[0].model_copy(
                    update={
                        "kind": "recovery",
                        "reason": "lease_expired",
                        "verification_digest": None,
                    }
                ),
            ),
            verification=None,
        )
        original, used = repo._nonterminal, False

        def observed_once(operation_id):
            nonlocal used
            if not used:
                used = True
                return stale
            return original(operation_id)

        monkeypatch.setattr(repo, "_nonterminal", observed_once)
        with pytest.raises(OperationError) as raised:
            repo.require_created_baseline(identifier)
        assert (
            raised.value.code == "operation_uncertain"
            and raised.value.reason_code == "operation_conflict"
        )
        assert repo.show(operation_id=identifier) == actual
        store.verify()
