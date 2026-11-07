"""Versioned receipt in actual schema-7 full reads, reset consent and backups."""

import sqlite3

import pytest

from tests.contracts.test_create_receipt import GOLDEN, receipt
from tests.fixtures.upload_history import install_fixture
from yorunge import api
from yorunge.adapters.local_files import Deadline
from yorunge.adapters.state import DB_NAME, backup, open_store
from yorunge.adapters.upload_maintenance import upload_snapshot
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import capacity, read_any_view, validate_uploads
from yorunge.domain.create_receipt import CreateReceiptV2
from yorunge.domain.errors import YorungeError


def install_baseline(store, *, terminal=True):
    data = install_fixture(store, terminal=terminal)
    before = capacity(store.connection)
    store.connection.execute(
        "UPDATE upload_stage_receipts SET payload=? WHERE intent_id=?",
        (GOLDEN.decode(), data["receipts"][0]["intent_id"]),
    )
    assert capacity(store.connection) == before
    return data


@pytest.mark.parametrize("terminal", [False, True])
def test_real_new_receipt_read_full_capacity_and_backup(tmp_path, terminal):
    root = tmp_path / "state"
    with open_store(root) as store:
        data = install_baseline(store, terminal=terminal)
        repo = StateUploads(store)
        before = store.connection.total_changes
        view = repo.show(plan_id=data["plan"]["plan_id"])
        assert view.receipts[0] == receipt()
        assert isinstance(view.receipts[0], CreateReceiptV2)
        assert view.operation.dataset_id == view.receipts[0].created_dataset.id
        assert repo.show(operation_id=data["record"]["operation_id"]) == view
        assert repo.list()[0][0].operation_status == ("succeeded" if terminal else "unknown")
        validate_uploads(store.connection)
        assert store.verify().store_schema_version == 7
        assert store.connection.total_changes == before
        snapshot = upload_snapshot(store.connection, Deadline())
        assert snapshot["transfer_operation_count"] == 1
        assert view.receipts[0].created_dataset.name not in str(snapshot)
        saved = backup(store.root, store.root / DB_NAME, Deadline(), store.migrations)
        connection = sqlite3.connect(saved / "snapshot.sqlite3")
        try:
            assert read_any_view(connection, data["plan"]["plan_id"]).receipts == view.receipts
        finally:
            connection.close()
    with open_store(root) as reopened:
        assert (
            StateUploads(reopened).show(plan_id=data["plan"]["plan_id"]).receipts == view.receipts
        )


def test_identity_reset_preserves_full_create_baseline(tmp_path):
    root = tmp_path / "state"
    with open_store(root) as store:
        data = install_baseline(store, terminal=False)
    preview = api.preview_identity_reset(state_dir=root).data
    api.reset_identity(preview.digest, state_dir=root)
    with open_store(root) as store:
        view = StateUploads(store).show(plan_id=data["plan"]["plan_id"])
        assert view.operation.reason == "identity_reset"
        assert view.receipts[0] == receipt()
        validate_uploads(store.connection)


def test_wrong_kind_union_payload_corruption_is_state_invalid(tmp_path):
    with open_store(tmp_path / "state") as store:
        data = install_fixture(store)
        changed = receipt(intent_id=data["receipts"][1]["intent_id"])
        store.connection.execute(
            "UPDATE upload_stage_receipts SET payload=? WHERE intent_id=?",
            (changed.encoded().decode(), changed.intent_id),
        )
        with pytest.raises(YorungeError) as raised:
            validate_uploads(store.connection)
        assert raised.value.code == "state_invalid"
