"""One authorized research attempt; no public grant, price proof, replay or cleanup."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import struct
import subprocess
import time
import tomllib
import uuid
import zlib
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from yorunge.adapters.guarded_http import GuardedHttpTransport
from yorunge.adapters.storage_source import DescriptorByteSource
from yorunge.adapters.storage_transport import TransferHttpxTransport, TransferSession
from yorunge.application.http_transport import HttpCredential, HttpRequest, HttpStatusFailure
from yorunge.application.response_json import literal_secret_match, parse_json
from yorunge.application.storage import StorageRequest, StorageTarget
from yorunge.domain.credentials import SecretValue, normalize_target
from yorunge.domain.dataset_manifest import DatasetFile, safe_text
from yorunge.domain.dataset_upload import UploadRoot, provider_uuid
from yorunge.domain.errors import YorungeError

ROOT = Path(__file__).resolve().parents[4]
PREP = ROOT / ".local/p02-pilot"
WORK = PREP / "p02-2-write-20261102"
TARGET = normalize_target("https://api.ssyz.org.tr/api/v1")
MAX_RESPONSE, MAX_TOTAL = 512 * 1024, 5 * 1024 * 1024
FIELDS = frozenset(
    {
        "success",
        "data",
        "message",
        "id",
        "org_id",
        "owner_id",
        "name",
        "visibility",
        "modality",
        "contributions_enabled",
        "role",
        "permissions",
        "presigned_urls",
        "duplicates",
        "upload_url",
        "direct_upload_url",
        "object_key",
        "filename",
        "client_uid",
        "sha256_hash",
        "file_size",
        "content_type",
        "items",
        "next_cursor",
        "total",
        "dataset_id",
        "original_filename",
        "file_size_bytes",
        "created",
        "actual_count",
        "batch_duplicates",
    }
)


def encoded(value):
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def checked_id(value, secret):
    if type(value) is not str:
        raise YorungeError("invalid_response")
    try:
        provider_uuid(value)
    except ValueError:
        raise YorungeError("invalid_response") from None
    if literal_secret_match(value, secret.reveal()):
        raise YorungeError("invalid_response")
    return value


def raw_safe(value, secret):
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is str and literal_secret_match(item, secret.reveal()):
            raise YorungeError("invalid_response")
        if type(item) is dict:
            pending.extend(key for key in item if key not in FIELDS)
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)


def payload(raw, secret):
    raw_safe(raw, secret)
    if type(raw) is dict:
        if "success" in raw and raw["success"] is not True:
            raise YorungeError("invalid_response")
        if "data" in raw:
            inner = raw["data"]
            if type(inner) is dict and "success" in inner and inner["success"] is not True:
                raise YorungeError("invalid_response")
            return inner
    return raw


def object_value(value):
    if type(value) is not dict:
        raise YorungeError("invalid_response")
    return value


def shape(value, depth=0):
    if type(value) is dict:
        return {
            "type": "object",
            "fields": {
                key: shape(child, depth + 1)
                for key, child in value.items()
                if key in FIELDS and depth < 4
            },
        }
    if type(value) is list:
        variants = (
            {json.dumps(shape(child, depth + 1), sort_keys=True) for child in value}
            if depth < 4
            else set()
        )
        return {
            "type": "array",
            "count": len(value),
            "shapes": [json.loads(item) for item in sorted(variants)],
        }
    return {"type": type(value).__name__}


def png(rgb):
    def chunk(kind, data):
        return (
            struct.pack("!I", len(data)) + kind + data + struct.pack("!I", zlib.crc32(kind + data))
        )

    header = struct.pack("!IIBBBBB", 16, 16, 8, 2, 0, 0, 0)
    pixels = (b"\0" + bytes(rgb) * 16) * 16
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(pixels))
        + chunk(b"IEND", b"")
    )


def fixtures():
    first, other = png((20, 80, 160)), png((180, 60, 20))
    return (("first.png", first), ("same-content.png", first), ("different.png", other))


class Ledger:
    def __init__(self, root, project):
        info = root.parent.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700
        ):
            raise YorungeError("invalid_request")
        root.mkdir(mode=0o700)  # Exclusive forever, including an uncertain prior run.
        descriptor = os.open(
            root / "journal.jsonl", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        self.output = os.fdopen(descriptor, "wb")
        self.intents, self.root = set(), root
        self.append({"event": "reserved", "project_id": project, "operation_id": str(uuid.uuid4())})
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        parent = os.open(root.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)

    def append(self, row):
        data = encoded(row)
        if len(data) > 8192:
            raise YorungeError("invalid_request")
        self.output.write(data)
        self.output.flush()
        os.fsync(self.output.fileno())

    def intent(self, stage):
        if stage in self.intents or len(self.intents) >= 11:
            raise YorungeError("invalid_request")
        self.intents.add(stage)
        self.append({"event": "intent", "stage": stage})

    def close(self):
        self.output.close()


class BudgetStream(httpx.AsyncByteStream):
    def __init__(self, wrapped, budget, limit):
        self.wrapped, self.budget, self.limit = wrapped, budget, limit

    async def __aiter__(self):
        count = 0
        async for chunk in self.wrapped:
            count += len(chunk)
            self.budget.body_bytes += len(chunk)
            if count > self.limit or self.budget.body_bytes > MAX_TOTAL:
                raise YorungeError("invalid_response")
            yield chunk

    async def aclose(self):
        await self.wrapped.aclose()


class BudgetTransport(httpx.AsyncBaseTransport):
    def __init__(self, key, delegate, project):
        self.key, self.delegate, self.project = key, delegate, project
        self.dataset = None
        self.effect_counts = {}
        self.end = time.monotonic() + 120
        self.active = None
        self.attempts = self.read_attempts = self.effects = self.body_bytes = self.per_call = 0

    def select(self, method, url, size):
        if self.route(method, url) is None or type(size) is not int or size < 0:
            raise YorungeError("invalid_request")
        self.active, self.per_call = (method, url, size), 0

    def bind_dataset(self, identifier):
        identifier = checked_id(identifier, self.key.secret)
        if self.dataset is not None:
            raise YorungeError("invalid_request")
        self.dataset = identifier

    def route(self, method, url):
        base = TARGET.service_origin + TARGET.api_base_path.rstrip("/") + "/"
        fixed = {
            ("GET", f"projects/{self.project}"): ("read", 20),
            ("POST", "datasets"): ("create", 1),
            ("POST", f"projects/{self.project}/datasets"): ("link", 1),
            ("GET", f"projects/{self.project}/datasets"): ("read", 20),
        }
        if type(url) is not str or not url.startswith(base):
            return None
        suffix = url[len(base) :]
        if self.dataset is not None:
            prefix = f"datasets/{self.dataset}"
            fixed.update(
                {
                    ("GET", prefix): ("read", 20),
                    ("GET", prefix + "/my-role"): ("read", 20),
                    ("GET", prefix + "/items?limit=10"): ("read", 20),
                    ("POST", prefix + "/upload/presign"): ("presign", 3),
                    ("POST", prefix + "/upload/confirm"): ("confirm", 3),
                }
            )
            if method == "PUT" and suffix.startswith(prefix + "/upload/put?"):
                return ("put", 3)
        return fixed.get((method, suffix))

    async def handle_async_request(self, request):
        route = self.route(request.method, str(request.url))
        if route is None:
            raise YorungeError("invalid_request")
        group, maximum = route
        expected = (
            request.method,
            str(request.url),
            int(request.headers.get("content-length", "0")),
        )
        read = request.method == "GET"
        if (
            expected != self.active
            or time.monotonic() >= self.end
            or self.per_call >= (2 if read else 1)
            or request.headers.get("X-API-Key") != self.key.secret.reveal()
            or any(
                name in request.headers
                for name in ("cookie", "authorization", "proxy-authorization", "transfer-encoding")
            )
            or (read and self.read_attempts >= 20)
            or (not read and self.effects >= 11)
            or (not read and self.effect_counts.get(group, 0) >= maximum)
        ):
            raise YorungeError("invalid_request")
        self.per_call += 1
        self.attempts += 1
        self.read_attempts += int(read)
        self.effects += int(not read)
        if not read:
            self.effect_counts[group] = self.effect_counts.get(group, 0) + 1
        response = await self.delegate.handle_async_request(request)
        response.stream = BudgetStream(
            response.stream, self, 65536 if request.method == "PUT" else MAX_RESPONSE
        )
        return response

    async def aclose(self):
        await self.delegate.aclose()


class Pilot:
    def __init__(self, key, budget, ledger, project):
        self.key, self.budget, self.ledger, self.project = key, budget, ledger, project
        self.reads, self.rows = 0, []
        self.dataset = None
        self.images = fixtures()
        if len(self.images) != 3 or sum(len(data) for _, data in self.images) > 1024 * 1024:
            raise YorungeError("invalid_request")

    async def json(self, transport, stage, method, path, body=None, query=()):
        read = method == "GET"
        if read:
            self.reads += 1
            if self.reads > 10:
                raise YorungeError("invalid_request")
        else:
            self.ledger.intent(stage)
        content = b"" if body is None else encoded(body)
        raw_safe(body, self.key.secret)
        request = HttpRequest(
            TARGET,
            method,
            path,
            content=content,
            query=query,
            headers=() if not content else (("Content-Type", "application/json"),),
            credential=self.key,
            service_id="evren-platform",
            read_only=read,
            max_bytes=MAX_RESPONSE,
        )
        self.budget.select(method, request.url, len(content))
        row = {"stage": stage}
        self.rows.append(row)
        async with transport.open(request, deadline=self.budget.end) as response:
            row["status"] = response.status_code
            data = b"".join([part async for part in response.chunks()])
        row["body_bytes"] = len(data)
        self.ledger.append({"event": "acknowledged_http", **row})
        if not data:
            return None
        raw = parse_json(data, max_bytes=MAX_RESPONSE)
        raw_safe(raw, self.key.secret)
        row["shape"] = shape(raw)
        return payload(raw, self.key.secret)

    async def _create(self, transport):
        secret = self.key.secret
        project = object_value(
            await self.json(transport, "project", "GET", f"projects/{self.project}")
        )
        if (
            checked_id(project.get("id"), secret) != self.project
            or project.get("visibility") != "private"
        ):
            raise YorungeError("invalid_response")
        owner = checked_id(project.get("owner_id"), secret)
        org = project.get("org_id")
        if org is not None:
            org = checked_id(org, secret)
        name = "yorunge-upload-pilot-" + uuid.uuid4().hex[:12]
        body = {
            "name": name,
            "modality": "VISION",
            "visibility": "private",
            "contributions_enabled": False,
            "tags": [],
        }
        if org is not None:
            body["org_id"] = org
        created = object_value(await self.json(transport, "create", "POST", "datasets", body))
        self.dataset = checked_id(created.get("id"), secret)
        self.budget.bind_dataset(self.dataset)
        self.ledger.append({"event": "dataset_known", "dataset_id": self.dataset})
        prefix = f"datasets/{self.dataset}"
        detail = object_value(await self.json(transport, "dataset", "GET", prefix))
        if (
            checked_id(detail.get("id"), secret) != self.dataset
            or detail.get("name") != name
            or detail.get("visibility") != "private"
            or detail.get("org_id") != org
            or (org is None and checked_id(detail.get("owner_id"), secret) != owner)
        ):
            raise YorungeError("invalid_response")
        role = object_value(await self.json(transport, "role", "GET", prefix + "/my-role"))
        permissions = role.get("permissions")
        if (
            type(permissions) is not list
            or not all(type(value) is str for value in permissions)
            or "upload" not in permissions
        ):
            raise YorungeError("remote_access_denied")

    async def _link(self, transport):
        await self.json(
            transport,
            "link",
            "POST",
            f"projects/{self.project}/datasets",
            {"dataset_id": self.dataset},
        )
        linked = await self.json(transport, "linked", "GET", f"projects/{self.project}/datasets")
        if (
            type(linked) is not list
            or len(linked) > 128
            or sum(type(item) is dict and item.get("id") == self.dataset for item in linked) != 1
        ):
            raise YorungeError("invalid_response")

    def _descriptor(self, presign, info):
        urls = presign.get("presigned_urls")
        if type(urls) is not list or len(urls) != 1 or presign.get("duplicates", []) != []:
            raise YorungeError("invalid_response")
        descriptor = object_value(urls[0])
        if any(descriptor.get(field) != info[field] for field in ("filename", "sha256_hash")):
            raise YorungeError("invalid_response")
        if descriptor.get("client_uid", info["client_uid"]) != info["client_uid"]:
            raise YorungeError("invalid_response")
        object_key, upload_url = descriptor.get("object_key"), descriptor.get("upload_url")
        if (
            type(object_key) is not str
            or not 1 <= len(object_key) <= 2048
            or type(upload_url) is not str
        ):
            raise YorungeError("invalid_response")
        safe_text(object_key)
        # Select the provider's explicit proxy descriptor; never try/fallback from direct.
        if upload_url.startswith("/") and not upload_url.startswith("//"):
            upload_url = TARGET.service_origin + upload_url
        route = TARGET.api_base_path.rstrip("/") + f"/datasets/{self.dataset}/upload/"
        target = StorageTarget(
            upload_url,
            mode="proxy",
            origin=TARGET.service_origin,
            prefix=route,
            expires_at=None,
            service=TARGET,
            dataset_id=self.dataset,
        )
        if urlsplit(upload_url).path != route + "put":
            raise YorungeError("invalid_service_target")
        return object_key, target

    async def _presign(self, transport):
        prefix = f"datasets/{self.dataset}"
        files = self.ledger.root / "images"
        files.mkdir(mode=0o700)
        descriptors = []
        for index, (filename, data) in enumerate(self.images):
            with (files / filename).open("xb") as output:
                output.write(data)
            sha = hashlib.sha256(data).hexdigest()
            info = {
                "filename": filename,
                "sha256_hash": sha,
                "file_size": len(data),
                "client_uid": str(uuid.uuid4()),
            }
            presign = object_value(
                await self.json(
                    transport,
                    f"presign_{index}",
                    "POST",
                    prefix + "/upload/presign",
                    {"files": [info]},
                )
            )
            object_key, target = self._descriptor(presign, info)
            descriptors.append((index, info, object_key, target))
        return files, descriptors

    async def _upload(self, transport, files, descriptors):
        secret, prefix = self.key.secret, f"datasets/{self.dataset}"
        for index, info, object_key, target in descriptors:
            metadata = files.stat()
            source = DescriptorByteSource(
                UploadRoot(
                    anchor=str(files.resolve()), device=metadata.st_dev, inode=metadata.st_ino
                ),
                DatasetFile(
                    path=info["filename"], size=info["file_size"], sha256=info["sha256_hash"]
                ),
                deadline=self.budget.end,
            )
            request = StorageRequest(target, source, secret, "image/png", credential=self.key)
            stage = f"put_{index}"
            self.ledger.intent(stage)
            self.budget.select("PUT", target.wire_url, source.size)
            row = {"stage": stage}
            self.rows.append(row)
            async with transport.open_storage(request, deadline=self.budget.end) as response:
                row["status"] = response.status_code
                data = b"".join([part async for part in response.chunks()])
                row["sent_bytes"] = response.sent_bytes
                if response.sent_sha256 != info["sha256_hash"]:
                    raise YorungeError("input_changed")
            if data:
                payload(parse_json(data, max_bytes=65536), secret)
            self.ledger.append({"event": "acknowledged_http", **row})
            item = {key: info[key] for key in ("filename", "sha256_hash", "file_size")}
            item["object_key"] = object_key
            await self.json(
                transport,
                f"confirm_{index}",
                "POST",
                prefix + "/upload/confirm",
                {"items": [item], "skip_dedup": True},
            )

    async def _verify(self, transport):
        secret, prefix = self.key.secret, f"datasets/{self.dataset}"
        listing = object_value(
            await self.json(transport, "items", "GET", prefix + "/items", query=(("limit", "10"),))
        )
        items = listing.get("items")
        if type(items) is not list or len(items) != 3 or listing.get("next_cursor") is not None:
            raise YorungeError("invalid_response")
        expected = {
            (name, len(data), hashlib.sha256(data).hexdigest()) for name, data in self.images
        }
        actual, ids = set(), set()
        for item in items:
            item = object_value(item)
            ids.add(checked_id(item.get("id"), secret))
            if (
                item.get("dataset_id") != self.dataset
                or type(item.get("file_size_bytes")) is not int
            ):
                raise YorungeError("invalid_response")
            actual.add(
                (item.get("original_filename"), item["file_size_bytes"], item.get("sha256_hash"))
            )
        if actual != expected or len(ids) != 3:
            raise YorungeError("invalid_response")
        return {
            "private_dataset_observed": True,
            "project_link_observed": True,
            "three_named_files_metadata_match": True,
            "remote_bytes_verified": False,
            "authority_verified": False,
            "pricing_verified": False,
        }

    async def run(self, transport):
        await self._create(transport)
        await self._link(transport)
        files, descriptors = await self._presign(transport)
        await self._upload(transport, files, descriptors)
        return await self._verify(transport)


def private_bytes(path):
    ancestor = path.parent.parent.lstat()
    if not stat.S_ISDIR(ancestor.st_mode) or ancestor.st_uid != os.getuid():
        raise YorungeError("invalid_request")
    parent = path.parent.lstat()
    if (
        not stat.S_ISDIR(parent.st_mode)
        or parent.st_uid != os.getuid()
        or stat.S_IMODE(parent.st_mode) != 0o700
    ):
        raise YorungeError("invalid_request")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size > 65536
        ):
            raise YorungeError("invalid_request")
        data = stream.read(65537)
        if len(data) > 65536:
            raise YorungeError("invalid_request")
        return data


def execute(project):
    os.umask(0o077)
    provider_uuid(project)
    if Path.cwd().resolve() != ROOT:
        raise YorungeError("invalid_request")
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if subprocess.run(["git", "diff", "--quiet", "HEAD"], cwd=ROOT).returncode != 0:
        raise YorungeError("invalid_request")
    probe_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    test_hash = hashlib.sha256(Path(__file__).with_name("test_pilot.py").read_bytes()).hexdigest()
    values = parse_json(private_bytes(PREP / "credentials.json"), max_bytes=65536)
    config = tomllib.loads(private_bytes(PREP / "config.toml").decode("utf-8", "strict"))
    profile = config["profiles"]["pilot"]
    if (
        normalize_target(profile["platform_url"]) != TARGET
        or profile["platform_key_env"] != "PILOT_PLATFORM_KEY"
    ):
        raise YorungeError("invalid_service_target")
    secret = SecretValue(values["PILOT_PLATFORM_KEY"])
    checked_id(project, secret)
    del values
    key = HttpCredential("X-API-Key", secret, target=TARGET, service_id="evren-platform")
    ledger = Ledger(WORK, project)
    budget = BudgetTransport(key, GuardedHttpTransport(), project)
    pilot = Pilot(key, budget, ledger, project)
    started = time.monotonic()
    report = {
        "schema_version": 1,
        "outcome": "stopped",
        "authority_verified": False,
        "pricing_verified": False,
    }
    try:
        with TransferSession(
            key, transport_factory=lambda: TransferHttpxTransport(key, transport=budget)
        ) as session:
            report.update(session.exchange(pilot.run))
        report["outcome"] = "completed_observations"
    except HttpStatusFailure as error:
        report.update(error_code=error.code, http_status=error.status_code)
    except YorungeError as error:
        report["error_code"] = error.code
    finally:
        report.update(
            rows=pilot.rows,
            attempts=budget.attempts,
            read_requests=pilot.reads,
            effectful_requests=budget.effects,
            consumed_body_bytes=budget.body_bytes,
            elapsed_seconds=time.monotonic() - started,
            source_commit=source,
            probe_sha256=probe_hash,
            test_sha256=test_hash,
            source_unchanged=(
                subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
                == source
                and subprocess.run(["git", "diff", "--quiet", "HEAD"], cwd=ROOT).returncode == 0
            ),
            fixture_bytes=sum(len(data) for _, data in fixtures()),
        )
        ledger.append({"event": "finished", "outcome": report["outcome"]})
        ledger.close()
        receipt = WORK / "receipt.json"
        with receipt.open("xb") as output:
            output.write(encoded(report))
            output.flush()
            os.fsync(output.fileno())
    print(
        json.dumps(
            {
                key: report[key]
                for key in ("outcome", "attempts", "effectful_requests", "consumed_body_bytes")
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(
        description="One specifically authorized private research pilot."
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--execute", action="store_true", required=True)
    args = parser.parse_args()
    try:
        execute(args.project)
    except Exception:
        # Terminal research envelope: unforeseen errors must not print private tracebacks.
        raise SystemExit(
            "Pilot stopped; private inputs and raw exceptions were not printed."
        ) from None
    except KeyboardInterrupt:
        raise SystemExit(
            "Pilot interrupted; inspect the private journal without replaying."
        ) from None


if __name__ == "__main__":
    main()
