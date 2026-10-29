"""Real local query contract: request boundaries, cursor, CLI and historical states."""

import base64
import json
from uuid import uuid4

import pytest

from tests.fixtures.operation_backend import ReadObserver
from yorunge import api
from yorunge.adapters.state import open_store
from yorunge.domain.capabilities import canonical
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.jobs import JobsCursor


@pytest.mark.parametrize(
    "arguments",
    [
        {"limit": True},
        {"limit": 1.0},
        {"limit": "1"},
        {"limit": 0},
        {"limit": 101},
        {"status": "complete"},
        {"status": True},
        {"plan_id": "12345678-1234-4234-9234-123456789ABC"},
        {"plan_id": 1},
        {"plan_id": "unknown"},
        {"cursor": True},
        {"cursor": b"abcd"},
        {"cursor": ""},
        {"cursor": "a" * 1025},
        {"cursor": "🌍"},
        {"cursor": "not-base64"},
    ],
)
def test_invalid_list_request_is_rejected_before_state_access(tmp_path, arguments):
    state = tmp_path / "new-state"
    with pytest.raises(YorungeError) as error:
        api.list_jobs(state_dir=state, **arguments)
    assert error.value.code == "invalid_request"
    assert not state.exists()


@pytest.mark.parametrize(
    "identifier", [None, True, 1, "unknown", "12345678-1234-4234-9234-123456789ABC"]
)
def test_show_uuid_is_strict_before_state_access(tmp_path, identifier):
    state = tmp_path / "new-state"
    with pytest.raises(YorungeError) as error:
        api.show_job(identifier, state_dir=state)
    assert error.value.code == "invalid_request"
    assert not state.exists()


@pytest.mark.parametrize("action", ["list", "show"])
def test_jobs_paths_and_unsupported_platform_are_controlled(tmp_path, monkeypatch, action):
    invoke = api.list_jobs if action == "list" else lambda **kw: api.show_job(str(uuid4()), **kw)
    with pytest.raises(YorungeError) as error:
        invoke(state_dir=str(tmp_path))
    assert error.value.code == "invalid_request"
    monkeypatch.setattr("sys.platform", "win32")
    with pytest.raises(YorungeError) as error:
        invoke(state_dir=tmp_path / "state")
    assert error.value.code == "state_unsupported"


CURSOR = dict(
    version=1,
    store_id="12345678-1234-4234-9234-123456789abc",
    status=None,
    plan_id=None,
    created_at="2026-10-29T12:34:56.123456Z",
    operation_id="87654321-4321-4321-8321-cba987654321",
)


@pytest.mark.parametrize(
    "payload",
    [
        canonical({**CURSOR, "version": True}),
        canonical({**CURSOR, "version": 1.0}),
        canonical({**CURSOR, "version": 2}),
        canonical({**CURSOR, "extra": 0}),
        canonical({**CURSOR, "store_id": "other"}),
        canonical({**CURSOR, "status": "complete"}),
        canonical({**CURSOR, "created_at": "2026-02-30T12:34:56.123456Z"}),
        canonical({**CURSOR, "operation_id": CURSOR["operation_id"].upper()}),
        canonical({name: value for name, value in CURSOR.items() if name != "plan_id"}),
        b'{"version":1,' + canonical(CURSOR)[1:],
        b"\xff",
        b"[]",
        b"NaN",
        json.dumps(CURSOR, indent=2).encode(),
    ],
)
def test_cursor_closed_canonical_format_rejects_invalid_payload(payload):
    cursor = base64.urlsafe_b64encode(payload).decode()
    with pytest.raises(YorungeError) as error:
        JobsCursor.decode(cursor)
    assert error.value.code == "invalid_request"


def test_cursor_canonical_padding_and_roundtrip():
    value = JobsCursor.model_validate(CURSOR)
    cursor = value.encoded()
    assert JobsCursor.decode(cursor) == value
    for wrong in (cursor + "=", " " + cursor, cursor + "\n", cursor.rstrip("=") + "!"):
        with pytest.raises(YorungeError) as error:
            JobsCursor.decode(wrong)
        assert error.value.code == "invalid_request"


def test_empty_store_plan_only_and_unknown_id_have_distinct_results(operation_setup, cli):
    state, plan, _ = operation_setup
    result = api.list_jobs(state_dir=state)
    assert result.status == "completed"
    assert result.operation_id is None
    assert result.data.jobs == ()
    assert result.data.next_cursor is None
    assert result.warnings == ("local_history_only",)
    assert api.list_jobs(plan_id=plan.plan_id, state_dir=state).data.jobs == ()
    assert api.list_jobs(plan_id=str(uuid4()), state_dir=state).data.jobs == ()
    identifier = str(uuid4())
    with pytest.raises(OperationError) as error:
        api.show_job(identifier, state_dir=state)
    assert error.value.code == "operation_not_found"
    assert error.value.operation_id == identifier
    result = cli(
        "jobs",
        "show",
        "--operation-id",
        identifier,
        "--state-dir",
        str(state),
        "--output",
        "json",
        state=True,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.count("\n") == 1
    assert json.loads(result.stderr) == error.value.envelope()


@pytest.mark.parametrize(
    "status", ["admitted", "submitted", "running", "unknown", "succeeded", "failed", "cancelled"]
)
def test_cli_python_and_text_show_same_historical_state(
    operation_setup, execution_clock, cli, status
):
    state, plan, backend = operation_setup
    observer = ReadObserver(execution_clock)
    with api._operation_session(
        plan.plan_id, backend, observer=observer, state_dir=state
    ) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        if status != "admitted":
            coordinator.dispatch(identifier, claim.ownership)
        if status not in {"admitted", "submitted"}:
            if status == "unknown":
                observer.kind = "not_found"
            else:
                observer.execution = status
                observer.delivery = "complete" if status == "succeeded" else "pending"
            coordinator.reconcile(identifier, claim.ownership)
    expected = api.show_job(identifier, state_dir=state)
    assert expected.data.operation.status == status
    assert expected.status == "completed"
    assert expected.operation_id is None
    assert expected.warnings == ("local_history_only",)
    shown = cli(
        "jobs",
        "show",
        "--operation-id",
        identifier,
        "--state-dir",
        str(state),
        "--output",
        "json",
        state=True,
        recipe_loader=False,
    )
    assert shown.returncode == 0, shown.stderr
    assert shown.stderr == ""
    assert json.loads(shown.stdout) == expected.model_dump(mode="json")
    listed = cli(
        "jobs",
        "--state-dir",
        str(state),
        "--output",
        "json",
        "list",
        "--status",
        status,
        state=True,
        recipe_loader=False,
    )
    assert listed.returncode == 0, listed.stderr
    assert listed.stderr == ""
    assert json.loads(listed.stdout) == api.list_jobs(status=status, state_dir=state).model_dump(
        mode="json"
    )
    text = cli(
        "jobs",
        "show",
        "--operation-id",
        identifier,
        "--state-dir",
        str(state),
        state=True,
        recipe_loader=False,
    )
    assert text.returncode == 0, text.stderr
    assert identifier in text.stdout
    assert plan.plan_id in text.stdout
    assert plan.digest in text.stdout
    assert f"Durum: {status}" in text.stdout
    assert "güncel uzak durumu yansıtmayabilir" in text.stdout
    assert "sentetik" not in text.stdout
    assert len(backend.effects()) == int(status != "admitted")


@pytest.mark.parametrize(
    "arguments",
    [
        ["jobs", "list", "--limit", "1", "--limit", "2"],
        ["jobs", "--state-dir", "a", "list", "--state-dir=b"],
        ["--output", "json", "jobs", "list", "--output=json"],
        ["--config", "private-marker.toml", "jobs", "list"],
        ["--profile", "private-marker", "jobs", "list"],
        ["--project", "private-marker", "jobs", "list"],
        ["jobs", "list", "--task", "llm.train"],
        ["jobs", "list", "--config", "private-marker.toml"],
        ["jobs", "list", "--stat", "running"],
        ["jobs", "show"],
        ["jobs", "run"],
        ["jobs", "list", "--limit", "1.0"],
        ["jobs", "show", "--operation-id", "private-marker"],
    ],
)
def test_invalid_cli_request_has_one_safe_error_and_no_side_effect(cli, arguments):
    if "--output" not in arguments:
        arguments = [*arguments, "--output", "json"]
    result = cli(*arguments)
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.count("\n") == 1
    assert json.loads(result.stderr)["code"] == "invalid_request"
    assert "private-marker" not in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("arguments", [["jobs"], ["jobs", "list"], ["jobs", "show"]])
def test_jobs_help_is_metadata_only(cli, arguments):
    result = cli(*arguments, "--help", metadata=True)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert "usage: yorunge jobs" in result.stdout


def test_no_jobs_read_resolves_config_credentials_or_inputs(admitted_operation, monkeypatch):
    state, _, record, _, _ = admitted_operation

    def forbidden(*args, **kwargs):
        pytest.fail("local query touched execution/config/credentials/inputs")

    for name in (
        "load_config",
        "load_recipe",
        "_execution_credentials",
        "_execution_validator",
        "_context",
    ):
        monkeypatch.setattr(api, name, forbidden)
    monkeypatch.setattr("yorunge.adapters.input_files.DescriptorInputs.bind", forbidden)
    before = api.show_job(record.summary.operation_id, state_dir=state)
    assert api.list_jobs(state_dir=state).data.jobs == (before.data.operation,)
    assert api.show_job(record.summary.operation_id, state_dir=state) == before
    with open_store(state) as store:
        assert store.connection.execute("SELECT count(*) FROM operations").fetchone()[0] == 1
