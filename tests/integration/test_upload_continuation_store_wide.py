"""What a stored continuation changes for the store as a whole, on real roots and chains.

The histories are the ones of ``tests/fixtures/continuation_history.py``: a real root upload and
continuations chained to it, stored as SQLite rows. Expected figures are written out here from the
builder's own plain data (and from independent arithmetic), never taken from the code under test.
"""

import json
from dataclasses import replace
from functools import partial
from pathlib import Path

import pytest

import yorunge.adapters.upload_maintenance as maintenance_module
import yorunge.adapters.upload_store as store_module
from tests.fixtures.continuation_history import (
    DATASET_ID,
    FILES,
    FIRST,
    OTHER,
    SECOND,
    SHAPES,
    UNKNOWN,
    build,
    canon,
    install,
    install_root,
    reservation,
    world,
)
from yorunge import api
from yorunge.adapters.expiry_fences import next_expiry
from yorunge.adapters.local_files import Deadline
from yorunge.adapters.state import metadata, open_store
from yorunge.adapters.upload_maintenance import invalidate_uploads, upload_snapshot
from yorunge.adapters.upload_projection import original_summary, review, summary
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import (
    VersionedTransferView,
    capacity,
    quota_used,
    read_any_view,
    require_capacity,
    validate_uploads,
)
from yorunge.domain.capabilities import instant
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3, DatasetUploadApprovalV3
from yorunge.domain.dataset_transfer_v3 import TransferControlV3, TransferRecordV3
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_public import DatasetUploadSummaryV3

FIXTURES = Path(__file__).parents[1] / "fixtures"
LATER = {"status": "running", "source": FIRST, "indices": (2,), "uncertain": ()}
KIB = 1024
BOUNDS = (
    "MAX_TRANSFER_PLANS",
    "MAX_TRANSFER_OPERATIONS",
    "MAX_TRANSFER_FILES",
    "MAX_TRANSFER_PAYLOAD_BYTES",
)


def raw(name):
    return json.loads((FIXTURES / name).read_bytes())


def code_of(call):
    with pytest.raises(YorungeError) as error:
        call()
    return error.value.code


def expected_counters(base, items):
    """The counters of a store holding ``base`` and then these continuations, from the figures."""
    plans, operations, files, payload = base
    for item in items:
        plans += 1
        operations += item.record is not None
        files += len(FILES)  # every plan stands for the whole manifest
        payload += len(canon(item.plan)) + 16 * KIB  # the plan row and the flat allowance
        payload += reservation(item.selected) if item.record is not None else 0
    return plans, operations, files, payload


# --- capacity ------------------------------------------------------------------------------------


def root_counters(tmp_path):
    with world(tmp_path / "root") as (store, _, _):
        return capacity(store.connection)


def test_capacity_counts_a_continuation_as_a_plan_an_operation_its_files_and_its_bytes(tmp_path):
    base = root_counters(tmp_path)
    assert base[0] == base[1] == 1 and base[2] == len(FILES)
    with world(tmp_path / "chain", UNKNOWN, LATER) as (store, _, built):
        assert capacity(store.connection) == expected_counters(base, built)
    # A prepared continuation that was never admitted is a plan with no operation and no journal.
    with world(tmp_path / "plan", {"status": "admitted", "plan_only": True}) as (store, _, built):
        assert capacity(store.connection) == expected_counters(base, built)
        assert capacity(store.connection)[1] == base[1]


@pytest.mark.parametrize("bound", range(4), ids=[name.lower() for name in BOUNDS])
def test_each_bound_holds_a_continuation_to_the_exact_figure_of_the_counters(
    tmp_path, monkeypatch, bound
):
    with world(tmp_path, UNKNOWN, LATER) as (store, _, _):
        found = capacity(store.connection)
        connection = store.connection
        monkeypatch.setattr(store_module, BOUNDS[bound], found[bound])
        require_capacity(connection)  # exactly full is not over
        assert quota_used(connection) is not None
        monkeypatch.setattr(store_module, BOUNDS[bound], found[bound] - 1)
        assert code_of(lambda: require_capacity(connection)) == "upload_capacity_exceeded"
        assert code_of(lambda: require_capacity(connection, corrupt=True)) == "state_invalid"
        assert code_of(lambda: quota_used(connection)) == "state_invalid"
        assert code_of(lambda: validate_uploads(connection)) == "state_invalid"


def test_the_real_plan_bound_admits_a_store_of_128_plans_and_refuses_the_next(tmp_path):
    prepared = {"status": "admitted", "plan_only": True}
    with world(tmp_path, *[prepared] * 127) as (store, root, built):
        assert capacity(store.connection)[0] == 128
        require_capacity(store.connection)
        validate_uploads(store.connection)  # a full store is valid, only a fuller one is not
        beyond = build(root, 128, status="admitted")
        beyond.record = None  # a plan only: the bound is the plans', not the operations'
        install(store, beyond)
        assert capacity(store.connection)[0] == 129
        assert code_of(lambda: require_capacity(store.connection)) == "upload_capacity_exceeded"
        assert code_of(lambda: validate_uploads(store.connection)) == "state_invalid"
        assert len(built) == 127


def test_quota_used_is_what_the_capacity_check_counts_and_nothing_else(tmp_path):
    with world(tmp_path, UNKNOWN, LATER) as (store, _, _):
        used = quota_used(store.connection)
        assert (used.plans, used.operations, used.files, used.payload_bytes) == capacity(
            store.connection
        )
        assert used.plans == used.operations == 3 and used.files == 3 * len(FILES)


# --- the full validation of a store ---------------------------------------------------------------


@pytest.mark.parametrize("shape", SHAPES.values(), ids=SHAPES)
def test_a_store_holding_any_shape_of_continuation_passes_the_full_validation(tmp_path, shape):
    with world(tmp_path, shape) as (store, _, _):
        validate_uploads(store.connection)
        store.verify()


def test_a_store_holding_a_chain_passes_the_full_validation(tmp_path):
    with world(tmp_path, UNKNOWN, LATER) as (store, _, _):
        validate_uploads(store.connection)


def live(**changes):
    return {"status": "running", **changes}


SIBLINGS = {
    "two running continuations of one source": (live(), live()),
    "a running and an admitted one": (live(), {"status": "admitted"}),
    "an unknown and a running one": (UNKNOWN, live()),
    "a finished check-only one and a running one": (SHAPES["check-only succeeded"], live()),
}


@pytest.mark.parametrize("pair", SIBLINGS.values(), ids=SIBLINGS)
def test_a_source_with_two_continuations_that_were_not_cancelled_is_a_corrupt_history(
    tmp_path, pair
):
    with world(tmp_path, *pair) as (store, _, _):
        assert code_of(lambda: validate_uploads(store.connection)) == "state_invalid"


CONTROLS = {
    "a cancelled one beside a running one": ({"status": "cancelled"}, live()),
    "a running one beside a cancelled one": (live(), {"status": "cancelled"}),
    "many cancelled ones": ({"status": "cancelled"},) * 5,
    "a plan that was never admitted beside a running one": (
        {"status": "admitted", "plan_only": True},
        live(),
    ),
}


@pytest.mark.parametrize("pair", CONTROLS.values(), ids=CONTROLS)
def test_cancelled_continuations_and_unadmitted_plans_do_not_make_a_source_superseded(
    tmp_path, pair
):
    with world(tmp_path, *pair) as (store, _, _):
        validate_uploads(store.connection)


def test_the_one_continuation_a_source_may_have_is_counted_per_source(tmp_path):
    # The root has one continuation and that one has another: two sources, one each.
    with world(tmp_path, UNKNOWN, LATER) as (store, _, _):
        validate_uploads(store.connection)
    # A third continuation of the first source is the first one's second descendant.
    second = {**LATER, "status": "admitted", "intents": 0, "acknowledged": 0}
    third = {**LATER, "status": "running"}
    with world(tmp_path / "bad", UNKNOWN, second, third) as (store, _, _):
        assert code_of(lambda: validate_uploads(store.connection)) == "state_invalid"


def test_a_fault_of_an_earlier_continuation_is_found_by_the_full_validation(tmp_path):
    flawed = {
        **UNKNOWN,
        "uncertain": (),
    }  # resends file 1 and leaves its unanswered confirm unmarked
    with world(tmp_path, flawed, {**LATER, "intents": 2, "acknowledged": 2}) as (store, _, _):
        assert code_of(lambda: validate_uploads(store.connection)) == "state_invalid"


# --- the identity reset ---------------------------------------------------------------------------


def reset(store, root, *, epoch=None, now="2026-11-03T11:00:00.000000Z"):
    scope = root["plan"]["scope"]
    with store.connection:
        store.connection.execute("BEGIN IMMEDIATE")
        invalidate_uploads(
            store.connection,
            scope["store_id"],
            epoch or scope["identity_epoch"],
            instant(now),
            store.deadline,
        )


def control_rows(store, operation_id):
    return {
        kind: json.loads(payload)
        for kind, payload in store.connection.execute(
            "SELECT kind,payload FROM upload_controls WHERE operation_id=?", (operation_id,)
        )
    }


def expected_control(kind, record, *, epoch, now):
    return {
        "schema_version": 3,
        "kind": kind,
        "operation_id": record["operation_id"],
        "revision": record["revision"] + 1,
        "observed_at": now,
        "identity_epoch": epoch,
        "clock_generation": 1,
        "reason": "identity_reset",
        "verification_digest": None,
    }


NOW = "2026-11-03T11:00:00.000000Z"


def test_a_reset_leaves_a_continuation_that_sent_something_unknown_with_a_v3_recovery_control(
    tmp_path,
):
    with world(tmp_path, live()) as (store, root, (item,)):
        epoch = root["plan"]["scope"]["identity_epoch"]
        before = read_any_view(store.connection, item.plan["plan_id"])
        assert before.operation.workflow_latched and before.operation.status == "running"
        reset(store, root)
        after = read_any_view(store.connection, item.plan["plan_id"])
        assert type(after.operation) is TransferRecordV3
        assert (after.operation.status, after.operation.reason) == ("unknown", "identity_reset")
        assert after.operation.lease is None and after.operation.workflow_latched
        assert after.operation.revision == item.record["revision"] + 1
        assert after.operation.updated_at == NOW
        assert (
            after.operation.observed_identity_epoch,
            after.operation.observed_clock_generation,
        ) == (
            epoch,
            1,
        )
        # The one control is the recovery marker, written in the record's own family.
        assert [type(control) for control in after.controls] == [TransferControlV3]
        assert control_rows(store, item.record["operation_id"]) == {
            "recovery": expected_control("recovery", item.record, epoch=epoch, now=NOW)
        }
        # Nothing but the record's state moved: the plan, the approval and the journal are intact.
        assert after.plan.encoded() == before.plan.encoded()
        assert after.approval.encoded() == before.approval.encoded()
        assert after.intents == before.intents and after.receipts == before.receipts
        validate_uploads(store.connection)


def test_a_reset_cancels_a_continuation_that_sent_nothing_with_a_v3_terminal_control(tmp_path):
    with world(tmp_path, {"status": "admitted"}) as (store, root, (item,)):
        epoch = root["plan"]["scope"]["identity_epoch"]
        reset(store, root)
        after = read_any_view(store.connection, item.plan["plan_id"])
        assert (after.operation.status, after.operation.reason) == ("cancelled", "identity_reset")
        assert not after.operation.workflow_latched and after.operation.lease is None
        assert control_rows(store, item.record["operation_id"]) == {
            "terminal": expected_control("terminal", item.record, epoch=epoch, now=NOW)
        }
        validate_uploads(store.connection)


def test_a_check_only_continuation_is_cancelled_by_a_reset_never_left_unknown(tmp_path):
    with world(tmp_path, SHAPES["check-only admitted"]) as (store, root, (item,)):
        assert item.record["verification_only"] is True
        reset(store, root)
        after = read_any_view(store.connection, item.plan["plan_id"])
        assert (after.operation.status, after.operation.reason) == ("cancelled", "identity_reset")
        assert set(control_rows(store, item.record["operation_id"])) == {"terminal"}


def test_a_reset_resets_a_whole_chain_and_leaves_what_is_finished_alone(tmp_path):
    finished = SHAPES["check-only succeeded"]
    with world(tmp_path, UNKNOWN, {**LATER, "intents": 2, "acknowledged": 2}) as (
        store,
        root,
        built,
    ):
        root_before = read_any_view(store.connection, root["plan"]["plan_id"])
        reset(store, root)
        for item in built:
            after = read_any_view(store.connection, item.plan["plan_id"])
            assert (after.operation.status, after.operation.reason) == ("unknown", "identity_reset")
        # The root is the same kind of source: its own recovery marker moved forward too.
        root_after = read_any_view(store.connection, root["plan"]["plan_id"])
        assert root_after.operation.status == "unknown"
        assert root_after.operation.revision == root_before.operation.revision + 1
        # Reading the continuation still finds its whole lineage and the same baseline.
        assert StateUploads(store).require_created_baseline(SECOND).id == DATASET_ID
        validate_uploads(store.connection)
    with world(tmp_path / "done", finished) as (store, root, (item,)):
        own = item.record["operation_id"]
        row = "SELECT * FROM upload_operations WHERE operation_id=?"
        controls = "SELECT * FROM upload_controls WHERE operation_id=?"
        before = store.connection.execute(row, (own,)).fetchall()
        before_controls = store.connection.execute(controls, (own,)).fetchall()
        reset(store, root)
        after = read_any_view(store.connection, item.plan["plan_id"])
        assert after.operation.status == "succeeded"  # a terminal record is skipped, not reset
        assert store.connection.execute(row, (own,)).fetchall() == before
        assert store.connection.execute(controls, (own,)).fetchall() == before_controls
        validate_uploads(store.connection)


def test_a_reset_that_fails_on_the_way_changes_nothing(tmp_path, monkeypatch):
    with world(tmp_path, live()) as (store, root, (item,)):
        before = store.connection.execute("SELECT * FROM upload_operations").fetchall()

        def fail(*args):
            raise RuntimeError("synthetic failure after the first write")

        monkeypatch.setattr(maintenance_module, "decode_versioned", fail)
        with pytest.raises(RuntimeError):
            reset(store, root)
        assert store.connection.execute("SELECT * FROM upload_operations").fetchall() == before
        assert item.record["status"] == "running"


def test_the_public_identity_reset_carries_a_chain_to_the_new_epoch_and_the_store_verifies(
    tmp_path,
):
    root_dir = tmp_path / "state"
    with open_store(root_dir, timeout=60) as store:
        root = install_root(store)
        built = [build(root, n, **spec) for n, spec in enumerate((UNKNOWN, LATER), 1)]
        for item in built:
            install(store, item)
        old_epoch = metadata(store.connection).identity_epoch
    preview = api.preview_identity_reset(state_dir=root_dir).data
    current = preview.current
    assert current.upload_plan_count == current.transfer_operation_count == 3
    assert current.nonterminal_transfer_count == 3 and current.unknown_transfer_count == 2
    api.reset_identity(preview.digest, state_dir=root_dir)
    with open_store(root_dir, timeout=60) as store:
        new_epoch = metadata(store.connection).identity_epoch
        assert new_epoch != old_epoch
        for item in built:
            after = read_any_view(store.connection, item.plan["plan_id"])
            assert type(after.operation) is TransferRecordV3
            assert after.operation.observed_identity_epoch == new_epoch
            assert (after.operation.status, after.operation.reason) == ("unknown", "identity_reset")
            assert after.controls[0].identity_epoch == new_epoch
            assert type(after.controls[0]) is TransferControlV3
        assert store.verify().store_schema_version == 7
        # Reading the second continuation still walks back to the root's baseline.
        assert StateUploads(store).require_created_baseline(SECOND).id == DATASET_ID


# --- the reset preview ----------------------------------------------------------------------------


def fingerprint(store):
    return upload_snapshot(store.connection, Deadline())["transfer_fingerprint"]


def test_the_preview_fingerprint_does_not_change_when_only_a_lease_is_renewed(tmp_path):
    with world(tmp_path, live()) as (store, _, (item,)):
        before = fingerprint(store)
        record = dict(item.record)
        lease = dict(record["lease"])
        lease["renewed_at"], lease["expires_at"] = (
            "2026-11-02T11:00:03.000000Z",  # a renewal inside the record's own lifetime
            "2026-11-02T11:02:33.000000Z",  # one lease term later
        )
        record["lease"] = lease
        store.connection.execute(
            "UPDATE upload_operations SET payload=?, lease_expires_at=? WHERE operation_id=?",
            (canon(record).decode(), lease["expires_at"], record["operation_id"]),
        )
        assert read_any_view(store.connection, item.plan["plan_id"]).operation.lease.fence == 1
        assert fingerprint(store) == before


def perturbations(model):
    """One changed copy of ``model`` per field that holds a plain value (no validation runs)."""
    for name in type(model).model_fields:
        value = getattr(model, name)
        if isinstance(value, bool):
            yield name, model.model_copy(update={name: not value})
        elif isinstance(value, int):
            yield name, model.model_copy(update={name: value + 1})
        elif isinstance(value, str):
            yield name, model.model_copy(update={name: value + "0"})


def test_the_preview_fingerprint_changes_with_every_plain_field_of_a_continuations_rows(
    tmp_path, monkeypatch
):
    with world(tmp_path, live()) as (store, _, (item,)):
        real = read_any_view
        plan_id = item.plan["plan_id"]

        def digest_with(change):
            def patched(connection, identifier, views=None):
                view = real(connection, identifier, views)
                return change(view) if identifier == plan_id else view

            monkeypatch.setattr(maintenance_module, "read_any_view", patched)
            return fingerprint(store)

        same = digest_with(lambda view: view)
        view = real(store.connection, plan_id)
        changed = {}
        for part in ("plan", "approval", "operation"):
            for name, model in perturbations(getattr(view, part)):
                changed[f"{part}.{name}"] = digest_with(
                    lambda v, part=part, model=model: replace(v, **{part: model})
                )
        assert same not in changed.values()
        assert len(set(changed.values())) == len(changed)  # each field leaves its own mark
        # The v3-only fields are among them, and so is the file selection of the binding.
        assert {"operation.verification_only", "plan.digest", "operation.revision"} <= set(changed)
        binding = view.plan.continuation
        moved = view.plan.model_copy(
            update={"continuation": binding.model_copy(update={"file_indices": (1,)})}
        )
        assert digest_with(lambda v: replace(v, plan=moved)) not in (same, *changed.values())
        # A lease renewal is not a field of the reset: its two instants leave the digest alone.
        lease = view.operation.lease
        renewed = view.operation.model_copy(
            update={
                "lease": lease.model_copy(
                    update={
                        "renewed_at": "2026-11-02T11:00:09.000000Z",
                        "expires_at": "2027-01-01T00:00:00.000000Z",
                    }
                )
            }
        )
        assert digest_with(lambda v: replace(v, operation=renewed)) == same
        # but its owner is.
        other = view.operation.model_copy(
            update={"lease": lease.model_copy(update={"owner_id": OTHER})}
        )
        assert digest_with(lambda v: replace(v, operation=other)) != same


def test_the_preview_counts_and_fingerprint_read_every_continuation_of_the_store(tmp_path):
    with world(tmp_path, UNKNOWN, LATER) as (store, _, _):
        counts = upload_snapshot(store.connection, Deadline())
        assert counts["upload_plan_count"] == counts["transfer_operation_count"] == 3
        assert counts["nonterminal_transfer_count"] == 3
        assert counts["unknown_transfer_count"] == 2
    with world(tmp_path / "fewer", UNKNOWN) as (store, _, _):
        assert upload_snapshot(store.connection, Deadline())["upload_plan_count"] == 2
        assert fingerprint(store) != "0" * 64


# --- the shared expiry of the store ---------------------------------------------------------------


def test_the_next_expiry_of_the_store_sees_every_expiring_row_of_a_continuation(tmp_path):
    early, floor = "2026-11-02T10:00:00.000000Z", "2026-11-02T09:00:00.000000Z"
    with world(tmp_path, live()) as (store, _, (item,)):
        connection = store.connection
        # As stored, the continuation's lease is the first date left (the root has none).
        assert next_expiry(connection, floor) == instant(item.record["lease"]["expires_at"])
        rows = (
            ("upload_plans", "expires_at", "plan_id", item.plan["plan_id"]),
            ("upload_approvals", "expires_at", "plan_id", item.plan["plan_id"]),
            ("upload_operations", "lease_expires_at", "operation_id", item.record["operation_id"]),
        )
        for table, column, key, value in rows:
            old = connection.execute(
                f"SELECT {column} FROM {table} WHERE {key}=?", (value,)
            ).fetchone()[0]
            connection.execute(f"UPDATE {table} SET {column}=? WHERE {key}=?", (early, value))
            try:
                assert next_expiry(connection, floor) == instant(early), table
            finally:
                connection.execute(f"UPDATE {table} SET {column}=? WHERE {key}=?", (old, value))
        # Past the last date of every row there is nothing left to wait for.
        assert next_expiry(connection, "2026-11-02T11:15:00.000000Z") is None


# --- reading a continuation back ------------------------------------------------------------------


def test_the_repository_shows_and_lists_a_continuation_next_to_its_root(tmp_path):
    with world(tmp_path, live()) as (store, root, (item,)):
        uploads = StateUploads(store)
        shown = uploads.show(plan_id=item.plan["plan_id"])
        assert type(shown.plan) is DatasetContinuationPlanV3
        assert type(shown.approval) is DatasetUploadApprovalV3
        assert (
            uploads.show(operation_id=item.record["operation_id"]).plan.plan_id
            == shown.plan.plan_id
        )
        entries, cursor = uploads.list()
        by_plan = {entry.plan_id: entry for entry in entries}
        assert cursor is None and set(by_plan) == {root["plan"]["plan_id"], item.plan["plan_id"]}
        listed = by_plan[item.plan["plan_id"]]
        assert (listed.operation_id, listed.operation_status) == (
            item.record["operation_id"],
            "running",
        )
        assert (listed.digest, listed.status) == (
            item.plan["digest"],
            item.plan["status"],
        )


def test_the_public_results_name_no_continuation_yet_so_they_fail_closed(tmp_path):
    root_dir = tmp_path / "state"
    with open_store(root_dir, timeout=60) as store:
        root = install_root(store)
        item = build(root, 1, status="running")
        install(store, item)
    plan_id, operation_id = item.plan["plan_id"], item.record["operation_id"]
    calls = (
        lambda: api.show_dataset_upload(plan_id=plan_id, state_dir=root_dir),
        lambda: api.show_dataset_upload(operation_id=operation_id, state_dir=root_dir),
        lambda: api.review_dataset_upload(plan_id, state_dir=root_dir),
        lambda: api.list_dataset_uploads(state_dir=root_dir),
        lambda: api.revoke_dataset_upload(plan_id, state_dir=root_dir),
    )
    for call in calls:
        assert code_of(call) == "state_invalid"
    # The refusal is a read: nothing about the stored continuation moved.
    with open_store(root_dir, timeout=60) as store:
        assert read_any_view(store.connection, plan_id).operation.status == "running"
        validate_uploads(store.connection)


def test_a_reader_of_two_families_refuses_every_row_of_a_continuation_and_rewrites_none(tmp_path):
    from yorunge.adapters.upload_store import decode_versioned
    from yorunge.domain.dataset_transfer import (
        TransferControl,
        TransferRecord,
        TransferVerification,
    )
    from yorunge.domain.dataset_transfer_v2 import (
        TransferControlV2,
        TransferRecordV2,
        TransferVerificationV2,
    )
    from yorunge.domain.dataset_upload import DatasetUploadApproval, DatasetUploadPlan
    from yorunge.domain.dataset_upload_v2 import DatasetUploadApprovalV2, DatasetUploadPlanV2

    tables = ("upload_plans", "upload_approvals", "upload_operations", "upload_controls")
    tables += ("upload_verifications", "upload_stage_intents", "upload_stage_receipts")
    with world(tmp_path, {"status": "succeeded"}) as (store, _, (item,)):
        connection = store.connection
        plan_id, operation_id = item.plan["plan_id"], item.record["operation_id"]
        rows = {
            "plan": ("SELECT payload FROM upload_plans WHERE plan_id=?", plan_id),
            "approval": ("SELECT payload FROM upload_approvals WHERE plan_id=?", plan_id),
            "record": ("SELECT payload FROM upload_operations WHERE operation_id=?", operation_id),
            "control": ("SELECT payload FROM upload_controls WHERE operation_id=?", operation_id),
            "proof": (
                "SELECT payload FROM upload_verifications WHERE operation_id=?",
                operation_id,
            ),
        }
        readers = {
            "plan": (DatasetUploadPlan, DatasetUploadPlanV2),
            "approval": (DatasetUploadApproval, DatasetUploadApprovalV2),
            "record": (TransferRecord, TransferRecordV2),
            "control": (TransferControl, TransferControlV2),
            "proof": (TransferVerification, TransferVerificationV2),
        }

        def snapshot():
            return [connection.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in tables]

        before = snapshot()
        for name, (query, key) in rows.items():
            payload = connection.execute(query, (key,)).fetchone()[0]
            call = partial(decode_versioned, *readers[name], payload)
            assert code_of(call) == "state_invalid", name
        assert snapshot() == before  # a refusal is a read: nothing is rewritten or downgraded


# --- the user view of a continuation --------------------------------------------------------------


def expected_summary(item):
    plan, record, approval = item.plan, item.record, item.approval
    binding = plan["continuation"]
    succeeded = record is not None and record["status"] == "succeeded"
    return {
        "schema_version": 3,
        "kind": "dataset_upload_summary",
        "source_plan_schema": 3,
        "legacy_history_only": False,
        "plan_id": plan["plan_id"],
        "plan_digest": plan["digest"],
        "plan_status": plan["status"],
        "admission_policy": plan["admission_policy"],
        "cost_policy": plan["cost_policy"],
        "risks": plan["risks"],
        "blockers": plan["blockers"],
        "approval_status": approval["status"],
        "approval_expires_at": approval["expires_at"],
        "operation_id": record["operation_id"] if record else None,
        "operation_status": record["status"] if record else None,
        "dataset_id": DATASET_ID,
        "verification_level": "metadata" if succeeded else "none",
        "remote_bytes_verified": False,
        "authority_verified": False,  # the stored plans carry no grant to have verified
        "cost_bound": None,
        "budget_micros": plan["budget_micros"],
        "cost_scope": "continuation_start_invocation",
        "continuation_of": binding["source_operation_id"],
        "continuation_files": len(binding["file_indices"]),
        "remote_present_files": len(FILES) - len(binding["file_indices"]),
        "uncertain_files": len(binding["uncertain_indices"]),
    }


@pytest.mark.parametrize("shape", SHAPES.values(), ids=SHAPES)
def test_a_continuation_is_summarized_as_itself_whatever_its_state(tmp_path, shape):
    with world(tmp_path, shape) as (store, root, (item,)):
        found = summary(read_any_view(store.connection, item.plan["plan_id"]))
        assert type(found) is DatasetUploadSummaryV3
        assert json.loads(found.encoded()) == expected_summary(item)
        assert found.continuation_of == root["record"]["operation_id"]


def test_a_continuation_of_a_continuation_names_the_operation_it_continues(tmp_path):
    with world(tmp_path, UNKNOWN, LATER) as (store, _, (first, second)):
        found = summary(read_any_view(store.connection, second.plan["plan_id"]))
        assert found.continuation_of == FIRST and found.operation_id == SECOND
        assert json.loads(found.encoded()) == expected_summary(second)
        assert summary(read_any_view(store.connection, first.plan["plan_id"])).uncertain_files == 1


def test_a_plan_that_was_never_admitted_is_summarized_without_an_operation(tmp_path):
    with world(tmp_path, {"status": "admitted", "plan_only": True}) as (store, _, (item,)):
        found = summary(read_any_view(store.connection, item.plan["plan_id"]))
        assert (found.operation_id, found.operation_status) == (None, None)
        assert found.dataset_id == DATASET_ID  # the plan names the dataset, whatever happens
        assert json.loads(found.encoded()) == expected_summary(item)


def test_the_summary_golden_is_what_the_stored_fixtures_project_to():
    plan = DatasetContinuationPlanV3.model_validate_json(
        (FIXTURES / "dataset-continuation-plan-v3.json").read_bytes()
    )
    approval = DatasetUploadApprovalV3.model_validate_json(
        (FIXTURES / "dataset-continuation-approval-v3.json").read_bytes()
    )
    record = TransferRecordV3.model_validate_json(
        (FIXTURES / "dataset-continuation-record-v3-running.json").read_bytes()
    )
    golden = raw("dataset-continuation-summary-v3.json")
    found = summary(VersionedTransferView(plan, approval, record))
    assert json.loads(found.encoded()) == golden


def test_evidence_the_plan_holds_shows_in_the_summary_once_the_upload_has_finished():
    plan = DatasetContinuationPlanV3.model_validate_json(
        (FIXTURES / "dataset-continuation-plan-v3-evidenced.json").read_bytes()
    )
    approval = DatasetUploadApprovalV3.model_validate_json(
        (FIXTURES / "dataset-continuation-approval-v3-evidenced.json").read_bytes()
    )
    record = TransferRecordV3.model_validate_json(
        (FIXTURES / "dataset-continuation-record-v3-verification-only-succeeded.json").read_bytes()
    )
    document = raw("dataset-continuation-plan-v3-evidenced.json")
    bound = document["cost_bound"]
    waiting = summary(VersionedTransferView(plan, approval, None))
    done = summary(VersionedTransferView(plan, approval, record))
    assert (waiting.authority_verified, waiting.verification_level) == (False, "none")
    assert (done.authority_verified, done.verification_level) == (True, "metadata")
    assert done.operation_status == "succeeded" and done.cost_policy == "bounded_required"
    assert done.budget_micros == document["budget_micros"]
    assert (done.risks, done.blockers) == ((), ())
    # The cost evidence is projected field for field, with no extra and no payload.
    cost = done.cost_bound
    assert cost is not None
    for name in (
        "work_digest",
        "maximum_micros",
        "post_period_storage",
        "source_id",
        "source_version",
    ):
        assert getattr(cost, name) == bound[name], name
    assert cost.charge_categories == tuple(bound["charge_categories"])
    assert (cost.checked_at, cost.expires_at) == (bound["checked_at"], bound["expires_at"])
    assert (cost.charge_period_start, cost.charge_period_end) == (
        bound["charge_period_start"],
        bound["charge_period_end"],
    )
    assert waiting.cost_bound == cost


def test_the_summary_of_a_continuation_names_no_path_baseline_or_provider_payload(tmp_path):
    with world(tmp_path, UNKNOWN) as (store, root, (item,)):
        text = summary(read_any_view(store.connection, item.plan["plan_id"])).encoded().decode()
        for secret in (
            root["plan"]["root"]["anchor"],
            *(file["path"] for file in FILES),
            "object_key",
            "created_dataset",
            "baseline",
            "write_access",
            "credential",
        ):
            assert secret not in text, secret


def test_the_original_projections_refuse_a_continuation_instead_of_calling_it_legacy(tmp_path):
    with world(tmp_path, live()) as (store, _, (item,)):
        view = read_any_view(store.connection, item.plan["plan_id"])
        assert code_of(lambda: original_summary(view)) == "state_invalid"
        # The review type carries a v2 summary and v2 request limits; the continuation's own is
        # the user surface's (P02-3i), so it stays closed here and never falls back to "legacy".
        assert code_of(lambda: review(view)) == "state_invalid"
