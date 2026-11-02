"""Three strictly read-only observations of the same journaled dataset; no write resume."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
import tomllib
from pathlib import Path
from types import ModuleType

import httpx

from yorunge.adapters.guarded_http import GuardedHttpTransport
from yorunge.adapters.storage_transport import TransferHttpxTransport, TransferSession
from yorunge.application.http_transport import HttpCredential, HttpRequest, HttpStatusFailure
from yorunge.application.response_json import literal_secret_match, parse_json
from yorunge.domain.credentials import SecretValue
from yorunge.domain.errors import YorungeError

ROOT = Path(__file__).resolve().parents[4]
PREP = ROOT / ".local/p02-pilot"
PRIOR = PREP / "p02-2-write-20261102"
OUTPUT = PREP / "p02-2-created-read-20261102"
HELPER = Path(__file__).parent.parent / "platform-upload-pilot-20261102/pilot.py"
HELPER_SHA = "c7a192c3ac9b5f25613fe817d4138951d18814376058705ae141f375e3e984cf"


def checked_helper(path, checksum):
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != checksum:
        raise RuntimeError("frozen helper hash mismatch")
    module = ModuleType("frozen_upload_helpers")
    module.__file__ = str(path)
    exec(compile(content, str(path), "exec"), module.__dict__)
    return module


shared = checked_helper(HELPER, HELPER_SHA)
TARGET = shared.TARGET
LIMIT = 512 * 1024
PART = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", flags=re.ASCII)


def segment(value, secret):
    if (
        type(value) is not str
        or not PART.fullmatch(value)
        or literal_secret_match(value, secret.reveal())
    ):
        raise YorungeError("invalid_response")
    return value


class ReadBudget(httpx.AsyncBaseTransport):
    def __init__(self, key, delegate, dataset):
        self.key, self.delegate = key, delegate
        self.dataset = shared.checked_id(dataset, key.secret)
        self.paths = [
            HttpRequest(
                TARGET,
                "GET",
                "datasets",
                query=(("page", "1"), ("page_size", "5"), ("scope", "owned")),
                service_id="evren-platform",
            ).url
        ]
        self.selected = []
        self.end = time.monotonic() + 30
        self.active = None
        self.attempts = self.per_call = self.body_bytes = 0

    def select(self, request):
        if (
            type(request) is not HttpRequest
            or request.method != "GET"
            or request.content
            or request.target != TARGET
            or request.credential is not self.key
            or request.read_only is not True
            or len(self.selected) >= len(self.paths)
            or request.url != self.paths[len(self.selected)]
        ):
            raise YorungeError("invalid_request")
        self.active, self.per_call = request.url, 0
        self.selected.append(request.url)

    def bind_detail(self, username, slug):
        if len(self.paths) != 1 or self.selected != self.paths:
            raise YorungeError("invalid_request")
        username, slug = segment(username, self.key.secret), segment(slug, self.key.secret)
        self.paths.extend(
            HttpRequest(TARGET, "GET", path, service_id="evren-platform").url
            for path in (f"datasets/{username}/{slug}", f"datasets/{self.dataset}/my-role")
        )

    async def handle_async_request(self, request):
        if (
            request.method != "GET"
            or str(request.url) != self.active
            or request.headers.get("content-length", "0") != "0"
            or request.headers.get("X-API-Key") != self.key.secret.reveal()
            or any(
                name in request.headers
                for name in ("authorization", "cookie", "proxy-authorization", "transfer-encoding")
            )
            or self.attempts >= 6
            or self.per_call >= 2
            or time.monotonic() >= self.end
        ):
            raise YorungeError("invalid_request")
        self.attempts += 1
        self.per_call += 1
        response = await self.delegate.handle_async_request(request)
        response.stream = ResponseBytes(response.stream, self)
        return response

    async def aclose(self):
        await self.delegate.aclose()


class ResponseBytes(httpx.AsyncByteStream):
    def __init__(self, wrapped, budget):
        self.wrapped, self.budget = wrapped, budget

    async def __aiter__(self):
        count = 0
        async for chunk in self.wrapped:
            count += len(chunk)
            self.budget.body_bytes += len(chunk)
            if count > LIMIT or self.budget.body_bytes > 3 * LIMIT:
                raise YorungeError("invalid_response")
            yield chunk

    async def aclose(self):
        await self.wrapped.aclose()


class Observer:
    def __init__(self, key, budget, dataset, name):
        self.key, self.budget, self.dataset, self.name = key, budget, dataset, name
        self.rows = []

    def deadline(self):
        if time.monotonic() >= self.budget.end:
            raise YorungeError("transport_timeout")

    async def get(self, transport, label, path, query=()):
        self.deadline()
        if len(self.rows) >= 3:
            raise YorungeError("invalid_request")
        request = HttpRequest(
            TARGET,
            "GET",
            path,
            query=query,
            credential=self.key,
            service_id="evren-platform",
            read_only=True,
            max_bytes=LIMIT,
        )
        self.budget.select(request)
        row = {"endpoint": label}
        self.rows.append(row)
        async with transport.open(request, deadline=self.budget.end) as response:
            row["status"] = response.status_code
            body = b"".join([part async for part in response.chunks()])
        raw = parse_json(body, max_bytes=LIMIT)
        value = shared.payload(raw, self.key.secret)
        row.update(body_bytes=len(body), shape=shared.shape(raw))
        self.deadline()
        return value

    async def run(self, transport):
        owned = await self.get(
            transport, "owned", "datasets", (("page", "1"), ("page_size", "5"), ("scope", "owned"))
        )
        if type(owned) is not list or len(owned) > 5:
            raise YorungeError("invalid_response")
        matching = [row for row in owned if type(row) is dict and row.get("id") == self.dataset]
        if len(matching) != 1:
            raise YorungeError("invalid_response")
        selected = matching[0]
        self.check_record(selected)
        username = segment(selected.get("owner_username"), self.key.secret)
        slug = segment(selected.get("slug"), self.key.secret)
        self.budget.bind_detail(username, slug)
        detail = await self.get(transport, "detail_by_slug", f"datasets/{username}/{slug}")
        self.check_record(detail)
        if any(detail.get(field) != selected.get(field) for field in ("owner_id", "org_id")):
            raise YorungeError("invalid_response")
        role = await self.get(transport, "my_role", f"datasets/{self.dataset}/my-role")
        role = shared.object_value(role)
        permissions = role.get("permissions")
        if (
            type(permissions) is not list
            or len(permissions) > 32
            or not all(type(value) is str and len(value) <= 64 for value in permissions)
        ):
            raise YorungeError("invalid_response")
        self.deadline()
        return {
            "same_private_dataset_observed": True,
            "upload_label_observed": "upload" in permissions,
            "authority_verified": False,
            "pricing_verified": False,
        }

    def check_record(self, row):
        row = shared.object_value(row)
        if (
            row.get("id") != self.dataset
            or row.get("name") != self.name
            or row.get("visibility") != "private"
            or "org_id" not in row
        ):
            raise YorungeError("invalid_response")
        shared.checked_id(row.get("owner_id"), self.key.secret)
        if row.get("org_id") is not None:
            shared.checked_id(row["org_id"], self.key.secret)


def inputs():
    values = parse_json(shared.private_bytes(PREP / "credentials.json"), max_bytes=65536)
    config = tomllib.loads(shared.private_bytes(PREP / "config.toml").decode("utf-8", "strict"))
    profile = config["profiles"]["pilot"]
    if (
        shared.normalize_target(profile["platform_url"]) != TARGET
        or profile["platform_key_env"] != "PILOT_PLATFORM_KEY"
    ):
        raise YorungeError("invalid_request")
    secret = SecretValue(values["PILOT_PLATFORM_KEY"])
    journal = [
        parse_json(line, max_bytes=8192)
        for line in shared.private_bytes(PRIOR / "journal.jsonl").splitlines()
    ]

    def one(event, field):
        rows = [row for row in journal if type(row) is dict and row.get("event") == event]
        if len(rows) != 1:
            raise YorungeError("invalid_request")
        return rows[0][field]

    project = shared.checked_id(one("reserved", "project_id"), secret)
    dataset = shared.checked_id(one("dataset_known", "dataset_id"), secret)
    name = one("selected_private_name", "dataset_name")
    if (
        type(name) is not str
        or not name.startswith("yorunge-upload-pilot-")
        or literal_secret_match(name, secret.reveal())
    ):
        raise YorungeError("invalid_request")
    return (
        HttpCredential("X-API-Key", secret, target=TARGET, service_id="evren-platform"),
        project,
        dataset,
        name,
    )


def execute():
    os.umask(0o077)
    if (
        Path.cwd().resolve() != ROOT
        or subprocess.run(["git", "diff", "--quiet", "HEAD"], cwd=ROOT).returncode
    ):
        raise YorungeError("invalid_request")
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    probe_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    test_hash = hashlib.sha256(
        Path(__file__).with_name("test_read_probe.py").read_bytes()
    ).hexdigest()
    key, project, dataset, name = inputs()
    ledger = shared.Ledger(OUTPUT, project)
    budget = ReadBudget(key, GuardedHttpTransport(), dataset)
    observer = Observer(key, budget, dataset, name)
    started = time.monotonic()
    report = {
        "schema_version": 1,
        "outcome": "stopped",
        "effectful_requests": 0,
        "authority_verified": False,
        "pricing_verified": False,
    }
    try:
        with TransferSession(
            key, transport_factory=lambda: TransferHttpxTransport(key, transport=budget)
        ) as session:
            report.update(session.exchange(observer.run))
        report["outcome"] = "completed_read_observations"
    except HttpStatusFailure as error:
        report.update(error_code=error.code, http_status=error.status_code)
    except YorungeError as error:
        report["error_code"] = error.code
    finally:
        report.update(
            rows=observer.rows,
            attempts=budget.attempts,
            consumed_body_bytes=budget.body_bytes,
            elapsed_seconds=time.monotonic() - started,
            source_commit=source,
            probe_sha256=probe_hash,
            test_sha256=test_hash,
            helper_sha256=HELPER_SHA,
            source_unchanged=(
                subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
                == source
                and subprocess.run(["git", "diff", "--quiet", "HEAD"], cwd=ROOT).returncode == 0
            ),
        )
        try:
            ledger.append({"event": "finished", "outcome": report["outcome"]})
        finally:
            ledger.close()
        with (OUTPUT / "receipt.json").open("xb") as output:
            output.write(shared.encoded(report))
            output.flush()
            os.fsync(output.fileno())
    print(json.dumps({key: report[key] for key in ("outcome", "attempts", "effectful_requests")}))


def main():
    parser = argparse.ArgumentParser(
        description="Specifically authorized three-GET read observation."
    )
    parser.add_argument("--execute", action="store_true", required=True)
    parser.parse_args()
    try:
        execute()
    except Exception:
        raise SystemExit(
            "Read observation stopped; private data and raw errors were not printed."
        ) from None
    except KeyboardInterrupt:
        raise SystemExit("Read observation interrupted; no writes were attempted.") from None


if __name__ == "__main__":
    main()
