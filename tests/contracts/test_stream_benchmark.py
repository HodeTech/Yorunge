"""Bounded real TLS smoke and negative guards for the raw-stream RSS tool.

Small fixtures prove the measurement path; none is a 1GiB performance acceptance.
"""

import copy
import hashlib
import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from tests.contracts.test_installed_transport import runtime_tree as runtime_tree  # noqa: F401
from tests.fixtures import stream_budget
from tests.fixtures.http_server import certificate

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/benchmark-stream.py"


def helpers():
    return runpy.run_path(str(SCRIPT))


@pytest.mark.parametrize(
    "size,expected",
    [
        (1, "6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d"),
        (256, "40aff2e9d2d8922e47afd4648e6967497158785fbd1da870e7110266bf944880"),
        (32768, "e11360251d1173650cdcd20f111d8f1ca2e412f572e8b36a4dc067121c1799b8"),
    ],
)
def test_expected_digest_has_independent_fixed_vectors(size, expected):
    assert helpers()["expected_sha256"](size) == expected


@pytest.mark.parametrize("size", [True, 0, -1, 1.5, 1024 * 1024 * 1024 + 1])
def test_expected_digest_rejects_unbounded_or_noninteger_size(size):
    with pytest.raises(ValueError, match="expected size"):
        helpers()["expected_sha256"](size)


@pytest.mark.parametrize(
    "native,system,expected", [(1000, "Darwin", 1000), (1000, "Linux", 1024000)]
)
def test_rss_native_units_are_converted_without_counting_server_or_children(
    native, system, expected
):
    assert stream_budget.rss_bytes(native, system) == expected


@pytest.mark.parametrize(
    "native,system", [(1, "Windows"), (True, "Linux"), (-1, "Linux"), (float("inf"), "Darwin")]
)
def test_rss_rejects_unknown_units_or_invalid_numbers(native, system):
    with pytest.raises(ValueError):
        stream_budget.rss_bytes(native, system)


def measurement(size=65537):
    digest = hashlib.sha256(bytes(range(256)) * 256 + b"\x00").hexdigest()
    return {
        "size_bytes": size,
        "stream_count": 1,
        "received_bytes": size,
        "received_sha256": digest,
        "baseline_rss_native": 100_000_000,
        "peak_rss_native": 100_000_000,
        "rss_native_unit": "bytes",
        "baseline_rss_bytes": 100_000_000,
        "peak_rss_bytes": 100_000_000,
        "extra_rss_bytes": 0,
        "elapsed_seconds": 0.1,
        "max_chunk_bytes": 32768,
        "chunk_count": 3,
        "warmup_requests": 1,
        "measurement_requests": 1,
        "runtime": {"isolated": True, "installed_source_matches": True},
    }


def telemetry(size=65537):
    return {
        "request_count": 2,
        "connection_count": 1,
        "peak_active_requests": 1,
        "requests": [
            {"size_bytes": 32768, "sent_bytes": 32768, "completed": True},
            {"size_bytes": size, "sent_bytes": size, "completed": True},
        ],
    }


def test_rss_gate_is_exact_and_keeps_failed_measured_values():
    evaluate = helpers()["evaluate_run"]
    value = measurement()
    for extra, passed in [(67108864, True), (67108865, False)]:
        value.update(
            peak_rss_bytes=value["baseline_rss_bytes"] + extra,
            peak_rss_native=value["baseline_rss_bytes"] + extra,
            extra_rss_bytes=extra,
        )
        result = evaluate(value, telemetry(), 65537, value["received_sha256"])
        assert result["passed"] is passed
        assert result["extra_rss_bytes"] == extra


@pytest.mark.parametrize(
    "field,value",
    [
        ("received_bytes", 65536),
        ("received_sha256", "0" * 64),
        ("max_chunk_bytes", 32769),
        ("stream_count", True),
        ("warmup_requests", 0),
        ("measurement_requests", 2),
    ],
)
def test_wrong_bytes_unbounded_chunks_or_hidden_requests_cannot_pass(field, value):
    record = measurement()
    expected = record["received_sha256"]
    record[field] = value
    assert helpers()["evaluate_run"](record, telemetry(), 65537, expected)["passed"] is False


@pytest.mark.parametrize(
    "field,value", [("request_count", 3), ("connection_count", 3), ("peak_active_requests", 3)]
)
def test_server_counts_limit_actual_requests_and_connections(field, value):
    server = telemetry()
    server[field] = value
    record = measurement()
    assert (
        helpers()["evaluate_run"](record, server, 65537, record["received_sha256"])["passed"]
        is False
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"extra_rss_bytes": 1},
        {"peak_rss_bytes": 1},
        {"baseline_rss_bytes": True},
        {"elapsed_seconds": float("nan")},
    ],
)
def test_inconsistent_or_nonfinite_measurements_are_rejected(changes):
    record = measurement()
    record.update(changes)
    with pytest.raises(ValueError):
        helpers()["evaluate_run"](record, telemetry(), 65537, record["received_sha256"])


def test_small_fixture_uses_isolated_installed_client_and_separate_real_tls_process(
    runtime_tree, tmp_path
):
    prefix, python, _ = runtime_tree
    tools = helpers()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(tools["source"](ROOT)["source_sha256"]))
    result = tools["measure_one"](
        ROOT, python, tmp_path / "run", manifest, certificate(tmp_path / "cert"), 65537
    )
    assert result["passed"] is True
    assert (
        result["expected_sha256"]
        == "2deb0bd2129a9d3aed91e3cff58b3993752be549642890a3e853ec1065f9b617"
    )
    assert result["received_bytes"] == 65537
    assert result["runtime"]["isolated"] is True
    assert Path(result["runtime"]["prefix"]) == prefix
    assert "pytest" not in result["runtime"]["packages"]
    assert result["server"]["pid"] != result["runtime"]["pid"]
    assert result["peak_rss_bytes"] >= result["baseline_rss_bytes"] > 0
    assert result["extra_rss_bytes"] == result["peak_rss_bytes"] - result["baseline_rss_bytes"]
    assert result["chunk_count"] >= 3
    assert result["request_count"] == 2
    assert result["connection_count"] <= 2


def test_isolated_source_manifest_mismatch_fails_before_any_tls_connection(runtime_tree, tmp_path):
    prefix, python, _ = runtime_tree
    source = helpers()["source"](ROOT)["source_sha256"]
    source["src/yorunge/__init__.py"] = "0" * 64
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(source))
    child = subprocess.run(
        [
            str(python),
            "-I",
            str(ROOT / "tests/fixtures/stream_budget.py"),
            "client",
            "--ca",
            str(tmp_path / "missing.pem"),
            "--port",
            "1",
            "--size",
            "1",
            "--manifest",
            str(manifest),
            "--prefix",
            str(prefix),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert child.returncode != 0
    assert "installed package bytes do not match" in child.stderr
    assert "ConnectError" not in child.stderr
    assert not child.stdout


@pytest.mark.parametrize(
    "kind", ["file", "symlink", "dangling_symlink", "parent_symlink", "missing_parent"]
)
def test_output_is_explicit_new_path_and_never_overwrites_existing_evidence(tmp_path, kind):
    target, report = tmp_path / "target.json", tmp_path / "report.json"
    if kind == "file":
        report.write_text("original")
    elif kind in {"symlink", "dangling_symlink"}:
        if kind == "symlink":
            target.write_text("original")
        report.symlink_to(target)
    elif kind == "parent_symlink":
        (tmp_path / "alias").symlink_to(tmp_path, target_is_directory=True)
        report = tmp_path / "alias" / "report.json"
    else:
        report = tmp_path / "missing" / "report.json"
    with pytest.raises(ValueError, match="new path"):
        helpers()["new_path"](report)
    if kind == "file":
        assert report.read_text() == "original"
    if kind == "symlink":
        assert target.read_text() == "original"


@pytest.mark.parametrize("drift", ["source_bytes", "head_only"])
def test_full_orchestrator_keeps_all_three_required_sizes_and_source_change_failure(
    tmp_path, monkeypatch, drift
):
    tools = helpers()
    check = tools["check"]
    calls = []
    original_source = tools["source"](ROOT)
    changed_source = copy.deepcopy(original_source)
    if drift == "head_only":
        changed_source["commit"] = "0" * 40
        assert changed_source["source_sha256"] == original_source["source_sha256"]
    else:
        changed_source["source_sha256"]["src/yorunge/__init__.py"] = "0" * 64

    def source(project):
        return original_source if not calls else changed_source

    def measure(project, python, work, manifest, certificates, size):
        calls.append(size)
        record = measurement(size)
        record.update(
            passed=True,
            runtime={
                "installed_source_matches": True,
                "os": "test",
                "machine": "test",
                "python": "test",
                "python_executable": "test",
                "sqlite": "test",
                "packages": {},
            },
        )
        return record

    monkeypatch.setitem(check.__globals__, "source", source)
    monkeypatch.setitem(check.__globals__, "measure_one", measure)
    monkeypatch.setitem(
        check.__globals__,
        "runpy",
        type(
            "Fixture",
            (),
            {"run_path": staticmethod(lambda path: {"certificate": lambda path: (path, path)})},
        ),
    )
    output = tmp_path / "report.json"
    assert (
        check(ROOT, Path(sys.executable), tmp_path / "work", output, cpu="unknown", disk="unknown")
        == 1
    )
    result = json.loads(output.read_text())
    assert calls == [16 * 1024**2, 256 * 1024**2, 1024**3]
    assert result["passed"] is False
    assert result["provenance"]["source_unchanged_during_measurement"] is False
    assert result["source_commit"] == original_source["commit"]
    assert result["provenance"]["source_before"] == original_source
    assert result["provenance"]["source_after"] == changed_source
    if drift == "head_only":
        assert (
            result["provenance"]["source_before"]["source_sha256"]
            == result["provenance"]["source_after"]["source_sha256"]
        )
        assert (
            result["provenance"]["source_before"]["commit"]
            != result["provenance"]["source_after"]["commit"]
        )
