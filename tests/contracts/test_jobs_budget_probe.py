"""Resource evidence must reject wrong origins and preserve existing stores."""

import runpy
import sys
from pathlib import Path

import pytest

from tests.fixtures.seed_jobs import seed
from yorunge import api

PROBE = Path(__file__).resolve().parents[2] / "docs/research/p01-4-jobs-budget-probe.py"


@pytest.mark.parametrize("kind", ["existing", "symlink", "wrong_type"])
def test_seeder_refuses_existing_or_non_disposable_target(tmp_path, kind):
    target = tmp_path / "state"
    sentinel = tmp_path / "keep"
    sentinel.write_bytes(b"keep-existing-data")
    if kind == "existing":
        target.mkdir()
        (target / "keep").write_bytes(b"keep-existing-data")
    elif kind == "symlink":
        target.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        seed(target, dense=1 if kind == "wrong_type" else False)
    assert sentinel.read_bytes() == b"keep-existing-data"
    if kind == "existing":
        assert (target / "keep").read_bytes() == b"keep-existing-data"


def test_normal_fixture_is_one_valid_nonterminal_job_and_has_no_public_seed_command(tmp_path):
    state = tmp_path / "state"
    identifier = seed(state, dense=False)
    job = api.show_job(identifier, state_dir=state).data
    assert job.operation.status == "running"
    assert job.outcome is None
    assert len(job.attempts) == 1
    assert api.list_jobs(state_dir=state).data.jobs == (job.operation,)
    assert api.initialize_state(state_dir=state).data.store_schema_version == 6


def test_probe_rejects_repository_import_instead_of_installed_runtime(tmp_path):
    module = runpy.run_path(str(PROBE))
    prefix, expected = Path(sys.prefix), module["sources"]()
    with pytest.raises(ValueError, match="isolated installed"):
        module["installation"](prefix, expected)


def test_probe_rejects_unmarked_worker_before_state_access(tmp_path, monkeypatch):
    import sqlite3
    from argparse import Namespace

    module = runpy.run_path(str(PROBE))

    def denied(*args):
        pytest.fail("unmarked worker accessed SQLite")

    monkeypatch.setattr(sqlite3, "connect", denied)
    args = Namespace(manifest=tmp_path / "manifest.json")
    with pytest.raises(ValueError, match="orchestrator-owned"):
        module["worker"](args)
