"""Handwritten receipts exercise archival verification without running a benchmark."""

import copy
import gzip
import json
import runpy
from pathlib import Path

import pytest

CHECKS = runpy.run_path(str(Path(__file__).parents[2] / "scripts/research_evidence.py"))
HASHES = {
    16: "341aacac661ccb210720bedaa9ead5d668fe5ea41a73532fc147c71e34040df1",
    256: "486cc817b95d853d3c357ff283b204c0144bd255e73fe2deb1389493b257e3c0",
    1024: "2c06ade942ee3f17a048dd1064b2fab046a4bb95386d8bb41b68dc6711ac2af3",
}


def receipt(unit="KiB"):
    """A small independently authored Linux/macOS record, never a producer result."""
    factor = 1024 if unit == "KiB" else 1
    runtime = {
        "prefix": "/runtime",
        "pid": 41,
        "modules": {"yorunge": "/runtime/lib/yorunge/__init__.py"},
        "installed_source_sha256": {"__init__.py": "b" * 64},
        "installed_source_matches": True,
        "metadata": "/runtime/lib",
        "packages": {"yorunge": "0.1.0.dev0", "httpx": "0.28.1"},
        "python": "3.14.0",
        "python_executable": "/runtime/bin/python",
        "isolated": True,
        "sqlite": "3.50.4",
        "os": "Linux-6.1" if unit == "KiB" else "macOS-15.0",
        "machine": "arm64",
    }
    source = {
        "commit": "a" * 40,
        "source_sha256": {
            "src/yorunge/__init__.py": "b" * 64,
            "scripts/benchmark-stream.py": "c" * 64,
        },
    }
    runs = []
    for index, (mib, digest) in enumerate(HASHES.items()):
        size = mib * 1024 * 1024
        server = {
            "requests": [
                {"size_bytes": 32768, "sent_bytes": 32768, "completed": True},
                {"size_bytes": size, "sent_bytes": size, "completed": True},
            ],
            "request_count": 2,
            "connection_count": 1,
            "peak_active_requests": 1,
            "pid": 51 + index,
        }
        runs.append(
            {
                "size_bytes": size,
                "size_mib": mib,
                "expected_bytes": size,
                "expected_sha256": digest,
                "received_bytes": size,
                "received_sha256": digest,
                "stream_count": 1,
                "warmup_requests": 1,
                "measurement_requests": 1,
                "baseline_rss_native": 32 * 1024 * 1024 // factor,
                "peak_rss_native": 34 * 1024 * 1024 // factor,
                "rss_native_unit": unit,
                "baseline_rss_bytes": 32 * 1024 * 1024,
                "peak_rss_bytes": 34 * 1024 * 1024,
                "extra_rss_bytes": 2 * 1024 * 1024,
                "elapsed_seconds": 0.5 + index,
                "max_chunk_bytes": 32768,
                "chunk_count": size // 32768,
                "runtime": {**copy.deepcopy(runtime), "pid": 41 + index},
                "server": server,
                "request_count": 2,
                "connection_count": 1,
                "peak_active_requests": 1,
                "passed": True,
            }
        )
    return {
        "schema_version": 1,
        "report_kind": "raw_stream_budget_v1",
        "source_commit": "a" * 40,
        "environment": {
            key: runtime[key]
            for key in (
                "os",
                "machine",
                "python",
                "python_executable",
                "sqlite",
                "packages",
            )
        }
        | {"cpu": "synthetic test CPU", "disk": "synthetic test disk"},
        "provenance": {
            "source_before": source,
            "source_after": copy.deepcopy(source),
            "source_unchanged_during_measurement": True,
            "installed_source_matches": True,
        },
        "method": {
            "rss_method": "resource.getrusage(RUSAGE_SELF).ru_maxrss",
            "rss_baseline": "fresh high-water after fixed TLS warmup, not instantaneous RSS",
            "rss_native_unit": unit,
            "server_process_excluded": True,
            "consumer": "incremental_sha256_and_count",
            "server_generation": "repeating_0_to_255_bounded_32768_bytes",
            "client_process_per_size": True,
            "streams_per_client": 1,
            "consumer_queue_chunks": 0,
            "backpressure": "one awaited next chunk",
            "phase_timeout_seconds": 5,
            "pool_timeout_seconds": 1,
            "limit": "synthetic raw byte transport",
        },
        "limits": {
            "extra_rss_bytes": 67108864,
            "chunk_bytes": 32768,
            "connections": 2,
            "total_deadline_seconds": 120.0,
        },
        "runs": runs,
        "size_growth_diagnostic": {
            "size_bytes": [item["size_bytes"] for item in runs],
            "extra_rss_bytes": [2097152] * 3,
        },
        "passed": True,
    }


def archive(tmp_path, report):
    root = tmp_path / "repository"
    (root / "dist").mkdir(parents=True)
    (root / "docs/research").mkdir(parents=True)
    source = root / "dist/stream-budget.json"
    original = (json.dumps(report, indent=4) + "\n").encode()
    source.write_bytes(original)
    CHECKS["archive_report"](root, source, None)
    assert CHECKS["verify"](root) == 1
    packed = root / "docs/research/raw/stream-budget.json.gz"
    assert gzip.decompress(packed.read_bytes()) == original == source.read_bytes()
    return json.loads((root / "docs/research/evidence-manifest.json").read_bytes())["entries"][0]


@pytest.mark.parametrize("unit", ["KiB", "bytes"])
def test_stream_summary_exposes_all_sizes_native_rss_method_and_source(tmp_path, unit):
    summary = archive(tmp_path, receipt(unit))["summary"]
    assert summary["source_commit"] == "a" * 40
    assert summary["kind"] == "raw_stream_budget_v1"
    assert summary["rss_method"] == "resource.getrusage(RUSAGE_SELF).ru_maxrss"
    assert "not instantaneous" in summary["rss_baseline"]
    assert summary["rss_native_unit"] == unit
    assert summary["passed"] is True
    assert list(summary["measurements"]) == ["16MiB", "256MiB", "1024MiB"]
    assert summary["measurements"]["1024MiB"]["received_bytes"] == 1073741824


@pytest.mark.parametrize("failure", ["rss", "hash", "bytes", "requests", "isolation", "pid"])
def test_truthful_failed_streams_are_preserved_and_false_green_is_rejected(tmp_path, failure):
    report = receipt()
    run = report["runs"][-1]
    if failure == "rss":
        run["extra_rss_bytes"] = 67109888
        run["peak_rss_bytes"] = run["baseline_rss_bytes"] + run["extra_rss_bytes"]
        run["peak_rss_native"] = run["peak_rss_bytes"] // 1024
        report["size_growth_diagnostic"]["extra_rss_bytes"][-1] = run["extra_rss_bytes"]
    elif failure == "hash":
        run["received_sha256"] = "f" * 64
    elif failure == "bytes":
        run["received_bytes"] -= 1
    elif failure == "requests":
        run["server"]["requests"][0]["sent_bytes"] -= 1
        run["server"]["requests"][0]["completed"] = False
    elif failure == "isolation":
        run["runtime"]["isolated"] = False
    else:
        run["server"]["pid"] = run["runtime"]["pid"]
    run["passed"] = report["passed"] = False
    summary = archive(tmp_path, report)["summary"]
    assert summary["passed"] is False
    assert summary["measurements"]["1024MiB"]["passed"] is False
    report["passed"] = True
    with pytest.raises(ValueError, match="flag"):
        CHECKS["summarize"](report)
    report["passed"] = False
    run["passed"] = True
    with pytest.raises(ValueError, match="flag"):
        CHECKS["summarize"](report)


@pytest.mark.parametrize("drift", ["source", "transient_source", "installed"])
def test_drift_is_failed_evidence_even_when_final_snapshots_match(tmp_path, drift):
    report = receipt()
    if drift == "source":
        report["provenance"]["source_after"]["source_sha256"]["scripts/benchmark-stream.py"] = (
            "d" * 64
        )
    if drift in {"source", "transient_source"}:
        report["provenance"]["source_unchanged_during_measurement"] = False
    else:
        runtime = report["runs"][-1]["runtime"]
        runtime["installed_source_sha256"]["__init__.py"] = "d" * 64
        runtime["installed_source_matches"] = False
        report["runs"][-1]["passed"] = False
        report["provenance"]["installed_source_matches"] = False
    report["passed"] = False
    assert archive(tmp_path, report)["summary"]["passed"] is False
    if drift != "transient_source":
        key = (
            "source_unchanged_during_measurement"
            if drift == "source"
            else "installed_source_matches"
        )
        report["provenance"][key] = True
        with pytest.raises(ValueError, match="flag"):
            CHECKS["summarize"](report)


@pytest.mark.parametrize(
    "location,key,value",
    [
        ("top", "report_kind", "raw_stream_budget_v2"),
        ("top", "schema_version", True),
        ("top", "schema_version", 2),
        ("top", "source_commit", "d" * 40),
        ("top", "passed", 1),
        ("run", "size_bytes", True),
        ("run", "received_bytes", True),
        ("run", "chunk_count", True),
        ("run", "baseline_rss_bytes", True),
        ("run", "extra_rss_bytes", -1),
        ("run", "peak_rss_bytes", 1),
        ("run", "baseline_rss_native", -1),
        ("run", "baseline_rss_native", True),
        ("run", "rss_native_unit", "MB"),
        ("run", "rss_native_unit", "bytes"),
        ("run", "elapsed_seconds", float("nan")),
        ("run", "elapsed_seconds", float("inf")),
        ("run", "elapsed_seconds", True),
        ("run", "elapsed_seconds", 0),
        ("run", "expected_sha256", "f" * 64),
        ("run", "received_sha256", "not-a-digest"),
        ("run", "request_count", 1),
        ("run", "chunk_count", 1),
        ("runtime", "isolated", 1),
        ("runtime", "installed_source_matches", False),
        ("runtime", "pid", True),
        ("runtime", "prefix", "relative/runtime"),
        ("runtime", "python_executable", "/runtime/../elsewhere/python"),
        ("limit", "extra_rss_bytes", 67108865),
        ("limit", "connections", True),
        ("limit", "chunk_bytes", 65536),
        ("limit", "total_deadline_seconds", 121),
        ("method", "server_process_excluded", False),
        ("method", "streams_per_client", True),
        ("method", "rss_method", "process tree RSS"),
        ("method", "consumer_queue_chunks", 1),
    ],
)
def test_stream_rejects_wrong_types_units_or_dishonest_measurements(location, key, value):
    report = receipt()
    targets = {
        "top": report,
        "run": report["runs"][0],
        "runtime": report["runs"][0]["runtime"],
        "limit": report["limits"],
        "method": report["method"],
    }
    targets[location][key] = value
    with pytest.raises(ValueError):
        CHECKS["summarize"](report)


@pytest.mark.parametrize(
    "part",
    [
        "report",
        "run",
        "runtime",
        "server",
        "request",
        "provenance",
        "source",
        "method",
        "limits",
        "growth",
        "environment",
    ],
)
@pytest.mark.parametrize("damage", ["extra", "missing"])
def test_stream_schema_is_closed_at_each_record_boundary(part, damage):
    report = receipt()
    run = report["runs"][0]
    target = {
        "report": report,
        "run": run,
        "runtime": run["runtime"],
        "server": run["server"],
        "request": run["server"]["requests"][0],
        "provenance": report["provenance"],
        "source": report["provenance"]["source_before"],
        "method": report["method"],
        "limits": report["limits"],
        "growth": report["size_growth_diagnostic"],
        "environment": report["environment"],
    }[part]
    if damage == "extra":
        target["unchecked"] = 1
    else:
        del target[next(iter(target))]
    with pytest.raises(ValueError):
        CHECKS["summarize"](report)


@pytest.mark.parametrize(
    "damage",
    [
        "missing",
        "duplicate",
        "reordered",
        "growth",
        "bool_growth",
        "server_bool",
        "native_conversion",
        "package_tools",
    ],
)
def test_stream_acceptance_requires_all_distinct_cases_and_consistent_telemetry(damage):
    report = receipt()
    if damage == "missing":
        report["runs"].pop()
    elif damage == "duplicate":
        report["runs"][1] = copy.deepcopy(report["runs"][0])
    elif damage == "reordered":
        report["runs"].reverse()
    elif damage == "growth":
        report["size_growth_diagnostic"]["extra_rss_bytes"][0] = 1
    elif damage == "bool_growth":
        report["size_growth_diagnostic"]["extra_rss_bytes"][0] = True
    elif damage == "server_bool":
        report["runs"][0]["server"]["requests"][0]["completed"] = 1
    elif damage == "native_conversion":
        report["runs"][0]["baseline_rss_native"] += 1
    else:
        report["runs"][0]["runtime"]["packages"]["pytest"] = "9.0"
    with pytest.raises(ValueError):
        CHECKS["summarize"](report)


def test_future_typed_kind_cannot_fall_back_to_legacy_shape_detection():
    with pytest.raises(ValueError, match="kind or schema"):
        CHECKS["summarize"]({"schema_version": 1, "report_kind": "unknown", "results": []})


def test_json_rejects_duplicate_and_nonfinite_stream_fields():
    with pytest.raises(ValueError, match="duplicate"):
        CHECKS["decode"](b'{"report_kind":"raw_stream_budget_v1","passed":false,"passed":true}')
    with pytest.raises(ValueError, match="non-finite"):
        CHECKS["decode"](b'{"elapsed_seconds":1e999}')


@pytest.mark.parametrize("alias", ["tmp", "var"])
@pytest.mark.parametrize("private_prefix", [True, False])
def test_macos_aliases_are_checked_lexically_on_any_verifier_host(
    monkeypatch,
    alias,
    private_prefix,
):
    report = receipt("bytes")
    prefix = f"/{'private/' if private_prefix else ''}{alias}/absent-runtime"
    executable = f"/{'' if private_prefix else 'private/'}{alias}/absent-runtime/bin/python"
    for run in report["runs"]:
        run["runtime"].update(
            prefix=prefix,
            python_executable=executable,
            metadata=prefix + "/lib",
            modules={"yorunge": prefix + "/lib/yorunge/__init__.py"},
        )
    report["environment"]["python_executable"] = executable

    def forbidden(*args, **kwargs):
        raise AssertionError("historical runtime paths must not touch the verifier filesystem")

    monkeypatch.setattr(Path, "resolve", forbidden)
    monkeypatch.setattr(Path, "exists", forbidden)
    assert CHECKS["summarize"](report)["passed"] is True
    report["environment"]["os"] = "Linux-6.1"
    report["method"]["rss_native_unit"] = "KiB"
    for run in report["runs"]:
        run["runtime"]["os"] = "Linux-6.1"
    with pytest.raises(ValueError, match="escaped"):
        CHECKS["summarize"](report)
