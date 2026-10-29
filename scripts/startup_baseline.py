"""Preserve the existing first-runtime release control without inventing an old runtime."""

from __future__ import annotations

import hashlib
import runpy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STARTUP = runpy.run_path(str(ROOT / "scripts/startup_evidence.py"))
CHECKS = STARTUP["CHECKS"]
PINNED_RUNTIME = "pinned_runtime"
INITIAL_CONTROL = "initial_runtime_same_source_control"
RUNTIME_PATHS = ("pyproject.toml", "src", "setup.py", "setup.cfg", "yorunge")


def initial_commit(baseline: Path) -> str:
    if baseline.is_symlink() or not baseline.is_dir():
        raise ValueError("initial startup baseline must be a complete Git checkout")
    run = STARTUP["JOBS"]["run"]
    top = run(["git", "rev-parse", "--show-toplevel"], cwd=baseline).stdout.strip()
    if Path(top).resolve() != baseline.resolve():
        raise ValueError("initial startup baseline is not its own Git checkout")
    commit: str = run(["git", "rev-parse", "HEAD"], cwd=baseline).stdout.strip()
    CHECKS["pattern_value"](commit, CHECKS["COMMIT"])
    tracked = run(["git", "ls-tree", "--name-only", "HEAD", "--", *RUNTIME_PATHS], cwd=baseline)
    dirty = run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=baseline)
    if tracked.stdout.strip() or dirty.stdout.strip():
        raise ValueError("missing or modified runtime baseline cannot become an initial control")
    if any((baseline / name).exists() or (baseline / name).is_symlink() for name in RUNTIME_PATHS):
        raise ValueError("initial startup baseline must have no runtime project inputs")
    return commit


def select(root: Path, baseline: Path) -> tuple[Path, dict[str, Any]]:
    if baseline.is_symlink():
        raise ValueError("startup baseline must not be a symlink")
    current = STARTUP["source"](root)["commit"]
    project = baseline / "pyproject.toml"
    if project.is_file() and not project.is_symlink():
        pinned = STARTUP["source"](baseline)["commit"]
        effective, mode = baseline, PINNED_RUNTIME
    else:
        pinned = initial_commit(baseline)
        effective, mode = root, INITIAL_CONTROL
    value = {
        "schema_version": 1,
        "report_kind": "startup_baseline_selection_v1",
        "source_commit": current,
        "pinned_baseline_commit": pinned,
        "effective_baseline_commit": pinned if mode == PINNED_RUNTIME else current,
        "mode": mode,
        "report_sha256": None,
    }
    summarize(value)
    return effective, value


def summarize(value: dict[str, Any]) -> dict[str, Any]:
    CHECKS["closed"](
        value,
        "schema_version report_kind source_commit pinned_baseline_commit "
        "effective_baseline_commit mode report_sha256",
        "startup baseline selection",
    )
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError("unknown startup baseline selection version")
    if value["report_kind"] != "startup_baseline_selection_v1":
        raise ValueError("unknown startup baseline selection kind")
    for name in ("source_commit", "pinned_baseline_commit", "effective_baseline_commit"):
        CHECKS["pattern_value"](value[name], CHECKS["COMMIT"])
    if value["mode"] == PINNED_RUNTIME:
        expected = value["pinned_baseline_commit"]
    elif value["mode"] == INITIAL_CONTROL:
        expected = value["source_commit"]
        if value["pinned_baseline_commit"] == expected:
            raise ValueError("initial control requires a distinct documentation-only baseline")
    else:
        raise ValueError("unknown startup baseline selection mode")
    if value["effective_baseline_commit"] != expected:
        raise ValueError("startup effective baseline contradicts its declared selection mode")
    if value["report_sha256"] is not None:
        CHECKS["pattern_value"](value["report_sha256"], CHECKS["SHA256"])
    return {
        "kind": "startup_baseline_selection",
        "source_commit": value["source_commit"],
        "mode": value["mode"],
        "pinned_baseline_commit": value["pinned_baseline_commit"],
        "effective_baseline_commit": expected,
        "report_sha256": value["report_sha256"],
        "complete": value["report_sha256"] is not None,
        "diagnostic_only": True,
    }


def verify(
    root: Path, baseline: Path, report: dict[str, Any], raw: bytes, value: dict[str, Any]
) -> None:
    summarize(value)
    effective, expected = select(root, baseline)
    expected["report_sha256"] = hashlib.sha256(raw).hexdigest()
    if value != expected or value["source_commit"] != report["source_commit"]:
        raise ValueError("startup baseline selection does not match its pinned checkout or report")
    expected_source = STARTUP["source"](effective)
    for point in ("before", "after"):
        if report["snapshots"][point]["baseline"]["source"] != expected_source:
            raise ValueError(
                "startup report differs from the explicitly selected effective baseline"
            )
