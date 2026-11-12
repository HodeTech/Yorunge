"""Stored journal shapes reduce to the right lineage facts through the real SQLite journal."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from tests.integration.test_upload_journal import journal as journal
from yorunge.adapters.state import open_store
from yorunge.adapters.upload_chain import operation_journal
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_resume import (
    ContinuationSelection,
    RemoteInventory,
    RemoteItem,
    classify,
    merge_chain,
)

CREATE = ("create", None)
LINK = ("project_link", None)
FIRST_FILE = [CREATE, LINK, ("presign", 0)]
CONFIRMABLE = [*FIRST_FILE, ("put", 0)]
EVERY_STAGE = [
    CREATE,
    LINK,
    *[(kind, index) for index in range(3) for kind in ("presign", "put", "confirm")],
]


def advance(journal, stages, *, unanswered=(), rejected=()):
    """Arm every stage; answer it with an accepted receipt unless listed otherwise."""
    record = journal.approved()
    for stage in stages:
        intent, permit, _ = journal.arm(record, *stage)
        permit.consume()
        if stage not in unanswered:
            record = journal.accept(record, intent, rejected=stage in rejected).operation
    return record


def facts_of(journal, record):
    with open_store(journal.root) as store:
        return journal.repository(store).operation_journal(record.operation_id)


def receipts(facts):
    return [(s.kind, s.file_index, s.receipt) for s in facts.stages]


def accepted(stages):
    return [(kind, index, "accepted") for kind, index in stages]


SHAPES = {
    "only presign": (FIRST_FILE, (), (), ("none", "none", "none"), accepted(FIRST_FILE)),
    "presign and put accepted": (
        CONFIRMABLE,
        (),
        (),
        ("none", "none", "none"),
        accepted(CONFIRMABLE),
    ),
    "two workers, one put unknown": (
        [CREATE, LINK, ("presign", 0), ("presign", 1), ("put", 0), ("put", 1)],
        (("put", 1),),
        (),
        ("none", "none", "none"),
        [*accepted([CREATE, LINK, ("presign", 0), ("presign", 1), ("put", 0)]), ("put", 1, "none")],
    ),
    "confirm intent without receipt": (
        [*CONFIRMABLE, ("confirm", 0)],
        (("confirm", 0),),
        (),
        ("intent", "none", "none"),
        [*accepted(CONFIRMABLE), ("confirm", 0, "none")],
    ),
    "accepted confirm": (
        [*CONFIRMABLE, ("confirm", 0)],
        (),
        (),
        ("accepted", "none", "none"),
        accepted([*CONFIRMABLE, ("confirm", 0)]),
    ),
    "rejected presign": (
        FIRST_FILE,
        (),
        (("presign", 0),),
        ("none", "none", "none"),
        [*accepted([CREATE, LINK]), ("presign", 0, "rejected")],
    ),
}


@pytest.mark.parametrize("name", SHAPES)
def test_every_stored_shape_reduces_to_the_expected_facts_and_state(journal, name):
    stages, unanswered, rejected, states, expected = SHAPES[name]
    record = advance(journal, stages, unanswered=unanswered, rejected=rejected)
    facts = facts_of(journal, record)
    assert facts.operation_id == record.operation_id
    assert facts.parent_operation_id is None
    assert receipts(facts) == expected
    summary = merge_chain([facts], journal.manifest)
    assert summary.states == states
    assert summary.rejected_receipt == bool(rejected)
    assert not summary.source_graph_complete


def test_a_complete_graph_marks_the_source_graph_complete(journal):
    record = advance(journal, EVERY_STAGE)
    facts = facts_of(journal, record)
    assert facts.graph_complete
    assert len(facts.stages) == 11
    summary = merge_chain([facts], journal.manifest)
    assert summary.states == ("accepted", "accepted", "accepted")
    assert summary.source_graph_complete


def test_an_unknown_operation_has_no_journal(journal):
    with open_store(journal.root) as store:
        repository_value = journal.repository(store)
        str_value = str(uuid4())
        with pytest.raises(YorungeError) as raised:
            repository_value.operation_journal(str_value)
        assert raised.value.code == "operation_not_found"


def test_a_view_without_an_operation_has_no_journal():
    simple_namespace = SimpleNamespace(operation=None)
    with pytest.raises(YorungeError) as raised:
        operation_journal(simple_namespace)
    assert raised.value.code == "operation_not_found"


def test_reading_the_journal_facts_writes_nothing_and_leaks_no_receipt_content(journal):
    record = advance(journal, [*CONFIRMABLE, ("confirm", 0)], unanswered=(("confirm", 0),))
    with open_store(journal.root) as store:
        repository = journal.repository(store)
        before = list(store.connection.iterdump())
        viewed = repository.show(operation_id=record.operation_id)
        facts = repository.operation_journal(record.operation_id)
        assert list(store.connection.iterdump()) == before
        assert repository.show(operation_id=record.operation_id) == viewed
        assert store.verify().store_schema_version == 7
    assert viewed.operation.status == "running"
    assert len(viewed.intents) == 5
    text = repr(facts)
    assert "objects/" not in text
    assert "created_dataset" not in text
    assert "http" not in text


def inventory_of(journal, *indices):
    return RemoteInventory(
        tuple(
            RemoteItem(f.path, f.size, f.sha256, f"item-{i}")
            for i, f in enumerate(journal.manifest.files)
            if i in indices
        )
    )


def test_stored_shapes_classify_end_to_end_against_a_remote_inventory(journal):
    manifest = journal.manifest
    record = advance(journal, [*CONFIRMABLE, ("confirm", 0)])
    summary = merge_chain([facts_of(journal, record)], journal.manifest)
    healthy = classify(manifest, summary, inventory_of(journal, 0))
    assert healthy.classes == ("confirmed", "pending_clean", "pending_clean")
    assert healthy.selection() == ContinuationSelection((1, 2), (), 1)
    assert healthy.plannable
    drifted = classify(manifest, summary, inventory_of(journal))
    assert drifted.classes[0] == "drift_missing"
    assert "drift_missing" in drifted.blockers


@pytest.mark.parametrize("present,expected", [(False, "pending_uncertain"), (True, "observed")])
def test_an_unreceipted_confirm_needs_the_remote_to_tell_whether_it_landed(
    journal, present, expected
):
    record = advance(journal, [*CONFIRMABLE, ("confirm", 0)], unanswered=(("confirm", 0),))
    summary = merge_chain([facts_of(journal, record)], journal.manifest)
    result = classify(journal.manifest, summary, inventory_of(journal, *((0,) if present else ())))
    assert result.classes[0] == expected
    expected_selection = (
        ContinuationSelection((1, 2), (), 1)
        if present
        else ContinuationSelection((0, 1, 2), (0,), 0)
    )
    assert result.selection() == expected_selection


def test_facts_carry_the_stored_dataset_and_manifest_identity(journal):
    record = advance(journal, CONFIRMABLE)
    facts = facts_of(journal, record)
    assert record.dataset_id is not None
    assert facts.dataset_id == record.dataset_id
    assert facts.manifest_digest == journal.plan.manifest.digest


def test_a_malformed_operation_id_is_invalid_request(journal):
    with open_store(journal.root) as store:
        repository_value = journal.repository(store)
        with pytest.raises(YorungeError) as raised:
            repository_value.operation_journal("not-a-uuid")
        assert raised.value.code == "invalid_request"


def test_a_plan_of_another_type_is_refused_instead_of_read_as_a_chain_root():
    record = SimpleNamespace(operation_id=str(uuid4()), dataset_id=None)
    simple_namespace = SimpleNamespace(operation=record, plan=object())
    with pytest.raises(YorungeError) as raised:
        operation_journal(simple_namespace)
    assert raised.value.code == "state_invalid"


def test_a_stored_v1_plan_is_a_valid_chain_root_and_a_wrong_one_is_refused():
    import json
    from pathlib import Path

    from yorunge.domain.capabilities import canonical
    from yorunge.domain.dataset_upload import DatasetUploadPlan as V1Plan

    fixtures = Path(__file__).parents[1] / "fixtures"
    legacy = V1Plan.model_validate_json(
        canonical(json.loads((fixtures / "dataset-upload-approved-v1.json").read_bytes())["plan"])
    )
    record = SimpleNamespace(operation_id=str(uuid4()), dataset_id=None)
    facts = operation_journal(
        SimpleNamespace(plan=legacy, operation=record, intents=(), receipts=())
    )
    assert facts.manifest_digest == legacy.manifest.digest
    assert facts.parent_operation_id is None
    assert facts.stages == ()
    assert facts.graph_complete is False


def test_a_refused_plan_type_keeps_the_operation_identity_in_the_error(journal, monkeypatch):
    from yorunge.adapters import upload_repository

    record = advance(journal, FIRST_FILE)

    def refuse(view):
        raise YorungeError("state_invalid")

    monkeypatch.setattr(upload_repository, "stored_journal", refuse)
    with open_store(journal.root) as store:
        repository_value = journal.repository(store)
        with pytest.raises(YorungeError) as raised:
            repository_value.operation_journal(record.operation_id)
    assert raised.value.code == "state_invalid"
    assert raised.value.operation_id == record.operation_id
