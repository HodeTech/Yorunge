"""The pure v3 builders reproduce the independently generated goldens and refuse what v2 refuses."""

import hashlib
import json
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from yorunge.application.continuation_policy import (
    ContinuationPreparation,
    approve_upload_v3,
    continuation_binding,
    continuation_limits,
    prepare_continuation_v3,
)
from yorunge.application.upload_policy import approve_upload_v2
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.dataset_continuation import (
    ContinuationBinding,
    DatasetContinuationPlanV3,
    DatasetUploadApprovalV3,
    binding_matches,
    validate_approval_binding_v3,
)
from yorunge.domain.dataset_manifest import DatasetManifest, canonical_manifest
from yorunge.domain.dataset_upload import UploadGrant
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_costs import ContinuationCostWork, UploadCostBoundV2
from yorunge.domain.upload_resume import ChainSummary, RemoteInventory, RemoteItem, classify

FIXTURES = Path(__file__).parents[1] / "fixtures"
SOURCE = "00000000-0000-4000-8000-000000000009"
DATASET = "00000000-0000-4000-8000-000000000909"
APPROVAL_ID = "00000000-0000-4000-8000-000000000007"
PLANS = ["plan-v3", "plan-v3-evidenced", "plan-v3-verification-only", "plan-v3-all-files"]


def canon(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode()


def fixture(name):
    return (FIXTURES / f"dataset-continuation-{name}.json").read_bytes()


@contextmanager
def failure(code):
    with pytest.raises(YorungeError) as raised:
        yield
    assert raised.value.code == code


MANIFEST = DatasetManifest.model_validate_json((FIXTURES / "dataset-manifest-v1.json").read_bytes())
MAIN = DatasetContinuationPlanV3.model_validate_json(fixture("plan-v3"))
EVIDENCED = DatasetContinuationPlanV3.model_validate_json(fixture("plan-v3-evidenced"))
CHECK_ONLY = DatasetContinuationPlanV3.model_validate_json(fixture("plan-v3-verification-only"))
WORK_FIELDS = ("scope", "root", "manifest", "parameters", "storage", "request_limits")


def work_of(golden, **changes):
    fields = {name: golden[name] for name in (*WORK_FIELDS, "execution_window")}
    return ContinuationCostWork.model_validate_json(canon({**fields, **changes}))


def request_from(name, **changes):
    """The producer's input that must yield the golden plan ``name``."""
    golden = json.loads(fixture(name))
    grant, cost = golden["grant"], golden["cost_bound"]
    values = {
        "plan_id": golden["plan_id"],
        "work": work_of(golden),
        "manifest": MANIFEST,
        "binding": ContinuationBinding.model_validate_json(canon(golden["continuation"])),
        "admission_policy": golden["admission_policy"],
        "cost_policy": golden["cost_policy"],
        "budget_micros": golden["budget_micros"],
        "inputs_verified": golden["inputs_verified"],
        "grant": UploadGrant.model_validate_json(canon(grant)) if grant else None,
        "cost_bound": UploadCostBoundV2.model_validate_json(canon(cost)) if cost else None,
        "prepared_at": golden["prepared_at"],
    }
    return ContinuationPreparation(**{**values, **changes})


# --- the goldens, rebuilt by production code -----------------------------------------------------
@pytest.mark.parametrize("name", PLANS)
def test_the_builder_reproduces_every_golden_plan_byte_for_byte(name):
    plan = prepare_continuation_v3(request_from(name))
    assert plan.encoded() == fixture(name)
    assert plan.digest == plan.computed_digest() and plan.executable is False
    assert continuation_limits(MANIFEST, plan.continuation.file_indices) == plan.request_limits


@pytest.mark.parametrize(
    "approval,plan", [("approval-v3", MAIN), ("approval-v3-evidenced", EVIDENCED)]
)
def test_the_approval_builder_reproduces_both_golden_approvals(approval, plan):
    golden = json.loads(fixture(approval))
    built = approve_upload_v3(
        plan,
        approval_id=golden["approval_id"],
        confirmed_digest=plan.digest,
        approved_at=golden["approved_at"],
        acknowledge_unverified_authority=golden["acknowledge_unverified_authority"],
        acknowledge_unpriced_cost=golden["acknowledge_unpriced_cost"],
        acknowledge_unconfirmed_effects=golden["acknowledge_unconfirmed_effects"],
    )
    assert built.encoded() == fixture(approval)
    validate_approval_binding_v3(plan, built)


# --- request limits ------------------------------------------------------------------------------
# The manifest holds a.txt (3 bytes), empty.bin (0 bytes) and ölçüm.txt (5 bytes).
@pytest.mark.parametrize(
    "indices,size",
    [
        ((), 0),
        ((0,), 3),
        ((1,), 0),
        ((2,), 5),
        ((0, 1), 3),
        ((0, 2), 8),
        ((1, 2), 5),
        ((0, 1, 2), 8),
    ],
)
def test_limits_count_the_selected_files_and_their_exact_bytes(indices, size):
    limits = continuation_limits(MANIFEST, indices)
    assert (limits.max_presign, limits.max_put, limits.max_confirm) == (len(indices),) * 3
    assert (limits.max_create, limits.max_project_link) == (0, 0)
    assert limits.max_upload_bytes == size and limits.files == len(indices)
    assert (limits.max_read_requests, limits.max_read_attempts) == (512, 1024)
    assert limits.max_control_request_bytes == 4 * 1024 * 1024
    assert limits.max_control_response_bytes == 16 * 1024 * 1024
    assert limits == continuation_limits(MANIFEST, list(indices))


@pytest.mark.parametrize(
    "indices",
    [(1, 0), (0, 0), (-1,), (3,), (0, 1, 2, 3), (True,), ("0",), (0.0,), (None,)],
)
def test_limits_refuse_unordered_repeated_foreign_and_untyped_indices(indices):
    with pytest.raises(ValueError, match="ordered distinct manifest file indices"):
        continuation_limits(MANIFEST, indices)


# --- the binding of a classification -------------------------------------------------------------
def classified(*, states, present=(), faults=()):
    chain = ChainSummary(states, False, False, MANIFEST.digest)
    items = tuple(
        RemoteItem(f.path, f.size, f.sha256, f"item-{i}")
        for i, f in enumerate(MANIFEST.files)
        if i in present
    )
    return classify(MANIFEST, chain, RemoteInventory(items, frozenset(faults)))


def bound(classification, **changes):
    values = {
        "source_operation_id": SOURCE,
        "baseline_operation_id": SOURCE,
        "dataset_id": DATASET,
        "baseline_digest": "b" * 64,
        "intent_digest": MAIN.intent_digest(),
        "observed_at": "2026-11-02T11:00:00.000000Z",
    }
    return continuation_binding(classification, **{**values, **changes})


CASES = {
    "mixed": dict(states=("none", "none", "intent"), present=(1,)),
    "nothing_sent": dict(states=("none", "none", "none")),
    "everything_confirmed": dict(states=("accepted", "accepted", "accepted"), present=(0, 1, 2)),
    "one_unconfirmed": dict(states=("accepted", "accepted", "intent"), present=(0, 1)),
}


@pytest.mark.parametrize("case", CASES)
def test_a_binding_built_from_a_classification_matches_that_classification(case):
    classification = classified(**CASES[case])
    binding = bound(classification)
    selection = classification.selection()
    assert (binding.file_indices, binding.uncertain_indices, binding.remote_present_count) == (
        selection.file_indices,
        selection.uncertain_indices,
        selection.remote_present_count,
    )
    assert binding.classification_digest == classification.classification_digest
    assert binding.inventory_digest == classification.inventory_digest
    assert binding_matches(binding, classification)
    assert binding_matches(binding, classified(**CASES[case]))


def test_the_selections_of_the_four_cases_are_the_expected_ones():
    expected = {
        "mixed": ((0, 2), (2,), 1),
        "nothing_sent": ((0, 1, 2), (), 0),
        "everything_confirmed": ((), (), 3),
        "one_unconfirmed": ((2,), (2,), 2),
    }
    for case, (files, uncertain, present) in expected.items():
        binding = bound(classified(**CASES[case]))
        assert (binding.file_indices, binding.uncertain_indices, binding.remote_present_count) == (
            files,
            uncertain,
            present,
        )


def test_the_binding_carries_the_identities_it_is_given():
    binding = bound(
        classified(**CASES["mixed"]),
        source_operation_id="00000000-0000-4000-8000-00000000000a",
        baseline_operation_id="00000000-0000-4000-8000-00000000000b",
        dataset_id="00000000-0000-4000-8000-00000000090a",
        baseline_digest="c" * 64,
        intent_digest="d" * 64,
        observed_at="2026-11-02T11:00:01.000000Z",
    )
    assert binding.source_operation_id == "00000000-0000-4000-8000-00000000000a"
    assert binding.baseline_operation_id == "00000000-0000-4000-8000-00000000000b"
    assert binding.dataset_id == "00000000-0000-4000-8000-00000000090a"
    assert (binding.baseline_digest, binding.intent_digest) == ("c" * 64, "d" * 64)
    assert binding.observed_at == "2026-11-02T11:00:01.000000Z"


def test_a_blocked_classification_cannot_be_bound():
    blocked = classified(**CASES["mixed"], faults=("cursor_loop",))
    assert blocked.selection() is None
    with pytest.raises(ValueError, match="blockers cannot be bound"):
        bound(blocked)
    with pytest.raises(ValueError, match="blockers cannot be bound"):
        bound(classified(**CASES["mixed"]).with_blockers(("source_superseded",)))


@pytest.mark.parametrize("case", CASES)
def test_a_classification_flows_through_limits_and_binding_into_a_valid_plan(case):
    binding = bound(classified(**CASES[case]))
    work = ContinuationCostWork(
        scope=MAIN.scope,
        root=MAIN.root,
        manifest=MAIN.manifest,
        parameters=MAIN.parameters,
        storage=MAIN.storage,
        request_limits=continuation_limits(MANIFEST, binding.file_indices),
        execution_window=MAIN.execution_window,
    )
    plan = prepare_continuation_v3(request_from("plan-v3", work=work, binding=binding))
    assert plan.continuation == binding and plan.request_limits.files == len(binding.file_indices)
    approval = approve_upload_v3(
        plan,
        approval_id=APPROVAL_ID,
        confirmed_digest=plan.digest,
        approved_at="2026-11-02T11:00:01.000000Z",
        acknowledge_unverified_authority=True,
        acknowledge_unpriced_cost=True,
        acknowledge_unconfirmed_effects=bool(binding.uncertain_indices),
    )
    validate_approval_binding_v3(plan, approval)


# --- sealing a plan ------------------------------------------------------------------------------
def changed_manifest():
    data = json.loads((FIXTURES / "dataset-manifest-v1.json").read_bytes())
    del data["digest"]
    data["files"][0]["size"] += 1
    data["total_bytes"] += 1
    digest = hashlib.sha256(canonical_manifest(data)).hexdigest()
    return DatasetManifest.model_validate_json(canon({**data, "digest": digest}))


def test_a_manifest_that_is_not_the_planned_one_is_input_changed():
    with failure("input_changed"):
        prepare_continuation_v3(request_from("plan-v3", manifest=changed_manifest()))


def test_selected_bytes_that_are_not_the_selected_files_are_refused():
    golden = json.loads(fixture("plan-v3"))
    limits = {**golden["request_limits"], "max_upload_bytes": 7}  # files 0 and 2 hold 8 bytes
    work = work_of(golden, request_limits=limits)
    with pytest.raises(ValueError, match="selected file bytes differ"):
        prepare_continuation_v3(request_from("plan-v3", work=work))


def expiring(value, moment):
    return type(value).model_validate_json(
        canon({**value.model_dump(mode="json"), "expires_at": moment})
    )


def test_the_plan_lives_as_long_as_its_window_and_its_shortest_evidence_allow():
    assert EVIDENCED.expires_at == EVIDENCED.execution_window.not_after  # nothing is shorter
    request = request_from("plan-v3-evidenced")
    early, late = "2026-11-02T11:10:00.000000Z", "2026-11-02T11:12:00.000000Z"
    for grant_end, cost_end, expected in (
        (early, None, early),
        (None, late, late),
        (early, late, early),
        (late, early, early),
    ):
        grant = expiring(request.grant, grant_end) if grant_end else request.grant
        cost = expiring(request.cost_bound, cost_end) if cost_end else request.cost_bound
        plan = prepare_continuation_v3(
            request_from("plan-v3-evidenced", grant=grant, cost_bound=cost)
        )
        assert plan.expires_at == expected and plan.digest == plan.computed_digest()


def test_a_plan_needs_a_moment_inside_its_window_and_inside_its_evidence():
    request = request_from("plan-v3-evidenced")
    spent = expiring(request.grant, "2026-11-02T11:00:00.000000Z")  # as the plan is prepared
    for changes in (
        {"prepared_at": "2026-11-02T10:59:59.999999Z"},  # before the window opens
        {"prepared_at": "2026-11-02T11:15:00.000000Z"},  # when it closes: no lifetime left
        {"grant": spent},
    ):
        with pytest.raises((ValidationError, ValueError)):
            prepare_continuation_v3(request_from("plan-v3-evidenced", **changes))


def test_the_policy_decides_status_risks_and_blockers_like_it_does_for_v2():
    prepared = prepare_continuation_v3(request_from("plan-v3-evidenced"))
    assert (prepared.status, prepared.risks, prepared.blockers) == ("prepared", (), ())
    attempt = prepare_continuation_v3(request_from("plan-v3"))
    assert attempt.status == "attempt_ready"
    assert attempt.risks == ("authority_unverified", "cost_unverified")
    draft = prepare_continuation_v3(request_from("plan-v3", inputs_verified=False))
    assert (draft.status, draft.blockers) == ("draft", ("inputs_unverified",))
    strict = prepare_continuation_v3(
        request_from(
            "plan-v3",
            admission_policy="verified_only",
            cost_policy="bounded_required",
            budget_micros=5,
        )
    )
    assert strict.status == "draft"
    assert strict.blockers == ("authority_unverified", "cost_unverified")


def test_a_policy_choice_the_policy_cannot_state_is_an_invalid_request():
    with failure("invalid_request"):
        prepare_continuation_v3(
            request_from(
                "plan-v3", admission_policy="verified_only", cost_policy="unpriced_accepted"
            )
        )
    with failure("invalid_request"):
        prepare_continuation_v3(
            request_from("plan-v3", cost_policy="bounded_required", budget_micros=None)
        )


def test_the_observation_instant_is_kept_as_observed_when_the_plan_is_prepared_later():
    later = prepare_continuation_v3(
        request_from("plan-v3", prepared_at="2026-11-02T11:00:02.000000Z")
    )
    assert later.prepared_at == "2026-11-02T11:00:02.000000Z"
    assert later.continuation.observed_at == "2026-11-02T11:00:00.000000Z"
    assert later.binding_digest() == MAIN.binding_digest()  # a later preparation binds the same


def test_sealing_is_deterministic_and_the_identity_stays_out_of_the_binding():
    first, second = (prepare_continuation_v3(request_from("plan-v3")) for _ in range(2))
    assert first.encoded() == second.encoded() and first == second
    other = prepare_continuation_v3(
        request_from("plan-v3", plan_id="00000000-0000-4000-8000-000000000066")
    )
    assert other.digest != first.digest and other.binding_digest() == first.binding_digest()


# --- approving a plan ----------------------------------------------------------------------------
def approve(plan=MAIN, **changes):
    values = {
        "approval_id": APPROVAL_ID,
        "confirmed_digest": plan.digest,
        "approved_at": "2026-11-02T11:00:01.000000Z",
        "acknowledge_unverified_authority": True,
        "acknowledge_unpriced_cost": True,
        "acknowledge_unconfirmed_effects": True,
    }
    return approve_upload_v3(plan, **{**values, **changes})


def test_an_approval_takes_everything_it_binds_from_the_plan():
    approval = approve()
    assert isinstance(approval, DatasetUploadApprovalV3)
    assert approval.approval_id == APPROVAL_ID
    assert (approval.plan_id, approval.plan_digest, approval.binding_digest) == (
        MAIN.plan_id,
        MAIN.digest,
        MAIN.binding_digest(),
    )
    assert (approval.store_id, approval.identity_epoch, approval.clock_generation) == (
        MAIN.scope.store_id,
        MAIN.scope.identity_epoch,
        MAIN.scope.clock_generation,
    )
    assert (approval.admission_policy, approval.cost_policy) == (
        MAIN.admission_policy,
        MAIN.cost_policy,
    )
    assert approval.expires_at == MAIN.expires_at
    assert (approval.status, approval.revoked_at) == ("approved", None)


def test_an_approval_exists_only_from_the_plans_start_until_just_before_its_end():
    assert approve(approved_at=MAIN.prepared_at).approved_at == MAIN.prepared_at
    last = timestamp(instant(MAIN.expires_at) - timedelta(microseconds=1))
    assert approve(approved_at=last).approved_at == last
    for moment in (
        "2026-11-01T23:59:59.999999Z",
        "2026-11-02T10:59:59.999999Z",
        MAIN.expires_at,
        "2026-11-02T11:15:00.000001Z",
    ):
        with failure("upload_plan_not_valid"):
            approve(approved_at=moment)
    with pytest.raises(ValueError):
        approve(approved_at="not an instant")


def test_a_draft_or_an_unconfirmed_plan_is_not_approved():
    draft = prepare_continuation_v3(request_from("plan-v3", inputs_verified=False))
    with failure("upload_plan_not_valid"):
        approve(draft)
    for digest in ("0" * 64, MAIN.digest.upper(), "", MAIN.binding_digest()):
        with failure("upload_plan_not_valid"):
            approve(confirmed_digest=digest)


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"acknowledge_unverified_authority": False}, "approval_required"),
        ({"acknowledge_unpriced_cost": False}, "approval_required"),
        ({"acknowledge_unconfirmed_effects": False}, "approval_required"),
        ({"acknowledge_unconfirmed_effects": 1}, "invalid_request"),
        ({"acknowledge_unpriced_cost": None}, "invalid_request"),
        ({"acknowledge_unverified_authority": "yes"}, "invalid_request"),
    ],
)
def test_the_needed_acknowledgements_are_exactly_those_the_plan_requires(changes, code):
    with failure(code):
        approve(**changes)


def test_unneeded_acknowledgements_are_invalid_and_are_judged_before_missing_ones():
    none = NO_ACKS
    approve(EVIDENCED, **none)  # no risk and no uncertain file: nothing to acknowledge
    for flag in none:
        with failure("invalid_request"):
            approve(EVIDENCED, **{**none, flag: True})
    # A check-only plan needs the two v2 acknowledgements but never the third. Offering the third
    # while leaving the first out is an unrelated request, not a missing consent.
    approve(
        CHECK_ONLY,
        **{**none, "acknowledge_unverified_authority": True, "acknowledge_unpriced_cost": True},
    )
    with failure("invalid_request"):
        approve(
            CHECK_ONLY,
            **{**none, "acknowledge_unconfirmed_effects": True, "acknowledge_unpriced_cost": True},
        )


NO_ACKS = dict(
    acknowledge_unverified_authority=False,
    acknowledge_unpriced_cost=False,
    acknowledge_unconfirmed_effects=False,
)


def test_an_approval_never_outlives_a_plan_that_its_evidence_shortened():
    request = request_from("plan-v3-evidenced")
    short = prepare_continuation_v3(
        request_from(
            "plan-v3-evidenced", grant=expiring(request.grant, "2026-11-02T11:10:00.000000Z")
        )
    )
    assert short.expires_at == "2026-11-02T11:10:00.000000Z" != short.execution_window.not_after
    assert approve(short, **NO_ACKS).expires_at == short.expires_at


def test_an_approval_copies_the_policy_and_the_clock_generation_of_the_plan_it_binds():
    # Values the goldens never use: a strict admission policy and a later clock generation.
    strict = prepare_continuation_v3(
        request_from("plan-v3-evidenced", admission_policy="verified_only")
    )
    assert (strict.status, strict.admission_policy) == ("prepared", "verified_only")
    assert approve(strict, **NO_ACKS).admission_policy == "verified_only"
    golden = json.loads(fixture("plan-v3"))
    later = work_of(golden, scope={**golden["scope"], "clock_generation": 2})
    plan = prepare_continuation_v3(request_from("plan-v3", work=later))
    assert approve(plan).clock_generation == 2


def test_only_a_genuine_v3_plan_is_approved_by_the_v3_builder_and_never_by_the_v2_one():
    v2 = DatasetUploadPlanV2.model_validate_json(
        (FIXTURES / "dataset-upload-plan-v2.json").read_bytes()
    )

    class Imitation(DatasetContinuationPlanV3):
        pass

    imitation = Imitation.model_construct(**dict(MAIN))
    for impostor in (v2, imitation, None, {"digest": MAIN.digest}, object()):
        with failure("upload_plan_not_valid"):
            approve_upload_v3(
                impostor,
                approval_id=APPROVAL_ID,
                confirmed_digest=MAIN.digest,
                approved_at="2026-11-02T11:00:01.000000Z",
                acknowledge_unverified_authority=True,
                acknowledge_unpriced_cost=True,
                acknowledge_unconfirmed_effects=True,
            )
    for impostor in (MAIN, imitation, None, {"digest": MAIN.digest}):
        with failure("upload_plan_not_valid"):
            approve_upload_v2(
                impostor,
                approval_id=APPROVAL_ID,
                confirmed_digest=MAIN.digest,
                approved_at="2026-11-02T11:00:01.000000Z",
                acknowledge_unverified_authority=True,
                acknowledge_unpriced_cost=True,
            )


def test_a_plan_changed_after_sealing_cannot_be_approved_even_when_its_old_digest_is_confirmed():
    stale = MAIN.model_copy(update={"budget_micros": 1})
    with pytest.raises(ValueError, match="plan digest mismatch"):
        approve(stale, confirmed_digest=stale.digest)
