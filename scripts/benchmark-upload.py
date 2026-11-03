"""Serial installed upload measurements, separate bounded TLS sinks and lossless failures."""

from __future__ import annotations

import argparse
import json
import os
import runpy
import subprocess
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
HTTP = runpy.run_path(str(ROOT / "tests/fixtures/http_server.py"))
CONTROL = runpy.run_path(str(ROOT / "tests/fixtures/upload_native_control.py"))
DATA = runpy.run_path(str(ROOT / "tests/fixtures/upload_native_data.py"))
EVIDENCE = runpy.run_path(str(ROOT / "scripts/upload_evidence.py"))
CHECKS = EVIDENCE["CHECKS"]
STREAM = EVIDENCE["STREAM"]
WHEEL = runpy.run_path(str(ROOT / "scripts/dataset_wheel.py"))
DIAGNOSTIC = runpy.run_path(str(ROOT / "scripts/upload_diagnostic.py"))


def decode_output(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], CHECKS["decode"](CHECKS["read_bounded"](path, 1_048_576)))


def worker(
    python: Path,
    work: Path,
    provenance: Path,
    certificates: tuple[Path, Path],
    warm: dict[str, int],
    sink: dict[str, int],
) -> tuple[dict[str, Any], int]:
    command = [
        str(python),
        "-I",
        "-W",
        "error",
        str(ROOT / "tests/fixtures/upload_native_client.py"),
        "--ca",
        str(certificates[0]),
        "--port",
        str(sink["port"]),
        "--warm-port",
        str(warm["port"]),
        "--prefix",
        str(python.parent.parent),
        "--provenance",
        str(provenance),
        "--work",
        str(work / "measured"),
        "--warm",
        str(work / "warm"),
    ]
    with (
        (work / "client-stdout.json").open("xb") as stdout,
        (work / "client-stderr.txt").open("xb") as stderr,
    ):
        with subprocess.Popen(
            command, cwd=work, env=CONTROL["environment"](), stdout=stdout, stderr=stderr
        ) as process:
            try:
                result = process.wait(timeout=1020)
            except BaseException:
                process.kill()
                process.wait(timeout=10)
                raise
    if result or (work / "client-stderr.txt").stat().st_size:
        raise ValueError("upload worker failed; original stdout/stderr preserved")
    value = decode_output(work / "client-stdout.json")
    if value.get("pid") != process.pid or result_pid(value) != process.pid:
        raise ValueError("invalid upload worker identity")
    return value, process.pid


def result_pid(value: dict[str, Any]) -> int:
    runtime = value.get("runtime")
    if not isinstance(runtime, dict):
        raise ValueError("upload worker runtime identity missing")
    return cast(int, CHECKS["integer"](runtime.get("pid"), minimum=1))


def measure_one(
    python: Path,
    workspace: Path,
    receipt: Path,
    certificates: tuple[Path, Path],
    label: str,
    sample: int,
) -> dict[str, Any]:
    work = workspace / f"{label}-{sample}"
    work.mkdir()
    for name, selected in (("warm", "warm"), ("measured", label)):
        directory = work / name
        directory.mkdir()
        DATA["write_fixture"](
            directory / "source", directory / "manifest.json", DATA["fixture"](selected)
        )
        DATA["write_config"](directory / "config.toml")
    with (
        CONTROL["server"](work / "warm-server", certificates, "warm") as warm,
        CONTROL["server"](work / "measured-server", certificates, label) as sink,
    ):
        client, client_pid = worker(python, work, receipt, certificates, warm, sink)
    for name in ("warm-server", "measured-server"):
        if (work / name / "stderr.txt").stat().st_size:
            raise ValueError("upload sink wrote unexpected stderr; original preserved")
    return {
        "label": label,
        "sample": sample,
        "client": client,
        "client_process_pid": client_pid,
        "server_process_pid": sink["pid"],
        "warm_server_process_pid": warm["pid"],
        "server": decode_output(work / "measured-server/stdout.json"),
        "warm_server": decode_output(work / "warm-server/stdout.json"),
    }


def run_measurements(
    python: Path, workspace: Path, receipt: Path, certificates: tuple[Path, Path]
) -> list[dict[str, Any]]:
    return [
        measure_one(python, workspace, receipt, certificates, label, sample)
        for label in EVIDENCE["LABELS"]
        for sample in (1, 2, 3)
    ]


def assemble(
    before: dict[str, Any],
    after: dict[str, Any],
    wheel_before: dict[str, Any],
    wheel_after: dict[str, Any],
    locked: dict[str, str],
    runs: list[dict[str, Any]],
    *,
    cpu: str,
    disk: str,
) -> dict[str, Any]:
    proof = {
        "source_before": before,
        "source_after": after,
        "locked_runtime": locked,
        "wheel_before": wheel_before["sha256"],
        "wheel_after": wheel_after["sha256"],
        "wheel_product_sha256": wheel_before["product_sha256"],
        "wheel_metadata_sha256": wheel_before["metadata_sha256"],
    }
    for row in runs:
        row["passed"] = False
        row["passed"] = EVIDENCE["evaluate_run"](row, proof, os.getpid())
    report = {
        "schema_version": 1,
        "report_kind": "upload_budget_v1",
        "source_commit": before["commit"],
        "environment": {"cpu": cpu, "disk_type": disk},
        "provenance": proof,
        "method": EVIDENCE["METHOD"],
        "limits": EVIDENCE["LIMITS"],
        "controller_pid": os.getpid(),
        "runs": runs,
        "growth": EVIDENCE["growth"](runs),
        "passed": False,
    }
    report["passed"] = EVIDENCE["report_passed"](proof, runs, report["growth"])
    EVIDENCE["summarize_report"](report)
    return report


def check(args: argparse.Namespace) -> int:
    output = STREAM["new_path"](args.output)
    workspace = STREAM["new_path"](args.workspace)
    if output.parent != ROOT / "dist" or CHECKS["NAME"].fullmatch(output.name) is None:
        raise ValueError("upload report requires a new canonical name directly in dist")
    python, wheel = args.python.absolute(), args.wheel.absolute()
    if not python.is_file() or not wheel.is_file():
        raise ValueError("installed runtime Python and wheel required")
    if args.run_url is not None:
        CHECKS["pattern_value"](args.run_url, CHECKS["CI_RUN_URL"])
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        env=CONTROL["environment"](),
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    ).stdout.strip()
    workspace.mkdir(mode=0o700)
    try:
        before = EVIDENCE["source"](ROOT)
        (workspace / "source-before.json").write_bytes(CHECKS["encode"](before))
        locked = STREAM["locked_runtime"](ROOT)
        first = WHEEL["snapshot"](wheel, before["source_sha256"], locked["yorunge"])
        receipt = workspace / "source-manifest.json"
        receipt.write_bytes(
            CHECKS["encode"](
                {
                    "source_sha256": before["source_sha256"],
                    "locked_runtime": locked,
                    "metadata_sha256": first["metadata_sha256"],
                }
            )
        )
        (workspace / "oracle.json").write_bytes((ROOT / EVIDENCE["VECTOR_PATH"]).read_bytes())
        certificates = HTTP["certificate"](workspace / "cert", names=("api.ssyz.org.tr",))
        runs = run_measurements(python, workspace, receipt, certificates)
        after = EVIDENCE["source"](ROOT)
        (workspace / "source-after.json").write_bytes(CHECKS["encode"](after))
        last = WHEEL["snapshot"](wheel, before["source_sha256"], locked["yorunge"])
        report = assemble(
            before, after, first, last, locked, runs, cpu=args.cpu, disk=args.disk_type
        )
        with output.open("xb") as target:
            target.write(CHECKS["encode"](report))
    except BaseException:
        (workspace / "controller-error.json").write_bytes(
            b'{"outcome":"incomplete_upload_measurement"}\n'
        )
        DIAGNOSTIC["retain"](
            ROOT,
            workspace,
            output.stem + "-rejected.json",
            commit,
            "interrupted_measurement",
            args.run_url,
        )
        raise
    if not report["passed"]:
        CHECKS["archive_report"](ROOT, output, None)
    print(json.dumps(EVIDENCE["summarize_report"](report), allow_nan=False))
    return 0 if report["passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True, type=Path)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cpu", required=True)
    parser.add_argument("--disk-type", required=True)
    parser.add_argument("--run-url")
    args = parser.parse_args()
    try:
        return check(args)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Upload measurement failed: {error}; original files remain in workspace.\n")


if __name__ == "__main__":
    raise SystemExit(main())
