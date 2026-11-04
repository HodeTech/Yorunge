"""Independent wire/digest and closed upload preparation/approval invariants."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from yorunge.domain import dataset_upload as upload
from yorunge.domain.dataset_manifest import DatasetFile, DatasetManifest, build_manifest

FIXTURES = Path(__file__).parents[1] / "fixtures"
GOLDEN = FIXTURES / "dataset-upload-plan-v1.json"
EXPECTED_DIGEST = "97a90e0b3e7bd820994d90a7e64f3727e7de9ed7aa975718f9e1513766a9acf5"


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode()


def payload():
    return json.loads(GOLDEN.read_bytes())


def reseal(value):
    body = {key: item for key, item in value.items() if key != "digest"}
    return canonical({**body, "digest": hashlib.sha256(canonical(body)).hexdigest()})


def prepared():
    value = payload()
    value["grant"] = {
        "schema_version": 1,
        "scope": deepcopy(value["scope"]),
        "permissions": [
            "create_private_dataset",
            "link_project",
            "read_created_dataset",
            "upload_created_dataset",
        ],
        "producer_id": "fixture_only",
        "producer_version": "1",
        "checked_at": "2026-11-02T10:59:59.000000Z",
        "expires_at": value["expires_at"],
    }
    value["cost_bound"] = {
        "schema_version": 1,
        "scope": deepcopy(value["scope"]),
        "maximum_micros": 1,
        "source_id": "fixture_only",
        "source_version": "1",
        "checked_at": "2026-11-02T10:59:59.000000Z",
        "expires_at": value["expires_at"],
    }
    value["blockers"], value["status"] = [], "prepared"
    return upload.DatasetUploadPlan.model_validate_json(reseal(value))


def approval(plan):
    return upload.DatasetUploadApproval(
        schema_version=1,
        approval_id="00000000-0000-4000-8000-000000000007",
        plan_id=plan.plan_id,
        plan_digest=plan.digest,
        binding_digest=plan.binding_digest(),
        store_id=plan.scope.store_id,
        identity_epoch=plan.scope.identity_epoch,
        clock_generation=plan.scope.clock_generation,
        approved_at="2026-11-02T11:00:01.000000Z",
        expires_at=plan.expires_at,
        status="approved",
        revoked_at=None,
    )


def test_literal_golden_and_manifest_byte_bound():
    content = GOLDEN.read_bytes()
    actual = upload.DatasetUploadPlan.model_validate_json(content)
    assert actual.digest == EXPECTED_DIGEST
    assert actual.encoded() == content
    manifest = DatasetManifest.model_validate_json(
        (FIXTURES / "dataset-manifest-v1.json").read_bytes()
    )
    assert upload.manifest_reference(manifest) == actual.manifest
    assert actual.status == "draft"
    assert actual.executable is False
    assert actual.blockers == ("authority_unverified", "cost_unverified")
    assert actual.cost_bound is None


@pytest.mark.parametrize(
    "path,value",
    [
        (("schema_version",), True),
        (("policy_version",), 1.0),
        (("scope", "clock_generation"), True),
        (("scope", "credential_revision"), 0),
        (("root", "device"), False),
        (("root", "inode"), 0),
        (("budget_micros",), 200.0),
        (("inputs_verified",), 1),
        (("executable",), 0),
        (("parameters", "contributions_enabled"), 0),
        (("parameters", "visibility"), "public"),
        (("scope", "service_id"), "evren-llm"),
        (("parameters", "extra"), 1),
        (("manifest", "file_count"), 129),
        (("manifest", "total_bytes"), 1024**3 + 1),
        (("root", "anchor"), "/a/../b"),
        (("root", "anchor"), "/a/\u202eb"),
        (("storage", "mode"), "fallback"),
        (("storage", "origin"), "https://storage.invalid"),
        (("scope", "service_origin"), "https://api.ssyz.org.tr/api"),
        (("scope", "project_id"), "not-a-uuid"),
        (("plan_id",), "0192a1b2-c3d4-7a56-8b90-123456789abc"),
        (("expires_at",), "2026-11-02T11:15:00.000001Z"),
        (("expires_at",), "2026-11-02T11:00:00.000000Z"),
        (("blockers",), ["cost_unverified", "authority_unverified"]),
        (("status",), "prepared"),
        (("parameters", "tags"), ["b", "a"]),
        (("parameters", "name"), " sample"),
        (("parameters", "license"), "x" * 129),
    ],
)
def test_raw_closed_type_policy_and_relation_rejection(path, value):
    data = payload()
    node = data
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    content = reseal(data)
    with pytest.raises(ValueError):
        upload.DatasetUploadPlan.model_validate_json(content)


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"{}",
        b"null",
        b'{"schema_version":1,"schema_version":1}',
        b'{"x":NaN}',
        b'{"x":1e999}',
        b'{"x":"\\ud800"}',
        b"\xef\xbb\xbf{}",
        b"{} trailing",
        b"\xff",
    ],
)
def test_malformed_wire_is_never_normalized(raw):
    with pytest.raises(ValueError):
        upload.DatasetUploadPlan.model_validate_json(raw)


def test_every_required_key_including_nullable_is_required():
    for key in payload():
        value = payload()
        del value[key]
        content = canonical(value)
        with pytest.raises(ValueError):
            upload.DatasetUploadPlan.model_validate_json(content)


def test_unicode_name_byte_bound_and_original_spelling():
    data = payload()
    data["parameters"]["name"] = "ö" * 128
    plan = upload.DatasetUploadPlan.model_validate_json(reseal(data))
    assert plan.parameters.name == "ö" * 128
    data["parameters"]["name"] = "漢" * 128
    content = reseal(data)
    with pytest.raises(ValueError):
        upload.DatasetUploadPlan.model_validate_json(content)


def test_provider_v7_id_is_preserved_and_internal_v7_is_not_accepted():
    data = payload()
    identifier = "0192a1b2-c3d4-7a56-8b90-123456789abc"
    data["scope"]["project_id"] = identifier
    plan = upload.DatasetUploadPlan.model_validate_json(reseal(data))
    assert plan.scope.project_id == identifier


@pytest.mark.parametrize(
    "mode,origin",
    [
        ("direct", None),
        ("direct", "http://storage.invalid"),
        ("direct", "https://storage.invalid/path"),
        ("direct", "https://storage.invalid?key=x"),
        ("direct", "https://user@storage.invalid"),
        ("direct", "https://storage.invalid:444"),
    ],
)
def test_direct_target_cannot_be_implicit_or_mutated(mode, origin):
    with pytest.raises(ValueError):
        upload.UploadStoragePolicy(mode=mode, origin=origin)


def test_direct_canonical_origin_is_bound_to_plan():
    data = payload()
    data["storage"] = {"mode": "direct", "origin": "https://storage.invalid"}
    plan = upload.DatasetUploadPlan.model_validate_json(reseal(data))
    assert plan.storage.origin == "https://storage.invalid"
    assert plan.digest != upload.DatasetUploadPlan.model_validate_json(GOLDEN.read_bytes()).digest


@pytest.mark.parametrize(
    "change",
    [
        "grant_scope",
        "cost_scope",
        "future_grant",
        "early_expiry",
        "missing_permission",
        "price_over_budget",
        "stale_status",
    ],
)
def test_prepared_requires_exact_current_observation_snapshot(change):
    data = prepared().model_dump(mode="json")
    if change == "grant_scope":
        data["grant"]["scope"]["credential_revision"] = 2
    elif change == "cost_scope":
        data["cost_bound"]["scope"]["project_id"] = "00000000-0000-4000-8000-000000000008"
    elif change == "future_grant":
        data["grant"]["checked_at"] = "2026-11-02T11:00:00.000001Z"
    elif change == "early_expiry":
        data["grant"]["expires_at"] = "2026-11-02T11:14:59.000000Z"
    elif change == "missing_permission":
        data["grant"]["permissions"].pop()
    elif change == "price_over_budget":
        data["cost_bound"]["maximum_micros"] = 200_000_001
    else:
        data["blockers"] = ["cost_unverified"]
    content = reseal(data)
    with pytest.raises(ValueError):
        upload.DatasetUploadPlan.model_validate_json(content)


def test_draft_reducer_exposes_unknown_inputs_and_cost_without_fake_price():
    data = payload()
    data["inputs_verified"] = False
    data["blockers"] = ["authority_unverified", "cost_unverified", "inputs_unverified"]
    plan = upload.DatasetUploadPlan.model_validate_json(reseal(data))
    assert plan.cost_bound is None
    assert plan.blockers[-1] == "inputs_unverified"


def test_plan_identity_and_time_do_not_bypass_same_create_intent():
    first = prepared()
    data = first.model_dump(mode="json")
    data["plan_id"] = "00000000-0000-4000-8000-000000000009"
    data["scope"]["credential_revision"] = 2
    data["grant"]["scope"] = deepcopy(data["scope"])
    data["cost_bound"]["scope"] = deepcopy(data["scope"])
    second = upload.DatasetUploadPlan.model_validate_json(reseal(data))
    assert second.intent_digest() == first.intent_digest()
    assert second.binding_digest() != first.binding_digest()
    assert second.digest != first.digest


def test_observation_time_refresh_keeps_semantic_binding_only():
    first = prepared()
    data = first.model_dump(mode="json")
    data["prepared_at"] = "2026-11-02T11:00:00.000001Z"
    data["grant"]["checked_at"] = data["prepared_at"]
    data["cost_bound"]["checked_at"] = data["prepared_at"]
    second = upload.DatasetUploadPlan.model_validate_json(reseal(data))
    assert second.binding_digest() == first.binding_digest()
    assert second.digest != first.digest


def test_valid_approval_and_revocation_are_structurally_bound():
    plan = prepared()
    record = approval(plan)
    upload.validate_approval_binding(plan, record)
    copy = upload.DatasetUploadApproval.model_validate_json(record.encoded())
    assert copy == record
    data = record.model_dump(mode="json")
    data.update(status="revoked", revoked_at="2026-11-02T11:16:00.000000Z")
    revoked = upload.DatasetUploadApproval.model_validate_json(canonical(data))
    upload.validate_approval_binding(plan, revoked)
    assert revoked.status == "revoked"


@pytest.mark.parametrize(
    "change",
    [
        "plan_id",
        "plan_digest",
        "binding_digest",
        "store_id",
        "identity_epoch",
        "clock_generation",
        "early_approval",
        "late_expiry",
        "draft_plan",
    ],
)
def test_approval_cannot_bind_other_plan_or_scope(change):
    plan = prepared()
    data = approval(plan).model_dump(mode="json")
    if change in ("plan_id", "store_id", "identity_epoch"):
        data[change] = "00000000-0000-4000-8000-000000000008"
    elif change in ("plan_digest", "binding_digest"):
        data[change] = "0" * 64
    elif change == "clock_generation":
        data[change] = 2
    elif change == "early_approval":
        data["approved_at"] = "2026-11-02T10:59:59.000000Z"
        data["expires_at"] = "2026-11-02T11:14:59.000000Z"
    elif change == "late_expiry":
        data["expires_at"] = "2026-11-02T11:15:00.000001Z"
    else:
        plan = upload.DatasetUploadPlan.model_validate_json(GOLDEN.read_bytes())
    record = upload.DatasetUploadApproval.model_validate_json(canonical(data))
    with pytest.raises(ValueError):
        upload.validate_approval_binding(plan, record)


def test_upload_manifest_bounds_and_equal_hash_names_are_separate():
    digest = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    files = tuple(DatasetFile(path=f"file-{n:03d}.png", size=0, sha256=digest) for n in range(128))
    ref = upload.manifest_reference(build_manifest(files))
    assert ref.file_count == 128
    over_files = build_manifest(files + (DatasetFile(path="z.png", size=0, sha256=digest),))
    with pytest.raises(ValueError):
        upload.manifest_reference(over_files)
    empty = build_manifest(())
    with pytest.raises(ValueError):
        upload.manifest_reference(empty)
    limit = build_manifest((DatasetFile(path="a.png", size=500_000_000, sha256=digest),))
    assert upload.manifest_reference(limit).total_bytes == 500_000_000
    above = build_manifest((DatasetFile(path="a.png", size=500_000_001, sha256=digest),))
    with pytest.raises(ValueError):
        upload.manifest_reference(above)


@pytest.mark.parametrize("extra", [0, 1])
def test_upload_input_aggregate_byte_boundary_with_individually_valid_file_sizes(extra):
    sizes = (500_000_000, 500_000_000, 73_741_824 + extra)
    files = tuple(
        DatasetFile(path=f"part-{i}.bin", size=size, sha256=str(i) * 64)
        for i, size in enumerate(sizes)
    )

    def reference():
        return upload.manifest_reference(build_manifest(files))

    if extra:
        with pytest.raises(ValueError):
            reference()
    else:
        assert reference().total_bytes == 1_073_741_824


def test_literal_intent_and_semantic_binding_digests():
    plan = upload.DatasetUploadPlan.model_validate_json(GOLDEN.read_bytes())
    assert (
        plan.intent_digest() == "6996717f0ad7f30b1e70ae153e07fd4049265cdd8cba8043e74ab11ed5a63534"
    )
    assert (
        plan.binding_digest() == "778be368dcf9e8a4bde45993d582fea628532ad8b47e474004a65c79b2d992c3"
    )


@pytest.mark.parametrize(
    "field", ["service_origin", "api_base_path", "owner", "project_id", "name"]
)
def test_every_namespace_component_changes_intent(field):
    data = payload()
    if field == "name":
        data["parameters"]["name"] = "other"
    elif field == "owner":
        data["scope"]["owner"]["kind"] = "organization"
    elif field == "service_origin":
        data["scope"][field] = "https://other.invalid"
    elif field == "api_base_path":
        data["scope"][field] = "/other"
    else:
        data["scope"][field] = "00000000-0000-4000-8000-000000000009"
    plan = upload.DatasetUploadPlan.model_validate_json(reseal(data))
    assert (
        plan.intent_digest() != "6996717f0ad7f30b1e70ae153e07fd4049265cdd8cba8043e74ab11ed5a63534"
    )


def test_independent_prepared_plan_and_approval_golden():
    raw = json.loads((FIXTURES / "dataset-upload-approved-v1.json").read_bytes())
    plan = upload.DatasetUploadPlan.model_validate_json(canonical(raw["plan"]))
    record = upload.DatasetUploadApproval.model_validate_json(canonical(raw["approval"]))
    assert prepared().encoded() == canonical(raw["plan"])
    assert approval(plan).encoded() == canonical(raw["approval"])
    upload.validate_approval_binding(plan, record)
    assert plan.status == "prepared"
    assert plan.executable is False


def captured(plan):
    from yorunge.application.dataset_upload_plan import UploadPreparation

    manifest = DatasetManifest.model_validate_json(
        (FIXTURES / "dataset-manifest-v1.json").read_bytes()
    )
    return UploadPreparation(
        plan_id=plan.plan_id,
        scope=plan.scope,
        root=plan.root,
        manifest=manifest,
        parameters=plan.parameters,
        storage=plan.storage,
        budget_micros=plan.budget_micros,
        inputs_verified=plan.inputs_verified,
        grant=plan.grant,
        cost_bound=plan.cost_bound,
        prepared_at=plan.prepared_at,
    )


def test_application_snapshot_never_invents_authority_or_price():
    from yorunge.application.dataset_upload_plan import prepare_upload_snapshot

    draft = upload.DatasetUploadPlan.model_validate_json(GOLDEN.read_bytes())
    result = prepare_upload_snapshot(captured(draft))
    assert result.encoded() == GOLDEN.read_bytes()
    assert result.grant is None
    assert result.cost_bound is None
    assert prepare_upload_snapshot(captured(prepared())) == prepared()


def test_snapshot_expiry_is_earliest_real_observation_and_status_is_derived():
    from dataclasses import replace

    from yorunge.application.dataset_upload_plan import prepare_upload_snapshot

    snapshot = captured(prepared())
    grant = snapshot.grant.model_dump(mode="json")
    grant["expires_at"] = "2026-11-02T11:01:00.000000Z"
    shorter = upload.UploadGrant.model_validate_json(canonical(grant))
    result = prepare_upload_snapshot(replace(snapshot, grant=shorter))
    assert result.expires_at == "2026-11-02T11:01:00.000000Z"
    assert result.status == "prepared"
    blocked = prepare_upload_snapshot(replace(snapshot, budget_micros=0, inputs_verified=False))
    assert blocked.status == "draft"
    assert blocked.blockers == ("cost_exceeds_budget", "inputs_unverified")


def test_wire_limit_is_checked_on_original_bytes_not_only_normalized_output():
    content = GOLDEN.read_bytes()
    exact = content + b" " * (upload.MAX_UPLOAD_PLAN_BYTES - len(content))
    assert upload.DatasetUploadPlan.model_validate_json(exact).encoded() == content
    above = exact + b" "
    with pytest.raises(ValueError):
        upload.DatasetUploadPlan.model_validate_json(above)


def test_stored_manifest_ref_does_not_trust_constructed_manifest_instances():
    manifest = DatasetManifest.model_validate_json(
        (FIXTURES / "dataset-manifest-v1.json").read_bytes()
    )
    corrupted = manifest.model_copy(update={"digest": "0" * 64})
    with pytest.raises(ValueError):
        upload.manifest_reference(corrupted)
