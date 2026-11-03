"""Independent budget decisions and byte-preserving failure retention."""

import base64
import copy
import hashlib
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.fixtures.upload_report import report as report_vector

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def evidence():
    return runpy.run_path(str(ROOT / "scripts/upload_evidence.py"))


@pytest.fixture
def report(evidence):
    return report_vector(evidence["METHOD"], evidence["LIMITS"])


def test_closed_synthetic_report_recomputes_twelve_runs_and_fixed_oracle(evidence, report):
    result = evidence["summarize_report"](report)
    assert result == {
        "kind": "upload-budget",
        "cases": 12,
        "passed": True,
        "growth": {"span_upper_bound_bytes": 4_194_304, "passed": True},
        "max_elapsed_seconds": 1.0,
        "max_extra_rss_upper_bound_bytes": 4_194_304,
    }
    evidence["validate_vectors"](ROOT / evidence["VECTOR_PATH"])
    assert evidence["CHECKS"]["typed_summary"](report) == result


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("schema_version",), True),
        (("passed",), False),
        (("extra",), "unknown"),
        (("controller_pid",), True),
        (("runs", 0, "sample"), True),
        (("runs", 0, "client_process_pid"), 999),
        (("runs", 0, "server_process_pid"), 100),
        (("runs", 0, "client", "elapsed_seconds"), float("inf")),
        (("runs", 0, "client", "elapsed_seconds"), 0),
        (("runs", 0, "client", "peak_rss_bytes"), 1),
        (("runs", 0, "client", "extra_rss_lower_bound_bytes"), 4_194_304),
        (("runs", 0, "client", "rss_page_bytes"), 4097),
        (("runs", 0, "client", "runtime", "isolated"), False),
        (("runs", 0, "client", "runtime", "type_marker_sha256"), "0" * 64),
        (("runs", 0, "client", "runtime", "packages", "pytest"), "9.0"),
        (("runs", 0, "client", "runtime", "modules", "yorunge"), "/outside/yorunge.py"),
        (("runs", 0, "client", "metrics", "confirmed_bytes"), 1),
        (("runs", 0, "client", "metrics", "source_bytes"), True),
        (("runs", 0, "client", "metrics", "sessions", 2, "effect_attempts"), 1),
        (("runs", 0, "client", "metrics", "put_seconds"), []),
        (("runs", 0, "client", "metrics", "put_seconds", 0), 0.2),
        (("runs", 0, "client", "metrics", "peak_connections"), 9),
        (("runs", 0, "client", "graph", "receipts"), []),
        (("runs", 0, "client", "graph", "intents", 0, "kind"), "put"),
        (("runs", 0, "client", "graph", "files", 0, "item_id"), "0" * 36),
        (("runs", 0, "client", "public", "authority_verified"), True),
        (("runs", 0, "server", "requests", "GET"), 1),
        (("runs", 0, "server", "control_bytes"), True),
        (("runs", 0, "warm_server", "received", 0, "size"), 1),
    ],
)
def test_false_or_malformed_measurement_is_rejected(evidence, report, path, value):
    target = report
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        evidence["summarize_report"](report)


@pytest.mark.parametrize("field", ["path", "size", "sha256"])
def test_consistent_wrong_producer_and_sink_cannot_replace_independent_oracle(
    evidence, report, field
):
    row = report["runs"][0]
    value = {"path": "other.bin", "size": 1, "sha256": "0" * 64}[field]
    row["server"]["received"][0][field] = value
    remote_field = {
        "path": "original_filename",
        "size": "file_size_bytes",
        "sha256": "sha256_hash",
    }[field]
    row["server"]["items"][0][remote_field] = value
    graph_field = {"path": "path_digest", "size": "size_bytes", "sha256": "sha256"}[field]
    row["client"]["graph"]["files"][0][graph_field] = (
        hashlib.sha256(value.encode()).hexdigest() if field == "path" else value
    )
    with pytest.raises(ValueError):
        evidence["summarize_report"](report)


@pytest.mark.parametrize("change", ["missing", "duplicate", "same_pid", "swapped"])
def test_all_samples_must_be_complete_fresh_unique_and_ordered(evidence, report, change):
    runs = report["runs"]
    if change == "missing":
        runs.pop()
    elif change == "duplicate":
        runs[-1] = copy.deepcopy(runs[0])
    elif change == "same_pid":
        runs[-1]["client"]["pid"] = runs[-1]["client"]["runtime"]["pid"] = runs[-1][
            "client_process_pid"
        ] = runs[0]["client"]["pid"]
    else:
        runs[0], runs[1] = runs[1], runs[0]
    with pytest.raises(ValueError):
        evidence["summarize_report"](report)


def rss(client, upper_mib, lower_is_upper=False):
    baseline = client["baseline_rss_bytes"]
    upper = upper_mib * 1_048_576
    h1 = baseline + upper
    h0 = baseline if lower_is_upper else h1
    client.update(
        {
            "peak_rss_native": h1 // 1024,
            "peak_rss_bytes": h1,
            "pretransfer_peak_rss_native": h0 // 1024,
            "pretransfer_peak_rss_bytes": h0,
            "extra_rss_lower_bound_bytes": upper if lower_is_upper else 0,
            "extra_rss_upper_bound_bytes": upper,
        }
    )


def test_growth_uses_all_cross_label_sample_pairs_not_correlated_high_peaks(evidence, report):
    for row in report["runs"][:9]:
        rss(row["client"], 64 if row["label"] == "1024" else 60, row["label"] == "1024")
    report["growth"] = {"span_upper_bound_bytes": 64 * 1_048_576, "passed": False}
    report["passed"] = False
    result = evidence["summarize_report"](report)
    assert result["passed"] is False and result["growth"]["span_upper_bound_bytes"] == 67_108_864


def test_capacity_is_bounded_separately_and_not_constant_file_count_growth(evidence, report):
    for row in report["runs"][9:]:
        rss(row["client"], 64)
    assert evidence["summarize_report"](report)["passed"] is True


@pytest.mark.parametrize("failure", ["rss", "time", "resources", "source_changed"])
def test_honest_failed_budget_is_retained_as_failed_not_forced_green(evidence, report, failure):
    row = report["runs"][0]
    if failure == "rss":
        rss(row["client"], 65)
    elif failure == "time":
        row["client"]["elapsed_seconds"] = 901
    elif failure == "resources":
        row["client"]["metrics"]["open_sources"] = 1
    else:
        report["provenance"]["source_after"]["source_sha256"]["src/yorunge/__init__.py"] = "9" * 64
    if failure != "source_changed":
        row["passed"] = False
    report["growth"] = evidence["growth"](report["runs"])
    report["passed"] = False
    assert evidence["summarize_report"](report)["passed"] is False


def diagnostic():
    return runpy.run_path(str(ROOT / "scripts/upload_diagnostic.py"))


def test_rejected_bytes_are_lossless_bounded_and_never_acceptance(tmp_path):
    helper = diagnostic()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    original = b"\xffnot-json\x00\n"
    (workspace / "stdout.json").write_bytes(original)
    (workspace / "credentials.json").write_bytes(b"must-not-archive")
    (workspace / "source").mkdir()
    (workspace / "source/body.bin").write_bytes(b"never-archive-file-bodies")
    (tmp_path / "dist").mkdir()
    (tmp_path / "docs/research").mkdir(parents=True)
    output = helper["retain"](
        tmp_path, workspace, "failed-upload.json", "a" * 40, "invalid_evidence"
    )
    value = helper["CHECKS"]["decode"](output.read_bytes())
    assert value["files"] == [
        {
            "name": "stdout.json",
            "bytes": len(original),
            "sha256": hashlib.sha256(original).hexdigest(),
            "content_base64": base64.b64encode(original).decode("ascii"),
        }
    ]
    assert helper["summarize"](value) == {
        "kind": "rejected-upload",
        "accepted": False,
        "diagnostic_only": True,
        "files": 1,
        "original_bytes": len(original),
    }
    assert helper["CHECKS"]["verify"](tmp_path) == 1
    assert (workspace / "stdout.json").read_bytes() == original


@pytest.mark.parametrize(
    "change",
    [
        "bad_base64",
        "wrong_hash",
        "wrong_bytes",
        "duplicate",
        "unknown_file",
        "bool_schema",
        "extra",
    ],
)
def test_rejected_diagnostic_cannot_lie_about_original_bytes(change):
    helper = diagnostic()
    original = b"\xff"
    value = {
        "schema_version": 1,
        "report_kind": "rejected_upload_evidence_v1",
        "source_commit": "a" * 40,
        "run_url": None,
        "rejection_reason": "invalid_evidence",
        "files": [
            {
                "name": "stdout.json",
                "bytes": 1,
                "sha256": hashlib.sha256(original).hexdigest(),
                "content_base64": base64.b64encode(original).decode(),
            }
        ],
    }
    file = value["files"][0]
    if change == "bad_base64":
        file["content_base64"] = "!"
    elif change == "wrong_hash":
        file["sha256"] = "0" * 64
    elif change == "wrong_bytes":
        file["bytes"] = True
    elif change == "duplicate":
        value["files"].append(copy.deepcopy(file))
    elif change == "unknown_file":
        file["name"] = "credentials.json"
    elif change == "bool_schema":
        value["schema_version"] = True
    else:
        value["passed"] = True
    with pytest.raises(ValueError):
        helper["summarize"](value)


@pytest.mark.parametrize("failure", ["symlink", "oversize", "empty"])
def test_unarchivable_diagnostics_fail_and_preserve_originals(tmp_path, failure):
    helper = diagnostic()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    selected = workspace / "stdout.json"
    if failure == "symlink":
        elsewhere = tmp_path / "elsewhere"
        elsewhere.write_bytes(b"not-followed")
        selected.symlink_to(elsewhere)
    elif failure == "oversize":
        selected.write_bytes(b"x" * (helper["MAX_FILE"] + 1))
    (tmp_path / "dist").mkdir()
    with pytest.raises(ValueError):
        helper["retain"](tmp_path, workspace, "failed-upload.json", "a" * 40, "invalid_evidence")
    assert not (tmp_path / "dist/failed-upload.json").exists()
    if failure != "empty":
        assert selected.exists()


@pytest.mark.parametrize("original", [b"\xff", b'{"a":1,"a":2}', b"[]", b"{partial"])
def test_driver_rejects_malformed_stdout_without_rewriting_original(tmp_path, original):
    driver = runpy.run_path(str(ROOT / "scripts/benchmark-upload.py"))
    output = tmp_path / "stdout.json"
    output.write_bytes(original)
    with pytest.raises(ValueError):
        driver["decode_output"](output)
    assert output.read_bytes() == original


def test_interrupted_driver_archives_available_originals_and_reraises(tmp_path, monkeypatch):
    driver = runpy.run_path(str(ROOT / "scripts/benchmark-upload.py"))
    globals_ = driver["check"].__globals__
    root = tmp_path.resolve()
    (root / "dist").mkdir()
    (root / "docs/research").mkdir(parents=True)
    vector = root / "tests/fixtures/upload-native-vectors-v1.json"
    vector.parent.mkdir(parents=True)
    vector.write_bytes((ROOT / "tests/fixtures/upload-native-vectors-v1.json").read_bytes())
    python, wheel = root / "python", root / "package.whl"
    python.write_bytes(b"synthetic unused file")
    wheel.write_bytes(b"synthetic unused file")
    provenance = {"commit": "a" * 40, "source_sha256": {"src/yorunge/__init__.py": "1" * 64}}
    monkeypatch.setitem(globals_, "ROOT", root)
    monkeypatch.setitem(globals_["EVIDENCE"], "source", lambda root: copy.deepcopy(provenance))
    monkeypatch.setitem(
        globals_["STREAM"], "locked_runtime", lambda root: {"yorunge": "0.1.0.dev0"}
    )
    monkeypatch.setitem(
        globals_["WHEEL"], "snapshot", lambda *args: {"metadata_sha256": {"METADATA": "2" * 64}}
    )
    monkeypatch.setitem(
        globals_["HTTP"], "certificate", lambda *args, **kwargs: (root / "ca", root / "key")
    )

    def fail(*args):
        raise ValueError("synthetic interrupted worker")

    monkeypatch.setitem(globals_, "run_measurements", fail)
    monkeypatch.setattr(
        globals_["subprocess"], "run", lambda *args, **kwargs: SimpleNamespace(stdout="a" * 40)
    )
    args = SimpleNamespace(
        python=python,
        wheel=wheel,
        output=root / "dist/interrupted.json",
        workspace=root / "workspace",
        cpu="synthetic",
        disk_type="synthetic",
        run_url=None,
    )
    with pytest.raises(ValueError, match="synthetic interrupted worker"):
        driver["check"](args)
    attachment = globals_["CHECKS"]["decode"](
        (root / "dist/interrupted-rejected.json").read_bytes()
    )
    names = {file["name"] for file in attachment["files"]}
    assert names == {
        "source-before.json",
        "source-manifest.json",
        "oracle.json",
        "controller-error.json",
    }
    assert globals_["CHECKS"]["verify"](root) == 1
    assert not (root / "dist/interrupted.json").exists()
