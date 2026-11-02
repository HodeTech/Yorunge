"""Explicit five-GET research survey. Never persist account values or perform writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import time
import tomllib
import uuid
from pathlib import Path
from typing import Any

import httpx

from yorunge.adapters.http_session import HttpSession
from yorunge.adapters.http_transport import HttpxTransport
from yorunge.application.http_transport import HttpCredential, HttpRequest, HttpStatusFailure
from yorunge.application.response_json import literal_secret_match, parse_json
from yorunge.domain.credentials import SecretValue, normalize_target
from yorunge.domain.errors import YorungeError

ROOT = Path(__file__).resolve().parents[4]
PREP = ROOT / ".local/p02-pilot"
OUTPUT = PREP / "p02-2-preflight-20261102.json"
TARGET = normalize_target("https://api.ssyz.org.tr/api/v1")
LIMIT = 524_288
TOTAL_LIMIT = 5_242_880
FIELDS = frozenset(
    {
        "success",
        "data",
        "message",
        "id",
        "user_id",
        "owner_id",
        "org_id",
        "organization_id",
        "personal_org_id",
        "role",
        "permissions",
        "name",
        "slug",
        "visibility",
        "item_count",
        "items",
        "total",
        "next_cursor",
        "credit_balance",
    }
)


def private_bytes(path: Path) -> bytes:
    for parent in (path.parent.parent, path.parent):
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
            raise YorungeError("invalid_request")
    if stat.S_IMODE(path.parent.stat().st_mode) != 0o700:
        raise YorungeError("invalid_request")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size > 65_536
        ):
            raise YorungeError("invalid_request")
        data = stream.read(65_537)
        if len(data) > 65_536:
            raise YorungeError("invalid_request")
        return data


def endpoints(project: str) -> tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...]:
    if type(project) is not str:
        raise YorungeError("invalid_request")
    try:
        parsed = uuid.UUID(project)
    except ValueError:
        raise YorungeError("invalid_request") from None
    if str(parsed) != project:
        raise YorungeError("invalid_request")
    return (
        ("me", "auth/me", ()),
        ("organizations", "organizations", ()),
        ("project", f"projects/{project}", ()),
        ("project_datasets", f"projects/{project}/datasets", ()),
        ("owned_datasets", "datasets", (("page", "1"), ("page_size", "5"), ("scope", "owned"))),
    )


def shape(value: object, *, depth: int = 0) -> dict[str, object]:
    if value is None:
        return {"type": "null"}
    if type(value) is bool:
        return {"type": "bool"}
    if type(value) in (int, float, str):
        return {"type": type(value).__name__}
    if depth >= 4:
        return {"type": "container"}
    if isinstance(value, list):
        variants = {json.dumps(shape(item, depth=depth + 1), sort_keys=True) for item in value}
        return {
            "type": "array",
            "count": len(value),
            "shapes": [json.loads(v) for v in sorted(variants)],
        }
    if isinstance(value, dict):
        return {
            "type": "object",
            "fields": {
                key: shape(child, depth=depth + 1) for key, child in value.items() if key in FIELDS
            },
            "discarded_field_count": sum(key not in FIELDS for key in value),
        }
    raise YorungeError("invalid_response")


def no_secret(value: object, secret: SecretValue) -> None:
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, str) and literal_secret_match(item, secret.reveal()):
            raise YorungeError("invalid_response")
        if isinstance(item, dict):
            pending.extend(key for key in item if key not in FIELDS)
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)


class BudgetTransport(httpx.AsyncBaseTransport):
    def __init__(
        self,
        secret: SecretValue,
        project: str,
        delegate: httpx.AsyncBaseTransport,
        *,
        started: float | None = None,
    ) -> None:
        self.secret, self.delegate = secret, delegate
        self.allowed = tuple(
            HttpRequest(TARGET, "GET", path, query=query, service_id="evren-platform").url
            for _, path, query in endpoints(project)
        )
        self.attempts = 0
        self.active: str | None = None
        self.per_call = 0
        self.started = time.monotonic() if started is None else started
        self.end = self.started + 30
        self.body_bytes = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if (
            request.method != "GET"
            or str(request.url) not in self.allowed
            or str(request.url) != self.active
            or request.headers.get("content-length", "0") != "0"
            or "transfer-encoding" in request.headers
            or self.attempts >= 10
            or self.per_call >= 2
            or time.monotonic() >= self.end
            or request.headers.get("X-API-Key") != self.secret.reveal()
            or any(
                key in request.headers for key in ("authorization", "cookie", "proxy-authorization")
            )
        ):
            raise YorungeError("invalid_request")
        self.attempts += 1
        self.per_call += 1
        response = await self.delegate.handle_async_request(request)
        response.stream = BudgetStream(response.stream, self)
        return response

    async def aclose(self) -> None:
        await self.delegate.aclose()


class BudgetStream(httpx.AsyncByteStream):
    def __init__(self, delegate: httpx.AsyncByteStream, budget: BudgetTransport) -> None:
        self.delegate, self.budget = delegate, budget

    async def __aiter__(self):
        size = 0
        async for part in self.delegate:
            self.budget.body_bytes += len(part)
            size += len(part)
            if self.budget.body_bytes > TOTAL_LIMIT or size > LIMIT:
                raise YorungeError("invalid_response")
            yield part

    async def aclose(self) -> None:
        await self.delegate.aclose()


def survey(secret: SecretValue, project: str, budget: BudgetTransport) -> dict[str, Any]:
    calls: list[dict[str, object]] = []
    consumed = 0
    report: dict[str, Any] = {
        "schema_version": 1,
        "purpose": "p02_2_five_get_preflight",
        "limits": {
            "logical_gets": 5,
            "attempts": 10,
            "body_bytes": TOTAL_LIMIT,
            "per_response_bytes": LIMIT,
            "total_seconds": 30,
        },
        "calls": calls,
        "attempts": 0,
        "consumed_body_bytes": 0,
        "outcome": "incomplete",
        "authority_verified": False,
        "pricing_verified": False,
        "effectful_requests": 0,
    }
    denied = False
    try:
        with HttpSession(transport_factory=lambda: HttpxTransport(transport=budget)) as session:
            for label, path, query in endpoints(project):
                if len(calls) >= 5 or time.monotonic() >= budget.end:
                    raise YorungeError("transport_timeout")
                # Dynamic path segments must not contain the selected literal credential.
                if literal_secret_match(project, secret.reveal()):
                    raise YorungeError("invalid_request")
                request = HttpRequest(
                    TARGET,
                    "GET",
                    path,
                    query=query,
                    service_id="evren-platform",
                    credential=HttpCredential(
                        "X-API-Key", secret, target=TARGET, service_id="evren-platform"
                    ),
                    read_only=True,
                    max_bytes=LIMIT,
                )
                budget.active, budget.per_call = request.url, 0
                row: dict[str, object] = {"endpoint": label}
                calls.append(row)

                async def read(
                    transport: Any,
                    captured: HttpRequest = request,
                    current: dict[str, object] = row,
                ) -> bytes:
                    nonlocal consumed
                    body = bytearray()
                    async with transport.open(captured, deadline=budget.end) as response:
                        current["status"] = response.status_code
                        async for part in response.chunks():
                            consumed += len(part)
                            if consumed > 5 * LIMIT or len(body) + len(part) > LIMIT:
                                raise YorungeError("invalid_response")
                            body.extend(part)
                    return bytes(body)

                try:
                    body = session.call(read)
                    raw = parse_json(body)
                    no_secret(raw, secret)
                    row.update(body_bytes=len(body), shape=shape(raw))
                    if time.monotonic() >= budget.end:
                        raise YorungeError("transport_timeout")
                    row["logical_success_flag"] = (
                        raw.get("success") is True
                        if isinstance(raw, dict) and "success" in raw
                        else None
                    )
                except HttpStatusFailure as error:
                    row["status"] = error.status_code
                    row["error_code"] = error.code
                    if error.status_code in (401, 403):
                        denied = True
                        break
                finally:
                    row["attempts"] = budget.per_call
                    budget.active = None
            report["outcome"] = "stopped_access_denied" if denied else "completed_observations"
    except YorungeError as error:
        report["error_code"] = error.code
        report["outcome"] = "stopped_controlled_error"
    finally:
        report["attempts"] = budget.attempts
        report["consumed_body_bytes"] = budget.body_bytes
        report["delivered_body_bytes"] = consumed
        report["elapsed_seconds"] = time.monotonic() - budget.started
    # All keys/values in the public record are protocol names, types/counts, or local codes.
    if len(json.dumps(report).encode("utf-8")) > 32_768:
        raise YorungeError("invalid_response")
    return report


def execute(project: str) -> None:
    started = time.monotonic()
    os.umask(0o077)
    if Path.cwd().resolve() != ROOT:
        raise YorungeError("invalid_request")
    endpoints(project)
    values = parse_json(private_bytes(PREP / "credentials.json"), max_bytes=65_536)
    config = tomllib.loads(private_bytes(PREP / "config.toml").decode("utf-8", "strict"))
    profile = config["profiles"]["pilot"]
    if (
        normalize_target(profile["platform_url"]) != TARGET
        or profile["platform_key_env"] != "PILOT_PLATFORM_KEY"
    ):
        raise YorungeError("invalid_service_target")
    if not isinstance(values, dict) or type(values.get("PILOT_PLATFORM_KEY")) is not str:
        raise YorungeError("credential_unavailable")
    secret = SecretValue(values["PILOT_PLATFORM_KEY"])
    del values
    descriptor = os.open(OUTPUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(b'{"outcome":"reserved_before_network"}\n')
        output.flush()
        os.fsync(output.fileno())
        delegate = httpx.AsyncHTTPTransport(
            retries=0,
            trust_env=False,
            limits=httpx.Limits(max_connections=2, max_keepalive_connections=2),
        )
        budget = BudgetTransport(secret, project, delegate, started=started)
        report = survey(secret, project, budget)
        report["probe_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        report["source_commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        data = (json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        output.seek(0)
        output.write(data)
        output.truncate()
        output.flush()
        os.fsync(output.fileno())
    print(
        json.dumps(
            {
                key: report[key]
                for key in ("outcome", "attempts", "consumed_body_bytes", "effectful_requests")
            }
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Explicit authorized five-GET research; no writes."
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--execute", action="store_true", required=True)
    args = parser.parse_args()
    failed = False
    try:
        execute(args.project)
    except (OSError, ValueError, KeyError, TypeError, YorungeError):
        failed = True
    if failed:
        raise SystemExit("Preflight stopped; private inputs and exceptions were not printed.")


if __name__ == "__main__":
    main()
