"""Bounded real TLS smoke and negative guards for the raw-stream RSS tool.

Small fixtures prove the measurement path; none is a 1GiB performance acceptance.
"""

import copy
import hashlib
import json
import os
import platform
import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.contracts.test_installed_transport import runtime_tree as runtime_tree  # noqa: F401
from tests.fixtures import stream_budget
from tests.fixtures.http_server import certificate

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/benchmark-stream.py"


def helpers():
    return runpy.run_path(str(SCRIPT))


def test_readiness_is_invisible_until_the_complete_json_is_published(tmp_path, monkeypatch):
    ready = tmp_path / "ready.json"
    payload = {"port": 12345, "pid": 67890}
    serialized = json.dumps(payload)

    def paused_write(value, target):
        assert value == payload
        target.write(serialized[:3])
        target.flush()
        assert not ready.exists()
        target.write(serialized[3:])

    monkeypatch.setattr(stream_budget.json, "dump", paused_write)
    stream_budget.publish_ready(ready, payload)
    assert json.loads(ready.read_text()) == payload
    assert list(tmp_path.iterdir()) == [ready]


def test_readiness_publication_preserves_an_existing_file(tmp_path):
    ready = tmp_path / "ready.json"
    original = b'{"port": 12345, "pid": 67890}'
    ready.write_bytes(original)
    payload = {"port": 54321, "pid": 9876}
    with pytest.raises(FileExistsError):
        stream_budget.publish_ready(ready, payload)
    assert ready.read_bytes() == original
    assert list(tmp_path.iterdir()) == [ready]


def test_failed_readiness_write_leaves_no_partial_file(tmp_path, monkeypatch):
    ready = tmp_path / "ready.json"
    payload = {"port": 12345, "pid": 67890}

    def failed_write(_value, target):
        target.write("{")
        target.flush()
        raise OSError("synthetic readiness I/O failure")

    monkeypatch.setattr(stream_budget.json, "dump", failed_write)
    with pytest.raises(OSError, match="synthetic readiness I/O failure"):
        stream_budget.publish_ready(ready, payload)
    assert not ready.exists()
    assert list(tmp_path.iterdir()) == []


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
    expected_sha256 = helpers()["expected_sha256"]
    with pytest.raises(ValueError, match="expected size"):
        expected_sha256(size)


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
    evaluate_run = helpers()["evaluate_run"]
    payload = telemetry()
    with pytest.raises(ValueError):
        evaluate_run(record, payload, 65537, record["received_sha256"])


@pytest.mark.parametrize("reverse_dns_allowed", [True, False])
def test_small_fixture_uses_isolated_installed_client_and_separate_real_tls_process(
    runtime_tree, tmp_path, reverse_dns_allowed
):
    prefix, python, _ = runtime_tree
    tools = helpers()
    manifest = tmp_path / "manifest.json"
    source = tools["source"](ROOT)
    manifest.write_text(
        json.dumps(
            {
                "source_sha256": source["source_sha256"],
                "locked_runtime": tools["locked_runtime"](ROOT),
            }
        )
    )
    project = ROOT
    if not reverse_dns_allowed:
        project = tmp_path / "fixture-wrapper"
        helper = project / "tests/fixtures/stream_budget.py"
        helper.parent.mkdir(parents=True)
        helper.write_text(
            "import runpy, socket\n"
            "def denied(*args): raise AssertionError('fixture must not request reverse DNS')\n"
            "socket.getfqdn = denied\n"
            f"runpy.run_path({str(ROOT / 'tests/fixtures/stream_budget.py')!r}, "
            "run_name='__main__')\n"
        )
    work = tmp_path / "run"
    try:
        result = tools["measure_one"](
            project, python, work, manifest, certificate(tmp_path / "cert"), 65537
        )
    except ValueError as error:
        stderr = work / "server-stderr.txt"
        tail = "not available"
        if stderr.is_file():
            with stderr.open("rb") as reader:
                reader.seek(0, os.SEEK_END)
                reader.seek(max(0, reader.tell() - 4096))
                tail = reader.read(4096).decode("utf-8", errors="replace")
        pytest.fail(
            f"{error}; host={platform.platform()}; cpu={platform.processor() or 'unknown'}; "
            f"python={sys.version.split()[0]}; source={source['commit']}; "
            f"synthetic server stderr tail (max 4096 bytes)={tail!r}",
            pytrace=False,
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
    manifest.write_text(
        json.dumps({"source_sha256": source, "locked_runtime": helpers()["locked_runtime"](ROOT)})
    )
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
    new_path = helpers()["new_path"]
    with pytest.raises(ValueError, match="new path"):
        new_path(report)
    if kind == "file":
        assert report.read_text() == "original"
    if kind == "symlink":
        assert target.read_text() == "original"


@pytest.mark.parametrize(
    "drift", ["source_bytes", "head_only", "runtime_packages", "runtime_python"]
)
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
    elif drift == "source_bytes":
        changed_source["source_sha256"]["src/yorunge/__init__.py"] = "0" * 64

    def source(project):
        return original_source if not calls else changed_source

    def measure(project, python, work, manifest, certificates, size):
        work.mkdir()
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
        if len(calls) == 2 and drift.startswith("runtime_"):
            field = drift.removeprefix("runtime_")
            record["runtime"][field] = (
                {"httpx": "0.0.0"} if field == "packages" else "changed-python"
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
    assert result["provenance"]["source_unchanged_during_measurement"] is drift.startswith(
        "runtime_"
    )
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


def test_client_rejects_dependency_drift_with_unchanged_product_sources(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"source_sha256": {}, "locked_runtime": {"httpx": "0.28.1"}}))
    before = {"installed_source_sha256": {"__init__.py": "a" * 64}, "packages": {"httpx": "0.28.1"}}
    after = copy.deepcopy(before)
    after["packages"]["httpx"] = "0.0.0"
    snapshots = iter([before, after])
    monkeypatch.setattr(stream_budget, "installed_provenance", lambda *args: next(snapshots))
    monkeypatch.setattr(stream_budget, "sys", SimpleNamespace(flags=SimpleNamespace(isolated=True)))

    async def consume(*args):
        return measurement()

    monkeypatch.setattr(stream_budget, "consume", consume)
    args = SimpleNamespace(
        size=1,
        manifest=manifest,
        prefix=tmp_path,
        port=1,
        ca=tmp_path / "unused",
        total_seconds=120,
    )
    with pytest.raises(ValueError, match="installed runtime changed"):
        stream_budget.client(args)


@pytest.mark.parametrize("mutation", ["wrong_version", "unexpected", "duplicate", "missing"])
def test_frozen_package_set_is_checked_before_tls(runtime_tree, tmp_path, mutation):
    """Mutate actual installed metadata; no server is listening and no CA exists."""
    prefix, python, site = runtime_tree
    tools = helpers()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "source_sha256": tools["source"](ROOT)["source_sha256"],
                "locked_runtime": tools["locked_runtime"](ROOT),
            }
        )
    )
    restored = None
    created = None
    removed = None
    if mutation == "wrong_version":
        metadata = next(site.glob("httpx-*.dist-info/METADATA"))
        restored = metadata, metadata.read_bytes()
        metadata.write_text(metadata.read_text().replace("Version: 0.28.1", "Version: 0.0.0", 1))
    elif mutation in {"unexpected", "duplicate"}:
        created = site / "injected-1.0.dist-info"
        created.mkdir()
        name = "HTTPX" if mutation == "duplicate" else "unexpected-runtime-helper"
        (created / "METADATA").write_text(f"Metadata-Version: 2.4\nName: {name}\nVersion: 1.0\n")
    else:
        metadata = next(site.glob("[Pp][Yy][Yy][Aa][Mm][Ll]-*.dist-info"))
        removed = metadata, tmp_path / "removed-metadata"
        metadata.rename(removed[1])
    try:
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
        assert (
            "duplicate normalized installed distribution"
            if mutation == "duplicate"
            else "do not match the frozen runtime closure"
        ) in child.stderr
        assert "ConnectError" not in child.stderr
        assert not child.stdout
    finally:
        if restored is not None:
            restored[0].write_bytes(restored[1])
        if created is not None:
            (created / "METADATA").unlink()
            created.rmdir()
        if removed is not None:
            removed[1].rename(removed[0])


@pytest.mark.parametrize("first_passed", [True, False])
@pytest.mark.parametrize("fail_on", [2, 3])
def test_completed_receipts_survive_later_worker_failure(
    tmp_path, monkeypatch, first_passed, fail_on
):
    """Control-flow fixture: preserve truthful run data without inventing acceptance."""
    tools = helpers()
    check = tools["check"]
    original_source = tools["source"](ROOT)
    calls, completed = [], {}
    failure = ValueError("private exception detail must not enter the failure receipt")

    def measure(project, python, work, manifest, certificates, size):
        work.mkdir()
        for previous_size, previous in completed.items():
            # The earlier receipt must already exist before this worker starts.
            retained = work.parent / str(previous_size // 1024**2) / "measurement.json"
            assert json.loads(retained.read_text()) == previous
        calls.append(size)
        if len(calls) == fail_on:
            (work / "client-stderr.txt").write_text("retained private subprocess diagnostic")
            raise failure
        record = measurement(size)
        record.update(passed=first_passed if len(calls) == 1 else True, server=telemetry(size))
        completed[size] = record
        return record

    monkeypatch.setitem(check.__globals__, "source", lambda project: original_source)
    monkeypatch.setitem(check.__globals__, "measure_one", measure)
    monkeypatch.setitem(
        check.__globals__,
        "runpy",
        SimpleNamespace(run_path=lambda path: {"certificate": lambda path: (path, path)}),
    )
    output, workspace = tmp_path / "report.json", tmp_path / "work"
    with pytest.raises(ValueError) as caught:
        check(ROOT, Path(sys.executable), workspace, output, cpu="unknown", disk="unknown")
    assert caught.value is failure
    assert not output.exists()
    for size, original in completed.items():
        retained = json.loads((workspace / str(size // 1024**2) / "measurement.json").read_text())
        assert retained == original
        assert retained["server"]["requests"][1]["size_bytes"] == size
    first = json.loads((workspace / "16" / "measurement.json").read_text())
    assert first["passed"] is first_passed
    failed_size = tools["SIZES_MIB"][fail_on - 1]
    failed = json.loads((workspace / str(failed_size) / "failure.json").read_text())
    assert failed == {
        "error_type": "ValueError",
        "size_bytes": failed_size * 1024**2,
        "diagnostics": ["client-stderr.txt"],
    }
    assert "private" not in json.dumps(failed)
    assert not (workspace / str(failed_size) / "measurement.json").exists()


def test_server_startup_exit_is_distinct_and_retains_diagnostics(tmp_path):
    project = tmp_path / "fixture"
    helper = project / "tests/fixtures/stream_budget.py"
    helper.parent.mkdir(parents=True)
    helper.write_text(
        "import sys\nsys.stderr.write('forced synthetic startup failure\\n')\n"
        "raise SystemExit(23)\n"
    )
    work = tmp_path / "run"
    measure_one = helpers()["measure_one"]
    python = Path(sys.executable)
    with pytest.raises(ValueError, match="server exited before readiness.*23"):
        measure_one(
            project,
            python,
            work,
            tmp_path / "unused-manifest",
            (tmp_path / "unused-cert", tmp_path / "unused-key"),
            65537,
        )
    assert (work / "server-stderr.txt").read_text() == "forced synthetic startup failure\n"
    assert not (work / "ready.json").exists()


def test_client_timeout_keeps_partial_diagnostics_and_original_exception(tmp_path, monkeypatch):
    certs = certificate(tmp_path / "cert")
    failure = subprocess.TimeoutExpired(
        "synthetic-client", 270, output=b"partial stdout", stderr=b"partial stderr"
    )

    def expired(*args, **kwargs):
        raise failure

    monkeypatch.setattr(subprocess, "run", expired)
    work = tmp_path / "run"
    measure_one = helpers()["measure_one"]
    python = Path(sys.executable)
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        measure_one(ROOT, python, work, tmp_path / "unused-manifest", certs, 65537)
    assert caught.value is failure
    assert (work / "client-stdout.txt").read_text() == "partial stdout"
    assert (work / "client-stderr.txt").read_text() == "partial stderr"
    assert (work / "server-stdout.txt").is_file()
    assert (work / "server-stderr.txt").is_file()


def test_live_server_readiness_timeout_is_distinct_without_waiting_for_the_deadline(
    tmp_path, monkeypatch
):
    tools = helpers()
    measure = tools["measure_one"]
    project = tmp_path / "fixture"
    helper = project / "tests/fixtures/stream_budget.py"
    helper.parent.mkdir(parents=True)
    helper.write_text("import signal\nsignal.pause()\n")
    clock = iter([0.0, 11.0])
    monkeypatch.setitem(measure.__globals__, "time", SimpleNamespace(monotonic=lambda: next(clock)))
    work = tmp_path / "run"
    with pytest.raises(
        ValueError, match="readiness timed out after 10 seconds while process was running"
    ):
        measure(
            project,
            Path(sys.executable),
            work,
            tmp_path / "unused-manifest",
            (tmp_path / "unused-cert", tmp_path / "unused-key"),
            65537,
        )
    assert not (work / "ready.json").exists()
    assert (work / "server-stderr.txt").is_file()


@pytest.mark.parametrize("failure_kind", ["timeout", "value_error"])
def test_server_log_write_error_preserves_original_worker_exception(
    tmp_path, monkeypatch, failure_kind
):
    certs = certificate(tmp_path / "cert")
    failure = (
        subprocess.TimeoutExpired("synthetic-client", 270, stderr=b"partial")
        if failure_kind == "timeout"
        else ValueError("synthetic worker failure")
    )
    write_text = Path.write_text

    def denied(self, *args, **kwargs):
        if self.name == "server-stderr.txt":
            raise PermissionError("synthetic diagnostic write denial")
        return write_text(self, *args, **kwargs)

    def failed(*args, **kwargs):
        raise failure

    monkeypatch.setattr(Path, "write_text", denied)
    monkeypatch.setattr(subprocess, "run", failed)
    measure_one = helpers()["measure_one"]
    python = Path(sys.executable)
    with pytest.raises(type(failure)) as caught:
        measure_one(ROOT, python, tmp_path / "run", tmp_path / "unused", certs, 65537)
    assert caught.value is failure
    assert (tmp_path / "run/server-stdout.txt").is_file()


def test_server_log_write_error_still_fails_without_measurement_error(tmp_path, monkeypatch):
    """A caller's enclosing except block is not an error in this measurement."""
    certs = certificate(tmp_path / "cert")
    failure = PermissionError("synthetic diagnostic write denial")
    write_text = Path.write_text

    def denied(self, *args, **kwargs):
        if self.name == "server-stderr.txt":
            raise failure
        return write_text(self, *args, **kwargs)

    def completed(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, json.dumps(measurement()), "")

    monkeypatch.setattr(Path, "write_text", denied)
    monkeypatch.setattr(subprocess, "run", completed)
    try:
        raise ValueError("outer caller exception")
    except ValueError:
        measure_one = helpers()["measure_one"]
        python = Path(sys.executable)
        with pytest.raises(PermissionError) as caught:
            measure_one(ROOT, python, tmp_path / "run", tmp_path / "unused", certs, 65537)
    assert caught.value is failure
    assert (tmp_path / "run/server-stdout.txt").is_file()
