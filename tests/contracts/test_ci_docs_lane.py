"""The workflow side of the documentation lane: the classification step, the test step and the gate.

``test_ci_changes.py`` pins the classifier script; these tests run the workflow's own shell steps
and its aggregate gate against real merge checkouts and hostile claims. The lane may never let a
pull request that touches more than documents skip the suite, and may never let a cell lie.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.contracts.test_ci_matrix import (
    CELLS,
    environment_report_code,
    invoke_gate,
    steps_by_id,
    successful_needs,
)
from tests.contracts.test_ci_matrix import workflow as workflow
from tests.fixtures.ci_git import git, isolate_git, write

ROOT = Path(__file__).resolve().parents[2]
CLASSIFIER = (ROOT / "scripts" / "ci_changes.py").read_text(encoding="utf-8")
GUARD = "steps.change-set.outputs.docs_only != 'true'"
READER = "text = open('docs/a.md').read()\n"
PYTEST_FLAGS = ["--dist", "loadfile", "--durations=25", "-o", "faulthandler_timeout=60"]


# --- structure --------------------------------------------------------------------------------


@pytest.mark.parametrize("cell", CELLS)
def test_every_cell_reports_the_classification_to_the_gate(workflow, cell):
    outputs = workflow["jobs"][cell]["outputs"]
    assert outputs["docs_only"] == "${{ steps.change-set.outputs.docs_only }}"


def test_the_classification_is_the_second_step_and_never_conditional(workflow):
    steps = workflow["jobs"]["linux311"]["steps"]
    assert steps[0]["uses"] == "actions/checkout@v4"
    assert steps[0]["with"]["fetch-depth"] == "0"  # the first parent must be reachable
    step = steps[1]
    assert step["id"] == "change-set"
    assert "if" not in step and "continue-on-error" not in step and "uses" not in step
    assert step["env"] == {
        "EVENT_NAME": "${{ github.event_name }}",
        "BASE_REF": "${{ github.base_ref }}",
    }
    run = step["run"]
    # The target branch's classifier decides, never the pull request's own copy.
    assert 'git show "HEAD^1:scripts/ci_changes.py"' in run
    assert "scripts/ci_changes.py classify" not in run
    assert 'git rev-parse -q --verify "HEAD^2"' in run


REFERENCE_VERIFIERS = (
    "startup-reference",
    "jobs-budgets",
    "dataset-budgets",
    "upload-reference",
    "download-reference",
)
NATIVE_MEASUREMENTS = (
    "startup-baseline",
    "startup-budgets",
    "raw-stream-budgets",
    "upload-budgets",
    "download-budgets",
    "startup-diagnostics",
)


def test_every_code_bound_measurement_is_skipped_for_a_documentation_change_set(workflow):
    steps = steps_by_id(workflow["jobs"]["linux311"])
    guarded = {step_id for step_id, step in steps.items() if GUARD in step.get("if", "")}
    assert guarded == set(NATIVE_MEASUREMENTS)
    for step_id in NATIVE_MEASUREMENTS:
        assert "RUN_BUDGETS == 'true'" in steps[step_id]["if"], step_id


def test_the_reference_verifiers_read_archived_documents_so_they_always_run(workflow):
    # A documentation change can replace a reference archive or its manifest entry: the catalogue
    # check alone would pass, the verifier would not. They only verify, and run on Linux 3.11 only.
    steps = steps_by_id(workflow["jobs"]["linux311"])
    for step_id in REFERENCE_VERIFIERS:
        assert steps[step_id]["if"] == "${{ success() && env.RUN_BUDGETS == 'true' }}", step_id
        assert "verify-" in steps[step_id]["run"] and "-reference" in steps[step_id]["run"]
    # The guard of a completed measurement only runs after the measurement itself ran.
    assert "steps.startup-budgets.outcome == 'success'" in steps["startup-evidence-guard"]["if"]


def test_what_a_documentation_change_can_still_break_always_runs(workflow):
    steps = steps_by_id(workflow["jobs"]["linux311"])
    for required in ("static-checks", "build", "tests", "environment-setup"):
        assert "if" not in steps[required], required


# --- the gate ---------------------------------------------------------------------------------


def docs_needs(**changes):
    needs = {cell: {"result": "success", "outputs": {"docs_only": "true"}} for cell in CELLS}
    for cell, value in changes.items():
        needs[cell]["outputs"]["docs_only"] = value
    return needs


def test_a_documentation_change_set_passes_without_the_code_bound_outputs(
    workflow, tmp_path, monkeypatch
):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    result = invoke_gate(workflow, tmp_path, json.dumps(docs_needs()))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {cell: "success" for cell in CELLS}
    assert "Documentation-only change set" in summary.read_text()
    assert "did not" in summary.read_text()  # the summary says what was not run


def test_a_code_change_set_still_needs_the_startup_outputs(workflow, tmp_path):
    needs = successful_needs()  # every cell says "false"
    assert invoke_gate(workflow, tmp_path, json.dumps(needs)).returncode == 0
    del needs["linux311"]["outputs"]["startup_diagnostic"]
    assert invoke_gate(workflow, tmp_path, json.dumps(needs)).returncode != 0
    del needs["linux311"]["outputs"]["startup_baseline_mode"]
    assert invoke_gate(workflow, tmp_path, json.dumps(needs)).returncode != 0


@pytest.mark.parametrize("cell", CELLS)
@pytest.mark.parametrize("claim", ["false", "", "True", "yes", "1", None, True, 1, [], {}])
def test_one_cell_that_disagrees_fails_the_gate(workflow, tmp_path, cell, claim):
    assert invoke_gate(workflow, tmp_path, json.dumps(docs_needs(**{cell: claim}))).returncode != 0


@pytest.mark.parametrize("cell", CELLS)
def test_a_missing_claim_fails_the_gate_in_both_directions(workflow, tmp_path, cell):
    needs = docs_needs()
    del needs[cell]["outputs"]["docs_only"]
    assert invoke_gate(workflow, tmp_path, json.dumps(needs)).returncode != 0
    needs = successful_needs()
    del needs[cell]["outputs"]["docs_only"]
    assert invoke_gate(workflow, tmp_path, json.dumps(needs)).returncode != 0


@pytest.mark.parametrize("cell", CELLS)
@pytest.mark.parametrize("status", ["failure", "cancelled", "skipped", "unknown", "", None])
def test_every_cell_must_still_succeed_for_a_documentation_change_set(
    workflow, tmp_path, cell, status
):
    needs = docs_needs()
    needs[cell]["result"] = status
    assert invoke_gate(workflow, tmp_path, json.dumps(needs)).returncode != 0


@pytest.mark.parametrize("outputs", [None, "true", ["true"], 1])
def test_malformed_outputs_fail_the_gate(workflow, tmp_path, outputs):
    needs = docs_needs()
    needs["macos311"]["outputs"] = outputs
    assert invoke_gate(workflow, tmp_path, json.dumps(needs)).returncode != 0


def test_a_claim_cannot_stand_in_for_a_cell_or_add_one(workflow, tmp_path):
    needs = docs_needs()
    needs["extra"] = {"result": "success", "outputs": {"docs_only": "true"}}
    assert invoke_gate(workflow, tmp_path, json.dumps(needs)).returncode != 0
    needs = docs_needs()
    del needs["linux314"]
    assert invoke_gate(workflow, tmp_path, json.dumps(needs)).returncode != 0


def test_all_skipped_cells_never_pass_even_with_a_documentation_claim(workflow, tmp_path):
    needs = {cell: {"result": "skipped", "outputs": {"docs_only": "true"}} for cell in CELLS}
    assert invoke_gate(workflow, tmp_path, json.dumps(needs)).returncode != 0


# --- the steps, run for real ------------------------------------------------------------------


@pytest.fixture(autouse=True)
def git_environment(monkeypatch):
    isolate_git(monkeypatch)


def assert_workers(arguments):
    """``-n N``: one worker fewer than the CPUs the process may use, at least one."""
    cpus = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count()
    assert arguments[0] == "-n"
    assert arguments[1] == str(max(1, cpus - 1))


def merge_checkout(tmp_path, change, *, classifier=CLASSIFIER, reader=READER):
    """A merge into ``development``; the base carries ``classifier`` (or none)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "development")
    write(repo, "src/a.py", "a\n")
    write(repo, "docs/a.md", "a\n")
    write(repo, "tests/contracts/test_reader.py", reader)
    write(repo, "tests/contracts/test_plain.py", "x = 1\n")
    if classifier is not None:
        write(repo, "scripts/ci_changes.py", classifier)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    git(repo, "switch", "-q", "-c", "feature")
    change(repo)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", "feature")
    git(repo, "switch", "-q", "development")
    write(repo, "docs/later.md")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "moved")
    git(repo, "update-ref", "refs/remotes/origin/development", "development")
    git(repo, "merge", "-q", "--no-ff", "-m", "merge", "feature")
    return repo


def run_step(script, repo, tmp_path, **environment):
    temp = tmp_path / "runner-temp"
    temp.mkdir(exist_ok=True)
    out = tmp_path / "output"
    out.write_text("", encoding="utf-8")
    summary = tmp_path / "summary"
    summary.write_text("", encoding="utf-8")
    env = {
        "PATH": os.environ["PATH"],
        "RUNNER_TEMP": str(temp),
        "GITHUB_OUTPUT": str(out),
        "GITHUB_STEP_SUMMARY": str(summary),
        **environment,
    }
    # GitHub's default shell for ``run`` steps.
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", script],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result, out.read_text(encoding="utf-8")


def classification(workflow, repo, tmp_path, event="pull_request", base="development"):
    step = steps_by_id(workflow["jobs"]["linux311"])["change-set"]
    return run_step(step["run"], repo, tmp_path, EVENT_NAME=event, BASE_REF=base)


def test_the_step_classifies_a_documentation_merge_as_documentation(workflow, tmp_path):
    repo = merge_checkout(tmp_path, lambda repo: write(repo, "docs/a.md", "changed\n"))
    result, output = classification(workflow, repo, tmp_path)
    assert result.returncode == 0, result.stderr
    assert output == "docs_only=true\n"


@pytest.mark.parametrize(
    "change",
    [
        lambda repo: (write(repo, "docs/a.md", "c\n"), write(repo, "src/a.py", "changed\n")),
        lambda repo: write(repo, "tests/contracts/test_plain.py", "x = 2\n"),
        lambda repo: write(repo, ".github/workflows/checks.yml", "name: x\n"),
        lambda repo: write(repo, "uv.lock", "x\n"),
        lambda repo: (repo / "src/a.py").unlink(),
    ],
    ids=["mixed", "test", "workflow", "lock", "deleted-source"],
)
def test_the_step_never_classifies_a_code_change_as_documentation(workflow, tmp_path, change):
    repo = merge_checkout(tmp_path, change)
    result, output = classification(workflow, repo, tmp_path)
    assert result.returncode == 0, result.stderr
    assert output == "docs_only=false\n"


def test_a_pull_request_cannot_classify_itself(workflow, tmp_path):
    liar = "import sys\nsys.stdout.write('true\\n')\n"

    def change(repo):
        write(repo, "scripts/ci_changes.py", liar)  # its own copy says "true" for everything
        write(repo, "src/a.py", "changed\n")

    repo = merge_checkout(tmp_path, change)
    assert (repo / "scripts/ci_changes.py").read_text() == liar  # the checkout holds the lie
    result, output = classification(workflow, repo, tmp_path)
    assert result.returncode == 0, result.stderr
    assert output == "docs_only=false\n"  # the base's copy judged the change set


@pytest.mark.parametrize(
    "classifier",
    [
        None,
        "raise SystemExit(3)\n",
        "this is not python(\n",
        "print('maybe')\n",
        "print('true extra')\n",
    ],
    ids=["absent-on-base", "fails", "syntax-error", "other-word", "extra-word"],
)
def test_a_missing_or_unreliable_base_classifier_runs_everything(workflow, tmp_path, classifier):
    repo = merge_checkout(
        tmp_path, lambda repo: write(repo, "docs/a.md", "changed\n"), classifier=classifier
    )
    result, output = classification(workflow, repo, tmp_path)
    assert result.returncode == 0, result.stderr
    assert output == "docs_only=false\n"


@pytest.mark.parametrize(
    ("event", "base"),
    [("push", "development"), ("workflow_dispatch", ""), ("pull_request", "Master"), ("", "")],
)
def test_only_a_pull_request_into_development_is_ever_classified_as_documentation(
    workflow, tmp_path, event, base
):
    repo = merge_checkout(tmp_path, lambda repo: write(repo, "docs/a.md", "changed\n"))
    result, output = classification(workflow, repo, tmp_path, event=event, base=base)
    assert result.returncode == 0, result.stderr
    assert output == "docs_only=false\n"


def test_a_checkout_that_is_not_a_merge_runs_everything(workflow, tmp_path):
    repo = merge_checkout(tmp_path, lambda repo: write(repo, "docs/a.md", "changed\n"))
    git(repo, "reset", "-q", "--hard", "HEAD^1")  # a plain commit: no second parent
    result, output = classification(workflow, repo, tmp_path)
    assert result.returncode == 0, result.stderr
    assert output == "docs_only=false\n"


def workflow_tests_step(workflow):
    return steps_by_id(workflow["jobs"]["linux311"])["tests"]["run"]


def selected_arguments(workflow, repo, tmp_path, docs_only):
    """What the tests step would pass to pytest, with pytest replaced by a printer."""
    classified, _ = classification(workflow, repo, tmp_path)
    assert classified.returncode == 0, classified.stderr
    script = workflow_tests_step(workflow).replace(".venv/bin/pytest", "printf '%s\\n'")
    result, _ = run_step(script, repo, tmp_path, DOCS_ONLY=docs_only)
    assert result.returncode == 0, result.stderr
    return result.stdout.splitlines()


def test_the_documentation_lane_runs_only_the_tests_that_read_documents(workflow, tmp_path):
    repo = merge_checkout(tmp_path, lambda repo: write(repo, "docs/a.md", "changed\n"))
    lines = selected_arguments(workflow, repo, tmp_path, "true")
    arguments = lines[lines.index("-n") :]  # what follows the echo of the selection
    assert_workers(arguments[:2])
    assert arguments[2:7] == PYTEST_FLAGS
    assert arguments[7:] == ["tests/contracts/test_reader.py"]  # a concrete selection, not the tree


@pytest.mark.parametrize("docs_only", ["false", "", "maybe"])
def test_anything_but_a_documentation_claim_runs_the_whole_suite(workflow, tmp_path, docs_only):
    repo = merge_checkout(tmp_path, lambda repo: write(repo, "docs/a.md", "changed\n"))
    lines = selected_arguments(workflow, repo, tmp_path, docs_only)
    assert_workers(lines[:2])
    assert lines[2:] == PYTEST_FLAGS  # no selection: pytest runs ``testpaths``


def test_a_selection_that_fails_or_is_empty_runs_everything(workflow, tmp_path):
    # The classifier says "true" for the change set but cannot produce a selection.
    classifier = (
        "import sys\nif sys.argv[1] == 'classify':\n    print('true')\nelse:\n    sys.exit(3)\n"
    )
    repo = merge_checkout(
        tmp_path, lambda repo: write(repo, "docs/a.md", "changed\n"), classifier=classifier
    )
    lines = selected_arguments(workflow, repo, tmp_path, "true")
    assert lines[-1] == "tests"
    empty = classifier.replace("sys.exit(3)", "pass")
    other = tmp_path / "second"
    other.mkdir()
    repo = merge_checkout(
        other, lambda repo: write(repo, "docs/a.md", "changed\n"), classifier=empty
    )
    assert selected_arguments(workflow, repo, other, "true")[-1] == "tests"


def test_the_lane_runs_everything_when_no_test_reads_a_document(workflow, tmp_path):
    repo = merge_checkout(
        tmp_path, lambda repo: write(repo, "docs/a.md", "changed\n"), reader="x = 1\n"
    )
    lines = selected_arguments(workflow, repo, tmp_path, "true")
    assert lines[-1] == "tests"


def test_the_classifier_imports_only_the_standard_library():
    # The step runs it with the runner's own ``python3``, where nothing else is installed.
    import ast

    imported = set()
    for node in ast.walk(ast.parse(CLASSIFIER)):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            imported.add((node.module or "").split(".")[0])
    assert imported <= set(sys.stdlib_module_names), imported


# --- the evidence record says what the cell really ran ----------------------------------------


@pytest.mark.parametrize(
    ("docs_only", "budgets", "expected"),
    [
        (
            "true",
            "true",
            "documentation_lane",
        ),  # Linux 3.11 keeps RUN_BUDGETS but ran no measurement
        ("true", "false", "documentation_lane"),
        ("false", "false", "compatibility_only"),
    ],
)
def test_the_environment_report_does_not_claim_budgets_the_lane_did_not_run(
    workflow, tmp_path, monkeypatch, docs_only, budgets, expected
):
    code = environment_report_code(workflow)
    monkeypatch.chdir(tmp_path)
    for key, value in {
        "PYTHON_VERSION": f"{sys.version_info.major}.{sys.version_info.minor}",
        "RUN_BUDGETS": budgets,
        "DOCS_ONLY": docs_only,
        "GITHUB_SHA": "b" * 40,
        "CI_JOB": "linux311",
        "RUNNER_LABEL": "ubuntu-24.04",
        "RUNNER_OS": "Linux",
        "RUNNER_ARCH": "X64",
    }.items():
        monkeypatch.setenv(key, value)
    original = subprocess.check_output

    def check_output(command, **kwargs):
        if tuple(command) == ("git", "rev-parse", "HEAD"):
            return "a" * 40 + "\n"
        if tuple(command) == (".ci-tools/bin/uv", "--version"):
            return "uv 0.11.2\n"
        return original(command, **kwargs)

    monkeypatch.setattr(subprocess, "check_output", check_output)
    exec(code, {})
    report = json.loads((tmp_path / "dist/ci-environment.json").read_text(encoding="utf-8"))
    scopes = {key: value for key, value in report.items() if key.endswith("_budget_scope")}
    assert set(scopes) == {
        "startup_budget_scope",
        "jobs_budget_scope",
        "raw_stream_budget_scope",
        "upload_budget_scope",
        "download_budget_scope",
    }
    assert set(scopes.values()) == {expected}
