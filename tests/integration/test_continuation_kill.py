"""Real processes: a kill at each commit boundary leaves a readable history; races have a winner."""

import multiprocessing
import signal
from datetime import timedelta

from tests.fixtures.continuation_history import FIRST, build, install
from yorunge.adapters.state import open_store
from yorunge.adapters.upload_store import read_any_view, validate_uploads
from yorunge.domain.capabilities import instant
from yorunge.domain.errors import YorungeError

CONTEXT = multiprocessing.get_context("fork")


def saved_and_approved(lifecycle, number=1, **spec):
    plan = lifecycle.plan(number, **spec)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        repository.save(plan, lifecycle.manifest)
        repository.approve_continuation(
            plan.plan_id,
            plan.digest,
            plan,
            acknowledge_unverified_authority=True,
            acknowledge_unpriced_cost=True,
            acknowledge_unconfirmed_effects=bool(plan.continuation.uncertain_indices),
        )
    return plan


def killed_after(lifecycle, step, *arguments):
    """Run ``step`` in a child, kill it the moment it has committed, and leave the store to us."""
    committed = CONTEXT.Event()
    process = CONTEXT.Process(target=step, args=(lifecycle, committed, *arguments))
    process.start()
    try:
        assert committed.wait(30), "the child did not commit"
        process.kill()
        process.join(10)
        assert process.exitcode != 0 and not process.is_alive()
    finally:
        if process.is_alive():
            process.kill()
            process.join(10)


def admit_then_pause(lifecycle, committed, plan):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        lifecycle.repository(store).admit(plan.plan_id, plan)
        committed.set()  # the caller never got the operation id
        signal.pause()


def arm_then_pause(lifecycle, committed, plan):
    # The write access belongs to the process that admitted: one child does everything.
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        record = repository.admit(plan.plan_id, plan)
        repository.arm(
            record.operation_id,
            record.lease,
            plan,
            "presign",
            1,
            total_end=lifecycle.clock.monotonic() + 900,
        )
        committed.set()  # the permit was never used
        signal.pause()


def accept_then_pause(lifecycle, committed, plan):
    from tests.fixtures.continuation_lifecycle import receipt_for

    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        record = repository.admit(plan.plan_id, plan)
        repository.arm(
            record.operation_id,
            record.lease,
            plan,
            "presign",
            1,
            total_end=lifecycle.clock.monotonic() + 900,
        )
        lifecycle.clock.value += timedelta(seconds=1)
        intent = repository.show(operation_id=record.operation_id).intents[-1]
        repository.receipt(record.operation_id, record.lease, receipt_for(intent, lifecycle.clock))
        committed.set()
        signal.pause()


# --- kills ------------------------------------------------------------------------------------


def test_a_kill_after_admission_before_the_id_is_given_leaves_a_recoverable_admission(lifecycle):
    plan = saved_and_approved(lifecycle)
    killed_after(lifecycle, admit_then_pause, plan)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        view = repository.show(plan_id=plan.plan_id)
        assert view.operation is not None and view.operation.status == "admitted"
        assert view.intents == () and view.operation.workflow_latched is False
        # Asking again finds the same operation; the lease ends it, and nothing was ever sent.
        assert repository.admit(plan.plan_id, plan) == view.operation
        lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")
        cleaned = repository.cleanup_expired(view.operation.operation_id)
        assert (cleaned.operation.status, cleaned.operation.reason) == (
            "cancelled",
            "lease_expired",
        )
        assert store.verify().store_schema_version == 7


def test_a_kill_after_arming_leaves_an_intent_no_second_effect_and_an_unknown_operation(lifecycle):
    plan = saved_and_approved(lifecycle)
    killed_after(lifecycle, arm_then_pause, plan)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        view = repository.show(plan_id=plan.plan_id)
        record = view.operation
        assert len(view.intents) == 1 and view.receipts == ()
        assert record.status == "running" and record.workflow_latched is True
        # The permit died with the process: nothing can arm the stage again or use the lease.
        total_end = lifecycle.clock.monotonic() + 900
        try:
            repository.arm(
                record.operation_id, record.lease, plan, "presign", 1, total_end=total_end
            )
        except YorungeError as error:
            assert error.code in {"operation_conflict", "operation_lease_lost"}
        else:  # pragma: no cover
            raise AssertionError("a spent stage was armed again")
        lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")
        cleaned = repository.cleanup_expired(record.operation_id)
        assert (cleaned.operation.status, cleaned.operation.reason) == (
            "unknown",
            "request_uncertain",
        )
        validate_uploads(store.connection)
        assert store.verify().store_schema_version == 7


def test_a_kill_after_a_receipt_leaves_the_receipt_and_a_readable_history(lifecycle):
    plan = saved_and_approved(lifecycle)
    killed_after(lifecycle, accept_then_pause, plan)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        view = read_any_view(store.connection, plan.plan_id)
        assert len(view.intents) == len(view.receipts) == 1
        assert view.receipts[0].intent_id == view.intents[0].intent_id
        assert view.receipts[0].result == "accepted" and view.operation.status == "running"
        validate_uploads(store.connection)
        assert store.verify().store_schema_version == 7


# --- races ------------------------------------------------------------------------------------


def admit_race(lifecycle, barrier, results, plan):
    try:
        with open_store(lifecycle.root_dir, timeout=60) as store:
            repository = lifecycle.repository(store)
            barrier.wait(timeout=15)
            record = repository.admit(plan.plan_id, plan)
            results.put(("admitted", plan.plan_id, record.operation_id))
    except YorungeError as error:
        results.put(("error", plan.plan_id, error.code))


def race(lifecycle, target, *plans):
    barrier, results = CONTEXT.Barrier(len(plans)), CONTEXT.Queue()
    processes = [
        CONTEXT.Process(target=target, args=(lifecycle, barrier, results, plan)) for plan in plans
    ]
    for process in processes:
        process.start()
    try:
        return [results.get(timeout=60) for _ in processes]
    finally:
        for process in processes:
            process.join(15)
            if process.is_alive():
                process.kill()
                process.join(10)


def test_two_processes_admitting_the_same_plan_make_one_operation(lifecycle):
    plan = saved_and_approved(lifecycle)
    replies = race(lifecycle, admit_race, plan, plan)
    assert sorted(r[0] for r in replies) == ["admitted", "admitted"]
    assert len({r[2] for r in replies}) == 1  # both found the one operation
    with open_store(lifecycle.root_dir, timeout=60) as store:
        operations = store.connection.execute("SELECT count(*) FROM upload_operations").fetchone()
        assert operations == (2,)  # the root's and the one
        validate_uploads(store.connection)


def test_two_processes_admitting_two_plans_of_one_source_have_exactly_one_winner(lifecycle):
    first = saved_and_approved(lifecycle, 1)
    second = saved_and_approved(lifecycle, 2)
    replies = race(lifecycle, admit_race, first, second)
    kinds = sorted(r[0] for r in replies)
    assert kinds == ["admitted", "error"], replies
    assert [r[2] for r in replies if r[0] == "error"] == ["operation_conflict"]
    with open_store(lifecycle.root_dir, timeout=60) as store:
        # Exactly one descendant of the root exists, and the whole store is valid.
        assert store.connection.execute("SELECT count(*) FROM upload_operations").fetchone() == (2,)
        validate_uploads(store.connection)


def freeze_race(lifecycle, barrier, results, source):
    try:
        with open_store(lifecycle.root_dir, timeout=60) as store:
            repository = lifecycle.repository(store)
            barrier.wait(timeout=15)
            view = repository.freeze_source(source)
            results.put(("frozen", source, (view.operation.fence, view.operation.revision)))
    except YorungeError as error:
        results.put(("error", source, error.code))


def test_two_prepares_freezing_one_source_at_once_move_its_fence_and_revision_once(lifecycle):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        install(store, build(lifecycle.root, 1, status="running"))
        before = read_any_view(store.connection, build(lifecycle.root, 1).plan["plan_id"])
    lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")
    replies = race(lifecycle, freeze_race, FIRST, FIRST)
    assert sorted(r[0] for r in replies) == ["frozen", "frozen"]
    assert (
        replies[0][2]
        == replies[1][2]
        == (before.operation.fence + 1, before.operation.revision + 1)
    )
