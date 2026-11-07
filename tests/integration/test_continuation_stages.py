"""The stages of an admitted continuation: arm, receipt, renew, stop and cleanup on real rows."""

import hashlib
import json
from datetime import timedelta
from functools import partial

import pytest

from tests.fixtures.continuation_history import CREATE_RECEIPT, DATASET_ID, FILES, canon
from yorunge.adapters.state import open_store
from yorunge.adapters.upload_maintenance import invalidate_uploads
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import acknowledged_stages, read_any_view, validate_uploads
from yorunge.domain.capabilities import instant
from yorunge.domain.create_receipt import CreateReceiptV2
from yorunge.domain.dataset_transfer_v3 import TransferControlV3, TransferRecordV3
from yorunge.domain.errors import YorungeError

TABLES = ("upload_operations", "upload_controls", "upload_stage_intents", "upload_stage_receipts")
STAGES = [(kind, index) for index in (1, 2) for kind in ("presign", "put", "confirm")]


def dump(store):
    return [store.connection.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in TABLES]


def code_of(call):
    with pytest.raises(YorungeError) as error:
        call()
    return error.value.code


def tick(lifecycle, seconds=1):
    lifecycle.clock.value += timedelta(seconds=seconds)


def view_of(lifecycle, record):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        return read_any_view(store.connection, record.plan_id)


def expected_digest(plan, kind, index):
    request = {
        "plan_digest": plan.digest,
        "kind": kind,
        "file_index": index,
        "file": FILES[index],
        "dataset_id": DATASET_ID,
        "object_key": f"objects/{index}" if kind in ("put", "confirm") else None,
    }
    return hashlib.sha256(canon(request)).hexdigest()


def run(lifecycle, plan, record, kind, index):
    """Arm one stage, let a second pass, and answer it as the provider would."""
    arm = lifecycle.arm(plan, record, kind, index)
    tick(lifecycle)
    view = view_of(lifecycle, record)
    intent = view.intents[-1]
    assert (intent.kind, intent.file_index) == (kind, index)
    return arm, intent, lifecycle.accept(record, intent)


# --- the stages -------------------------------------------------------------------------------


def test_the_stages_of_a_continuation_run_in_order_for_the_selected_files_only(lifecycle):
    plan, record = lifecycle.admitted()
    for position, (kind, index) in enumerate(STAGES, 1):
        _, intent, view = run(lifecycle, plan, record, kind, index)
        assert intent.sequence == position
        assert intent.request_digest == expected_digest(plan, kind, index)
        assert view.operation.status == "running" and view.operation.workflow_latched is True
        assert view.operation.dataset_id == DATASET_ID  # the plan's, not a create receipt's
        assert not any(i.kind in {"create", "project_link"} for i in view.intents)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        view = read_any_view(store.connection, plan.plan_id)
        assert len(view.intents) == len(view.receipts) == 6 and acknowledged_stages(view)
        assert type(view.operation) is TransferRecordV3
        validate_uploads(store.connection)


def test_a_stage_whose_predecessor_is_not_accepted_is_not_armed(lifecycle):
    plan, record = lifecycle.admitted()
    lifecycle.arm(plan, record, "presign", 1)  # armed, not yet answered
    with open_store(lifecycle.root_dir, timeout=60) as store:
        before = dump(store)
        repository = lifecycle.repository(store)
        total_end = lifecycle.clock.monotonic() + 900
        assert (
            code_of(
                lambda: repository.arm(
                    record.operation_id, record.lease, plan, "put", 1, total_end=total_end
                )
            )
            == "operation_conflict"
        )
        assert (
            code_of(
                lambda: repository.arm(
                    record.operation_id, record.lease, plan, "presign", 1, total_end=total_end
                )
            )
            == "operation_conflict"
        )  # and a stage is armed once
        assert dump(store) == before


ARM_REFUSALS = {
    "create": ("create", None),
    "link": ("project_link", None),
    "a file the continuation does not send": ("presign", 0),
    "a file stage without a file": ("presign", None),
    "a file beyond the manifest": ("presign", 9),
}


@pytest.mark.parametrize("stage", ARM_REFUSALS.values(), ids=ARM_REFUSALS)
def test_a_continuation_arms_neither_create_nor_link_nor_a_file_it_does_not_send(lifecycle, stage):
    plan, record = lifecycle.admitted()
    with open_store(lifecycle.root_dir, timeout=60) as store:
        before = dump(store)
        repository = lifecycle.repository(store)
        total_end = lifecycle.clock.monotonic() + 900
        kind, index = stage
        assert (
            code_of(
                lambda: repository.arm(
                    record.operation_id, record.lease, plan, kind, index, total_end=total_end
                )
            )
            == "invalid_request"
        )
        assert dump(store) == before


def test_a_check_only_continuation_arms_nothing(lifecycle):
    plan, record = lifecycle.admitted(indices=(), uncertain=())
    with open_store(lifecycle.root_dir, timeout=60) as store:
        before = dump(store)
        repository = lifecycle.repository(store)
        total_end = lifecycle.clock.monotonic() + 900
        assert (
            code_of(
                lambda: repository.arm(
                    record.operation_id, record.lease, plan, "presign", 1, total_end=total_end
                )
            )
            == "operation_conflict"
        )
        assert dump(store) == before


def test_the_receipt_of_a_stage_names_the_plans_dataset_and_is_no_create_receipt(lifecycle):
    plan, record = lifecycle.admitted()
    lifecycle.arm(plan, record, "presign", 1)
    tick(lifecycle)
    intent = view_of(lifecycle, record).intents[-1]
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        before = dump(store)
        foreign = CreateReceiptV2.model_validate_json(CREATE_RECEIPT).model_copy(
            update={"intent_id": intent.intent_id}
        )  # a create receipt for the stage that was armed
        assert (
            code_of(lambda: repository.receipt(record.operation_id, record.lease, foreign))
            == "invalid_request"
        )
        from tests.fixtures.continuation_lifecycle import receipt_for

        other = receipt_for(intent, lifecycle.clock).model_copy(
            update={"dataset_id": "00000000-0000-4000-8000-000000000555"}
        )
        assert (
            code_of(lambda: repository.receipt(record.operation_id, record.lease, other))
            == "state_invalid"
        )
        assert dump(store) == before


def test_a_rejection_with_nothing_else_in_flight_fails_the_operation(lifecycle):
    plan, record = lifecycle.admitted()
    run(lifecycle, plan, record, "presign", 1)
    lifecycle.arm(plan, record, "put", 1)
    tick(lifecycle)
    put = view_of(lifecycle, record).intents[-1]
    view = lifecycle.accept(record, put, rejected=True)
    assert (view.operation.status, view.operation.reason) == ("failed", "provider_rejected")
    assert view.operation.lease is None and view.operation.workflow_latched is True
    assert [(c.kind, type(c)) for c in view.controls] == [("terminal", TransferControlV3)]
    with open_store(lifecycle.root_dir, timeout=60) as store:
        validate_uploads(store.connection)


def test_a_rejection_with_another_request_in_flight_leaves_the_operation_unknown(
    lifecycle,
):
    plan, record = lifecycle.admitted()
    run(lifecycle, plan, record, "presign", 1)
    lifecycle.arm(plan, record, "put", 1)
    tick(lifecycle)
    put = view_of(lifecycle, record).intents[-1]
    lifecycle.arm(plan, record, "presign", 2)  # another request is in flight beside the put
    tick(lifecycle)
    view = lifecycle.accept(record, put, rejected=True)
    assert (view.operation.status, view.operation.reason) == ("unknown", "provider_rejected")
    assert [(c.kind, type(c)) for c in view.controls] == [("recovery", TransferControlV3)]
    assert len(view.intents) == 3 and len(view.receipts) == 2  # the presign of file 2 is open
    with open_store(lifecycle.root_dir, timeout=60) as store:
        validate_uploads(store.connection)


# --- stopping, expiring and renewing ----------------------------------------------------------


def test_stopping_before_the_first_intent_cancels_even_with_the_reason_that_says_uncertain(
    lifecycle,
):
    plan, record = lifecycle.admitted()
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        # The default reason says "uncertain": a continuation that sent nothing is cancelled anyway.
        stopped = repository.stop_local(record.operation_id, record.lease)
        assert (stopped.operation.status, stopped.operation.reason) == (
            "cancelled",
            "local_cancelled",
        )
        assert [(c.kind, type(c)) for c in stopped.controls] == [("terminal", TransferControlV3)]
        assert stopped.operation.lease is None and stopped.operation.workflow_latched is False
        validate_uploads(store.connection)


def test_a_check_only_continuation_is_stopped_as_cancelled_never_unknown(lifecycle):
    plan, record = lifecycle.admitted(indices=(), uncertain=())
    with open_store(lifecycle.root_dir, timeout=60) as store:
        stopped = lifecycle.repository(store).stop_local(
            record.operation_id, record.lease, "local_cancelled"
        )
        assert (stopped.operation.status, stopped.operation.reason) == (
            "cancelled",
            "local_cancelled",
        )
        assert stopped.operation.verification_only is True


def test_stopping_after_the_first_intent_leaves_the_operation_unknown_with_a_recovery_marker(
    lifecycle,
):
    plan, record = lifecycle.admitted()
    run(lifecycle, plan, record, "presign", 1)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        stopped = lifecycle.repository(store).stop_local(record.operation_id, record.lease)
        assert (stopped.operation.status, stopped.operation.reason) == (
            "unknown",
            "request_uncertain",
        )
        assert [c.kind for c in stopped.controls] == ["recovery"]
        validate_uploads(store.connection)


def test_an_expired_continuation_that_sent_nothing_is_cancelled_and_its_source_is_untouched(
    lifecycle,
):
    plan, record = lifecycle.admitted()
    root = lifecycle.root["record"]["operation_id"]
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        source_rows = store.connection.execute(
            "SELECT * FROM upload_operations WHERE operation_id=?", (root,)
        ).fetchall()
        assert (
            code_of(lambda: repository.cleanup_expired(record.operation_id)) == "operation_conflict"
        )
        lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")  # the lease is over
        cleaned = repository.cleanup_expired(record.operation_id)
        assert (cleaned.operation.status, cleaned.operation.reason) == (
            "cancelled",
            "lease_expired",
        )
        assert cleaned.operation.fence == 2 and cleaned.operation.lease is None
        assert [(c.kind, type(c)) for c in cleaned.controls] == [("terminal", TransferControlV3)]
        assert (
            store.connection.execute(
                "SELECT * FROM upload_operations WHERE operation_id=?", (root,)
            ).fetchall()
            == source_rows
        )  # the source stays as the producer left it
        validate_uploads(store.connection)


def test_an_expired_continuation_that_had_sent_something_becomes_unknown(lifecycle):
    plan, record = lifecycle.admitted()
    run(lifecycle, plan, record, "presign", 1)
    lifecycle.clock.value = instant("2026-11-02T11:08:00.000000Z")
    with open_store(lifecycle.root_dir, timeout=60) as store:
        cleaned = lifecycle.repository(store).cleanup_expired(record.operation_id)
        assert (cleaned.operation.status, cleaned.operation.reason) == (
            "unknown",
            "request_uncertain",
        )
        assert cleaned.operation.fence == 2 and cleaned.operation.workflow_latched is True
        assert [c.kind for c in cleaned.controls] == ["recovery"]
        validate_uploads(store.connection)


def test_the_lease_of_a_continuation_is_renewed_by_its_own_write_owner(lifecycle):
    plan, record = lifecycle.admitted()
    tick(lifecycle, 20)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        renewed = lifecycle.repository(store).renew(record.operation_id, record.lease)
        assert renewed.owner_id == record.lease.owner_id and renewed.fence == record.lease.fence
        assert instant(renewed.expires_at) > instant(record.lease.expires_at)
        now = read_any_view(store.connection, plan.plan_id).operation
        assert now.lease == renewed and json.loads(now.encoded())["lease"]["owner_id"]


# --- the current check each stage is armed on -------------------------------------------------


def test_a_stage_is_not_armed_on_a_stale_a_foreign_or_a_wrong_current_check(lifecycle):
    plan, record = lifecycle.admitted()
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        stale = repository.capture(plan, "upload_created_dataset", DATASET_ID)
        tick(lifecycle, 31)  # older than the thirty seconds a check may be
        elsewhere = "00000000-0000-4000-8000-000000000777"
        refused = {
            "stale": (stale, "upload_plan_not_valid"),
            "of another dataset": (
                repository.capture(plan, "upload_created_dataset", elsewhere),
                "state_changed",
            ),
            "for another action": (
                repository.capture(plan, "read_created_dataset", DATASET_ID),
                "state_changed",
            ),
        }
        before = dump(store)
        total_end = lifecycle.clock.monotonic() + 900
        for name, (check, code) in refused.items():
            arm = partial(
                StateUploads.arm,
                repository,
                record.operation_id,
                record.lease,
                check,
                "presign",
                1,
                total_end=total_end,
            )
            assert code_of(arm) == code, name
        assert dump(store) == before


# --- an identity reset over what the gates wrote ----------------------------------------------

NEW_EPOCH = "00000000-0000-4000-8000-0000000000e9"
RESET_CASES = {
    "after the first intent": ({}, True, ("unknown", "identity_reset", "recovery")),
    "check-only": (
        {"indices": (), "uncertain": ()},
        False,
        ("cancelled", "identity_reset", "terminal"),
    ),
}


@pytest.mark.parametrize("case", RESET_CASES.values(), ids=RESET_CASES)
def test_an_identity_reset_closes_a_record_the_gates_wrote_like_any_other_history(lifecycle, case):
    spec, sends, (status, reason, kind) = case
    plan, record = lifecycle.admitted(**spec)
    if sends:
        run(lifecycle, plan, record, "presign", 1)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        scope = lifecycle.root["plan"]["scope"]
        with store.connection:
            store.connection.execute("BEGIN IMMEDIATE")
            invalidate_uploads(
                store.connection,
                scope["store_id"],
                NEW_EPOCH,
                instant("2026-11-03T11:00:00.000000Z"),
                store.deadline,
            )
        view = read_any_view(store.connection, plan.plan_id)
        assert (view.operation.status, view.operation.reason) == (status, reason)
        assert [(c.kind, type(c)) for c in view.controls] == [(kind, TransferControlV3)]
        assert view.operation.lease is None
        validate_uploads(store.connection)
