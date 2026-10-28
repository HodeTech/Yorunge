"""Profile only new synthetic historical stores; never accepts an existing user store."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import runpy
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
from contextlib import closing, contextmanager
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

if sys.platform in ("darwin", "linux"):
    import resource

PROJECT = Path(__file__).resolve().parents[2]
CASES = ("schema-2", "schema-3", "schema-4", "stage", "live")
MARKER = "synthetic-migration-profile.json"


class Recorder:
    def __init__(self, vm):
        self.vm = vm
        self.steps = 0
        self.deadline_handlers = 0
        self.deadline_calls = 0
        self.original_intervals = set()
        self.stack = []
        self.events = []

    @contextmanager
    def phase(self, name, **fields):
        event = {
            "id": len(self.events),
            "parent": self.stack[-1] if self.stack else None,
            "name": name,
            **fields,
        }
        self.events.append(event)
        self.stack.append(event["id"])
        before, started = self.steps, time.perf_counter_ns()
        try:
            yield event
            event["outcome"] = "ok"
        except Exception as error:
            event["outcome"] = getattr(error, "code", type(error).__name__)
            raise
        finally:
            event["elapsed_ms"] = (time.perf_counter_ns() - started) / 1_000_000
            event["vm_callbacks"] = self.steps - before if self.vm else None
            self.stack.pop()


def observed_factory(recorder):
    from yorunge.adapters.state_schema import MIGRATIONS

    ddl = {
        sql: (step.from_version, step.to_version, index)
        for step in MIGRATIONS
        for index, sql in enumerate(step.statements)
    }

    class Connection(sqlite3.Connection):
        def __init__(self, database, *args, **kwargs):
            self.role = "schema-template" if str(database) == ":memory:" else "file"
            self.original_progress = None
            self.interval = 0
            self.since_check = 0
            super().__init__(database, *args, **kwargs)
            if recorder.vm:
                super().set_progress_handler(self.progress, 1)

        def progress(self):
            recorder.steps += 1
            self.since_check += 1
            if self.original_progress is not None and self.since_check >= self.interval:
                self.since_check = 0
                recorder.deadline_calls += 1
                return self.original_progress()
            return 0

        def set_progress_handler(self, callback, n=0):
            if not recorder.vm:
                return super().set_progress_handler(callback, n)
            self.original_progress = callback if n > 0 else None
            self.interval = n
            self.since_check = 0
            if callback is not None and n > 0:
                recorder.deadline_handlers += 1
                recorder.original_intervals.add(n)
            return super().set_progress_handler(self.progress, 1)

        def execute(self, sql, parameters=()):
            if sql in ddl:
                start, end, index = ddl[sql]
                with recorder.phase(
                    "ddl",
                    from_version=start,
                    to_version=end,
                    statement_index=index,
                    database_role=self.role,
                ):
                    return super().execute(sql, parameters)
            if sql in ("COMMIT", "ROLLBACK"):
                with recorder.phase(sql.lower(), database_role=self.role):
                    return super().execute(sql, parameters)
            return super().execute(sql, parameters)

    return Connection


@contextmanager
def instrument(recorder):
    from yorunge.adapters import local_files, maintenance, state

    original_connect = sqlite3.connect
    factory = observed_factory(recorder)

    def connect(*args, **kwargs):
        return original_connect(*args, **kwargs, factory=factory)

    def wrapper(original, name):
        def call(*args, **kwargs):
            with recorder.phase(name) as event:
                if name in ("handler_prepare", "migration"):
                    step = args[0] if name == "handler_prepare" else args[1]
                    event.update(from_version=step.from_version, to_version=step.to_version)
                result = original(*args, **kwargs)
                if name == "validation":
                    event["version"] = result[0]
                    event["full"] = kwargs["full"]
                if name == "handler_prepare" and result is not None:
                    handler = result.apply

                    def apply(connection):
                        with recorder.phase("backfill"):
                            return handler(connection)

                    result = replace(result, apply=apply)
                return result

        return call

    targets = [
        (module, name, label)
        for module in (state, maintenance)
        for name, label in (
            ("validate", "validation"),
            ("backup", "backup"),
            ("prepare_migration", "handler_prepare"),
            ("apply_migration", "migration"),
            ("file_sha256", "snapshot_hash"),
        )
    ]
    targets += [
        (local_files, "full_sync", "file_sync"),
        (local_files, "sync_directory", "directory_sync"),
        (maintenance, "sync_directory", "directory_sync"),
    ]
    originals = [(module, name, getattr(module, name)) for module, name, _ in targets]
    with patch.object(sqlite3, "connect", connect):
        try:
            for module, name, label in targets:
                setattr(module, name, wrapper(getattr(module, name), label))
            yield
        finally:
            for module, name, original in originals:
                setattr(module, name, original)


def contents(path):
    result = {}
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as conn:
        for table in ("capability_cache", "execution_plans", "execution_approvals"):
            if not conn.execute("SELECT 1 FROM sqlite_schema WHERE name=?", (table,)).fetchone():
                continue
            digest = hashlib.sha256()
            for row in conn.execute(f"SELECT * FROM {table} ORDER BY 1"):
                digest.update(json.dumps(row, separators=(",", ":"), ensure_ascii=True).encode())
            count, total, largest = conn.execute(
                f"SELECT count(*),sum(length(CAST(payload AS BLOB))),"
                f"max(length(CAST(payload AS BLOB))) FROM {table}"
            ).fetchone()
            result[table] = {
                "rows": count,
                "payload_bytes": total or 0,
                "largest_payload_bytes": largest or 0,
                "row_sha256": digest.hexdigest(),
            }
    return result


def source_pair(root, kind):
    from yorunge.adapters import maintenance
    from yorunge.adapters.state import DB_NAME

    if kind != "stage":
        return root / DB_NAME
    intent = maintenance.read_intent(root)
    return root / ("restore-" + intent.stage_id + maintenance.STAGE_SUFFIX)


def baseline(path, vm):
    from yorunge.adapters import state, state_schema
    from yorunge.adapters.local_files import Deadline

    copied = path.parent.parent / "ddl-only.sqlite3"
    shutil.copy2(path, copied)
    recorder = Recorder(vm)
    with instrument(recorder), recorder.phase("ddl_only_baseline"):
        conn = state.connect(copied, Deadline())
        try:
            conn.execute("BEGIN IMMEDIATE")
            for sql in state_schema.MIGRATIONS[-1].statements:
                conn.execute(sql)
            conn.execute("COMMIT")
        finally:
            conn.close()
    return {
        "events": recorder.events,
        "includes_backfill_or_validation": False,
        "valid_final_store": False,
        "acceptance": "diagnostic_only",
    }


def worker(args):
    from yorunge import api
    from yorunge.adapters import state, state_schema
    from yorunge.domain.errors import YorungeError

    root = Path(args.worker).resolve()
    owner = root.parent.stat()
    marker = root.parent / MARKER
    if (
        not root.parent.name.startswith("p013-migration-profile-")
        or owner.st_uid != os.getuid()
        or stat.S_IMODE(owner.st_mode) != 0o700
        or marker.is_symlink()
        or marker.read_text() != root.name
    ):
        raise ValueError("only the orchestrator's new synthetic store is accepted")
    if args.preview_only:
        started = time.perf_counter_ns()
        confirmation = api.preview_state_recovery(state_dir=root).data.digest
        return {
            "confirmation": confirmation,
            "preview_ms": (time.perf_counter_ns() - started) / 1_000_000,
        }
    source = source_pair(root, args.case)
    before = contents(source)
    comparison = baseline(source, args.vm) if args.case in ("schema-4", "stage", "live") else None
    if args.case in ("stage", "live") and args.confirmation is None:
        raise ValueError("fresh-process recovery requires the preceding preview digest")
    recorder = Recorder(args.vm)
    cpu_before = resource.getrusage(resource.RUSAGE_SELF)
    failure = None
    try:
        with instrument(recorder), recorder.phase("use_case"):
            if args.case.startswith("schema-"):
                api.initialize_state(state_dir=root)
            else:
                api.recover_state(args.confirmation, state_dir=root)
    except YorungeError as error:
        failure = error.code
    cpu_after = resource.getrusage(resource.RUSAGE_SELF)
    pair = root / state.DB_NAME if (root / state.DB_NAME).exists() else source
    after = contents(pair)
    with closing(sqlite3.connect(pair.as_uri() + "?mode=ro&immutable=1", uri=True)) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        # Outside the measured call; never resume/repair after a failed measurement.
        state.validate(conn, state_schema.MIGRATIONS, full=True)
        expiry_rows = (
            conn.execute("SELECT count(*) FROM capability_expiries").fetchone()[0]
            if version == 5
            else None
        )
    return {
        "outcome": failure or "ok",
        "target_reached": version == 5,
        "call_budget_seconds": 5,
        "within_wall_budget": recorder.events[0]["elapsed_ms"] <= 5000,
        "final_version": version,
        "source": before,
        "target": after,
        "payload_rows_unchanged": all(after.get(table) == value for table, value in before.items()),
        "expiry_rows": expiry_rows,
        "post_call_full_validation": "passed",
        "cpu_user_ms": (cpu_after.ru_utime - cpu_before.ru_utime) * 1000,
        "cpu_system_ms": (cpu_after.ru_stime - cpu_before.ru_stime) * 1000,
        "worker_peak_rss_native_through_call": cpu_after.ru_maxrss,
        "vm_progress_interval": 1 if args.vm else None,
        "original_deadline_callback_preserved": True,
        "original_progress_handlers": recorder.deadline_handlers if args.vm else None,
        "delegated_progress_calls": recorder.deadline_calls if args.vm else None,
        "original_progress_intervals": sorted(recorder.original_intervals) if args.vm else None,
        "events": recorder.events,
        "ddl_only_baseline": comparison,
    }


def prepare(root, case, maximum):
    from yorunge.adapters import state, state_schema
    from yorunge.adapters.local_files import Deadline

    seed = runpy.run_path(str(PROJECT / "tests/fixtures/seed_migration_state.py"))["seed"]
    version = int(case[-1]) if case.startswith("schema-") else 4
    source = root if case.startswith("schema-") else root.parent / "source"
    seed(source, version=version, maximum=maximum)
    if source == root:
        return
    with patch.object(state_schema, "MIGRATIONS", state_schema.MIGRATIONS[:4]):
        with state.open_store(source, timeout=60):
            saved = state.backup(
                source, source / state.DB_NAME, Deadline(60), state_schema.MIGRATIONS
            )
    # The old restore is fixture preparation; measured recovery keeps the public 5 s budget.
    fixture = PROJECT / "tests/fixtures/recovery_upgrade_failure.py"
    code = (
        "import runpy; from yorunge.adapters import maintenance as m; "
        "from yorunge.adapters.local_files import Deadline; "
        "m.Deadline=lambda:Deadline(60); runpy.run_path(" + repr(str(fixture)) + ")"
    )
    child = subprocess.run(
        [sys.executable, "-c", code, "old", str(root), case, "4", str(saved)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if child.returncode != 73:
        raise RuntimeError("old synthetic completed pair was not created: " + child.stderr)
    shutil.rmtree(source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", help=argparse.SUPPRESS)
    parser.add_argument("--preview-only", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--confirmation", help=argparse.SUPPRESS)
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--maximum", action="store_true")
    parser.add_argument("--vm", action="store_true")
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cpu-label", default="unknown")
    parser.add_argument("--disk-type", default="unknown")
    args = parser.parse_args()
    if sys.platform not in ("darwin", "linux"):
        parser.error("macOS/Linux local synthetic profiling is required")
    if args.worker:
        print(json.dumps(worker(args)))
        return 0
    if Path.cwd().resolve() != PROJECT:
        parser.error("run from the repository root")
    if (
        args.samples < 3
        or args.output is None
        or args.output.exists()
        or args.output.is_symlink()
        or not args.output.parent.is_dir()
    ):
        parser.error("at least three samples and a new --output file are required")
    work = PROJECT / ".local"
    work.mkdir(exist_ok=True)
    sources = {
        str(p.relative_to(PROJECT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [
            *sorted((PROJECT / "src").rglob("*.py")),
            PROJECT / "tests/fixtures/seed_migration_state.py",
            PROJECT / "tests/fixtures/seed_capability_cache.py",
            PROJECT / "tests/fixtures/recovery_upgrade_failure.py",
            Path(__file__),
        ]
    }
    sources["tests/conftest.py"] = hashlib.sha256(
        (PROJECT / "tests/conftest.py").read_bytes()
    ).hexdigest()
    runs = []
    for index in range(args.samples):
        with tempfile.TemporaryDirectory(prefix="p013-migration-profile-", dir=work) as folder:
            root = Path(folder).resolve() / "target"
            prepare(root, args.case, args.maximum)
            marker = root.parent / MARKER
            marker.write_text(root.name)
            command = [
                sys.executable,
                str(Path(__file__).resolve()),
                "--worker",
                str(root),
                "--case",
                args.case,
                *(["--vm"] if args.vm else []),
            ]
            preview = {"preview_ms": None}
            if args.case in ("stage", "live"):
                viewed = subprocess.run(
                    [*command, "--preview-only"], capture_output=True, text=True, timeout=120
                )
                if viewed.returncode != 0:
                    raise RuntimeError("synthetic preview failed: " + viewed.stderr)
                preview = json.loads(viewed.stdout)
                command += ["--confirmation", preview["confirmation"]]
            child = subprocess.run(command, capture_output=True, text=True, timeout=120)
            if child.returncode != 0:
                raise RuntimeError("synthetic worker failed: " + child.stderr)
            runs.append(json.loads(child.stdout))
            runs[-1]["preview_ms"] = preview["preview_ms"]
            runs[-1]["preview_within_budget"] = (
                preview["preview_ms"] is None or preview["preview_ms"] <= 5000
            )
            print(f"{args.case} sample {index + 1}: {runs[-1]['outcome']}", file=sys.stderr)
    unchanged = all(
        hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() == sha
        for name, sha in sources.items()
    )
    report = {
        "schema_version": 1,
        "source_reference": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "case": args.case,
        "maximum": args.maximum,
        "vm_instrumented": args.vm,
        "samples": args.samples,
        "vm_method": "progress callbacks at interval 1; original deadline cadence preserved",
        "phase_time_method": "inclusive; parent IDs identify nesting; use_case is total",
        "fixture_preparation_budget_seconds": 60,
        "python": sys.version,
        "package_versions": {
            "pydantic": importlib.metadata.version("pydantic"),
            "sqlite": sqlite3.sqlite_version,
        },
        "platform": platform.platform(),
        "cpu": args.cpu_label,
        "disk_type": args.disk_type,
        "installation": "editable .venv; lock SHA recorded",
        "lock_sha256": hashlib.sha256((PROJECT / "uv.lock").read_bytes()).hexdigest(),
        "command": [
            ".venv/bin/python",
            str(Path(__file__).resolve().relative_to(PROJECT)),
            *sys.argv[1:],
        ],
        "source_sha256": sources,
        "source_unchanged_during_runs": unchanged,
        "runs": runs,
    }
    with args.output.open("x") as output:
        output.write(json.dumps(report, indent=2) + "\n")
    return (
        0
        if unchanged
        and all(
            r["outcome"] == "ok"
            and r["target_reached"]
            and r["within_wall_budget"]
            and r["preview_within_budget"]
            and r["payload_rows_unchanged"]
            for r in runs
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
