import json
from importlib.metadata import version
from pathlib import Path

import pytest

from yorunge import __version__, api


def test_installed_metadata_and_import_origin():
    import yorunge

    assert version("yorunge") == __version__
    expected = Path(__file__).resolve().parents[2] / "src" / "yorunge" / "__init__.py"
    assert Path(yorunge.__file__).resolve() == expected


@pytest.mark.parametrize(
    "args",
    [
        ("--help",),
        ("--version",),
        ("train", "plan", "--help"),
        ("plan", "prepare", "--help"),
        ("context", "show", "--help"),
    ],
)
def test_installed_metadata_entrypoint_has_no_side_effects(cli, args):
    result = cli(*args, metadata=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout and result.stderr == ""
    assert "Traceback" not in result.stdout
    if args == ("--version",):
        assert result.stdout.strip() == f"yorunge {__version__}"


def test_cli_and_python_have_identical_results(cli, config, recipe):
    command = cli(
        "train",
        "plan",
        "--config",
        str(config),
        "--recipe",
        str(recipe),
        "--tool",
        "axolotl",
        "--output",
        "json",
    )
    python = api.prepare_plan(config=config, recipe=recipe, task="llm.train", tool="axolotl")
    assert command.returncode == 0, command.stderr
    assert json.loads(command.stdout) == python.model_dump(mode="json")
    assert command.stderr == ""
    assert command.stdout.count("\n") == 1


def test_local_context_and_capabilities_are_offline(cli, config):
    context = cli("--output", "json", "context", "show", "--config", str(config))
    assert context.returncode == 0, context.stderr
    assert json.loads(context.stdout) == api.show_context(config=config).model_dump(mode="json")
    capabilities = cli("capabilities", "--task", "dataset.upload", "--output", "json")
    assert capabilities.returncode == 0, capabilities.stderr
    assert json.loads(capabilities.stdout) == api.inspect_capabilities(
        task="dataset.upload",
    ).model_dump(mode="json")


@pytest.mark.parametrize(
    "args,code",
    [
        (("--unknown", "synthetic-secret-NEVER-PRINT-48291"), "invalid_request"),
        (("plan", "prepare"), "invalid_request"),
        (("plan", "prepare", "--task", "llm.train", "--tool", "missing"), "tool_unavailable"),
        (
            ("plan", "prepare", "--task", "dataset.upload", "--tool", "forgelm"),
            "unsupported_combination",
        ),
        (
            ("context", "show", "--config", "/missing/synthetic-secret-NEVER-PRINT-48291"),
            "file_unreadable",
        ),
    ],
)
def test_json_errors_have_no_stdout_and_safe_exit_code(cli, args, code):
    result = cli(*args, "--output", "json")
    assert result.returncode == 2
    assert result.stdout == ""
    error = json.loads(result.stderr)
    assert error["code"] == code
    assert error["retryable"] is False and error["operation_id"] is None
    assert "synthetic-secret" not in result.stderr
    assert result.stderr.count("\n") == 1


def test_plan_show_preserves_saved_selection(cli, config, tmp_path):
    plan = api.prepare_plan(task="llm.train", config=config).data
    path = tmp_path / "plan.json"
    path.write_text(plan.model_dump_json())
    config.write_text("invalid")
    command = cli("plan", "show", "--plan", str(path), "--output=json")
    assert command.returncode == 0, command.stderr
    assert json.loads(command.stdout)["data"] == plan.model_dump(mode="json")


def test_documented_examples_run(cli):
    root = Path(__file__).resolve().parents[2]
    result = cli(
        "train",
        "plan",
        "--config",
        str(root / "examples/profile.toml"),
        "--recipe",
        str(root / "examples/training.yaml"),
    )
    assert result.returncode == 0, result.stderr
    assert "yürütülemez" in result.stdout


def test_option_abbreviations_are_rejected_consistently(cli):
    result = cli("--output", "json", "--out", "json", "--invalid-option")
    assert result.returncode == 2 and result.stdout == ""
    assert json.loads(result.stderr)["code"] == "invalid_request"


def test_cli_config_and_recipe_errors_are_safe(cli, tmp_path):
    config = tmp_path / "bad.toml"
    config.write_text('schema_version = 1\nsecret = "synthetic-secret-NEVER-PRINT-48291"')
    recipe = tmp_path / "bad.yaml"
    recipe.write_text("schema_version: 1\ntask: llm.train\nsecret: hidden")
    for args, code in (
        (("context", "show", "--config", str(config)), "invalid_config"),
        (("train", "plan", "--recipe", str(recipe)), "invalid_recipe"),
    ):
        result = cli(*args, "--output", "json")
        assert result.returncode == 2 and result.stdout == ""
        assert json.loads(result.stderr)["code"] == code
        assert "synthetic-secret" not in result.stderr


@pytest.mark.parametrize(
    "case",
    [
        "context",
        "offline-capability",
        "cached",
        "refresh",
        "offline-plan",
        "execution",
        "state-init",
    ],
)
def test_commands_without_recipe_do_not_import_yaml(tmp_path, cli, config, case):
    root = str(tmp_path / "state")
    commands = {
        "context": ("context", "show", "--config", str(config)),
        "offline-capability": ("capabilities", "--task", "llm.train"),
        "cached": ("capabilities", "--task", "llm.train", "--cached", "--state-dir", root),
        "refresh": ("capabilities", "--task", "llm.train", "--refresh", "--state-dir", root),
        "offline-plan": ("plan", "prepare", "--task", "llm.train"),
        "execution": ("plan", "execution", "prepare", "--task", "llm.train", "--state-dir", root),
        "state-init": ("state", "init", "--state-dir", root),
    }
    result = cli(
        *commands[case],
        "--output",
        "json",
        recipe_loader=False,
        state=case in ("cached", "refresh", "execution", "state-init"),
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "completed"
    assert result.stderr == ""
