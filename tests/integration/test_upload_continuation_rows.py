"""Stored continuation rows are read as their own family; the unvalidated fail closed."""

import json
from datetime import timedelta
from pathlib import Path

import pytest

from yorunge.adapters.state import open_store
from yorunge.adapters.upload_maintenance import invalidate_uploads
from yorunge.adapters.upload_projection import original_summary, review, summary
from yorunge.adapters.upload_store import (
    VersionedTransferView,
    capacity,
    read_any_record,
    read_any_view,
    read_approval,
    read_plan,
    write_record,
)
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3, DatasetUploadApprovalV3
from yorunge.domain.dataset_transfer_v3 import TransferRecordV3
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_public import DatasetUploadSummaryV3
from yorunge.domain.upload_versions import graph_of

FIXTURES = Path(__file__).parents[1] / "fixtures"


def raw(name):
    return (FIXTURES / name).read_bytes()


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


PLAN = DatasetContinuationPlanV3.model_validate_json(raw("dataset-continuation-plan-v3.json"))
APPROVAL = DatasetUploadApprovalV3.model_validate_json(raw("dataset-continuation-approval-v3.json"))
RECORD = TransferRecordV3.model_validate_json(raw("dataset-continuation-record-v3-admitted.json"))
RUNNING = TransferRecordV3.model_validate_json(raw("dataset-continuation-record-v3-running.json"))
ANOTHER_DATASET = "00000000-0000-4000-8000-000000000999"
# Two of three files are sent: 3 x 2 intents of 4 KiB, the 16 and 20 KiB fixed parts, and the
# closing proof reads all three files (512 bytes each).
RESERVATION = 16 * 1024 + 3 * 2 * 4096 + 20 * 1024 + 3 * 512


def install(store, *, operation=True, record=RECORD, plan=PLAN, approval=APPROVAL):
    """The rows a continuation would leave: the root's namespace and manifest, then its own."""
    connection = store.connection
    namespace = {
        key: plan.scope.model_dump(mode="json")[key]
        for key in ("service_origin", "api_base_path", "owner", "project_id")
    }
    namespace["name"] = plan.parameters.name
    connection.execute(
        "INSERT INTO upload_namespaces VALUES(?,?,NULL)",
        (plan.intent_digest(), encode(namespace).decode()),
    )
    connection.execute(
        "INSERT INTO upload_manifests VALUES(?,?)",
        (plan.manifest.digest, raw("dataset-manifest-v1.json").decode()),
    )
    connection.execute(
        "INSERT INTO upload_plans VALUES(?,?,?,?,?,?)",
        (
            plan.plan_id,
            plan.intent_digest(),
            plan.manifest.digest,
            plan.prepared_at,
            plan.expires_at,
            plan.encoded().decode(),
        ),
    )
    connection.execute(
        "INSERT INTO upload_approvals VALUES(?,?,?,?)",
        (plan.plan_id, approval.approval_id, approval.expires_at, approval.encoded().decode()),
    )
    if operation:
        connection.execute(
            "INSERT INTO upload_operations VALUES(?,?,?,?,?,?,?)",
            (
                record.operation_id,
                record.plan_id,
                record.intent_digest,
                record.revision,
                record.lease.expires_at if record.lease else None,
                graph_of(plan).operation_reservation(),
                record.encoded().decode(),
            ),
        )


def reset(store):
    with store.connection:
        store.connection.execute("BEGIN IMMEDIATE")
        invalidate_uploads(
            store.connection,
            PLAN.scope.store_id,
            PLAN.scope.identity_epoch,
            instant("2026-11-03T11:00:00.000000Z"),
            store.deadline,
        )


def refuses(call):
    with pytest.raises(YorungeError) as error:
        call()
    assert error.value.code == "state_invalid"


def test_the_reservation_formula_of_a_continuation_is_the_stored_one():
    assert graph_of(PLAN).operation_reservation() == RESERVATION


def test_plan_approval_and_record_rows_come_back_as_the_continuation_family(tmp_path):
    with open_store(tmp_path / "state") as store:
        install(store)
        plan = read_plan(store.connection, PLAN.plan_id)
        assert type(plan) is DatasetContinuationPlanV3 and plan.encoded() == PLAN.encoded()
        approval = read_approval(store.connection, plan)
        assert type(approval) is DatasetUploadApprovalV3
        assert approval.encoded() == APPROVAL.encoded()
        record = read_any_record(store.connection, RECORD.operation_id)
        assert type(record) is TransferRecordV3 and record.encoded() == RECORD.encoded()


def test_a_stored_row_that_disagrees_with_its_payload_is_state_invalid(tmp_path):
    cases = [
        ("UPDATE upload_plans SET prepared_at='2026-11-02T11:00:01.000000Z'", "plan"),
        ("UPDATE upload_plans SET expires_at='2026-11-02T11:14:59.000000Z'", "plan"),
        ("UPDATE upload_namespaces SET payload='{}'", "plan"),
        ("UPDATE upload_operations SET reservation=reservation+1", "record"),
        ("UPDATE upload_operations SET revision=revision+1", "record"),
        ("UPDATE upload_operations SET lease_expires_at=NULL", "record"),
        ("UPDATE upload_approvals SET expires_at='2026-11-02T11:14:59.000000Z'", "approval"),
    ]
    for statement, target in cases:
        with open_store(tmp_path / f"state-{abs(hash(statement))}") as store:
            install(store)
            store.connection.execute(statement)
            if target == "plan":
                refuses(lambda: read_plan(store.connection, PLAN.plan_id))
            elif target == "record":
                refuses(lambda: read_any_record(store.connection, RECORD.operation_id))
            else:
                refuses(lambda: read_approval(store.connection, PLAN))


def test_a_payload_that_is_not_the_canonical_bytes_of_its_family_is_state_invalid(tmp_path):
    with open_store(tmp_path / "state") as store:
        install(store)
        loose = PLAN.encoded().decode().replace(",", ", ", 1)
        store.connection.execute("UPDATE upload_plans SET payload=?", (loose,))
        refuses(lambda: read_plan(store.connection, PLAN.plan_id))


def test_a_record_of_another_version_than_its_plan_is_state_invalid(tmp_path):
    with open_store(tmp_path / "state") as store:
        install(store)
        v2 = json.loads(raw("dataset-transfer-graph-v2.json"))["record"]
        store.connection.execute(
            "UPDATE upload_operations SET payload=?, revision=?, lease_expires_at=?",
            (
                encode(v2).decode(),
                v2["revision"],
                v2["lease"]["expires_at"] if v2["lease"] else None,
            ),
        )
        refuses(lambda: read_any_record(store.connection, RECORD.operation_id))


def test_a_continuation_read_without_its_root_is_a_corrupt_history(tmp_path):
    # The rows alone, with no root upload to lead to, are not a history (the lineage tests build
    # real ones): a plan with no operation and a plan with one are both refused.
    for number, operation in enumerate((False, True)):
        with open_store(tmp_path / str(number)) as store:
            install(store, operation=operation)
            refuses(lambda: read_any_view(store.connection, PLAN.plan_id))


def test_capacity_counts_a_stored_continuation_as_a_plan_with_the_files_of_its_manifest(tmp_path):
    with open_store(tmp_path / "state") as store:
        assert capacity(store.connection) == (0, 0, 0, 0)
        install(store, operation=False)
        plans, operations, files, payload = capacity(store.connection)
        assert (plans, operations, files) == (1, 0, 3)
        assert payload >= 16 * 1024 + len(PLAN.encoded())  # the allowance and the plan row


def test_a_record_of_a_continuation_is_written_with_its_own_reservation_and_rules(tmp_path):
    with open_store(tmp_path / "state") as store:
        install(store, operation=False)
        write_record(store.connection, RECORD, None)
        stored = store.connection.execute(
            "SELECT reservation, revision FROM upload_operations WHERE operation_id=?",
            (RECORD.operation_id,),
        ).fetchone()
        assert stored == (RESERVATION, RECORD.revision)
        assert read_any_record(store.connection, RECORD.operation_id) == RECORD
        later = RECORD.model_copy(update={"revision": RECORD.revision + 1})
        write_record(store.connection, later, RECORD.revision)
        assert read_any_record(store.connection, RECORD.operation_id).revision == later.revision
        # The fixed parts of a stored record never change: the approval is the admission's.
        other_plan = RECORD.model_copy(
            update={"revision": later.revision + 1, "plan_digest": "0" * 64}
        )
        with pytest.raises(YorungeError) as error:
            write_record(store.connection, other_plan, later.revision)
        assert error.value.code == "operation_conflict"


def test_the_original_projections_refuse_a_continuation_instead_of_calling_it_legacy():
    view = VersionedTransferView(PLAN, APPROVAL, None)
    refuses(lambda: original_summary(view))
    refuses(lambda: review(view))
    assert type(summary(view)) is DatasetUploadSummaryV3  # its own summary is the other function


EARLIER = timestamp(instant(RECORD.created_at) - timedelta(seconds=1))
FIXED = {
    "dataset": {"dataset_id": ANOTHER_DATASET},
    "mode": {"verification_only": True},
    "plan": {"plan_id": ANOTHER_DATASET},
    "plan_digest": {"plan_digest": "0" * 64},
    "intent_digest": {"intent_digest": "0" * 64},
    "approval": {"approval": RECORD.approval.model_copy(update={"approval_id": ANOTHER_DATASET})},
    "created_at": {"created_at": EARLIER},
    # The lease names the same owner, so both change together to be a valid record at all.
    "write_owner": {
        "write_owner_id": ANOTHER_DATASET,
        "lease": RECORD.lease.model_copy(update={"owner_id": ANOTHER_DATASET}),
    },
    "write_access": {"write_access_digest": "b" * 64},
}


@pytest.mark.parametrize("change", FIXED.values(), ids=FIXED)
def test_the_fixed_part_of_an_admitted_continuation_record_cannot_change(tmp_path, change):
    with open_store(tmp_path / "state") as store:
        install(store, operation=False)
        write_record(store.connection, RECORD, None)
        later = RECORD.model_copy(update={"revision": RECORD.revision + 1, **change})
        with pytest.raises(YorungeError) as error:
            write_record(store.connection, later, RECORD.revision)
        assert error.value.code == "operation_conflict"
        assert read_any_record(store.connection, RECORD.operation_id) == RECORD


def test_a_latched_continuation_record_never_becomes_unlatched(tmp_path):
    cancelled = RUNNING.model_copy(
        update={
            "revision": RUNNING.revision + 1,
            "status": "cancelled",
            "workflow_latched": False,
            "reason": "identity_reset",
            "lease": None,
        }
    )
    assert (
        cancelled.model_dump()
        == TransferRecordV3.model_validate_json(cancelled.encoded()).model_dump()
    )
    with open_store(tmp_path / "state") as store:
        install(store, operation=False)
        write_record(store.connection, RUNNING, None)
        with pytest.raises(YorungeError) as error:
            write_record(store.connection, cancelled, RUNNING.revision)
        assert error.value.code == "operation_conflict"
        assert read_any_record(store.connection, RUNNING.operation_id) == RUNNING


@pytest.mark.parametrize(
    "change",
    [{"dataset_id": ANOTHER_DATASET}, {"verification_only": True}, {"plan_digest": "0" * 64}],
    ids=["dataset", "mode", "plan"],
)
def test_a_record_that_is_not_its_plans_admission_is_not_written(tmp_path, change):
    with open_store(tmp_path / "state") as store:
        install(store, operation=False)
        with pytest.raises(YorungeError) as error:
            write_record(store.connection, RECORD.model_copy(update=change), None)
        assert error.value.code == "state_invalid"
        assert store.connection.execute("SELECT count(*) FROM upload_operations").fetchone() == (0,)


@pytest.mark.parametrize(
    "change",
    [{"dataset_id": ANOTHER_DATASET}, {"verification_only": True}],
    ids=["dataset", "mode"],
)
def test_a_stored_record_that_is_not_its_plans_admission_is_state_invalid(tmp_path, change):
    with open_store(tmp_path / "state") as store:
        install(store)
        # Every index column still agrees with the payload; only the binding to the plan is wrong.
        store.connection.execute(
            "UPDATE upload_operations SET payload=?",
            (RECORD.model_copy(update=change).encoded().decode(),),
        )
        refuses(lambda: read_any_record(store.connection, RECORD.operation_id))


CHECK_ONLY_PLAN = DatasetContinuationPlanV3.model_validate_json(
    raw("dataset-continuation-plan-v3-verification-only.json")
)
CHECK_ONLY_APPROVAL = DatasetUploadApprovalV3.model_validate_json(
    raw("dataset-continuation-approval-v3-verification-only.json")
)
CHECK_ONLY_DONE = TransferRecordV3.model_validate_json(
    raw("dataset-continuation-record-v3-verification-only-succeeded.json")
)


def test_a_reset_leaves_a_finished_continuation_as_it_is(tmp_path, monkeypatch):
    # The guard is for what a reset would have to change; a terminal record is skipped before it.
    written = []
    monkeypatch.setattr(
        "yorunge.adapters.upload_maintenance.write_record", lambda *args: written.append(args)
    )
    assert CHECK_ONLY_DONE.status == "succeeded"
    with open_store(tmp_path / "state") as store:
        install(store, record=CHECK_ONLY_DONE, plan=CHECK_ONLY_PLAN, approval=CHECK_ONLY_APPROVAL)
        before = store.connection.execute("SELECT * FROM upload_operations").fetchall()
        reset(store)
        assert written == []
        assert store.connection.execute("SELECT * FROM upload_operations").fetchall() == before
