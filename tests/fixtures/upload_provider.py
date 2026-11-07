"""Stateful loopback provider oracle; never imported or selectable by product code."""

import hashlib
import json
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit
from uuid import uuid4

from tests.fixtures.http_server import Reply

DATASET = "00000000-0000-4000-8000-000000000909"


def reply(value, status=200):
    return Reply(status=status, body=json.dumps(value).encode())


@dataclass
class UploadProvider:
    owner_id: str
    project_id: str
    name: str = "sample"
    created: bool = False
    linked: bool = False
    create_calls: int = 0
    link_calls: int = 0
    create_reply: Reply | None = None
    link_reply: Reply | None = None
    after_create: Callable[[], None] | None = None
    wrong_detail_owner: bool = False
    on_request: Callable[[], None] | None = None
    duplicate_keys: bool = False
    upload_allowed: bool = True
    fail_put_name: str | None = None
    wrong_confirm_count: bool = False
    # Confirms handled before the count starts: the confirm reports the dataset's own count when 0
    # (what every confirm counts so far), and the operation's own count from this origin on.
    count_origin: int = 0
    # A file may be presigned again by a later operation (a continuation of an unconfirmed one).
    represign: bool = False
    after_put: Callable[[str], None] | None = None
    after_presign: Callable[[str], None] | None = None
    presign_calls: int = 0
    put_calls: int = 0
    confirm_calls: int = 0
    presigns: dict = field(default_factory=dict, repr=False)
    objects: dict = field(default_factory=dict, repr=False)
    confirmed: dict = field(default_factory=dict, repr=False)
    events: list[str] = field(default_factory=list)
    route_table: dict = field(default_factory=dict, repr=False)
    lock: object = field(default_factory=threading.Lock, repr=False)

    def dataset(self):
        return {
            "id": DATASET,
            "owner_id": self.owner_id,
            "org_id": None,
            "name": self.name,
            "modality": "VISION",
            "visibility": "private",
            "contributions_enabled": False,
        }

    def create(self, request, count):
        if self.on_request:
            self.on_request()
        self.create_calls += 1
        assert request.method == "POST" and not self.created
        body = json.loads(request.body)
        assert body["name"] == self.name and body["visibility"] == "private"
        assert body["contributions_enabled"] is False and "project_id" not in body
        self.events.append("create")
        self.created = True
        if self.after_create:
            self.after_create()
        return self.create_reply or reply({"success": True, "data": self.dataset()}, 201)

    def link(self, request, count):
        if self.on_request:
            self.on_request()
        if request.method == "GET":
            return reply([{"id": DATASET}] if self.linked else [])
        self.link_calls += 1
        assert request.method == "POST" and self.created and not self.linked
        assert json.loads(request.body) == {"dataset_id": DATASET}
        self.events.append("project_link")
        self.linked = True
        return self.link_reply or reply(
            {
                "project_id": self.project_id,
                "dataset_id": DATASET,
                "id": "00000000-0000-4000-8000-000000000098",
                "unconsumed": "fixture metadata",
            }
        )

    def owned(self, request, count):
        if self.on_request:
            self.on_request()
        listed = self.dataset()
        listed.pop("contributions_enabled")
        return reply(
            [{**listed, "owner_username": "test-user", "slug": "test-dataset"}]
            if self.created
            else []
        )

    def detail(self, request, count):
        if self.on_request:
            self.on_request()
        if not self.created:
            return reply({}, 404)
        value = self.dataset()
        if self.wrong_detail_owner:
            value["owner_id"] = "00000000-0000-4000-8000-000000000999"
        return reply(value)

    def presign(self, request, count):
        if self.on_request:
            self.on_request()
        assert request.method == "POST" and self.created and self.linked
        rows = json.loads(request.body)["files"]
        assert len(rows) == 1 and (self.represign or rows[0]["filename"] not in self.presigns)
        self.presign_calls += 1
        self.events.append("presign")
        row = dict(rows[0])
        key = "objects/shared" if self.duplicate_keys else f"objects/blob-{self.presign_calls}"
        row.update(
            object_key=key,
            upload_url=f"/datasets/{DATASET}/upload/put?" + urlencode({"key": key}),
            content_type="application/octet-stream",
        )
        self.presigns[row["filename"]] = row
        self.route_table["/api/v1" + row["upload_url"]] = self.put
        if self.after_presign:
            self.after_presign(row["filename"])
        return reply({"presigned_urls": [row], "duplicates": []})

    def put(self, request, count):
        if self.on_request:
            self.on_request()
        query = parse_qsl(urlsplit(request.path).query)
        assert request.method == "PUT" and len(query) == 1 and query[0][0] == "key"
        key = query[0][1]
        row = next(value for value in self.presigns.values() if value["object_key"] == key)
        with self.lock:
            self.put_calls += 1
            self.events.append("put")
        if (
            len(request.body) != row["file_size"]
            or hashlib.sha256(request.body).hexdigest() != row["sha256_hash"]
        ):
            return reply({"success": False}, 400)
        with self.lock:
            assert key not in self.objects
            self.objects[key] = request.body
        if self.after_put:
            self.after_put(row["filename"])
        return reply(
            {"ok": True, "size": len(request.body), "key": key},
            503 if row["filename"] == self.fail_put_name else 200,
        )

    def confirm(self, request, count):
        if self.on_request:
            self.on_request()
        body = json.loads(request.body)
        assert request.method == "POST" and body["skip_dedup"] is True and len(body["items"]) == 1
        item = body["items"][0]
        row = self.presigns[item["filename"]]
        assert item["object_key"] in self.objects and item["filename"] not in self.confirmed
        assert {key: item[key] for key in ("filename", "sha256_hash", "file_size")} == {
            key: row[key] for key in ("filename", "sha256_hash", "file_size")
        }
        self.confirm_calls += 1
        self.events.append("confirm")
        self.confirmed[item["filename"]] = {
            "id": str(uuid4()),
            "dataset_id": DATASET,
            "original_filename": item["filename"],
            "file_size_bytes": item["file_size"],
            "sha256_hash": item["sha256_hash"],
        }
        actual = self.confirm_calls - self.count_origin + int(self.wrong_confirm_count)
        return reply({"created": 1, "actual_count": actual, "batch_duplicates": 0})

    def role(self, request, count):
        if self.on_request:
            self.on_request()
        return reply(
            {
                "role": "owner",
                "permissions": ["read", "upload"] if self.upload_allowed else ["read"],
            }
        )

    def items(self, request, count):
        if self.on_request:
            self.on_request()
        return reply(
            {
                "items": list(self.confirmed.values()),
                "total": len(self.confirmed),
                "next_cursor": None,
            }
        )

    def routes(self):
        def me(request, count):
            if self.on_request:
                self.on_request()
            return reply({"success": True, "data": {"id": self.owner_id}})

        def project(request, count):
            if self.on_request:
                self.on_request()
            return reply(
                {
                    "id": self.project_id,
                    "owner_id": self.owner_id,
                    "org_id": None,
                    "visibility": "private",
                }
            )

        self.route_table = {
            "/api/v1/auth/me": me,
            f"/api/v1/projects/{self.project_id}": project,
            "/api/v1/datasets": self.create,
            f"/api/v1/projects/{self.project_id}/datasets": self.link,
            "/api/v1/datasets?page=1&page_size=20&scope=owned": self.owned,
            "/api/v1/datasets/test-user/test-dataset": self.detail,
            f"/api/v1/datasets/{DATASET}/my-role": self.role,
            f"/api/v1/datasets/{DATASET}/upload/presign": self.presign,
            f"/api/v1/datasets/{DATASET}/upload/confirm": self.confirm,
            f"/api/v1/datasets/{DATASET}/items?limit=128": self.items,
        }
        return self.route_table
