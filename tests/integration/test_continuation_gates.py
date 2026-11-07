"""The write gates of a continuation, on a real store, a real root and the real repository.

Save, approve and revoke here; admission, the stages and the reads are in the files beside it.
Every history is the interrupted root of ``tests/fixtures/continuation_lifecycle.py`` and plans
built from it with plain hashlib/json; nothing here talks to a network.
"""

import pytest

from tests.fixtures.continuation_lifecycle import ACKNOWLEDGE_ALL
from yorunge.adapters.state import open_store
from yorunge.adapters.upload_store import capacity
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.errors import YorungeError


def code_of(call):
    with pytest.raises(YorungeError) as error:
        call()
    return error.value.code


def rows(store):
    tables = ("upload_namespaces", "upload_manifests", "upload_plans", "upload_approvals")
    tables += ("upload_operations", "upload_controls", "upload_stage_intents")
    return [store.connection.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in tables]


# --- save ----------------------------------------------------------------------------------------


def test_a_continuation_plan_is_saved_beside_its_root_and_makes_no_create_right(lifecycle):
    plan = lifecycle.plan(1)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        before = capacity(store.connection)
        namespaces = store.connection.execute("SELECT * FROM upload_namespaces").fetchall()
        view = lifecycle.repository(store).save(plan, lifecycle.manifest)
        assert type(view.plan) is DatasetContinuationPlanV3 and view.plan == plan
        assert view.operation is None and view.approval is None
        # The root's namespace row is untouched: still the root's create right, no second one.
        assert store.connection.execute("SELECT * FROM upload_namespaces").fetchall() == namespaces
        after = capacity(store.connection)
        assert (after[0], after[1]) == (before[0] + 1, before[1])


def test_saving_the_same_plan_again_is_the_same_plan_and_a_different_one_is_a_conflict(lifecycle):
    plan = lifecycle.plan(1)
    other = lifecycle.plan(1, indices=(2,), uncertain=())  # same id, other content
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        first = repository.save(plan, lifecycle.manifest)
        again = repository.save(plan, lifecycle.manifest)
        assert first == again
        assert code_of(lambda: repository.save(other, lifecycle.manifest)) == "operation_conflict"
        assert capacity(store.connection)[0] == 2  # the root and the one continuation plan


def saved(lifecycle, store, number=1, **spec):
    plan = lifecycle.plan(number, **spec)
    return plan, lifecycle.repository(store).save(plan, lifecycle.manifest)


SAVE_REFUSALS = {
    "a source that is no operation": {"source": "00000000-0000-4000-8000-00000000dead"},
    "a selection the lineage does not allow": {"indices": (0, 2), "uncertain": ()},
    "another baseline than the root made": {"binding": {"baseline_digest": "e" * 64}},
}


@pytest.mark.parametrize("spec", SAVE_REFUSALS.values(), ids=SAVE_REFUSALS)
def test_a_plan_whose_lineage_does_not_hold_is_not_saved_and_leaves_no_trace(lifecycle, spec):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        before = rows(store)
        repository = lifecycle.repository(store)
        refused = lifecycle.plan(1, **spec)
        assert code_of(lambda: repository.save(refused, lifecycle.manifest)) == "state_invalid"
        assert rows(store) == before  # the savepoint of the transaction took the plan row back


def test_a_continuation_is_saved_without_a_preparation_check_and_not_outside_its_window(lifecycle):
    from yorunge.domain.capabilities import instant

    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        plan = lifecycle.plan(1)
        # The create preparation check is for original uploads: a continuation brings none.
        check = repository.capture(plan)
        assert (
            code_of(
                lambda: repository.save(plan, lifecycle.manifest, authorization=check.authorization)
            )
            == "upload_plan_not_valid"
        )
        lifecycle.clock.value = instant("2026-11-02T11:16:00.000000Z")  # after the plan expired
        assert code_of(lambda: repository.save(plan, lifecycle.manifest)) == "upload_plan_not_valid"
        assert capacity(store.connection)[0] == 1  # only the root


def test_a_plan_of_another_credential_is_not_saved(lifecycle):
    scope = dict(lifecycle.root["plan"]["scope"], credential_revision=2)
    other = lifecycle.plan(1, plan_changes={"scope": scope})
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        assert code_of(lambda: repository.save(other, lifecycle.manifest)) == "state_changed"


# --- approve and revoke ---------------------------------------------------------------------------


def test_a_saved_continuation_is_approved_once_with_the_acknowledgements_it_needs(lifecycle):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        plan, _ = saved(lifecycle, store)
        repository = lifecycle.repository(store)
        approval = repository.approve_continuation(
            plan.plan_id, plan.digest, plan, **ACKNOWLEDGE_ALL
        )
        assert type(approval).__name__ == "DatasetUploadApprovalV3"
        assert (approval.plan_id, approval.plan_digest) == (plan.plan_id, plan.digest)
        assert approval.binding_digest == plan.binding_digest()
        assert approval.status == "approved" and approval.expires_at == plan.expires_at
        assert approval.acknowledge_unconfirmed_effects is True  # the plan has an unconfirmed file
        view = repository.show(plan_id=plan.plan_id)
        assert view.approval == approval and view.operation is None
        assert (
            code_of(
                lambda: repository.approve_continuation(
                    plan.plan_id, plan.digest, plan, **ACKNOWLEDGE_ALL
                )
            )
            == "operation_conflict"
        )


NEEDED = (
    "acknowledge_unverified_authority",
    "acknowledge_unpriced_cost",
    "acknowledge_unconfirmed_effects",
)


@pytest.mark.parametrize("missing", NEEDED)
def test_an_approval_needs_each_acknowledgement_the_plan_requires(lifecycle, missing):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        plan, _ = saved(lifecycle, store)
        repository = lifecycle.repository(store)
        flags = {**ACKNOWLEDGE_ALL, missing: False}
        before = rows(store)
        assert (
            code_of(
                lambda: repository.approve_continuation(plan.plan_id, plan.digest, plan, **flags)
            )
            == "approval_required"
        )
        assert rows(store) == before


def test_an_acknowledgement_the_plan_does_not_need_is_refused(lifecycle):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        # Nothing of this plan is unconfirmed: the root's open confirm is left out of the selection.
        plan, _ = saved(lifecycle, store, indices=(2,), uncertain=())
        repository = lifecycle.repository(store)
        assert code_of(
            lambda: repository.approve_continuation(
                plan.plan_id, plan.digest, plan, **ACKNOWLEDGE_ALL
            )
        ) in {"invalid_request", "approval_required"}
        flags = {**ACKNOWLEDGE_ALL, "acknowledge_unconfirmed_effects": False}
        approval = repository.approve_continuation(plan.plan_id, plan.digest, plan, **flags)
        assert approval.acknowledge_unconfirmed_effects is False


def test_an_approval_confirms_exactly_the_plan_digest_and_a_plan_that_is_still_valid(lifecycle):
    from yorunge.domain.capabilities import instant

    with open_store(lifecycle.root_dir, timeout=60) as store:
        plan, _ = saved(lifecycle, store)
        repository = lifecycle.repository(store)
        assert (
            code_of(
                lambda: repository.approve_continuation(
                    plan.plan_id, "0" * 64, plan, **ACKNOWLEDGE_ALL
                )
            )
            == "upload_plan_not_valid"
        )
        # The original-upload approval is not the way to approve a continuation.
        assert (
            code_of(lambda: repository.approve(plan.plan_id, plan.digest, plan))
            == "upload_plan_not_valid"
        )
        lifecycle.clock.value = instant("2026-11-02T11:15:00.000000Z")  # the plan's last instant
        assert (
            code_of(
                lambda: repository.approve_continuation(
                    plan.plan_id, plan.digest, plan, **ACKNOWLEDGE_ALL
                )
            )
            == "upload_plan_not_valid"
        )
        assert repository.show(plan_id=plan.plan_id).approval is None


def test_an_approval_is_revoked_locally_and_a_revoked_one_stays_revoked(lifecycle):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        plan, _ = saved(lifecycle, store)
        repository = lifecycle.repository(store)
        approval = repository.approve_continuation(
            plan.plan_id, plan.digest, plan, **ACKNOWLEDGE_ALL
        )
        assert code_of(lambda: repository.revoke(plan.plan_id, "0" * 64)) == "state_changed"
        view = repository.revoke(plan.plan_id, plan.digest)
        assert type(view.approval).__name__ == "DatasetUploadApprovalV3"
        assert view.approval.status == "revoked" and view.approval.revoked_at is not None
        assert view.approval.approval_id == approval.approval_id
        assert repository.revoke(plan.plan_id, plan.digest).approval == view.approval
