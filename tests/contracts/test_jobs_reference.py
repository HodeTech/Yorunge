"""Reference proofs bind declared M5 measurements to the complete current source scope."""

import copy
import gzip
import hashlib
import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
CHECKS = runpy.run_path(str(ROOT / "scripts/research_evidence.py"))
NAME = "reference-jobs.json"


@pytest.fixture
def reference(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    contents = {
        "src/yorunge/__init__.py": b"__version__ = 'fixture'\n",
        "tests/fixtures/seed_jobs.py": b"# synthetic fixture\n",
        "tests/conftest.py": b"# synthetic test setup\n",
        "examples/profile.toml": b"name = 'fixture'\n",
        ".github/workflows/checks.yml": b"name: synthetic checks\n",
        "pyproject.toml": b"[project]\nname = 'yorunge'\nversion = '0.1.0.dev0'\n",
        "uv.lock": (
            b"version = 1\n[[package]]\nname = 'yorunge'\nversion = '0.1.0.dev0'\n"
            b"dependencies = [{name = 'httpx'}]\n"
            b"[[package]]\nname = 'httpx'\nversion = '0.28.1'\n"
        ),
        "scripts/benchmark-jobs.py": (ROOT / "scripts/benchmark-jobs.py").read_bytes(),
        "scripts/research_evidence.py": (ROOT / "scripts/research_evidence.py").read_bytes(),
    }
    for name, content in contents.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    expected = {name: hashlib.sha256(content).hexdigest() for name, content in contents.items()}
    revision = {"value": "c" * 40, "commands": []}
    real_run_path = runpy.run_path

    def load_producer(path):
        namespace = real_run_path(path)
        assert Path(path) == root / "scripts/benchmark-jobs.py"

        def git_only(command, *, cwd):
            assert command == ["git", "rev-parse", "HEAD"]
            assert cwd == root
            revision["commands"].append(command)
            return subprocess.CompletedProcess(command, 0, revision["value"] + "\n", "")

        namespace["source"].__globals__["run"] = git_only
        return namespace

    monkeypatch.setattr(runpy, "run_path", load_producer)
    return root, receipt(expected), revision


def receipt(source_hashes):
    """Handwritten measurement values and metadata; no benchmark producer oracle."""
    source = {"commit": "a" * 40, "source_sha256": source_hashes}
    installed = {
        "python": "3.11.14 (fixture build)",
        "executable": "/runtime/bin/python",
        "prefix": "/runtime",
        "platform": "macOS-27.0.1-arm64-arm-64bit",
        "machine": "arm64",
        "sqlite": "3.50.4",
        "packages": {"yorunge": "0.1.0.dev0", "httpx": "0.28.1"},
        "product_origin": "/runtime/lib/yorunge",
        "product_version": "0.1.0.dev0",
        "console": "/runtime/bin/yorunge",
        "console_sha256": "b" * 64,
        "installed_source_sha256": {
            "yorunge/__init__.py": source_hashes["src/yorunge/__init__.py"]
        },
    }
    runs = []
    for layout in ("normal", "dense"):
        for action in ("list", "show"):
            runs.append(
                {
                    "layout": layout,
                    "action": action,
                    "command": [
                        "/runtime/bin/python",
                        "-I",
                        "/runtime/bin/yorunge",
                        "jobs",
                        action,
                        "--limit" if action == "list" else "--operation-id",
                        "50" if action == "list" else "00000000-0000-4000-8000-000000000001",
                        "--state-dir",
                        "/fixture/" + layout,
                        "--output",
                        "json",
                    ],
                    "first_process_ms": 12,
                    "warmups_ms": [11, 12, 10],
                    "samples_ms": [10] * 30,
                    "median_ms": 10,
                    "p95_ms": 10,
                    "budget_ms": 200,
                    "passed": True,
                    "typed_stdout_verified": True,
                    "verified_processes": 34,
                    "stdout_sha256": ["d" * 64] * 34,
                    "expected_list_rows": (1 if layout == "normal" else 50)
                    if action == "list"
                    else None,
                    "expected_operation_id": None
                    if action == "list"
                    else "00000000-0000-4000-8000-000000000001",
                    "expected_plan_digest": None if action == "list" else "e" * 64,
                }
            )
    return {
        "schema_version": 1,
        "kind": "jobs",
        "source_commit": "a" * 40,
        "samples_per_command": 30,
        "method": "three warmups, nearest-rank p95, every sample",
        "cold_method": "first process, uncontrolled OS caches",
        "validation_method": "typed fixture",
        "environment": {
            "runtime": installed,
            "cpu": "Apple M5 Max",
            "disk_type": "internal SSD/APFS",
        },
        "fixtures": {layout: fixture(layout) for layout in ("normal", "dense")},
        "runs": runs,
        "provenance": {
            "source_before": source,
            "source_after": copy.deepcopy(source),
            "installed_before": installed,
            "installed_after": copy.deepcopy(installed),
            "wheel_sha256": "f" * 64,
            "wheel_path": "/artifacts/yorunge.whl",
            "source_unchanged_during_measurement": True,
            "installed_unchanged_during_measurement": True,
            "fixtures_unchanged_during_measurement": True,
            "unchanged": True,
            "isolated_python": True,
            "fixture_preparation_python": "/development/bin/python",
            "fixture_preparation": "synthetic fixture prepared outside measured processes",
        },
        "passed": True,
    }


def test_reference_page_cannot_reuse_one_plan_for_multiple_operations(reference):
    root, report, _ = reference
    summaries = report["fixtures"]["dense"]["list_summaries"]
    summaries[-1]["plan_id"] = summaries[0]["plan_id"]
    archive(root, report)
    with pytest.raises(ValueError, match="duplicate plan IDs"):
        CHECKS["verify_jobs_reference"](root, NAME)


def fixture(layout):
    counts = {
        "operations": (1, 1024),
        "operation_attempts": (1, 16384),
        "operation_events": (3, 262144),
        "operation_outcomes": (0, 1024),
        "execution_plans": (1, 1024),
        "execution_approvals": (1, 1024),
        "capability_cache": (1, 1024),
    }
    rows = {}
    for table, cases in counts.items():
        count = cases[layout == "dense"]
        rows[table] = {
            "records": count,
            "payload_bytes": count * 100,
            "largest_record_bytes": 100 if count else 0,
        }
    if layout == "dense":
        rows["execution_plans"].update(payload_bytes=67108864, largest_record_bytes=65536)
        rows["capability_cache"].update(payload_bytes=33554432, largest_record_bytes=32768)
    summaries = [summary(index, layout) for index in range(50 if layout == "dense" else 1)]
    return {
        "rows": rows,
        "database_bytes": 200 * 1024 * 1024,
        "database_sha256": "9" * 64,
        "list_summaries": summaries,
        "has_next_cursor": layout == "dense",
        "show_summary": summaries[0],
        "show_attempts": [
            attempt(index, layout) for index in range(1, 17 if layout == "dense" else 2)
        ],
        "show_outcome": {
            "schema_version": 1,
            "recorded_at": "2026-10-29T00:00:00.000000Z",
            "execution_status": "succeeded",
            "delivery_status": "complete",
            "provider_exit_code": 0,
            "reason_code": None,
        }
        if layout == "dense"
        else None,
    }


def summary(index, layout):
    return {
        "operation_id": f"00000000-0000-4000-8000-{index + 1:012d}",
        "plan_id": f"10000000-0000-4000-8000-{index + 1:012d}",
        "plan_digest": "e" * 64,
        "task": "llm.train",
        "tool": "forgelm",
        "execution": "local",
        "created_at": "2026-10-29T00:00:00.000000Z",
        "updated_at": "2026-10-29T00:00:00.000000Z",
        "status": "succeeded" if layout == "dense" else "running",
        "execution_status": "succeeded" if layout == "dense" else "running",
        "delivery_status": "complete" if layout == "dense" else "pending",
        "attempt_count": 16 if layout == "dense" else 1,
        "revision": 271 if layout == "dense" else 3,
        "clock_anomaly": False,
    }


def attempt(index, layout):
    current = index == (16 if layout == "dense" else 1)
    return {
        "attempt_id": f"20000000-0000-4000-8000-{index:012d}",
        "number": index,
        "created_at": "2026-10-29T00:00:00.000000Z",
        "updated_at": "2026-10-29T00:00:00.000000Z",
        "status": ("succeeded" if layout == "dense" else "running") if current else "abandoned",
        "provider_run_id": "fixture-current" if current else None,
        "provider_status": ("complete" if layout == "dense" else "running") if current else None,
        "provider_exit_code": 0 if layout == "dense" and current else None,
        "reason_code": None if current else "owner_changed",
    }


def archive(root, report):
    (root / "docs/research").mkdir(parents=True, exist_ok=True)
    (root / "dist").mkdir(exist_ok=True)
    source = root / "dist" / NAME
    source.write_bytes((json.dumps(report, indent=2) + "\n").encode())
    CHECKS["archive_report"](root, source, None)


def unchecked_archive(root, report):
    """Allow malformed measurement data to reach the reader through intact gzip bytes."""
    directory = root / "docs/research"
    (directory / "raw").mkdir(parents=True)
    content = (json.dumps(report) + "\n").encode()
    packed = gzip.compress(content, mtime=0)
    item = {
        "name": NAME,
        "archive": "raw/" + NAME + ".gz",
        "original_commit": None,
        "content_bytes": len(content),
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "archive_bytes": len(packed),
        "archive_sha256": hashlib.sha256(packed).hexdigest(),
        "summary": {"kind": "jobs"},
    }
    (directory / "raw" / (NAME + ".gz")).write_bytes(packed)
    (directory / "evidence-manifest.json").write_bytes(
        CHECKS["encode"](
            {"schema_version": 1, "entries": [item]},
        )
    )
    (directory / "evidence.md").write_text(CHECKS["index_text"]([item]))


def test_source_bound_reference_uses_current_complete_producer_scope_and_frozen_runtime(reference):
    root, report, revision = reference
    archive(root, report)
    result = CHECKS["verify_jobs_reference"](root, NAME)
    assert result == {
        "name": NAME,
        "source_commit": "a" * 40,
        "cpu": "Apple M5 Max",
        "p95_ms": {
            "normal/list": 10.0,
            "normal/show": 10.0,
            "dense/list": 10.0,
            "dense/show": 10.0,
        },
    }
    assert revision["commands"] == [["git", "rev-parse", "HEAD"]]


def test_docs_only_commit_change_keeps_reference_valid_when_measured_bytes_are_equal(reference):
    root, report, revision = reference
    archive(root, report)
    (root / "docs/new-review.md").write_text("Independent prose change.\n")
    revision["value"] = "d" * 40
    assert CHECKS["verify_jobs_reference"](root, NAME)["source_commit"] == "a" * 40


@pytest.mark.parametrize(
    "path",
    [
        "src/yorunge/__init__.py",
        "scripts/benchmark-jobs.py",
        "scripts/research_evidence.py",
        "tests/fixtures/seed_jobs.py",
        "tests/conftest.py",
        "examples/profile.toml",
        "pyproject.toml",
        "uv.lock",
        ".github/workflows/checks.yml",
    ],
)
def test_every_changed_measured_input_invalidates_reference_even_before_git_commit(reference, path):
    root, report, _ = reference
    archive(root, report)
    with (root / path).open("a") as stream:
        stream.write("\n# uncommitted byte change\n")
    with pytest.raises(ValueError, match="complete current source bytes"):
        CHECKS["verify_jobs_reference"](root, NAME)


@pytest.mark.parametrize(
    "path",
    [
        "src/yorunge/new.py",
        "scripts/new.py",
        "tests/fixtures/new.py",
        "tests/__init__.py",
        "tests/fixtures/__init__.py",
        "tests/contracts/__init__.py",
        "tests.py",
        "fixtures.py",
        "src/tests.py",
        "src/unrelated/import_guard.py",
        "tests/fixtures.py",
    ],
)
def test_new_measured_inputs_invalidate_prior_reference(reference, path):
    root, report, _ = reference
    archive(root, report)
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    (root / path).write_text("# newly added source\n")
    with pytest.raises(ValueError, match="complete current source bytes"):
        CHECKS["verify_jobs_reference"](root, NAME)


@pytest.mark.parametrize("change", ["modify", "delete"])
def test_checked_initializer_edits_and_removal_invalidate_reference(reference, change):
    root, report, _ = reference
    initializer = root / "tests/__init__.py"
    original = b"CHECKED_INITIALIZER = True\n"
    initializer.write_bytes(original)
    for snapshot in ("source_before", "source_after"):
        report["provenance"][snapshot]["source_sha256"]["tests/__init__.py"] = hashlib.sha256(
            original
        ).hexdigest()
    archive(root, report)
    if change == "modify":
        initializer.write_text("raise RuntimeError('changed initializer')\n")
    else:
        initializer.unlink()
    with pytest.raises(ValueError, match="complete current source bytes"):
        CHECKS["verify_jobs_reference"](root, NAME)


def test_unrelated_local_and_document_python_are_outside_the_public_import_scope(reference):
    root, report, _ = reference
    archive(root, report)
    for name in (".local/ignored.py", "docs/ignored.py"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("raise RuntimeError('not an import input')\n")
    assert CHECKS["verify_jobs_reference"](root, NAME)["cpu"] == "Apple M5 Max"


@pytest.mark.parametrize(
    "damage", ["missing_map_key", "added_map_key", "changed_map_value", "minimal"]
)
def test_old_extra_or_partial_measurement_map_cannot_stand_in_for_current_full_map(
    reference, damage
):
    root, report, _ = reference
    for key in ("source_before", "source_after"):
        hashes = report["provenance"][key]["source_sha256"]
        if damage == "missing_map_key":
            del hashes[".github/workflows/checks.yml"]
        elif damage == "added_map_key":
            hashes["scripts/deleted.py"] = "0" * 64
        elif damage == "changed_map_value":
            hashes["tests/conftest.py"] = "0" * 64
        else:
            report["provenance"][key]["source_sha256"] = {
                "src/yorunge/__init__.py": hashes["src/yorunge/__init__.py"],
            }
    archive(root, report)
    with pytest.raises(ValueError, match="complete current source bytes"):
        CHECKS["verify_jobs_reference"](root, NAME)


@pytest.mark.parametrize(
    "key,value",
    [
        ("cpu", "AMD EPYC 7763"),
        ("cpu", None),
        ("disk_type", "unknown"),
        ("machine", "x86_64"),
        ("platform", "Linux-6.1-arm64"),
        ("platform", "macOS-27.0.2-arm64"),
        ("python", "3.14.0"),
    ],
)
def test_same_fast_code_on_other_declared_hardware_is_not_the_configured_reference(
    reference, key, value
):
    root, report, _ = reference
    if key in {"cpu", "disk_type"}:
        report["environment"][key] = value
    else:
        for snapshot in ("installed_before", "installed_after"):
            report["provenance"][snapshot][key] = value
    archive(root, report)
    with pytest.raises(ValueError, match="configured M5 reference"):
        CHECKS["verify_jobs_reference"](root, NAME)


@pytest.mark.parametrize("damage", ["extra", "missing", "wrong_version"])
def test_reference_runtime_packages_must_equal_the_current_frozen_lock(reference, damage):
    root, report, _ = reference
    for snapshot in ("installed_before", "installed_after"):
        packages = report["provenance"][snapshot]["packages"]
        if damage == "extra":
            packages["unexpected-runtime-package"] = "1.0"
        elif damage == "missing":
            del packages["httpx"]
        else:
            packages["httpx"] = "0.27.0"
    archive(root, report)
    with pytest.raises(ValueError, match="current frozen lock"):
        CHECKS["verify_jobs_reference"](root, NAME)


@pytest.mark.parametrize(
    "damage",
    [
        "missing",
        "tiny_dense",
        "missing_table",
        "wrong_count",
        "small_plan_payload",
        "small_cache_payload",
        "wrong_max_payload",
        "short_list",
        "cursor",
        "bool_cursor",
        "list_expectation",
        "bool_list_expectation",
        "show_id",
        "show_digest",
        "show_target",
    ],
)
def test_reference_requires_the_declared_normal_and_dense_acceptance_workloads(reference, damage):
    root, report, _ = reference
    dense = report["fixtures"]["dense"]
    if damage == "missing":
        report["fixtures"]["dense"] = {}
    elif damage == "tiny_dense":
        report["fixtures"]["dense"] = copy.deepcopy(report["fixtures"]["normal"])
    elif damage == "missing_table":
        del dense["rows"]["operation_events"]
    elif damage == "wrong_count":
        dense["rows"]["operation_events"]["records"] = 1
    elif damage == "small_plan_payload":
        dense["rows"]["execution_plans"].update(payload_bytes=102400, largest_record_bytes=100)
    elif damage == "small_cache_payload":
        dense["rows"]["capability_cache"].update(payload_bytes=102400, largest_record_bytes=100)
    elif damage == "wrong_max_payload":
        dense["rows"]["execution_plans"]["largest_record_bytes"] = 131072
    elif damage == "short_list":
        dense["list_summaries"].pop()
    elif damage == "cursor":
        dense["has_next_cursor"] = False
    elif damage == "bool_cursor":
        dense["has_next_cursor"] = 1
    elif damage in {"list_expectation", "bool_list_expectation"}:
        report["runs"][2]["expected_list_rows"] = 1 if damage == "list_expectation" else True
    elif damage == "show_id":
        report["runs"][3]["expected_operation_id"] = "another-operation"
        report["runs"][3]["command"][6] = "another-operation"
    elif damage == "show_digest":
        report["runs"][3]["expected_plan_digest"] = "0" * 64
    else:
        dense["show_summary"] = {"operation_id": "other-operation", "plan_digest": "0" * 64}
    archive(root, report)
    with pytest.raises(ValueError):
        CHECKS["verify_jobs_reference"](root, NAME)


@pytest.mark.parametrize(
    "damage",
    [
        "last_none",
        "last_extra",
        "last_bad_time",
        "last_bool_attempts",
        "last_bool_clock",
        "last_wrong_layout",
        "duplicate_operation_id",
        "attempts_text",
        "attempt_none",
        "attempt_bool_number",
        "missing_attempt",
        "attempt_order",
        "duplicate_attempt_id",
        "attempt_wrong_status",
        "attempt_bool_exit",
        "outcome_false",
        "outcome_none",
        "outcome_bool_exit",
        "outcome_bool_version",
        "outcome_wrong_layout",
        "normal_outcome_false",
    ],
)
def test_every_reference_summary_attempt_and_outcome_has_strict_typed_layout_shape(
    reference, damage
):
    root, report, _ = reference
    dense = report["fixtures"]["dense"]
    last = dense["list_summaries"][-1]
    attempts = dense["show_attempts"]
    if damage == "last_none":
        dense["list_summaries"][-1] = None
    elif damage == "last_extra":
        last["unchecked"] = True
    elif damage == "last_bad_time":
        last["created_at"] = "yesterday"
    elif damage == "last_bool_attempts":
        last["attempt_count"] = True
    elif damage == "last_bool_clock":
        last["clock_anomaly"] = 0
    elif damage == "last_wrong_layout":
        last.update(
            status="running", execution_status="running", delivery_status="pending", attempt_count=1
        )
    elif damage == "duplicate_operation_id":
        last["operation_id"] = dense["list_summaries"][0]["operation_id"]
    elif damage == "attempts_text":
        dense["show_attempts"] = "invalid"
    elif damage == "attempt_none":
        attempts[14] = None
    elif damage == "attempt_bool_number":
        attempts[0]["number"] = True
    elif damage == "missing_attempt":
        attempts.pop()
    elif damage == "attempt_order":
        attempts[0], attempts[1] = attempts[1], attempts[0]
    elif damage == "duplicate_attempt_id":
        attempts[-1]["attempt_id"] = attempts[0]["attempt_id"]
    elif damage == "attempt_wrong_status":
        attempts[-1]["status"] = "running"
    elif damage == "attempt_bool_exit":
        attempts[-1]["provider_exit_code"] = False
    elif damage == "outcome_false":
        dense["show_outcome"] = False
    elif damage == "outcome_none":
        dense["show_outcome"] = None
    elif damage == "outcome_bool_exit":
        dense["show_outcome"]["provider_exit_code"] = False
    elif damage == "outcome_bool_version":
        dense["show_outcome"]["schema_version"] = True
    elif damage == "outcome_wrong_layout":
        dense["show_outcome"].update(execution_status="running", delivery_status="pending")
    else:
        report["fixtures"]["normal"]["show_outcome"] = False
    archive(root, report)
    # Generic archived receipt semantics stay descriptive; only the reference gate tightens.
    assert CHECKS["verify"](root) == 1
    with pytest.raises(ValueError):
        CHECKS["verify_jobs_reference"](root, NAME)


@pytest.mark.parametrize(
    "damage", ["one_layout", "all_normal", "alias_same_store", "normal_mismatch"]
)
def test_reference_commands_bind_both_actions_to_distinct_canonical_layout_state_paths(
    reference, damage
):
    root, report, _ = reference
    runs = report["runs"]
    if damage == "one_layout":
        runs[3]["command"][8] = "/different/dense"
    elif damage == "all_normal":
        for run in runs:
            run["command"][8] = "/fixture/normal"
    elif damage == "alias_same_store":
        for run in runs:
            run["command"][8] = "/tmp/same" if run["layout"] == "normal" else "/private/tmp/same"
    else:
        runs[1]["command"][8] = "/different/normal"
    archive(root, report)
    with pytest.raises(ValueError, match="distinct state path"):
        CHECKS["verify_jobs_reference"](root, NAME)


@pytest.mark.parametrize(
    "flag", ["isolated_python", "fixtures_unchanged_during_measurement", "unchanged"]
)
def test_truthful_failed_provenance_is_valid_history_but_not_a_passing_reference(reference, flag):
    root, report, _ = reference
    report["provenance"][flag] = False
    if flag == "fixtures_unchanged_during_measurement":
        report["provenance"]["unchanged"] = False
    report["passed"] = False
    archive(root, report)
    assert CHECKS["verify"](root) == 1
    with pytest.raises(ValueError, match="four passing"):
        CHECKS["verify_jobs_reference"](root, NAME)


@pytest.mark.parametrize("samples", [29, 31])
def test_reference_requires_exactly_thirty_measurement_processes_per_case(reference, samples):
    root, report, _ = reference
    report["samples_per_command"] = samples
    for run in report["runs"]:
        run.update(
            samples_ms=[10] * samples,
            verified_processes=samples + 4,
            stdout_sha256=["d" * 64] * (samples + 4),
        )
    if samples < 30:
        unchecked_archive(root, report)
    else:
        archive(root, report)
    with pytest.raises(ValueError):
        CHECKS["verify_jobs_reference"](root, NAME)


@pytest.mark.parametrize(
    "damage", ["p95", "wrong_origin", "installed_bytes", "commit_drift", "typed"]
)
def test_reference_reuses_closed_modern_verifier_for_p95_origin_and_measurement_flags(
    reference, damage
):
    root, report, _ = reference
    if damage == "p95":
        report["runs"][0]["samples_ms"][-2:] = [201, 205]
    elif damage == "wrong_origin":
        for snapshot in ("installed_before", "installed_after"):
            report["provenance"][snapshot]["product_origin"] = "/outside/yorunge"
    elif damage == "installed_bytes":
        for snapshot in ("installed_before", "installed_after"):
            report["provenance"][snapshot]["installed_source_sha256"]["yorunge/__init__.py"] = (
                "0" * 64
            )
    elif damage == "commit_drift":
        report["provenance"]["source_after"]["commit"] = "b" * 40
    else:
        report["runs"][0]["typed_stdout_verified"] = False
    unchecked_archive(root, report)
    with pytest.raises(ValueError):
        CHECKS["verify_jobs_reference"](root, NAME)


@pytest.mark.parametrize("kind", ["legacy", "operation", "missing_provenance"])
def test_reference_rejects_non_modern_jobs_evidence(reference, kind):
    root, report, _ = reference
    if kind == "legacy":
        report = {
            "runs": [
                {
                    "layout": "old",
                    "action": "list",
                    "samples_ms": [10] * 30,
                    "p95_ms": 10,
                    "budget_ms": 200,
                    "passed": True,
                }
            ]
        }
    elif kind == "operation":
        report = {"runs": [{"outcome": "ok"}]}
    else:
        del report["provenance"]
        unchecked_archive(root, report)
    if kind != "missing_provenance":
        archive(root, report)
    with pytest.raises(ValueError):
        CHECKS["verify_jobs_reference"](root, NAME)


@pytest.mark.parametrize("damage", ["manifest", "index", "archive", "missing_name", "bad_name"])
def test_reference_gate_requires_registered_intact_evidence_and_current_index(reference, damage):
    root, report, _ = reference
    archive(root, report)
    directory = root / "docs/research"
    name = NAME
    if damage == "manifest":
        (directory / "evidence-manifest.json").unlink()
    elif damage == "index":
        (directory / "evidence.md").write_text("stale index\n")
    elif damage == "archive":
        (directory / "raw" / (NAME + ".gz")).write_bytes(b"damaged gzip")
    elif damage == "missing_name":
        name = "unregistered.json"
    else:
        name = "../reference-jobs.json"
    with pytest.raises((ValueError, OSError)):
        CHECKS["verify_jobs_reference"](root, name)


def test_cli_emits_one_clear_reference_proof_line_without_claiming_a_benchmark_rerun(
    reference,
    monkeypatch,
    capsys,
):
    root, report, _ = reference
    archive(root, report)
    monkeypatch.setitem(
        CHECKS["main"].__globals__, "__file__", str(root / "scripts/research_evidence.py")
    )
    monkeypatch.setattr(sys, "argv", ["research_evidence.py", "verify-jobs-reference", NAME])
    assert CHECKS["main"]() == 0
    output = capsys.readouterr()
    assert output.err == ""
    assert output.out.splitlines() == [
        f"Jobs reference proof validated: {NAME}; four 30-process cases, "
        "each p95 <= 200 ms; current source bytes match the declared M5 reference.",
    ]
