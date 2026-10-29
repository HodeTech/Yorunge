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
        recipe_loader: bool = True,
        legacy_schema5: bool = False,
    ):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "tests" / "fixtures" / "guards")
        environment["YORUNGE_TEST_METADATA"] = "1" if metadata else "0"
        environment["YORUNGE_TEST_YAML"] = "1" if recipe_loader else "0"
        environment["YORUNGE_TEST_CREDENTIAL"] = "1" if credential else "0"
        environment["YORUNGE_TEST_STATE"] = "1" if state else "0"
        environment["YORUNGE_TEST_SECRET_NAMES"] = json.dumps(secret_names)
        command = [str(Path(sys.executable).parent / "yorunge"), *args]
        if legacy_schema5:
            command = [
                sys.executable,
                "-c",
                (
                    "from yorunge.adapters import state_schema; "
                    "state_schema.MIGRATIONS=state_schema.MIGRATIONS[:5]; "
                    "from yorunge.cli import main; raise SystemExit(main())"
                ),
                *args,
            ]
        return subprocess.run(
            command,
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


@pytest.fixture
def operation_setup(tmp_path, execution_fixture, execution_clock):
    from tests.fixtures.operation_backend import ProcessBackend
    from yorunge import api

    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    approval = api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state).data
    assert approval.effective
    return state, plan, ProcessBackend(tmp_path / "effects")


@pytest.fixture
def admitted_operation(tmp_path, execution_fixture, execution_clock, request):
    """Real private DB record; no fixture task is registered in the product."""
    from datetime import timedelta
    from uuid import uuid4

    from yorunge import api
    from yorunge.adapters.operation_store import insert_record, plan_authorities
    from yorunge.adapters.state import open_store
    from yorunge.domain.capabilities import timestamp
    from yorunge.domain.operations import (
        AttemptView,
        JobSummary,
        OperationAdmission,
        OperationEvent,
        OperationLease,
        OperationRecord,
    )

    root = tmp_path / "state"
    delivery_required = getattr(request, "param", False)
    if not delivery_required:
        execution_fixture.change = lambda assessment: assessment.model_copy(
            update={
                "effects": tuple(
                    effect.model_copy(update={"kind": "local_read"})
                    for effect in assessment.effects
                )
            }
        )
    plan = api.prepare_execution_plan(task="llm.train", state_dir=root).data.plan
    approval = api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=root).data.record
    identifier, attempt_id = str(uuid4()), str(uuid4())
    now = timestamp(execution_clock.value)
    admission = OperationAdmission(
        operation_id=identifier,
        plan_id=plan.plan_id,
        plan_digest=plan.digest,
        store_id=plan.store_id,
        admission_identity_epoch=plan.identity_epoch,
        admission_clock_generation=plan.clock_generation,
        approval=approval,
        authorities=plan_authorities(plan),
        correlation=str(uuid4()),
        delivery_required=delivery_required,
    )
    summary = JobSummary(
        operation_id=identifier,
        plan_id=plan.plan_id,
        plan_digest=plan.digest,
        task=plan.selection.task,
        tool=plan.selection.tool,
        execution=plan.selection.execution,
        created_at=now,
        updated_at=now,
        status="admitted",
        execution_status="not_started",
        delivery_status="pending" if delivery_required else "not_required",
        attempt_count=1,
        revision=1,
        clock_anomaly=False,
    )
    record = OperationRecord(
        admission=admission,
        summary=summary,
        lease=OperationLease(
            owner_id=str(uuid4()),
            fence=1,
            ownership_identity_epoch=plan.identity_epoch,
            ownership_clock_generation=plan.clock_generation,
            expires_at=timestamp(execution_clock.value + timedelta(seconds=30)),
        ),
        fence=1,
        dispatch_attempt_id=None,
        event_count=1,
        recovery_reason=None,
        observed_identity_epoch=plan.identity_epoch,
        observed_clock_generation=plan.clock_generation,
    )
    attempt = AttemptView(
        attempt_id=attempt_id,
        number=1,
        created_at=now,
        updated_at=now,
        status="claimed",
        provider_run_id=None,
        provider_status=None,
        provider_exit_code=None,
        reason_code=None,
    )
    event = OperationEvent(
        sequence=1,
        revision=1,
        fence=1,
        attempt_id=attempt_id,
        observed_at=now,
        identity_epoch=plan.identity_epoch,
        clock_generation=plan.clock_generation,
        status="admitted",
        execution_status="not_started",
        delivery_status="pending" if delivery_required else "not_required",
        reason_code=None,
    )
    with open_store(root) as store:
        store.connection.execute("BEGIN IMMEDIATE")
        insert_record(store.connection, record, attempt, event)
        store.connection.execute("COMMIT")
    return root, plan, record, attempt, event


@pytest.fixture
def schema5_runtime(monkeypatch):
    """Replay the delivered pre-operation runtime, never bypass the schema-6 gate."""
    from yorunge.adapters import state_schema

    monkeypatch.setattr(state_schema, "MIGRATIONS", state_schema.MIGRATIONS[:5])
