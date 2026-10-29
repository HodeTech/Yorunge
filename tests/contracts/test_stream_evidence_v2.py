"""Independent handwritten RSS interval receipts; no benchmark helpers are used."""

import copy
import gzip
import json
import runpy
from pathlib import Path

import pytest

LEGACY = runpy.run_path(str(Path(__file__).with_name("test_stream_evidence.py")))
CHECKS = LEGACY["CHECKS"]
MIB = 1_048_576
SIZES = [16 * MIB, 256 * MIB, 1024 * MIB]


def receipt(bounds=((2 * MIB, 2 * MIB),) * 3, *, span=0, growth=True, passed=True, unit="KiB"):
    """Supply expected bounds, cross-size span and outcomes explicitly, never derive them."""
    report = LEGACY["receipt"](unit)
    report.update(schema_version=2, report_kind="raw_stream_budget_v2", passed=passed)
    del report["size_growth_diagnostic"]
    baseline_method = (
        "linux.proc_self_status.VmRSS"
        if unit == "KiB"
        else "darwin.MACH_TASK_BASIC_INFO.resident_size"
    )
    factor = 1024 if unit == "KiB" else 1
    for run, (lower, upper) in zip(report["runs"], bounds, strict=True):
        del run["extra_rss_bytes"]
        # An unchanged prior high-water gives [0, upper]; a new one gives [upper, upper].
        baseline = 32 * MIB
        peak = baseline + upper
        before = peak if lower == 0 else baseline
        run.update(
            baseline_rss_native=baseline // factor,
            baseline_rss_bytes=baseline,
            baseline_rss_method=baseline_method,
            pretransfer_peak_rss_native=before // factor,
            pretransfer_peak_rss_bytes=before,
            peak_rss_native=peak // factor,
            peak_rss_bytes=peak,
            extra_rss_lower_bound_bytes=lower,
            extra_rss_upper_bound_bytes=upper,
        )
    report["method"].update(
        rss_method="instantaneous_baseline_and_lifetime_peak_interval_v2",
        rss_baseline="native_current_rss_after_imports_and_fixed_tls_warmup",
        rss_baseline_source=baseline_method,
        rss_peak_source="linux.proc_self_status.VmHWM"
        if unit == "KiB"
        else "resource.getrusage(RUSAGE_SELF).ru_maxrss",
        rss_interval="new_high_water_exact_else_zero_to_upper",
        rss_window="after_pretransfer_peak_until_posttransfer_peak_including_instrumentation",
        backpressure="consumer awaits each next chunk; no producer task or body queue",
        limit="synthetic raw byte transport; no dataset endpoint or hard physical deadline",
    )
    report["limits"] = {
        "extra_rss_upper_bound_bytes": 67_108_864,
        "cross_size_span_upper_bound_bytes": 8_388_608,
        "chunk_bytes": 32_768,
        "connections": 2,
        "total_deadline_seconds": 120.0,
    }
    report["size_growth_acceptance"] = {
        "method": "max_cross_size_upper_minus_lower",
        "size_bytes": SIZES.copy(),
        "lower_bound_bytes": [pair[0] for pair in bounds],
        "upper_bound_bytes": [pair[1] for pair in bounds],
        "span_upper_bound_bytes": span,
        "passed": growth,
    }
    return report


def archive(root, report, name):
    (root / "dist").mkdir(parents=True, exist_ok=True)
    (root / "docs/research").mkdir(parents=True, exist_ok=True)
    source = root / "dist" / name
    original = (json.dumps(report, indent=4) + "\n").encode()
    source.write_bytes(original)
    CHECKS["archive_report"](root, source, None)
    packed = root / "docs/research/raw" / (name + ".gz")
    assert gzip.decompress(packed.read_bytes()) == original == source.read_bytes()
    entries = json.loads((root / "docs/research/evidence-manifest.json").read_bytes())["entries"]
    return next(entry["summary"] for entry in entries if entry["name"] == name), packed


@pytest.mark.parametrize("unit", ["KiB", "bytes"])
def test_v2_native_baseline_peak_interval_and_summary_are_explicit(unit):
    report = receipt(unit=unit)
    summary = CHECKS["summarize"](report)
    assert summary["kind"] == "raw_stream_budget_v2"
    assert summary["passed"] is True
    assert summary["rss_method"] == "instantaneous_baseline_and_lifetime_peak_interval_v2"
    assert summary["rss_native_unit"] == unit
    assert summary["size_growth_acceptance"] == report["size_growth_acceptance"]
    for measurement in summary["measurements"].values():
        assert measurement["baseline_rss_bytes"] == 33_554_432
        assert measurement["pretransfer_peak_rss_bytes"] == 33_554_432
        assert measurement["peak_rss_bytes"] == 35_651_584
        assert measurement["extra_rss_lower_bound_bytes"] == 2_097_152
        assert measurement["extra_rss_upper_bound_bytes"] == 2_097_152
        assert "extra_rss_bytes" not in measurement


@pytest.mark.parametrize(
    "bounds,span,growth",
    [
        (((MIB, MIB), (16 * MIB, 16 * MIB), (64 * MIB, 64 * MIB)), 63 * MIB, False),
        (((0, 60 * MIB), (0, 60 * MIB), (64 * MIB, 64 * MIB)), 64 * MIB, False),
        (((MIB, MIB), (9 * MIB, 9 * MIB), (9 * MIB, 9 * MIB)), 8 * MIB, True),
        (
            ((MIB, MIB), (9 * MIB, 9 * MIB), (9 * MIB + 1, 9 * MIB + 1)),
            8 * MIB + 1,
            False,
        ),
        (((0, 10 * MIB), (5 * MIB, 5 * MIB), (5 * MIB, 5 * MIB)), 5 * MIB, True),
        (((64 * MIB, 64 * MIB),) * 3, 0, True),
    ],
    ids=["linear", "hidden-growth", "exact-8MiB", "8MiB-plus-byte", "exclude-self", "constant-64"],
)
def test_cross_size_interval_gate_has_handwritten_expected_span(bounds, span, growth):
    report = receipt(bounds, span=span, growth=growth, passed=growth, unit="bytes")
    summary = CHECKS["summarize"](report)
    assert all(run["passed"] for run in summary["measurements"].values())
    assert summary["passed"] is growth
    assert summary["size_growth_acceptance"] == {
        "method": "max_cross_size_upper_minus_lower",
        "size_bytes": [16_777_216, 268_435_456, 1_073_741_824],
        "lower_bound_bytes": [pair[0] for pair in bounds],
        "upper_bound_bytes": [pair[1] for pair in bounds],
        "span_upper_bound_bytes": span,
        "passed": growth,
    }
    if not growth:
        report["passed"] = True
        with pytest.raises(ValueError):
            CHECKS["summarize"](report)


def test_previous_100MiB_peak_cannot_mask_65MiB_above_current_baseline():
    report = receipt(((65 * MIB, 65 * MIB),) * 3, passed=False)
    for run in report["runs"]:
        run.update(
            baseline_rss_native=40 * 1024,
            baseline_rss_bytes=40 * MIB,
            pretransfer_peak_rss_native=100 * 1024,
            pretransfer_peak_rss_bytes=100 * MIB,
            peak_rss_native=105 * 1024,
            peak_rss_bytes=105 * MIB,
            passed=False,
        )
    summary = CHECKS["summarize"](report)
    assert summary["passed"] is False
    assert summary["size_growth_acceptance"]["passed"] is True
    assert all(not run["passed"] for run in summary["measurements"].values())
    report["runs"][0]["passed"] = True
    with pytest.raises(ValueError):
        CHECKS["summarize"](report)


def test_truthful_growth_failure_roundtrips_without_becoming_acceptance(tmp_path):
    report = receipt(
        ((MIB, MIB), (16 * MIB, 16 * MIB), (64 * MIB, 64 * MIB)),
        span=63 * MIB,
        growth=False,
        passed=False,
    )
    summary, _ = archive(tmp_path, report, "growth-failure.json")
    assert CHECKS["verify"](tmp_path) == 1
    assert summary["passed"] is False
    assert summary["size_growth_acceptance"]["span_upper_bound_bytes"] == 66_060_288
    assert all(run["passed"] for run in summary["measurements"].values())


@pytest.mark.parametrize(
    "part,key,value",
    [
        ("report", "schema_version", True),
        ("report", "schema_version", 1),
        ("report", "report_kind", "raw_stream_budget_v1"),
        ("report", "report_kind", "raw_stream_budget_v3"),
        ("report", "passed", 1),
        ("run", "baseline_rss_bytes", True),
        ("run", "pretransfer_peak_rss_bytes", True),
        ("run", "peak_rss_bytes", float("inf")),
        ("run", "baseline_rss_native", True),
        ("run", "pretransfer_peak_rss_native", True),
        ("run", "pretransfer_peak_rss_native", 32_768.5),
        ("run", "peak_rss_native", float("nan")),
        ("run", "pretransfer_peak_rss_native", 32_769),
        ("run", "extra_rss_upper_bound_bytes", 2_097_153),
        ("run", "extra_rss_lower_bound_bytes", 0),
        ("run", "extra_rss_lower_bound_bytes", True),
        ("run", "extra_rss_upper_bound_bytes", float("nan")),
        ("run", "baseline_rss_method", "darwin.MACH_TASK_BASIC_INFO.resident_size"),
        ("run", "rss_native_unit", "bytes"),
        ("method", "rss_method", "resource.getrusage(RUSAGE_SELF).ru_maxrss"),
        ("method", "rss_baseline", "fresh high-water after TLS warmup"),
        ("method", "rss_baseline_source", "linux.proc_self_smaps_rollup.Rss"),
        ("method", "rss_peak_source", "instantaneous RSS"),
        ("method", "rss_peak_source", "resource.getrusage(RUSAGE_SELF).ru_maxrss"),
        ("method", "rss_interval", "clamp_negative_to_zero"),
        ("method", "rss_window", "transfer_only"),
        ("method", "backpressure", "one awaited next chunk"),
        ("method", "limit", "synthetic raw byte transport"),
        ("limits", "extra_rss_upper_bound_bytes", 67_108_865),
        ("limits", "cross_size_span_upper_bound_bytes", 8_388_609),
        ("limits", "cross_size_span_upper_bound_bytes", True),
        ("growth", "method", "max_upper_minus_min_lower"),
        ("growth", "span_upper_bound_bytes", True),
        ("growth", "span_upper_bound_bytes", 1),
        ("growth", "passed", 1),
        ("growth", "passed", False),
        ("growth", "size_bytes", [True, 268_435_456, 1_073_741_824]),
        ("growth", "lower_bound_bytes", [0, 2_097_152, 2_097_152]),
        ("growth", "upper_bound_bytes", [True, 2_097_152, 2_097_152]),
    ],
)
def test_v2_rejects_forged_schema_numbers_methods_arithmetic_and_limits(part, key, value):
    report = receipt()
    target = {
        "report": report,
        "run": report["runs"][0],
        "method": report["method"],
        "limits": report["limits"],
        "growth": report["size_growth_acceptance"],
    }[part]
    target[key] = value
    with pytest.raises(ValueError):
        CHECKS["summarize"](report)


@pytest.mark.parametrize("before,after", [(31 * MIB, 34 * MIB), (35 * MIB, 34 * MIB)])
def test_v2_rejects_reversed_native_observations_instead_of_clamping(before, after):
    report = receipt()
    run = report["runs"][0]
    run.update(
        pretransfer_peak_rss_bytes=before,
        pretransfer_peak_rss_native=before // 1024,
        peak_rss_bytes=after,
        peak_rss_native=after // 1024,
    )
    with pytest.raises(ValueError):
        CHECKS["summarize"](report)


def test_fractional_native_counters_are_rejected_even_when_byte_conversion_is_exact():
    report = receipt()
    run = report["runs"][0]
    for prefix in ("baseline", "pretransfer_peak", "peak"):
        run[prefix + "_rss_native"] += 0.5
        run[prefix + "_rss_bytes"] += 512
    with pytest.raises(ValueError):
        CHECKS["summarize"](report)


@pytest.mark.parametrize("part", ["report", "run", "method", "limits", "growth"])
@pytest.mark.parametrize("damage", ["extra", "missing"])
def test_v2_new_boundaries_are_closed(part, damage):
    report = receipt()
    target = {
        "report": report,
        "run": report["runs"][0],
        "method": report["method"],
        "limits": report["limits"],
        "growth": report["size_growth_acceptance"],
    }[part]
    if damage == "extra":
        target["unchecked"] = 1
    else:
        del target[next(iter(target))]
    with pytest.raises(ValueError):
        CHECKS["summarize"](report)


def test_unchanged_high_water_cannot_claim_an_exact_lower_bound():
    report = receipt(((0, 2 * MIB),) * 3, span=2 * MIB)
    report["runs"][0]["extra_rss_lower_bound_bytes"] = 2 * MIB
    report["size_growth_acceptance"]["lower_bound_bytes"][0] = 2 * MIB
    with pytest.raises(ValueError):
        CHECKS["summarize"](report)


def test_forged_growth_pass_is_rejected_even_when_every_run_passes():
    report = receipt(
        ((0, 60 * MIB), (0, 60 * MIB), (64 * MIB, 64 * MIB)),
        span=64 * MIB,
        growth=False,
        passed=False,
    )
    report["size_growth_acceptance"]["passed"] = True
    report["passed"] = True
    with pytest.raises(ValueError):
        CHECKS["summarize"](report)


def test_v1_linear_rss_stays_historical_validity_without_v2_growth_upgrade():
    report = LEGACY["receipt"]()
    for run, extra in zip(report["runs"], (MIB, 16 * MIB, 64 * MIB), strict=True):
        run["extra_rss_bytes"] = extra
        run["peak_rss_bytes"] = 32 * MIB + extra
        run["peak_rss_native"] = run["peak_rss_bytes"] // 1024
    report["size_growth_diagnostic"]["extra_rss_bytes"] = [MIB, 16 * MIB, 64 * MIB]
    original = copy.deepcopy(report)
    summary = CHECKS["summarize"](report)
    assert summary["kind"] == "raw_stream_budget_v1"
    assert summary["passed"] is True
    assert "size_growth_acceptance" not in summary
    assert report == original


def test_v2_archiving_does_not_rewrite_historical_64MiB_receipt(tmp_path):
    old = LEGACY["receipt"]()
    for run in old["runs"]:
        run.update(extra_rss_bytes=64 * MIB, peak_rss_bytes=96 * MIB, peak_rss_native=96 * 1024)
    old["size_growth_diagnostic"]["extra_rss_bytes"] = [64 * MIB] * 3
    old_summary, old_packed = archive(tmp_path, old, "legacy-64.json")
    old_bytes = old_packed.read_bytes()
    summary_snapshot = copy.deepcopy(old_summary)
    new_summary, _ = archive(tmp_path, receipt(), "current-v2.json")
    assert CHECKS["verify"](tmp_path) == 2
    manifest = tmp_path / "docs/research/evidence-manifest.json"
    entries = json.loads(manifest.read_bytes())["entries"]
    assert old_packed.read_bytes() == old_bytes
    assert any(entry["summary"] == summary_snapshot for entry in entries)
    assert old_summary["kind"] == "raw_stream_budget_v1"
    assert old_summary["passed"] is True
    assert new_summary["kind"] == "raw_stream_budget_v2"
