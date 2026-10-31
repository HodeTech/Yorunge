"""Platform public API/CLI parity, actual subprocess stdio and no implicit authority."""

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
from yorunge.adapters import platform_context
from yorunge.adapters.http_session import HttpSession
from yorunge.adapters.http_transport import HttpxTransport
from yorunge.adapters.secrets import EnvSecretReader
from yorunge.domain.platform_discovery import PlatformContextDiscovery

CONNECT, CONNECT_EX, GETADDRINFO = (
    socket.socket.connect,
    socket.socket.connect_ex,
    socket.getaddrinfo,
)
SECRET = "synthetic-public-platform-key-25431"
OTHER = "synthetic-llm-key-not-selected-24982"
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(tmp_path_factory.mktemp("public-platform-tls"))


@pytest.fixture(autouse=True)
def actual_loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


@pytest.fixture
def files(tmp_path, monkeypatch):
    config = tmp_path / "platform.toml"
    config.write_text(
        'schema_version=1\nactive_profile="work"\n[profiles.work]\nplatform_url="https://localhost/api/v1"\nplatform_key_env="EVREN_PLATFORM_API_KEY"\nllm_key_env="EVREN_LLM_API_KEY"\naccount_id="preferred"\nproject_id="profile-project"\n'
    )
    monkeypatch.setenv("EVREN_PLATFORM_API_KEY", SECRET)
    monkeypatch.setenv("EVREN_LLM_API_KEY", OTHER)
    state = tmp_path / "state"
    api.initialize_state(state_dir=state)
    return config, state


def routes():
    def reply(value):
        return Reply(body=json.dumps(value).encode())

    return {
        "/api/v1/auth/me": reply(
            {"success": True, "data": {"id": "me", "email": "private@example.test"}}
        ),
        "/api/v1/organizations": reply({"items": [{"id": "org"}], "total": 2}),
        "/api/v1/projects": reply([{"id": "listed", "org_id": "org"}]),
        "/api/v1/projects/profile-project": reply({"id": "profile-project", "org_id": None}),
        "/api/v1/projects/explicit": Reply(status=404),
    }


def bind(monkeypatch, server):
    monkeypatch.setattr(
        platform_context,
        "HttpSession",
        lambda: HttpSession(transport_factory=lambda: HttpxTransport(transport=server.transport())),
    )


def command(server, certificates, config, state, *options):
    return [
        sys.executable,
        "-m",
        "tests.fixtures.discovery_cli",
        str(server.port),
        str(certificates[0]),
        "context",
        "discover",
        "--service",
        "evren-platform",
        "--config",
        str(config),
        "--state-dir",
        str(state),
        *options,
    ]


def child(server, certificates, config, state, *options):
    env = dict(os.environ)
    env.update({"LC_ALL": "C", "PYTHONIOENCODING": "ascii", "PYTHONUTF8": "0"})
    return subprocess.run(
        command(server, certificates, config, state, *options),
        cwd=ROOT,
        env=env,
        capture_output=True,
        timeout=8,
    )


@pytest.mark.parametrize("output", ["json", "ndjson"])
@pytest.mark.parametrize("project", [None, "explicit"])
def test_platform_api_and_real_cli_share_typed_result_and_one_service_secret(
    files, certificates, monkeypatch, output, project
):
    config, state = files
    calls = []
    read = EnvSecretReader.read

    def counted(reader, reference):
        calls.append(reference.service_id)
        return read(reader, reference)

    monkeypatch.setattr(EnvSecretReader, "read", counted)
    with TlsServer(certificates, routes()) as server:
        bind(monkeypatch, server)
        expected = api.discover_context(
            "evren-platform", config=config, state_dir=state, project=project
        )
        actual = child(
            server,
            certificates,
            config,
            state,
            "--output=" + output,
            *(["--project", project] if project else []),
        )
    assert isinstance(expected.data, PlatformContextDiscovery)
    assert calls == ["evren-platform"]
    assert actual.returncode == 0, actual.stderr
    assert actual.stderr == b""
    assert actual.stdout.count(b"\n") == 1
    wire = json.loads(actual.stdout)
    if output == "ndjson":
        assert wire["event"] == "result"
        assert wire["sequence"] == 1
        wire = wire["payload"]
    assert wire["status"] == "completed"
    assert wire["operation_id"] is None
    assert wire["warnings"] == ["context_not_verified"]
    for name in (
        "service_id",
        "selected",
        "provider",
        "reported_identity",
        "organizations",
        "projects",
        "list_completeness",
        "binding",
        "profile_preference",
        "reasons",
    ):
        assert wire["data"][name] == expected.data.model_dump(mode="json")[name]
    assert wire["data"]["profile_preference"]["project_id"] == "profile-project"
    assert wire["data"]["selected"]["project_id"] == (project or "profile-project")
    assert wire["data"]["validation"] == "unverified"
    assert len(server.requests) == 8
    assert [r.header("X-API-Key") for r in server.requests] == [SECRET] * 8
    assert all(r.header("Authorization") is None for r in server.requests)
    for private in (SECRET, OTHER, "private@example.test", "EVREN_PLATFORM_API_KEY"):
        assert private.encode() not in actual.stdout


def test_platform_text_is_utf8_and_explains_preferences_and_unverified_ids(files, certificates):
    config, state = files
    with TlsServer(certificates, routes()) as server:
        result = child(server, certificates, config, state)
    assert result.returncode == 0, result.stderr
    text = result.stdout.decode("utf-8", "strict")
    assert "Bildirilen auth/me ID: me" in text
    assert "Seçilen proje: profile-project (observed)" in text
    assert "Liste tamlığı: eksik" in text
    assert "doğrulanmadı" in text
    assert "yürütme izni vermez" in text
    assert "kişiye bağlanabilir" in text
    assert "private@example.test" not in text


def test_platform_default_state_and_profile_snapshot_are_loaded_once(
    files, certificates, monkeypatch
):
    config, explicit = files
    default = api.initialize_state().data
    loads = []
    load = api._configuration

    def once(path):
        loads.append(path)
        return load(path)

    monkeypatch.setattr(api, "_configuration", once)
    with TlsServer(certificates, routes()) as server:
        bind(monkeypatch, server)
        one = api.discover_context("evren-platform", config=config).data
        two = api.discover_context("evren-platform", config=config, state_dir=explicit).data
    assert loads == [config, config]
    assert one.binding.store_id == default.store_id
    assert two.binding.store_id != default.store_id


@pytest.mark.parametrize(
    "case,code,exit_code",
    [
        ("missing", "state_invalid", 2),
        ("denied", "remote_access_denied", 3),
        ("malformed", "invalid_response", 1),
    ],
)
def test_platform_errors_are_controlled_machine_envelopes(
    files, certificates, case, code, exit_code
):
    config, state = files
    selected = routes()
    if case == "missing":
        state = state / "absent"
    elif case == "denied":
        selected["/api/v1/auth/me"] = Reply(status=403)
    else:
        selected["/api/v1/auth/me"] = Reply(body=b'{"success":1,"data":{"id":"me"}}')
    with TlsServer(certificates, selected) as server:
        result = child(server, certificates, config, state, "--output=ndjson")
    assert result.returncode == exit_code
    assert result.stdout == b""
    assert json.loads(result.stderr)["code"] == code
    assert b"Traceback" not in result.stderr
    assert SECRET.encode() not in result.stderr
    assert len(server.requests) == (0 if case == "missing" else 1)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal contract")
def test_platform_sigint_closes_request_without_remote_cancellation_claim(files, certificates):
    config, state = files
    selected = routes()
    selected["/api/v1/auth/me"] = Reply(body=b"{}", header_delay=2)
    with TlsServer(certificates, selected) as server:
        process = subprocess.Popen(
            command(server, certificates, config, state, "--output=json"),
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            end = time.monotonic() + 4
            while not server.requests and time.monotonic() < end:
                time.sleep(0.01)
            assert server.requests
            process.send_signal(signal.SIGINT)
            stdout, stderr = process.communicate(timeout=4)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    assert process.returncode == 6
    assert stdout == b""
    assert json.loads(stderr)["code"] == "request_cancelled"
    assert len(server.requests) == 1


def test_platform_closed_stdout_is_local_output_closed_after_four_reads(files, certificates):
    config, state = files
    with TlsServer(certificates, routes()) as server:
        process = subprocess.Popen(
            command(server, certificates, config, state, "--output=json"),
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert process.stdout is not None
        process.stdout.close()
        try:
            assert process.wait(timeout=6) == 6
            stderr = process.stderr.read()
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stderr.close()
    assert json.loads(stderr)["code"] == "output_closed"
    assert len(server.requests) == 4
