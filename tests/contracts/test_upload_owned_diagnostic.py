"""No live account: the diagnostic exposes field types and performs at most two GETs."""

import asyncio
import json
import runpy
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
    PLAN,
    SCOPE,
    SECRET,
    dataset,
    encoded,
    located,
)
from yorunge.application import platform_upload_codec as codec
from yorunge.application.http_transport import HttpCredential
from yorunge.application.upload_budget import UploadBudget
from yorunge.domain.credentials import normalize_target
from yorunge.domain.errors import YorungeError

HELPER = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / "scripts/upload_owned_diagnostic.py")
)


@pytest.mark.parametrize(
    "case", ["valid", "missing", "bad_locator", "wrong_owner", "pii", "secret", "wrong_boolean"]
)
def test_two_get_consumer_diagnostic_has_no_write_or_private_value_output(case):
    selected = located()
    if case == "bad_locator":
        selected["owner_username"] = "../private-locator-canary"
    if case == "wrong_owner":
        selected["owner_id"] = "00000000-0000-4000-8000-000000000099"
    if case == "wrong_boolean":
        selected["contributions_enabled"] = 0
    if case == "pii":
        selected["email"] = "private-person-canary@example.test"
    if case == "secret":
        selected["unused"] = "synthetic-platform-secret"
    body = encoded([] if case == "missing" else [selected])
    calls = []

    class Response:
        status_code = 200

        def __init__(self, data, reservation):
            self.data, self.reservation = data, reservation

        async def chunks(self):
            self.reservation.response(len(self.data))
            yield self.data

    class Client:
        @asynccontextmanager
        async def open_budgeted(self, request, reservation, *, deadline):
            calls.append(request)
            reservation.require(
                budget, "read", request_bytes=0, upload_bytes=0, response_bytes=request.max_bytes
            )
            reservation.begin()
            reservation.attempt()
            yield Response(body if len(calls) == 1 else encoded(dataset()), reservation)

    budget = UploadBudget(PLAN.request_limits, end=time.monotonic() + 30, read_only=True)
    key = HttpCredential(
        "X-API-Key",
        SECRET,
        target=normalize_target("https://api.ssyz.org.tr/api/v1"),
        service_id="evren-platform",
    )
    report = {"requests": [], "outcome": "incomplete"}
    action = HELPER["inspect"](
        Client(),
        budget,
        key,
        SimpleNamespace(plan=SimpleNamespace(scope=SCOPE, parameters=PARAMETERS)),
        codec.created(encoded(dataset()), SCOPE, PARAMETERS, SECRET),
        report,
    )
    if case in ("valid", "pii"):
        asyncio.run(action)
        assert report["consumer_accepted"] is True
        assert len(calls) == 2
    else:
        with pytest.raises(YorungeError) as raised:
            asyncio.run(action)
        assert raised.value.code == "invalid_response"
        assert len(calls) == 1
    if case == "wrong_owner":
        assert report["owned_shape"]["matches_create"]["owner_id"] is False
    if case == "wrong_boolean":
        assert report["owned_shape"]["matches_create"]["contributions_enabled"] is False
    for request in calls:
        assert request.method == "GET"
        assert request.read_only is True
        assert request.max_bytes == 1_048_576
    assert budget.snapshot().effect_attempts == 0
    assert budget.snapshot().response_pending == 0
    assert DATASET not in json.dumps(report)
    assert "private-person-canary" not in json.dumps(report)
    assert "private-locator-canary" not in json.dumps(report)
    assert "synthetic-platform-secret" not in json.dumps(report)


@pytest.mark.parametrize("case", ["missing_profile", "wrong_profiles_type"])
def test_diagnostic_cli_hides_private_preflight_lookup_failures(tmp_path, case):
    root = tmp_path.resolve()
    config = root / "config.toml"
    profile = "private-profile-lookup-canary"
    spec = f'active_profile = "{profile}"\n'
    if case == "missing_profile":
        spec += '[profiles.other]\nplatform_url = "https://api.ssyz.org.tr/api/v1"\n'
    else:
        spec += 'profiles = "private-profiles-type-canary"\n'
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


@pytest.mark.parametrize("leaf", ["started.json", ".."])
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
