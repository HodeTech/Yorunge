"""Measure installed local jobs commands against fresh disposable synthetic stores."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import sqlite3
import statistics
import subprocess
import sys
import time
import tomllib
from contextlib import closing
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TABLES = (
    "operations",
    "operation_attempts",
    "operation_events",
    "operation_outcomes",
    "execution_plans",
    "execution_approvals",
    "capability_cache",
)
PROBE = """
import hashlib
import importlib.metadata as metadata
import json
import platform
import sqlite3
import sys
from pathlib import Path
import yorunge
prefix = Path(sys.prefix).resolve()
root = Path(yorunge.__file__).resolve().parent
if sys.prefix == sys.base_prefix or not root.is_relative_to(prefix):
    raise ValueError('installed product must originate inside an isolated venv')
dist = metadata.distribution('yorunge')
if not Path(dist.locate_file('')).resolve().is_relative_to(prefix):
    raise ValueError('distribution metadata escaped its isolated environment')
if not any(ep.group == 'console_scripts' and ep.name == 'yorunge'
           and ep.value == 'yorunge.cli:main' for ep in dist.entry_points):
    raise ValueError('installed console metadata mismatch')
console_name = 'yorunge.exe' if sys.platform == 'win32' else 'yorunge'
console = Path(sys.executable).absolute().parent / console_name
if not console.is_file() or console.is_symlink() or not console.resolve().is_relative_to(prefix):
    raise ValueError('console must be a regular file in the runtime venv')
files = sorted(root.rglob('*.py'))
if not files or any(p.is_symlink() or not p.resolve().is_relative_to(prefix) for p in files):
    raise ValueError('installed Python sources escaped their runtime venv')
packages = {}
for item in metadata.distributions():
    name = item.metadata['Name'].lower().replace('_', '-').replace('.', '-')
    if name in packages:
        raise ValueError('duplicate installed distribution')
    packages[name] = item.version
print(json.dumps({
    'python': sys.version, 'executable': sys.executable, 'prefix': str(prefix),
    'platform': platform.platform(), 'machine': platform.machine(),
    'sqlite': sqlite3.sqlite_version, 'packages': packages,
    'product_origin': str(root), 'product_version': dist.version,
    'console': str(console), 'console_sha256': hashlib.sha256(console.read_bytes()).hexdigest(),
    'installed_source_sha256': {
        'yorunge/' + str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in files
    },
}))
"""
VALIDATE = """
import json
import sys
from yorunge.domain.models import Result
from yorunge.domain.operations import JobsPage, JobView
request = json.load(sys.stdin)
model = Result[JobsPage] if request['action'] == 'list' else Result[JobView]
for output in request['outputs']:
    model.model_validate_json(output)
print(json.dumps({'validated': len(request['outputs'])}))
"""
SEED = """
import sys
from pathlib import Path
project, root, layout = sys.argv[1:]
sys.path[:0] = [str(Path(project) / 'src'), project]
from tests.fixtures.seed_jobs import seed
seed(Path(root), dense=layout == 'dense')
"""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def environment() -> dict[str, str]:
    result = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("PYTHON") and key != "VIRTUAL_ENV"
    }
    result.update(PYTHONNOUSERSITE="1")
    return result


def run(
    command: list[str], *, cwd: Path, content: str | None = None, timeout: int = 30
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment(),
        input=content,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=True,
        timeout=timeout,
    )


def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate JSON key")
    return result


def reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON value: {value}")


def decode(content: str) -> dict[str, Any]:
    value = json.loads(content, object_pairs_hook=object_pairs, parse_constant=reject_constant)
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def source(project: Path) -> dict[str, Any]:
    for directory in (project / name for name in ("src", "scripts", "tests")):
        if directory.is_symlink() or any(path.is_symlink() for path in directory.rglob("*")):
            raise ValueError("public measurement sources must not contain symlinks")
    paths = sorted(project.glob("*.py"))
    paths += sorted((project / "src").rglob("*.py"))
    paths += sorted((project / "scripts").glob("*.py"))
    paths += sorted((project / "tests").rglob("*.py"))
    paths += [
        project / name
        for name in (
            "pyproject.toml",
            "uv.lock",
            "examples/profile.toml",
            ".github/workflows/checks.yml",
        )
    ]
    if any(path.is_symlink() for path in paths):
        raise ValueError("measured source inputs must not be symlinks")
    revision = run(["git", "rev-parse", "HEAD"], cwd=project).stdout.strip()
    return {
        "commit": revision,
        "source_sha256": {str(path.relative_to(project)): digest(path) for path in paths},
    }


def prepare_fixture(project: Path, workspace: Path, layout: str) -> None:
    """Import checked fixture sources with a fresh bytecode namespace per layout."""
    run(
        [
            sys.executable,
            "-X",
            f"pycache_prefix={workspace / 'fixture-pycache' / layout}",
            "-c",
            SEED,
            str(project),
            str(workspace / layout),
            layout,
        ],
        cwd=workspace,
        timeout=600,
    )


def locked_runtime(project: Path) -> dict[str, str]:
    lock = tomllib.loads((project / "uv.lock").read_text())
    packages = {item["name"]: item for item in lock["package"]}
    pending, versions = ["yorunge"], {}
    while pending:
        name = pending.pop()
        if name in versions:
            continue
        item = packages[name]
        versions[name] = item["version"]
        pending.extend(dependency["name"] for dependency in item.get("dependencies", []))
    return versions


def runtime_snapshot(python: Path, cwd: Path) -> dict[str, Any]:
    return decode(run([str(python), "-I", "-c", PROBE], cwd=cwd).stdout)


def runtime(python: Path, project: Path, cwd: Path) -> dict[str, Any]:
    value = runtime_snapshot(python, cwd)
    expected = {
        str(path.relative_to(project / "src")): digest(path)
        for path in sorted((project / "src/yorunge").rglob("*.py"))
    }
    if not expected or value["installed_source_sha256"] != expected:
        raise ValueError("every installed product Python source must match the checkout")
    if value["packages"] != locked_runtime(project):
        raise ValueError("runtime venv must contain exactly frozen runtime packages; no dev tools")
    if Path(value["console"]).absolute().parent != python.absolute().parent:
        raise ValueError("console and explicit interpreter must belong to the same runtime venv")
    return value


def fixture(state: Path, layout: str) -> dict[str, Any]:
    database = state / "state.sqlite3"
    if layout not in {"normal", "dense"} or database.is_symlink() or not database.is_file():
        raise ValueError("a fresh normal or dense synthetic jobs fixture is required")
    counts = (
        (1, 1, 3, 0, 1, 1, 1)
        if layout == "normal"
        else (1024, 16384, 262144, 1024, 1024, 1024, 1024)
    )
    rows = {}
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        for table, expected in zip(TABLES, counts, strict=True):
            count, total, largest = db.execute(
                f"SELECT count(*),coalesce(sum(length(CAST(payload AS BLOB))),0),"
                f"coalesce(max(length(CAST(payload AS BLOB))),0) FROM {table}"
            ).fetchone()
            if count != expected or (count and (total <= 0 or largest <= 0)):
                raise ValueError(f"invalid {layout} fixture row count or payload: {table}")
            rows[table] = {
                "records": count,
                "payload_bytes": total,
                "largest_record_bytes": largest,
            }
        selected = db.execute(
            "SELECT payload FROM operations ORDER BY created_at,operation_id LIMIT 50"
        ).fetchall()
        summaries = [decode(payload)["summary"] for (payload,) in selected]
        target = summaries[0]
        identifier = target["operation_id"]
        attempts = [
            decode(payload)
            for (payload,) in db.execute(
                "SELECT payload FROM operation_attempts WHERE operation_id=? ORDER BY number",
                (identifier,),
            )
        ]
        outcomes = db.execute(
            "SELECT payload FROM operation_outcomes WHERE operation_id=?", (identifier,)
        ).fetchall()
    status, delivery = ("running", "pending") if layout == "normal" else ("succeeded", "complete")
    if any(
        item["status"] != status
        or item["execution_status"] != status
        or item["delivery_status"] != delivery
        or item["attempt_count"] != (1 if layout == "normal" else 16)
        or not re.fullmatch(r"[0-9a-f]{64}", item["plan_digest"])
        for item in summaries
    ):
        raise ValueError("fixture status, digest or attempt count mismatch")
    return {
        "rows": rows,
        "database_bytes": database.stat().st_size,
        "database_sha256": digest(database),
        "list_summaries": summaries,
        "has_next_cursor": layout == "dense",
        "show_summary": target,
        "show_attempts": attempts,
        "show_outcome": decode(outcomes[0][0]) if outcomes else None,
    }


def validate_output(output: str, action: str, expected: dict[str, Any]) -> None:
    value = decode(output)
    if (
        value.get("schema_version") != 1
        or value.get("operation_id") is not None
        or value.get("status") != "completed"
        or value.get("warnings") != ["local_history_only"]
    ):
        raise ValueError("jobs benchmark requires a completed local-history result")
    data = value["data"]
    if action == "list":
        if (
            data["jobs"] != expected["list_summaries"]
            or (isinstance(data.get("next_cursor"), str) and bool(data["next_cursor"]))
            != expected["has_next_cursor"]
        ):
            raise ValueError("jobs list returned incorrect jobs or pagination")
        if not expected["has_next_cursor"] and data.get("next_cursor") is not None:
            raise ValueError("normal jobs list must have no next cursor")
    elif action == "show":
        if (
            data["operation"] != expected["show_summary"]
            or data["plan"]["digest"] != expected["show_summary"]["plan_digest"]
            or data["attempts"] != expected["show_attempts"]
            or data["outcome"] != expected["show_outcome"]
        ):
            raise ValueError("jobs show returned incorrect job, digest, attempts or outcome")
    else:
        raise ValueError("unknown jobs benchmark action")


def measure(command: list[str], *, cwd: Path) -> tuple[float, str]:
    start = time.perf_counter()
    result = run(command, cwd=cwd, timeout=10)
    elapsed = (time.perf_counter() - start) * 1000
    if result.stderr:
        raise ValueError("successful jobs command emitted unexpected stderr")
    if not math.isfinite(elapsed) or elapsed <= 0:
        raise ValueError("process wall measurement must be positive and finite")
    return elapsed, result.stdout


def summarize(samples: list[float]) -> dict[str, Any]:
    if len(samples) < 30 or any(not math.isfinite(item) or item <= 0 for item in samples):
        raise ValueError("at least 30 positive finite process samples are required")
    p95 = sorted(samples)[math.ceil(len(samples) * 0.95) - 1]
    return {
        "samples_ms": samples,
        "median_ms": statistics.median(samples),
        "p95_ms": p95,
        "budget_ms": 200,
        "passed": p95 <= 200,
    }


def measure_case(
    python: Path,
    console: Path,
    workspace: Path,
    layout: str,
    action: str,
    expected: dict[str, Any],
    count: int,
) -> dict[str, Any]:
    command = [str(python), "-I", str(console), "jobs", action]
    if action == "list":
        command.extend(("--limit", "50"))
    else:
        command.extend(("--operation-id", expected["show_summary"]["operation_id"]))
    command.extend(("--state-dir", str(workspace / layout), "--output", "json"))
    times, outputs = [], []
    for _ in range(count + 4):
        elapsed, output = measure(command, cwd=workspace)
        validate_output(output, action, expected)
        times.append(elapsed)
        outputs.append(output)
    typed = decode(
        run(
            [str(python), "-I", "-c", VALIDATE],
            cwd=workspace,
            content=json.dumps({"action": action, "outputs": outputs}),
        ).stdout
    )
    if typed != {"validated": count + 4}:
        raise ValueError("installed typed result validation did not cover every process")
    return {
        "layout": layout,
        "action": action,
        "command": command,
        "first_process_ms": times[0],
        "warmups_ms": times[1:4],
        **summarize(times[4:]),
        "typed_stdout_verified": True,
        "verified_processes": len(outputs),
        "stdout_sha256": [hashlib.sha256(item.encode()).hexdigest() for item in outputs],
        "expected_list_rows": len(expected["list_summaries"]) if action == "list" else None,
        "expected_operation_id": expected["show_summary"]["operation_id"]
        if action == "show"
        else None,
        "expected_plan_digest": expected["show_summary"]["plan_digest"]
        if action == "show"
        else None,
    }


def cpu_label() -> str:
    if sys.platform == "linux":
        try:
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.startswith("model name") and ":" in line:
                    return line.split(":", 1)[1].strip() or "unknown"
        except OSError:
            pass
    if sys.platform == "darwin":
        try:
            return (
                subprocess.check_output(
                    ["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"], text=True, timeout=5
                ).strip()
                or "unknown"
            )
        except (OSError, subprocess.SubprocessError):
            pass
    return platform.processor() or "unknown"


def validate_inputs(workspace: Path, output: Path, samples: int, wheel: Path | None) -> None:
    if samples < 30:
        raise ValueError("at least 30 samples are required")
    if (
        output.exists()
        or output.is_symlink()
        or not output.parent.is_dir()
        or output.parent.resolve() != output.parent.absolute()
    ):
        raise ValueError("output must be a new file in an existing directory")
    if workspace.exists() or workspace.is_symlink():
        raise ValueError("workspace must be new; never use an existing state store")
    if workspace.parent.resolve() != workspace.parent.absolute():
        raise ValueError("workspace parent must not contain symlinks")
    if wheel is not None and (wheel.is_symlink() or not wheel.is_file()):
        raise ValueError("wheel must be an existing regular artifact")


def check(
    python: Path,
    workspace: Path,
    output: Path,
    *,
    samples: int,
    wheel: Path | None,
    cpu: str,
    disk: str,
) -> int:
    validate_inputs(workspace, output, samples, wheel)
    workspace.mkdir(mode=0o700)
    before = source(ROOT)
    installed_before = runtime(python, ROOT, workspace)
    wheel_before = digest(wheel) if wheel else None
    fixtures = {}
    for layout in ("normal", "dense"):
        prepare_fixture(ROOT, workspace, layout)
        fixtures[layout] = fixture(workspace / layout, layout)
    runs = [
        measure_case(
            python,
            Path(installed_before["console"]),
            workspace,
            layout,
            action,
            fixtures[layout],
            samples,
        )
        for layout in ("normal", "dense")
        for action in ("list", "show")
    ]
    after = source(ROOT)
    installed_after = runtime_snapshot(python, workspace)
    fixture_after = {layout: fixture(workspace / layout, layout) for layout in fixtures}
    unchanged = (
        before == after and installed_before == installed_after and fixtures == fixture_after
    )
    unchanged = unchanged and (wheel is None or digest(wheel) == wheel_before)
    report = {
        "schema_version": 1,
        "kind": "jobs",
        "source_commit": before["commit"],
        "samples_per_command": samples,
        "method": "first process separately; three warmups; all separate process samples retained; "
        "nearest-rank p95; absolute 200 ms per case; no outlier removal",
        "cold_method": "first command process; OS/disk caches uncontrolled; not a cold boot",
        "validation_method": "strict JSON and SQLite fixture expectations for every output; "
        "installed Result[JobsPage|JobView] validation outside measured process intervals",
        "environment": {
            "runtime": installed_before,
            "cpu": cpu,
            "disk_type": disk,
            "runner_image": {key: os.environ.get(key) for key in ("ImageOS", "ImageVersion")},
        },
        "fixtures": fixtures,
        "runs": runs,
        "provenance": {
            "source_before": before,
            "source_after": after,
            "installed_before": installed_before,
            "installed_after": installed_after,
            "wheel_sha256": wheel_before,
            "wheel_path": str(wheel) if wheel else None,
            "source_unchanged_during_measurement": before == after,
            "installed_unchanged_during_measurement": installed_before == installed_after,
            "fixtures_unchanged_during_measurement": fixtures == fixture_after,
            "unchanged": unchanged,
            "isolated_python": True,
            "fixture_preparation_python": sys.executable,
            "fixture_preparation": "checkout fixture and source imports outside measured runtime; "
            "installed product sources matched before and after",
        },
        "passed": unchanged and all(item["passed"] for item in runs),
    }
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    with output.open("x", encoding="utf-8") as destination:
        destination.write(encoded)
    print(encoded, end="")
    return 0 if report["passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python", type=Path, required=True, help="Installed runtime-only interpreter"
    )
    parser.add_argument("--workspace", type=Path, required=True, help="New disposable workspace")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument(
        "--wheel", type=Path, help="Optional installed wheel artifact for provenance"
    )
    parser.add_argument("--cpu-label", default=cpu_label())
    parser.add_argument("--disk-type", default="unknown")
    args = parser.parse_args()
    try:
        return check(
            args.python.absolute(),
            args.workspace.absolute(),
            args.output.absolute(),
            samples=args.samples,
            wheel=args.wheel.absolute() if args.wheel else None,
            cpu=args.cpu_label,
            disk=args.disk_type,
        )
    except (ValueError, FileExistsError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
