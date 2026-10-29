"""Real TLS + SQLite operation admission, uncertainty, reads and restart."""

import asyncio
import json
import socket
import subprocess
import sys
from datetime import timedelta
from functools import partial
from urllib.parse import urlsplit
from uuid import uuid4

import pytest

from tests.conftest import SECRET
from tests.fixtures.http_operations import NetworkBackend, OperationEndpoint
from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from yorunge import api
from yorunge.adapters.http_session import HttpSession
from yorunge.adapters.http_transport import HttpxTransport
from yorunge.adapters.state import open_store, validate_contents
from yorunge.domain.errors import OperationError, YorungeError

CONNECT = socket.socket.connect
CONNECT_EX = socket.socket.connect_ex
GETADDRINFO = socket.getaddrinfo


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(tmp_path_factory.mktemp("operation-tls-certificate"))


@pytest.fixture(autouse=True)
def actual_loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


@pytest.fixture
def remote_plan(tmp_path, execution_fixture, execution_clock):
    config, state = tmp_path / "remote.toml", tmp_path / "state"
    config.write_text(
        'schema_version=1\nactive_profile="work"\n[profiles.work]\n'
        'account_id="fixture-account"\nproject_id="fixture-project"\n'
        'platform_url="https://localhost/v1"\nplatform_key_env="EVREN_PLATFORM_API_KEY"\n'
    )
    plan = api.prepare_execution_plan(
        task="dataset.upload", config=config, state_dir=state
    ).data.plan
    assert plan.status == "prepared"
    approved = api.approve_execution_plan(
        plan.plan_id, plan.digest, config=config, state_dir=state
    ).data
    assert approved.effective
    return state, config, plan


def session(server):
    return HttpSession(transport_factory=lambda: HttpxTransport(transport=server.transport()))


def operation(remote_plan, backend):
    state, config, plan = remote_plan
    return api._operation_session(
        plan.plan_id, backend, observer=backend, config=config, state_dir=state
    )


def paths(server):
    return [urlsplit(request.path).path for request in server.requests]


def test_approved_plan_uses_captured_credential_and_typed_remote_evidence(
    remote_plan, certificates, execution_clock, monkeypatch
):
    endpoint = OperationEndpoint(execution_clock, SECRET)
    with TlsServer(certificates, endpoint.routes()) as server, session(server) as http:
        backend = NetworkBackend(http)
        # Rotate the process environment after final arm; the already selected
        # credential is the only auth source for this request.
        backend.before_start = lambda: monkeypatch.setenv(
            "EVREN_PLATFORM_API_KEY", "different-unobserved-environment-token"
        )
        with operation(remote_plan, backend) as coordinator:
            claim = coordinator.admit(remote_plan[2].plan_id)
            identifier = claim.job.operation.operation_id
            assert claim.ownership is not None
            submitted = coordinator.dispatch(identifier, claim.ownership)
            assert submitted.operation.status == "submitted"
            assert submitted.attempts[-1].provider_run_id == endpoint.provider_run_id
            latch = coordinator.repository.operation(identifier).dispatch_attempt_id
            assert latch == endpoint.effects[0]
            completed = coordinator.reconcile(identifier, claim.ownership)
            assert completed.operation.status == "succeeded"
            assert completed.operation.execution_status == "succeeded"
            assert completed.operation.delivery_status == "complete"
            assert completed.outcome is not None
        assert endpoint.effects == [latch]
        assert backend.calls == 1
        assert paths(server) == [
            "/v1/fixture/start",
            "/v1/fixture/access",
            "/v1/fixture/observe",
        ]
        assert len({request.connection for request in server.requests}) == 1
    with open_store(remote_plan[0]) as store:
        validate_contents(store.connection)


@pytest.mark.parametrize("failure", ["timeout", "reply_drop", "task_cancel", "malformed_2xx"])
def test_after_arm_network_failure_preserves_unknown_and_never_replays(
    remote_plan, certificates, execution_clock, failure
):
    endpoint = OperationEndpoint(execution_clock, SECRET)
    if failure == "timeout":
        endpoint.start_reply = lambda body: Reply(body=body, header_delay=0.15)
    elif failure == "reply_drop":
        endpoint.start_reply = lambda body: Reply(body=body, truncate_at=1)
    elif failure == "malformed_2xx":
        endpoint.start_reply = lambda body: Reply(body=b'{"ok":true}')
    with TlsServer(certificates, endpoint.routes()) as server, session(server) as http:
        backend = NetworkBackend(http)
        if failure == "timeout":
            backend.start_timeout = 0.07
        backend.cancel_after_headers = failure == "task_cancel"
        with operation(remote_plan, backend) as coordinator:
            claim = coordinator.admit(remote_plan[2].plan_id)
            identifier = claim.job.operation.operation_id
            invoke = partial(coordinator.dispatch, identifier, claim.ownership)
            with pytest.raises(OperationError) as error:
                invoke()
            assert error.value.code == "operation_uncertain"
            assert error.value.exit_code == 5
            assert error.value.operation_id == identifier
            assert (
                error.value.reason_code
                == {
                    "timeout": "transport_timeout",
                    "reply_drop": "transport_failed",
                    "task_cancel": "request_cancelled",
                    "malformed_2xx": "invalid_response",
                }[failure]
            )
            record = coordinator.repository.operation(identifier)
            assert record.summary.status == "unknown"
            assert record.dispatch_attempt_id is not None
            assert coordinator.admit(remote_plan[2].plan_id).ownership is None
            with pytest.raises(OperationError) as repeated:
                invoke()
            assert repeated.value.code == "operation_conflict"
        assert len(endpoint.effects) == 1
        assert backend.calls == 1
        assert paths(server) == ["/v1/fixture/start"]
    with open_store(remote_plan[0]) as store:
        validate_contents(store.connection)


@pytest.mark.parametrize(
    "stage,reply,reason,request_count",
    [
        ("observe", Reply(status=404, body=b""), "provider_not_found", 1),
        ("observe", Reply(status=401, body=b""), "provider_unauthorized", 1),
        ("observe", Reply(status=403, body=b""), "provider_unauthorized", 1),
        ("observe", Reply(status=503, body=b""), "provider_unavailable", 2),
        ("observe", Reply(body=b"{}"), "evidence_mismatch", 1),
        ("observe", Reply(body=b"{}", truncate_at=1), "provider_unavailable", 1),
        ("access", Reply(status=401, body=b""), "provider_unauthorized", 1),
        ("access", Reply(status=403, body=b""), "provider_unauthorized", 1),
        ("access", Reply(status=503, body=b""), "provider_unavailable", 2),
        ("access", Reply(body=b"{}"), "evidence_mismatch", 1),
        ("access", Reply(body=b"{}", truncate_at=1), "provider_unavailable", 1),
    ],
)
def test_read_endpoint_errors_are_local_unknown_markers_without_terminal_claims(
    remote_plan, certificates, execution_clock, cli, stage, reply, reason, request_count
):
    endpoint = OperationEndpoint(execution_clock, SECRET)
    setattr(endpoint, stage + "_reply", lambda body: reply)
    with TlsServer(certificates, endpoint.routes()) as server, session(server) as http:
        backend = NetworkBackend(http)
        with operation(remote_plan, backend) as coordinator:
            claim = coordinator.admit(remote_plan[2].plan_id)
            identifier = claim.job.operation.operation_id
            coordinator.dispatch(identifier, claim.ownership)
            uncertain = coordinator.reconcile(identifier, claim.ownership)
            assert uncertain.operation.status == "unknown"
            assert uncertain.attempts[-1].reason_code == reason
            assert uncertain.outcome is None
        before = len(server.requests)
        assert paths(server).count("/v1/fixture/" + stage) == request_count
        if stage == "access":
            assert "/v1/fixture/observe" not in paths(server)
        assert api.show_job(identifier, state_dir=remote_plan[0]).data == uncertain
        assert api.list_jobs(state_dir=remote_plan[0]).data.jobs == (uncertain.operation,)
        result = cli(
            "jobs",
            "show",
            "--operation-id",
            identifier,
            "--output",
            "json",
            "--state-dir",
            str(remote_plan[0]),
            state=True,
        )
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["data"]["operation"]["status"] == "unknown"
        assert len(server.requests) == before
        assert len(endpoint.effects) == 1


@pytest.mark.parametrize("evidence", ["cancel_accepted", "wrong_job", "wrong_scope"])
def test_only_matching_typed_evidence_can_change_remote_job_state(
    remote_plan, certificates, execution_clock, evidence
):
    endpoint = OperationEndpoint(execution_clock, SECRET)

    def change(observation):
        if evidence == "cancel_accepted":
            return observation.model_copy(update={"kind": "cancel_accepted"})
        if evidence == "wrong_job":
            return observation.model_copy(update={"provider_run_id": "another-provider-run"})
        return observation.model_copy(
            update={"authority": observation.authority.model_copy(update={"project_id": "other"})}
        )

    endpoint.observation_change = change
    with TlsServer(certificates, endpoint.routes()) as server, session(server) as http:
        backend = NetworkBackend(http)
        with operation(remote_plan, backend) as coordinator:
            claim = coordinator.admit(remote_plan[2].plan_id)
            identifier = claim.job.operation.operation_id
            coordinator.dispatch(identifier, claim.ownership)
            job = coordinator.reconcile(identifier, claim.ownership)
            assert job.operation.status == "unknown"
            assert job.operation.execution_status != "cancelled"
            assert job.outcome is None
            assert job.attempts[-1].reason_code == (
                "provider_unavailable" if evidence == "cancel_accepted" else "evidence_mismatch"
            )
        assert len(endpoint.effects) == 1


@pytest.mark.parametrize("stage", ["admission", "arm"])
def test_final_transaction_rechecks_credential_generation_before_any_http_effect(
    remote_plan, certificates, execution_clock, execution_fixture, monkeypatch, stage
):
    endpoint = OperationEndpoint(execution_clock, SECRET)

    def rotate(assessment):
        monkeypatch.setenv("EVREN_PLATFORM_API_KEY", "rotated-observed-before-arm")
        api.observe_credential("evren-platform", config=remote_plan[1], state_dir=remote_plan[0])
        return assessment

    with TlsServer(certificates, endpoint.routes()) as server, session(server) as http:
        backend = NetworkBackend(http)
        with operation(remote_plan, backend) as coordinator:
            if stage == "arm":
                claim = coordinator.admit(remote_plan[2].plan_id)
                identifier = claim.job.operation.operation_id
                invoke = partial(coordinator.dispatch, identifier, claim.ownership)
            else:
                invoke = partial(coordinator.admit, remote_plan[2].plan_id)
            execution_fixture.change = rotate
            with pytest.raises(YorungeError) as error:
                invoke()
            assert error.value.code == "state_changed"
            if stage == "arm":
                record = coordinator.repository.operation(identifier)
                assert record.summary.status == "admitted"
                assert record.dispatch_attempt_id is None
        assert api.list_jobs(state_dir=remote_plan[0]).data.jobs == (
            (claim.job.operation,) if stage == "arm" else ()
        )
        assert backend.calls == 0
        assert endpoint.effects == []
        assert server.requests == []


@pytest.mark.parametrize("stage", ["admission", "arm"])
@pytest.mark.parametrize("control", [KeyboardInterrupt, asyncio.CancelledError])
def test_pre_arm_interruption_does_not_consume_dispatch_permission(
    remote_plan, certificates, execution_clock, execution_fixture, stage, control
):
    endpoint = OperationEndpoint(execution_clock, SECRET)

    def interrupted(assessment):
        raise control()

    with TlsServer(certificates, endpoint.routes()) as server, session(server) as http:
        backend = NetworkBackend(http)
        with operation(remote_plan, backend) as coordinator:
            if stage == "arm":
                claim = coordinator.admit(remote_plan[2].plan_id)
                identifier = claim.job.operation.operation_id
                invoke = partial(coordinator.dispatch, identifier, claim.ownership)
            else:
                invoke = partial(coordinator.admit, remote_plan[2].plan_id)
            execution_fixture.change = interrupted
            with pytest.raises(control):
                invoke()
            if stage == "arm":
                record = coordinator.repository.operation(identifier)
                assert record.summary.status == "admitted"
                assert record.dispatch_attempt_id is None
        assert backend.calls == 0
        assert endpoint.effects == []
        assert server.requests == []


@pytest.mark.parametrize("stage", ["access", "observe"])
def test_failed_remote_read_cannot_write_a_marker_after_credential_rotation(
    remote_plan, certificates, execution_clock, monkeypatch, stage
):
    endpoint = OperationEndpoint(execution_clock, SECRET)

    def rotate_and_deny(body):
        monkeypatch.setenv("EVREN_PLATFORM_API_KEY", "rotated-observed-during-read")
        api.observe_credential("evren-platform", config=remote_plan[1], state_dir=remote_plan[0])
        return Reply(status=401, body=b"")

    setattr(endpoint, stage + "_reply", rotate_and_deny)
    with TlsServer(certificates, endpoint.routes()) as server, session(server) as http:
        backend = NetworkBackend(http)
        with operation(remote_plan, backend) as coordinator:
            claim = coordinator.admit(remote_plan[2].plan_id)
            identifier = claim.job.operation.operation_id
            coordinator.dispatch(identifier, claim.ownership)
            before = coordinator.repository.operation(identifier)
            invoke = partial(coordinator.reconcile, identifier, claim.ownership)
            with pytest.raises(OperationError) as error:
                invoke()
            assert error.value.code == "state_changed"
            assert coordinator.repository.operation(identifier) == before
        assert len(endpoint.effects) == 1
        if stage == "access":
            assert "/v1/fixture/observe" not in paths(server)


@pytest.mark.parametrize("stage", ["access", "observe"])
def test_cancelled_read_closes_response_without_cancelling_the_remote_operation(
    remote_plan, certificates, execution_clock, stage
):
    endpoint = OperationEndpoint(execution_clock, SECRET)
    with TlsServer(certificates, endpoint.routes()) as server, session(server) as http:
        backend = NetworkBackend(http)
        with operation(remote_plan, backend) as coordinator:
            claim = coordinator.admit(remote_plan[2].plan_id)
            identifier = claim.job.operation.operation_id
            coordinator.dispatch(identifier, claim.ownership)
            before = coordinator.repository.operation(identifier)
            backend.cancel_read_stage = stage
            invoke = partial(coordinator.reconcile, identifier, claim.ownership)
            with pytest.raises(asyncio.CancelledError):
                invoke()
            assert coordinator.repository.operation(identifier) == before
            assert api.show_job(identifier, state_dir=remote_plan[0]).data.outcome is None
            backend.cancel_read_stage = None
            completed = coordinator.reconcile(identifier, claim.ownership)
            assert completed.operation.status == "succeeded"
            assert completed.outcome.reason_code is None
        assert len(endpoint.effects) == 1
        assert paths(server).count("/v1/fixture/start") == 1


@pytest.mark.parametrize("change", ["new_approval", "identity_reset"])
def test_persisted_dispatch_latch_survives_authorization_replacement(
    remote_plan, certificates, execution_clock, change
):
    endpoint = OperationEndpoint(execution_clock, SECRET)
    state, config, plan = remote_plan
    with TlsServer(certificates, endpoint.routes()) as server:
        with session(server) as http:
            backend = NetworkBackend(http)
            with operation(remote_plan, backend) as coordinator:
                claim = coordinator.admit(plan.plan_id)
                identifier = claim.job.operation.operation_id
                coordinator.dispatch(identifier, claim.ownership)
        if change == "new_approval":
            api.revoke_execution_approval(plan.plan_id, state_dir=state)
            approved = api.approve_execution_plan(
                plan.plan_id, plan.digest, config=config, state_dir=state
            ).data
            assert approved.effective
        else:
            preview = api.preview_identity_reset(state_dir=state).data
            api.reset_identity(preview.digest, state_dir=state)
        with session(server) as http:
            backend = NetworkBackend(http)
            with operation(remote_plan, backend) as coordinator:
                repeated = coordinator.admit(plan.plan_id)
                assert repeated.ownership is None
                assert repeated.job.operation.operation_id == identifier
                invoke = partial(coordinator.dispatch, identifier, claim.ownership)
                with pytest.raises(OperationError) as error:
                    invoke()
                assert error.value.code == "operation_conflict"
                record = coordinator.repository.operation(identifier)
                assert record.dispatch_attempt_id == endpoint.effects[0]
            assert backend.calls == 0
        assert len(endpoint.effects) == 1
        assert paths(server) == ["/v1/fixture/start"]


@pytest.mark.parametrize("mode", ["not_entered", "closed", "active_loop"])
def test_invalid_http_composition_stops_before_state_or_credential_access(
    tmp_path, monkeypatch, mode
):
    http = HttpSession()
    if mode in {"closed", "active_loop"}:
        http.__enter__()
    if mode == "closed":
        http.__exit__(None, None, None)
    backend = NetworkBackend(http)

    def forbidden(*args, **kwargs):
        pytest.fail("composition reached credential/state/budget before preflight")

    monkeypatch.setattr(api, "_context", forbidden)
    monkeypatch.setattr(api, "_execution_credentials", forbidden)
    monkeypatch.setattr(api, "_execution_budget", forbidden)
    monkeypatch.setattr("yorunge.adapters.state.open_store", forbidden)
    target = tmp_path / "must-not-exist"
    plan_id = str(uuid4())

    def invoke():
        with api._operation_session(plan_id, backend, state_dir=target):
            pytest.fail("invalid composition yielded coordinator")

    try:
        if mode == "active_loop":

            async def run():
                invoke()

            pending = run()
            target_call = partial(asyncio.run, pending)
        else:
            target_call = invoke
        with pytest.raises(YorungeError) as error:
            target_call()
        assert error.value.code == "invalid_request"
        assert not target.exists()
        assert backend.calls == 0
    finally:
        if mode == "active_loop":
            http.__exit__(None, None, None)


def test_new_process_takes_over_and_reconciles_without_a_second_start(
    remote_plan, certificates, execution_clock
):
    endpoint = OperationEndpoint(execution_clock, SECRET)
    with TlsServer(certificates, endpoint.routes()) as server:
        with session(server) as http:
            backend = NetworkBackend(http)
            with operation(remote_plan, backend) as coordinator:
                claim = coordinator.admit(remote_plan[2].plan_id)
                identifier = claim.job.operation.operation_id
                submitted = coordinator.dispatch(identifier, claim.ownership)
                attempt = submitted.attempts[-1].attempt_id
        execution_clock.value += timedelta(seconds=31)
        script = """
import json, ssl, sys, time
from datetime import datetime
from pathlib import Path
from tests.fixtures.http_operations import NetworkBackend
from tests.fixtures.http_server import LoopbackTransport
from yorunge import api
from yorunge.adapters import capability_cache
from yorunge.adapters.http_session import HttpSession
from yorunge.adapters.http_transport import HttpxTransport
from yorunge.domain.errors import OperationError
state, config, plan, identifier, port, cert, now = sys.argv[1:]
class Clock:
    def now(self): return datetime.fromisoformat(now)
    def monotonic(self): return time.monotonic()
capability_cache.SystemClock = Clock
context = ssl.create_default_context(cafile=cert)
with HttpSession(transport_factory=lambda: HttpxTransport(
    transport=LoopbackTransport(int(port), context))) as http:
    backend = NetworkBackend(http)
    with api._operation_session(plan, backend, observer=backend,
        state_dir=Path(state), config=Path(config)) as coordinator:
        claim = coordinator.takeover(identifier)
        assert claim.job.operation.status == 'unknown'
        try:
            coordinator.dispatch(identifier, claim.ownership)
        except OperationError as error:
            assert error.code == 'operation_conflict'
        else:
            raise AssertionError('restart allowed another dispatch')
        completed = coordinator.reconcile(identifier, claim.ownership)
        print(json.dumps({'job': completed.model_dump(mode='json'), 'starts': backend.calls}))
"""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                script,
                str(remote_plan[0]),
                str(remote_plan[1]),
                remote_plan[2].plan_id,
                identifier,
                str(server.port),
                str(certificates[0]),
                execution_clock.value.isoformat(),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0, result.stderr
        restarted = json.loads(result.stdout)
        assert restarted["starts"] == 0
        assert restarted["job"]["operation"]["operation_id"] == identifier
        assert restarted["job"]["operation"]["status"] == "succeeded"
        assert restarted["job"]["attempts"][-1]["attempt_id"] == attempt
        assert endpoint.effects == [attempt]
        assert paths(server).count("/v1/fixture/start") == 1
    with open_store(remote_plan[0]) as store:
        validate_contents(store.connection)
