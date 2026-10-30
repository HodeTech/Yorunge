"""Real TLS/SQLite discovery, bounded raw data and independent-process authority races."""

import asyncio
import socket
import sqlite3
import subprocess
import sys
import time
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from yorunge import api
from yorunge.adapters.capability_cache import SystemClock
from yorunge.adapters.context_state import StateDiscovery
from yorunge.adapters.http_session import HttpSession
from yorunge.adapters.http_transport import HttpxTransport
from yorunge.adapters.llm_context import LlmTermsReader
from yorunge.adapters.state import DB_NAME, open_existing_store, open_store
from yorunge.application.context_discovery import ObservationClock, discover_context
from yorunge.domain.credentials import EnvReference, ResolvedCredential, SecretValue
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Context, Profile

CONNECT = socket.socket.connect
CONNECT_EX = socket.socket.connect_ex
GETADDRINFO = socket.getaddrinfo
SECRET = "synthetic-discovery-secret-3185029"
GOOD = b'{"accepted":true,"current_version":2,"is_material":true,"doc_path":"terms/v2.md"}'


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(tmp_path_factory.mktemp("discovery-tls"))


@pytest.fixture(autouse=True)
def actual_loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


class Secrets:
    def __init__(self, value=SECRET):
        self.value, self.calls = value, 0

    def read(self, reference):
        assert reference.service_id == "evren-llm"
        assert reference.name == "EVREN_LLM_API_KEY"
        self.calls += 1
        return SecretValue(self.value)


def state(root, clock, secrets=None, *, preferences=True):
    profile = Profile(
        llm_url="https://localhost/v1",
        llm_key_env="EVREN_LLM_API_KEY",
        account_id="platform-account" if preferences else None,
        project_id="platform-project" if preferences else None,
    )
    context = Context(
        profile="work",
        account_id=profile.account_id,
        project_id=profile.project_id,
        platform_url=profile.platform_url,
        llm_url=profile.llm_url,
    )
    return StateDiscovery(root, lambda: (context, profile), secrets or Secrets(), clock)


def run(root, server, *, clock=None, secrets=None, timeout=4, preferences=True):
    clock = clock or ObservationClock(SystemClock())
    session = HttpSession(transport_factory=lambda: HttpxTransport(transport=server.transport()))
    return discover_context(
        state(root, clock, secrets, preferences=preferences),
        LlmTermsReader(clock, session=session),
        clock,
        deadline=clock.monotonic() + timeout,
    )


def test_real_terms_discovery_keeps_platform_preferences_separate_and_bounds_authority(
    tmp_path, certificates
):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    secrets = Secrets()
    with TlsServer(certificates, {"/v1/terms/status": Reply(body=GOOD)}) as server:
        result = run(root, server, secrets=secrets)
    assert len(server.requests) == 1
    received = server.requests[0]
    assert received.method == "GET"
    assert received.path == "/v1/terms/status"
    assert received.header("Authorization") == "Bearer " + SECRET
    assert received.header("X-API-Key") is None
    assert received.header("Cookie") is None
    assert secrets.calls == 1
    assert result.profile_preference.project_id == "platform-project"
    assert result.profile_preference.service_scope == "unknown"
    assert result.selected.project_id is None
    assert result.selected.account_id is None
    assert result.provider.identity_status == "not_exposed"
    assert result.terms.accepted is True
    assert result.observations[0].authentication == "unknown"
    assert result.validation == "unverified"
    assert result.authorization_scope is None
    assert result.reasons == (
        "authorization_not_verified",
        "identity_not_exposed",
        "profile_scope_unknown",
        "remote_snapshot_not_guaranteed",
    )
    assert result.observed_from <= result.observations[0].started_at
    assert result.observations[0].completed_at <= result.observed_until <= result.validated_at
    public = result.model_dump_json()
    assert SECRET not in public
    assert "terms/v2.md" not in public
    assert "EVREN_LLM_API_KEY" not in public
    assert SECRET.encode() not in (root / DB_NAME).read_bytes()


def test_terms_not_accepted_is_not_an_auth_or_identity_claim(tmp_path, certificates):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    body = GOOD.replace(b'"accepted":true', b'"accepted":false')
    with TlsServer(certificates, {"/v1/terms/status": Reply(body=body)}) as server:
        result = run(root, server, preferences=False)
    assert result.profile_preference.service_scope == "not_applicable"
    assert result.terms.accepted is False
    assert "terms_not_accepted" in result.reasons
    assert "authorization_not_verified" in result.reasons
    assert "identity_not_exposed" in result.reasons


def test_existing_default_state_and_reader_cleanup_before_final_gate(tmp_path, certificates):
    info = api.initialize_state().data
    clock = ObservationClock(SystemClock())
    session = None

    class FinalGate:
        def __init__(self):
            self.inner = state(None, clock)
            self.checked = False

        def capture(self, *, deadline):
            return self.inner.capture(deadline=deadline)

        def finish(self, snapshot, *, deadline):
            assert session._closed is True
            assert session._runner is None
            self.checked = True
            return self.inner.finish(snapshot, deadline=deadline)

    gate = FinalGate()
    with TlsServer(certificates, {"/v1/terms/status": Reply(body=GOOD)}) as server:
        session = HttpSession(
            transport_factory=lambda: HttpxTransport(transport=server.transport())
        )
        result = discover_context(
            gate, LlmTermsReader(clock, session=session), clock, deadline=time.monotonic() + 3
        )
    assert gate.checked is True
    assert result.binding.store_id == info.store_id
    assert (tmp_path / ".local/state/yorunge" / DB_NAME).is_file()


@pytest.mark.parametrize("kind", ["missing", "empty", "old-schema"])
def test_existing_store_gate_never_initializes_or_reads_a_secret(tmp_path, kind):
    root = tmp_path / "existing"
    if kind == "empty":
        root.mkdir(mode=0o700)
    if kind == "old-schema":
        import yorunge.adapters.state_schema as schema

        original = schema.MIGRATIONS
        try:
            schema.MIGRATIONS = original[:5]
            api.initialize_state(state_dir=root)
        finally:
            schema.MIGRATIONS = original
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    secrets = Secrets()
    clock = ObservationClock(SystemClock())
    with pytest.raises(YorungeError) as failure:
        state(root, clock, secrets).capture(deadline=time.monotonic() + 2)
    assert failure.value.code == "state_invalid"
    assert secrets.calls == 0
    after = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert after == before
    assert root.exists() is (kind != "missing")


@pytest.mark.parametrize(
    ("status", "expected", "count"),
    [
        (401, "remote_access_denied", 1),
        (403, "remote_access_denied", 1),
        (404, "invalid_response", 1),
        (429, "remote_rate_limited", 2),
        (503, "remote_failed", 2),
        (302, "remote_failed", 1),
    ],
)
def test_status_mapping_and_retry_budget(tmp_path, certificates, status, expected, count):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    reply = Reply(status=status, body=SECRET.encode())
    with TlsServer(certificates, {"/v1/terms/status": reply}) as server:
        with pytest.raises(YorungeError) as failure:
            run(root, server)
    assert failure.value.code == expected
    assert len(server.requests) == count
    assert SECRET not in str(failure.value.envelope())


@pytest.mark.parametrize(
    "body",
    [
        b"",
        b"[]",
        b'{"success":false}',
        GOOD.replace(b'"accepted":true', b'"accepted":1'),
        GOOD.replace(b'"current_version":2', b'"current_version":true'),
        GOOD.replace(b'"current_version":2', b'"current_version":NaN'),
        GOOD.replace(b'"current_version":2', b'"current_version":-1'),
        GOOD.replace(b'"accepted":true', b'"accepted":true,"accepted":false'),
        GOOD.replace(b'"terms/v2.md"', b'"\\u0000"'),
        GOOD.replace(b'"terms/v2.md"', b'"' + b"x" * 2049 + b'"'),
        GOOD.replace(b'"terms/v2.md"', b'"' + SECRET.encode() + b'"'),
        GOOD[:-1] + b',"extra":true}',
        b"x" * (1_048_576 + 1),
    ],
)
def test_strict_raw_boundary_never_returns_empty_or_reflected_success(tmp_path, certificates, body):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    with TlsServer(certificates, {"/v1/terms/status": Reply(body=body)}) as server:
        with pytest.raises(YorungeError) as failure:
            run(root, server)
    assert failure.value.code == "invalid_response"
    assert len(server.requests) == 1
    assert SECRET not in str(failure.value.envelope())


def test_short_secret_substrings_do_not_reject_valid_provider_metadata(tmp_path, certificates):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    with TlsServer(certificates, {"/v1/terms/status": Reply(body=GOOD)}) as server:
        assert run(root, server, secrets=Secrets("a")).terms.accepted is True


def test_shared_total_deadline_closes_slow_response_without_second_attempt(tmp_path, certificates):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    with TlsServer(
        certificates, {"/v1/terms/status": Reply(body=GOOD, header_delay=0.4)}
    ) as server:
        with pytest.raises(YorungeError) as failure:
            run(root, server, timeout=0.15)
    assert failure.value.code == "transport_timeout"
    assert len(server.requests) == 1


@pytest.mark.parametrize("change", ["credential", "reset", "generation"])
def test_independent_process_changes_reject_old_snapshot_without_holding_store_lock(
    tmp_path, certificates, change
):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    config = tmp_path / "context.toml"
    config.write_text(
        'schema_version=1\nactive_profile="work"\n[profiles.work]\n'
        'llm_url="https://localhost/v1"\nllm_key_env="EVREN_LLM_API_KEY"\n'
    )
    code = """
import os,sys
from pathlib import Path
from yorunge import api
from yorunge.adapters.state import open_store
root,config,change=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3]
if change=='credential':
    os.environ['EVREN_LLM_API_KEY']='synthetic-independent-rotation'
    api.observe_credential('evren-llm',config=config,state_dir=root)
elif change=='reset':
    api.reset_identity(api.preview_identity_reset(state_dir=root).data.digest,state_dir=root)
else:
    with open_store(root) as store:
        store.connection.execute('BEGIN IMMEDIATE')
        store.connection.execute('UPDATE cache_clock SET clock_generation=clock_generation+1')
        store.connection.execute('COMMIT')
"""
    completed = []

    def mutate(record, count):
        child = subprocess.run(
            [sys.executable, "-c", code, str(root), str(config), change],
            capture_output=True,
            text=True,
            timeout=4,
        )
        completed.append(child)
        return Reply(body=GOOD)

    secrets = Secrets()
    with TlsServer(certificates, {"/v1/terms/status": mutate}) as server:
        with pytest.raises(YorungeError) as failure:
            run(root, server, secrets=secrets)
    assert [child.returncode for child in completed] == [0], [c.stderr for c in completed]
    assert failure.value.code == "state_changed"
    assert len(server.requests) == 1
    assert secrets.calls == 1


def test_active_loop_rejects_before_store_or_secret_capture(tmp_path):
    secrets = Secrets()
    clock = ObservationClock(SystemClock())

    async def attempt():
        with pytest.raises(YorungeError) as failure:
            discover_context(
                state(tmp_path / "absent", clock, secrets),
                LlmTermsReader(clock),
                clock,
                deadline=time.monotonic() + 2,
            )
        assert failure.value.code == "invalid_request"

    asyncio.run(attempt())
    assert secrets.calls == 0
    assert not (tmp_path / "absent").exists()


def test_observed_rollback_cannot_disappear_when_utc_recovers_before_final_gate(tmp_path):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)

    class Clock(SystemClock):
        offset = timedelta()

        def now(self):
            return datetime.now(UTC) + self.offset

    source = Clock()
    clock = ObservationClock(source)
    registry = state(root, clock)
    snapshot = registry.capture(deadline=time.monotonic() + 3)
    source.offset = timedelta(hours=1)
    clock.now()
    source.offset = timedelta()
    clock.now()
    source.offset = timedelta(hours=2)
    clock.now()
    with pytest.raises(YorungeError) as failure:
        registry.finish(snapshot, deadline=time.monotonic() + 3)
    assert failure.value.code == "state_changed"
    with sqlite3.connect(root / DB_NAME) as connection:
        assert connection.execute("SELECT clock_generation FROM cache_clock").fetchone() == (2,)


def test_utc_rollback_during_http_rejects_cleanly_and_persists_clock_invalidation(
    tmp_path, certificates
):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)

    class Clock(SystemClock):
        offset = timedelta()

        def now(self):
            return datetime.now(UTC) + self.offset

    source = Clock()
    clock = ObservationClock(source)

    def rollback(record, count):
        source.offset = -timedelta(hours=1)
        return Reply(body=GOOD)

    with TlsServer(certificates, {"/v1/terms/status": rollback}) as server:
        with pytest.raises(YorungeError) as failure:
            run(root, server, clock=clock)
    assert failure.value.code == "state_changed"
    assert len(server.requests) == 1
    with sqlite3.connect(root / DB_NAME) as connection:
        assert connection.execute(
            "SELECT clock_generation,anomaly_active FROM cache_clock"
        ).fetchone() == (2, 1)


def test_missing_database_cannot_be_created_through_existing_only_sqlite_open(tmp_path):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    (root / DB_NAME).unlink()
    with pytest.raises(YorungeError) as failure:
        with open_existing_store(root):
            pytest.fail("missing database must not open")
    assert failure.value.code == "state_invalid"
    assert not (root / DB_NAME).exists()


def test_legacy_open_store_still_explicitly_bootstraps_new_state(tmp_path):
    root = tmp_path / "legacy-open"
    with open_store(root) as store:
        assert store.info.store_schema_version == 6


@pytest.mark.parametrize("name", ["ölçüm-東京", "literal?mode=ro#fragment"])
def test_existing_only_connection_preserves_literal_unicode_and_uri_characters(tmp_path, name):
    root = tmp_path / name
    original = api.initialize_state(state_dir=root).data
    with open_existing_store(root) as store:
        assert store.info == original


def test_wrong_service_snapshot_is_rejected_before_any_http_request(tmp_path, certificates):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    clock = ObservationClock(SystemClock())
    snapshot = state(root, clock).capture(deadline=time.monotonic() + 3)
    wrong = replace(
        snapshot,
        credential=ResolvedCredential(
            reference=EnvReference(service_id="evren-platform", name="EVREN_PLATFORM_API_KEY"),
            target=snapshot.credential.target,
            secret=SecretValue("synthetic-wrong-service-value"),
        ),
    )
    with TlsServer(certificates, {"/v1/terms/status": Reply(body=GOOD)}) as server:
        session = HttpSession(
            transport_factory=lambda: HttpxTransport(transport=server.transport())
        )
        with LlmTermsReader(clock, session=session) as reader:
            with pytest.raises(YorungeError) as failure:
                reader.observe(wrong, deadline=time.monotonic() + 3)
    assert failure.value.code == "invalid_service_target"
    assert server.requests == []
