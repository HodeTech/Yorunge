"""Actual SIGINT and OS output failures preserve local publication/job semantics."""

import json
import signal
import socket
import subprocess
import sys
from asyncio import CancelledError
from contextlib import contextmanager
from pathlib import Path

import pytest

from tests.fixtures.operation_backend import ReadObserver
from yorunge import api
from yorunge.adapters import configuration
from yorunge.adapters.files import load_config
from yorunge.domain.errors import YorungeError

FIXTURE = Path(__file__).parents[1] / "fixtures/cli_interruption.py"


def receive_line(control):
    value = bytearray()
    while not value.endswith(b"\n"):
        chunk = control.recv(1)
        if not chunk or len(value) >= 128:
            raise AssertionError(f"missing fixture barrier: {bytes(value)!r}")
        value.extend(chunk)
    return bytes(value)


def with_closed_descriptor(command, descriptor):
    # Close before a fresh interpreter starts so sys.stdout/stderr really is
    # None, rather than a TextIOWrapper left around an invalid file descriptor.
    return [
        sys.executable,
        "-c",
        "import os,sys; os.close(int(sys.argv[1])); os.execv(sys.argv[2], sys.argv[2:])",
        str(descriptor),
        *command,
    ]


@contextmanager
def gated_cli(target, phase, *arguments, closed_descriptor=None):
    parent, child = socket.socketpair()
    parent.settimeout(10)
    command = [sys.executable, str(FIXTURE), str(child.fileno()), phase, str(target), *arguments]
    if closed_descriptor is not None:
        command = with_closed_descriptor(command, closed_descriptor)
    process = subprocess.Popen(
        command,
        pass_fds=(child.fileno(),),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    child.close()
    try:
        assert receive_line(parent) == b"ready\n"
        yield process, parent
    finally:
        parent.close()
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=10)


def interrupt(target, phase, *arguments):
    with gated_cli(target, phase, *arguments) as (process, control):
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=10)
        publication = receive_line(control)
        return process.returncode, stdout.decode(), stderr.decode(), publication


PUBLICATION_PHASES = (
    ("stage-before", False, 6, 0),
    ("temporary-fsync", False, 6, 0),
    ("publish-before", False, 6, 0),
    ("parent-sync-before", True, 5, 1),
    ("parent-sync-after", True, 5, 1),
    ("file-sync-before", True, 5, 1),
    ("file-sync-after", True, 5, 1),
    ("confirmed", True, 6, 1),
)


@pytest.mark.parametrize("output", ["json", "ndjson"])
@pytest.mark.parametrize(
    "action,phase,published,exit_code,calls",
    [
        (action, phase, published, exit_code, calls)
        for action in ("init", "update")
        for phase, published, exit_code, calls in (
            *PUBLICATION_PHASES,
            ("link-before" if action == "init" else "replace-before", False, 5, 1),
            ("link-after" if action == "init" else "replace-after", True, 5, 1),
            *((("snapshot-before", False, 6, 0),) if action == "update" else ()),
        )
    ],
)
def test_sigint_distinguishes_prepublication_uncertainty_and_confirmed_publication(
    config, tmp_path, action, phase, published, exit_code, calls, output
):
    target = tmp_path / "new.toml" if action == "init" else config
    original = target.read_bytes() if action == "update" else None
    arguments = (
        ("init", "--profile", "created")
        if action == "init"
        else ("context", "set-project", "changed")
    )
    actual, stdout, stderr, publication = interrupt(
        target, phase, *arguments, "--config", str(target), "--output", output
    )
    assert actual == exit_code, stderr
    assert stdout == ""
    expected = "config_write_uncertain" if exit_code == 5 else "request_cancelled"
    assert json.loads(stderr) == YorungeError(expected).envelope()
    assert publication == f"publication={calls}\n".encode()
    if action == "init":
        assert target.exists() is published
        if published:
            assert load_config(target).active_profile == "created"
        assert not target.with_name("." + target.name + ".backups").exists()
    else:
        if published:
            assert load_config(target).profiles["work"].project_id == "changed"
        else:
            assert target.read_bytes() == original
        backups = list(target.with_name("." + target.name + ".backups").glob("*.toml"))
        assert len(backups) == (0 if phase == "snapshot-before" else 1)
        assert all(path.read_bytes() == original for path in backups)


@pytest.mark.parametrize("output", ["text", "json", "ndjson"])
def test_sigint_while_reading_is_local_cancellation_with_unchanged_config(config, output):
    original = config.read_bytes()
    exit_code, stdout, stderr, publication = interrupt(
        config, "read-before", "context", "show", "--config", str(config), "--output", output
    )
    assert exit_code == 6, stderr
    assert stdout == ""
    if output == "text":
        assert stderr.strip() == YorungeError("request_cancelled").message
    else:
        assert json.loads(stderr) == YorungeError("request_cancelled").envelope()
    assert publication == b"publication=0\n"
    assert config.read_bytes() == original
    assert not config.with_name("." + config.name + ".backups").exists()


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, CancelledError])
@pytest.mark.parametrize(
    "initial,boundary",
    [
        (initial, boundary)
        for initial in (False, True)
        for boundary in (
            "stage",
            "publish",
            "confirmed",
            *(("read_snapshot",) if not initial else ()),
        )
    ],
)
def test_python_cancellation_outside_critical_publication_propagates(
    config, tmp_path, monkeypatch, interruption, initial, boundary
):
    target = tmp_path / "new.toml" if initial else config
    before = None if initial else target.read_bytes()
    name = "publish" if boundary == "confirmed" else boundary
    original = getattr(configuration, name)
    cancellation = interruption("private-cancellation-payload")
    calls = []

    def cancelled(*args, **kwargs):
        calls.append(1)
        if boundary == "confirmed":
            original(*args, **kwargs)
        raise cancellation

    monkeypatch.setattr(configuration, name, cancelled)
    with pytest.raises(interruption) as caught:
        if initial:
            api.initialize_config(config=target, profile="created")
        else:
            api.set_project("changed", config=target)
    assert caught.value is cancellation
    assert calls == [1]
    if boundary == "confirmed":
        if initial:
            assert load_config(target).active_profile == "created"
        else:
            assert load_config(target).profiles["work"].project_id == "changed"
    elif initial:
        assert not target.exists()
    else:
        assert target.read_bytes() == before


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, CancelledError])
@pytest.mark.parametrize("initial", [False, True])
@pytest.mark.parametrize("boundary", ["publication", "sync"])
def test_python_critical_publication_cancellation_has_detached_safe_error(
    tmp_path, monkeypatch, interruption, initial, boundary
):
    target, temporary = tmp_path / "target", tmp_path / "temporary"
    temporary.write_bytes(b"new")
    if not initial:
        target.write_bytes(b"old")
    calls = []

    def cancelled(*args, **kwargs):
        calls.append(1)
        raise interruption("private-cancellation-payload")

    if boundary == "publication":
        monkeypatch.setattr(configuration.os, "link" if initial else "replace", cancelled)
    else:
        monkeypatch.setattr(configuration, "sync_directory", cancelled)
    with pytest.raises(YorungeError) as caught:
        configuration.publish(target, temporary, initial=initial)
    assert caught.value.code == "config_write_uncertain"
    assert caught.value.exit_code == 5
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None
    assert "private-cancellation-payload" not in str(caught.value.envelope())
    assert calls == [1]
    if boundary == "sync":
        assert target.read_bytes() == b"new"
    elif initial:
        assert not target.exists()
    else:
        assert target.read_bytes() == b"old"


@pytest.mark.parametrize("interruption", [SystemExit, GeneratorExit])
def test_publication_does_not_swallow_other_base_exceptions(tmp_path, monkeypatch, interruption):
    def stopped(*args, **kwargs):
        raise interruption

    monkeypatch.setattr(configuration.os, "link", stopped)
    with pytest.raises(interruption):
        configuration.publish(tmp_path / "target", tmp_path / "temporary", initial=True)


def test_publication_existing_target_keeps_config_exists(tmp_path):
    target, temporary = tmp_path / "target", tmp_path / "temporary"
    target.write_bytes(b"existing")
    temporary.write_bytes(b"new")
    with pytest.raises(YorungeError) as caught:
        configuration.publish(target, temporary, initial=True)
    assert caught.value.code == "config_exists"
    assert caught.value.exit_code == 2
    assert caught.value.__context__ is None
    assert target.read_bytes() == b"existing"


@pytest.fixture
def successful_job(operation_setup, execution_clock):
    state, plan, backend = operation_setup
    observer = ReadObserver(execution_clock, marker=backend.marker)
    with api._operation_session(
        plan.plan_id, backend, observer=observer, state_dir=state
    ) as coordinator:
        claim = coordinator.admit(plan.plan_id)
        identifier = claim.job.operation.operation_id
        coordinator.dispatch(identifier, claim.ownership)
        job = coordinator.reconcile(identifier, claim.ownership)
    assert job.operation.status == "succeeded"
    assert job.outcome is not None
    return state, identifier, job, backend


@pytest.mark.parametrize("output", ["json", "ndjson"])
@pytest.mark.parametrize("failure", ["pipe-closed", "output-ebadf", "result-ready"])
def test_output_failure_or_local_cancel_keeps_successful_persistent_job(
    successful_job, output, failure
):
    state, identifier, before, backend = successful_job
    arguments = (
        "jobs",
        "show",
        "--state-dir",
        str(state),
        "--operation-id",
        identifier,
        "--output",
        output,
    )
    with gated_cli(state, failure, *arguments) as (process, control):
        if failure == "result-ready":
            process.send_signal(signal.SIGINT)
        else:
            if failure == "pipe-closed":
                process.stdout.close()
                process.stdout = None
            control.sendall(b"r")
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == (1 if failure == "output-ebadf" else 6), stderr
        assert not stdout
        code = {
            "pipe-closed": "output_closed",
            "output-ebadf": "output_write_failed",
            "result-ready": "request_cancelled",
        }[failure]
        assert json.loads(stderr) == YorungeError(code).envelope()
        assert receive_line(control) == b"publication=0\n"
    assert api.show_job(identifier, state_dir=state).data == before
    assert len(backend.effects()) == 1


def test_config_uncertainty_exit_survives_closed_error_pipe(tmp_path):
    target = tmp_path / "new.toml"
    with gated_cli(target, "link-after", "init", "--config", str(target), "--output", "ndjson") as (
        process,
        control,
    ):
        process.stderr.close()
        process.stderr = None
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 5
        assert stdout == b""
        assert stderr is None
        assert receive_line(control) == b"publication=1\n"
    assert load_config(target).active_profile == "default"


@pytest.mark.parametrize(
    "descriptor,arguments,expected",
    [
        (1, ["context", "show", "--output=json"], 1),
        (1, ["--help", "--output=json"], 1),
        (1, ["--version", "--output=json"], 1),
        (2, ["--unknown", "--output=ndjson"], 2),
    ],
)
def test_stdio_absent_at_python_startup_remains_controlled(descriptor, arguments, expected):
    command = with_closed_descriptor([sys.executable, "-m", "yorunge", *arguments], descriptor)
    result = subprocess.run(command, capture_output=True, timeout=10)
    assert result.returncode == expected
    assert result.stdout == b""
    if descriptor == 1:
        assert json.loads(result.stderr)["code"] == "output_write_failed"
    else:
        assert result.stderr == b""


def test_missing_stderr_at_startup_preserves_actual_config_publish_uncertainty(tmp_path):
    target = tmp_path / "new.toml"
    with gated_cli(
        target,
        "link-after",
        "init",
        "--config",
        str(target),
        "--output=ndjson",
        closed_descriptor=2,
    ) as (process, control):
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 5
        assert stdout == b""
        assert stderr == b""
        assert receive_line(control) == b"publication=1\n"
    assert load_config(target).active_profile == "default"
