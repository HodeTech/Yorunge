"""A download killed at every boundary of the closed order is finished by the next run.

For each scenario a child process runs the engine's side of a conforming exchange while every
boundary is announced (``download_files.step``). The test first records the boundaries, then
kills a fresh child at each of them with SIGKILL, looks at what the directory holds (only names
of the protocol, a target that is whole or absent, a stage that is a prefix of the data) and runs
the same command again in this process. The next run must finish without anyone deleting
anything: a target that is whole, no lock object, no stage, no sidecar, no temporary copy (the
one trace that may stay is the orphan sidecar of a publication that was cut after the stage went).
"""

import os
import re
import signal
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures import download_sink_driver as driver
from yorunge.adapters import download_sink
from yorunge.domain.download import download_names
from yorunge.domain.errors import YorungeError

REPOSITORY = Path(__file__).resolve().parents[2]
NAMES = download_names(driver.NAME)
PROTOCOL = {NAMES.lock, NAMES.stage, NAMES.sidecar, NAMES.sidecar_tmp}

SCENARIOS = {
    "fresh": ("fresh", None, {}),
    "resume": ("fresh", "stopped", {}),
    "publish": ("fresh", "unpublished", {}),
    "chunked": ("chunked", None, {}),
    "checkpoints": ("checkpoints", None, {}),
    "restart": ("restart", "stopped", {}),
    "discard": ("discard", "stopped", {}),
    "mismatch": ("fresh", "unpublished", {"SINK_EXPECTED": "00" * 32}),
    "no_resume": ("fresh", "stopped", {"SINK_NO_RESUME": "1"}),
    "stale_tmp": ("fresh", "stopped_with_tmp", {}),
    "overrun": ("fresh", "stopped_overrun", {}),
}


def child(directory, scenario, extra, *, kill=None, record=None):
    environment = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(REPOSITORY), *sys.path]),
        "SINK_DIRECTORY": str(directory),
        "SINK_SCENARIO": scenario,
        **extra,
    }
    if kill:
        environment["SINK_KILL"] = kill
    if record:
        Path(record).touch()  # made here: the child may run under a umask that forbids appending
        environment["SINK_RECORD"] = str(record)
    return subprocess.run(
        [sys.executable, "-c", "from tests.fixtures.download_sink_driver import main; main()"],
        env=environment,
        cwd=REPOSITORY,
        capture_output=True,
        timeout=60,
    )


def listing(directory):
    return sorted(p.name for p in Path(directory).iterdir())


def prepared(tmp_path, name, preparation):
    directory = tmp_path / name
    directory.mkdir()
    if preparation:
        driver.prepare(directory, preparation)
    return directory


def assert_only_the_protocols_own_traces(directory):
    names = set(listing(directory))
    assert names <= PROTOCOL | {driver.NAME}, names
    target = directory / driver.NAME
    if driver.NAME in names:  # a target is whole or it is not there
        assert target.read_bytes() == driver.DATA
        assert stat.S_IMODE(target.stat().st_mode) == 0o600
    stage = directory / NAMES.stage
    if NAMES.stage in names:
        assert driver.DATA.startswith(stage.read_bytes())  # what was written is a prefix
    for name in names & PROTOCOL:
        assert stat.S_IMODE((directory / name).stat().st_mode) == 0o600, name


@pytest.fixture(autouse=True)
def keep_checkpoint_interval(monkeypatch):
    monkeypatch.setattr(download_sink, "CHECKPOINT_BYTES", download_sink.CHECKPOINT_BYTES)


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_a_kill_at_every_boundary_is_finished_by_the_next_run(tmp_path, name):
    scenario, preparation, extra = SCENARIOS[name]
    record = tmp_path / "steps.txt"
    run = child(prepared(tmp_path, "recording", preparation), scenario, extra, record=record)
    assert run.returncode == 0, run.stderr.decode()[-500:]
    steps = record.read_text().split()
    assert len(steps) >= 10, steps  # the boundaries were announced
    problems = []
    for number, label in enumerate(steps):
        directory = prepared(tmp_path, f"kill-{number}", preparation)
        run = child(directory, scenario, extra, kill=label)
        if run.returncode != -signal.SIGKILL:
            problems.append((label, "was not killed", run.returncode, run.stderr[-200:]))
            continue
        try:
            assert_only_the_protocols_own_traces(directory)
            published = True
            try:
                driver.engine_run(directory)
            except YorungeError as error:
                assert error.code == "download_output_exists", error.code
                published = False
            target = directory / driver.NAME
            assert target.read_bytes() == driver.DATA
            if published:
                assert listing(directory) == [driver.NAME], listing(directory)
            else:  # the killed run had published: only an orphan sidecar may be left behind
                assert set(listing(directory)) - {driver.NAME} <= {NAMES.sidecar}, listing(
                    directory
                )
        except AssertionError as error:
            problems.append((label, str(error)[:300]))
    assert not problems, problems


def documented_boundaries():
    """The names the reference lists under "Sınır adları (`step`)", alternatives expanded."""
    text = (REPOSITORY / "docs/reference/download-engine.md").read_text(encoding="utf-8")
    paragraph = next(p for p in text.split("\n\n") if p.startswith("**Sınır adları (`step`).**"))
    names = set()
    for token in re.findall(r"`([^`]+)`", paragraph)[1:]:  # the first is the function's own name
        head, colon, tail = token.partition(":")
        if colon:
            names.update(f"{head}:{alternative}" for alternative in tail.split("|"))
        elif re.fullmatch(r"[a-z_]+", token):
            names.add(token)
    return names


def test_the_boundary_names_of_the_reference_are_the_ones_the_scenarios_announce(tmp_path):
    announced = set()
    for name, (scenario, preparation, extra) in SCENARIOS.items():
        record = tmp_path / f"{name}.txt"
        run = child(prepared(tmp_path, name, preparation), scenario, extra, record=record)
        assert run.returncode == 0, (name, run.stderr.decode()[-300:])
        announced |= {label.split("#")[0] for label in record.read_text().split()}
    documented = documented_boundaries()
    assert documented - announced == set(), "documented, never announced"
    assert announced - documented == set(), "announced, never documented"


def test_the_boundaries_come_in_the_order_the_reference_closes(tmp_path):
    record = tmp_path / "steps.txt"
    directory = prepared(tmp_path, "run", None)
    assert child(directory, "fresh", {}, record=record).returncode == 0
    steps = [label.split("#")[0] for label in record.read_text().split()]
    milestones = [
        "lock:created",  # 2. the lock object, exclusively, private
        "lock:private",
        "lock:held",  # 3. flock, and the name still leads to the locked file
        "decided",  # 5. the table decides on the directory as found
        "stage:created",  # 6. then the stage is created
        "stage:private",
        "sidecar_tmp:created",  # 8. the header checkpoint, before the first byte
        "sidecar:replaced",
        "body:written",  # 9. the body
        "complete:stage_synced",  # 10. the completion checkpoint
        "completion_checkpoint",
        "compared",  # 11. the comparison
        "publish:synced",  # 12. full sync, then the link
        "publish:before_link",
        "publish:after_link",
        "cleanup:stage",  # 13. stage, sidecar, (tmp), directory sync, lock object last
        "removed:sidecar",
        "cleanup:all_removed",
        "publish:directory_synced",
        "removed:lock",
    ]
    position = -1
    for milestone in milestones:
        later = [i for i, step in enumerate(steps) if step == milestone and i > position]
        assert later, f"{milestone!r} does not come after position {position} in {steps}"
        position = later[0]
    assert steps[-1] == "removed:lock"  # the lock object is the last change to the directory


@pytest.mark.parametrize("preparation", [None, "stopped", "unpublished"])
def test_a_kill_under_a_hostile_umask_leaves_files_the_next_run_accepts(tmp_path, preparation):
    record = tmp_path / "steps.txt"
    extra = {"SINK_UMASK": "277"}
    run = child(prepared(tmp_path, "recording", preparation), "fresh", extra, record=record)
    assert run.returncode == 0, run.stderr.decode()[-500:]
    creations = [
        label
        for label in record.read_text().split()
        if label.split("#")[0].endswith((":created", ":private"))
    ]
    assert creations
    for number, label in enumerate(creations):
        directory = prepared(tmp_path, f"umask-{number}", preparation)
        assert child(directory, "fresh", extra, kill=label).returncode == -signal.SIGKILL
        assert_only_the_protocols_own_traces(directory)  # and every file of it is 0600
        driver.engine_run(directory)
        assert listing(directory) == [driver.NAME], (label, listing(directory))
        assert (directory / driver.NAME).read_bytes() == driver.DATA
