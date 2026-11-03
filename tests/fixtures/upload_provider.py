"""Stateful loopback provider oracle; never imported or selectable by product code."""

import json
from collections.abc import Callable
from dataclasses import dataclass

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
        self.linked = True
        return self.link_reply or reply({"success": True})

    def owned(self, request, count):
        if self.on_request:
            self.on_request()
        return reply(
            [{**self.dataset(), "owner_username": "test-user", "slug": "test-dataset"}]
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

        return {
            "/api/v1/auth/me": me,
            f"/api/v1/projects/{self.project_id}": project,
            "/api/v1/datasets": self.create,
            f"/api/v1/projects/{self.project_id}/datasets": self.link,
            "/api/v1/datasets?page=1&page_size=128&scope=owned": self.owned,
            "/api/v1/datasets/test-user/test-dataset": self.detail,
        }
