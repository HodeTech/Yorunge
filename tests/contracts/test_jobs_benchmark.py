"""Jobs acceptance must reject fast wrong results and preserve failed evidence."""

import copy
import hashlib
import json
import runpy
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.seed_jobs import seed
from yorunge import api

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/benchmark-jobs.py"


@pytest.fixture
def helpers():
    return runpy.run_path(str(SCRIPT))


@pytest.fixture
def normal(tmp_path, helpers):
    state = tmp_path / "state"
    identifier = seed(state, dense=False)
    expected = helpers["fixture"](state, "normal")
    outputs = {
        "list": api.list_jobs(limit=50, state_dir=state).model_dump_json(),
        "show": api.show_job(identifier, state_dir=state).model_dump_json(),
    }
    return state, expected, outputs


def test_fixture_reports_actual_database_and_payload_volume(normal, helpers):
    state, expected, _ = normal
    assert expected["rows"]["operations"]["records"] == 1
    assert expected["rows"]["operation_events"]["records"] == 3
    assert expected["rows"]["operation_outcomes"]["records"] == 0
    assert expected["database_bytes"] == (state / "state.sqlite3").stat().st_size
    with sqlite3.connect(state / "state.sqlite3") as db:
        length = db.execute("SELECT length(CAST(payload AS BLOB)) FROM operations").fetchone()[0]
    assert expected["rows"]["operations"]["payload_bytes"] == length
    assert expected["rows"]["operations"]["largest_record_bytes"] == length
    with pytest.raises(ValueError, match="invalid dense fixture"):
        helpers["fixture"](state, "dense")


@pytest.mark.parametrize("damage", ["empty", "missing_history", "wrong_status"])
def test_corrupt_fixture_cannot_be_accepted_as_a_smaller_fast_dataset(normal, helpers, damage):
    state, _, _ = normal
    with sqlite3.connect(state / "state.sqlite3") as db:
        if damage == "empty":
            db.execute("DELETE FROM operations")
        elif damage == "missing_history":
            db.execute("DELETE FROM operation_events WHERE sequence=3")
        else:
            payload = json.loads(db.execute("SELECT payload FROM operations").fetchone()[0])
            payload["summary"]["status"] = "succeeded"
            db.execute("UPDATE operations SET payload=?", (json.dumps(payload),))
    with pytest.raises(ValueError, match="fixture"):
        helpers["fixture"](state, "normal")


@pytest.mark.parametrize("action", ["list", "show"])
def test_every_response_is_checked_against_the_fixture_and_installed_result_model(
    normal, helpers, action, tmp_path
):
    _, expected, outputs = normal
    helpers["validate_output"](outputs[action], action, expected)
    # This is a schema check on one small real result, not a timing acceptance run.
    result = helpers["run"](
        [sys.executable, "-I", "-c", helpers["VALIDATE"]],
        cwd=tmp_path,
        content=json.dumps({"action": action, "outputs": [outputs[action]]}),
    )
    assert json.loads(result.stdout) == {"validated": 1}
    wrong = json.loads(outputs[action])
    wrong["data"]["unexpected_wire_field"] = True
    with pytest.raises(subprocess.CalledProcessError):
        helpers["run"](
            [sys.executable, "-I", "-c", helpers["VALIDATE"]],
            cwd=tmp_path,
            content=json.dumps({"action": action, "outputs": [json.dumps(wrong)]}),
        )


@pytest.mark.parametrize(
    ("action", "damage"),
    [
        ("list", "empty"),
        ("list", "wrong_id"),
        ("list", "wrong_digest"),
        ("list", "wrong_status"),
        ("list", "cursor"),
        ("show", "wrong_id"),
        ("show", "wrong_digest"),
        ("show", "wrong_status"),
        ("show", "missing_attempt"),
        ("show", "outcome"),
    ],
)
def test_zero_exit_cannot_make_a_false_job_or_empty_list_a_success(normal, helpers, action, damage):
    _, expected, outputs = normal
    value = json.loads(outputs[action])
    data = value["data"]
    summary = data["jobs"][0] if action == "list" else data["operation"]
    if damage == "empty":
        data["jobs"] = []
    elif damage == "wrong_id":
        summary["operation_id"] = "00000000-0000-4000-8000-000000000000"
    elif damage == "wrong_digest":
        summary["plan_digest"] = "f" * 64
    elif damage == "wrong_status":
        summary["status"] = "succeeded"
    elif damage == "cursor":
        data["next_cursor"] = "wrong-page"
    elif damage == "missing_attempt":
        data["attempts"] = []
    else:
        data["outcome"] = {"execution_status": "succeeded"}
    with pytest.raises(ValueError, match="incorrect|cursor"):
        helpers["validate_output"](json.dumps(value), action, expected)


def test_duplicate_json_keys_are_rejected_before_typed_validation(normal, helpers):
    _, expected, outputs = normal
    duplicate = outputs["list"].replace(
        '"status":"completed"', '"status":"failed","status":"completed"'
    )
    with pytest.raises(ValueError, match="duplicate"):
        helpers["validate_output"](duplicate, "list", expected)


def test_nearest_rank_uses_unrounded_samples_and_retains_the_slowest(helpers):
    boundary = helpers["summarize"]([1.0] * 28 + [200.0, 9999.0])
    assert boundary["p95_ms"] == 200.0
    assert boundary["passed"] is True
    values = [1.0] * 28 + [200.000001, 9999.0]
    failed = helpers["summarize"](values)
    assert failed["samples_ms"] == values
    assert failed["p95_ms"] == 200.000001
    assert failed["passed"] is False
    for invalid in ([1.0] * 29, [1.0] * 29 + [float("nan")], [1.0] * 29 + [0.0]):
        with pytest.raises(ValueError):
            helpers["summarize"](invalid)


def test_each_case_has_first_three_warmups_and_thirty_independent_checked_processes(
    helpers, normal, tmp_path, monkeypatch
):
    _, expected, outputs = normal
    measure_case = helpers["measure_case"]
    calls = []

    def measured(command, *, cwd):
        calls.append((command, cwd))
        return float(len(calls)), outputs["list"]

    def checked(command, *, cwd, content):
        assert command[:3] == ["/runtime/bin/python", "-I", "-c"]
        assert len(json.loads(content)["outputs"]) == 34
        return subprocess.CompletedProcess(command, 0, '{"validated":34}', "")

    monkeypatch.setitem(measure_case.__globals__, "measure", measured)
    monkeypatch.setitem(measure_case.__globals__, "run", checked)
    result = measure_case(
        Path("/runtime/bin/python"),
        Path("/runtime/bin/yorunge"),
        tmp_path,
        "normal",
        "list",
        expected,
        30,
    )
    assert len(calls) == 34
    assert all(
        command[:3] == ["/runtime/bin/python", "-I", "/runtime/bin/yorunge"] for command, _ in calls
    )
    assert result["first_process_ms"] == 1.0
    assert result["warmups_ms"] == [2.0, 3.0, 4.0]
    assert result["samples_ms"] == list(map(float, range(5, 35)))
    assert result["typed_stdout_verified"] is True
    assert len(result["stdout_sha256"]) == 34


def test_runtime_requires_all_source_bytes_and_frozen_runtime_only_packages(
    helpers, tmp_path, monkeypatch
):
    project = tmp_path / "project"
    package = project / "src/yorunge"
    package.mkdir(parents=True)
    module = package / "__init__.py"
    module.write_text("# current\n")
    project.joinpath("uv.lock").write_text(
        '[[package]]\nname="yorunge"\nversion="1"\ndependencies=[{name="core"}]\n'
        '[[package]]\nname="core"\nversion="2"\n'
    )
    expected = {
        "installed_source_sha256": {
            "yorunge/__init__.py": hashlib.sha256(module.read_bytes()).hexdigest()
        },
        "packages": {"yorunge": "1", "core": "2"},
        "console": "/runtime/bin/yorunge",
    }
    runtime = helpers["runtime"]
    monkeypatch.setitem(runtime.__globals__, "runtime_snapshot", lambda *_: expected)
    assert runtime(Path("/runtime/bin/python"), project, tmp_path) == expected
    for damage in (
        "changed_source",
        "extra_source",
        "dev_package",
        "wrong_version",
        "other_console",
    ):
        wrong = copy.deepcopy(expected)
        if damage == "changed_source":
            wrong["installed_source_sha256"]["yorunge/__init__.py"] = "0" * 64
        elif damage == "extra_source":
            wrong["installed_source_sha256"]["yorunge/stale.py"] = "0" * 64
        elif damage == "dev_package":
            wrong["packages"]["pytest"] = "9"
        elif damage == "wrong_version":
            wrong["packages"]["core"] = "3"
        else:
            wrong["console"] = "/other/bin/yorunge"
        monkeypatch.setitem(runtime.__globals__, "runtime_snapshot", lambda *_, value=wrong: value)
        with pytest.raises(ValueError):
            runtime(Path("/runtime/bin/python"), project, tmp_path)


def test_real_development_editable_environment_is_rejected(helpers, tmp_path):
    with pytest.raises(subprocess.CalledProcessError) as error:
        helpers["runtime_snapshot"](Path(sys.executable), tmp_path)
    assert "installed product must originate inside an isolated venv" in error.value.stderr


@pytest.mark.parametrize(
    "kind", ["existing", "symlink", "dangling_symlink", "parent_symlink", "missing_parent"]
)
def test_output_is_exclusive_before_preparation(helpers, tmp_path, kind):
    target, output = tmp_path / "target", tmp_path / "report.json"
    if kind == "existing":
        output.write_text("original")
    elif kind in {"symlink", "dangling_symlink"}:
        if kind == "symlink":
            target.write_text("original")
        output.symlink_to(target)
    elif kind == "parent_symlink":
        target.mkdir()
        link = tmp_path / "link"
        link.symlink_to(target, target_is_directory=True)
        output = link / "report.json"
    else:
        output = tmp_path / "absent/report.json"
    with pytest.raises(ValueError, match="output must be a new file"):
        helpers["check"](
            Path("unused"),
            tmp_path / "workspace",
            output,
            samples=30,
            wheel=None,
            cpu="test",
            disk="unknown",
        )
    assert not (tmp_path / "workspace").exists()
    if kind == "existing":
        assert output.read_text() == "original"
    if kind == "symlink":
        assert target.read_text() == "original"


@pytest.mark.parametrize("kind", ["existing", "symlink", "dangling_symlink"])
def test_existing_workspace_never_becomes_a_fixture_store(helpers, tmp_path, kind):
    workspace = tmp_path / "workspace"
    if kind == "existing":
        workspace.mkdir()
        (workspace / "user-data").write_text("original")
    else:
        workspace.symlink_to(tmp_path / "target", target_is_directory=True)
    with pytest.raises(ValueError, match="workspace must be new"):
        helpers["check"](
            Path("unused"),
            workspace,
            tmp_path / "report.json",
            samples=30,
            wheel=None,
            cpu="test",
            disk="unknown",
        )
    if kind == "existing":
        assert (workspace / "user-data").read_text() == "original"


@pytest.mark.parametrize(
    "change", ["budget", "source", "head", "installed", "fixture", "output_race"]
)
def test_failed_budget_or_changed_provenance_is_saved_with_nonzero_status(
    helpers, tmp_path, monkeypatch, change
):
    check = helpers["check"]
    output = tmp_path / "report.json"
    before = {"commit": "a" * 40, "source_sha256": {"script.py": "0" * 64}}
    after = copy.deepcopy(before)
    if change == "source":
        after["source_sha256"]["script.py"] = "1" * 64
    elif change == "head":
        # Equal product bytes cannot make a different source commit a frozen receipt.
        after["commit"] = "b" * 40
        assert after["source_sha256"] == before["source_sha256"]
    sources = iter((before, after))
    current_runtime = {"console": "/runtime/bin/yorunge", "python": "test"}
    after_runtime = (
        {**current_runtime, "python": "changed"} if change == "installed" else current_runtime
    )
    monkeypatch.setitem(check.__globals__, "source", lambda *_: next(sources))
    monkeypatch.setitem(check.__globals__, "runtime", lambda *_: current_runtime)
    monkeypatch.setitem(check.__globals__, "runtime_snapshot", lambda *_: after_runtime)
    monkeypatch.setitem(check.__globals__, "run", lambda *_, **__: None)
    fixture_calls = 0

    def fixture(*_):
        nonlocal fixture_calls
        fixture_calls += 1
        return {"database_bytes": 2 if change == "fixture" and fixture_calls > 2 else 1}

    def case(_python, _console, _workspace, layout, action, _fixture, _count):
        if change == "output_race" and not output.exists():
            output.write_text("concurrent evidence")
        return {"layout": layout, "action": action, "passed": change != "budget"}

    monkeypatch.setitem(check.__globals__, "fixture", fixture)
    monkeypatch.setitem(check.__globals__, "measure_case", case)
    if change == "output_race":
        with pytest.raises(FileExistsError):
            check(
                Path("unused"),
                tmp_path / "workspace",
                output,
                samples=30,
                wheel=None,
                cpu="test",
                disk="unknown",
            )
        assert output.read_text() == "concurrent evidence"
    else:
        assert (
            check(
                Path("unused"),
                tmp_path / "workspace",
                output,
                samples=30,
                wheel=None,
                cpu="test",
                disk="unknown",
            )
            == 1
        )
        report = json.loads(output.read_text())
        assert report["passed"] is False
        assert report["source_commit"] == "a" * 40
        assert {(run["layout"], run["action"]) for run in report["runs"]} == {
            ("normal", "list"),
            ("normal", "show"),
            ("dense", "list"),
            ("dense", "show"),
        }
        assert report["provenance"]["unchanged"] is (change == "budget")


def test_cli_cannot_lower_the_required_sample_count(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--python",
            "unused",
            "--workspace",
            str(tmp_path / "work"),
            "--output",
            str(tmp_path / "report.json"),
            "--samples",
            "29",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert "at least 30 samples" in result.stderr
    assert not (tmp_path / "work").exists()
