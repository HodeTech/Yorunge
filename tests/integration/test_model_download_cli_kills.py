"""Mutants of the command line that no test of the first suite killed (P02-3n R1).

Every option is a singleton, every typed option is what the API receives, the progress line on a
real terminal (a pty), machine output is given no progress receiver, a stream that cannot prove it
is a terminal is not one, and `--timeout` is as strict as the API.
"""

import json

import pytest

from tests.integration.test_model_download import VERSION
from yorunge import api
from yorunge.cli import main
from yorunge.domain.errors import YorungeError

SHA = "ab" * 32
# The twelve options of the command, by the literal list of the card (not the module's own set).
OPTIONS = {
    "--output": ["json"],
    "--non-interactive": [],
    "--state-dir": ["/tmp/s"],
    "--config": ["/tmp/c.toml"],
    "--profile": ["p"],
    "--version-id": [VERSION],
    "--format": ["onnx"],
    "--fold": ["1"],
    "--sha256": [SHA],
    "--timeout": ["30"],
    "--weights-out": ["/tmp/x.onnx"],
    "--no-resume": [],
}
REQUIRED = ["--version-id", VERSION, "--format", "onnx", "--weights-out", "/tmp/x.onnx"]


@pytest.mark.parametrize("option", sorted(OPTIONS))
def test_every_option_of_the_command_is_a_singleton(option, monkeypatch):
    """A repeated option is exit 2 before anything is asked (the last must not silently win)."""
    calls = []

    def stub(*args, **kwargs):
        calls.append(kwargs)
        raise YorungeError("remote_failed")

    monkeypatch.setattr(api, "download_model_weights", stub)
    once = [option, *OPTIONS[option]]
    argv = ["models", "download", *REQUIRED, *once, *once]
    if option != "--output":
        argv += ["--output", "json"]
    assert main(argv) == 2 and calls == []
    # control: given once, the same command reaches the API (so the 2 above is the repeat)
    single = ["models", "download", *REQUIRED]
    if option not in ("--version-id", "--format", "--weights-out"):
        single += once
    if option != "--output":
        single += ["--output", "json"]
    assert main(single) == 1 and len(calls) == 1


import os  # noqa: E402
import pty  # noqa: E402
import select  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402

from tests.fixtures.http_server import Reply  # noqa: E402
from tests.integration.test_download_engine import DATA, TAG  # noqa: E402
from tests.integration.test_model_download import Rig  # noqa: E402
from tests.integration.test_model_download import certificates as certificates  # noqa: E402
from tests.integration.test_model_download import workspace as workspace  # noqa: E402
from tests.integration.test_model_download_cli import argv, command, environment, run  # noqa: E402
from tests.integration.test_model_download_cli import rig as rig  # noqa: E402
from tests.integration.test_upload_preparation import loopback_only as loopback_only  # noqa: E402


def _on_terminal(rig, certificates, args, *, stdout_too):
    master, slave = pty.openpty()
    process = subprocess.Popen(
        argv(rig, certificates, args),
        stdin=subprocess.DEVNULL,
        stdout=slave if stdout_too else subprocess.PIPE,
        stderr=slave,
        env=environment(),
    )
    os.close(slave)
    seen = bytearray()
    end = time.monotonic() + 120
    while time.monotonic() < end:
        ready, _, _ = select.select([master], [], [], 0.1)
        if ready:
            try:
                chunk = os.read(master, 65536)
            except OSError:
                break
            if not chunk:
                break
            seen += chunk
        elif process.poll() is not None:
            break
    stdout, _ = process.communicate(timeout=60)
    os.close(master)
    return (
        process.returncode,
        bytes(seen).decode("utf-8", "replace"),
        (stdout or b"").decode("utf-8"),
    )


@pytest.fixture
def slow(certificates, workspace):
    with Rig(certificates, workspace) as rig:
        rig.provider.script = [
            Reply(body=DATA, headers=(("ETag", TAG),), chunk_size=65536, chunk_delay=0.03)
        ]
        yield rig


def test_a_terminal_sees_one_rewritten_line_then_a_newline_then_the_result(slow, certificates):
    code, terminal, _ = _on_terminal(slow, certificates, command(slow), stdout_too=True)
    assert code == 0 and slow.target.read_bytes() == DATA
    first, last = terminal.index("İndiriliyor"), terminal.index("Model ağırlığı indirildi")
    assert terminal.count("\rİndiriliyor") >= 3  # rewritten, not appended
    assert terminal[first:last].rstrip().endswith("(%100)")  # ends at the whole object ...
    assert (
        terminal[last - 2 : last] == "\r\n" or terminal[last - 1] == "\n"
    )  # ... and the result starts a new line


def test_machine_output_on_a_terminal_has_no_progress(certificates, workspace):
    with Rig(certificates, workspace) as rig:
        rig.provider.script = [
            Reply(body=DATA, headers=(("ETag", TAG),), chunk_size=65536, chunk_delay=0.03)
        ]
        code, terminal, _ = _on_terminal(
            rig, certificates, command(rig, output="json"), stdout_too=True
        )
        assert code == 0 and "İndiriliyor" not in terminal and terminal.lstrip().startswith("{")


def test_an_error_after_progress_starts_on_a_new_line(certificates, workspace):
    from tests.integration.test_download_engine import CUT

    with Rig(certificates, workspace) as rig:
        rig.provider.script = [
            Reply(
                body=DATA,
                headers=(("ETag", TAG),),
                truncate_at=CUT,
                chunk_size=65536,
                chunk_delay=0.03,
            )
        ]
        code, terminal, _ = _on_terminal(rig, certificates, command(rig), stdout_too=True)
        assert code == 1 and "İndiriliyor" in terminal
        message = terminal.index("İndirme tamamlanmadan kesildi")
        assert terminal[message - 1] == "\n"


def test_machine_output_is_given_no_progress_receiver_even_on_a_terminal(monkeypatch):
    import io
    import sys

    seen = []

    def stub(*args, **kwargs):
        seen.append(kwargs["progress"])
        raise YorungeError("invalid_request")

    class Terminal(io.StringIO):
        def isatty(self):
            return True

    monkeypatch.setattr(api, "download_model_weights", stub)
    monkeypatch.setattr(sys, "stderr", Terminal())
    base = ["models", "download", *REQUIRED]
    assert main([*base, "--output", "json"]) == 2 and seen == [None]
    assert main([*base, "--output", "ndjson"]) == 2 and seen == [None, None]
    assert main(base) == 2 and seen[-1] is not None  # control: text on a terminal gets one


def test_every_cli_option_reaches_the_api_and_the_defaults_are_the_apis(monkeypatch):
    from pathlib import Path

    calls = []

    def stub(version_id, **kwargs):
        calls.append((version_id, kwargs))
        raise YorungeError("remote_failed")

    monkeypatch.setattr(api, "download_model_weights", stub)
    main(
        [
            "models",
            "download",
            "--version-id",
            VERSION,
            "--format",
            "tflite",
            "--weights-out",
            "/tmp/x/w.tflite",
            "--fold",
            "7",
            "--sha256",
            SHA,
            "--timeout",
            "77",
            "--no-resume",
            "--config",
            "/tmp/c.toml",
            "--profile",
            "other",
            "--state-dir",
            "/tmp/s",
            "--output",
            "json",
        ]
    )
    main(["models", "download", *REQUIRED, "--output", "json"])
    (version, full), (_, bare) = calls
    assert version == VERSION
    assert full == {
        "artifact_format": "tflite",
        "weights_out": Path("/tmp/x/w.tflite"),
        "fold": 7,
        "sha256": SHA,
        "timeout": 77,
        "no_resume": True,
        "config": Path("/tmp/c.toml"),
        "profile": "other",
        "state_dir": Path("/tmp/s"),
        "progress": None,
    }
    assert bare == {
        "artifact_format": "onnx",
        "weights_out": Path("/tmp/x.onnx"),
        "fold": None,
        "sha256": None,
        "timeout": None,
        "no_resume": False,
        "config": None,
        "profile": None,
        "state_dir": None,
        "progress": None,
    }


def test_a_stream_that_cannot_say_whether_it_is_a_terminal_is_not_one():
    import io

    from yorunge.cli.models import ProgressText

    closed = io.StringIO()
    closed.close()  # isatty() raises ValueError

    class Raises(io.StringIO):
        def __init__(self, error):
            super().__init__()
            self.error = error

        def isatty(self):
            raise self.error

    assert ProgressText(closed).enabled is False
    assert ProgressText(None).enabled is False  # no isatty at all (AttributeError)
    assert ProgressText(Raises(OSError("x"))).enabled is False
    assert ProgressText(Raises(ValueError("x"))).enabled is False


@pytest.mark.parametrize(
    "error", [ValueError("I/O operation on closed file"), OSError(5, "EIO"), BrokenPipeError()]
)
def test_a_progress_write_that_fails_with_any_of_these_is_swallowed_and_silences_the_line(error):
    import io

    from yorunge.cli.models import ProgressText

    class Terminal(io.StringIO):
        def isatty(self):
            return True

        def write(self, text):
            raise error

    stream = Terminal()
    progress = ProgressText(stream)
    progress(1, 2)  # must not raise
    assert progress.enabled is False
    progress(2, 2)
    progress.close()


@pytest.mark.parametrize(
    "value", ["0900", "+900", "9_00", " 900", "900 ", "９００", "9e2", "900.0", ""]
)
def test_a_timeout_that_is_not_a_plain_decimal_integer_is_exit_2(value, monkeypatch):
    calls = []
    monkeypatch.setattr(
        api,
        "download_model_weights",
        lambda *a, **k: calls.append(k) or (_ for _ in ()).throw(YorungeError("remote_failed")),
    )
    assert (
        main(["models", "download", *REQUIRED, "--timeout", value, "--output", "json"]) == 2
        and calls == []
    )


# --- the progress line never decides the fate of the command --------------------------------------


def test_a_terminal_that_is_only_full_for_now_is_not_cut_off(monkeypatch):
    import errno
    import io

    from yorunge.cli import models
    from yorunge.cli.models import ProgressText

    silenced = []
    monkeypatch.setattr(
        models, "_silence_failed_descriptor", lambda stream: silenced.append(stream)
    )

    class Terminal(io.StringIO):
        def __init__(self, error):
            super().__init__()
            self.error = error

        def isatty(self):
            return True

        def write(self, text):
            raise self.error

    # a non-blocking terminal whose buffer is full: the real error may still be written to it
    full = Terminal(BlockingIOError(errno.EAGAIN, "full"))
    progress = ProgressText(full)
    progress(1, 2)
    assert progress.enabled is False and silenced == []
    # a terminal that is gone is cut off, as before
    gone = Terminal(OSError(errno.EIO, "gone"))
    progress = ProgressText(gone)
    progress(1, 2)
    assert progress.enabled is False and silenced == [gone]


def test_a_stopped_terminal_is_never_waited_for():
    """^S or a stalled ssh stops the terminal: a write would block the thread that the download's
    own deadlines need, so the report is dropped when the terminal takes nothing now."""
    import io
    import os
    import threading

    from yorunge.cli.models import ProgressText

    class Stopped(io.TextIOWrapper):
        def isatty(self):
            return True

    read, write = os.pipe()
    os.set_blocking(write, False)
    try:
        while True:  # fill the pipe nobody reads
            os.write(write, b"x" * 65_536)
    except BlockingIOError:
        pass
    os.set_blocking(write, True)  # a blocking write would now wait for ever
    stream = Stopped(io.FileIO(write, "w", closefd=True), write_through=True)
    progress = ProgressText(stream)
    done = threading.Event()

    def report():
        progress(1, 2)
        progress.close()
        done.set()

    thread = threading.Thread(target=report, daemon=True)
    thread.start()
    try:
        assert done.wait(10), "the report waited for a terminal that takes nothing"
    finally:
        os.close(read)  # lets a blocked writer (if the guard is gone) finish with EPIPE
        thread.join(10)


def test_a_target_through_a_symlink_says_so_in_text_and_the_envelope_is_unchanged(
    rig, certificates, tmp_path
):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    target = link / "w.onnx"
    as_text = run(rig, certificates, command(rig, out=target))
    as_json = run(rig, certificates, command(rig, out=target, output="json"))
    assert as_text.returncode == as_json.returncode == 2 and rig.server.requests == []
    assert "symlink içermemeli" in as_text.stderr.decode()
    assert "symlink içermemeli" not in as_json.stderr.decode()
    assert json.loads(as_json.stderr)["code"] == "download_target_invalid"
