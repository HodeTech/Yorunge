"""Measurement instrumentation preserves the product deadline callback and quantum."""

import runpy
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

PROBE = Path(__file__).resolve().parents[2] / "docs/research/p01-4-operation-budget-probe.py"


@pytest.mark.parametrize("interrupt", [False, True])
def test_vm_measurement_delegates_each_original_callback_without_changing_quantum(interrupt):
    module = runpy.run_path(str(PROBE))
    recorder = module["Recorder"]()
    calls = []

    def original():
        calls.append(1)
        return int(interrupt)

    with module["instrument"](recorder):
        with closing(sqlite3.connect(":memory:")) as connection:
            connection.set_progress_handler(original, 1000)
            query = (
                "WITH RECURSIVE n(x) AS (VALUES(0) UNION ALL SELECT x+1 FROM n WHERE x<10000) "
                "SELECT sum(x) FROM n"
            )
            if interrupt:
                with pytest.raises(sqlite3.OperationalError, match="interrupted"):
                    connection.execute(query)
            else:
                assert connection.execute(query).fetchone() == (50005000,)
    assert len(calls) > 0
    assert len(calls) == recorder.callbacks == recorder.delegated
    assert recorder.intervals == {1000}
    assert recorder.nominal_steps == 1000 * len(calls)


def test_probe_rejects_unmarked_or_non_disposable_store_before_sql_access(tmp_path, monkeypatch):
    module = runpy.run_path(str(PROBE))

    def denied(*args):
        pytest.fail("probe touched an unmarked database")

    monkeypatch.setattr(sqlite3, "connect", denied)
    with pytest.raises(ValueError, match="synthetic store"):
        module["worker"](tmp_path / "state", "full", None)


@pytest.mark.parametrize("mismatch", ["origin", "interpreter"])
def test_probe_rejects_wrong_checkout_or_interpreter(tmp_path, monkeypatch, mismatch):
    import sys

    import yorunge

    module = runpy.run_path(str(PROBE))
    if mismatch == "origin":
        monkeypatch.setattr(yorunge, "__file__", str(tmp_path / "foreign/__init__.py"))
    else:
        monkeypatch.setattr(sys, "prefix", str(tmp_path / "foreign-env"))
    with pytest.raises(RuntimeError):
        module["installation"]()
