"""Resume classification equals its closed decision table cell by cell, by hand-made vectors."""

import hashlib
import unicodedata
from dataclasses import fields
from itertools import product
from pathlib import Path
from typing import get_args

import pytest

from yorunge.domain.dataset_manifest import DatasetFile
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_resume import (
    BLOCKERS,
    CHAIN_STATES,
    FILE_CLASSES,
    MAX_INVENTORY_ITEMS,
    MAX_INVENTORY_PAGES,
    Blocker,
    ChainSummary,
    DescendantFact,
    FileClass,
    InventoryFold,
    OperationJournal,
    RemoteInventory,
    RemoteItem,
    Selection,
    StageFact,
    classify,
    descendant_verdict,
    inventory_digest,
    merge_chain,
)

REFERENCE = Path(__file__).parents[2] / "docs" / "reference" / "dataset-upload-continuation.md"


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


A = DatasetFile(path="a.bin", size=3, sha256=sha("a"))
B = DatasetFile(path="b.bin", size=0, sha256=sha("b"))
C = DatasetFile(path="c.bin", size=5, sha256=sha("c"))
FILES = (A, B, C)
IDS = {"a.bin": "id-a", "b.bin": "id-b", "c.bin": "id-c"}


def item(file, *, path=None, size=None, digest="same", item_id=None):
    return RemoteItem(
        path=path or file.path,
        size=file.size if size is None else size,
        sha256=file.sha256 if digest == "same" else digest,
        item_id=item_id or IDS.get(path or file.path, f"id-{path}"),
    )


def chain(*states, rejected=False, complete=False):
    return ChainSummary(tuple(states), rejected, complete, ("op",))


def inventory(*items, faults=()):
    return RemoteInventory(tuple(items), frozenset(faults))


def one(state, items, faults=()):
    """Class of a single-file manifest: the decision-table cell for (state, items)."""
    return classify((A,), chain(state), inventory(*items, faults=faults)).classes[0]


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
    result = classify((A,), chain(state), inventory(*items, faults=faults))
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
        FILES,
        chain("accepted", "none", "none"),
        inventory(item(A, size=4), item(B), faults=("cursor_loop",)),
    )
    assert result.classes == ("conflict", "inventory_unreliable", "inventory_unreliable")
    assert result.blockers == ("conflict", "inventory_unreliable")


def test_blockers_follow_the_closed_order_and_only_what_was_observed():
    extra = item(A, path="extra.bin", digest=sha("e"), item_id="id-extra")
    result = classify(
        FILES,
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
    result = classify(FILES, chain("accepted", "none", "none"), inventory(item(A), extra))
    assert result.classes == ("confirmed", "pending_clean", "pending_clean")
    assert result.blockers == ("extra_remote",)
    assert not result.plannable


def test_selection_counters_and_the_remote_present_count():
    result = classify(
        FILES,
        chain("accepted", "intent", "none"),
        inventory(item(A)),
    )
    assert result.classes == ("confirmed", "pending_uncertain", "pending_clean")
    # The whole pending set, never a partial selection; present + sent covers the manifest.
    assert result.selection() == Selection((1, 2), (1,), 1)
    assert [result.count(c) for c in FILE_CLASSES] == [1, 0, 1, 1, 0, 0, 0]
    assert result.blockers == () and result.plannable


def test_a_fully_present_folder_is_a_valid_verification_only_selection():
    result = classify(
        FILES, chain("accepted", "none", "intent"), inventory(item(A), item(B), item(C))
    )
    assert result.classes == ("confirmed", "observed", "observed")
    assert result.selection() == Selection((), (), 3)
    assert result.plannable


def test_one_blocking_file_makes_the_whole_classification_unplannable():
    for bad in ("drift_missing", "conflict"):
        items = [item(B)] if bad == "drift_missing" else [item(A, size=9), item(B)]
        result = classify(FILES, chain("accepted", "none", "none"), inventory(*items))
        assert bad in result.blockers and not result.plannable


# --- the lineage union ---------------------------------------------------------------------------
def stage(kind, index=None, receipt="accepted"):
    return StageFact(kind, index, receipt)


def op(name, parent, stages, *, dataset="ds", manifest="m", complete=False):
    return OperationJournal(name, parent, dataset, manifest, tuple(stages), complete)


ROOT_PREFIX = [stage("create"), stage("project_link")]


def states(*journals, count=3):
    return merge_chain(journals, count).states


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
    assert merge_chain([root], 3).rejected_receipt
    later = [op("r", None, []), op("c", "r", [stage("put", 1, "rejected")])]
    assert merge_chain(later, 3).rejected_receipt
    assert not merge_chain([op("r", None, [stage("confirm", 0, "none")])], 3).rejected_receipt


def test_only_the_source_decides_whether_its_own_graph_is_already_complete():
    root = op("r", None, [], complete=True)
    child = op("c", "r", [], complete=False)
    assert merge_chain([root], 3).source_graph_complete
    assert not merge_chain([root, child], 3).source_graph_complete
    assert merge_chain(
        [op("r", None, []), op("c", "r", [], complete=True)], 3
    ).source_graph_complete
    assert merge_chain([root, child], 3).operation_ids == ("r", "c")


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
        merge_chain(journals, 3)
    assert raised.value.code == "state_invalid"


@pytest.mark.parametrize("count", [0, 129, -1, True, None, 1.0])
def test_merge_chain_rejects_programming_errors(count):
    with pytest.raises(ValueError, match="unsupported upload file count"):
        merge_chain([op("r", None, [])], count)
    with pytest.raises(ValueError, match="at least its source"):
        merge_chain([], 3)


def test_classify_requires_a_summary_for_exactly_the_manifest():
    with pytest.raises(ValueError, match="does not cover the manifest"):
        classify(FILES, chain("none", "none"), inventory())


# --- digests ------------------------------------------------------------------------------------
def test_digests_equal_hand_written_preimages():
    a = DatasetFile(path="a.bin", size=3, sha256="a" * 64)
    b = DatasetFile(path="b.bin", size=0, sha256="b" * 64)
    summary = ChainSummary(("accepted", "intent"), True, False, ("op",))
    items = [
        RemoteItem("b.bin", 0, "b" * 64, "id-2"),
        RemoteItem("a.bin", 3, "a" * 64, "id-1"),
    ]
    result = classify((a, b), summary, RemoteInventory(tuple(items)))
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
        classify((A,), chain("none"), RemoteInventory((only,))).inventory_digest
        == hashlib.sha256(preimage.encode()).hexdigest()
    )


def test_digests_ignore_item_identity_order_and_provider_time_but_follow_content():
    base = classify(FILES, chain("accepted", "none", "intent"), inventory(item(A), item(C)))
    shuffled = classify(
        FILES,
        chain("accepted", "none", "intent"),
        inventory(item(C, item_id="other-c"), item(A, item_id="other-a")),
    )
    assert shuffled.inventory_digest == base.inventory_digest
    assert shuffled.classification_digest == base.classification_digest
    renamed = classify(
        FILES, chain("accepted", "none", "intent"), inventory(item(A), item(C, size=6))
    )
    assert renamed.inventory_digest != base.inventory_digest
    for changed in (
        item(A, path="z.bin", item_id="id-a"),
        item(A, digest=sha("q")),
        item(A, size=8),
    ):
        other = classify(FILES, chain("accepted", "none", "intent"), inventory(changed, item(C)))
        assert other.inventory_digest != base.inventory_digest


def test_classification_digest_follows_the_lineage_summary_not_only_the_classes():
    # An exact item makes both journal states 'observed', yet the lineages differ.
    present = inventory(item(A))
    never = classify((A,), chain("none"), present)
    attempted = classify((A,), chain("intent"), present)
    assert never.classes == attempted.classes == ("observed",)
    assert never.classification_digest != attempted.classification_digest
    rejected = classify((A,), chain("none", rejected=True), present)
    assert rejected.classification_digest != never.classification_digest
    # Completeness of the source graph is not part of the digest: it is a blocker, not a class.
    complete = classify((A,), chain("none", complete=True), present)
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
        "operation_ids",
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
        "reconcile_available": classify((A,), chain("accepted", complete=True), inventory(item(A))),
        "known_negative": classify((A,), chain("accepted", rejected=True), inventory(item(A))),
        "drift_missing": classify((A,), chain("accepted"), inventory()),
        "conflict": classify((A,), chain("none"), inventory(item(A, size=9))),
        "extra_remote": classify((A,), chain("accepted"), inventory(item(A), extra)),
        "inventory_unreliable": classify(
            (A,), chain("none"), inventory(item(A), faults=("cursor_loop",))
        ),
    }
    for blocker, result in alone.items():
        assert result.blockers == (blocker,), blocker
        assert not result.plannable and result.selection() is None
    # Too many items is always also an untrustworthy listing.
    huge = classify((A,), chain("none"), inventory(item(A), faults=("too_large",)))
    assert huge.blockers == ("inventory_unreliable", "inventory_too_large")
    assert huge.selection() is None


@pytest.mark.parametrize("name", ["A.BIN", unicodedata.normalize("NFD", "ä.bin")])
def test_names_are_compared_exactly_without_case_or_unicode_folding(name):
    path = "a.bin" if name == "A.BIN" else unicodedata.normalize("NFC", "ä.bin")
    file = DatasetFile(path=path, size=3, sha256=sha("a"))
    other = classify((file,), chain("none"), inventory(RemoteItem(name, 3, sha("z"), "x")))
    # A look-alike name is a foreign item, not the file; the file itself is not on the remote.
    assert other.classes == ("pending_clean",)
    assert other.blockers == ("extra_remote",) and other.selection() is None
    same = classify((file,), chain("none"), inventory(RemoteItem(name, 3, file.sha256, "x")))
    # The same content under a look-alike name is a copy of this file.
    assert same.classes == ("conflict",) and not same.plannable


def test_a_manifest_that_repeats_a_path_or_a_hash_is_state_invalid():
    twin = DatasetFile(path="twin.bin", size=3, sha256=A.sha256)
    again = DatasetFile(path=A.path, size=4, sha256=sha("other"))
    for files in ((A, twin), (A, again)):
        with pytest.raises(YorungeError) as raised:
            classify(files, chain("none", "none"), inventory())
        assert raised.value.code == "state_invalid"


@pytest.mark.parametrize(
    "states", [("Accepted",), ("accepted ",), ("rejected",), ("bogus",), (None,), ("none", 1)]
)
def test_a_chain_summary_refuses_states_outside_the_closed_set(states):
    with pytest.raises(ValueError, match="invalid chain summary"):
        ChainSummary(states, False, False, ("op",))
    with pytest.raises(ValueError, match="invalid chain summary"):
        ChainSummary(["none"], False, False, ("op",))
    for flags in ((1, False), (False, 1), ("no", False)):
        with pytest.raises(ValueError, match="invalid chain summary"):
            ChainSummary(("none",), *flags, ("op",))


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
    assert "a.bin" not in text and "id-a" not in text


def test_the_page_limit_and_item_cap_hold_their_documented_values():
    # The fold's own tests import these constants, so only a literal pins the contract.
    assert MAX_INVENTORY_ITEMS == 1024 and MAX_INVENTORY_PAGES == 128
