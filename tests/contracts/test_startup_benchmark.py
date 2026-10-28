"""Full startup acceptance cannot silently omit the persistent cache path."""

import json
import runpy
import subprocess
import sys
from pathlib import Path

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
        return 10.0  # Control-flow fixture; this is not a performance measurement.

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
    assert sum(cache_hit for _, cache_hit in calls) == 34
