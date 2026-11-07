"""Real schema-7 history reads/reset; v2 fixtures do not create write authority."""

import json
from functools import partial
from pathlib import Path

import pytest

from tests.fixtures.upload_history import encode, install_fixture
from yorunge import api
from yorunge.adapters.state import metadata, open_store
from yorunge.adapters.upload_maintenance import invalidate_uploads
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import (
    read_any_record,
    read_any_view,
    read_view,
    validate_uploads,
)
from yorunge.domain.capabilities import instant
from yorunge.domain.dataset_transfer import TransferRecord, operation_reservation
from yorunge.domain.dataset_upload import DatasetUploadPlan, upload_namespace
from yorunge.domain.errors import YorungeError

FIXTURES = Path(__file__).parents[1] / "fixtures"


def legacy_record(**changes):
    """The golden running v1 record, re-addressed with ``changes`` (it is valid on its own)."""
    data = json.loads((FIXTURES / "dataset-transfer-journal-v1.json").read_bytes())["record"]
    return TransferRecord.model_validate_json(encode({**data, **changes}))


def install_legacy_running(store):
    """A v1 plan with the golden running v1 record: the oldest family, on real rows."""
    pair = json.loads((FIXTURES / "dataset-upload-approved-v1.json").read_bytes())
    plan = DatasetUploadPlan.model_validate_json(encode(pair["plan"]))
    record = legacy_record(
        plan_id=plan.plan_id, plan_digest=plan.digest, intent_digest=plan.intent_digest()
    )
    c = store.connection
    c.execute(
        "INSERT INTO upload_namespaces VALUES(?,?,NULL)",
        (plan.intent_digest(), upload_namespace(plan.scope, plan.parameters.name).decode()),
    )
    c.execute(
        "INSERT INTO upload_manifests VALUES(?,?)",
        (plan.manifest.digest, (FIXTURES / "dataset-manifest-v1.json").read_text()),
    )
    c.execute(
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
    c.execute(
        "INSERT INTO upload_operations VALUES(?,?,?,?,?,?,?)",
        (
            record.operation_id,
            record.plan_id,
            record.intent_digest,
            record.revision,
            record.lease.expires_at if record.lease else None,
            operation_reservation(3),
            record.encoded().decode(),
        ),
    )
    return plan, record


def test_reset_makes_a_running_v1_operation_unknown_with_a_v1_recovery_control(tmp_path):
    # The continuation guard of the reset must not touch the oldest family.
    with open_store(tmp_path / "state") as store:
        plan, record = install_legacy_running(store)
        with store.connection:
            store.connection.execute("BEGIN IMMEDIATE")
            invalidate_uploads(
                store.connection,
                plan.scope.store_id,
                plan.scope.identity_epoch,
                instant("2026-11-03T11:00:00.000000Z"),
                store.deadline,
            )
        changed = read_any_record(store.connection, record.operation_id)
        assert (changed.schema_version, changed.status, changed.reason) == (
            1,
            "unknown",
            "identity_reset",
        )
        kind, payload = store.connection.execute(
            "SELECT kind,payload FROM upload_controls"
        ).fetchone()
        assert kind == "recovery" and json.loads(payload)["schema_version"] == 1


def test_a_record_of_another_family_than_its_plan_is_never_read_as_its_own(tmp_path):
    with open_store(tmp_path / "state") as store:
        data = install_fixture(store, terminal=False)  # a v2 plan with its v2 record
        v2 = data["record"]
        record = legacy_record(
            operation_id=v2["operation_id"],
            plan_id=v2["plan_id"],
            plan_digest=v2["plan_digest"],
            intent_digest=v2["intent_digest"],
        )
        # Every index column agrees with the v1 payload; only its family is not its plan's.
        store.connection.execute(
            "UPDATE upload_operations SET payload=?, revision=?, lease_expires_at=?",
            (
                record.encoded().decode(),
                record.revision,
                record.lease.expires_at if record.lease else None,
            ),
        )
        with pytest.raises(YorungeError) as error:
            read_any_record(store.connection, record.operation_id)
        assert error.value.code == "state_invalid"


def test_a_v2_record_of_a_dataset_its_create_receipt_did_not_make_is_invalid(tmp_path):
    with open_store(tmp_path / "state") as store:
        data = install_fixture(store, terminal=False)
        plan_id = data["plan"]["plan_id"]
        assert read_any_view(store.connection, plan_id).operation.dataset_id is not None
        stored = json.loads(
            store.connection.execute("SELECT payload FROM upload_operations").fetchone()[0]
        )
        stored["dataset_id"] = "00000000-0000-4000-8000-000000000777"
        store.connection.execute(
            "UPDATE upload_operations SET payload=?", (encode(stored).decode(),)
        )
        with pytest.raises(YorungeError) as error:
            read_any_view(store.connection, plan_id)
        assert error.value.code == "state_invalid"


def test_v2_full_history_show_list_and_validation_never_rewrite_payload(tmp_path):
    with open_store(tmp_path / "state") as store:
        data = install_fixture(store)
        before = store.connection.total_changes
        repo = StateUploads(store)
        found = repo.show(plan_id=data["plan"]["plan_id"])
        assert repo.show(operation_id=data["record"]["operation_id"]) == found
        rows, cursor = repo.list()
        assert len(rows) == 1
        assert rows[0].operation_status == "succeeded"
        assert cursor is None
        assert found.operation.reason == "metadata_verified"
        assert found.verification.grant is None
        validate_uploads(store.connection)
        assert store.verify().store_schema_version == 7
        assert store.connection.total_changes == before
        # A legacy writer/reader cannot consume this payload as v1.
        with pytest.raises(YorungeError) as error:
            read_view(store.connection, data["plan"]["plan_id"])
        assert error.value.code == "state_invalid"


def test_reset_coalesces_v2_recovery_in_existing_slot_and_preserves_history(tmp_path):
    with open_store(tmp_path / "state") as store:
        data = install_fixture(store, terminal=False)
        original = read_any_view(store.connection, data["plan"]["plan_id"])
        with store.connection:
            store.connection.execute("BEGIN IMMEDIATE")
            invalidate_uploads(
                store.connection,
                original.plan.scope.store_id,
                original.plan.scope.identity_epoch,
                instant("2026-11-03T11:00:00.000000Z"),
                store.deadline,
            )
        updated = read_any_view(store.connection, data["plan"]["plan_id"])
        assert updated.operation.schema_version == updated.controls[0].schema_version == 2
        assert updated.operation.status == "unknown"
        assert updated.operation.reason == "identity_reset"
        assert len(updated.controls) == 1
        assert updated.plan.encoded() == original.plan.encoded()
        assert updated.intents == original.intents
        assert updated.receipts == original.receipts
        validate_uploads(store.connection)


def test_terminal_v2_reset_is_immutable(tmp_path):
    with open_store(tmp_path / "state") as store:
        data = install_fixture(store)
        original = read_any_view(store.connection, data["plan"]["plan_id"])
        with store.connection:
            store.connection.execute("BEGIN IMMEDIATE")
            invalidate_uploads(
                store.connection,
                original.plan.scope.store_id,
                original.plan.scope.identity_epoch,
                instant("2026-11-03T11:00:00.000000Z"),
                store.deadline,
            )
        assert read_any_view(store.connection, data["plan"]["plan_id"]) == original


def test_public_identity_reset_handles_v2_epoch_and_new_preview_without_downgrade(tmp_path):
    root = tmp_path / "state"
    with open_store(root) as store:
        data = install_fixture(store, terminal=False)
        original = read_any_view(store.connection, data["plan"]["plan_id"])
    preview = api.preview_identity_reset(state_dir=root).data
    assert preview.current.transfer_operation_count == preview.current.unknown_transfer_count == 1
    api.reset_identity(preview.digest, state_dir=root)
    with open_store(root) as store:
        found = read_any_view(store.connection, data["plan"]["plan_id"])
        assert found.operation.schema_version == found.controls[0].schema_version == 2
        assert found.operation.observed_identity_epoch == metadata(store.connection).identity_epoch
        assert found.operation.observed_identity_epoch != original.operation.observed_identity_epoch
        assert found.controls[0].identity_epoch == found.operation.observed_identity_epoch
        assert found.plan.encoded() == original.plan.encoded()
        assert found.operation.approval.encoded() == original.operation.approval.encoded()
        assert store.verify().store_schema_version == 7


@pytest.mark.parametrize(
    "field,value",
    [
        ("revision", 1),
        ("reason", "read_unavailable"),
        ("observed_at", "2020-01-01T00:00:00.000000Z"),
        ("identity_epoch", "00000000-0000-4000-8000-000000000099"),
        ("clock_generation", 99),
    ],
)
@pytest.mark.parametrize("boundary", ["warm", "full"])
def test_unknown_recovery_marker_is_exact_current_state_not_unrelated_history(
    tmp_path, field, value, boundary
):
    with open_store(tmp_path / "state") as store:
        data = install_fixture(store, terminal=False)
        control = {**data["controls"][0], field: value}
        store.connection.execute(
            "UPDATE upload_controls SET payload=?", (encode(control).decode(),)
        )
        if boundary == "warm":
            invoke = partial(read_any_view, store.connection, data["plan"]["plan_id"])
        else:
            invoke = store.verify
        with pytest.raises(YorungeError) as error:
            invoke()
        assert error.value.code == "state_invalid"
