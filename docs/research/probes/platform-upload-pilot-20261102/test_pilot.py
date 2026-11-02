"""Offline one-attempt research safety; never loads private inputs or real accounts."""

import asyncio
import importlib.util
import json
import time
from pathlib import Path

import httpx
import pytest

from yorunge.adapters.storage_transport import TransferHttpxTransport, TransferSession
from yorunge.application.http_transport import HttpCredential
from yorunge.domain.credentials import SecretValue
from yorunge.domain.errors import YorungeError

spec = importlib.util.spec_from_file_location("upload_pilot", Path(__file__).with_name("pilot.py"))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
PROJECT = "00000000-0000-4000-8000-000000000001"
DATASET = "00000000-0000-4000-8000-000000000002"
OWNER = "00000000-0000-4000-8000-000000000003"
ORG = "00000000-0000-4000-8000-000000000004"
SECRET = "synthetic-private-key-must-never-be-persisted"


class Bytes(httpx.AsyncByteStream):
    def __init__(self, content):
        self.content = content

    async def __aiter__(self):
        for start in range(0, len(self.content), 32768):
            yield self.content[start : start + 32768]


class Provider(httpx.AsyncBaseTransport):
    def __init__(self, ledger, mutation=None):
        self.ledger, self.mutation, self.calls, self.items, self.uploaded = (
            ledger,
            mutation,
            [],
            [],
            {},
        )
        self.name = None

    async def handle_async_request(self, request):
        path, method = request.url.path, request.method
        content = await request.aread()
        self.calls.append((method, path, content))
        if method != "GET":
            journal = [
                json.loads(row)
                for row in (self.ledger.root / "journal.jsonl").read_text().splitlines()
            ]
            assert journal[-1]["event"] == "intent"  # Intent is already readable/fsynced.
        body = json.loads(content) if content and method == "POST" else None
        stage, raw = self.reply(method, path, body, content, request)
        status = 200
        if self.mutation is not None:
            status, raw = self.mutation(stage, raw)
        return httpx.Response(status, stream=Bytes(probe.encoded(raw)))

    def reply(self, method, path, body, content, request):
        prefix = f"/api/v1/datasets/{DATASET}"
        if path == f"/api/v1/projects/{PROJECT}" and method == "GET":
            return "project", {
                "id": PROJECT,
                "owner_id": OWNER,
                "org_id": ORG,
                "visibility": "private",
            }
        if path == "/api/v1/datasets" and method == "POST":
            assert body["visibility"] == "private" and body["org_id"] == ORG
            self.name = body["name"]
            return "create", {"success": True, "data": {"id": DATASET}}
        if path == prefix and method == "GET":
            return "dataset", {
                "id": DATASET,
                "name": self.name,
                "org_id": ORG,
                "visibility": "private",
            }
        if path == prefix + "/my-role":
            return "role", {"role": "owner", "permissions": ["upload"]}
        if path == f"/api/v1/projects/{PROJECT}/datasets":
            if method == "POST":
                assert body == {"dataset_id": DATASET}
                return "link", {"success": True}
            return "linked", [{"id": DATASET}]
        if path == prefix + "/upload/presign":
            info = body["files"][0]
            descriptor = dict(
                info,
                object_key="objects/" + info["filename"],
                upload_url=prefix + "/upload/put?key=objects%2F" + info["filename"],
                direct_upload_url="https://unused.example/signed?token=PRIVATE-URL-CANARY",
            )
            return "presign", {"presigned_urls": [descriptor], "duplicates": []}
        if path == prefix + "/upload/put":
            self.uploaded[request.url.params["key"]] = content
            return "put", {"success": True}
        if path == prefix + "/upload/confirm":
            assert body["skip_dedup"] is True
            item = body["items"][0]
            assert self.uploaded[item["object_key"]]
            self.items.append(
                {
                    "id": f"00000000-0000-4000-8000-{10 + len(self.items):012d}",
                    "dataset_id": DATASET,
                    "original_filename": item["filename"],
                    "file_size_bytes": item["file_size"],
                    "sha256_hash": item["sha256_hash"],
                }
            )
            return "confirm", {"created": 1, "actual_count": len(self.items)}
        assert path == prefix + "/items" and request.url.query == b"limit=10"
        return "items", {"items": self.items, "next_cursor": None, "total": len(self.items)}


def setup(tmp_path, mutation=None):
    key = HttpCredential(
        "X-API-Key", SecretValue(SECRET), target=probe.TARGET, service_id="evren-platform"
    )
    ledger = probe.Ledger(tmp_path / "pilot", PROJECT)
    provider = Provider(ledger, mutation)
    budget = probe.BudgetTransport(key, provider, PROJECT)
    pilot = probe.Pilot(key, budget, ledger, PROJECT)
    return key, ledger, provider, budget, pilot


def run(key, budget, pilot):
    with TransferSession(
        key, transport_factory=lambda: TransferHttpxTransport(key, transport=budget)
    ) as session:
        return session.exchange(pilot.run)


def test_three_named_images_preserve_duplicate_content_and_private_journal(tmp_path):
    key, ledger, provider, budget, pilot = setup(tmp_path)
    try:
        result = run(key, budget, pilot)
    finally:
        ledger.close()
    assert result["three_named_files_metadata_match"] is True
    assert (
        result["authority_verified"]
        is result["pricing_verified"]
        is result["remote_bytes_verified"]
        is False
    )
    assert budget.effect_counts == {"create": 1, "link": 1, "presign": 3, "put": 3, "confirm": 3}
    assert budget.attempts == 16 and pilot.reads == 5
    assert len(provider.items) == 3 and len(provider.uploaded) == 3
    assert len({item["sha256_hash"] for item in provider.items}) == 2
    public = json.dumps(pilot.rows)
    journal = (ledger.root / "journal.jsonl").read_text()
    assert SECRET not in public + journal and "PRIVATE-URL" not in public + journal
    assert "object_key" not in journal and "objects/" not in journal
    assert DATASET not in public and DATASET in journal
    assert sum(len(data) for _, data in probe.fixtures()) < 1024 * 1024


@pytest.mark.parametrize(
    "stage",
    [
        "project",
        "create",
        "dataset",
        "role",
        "link",
        "linked",
        "presign",
        "put",
        "confirm",
        "items",
    ],
)
def test_first_access_failure_stops_without_effect_replay_or_cleanup(tmp_path, stage):
    def denied(current, raw):
        return (403, {"message": SECRET}) if current == stage else (200, raw)

    key, ledger, provider, budget, pilot = setup(tmp_path, denied)
    try:
        with pytest.raises(YorungeError) as failure:
            run(key, budget, pilot)
    finally:
        ledger.close()
    assert failure.value.code == "remote_access_denied"
    assert failure.value.__context__ is failure.value.__cause__ is None
    assert all(method != "DELETE" for method, _, _ in provider.calls)
    assert budget.effect_counts.get("create", 0) <= 1 and budget.effect_counts.get("put", 0) <= 3


@pytest.mark.parametrize("bad", [False, 0, 1, "true", None])
def test_success_control_is_strict_even_inside_envelope(bad):
    secret = SecretValue(SECRET)
    value = {"success": True, "data": {"success": bad, "id": DATASET}}
    with pytest.raises(YorungeError):
        probe.payload(value, secret)


@pytest.mark.parametrize(
    "case",
    [
        "secret_metadata",
        "wrong_private",
        "wrong_parent",
        "role_missing",
        "link_missing",
        "direct_only",
        "wrong_hash",
        "wrong_client_uid",
        "duplicate_names",
        "wrong_item_parent",
    ],
)
def test_bad_consumed_or_discarded_wire_stops(tmp_path, case):
    def mutate(stage, raw):
        if case == "secret_metadata" and stage == "create":
            raw["unused"] = {"private": SECRET}
        elif stage == "dataset" and case in ("wrong_private", "wrong_parent"):
            raw["visibility" if case == "wrong_private" else "org_id"] = (
                "public" if case == "wrong_private" else OWNER
            )
        elif case == "role_missing" and stage == "role":
            raw["permissions"] = []
        elif case == "link_missing" and stage == "linked":
            raw = []
        elif stage == "presign":
            item = raw["presigned_urls"][0]
            if case == "direct_only":
                item.pop("upload_url")
            if case == "wrong_hash":
                item["sha256_hash"] = "0" * 64
            if case == "wrong_client_uid":
                item["client_uid"] = "wrong"
        elif stage == "items" and case == "duplicate_names":
            raw["items"][1]["original_filename"] = raw["items"][0]["original_filename"]
        elif stage == "items" and case == "wrong_item_parent":
            raw["items"][0]["dataset_id"] = PROJECT
        return 200, raw

    key, ledger, _, budget, pilot = setup(tmp_path, mutate)
    try:
        with pytest.raises(YorungeError):
            run(key, budget, pilot)
    finally:
        ledger.close()
    assert budget.effect_counts.get("create", 0) <= 1
    assert SECRET not in (ledger.root / "journal.jsonl").read_text()


@pytest.mark.parametrize(
    "method,suffix",
    [
        ("DELETE", "datasets"),
        ("POST", "terms/accept"),
        ("GET", "billing"),
        ("POST", "projects/other/datasets"),
        ("PUT", "datasets/other/upload/put?key=a"),
    ],
)
def test_request_allowlist_cannot_be_widened_by_active_selection(tmp_path, method, suffix):
    key, ledger, _, budget, _ = setup(tmp_path)
    url = probe.TARGET.service_origin + "/api/v1/" + suffix
    try:
        with pytest.raises(YorungeError):
            budget.select(method, url, 0)
    finally:
        ledger.close()
    assert budget.attempts == 0


def test_existing_research_directory_permanently_blocks_reentry_after_intent(tmp_path):
    ledger = probe.Ledger(tmp_path / "pilot", PROJECT)
    ledger.intent("create")
    ledger.close()
    with pytest.raises(FileExistsError):
        probe.Ledger(tmp_path / "pilot", PROJECT)


def test_journal_failure_before_create_has_zero_create_http(tmp_path, monkeypatch):
    key, ledger, provider, budget, pilot = setup(tmp_path)
    original = ledger.append

    def fail_intent(row):
        if row["event"] == "intent":
            raise OSError("private filesystem failure")
        original(row)

    monkeypatch.setattr(ledger, "append", fail_intent)
    try:
        with pytest.raises(OSError):
            run(key, budget, pilot)
    finally:
        ledger.close()
    assert len(provider.calls) == 1 and budget.effects == 0


def test_elapsed_total_budget_has_zero_new_http(tmp_path):
    key, ledger, _, budget, pilot = setup(tmp_path)
    budget.end = time.monotonic() - 1
    try:
        with pytest.raises(YorungeError):
            run(key, budget, pilot)
    finally:
        ledger.close()
    assert budget.attempts == budget.effects == 0


def test_second_create_is_rejected_even_after_active_selection_is_reset():
    calls = []

    def reply(request):
        calls.append(request)
        return httpx.Response(200, stream=Bytes(b"{}"))

    key = HttpCredential(
        "X-API-Key", SecretValue(SECRET), target=probe.TARGET, service_id="evren-platform"
    )
    budget = probe.BudgetTransport(key, httpx.MockTransport(reply), PROJECT)
    url = probe.TARGET.service_origin + "/api/v1/datasets"

    async def attempt():
        budget.select("POST", url, 0)
        request = httpx.Request("POST", url, headers={"X-API-Key": SECRET})
        response = await budget.handle_async_request(request)
        await response.aclose()
        budget.select("POST", url, 0)
        await budget.handle_async_request(request)

    with pytest.raises(YorungeError):
        asyncio.run(attempt())
    assert len(calls) == budget.effects == budget.attempts == 1


@pytest.mark.parametrize(
    "headers",
    [
        {"X-API-Key": "wrong"},
        {"X-API-Key": SECRET, "Cookie": "x=y"},
        {"X-API-Key": SECRET, "Authorization": "Bearer bad"},
    ],
)
def test_wrong_auth_or_ambient_headers_never_reach_delegate(headers):
    key = HttpCredential(
        "X-API-Key", SecretValue(SECRET), target=probe.TARGET, service_id="evren-platform"
    )
    budget = probe.BudgetTransport(
        key, httpx.MockTransport(lambda request: pytest.fail("network reached")), PROJECT
    )
    url = probe.TARGET.service_origin + f"/api/v1/projects/{PROJECT}"
    budget.select("GET", url, 0)
    request = httpx.Request("GET", url, headers=headers)
    with pytest.raises(YorungeError):
        asyncio.run(budget.handle_async_request(request))
    assert budget.attempts == 0


def test_body_and_aggregate_budgets_are_enforced_before_publication(tmp_path):
    _, ledger, _, budget, _ = setup(tmp_path)
    budget.body_bytes = probe.MAX_TOTAL - 2
    stream = probe.BudgetStream(Bytes(b"123"), budget, 512)

    async def read():
        return [part async for part in stream]

    try:
        with pytest.raises(YorungeError):
            asyncio.run(read())
    finally:
        ledger.close()


def test_unforeseen_cli_exception_never_prints_private_traceback(monkeypatch):
    def unexpected(project):
        raise RuntimeError(SECRET)

    monkeypatch.setattr(probe, "execute", unexpected)
    monkeypatch.setattr("sys.argv", ["pilot.py", "--project", PROJECT, "--execute"])
    with pytest.raises(SystemExit) as failure:
        probe.main()
    assert SECRET not in str(failure.value) and "private inputs" in str(failure.value)
