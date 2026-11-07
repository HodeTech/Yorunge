"""The closing read of a continuation: success, the check-only path and every way it can fail."""

import json
from datetime import timedelta

import pytest

from tests.fixtures.continuation_history import DATASET_ID, FIRST, build, canon, install
from tests.fixtures.continuation_lifecycle import (
    code_of,
    dump,
    proof_of,
    read_check,
    send_all,
    tick,
)
from yorunge.adapters.state import open_store
from yorunge.adapters.upload_projection import summary
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import read_any_view, validate_uploads
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.dataset_transfer_v2 import TransferVerificationV2
from yorunge.domain.dataset_transfer_v3 import TransferControlV3, TransferVerificationV3
from yorunge.domain.errors import OperationError
from yorunge.domain.upload_versions import proof_digest


def close(lifecycle, plan, record, **flags):
    """The closing read: the initial gate, then the proof of the whole dataset."""
    check = read_check(plan, lifecycle.clock)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        access = repository.prepare_initial_read(
            record.operation_id, record.lease, authorization=check
        )
        proof = proof_of(plan, timestamp(lifecycle.clock.value))
        view = repository.verified(
            record.operation_id, record.lease, proof, authorization=check, **flags
        )
        return access, proof, view


# --- success ----------------------------------------------------------------------------------


def test_a_continuation_that_sent_its_files_is_verified_by_reading_the_whole_dataset(lifecycle):
    plan, record = lifecycle.admitted()
    send_all(lifecycle, plan, record)
    access, proof, view = close(lifecycle, plan, record)
    assert access.policy == "explicit_read_attempt" and access.grant is None
    operation = view.operation
    assert (operation.status, operation.reason) == ("succeeded", "metadata_verified")
    assert operation.lease is None and operation.workflow_latched is True
    assert type(view.verification) is TransferVerificationV3 and view.verification == proof
    assert len(view.verification.files) == 3  # the whole manifest, though two files were sent
    assert [(c.kind, type(c)) for c in view.controls] == [("terminal", TransferControlV3)]
    assert view.controls[0].verification_digest == proof_digest(proof)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        validate_uploads(store.connection)
        found = summary(read_any_view(store.connection, plan.plan_id))
        assert found.operation_status == "succeeded" and found.verification_level == "metadata"
        assert found.authority_verified is False  # nothing proved the authority: a bare attempt


def test_a_second_continuation_runs_from_the_first_that_stopped_to_a_verified_dataset(lifecycle):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        install(store, build(lifecycle.root, 3, status="cancelled"))  # an attempt that is over
        install(store, build(lifecycle.root, 1, status="unknown", intents=5, acknowledged=4))
    plan, record = lifecycle.admitted(2, source=FIRST, indices=(2,), uncertain=(), intents=0)
    send_all(lifecycle, plan, record, [(kind, 2) for kind in ("presign", "put", "confirm")])
    _, proof, view = close(lifecycle, plan, record)
    assert (view.operation.status, view.operation.reason) == ("succeeded", "metadata_verified")
    assert len(view.intents) == len(view.receipts) == 3 and view.verification == proof
    assert view.plan.continuation.source_operation_id == FIRST
    with open_store(lifecycle.root_dir, timeout=60) as store:
        validate_uploads(store.connection)
        assert summary(read_any_view(store.connection, plan.plan_id)).continuation_of == FIRST


def test_a_proof_before_anything_was_sent_is_early_and_leaves_the_operation_alone(lifecycle):
    plan, record = lifecycle.admitted()
    check = read_check(plan, lifecycle.clock)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        before = dump(store)
        proof = proof_of(plan, timestamp(lifecycle.clock.value))
        assert (
            code_of(
                lambda: repository.verified(
                    record.operation_id, record.lease, proof, authorization=check
                )
            )
            == "operation_conflict"
        )
        assert dump(store) == before  # nothing was cancelled or marked: it is still admitted
        assert repository.show(operation_id=record.operation_id).operation.status == "admitted"


def test_a_continuation_with_an_unanswered_stage_is_not_verified_and_becomes_unknown(lifecycle):
    plan, record = lifecycle.admitted()
    lifecycle.arm(plan, record, "presign", 1)  # armed, never answered
    tick(lifecycle)
    check = read_check(plan, lifecycle.clock)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        assert (
            code_of(
                lambda: repository.prepare_initial_read(
                    record.operation_id, record.lease, authorization=check
                )
            )
            == "operation_uncertain"
        )
        proof = proof_of(plan, timestamp(lifecycle.clock.value))
        assert (
            code_of(
                lambda: repository.verified(
                    record.operation_id, record.lease, proof, authorization=check
                )
            )
            == "operation_uncertain"
        )
        view = repository.show(operation_id=record.operation_id)
        assert (view.operation.status, view.operation.reason) == ("unknown", "request_uncertain")
        assert view.verification is None
        # Asked again, it is no more and no less uncertain: no timeout, and nothing is written.
        before = dump(store)
        assert (
            code_of(
                lambda: repository.verified(
                    record.operation_id, record.lease, proof, authorization=check
                )
            )
            == "operation_uncertain"
        )
        assert dump(store) == before


def test_a_proof_of_another_family_than_the_record_is_refused_before_anything_is_written(
    lifecycle,
):
    plan, record = lifecycle.admitted(indices=(), uncertain=())
    check = read_check(plan, lifecycle.clock)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        before = dump(store)
        right = proof_of(plan, timestamp(lifecycle.clock.value))
        # The same observation, of the plan's own scope and dataset, in the older family.
        older = {**json.loads(right.encoded()), "schema_version": 2}
        old_family = TransferVerificationV2.model_validate_json(canon(older))
        assert (
            code_of(
                lambda: repository.verified(
                    record.operation_id, record.lease, old_family, authorization=check
                )
            )
            == "upload_plan_not_valid"
        )
        assert dump(store) == before


def test_the_proof_must_be_of_the_plans_dataset_and_cover_the_whole_manifest(lifecycle):
    plan, record = lifecycle.admitted()
    send_all(lifecycle, plan, record)
    check = read_check(plan, lifecycle.clock)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        before = dump(store)
        right = proof_of(plan, timestamp(lifecycle.clock.value))
        elsewhere = right.model_copy(update={"dataset_id": "00000000-0000-4000-8000-000000000777"})
        assert (
            code_of(
                lambda: repository.verified(
                    record.operation_id, record.lease, elsewhere, authorization=check
                )
            )
            == "operation_conflict"
        )
        short = right.model_copy(update={"files": right.files[:2]})
        assert (
            code_of(
                lambda: repository.verified(
                    record.operation_id, record.lease, short, authorization=check
                )
            )
            == "state_invalid"
        )
        assert dump(store) == before  # the savepoint took every attempt back
        assert right.dataset_id == DATASET_ID


# --- the check-only continuation --------------------------------------------------------------


def test_a_check_only_continuation_reads_and_is_verified_without_sending_or_a_latch(lifecycle):
    plan, record = lifecycle.admitted(indices=(), uncertain=())
    assert record.verification_only and record.status == "admitted"
    access, proof, view = close(lifecycle, plan, record)
    operation = view.operation
    assert access.policy == "explicit_read_attempt"
    assert (operation.status, operation.reason) == ("succeeded", "metadata_verified")
    assert operation.workflow_latched is False and operation.verification_only is True
    assert view.intents == () and view.receipts == () and view.verification == proof
    with open_store(lifecycle.root_dir, timeout=60) as store:
        validate_uploads(store.connection)


def test_a_finished_check_only_continuation_supersedes_its_source(lifecycle):
    plan, record = lifecycle.admitted(indices=(), uncertain=())
    close(lifecycle, plan, record)
    tick(lifecycle)
    # The root already continues into a verified, finished operation: another is refused.
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        other = lifecycle.plan(2)
        repository.save(other, lifecycle.manifest)
        repository.approve_continuation(
            other.plan_id, other.digest, other,
            acknowledge_unverified_authority=True, acknowledge_unpriced_cost=True,
            acknowledge_unconfirmed_effects=True,
        )  # fmt: skip
        with pytest.raises(OperationError) as error:
            repository.admit(other.plan_id, other)
        assert (error.value.code, error.value.operation_id) == (
            "operation_conflict",
            record.operation_id,
        )


def test_a_failed_read_cancels_a_check_only_continuation_and_reports_the_reads_own_error(lifecycle):
    plan, record = lifecycle.admitted(indices=(), uncertain=())
    failure = read_check(plan, lifecycle.clock, error="remote_failed")
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        with pytest.raises(OperationError) as error:
            repository.read_failed(record.operation_id, record.lease, failure)
        # The read's own code, never "operation_uncertain": nothing was sent.
        assert error.value.code == "remote_failed" and error.value.reason_code == "remote_failed"
        view = repository.show(operation_id=record.operation_id)
        assert (view.operation.status, view.operation.reason) == ("cancelled", "local_cancelled")
        assert view.operation.workflow_latched is False and view.intents == ()
        assert [(c.kind, type(c)) for c in view.controls] == [("terminal", TransferControlV3)]
        # The same plan cannot be started again: its operation is over (a new prepare is needed).
        assert repository.admit(plan.plan_id, plan).status == "cancelled"
        assert (
            code_of(
                lambda: repository.prepare_initial_read(
                    record.operation_id,
                    record.lease,
                    authorization=read_check(plan, lifecycle.clock),
                )
            )
            == "operation_conflict"
        )
        validate_uploads(store.connection)


def test_a_proof_that_comes_too_late_cancels_a_check_only_continuation_without_uncertainty(
    lifecycle,
):
    plan, record = lifecycle.admitted(indices=(), uncertain=())
    observed = timestamp(lifecycle.clock.value + timedelta(seconds=5))
    tick(lifecycle, 50)  # the observation is older than the thirty seconds a proof may be
    check = read_check(plan, lifecycle.clock)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        proof = proof_of(plan, observed)
        assert (
            code_of(
                lambda: repository.verified(
                    record.operation_id, record.lease, proof, authorization=check
                )
            )
            == "execution_timeout"
        )
        view = repository.show(operation_id=record.operation_id)
        assert (view.operation.status, view.operation.reason) == ("cancelled", "local_cancelled")
        assert view.verification is None and view.intents == ()


def test_a_failed_read_before_anything_was_sent_is_a_conflict_and_leaves_the_operation_alone(
    lifecycle,
):
    plan, record = lifecycle.admitted()
    failure = read_check(plan, lifecycle.clock, error="remote_failed")
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        before = dump(store)
        # No stage was armed, so no read can have been started: nothing is uncertain.
        for owner in (record.lease, None):
            assert (
                code_of(
                    lambda owner=owner: repository.read_failed(record.operation_id, owner, failure)
                )
                == "operation_conflict"
            )
        assert dump(store) == before
        assert repository.show(operation_id=record.operation_id).operation.status == "admitted"


def test_a_proof_observed_before_a_check_only_operation_began_is_refused_and_leaves_it_alone(
    lifecycle,
):
    tick(lifecycle, 10)
    before_admission = timestamp(lifecycle.clock.value - timedelta(seconds=3))
    plan, record = lifecycle.admitted(indices=(), uncertain=())
    tick(lifecycle)
    check = read_check(plan, lifecycle.clock)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        repository.prepare_initial_read(record.operation_id, record.lease, authorization=check)
        before = dump(store)
        # What `--prepare` read to classify the files cannot be the closing proof of the operation
        # that came after it: the operation is not at fault, so it stays and can read again.
        early = proof_of(plan, before_admission)
        assert (
            code_of(
                lambda: repository.verified(
                    record.operation_id, record.lease, early, authorization=check
                )
            )
            == "operation_conflict"
        )
        assert dump(store) == before
        again = proof_of(plan, timestamp(lifecycle.clock.value))
        view = repository.verified(record.operation_id, record.lease, again, authorization=check)
        assert (view.operation.status, view.operation.reason) == ("succeeded", "metadata_verified")


def test_a_failed_read_of_a_check_only_continuation_is_reported_by_its_owner_only(lifecycle):
    plan, record = lifecycle.admitted(indices=(), uncertain=())
    failure = read_check(plan, lifecycle.clock, error="remote_failed")
    stranger = record.lease.model_copy(update={"owner_id": "00000000-0000-4000-8000-0000000000aa"})
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        before = dump(store)
        for owner, code in ((None, "operation_conflict"), (stranger, "operation_lease_lost")):
            assert (
                code_of(
                    lambda owner=owner: repository.read_failed(record.operation_id, owner, failure)
                )
                == code
            )
            assert dump(store) == before  # a caller without the lease cannot cancel the operation
        lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")  # its own lease is over
        late = read_check(plan, lifecycle.clock, error="remote_failed")
        assert (
            code_of(lambda: repository.read_failed(record.operation_id, record.lease, late))
            == "operation_lease_lost"
        )
        assert dump(store) == before  # the lease cleanup, not this caller, cancels it


def test_a_late_proof_whose_marker_cannot_be_written_is_a_timeout_and_never_uncertain(
    lifecycle, monkeypatch
):
    plan, record = lifecycle.admitted(indices=(), uncertain=())
    observed = timestamp(lifecycle.clock.value + timedelta(seconds=5))
    tick(lifecycle, 50)  # the observation is older than the thirty seconds a proof may be
    check = read_check(plan, lifecycle.clock)
    original = StateUploads._uncertain_verification

    def after_the_lease_is_over(self, operation_id, owner):
        lifecycle.clock.value = instant("2026-11-02T11:04:00.000000Z")
        return original(self, operation_id, owner)

    monkeypatch.setattr(StateUploads, "_uncertain_verification", after_the_lease_is_over)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        with pytest.raises(OperationError) as error:
            repository.verified(
                record.operation_id, record.lease, proof_of(plan, observed), authorization=check
            )
        # The marker could not land, but nothing was sent: no uncertainty, only a late proof.
        assert (error.value.code, error.value.reason_code) == (
            "execution_timeout",
            "operation_lease_lost",
        )
        assert repository.show(operation_id=record.operation_id).operation.status == "admitted"
        cleaned = repository.cleanup_expired(record.operation_id)  # the lease cleanup finishes it
        assert (cleaned.operation.status, cleaned.operation.reason) == (
            "cancelled",
            "lease_expired",
        )


def test_a_late_proof_of_a_continuation_that_sent_something_stays_uncertain_without_a_marker(
    lifecycle, monkeypatch
):
    plan, record = lifecycle.admitted()
    send_all(lifecycle, plan, record)
    observed = timestamp(lifecycle.clock.value + timedelta(seconds=5))
    tick(lifecycle, 50)  # the observation is older than the thirty seconds a proof may be
    check = read_check(plan, lifecycle.clock)
    original = StateUploads._uncertain_verification

    def after_the_lease_is_over(self, operation_id, owner):
        lifecycle.clock.value = instant("2026-11-02T11:09:00.000000Z")
        return original(self, operation_id, owner)

    monkeypatch.setattr(StateUploads, "_uncertain_verification", after_the_lease_is_over)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        with pytest.raises(OperationError) as error:
            repository.verified(
                record.operation_id, record.lease, proof_of(plan, observed), authorization=check
            )
        # Something was sent, so what the late proof means is not known, marker or no marker.
        assert (error.value.code, error.value.reason_code) == (
            "operation_uncertain",
            "operation_lease_lost",
        )


def test_a_check_only_continuation_that_lost_its_lease_is_cancelled_and_not_taken_over(
    lifecycle,
):
    plan, record = lifecycle.admitted(indices=(), uncertain=())
    lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")
    check = read_check(plan, lifecycle.clock)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        # There is nothing sent to recover: taking a read lease over it cleans it up instead.
        assert (
            code_of(
                lambda: repository.acquire_read(
                    record.operation_id, authorization=check, accept_unverified_read=True
                )
            )
            == "operation_conflict"
        )
        view = repository.show(operation_id=record.operation_id)
        assert (view.operation.status, view.operation.reason) == ("cancelled", "lease_expired")
        validate_uploads(store.connection)


# --- a read that failed after something was sent ----------------------------------------------


def test_a_failed_read_after_the_first_intent_leaves_the_operation_unknown_and_unavailable(
    lifecycle,
):
    plan, record = lifecycle.admitted()
    send_all(lifecycle, plan, record)
    failure = read_check(plan, lifecycle.clock, error="transport_timeout")
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        with pytest.raises(OperationError) as error:
            repository.read_failed(record.operation_id, record.lease, failure)
        # The writer was still active: the outcome of the whole attempt is not known.
        assert error.value.code == "operation_uncertain"
        assert error.value.reason_code == "transport_timeout"
        view = repository.show(operation_id=record.operation_id)
        assert (view.operation.status, view.operation.reason) == ("unknown", "read_unavailable")
        assert [(c.kind, type(c)) for c in view.controls] == [("recovery", TransferControlV3)]
        validate_uploads(store.connection)


def test_an_unknown_continuation_is_verified_later_by_a_read_owner(lifecycle):
    plan, record = lifecycle.admitted()
    send_all(lifecycle, plan, record)
    lifecycle.clock.value = instant("2026-11-02T11:09:00.000000Z")  # the writer's lease is over
    check = read_check(plan, lifecycle.clock)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        lease = repository.acquire_read(
            record.operation_id, authorization=check, accept_unverified_read=True
        )
        assert lease.mode == "read" and lease.fence == 2
        proof = proof_of(plan, timestamp(lifecycle.clock.value))
        view = repository.verified(
            record.operation_id, lease, proof, authorization=check, accept_unverified_read=True
        )
        assert (view.operation.status, view.operation.reason) == ("succeeded", "metadata_verified")
        validate_uploads(store.connection)


def test_a_proof_that_contradicts_its_own_policy_is_refused_before_anything_is_written(lifecycle):
    plan, record = lifecycle.admitted(indices=(), uncertain=())
    check = read_check(plan, lifecycle.clock)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        repository.prepare_initial_read(record.operation_id, record.lease, authorization=check)
        before = dump(store)
        proof = proof_of(plan, timestamp(lifecycle.clock.value))
        verified_read = proof.model_copy(update={"authorization_policy": "verified_read"})
        assert (
            code_of(
                lambda: repository.verified(
                    record.operation_id, record.lease, verified_read, authorization=check
                )
            )
            == "state_invalid"  # it claims a verified read and holds no grant
        )
        assert dump(store) == before
