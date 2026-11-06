"""Stored continuation rows are read as their own family; the unvalidated fail closed."""

import json
from pathlib import Path

import pytest

from yorunge.adapters.state import open_store
from yorunge.adapters.upload_maintenance import invalidate_uploads
from yorunge.adapters.upload_projection import review, summary
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import (
    VersionedTransferView,
    capacity,
    read_any_record,
    read_any_view,
    read_approval,
    read_plan,
    write_record,
)
from yorunge.domain.capabilities import instant
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3, DatasetUploadApprovalV3
from yorunge.domain.dataset_transfer_v3 import (
    TransferControlV3,
    TransferRecordV3,
    TransferVerificationV3,
)
from yorunge.domain.errors import YorungeError
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
CONTROL = TransferControlV3.model_validate_json(raw("dataset-continuation-control-v3.json"))
PROOF = TransferVerificationV3.model_validate_json(raw("dataset-continuation-verification-v3.json"))
ANOTHER_DATASET = "00000000-0000-4000-8000-000000000999"
# Two of three files are sent: 3 x 2 intents of 4 KiB, the 16 and 20 KiB fixed parts, and the
# closing proof reads all three files (512 bytes each).
RESERVATION = 16 * 1024 + 3 * 2 * 4096 + 20 * 1024 + 3 * 512


def install(store, *, operation=True, record=RECORD):
    """The rows a continuation would leave: the root's namespace and manifest, then its own."""
    connection = store.connection
    namespace = {
        key: PLAN.scope.model_dump(mode="json")[key]
        for key in ("service_origin", "api_base_path", "owner", "project_id")
    }
    namespace["name"] = PLAN.parameters.name
    connection.execute(
        "INSERT INTO upload_namespaces VALUES(?,?,NULL)",
        (PLAN.intent_digest(), encode(namespace).decode()),
    )
    connection.execute(
        "INSERT INTO upload_manifests VALUES(?,?)",
        (PLAN.manifest.digest, raw("dataset-manifest-v1.json").decode()),
    )
    connection.execute(
        "INSERT INTO upload_plans VALUES(?,?,?,?,?,?)",
        (
            PLAN.plan_id,
            PLAN.intent_digest(),
            PLAN.manifest.digest,
            PLAN.prepared_at,
            PLAN.expires_at,
            PLAN.encoded().decode(),
        ),
    )
    connection.execute(
        "INSERT INTO upload_approvals VALUES(?,?,?,?)",
        (PLAN.plan_id, APPROVAL.approval_id, APPROVAL.expires_at, APPROVAL.encoded().decode()),
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
                RESERVATION,
                record.encoded().decode(),
            ),
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


def test_a_continuations_history_fails_closed_until_its_graph_is_validated(tmp_path):
    with open_store(tmp_path / "state") as store:
        install(store, operation=False)
        view = read_any_view(store.connection, PLAN.plan_id)  # nothing started: no graph yet
        assert type(view.plan) is DatasetContinuationPlanV3 and view.operation is None
    with open_store(tmp_path / "started") as store:
        install(store)
        refuses(lambda: read_any_view(store.connection, PLAN.plan_id))


def test_capacity_fails_closed_for_a_stored_continuation_until_it_counts_one(tmp_path):
    with open_store(tmp_path / "state") as store:
        before = capacity(store.connection)
        install(store, operation=False)
        refuses(lambda: capacity(store.connection))
        assert before == (0, 0, 0, 0)


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


def test_the_original_summary_projection_refuses_a_continuation_instead_of_calling_it_legacy():
    view = VersionedTransferView(PLAN, APPROVAL, None)
    refuses(lambda: summary(view))
    refuses(lambda: review(view))


def test_a_continuations_control_and_proof_rows_are_read_as_their_own_family(tmp_path, monkeypatch):
    # validate_graph refuses every continuation until P02-3u, so the outcome of these reads would
    # be the same whichever family they decoded; it is replaced here to see what they return.
    monkeypatch.setattr("yorunge.adapters.upload_store.validate_graph", lambda view, manifest: None)
    with open_store(tmp_path / "state") as store:
        install(store)
        store.connection.execute(
            "INSERT INTO upload_controls VALUES(?,?,?)",
            (RECORD.operation_id, CONTROL.kind, CONTROL.encoded().decode()),
        )
        store.connection.execute(
            "INSERT INTO upload_verifications VALUES(?,?)",
            (RECORD.operation_id, PROOF.encoded().decode()),
        )
        view = read_any_view(store.connection, PLAN.plan_id)
        assert view.operation == RECORD
        assert [type(c) for c in view.controls] == [TransferControlV3]
        assert view.controls[0].encoded() == CONTROL.encoded()
        assert type(view.verification) is TransferVerificationV3
        assert view.verification.encoded() == PROOF.encoded()
        # A control keyed under another kind than its payload says is a disagreeing row.
        store.connection.execute("UPDATE upload_controls SET kind='recovery'")
        refuses(lambda: read_any_view(store.connection, PLAN.plan_id))


@pytest.mark.parametrize(
    "change",
    [{"dataset_id": ANOTHER_DATASET}, {"verification_only": True}],
    ids=["dataset", "mode"],
)
def test_the_dataset_and_mode_of_an_admitted_continuation_cannot_change(tmp_path, change):
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


def test_a_reset_refuses_a_stored_continuation_before_it_changes_anything(tmp_path, monkeypatch):
    written = []
    monkeypatch.setattr(
        "yorunge.adapters.upload_maintenance.write_record", lambda *args: written.append(args)
    )
    with open_store(tmp_path / "state") as store:
        install(store)
        before = store.connection.execute("SELECT * FROM upload_operations").fetchall()
        with pytest.raises(YorungeError) as error, store.connection:
            store.connection.execute("BEGIN IMMEDIATE")
            invalidate_uploads(
                store.connection,
                PLAN.scope.store_id,
                PLAN.scope.identity_epoch,
                instant("2026-11-03T11:00:00.000000Z"),
                store.deadline,
            )
        assert error.value.code == "state_invalid"
        # A rolled-back transaction would hide a write that came first: nothing was attempted.
        assert written == []
        assert store.connection.execute("SELECT * FROM upload_operations").fetchall() == before
        assert store.connection.execute("SELECT count(*) FROM upload_controls").fetchone() == (0,)


def test_the_namespace_of_a_latched_continuation_belongs_to_its_baseline(tmp_path, monkeypatch):
    # validate_graph would refuse a continuation first (until P02-3u), hiding the namespace rule.
    monkeypatch.setattr("yorunge.adapters.upload_store.validate_graph", lambda view, manifest: None)
    baseline = PLAN.continuation.baseline_operation_id
    assert baseline != RUNNING.operation_id
    with open_store(tmp_path / "state") as store:
        install(store, record=RUNNING)
        # The baseline's own rows are not built here; the rule under test is the comparison.
        store.connection.execute("PRAGMA foreign_keys=OFF")

        def own(operation_id):
            store.connection.execute(
                "UPDATE upload_namespaces SET create_operation_id=?", (operation_id,)
            )

        own(baseline)
        assert read_any_view(store.connection, PLAN.plan_id).operation == RUNNING
        for other in (RUNNING.operation_id, PLAN.continuation.dataset_id, None):
            own(other)
            refuses(lambda: read_any_view(store.connection, PLAN.plan_id))
    with open_store(tmp_path / "unlatched") as store:
        install(store)  # an admitted record has sent nothing: it owes the namespace nothing yet
        assert RECORD.workflow_latched is False
        assert read_any_view(store.connection, PLAN.plan_id).operation == RECORD


def test_the_repository_reads_a_continuation_as_itself_and_will_not_revoke_it_as_a_v2(tmp_path):
    with open_store(tmp_path / "state") as store:
        install(store, operation=False)
        uploads = StateUploads(store)
        # Reading is family-agnostic: the view is the continuation's own, never a converted one.
        view = uploads.show(plan_id=PLAN.plan_id)
        assert type(view.plan) is DatasetContinuationPlanV3 and type(view.approval) is type(
            APPROVAL
        )
        assert [entry.plan_id for entry in uploads.list()[0]] == [PLAN.plan_id]
        # Revoking re-decodes the approval as v1/v2 until P02-3r gives the continuation its own.
        approval = store.connection.execute("SELECT payload FROM upload_approvals").fetchone()
        refuses(lambda: uploads.revoke(PLAN.plan_id, PLAN.digest))
        assert (
            store.connection.execute("SELECT payload FROM upload_approvals").fetchone() == approval
        )
