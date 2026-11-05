"""Separately authorized, at most three GETs for an accepted create; no writes."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import runpy
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
BASE = runpy.run_path(str(ROOT / "scripts/upload_live_acceptance.py"))
api_codec = BASE["codec"]
TARGET = BASE["TARGET"]

FIELDS = (
    "id",
    "name",
    "modality",
    "visibility",
    "contributions_enabled",
    "owner_id",
    "org_id",
    "owner_username",
    "slug",
)
TYPES = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    dict: "object",
    list: "array",
    type(None): "null",
}


def selected_facts(selected: dict[str, Any], expected: Any) -> dict[str, Any]:
    baseline = expected.model_dump()
    return {
        "selected_fields": {
            name: TYPES[type(selected[name])] if name in selected else "missing" for name in FIELDS
        },
        "matches_create": {
            name: type(selected.get(name)) is type(baseline[name])
            and selected.get(name) == baseline[name]
            and name in selected
            for name in FIELDS[:7]
        },
    }


def wire_shape(data: bytes, expected: Any) -> dict[str, Any]:
    from yorunge.application.response_json import parse_json

    root = parse_json(data, max_bytes=1_048_576)
    has_success = type(root) is dict and "success" in root
    success = root.get("success") if type(root) is dict else None
    value = root.get("data", root) if type(root) is dict else root
    rows = value
    if type(value) is dict:
        rows = value.get("items")
    matches = []
    if type(rows) is list and len(rows) <= 128:
        matches = [row for row in rows if type(row) is dict and row.get("id") == expected.id]
    selected = matches[0] if len(matches) == 1 else {}
    return {
        "root_type": TYPES[type(root)],
        "success_present": has_success,
        "success_type": TYPES[type(success)] if has_success else "missing",
        "success_true": success is True,
        "data_type": TYPES[type(value)],
        "rows_type": TYPES[type(rows)],
        "row_count": len(rows) if type(rows) is list else None,
        "selected_count": len(matches),
        **selected_facts(selected, expected),
    }


def locate(raw: bytes, view: Any, expected: Any, secret: Any, report: dict[str, Any]) -> str:
    from yorunge.domain.errors import YorungeError
    from yorunge.domain.platform_upload import LocatedDataset

    rows = api_codec._rows(api_codec.raw(raw, "owned", secret, selected_id=expected.id))
    selected = next((row for row in rows if row["id"] == expected.id), None)
    if selected is None:
        raise YorungeError("invalid_response")
    matches = selected_facts(selected, expected)["matches_create"]
    if any(not matches[name] for name in FIELDS[:7] if name in selected):
        raise YorungeError("invalid_response")
    try:
        username = LocatedDataset.segment(selected.get("owner_username"))
        slug = LocatedDataset.segment(selected.get("slug"))
    except (TypeError, ValueError):
        raise YorungeError("invalid_response") from None
    # This research read uses only the exact ID and validated locator. Missing list
    # metadata stays missing; it is never filled from the create receipt.
    try:
        api_codec.owned_page(raw, expected.id, view.plan.scope, view.plan.parameters, secret)
        report["owned_consumer_accepted"] = True
    except YorungeError as error:
        report["owned_consumer_accepted"] = False
        report["owned_consumer_error_code"] = error.code
    return f"datasets/{api_codec.segment(username, secret)}/{api_codec.segment(slug, secret)}"


async def inspect(
    client: Any, key: Any, view: Any, expected: Any, report: dict[str, Any], *, end: float
) -> None:
    from yorunge.application.http_transport import HttpRequest, HttpStatusFailure
    from yorunge.domain.errors import YorungeError

    async def read(
        kind: Literal["owned", "detail"], endpoint: str, query: tuple[tuple[str, str], ...] = ()
    ) -> bytes:
        if len(report["requests"]) >= 3:
            raise YorungeError("upload_limit_exceeded")
        report["stage"] = kind
        row: dict[str, Any] = {
            "endpoint_kind": kind,
            "status": None,
            "bytes": 0,
            "page_size": int(dict(query)["page_size"]) if kind == "owned" else None,
        }
        report["requests"].append(row)
        request = HttpRequest(
            TARGET,
            "GET",
            endpoint,
            query=query,
            credential=key,
            service_id="evren-platform",
            read_only=True,
        )
        try:
            async with client.open(request, deadline=end) as response:
                row["status"] = response.status_code
                data = b"".join([part async for part in response.chunks()])
                row["bytes"] = len(data)
                return data
        except HttpStatusFailure as error:
            row["status"] = error.status_code
            raise

    try:
        raw = await read(
            "owned", "datasets", (("page", "1"), ("page_size", "20"), ("scope", "owned"))
        )
    except HttpStatusFailure as error:
        if error.status_code != 422:
            raise
        raw = await read(
            "owned", "datasets", (("page", "1"), ("page_size", "5"), ("scope", "owned"))
        )
    report["stage"] = "owned_shape"
    report["owned_shape"] = wire_shape(raw, expected)
    report["stage"] = "owned_locator"
    endpoint = locate(raw, view, expected, key.secret, report)
    raw = await read("detail", endpoint)
    report["stage"] = "detail_consumer"
    detail = api_codec._object(api_codec.raw(raw, "dataset", key.secret))
    report["detail_shape"] = selected_facts(detail, expected)
    api_codec.detail(raw, expected, view.plan.scope, view.plan.parameters, key.secret)
    report.update(
        consumer_accepted=report["owned_consumer_accepted"],
        detail_matches_create=True,
        stage="complete",
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    from yorunge.adapters.guarded_http import GuardedHttpTransport
    from yorunge.adapters.http_session import HttpSession
    from yorunge.adapters.http_transport import HttpxTransport
    from yorunge.domain.create_receipt import CreateReceiptV2
    from yorunge.domain.credentials import SecretValue
    from yorunge.domain.errors import YorungeError

    if not sys.flags.isolated or not args.accept_read_diagnostic:
        raise ValueError("isolated runtime and separate read consent required")
    if args.output.name.casefold() in ("", ".", "..", "started.json"):
        raise ValueError("diagnostic output must be a non-reserved file name")
    _, value = BASE["credential"](args.config, args.credentials)
    identity = json.loads(BASE["private_file"](args.pilot / "uncertain-identity.json"))
    with BASE["open_existing_store"](args.pilot / "state") as store:
        view = BASE["StateUploads"](store).show(operation_id=identity["operation_id"])
    receipts = [r for r in view.receipts if type(r) is CreateReceiptV2 and r.result == "accepted"]
    if len(receipts) != 1 or view.operation.status != "unknown":
        raise ValueError("one durable accepted create and unknown operation required")
    expected = receipts[0].created_dataset
    if expected.id != view.operation.dataset_id or (
        view.plan.scope.service_origin,
        view.plan.scope.api_base_path,
    ) != (TARGET.service_origin, TARGET.api_base_path):
        raise ValueError("exact historical resource and target required")
    key = BASE["HttpCredential"](
        "X-API-Key", SecretValue(value), target=TARGET, service_id="evren-platform"
    )
    end = time.monotonic() + 30
    driver = runpy.run_path(str(ROOT / "scripts/benchmark-upload.py"))
    before = driver["EVIDENCE"]["source"](ROOT)
    driver["STREAM"]["new_path"](args.output.parent).mkdir(mode=0o700)
    BASE["write"](args.output.parent / "started.json", {"source_commit": before["commit"]})
    if args.output.exists():
        raise ValueError("diagnostic output aliases the start marker")
    report: dict[str, Any] = {
        "schema_version": 1,
        "diagnostic_only": True,
        "outcome": "incomplete",
        "source_commit": before["commit"],
        "requests": [],
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "limits": {"get": 3, "attempts": 6, "response_bytes": 6_291_456, "seconds": 30},
        "authority_verified": False,
        "operation_mutated": False,
    }
    # Research queries use the ordinary P01 read port with the real guarded
    # backend. The production upload literal registry is left unchanged.
    session = HttpSession(
        transport_factory=lambda: HttpxTransport(transport=GuardedHttpTransport())
    )
    try:
        with session:
            session.call(lambda client: inspect(client, key, view, expected, report, end=end))
        if before != driver["EVIDENCE"]["source"](ROOT):
            raise ValueError("diagnostic source changed")
        report["outcome"] = "evidence_collected"
    except YorungeError as error:
        report["error_code"] = error.code
        raise
    finally:
        report["counters"] = {
            "logical_gets": len(report["requests"]),
            "physical_attempts_upper_bound": 2 * len(report["requests"]),
            "returned_body_bytes": sum(row["bytes"] for row in report["requests"]),
            "write_requests": 0,
        }
        BASE["write"](args.output, report)
    return report


def main() -> int:
    from yorunge.domain.errors import YorungeError

    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "credentials", "pilot", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--accept-read-diagnostic", action="store_true")
    args = parser.parse_args()
    try:
        run(args)
    except (
        YorungeError,
        OSError,
        ValueError,
        LookupError,
        TypeError,
        KeyboardInterrupt,
        SystemExit,
        asyncio.CancelledError,
        subprocess.SubprocessError,
    ):
        print("Read diagnostic stopped; preserve its safe receipt.", file=sys.stderr)
        return 1
    print("Read diagnostic completed; no write or operation transition was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
