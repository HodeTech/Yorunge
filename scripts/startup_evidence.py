"""Closed startup receipts: historical artifact identity and current source equivalence."""

from __future__ import annotations

import hashlib
import math
import runpy
import sqlite3
import statistics
import subprocess
from contextlib import closing
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHECKS = runpy.run_path(str(ROOT / "scripts/research_evidence.py"))
JOBS = runpy.run_path(str(ROOT / "scripts/benchmark-jobs.py"))
BUDGETS = {"help": 500, "version": 500, "context": 200, "cache": 200}
PAIR_METHOD = (
    "alternating AB/BA process pairs on the same host; three warmups; all samples retained"
)
ACCEPTANCE = "candidate absolute budgets only; baseline and paired ratios are diagnostic"
COLD_METHOD = "first command process; OS/disk caches uncontrolled; not a cold boot"
CPU_METHOD = (
    "RUSAGE_CHILDREN deltas for sequential waited children; wall minus child CPU "
    "includes parent overhead and wait; does not identify I/O or scheduler cause"
)
INSTALLATION = "isolated runtime-only wheel; frozen uv.lock; fixed hash seed"
TYPED_OUTPUT_PROBE = """
import sys
from yorunge.domain.models import Context, Result
from yorunge.domain.capabilities import CachedCapabilityView
model = Result[Context] if sys.argv[1] == 'context' else Result[CachedCapabilityView]
model.model_validate_json(sys.stdin.buffer.read(1048577))
print('validated')
"""


def closed(value: object, fields: str) -> dict[str, Any]:
    return CHECKS["closed"](value, fields, "startup evidence")  # type: ignore[no-any-return]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source(project: Path) -> dict[str, Any]:
    # No untracked runtime data may silently escape the measured input scope.
    for path in (project / "src/yorunge").rglob("*"):
        if (
            path.is_file()
            and path.suffix != ".py"
            and "__pycache__" not in path.parts
            and path != project / "src/yorunge/py.typed"
        ):
            raise ValueError("startup source scope requires explicit non-Python runtime inputs")
    result: dict[str, Any] = JOBS["source"](project)
    workflows = project / ".github/workflows"
    if (project / ".github").is_symlink() or workflows.is_symlink():
        raise ValueError("startup workflows must not be symlinks")
    for path in sorted(workflows.rglob("*")):
        if path.is_symlink():
            raise ValueError("startup workflows must not be symlinks")
        if path.is_file():
            result["source_sha256"][str(path.relative_to(project))] = digest(path)
    marker = project / "src/yorunge/py.typed"
    if marker.is_file():
        result["source_sha256"]["src/yorunge/py.typed"] = digest(marker)
    return result


def fixture(state: Path, profile: Path) -> dict[str, Any]:
    database = state / "state.sqlite3"
    if state.is_symlink() or database.is_symlink() or profile.is_symlink():
        raise ValueError("startup fixtures must not be symlinks")
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        rows = db.execute("SELECT * FROM capability_cache ORDER BY cache_key").fetchall()
        expiries = db.execute(
            "SELECT * FROM capability_expiries ORDER BY cache_key,expires_at"
        ).fetchall()
        totals = db.execute(
            "SELECT count(*),sum(length(CAST(payload AS BLOB))),"
            "max(length(CAST(payload AS BLOB))) FROM capability_cache"
        ).fetchone()
    if totals[0] != 1024 or not all(type(x) is int and x > 0 for x in totals):
        raise ValueError("startup requires 1024 nonempty cache payloads")
    return {
        "state": str(state),
        "profile": str(profile),
        "profile_sha256": digest(profile),
        "profile_bytes": profile.stat().st_size,
        "records": totals[0],
        "payload_bytes": totals[1],
        "largest_record_bytes": totals[2],
        "cache_sha256": hashlib.sha256(CHECKS["encode"](rows)).hexdigest(),
        "expiries_sha256": hashlib.sha256(CHECKS["encode"](expiries)).hexdigest(),
    }


def validate_output(
    command: list[str], content: bytes, *, version: str | None = None, python: str | None = None
) -> None:
    """Independent fixed-fixture semantics plus installed wire types; outside timing."""
    if not content or len(content) > 1024 * 1024:
        raise ValueError("startup stdout must be nonempty and bounded")
    text = content.decode("utf-8", "strict")
    if command[-1] == "--help":
        if not text.startswith("usage: yorunge ") or not all(
            word in text for word in ("context", "capabilities", "jobs", "--output", "--version")
        ):
            raise ValueError("startup help output mismatch")
        return
    if command[-1] == "--version":
        from yorunge import __version__

        if text != f"yorunge {version if version is not None else __version__}\n":
            raise ValueError("startup version output mismatch")
        return
    from yorunge.domain.capabilities import CachedCapabilityView
    from yorunge.domain.models import Context, Result

    value = CHECKS["decode"](content)
    if command[1:3] == ["context", "show"]:
        validate_typed_output(content, python, "context", Result[Context])
        validate_context(value["data"])
    elif command[1] == "capabilities":
        validate_typed_output(content, python, "cache", Result[CachedCapabilityView])
        state = Path(command[command.index("--state-dir") + 1])
        validate_cache(value["data"]["records"], state)
    else:
        raise ValueError("unknown startup command")
    if value["warnings"] != [] or value["operation_id"] is not None:
        raise ValueError("startup must return the unbound warning-free Result")


def validate_typed_output(content: bytes, python: str | None, kind: str, model: Any) -> None:
    if python is None:
        model.model_validate_json(content)
        return
    result = subprocess.run(
        [python, "-I", "-c", TYPED_OUTPUT_PROBE, kind],
        input=content,
        capture_output=True,
        check=True,
        timeout=10,
    )
    if result.stdout != b"validated\n" or result.stderr:
        raise ValueError("startup installed wire validation failed")


def validate_context(value: object) -> None:
    expected = {
        "profile": "work",
        "project_id": "synthetic-project",
        "account_id": None,
        "platform_url": "https://api.ssyz.org.tr/api/v1",
        "llm_url": "https://evren-llmapi.ssyz.org.tr/v1",
        "remote_verified": False,
    }
    if value != expected:
        raise ValueError("startup context differs from the fixed profile oracle")


def validate_cache(records: list[dict[str, Any]], state: Path) -> None:
    expected = {
        "planning.offline": ("supported", "offline_planner_implemented"),
        "tool.adapter": ("unsupported", "adapter_not_implemented"),
    }
    if len(records) != 2 or {r["key"]["capability_id"] for r in records} != set(expected):
        raise ValueError("startup cache must return the two expected capabilities")
    with closing(
        sqlite3.connect((state / "state.sqlite3").resolve().as_uri() + "?mode=ro", uri=True)
    ) as db:
        store_id, epoch = db.execute(
            "SELECT store_id,identity_epoch FROM state_meta WHERE singleton=1"
        ).fetchone()
    scope = {
        "schema_version": 2,
        "store_id": store_id,
        "identity_epoch": epoch,
        "clock_generation": 1,
        "service_id": "local",
        "service_origin": None,
        "api_base_path": None,
        "account_id": None,
        "project_id": "synthetic-project",
        "credential_id": None,
        "credential_revision": None,
        "authorization_scope": None,
        "model": None,
        "tool": {
            "id": "forgelm",
            "version": None,
            "executable_digest": None,
            "environment_digest": None,
        },
        "execution": {
            "backend": "local",
            "runtime_id": None,
            "runtime_revision": None,
            "environment_digest": None,
        },
    }
    for record in records:
        key = record["key"]
        valid = (
            record["hit"] is True
            and record["freshness"] == "fresh"
            and key["task"] == "llm.train"
            and key["scope"] == scope
            and (record["effective_support"], record["reason_code"])
            == expected[key["capability_id"]]
            and record["record"] is not None
            and record["record"]["key"] == key
        )
        if not valid:
            raise ValueError("startup cached output differs from fixture expectations")
        inner = record["record"]
        if (inner["support"], inner["reason_code"]) != expected[key["capability_id"]]:
            raise ValueError("startup stored capability differs from fixture expectations")
        validate_evidence(inner, expected[key["capability_id"]])


def validate_evidence(inner: dict[str, Any], expected: tuple[str, str]) -> None:
    if len(inner["evidence"]) != 1 or inner["conflict_until"] is not None:
        raise ValueError("startup requires the single local policy proof")
    proof = inner["evidence"][0]
    fixed = {key: value for key, value in proof.items() if key not in ("checked_at", "expires_at")}
    if fixed != {
        "kind": "local_policy",
        "producer_id": "yorunge-local-policy",
        "producer_version": "1",
        "policy_version": 1,
        "provenance": "offline-selection-policy",
        "support": expected[0],
        "reason_code": expected[1],
        "constraints": [],
    }:
        raise ValueError("startup proof differs from the independent policy oracle")


def numbers(value: object, length: int, *, nullable: bool = False) -> list[Any]:
    if not isinstance(value, list) or len(value) != length:
        raise ValueError("startup sample count mismatch")
    for item in value:
        if item is not None or not nullable:
            CHECKS["number"](item)
    return value


def measurements(value: object, samples: int) -> dict[str, Any]:
    rows = closed(value, " ".join(BUDGETS))
    for name, budget in BUDGETS.items():
        row = closed(
            rows[name],
            "first_process_ms warm_median_ms warm_p95_ms warm_samples_ms "
            "warm_child_user_cpu_ms warm_child_system_cpu_ms warm_non_cpu_estimate_ms "
            "target_ms passed fresh_cache_hit_verified",
        )
        walls = numbers(row["warm_samples_ms"], samples)
        if min(walls) <= 0 or CHECKS["number"](row["first_process_ms"]) <= 0:
            raise ValueError("startup wall samples must be positive")
        for key in (
            "warm_child_user_cpu_ms",
            "warm_child_system_cpu_ms",
            "warm_non_cpu_estimate_ms",
        ):
            numbers(row[key], samples, nullable=True)
        if type(row["target_ms"]) is not int or row["target_ms"] != budget:
            raise ValueError("startup budget must retain 500/200 ms")
        p95 = sorted(walls)[math.ceil(samples * 0.95) - 1]
        if CHECKS["number"](row["warm_p95_ms"]) != p95 or CHECKS["number"](
            row["warm_median_ms"]
        ) != round(statistics.median(walls), 3):
            raise ValueError("startup percentile or median differs from all samples")
        CHECKS["flag"](row["passed"], p95 <= budget)
        CHECKS["flag"](row["fresh_cache_hit_verified"], name == "cache")
    return rows


def validate_fixture(value: object) -> dict[str, Any]:
    data = closed(
        value,
        "state profile profile_sha256 profile_bytes records payload_bytes largest_record_bytes "
        "cache_sha256 expiries_sha256",
    )
    for name in ("state", "profile"):
        CHECKS["runtime_path"](data[name])
    for name in ("profile_sha256", "cache_sha256", "expiries_sha256"):
        CHECKS["pattern_value"](data[name], CHECKS["SHA256"])
    for name in ("profile_bytes", "records", "payload_bytes", "largest_record_bytes"):
        CHECKS["integer"](data[name], minimum=1)
    if data["records"] != 1024 or data["payload_bytes"] < data["largest_record_bytes"]:
        raise ValueError("startup fixture dataset mismatch")
    return data


def snapshot(value: object) -> dict[str, Any]:
    data = closed(value, "source installed runtime_data_sha256 fixture wheel_path wheel_sha256")
    src = CHECKS["source_snapshot"](data["source"])
    installed = CHECKS["jobs_runtime"](data["installed"])
    if installed["installed_source_sha256"] != CHECKS["python_hashes"](src, package_prefix=True):
        raise ValueError("startup installed product differs from measured source")
    expected_data = {
        name.removeprefix("src/"): value
        for name, value in src["source_sha256"].items()
        if name.startswith("src/yorunge/") and not name.endswith(".py")
    }
    if data["runtime_data_sha256"] != expected_data:
        raise ValueError("startup installed runtime data differs from measured source")
    CHECKS["runtime_path"](data["wheel_path"])
    CHECKS["pattern_value"](data["wheel_sha256"], CHECKS["SHA256"])
    validate_fixture(data["fixture"])
    return data


def raw_metadata(value: object) -> dict[str, Any]:
    raw = closed(
        value,
        "schema_version python platform machine cpu cpu_affinity runner_image disk_type "
        "cache_dataset profile_bytes profile_sha256 samples_per_command installation "
        "cold_method cpu_method measurements comparison",
    )
    if type(raw["schema_version"]) is not int or raw["schema_version"] != 2:
        raise ValueError("startup evidence requires original v2 samples")
    CHECKS["integer"](raw["samples_per_command"], minimum=30)
    expected_methods = {
        "installation": INSTALLATION,
        "cold_method": COLD_METHOD,
        "cpu_method": CPU_METHOD,
    }
    if any(raw[key] != expected for key, expected in expected_methods.items()):
        raise ValueError("startup measurement method mismatch")
    for key in ("python", "platform", "machine", "cpu", "disk_type"):
        CHECKS["text_value"](raw[key])
    validate_scheduling(raw)
    dataset = closed(raw["cache_dataset"], "records payload_bytes largest_record_bytes")
    for item in dataset.values():
        CHECKS["integer"](item, minimum=1)
    CHECKS["integer"](raw["profile_bytes"], minimum=1)
    CHECKS["pattern_value"](raw["profile_sha256"], CHECKS["SHA256"])
    return raw


def validate_scheduling(raw: dict[str, Any]) -> None:
    for item in closed(raw["runner_image"], "ImageOS ImageVersion").values():
        if item is not None:
            CHECKS["text_value"](item)
    affinity = raw["cpu_affinity"]
    if affinity is not None:
        if not isinstance(affinity, list) or not affinity:
            raise ValueError("invalid CPU affinity")
        for item in affinity:
            CHECKS["integer"](item)
        if affinity != sorted(set(affinity)):
            raise ValueError("invalid CPU affinity order")


def paired_comparison(raw: dict[str, Any], rows: dict[str, Any]) -> dict[str, Any]:
    samples = raw["samples_per_command"]
    comparison = closed(
        raw["comparison"],
        "method baseline_cache_dataset baseline_measurements paired_comparisons acceptance",
    )
    if comparison["method"] != PAIR_METHOD or comparison["acceptance"] != ACCEPTANCE:
        raise ValueError("startup requires same-host alternating AB/BA comparison")
    baseline_dataset = closed(
        comparison["baseline_cache_dataset"], "records payload_bytes largest_record_bytes"
    )
    for item in baseline_dataset.values():
        CHECKS["integer"](item, minimum=1)
    baseline_rows = measurements(comparison["baseline_measurements"], samples)
    pairs = closed(comparison["paired_comparisons"], " ".join(BUDGETS))
    for name in BUDGETS:
        validate_pair(pairs[name], rows[name], baseline_rows[name], samples)
    return baseline_rows


def validate_pair(
    value: object, current: dict[str, Any], baseline: dict[str, Any], samples: int
) -> None:
    pair = closed(value, "paired_wall_ratios median_paired_wall_ratio candidate_faster_pairs pairs")
    ratios = [
        a / b for a, b in zip(current["warm_samples_ms"], baseline["warm_samples_ms"], strict=True)
    ]
    if numbers(pair["paired_wall_ratios"], samples) != [round(x, 6) for x in ratios]:
        raise ValueError("startup paired ratios mismatch")
    if CHECKS["integer"](pair["pairs"]) != samples or CHECKS["integer"](
        pair["candidate_faster_pairs"]
    ) != sum(x < 1 for x in ratios):
        raise ValueError("startup pair count mismatch")
    if CHECKS["number"](pair["median_paired_wall_ratio"]) != round(statistics.median(ratios), 6):
        raise ValueError("startup median ratio mismatch")


def validate_snapshots(report: dict[str, Any], raw: dict[str, Any]) -> None:
    snapshots = closed(report["snapshots"], "before after")
    for point in ("before", "after"):
        for side in closed(snapshots[point], "candidate baseline").values():
            snapshot(side)
    if snapshots["before"] != snapshots["after"]:
        raise ValueError(
            "startup source, installation, wheel or fixture changed during measurement"
        )
    head, base = (snapshots["before"][side] for side in ("candidate", "baseline"))
    if report["source_commit"] != head["source"]["commit"]:
        raise ValueError("startup source identity mismatch")
    if head["fixture"]["profile_sha256"] != head["source"]["source_sha256"].get(
        "examples/profile.toml"
    ):
        raise ValueError("startup common profile must match the candidate source snapshot")
    for side in (head, base):
        validate_snapshot_equivalence(side, raw)
    if head["fixture"]["state"] == base["fixture"]["state"]:
        raise ValueError("startup requires separate baseline and candidate stores")
    if head["installed"]["prefix"] == base["installed"]["prefix"]:
        raise ValueError("startup requires separate baseline and candidate installations")


def validate_snapshot_equivalence(side: dict[str, Any], raw: dict[str, Any]) -> None:
    if any(raw[key] != side["installed"][key] for key in ("python", "platform", "machine")):
        raise ValueError("startup runtimes must share the measured interpreter and host")
    fx = side["fixture"]
    dataset = {key: fx[key] for key in ("records", "payload_bytes", "largest_record_bytes")}
    if raw["cache_dataset"] != dataset or raw["comparison"]["baseline_cache_dataset"] != dataset:
        raise ValueError("startup dataset equivalence mismatch")
    if raw["profile_sha256"] != fx["profile_sha256"] or raw["profile_bytes"] != fx["profile_bytes"]:
        raise ValueError("startup profile equivalence mismatch")


def output_checks(
    value: object, rows: dict[str, Any], samples: int, runtime: dict[str, Any]
) -> None:
    for name, row in closed(value, " ".join(BUDGETS)).items():
        row = closed(
            row,
            "typed_stdout_verified verified_processes stdout_sha256 wall_ms "
            "expected_version expected_python",
        )
        if (
            row["expected_version"] != runtime["product_version"]
            or row["expected_python"] != runtime["executable"]
        ):
            raise ValueError("startup output oracle version differs from its installed product")
        CHECKS["flag"](row["typed_stdout_verified"], True)
        if CHECKS["integer"](row["verified_processes"]) != samples + 4:
            raise ValueError("startup typed output process count mismatch")
        if not isinstance(row["stdout_sha256"], list) or len(row["stdout_sha256"]) != samples + 4:
            raise ValueError("startup output hash count mismatch")
        for digest_value in row["stdout_sha256"]:
            CHECKS["pattern_value"](digest_value, CHECKS["SHA256"])
        walls = numbers(row["wall_ms"], samples + 4)
        if min(walls) <= 0 or walls[4:] != rows[name]["warm_samples_ms"]:
            raise ValueError("startup output validation timing differs from measured samples")
        if round(walls[0], 3) != rows[name]["first_process_ms"]:
            raise ValueError("startup first process mismatch")


def validate(report: dict[str, Any]) -> dict[str, Any]:
    closed(
        report,
        "schema_version report_kind source_commit measurement snapshots output_checks "
        "measurement_exit passed",
    )
    if type(report["schema_version"]) is not int or report["schema_version"] != 1:
        raise ValueError("unknown startup evidence version")
    if report["report_kind"] != "startup_evidence_v1":
        raise ValueError("unknown startup evidence kind")
    CHECKS["pattern_value"](report["source_commit"], CHECKS["COMMIT"])
    raw = raw_metadata(report["measurement"])
    samples = raw["samples_per_command"]
    rows = measurements(raw["measurements"], samples)
    baseline_rows = paired_comparison(raw, rows)
    validate_snapshots(report, raw)
    outputs = closed(report["output_checks"], "candidate baseline")
    for side, side_rows in (("candidate", rows), ("baseline", baseline_rows)):
        runtime = report["snapshots"]["before"][side]["installed"]
        output_checks(outputs[side], side_rows, samples, runtime)
    passed = all(row["passed"] for row in rows.values())
    if type(report["measurement_exit"]) is not int or report["measurement_exit"] != int(not passed):
        raise ValueError("startup exit contradicts recomputed absolute budget outcome")
    CHECKS["flag"](report["passed"], passed)
    return {
        "kind": "startup_evidence",
        "passed": passed,
        "source_commit": report["source_commit"],
        "outcome": "passed" if passed else "diagnostic_budget_exceeded",
        "measurements": CHECKS["startup_summary"](raw)["measurements"],
    }


def current_sources(root: Path, report: dict[str, Any]) -> None:
    current = source(root)["source_sha256"]
    expected_packages = JOBS["locked_runtime"](root)
    for point in ("before", "after"):
        candidate = report["snapshots"][point]["candidate"]
        if candidate["source"]["source_sha256"] != current:
            raise ValueError("startup reference differs from complete current source bytes")
        if candidate["installed"]["packages"] != expected_packages:
            raise ValueError("startup reference differs from current frozen runtime")


def reference(root: Path, report: dict[str, Any]) -> dict[str, Any]:
    summary = validate(report)
    if not summary["passed"]:
        raise ValueError("startup reference must pass all four absolute budgets")
    current_sources(root, report)
    raw = report["measurement"]
    CHECKS["jobs_reference_environment"](
        {"runtime": raw, "cpu": raw["cpu"], "disk_type": raw["disk_type"]}
    )
    return summary
