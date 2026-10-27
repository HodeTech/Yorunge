import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from yorunge import api
from yorunge.domain.errors import YorungeError

SCENARIOS = ["unsupported-missing-fcntl", "unsupported-with-fcntl", "native-missing-fcntl"]
CONFIG_ACTIONS = ("config-init", "activate", "set-project", "clear-project")
STATE_ACTIONS = (
    "state-init",
    "reset-preview",
    "reset",
    "restore-preview",
    "restore",
    "recover-preview",
    "recover",
    "identity",
    "doctor",
)


@pytest.mark.parametrize("scenario", SCENARIOS)
@pytest.mark.parametrize("surface", ["api", "cli"])
@pytest.mark.parametrize("action", (*STATE_ACTIONS, *CONFIG_ACTIONS))
def test_unsupported_local_operations_return_safe_error_before_io(
    config,
    tmp_path,
    scenario,
    surface,
    action,
):
    state_dir = tmp_path / "state"
    if action == "doctor":
        api.initialize_state(state_dir=state_dir)
    before = {str(path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "fixtures/guards")
    environment["YORUNGE_TEST_CREDENTIAL"] = "0"
    environment["YORUNGE_TEST_STATE"] = "1"
    environment["YORUNGE_TEST_METADATA"] = "0"
    fixture = Path(__file__).parents[1] / "fixtures/unsupported_platform.py"
    result = subprocess.run(
        [sys.executable, str(fixture), scenario, surface, action, str(config), str(state_dir)],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    expected = YorungeError(
        "config_unsupported" if action in CONFIG_ACTIONS else "state_unsupported"
    )
    assert result.returncode == 2, result.stderr
    assert result.stdout == ""
    assert json.loads(result.stderr) == expected.envelope()
    assert {
        str(path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()
    } == before


@pytest.mark.parametrize("option", ["--help", "--version"])
def test_metadata_still_works_without_local_platform_support(option):
    # The metadata guard already denies importing api/Pydantic/YAML; fcntl must stay lazy too.
    source = """
import builtins, sys
from yorunge.cli import main
original = builtins.__import__
def importing(name, *args, **kwargs):
    if name == 'fcntl':
        raise ModuleNotFoundError('synthetic missing fcntl')
    return original(name, *args, **kwargs)
builtins.__import__ = importing
sys.platform = 'win32'
raise SystemExit(main([sys.argv[1]]))
"""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "fixtures/guards")
    environment["YORUNGE_TEST_METADATA"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", source, option],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
