"""Installed smoke failures retain metadata/measurement bytes outside temporary venvs."""

import copy
import json
import runpy
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.fixtures.upload_report import row as row_vector

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.usefixtures("evidence_publication_context")


@pytest.mark.parametrize(
    "failure", [None, "metadata_exit", "metadata_utf8", "measure", "source_changed"]
)
def test_installed_smoke_source_and_metadata_failures_cannot_be_hidden(
    tmp_path, monkeypatch, failure
):
    helper = runpy.run_path(str(ROOT / "scripts/upload_installation.py"))
    namespace = helper["verify"].__globals__
    root = tmp_path.resolve()
    (root / "docs/research").mkdir(parents=True)
    (root / "dist").mkdir()
    vector = root / helper["EVIDENCE"]["VECTOR_PATH"]
    vector.parent.mkdir(parents=True)
    vector.write_bytes((ROOT / helper["EVIDENCE"]["VECTOR_PATH"]).read_bytes())
    before = {
        "commit": "a" * 40,
        "source_sha256": {
            "src/yorunge/__init__.py": "1" * 64,
            "src/yorunge/py.typed": "2" * 64,
            helper["EVIDENCE"]["VECTOR_PATH"]: "3" * 64,
        },
    }
    calls = []

    def source(root):
        calls.append("source")
        value = copy.deepcopy(before)
        if failure == "source_changed" and len(calls) > 1:
            value["source_sha256"]["src/yorunge/__init__.py"] = "9" * 64
        return value

    metadata = {name: "5" * 64 for name in ("METADATA", "WHEEL", "entry_points.txt")}

    def run(command, **kwargs):
        if command[0] == "git":
            return SimpleNamespace(stdout="a" * 40)
        assert command[1:3] == ["-I", "-c"]
        kwargs["stdout"].write(
            b"\xffbroken" if failure == "metadata_utf8" else json.dumps(metadata).encode()
        )
        if failure == "metadata_exit":
            kwargs["stderr"].write(b"metadata failed")
            raise subprocess.CalledProcessError(1, command)
        return SimpleNamespace(returncode=0)

    def measured(*args):
        if failure == "measure":
            raise ValueError("synthetic worker failed")
        return row_vector("16", 1, 0)

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setitem(namespace["EVIDENCE"], "source", source)
    monkeypatch.setitem(
        namespace["DRIVER"]["STREAM"],
        "locked_runtime",
        lambda root: {"yorunge": "0.1.0.dev0", "httpx": "0.28.1"},
    )
    monkeypatch.setitem(
        namespace["DRIVER"]["HTTP"],
        "certificate",
        lambda *args, **kwargs: (root / "ca", root / "key"),
    )
    monkeypatch.setitem(namespace["DRIVER"], "measure_one", measured)
    arguments = (root / "python", root / "env", root, root, root / "workspace", {}, "wheel")
    if failure is None:
        assert helper["verify"](*arguments) == "passed"
        assert not (root / "dist/installation-upload-wheel-rejected.json").exists()
    else:
        with pytest.raises((ValueError, subprocess.CalledProcessError)):
            helper["verify"](*arguments)
        rejected = helper["CHECKS"]["decode"](
            (root / "dist/installation-upload-wheel-rejected.json").read_bytes()
        )
        assert helper["DRIVER"]["DIAGNOSTIC"]["summarize"](rejected)["accepted"] is False
        assert {"metadata-stdout.json", "metadata-stderr.txt"} <= {
            file["name"] for file in rejected["files"]
        }
        if failure == "metadata_utf8":
            assert (root / "workspace/metadata-stdout.json").read_bytes() == b"\xffbroken"
            assert not any((root / "docs/research").iterdir())
        else:
            assert helper["CHECKS"]["verify"](root) == 1
    assert (root / "workspace/metadata-stdout.json").is_file()


def test_ci_installation_diagnostics_require_real_run_identity_before_start(tmp_path):
    helper = runpy.run_path(str(ROOT / "scripts/upload_installation.py"))
    assert helper["run_url"]({}) is None
    assert (
        helper["run_url"](
            {
                "GITHUB_ACTIONS": "true",
                "GITHUB_REPOSITORY": "HodeTech/Yorunge",
                "GITHUB_RUN_ID": "123",
            }
        )
        == "https://github.com/HodeTech/Yorunge/actions/runs/123"
    )
    environment = {"GITHUB_ACTIONS": "true"}
    arguments = (
        tmp_path / "python",
        tmp_path,
        tmp_path,
        tmp_path,
        tmp_path / "workspace",
        environment,
        "wheel",
    )
    with pytest.raises(ValueError):
        helper["verify"](*arguments)
    assert not (tmp_path / "workspace").exists()
