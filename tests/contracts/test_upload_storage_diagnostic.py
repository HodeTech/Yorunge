"""Real descriptor bytes plus fake account responses; no account or network call."""

import asyncio
import hashlib
import json
import runpy
import time
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

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
    project,
)
from yorunge.adapters.upload_input_files import capture_upload_input
from yorunge.application.http_transport import HttpCredential, HttpStatusFailure
from yorunge.application.upload_descriptors import FileContext
from yorunge.domain.errors import YorungeError

ROOT = Path(__file__).parents[2]
HELPER = runpy.run_path(str(ROOT / "scripts/upload_storage_diagnostic.py"))


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "opaque",
        "denied",
        "wrong_sent",
        "confirm_counter",
        "bad_confirm",
        "existing",
        "secret_put",
        "missing_hash",
        "changed_input",
        "role_denied",
        "changed_after_put",
        "changed_during_presign",
    ],
)
def test_storage_research_keeps_one_effect_per_stage_and_exact_source_bytes(tmp_path, case):
    work = tmp_path.resolve() / "fixture"
    work.mkdir()
    manifest = HELPER["BASE"]["fixtures"](work)
    observed = capture_upload_input(work / "source", manifest, SECRET, end=time.monotonic() + 30)
    index, file = next(
        (index, file) for index, file in enumerate(manifest.files) if file.path == "first.png"
    )
    context = FileContext(
        PLAN.plan_id,
        PLAN.digest,
        str(uuid4()),
        DATASET,
        index,
        file,
        HELPER["TARGET"],
        str(uuid4()),
        str(uuid4()),
        manifest.file_count,
    )
    expected = HELPER["codec"].created(encoded(dataset()), SCOPE, PARAMETERS, SECRET)
    view = SimpleNamespace(
        plan=SimpleNamespace(scope=SCOPE, parameters=PARAMETERS, root=observed.root)
    )
    key = HttpCredential("X-API-Key", SECRET, target=HELPER["TARGET"], service_id="evren-platform")
    requests, storage_requests, sinks = [], [], []
    items = []

    def item(name, identifier):
        source = next(file for file in manifest.files if file.path == name)
        return {
            "id": identifier,
            "dataset_id": DATASET,
            "original_filename": name,
            "file_size_bytes": source.size,
            "sha256_hash": source.sha256,
        }

    if case == "confirm_counter":
        items.append(item("different.png", "00000000-0000-4000-8000-000000000088"))
    if case == "existing":
        items.append(item("first.png", "00000000-0000-4000-8000-000000000088"))
    if case == "changed_input":
        (work / "source/first.png").write_bytes(b"x" * 79)

    class Response:
        status_code = 200

        def __init__(self, raw):
            self.raw = encoded(raw)

        async def chunks(self):
            yield self.raw

    class Client:
        @asynccontextmanager
        async def open(self, request, *, deadline):
            requests.append(request)
            path = request.endpoint
            if path.endswith("/upload/presign"):
                sent = json.loads(request.content)["files"][0]
                assert sent["filename"] == "first.png"
                assert sent["sha256_hash"] == HELPER["FILES"]["first.png"]
                raw = {
                    "presigned_urls": [
                        {
                            **sent,
                            "object_key": "synthetic/key.png",
                            "upload_url": f"/datasets/{DATASET}/upload/put?key=synthetic%2Fkey.png",
                            "content_type": "image/png",
                        }
                    ],
                    "duplicates": [],
                }
                if case == "changed_during_presign":
                    (work / "source/first.png").write_bytes(b"x" * 79)
            elif path.endswith("/upload/confirm"):
                assert len(storage_requests) == 1
                raw = {
                    "created": 0 if case == "bad_confirm" else 1,
                    "actual_count": 1,
                    "batch_duplicates": 0,
                }
                if case != "bad_confirm":
                    new = item("first.png", "00000000-0000-4000-8000-000000000089")
                    if case == "missing_hash":
                        new["sha256_hash"] = None
                    items.append(new)
            elif path.endswith("/items"):
                raw = {"items": list(items), "total": len(items), "next_cursor": None}
            elif path.endswith("/my-role"):
                raw = {
                    "role": "owner",
                    "permissions": ["read"] if case == "role_denied" else ["read", "upload"],
                }
            elif path == "auth/me":
                raw = {"success": True, "data": {"id": SCOPE.owner.id}}
            elif path == "projects/" + SCOPE.project_id:
                raw = project()
            elif path == "datasets":
                row = located()
                row.pop("contributions_enabled")
                raw = [row]
            elif path.startswith("datasets/"):
                raw = dataset()
            else:
                raw = [{"id": DATASET}]
            yield Response(raw)

        @asynccontextmanager
        async def open_storage(self, request, *, deadline):
            storage_requests.append(request)
            sink = b"".join([chunk async for chunk in request.source.chunks()])
            sinks.append(sink)
            if case == "denied":
                raise HttpStatusFailure(403)
            raw = {"success": True}
            if case == "opaque":
                raw = {"uploaded": True, "size": 79, "object_key": "synthetic/key.png"}
            if case == "secret_put":
                raw["unused"] = SECRET.reveal()
            response = Response(raw)
            response.sent_bytes = len(sink)
            response.sent_sha256 = (
                "a" * 64 if case == "wrong_sent" else hashlib.sha256(sink).hexdigest()
            )
            if case == "changed_after_put":
                (work / "source/first.png").write_bytes(b"x" * 79)
            yield response

    report = {"requests": [], "outcome": "incomplete"}
    action = HELPER["Probe"](Client(), key, view, expected, context, manifest, report, True).run()
    if case in (
        "denied",
        "wrong_sent",
        "existing",
        "missing_hash",
        "changed_input",
        "role_denied",
        "changed_after_put",
        "changed_during_presign",
    ):
        with pytest.raises(YorungeError) as error:
            asyncio.run(action)
        assert error.value.code == {
            "denied": "remote_access_denied",
            "wrong_sent": "input_changed",
            "changed_input": "input_changed",
            "role_denied": "remote_access_denied",
            "changed_after_put": "input_changed",
            "changed_during_presign": "input_changed",
        }.get(case, "invalid_response")
    else:
        asyncio.run(action)
        assert report["outcome"] == "evidence_collected"
    assert len(storage_requests) == (
        0 if case in ("existing", "changed_input", "role_denied", "changed_during_presign") else 1
    )
    assert sum(request.endpoint.endswith("/upload/presign") for request in requests) == (
        0 if case in ("existing", "changed_input", "role_denied") else 1
    )
    confirmed = sum(request.endpoint.endswith("/upload/confirm") for request in requests)
    assert confirmed == (
        1 if case in ("valid", "confirm_counter", "bad_confirm", "missing_hash") else 0
    )
    if sinks:
        assert len(sinks[0]) == 79
        assert hashlib.sha256(sinks[0]).hexdigest() == HELPER["FILES"]["first.png"]
        assert storage_requests[0].source._closed is True
    if case == "opaque":
        assert report["typed_put_ack_accepted"] is False
        assert report["put_shape"]["root"]["matches_expected"]["object_key"] is True
    if case == "confirm_counter":
        assert report["confirm_candidates"] == {"current": False, "one": True}
        assert report["new_file_metadata_matches"] is True
    assert len(report["requests"]) <= 11
    if case == "changed_input":
        assert requests == []
    assert DATASET not in json.dumps(report)
    assert SECRET.reveal() not in json.dumps(report)
    assert "synthetic/key.png" not in json.dumps(report)
