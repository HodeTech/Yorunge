"""Exercise the actual compatibility gate and preserve its required job graph."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/checks.yml"
CELLS = {
    "linux311": ("ubuntu-24.04", "3.11", "true"),
    "linux314": ("ubuntu-24.04", "3.14", "false"),
    "macos311": ("macos-15", "3.11", "false"),
}


@pytest.fixture(scope="module")
def workflow():
    # BaseLoader keeps GitHub's `on` key and all version strings unchanged.
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def steps_by_id(job):
    return {step["id"]: step for step in job["steps"] if "id" in step}


def test_required_check_waits_for_exactly_the_three_compatibility_cells(workflow):
    jobs = workflow["jobs"]
    assert set(jobs) == {*CELLS, "offline-core"}
    gate = jobs["offline-core"]
    assert gate["name"] == "offline-core"
    assert gate["needs"] == list(CELLS)
    assert gate["if"] == "${{ always() }}"
    assert gate["runs-on"] == "ubuntu-24.04"
    assert gate["timeout-minutes"] == "2"
    assert "continue-on-error" not in gate
    assert len(gate["steps"]) == 1
    step = gate["steps"][0]
    assert step["id"] == "compatibility-gate"
    assert step["shell"] == "python"
    assert step["env"] == {"NEEDS": "${{ toJSON(needs) }}"}
    assert "uses" not in step  # A failing checkout cannot hide the aggregate result.
    assert "if" not in step
    assert "continue-on-error" not in step


def test_workflow_still_checks_prs_protected_branches_and_manual_runs(workflow):
    assert workflow["permissions"] == {"contents": "read"}
    assert set(workflow["on"]) == {"push", "pull_request", "workflow_dispatch"}
    for event in ("push", "pull_request"):
        assert workflow["on"][event]["branches"] == ["development", "Master"]


@pytest.mark.parametrize("cell", CELLS)
def test_cells_share_full_checks_without_allowed_failures(workflow, cell):
    job = workflow["jobs"][cell]
    runner, python, budgets = CELLS[cell]
    assert job["runs-on"] == runner
    assert job["timeout-minutes"] == "25"
    assert job["env"] == {
        "PYTHON_VERSION": python,
        "RUN_BUDGETS": budgets,
        "RUNNER_LABEL": runner,
    }
    assert job["steps"] is workflow["jobs"]["linux311"]["steps"]
    assert not {"if", "continue-on-error", "strategy", "needs"} & job.keys()
    for step in job["steps"]:
        assert "continue-on-error" not in step
    steps = steps_by_id(job)
    for required in (
        "python",
        "environment-setup",
        "environment-report",
        "static-checks",
        "tests",
        "build",
    ):
        assert "if" not in steps[required]
    assert steps["python"]["uses"] == "actions/setup-python@v7"
    assert steps["python"]["with"] == {"python-version": "${{ env.PYTHON_VERSION }}"}
    assert steps["environment-setup"]["run"].splitlines() == [
        "python -m venv .ci-tools",
        ".ci-tools/bin/pip install uv==0.11.2",
        '.ci-tools/bin/uv sync --frozen --python "$PYTHON_VERSION"',
    ]
    assert steps["static-checks"]["run"].splitlines() == [
        ".venv/bin/ruff format --check src tests scripts",
        ".venv/bin/ruff check src tests scripts",
        ".venv/bin/mypy",
        ".venv/bin/python scripts/check-docs.py",
        ".venv/bin/python scripts/check-agent-guides.py",
        ".venv/bin/python scripts/research_evidence.py verify",
    ]
    assert steps["tests"]["run"] == ".venv/bin/pytest"
    assert steps["build"]["run"].splitlines() == [
        ".ci-tools/bin/uv build",
        ".venv/bin/python scripts/verify-distributions.py --uv .ci-tools/bin/uv "
        "> dist/verification.jsonl",
        "cat dist/verification.jsonl",
    ]


def test_reference_startup_gate_and_failure_diagnostics_keep_the_existing_path(workflow):
    steps = steps_by_id(workflow["jobs"]["linux311"])
    baseline = steps["startup-baseline"]
    assert baseline["if"] == "${{ env.RUN_BUDGETS == 'true' }}"
    assert baseline["with"]["path"] == ".local/startup-baseline"
    assert baseline["with"]["persist-credentials"] == "false"
    assert baseline["with"]["ref"] == (
        "${{ github.event.pull_request.base.sha || "
        "(github.event.before != '0000000000000000000000000000000000000000' "
        "&& github.event.before) || github.sha }}"
    )
    budgets = steps["startup-budgets"]
    assert budgets["if"] == "${{ env.RUN_BUDGETS == 'true' }}"
    assert budgets["run"].strip() == (
        ".venv/bin/python scripts/check-startup.py --uv .ci-tools/bin/uv "
        "--baseline-project .local/startup-baseline --workspace .local/startup-check "
        "--output dist/startup.json"
    )
    diagnostics = steps["startup-diagnostics"]
    assert diagnostics["if"] == "${{ failure() && env.RUN_BUDGETS == 'true' }}"
    assert "scripts/check-startup.py" not in diagnostics["run"]


def test_reference_jobs_and_raw_stream_gates_follow_successful_tests_build_and_startup(workflow):
    job = workflow["jobs"]["linux311"]
    steps = steps_by_id(job)
    ordered = list(steps)
    assert [step for step in ordered if step in {"tests", "build", "startup-budgets"}] == [
        "tests",
        "build",
        "startup-budgets",
    ]
    previous = "startup-budgets"
    for step_id, command in (
        (
            "jobs-budgets",
            ".venv/bin/python scripts/research_evidence.py verify-jobs-reference "
            "p01-6-reference-jobs-rss-v2.json > dist/jobs-reference.txt",
        ),
        (
            "raw-stream-budgets",
            ".venv/bin/python scripts/benchmark-stream.py "
            "--python .local/startup-check/candidate/env/bin/python "
            "--workspace .local/stream-check --output dist/stream.json --disk-type unknown",
        ),
    ):
        step = steps[step_id]
        assert step["if"] == "${{ success() && env.RUN_BUDGETS == 'true' }}"
        assert step["run"].strip() == command
        assert ordered.index(previous) < ordered.index(step_id)
        previous = step_id
    assert ordered.index(previous) < ordered.index("upload-evidence")


def test_each_cell_preserves_evidence_even_after_failure(workflow):
    steps = steps_by_id(workflow["jobs"]["linux311"])
    upload = steps["upload-evidence"]
    assert upload is workflow["jobs"]["linux311"]["steps"][-1]
    assert upload["if"] == "${{ always() }}"
    assert upload["uses"] == "actions/upload-artifact@v4"
    assert upload["with"]["name"] == "compatibility-${{ github.job }}"
    assert upload["with"]["if-no-files-found"] == "warn"
    assert upload["with"]["include-hidden-files"] == "true"
    assert set(upload["with"]["path"].splitlines()) == {
        "dist/ci-environment.json",
        "dist/verification.jsonl",
        "dist/startup.json",
        "dist/jobs-reference.txt",
        "dist/stream.json",
        "dist/cache-startup.prof",
        ".local/stream-check/source-manifest.json",
        ".local/stream-check/*/measurement.json",
        ".local/stream-check/*/failure.json",
        ".local/stream-check/*/client-stdout.txt",
        ".local/stream-check/*/client-stderr.txt",
        ".local/stream-check/*/server-stdout.txt",
        ".local/stream-check/*/server-stderr.txt",
    }


def invoke_gate(workflow, tmp_path, content):
    step = workflow["jobs"]["offline-core"]["steps"][0]
    environment = dict(os.environ, NEEDS=content)
    return subprocess.run(
        [sys.executable, "-c", step["run"]],
        env=environment,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=5,
    )


def successful_needs():
    return {cell: {"result": "success", "outputs": {}} for cell in CELLS}


def test_actual_gate_accepts_all_success_without_a_checkout(workflow, tmp_path):
    result = invoke_gate(workflow, tmp_path, json.dumps(successful_needs()))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {cell: "success" for cell in CELLS}


@pytest.mark.parametrize("cell", CELLS)
@pytest.mark.parametrize("status", ["failure", "cancelled", "skipped", "unknown", "", None])
def test_actual_gate_rejects_any_unsuccessful_required_cell(workflow, tmp_path, cell, status):
    needs = successful_needs()
    needs[cell]["result"] = status
    result = invoke_gate(workflow, tmp_path, json.dumps(needs))
    assert result.returncode != 0


@pytest.mark.parametrize("cell", CELLS)
def test_actual_gate_rejects_a_missing_cell(workflow, tmp_path, cell):
    needs = successful_needs()
    del needs[cell]
    assert invoke_gate(workflow, tmp_path, json.dumps(needs)).returncode != 0


@pytest.mark.parametrize("status", ["success", "failure", "cancelled", "skipped"])
def test_actual_gate_rejects_unexpected_dependencies(workflow, tmp_path, status):
    needs = successful_needs()
    needs["extra"] = {"result": status}
    assert invoke_gate(workflow, tmp_path, json.dumps(needs)).returncode != 0


@pytest.mark.parametrize("value", [{}, None, "success", [], {"outputs": {}}])
def test_actual_gate_rejects_missing_or_malformed_cell_results(workflow, tmp_path, value):
    needs = successful_needs()
    needs["linux311"] = value
    assert invoke_gate(workflow, tmp_path, json.dumps(needs)).returncode != 0


@pytest.mark.parametrize("content", ["{}", "[]", "null", '"success"', "{broken"])
def test_actual_gate_rejects_empty_or_malformed_needs(workflow, tmp_path, content):
    assert invoke_gate(workflow, tmp_path, content).returncode != 0


def environment_report_code(workflow):
    step = steps_by_id(workflow["jobs"]["linux311"])["environment-report"]
    assert step["env"] == {"CI_JOB": "${{ github.job }}"}
    lines = step["run"].splitlines()
    assert lines[0] == ".venv/bin/python - <<'PY'"
    assert lines[-1] == "PY"
    return compile("\n".join(lines[1:-1]), str(WORKFLOW), "exec")


@pytest.mark.parametrize(
    "budgets,scope", [("true", "reference_linux311"), ("false", "compatibility_only")]
)
def test_actual_environment_report_records_source_runtime_and_scope(
    workflow, tmp_path, monkeypatch, budgets, scope
):
    code = environment_report_code(workflow)
    monkeypatch.chdir(tmp_path)
    for key, value in {
        "PYTHON_VERSION": f"{sys.version_info.major}.{sys.version_info.minor}",
        "RUN_BUDGETS": budgets,
        "GITHUB_SHA": "b" * 40,
        "CI_JOB": "linux311",
        "RUNNER_LABEL": "ubuntu-24.04",
        "RUNNER_OS": "Linux",
        "RUNNER_ARCH": "X64",
        "ImageOS": "ubuntu24",
        "ImageVersion": "20261029.1.0",
        "UNRELATED_SECRET": "do-not-record-ambient-values",
    }.items():
        monkeypatch.setenv(key, value)

    original_check_output = subprocess.check_output

    def check_output(command, **kwargs):
        responses = {
            ("git", "rev-parse", "HEAD"): "a" * 40 + "\n",
            (".ci-tools/bin/uv", "--version"): "uv 0.11.2\n",
            ("sysctl", "-n", "machdep.cpu.brand_string"): "fixture CPU\n",
        }
        if tuple(command) in responses:
            assert kwargs == {"text": True, "timeout": 5}
            return responses[tuple(command)]
        # platform.processor()/platform.platform() may also invoke system utilities.
        return original_check_output(command, **kwargs)

    monkeypatch.setattr(subprocess, "check_output", check_output)
    exec(code, {})
    encoded = (tmp_path / "dist/ci-environment.json").read_text(encoding="utf-8")
    report = json.loads(encoded)
    assert report["source_sha"] == "a" * 40
    assert report["github_sha"] == "b" * 40
    assert report["job"] == "linux311"
    assert report["python"] == sys.version
    assert report["python_executable"] == sys.executable
    assert report["python_implementation"] == "CPython"
    for key in ("os", "os_release", "platform", "architecture", "sqlite", "cpu"):
        assert isinstance(report[key], str)
        assert report[key]
    assert report["packages"]["pytest"]
    assert report["uv"] == "uv 0.11.2"
    assert report["runner_label"] == "ubuntu-24.04"
    assert report["runner_os"] == "Linux"
    assert report["runner_architecture"] == "X64"
    assert report["runner_image"] == {"ImageOS": "ubuntu24", "ImageVersion": "20261029.1.0"}
    assert "cpu_count" in report
    assert "cpu_affinity" in report
    assert report["disk_type"] == "unknown"
    assert report["startup_budget_scope"] == scope
    assert report["jobs_budget_scope"] == (
        "reference_receipt_macos_m5max_py311" if budgets == "true" else "compatibility_only"
    )
    assert report["raw_stream_budget_scope"] == scope
    assert "do-not-record-ambient-values" not in encoded


def test_actual_environment_report_rejects_the_wrong_python(workflow, tmp_path, monkeypatch):
    code = environment_report_code(workflow)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTHON_VERSION", "0.0")
    with pytest.raises(SystemExit, match="does not match the required version"):
        exec(code, {})
    assert not (tmp_path / "dist/ci-environment.json").exists()
