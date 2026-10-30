"""Public API/CLI parity through real TLS, actual child processes and hostile stdio."""

import asyncio
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from yorunge import api
from yorunge.adapters import llm_context
from yorunge.adapters.http_session import HttpSession
from yorunge.adapters.http_transport import HttpxTransport
from yorunge.adapters.secrets import EnvSecretReader
from yorunge.adapters.state import open_store
from yorunge.domain.errors import YorungeError

CONNECT = socket.socket.connect
CONNECT_EX = socket.socket.connect_ex
GETADDRINFO = socket.getaddrinfo
SECRET = "synthetic-public-llm-secret-65179"
PLATFORM_SECRET = "synthetic-platform-only-secret-18562"
BODY = b'{"accepted":true,"current_version":3,"is_material":false,"doc_path":"terms/v3.md"}'
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(tmp_path_factory.mktemp("public-discovery-tls"))


@pytest.fixture(autouse=True)
def actual_loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


@pytest.fixture
def context_files(tmp_path, monkeypatch):
    config = tmp_path / "remote.toml"
    config.write_text(
        'schema_version=1\nactive_profile="work"\n[profiles.work]\n'
        'llm_url="https://localhost/v1"\nllm_key_env="EVREN_LLM_API_KEY"\n'
        'platform_key_env="EVREN_PLATFORM_API_KEY"\n'
        'account_id="platform-account"\nproject_id="platform-project"\n'
    )
    monkeypatch.setenv("EVREN_LLM_API_KEY", SECRET)
    monkeypatch.setenv("EVREN_PLATFORM_API_KEY", PLATFORM_SECRET)
    state = tmp_path / "state"
    api.initialize_state(state_dir=state)
    return config, state


def child_command(server, certificates, config, root, *options):
    return [
        sys.executable,
        "-m",
        "tests.fixtures.discovery_cli",
        str(server.port),
        str(certificates[0]),
        "context",
        "discover",
        "--service",
        "evren-llm",
        "--config",
        str(config),
        "--state-dir",
        str(root),
        *options,
    ]


def child(server, certificates, config, root, *options):
    env = dict(os.environ)
    env.update({"LC_ALL": "C", "PYTHONIOENCODING": "ascii", "PYTHONUTF8": "0"})
    return subprocess.run(
        child_command(server, certificates, config, root, *options),
        cwd=ROOT,
        env=env,
        capture_output=True,
        timeout=8,
    )


def bind_fixture(monkeypatch, server):
    monkeypatch.setattr(
        llm_context,
        "HttpSession",
        lambda: HttpSession(transport_factory=lambda: HttpxTransport(transport=server.transport())),
    )


@pytest.mark.parametrize("output", ["json", "ndjson"])
def test_public_api_and_real_cli_use_the_same_typed_core_and_only_the_llm_key(
    context_files, certificates, monkeypatch, output
):
    config, root = context_files
    calls = []
    read = EnvSecretReader.read

    def counted(reader, reference):
        calls.append(reference.service_id)
        return read(reader, reference)

    monkeypatch.setattr(EnvSecretReader, "read", counted)
    with TlsServer(certificates, {"/v1/terms/status": Reply(body=BODY)}) as server:
        bind_fixture(monkeypatch, server)
        expected = api.discover_context("evren-llm", config=config, state_dir=root)
        result = child(server, certificates, config, root, "--output", output)
    assert calls == ["evren-llm"]
    assert result.returncode == 0, result.stderr
    assert result.stderr == b""
    assert result.stdout.count(b"\n") == 1
    wire = json.loads(result.stdout)
    if output == "ndjson":
        assert wire["event"] == "result"
        assert wire["sequence"] == 1
        wire = wire["payload"]
    assert wire["status"] == "completed"
    assert wire["operation_id"] is None
    assert wire["warnings"] == ["context_not_verified"]
    data = wire["data"]
    expected_data = expected.data.model_dump(mode="json")
    for name in ("terms", "selected", "profile_preference", "provider", "binding", "reasons"):
        assert data[name] == expected_data[name]
    assert data["validation"] == "unverified"
    assert data["observations"][0]["authentication"] == "unknown"
    assert len(server.requests) == 2
    assert all(r.header("Authorization") == "Bearer " + SECRET for r in server.requests)
    assert SECRET.encode() not in result.stdout
    assert PLATFORM_SECRET.encode() not in result.stdout
    assert b"terms/v3.md" not in result.stdout


def test_public_text_is_utf8_and_explicit_about_terms_and_unverified_identity(
    context_files, certificates
):
    config, root = context_files
    with TlsServer(certificates, {"/v1/terms/status": Reply(body=BODY)}) as server:
        result = child(server, certificates, config, root)
    assert result.returncode == 0, result.stderr
    text = result.stdout.decode("utf-8", "strict")
    assert "şart durumu: kabul edilmiş" in text
    assert "doğrulanmadı" in text
    assert "hizmet kapsamı bilinmiyor" in text
    assert result.stderr == b""


def test_api_default_state_is_explicit_and_does_not_fall_back_from_another_root(
    context_files, certificates, monkeypatch
):
    config, explicit = context_files
    default = api.initialize_state().data
    with TlsServer(certificates, {"/v1/terms/status": Reply(body=BODY)}) as server:
        bind_fixture(monkeypatch, server)
        first = api.discover_context("evren-llm", config=config).data
        second = api.discover_context("evren-llm", config=config, state_dir=explicit).data
    assert first.binding.store_id == default.store_id
    assert first.binding.store_id != second.binding.store_id
    assert len(server.requests) == 2


def test_cli_platform_gate_is_explicit_without_env_state_or_remote_access(cli):
    result = cli("context", "discover", "--service", "evren-platform", "--output=json")
    assert result.returncode == 2
    assert result.stdout == ""
    assert json.loads(result.stderr)["code"] == "unsupported_combination"


@pytest.mark.parametrize("option", ["--config", "--service", "--output"])
def test_cli_repeated_singleton_forms_are_rejected_before_dispatch(
    context_files, certificates, option
):
    config, root = context_files
    value = {"--config": str(config), "--service": "evren-llm", "--output": "text"}[option]
    with TlsServer(certificates, {}) as server:
        result = child(server, certificates, config, root, option + "=" + value, "--output=json")
    assert result.returncode == 2
    assert result.stdout == b""
    assert json.loads(result.stderr)["code"] == "invalid_request"
    assert server.requests == []


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"service_id": "unknown"}, "invalid_request"),
        ({"service_id": True}, "invalid_request"),
        ({"service_id": "evren-platform"}, "unsupported_combination"),
        ({"project": "explicit-platform-project"}, "invalid_request"),
        ({"config": "string-not-Path"}, "invalid_request"),
        ({"state_dir": "string-not-Path"}, "invalid_request"),
        ({"profile": 4}, "invalid_request"),
    ],
)
def test_api_rejects_invalid_or_gated_inputs_before_env_state_or_client(
    tmp_path, monkeypatch, overrides, expected
):
    def denied(*args, **kwargs):
        pytest.fail("invalid request must not read config/state/env or create a client")

    monkeypatch.setattr(api, "_context", denied)
    monkeypatch.setattr(EnvSecretReader, "read", denied)
    monkeypatch.setattr(HttpSession, "__enter__", denied)
    arguments = {"service_id": "evren-llm", "state_dir": tmp_path / "missing", **overrides}
    with pytest.raises(YorungeError) as failure:
        api.discover_context(**arguments)
    assert failure.value.code == expected


def test_api_active_loop_rejects_before_config_or_secret_resolution(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail("active-loop call must not capture context or credentials")

    monkeypatch.setattr(api, "_context", denied)
    monkeypatch.setattr(EnvSecretReader, "read", denied)

    async def attempt():
        with pytest.raises(YorungeError) as failure:
            api.discover_context("evren-llm", state_dir=tmp_path / "missing")
        assert failure.value.code == "invalid_request"

    asyncio.run(attempt())
    assert not (tmp_path / "missing").exists()


@pytest.mark.parametrize("extra", [["--project", "project"], ["--state-dir", "other"]])
def test_cli_invalid_or_repeated_discovery_options_reject_without_request(
    context_files, certificates, extra
):
    config, root = context_files
    with TlsServer(certificates, {}) as server:
        result = child(server, certificates, config, root, *extra, "--output=ndjson")
    assert result.returncode == 2
    assert result.stdout == b""
    assert json.loads(result.stderr)["code"] == "invalid_request"
    assert server.requests == []


@pytest.mark.parametrize("output", ["json", "ndjson"])
def test_cli_missing_existing_store_is_state_invalid_and_has_no_remote_call(
    tmp_path, context_files, certificates, output
):
    config, _ = context_files
    root = tmp_path / "missing"
    with TlsServer(certificates, {}) as server:
        result = child(server, certificates, config, root, "--output", output)
    assert result.returncode == 2
    assert result.stdout == b""
    assert json.loads(result.stderr)["code"] == "state_invalid"
    assert server.requests == []
    assert not root.exists()


@pytest.mark.parametrize(
    ("status", "expected", "exit_code"),
    [
        (403, "remote_access_denied", 3),
        (404, "invalid_response", 1),
    ],
)
def test_cli_remote_error_is_a_safe_utf8_stderr_envelope(
    context_files, certificates, status, expected, exit_code
):
    config, root = context_files
    with TlsServer(certificates, {"/v1/terms/status": Reply(status=status)}) as server:
        result = child(server, certificates, config, root, "--output=json")
    assert result.returncode == exit_code
    assert result.stdout == b""
    assert result.stderr.count(b"\n") == 1
    assert json.loads(result.stderr.decode("utf-8"))["code"] == expected
    assert b"Traceback" not in result.stderr


def test_api_does_not_resolve_environment_again_after_network_start(
    context_files, certificates, monkeypatch
):
    config, root = context_files
    calls = []
    read = EnvSecretReader.read

    def counted(reader, reference):
        calls.append(True)
        return read(reader, reference)

    def change_unobserved_environment(record, count):
        monkeypatch.setenv("EVREN_LLM_API_KEY", "different-unobserved-value")
        return Reply(body=BODY)

    monkeypatch.setattr(EnvSecretReader, "read", counted)
    with TlsServer(certificates, {"/v1/terms/status": change_unobserved_environment}) as server:
        bind_fixture(monkeypatch, server)
        result = api.discover_context("evren-llm", config=config, state_dir=root)
    assert calls == [True]
    assert result.data.terms.accepted is True
    assert server.requests[0].header("Authorization") == "Bearer " + SECRET


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal contract")
def test_cli_sigint_waiting_for_headers_closes_and_preserves_read_only_semantics(
    context_files, certificates
):
    config, root = context_files
    with TlsServer(certificates, {"/v1/terms/status": Reply(body=BODY, header_delay=2)}) as server:
        process = subprocess.Popen(
            child_command(server, certificates, config, root, "--output=json"),
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            end = time.monotonic() + 5
            while not server.requests and process.poll() is None and time.monotonic() < end:
                time.sleep(0.01)
            assert server.requests, "child did not begin the fixture request"
            process.send_signal(signal.SIGINT)
            stdout, stderr = process.communicate(timeout=6)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
    assert process.returncode == 6
    assert stdout == b""
    assert json.loads(stderr)["code"] == "request_cancelled"
    assert b"Traceback" not in stderr
    assert len(server.requests) == 1
    with open_store(root) as store:
        assert store.connection.execute("SELECT count(*) FROM operations").fetchone() == (0,)


def test_cli_broken_pipe_after_success_keeps_local_observation_and_has_no_traceback(
    context_files, certificates
):
    config, root = context_files
    with TlsServer(certificates, {"/v1/terms/status": Reply(body=BODY)}) as server:
        process = subprocess.Popen(
            child_command(server, certificates, config, root, "--output=json"),
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            process.stdout.close()
            process.stdout = None
            _, stderr = process.communicate(timeout=6)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    assert process.returncode == 6
    assert json.loads(stderr)["code"] == "output_closed"
    assert b"Traceback" not in stderr
    assert len(server.requests) == 1
    with open_store(root) as store:
        assert store.connection.execute("SELECT count(*) FROM credential_bindings").fetchone() == (
            1,
        )
        assert store.connection.execute("SELECT count(*) FROM operations").fetchone() == (0,)
