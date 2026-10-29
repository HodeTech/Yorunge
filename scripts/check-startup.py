"""Prepare isolated locked wheel environments and compare startup on one host."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROBE = """
import importlib.metadata as metadata
import json
import sys
from pathlib import Path
import yorunge
if not Path(yorunge.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()):
    raise RuntimeError('benchmark import escaped its isolated environment')
print(json.dumps({'python': sys.version, 'packages': {
    dist.metadata['Name']: dist.version for dist in metadata.distributions()
}}))
"""


@dataclass(frozen=True)
class Prepared:
    project: Path
    python: Path
    console: Path
    wheel_sha256: str
    runtime: dict[str, object]


def environment() -> dict[str, str]:
    result = dict(os.environ)
    for key in tuple(result):
        if key.startswith("PYTHON") or key == "VIRTUAL_ENV":
            result.pop(key)
    # Only synthetic benchmark processes inherit this setting; product defaults do not change.
    result.update(PYTHONHASHSEED="0", PYTHONNOUSERSITE="1")
    return result


def run(
    command: list[str], *, cwd: Path, accepted: tuple[int, ...] = (0,)
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command, cwd=cwd, env=environment(), capture_output=True, text=True, timeout=180
    )
    if result.returncode not in accepted:
        raise subprocess.CalledProcessError(
            result.returncode, command, result.stdout, result.stderr
        )
    return result


def revision(project: Path) -> str | None:
    top = run(["git", "rev-parse", "--show-toplevel"], cwd=project, accepted=(0, 128))
    if top.returncode == 0 and Path(top.stdout.strip()).resolve() == project:
        return run(["git", "rev-parse", "HEAD"], cwd=project).stdout.strip()
    return None


def source(project: Path) -> dict[str, object]:
    paths = sorted((project / "src").rglob("*.py"))
    paths += sorted((project / "scripts").glob("*.py"))
    paths += [
        project / name
        for name in (
            "pyproject.toml",
            "uv.lock",
            "examples/profile.toml",
            ".github/workflows/checks.yml",
            "tests/fixtures/seed_capability_cache.py",
        )
    ]
    hashes = {
        str(path.relative_to(project)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }
    return {"commit": revision(project), "source_sha256": hashes}


def prepare(project: Path, work: Path, uv: Path) -> Prepared:
    work.mkdir()
    requirements = work / "runtime.txt"
    run(
        [
            str(uv),
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--output-file",
            str(requirements),
        ],
        cwd=project,
    )
    run([str(uv), "build", "--wheel", "--out-dir", str(work / "dist")], cwd=project)
    wheels = list((work / "dist").glob("*.whl"))
    if len(wheels) != 1 or not wheels[0].name.startswith("yorunge-"):
        raise ValueError("one freshly built yorunge wheel is required")
    venv = work / "env"
    run([str(uv), "venv", str(venv), "--python", sys.executable], cwd=work)
    binaries = venv / ("Scripts" if os.name == "nt" else "bin")
    python = binaries / ("python.exe" if os.name == "nt" else "python")
    console = binaries / ("yorunge.exe" if os.name == "nt" else "yorunge")
    run(
        [
            str(uv),
            "pip",
            "install",
            "--python",
            str(python),
            "--require-hashes",
            "-r",
            str(requirements),
        ],
        cwd=work,
    )
    run([str(uv), "pip", "install", "--python", str(python), "--no-deps", str(wheels[0])], cwd=work)
    runtime = json.loads(run([str(python), "-c", PROBE], cwd=work.parent).stdout)
    if not isinstance(runtime, dict) or runtime.get("python") != sys.version:
        raise ValueError("benchmark runtimes must use the same interpreter build")
    packages = runtime.get("packages")
    if not isinstance(packages, dict) or any(
        str(name).lower() in {"pytest", "mypy", "ruff", "types-pyyaml"} for name in packages
    ):
        raise ValueError("benchmark environment must contain only locked runtime packages")
    return Prepared(
        project, python, console, hashlib.sha256(wheels[0].read_bytes()).hexdigest(), runtime
    )


def seed(prepared: Prepared, state: Path, profile: Path) -> None:
    run(
        [
            str(prepared.python),
            str(prepared.project / "tests/fixtures/seed_capability_cache.py"),
            str(state),
            str(profile),
        ],
        cwd=prepared.project,
    )


def provenance(
    before: dict[str, dict[str, object]],
    after: dict[str, dict[str, object]],
    candidate: Prepared,
    previous: Prepared | None,
    baseline: Path | None,
    baseline_status: str,
) -> tuple[dict[str, object], bool]:
    unchanged = all(
        before[name]["source_sha256"] == after[name]["source_sha256"] for name in before
    )
    comparison_kind = "unavailable"
    if previous is not None:
        comparison_kind = (
            "same_source_control"
            if before["candidate"]["source_sha256"] == before["baseline"]["source_sha256"]
            else "baseline_candidate"
        )
    value: dict[str, object] = {
        "sources": before,
        "source_unchanged_during_measurement": unchanged,
        "baseline_status": baseline_status,
        "comparison_kind": comparison_kind,
        "baseline_revision": revision(baseline) if baseline else None,
        "candidate_wheel_sha256": candidate.wheel_sha256,
        "candidate_runtime": candidate.runtime,
        "baseline_wheel_sha256": previous.wheel_sha256 if previous else None,
        "baseline_runtime": previous.runtime if previous else None,
        "python_hash_seed": "0",
        "user_site_disabled": True,
        "working_directory": "fresh benchmark workspace with no checkout PYTHONPATH",
        "limit": "One host and identical interpreter per pair; "
        "CPU/image are recorded, not fixed hardware.",
    }
    return value, unchanged


def check(
    project: Path,
    baseline: Path | None,
    workspace: Path,
    output: Path,
    uv: Path,
    *,
    cpu: str | None,
    disk: str,
) -> int:
    if output.exists() or output.is_symlink():
        raise ValueError("use a new output file; previous evidence is preserved")
    if baseline is not None and not baseline.is_dir():
        raise ValueError("baseline checkout is missing")
    workspace.mkdir(mode=0o700)
    before = {"candidate": source(project)}
    candidate = prepare(project, workspace / "candidate", uv)
    previous = None
    baseline_status = "not_requested"
    if baseline is not None:
        if (baseline / "pyproject.toml").is_file():
            before["baseline"] = source(baseline)
            previous = prepare(baseline, workspace / "baseline", uv)
            baseline_status = "prepared"
        else:
            # A first release may have a documentation-only parent; head absolute gates still run.
            if revision(baseline) is None:
                raise ValueError("a documentation-only baseline must be a complete Git checkout")
            baseline_status = "no_runtime_project_at_baseline"
    profile = project / "examples/profile.toml"
    seed(candidate, workspace / "candidate-state", profile)
    raw_output = workspace / "measurement.json"
    arguments = [
        str(candidate.python),
        str(project / "scripts/benchmark-startup.py"),
        "--command",
        str(candidate.console),
        "--profile",
        str(profile),
        "--cache-state",
        str(workspace / "candidate-state"),
        "--output",
        str(raw_output),
        "--installation-label",
        "isolated runtime-only wheel; frozen uv.lock; fixed hash seed",
        "--disk-type",
        disk,
    ]
    if cpu:
        arguments.extend(("--cpu-label", cpu))
    if previous is not None:
        seed(previous, workspace / "baseline-state", profile)
        arguments.extend(
            (
                "--baseline-command",
                str(previous.console),
                "--baseline-profile",
                str(profile),
                "--baseline-cache-state",
                str(workspace / "baseline-state"),
            )
        )
    measured = run(arguments, cwd=workspace, accepted=(0, 1))
    report = json.loads(raw_output.read_text())
    after = {"candidate": source(project)}
    if previous is not None:
        after["baseline"] = source(previous.project)
    report["provenance"], unchanged = provenance(
        before, after, candidate, previous, baseline, baseline_status
    )
    with output.open("x", encoding="utf-8") as destination:
        destination.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2, allow_nan=False))
    return measured.returncode if unchanged else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--baseline-project", type=Path)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--uv", type=Path, required=True)
    parser.add_argument("--cpu-label")
    parser.add_argument("--disk-type", default="unknown")
    args = parser.parse_args()
    return check(
        args.project.resolve(),
        args.baseline_project.resolve() if args.baseline_project else None,
        args.workspace.absolute(),
        args.output.absolute(),
        args.uv.resolve(),
        cpu=args.cpu_label,
        disk=args.disk_type,
    )


if __name__ == "__main__":
    raise SystemExit(main())
