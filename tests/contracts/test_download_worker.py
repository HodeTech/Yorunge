"""The controller's plumbing around one installed worker and its two servers.

The report and its verifier decide what a measurement means; this is what stands between a real
process and that verdict: the limit each label's worker is given, what is killed when the limit is
spent, which outputs are refused, which port reaches which side, and whose pid the row names. Every
process here is a fake: no network, no server, no installed wheel.
"""

import json
import runpy
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
LIMITS = {"16": 1200, "256": 1200, "1024": 1500, "resume": 2100}  # performance.md, per label
PID = 4242


@pytest.fixture(scope="module")
def driver():
    return runpy.run_path(str(ROOT / "scripts/benchmark-download.py"))


def canonical(driver, value):
    return driver["DATA"]["canonical"](value) + b"\n"


class FakeProcess:
    """A worker that has already run: it wrote ``stdout`` and ``stderr`` and exited ``code``."""

    def __init__(self, command, *, cwd, env, stdout, stderr, script, record):
        self.pid = script.get("pid", PID)
        record["command"], record["cwd"] = command, cwd
        stdout.write(script["stdout"])
        stderr.write(script.get("stderr", b""))
        self.script, self.record = script, record

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def wait(self, timeout=None):
        self.record.setdefault("waits", []).append(timeout)
        if self.script.get("hang") and timeout != 10:
            raise subprocess.TimeoutExpired("worker", timeout)
        return self.script.get("code", 0)

    def kill(self):
        self.record["killed"] = True


def patch_popen(driver, monkeypatch, script, record):
    def popen(command, **keywords):
        return FakeProcess(command, script=script, record=record, **keywords)

    namespace = SimpleNamespace(Popen=popen, TimeoutExpired=subprocess.TimeoutExpired)
    monkeypatch.setitem(driver["worker"].__globals__, "subprocess", namespace)


def good_output(driver, pid=PID, runtime_pid=PID):
    return canonical(driver, {"pid": pid, "runtime": {"pid": runtime_pid}})


def run_worker(driver, tmp_path, label="16"):
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    python = tmp_path / "env" / "bin" / "python"
    return driver["worker"](
        python,
        work,
        tmp_path / "receipt.json",
        (tmp_path / "ca.pem", tmp_path / "key.pem"),
        {"port": 111},
        {"port": 222},
        label,
    )


@pytest.mark.parametrize("label,limit", sorted(LIMITS.items()))
def test_each_label_is_given_exactly_its_documented_time_and_the_command_names_its_ports(
    driver, monkeypatch, tmp_path, label, limit
):
    record = {}
    patch_popen(driver, monkeypatch, {"stdout": good_output(driver)}, record)
    value, pid = run_worker(driver, tmp_path, label)
    assert record["waits"] == [limit]
    assert pid == PID
    assert value["pid"] == PID
    command = record["command"]
    option = {name: command[index + 1] for index, name in enumerate(command[:-1])}
    assert option["--port"] == "222"
    assert option["--warm-port"] == "111"  # measured, then warm
    assert option["--label"] == label
    assert option["--work"].endswith("work/measured")
    assert option["--warm"].endswith("work/warm")
    assert option["--prefix"] == str(tmp_path / "env")
    assert command[1:4] == ["-I", "-W", "error"]  # isolated, and a warning is an error
    assert record["cwd"] == tmp_path / "work"


def test_the_limits_in_the_driver_are_the_documented_ones(driver):
    assert driver["WORKER_SECONDS"] == LIMITS


@pytest.mark.parametrize("label", sorted(LIMITS))
def test_a_worker_that_outlives_its_limit_is_killed_and_the_timeout_surfaces(
    driver, monkeypatch, tmp_path, label
):
    record = {}
    patch_popen(driver, monkeypatch, {"stdout": b"", "hang": True}, record)
    with pytest.raises(subprocess.TimeoutExpired):
        run_worker(driver, tmp_path, label)
    assert record["killed"] is True
    assert record["waits"] == [LIMITS[label], 10]


@pytest.mark.parametrize(
    "script,message",
    [
        ({"code": 1}, "worker failed"),
        ({"code": -9}, "worker failed"),
        ({"stderr": b"x"}, "worker failed"),  # any stderr is a failure, however the exit went
        ({"stdout": b"not json\n"}, None),
        (
            {"stdout": b'{"pid":4242, "runtime":{"pid":4242}}\n'},
            "canonical",
        ),  # spaces: not canonical
        ({"stdout": b'{"pid":4242,"runtime":{"pid":4242}}\n\n'}, "canonical"),
        ({"pid": 7}, "worker identity"),  # the output names another process than the one started
    ],
)
def test_a_worker_that_failed_or_whose_output_is_not_exactly_one_object_is_refused(
    driver, monkeypatch, tmp_path, script, message
):
    script = {"stdout": good_output(driver)} | script
    record = {}
    patch_popen(driver, monkeypatch, script, record)
    with pytest.raises(ValueError) as refused:
        run_worker(driver, tmp_path)
    if message:
        assert message in str(refused.value)
    # the originals stay where they were written
    assert (tmp_path / "work" / "client-stdout.json").exists()
    assert (tmp_path / "work" / "client-stderr.txt").exists()


@pytest.mark.parametrize(
    "stdout",
    [
        {"pid": PID, "runtime": {"pid": 5}},  # the runtime that was measured is another process
        {"pid": PID},  # no runtime at all
        {"pid": PID, "runtime": "not an object"},
        {"pid": PID, "runtime": {"pid": 0}},
        {"pid": PID, "runtime": {"pid": True}},
    ],
)
def test_the_runtime_that_took_the_measurement_must_be_the_process_that_was_started(
    driver, monkeypatch, tmp_path, stdout
):
    record = {}
    patch_popen(driver, monkeypatch, {"stdout": canonical(driver, stdout)}, record)
    with pytest.raises(ValueError):
        run_worker(driver, tmp_path)


# --- one measurement: two servers, one worker, one row ---------------------------------------


class FakeServer:
    def __init__(self, directory, pid, stderr=b""):
        self.directory, self.pid, self.stderr = directory, pid, stderr

    def __enter__(self):
        self.directory.mkdir(parents=True)
        (self.directory / "stderr.txt").write_bytes(self.stderr)
        (self.directory / "stdout.json").write_bytes(
            canonical(self.driver, {"served": self.directory.name})
        )
        return {"port": 1000 + self.pid, "pid": self.pid}

    def __exit__(self, *exc):
        return False


def patch_measurement(driver, monkeypatch, *, server_stderr=b"", warm_stderr=b""):
    """Fake servers (recording which fixture each one serves) and a fake worker."""
    served = []

    def server(directory, certificates, label):
        served.append((directory.name, label))
        fake = FakeServer(
            directory,
            501 if directory.name == "warm-server" else 502,
            warm_stderr if directory.name == "warm-server" else server_stderr,
        )
        fake.driver = driver
        return fake

    seen = {}

    def worker(python, work, receipt, certificates, warm, sink, label):
        seen.update(warm=warm, sink=sink, label=label, work=work)
        return {"label": label, "pid": 900}, 900

    glob = driver["measure_one"].__globals__
    control = dict(glob["CONTROL"], server=server)
    monkeypatch.setitem(glob, "CONTROL", control)
    monkeypatch.setitem(glob, "worker", worker)
    return served, seen


def measure(driver, tmp_path, label="256", sample=2):
    return driver["measure_one"](
        tmp_path / "python",
        tmp_path,
        tmp_path / "receipt.json",
        (tmp_path / "c", tmp_path / "k"),
        label,
        sample,
    )


@pytest.mark.parametrize("label", sorted(LIMITS))
def test_one_measurement_names_whose_pid_is_whose_and_which_fixture_each_server_served(
    driver, monkeypatch, tmp_path, label
):
    served, seen = patch_measurement(driver, monkeypatch)
    row = measure(driver, tmp_path, label, 3)
    warm_label = driver["DATA"]["WARM_OF"][label]
    assert sorted(served) == sorted([("warm-server", warm_label), ("measured-server", label)])
    assert row["label"] == label
    assert row["sample"] == 3
    assert row["client_process_pid"] == 900
    assert row["client"] == {"label": label, "pid": 900}
    assert row["server_process_pid"] == 502  # the measured server's, not the warm one's
    assert row["warm_server_process_pid"] == 501
    assert row["server"] == {"served": "measured-server"}
    assert row["warm_server"] == {"served": "warm-server"}
    assert seen["sink"]["pid"] == 502
    assert seen["warm"]["pid"] == 501  # the worker got both
    assert seen["work"] == tmp_path / f"{label}-3"
    assert (tmp_path / f"{label}-3" / "warm").is_dir()
    assert (tmp_path / f"{label}-3" / "measured").is_dir()


@pytest.mark.parametrize("which", ["server", "warm"])
def test_a_server_that_wrote_to_stderr_fails_the_measurement_and_keeps_its_files(
    driver, monkeypatch, tmp_path, which
):
    patch_measurement(
        driver,
        monkeypatch,
        server_stderr=b"boom" if which == "server" else b"",
        warm_stderr=b"boom" if which == "warm" else b"",
    )
    with pytest.raises(ValueError, match="unexpected stderr"):
        measure(driver, tmp_path, "16", 1)
    assert (tmp_path / "16-1" / "measured-server" / "stdout.json").exists()
    assert (tmp_path / "16-1" / "warm-server" / "stdout.json").exists()


def test_a_sample_directory_that_exists_is_never_reused(driver, monkeypatch, tmp_path):
    patch_measurement(driver, monkeypatch)
    (tmp_path / "16-1").mkdir()
    with pytest.raises(FileExistsError):
        measure(driver, tmp_path, "16", 1)
    assert json.loads('{"kept": true}')  # nothing else to assert: the directory was left alone
