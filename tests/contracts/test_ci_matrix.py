"""Exercise the actual compatibility gate and preserve its required job graph."""

import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/checks.yml"
ARTIFACT_PATHS = Path(__file__).resolve().parents[2] / "scripts/evidence-artifact-paths.txt"
CELLS = {
    "linux311": ("ubuntu-24.04", "3.11", "true"),
    "linux314": ("ubuntu-24.04", "3.14", "false"),
    "macos311": ("macos-15", "3.11", "false"),
}

METADATA_EVENT = (
    "github.event_name == 'pull_request' && github.event.action == 'edited' "
    "&& github.event.changes.base == null && "
    "(github.event.changes.body != null || github.event.changes.title != null)"
)


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
    assert workflow["on"]["pull_request"]["types"] == [
        "opened",
        "synchronize",
        "reopened",
        "edited",
        "ready_for_review",
    ]


def test_only_known_body_or_title_edits_use_an_independent_validation_group(workflow):
    # Base changes, unknown edits, pushes and manual calls remain source events.
    # Metadata changes still validate all three cells, without cancelling source work.
    assert workflow["concurrency"] == {
        "group": (
            "core-checks-${{ github.event.pull_request.number || github.ref }}"
            "${{ (" + METADATA_EVENT + ") && '-metadata' || '' }}"
        ),
        "cancel-in-progress": "true",
    }
    policy = yaml.load(WORKFLOW.with_name("pr-policy.yml").read_text(), Loader=yaml.BaseLoader)
    assert "edited" in policy["on"]["pull_request_target"]["types"]


@pytest.mark.parametrize("cell", CELLS)
def test_cells_share_full_checks_without_allowed_failures(workflow, cell):
    job = workflow["jobs"][cell]
    runner, python, budgets = CELLS[cell]
    assert job["runs-on"] == runner
    assert job["timeout-minutes"] == "90"
    assert job["env"] == {
        "PYTHON_VERSION": python,
        "RUN_BUDGETS": budgets,
        "RUNNER_LABEL": runner,
    }
    assert job["steps"] is workflow["jobs"]["linux311"]["steps"]
    assert "if" not in job
    assert job["name"] == ("macOS" if cell == "macos311" else "Linux") + " / Python " + python
    assert not {"continue-on-error", "strategy", "needs"} & job.keys()
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
    assert steps["tests"]["run"] == ".venv/bin/pytest -o faulthandler_timeout=60"
    assert steps["build"]["run"].splitlines() == [
        ".ci-tools/bin/uv build",
        ".venv/bin/python scripts/verify-distributions.py --uv .ci-tools/bin/uv "
        "--evidence-output dist/installation.json --upload-workspace "
        ".local/distribution-upload-check --download-workspace "
        ".local/distribution-download-check > dist/verification.jsonl",
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
        ".venv/bin/python scripts/startup_diagnostic.py --uv .ci-tools/bin/uv "
        "--baseline-project .local/startup-baseline --workspace .local/startup-check "
        "--report dist/startup.json --receipt dist/startup-diagnostic.json"
    )
    diagnostics = steps["startup-diagnostics"]
    assert diagnostics["if"] == (
        "${{ (failure() || steps.startup-budgets.outputs.outcome == 'diagnostic_budget_exceeded') "
        "&& env.RUN_BUDGETS == 'true' }}"
    )
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
            "startup-reference",
            ".venv/bin/python scripts/research_evidence.py verify-startup-reference "
            "p02-3-reference-startup-5.json > dist/startup-reference.txt",
        ),
        (
            "jobs-budgets",
            ".venv/bin/python scripts/research_evidence.py verify-jobs-reference "
            "p02-3-reference-jobs-5.json > dist/jobs-reference.txt",
        ),
        (
            "dataset-budgets",
            ".venv/bin/python scripts/research_evidence.py verify-dataset-reference "
            "p02-3-reference-datasets-5.json > dist/dataset-reference.txt",
        ),
        (
            "raw-stream-budgets",
            ".venv/bin/python scripts/benchmark-stream.py "
            "--python .local/startup-check/candidate/env/bin/python "
            "--workspace .local/stream-check --output dist/stream.json --disk-type unknown",
        ),
        (
            "upload-reference",
            ".venv/bin/python scripts/research_evidence.py verify-upload-reference "
            "p02-3-reference-upload-5.json > dist/upload-reference.txt",
        ),
        (
            "upload-budgets",
            ".venv/bin/python scripts/upload_ci.py "
            "--python .local/startup-check/candidate/env/bin/python "
            "--wheel-dir .local/startup-check/candidate/dist --workspace .local/upload-check "
            "--output dist/upload.json --environment dist/ci-environment.json "
            '--run-url "https://github.com/${{ github.repository }}'
            '/actions/runs/${{ github.run_id }}"',
        ),
        (
            "download-reference",
            ".venv/bin/python scripts/research_evidence.py verify-download-reference "
            "p02-3-reference-download-5.json > dist/download-reference.txt",
        ),
        (
            "download-budgets",
            ".venv/bin/python scripts/download_ci.py "
            "--python .local/startup-check/candidate/env/bin/python "
            "--wheel-dir .local/startup-check/candidate/dist --workspace .local/download-check "
            "--output dist/download.json --environment dist/ci-environment.json "
            '--run-url "https://github.com/${{ github.repository }}'
            '/actions/runs/${{ github.run_id }}"',
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
    assert workflow["jobs"]["linux311"]["steps"][0]["with"]["fetch-depth"] == "0"
    upload = steps["upload-evidence"]
    assert upload is workflow["jobs"]["linux311"]["steps"][-1]
    assert upload["if"] == "${{ always() && steps.evidence-privacy.outcome == 'success' }}"
    assert upload["with"]["path"] == ".local/evidence-publication/"
    context, privacy = steps["evidence-context"], steps["evidence-privacy"]
    assert context["if"] == privacy["if"] == "${{ always() }}"
    assert "--producer-preflight" in context["run"]
    assert "--child-root" in context["run"]
    assert "TMPDIR" in context["run"]
    assert (
        'echo "YORUNGE_EVIDENCE_CONTEXT=$GITHUB_WORKSPACE/.local/evidence-privacy-context.json" '
        '>> "$GITHUB_ENV"' in context["run"]
    )
    assert "stage-ci --context .local/evidence-privacy-context.json" in privacy["run"]
    assert "--patterns scripts/evidence-artifact-paths.txt" in privacy["run"]
    assert "--destination .local/evidence-publication" in privacy["run"]
    assert list(steps).index("evidence-context") < list(steps).index("environment-report")
    assert list(steps).index("evidence-privacy") < list(steps).index("upload-evidence")
    assert upload["uses"] == "actions/upload-artifact@v4"
    assert upload["with"]["name"] == "compatibility-${{ github.job }}"
    assert upload["with"]["if-no-files-found"] == "error"
    assert upload["with"]["retention-days"] == "90"
    assert upload["with"]["include-hidden-files"] == "true"
    assert set(ARTIFACT_PATHS.read_text().splitlines()) == {
        "dist/ci-environment.json",
        "dist/verification.jsonl",
        "dist/installation.json",
        "dist/installation-upload-*-rejected.json",
        "dist/startup.json",
        "dist/startup-diagnostic.json",
        "dist/startup-baseline-selection.json",
        "dist/startup-reference.txt",
        "dist/jobs-reference.txt",
        "dist/dataset-reference.txt",
        "dist/stream.json",
        "dist/upload.json",
        "dist/upload-reference.txt",
        "dist/upload*-rejected.json",
        "dist/cache-startup.prof",
        ".local/startup-check/source-manifest.json",
        ".local/startup-check/measurement.json",
        ".local/startup-check/stdout-checks.json",
        ".local/stream-check/source-manifest.json",
        ".local/stream-check/*/measurement.json",
        ".local/stream-check/*/failure.json",
        ".local/stream-check/*/client-stdout.txt",
        ".local/stream-check/*/client-stderr.txt",
        ".local/stream-check/*/server-stdout.txt",
        ".local/stream-check/*/server-stderr.txt",
        ".local/upload-check/source-before.json",
        ".local/upload-check/source-manifest.json",
        ".local/upload-check/source-after.json",
        ".local/upload-check/oracle.json",
        ".local/upload-check/controller-error.json",
        ".local/upload-check/stdout.json",
        ".local/upload-check/stderr.txt",
        ".local/upload-check-controller-stdout.txt",
        ".local/upload-check-controller-stderr.txt",
        ".local/upload-check/*/client-stdout.json",
        ".local/upload-check/*/client-stderr.txt",
        ".local/upload-check/*/*-server/*.json",
        ".local/upload-check/*/*-server/*.txt",
        "dist/download.json",
        "dist/download-reference.txt",
        "dist/download*-rejected.json",
        ".local/download-check/source-before.json",
        ".local/download-check/source-manifest.json",
        ".local/download-check/source-after.json",
        ".local/download-check/controller-error.json",
        ".local/download-check/stdout.json",
        ".local/download-check/stderr.txt",
        ".local/download-check-controller-stdout.txt",
        ".local/download-check-controller-stderr.txt",
        ".local/download-check/*/client-stdout.json",
        ".local/download-check/*/client-stderr.txt",
        ".local/download-check/*/*-server/*.json",
        ".local/download-check/*/*-server/*.txt",
        ".local/distribution-upload-check/*/source-before.json",
        ".local/distribution-upload-check/*/source-manifest.json",
        ".local/distribution-upload-check/*/source-after.json",
        ".local/distribution-upload-check/*/oracle.json",
        ".local/distribution-upload-check/*/controller-error.json",
        ".local/distribution-upload-check/*/metadata-stdout.json",
        ".local/distribution-upload-check/*/metadata-stderr.txt",
        ".local/distribution-upload-check/*/stdout.json",
        ".local/distribution-upload-check/*/*/client-stdout.json",
        ".local/distribution-upload-check/*/*/client-stderr.txt",
        ".local/distribution-upload-check/*/*/*-server/*.json",
        ".local/distribution-upload-check/*/*/*-server/*.txt",
        "dist/installation-download-*-rejected.json",
        ".local/distribution-download-check/*/source-before.json",
        ".local/distribution-download-check/*/source-manifest.json",
        ".local/distribution-download-check/*/source-after.json",
        ".local/distribution-download-check/*/controller-error.json",
        ".local/distribution-download-check/*/metadata-stdout.json",
        ".local/distribution-download-check/*/metadata-stderr.txt",
        ".local/distribution-download-check/*/stdout.json",
        ".local/distribution-download-check/*/*/client-stdout.json",
        ".local/distribution-download-check/*/*/client-stderr.txt",
        ".local/distribution-download-check/*/*/*-server/*.json",
        ".local/distribution-download-check/*/*/*-server/*.txt",
    }


def test_upload_artifacts_preserve_interrupted_logs_and_exclude_payloads_and_state(workflow):
    upload = steps_by_id(workflow["jobs"]["linux311"])["upload-evidence"]
    assert upload["with"]["path"] == ".local/evidence-publication/"
    patterns = ARTIFACT_PATHS.read_text().splitlines()
    selected = (
        ".local/upload-check/16-1/client-stdout.json",
        ".local/upload-check/16-1/measured-server/stderr.txt",
        ".local/upload-check/source-before.json",
        ".local/upload-check-controller-stderr.txt",
        ".local/distribution-upload-check/wheel/metadata-stdout.json",
        ".local/distribution-upload-check/sdist/16-1/warm-server/stdout.json",
    )
    excluded = (
        ".local/upload-check/16-1/measured/source/file-000.bin",
        ".local/upload-check/16-1/measured/state/state.sqlite3",
        ".local/upload-check/16-1/measured/config.toml",
        ".local/upload-check/cert/key.pem",
        ".local/distribution-upload-check/wheel/16-1/warm/source/file-000.bin",
        ".local/distribution-upload-check/sdist/16-1/measured/state/state.sqlite3",
    )
    assert all(any(PurePosixPath(name).match(pattern) for pattern in patterns) for name in selected)
    assert not any(PurePosixPath(name).match(pattern) for pattern in patterns for name in excluded)


def test_installation_download_artifacts_keep_the_smoke_logs_and_exclude_payloads_and_state(
    workflow,
):
    patterns = ARTIFACT_PATHS.read_text().splitlines()
    selected = (
        "dist/installation-download-wheel-rejected.json",
        "dist/installation-download-sdist-rejected.json",
        ".local/distribution-download-check/wheel/source-before.json",
        ".local/distribution-download-check/wheel/controller-error.json",
        ".local/distribution-download-check/wheel/metadata-stdout.json",
        ".local/distribution-download-check/sdist/stdout.json",
        ".local/distribution-download-check/wheel/16-1/client-stdout.json",
        ".local/distribution-download-check/wheel/16-2/client-stderr.txt",
        ".local/distribution-download-check/sdist/16-1/warm-server/stdout.json",
        ".local/distribution-download-check/sdist/16-2/measured-server/ready.json",
    )
    excluded = (
        ".local/distribution-download-check/wheel/cert/key.pem",
        ".local/distribution-download-check/wheel/16-1/measured/out/weights.onnx",
        ".local/distribution-download-check/wheel/16-1/measured/state/state.sqlite3",
        ".local/distribution-download-check/sdist/16-1/warm/config.toml",
        ".local/distribution-download-check/wheel/oracle.json",
    )
    assert all(any(PurePosixPath(name).match(pattern) for pattern in patterns) for name in selected)
    assert not any(PurePosixPath(name).match(pattern) for pattern in patterns for name in excluded)


def test_evidence_context_declares_every_download_workspace_and_child_root(workflow):
    run = steps_by_id(workflow["jobs"]["linux311"])["evidence-context"]["run"]
    command = next(line for line in run.splitlines() if "evidence_privacy.py context" in line)
    words = command.split()
    declared = {
        option: [words[index + 1] for index, word in enumerate(words) if word == option]
        for option in ("--workspace", "--child-root")
    }
    for option, paths in declared.items():
        assert len(paths) == len(set(paths)), option  # each path is declared once
    for path in (
        ".local/upload-check",
        ".local/distribution-upload-check",
        ".local/download-check",
        ".local/distribution-download-check",
    ):
        assert path in declared["--workspace"], path
        assert path in declared["--child-root"], path


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
    needs = {cell: {"result": "success", "outputs": {}} for cell in CELLS}
    needs["linux311"]["outputs"]["startup_diagnostic"] = "passed"
    needs["linux311"]["outputs"]["startup_baseline_mode"] = "pinned_runtime"
    return needs


@pytest.mark.parametrize("mode", [None, "", "fallback", "initial_runtime_same_source_control"])
def test_aggregate_requires_and_displays_explicit_baseline_selection(workflow, tmp_path, mode):
    needs = successful_needs()
    needs["linux311"]["outputs"]["startup_baseline_mode"] = mode
    result = invoke_gate(workflow, tmp_path, json.dumps(needs))
    assert (result.returncode == 0) is (mode == "initial_runtime_same_source_control")


def test_actual_gate_accepts_all_success_without_a_checkout(workflow, tmp_path):
    result = invoke_gate(workflow, tmp_path, json.dumps(successful_needs()))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {cell: "success" for cell in CELLS}


def test_even_all_skipped_cells_cannot_satisfy_the_required_check(workflow, tmp_path):
    needs = {cell: {"result": "skipped"} for cell in CELLS}
    result = invoke_gate(workflow, tmp_path, json.dumps(needs))
    assert result.returncode != 0


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
    assert report["startup_budget_scope"] == (
        "source_bound_m5_and_linux_diagnostic" if budgets == "true" else "compatibility_only"
    )
    assert report["jobs_budget_scope"] == (
        "reference_receipt_macos_m5max_py311" if budgets == "true" else "compatibility_only"
    )
    assert report["raw_stream_budget_scope"] == scope
    assert report["upload_budget_scope"] == (
        "native_linux311_and_source_bound_m5" if budgets == "true" else "compatibility_only"
    )
    assert report["download_budget_scope"] == (
        "native_linux311_and_source_bound_m5" if budgets == "true" else "compatibility_only"
    )
    assert "do-not-record-ambient-values" not in encoded


def test_actual_environment_report_rejects_the_wrong_python(workflow, tmp_path, monkeypatch):
    code = environment_report_code(workflow)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTHON_VERSION", "0.0")
    with pytest.raises(SystemExit, match="does not match the required version"):
        exec(code, {})
    assert not (tmp_path / "dist/ci-environment.json").exists()


@pytest.mark.parametrize("outcome", [None, "", "error", "unknown", True])
def test_aggregate_rejects_missing_or_unverified_startup_diagnostics(workflow, tmp_path, outcome):
    needs = successful_needs()
    needs["linux311"]["outputs"]["startup_diagnostic"] = outcome
    assert invoke_gate(workflow, tmp_path, json.dumps(needs)).returncode != 0


def test_aggregate_allows_verified_budget_overrun_and_shows_it_without_performance_claim(
    workflow, tmp_path, monkeypatch
):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    needs = successful_needs()
    needs["linux311"]["outputs"]["startup_diagnostic"] = "diagnostic_budget_exceeded"
    assert invoke_gate(workflow, tmp_path, json.dumps(needs)).returncode == 0
    text = summary.read_text()
    assert "diagnostic_budget_exceeded" in text
    assert "M5 startup/jobs and Linux raw gates remain required" in text


def test_completed_measurement_is_guarded_before_artifact_upload(workflow):
    job = workflow["jobs"]["linux311"]
    assert job["outputs"] == {
        "startup_diagnostic": "${{ steps.startup-budgets.outputs.outcome }}",
        "startup_baseline_mode": "${{ steps.startup-budgets.outputs.baseline_mode }}",
    }
    steps = steps_by_id(job)
    guard = steps["startup-evidence-guard"]
    assert guard["if"] == (
        "${{ always() && env.RUN_BUDGETS == 'true' && steps.startup-budgets.outcome == 'success' }}"
    )
    assert "--verify-receipt" in guard["run"]
    assert list(steps).index("startup-evidence-guard") < list(steps).index("upload-evidence")
