"""Measure only new synthetic schema-2..5 stores upgrading to operation schema 6."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import runpy
import sqlite3
import stat
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[2]
MARKER = "synthetic-p014-migration.json"


def sources():
    paths = [
        *sorted((PROJECT / "src").rglob("*.py")),
        PROJECT / "tests/conftest.py",
        PROJECT / "tests/fixtures/seed_migration_state.py",
        PROJECT / "tests/fixtures/seed_capability_cache.py",
        PROJECT / "docs/research/p01-3-migration-budget-probe.py",
        Path(__file__).resolve(),
    ]
    return {str(p.relative_to(PROJECT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def worker(path):
    from yorunge import api
    from yorunge.adapters import state, state_schema
    from yorunge.domain.errors import YorungeError

    root = Path(path).resolve()
    parent = root.parent.stat()
    marker = root.parent / MARKER
    if (
        not root.parent.name.startswith("p014-migration-")
        or parent.st_uid != os.getuid()
        or stat.S_IMODE(parent.st_mode) != 0o700
        or marker.is_symlink()
        or marker.read_text() != root.name
    ):
        raise ValueError("only the orchestrator's new synthetic store is accepted")
    helpers = runpy.run_path(str(PROJECT / "docs/research/p01-3-migration-budget-probe.py"))
    before = helpers["contents"](root / state.DB_NAME)
    recorder = helpers["Recorder"](True)
    failure = None
    try:
        with helpers["instrument"](recorder), recorder.phase("use_case"):
            api.initialize_state(state_dir=root)
    except YorungeError as error:
        failure = error.code
    after = helpers["contents"](root / state.DB_NAME)
    with closing(
        sqlite3.connect((root / state.DB_NAME).as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        state.validate(conn, state_schema.MIGRATIONS, full=True)
        operations = (
            conn.execute("SELECT count(*) FROM operations").fetchone()[0] if version == 6 else None
        )
    elapsed = recorder.events[0]["elapsed_ms"]
    return {
        "outcome": failure or "ok",
        "final_version": version,
        "target_reached": version == 6,
        "call_budget_seconds": 5,
        "elapsed_ms": elapsed,
        "within_wall_budget": elapsed <= 5000,
        "source": before,
        "target": after,
        "payload_rows_unchanged": all(after.get(table) == value for table, value in before.items()),
        "operation_rows": operations,
        "post_call_full_validation": "passed",
        "vm_steps": recorder.steps,
        "events": recorder.events,
        "original_deadline_callback_preserved": True,
        "original_progress_intervals": sorted(recorder.original_intervals),
        "delegated_progress_calls": recorder.deadline_calls,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--disk-type", default="unknown")
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker), allow_nan=False))
        return 0
    if (
        Path.cwd().resolve() != PROJECT
        or args.samples < 3
        or args.output is None
        or args.output.exists()
        or args.output.is_symlink()
        or not args.output.parent.is_dir()
    ):
        parser.error(
            "repository CWD, >=3 samples and a new output in an existing directory required"
        )
    from yorunge.adapters import state_schema
    from yorunge.adapters.state import open_store

    before = sources()
    seed = runpy.run_path(str(PROJECT / "tests/fixtures/seed_migration_state.py"))["seed"]
    work = PROJECT / ".local"
    work.mkdir(exist_ok=True)
    runs = []
    for maximum in (False, True):
        for version in (2, 3, 4, 5):
            for sample in range(args.samples):
                with tempfile.TemporaryDirectory(prefix="p014-migration-", dir=work) as folder:
                    root = Path(folder).resolve() / "state"
                    seed(root, version=min(version, 4), maximum=maximum)
                    if version == 5:
                        with patch.object(state_schema, "MIGRATIONS", state_schema.MIGRATIONS[:5]):
                            with open_store(root) as store:
                                store.verify()
                    (root.parent / MARKER).write_text(root.name)
                    child = subprocess.run(
                        [sys.executable, str(Path(__file__).resolve()), "--worker", str(root)],
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    if child.returncode:
                        raise RuntimeError("synthetic worker failed: " + child.stderr)
                    result = json.loads(child.stdout)
                    result.update(source_version=version, maximum=maximum, sample=sample + 1)
                    runs.append(result)
                    print(
                        f"schema {version}, maximum={maximum}, sample {sample + 1}: "
                        f"{result['outcome']} {result['elapsed_ms']:.1f} ms",
                        file=sys.stderr,
                    )
    unchanged = before == sources()
    report = {
        "schema_version": 1,
        "source_reference": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "source_sha256": before,
        "source_unchanged": unchanged,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version,
        "sqlite": sqlite3.sqlite_version,
        "disk_type": args.disk_type,
        "cpu": subprocess.check_output(
            ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
        ).strip()
        if sys.platform == "darwin"
        else platform.processor() or "unknown",
        "runs": runs,
    }
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2, allow_nan=False)
        output.write("\n")
    return (
        0
        if unchanged
        and all(
            r["outcome"] == "ok"
            and r["target_reached"]
            and r["within_wall_budget"]
            and r["payload_rows_unchanged"]
            and r["operation_rows"] == 0
            for r in runs
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
