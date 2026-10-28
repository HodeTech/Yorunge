"""Measure real descriptor hash allocation/RSS in separate synthetic worker processes."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import resource
import subprocess
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

from yorunge.adapters.capability_cache import SystemClock
from yorunge.adapters.input_files import BLOCK_BYTES, DescriptorInputs
from yorunge.application.execution import ExecutionBudget


def peak_rss() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def worker(size_mib: int) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="yorunge-input-measure-") as directory:
        root = Path(directory).resolve()
        path = root / "zeros.bin"
        size = size_mib * BLOCK_BYTES
        with path.open("wb") as stream:
            stream.truncate(size)
        baseline = peak_rss()
        started = time.monotonic()
        tracemalloc.start()
        try:
            _, inputs = DescriptorInputs().bind(
                root, (("fixture", "zeros.bin"),), ExecutionBudget(SystemClock(), started)
            )
            _, python_peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        elapsed, rss = time.monotonic() - started, peak_rss()
        expected = hashlib.sha256()
        block = bytes(BLOCK_BYTES)
        for _ in range(size_mib):
            expected.update(block)
        complete = inputs[0].size == size and inputs[0].digest == expected.hexdigest()
        extra = max(0, rss - baseline)
        return {
            "size_mib": size_mib,
            "elapsed_ms": round(elapsed * 1000, 3),
            "python_peak_bytes": python_peak,
            "baseline_peak_rss_bytes": baseline,
            "peak_rss_bytes": rss,
            "additional_peak_rss_bytes": extra,
            "complete_hash_verified": complete,
            "passed": complete and python_peak < 8 * BLOCK_BYTES and extra <= 64 * BLOCK_BYTES,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker-mib", type=int, choices=(16, 256, 1024))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cpu-label", default="unknown")
    parser.add_argument("--disk-type", default="unknown")
    parser.add_argument("--installation-label", default="unknown")
    args = parser.parse_args()
    if args.worker_mib is not None:
        print(json.dumps(worker(args.worker_mib)))
        return 0
    if args.output is None:
        parser.error("--output is required")
    rows = []
    for size in (16, 256, 1024):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--worker-mib", str(size)],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        rows.append(json.loads(result.stdout))
    peaks = [row["python_peak_bytes"] for row in rows]
    passed = all(row["passed"] for row in rows) and max(peaks) - min(peaks) < 2 * BLOCK_BYTES
    report = {
        "schema_version": 1,
        "platform": platform.platform(),
        "python": sys.version,
        "block_bytes": BLOCK_BYTES,
        "installation": args.installation_label,
        "cpu": args.cpu_label,
        "disk_type": args.disk_type,
        "fixture": (
            "separate sparse zero files; complete content read and independent expected digest"
        ),
        "rss_method": "ru_maxrss before/after bind in each new process; delta of process maxima",
        "measurements": rows,
        "passed": passed,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
