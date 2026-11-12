"""Real TLS and SQLite Platform observations without live account or permission claims."""

import json
import socket
import sqlite3
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta

import pytest

from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from yorunge import api
from yorunge.adapters.capability_cache import SystemClock
from yorunge.adapters.context_state import StateDiscovery
from yorunge.adapters.http_session import HttpSession
from yorunge.adapters.http_transport import HttpxTransport
from yorunge.adapters.platform_context import PlatformReader
from yorunge.adapters.state import DB_NAME
from yorunge.application.context_discovery import ObservationClock
from yorunge.application.platform_discovery import discover_platform
from yorunge.domain.credentials import SecretValue
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Context, Profile

CONNECT, CONNECT_EX, GETADDRINFO = (
    socket.socket.connect,
    socket.socket.connect_ex,
    socket.getaddrinfo,
)
SECRET = "synthetic-platform-secret-308174"
ME = {"success": True, "data": {"id": "me-1", "email": "private@example.test", "role": "admin"}}
ORGS = {"items": [{"id": "org-1", "owner_id": "owner-private"}], "total": 1}


def body(value):
    return Reply(body=json.dumps(value).encode())


def routes(projects=None, detail=None):
    return {
        "/api/v1/auth/me": body(ME),
        "/api/v1/organizations": body(ORGS),
        "/api/v1/projects": body([] if projects is None else projects),
        "/api/v1/projects/selected": body(
            {"id": "selected", "org_id": None} if detail is None else detail
        ),
    }


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(tmp_path_factory.mktemp("platform-tls"))


@pytest.fixture(autouse=True)
def actual_loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


class Secrets:
    def __init__(self, value=SECRET):
        self.value, self.calls = value, 0

    def read(self, reference):
        assert reference.service_id == "evren-platform"
        assert reference.name == "EVREN_PLATFORM_API_KEY"
        self.calls += 1
        return SecretValue(self.value)


def state(root, clock, secrets=None, *, project=None, override=None):
    profile = Profile(
        platform_url="https://localhost/api/v1",
        platform_key_env="EVREN_PLATFORM_API_KEY",
        account_id="preferred-account",
        project_id=project,
    )
    context = Context(
        profile="work",
        platform_url=profile.platform_url,
        llm_url=profile.llm_url,
        account_id=profile.account_id,
        project_id=override or project,
    )
    return StateDiscovery(
        root, lambda: (context, profile), secrets or Secrets(), clock, service_id="evren-platform"
    )


def run(root, server, *, clock=None, secrets=None, project=None, override=None, timeout=4):
    clock = clock or ObservationClock(SystemClock())
    session = HttpSession(transport_factory=lambda: HttpxTransport(transport=server.transport()))
    return discover_platform(
        state(root, clock, secrets, project=project, override=override),
        PlatformReader(clock, session=session),
        clock,
        deadline=clock.monotonic() + timeout,
    )


@pytest.mark.parametrize(
    "project,override", [(None, None), ("selected", None), ("original", "selected")]
)
def test_real_platform_request_order_selection_snapshot_and_private_projection(
    tmp_path, certificates, project, override
):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    secrets = Secrets()
    with TlsServer(
        certificates, routes(projects=[{"id": "selected", "org_id": "other-parent"}])
    ) as server:
        result = run(root, server, secrets=secrets, project=project, override=override)
    selected = override or project
    assert [r.path for r in server.requests] == [
        "/api/v1/auth/me",
        "/api/v1/organizations",
        "/api/v1/projects",
    ] + (["/api/v1/projects/selected"] if selected else [])
    assert secrets.calls == 1
    for record in server.requests:
        assert record.method == "GET"
        assert record.header("X-API-Key") == SECRET
        assert record.header("Authorization") is None
        assert record.header("Cookie") is None
    assert result.profile_preference.project_id == project
    assert result.selected.project_id == selected
    assert result.selected.account_id == "preferred-account"
    assert result.reported_identity.me_id == "me-1"
    assert result.provider.principal_id is None
    assert result.provider.identity_status == "unverified"
    assert result.authorization_scope is None
    assert result.validation == "unverified"
    assert result.list_completeness.organizations == "unknown"
    assert result.projects.items[0].organization_id == "other-parent"
    assert result.projects.selection.state == ("observed" if selected else "not_selected")
    if selected:
        assert result.projects.selection.project.organization_id is None
    assert result.reasons == tuple(
        sorted(
            (
                "account_semantics_unknown",
                "authorization_not_verified",
                "identity_not_verified",
                "list_completeness_unknown",
                "profile_scope_unknown",
                "remote_snapshot_not_guaranteed",
            )
            + (() if selected else ("project_selection_required",))
        )
    )
    public = result.model_dump_json()
    for private in (
        SECRET,
        "private@example.test",
        "owner-private",
        '"admin"',
        "EVREN_PLATFORM_API_KEY",
    ):
        assert private not in public
        if private != "EVREN_PLATFORM_API_KEY":
            assert private.encode() not in (root / DB_NAME).read_bytes()


def test_detail_404_is_unverified_observation_and_does_not_empty_the_list(tmp_path, certificates):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    selected_routes = routes(projects=[{"id": "listed"}])
    selected_routes["/api/v1/projects/selected"] = Reply(status=404)
    with TlsServer(certificates, selected_routes) as server:
        result = run(root, server, project="selected")
    assert result.projects.selection.state == "not_found"
    assert result.projects.selection.project is None
    assert [v.id for v in result.projects.items] == ["listed"]
    assert result.observations[-1].outcome == "not_found"
    assert "selected_project_not_found" in result.reasons


@pytest.mark.parametrize(
    "status,expected",
    [
        (401, "remote_access_denied"),
        (403, "remote_access_denied"),
        (404, "invalid_response"),
        (429, "remote_rate_limited"),
    ],
)
def test_endpoint_failures_are_not_blank_success(tmp_path, certificates, status, expected):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    selected_routes = routes()
    selected_routes["/api/v1/organizations"] = Reply(status=status)
    with TlsServer(certificates, selected_routes) as server:
        with pytest.raises(YorungeError) as failure:
            run(root, server)
    assert failure.value.code == expected
    assert len(server.requests) == (3 if status == 429 else 2)


@pytest.mark.parametrize("change", ["credential", "reset", "generation"])
@pytest.mark.parametrize("endpoint", ["auth/me", "projects"])
def test_independent_process_changes_reject_final_snapshot_without_network_lock(
    tmp_path, certificates, change, endpoint
):
    root, config = tmp_path / "state", tmp_path / "context.toml"
    api.initialize_state(state_dir=root)
    config.write_text(
        'schema_version=1\nactive_profile="work"\n[profiles.work]\nplatform_url="https://localhost/api/v1"\nplatform_key_env="EVREN_PLATFORM_API_KEY"\n'
    )
    script = """
import os,sys
from pathlib import Path
from yorunge import api
from yorunge.adapters.state import open_store
root,config,change=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3]
if change=='credential':
    os.environ['EVREN_PLATFORM_API_KEY']='synthetic-independent-rotation'
    api.observe_credential('evren-platform',config=config,state_dir=root)
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
            [sys.executable, "-c", script, str(root), str(config), change],
            capture_output=True,
            text=True,
            timeout=4,
        )
        completed.append(child)
        return body(ME if endpoint == "auth/me" else [])

    selected_routes = routes()
    selected_routes["/api/v1/" + endpoint] = mutate
    with TlsServer(certificates, selected_routes) as server:
        with pytest.raises(YorungeError) as failure:
            run(root, server)
    assert [c.returncode for c in completed] == [0], [c.stderr for c in completed]
    assert failure.value.code == "state_changed"
    assert len(server.requests) == 3


def test_platform_clock_rollback_is_persistently_fenced(tmp_path, certificates):
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
        return body([])

    selected_routes = routes()
    selected_routes["/api/v1/projects"] = rollback
    with TlsServer(certificates, selected_routes) as server:
        with pytest.raises(YorungeError) as failure:
            run(root, server, clock=clock)
    assert failure.value.code == "state_changed"
    with sqlite3.connect(root / DB_NAME) as connection:
        assert connection.execute(
            "SELECT clock_generation,anomaly_active FROM cache_clock"
        ).fetchone() == (2, 1)


def test_platform_no_init_and_no_secret_read_for_absent_store(tmp_path, certificates):
    root = tmp_path / "absent"
    secrets = Secrets()
    with TlsServer(certificates, routes()) as server:
        with pytest.raises(YorungeError) as failure:
            run(root, server, secrets=secrets)
    assert failure.value.code == "state_invalid"
    assert secrets.calls == 0
    assert server.requests == []
    assert not root.exists()


class RecordingTransport(HttpxTransport):
    """Notes the deadline every read of one discovery is given, and changes nothing else."""

    deadlines: list[float]

    def open(self, request, *, deadline):
        self.deadlines.append(deadline)
        return super().open(request, deadline=deadline)


def test_every_read_of_one_discovery_is_given_the_one_absolute_deadline(
    tmp_path, certificates, monkeypatch
):
    """The deadline is shared by the reads: not a fresh budget per read (no wall-clock margin)."""
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    deadlines: list[float] = []
    # the class declares ``deadlines`` as an annotation only: there is no attribute to restore
    monkeypatch.setattr(RecordingTransport, "deadlines", deadlines, raising=False)
    clock = ObservationClock(SystemClock())
    with TlsServer(certificates, routes()) as server:
        session = HttpSession(
            transport_factory=lambda: RecordingTransport(transport=server.transport())
        )
        discover_platform(
            state(root, clock, project="selected"),
            PlatformReader(clock, session=session),
            clock,
            deadline=clock.monotonic() + 30,
        )
    assert len(deadlines) == 4  # me, organizations, projects, the selected project
    assert len(set(deadlines)) == 1, deadlines


def test_a_slow_second_read_ends_at_the_shared_deadline_not_at_its_own_reply(
    tmp_path, certificates
):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    selected_routes = routes()
    selected_routes["/api/v1/organizations"] = Reply(
        body=b'{"items":[],"total":0}', header_delay=10.0
    )
    with TlsServer(certificates, selected_routes) as server:
        started = time.monotonic()
        with pytest.raises(YorungeError) as failure:
            run(root, server, timeout=2.0)
        elapsed = time.monotonic() - started
        # The server records a request before it waits to answer it: this only waits (bounded, by
        # an event) for its thread to have been scheduled, whatever the machine's load.
        assert server.wait_for_requests(2, timeout=10)
    assert failure.value.code == "transport_timeout"
    assert elapsed < 4.0  # the reply was due after ten seconds: the deadline ended the read
    assert [request.path for request in server.requests] == [
        "/api/v1/auth/me",
        "/api/v1/organizations",
    ]


@pytest.mark.parametrize(
    "case", ["metadata-secret", "detail-id", "logical-failure", "project-envelope", "oversize"]
)
def test_platform_raw_failures_reject_at_real_http_boundary(tmp_path, certificates, case):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    selected_routes = routes()
    if case == "metadata-secret":
        selected_routes["/api/v1/auth/me"] = body(
            {"success": True, "data": {"id": "me-1", "unused": {"nested": SECRET}}}
        )
    elif case == "detail-id":
        selected_routes["/api/v1/projects/selected"] = body({"id": "another"})
    elif case == "logical-failure":
        selected_routes["/api/v1/organizations"] = body({"success": False, "items": [], "total": 0})
    elif case == "project-envelope":
        selected_routes["/api/v1/projects"] = body({"items": []})
    else:
        selected_routes["/api/v1/projects"] = Reply(body=b" " * (1_048_576 + 1))
    with TlsServer(certificates, selected_routes) as server:
        with pytest.raises(YorungeError) as failure:
            run(root, server, project="selected")
    assert failure.value.code == "invalid_response"
    assert SECRET not in str(failure.value.envelope())


def test_platform_session_cleanup_precedes_final_gate_and_cookies_never_replay(
    tmp_path, certificates
):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    clock = ObservationClock(SystemClock())
    selected_routes = routes()
    selected_routes["/api/v1/auth/me"] = Reply(
        body=json.dumps(ME).encode(), headers=(("Set-Cookie", "session=private; Path=/"),)
    )
    session = None
    inner = state(root, clock)

    class Gate:
        checked = False

        def capture(self, *, deadline):
            return inner.capture(deadline=deadline)

        def finish(self, snapshot, *, deadline):
            assert session._closed is True
            assert session._runner is None
            self.checked = True
            return inner.finish(snapshot, deadline=deadline)

    gate = Gate()
    with TlsServer(certificates, selected_routes) as server:
        session = HttpSession(
            transport_factory=lambda: HttpxTransport(transport=server.transport())
        )
        result = discover_platform(
            gate, PlatformReader(clock, session=session), clock, deadline=time.monotonic() + 4
        )
    assert result.validation == "unverified"
    assert gate.checked is True
    assert [r.header("Cookie") for r in server.requests] == [None, None, None]


def test_short_platform_secret_accepts_unrelated_provider_values(tmp_path, certificates):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    with TlsServer(certificates, routes()) as server:
        result = run(root, server, secrets=Secrets("a"))
    assert result.reported_identity.me_id == "me-1"
