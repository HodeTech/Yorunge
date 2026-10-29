"""Measure installed raw HTTPS streams without retaining response bodies.

All three acceptance sizes run serially, each in a fresh isolated runtime-only
client. This synthetic localhost TLS probe does not demonstrate dataset support.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import runpy
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
SIZES_MIB = (16, 256, 1024)
CHUNK_BYTES = 32_768
RSS_LIMIT_BYTES = 67_108_864
TOTAL_SECONDS = 120.0


def environment() -> dict[str, str]:
    value = dict(os.environ)
    for name in tuple(value):
        if name.startswith("PYTHON") or name == "VIRTUAL_ENV":
            value.pop(name)
    return value


def new_path(path: Path, *, parent_required: bool = True) -> Path:
    """Reject existing names and symlink ancestors before touching input sources."""
    path = path.absolute()
    if (
        path.exists()
        or path.is_symlink()
        or any(parent.is_symlink() for parent in path.parents)
        or (parent_required and not path.parent.is_dir())
    ):
        raise ValueError("use a new path in an existing directory without symlinks")
    return path


def source(project: Path) -> dict[str, Any]:
    paths = sorted((project / "src").rglob("*.py"))
    paths += sorted((project / "scripts").glob("*.py"))
    paths += [
        project / name
        for name in (
            "pyproject.toml",
            "uv.lock",
            "tests/fixtures/stream_budget.py",
            "tests/fixtures/http_server.py",
        )
    ]
    if not any(path.is_relative_to(project / "src" / "yorunge") for path in paths):
        raise ValueError("measured checkout has no product Python sources")
    if any(path.is_symlink() for path in paths):
        raise ValueError("measured sources must not be symlinks")
    hashes = {
        str(path.relative_to(project)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project,
        env=environment(),
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    ).stdout.strip()
    return {"commit": revision, "source_sha256": hashes}


def locked_runtime(project: Path) -> dict[str, str]:
    """Follow the frozen runtime dependency closure, excluding development groups."""
    lock = tomllib.loads((project / "uv.lock").read_text(encoding="utf-8"))
    packages = {}
    for item in lock["package"]:
        name = re.sub(r"[-_.]+", "-", item["name"].lower())
        if name in packages:
            raise ValueError("duplicate normalized package in runtime lock")
        packages[name] = item
    pending, versions = ["yorunge"], {}
    while pending:
        name = pending.pop()
        if name in versions:
            continue
        item = packages[name]
        versions[name] = item["version"]
        pending.extend(
            re.sub(r"[-_.]+", "-", dependency["name"].lower())
            for dependency in item.get("dependencies", [])
        )
    return versions


def runtime_identity(runtime: dict[str, Any]) -> dict[str, Any]:
    """PIDs and the lazily imported module set may differ; runtime identity may not."""
    return {name: value for name, value in runtime.items() if name not in {"pid", "modules"}}


def expected_sha256(size: int) -> str:
    """Independent bounded oracle: generate 64KiB arithmetic-pattern blocks.

    The TLS server uses bytes(range(256)) and a different 32KiB block size. Neither
    side allocates a response-sized object or obtains its expected hash from HTTP.
    """
    if type(size) is not int or not 1 <= size <= 1024 * 1024 * 1024:
        raise ValueError("expected size must be between 1 byte and 1 GiB")
    block = bytes(index % 256 for index in range(65_536))
    digest = hashlib.sha256()
    remaining = size
    while remaining:
        used = min(remaining, len(block))
        digest.update(memoryview(block)[:used])
        remaining -= used
    return digest.hexdigest()


def _integer(value: object, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError("invalid integer in stream measurement")
    return value


def evaluate_run(
    measured: dict[str, Any], server: dict[str, Any], size: int, expected: str
) -> dict[str, Any]:
    """Keep actual values and apply the byte/RSS limits without rounding tolerance."""
    baseline = _integer(measured["baseline_rss_bytes"], minimum=1)
    peak = _integer(measured["peak_rss_bytes"], minimum=baseline)
    extra = _integer(measured["extra_rss_bytes"])
    if extra != peak - baseline:
        raise ValueError("reported extra RSS differs from the process high-water difference")
    unit = measured["rss_native_unit"]
    if unit not in {"bytes", "KiB"}:
        raise ValueError("unknown native RSS unit")
    for name in ("baseline", "peak"):
        native = measured[name + "_rss_native"]
        if (
            type(native) not in (int, float)
            or not math.isfinite(native)
            or native <= 0
            or native * (1024 if unit == "KiB" else 1) != measured[name + "_rss_bytes"]
        ):
            raise ValueError("native RSS and byte measurements differ")
    elapsed = measured["elapsed_seconds"]
    if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed <= 0:
        raise ValueError("elapsed stream time must be finite and positive")
    received = _integer(measured["received_bytes"])
    largest = _integer(measured["max_chunk_bytes"], minimum=1)
    _integer(measured["chunk_count"], minimum=1)
    requests = server["requests"]
    if not isinstance(requests, list):
        raise ValueError("server request telemetry must be a bounded list")
    request_count = _integer(server["request_count"])
    connections = _integer(server["connection_count"])
    active = _integer(server["peak_active_requests"])
    # A single measured stream follows a fixed 32KiB TLS warmup in the same session.
    expected_requests = [
        {"size_bytes": CHUNK_BYTES, "sent_bytes": CHUNK_BYTES, "completed": True},
        {"size_bytes": size, "sent_bytes": size, "completed": True},
    ]
    valid = (
        measured["size_bytes"] == size
        and type(measured["size_bytes"]) is int
        and measured["stream_count"] == 1
        and type(measured["stream_count"]) is int
        and measured["warmup_requests"] == 1
        and type(measured["warmup_requests"]) is int
        and measured["measurement_requests"] == 1
        and type(measured["measurement_requests"]) is int
        and received == size
        and measured["received_sha256"] == expected
        and extra <= RSS_LIMIT_BYTES
        and largest <= CHUNK_BYTES
        and request_count == len(requests) == 2
        and requests == expected_requests
        and all(
            type(item["size_bytes"]) is int
            and type(item["sent_bytes"]) is int
            and item["completed"] is True
            for item in requests
        )
        and 1 <= connections <= 2
        and 1 <= active <= 2
        and measured["runtime"]["isolated"] is True
        and measured["runtime"]["installed_source_matches"] is True
    )
    return {
        **measured,
        "size_mib": size // (1024 * 1024),
        "expected_bytes": size,
        "expected_sha256": expected,
        "request_count": request_count,
        "connection_count": connections,
        "peak_active_requests": active,
        "server": server,
        "passed": bool(valid),
    }


def measure_one(
    project: Path,
    python: Path,
    work: Path,
    manifest: Path,
    certificates: tuple[Path, Path],
    size: int,
) -> dict[str, Any]:
    """The development parent and synthetic TLS server are never part of client RSS."""
    work.mkdir()
    helper = project / "tests" / "fixtures" / "stream_budget.py"
    cert, key = certificates
    ready = work / "ready.json"
    command = [
        sys.executable,
        "-I",
        str(helper),
        "server",
        "--ca",
        str(cert),
        "--key",
        str(key),
        "--ready",
        str(ready),
    ]
    with subprocess.Popen(
        command,
        cwd=work,
        env=environment(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as server:
        try:
            until = time.monotonic() + 10
            while not ready.is_file():
                exit_code = server.poll()
                if exit_code is not None:
                    raise ValueError(
                        f"synthetic TLS server exited before readiness (exit={exit_code}); "
                        f"diagnostics retained at {work}"
                    )
                if time.monotonic() >= until:
                    raise ValueError(
                        "synthetic TLS server readiness timed out after 10 seconds "
                        f"while process was running; diagnostics retained at {work}"
                    )
                time.sleep(0.02)
            address = json.loads(ready.read_text(encoding="utf-8"))
            try:
                result = subprocess.run(
                    [
                        str(python),
                        "-I",
                        str(helper),
                        "client",
                        "--ca",
                        str(cert),
                        "--port",
                        str(address["port"]),
                        "--size",
                        str(size),
                        "--manifest",
                        str(manifest),
                        "--prefix",
                        str(python.parent.parent),
                        "--total-seconds",
                        str(TOTAL_SECONDS),
                    ],
                    cwd=work,
                    env=environment(),
                    capture_output=True,
                    text=True,
                    timeout=2 * TOTAL_SECONDS + 30,
                )
            except subprocess.TimeoutExpired as error:
                for name, partial in (
                    ("client-stdout.txt", error.stdout),
                    ("client-stderr.txt", error.stderr),
                ):
                    text = (
                        partial.decode("utf-8", errors="replace")
                        if isinstance(partial, bytes)
                        else partial or ""
                    )
                    try:
                        (work / name).write_text(text, encoding="utf-8")
                    except OSError:
                        # Retaining diagnostics must not replace the timeout.
                        pass
                raise
            # Preserve subprocess failures and malformed records in the fresh workspace.
            (work / "client-stdout.txt").write_text(result.stdout, encoding="utf-8")
            (work / "client-stderr.txt").write_text(result.stderr, encoding="utf-8")
            if result.returncode != 0 or result.stderr:
                raise ValueError(
                    "installed stream worker failed; retained workspace has diagnostics"
                )
            measured = json.loads(result.stdout)
        finally:
            server.terminate()
            try:
                stdout, stderr = server.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                stdout, stderr = server.communicate(timeout=10)
            (work / "server-stdout.txt").write_text(stdout, encoding="utf-8")
            (work / "server-stderr.txt").write_text(stderr, encoding="utf-8")
        if server.returncode != 0 or stderr:
            raise ValueError("synthetic TLS server failed; retained workspace has diagnostics")
    return evaluate_run(measured, json.loads(stdout), size, expected_sha256(size))


def check(
    project: Path,
    python: Path,
    workspace: Path,
    output: Path,
    *,
    cpu: str,
    disk: str,
) -> int:
    output = new_path(output)
    workspace = new_path(workspace)
    project = project.resolve(strict=True)
    # Do not resolve the venv interpreter symlink to its system Python executable.
    python = python.absolute()
    if not python.is_file() or python.parent.name not in {"bin", "Scripts"}:
        raise ValueError("--python must select an installed runtime environment interpreter")
    before = source(project)
    workspace.mkdir(mode=0o700)
    manifest = workspace / "source-manifest.json"
    manifest.write_text(
        json.dumps(
            {"source_sha256": before["source_sha256"], "locked_runtime": locked_runtime(project)}
        ),
        encoding="utf-8",
    )
    certificate = runpy.run_path(str(project / "tests/fixtures/http_server.py"))["certificate"]
    certificates = cast(tuple[Path, Path], certificate(workspace / "certificates"))
    runs = []
    stable = True
    for size_mib in SIZES_MIB:
        run_work = workspace / str(size_mib)
        size = size_mib * 1024 * 1024
        try:
            measured = measure_one(project, python, run_work, manifest, certificates, size)
            # Keep each complete result before another worker can fail. This is
            # an individual observation, never a substitute for full acceptance.
            with (run_work / "measurement.json").open("x", encoding="utf-8") as target:
                json.dump(measured, target, ensure_ascii=False, allow_nan=False, indent=2)
                target.write("\n")
        except Exception as error:
            if run_work.is_dir() and not run_work.is_symlink():
                diagnostics = [
                    name
                    for name in (
                        "client-stdout.txt",
                        "client-stderr.txt",
                        "server-stdout.txt",
                        "server-stderr.txt",
                    )
                    if (run_work / name).is_file() and not (run_work / name).is_symlink()
                ]
                try:
                    with (run_work / "failure.json").open("x", encoding="utf-8") as target:
                        json.dump(
                            {
                                "error_type": type(error).__name__,
                                "size_bytes": size,
                                "diagnostics": diagnostics,
                            },
                            target,
                        )
                        target.write("\n")
                except OSError:
                    # A diagnostic-write failure must not mask the original
                    # measurement failure or overwrite another writer's file.
                    pass
            raise
        runs.append(measured)
        stable = source(project) == before and stable
    after = source(project)
    stable = stable and before == after
    runtime = runs[0]["runtime"]
    installed_matches = all(run["runtime"]["installed_source_matches"] is True for run in runs)
    runtime_consistent = all(
        runtime_identity(run["runtime"]) == runtime_identity(runtime) for run in runs
    )
    value = {
        "schema_version": 1,
        "report_kind": "raw_stream_budget_v1",
        "source_commit": before["commit"],
        "environment": {
            name: runtime[name]
            for name in ("os", "machine", "python", "python_executable", "sqlite", "packages")
        }
        | {"cpu": cpu, "disk": disk},
        "provenance": {
            "source_before": before,
            "source_after": after,
            "source_unchanged_during_measurement": stable,
            "installed_source_matches": installed_matches,
        },
        "method": {
            "rss_method": "resource.getrusage(RUSAGE_SELF).ru_maxrss",
            "rss_baseline": "fresh client process high-water maxRSS after imports, source "
            "verification and fixed 32KiB TLS warmup; not instantaneous RSS",
            "rss_native_unit": runs[0]["rss_native_unit"],
            "server_process_excluded": True,
            "consumer": "incremental_sha256_and_count",
            "server_generation": "repeating_0_to_255_bounded_32768_bytes",
            "client_process_per_size": True,
            "streams_per_client": 1,
            "consumer_queue_chunks": 0,
            "backpressure": "consumer awaits each next chunk; no producer task or body queue",
            "phase_timeout_seconds": 5,
            "pool_timeout_seconds": 1,
            "limit": "synthetic raw byte transport; no dataset endpoint or hard physical deadline",
        },
        "limits": {
            "extra_rss_bytes": RSS_LIMIT_BYTES,
            "chunk_bytes": CHUNK_BYTES,
            "connections": 2,
            "total_deadline_seconds": TOTAL_SECONDS,
        },
        "runs": runs,
        "size_growth_diagnostic": {
            "size_bytes": [run["size_bytes"] for run in runs],
            "extra_rss_bytes": [run["extra_rss_bytes"] for run in runs],
        },
        "passed": stable
        and installed_matches
        and runtime_consistent
        and all(run["passed"] is True for run in runs),
    }
    # Exclusive creation closes the race with another writer and never follows a symlink.
    with new_path(output).open("x", encoding="utf-8") as target:
        json.dump(value, target, ensure_ascii=False, allow_nan=False, indent=2)
        target.write("\n")
    return 0 if value["passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=ROOT)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cpu-label", default="unknown")
    parser.add_argument("--disk-type", default="unknown")
    args = parser.parse_args()
    try:
        return check(
            args.project,
            args.python,
            args.workspace,
            args.output,
            cpu=args.cpu_label,
            disk=args.disk_type,
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
