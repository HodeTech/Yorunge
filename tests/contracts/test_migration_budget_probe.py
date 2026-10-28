import runpy
import sqlite3
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import pytest

PROBE = Path(__file__).parents[2] / "docs/research/p01-3-migration-budget-probe.py"


def test_vm_counter_preserves_original_progress_cancellation():
    helpers = runpy.run_path(str(PROBE))
    recorder = helpers["Recorder"](True)
    factory = helpers["observed_factory"](recorder)
    calls = []
    with closing(sqlite3.connect(":memory:", factory=factory)) as conn:
        conn.set_progress_handler(lambda: calls.append(True) or 1, 17)
        sql = (
            "WITH RECURSIVE n(x) AS (VALUES(0) UNION ALL SELECT x+1 FROM n WHERE x<1000) "
            "SELECT sum(x) FROM n"
        )
        with pytest.raises(sqlite3.OperationalError) as failure:
            conn.execute(sql)
        assert failure.value.sqlite_errorcode == sqlite3.SQLITE_INTERRUPT
    assert calls == [True]
    assert recorder.steps >= 17
    assert recorder.deadline_calls == 1
    assert recorder.original_intervals == {17}


def test_vm_counter_preserves_disabled_progress_handler():
    helpers = runpy.run_path(str(PROBE))
    recorder = helpers["Recorder"](True)
    factory = helpers["observed_factory"](recorder)
    with closing(sqlite3.connect(":memory:", factory=factory)) as conn:
        conn.set_progress_handler(lambda: pytest.fail("disabled callback was invoked"), 0)
        assert conn.execute("SELECT 1+2").fetchone() == (3,)
    assert recorder.steps > 0
    assert recorder.deadline_calls == 0


def test_worker_rejects_existing_paths_without_synthetic_orchestrator_marker(tmp_path):
    helpers = runpy.run_path(str(PROBE))
    root = tmp_path / "existing-user-state"
    args = SimpleNamespace(
        worker=str(root), case="schema-4", preview_only=False, confirmation=None, vm=False
    )
    with pytest.raises(ValueError, match="only the orchestrator"):
        helpers["worker"](args)
    assert not root.exists()
