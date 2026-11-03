"""Actual installed upload smoke; persistent synthetic diagnostics survive installer cleanup."""

from __future__ import annotations

import os
import runpy
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DRIVER = runpy.run_path(str(ROOT / "scripts/benchmark-upload.py"))
EVIDENCE = DRIVER["EVIDENCE"]
CHECKS = DRIVER["CHECKS"]
METADATA_PROBE = """
import json,runpy,sys
from pathlib import Path
helper=runpy.run_path(sys.argv[1])
print(json.dumps(helper['installed_metadata'](Path(sys.argv[2]),sys.argv[3])))
"""


def verify(
    python: Path,
    prefix: Path,
    root: Path,
    scratch: Path,
    workspace: Path,
    environment: dict[str, str],
    artifact_kind: str,
) -> str:
    if artifact_kind not in {"wheel", "sdist"}:
        raise ValueError("unknown installation upload artifact")
    url = run_url(environment)
    workspace = DRIVER["STREAM"]["new_path"](workspace)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()
    workspace.mkdir(mode=0o700)
    try:
        before = EVIDENCE["source"](root)
        (workspace / "source-before.json").write_bytes(CHECKS["encode"](before))
        locked = DRIVER["STREAM"]["locked_runtime"](root)
        with (
            (workspace / "metadata-stdout.json").open("xb") as stdout,
            (workspace / "metadata-stderr.txt").open("xb") as stderr,
        ):
            subprocess.run(
                [
                    str(python),
                    "-I",
                    "-c",
                    METADATA_PROBE,
                    str(root / "scripts/dataset_wheel.py"),
                    str(prefix),
                    locked["yorunge"],
                ],
                cwd=scratch,
                env=environment,
                stdout=stdout,
                stderr=stderr,
                check=True,
                timeout=30,
            )
        metadata = CHECKS["decode"](
            CHECKS["read_bounded"](workspace / "metadata-stdout.json", 1_048_576)
        )
        if (workspace / "metadata-stderr.txt").stat().st_size:
            raise ValueError("installed upload metadata probe wrote unexpected stderr")
        context: dict[str, Any] = {
            "source_before": before,
            "locked_runtime": locked,
            "wheel_metadata_sha256": metadata,
        }
        receipt = workspace / "source-manifest.json"
        receipt.write_bytes(
            CHECKS["encode"](
                {
                    "source_sha256": before["source_sha256"],
                    "locked_runtime": locked,
                    "metadata_sha256": metadata,
                }
            )
        )
        (workspace / "oracle.json").write_bytes((root / EVIDENCE["VECTOR_PATH"]).read_bytes())
        certificates = DRIVER["HTTP"]["certificate"](workspace / "cert", names=("api.ssyz.org.tr",))
        row = DRIVER["measure_one"](python, workspace, receipt, certificates, "16", 1)
        row["passed"] = False
        row["passed"] = EVIDENCE["evaluate_run"](row, context, os.getpid())
        (workspace / "stdout.json").write_bytes(CHECKS["encode"](row))
        after = EVIDENCE["source"](root)
        (workspace / "source-after.json").write_bytes(CHECKS["encode"](after))
        if not row["passed"] or before != after:
            raise ValueError("installed upload smoke failed or source changed")
    except BaseException:
        (workspace / "controller-error.json").write_bytes(
            b'{"outcome":"incomplete_installation_upload"}\n'
        )
        DRIVER["DIAGNOSTIC"]["retain"](
            root,
            workspace,
            f"installation-upload-{artifact_kind}-rejected.json",
            commit,
            "interrupted_measurement",
            url,
        )
        raise
    return "passed"


def run_url(environment: dict[str, str]) -> str | None:
    if environment.get("GITHUB_ACTIONS") != "true":
        return None
    repository, identity = environment.get("GITHUB_REPOSITORY"), environment.get("GITHUB_RUN_ID")
    value = f"https://github.com/{repository}/actions/runs/{identity}"
    return str(CHECKS["pattern_value"](value, CHECKS["CI_RUN_URL"]))
