"""Admission of a continuation: what the chain must show, in the transaction that writes it."""

import json

import pytest

from tests.fixtures.continuation_history import FIRST, build, canon, install
from tests.fixtures.continuation_lifecycle import lifecycle  # noqa: F401
from yorunge.adapters.state import open_store
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import capacity, read_any_view, validate_uploads
from yorunge.domain.capabilities import instant
from yorunge.domain.dataset_transfer_v3 import TransferControlV3, TransferRecordV3
from yorunge.domain.errors import OperationError, YorungeError

TABLES = ("upload_namespaces", "upload_plans", "upload_approvals", "upload_operations")
TABLES += ("upload_controls", "upload_stage_intents", "upload_stage_receipts")


def dump(store):
    return [store.connection.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in TABLES]


def code_of(call):
    with pytest.raises(YorungeError) as error:
        call()
    return error.value.code


def related_of(call):
    with pytest.raises(OperationError) as error:
        call()
    return error.value.code, error.value.operation_id


def ready(lifecycle, store, number=1, **spec):  # noqa: F811
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


def open_chain(lifecycle):  # noqa: F811
    return open_store(lifecycle.root_dir, timeout=60)


# --- the record that admission writes -----------------------------------------------------------


def test_an_approved_continuation_is_admitted_as_a_record_that_has_sent_nothing(lifecycle):  # noqa: F811
    with open_chain(lifecycle) as store:
        plan, repository = ready(lifecycle, store)
        namespaces = store.connection.execute("SELECT * FROM upload_namespaces").fetchall()
        before = capacity(store.connection)
        record = repository.admit(plan.plan_id, plan)
        assert type(record) is TransferRecordV3
        assert (record.status, record.revision, record.fence) == ("admitted", 1, 1)
        assert record.workflow_latched is False and record.reason is None
        assert record.verification_only is False
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
        assert store.connection.execute("SELECT * FROM upload_namespaces").fetchall() == namespaces
        assert capacity(store.connection)[1] == before[1] + 1
        # The same admission again is the same record, found without a new permit.
        assert repository.admit(plan.plan_id, plan) == record
        assert capacity(store.connection)[1] == before[1] + 1
        validate_uploads(store.connection)


def test_a_continuation_that_sends_nothing_is_admitted_as_a_check_only_record(lifecycle):  # noqa: F811
    with open_chain(lifecycle) as store:
        plan, repository = ready(lifecycle, store, indices=(), uncertain=())
        record = repository.admit(plan.plan_id, plan)
        assert record.verification_only is True and record.workflow_latched is False
        assert plan.continuation.file_indices == ()
        validate_uploads(store.connection)


def test_the_baseline_of_an_admitted_continuation_is_its_roots(lifecycle):  # noqa: F811
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


def refused_untouched(lifecycle, store, plan, repository, code):  # noqa: F811
    before = dump(store)
    assert code_of(lambda: repository.admit(plan.plan_id, plan)) == code
    assert dump(store) == before  # nothing was written, not even a cancellation


def test_a_plan_without_an_effective_approval_is_not_admitted(lifecycle):  # noqa: F811
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


def test_an_approval_or_plan_past_its_window_is_not_admitted(lifecycle):  # noqa: F811
    with open_chain(lifecycle) as store:
        plan, repository = ready(lifecycle, store)
        lifecycle.clock.value = instant("2026-11-02T11:15:00.000000Z")
        refused_untouched(lifecycle, store, plan, repository, "upload_plan_not_valid")


def test_a_stale_or_foreign_current_check_is_not_admitted(lifecycle):  # noqa: F811
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


def test_a_source_that_still_runs_with_a_live_lease_is_not_continued(lifecycle):  # noqa: F811
    with open_chain(lifecycle) as store:
        install(store, build(lifecycle.root, 1, status="running"))  # lease until 11:02:32
        plan, repository = ready(lifecycle, store, 2, source=FIRST, indices=(2,), uncertain=())
        before = dump(store)
        assert related_of(lambda: repository.admit(plan.plan_id, plan)) == (
            "operation_conflict",
            FIRST,
        )
        assert dump(store) == before


def test_a_source_whose_lease_lapsed_but_was_never_frozen_is_not_continued(lifecycle):  # noqa: F811
    with open_chain(lifecycle) as store:
        install(store, build(lifecycle.root, 1, status="running"))
        plan, repository = ready(lifecycle, store, 2, source=FIRST, indices=(2,), uncertain=())
        lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")  # the lease is over
        refused_untouched(lifecycle, store, plan, repository, "operation_conflict")


def test_a_source_that_already_has_a_continuation_that_was_not_cancelled_is_not_continued(
    lifecycle,  # noqa: F811
):
    with open_chain(lifecycle) as store:
        # The root already continues into an unknown one: the new plan would be a second branch.
        install(store, build(lifecycle.root, 1, status="unknown", intents=5, acknowledged=4))
        plan, repository = ready(lifecycle, store, 2)
        assert related_of(lambda: repository.admit(plan.plan_id, plan)) == (
            "operation_conflict",
            FIRST,
        )


def test_a_cancelled_continuation_of_the_source_is_no_obstacle(lifecycle):  # noqa: F811
    with open_chain(lifecycle) as store:
        install(store, build(lifecycle.root, 1, status="cancelled"))
        plan, repository = ready(lifecycle, store, 2)
        assert repository.admit(plan.plan_id, plan).status == "admitted"
        validate_uploads(store.connection)


def test_a_descendant_that_lapsed_before_it_sent_anything_is_cancelled_by_the_next_admission(
    lifecycle,  # noqa: F811
):
    with open_chain(lifecycle) as store:
        install(store, build(lifecycle.root, 1, status="admitted"))  # lease until 11:02:32
        plan, repository = ready(lifecycle, store, 2)
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


def test_nothing_else_may_run_against_the_dataset_outside_the_chain(lifecycle):  # noqa: F811
    with open_chain(lifecycle) as store:
        install(store, build(lifecycle.root, 1, status="unknown", intents=5, acknowledged=4))
        # A second, admitted branch off the root: not part of the chain that continues FIRST.
        install(store, build(lifecycle.root, 3, status="admitted"))
        plan, repository = ready(
            lifecycle, store, 2, source=FIRST, indices=(2,), uncertain=(), intents=0
        )
        outsider = "00000000-0000-4000-8000-000000000303"
        assert related_of(lambda: repository.admit(plan.plan_id, plan)) == (
            "operation_conflict",
            outsider,
        )


def test_an_operation_is_never_born_before_the_last_thing_its_source_did(lifecycle):  # noqa: F811
    with open_chain(lifecycle) as store:
        plan, repository = ready(lifecycle, store)
        later = "2026-11-02T11:10:00.000000Z"  # after the clock of the test, within the plan window
        root = lifecycle.root["record"]["operation_id"]
        row = store.connection.execute(
            "SELECT payload FROM upload_operations WHERE operation_id=?", (root,)
        ).fetchone()[0]
        record = {**json.loads(row), "updated_at": later}
        control = json.loads(
            store.connection.execute(
                "SELECT payload FROM upload_controls WHERE operation_id=?", (root,)
            ).fetchone()[0]
        )
        store.connection.execute(
            "UPDATE upload_operations SET payload=? WHERE operation_id=?",
            (canon(record).decode(), root),
        )
        store.connection.execute(
            "UPDATE upload_controls SET payload=? WHERE operation_id=?",
            (canon({**control, "observed_at": later}).decode(), root),
        )
        assert read_any_view(store.connection, plan.plan_id).operation is None  # still readable
        refused_untouched(lifecycle, store, plan, repository, "operation_conflict")
