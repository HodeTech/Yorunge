from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SECRET = "synthetic-secret-NEVER-PRINT-48291"


@pytest.fixture(autouse=True)
def offline_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("EVREN_PLATFORM_API_KEY", SECRET)
    monkeypatch.setenv("EVREN_LLM_API_KEY", SECRET)

    def denied(*args, **kwargs):
        raise AssertionError("network is forbidden in offline tests")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


@pytest.fixture
def cli():
    def invoke(
        *args: str,
        metadata: bool = False,
        credential: bool = False,
        state: bool = False,
        secret_names: tuple[str, ...] = (),
    ):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "tests" / "fixtures" / "guards")
        environment["YORUNGE_TEST_METADATA"] = "1" if metadata else "0"
        environment["YORUNGE_TEST_CREDENTIAL"] = "1" if credential else "0"
        environment["YORUNGE_TEST_STATE"] = "1" if state else "0"
        environment["YORUNGE_TEST_SECRET_NAMES"] = json.dumps(secret_names)
        return subprocess.run(
            [str(Path(sys.executable).parent / "yorunge"), *args],
            capture_output=True,
            text=True,
            env=environment,
            timeout=10,
        )

    return invoke


@pytest.fixture
def config(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("""schema_version = 1
active_profile = "work"
[profiles.work]
platform_key_env = "EVREN_PLATFORM_API_KEY"
llm_key_env = "EVREN_LLM_API_KEY"
[profiles.work.tools.defaults]
"llm.train" = "axolotl"
[profiles.other]
project_id = "other-project"
""")
    return path


@pytest.fixture
def recipe(tmp_path):
    path = tmp_path / "recipe.yaml"
    path.write_text("""schema_version: 1
task: llm.train
profile: work
project: recipe-project
tool: {id: llamafactory}
execution: {backend: local}
training: {method: sft, epochs: 1}
""")
    return path
