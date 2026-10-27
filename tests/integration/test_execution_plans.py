import hashlib
import json
import os
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from yorunge import api
from yorunge.adapters.execution_store import PLAN_COLUMNS, decode_plan
from yorunge.adapters.state import open_store
from yorunge.domain.capabilities import canonical
from yorunge.domain.errors import YorungeError
from yorunge.domain.execution import ExecutionPlan


@pytest.fixture
def inputs(tmp_path):
    root = tmp_path / "inputs"
    root.mkdir()
    (root / "manifest.json").write_text('{"data": "fixture"}')
    recipe = tmp_path / "recipe.yaml"
    recipe.write_text("schema_version: 1\ntask: llm.train\ndata: {manifest: manifest.json}\n")
    return root, recipe


def test_public_draft_and_fixture_prepared_are_separate_and_v1_remains_offline(
    tmp_path,
    inputs,
    execution_fixture,
    monkeypatch,
    cli,
):
    root, recipe = inputs
    state = tmp_path / "state"
    prepared = api.prepare_execution_plan(recipe=recipe, input_root=root, state_dir=state).data
    assert prepared.plan.status == "prepared"
    assert prepared.validity.valid
    assert prepared.plan.executable is False
    assert (
        prepared.plan.inputs[0].digest
        == hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest()
    )
    assert api.validate_execution_plan(prepared.plan.plan_id, state_dir=state).data.valid
    shown = api.show_execution_plan(prepared.plan.plan_id, state_dir=state).data
    assert shown.plan == prepared.plan
    assert shown.validity is None
    monkeypatch.undo()
    public = api.prepare_execution_plan(task="llm.train", state_dir=state).data
    assert public.plan.status == "draft"
    assert public.validity.valid is False
    assert "execution_adapter_unavailable" in public.plan.assessment.blockers
    result = cli(
        "plan",
        "execution",
        "show",
        "--plan-id",
        public.plan.plan_id,
        "--state-dir",
        str(state),
        "--output",
        "json",
        state=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["data"]["plan"]["digest"] == public.plan.digest
    assert api.prepare_plan(task="llm.train").data.schema_version == 1


def test_saved_root_survives_cwd_change_and_rejects_identical_replacement(
    tmp_path,
    inputs,
    execution_fixture,
    monkeypatch,
):
    root, recipe = inputs
    state = tmp_path / "state"
    monkeypatch.chdir(tmp_path)
    prepared = api.prepare_execution_plan(
        recipe=recipe, input_root=type(root)("inputs"), state_dir=state
    ).data.plan
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    (decoy / "inputs").mkdir()
    (decoy / "inputs" / "manifest.json").write_text("decoy")
    monkeypatch.chdir(decoy)
    assert api.validate_execution_plan(prepared.plan_id, state_dir=state).data.valid
    root.rename(tmp_path / "original-inputs")
    root.mkdir()
    (root / "manifest.json").write_bytes(
        (tmp_path / "original-inputs" / "manifest.json").read_bytes()
    )
    invalid = api.validate_execution_plan(prepared.plan_id, state_dir=state).data
    assert invalid.valid is False
    assert "inputs_changed" in invalid.reasons
    assert api.show_execution_plan(prepared.plan_id, state_dir=state).data.plan == prepared


def test_same_size_mtime_content_change_is_detected(tmp_path, inputs, execution_fixture):
    root, recipe = inputs
    plan = api.prepare_execution_plan(
        recipe=recipe, input_root=root, state_dir=tmp_path / "state"
    ).data.plan
    file = root / "manifest.json"
    before = file.stat()
    file.write_bytes(b"X" * before.st_size)
    os.utime(file, ns=(before.st_atime_ns, before.st_mtime_ns))
    result = api.validate_execution_plan(plan.plan_id, state_dir=tmp_path / "state").data
    assert result.valid is False
    assert "inputs_changed" in result.reasons


@pytest.mark.parametrize("change", ["tool", "environment", "model", "source", "constraints"])
def test_current_trusted_binding_change_invalidates_without_rewriting_saved_plan(
    tmp_path,
    recipe,
    execution_fixture,
    change,
):
    recipe.write_text(
        "schema_version: 1\ntask: llm.train\n"
        "model: {source: huggingface, id: org/model, revision: main}\n"
    )
    state = tmp_path / "state"
    plan = api.prepare_execution_plan(recipe=recipe, state_dir=state).data.plan

    def mutate(assessment):
        from yorunge.domain.capabilities import Constraint

        record = assessment.capabilities[0]
        scope = record.key.scope
        if change == "tool":
            scope = scope.model_copy(
                update={"tool": scope.tool.model_copy(update={"version": "fixture-2"})}
            )
        elif change == "environment":
            scope = scope.model_copy(
                update={
                    "execution": scope.execution.model_copy(update={"environment_digest": "a" * 64})
                }
            )
        elif change == "model":
            scope = scope.model_copy(
                update={"model": scope.model.model_copy(update={"content_digest": "b" * 64})}
            )
        proofs = record.evidence
        if change == "source":
            proofs = (proofs[0].model_copy(update={"producer_version": "2"}),)
        elif change == "constraints":
            proofs = (
                proofs[0].model_copy(update={"constraints": (Constraint(name="quota", value=1),)}),
            )
        record = record.model_copy(
            update={"key": record.key.model_copy(update={"scope": scope}), "evidence": proofs}
        )
        return assessment.model_copy(update={"capabilities": (record,)})

    execution_fixture.change = mutate
    result = api.validate_execution_plan(plan.plan_id, state_dir=state).data
    assert result.valid is False
    assert "execution_bindings_changed" in result.reasons
    assert api.show_execution_plan(plan.plan_id, state_dir=state).data.plan == plan


def test_custom_context_requires_explicit_reselection_and_secret_is_read_once(
    tmp_path,
    execution_fixture,
    monkeypatch,
):
    config = tmp_path / "custom.toml"
    marker = "PRIVATE_REFERENCE_MARKER"
    config.write_text(
        'schema_version=1\nactive_profile="default"\n[profiles.default]\n'
        '[profiles.work]\naccount_id="account"\nplatform_key_env="' + marker + '"\n'
    )
    monkeypatch.setenv(marker, "fixture-secret-marker")
    reads = []
    from yorunge.adapters.secrets import EnvSecretReader

    original = EnvSecretReader.read

    def read(self, reference):
        reads.append(reference.name)
        return original(self, reference)

    monkeypatch.setattr(EnvSecretReader, "read", read)
    state = tmp_path / "state"
    plan = api.prepare_execution_plan(
        task="dataset.upload", config=config, profile="work", project="project", state_dir=state
    ).data.plan
    assert reads == [marker]
    reads.clear()
    assert api.validate_execution_plan(
        plan.plan_id, config=config, profile="work", project="project", state_dir=state
    ).data.valid
    assert reads == [marker]
    assert marker not in plan.model_dump_json()
    assert "fixture-secret-marker" not in repr(plan)
    assert not api.validate_execution_plan(plan.plan_id, config=config, state_dir=state).data.valid
    monkeypatch.setenv(marker, "different-fixture-secret")
    assert not api.validate_execution_plan(
        plan.plan_id, config=config, profile="work", project="project", state_dir=state
    ).data.valid
    assert api.show_execution_plan(plan.plan_id, state_dir=state).data.plan.digest == plan.digest


def test_list_is_bounded_and_does_not_open_inputs_or_env(tmp_path, execution_fixture, monkeypatch):
    state = tmp_path / "state"
    plans = [
        api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan for _ in range(3)
    ]
    monkeypatch.setattr(
        "yorunge.adapters.secrets.EnvSecretReader.read", lambda *a: pytest.fail("env read")
    )
    monkeypatch.setattr(
        "yorunge.adapters.input_files.DescriptorInputs.bind", lambda *a: pytest.fail("input read")
    )
    first = api.list_execution_plans(limit=2, state_dir=state).data
    second = api.list_execution_plans(limit=2, cursor=first.next_cursor, state_dir=state).data
    assert [p.plan_id for p in (*first.plans, *second.plans)] == [p.plan_id for p in plans]
    assert second.next_cursor is None
    for bad in (0, 101, True, "50"):
        with pytest.raises(YorungeError):
            api.list_execution_plans(limit=bad, state_dir=state)
    with pytest.raises(YorungeError):
        api.list_execution_plans(cursor="bad", state_dir=state)
    assert api.show_execution_plan(plans[0].plan_id, state_dir=state).data.plan == plans[0]


def test_plan_corruption_is_rejected_before_epoch_reset(tmp_path, execution_fixture):
    state = tmp_path / "state"
    api.prepare_execution_plan(task="llm.train", state_dir=state)
    with open_store(state) as store:
        row = store.connection.execute(f"SELECT {PLAN_COLUMNS} FROM execution_plans").fetchone()
        damaged = list(row)
        body = json.loads(damaged[-1])
        body["digest"] = "0" * 64
        damaged[-1] = json.dumps(body)
        with pytest.raises(YorungeError):
            decode_plan(tuple(damaged))
        store.connection.execute("UPDATE execution_plans SET payload=?", (damaged[-1],))
    with pytest.raises(YorungeError) as error:
        api.preview_identity_reset(state_dir=state)
    assert error.value.code == "state_invalid"
    with pytest.raises(ValidationError):
        ExecutionPlan.model_validate_json(canonical(body))


def test_plan_changes_stale_maintenance_preview_but_cache_churn_does_not(
    tmp_path, execution_fixture
):
    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    preview = api.preview_identity_reset(state_dir=state).data
    assert preview.schema_version == 2
    assert preview.current.plan_count == 1
    api.query_capabilities(task="llm.train", state_dir=state, refresh=True)
    assert api.preview_identity_reset(state_dir=state).data.digest == preview.digest
    api.prepare_execution_plan(task="llm.train", state_dir=state)
    with pytest.raises(YorungeError) as error:
        api.reset_identity(preview.digest, state_dir=state)
    assert error.value.code == "state_changed"
    final = api.preview_identity_reset(state_dir=state).data
    api.reset_identity(final.digest, state_dir=state)
    assert api.show_execution_plan(plan.plan_id, state_dir=state).data.plan == plan
    assert not api.validate_execution_plan(plan.plan_id, state_dir=state).data.valid


@pytest.fixture
def execution_clock(monkeypatch):
    import time

    class Clock:
        value = datetime(2026, 10, 28, tzinfo=UTC)
        elapsed = 0

        def now(self):
            return self.value

        def monotonic(self):
            return time.monotonic() + self.elapsed

    clock = Clock()
    monkeypatch.setattr("yorunge.adapters.capability_cache.SystemClock", lambda: clock)
    return clock


def test_semantic_revalidation_does_not_extend_original_expiry_and_clock_fences_restart(
    tmp_path,
    execution_fixture,
    execution_clock,
):
    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    execution_clock.value += timedelta(seconds=100)
    result = api.validate_execution_plan(plan.plan_id, state_dir=state).data
    assert result.valid
    assert result.valid_until == plan.expires_at
    assert api.show_execution_plan(plan.plan_id, state_dir=state).data.plan == plan
    execution_clock.value -= timedelta(seconds=1)
    assert not api.validate_execution_plan(plan.plan_id, state_dir=state).data.valid
    execution_clock.value += timedelta(seconds=1)
    assert not api.validate_execution_plan(plan.plan_id, state_dir=state).data.valid
    with open_store(state) as store:
        assert store.connection.execute("SELECT clock_generation FROM cache_clock").fetchone() == (
            2,
        )


def test_exact_expiry_and_producer_total_budget_cannot_validate(
    tmp_path, execution_fixture, execution_clock
):
    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    execution_clock.value += timedelta(seconds=300)
    assert not api.validate_execution_plan(plan.plan_id, state_dir=state).data.valid
    execution_fixture.change = lambda assessment: (
        setattr(execution_clock, "elapsed", 30) or assessment
    )
    with pytest.raises(YorungeError) as failure:
        api.prepare_execution_plan(task="llm.train", state_dir=state)
    assert failure.value.code == "execution_timeout"


@pytest.mark.parametrize("after_commit", [False, True])
def test_plan_final_write_and_commit_delay_have_separate_expiry_gates(
    tmp_path,
    monkeypatch,
    execution_fixture,
    execution_clock,
    after_commit,
):
    original = api._execution_repository
    inserted = False

    def repository(*args):
        result = original(*args)

        def move(statement):
            nonlocal inserted
            if statement.startswith("INSERT INTO execution_plans"):
                inserted = True
                if not after_commit:
                    execution_clock.value += timedelta(seconds=300)
            elif statement == "COMMIT" and inserted:
                inserted = False
                if after_commit:
                    execution_clock.value += timedelta(seconds=300)

        result.store.connection.set_trace_callback(move)
        return result

    monkeypatch.setattr(api, "_execution_repository", repository)
    state = tmp_path / "state"
    if after_commit:
        prepared = api.prepare_execution_plan(task="llm.train", state_dir=state).data
        assert prepared.validity.valid is False
        assert prepared.plan.status == "prepared"  # immutable historical body remains visible
        assert (
            api.show_execution_plan(prepared.plan.plan_id, state_dir=state).data.plan
            == prepared.plan
        )
    else:
        with pytest.raises(YorungeError) as failure:
            api.prepare_execution_plan(task="llm.train", state_dir=state)
        assert failure.value.code == "plan_not_valid"
        assert api.list_execution_plans(state_dir=state).data.plans == ()


def test_plan_quota_and_pagination_are_real_database_constraints(tmp_path, execution_fixture):
    from uuid import uuid4

    state = tmp_path / "state"
    first = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    rows = []
    for _ in range(1023):
        body = first.model_dump(mode="json", exclude={"digest"})
        body["plan_id"] = str(uuid4())
        body["digest"] = hashlib.sha256(canonical(body)).hexdigest()
        plan = ExecutionPlan.model_validate_json(canonical(body))
        rows.append(
            (
                plan.plan_id,
                plan.digest,
                plan.selection.task,
                plan.prepared_at,
                plan.expires_at,
                plan.status,
                canonical(plan.model_dump(mode="json")).decode("ascii"),
            )
        )
    with open_store(state) as store:
        store.connection.execute("BEGIN")
        store.connection.executemany("INSERT INTO execution_plans VALUES(?,?,?,?,?,?,?)", rows)
        store.connection.execute("COMMIT")
        assert store.verify().store_schema_version >= 3
    with pytest.raises(YorungeError) as failure:
        api.prepare_execution_plan(task="llm.train", state_dir=state)
    assert failure.value.code == "plan_capacity_exceeded"
    seen, cursor = set(), None
    while True:
        page = api.list_execution_plans(limit=100, cursor=cursor, state_dir=state).data
        seen.update(p.plan_id for p in page.plans)
        cursor = page.next_cursor
        if cursor is None:
            break
    assert len(seen) == 1024
    assert first.plan_id in seen


def test_credential_rotation_inside_producer_rejects_the_stale_snapshot(
    tmp_path,
    config,
    execution_fixture,
    monkeypatch,
):
    # Fixture config needs a named account for positive remote authority.
    config.write_text(
        config.read_text().replace("[profiles.work]", '[profiles.work]\naccount_id="account"')
    )
    state = tmp_path / "state"

    def rotate(assessment):
        monkeypatch.setenv("EVREN_PLATFORM_API_KEY", "rotated-during-execution-fixture")
        api.observe_credential("evren-platform", config=config, state_dir=state)
        return assessment

    execution_fixture.change = rotate
    with pytest.raises(YorungeError) as failure:
        api.prepare_execution_plan(
            task="dataset.upload", config=config, project="project", state_dir=state
        )
    assert failure.value.code == "state_changed"
    assert api.list_execution_plans(state_dir=state).data.plans == ()


@pytest.mark.parametrize("mismatch", ["account", "project", "local", "planning_only", "target"])
def test_execution_authority_must_match_full_request_scope(
    tmp_path,
    config,
    execution_fixture,
    mismatch,
):
    config.write_text(
        config.read_text().replace("[profiles.work]", '[profiles.work]\naccount_id="account"')
    )
    state = tmp_path / "state"
    plan = api.prepare_execution_plan(
        task="dataset.upload", config=config, project="project", state_dir=state
    ).data.plan

    def wrong_scope(assessment):
        record = assessment.capabilities[0]
        key = record.key
        scope = key.scope
        proof = record.evidence[0]
        if mismatch in ("account", "project"):
            scope = scope.model_copy(update={mismatch + "_id": "different"})
        elif mismatch in ("local", "planning_only"):
            scope = scope.model_copy(
                update={
                    "service_id": "local",
                    "service_origin": None,
                    "api_base_path": None,
                    "credential_id": None,
                    "credential_revision": None,
                    "authorization_scope": None,
                }
            )
            proof = proof.model_copy(update={"kind": "local_policy"})
            if mismatch == "planning_only":
                key = key.model_copy(update={"capability_id": "planning.offline"})
        else:
            scope = scope.model_copy(update={"api_base_path": "/different"})
        key = key.model_copy(update={"scope": scope})
        return assessment.model_copy(
            update={"capabilities": (record.model_copy(update={"key": key, "evidence": (proof,)}),)}
        )

    execution_fixture.change = wrong_scope
    with pytest.raises(YorungeError) as failure:
        api.prepare_execution_plan(
            task="dataset.upload", config=config, project="project", state_dir=state
        )
    assert failure.value.code == "plan_not_valid"
    invalid = api.validate_execution_plan(
        plan.plan_id, config=config, project="project", state_dir=state
    ).data
    assert invalid.valid is False
    assert "current_validation_blocked" in invalid.reasons
    # A newly hashed hostile body is still rejected structurally, without live validation.
    body = plan.model_dump(mode="json", exclude={"digest"})
    body["assessment"] = wrong_scope(plan.assessment).model_dump(mode="json")
    body["digest"] = hashlib.sha256(canonical(body)).hexdigest()
    with pytest.raises(ValueError):
        ExecutionPlan.model_validate_json(canonical(body))
