"""Measure real installed commands; each sample starts a distinct process."""

from __future__ import annotations

import argparse
import json
import math
import platform
import sqlite3
import statistics
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path


def measure(command: list[str], *, cache_hit: bool = False) -> float:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE if cache_hit else subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    duration = (time.perf_counter() - started) * 1000
    if cache_hit:
        records = json.loads(completed.stdout)["data"]["records"]
        if not records or not all(r["hit"] is True and r["freshness"] == "fresh" for r in records):
            raise RuntimeError("cache benchmark requires fresh hits, not misses")
    return duration


def cpu_label() -> str:
    if sys.platform == "linux":
        try:
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.startswith("model name") and ":" in line:
                    return line.split(":", 1)[1].strip() or "unknown"
        except OSError:
            pass
    return platform.processor() or "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", type=Path, required=True)
    parser.add_argument("--profile", type=Path, default=Path("examples/profile.toml"))
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-state", type=Path, help="Prepared synthetic cache dataset")
    parser.add_argument("--disk-type", default="unknown")
    parser.add_argument("--cpu-label", default=cpu_label())
    parser.add_argument("--installation-label", default="unknown; specify measured environment")
    args = parser.parse_args()
    if args.samples < 30:
        parser.error("at least 30 samples are required")
    command = str(args.command.resolve())
    profile = args.profile.resolve()
    cases = {
        "help": ([command, "--help"], 500),
        "version": ([command, "--version"], 500),
        "context": (
            [command, "context", "show", "--config", str(profile), "--output", "json"],
            200,
        ),
    }
    cache_dataset: dict[str, object] | None = None
    if args.cache_state is not None:
        database = args.cache_state.resolve() / "state.sqlite3"
        with closing(
            sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
        ) as reader:
            count, total, largest = reader.execute(
                "SELECT count(*),sum(length(payload)),max(length(payload)) FROM capability_cache"
            ).fetchone()
        cache_dataset = {"records": count, "payload_bytes": total, "largest_record_bytes": largest}
        cases["cache"] = (
            [
                command,
                "capabilities",
                "--task",
                "llm.train",
                "--cached",
                "--config",
                str(profile),
                "--state-dir",
                str(args.cache_state.resolve()),
                "--output",
                "json",
            ],
            200,
        )
    measurements: dict[str, object] = {}
    passed = True
    for name, (invocation, target) in cases.items():
        first = measure(invocation, cache_hit=name == "cache")
        for _ in range(3):
            measure(invocation, cache_hit=name == "cache")
        samples = [measure(invocation, cache_hit=name == "cache") for _ in range(args.samples)]
        p95 = sorted(samples)[math.ceil(len(samples) * 0.95) - 1]
        passed = passed and p95 <= target
        measurements[name] = {
            "first_process_ms": round(first, 3),
            "warm_median_ms": round(statistics.median(samples), 3),
            "warm_p95_ms": round(p95, 3),
            "warm_samples_ms": [round(sample, 3) for sample in samples],
            "target_ms": target,
            "passed": p95 <= target,
            "fresh_cache_hit_verified": name == "cache",
        }
    report = {
        "schema_version": 1,
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu": args.cpu_label,
        "disk_type": args.disk_type,
        "cache_dataset": cache_dataset,
        "profile_bytes": profile.stat().st_size,
        "samples_per_command": args.samples,
        "installation": args.installation_label,
        "cold_method": "first command process; OS/disk caches uncontrolled; not a cold boot",
        "measurements": measurements,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
