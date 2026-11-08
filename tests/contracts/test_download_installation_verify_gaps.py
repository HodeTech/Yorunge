"""Reviewer B (R2): survivors of a mutation run of scripts/download_installation.py."""

import base64
import copy
import json
import runpy
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.contracts.test_download_evidence import proof, row

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.usefixtures("evidence_publication_context")


def smoke(tmp_path, monkeypatch, measure):
    """verify() with synthetic parts: ``measure`` stands for the harness sample."""
    helper = runpy.run_path(str(ROOT / "scripts/download_installation.py"))
    namespace = helper["verify"].__globals__
    root = tmp_path.resolve()
    (root / "docs/research").mkdir(parents=True)
    (root / "dist").mkdir()
    synthetic = proof()

    def run(command, **kwargs):
        if command[0] == "git":
            return SimpleNamespace(stdout="a" * 40)
        kwargs["stdout"].write(json.dumps(synthetic["wheel_metadata_sha256"]).encode())
        return SimpleNamespace(returncode=0)

    def surface(*arguments):
        run_directory = arguments[3]
        (run_directory / "measured-server").mkdir(parents=True)
        (run_directory / "client-stdout.json").write_bytes(b'{"console":"output"}\n')
        (run_directory / "client-stderr.txt").write_bytes(b"")
        (run_directory / "measured-server/stdout.json").write_bytes(b'{"server":"account"}\n')

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setitem(
        namespace["EVIDENCE"], "source", lambda root: copy.deepcopy(synthetic["source_before"])
    )
    monkeypatch.setitem(
        namespace["STREAM"], "locked_runtime", lambda root: synthetic["locked_runtime"]
    )
    monkeypatch.setitem(
        namespace["HTTP"], "certificate", lambda *args, **kwargs: (root / "ca", root / "key")
    )
    monkeypatch.setitem(namespace, "surface", surface)
    monkeypatch.setitem(namespace["DRIVER"], "measure_one", measure)
    workspace = root / "workspace"
    arguments = (
        root / "env/bin/python",
        root / "env",
        root,
        root / "scratch",
        workspace,
        {},
        "wheel",
    )
    return helper, arguments, workspace, root


def test_a_passing_smoke_keeps_the_judged_row_and_a_private_workspace(tmp_path, monkeypatch):
    # mutants L127-L129 (the row written before it was judged), L66 (workspace mode)
    helper, arguments, workspace, root = smoke(tmp_path, monkeypatch, lambda *a: row("16", 1, 0))
    assert helper["verify"](*arguments) == "passed"
    kept = json.loads((workspace / "stdout.json").read_bytes())
    assert kept["passed"] is True and kept["label"] == "16"
    assert stat.S_IMODE(workspace.stat().st_mode) == 0o700


@pytest.mark.parametrize(
    "error", [KeyboardInterrupt(), SystemExit(143)], ids=["ctrl-c", "terminated"]
)
def test_an_interrupted_smoke_keeps_its_originals_like_a_failed_one(tmp_path, monkeypatch, error):
    # mutant L140 (`except BaseException` -> Exception): a cancelled CI step must retain too
    def measured(*arguments):
        raise error

    helper, arguments, workspace, root = smoke(tmp_path, monkeypatch, measured)
    with pytest.raises(type(error)) as raised:
        helper["verify"](*arguments)
    assert raised.value is error
    marker = json.loads((workspace / "controller-error.json").read_bytes())
    assert marker == {"outcome": "incomplete_installation_download", "stage": "measurement"}
    rejected = json.loads((root / "dist/installation-download-wheel-rejected.json").read_bytes())
    names = {item["name"]: base64.b64decode(item["content_base64"]) for item in rejected["files"]}
    assert names["16-2/client-stdout.json"] == b'{"console":"output"}\n'
    assert json.loads(names["controller-error.json"]) == marker
