import json
import os
from pathlib import Path

import pytest

from yorunge import api
from yorunge.adapters.files import load_config, load_recipe
from yorunge.domain.errors import YorungeError

SECRET = "synthetic-secret-NEVER-PRINT-48291"


@pytest.mark.parametrize(
    "text",
    [
        "",
        "[profiles",
        'schema_version = "1"',
        "schema_version = 1\nschema_version = 1",
        'schema_version = 2\nactive_profile = "work"\n[profiles.work]',
        'schema_version = true\nactive_profile = "work"\n[profiles.work]',
        'schema_version = 1\nactive_profile = "missing"\n[profiles.work]',
        'schema_version = 1\nactive_profile = "work"\n[profiles.work]\nproject_id = 1',
        f'schema_version = 1\nactive_profile = "work"\n[profiles.work]\napi_key = "{SECRET}"',
        f'schema_version = 1\nactive_profile = "work"\n[profiles.work]\n"{SECRET}" = "x"',
        'schema_version = 1\nactive_profile = "work"\n[profiles.work]\n'
        'platform_url = "https://evren-llmapi.ssyz.org.tr/v1"',
        f'schema_version = 1\nactive_profile = "work"\n[profiles.work]\n'
        f'platform_url = "https://user:{SECRET}@example.test/api"',
        'schema_version = 1\nactive_profile = "work"\n[profiles.work]\n'
        'platform_url = "https://example.test:bad/api"',
        'schema_version = 1\nactive_profile = "work"\n[profiles.work.tools.defaults]\n'
        '"dataset.upload" = "forgelm"',
    ],
)
def test_invalid_config_is_safe(tmp_path, text):
    path = tmp_path / "profile.toml"
    path.write_text(text)
    with pytest.raises(YorungeError) as failure:
        load_config(path)
    assert failure.value.code == "invalid_config"
    assert SECRET not in str(failure.value)
    assert SECRET not in json.dumps(failure.value.envelope())


@pytest.mark.parametrize(
    "text",
    [
        "",
        "[broken",
        "schema_version: 1\nschema_version: 1\ntask: llm.train",
        "schema_version: true\ntask: llm.train",
        "schema_version: 2\ntask: llm.train",
        "schema_version: 1\ntask: llm.train\ntraining: {method: sft, epochs: '1'}",
        "schema_version: 1\ntask: llm.train\ntraining: {method: sft, epochs: true}",
        "schema_version: 1\ntask: llm.train\ntraining: {method: sft, epochs: .nan}",
        "schema_version: 1\ntask: llm.train\ntraining: {method: sft, epochs: .inf}",
        "schema_version: 1\ntask: llm.train\ntraining: {method: sft, epochs: 0}",
        "schema_version: 1\ntask: llm.train\ntool: {id: forgelm, id: axolotl}",
        "schema_version: 1\ntask: llm.train\nprovider_options: {forgelm: {shell: command}}",
        "schema_version: 1\ntask: llm.train\ndata: {manifest: 'https://example.test/file'}",
        "schema_version: 1\ntask: llm.train\nproject: &project value\nprofile: *project",
        "!!python/object/apply:os.system ['false']",
        "schema_version: 1\ntask: llm.train\n---\nschema_version: 1",
        f"schema_version: 1\ntask: llm.train\nsecret: {SECRET}",
        "schema_version: 1\ntask: llm.train\nx: " + "[" * 40 + "0" + "]" * 40,
        "schema_version: 1\ntask: llm.train\nx: [" + ",".join("0" for _ in range(2100)) + "]",
    ],
)
def test_invalid_recipe_is_safe(tmp_path, text):
    path = tmp_path / "recipe.yaml"
    path.write_text(text)
    with pytest.raises(YorungeError) as failure:
        load_recipe(path)
    assert failure.value.code == "invalid_recipe"
    assert SECRET not in str(failure.value)


def test_file_limits_encoding_and_missing_file(tmp_path):
    path = tmp_path / "config.toml"
    with pytest.raises(YorungeError) as failure:
        api.show_context(config=path)
    assert failure.value.code == "file_unreadable"
    path.write_bytes(b"\xff")
    with pytest.raises(YorungeError):
        load_config(path)
    path.write_text(" " * 65_537)
    with pytest.raises(YorungeError) as failure:
        load_config(path)
    assert failure.value.code == "invalid_config"
    with pytest.raises(YorungeError):
        load_config(tmp_path)


def test_missing_profile_is_controlled(config):
    with pytest.raises(YorungeError) as failure:
        api.show_context(config=config, profile="missing")
    assert failure.value.code == "profile_not_found"


@pytest.mark.parametrize(
    "fragment", ['"schema_version": 1, "schema_version": 1', '"amount": NaN', '"amount": Infinity']
)
def test_saved_json_rejects_duplicates_and_nonfinite(tmp_path, fragment):
    path = tmp_path / "plan.json"
    path.write_text("{" + fragment + "}")
    with pytest.raises(YorungeError) as failure:
        api.load_plan(path)
    assert failure.value.code == "invalid_plan"


def test_valid_secret_refs_never_resolve_or_appear_in_result(config, monkeypatch, caplog):
    original = type(os.environ).__getitem__

    def guarded(environ, key):
        if key in ("EVREN_PLATFORM_API_KEY", "EVREN_LLM_API_KEY"):
            raise AssertionError("credential lookup is forbidden")
        return original(environ, key)

    monkeypatch.setattr(type(os.environ), "__getitem__", guarded)
    context = api.show_context(config=config)
    plan = api.prepare_plan(config=config, task="llm.train")
    output = context.model_dump_json() + plan.model_dump_json() + caplog.text
    assert SECRET not in output
    assert "EVREN_PLATFORM_API_KEY" not in output
    assert plan.data.context.project_id is None


@pytest.mark.parametrize("use_case", ["context", "recipe", "saved"])
def test_embedded_nul_path_is_a_controlled_file_error(use_case):
    path = Path("\x00")
    with pytest.raises(YorungeError) as failure:
        if use_case == "context":
            api.show_context(config=path)
        elif use_case == "recipe":
            api.prepare_plan(recipe=path)
        else:
            api.load_plan(path)
    assert failure.value.code == "file_unreadable"


def test_inaccessible_default_config_does_not_fall_back(monkeypatch):
    original = Path.exists

    def guarded(path):
        if path.name == "config.toml":
            raise PermissionError(SECRET)
        return original(path)

    monkeypatch.setattr(Path, "exists", guarded)
    with pytest.raises(YorungeError) as failure:
        api.show_context()
    assert failure.value.code == "file_unreadable"
    assert SECRET not in str(failure.value)
