"""Resume classification equals its closed decision table cell by cell, by hand-made vectors."""

import hashlib
import unicodedata
from dataclasses import fields
from itertools import product
from pathlib import Path
from typing import get_args

import pytest

from yorunge.domain.dataset_manifest import DatasetFile, build_manifest
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_resume import (
    BLOCKERS,
    CHAIN_STATES,
    FILE_CLASSES,
    MAX_INVENTORY_ITEMS,
    MAX_INVENTORY_PAGES,
    Blocker,
    ChainSummary,
    Classification,
    ContinuationSelection,
    DescendantFact,
    DescendantVerdict,
    FileClass,
    InventoryFold,
    OperationJournal,
    RemoteInventory,
    RemoteItem,
    SourceFacts,
    StageFact,
    chain_blockers,
    classify,
    descendant_verdict,
    inventory_digest,
    merge_chain,
    merge_chain_steps,
    recommended_action,
    source_blockers,
)

REFERENCE = Path(__file__).parents[2] / "docs" / "reference" / "dataset-upload-continuation.md"


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


A = DatasetFile(path="a.bin", size=3, sha256=sha("a"))
B = DatasetFile(path="b.bin", size=0, sha256=sha("b"))
C = DatasetFile(path="c.bin", size=5, sha256=sha("c"))
FILES = (A, B, C)
MANIFEST_A = build_manifest((A,))
MANIFEST = build_manifest(FILES)
MANIFESTS = {1: MANIFEST_A, 3: MANIFEST}
IDS = {"a.bin": "id-a", "b.bin": "id-b", "c.bin": "id-c"}


def item(file, *, path=None, size=None, digest="same", item_id=None):
    return RemoteItem(
        path=path or file.path,
        size=file.size if size is None else size,
        sha256=file.sha256 if digest == "same" else digest,
        item_id=item_id or IDS.get(path or file.path, f"id-{path}"),
    )


def chain(*states, rejected=False, complete=False):
    digest = MANIFESTS[len(states)].digest if len(states) in MANIFESTS else sha("other manifest")
    return ChainSummary(tuple(states), rejected, complete, digest)


def inventory(*items, faults=()):
    return RemoteInventory(tuple(items), frozenset(faults))


def one(state, items, faults=()):
    """Class of a single-file manifest: the decision-table cell for (state, items)."""
    return classify(MANIFEST_A, chain(state), inventory(*items, faults=faults)).classes[0]


# --- the closed decision table ------------------------------------------------------------------
@pytest.mark.parametrize(
    "state,present,expected",
    [
        ("accepted", True, "confirmed"),
        ("accepted", False, "drift_missing"),
        ("intent", True, "observed"),
        ("intent", False, "pending_uncertain"),
        ("none", True, "observed"),
        ("none", False, "pending_clean"),
    ],
)
def test_every_journal_by_remote_cell_of_the_table(state, present, expected):
    assert one(state, [item(A)] if present else []) == expected


# Each attack names the class it must produce; none can leave a file in a safe class.
ATTACKS = {
    "same name, other size": ([item(A, size=4)], (), "conflict"),
    "same name, other hash": ([item(A, digest=sha("x"))], (), "conflict"),
    "duplicate name, two ids": ([item(A), item(A, item_id="id-other")], (), "conflict"),
    "same hash under another name": ([item(A, path="copy.bin", item_id="id-copy")], (), "conflict"),
    "exact item plus the same hash elsewhere": (
        [item(A), item(A, path="copy.bin", item_id="id-copy")],
        (),
        "conflict",
    ),
    "null hash on its item": ([item(A, digest=None)], (), "inventory_unreliable"),
    "null hash on an extra item": (
        [item(A), item(B, path="x.bin", digest=None, item_id="id-x")],
        (),
        "inventory_unreliable",
    ),
    "same item listed twice": ([item(A), item(A)], (), "inventory_unreliable"),
    "two names share one id": (
        [item(A), item(A, path="x.bin", item_id="id-a", digest=sha("x"))],
        (),
        "inventory_unreliable",
    ),
    "total mismatch": ([item(A)], ("total_mismatch",), "inventory_unreliable"),
    "cursor loop": ([item(A)], ("cursor_loop",), "inventory_unreliable"),
    "page limit": ([item(A)], ("page_limit",), "inventory_unreliable"),
    "too large": ([item(A)], ("too_large",), "inventory_unreliable"),
}


@pytest.mark.parametrize("state", ["none", "intent", "accepted"])
@pytest.mark.parametrize("name", ATTACKS)
def test_hostile_or_unverifiable_inventories_never_leave_a_safe_class(state, name):
    items, faults, expected = ATTACKS[name]
    result = classify(MANIFEST_A, chain(state), inventory(*items, faults=faults))
    assert result.classes == (expected,)
    assert not result.plannable
    assert expected in result.blockers
    assert not set(result.classes) & {"confirmed", "observed", "pending_clean", "pending_uncertain"}


def test_unreliable_listing_hides_absence_so_drift_is_never_claimed():
    # With an accepted receipt and no item, a trustworthy listing says drift; an untrustworthy
    # one says nothing about absence.
    assert one("accepted", []) == "drift_missing"
    assert one("accepted", [], faults=("cursor_loop",)) == "inventory_unreliable"
    assert one("none", [], faults=("total_mismatch",)) == "inventory_unreliable"


def test_a_positive_conflict_outranks_an_unreliable_listing_and_other_files_stay_unreliable():
    result = classify(
        MANIFEST,
        chain("accepted", "none", "none"),
        inventory(item(A, size=4), item(B), faults=("cursor_loop",)),
    )
    assert result.classes == ("conflict", "inventory_unreliable", "inventory_unreliable")
    assert result.blockers == ("conflict", "inventory_unreliable")


def test_blockers_follow_the_closed_order_and_only_what_was_observed():
    extra = item(A, path="extra.bin", digest=sha("e"), item_id="id-extra")
    result = classify(
        MANIFEST,
        chain("accepted", "accepted", "none", rejected=True, complete=True),
        inventory(item(A), extra, faults=("too_large",)),
    )
    # The listing is untrustworthy, so absence (B accepted but missing) is not drift either.
    assert result.classes == ("inventory_unreliable",) * 3
    assert result.blockers == (
        "reconcile_available",
        "known_negative",
        "extra_remote",
        "inventory_unreliable",
        "inventory_too_large",
    )
    assert list(result.blockers) == [b for b in BLOCKERS if b in result.blockers]


def test_extra_remote_item_blocks_without_changing_the_files_classes():
    extra = item(A, path="extra.bin", digest=sha("e"), item_id="id-extra")
    result = classify(MANIFEST, chain("accepted", "none", "none"), inventory(item(A), extra))
    assert result.classes == ("confirmed", "pending_clean", "pending_clean")
    assert result.blockers == ("extra_remote",)
    assert not result.plannable


def test_selection_counters_and_the_remote_present_count():
    result = classify(
        MANIFEST,
        chain("accepted", "intent", "none"),
        inventory(item(A)),
    )
    assert result.classes == ("confirmed", "pending_uncertain", "pending_clean")
    # The whole pending set, never a partial selection; present + sent covers the manifest.
    assert result.selection() == ContinuationSelection((1, 2), (1,), 1)
    assert [result.count(c) for c in FILE_CLASSES] == [1, 0, 1, 1, 0, 0, 0]
    assert result.blockers == ()
    assert result.plannable


def test_a_fully_present_folder_is_a_valid_verification_only_selection():
    result = classify(
        MANIFEST, chain("accepted", "none", "intent"), inventory(item(A), item(B), item(C))
    )
    assert result.classes == ("confirmed", "observed", "observed")
    assert result.selection() == ContinuationSelection((), (), 3)
    assert result.plannable


def test_one_blocking_file_makes_the_whole_classification_unplannable():
    for bad in ("drift_missing", "conflict"):
        items = [item(B)] if bad == "drift_missing" else [item(A, size=9), item(B)]
        result = classify(MANIFEST, chain("accepted", "none", "none"), inventory(*items))
        assert bad in result.blockers
        assert not result.plannable


# --- the lineage union ---------------------------------------------------------------------------
def stage(kind, index=None, receipt="accepted"):
    return StageFact(kind, index, receipt)


def op(name, parent, stages, *, dataset="ds", manifest=MANIFEST.digest, complete=False):
    return OperationJournal(name, parent, dataset, manifest, tuple(stages), complete)


ROOT_PREFIX = [stage("create"), stage("project_link")]


def states(*journals):
    return merge_chain(journals, MANIFEST).states


def test_only_confirm_facts_change_the_state_never_presign_or_put():
    prefix = [*ROOT_PREFIX, stage("presign", 0), stage("put", 0), stage("presign", 1, "none")]
    assert states(op("r", None, prefix)) == ("none", "none", "none")
    assert states(op("r", None, [*prefix, stage("confirm", 0, "none")])) == (
        "intent",
        "none",
        "none",
    )
    assert states(op("r", None, [*prefix, stage("confirm", 0)])) == ("accepted", "none", "none")
    assert states(op("r", None, [*prefix, stage("confirm", 1, "rejected")]))[1] == "intent"


def test_union_over_lineage_takes_accepted_over_intent_over_none():
    root = op("r", None, [stage("confirm", 0, "none"), stage("confirm", 1)], dataset="ds")
    child = op("c1", "r", [stage("confirm", 0), stage("confirm", 2, "none")])
    grand = op("c2", "c1", [stage("confirm", 2, "none")])
    assert states(root) == ("intent", "accepted", "none")
    assert states(root, child) == ("accepted", "accepted", "intent")
    # A later attempt never downgrades an earlier acceptance.
    assert states(root, child, op("c2", "c1", [stage("confirm", 1, "none")])) == (
        "accepted",
        "accepted",
        "intent",
    )
    assert states(root, child, grand) == ("accepted", "accepted", "intent")


def test_a_continuation_without_intents_adds_nothing():
    root = op("r", None, [stage("confirm", 0, "none")])
    assert states(root, op("c", "r", [])) == states(root)


def test_a_rejected_receipt_anywhere_in_the_lineage_is_remembered():
    root = op("r", None, [stage("presign", 0, "rejected")])
    assert merge_chain([root], MANIFEST).rejected_receipt
    later = [op("r", None, []), op("c", "r", [stage("put", 1, "rejected")])]
    assert merge_chain(later, MANIFEST).rejected_receipt
    assert not merge_chain(
        [op("r", None, [stage("confirm", 0, "none")])], MANIFEST
    ).rejected_receipt


def test_only_the_source_decides_whether_its_own_graph_is_already_complete():
    root = op("r", None, [], complete=True)
    child = op("c", "r", [], complete=False)
    assert merge_chain([root], MANIFEST).source_graph_complete
    assert not merge_chain([root, child], MANIFEST).source_graph_complete
    assert merge_chain(
        [op("r", None, []), op("c", "r", [], complete=True)], MANIFEST
    ).source_graph_complete


def test_the_steps_of_a_chain_are_its_prefixes_merged_one_by_one():
    root = op("r", None, [stage("confirm", 0, "none"), stage("confirm", 1)], complete=False)
    child = op(
        "c1", "r", [stage("confirm", 0), stage("put", 2, "rejected"), stage("confirm", 2, "none")]
    )
    grand = op("c2", "c1", [stage("confirm", 1)], complete=True)
    journals = [root, child, grand]
    steps = list(merge_chain_steps(journals, MANIFEST))
    assert steps == [merge_chain(journals[: n + 1], MANIFEST) for n in range(3)]
    # What each step says: a later member never changes an earlier summary.
    assert [step.states for step in steps] == [
        ("intent", "accepted", "none"),
        ("accepted", "accepted", "intent"),
        ("accepted", "accepted", "intent"),
    ]
    assert [step.rejected_receipt for step in steps] == [False, True, True]
    assert [step.source_graph_complete for step in steps] == [False, False, True]


def test_the_steps_of_a_chain_refuse_what_the_whole_chain_refuses_at_the_first_step():
    steps = merge_chain_steps([op("r", None, []), op("c", "r", [stage("create")])], MANIFEST)
    with pytest.raises(YorungeError) as raised:
        next(steps)  # the chain is checked as a whole, before any prefix is answered
    assert raised.value.code == "state_invalid"
    with pytest.raises(ValueError, match="at least its source"):
        next(merge_chain_steps([], MANIFEST))


@pytest.mark.parametrize(
    "journals",
    [
        [op("r", None, []), op("r", "r", [])],  # cycle / repeated identity
        [op("a", None, []), op("b", "a", []), op("a", "b", [])],  # loop back to the root
        [op("r", "x", [])],  # the root names a parent
        [op("r", None, []), op("c", "ghost", [])],  # broken lineage
        [op("r", None, []), op("c", None, [])],  # a second root
        [op("r", None, [], dataset="d1"), op("c", "r", [], dataset="d2")],  # other dataset
        [op("r", None, [], dataset=None), op("c", "r", [], dataset="d1")],  # no dataset at root
        [op("r", None, [], dataset=None), op("c", "r", [], dataset=None)],  # continues nothing
        [op("r", None, [stage("confirm", 3)])],  # index equals the file count
        [op("r", None, [stage("presign", -1)])],
        [op("r", None, [stage("create", 0)])],  # create carries no file index
        [op("r", None, [stage("put", None)])],  # a file stage needs its index
        [op("r", None, [stage("confirm", True)])],
        [op("r", None, []), op("c", "r", [], manifest="other")],  # another manifest
        [op("r", None, []), op("c", "r", [stage("create")])],  # a continuation never creates
        [op("r", None, []), op("c", "r", [stage("project_link")])],  # nor links
        [op("r", None, [stage("presign", 0), stage("presign", 0, "none")])],  # a stage twice
        [op("r", None, [stage("bogus", None)])],  # outside the closed stage kinds
        [op("r", None, [stage("confirm", 0, "maybe")])],  # outside the closed receipt states
    ],
)
def test_an_inconsistent_chain_or_stage_is_state_invalid(journals):
    with pytest.raises(YorungeError) as raised:
        merge_chain(journals, MANIFEST)
    assert raised.value.code == "state_invalid"


def numbered_manifest(count):
    return build_manifest(
        tuple(DatasetFile(path=f"f{n:03}.bin", size=1, sha256=sha(str(n))) for n in range(count))
    )


def test_merge_chain_takes_the_largest_upload_manifest_and_refuses_larger_or_empty_input():
    largest, larger = numbered_manifest(128), numbered_manifest(129)
    summary = merge_chain([op("r", None, [], manifest=largest.digest)], largest)
    assert len(summary.states) == 128
    with pytest.raises(ValueError, match="unsupported upload file count"):
        merge_chain([op("r", None, [], manifest=larger.digest)], larger)
    with pytest.raises(ValueError, match="at least its source"):
        merge_chain([], MANIFEST)


def test_a_journal_recorded_over_another_manifest_is_state_invalid():
    for journals in (
        [op("r", None, [], manifest=sha("elsewhere"))],
        [op("r", None, []), op("c", "r", [], manifest=sha("elsewhere"))],
    ):
        with pytest.raises(YorungeError) as raised:
            merge_chain(journals, MANIFEST)
        assert raised.value.code == "state_invalid"


def test_classify_requires_a_summary_for_exactly_the_manifest():
    with pytest.raises(ValueError, match="belongs to another manifest"):
        classify(MANIFEST, chain("none", "none"), inventory())
    short = ChainSummary(("none", "none"), False, False, MANIFEST.digest)
    with pytest.raises(ValueError, match="does not cover the manifest"):
        classify(MANIFEST, short, inventory())


# --- digests ------------------------------------------------------------------------------------
def test_digests_equal_hand_written_preimages():
    a = DatasetFile(path="a.bin", size=3, sha256="a" * 64)
    b = DatasetFile(path="b.bin", size=0, sha256="b" * 64)
    manifest = build_manifest((a, b))
    summary = ChainSummary(("accepted", "intent"), True, False, manifest.digest)
    items = [
        RemoteItem("b.bin", 0, "b" * 64, "id-2"),
        RemoteItem("a.bin", 3, "a" * 64, "id-1"),
    ]
    result = classify(manifest, summary, RemoteInventory(tuple(items)))
    assert result.classes == ("confirmed", "observed")
    inventory_preimage = (
        '{"items":[["a.bin",3,"' + "a" * 64 + '"],["b.bin",0,"' + "b" * 64 + '"]],'
        '"kind":"upload_inventory"}'
    )
    classification_preimage = (
        '{"chain":{"rejected":true,"states":["accepted","intent"]},'
        '"files":[[0,"confirmed"],[1,"observed"]],"kind":"upload_classification"}'
    )
    assert result.inventory_digest == hashlib.sha256(inventory_preimage.encode()).hexdigest()
    assert (
        result.classification_digest == hashlib.sha256(classification_preimage.encode()).hexdigest()
    )


def test_a_null_hash_stays_null_in_the_inventory_preimage():
    only = RemoteItem("a.bin", 3, None, "id-1")
    preimage = '{"items":[["a.bin",3,null]],"kind":"upload_inventory"}'
    assert (
        classify(MANIFEST_A, chain("none"), RemoteInventory((only,))).inventory_digest
        == hashlib.sha256(preimage.encode()).hexdigest()
    )


def test_digests_ignore_item_identity_order_and_provider_time_but_follow_content():
    base = classify(MANIFEST, chain("accepted", "none", "intent"), inventory(item(A), item(C)))
    shuffled = classify(
        MANIFEST,
        chain("accepted", "none", "intent"),
        inventory(item(C, item_id="other-c"), item(A, item_id="other-a")),
    )
    assert shuffled.inventory_digest == base.inventory_digest
    assert shuffled.classification_digest == base.classification_digest
    renamed = classify(
        MANIFEST, chain("accepted", "none", "intent"), inventory(item(A), item(C, size=6))
    )
    assert renamed.inventory_digest != base.inventory_digest
    for changed in (
        item(A, path="z.bin", item_id="id-a"),
        item(A, digest=sha("q")),
        item(A, size=8),
    ):
        other = classify(MANIFEST, chain("accepted", "none", "intent"), inventory(changed, item(C)))
        assert other.inventory_digest != base.inventory_digest


def test_classification_digest_follows_the_lineage_summary_not_only_the_classes():
    # An exact item makes both journal states 'observed', yet the lineages differ.
    present = inventory(item(A))
    never = classify(MANIFEST_A, chain("none"), present)
    attempted = classify(MANIFEST_A, chain("intent"), present)
    assert never.classes == attempted.classes == ("observed",)
    assert never.classification_digest != attempted.classification_digest
    rejected = classify(MANIFEST_A, chain("none", rejected=True), present)
    assert rejected.classification_digest != never.classification_digest
    # Completeness of the source graph is not part of the digest: it is a blocker, not a class.
    complete = classify(MANIFEST_A, chain("none", complete=True), present)
    assert complete.classification_digest == never.classification_digest


# --- the listing fold ----------------------------------------------------------------------------
def page(count, start=0):
    return [
        RemoteItem(f"f{start + i}.bin", 1, sha(str(start + i)), f"id{start + i}")
        for i in range(count)
    ]


def test_a_complete_two_page_listing_has_no_fault():
    fold = InventoryFold()
    assert fold.add(page(2), 3, "next") == "next"
    assert fold.add(page(1, 2), 3, None) is None
    result = fold.result()
    assert [i.path for i in result.items] == ["f0.bin", "f1.bin", "f2.bin"]
    assert result.faults == frozenset()


@pytest.mark.parametrize(
    "totals",
    [(5, 5, 5), (4, 4, 4), (3, 4, 3)],  # too many reported, too few, and a total that moves
)
def test_total_must_equal_the_collected_count_on_every_page(totals):
    fold = InventoryFold()
    fold.add(page(1), totals[0], "n1")
    fold.add(page(1, 1), totals[1], "n2")
    assert fold.add(page(1, 2), totals[2], None) is None
    assert fold.result().faults == frozenset({"total_mismatch"})


def test_a_repeated_cursor_stops_the_listing_as_a_loop():
    fold = InventoryFold()
    assert fold.add([], 0, "again") == "again"
    assert fold.add([], 0, "again") is None
    assert fold.result().faults == frozenset({"cursor_loop"})


def test_the_item_cap_is_exact_and_nothing_is_cut_silently():
    fold = InventoryFold()
    for number in range(MAX_INVENTORY_ITEMS // 128):
        assert fold.add(page(128, number * 128), 1024, f"c{number}") == f"c{number}"
    assert fold.add([], 1024, None) is None
    assert fold.result().faults == frozenset()
    assert len(fold.result().items) == MAX_INVENTORY_ITEMS

    over = InventoryFold()
    for number in range(MAX_INVENTORY_ITEMS // 128):
        over.add(page(128, number * 128), 1025, f"c{number}")
    assert over.add(page(1, 1024), 1025, "more") is None
    result = over.result()
    assert result.faults == frozenset({"too_large"})
    assert len(result.items) == MAX_INVENTORY_ITEMS + 1  # kept for evidence, never trusted


def test_endless_distinct_cursors_stop_at_the_page_limit():
    fold = InventoryFold()
    for number in range(MAX_INVENTORY_PAGES - 1):
        assert fold.add([], 0, f"c{number}") == f"c{number}"
    assert fold.add([], 0, "last") is None
    assert fold.result().faults == frozenset({"page_limit"})


def test_fold_is_single_use_and_cannot_report_before_it_ends():
    fold = InventoryFold()
    with pytest.raises(ValueError, match="not finished"):
        fold.result()
    fold.add([], 0, None)
    with pytest.raises(ValueError, match="already finished"):
        fold.add([], 0, None)


# --- descendants ----------------------------------------------------------------------------------
def verdict(*pairs):
    facts = [DescendantFact(f"d{n}", status, active) for n, (status, active) in enumerate(pairs)]
    result = descendant_verdict(facts)
    return result.blocker, result.related_operation_id


@pytest.mark.parametrize(
    "status,active,expected",
    [
        ("cancelled", False, None),
        ("admitted", False, None),
        ("admitted", True, "source_active"),
        ("running", True, "source_active"),
        ("unknown", True, "source_active"),
        ("running", False, "source_superseded"),
        ("unknown", False, "source_superseded"),
        ("failed", False, "source_superseded"),
        ("succeeded", False, "source_superseded"),
        # A terminal record has no lease; a stray flag must not make it 'active'.
        ("succeeded", True, "source_superseded"),
    ],
)
def test_descendant_table(status, active, expected):
    blocker, related = verdict((status, active))
    assert blocker == expected
    assert related == ("d0" if expected else None)


def test_cancelled_siblings_do_not_hide_the_one_relevant_descendant():
    assert verdict(("cancelled", False), ("unknown", False), ("admitted", False)) == (
        "source_superseded",
        "d1",
    )
    assert descendant_verdict([]).blocker is None


def test_two_relevant_descendants_are_a_branch_and_state_invalid():
    with pytest.raises(YorungeError) as raised:
        verdict(("unknown", False), ("succeeded", False))
    assert raised.value.code == "state_invalid"


# --- vocabulary and secrecy ----------------------------------------------------------------------
def test_closed_vocabularies_and_the_reference_agree():
    assert get_args(FileClass) == FILE_CLASSES
    assert get_args(Blocker) == BLOCKERS
    assert FILE_CLASSES == (
        "confirmed",
        "observed",
        "pending_clean",
        "pending_uncertain",
        "drift_missing",
        "conflict",
        "inventory_unreliable",
    )
    assert BLOCKERS == (
        "source_active",
        "source_ineligible",
        "source_superseded",
        "source_terminal",
        "reconcile_available",
        "create_unknown",
        "membership_unobserved",
        "known_negative",
        "drift_missing",
        "conflict",
        "extra_remote",
        "inventory_unreliable",
        "inventory_too_large",
        "local_changed",
    )
    assert CHAIN_STATES == ("none", "intent", "accepted")
    assert (MAX_INVENTORY_ITEMS, MAX_INVENTORY_PAGES) == (1024, 128)
    text = REFERENCE.read_text()
    start = text.index("Kapalı `blockers`")
    section = text[start : text.index("**Eylem önceliği.**", start)]
    # The reference lists every blocker once, in the reporting order.
    positions = [section.index(f"`{name}`") for name in BLOCKERS]
    assert positions == sorted(positions)
    assert all(f"`{name}`" in text for name in FILE_CLASSES)


def test_facts_and_summaries_carry_no_receipt_key_url_or_dataset_content():
    # By construction: the only strings in the facts are identifiers, kinds and receipt states.
    assert {f.name for f in fields(StageFact)} == {"kind", "file_index", "receipt"}
    assert {f.name for f in fields(OperationJournal)} == {
        "operation_id",
        "parent_operation_id",
        "dataset_id",
        "manifest_digest",
        "stages",
        "graph_complete",
    }
    assert {f.name for f in fields(ChainSummary)} == {
        "states",
        "rejected_receipt",
        "source_graph_complete",
        "manifest_digest",
    }


def test_every_class_is_reachable_from_some_state_and_inventory():
    reached = {
        one(state, items)
        for state, items in product(
            ("none", "intent", "accepted"),
            ([], [item(A)], [item(A, size=4)], [item(A, digest=None)]),
        )
    }
    assert reached == set(FILE_CLASSES)


# --- review hardening: single blockers, exact names, ties, self-defence -------------------------
def test_each_evidence_blocker_alone_blocks_planning_and_withholds_the_selection():
    extra = item(A, path="extra.bin", digest=sha("e"), item_id="id-extra")
    alone = {
        "reconcile_available": classify(
            MANIFEST_A, chain("accepted", complete=True), inventory(item(A))
        ),
        "known_negative": classify(
            MANIFEST_A, chain("accepted", rejected=True), inventory(item(A))
        ),
        "drift_missing": classify(MANIFEST_A, chain("accepted"), inventory()),
        "conflict": classify(MANIFEST_A, chain("none"), inventory(item(A, size=9))),
        "extra_remote": classify(MANIFEST_A, chain("accepted"), inventory(item(A), extra)),
        "inventory_unreliable": classify(
            MANIFEST_A, chain("none"), inventory(item(A), faults=("cursor_loop",))
        ),
    }
    for blocker, result in alone.items():
        assert result.blockers == (blocker,), blocker
        assert not result.plannable
        assert result.selection() is None
    # Too many items is always also an untrustworthy listing.
    huge = classify(MANIFEST_A, chain("none"), inventory(item(A), faults=("too_large",)))
    assert huge.blockers == ("inventory_unreliable", "inventory_too_large")
    assert huge.selection() is None


@pytest.mark.parametrize("name", ["A.BIN", unicodedata.normalize("NFD", "ä.bin")])
def test_names_are_compared_exactly_without_case_or_unicode_folding(name):
    path = "a.bin" if name == "A.BIN" else unicodedata.normalize("NFC", "ä.bin")
    file = DatasetFile(path=path, size=3, sha256=sha("a"))
    manifest = build_manifest((file,))
    unsent = ChainSummary(("none",), False, False, manifest.digest)
    other = classify(manifest, unsent, inventory(RemoteItem(name, 3, sha("z"), "x")))
    # A look-alike name is a foreign item, not the file; the file itself is not on the remote.
    assert other.classes == ("pending_clean",)
    assert other.blockers == ("extra_remote",)
    assert other.selection() is None
    same = classify(manifest, unsent, inventory(RemoteItem(name, 3, file.sha256, "x")))
    # The same content under a look-alike name is a copy of this file.
    assert same.classes == ("conflict",)
    assert not same.plannable


def test_a_manifest_that_repeats_a_hash_follows_the_table_and_marks_the_twin_a_conflict():
    twin = DatasetFile(path="twin.bin", size=3, sha256=A.sha256)
    manifest = build_manifest((A, twin))
    summary = ChainSummary(("none", "none"), False, False, manifest.digest)
    # Nothing remote: both look unsent (`--prepare` refuses duplicate content before any plan).
    assert classify(manifest, summary, inventory()).classes == ("pending_clean", "pending_clean")
    # Once one of them is there, the other is a copy of it.
    present = classify(manifest, summary, inventory(item(A)))
    assert present.classes == ("observed", "conflict")
    assert not present.plannable


@pytest.mark.parametrize(
    "states", [("Accepted",), ("accepted ",), ("rejected",), ("bogus",), (None,), ("none", 1)]
)
def test_a_chain_summary_refuses_states_outside_the_closed_set(states):
    with pytest.raises(ValueError, match="invalid chain summary"):
        ChainSummary(states, False, False, MANIFEST.digest)
    with pytest.raises(ValueError, match="invalid chain summary"):
        ChainSummary(["none"], False, False, MANIFEST.digest)
    for flags in ((1, False), (False, 1), ("no", False)):
        with pytest.raises(ValueError, match="invalid chain summary"):
            ChainSummary(("none",), *flags, MANIFEST.digest)


def test_a_root_may_create_and_link_while_its_continuation_sends_files():
    root = op("r", None, [*ROOT_PREFIX, stage("presign", 0), stage("confirm", 0, "none")])
    child = op("c", "r", [stage("presign", 0), stage("put", 0), stage("confirm", 0)])
    assert states(root, child) == ("accepted", "none", "none")


def test_the_digest_orders_ties_by_size_then_hash_with_a_null_hash_first():
    unhashed = RemoteItem("a.bin", 3, None, "i1")
    hashed = RemoteItem("a.bin", 3, sha("a"), "i2")
    larger = RemoteItem("a.bin", 4, sha("a"), "i3")
    expected = (
        '{"items":[["a.bin",3,null],["a.bin",3,"' + sha("a") + '"],["a.bin",4,"' + sha("a") + '"]],'
        '"kind":"upload_inventory"}'
    )
    for order in (
        [unhashed, hashed, larger],
        [larger, hashed, unhashed],
        [hashed, unhashed, larger],
    ):
        assert inventory_digest(order) == hashlib.sha256(expected.encode()).hexdigest()
    one, two = RemoteItem("a.bin", 3, sha("a"), "i1"), RemoteItem("a.bin", 3, sha("b"), "i2")
    assert inventory_digest([one, two]) == inventory_digest([two, one])
    short, long = RemoteItem("a.bin", 3, sha("a"), "i1"), RemoteItem("a.bin", 5, sha("a"), "i2")
    assert inventory_digest([short, long]) == inventory_digest([long, short])


def test_remote_names_and_identities_stay_out_of_reprs():
    listing = inventory(item(A))
    text = repr(listing) + repr(listing.items[0])
    assert "a.bin" not in text
    assert "id-a" not in text


def test_the_page_limit_and_item_cap_hold_their_documented_values():
    # The fold's own tests import these constants, so only a literal pins the contract.
    assert MAX_INVENTORY_ITEMS == 1024
    assert MAX_INVENTORY_PAGES == 128


# --- review round 2: rejected receipts, blocker merging, source eligibility, actions ------------
def test_a_rejected_receipt_is_found_in_any_journal_not_only_when_all_stages_are_rejected():
    base = [stage("presign", 0), stage("put", 0, "none")]
    early = op("r", None, [stage("presign", 0, "rejected"), stage("put", 0, "none")])
    late = op("c", "r", [stage("presign", 0, "none")])
    clean_root = op("r", None, base)
    flagged_child = op("c", "r", [stage("put", 0, "rejected")])
    assert merge_chain([early], MANIFEST).rejected_receipt
    assert merge_chain([early, late], MANIFEST).rejected_receipt  # only an ancestor rejected
    assert merge_chain([clean_root, flagged_child], MANIFEST).rejected_receipt  # only the source
    assert not merge_chain([clean_root, late], MANIFEST).rejected_receipt


def test_with_blockers_merges_caller_blockers_in_the_closed_order_and_closes_the_selection():
    clear = classify(MANIFEST_A, chain("none"), inventory())
    assert clear.plannable
    assert clear.selection() is not None
    held = clear.with_blockers(("local_changed", "source_active", "source_active"))
    assert held.blockers == ("source_active", "local_changed")
    assert not held.plannable
    assert held.selection() is None
    assert held.classes == clear.classes
    assert held.inventory_digest == clear.inventory_digest
    mixed = classify(MANIFEST_A, chain("accepted", rejected=True), inventory(item(A)))
    assert mixed.with_blockers(("source_terminal", "known_negative")).blockers == (
        "source_terminal",
        "known_negative",
    )
    assert clear.with_blockers(()) == clear
    with pytest.raises(ValueError, match="closed blockers"):
        clear.with_blockers(("bogus",))


def test_indices_report_one_class_without_being_a_selection():
    result = classify(MANIFEST, chain("accepted", "intent", "none"), inventory(item(A), item(B)))
    assert result.classes == ("confirmed", "observed", "pending_clean")
    assert [result.indices(name) for name in FILE_CLASSES] == [(0,), (1,), (2,), (), (), (), ()]
    blocked = classify(MANIFEST, chain("accepted", "none", "none"), inventory())
    assert blocked.indices("drift_missing") == (0,)
    assert blocked.selection() is None


@pytest.mark.parametrize(
    "changes",
    [
        {"classes": ()},
        {"classes": ("bogus",)},
        {"classes": ["conflict"]},
        {"blockers": ("extra_remote", "conflict")},  # not in the closed order
        {"blockers": ("conflict", "conflict")},
        {"blockers": ("bogus",)},
        {"blockers": ["conflict"]},
        {"classification_digest": "C" * 64},
        {"inventory_digest": "short"},
        {"manifest_digest": "short"},
        {"manifest_digest": "C" * 64},
        {"classes": ("conflict",), "blockers": ()},  # a blocking class without its blocker
        {"classes": ("drift_missing",), "blockers": ("conflict",)},
        {"classes": ("inventory_unreliable",), "blockers": ("conflict",)},
        {"classes": ("confirmed",) * 129},
    ],
)
def test_a_classification_refuses_inconsistent_parts(changes):
    good = classify(MANIFEST_A, chain("none"), inventory())
    fields_of = {
        "classes": good.classes,
        "blockers": good.blockers,
        "classification_digest": good.classification_digest,
        "inventory_digest": good.inventory_digest,
        "manifest_digest": good.manifest_digest,
    }
    with pytest.raises(ValueError, match="invalid classification"):
        Classification(**{**fields_of, **changes})


@pytest.mark.parametrize(
    "arguments",
    [
        ((1, 0), (), 0),
        ((0, 0), (), 0),
        ((0,), (1,), 0),
        ((0,), (0, 0), 0),
        ((True,), (), 0),
        ((128,), (), 0),
        ((0,), (), -1),
        ((0,), (), 129),
        ([0], (), 0),
        ((0,), (), True),
    ],
)
def test_a_continuation_selection_refuses_unordered_or_open_parts(arguments):
    with pytest.raises(ValueError, match="invalid continuation selection"):
        ContinuationSelection(*arguments)


def test_a_chain_summary_refuses_empty_or_oversized_state_vectors():
    for states in ((), ("none",) * 129):
        with pytest.raises(ValueError, match="invalid chain summary"):
            ChainSummary(states, False, False, MANIFEST.digest)
    with pytest.raises(ValueError, match="invalid chain summary"):
        ChainSummary(("none",), False, False, "not a digest")


NO_DESCENDANT = DescendantVerdict(None, None)


def facts(status="unknown", lease=False, policy="explicit_attempt", dataset=True):
    return SourceFacts(status, lease, policy, dataset)


@pytest.mark.parametrize(
    "source,verdict,expected",
    [
        # the eligible shapes: a lapsed running source and an unknown one
        (facts("running"), NO_DESCENDANT, ()),
        (facts("unknown"), NO_DESCENDANT, ()),
        (facts("succeeded"), NO_DESCENDANT, ("source_terminal",)),
        (facts("failed"), NO_DESCENDANT, ("source_terminal",)),
        (facts("cancelled"), NO_DESCENDANT, ("source_terminal",)),
        (facts("admitted"), NO_DESCENDANT, ("source_ineligible",)),
        (facts("admitted", lease=True), NO_DESCENDANT, ("source_ineligible", "source_active")),
        (facts("unknown", policy="verified_only"), NO_DESCENDANT, ("source_ineligible",)),
        (facts("running", lease=True), NO_DESCENDANT, ("source_active",)),
        (facts("unknown", lease=True), NO_DESCENDANT, ("source_active",)),
        (facts("unknown", dataset=False), NO_DESCENDANT, ("create_unknown",)),
        (facts("unknown"), DescendantVerdict("source_active", "d"), ("source_active",)),
        (facts("unknown"), DescendantVerdict("source_superseded", "d"), ("source_superseded",)),
        (
            facts("succeeded", policy="verified_only", dataset=False),
            DescendantVerdict("source_superseded", "d"),
            ("source_ineligible", "source_superseded", "source_terminal", "create_unknown"),
        ),
    ],
)
def test_source_blockers_follow_the_eligibility_table_in_reporting_order(source, verdict, expected):
    result = source_blockers(source, verdict)
    assert result == tuple(b for b in BLOCKERS if b in expected)
    assert set(result) == set(expected)


@pytest.mark.parametrize(
    "blockers,expected",
    [
        ((), "prepare"),
        (("source_terminal",), "none"),
        (("source_active",), "wait"),
        (("source_superseded",), "none"),
        (("source_ineligible",), "none"),
        (("create_unknown",), "none"),
        (("membership_unobserved",), "none"),
        (("known_negative",), "none"),
        (("reconcile_available",), "reconcile"),
        (("local_changed",), "none"),
        (("drift_missing",), "none"),
        (("conflict",), "none"),
        (("extra_remote",), "none"),
        (("inventory_unreliable",), "none"),
        (("inventory_unreliable", "inventory_too_large"), "none"),
        # the first match in the reference's order wins
        (("source_terminal", "source_active"), "none"),
        (("source_active", "source_superseded"), "wait"),
        (("source_active", "reconcile_available"), "wait"),
        (("reconcile_available", "known_negative"), "none"),
        (("reconcile_available", "local_changed"), "reconcile"),
        (("reconcile_available", "drift_missing", "conflict"), "reconcile"),
    ],
)
def test_the_recommended_action_follows_the_reference_priority(blockers, expected):
    assert recommended_action(blockers) == expected


def test_recommended_action_refuses_open_names_and_answers_for_every_blocker():
    with pytest.raises(ValueError, match="closed blockers"):
        recommended_action(("bogus",))
    assert {b: recommended_action((b,)) for b in BLOCKERS}.keys() == set(BLOCKERS)


def test_a_classification_names_the_manifest_it_indexes_and_keeps_it_when_blockers_are_merged():
    good = classify(MANIFEST, chain("none", "none", "none"), inventory())
    assert good.manifest_digest == MANIFEST.digest
    assert good.with_blockers(("local_changed",)).manifest_digest == MANIFEST.digest
    assert classify(MANIFEST_A, chain("none"), inventory()).manifest_digest == MANIFEST_A.digest


@pytest.mark.parametrize(
    "complete,rejected,expected",
    [
        (False, False, ()),
        (True, False, ("reconcile_available",)),
        (False, True, ("known_negative",)),
        (True, True, ("reconcile_available", "known_negative")),
    ],
)
def test_the_journal_alone_establishes_the_reconcile_and_known_negative_blockers(
    complete, rejected, expected
):
    summary = chain("none", "none", "none", rejected=rejected, complete=complete)
    assert chain_blockers(summary) == expected
    # classify raises exactly these before it looks at any item, whatever the inventory holds.
    for found in (inventory(), inventory(item(A), item(B), item(C))):
        assert set(expected) <= set(classify(MANIFEST, summary, found).blockers)
    plain = classify(MANIFEST, chain("none", "none", "none"), inventory())
    assert not set(plain.blockers) & {"reconcile_available", "known_negative"}
