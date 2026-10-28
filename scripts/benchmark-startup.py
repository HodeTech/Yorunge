"""Measure real installed commands; each sample starts a distinct process."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sqlite3
import statistics
import subprocess
import sys
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

resource_module: ModuleType | None
try:
    import resource
except ImportError:
    resource_module = None
else:
    resource_module = resource


@dataclass(frozen=True)
class Sample:
    wall_ms: float
    user_ms: float | None
    system_ms: float | None


def child_cpu() -> tuple[float, float] | None:
    if resource_module is None:
        return None
    try:
        usage = resource_module.getrusage(resource_module.RUSAGE_CHILDREN)
        return float(usage.ru_utime) * 1000, float(usage.ru_stime) * 1000
    except OSError:
        return None


def measure(command: list[str], *, cache_hit: bool = False) -> Sample:
    before = child_cpu()
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE if cache_hit else subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    duration = (time.perf_counter() - started) * 1000
    after = child_cpu()
    if cache_hit:
        records = json.loads(completed.stdout)["data"]["records"]
        if not records or not all(r["hit"] is True and r["freshness"] == "fresh" for r in records):
            raise RuntimeError("cache benchmark requires fresh hits, not misses")
    return Sample(
        duration,
        after[0] - before[0] if after is not None and before is not None else None,
        after[1] - before[1] if after is not None and before is not None else None,
    )


def cpu_label() -> str:
    if sys.platform == "linux":
        try:
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.startswith("model name") and ":" in line:
                    return line.split(":", 1)[1].strip() or "unknown"
        except OSError:
            pass
    return platform.processor() or "unknown"


def cpu_affinity() -> list[int] | None:
    try:
        return sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None
    except OSError:
        return None


def dataset(state: Path) -> dict[str, int]:
    database = state.resolve() / "state.sqlite3"
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)) as reader:
        count, total, largest = reader.execute(
            "SELECT count(*),sum(length(CAST(payload AS BLOB))),"
            "max(length(CAST(payload AS BLOB))) FROM capability_cache"
        ).fetchone()
    if count != 1024 or not all(type(value) is int and value > 0 for value in (total, largest)):
        raise ValueError("startup acceptance requires 1024 nonempty synthetic cache records")
    return {"records": count, "payload_bytes": total, "largest_record_bytes": largest}


def cases(command: Path, profile: Path, state: Path) -> dict[str, tuple[list[str], int]]:
    executable = str(command.resolve())
    return {
        "help": ([executable, "--help"], 500),
        "version": ([executable, "--version"], 500),
        "context": (
            [executable, "context", "show", "--config", str(profile.resolve()), "--output", "json"],
            200,
        ),
        "cache": (
            [
                executable,
                "capabilities",
                "--task",
                "llm.train",
                "--cached",
                "--config",
                str(profile.resolve()),
                "--state-dir",
                str(state.resolve()),
                "--output",
                "json",
            ],
            200,
        ),
    }


def summary(
    first: Sample, samples: list[Sample], target: int, *, cached: bool
) -> dict[str, object]:
    walls = [sample.wall_ms for sample in samples]
    if any(not math.isfinite(value) or value <= 0 for value in (first.wall_ms, *walls)):
        raise ValueError("process wall measurements must be positive and finite")
    p95 = sorted(walls)[math.ceil(len(walls) * 0.95) - 1]
    return {
        "first_process_ms": round(first.wall_ms, 3),
        "warm_median_ms": round(statistics.median(walls), 3),
        "warm_p95_ms": p95,
        "warm_samples_ms": walls,
        "warm_child_user_cpu_ms": [
            round(sample.user_ms, 3) if sample.user_ms is not None else None for sample in samples
        ],
        "warm_child_system_cpu_ms": [
            round(sample.system_ms, 3) if sample.system_ms is not None else None
            for sample in samples
        ],
        "warm_non_cpu_estimate_ms": [
            round(sample.wall_ms - sample.user_ms - sample.system_ms, 3)
            if sample.user_ms is not None and sample.system_ms is not None
            else None
            for sample in samples
        ],
        "target_ms": target,
        "passed": p95 <= target,
        "fresh_cache_hit_verified": cached,
    }


def paired_samples(
    command: list[str], baseline: list[str] | None, count: int, *, cached: bool
) -> tuple[Sample, list[Sample], Sample | None, list[Sample]]:
    observed: list[Sample] = []
    reference: list[Sample] = []
    first: Sample | None = None
    baseline_first: Sample | None = None
    # Each pair alternates AB/BA; no concurrent child and no discarded slow sample.
    for index in range(count + 4):
        before = measure(baseline, cache_hit=cached) if baseline and index % 2 == 0 else None
        current = measure(command, cache_hit=cached)
        previous = before or (measure(baseline, cache_hit=cached) if baseline else None)
        if index == 0:
            first, baseline_first = current, previous
        elif index >= 4:
            observed.append(current)
            if previous is not None:
                reference.append(previous)
    if first is None:
        raise ValueError("missing first process measurement")
    return first, observed, baseline_first, reference


def measure_cases(
    current_cases: dict[str, tuple[list[str], int]],
    baseline_cases: dict[str, tuple[list[str], int]] | None,
    count: int,
) -> tuple[dict[str, object], dict[str, object], dict[str, object], bool]:
    measurements: dict[str, object] = {}
    baseline_measurements: dict[str, object] = {}
    comparisons: dict[str, object] = {}
    passed = True
    for name, (invocation, target) in current_cases.items():
        reference = baseline_cases[name][0] if baseline_cases else None
        first, samples, old_first, old_samples = paired_samples(
            invocation, reference, count, cached=name == "cache"
        )
        result = summary(first, samples, target, cached=name == "cache")
        measurements[name] = result
        passed = passed and result["passed"] is True
        if old_first is not None:
            old_result = summary(old_first, old_samples, target, cached=name == "cache")
            baseline_measurements[name] = old_result
            ratios = [
                new.wall_ms / old.wall_ms for new, old in zip(samples, old_samples, strict=True)
            ]
            comparisons[name] = {
                "paired_wall_ratios": [round(ratio, 6) for ratio in ratios],
                "median_paired_wall_ratio": round(statistics.median(ratios), 6),
                "candidate_faster_pairs": sum(ratio < 1 for ratio in ratios),
                "pairs": len(ratios),
            }
    return measurements, baseline_measurements, comparisons, passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", type=Path, required=True)
    parser.add_argument("--profile", type=Path, default=Path("examples/profile.toml"))
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--cache-state", type=Path, required=True, help="Prepared synthetic cache dataset"
    )
    parser.add_argument("--baseline-command", type=Path)
    parser.add_argument("--baseline-profile", type=Path)
    parser.add_argument("--baseline-cache-state", type=Path)
    parser.add_argument("--disk-type", default="unknown")
    parser.add_argument("--cpu-label", default=cpu_label())
    parser.add_argument("--installation-label", default="unknown; specify measured environment")
    args = parser.parse_args()
    if args.samples < 30:
        parser.error("at least 30 samples are required")
    baseline_args = (args.baseline_command, args.baseline_profile, args.baseline_cache_state)
    if any(value is not None for value in baseline_args) and not all(
        value is not None for value in baseline_args
    ):
        parser.error("all three --baseline options must be supplied together")
    profile = args.profile.resolve()
    head_dataset = dataset(args.cache_state)
    current_cases = cases(args.command, profile, args.cache_state)
    baseline_cases = None
    baseline_dataset = None
    if args.baseline_command is not None:
        if args.baseline_cache_state.resolve() == args.cache_state.resolve():
            parser.error("baseline and candidate require separate synthetic state directories")
        baseline_dataset = dataset(args.baseline_cache_state)
        if (
            baseline_dataset != head_dataset
            or args.baseline_profile.read_bytes() != profile.read_bytes()
        ):
            parser.error(
                "baseline and candidate must use equivalent datasets and identical profiles"
            )
        baseline_cases = cases(
            args.baseline_command, args.baseline_profile, args.baseline_cache_state
        )
    measurements, baseline_measurements, comparisons, passed = measure_cases(
        current_cases, baseline_cases, args.samples
    )
    report = {
        "schema_version": 2,
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu": args.cpu_label,
        "cpu_affinity": cpu_affinity(),
        "runner_image": {key: os.environ.get(key) for key in ("ImageOS", "ImageVersion")},
        "disk_type": args.disk_type,
        "cache_dataset": head_dataset,
        "profile_bytes": profile.stat().st_size,
        "profile_sha256": hashlib.sha256(profile.read_bytes()).hexdigest(),
        "samples_per_command": args.samples,
        "installation": args.installation_label,
        "cold_method": "first command process; OS/disk caches uncontrolled; not a cold boot",
        "cpu_method": "RUSAGE_CHILDREN deltas for sequential waited children; wall minus child CPU "
        "includes parent overhead and wait; does not identify I/O or scheduler cause",
        "measurements": measurements,
        "comparison": {
            "method": "alternating AB/BA process pairs on the same host; "
            "three warmups; all samples retained",
            "baseline_cache_dataset": baseline_dataset,
            "baseline_measurements": baseline_measurements,
            "paired_comparisons": comparisons,
            "acceptance": "candidate absolute budgets only; "
            "baseline and paired ratios are diagnostic",
        }
        if baseline_cases
        else None,
    }
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
