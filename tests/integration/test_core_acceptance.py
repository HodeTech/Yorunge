"""Independent full-core acceptance across real processes, TLS and SQLite.

This synthetic journey is not a registered provider, a live EVREN experiment,
physical power-loss evidence or a public execution capability.
"""

from __future__ import annotations

import hashlib
import json
import os
import selectors
import signal
import socket
import subprocess
import sys
import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import pytest

from tests.fixtures.http_operations import OperationEndpoint
from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from yorunge import api
from yorunge.adapters.operation_store import read_operation
from yorunge.adapters.state import open_store, validate_contents

CONNECT = socket.socket.connect
CONNECT_EX = socket.socket.connect_ex
GETADDRINFO = socket.getaddrinfo
WORKER = Path(__file__).resolve().parents[1] / "fixtures" / "core_acceptance_worker.py"
SELECTED_SECRET = "synthetic-core-acceptance-selected-token-90324"
SELECTED_ENV = "YORUNGE_ACCEPTANCE_PLATFORM_TOKEN"
STREAM_ID = "5cbcd726-42dd-4ab5-ac7c-03c33f306c93"
INPUT = b'{"dataset":"synthetic-acceptance","rows":2}\n'
INPUT_SHA256 = "5e219e800ae7c0bb0cd80d947eb5c79bcaa9810269546aaf5139dbbfbf34dddf"
NOW = datetime(2026, 10, 29, tzinfo=UTC)
PROVIDER_RUN_ID = "tls-fixture-run-1"
RECEIPT = {
    "provider_run_id": PROVIDER_RUN_ID,
    "input_sha256": INPUT_SHA256,
    "result_code": "fixture-complete",
}


def read(root, name):
    return json.loads((root / name).read_text(encoding="utf-8"))


def command(root, mode, server=None, *options):
    args = [sys.executable, "-W", "error", str(WORKER), mode, "--root", str(root)]
    if server is not None:
        args += ["--ca", str(server.certificates[0]), "--port", str(server.port)]
    return [*args, *options]


def environment(*, credentials=True):
    result = dict(os.environ)
    result[SELECTED_ENV] = SELECTED_SECRET
    # The default service variables are deliberate decoys. The configured
    # selected reference is the only credential accepted by the remote fixture.
    result["EVREN_PLATFORM_API_KEY"] = "wrong-default-platform-token"
    result["EVREN_LLM_API_KEY"] = "wrong-default-llm-token"
    result["YORUNGE_ACCEPTANCE_UNUSED_LLM_TOKEN"] = "wrong-unused-service-token"
    if not credentials:
        for name in (
            SELECTED_ENV,
            "EVREN_PLATFORM_API_KEY",
            "EVREN_LLM_API_KEY",
            "YORUNGE_ACCEPTANCE_UNUSED_LLM_TOKEN",
        ):
            result.pop(name, None)
    return result


def invoke(root, mode, server=None, *options):
    return subprocess.run(
        command(root, mode, server, *options),
        env=environment(credentials=mode != "jobs"),
        capture_output=True,
        timeout=12,
    )


@contextmanager
def running(root, mode, server, *options):
    process = subprocess.Popen(
        command(root, mode, server, *options),
        env=environment(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        yield process
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=10)


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(tmp_path_factory.mktemp("core-acceptance-tls"))


@pytest.fixture(autouse=True)
def actual_loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


@pytest.fixture
def journey(tmp_path):
    root = tmp_path / "journey"
    root.mkdir()
    (root / "inputs").mkdir()
    (root / "inputs" / "manifest.json").write_bytes(INPUT)
    (root / "recipe.yaml").write_text(
        "schema_version: 1\ntask: llm.train\ndata: {manifest: manifest.json}\n"
        "execution: {backend: evren-workspace}\n",
        encoding="utf-8",
    )
    (root / "clock.txt").write_text("2026-10-29T00:00:00.000000Z", encoding="ascii")
    result = invoke(root, "bootstrap")
    assert result.returncode == 0, result.stderr.decode()
    assert result.stdout == b"" and result.stderr == b""
    return root


class Clock:
    def __init__(self, root):
        self.root = root

    def now(self):
        return datetime.fromisoformat((self.root / "clock.txt").read_text().replace("Z", "+00:00"))


def endpoint(root):
    return OperationEndpoint(Clock(root), SELECTED_SECRET)


def paths(server):
    return [urlsplit(request.path).path for request in server.requests]


def event_bytes(kind, sequence, operation, payload):
    # Wire oracle intentionally does not call encode_event/result_event or the
    # expected model parser. Fixed payload/domain expectations are independent.
    return (
        json.dumps(
            {
                "schema_version": 1,
                "stream_id": STREAM_ID,
                "sequence": sequence,
                "event": kind,
                "operation_id": operation,
                "payload": payload,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
        + b"\n"
    )


def stream_body(operation):
    return b"".join(
        (
            event_bytes(
                "progress", 1, operation, {"stage": "receiving", "completed": 1, "total": 2}
            ),
            event_bytes(
                "progress", 2, operation, {"stage": "validating", "completed": 2, "total": 2}
            ),
            event_bytes(
                "result",
                3,
                operation,
                {
                    "schema_version": 1,
                    "status": "completed",
                    "operation_id": None,
                    "data": RECEIPT,
                    "warnings": [],
                },
            ),
        )
    )


def routes(remote, root, *, stream_reply=None):
    class Routes(dict):
        def get(self, key, default=None):
            if urlsplit(key).path == "/v1/fixture/events":
                return events
            return remote.routes().get(key, default)

    def events(request, count):
        assert request.method == "GET"
        assert request.header("Authorization") == "Bearer " + SELECTED_SECRET
        query = parse_qs(urlsplit(request.path).query)
        operation = read(root, "claim.json")["operation_id"]
        assert query == {
            "operation_id": [operation],
            "stream_id": [STREAM_ID],
            "correlation": [remote.correlation],
        }
        body = stream_body(operation)
        return stream_reply(body) if stream_reply else Reply(body=body, chunk_size=7)

    return Routes()


def saved(root):
    identifier = read(root, "claim.json")["operation_id"]
    with open_store(root / "state") as store:
        validate_contents(store.connection)
        return read_operation(store.connection, identifier)


def records(output):
    assert output.endswith(b"\n")
    return [json.loads(line) for line in output.splitlines()]


def assert_history(root, expected_status, cli):
    """Fresh Python and public CLI read the same record without network/auth/input."""
    identifier = read(root, "claim.json")["operation_id"]
    # Historical queries must survive absent config/input paths and env secrets.
    # Restoring the same directory preserves the descriptor-bound inode used by
    # subsequent trusted recovery; no replacement input is silently accepted.
    (root / "config.toml").rename(root / "config.unavailable")
    (root / "inputs").rename(root / "inputs.unavailable")
    try:
        python = invoke(root, "jobs")
        assert python.returncode == 0, python.stderr
        result = cli(
            "jobs",
            "show",
            "--operation-id",
            identifier,
            "--state-dir",
            str(root / "state"),
            "--output",
            "json",
            state=True,
            secret_names=(SELECTED_ENV, "YORUNGE_ACCEPTANCE_UNUSED_LLM_TOKEN"),
        )
        assert result.returncode == 0, result.stderr
    finally:
        (root / "config.unavailable").rename(root / "config.toml")
        (root / "inputs.unavailable").rename(root / "inputs")
    assert json.loads(python.stdout) == json.loads(result.stdout)
    job = json.loads(python.stdout)["data"]
    prepared = read(root, "prepared.json")["prepared"]["plan"]
    assert job["operation"]["status"] == expected_status
    assert job["operation"]["operation_id"] == identifier
    assert job["operation"]["plan_id"] == prepared["plan_id"]
    assert job["operation"]["plan_digest"] == prepared["digest"]
    assert job["plan"] == prepared
    assert len(job["attempts"]) == 1
    listed = api.list_jobs(state_dir=root / "state").data
    assert [item.operation_id for item in listed.jobs] == [identifier]
    assert SELECTED_SECRET.encode() not in python.stdout + python.stderr + result.stdout.encode()
    return job


def recover(root, server, *, seconds=31, fence=2):
    # Real process restart with a fixed 31-second advance, never a lease sleep.
    (root / "clock.txt").write_text(
        (NOW + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    )
    result = invoke(root, "recover", server)
    assert result.returncode == 0, result.stderr
    assert result.stdout == b"" and result.stderr == b""
    report = read(root, "recovered.json")
    assert report["errors"] == {
        "stale_owner": "operation_lease_lost",
        "redispatch": "operation_conflict",
    }
    assert report["start_calls"] == 0
    assert report["takeover_status"] == "unknown"
    assert report["record"]["fence"] == fence
    assert report["record"]["dispatch_attempt_id"] is not None
    return report


def test_full_journey_binds_real_input_identity_approval_and_typed_stream_after_restart(
    journey, certificates, cli
):
    initial = read(journey, "prepared.json")
    plan, approval = initial["prepared"]["plan"], initial["approval"]
    assert initial["initialized"]["data"]["active_profile"] == "work"
    assert initial["initialized"]["data"]["project_id"] == "fixture-project"
    assert initial["state"]["data"]["store_schema_version"] == 6
    assert initial["context"]["data"]["profile"] == "work"
    assert initial["context"]["data"]["account_id"] == "fixture-account"
    assert plan["status"] == "prepared" and plan["executable"] is False
    assert plan["selection"] == {
        "task": "llm.train",
        "tool": "forgelm",
        "execution": "evren-workspace",
        "tool_source": "product_default",
        "tool_version": None,
        "execution_source": "recipe",
    }
    assert plan["inputs"] == [
        {
            "role": "data.manifest",
            "path": "manifest.json",
            "size": len(INPUT),
            "digest": INPUT_SHA256,
        }
    ]
    assert plan["input_root"]["anchor"] == str((journey / "inputs").resolve())
    actual = (journey / "inputs").stat()
    assert (plan["input_root"]["device"], plan["input_root"]["inode"]) == (
        actual.st_dev,
        actual.st_ino,
    )
    body = {key: value for key, value in plan.items() if key != "digest"}
    independent = json.dumps(
        body, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode()
    assert hashlib.sha256(independent).hexdigest() == plan["digest"]
    assert approval["effective"] is True
    assert approval["record"]["plan_digest"] == plan["digest"]
    identity = initial["identity"]["data"]["identity"]
    scope = plan["assessment"]["capabilities"][0]["key"]["scope"]
    assert UUID(identity["credential_id"]).version == 4
    assert scope["credential_id"] == identity["credential_id"]
    assert scope["credential_revision"] == 1 == identity["credential_revision"]
    assert scope["service_id"] == "evren-platform"
    assert scope["service_origin"] == "https://localhost" and scope["api_base_path"] == "/v1"
    assert scope["account_id"] == "fixture-account" and scope["project_id"] == "fixture-project"
    proof = plan["assessment"]["capabilities"][0]["evidence"][0]
    assert proof["kind"] == "live_account" and proof["support"] == "supported"
    assert proof["producer_id"] == "fixture-execution" and proof["provenance"] == "fixture-only"
    assert initial["public"]["plan"]["status"] == "draft"
    assert initial["public"]["validity"]["valid"] is False
    assert "execution_adapter_unavailable" in initial["public"]["plan"]["assessment"]["blockers"]
    assert initial["public_approval_error"] == "plan_not_valid"
    remote = endpoint(journey)
    with TlsServer(certificates, routes(remote, journey)) as server:
        result = invoke(journey, "dispatch", server, "--stream", "--reconcile")
        assert result.returncode == 0, result.stderr
        events = records(result.stdout)
        assert [event["event"] for event in events] == ["progress", "progress", "result"]
        assert [event["sequence"] for event in events] == [1, 2, 3]
        identifier = read(journey, "claim.json")["operation_id"]
        assert all(e["operation_id"] == identifier and e["stream_id"] == STREAM_ID for e in events)
        assert events[-1]["payload"]["data"] == RECEIPT
        assert result.stderr == b"" and SELECTED_SECRET.encode() not in result.stdout
        before = len(server.requests)
        job = assert_history(journey, "succeeded", cli)
        assert job == read(journey, "finished.json")
        assert job["outcome"]["execution_status"] == "succeeded"
        assert job["outcome"]["delivery_status"] == "complete"
        assert job["attempts"][0]["provider_run_id"] == PROVIDER_RUN_ID
        record = saved(journey)
        assert record.dispatch_attempt_id == remote.effects[0]
        assert len(server.requests) == before and len(remote.effects) == 1
        assert paths(server) == [
            "/v1/fixture/start",
            "/v1/fixture/events",
            "/v1/fixture/access",
            "/v1/fixture/observe",
        ]


@pytest.mark.parametrize("failure", ["lost_receipt", "deadline", "cancel"])
def test_after_arm_lost_receipt_deadline_and_cancel_recover_same_job_without_dispatch(
    journey, certificates, cli, failure
):
    remote = endpoint(journey)
    if failure == "lost_receipt":
        remote.start_reply = lambda body: Reply(body=body, truncate_at=1)
    elif failure == "deadline":
        remote.start_reply = lambda body: Reply(body=body, header_delay=0.2)
    with TlsServer(certificates, routes(remote, journey)) as server:
        extra = () if failure == "lost_receipt" else ("--failure", failure)
        result = invoke(journey, "dispatch", server, *extra)
        assert result.returncode == 5, result.stderr
        error = json.loads(result.stderr)
        assert error["code"] == "operation_uncertain" and result.stdout == b""
        assert (
            error["details"]["reason_code"]
            == {
                "lost_receipt": "transport_failed",
                "deadline": "transport_timeout",
                "cancel": "request_cancelled",
            }[failure]
        )
        before = saved(journey)
        assert before.summary.status == "unknown" and before.dispatch_attempt_id is not None
        job = assert_history(journey, "unknown", cli)
        assert job["outcome"] is None
        report = recover(journey, server)
        assert report["record"]["dispatch_attempt_id"] == before.dispatch_attempt_id
        assert report["job"]["operation"]["operation_id"] == error["operation_id"]
        assert report["job"]["operation"]["status"] == "succeeded"
        assert_history(journey, "succeeded", cli)
        assert remote.effects == [before.dispatch_attempt_id]
        assert paths(server) == ["/v1/fixture/start", "/v1/fixture/access", "/v1/fixture/observe"]


@pytest.mark.parametrize("evidence", ["unauthorized", "wrong_job"])
def test_unknown_recovery_needs_current_auth_and_matching_typed_provider_evidence(
    journey, certificates, cli, evidence
):
    remote = endpoint(journey)
    remote.start_reply = lambda body: Reply(body=body, truncate_at=1)
    if evidence == "unauthorized":
        remote.access_reply = lambda body: Reply(status=403, body=b"")
    else:
        remote.observation_change = lambda observation: observation.model_copy(
            update={"correlation": "c3b03835-730a-4464-8994-15fa872ecacd"}
        )
    with TlsServer(certificates, routes(remote, journey)) as server:
        result = invoke(journey, "dispatch", server)
        assert result.returncode == 5, result.stderr
        latch = saved(journey).dispatch_attempt_id
        rejected = recover(journey, server)
        assert rejected["job"]["operation"]["status"] == "unknown"
        assert rejected["job"]["outcome"] is None
        assert rejected["job"]["attempts"][0]["reason_code"] == (
            "provider_unauthorized" if evidence == "unauthorized" else "evidence_mismatch"
        )
        assert_history(journey, "unknown", cli)
        if evidence == "unauthorized":
            assert "/v1/fixture/observe" not in paths(server)
        remote.access_reply = lambda body: Reply(body=body)
        remote.observation_change = None
        completed = recover(journey, server, seconds=62, fence=3)
        assert completed["job"]["operation"]["status"] == "succeeded"
        assert completed["record"]["dispatch_attempt_id"] == latch
        assert_history(journey, "succeeded", cli)
        assert remote.effects == [latch]
        assert paths(server).count("/v1/fixture/start") == 1


def test_actual_sigkill_after_remote_effect_preserves_latch_and_unknown_takeover(
    journey, certificates, cli
):
    remote = endpoint(journey)
    effect, release = threading.Event(), threading.Event()

    def pending_receipt(body):
        # OperationEndpoint has already applied exactly one effect before this
        # barrier. Killing the client here cannot leave a saved receipt.
        effect.set()
        assert release.wait(10), "parent did not release the remote effect barrier"
        return Reply(body=body)

    remote.start_reply = pending_receipt
    with TlsServer(certificates, routes(remote, journey)) as server:
        try:
            with running(journey, "dispatch", server) as process:
                assert effect.wait(8), "child did not reach the remote effect"
                assert not (journey / "submitted.json").exists()
                process.send_signal(signal.SIGKILL)
                stdout, stderr = process.communicate(timeout=8)
                assert process.returncode == -signal.SIGKILL
                assert stdout == b"" and stderr == b""
            before = saved(journey)
            assert before.dispatch_attempt_id == remote.effects[0]
            assert before.summary.status == "submitted"
            assert_history(journey, "submitted", cli)
        finally:
            release.set()
        report = recover(journey, server)
        assert report["record"]["dispatch_attempt_id"] == before.dispatch_attempt_id
        assert report["job"]["operation"]["status"] == "succeeded"
        assert_history(journey, "succeeded", cli)
        assert remote.effects == [before.dispatch_attempt_id]
        assert paths(server).count("/v1/fixture/start") == 1


@pytest.mark.parametrize("change", ["target", "credential", "revoke", "input"])
def test_prearm_context_credential_approval_and_descriptor_changes_have_zero_http_effect(
    journey, certificates, change
):
    remote = endpoint(journey)
    original = read(journey, "prepared.json")["prepared"]["plan"]
    with TlsServer(certificates, routes(remote, journey)) as server:
        result = invoke(journey, "dispatch", server, "--mutation", change)
        assert result.returncode != 0 and result.stdout == b"", result.stderr
        error = json.loads(result.stderr)
        assert (
            error["code"]
            == {
                "target": "state_changed",
                "credential": "state_changed",
                "revoke": "approval_required",
                "input": "plan_not_valid",
            }[change]
        )
        assert server.requests == [] and remote.effects == []
        if change != "target":
            record = saved(journey)
            assert record.dispatch_attempt_id is None and record.summary.status == "admitted"
        else:
            assert api.list_jobs(state_dir=journey / "state").data.jobs == ()
    assert (
        api.show_execution_plan(
            original["plan_id"], state_dir=journey / "state"
        ).data.plan.model_dump(mode="json")
        == original
    )


@pytest.mark.parametrize("interruption", ["truncated", "sigint"])
def test_readonly_watch_interruption_preserves_submitted_job_and_never_resubscribes(
    journey, certificates, cli, interruption
):
    remote = endpoint(journey)
    first_sent, release = threading.Event(), threading.Event()

    def reply(body):
        operation = read(journey, "claim.json")["operation_id"]
        first = event_bytes(
            "progress", 1, operation, {"stage": "receiving", "completed": 1, "total": 2}
        )
        if interruption == "truncated":
            return Reply(body=body, chunk_size=len(first), truncate_at=len(first))

        def paused():
            first_sent.set()
            assert release.wait(10), "parent did not release stream barrier"

        return Reply(body=body, chunk_size=len(first), after_first_chunk=paused)

    with TlsServer(certificates, routes(remote, journey, stream_reply=reply)) as server:
        submitted = invoke(journey, "dispatch", server)
        assert submitted.returncode == 0, submitted.stderr
        before = assert_history(journey, "submitted", cli)
        try:
            with running(journey, "watch", server) as process:
                first = b""
                if interruption == "sigint":
                    assert process.stdout is not None
                    with selectors.DefaultSelector() as selector:
                        selector.register(process.stdout, selectors.EVENT_READ)
                        assert selector.select(8), "watch did not publish progress"
                    first = process.stdout.readline()
                    assert first_sent.wait(2)
                    process.send_signal(signal.SIGINT)
                stdout, stderr = process.communicate(timeout=10)
                assert process.returncode == (6 if interruption == "sigint" else 1), stderr
            events = records(first + stdout)
            assert [event["event"] for event in events] == ["progress", "error"]
            assert events[-1]["payload"]["code"] == (
                "request_cancelled" if interruption == "sigint" else "stream_interrupted"
            )
            assert events[-1]["payload"]["operation_id"] == before["operation"]["operation_id"]
            assert stderr == b"" and b'"status":"completed"' not in stdout
            assert assert_history(journey, "submitted", cli) == before
            assert len(remote.effects) == 1
            assert paths(server) == ["/v1/fixture/start", "/v1/fixture/events"]
        finally:
            release.set()

        remote.observation_change = lambda observation: observation.model_copy(
            update={
                "execution_status": "cancelled",
                "delivery_status": "pending",
                "provider_status": "cancelled",
                "provider_exit_code": None,
            }
        )
        verified = recover(journey, server)
        assert verified["job"]["operation"]["status"] == "cancelled"
        assert verified["job"]["outcome"]["reason_code"] == "provider_cancelled"
        assert_history(journey, "cancelled", cli)
        assert len(remote.effects) == 1
        assert paths(server) == [
            "/v1/fixture/start",
            "/v1/fixture/events",
            "/v1/fixture/access",
            "/v1/fixture/observe",
        ]
