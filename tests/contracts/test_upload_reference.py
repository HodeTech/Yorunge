"""Source-reference gate rejects stale oracle/lock and non-reference evidence."""

import copy
import runpy
from pathlib import Path

import pytest

from tests.contracts.test_installation_evidence import receipt as installation
from tests.fixtures.upload_report import report as vector

ROOT = Path(__file__).resolve().parents[2]


def reference(evidence):
    report = vector(evidence["METHOD"], evidence["LIMITS"])
    report["environment"] = {"cpu": "Apple M5 Max", "disk_type": "internal SSD/APFS"}
    for row in report["runs"]:
        client = row["client"]
        client["runtime"].update(os="macOS-27.0.1-synthetic", machine="arm64")
        client["rss_native_unit"] = "bytes"
        client["baseline_rss_method"] = "darwin.MACH_TASK_BASIC_INFO.resident_size"
        for prefix in ("baseline", "pretransfer_peak", "peak"):
            client[prefix + "_rss_native"] = client[prefix + "_rss_bytes"]
        del client["baseline_rss_pages"], client["rss_page_bytes"]
    return report


@pytest.mark.parametrize(
    "damage", [None, "source", "oracle", "lock", "failed", "host", "not_reference"]
)
def test_actual_catalog_reference_gate_requires_current_bytes_and_declared_reference(
    tmp_path, monkeypatch, damage
):
    checks = runpy.run_path(str(ROOT / "scripts/research_evidence.py"))
    evidence = runpy.run_path(str(ROOT / "scripts/upload_evidence.py"))
    report = reference(evidence)
    current = copy.deepcopy(report["provenance"]["source_before"])
    locked = copy.deepcopy(report["provenance"]["locked_runtime"])
    if damage in {"source", "oracle"}:
        key = "src/yorunge/__init__.py" if damage == "source" else evidence["VECTOR_PATH"]
        current["source_sha256"][key] = "9" * 64
    elif damage == "lock":
        locked["httpx"] = "0.28.2"
    elif damage == "failed":
        report["runs"][0]["client"]["elapsed_seconds"] = 901
        report["runs"][0]["passed"] = report["passed"] = False
    elif damage == "host":
        report["environment"]["cpu"] = "synthetic"
    elif damage == "not_reference":
        report = installation()
    original = runpy.run_path

    def load(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        if Path(path).name == "upload_evidence.py":
            result["source"] = lambda root: current
            result["STREAM"] = {**result["STREAM"], "locked_runtime": lambda root: locked}
        return result

    monkeypatch.setattr(runpy, "run_path", load)
    (tmp_path / "dist").mkdir()
    (tmp_path / "docs/research").mkdir(parents=True)
    name = "p02-2-reference-upload-03.json"
    source = tmp_path / "dist" / name
    source.write_bytes(checks["encode"](report))
    checks["archive_report"](tmp_path, source, None)
    if damage is None:
        result = checks["verify_upload_reference"](tmp_path, name)
        assert result["passed"] is True
        assert result["cases"] == 12
        assert result["name"] == name
    else:
        with pytest.raises(ValueError):
            checks["verify_upload_reference"](tmp_path, name)
