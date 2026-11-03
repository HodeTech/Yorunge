"""Literal policy matrix, approval UX and immutable current-evidence boundaries."""

import hashlib
import json
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

import pytest

from yorunge.application.upload_policy import (
    UploadPreparationV2,
    approve_upload_v2,
    parse_budget_cr,
    prepare_upload_v2,
)
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_upload import REQUIRED_PERMISSIONS, UploadGrant
from yorunge.domain.dataset_upload_v2 import (
    DatasetUploadApprovalV2,
    DatasetUploadPlanV2,
    validate_approval_binding_v2,
)
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_checks import (
    AuthorizationCheck,
    UploadCurrentCheck,
    UploadObservation,
    mandatory_http_failure,
)
from yorunge.domain.upload_costs import UploadCostBoundV2, UploadCostWork

FIXTURES = Path(__file__).parents[1] / "fixtures"
NOW = "2026-11-02T11:00:02.000000Z"
CHECKED = "2026-11-02T11:00:01.000000Z"
DATASET = "00000000-0000-4000-8000-000000000009"
PROFILE = "evren-platform-observed-upload-v2"
MATRIX = json.loads((FIXTURES / "dataset-upload-policy-matrix-v2.json").read_bytes())


@contextmanager
def failure(code):
    with pytest.raises(YorungeError) as raised:
        yield
    assert raised.value.code == code


def encode(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode()


def fixture(name):
    return (FIXTURES / name).read_bytes()


def grant_for(work, kind):
    if kind == "none":
        return None
    return UploadGrant(
        schema_version=1,
        scope=work.scope,
        permissions=REQUIRED_PERMISSIONS if kind == "full" else ("create_private_dataset",),
        producer_id="fixture_only",
        producer_version="2",
        checked_at="2026-11-02T10:59:59.000000Z",
        expires_at=work.execution_window.not_after,
    )


def cost_for(kind):
    if kind == "none":
        return None
    data = json.loads(fixture("dataset-upload-cost-bound-v2.json"))
    if kind.startswith("partial"):
        data["charge_categories"] = ["transfer"]
    data["maximum_micros"] = 201_000_000 if kind.endswith("over") else 1_000_000
    return UploadCostBoundV2.model_validate_json(encode(data))


def prepare(
    *,
    admission_policy="explicit_attempt",
    cost_policy="unpriced_accepted",
    grant="none",
    cost="none",
    inputs=True,
    **updates,
):
    work = UploadCostWork.model_validate_json(fixture("dataset-upload-cost-work-v2.json"))
    fields = dict(
        plan_id="00000000-0000-4000-8000-000000000006",
        work=work,
        manifest=DatasetManifest.model_validate_json(fixture("dataset-manifest-v1.json")),
        admission_policy=admission_policy,
        cost_policy=cost_policy,
        budget_micros=200_000_000 if cost_policy == "bounded_required" else None,
        inputs_verified=inputs,
        grant=grant_for(work, grant),
        cost_bound=cost_for(cost),
        prepared_at=work.execution_window.not_before,
    )
    return prepare_upload_v2(UploadPreparationV2(**{**fields, **updates}))


def approve(plan, authority=True, unpriced=True, **updates):
    fields = dict(
        approval_id="00000000-0000-4000-8000-000000000007",
        confirmed_digest=plan.digest,
        approved_at=CHECKED,
        acknowledge_unverified_authority=authority,
        acknowledge_unpriced_cost=unpriced,
    )
    return approve_upload_v2(plan, **{**fields, **updates})


def authorization(plan, **updates):
    data = dict(
        consumer_profile=PROFILE,
        policy_version=2,
        action="create_private_dataset",
        scope=plan.scope,
        dataset_id=None,
        producer_id="fixture_only",
        producer_version="2",
        checked_at=CHECKED,
        outcome="not_exposed",
        grant=None,
        error_code=None,
    )
    return AuthorizationCheck(**{**data, **updates})


def current(plan, **updates):
    data = dict(
        saved_plan_id=plan.plan_id,
        saved_plan_digest=plan.digest,
        saved_binding_digest=plan.binding_digest(),
        work_digest=plan.cost_work().digest(),
        scope=plan.scope,
        checked_at=CHECKED,
        baseline_grant=plan.grant,
        baseline_cost_bound=plan.cost_bound,
        supplemental_grant=None,
        supplemental_cost_bound=None,
        authorization=authorization(plan),
        inputs_verified=True,
        upload_observation=None,
    )
    return UploadCurrentCheck(**{**data, **updates})


def require(check, plan, **updates):
    check.require_current(
        plan, **{**dict(now=NOW, action="create_private_dataset", dataset_id=None), **updates}
    )


def test_independent_plan_approval_golden_bytes_and_digests():
    plan = prepare()
    assert plan.encoded() == fixture("dataset-upload-plan-v2.json")
    assert plan.digest == "af330ada6632237fdfca9d42b06e3475f720517d06a4eb80547fdc14d74f11d6"
    assert (
        plan.binding_digest() == "3bd869f9103eae4e8b26a2b79cf66210f54224ef8ae3b79b524952ba8e6aa3e3"
    )
    approval = approve(plan)
    assert approval.encoded() == fixture("dataset-upload-approval-v2.json")
    validate_approval_binding_v2(plan, approval)


@pytest.mark.parametrize("row", MATRIX)
def test_all_96_independent_literal_policy_proof_budget_input_rows(row):
    kwargs = {k: row[k] for k in ("admission_policy", "cost_policy", "grant", "cost", "inputs")}
    if row["error"] is not None:
        with failure(row["error"]):
            prepare(**kwargs)
        return
    plan = prepare(**kwargs)
    assert plan.status == row["status"]
    assert list(plan.risks) == row["risks"]
    assert list(plan.blockers) == row["blockers"]
    if plan.status == "draft":
        assert row["ack_authority"] is row["ack_cost"] is None
        with failure("upload_plan_not_valid"):
            approve(plan, authority=False, unpriced=False)
    else:
        result = approve(plan, row["ack_authority"], row["ack_cost"])
        validate_approval_binding_v2(plan, result)


def test_matrix_has_full_independent_cartesian_coverage():
    assert len(MATRIX) == len({encode(row) for row in MATRIX}) == 96
    assert Counter(row["status"] or "invalid" for row in MATRIX) == {
        "draft": 65,
        "prepared": 2,
        "attempt_ready": 11,
        "invalid": 18,
    }
    eligible = [row for row in MATRIX if row["status"] in ("prepared", "attempt_ready")]
    assert sum(row["ack_cost"] for row in eligible) == 9
    assert sum(row["ack_authority"] for row in eligible) == 8


@pytest.mark.parametrize(
    "authority,unpriced,error",
    [
        (False, True, "approval_required"),
        (True, False, "approval_required"),
        (1, True, "invalid_request"),
    ],
)
def test_required_ack_flags_are_not_inferred(authority, unpriced, error):
    plan = prepare()
    with failure(error):
        approve(plan, authority, unpriced)


def test_wrong_confirm_digest_is_invalid_plan_not_missing_acknowledgement():
    plan = prepare()
    with failure("upload_plan_not_valid"):
        approve(plan, confirmed_digest="0" * 64)


@pytest.mark.parametrize("authority,unpriced", [(True, False), (False, True), (True, True)])
def test_unnecessary_ack_is_argument_error(authority, unpriced):
    plan = prepare(grant="full", cost="complete", cost_policy="bounded_required")
    with failure("invalid_request"):
        approve(plan, authority, unpriced)


@pytest.mark.parametrize(
    "value", ["-1", "1e2", "NaN", "1.0000001", " 1", "1.", ".1", True, 1.0, "9223372036854.775808"]
)
def test_money_rejects_coercion_rounding_and_overflow(value):
    with failure("invalid_request"):
        parse_budget_cr(value)


@pytest.mark.parametrize(
    "value,expected",
    [("0", 0), ("200", 200_000_000), ("0.000001", 1), ("9223372036854.775807", 2**63 - 1)],
)
def test_exact_microcredits(value, expected):
    assert parse_budget_cr(value) == expected


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("policy_version", True),
        ("inputs_verified", 1),
        ("budget_micros", 1.0),
        ("executable", 0),
        ("risks", []),
        ("status", "prepared"),
        ("extra", None),
    ],
)
def test_v2_plan_wire_rejects_invalid_type_or_reducer_even_with_resealed_digest(field, value):
    data = json.loads(fixture("dataset-upload-plan-v2.json"))
    data[field] = value
    data.pop("digest")
    data["digest"] = hashlib.sha256(encode(data)).hexdigest()
    raw = encode(data)
    with pytest.raises(ValueError):
        DatasetUploadPlanV2.model_validate_json(raw)


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", 1),
        ("acknowledge_unverified_authority", 1),
        ("acknowledge_unpriced_cost", False),
        ("admission_policy", "verified_only"),
        ("cost_policy", "bounded_required"),
        ("extra", 1),
    ],
)
def test_v2_approval_wire_strict_and_closed(field, value):
    data = json.loads(fixture("dataset-upload-approval-v2.json"))
    data[field] = value
    raw = encode(data)
    with pytest.raises(ValueError):
        DatasetUploadApprovalV2.model_validate_json(raw)


def test_current_new_positive_evidence_never_rewrites_saved_plan_or_approval():
    plan = prepare()
    approval = approve(plan)
    before = plan.encoded(), approval.encoded()
    check = current(
        plan,
        supplemental_grant=grant_for(plan.cost_work(), "full"),
        supplemental_cost_bound=cost_for("complete"),
    )
    assert check.baseline_grant is check.baseline_cost_bound is None
    require(check, plan)
    assert before == (plan.encoded(), approval.encoded())
    assert plan.risks == ("authority_unverified", "cost_unverified")


def test_current_partial_grant_and_cost_keep_baseline_and_separate_supplemental():
    plan = prepare(grant="partial", cost="partial")
    check = current(
        plan,
        supplemental_grant=grant_for(plan.cost_work(), "full"),
        supplemental_cost_bound=cost_for("complete"),
    )
    require(check, plan)
    assert check.baseline_grant.permissions == ("create_private_dataset",)
    assert check.baseline_cost_bound.charge_categories == ("transfer",)
    swapped = current(plan, baseline_grant=grant_for(plan.cost_work(), "full"))
    with failure("upload_plan_not_valid"):
        require(swapped, plan)


@pytest.mark.parametrize("field", ["baseline_grant", "baseline_cost_bound"])
def test_current_full_evidence_cannot_disappear(field):
    plan = prepare(grant="full", cost="complete", cost_policy="bounded_required")
    check = current(plan, **{field: None})
    with failure("upload_plan_not_valid"):
        require(check, plan)


def test_cost_source_amount_and_period_are_immutable_semantics():
    plan = prepare(cost="partial")
    for field, changed in [
        ("maximum_micros", 2),
        ("source_version", "3"),
        ("charge_period_end", "2026-11-02T11:14:00.000000Z"),
    ]:
        data = plan.cost_bound.model_dump(mode="json")
        data[field] = changed
        bound = UploadCostBoundV2.model_validate_json(encode(data))
        check = current(plan, baseline_cost_bound=bound)
        with failure("upload_plan_not_valid"):
            require(check, plan)


@pytest.mark.parametrize(
    "now",
    ["2026-11-02T11:00:00.000000Z", "2026-11-02T11:00:31.000001Z", "2026-11-02T11:15:00.000000Z"],
)
def test_current_rejects_future_stale_and_expired_probes(now):
    plan = prepare()
    check = current(plan)
    with failure("upload_plan_not_valid"):
        require(check, plan, now=now)


def test_current_scope_input_and_action_changes_are_not_a_positive_refresh():
    plan = prepare()
    for changes in [
        dict(inputs_verified=False),
        dict(scope=plan.scope.model_copy(update={"credential_revision": 2})),
        dict(authorization=authorization(plan, action="link_project")),
    ]:
        check = current(plan, **changes)
        with failure("state_changed"):
            require(check, plan)


@pytest.mark.parametrize(
    "status,outcome,code",
    [
        (401, "denied", "remote_access_denied"),
        (403, "denied", "remote_access_denied"),
        (404, "invalid", "invalid_response"),
        (405, "invalid", "invalid_response"),
        (302, "invalid", "invalid_response"),
        (429, "unavailable", "remote_rate_limited"),
        (500, "unavailable", "remote_failed"),
        (503, "unavailable", "remote_failed"),
    ],
)
def test_mandatory_http_failures_never_become_not_exposed(status, outcome, code):
    assert mandatory_http_failure(status) == (outcome, code)
    plan = prepare()
    check = current(plan, authorization=authorization(plan, outcome=outcome, error_code=code))
    with failure(code):
        require(check, plan)


@pytest.mark.parametrize(
    "outcome,error",
    [
        ("allowed", None),
        ("not_exposed", "invalid_response"),
        ("denied", None),
        ("unavailable", "remote_access_denied"),
        ("invalid", "remote_failed"),
    ],
)
def test_check_outcome_and_error_catalog_cannot_weaken_failure(outcome, error):
    plan = prepare()
    with pytest.raises(ValueError):
        authorization(plan, outcome=outcome, error_code=error)


def test_upload_observation_is_required_fresh_and_never_a_grant():
    plan = prepare()
    auth = authorization(plan, action="upload_created_dataset", dataset_id=DATASET)
    check = current(plan, authorization=auth)
    with failure("upload_plan_not_valid"):
        require(check, plan, action="upload_created_dataset", dataset_id=DATASET)
    obs = UploadObservation(
        consumer_profile=PROFILE,
        policy_version=2,
        scope=plan.scope,
        dataset_id=DATASET,
        checked_at=CHECKED,
        has_upload=True,
    )
    check = current(plan, authorization=auth, upload_observation=obs)
    require(check, plan, action="upload_created_dataset", dataset_id=DATASET)
    assert plan.grant is None
    assert auth.outcome == "not_exposed"
    denied = current(
        plan, authorization=auth, upload_observation=obs.model_copy(update={"has_upload": False})
    )
    with failure("remote_access_denied"):
        require(denied, plan, action="upload_created_dataset", dataset_id=DATASET)


def test_verified_policy_requires_real_current_action_grant():
    plan = prepare(
        admission_policy="verified_only",
        cost_policy="bounded_required",
        grant="full",
        cost="complete",
    )
    absent = current(plan)
    with failure("upload_plan_not_valid"):
        require(absent, plan)
    allowed = authorization(plan, outcome="allowed", grant=plan.grant)
    require(current(plan, authorization=allowed), plan)
    assert allowed.grant is plan.grant


def test_current_action_grant_expiry_is_also_an_arm_deadline_term():
    plan = prepare()
    data = grant_for(plan.cost_work(), "full").model_dump(mode="json")
    data["expires_at"] = "2026-11-02T11:00:02.500000Z"
    short = UploadGrant.model_validate_json(encode(data))
    check = current(plan, authorization=authorization(plan, outcome="allowed", grant=short))
    expiries = check.require_current(
        plan, now=NOW, action="create_private_dataset", dataset_id=None
    )
    assert expiries == (short.expires_at,)


@pytest.mark.parametrize("field", ["baseline_grant", "baseline_cost_bound"])
def test_expired_baseline_cannot_be_replaced_with_supplemental_full_proof(field):
    plan = prepare(grant="partial", cost="partial")
    original = getattr(plan, "grant" if field == "baseline_grant" else "cost_bound")
    data = original.model_dump(mode="json")
    data["expires_at"] = CHECKED
    expired = type(original).model_validate_json(encode(data))
    check = current(
        plan,
        **{field: expired},
        supplemental_grant=grant_for(plan.cost_work(), "full"),
        supplemental_cost_bound=cost_for("complete"),
    )
    with failure("upload_plan_not_valid"):
        require(check, plan)


@pytest.mark.parametrize("field", ["baseline_grant", "baseline_cost_bound"])
def test_null_baseline_is_not_silently_replaced_with_new_positive(field):
    plan = prepare()
    positive = (
        grant_for(plan.cost_work(), "full") if field == "baseline_grant" else cost_for("complete")
    )
    check = current(plan, **{field: positive})
    with failure("upload_plan_not_valid"):
        require(check, plan)


def test_supplemental_wrong_work_is_safe_plan_error_not_a_type_leak():
    plan = prepare()
    data = cost_for("complete").model_dump(mode="json")
    data["work_digest"] = "a" * 64
    wrong = UploadCostBoundV2.model_validate_json(encode(data))
    check = current(plan, supplemental_cost_bound=wrong)
    with failure("upload_plan_not_valid"):
        require(check, plan)


def test_refreshed_current_timestamps_preserve_binding_but_not_historical_expiry():
    plan = prepare(grant="full", cost="complete", cost_policy="bounded_required")
    data = plan.grant.model_dump(mode="json")
    data["checked_at"] = CHECKED
    refreshed = UploadGrant.model_validate_json(encode(data))
    check = current(plan, baseline_grant=refreshed)
    original = plan.encoded()
    require(check, plan)
    assert original == plan.encoded()
    with failure("upload_plan_not_valid"):
        require(check, plan, now=plan.expires_at)


@pytest.mark.parametrize(
    "field,value",
    [
        ("acknowledge_unverified_authority", False),
        ("plan_digest", "a" * 64),
        ("binding_digest", "b" * 64),
        ("cost_policy", "bounded_required"),
    ],
)
def test_saved_approval_binding_mismatch_is_rejected(field, value):
    plan = prepare()
    data = approve(plan).model_dump(mode="json")
    data[field] = value
    if field == "cost_policy":
        data["acknowledge_unpriced_cost"] = False
    altered = DatasetUploadApprovalV2.model_validate_json(encode(data))
    with pytest.raises(ValueError, match="mismatch"):
        validate_approval_binding_v2(plan, altered)


@pytest.mark.parametrize(
    "model,path,key",
    [
        (DatasetUploadPlanV2, "dataset-upload-plan-v2.json", "status"),
        (DatasetUploadApprovalV2, "dataset-upload-approval-v2.json", "approved_at"),
    ],
)
def test_v2_valid_payload_duplicate_and_size_guards(model, path, key):
    raw = fixture(path)
    data = json.loads(raw)
    duplicate = raw[:-1] + b"," + encode(key) + b":" + encode(data[key]) + b"}"
    assert json.loads(duplicate) == data
    with pytest.raises(ValueError, match="duplicate"):
        model.model_validate_json(duplicate)
    padded = b" " * (16 * 1024) + raw
    assert json.loads(padded) == data
    with pytest.raises(ValueError, match="bounded upload wire"):
        model.model_validate_json(padded)
