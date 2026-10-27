"""Measure real installed commands; each sample starts a distinct process."""

from __future__ import annotations

import argparse
import json
import math
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path


def measure(command: list[str]) -> float:
    started = time.perf_counter()
    subprocess.run(
        command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=10
    )
    return (time.perf_counter() - started) * 1000


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", type=Path, required=True)
    parser.add_argument("--profile", type=Path, default=Path("examples/profile.toml"))
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
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
    measurements: dict[str, object] = {}
    passed = True
    for name, (invocation, target) in cases.items():
        first = measure(invocation)
        for _ in range(3):
            measure(invocation)
        samples = [measure(invocation) for _ in range(args.samples)]
        p95 = sorted(samples)[math.ceil(len(samples) * 0.95) - 1]
        passed = passed and p95 <= target
        measurements[name] = {
            "first_process_ms": round(first, 3),
            "warm_median_ms": round(statistics.median(samples), 3),
            "warm_p95_ms": round(p95, 3),
            "warm_samples_ms": [round(sample, 3) for sample in samples],
            "target_ms": target,
            "passed": p95 <= target,
        }
    report = {
        "schema_version": 1,
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "profile_bytes": profile.stat().st_size,
        "samples_per_command": args.samples,
        "installation": "installed console script; specify environment in accompanying report",
        "cold_method": "first command process; OS/disk caches uncontrolled; not a cold boot",
        "measurements": measurements,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
