"""Run Linux startup diagnostics; only a fully verified budget overrun is nonblocking."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import runpy
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STARTUP = runpy.run_path(str(ROOT / "scripts/startup_evidence.py"))
CHECKS = STARTUP["CHECKS"]
RUN_URL = re.compile(
    r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/runs/[1-9][0-9]*"
)
OUTCOMES = {"passed", "diagnostic_budget_exceeded", "error"}


def classify(root: Path, baseline: Path, report: dict[str, Any], code: int) -> dict[str, Any]:
    summary: dict[str, Any] = STARTUP["validate"](report)
    STARTUP["current_sources"](root, report)
    if type(code) is not int or code != report["measurement_exit"]:
        raise ValueError("startup producer exit differs from the verified measurement")
    if not report["measurement"]["platform"].startswith("Linux-"):
        raise ValueError("startup diagnostic policy applies only to Linux")
    expected = STARTUP["source"](baseline)
    packages = STARTUP["JOBS"]["locked_runtime"](baseline)
    for point in ("before", "after"):
        saved = report["snapshots"][point]["baseline"]
        if saved["source"] != expected or saved["installed"]["packages"] != packages:
            raise ValueError("startup diagnostic baseline differs from the pinned checkout")
    return summary


def receipt_summary(value: dict[str, Any]) -> dict[str, Any]:
    CHECKS["closed"](
        value,
        "schema_version report_kind source_commit run_url report_name report_sha256 "
        "producer_exit outcome reason p95_ms",
        "startup diagnostic receipt",
    )
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError("unknown startup diagnostic receipt version")
    if value["report_kind"] != "startup_ci_diagnostic_v1" or value["outcome"] not in OUTCOMES:
        raise ValueError("unknown startup diagnostic kind or outcome")
    CHECKS["pattern_value"](value["source_commit"], CHECKS["COMMIT"])
    CHECKS["pattern_value"](value["run_url"], RUN_URL)
    CHECKS["pattern_value"](value["report_name"], CHECKS["NAME"])
    if value["report_sha256"] is not None:
        CHECKS["pattern_value"](value["report_sha256"], CHECKS["SHA256"])
    if type(value["producer_exit"]) is not int:
        raise ValueError("startup diagnostic exit must be an integer")
    if value["outcome"] == "error":
        if value["reason"] not in {"measurement_failed", "invalid_evidence", "missing_evidence"}:
            raise ValueError("unknown startup diagnostic failure reason")
        if value["p95_ms"] != {}:
            raise ValueError("unverified startup failure cannot claim valid metrics")
    else:
        valid_receipt_metrics(value)
    return {
        "kind": "startup_ci_diagnostic",
        "source_commit": value["source_commit"],
        "outcome": value["outcome"],
        "reason": value["reason"],
        "run_url": value["run_url"],
        "diagnostic_only": True,
        "passed": value["outcome"] == "passed",
        "ci_classification_accepted": value["outcome"] != "error",
        "p95_ms": value["p95_ms"],
        "report_sha256": value["report_sha256"],
    }


def valid_receipt_metrics(value: dict[str, Any]) -> None:
    names = [f"{side}/{name}" for side in ("candidate", "baseline") for name in STARTUP["BUDGETS"]]
    metrics = CHECKS["closed"](value["p95_ms"], " ".join(names), "startup diagnostic p95")
    for duration in metrics.values():
        if CHECKS["number"](duration) <= 0:
            raise ValueError("startup diagnostic metrics must be positive")
    passed = all(
        metrics[f"candidate/{name}"] <= budget for name, budget in STARTUP["BUDGETS"].items()
    )
    expected = "passed" if passed else "diagnostic_budget_exceeded"
    if (
        value["outcome"] != expected
        or value["producer_exit"] != int(not passed)
        or value["reason"] != "validated"
        or value["report_sha256"] is None
    ):
        raise ValueError("startup diagnostic outcome contradicts its absolute budget metrics")


def verify_files(
    root: Path, baseline: Path, report_path: Path, receipt_path: Path
) -> dict[str, Any]:
    raw = CHECKS["read_bounded"](report_path, CHECKS["MAX_REPORT_BYTES"])
    report = CHECKS["decode"](raw)
    receipt: dict[str, Any] = CHECKS["decode"](
        CHECKS["read_bounded"](receipt_path, CHECKS["MAX_REPORT_BYTES"])
    )
    receipt_summary(receipt)
    summary = classify(root, baseline, report, receipt["producer_exit"])
    if (
        receipt["outcome"] != summary["outcome"]
        or receipt["source_commit"] != report["source_commit"]
        or receipt["report_name"] != report_path.name
        or receipt["report_sha256"] != hashlib.sha256(raw).hexdigest()
        or receipt["p95_ms"]
        != {name: row["p95_ms"] for name, row in summary["measurements"].items()}
    ):
        raise ValueError("startup diagnostic receipt differs from its original report bytes")
    return receipt


def publish(value: dict[str, Any]) -> None:
    receipt_summary(value)
    outcome = value["outcome"]
    lines = [
        f"### Linux startup: `{outcome}`",
        "",
        f"Run: {value['run_url']}",
        f"Source: `{value['source_commit']}`",
        f"Raw report: `{value['report_name']}`; SHA-256: `{value['report_sha256']}`",
        "",
        "| Command | Candidate p95 ms | Baseline p95 ms |",
        "|---|---:|---:|",
    ]
    if outcome != "error":
        for name in STARTUP["BUDGETS"]:
            lines.append(
                f"| {name} | {value['p95_ms']['candidate/' + name]:.6f} | "
                f"{value['p95_ms']['baseline/' + name]:.6f} |"
            )
    lines += [
        "",
        "Diagnostic only; M5 source-bound startup/jobs and Linux raw gates remain required.",
        "Maintainer: archive original report and receipt before acceptance; final docs/merge "
        "runs remain explicit retention follow-ups under ADR-0019.",
        "",
    ]
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(path).open("a", encoding="utf-8") as output:
            output.write("\n".join(lines))
    if path := os.environ.get("GITHUB_OUTPUT"):
        with Path(path).open("a", encoding="utf-8") as output:
            output.write(f"outcome={outcome}\n")
    if outcome == "diagnostic_budget_exceeded":
        print(
            "::warning title=Linux startup diagnostic_budget_exceeded::Absolute startup budget "
            "exceeded on this Linux host; review and permanent archival are required. "
            "This is not Linux performance acceptance."
        )
    print(json.dumps(value, sort_keys=True, allow_nan=False))


def run(args: argparse.Namespace) -> int:
    if args.receipt.exists() or args.receipt.is_symlink():
        raise ValueError("use a new startup diagnostic receipt path")
    source = STARTUP["source"](ROOT)
    value: dict[str, Any] = {
        "schema_version": 1,
        "report_kind": "startup_ci_diagnostic_v1",
        "source_commit": source["commit"],
        "run_url": args.run_url,
        "report_name": args.report.name,
        "report_sha256": None,
        "producer_exit": 1,
        "outcome": "error",
        "reason": "measurement_failed",
        "p95_ms": {},
    }
    producer = runpy.run_path(str(ROOT / "scripts/check-startup-evidence.py"))
    try:
        value["producer_exit"] = producer["check"](
            ROOT,
            args.baseline_project,
            args.workspace,
            args.report,
            args.uv,
            cpu=None,
            disk="unknown",
        )
        value["reason"] = "invalid_evidence"
        raw = CHECKS["read_bounded"](args.report, CHECKS["MAX_REPORT_BYTES"])
        summary = classify(
            ROOT, args.baseline_project, CHECKS["decode"](raw), value["producer_exit"]
        )
        value.update(
            outcome=summary["outcome"],
            reason="validated",
            p95_ms={key: row["p95_ms"] for key, row in summary["measurements"].items()},
        )
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        if not args.report.is_file():
            value["reason"] = "missing_evidence"
    if args.report.is_file():
        try:
            bounded = CHECKS["read_bounded"](args.report, CHECKS["MAX_REPORT_BYTES"])
            value["report_sha256"] = hashlib.sha256(bounded).hexdigest()
        except ValueError:
            value.update(outcome="error", reason="invalid_evidence", p95_ms={})
    receipt_summary(value)
    with args.receipt.open("x", encoding="utf-8") as output:
        output.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
    publish(value)
    return 1 if value["outcome"] == "error" else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-project", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--uv", type=Path)
    parser.add_argument("--verify-receipt", action="store_true")
    parser.add_argument(
        "--run-url",
        default=f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}"
        f"/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}",
    )
    args = parser.parse_args()
    args.baseline_project = args.baseline_project.resolve()
    args.report, args.receipt = args.report.absolute(), args.receipt.absolute()
    try:
        CHECKS["pattern_value"](args.run_url, RUN_URL)
        if args.verify_receipt:
            verify_files(ROOT, args.baseline_project, args.report, args.receipt)
            return 0
        if args.workspace is None or args.uv is None:
            parser.error("run requires --workspace and --uv")
        args.workspace, args.uv = args.workspace.absolute(), args.uv.resolve()
        return run(args)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Startup diagnostic failed: {type(error).__name__}\n")


if __name__ == "__main__":
    raise SystemExit(main())
