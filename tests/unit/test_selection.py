import json

import pytest

from yorunge import api
from yorunge.domain.errors import YorungeError


def test_default_and_explicit_alternative():
    default = api.prepare_plan(task="llm.train").data
    alternative = api.prepare_plan(task="llm.train", tool="axolotl").data
    assert default.selection.tool == "forgelm"
    assert default.selection.tool_source == "product_default"
    assert alternative.selection.tool == "axolotl"
    assert alternative.selection.tool_source == "request"
    for plan in (default, alternative):
        assert plan.state == "draft" and plan.executable is False
        assert "adapter_not_implemented" in plan.blockers
        assert plan.digest == plan.computed_digest()


@pytest.mark.parametrize(
    "task",
    [
        "llm.data.ingest",
        "llm.data.audit",
        "llm.data.generate",
        "llm.fit.check",
        "llm.train",
        "llm.evaluate",
        "llm.merge",
        "llm.export",
    ],
)
def test_only_relevant_tasks_default_to_forgelm(task):
    assert api.prepare_plan(task=task).data.selection.tool == "forgelm"


def test_precedence_and_context(config, recipe):
    assert api.prepare_plan(config=config, task="llm.train").data.selection.tool == "axolotl"
    from_recipe = api.prepare_plan(config=config, recipe=recipe).data
    assert from_recipe.selection.tool == "llamafactory"
    assert from_recipe.selection.tool_source == "recipe"
    assert from_recipe.context.project_id == "recipe-project"
    explicit = api.prepare_plan(
        config=config,
        recipe=recipe,
        tool="forgelm",
        execution="evren-workspace",
        profile="other",
        project="explicit-project",
    ).data
    assert explicit.selection.tool == "forgelm"
    assert explicit.selection.execution == "evren-workspace"
    assert explicit.context.profile == "other"
    assert explicit.context.project_id == "explicit-project"
    assert api.show_context(config=config).data.project_id is None


@pytest.mark.parametrize("task", ["dataset.upload", "llm.chat", "vision.train.managed"])
def test_native_tasks_are_independent(task, config):
    plan = api.prepare_plan(task=task, config=config).data
    assert plan.selection.tool is None
    assert plan.selection.execution == (
        "evren-managed" if task == "vision.train.managed" else "local"
    )
    assert plan.capabilities[0].scope.service_id != "local"
    assert "service_not_verified" in plan.blockers


@pytest.mark.parametrize(
    "options,code",
    [
        ({"task": "llm.train", "execution": "evren-managed"}, "unsupported_combination"),
        ({"task": "dataset.upload", "tool": "forgelm"}, "unsupported_combination"),
        ({"task": "llm.chat", "execution": "evren-managed"}, "unsupported_combination"),
        ({"task": "llm.train", "tool": "missing"}, "tool_unavailable"),
        ({"task": "llm.train", "execution": "unknown"}, "invalid_request"),
        ({"task": "undefined"}, "invalid_request"),
        ({}, "invalid_request"),
    ],
)
def test_rejects_incompatible_selections_without_fallback(options, code):
    with pytest.raises(YorungeError) as failure:
        api.prepare_plan(**options)
    assert failure.value.code == code


def test_capabilities_distinguish_all_four_states():
    local = api.inspect_capabilities(task="llm.train").data.records
    native = api.inspect_capabilities(task="dataset.upload").data.records
    assert {r.support for r in (*local, *native)} == {
        "supported",
        "unsupported",
        "unknown",
        "requires_access",
    }
    assert all(
        r.capability_id == "planning.offline" for r in (*local, *native) if r.support == "supported"
    )
    incompatible = api.inspect_capabilities(task="llm.train", execution="evren-managed")
    assert incompatible.data.records[-1].support == "unsupported"
    assert all(r.scope.credential_id is None for r in native)


def test_saved_plan_ignores_profile_changes_and_rejects_tampering(tmp_path, config):
    original = api.prepare_plan(config=config, task="llm.train").data
    saved = tmp_path / "plan.json"
    saved.write_text(original.model_dump_json())
    config.write_text("broken config")
    assert api.load_plan(saved).data == original
    data = json.loads(saved.read_text())
    data["selection"]["tool"] = "forgelm"
    saved.write_text(json.dumps(data))
    with pytest.raises(YorungeError, match="Plan geçersiz"):
        api.load_plan(saved)


def test_digest_binds_context_parameters_and_execution(config):
    base = api.prepare_plan(config=config, task="llm.train").data.digest
    assert api.prepare_plan(config=config, task="llm.train", project="new").data.digest != base
    assert api.prepare_plan(config=config, task="llm.train", tool="forgelm").data.digest != base
    assert (
        api.prepare_plan(
            config=config,
            task="llm.train",
            execution="evren-workspace",
        ).data.digest
        != base
    )


def test_request_task_override_cannot_discard_parameters(config, recipe):
    with pytest.raises(YorungeError):
        api.prepare_plan(config=config, recipe=recipe, task="dataset.upload")


def test_workspace_contract_is_unknown_before_access_is_established():
    records = api.inspect_capabilities(task="llm.train", execution="evren-workspace").data.records
    runtime = next(record for record in records if record.capability_id == "runtime.access")
    assert runtime.support == "unknown"


def test_ipv6_service_origin_roundtrip(config, tmp_path):
    text = config.read_text().replace(
        "[profiles.work]", '[profiles.work]\nplatform_url = "https://[::1]/api/v1"'
    )
    config.write_text(text)
    plan = api.prepare_plan(task="dataset.upload", config=config).data
    assert plan.capabilities[0].scope.service_origin == "https://[::1]"
    saved = tmp_path / "plan.json"
    saved.write_text(plan.model_dump_json())
    assert api.load_plan(saved).data == plan


def test_saved_plan_cannot_forge_capability_evidence(tmp_path):
    plan = api.prepare_plan(task="llm.train").data
    forged_record = plan.capabilities[1].model_copy(update={"support": "supported"})
    forged = plan.model_copy(update={"capabilities": (plan.capabilities[0], forged_record)})
    forged = forged.model_copy(update={"digest": forged.computed_digest()})
    path = tmp_path / "forged.json"
    path.write_text(forged.model_dump_json())
    with pytest.raises(YorungeError) as failure:
        api.load_plan(path)
    assert failure.value.code == "invalid_plan"
