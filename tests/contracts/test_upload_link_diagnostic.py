"""Bounded synthetic link research; never an account call or a replay permission."""

import asyncio
import json
import runpy
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.contracts.test_platform_upload_codec import (
    DATASET,
    OTHER,
    PARAMETERS,
    SCOPE,
    SECRET,
    dataset,
    encoded,
    located,
    project,
)
from yorunge.application import platform_upload_codec as codec
from yorunge.application.http_transport import HttpCredential, HttpStatusFailure
from yorunge.domain.capabilities import timestamp
from yorunge.domain.create_receipt import CreateReceiptV2
from yorunge.domain.errors import YorungeError

HELPER = runpy.run_path(str(Path(__file__).parents[2] / "scripts/upload_link_diagnostic.py"))


@pytest.mark.parametrize(
    "case",
    [
        "message",
        "standard",
        "already",
        "wrong_binding",
        "logical_false",
        "denied",
        "wrong_detail",
        "secret",
    ],
)
def test_link_probe_never_replays_and_only_records_closed_shape_predicates(case):
    calls = []
    expected = codec.created(encoded(dataset()), SCOPE, PARAMETERS, SECRET)
    link = {
        "dataset_id": DATASET,
        "project_id": SCOPE.project_id,
        "message": "private-link-message-canary",
    }
    if case == "standard":
        link["success"] = True
    if case == "wrong_binding":
        link["dataset_id"] = OTHER
    if case == "logical_false":
        link["success"] = False
    if case == "secret":
        link["unused-private-key-canary"] = SECRET.reveal()

    class Response:
        status_code = 200

        def __init__(self, data):
            self.data = data

        async def chunks(self):
            yield self.data

    class Client:
        @asynccontextmanager
        async def open(self, request, *, deadline):
            calls.append(request)
            if request.method == "POST":
                if case == "denied":
                    raise HttpStatusFailure(403)
                raw = link
            elif request.endpoint == "auth/me":
                raw = {"success": True, "data": {"id": SCOPE.owner.id}}
            elif request.endpoint == "projects/" + SCOPE.project_id:
                raw = project()
            elif request.endpoint == "datasets":
                listed = located()
                listed.pop("contributions_enabled")
                raw = [listed]
            elif request.endpoint.startswith("datasets/"):
                raw = dataset(owner_id=OTHER) if case == "wrong_detail" else dataset()
            else:
                raw = [{"id": DATASET}] if case == "already" or len(calls) == 7 else []
            yield Response(encoded(raw))

    key = HttpCredential("X-API-Key", SECRET, target=HELPER["TARGET"], service_id="evren-platform")
    view = SimpleNamespace(plan=SimpleNamespace(scope=SCOPE, parameters=PARAMETERS))
    report = {"requests": [], "outcome": "incomplete"}
    action = HELPER["probe"](Client(), key, view, expected, report)
    if case in ("message", "standard", "already"):
        asyncio.run(action)
        assert report["outcome"] == (
            "already_linked_no_post" if case == "already" else "evidence_collected"
        )
    else:
        with pytest.raises(YorungeError) as failure:
            asyncio.run(action)
        assert failure.value.code == (
            "remote_access_denied" if case == "denied" else "invalid_response"
        )
    assert len(calls) == {"message": 7, "standard": 7, "already": 5, "wrong_detail": 4}.get(case, 6)
    assert sum(request.method == "POST" for request in calls) == (
        0 if case in ("already", "wrong_detail") else 1
    )
    if case in ("message", "standard"):
        assert report["typed_ack_accepted"] is (case == "standard")
        assert report["membership_after"] is True
        assert report["link_shape"]["root"]["matches_expected"] == {
            "dataset_id": True,
            "project_id": True,
        }
    if case == "denied":
        assert report["requests"][-1]["status"] == 403
    public = json.dumps(report)
    for private in (
        DATASET,
        SCOPE.project_id,
        SCOPE.owner.id,
        SECRET.reveal(),
        "private-link-message-canary",
        "unused-private-key-canary",
    ):
        assert private not in public
    assert all(request.read_only == (request.method == "GET") for request in calls)
    assert all(request.max_bytes == 1_048_576 for request in calls)
    assert all(
        request.headers == (("Content-Type", "application/json"),)
        for request in calls
        if request.method == "POST"
    )


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"{",
        b'{"success":true,"success":false}',
        b'{"unknown-private-field":"private-value-canary","message":"private-value-canary"}',
    ],
)
def test_control_trace_has_no_free_field_names_values_or_exception_text(raw):
    shape = HELPER["TRACE"]["body_shape"](raw, {})
    text = json.dumps(shape)
    assert "private-value-canary" not in text
    assert "unknown-private-field" not in text
    assert "Traceback" not in text
    assert shape["json_valid"] is (raw.startswith(b'{"unknown'))


@pytest.mark.parametrize("case", ["existing_link", "active_owner", "wrong_project", "non_test"])
def test_link_probe_preflight_cannot_touch_an_existing_arm_owner_or_other_resource(
    tmp_path, monkeypatch, case
):
    namespace = HELPER["run"].__globals__
    receipt = CreateReceiptV2.model_validate_json(
        (Path(__file__).parents[1] / "fixtures/dataset-create-receipt-v2.json").read_bytes()
    )
    name = "ordinary-private-dataset" if case == "non_test" else "yorunge-acceptance-synthetic"
    receipt = receipt.model_copy(
        update={"created_dataset": receipt.created_dataset.model_copy(update={"name": name})}
    )
    lease = (
        SimpleNamespace(expires_at=timestamp(datetime.now(UTC) + timedelta(seconds=150)))
        if case == "active_owner"
        else None
    )
    view = SimpleNamespace(
        operation=SimpleNamespace(status="unknown", dataset_id=receipt.dataset_id, lease=lease),
        intents=[SimpleNamespace(kind="create")]
        + ([SimpleNamespace(kind="project_link")] if case == "existing_link" else []),
        receipts=[receipt],
        plan=SimpleNamespace(scope=SCOPE),
    )

    @contextmanager
    def store(*args):
        yield None

    monkeypatch.setitem(namespace, "sys", SimpleNamespace(flags=SimpleNamespace(isolated=True)))
    base = namespace["BASE"]
    monkeypatch.setitem(base, "credential", lambda *args: ("pilot", "synthetic-key"))
    monkeypatch.setitem(base, "private_file", lambda *args: b'{"operation_id":"private-op-canary"}')
    monkeypatch.setitem(base, "open_existing_store", store)
    monkeypatch.setitem(
        base, "StateUploads", lambda *args: SimpleNamespace(show=lambda **kwargs: view)
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("rejected preflight must not create a network session")

    import yorunge.adapters.http_session as sessions

    monkeypatch.setattr(sessions, "HttpSession", forbidden)
    args = SimpleNamespace(
        accept_link_probe=True,
        config=tmp_path / "config",
        credentials=tmp_path / "keys",
        pilot=tmp_path / "old",
        workspace=tmp_path / "new",
        project=OTHER if case == "wrong_project" else SCOPE.project_id,
    )
    with pytest.raises(ValueError):
        HELPER["run"](args)
    assert not args.workspace.exists()
