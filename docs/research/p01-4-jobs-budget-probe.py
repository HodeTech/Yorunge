"""Measure fresh installed jobs processes on new, disposable normal/dense fixtures."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import resource
import runpy
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]


def environment():
    value = dict(os.environ)
    for name in tuple(value):
        if name.startswith("PYTHON") or name == "VIRTUAL_ENV":
            value.pop(name)
    value.update(PYTHONHASHSEED="0", PYTHONNOUSERSITE="1")
    return value


def sources():
    paths = [
        *sorted((PROJECT / "src").rglob("*.py")),
        PROJECT / "pyproject.toml",
        PROJECT / "uv.lock",
        PROJECT / "tests/conftest.py",
        *(
            PROJECT / "tests/fixtures" / name
            for name in (
                "seed_jobs.py",
                "seed_operation_state.py",
                "seed_migration_state.py",
                "seed_capability_cache.py",
            )
        ),
        PROJECT / "docs/research/p01-4-operation-budget-probe.py",
        Path(__file__).resolve(),
    ]
    return {str(p.relative_to(PROJECT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def installation(prefix, expected):
    import yorunge

    package = Path(yorunge.__file__).resolve().parent
    if Path(sys.prefix).resolve() != prefix.resolve() or not package.is_relative_to(
        prefix.resolve()
    ):
        raise ValueError("isolated installed runtime origin required")
    for name, digest in expected.items():
        if name.startswith("src/yorunge/"):
            path = package / name.removeprefix("src/yorunge/")
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError("installed source differs from measured candidate")
    packages = {dist.metadata["Name"]: dist.version for dist in importlib.metadata.distributions()}
    if any(name.lower() in {"pytest", "mypy", "ruff", "types-pyyaml"} for name in packages):
        raise ValueError("runtime contains development tools")
    return dict(
        label="installed wheel; separate frozen runtime venv",
        python=sys.version,
        packages=packages,
        source_origin_matches=True,
        prefix_relative=str(prefix.relative_to(PROJECT)),
    )


def manifest(path):
    parent = path.parent.resolve()
    info = parent.stat()
    if (
        not parent.name.startswith("p014-jobs-budget-")
        or path.is_symlink()
        or parent.parent != (PROJECT / ".local").resolve()
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise ValueError("new orchestrator-owned fixture required")
    return json.loads(path.read_text())


def worker(args):
    saved = manifest(args.manifest)
    provenance = installation(Path(saved["prefix"]), saved["sources"])
    if args.worker == "origin":
        return provenance
    from yorunge import api

    root = args.manifest.parent / args.layout
    if args.layout not in saved["fixtures"]:
        raise ValueError("known marked fixture required")
    identifier = saved["fixtures"][args.layout]
    helpers = runpy.run_path(str(PROJECT / "docs/research/p01-4-operation-budget-probe.py"))
    recorder = helpers["Recorder"]()
    with helpers["instrument"](recorder), recorder.phase("query"):
        result = (
            api.list_jobs(state_dir=root)
            if args.action == "list"
            else api.show_job(identifier, state_dir=root)
        )
    maximum = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return dict(
        peak_rss_bytes=maximum if sys.platform == "darwin" else maximum * 1024,
        sqlite_statements=recorder.statements,
        progress_quantum=sorted(recorder.intervals),
        sampled_vm_steps=recorder.nominal_steps,
        progress_calls=recorder.callbacks,
        delegated_deadline_calls=recorder.delegated,
        diagnostic_ms=recorder.events[0]["elapsed_ms"],
        result_bytes=len(result.model_dump_json().encode()),
    )


def measure(command, cwd, env, action, identifier, dense):
    started = time.perf_counter_ns()
    child = subprocess.run(command, cwd=cwd, env=env, capture_output=True, timeout=10, check=True)
    elapsed = (time.perf_counter_ns() - started) / 1_000_000
    if child.stderr:
        raise ValueError("unexpected stderr in measured jobs query")
    value = json.loads(child.stdout)
    if (
        value["schema_version"] != 1
        or value["status"] != "completed"
        or value["operation_id"] is not None
        or value["warnings"] != ["local_history_only"]
    ):
        raise ValueError("query result envelope mismatch")
    data = value["data"]
    if action == "list":
        if len(data["jobs"]) != (50 if dense else 1) or bool(data["next_cursor"]) != dense:
            raise ValueError("query must read the expected real fixture")
    elif data["operation"]["operation_id"] != identifier or len(data["attempts"]) != (
        16 if dense else 1
    ):
        raise ValueError("show fixture mismatch")
    return elapsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=("origin", "diagnostic"), help=argparse.SUPPRESS)
    parser.add_argument("--manifest", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--layout", help=argparse.SUPPRESS)
    parser.add_argument("--action", choices=("list", "show"), help=argparse.SUPPRESS)
    parser.add_argument("--python", type=Path)
    parser.add_argument("--command", type=Path)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--disk-type", default="unknown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args), allow_nan=False))
        return 0
    if (
        Path.cwd().resolve() != PROJECT
        or args.samples < 30
        or args.output is None
        or args.output.exists()
        or args.output.is_symlink()
        or not args.output.parent.is_dir()
        or args.python is None
        or args.command is None
        or args.wheel is None
        or args.python.parent.resolve() != args.command.parent.resolve()
    ):
        parser.error("repository CWD, isolated Python/console/wheel and new output required")
    # Keep the venv launcher path (resolving its symlink would bypass sys.prefix),
    # but make it independent of the disposable child working directory.
    args.python, args.command, args.wheel = (
        path.absolute() for path in (args.python, args.command, args.wheel)
    )
    import yorunge

    if Path(yorunge.__file__).resolve() != (PROJECT / "src/yorunge/__init__.py").resolve():
        raise ValueError("fixture preparation requires repository runtime")
    sys.path.insert(0, str(PROJECT))
    from tests.fixtures.seed_jobs import seed

    helpers = runpy.run_path(str(PROJECT / "docs/research/p01-4-operation-budget-probe.py"))
    before, runs, volumes = sources(), [], {}
    env = environment()
    with tempfile.TemporaryDirectory(prefix="p014-jobs-budget-", dir=PROJECT / ".local") as folder:
        work = Path(folder).resolve()
        saved = dict(prefix=str(args.python.parent.parent.resolve()), sources=before, fixtures={})
        marker = work / "manifest.json"
        marker.write_text(json.dumps(saved))

        def child(kind, *options):
            process = subprocess.run(
                [
                    str(args.python),
                    "-I",
                    str(Path(__file__).resolve()),
                    "--worker",
                    kind,
                    "--manifest",
                    str(marker),
                    *options,
                ],
                cwd=work,
                env=env,
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            return json.loads(process.stdout)

        provenance = child("origin")
        for dense in (False, True):
            layout = "dense" if dense else "normal"
            root = work / layout
            identifier = seed(root, dense=dense)
            saved["fixtures"][layout] = identifier
            marker.write_text(json.dumps(saved))
            volumes[layout] = helpers["contents"](root)
            reader = sqlite3.connect(
                (root / "state.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
            )
            try:
                volumes[layout]["largest_payload_bytes"] = {
                    table: reader.execute(
                        f"SELECT max(length(CAST(payload AS BLOB))) FROM {table}"
                    ).fetchone()[0]
                    for table in (
                        "operations",
                        "operation_attempts",
                        "operation_outcomes",
                        "execution_plans",
                    )
                }
                volumes[layout]["database_bytes"] = (root / "state.sqlite3").stat().st_size
            finally:
                reader.close()
            for action in ("list", "show"):
                command = [
                    str(args.command),
                    "jobs",
                    action,
                    "--state-dir",
                    str(root),
                    "--output",
                    "json",
                ]
                if action == "show":
                    command += ["--operation-id", identifier]
                first = measure(command, work, env, action, identifier, dense)
                warmup = [measure(command, work, env, action, identifier, dense) for _ in range(3)]
                samples = [
                    measure(command, work, env, action, identifier, dense)
                    for _ in range(args.samples)
                ]
                p95 = sorted(samples)[math.ceil(len(samples) * 0.95) - 1]
                diagnostic = child("diagnostic", "--layout", layout, "--action", action)
                runs.append(
                    dict(
                        layout=layout,
                        action=action,
                        first_ms=first,
                        warmup_ms=warmup,
                        samples_ms=samples,
                        p95_ms=p95,
                        budget_ms=200,
                        passed=p95 <= 200,
                        diagnostic=diagnostic,
                    )
                )
                print(f"{layout} {action}: p95 {p95:.3f} ms", file=sys.stderr, flush=True)
            after = helpers["contents"](root)
            if after != {
                key: value
                for key, value in volumes[layout].items()
                if key not in {"largest_payload_bytes", "database_bytes"}
            }:
                raise ValueError("read-only jobs changed fixture state")
    unchanged = before == sources()
    report = dict(
        schema_version=1,
        source_base_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        source_sha256=before,
        source_unchanged=unchanged,
        installation=provenance,
        wheel_sha256=hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
        platform=platform.platform(),
        machine=platform.machine(),
        sqlite=sqlite3.sqlite_version,
        cpu=subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
        if sys.platform == "darwin"
        else platform.processor() or "unknown",
        disk_type=args.disk_type,
        fixture=volumes,
        runs=runs,
        measurement_note=(
            "first separate; three warmups; >=30 fresh processes; nearest-rank p95; "
            "no OS cache flush; setup/hash/diagnostic outside timed commands; all samples retained"
        ),
    )
    with args.output.open("x") as output:
        json.dump(report, output, indent=2, allow_nan=False)
        output.write("\n")
    return 0 if unchanged and all(run["passed"] for run in runs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
