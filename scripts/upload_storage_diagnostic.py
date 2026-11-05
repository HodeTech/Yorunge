"""One fresh synthetic file's storage contract; never resume an old operation."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import runpy
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
LINK = runpy.run_path(str(ROOT / "scripts/upload_link_diagnostic.py"))
BASE, TRACE, codec, TARGET = LINK["BASE"], LINK["TRACE"], LINK["codec"], LINK["TARGET"]
DATASET_PREFIX = "datasets/"
FILES = {
    "first.png": "8f7eb0f9bebe51f1f6aceaf60bbb8e99a845b88e77cb86e0aaf66df9bb0b21aa",
    "same-content.png": "8f7eb0f9bebe51f1f6aceaf60bbb8e99a845b88e77cb86e0aaf66df9bb0b21aa",
    "different.png": "2ba82df1c51676319e2542bec023cc95fd9d594cc70b0d6b60cdaa9bafb77fd9",
}


class Probe:
    def __init__(
        self,
        client: Any,
        key: Any,
        view: Any,
        expected: Any,
        context: Any,
        manifest: Any,
        report: dict[str, Any],
        confirm: bool,
    ) -> None:
        self.client, self.key, self.view, self.expected = client, key, view, expected
        self.context, self.manifest, self.report, self.confirm = context, manifest, report, confirm
        self.end = time.monotonic() + 30

    async def exchange(
        self, kind: str, path: str, *, content: bytes = b"", query: Any = ()
    ) -> bytes:
        from yorunge.application.http_transport import HttpRequest, HttpStatusFailure
        from yorunge.domain.errors import YorungeError

        write = kind in {"presign", "confirm"}
        if (
            len(self.report["requests"]) >= 11
            or len(content) > 2048
            or (write and any(row["kind"] == kind for row in self.report["requests"]))
        ):
            raise YorungeError("upload_limit_exceeded")
        row: dict[str, Any] = {"kind": kind, "method": "POST" if write else "GET", "status": None}
        self.report["requests"].append(row)
        request = HttpRequest(
            TARGET,
            row["method"],
            path,
            query=query,
            content=content,
            headers=(("Content-Type", "application/json"),) if write else (),
            credential=self.key,
            service_id="evren-platform",
            read_only=not write,
            max_bytes=262_144,
        )
        try:
            async with self.client.open(request, deadline=self.end) as response:
                row["status"] = response.status_code
                raw = b"".join([part async for part in response.chunks()])
                row["body_bytes"] = len(raw)
                return raw
        except HttpStatusFailure as error:
            row["status"] = error.status_code
            raise

    async def inventory(self, label: str) -> Any:
        from yorunge.application import upload_metadata_codec as metadata
        from yorunge.domain.errors import YorungeError

        path = DATASET_PREFIX + codec.segment(self.expected.id, self.key.secret) + "/items"
        raw = await self.exchange(label, path, query=(("limit", "128"),))
        self.report[label + "_shape"] = TRACE["body_shape"](raw, {"dataset_id": self.expected.id})
        result = metadata.items(raw, self.expected.id, self.key.secret)
        originals = {file.path: file for file in self.manifest.files}
        if result.next_cursor is not None or result.total != len(result.items) or result.total > 3:
            raise YorungeError("invalid_response")
        for row in result.items:
            file = originals.get(row.original_filename)
            if file is None or (row.file_size_bytes, row.sha256_hash) != (file.size, file.sha256):
                raise YorungeError("invalid_response")
        return result

    async def put(self, upload: Any) -> bool:
        from yorunge.adapters.storage_source import DescriptorByteSource
        from yorunge.application import upload_metadata_codec as metadata
        from yorunge.application.http_transport import HttpStatusFailure
        from yorunge.application.storage import StorageRequest
        from yorunge.domain.errors import YorungeError

        file = self.context.file
        source = DescriptorByteSource(self.view.plan.root, file, deadline=self.end)
        request = StorageRequest(
            upload.target, source, self.key.secret, upload.content_type, credential=self.key
        )
        row: dict[str, Any] = {"kind": "put", "method": "PUT", "status": None}
        self.report["requests"].append(row)
        try:
            async with self.client.open_storage(request, deadline=self.end) as response:
                row["status"] = response.status_code
                raw = b"".join([part async for part in response.chunks()])
                row["body_bytes"] = len(raw)
                sent = response.sent_bytes, response.sent_sha256
            self.report["sent_bytes"] = sent[0]
            self.report["source_sent_matches"] = (
                source.complete is True
                and sent == (file.size, file.sha256)
                and (source.sent_bytes, source.sent_sha256) == sent
            )
            if not self.report["source_sent_matches"]:
                raise YorungeError("input_changed")
            self.report["put_shape"] = TRACE["body_shape"](
                raw,
                {
                    "object_key": upload.provider_key.reveal(),
                    "key": upload.provider_key.reveal(),
                    "size": file.size,
                    "file_size": file.size,
                    "bytes_written": file.size,
                    "sha256_hash": file.sha256,
                },
            )
            try:
                metadata.put_ack(
                    raw, self.key.secret, expected_size=file.size, expected_key=upload.provider_key
                )
            except YorungeError as error:
                self.report.update(
                    typed_put_ack_accepted=False, typed_put_ack_error_code=error.code
                )
                return False
            self.report["typed_put_ack_accepted"] = True
            return True
        except HttpStatusFailure as error:
            row["status"] = error.status_code
            raise
        finally:
            await source.aclose()

    async def confirm_upload(self, upload: Any, before: Any) -> None:
        from yorunge.application import upload_descriptors as descriptors
        from yorunge.application import upload_metadata_codec as metadata
        from yorunge.domain.errors import YorungeError

        path = DATASET_PREFIX + codec.segment(self.expected.id, self.key.secret) + "/upload/confirm"
        raw = await self.exchange(
            "confirm",
            path,
            content=descriptors.confirm_content(upload, self.context, self.key.secret),
        )
        self.report["confirm_shape"] = TRACE["body_shape"](
            raw, {"created": 1, "actual_count": before.total + 1, "batch_duplicates": 0}
        )
        # Explicit negatives/malformed controls never open another step. The two
        # bounded counter candidates are observation predicates, not product policy.
        codec._ack_controls(codec._object(codec.raw(raw, "confirm", self.key.secret)), None)
        candidates = {}
        for label, count in (("current", before.total + 1), ("one", 1)):
            try:
                metadata.confirm_ack(raw, count, self.key.secret)
                candidates[label] = True
            except YorungeError:
                candidates[label] = False
        self.report["confirm_candidates"] = candidates
        if not any(candidates.values()):
            return
        after = await self.inventory("items_after")
        self.report["item_count_after"] = after.total
        self.report["new_file_metadata_matches"] = (
            after.total == before.total + 1
            and sum(row.original_filename == self.context.file.path for row in after.items) == 1
        )

    async def run(self) -> None:
        from yorunge.adapters.upload_input_files import capture_upload_input
        from yorunge.application import upload_descriptors as descriptors
        from yorunge.domain.errors import YorungeError

        observed = capture_upload_input(
            Path(self.view.plan.root.anchor),
            self.manifest,
            self.key.secret,
            end=self.end,
            expected_root=self.view.plan.root,
        )
        _, linked = await LINK["inspect_context"](self.exchange, self.key, self.view, self.expected)
        if not linked:
            raise YorungeError("invalid_response")
        role_path = DATASET_PREFIX + codec.segment(self.expected.id, self.key.secret) + "/my-role"
        codec.role(await self.exchange("role", role_path), self.key.secret)
        self.report["upload_label_observed"] = True
        before = await self.inventory("items_before")
        if before.total > 2 or any(
            row.original_filename == self.context.file.path for row in before.items
        ):
            raise YorungeError("invalid_response")
        self.report["item_count_before"] = before.total
        observed.recheck()
        path = DATASET_PREFIX + codec.segment(self.expected.id, self.key.secret) + "/upload/presign"
        raw = await self.exchange(
            "presign", path, content=descriptors.presign_content(self.context, self.key.secret)
        )
        self.report["presign_shape"] = TRACE["body_shape"](raw, {})
        upload = descriptors.presigned(raw, self.context, self.key.secret)
        observed.recheck()
        if await self.put(upload) and self.confirm:
            observed.recheck()
            await self.confirm_upload(upload, before)
        self.report["outcome"] = "evidence_collected"


def run(args: argparse.Namespace) -> None:
    from yorunge.adapters.storage_transport import TransferSession
    from yorunge.application import upload_descriptors as descriptors
    from yorunge.domain.dataset_manifest import DatasetManifest
    from yorunge.domain.errors import YorungeError

    if not sys.flags.isolated or not args.accept_storage_probe:
        raise ValueError("isolated runtime and storage-probe authorization required")
    view, expected, key = LINK["historical_context"](args)
    manifest = DatasetManifest.model_validate_json(
        BASE["private_file"](args.pilot / "manifest.json")
    )
    if {file.path: (file.size, file.sha256) for file in manifest.files} != {
        name: (79, digest) for name, digest in FILES.items()
    }:
        raise ValueError("only the three original synthetic PNGs may be used")
    contexts = descriptors.contexts(view.plan, manifest, str(uuid4()), expected.id, key.secret)
    context = next(value for value in contexts if value.file.path == args.file)
    driver = runpy.run_path(str(ROOT / "scripts/benchmark-upload.py"))
    before = driver["EVIDENCE"]["source"](ROOT)
    driver["STREAM"]["new_path"](args.workspace).mkdir(mode=0o700)
    BASE["write"](
        args.workspace / "started.json",
        {"source_commit": before["commit"], "file_index": context.file_index},
    )
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
        "file_index": context.file_index,
        "requests": [],
        "operation_mutated": False,
        "authority_verified": False,
        "remote_bytes_verified": False,
        "limits": {
            "get": 8,
            "presign": 1,
            "put": 1,
            "confirm": int(args.confirm),
            "attempts": 19,
            "response_bytes": 5_242_880,
            "control_request_bytes": 4096,
            "upload_bytes": 79,
            "seconds": 30,
        },
    }
    completed = False
    try:
        session = TransferSession(key)
        with session:
            session.exchange(
                lambda client: Probe(
                    client, key, view, expected, context, manifest, report, args.confirm
                ).run()
            )
        if before != driver["EVIDENCE"]["source"](ROOT):
            raise ValueError("storage diagnostic source changed")
        completed = True
    except YorungeError as error:
        report["error_code"] = error.code
        raise
    finally:
        if not completed:
            report["outcome"] = "incomplete"
        BASE["write"](args.workspace / "receipt.json", report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "credentials", "pilot", "workspace"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--project", required=True)
    parser.add_argument("--file", required=True, choices=tuple(FILES))
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--accept-storage-probe", action="store_true")
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
        print("Storage diagnostic stopped; preserve its safe receipt.", file=sys.stderr)
        return 1
    print("Storage diagnostic completed; no create, link or operation transition was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
