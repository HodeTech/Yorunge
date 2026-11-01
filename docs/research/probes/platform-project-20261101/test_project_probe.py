"""Only synthetic inputs and MockTransport; never execute against a real account."""

import importlib.util
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path.cwd() / "src"))
spec = importlib.util.spec_from_file_location(
    "project_probe", Path(__file__).with_name("project_probe.py")
)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
SECRET = "synthetic-project-probe-secret-29408"
CHOSEN = "synthetic-selected-project"


def prepare(tmp_path, monkeypatch, *, secret=SECRET, project=CHOSEN):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    values = {
        "credentials.json": json.dumps({"PILOT_PLATFORM_KEY": secret}),
        "config.toml": 'schema_version=1\nactive_profile="pilot"\n[profiles.pilot]\nplatform_url="https://api.ssyz.org.tr/api/v1"\nplatform_key_env="PILOT_PLATFORM_KEY"\n',
        "project-input.json": json.dumps({"project_id": project}),
    }
    for name, value in values.items():
        path = root / name
        path.write_text(value)
        path.chmod(0o600)
    monkeypatch.setattr(p, "PREP", root)
    monkeypatch.setattr(p, "INPUT", root / "project-input.json")
    monkeypatch.setattr(p, "OUTPUT", root / "receipt.json")
    p.helper.api.initialize_state(state_dir=root / "state")
    return root


def wire(monkeypatch, case="good"):
    original = p.helper.CountedWire
    calls = []

    async def response(request):
        calls.append((request.method, request.url.path, request.headers.get("X-API-Key")))
        if request.headers.get("X-API-Key") is None:
            return httpx.Response(401, content=b"not retained")
        path = request.url.path
        if path.endswith("/auth/me"):
            value = {
                "success": True,
                "data": {"id": "synthetic-me", "email": "private@example.test"},
            }
        elif path.endswith("/organizations"):
            value = {"items": [{"id": "synthetic-org"}], "total": 1}
        elif path.endswith("/projects"):
            value = [] if case == "empty" else [{"id": CHOSEN, "org_id": None}]
        else:
            if case == "missing":
                return httpx.Response(404)
            value = {
                "id": "wrong-id" if case == "mismatch" else CHOSEN,
                "org_id": None,
                "name": "private-name",
                "visibility": "private",
            }
            if case == "reflection":
                value["discarded"] = SECRET
        return httpx.Response(
            200,
            stream=httpx.ByteStream(json.dumps(value).encode()),
            headers={"Content-Type": "application/json"},
        )

    class MockWire(original):
        def __init__(self, budget, secret):
            super().__init__(budget, secret, inner=httpx.MockTransport(response))

    monkeypatch.setattr(p.helper, "CountedWire", MockWire)
    return calls


def test_real_public_api_mock_http_selected_path_and_value_free_receipt(
    tmp_path, monkeypatch, capsys
):
    root = prepare(tmp_path, monkeypatch)
    calls = wire(monkeypatch)
    p.execute()
    summary = json.loads(capsys.readouterr().out)
    receipt = json.loads((root / "receipt.json").read_text())
    assert summary["outcome"] == "selected_project_observation_accepted"
    assert all(summary["product_acceptance"].values())
    assert summary["project_count"] == 1
    assert summary["attempts"] == 5
    assert len(calls) == 5
    assert [call[2] for call in calls] == [SECRET] * 4 + [None]
    assert receipt["calls"][-1]["status"] == 401
    for value in (SECRET, CHOSEN, "private-name", "private@example.test"):
        assert value not in (root / "receipt.json").read_text()
        assert value not in json.dumps(summary)


@pytest.mark.parametrize(
    "case,outcome",
    [
        ("missing", "acceptance_predicate_failed"),
        ("empty", "acceptance_predicate_failed"),
        ("mismatch", "stopped_controlled"),
        ("reflection", "stopped_controlled"),
    ],
)
def test_failed_or_partial_selected_observation_never_becomes_acceptance(
    tmp_path, monkeypatch, capsys, case, outcome
):
    root = prepare(tmp_path, monkeypatch)
    calls = wire(monkeypatch, case)
    p.execute()
    result = json.loads(capsys.readouterr().out)
    assert result["outcome"] == outcome
    assert result["attempts"] == 4
    assert len(calls) == 4
    assert SECRET not in (root / "receipt.json").read_text()
    assert CHOSEN not in (root / "receipt.json").read_text()


def test_receipt_reservation_prevents_a_second_execution(tmp_path, monkeypatch, capsys):
    prepare(tmp_path, monkeypatch)
    calls = wire(monkeypatch)
    p.execute()
    capsys.readouterr()
    with pytest.raises(FileExistsError):
        p.execute()
    assert len(calls) == 5


def test_late_final_cleanup_cannot_be_reported_as_acceptance(tmp_path, monkeypatch, capsys):
    prepare(tmp_path, monkeypatch)
    calls = wire(monkeypatch)
    original_close = p.helper.CountedWire.aclose

    async def late_close(transport):
        await original_close(transport)
        if transport.budget.current["credential_mode"] == "no_key":
            transport.budget.end = p.time.monotonic() - 1

    monkeypatch.setattr(p.helper.CountedWire, "aclose", late_close)
    p.execute()
    result = json.loads(capsys.readouterr().out)
    assert len(calls) == 5
    assert result["outcome"] == "stopped_controlled"
    receipt = json.loads(p.OUTPUT.read_text())
    assert receipt["code"] == "transport_timeout"


def test_invalid_environment_setup_restores_all_process_patches(tmp_path, monkeypatch, capsys):
    prepare(tmp_path, monkeypatch, secret="synthetic\x00bad")
    calls = wire(monkeypatch)
    original_read = p.helper.platform_context.PlatformReader._read
    original_session = p.helper.platform_context.HttpSession
    monkeypatch.setenv("PILOT_PLATFORM_KEY", "synthetic-before")
    p.execute()
    result = json.loads(capsys.readouterr().out)
    assert result["outcome"] == "preparation_or_analysis_failure"
    assert result["attempts"] == 0
    assert calls == []
    assert p.helper.platform_context.PlatformReader._read is original_read
    assert p.helper.platform_context.HttpSession is original_session
    assert p.os.environ["PILOT_PLATFORM_KEY"] == "synthetic-before"


def test_live_command_requires_an_explicit_execute_flag(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["project_probe.py"])
    with pytest.raises(SystemExit):
        p.main()


def test_project_budget_shares_five_slots_across_all_sessions(tmp_path):
    path = tmp_path / "receipt.json"
    path.write_text("{}")
    budget = p.ProjectBudget(
        end=p.time.monotonic() + 10,
        output=path,
        allowed_paths=frozenset({"/api/v1/projects/synthetic"}),
    )
    for _ in range(5):
        budget.begin("platform_project_detail", "/api/v1/projects/synthetic", "no_key")
        budget.end_call()
    with pytest.raises(p.helper.YorungeError):
        budget.begin("platform_project_detail", "/api/v1/projects/synthetic", "no_key")
    assert len(budget.report["calls"]) == 5
