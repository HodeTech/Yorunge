"""Independent native-RSS rejection oracles and the real isolated dataset worker."""

import copy
import hashlib
import json
import runpy
import subprocess
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.contracts.test_installed_transport import runtime_tree as runtime_tree  # noqa: F401
from tests.fixtures.dataset_budget import canonical_artifact

ROOT = Path(__file__).resolve().parents[2]
CHECKS = runpy.run_path(str(ROOT / "scripts/benchmark-datasets.py"))


def receipt():
    source = {
        "commit": "a" * 40,
        "source_sha256": {"src/yorunge/__init__.py": "1" * 64, "src/yorunge/py.typed": "3" * 64},
    }
    packages = {"yorunge": "0.1.0.dev0", "pydantic": "2.14.1"}
    runtime = {
        "prefix": "/tmp/env",
        "pid": 1,
        "modules": {"yorunge": "/tmp/env/lib/yorunge/__init__.py"},
        "installed_source_sha256": {"__init__.py": "1" * 64},
        "installed_source_matches": True,
        "metadata": "/tmp/env/lib",
        "packages": packages,
        "python": "3.11.18",
        "python_executable": "/tmp/env/bin/python",
        "isolated": True,
        "sqlite": "3.51.0",
        "os": "macOS-27.0.1-arm64-arm-64bit",
        "machine": "arm64",
    }
    fixtures, runs = {}, []
    for label in CHECKS["LABELS"]:
        expected = CHECKS["expected_manifest"](label)
        fixtures[label] = CHECKS["fixture_summary"](expected, label)
        for action in ("inspect", "verify"):
            for sample in range(1, 4):
                runs.append(
                    {
                        "action": action,
                        "label": label,
                        "sample": sample,
                        "manifest_digest": expected["digest"],
                        "file_count": expected["file_count"],
                        "total_bytes": expected["total_bytes"],
                        "result_valid": True,
                        "elapsed_seconds": 0.1,
                        "baseline_rss_native": 10 * 1024**2,
                        "baseline_rss_bytes": 10 * 1024**2,
                        "baseline_rss_method": "darwin.MACH_TASK_BASIC_INFO.resident_size",
                        "pretransfer_peak_rss_native": 12 * 1024**2,
                        "pretransfer_peak_rss_bytes": 12 * 1024**2,
                        "peak_rss_native": 14 * 1024**2,
                        "peak_rss_bytes": 14 * 1024**2,
                        "rss_native_unit": "bytes",
                        "extra_rss_lower_bound_bytes": 4 * 1024**2,
                        "extra_rss_upper_bound_bytes": 4 * 1024**2,
                        "runtime": {**runtime, "pid": len(runs) + 1},
                        "runtime_data_sha256": {"src/yorunge/py.typed": "3" * 64},
                        "distribution_metadata_sha256": {
                            name: "4" * 64 for name in CHECKS["WHEEL"]["METADATA_FILES"]
                        },
                        "passed": True,
                    }
                )
    return {
        "schema_version": 1,
        "report_kind": "dataset_hash_budget_v1",
        "source_commit": "a" * 40,
        "environment": {"cpu": "Apple M5 Max", "disk_type": "internal SSD/APFS"},
        "provenance": {
            "source_before": source,
            "source_after": copy.deepcopy(source),
            "locked_runtime": packages,
            "wheel_before": "2" * 64,
            "wheel_after": "2" * 64,
            "wheel_product_sha256": copy.deepcopy(source["source_sha256"]),
            "wheel_metadata_sha256": {name: "4" * 64 for name in CHECKS["WHEEL"]["METADATA_FILES"]},
        },
        "fixtures": fixtures,
        "runs": runs,
        "growth": {
            action: {"span_upper_bound_bytes": 0, "passed": True}
            for action in ("inspect", "verify")
        },
        "passed": True,
    }


def test_complete_dataset_report_has_24_distinct_workers_and_independent_fixture_oracles():
    report = receipt()
    summary = CHECKS["summarize_report"](report)
    assert summary["passed"] is True
    assert summary["cases"] == 24
    assert report["fixtures"]["capacity"] == {
        "file_count": 4096,
        "directory_count": 4096,
        "total_bytes": 4096,
        "digest": CHECKS["expected_manifest"]("capacity")["digest"],
    }
    archive = runpy.run_path(str(ROOT / "scripts/research_evidence.py"))
    assert archive["payload_summary"](report) == summary


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate_case",
        "reused_pid",
        "bool_sample",
        "bool_fixture",
        "unknown_fixture",
        "bad_artifact",
        "bad_bytes",
        "bad_count",
        "invalid_result",
        "zero_time",
        "timeout",
        "hwm_order",
        "rss_interval",
        "native_unit",
        "rss_limit",
        "unisolated",
        "source_changed",
        "wheel_changed",
        "escaped_origin",
        "wrong_package",
        "false_growth",
        "bool_growth",
        "extra",
    ],
)
def test_forged_or_incomplete_dataset_acceptance_is_rejected(mutation):
    report = receipt()
    row = report["runs"][0]
    if mutation == "missing":
        report["runs"].pop()
    elif mutation == "duplicate_case":
        report["runs"][-1] = copy.deepcopy(row)
    elif mutation == "reused_pid":
        report["runs"][1]["runtime"]["pid"] = row["runtime"]["pid"]
    elif mutation == "bool_sample":
        row["sample"] = True
    elif mutation == "bool_fixture":
        report["fixtures"]["16"]["file_count"] = True
    elif mutation == "unknown_fixture":
        row["label"] = "8"
    elif mutation == "bad_artifact":
        row["manifest_digest"] = "0" * 64
    elif mutation == "bad_bytes":
        row["total_bytes"] -= 1
    elif mutation == "bad_count":
        row["file_count"] += 1
    elif mutation == "invalid_result":
        row["result_valid"] = False
    elif mutation == "zero_time":
        row["elapsed_seconds"] = 0
    elif mutation == "timeout":
        row["elapsed_seconds"] = 30.000001
    elif mutation == "hwm_order":
        row["pretransfer_peak_rss_bytes"] = row["peak_rss_bytes"] + 1
    elif mutation == "rss_interval":
        row["extra_rss_upper_bound_bytes"] = 0
    elif mutation == "native_unit":
        row["rss_native_unit"] = "KiB"
    elif mutation == "rss_limit":
        row["peak_rss_native"] = row["peak_rss_bytes"] = 75 * 1024**2
        row["extra_rss_lower_bound_bytes"] = row["extra_rss_upper_bound_bytes"] = 65 * 1024**2
    elif mutation == "unisolated":
        row["runtime"]["isolated"] = False
    elif mutation == "source_changed":
        report["provenance"]["source_after"]["source_sha256"]["src/yorunge/__init__.py"] = "0" * 64
    elif mutation == "wheel_changed":
        report["provenance"]["wheel_after"] = "3" * 64
    elif mutation == "escaped_origin":
        row["runtime"]["modules"]["yorunge"] = "/outside/__init__.py"
    elif mutation == "wrong_package":
        row["runtime"]["packages"] = {"yorunge": "wrong"}
    elif mutation == "false_growth":
        report["growth"]["inspect"]["span_upper_bound_bytes"] = 1
    elif mutation == "bool_growth":
        report["growth"]["inspect"]["passed"] = 1
    else:
        row["extra"] = True
    with pytest.raises(ValueError):
        CHECKS["summarize_report"](report)


@pytest.mark.parametrize(
    "lower,upper,passed",
    [
        ([0, 0, 64], [60, 60, 64], False),
        ([1, 16, 64], [1, 16, 64], False),
        ([4, 4, 4], [4, 4, 4], True),
        ([0, 0, 0], [8, 8, 8], True),
        ([0, 0, 0], [8, 8, 9], False),
    ],
)
def test_native_interval_growth_never_subtracts_old_hwm(lower, upper, passed):
    runs = [
        {
            "label": label,
            "extra_rss_lower_bound_bytes": low * 1024**2,
            "extra_rss_upper_bound_bytes": high * 1024**2,
        }
        for label, low, high in zip(("16", "256", "1024"), lower, upper, strict=True)
    ]
    assert CHECKS["growth_acceptance"](runs)["passed"] is passed


def test_real_installed_worker_hashes_and_verifies_fixed_16mib_oracle(runtime_tree, tmp_path):
    _, python, site = runtime_tree
    metadata = site / "yorunge-0.1.0.dev0.dist-info"
    (metadata / "WHEEL").write_text("Wheel-Version: 1.0\n")
    (metadata / "entry_points.txt").write_text("[console_scripts]\nyorunge = yorunge.cli:main\n")
    source = CHECKS["SOURCES"]["source"](ROOT)
    locked = CHECKS["STREAM"]["locked_runtime"](ROOT)
    receipt_path = tmp_path / "source-manifest.json"
    receipt_path.write_text(
        json.dumps({"source_sha256": source["source_sha256"], "locked_runtime": locked})
    )
    expected = CHECKS["expected_manifest"]("16")
    root = tmp_path / "source"
    CHECKS["prepare_fixture"](root, expected, "16")
    expected_path = tmp_path / "expected.json"
    expected_path.write_text(
        json.dumps(expected, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    for action in ("inspect", "verify"):
        result = CHECKS["measure_one"](
            python, tmp_path, root, expected_path, receipt_path, action, "16", 1
        )
        assert result["result_valid"] is True
        assert result["total_bytes"] == 16 * 1024**2
        assert result["manifest_digest"] == expected["digest"]
        assert result["runtime"]["isolated"] is True
        assert CHECKS["STREAM"]["rss_interval"](result) >= 0
        assert result["elapsed_seconds"] > 0
    # This small correctness fixture is not the 24-process reference acceptance.


@pytest.fixture
def reference(tmp_path, monkeypatch):
    namespace = runpy.run_path(str(ROOT / "scripts/research_evidence.py"))
    function = namespace["verify_dataset_reference"]
    report = receipt()
    current = copy.deepcopy(report["provenance"]["source_before"])
    locked = copy.deepcopy(report["provenance"]["locked_runtime"])
    helper = {
        "summarize_report": CHECKS["summarize_report"],
        "SOURCES": {"source": lambda root: current},
        "STREAM": {"locked_runtime": lambda root: locked},
    }
    globals_ = function.__globals__
    monkeypatch.setitem(globals_, "verify", lambda root: 1)
    monkeypatch.setitem(globals_, "research_directory", lambda root: tmp_path)
    monkeypatch.setitem(globals_, "catalog", lambda directory: [{"name": "dataset-reference.json"}])
    monkeypatch.setitem(globals_, "unpack", lambda directory, item: json.dumps(report).encode())
    monkeypatch.setitem(globals_, "runpy", SimpleNamespace(run_path=lambda path: helper))
    return lambda: function(tmp_path, "dataset-reference.json"), report, current, locked


def test_dataset_reference_accepts_docs_only_commit_change_but_same_complete_source_bytes(
    reference,
):
    verify, _, current, _ = reference
    current["commit"] = "b" * 40
    assert verify()["passed"] is True


@pytest.mark.parametrize(
    "mutation",
    [
        "source",
        "extra_source",
        "missing_source",
        "lock",
        "cpu",
        "disk",
        "python",
        "os",
        "machine",
        "failed",
    ],
)
def test_dataset_reference_rejects_stale_source_runtime_and_failed_budgets(reference, mutation):
    verify, report, current, locked = reference
    if mutation == "source":
        current["source_sha256"]["src/yorunge/__init__.py"] = "0" * 64
    elif mutation == "extra_source":
        current["source_sha256"]["src/yorunge/extra.py"] = "0" * 64
    elif mutation == "missing_source":
        current["source_sha256"].pop("src/yorunge/py.typed")
    elif mutation == "lock":
        locked["pydantic"] = "2.14.2"
    elif mutation in ("cpu", "disk"):
        report["environment"]["cpu" if mutation == "cpu" else "disk_type"] = "unknown"
    elif mutation == "failed":
        report["runs"][0]["elapsed_seconds"] = 31
        report["runs"][0]["passed"] = report["passed"] = False
    else:
        for row in report["runs"]:
            row["runtime"][mutation] = "unknown"
    with pytest.raises(ValueError):
        verify()


@pytest.mark.parametrize(
    "path,value",
    [
        (("file_count",), True),
        (("file_count",), 1.0),
        (("schema_version",), True),
        (("schema_version",), 1.0),
        (("policy_version",), True),
        (("policy_version",), 1.0),
        (("files", 0, "size"), float(16 * 1024**2)),
    ],
)
def test_artifact_oracle_distinguishes_json_numeric_types(path, value):
    expected = CHECKS["expected_manifest"]("16")
    artifact = copy.deepcopy(expected)
    parent = artifact
    for part in path[:-1]:
        parent = parent[part]
    parent[path[-1]] = value
    assert artifact == expected  # The former dict oracle misses each of these differences.
    encoded = (
        json.dumps(artifact, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        + b"\n"
    )
    assert canonical_artifact(encoded, expected) is False


@pytest.mark.parametrize(
    "form", ["canonical", "no_lf", "extra_lf", "indent", "duplicate", "invalid_utf8"]
)
def test_artifact_oracle_requires_complete_independent_canonical_bytes(form):
    expected = CHECKS["expected_manifest"]("16")
    encoded = (
        json.dumps(expected, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        + b"\n"
    )
    if form == "no_lf":
        encoded = encoded[:-1]
    elif form == "extra_lf":
        encoded += b"\n"
    elif form == "indent":
        encoded = json.dumps(expected, indent=2).encode() + b"\n"
    elif form == "duplicate":
        encoded = encoded.replace(b'"file_count":1', b'"file_count":1,"file_count":1')
    elif form == "invalid_utf8":
        encoded += b"\xff"
    assert canonical_artifact(encoded, expected) is (form == "canonical")


@pytest.mark.parametrize("failure", ["timeout", "invalid_utf8", "nonzero"])
def test_worker_failure_preserves_original_binary_diagnostics(tmp_path, monkeypatch, failure):
    original_run = subprocess.run

    def run_child(command, **options):
        if failure == "timeout":
            code = (
                "import sys,time; print('partial measurement',flush=True); "
                "print('worker diagnostic',file=sys.stderr,flush=True); time.sleep(30)"
            )
            options["timeout"] = 1
        elif failure == "invalid_utf8":
            code = "import os; os.write(1,b'\\xff')"
        else:
            code = (
                "import os; os.write(1,b'partial'); os.write(2,b'\\xffdiagnostic'); "
                "raise SystemExit(9)"
            )
        return original_run([sys.executable, "-I", "-c", code], **options)

    function = CHECKS["measure_one"]
    monkeypatch.setitem(
        function.__globals__,
        "subprocess",
        SimpleNamespace(run=run_child, TimeoutExpired=subprocess.TimeoutExpired),
    )
    expected = subprocess.TimeoutExpired if failure == "timeout" else ValueError
    with pytest.raises(expected):
        function(
            Path(sys.executable),
            tmp_path,
            tmp_path / "root",
            tmp_path / "expected",
            tmp_path / "receipt",
            "inspect",
            "16",
            1,
        )
    work = tmp_path / "16-inspect-1"
    stdout, stderr = (work / "stdout.txt").read_bytes(), (work / "stderr.txt").read_bytes()
    if failure == "timeout":
        assert stdout == b"partial measurement\n"
        assert stderr == b"worker diagnostic\n"
        assert json.loads((work / "failure.json").read_bytes())["outcome"] == "worker_timeout"
    elif failure == "invalid_utf8":
        assert stdout == b"\xff"
        assert stderr == b""
    else:
        assert stdout == b"partial"
        assert stderr == b"\xffdiagnostic"


def wheel_fixture(tmp_path, mutation=None):
    contents = {
        "yorunge/__init__.py": b"__version__ = 'fixture'\n",
        "yorunge/py.typed": b"",
        "yorunge-0.1.0.dev0.dist-info/METADATA": (
            b"Metadata-Version: 2.4\nName: yorunge\nVersion: 0.1.0.dev0\n"
        ),
        "yorunge-0.1.0.dev0.dist-info/WHEEL": (
            b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        ),
        "yorunge-0.1.0.dev0.dist-info/entry_points.txt": (
            b"[console_scripts]\nyorunge = yorunge.cli:main\n"
        ),
    }
    expected = {
        "src/" + name: hashlib.sha256(content).hexdigest()
        for name, content in contents.items()
        if name.startswith("yorunge/")
    }
    if mutation == "product":
        contents["yorunge/__init__.py"] = b"different code"
    elif mutation == "marker":
        contents["yorunge/py.typed"] = b"different marker"
    elif mutation == "missing":
        contents.pop("yorunge/py.typed")
    elif mutation == "extra":
        contents["yorunge/extra.py"] = b"extra code"
    elif mutation == "metadata":
        contents["yorunge-0.1.0.dev0.dist-info/METADATA"] = b"Name: yorunge\nVersion: wrong\n"
    elif mutation == "entry_point":
        contents["yorunge-0.1.0.dev0.dist-info/entry_points.txt"] = (
            b"[console_scripts]\nyorunge = other:main\n"
        )
    elif mutation == "wheel":
        contents["yorunge-0.1.0.dev0.dist-info/WHEEL"] = b"Wheel-Version: 1.0\n"
    path = tmp_path / "yorunge-0.1.0.dev0-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in contents.items():
            archive.writestr(name, content)
    return path, expected


def test_wheel_snapshot_binds_all_product_marker_metadata_and_entry_bytes(tmp_path):
    path, expected = wheel_fixture(tmp_path)
    result = CHECKS["WHEEL"]["snapshot"](path, expected, "0.1.0.dev0")
    assert result["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result["product_sha256"] == expected
    with zipfile.ZipFile(path) as archive:
        assert result["metadata_sha256"] == {
            name: hashlib.sha256(archive.read("yorunge-0.1.0.dev0.dist-info/" + name)).hexdigest()
            for name in CHECKS["WHEEL"]["METADATA_FILES"]
        }


@pytest.mark.parametrize(
    "mutation",
    ["product", "marker", "missing", "extra", "metadata", "entry_point", "wheel", "not_zip"],
)
def test_unrelated_or_invalid_wheel_cannot_be_a_measurement_witness(tmp_path, mutation):
    path, expected = wheel_fixture(tmp_path, mutation)
    if mutation == "not_zip":
        path.write_bytes(b"not a wheel")
    with pytest.raises(ValueError):
        CHECKS["WHEEL"]["snapshot"](path, expected, "0.1.0.dev0")


@pytest.mark.parametrize(
    "which", ["wheel_product_sha256", "wheel_metadata_sha256", "distribution_metadata_sha256"]
)
def test_report_cannot_change_wheel_or_installed_metadata_binding(which):
    report = receipt()
    if which == "distribution_metadata_sha256":
        report["runs"][0][which]["METADATA"] = "0" * 64
    elif which == "wheel_product_sha256":
        report["provenance"][which]["src/yorunge/__init__.py"] = "0" * 64
    else:
        report["provenance"][which]["METADATA"] = "0" * 64
    with pytest.raises(ValueError):
        CHECKS["summarize_report"](report)
