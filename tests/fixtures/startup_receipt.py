"""Handwritten startup proof vector; never a performance measurement."""

import copy


def receipt():
    source = {
        "commit": "a" * 40,
        "source_sha256": {"src/yorunge/__init__.py": "b" * 64, "examples/profile.toml": "c" * 64},
    }
    installed = {
        "python": "3.11.18 (fixture)",
        "executable": "/candidate/env/bin/python",
        "prefix": "/candidate/env",
        "platform": "macOS-27.0.1-arm64-arm-64bit",
        "machine": "arm64",
        "sqlite": "3.54.1",
        "packages": {"yorunge": "0.1.0.dev0"},
        "product_origin": "/candidate/env/lib/yorunge",
        "product_version": "0.1.0.dev0",
        "console": "/candidate/env/bin/yorunge",
        "console_sha256": "d" * 64,
        "installed_source_sha256": {"yorunge/__init__.py": "b" * 64},
    }
    fixture = {
        "state": "/candidate/state",
        "profile": "/checkout/examples/profile.toml",
        "profile_sha256": "c" * 64,
        "profile_bytes": 270,
        "records": 1024,
        "payload_bytes": 2500000,
        "largest_record_bytes": 2500,
        "cache_sha256": "e" * 64,
        "expiries_sha256": "f" * 64,
    }
    candidate = {
        "source": source,
        "installed": installed,
        "runtime_data_sha256": {},
        "fixture": fixture,
        "wheel_path": "/candidate/dist/yorunge.whl",
        "wheel_sha256": "1" * 64,
    }
    baseline = copy.deepcopy(candidate)
    for key in ("prefix", "executable", "product_origin", "console"):
        baseline["installed"][key] = baseline["installed"][key].replace("candidate", "baseline")
    baseline["fixture"]["state"] = "/baseline/state"
    baseline["wheel_path"] = "/baseline/dist/yorunge.whl"
    rows, pairs, checks = {}, {}, {}
    for name, target in (("help", 500), ("version", 500), ("context", 200), ("cache", 200)):
        rows[name] = {
            "first_process_ms": 20.0,
            "warm_median_ms": 10.0,
            "warm_p95_ms": 10.0,
            "warm_samples_ms": [10.0] * 30,
            "warm_child_user_cpu_ms": [5.0] * 30,
            "warm_child_system_cpu_ms": [1.0] * 30,
            "warm_non_cpu_estimate_ms": [4.0] * 30,
            "target_ms": target,
            "passed": True,
            "fresh_cache_hit_verified": name == "cache",
        }
        pairs[name] = {
            "paired_wall_ratios": [1.0] * 30,
            "median_paired_wall_ratio": 1.0,
            "candidate_faster_pairs": 0,
            "pairs": 30,
        }
        checks[name] = {
            "typed_stdout_verified": True,
            "expected_version": "0.1.0.dev0",
            "expected_python": "/candidate/env/bin/python",
            "verified_processes": 34,
            "stdout_sha256": ["2" * 64] * 34,
            "wall_ms": [20.0, 11.0, 12.0, 13.0] + [10.0] * 30,
        }
    raw = {
        "schema_version": 2,
        "python": installed["python"],
        "platform": installed["platform"],
        "machine": "arm64",
        "cpu": "Apple M5 Max",
        "cpu_affinity": None,
        "runner_image": {"ImageOS": None, "ImageVersion": None},
        "disk_type": "internal SSD/APFS",
        "cache_dataset": {
            key: fixture[key] for key in ("records", "payload_bytes", "largest_record_bytes")
        },
        "profile_bytes": 270,
        "profile_sha256": "c" * 64,
        "samples_per_command": 30,
        "installation": "isolated runtime-only wheel; frozen uv.lock; fixed hash seed",
        "cold_method": "first command process; OS/disk caches uncontrolled; not a cold boot",
        "cpu_method": "RUSAGE_CHILDREN deltas for sequential waited children; wall minus child CPU "
        "includes parent overhead and wait; does not identify I/O or scheduler cause",
        "measurements": rows,
        "comparison": {
            "method": "alternating AB/BA process pairs on the same host; "
            "three warmups; all samples retained",
            "baseline_cache_dataset": {
                key: fixture[key] for key in ("records", "payload_bytes", "largest_record_bytes")
            },
            "baseline_measurements": copy.deepcopy(rows),
            "paired_comparisons": pairs,
            "acceptance": "candidate absolute budgets only; "
            "baseline and paired ratios are diagnostic",
        },
    }
    baseline_checks = copy.deepcopy(checks)
    for item in baseline_checks.values():
        item["expected_python"] = "/baseline/env/bin/python"
    before = {"candidate": candidate, "baseline": baseline}
    return {
        "schema_version": 1,
        "report_kind": "startup_evidence_v1",
        "source_commit": "a" * 40,
        "measurement": raw,
        "snapshots": {"before": before, "after": copy.deepcopy(before)},
        "output_checks": {"candidate": checks, "baseline": baseline_checks},
        "measurement_exit": 0,
        "passed": True,
    }
