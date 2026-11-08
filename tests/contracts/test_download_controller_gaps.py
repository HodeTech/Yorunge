"""Reviewer B (R2): survivors of a systematic mutation run of scripts/benchmark-download.py."""

import copy
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.contracts.test_download_controller import driver as driver  # noqa: F401
from tests.contracts.test_download_evidence import (
    LABELS,
    controller_args,
    patch_controller,
    proof,
    scoped_runs,
)

pytestmark = pytest.mark.usefixtures("evidence_publication_context")

ROOT = Path(__file__).resolve().parents[2]


def changing(driver, monkeypatch, tmp_path, *, source=False, wheel=False):
    """A controller whose source map / wheel digest differ once the measurements have run."""
    runs = scoped_runs(list(LABELS), 3)
    for item in runs:
        item["passed"] = None
    globals_ = patch_controller(driver, monkeypatch, tmp_path, runs)
    monkeypatch.setattr(os, "getpid", lambda: 999)
    state = {"measured": False}
    base = proof()

    def measure(*args):
        state["measured"] = True
        return runs

    def source_map(root):
        value = copy.deepcopy(base["source_before"])
        if source and state["measured"]:
            value["source_sha256"]["scripts/download_evidence.py"] = "9" * 64
        return value

    def snapshot(*args):
        return {
            "sha256": "8" * 64 if wheel and state["measured"] else base["wheel_before"],
            "product_sha256": base["wheel_product_sha256"],
            "metadata_sha256": base["wheel_metadata_sha256"],
        }

    monkeypatch.setitem(globals_, "run_measurements", measure)
    monkeypatch.setitem(globals_["EVIDENCE"], "source", source_map)
    monkeypatch.setitem(globals_["WHEEL"], "snapshot", snapshot)
    return controller_args(tmp_path, list(LABELS), 3)


@pytest.mark.parametrize("what", ["source", "wheel"])
def test_a_change_during_the_measurements_is_recorded_and_fails_the_report(
    tmp_path, driver, monkeypatch, capsys, what
):
    # mutants L280/L282 of benchmark-download.py: the "after" snapshots must be taken after the runs
    args = changing(driver, monkeypatch, tmp_path, **{what: True})
    assert driver["check"](args) == 1
    written = driver["CHECKS"]["decode"](args.output.read_bytes())
    proof_ = written["provenance"]
    assert written["passed"] is False and written["accepted"] is False
    if what == "source":
        key = "scripts/download_evidence.py"
        assert proof_["source_before"]["source_sha256"][key] == "3" * 64  # the first snapshot
        assert proof_["source_after"]["source_sha256"][key] == "9" * 64  # the one after the runs
    else:
        assert (proof_["wheel_before"], proof_["wheel_after"]) == ("4" * 64, "8" * 64)
    printed = json.loads(capsys.readouterr().out)
    assert printed["passed"] is False
    # a failed complete measurement is evidence: archived as it is
    assert (tmp_path / "docs/research/raw/report.json.gz").is_file()


def run_script(*arguments):
    return subprocess.run(
        [sys.executable, "-I", str(ROOT / "scripts/benchmark-download.py"), *arguments],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_the_controller_script_runs_as_a_process_and_documents_itself():
    # mutant L358 (`if __name__ == "__main__"` forced False): a script that silently does nothing
    result = run_script("--help")
    assert result.returncode == 0 and "--labels" in result.stdout and "--run-url" in result.stdout


def test_the_controller_process_ends_nonzero_with_a_closed_message_on_a_refused_run(tmp_path):
    # mutants L358/L359: the exit status of the script is its contract
    result = run_script(
        "--python",
        str(tmp_path / "no-python"),
        "--wheel",
        str(tmp_path / "no.whl"),
        "--workspace",
        str(tmp_path / "w"),
        "--output",
        str(tmp_path / "o.json"),
        "--cpu",
        "c",
        "--disk-type",
        "d",
    )
    assert result.returncode == 1
    assert "Download measurement failed" in result.stderr and "Traceback" not in result.stderr
    assert not (tmp_path / "w").exists() and not (tmp_path / "o.json").exists()


# --- the worker is killed on every way out (BaseException), and before it is reaped
# mutants L118 (`except BaseException` -> Exception) and L119 (wait before kill)


class Hanging:
    """A worker that is still running: it only dies from ``kill`` (unlike FakeProcess)."""

    def __init__(self, command, *, cwd, env, stdout, stderr, record, behaviour):
        self.pid, self.record, self.behaviour = 4242, record, behaviour

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def wait(self, timeout=None):
        self.record.setdefault("waits", []).append(timeout)
        if self.record.get("killed"):
            return -9
        if timeout != 10 and self.behaviour is not None:
            raise self.behaviour  # Ctrl-C, SIGTERM -> SystemExit, or a spent limit
        raise subprocess.TimeoutExpired("worker", timeout)  # alive: neither exit nor limit yet

    def kill(self):
        self.record["killed"] = True


@pytest.mark.parametrize(
    "behaviour",
    [KeyboardInterrupt(), SystemExit(143), subprocess.TimeoutExpired("worker", 1200)],
    ids=["ctrl-c", "terminated", "limit"],
)
def test_the_running_worker_is_killed_before_it_is_reaped_on_every_way_out(
    driver, monkeypatch, tmp_path, behaviour
):
    from types import SimpleNamespace

    record = {}

    def popen(command, **keywords):
        return Hanging(command, record=record, behaviour=behaviour, **keywords)

    monkeypatch.setitem(
        driver["worker"].__globals__,
        "subprocess",
        SimpleNamespace(Popen=popen, TimeoutExpired=subprocess.TimeoutExpired),
    )
    work = tmp_path / "work"
    work.mkdir()
    with pytest.raises(type(behaviour)):
        driver["worker"](
            tmp_path / "env/bin/python",
            work,
            tmp_path / "receipt.json",
            (tmp_path / "ca.pem", tmp_path / "key.pem"),
            {"port": 1},
            {"port": 2},
            "16",
        )
    assert record["killed"] is True
    assert record["waits"] == [1200, 10]  # the reaping wait came after the kill (else it times out)


def test_run_measurements_is_label_major_and_passes_its_arguments_in_order(driver, monkeypatch):
    seen = []

    def measure_one(*arguments):
        seen.append(arguments)
        return {"label": arguments[4], "sample": arguments[5]}

    monkeypatch.setitem(driver["run_measurements"].__globals__, "measure_one", measure_one)
    python, workspace, receipt, certificates = (
        Path("py"),
        Path("ws"),
        Path("rc"),
        (Path("a"), Path("b")),
    )
    rows = driver["run_measurements"](python, workspace, receipt, certificates, ["16", "resume"], 2)
    assert seen == [
        (python, workspace, receipt, certificates, label, sample)
        for label in ("16", "resume")
        for sample in (1, 2)
    ]  # mutant L193: first two arguments swapped
    assert [(row["label"], row["sample"]) for row in rows] == [
        ("16", 1),
        ("16", 2),
        ("resume", 1),
        ("resume", 2),
    ]


# --- termination_signals: the second signal and an ignored hangup


def test_a_second_signal_during_the_cleanup_is_ignored_until_the_handlers_come_back(driver):
    import signal
    import time

    before = {n: signal.getsignal(n) for n in (signal.SIGTERM, signal.SIGHUP)}
    seen = {}
    with pytest.raises(SystemExit):
        with driver["termination_signals"]():
            try:
                os.kill(os.getpid(), signal.SIGTERM)
                time.sleep(1)
            except SystemExit:
                seen["term"] = signal.getsignal(signal.SIGTERM)
                seen["hup"] = signal.getsignal(signal.SIGHUP)
                raise
    assert seen == {"term": signal.SIG_IGN, "hup": signal.SIG_IGN}  # mutant L56
    assert {n: signal.getsignal(n) for n in before} == before


def test_a_hangup_that_was_ignored_on_entry_stays_ignored(driver):
    # `nohup controller ... &`: SIGHUP is SIG_IGN on entry and the user chose that; the handler
    # must not overwrite it, or a hangup would kill the measurement (exit 129, marker).
    import signal

    original = signal.signal(signal.SIGHUP, signal.SIG_IGN)
    try:
        with driver["termination_signals"]():
            inside = signal.getsignal(signal.SIGHUP)
        after = signal.getsignal(signal.SIGHUP)
    finally:
        signal.signal(signal.SIGHUP, original)
    assert after == signal.SIG_IGN  # restored either way
    assert inside == signal.SIG_IGN


# --- main(): every closed failure type; check(): both files are required


@pytest.mark.parametrize(
    "error",
    [
        OSError("os"),
        ValueError("value"),
        KeyError("key"),
        TypeError("type"),
        RecursionError("deep"),
        subprocess.TimeoutExpired("git", 1),
    ],
    ids=lambda error: type(error).__name__,
)
def test_every_closed_failure_type_of_the_command_ends_with_exit_one(
    driver, monkeypatch, capsys, error
):
    # mutants L345: one exception type dropped from the tuple
    def check(args):
        raise error

    monkeypatch.setitem(driver["main"].__globals__, "check", check)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark-download.py",
            "--python",
            "p",
            "--wheel",
            "w",
            "--workspace",
            "x",
            "--output",
            "o",
            "--cpu",
            "c",
            "--disk-type",
            "d",
        ],
    )
    with pytest.raises(SystemExit) as stopped:
        driver["main"]()
    assert stopped.value.code == 1
    assert "Download measurement failed" in capsys.readouterr().err


@pytest.mark.parametrize("missing", ["python", "wheel"])
def test_both_the_runtime_python_and_the_wheel_must_exist(tmp_path, driver, monkeypatch, missing):
    # mutants L248: Or -> And, either operand dropped
    root = tmp_path
    (root / "dist").mkdir()
    monkeypatch.setitem(driver["check"].__globals__, "ROOT", root)
    args = controller_args(tmp_path, list(LABELS), 3)
    present = tmp_path / "present"
    present.write_bytes(b"x")
    args.python = present if missing == "wheel" else tmp_path / "no-python"
    args.wheel = present if missing == "python" else tmp_path / "no.whl"
    with pytest.raises(ValueError, match="installed runtime Python and wheel required"):
        driver["check"](args)


# --- the command line, the sample bounds, the output bound, the private workspace

REQUIRED = ["--python", "--wheel", "--workspace", "--output", "--cpu", "--disk-type"]


@pytest.mark.parametrize("flag", REQUIRED)
def test_every_required_flag_of_the_controller_is_required(driver, monkeypatch, flag):
    # mutants L320-L325 (required=True -> False)
    values = dict(zip(REQUIRED, ["p", "w", "x", "o", "c", "d"], strict=True))
    line = ["benchmark-download.py"]
    for name, value in values.items():
        if name != flag:
            line += [name, value]
    monkeypatch.setitem(driver["main"].__globals__, "check", lambda args: 0)
    monkeypatch.setattr(sys, "argv", line)
    with pytest.raises(SystemExit) as stopped:
        driver["main"]()
    assert stopped.value.code == 2


@pytest.mark.parametrize("samples", [0, 4, -1, True, 2.0, "3"])
def test_the_sample_count_is_one_two_or_three_integers(driver, samples):
    # mutants L337
    with pytest.raises(ValueError):
        driver["chosen"](SimpleNamespace(labels=["16"], samples=samples))
    for good in (1, 2, 3):
        assert driver["chosen"](SimpleNamespace(labels=["16"], samples=good)) == (["16"], good)


@pytest.mark.parametrize("labels", [[], ["resume", "16"], ["16", "16"], ["7"]])
def test_the_labels_are_unique_known_and_canonically_ordered(driver, labels):
    with pytest.raises(ValueError):
        driver["chosen"](SimpleNamespace(labels=labels, samples=3))


def test_a_worker_output_is_bounded_at_one_mebibyte(tmp_path, driver):
    # mutants L70: the limit handed to read_bounded
    def canonical_of(size):
        body = driver["DATA"]["canonical"]({"pad": ""})
        filler = size - len(body) - 1  # the LF
        return driver["DATA"]["canonical"]({"pad": "x" * filler}) + b"\n"

    exact, over = tmp_path / "exact", tmp_path / "over"
    exact.write_bytes(canonical_of(1_048_576))
    over.write_bytes(canonical_of(1_048_577))
    assert len(driver["decode_output"](exact)["pad"]) > 1_000_000
    with pytest.raises(ValueError):
        driver["decode_output"](over)


def test_the_workspace_of_a_run_is_private(tmp_path, driver, monkeypatch):
    # mutant L263 (mode 0o700 -> 0o701): the workspace holds the TLS key of the run
    runs = scoped_runs(list(LABELS), 3)
    for item in runs:
        item["passed"] = None
    patch_controller(driver, monkeypatch, tmp_path, runs)
    monkeypatch.setattr(os, "getpid", lambda: 999)
    args = controller_args(tmp_path, list(LABELS), 3)
    driver["check"](args)
    import stat

    assert stat.S_IMODE(args.workspace.stat().st_mode) == 0o700
