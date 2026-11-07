"""A continuation is read only with the lineage it was prepared from, and its graph is validated.

Every history here is a real root upload (with its strict create receipt) and continuations built
by plain hashlib/json in ``tests/fixtures/continuation_history.py``, stored as SQLite rows and read
back through the store. A negative test breaks exactly one thing in an otherwise valid history.
"""

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from tests.fixtures.continuation_history import (
    BASE_PLAN,
    CREATE_RECEIPT,
    DATASET_ID,
    FILES,
    FIRST,
    INTENT_SHAPE,
    MANIFEST,
    OTHER,
    SECOND,
    SHAPES,
    UNKNOWN,
    build,
    canon,
    install,
    install_root,
    sha,
    uuid,
    world,
)
from tests.fixtures.continuation_history import stamp as builder_stamp
from tests.fixtures.upload_history import install_legacy_running
from yorunge.adapters.capability_cache import Stamp
from yorunge.adapters.local_files import Deadline
from yorunge.adapters.state import DB_NAME, open_store
from yorunge.adapters.upload_chain import operation_journal
from yorunge.adapters.upload_maintenance import upload_snapshot
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import (
    created_dataset,
    legacy_create_without_baseline,
    read_any_view,
    read_plan,
    read_view_and_lineage,
)
from yorunge.domain.create_receipt import CreateReceiptV2
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3, DatasetUploadApprovalV3
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_transfer_v3 import TransferControlV3, TransferVerificationV3
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_resume import merge_chain


def read(store, item):
    return read_any_view(store.connection, item.plan["plan_id"])


def refused(store, item):
    with pytest.raises(YorungeError) as error:
        read(store, item)
    assert error.value.code == "state_invalid"


# --- the lineage: valid shapes -----------------------------------------------------------------


@pytest.mark.parametrize("shape", SHAPES.values(), ids=SHAPES)
def test_every_shape_of_a_continuation_reads_back_with_its_root(tmp_path, shape):
    with world(tmp_path, shape) as (store, root, (item,)):
        view, lineage = read_view_and_lineage(store.connection, item.plan["plan_id"])
        assert view.operation.status == item.record["status"]
        assert [s.operation.operation_id for s in lineage.sources] == [
            root["record"]["operation_id"]
        ]
        assert lineage.baseline.id == DATASET_ID


def test_a_prepared_continuation_with_no_operation_yet_reads_back_with_its_root(tmp_path):
    with world(tmp_path, {"status": "admitted", "plan_only": True}) as (store, root, (item,)):
        view, lineage = read_view_and_lineage(store.connection, item.plan["plan_id"])
        assert view.operation is None and view.approval is not None
        assert lineage.sources[0].operation.operation_id == root["record"]["operation_id"]


def test_a_continuation_of_a_continuation_reads_back_with_both_sources_root_first(tmp_path):
    second = {
        "status": "running",
        "source": FIRST,
        "indices": (2,),
        "uncertain": (),
        "intents": 2,
        "acknowledged": 2,
    }
    with world(tmp_path, UNKNOWN, second) as (store, root, (first, later)):
        view, lineage = read_view_and_lineage(store.connection, later.plan["plan_id"])
        assert view.operation.operation_id == SECOND
        assert [s.operation.operation_id for s in lineage.sources] == [
            root["record"]["operation_id"],
            FIRST,
        ]
        assert len(read_view_and_lineage(store.connection, first.plan["plan_id"])[1].sources) == 1


def test_a_cancelled_continuation_beside_a_live_one_changes_nothing_about_either(tmp_path):
    with world(tmp_path, {"status": "cancelled"}, {"status": "running"}) as (store, _, (a, b)):
        assert read(store, a).operation.status == "cancelled"
        assert read(store, b).operation.status == "running"


# --- the lineage: corrupt histories, one fault at a time ---------------------------------------


@pytest.mark.parametrize("shape", ["admitted", "cancelled", "check-only succeeded"])
def test_a_source_that_never_sent_anything_cannot_be_continued(tmp_path, shape):
    follow = {"status": "running", "source": FIRST, "indices": (2,), "uncertain": ()}
    with world(tmp_path / "bad", SHAPES[shape], follow) as (store, _, (source, later)):
        assert read(store, source).operation.status == SHAPES[shape]["status"]
        refused(store, later)
    # The control: the same chain over a source that did send something reads back.
    with world(tmp_path / "ok", UNKNOWN, follow) as (store, _, (_, later)):
        assert read(store, later).operation.status == "running"


BROKEN = {
    "source is not an operation": {"source": uuid(0xDEAD)},
    "baseline digest differs": {"binding": {"baseline_digest": "e" * 64}},
    "baseline operation is not the root": {"binding": {"baseline_operation_id": uuid(0xBAD)}},
}


@pytest.mark.parametrize("fault", BROKEN.values(), ids=BROKEN)
def test_a_continuation_that_does_not_lead_to_its_baseline_is_a_corrupt_history(tmp_path, fault):
    with world(tmp_path / "running", {"status": "running", **fault}) as (store, _, (item,)):
        refused(store, item)
    # A plan alone is already unbound: reading it, not only its operation, is refused.
    spec = {"status": "admitted", "plan_only": True, **fault}
    with world(tmp_path / "plan", spec) as (store, _, (item,)):
        refused(store, item)


def test_a_continuation_of_a_dataset_the_root_did_not_make_is_a_corrupt_history(tmp_path):
    def agree_with_the_plan(item):
        item.record["dataset_id"] = OTHER  # the record agrees with its plan; the root does not

    spec = {"status": "running", "binding": {"dataset_id": OTHER}, "tweak": agree_with_the_plan}
    with world(tmp_path, spec) as (store, _, (item,)):
        refused(store, item)


def test_a_lineage_that_loops_is_a_corrupt_history(tmp_path):
    first = {"status": "running", "source": SECOND}
    second = {"status": "running", "source": FIRST, "indices": (2,), "uncertain": ()}
    with world(tmp_path, first, second) as (store, _, (a, b)):
        refused(store, a)
        refused(store, b)


def test_a_continuation_cannot_be_its_own_source(tmp_path):
    with world(tmp_path, {"status": "running", "source": FIRST}) as (store, _, (item,)):
        refused(store, item)


def test_a_source_that_is_only_a_plan_is_not_a_source(tmp_path):
    later = {"status": "running", "source": FIRST, "indices": (2,), "uncertain": ()}
    with world(tmp_path, {**UNKNOWN, "plan_only": True}, later) as (store, _, (_, item)):
        refused(store, item)


def test_a_continuation_whose_root_rows_are_gone_is_a_corrupt_history(tmp_path):
    with open_store(tmp_path / "state", timeout=60) as store:
        root = install_root(store)
        item = build(root, 1, status="running")
        store.connection.execute("PRAGMA foreign_keys=OFF")  # the root is deleted below
        for table in (
            "upload_controls",
            "upload_stage_receipts",
            "upload_stage_intents",
            "upload_verifications",
            "upload_operations",
            "upload_approvals",
            "upload_plans",
        ):
            store.connection.execute(f"DELETE FROM {table}")
        store.connection.execute("UPDATE upload_namespaces SET create_operation_id=NULL")
        install(store, item)
        refused(store, item)


def test_the_namespace_of_a_continuation_is_its_roots_whatever_its_own_state(tmp_path):
    for number, shape in enumerate(({"status": "admitted"}, {"status": "running"})):
        with world(tmp_path / str(number), shape) as (store, root, (item,)):
            assert read(store, item).plan.plan_id == item.plan["plan_id"]
            # Its own operation holding the namespace instead of the root is a corrupt history.
            own = item.record["operation_id"]
            store.connection.execute("UPDATE upload_namespaces SET create_operation_id=?", (own,))
            refused(store, item)


def test_the_namespace_of_a_continuations_continuation_is_still_the_roots(tmp_path):
    later = {"status": "running", "source": FIRST, "indices": (2,), "uncertain": ()}
    with world(tmp_path, UNKNOWN, later) as (store, _, (_, item)):
        assert read(store, item).operation.operation_id == SECOND
        store.connection.execute("PRAGMA foreign_keys=OFF")
        for owner in (FIRST, SECOND):  # its source, and itself
            store.connection.execute("UPDATE upload_namespaces SET create_operation_id=?", (owner,))
            refused(store, item)


# --- the graph of a continuation: one fault at a time ------------------------------------------


def sent(**changes):
    return {"status": "running", "intents": 1, "acknowledged": 1, **changes}


def extra_intent(item, **changes):
    return {
        **item.intents[0],
        "intent_id": uuid(0x9001),
        "sequence": len(item.intents) + 1,
        **changes,
    }


def request_without_the_dataset(item):
    """What the intent's digest would be if the dataset were left out (the unfixed request)."""
    first = item.intents[0]
    return sha(
        {
            "plan_digest": item.plan["digest"],
            "kind": first["kind"],
            "file_index": first["file_index"],
            "file": FILES[first["file_index"]],
            "dataset_id": None,
            "object_key": None,
        }
    )


def check_only_intent(item):
    item.intents.append(
        {
            **INTENT_SHAPE,
            "intent_id": uuid(0x9002),
            "operation_id": item.record["operation_id"],
            "sequence": 1,
            "kind": "presign",
            "file_index": 0,
        }
    )


GRAPH_FAULTS = {
    "a create intent": (
        sent(),
        lambda c: c.intents.append(extra_intent(c, kind="create", file_index=None)),
    ),
    "a link intent": (
        sent(),
        lambda c: c.intents.append(extra_intent(c, kind="project_link", file_index=None)),
    ),
    "a file outside the selection": (
        sent(),
        lambda c: c.intents.append(extra_intent(c, kind="presign", file_index=0)),
    ),
    "more intents than the graph has": (
        {"status": "unknown", "intents": 6, "acknowledged": 5},
        lambda c: c.intents.append(extra_intent(c, kind="create", file_index=None)),
    ),
    "a request whose digest leaves the plan's dataset out": (
        sent(),
        lambda c: c.intents[0].update(request_digest=request_without_the_dataset(c)),
    ),
    "a receipt naming another dataset": (
        sent(intents=2, acknowledged=2),
        lambda c: c.receipts[1].update(dataset_id=OTHER),
    ),
    "an intent but no latch": (
        {"status": "admitted", "intents": 1, "acknowledged": 1},
        lambda c: c.record.update(workflow_latched=False),
        sent(),  # the admitted record is only valid once its latch is off; the control is running
    ),
    "a latch but no intent": (
        {"status": "unknown", "intents": 0},
        lambda c: c.record.update(workflow_latched=True),
        UNKNOWN,
    ),
    "a check-only continuation with an intent": (
        {"status": "admitted", "indices": ()},
        check_only_intent,
    ),
    "success without a proof": ({"status": "succeeded"}, lambda c: setattr(c, "proof", None)),
    "an unknown record with no recovery marker": (UNKNOWN, lambda c: c.controls.clear()),
    "a terminal control of another proof": (
        {"status": "succeeded"},
        lambda c: c.controls[0].update(verification_digest="f" * 64),
    ),
    "a control of another version": (
        UNKNOWN,
        lambda c: c.controls[0].update(
            schema_version=2
        ),  # v2's fields are v3's: only the tag differs
    ),
}


@pytest.mark.parametrize("fault", GRAPH_FAULTS.values(), ids=GRAPH_FAULTS)
def test_a_continuation_graph_with_one_fault_is_a_corrupt_history(tmp_path, fault):
    shape, tweak, *control = fault
    with world(tmp_path / "bad", {**shape, "tweak": tweak}) as (store, _, (item,)):
        refused(store, item)
    healthy = control[0] if control else shape  # the control: a valid history without the fault
    with world(tmp_path / "ok", healthy) as (store, _, (item,)):
        assert read(store, item).operation.status == healthy["status"]


def with_new_digest(fault):
    def tweak(item):
        fault(item)
        item.controls[0]["verification_digest"] = sha(
            item.proof
        )  # the control agrees; the proof not

    return tweak


PROOF_FAULTS = {
    "a proof that differs from the manifest": lambda c: c.proof["files"][1].update(
        sha256="00" * 32
    ),
    "a proof of another dataset": lambda c: c.proof.update(dataset_id=OTHER),
    "a proof of another version": lambda c: c.proof.update(schema_version=2),
    "a proof from another clock generation": lambda c: c.proof["scope"].update(clock_generation=2),
    "a proof with a file missing": lambda c: c.proof["files"].pop(),
    "a proof of another project": lambda c: c.proof.update(project_id=OTHER),
}


@pytest.mark.parametrize("fault", PROOF_FAULTS.values(), ids=PROOF_FAULTS)
def test_a_proof_that_is_not_this_continuations_is_a_corrupt_history(tmp_path, fault):
    spec = {"status": "succeeded", "tweak": with_new_digest(fault)}
    with world(tmp_path, spec) as (store, _, (item,)):
        refused(store, item)


def test_the_store_asks_the_continuations_own_rule_about_its_proof(tmp_path, monkeypatch):
    # Its checks overlap with the store's other ones (dataset, project, scope, file count); the
    # policy rule does not, and a verified-only plan cannot be built here: the call is observed.
    asked = []

    def refuse(plan, proof):
        asked.append((plan.plan_id, proof.dataset_id))
        raise ValueError("this proof is not this continuation's")

    with world(tmp_path, {"status": "succeeded"}) as (store, _, (item,)):
        assert read(store, item).verification is not None and asked == []
        monkeypatch.setattr(
            "yorunge.adapters.upload_store.validate_verification_binding_v3", refuse
        )
        refused(store, item)
        assert asked == [(item.plan["plan_id"], DATASET_ID)]


def test_a_proof_with_every_manifest_file_and_the_plans_dataset_is_accepted(tmp_path):
    with world(tmp_path, {"status": "succeeded"}) as (store, _, (item,)):
        view = read(store, item)
        assert len(view.verification.files) == len(MANIFEST["files"])
        assert view.verification.dataset_id == DATASET_ID


# --- the baseline and the journal facts --------------------------------------------------------


def test_the_baseline_of_a_continuation_is_the_roots_created_dataset_not_a_receipts(tmp_path):
    created = CreateReceiptV2.model_validate_json(CREATE_RECEIPT).created_dataset
    with world(tmp_path, UNKNOWN) as (store, root, (item,)):
        uploads = StateUploads(store)
        assert uploads.require_created_baseline(item.record["operation_id"]) == created
        assert uploads.require_created_baseline(root["record"]["operation_id"]) == created
        view = read(store, item)
        # The helper that reads one operation's own receipt refuses to answer for a continuation.
        with pytest.raises(ValueError):
            created_dataset(view)
        assert legacy_create_without_baseline(view) is False


def stamp(store, root, *, now):
    meta = root["plan"]["scope"]
    return Stamp(meta["store_id"], meta["identity_epoch"], 1, now, False)


def test_the_journals_of_a_chain_run_from_the_root_to_the_source(tmp_path):
    later = {
        "status": "running",
        "source": FIRST,
        "indices": (2,),
        "uncertain": (),
        "intents": 2,
        "acknowledged": 2,
    }
    with world(tmp_path, UNKNOWN, later) as (store, root, (first, _)):
        uploads = StateUploads(store)
        at = stamp(store, root, now=datetime(2026, 11, 2, 11, 1, tzinfo=UTC))
        snapshot = uploads.chain_snapshot(FIRST, at)
        root_operation = root["record"]["operation_id"]
        assert [j.operation_id for j in snapshot.journals] == [root_operation, FIRST]
        assert [j.parent_operation_id for j in snapshot.journals] == [None, root_operation]
        assert {j.dataset_id for j in snapshot.journals} == {DATASET_ID}
        assert {j.manifest_digest for j in snapshot.journals} == {MANIFEST["digest"]}
        # The combined lineage is what merge_chain takes: the root confirmed the first file, the
        # first continuation the second, and nothing has reached the third.
        manifest = DatasetManifest.model_validate_json(canon_manifest())
        assert merge_chain(snapshot.journals, manifest).states == ("accepted", "accepted", "none")
        assert snapshot.source.status == "unknown" and snapshot.source.lease_active is False
        assert snapshot.source.policy == "explicit_attempt" and snapshot.source.has_created_dataset
        # Its one descendant is the running continuation, whose lease is still live at this stamp.
        assert [(d.operation_id, d.status, d.lease_active) for d in snapshot.descendants] == [
            (SECOND, "running", True)
        ]
        late = stamp(store, root, now=datetime(2026, 11, 2, 11, 5, tzinfo=UTC))
        assert uploads.chain_snapshot(FIRST, late).descendants[0].lease_active is False
        # A lease of another clock generation or identity epoch is not active, whatever its expiry.
        scope = root["plan"]["scope"]
        for other in (
            Stamp(scope["store_id"], scope["identity_epoch"], 2, at.now, False),
            Stamp(scope["store_id"], OTHER, 1, at.now, False),
        ):
            assert uploads.chain_snapshot(FIRST, other).descendants[0].lease_active is False
        assert uploads.chain_snapshot(root_operation, at).descendants[0].operation_id == FIRST
        assert uploads.chain_snapshot(SECOND, at).descendants == ()
        # A root has itself as its only journal and no parent.
        only = uploads.chain_snapshot(root_operation, at)
        assert [j.parent_operation_id for j in only.journals] == [None]
        assert first.record["operation_id"] == FIRST


def canon_manifest():
    import json

    return json.dumps(MANIFEST, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def test_an_operation_that_sent_nothing_is_not_a_complete_graph(tmp_path):
    # A graph with no stages is vacuously acknowledged; that must not read as "reconcile it".
    for name in ("check-only admitted", "check-only cancelled", "admitted"):
        with world(tmp_path / name, SHAPES[name]) as (store, _, (item,)):
            assert operation_journal(read(store, item)).graph_complete is False
    with world(tmp_path / "done", {"status": "succeeded"}) as (store, _, (item,)):
        assert operation_journal(read(store, item)).graph_complete is True
    with world(tmp_path / "partial", SHAPES["running, a stage in flight"]) as (store, _, (item,)):
        assert operation_journal(read(store, item)).graph_complete is False


def test_the_facts_of_a_chain_are_read_in_one_snapshot_no_writer_can_slip_into(
    tmp_path, monkeypatch
):
    later = {"status": "running", "source": FIRST, "indices": (2,), "uncertain": ()}
    with world(tmp_path, UNKNOWN, later) as (store, root, _):
        uploads = StateUploads(store)
        other = sqlite3.connect(store.root / DB_NAME, timeout=0)
        refusals = set()

        def try_to_add_a_descendant(phase):
            # It may start writing, but its commit needs the lock the reader's snapshot holds.
            other.execute("BEGIN IMMEDIATE")
            try:
                other.execute("UPDATE upload_namespaces SET payload=payload")
                other.execute("COMMIT")
            except sqlite3.OperationalError as error:
                assert "locked" in str(error)
                refusals.add(phase)
            finally:
                if other.in_transaction:
                    other.execute("ROLLBACK")

        def spy(real, phase):
            def watched(*args):
                try_to_add_a_descendant(phase)
                return real(*args)

            return watched

        monkeypatch.setattr(
            "yorunge.adapters.upload_chain.operation_journal",
            spy(operation_journal, "journals"),
        )
        monkeypatch.setattr(
            "yorunge.adapters.upload_chain.read_plan", spy(read_plan, "descendants")
        )
        try:
            at = stamp(store, root, now=datetime(2026, 11, 2, 11, 1, tzinfo=UTC))
            uploads.chain_snapshot(FIRST, at)
        finally:
            other.close()
        assert refusals == {"journals", "descendants"}


def test_a_missing_operation_is_not_found_and_a_broken_lineage_is_invalid(tmp_path):
    with world(tmp_path, {"status": "running", "source": uuid(0xDEAD)}) as (store, root, (item,)):
        uploads = StateUploads(store)
        at = stamp(store, root, now=datetime(2026, 11, 2, 11, 1, tzinfo=UTC))
        with pytest.raises(YorungeError) as missing:
            uploads.chain_snapshot(uuid(0xABC), at)
        assert missing.value.code == "operation_not_found"
        with pytest.raises(YorungeError) as broken:
            uploads.chain_snapshot(item.record["operation_id"], at)
        assert broken.value.code == "state_invalid"


# --- what a stored continuation brings with it -------------------------------------------------


def test_a_succeeded_continuation_reads_back_with_its_own_control_and_proof_families(tmp_path):
    with world(tmp_path, {"status": "succeeded"}) as (store, _, (item,)):
        view = read(store, item)
        assert [type(c) for c in view.controls] == [TransferControlV3]
        assert type(view.verification) is TransferVerificationV3
        # A control stored under another kind than its payload names is a disagreeing row.
        store.connection.execute("UPDATE upload_controls SET kind='recovery'")
        refused(store, item)


def test_the_repository_reads_a_continuation_as_itself_and_will_not_revoke_it_as_a_v2(tmp_path):
    with world(tmp_path, {"status": "admitted", "plan_only": True}) as (store, _, (item,)):
        uploads = StateUploads(store)
        view = uploads.show(plan_id=item.plan["plan_id"])
        assert type(view.plan) is DatasetContinuationPlanV3
        assert type(view.approval) is DatasetUploadApprovalV3
        assert item.plan["plan_id"] in [entry.plan_id for entry in uploads.list()[0]]
        # Revoking re-decodes the approval as v1/v2 until P02-3r gives the continuation its own.
        approval = store.connection.execute(
            "SELECT payload FROM upload_approvals WHERE plan_id=?", (item.plan["plan_id"],)
        ).fetchone()
        with pytest.raises(YorungeError) as error:
            uploads.revoke(item.plan["plan_id"], item.plan["digest"])
        assert error.value.code == "state_invalid"
        assert (
            store.connection.execute(
                "SELECT payload FROM upload_approvals WHERE plan_id=?", (item.plan["plan_id"],)
            ).fetchone()
            == approval
        )


def test_the_snapshot_a_reset_is_previewed_from_reads_every_plan_with_its_lineage(tmp_path):
    from yorunge.adapters.local_files import Deadline
    from yorunge.adapters.upload_maintenance import upload_snapshot

    later = {"status": "running", "source": FIRST, "indices": (2,), "uncertain": ()}
    with world(tmp_path, UNKNOWN, later) as (store, _, _):
        counts = upload_snapshot(store.connection, Deadline())
        assert counts["upload_plan_count"] == 3  # the root and the two continuations
        assert counts["transfer_operation_count"] == 3
        assert counts["unknown_transfer_count"] == 2  # the root and the first continuation
        assert counts["nonterminal_transfer_count"] == 3
    with world(tmp_path / "broken", {"status": "running", "source": uuid(0xDEAD)}) as (store, _, _):
        with pytest.raises(YorungeError) as error:
            upload_snapshot(store.connection, Deadline())
        assert error.value.code == "state_invalid"


# --- what a plan copies from its source, and what its lineage allows it to send ----------------

COPIES = {
    "other parameters": {"parameters": {**BASE_PLAN["parameters"], "modality": "AUDIO"}},
    "another root folder": {"root": {**BASE_PLAN["root"], "anchor": "/elsewhere"}},
}


@pytest.mark.parametrize("change", COPIES.values(), ids=COPIES)
def test_a_plan_that_differs_from_its_source_in_what_it_copies_is_a_corrupt_history(
    tmp_path, change
):
    with world(tmp_path / "bad", {"status": "running", "plan_changes": change}) as (store, _, (a,)):
        refused(store, a)
    with world(tmp_path / "ok", {"status": "running"}) as (store, _, (a,)):  # the control
        assert read(store, a).operation.status == "running"


SELECTIONS = {
    "a file the root already confirmed": {"indices": (0, 2), "uncertain": ()},
    "an unanswered confirm that is not marked": {"indices": (1, 2), "uncertain": ()},
    "a clean file that is marked uncertain": {"indices": (1, 2), "uncertain": (1, 2)},
}


@pytest.mark.parametrize("selection", SELECTIONS.values(), ids=SELECTIONS)
def test_a_selection_its_lineage_does_not_allow_is_a_corrupt_history(tmp_path, selection):
    with world(tmp_path / "bad", {"status": "running", **selection}) as (store, _, (a,)):
        refused(store, a)
    with world(tmp_path / "ok", {"status": "running"}) as (store, _, (a,)):
        assert read(store, a).operation.status == "running"


def test_a_continuation_of_a_lineage_with_a_known_rejection_is_a_corrupt_history(tmp_path):
    with open_store(tmp_path / "state", timeout=60) as store:
        root = install_root(store)
        item = build(root, 1, status="running")
        install(store, item)
        assert read(store, item).operation.status == "running"  # the control
        confirm = root["receipts"][4]  # the first file's confirm, answered with a rejection
        rejected = {**confirm, "result": "rejected", "object_key": None, "dataset_id": None}
        store.connection.execute(
            "UPDATE upload_stage_receipts SET payload=? WHERE intent_id=?",
            (canon(rejected).decode(), confirm["intent_id"]),
        )
        refused(store, item)


def test_a_source_whose_graph_is_already_complete_is_reconciled_not_continued(tmp_path):
    check_only = {"status": "admitted", "indices": ()}
    with open_store(tmp_path / "bad", timeout=60) as store:
        root = install_root(store, partial=False)
        item = build(root, 1, **check_only)
        install(store, item)
        refused(store, item)
    with world(tmp_path / "ok", check_only) as (store, _, (item,)):  # a partial root: the control
        assert read(store, item).operation.status == "admitted"


def test_a_root_that_made_no_dataset_it_can_prove_is_no_baseline(tmp_path):
    with open_store(tmp_path / "state", timeout=60) as store:
        root = install_root(store, strict=False)  # its create left only the plain receipt
        item = build(root, 1, status="running")
        install(store, item)
        refused(store, item)


def test_a_proof_read_after_an_identity_reset_needs_the_recovery_that_followed_it(tmp_path):
    reset = {"status": "succeeded", "reset": True}
    with world(tmp_path / "ok", reset) as (store, _, (item,)):
        assert read(store, item).operation.status == "succeeded"
        assert {c.kind for c in read(store, item).controls} == {"terminal", "recovery"}
    with world(tmp_path / "none", {**reset, "tweak": lambda c: c.controls.pop()}) as (
        store,
        _,
        (item,),
    ):
        refused(store, item)
    with world(
        tmp_path / "late",
        {**reset, "tweak": lambda c: c.controls[1].update(observed_at=builder_stamp(100))},
    ) as (
        store,
        _,
        (item,),
    ):
        refused(store, item)


def test_reading_every_plan_of_a_long_lineage_reads_each_operation_once(tmp_path, monkeypatch):
    import yorunge.adapters.upload_store as store_module

    count = 30
    specs = [
        {
            "status": "unknown",
            "indices": (2,),
            "uncertain": () if number == 1 else (2,),
            "intents": 3,
            "acknowledged": 2,
            **({"source": uuid(0x300 + number - 1)} if number > 1 else {}),
        }
        for number in range(1, count + 1)
    ]
    # Building thirty histories takes longer than the store's usual budget for one operation.
    with world(tmp_path, *specs, timeout=120) as (store, _, built):
        assert len(built) == count
        calls = []
        real = store_module._read_view
        monkeypatch.setattr(
            store_module, "_read_view", lambda *args: (calls.append(args[1]), real(*args))[1]
        )
        assert upload_snapshot(store.connection, Deadline())["upload_plan_count"] == count + 1
        # The plans come in plan-id order, a source before its continuation, so each operation's
        # view is read once as itself and never again as a source; unshared it is about n²/2.
        assert len(calls) == count + 1
        calls.clear()
        entries, _ = StateUploads(store).list(limit=100)
        assert len(entries) == count + 1 and len(calls) <= count + 2


# --- the facts of a chain, in the places a mutant could hide ------------------------------------


def test_the_facts_of_a_deeper_chain_name_each_operations_own_status_parent_and_lease(tmp_path):
    later = {"status": "running", "source": FIRST, "indices": (2,), "uncertain": ()}
    with world(tmp_path, UNKNOWN, later) as (store, root, _):
        uploads = StateUploads(store)
        at = stamp(store, root, now=datetime(2026, 11, 2, 11, 1, tzinfo=UTC))
        deep = uploads.chain_snapshot(SECOND, at)
        root_operation = root["record"]["operation_id"]
        # Each journal's parent is the operation before it; the facts are the source's own.
        assert [j.parent_operation_id for j in deep.journals] == [None, root_operation, FIRST]
        assert deep.source.status == "running" and deep.source.lease_active is True
        assert uploads.chain_snapshot(FIRST, at).source.status == "unknown"
        assert deep.descendants == ()
        # A lease is over at the very instant it expires, not a moment later.
        expires = datetime(2026, 11, 2, 11, 2, 32, tzinfo=UTC)
        for now, active in ((expires - timedelta(microseconds=1), True), (expires, False)):
            facts = uploads.chain_snapshot(FIRST, stamp(store, root, now=now)).descendants[0]
            assert facts.lease_active is active


def test_the_descendants_of_a_source_come_in_operation_order_whatever_their_state(tmp_path):
    with world(tmp_path, {"status": "cancelled"}, {"status": "running"}) as (store, root, _):
        at = stamp(store, root, now=datetime(2026, 11, 2, 11, 1, tzinfo=UTC))
        snapshot = StateUploads(store).chain_snapshot(root["record"]["operation_id"], at)
        assert [(d.operation_id, d.status, d.lease_active) for d in snapshot.descendants] == [
            (FIRST, "cancelled", False),
            (SECOND, "running", True),
        ]


def test_a_v1_operation_is_a_root_with_no_explicit_policy_and_no_dataset_of_its_own(tmp_path):
    with open_store(tmp_path / "state", timeout=60) as store:
        plan, record = install_legacy_running(store, history=True)
        view = read_any_view(store.connection, plan.plan_id)
        assert view.operation.schema_version == 1 and len(view.intents) == 1
        at = Stamp(
            plan.scope.store_id,
            plan.scope.identity_epoch,
            1,
            datetime(2026, 11, 2, 11, 1, tzinfo=UTC),
            False,
        )
        snapshot = StateUploads(store).chain_snapshot(record.operation_id, at)
        assert [j.operation_id for j in snapshot.journals] == [record.operation_id]
        assert snapshot.journals[0].parent_operation_id is None
        # The oldest family never granted an explicit read, and its create left no strict receipt.
        assert snapshot.source.policy == "verified_only"
        assert snapshot.source.has_created_dataset is False
        assert snapshot.source.status == "running" and snapshot.descendants == ()


def test_a_source_whose_plan_row_is_gone_is_a_corrupt_history(tmp_path):
    later = {"status": "running", "source": FIRST, "indices": (2,), "uncertain": ()}
    with world(tmp_path, UNKNOWN, later) as (store, _, (first, item)):
        assert read(store, item).operation.status == "running"  # the control
        store.connection.execute("PRAGMA foreign_keys=OFF")  # the operation row stays, dangling
        store.connection.execute(
            "DELETE FROM upload_approvals WHERE plan_id=?", (first.plan["plan_id"],)
        )
        store.connection.execute(
            "DELETE FROM upload_plans WHERE plan_id=?", (first.plan["plan_id"],)
        )
        refused(store, item)


# --- what only a continuation as a source can show ---------------------------------------------


def test_a_continuation_source_whose_graph_is_complete_is_reconciled_not_continued(tmp_path):
    check_only = {"status": "admitted", "source": FIRST, "indices": ()}
    complete = {"status": "unknown", "intents": 6, "acknowledged": 6}  # every stage answered
    with world(tmp_path / "bad", complete, check_only) as (store, _, (source, later)):
        assert read(store, source).operation.status == "unknown"  # a valid history on its own
        refused(store, later)
    # The control: the same chain over a source that still has a stage in flight reads back.
    with world(tmp_path / "ok", UNKNOWN, check_only) as (store, _, (_, later)):
        assert read(store, later).operation.status == "admitted"


def test_a_continuation_of_a_source_that_holds_a_known_rejection_is_a_corrupt_history(tmp_path):
    held = {"status": "unknown", "intents": 2, "acknowledged": 2}  # a presign and a put, answered
    follow = {"status": "running", "source": FIRST}  # sends the second and third files again
    with world(tmp_path / "ok", held, follow) as (store, _, (_, later)):
        assert read(store, later).operation.status == "running"  # the control
    with world(tmp_path / "bad", held, follow) as (store, _, (source, later)):
        put = source.receipts[1]  # the source's put, answered with a rejection after all
        rejected = {
            **put,
            "result": "rejected",
            "dataset_id": None,
            "object_key": None,
            "sent_bytes": None,
            "sent_sha256": None,
        }
        store.connection.execute(
            "UPDATE upload_stage_receipts SET payload=? WHERE intent_id=?",
            (canon(rejected).decode(), put["intent_id"]),
        )
        assert read(store, source).operation.status == "unknown"  # the source alone still reads
        refused(store, later)


def test_the_descendants_of_a_source_come_in_operation_order_not_in_storing_order(tmp_path):
    with open_store(tmp_path / "state", timeout=60) as store:
        root = install_root(store)
        stored_first = build(root, 2, status="running")
        stored_last = build(root, 1, status="cancelled")
        install(store, stored_first)
        install(store, stored_last)
        at = stamp(store, root, now=datetime(2026, 11, 2, 11, 1, tzinfo=UTC))
        snapshot = StateUploads(store).chain_snapshot(root["record"]["operation_id"], at)
        assert [d.operation_id for d in snapshot.descendants] == [FIRST, SECOND]


def test_the_baseline_gate_of_a_continuation_reads_and_walks_its_lineage_once(
    tmp_path, monkeypatch
):
    import yorunge.adapters.upload_store as store_module

    later = {"status": "running", "source": FIRST, "indices": (2,), "uncertain": ()}
    with world(tmp_path, UNKNOWN, later) as (store, _, _):
        walks, reads = [], []
        real_walk, real_read = store_module.resolve_lineage, store_module._read_view
        monkeypatch.setattr(
            store_module,
            "resolve_lineage",
            lambda *args: (walks.append(args[0]), real_walk(*args))[1],
        )
        monkeypatch.setattr(
            store_module, "_read_view", lambda *args: (reads.append(args[1]), real_read(*args))[1]
        )
        baseline = StateUploads(store).require_created_baseline(SECOND)
        assert baseline.id == DATASET_ID
        # The continuation, its source and the root are each read once, in one walk.
        assert len(walks) == 1 and len(reads) == 3


def test_a_continuation_and_its_lineage_are_read_in_one_snapshot_no_writer_can_slip_into(
    tmp_path, monkeypatch
):
    import yorunge.adapters.upload_store as store_module

    later = {"status": "running", "source": FIRST, "indices": (2,), "uncertain": ()}
    with world(tmp_path, UNKNOWN, later) as (store, _, _):
        other = sqlite3.connect(store.root / DB_NAME, timeout=0)
        refusals = []
        real = store_module.resolve_lineage

        def watched(*args):
            # The continuation's own view is read; a writer that wants to commit now is kept out.
            other.execute("BEGIN IMMEDIATE")
            try:
                other.execute("UPDATE upload_namespaces SET payload=payload")
                other.execute("COMMIT")
            except sqlite3.OperationalError as error:
                assert "locked" in str(error)
                refusals.append(True)
            finally:
                if other.in_transaction:
                    other.execute("ROLLBACK")
            return real(*args)

        monkeypatch.setattr(store_module, "resolve_lineage", watched)
        try:
            assert StateUploads(store).show(operation_id=SECOND).operation.status == "running"
        finally:
            other.close()
        assert refusals == [True]


# --- every member of a lineage is held to what came before it ----------------------------------

SECOND_AFTER_FIRST = {
    "status": "running",
    "source": FIRST,
    "indices": (2,),
    "uncertain": (),
    "intents": 2,
    "acknowledged": 2,
}
EARLIER_FAULTS = {
    "an unanswered confirm that is not marked": {**UNKNOWN, "uncertain": ()},
    "a file the root already confirmed": {
        "status": "unknown",
        "indices": (0, 1, 2),
        "uncertain": (1,),
        "intents": 5,
        "acknowledged": 4,
    },
}


@pytest.mark.parametrize("first", EARLIER_FAULTS.values(), ids=EARLIER_FAULTS)
def test_a_fault_in_an_earlier_continuation_is_found_from_the_continuation_after_it(
    tmp_path, first
):
    with world(tmp_path / "ok", UNKNOWN, SECOND_AFTER_FIRST) as (store, _, (_, item)):
        assert read(store, item).operation.status == "running"  # the control
    with world(tmp_path / "bad", first, SECOND_AFTER_FIRST) as (store, _, (earlier, item)):
        # The second continuation chooses right for what it follows; the first does not, and a
        # lineage that holds it is as corrupt as the first is alone.
        refused(store, earlier)
        refused(store, item)


def test_a_continuation_prepared_over_a_source_that_was_already_complete_is_found_later(tmp_path):
    whole = {"status": "unknown", "indices": (1,), "uncertain": (1,), "intents": 3}
    check_only = {"status": "admitted", "source": SECOND, "indices": ()}
    with world(tmp_path / "ok", {**whole, "intents": 2}, SECOND_AFTER_FIRST, check_only) as (
        store,
        _,
        (_, _, last),
    ):
        assert read(store, last).operation.status == "admitted"  # the control: a stage in flight
    with world(tmp_path / "bad", whole, SECOND_AFTER_FIRST, check_only) as (
        store,
        _,
        (first, second, last),
    ):
        assert read(store, first).operation.status == "unknown"  # the first is valid alone
        refused(store, second)  # the second was prepared over a source with nothing left to send
        refused(store, last)  # and the third follows the second, whose own fault is found


def test_a_cache_handed_in_empty_is_filled_by_the_first_walk_and_used_by_the_next(
    tmp_path, monkeypatch
):
    import yorunge.adapters.upload_store as store_module

    later = {"status": "running", "source": FIRST, "indices": (2,), "uncertain": ()}
    with world(tmp_path, UNKNOWN, later) as (store, _, (_, item)):
        view = store_module._read_view(store.connection, item.plan["plan_id"])
        reads, cache = [], {}
        real = store_module._read_view
        monkeypatch.setattr(
            store_module, "_read_view", lambda *args: (reads.append(args[1]), real(*args))[1]
        )
        assert len(store_module.lineage_of(store.connection, view, cache).sources) == 2
        assert len(reads) == 2 and len(cache) == 2  # both sources, each read once
        store_module.lineage_of(store.connection, view, cache)
        assert len(reads) == 2  # the empty dict that was handed in is the one that was filled
