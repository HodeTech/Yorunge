"""Offline safety oracles; no real credentials or network are read."""

import asyncio
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

from yorunge.domain.credentials import SecretValue
from yorunge.domain.errors import YorungeError

PATH = Path(__file__).with_name("preflight.py")
SPEC = importlib.util.spec_from_file_location("upload_preflight", PATH)
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)
PROJECT = "00000000-0000-4000-8000-000000000001"
SECRET = "synthetic_key_4fef1284"


class Parts(httpx.AsyncByteStream):
    def __init__(self, body):
        self.body = body

    async def __aiter__(self):
        for offset in range(0, len(self.body), 65_536):
            yield self.body[offset : offset + 65_536]


def streamed(status, *, content=b"", json=None, headers=None):
    body = globals()["json"].dumps(json).encode() if json is not None else content
    return httpx.Response(status, stream=Parts(body), headers=headers)


def survey(handler, *, secret=SECRET):
    budget = probe.BudgetTransport(SecretValue(secret), PROJECT, httpx.MockTransport(handler))
    return probe.survey(SecretValue(secret), PROJECT, budget)


def test_exact_five_gets_no_private_values():
    seen = []

    def handler(request):
        seen.append(request)
        return streamed(
            200, json={"success": True, "data": {"id": PROJECT, "email": "private@example.test"}}
        )

    result = survey(handler)
    assert len(seen) == 5
    assert result["attempts"] == 5
    assert all(request.method == "GET" for request in seen)
    assert all(request.headers["X-API-Key"] == SECRET for request in seen)
    assert all(
        "authorization" not in request.headers and "cookie" not in request.headers
        for request in seen
    )
    assert seen[-1].url.query == b"page=1&page_size=5&scope=owned"
    output = json.dumps(result)
    for value in (SECRET, PROJECT, "private@example.test"):
        assert value not in output
    assert result["authority_verified"] is False
    assert result["pricing_verified"] is False
    assert result["effectful_requests"] == 0


def test_read_retry_single_owner(monkeypatch):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return streamed(503 if calls == 1 else 200, json={"data": []})

    monkeypatch.setattr("yorunge.adapters.http_transport._retry_wait", lambda _: 0)
    result = survey(handler)
    assert result["attempts"] == 6
    assert result["calls"][0]["attempts"] == 2


@pytest.mark.parametrize("status", [401, 403])
def test_denial_stops_first_call(status):
    result = survey(lambda request: streamed(status, content=SECRET.encode()))
    assert result["attempts"] == 1
    assert len(result["calls"]) == 1
    assert SECRET not in json.dumps(result)


@pytest.mark.parametrize("body", [b'{"data":1,"data":2}', b'{"data":NaN}', b"\xff"])
def test_invalid_json_stops_safely(body):
    result = survey(lambda request: streamed(200, content=body))
    assert result["attempts"] == 1
    assert result["error_code"] == "invalid_response"


@pytest.mark.parametrize(
    "raw", [{"data": SECRET}, {"unknown": {SECRET: 1}}, {"data": ["prefix" + SECRET]}]
)
def test_literal_canary_everywhere(raw):
    result = survey(lambda request: streamed(200, json=raw))
    assert result["attempts"] == 1
    assert result["error_code"] == "invalid_response"
    assert SECRET not in json.dumps(result)


def test_short_secret_rule():
    result = survey(lambda request: streamed(200, json={"data": "alpha"}), secret="a")
    assert result["attempts"] == 5


def test_over_response_limit_records_consumption_and_stops():
    result = survey(lambda request: streamed(200, content=b"x" * (probe.LIMIT + 1)))
    assert result["attempts"] == 1
    assert result["consumed_body_bytes"] == probe.LIMIT + 1
    assert result["error_code"] == "invalid_response"


def test_redirect_not_followed():
    result = survey(
        lambda request: streamed(302, headers={"location": "https://elsewhere.invalid/"})
    )
    assert result["attempts"] == 5
    assert all(row["status"] == 302 for row in result["calls"])


@pytest.mark.parametrize(
    "method,url",
    [
        ("POST", "https://api.ssyz.org.tr/api/v1/auth/me"),
        ("GET", "https://api.ssyz.org.tr/api/v1/billing/balance"),
        ("GET", "https://elsewhere.invalid/api/v1/auth/me"),
    ],
)
def test_transport_rejects_unapproved_request(method, url):
    calls = []
    budget = probe.BudgetTransport(
        SecretValue(SECRET), PROJECT, httpx.MockTransport(lambda request: calls.append(request))
    )
    budget.active = url
    request = httpx.Request(method, url, headers={"X-API-Key": SECRET})
    with pytest.raises(YorungeError):
        asyncio.run(budget.handle_async_request(request))
    assert not calls
    assert budget.attempts == 0


def test_expired_total_no_network():
    calls = []
    budget = probe.BudgetTransport(
        SecretValue(SECRET),
        PROJECT,
        httpx.MockTransport(lambda request: calls.append(request)),
        started=0,
    )
    result = probe.survey(SecretValue(SECRET), PROJECT, budget)
    assert result["attempts"] == 0
    assert not calls


def test_existing_output_is_never_overwritten(tmp_path, monkeypatch):
    root = tmp_path / "p02-pilot"
    root.mkdir(mode=0o700)
    (root / "credentials.json").write_text(json.dumps({"PILOT_PLATFORM_KEY": SECRET}))
    (root / "config.toml").write_text(
        '[profiles.pilot]\nplatform_url="https://api.ssyz.org.tr/api/v1"\nplatform_key_env="PILOT_PLATFORM_KEY"\n'
    )
    for name in ("config.toml", "credentials.json"):
        (root / name).chmod(0o600)
    output = root / "receipt.json"
    output.write_bytes(b"preserved")
    monkeypatch.setattr(probe, "PREP", root)
    monkeypatch.setattr(probe, "ROOT", Path.cwd())
    monkeypatch.setattr(probe, "OUTPUT", output)

    def forbidden_transport(*args, **kwargs):
        raise AssertionError("offline test must never construct a real network transport")

    monkeypatch.setattr(probe.httpx, "AsyncHTTPTransport", forbidden_transport)
    with pytest.raises(FileExistsError):
        probe.execute(PROJECT)
    assert output.read_bytes() == b"preserved"


def test_private_input_rejects_symlink(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    target = root / "real"
    target.write_text("secret")
    target.chmod(0o600)
    link = root / "input"
    link.symlink_to(target)
    with pytest.raises(OSError):
        probe.private_bytes(link)
