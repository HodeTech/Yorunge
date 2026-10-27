import json
import runpy
import shutil
import stat
from pathlib import Path

import pytest


def report_writer(tmp_path):
    helper = Path(__file__).parents[2] / "docs/research/probe_output.py"
    target = tmp_path / "repo/docs/research/probe_output.py"
    target.parent.mkdir(parents=True)
    shutil.copyfile(helper, target)
    return target.parents[2], runpy.run_path(str(target))["write_report"]


@pytest.mark.parametrize("name", ["p01-2-decision-probe.json", "p01-2-review-probe.json"])
def test_research_report_uses_only_private_no_clobber_documented_output(tmp_path, name):
    root, write = report_writer(tmp_path)
    write(name, {"synthetic": True})
    path = root / "dist" / name
    assert json.loads(path.read_text()) == {"synthetic": True}
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    with pytest.raises(FileExistsError):
        write(name, {"synthetic": False})
    assert json.loads(path.read_text()) == {"synthetic": True}


@pytest.mark.parametrize(
    "attack", ["traversal", "directory-link", "file-link", "writable-directory"]
)
def test_research_output_cannot_clobber_arbitrary_path_or_follow_links(tmp_path, attack):
    root, write = report_writer(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    retained = outside / "p01-2-review-probe.json"
    retained.write_bytes(b"retained")
    filename = "p01-2-review-probe.json"
    expected = (ValueError, OSError)
    if attack == "traversal":
        filename = "../outside/p01-2-review-probe.json"
    elif attack == "directory-link":
        (root / "dist").symlink_to(outside)
    elif attack == "file-link":
        (root / "dist").mkdir()
        (root / "dist" / filename).symlink_to(retained)
    else:
        (root / "dist").mkdir()
        (root / "dist").chmod(0o777)
    with pytest.raises(expected):
        write(filename, {"synthetic": True})
    assert retained.read_bytes() == b"retained"


def test_cache_performance_seed_tracks_current_schema_and_never_clobbers(tmp_path, monkeypatch):
    from yorunge import api
    from yorunge.adapters.state import open_store
    from yorunge.adapters.state_schema import MIGRATIONS

    root = tmp_path / "synthetic-cache"
    fixture = Path(__file__).parents[1] / "fixtures/seed_capability_cache.py"
    seed = runpy.run_path(str(fixture))["seed"]
    seed(root, Path(__file__).parents[2] / "examples/profile.toml")
    with open_store(root) as store:
        assert store.verify().store_schema_version == len(MIGRATIONS)
        assert store.connection.execute("SELECT count(*) FROM capability_cache").fetchone() == (
            1024,
        )
    monkeypatch.setattr(
        api, "query_capabilities", lambda **kwargs: pytest.fail("existing seed mutated")
    )
    with pytest.raises(ValueError, match="existing data is preserved"):
        seed(root, Path(__file__).parents[2] / "examples/profile.toml")
