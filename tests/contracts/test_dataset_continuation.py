"""V3 continuation plan and approval: golden bytes, closed negatives, binding, policy matrix."""

import hashlib
import json
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

import pytest
from pydantic import ValidationError

from yorunge.application.upload_policy import approve_upload_v2
from yorunge.domain.dataset_continuation import (
    ContinuationBinding,
    DatasetContinuationPlanV3,
    DatasetUploadApprovalV3,
    baseline_digest,
    binding_matches,
    require_continuation_acknowledgements,
    validate_approval_binding_v3,
    validate_continuation_selection,
)
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_upload import REQUIRED_PERMISSIONS, UploadGrant
from yorunge.domain.dataset_upload_v2 import (
    DatasetUploadApprovalV2,
    DatasetUploadPlanV2,
    reduce_upload_policy,
    require_acknowledgements,
    validate_approval_binding_v2,
)
from yorunge.domain.errors import MESSAGES, OperationError, YorungeError
from yorunge.domain.platform_upload import ProviderDataset
from yorunge.domain.upload_costs import (
    ContinuationCostWork,
    ContinuationRequestLimits,
    UploadCostBoundV2,
)
from yorunge.domain.upload_resume import (
    BLOCKERS,
    ChainSummary,
    ContinuationNotPossible,
    RemoteInventory,
    RemoteItem,
    classify,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"
MATRIX = json.loads((FIXTURES / "dataset-upload-policy-matrix-v2.json").read_bytes())
DATASET = "00000000-0000-4000-8000-000000000909"
SOURCE = "00000000-0000-4000-8000-000000000009"
# Independent literals: computed once with plain hashlib/json by the fixture generator.
PLAN_DIGEST = "6e1fea1f76cef3b16a34b4c7efe97e9380b787bd7a1886bef8ee0d2c2f29cd6c"
BINDING_DIGEST = "7964b7a9538e7c57d4acf487d9536b6fe8cff1750eaf929afdac4e5df17aa641"
WORK_DIGEST = "5e839a73a1f585283cd8d95ea3191151ed43ab90adcfe7fb56b1c6c538bc60ab"
EVIDENCED_DIGEST = "85d76bfccc700c6397d0f485032e960e10ef35f64cebebb290c7d7fa3b38bb78"
EVIDENCED_BINDING = "eac9d4908f666a1bb209d280466cac54b06b7706b65ab6957a132251db5017a9"
CHECK_ONLY_DIGEST = "46df7fde4bd41fc8823c459025940f2c39c76ac7bbc3fa31fe20867371e4f783"
CHECK_ONLY_BINDING = "02353c81fb51320a10dcdab2785afdc8bb15f1542c1241dc57cc46c6b3b86a8f"
ALL_FILES_DIGEST = "8cfd514beccc9b5440e9524507d5ac657a3dcc93593e84fee294f8a6b36c1d51"
ALL_FILES_BINDING = "a33191a81b56bcedab6ab210640279d067da01d1cc5e0e5b4e67cb44338f7c22"


def canon(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture(name):
    return (FIXTURES / name).read_bytes()


def body(name="dataset-continuation-plan-v3.json"):
    return json.loads(fixture(name))


def seal(value):
    """A plan whose digest is recomputed by hand; the models must accept or reject it on merit."""
    value = {k: v for k, v in value.items() if k != "digest"}
    return {**value, "digest": sha(canon(value))}


def plan_of(value):
    return DatasetContinuationPlanV3.model_validate_json(canon(seal(value)))


def rejects(value, *, sealed=True):
    data = seal(value) if sealed else value
    canon_value = canon(data)
    with pytest.raises((ValidationError, ValueError)):
        DatasetContinuationPlanV3.model_validate_json(canon_value)


def changed(path, value, source=None):
    data = source or body()
    node = data
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return data


@contextmanager
def failure(code):
    with pytest.raises(YorungeError) as raised:
        yield
    assert raised.value.code == code


MAIN = DatasetContinuationPlanV3.model_validate_json(fixture("dataset-continuation-plan-v3.json"))
MANIFEST = DatasetManifest.model_validate_json(fixture("dataset-manifest-v1.json"))


# --- golden bytes and digests ------------------------------------------------------------------
def test_plan_approval_and_cost_work_goldens_round_trip_with_independent_digests():
    assert MAIN.encoded() == fixture("dataset-continuation-plan-v3.json")
    assert MAIN.digest == sha(canon({k: v for k, v in body().items() if k != "digest"}))
    assert MAIN.digest == MAIN.computed_digest() == PLAN_DIGEST
    assert MAIN.binding_digest() == BINDING_DIGEST
    approval = DatasetUploadApprovalV3.model_validate_json(
        fixture("dataset-continuation-approval-v3.json")
    )
    assert approval.encoded() == fixture("dataset-continuation-approval-v3.json")
    assert approval.binding_digest == BINDING_DIGEST
    assert approval.plan_digest == PLAN_DIGEST
    validate_approval_binding_v3(MAIN, approval)
    work = ContinuationCostWork.model_validate_json(
        fixture("dataset-continuation-cost-work-v3.json")
    )
    assert work.encoded() == fixture("dataset-continuation-cost-work-v3.json")
    assert work.digest() == WORK_DIGEST == MAIN.cost_work().digest()
    assert MAIN.cost_work() == work


def test_the_selection_goldens_cover_some_none_and_all_files():
    only = DatasetContinuationPlanV3.model_validate_json(
        fixture("dataset-continuation-plan-v3-verification-only.json")
    )
    everything = DatasetContinuationPlanV3.model_validate_json(
        fixture("dataset-continuation-plan-v3-all-files.json")
    )
    assert only.continuation.file_indices == ()
    assert only.request_limits.max_upload_bytes == 0
    assert only.continuation.remote_present_count == 3
    assert only.request_limits.files == 0
    assert everything.continuation.file_indices == (0, 1, 2)
    assert everything.continuation.remote_present_count == 0
    assert everything.request_limits.max_upload_bytes == MANIFEST.total_bytes == 8
    for plan in (only, everything):
        validate_continuation_selection(plan, MANIFEST)
    assert MAIN.continuation.uncertain_indices == (2,)
    assert MAIN.request_limits.max_upload_bytes == 8  # files 0 and 2: 3 + 5 bytes


def test_a_plan_is_a_closed_executable_false_v3_value():
    assert (MAIN.schema_version, MAIN.policy_version) == (3, 3)
    assert MAIN.kind == "dataset_upload_continuation_plan"
    assert MAIN.executable is False
    assert len(MAIN.encoded()) < 16 * 1024


def test_the_baseline_digest_equals_a_hand_written_preimage():
    created = ProviderDataset.model_validate(
        {
            "id": DATASET,
            "owner_id": "00000000-0000-4000-8000-000000000003",
            "org_id": None,
            "name": "sample",
            "modality": "VISION",
            "visibility": "private",
            "contributions_enabled": False,
        }
    )
    preimage = (
        '{"dataset":{"contributions_enabled":false,"id":"' + DATASET + '","modality":"VISION",'
        '"name":"sample","org_id":null,"owner_id":"00000000-0000-4000-8000-000000000003",'
        '"visibility":"private"},"kind":"upload_baseline"}'
    )
    assert baseline_digest(created) == sha(preimage.encode())


# --- the selection against the full manifest ---------------------------------------------------
def test_selected_bytes_are_checked_against_the_full_manifest_only_when_it_is_given():
    validate_continuation_selection(MAIN, MANIFEST)
    wrong = plan_of(changed(["request_limits", "max_upload_bytes"], 7))
    with pytest.raises(ValueError, match="selected file bytes"):
        validate_continuation_selection(wrong, MANIFEST)
    other = MANIFEST.model_copy(update={"digest": "0" * 64})
    with pytest.raises(ValueError):
        validate_continuation_selection(MAIN, other)


# --- closed negatives --------------------------------------------------------------------------
NEGATIVES = {
    "unordered indices": changed(["continuation", "file_indices"], [2, 0]),
    "repeated index": changed(
        ["continuation", "file_indices"],
        [1, 1],
        changed(
            ["continuation", "uncertain_indices"],
            [],
            changed(
                ["request_limits", "max_upload_bytes"],
                0,
                changed(["continuation", "remote_present_count"], 1),
            ),
        ),
    ),
    "non-canonical plan id": changed(["plan_id"], "00000000-0000-4000-8000-00000000000B"),
    "foreign uuid version": changed(["plan_id"], "00000000-0000-1000-8000-00000000000b"),
    "uppercase baseline digest": changed(["continuation", "baseline_digest"], "B" * 64),
    "short baseline digest": changed(["continuation", "baseline_digest"], "b" * 63),
    "index past the manifest": changed(
        ["continuation", "file_indices"], [0, 3], changed(["continuation", "uncertain_indices"], [])
    ),
    "selection longer than the limits": changed(
        ["request_limits", "max_presign"],
        1,
        changed(
            ["request_limits", "max_put"],
            1,
            changed(
                ["request_limits", "max_confirm"],
                1,
                changed(["continuation", "remote_present_count"], 2),
            ),
        ),
    ),
    "selection shorter than the limits": changed(
        ["continuation", "file_indices"],
        [0],
        changed(
            ["continuation", "uncertain_indices"],
            [],
            changed(["continuation", "remote_present_count"], 1),
        ),
    ),
    "index past the file limit": changed(["continuation", "file_indices"], [0, 128]),
    "negative index": changed(["continuation", "file_indices"], [-1, 2]),
    "uncertain outside the selection": changed(["continuation", "uncertain_indices"], [1]),
    "uncertain partly outside the selection": changed(
        ["continuation", "uncertain_indices"], [1, 2]
    ),
    "uncertain unordered": changed(["continuation", "uncertain_indices"], [2, 0]),
    "uncertain repeated": changed(["continuation", "uncertain_indices"], [2, 2]),
    "present count too low": changed(["continuation", "remote_present_count"], 0),
    "present count too high": changed(["continuation", "remote_present_count"], 2),
    "limits differ from the selection": changed(["request_limits", "max_presign"], 3),
    "put limit differs": changed(["request_limits", "max_put"], 1),
    "confirm limit differs": changed(["request_limits", "max_confirm"], 3),
    "a create is allowed": changed(["request_limits", "max_create"], 1),
    "a link is allowed": changed(["request_limits", "max_project_link"], 1),
    "bytes above the manifest": changed(["request_limits", "max_upload_bytes"], 9),
    "foreign intent digest": changed(["continuation", "intent_digest"], "e" * 64),
    "uppercase digest": changed(["continuation", "classification_digest"], "C" * 64),
    "short digest": changed(["continuation", "inventory_digest"], "d" * 63),
    "bad source id": changed(["continuation", "source_operation_id"], "not-a-uuid"),
    "uppercase baseline id": changed(
        ["continuation", "baseline_operation_id"], "00000000-0000-4000-8000-0000000000AB"
    ),
    "bad dataset id": changed(["continuation", "dataset_id"], "x"),
    "malformed observation instant": changed(["continuation", "observed_at"], "yesterday"),
    "window of zero": changed(["execution_window", "not_after"], "2026-11-02T11:00:00.000000Z"),
    "window over 900 seconds": changed(
        ["execution_window", "not_after"], "2026-11-02T11:15:01.000000Z"
    ),
    "plan after its window": changed(["expires_at"], "2026-11-02T11:15:01.000000Z"),
    "plan version 2": changed(["schema_version"], 2),
    "policy version 2": changed(["policy_version"], 2),
    "executable plan": changed(["executable"], True),
    "wrong kind": changed(["kind"], "dataset_upload_plan"),
    "bool as present count": changed(["continuation", "remote_present_count"], True),
    "bool as limit": changed(["request_limits", "max_presign"], True),
    "bool as policy version": changed(["policy_version"], True),
    "wrong risks": changed(["risks"], []),
    "wrong status": changed(["status"], "prepared"),
}


@pytest.mark.parametrize("name", NEGATIVES)
def test_every_closed_negative_is_rejected(name):
    rejects(NEGATIVES[name])


def test_unknown_missing_and_wrongly_typed_fields_are_rejected():
    for extra in ({"extra": 1}, {"continuation": {**body()["continuation"], "extra": 1}}):
        rejects({**body(), **extra})
    missing = body()
    del missing["continuation"]
    rejects(missing)
    for field in body()["continuation"]:
        data = body()
        del data["continuation"][field]
        rejects(data)
    nullable = changed(["continuation", "dataset_id"], None)
    rejects(nullable)


def test_a_stale_plan_digest_is_rejected():
    rejects(changed(["status"], "attempt_ready", {**body(), "digest": "0" * 64}), sealed=False)
    rejects({**body(), "digest": "0" * 64}, sealed=False)


@pytest.mark.parametrize("files", [0, 1, 2, 3])
def test_every_selection_size_that_fits_the_manifest_is_a_valid_plan(files):
    sizes = [3, 0, 5]
    indices = list(range(files))
    data = body()
    data["request_limits"].update(
        max_presign=files,
        max_put=files,
        max_confirm=files,
        max_upload_bytes=sum(sizes[i] for i in indices),
    )
    data["continuation"].update(
        file_indices=indices, uncertain_indices=[], remote_present_count=3 - files
    )
    assert plan_of(data).request_limits.files == files


def test_the_largest_plan_stays_inside_the_wire_limit():
    data = body()
    data["manifest"].update(file_count=128, total_bytes=0)
    data["request_limits"].update(max_presign=128, max_put=128, max_confirm=128, max_upload_bytes=0)
    data["continuation"].update(
        file_indices=list(range(128)), uncertain_indices=list(range(128)), remote_present_count=0
    )
    assert len(plan_of(data).encoded()) < 16 * 1024


# --- request limits and cost work --------------------------------------------------------------
def limits(**changes):
    value = body()["request_limits"]
    value.update(changes)
    return value


@pytest.mark.parametrize(
    "changes",
    [
        {"max_put": 1},
        {"max_confirm": 1},
        {"max_presign": 0, "max_put": 0, "max_confirm": 0},  # no files, yet bytes
        {"max_create": 1},
        {"max_project_link": 1},
        {"max_presign": 129, "max_put": 129, "max_confirm": 129},
        {"max_presign": True},
        {"max_read_requests": 511},
        {"max_read_requests": 513},
        {"max_read_attempts": 1023},
        {"max_read_attempts": 1025},
        {"max_read_attempts": 2048},
        {"max_presign": 3},  # put and confirm differ from presign
        {"max_control_request_bytes": 4194303},
        {"max_control_request_bytes": 4194305},
        {"max_control_response_bytes": 16777215},
        {"max_control_response_bytes": 16777217},
        {"max_upload_bytes": 1024**3 + 1},
        {"max_upload_bytes": -1},
        {"extra": 1},
    ],
)
def test_continuation_limits_reject_what_they_cannot_state(changes):
    canon_value = canon(limits(**changes))
    with pytest.raises(ValidationError):
        ContinuationRequestLimits.model_validate_json(canon_value)


ZERO_FILES = dict(
    max_create=0,
    max_project_link=0,
    max_presign=0,
    max_put=0,
    max_confirm=0,
    max_read_requests=512,
    max_read_attempts=1024,
    max_control_request_bytes=4194304,
    max_control_response_bytes=16777216,
    max_upload_bytes=0,
)
ONE_FILE = {**ZERO_FILES, "max_presign": 1, "max_put": 1, "max_confirm": 1, "max_upload_bytes": 1}


@pytest.mark.parametrize("base", [ZERO_FILES, ONE_FILE], ids=["no files", "one file"])
def test_limits_built_in_python_refuse_every_non_integer_even_one_equal_to_the_value(base):
    ContinuationRequestLimits(**base)  # control
    for field, value in base.items():
        impostors = [float(value), str(value), None]
        if value in (0, 1):
            impostors.append(bool(value))
        for impostor in impostors:
            with pytest.raises(ValidationError):
                ContinuationRequestLimits(**{**base, field: impostor})


def test_limits_accept_their_edges_and_nothing_beyond():
    largest = {**ZERO_FILES, "max_presign": 128, "max_put": 128, "max_confirm": 128}
    assert ContinuationRequestLimits(**{**largest, "max_upload_bytes": 1024**3}).files == 128
    for beyond in (
        {"max_presign": 129, "max_put": 129, "max_confirm": 129},
        {"max_upload_bytes": 1024**3 + 1},
    ):
        with pytest.raises(ValidationError):
            ContinuationRequestLimits(**{**largest, **beyond})
    assert ContinuationRequestLimits(**ZERO_FILES).files == 0


def test_cost_work_requires_a_selection_that_fits_the_manifest():
    work = json.loads(fixture("dataset-continuation-cost-work-v3.json"))
    for changes in (
        {"max_upload_bytes": 9},  # more than the manifest holds
        {"max_presign": 3, "max_put": 3, "max_confirm": 3, "max_upload_bytes": 7},  # not all bytes
    ):
        broken = {**work, "request_limits": {**work["request_limits"], **changes}}
        canon_value = canon(broken)
        with pytest.raises(ValidationError):
            ContinuationCostWork.model_validate_json(canon_value)
    too_many = {
        **work,
        "request_limits": {
            **work["request_limits"],
            "max_presign": 4,
            "max_put": 4,
            "max_confirm": 4,
        },
    }
    canon_value = canon(too_many)
    with pytest.raises(ValidationError):
        ContinuationCostWork.model_validate_json(canon_value)


def test_the_cost_work_digest_is_domain_separated_from_the_v2_work():
    work = MAIN.cost_work()
    assert work.digest() == sha(b"yorunge-upload-cost-work-v3\0" + work.encoded())
    assert work.digest() != sha(b"yorunge-upload-cost-work-v2\0" + work.encoded())


# --- acknowledgements and the approval ---------------------------------------------------------
def approval_body(**changes):
    value = json.loads(fixture("dataset-continuation-approval-v3.json"))
    value.update(changes)
    return value


def approval_of(**changes):
    return DatasetUploadApprovalV3.model_validate_json(canon(approval_body(**changes)))


@pytest.mark.parametrize(
    "unconfirmed,expected",
    [(False, "approval_required"), (True, None)],
)
def test_unconfirmed_effects_need_their_own_acknowledgement_when_a_file_is_uncertain(
    unconfirmed, expected
):
    kwargs = dict(authority=True, unpriced=True, unconfirmed=unconfirmed)
    if expected is None:
        require_continuation_acknowledgements(MAIN, **kwargs)
    else:
        with failure(expected):
            require_continuation_acknowledgements(MAIN, **kwargs)


def test_the_unconfirmed_acknowledgement_is_unneeded_without_an_uncertain_file():
    certain = plan_of(
        {
            **changed(["continuation", "uncertain_indices"], []),
        }
    )
    require_continuation_acknowledgements(certain, authority=True, unpriced=True, unconfirmed=False)
    with failure("invalid_request"):
        require_continuation_acknowledgements(
            certain, authority=True, unpriced=True, unconfirmed=True
        )
    with failure("approval_required"):
        require_continuation_acknowledgements(
            certain, authority=False, unpriced=True, unconfirmed=False
        )


def test_flags_must_be_booleans_and_a_draft_cannot_be_approved():
    with failure("invalid_request"):
        require_continuation_acknowledgements(MAIN, authority=1, unpriced=True, unconfirmed=True)
    draft = changed(["status"], "draft")
    draft["blockers"] = ["inputs_unverified"]
    draft["inputs_verified"] = False
    drafted = plan_of(draft)
    assert drafted.status == "draft"
    with failure("upload_plan_not_valid"):
        require_continuation_acknowledgements(
            drafted, authority=False, unpriced=False, unconfirmed=False
        )


def judged_against_main(**changes):
    """Make the approval these changes describe and judge it against the plan: either may refuse."""
    validate_approval_binding_v3(MAIN, approval_of(**changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"plan_digest": "0" * 64},
        {"binding_digest": "0" * 64},
        {"store_id": "00000000-0000-4000-8000-0000000000aa"},
        {"identity_epoch": "00000000-0000-4000-8000-0000000000aa"},
        {"clock_generation": 2},
        {
            "admission_policy": "verified_only",
            "acknowledge_unverified_authority": False,
            "acknowledge_unpriced_cost": False,
            "cost_policy": "bounded_required",
        },
        # Approved a second before the plan existed, with a valid 15-minute lifetime.
        {"approved_at": "2026-11-02T10:59:59.000000Z", "expires_at": "2026-11-02T11:14:59.000000Z"},
        {"expires_at": "2026-11-02T11:15:01.000000Z"},
        {"acknowledge_unconfirmed_effects": False},
        {"acknowledge_unverified_authority": False},
        {"acknowledge_unpriced_cost": False},
    ],
)
def test_an_approval_that_does_not_bind_this_plan_is_rejected(changes):
    with pytest.raises((ValueError, ValidationError)):
        judged_against_main(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "revoked"},
        {"revoked_at": "2026-11-02T11:00:02.000000Z"},
        {"approved_at": "2026-11-02T11:00:00.000000Z", "expires_at": "2026-11-02T11:15:01.000000Z"},
        {"approved_at": "2026-11-02T11:15:00.000000Z"},
        {"approved_at": "2026-11-01T11:00:00.000000Z"},  # a day before: lifetime over 900 s
        {"acknowledge_unconfirmed_effects": 1},
        {"schema_version": 2},
        {"extra": 1},
    ],
)
def test_malformed_approvals_are_rejected(changes):
    canon_value = canon(approval_body(**changes))
    with pytest.raises(ValidationError):
        DatasetUploadApprovalV3.model_validate_json(canon_value)
    stripped = approval_body()
    del stripped["acknowledge_unconfirmed_effects"]
    canon_value = canon(stripped)
    with pytest.raises(ValidationError):
        DatasetUploadApprovalV3.model_validate_json(canon_value)


def test_versions_never_mix_between_plan_and_approval():
    v2 = DatasetUploadApprovalV2.model_validate_json(fixture("dataset-upload-approval-v2.json"))
    with pytest.raises(ValueError, match="mixed upload plan/approval versions"):
        validate_approval_binding_v3(MAIN, v2)
    v2_plan = DatasetUploadPlanV2.model_validate_json(fixture("dataset-upload-plan-v2.json"))
    approval = DatasetUploadApprovalV3.model_validate_json(
        fixture("dataset-continuation-approval-v3.json")
    )
    with pytest.raises(ValueError, match="mixed upload plan/approval versions"):
        validate_approval_binding_v3(v2_plan, approval)


# --- the binding digest ------------------------------------------------------------------------
def test_every_binding_field_changes_the_digest_but_observation_instants_do_not():
    base = MAIN.binding_digest()
    flips = {
        "source_operation_id": "00000000-0000-4000-8000-0000000000a1",
        "baseline_operation_id": "00000000-0000-4000-8000-0000000000a2",
        "dataset_id": "00000000-0000-4000-8000-0000000000a3",
        "baseline_digest": "a" * 64,
        "classification_digest": "a" * 64,
        "inventory_digest": "a" * 64,
    }
    for field, value in flips.items():
        assert plan_of(changed(["continuation", field], value)).binding_digest() != base, field
    selection = body()
    selection["continuation"].update(
        file_indices=[0, 1], uncertain_indices=[], remote_present_count=1
    )
    selection["request_limits"].update(max_presign=2, max_put=2, max_confirm=2, max_upload_bytes=3)
    assert plan_of(selection).binding_digest() != base
    uncertain = body()
    uncertain["continuation"]["uncertain_indices"] = []
    assert plan_of(uncertain).binding_digest() != base
    # Not bound: when the observation was made, plan identity and validity instants.
    moved = changed(["continuation", "observed_at"], "2026-11-02T10:59:30.000000Z")
    assert plan_of(moved).binding_digest() == base
    other = changed(["plan_id"], "00000000-0000-4000-8000-0000000000b0")
    assert plan_of(other).binding_digest() == base
    shorter = changed(["expires_at"], "2026-11-02T11:10:00.000000Z")
    assert plan_of(shorter).binding_digest() == base
    # Bound: every other plan field, including the request budget of a plan that has one.
    assert plan_of(changed(["parameters", "tags"], ["other"])).binding_digest() != base
    evidenced = evidenced_plan()
    budgeted = plan_of(evidenced).binding_digest()
    assert plan_of({**evidenced, "budget_micros": 300_000_000}).binding_digest() != budgeted


# --- the policy: the 96-row v2 matrix gives the same answers for a continuation ----------------
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


def cost_for(kind, work):
    if kind == "none":
        return None
    data = json.loads(fixture("dataset-upload-cost-bound-v2.json"))
    data["work_digest"] = work.digest()
    if kind.startswith("partial"):
        data["charge_categories"] = ["transfer"]
    data["maximum_micros"] = 201_000_000 if kind.endswith("over") else 1_000_000
    return UploadCostBoundV2.model_validate_json(canon(data))


def policy_arguments(row, work):
    return dict(
        admission_policy=row["admission_policy"],
        cost_policy=row["cost_policy"],
        budget_micros=200_000_000 if row["cost_policy"] == "bounded_required" else None,
        inputs_verified=row["inputs"],
        grant=grant_for(work, row["grant"]),
        cost_bound=cost_for(row["cost"], work),
    )


@pytest.mark.parametrize("row", MATRIX)
def test_all_96_policy_rows_give_the_same_answers_for_a_continuation(row):
    work = MAIN.cost_work()
    arguments = policy_arguments(row, work)
    if row["error"] is not None:
        with failure(row["error"]):
            reduce_upload_policy(work, **arguments)
        return
    state = reduce_upload_policy(work, **arguments)
    assert (state.status, list(state.risks), list(state.blockers)) == (
        row["status"],
        row["risks"],
        row["blockers"],
    )
    # The same row sealed into a plan is accepted whole, and its approval follows the matrix.
    sealed = body()
    sealed.update(
        admission_policy=row["admission_policy"],
        cost_policy=row["cost_policy"],
        budget_micros=arguments["budget_micros"],
        inputs_verified=row["inputs"],
        grant=arguments["grant"].model_dump(mode="json") if arguments["grant"] else None,
        cost_bound=arguments["cost_bound"].model_dump(mode="json")
        if arguments["cost_bound"]
        else None,
        risks=row["risks"],
        blockers=row["blockers"],
        status=row["status"],
    )
    plan = plan_of(sealed)
    if plan.status == "draft":
        with failure("upload_plan_not_valid"):
            require_continuation_acknowledgements(
                plan, authority=False, unpriced=False, unconfirmed=False
            )
        return
    # An uncertain file adds the third acknowledgement; the first two follow the v2 row.
    require_continuation_acknowledgements(
        plan, authority=row["ack_authority"], unpriced=row["ack_cost"], unconfirmed=True
    )


def test_the_matrix_replay_covers_every_status_of_the_v2_matrix():
    assert len(MATRIX) == 96
    assert Counter(row["status"] or "invalid" for row in MATRIX) == {
        "draft": 65,
        "prepared": 2,
        "attempt_ready": 11,
        "invalid": 18,
    }


# --- the two new error codes -------------------------------------------------------------------
def test_continuation_not_possible_carries_closed_ordered_blockers_and_the_operation_id():
    error = ContinuationNotPossible(("drift_missing", "extra_remote"), SOURCE)
    envelope = error.envelope()
    assert error.code == "continuation_not_possible"
    assert error.exit_code == 2
    assert envelope["operation_id"] == SOURCE
    assert envelope["details"]["blockers"] == ["drift_missing", "extra_remote"]
    assert envelope["message"] == MESSAGES["continuation_not_possible"]
    assert envelope["code"] == "continuation_not_possible"


@pytest.mark.parametrize(
    "blockers",
    [(), ("extra_remote", "drift_missing"), ("drift_missing", "drift_missing"), ("bogus",)],
)
def test_continuation_not_possible_refuses_open_unordered_or_repeated_blockers(blockers):
    with pytest.raises(ValueError, match="closed, ordered, distinct blockers"):
        ContinuationNotPossible(blockers)


def test_an_active_source_is_an_operation_conflict_never_a_continuation_refusal():
    for blockers in (("source_active",), ("source_active", "drift_missing")):
        with pytest.raises(ValueError, match="without source_active"):
            ContinuationNotPossible(blockers)


def test_every_other_blocker_name_can_be_carried_alone():
    for blocker in (b for b in BLOCKERS if b != "source_active"):
        assert ContinuationNotPossible((blocker,)).envelope()["details"]["blockers"] == [blocker]


def test_continuation_remote_changed_is_a_plain_exit_two_error_with_a_fixed_message():
    error = YorungeError("continuation_remote_changed")
    assert type(error) is YorungeError
    assert not isinstance(error, OperationError)
    assert error.exit_code == 2
    assert error.message == MESSAGES["continuation_remote_changed"]
    assert "http" not in error.message


def test_the_plan_wire_carries_no_created_dataset_owner_or_receipt_fields():
    text = fixture("dataset-continuation-plan-v3.json").decode()
    for needle in ("created_dataset", "object_key", "receipt", "owner_username", "slug"):
        assert needle not in text
    assert set(ContinuationBinding.model_fields) == set(body()["continuation"])


# --- the fresh classification against what a plan bound ----------------------------------------
def fresh_classification(*, states=("none", "none", "intent"), present=(1,), faults=()):
    chain = ChainSummary(states, False, False, MANIFEST.digest)
    items = tuple(
        RemoteItem(f.path, f.size, f.sha256, f"item-{i}")
        for i, f in enumerate(MANIFEST.files)
        if i in present
    )
    return classify(MANIFEST, chain, RemoteInventory(items, frozenset(faults)))


def bound_to(classification):
    """The plan's binding as the producer would write it from this classification."""
    selection = classification.selection()
    assert selection is not None
    return MAIN.continuation.model_copy(
        update={
            "file_indices": selection.file_indices,
            "uncertain_indices": selection.uncertain_indices,
            "remote_present_count": selection.remote_present_count,
            "classification_digest": classification.classification_digest,
            "inventory_digest": classification.inventory_digest,
        }
    )


def test_a_fresh_classification_that_says_the_same_matches_the_binding():
    fresh = fresh_classification()
    assert fresh.classes == ("pending_clean", "observed", "pending_uncertain")
    binding = bound_to(fresh)
    assert binding.file_indices == (0, 2)
    assert binding.uncertain_indices == (2,)
    assert binding_matches(binding, fresh)
    # The same evidence rebuilt from scratch matches too.
    assert binding_matches(binding, fresh_classification())


@pytest.mark.parametrize(
    "changes",
    [
        {"file_indices": (0, 1, 2)},
        {"file_indices": (0,), "uncertain_indices": ()},
        {"uncertain_indices": ()},
        {"remote_present_count": 0},
        {"classification_digest": "f" * 64},
        {"inventory_digest": "f" * 64},
    ],
)
def test_a_binding_that_differs_in_any_compared_field_does_not_match(changes):
    fresh = fresh_classification()
    assert not binding_matches(bound_to(fresh).model_copy(update=changes), fresh)


def test_a_changed_remote_or_chain_state_or_any_blocker_breaks_the_match():
    binding = bound_to(fresh_classification())
    # The remote now also holds file 0: the selection and both digests move.
    assert not binding_matches(binding, fresh_classification(present=(0, 1)))
    # The lineage learned that file 2 was never attempted: classes and the digest move.
    assert not binding_matches(binding, fresh_classification(states=("none", "none", "none")))
    # A transient listing fault blocks everything, even with the same items.
    assert not binding_matches(binding, fresh_classification(faults=("cursor_loop",)))
    # A blocker the caller merged in withdraws the selection.
    assert not binding_matches(binding, fresh_classification().with_blockers(("source_active",)))


# --- evidence instants are observation time, not part of what an approval commits to -----------
def evidenced_plan():
    prepared = next(row for row in MATRIX if row["status"] == "prepared")
    work = MAIN.cost_work()
    data = body()
    grant = grant_for(work, prepared["grant"])
    cost = cost_for(prepared["cost"], work)
    data.update(
        admission_policy=prepared["admission_policy"],
        cost_policy=prepared["cost_policy"],
        budget_micros=200_000_000,
        inputs_verified=prepared["inputs"],
        grant=grant.model_dump(mode="json"),
        cost_bound=cost.model_dump(mode="json"),
        risks=prepared["risks"],
        blockers=prepared["blockers"],
        status=prepared["status"],
    )
    return data


def test_grant_and_cost_evidence_instants_do_not_change_the_binding_but_content_does():
    data = evidenced_plan()
    base = plan_of(data)
    assert base.grant is not None
    assert base.cost_bound is not None
    earlier_and_longer = json.loads(json.dumps(data))
    earlier_and_longer["grant"].update(
        checked_at="2026-11-02T10:59:00.000000Z", expires_at="2026-11-02T11:20:00.000000Z"
    )
    earlier_and_longer["cost_bound"].update(
        checked_at="2026-11-02T10:58:00.000000Z", expires_at="2026-11-02T11:20:00.000000Z"
    )
    moved = plan_of(earlier_and_longer)
    assert moved.digest != base.digest
    assert moved.binding_digest() == base.binding_digest()
    for evidence, field, value in (
        ("grant", "producer_version", "9"),
        ("cost_bound", "maximum_micros", 2_000_000),
    ):
        other = json.loads(json.dumps(data))
        other[evidence][field] = value
        assert plan_of(other).binding_digest() != base.binding_digest(), (evidence, field)


# --- review round 1: consent entry points, isolated bindings, boundaries, extra goldens --------
def approval_for(plan, **changes):
    value = {
        **approval_body(),
        "plan_id": plan.plan_id,
        "plan_digest": plan.digest,
        "binding_digest": plan.binding_digest(),
        **changes,
    }
    return DatasetUploadApprovalV3.model_validate_json(canon(value))


def test_the_v2_consent_entry_points_refuse_a_v3_plan_and_a_v3_approval():
    v2_approval = DatasetUploadApprovalV2.model_validate_json(
        fixture("dataset-upload-approval-v2.json")
    )
    with pytest.raises(ValueError, match="mixed upload plan/approval versions"):
        validate_approval_binding_v2(MAIN, v2_approval)
    with failure("upload_plan_not_valid"):
        require_acknowledgements(MAIN, authority=True, unpriced=True)
    with failure("upload_plan_not_valid"):
        approve_upload_v2(
            MAIN,
            approval_id="00000000-0000-4000-8000-000000000007",
            confirmed_digest=MAIN.digest,
            approved_at="2026-11-02T11:00:01.000000Z",
            acknowledge_unverified_authority=True,
            acknowledge_unpriced_cost=True,
        )
    v2_plan = DatasetUploadPlanV2.model_validate_json(fixture("dataset-upload-plan-v2.json"))
    v3_approval = DatasetUploadApprovalV3.model_validate_json(
        fixture("dataset-continuation-approval-v3.json")
    )
    with pytest.raises(ValueError, match="mixed upload plan/approval versions"):
        validate_approval_binding_v2(v2_plan, v3_approval)


def test_the_exact_type_rule_also_refuses_a_subclass():
    class Derived(DatasetContinuationPlanV3):
        pass

    derived = Derived.model_validate_json(fixture("dataset-continuation-plan-v3.json"))
    approval = DatasetUploadApprovalV3.model_validate_json(
        fixture("dataset-continuation-approval-v3.json")
    )
    with pytest.raises(ValueError, match="mixed upload plan/approval versions"):
        validate_approval_binding_v3(derived, approval)


def test_an_approval_for_another_plan_id_is_rejected_even_with_matching_digests():
    other = approval_for(MAIN, plan_id="00000000-0000-4000-8000-0000000000dd")
    with pytest.raises(ValueError, match="binding mismatch"):
        validate_approval_binding_v3(MAIN, other)


def test_another_admission_policy_is_rejected_when_no_acknowledgement_can_mask_it():
    plan = DatasetContinuationPlanV3.model_validate_json(
        fixture("dataset-continuation-plan-v3-evidenced.json")
    )
    assert plan.status == "prepared"
    assert plan.risks == ()
    assert plan.admission_policy == "explicit_attempt"
    clean = dict(
        acknowledge_unverified_authority=False,
        acknowledge_unpriced_cost=False,
        acknowledge_unconfirmed_effects=False,
        cost_policy="bounded_required",
    )
    validate_approval_binding_v3(
        plan, approval_for(plan, admission_policy="explicit_attempt", **clean)
    )
    other = approval_for(plan, admission_policy="verified_only", **clean)
    with pytest.raises(ValueError, match="binding mismatch"):
        validate_approval_binding_v3(plan, other)


def test_an_approval_may_start_with_the_plan_but_never_before_it():
    short = plan_of(changed(["expires_at"], "2026-11-02T11:10:00.000000Z"))
    on_time = approval_for(
        short, approved_at="2026-11-02T11:00:00.000000Z", expires_at="2026-11-02T11:10:00.000000Z"
    )
    validate_approval_binding_v3(short, on_time)
    early = approval_for(
        short, approved_at="2026-11-02T10:59:59.000000Z", expires_at="2026-11-02T11:10:00.000000Z"
    )
    with pytest.raises(ValueError, match="binding mismatch"):
        validate_approval_binding_v3(short, early)


def test_binding_a_revoked_approval_is_valid_because_effectiveness_is_the_callers_check():
    revoked = approval_for(MAIN, status="revoked", revoked_at="2026-11-02T11:00:02.000000Z")
    validate_approval_binding_v3(MAIN, revoked)
    assert revoked.status == "revoked"


def test_a_plan_whose_digest_no_longer_matches_its_content_cannot_be_approved():
    stale = MAIN.model_copy(update={"digest": "0" * 64})
    approval = DatasetUploadApprovalV3.model_validate_json(
        fixture("dataset-continuation-approval-v3.json")
    )
    with pytest.raises(ValueError, match="plan digest mismatch"):
        validate_approval_binding_v3(stale, approval)


@pytest.mark.parametrize("field", ["approval_id", "plan_id", "store_id", "identity_epoch"])
def test_approval_identifiers_must_be_canonical(field):
    with pytest.raises(ValidationError):
        approval_of(**{field: "00000000-0000-4000-8000-00000000000B"})


def test_approval_status_is_closed_and_verified_policy_cannot_acknowledge_unknown_risks():
    for status in ("bogus", "approved "):
        with pytest.raises(ValidationError):
            approval_of(status=status)
    with pytest.raises(ValidationError):
        approval_of(
            admission_policy="verified_only",
            cost_policy="bounded_required",
            acknowledge_unverified_authority=True,
            acknowledge_unpriced_cost=False,
        )


def test_selected_bytes_below_the_limit_are_rejected_like_those_above_it():
    data = body()
    data["continuation"].update(file_indices=[0], uncertain_indices=[], remote_present_count=2)
    data["request_limits"].update(max_presign=1, max_put=1, max_confirm=1, max_upload_bytes=5)
    plan_of_value = plan_of(data)
    with pytest.raises(ValueError, match="selected file bytes"):
        validate_continuation_selection(plan_of_value, MANIFEST)


def test_observation_may_equal_but_never_follow_the_plan_preparation():
    plan_of(changed(["continuation", "observed_at"], body()["prepared_at"]))
    rejects(changed(["continuation", "observed_at"], "2026-11-02T11:00:00.000001Z"))


def test_the_intent_digest_is_derived_from_the_exact_name():
    data = body()
    data["parameters"]["name"] = "Sample"
    scope = data["scope"]
    preimage = canon(
        {
            "service_origin": scope["service_origin"],
            "api_base_path": scope["api_base_path"],
            "owner": scope["owner"],
            "project_id": scope["project_id"],
            "name": "Sample",
        }
    )
    data["continuation"]["intent_digest"] = sha(preimage)
    plan_of(data)
    data["continuation"]["intent_digest"] = sha(preimage.replace(b"Sample", b"sample"))
    rejects(data)


def test_cost_evidence_priced_for_other_work_is_rejected_for_a_v3_plan():
    data = evidenced_plan()
    plan_of(data)  # control: bound to this very work
    data["cost_bound"] = {**data["cost_bound"], "work_digest": "0" * 64}
    rejects(data)


def test_plan_facts_hold_for_v3_at_their_evidence_and_window_boundaries():
    data = evidenced_plan()

    def altered(path, value):
        copy = json.loads(json.dumps(data))
        node = copy
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
        return copy

    other_scope = {**data["scope"], "profile": "other"}
    for evidence in ("grant", "cost_bound"):
        rejects(altered([evidence, "scope"], other_scope))
        rejects(altered([evidence, "checked_at"], "2026-11-02T11:00:00.000001Z"))
        plan_of(altered([evidence, "checked_at"], "2026-11-02T11:00:00.000000Z"))
        rejects(altered([evidence, "expires_at"], "2026-11-02T11:14:59.999999Z"))
        plan_of(altered([evidence, "expires_at"], "2026-11-02T11:15:00.000000Z"))
    rejects({**data, "budget_micros": None})  # a bounded policy needs its budget
    rejects({**data, "expires_at": data["prepared_at"]})
    rejects({**data, "prepared_at": "2026-11-02T10:59:59.000000Z"})
    draft = altered(["status"], "draft")
    draft["inputs_verified"] = False
    draft["blockers"] = ["cost_unverified"]  # status and risks are right, the blocker set is not
    rejects(draft)


def test_a_plan_over_the_wire_limit_is_rejected_cleanly_even_when_only_its_canonical_form_is():
    data = body()
    data["root"]["anchor"] = "/" + "\U0001f600" * 1023
    data["parameters"]["license"] = "\U0001f600" * 32
    data["parameters"]["tags"] = sorted(f"t{n}" + "a" * 120 for n in range(10))
    data["scope"]["profile"] = "p" * 128
    data = seal(data)
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
    assert len(raw) < 16 * 1024 < len(canon(data))
    with pytest.raises((ValidationError, ValueError)):
        DatasetContinuationPlanV3.model_validate_json(raw)
    canon_value = canon(data)
    with pytest.raises(ValueError, match="bounded upload wire"):
        DatasetContinuationPlanV3.model_validate_json(canon_value + b" " * 16384)


def test_the_message_of_a_remote_change_is_a_fixed_instruction_to_prepare_again():
    assert MESSAGES["continuation_remote_changed"] == (
        "Uzak durum devam planı hazırlandıktan sonra değişti; "
        "istek gönderilmedi. Yeniden hazırlayın."
    )
    assert MESSAGES["continuation_not_possible"] == (
        "Devam bu işten şu an hazırlanamıyor. Nedenler için resume raporunu inceleyin."
    )


# --- the extra goldens: non-null evidence, fewer files and fewer bytes than the manifest ---------
def test_the_evidenced_golden_pins_non_null_evidence_and_a_partial_selection():
    raw = fixture("dataset-continuation-plan-v3-evidenced.json")
    plan = DatasetContinuationPlanV3.model_validate_json(raw)
    assert plan.encoded() == raw
    assert plan.digest == EVIDENCED_DIGEST
    assert plan.binding_digest() == EVIDENCED_BINDING
    assert plan.grant is not None
    assert plan.cost_bound is not None
    assert plan.status == "prepared"
    assert plan.risks == ()
    assert plan.blockers == ()
    # Two of three files and 3 of the manifest's 8 bytes: M < N and fewer bytes than the total.
    assert plan.continuation.file_indices == (0, 1)
    assert plan.request_limits.max_upload_bytes == 3
    approval = DatasetUploadApprovalV3.model_validate_json(
        fixture("dataset-continuation-approval-v3-evidenced.json")
    )
    assert approval.encoded() == fixture("dataset-continuation-approval-v3-evidenced.json")
    assert not approval.acknowledge_unverified_authority
    assert not approval.acknowledge_unpriced_cost
    assert not approval.acknowledge_unconfirmed_effects
    validate_approval_binding_v3(plan, approval)
    validate_continuation_selection(plan, MANIFEST)


@pytest.mark.parametrize(
    "name,digest,binding",
    [
        ("verification-only", CHECK_ONLY_DIGEST, CHECK_ONLY_BINDING),
        ("all-files", ALL_FILES_DIGEST, ALL_FILES_BINDING),
    ],
)
def test_the_selection_goldens_are_byte_exact_with_literal_digests(name, digest, binding):
    raw = fixture(f"dataset-continuation-plan-v3-{name}.json")
    plan = DatasetContinuationPlanV3.model_validate_json(raw)
    assert plan.encoded() == raw
    assert (plan.digest, plan.binding_digest()) == (digest, binding)


# --- field-level rules the plan- and binding-level checks would otherwise mask -----------------
# A plan or an approval rejects most malformed fields through a second, cross-field rule, so a
# model checked only through them could lose its own field rule unnoticed. These tests build the
# binding and both approval versions directly, then pin each rule on its own.
APPROVALS = [
    pytest.param(DatasetUploadApprovalV2, "dataset-upload-approval-v2.json", id="v2"),
    pytest.param(DatasetUploadApprovalV3, "dataset-continuation-approval-v3.json", id="v3"),
]
BAD_DIGESTS = ["", "0" * 63, "0" * 65, "g" * 64, "A" * 64, "0" * 63 + "G"]


def binding_of(**changes):
    return ContinuationBinding.model_validate_json(canon({**body()["continuation"], **changes}))


def approval_model(model, name, **changes):
    return model.model_validate_json(canon({**json.loads(fixture(name)), **changes}))


@pytest.mark.parametrize("value", BAD_DIGESTS)
@pytest.mark.parametrize(
    "field", ["baseline_digest", "intent_digest", "classification_digest", "inventory_digest"]
)
def test_the_binding_digests_are_lowercase_sha256_hex(field, value):
    assert binding_of().model_dump(mode="json") == body()["continuation"]  # control
    with pytest.raises(ValidationError):
        binding_of(**{field: value})


@pytest.mark.parametrize(
    "value",
    [
        "",
        "tomorrow",
        "2026-11-02T11:00:00Z",  # no microseconds
        "2026-11-02T11:00:00.000000+00:00",  # not the Z form
        "2026-11-02T11:00:00.000000z",
        "2026-11-02 11:00:00.000000Z",
    ],
)
def test_the_binding_observation_is_a_canonical_utc_instant_on_its_own(value):
    with pytest.raises(ValidationError):
        binding_of(observed_at=value)


def test_the_remote_present_count_is_bounded_by_the_largest_upload():
    binding_of(remote_present_count=0)
    binding_of(remote_present_count=128)
    for value in (129, -1, True, "1", 1.0):
        with pytest.raises(ValidationError):
            binding_of(remote_present_count=value)


@pytest.mark.parametrize("model,name", APPROVALS)
@pytest.mark.parametrize("value", [0, -1, 2**63, True, "1", 1.0])
def test_the_approval_clock_generation_is_a_positive_signed_64_bit_integer(model, name, value):
    approval_model(model, name, clock_generation=1)
    approval_model(model, name, clock_generation=2**63 - 1)
    with pytest.raises(ValidationError):
        approval_model(model, name, clock_generation=value)


@pytest.mark.parametrize("model,name", APPROVALS)
@pytest.mark.parametrize("value", BAD_DIGESTS)
@pytest.mark.parametrize("field", ["plan_digest", "binding_digest"])
def test_the_approval_digests_are_lowercase_sha256_hex_on_their_own(model, name, field, value):
    with pytest.raises(ValidationError):
        approval_model(model, name, **{field: value})


@pytest.mark.parametrize("model,name", APPROVALS)
def test_an_approval_lives_for_at_most_exactly_fifteen_minutes(model, name):
    approval_model(model, name, approved_at="2026-11-02T11:00:00.000000Z")  # exactly 900 s
    for approved, expires in (
        ("2026-11-02T10:59:59.999999Z", "2026-11-02T11:15:00.000000Z"),  # 900 s and one microsecond
        ("2026-11-02T11:00:01.000000Z", "2026-11-02T11:00:01.000000Z"),  # no lifetime
        ("2026-11-02T11:00:01.000000Z", "2026-11-02T11:00:00.999999Z"),  # a negative one
    ):
        with pytest.raises(ValidationError):
            approval_model(model, name, approved_at=approved, expires_at=expires)


@pytest.mark.parametrize("model,name", APPROVALS)
def test_a_revocation_may_coincide_with_the_approval_but_never_precede_it(model, name):
    approval_model(model, name, status="revoked", revoked_at="2026-11-02T11:00:01.000000Z")
    approval_model(model, name, status="revoked", revoked_at="2026-11-02T11:00:01.000001Z")
    with pytest.raises(ValidationError):
        approval_model(model, name, status="revoked", revoked_at="2026-11-02T11:00:00.999999Z")


def test_the_acknowledgement_and_selection_checks_accept_only_a_genuine_v3_plan():
    v2_plan = DatasetUploadPlanV2.model_validate_json(fixture("dataset-upload-plan-v2.json"))

    class Imitation(DatasetContinuationPlanV3):
        pass

    imitation = Imitation.model_construct(**dict(MAIN))
    for impostor in (v2_plan, imitation, None, {"continuation": 1}, object()):
        with failure("upload_plan_not_valid"):
            require_continuation_acknowledgements(
                impostor, authority=True, unpriced=True, unconfirmed=True
            )
        with pytest.raises(ValueError, match="continuation plan is required"):
            validate_continuation_selection(impostor, MANIFEST)
    # The genuine plan still passes both.
    require_continuation_acknowledgements(MAIN, authority=True, unpriced=True, unconfirmed=True)
    validate_continuation_selection(MAIN, MANIFEST)
