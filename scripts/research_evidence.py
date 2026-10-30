"""Archive public measurement reports losslessly and verify their reviewable index."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import json
import math
import os
import re
import runpy
import statistics
import sys
import tempfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

MAX_REPORT_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_BYTES = 4 * 1024 * 1024
MAX_ENTRIES = 256
MAX_REJECTED_STARTUP_BYTES = 2 * 1024 * 1024
NAME = re.compile(r"[a-z0-9][a-z0-9-]*\.json")
COMMIT = re.compile(r"[0-9a-f]{40}")
CI_RUN_URL = re.compile(
    r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/runs/[1-9]\d*", re.ASCII
)
SHA256 = re.compile(r"[0-9a-f]{64}")
STREAM_HASHES = {
    16: "341aacac661ccb210720bedaa9ead5d668fe5ea41a73532fc147c71e34040df1",
    256: "486cc817b95d853d3c357ff283b204c0144bd255e73fe2deb1389493b257e3c0",
    1024: "2c06ade942ee3f17a048dd1064b2fab046a4bb95386d8bb41b68dc6711ac2af3",
}
INSTALL_CHECKS = (
    "origin_verified",
    "smoke",
    "ndjson_smoke",
    "http_smoke",
    "stream_smoke",
    "cache_smoke",
    "execution_smoke",
    "jobs_smoke",
)
JOBS_REFERENCE = {
    "cpu": "Apple M5 Max",
    "disk_type": "internal SSD/APFS",
    "machine": "arm64",
    "platform_prefix": "macOS-27.0.1-",
    "python_prefix": "3.11.",
}
JOBS_REFERENCE_ROWS = {
    "operations": (1, 1024),
    "operation_attempts": (1, 16384),
    "operation_events": (3, 262144),
    "operation_outcomes": (0, 1024),
    "execution_plans": (1, 1024),
    "execution_approvals": (1, 1024),
    "capability_cache": (1, 1024),
}
MANIFEST = "evidence-manifest.json"
INDEX = "evidence.md"
FINITE_MEASUREMENT = "expected a finite measurement"
STREAM_PEAK_SOURCE = "resource.getrusage(RUSAGE_SELF).ru_maxrss"
PRODUCT_SOURCE_PREFIX = "src/yorunge/"


def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate JSON key")
    return result


def reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON value: {value}")


def finite_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("non-finite JSON number")
    return result


def decode(content: bytes) -> dict[str, Any]:
    value = json.loads(
        content.decode("utf-8"),
        object_pairs_hook=object_pairs,
        parse_constant=reject_constant,
        parse_float=finite_float,
    )
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return dict(value)


def encode(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def read_bounded(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("expected a regular evidence file")
    with path.open("rb") as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError("evidence size limit exceeded")
    return content


def research_directory(root: Path) -> Path:
    path = root / "docs/research"
    for candidate in (root / "docs", path, path / "raw"):
        if candidate.is_symlink():
            raise ValueError("evidence directory must not be a symlink")
    return path


def number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(FINITE_MEASUREMENT)
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError(FINITE_MEASUREMENT) from error
    if not math.isfinite(result):
        raise ValueError(FINITE_MEASUREMENT)
    return result


def closed(value: object, fields: str, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise ValueError(f"invalid {label} fields")
    return dict(value)


def integer(value: object, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or type(value) is not int or value < minimum:
        raise ValueError("expected an integer measurement in range")
    return value


def text_value(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("expected nonempty evidence text")
    return value


def pattern_value(value: object, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValueError("invalid evidence digest or identifier")
    return value


def flag(value: object, expected: bool) -> None:
    if type(value) is not bool or value != expected:
        raise ValueError("reported flag does not match evidence")


def hash_map(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise ValueError("expected nonempty source hashes")
    result = {}
    for name, digest in value.items():
        if (
            not isinstance(name, str)
            or not name
            or name.startswith("/")
            or "\\" in name
            or any(part in {"", ".", ".."} for part in name.split("/"))
        ):
            raise ValueError("invalid source hash path")
        result[name] = pattern_value(digest, SHA256)
    return result


def source_snapshot(value: object) -> dict[str, Any]:
    source = closed(value, "commit source_sha256", "source snapshot")
    pattern_value(source["commit"], COMMIT)
    hashes = hash_map(source["source_sha256"])
    if not any(name.startswith(PRODUCT_SOURCE_PREFIX) and name.endswith(".py") for name in hashes):
        raise ValueError("source snapshot has no product Python files")
    return source


def python_hashes(source: dict[str, Any], *, package_prefix: bool = False) -> dict[str, str]:
    return {
        name.removeprefix("src/" if package_prefix else PRODUCT_SOURCE_PREFIX): digest
        for name, digest in source["source_sha256"].items()
        if name.startswith(PRODUCT_SOURCE_PREFIX) and name.endswith(".py")
    }


def package_versions(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise ValueError("expected installed package versions")
    for name, version in value.items():
        text_value(name)
        text_value(version)
        if name.lower().replace("_", "-") in {"pytest", "ruff", "mypy", "types-pyyaml"}:
            raise ValueError("measurement runtime contains development tools")
    return dict(value)


def runtime_path(value: object) -> PurePosixPath:
    path = PurePosixPath(text_value(value))
    if not path.is_absolute() or any(part in {".", ".."} for part in path.parts):
        raise ValueError("runtime path must be absolute without traversal")
    return path


def canonical_runtime_path(value: object, os_name: str) -> PurePosixPath:
    path = runtime_path(value)
    if os_name.startswith(("Darwin", "macOS")):
        # macOS resolves these system aliases in sys.prefix, but not sys.executable.
        for alias in ("tmp", "var"):
            base = PurePosixPath("/") / alias
            if path.is_relative_to(base):
                path = PurePosixPath("/private") / alias / path.relative_to(base)
                break
    return path


def runtime_origin(value: object, prefix: PurePosixPath, os_name: str) -> bool:
    return canonical_runtime_path(value, os_name).is_relative_to(
        canonical_runtime_path(str(prefix), os_name)
    )


def stream_runtime(value: object, expected: dict[str, str]) -> dict[str, Any]:
    runtime = closed(
        value,
        "prefix pid modules installed_source_sha256 installed_source_matches metadata packages "
        "python python_executable isolated sqlite os machine",
        "stream runtime",
    )
    integer(runtime["pid"], minimum=1)
    prefix = runtime_path(runtime["prefix"])
    origins = runtime["modules"]
    if not isinstance(origins, dict) or "yorunge" not in origins:
        raise ValueError("missing installed product module origins")
    for name, origin in origins.items():
        if not isinstance(name, str) or not (name == "yorunge" or name.startswith("yorunge.")):
            raise ValueError("invalid product module origin name")
        if not runtime_origin(origin, prefix, text_value(runtime["os"])):
            raise ValueError("product module escaped its runtime prefix")
    for name in ("metadata", "python_executable"):
        if not runtime_origin(runtime[name], prefix, text_value(runtime["os"])):
            raise ValueError("runtime metadata or interpreter escaped its prefix")
    for name in ("python", "sqlite", "os", "machine"):
        text_value(runtime[name])
    package_versions(runtime["packages"])
    actual = hash_map(runtime["installed_source_sha256"])
    flag(runtime["installed_source_matches"], actual == expected)
    if type(runtime["isolated"]) is not bool:
        raise ValueError("runtime isolation flag must be boolean")
    return runtime


def stream_rss(run: dict[str, Any], native_unit: str) -> None:
    baseline = integer(run["baseline_rss_bytes"], minimum=1)
    peak = integer(run["peak_rss_bytes"], minimum=baseline)
    if integer(run["extra_rss_bytes"]) != peak - baseline:
        raise ValueError("extra RSS does not match baseline and peak")
    if run["rss_native_unit"] != native_unit or native_unit != stream_native_unit(
        run["runtime"]["os"]
    ):
        raise ValueError("native RSS unit does not match the runtime OS")
    factor = 1024 if native_unit == "KiB" else 1
    for name in ("baseline", "peak"):
        native = number(run[name + "_rss_native"])
        if native <= 0 or native * factor != run[name + "_rss_bytes"]:
            raise ValueError("native RSS does not match byte measurement")


def stream_server(run: dict[str, Any], size: int) -> bool:
    server = closed(
        run["server"],
        "requests request_count connection_count peak_active_requests pid",
        "stream server",
    )
    integer(server["pid"], minimum=1)
    for name in ("request_count", "connection_count", "peak_active_requests"):
        integer(server[name])
        integer(run[name])
        if run[name] != server[name]:
            raise ValueError("server telemetry differs from copied counters")
    requests = server["requests"]
    if not isinstance(requests, list) or len(requests) > 16:
        raise ValueError("invalid bounded server request telemetry")
    for item in requests:
        request = closed(item, "size_bytes sent_bytes completed", "stream request")
        integer(request["size_bytes"], minimum=1)
        integer(request["sent_bytes"])
        if type(request["completed"]) is not bool:
            raise ValueError("request completion must be boolean")
    if len(requests) != server["request_count"]:
        raise ValueError("server request count does not match telemetry")
    expected = [
        {"size_bytes": 32768, "sent_bytes": 32768, "completed": True},
        {"size_bytes": size, "sent_bytes": size, "completed": True},
    ]
    return (
        requests == expected
        and 1 <= server["connection_count"] <= 2
        and 1 <= server["peak_active_requests"] <= 2
        and server["pid"] != run["runtime"]["pid"]
    )


def stream_byte_counts(run: dict[str, Any]) -> bool:
    received = integer(run["received_bytes"])
    largest = integer(run["max_chunk_bytes"])
    chunks = integer(run["chunk_count"])
    for name in ("stream_count", "warmup_requests", "measurement_requests"):
        integer(run[name])
    if received == 0:
        if largest or chunks:
            raise ValueError("empty stream has inconsistent chunk counters")
    elif not (
        0 < largest <= received
        and 0 < chunks
        and largest + chunks - 1 <= received <= chunks * largest
    ):
        raise ValueError("inconsistent stream chunk counters")
    pattern_value(run["received_sha256"], SHA256)
    return (
        received == run["expected_bytes"]
        and run["received_sha256"] == run["expected_sha256"]
        and 0 < largest <= 32768
        and all(
            run[name] == 1 for name in ("stream_count", "warmup_requests", "measurement_requests")
        )
    )


def stream_run(value: object, expected_source: dict[str, str], native_unit: str) -> dict[str, Any]:
    run = closed(
        value,
        "size_bytes stream_count received_bytes received_sha256 baseline_rss_native "
        "peak_rss_native rss_native_unit baseline_rss_bytes peak_rss_bytes extra_rss_bytes "
        "elapsed_seconds max_chunk_bytes chunk_count warmup_requests measurement_requests "
        "runtime size_mib expected_bytes expected_sha256 request_count connection_count "
        "peak_active_requests server passed",
        "stream run",
    )
    mib = integer(run["size_mib"], minimum=1)
    size = integer(run["size_bytes"], minimum=1)
    if mib not in STREAM_HASHES or size != mib * 1024 * 1024:
        raise ValueError("unknown stream measurement size")
    integer(run["expected_bytes"], minimum=1)
    if run["expected_bytes"] != size or run["expected_sha256"] != STREAM_HASHES[mib]:
        raise ValueError("stream expected bytes or fixed SHA-256 oracle differs")
    runtime = stream_runtime(run["runtime"], expected_source)
    stream_rss(run, native_unit)
    if number(run["elapsed_seconds"]) <= 0:
        raise ValueError("stream elapsed time must be positive")
    bytes_ok, server_ok = stream_byte_counts(run), stream_server(run, size)
    passed = (
        bytes_ok
        and server_ok
        and run["extra_rss_bytes"] <= 67108864
        and runtime["isolated"]
        and runtime["installed_source_matches"]
    )
    flag(run["passed"], passed)
    return run


def stream_native_unit(os_name: str) -> str:
    if os_name.startswith("Linux"):
        return "KiB"
    if os_name.startswith(("Darwin", "macOS")):
        return "bytes"
    raise ValueError("unsupported native RSS platform")


def stream_method(value: object, os_name: str) -> dict[str, Any]:
    method = closed(
        value,
        "rss_method rss_baseline rss_native_unit server_process_excluded consumer "
        "server_generation client_process_per_size streams_per_client consumer_queue_chunks "
        "backpressure phase_timeout_seconds pool_timeout_seconds limit",
        "stream method",
    )
    native_unit = stream_native_unit(os_name)
    required = {
        "rss_method": STREAM_PEAK_SOURCE,
        "rss_native_unit": native_unit,
        "consumer": "incremental_sha256_and_count",
        "server_generation": "repeating_0_to_255_bounded_32768_bytes",
    }
    if any(method[key] != expected for key, expected in required.items()):
        raise ValueError("unsupported stream measurement method")
    for name in ("server_process_excluded", "client_process_per_size"):
        flag(method[name], True)
    for name, expected in (("streams_per_client", 1), ("consumer_queue_chunks", 0)):
        if integer(method[name]) != expected:
            raise ValueError("unsupported stream concurrency method")
    for name, expected in (("phase_timeout_seconds", 5), ("pool_timeout_seconds", 1)):
        if number(method[name]) != expected:
            raise ValueError("unsupported stream timeout method")
    for name in ("rss_baseline", "backpressure", "limit"):
        text_value(method[name])
    return method


def stream_provenance(value: object, source_commit: str) -> tuple[dict[str, str], bool]:
    provenance = closed(
        value,
        "source_before source_after source_unchanged_during_measurement installed_source_matches",
        "stream provenance",
    )
    before, after = (source_snapshot(provenance[key]) for key in ("source_before", "source_after"))
    if before["commit"] != source_commit:
        raise ValueError("source commit differs from source snapshot")
    stable = provenance["source_unchanged_during_measurement"]
    if type(stable) is not bool or (stable and before != after):
        raise ValueError("source stability flag does not match snapshots")
    return python_hashes(before), stable


def stream_summary(report: dict[str, Any]) -> dict[str, Any]:
    closed(
        report,
        "schema_version report_kind source_commit environment provenance method limits "
        "runs size_growth_diagnostic passed",
        "stream report",
    )
    pattern_value(report["source_commit"], COMMIT)
    env = closed(
        report["environment"],
        "os machine python python_executable sqlite packages cpu disk",
        "stream environment",
    )
    for name in set(env) - {"packages"}:
        text_value(env[name])
    package_versions(env["packages"])
    method = stream_method(report["method"], env["os"])
    limits = closed(
        report["limits"],
        "extra_rss_bytes chunk_bytes connections total_deadline_seconds",
        "stream limits",
    )
    expected_limits = {"extra_rss_bytes": 67108864, "chunk_bytes": 32768, "connections": 2}
    if any(integer(limits[key]) != value for key, value in expected_limits.items()):
        raise ValueError("stream acceptance limits changed")
    if number(limits["total_deadline_seconds"]) != 120:
        raise ValueError("stream total deadline changed")
    expected, stable = stream_provenance(report["provenance"], report["source_commit"])
    if not isinstance(report["runs"], list) or len(report["runs"]) != 3:
        raise ValueError("exactly three stream sizes are required")
    runs = [stream_run(item, expected, method["rss_native_unit"]) for item in report["runs"]]
    if [run["size_mib"] for run in runs] != list(STREAM_HASHES):
        raise ValueError("stream sizes must be unique and ordered 16, 256, 1024 MiB")
    return stream_outcome(report, runs, stable, env, method)


def stream_outcome(
    report: dict[str, Any],
    runs: list[dict[str, Any]],
    stable: bool,
    environment: dict[str, Any],
    method: dict[str, Any],
) -> dict[str, Any]:
    growth = closed(report["size_growth_diagnostic"], "size_bytes extra_rss_bytes", "size growth")
    for name in ("size_bytes", "extra_rss_bytes"):
        values = growth[name]
        if not isinstance(values, list) or any(type(value) is not int for value in values):
            raise ValueError("invalid size growth diagnostic values")
        if values != [run[name] for run in runs]:
            raise ValueError("size growth diagnostic differs from stream measurements")
    installed = all(run["runtime"]["installed_source_matches"] for run in runs)
    flag(report["provenance"]["installed_source_matches"], installed)
    identity = {
        key: value for key, value in runs[0]["runtime"].items() if key not in {"pid", "modules"}
    }
    same_runtime = all(
        {key: value for key, value in run["runtime"].items() if key not in {"pid", "modules"}}
        == identity
        for run in runs
    ) and all(
        run["runtime"][key] == environment[key]
        for run in runs
        for key in ("os", "machine", "python", "python_executable", "sqlite", "packages")
    )
    passed = stable and installed and same_runtime and all(run["passed"] for run in runs)
    flag(report["passed"], passed)
    return {
        "kind": "raw_stream_budget_v1",
        "passed": passed,
        "rss_method": method["rss_method"],
        "rss_baseline": method["rss_baseline"],
        "rss_native_unit": method["rss_native_unit"],
        "source_unchanged_during_measurement": stable,
        "installed_source_matches": installed,
        "measurements": {
            str(run["size_mib"]) + "MiB": {
                key: run[key]
                for key in (
                    "received_bytes",
                    "extra_rss_bytes",
                    "baseline_rss_bytes",
                    "peak_rss_bytes",
                    "elapsed_seconds",
                    "max_chunk_bytes",
                    "chunk_count",
                    "connection_count",
                    "passed",
                )
            }
            for run in runs
        },
    }


def stream_v2_baseline_source(os_name: str) -> str:
    if stream_native_unit(os_name) == "KiB":
        return "linux.proc_self_stat.rss_pages"
    return "darwin.MACH_TASK_BASIC_INFO.resident_size"


def stream_v2_method(value: object, os_name: str) -> dict[str, Any]:
    additions = "rss_baseline_source rss_peak_source rss_interval rss_window".split()
    common = (
        "rss_method rss_baseline rss_native_unit server_process_excluded consumer "
        "server_generation client_process_per_size streams_per_client consumer_queue_chunks "
        "backpressure phase_timeout_seconds pool_timeout_seconds limit"
    )
    method = closed(value, common + " " + " ".join(additions), "stream v2 method")
    required = {
        "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2",
        "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup",
        "rss_baseline_source": stream_v2_baseline_source(os_name),
        "rss_peak_source": STREAM_PEAK_SOURCE,
        "rss_interval": "new_high_water_exact_else_zero_to_upper",
        "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation",
        "backpressure": "consumer awaits each next chunk; no producer task or body queue",
        "limit": "synthetic raw byte transport; no dataset endpoint or hard physical deadline",
    }
    if any(method[key] != expected for key, expected in required.items()):
        raise ValueError("unsupported stream v2 RSS method")
    # Reuse only the frozen v1 validator's common concurrency/transport checks.
    common_values = {key: item for key, item in method.items() if key not in additions}
    common_values["rss_method"] = STREAM_PEAK_SOURCE
    stream_method(common_values, os_name)
    return method


def stream_v2_rss(run: dict[str, Any], native_unit: str) -> None:
    baseline = integer(run["baseline_rss_bytes"], minimum=1)
    before = integer(run["pretransfer_peak_rss_bytes"], minimum=baseline)
    after = integer(run["peak_rss_bytes"], minimum=before)
    upper = integer(run["extra_rss_upper_bound_bytes"])
    lower = integer(run["extra_rss_lower_bound_bytes"])
    if upper != after - baseline or lower != (upper if after > before else 0):
        raise ValueError("stream RSS interval does not match native counter bounds")
    expected_method = stream_v2_baseline_source(run["runtime"]["os"])
    if run["baseline_rss_method"] != expected_method:
        raise ValueError("stream baseline method differs from runtime OS")
    factor = 1024 if native_unit == "KiB" else 1
    if native_unit == "KiB":
        pages = integer(run["baseline_rss_pages"], minimum=1)
        page_bytes = integer(run["rss_page_bytes"], minimum=1024)
        if page_bytes & (page_bytes - 1) or pages * page_bytes != baseline:
            raise ValueError("native RSS pages do not match byte measurement")
    for name in ("baseline", "pretransfer_peak", "peak"):
        native = number(run[name + "_rss_native"])
        if native <= 0 or native != int(native) or native * factor != run[name + "_rss_bytes"]:
            raise ValueError("native RSS does not match integer byte measurement")


def stream_v2_run(value: object, expected: dict[str, str], native_unit: str) -> dict[str, Any]:
    native_fields = " baseline_rss_pages rss_page_bytes" if native_unit == "KiB" else ""
    run = closed(
        value,
        "size_bytes stream_count received_bytes received_sha256 baseline_rss_native "
        "pretransfer_peak_rss_native pretransfer_peak_rss_bytes baseline_rss_method "
        "peak_rss_native rss_native_unit baseline_rss_bytes peak_rss_bytes "
        "extra_rss_lower_bound_bytes extra_rss_upper_bound_bytes elapsed_seconds "
        "max_chunk_bytes chunk_count warmup_requests measurement_requests runtime size_mib "
        "expected_bytes expected_sha256 request_count connection_count peak_active_requests "
        "server passed" + native_fields,
        "stream v2 run",
    )
    additions = {
        "pretransfer_peak_rss_native",
        "pretransfer_peak_rss_bytes",
        "baseline_rss_method",
        "extra_rss_lower_bound_bytes",
        "extra_rss_upper_bound_bytes",
    }
    additions.update(native_fields.split())
    # Common byte/hash/server/runtime checks still apply. The private projection's
    # 'extra' is the v2 upper bound, never the historical peak-minus-peak metric.
    common = {key: item for key, item in run.items() if key not in additions}
    common["extra_rss_bytes"] = run["extra_rss_upper_bound_bytes"]
    stream_run(common, expected, native_unit)
    stream_v2_rss(run, native_unit)
    return run


def stream_v2_limits(value: object) -> None:
    limits = closed(
        value,
        "extra_rss_upper_bound_bytes cross_size_span_upper_bound_bytes chunk_bytes "
        "connections total_deadline_seconds",
        "stream v2 limits",
    )
    required = {
        "extra_rss_upper_bound_bytes": 67108864,
        "cross_size_span_upper_bound_bytes": 8388608,
        "chunk_bytes": 32768,
        "connections": 2,
    }
    if any(integer(limits[key]) != expected for key, expected in required.items()):
        raise ValueError("stream v2 acceptance limits changed")
    if number(limits["total_deadline_seconds"]) != 120:
        raise ValueError("stream v2 total deadline changed")


def stream_v2_span_bound(runs: list[dict[str, Any]]) -> int:
    bound = 0
    for index, first in enumerate(runs):
        for other, second in enumerate(runs):
            if index != other:
                difference = (
                    first["extra_rss_upper_bound_bytes"] - second["extra_rss_lower_bound_bytes"]
                )
                bound = max(bound, difference)
    return bound


def stream_v2_growth(value: object, runs: list[dict[str, Any]]) -> dict[str, Any]:
    growth = closed(
        value,
        "method size_bytes lower_bound_bytes upper_bound_bytes span_upper_bound_bytes passed",
        "stream size growth acceptance",
    )
    if growth["method"] != "max_cross_size_upper_minus_lower":
        raise ValueError("unsupported stream growth method")
    expected_arrays = {
        "size_bytes": [run["size_bytes"] for run in runs],
        "lower_bound_bytes": [run["extra_rss_lower_bound_bytes"] for run in runs],
        "upper_bound_bytes": [run["extra_rss_upper_bound_bytes"] for run in runs],
    }
    for name, expected in expected_arrays.items():
        values = growth[name]
        if not isinstance(values, list) or any(type(item) is not int for item in values):
            raise ValueError("invalid stream growth acceptance array")
        if values != expected:
            raise ValueError("stream growth acceptance differs from RSS measurements")
    bound = stream_v2_span_bound(runs)
    if integer(growth["span_upper_bound_bytes"]) != bound:
        raise ValueError("stream cross-size RSS span bound differs from intervals")
    flag(growth["passed"], bound <= 8388608)
    return growth


def stream_v2_same_runtime(runs: list[dict[str, Any]], environment: dict[str, Any]) -> bool:
    identity = {
        key: value for key, value in runs[0]["runtime"].items() if key not in {"pid", "modules"}
    }
    return all(
        {key: value for key, value in run["runtime"].items() if key not in {"pid", "modules"}}
        == identity
        for run in runs
    ) and all(
        run["runtime"][key] == environment[key]
        for run in runs
        for key in ("os", "machine", "python", "python_executable", "sqlite", "packages")
    )


def stream_summary_v2(report: dict[str, Any]) -> dict[str, Any]:
    closed(
        report,
        "schema_version report_kind source_commit environment provenance method limits "
        "runs size_growth_acceptance passed",
        "stream v2 report",
    )
    pattern_value(report["source_commit"], COMMIT)
    environment = closed(
        report["environment"],
        "os machine python python_executable sqlite packages cpu disk",
        "stream environment",
    )
    for name in set(environment) - {"packages"}:
        text_value(environment[name])
    package_versions(environment["packages"])
    method = stream_v2_method(report["method"], environment["os"])
    stream_v2_limits(report["limits"])
    expected, stable = stream_provenance(report["provenance"], report["source_commit"])
    if not isinstance(report["runs"], list) or len(report["runs"]) != 3:
        raise ValueError("exactly three stream sizes are required")
    runs = [stream_v2_run(item, expected, method["rss_native_unit"]) for item in report["runs"]]
    if [run["size_mib"] for run in runs] != list(STREAM_HASHES):
        raise ValueError("stream sizes must be unique and ordered 16, 256, 1024 MiB")
    growth = stream_v2_growth(report["size_growth_acceptance"], runs)
    installed = all(run["runtime"]["installed_source_matches"] for run in runs)
    flag(report["provenance"]["installed_source_matches"], installed)
    passed = (
        stable
        and installed
        and stream_v2_same_runtime(runs, environment)
        and growth["passed"]
        and all(run["passed"] for run in runs)
    )
    flag(report["passed"], passed)
    fields = (
        "received_bytes baseline_rss_bytes pretransfer_peak_rss_bytes peak_rss_bytes "
        "extra_rss_lower_bound_bytes extra_rss_upper_bound_bytes elapsed_seconds "
        "max_chunk_bytes chunk_count connection_count passed"
    ).split()
    return {
        "kind": "raw_stream_budget_v2",
        "passed": passed,
        **{key: method[key] for key in method if key.startswith("rss_")},
        "source_unchanged_during_measurement": stable,
        "installed_source_matches": installed,
        "size_growth_acceptance": growth,
        "measurements": {
            str(run["size_mib"]) + "MiB": {key: run[key] for key in fields} for run in runs
        },
    }


def installation_summary(report: dict[str, Any]) -> dict[str, Any]:
    closed(
        report,
        "schema_version report_kind source_commit environment results passed",
        "installation",
    )
    pattern_value(report["source_commit"], COMMIT)
    if not isinstance(report["environment"], dict):
        raise ValueError("installation environment must be an object")
    results = report["results"]
    if not isinstance(results, list) or len(results) != 2:
        raise ValueError("one wheel and one sdist installation are required")
    kinds = [installation_row(row) for row in results]
    if set(kinds) != {"wheel", "sdist"}:
        raise ValueError("installation artifacts must be unique wheel and sdist")
    passed = all(
        row["origin_verified"] and all(row[key] == "passed" for key in INSTALL_CHECKS[1:])
        for row in results
    )
    flag(report["passed"], passed)
    return {
        "kind": "installation_v2",
        "cases": 2,
        "passed": passed,
        "checks": check_counts(results, INSTALL_CHECKS),
    }


def installation_row(value: object) -> str:
    row = closed(value, "archive sha256 members " + " ".join(INSTALL_CHECKS), "installation result")
    archive = text_value(row["archive"])
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+-]*", archive) is None or ".." in archive:
        raise ValueError("invalid installation artifact filename")
    if archive.endswith(".whl"):
        kind = "wheel"
    elif archive.endswith(".tar.gz"):
        kind = "sdist"
    else:
        raise ValueError("unknown installation artifact type")
    pattern_value(row["sha256"], SHA256)
    integer(row["members"], minimum=1)
    if type(row["origin_verified"]) is not bool:
        raise ValueError("installation origin result must be boolean")
    for name in INSTALL_CHECKS[1:]:
        if not isinstance(row[name], str) or row[name] not in {
            "passed",
            "failed",
            "not_run_unsupported_platform",
        }:
            raise ValueError("unknown installation smoke status")
    return kind


def measurement(value: dict[str, Any], *, startup: bool, rounded: bool = False) -> dict[str, Any]:
    samples_key, p95_key = (
        ("warm_samples_ms", "warm_p95_ms") if startup else ("samples_ms", "p95_ms")
    )
    samples = [number(item) for item in value[samples_key]]
    if len(samples) < 30 or any(item < 0 for item in samples):
        raise ValueError("invalid measurement samples")
    p95 = sorted(samples)[math.ceil(0.95 * len(samples)) - 1]
    reported = number(value[p95_key])
    # Older v1 receipts rounded the percentile to three decimal places.
    tolerance = 0.000501 if rounded else 1e-9
    if not math.isclose(p95, reported, rel_tol=0, abs_tol=tolerance):
        raise ValueError("reported p95 does not match all samples")
    budget = number(value["target_ms" if startup else "budget_ms"])
    passed = value["passed"]
    ambiguous = rounded and abs(reported - budget) <= 0.000501
    if (
        budget <= 0
        or type(passed) is not bool
        or (not ambiguous and passed != (reported <= budget))
    ):
        raise ValueError("reported budget outcome does not match p95")
    result = {"samples": len(samples), "p95_ms": reported, "budget_ms": budget, "passed": passed}
    if rounded:
        result["budget_decision_ambiguous_after_rounding"] = ambiguous
    return result


def check_counts(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> dict[str, Any]:
    return {
        field: dict(
            sorted(
                Counter(
                    str(row[field]).lower() if field in row else "not_recorded" for row in rows
                ).items()
            )
        )
        for field in fields
    }


def startup_summary(report: dict[str, Any]) -> dict[str, Any]:
    groups = {"candidate": report["measurements"]}
    comparison = report.get("comparison")
    if comparison is None:
        comparison = {}
    if not isinstance(comparison, dict):
        raise ValueError("startup comparison must be an object or null")
    baseline = comparison.get("baseline_measurements")
    if baseline is not None:
        groups["baseline"] = baseline
    return {
        "kind": "startup",
        "measurements": {
            f"{group}/{key}": measurement(
                value, startup=True, rounded=report.get("schema_version") == 1
            )
            for group, entries in groups.items()
            for key, value in entries.items()
        },
    }


def jobs_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = {f"{r['layout']}/{r['action']}": measurement(r, startup=False) for r in runs}
    if len(metrics) != len(runs):
        raise ValueError("duplicate measurement group")
    return {"kind": "jobs", "measurements": metrics}


def jobs_runtime(value: object) -> dict[str, Any]:
    runtime = closed(
        value,
        "python executable prefix platform machine sqlite packages product_origin product_version "
        "console console_sha256 installed_source_sha256",
        "jobs runtime",
    )
    prefix = runtime_path(runtime["prefix"])
    for name in ("executable", "product_origin", "console"):
        if not runtime_origin(runtime[name], prefix, text_value(runtime["platform"])):
            raise ValueError("jobs runtime origin escaped its installed environment")
    for name in ("python", "platform", "machine", "sqlite", "product_version"):
        text_value(runtime[name])
    pattern_value(runtime["console_sha256"], SHA256)
    package_versions(runtime["packages"])
    hash_map(runtime["installed_source_sha256"])
    return runtime


def jobs_artifact_metadata(provenance: dict[str, Any]) -> None:
    for key in ("fixture_preparation_python", "fixture_preparation"):
        text_value(provenance[key])
    if provenance["wheel_sha256"] is not None:
        pattern_value(provenance["wheel_sha256"], SHA256)
        text_value(provenance["wheel_path"])
    elif provenance["wheel_path"] is not None:
        raise ValueError("jobs wheel path without wheel digest")


def jobs_provenance(report: dict[str, Any]) -> dict[str, Any]:
    provenance = closed(
        report["provenance"],
        "source_before source_after installed_before installed_after wheel_sha256 wheel_path "
        "source_unchanged_during_measurement installed_unchanged_during_measurement "
        "fixtures_unchanged_during_measurement unchanged isolated_python "
        "fixture_preparation_python fixture_preparation",
        "jobs provenance",
    )
    before, after = (source_snapshot(provenance[key]) for key in ("source_before", "source_after"))
    if before["commit"] != report["source_commit"]:
        raise ValueError("jobs source commit differs from snapshot")
    installed_before, installed_after = (
        jobs_runtime(provenance[key]) for key in ("installed_before", "installed_after")
    )
    flag(provenance["source_unchanged_during_measurement"], before == after)
    flag(provenance["installed_unchanged_during_measurement"], installed_before == installed_after)
    for key in ("fixtures_unchanged_during_measurement", "unchanged", "isolated_python"):
        if type(provenance[key]) is not bool:
            raise ValueError("jobs provenance flags must be boolean")
    known_stable = (
        before == after
        and installed_before == installed_after
        and provenance["fixtures_unchanged_during_measurement"]
    )
    # The producer retains the initial wheel hash, not a second wheel/fixture snapshot.
    # A false unchanged flag can therefore record a real transient artifact change.
    if provenance["unchanged"] and not known_stable:
        raise ValueError("jobs unchanged flag contradicts retained snapshots")
    jobs_artifact_metadata(provenance)
    for source, installed in ((before, installed_before), (after, installed_after)):
        expected = python_hashes(source, package_prefix=True)
        if provenance["unchanged"] and installed["installed_source_sha256"] != expected:
            raise ValueError("jobs installed Python bytes differ from source")
    if report["environment"]["runtime"] != installed_before:
        raise ValueError("jobs environment differs from installed provenance")
    return provenance


def jobs_command(run: dict[str, Any], runtime: dict[str, Any]) -> None:
    command = run["command"]
    if not isinstance(command, list) or len(command) != 11:
        raise ValueError("jobs command must record the complete measured invocation")
    for part in command:
        text_value(part)
    prefix = [runtime["executable"], "-I", runtime["console"], "jobs", run["action"]]
    selection = (
        ["--limit", "50"]
        if run["action"] == "list"
        else ["--operation-id", run["expected_operation_id"]]
    )
    expected = prefix + selection + ["--state-dir", command[8], "--output", "json"]
    if command != expected:
        raise ValueError("jobs command contradicts its installed runtime or measurement")
    runtime_path(command[8])


def jobs_run_checks(run: dict[str, Any], samples: int, runtime: dict[str, Any]) -> bool:
    closed(
        run,
        "layout action command first_process_ms warmups_ms samples_ms median_ms p95_ms budget_ms "
        "passed typed_stdout_verified verified_processes stdout_sha256 expected_list_rows "
        "expected_operation_id expected_plan_digest",
        "jobs run",
    )
    if len(run["samples_ms"]) != samples or number(run["budget_ms"]) != 200:
        raise ValueError("jobs sample count or acceptance budget differs")
    if number(run["median_ms"]) != statistics.median(run["samples_ms"]):
        raise ValueError("jobs median differs from all samples")
    warmups = run["warmups_ms"]
    if not isinstance(warmups, list) or len(warmups) != 3:
        raise ValueError("jobs requires three warmup processes")
    if any(number(value) <= 0 for value in [run["first_process_ms"], *warmups, *run["samples_ms"]]):
        raise ValueError("jobs process times must be positive")
    processes = integer(run["verified_processes"], minimum=1)
    hashes = run["stdout_sha256"]
    if processes != samples + 4 or not isinstance(hashes, list) or len(hashes) != processes:
        raise ValueError("jobs output verification must cover every process")
    for digest in hashes:
        pattern_value(digest, SHA256)
    if type(run["typed_stdout_verified"]) is not bool:
        raise ValueError("jobs typed output verification must be boolean")
    jobs_command(run, runtime)
    return bool(run["typed_stdout_verified"])


def modern_jobs_summary(report: dict[str, Any]) -> dict[str, Any]:
    closed(
        report,
        "schema_version kind source_commit samples_per_command method cold_method "
        "validation_method "
        "environment fixtures runs provenance passed",
        "jobs report",
    )
    if type(report["schema_version"]) is not int or report["schema_version"] != 1:
        raise ValueError("unsupported jobs report schema version")
    pattern_value(report["source_commit"], COMMIT)
    samples = integer(report["samples_per_command"], minimum=30)
    for key in ("method", "cold_method", "validation_method"):
        text_value(report[key])
    if not isinstance(report["environment"], dict) or "runtime" not in report["environment"]:
        raise ValueError("missing jobs environment runtime")
    if not isinstance(report["fixtures"], dict) or set(report["fixtures"]) != {"normal", "dense"}:
        raise ValueError("jobs requires normal and dense fixtures")
    runs = report["runs"]
    if not isinstance(runs, list) or len(runs) != 4:
        raise ValueError("jobs requires four measurement groups")
    summary = jobs_summary(runs)
    if set(summary["measurements"]) != {"normal/list", "normal/show", "dense/list", "dense/show"}:
        raise ValueError("jobs measurement groups differ from acceptance cases")
    provenance = jobs_provenance(report)
    checked = True
    # Validate every group even when an earlier group truthfully failed its gate.
    for run in runs:
        checked = jobs_run_checks(run, samples, provenance["installed_before"]) and checked
    passed = (
        provenance["unchanged"]
        and provenance["isolated_python"]
        and checked
        and all(run["passed"] for run in runs)
    )
    flag(report["passed"], passed)
    summary.update(
        {
            key: provenance[key]
            for key in (
                "source_unchanged_during_measurement",
                "installed_unchanged_during_measurement",
                "fixtures_unchanged_during_measurement",
                "unchanged",
                "isolated_python",
            )
        }
    )
    summary["passed"] = passed
    return summary


def run_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "kind": "migration" if "source_version" in runs[0] else "operation",
        "cases": len(runs),
        "outcomes": dict(sorted(Counter(r["outcome"] for r in runs).items())),
    }
    elapsed = [number(r["elapsed_ms"]) for r in runs if "elapsed_ms" in r]
    if elapsed:
        result["max_elapsed_ms"] = max(elapsed)
    return result


def payload_summary(report: dict[str, Any]) -> dict[str, Any]:
    if "report_kind" in report:
        return typed_summary(report)
    if report.get("kind") == "jobs":
        return modern_jobs_summary(report)
    runs = report.get("runs", [])
    if "measurements" in report:
        return startup_summary(report)
    if isinstance(runs, list) and runs and "samples_ms" in runs[0]:
        return jobs_summary(runs)
    if "sources" in report and "unchanged" in report:
        return {
            "kind": "comparison",
            "cases": len(runs),
            "diagnostic_only": True,
            "outcomes": dict(sorted(Counter(r["outcome"] for r in runs).items())),
        }
    if isinstance(runs, list) and runs and "outcome" in runs[0]:
        return run_summary(runs)
    if "results" in report:
        return {
            "kind": "installation",
            "cases": len(report["results"]),
            "checks": check_counts(
                report["results"],
                ("origin_verified", "smoke", "cache_smoke", "execution_smoke", "jobs_smoke"),
            ),
        }
    if "cases" in report:
        return {
            "kind": "help-parity",
            "cases": len(report["cases"]),
            "checks": check_counts(
                report["cases"], ("equal", "root_expected_jobs_addition", "matches_initial_p014")
            ),
        }
    if "outcome" in report:
        return {"kind": "diagnostic", "outcome": report["outcome"], "diagnostic_only": True}
    if report.get("diagnostic_only") is True:
        return {"kind": "diagnostic", "cases": len(runs), "diagnostic_only": True}
    raise ValueError("unsupported measurement report; test vectors are not raw receipts")


def typed_summary(report: dict[str, Any]) -> dict[str, Any]:
    kind = report["report_kind"]
    version = report.get("schema_version")
    if type(version) is not int:
        raise ValueError("invalid typed report schema version")
    if kind == "raw_stream_budget_v1" and version == 1:
        return stream_summary(report)
    if kind == "raw_stream_budget_v2" and version == 2:
        return stream_summary_v2(report)
    if kind == "installation_v2" and version == 2:
        return installation_summary(report)
    if kind == "startup_evidence_v1" and version == 1:
        startup = runpy.run_path(str(Path(__file__).with_name("startup_evidence.py")))
        return startup["validate"](report)  # type: ignore[no-any-return]
    if kind == "startup_ci_diagnostic_v1" and version == 1:
        startup_ci = runpy.run_path(str(Path(__file__).with_name("startup_diagnostic.py")))
        return startup_ci["receipt_summary"](report)  # type: ignore[no-any-return]
    if kind == "startup_baseline_selection_v1" and version == 1:
        baseline = runpy.run_path(str(Path(__file__).with_name("startup_baseline.py")))
        return baseline["summarize"](report)  # type: ignore[no-any-return]
    if kind == "rejected_startup_evidence_v1" and version == 1:
        return rejected_startup_summary(report)
    raise ValueError("unsupported typed report kind or schema version")


def rejected_startup_summary(report: dict[str, Any]) -> dict[str, Any]:
    closed(
        report,
        "schema_version report_kind source_commit run_url original_name original_sha256 "
        "original_bytes rejection_reason content_base64",
        "rejected startup attachment",
    )
    pattern_value(report["source_commit"], COMMIT)
    pattern_value(report["original_name"], NAME)
    pattern_value(report["original_sha256"], SHA256)
    if report["rejection_reason"] not in {
        "invalid_evidence",
        "interrupted_measurement",
        "unverified_measurement",
    }:
        raise ValueError("unknown rejected startup reason")
    pattern_value(report["run_url"], CI_RUN_URL)
    size = integer(report["original_bytes"])
    encoded = report["content_base64"]
    if not isinstance(encoded, str):
        raise ValueError("rejected startup content must be base64 text")
    if size > MAX_REJECTED_STARTUP_BYTES or len(encoded) > 4 * (
        (MAX_REJECTED_STARTUP_BYTES + 2) // 3
    ):
        raise ValueError("rejected startup attachment exceeds its byte limit")
    try:
        original = base64.b64decode(encoded, validate=True)
    except ValueError:
        raise ValueError("invalid rejected startup base64") from None
    if len(original) != size or hashlib.sha256(original).hexdigest() != report["original_sha256"]:
        raise ValueError("rejected startup attachment bytes/hash mismatch")
    return {
        "kind": "rejected_startup_evidence",
        "source_commit": report["source_commit"],
        "run_url": report["run_url"],
        "original_name": report["original_name"],
        "original_sha256": report["original_sha256"],
        "original_bytes": size,
        "rejection_reason": report["rejection_reason"],
        "diagnostic_only": True,
        "accepted": False,
    }


def summarize(report: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "source_commit": next(
            (
                report[key]
                for key in ("source_commit", "source_base_commit", "source_reference")
                if key in report
            ),
            None,
        ),
        "diagnostic_only": report.get("diagnostic_only", False),
    }
    summary.update(payload_summary(report))
    return summary


def entry(name: str, content: bytes, archive: bytes, original_commit: str | None) -> dict[str, Any]:
    if NAME.fullmatch(name) is None or (
        original_commit is not None and COMMIT.fullmatch(original_commit) is None
    ):
        raise ValueError("invalid evidence name or original commit")
    return {
        "name": name,
        "archive": f"raw/{name}.gz",
        "original_commit": original_commit,
        "content_bytes": len(content),
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "archive_bytes": len(archive),
        "archive_sha256": hashlib.sha256(archive).hexdigest(),
        "summary": summarize(decode(content)),
    }


def catalog(directory: Path) -> list[dict[str, Any]]:
    data = decode(read_bounded(directory / MANIFEST, MAX_REPORT_BYTES))
    if set(data) != {"schema_version", "entries"} or type(data["schema_version"]) is not int:
        raise ValueError("invalid evidence manifest")
    entries = data["entries"]
    if (
        data["schema_version"] != 1
        or not isinstance(entries, list)
        or not 1 <= len(entries) <= MAX_ENTRIES
    ):
        raise ValueError("invalid evidence manifest entries")
    if any(
        not isinstance(item, dict)
        or not isinstance(item.get("name"), str)
        or NAME.fullmatch(item["name"]) is None
        for item in entries
    ):
        raise ValueError("invalid evidence manifest entry")
    names = [item["name"] for item in entries]
    if names != sorted(set(names)):
        raise ValueError("evidence entries must be unique and sorted")
    return list(entries)


def index_text(entries: list[dict[str, Any]]) -> str:
    lines = [
        "# Ham ölçüm kanıtları",
        "",
        "Bu indeks manifest ve özgün JSON baytlarından üretilir.",
        "Arşiv biçimi ve sınırlar [kanıt standardındadır](../standards/research-evidence.md).",
        "Eski başarısız ölçümler ve tanılar korunur; güncel kabul ayrıca incelenir.",
        "Gzip dosyaları Git checkout'unda tutulur; sdist/wheel içine girmez.",
        "",
    ]
    for item in entries:
        name, summary = item["name"], item["summary"]
        lines += [f"## {name.removesuffix('.json')}", "", f"**Tür:** `{summary['kind']}`."]
        lines.append(f"**Özgün JSON SHA-256:** `{item['content_sha256']}`.")
        if item["original_commit"] is not None:
            url = (
                "https://github.com/HodeTech/Yorunge/blob/"
                f"{item['original_commit']}/docs/research/{name}"
            )
            lines.append(f"[İlk kayıt baytları]({url}); yerel arşiv `raw/{name}.gz`.")
        else:
            lines.append(f"**Yerel arşiv:** `raw/{name}.gz`.")
        lines.append("**Özet:** `" + json.dumps(summary, ensure_ascii=False, sort_keys=True) + "`.")
        lines.append("")
    return "\n".join(lines)


def unpack(directory: Path, item: dict[str, Any]) -> bytes:
    archive = read_bounded(directory / "raw" / f"{item['name']}.gz", MAX_ARCHIVE_BYTES)
    with gzip.GzipFile(fileobj=io.BytesIO(archive)) as stream:
        content = stream.read(MAX_REPORT_BYTES + 1)
    if len(content) > MAX_REPORT_BYTES:
        raise ValueError("decompressed evidence size limit exceeded")
    expected = entry(item["name"], content, archive, item.get("original_commit"))
    if json.dumps(expected, sort_keys=True) != json.dumps(item, sort_keys=True):
        raise ValueError(f"evidence hash or summary mismatch: {item['name']}")
    return content


def verify(root: Path) -> int:
    directory = research_directory(root)
    entries = catalog(directory)
    expected = {f"{item['name']}.gz" for item in entries}
    if {path.name for path in (directory / "raw").iterdir()} != expected:
        raise ValueError("unregistered or missing evidence archive")
    for item in entries:
        unpack(directory, item)
        if (directory / item["name"]).exists():
            raise ValueError("archived report must not also be committed as expanded JSON")
    if read_bounded(directory / INDEX, MAX_REPORT_BYTES) != index_text(entries).encode():
        raise ValueError("evidence index is stale")
    return len(entries)


def current_jobs_inputs(root: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Read the producer's complete source scope and frozen runtime without running it."""
    benchmark = runpy.run_path(str(root / "scripts/benchmark-jobs.py"))
    source = benchmark["source"](root)
    return hash_map(source["source_sha256"]), package_versions(benchmark["locked_runtime"](root))


def jobs_reference_environment(environment: dict[str, Any]) -> None:
    runtime = environment["runtime"]
    declared = {key: environment.get(key) for key in ("cpu", "disk_type")}
    expected = {key: JOBS_REFERENCE[key] for key in declared}
    if declared != expected or runtime["machine"] != JOBS_REFERENCE["machine"]:
        raise ValueError("jobs proof does not declare the configured M5 reference environment")
    for key in ("platform", "python"):
        if not runtime[key].startswith(JOBS_REFERENCE[key + "_prefix"]):
            raise ValueError("jobs proof does not declare the configured M5 reference runtime")


def jobs_reference_sources(root: Path, provenance: dict[str, Any]) -> None:
    current_source, locked_packages = current_jobs_inputs(root)
    for key in ("source_before", "source_after"):
        if provenance[key]["source_sha256"] != current_source:
            raise ValueError(
                "jobs reference proof does not match the complete current source bytes"
            )
    for key in ("installed_before", "installed_after"):
        if provenance[key]["packages"] != locked_packages:
            raise ValueError("jobs reference runtime packages differ from the current frozen lock")


def jobs_reference_rows(value: object, layout: str) -> None:
    rows = closed(value, " ".join(JOBS_REFERENCE_ROWS), "jobs reference fixture rows")
    for table, counts in JOBS_REFERENCE_ROWS.items():
        row = closed(
            rows[table],
            "records payload_bytes largest_record_bytes",
            "jobs reference table",
        )
        count = integer(row["records"])
        total, largest = integer(row["payload_bytes"]), integer(row["largest_record_bytes"])
        if count != counts[layout == "dense"]:
            raise ValueError("jobs reference fixture row count differs from acceptance workload")
        if (count == 0 and (total or largest)) or (
            count > 0 and not 0 < largest <= total <= count * largest
        ):
            raise ValueError("jobs reference fixture payload counters are inconsistent")
    if layout == "dense":
        jobs_reference_dense_rows(rows)


def jobs_reference_dense_rows(rows: dict[str, Any]) -> None:
    required = {"execution_plans": (67108864, 65536), "capability_cache": (33554432, 32768)}
    for table, (total, largest) in required.items():
        if rows[table]["payload_bytes"] != total or rows[table]["largest_record_bytes"] != largest:
            raise ValueError(
                "jobs reference dense fixture payload differs from acceptance workload"
            )


def jobs_reference_fixture(value: object, layout: str) -> dict[str, Any]:
    fixture = closed(
        value,
        "rows database_bytes database_sha256 list_summaries has_next_cursor "
        "show_summary show_attempts show_outcome",
        "jobs reference fixture",
    )
    jobs_reference_rows(fixture["rows"], layout)
    integer(fixture["database_bytes"], minimum=1)
    pattern_value(fixture["database_sha256"], SHA256)
    summaries = fixture["list_summaries"]
    expected_rows = 50 if layout == "dense" else 1
    if not isinstance(summaries, list) or len(summaries) != expected_rows:
        raise ValueError("jobs reference list fixture has the wrong result count")
    flag(fixture["has_next_cursor"], layout == "dense")
    target = fixture["show_summary"]
    if not isinstance(target, dict) or target != summaries[0]:
        raise ValueError("jobs reference show fixture differs from the selected list result")
    text_value(target.get("operation_id"))
    pattern_value(target.get("plan_digest"), SHA256)
    jobs_reference_summaries(fixture, layout)
    jobs_reference_attempts(fixture, layout)
    jobs_reference_outcome(fixture, layout)
    return fixture


def jobs_reference_summaries(fixture: dict[str, Any], layout: str) -> None:
    from yorunge.domain.operations import JobSummary

    summaries = [
        JobSummary.model_validate(value, strict=True) for value in fixture["list_summaries"]
    ]
    if len({summary.operation_id for summary in summaries}) != len(summaries):
        raise ValueError("jobs reference list contains duplicate operation IDs")
    if len({summary.plan_id for summary in summaries}) != len(summaries):
        raise ValueError("jobs reference list contains duplicate plan IDs")
    expected = (
        ("succeeded", "succeeded", "complete", 16, False)
        if layout == "dense"
        else (
            "running",
            "running",
            "pending",
            1,
            False,
        )
    )
    for summary in summaries:
        actual = (
            summary.status,
            summary.execution_status,
            summary.delivery_status,
            summary.attempt_count,
            summary.clock_anomaly,
        )
        if actual != expected:
            raise ValueError("jobs reference summary differs from the declared fixture layout")


def jobs_reference_attempts(fixture: dict[str, Any], layout: str) -> None:
    from yorunge.domain.operations import AttemptView

    values = fixture["show_attempts"]
    count = 16 if layout == "dense" else 1
    if not isinstance(values, list) or len(values) != count:
        raise ValueError("jobs reference show requires every fixture attempt")
    attempts = [AttemptView.model_validate(value, strict=True) for value in values]
    if [attempt.number for attempt in attempts] != list(range(1, count + 1)) or len(
        {attempt.attempt_id for attempt in attempts}
    ) != count:
        raise ValueError("jobs reference attempts require sequential numbers and unique IDs")
    for attempt in attempts[:-1]:
        if attempt.status != "abandoned" or attempt.reason_code != "owner_changed":
            raise ValueError("jobs reference historical attempts differ from the fixture layout")
    current = attempts[-1]
    expected_status, expected_exit = ("succeeded", 0) if layout == "dense" else ("running", None)
    if (
        current.status != expected_status
        or current.reason_code is not None
        or current.provider_run_id is None
        or current.provider_status is None
        or current.provider_exit_code != expected_exit
    ):
        raise ValueError("jobs reference current attempt differs from the fixture layout")


def jobs_reference_outcome(fixture: dict[str, Any], layout: str) -> None:
    from yorunge.domain.operations import OperationOutcome

    value = fixture["show_outcome"]
    if layout == "normal":
        if value is not None:
            raise ValueError("jobs reference running fixture cannot have a terminal outcome")
        return
    outcome_fields = " ".join(OperationOutcome.model_fields)
    data = closed(value, outcome_fields, "jobs reference terminal outcome")
    if integer(data["schema_version"], minimum=1) != 1:
        raise ValueError("jobs reference outcome requires schema version 1")
    outcome = OperationOutcome.model_validate(data, strict=True)
    if (
        outcome.execution_status != "succeeded"
        or outcome.delivery_status != "complete"
        or outcome.provider_exit_code != 0
        or outcome.reason_code is not None
    ):
        raise ValueError("jobs reference terminal outcome differs from the fixture layout")


def jobs_reference_state_paths(report: dict[str, Any]) -> None:
    platform = report["environment"]["runtime"]["platform"]
    paths = {
        layout: {
            canonical_runtime_path(run["command"][8], platform)
            for run in report["runs"]
            if run["layout"] == layout
        }
        for layout in ("normal", "dense")
    }
    if any(len(values) != 1 for values in paths.values()) or paths["normal"] == paths["dense"]:
        raise ValueError("jobs reference requires one distinct state path per fixture layout")


def jobs_reference_fixtures(report: dict[str, Any]) -> None:
    fixtures = {
        layout: jobs_reference_fixture(report["fixtures"][layout], layout)
        for layout in ("normal", "dense")
    }
    for run in report["runs"]:
        fixture = fixtures[run["layout"]]
        if run["action"] == "list":
            rows = integer(run["expected_list_rows"], minimum=1)
            if rows != len(fixture["list_summaries"]):
                raise ValueError("jobs reference list expectation differs from its fixture")
        elif (
            run["expected_operation_id"] != fixture["show_summary"]["operation_id"]
            or run["expected_plan_digest"] != fixture["show_summary"]["plan_digest"]
        ):
            raise ValueError("jobs reference show expectation differs from its fixture")
    jobs_reference_state_paths(report)


def verify_jobs_reference(root: Path, name: str) -> dict[str, Any]:
    """Check a declared reference receipt against current code, never rerun its benchmark.

    Hash equality binds retained evidence to source bytes; it is not an attestation
    of the physical host or a performance result for the verifier's current host.
    A docs-only Git commit may differ when the complete measured source map is equal.
    """
    if NAME.fullmatch(name) is None:
        raise ValueError("invalid jobs reference evidence name")
    verify(root)
    directory = research_directory(root)
    item = next((item for item in catalog(directory) if item["name"] == name), None)
    if item is None:
        raise ValueError("unknown jobs reference evidence name")
    report = decode(unpack(directory, item))
    if report.get("kind") != "jobs":
        raise ValueError("jobs reference proof requires a modern jobs receipt")
    summary = modern_jobs_summary(report)
    if not summary["passed"] or report["samples_per_command"] != 30:
        raise ValueError("jobs reference proof requires four passing 200 ms / 30-process cases")
    jobs_reference_environment(report["environment"])
    jobs_reference_fixtures(report)
    jobs_reference_sources(root, report["provenance"])
    return {
        "name": name,
        "source_commit": report["source_commit"],
        "cpu": report["environment"]["cpu"],
        "p95_ms": {key: value["p95_ms"] for key, value in summary["measurements"].items()},
    }


def verify_startup_reference(root: Path, name: str) -> dict[str, Any]:
    if NAME.fullmatch(name) is None:
        raise ValueError("invalid startup reference evidence name")
    verify(root)
    directory = research_directory(root)
    item = next((item for item in catalog(directory) if item["name"] == name), None)
    if item is None:
        raise ValueError("unknown startup reference evidence name")
    report = decode(unpack(directory, item))
    startup = runpy.run_path(str(Path(__file__).with_name("startup_evidence.py")))
    return startup["reference"](root, report)  # type: ignore[no-any-return]


def replace_metadata(path: Path, content: bytes) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("metadata target must be a regular file")
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.close()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def report_source(root: Path, source: Path) -> Path:
    source = source.absolute()
    if NAME.fullmatch(source.name) is None or ".." in source.parts:
        raise ValueError("expected a canonical measurement filename")
    directory = root / "dist"
    if source.parent != directory:
        raise ValueError("report input must be directly inside dist")
    if directory.is_symlink():
        raise ValueError("report input directory must not be a symlink")
    return directory / source.name


def archive_report(root: Path, source: Path, original_commit: str | None) -> None:
    directory = research_directory(root)
    source = report_source(root, source)
    content = read_bounded(source, MAX_REPORT_BYTES)
    archive = gzip.compress(content, mtime=0)
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise ValueError("compressed evidence size limit exceeded")
    item = entry(source.name, content, archive, original_commit)
    entries = catalog(directory) if (directory / MANIFEST).exists() else []
    if any(existing["name"] == source.name for existing in entries):
        raise ValueError("evidence already registered; existing bytes are preserved")
    if len(entries) >= MAX_ENTRIES:
        raise ValueError("evidence catalog capacity exceeded; existing bytes are preserved")
    entries = sorted([*entries, item], key=lambda value: value["name"])
    (directory / "raw").mkdir(exist_ok=True)
    with (directory / "raw" / f"{source.name}.gz").open("xb") as stream:
        stream.write(archive)
    replace_metadata(directory / MANIFEST, encode({"schema_version": 1, "entries": entries}))
    replace_metadata(directory / INDEX, index_text(entries).encode())


def archive_rejected_startup(
    root: Path, source: Path, name: str, source_commit: str, run_url: str, reason: str
) -> None:
    source = report_source(root, source)
    if NAME.fullmatch(name) is None:
        raise ValueError("invalid rejected startup archive name")
    content = read_bounded(source, MAX_REJECTED_STARTUP_BYTES)
    report = {
        "schema_version": 1,
        "report_kind": "rejected_startup_evidence_v1",
        "source_commit": source_commit,
        "run_url": run_url,
        "original_name": source.name,
        "original_sha256": hashlib.sha256(content).hexdigest(),
        "original_bytes": len(content),
        "rejection_reason": reason,
        "content_base64": base64.b64encode(content).decode("ascii"),
    }
    rejected_startup_summary(report)
    destination = root / "dist" / name
    with destination.open("xb") as stream:
        stream.write(encode(report))
    archive_report(root, destination, None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("verify")
    add = commands.add_parser("archive")
    add.add_argument("source", type=Path)
    add.add_argument("--original-commit")
    show = commands.add_parser("show")
    show.add_argument("name")
    reference = commands.add_parser("verify-jobs-reference")
    reference.add_argument("name")
    startup_reference = commands.add_parser("verify-startup-reference")
    startup_reference.add_argument("name")
    rejected = commands.add_parser("archive-rejected-startup")
    rejected.add_argument("source", type=Path)
    rejected.add_argument("--name", required=True)
    rejected.add_argument("--source-commit", required=True)
    rejected.add_argument("--run-url", required=True)
    rejected.add_argument(
        "--reason",
        required=True,
        choices=("invalid_evidence", "interrupted_measurement", "unverified_measurement"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        if args.action == "archive-rejected-startup":
            archive_rejected_startup(
                root, args.source, args.name, args.source_commit, args.run_url, args.reason
            )
            print("Archived rejected startup bytes as a diagnostic attachment; not acceptance.")
        elif args.action == "archive":
            archive_report(root, args.source, args.original_commit)
            print("Archived original bytes; the input file was preserved.")
        elif args.action == "show":
            directory = research_directory(root)
            item = next((item for item in catalog(directory) if item["name"] == args.name), None)
            if item is None:
                raise ValueError("unknown evidence name")
            sys.stdout.buffer.write(unpack(directory, item))
        elif args.action == "verify-jobs-reference":
            verify_jobs_reference(root, args.name)
            print(
                f"Jobs reference proof validated: {args.name}; four 30-process cases, "
                "each p95 <= 200 ms; current source bytes match the declared M5 reference."
            )
        elif args.action == "verify-startup-reference":
            summary = verify_startup_reference(root, args.name)
            print(json.dumps(summary, sort_keys=True, allow_nan=False))
        else:
            print(f"Verified {verify(root)} lossless evidence archives and their index.")
    except (OSError, ValueError, KeyError, TypeError, EOFError) as error:
        parser.exit(1, f"Evidence check failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
