"""Exercise malformed external input through the real API and console boundary."""

import hashlib
import json

import pytest

from yorunge import api
from yorunge.domain.errors import YorungeError

MARKER = "synthetic-secret-48291"
MALFORMED_TAGS = [
    pytest.param(f"task: !!bool {MARKER}", id="bool"),
    pytest.param('task: !!int ""', id="empty-int"),
    pytest.param('task: !!float ""', id="empty-float"),
    pytest.param(f"task: !!timestamp {MARKER}", id="timestamp"),
    pytest.param('task: !!float "1:' + "00:" * 200 + '00.0"', id="float-overflow"),
    pytest.param(f"task: !!map [{MARKER}]", id="map-scalar-sequence"),
    pytest.param(f"task: !!set [{MARKER}]", id="set-scalar-sequence"),
    pytest.param("task: !!map [{}]", id="map-mapping-sequence"),
    pytest.param("task: llm.train\nprovider_options: !!map []", id="empty-map-sequence"),
    pytest.param("task: !!timestamp {=: 2026-10-27}", id="timestamp-value-mapping"),
    pytest.param(f"task: !!timestamp {{=: {MARKER}}}", id="timestamp-invalid-value-mapping"),
    pytest.param("task: !!timestamp {=: {=: nested}}", id="timestamp-nested-value-mapping"),
]
CONTROLS = [chr(value) for value in (*range(32), *range(127, 160))]


def write_plan(path, value):
    payload = {key: item for key, item in value.items() if key != "digest"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    value["digest"] = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.mark.parametrize("body", MALFORMED_TAGS)
def test_malformed_yaml_tag_is_safe_in_api_and_console(tmp_path, cli, body):
    recipe = tmp_path / "recipe.yaml"
    recipe.write_text(f"schema_version: 1\n{body}\n", encoding="utf-8")
    with pytest.raises(YorungeError) as failure:
        api.prepare_plan(recipe=recipe)
    assert failure.value.code == "invalid_recipe"
    assert MARKER not in str(failure.value)
    result = cli("plan", "prepare", "--recipe", str(recipe), "--output", "json")
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.count("\n") == 1
    assert json.loads(result.stderr) == failure.value.envelope()
    assert MARKER not in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("control", CONTROLS)
def test_manifest_controls_rejected_in_recipe_and_saved_plan(tmp_path, control):
    recipe = tmp_path / "recipe.yaml"
    manifest = "data/" + control + "manifest.json"
    recipe.write_text(
        "schema_version: 1\ntask: llm.train\ndata: {manifest: " + json.dumps(manifest) + "}\n",
        encoding="utf-8",
    )
    with pytest.raises(YorungeError) as failure:
        api.prepare_plan(recipe=recipe)
    assert failure.value.code == "invalid_recipe"
    value = api.prepare_plan(task="llm.train").data.model_dump(mode="json")
    value["recipe"]["data"] = {"manifest": manifest}
    saved = tmp_path / "plan.json"
    write_plan(saved, value)
    with pytest.raises(YorungeError) as failure:
        api.load_plan(saved)
    assert failure.value.code == "invalid_plan"


@pytest.mark.parametrize(
    "url",
    ["https://example.test/" + control + "api" for control in CONTROLS]
    + ["https://@example.test/api", "https://:@example.test/api"],
)
@pytest.mark.parametrize("field", ["platform_url", "llm_url"])
def test_service_url_rejected_in_config_and_saved_plan(tmp_path, url, field):
    config = tmp_path / "config.toml"
    config.write_text(
        'schema_version = 1\nactive_profile = "work"\n[profiles.work]\n'
        + field
        + " = "
        + json.dumps(url)
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(YorungeError) as failure:
        api.show_context(config=config)
    assert failure.value.code == "invalid_config"
    value = api.prepare_plan(task="llm.train").data.model_dump(mode="json")
    value["context"][field] = url
    saved = tmp_path / "plan.json"
    write_plan(saved, value)
    with pytest.raises(YorungeError) as failure:
        api.load_plan(saved)
    assert failure.value.code == "invalid_plan"


def test_valid_standard_yaml_and_unicode_references_roundtrip(tmp_path, cli):
    recipe = tmp_path / "recipe.yaml"
    recipe.write_text(
        "schema_version: !!int 1\ntask: !!str llm.train\n"
        'data: {manifest: "./veri/ölçüm-東京.json"}\n'
        "training: {method: sft, epochs: !!int 2}\n",
        encoding="utf-8",
    )
    plan = api.prepare_plan(recipe=recipe).data
    assert plan.recipe.data.manifest == "./veri/ölçüm-東京.json"
    assert plan.recipe.training.epochs == 2
    saved = tmp_path / "plan.json"
    saved.write_text(plan.model_dump_json(), encoding="utf-8")
    assert api.load_plan(saved).data == plan
    result = cli("plan", "show", "--plan", str(saved), "--output", "json")
    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout)["data"] == plan.model_dump(mode="json")


@pytest.mark.parametrize(
    "options,code",
    [
        ({"tool": "missing"}, "tool_unavailable"),
        ({"execution": "evren-managed"}, "unsupported_combination"),
    ],
)
def test_capability_query_and_plan_rejection_agree_with_api(cli, options, code):
    arguments = [item for name, value in options.items() for item in ("--" + name, value)]
    query = cli("capabilities", "--task", "llm.train", *arguments, "--output", "json")
    assert query.returncode == 0
    assert query.stderr == ""
    python = api.inspect_capabilities(task="llm.train", **options)
    assert json.loads(query.stdout) == python.model_dump(mode="json")
    record = python.data.records[-1]
    assert record.support == "unsupported"
    assert record.reason_code == code
    command = cli("plan", "prepare", "--task", "llm.train", *arguments, "--output", "json")
    assert command.returncode == 2
    assert command.stdout == ""
    with pytest.raises(YorungeError) as failure:
        api.prepare_plan(task="llm.train", **options)
    assert failure.value.code == code
    assert json.loads(command.stderr) == failure.value.envelope()
