"""Boundaries of scripts/download_evidence.py that no test pinned.

Each test passes on the tree and fails on the mutant named in its comment.
"""

import math
import runpy
from pathlib import Path

import pytest

from tests.contracts.test_download_evidence import (
    NORMAL,
    RESUME,
    SIZE16,
    build,
    failed,
    put,
    verdicts,
)
from tests.contracts.test_download_evidence import evidence as evidence
from tests.contracts.test_download_evidence import report as report

pytestmark = pytest.mark.usefixtures("evidence_publication_context")

ROOT = Path(__file__).resolve().parents[2]


# --- reported flags must be booleans (CHECKS["flag"](reported, expected) argument order)


def test_the_reported_overall_flags_must_be_booleans_not_1_and_0(evidence, report):
    # mutants L603/L605: CHECKS["flag"](expected, reported) lets 1 stand for True
    report["passed"] = 1
    with pytest.raises(ValueError):
        evidence["summarize_report"](report)
    report["passed"] = True
    report["accepted"] = 1
    with pytest.raises(ValueError):
        evidence["summarize_report"](report)


def test_a_partial_report_flag_must_be_a_boolean(evidence):
    smoke = build(evidence, labels=("16",), samples=1)
    smoke["scope"]["partial"] = 1  # mutant L570
    with pytest.raises(ValueError):
        evidence["summarize_report"](smoke)
    smoke["scope"]["partial"] = True
    smoke["accepted"] = 0  # the honest value is False; 0 is not a boolean
    with pytest.raises(ValueError):
        evidence["summarize_report"](smoke)


def test_a_run_verdict_flag_must_be_a_boolean(evidence, report):
    report["runs"][4]["passed"] = 1  # mutant L518
    with pytest.raises(ValueError):
        evidence["summarize_report"](report)


def test_the_instrumented_marker_must_be_true_and_a_boolean(evidence, report):
    put(report["runs"][NORMAL], ("client", "window", "instrumented"), 1)  # mutant L235
    with pytest.raises(ValueError):
        verdicts(evidence, report, NORMAL)
    put(report["runs"][NORMAL], ("client", "window", "instrumented"), False)
    with pytest.raises(ValueError):
        verdicts(evidence, report, NORMAL)


# --- a refused signed request is a record, not a malformed record


def test_a_refused_signed_request_without_a_length_stays_a_judged_record(evidence, report):
    # mutant: integer(None) for content_length. The server answers a violation with a status
    # and no Content-Length; such a run stays in the report as a failed run, not an invalid one.
    sink = report["runs"][NORMAL]["server"]
    sink["signed"] = [
        {
            "range": None,
            "if_range": None,
            "status": 403,
            "content_length": None,
            "content_range": None,
            "bytes_sent": 0,
            "completed": False,
            "cut": False,
        }
    ]
    sink["bytes_sent"] = 0
    sink["credential_violations"] = 1
    bad = failed(evidence, report, NORMAL)
    assert {"server_ranges", "server_credentials", "write_accounting"} <= bad


# --- boundaries of the window's internal consistency


def test_one_write_as_big_as_the_whole_object_is_consistent(evidence, report):
    window = report["runs"][NORMAL]["client"]["window"]  # mutant L244 (largest <= size)
    window.update(write_calls=1, max_write_bytes=SIZE16, write_bytes=SIZE16)
    window["max_write_seconds"] = window["write_seconds"]  # mutant L246 (>=): a single write
    assert "write_block" in failed(evidence, report, NORMAL)  # consistent, and too big a block


def test_one_byte_per_write_is_consistent(evidence, report):
    window = report["runs"][NORMAL]["client"]["window"]  # mutant L245 (calls > size)
    window.update(write_calls=SIZE16, max_write_bytes=1, write_bytes=SIZE16)
    assert failed(evidence, report, NORMAL) == set()


def test_call_durations_may_fill_the_window_exactly(evidence, report):
    client = report["runs"][NORMAL]["client"]  # mutant L273 (total > elapsed)
    window = client["window"]
    kinds = ("write_seconds", "stage_fsync_seconds", "other_fsync_seconds", "full_sync_seconds")
    client["elapsed_seconds"] = math.fsum(window[key] for key in kinds)
    assert failed(evidence, report, NORMAL) == set()


def test_the_platform_call_may_carry_exactly_host_and_key(evidence, report):
    put(
        report["runs"][NORMAL], ("server", "json_header_names"), ["host", "x-api-key"]
    )  # mutant L397
    assert failed(evidence, report, NORMAL) == set()


def test_a_one_byte_server_block_is_a_block(evidence, report):
    put(report["runs"][NORMAL], ("server", "max_block_bytes"), 1)  # mutant L404
    assert failed(evidence, report, NORMAL) == set()


def test_a_negative_counter_is_refused_even_by_one(evidence, report):
    put(report["runs"][NORMAL], ("client", "window", "other_fsync_calls"), -1)  # mutant L108
    with pytest.raises(ValueError):
        verdicts(evidence, report, NORMAL)
    put(report["runs"][RESUME], ("client", "public", "bytes"), -1)
    with pytest.raises(ValueError):
        verdicts(evidence, report, RESUME)


def test_process_ids_are_positive_and_zero_is_no_process(evidence, report):
    row = report["runs"][NORMAL]  # mutants L477/L479 (minimum 1 -> 0)
    row["server"]["pid"] = row["server_process_pid"] = 0
    with pytest.raises(ValueError):
        verdicts(evidence, report, NORMAL)


# --- the vector file in the source map


def _map_with(monkeypatch, evidence, tmp_path, make_vector):
    namespace = evidence["source"].__globals__
    names = {
        name: "0" * 64
        for name in namespace["REQUIRED_SOURCES"]
        if name != namespace["UPLOAD_VECTOR"]
    }
    real = runpy.run_path
    startup = {"source": lambda root: {"commit": "a" * 40, "source_sha256": dict(names)}}

    def run_path(path, *args, **kwargs):
        return startup if str(path).endswith("startup_evidence.py") else real(path, *args, **kwargs)

    monkeypatch.setattr(runpy, "run_path", run_path)
    vector = tmp_path / namespace["UPLOAD_VECTOR"]
    vector.parent.mkdir(parents=True)
    make_vector(vector)


def test_a_missing_vector_file_is_a_refused_map_not_an_os_error(monkeypatch, tmp_path, evidence):
    _map_with(monkeypatch, evidence, tmp_path, lambda vector: None)  # mutants L174 And->Or, force
    with pytest.raises(ValueError, match="lacks"):
        evidence["source"](tmp_path)


def test_a_symlinked_vector_file_is_not_part_of_the_map(monkeypatch, tmp_path, evidence):
    target = tmp_path / "elsewhere.json"
    target.write_bytes(b"{}")
    _map_with(monkeypatch, evidence, tmp_path, lambda vector: vector.symlink_to(target))
    with pytest.raises(ValueError, match="lacks"):  # mutants L174 operand 1 -> True / force
        evidence["source"](tmp_path)


def test_a_regular_vector_file_is_hashed(monkeypatch, tmp_path, evidence):
    _map_with(monkeypatch, evidence, tmp_path, lambda vector: vector.write_bytes(b"{}"))
    value = evidence["source"](tmp_path)
    assert value["source_sha256"][evidence["UPLOAD_VECTOR"]] != "0" * 64
