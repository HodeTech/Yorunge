"""Lossless bounded synthetic download diagnostics; never an acceptance receipt."""

from __future__ import annotations

import base64
import hashlib
import re
import runpy
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHECKS = runpy.run_path(str(ROOT / "scripts/research_evidence.py"))
MAX_FILE = 2_097_152
MAX_TOTAL = 8_388_608
MAX_FILES = 128
# What the controller, the CI wrapper and the installation smoke write beside the run directories.
ROOT_FILES = (
    "source-manifest.json",
    "source-before.json",
    "source-after.json",
    "controller-error.json",
    "metadata-stdout.json",
    "metadata-stderr.txt",
    "stdout.json",
    "stderr.txt",
)
# What one ``LABEL-N`` run directory keeps of the client and of its two object servers. Everything
# else in it (the warm and measured client directories with their config, state and a downloaded
# payload) is a body or a credential-bearing store and is never taken.
LABELS = ("16", "256", "1024", "resume")
SAMPLES = (1, 2, 3)
CLIENT_FILES = ("client-stdout.json", "client-stderr.txt")
SERVERS = ("warm-server", "measured-server")
SERVER_FILES = ("stdout.json", "stderr.txt", "ready.json")
RUN_NAME = re.compile(r"(?:16|256|1024|resume)-[123]", re.ASCII)
REASONS = ("invalid_evidence", "interrupted_measurement", "unverified_measurement")


def allowed(name: str) -> bool:
    parts = PurePosixPath(name).parts
    if not parts or name != str(PurePosixPath(name)):
        return False
    if len(parts) == 1:
        return name in ROOT_FILES
    if RUN_NAME.fullmatch(parts[0]):
        return (len(parts) == 2 and parts[1] in CLIENT_FILES) or (
            len(parts) == 3 and parts[1] in SERVERS and parts[2] in SERVER_FILES
        )
    return False


def paths(workspace: Path) -> list[Path]:
    if workspace.is_symlink() or any(parent.is_symlink() for parent in workspace.parents):
        raise ValueError("download diagnostics require a synthetic workspace without symlinks")
    found = [workspace / name for name in ROOT_FILES]
    for label in LABELS:
        for sample in SAMPLES:
            base = workspace / f"{label}-{sample}"
            found.extend(base / name for name in CLIENT_FILES)
            for server in SERVERS:
                found.extend(base / server / name for name in SERVER_FILES)
    return [path for path in found if path.exists() or path.is_symlink()]


def attachment(path: Path, workspace: Path) -> dict[str, Any]:
    if any(parent.is_symlink() for parent in path.parents):
        raise ValueError("download diagnostic ancestors must not be symlinks")
    content = CHECKS["read_bounded"](path, MAX_FILE)
    return {
        "name": str(path.relative_to(workspace)),
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "content_base64": base64.b64encode(content).decode("ascii"),
    }


def summarize(report: object) -> dict[str, Any]:
    value = CHECKS["closed"](
        report,
        "schema_version report_kind source_commit run_url rejection_reason files",
        "rejected download",
    )
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError("invalid rejected download schema version")
    if (
        value["report_kind"] != "rejected_download_evidence_v1"
        or value["rejection_reason"] not in REASONS
    ):
        raise ValueError("unknown download diagnostic kind/reason")
    CHECKS["pattern_value"](value["source_commit"], CHECKS["COMMIT"])
    if value["run_url"] is not None:
        CHECKS["pattern_value"](value["run_url"], CHECKS["CI_RUN_URL"])
    files = value["files"]
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
        raise ValueError("download diagnostic requires bounded original files")
    names, total = set(), 0
    for item in files:
        name, size = validate_attachment(item)
        if name in names:
            raise ValueError("unknown/duplicate download diagnostic file")
        names.add(name)
        total += size
    if total > MAX_TOTAL:
        raise ValueError("download diagnostic total byte limit exceeded")
    return {
        "kind": "rejected-download",
        "accepted": False,
        "diagnostic_only": True,
        "files": len(files),
        "original_bytes": total,
    }


def validate_attachment(item: object) -> tuple[str, int]:
    part = CHECKS["closed"](item, "name bytes sha256 content_base64", "download diagnostic file")
    name = str(CHECKS["text_value"](part["name"]))
    if not allowed(name):
        raise ValueError("unknown download diagnostic file")
    size = int(CHECKS["integer"](part["bytes"]))
    encoded = part["content_base64"]
    if size > MAX_FILE or not isinstance(encoded, str) or len(encoded) > 4 * ((MAX_FILE + 2) // 3):
        raise ValueError("download diagnostic file size limit exceeded")
    try:
        content = base64.b64decode(encoded, validate=True)
    except ValueError:
        raise ValueError("invalid download diagnostic base64") from None
    CHECKS["pattern_value"](part["sha256"], CHECKS["SHA256"])
    if len(content) != size or hashlib.sha256(content).hexdigest() != part["sha256"]:
        raise ValueError("download diagnostic bytes/hash mismatch")
    return name, size


def retain(
    root: Path,
    workspace: Path,
    name: str,
    commit: str,
    reason: str,
    run_url: str | None = None,
    *,
    privacy_context: dict[str, Any] | None = None,
) -> Path:
    if CHECKS["NAME"].fullmatch(name) is None:
        raise ValueError("invalid download diagnostic archive name")
    originals = paths(workspace)
    if len(originals) > MAX_FILES:
        raise ValueError("too many download diagnostic files; originals preserved")
    files, total = [], 0
    for path in originals:
        item = attachment(path, workspace)
        total += item["bytes"]
        if total > MAX_TOTAL:
            raise ValueError("download diagnostic total limit exceeded; originals preserved")
        files.append(item)
    report = {
        "schema_version": 1,
        "report_kind": "rejected_download_evidence_v1",
        "source_commit": commit,
        "run_url": run_url,
        "rejection_reason": reason,
        "files": files,
    }
    summarize(report)
    destination = root / "dist" / name
    if destination.parent.is_symlink():
        raise ValueError("download diagnostic output must not use a symlink")
    with destination.open("xb") as stream:
        stream.write(CHECKS["encode"](report))
    CHECKS["archive_report"](root, destination, None, privacy_context=privacy_context)
    return destination
