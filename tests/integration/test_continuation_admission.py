"""Admission of a continuation: what the chain must show, in the transaction that writes it."""

import json

import pytest

from tests.fixtures.continuation_history import FIRST, build, canon, install
from tests.fixtures.continuation_lifecycle import code_of, dump, related_of
from yorunge.adapters.state import open_store
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import capacity, read_any_view, validate_uploads
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.dataset_transfer_v3 import TransferControlV3, TransferRecordV3
from yorunge.domain.errors import YorungeError


def ready(lifecycle, store, number=1, **spec):
    """Save and approve a continuation plan with exactly the acknowledgements it needs."""
    plan = lifecycle.plan(number, **spec)
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
    return plan, repository


def open_chain(lifecycle):
    return open_store(lifecycle.root_dir, timeout=60)


# --- the record that admission writes -----------------------------------------------------------


def test_an_approved_continuation_is_admitted_as_a_record_that_has_sent_nothing(lifecycle):
    with open_chain(lifecycle) as store:
        plan, repository = ready(lifecycle, store)
        namespaces = store.connection.execute("SELECT * FROM upload_namespaces").fetchall()
        before = capacity(store.connection)
        record = repository.admit(plan.plan_id, plan)
        assert type(record) is TransferRecordV3
        assert (record.status, record.revision, record.fence) == ("admitted", 1, 1)
        assert record.workflow_latched is False and record.reason is None
        assert record.verification_only is False and record.clock_anomaly is False
        assert record.dataset_id == plan.continuation.dataset_id
        assert (
            record.intent_digest
            == plan.intent_digest()
            == lifecycle.root["record"]["intent_digest"]
        )
        assert record.plan_id == plan.plan_id and record.plan_digest == plan.digest
        assert record.lease.mode == "write" and record.lease.fence == 1
        assert record.approval == repository.show(plan_id=plan.plan_id).approval
        # Its journal is empty, its namespace is its root's and no create right was taken.
        assert repository.show(operation_id=record.operation_id).intents == ()
        # The base of the confirm counter, N-M, is read from the plan the record is bound to.
        stored = repository.show(operation_id=record.operation_id).plan
        assert stored.continuation.remote_present_count == 3 - len(plan.continuation.file_indices)
        assert store.connection.execute("SELECT * FROM upload_namespaces").fetchall() == namespaces
        assert capacity(store.connection)[1] == before[1] + 1
        # The same admission again is the same record, found without a new permit.
        assert repository.admit(plan.plan_id, plan) == record
        assert capacity(store.connection)[1] == before[1] + 1
        validate_uploads(store.connection)


def test_a_continuation_that_sends_nothing_is_admitted_as_a_check_only_record(lifecycle):
    with open_chain(lifecycle) as store:
        plan, repository = ready(lifecycle, store, indices=(), uncertain=())
        record = repository.admit(plan.plan_id, plan)
        assert record.verification_only is True and record.workflow_latched is False
        assert plan.continuation.file_indices == ()
        validate_uploads(store.connection)


def test_the_baseline_of_an_admitted_continuation_is_its_roots(lifecycle):
    with open_chain(lifecycle) as store:
        plan, repository = ready(lifecycle, store)
        record = repository.admit(plan.plan_id, plan)
        baseline = repository.require_created_baseline(record.operation_id, record.lease)
        assert baseline.id == plan.continuation.dataset_id  # the receipt stays the root's
        assert not any(
            "create" in kind
            for (kind,) in store.connection.execute(
                "SELECT kind FROM upload_stage_intents WHERE operation_id=?", (record.operation_id,)
            )
        )


# --- what it refuses -----------------------------------------------------------------------------


def refused_untouched(lifecycle, store, plan, repository, code):
    before = dump(store)
    assert code_of(lambda: repository.admit(plan.plan_id, plan)) == code
    assert dump(store) == before  # nothing was written, not even a cancellation


def test_a_plan_without_an_effective_approval_is_not_admitted(lifecycle):
    with open_chain(lifecycle) as store:
        repository = lifecycle.repository(store)
        plan = lifecycle.plan(1)
        repository.save(plan, lifecycle.manifest)
        refused_untouched(lifecycle, store, plan, repository, "approval_required")  # never approved
        repository.approve_continuation(
            plan.plan_id, plan.digest, plan,
            acknowledge_unverified_authority=True, acknowledge_unpriced_cost=True,
            acknowledge_unconfirmed_effects=True,
        )  # fmt: skip
        repository.revoke(plan.plan_id, plan.digest)
        refused_untouched(lifecycle, store, plan, repository, "approval_required")  # revoked


def test_an_approval_or_plan_past_its_window_is_not_admitted(lifecycle):
    with open_chain(lifecycle) as store:
        plan, repository = ready(lifecycle, store)
        lifecycle.clock.value = instant("2026-11-02T11:15:00.000000Z")
        refused_untouched(lifecycle, store, plan, repository, "upload_plan_not_valid")


def test_a_stale_or_foreign_current_check_is_not_admitted(lifecycle):
    from datetime import timedelta

    with open_chain(lifecycle) as store:
        plan, repository = ready(lifecycle, store)
        old = repository.capture(plan)
        lifecycle.clock.value += timedelta(seconds=31)  # older than 30 seconds now
        before = dump(store)
        assert code_of(lambda: StateUploads.admit(repository, plan.plan_id, old)) == (
            "upload_plan_not_valid"
        )
        other = lifecycle.plan(7)
        assert (
            code_of(lambda: StateUploads.admit(repository, plan.plan_id, repository.capture(other)))
            == "upload_plan_not_valid"
        )
        assert dump(store) == before


def test_a_source_that_still_runs_with_a_live_lease_is_not_continued(lifecycle):
    with open_chain(lifecycle) as store:
        install(store, build(lifecycle.root, 1, status="running"))  # lease until 11:02:32
        plan, repository = ready(lifecycle, store, 2, source=FIRST, indices=(2,), uncertain=())
        before = dump(store)
        assert related_of(lambda: repository.admit(plan.plan_id, plan)) == (
            "operation_conflict",
            FIRST,
        )
        assert dump(store) == before


def test_a_source_whose_lease_lapsed_but_was_never_frozen_is_not_continued(lifecycle):
    with open_chain(lifecycle) as store:
        install(store, build(lifecycle.root, 1, status="running"))
        plan, repository = ready(lifecycle, store, 2, source=FIRST, indices=(2,), uncertain=())
        lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")  # the lease is over
        refused_untouched(lifecycle, store, plan, repository, "operation_conflict")


# What the source's other continuation can be, for it to stand in the way: anything but cancelled.
BRANCHES = {
    "unknown": ({"status": "unknown", "intents": 5, "acknowledged": 4}, False),
    "admitted with a live lease": ({"status": "admitted"}, False),
    "running with a live lease": ({"status": "running"}, False),
    "running whose lease lapsed": ({"status": "running"}, True),
    "failed": ({"status": "failed"}, False),
    "succeeded": ({"status": "succeeded"}, False),
}


@pytest.mark.parametrize("branch", BRANCHES.values(), ids=BRANCHES)
def test_a_source_that_already_has_a_continuation_that_was_not_cancelled_is_not_continued(
    lifecycle, branch
):
    spec, lapsed = branch
    with open_chain(lifecycle) as store:
        # The plan was saved while the root continued into nothing ...
        plan, repository = ready(lifecycle, store, 2)
        # ... and then the root continued into another one (a racing process): admitting the plan
        # now would make a second branch.
        install(store, build(lifecycle.root, 1, **spec))
        if lapsed:
            lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")
        before = dump(store)
        assert related_of(lambda: repository.admit(plan.plan_id, plan)) == (
            "operation_conflict",
            FIRST,
        )
        assert dump(store) == before


def test_a_cancelled_continuation_of_the_source_is_no_obstacle(lifecycle):
    with open_chain(lifecycle) as store:
        install(store, build(lifecycle.root, 1, status="cancelled"))
        plan, repository = ready(lifecycle, store, 2)
        assert repository.admit(plan.plan_id, plan).status == "admitted"
        validate_uploads(store.connection)


def test_a_descendant_that_lapsed_before_it_sent_anything_is_cancelled_by_the_next_admission(
    lifecycle,
):
    with open_chain(lifecycle) as store:
        plan, repository = ready(lifecycle, store, 2)  # saved before the root had a continuation
        install(store, build(lifecycle.root, 1, status="admitted"))  # lease until 11:02:32
        # While its lease lives it is the live descendant of the source and blocks.
        assert related_of(lambda: repository.admit(plan.plan_id, plan)) == (
            "operation_conflict",
            FIRST,
        )
        lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")
        record = repository.admit(plan.plan_id, plan)
        assert record.status == "admitted"
        stale = repository.show(operation_id=FIRST)
        assert (stale.operation.status, stale.operation.reason) == ("cancelled", "lease_expired")
        assert stale.operation.lease is None and stale.operation.fence == 2
        kinds = [c.kind for c in stale.controls]
        assert kinds == ["terminal"] and type(stale.controls[0]) is TransferControlV3
        # The store never holds two descendants of the root that are not cancelled.
        validate_uploads(store.connection)


def test_nothing_else_may_run_against_the_dataset_outside_the_chain(lifecycle):
    # A second line of defence: full validation already refuses a store with two live branches off
    # one source, so this store is one that only a fault could leave behind.
    with open_chain(lifecycle) as store:
        install(store, build(lifecycle.root, 1, status="unknown", intents=5, acknowledged=4))
        # A second, admitted branch off the root: not part of the chain that continues FIRST.
        install(store, build(lifecycle.root, 3, status="admitted"))
        plan, repository = ready(
            lifecycle, store, 2, source=FIRST, indices=(2,), uncertain=(), intents=0
        )
        outsider = "00000000-0000-4000-8000-000000000303"
        before = dump(store)
        assert related_of(lambda: repository.admit(plan.plan_id, plan)) == (
            "operation_conflict",
            outsider,
        )
        assert dump(store) == before


def last_event_of_the_root(store, lifecycle, when):
    """Move the last thing the root (the source of the default plan) did to ``when``."""
    root = lifecycle.root["record"]["operation_id"]
    row = store.connection.execute(
        "SELECT payload FROM upload_operations WHERE operation_id=?", (root,)
    ).fetchone()[0]
    control = json.loads(
        store.connection.execute(
            "SELECT payload FROM upload_controls WHERE operation_id=?", (root,)
        ).fetchone()[0]
    )
    store.connection.execute(
        "UPDATE upload_operations SET payload=? WHERE operation_id=?",
        (canon({**json.loads(row), "updated_at": when}).decode(), root),
    )
    store.connection.execute(
        "UPDATE upload_controls SET payload=? WHERE operation_id=?",
        (canon({**control, "observed_at": when}).decode(), root),
    )


def test_an_operation_is_never_born_before_the_last_thing_its_source_did(lifecycle):
    with open_chain(lifecycle) as store:
        plan, repository = ready(lifecycle, store)
        # After the clock of the test, within the plan window.
        last_event_of_the_root(store, lifecycle, "2026-11-02T11:10:00.000000Z")
        assert read_any_view(store.connection, plan.plan_id).operation is None  # still readable
        refused_untouched(lifecycle, store, plan, repository, "operation_conflict")


def test_an_operation_may_be_born_in_the_very_instant_its_source_last_did_something(lifecycle):
    with open_chain(lifecycle) as store:
        plan, repository = ready(lifecycle, store)
        last_event_of_the_root(store, lifecycle, timestamp(lifecycle.clock.value))
        record = repository.admit(plan.plan_id, plan)
        assert record.created_at == timestamp(lifecycle.clock.value)


def test_a_descendant_whose_approval_was_revoked_is_cancelled_for_that_reason(lifecycle):
    with open_chain(lifecycle) as store:
        plan, repository = ready(lifecycle, store, 2)  # saved before the root had a continuation
        sibling = build(lifecycle.root, 1, status="admitted")
        install(store, sibling)
        revoked = {
            **sibling.approval,
            "status": "revoked",
            "revoked_at": "2026-11-02T11:00:30.000000Z",
        }
        store.connection.execute(
            "UPDATE upload_approvals SET payload=? WHERE plan_id=?",
            (canon(revoked).decode(), sibling.plan["plan_id"]),
        )
        lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")
        repository.admit(plan.plan_id, plan)
        stale = repository.show(operation_id=FIRST)
        assert (stale.operation.status, stale.operation.reason) == ("cancelled", "approval_revoked")
        validate_uploads(store.connection)


# --- the closed rule, state by state --------------------------------------------------------------


def stopped_first(lifecycle, store):
    """The first continuation of the root, stopped unknown: file 2's put was never answered."""
    install(store, build(lifecycle.root, 1, status="unknown", intents=5, acknowledged=4))


def second_plan(lifecycle, store):
    """The plan that continues it: file 2 only."""
    return ready(lifecycle, store, 2, source=FIRST, indices=(2,), uncertain=(), intents=0)


def test_a_second_continuation_is_admitted_from_the_first_that_stopped(lifecycle):
    with open_chain(lifecycle) as store:
        # An earlier attempt off the root was cancelled and is over; it must not hold the chain.
        install(store, build(lifecycle.root, 3, status="cancelled"))
        stopped_first(lifecycle, store)
        plan, repository = second_plan(lifecycle, store)
        record = repository.admit(plan.plan_id, plan)
        assert (record.status, record.verification_only, record.workflow_latched) == (
            "admitted",
            False,
            False,
        )
        stored = repository.show(operation_id=record.operation_id).plan
        assert stored.continuation.source_operation_id == FIRST
        assert stored.continuation.baseline_operation_id == lifecycle.root["record"]["operation_id"]
        assert stored.continuation.remote_present_count == 2
        validate_uploads(store.connection)


def give_a_read_lease(store, operation_id, until):
    """What a reader that took the unknown source leaves: a live read lease, one fence higher."""
    record = json.loads(
        store.connection.execute(
            "SELECT payload FROM upload_operations WHERE operation_id=?", (operation_id,)
        ).fetchone()[0]
    )
    lease = {
        "owner_id": "00000000-0000-4000-8000-0000000000aa",
        "fence": record["fence"] + 1,
        "identity_epoch": record["observed_identity_epoch"],
        "clock_generation": record["observed_clock_generation"],
        "mode": "read",
        "renewed_at": record["updated_at"],
        "expires_at": until,
    }
    changed = {
        **record,
        "lease": lease,
        "fence": lease["fence"],
        "revision": record["revision"] + 1,
    }
    store.connection.execute(
        "UPDATE upload_operations SET payload=?, revision=?, lease_expires_at=? "
        "WHERE operation_id=?",
        (canon(changed).decode(), changed["revision"], until, operation_id),
    )
    control = json.loads(
        store.connection.execute(
            "SELECT payload FROM upload_controls WHERE operation_id=? AND kind='recovery'",
            (operation_id,),
        ).fetchone()[0]
    )
    store.connection.execute(
        "UPDATE upload_controls SET payload=? WHERE operation_id=? AND kind='recovery'",
        (canon({**control, "revision": changed["revision"]}).decode(), operation_id),
    )


def test_an_unknown_source_that_a_reader_holds_is_not_continued_until_the_lease_is_over(lifecycle):
    with open_chain(lifecycle) as store:
        stopped_first(lifecycle, store)
        give_a_read_lease(store, FIRST, until="2026-11-02T11:02:30.000000Z")
        plan, repository = second_plan(lifecycle, store)
        validate_uploads(store.connection)  # a store that production can leave behind
        before = dump(store)
        assert related_of(lambda: repository.admit(plan.plan_id, plan)) == (
            "operation_conflict",
            FIRST,
        )
        assert dump(store) == before
        lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")  # the reader's lease is over
        assert repository.admit(plan.plan_id, plan).status == "admitted"


def test_work_on_another_dataset_does_not_hold_this_one_back(lifecycle):
    elsewhere = "00000000-0000-4000-8000-000000000777"
    with open_chain(lifecycle) as store:
        stopped_first(lifecycle, store)
        # Somebody else's upload, still admitted, against another dataset of the same store (a
        # stand-in: its lineage is not a valid one, but only the record is read by the scan).
        stand_in = build(lifecycle.root, 4, status="admitted", binding={"dataset_id": elsewhere})
        stand_in.record = {**stand_in.record, "dataset_id": elsewhere}
        install(store, stand_in)
        plan, repository = second_plan(lifecycle, store)
        assert repository.admit(plan.plan_id, plan).status == "admitted"


def test_a_descendant_whose_approval_ran_out_is_cancelled_for_that_reason(lifecycle):
    with open_chain(lifecycle) as store:
        plan, repository = ready(lifecycle, store, 2)  # saved before the root had a continuation
        sibling = build(lifecycle.root, 1, status="admitted")
        over = "2026-11-02T11:03:00.000000Z"  # before the second admission, after the first lease
        sibling.approval = {**sibling.approval, "expires_at": over}
        sibling.record = {**sibling.record, "approval": sibling.approval}
        install(store, sibling)
        lifecycle.clock.value = instant(over)  # the very instant the approval runs out
        repository.admit(plan.plan_id, plan)
        stale = repository.show(operation_id=FIRST)
        assert (stale.operation.status, stale.operation.reason) == ("cancelled", "approval_expired")
        validate_uploads(store.connection)


def test_an_admission_that_fails_after_it_cancelled_a_stale_descendant_takes_that_back(
    lifecycle, monkeypatch
):
    def full(connection):
        raise YorungeError("upload_capacity_exceeded")

    with open_chain(lifecycle) as store:
        plan, repository = ready(lifecycle, store, 2)  # saved before the root had a continuation
        install(store, build(lifecycle.root, 1, status="admitted"))
        lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")
        before = dump(store)
        monkeypatch.setattr("yorunge.adapters.upload_repository.require_capacity", full)
        assert code_of(lambda: repository.admit(plan.plan_id, plan)) == "upload_capacity_exceeded"
        assert dump(store) == before  # the cancellation of FIRST was part of the same transaction
        assert repository.show(operation_id=FIRST).operation.status == "admitted"


def replace_source(store, item):
    """The first continuation as it would be had it ended differently (same plan row stays)."""
    c = store.connection
    c.execute(
        "DELETE FROM upload_stage_receipts WHERE intent_id IN "
        "(SELECT intent_id FROM upload_stage_intents WHERE operation_id=?)",
        (FIRST,),
    )
    for table in ("upload_stage_intents", "upload_controls", "upload_verifications"):
        c.execute(f"DELETE FROM {table} WHERE operation_id=?", (FIRST,))
    c.execute("DELETE FROM upload_operations WHERE operation_id=?", (FIRST,))
    install(store, item, plan=False, approval=False)


@pytest.mark.parametrize("status", ["succeeded", "failed", "cancelled", "admitted"])
def test_a_plan_whose_source_ended_after_it_was_saved_cannot_be_admitted(lifecycle, status):
    with open_chain(lifecycle) as store:
        stopped_first(lifecycle, store)
        plan, repository = second_plan(lifecycle, store)
        replace_source(store, build(lifecycle.root, 1, status=status))
        # The lineage no longer holds (a source that is over, or sent nothing, is not continued):
        # the stored plan is read as an invalid history, before any gate looks at the source.
        refused_untouched(lifecycle, store, plan, repository, "state_invalid")
