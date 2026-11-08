"""A kill in the middle of the gates that change more than one row, at every write statement.

``test_continuation_kill.py`` kills a process after a call has returned. Here a child process runs
one gate with a trace callback that SIGKILLs it before its k-th write or transaction statement,
for every k that gate issues. The store the child leaves behind must always validate and must be
in one of the states the transaction allows, never in a state between them.
"""

import multiprocessing
import os
import shutil
import signal
from datetime import timedelta

import pytest

from tests.fixtures.continuation_history import FIRST, build, install
from tests.fixtures.continuation_lifecycle import read_check
from yorunge.adapters.state import open_store
from yorunge.adapters.upload_store import read_any_view, validate_uploads
from yorunge.domain.capabilities import instant
from yorunge.domain.errors import YorungeError

CONTEXT = multiprocessing.get_context("fork")
WRITES = {"INSERT", "UPDATE", "DELETE", "BEGIN", "SAVEPOINT", "RELEASE", "COMMIT", "ROLLBACK"}


def run_traced(act, kill_at, log):
    """In a child process: run ``act(trace)``; die before statement ``kill_at`` when it is given."""
    count = 0
    statements = []

    def trace(statement):
        nonlocal count
        count += 1
        statements.append(statement)
        if count == kill_at:
            os.kill(os.getpid(), signal.SIGKILL)

    act(trace)
    if log is not None:
        log.put(statements)


def sweep(lifecycle, tmp_path, act, outcome):
    """Kill ``act`` before each of its write statements; return the outcomes the stores show."""
    pristine = tmp_path / "pristine"
    shutil.copytree(lifecycle.root_dir, pristine)
    log = CONTEXT.Queue()
    counting = CONTEXT.Process(target=run_traced, args=(act, None, log))
    counting.start()
    try:
        statements = log.get(timeout=60)
    finally:
        counting.join(60)
        if counting.is_alive():
            counting.kill()
            counting.join()
    points = [i for i, text in enumerate(statements, 1) if text.split()[0].upper() in WRITES]
    assert len(points) >= 10  # a gate that writes more than one row issues many of them
    seen = set()
    for point in points:
        shutil.rmtree(lifecycle.root_dir)
        shutil.copytree(pristine, lifecycle.root_dir)
        child = CONTEXT.Process(target=run_traced, args=(act, point, None))
        child.start()
        child.join(60)
        if child.is_alive():  # a hang is a failure, and must not outlive the test
            child.kill()
            child.join()
        assert child.exitcode == -signal.SIGKILL, (point, child.exitcode)
        with open_store(lifecycle.root_dir, timeout=60) as store:
            validate_uploads(store.connection)
            seen.add(outcome(store))
    return seen


def admitted_first_that_lapsed(lifecycle):
    """An admitted continuation whose lease is over, and a second plan of the same source.

    The second plan is saved first, while the source continues into nothing: a source that
    already has a continuation takes no more plans.
    """
    second = lifecycle.plan(2)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        repository.save(second, lifecycle.manifest)
        repository.approve_continuation(
            second.plan_id,
            second.digest,
            second,
            acknowledge_unverified_authority=True,
            acknowledge_unpriced_cost=True,
            acknowledge_unconfirmed_effects=True,
        )
    first, _ = lifecycle.admitted(1)
    lifecycle.clock.value += timedelta(seconds=200)
    return first, second


def test_a_kill_at_any_statement_of_an_admission_that_cancels_a_stale_descendant(
    lifecycle, tmp_path
):
    first, second = admitted_first_that_lapsed(lifecycle)

    def act(trace):
        with open_store(lifecycle.root_dir, timeout=60) as store:
            store.connection.set_trace_callback(trace)
            lifecycle.repository(store).admit(second.plan_id, second)

    def outcome(store):
        before = read_any_view(store.connection, first.plan_id).operation
        after = read_any_view(store.connection, second.plan_id).operation
        return (before.status, None if after is None else after.status)

    # The cancellation of the stale descendant and the new operation are one transaction.
    assert sweep(lifecycle, tmp_path, act, outcome) == {
        ("admitted", None),
        ("cancelled", "admitted"),
    }


def test_a_kill_at_any_statement_of_freezing_a_source_that_has_a_stale_descendant(
    lifecycle, tmp_path
):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        source = build(lifecycle.root, 1, status="running")
        stale = build(lifecycle.root, 2, source=FIRST, status="admitted")
        install(store, source)
        install(store, stale)
    lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")  # every lease is over

    def act(trace):
        with open_store(lifecycle.root_dir, timeout=60) as store:
            store.connection.set_trace_callback(trace)
            lifecycle.repository(store).freeze_source(FIRST)

    def outcome(store):
        before = read_any_view(store.connection, source.plan["plan_id"]).operation
        after = read_any_view(store.connection, stale.plan["plan_id"]).operation
        return (before.status, after.status)

    assert sweep(lifecycle, tmp_path, act, outcome) == {
        ("running", "admitted"),
        ("unknown", "cancelled"),
    }


def test_a_kill_at_any_statement_of_a_check_only_continuation_that_fails_its_read(
    lifecycle, tmp_path
):
    plan = lifecycle.plan(1, indices=(), uncertain=())
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        repository.save(plan, lifecycle.manifest)
        repository.approve_continuation(
            plan.plan_id,
            plan.digest,
            plan,
            acknowledge_unverified_authority=True,
            acknowledge_unpriced_cost=True,
        )

    def act(trace):
        with open_store(lifecycle.root_dir, timeout=60) as store:
            store.connection.set_trace_callback(trace)
            repository = lifecycle.repository(store)
            record = repository.admit(plan.plan_id, plan)
            lifecycle.clock.value += timedelta(seconds=1)
            failure = read_check(plan, lifecycle.clock, error="remote_failed")
            with pytest.raises(YorungeError):
                repository.read_failed(record.operation_id, record.lease, failure)

    def outcome(store):
        record = read_any_view(store.connection, plan.plan_id).operation
        return None if record is None else (record.status, record.reason)

    # Never admitted, admitted but not yet failed, or cancelled by its failed read: nothing between.
    assert sweep(lifecycle, tmp_path, act, outcome) == {
        None,
        ("admitted", None),
        ("cancelled", "local_cancelled"),
    }
