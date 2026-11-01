import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path.cwd() / "src"))
spec = importlib.util.spec_from_file_location(
    "account_probe", Path(__file__).with_name("account_probe.py")
)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

SECRET = p.SecretValue("synthetic-only-probe-secret-18492")


def test_shape_never_emits_values_or_free_keys():
    value = {
        "id": "private-id",
        "email": "private@example.test",
        "data": {"dynamic_person_name": "private-value"},
        "unknown-person": "private-data",
    }
    result = p.shape(value, frozenset({"id", "email", "data"}))
    wire = json.dumps(result)
    for text in (
        "private-id",
        "private@example.test",
        "dynamic_person_name",
        "private-value",
        "unknown-person",
        "private-data",
    ):
        assert text not in wire
    assert result["unpublished_field_count"] == 1


def test_full_raw_secret_scan_precedes_shape():
    raw = json.dumps(
        {"success": True, "data": {"id": "me", "unused": {"free": SECRET.reveal()}}}
    ).encode()
    with pytest.raises(p.YorungeError) as failure:
        p.projection.safe_raw(raw, "me", SECRET)
    assert failure.value.code == "invalid_response"


def test_real_projection_predicates_are_not_type_only_oracles():
    result = p.predicates({"items": [{"id": "org"}], "total": 1}, "organizations")
    assert result == {
        "projection_passed": True,
        "total_nonnegative_int64": True,
        "total_gte_item_count": True,
        "total_equals_item_count": True,
        "all_identifiers_valid": True,
    }
    assert p.predicates({"id": "chosen"}, "detail", "chosen")["detail_id_matches_request"] is True
    with pytest.raises(p.YorungeError):
        p.predicates({"id": "different"}, "detail", "chosen")


def test_budget_owns_one_global_counter_and_does_not_reset_per_client(tmp_path):
    path = tmp_path / "receipt.json"
    path.write_text("{}")
    budget = p.Budget(
        end=p.time.monotonic() + 10, output=path, allowed_paths=frozenset({"/api/v1/auth/me"})
    )
    for _ in range(8):
        budget.begin("platform_me", "/api/v1/auth/me", "selected_key")
        request = httpx.Request(
            "GET", p.ORIGIN + "/api/v1/auth/me", headers={"X-API-Key": SECRET.reveal()}
        )
        budget.attempt(request, SECRET)
        budget.end_call()
    with pytest.raises(p.YorungeError):
        budget.begin("platform_me", "/api/v1/auth/me", "selected_key")
    assert budget.report["attempts"] == 8
    assert len(budget.report["calls"]) == 8
    assert SECRET.reveal() not in path.read_text()


@pytest.mark.parametrize(
    "case", ["foreign", "query", "cookie", "authorization", "wrong-key", "write"]
)
def test_wire_guard_rejects_before_io(tmp_path, case):
    path = tmp_path / "receipt.json"
    path.write_text("{}")
    budget = p.Budget(
        end=p.time.monotonic() + 10, output=path, allowed_paths=frozenset({"/api/v1/auth/me"})
    )
    budget.begin("platform_me", "/api/v1/auth/me", "selected_key")
    url = p.ORIGIN + "/api/v1/auth/me"
    headers = {"X-API-Key": SECRET.reveal()}
    method = "GET"
    if case == "foreign":
        url = "https://other.example.test/api/v1/auth/me"
    if case == "query":
        url += "?unexpected=1"
    if case == "cookie":
        headers["Cookie"] = "private"
    if case == "authorization":
        headers["Authorization"] = "Bearer private"
    if case == "wrong-key":
        headers["X-API-Key"] = "wrong"
    if case == "write":
        method = "POST"
    request = httpx.Request(method, url, headers=headers)
    with pytest.raises(p.YorungeError):
        budget.attempt(request, SECRET)
    assert budget.report["attempts"] == 0


def test_existing_logical_slot_survives_analysis_failure(tmp_path):
    path = tmp_path / "receipt.json"
    path.write_text("{}")
    budget = p.Budget(
        end=p.time.monotonic() + 10, output=path, allowed_paths=frozenset({"/api/v1/auth/me"})
    )
    budget.begin("platform_me", "/api/v1/auth/me", "selected_key")
    budget.end_call()
    assert len(json.loads(path.read_text())["calls"]) == 1
    with pytest.raises(p.YorungeError):
        budget.consume(4194305)


def test_no_key_control_never_injects_secret_and_uses_one_attempt(tmp_path):
    path = tmp_path / "receipt.json"
    path.write_text("{}")
    budget = p.Budget(
        end=p.time.monotonic() + 10, output=path, allowed_paths=frozenset({"/api/v1/auth/me"})
    )

    async def handler(request):
        assert "X-API-Key" not in request.headers
        assert "Authorization" not in request.headers
        return httpx.Response(401, content=b"not retained")

    async def exercise():
        wire = p.CountedWire(budget, SECRET, inner=httpx.MockTransport(handler))
        async with p.SingleAttempt(transport=wire) as transport:
            budget.begin("platform_me", "/api/v1/auth/me", "no_key")
            request = p.HttpRequest(
                p.normalize_target(p.ORIGIN + p.BASE),
                "GET",
                "auth/me",
                service_id="evren-platform",
                read_only=False,
            )
            try:
                with pytest.raises(p.HttpStatusFailure) as failure:
                    async with transport.open(request, deadline=budget.end):
                        pass
                assert failure.value.status_code == 401
            finally:
                budget.end_call()

    asyncio.run(exercise())
    assert budget.report["attempts"] == 1
    assert budget.report["calls"][0]["status"] == 401
    assert budget.report["body_bytes"] == 0


def test_failed_ledger_write_preserves_last_durable_record(tmp_path, monkeypatch):
    path = tmp_path / "receipt.json"
    path.write_text("{}")
    budget = p.Budget(
        end=p.time.monotonic() + 10, output=path, allowed_paths=frozenset({"/api/v1/auth/me"})
    )
    budget.begin("platform_me", "/api/v1/auth/me", "selected_key")
    before = path.read_bytes()

    def failed(*args, **kwargs):
        raise OSError("synthetic disk failure")

    monkeypatch.setattr(p.json, "dump", failed)
    with pytest.raises(OSError):
        budget.persist()
    assert path.read_bytes() == before
    assert not path.with_name(path.name + ".pending").exists()


def prepare_fake(tmp_path, monkeypatch, key, project=None):
    import os

    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    values = {
        "credentials.json": json.dumps({"PILOT_PLATFORM_KEY": key}),
        "scope.json": json.dumps({"project_id": None}),
        "config.toml": 'schema_version=1\n[profiles.pilot]\nplatform_url="https://api.ssyz.org.tr/api/v1"\nplatform_key_env="PILOT_PLATFORM_KEY"\n'
        + (f'project_id="{project}"\n' if project else ""),
    }
    for name, content in values.items():
        path = root / name
        path.write_text(content)
        path.chmod(0o600)
    monkeypatch.setattr(p, "PREP", root)
    monkeypatch.setattr(p, "OUTPUT", root / "receipt.json")
    return root


def test_setup_failure_restores_both_patches_and_env_before_any_network(
    tmp_path, monkeypatch, capsys
):
    prepare_fake(tmp_path, monkeypatch, "synthetic\x00invalid")
    monkeypatch.setenv("PILOT_PLATFORM_KEY", "synthetic-original")
    original_read = p.platform_context.PlatformReader._read
    original_session = p.platform_context.HttpSession

    def forbidden(*args, **kwargs):
        pytest.fail("no API invocation before valid env setup")

    monkeypatch.setattr(p.api, "discover_context", forbidden)
    p.main()
    assert p.platform_context.PlatformReader._read is original_read
    assert p.platform_context.HttpSession is original_session
    assert p.os.environ["PILOT_PLATFORM_KEY"] == "synthetic-original"
    assert json.loads(capsys.readouterr().out)["actual_attempts"] == 0


def test_profile_only_project_is_in_allowlist_and_not_an_explicit_override(
    tmp_path, monkeypatch, capsys
):
    prepare_fake(tmp_path, monkeypatch, SECRET.reveal(), "from-profile")
    allowed = []
    original_budget = p.Budget

    class Captured(original_budget):
        def __init__(self, **kwargs):
            allowed.append(kwargs["allowed_paths"])
            super().__init__(**kwargs)

    monkeypatch.setattr(p, "Budget", Captured)

    def denied(*args, **kwargs):
        assert kwargs["project"] is None
        raise p.YorungeError("state_invalid")

    monkeypatch.setattr(p.api, "discover_context", denied)
    p.main()
    assert "/api/v1/projects/from-profile" in allowed[0]
    result = json.loads(capsys.readouterr().out)
    assert result["actual_attempts"] == 0
    assert result["code"] if "code" in result else result["outcome"] == "stopped_controlled"


@pytest.mark.parametrize("wrapper", [p.CountedStream, p.CountedWire])
def test_inner_cleanup_uses_the_shared_final_deadline(tmp_path, wrapper):
    path = tmp_path / "receipt.json"
    path.write_text("{}")
    budget = p.Budget(end=p.time.monotonic() + 0.03, output=path, allowed_paths=frozenset())

    class Slow:
        async def aclose(self):
            await asyncio.sleep(10)

    instance = (
        wrapper(Slow(), budget)
        if wrapper is p.CountedStream
        else wrapper(budget, SECRET, inner=Slow())
    )

    async def exercise():
        with pytest.raises(p.YorungeError) as failure:
            await instance.aclose()
        assert failure.value.code == "transport_timeout"

    asyncio.run(exercise())


def test_remaining_body_budget_rejects_before_advancing_inner_stream(tmp_path):
    path = tmp_path / "receipt.json"
    path.write_text("{}")
    budget = p.Budget(
        end=p.time.monotonic() + 10, output=path, allowed_paths=frozenset({"/api/v1/auth/me"})
    )
    budget.report["body_bytes"] = p.BODY_MAX - 1

    class Inner:
        advanced = False

        def __aiter__(self):
            return self

        async def __anext__(self):
            self.advanced = True
            return b"ab"

    inner = Inner()
    stream = p.CountedStream(inner, budget)

    async def exercise():
        with pytest.raises(p.YorungeError):
            await anext(stream.__aiter__())

    asyncio.run(exercise())
    assert inner.advanced is False
    assert budget.report["body_bytes"] == p.BODY_MAX - 1
    with pytest.raises(p.YorungeError):
        budget.begin("platform_me", "/api/v1/auth/me", "no_key")
    assert budget.report["calls"] == []


def test_chunk_accounting_rejects_without_mutating_consumed_count(tmp_path):
    path = tmp_path / "receipt.json"
    path.write_text("{}")
    budget = p.Budget(end=p.time.monotonic() + 10, output=path, allowed_paths=frozenset())
    budget.report["body_bytes"] = p.BODY_MAX - 1
    with pytest.raises(p.YorungeError):
        budget.consume(2)
    assert budget.report["body_bytes"] == p.BODY_MAX - 1
