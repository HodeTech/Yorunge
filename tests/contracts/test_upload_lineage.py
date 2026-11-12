"""The walk from a continuation to the root that made its dataset, rule by rule.

The views are built from real models and handed to ``resolve_lineage`` through a reader and a
create-receipt lookup of the test's own, so each rule is broken alone and the unbroken walk (the
control) is checked in the same test.
"""

from types import SimpleNamespace

import pytest

from tests.fixtures.continuation_history import (
    CREATE_RECEIPT,
    DATASET_ID,
    GRAPH,
    build,
    canon,
    fixture,
    sha,
    uuid,
)
from yorunge.adapters.upload_chain import operation_journal
from yorunge.adapters.upload_lineage import (
    MAX_LINEAGE,
    check_selection,
    journal_of,
    resolve_lineage,
)
from yorunge.domain.create_receipt import CreateReceiptV2
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.dataset_transfer_v2 import TransferRecordV2
from yorunge.domain.dataset_transfer_v3 import TransferRecordV3
from yorunge.domain.dataset_upload import DatasetUploadPlan
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import YorungeError

OTHER = uuid(0x999)
CREATED = CreateReceiptV2.model_validate_json(CREATE_RECEIPT).created_dataset
ROOT_OPERATION = GRAPH["record"]["operation_id"]
FIRST, SECOND = uuid(0x301), uuid(0x302)
# What ``build`` reads of an installed root: its scope, its operation and its namespace digest.
ROOT = {
    "plan": {"scope": GRAPH["plan"]["scope"]},
    "record": {
        "operation_id": ROOT_OPERATION,
        "intent_digest": GRAPH["record"]["intent_digest"],
    },
}
ROOT_VIEW = SimpleNamespace(
    plan=DatasetUploadPlanV2.model_validate_json(canon(GRAPH["plan"])),
    operation=TransferRecordV2.model_validate_json(canon(GRAPH["record"])),
    receipts=(),
)


def view(item, *, plan=None, operation=True, **changes):
    """The view of a built continuation; ``changes`` break its record without re-validating it."""
    model = DatasetContinuationPlanV3.model_validate_json(canon(item.plan))
    record = TransferRecordV3.model_validate_json(canon(item.record)).model_copy(update=changes)
    return SimpleNamespace(
        plan=plan or model,
        operation=record if operation else None,
        intents=(),
        receipts=(),
        key=item.record["operation_id"],  # which operation this stands for, even as a plan only
    )


def resolve(target, views, *, root=ROOT_VIEW, created=lambda _: CREATED):
    # The store can read the continuation's own operation too, so a walk may come back to it.
    by_operation = {ROOT_OPERATION: root, target.record["operation_id"]: view(target)}
    by_operation |= {v.key: v for v in views}

    def read(operation_id):
        if operation_id not in by_operation:
            raise YorungeError("operation_not_found")
        return by_operation[operation_id]

    return resolve_lineage(view(target).plan, read, created)


def chain(**binding):
    """A continuation of the root, and a second one of the first."""
    first = build(ROOT, 1, status="unknown", intents=5, acknowledged=4, binding=binding)
    second = build(ROOT, 2, status="running", source=FIRST, indices=(1,), binding=binding)
    return first, second


def test_a_valid_lineage_runs_from_the_root_and_names_the_baseline():
    first, second = chain()
    lineage = resolve(second, [view(first)])
    assert [v.operation.operation_id for v in lineage.sources] == [ROOT_OPERATION, FIRST]
    assert lineage.baseline == CREATED
    assert lineage.baseline.id == DATASET_ID
    # The continuations among the sources keep their bindings, in the same order; the root has none.
    assert [b.source_operation_id for b in lineage.bindings] == [ROOT_OPERATION]
    assert lineage.bindings[0] == view(first).plan.continuation
    # The first continuation's own lineage is the root alone.
    alone = resolve(first, [])
    assert [v.operation.operation_id for v in alone.sources] == [ROOT_OPERATION]
    assert alone.bindings == ()


def refuses(target, views, **how):
    with pytest.raises(ValueError):
        resolve(target, views, **how)


def test_a_source_that_is_only_a_plan_is_refused():
    first, second = chain()
    assert resolve(second, [view(first)])
    refuses(second, [view(first, operation=False)])


def test_a_source_that_never_sent_anything_is_refused():
    first, second = chain()
    refuses(second, [view(first, workflow_latched=False)])


def test_a_source_over_another_manifest_is_refused():
    first, second = chain()
    source = view(first)
    other = source.plan.manifest.model_copy(update={"digest": "9" * 64})
    refuses(second, [view(first, plan=source.plan.model_copy(update={"manifest": other}))])


COPIED = {
    "parameters": lambda plan: {
        "parameters": plan.parameters.model_copy(update={"modality": "AUDIO"})
    },
    "root": lambda plan: {"root": plan.root.model_copy(update={"anchor": "/elsewhere"})},
    "manifest reference": lambda plan: {
        "manifest": plan.manifest.model_copy(update={"total_bytes": plan.manifest.total_bytes + 1})
    },
    "admission policy": lambda plan: {"admission_policy": "verified_only"},
    "cost policy": lambda plan: {"cost_policy": "bounded_required"},
}


@pytest.mark.parametrize("change", COPIED.values(), ids=COPIED)
def test_a_source_that_differs_in_what_the_plan_copies_or_inherits_is_refused(change):
    first, second = chain()
    source = view(first)
    assert resolve(second, [view(first)])
    refuses(second, [view(first, plan=source.plan.model_copy(update=change(source.plan)))])


@pytest.mark.parametrize(
    "states,files,uncertain,allowed",
    [
        (("accepted", "intent", "none"), (1, 2), (1,), True),
        (("accepted", "accepted", "none"), (2,), (), True),
        (("none", "none", "none"), (0, 1, 2), (), True),
        (("accepted", "accepted", "accepted"), (), (), True),
        (("accepted", "intent", "none"), (0, 2), (), False),  # a confirmed file again
        (("accepted", "intent", "none"), (1, 2), (), False),  # an unanswered confirm unmarked
        (("accepted", "intent", "none"), (1, 2), (1, 2), False),  # a clean file marked
        (("accepted", "intent", "none"), (1, 2), (2,), False),  # the wrong file marked
    ],
)
def test_a_selection_is_what_the_lineage_has_not_confirmed_and_what_it_left_unanswered(
    states, files, uncertain, allowed
):
    binding = SimpleNamespace(file_indices=files, uncertain_indices=uncertain)
    if allowed:
        check_selection(binding, states)
    else:
        with pytest.raises(ValueError):
            check_selection(binding, states)


def test_a_source_in_another_namespace_is_refused():
    first, second = chain()
    source = view(first)
    assert resolve(second, [view(first)])
    # Same parameters, another project: only the namespace digest (target, owner, project, name)
    # tells; the copied fields alone would pass.
    moved = source.plan.scope.model_copy(update={"project_id": OTHER})
    assert source.plan.model_copy(update={"scope": moved}).intent_digest() != (
        source.plan.intent_digest()
    )
    refuses(second, [view(first, plan=source.plan.model_copy(update={"scope": moved}))])
    # Another name is a namespace change too (and a parameter change: either is enough).
    renamed = source.plan.parameters.model_copy(update={"name": "other"})
    refuses(second, [view(first, plan=source.plan.model_copy(update={"parameters": renamed}))])


def test_a_source_that_holds_another_dataset_is_refused():
    first, second = chain()
    refuses(second, [view(first, dataset_id=OTHER)])


@pytest.mark.parametrize(
    "change",
    [
        {"baseline_digest": "e" * 64},
        {"baseline_operation_id": OTHER},
        {"dataset_id": OTHER},
    ],
    ids=["digest", "operation", "dataset"],
)
def test_sources_that_disagree_about_the_baseline_are_refused(change):
    first, second = chain()
    source = view(first)
    bound = source.plan.continuation.model_copy(update=change)
    resolve(second, [view(first)])
    refuses(second, [view(first, plan=source.plan.model_copy(update={"continuation": bound}))])


def test_a_root_that_is_not_the_baseline_operation_is_refused():
    first, _ = chain()
    other = build(
        ROOT,
        1,
        status="unknown",
        intents=5,
        acknowledged=4,
        binding={"baseline_operation_id": OTHER},
    )
    assert resolve(first, [])
    refuses(other, [])


def test_a_root_with_no_strict_create_receipt_is_refused():
    first, _ = chain()
    assert resolve(first, [])
    refuses(first, [], created=lambda _: None)


def test_a_root_that_created_another_dataset_is_refused():
    first, _ = chain()
    refuses(first, [], created=lambda _: CREATED.model_copy(update={"id": OTHER}))


def test_a_root_that_made_a_dataset_the_plan_does_not_name_is_refused():
    # The plan's digest is of that other dataset, so only its id disagrees with the plan's.
    other = {**CREATED.model_dump(mode="json"), "id": OTHER}
    first, _ = chain()
    named = build(
        ROOT,
        1,
        status="unknown",
        intents=5,
        acknowledged=4,
        binding={"baseline_digest": sha({"kind": "upload_baseline", "dataset": other})},
    )
    made = CREATED.model_copy(update={"id": OTHER})
    assert resolve(first, [])
    refuses(named, [], created=lambda _: made)


def test_a_root_whose_baseline_digest_differs_is_refused():
    first, _ = chain()
    assert resolve(first, [])
    refuses(first, [], created=lambda _: CREATED.model_copy(update={"name": "renamed"}))


def test_a_v1_root_is_no_source_and_is_refused_as_a_value_error_not_a_crash():
    first, _ = chain()
    v1 = DatasetUploadPlan.model_validate_json(canon(fixture("dataset-upload-plan-v1.json")))
    v2 = ROOT_VIEW.plan
    # The same scope, root, manifest and parameters as the v2 root: only the family differs, and
    # it holds no policy to compare, so the walk must say so instead of failing on the attribute.
    same = v1.model_copy(
        update={
            "scope": v2.scope,
            "root": v2.root,
            "manifest": v2.manifest,
            "parameters": v2.parameters,
        }
    )
    root = SimpleNamespace(plan=same, operation=ROOT_VIEW.operation, receipts=())
    assert resolve(first, [])
    refuses(first, [], root=root)


def test_a_lineage_that_is_verified_only_throughout_is_refused():
    # Every source agrees with the plan, so the comparison of policies alone lets it through; but
    # the policy is inherited, never raised to verified_only, and a verified_only source is not
    # eligible (ADR-0031), so no stored continuation can belong to such a lineage.
    first, second = chain()
    strict = {"admission_policy": "verified_only"}
    root = SimpleNamespace(
        plan=ROOT_VIEW.plan.model_copy(update=strict),
        operation=ROOT_VIEW.operation,
        receipts=(),
    )
    source = view(first)
    sources = {
        ROOT_OPERATION: root,
        FIRST: view(first, plan=source.plan.model_copy(update=strict)),
    }
    plan = view(second).plan.model_copy(update=strict)
    with pytest.raises(ValueError):
        resolve_lineage(plan, sources.__getitem__, lambda _: CREATED)
    # The control: the same walk under the policy the lineage really has resolves.
    ok = {ROOT_OPERATION: ROOT_VIEW, FIRST: source}
    assert resolve_lineage(view(second).plan, ok.__getitem__, lambda _: CREATED)


def test_a_root_of_an_unsupported_plan_type_is_refused():
    first, _ = chain()
    plan = ROOT_VIEW.plan
    imitation = SimpleNamespace(
        manifest=plan.manifest,
        intent_digest=plan.intent_digest,
        root=plan.root,
        parameters=plan.parameters,
        admission_policy=plan.admission_policy,
        cost_policy=plan.cost_policy,
    )
    root = SimpleNamespace(plan=imitation, operation=ROOT_VIEW.operation, receipts=())
    refuses(first, [], root=root)


def test_a_lineage_that_returns_to_the_continuation_itself_loops():
    first, second = chain()
    looping = build(ROOT, 1, status="running", source=SECOND)
    looped = build(ROOT, 2, status="running", source=FIRST, indices=(1,))
    refuses(looping, [view(looped)])
    refuses(looped, [view(looping)])
    assert resolve(second, [view(first)])


def test_a_loop_is_found_at_its_first_repetition_not_at_the_length_bound():
    first = build(ROOT, 1, status="running", source=SECOND)
    second = build(ROOT, 2, status="running", source=FIRST, indices=(1,))
    reads = []
    by_operation = {FIRST: view(first), SECOND: view(second), ROOT_OPERATION: ROOT_VIEW}

    def read(operation_id):
        reads.append(operation_id)
        return by_operation[operation_id]

    view_value = view(first)
    with pytest.raises(ValueError):
        resolve_lineage(view_value.plan, read, lambda _: CREATED)
    assert reads == [SECOND, FIRST]  # the second visit of the first is the repetition


def test_a_lineage_that_loops_without_touching_the_continuation_is_refused():
    # The continuation is a plan only (nothing to find in the walk): two sources chase each other.
    a = build(ROOT, 1, status="running", source=SECOND)
    b = build(ROOT, 2, status="running", source=FIRST, indices=(1,))
    target = build(ROOT, 3, status="running", source=FIRST, indices=(0,))
    refuses(target, [view(a), view(b)])


def test_a_lineage_longer_than_the_store_can_hold_is_refused():
    template = build(ROOT, 1, status="unknown", intents=5, acknowledged=4)
    source = view(template)

    def read(operation_id):
        number = int(operation_id[-12:], 16)
        bound = source.plan.continuation.model_copy(
            update={"source_operation_id": uuid(number + 1)}
        )
        return view(
            template,
            plan=source.plan.model_copy(update={"continuation": bound}),
            operation_id=operation_id,
        )

    plan = source.plan.model_copy(
        update={
            "continuation": source.plan.continuation.model_copy(
                update={"source_operation_id": uuid(0x6000)}
            )
        }
    )
    with pytest.raises(ValueError):
        resolve_lineage(plan, read, lambda _: CREATED)
    assert MAX_LINEAGE == 128


def test_the_length_bound_admits_exactly_that_many_sources(monkeypatch):
    monkeypatch.setattr("yorunge.adapters.upload_lineage.MAX_LINEAGE", 3)
    items = [build(ROOT, 1, status="running")]
    for number in (2, 3, 4):
        items.append(
            build(ROOT, number, status="running", source=uuid(0x300 + number - 1), indices=(2,))
        )
    views = [view(item) for item in items]
    assert len(resolve(items[2], views[:2]).sources) == 3  # two continuations and the root
    refuses(items[3], views[:3])  # a fourth source is one too many


def test_a_journal_is_refused_for_a_plan_of_no_known_family_and_for_no_operation():
    first, _ = chain()
    known = view(first)
    odd = SimpleNamespace(
        plan=SimpleNamespace(), operation=known.operation, intents=(), receipts=()
    )
    with pytest.raises(ValueError):
        journal_of(odd, complete=False)
    view_value = view(first, operation=False)
    with pytest.raises(ValueError):
        journal_of(view_value, complete=False)
    with pytest.raises(YorungeError) as error:
        operation_journal(odd)
    assert error.value.code == "state_invalid"
    assert journal_of(known, complete=True).graph_complete is True
