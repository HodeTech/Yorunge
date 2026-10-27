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


def execution_validator_fixture():
    """Trusted execution proof exists only in tests, never in the public task registry."""
    from datetime import timedelta

    from yorunge.application.capabilities import combine, policy_keys
    from yorunge.domain.capabilities import AuthorizationScope, Evidence, timestamp
    from yorunge.domain.execution import Effect, ExecutionAssessment

    class Validator:
        change = None
        calls = 0

        def observe(self, request, moment):
            self.calls += 1
            identity = request.credentials[0].identity if request.credentials else None
            key = policy_keys(
                request.context,
                request.selection,
                request.recipe,
                store_id=moment.store_id,
                identity_epoch=moment.identity_epoch,
                clock_generation=moment.generation,
                identity=identity,
            )[-1][0]
            if key.scope.service_id != "local" and (
                identity is None or request.context.account_id is None
            ):
                from yorunge.application.execution import LocalExecutionValidator

                return LocalExecutionValidator().observe(request, moment)
            scope = key.scope.model_copy(
                update={
                    "tool": key.scope.tool.model_copy(
                        update={
                            "version": "fixture-1",
                            "executable_digest": "1" * 64,
                            "environment_digest": "2" * 64,
                        }
                    )
                    if key.scope.tool
                    else None,
                    "model": key.scope.model.model_copy(update={"content_digest": "3" * 64})
                    if key.scope.model
                    else None,
                    "execution": key.scope.execution.model_copy(
                        update={
                            "runtime_id": "fixture-runtime",
                            "runtime_revision": "1",
                            "environment_digest": "4" * 64,
                        }
                    ),
                    "authorization_scope": AuthorizationScope(permissions=("read",), resources=())
                    if key.scope.service_id != "local"
                    else None,
                }
            )
            key = key.model_copy(update={"capability_id": "execution.fixture", "scope": scope})
            proof = Evidence(
                kind="local_policy" if scope.service_id == "local" else "live_account",
                producer_id="fixture-execution",
                producer_version="1",
                provenance="fixture-only",
                support="supported",
                reason_code="fixture_verified",
                checked_at=timestamp(moment.now),
                expires_at=timestamp(moment.now + timedelta(seconds=300)),
            )
            record = combine(key, None, (proof,), moment.now, replace_own=True)
            result = ExecutionAssessment(
                capabilities=(record,),
                inputs_verified=True,
                blockers=(),
                effects=(
                    Effect(
                        kind="execution",
                        service_id=scope.service_id,
                        description_code="fixture_effect",
                    ),
                ),
                parameter_mapping=(),
                parameter_losses=(),
                cost=None,
            )
            return self.change(result) if self.change else result

    return Validator()


@pytest.fixture
def execution_fixture(monkeypatch):
    from yorunge import api

    validator = execution_validator_fixture()
    monkeypatch.setattr(api, "_execution_validator", lambda: validator)
    return validator


@pytest.fixture
def execution_clock(monkeypatch):
    import time
    from datetime import UTC, datetime

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
