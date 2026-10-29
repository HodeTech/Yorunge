"""Batch query, keyset and snapshot invariants on actual SQLite stores."""

import json
import sqlite3
from contextlib import nullcontext
from datetime import timedelta
from functools import partial
from threading import Event, Thread
from uuid import uuid4

import pytest

from yorunge import api
from yorunge.adapters import operation_store
from yorunge.adapters.jobs import list_jobs
from yorunge.adapters.local_files import Deadline, file_lock
from yorunge.adapters.state import DB_NAME, open_store
from yorunge.domain.capabilities import timestamp
from yorunge.domain.errors import YorungeError
from yorunge.domain.jobs import JobsQuery


@pytest.fixture
def recorded_jobs(operation_setup):
    state, first, backend = operation_setup
    plans = [first]
    for _ in range(6):
        plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
        api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state)
        plans.append(plan)
    jobs = []
    for plan in plans:
        with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
            jobs.append(coordinator.admit(plan.plan_id).job)
    return state, sorted(
        jobs, key=lambda job: (job.operation.created_at, job.operation.operation_id)
    )


def test_keyset_tie_breaks_ids_and_repeats_bound_filters(recorded_jobs, tmp_path):
    state, jobs = recorded_jobs
    result, cursor, pages = [], None, []
    while True:
        page = api.list_jobs(status="admitted", limit=2, cursor=cursor, state_dir=state).data
        pages.append(page)
        result.extend(page.jobs)
        cursor = page.next_cursor
        if cursor is None:
            break
    assert result == [job.operation for job in jobs]
    assert [len(page.jobs) for page in pages] == [2, 2, 2, 1]
    selected = jobs[3]
    assert api.list_jobs(
        status="admitted", plan_id=selected.plan.plan_id, limit=1, state_dir=state
    ).data.jobs == (selected.operation,)
    assert api.list_jobs(plan_id=str(uuid4()), state_dir=state).data.jobs == ()
    cursor = pages[0].next_cursor
    for options in (
        {},
        {"status": "running"},
        {"status": "admitted", "plan_id": selected.plan.plan_id},
    ):
        with pytest.raises(YorungeError) as error:
            api.list_jobs(cursor=cursor, state_dir=state, **options)
        assert error.value.code == "invalid_request"
    other = tmp_path / "other"
    api.initialize_state(state_dir=other)
    with pytest.raises(YorungeError) as error:
        api.list_jobs(status="admitted", cursor=cursor, state_dir=other)
    assert error.value.code == "invalid_request"


def test_each_page_is_a_new_snapshot_and_reset_does_not_rewrite_cursor_keys(recorded_jobs):
    state, jobs = recorded_jobs
    first = api.list_jobs(status="admitted", limit=2, state_dir=state).data
    preview = api.preview_identity_reset(state_dir=state).data
    api.reset_identity(preview.digest, state_dir=state)
    assert (
        api.list_jobs(status="admitted", cursor=first.next_cursor, state_dir=state).data.jobs == ()
    )
    cancelled = api.list_jobs(status="cancelled", state_dir=state).data.jobs
    assert [(job.created_at, job.operation_id) for job in cancelled] == [
        (job.operation.created_at, job.operation.operation_id) for job in jobs
    ]


def test_list_text_shows_status_axes_cursor_and_explicit_empty_message(recorded_jobs, cli):
    state, _ = recorded_jobs
    page = api.list_jobs(limit=2, state_dir=state).data
    result = cli("jobs", "list", "--limit", "2", "--state-dir", str(state), state=True)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    for job in page.jobs:
        assert job.operation_id in result.stdout
        assert job.task in result.stdout
        assert f"execution: {job.execution_status}" in result.stdout
        assert f"delivery: {job.delivery_status}" in result.stdout
    assert f"Sonraki cursor: {page.next_cursor}" in result.stdout
    assert "güncel uzak durumu yansıtmayabilir" in result.stdout
    empty = cli("jobs", "list", "--status", "cancelled", "--state-dir", str(state), state=True)
    assert empty.returncode == 0, empty.stderr
    assert "Kayıtlı iş yok." in empty.stdout


def test_list_uses_constant_batch_queries_and_no_history_payload_scan(recorded_jobs):
    state, jobs = recorded_jobs
    statements = []
    with open_store(state) as store:
        store.connection.set_trace_callback(statements.append)
        counts = []
        for limit in (1, 7):
            statements.clear()
            result = list_jobs(store.connection, JobsQuery(limit=limit))
            assert len(result.jobs) == limit
            assert not store.connection.in_transaction
            counts.append(len(statements))
            assert statements[0] == "BEGIN"
            assert statements[-1] == "ROLLBACK"
            # Only the latest event payload is joined to an indexed count/min/max.
            event_reads = [
                statement for statement in statements if "FROM operation_events" in statement
            ]
            assert len(event_reads) == 1
            assert "count(*)" in event_reads[0]
            assert "e.sequence=h.last" in event_reads[0]
        store.connection.set_trace_callback(None)
    assert counts == [7, 7]
    assert len(jobs) == 7


@pytest.mark.parametrize("action", ["list", "show"])
@pytest.mark.parametrize(
    "damage", ["operation_index", "plan", "attempt", "outcome", "event_count", "last_event"]
)
def test_public_reads_reject_broken_selected_projection(admitted_operation, action, damage, cli):
    state, _, record, _, _ = admitted_operation
    identifier = record.summary.operation_id
    with sqlite3.connect(state / DB_NAME) as connection:
        if damage == "operation_index":
            connection.execute("UPDATE operations SET revision=revision+1")
        elif damage == "plan":
            connection.execute("UPDATE execution_plans SET payload='{}'")
        elif damage == "attempt":
            connection.execute("UPDATE operation_attempts SET status='unknown'")
        elif damage == "outcome":
            connection.execute("INSERT INTO operation_outcomes VALUES(?, '{}')", (identifier,))
        elif damage == "event_count":
            connection.execute("DELETE FROM operation_events")
        else:
            connection.execute("UPDATE operation_events SET payload='{}'")
    invoke = api.list_jobs if action == "list" else lambda **kw: api.show_job(identifier, **kw)
    with pytest.raises(YorungeError) as error:
        invoke(state_dir=state)
    assert error.value.code == "state_invalid"
    options = [] if action == "list" else ["--operation-id", identifier]
    result = cli(
        "jobs", action, *options, "--state-dir", str(state), "--output", "json", state=True
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert json.loads(result.stderr)["code"] == "state_invalid"
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("action", ["list", "show"])
def test_read_snapshot_prevents_mixing_concurrent_takeover(
    operation_setup, execution_clock, monkeypatch, action
):
    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        admitted = coordinator.admit(plan.plan_id).job
    identifier = admitted.operation.operation_id
    execution_clock.value += timedelta(seconds=31)
    with open_store(state) as store:
        record = operation_store.read_operation(store.connection, identifier)
    now = timestamp(execution_clock.value)
    next_attempt = admitted.attempts[-1].model_copy(
        update={
            "attempt_id": str(uuid4()),
            "number": 2,
            "created_at": now,
            "updated_at": now,
        }
    )
    changed = record.model_copy(
        update={
            "summary": record.summary.model_copy(
                update={"revision": 2, "attempt_count": 2, "updated_at": now}
            ),
            "fence": 2,
            "lease": record.lease.model_copy(
                update={
                    "owner_id": str(uuid4()),
                    "fence": 2,
                    "expires_at": timestamp(execution_clock.value + timedelta(seconds=30)),
                }
            ),
        }
    )
    writing, finished = Event(), Event()
    failures = []

    def writer():
        try:
            with open_store(state) as store:
                connection = store.connection
                connection.execute("BEGIN IMMEDIATE")
                operation_store.write_record(connection, changed, expected_revision=1)
                operation_store.write_attempt(
                    connection,
                    identifier,
                    admitted.attempts[-1].model_copy(
                        update={
                            "status": "abandoned",
                            "reason_code": "owner_changed",
                            "updated_at": now,
                        }
                    ),
                )
                operation_store.write_attempt(connection, identifier, next_attempt)
                # A valid ownership change is ready to commit on a separate connection.
                writing.set()
                connection.execute("COMMIT")
                operation_store.read_job(connection, identifier)
        except BaseException as error:
            failures.append(error)
            writing.set()
        finally:
            finished.set()

    thread = Thread(target=writer)
    original = operation_store.decode_attempts
    started = False

    def interleaved(operation_id, rows):
        nonlocal started
        if not started and operation_id == identifier:
            started = True
            thread.start()
            assert writing.wait(5), "writer never reached its attempt mutation"
            assert not finished.is_set(), "writer committed while the read snapshot was open"
        return original(operation_id, rows)

    # Both readers use this shared pure decoder after opening their read snapshot.
    monkeypatch.setattr(operation_store, "decode_attempts", interleaved)
    monkeypatch.setattr("yorunge.adapters.jobs.decode_attempts", interleaved)
    try:
        result = (
            api.list_jobs(state_dir=state).data.jobs[0]
            if action == "list"
            else api.show_job(identifier, state_dir=state).data.operation
        )
    finally:
        if started:
            thread.join(10)
    assert finished.is_set()
    assert failures == []
    assert result == admitted.operation
    assert api.show_job(identifier, state_dir=state).data.operation.attempt_count == 2
    assert backend.effects() == []


@pytest.mark.parametrize("action", ["list", "show"])
@pytest.mark.parametrize(
    "failure,code",
    [("busy", "state_busy"), ("intent", "state_repair_required"), ("io", "state_write_failed")],
)
def test_state_failures_never_become_empty_or_unknown_jobs(
    admitted_operation, monkeypatch, action, failure, code
):
    state, _, record, _, _ = admitted_operation
    if failure == "intent":
        (state / "restore-intent.json").write_bytes(b"incomplete")
    if failure == "io":

        def failed(*args, **kwargs):
            raise OSError("private-path-marker")

        monkeypatch.setattr("yorunge.adapters.state.connect", failed)
    lock = (
        file_lock(state / "store.lock", Deadline(), exclusive=True, create=False)
        if failure == "busy"
        else nullcontext()
    )
    if action == "list":
        invoke = partial(api.list_jobs, state_dir=state)
    else:
        invoke = partial(api.show_job, record.summary.operation_id, state_dir=state)
    with lock, pytest.raises(YorungeError) as error:
        invoke()
    assert error.value.code == code
    assert "private-path-marker" not in str(error.value)
    if failure == "intent":
        assert (state / "restore-intent.json").read_bytes() == b"incomplete"


@pytest.mark.parametrize("damage", ["fence", "timestamp", "attempt"])
def test_list_rejects_latest_event_with_broken_candidate_binding(
    operation_setup, execution_clock, damage
):
    from yorunge.domain.capabilities import canonical

    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        original = coordinator.admit(plan.plan_id)
    execution_clock.value += timedelta(seconds=31)
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        identifier = original.job.operation.operation_id
        taken = coordinator.takeover(identifier)
        coordinator.dispatch(identifier, taken.ownership)
        if damage == "attempt":
            execution_clock.value += timedelta(seconds=31)
            coordinator.takeover(identifier)
    with sqlite3.connect(state / DB_NAME) as connection:
        sequence, payload = connection.execute(
            "SELECT sequence,payload FROM operation_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        raw = json.loads(payload)
        if damage == "fence":
            raw["fence"] = 1
        elif damage == "timestamp":
            raw["observed_at"] = original.job.operation.created_at
        else:
            raw["attempt_id"] = original.job.attempts[0].attempt_id
        connection.execute(
            "UPDATE operation_events SET attempt_id=?,payload=? WHERE sequence=?",
            (raw["attempt_id"], canonical(raw).decode(), sequence),
        )
    for invoke in (lambda **kw: api.show_job(identifier, **kw), api.list_jobs):
        with pytest.raises(YorungeError) as error:
            invoke(state_dir=state)
        assert error.value.code == "state_invalid"
    assert len(backend.effects()) == 1


@pytest.mark.parametrize("terminal", [False, True])
def test_list_rejects_impossible_extra_predispatch_normal_event(admitted_operation, terminal):
    from tests.integration.test_operation_store import raw_record
    from yorunge.domain.capabilities import canonical

    state, _, record, _, _ = admitted_operation
    identifier = record.summary.operation_id
    if terminal:
        preview = api.preview_identity_reset(state_dir=state).data
        api.reset_identity(preview.digest, state_dir=state)
    with open_store(state) as store:
        record = operation_store.read_operation(store.connection, identifier)
        sequence, payload = store.connection.execute(
            "SELECT sequence,payload FROM operation_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        raw = json.loads(payload)
        raw["sequence"] = sequence + 1
        raw["revision"] = record.summary.revision + 1
        store.connection.execute("BEGIN IMMEDIATE")
        raw_record(
            store.connection,
            record.model_copy(
                update={
                    "event_count": record.event_count + 1,
                    "summary": record.summary.model_copy(
                        update={"revision": record.summary.revision + 1}
                    ),
                }
            ),
        )
        store.connection.execute(
            "INSERT INTO operation_events VALUES(?,?,?,?)",
            (identifier, sequence + 1, raw["attempt_id"], canonical(raw).decode()),
        )
        store.connection.execute("COMMIT")
    for invoke in (lambda **kw: api.show_job(identifier, **kw), api.list_jobs):
        with pytest.raises(YorungeError) as error:
            invoke(state_dir=state)
        assert error.value.code == "state_invalid"


@pytest.mark.parametrize("damage", ["revision", "epoch", "generation", "first_status"])
def test_latest_first_dispatch_retains_original_intent_authority(operation_setup, damage):
    from yorunge.domain.capabilities import canonical
    from yorunge.domain.errors import OperationError

    state, plan, backend = operation_setup
    backend.mode = "not_sent"
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        with pytest.raises(OperationError) as error:
            coordinator.dispatch(identifier, claim.ownership)
        assert error.value.code == "operation_uncertain"
    with sqlite3.connect(state / DB_NAME) as connection:
        payload = connection.execute(
            "SELECT payload FROM operation_events WHERE sequence=2"
        ).fetchone()[0]
        raw = json.loads(payload)
        if damage == "revision":
            raw["revision"] = 1
        elif damage == "epoch":
            raw["identity_epoch"] = str(uuid4())
        elif damage == "generation":
            raw["clock_generation"] += 1
        else:
            raw["status"] = raw["execution_status"] = "running"
        connection.execute(
            "UPDATE operation_events SET payload=? WHERE sequence=2", (canonical(raw).decode(),)
        )
    for invoke in (lambda **kw: api.show_job(identifier, **kw), api.list_jobs):
        with pytest.raises(YorungeError) as error:
            invoke(state_dir=state)
        assert error.value.code == "state_invalid"
    assert backend.effects() == []


@pytest.mark.parametrize("action", ["list", "show", "full"])
def test_persisted_execution_success_cannot_have_nonzero_exit(admitted_operation, action):
    from tests.integration.test_operation_store import raw_attempt, terminal_fixture
    from yorunge.domain.capabilities import canonical

    state, _, record, attempt, event = admitted_operation
    identifier = record.summary.operation_id
    with open_store(state) as store:
        connection = store.connection
        connection.execute("BEGIN IMMEDIATE")
        _, attempt, _ = terminal_fixture(connection, record, attempt, event)
        connection.execute("COMMIT")
        assert operation_store.read_job(connection, identifier).operation.status == "succeeded"
        raw_attempt(connection, attempt.model_copy(update={"provider_exit_code": 1}))
        raw = json.loads(connection.execute("SELECT payload FROM operation_outcomes").fetchone()[0])
        raw["provider_exit_code"] = 1
        connection.execute("UPDATE operation_outcomes SET payload=?", (canonical(raw).decode(),))
    if action == "list":
        invoke = partial(api.list_jobs, state_dir=state)
    elif action == "show":
        invoke = partial(api.show_job, identifier, state_dir=state)
    else:
        invoke = partial(api.initialize_state, state_dir=state)
    with pytest.raises(YorungeError) as error:
        invoke()
    assert error.value.code == "state_invalid"


def test_nonzero_exit_cannot_contradict_confirmed_execution_during_delivery(
    operation_setup, execution_clock
):
    from tests.fixtures.operation_backend import ReadObserver
    from tests.integration.test_operation_store import raw_attempt

    state, plan, backend = operation_setup
    observer = ReadObserver(execution_clock)
    observer.delivery = "pending"
    with api._operation_session(
        plan.plan_id, backend, observer=observer, state_dir=state
    ) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        coordinator.dispatch(identifier, claim.ownership)
        job = coordinator.reconcile(identifier, claim.ownership)
        assert job.operation.status == "running"
        assert job.operation.execution_status == "succeeded"
        assert job.outcome is None
    with open_store(state) as store:
        raw_attempt(store.connection, job.attempts[-1].model_copy(update={"provider_exit_code": 1}))
    with pytest.raises(YorungeError) as error:
        api.show_job(identifier, state_dir=state)
    assert error.value.code == "state_invalid"
