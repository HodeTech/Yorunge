"""Offline read-only allowlist/identity/secret/byte regressions; no private input access."""

import asyncio
import hashlib
import importlib.util
import os
import py_compile
import sys
from pathlib import Path
from types import ModuleType

import httpx
import pytest

from yorunge.adapters.storage_transport import TransferHttpxTransport, TransferSession
from yorunge.application.http_transport import HttpCredential, HttpRequest
from yorunge.domain.credentials import SecretValue
from yorunge.domain.errors import YorungeError

spec = importlib.util.spec_from_file_location(
    "created_read", Path(__file__).with_name("read_probe.py")
)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
DATASET = "00000000-0000-4000-8000-000000000001"
OWNER = "00000000-0000-4000-8000-000000000002"
SECRET = "synthetic-api-key-do-not-publish"
NAME = "yorunge-upload-pilot-synthetic"


class Bytes(httpx.AsyncByteStream):
    def __init__(self, value):
        self.value = value

    async def __aiter__(self):
        data = probe.shared.encoded(self.value)
        for offset in range(0, len(data), 32768):
            yield data[offset : offset + 32768]


def setup(mutation=None, secret=SECRET):
    calls = []
    key = HttpCredential(
        "X-API-Key", SecretValue(secret), target=probe.TARGET, service_id="evren-platform"
    )

    def reply(request):
        index = len(calls)
        calls.append(request)
        record = {
            "id": DATASET,
            "owner_id": OWNER,
            "org_id": None,
            "name": NAME,
            "visibility": "private",
            "owner_username": "alice",
            "slug": "pilot",
        }
        rows = [([record], 200), (record, 200), ({"permissions": ["upload"], "role": "owner"}, 200)]
        body, status = rows[index]
        if mutation:
            body, status = mutation(index, body, status)
        return httpx.Response(status, stream=Bytes(body))

    budget = probe.ReadBudget(key, httpx.MockTransport(reply), DATASET)
    observer = probe.Observer(key, budget, DATASET, NAME)
    return key, budget, observer, calls


def run(key, budget, observer):
    with TransferSession(
        key, transport_factory=lambda: TransferHttpxTransport(key, transport=budget)
    ) as session:
        return session.exchange(observer.run)


@pytest.mark.parametrize("secret", [SECRET, "a"])
def test_only_three_exact_reads_and_no_authority_upgrade(secret):
    key, budget, observer, calls = setup(secret=secret)
    result = run(key, budget, observer)
    assert result == {
        "same_private_dataset_observed": True,
        "upload_label_observed": True,
        "authority_verified": False,
        "pricing_verified": False,
    }
    assert [call.method for call in calls] == ["GET"] * 3
    assert [call.url.path for call in calls] == [
        "/api/v1/datasets",
        "/api/v1/datasets/alice/pilot",
        f"/api/v1/datasets/{DATASET}/my-role",
    ]
    assert calls[0].url.query == b"page=1&page_size=5&scope=owned"
    assert budget.attempts == 3
    assert "alice" not in str(observer.rows) and NAME not in str(observer.rows)
    assert SECRET not in str(observer.rows) and DATASET not in str(observer.rows)


@pytest.mark.parametrize(
    "username", ["", "..", "../other", "https://other.example", "%2f", "x" * 129, SECRET]
)
def test_bad_dynamic_detail_segment_never_leaves_owned_endpoint(username):
    def mutate(index, body, status):
        if index == 0:
            body[0]["owner_username"] = username
        return body, status

    key, budget, observer, calls = setup(mutate)
    with pytest.raises(YorungeError):
        run(key, budget, observer)
    assert len(calls) == budget.attempts == 1


@pytest.mark.parametrize(
    "case", ["absent", "duplicate", "public", "wrong_name", "wrong_parent", "secret_metadata"]
)
def test_identity_or_scope_mismatch_stops_without_alternate_lookup(case):
    def mutate(index, body, status):
        if index == 0:
            if case == "absent":
                body = []
            elif case == "duplicate":
                body.append(dict(body[0]))
            elif case == "public":
                body[0]["visibility"] = "public"
            elif case == "wrong_name":
                body[0]["name"] = "other"
            elif case == "secret_metadata":
                body[0]["discarded"] = {"x": SECRET}
        if index == 1 and case == "wrong_parent":
            body["owner_id"] = DATASET
        return body, status

    key, budget, observer, calls = setup(mutate)
    with pytest.raises(YorungeError):
        run(key, budget, observer)
    assert budget.attempts == len(calls) <= 2


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("status", [401, 403, 405])
def test_first_access_or_route_failure_stops(index, status):
    def mutate(current, body, code):
        return (SECRET, status) if current == index else (body, code)

    key, budget, observer, calls = setup(mutate)
    with pytest.raises(YorungeError) as failure:
        run(key, budget, observer)
    assert budget.attempts == len(calls) == index + 1
    assert SECRET not in str(failure.value) and SECRET not in str(observer.rows)
    assert all(call.method == "GET" for call in calls)


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "datasets"),
        ("GET", "billing"),
        ("GET", f"datasets/{DATASET}"),
        ("DELETE", f"datasets/{DATASET}"),
    ],
)
def test_transport_cannot_select_mutations_or_other_reads(method, path):
    key, budget, _, calls = setup()
    request = HttpRequest(
        probe.TARGET,
        method,
        path,
        credential=key,
        read_only=method == "GET",
        service_id="evren-platform",
    )
    with pytest.raises(YorungeError):
        budget.select(request)
    assert budget.attempts == 0 and not calls


def test_raw_http_mutation_never_reaches_delegate_after_valid_selection():
    key, budget, _, calls = setup()
    selected = HttpRequest(
        probe.TARGET,
        "GET",
        "datasets",
        query=(("page", "1"), ("page_size", "5"), ("scope", "owned")),
        credential=key,
        read_only=True,
        service_id="evren-platform",
    )
    budget.select(selected)
    wire = httpx.Request("POST", selected.url, headers={"X-API-Key": SECRET})
    with pytest.raises(YorungeError):
        asyncio.run(budget.handle_async_request(wire))
    assert not calls and budget.attempts == 0


def test_oversized_owned_response_is_never_published():
    key, budget, observer, calls = setup(lambda i, body, code: ("x" * (probe.LIMIT + 1), code))
    with pytest.raises(YorungeError):
        run(key, budget, observer)
    assert budget.attempts == len(calls) == 1
    assert "shape" not in observer.rows[0]


def test_helper_runs_the_hashed_bytes_despite_valid_stale_bytecode_and_loaded_module(
    tmp_path, monkeypatch
):
    path = tmp_path / "helper.py"
    path.write_bytes(b'VALUE = "old"\n')
    before = path.stat()
    py_compile.compile(str(path), doraise=True)
    path.write_bytes(b'VALUE = "new"\n')
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    old = ModuleType("frozen_upload_helpers")
    old.VALUE = "cached"
    monkeypatch.setitem(sys.modules, "frozen_upload_helpers", old)
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    result = probe.checked_helper(path, checksum)
    assert result.VALUE == "new" and result is not old
    assert result.__file__ == str(path)


def test_wrong_helper_hash_never_executes_source(tmp_path):
    marker, path = tmp_path / "marker", tmp_path / "helper.py"
    path.write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\n")
    with pytest.raises(RuntimeError):
        probe.checked_helper(path, "0" * 64)
    assert not marker.exists()


@pytest.mark.parametrize("missing", ["owned", "detail", "both"])
def test_absent_org_is_not_evidence_of_explicit_personal_null(missing):
    def mutate(index, body, status):
        if index == 0 and missing in {"owned", "both"}:
            body[0].pop("org_id")
        if index == 1 and missing in {"detail", "both"}:
            body.pop("org_id")
        return body, status

    key, budget, observer, calls = setup(mutate)
    with pytest.raises(YorungeError) as failure:
        run(key, budget, observer)
    assert failure.value.code == "invalid_response"
    assert budget.attempts == len(calls) == (2 if missing == "detail" else 1)
