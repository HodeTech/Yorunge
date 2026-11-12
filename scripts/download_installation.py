"""Actual installed download smoke; persistent synthetic diagnostics survive installer cleanup.

The installed runtime is asked for the path a person takes and for the measured one. First the
surface: the help, the closed gates, and a real ``yorunge models download`` of the 16 MiB fixture
(the installed package behind the test-only loopback TLS wiring), all against one object server
whose own closed account must then show exactly one JSON call and one signed GET, so no gate
reached it. Then the harness's worker sample of the same object, judged by the measurement
verifier. Whatever fails keeps its synthetic originals outside the temporary installation.
"""

from __future__ import annotations

import hashlib
import os
import runpy
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DRIVER = runpy.run_path(str(ROOT / "scripts/benchmark-download.py"))
EVIDENCE = DRIVER["EVIDENCE"]
CHECKS = DRIVER["CHECKS"]
CONTROL = DRIVER["CONTROL"]
DATA = DRIVER["DATA"]
HTTP = DRIVER["HTTP"]
STREAM = DRIVER["STREAM"]
SURFACE = runpy.run_path(str(ROOT / "scripts/surface_installation.py"))
DIAGNOSTIC = runpy.run_path(str(ROOT / "scripts/download_diagnostic.py"))
CONSOLE = ROOT / "tests/fixtures/model_console.py"
LABEL = "16"
# The worker sample is 16-1. The retention allow-list is the measurement controller's, so the CLI
# download keeps its console output and its server account in the next free sample slot.
CLI_RUN = "16-2"
HELP = ("--version-id", "--format", "--weights-out", "--sha256", "--timeout", "--no-resume")
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
        raise ValueError("unknown installation download artifact")
    url = run_url(environment)
    workspace = STREAM["new_path"](workspace)
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
    stage = "start"
    try:
        stage = "source"
        before = EVIDENCE["source"](root)
        (workspace / "source-before.json").write_bytes(CHECKS["encode"](before))
        locked = STREAM["locked_runtime"](root)
        stage = "metadata"
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
            raise ValueError("installed download metadata probe wrote unexpected stderr")
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
        certificates = HTTP["certificate"](workspace / "cert", names=(DATA["PLATFORM_HOST"],))
        stage = "surface"
        surface(
            python,
            prefix / "bin" / "yorunge",
            scratch,
            workspace / CLI_RUN,
            certificates,
            environment,
        )
        stage = "measurement"
        row = DRIVER["measure_one"](python, workspace, receipt, certificates, LABEL, 1)
        row["passed"] = False
        row["passed"] = EVIDENCE["evaluate_run"](row, context, os.getpid())
        (workspace / "stdout.json").write_bytes(CHECKS["encode"](row))
        stage = "judgement"
        after = EVIDENCE["source"](root)
        (workspace / "source-after.json").write_bytes(CHECKS["encode"](after))
        if not row["passed"] or before != after:
            rules = EVIDENCE["judge_run"](row, context, os.getpid())
            failed = ", ".join(name for name, ok in rules.items() if not ok) or "none"
            raise ValueError(
                f"installed download smoke failed or source changed: failed rules {failed}; "
                f"source map changed {before != after}"
            )
    except BaseException:
        (workspace / "controller-error.json").write_bytes(
            CHECKS["encode"]({"outcome": "incomplete_installation_download", "stage": stage})
        )
        DIAGNOSTIC["retain_beside"](
            root,
            workspace,
            f"installation-download-{artifact_kind}-rejected.json",
            commit,
            "interrupted_measurement",
            url,
        )
        raise
    return "passed"


def surface(
    python: Path,
    console: Path,
    scratch: Path,
    run: Path,
    certificates: tuple[Path, Path],
    environment: dict[str, str],
) -> None:
    """The help, the closed gates and one real download of the installed package, off EVREN."""
    offline = SURFACE["offline_environment"](environment)
    SURFACE["check_help"](
        SURFACE["execute"]([str(console), "models", "download", "--help"], scratch, offline),
        "models download",
        HELP,
    )
    work = scratch / "cli-download"
    work.mkdir()
    layout = DATA["paths"](work)
    DATA["write_config"](layout.config)
    layout.out.mkdir()
    occupied = work / "occupied" / "taken.onnx"
    occupied.parent.mkdir()
    occupied.write_bytes(b"mine")
    SURFACE["initialise"](console, layout.state, scratch, offline)
    size = DATA["FIXTURES"][LABEL].size
    oracle = DATA["expected_sha256"](size)
    keyed = {**offline, DATA["KEY_ENV"]: DATA["KEY"]}
    run.mkdir()
    with CONTROL["server"](run / "measured-server", certificates, LABEL) as sink:

        def command(target: str, *extra: str, version: str = DATA["VERSION"]) -> list[str]:
            return [
                str(python),
                "-I",
                "-W",
                "error",
                str(CONSOLE),
                "--ca",
                str(certificates[0]),
                "--port",
                str(sink["port"]),
                "--",
                "models",
                "download",
                "--version-id",
                version,
                "--format",
                DATA["FORMAT"],
                "--weights-out",
                target,
                "--config",
                str(layout.config),
                "--state-dir",
                str(layout.state),
                "--output",
                "json",
                *extra,
            ]

        target = str(layout.target)
        for label, arguments, code, exit_code, environment_of in (
            ("download without a key", command(target), "credential_unavailable", 3, offline),
            ("download onto a file", command(str(occupied)), "download_output_exists", 2, keyed),
            (
                "download beside a missing parent",
                command("missing/weights.onnx"),
                "download_target_invalid",
                2,
                keyed,
            ),
            (
                "download of a malformed version",
                command(target, version="no"),
                "invalid_request",
                2,
                keyed,
            ),
            (
                "download with a malformed digest",
                command(target, "--sha256", "XYZ"),
                "invalid_request",
                2,
                keyed,
            ),
        ):
            result = SURFACE["execute"](arguments, work, environment_of)
            SURFACE["check_error"](result, label, code, exit_code)
        fetched = subprocess.run(
            command(target, "--sha256", oracle),
            cwd=work,
            env=keyed,
            capture_output=True,
            timeout=300,
            check=False,
        )
    with (run / "client-stderr.txt").open("xb") as stderr:
        stderr.write(fetched.stderr)
    if fetched.stdout:  # a failed download prints nothing here: no empty original is kept as JSON
        with (run / "client-stdout.json").open("xb") as stdout:
            stdout.write(fetched.stdout)
    settle(fetched, layout, occupied, run, size, oracle)


def settle(
    fetched: subprocess.CompletedProcess[bytes],
    layout: Any,
    occupied: Path,
    run: Path,
    size: int,
    oracle: str,
) -> None:
    """What a person and the object server must see once the download is over."""
    if fetched.returncode != 0 or fetched.stderr:
        raise ValueError(
            f"installed download failed: exit {fetched.returncode}, stderr {fetched.stderr[:200]!r}"
        )
    EVIDENCE["equal"](
        CHECKS["decode"](fetched.stdout),
        summary(layout.target, size, oracle),
        "installed download result differs from the closed summary",
    )
    written, digest = file_digest(layout.target)
    if written != size or digest != oracle or digest != EVIDENCE["object_sha256"](size):
        raise ValueError("installed download bytes differ from the independent oracle")
    if (
        sorted(entry.name for entry in layout.out.iterdir()) != [DATA["TARGET_NAME"]]
        or occupied.read_bytes() != b"mine"
        or (layout.out.parent / "missing").exists()
    ):
        raise ValueError("installed download left or changed unexpected files")
    if (run / "measured-server/stderr.txt").stat().st_size:
        raise ValueError("installed download server wrote unexpected stderr; original preserved")
    account = EVIDENCE["server"](
        DRIVER["decode_output"](run / "measured-server/stdout.json"), LABEL
    )
    broken = [name for name, ok in EVIDENCE["exchange"](account, LABEL, 0).items() if not ok]
    if broken:
        raise ValueError("installed download server account differs: " + ", ".join(broken))


def summary(target: Path, size: int, digest: str) -> dict[str, Any]:
    """The one result a verified download of the fixture prints; nothing in it is optional."""
    return {
        "schema_version": 1,
        "operation_id": None,
        "status": "completed",
        "data": {
            "schema_version": 1,
            "kind": "download_summary",
            "output_path": str(target),
            "bytes": size,
            "sha256": digest,
            "verification_level": "sha256_matched",
            "expectation_source": "user_supplied",
            "resumed": False,
            "resumed_from_bytes": 0,
            "source": {
                "kind": "model_version",
                "version_id": DATA["VERSION"],
                "format": DATA["FORMAT"],
                "fold": None,
            },
        },
        "warnings": [],
    }


def run_url(environment: dict[str, str]) -> str | None:
    if environment.get("GITHUB_ACTIONS") != "true":
        return None
    repository, identity = environment.get("GITHUB_REPOSITORY"), environment.get("GITHUB_RUN_ID")
    value = f"https://github.com/{repository}/actions/runs/{identity}"
    return str(CHECKS["pattern_value"](value, CHECKS["CI_RUN_URL"]))


def file_digest(path: Path) -> tuple[int, str]:
    digest, size = hashlib.sha256(), 0
    with path.open("rb", buffering=0) as source:
        while block := source.read(1_048_576):
            digest.update(block)
            size += len(block)
    return size, digest.hexdigest()
