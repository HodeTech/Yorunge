"""A continuation is read only with the lineage it was prepared from, and its graph is validated.

Every history here is a real root upload (with its strict create receipt) and continuations built
by plain hashlib/json in ``tests/fixtures/continuation_history.py``, stored as SQLite rows and read
back through the store. A negative test breaks exactly one thing in an otherwise valid history.
"""

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest

from tests.fixtures.continuation_history import (
    CREATE_RECEIPT,
    DATASET_ID,
    FILES,
    INTENT_SHAPE,
    MANIFEST,
    build,
    install,
    install_root,
    sha,
    uuid,
)
from yorunge.adapters.capability_cache import Stamp
from yorunge.adapters.state import DB_NAME, open_store
from yorunge.adapters.upload_chain import operation_journal
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import (
    created_dataset,
    legacy_create_without_baseline,
    read_any_view,
    read_view_and_lineage,
)
from yorunge.domain.create_receipt import CreateReceiptV2
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3, DatasetUploadApprovalV3
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_transfer_v3 import TransferControlV3, TransferVerificationV3
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_resume import merge_chain

OTHER = uuid(0x999)
FIRST, SECOND = uuid(0x301), uuid(0x302)  # the operations of continuations numbered 1 and 2

SHAPES = {
    "admitted": {"status": "admitted"},
    "running, one stage sent": {"status": "running", "intents": 1, "acknowledged": 1},
    "running, a stage in flight": {"status": "running", "intents": 4, "acknowledged": 3},
    "unknown": {"status": "unknown", "intents": 5, "acknowledged": 4},
    "succeeded": {"status": "succeeded"},
    "cancelled": {"status": "cancelled"},
    "check-only admitted": {"status": "admitted", "indices": ()},
    "check-only succeeded": {"status": "succeeded", "indices": ()},
    "check-only cancelled": {"status": "cancelled", "indices": ()},
}
UNKNOWN = SHAPES["unknown"]


@contextmanager
def world(tmp_path, *specs):
    """A store with the root and the continuations ``specs`` describe.

    A spec is ``build`` keywords, plus ``tweak`` (a function that breaks one thing of the built
    continuation before it is stored) and ``plan_only`` (store its plan and approval, no operation).
    """
    with open_store(tmp_path / "state") as store:
        root = install_root(store)
        built = []
        for number, spec in enumerate(specs, 1):
            spec = dict(spec)
            tweak = spec.pop("tweak", None)
            plan_only = spec.pop("plan_only", False)
            item = build(root, number, **spec)
            if tweak is not None:
                tweak(item)
            if plan_only:
                item.record = None
            install(store, item)
            built.append(item)
        yield store, root, built


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
        "indices": (1,),
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
    follow = {"status": "running", "source": FIRST, "indices": (1,)}
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
    second = {"status": "running", "source": FIRST, "indices": (1,)}
    with world(tmp_path, first, second) as (store, _, (a, b)):
        refused(store, a)
        refused(store, b)


def test_a_continuation_cannot_be_its_own_source(tmp_path):
    with world(tmp_path, {"status": "running", "source": FIRST}) as (store, _, (item,)):
        refused(store, item)


def test_a_source_that_is_only_a_plan_is_not_a_source(tmp_path):
    later = {"status": "running", "source": FIRST, "indices": (1,)}
    with world(tmp_path, {**UNKNOWN, "plan_only": True}, later) as (store, _, (_, item)):
        refused(store, item)


def test_a_continuation_whose_root_rows_are_gone_is_a_corrupt_history(tmp_path):
    with open_store(tmp_path / "state") as store:
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
    later = {"status": "running", "source": FIRST, "indices": (1,)}
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
        lambda c: c.intents.append(extra_intent(c, kind="presign", file_index=1)),
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
    later = {"status": "running", "source": FIRST, "indices": (1,), "intents": 2, "acknowledged": 2}
    with world(tmp_path, UNKNOWN, later) as (store, root, (first, _)):
        uploads = StateUploads(store)
        at = stamp(store, root, now=datetime(2026, 11, 2, 11, 1, tzinfo=UTC))
        snapshot = uploads.chain_snapshot(FIRST, at)
        root_operation = root["record"]["operation_id"]
        assert [j.operation_id for j in snapshot.journals] == [root_operation, FIRST]
        assert [j.parent_operation_id for j in snapshot.journals] == [None, root_operation]
        assert {j.dataset_id for j in snapshot.journals} == {DATASET_ID}
        assert {j.manifest_digest for j in snapshot.journals} == {MANIFEST["digest"]}
        # The combined lineage is what merge_chain takes: the root confirmed all three files.
        manifest = DatasetManifest.model_validate_json(canon_manifest())
        assert merge_chain(snapshot.journals, manifest).states == ("accepted",) * 3
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
    later = {"status": "running", "source": FIRST, "indices": (1,)}
    with world(tmp_path, UNKNOWN, later) as (store, root, _):
        uploads = StateUploads(store)
        other = sqlite3.connect(store.root / DB_NAME, timeout=0)
        refusals = []
        real = operation_journal

        def spy(view):
            # While the journals are being read, another connection cannot add a descendant: it
            # may start writing, but its commit needs the lock the reader's snapshot holds.
            other.execute("BEGIN IMMEDIATE")
            try:
                other.execute("UPDATE upload_namespaces SET payload=payload")
                other.execute("COMMIT")
            except sqlite3.OperationalError as error:
                refusals.append(str(error))
            finally:
                if other.in_transaction:
                    other.execute("ROLLBACK")
            return real(view)

        monkeypatch.setattr("yorunge.adapters.upload_chain.operation_journal", spy)
        try:
            at = stamp(store, root, now=datetime(2026, 11, 2, 11, 1, tzinfo=UTC))
            uploads.chain_snapshot(FIRST, at)
        finally:
            other.close()
        assert refusals and all("locked" in message for message in refusals)


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

    later = {"status": "running", "source": FIRST, "indices": (1,)}
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
