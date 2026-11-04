"""One bounded research link on a previously created, never-linked test dataset."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import runpy
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = runpy.run_path(str(ROOT / "scripts/upload_live_acceptance.py"))
TRACE = runpy.run_path(str(ROOT / "scripts/upload_control_trace.py"))
codec, TARGET = BASE["codec"], BASE["TARGET"]


async def probe(client: Any, key: Any, view: Any, expected: Any, report: dict[str, Any]) -> None:
    from yorunge.application.http_transport import HttpRequest, HttpStatusFailure
    from yorunge.domain.errors import YorungeError

    end = time.monotonic() + 30
    secret, scope = key.secret, view.plan.scope

    async def exchange(kind: str, path: str, *, content: bytes = b"", query: Any = ()) -> bytes:
        if len(report["requests"]) >= 7 or len(content) > 128:
            raise YorungeError("upload_limit_exceeded")
        write = kind == "link"
        if write and any(row["method"] == "POST" for row in report["requests"]):
            raise YorungeError("invalid_request")
        row: dict[str, Any] = {"kind": kind, "method": "POST" if write else "GET", "status": None}
        report["requests"].append(row)
        request = HttpRequest(
            TARGET,
            row["method"],
            path,
            content=content,
            headers=(("Content-Type", "application/json"),) if write else (),
            query=query,
            credential=key,
            service_id="evren-platform",
            read_only=not write,
        )
        try:
            async with client.open(request, deadline=end) as response:
                row["status"] = response.status_code
                raw = b"".join([part async for part in response.chunks()])
                row["body_bytes"] = len(raw)
                return raw
        except HttpStatusFailure as error:
            row["status"] = error.status_code
            raise

    project_path = "projects/" + codec.segment(scope.project_id, secret)
    me = codec.identity(await exchange("me", "auth/me"), secret)
    selected_project = codec.project(await exchange("project", project_path), scope, secret)
    codec.context(me, selected_project, scope)
    owned = codec.owned_page(
        await exchange(
            "owned", "datasets", query=(("page", "1"), ("page_size", "20"), ("scope", "owned"))
        ),
        expected.id,
        scope,
        view.plan.parameters,
        secret,
    )
    if owned.selected is None:
        raise YorungeError("invalid_response")
    codec.detail(
        await exchange("detail", codec.detail_path(owned.selected, secret)),
        expected,
        scope,
        view.plan.parameters,
        secret,
    )
    member_path = project_path + "/datasets"
    if codec.membership(await exchange("membership_before", member_path), expected.id, secret):
        report["outcome"] = "already_linked_no_post"
        return
    raw = await exchange("link", member_path, content=codec.link_content(expected.id, secret))
    matches = {"dataset_id": expected.id, "project_id": scope.project_id}
    report["link_shape"] = TRACE["body_shape"](raw, matches)
    if raw:
        value = codec._object(codec.raw(raw, "link", secret))
        for node in (value, value.get("data")):
            if type(node) is dict and any(
                type(node[key]) is not str or node[key] != wanted
                for key, wanted in matches.items()
                if key in node
            ):
                raise YorungeError("invalid_response")
    try:
        codec.link_ack(raw, secret)
        report["typed_ack_accepted"] = True
    except YorungeError as error:
        report.update(typed_ack_accepted=False, typed_ack_error_code=error.code)
    report["membership_after"] = codec.membership(
        await exchange("membership_after", member_path), expected.id, secret
    )
    report["outcome"] = "evidence_collected"


def run(args: argparse.Namespace) -> None:
    from yorunge.adapters.guarded_http import GuardedHttpTransport
    from yorunge.adapters.http_session import HttpSession
    from yorunge.adapters.http_transport import HttpxTransport
    from yorunge.domain.capabilities import instant
    from yorunge.domain.create_receipt import CreateReceiptV2
    from yorunge.domain.credentials import SecretValue
    from yorunge.domain.errors import YorungeError

    if not sys.flags.isolated or not args.accept_link_probe:
        raise ValueError("isolated runtime and explicit link-probe authorization required")
    _, value = BASE["credential"](args.config, args.credentials)
    identity = json.loads(BASE["private_file"](args.pilot / "uncertain-identity.json"))
    with BASE["open_existing_store"](args.pilot / "state") as store:
        view = BASE["StateUploads"](store).show(operation_id=identity["operation_id"])
    if (
        view.operation.status != "unknown"
        or len(view.intents) != 1
        or view.intents[0].kind != "create"
        or len(view.receipts) != 1
        or type(view.receipts[0]) is not CreateReceiptV2
    ):
        raise ValueError("only a never-link-armed test resource may be used")
    expected = view.receipts[0].created_dataset
    if view.operation.lease is not None and instant(view.operation.lease.expires_at) > datetime.now(
        UTC
    ):
        raise ValueError("active ownership prevents an independent link probe")
    if (
        view.receipts[0].result != "accepted"
        or expected.id != view.operation.dataset_id
        or view.plan.scope.project_id != args.project
        or not expected.name.startswith("yorunge-acceptance-")
        or (view.plan.scope.service_origin, view.plan.scope.api_base_path)
        != (TARGET.service_origin, TARGET.api_base_path)
    ):
        raise ValueError("exact historical test resource and canonical project required")
    key = BASE["HttpCredential"](
        "X-API-Key", SecretValue(value), target=TARGET, service_id="evren-platform"
    )
    driver = runpy.run_path(str(ROOT / "scripts/benchmark-upload.py"))
    before = driver["EVIDENCE"]["source"](ROOT)
    driver["STREAM"]["new_path"](args.workspace).mkdir(mode=0o700)
    BASE["write"](args.workspace / "started.json", {"source_commit": before["commit"]})
    for path in (args.workspace, args.workspace.parent):
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    report: dict[str, Any] = {
        "schema_version": 1,
        "diagnostic_only": True,
        "outcome": "incomplete",
        "source_commit": before["commit"],
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "limits": {
            "get": 6,
            "post": 1,
            "attempts": 13,
            "response_bytes": 13 * 1_048_576,
            "request_bytes": 128,
            "seconds": 30,
        },
        "requests": [],
        "operation_mutated": False,
        "authority_verified": False,
    }
    try:
        with HttpSession(
            transport_factory=lambda: HttpxTransport(transport=GuardedHttpTransport())
        ) as session:
            session.call(lambda client: probe(client, key, view, expected, report))
        if before != driver["EVIDENCE"]["source"](ROOT):
            raise ValueError("link diagnostic source changed")
    except YorungeError as error:
        report["error_code"] = error.code
        raise
    finally:
        BASE["write"](args.workspace / "receipt.json", report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "credentials", "pilot", "workspace"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--project", required=True)
    parser.add_argument("--accept-link-probe", action="store_true")
    args = parser.parse_args()
    from yorunge.domain.errors import YorungeError

    try:
        run(args)
    except (
        YorungeError,
        OSError,
        ValueError,
        LookupError,
        TypeError,
        KeyboardInterrupt,
        asyncio.CancelledError,
        subprocess.SubprocessError,
    ):
        print("Link diagnostic stopped; preserve its safe receipt.", file=sys.stderr)
        return 1
    print("Link diagnostic completed; no create, upload or operation transition was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
