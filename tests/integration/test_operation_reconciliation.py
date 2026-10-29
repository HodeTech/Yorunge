import hashlib
import subprocess
import sys
from datetime import timedelta
from uuid import uuid4

import pytest

from tests.fixtures.operation_backend import ProcessBackend, ReadObserver
from yorunge import api
from yorunge.adapters.operation_store import read_job, read_operation
from yorunge.adapters.state import open_store, validate_contents
from yorunge.domain.errors import OperationError, YorungeError


@pytest.fixture
def started_operation(tmp_path, execution_fixture, execution_clock):
    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state)
    backend, observer = ProcessBackend(tmp_path / "effects"), ReadObserver(execution_clock)
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        coordinator.dispatch(identifier, claim.ownership)
    return state, plan, backend, observer, identifier, claim.ownership


@pytest.mark.parametrize(
    "execution,delivery,status",
    [
        ("submitted", "pending", "submitted"),
        ("running", "pending", "running"),
        ("succeeded", "pending", "running"),
        ("succeeded", "unknown", "unknown"),
        ("succeeded", "complete", "succeeded"),
        ("succeeded", "failed", "failed"),
        ("failed", "pending", "failed"),
        ("cancelled", "pending", "cancelled"),
    ],
)
def test_trusted_read_reducer_and_terminal_outcome(started_operation, execution, delivery, status):
    state, plan, backend, observer, identifier, owner = started_operation
    observer.execution, observer.delivery = execution, delivery
    with api._operation_session(
        plan.plan_id, backend, observer=observer, state_dir=state
    ) as coordinator:
        job = coordinator.reconcile(identifier, owner)
        assert job.operation.status == status
        assert job.operation.execution_status == execution
        assert job.operation.delivery_status == delivery
        terminal = status in {"succeeded", "failed", "cancelled"}
        assert (job.outcome is not None) == terminal
        if terminal:
            assert coordinator.reconcile(identifier, owner) == job
            assert len(observer.requests) == 1
            assert coordinator.repository.operation(identifier).lease is None
    assert len(backend.effects()) == 1
    with open_store(state) as store:
        validate_contents(store.connection)


@pytest.mark.parametrize(
    "kind,reason",
    [
        ("not_found", "provider_not_found"),
        ("unauthorized", "provider_unauthorized"),
        ("cancel_accepted", "provider_unavailable"),
        ("unavailable", "provider_unavailable"),
    ],
)
def test_absence_or_cancel_request_is_never_a_terminal_proof(started_operation, kind, reason):
    state, plan, backend, observer, identifier, owner = started_operation
    observer.kind = kind
    with api._operation_session(
        plan.plan_id, backend, observer=observer, state_dir=state
    ) as coordinator:
        job = coordinator.reconcile(identifier, owner)
        assert job.operation.status == "unknown"
        assert job.outcome is None
        assert job.attempts[-1].reason_code == reason
        assert coordinator.repository.operation(identifier).event_count == 3
    assert len(backend.effects()) == 1


@pytest.mark.parametrize(
    "mismatch", ["correlation", "run_id", "target", "account", "project", "exit", "delivery"]
)
def test_wrong_or_contradictory_observation_is_unknown(started_operation, mismatch):
    state, plan, backend, observer, identifier, owner = started_operation

    def change(result):
        if mismatch == "correlation":
            return result.model_copy(update={"correlation": str(uuid4())})
        if mismatch == "run_id":
            return result.model_copy(update={"provider_run_id": "different-job"})
        if mismatch in {"target", "account", "project"}:
            field = {"target": "service_id", "account": "account_id", "project": "project_id"}[
                mismatch
            ]
            value = "evren-platform" if mismatch == "target" else "different"
            return result.model_copy(
                update={"authority": result.authority.model_copy(update={field: value})}
            )
        if mismatch == "exit":
            return result.model_copy(update={"provider_exit_code": 1})
        return result.model_copy(
            update={"execution_status": "running", "delivery_status": "complete"}
        )

    observer.change = change
    with api._operation_session(
        plan.plan_id, backend, observer=observer, state_dir=state
    ) as coordinator:
        job = coordinator.reconcile(identifier, owner)
        assert job.operation.status == "unknown"
        assert job.attempts[-1].reason_code == "evidence_mismatch"
        assert job.attempts[-1].provider_run_id == "fixture-run-1"
        assert job.outcome is None


def test_confirmed_execution_survives_negative_and_delivery_observations(started_operation):
    state, plan, backend, observer, identifier, owner = started_operation
    observer.delivery = "pending"
    with api._operation_session(
        plan.plan_id, backend, observer=observer, state_dir=state
    ) as coordinator:
        progress = coordinator.reconcile(identifier, owner)
        assert progress.operation.execution_status == "succeeded"
        observer.kind = "not_found"
        uncertain = coordinator.reconcile(identifier, owner)
        assert uncertain.operation.status == "unknown"
        assert uncertain.operation.execution_status == "succeeded"
        assert uncertain.operation.delivery_status == "unknown"
        observer.kind, observer.execution, observer.delivery = "observed", "failed", "pending"
        contradictory = coordinator.reconcile(identifier, owner)
        assert contradictory.operation.execution_status == "succeeded"
        assert contradictory.attempts[-1].reason_code == "evidence_mismatch"
        observer.execution, observer.delivery = "succeeded", "complete"
        assert coordinator.reconcile(identifier, owner).operation.status == "succeeded"


def test_expired_plan_and_revoke_do_not_authorize_restart_or_block_historical_read(
    started_operation, execution_clock, monkeypatch
):
    state, plan, backend, observer, identifier, owner = started_operation
    api.revoke_execution_approval(plan.plan_id, state_dir=state)
    execution_clock.value += timedelta(seconds=301)
    monkeypatch.setattr(
        api, "_execution_validator", lambda: pytest.fail("history read executed validator")
    )
    monkeypatch.setattr(
        "yorunge.adapters.input_files.DescriptorInputs.bind",
        lambda *a: pytest.fail("history read hashed inputs"),
    )
    with api._operation_session(
        plan.plan_id, backend, observer=observer, state_dir=state
    ) as coordinator:
        claim = coordinator.takeover(identifier)
        assert claim.job.operation.status == "unknown"
        assert coordinator.reconcile(identifier, claim.ownership).operation.status == "succeeded"
        with pytest.raises(OperationError) as error:
            coordinator.dispatch(identifier, claim.ownership)
        assert error.value.code == "operation_conflict"
    assert len(backend.effects()) == 1


def test_reset_v3_heartbeat_stable_owner_change_invalidates_and_history_survives(started_operation):
    state, plan, backend, observer, identifier, owner = started_operation
    preview = api.preview_identity_reset(state_dir=state).data
    assert preview.schema_version == 3
    assert preview.current.operation_count == 1
    assert preview.current.attempt_count == 1
    assert preview.current.nonterminal_operation_count == 1
    assert preview.current.unknown_operation_count == 0
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        coordinator.renew(identifier, owner)
    assert api.preview_identity_reset(state_dir=state).data.digest == preview.digest
    api.reset_identity(preview.digest, state_dir=state)
    with open_store(state) as store:
        record = read_operation(store.connection, identifier)
        assert record.lease is None
        assert record.dispatch_attempt_id is not None
        assert record.recovery_reason == "identity_reset"
        assert read_job(store.connection, identifier).operation.status == "unknown"
    with api._operation_session(
        plan.plan_id, backend, observer=observer, state_dir=state
    ) as coordinator:
        with pytest.raises(OperationError) as error:
            coordinator.renew(identifier, owner)
        assert error.value.code == "operation_lease_lost"
        claim = coordinator.takeover(identifier)
        assert coordinator.reconcile(identifier, claim.ownership).operation.status == "succeeded"
    assert len(backend.effects()) == 1


def test_reset_cancels_unarmed_job_and_keeps_terminal_outcome(
    tmp_path, execution_fixture, execution_clock
):
    state = tmp_path / "state"
    backend, observer = ProcessBackend(tmp_path / "effects"), ReadObserver(execution_clock)
    identifiers = []
    for terminal in (False, True):
        plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
        api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state)
        with api._operation_session(
            plan.plan_id, backend, observer=observer, state_dir=state
        ) as coordinator:
            claim = coordinator.admit(plan.plan_id)
            identifier = claim.job.operation.operation_id
            identifiers.append(identifier)
            if terminal:
                coordinator.dispatch(identifier, claim.ownership)
                before = coordinator.reconcile(identifier, claim.ownership)
    preview = api.preview_identity_reset(state_dir=state).data
    api.reset_identity(preview.digest, state_dir=state)
    with open_store(state) as store:
        cancelled = read_job(store.connection, identifiers[0])
        assert cancelled.operation.status == "cancelled"
        assert cancelled.operation.execution_status == "not_started"
        assert cancelled.outcome.reason_code == "identity_reset"
        assert read_operation(store.connection, identifiers[0]).dispatch_attempt_id is None
        assert read_job(store.connection, identifiers[1]) == before
        validate_contents(store.connection)


def test_future_year_then_clock_correction_reset_and_reconcile_without_wait(
    tmp_path, execution_fixture, execution_clock
):
    base = execution_clock.value
    execution_clock.value += timedelta(days=365)
    state = tmp_path / "state"
    backend, observer = ProcessBackend(tmp_path / "effects"), ReadObserver(execution_clock)
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state)
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        coordinator.dispatch(identifier, claim.ownership)
    with open_store(state) as store:
        events = store.connection.execute(
            "SELECT payload FROM operation_events ORDER BY sequence"
        ).fetchall()
    execution_clock.value = base
    preview = api.preview_identity_reset(state_dir=state).data
    api.reset_identity(preview.digest, state_dir=state)
    with api._operation_session(
        plan.plan_id, backend, observer=observer, state_dir=state
    ) as coordinator:
        claim = coordinator.takeover(identifier)
        job = coordinator.reconcile(identifier, claim.ownership)
        assert job.operation.status == "succeeded"
        assert job.operation.clock_anomaly
        assert job.operation.updated_at < job.operation.created_at
    with open_store(state) as store:
        assert (
            store.connection.execute(
                "SELECT payload FROM operation_events ORDER BY sequence LIMIT 3"
            ).fetchall()
            == events
        )
        validate_contents(store.connection)
    assert len(backend.effects()) == 1


def test_current_read_credential_may_change_without_reauthorizing_execution(
    tmp_path, execution_fixture, execution_clock, monkeypatch
):
    from yorunge.adapters.operation_store import read_operation

    state, config = tmp_path / "state", tmp_path / "config.toml"
    config.write_text(
        'schema_version=1\nactive_profile="work"\n[profiles.work]\n'
        'account_id="account"\nplatform_key_env="EVREN_PLATFORM_API_KEY"\n'
    )
    backend, observer = ProcessBackend(tmp_path / "effects"), ReadObserver(execution_clock)
    plan = api.prepare_execution_plan(
        task="dataset.upload", config=config, state_dir=state
    ).data.plan
    api.approve_execution_plan(plan.plan_id, plan.digest, config=config, state_dir=state)
    with api._operation_session(
        plan.plan_id, backend, config=config, state_dir=state
    ) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        coordinator.dispatch(identifier, claim.ownership)
        admission = coordinator.repository.operation(identifier).admission
    monkeypatch.setenv("EVREN_PLATFORM_API_KEY", "rotated-private-read-token")
    current = api.observe_credential("evren-platform", config=config, state_dir=state).data.identity
    assert current.credential_revision == 2
    monkeypatch.setattr(
        api, "_execution_validator", lambda: pytest.fail("read reauthorized execution")
    )
    with api._operation_session(
        plan.plan_id, backend, observer=observer, config=config, state_dir=state
    ) as coordinator:
        job = coordinator.reconcile(identifier, claim.ownership)
        assert job.operation.status == "succeeded"
        assert observer.requests[0].authorities[0].credential_revision == 2
    with open_store(state) as store:
        assert read_operation(store.connection, identifier).admission == admission
    assert "rotated-private-read-token" not in job.model_dump_json()
    assert len(backend.effects()) == 1


@pytest.mark.parametrize("failure", ["scope", "target", "expiry", "future"])
def test_current_read_permission_is_checked_before_observation(
    tmp_path, execution_fixture, execution_clock, failure
):
    from yorunge.domain.capabilities import AuthorizationScope, timestamp

    state, config = tmp_path / "state", tmp_path / "config.toml"
    config.write_text(
        'schema_version=1\nactive_profile="work"\n[profiles.work]\n'
        'account_id="account"\nplatform_key_env="EVREN_PLATFORM_API_KEY"\n'
    )
    backend, observer = ProcessBackend(tmp_path / "effects"), ReadObserver(execution_clock)
    plan = api.prepare_execution_plan(
        task="dataset.upload", config=config, state_dir=state
    ).data.plan
    api.approve_execution_plan(plan.plan_id, plan.digest, config=config, state_dir=state)
    with api._operation_session(
        plan.plan_id, backend, config=config, state_dir=state
    ) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        coordinator.dispatch(claim.job.operation.operation_id, claim.ownership)

    def wrong(access):
        if failure in {"scope", "target"}:
            authority = access.authorities[0].model_copy(
                update={
                    "authorization_scope": AuthorizationScope(permissions=("write",), resources=())
                }
                if failure == "scope"
                else {"account_id": "other-account"}
            )
            return access.model_copy(update={"authorities": (authority,)})
        shift = -61 if failure == "expiry" else 61
        return access.model_copy(
            update={
                "checked_at": timestamp(execution_clock.value + timedelta(seconds=shift)),
                "expires_at": timestamp(execution_clock.value + timedelta(seconds=shift + 60)),
            }
        )

    observer.access_change = wrong
    with api._operation_session(
        plan.plan_id, backend, observer=observer, config=config, state_dir=state
    ) as coordinator:
        with pytest.raises(OperationError) as error:
            coordinator.reconcile(claim.job.operation.operation_id, claim.ownership)
        assert error.value.code == "state_changed"
        assert coordinator.repository.job(claim.job.operation.operation_id).outcome is None
    assert observer.requests == []


def fill_normal_history(state, identifier, *, count=255):
    from tests.integration.test_operation_store import raw_attempt, raw_record
    from yorunge.adapters.operation_store import append_event
    from yorunge.domain.operations import OperationEvent

    with open_store(state) as store:
        connection = store.connection
        record, job = read_operation(connection, identifier), read_job(connection, identifier)
        current = job.attempts[-1]
        connection.execute("BEGIN IMMEDIATE")
        for sequence in range(record.event_count + 1, count + 1):
            append_event(
                connection,
                identifier,
                OperationEvent(
                    sequence=sequence,
                    revision=sequence,
                    fence=record.fence,
                    attempt_id=current.attempt_id,
                    observed_at=record.summary.updated_at,
                    identity_epoch=record.observed_identity_epoch,
                    clock_generation=record.observed_clock_generation,
                    status="running",
                    execution_status="running",
                    delivery_status="pending",
                    reason_code=None,
                ),
            )
        changed = record.model_copy(
            update={
                "event_count": count,
                "summary": record.summary.model_copy(
                    update={"revision": count, "status": "running", "execution_status": "running"}
                ),
            }
        )
        raw_record(connection, changed)
        raw_attempt(connection, current.model_copy(update={"status": "running"}))
        connection.execute("COMMIT")
        validate_contents(connection)


def test_full_normal_history_orphan_can_recover_and_use_terminal_reserve(
    started_operation, execution_clock
):
    state, plan, backend, observer, identifier, _ = started_operation
    fill_normal_history(state, identifier)
    with open_store(state) as store:
        before = hashlib.sha256(
            b"".join(
                row[0].encode()
                for row in store.connection.execute(
                    "SELECT payload FROM operation_events ORDER BY sequence"
                )
            )
        ).hexdigest()
    execution_clock.value += timedelta(seconds=31)
    with api._operation_session(
        plan.plan_id, backend, observer=observer, state_dir=state
    ) as coordinator:
        claim = coordinator.takeover(identifier)
        assert coordinator.repository.operation(identifier).event_count == 255
        observer.execution, observer.delivery = "running", "pending"
        limited = coordinator.reconcile(identifier, claim.ownership)
        assert limited.operation.status == "unknown"
        assert limited.attempts[-1].reason_code == "capacity_exceeded"
        assert coordinator.repository.operation(identifier).event_count == 255
        observer.execution, observer.delivery = "succeeded", "complete"
        assert coordinator.reconcile(identifier, claim.ownership).operation.status == "succeeded"
        assert coordinator.repository.operation(identifier).event_count == 256
    with open_store(state) as store:
        after = hashlib.sha256(
            b"".join(
                row[0].encode()
                for row in store.connection.execute(
                    "SELECT payload FROM operation_events ORDER BY sequence LIMIT 255"
                )
            )
        ).hexdigest()
        assert after == before
        validate_contents(store.connection)
    assert len(backend.effects()) == 1


def test_full_normal_history_reset_does_not_need_a_business_slot(started_operation):
    state, plan, backend, observer, identifier, _ = started_operation
    fill_normal_history(state, identifier)
    preview = api.preview_identity_reset(state_dir=state).data
    api.reset_identity(preview.digest, state_dir=state)
    with api._operation_session(
        plan.plan_id, backend, observer=observer, state_dir=state
    ) as coordinator:
        claim = coordinator.takeover(identifier)
        assert coordinator.repository.operation(identifier).event_count == 255
        assert coordinator.reconcile(identifier, claim.ownership).operation.status == "succeeded"
    assert len(backend.effects()) == 1


@pytest.mark.parametrize("entry", ["warm", "full"])
def test_recovery_owner_cannot_claim_a_future_generation_of_current_store(started_operation, entry):
    from tests.integration.test_operation_store import raw_attempt, raw_record

    state, _, _, _, identifier, _ = started_operation
    with open_store(state) as store:
        record, job = (
            read_operation(store.connection, identifier),
            read_job(store.connection, identifier),
        )
        changed = record.model_copy(
            update={
                "observed_clock_generation": 2,
                "fence": 2,
                "lease": record.lease.model_copy(
                    update={"ownership_clock_generation": 2, "fence": 2, "owner_id": str(uuid4())}
                ),
                "recovery_reason": "owner_changed",
                "summary": record.summary.model_copy(
                    update={
                        "status": "unknown",
                        "execution_status": "unknown",
                        "revision": record.summary.revision + 1,
                    }
                ),
            }
        )
        raw_record(store.connection, changed)
        raw_attempt(
            store.connection,
            job.attempts[-1].model_copy(
                update={"status": "unknown", "reason_code": "owner_changed"}
            ),
        )
        with pytest.raises(YorungeError) as error:
            if entry == "warm":
                read_job(store.connection, identifier)
            else:
                validate_contents(store.connection)
        assert error.value.code == "state_invalid"


def test_read_result_final_transaction_rejects_rotated_credential_without_reresolving(
    tmp_path, execution_fixture, execution_clock, monkeypatch
):
    from yorunge.adapters.operation_repository import StateOperations
    from yorunge.adapters.secrets import EnvSecretReader
    from yorunge.domain.capabilities import timestamp

    state, config = tmp_path / "state", tmp_path / "config.toml"
    config.write_text(
        'schema_version=1\nactive_profile="work"\n[profiles.work]\n'
        'account_id="account"\nplatform_key_env="EVREN_PLATFORM_API_KEY"\n'
    )
    backend, observer = ProcessBackend(tmp_path / "effects"), ReadObserver(execution_clock)
    plan = api.prepare_execution_plan(
        task="dataset.upload", config=config, state_dir=state
    ).data.plan
    api.approve_execution_plan(plan.plan_id, plan.digest, config=config, state_dir=state)
    with api._operation_session(
        plan.plan_id, backend, config=config, state_dir=state
    ) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        coordinator.dispatch(identifier, claim.ownership)
        before = coordinator.repository.operation(identifier)
    original = StateOperations.reconcile
    original_read, reads = EnvSecretReader.read, []

    def read(self, reference):
        reads.append(reference.name)
        return original_read(self, reference)

    def rotate(self, *args):
        child = subprocess.run(
            [
                sys.executable,
                "-m",
                "tests.fixtures.operation_worker",
                "rotate",
                str(state),
                plan.plan_id,
                str(backend.marker),
                timestamp(execution_clock.value),
                str(config),
                "evren-platform",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert child.returncode == 0, child.stderr
        return original(self, *args)

    with monkeypatch.context() as patch:
        patch.setattr(StateOperations, "reconcile", rotate)
        patch.setattr(EnvSecretReader, "read", read)
        with api._operation_session(
            plan.plan_id, backend, observer=observer, config=config, state_dir=state
        ) as coordinator:
            with pytest.raises(OperationError) as error:
                coordinator.reconcile(identifier, claim.ownership)
            assert error.value.code == "state_changed"
            assert error.value.operation_id == identifier
            assert coordinator.repository.operation(identifier) == before
    assert reads == ["EVREN_PLATFORM_API_KEY"]
    assert len(observer.requests) == 1
    assert len(backend.effects()) == 1


@pytest.mark.parametrize("failure", ["timeout", "permission", "secret_id", "secret_status"])
def test_read_port_failures_are_safe_unknown_without_another_start(
    tmp_path, execution_fixture, execution_clock, failure
):
    state, config = tmp_path / "state", tmp_path / "config.toml"
    config.write_text(
        'schema_version=1\nactive_profile="work"\n[profiles.work]\n'
        'account_id="account"\nplatform_key_env="EVREN_PLATFORM_API_KEY"\n'
    )
    backend, observer = ProcessBackend(tmp_path / "effects"), ReadObserver(execution_clock)
    plan = api.prepare_execution_plan(
        task="dataset.upload", config=config, state_dir=state
    ).data.plan
    api.approve_execution_plan(plan.plan_id, plan.digest, config=config, state_dir=state)
    with api._operation_session(
        plan.plan_id, backend, config=config, state_dir=state
    ) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        coordinator.dispatch(identifier, claim.ownership)

    def fail(result):
        if failure == "timeout":
            raise TimeoutError("private transport body")
        if failure == "permission":
            raise PermissionError("private transport body")
        secret = observer.requests[-1].credentials[0].credential.secret.reveal()
        return result.model_copy(
            update={"provider_run_id" if failure == "secret_id" else "provider_status": secret}
        )

    observer.change = fail
    with api._operation_session(
        plan.plan_id, backend, observer=observer, config=config, state_dir=state
    ) as coordinator:
        job = coordinator.reconcile(identifier, claim.ownership)
        assert job.operation.status == "unknown"
        assert job.attempts[-1].reason_code == (
            "provider_unavailable"
            if failure == "timeout"
            else "provider_unauthorized"
            if failure == "permission"
            else "evidence_mismatch"
        )
        assert "synthetic-secret" not in job.model_dump_json()
        assert "private transport" not in job.model_dump_json()
        assert job.attempts[-1].provider_run_id == "fixture-run-1"
    assert len(backend.effects()) == 1


@pytest.mark.parametrize("change", ["owner", "result"])
def test_reset_preview_stales_on_semantic_change_before_creating_new_key(
    started_operation, execution_clock, change
):
    state, plan, backend, observer, identifier, owner = started_operation
    preview = api.preview_identity_reset(state_dir=state).data
    if change == "owner":
        execution_clock.value += timedelta(seconds=31)
    with api._operation_session(
        plan.plan_id, backend, observer=observer, state_dir=state
    ) as coordinator:
        if change == "owner":
            coordinator.takeover(identifier)
        else:
            coordinator.reconcile(identifier, owner)
    keys = sorted(path.name for path in (state / "keys").iterdir())
    with pytest.raises(YorungeError) as error:
        api.reset_identity(preview.digest, state_dir=state)
    assert error.value.code == "state_changed"
    assert sorted(path.name for path in (state / "keys").iterdir()) == keys
    assert api.preview_identity_reset(state_dir=state).data.digest != preview.digest


def test_reset_v3_cli_text_and_json_share_counts(started_operation, cli):
    import json

    state, _, _, _, _, _ = started_operation
    result = cli("state", "reset", "--state-dir", str(state), "--output", "json", state=True)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    preview = json.loads(result.stdout)["data"]
    assert preview["schema_version"] == 3
    assert preview["current"]["operation_count"] == 1
    assert preview["current"]["attempt_count"] == 1
    text = cli("state", "reset", "--state-dir", str(state), state=True)
    assert text.returncode == 0, text.stderr
    assert "Mevcut operation: 1" in text.stdout
    assert "Mevcut attempt: 1" in text.stdout
    assert "unknown" in text.stdout
    assert "garanti edilmez" in text.stdout


@pytest.mark.parametrize("confirmed", [False, True])
def test_failed_terminal_commit_returns_uncertain_and_preserves_confirmed_execution(
    started_operation, monkeypatch, confirmed
):
    from yorunge.adapters import operation_repository

    state, plan, backend, observer, identifier, owner = started_operation
    with api._operation_session(
        plan.plan_id, backend, observer=observer, state_dir=state
    ) as coordinator:
        if confirmed:
            observer.delivery = "pending"
            coordinator.reconcile(identifier, owner)
            observer.delivery = "complete"
        original = operation_repository.write_outcome

        def failed_write(*args):
            original(*args)
            raise OSError("private disk path")

        with monkeypatch.context() as patch:
            patch.setattr(operation_repository, "write_outcome", failed_write)
            with pytest.raises(OperationError) as error:
                coordinator.reconcile(identifier, owner)
            assert error.value.code == "operation_uncertain"
            assert error.value.reason_code == "state_write_failed"
            assert error.value.exit_code == 5
        job = coordinator.repository.job(identifier)
        assert job.operation.status == "unknown"
        assert job.operation.execution_status == ("succeeded" if confirmed else "unknown")
        assert job.attempts[-1].reason_code == "outcome_write_failed"
        assert job.outcome is None
        assert coordinator.reconcile(identifier, owner).operation.status == "succeeded"
    assert len(backend.effects()) == 1


def test_terminal_commit_succeeded_but_return_failed_never_reopens_record(
    started_operation, monkeypatch
):
    from yorunge.adapters.operation_repository import StateOperations

    state, plan, backend, observer, identifier, owner = started_operation
    original = StateOperations.reconcile

    def late_failure(self, *args):
        original(self, *args)
        raise OperationError("state_busy", identifier)

    with api._operation_session(
        plan.plan_id, backend, observer=observer, state_dir=state
    ) as coordinator:
        with monkeypatch.context() as patch:
            patch.setattr(StateOperations, "reconcile", late_failure)
            with pytest.raises(OperationError) as error:
                coordinator.reconcile(identifier, owner)
            assert error.value.code == "operation_uncertain"
            assert error.value.reason_code == "state_busy"
        job = coordinator.repository.job(identifier)
        assert job.operation.status == "succeeded"
        assert coordinator.reconcile(identifier, owner) == job
    assert len(backend.effects()) == 1
