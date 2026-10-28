import copy
import os
import pickle
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest

from tests.fixtures.operation_backend import ProcessBackend
from yorunge import api
from yorunge.adapters.operation_store import read_job, read_operation
from yorunge.adapters.state import open_store, validate_contents
from yorunge.application.operations import DispatchPermit
from yorunge.domain.errors import OperationError, YorungeError


@pytest.fixture
def operation_setup(tmp_path, execution_fixture, execution_clock):
    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    approval = api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state).data
    assert approval.effective
    return state, plan, ProcessBackend(tmp_path / "effects")


def test_admission_dispatch_and_restart_never_repeat(operation_setup):
    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        assert claim.ownership is not None
        assert coordinator.admit(plan.plan_id).ownership is None
        job = coordinator.dispatch(identifier, claim.ownership)
        assert job.operation.status == "submitted"
        assert job.attempts[-1].provider_run_id == "fixture-run-1"
        assert job.outcome is None
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        repeated = coordinator.admit(plan.plan_id)
        assert repeated.ownership is None
        assert repeated.job.operation.operation_id == identifier
        with pytest.raises(OperationError) as error:
            coordinator.dispatch(identifier, claim.ownership)
        assert error.value.code == "operation_conflict"
    assert backend.calls == 1
    assert len(backend.effects()) == 1
    with open_store(state) as store:
        validate_contents(store.connection)


@pytest.mark.parametrize("mode, effects", [("lost_reply", 1), ("not_sent", 0)])
def test_every_post_arm_transport_failure_is_uncertain(operation_setup, mode, effects):
    state, plan, backend = operation_setup
    backend.mode = mode
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        with pytest.raises(OperationError) as error:
            coordinator.dispatch(identifier, claim.ownership)
        assert error.value.code == "operation_uncertain"
        assert error.value.operation_id == identifier
        assert "private transport" not in str(error.value)
        record = coordinator.repository.operation(identifier)
        assert record.dispatch_attempt_id is not None
        assert record.summary.status == "unknown"
        assert coordinator.admit(plan.plan_id).ownership is None
        with pytest.raises(OperationError) as repeated:
            coordinator.dispatch(identifier, claim.ownership)
        assert repeated.value.code == "operation_conflict"
    assert len(backend.effects()) == effects
    assert backend.calls == 1


def test_pre_dispatch_takeover_creates_candidate_and_fences_old_owner(
    operation_setup, execution_clock
):
    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        first = coordinator.admit(plan.plan_id)
        identifier = first.job.operation.operation_id
        renewed = coordinator.renew(identifier, first.ownership)
        assert renewed.token() == first.ownership.token()
    execution_clock.value += timedelta(seconds=31)
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        second = coordinator.takeover(identifier)
        assert second.ownership.fence == first.ownership.fence + 1
        assert second.job.attempts[0].status == "abandoned"
        assert second.job.attempts[-1].number == 2
        assert coordinator.repository.operation(identifier).event_count == 1
        for action in (
            lambda: coordinator.renew(identifier, first.ownership),
            lambda: coordinator.dispatch(identifier, first.ownership),
        ):
            with pytest.raises(OperationError) as error:
                action()
            assert error.value.code == "operation_lease_lost"
        job = coordinator.dispatch(identifier, second.ownership)
        assert job.operation.status == "submitted"
    assert len(backend.effects()) == 1


def test_post_dispatch_takeover_never_creates_candidate_or_start(operation_setup, execution_clock):
    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        coordinator.dispatch(identifier, claim.ownership)
    execution_clock.value += timedelta(seconds=31)
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        takeover = coordinator.takeover(identifier)
        assert takeover.job.operation.status == "unknown"
        assert takeover.job.operation.attempt_count == 1
        assert takeover.job.attempts[0].provider_run_id == "fixture-run-1"
        with pytest.raises(OperationError) as error:
            coordinator.dispatch(identifier, takeover.ownership)
        assert error.value.code == "operation_conflict"
    assert backend.calls == 1
    assert len(backend.effects()) == 1


@pytest.mark.parametrize("rejection", ["revoked", "expired", "reapproved"])
def test_dead_pre_dispatch_owner_can_be_cleaned_without_execution_validation(
    operation_setup, execution_clock, monkeypatch, rejection
):
    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        first = coordinator.admit(plan.plan_id)
        identifier = first.job.operation.operation_id
    if rejection != "expired":
        api.revoke_execution_approval(plan.plan_id, state_dir=state)
        if rejection == "reapproved":
            api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state)
        execution_clock.value += timedelta(seconds=31)
    else:
        execution_clock.value += timedelta(seconds=301)
    monkeypatch.setattr(api, "_context", lambda *args: pytest.fail("cleanup resolved config"))
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        cleaned = coordinator.takeover(identifier)
        assert cleaned.ownership is None
        assert cleaned.job.operation.status == "failed"
        assert cleaned.job.operation.execution_status == "not_started"
        assert cleaned.job.operation.attempt_count == 1
        assert (
            cleaned.job.outcome.reason_code
            == {
                "revoked": "approval_revoked",
                "expired": "approval_expired",
                "reapproved": "approval_changed",
            }[rejection]
        )
        record = coordinator.repository.operation(identifier)
        assert record.dispatch_attempt_id is None
    assert backend.calls == 0


def test_expired_lease_cannot_renew(operation_setup, execution_clock):
    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        first = coordinator.admit(plan.plan_id)
    execution_clock.value += timedelta(seconds=30)
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        with pytest.raises(OperationError) as error:
            coordinator.renew(first.job.operation.operation_id, first.ownership)
        assert error.value.code == "operation_lease_lost"


def test_port_has_result_headroom_and_persists_near_deadline(operation_setup, execution_clock):
    state, plan, backend = operation_setup

    def consume_window(request, deadline):
        available = deadline - execution_clock.monotonic()
        assert 20 < available < 25.001
        execution_clock.elapsed += available - 0.5
        execution_clock.value += timedelta(seconds=available - 0.5)

    backend.before = consume_window
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        job = coordinator.dispatch(claim.job.operation.operation_id, claim.ownership)
        assert job.operation.status == "submitted"
        assert coordinator.budget.remaining() > 4
    assert len(backend.effects()) == 1


def test_public_producer_cannot_admit(tmp_path, execution_clock):
    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    backend = ProcessBackend(tmp_path / "effects")
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        with pytest.raises(YorungeError) as error:
            coordinator.admit(plan.plan_id)
        assert error.value.code == "plan_not_valid"
    with open_store(state) as store:
        assert store.connection.execute("SELECT count(*) FROM operations").fetchone()[0] == 0
    assert backend.calls == 0


def test_permit_thread_copy_pickle_and_fork_boundaries():
    permit = DispatchPermit(os.getpid)
    for clone in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(TypeError):
            clone(permit)

    def consume():
        try:
            permit.consume()
            return True
        except OperationError:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(lambda _: consume(), range(32))) == 1
    forked = DispatchPermit(os.getpid)
    # PID rejection must precede a potentially inherited locked threading.Lock.
    with forked._lock:
        pid = os.fork()
        if pid == 0:
            try:
                forked.consume()
            except OperationError:
                os._exit(0)
            os._exit(1)
        assert os.waitpid(pid, 0)[1] == 0
    forked.consume()


@pytest.mark.parametrize("point", ["admit", "arm"])
@pytest.mark.parametrize(
    "task,service", [("llm.chat", "evren-llm"), ("dataset.upload", "evren-platform")]
)
def test_final_transaction_rechecks_credential_revision_across_processes(
    tmp_path, execution_fixture, execution_clock, monkeypatch, point, task, service
):
    from yorunge.adapters.operation_repository import StateOperations
    from yorunge.adapters.secrets import EnvSecretReader
    from yorunge.domain.capabilities import timestamp

    config = tmp_path / "config.toml"
    config.write_text(
        'schema_version=1\nactive_profile="work"\n[profiles.work]\naccount_id="account"\n'
        'platform_key_env="EVREN_PLATFORM_API_KEY"\nllm_key_env="EVREN_LLM_API_KEY"\n'
    )
    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task=task, config=config, state_dir=state).data.plan
    assert api.approve_execution_plan(
        plan.plan_id, plan.digest, config=config, state_dir=state
    ).data.effective
    backend = ProcessBackend(tmp_path / "effects")
    reads = []
    original_read = EnvSecretReader.read

    def read(self, reference):
        reads.append(reference.name)
        return original_read(self, reference)

    original = getattr(StateOperations, point)

    def raced(self, *args):
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
                service,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert child.returncode == 0, child.stderr
        return original(self, *args)

    with api._operation_session(
        plan.plan_id, backend, config=config, state_dir=state
    ) as coordinator:
        first = coordinator.admit(plan.plan_id) if point == "arm" else None
        monkeypatch.setattr(StateOperations, point, raced)
        monkeypatch.setattr(EnvSecretReader, "read", read)
        with pytest.raises(YorungeError) as error:
            if first:
                coordinator.dispatch(first.job.operation.operation_id, first.ownership)
            else:
                coordinator.admit(plan.plan_id)
        assert error.value.code == "state_changed"
    # A single call captures once; no automatic reread of a changed environment.
    assert len(reads) == (0 if point == "arm" else 1)
    assert backend.calls == 0
    with open_store(state) as store:
        validate_contents(store.connection)
        row = store.connection.execute("SELECT operation_id FROM operations").fetchone()
        assert (row is None) == (point == "admit")
        if row:
            assert read_operation(store.connection, row[0]).dispatch_attempt_id is None


@pytest.mark.parametrize("point", ["admission", "arm"])
def test_business_write_failure_rolls_back_before_external_effect(
    operation_setup, monkeypatch, point
):
    from yorunge.adapters import operation_repository

    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        first = coordinator.admit(plan.plan_id) if point == "arm" else None
        name = "append_event" if first else "insert_record"
        original = getattr(operation_repository, name)

        def fail_after_write(*args):
            original(*args)
            raise OSError("private disk location must not escape")

        with monkeypatch.context() as patch:
            patch.setattr(operation_repository, name, fail_after_write)
            with pytest.raises(OperationError) as error:
                if first:
                    coordinator.dispatch(first.job.operation.operation_id, first.ownership)
                else:
                    coordinator.admit(plan.plan_id)
            assert error.value.code == "state_write_failed"
        if first:
            record = coordinator.repository.operation(first.job.operation.operation_id)
            assert record.event_count == 1
            assert record.dispatch_attempt_id is None
        else:
            assert coordinator.repository.existing(plan.plan_id) is None
    assert backend.calls == 0


@pytest.mark.parametrize(
    "point",
    [
        "admit_before",
        "admit_mid",
        "admit_after",
        "arm_before",
        "arm_mid",
        "arm_after",
        "kill_after_effect",
        "receipt_mid",
        "receipt_after",
    ],
)
def test_sigkill_transaction_cutpoints_never_authorize_second_start(
    operation_setup, execution_clock, point
):
    import signal

    from yorunge.domain.capabilities import timestamp

    state, plan, backend = operation_setup
    child = subprocess.run(
        [
            sys.executable,
            "-m",
            "tests.fixtures.operation_worker",
            point,
            str(state),
            plan.plan_id,
            str(backend.marker),
            timestamp(execution_clock.value),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert child.returncode == -signal.SIGKILL, child.stderr
    with open_store(state) as store:
        validate_contents(store.connection)
        row = store.connection.execute("SELECT operation_id FROM operations").fetchone()
        saved = read_operation(store.connection, row[0]) if row else None
        armed = saved is not None and saved.dispatch_attempt_id is not None
        if point == "receipt_after":
            assert (
                read_job(store.connection, row[0]).attempts[-1].provider_run_id == "fixture-run-1"
            )
    assert armed == (point in {"arm_after", "kill_after_effect", "receipt_mid", "receipt_after"})
    execution_clock.value += timedelta(seconds=31)
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        if saved:
            claim = coordinator.takeover(saved.summary.operation_id)
        else:
            claim = coordinator.admit(plan.plan_id)
        if armed:
            with pytest.raises(OperationError) as error:
                coordinator.dispatch(claim.job.operation.operation_id, claim.ownership)
            assert error.value.code == "operation_conflict"
        else:
            coordinator.dispatch(claim.job.operation.operation_id, claim.ownership)
    assert len(backend.effects()) == (0 if point == "arm_after" else 1)


def wait_files(*paths):
    end = time.monotonic() + 8
    while not all(path.exists() for path in paths):
        if time.monotonic() >= end:
            pytest.fail("process barrier timed out")
        time.sleep(0.005)


def test_two_process_admission_contenders_share_single_intent_and_effect(
    operation_setup, execution_clock, tmp_path
):
    from yorunge.domain.capabilities import timestamp

    state, plan, backend = operation_setup
    release = tmp_path / "release"
    ready = [tmp_path / f"ready-{i}" for i in range(2)]
    children = [
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "tests.fixtures.operation_worker",
                "contend",
                str(state),
                plan.plan_id,
                str(backend.marker),
                timestamp(execution_clock.value),
                str(path),
                str(release),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for path in ready
    ]
    try:
        wait_files(*ready)
        release.touch()
        for child in children:
            _, error = child.communicate(timeout=10)
            assert child.returncode == 0, error
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait()
    with open_store(state) as store:
        validate_contents(store.connection)
        ids = store.connection.execute("SELECT operation_id FROM operations").fetchall()
        assert len(ids) == 1
        record = read_operation(store.connection, ids[0][0])
        assert record.fence == 1
        assert record.summary.attempt_count == 1
    assert len(backend.effects()) == 1


def test_paused_sender_can_make_one_late_effect_but_cannot_overwrite_new_owner(
    operation_setup, execution_clock, tmp_path
):
    from yorunge.domain.capabilities import timestamp

    state, plan, backend = operation_setup
    ready, release, clock_file = (tmp_path / name for name in ("ready", "release", "clock"))
    clock_file.write_text(timestamp(execution_clock.value))
    child = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "tests.fixtures.operation_worker",
            "paused",
            str(state),
            plan.plan_id,
            str(backend.marker),
            timestamp(execution_clock.value),
            str(ready),
            str(release),
            str(clock_file),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_files(ready)
        execution_clock.value += timedelta(seconds=31)
        clock_file.write_text(timestamp(execution_clock.value))
        with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
            existing = coordinator.admit(plan.plan_id)
            identifier = existing.job.operation.operation_id
            takeover = coordinator.takeover(identifier)
            record = coordinator.repository.operation(identifier)
            assert takeover.job.operation.status == "unknown"
            assert takeover.job.operation.attempt_count == 1
            with pytest.raises(OperationError) as error:
                coordinator.dispatch(identifier, takeover.ownership)
            assert error.value.code == "operation_conflict"
        release.touch()
        _, error = child.communicate(timeout=10)
        assert child.returncode != 0
        assert "OperationError" in error
        with open_store(state) as store:
            assert read_operation(store.connection, identifier) == record
            assert read_job(store.connection, identifier).attempts[0].provider_run_id is None
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
    assert backend.calls == 0
    assert len(backend.effects()) == 1


def test_exhausted_headroom_after_arm_never_calls_port(
    operation_setup, execution_clock, monkeypatch
):
    from yorunge.adapters.operation_repository import StateOperations

    state, plan, backend = operation_setup
    original = StateOperations.arm

    def delayed(self, *args):
        result = original(self, *args)
        execution_clock.elapsed += 26
        execution_clock.value += timedelta(seconds=26)
        return result

    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        first = coordinator.admit(plan.plan_id)
        monkeypatch.setattr(StateOperations, "arm", delayed)
        with pytest.raises(OperationError) as error:
            coordinator.dispatch(first.job.operation.operation_id, first.ownership)
        assert error.value.code == "execution_timeout"
        record = coordinator.repository.operation(first.job.operation.operation_id)
        assert record.dispatch_attempt_id is not None
        assert record.summary.status == "unknown"
    assert backend.calls == 0


def test_fork_between_arm_commit_and_permit_cannot_start_twice(operation_setup, execution_clock):
    from yorunge.domain.capabilities import timestamp

    state, plan, backend = operation_setup
    child = subprocess.run(
        [
            sys.executable,
            "-m",
            "tests.fixtures.operation_worker",
            "fork_after_arm",
            str(state),
            plan.plan_id,
            str(backend.marker),
            timestamp(execution_clock.value),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert child.returncode == 0, child.stderr
    assert len(backend.effects()) == 1


@pytest.mark.parametrize("field", ["provider_status", "provider_run_id"])
def test_known_credential_secret_is_rejected_before_receipt_persistence(
    tmp_path, execution_fixture, execution_clock, field
):
    from yorunge.application.operations import Submission

    config, state = tmp_path / "config.toml", tmp_path / "state"
    config.write_text(
        'schema_version=1\nactive_profile="work"\n[profiles.work]\n'
        'account_id="account"\nplatform_key_env="EVREN_PLATFORM_API_KEY"\n'
    )
    plan = api.prepare_execution_plan(
        task="dataset.upload", config=config, state_dir=state
    ).data.plan
    api.approve_execution_plan(plan.plan_id, plan.digest, config=config, state_dir=state)

    class EchoBackend:
        def start(self, request, *, deadline):
            receipt = Submission(
                correlation=request.admission.correlation,
                authority=request.admission.authorities[0],
                provider_run_id="fixture-run",
                provider_status="queued",
                running=False,
            )
            return receipt.model_copy(
                update={field: request.credentials[0].credential.secret.reveal()}
            )

    with api._operation_session(
        plan.plan_id, EchoBackend(), config=config, state_dir=state
    ) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        with pytest.raises(OperationError) as error:
            coordinator.dispatch(claim.job.operation.operation_id, claim.ownership)
        assert error.value.code == "operation_uncertain"
        assert "synthetic-secret" not in str(error.value.envelope())
    with open_store(state) as store:
        job = read_job(store.connection, claim.job.operation.operation_id)
        assert job.operation.status == "unknown"
        assert "synthetic-secret" not in job.model_dump_json()
        assert all(
            "synthetic-secret" not in row[0]
            for row in store.connection.execute("SELECT payload FROM operation_attempts")
        )


def test_malformed_id_remains_a_controlled_request_error(operation_setup):
    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        with pytest.raises(YorungeError) as error:
            coordinator.repository.operation("malformed")
        assert error.value.code == "invalid_request"
        assert error.value.envelope()["operation_id"] is None


def test_fence_exhaustion_preserves_known_operation_id(operation_setup, execution_clock):
    from tests.integration.test_operation_store import raw_attempt, raw_record

    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        coordinator.dispatch(identifier, claim.ownership)
    with open_store(state) as store:
        record, job = (
            read_operation(store.connection, identifier),
            read_job(store.connection, identifier),
        )
        changed = record.model_copy(
            update={
                "fence": 2**63 - 1,
                "lease": record.lease.model_copy(update={"fence": 2**63 - 1}),
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
        validate_contents(store.connection)
    execution_clock.value += timedelta(seconds=31)
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        with pytest.raises(OperationError) as error:
            coordinator.takeover(identifier)
        assert error.value.code == "operation_fence_exhausted"
        assert error.value.operation_id == identifier


def test_other_stateful_observation_of_lease_expiry_prevents_clock_revival(
    operation_setup, execution_clock
):
    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
    execution_clock.value += timedelta(seconds=31)
    api.query_capabilities(task="llm.train", state_dir=state)
    execution_clock.value -= timedelta(seconds=2)
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        with pytest.raises(OperationError) as error:
            coordinator.renew(claim.job.operation.operation_id, claim.ownership)
        assert error.value.code == "operation_lease_lost"
    assert backend.calls == 0


def test_valid_plan_that_exceeds_admission_bytes_has_controlled_rejection(
    tmp_path, execution_fixture, execution_clock
):
    from yorunge.domain.capabilities import AuthorizationScope, ResourceGrant

    scope = AuthorizationScope(
        permissions=("read",),
        resources=tuple(
            ResourceGrant(
                namespace="fixture",
                resource_type="dataset",
                resource_id=f"{i:02d}" + "x" * 240,
                permissions=("read",),
            )
            for i in range(40)
        ),
    )

    def enrich(assessment):
        capability = assessment.capabilities[0]
        return assessment.model_copy(
            update={
                "capabilities": (
                    capability.model_copy(
                        update={
                            "key": capability.key.model_copy(
                                update={
                                    "scope": capability.key.scope.model_copy(
                                        update={"authorization_scope": scope}
                                    )
                                }
                            )
                        }
                    ),
                )
            }
        )

    execution_fixture.change = enrich
    config, state = tmp_path / "config.toml", tmp_path / "state"
    config.write_text(
        'schema_version=1\nactive_profile="work"\n[profiles.work]\n'
        'account_id="account"\nllm_key_env="EVREN_LLM_API_KEY"\n'
    )
    plan = api.prepare_execution_plan(task="llm.chat", config=config, state_dir=state).data.plan
    assert plan.status == "prepared"
    assert api.approve_execution_plan(
        plan.plan_id, plan.digest, config=config, state_dir=state
    ).data.effective
    backend = ProcessBackend(tmp_path / "effects")
    with api._operation_session(
        plan.plan_id, backend, config=config, state_dir=state
    ) as coordinator:
        with pytest.raises(OperationError) as error:
            coordinator.admit(plan.plan_id)
        assert error.value.code == "plan_not_valid"
        assert coordinator.repository.existing(plan.plan_id) is None
    assert backend.calls == 0


@pytest.mark.parametrize("failure", ["validation", "budget"])
def test_known_id_survives_pre_arm_use_case_failure(
    operation_setup, execution_fixture, execution_clock, failure
):
    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        if failure == "validation":
            execution_fixture.change = lambda assessment: assessment.model_copy(
                update={"inputs_verified": False, "blockers": ("fixture_changed",)}
            )
        else:
            execution_clock.elapsed += 31
        with pytest.raises(YorungeError) as error:
            if failure == "validation":
                coordinator.dispatch(identifier, claim.ownership)
            else:
                coordinator.renew(identifier, claim.ownership)
        assert error.value.envelope()["operation_id"] == identifier
    assert backend.calls == 0


@pytest.mark.parametrize("jump", [2, -2])
@pytest.mark.parametrize("point", ["entry", "final"])
def test_final_transaction_clock_gate_uses_ownership_error_and_rolls_back(
    operation_setup, execution_clock, monkeypatch, jump, point
):
    from yorunge.adapters import operation_repository

    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        before = coordinator.repository.operation(identifier)
        execution_clock.value += timedelta(seconds=29)
        original = operation_repository.write_record
        original_stamp = operation_repository.StateOperations._ownership_stamp

        def jump_after_write(*args, **kwargs):
            original(*args, **kwargs)
            execution_clock.value += timedelta(seconds=jump)

        def jump_after_stamp(self, *args):
            result = original_stamp(self, *args)
            execution_clock.value += timedelta(seconds=jump)
            return result

        with monkeypatch.context() as patch:
            if point == "final":
                patch.setattr(operation_repository, "write_record", jump_after_write)
            else:
                patch.setattr(
                    operation_repository.StateOperations, "_ownership_stamp", jump_after_stamp
                )
            with pytest.raises(OperationError) as error:
                coordinator.renew(identifier, claim.ownership)
            assert error.value.code == "operation_lease_lost"
            assert error.value.reason_code == "operation_lease_lost"
            assert error.value.operation_id == identifier
        assert coordinator.repository.operation(identifier) == before
    assert backend.calls == 0


@pytest.mark.parametrize("path", ["lookup", "raced_admit"])
@pytest.mark.parametrize("failure", ["budget", "record"])
def test_repeated_admission_failure_identifies_persisted_operation(
    operation_setup, execution_clock, monkeypatch, path, failure
):
    from yorunge.adapters import operation_repository

    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        validity = coordinator.validate(plan)
        original = operation_repository.read_job

        def expire_after_read(*args, **kwargs):
            if failure == "record":
                raise YorungeError("state_invalid")
            result = original(*args, **kwargs)
            execution_clock.elapsed += 31
            return result

        with monkeypatch.context() as patch:
            patch.setattr(operation_repository, "read_job", expire_after_read)
            with pytest.raises(YorungeError) as error:
                if path == "lookup":
                    coordinator.admit(plan.plan_id)
                else:
                    coordinator.repository.admit(plan, validity)
            assert error.value.envelope()["operation_id"] == identifier
    assert backend.calls == 0
