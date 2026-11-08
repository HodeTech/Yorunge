"""Serial installed download measurements, separate TLS object servers and lossless failures.

Twelve fresh runtime-only ``-I`` clients (labels 16, 256, 1024 and ``resume``, three samples each)
download through the product's public API from a separate-process server; the report is written once
to a new canonical path directly in ``dist``. ``--labels`` and ``--samples`` select a smoke subset:
its report says it is partial and is never accepted.

A complete report that did not pass is archived as it is. An interrupted complete run (an error,
Ctrl-C, SIGTERM or SIGHUP; SIGKILL cannot be caught) leaves a ``controller-error.json`` marker in
its workspace and retains the original files that exist as a rejected-download attachment; nothing
is retried, deleted or rewritten. A smoke subset is a tool: its originals stay in the workspace and
it never writes the evidence archive.
"""

from __future__ import annotations

import argparse
import json
import os
import runpy
import signal
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
HTTP = runpy.run_path(str(ROOT / "tests/fixtures/http_server.py"))
CONTROL = runpy.run_path(str(ROOT / "tests/fixtures/download_native_control.py"))
DATA = runpy.run_path(str(ROOT / "tests/fixtures/download_native_data.py"))
EVIDENCE = runpy.run_path(str(ROOT / "scripts/download_evidence.py"))
CHECKS = EVIDENCE["CHECKS"]
STREAM = EVIDENCE["STREAM"]
WHEEL = runpy.run_path(str(ROOT / "scripts/dataset_wheel.py"))
DIAGNOSTIC = runpy.run_path(str(ROOT / "scripts/download_diagnostic.py"))
# Longest a worker may take: warm, oracle, one 900 s product budget per call, and the verification.
WORKER_SECONDS = {"16": 1200, "256": 1200, "1024": 1500, "resume": 2100}


@contextmanager
def termination_signals() -> Iterator[None]:
    """SIGTERM and SIGHUP stop the controller the way Ctrl-C does.

    They become ``SystemExit`` so that the ``BaseException`` path of ``check`` runs (the marker, the
    retained diagnostics), the worker that is running is killed and both servers stop; without this
    a ``kill`` of the controller would leave all three alive. A second signal during that cleanup is
    ignored. SIGKILL cannot be caught: nothing here can help with it (``download_ci.py`` owns a
    process group for that).
    """
    # a signal that was ignored on entry (a hangup under ``nohup``) stays ignored
    numbers = tuple(
        number
        for number in (signal.SIGTERM, signal.SIGHUP)
        if signal.getsignal(number) is not signal.SIG_IGN
    )
    previous = {number: signal.getsignal(number) for number in numbers}

    def interrupted(number: int, frame: object) -> None:
        for other in numbers:
            signal.signal(other, signal.SIG_IGN)
        raise SystemExit(128 + number)

    for number in numbers:
        signal.signal(number, interrupted)
    try:
        yield
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def decode_output(path: Path) -> dict[str, Any]:
    """A worker's or server's stdout: one canonical JSON object and one LF, nothing else."""
    content = cast(bytes, CHECKS["read_bounded"](path, 1_048_576))
    value = cast(dict[str, Any], CHECKS["decode"](content))
    if content != DATA["canonical"](value) + b"\n":
        raise ValueError("download output is not one canonical JSON object followed by LF")
    return value


def worker(
    python: Path,
    work: Path,
    provenance: Path,
    certificates: tuple[Path, Path],
    warm: dict[str, int],
    sink: dict[str, int],
    label: str,
) -> tuple[dict[str, Any], int]:
    command = [
        str(python),
        "-I",
        "-W",
        "error",
        str(ROOT / "tests/fixtures/download_native_client.py"),
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
        "--label",
        label,
    ]
    with (
        (work / "client-stdout.json").open("xb") as stdout,
        (work / "client-stderr.txt").open("xb") as stderr,
        subprocess.Popen(
            command, cwd=work, env=CONTROL["environment"](), stdout=stdout, stderr=stderr
        ) as process,
    ):
        try:
            result = process.wait(timeout=WORKER_SECONDS[label])
        except BaseException:
            process.kill()
            process.wait(timeout=10)
            raise
    if result or (work / "client-stderr.txt").stat().st_size:
        raise ValueError("download worker failed; original stdout/stderr preserved")
    value = decode_output(work / "client-stdout.json")
    if value.get("pid") != process.pid or result_pid(value) != process.pid:
        raise ValueError("invalid download worker identity")
    return value, process.pid


def result_pid(value: dict[str, Any]) -> int:
    runtime = value.get("runtime")
    if not isinstance(runtime, dict):
        raise ValueError("download worker runtime identity missing")
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
    for name in ("warm", "measured"):
        (work / name).mkdir()
    with (
        CONTROL["server"](work / "warm-server", certificates, DATA["WARM_OF"][label]) as warm,
        CONTROL["server"](work / "measured-server", certificates, label) as sink,
    ):
        client, client_pid = worker(python, work, receipt, certificates, warm, sink, label)
    for name in ("warm-server", "measured-server"):
        if (work / name / "stderr.txt").stat().st_size:
            raise ValueError("download server wrote unexpected stderr; original preserved")
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
    python: Path,
    workspace: Path,
    receipt: Path,
    certificates: tuple[Path, Path],
    labels: list[str],
    samples: int,
) -> list[dict[str, Any]]:
    return [
        measure_one(python, workspace, receipt, certificates, label, sample)
        for label in labels
        for sample in range(1, samples + 1)
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
    labels: list[str],
    samples: int,
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
    partial = EVIDENCE["is_partial"](labels, samples)
    report: dict[str, Any] = {
        "schema_version": 1,
        "report_kind": "download_budget_v1",
        "source_commit": before["commit"],
        "environment": {"cpu": cpu, "disk_type": disk},
        "provenance": proof,
        "method": EVIDENCE["METHOD"],
        "limits": EVIDENCE["LIMITS"],
        "scope": {"labels": labels, "samples": samples, "partial": partial},
        "controller_pid": os.getpid(),
        "runs": runs,
        "growth": EVIDENCE["growth"](runs),
        "passed": False,
        "accepted": False,
    }
    report["passed"] = EVIDENCE["report_passed"](proof, runs, report["growth"])
    report["accepted"] = report["passed"] and not partial
    EVIDENCE["summarize_report"](report)
    return report


def chosen(args: argparse.Namespace) -> tuple[list[str], int]:
    labels, samples = list(args.labels), args.samples
    if not labels or labels != [label for label in DATA["LABELS"] if label in labels]:
        raise ValueError("download labels must be unique and in canonical order")
    if type(samples) is not int or not 1 <= samples <= 3:
        raise ValueError("download samples per label must be 1, 2 or 3")
    return labels, samples


def check(args: argparse.Namespace) -> int:
    output = STREAM["new_path"](args.output)
    workspace = STREAM["new_path"](args.workspace)
    if CHECKS["NAME"].fullmatch(output.name) is None:
        raise ValueError("download report requires a new canonical lowercase name")
    labels, samples = chosen(args)
    partial = EVIDENCE["is_partial"](labels, samples)
    python, wheel = args.python.absolute(), args.wheel.absolute()
    if not python.is_file() or not wheel.is_file():
        raise ValueError("installed runtime Python and wheel required")
    if output.parent != ROOT / "dist":
        raise ValueError("download report must be created directly in dist")
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
        certificates = HTTP["certificate"](workspace / "cert", names=("api.ssyz.org.tr",))
        runs = run_measurements(python, workspace, receipt, certificates, labels, samples)
        after = EVIDENCE["source"](ROOT)
        (workspace / "source-after.json").write_bytes(CHECKS["encode"](after))
        last = WHEEL["snapshot"](wheel, before["source_sha256"], locked["yorunge"])
        report = assemble(
            before,
            after,
            first,
            last,
            locked,
            runs,
            cpu=args.cpu,
            disk=args.disk_type,
            labels=labels,
            samples=samples,
        )
        with output.open("xb") as target:
            target.write(CHECKS["encode"](report))
    except BaseException:
        (workspace / "controller-error.json").write_bytes(
            b'{"outcome":"incomplete_download_measurement"}\n'
        )
        if not partial:  # a smoke subset is a tool: its originals stay in the workspace
            DIAGNOSTIC["retain_beside"](
                ROOT,
                workspace,
                output.stem + "-rejected.json",
                commit,
                "interrupted_measurement",
                args.run_url,
            )
        raise
    if not report["passed"] and not partial:  # a failed complete measurement is evidence
        CHECKS["archive_report"](ROOT, output, None)
    print(json.dumps(EVIDENCE["summarize_report"](report), allow_nan=False))
    return 0 if report["accepted"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True, type=Path)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cpu", required=True)
    parser.add_argument("--disk-type", required=True)
    parser.add_argument("--run-url")
    parser.add_argument(
        "--labels",
        nargs="+",
        choices=DATA["LABELS"],
        default=list(DATA["LABELS"]),
        help="smoke subset (canonical order): the report is partial and never accepted",
    )
    parser.add_argument(
        "--samples",
        type=int,
        choices=(1, 2, 3),
        default=3,
        help="samples per label; fewer than three is a smoke run and never accepted",
    )
    args = parser.parse_args()
    try:
        with termination_signals():
            return check(args)
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        RecursionError,
        subprocess.SubprocessError,
    ) as error:
        parser.exit(
            1, f"Download measurement failed: {error}; original files remain in workspace.\n"
        )


if __name__ == "__main__":
    raise SystemExit(main())
