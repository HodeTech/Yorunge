"""What a gate says when the clock, the credential or the read around it goes wrong.

The code an error carries and the operation it names are what the producer maps to a message for
the user, so they are pinned gate by gate: a refusal is what it is, names the operation it is
about and leaves the store as it found it.
"""

from datetime import timedelta

import pytest

from tests.fixtures.continuation_history import FIRST, build, install
from tests.fixtures.continuation_lifecycle import (
    ACKNOWLEDGE_ALL,
    FixtureContinuations,
    code_of,
    dump,
    proof_of,
    read_check,
    related_of,
    send_all,
    tick,
)
from yorunge.adapters.state import open_store
from yorunge.adapters.upload_repository import StateUploads
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.errors import OperationError, YorungeError


def clock_goes_back(repository, lifecycle):
    """The clock is an hour earlier once the repository has taken its stamp: a new generation."""
    taken = repository.cache.stamp

    def stamp():
        found = taken()
        lifecycle.clock.value -= timedelta(hours=1)
        return found

    repository.cache.stamp = stamp
    return repository


# --- a clock that goes back --------------------------------------------------------------------


def test_approving_when_the_clock_goes_back_finds_the_state_changed(lifecycle):
    plan = lifecycle.plan(1)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        repository.save(plan, lifecycle.manifest)
        before = dump(store)
        clock_goes_back(repository, lifecycle)
        approve = repository.approve_continuation
        assert (
            code_of(lambda: approve(plan.plan_id, plan.digest, plan, **ACKNOWLEDGE_ALL))
            == "state_changed"
        )
        assert dump(store) == before


def test_freezing_when_the_clock_goes_back_loses_the_lease_it_would_have_judged(lifecycle):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        install(store, build(lifecycle.root, 1, status="running"))
        lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")
        before = dump(store)
        repository = clock_goes_back(lifecycle.repository(store), lifecycle)
        assert code_of(lambda: repository.freeze_source(FIRST)) == "operation_lease_lost"
        assert dump(store) == before


@pytest.mark.parametrize("gate", ["read_failed", "prepare_initial_read"])
def test_reading_when_the_clock_goes_back_loses_the_lease(lifecycle, gate):
    plan, record = lifecycle.admitted(indices=(), uncertain=())
    failure = read_check(plan, lifecycle.clock, error="remote_failed")
    check = read_check(plan, lifecycle.clock)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = clock_goes_back(lifecycle.repository(store), lifecycle)
        before = dump(store)
        calls = {
            "read_failed": lambda: repository.read_failed(
                record.operation_id, record.lease, failure
            ),
            "prepare_initial_read": lambda: repository.prepare_initial_read(
                record.operation_id, record.lease, authorization=check
            ),
        }
        assert code_of(calls[gate]) == "operation_lease_lost"
        assert dump(store) == before


def test_a_late_proof_whose_marker_meets_a_clock_that_went_back_is_still_a_timeout(
    lifecycle,
):
    plan, record = lifecycle.admitted(indices=(), uncertain=())
    observed = timestamp(lifecycle.clock.value + timedelta(seconds=5))
    tick(lifecycle, 50)  # the observation is older than the thirty seconds a proof may be
    check = read_check(plan, lifecycle.clock)

    class GoesBack(FixtureContinuations):
        def _uncertain_verification(self, operation_id, owner):
            clock_goes_back(self, lifecycle)
            return super()._uncertain_verification(operation_id, owner)

    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = GoesBack(
            store, lifecycle.bound, clock=lifecycle.clock, write_access=lifecycle.access
        )
        with pytest.raises(OperationError) as error:
            repository.verified(
                record.operation_id, record.lease, proof_of(plan, observed), authorization=check
            )
        assert (error.value.code, error.value.reason_code) == (
            "execution_timeout",
            "operation_lease_lost",
        )


# --- who an error names ---------------------------------------------------------------------------


def test_freezing_a_source_that_still_runs_names_it(lifecycle):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        install(store, build(lifecycle.root, 1, status="running"))  # its lease is live
        repository = lifecycle.repository(store)
        assert related_of(lambda: repository.freeze_source(FIRST)) == ("operation_conflict", FIRST)


def test_an_admission_that_fails_once_committed_names_the_operation_it_made(lifecycle, monkeypatch):
    plan = lifecycle.plan(1)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        repository.save(plan, lifecycle.manifest)
        repository.approve_continuation(plan.plan_id, plan.digest, plan, **ACKNOWLEDGE_ALL)

        def fails(self, stamp, gate, *, scope):
            raise YorungeError("state_busy")

        monkeypatch.setattr(StateUploads, "_finish", fails)
        with pytest.raises(OperationError) as error:
            repository.admit(plan.plan_id, plan)
        monkeypatch.undo()
        made = repository.show(plan_id=plan.plan_id).operation
        # The admission is committed; the caller learns which operation it is.
        assert made is not None and error.value.operation_id == made.operation_id
        assert error.value.code == "state_busy"


# --- what a failed read, a proof and an approval must still satisfy -----------------------------


def test_a_failed_read_of_another_dataset_is_refused(lifecycle):
    plan, record = lifecycle.admitted(indices=(), uncertain=())
    elsewhere = read_check(plan, lifecycle.clock, error="remote_failed").model_copy(
        update={"dataset_id": "00000000-0000-4000-8000-0000000000ff"}
    )
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        before = dump(store)
        assert (
            code_of(lambda: repository.read_failed(record.operation_id, record.lease, elsewhere))
            == "state_changed"
        )
        assert dump(store) == before


def test_the_write_owner_reporting_a_failed_read_keeps_its_fence(lifecycle):
    plan, record = lifecycle.admitted()
    send_all(lifecycle, plan, record)
    failure = read_check(plan, lifecycle.clock, error="transport_timeout")
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        before = repository.show(operation_id=record.operation_id).operation
        code_of(lambda: repository.read_failed(record.operation_id, record.lease, failure))
        after = repository.show(operation_id=record.operation_id).operation
        assert (after.status, after.lease, after.fence) == ("unknown", None, before.fence)


def test_a_reader_taking_over_to_report_a_failed_read_moves_the_fence_and_gives_the_reads_code(
    lifecycle,
):
    plan, record = lifecycle.admitted()
    send_all(lifecycle, plan, record)
    lifecycle.clock.value += timedelta(seconds=200)  # the writer's lease is over
    failure = read_check(plan, lifecycle.clock, error="transport_timeout")
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        before = repository.show(operation_id=record.operation_id).operation
        with pytest.raises(OperationError) as error:
            repository.read_failed(record.operation_id, None, failure)
        assert (error.value.code, error.value.reason_code) == (
            "transport_timeout",
            "transport_timeout",
        )
        after = repository.show(operation_id=record.operation_id).operation
        assert after.fence == before.fence + 1


def test_the_approval_must_still_stand_when_the_initial_read_is_prepared(lifecycle):
    plan, record = lifecycle.admitted(indices=(), uncertain=())
    check = read_check(plan, lifecycle.clock)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        repository.revoke(plan.plan_id, plan.digest)
        before = dump(store)
        assert (
            code_of(
                lambda: repository.prepare_initial_read(
                    record.operation_id, record.lease, authorization=check
                )
            )
            == "approval_required"
        )
        assert dump(store) == before


def test_a_proof_exactly_as_old_as_a_proof_may_be_is_still_current(lifecycle):
    plan, record = lifecycle.admitted(indices=(), uncertain=())
    observed = timestamp(lifecycle.clock.value)
    tick(lifecycle, 30)
    check = read_check(plan, lifecycle.clock)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        proof = proof_of(plan, observed)
        view = repository.verified(record.operation_id, record.lease, proof, authorization=check)
        assert view.operation.status == "succeeded"


def test_a_record_that_cannot_be_read_after_a_failed_marker_is_not_taken_for_one_that_sent_nothing(
    lifecycle,
):
    plan, record = lifecycle.admitted(indices=(), uncertain=())
    observed = timestamp(lifecycle.clock.value + timedelta(seconds=5))
    tick(lifecycle, 50)
    check = read_check(plan, lifecycle.clock)

    class Hostile(FixtureContinuations):
        broken = False

        def _uncertain_verification(self, operation_id, owner):
            self.broken = True
            raise YorungeError("operation_lease_lost")

        def show(self, **found):
            if self.broken:
                raise YorungeError("state_invalid")
            return super().show(**found)

    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = Hostile(
            store, lifecycle.bound, clock=lifecycle.clock, write_access=lifecycle.access
        )
        with pytest.raises(OperationError) as error:
            repository.verified(
                record.operation_id, record.lease, proof_of(plan, observed), authorization=check
            )
        # What cannot be read is not assumed to have sent nothing: it stays uncertain.
        assert (error.value.code, error.value.reason_code) == (
            "operation_uncertain",
            "operation_lease_lost",
        )


# --- a descendant that lapsed with its approval revoked and run out ------------------------------


def test_a_stale_descendant_whose_approval_was_revoked_and_ran_out_is_cancelled_as_revoked(
    lifecycle,
):
    first, _ = lifecycle.admitted(1)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        lifecycle.repository(store).revoke(first.plan_id, first.digest)
    lifecycle.clock.value += timedelta(days=40)  # long past its lease and its approval
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        repository.freeze_source(lifecycle.root["record"]["operation_id"])
        stale = repository.show(plan_id=first.plan_id).operation
        assert (stale.status, stale.reason) == ("cancelled", "approval_revoked")
