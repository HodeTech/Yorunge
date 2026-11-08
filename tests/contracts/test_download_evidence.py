"""Independent budget decisions for the download measurement, and its controller's lossless rules.

Every rule of one run is a named verdict (``judge_run``): a mutation of a record must fail exactly
the rules it violates, a malformed or self-contradicting record must be refused, and a partial
(smoke) report must never be accepted. The records below are synthetic: not observed performance.
"""

import copy
import json
import os
import runpy
import sys
from functools import cache
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.fixtures.download_native_data import FIXTURES, WARM_OF, expected_sha256

ROOT = Path(__file__).resolve().parents[2]
MIB = 1_048_576
LABELS = ("16", "256", "1024", "resume")
RULES = (
    "rss_upper window_seconds result_bytes result_sha256 result_level result_source result_resume "
    "directory_clean write_accounting write_block checkpoint_fsyncs full_sync warm_result"
).split() + [
    prefix + name
    for prefix in ("server_", "warm_server_")
    for name in "requests ranges credentials headers health connections blocks".split()
]


@pytest.fixture(scope="module")
def evidence():
    return runpy.run_path(str(ROOT / "scripts/download_evidence.py"))


@cache
def oracle(size):
    return expected_sha256(size)


# --- synthetic records: self-consistent, and independent of the verifier's own helpers ------------


def proof():
    names = (
        "tests/fixtures/upload-native-vectors-v1.json "
        "scripts/benchmark-download.py scripts/benchmark-stream.py scripts/dataset_wheel.py "
        "scripts/download_evidence.py tests/fixtures/download_native_client.py "
        "tests/fixtures/download_native_control.py tests/fixtures/download_native_data.py "
        "tests/fixtures/download_native_server.py tests/fixtures/http_server.py "
        "tests/fixtures/model_network.py tests/fixtures/stream_budget.py"
    ).split()
    source = {
        "commit": "a" * 40,
        "source_sha256": {
            "src/yorunge/__init__.py": "1" * 64,
            "src/yorunge/py.typed": "2" * 64,
            **{name: "3" * 64 for name in names},
        },
    }
    return {
        "source_before": source,
        "source_after": copy.deepcopy(source),
        "locked_runtime": {"yorunge": "0.1.0.dev0", "httpx": "0.28.1"},
        "wheel_before": "4" * 64,
        "wheel_after": "4" * 64,
        "wheel_product_sha256": {
            key: value for key, value in source["source_sha256"].items() if key.startswith("src/")
        },
        "wheel_metadata_sha256": {
            name: "5" * 64 for name in ("METADATA", "WHEEL", "entry_points.txt")
        },
    }


def runtime(pid):
    return {
        "prefix": "/synthetic/env",
        "pid": pid,
        "modules": {"yorunge": "/synthetic/env/lib/yorunge/__init__.py"},
        "installed_source_sha256": {"__init__.py": "1" * 64},
        "installed_source_matches": True,
        "metadata": "/synthetic/env/lib",
        "packages": {"yorunge": "0.1.0.dev0", "httpx": "0.28.1"},
        "python": "3.11.18 synthetic fixture",
        "python_executable": "/synthetic/env/bin/python",
        "isolated": True,
        "sqlite": "3.45.0",
        "os": "Linux-synthetic",
        "machine": "x86_64",
        "type_marker_sha256": "2" * 64,
        "metadata_sha256": {name: "5" * 64 for name in ("METADATA", "WHEEL", "entry_points.txt")},
    }


def outcome(label):
    item = FIXTURES[label]
    return {
        "bytes": item.size,
        "sha256": oracle(item.size),
        "verification_level": "sha256_matched",
        "expectation_source": "user_supplied",
        "resumed": item.cut_at is not None,
        "resumed_from_bytes": item.cut_at or 0,
        "first_error": None if item.cut_at is None else "download_incomplete",
    }


def window(label):
    item = FIXTURES[label]
    if item.cut_at is None:
        stage = item.size // (8 * MIB) + 1
    else:
        stage = item.cut_at // (8 * MIB) + (item.size - item.cut_at) // (8 * MIB) + 2
    return {
        "instrumented": True,
        "write_calls": item.size // 16_384 + (item.cut_at is not None),
        "write_bytes": item.size,
        "write_seconds": 1.0,
        "max_write_bytes": 16_384,
        "max_write_seconds": 0.01,
        "stage_fsync_calls": stage,
        "stage_fsync_seconds": 0.05,
        "max_stage_fsync_seconds": 0.01,
        "other_fsync_calls": 9,
        "other_fsync_seconds": 0.01,
        "full_sync_calls": 2,
        "full_sync_seconds": 0.02,
    }


def signed(*rows):
    names = ("range", "if_range", "status", "content_length", "content_range", "bytes_sent")
    return [
        {**dict(zip(names, row[:6], strict=True)), "completed": row[6], "cut": row[7]}
        for row in rows
    ]


def server(label, pid):
    item = FIXTURES[label]
    size, cut = item.size, item.cut_at
    if cut is None:
        rows = signed((None, None, 200, size, None, size, True, False))
    else:
        rows = signed(
            (None, None, 200, size, None, cut, False, True),
            (
                f"bytes={cut}-",
                item.etag,
                206,
                size - cut,
                f"bytes {cut}-{size - 1}/{size}",
                size - cut,
                True,
                False,
            ),
        )
    calls = len(rows)
    return {
        "pid": pid,
        "label": label,
        "size": size,
        "cut_at": cut,
        "etag": item.etag,
        "requests": {"json": calls, "signed": calls, "unexpected": 0},
        "signed": rows,
        "bytes_sent": sum(row["bytes_sent"] for row in rows),
        "connection_count": calls,
        "active_requests": 0,
        "peak_active_requests": 1,
        "credential_violations": 0,
        "header_violations": 0,
        "json_key_failures": 0,
        "errors": 0,
        "max_block_bytes": 65_536,
        "json_header_names": ["accept-encoding", "host", "x-api-key"],
        "signed_header_names": (
            ["accept-encoding", "host"]
            if cut is None
            else ["accept-encoding", "host", "if-range", "range"]
        ),
    }


def client(label, pid):
    item = FIXTURES[label]
    baseline, peak = 41_943_040, 46_137_344
    return {
        "runtime": runtime(pid),
        "pid": pid,
        "baseline_rss_native": baseline // 1024,
        "baseline_rss_method": "linux.proc_self_stat.rss_pages",
        "baseline_rss_bytes": baseline,
        "baseline_rss_pages": 10_240,
        "rss_page_bytes": 4096,
        "pretransfer_peak_rss_native": peak // 1024,
        "pretransfer_peak_rss_bytes": peak,
        "peak_rss_native": peak // 1024,
        "peak_rss_bytes": peak,
        "rss_native_unit": "KiB",
        "extra_rss_lower_bound_bytes": 0,
        "extra_rss_upper_bound_bytes": peak - baseline,
        "elapsed_seconds": 10.0,
        "window": window(label),
        "public": outcome(label),
        "written": {
            "file_bytes": item.size,
            "file_sha256": oracle(item.size),
            "entries": ["weights.onnx"],
            "payload_removed": True,
        },
        "warm": outcome(WARM_OF[label]),
    }


def row(label, sample, ordinal):
    pid = 100 + ordinal
    sink, warm = server(label, 300 + 2 * ordinal), server(WARM_OF[label], 301 + 2 * ordinal)
    return {
        "label": label,
        "sample": sample,
        "client": client(label, pid),
        "server": sink,
        "warm_server": warm,
        "passed": True,
        "client_process_pid": pid,
        "server_process_pid": sink["pid"],
        "warm_server_process_pid": warm["pid"],
    }


def scoped_runs(labels, samples):
    return [
        row(label, sample, ordinal)
        for ordinal, (label, sample) in enumerate(
            (label, sample) for label in labels for sample in range(1, samples + 1)
        )
    ]


def build(evidence, labels=LABELS, samples=3):
    runs = scoped_runs(labels, samples)
    partial = tuple(labels) != LABELS or samples != 3
    growth = evidence["growth"](runs)
    passed = growth["passed"]
    return {
        "schema_version": 1,
        "report_kind": "download_budget_v1",
        "source_commit": "a" * 40,
        "environment": {"cpu": "synthetic", "disk_type": "synthetic"},
        "provenance": proof(),
        "method": evidence["METHOD"],
        "limits": copy.deepcopy(evidence["LIMITS"]),
        "scope": {"labels": list(labels), "samples": samples, "partial": partial},
        "controller_pid": 999,
        "runs": runs,
        "growth": growth,
        "passed": passed,
        "accepted": passed and not partial,
    }


@pytest.fixture
def report(evidence):
    return build(evidence)


def reach(target, path):
    for component in path:
        target = target[component]
    return target


def put(target, path, value):
    reach(target, path[:-1])[path[-1]] = value


def rss(client, upper_mib, lower_is_upper=False):
    baseline = client["baseline_rss_bytes"]
    upper = int(upper_mib * MIB)
    top = baseline + upper
    low = baseline if lower_is_upper else top
    client.update(
        {
            "peak_rss_native": top // 1024,
            "peak_rss_bytes": top,
            "pretransfer_peak_rss_native": low // 1024,
            "pretransfer_peak_rss_bytes": low,
            "extra_rss_lower_bound_bytes": upper if lower_is_upper else 0,
            "extra_rss_upper_bound_bytes": upper,
        }
    )


def verdicts(evidence, report, index):
    return evidence["judge_run"](
        report["runs"][index], report["provenance"], report["controller_pid"]
    )


def failed(evidence, report, index):
    return {name for name, ok in verdicts(evidence, report, index).items() if not ok}


# --- the accepted record --------------------------------------------------------------------------


def test_the_synthetic_report_is_accepted_and_every_run_passes_every_rule(evidence, report):
    assert evidence["summarize_report"](report) == {
        "kind": "download-budget",
        "cases": 12,
        "partial": False,
        "passed": True,
        "accepted": True,
        "growth": {"span_upper_bound_bytes": 4_194_304, "passed": True},
        "max_elapsed_seconds": 10.0,
        "max_extra_rss_upper_bound_bytes": 4_194_304,
    }
    for index in range(12):
        assert list(verdicts(evidence, report, index)) == RULES
        assert all(verdicts(evidence, report, index).values())
        assert evidence["evaluate_run"](
            report["runs"][index], report["provenance"], report["controller_pid"]
        )


def test_a_single_run_is_judged_with_the_three_proof_fields_an_installation_smoke_has(
    evidence, report
):
    """``measure_one`` rows are judged alone, with only these fields of the proof, for label 16."""
    full = report["provenance"]
    context = {
        key: full[key] for key in ("source_before", "locked_runtime", "wheel_metadata_sha256")
    }
    row = report["runs"][0]
    row["passed"] = False
    assert row["label"] == "16"
    assert evidence["evaluate_run"](row, context, report["controller_pid"]) is True


def test_the_labels_and_limits_are_the_standards(evidence):
    assert evidence["LABELS"] == LABELS and evidence["BYTE_LABELS"] == ("16", "256", "1024")
    assert evidence["LIMITS"]["rss_upper_bytes"] == 67_108_864 == 64 * MIB
    assert evidence["LIMITS"]["growth_upper_bytes"] == 8_388_608 == 8 * MIB
    assert evidence["LIMITS"]["window_seconds"] == 900
    assert evidence["LIMITS"]["checkpoint_bytes"] == 8 * MIB
    assert evidence["LIMITS"]["write_block_bytes"] == MIB


@pytest.mark.parametrize("size", [1, 16 * MIB, 257 * 65_536 + 5])
def test_the_verifiers_oracle_is_the_fixtures_oracle(evidence, size):
    assert evidence["object_sha256"](size) == oracle(size)


# --- every rule fails exactly for its own mutation ------------------------------------------------

NORMAL, RESUME = 0, 9  # a "16" run and a "resume" run of the synthetic report
CUT = FIXTURES["resume"].cut_at
SIZE16 = 16 * MIB


def second_signed(row):
    row["server"]["requests"]["signed"] = 2
    row["server"]["signed"].append(signed((None, None, 200, SIZE16, None, 0, False, False))[0])


CASES = [
    # id, run index, edits (path in the run, value), rules that must fail, rules that may also fail
    ("rss", NORMAL, "rss", {"rss_upper"}, set()),
    ("seconds", NORMAL, [(("client", "elapsed_seconds"), 901.0)], {"window_seconds"}, set()),
    ("bytes", NORMAL, [(("client", "public", "bytes"), SIZE16 - 1)], {"result_bytes"}, set()),
    (
        "disk bytes",
        NORMAL,
        [(("client", "written", "file_bytes"), SIZE16 + 1)],
        {"result_bytes"},
        set(),
    ),
    ("sha", NORMAL, [(("client", "public", "sha256"), "0" * 64)], {"result_sha256"}, set()),
    (
        "disk sha",
        NORMAL,
        [(("client", "written", "file_sha256"), "0" * 64)],
        {"result_sha256"},
        set(),
    ),
    (
        "level",
        NORMAL,
        [(("client", "public", "verification_level"), "transfer_complete")],
        {"result_level"},
        set(),
    ),
    (
        "source",
        NORMAL,
        [(("client", "public", "expectation_source"), "none")],
        {"result_source"},
        set(),
    ),
    ("resumed", NORMAL, [(("client", "public", "resumed"), True)], {"result_resume"}, set()),
    ("from", NORMAL, [(("client", "public", "resumed_from_bytes"), 1)], {"result_resume"}, set()),
    (
        "first error",
        NORMAL,
        [(("client", "public", "first_error"), "download_incomplete")],
        {"result_resume"},
        set(),
    ),
    ("not resumed", RESUME, [(("client", "public", "resumed"), False)], {"result_resume"}, set()),
    ("no error", RESUME, [(("client", "public", "first_error"), None)], {"result_resume"}, set()),
    (
        "other error",
        RESUME,
        [(("client", "public", "first_error"), "transport_failed")],
        {"result_resume"},
        set(),
    ),
    (
        "beyond the cut",
        RESUME,
        [(("client", "public", "resumed_from_bytes"), CUT + 1)],
        {"result_resume", "server_ranges"},
        set(),
    ),
    (
        "from zero",
        RESUME,
        [(("client", "public", "resumed_from_bytes"), 0)],
        {"result_resume", "server_ranges"},
        {"checkpoint_fsyncs"},
    ),
    (
        "leftover",
        NORMAL,
        [(("client", "written", "entries"), [".yorunge-download-0123.part", "weights.onnx"])],
        {"directory_clean"},
        set(),
    ),
    (
        "writes",
        NORMAL,
        [
            (("client", "window", "write_bytes"), SIZE16 + 16_384),
            (("client", "window", "write_calls"), SIZE16 // 16_384 + 1),
        ],
        {"write_accounting"},
        set(),
    ),
    ("block", NORMAL, [(("client", "window", "max_write_bytes"), 2 * MIB)], {"write_block"}, set()),
    (
        "too many fsyncs",
        NORMAL,
        [(("client", "window", "stage_fsync_calls"), 1024)],
        {"checkpoint_fsyncs"},
        set(),
    ),
    (
        "no fsyncs",
        NORMAL,
        [
            (("client", "window", "stage_fsync_calls"), 0),
            (("client", "window", "stage_fsync_seconds"), 0.0),
            (("client", "window", "max_stage_fsync_seconds"), 0.0),
        ],
        {"checkpoint_fsyncs"},
        set(),
    ),
    (
        "resume: too few fsyncs",
        RESUME,
        [(("client", "window", "stage_fsync_calls"), 31)],
        {"checkpoint_fsyncs"},
        set(),
    ),
    (
        "resume: too many fsyncs",
        RESUME,
        [(("client", "window", "stage_fsync_calls"), 34)],
        {"checkpoint_fsyncs"},
        set(),
    ),
    (
        "no full-sync",
        NORMAL,
        [
            (("client", "window", "full_sync_calls"), 0),
            (("client", "window", "full_sync_seconds"), 0.0),
        ],
        {"full_sync"},
        set(),
    ),
    (
        "three full-syncs",
        NORMAL,
        [(("client", "window", "full_sync_calls"), 3)],
        {"full_sync"},
        set(),
    ),
    ("warm bytes", NORMAL, [(("client", "warm", "bytes"), 1)], {"warm_result"}, set()),
    ("warm sha", NORMAL, [(("client", "warm", "sha256"), "0" * 64)], {"warm_result"}, set()),
    (
        "warm level",
        NORMAL,
        [(("client", "warm", "verification_level"), "transfer_complete")],
        {"warm_result"},
        set(),
    ),
    ("warm resumed", NORMAL, [(("client", "warm", "resumed"), True)], {"warm_result"}, set()),
    (
        "warm error",
        NORMAL,
        [(("client", "warm", "first_error"), "download_incomplete")],
        {"warm_result"},
        set(),
    ),
    ("warm not cut", RESUME, [(("client", "warm", "first_error"), None)], {"warm_result"}, set()),
    ("two json calls", NORMAL, [(("server", "requests", "json"), 2)], {"server_requests"}, set()),
    (
        "unexpected request",
        NORMAL,
        [(("server", "requests", "unexpected"), 1)],
        {"server_requests"},
        set(),
    ),
    ("second signed GET", NORMAL, second_signed, {"server_requests", "server_ranges"}, set()),
    (
        "one json call on resume",
        RESUME,
        [(("server", "requests", "json"), 1)],
        {"server_requests"},
        set(),
    ),
    (
        "resume without Range",
        RESUME,
        [(("server", "signed", 1, "range"), None)],
        {"server_ranges"},
        set(),
    ),
    (
        "resume without If-Range",
        RESUME,
        [(("server", "signed", 1, "if_range"), None)],
        {"server_ranges"},
        set(),
    ),
    (
        "resume answered 200",
        RESUME,
        [(("server", "signed", 1, "status"), 200)],
        {"server_ranges"},
        set(),
    ),
    (
        "resume wrong Content-Range",
        RESUME,
        [(("server", "signed", 1, "content_range"), "bytes 0-1/2")],
        {"server_ranges"},
        set(),
    ),
    ("resume not cut", RESUME, [(("server", "signed", 0, "cut"), False)], {"server_ranges"}, set()),
    (
        "unfinished body",
        NORMAL,
        [(("server", "signed", 0, "completed"), False)],
        {"server_ranges"},
        set(),
    ),
    (
        "wrong length",
        NORMAL,
        [(("server", "signed", 0, "content_length"), SIZE16 - 1)],
        {"server_ranges"},
        set(),
    ),
    (
        "ranged first GET",
        NORMAL,
        [(("server", "signed", 0, "range"), "bytes=0-")],
        {"server_ranges"},
        set(),
    ),
    ("answered 206", NORMAL, [(("server", "signed", 0, "status"), 206)], {"server_ranges"}, set()),
    (
        "short body",
        NORMAL,
        [
            (("server", "signed", 0, "bytes_sent"), SIZE16 - 1),
            (("server", "bytes_sent"), SIZE16 - 1),
        ],
        {"server_ranges", "write_accounting"},
        set(),
    ),
    (
        "credential",
        NORMAL,
        [(("server", "credential_violations"), 1)],
        {"server_credentials"},
        set(),
    ),
    ("header", NORMAL, [(("server", "header_violations"), 1)], {"server_credentials"}, set()),
    ("json key", NORMAL, [(("server", "json_key_failures"), 1)], {"server_credentials"}, set()),
    (
        "authorization on the json call",
        NORMAL,
        [
            (
                ("server", "json_header_names"),
                ["accept-encoding", "authorization", "host", "x-api-key"],
            )
        ],
        {"server_credentials"},
        set(),
    ),
    (
        "cookie on the json call",
        NORMAL,
        [(("server", "json_header_names"), ["accept-encoding", "cookie", "host", "x-api-key"])],
        {"server_credentials"},
        set(),
    ),
    (
        "proxy credential on the json call",
        NORMAL,
        [
            (
                ("server", "json_header_names"),
                ["accept-encoding", "host", "proxy-authorization", "x-api-key"],
            )
        ],
        {"server_credentials"},
        set(),
    ),
    (
        "no key on the json call",
        NORMAL,
        [(("server", "json_header_names"), ["accept-encoding", "host"])],
        {"server_credentials"},
        set(),
    ),
    (
        "key on the signed GET",
        NORMAL,
        [(("server", "signed_header_names"), ["accept-encoding", "host", "x-api-key"])],
        {"server_headers"},
        set(),
    ),
    (
        "resume names no range headers",
        RESUME,
        [(("server", "signed_header_names"), ["accept-encoding", "host"])],
        {"server_headers"},
        set(),
    ),
    ("server errors", NORMAL, [(("server", "errors"), 1)], {"server_health"}, set()),
    ("server busy", NORMAL, [(("server", "active_requests"), 1)], {"server_health"}, set()),
    ("server overlap", NORMAL, [(("server", "peak_active_requests"), 3)], {"server_health"}, set()),
    ("server idle", NORMAL, [(("server", "peak_active_requests"), 0)], {"server_health"}, set()),
    (
        "two connections",
        NORMAL,
        [(("server", "connection_count"), 2)],
        {"server_connections"},
        set(),
    ),
    (
        "one connection",
        RESUME,
        [(("server", "connection_count"), 1)],
        {"server_connections"},
        set(),
    ),
    ("huge block", NORMAL, [(("server", "max_block_bytes"), 65_537)], {"server_blocks"}, set()),
    ("no block", NORMAL, [(("server", "max_block_bytes"), 0)], {"server_blocks"}, set()),
    (
        "warm server requests",
        NORMAL,
        [(("warm_server", "requests", "json"), 2)],
        {"warm_server_requests"},
        set(),
    ),
    (
        "warm server ranges",
        NORMAL,
        [(("warm_server", "signed", 0, "status"), 206)],
        {"warm_server_ranges"},
        set(),
    ),
    (
        "warm server credential",
        NORMAL,
        [(("warm_server", "credential_violations"), 1)],
        {"warm_server_credentials"},
        set(),
    ),
    (
        "warm server headers",
        NORMAL,
        [(("warm_server", "signed_header_names"), ["accept-encoding", "authorization", "host"])],
        {"warm_server_headers"},
        set(),
    ),
    ("warm server errors", NORMAL, [(("warm_server", "errors"), 1)], {"warm_server_health"}, set()),
    (
        "warm server connections",
        RESUME,
        [(("warm_server", "connection_count"), 1)],
        {"warm_server_connections"},
        set(),
    ),
    (
        "warm server blocks",
        NORMAL,
        [(("warm_server", "max_block_bytes"), 0)],
        {"warm_server_blocks"},
        set(),
    ),
    (
        "warm cut missing",
        RESUME,
        [(("warm_server", "signed", 0, "cut"), False)],
        {"warm_server_ranges"},
        set(),
    ),
]


@pytest.mark.parametrize(
    ("index", "edits", "required", "allowed"),
    [case[1:] for case in CASES],
    ids=[case[0] for case in CASES],
)
def test_a_mutation_fails_exactly_the_rules_it_violates(
    evidence, report, index, edits, required, allowed
):
    row = report["runs"][index]
    if edits == "rss":
        rss(row["client"], 65)
    elif callable(edits):
        edits(row)
    else:
        for path, value in edits:
            put(row, path, value)
    found = failed(evidence, report, index)
    assert required <= found <= required | allowed, found
    assert evidence["evaluate_run"](row, report["provenance"], report["controller_pid"]) is False
    # The run stays in the report: a measured failure is retained, flagged, and never accepted.
    row["passed"] = False
    report["growth"] = evidence["growth"](report["runs"])
    report["passed"] = report["accepted"] = False
    assert evidence["summarize_report"](report)["accepted"] is False


def test_every_rule_has_a_mutation_that_fails_it(evidence):
    killed = set()
    for case in CASES:
        killed |= case[3]
    assert killed == set(RULES)


def test_a_rule_at_its_exact_limit_passes_and_one_unit_beyond_fails(evidence, report):
    client = report["runs"][NORMAL]["client"]
    rss(client, 64)
    client["elapsed_seconds"] = 900.0
    assert failed(evidence, report, NORMAL) == set()
    rss(client, 64, lower_is_upper=True)
    assert failed(evidence, report, NORMAL) == set()
    rss(client, 64 + 1 / 1024)  # one native KiB beyond 64 MiB
    assert failed(evidence, report, NORMAL) == {"rss_upper"}
    rss(client, 4)
    client["elapsed_seconds"] = 900.001
    assert failed(evidence, report, NORMAL) == {"window_seconds"}
    client["elapsed_seconds"] = 10.0
    client["window"]["max_write_bytes"] = MIB
    assert failed(evidence, report, NORMAL) == set()
    client["window"]["max_write_bytes"] = MIB + 1
    assert failed(evidence, report, NORMAL) == {"write_block"}
    client["window"]["max_write_bytes"] = 16_384
    # A checkpoint may overshoot by the largest write: the second of two could land past the end.
    client["window"]["stage_fsync_calls"] = 2
    assert failed(evidence, report, NORMAL) == set()
    client["window"]["stage_fsync_calls"] = 1
    assert failed(evidence, report, NORMAL) == {"checkpoint_fsyncs"}
    client["window"]["stage_fsync_calls"] = 3
    for calls in (1, 2):
        client["window"]["full_sync_calls"] = calls
        assert failed(evidence, report, NORMAL) == set()
    # A cut run also syncs at its clean stop; without that fsync it is still one the rule allows.
    cut = report["runs"][RESUME]["client"]
    for calls, ok in ((31, False), (32, True), (33, True), (34, False)):
        cut["window"]["stage_fsync_calls"] = calls
        assert (failed(evidence, report, RESUME) == set()) is ok, calls
    # A byte that is no whole KiB of the native counter is a refused record, not a failed rule.
    client["peak_rss_bytes"] += 1
    with pytest.raises(ValueError):
        verdicts(evidence, report, NORMAL)


# --- malformed or self-contradicting records are refused -----------------------------------------

MALFORMED = [
    (("schema_version",), True),
    (("schema_version",), 2),
    (("report_kind",), "upload_budget_v1"),
    (("method",), "another method"),
    (("passed",), False),
    (("accepted",), False),
    (("extra",), "unknown"),
    (("controller_pid",), True),
    (("controller_pid",), 100),
    (("source_commit",), "b" * 40),
    (("limits", "growth_upper_bytes"), 9_437_184),
    (("limits", "rss_upper_bytes"), 134_217_728),
    (("limits", "window_seconds"), 1800),
    (("limits", "extra"), 1),
    (("environment", "cpu"), " "),
    (("environment", "extra"), "x"),
    (("scope", "partial"), True),
    (("scope", "samples"), True),
    (("growth", "passed"), False),
    (("growth", "span_upper_bound_bytes"), 1),
    (("provenance", "wheel_after"), "6" * 64),
    (("runs", 0, "sample"), True),
    (("runs", 0, "label"), "2048"),
    (("runs", 0, "passed"), False),
    (("runs", 0, "client_process_pid"), 999),
    (("runs", 0, "server_process_pid"), 100),
    (("runs", 0, "warm_server_process_pid"), 100),
    (("runs", 0, "client", "pid"), 1234),
    (("runs", 0, "client", "elapsed_seconds"), float("inf")),
    (("runs", 0, "client", "elapsed_seconds"), 0),
    (("runs", 0, "client", "peak_rss_bytes"), 1),
    (("runs", 0, "client", "pretransfer_peak_rss_bytes"), 99_000_000),
    (("runs", 0, "client", "baseline_rss_bytes"), True),
    (("runs", 0, "client", "extra_rss_lower_bound_bytes"), 4_194_304),
    (("runs", 0, "client", "rss_page_bytes"), 4097),
    (("runs", 0, "client", "rss_native_unit"), "bytes"),
    (("runs", 0, "client", "runtime", "isolated"), False),
    (("runs", 0, "client", "runtime", "type_marker_sha256"), "0" * 64),
    (("runs", 0, "client", "runtime", "packages", "pytest"), "9.0"),
    (("runs", 0, "client", "runtime", "modules", "yorunge"), "/outside/yorunge.py"),
    (("runs", 0, "client", "window", "instrumented"), False),
    (("runs", 0, "client", "window", "extra"), 1),
    (("runs", 0, "client", "window", "write_calls"), True),
    (("runs", 0, "client", "window", "write_calls"), 0),
    (("runs", 0, "client", "window", "write_seconds"), -1.0),
    (("runs", 0, "client", "window", "write_seconds"), 11.0),
    (("runs", 0, "client", "window", "max_write_bytes"), 10**9),
    (("runs", 0, "client", "window", "max_write_seconds"), 5.0),
    (("runs", 0, "client", "window", "stage_fsync_calls"), 0),
    (("runs", 0, "client", "window", "full_sync_seconds"), float("nan")),
    (("runs", 0, "client", "public", "bytes"), True),
    (("runs", 0, "client", "public", "sha256"), "ABC"),
    (("runs", 0, "client", "public", "resumed"), 1),
    (("runs", 0, "client", "public", "first_error"), ""),
    (("runs", 0, "client", "public", "extra"), 1),
    (("runs", 0, "client", "written", "entries"), "weights.onnx"),
    (("runs", 0, "client", "written", "payload_removed"), 1),
    (("runs", 0, "client", "written", "file_sha256"), "x"),
    (("runs", 0, "client", "warm"), {}),
    (("runs", 0, "server", "label"), "256"),
    (("runs", 0, "server", "size"), 1),
    (("runs", 0, "server", "etag"), '"other"'),
    (("runs", 0, "server", "cut_at"), 5),
    (("runs", 0, "server", "requests", "signed"), 2),
    (("runs", 0, "server", "requests", "extra"), 2),
    (("runs", 0, "server", "bytes_sent"), 1),
    (("runs", 0, "server", "extra"), 1),
    (("runs", 0, "server", "errors"), True),
    (("runs", 0, "server", "signed", 0, "completed"), 1),
    (("runs", 0, "server", "signed", 0, "range"), 5),
    (("runs", 0, "server", "signed", 0, "status"), "200"),
    (("runs", 0, "server", "json_header_names"), "host"),
    (("runs", 0, "server", "signed_header_names"), [1]),
    (("runs", 0, "warm_server", "label"), "warm-resume"),
    (("runs", 9, "server", "cut_at"), None),
]


SERVER_COUNTERS = (
    "pid connection_count active_requests peak_active_requests credential_violations "
    "header_violations json_key_failures errors max_block_bytes bytes_sent"
).split()
MALFORMED += [(("runs", 0, "server", key), True) for key in SERVER_COUNTERS]
MALFORMED += [
    (("runs", 0, "server", "requests", key), True) for key in ("json", "signed", "unexpected")
]
MALFORMED += [
    (("runs", 0, "server", "signed", 0, key), bad)
    for key, bad in (
        ("if_range", 5),
        ("content_range", 5),
        ("content_length", "1"),
        ("bytes_sent", True),
        ("cut", 0),
    )
]
MALFORMED += [
    (("runs", 0, "client", section, key), bad)
    for section in ("public", "warm")
    for key, bad in (
        ("resumed_from_bytes", True),
        ("verification_level", 5),
        ("expectation_source", ""),
        ("first_error", 5),
        ("sha256", 5),
        ("bytes", "1"),
    )
]
MALFORMED += [
    (("runs", 0, "client", "written", "file_bytes"), True),
    (("runs", 0, "client", "written", "entries"), [5]),
]
MALFORMED += [
    # more calls than bytes, bytes beyond what the calls can hold, and time without calls
    (("runs", 0, "client", "window", "write_calls"), 16 * MIB + 5),
    (("runs", 0, "client", "window", "write_calls"), 1),
    (("runs", 0, "client", "window", "max_stage_fsync_seconds"), 0.5),
    (("runs", 0, "client", "window", "other_fsync_calls"), 0),
    (("runs", 0, "client", "window", "full_sync_calls"), 0),
    # every kind of call counts in the window it lies in
    (("runs", 0, "client", "window", "stage_fsync_seconds"), 9.5),
    (("runs", 0, "client", "window", "other_fsync_seconds"), 9.5),
    (("runs", 0, "client", "window", "full_sync_seconds"), 9.5),
    (("runs", 0, "client", "runtime", "metadata_sha256", "METADATA"), "0" * 64),
    (("runs", 0, "client", "runtime", "packages", "httpx"), "0.29.0"),
    (("runs", 0, "client", "runtime", "installed_source_matches"), False),
    (("runs", 0, "client", "elapsed_seconds"), -1.0),
    (("runs", 0, "sample"), 0),
    (("runs", 0, "sample"), 4),
    (("provenance", "wheel_before"), "x"),
]


@pytest.mark.parametrize(("path", "value"), MALFORMED)
def test_false_or_malformed_measurement_is_rejected(evidence, report, path, value):
    put(report, path, value)
    with pytest.raises(ValueError):
        evidence["summarize_report"](report)
    if path[0] == "runs" and path[2:] != ("passed",):
        # The record itself is refused. A report would also refuse it for claiming a rule held
        # that failed, which would hide a validator that no longer looks at the field.
        with pytest.raises(ValueError):
            verdicts(evidence, report, path[1])


@pytest.mark.parametrize(
    ("edits", "message"),
    [
        ([(("sample",), 4)], "unknown download sample identity"),
        ([(("sample",), 99)], "unknown download sample identity"),
        ([(("client", "elapsed_seconds"), 0)], "must be positive"),
        ([(("client", "elapsed_seconds"), -1.0)], "must be positive"),
        (
            [(("client", "pid"), 1234), (("client_process_pid",), 1234)],
            "client PID mismatch",
        ),
        ([(("client_process_pid",), 999)], "child PID differs"),
        ([(("warm_server_process_pid",), 777)], "child PID differs"),
        (
            [
                (("warm_server", "pid"), 100),
                (("warm_server_process_pid",), 100),
            ],
            "separate processes",
        ),
        ([(("client", "window", "stage_fsync_calls"), 0)], "time without calls"),
        ([(("client", "window", "other_fsync_calls"), 0)], "time without calls"),
        ([(("client", "window", "full_sync_calls"), 0)], "time without calls"),
        ([(("client", "window", "write_calls"), 0)], "write counters are inconsistent"),
        ([(("client", "window", "write_calls"), 1)], "write counters are inconsistent"),
        ([(("client", "window", "write_calls"), 16 * MIB + 5)], "write counters are inconsistent"),
        ([(("client", "window", "max_write_bytes"), 10**9)], "write counters are inconsistent"),
        ([(("client", "window", "max_write_seconds"), 5.0)], "write counters are inconsistent"),
        ([(("client", "window", "max_stage_fsync_seconds"), 0.5)], "stage fsync counters"),
        ([(("client", "window", "write_seconds"), 11.0)], "contradict measured window"),
        ([(("client", "window", "stage_fsync_seconds"), 9.5)], "contradict measured window"),
        ([(("client", "window", "other_fsync_seconds"), 9.5)], "contradict measured window"),
        ([(("client", "window", "full_sync_seconds"), 9.5)], "contradict measured window"),
        ([(("client", "window", "write_seconds"), -1.0)], "cannot be negative"),
        ([(("client", "window", "instrumented"), False)], "does not match evidence"),
        ([(("client", "runtime", "isolated"), False)], "does not match evidence"),
        (
            [(("client", "runtime", "installed_source_matches"), False)],
            "does not match evidence",
        ),
        (
            [
                # An honest "the installed bytes differ from the measured source" is no valid run.
                (("client", "runtime", "installed_source_sha256", "__init__.py"), "9" * 64),
                (("client", "runtime", "installed_source_matches"), False),
            ],
            "does not match evidence",
        ),
        ([(("client", "runtime", "type_marker_sha256"), "0" * 64)], "marker mismatch"),
        (
            [(("client", "runtime", "metadata_sha256", "METADATA"), "0" * 64)],
            "metadata mismatch",
        ),
        ([(("client", "runtime", "packages", "httpx"), "0.29.0")], "frozen runtime mismatch"),
        ([(("server", "requests", "signed"), 2)], "differ from its counters"),
        ([(("server", "bytes_sent"), 1)], "byte counters differ"),
        ([(("server", "label"), "256")], "another fixture"),
        ([(("warm_server", "cut_at"), 5)], "another fixture"),
    ],
)
def test_each_guard_of_a_run_is_what_refuses_it(evidence, report, edits, message):
    row = report["runs"][NORMAL]
    for path, value in edits:
        put(row, path, value)
    with pytest.raises(ValueError, match=message):
        evidence["judge_run"](row, report["provenance"], report["controller_pid"])


CLOSED = [
    (),
    ("scope",),
    ("environment",),
    ("limits",),
    ("provenance",),
    ("provenance", "wheel_metadata_sha256"),
    ("growth",),
    ("runs", 0),
    ("runs", 0, "client"),
    ("runs", 0, "client", "window"),
    ("runs", 0, "client", "public"),
    ("runs", 0, "client", "written"),
    ("runs", 0, "client", "warm"),
    ("runs", 0, "client", "runtime"),
    ("runs", 0, "server"),
    ("runs", 0, "server", "requests"),
    ("runs", 0, "server", "signed", 0),
    ("runs", 0, "warm_server"),
]


@pytest.mark.parametrize(
    "path", CLOSED, ids=[".".join(map(str, path)) or "report" for path in CLOSED]
)
def test_every_closed_record_rejects_a_missing_and_an_extra_field(evidence, report, path):
    target = reach(report, path)
    missing = copy.deepcopy(report)
    victim = sorted(reach(missing, path))[0]
    del reach(missing, path)[victim]
    with pytest.raises(ValueError):
        evidence["summarize_report"](missing)
    target["unexpected_field"] = 1
    with pytest.raises(ValueError):
        evidence["summarize_report"](report)


@pytest.mark.parametrize("field", ["runtime", "window", "public", "written", "warm"])
def test_a_missing_client_section_is_a_refused_record_not_a_failed_rule(evidence, report, field):
    del report["runs"][0]["client"][field]
    with pytest.raises(ValueError):
        evidence["summarize_report"](report)


def test_a_server_that_served_another_fixture_is_refused(evidence, report):
    report["runs"][0]["server"] = server("256", 300)
    with pytest.raises(ValueError, match="another fixture"):
        evidence["summarize_report"](report)


def test_the_measuring_processes_must_be_four_separate_processes(evidence, report):
    report["controller_pid"] = report["runs"][0]["server"]["pid"]
    with pytest.raises(ValueError, match="separate processes"):
        evidence["summarize_report"](report)


# --- growth ---------------------------------------------------------------------------------------


def test_growth_uses_all_cross_label_sample_pairs_not_correlated_high_peaks(evidence, report):
    for row in report["runs"][:9]:
        rss(row["client"], 64 if row["label"] == "1024" else 60, row["label"] == "1024")
    result = evidence["growth"](report["runs"])
    assert result == {"span_upper_bound_bytes": 64 * MIB, "passed": False}
    report["growth"], report["passed"], report["accepted"] = result, False, False
    summary = evidence["summarize_report"](report)
    assert summary["passed"] is False and summary["accepted"] is False
    assert summary["growth"]["span_upper_bound_bytes"] == 67_108_864
    # The same series is refused as accepted: the verdicts of the report are recomputed.
    report["accepted"] = True
    with pytest.raises(ValueError):
        evidence["summarize_report"](report)


def spans(upper_lower):
    return [
        {
            "label": label,
            "client": {"extra_rss_upper_bound_bytes": upper, "extra_rss_lower_bound_bytes": lower},
        }
        for label, upper, lower in upper_lower
    ]


@pytest.mark.parametrize(
    ("limit_delta", "passed"), [(-1, True), (0, True), (1, False), (4 * MIB, False)]
)
def test_the_cross_size_span_limit_is_exactly_eight_mib(evidence, limit_delta, passed):
    runs = spans([("16", 8 * MIB + limit_delta, 0), ("256", 0, 0)])
    result = evidence["growth"](runs)
    assert result == {"span_upper_bound_bytes": 8 * MIB + limit_delta, "passed": passed}


def test_the_span_is_never_below_zero(evidence):
    # A lower bound above an upper bound is no valid run record; the formula's own clamp is pure.
    runs = spans([("16", 0, 100), ("256", 0, 100)])
    assert evidence["growth"](runs) == {"span_upper_bound_bytes": 0, "passed": True}


def test_samples_of_one_label_are_not_compared_with_each_other(evidence, report):
    rows = report["runs"]
    for row in rows[:9]:
        mib = (
            30 if (row["label"], row["sample"]) == ("16", 1) else 21 if row["label"] == "16" else 22
        )
        rss(row["client"], mib, True)
    # 16/1 against 16/2 would be 9 MiB; against the other sizes the span is exactly 8 MiB.
    assert evidence["growth"](rows) == {"span_upper_bound_bytes": 8 * MIB, "passed": True}
    report["growth"] = evidence["growth"](rows)
    assert evidence["summarize_report"](report)["accepted"] is True


def test_resume_runs_have_their_own_bound_and_are_not_part_of_the_span(evidence, report):
    for row in report["runs"][9:]:
        rss(row["client"], 64)
    assert evidence["growth"](report["runs"]) == {"span_upper_bound_bytes": 4 * MIB, "passed": True}
    assert evidence["summarize_report"](report)["accepted"] is True
    rss(report["runs"][9]["client"], 65)
    report["runs"][9]["passed"] = False
    report["passed"] = report["accepted"] = False
    assert evidence["growth"](report["runs"]) == {"span_upper_bound_bytes": 4 * MIB, "passed": True}
    assert evidence["summarize_report"](report)["passed"] is False


def test_fewer_than_two_byte_sizes_give_no_span_and_no_acceptance(evidence):
    assert evidence["growth"]([]) == {"span_upper_bound_bytes": None, "passed": False}
    assert evidence["growth"](spans([("16", 1, 0), ("16", 2, 0)])) == {
        "span_upper_bound_bytes": None,
        "passed": False,
    }
    only_resume = spans([("resume", 64 * MIB, 64 * MIB), ("16", 0, 0)])
    assert evidence["growth"](only_resume) == {"span_upper_bound_bytes": None, "passed": False}


# --- scope, partial reports, samples --------------------------------------------------------------


def test_a_complete_report_with_a_failed_run_is_valid_and_not_accepted(evidence, report):
    report["runs"][4]["client"]["public"]["verification_level"] = "transfer_complete"
    report["runs"][4]["passed"] = False
    report["passed"] = report["accepted"] = False
    summary = evidence["summarize_report"](report)
    assert (summary["passed"], summary["accepted"], summary["partial"]) == (False, False, False)
    assert summary["cases"] == 12


@pytest.mark.parametrize(
    ("labels", "samples", "passed"),
    [
        (("16", "resume"), 1, False),  # one byte size: no cross-size evidence
        (("16", "256"), 1, True),
        (("16", "256", "1024"), 3, True),
        (LABELS, 2, True),
        (("resume",), 3, False),
    ],
)
def test_a_partial_smoke_is_valid_and_can_never_be_accepted(evidence, labels, samples, passed):
    smoke = build(evidence, labels, samples)
    assert smoke["scope"]["partial"] is True and smoke["accepted"] is False
    summary = evidence["summarize_report"](smoke)
    assert summary["cases"] == len(labels) * samples
    assert (summary["partial"], summary["passed"], summary["accepted"]) == (True, passed, False)
    smoke["accepted"] = True
    with pytest.raises(ValueError):
        evidence["summarize_report"](smoke)


def test_the_full_label_set_with_three_samples_is_not_partial(evidence):
    assert evidence["is_partial"](list(LABELS), 3) is False
    assert evidence["is_partial"](list(LABELS), 2) is True
    assert evidence["is_partial"](["16", "256", "1024"], 3) is True


@pytest.mark.parametrize(
    "scope",
    [
        {"labels": [], "samples": 1, "partial": True},
        {"labels": ["resume", "16"], "samples": 1, "partial": True},
        {"labels": ["16", "16"], "samples": 1, "partial": True},
        {"labels": ["16", "2048"], "samples": 1, "partial": True},
        {"labels": "16", "samples": 1, "partial": True},
        {"labels": ["16"], "samples": 0, "partial": True},
        {"labels": ["16"], "samples": 4, "partial": True},
        {"labels": ["16"], "samples": True, "partial": True},
        {"labels": ["16"], "samples": 1, "partial": False},
        {"labels": list(LABELS), "samples": 3, "partial": True},
        {"labels": list(LABELS), "samples": 3, "partial": 0},
    ],
)
def test_an_impossible_scope_is_refused(evidence, scope):
    smoke = build(evidence, ("16",), 1)
    smoke["scope"] = scope
    with pytest.raises(ValueError):
        evidence["summarize_report"](smoke)


@pytest.mark.parametrize(
    ("labels", "samples", "message"),
    [
        (("resume", "16"), 1, "canonical order"),
        (("16", "16"), 1, "canonical order"),
        ((), 1, "canonical order"),
        (("16",), 4, "cannot exceed three"),
    ],
)
def test_an_odd_scope_is_refused_even_when_its_runs_agree_with_it(
    evidence, labels, samples, message
):
    smoke = build(evidence, labels, samples)
    if not labels:
        smoke["growth"], smoke["passed"], smoke["accepted"] = evidence["growth"]([]), False, False
    with pytest.raises(ValueError, match=message):
        evidence["summarize_report"](smoke)


def test_a_report_whose_scope_says_partial_but_holds_every_run_is_refused(evidence, report):
    report["scope"]["partial"] = True
    with pytest.raises(ValueError):
        evidence["summarize_report"](report)


@pytest.mark.parametrize("change", ["missing", "duplicate", "same_pid", "swapped", "extra"])
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
    elif change == "swapped":
        runs[0], runs[1] = runs[1], runs[0]
    else:
        runs.append(copy.deepcopy(runs[0]))
    counted = change in ("missing", "extra")
    with pytest.raises(ValueError, match="every chosen label and sample" if counted else None):
        evidence["summarize_report"](report)


@pytest.mark.parametrize("failure", ["source_changed", "wheel_changed", "runtime_changed"])
def test_a_changed_source_wheel_or_runtime_is_a_failed_not_forced_green_report(
    evidence, report, failure
):
    if failure == "source_changed":
        report["provenance"]["source_after"]["source_sha256"]["src/yorunge/__init__.py"] = "9" * 64
    elif failure == "wheel_changed":
        report["provenance"]["wheel_after"] = "9" * 64
    else:
        report["runs"][3]["client"]["runtime"]["python"] = "3.11.19 another build"
    report["passed"] = report["accepted"] = False
    summary = evidence["summarize_report"](report)
    assert summary["passed"] is False and summary["accepted"] is False
    report["passed"] = True
    with pytest.raises(ValueError):
        evidence["summarize_report"](report)


def test_report_passed_requires_each_of_its_conditions(evidence, report):
    runs, good = report["runs"], evidence["growth"](report["runs"])
    base = report["provenance"]
    assert evidence["report_passed"](base, runs, good) is True
    assert (
        evidence["report_passed"](base, runs, {"span_upper_bound_bytes": 9 * MIB, "passed": False})
        is False
    )
    changed = copy.deepcopy(base)
    changed["source_after"]["commit"] = "b" * 40
    assert evidence["report_passed"](changed, runs, good) is False
    changed = copy.deepcopy(base)
    changed["wheel_after"] = "9" * 64
    assert evidence["report_passed"](changed, runs, good) is False
    failing = copy.deepcopy(runs)
    failing[5]["passed"] = False
    assert evidence["report_passed"](base, failing, good) is False
    other = copy.deepcopy(runs)
    other[2]["client"]["runtime"]["sqlite"] = "3.46.0"
    assert evidence["report_passed"](base, other, good) is False
    other = copy.deepcopy(runs)
    other[2]["client"]["runtime"]["pid"] = 12345  # a pid is no part of the runtime identity
    other[2]["client"]["runtime"]["modules"] = {"yorunge": "/synthetic/env/x.py"}
    assert evidence["report_passed"](base, other, good) is True


# --- provenance and the source map ----------------------------------------------------------------


def test_the_real_source_map_includes_every_measurement_file(evidence):
    value = evidence["source"](ROOT)
    assert value["commit"] and set(evidence["REQUIRED_SOURCES"]) <= set(value["source_sha256"])
    assert "tests/fixtures/download_native_server.py" in value["source_sha256"]
    assert "scripts/upload_evidence.py" in value["source_sha256"]  # everything of the upload map
    upload = runpy.run_path(str(ROOT / "scripts/upload_evidence.py"))["source"](ROOT)
    assert upload["commit"] == value["commit"]
    assert upload["source_sha256"].items() <= value["source_sha256"].items()
    assert "tests/contracts/test_download_evidence.py" in value["source_sha256"]
    assert "src/yorunge/py.typed" in value["source_sha256"]


@pytest.mark.parametrize(
    "missing", ["scripts/benchmark-download.py", "tests/fixtures/model_network.py"]
)
def test_a_source_map_without_a_measurement_file_is_refused(evidence, monkeypatch, missing):
    complete = copy.deepcopy(proof()["source_before"])
    del complete["source_sha256"][missing]
    loader = evidence["source"].__globals__["runpy"]
    original = loader.run_path
    monkeypatch.setattr(
        loader,
        "run_path",
        lambda path, *a, **k: (
            {"source": lambda root: copy.deepcopy(complete)}
            if str(path).endswith("startup_evidence.py")
            else original(path, *a, **k)
        ),
    )
    with pytest.raises(ValueError, match="lacks"):
        evidence["source"](ROOT)
    with pytest.raises(ValueError, match="measurement files missing"):
        evidence["provenance"]({**proof(), "source_before": complete}, "a" * 40)


def test_provenance_binds_the_commit_the_wheel_and_the_marker(evidence):
    good = proof()
    assert evidence["provenance"](good, "a" * 40) == good
    with pytest.raises(ValueError):
        evidence["provenance"](good, "b" * 40)
    mismatch = proof()
    mismatch["wheel_product_sha256"]["src/yorunge/__init__.py"] = "7" * 64
    with pytest.raises(ValueError, match="wheel/source"):
        evidence["provenance"](mismatch, "a" * 40)
    untyped = proof()
    del untyped["source_before"]["source_sha256"]["src/yorunge/py.typed"]
    del untyped["wheel_product_sha256"]["src/yorunge/py.typed"]
    with pytest.raises(ValueError, match="marker"):
        evidence["provenance"](untyped, "a" * 40)
    tools = proof()
    tools["locked_runtime"]["pytest"] = "9.0"
    with pytest.raises(ValueError):
        evidence["provenance"](tools, "a" * 40)


# --- the controller -------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def driver():
    return runpy.run_path(str(ROOT / "scripts/benchmark-download.py"))


@pytest.mark.parametrize(
    "original",
    [
        b"\xff",
        b'{"a":1,"a":2}',
        b"[]",
        b"{partial",
        b'{ "a": 1 }\n',  # valid JSON, but not the canonical bytes
        b'{"a":1}',  # canonical, but no LF
        b'{"a":1}\n\n',
        b'{"a":1e0}\n',  # the same number, spelled other than the canonical encoder does
        b'{"a":NaN}\n',
    ],
)
def test_driver_rejects_noncanonical_or_malformed_stdout_without_rewriting_it(
    tmp_path, driver, original
):
    output = tmp_path / "stdout.json"
    output.write_bytes(original)
    with pytest.raises(ValueError):
        driver["decode_output"](output)
    assert output.read_bytes() == original


def test_driver_accepts_exactly_one_canonical_object_and_lf(tmp_path, driver):
    output = tmp_path / "stdout.json"
    output.write_bytes(b'{"a":[1,2.5,null,"\xc3\xa9"],"b":{"c":true}}\n')
    assert driver["decode_output"](output) == {"a": [1, 2.5, None, "é"], "b": {"c": True}}


def test_labels_and_samples_are_validated_before_any_file_is_made(tmp_path, driver):
    def args(labels, samples):
        return SimpleNamespace(labels=labels, samples=samples)

    assert driver["chosen"](args(list(LABELS), 3)) == (list(LABELS), 3)
    assert driver["chosen"](args(["16", "resume"], 1)) == (["16", "resume"], 1)
    for labels, samples in (
        ([], 3),
        (["resume", "16"], 3),
        (["16", "16"], 3),
        (["2048"], 3),
        (["16"], 0),
        (["16"], 4),
        (["16"], True),
    ):
        with pytest.raises(ValueError):
            driver["chosen"](args(labels, samples))


def command(driver, monkeypatch, capsys, tmp_path, *extra, output="report.json"):
    """Run ``main`` with this argument vector; its exit status and what it printed."""
    argv = [
        "benchmark-download.py",
        "--python",
        str(tmp_path / "python"),
        "--wheel",
        str(tmp_path / "package.whl"),
        "--workspace",
        str(tmp_path / "workspace"),
        "--output",
        str(tmp_path / output),
        "--cpu",
        "synthetic",
        "--disk-type",
        "synthetic",
        *extra,
    ]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as stop:
        driver["main"]()
    printed = capsys.readouterr()
    return stop.value.code, printed.out, printed.err


@pytest.mark.parametrize("extra", [("--labels", "resume", "16"), ("--labels", "16", "16")])
def test_the_command_refuses_bad_labels_before_it_creates_anything(
    tmp_path, driver, monkeypatch, capsys, extra
):
    code, out, err = command(driver, monkeypatch, capsys, tmp_path, *extra)
    assert code == 1 and "canonical order" in err and not out
    assert not (tmp_path / "workspace").exists() and not (tmp_path / "report.json").exists()


@pytest.mark.parametrize("extra", [("--samples", "4"), ("--samples", "0"), ("--labels", "2048")])
def test_the_command_refuses_unknown_samples_and_labels(
    tmp_path, driver, monkeypatch, capsys, extra
):
    code, out, err = command(driver, monkeypatch, capsys, tmp_path, *extra)
    assert code == 2 and "invalid choice" in err and not out


def test_the_command_never_overwrites_a_report_or_a_workspace(
    tmp_path, driver, monkeypatch, capsys
):
    (tmp_path / "report.json").write_bytes(b"previous evidence")
    code, _, err = command(driver, monkeypatch, capsys, tmp_path)
    assert code == 1 and "new path" in err
    assert (tmp_path / "report.json").read_bytes() == b"previous evidence"
    (tmp_path / "report.json").unlink()
    (tmp_path / "workspace").mkdir()
    (tmp_path / "workspace/kept.txt").write_bytes(b"previous workspace")
    code, _, err = command(driver, monkeypatch, capsys, tmp_path)
    assert code == 1 and "new path" in err
    assert (tmp_path / "workspace/kept.txt").read_bytes() == b"previous workspace"


def test_the_report_needs_a_canonical_lowercase_name(tmp_path, driver, monkeypatch, capsys):
    code, _, err = command(driver, monkeypatch, capsys, tmp_path, output="Report.JSON")
    assert code == 1 and "canonical lowercase name" in err


def test_the_command_needs_an_installed_python_and_a_wheel(tmp_path, driver, monkeypatch, capsys):
    code, _, err = command(driver, monkeypatch, capsys, tmp_path)
    assert code == 1 and "installed runtime Python and wheel" in err
    assert not (tmp_path / "workspace").exists()


def test_samples_run_serially_label_by_label_in_canonical_order(tmp_path, driver, monkeypatch):
    seen = []
    globals_ = driver["run_measurements"].__globals__
    monkeypatch.setitem(
        globals_, "measure_one", lambda *args: seen.append(args[-2:]) or {"label": args[-2]}
    )
    rows = driver["run_measurements"](
        Path("python"),
        tmp_path,
        tmp_path / "receipt",
        (tmp_path / "a", tmp_path / "b"),
        ["16", "resume"],
        2,
    )
    assert seen == [("16", 1), ("16", 2), ("resume", 1), ("resume", 2)] and len(rows) == 4


def test_a_failed_worker_leaves_every_original_and_stops_both_servers(tmp_path, driver):
    """The development interpreter is no installed runtime: the worker refuses it before any I/O."""
    from tests.fixtures.http_server import certificate

    certificates = certificate(tmp_path / "cert", names=("api.ssyz.org.tr",))
    receipt = tmp_path / "source-manifest.json"
    receipt.write_text(
        json.dumps({"source_sha256": {}, "locked_runtime": {}, "metadata_sha256": {}})
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    with pytest.raises(ValueError, match="worker failed; original stdout/stderr preserved"):
        driver["measure_one"](Path(sys.executable), workspace, receipt, certificates, "16", 1)
    work = workspace / "16-1"
    assert (work / "client-stdout.json").read_bytes() == b""
    assert (
        b"product import escaped the selected installed environment"
        in (work / "client-stderr.txt").read_bytes()
    )
    for name, label in (("warm-server", "warm"), ("measured-server", "16")):
        found = json.loads((work / name / "stdout.json").read_bytes())
        assert found["label"] == label and found["requests"] == {
            "json": 0,
            "signed": 0,
            "unexpected": 0,
        }
        assert (work / name / "stderr.txt").read_bytes() == b""
    assert sorted(entry.name for entry in work.iterdir()) == [
        "client-stderr.txt",
        "client-stdout.json",
        "measured",
        "measured-server",
        "warm",
        "warm-server",
    ]
    with pytest.raises(FileExistsError):  # a sample directory is never reused
        driver["measure_one"](Path(sys.executable), workspace, receipt, certificates, "16", 1)


def controller_args(tmp_path, labels, samples):
    python, wheel = tmp_path / "python", tmp_path / "package.whl"
    python.write_bytes(b"synthetic unused file")
    wheel.write_bytes(b"synthetic unused file")
    return SimpleNamespace(
        python=python,
        wheel=wheel,
        output=tmp_path / "report.json",
        workspace=tmp_path / "workspace",
        cpu="synthetic",
        disk_type="synthetic",
        labels=labels,
        samples=samples,
    )


def patch_controller(driver, monkeypatch, tmp_path, runs):
    globals_ = driver["check"].__globals__
    base = proof()
    monkeypatch.setitem(
        globals_["EVIDENCE"], "source", lambda root: copy.deepcopy(base["source_before"])
    )
    monkeypatch.setitem(globals_["STREAM"], "locked_runtime", lambda root: base["locked_runtime"])
    monkeypatch.setitem(
        globals_["WHEEL"],
        "snapshot",
        lambda *args: {
            "sha256": base["wheel_before"],
            "product_sha256": base["wheel_product_sha256"],
            "metadata_sha256": base["wheel_metadata_sha256"],
        },
    )
    monkeypatch.setitem(
        globals_["HTTP"], "certificate", lambda *args, **kwargs: (tmp_path / "ca", tmp_path / "key")
    )
    monkeypatch.setitem(globals_, "run_measurements", lambda *args: runs)
    return globals_


def test_an_interrupted_controller_keeps_its_workspace_and_writes_no_report(
    tmp_path, driver, monkeypatch
):
    def fail(*args):
        raise ValueError("synthetic interrupted worker")

    globals_ = patch_controller(driver, monkeypatch, tmp_path, [])
    monkeypatch.setitem(globals_, "run_measurements", fail)
    args = controller_args(tmp_path, list(LABELS), 3)
    with pytest.raises(ValueError, match="synthetic interrupted worker"):
        driver["check"](args)
    assert not args.output.exists()
    names = sorted(entry.name for entry in args.workspace.iterdir())
    assert names == ["controller-error.json", "source-before.json", "source-manifest.json"]
    assert json.loads((args.workspace / "controller-error.json").read_bytes()) == {
        "outcome": "incomplete_download_measurement"
    }
    with pytest.raises(ValueError, match="new path"):  # nothing is reused or overwritten
        driver["check"](args)


@pytest.mark.parametrize(
    ("labels", "samples", "exit_code", "partial"),
    [(["16", "resume"], 1, 1, True), (["16", "256"], 2, 1, True), (list(LABELS), 3, 0, False)],
)
def test_the_report_is_written_once_marked_partial_and_exits_zero_only_when_accepted(
    tmp_path, driver, monkeypatch, capsys, labels, samples, exit_code, partial
):
    runs = scoped_runs(labels, samples)
    for item in runs:
        item["passed"] = None  # the controller decides every verdict itself
    patch_controller(driver, monkeypatch, tmp_path, runs)
    monkeypatch.setattr(os, "getpid", lambda: 999)
    args = controller_args(tmp_path, labels, samples)
    assert driver["check"](args) == exit_code
    printed = json.loads(capsys.readouterr().out)
    written = driver["CHECKS"]["decode"](args.output.read_bytes())
    evidence = driver["EVIDENCE"]
    assert evidence["summarize_report"](written) == printed
    assert (printed["partial"], printed["cases"]) == (partial, len(labels) * samples)
    assert printed["accepted"] is (not partial and printed["passed"])
    assert written["scope"] == {"labels": labels, "samples": samples, "partial": partial}
    assert all(item["passed"] is True for item in written["runs"])
    assert sorted(entry.name for entry in args.workspace.iterdir()) == [
        "source-after.json",
        "source-before.json",
        "source-manifest.json",
    ]
    with pytest.raises(ValueError, match="new path"):
        driver["check"](args)
    assert driver["CHECKS"]["decode"](args.output.read_bytes()) == written


def test_a_failed_sample_stays_in_the_report_as_failed(tmp_path, driver, monkeypatch, capsys):
    runs = scoped_runs(list(LABELS), 3)
    runs[2]["client"]["public"]["sha256"] = "0" * 64  # the product wrote other bytes
    patch_controller(driver, monkeypatch, tmp_path, runs)
    monkeypatch.setattr(os, "getpid", lambda: 999)
    args = controller_args(tmp_path, list(LABELS), 3)
    assert driver["check"](args) == 1
    written = driver["CHECKS"]["decode"](args.output.read_bytes())
    assert [item["passed"] for item in written["runs"]].count(False) == 1
    assert written["runs"][2]["passed"] is False and written["passed"] is False
    assert written["accepted"] is False and written["scope"]["partial"] is False
    assert json.loads(capsys.readouterr().out)["passed"] is False
