"""Measure installed inspect/verify with independent byte and metadata fixtures.

All 24 workers run serially: three fresh processes per action and each of
16/256/1024 MiB, plus 4096 files/4096 directories. Never includes controller RSS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import runpy
import subprocess
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
STREAM = runpy.run_path(str(ROOT / "scripts/benchmark-stream.py"))
SOURCES = runpy.run_path(str(ROOT / "scripts/startup_evidence.py"))
CHECKS = runpy.run_path(str(ROOT / "scripts/research_evidence.py"))
SIZES = (16, 256, 1024)
LABELS = ("16", "256", "1024", "capacity")
RSS_LIMIT = 67_108_864
GROWTH_LIMIT = 8_388_608
SECONDS_LIMIT = 30
SAMPLES = 3
MEASUREMENT_FIELDS = (
    "action manifest_digest file_count total_bytes result_valid elapsed_seconds "
    "baseline_rss_native baseline_rss_bytes baseline_rss_method "
    "pretransfer_peak_rss_native pretransfer_peak_rss_bytes peak_rss_native peak_rss_bytes "
    "rss_native_unit extra_rss_lower_bound_bytes extra_rss_upper_bound_bytes runtime "
    "runtime_data_sha256"
)


def closed(value: object, fields: str) -> dict[str, Any]:
    return cast(dict[str, Any], CHECKS["closed"](value, fields, "dataset measurement"))


def expected_manifest(label: str) -> dict[str, Any]:
    files: list[dict[str, Any]]
    if label == "capacity":
        names = [f"d{index:04}/data.bin" for index in range(4095)] + ["root.bin"]
        digest = hashlib.sha256(b"x").hexdigest()
        files = [{"path": name, "size": 1, "sha256": digest} for name in names]
    elif label in LABELS[:-1]:
        size = int(label) * 1024 * 1024
        files = [{"path": "data.bin", "size": size, "sha256": CHECKS["STREAM_HASHES"][int(label)]}]
    else:
        raise ValueError("unknown dataset fixture")
    body = {
        "schema_version": 1,
        "policy_version": 1,
        "kind": "dataset_manifest",
        "hash_algorithm": "sha256",
        "files": files,
        "file_count": len(files),
        "total_bytes": sum(item["size"] for item in files),
    }
    encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {**body, "digest": hashlib.sha256(encoded.encode("utf-8")).hexdigest()}


def fixture_summary(expected: dict[str, Any], label: str) -> dict[str, Any]:
    return {name: expected[name] for name in ("file_count", "total_bytes", "digest")} | {
        "directory_count": 4096 if label == "capacity" else 1
    }


def prepare_fixture(root: Path, expected: dict[str, Any], label: str) -> None:
    root.mkdir()
    if label == "capacity":
        for file in expected["files"]:
            target = root / file["path"]
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(b"x")
    else:
        # Expected hashes are the existing fixed independent raw-byte vectors.
        block = bytes(range(256)) * 128
        with (root / "data.bin").open("xb") as stream:
            for _ in range(expected["total_bytes"] // len(block)):
                stream.write(block)


def evaluate_run(
    measured: dict[str, Any],
    expected: dict[str, Any],
    source: dict[str, Any],
    locked: dict[str, str],
) -> bool:
    runtime = CHECKS["stream_runtime"](measured["runtime"], CHECKS["python_hashes"](source))
    extra = STREAM["rss_interval"](measured)
    elapsed = CHECKS["number"](measured["elapsed_seconds"])
    if elapsed <= 0:
        raise ValueError("dataset elapsed time must be positive")
    for field in ("file_count", "total_bytes"):
        CHECKS["integer"](measured[field])
    if type(measured["result_valid"]) is not bool:
        raise ValueError("dataset result validity must be boolean")
    expected_data = {
        name: digest
        for name, digest in source["source_sha256"].items()
        if name == "src/yorunge/py.typed"
    }
    actual_data = CHECKS["hash_map"](measured["runtime_data_sha256"])
    if not expected_data or actual_data != expected_data:
        raise ValueError("dataset installed runtime data differs from measured source")
    return bool(
        measured["manifest_digest"] == expected["digest"]
        and measured["file_count"] == expected["file_count"]
        and measured["total_bytes"] == expected["total_bytes"]
        and measured["result_valid"]
        and elapsed <= SECONDS_LIMIT
        and extra <= RSS_LIMIT
        and runtime["installed_source_matches"] is True
        and runtime["isolated"] is True
        and runtime["packages"] == locked
    )


def growth_acceptance(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if len(runs) < 3 or len({run["label"] for run in runs}) < 3:
        raise ValueError("dataset growth requires all three distinct sizes")
    for run in runs:
        low, high = run["extra_rss_lower_bound_bytes"], run["extra_rss_upper_bound_bytes"]
        CHECKS["integer"](low)
        CHECKS["integer"](high)
        if low > high:
            raise ValueError("invalid dataset RSS interval")
    span = max(
        0,
        max(
            high["extra_rss_upper_bound_bytes"] - low["extra_rss_lower_bound_bytes"]
            for high in runs
            for low in runs
            if high["label"] != low["label"]
        ),
    )
    return {"span_upper_bound_bytes": span, "passed": span <= GROWTH_LIMIT}


def validated_fixtures(value: object) -> dict[str, Any]:
    fixtures = closed(value, "16 256 1024 capacity")
    expected = {label: expected_manifest(label) for label in LABELS}
    for label in LABELS:
        fixture = closed(fixtures[label], "file_count total_bytes digest directory_count")
        for field in ("file_count", "total_bytes", "directory_count"):
            CHECKS["integer"](fixture[field])
        CHECKS["pattern_value"](fixture["digest"], CHECKS["SHA256"])
        if fixtures[label] != fixture_summary(expected[label], label):
            raise ValueError("dataset fixture differs from its independent oracle")
    return expected


def validated_runs(
    value: object, expected: dict[str, Any], before: dict[str, Any], locked: dict[str, str]
) -> list[dict[str, Any]]:
    runs = value
    if not isinstance(runs, list) or len(runs) != 24:
        raise ValueError("dataset report requires all 24 process measurements")
    seen, pids = set(), set()
    for raw in runs:
        if not isinstance(raw, dict) or not isinstance(raw.get("runtime"), dict):
            raise ValueError("dataset measurement requires an object and runtime")
        fields = MEASUREMENT_FIELDS + " label sample passed"
        if CHECKS["text_value"](raw["runtime"].get("os")).startswith("Linux"):
            fields += " baseline_rss_pages rss_page_bytes"
        row = closed(raw, fields)
        key = (row["action"], row["label"], row["sample"])
        if row["action"] not in ("inspect", "verify") or row["label"] not in LABELS:
            raise ValueError("unknown dataset measurement case")
        if CHECKS["integer"](row["sample"], minimum=1) > SAMPLES:
            raise ValueError("dataset sample exceeds the fixed process count")
        valid = evaluate_run(row, expected[row["label"]], before, locked)
        if key in seen or row["runtime"]["pid"] in pids:
            raise ValueError("dataset sample or worker process repeated")
        seen.add(key)
        pids.add(row["runtime"]["pid"])
        CHECKS["flag"](row["passed"], valid)
    return runs


def validate_growth(value: object, growth: dict[str, Any]) -> None:
    reported_growth = closed(value, "inspect verify")
    for action, computed in growth.items():
        reported = closed(reported_growth[action], "span_upper_bound_bytes passed")
        CHECKS["integer"](reported["span_upper_bound_bytes"])
        CHECKS["flag"](reported["passed"], computed["passed"])
        if reported["span_upper_bound_bytes"] != computed["span_upper_bound_bytes"]:
            raise ValueError("dataset RSS growth summary differs from native intervals")


def summarize_report(value: object) -> dict[str, Any]:
    report = closed(
        value,
        "schema_version report_kind source_commit environment provenance "
        "fixtures runs growth passed",
    )
    if type(report["schema_version"]) is not int or report["schema_version"] != 1:
        raise ValueError("unknown dataset report version")
    if report["report_kind"] != "dataset_hash_budget_v1":
        raise ValueError("unknown dataset report kind")
    environment = closed(report["environment"], "cpu disk_type")
    for item in environment.values():
        CHECKS["text_value"](item)
    provenance = closed(
        report["provenance"], "source_before source_after locked_runtime wheel_before wheel_after"
    )
    before = CHECKS["source_snapshot"](provenance["source_before"])
    after = CHECKS["source_snapshot"](provenance["source_after"])
    if report["source_commit"] != before["commit"]:
        raise ValueError("dataset report source differs from its snapshot")
    locked = CHECKS["package_versions"](provenance["locked_runtime"])
    for field in ("wheel_before", "wheel_after"):
        CHECKS["pattern_value"](provenance[field], CHECKS["SHA256"])
    expected = validated_fixtures(report["fixtures"])
    runs = validated_runs(report["runs"], expected, before, locked)
    growth = {
        action: growth_acceptance(
            [row for row in runs if row["action"] == action and row["label"] != "capacity"]
        )
        for action in ("inspect", "verify")
    }
    validate_growth(report["growth"], growth)
    identities = [STREAM["runtime_identity"](row["runtime"]) for row in runs]
    passed = (
        before == after
        and provenance["wheel_before"] == provenance["wheel_after"]
        and all(identity == identities[0] for identity in identities)
        and all(row["passed"] for row in runs)
        and all(row["passed"] for row in growth.values())
    )
    CHECKS["flag"](report["passed"], passed)
    return {
        "kind": "dataset-hash",
        "cases": 24,
        "passed": passed,
        "max_elapsed_seconds": max(row["elapsed_seconds"] for row in runs),
        "max_extra_rss_upper_bound_bytes": max(row["extra_rss_upper_bound_bytes"] for row in runs),
        "growth": growth,
    }


def measure_one(
    python: Path,
    workspace: Path,
    fixture: Path,
    expected_path: Path,
    receipt: Path,
    action: str,
    label: str,
    sample: int,
) -> dict[str, Any]:
    work = workspace / f"{label}-{action}-{sample}"
    work.mkdir()
    manifest = work / "manifest.json"
    if action == "verify":
        manifest.write_bytes(expected_path.read_bytes())
    command = [
        str(python),
        "-I",
        str(ROOT / "tests/fixtures/dataset_budget.py"),
        "--root",
        str(fixture),
        "--expected",
        str(expected_path),
        "--receipt",
        str(receipt),
        "--prefix",
        str(python.parent.parent),
        "--work",
        str(work),
        "--manifest",
        str(manifest),
        "--action",
        action,
    ]
    result = subprocess.run(
        command,
        cwd=work,
        env=STREAM["environment"](),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    (work / "stdout.txt").write_text(result.stdout, encoding="utf-8")
    (work / "stderr.txt").write_text(result.stderr, encoding="utf-8")
    if result.returncode or result.stderr:
        raise ValueError("dataset worker failed; original diagnostics retained in workspace")
    measured = json.loads(result.stdout)
    return {**measured, "label": label, "sample": sample}


def measure_fixture(
    python: Path,
    workspace: Path,
    receipt: Path,
    label: str,
    expected: dict[str, Any],
    before: dict[str, Any],
    locked: dict[str, str],
) -> list[dict[str, Any]]:
    root, expected_path = workspace / label, workspace / f"expected-{label}.json"
    prepare_fixture(root, expected, label)
    expected_path.write_text(
        json.dumps(expected, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    runs = []
    for action in ("inspect", "verify"):
        for sample in range(1, SAMPLES + 1):
            measured = measure_one(
                python, workspace, root, expected_path, receipt, action, label, sample
            )
            measured["passed"] = evaluate_run(measured, expected, before, locked)
            runs.append(measured)
    return runs


def check(python: Path, wheel: Path, workspace: Path, output: Path, cpu: str, disk: str) -> int:
    output, workspace = STREAM["new_path"](output), STREAM["new_path"](workspace)
    python, wheel = python.absolute(), wheel.absolute()
    if not python.is_file() or not wheel.is_file():
        raise ValueError("dataset measurement requires installed Python and its wheel")
    before = SOURCES["source"](ROOT)
    locked = STREAM["locked_runtime"](ROOT)
    wheel_before = hashlib.sha256(wheel.read_bytes()).hexdigest()
    workspace.mkdir(mode=0o700)
    receipt = workspace / "source-manifest.json"
    receipt.write_text(
        json.dumps({"source_sha256": before["source_sha256"], "locked_runtime": locked}),
        encoding="utf-8",
    )
    runs, fixtures = [], {}
    for label in LABELS:
        expected = expected_manifest(label)
        fixtures[label] = fixture_summary(expected, label)
        runs.extend(measure_fixture(python, workspace, receipt, label, expected, before, locked))
    report = {
        "schema_version": 1,
        "report_kind": "dataset_hash_budget_v1",
        "source_commit": before["commit"],
        "environment": {"cpu": cpu, "disk_type": disk},
        "provenance": {
            "source_before": before,
            "source_after": SOURCES["source"](ROOT),
            "locked_runtime": locked,
            "wheel_before": wheel_before,
            "wheel_after": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        },
        "fixtures": fixtures,
        "runs": runs,
        "growth": {
            action: growth_acceptance(
                [row for row in runs if row["action"] == action and row["label"] != "capacity"]
            )
            for action in ("inspect", "verify")
        },
    }
    report["passed"] = (
        report["provenance"]["source_before"] == report["provenance"]["source_after"]
        and report["provenance"]["wheel_before"] == report["provenance"]["wheel_after"]
        and all(row["passed"] for row in runs)
        and all(row["passed"] for row in report["growth"].values())
        and all(
            STREAM["runtime_identity"](row["runtime"])
            == STREAM["runtime_identity"](runs[0]["runtime"])
            for row in runs
        )
    )
    summarize_report(report)
    with output.open("x", encoding="utf-8") as destination:
        json.dump(report, destination, ensure_ascii=False, allow_nan=False, indent=2)
        destination.write("\n")
    print(json.dumps(summarize_report(report)))
    return 0 if report["passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("python", "wheel", "workspace", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--cpu-label", default="unknown")
    parser.add_argument("--disk-type", default="unknown")
    args = parser.parse_args()
    return check(
        args.python, args.wheel, args.workspace, args.output, args.cpu_label, args.disk_type
    )


if __name__ == "__main__":
    raise SystemExit(main())
