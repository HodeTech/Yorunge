"""No live account: field types, exact locators and at most three research GETs."""

import asyncio
import json
import runpy
import socket
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.contracts.test_platform_upload_codec import (
    DATASET,
    PARAMETERS,
    SCOPE,
    SECRET,
    dataset,
    encoded,
    located,
)
from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from yorunge.adapters.http_session import HttpSession
from yorunge.adapters.http_transport import HttpxTransport
from yorunge.application import platform_upload_codec as codec
from yorunge.application.http_transport import HttpCredential, HttpStatusFailure
from yorunge.domain.credentials import normalize_target
from yorunge.domain.errors import YorungeError

HELPER = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / "scripts/upload_owned_diagnostic.py")
)
CONNECT, CONNECT_EX, GETADDRINFO = (
    socket.socket.connect,
    socket.socket.connect_ex,
    socket.getaddrinfo,
)


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "missing",
        "bad_locator",
        "wrong_owner",
        "pii",
        "secret",
        "wrong_boolean",
        "missing_metadata",
        "query_rejected",
        "http_405",
        "malformed_json",
    ],
)
def test_bounded_consumer_diagnostic_has_no_write_or_private_value_output(case):
    selected = located()
    if case == "bad_locator":
        selected["owner_username"] = "../private-locator-canary"
    if case == "wrong_owner":
        selected["owner_id"] = "00000000-0000-4000-8000-000000000099"
    if case == "wrong_boolean":
        selected["contributions_enabled"] = 0
    if case == "missing_metadata":
        selected.pop("contributions_enabled")
    if case == "pii":
        selected["email"] = "private-person-canary@example.test"
    if case == "secret":
        selected["unused"] = "synthetic-platform-secret"
    body = encoded([] if case == "missing" else [selected])
    if case == "malformed_json":
        body = b"{"
    calls = []

    class Response:
        status_code = 200

        def __init__(self, data):
            self.data = data

        async def chunks(self):
            yield self.data

    class Client:
        @asynccontextmanager
        async def open(self, request, *, deadline):
            calls.append(request)
            if case == "query_rejected" and len(calls) == 1:
                raise HttpStatusFailure(422)
            if case == "http_405":
                raise HttpStatusFailure(405)
            yield Response(body if request.endpoint == "datasets" else encoded(dataset()))

    key = HttpCredential(
        "X-API-Key",
        SECRET,
        target=normalize_target("https://api.ssyz.org.tr/api/v1"),
        service_id="evren-platform",
    )
    report = {"requests": [], "outcome": "incomplete"}
    action = HELPER["inspect"](
        Client(),
        key,
        SimpleNamespace(plan=SimpleNamespace(scope=SCOPE, parameters=PARAMETERS)),
        codec.created(encoded(dataset()), SCOPE, PARAMETERS, SECRET),
        report,
        end=time.monotonic() + 30,
    )
    if case in ("valid", "pii", "missing_metadata", "query_rejected"):
        asyncio.run(action)
        assert report["consumer_accepted"] is True
        assert report["detail_matches_create"] is True
        assert len(calls) == (3 if case == "query_rejected" else 2)
    else:
        with pytest.raises(YorungeError) as raised:
            asyncio.run(action)
        assert raised.value.code == ("remote_failed" if case == "http_405" else "invalid_response")
        assert len(calls) == 1
    if case == "http_405":
        assert report["requests"][0]["status"] == 405
    if case == "malformed_json":
        assert report["stage"] == "owned_shape"
        assert "owned_shape" not in report
    if case == "query_rejected":
        assert report["requests"][0]["status"] == 422
        assert report["requests"][1]["page_size"] == 5
    if case == "missing_metadata":
        assert report["owned_consumer_accepted"] is True
        assert report["owned_shape"]["selected_fields"]["contributions_enabled"] == "missing"
    if case == "wrong_owner":
        assert report["owned_shape"]["matches_create"]["owner_id"] is False
    if case == "wrong_boolean":
        assert report["owned_shape"]["matches_create"]["contributions_enabled"] is False
    for request in calls:
        assert request.method == "GET"
        assert request.read_only is True
        assert request.max_bytes == 1_048_576
        assert request.upload_endpoint is None
    assert DATASET not in json.dumps(report)
    assert "private-person-canary" not in json.dumps(report)
    assert "private-locator-canary" not in json.dumps(report)
    assert "synthetic-platform-secret" not in json.dumps(report)


def test_owned_diagnostic_uses_real_read_session_and_preserves_rejected_http_status(tmp_path):
    row = located()
    row.pop("contributions_enabled")
    routes = {
        "/api/v1/datasets?page=1&page_size=20&scope=owned": Reply(status=422, body=b"{}"),
        "/api/v1/datasets?page=1&page_size=5&scope=owned": Reply(body=encoded([row])),
        "/api/v1/datasets/sample-user/sample-dataset": Reply(body=encoded(dataset())),
    }
    key = HttpCredential("X-API-Key", SECRET, target=HELPER["TARGET"], service_id="evren-platform")
    expected = codec.created(encoded(dataset()), SCOPE, PARAMETERS, SECRET)
    view = SimpleNamespace(plan=SimpleNamespace(scope=SCOPE, parameters=PARAMETERS))
    report = {"requests": [], "outcome": "incomplete"}
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        with TlsServer(certificate(tmp_path), routes) as server:
            with HttpSession(
                transport_factory=lambda: HttpxTransport(transport=server.transport())
            ) as session:
                session.call(
                    lambda client: HELPER["inspect"](
                        client, key, view, expected, report, end=time.monotonic() + 5
                    )
                )
    assert [row["status"] for row in report["requests"]] == [422, 200, 200]
    assert report["owned_consumer_accepted"] is True
    assert report["detail_matches_create"] is True
    assert report["detail_shape"]["matches_create"] == dict.fromkeys(HELPER["FIELDS"][:7], True)
    assert report["consumer_accepted"] is True
    assert len(server.requests) == 3
    assert all(record.method == "GET" for record in server.requests)
    assert DATASET not in json.dumps(report)
    assert SECRET.reveal() not in json.dumps(report)


@pytest.mark.parametrize(
    "case", ["missing_profile", "wrong_profiles_type", "invalid_profile_index"]
)
def test_diagnostic_cli_hides_private_preflight_lookup_failures(tmp_path, case):
    root = tmp_path.resolve()
    config = root / "config.toml"
    profile = "private-profile-lookup-canary"
    spec = f'active_profile = "{profile}"\n'
    if case == "missing_profile":
        spec += '[profiles.other]\nplatform_url = "https://api.ssyz.org.tr/api/v1"\n'
    elif case == "wrong_profiles_type":
        spec += 'profiles = "private-profiles-type-canary"\n'
    else:
        spec = "active_profile = 0\nprofiles = []\n"
    config.write_text(spec)
    config.chmod(0o600)
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(Path(HELPER["__file__"])),
            "--config",
            str(config),
            "--credentials",
            str(root / "absent-credentials.json"),
            "--pilot",
            str(root / "absent-pilot"),
            "--output",
            str(root / "new/receipt.json"),
            "--accept-read-diagnostic",
        ],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 1
    assert result.stdout == b""
    assert b"Traceback" not in result.stderr
    assert b"private-profile" not in result.stderr
    assert b"Read diagnostic stopped" in result.stderr
    assert not (root / "new").exists()


@pytest.mark.parametrize("leaf", ["started.json", "STARTED.JSON", ".."])
def test_diagnostic_rejects_reserved_output_before_private_input_or_network(
    tmp_path, monkeypatch, leaf
):
    namespace = HELPER["run"].__globals__
    monkeypatch.setitem(namespace, "sys", SimpleNamespace(flags=SimpleNamespace(isolated=True)))

    def forbidden(*args):
        raise AssertionError("private inputs must not be opened for an invalid output")

    monkeypatch.setitem(namespace["BASE"], "credential", forbidden)
    args = SimpleNamespace(accept_read_diagnostic=True, output=tmp_path / "new" / leaf)
    with pytest.raises(ValueError, match="output"):
        HELPER["run"](args)
    assert not (tmp_path / "new").exists()


@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit, asyncio.CancelledError])
def test_private_diagnostic_cli_stops_without_revealing_interrupt_value(
    tmp_path, monkeypatch, capsys, exception
):
    arguments = ["diagnostic"]
    for name in ("config", "credentials", "pilot", "output"):
        arguments.extend(("--" + name, str(tmp_path / name)))
    arguments.append("--accept-read-diagnostic")
    monkeypatch.setattr(sys, "argv", arguments)

    def interrupted(args):
        raise exception("private-interrupt-canary")

    monkeypatch.setitem(HELPER["main"].__globals__, "run", interrupted)
    assert HELPER["main"]() == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "Read diagnostic stopped; preserve its safe receipt.\n"
    assert "private-interrupt-canary" not in output.err
