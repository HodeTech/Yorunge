"""The installed worker's measurement core, with every collaborator a fake.

Only real runs (the native CI cells and the installation smoke) ever reached ``measured()``: a
refactor that took the peak after the call, or measured outside the instrumented window, would have
made the memory budget vacuous with every test green. These pin the order of one measurement, what
stays outside the window, the refusal of a runtime that changed under it, and the removal rule of
a verified payload.
"""

import argparse
import hashlib
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tests.fixtures import download_native_client as client
from tests.fixtures import download_native_data as data
from tests.fixtures import download_native_server as served

MIB = 1_048_576
WORK, WARM = Path("work-dir"), Path("warm-dir")


class Stage:
    """``measured()`` with every collaborator replaced by one that notes what it was asked."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, *, system: str, runtime_after: str) -> None:
        self.events: list[str] = []
        self.calls: dict[str, list[tuple[Any, ...]]] = {}
        provenances = iter(
            [
                {"pid": 1, "modules": {"yorunge": "a"}, "runtime": "same"},
                {"pid": 2, "modules": {"yorunge": "b"}, "runtime": runtime_after},
            ]
        )
        peaks = iter([(111, 1_000), (222, 2_000)])
        clock = iter([10.0, 12.5])

        def current_rss() -> int:
            self.note("baseline")
            return 5_000

        def flow(directory: Path, item: data.Fixture, digest: str) -> tuple[None, str]:
            self.note(f"flow:{item.label}", directory, digest)
            return None, f"result-of-{item.label}"

        def peak() -> tuple[int, int]:
            self.note("peak")
            return next(peaks)

        def tick() -> float:
            self.note("clock")
            return next(clock)

        def provenance(expected: dict[str, Any], prefix: Path) -> dict[str, Any]:
            self.note("provenance", expected, prefix)
            return next(provenances)

        def rss_bounds(baseline: int, h0: int, h1: int) -> tuple[int, int]:
            self.note("rss_bounds", baseline, h0, h1)
            return 7, 8

        def rss_bytes(native: int, name: str) -> int:
            self.note("rss_bytes", native, name)
            return native

        def linux_rss_baseline() -> tuple[int, int, int]:
            self.note("baseline")
            return 4_000, 1, 4_096

        replacements = {
            "prepare_current_rss": lambda: self.noted(
                "prepare_current_rss", ("method", current_rss)
            ),
            "expected_sha256": lambda size: self.noted("oracle", f"digest-{size}", size),
            "prepare": lambda directory: self.note("prepare", directory),
            "loopback_models": lambda ca, port: self.window(f"loopback:{port}"),
            "instruments": lambda directory: self.window("instruments", {"write_calls": 1}),
            "provenance": provenance,
            "flow": flow,
            "linux_rss_baseline": linux_rss_baseline,
            "rss_bytes": rss_bytes,
            "self_peak_rss": peak,
            "rss_bounds": rss_bounds,
            "outcome": lambda result, error: self.noted("outcome", {"of": result}, result, error),
            "verify_output": lambda *arguments: self.noted(
                "verify_output", {"verified": True}, *arguments
            ),
            "platform": SimpleNamespace(system=lambda: system),
            "time": SimpleNamespace(perf_counter=tick),
        }
        for name, value in replacements.items():
            monkeypatch.setattr(client, name, value)

    def note(self, name: str, *arguments: Any) -> None:
        self.events.append(name)
        self.calls.setdefault(name, []).append(arguments)

    def noted(self, name: str, result: Any, *arguments: Any) -> Any:
        self.note(name, *arguments)
        return result

    @contextmanager
    def window(self, name: str, value: Any = None) -> Iterator[Any]:
        self.note(f"+{name}")
        try:
            yield value
        finally:
            self.note(f"-{name}")

    def between(self, start: str, stop: str) -> list[str]:
        return self.events[self.events.index(start) : self.events.index(stop) + 1]


def run(
    monkeypatch: pytest.MonkeyPatch,
    *,
    label: str = "16",
    system: str = "Darwin",
    runtime_after: str = "same",
) -> tuple[Stage, dict[str, Any]]:
    stage = Stage(monkeypatch, system=system, runtime_after=runtime_after)
    args = argparse.Namespace(
        label=label, warm=WARM, work=WORK, ca=Path("ca"), port=2, warm_port=1, prefix=Path("env")
    )
    return stage, client.measured(args, {"expected": True})


# --- one measurement: the order is the method --------------------------------------------------


def test_one_measurement_runs_in_the_order_that_the_method_is(monkeypatch):
    stage, _ = run(monkeypatch)
    window = stage.between("+instruments", "-instruments")
    # B (the baseline), then H0 (the lifetime peak before the call), the call, H1 (the peak after
    # it): the timer brackets the call alone and the peaks bracket the timer
    assert window == [
        "+instruments",
        "baseline",
        "rss_bytes",
        "peak",
        "clock",
        "flow:16",
        "clock",
        "peak",
        "-instruments",
    ]
    # the warm run (its own server, its own directory) comes first and is not the measured window
    assert stage.events[: stage.events.index("+instruments")] == [
        "prepare_current_rss",
        "oracle",
        "oracle",
        "prepare",
        "prepare",
        "+loopback:1",
        "flow:warm",
        "-loopback:1",
        "provenance",
        "+loopback:2",
    ]
    assert stage.events[stage.events.index("-instruments") + 1] == "-loopback:2"


def test_nothing_that_is_compared_hashed_or_verified_runs_inside_the_window(monkeypatch):
    stage, _ = run(monkeypatch)
    window = stage.between("+instruments", "-instruments")
    after = stage.events[stage.events.index("-instruments") :]
    for name in ("rss_bounds", "provenance", "verify_output", "outcome"):
        assert name not in window, name
        assert name in after, name
    assert after.index("rss_bounds") < after.index("provenance")  # the bounds, then the identity
    assert after.count("outcome") == 2  # the measured call and the warm one are both described


def test_the_bounds_are_taken_from_the_baseline_and_the_two_peaks_in_that_order(monkeypatch):
    stage, result = run(monkeypatch)
    assert stage.calls["rss_bounds"] == [(5_000, 1_000, 2_000)]
    assert stage.calls["rss_bytes"] == [(5_000, "Darwin")]
    assert result["baseline_rss_native"] == 5_000
    assert result["baseline_rss_bytes"] == 5_000
    assert result["baseline_rss_method"] == "method"
    assert result["pretransfer_peak_rss_native"] == 111
    assert result["pretransfer_peak_rss_bytes"] == 1_000
    assert result["peak_rss_native"] == 222
    assert result["peak_rss_bytes"] == 2_000
    assert result["extra_rss_lower_bound_bytes"] == 7
    assert result["extra_rss_upper_bound_bytes"] == 8
    assert result["rss_native_unit"] == "bytes"


def test_the_elapsed_time_is_the_call_alone(monkeypatch):
    _, result = run(monkeypatch)
    assert result["elapsed_seconds"] == 2.5  # two clock reads, 10.0 then 12.5, around the call


def test_on_linux_the_baseline_is_read_in_pages_inside_the_window(monkeypatch):
    stage, result = run(monkeypatch, system="Linux")
    window = stage.between("+instruments", "-instruments")
    assert window[:3] == ["+instruments", "baseline", "rss_bytes"]
    assert stage.events.count("baseline") == 1  # the Linux reader replaces the portable one
    assert stage.calls["rss_bytes"] == [(4_000, "Linux")]
    assert result["baseline_rss_pages"] == 1
    assert result["rss_page_bytes"] == 4_096
    assert result["rss_native_unit"] == "KiB"


def test_off_linux_there_are_no_page_details(monkeypatch):
    _, result = run(monkeypatch, system="Darwin")
    assert "baseline_rss_pages" not in result
    assert "rss_page_bytes" not in result


# --- what is recorded -------------------------------------------------------------------------


def test_the_record_describes_the_measured_call_the_warm_call_and_the_runtime_after(monkeypatch):
    stage, result = run(monkeypatch)
    assert result["pid"] == os.getpid()
    assert result["runtime"]["pid"] == 2  # the provenance AFTER the window, not before it
    assert result["window"] == {"write_calls": 1}
    assert result["public"] == {"of": "result-of-16"}
    assert result["warm"] == {"of": "result-of-warm"}
    assert result["written"] == {"verified": True}
    assert stage.calls["outcome"] == [("result-of-16", None), ("result-of-warm", None)]


@pytest.mark.parametrize("label", data.LABELS)
def test_each_label_warms_on_its_own_object_and_both_are_hashed_by_the_independent_oracle(
    monkeypatch, label
):
    stage, _ = run(monkeypatch, label=label)
    warm = data.WARM_OF[label]
    sizes = [data.FIXTURES[warm].size, data.FIXTURES[label].size]
    assert stage.calls["oracle"] == [(data.FIXTURES[label].size,), (data.FIXTURES[warm].size,)]
    assert stage.calls[f"flow:{warm}"] == [(WARM, f"digest-{sizes[0]}")]
    assert stage.calls[f"flow:{label}"] == [(WORK, f"digest-{sizes[1]}")]
    # the output check gets the MEASURED object and ITS digest, never the warm one
    assert stage.calls["verify_output"] == [(WORK, data.FIXTURES[label], f"digest-{sizes[1]}")]


def test_a_runtime_that_changed_during_the_measurement_is_refused(monkeypatch):
    with pytest.raises(ValueError, match="installed download runtime changed during measurement"):
        run(monkeypatch, runtime_after="another")


def test_the_process_and_module_identity_do_not_count_as_a_change(monkeypatch):
    stage, result = run(monkeypatch)  # pid 1 -> 2 and different module paths: the same runtime
    assert result["runtime"]["runtime"] == "same"
    assert [call[1] for call in stage.calls["provenance"]] == [Path("env"), Path("env")]


def test_the_provenance_is_taken_before_and_after_the_window_and_nowhere_else(monkeypatch):
    stage, _ = run(monkeypatch)
    positions = [i for i, name in enumerate(stage.events) if name == "provenance"]
    assert len(positions) == 2
    start, stop = stage.events.index("+instruments"), stage.events.index("-instruments")
    assert positions[0] < start
    assert positions[1] > stop


# --- what is on disk afterwards, outside the window --------------------------------------------


def written(tmp_path: Path, *, damaged: bool = False, extra: bytes = b"") -> tuple[Any, Any, str]:
    item = data.fixture("warm")
    layout = data.paths(tmp_path)
    layout.out.mkdir(parents=True)
    with layout.target.open("wb") as target:
        for block in served.body_blocks(0, item.size):
            target.write(block)
        target.write(extra)
    if damaged:
        raw = bytearray(layout.target.read_bytes())
        raw[17] ^= 0xFF
        layout.target.write_bytes(bytes(raw))
    return item, layout, data.expected_sha256(item.size)


def test_a_verified_payload_is_removed_and_the_record_says_so(tmp_path):
    item, layout, digest = written(tmp_path)
    assert client.verify_output(tmp_path, item, digest) == {
        "file_bytes": item.size,
        "file_sha256": digest,
        "entries": [layout.target.name],
        "payload_removed": True,
    }
    assert not layout.target.exists()  # the oracle fully determines it: nothing to keep


def test_a_payload_that_differs_from_the_oracle_is_kept_for_diagnosis(tmp_path):
    item, layout, digest = written(tmp_path, damaged=True)
    record = client.verify_output(tmp_path, item, digest)
    assert record["payload_removed"] is False
    assert layout.target.exists()
    assert record["file_bytes"] == item.size
    assert record["file_sha256"] != digest
    assert record["file_sha256"] == hashlib.sha256(layout.target.read_bytes()).hexdigest()


def test_a_payload_of_the_wrong_size_is_kept(tmp_path):
    item, layout, digest = written(tmp_path, extra=b"x")
    record = client.verify_output(tmp_path, item, digest)
    assert record["file_bytes"] == item.size + 1
    assert record["payload_removed"] is False
    assert layout.target.exists()


def test_a_payload_whose_digest_matches_but_is_not_the_measured_object_is_kept(tmp_path):
    item, layout, digest = written(tmp_path)  # the 1 MiB warm bytes and their own digest
    other = data.fixture("16")  # ... offered as the answer for the 16 MiB object
    record = client.verify_output(tmp_path, other, digest)
    assert record["file_sha256"] == digest
    assert record["payload_removed"] is False
    assert layout.target.exists()
    assert item.size != other.size


def test_the_directory_listing_is_taken_before_anything_is_removed(tmp_path):
    item, layout, digest = written(tmp_path)
    (layout.out / "leftover.part").write_bytes(b"x")  # something the product should not leave
    record = client.verify_output(tmp_path, item, digest)
    assert record["entries"] == ["leftover.part", layout.target.name]
    assert (layout.out / "leftover.part").exists()  # a stray file is never the worker's to remove
