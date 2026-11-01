"""One bounded private read survey: actual product decode plus missing-key controls.

No raw response values, identifiers, credentials, URLs with IDs, or exception text
are persisted. This is behavior research, not provider/auth conformance acceptance.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import stat
import time
import tomllib
from pathlib import Path
from typing import Any

import httpx
from httpcore._async.http11 import AsyncHTTP11Connection
from pydantic import TypeAdapter, ValidationError

from yorunge import api
from yorunge.adapters import platform_context
from yorunge.adapters.http_session import HttpSession
from yorunge.adapters.http_transport import HttpxTransport
from yorunge.application import platform_projection as projection
from yorunge.application.http_transport import HttpRequest, HttpStatusFailure
from yorunge.application.response_json import literal_secret_match, parse_json
from yorunge.domain.credentials import SecretValue, normalize_target
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Identifier

PREP = Path(__file__).resolve().parents[1] / "p02-pilot"
OUTPUT = PREP / "platform-reverse-20261101.json"
ORIGIN = "https://api.ssyz.org.tr"
BASE = "/api/v1"
ID = TypeAdapter(Identifier)
WIRE_READ_MAX = 65536
BODY_MAX = 4194304


def private_bytes(path: Path) -> bytes:
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise ValueError("unsafe preparation directory")
    info = path.parent.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("unsafe preparation directory")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb") as source:
        info = os.fstat(source.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size > 65536
        ):
            raise ValueError("unsafe preparation file")
        return source.read(65537)


def private_json(path: Path) -> dict[str, Any]:
    value = parse_json(private_bytes(path), max_bytes=65536)
    if not isinstance(value, dict):
        raise ValueError("invalid preparation object")
    return value


def known_names() -> frozenset[str]:
    receipt = json.loads(
        (Path.cwd() / "docs/research/p02-platform-discovery-observations.json").read_text()
    )
    names: set[str] = {
        "id",
        "name",
        "slug",
        "description",
        "visibility",
        "owner_id",
        "org_id",
        "org_name",
        "credit_balance",
        "settings",
        "created_at",
        "updated_at",
    }

    def collect(value: object) -> None:
        if isinstance(value, dict):
            fields = value.get("fields")
            if isinstance(fields, dict):
                names.update(fields)
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(receipt)
    return frozenset(names)


def shape(value: object, known: frozenset[str], *, depth: int = 0) -> dict[str, object]:
    if depth > 8:
        return {"type": "bounded_nested_value"}
    if isinstance(value, dict):
        fields = {k: shape(v, known, depth=depth + 1) for k, v in value.items() if k in known}
        return {
            "type": "object",
            "fields": fields,
            "unpublished_field_count": len(value) - len(fields),
        }
    if isinstance(value, list):
        if len(value) > 128:
            raise YorungeError("invalid_response")
        shapes = {json.dumps(shape(v, known, depth=depth + 1), sort_keys=True) for v in value}
        return {
            "type": "array",
            "count": len(value),
            "observed_item_shapes": [json.loads(v) for v in sorted(shapes)],
        }
    return {
        "type": {
            str: "string",
            bool: "boolean",
            int: "integer",
            float: "number",
            type(None): "null",
        }.get(type(value), "unsupported")
    }


def identifier_valid(value: object) -> bool:
    try:
        ID.validate_python(value, strict=True)
        return True
    except ValidationError:
        return False


class Budget:
    def __init__(self, *, end: float, output: Path, allowed_paths: frozenset[str]):
        self.end, self.output, self.allowed_paths = end, output, allowed_paths
        self.current: dict[str, object] | None = None
        self.active = False
        self.report: dict[str, Any] = {
            "schema_version": 1,
            "purpose": "behavior_research_not_auth_acceptance",
            "service": "evren-platform",
            "origin": ORIGIN,
            "api_base_path": BASE,
            "limits": {"logical_gets": 8, "attempts": 8, "body_bytes": 4194304, "seconds": 30},
            "retry": "disabled_for_research",
            "calls": [],
            "body_bytes": 0,
            "body_bytes_semantics": "consumed_raw_body_chunks_not_network_packet_total",
            "attempts": 0,
            "authentication": "unknown",
            "key_format_control": "not_run_unverified_grammar",
            "outcome": "prepared",
        }

    def remaining(self) -> float:
        remaining = self.end - 1.0 - time.monotonic()
        if remaining <= 0:
            raise YorungeError("transport_timeout")
        return remaining

    def persist(self) -> None:
        # Preserve the last durable ledger if serialization/write fails. A pending
        # file after an abrupt stop is private evidence, never a new-call permit.
        pending = self.output.with_name(self.output.name + ".pending")
        fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "w") as target:
                json.dump(self.report, target, ensure_ascii=True, sort_keys=True)
                target.write("\n")
                target.flush()
                os.fsync(target.fileno())
            os.replace(pending, self.output)
            directory = os.open(self.output.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except BaseException:
            if pending.exists():
                pending.unlink()
            raise

    def begin(self, endpoint: str, path: str, mode: str) -> dict[str, object]:
        self.remaining()
        self.before_read()
        if self.active or len(self.report["calls"]) >= 8 or path not in self.allowed_paths:
            raise YorungeError("invalid_request")
        row: dict[str, object] = {"endpoint": endpoint, "credential_mode": mode, "attempts": 0}
        self.report["calls"].append(row)
        self.current, self.active = row, True
        self.persist()  # The slot is consumed before network, including failed analysis.
        return row

    def end_call(self) -> None:
        self.active = False

    def attempt(self, request: httpx.Request, secret: SecretValue) -> None:
        self.remaining()
        if (
            not self.active
            or self.current is None
            or self.report["attempts"] >= 8
            or request.method != "GET"
            or request.url.scheme != "https"
            or request.url.host != "api.ssyz.org.tr"
            or request.url.port not in (None, 443)
            or request.url.username
            or request.url.password
            or request.url.path not in self.allowed_paths
            or request.url.query
            or "authorization" in request.headers
            or "cookie" in request.headers
        ):
            raise YorungeError("invalid_request")
        expected = secret.reveal() if self.current["credential_mode"] == "selected_key" else None
        if request.headers.get("X-API-Key") != expected:
            raise YorungeError("invalid_credential")
        self.report["attempts"] += 1
        self.current["attempts"] = int(self.current["attempts"]) + 1
        self.persist()

    def before_read(self) -> None:
        self.remaining()
        # HTTP/1.1 HTTPcore reads at most this pinned, verified bound. Reserve
        # one complete upstream read before advancing the response iterator.
        if BODY_MAX - self.report["body_bytes"] < WIRE_READ_MAX:
            raise YorungeError("invalid_response")

    def consume(self, size: int) -> None:
        self.remaining()
        if (
            type(size) is not int
            or not 0 <= size <= WIRE_READ_MAX
            or self.report["body_bytes"] + size > BODY_MAX
        ):
            raise YorungeError("invalid_response")
        self.report["body_bytes"] += size


class CountedStream(httpx.AsyncByteStream):
    def __init__(self, inner: httpx.AsyncByteStream, budget: Budget):
        self.inner, self.budget = inner, budget

    async def __aiter__(self):
        iterator = self.inner.__aiter__()
        while True:
            self.budget.before_read()
            try:
                async with asyncio.timeout(self.budget.remaining()):
                    chunk = await iterator.__anext__()
            except StopAsyncIteration:
                return
            self.budget.consume(len(chunk))
            yield chunk

    async def aclose(self):
        try:
            async with asyncio.timeout(max(0.0, self.budget.end - time.monotonic())):
                await self.inner.aclose()
        except TimeoutError:
            raise YorungeError("transport_timeout") from None


class CountedWire(httpx.AsyncBaseTransport):
    def __init__(self, budget: Budget, secret: SecretValue, inner=None):
        self.budget, self.secret = budget, secret
        if inner is None and AsyncHTTP11Connection.READ_NUM_BYTES != WIRE_READ_MAX:
            raise YorungeError("invalid_request")
        self.inner = inner or httpx.AsyncHTTPTransport(
            retries=0,
            trust_env=False,
            http2=False,
            limits=httpx.Limits(max_connections=2, max_keepalive_connections=2),
        )

    async def handle_async_request(self, request):
        self.budget.attempt(request, self.secret)
        async with asyncio.timeout(self.budget.remaining()):
            response = await self.inner.handle_async_request(request)
        row = self.budget.current
        assert row is not None
        row["status"] = response.status_code
        row["pagination_headers_present"] = sorted(
            set(k.lower() for k in response.headers)
            & {"link", "x-total-count", "x-has-next", "x-next-cursor", "content-range"}
        )
        self.budget.persist()
        response.stream = CountedStream(response.stream, self.budget)
        return response

    async def aclose(self):
        try:
            async with asyncio.timeout(max(0.0, self.budget.end - time.monotonic())):
                await self.inner.aclose()
        except TimeoutError:
            raise YorungeError("transport_timeout") from None


class SingleAttempt(HttpxTransport):
    async def _attempts(self, request, deadline):
        assert self._client is not None
        wire = self._wire_request(request, deadline)
        try:
            return await self._client.send(wire, stream=True, auth=None, follow_redirects=False)
        finally:
            self._client.cookies.clear()


def endpoint_name(path: str) -> str:
    return {
        "auth/me": "platform_me",
        "organizations": "platform_organizations",
        "projects": "platform_projects",
    }.get(path, "platform_project_detail")


def predicates(value: object, kind: str, selected: str | None = None) -> dict[str, bool]:
    if kind == "me":
        result = projection.identity(value)
        return {"projection_passed": True, "me_identifier_valid": identifier_valid(result.me_id)}
    if kind == "organizations":
        result = projection.organizations(value)
        return {
            "projection_passed": True,
            "total_nonnegative_int64": type(result.reported_total) is int
            and 0 <= result.reported_total < 2**63,
            "total_gte_item_count": result.reported_total >= len(result.items),
            "total_equals_item_count": result.reported_total == len(result.items),
            "all_identifiers_valid": all(identifier_valid(v.id) for v in result.items),
        }
    if kind == "projects":
        result = projection.projects(value)
        return {
            "projection_passed": True,
            "all_identifiers_valid": all(identifier_valid(v.id) for v in result),
        }
    if selected is None:
        raise YorungeError("invalid_request")
    detail = projection.detail(value, selected)
    return {"projection_passed": True, "detail_id_matches_request": detail.id == selected}


def main():
    os.umask(0o077)
    # Validate the private parent before reserving any output.
    info = PREP.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise SystemExit("Unsafe preparation directory; no request made.")
    # No rerun can reset the cumulative request/deadline counter.
    with OUTPUT.open("x", encoding="utf-8") as out:
        out.write('{"outcome":"reserved_before_preparation"}\n')
    started = time.monotonic()
    budget = None
    try:
        key_data = private_json(PREP / "credentials.json")
        secret = SecretValue(key_data["PILOT_PLATFORM_KEY"])
        del key_data
        scope = private_json(PREP / "scope.json")
        explicit_project = scope.get("project_id")
        config = tomllib.loads(private_bytes(PREP / "config.toml").decode("utf-8", "strict"))
        profile = config["profiles"]["pilot"]
        if (
            normalize_target(profile.get("platform_url", ORIGIN + BASE))
            != normalize_target(ORIGIN + BASE)
            or profile.get("platform_key_env") != "PILOT_PLATFORM_KEY"
        ):
            raise YorungeError("invalid_service_target")
        project = explicit_project if explicit_project is not None else profile.get("project_id")
        if project is not None:
            ID.validate_python(project, strict=True)
        endpoints = ["auth/me", "organizations", "projects"]
        if project is not None:
            endpoints.append("projects/" + project)
        paths = frozenset(BASE + "/" + v for v in endpoints)
        budget = Budget(end=started + 30, output=OUTPUT, allowed_paths=paths)
        names = known_names()
        target = normalize_target(ORIGIN + BASE)
        original_read = platform_context.PlatformReader._read
        original_session = platform_context.HttpSession
        original_env = os.environ.get("PILOT_PLATFORM_KEY")

        async def observed(transport, snapshot, path, deadline, *, detail):
            if snapshot.context.project_id != project:
                raise YorungeError("state_changed")
            row = budget.begin(endpoint_name(path), BASE + "/" + path, "selected_key")
            try:
                data = await original_read(
                    transport, snapshot, path, min(deadline, budget.end - 1.0), detail=detail
                )
                if data is not None:
                    kind = {
                        "auth/me": "me",
                        "organizations": "organizations",
                        "projects": "projects",
                    }.get(path, "detail")
                    value = projection.safe_raw(data, kind, secret)
                    row["schema_observation"] = shape(value, names)
                    row["predicates"] = predicates(
                        value, kind, path.removeprefix("projects/") if detail else None
                    )
                else:
                    row["detail_not_found"] = True
                return data
            finally:
                budget.end_call()
                budget.persist()

        def owned():
            return HttpSession(
                transport_factory=lambda: SingleAttempt(transport=CountedWire(budget, secret))
            )

        try:
            platform_context.PlatformReader._read = staticmethod(observed)
            platform_context.HttpSession = owned
            os.environ["PILOT_PLATFORM_KEY"] = secret.reveal()
            result = api.discover_context(
                "evren-platform",
                config=PREP / "config.toml",
                profile="pilot",
                project=explicit_project,
                state_dir=PREP / "state",
            )
            budget.report["product_discovery"] = {
                "returned_typed_result": True,
                "service_id": result.data.service_id,
                "validation": result.data.validation,
                "endpoint_count": len(result.data.observations),
                "selected_project_present": result.data.selected.project_id is not None,
                "project_count": len(result.data.projects.items),
                "organization_count": len(result.data.organizations.items),
                "reasons": list(result.data.reasons),
            }
        finally:
            platform_context.PlatformReader._read = staticmethod(original_read)
            platform_context.HttpSession = original_session
            if original_env is None:
                os.environ.pop("PILOT_PLATFORM_KEY", None)
            else:
                os.environ["PILOT_PLATFORM_KEY"] = original_env

        # Missing-key controls do not establish invalid-key grammar or principal meaning.
        async def controls(transport):
            for path in endpoints:
                row = budget.begin(endpoint_name(path), BASE + "/" + path, "no_key")
                try:
                    request = HttpRequest(
                        target,
                        "GET",
                        path,
                        service_id="evren-platform",
                        read_only=False,
                        max_bytes=1048576,
                    )
                    try:
                        async with transport.open(request, deadline=budget.end - 1.0) as response:
                            data = bytearray()
                            async for chunk in response.chunks():
                                if len(data) + len(chunk) > 1048576:
                                    raise YorungeError("invalid_response")
                                data.extend(chunk)
                        kind = {
                            "auth/me": "me",
                            "organizations": "organizations",
                            "projects": "projects",
                        }.get(path, "detail")
                        value = projection.safe_raw(bytes(data), kind, secret)
                        row["schema_observation"] = shape(value, names)
                        row["missing_key_rejected"] = False
                    except HttpStatusFailure as error:
                        row["missing_key_rejected"] = error.status_code in (401, 403)
                        if error.status_code not in (401, 403):
                            raise
                finally:
                    budget.end_call()
                    budget.persist()

        with owned() as session:
            session.call(controls)
        budget.report["outcome"] = "behavior_research_complete"
    except YorungeError as error:
        if budget is not None:
            budget.report.update(outcome="stopped_controlled", code=error.code)
    except Exception as error:
        if budget is not None:
            budget.report.update(
                outcome="preparation_or_analysis_failure", exception_class=type(error).__name__
            )
    finally:
        if budget is not None:
            budget.report["elapsed_seconds"] = round(time.monotonic() - started, 6)
            budget.persist()
            print(
                json.dumps(
                    {
                        "outcome": budget.report["outcome"],
                        "logical_gets": len(budget.report["calls"]),
                        "actual_attempts": budget.report["attempts"],
                        "body_bytes": budget.report["body_bytes"],
                        "elapsed_seconds": budget.report["elapsed_seconds"],
                        "product_discovery": budget.report.get("product_discovery"),
                        "calls": [
                            {
                                k: v
                                for k, v in r.items()
                                if k
                                in {
                                    "endpoint",
                                    "credential_mode",
                                    "status",
                                    "attempts",
                                    "missing_key_rejected",
                                    "predicates",
                                }
                            }
                            for r in budget.report["calls"]
                        ],
                    }
                )
            )
        else:
            print('{"outcome":"preparation_failed_before_network"}')


if __name__ == "__main__":
    main()
