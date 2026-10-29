"""Independent negative oracles for startup acceptance and source equivalence."""

import copy
import hashlib
import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.startup_receipt import receipt

ROOT = Path(__file__).resolve().parents[2]
HELPERS = runpy.run_path(str(ROOT / "scripts/startup_evidence.py"))


def test_handwritten_vector_recomputes_all_eight_metrics_and_preserves_v2_history():
    summary = HELPERS["validate"](receipt())
    assert summary["passed"] is True
    assert len(summary["measurements"]) == 8
    assert summary["outcome"] == "passed"
    assert HELPERS["CHECKS"]["summarize"](receipt())["kind"] == "startup_evidence"


@pytest.mark.parametrize(
    "path,value",
    [
        (("schema_version",), True),
        (("schema_version",), 2),
        (("report_kind",), "startup_v2"),
        (("measurement_exit",), True),
        (("measurement_exit",), 1),
        (("passed",), False),
        (("measurement", "schema_version"), True),
        (("measurement", "samples_per_command"), True),
        (("measurement", "samples_per_command"), 29),
        (("measurement", "profile_bytes"), True),
        (("measurement", "comparison", "baseline_cache_dataset", "records"), 1024.0),
        (("output_checks", "baseline", "version", "expected_version"), "wrong"),
        (("measurement", "cache_dataset", "records"), True),
        (("measurement", "cold_method"), "physical cold boot"),
        (("measurement", "comparison", "method"), "best of 30"),
        (("measurement", "comparison", "acceptance"), "baseline ratio"),
        (("measurement", "comparison", "baseline_cache_dataset", "records"), 1023),
        (("measurement", "cpu_affinity"), [1, 1]),
        (("measurement", "cpu_affinity"), [True]),
        (("measurement", "measurements", "help", "target_ms"), 501),
        (("measurement", "measurements", "help", "warm_p95_ms"), 9.0),
        (("measurement", "measurements", "help", "warm_median_ms"), 9.0),
        (("measurement", "measurements", "help", "warm_samples_ms"), [10.0] * 29),
        (("measurement", "measurements", "help", "warm_samples_ms"), [float("nan")] * 30),
        (("measurement", "measurements", "help", "warm_samples_ms"), [0.0] * 30),
        (("measurement", "measurements", "help", "passed"), 1),
        (("measurement", "measurements", "cache", "fresh_cache_hit_verified"), False),
        (("measurement", "comparison", "paired_comparisons", "cache", "pairs"), True),
        (("output_checks", "candidate", "cache", "typed_stdout_verified"), False),
        (("output_checks", "candidate", "cache", "verified_processes"), 33),
        (("output_checks", "candidate", "cache", "stdout_sha256"), ["a" * 64] * 33),
        (("output_checks", "candidate", "cache", "wall_ms"), [20.0] * 34),
        (("snapshots", "after", "candidate", "wheel_sha256"), "3" * 64),
        (("snapshots", "after", "candidate", "installed", "console_sha256"), "3" * 64),
        (("snapshots", "after", "candidate", "fixture", "cache_sha256"), "3" * 64),
        (("snapshots", "after", "candidate", "source", "commit"), "3" * 40),
    ],
)
def test_closed_vector_rejects_forgery_and_incomplete_measurement(path, value):
    report = receipt()
    target = report
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises((ValueError, TypeError)):
        HELPERS["validate"](report)


def test_duplicate_unknown_and_nonfinite_json_are_not_accepted():
    decode = HELPERS["CHECKS"]["decode"]
    for data in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b"\xff"):
        with pytest.raises(ValueError):
            decode(data)
    for path in ((), ("measurement",), ("snapshots", "before", "candidate", "fixture")):
        report = receipt()
        target = report
        for key in path:
            target = target[key]
        target["unknown"] = None
        with pytest.raises(ValueError):
            HELPERS["validate"](report)


def over_budget():
    report = receipt()
    row = report["measurement"]["measurements"]["cache"]
    row.update(
        warm_samples_ms=[2000.0] * 30, warm_median_ms=2000.0, warm_p95_ms=2000.0, passed=False
    )
    pair = report["measurement"]["comparison"]["paired_comparisons"]["cache"]
    pair.update(paired_wall_ratios=[200.0] * 30, median_paired_wall_ratio=200.0)
    report["output_checks"]["candidate"]["cache"]["wall_ms"][4:] = [2000.0] * 30
    report.update(measurement_exit=1, passed=False)
    return report


def test_truthful_linux_budget_overrun_can_be_archived_but_never_m5_accepted(tmp_path):
    report = over_budget()
    assert HELPERS["validate"](report)["outcome"] == "diagnostic_budget_exceeded"
    assert HELPERS["CHECKS"]["summarize"](report)["passed"] is False
    with pytest.raises(ValueError, match="all four absolute"):
        HELPERS["reference"](tmp_path, report)
    report["passed"] = True
    with pytest.raises(ValueError):
        HELPERS["validate"](report)


def current_vector():
    report = receipt()
    for point in ("before", "after"):
        candidate = report["snapshots"][point]["candidate"]
        candidate["source"] = HELPERS["source"](ROOT)
        candidate["source"]["commit"] = "a" * 40
        candidate["runtime_data_sha256"] = {
            name.removeprefix("src/"): value
            for name, value in candidate["source"]["source_sha256"].items()
            if name.startswith("src/yorunge/") and not name.endswith(".py")
        }
        candidate["installed"]["packages"] = HELPERS["JOBS"]["locked_runtime"](ROOT)
        candidate["installed"]["installed_source_sha256"] = HELPERS["CHECKS"]["python_hashes"](
            candidate["source"], package_prefix=True
        )
        candidate["fixture"]["profile_sha256"] = candidate["source"]["source_sha256"][
            "examples/profile.toml"
        ]
    profile_hash = report["snapshots"]["before"]["candidate"]["fixture"]["profile_sha256"]
    for point in ("before", "after"):
        report["snapshots"][point]["baseline"]["fixture"]["profile_sha256"] = profile_hash
        report["snapshots"][point]["baseline"]["source"]["source_sha256"][
            "examples/profile.toml"
        ] = profile_hash
    report["measurement"]["profile_sha256"] = profile_hash
    return report


def test_current_reference_uses_full_source_map_not_current_commit_or_wheel_hash():
    report = current_vector()
    # The retained wheel is historical; no current wheel/build is even required by this check.
    assert HELPERS["reference"](ROOT, report)["passed"] is True
    for point in ("before", "after"):
        report["snapshots"][point]["candidate"]["wheel_sha256"] = "9" * 64
    assert HELPERS["reference"](ROOT, report)["passed"] is True


@pytest.mark.parametrize("changed", ["runtime", "entry_point", "lock", "workflow", "test"])
def test_old_measurement_cannot_be_rebound_by_updating_only_its_commit(changed):
    report = current_vector()
    key = {
        "runtime": "src/yorunge/__init__.py",
        "entry_point": "pyproject.toml",
        "lock": "uv.lock",
        "workflow": ".github/workflows/checks.yml",
        "test": "tests/contracts/test_startup_evidence.py",
    }[changed]
    for point in ("before", "after"):
        snap = report["snapshots"][point]["candidate"]
        snap["source"]["source_sha256"][key] = "0" * 64
        snap["installed"]["installed_source_sha256"] = HELPERS["CHECKS"]["python_hashes"](
            snap["source"], package_prefix=True
        )
    with pytest.raises(ValueError, match="current source"):
        HELPERS["reference"](ROOT, report)


@pytest.mark.parametrize(
    "key,value",
    [("cpu", "AMD EPYC"), ("disk_type", "unknown"), ("machine", "x86_64"), ("python", "3.14.0")],
)
def test_reference_requires_declared_m5_runtime(key, value):
    report = current_vector()
    report["measurement"][key] = value
    if key in ("machine", "python"):
        for point in ("before", "after"):
            for side in ("candidate", "baseline"):
                report["snapshots"][point][side]["installed"][key] = value
    with pytest.raises(ValueError, match="M5 reference"):
        HELPERS["reference"](ROOT, report)


def test_readme_only_repack_preserves_source_equivalence_but_python_change_does_not(tmp_path):
    for name in ("src/yorunge", "scripts", "tests", "examples", ".github/workflows"):
        (tmp_path / name).mkdir(parents=True)
    for name in (
        "pyproject.toml",
        "uv.lock",
        "examples/profile.toml",
        ".github/workflows/checks.yml",
        "src/yorunge/__init__.py",
    ):
        (tmp_path / name).write_text("fixed")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.test",
            "commit",
            "--allow-empty",
            "-qm",
            "x",
        ],
        check=True,
        capture_output=True,
    )
    before = HELPERS["source"](tmp_path)["source_sha256"]
    (tmp_path / "README.md").write_text("metadata description changed")
    assert HELPERS["source"](tmp_path)["source_sha256"] == before
    (tmp_path / "src/yorunge/__init__.py").write_text("different")
    assert HELPERS["source"](tmp_path)["source_sha256"] != before


def test_original_v2_payload_cannot_be_relabelled_as_new_evidence():
    old = copy.deepcopy(receipt()["measurement"])
    old.update(schema_version=1, report_kind="startup_evidence_v1")
    with pytest.raises(ValueError):
        HELPERS["validate"](old)


def test_real_seeded_stdout_is_typed_and_has_independent_semantics(tmp_path):
    from yorunge import api

    seed = runpy.run_path(str(ROOT / "tests/fixtures/seed_capability_cache.py"))["seed"]
    profile, state = ROOT / "examples/profile.toml", tmp_path / "state"
    seed(state, profile)
    context = api.show_context(config=profile).model_dump(mode="json")
    cache = api.query_capabilities(task="llm.train", config=profile, state_dir=state).model_dump(
        mode="json"
    )
    for command, value in (
        (["yorunge", "context", "show"], context),
        (["yorunge", "capabilities", "--state-dir", str(state)], cache),
    ):
        HELPERS["validate_output"](command, json.dumps(value).encode())
    context["data"]["project_id"] = "wrong-but-valid-id"
    with pytest.raises(ValueError, match="fixed profile oracle"):
        HELPERS["validate_output"](["yorunge", "context", "show"], json.dumps(context).encode())
    for change in ("hit", "missing", "support", "tool", "inner_reason", "store", "evidence"):
        wrong = copy.deepcopy(cache)
        if change == "hit":
            wrong["data"]["records"][0]["hit"] = False
        elif change == "missing":
            wrong["data"]["records"].pop()
        elif change == "support":
            wrong["data"]["records"][0]["effective_support"] = "unknown"
        elif change == "inner_reason":
            wrong["data"]["records"][0]["record"]["reason_code"] = "wrong"
        elif change == "evidence":
            wrong["data"]["records"][0]["record"]["evidence"][0]["producer_id"] = "wrong"
        else:
            outer = wrong["data"]["records"][0]
            for key in (outer["key"], outer["record"]["key"]):
                if change == "tool":
                    key["scope"]["tool"]["id"] = "wrongtool"
                else:
                    key["scope"]["store_id"] = "11111111-1111-4111-8111-111111111111"
        with pytest.raises(ValueError):
            HELPERS["validate_output"](
                ["yorunge", "capabilities", "--state-dir", str(state)], json.dumps(wrong).encode()
            )


@pytest.mark.parametrize("content", [b"", b"{}", b"\xff", b"x" * (1024 * 1024 + 1)])
def test_exit_zero_alone_cannot_pass_stdout_oracle(content):
    with pytest.raises(ValueError):
        HELPERS["validate_output"](["yorunge", "context", "show"], content)


def test_audited_process_validates_after_timing_and_retains_all_processes(monkeypatch):
    benchmark = runpy.run_path(str(ROOT / "scripts/benchmark-startup.py"))
    measure = benchmark["measure"]
    observed = {}
    calls = []
    clock = iter([1.0, 1.025])
    monkeypatch.setitem(measure.__globals__, "AUDIT", observed)
    monkeypatch.setitem(
        measure.__globals__["audited_measure"].__globals__,
        "VALIDATE_OUTPUT",
        lambda command, content: calls.append(content),
    )
    monkeypatch.setattr(benchmark["time"], "perf_counter", lambda: next(clock))
    command = [sys.executable, "-c", "print('typed output')"]
    sample = measure(command)
    assert sample.wall_ms == pytest.approx(25.0)
    assert calls == [b"typed output\n"]
    row = observed["\0".join(command)]
    assert row["stdout_sha256"] == [hashlib.sha256(calls[0]).hexdigest()]
    assert row["wall_ms"] == [sample.wall_ms]


def test_fresh_producer_never_overwrites_report_or_reuses_a_workspace(tmp_path):
    producer = runpy.run_path(str(ROOT / "scripts/check-startup-evidence.py"))
    output = tmp_path / "previous.json"
    output.write_text("previous")
    with pytest.raises(ValueError, match="new output"):
        producer["check"](
            ROOT, ROOT, tmp_path / "fresh", output, Path("unused"), cpu=None, disk="unknown"
        )
    assert output.read_text() == "previous"
    assert not (tmp_path / "fresh").exists()
    workspace = tmp_path / "existing"
    workspace.mkdir()
    with pytest.raises(FileExistsError):
        producer["check"](
            ROOT, ROOT, workspace, tmp_path / "new.json", Path("unused"), cpu=None, disk="unknown"
        )


def test_non_python_runtime_inputs_require_explicit_scope(tmp_path):
    (tmp_path / "src/yorunge").mkdir(parents=True)
    (tmp_path / "src/yorunge/runtime-data.json").write_text("{}")
    with pytest.raises(ValueError, match="explicit non-Python"):
        HELPERS["source"](tmp_path)


def test_baseline_version_oracle_uses_its_own_installed_release():
    HELPERS["validate_output"](
        ["/baseline/env/bin/yorunge", "--version"], b"yorunge 0.0.9\n", version="0.0.9"
    )
    with pytest.raises(ValueError, match="version output mismatch"):
        HELPERS["validate_output"](
            ["/baseline/env/bin/yorunge", "--version"], b"yorunge 0.1.0.dev0\n", version="0.0.9"
        )


def test_common_candidate_profile_allows_historical_baseline_comment_difference():
    report = receipt()
    for point in ("before", "after"):
        report["snapshots"][point]["baseline"]["source"]["source_sha256"][
            "examples/profile.toml"
        ] = "9" * 64
    assert HELPERS["validate"](report)["passed"] is True


def test_workflow_changes_and_additions_are_included_in_current_source_scope(tmp_path):
    for name in ("src/yorunge", "scripts", "tests", "examples", ".github/workflows"):
        (tmp_path / name).mkdir(parents=True)
    for name in (
        "pyproject.toml",
        "uv.lock",
        "examples/profile.toml",
        ".github/workflows/checks.yml",
        "src/yorunge/__init__.py",
    ):
        (tmp_path / name).write_text("fixed")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.test",
            "commit",
            "--allow-empty",
            "-qm",
            "x",
        ],
        check=True,
        capture_output=True,
    )
    before = HELPERS["source"](tmp_path)["source_sha256"]
    policy = tmp_path / ".github/workflows/pr-policy.yml"
    policy.write_text("new workflow")
    after = HELPERS["source"](tmp_path)["source_sha256"]
    assert after != before
    assert (
        after[".github/workflows/pr-policy.yml"] == hashlib.sha256(policy.read_bytes()).hexdigest()
    )
    policy.write_text("changed workflow")
    assert HELPERS["source"](tmp_path)["source_sha256"] != after


@pytest.mark.parametrize("kind", ["stdout", "stderr", "exit", "oversize"])
def test_selector_capture_rejects_output_and_process_failures(kind):
    capture = runpy.run_path(str(ROOT / "scripts/benchmark-startup.py"))["bounded_capture"]
    scripts = {
        "stdout": "print('ok')",
        "stderr": "import sys; print('bad', file=sys.stderr)",
        "exit": "raise SystemExit(7)",
        "oversize": "print('x' * (1048576 + 1))",
    }
    if kind == "stdout":
        assert capture([sys.executable, "-c", scripts[kind]]) == b"ok\n"
    elif kind == "exit":
        with pytest.raises(subprocess.CalledProcessError) as error:
            capture([sys.executable, "-c", scripts[kind]])
        assert error.value.returncode == 7
    else:
        with pytest.raises(ValueError):
            capture([sys.executable, "-c", scripts[kind]])
