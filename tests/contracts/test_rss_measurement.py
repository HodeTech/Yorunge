"""Independent native RSS and historical-peak masking regression vectors."""

import ctypes
import io
from types import SimpleNamespace

import pytest

from tests.fixtures import stream_budget

MIB = 1_048_576


def stat_fixture(pages="8192", comm="python"):
    # State is field 3; twenty fields precede resident pages at field 24.
    return f"123 ({comm}) R " + "0 " * 20 + pages + " 0 0\n"


@pytest.mark.parametrize("comm", ["python", "a b", "a ) b ( c", "())", "a\nb"])
def test_linux_stat_selects_field_24_after_complete_comm(comm):
    assert stream_budget.parse_linux_stat_rss(stat_fixture(comm=comm)) == 8192


@pytest.mark.parametrize(
    "value",
    [
        "",
        "VmRSS: 123 kB\n",
        "123 python R " + "0 " * 20 + "8192",
        "123 (python) R 0 0",
        "0 (python) R " + "0 " * 20 + "8192",
        stat_fixture("-1"),
        stat_fixture("0"),
        stat_fixture("1.5"),
        stat_fixture("１２"),
        stat_fixture("12kB"),
        stat_fixture("+12"),
        b"123 (python) R 0",
        None,
    ],
)
def test_linux_stat_rejects_missing_or_invalid_resident_pages(value):
    with pytest.raises(ValueError):
        stream_budget.parse_linux_stat_rss(value)


@pytest.mark.parametrize(
    "page_bytes,expected_kib", [(4096, 32768), (16384, 131072), (65536, 524288)]
)
def test_linux_baseline_keeps_raw_pages_and_actual_page_size(monkeypatch, page_bytes, expected_kib):
    reads = []

    def opened(path, **kwargs):
        reads.append(str(path))
        assert str(path) == "/proc/self/stat"
        assert kwargs == {"encoding": "ascii"}
        return io.StringIO(stat_fixture())

    def sysconf(name):
        assert name == "SC_PAGE_SIZE"
        return page_bytes

    monkeypatch.setattr(stream_budget.Path, "open", opened)
    monkeypatch.setattr(stream_budget.os, "sysconf", sysconf)
    assert stream_budget.linux_rss_baseline() == (expected_kib, 8192, page_bytes)
    assert reads == ["/proc/self/stat"]


@pytest.mark.parametrize("page_bytes", [True, 0, -1, 512, 1025, 4096.0, "4096"])
def test_linux_baseline_rejects_invalid_page_sizes_without_fallback(monkeypatch, page_bytes):
    monkeypatch.setattr(stream_budget.Path, "open", lambda *a, **k: io.StringIO(stat_fixture()))
    monkeypatch.setattr(stream_budget.os, "sysconf", lambda name: page_bytes)
    with pytest.raises(ValueError, match="page size"):
        stream_budget.linux_rss_baseline()


def test_linux_current_normalizes_pages_to_peak_counter_kib(monkeypatch):
    monkeypatch.setattr(stream_budget, "linux_rss_baseline", lambda: (32768, 8192, 4096))
    assert stream_budget.linux_current_rss() == 32768
    assert stream_budget.rss_bytes(32768, "Linux") == 33_554_432


@pytest.mark.parametrize("error", [FileNotFoundError, PermissionError, UnicodeError])
def test_linux_native_read_errors_are_not_silenced(monkeypatch, error):
    def denied(*args, **kwargs):
        raise error("native probe failure")

    monkeypatch.setattr(stream_budget.Path, "open", denied)
    with pytest.raises(error, match="native probe failure"):
        stream_budget.linux_current_rss()


def test_linux_stat_read_has_a_fixed_size_bound(monkeypatch):
    monkeypatch.setattr(
        stream_budget.Path, "open", lambda *args, **kwargs: io.StringIO("x" * 65_536)
    )
    with pytest.raises(ValueError, match="bounded probe"):
        stream_budget.linux_current_rss()


def test_mach_abi_has_the_exported_field_widths_offsets_and_count():
    info = stream_budget.MachTaskBasicInfo
    assert ctypes.sizeof(info) == 48
    assert ctypes.alignment(info) == 4
    assert ctypes.sizeof(stream_budget.MachTimeValue) == 8
    assert [getattr(info, name).offset for name, _ in info._fields_] == [0, 8, 16, 24, 32, 40, 44]
    assert ctypes.sizeof(info) // ctypes.sizeof(ctypes.c_uint32) == 12


def mach_probe(*, result=0, count=12, resident_size=33_554_432):
    probe = object.__new__(stream_budget.DarwinRssProbe)
    probe.task = 77

    def task_info(task, flavor, info_pointer, count_pointer):
        assert task == 77
        assert flavor == 20
        assert count_pointer._obj.value == 12
        assert isinstance(info_pointer._obj, stream_budget.MachTaskBasicInfo)
        info_pointer._obj.resident_size = resident_size
        count_pointer._obj.value = count
        return result

    probe.task_info = task_info
    return probe


def test_mach_current_probe_returns_resident_bytes_without_unit_conversion():
    assert mach_probe()() == 33_554_432
    assert stream_budget.rss_bytes(mach_probe()(), "Darwin") == 33_554_432


@pytest.mark.parametrize(
    "arguments", [{"result": 5}, {"count": 11}, {"count": 13}, {"resident_size": 0}]
)
def test_mach_call_errors_count_changes_and_zero_rss_are_rejected(arguments):
    probe = mach_probe(**arguments)
    with pytest.raises(ValueError):
        probe()


def test_mach_initialization_loads_system_library_and_declares_the_abi(monkeypatch):
    function = SimpleNamespace()
    library = SimpleNamespace(task_info=function)

    def load(path):
        assert path == "/usr/lib/libSystem.B.dylib"
        return library

    def port(cls, handle, symbol):
        assert handle is library
        assert symbol == "mach_task_self_"
        return SimpleNamespace(value=77)

    monkeypatch.setattr(stream_budget.ctypes, "CDLL", load)
    monkeypatch.setattr(stream_budget.ctypes.c_uint32, "in_dll", classmethod(port))
    probe = stream_budget.DarwinRssProbe()
    assert probe.task == 77
    assert function.argtypes == [
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.POINTER(stream_budget.MachTaskBasicInfo),
        ctypes.POINTER(ctypes.c_uint32),
    ]
    assert function.restype is ctypes.c_int32


def test_mach_library_loading_failure_is_not_silenced(monkeypatch):
    def failed(*args):
        raise OSError("missing native API")

    monkeypatch.setattr(stream_budget.ctypes, "CDLL", failed)
    with pytest.raises(OSError, match="missing native API"):
        stream_budget.DarwinRssProbe()


@pytest.mark.parametrize(
    "system,method",
    [
        ("Linux", "linux.proc_self_stat.rss_pages"),
        ("Darwin", "darwin.MACH_TASK_BASIC_INFO.resident_size"),
    ],
)
def test_probe_and_peak_machinery_are_warmed_before_returning_a_reader(monkeypatch, system, method):
    calls = []

    def current():
        calls.append("current")
        return 32768

    monkeypatch.setattr(stream_budget.platform, "system", lambda: system)
    monkeypatch.setattr(stream_budget, "linux_current_rss", current)
    monkeypatch.setattr(stream_budget, "DarwinRssProbe", lambda: current)
    monkeypatch.setattr(stream_budget, "self_peak_rss", lambda: calls.append("peak"))
    actual_method, reader = stream_budget.prepare_current_rss()
    assert actual_method == method
    assert calls == ["current", "peak"]
    assert reader() == 32768


def test_unsupported_platform_does_not_fall_back_to_peak_rss(monkeypatch):
    monkeypatch.setattr(stream_budget.platform, "system", lambda: "Windows")
    with pytest.raises(ValueError, match="Linux or macOS"):
        stream_budget.prepare_current_rss()


@pytest.mark.parametrize("native", [True, -1, 0.5, float("nan"), float("inf"), "1", None])
def test_invalid_native_numbers_cannot_become_rss_bytes(native):
    with pytest.raises(ValueError, match="invalid RSS"):
        stream_budget.rss_bytes(native, "Linux")


@pytest.mark.parametrize(
    "baseline,before,after,expected_lower,expected_upper",
    [
        (32, 128, 128, 0, 96),
        (40, 100, 105, 65, 65),
        (40, 100, 100, 0, 60),
        (40, 40, 40, 0, 0),
        (40, 40, 104, 64, 64),
    ],
)
def test_independent_interval_vectors_preserve_old_peak_uncertainty(
    baseline, before, after, expected_lower, expected_upper
):
    assert stream_budget.rss_bounds(baseline * MIB, before * MIB, after * MIB) == (
        expected_lower * MIB,
        expected_upper * MIB,
    )


@pytest.mark.parametrize(
    "values",
    [(40, 39, 50), (40, 50, 49), (40, 50, 39), (0, 1, 1), (-1, 1, 1), (True, 1, 1), (1, 1.0, 1)],
)
def test_inconsistent_or_invalid_counters_are_not_clamped_into_success(values):
    with pytest.raises(ValueError):
        stream_budget.rss_bounds(*values)
