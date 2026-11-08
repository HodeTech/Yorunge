"""The download controller's evidence hooks: run URL, dist-only report, retention and archiving.

Everything runs against a temporary root (its ``dist``, its evidence archive and a stubbed Git
commit) and synthetic runs; the real archive is never touched. The runs are not observed
performance.
"""

import base64
import gzip
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from tests.contracts.test_download_evidence import (
    LABELS,
    controller_args,
    patch_controller,
    scoped_runs,
)

pytestmark = pytest.mark.usefixtures("evidence_publication_context")

ROOT = Path(__file__).resolve().parents[2]
RUN_URL = "https://github.com/HodeTech/Yorunge/actions/runs/123"
MARKER = b'{"outcome":"incomplete_download_measurement"}\n'


@pytest.fixture(scope="module")
def driver():
    return runpy.run_path(str(ROOT / "scripts/benchmark-download.py"))


def write_run(workspace, label="16", sample=1):
    """What a worker and its two servers had left when the run stopped."""
    base = workspace / f"{label}-{sample}"
    files = {
        "client-stdout.json": b'{"pid":101}\n',
        "client-stderr.txt": b"worker output\n",
    }
    for server in ("warm-server", "measured-server"):
        files |= {
            f"{server}/stdout.json": b'{"label":"16"}\n',
            f"{server}/stderr.txt": b"",
            f"{server}/ready.json": b'{"pid":301,"port":9}\n',
        }
    for name, raw in files.items():
        (base / name).parent.mkdir(parents=True, exist_ok=True)
        (base / name).write_bytes(raw)
    return {f"{label}-{sample}/{name}": raw for name, raw in files.items()}


def interrupt(driver, monkeypatch, tmp_path, error):
    """Patch the controller so that its measurements stop with ``error`` after one run's files."""
    globals_ = patch_controller(driver, monkeypatch, tmp_path, [])
    written = {}

    def stop(python, workspace, *rest):
        written.update(write_run(workspace))
        raise error

    monkeypatch.setitem(globals_, "run_measurements", stop)
    return written


def finish(driver, monkeypatch, tmp_path, runs):
    patch_controller(driver, monkeypatch, tmp_path, runs)
    monkeypatch.setattr(os, "getpid", lambda: 999)


def retained(path):
    value = json.loads(path.read_bytes())
    return value, {
        item["name"]: base64.b64decode(item["content_base64"], validate=True)
        for item in value["files"]
    }


@pytest.mark.parametrize(
    "error",
    [
        ValueError("synthetic interrupted worker"),
        OSError("synthetic"),
        KeyboardInterrupt(),
        SystemExit(143),
    ],
    ids=["value", "os", "interrupt", "terminated"],
)
def test_any_interruption_writes_the_marker_retains_the_originals_and_reraises(
    tmp_path, driver, monkeypatch, error
):
    written = interrupt(driver, monkeypatch, tmp_path, error)
    args = controller_args(tmp_path, list(LABELS), 3, run_url=RUN_URL)
    with pytest.raises(type(error)) as raised:
        driver["check"](args)
    assert raised.value is error  # the cause is what the caller sees, not a retention detail
    assert (args.workspace / "controller-error.json").read_bytes() == MARKER
    assert not args.output.exists()
    value, files = retained(tmp_path / "dist/report-rejected.json")
    assert value["report_kind"] == "rejected_download_evidence_v1"
    assert value["rejection_reason"] == "interrupted_measurement"
    assert value["source_commit"] == "a" * 40
    assert value["run_url"] == RUN_URL
    # The marker is written before the originals are retained, and nothing else is invented.
    assert list(files) == [
        "source-manifest.json",
        "source-before.json",
        "controller-error.json",
        *written,
    ]
    assert files["controller-error.json"] == MARKER
    assert {name: files[name] for name in written} == written
    for name in ("source-manifest.json", "source-before.json"):
        assert files[name] == (args.workspace / name).read_bytes()
    assert driver["CHECKS"]["verify"](tmp_path) == 1
    archived = tmp_path / "docs/research/raw/report-rejected.json.gz"
    assert (
        gzip.decompress(archived.read_bytes())
        == (tmp_path / "dist/report-rejected.json").read_bytes()
    )
    with pytest.raises(ValueError, match="new path"):  # nothing is reused or overwritten
        driver["check"](args)


def test_a_local_interruption_has_no_run_url(tmp_path, driver, monkeypatch):
    interrupt(driver, monkeypatch, tmp_path, ValueError("synthetic interrupted worker"))
    args = controller_args(tmp_path, list(LABELS), 3)
    with pytest.raises(ValueError, match="synthetic interrupted worker"):
        driver["check"](args)
    assert json.loads((tmp_path / "dist/report-rejected.json").read_bytes())["run_url"] is None


def test_a_smoke_subset_that_stops_keeps_its_originals_in_the_workspace_only(
    tmp_path, driver, monkeypatch
):
    written = interrupt(driver, monkeypatch, tmp_path, ValueError("synthetic interrupted worker"))
    args = controller_args(tmp_path, ["16"], 1)
    with pytest.raises(ValueError, match="synthetic interrupted worker"):
        driver["check"](args)
    assert (args.workspace / "controller-error.json").read_bytes() == MARKER
    assert (args.workspace / "16-1/client-stdout.json").read_bytes() == written[
        "16-1/client-stdout.json"
    ]
    assert list((tmp_path / "dist").iterdir()) == []
    assert list((tmp_path / "docs/research").iterdir()) == []


def test_a_failed_retention_replaces_the_cause_but_never_the_originals(
    tmp_path, driver, monkeypatch
):
    """With no declared privacy context the gate refuses: the report stays private in dist."""
    written = interrupt(driver, monkeypatch, tmp_path, ValueError("synthetic interrupted worker"))
    monkeypatch.delenv("YORUNGE_EVIDENCE_CONTEXT")
    args = controller_args(tmp_path, list(LABELS), 3)
    with pytest.raises(ValueError, match="missing_context"):
        driver["check"](args)
    assert (args.workspace / "16-1/client-stderr.txt").read_bytes() == b"worker output\n"
    assert (tmp_path / "dist/report-rejected.json").exists()
    assert list((tmp_path / "docs/research").iterdir()) == []
    assert written


def test_the_run_url_is_validated_before_anything_is_created(tmp_path, driver, monkeypatch):
    patch_controller(driver, monkeypatch, tmp_path, [])
    for url in (
        "",
        "http://github.com/HodeTech/Yorunge/actions/runs/123",
        "https://github.com/HodeTech/Yorunge/actions/runs/0",
        "https://github.com/HodeTech/Yorunge/actions/runs/123/",
        "https://example.com/HodeTech/Yorunge/actions/runs/123",
        "https://github.com/HodeTech/Yorunge/pull/123",
    ):
        args = controller_args(tmp_path, list(LABELS), 3, run_url=url)
        with pytest.raises(ValueError, match="invalid evidence digest or identifier"):
            driver["check"](args)
        assert not args.workspace.exists() and list((tmp_path / "dist").iterdir()) == []


@pytest.mark.parametrize(
    "output",
    ["report.json", "docs/report.json", "dist/nested/report.json", "other-dist/report.json"],
)
def test_the_report_must_be_created_directly_in_the_roots_dist(
    tmp_path, driver, monkeypatch, output
):
    patch_controller(driver, monkeypatch, tmp_path, [])
    args = controller_args(tmp_path, list(LABELS), 3)
    args.output = tmp_path / output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError, match="directly in dist"):
        driver["check"](args)
    assert not args.workspace.exists() and not args.output.exists()


def test_the_name_is_checked_before_the_place(tmp_path, driver, monkeypatch):
    patch_controller(driver, monkeypatch, tmp_path, [])
    args = controller_args(tmp_path, list(LABELS), 3)
    args.output = tmp_path / "dist/Report.JSON"
    with pytest.raises(ValueError, match="canonical lowercase name"):
        driver["check"](args)
    assert not args.workspace.exists()


def test_the_commit_is_read_from_git_in_the_root_before_the_workspace_exists(
    tmp_path, driver, monkeypatch
):
    globals_ = patch_controller(driver, monkeypatch, tmp_path, [])
    calls = []

    def git(*args, **kwargs):
        calls.append((args, kwargs))
        raise subprocess.CalledProcessError(128, "git")

    monkeypatch.setattr(globals_["subprocess"], "run", git)
    args = controller_args(tmp_path, list(LABELS), 3)
    with pytest.raises(subprocess.CalledProcessError):
        driver["check"](args)
    (((command,), keywords),) = calls
    assert command == ["git", "rev-parse", "HEAD"]
    assert keywords["cwd"] == tmp_path and keywords["check"] is True and keywords["timeout"] == 10
    assert not args.workspace.exists()  # no workspace, so nothing to retain


def test_a_failed_complete_measurement_is_archived_as_it_is(tmp_path, driver, monkeypatch, capsys):
    runs = scoped_runs(list(LABELS), 3)
    runs[2]["client"]["public"]["sha256"] = "0" * 64  # the product wrote other bytes
    finish(driver, monkeypatch, tmp_path, runs)
    args = controller_args(tmp_path, list(LABELS), 3)
    assert driver["check"](args) == 1
    printed = json.loads(capsys.readouterr().out)
    assert (printed["passed"], printed["accepted"], printed["partial"]) == (False, False, False)
    written = args.output.read_bytes()
    archive = tmp_path / "docs/research"
    assert gzip.decompress((archive / "raw/report.json.gz").read_bytes()) == written
    assert driver["CHECKS"]["verify"](tmp_path) == 1
    entry = json.loads((archive / "evidence-manifest.json").read_bytes())["entries"][0]
    assert entry["name"] == "report.json" and entry["summary"] == {
        "source_commit": "a" * 40,
        "diagnostic_only": False,
        **printed,
    }
    assert not (tmp_path / "dist/report-rejected.json").exists()  # it ran to the end


def test_a_report_the_archive_gate_refuses_stays_in_dist_and_the_run_fails(
    tmp_path, driver, monkeypatch
):
    runs = scoped_runs(list(LABELS), 3)
    runs[2]["client"]["public"]["sha256"] = "0" * 64
    finish(driver, monkeypatch, tmp_path, runs)
    args = controller_args(tmp_path, list(LABELS), 3)
    args.cpu = "/Users/synthetic-private-operator/cpu"  # a declared personal literal
    with pytest.raises(ValueError, match="personal_provenance"):
        driver["check"](args)
    assert args.output.exists()
    assert list((tmp_path / "docs/research").iterdir()) == []


def test_an_accepted_report_is_written_and_not_archived(tmp_path, driver, monkeypatch, capsys):
    finish(driver, monkeypatch, tmp_path, scoped_runs(list(LABELS), 3))
    args = controller_args(tmp_path, list(LABELS), 3)
    assert driver["check"](args) == 0
    assert json.loads(capsys.readouterr().out)["accepted"] is True
    assert args.output.is_file()
    assert list((tmp_path / "docs/research").iterdir()) == []


@pytest.mark.parametrize(
    ("labels", "samples", "passed"),
    [(["16", "resume"], 1, False), (["16", "256"], 2, True), (["16", "256", "1024"], 1, True)],
)
def test_a_smoke_subset_is_reported_and_never_reaches_the_archive(
    tmp_path, driver, monkeypatch, capsys, labels, samples, passed
):
    finish(driver, monkeypatch, tmp_path, scoped_runs(labels, samples))
    args = controller_args(tmp_path, labels, samples)
    assert driver["check"](args) == 1
    printed = json.loads(capsys.readouterr().out)
    assert (printed["partial"], printed["passed"], printed["accepted"]) == (True, passed, False)
    assert args.output.is_file()
    assert list((tmp_path / "docs/research").iterdir()) == []


# --- the command line ----------------------------------------------------------------------------


def invoke(driver, monkeypatch, tmp_path, *extra):
    args = controller_args(tmp_path, list(LABELS), 3)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark-download.py",
            "--python",
            str(args.python),
            "--wheel",
            str(args.wheel),
            "--workspace",
            str(args.workspace),
            "--output",
            str(args.output),
            "--cpu",
            "synthetic",
            "--disk-type",
            "synthetic",
            *extra,
        ],
    )
    with pytest.raises(SystemExit) as stop:
        driver["main"]()
    return stop.value.code, args


def test_the_command_takes_a_run_url_and_retains_an_interrupted_run_under_it(
    tmp_path, driver, monkeypatch, capsys
):
    interrupt(driver, monkeypatch, tmp_path, ValueError("synthetic interrupted worker"))
    code, _ = invoke(driver, monkeypatch, tmp_path, "--run-url", RUN_URL)
    assert code == 1
    assert "Download measurement failed: synthetic interrupted worker" in capsys.readouterr().err
    assert json.loads((tmp_path / "dist/report-rejected.json").read_bytes())["run_url"] == RUN_URL


def test_the_command_refuses_a_bad_run_url_before_it_creates_anything(
    tmp_path, driver, monkeypatch, capsys
):
    patch_controller(driver, monkeypatch, tmp_path, [])
    code, args = invoke(driver, monkeypatch, tmp_path, "--run-url", "https://example.com/runs/1")
    assert code == 1 and "invalid evidence digest or identifier" in capsys.readouterr().err
    assert not args.workspace.exists() and list((tmp_path / "dist").iterdir()) == []


def test_the_command_documents_the_run_url(driver, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["benchmark-download.py", "--help"])
    with pytest.raises(SystemExit) as stop:
        driver["main"]()
    assert stop.value.code == 0
    assert "--run-url" in capsys.readouterr().out


def test_the_wrappers_find_the_download_retention_and_the_shared_helpers_on_the_controller(driver):
    diagnostic = driver["DIAGNOSTIC"]
    assert diagnostic["MAX_FILE"] == 2_097_152
    assert diagnostic["allowed"]("16-1/client-stdout.json") is True
    assert diagnostic["allowed"]("capacity-1/client-stdout.json") is False
    assert driver["CHECKS"] is driver["EVIDENCE"]["CHECKS"]
    assert driver["STREAM"] is driver["EVIDENCE"]["STREAM"]
    for name in ("HTTP", "CONTROL", "WHEEL", "DATA"):
        assert name in driver
