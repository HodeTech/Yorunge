"""Full startup acceptance cannot silently omit the persistent cache path."""

import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/benchmark-startup.py"


def test_missing_cache_fixture_is_rejected_before_any_measurement(tmp_path):
    report = tmp_path / "startup.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--command",
            str(tmp_path / "not-run"),
            "--output",
            str(report),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert "--cache-state" in result.stderr
    assert not report.exists()


def test_full_benchmark_measures_cache_and_reports_its_real_dataset(tmp_path, monkeypatch):
    seed = runpy.run_path(str(ROOT / "tests/fixtures/seed_capability_cache.py"))["seed"]
    state, profile = tmp_path / "state", ROOT / "examples/profile.toml"
    seed(state, profile)
    checks = runpy.run_path(str(SCRIPT))
    main = checks["main"]
    calls = []

    def measure(command, *, cache_hit=False):
        calls.append((command, cache_hit))
        assert cache_hit == ("--cached" in command)
        # Control-flow fixture; this is not a performance measurement.
        return checks["Sample"](10.0, 0.0, 0.0)

    monkeypatch.setitem(main.__globals__, "measure", measure)
    report = tmp_path / "startup.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--command",
            str(tmp_path / "not-run"),
            "--profile",
            str(profile),
            "--cache-state",
            str(state),
            "--output",
            str(report),
        ],
    )
    assert main() == 0
    value = json.loads(report.read_text())
    assert value["cache_dataset"]["records"] == 1024
    assert set(value["measurements"]) == {"help", "version", "context", "cache"}
    assert value["measurements"]["cache"]["fresh_cache_hit_verified"]
    assert len(value["measurements"]["cache"]["warm_samples_ms"]) == 30
    assert len(value["measurements"]["cache"]["warm_child_user_cpu_ms"]) == 30
    assert len(value["measurements"]["cache"]["warm_child_system_cpu_ms"]) == 30
    assert sum(cache_hit for _, cache_hit in calls) == 34


def test_child_cpu_diagnostics_preserve_wall_measurement_and_allow_unavailable_metadata(
    monkeypatch,
):
    helpers = runpy.run_path(str(SCRIPT))
    sample = helpers["measure"]([sys.executable, "-c", "sum(i*i for i in range(250000))"])
    assert sample.wall_ms > 0
    if helpers["resource_module"] is not None:
        assert sample.user_ms >= 0
        assert sample.system_ms >= 0
        assert sample.user_ms + sample.system_ms > 0
    monkeypatch.setitem(helpers["measure"].__globals__, "resource_module", None)
    unavailable = helpers["measure"]([sys.executable, "--version"])
    assert unavailable.wall_ms > 0
    assert unavailable.user_ms is None
    assert unavailable.system_ms is None


# The following tiny databases and fixed samples exercise orchestration, not performance.
def synthetic_dataset(root, payload="x", count=1024):
    import sqlite3
    from contextlib import closing

    root.mkdir()
    with closing(sqlite3.connect(root / "state.sqlite3")) as connection:
        connection.execute("CREATE TABLE capability_cache(payload TEXT)")
        connection.executemany("INSERT INTO capability_cache VALUES(?)", [(payload,)] * count)
        connection.commit()


@pytest.mark.parametrize("kind", ["file", "symlink", "dangling_symlink", "missing_parent"])
def test_benchmark_preserves_existing_reports_before_accessing_inputs(
    tmp_path, monkeypatch, capsys, kind
):
    checks = runpy.run_path(str(SCRIPT))
    report, target = tmp_path / "report.json", tmp_path / "target.json"
    if kind == "file":
        report.write_text("original")
    elif kind in ("symlink", "dangling_symlink"):
        if kind == "symlink":
            target.write_text("original")
        report.symlink_to(target)
    else:
        report = tmp_path / "absent" / "report.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [str(SCRIPT), "--command", "unused", "--cache-state", "absent", "--output", str(report)],
    )
    with pytest.raises(SystemExit) as result:
        checks["main"]()
    assert result.value.code == 2
    assert "output must be a new file" in capsys.readouterr().err
    if kind == "file":
        assert report.read_text() == "original"
    elif kind in ("symlink", "dangling_symlink"):
        assert report.is_symlink()
        if kind == "symlink":
            assert target.read_text() == "original"
        else:
            assert not target.exists()
    else:
        assert not report.exists()


def test_benchmark_preserves_report_created_during_measurement(tmp_path, monkeypatch, capsys):
    synthetic_dataset(tmp_path / "state")
    profile = tmp_path / "profile.toml"
    profile.write_text("same")
    report = tmp_path / "report.json"
    checks = runpy.run_path(str(SCRIPT))

    def measure(command, *, cache_hit=False):
        if not report.exists():
            report.write_text("concurrent report")
        return checks["Sample"](10.0, 0.0, 0.0)

    monkeypatch.setitem(checks["main"].__globals__, "measure", measure)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--command",
            "unused",
            "--profile",
            str(profile),
            "--cache-state",
            str(tmp_path / "state"),
            "--output",
            str(report),
        ],
    )
    with pytest.raises(SystemExit) as result:
        checks["main"]()
    assert result.value.code == 2
    assert "output must be a new file" in capsys.readouterr().err
    assert report.read_text() == "concurrent report"


def test_comparison_alternates_every_pair_and_keeps_head_absolute_gate(tmp_path, monkeypatch):
    synthetic_dataset(tmp_path / "head")
    synthetic_dataset(tmp_path / "base")
    profile = tmp_path / "profile.toml"
    profile.write_text("same")
    checks = runpy.run_path(str(SCRIPT))
    calls = []

    def measure(command, *, cache_hit=False):
        side = Path(command[0]).name
        calls.append(side)
        return checks["Sample"](300.0 if side == "base" else 201.0, 1.0, 0.0)

    monkeypatch.setitem(checks["main"].__globals__, "measure", measure)
    report = tmp_path / "report.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--command",
            str(tmp_path / "candidate"),
            "--profile",
            str(profile),
            "--cache-state",
            str(tmp_path / "head"),
            "--baseline-command",
            str(tmp_path / "base"),
            "--baseline-profile",
            str(profile),
            "--baseline-cache-state",
            str(tmp_path / "base"),
            "--output",
            str(report),
        ],
    )
    assert checks["main"]() == 1
    value = json.loads(report.read_text())
    assert value["schema_version"] == 2
    assert calls[:8] == ["base", "candidate", "candidate", "base"] * 2
    cache = value["comparison"]["paired_comparisons"]["cache"]
    assert cache["candidate_faster_pairs"] == 30
    assert cache["median_paired_wall_ratio"] == 0.67
    assert len(value["measurements"]["cache"]["warm_samples_ms"]) == 30
    assert value["measurements"]["cache"]["passed"] is False
    assert len(calls) == 4 * 34 * 2


def test_slow_baseline_is_diagnostic_when_candidate_meets_absolute_targets(tmp_path, monkeypatch):
    checks = runpy.run_path(str(SCRIPT))
    samples = checks["Sample"]
    seen = []

    def measure(command, *, cache_hit=False):
        seen.append(command[0])
        return samples(300.0 if command[0] == "base" else 100.0, None, None)

    monkeypatch.setitem(checks["paired_samples"].__globals__, "measure", measure)
    first, current, old_first, previous = checks["paired_samples"](
        ["head"], ["base"], 30, cached=True
    )
    assert checks["summary"](first, current, 200, cached=True)["passed"] is True
    assert checks["summary"](old_first, previous, 200, cached=True)["passed"] is False
    assert seen[:4] == ["base", "head", "head", "base"]
    # Full precision avoids accepting a value just above 200 after rounding it to 200.000.
    tiny_overrun = [samples(200.0001, None, None)] * 30
    assert checks["summary"](first, tiny_overrun, 200, cached=True)["passed"] is False
    assert checks["summary"](first, tiny_overrun, 200, cached=True)["warm_p95_ms"] == 200.0001
    invalid = [samples(float("nan"), None, None)]
    with pytest.raises(ValueError, match="finite"):
        checks["summary"](first, invalid, 200, cached=True)


def test_incomplete_baseline_options_fail_before_database_or_process_access(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--command",
            "unused",
            "--cache-state",
            "absent",
            "--baseline-command",
            "unused",
            "--output",
            str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert "all three --baseline" in result.stderr
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("difference", ["data", "profile", "same_state"])
def test_comparison_rejects_different_data_before_running_commands(
    tmp_path, monkeypatch, capsys, difference
):
    synthetic_dataset(tmp_path / "head")
    synthetic_dataset(tmp_path / "base", payload="longer" if difference == "data" else "x")
    profile = tmp_path / "profile.toml"
    profile.write_text("same")
    other_profile = tmp_path / "other.toml"
    other_profile.write_text("else")
    baseline_profile = other_profile if difference == "profile" else profile
    baseline_state = tmp_path / ("head" if difference == "same_state" else "base")
    checks = runpy.run_path(str(SCRIPT))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--command",
            "unused",
            "--profile",
            str(profile),
            "--cache-state",
            str(tmp_path / "head"),
            "--baseline-command",
            "unused",
            "--baseline-profile",
            str(baseline_profile),
            "--baseline-cache-state",
            str(baseline_state),
            "--output",
            str(tmp_path / "out"),
        ],
    )
    with pytest.raises(SystemExit) as result:
        checks["main"]()
    assert result.value.code == 2
    expected = "separate synthetic" if difference == "same_state" else "equivalent datasets"
    assert expected in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_small_dataset_cannot_satisfy_full_startup_acceptance(tmp_path):
    synthetic_dataset(tmp_path / "small", count=1023)
    checks = runpy.run_path(str(SCRIPT))
    with pytest.raises(ValueError, match="1024"):
        checks["dataset"](tmp_path / "small")
