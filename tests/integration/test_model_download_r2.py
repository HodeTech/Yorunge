"""What round two of P02-3n pinned: R1 fixes that no test noticed, and what a person is told.

The advice of a timeout is true only where it is given; a terminated process leaves a state the
next run continues from; a progress callback is a plain synchronous callable; the capture of the
local snapshot waits for a busy store the way it says it does; the progress line is ended only if
it was written.
"""

import functools
import io
import json
import random
import signal
import sys
import time

import pytest

from tests.fixtures.http_server import Reply
from tests.integration.test_download_engine import TAG, Provider
from tests.integration.test_model_download import (
    NAME,
    VERSION,
    Rig,
    code_of,
)
from tests.integration.test_model_download import (
    certificates as certificates,
)
from tests.integration.test_model_download import (
    workspace as workspace,
)
from tests.integration.test_model_download_cli import (
    command,
    error_of,
    popen,
    run,
)
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from yorunge.adapters import model_download
from yorunge.cli.models import (
    NO_RESUME_HINT,
    TARGET_HINT,
    TIMEOUT_HINT,
    ProgressText,
    _mismatch_hint,
    error_hints,
)
from yorunge.domain.download import download_names
from yorunge.domain.errors import DownloadIntegrityMismatch, YorungeError

MIB = 1024 * 1024


# --- the advice of a timeout ----------------------------------------------------------------------


def test_a_stalled_json_call_times_out_after_five_seconds_and_only_text_says_what_helps(
    certificates, workspace
):
    stalled = Reply(body=b"{}", header_delay=7.0)
    with Rig(certificates, workspace, route=lambda record, count: stalled) as rig:
        began = time.monotonic()
        text = run(rig, certificates, command(rig))
        waited = time.monotonic() - began
        machine = run(rig, certificates, command(rig, output="json"))
    # the first-byte limit of the call (5 s), not the download's --timeout (30..3600 s)
    assert 4.5 < waited < 25
    assert text.returncode == machine.returncode == 1
    assert error_of(machine)["code"] == "transport_timeout"
    message = text.stderr.decode("utf-8")
    # exactly: the fixed message, a newline, the advice, a newline — nothing before or after
    assert message == f"{YorungeError('transport_timeout').message}\n{TIMEOUT_HINT}\n"
    assert "ETag ile toplam boyutu bildirdiyse" in message and "yardımcı olmaz" in message
    assert "yardımcı olmaz" not in machine.stderr.decode() and "hint" not in machine.stderr.decode()
    assert rig.signed() == [] and rig.names() == []  # nothing was downloaded, nothing was kept


def test_the_timeout_advice_does_not_promise_what_depends_on_the_provider():
    # A saved partial file needs the provider's ETag and total size; the advice says so, and it
    # separates a spent --timeout from a stalled connection that no timeout cures.
    assert "ETag" in TIMEOUT_HINT and "toplam boyutu" in TIMEOUT_HINT
    assert "--timeout" in TIMEOUT_HINT and "5 sn" in TIMEOUT_HINT
    hints = error_hints(_Args(no_resume=False))
    assert hints["transport_timeout"] == TIMEOUT_HINT
    assert hints["download_target_invalid"] == TARGET_HINT
    assert "download_partial_unverified" not in hints
    assert error_hints(_Args(no_resume=True))["download_partial_unverified"] == NO_RESUME_HINT


class _Args:
    def __init__(self, **values):
        self.__dict__.update(values)


def test_the_mismatch_hint_names_the_digest_only_for_an_error_that_carries_one():
    mismatch = DownloadIntegrityMismatch("a" * 64, 5)
    hint = _mismatch_hint(mismatch)
    assert hint is not None and "a" * 64 in hint and "(5 bayt)" in hint
    assert _mismatch_hint(YorungeError("download_integrity_mismatch")) is None  # no details at all
    for details in (
        None,
        "x",
        [],
        {},
        {"computed_sha256": "a" * 64},
        {"computed_sha256": 1, "bytes": 5},
        {"computed_sha256": "a" * 64, "bytes": "5"},
        {"computed_sha256": "a" * 64, "bytes": True},
    ):
        error = YorungeError("download_integrity_mismatch")
        error.details = details  # type: ignore[attr-defined]
        assert _mismatch_hint(error) is None, details


# --- the help -------------------------------------------------------------------------------------


def test_the_help_states_the_ceiling_the_prerequisites_and_the_symlink_rule(
    certificates, workspace
):
    with Rig(certificates, workspace) as rig:
        process = run(rig, certificates, ["models", "download", "--help"])
        text = " ".join(process.stdout.decode().split())
        assert process.returncode == 0 and rig.server.requests == []
    for phrase in (
        "En çok 1 GiB iner",
        "aşılırsa hedef oluşturulmaz",
        "Önkoşullar",
        "yorunge state init",
        "EVREN_PLATFORM_API_KEY",
        "Anahtar argüman değildir",
        "üst dizin zinciri symlink içermemeli",
        "/private/... verin",
        "Hedef var olan bir dosyaysa ezilmez",
        "k-fold sürümleri için fold (0-1024)",
    ):
        assert phrase in text, phrase


# --- a terminated process -------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal contract")
@pytest.mark.parametrize(
    "signal_number", [signal.SIGTERM, signal.SIGHUP], ids=["SIGTERM", "SIGHUP"]
)
def test_a_terminated_download_dies_by_the_signal_and_the_next_run_resumes_at_the_checkpoint(
    certificates, workspace, signal_number
):
    if signal_number == signal.SIGHUP and signal.getsignal(signal.SIGHUP) == signal.SIG_IGN:
        pytest.skip("started under nohup: a child inherits an ignored SIGHUP")
    big = random.Random(5).randbytes(20 * MIB)
    slow = Reply(body=big, headers=(("ETag", TAG),), chunk_size=MIB, chunk_delay=0.25)
    with Rig(certificates, workspace, Provider(data=big)) as rig:
        rig.provider.script = [slow]
        process = popen(rig, certificates, command(rig, output="json"))
        names = download_names(NAME)
        try:
            end = time.monotonic() + 60
            stage = rig.directory / names.stage
            while time.monotonic() < end and not (
                stage.exists() and stage.stat().st_size > 10 * MIB
            ):
                time.sleep(0.05)
            process.send_signal(signal_number)
            stdout, stderr = process.communicate(timeout=60)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
        assert process.returncode == -signal_number and stdout == b""  # no handler: died by it
        assert not rig.target.exists()
        sidecar = json.loads((rig.directory / names.sidecar).read_text())
        assert sidecar["committed_bytes"] == 8 * MIB  # the last checkpoint before the signal
        rig.provider.script, rig.provider.seen = [], []
        finished = run(rig, certificates, command(rig, output="json"))
        assert finished.returncode == 0 and rig.target.read_bytes() == big
        data = json.loads(finished.stdout)["data"]
        assert data["resumed"] is True and data["resumed_from_bytes"] == 8 * MIB
        assert rig.provider.seen[0][0] == f"bytes={8 * MIB}-"


# --- a progress callback is a synchronous callable ------------------------------------------------


class _Collector:
    def __init__(self):
        self.reports = []

    def __call__(self, held, total):
        self.reports.append((held, total))


async def _async_progress(held, total):
    raise AssertionError("never called")


class _AsyncCallable:
    async def __call__(self, held, total):
        raise AssertionError("never called")


@pytest.mark.parametrize(
    "progress",
    [
        _async_progress,
        functools.partial(_async_progress),
        _AsyncCallable(),
        "not callable",
        42,
    ],
    ids=["async def", "partial of async def", "async __call__", "string", "int"],
)
def test_a_progress_callback_that_would_only_produce_a_coroutine_is_refused_up_front(
    certificates, workspace, progress
):
    with Rig(certificates, workspace) as rig:
        assert code_of(lambda: rig.call(progress=progress)) == "invalid_request"
        assert rig.server.requests == [] and rig.names() == []


def test_an_instance_with_a_plain_call_is_a_progress_callback(certificates, workspace):
    collector = _Collector()
    with Rig(certificates, workspace) as rig:
        summary = rig.call(progress=collector).data
        assert rig.target.exists() and summary.bytes > 0
    assert collector.reports and collector.reports[-1][0] == summary.bytes


# --- the capture of the local snapshot ------------------------------------------------------------


class _Busy:
    """A store that other commands hold for a moment: ``busy`` answers, then the snapshot."""

    def __init__(self, busy, code="state_busy"):
        self.busy, self.code, self.deadlines = busy, code, []

    def capture(self, *, deadline):
        self.deadlines.append(deadline)
        assert len(self.deadlines) < 2_000, "the retry loop never ends"  # fail, do not hang
        if len(self.deadlines) <= self.busy:
            raise YorungeError(self.code)
        return "snapshot"


class _Clock:
    """A clock that only the slept time moves."""

    def __init__(self, monkeypatch, start=1000.0):
        self.now, self.slept = start, []
        monkeypatch.setattr(model_download.time, "monotonic", lambda: self.now)
        monkeypatch.setattr(model_download.time, "sleep", self.sleep)

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


@pytest.mark.parametrize(
    "fraction,expected", [(0.0, 0.05), (0.5, 0.175), (1.0, 0.30)], ids=["low", "middle", "high"]
)
def test_a_busy_store_is_waited_for_with_a_jitter_of_fifty_to_three_hundred_milliseconds(
    monkeypatch, fraction, expected
):
    clock = _Clock(monkeypatch)
    monkeypatch.setattr(model_download.random, "random", lambda: fraction)
    state = _Busy(2)
    assert model_download._captured(state, clock.now + 30) == "snapshot"
    assert clock.slept == pytest.approx([expected, expected])
    assert len(state.deadlines) == 3 and len(set(state.deadlines)) == 1  # one window for all


def test_the_wait_is_clamped_to_what_is_left_of_the_window(monkeypatch):
    clock = _Clock(monkeypatch)
    monkeypatch.setattr(model_download.random, "random", lambda: 1.0)  # the longest jitter
    state = _Busy(1)
    assert model_download._captured(state, clock.now + 0.45) == "snapshot"
    assert clock.slept == pytest.approx([0.25])  # 0.45 - 0.2, not the 0.30 jitter


def test_a_window_that_is_over_ends_the_wait_with_the_busy_error(monkeypatch):
    clock = _Clock(monkeypatch)
    state = _Busy(10)
    assert code_of(lambda: model_download._captured(state, clock.now + 0.3)) == "state_busy"
    assert clock.slept == [] and len(state.deadlines) == 1  # no time left: not waited for


def test_a_store_that_stays_busy_is_given_up_when_the_window_is_spent(monkeypatch):
    clock = _Clock(monkeypatch)
    monkeypatch.setattr(model_download.random, "random", lambda: 0.5)
    state = _Busy(10_000)
    assert code_of(lambda: model_download._captured(state, clock.now + 2.0)) == "state_busy"
    assert 1.5 <= sum(clock.slept) <= 2.0 and len(state.deadlines) >= 5  # waited, within the window


@pytest.mark.parametrize("code", ["credential_unavailable", "state_invalid", "invalid_request"])
def test_only_a_busy_store_is_waited_for(monkeypatch, code):
    clock = _Clock(monkeypatch)
    state = _Busy(1, code=code)
    assert code_of(lambda: model_download._captured(state, clock.now + 30)) == code
    assert clock.slept == [] and len(state.deadlines) == 1


def test_the_window_of_the_capture_is_thirty_seconds_from_the_start_of_the_call(
    monkeypatch, tmp_path
):
    assert model_download.CAPTURE_SECONDS == 30.0
    seen = []

    def stop(state, end):
        seen.append(end - time.monotonic())
        raise YorungeError("credential_unavailable")

    monkeypatch.setattr(model_download, "_captured", stop)
    from yorunge import api

    with pytest.raises(YorungeError):
        api.download_model_weights(
            VERSION,
            artifact_format="onnx",
            weights_out=tmp_path / NAME,
            config=tmp_path / "absent.toml",
            state_dir=tmp_path / "state",
        )
    assert seen and 25 < seen[0] <= 30  # started + 30 s, a few moments after the start


# --- the progress line is ended only if it was written --------------------------------------------


class _Terminal(io.StringIO):
    def isatty(self):
        return True


def test_a_report_that_was_dropped_does_not_leave_a_line_to_end(monkeypatch):
    stream = _Terminal()
    progress = ProgressText(stream)
    monkeypatch.setattr(progress, "_writable", lambda: False)  # the terminal takes nothing now
    progress(10, 100)
    monkeypatch.setattr(progress, "_writable", lambda: True)  # it recovers before the end
    progress.close()
    assert stream.getvalue() == ""  # no lone newline: no line was ever begun


def test_a_line_that_was_written_is_ended_when_the_terminal_takes_the_newline(monkeypatch):
    stream = _Terminal()
    progress = ProgressText(stream)
    progress(10, 100)
    progress.close()
    assert stream.getvalue().endswith("(%10)\n")
    stopped = _Terminal()
    other = ProgressText(stopped)
    other(10, 100)
    monkeypatch.setattr(other, "_writable", lambda: False)  # stopped exactly at the end
    other.close()  # never waited for: the newline is lost and nothing raises
    assert stopped.getvalue().endswith("(%10)") and other._open is False


def test_a_stream_that_cannot_say_whether_it_is_writable_takes_no_report():
    class Odd(_Terminal):
        def fileno(self):
            return -1  # select refuses it

    stream = Odd()
    progress = ProgressText(stream)
    progress(10, 100)
    progress.close()
    assert stream.getvalue() == "" and progress.enabled is True


# --- a terminal that cannot say whether it is writable: the write decides -------------------------


@pytest.mark.parametrize("error", [OSError, ValueError, AttributeError], ids=lambda e: e.__name__)
def test_a_stream_whose_descriptor_cannot_be_asked_for_still_takes_its_reports(error):
    class NoDescriptor(_Terminal):
        def fileno(self):
            raise error("no descriptor")

    stream = NoDescriptor()
    progress = ProgressText(stream)
    progress(10, 100)
    progress.close()
    assert stream.getvalue().endswith("(%10)\n")  # asked nothing, written, ended


# --- the options of the command group stand between `models` and the action ----------------------


def test_the_common_options_are_accepted_between_models_and_the_action(monkeypatch, tmp_path):
    from yorunge import api
    from yorunge.cli import main

    calls = []

    def stub(*args, **kwargs):
        calls.append(kwargs)
        raise YorungeError("remote_failed")

    monkeypatch.setattr(api, "download_model_weights", stub)
    arguments = [
        "--version-id",
        VERSION,
        "--format",
        "onnx",
        "--weights-out",
        str(tmp_path / "w.onnx"),
    ]
    state = tmp_path / "state"
    code = main(["models", "--output", "json", "--state-dir", str(state), "download", *arguments])
    assert code == 1 and calls[0]["state_dir"] == state
    # and without a state directory the API is given None: the user's default store
    assert main(["models", "download", *arguments]) == 1 and calls[1]["state_dir"] is None


def test_the_default_state_directory_is_used_when_none_is_given(
    certificates, workspace, monkeypatch, tmp_path
):
    from yorunge import api

    home = tmp_path / "home"
    home.mkdir()
    for name in ("XDG_STATE_HOME", "XDG_DATA_HOME", "XDG_CONFIG_HOME"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", str(home))
    api.initialize_state()  # the default store under HOME
    with Rig(certificates, workspace) as rig:
        summary = rig.call(state_dir=None).data
        assert summary.bytes > 0 and rig.target.exists()


# --- the text of a download, line by line ---------------------------------------------------------


def test_the_text_of_a_download_is_exactly_these_lines_in_this_order(certificates, workspace):
    from tests.integration.test_download_engine import DATA, sha

    with Rig(certificates, workspace) as rig:
        process = run(rig, certificates, command(rig))
        assert process.returncode == 0 and process.stderr == b""
        expected = "\n".join(
            (
                f"Model ağırlığı indirildi: {rig.target}",
                f"Sürüm: {VERSION}; biçim onnx",
                f"Boyut: {len(DATA)} bayt; SHA-256: {sha(DATA)}",
                "Doğrulama: yalnız aktarım tamamlandı (transfer_complete); beklenen bir özet "
                "verilmedi, içerik doğrulanmadı. Bağımsız bir özetiniz varsa --sha256 ile verin.",
                "Aktarım: baştan indirildi.",
                "Seviye yalnız indirilen baytların beklentinizle ilişkisini söyler; "
                "sağlayıcıdaki nesnenin özgünlüğünü, lisansını ya da model uygunluğunu söylemez.",
            )
        )
        assert process.stdout.decode("utf-8") == expected + "\n"
