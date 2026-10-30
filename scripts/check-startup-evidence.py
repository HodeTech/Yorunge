"""Prepare fresh frozen paired startup measurements with source-bound evidence."""

from __future__ import annotations

import argparse
import json
import runpy
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = runpy.run_path(str(ROOT / "scripts/startup_evidence.py"))
PREPARE = runpy.run_path(str(ROOT / "scripts/check-startup.py"))
DATA_PROBE = """
import hashlib, json
from pathlib import Path
import yorunge
root = Path(yorunge.__file__).resolve().parent
files = [p for p in root.rglob('*') if p.is_file() and p.suffix != '.py'
         and '__pycache__' not in p.parts]
if any(p.is_symlink() or not p.resolve().is_relative_to(root) for p in files):
    raise ValueError('runtime data escaped installed product')
print(json.dumps({'yorunge/' + str(p.relative_to(root)):
                  hashlib.sha256(p.read_bytes()).hexdigest() for p in files}))
"""


def snapshot(prepared: Any, state: Path, profile: Path, workspace: Path) -> dict[str, Any]:
    wheel = list((prepared.python.parent.parent.parent / "dist").glob("*.whl"))
    if len(wheel) != 1:
        raise ValueError("startup requires exactly one freshly built wheel")
    if EVIDENCE["digest"](wheel[0]) != prepared.wheel_sha256:
        raise ValueError("startup wheel changed after fresh installation")
    return {
        "source": EVIDENCE["source"](prepared.project),
        "installed": EVIDENCE["JOBS"]["runtime"](prepared.python, prepared.project, workspace),
        "runtime_data_sha256": EVIDENCE["CHECKS"]["decode"](
            PREPARE["run"](
                [str(prepared.python), "-I", "-c", DATA_PROBE], cwd=workspace
            ).stdout.encode()
        ),
        "fixture": EVIDENCE["fixture"](state, profile),
        "wheel_path": str(wheel[0]),
        "wheel_sha256": EVIDENCE["digest"](wheel[0]),
    }


def check(
    project: Path,
    baseline: Path,
    workspace: Path,
    output: Path,
    uv: Path,
    *,
    cpu: str | None,
    disk: str,
) -> int:
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        raise ValueError("startup evidence requires a new output in an existing directory")
    if not (baseline / "pyproject.toml").is_file():
        raise ValueError("audited startup requires a runtime baseline checkout")
    workspace.mkdir(mode=0o700)
    source_before = {
        side: EVIDENCE["source"](root)
        for side, root in (("candidate", project), ("baseline", baseline))
    }
    prepared = {
        side: PREPARE["prepare"](root, workspace / side, uv)
        for side, root in (("candidate", project), ("baseline", baseline))
    }
    profile = project / "examples/profile.toml"
    for side, install in prepared.items():
        PREPARE["seed"](install, workspace / (side + "-state"), profile)
    before = {
        side: snapshot(install, workspace / (side + "-state"), profile, workspace)
        for side, install in prepared.items()
    }
    if any(before[side]["source"] != source_before[side] for side in before):
        raise ValueError("startup source changed during preparation")
    manifest = {
        "schema_version": 1,
        "diagnostic_only": True,
        "source_commit": before["candidate"]["source"]["commit"],
        "outcome": "pre_measurement_provenance_only",
        "snapshots_before": before,
    }
    with (workspace / "source-manifest.json").open("x", encoding="utf-8") as destination:
        destination.write(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    raw, audit = workspace / "measurement.json", workspace / "stdout-checks.json"
    args = [
        str(prepared["candidate"].python),
        str(project / "scripts/benchmark-startup.py"),
        "--command",
        str(prepared["candidate"].console),
        "--profile",
        str(profile),
        "--cache-state",
        str(workspace / "candidate-state"),
        "--output",
        str(raw),
        "--audit-output",
        str(audit),
        "--audit-candidate-version",
        before["candidate"]["installed"]["product_version"],
        "--audit-baseline-version",
        before["baseline"]["installed"]["product_version"],
        "--audit-candidate-python",
        before["candidate"]["installed"]["executable"],
        "--audit-baseline-python",
        before["baseline"]["installed"]["executable"],
        "--installation-label",
        EVIDENCE["INSTALLATION"],
        "--disk-type",
        disk,
        "--baseline-command",
        str(prepared["baseline"].console),
        "--baseline-profile",
        str(profile),
        "--baseline-cache-state",
        str(workspace / "baseline-state"),
    ]
    if cpu is not None:
        args.extend(("--cpu-label", cpu))
    result = subprocess.run(
        args,
        cwd=workspace,
        env=PREPARE["environment"](),
        capture_output=True,
        text=True,
        timeout=900,
    )
    if result.returncode not in (0, 1):
        raise subprocess.CalledProcessError(result.returncode, args, result.stdout, result.stderr)
    after = {
        side: snapshot(install, workspace / (side + "-state"), profile, workspace)
        for side, install in prepared.items()
    }
    report = {
        "schema_version": 1,
        "report_kind": "startup_evidence_v1",
        "source_commit": before["candidate"]["source"]["commit"],
        "measurement": EVIDENCE["CHECKS"]["decode"](raw.read_bytes()),
        "snapshots": {"before": before, "after": after},
        "output_checks": EVIDENCE["CHECKS"]["decode"](audit.read_bytes()),
        "measurement_exit": result.returncode,
        "passed": result.returncode == 0,
    }
    # Preserve the original report even when strict validation rejects its provenance.
    with output.open("x", encoding="utf-8") as destination:
        destination.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    summary = EVIDENCE["validate"](report)
    EVIDENCE["current_sources"](project, report)
    print(json.dumps(summary, indent=2, allow_nan=False))
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=ROOT)
    parser.add_argument("--baseline-project", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--uv", type=Path, required=True)
    parser.add_argument("--cpu-label")
    parser.add_argument("--disk-type", default="unknown")
    args = parser.parse_args()
    return check(
        args.project.resolve(),
        args.baseline_project.resolve(),
        args.workspace.absolute(),
        args.output.absolute(),
        args.uv.resolve(),
        cpu=args.cpu_label,
        disk=args.disk_type,
    )


if __name__ == "__main__":
    raise SystemExit(main())
