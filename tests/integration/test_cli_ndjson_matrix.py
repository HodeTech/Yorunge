"""The opt-in event envelope wraps real command families and persistent writes."""

import json
from pathlib import Path

import pytest

from yorunge import api
from yorunge.domain.capabilities import instant
from yorunge.domain.state import canonical_uuid


def payload(result):
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert result.stdout.count("\n") == 1
    event = json.loads(result.stdout)
    assert set(event) == {
        "schema_version",
        "stream_id",
        "sequence",
        "event",
        "operation_id",
        "payload",
    }
    assert event["schema_version"] == 1
    assert event["sequence"] == 1
    assert event["event"] == "result"
    assert event["operation_id"] is None
    assert canonical_uuid(event["stream_id"]) == event["stream_id"]
    value = event["payload"]
    assert set(value) == {"schema_version", "operation_id", "status", "data", "warnings"}
    assert value["schema_version"] == 1
    assert value["status"] == "completed"
    assert value["operation_id"] is None
    return value


@pytest.mark.parametrize(
    "action,args",
    [
        ("profiles", ()),
        ("use-profile", ("other",)),
        ("set-project", ("chosen",)),
        ("clear-project", ()),
    ],
)
def test_context_management_ndjson_preserves_api_and_retained_backup(cli, config, action, args):
    before = config.read_bytes()
    calls = {
        "profiles": lambda: api.list_profiles(config=config),
        "use-profile": lambda: api.activate_profile("other", config=config),
        "set-project": lambda: api.set_project("chosen", config=config),
        "clear-project": lambda: api.clear_project(config=config),
    }
    expected = calls[action]().model_dump(mode="json")
    config.write_bytes(before)
    actual = payload(cli("context", action, *args, "--config", str(config), "--output=ndjson"))
    if action != "profiles":
        # Backup names are deliberately fresh for each separate mutation.
        assert Path(actual["data"].pop("backup_path")).read_bytes() == before
        expected["data"].pop("backup_path")
    assert actual == expected


def test_init_doctor_and_state_reset_use_one_result_after_actual_persistence(cli, tmp_path):
    config, state = tmp_path / "new.toml", tmp_path / "state"
    initialized = payload(cli("init", "--config", str(config), "--output", "ndjson"))
    assert initialized["data"]["config_path"] == str(config)
    assert initialized["data"]["backup_path"] is None
    assert api.show_context(config=config).data.profile == initialized["data"]["active_profile"]
    created = payload(
        cli("state", "init", "--state-dir", str(state), "--output=ndjson", state=True)
    )
    assert created == api.initialize_state(state_dir=state).model_dump(mode="json")
    report = payload(
        cli(
            "doctor",
            "--config",
            str(config),
            "--state-dir",
            str(state),
            "--output=ndjson",
            state=True,
        )
    )
    assert report == api.diagnose_local(config=config, state_dir=state).model_dump(mode="json")
    preview = payload(
        cli("state", "reset", "--state-dir", str(state), "--output=ndjson", state=True)
    )
    assert preview == api.preview_identity_reset(state_dir=state).model_dump(mode="json")
    reset = payload(
        cli(
            "state",
            "reset",
            "--state-dir",
            str(state),
            "--confirm",
            preview["data"]["digest"],
            "--output=ndjson",
            state=True,
        )
    )
    assert reset == api.initialize_state(state_dir=state).model_dump(mode="json")
    assert reset["data"]["identity_epoch"] != created["data"]["identity_epoch"]


@pytest.mark.parametrize("action", ["credential", "identity"])
def test_selected_credential_commands_wrap_only_public_observation(cli, config, tmp_path, action):
    state = tmp_path / "state"
    arguments = ["context", action, "--service", "evren-platform", "--config", str(config)]
    if action == "identity":
        arguments += ["--state-dir", str(state)]
    actual = payload(
        cli(*arguments, "--output=ndjson", credential=True, state=action == "identity")
    )
    expected = (
        api.observe_credential("evren-platform", config=config, state_dir=state)
        if action == "identity"
        else api.check_credential("evren-platform", config=config)
    )
    assert actual == expected.model_dump(mode="json")
    assert "synthetic-secret" not in json.dumps(actual)


def test_legacy_maintenance_union_keeps_the_delivered_v2_payload(cli, tmp_path, schema5_runtime):
    state = tmp_path / "legacy-state"
    api.initialize_state(state_dir=state)
    expected = api.preview_identity_reset(state_dir=state).model_dump(mode="json")
    assert expected["data"]["schema_version"] == 2
    actual = payload(
        cli(
            "state",
            "reset",
            "--state-dir",
            str(state),
            "--output=ndjson",
            state=True,
            legacy_schema5=True,
        )
    )
    assert actual == expected


def test_execution_lifecycle_ndjson_is_local_and_retains_saved_plan(cli, tmp_path):
    state = tmp_path / "state"
    base = ["plan", "execution"]
    options = ["--state-dir", str(state), "--output=ndjson"]
    prepared = payload(cli(*base, "prepare", "--task", "llm.train", *options, state=True))
    plan = prepared["data"]["plan"]
    assert plan["status"] == "draft"
    assert plan["executable"] is False
    selected = ["--plan-id", plan["plan_id"]]
    shown = payload(cli(*base, "show", *selected, *options, state=True))
    assert shown == api.show_execution_plan(plan["plan_id"], state_dir=state).model_dump(
        mode="json"
    )
    assert shown["data"]["plan"] == plan
    listed = payload(cli(*base, "list", *options, state=True))
    assert listed == api.list_execution_plans(state_dir=state).model_dump(mode="json")
    validity = payload(cli(*base, "validate", *selected, *options, state=True))
    assert validity["data"]["plan_id"] == plan["plan_id"]
    assert validity["data"]["digest"] == plan["digest"]
    assert validity["data"]["valid"] is False
    rejected = cli(*base, "approve", *selected, "--confirm", plan["digest"], *options, state=True)
    assert rejected.returncode == 2
    assert rejected.stdout == ""
    assert json.loads(rejected.stderr)["code"] == "plan_not_valid"
    revoked = payload(cli(*base, "revoke", *selected, *options, state=True))
    expected_revoke = api.revoke_execution_approval(plan["plan_id"], state_dir=state).model_dump(
        mode="json"
    )
    for view in (revoked, expected_revoke):
        instant(view["data"].pop("checked_at"))
    assert revoked == expected_revoke
    forgotten = payload(
        cli(*base, "forget", *selected, "--confirm", plan["digest"], *options, state=True)
    )
    assert forgotten["data"]["plan_id"] == plan["plan_id"]
    assert forgotten["data"]["digest"] == plan["digest"]
    assert forgotten["data"]["forgotten"] is True
    assert api.list_execution_plans(state_dir=state).data.plans == ()


@pytest.mark.parametrize("mode", ["--cached", "--refresh"])
def test_capability_cache_ndjson_preserves_snapshot_and_warnings(cli, tmp_path, mode):
    state = tmp_path / "state"
    api.query_capabilities(task="dataset.upload", state_dir=state, refresh=True)
    actual = payload(
        cli(
            "capabilities",
            "--task",
            "dataset.upload",
            mode,
            "--state-dir",
            str(state),
            "--output=ndjson",
            state=True,
        )
    )
    expected = api.query_capabilities(task="dataset.upload", state_dir=state).model_dump(
        mode="json"
    )
    assert actual["data"]["records"]
    # Each independent read has its own observation time; stored proof timestamps
    # and every other field must survive the renderer unchanged.
    for view in (actual, expected):
        for record in view["data"]["records"]:
            instant(record.pop("checked_at"))
    assert actual == expected


def test_saved_jobs_ndjson_matches_python_without_provider_or_credential_reads(
    cli, operation_setup
):
    state, plan, backend = operation_setup
    with api._operation_session(plan.plan_id, backend, state_dir=state) as coordinator:
        job = coordinator.admit(plan.plan_id).job
    operation_id = job.operation.operation_id
    shown = payload(
        cli(
            "jobs",
            "show",
            "--operation-id",
            operation_id,
            "--state-dir",
            str(state),
            "--output=ndjson",
            state=True,
        )
    )
    assert shown == api.show_job(operation_id, state_dir=state).model_dump(mode="json")
    listed = payload(cli("jobs", "list", "--state-dir", str(state), "--output=ndjson", state=True))
    assert listed == api.list_jobs(state_dir=state).model_dump(mode="json")
    assert backend.calls == 0
    assert backend.effects() == []
