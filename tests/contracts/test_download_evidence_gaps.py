"""What round one found nobody pinning in scripts/download_evidence.py."""

import pytest

from tests.contracts.test_download_evidence import (
    MIB,
    NORMAL,
    build,
    failed,
    put,
    rss,
    verdicts,
)
from tests.contracts.test_download_evidence import evidence as evidence
from tests.contracts.test_download_evidence import report as report

pytestmark = pytest.mark.usefixtures("evidence_publication_context")


def test_gap_source_after_must_be_a_valid_snapshot_even_in_a_failing_report(evidence, report):
    report["provenance"]["source_after"] = {"commit": "x", "source_sha256": {"a": "b"}}
    report["passed"] = report["accepted"] = False
    with pytest.raises(ValueError):
        evidence["summarize_report"](report)


def test_gap_wheel_metadata_digests_must_be_digests(evidence, report):
    report["provenance"]["wheel_metadata_sha256"]["METADATA"] = "not-a-digest"
    for row in report["runs"]:
        row["client"]["runtime"]["metadata_sha256"]["METADATA"] = "not-a-digest"
    with pytest.raises(ValueError):
        evidence["summarize_report"](report)


def test_gap_wheel_digests_must_be_digests(evidence, report):
    report["provenance"]["wheel_before"] = report["provenance"]["wheel_after"] = "x"
    with pytest.raises(ValueError):
        evidence["summarize_report"](report)


@pytest.mark.parametrize("key", ["other_fsync_calls", "full_sync_calls"])
def test_gap_window_counters_must_be_integers_not_booleans(evidence, report, key):
    put(report["runs"][NORMAL], ("client", "window", key), True)
    with pytest.raises(ValueError):
        verdicts(evidence, report, NORMAL)


def test_gap_signed_record_byte_count_must_be_an_integer(evidence, report):
    row = report["runs"][NORMAL]
    row["server"]["signed"][0]["bytes_sent"] = float(16 * MIB)  # equal to the sum, still no integer
    with pytest.raises(ValueError):
        verdicts(evidence, report, NORMAL)


def test_gap_one_bad_directory_name_among_good_ones_is_a_refused_record(evidence, report):
    put(report["runs"][NORMAL], ("client", "written", "entries"), ["weights.onnx", 5])
    with pytest.raises(ValueError):
        verdicts(evidence, report, NORMAL)
    put(report["runs"][NORMAL], ("server", "json_header_names"), ["host", 5])
    put(report["runs"][NORMAL], ("client", "written", "entries"), ["weights.onnx"])
    with pytest.raises(ValueError):
        verdicts(evidence, report, NORMAL)


def test_gap_a_sub_second_run_is_valid(evidence, report):
    client = report["runs"][NORMAL]["client"]
    client["elapsed_seconds"] = 0.5
    client["window"]["write_seconds"] = 0.2  # the real 16 MiB runs take 0.1-2 s
    assert failed(evidence, report, NORMAL) == set()


def test_gap_the_summary_reports_the_largest_not_the_smallest(evidence, report):
    report["runs"][3]["client"]["elapsed_seconds"] = 20.0
    rss(report["runs"][4]["client"], 6)
    report["growth"] = evidence["growth"](report["runs"])
    report["passed"] = report["growth"]["passed"]
    report["accepted"] = report["passed"]
    summary = evidence["summarize_report"](report)
    assert summary["max_elapsed_seconds"] == 20.0
    assert summary["max_extra_rss_upper_bound_bytes"] == 6 * MIB


def test_gap_two_concurrent_requests_are_within_the_documented_limit(evidence, report):
    put(report["runs"][NORMAL], ("server", "peak_active_requests"), 2)
    assert failed(evidence, report, NORMAL) == set()


def test_gap_one_stage_fsync_beyond_the_upper_bound_fails_a_plain_run(evidence, report):
    put(report["runs"][NORMAL], ("client", "window", "stage_fsync_calls"), 4)
    assert failed(evidence, report, NORMAL) == {"checkpoint_fsyncs"}


def test_gap_the_smallest_smoke_is_one_run(evidence):
    smoke = build(evidence, labels=("16",), samples=1)
    summary = evidence["summarize_report"](smoke)
    assert summary["cases"] == 1 and summary["partial"] is True and summary["accepted"] is False
