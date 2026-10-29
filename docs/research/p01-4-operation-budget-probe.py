"""Fresh-process operation validation/reset budgets on disposable quota-sized stores."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[2]
MARKER = "synthetic-p014-operation-budget.json"


def installation():
    import yorunge

    expected = PROJECT / "src/yorunge/__init__.py"
    if Path(yorunge.__file__).resolve() != expected.resolve():
        raise RuntimeError("unexpected runtime import origin")
    if Path(sys.prefix).resolve() != (PROJECT / ".venv").resolve():
        raise RuntimeError("repository .venv interpreter required")
    return dict(
        label="editable .venv; repository frozen uv environment",
        interpreter=str(Path(sys.executable).relative_to(PROJECT)),
        import_origin=str(expected.relative_to(PROJECT)),
    )


def sources():
    paths = [
        *sorted((PROJECT / "src").rglob("*.py")),
        PROJECT / "tests/conftest.py",
        *(
            PROJECT / "tests/fixtures" / name
            for name in (
                "seed_operation_state.py",
                "seed_migration_state.py",
                "seed_capability_cache.py",
            )
        ),
        Path(__file__).resolve(),
    ]
    return {
        str(path.relative_to(PROJECT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def contents(root):
    connection = sqlite3.connect(
        (root / "state.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    )
    try:
        volumes = {}
        for table in (
            "capability_cache",
            "execution_plans",
            "execution_approvals",
            "operations",
            "operation_attempts",
            "operation_events",
            "operation_outcomes",
        ):
            count, size = connection.execute(
                f"SELECT count(*),coalesce(sum(length(CAST(payload AS BLOB))),0) FROM {table}"
            ).fetchone()
            volumes[table] = dict(rows=count, payload_bytes=size)
        hashes = {}
        for table, order in (
            ("operation_events", "operation_id,sequence"),
            ("operation_outcomes", "operation_id"),
            ("execution_plans", "plan_id"),
            ("execution_approvals", "plan_id"),
        ):
            digest = hashlib.sha256()
            for (payload,) in connection.execute(f"SELECT payload FROM {table} ORDER BY {order}"):
                data = payload.encode("utf-8")
                digest.update(len(data).to_bytes(8, "big"))
                digest.update(data)
            hashes[table] = digest.hexdigest()
        epoch = connection.execute("SELECT identity_epoch FROM state_meta").fetchone()[0]
        leases = connection.execute(
            "SELECT count(*) FROM operations WHERE lease_expires_at IS NOT NULL"
        ).fetchone()[0]
        states = dict(connection.execute("SELECT status,count(*) FROM operations GROUP BY status"))
        return dict(volumes=volumes, hashes=hashes, epoch=epoch, leases=leases, states=states)
    finally:
        connection.close()


class Recorder:
    def __init__(self):
        self.events = []
        self.callbacks = self.nominal_steps = self.statements = self.delegated = 0
        self.intervals = set()

    @contextmanager
    def phase(self, name):
        before, started = self.callbacks, time.perf_counter_ns()
        event = dict(name=name)
        self.events.append(event)
        try:
            yield
            event["outcome"] = "ok"
        except Exception as error:
            event["outcome"] = getattr(error, "code", type(error).__name__)
            raise
        finally:
            event.update(
                elapsed_ms=(time.perf_counter_ns() - started) / 1_000_000,
                progress_callbacks=self.callbacks - before,
            )


@contextmanager
def instrument(recorder):
    from yorunge.adapters import maintenance, state

    original_connect, original_validate = sqlite3.connect, state.validate

    class Connection(sqlite3.Connection):
        def set_progress_handler(self, callback, n=0):
            if callback is None or n <= 0:
                return super().set_progress_handler(callback, n)
            recorder.intervals.add(n)

            def progress():
                recorder.callbacks += 1
                recorder.nominal_steps += n
                recorder.delegated += 1
                return callback()

            # Preserve the native callback quantum and every deadline invocation.
            return super().set_progress_handler(progress, n)

        def execute(self, sql, parameters=()):
            recorder.statements += 1
            if sql in ("COMMIT", "ROLLBACK"):
                with recorder.phase(sql.lower()):
                    return super().execute(sql, parameters)
            return super().execute(sql, parameters)

    def connect(*args, **kwargs):
        return original_connect(*args, **kwargs, factory=Connection)

    def validate(connection, migrations, *, full):
        if not full:
            return original_validate(connection, migrations, full=False)
        with recorder.phase("full_validation"):
            return original_validate(connection, migrations, full=True)

    with (
        patch.object(sqlite3, "connect", connect),
        patch.object(state, "validate", validate),
        patch.object(maintenance, "validate", validate),
    ):
        yield


def worker(root, action, confirmation):
    from yorunge import api
    from yorunge.domain.errors import YorungeError

    installation()
    root = Path(root).resolve()
    parent = root.parent.stat()
    marker = root.parent / MARKER
    if (
        not root.parent.name.startswith("p014-operation-budget-")
        or parent.st_uid != os.getuid()
        or stat.S_IMODE(parent.st_mode) != 0o700
        or marker.is_symlink()
        or json.loads(marker.read_text())["root"] != root.name
    ):
        raise ValueError("only a new orchestrator-owned synthetic store is accepted")
    before = contents(root)
    recorder = Recorder()
    failure, preview = None, None
    baseline_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    try:
        with instrument(recorder), recorder.phase("use_case"):
            if action == "full":
                api.initialize_state(state_dir=root)
            elif action == "preview":
                preview = api.preview_identity_reset(state_dir=root).data
            else:
                api.reset_identity(confirmation, state_dir=root)
    except YorungeError as error:
        failure = error.code
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    after = contents(root)
    elapsed = recorder.events[0]["elapsed_ms"]
    # Public history is immutable across reset; identity/cache/control state may change.
    preserved = before["hashes"] == after["hashes"]
    expected_reset = action != "reset" or (
        after["epoch"] != before["epoch"]
        and after["leases"] == 0
        and after["volumes"]["capability_cache"]["rows"] == 0
    )
    same_volumes = all(
        after["volumes"][table] == value
        for table, value in before["volumes"].items()
        if table not in {"operations", "operation_attempts", "capability_cache"}
    )
    same_rows = all(
        after["volumes"][table]["rows"] == value["rows"]
        for table, value in before["volumes"].items()
        if table != "capability_cache"
    )
    for value in (before, after):
        value.pop("epoch")
    scale = 1 if sys.platform == "darwin" else 1024
    return dict(
        action=action,
        outcome=failure or "ok",
        call_budget_seconds=5,
        elapsed_ms=elapsed,
        within_wall_budget=elapsed <= 5000,
        before=before,
        after=after,
        immutable_history_preserved=preserved,
        immutable_volumes_preserved=same_volumes,
        row_counts_preserved=same_rows,
        reset_effect_confirmed=expected_reset,
        confirmation=preview.digest if preview else None,
        peak_rss_bytes=peak_rss * scale,
        baseline_peak_rss_bytes=baseline_rss * scale,
        vm_progress_callbacks=recorder.callbacks,
        vm_nominal_step_quanta=recorder.nominal_steps,
        vm_count_method=(
            "original progress callbacks times their unchanged quantum; "
            "sampled, not exact instructions"
        ),
        original_progress_intervals=sorted(recorder.intervals),
        deadline_calls=recorder.delegated,
        original_deadline_callback_preserved=True,
        sql_statements=recorder.statements,
        events=recorder.events,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--action", choices=("full", "preview", "reset"), help=argparse.SUPPRESS)
    parser.add_argument("--confirmation", help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--disk-type", default="unknown")
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker, args.action, args.confirmation), allow_nan=False))
        return 0
    if (
        Path.cwd().resolve() != PROJECT
        or args.samples < 3
        or args.output is None
        or args.output.exists()
        or args.output.is_symlink()
        or not args.output.parent.is_dir()
    ):
        parser.error("repository CWD, >=3 samples and a new output path required")
    sys.path.insert(0, str(PROJECT))

    from tests.fixtures.seed_operation_state import seed

    environment = installation()
    before, runs = sources(), []
    work = PROJECT / ".local"
    work.mkdir(exist_ok=True)
    for layout in ("normal", "terminal", "mixed"):
        for sample in range(1, args.samples + 1):
            with tempfile.TemporaryDirectory(prefix="p014-operation-budget-", dir=work) as folder:
                root = Path(folder).resolve() / "state"
                expected = seed(root, layout=layout, maximum=layout != "normal")
                (root.parent / MARKER).write_text(json.dumps(dict(root=root.name)))
                confirmation = None
                for action in ("full", "preview", "reset"):
                    command = [
                        sys.executable,
                        str(Path(__file__).resolve()),
                        "--worker",
                        str(root),
                        "--action",
                        action,
                    ]
                    if confirmation:
                        command += ["--confirmation", confirmation]
                    child = subprocess.run(command, capture_output=True, text=True, timeout=30)
                    if child.returncode:
                        raise RuntimeError("synthetic worker failed: " + child.stderr)
                    result = json.loads(child.stdout)
                    confirmation = result.pop("confirmation") or confirmation
                    result.update(layout=layout, sample=sample, fixture_counts=expected)
                    runs.append(result)
                    print(
                        f"{layout} {sample} {action}: {result['outcome']} "
                        f"{result['elapsed_ms']:.1f} ms",
                        file=sys.stderr,
                        flush=True,
                    )
                    if action == "preview" and confirmation is None:
                        break
    unchanged = before == sources()
    report = dict(
        schema_version=1,
        source_base_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        source_sha256=before,
        source_unchanged=unchanged,
        platform=platform.platform(),
        machine=platform.machine(),
        cpu=subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
        if sys.platform == "darwin"
        else platform.processor() or "unknown",
        python=sys.version,
        sqlite=sqlite3.sqlite_version,
        disk_type=args.disk_type,
        installation=environment,
        measurement_note=(
            "fresh workers; setup and row hashes outside call; "
            "OS/disk caches not flushed; all samples retained"
        ),
        runs=runs,
    )
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2, allow_nan=False)
        output.write("\n")
    return (
        0
        if unchanged
        and len(runs) == 9 * args.samples
        and all(
            r["outcome"] == "ok"
            and r["within_wall_budget"]
            and r["immutable_history_preserved"]
            and r["immutable_volumes_preserved"]
            and r["row_counts_preserved"]
            and r["reset_effect_confirmed"]
            for r in runs
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
