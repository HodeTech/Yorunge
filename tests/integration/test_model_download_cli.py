"""``yorunge models download`` as a real CLI process against a loopback TLS provider.

What a person (or a CI job) sees: the help, the text and machine outputs and their purity, the exit
codes, the files, and nothing private anywhere. The provider is scripted; the state store, the
profile and the key's environment variable are the user's.
"""

import io
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.fixtures.http_server import Reply
from tests.integration.test_download_engine import CUT, DATA, TAG, sha
from tests.integration.test_model_download import (
    ENV,
    FILENAME,
    JSON_PATH,
    NAME,
    QUERY,
    SECRET,
    VERSION,
    Rig,
    json_route,
)
from tests.integration.test_model_download import (
    certificates as certificates,
)
from tests.integration.test_model_download import (
    workspace as workspace,
)
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from yorunge.cli.models import ProgressText
from yorunge.domain.download import download_names

CONSOLE = Path(__file__).parents[1] / "fixtures" / "model_console.py"
CANARIES = (SECRET, "PRIVATE-URL-CANARY", FILENAME, "X-Amz-Credential", TAG, QUERY)


def command(rig, *extra, output=None, version=VERSION, fmt="onnx", out=None):
    return [
        "models",
        "download",
        "--version-id",
        version,
        "--format",
        fmt,
        "--weights-out",
        str(out or rig.target),
        "--config",
        str(rig.config),
        "--state-dir",
        str(rig.state),
        *(["--output", output] if output else []),
        *extra,
    ]


def environment(extra=None):
    return {
        **os.environ,
        "LC_ALL": "C",
        "PYTHONIOENCODING": "ascii",
        "PYTHONUTF8": "0",
        **(extra or {}),
    }


def argv(rig, certificates, args):
    return [
        sys.executable,
        "-I",
        "-W",
        "error",
        str(CONSOLE),
        "--ca",
        str(certificates[0]),
        "--port",
        str(rig.server.port),
        "--",
        *args,
    ]


def run(rig, certificates, args, *, timeout=120, extra_env=None):
    return subprocess.run(
        argv(rig, certificates, args),
        env=environment(extra_env),
        capture_output=True,
        timeout=timeout,
    )


def popen(rig, certificates, args):
    return subprocess.Popen(
        argv(rig, certificates, args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment(),
    )


def stdout_of(process):
    return process.stdout.decode("utf-8", "strict")


def error_of(process):
    assert not process.stdout.strip(), process.stdout[:200]
    return json.loads(process.stderr.decode("utf-8", "strict"))


def assert_nothing_private(*streams, rig):
    texts = [s.decode("utf-8", "replace") if isinstance(s, bytes) else s for s in streams]
    for path in (rig.state, rig.directory):
        for item in path.rglob("*"):
            if item.is_file() and item != rig.target:
                texts.append(item.read_bytes().decode("latin-1"))
    for text in texts:
        for canary in CANARIES:
            assert canary not in text, canary


@pytest.fixture
def rig(certificates, workspace):
    with Rig(certificates, workspace) as held:
        yield held


# --- the help -------------------------------------------------------------------------------------


def test_the_help_says_where_the_version_id_comes_from_and_what_the_options_cost(rig, certificates):
    process = run(rig, certificates, ["models", "download", "--help"])
    text = " ".join(stdout_of(process).split())  # argparse wraps lines: compare words, not layout
    assert process.returncode == 0 and process.stderr == b""
    for phrase in (
        "--version-id",
        "Platform arayüzündeki model sürümü sayfasından",  # where the id is taken from
        "ad ya da slug çözülmez",
        "--format {onnx,pt,tflite}",
        "zorunlu",
        "--weights-out",
        "var olan ezilmez",
        "--fold",
        "--sha256",
        "sha256_matched",
        "transfer_complete",
        "--timeout",
        "30-3600",
        "varsayılan 900",
        "9,5 Mbit/s",  # what the default needs for the largest object
        "--no-resume",
        "kaldığı yerden devam eder",
    ):
        assert phrase in text, phrase
    assert rig.server.requests == []


def test_the_command_is_listed_and_documented_at_every_level(rig, certificates):
    assert "models" in stdout_of(run(rig, certificates, ["--help"]))
    assert "download" in stdout_of(run(rig, certificates, ["models", "--help"]))
    bare = run(rig, certificates, ["models", "--output", "json"])
    assert bare.returncode == 2 and json.loads(bare.stderr)["code"] == "invalid_request"


# --- the outputs ----------------------------------------------------------------------------------


def test_the_text_output_names_the_file_the_level_and_what_it_does_not_claim(rig, certificates):
    process = run(rig, certificates, command(rig))
    text = stdout_of(process)
    assert process.returncode == 0 and process.stderr == b"" and rig.target.read_bytes() == DATA
    assert f"Model ağırlığı indirildi: {rig.target}" in text
    assert f"Sürüm: {VERSION}; biçim onnx" in text and ", fold" not in text
    assert f"Boyut: {len(DATA)} bayt; SHA-256: {sha(DATA)}" in text
    assert "transfer_complete" in text and "içerik doğrulanmadı" in text
    assert "--sha256 ile verin" in text and "sha256_matched" not in text
    assert "Aktarım: baştan indirildi." in text
    assert "özgünlüğünü, lisansını ya da model uygunluğunu söylemez" in text
    assert_nothing_private(process.stdout, process.stderr, rig=rig)


def test_the_text_output_of_a_verified_download_says_whose_digest_matched(rig, certificates):
    rig.server.routes[f"{JSON_PATH}?format=onnx&fold=2"] = json_route()
    process = run(rig, certificates, command(rig, "--sha256", sha(DATA), "--fold", "2"))
    text = stdout_of(process)
    assert process.returncode == 0
    assert "sha256_matched" in text and "verdiğiniz beklenen özetle eşleşti" in text
    assert "transfer_complete" not in text and "biçim onnx, fold 2" in text


def test_json_is_one_result_and_nothing_else_and_ndjson_is_one_event(rig, certificates):
    as_json = run(rig, certificates, command(rig, output="json"))
    assert as_json.returncode == 0 and as_json.stderr == b""
    value = json.loads(as_json.stdout)
    data = value["data"]
    assert value["operation_id"] is None and value["warnings"] == []
    assert data["kind"] == "download_summary" and data["bytes"] == len(DATA)
    assert data["verification_level"] == "transfer_complete" and data["source"]["format"] == "onnx"
    rig.target.unlink()
    as_events = run(rig, certificates, command(rig, output="ndjson"))
    assert as_events.returncode == 0 and as_events.stderr == b""
    (line,) = as_events.stdout.decode().splitlines()
    event = json.loads(line)
    assert event["event"] == "result" and event["sequence"] == 1
    assert event["payload"]["data"]["sha256"] == sha(DATA)
    assert_nothing_private(as_json.stdout, as_events.stdout, rig=rig)


# --- exit codes and envelopes ---------------------------------------------------------------------


def test_a_digest_that_differs_is_exit_7_with_no_target_and_no_result(rig, certificates):
    process = run(rig, certificates, command(rig, "--sha256", "00" * 32, output="json"))
    assert process.returncode == 7
    assert error_of(process)["code"] == "download_integrity_mismatch"
    assert rig.names() == [] and len(rig.signed()) == 1
    assert_nothing_private(process.stdout, process.stderr, rig=rig)


def test_a_digest_that_differs_shows_the_digest_that_was_computed_in_text_too(rig, certificates):
    """The stage is gone after a mismatch, so seeing the digest again would cost a download."""
    text = run(rig, certificates, command(rig, "--sha256", "00" * 32))
    assert text.returncode == 7 and not text.stdout.strip()
    message = text.stderr.decode()
    assert f"Hesaplanan SHA-256: {sha(DATA)} ({len(DATA)} bayt)" in message
    machine = run(rig, certificates, command(rig, "--sha256", "00" * 32, output="json"))
    details = error_of(machine)["details"]
    assert details == {"computed_sha256": sha(DATA), "bytes": len(DATA)}  # the same, unchanged
    assert "Hesaplanan" not in machine.stderr.decode()


def test_a_target_that_exists_is_exit_2_and_nothing_is_asked_of_the_network(rig, certificates):
    rig.target.write_bytes(b"mine")
    process = run(rig, certificates, command(rig, output="json"))
    assert process.returncode == 2 and error_of(process)["code"] == "download_output_exists"
    assert rig.server.requests == [] and rig.target.read_bytes() == b"mine"


@pytest.mark.parametrize(
    "extra,replace",
    [
        ([], {"fmt": "gguf"}),
        ([], {"fmt": "ONNX"}),
        (["--fold", "01"], {}),
        (["--fold", "1025"], {}),
        (["--fold", "-1"], {}),
        (["--fold", "1", "--fold", "2"], {}),  # a repeated option
        (["--timeout", "29"], {}),
        (["--timeout", "3601"], {}),
        (["--timeout", "9e2"], {}),
        (["--sha256", "A" * 64], {}),
        (["--sha256", "a" * 63], {}),
        (["--no-resume", "--no-resume"], {}),
        (["--weights", "x"], {}),  # an abbreviation of --weights-out
        (["--unknown"], {}),
        ([], {"version": "not-a-uuid"}),
        ([], {"version": VERSION.replace("0", "O")}),
    ],
    ids=lambda value: " ".join(value) if isinstance(value, list) else str(sorted(value.items())),
)
def test_a_wrong_value_or_option_is_exit_2_invalid_request_and_the_key_is_not_read(
    rig, certificates, extra, replace
):
    process = run(
        rig,
        certificates,
        command(rig, *extra, output="json", **replace),
        extra_env={ENV: ""},  # an empty key would be a different, later error
    )
    assert process.returncode == 2 and error_of(process)["code"] == "invalid_request"
    assert rig.server.requests == [] and rig.names() == []


def test_a_missing_required_option_is_exit_2(rig, certificates):
    args = [a for a in command(rig, output="json") if a not in ("--weights-out", str(rig.target))]
    process = run(rig, certificates, args)
    assert process.returncode == 2 and error_of(process)["code"] == "invalid_request"


def test_a_missing_key_is_a_closed_credential_error_and_no_request_is_made(rig, certificates):
    env = environment()
    env.pop(ENV, None)
    process = subprocess.run(
        argv(rig, certificates, command(rig, output="json")),
        env={k: v for k, v in env.items() if k != ENV},
        capture_output=True,
        timeout=60,
    )
    assert process.returncode != 0 and rig.server.requests == []
    assert error_of(process)["code"] in {"credential_unavailable", "credential_missing"}


def test_a_statuses_error_goes_to_stderr_and_the_exit_code_is_the_codes(certificates, workspace):
    reply = Reply(status=403, body=b'{"detail":"PRIVATE-DETAIL"}')
    with Rig(certificates, workspace, route=lambda record, count: reply) as rig:
        process = run(rig, certificates, command(rig, output="json"))
        assert process.returncode == 3 and error_of(process)["code"] == "remote_access_denied"
        assert b"PRIVATE-DETAIL" not in process.stderr and rig.signed() == []


# --- resuming -------------------------------------------------------------------------------------


def test_a_cut_download_is_resumed_by_the_same_command_and_the_text_says_so(rig, certificates):
    rig.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),), truncate_at=CUT)]
    first = run(rig, certificates, command(rig, output="json"))
    assert first.returncode == 1 and error_of(first)["code"] == "download_incomplete"
    names = download_names(NAME)
    assert rig.names() == sorted([names.stage, names.sidecar])
    second = run(rig, certificates, command(rig))
    text = stdout_of(second)
    assert second.returncode == 0 and rig.target.read_bytes() == DATA
    assert f"yarım kalan indirmeden {CUT} bayttan devam edildi" in text
    assert rig.provider.seen == [(None, None), (f"bytes={CUT}-", TAG)]


def test_a_whole_stage_is_published_by_the_command_with_no_request_and_the_text_says_so(
    rig, certificates
):
    rig.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),))]

    def interrupted(held, total):
        if held >= len(DATA) - 1:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        rig.call(progress=interrupted)
    before = len(rig.server.requests)
    process = run(rig, certificates, command(rig))
    assert process.returncode == 0 and rig.target.read_bytes() == DATA
    assert len(rig.server.requests) == before  # not even the JSON call
    assert "ağ isteği yapılmadan yayımlandı" in stdout_of(process)
    assert rig.names() == [NAME]


def test_no_resume_starts_over_and_the_text_says_it_was_downloaded_afresh(rig, certificates):
    rig.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),), truncate_at=CUT)]
    assert run(rig, certificates, command(rig, output="json")).returncode == 1
    process = run(rig, certificates, command(rig, "--no-resume"))
    assert process.returncode == 0 and "baştan indirildi" in stdout_of(process)
    assert rig.provider.seen[-1] == (None, None)


def test_a_trace_that_is_not_ours_stops_the_command_and_the_message_names_no_file(
    rig, certificates
):
    names = download_names(NAME)
    (rig.directory / names.sidecar).mkdir()  # a directory where the sidecar belongs
    process = run(rig, certificates, command(rig, output="json"))
    envelope = error_of(process)
    assert process.returncode == 2 and envelope["code"] == "download_partial_unverified"
    assert "Hiçbir dosyaya dokunulmadı" in envelope["message"] and names.sidecar not in str(
        envelope
    )
    assert rig.server.requests == []


@pytest.mark.parametrize("given", [False, True], ids=["without", "with --no-resume"])
def test_the_advice_for_a_trace_that_is_not_ours_does_not_ask_for_what_was_already_given(
    rig, certificates, given
):
    (rig.directory / download_names(NAME).sidecar).mkdir()
    process = run(rig, certificates, command(rig, *(["--no-resume"] if given else [])))
    assert process.returncode == 2
    message = process.stderr.decode()
    assert ("--no-resume zaten verildi" in message) is given
    assert rig.server.requests == []


# --- signals and closed streams -------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal contract")
def test_an_interrupt_during_the_body_is_exit_6_prints_no_result_and_the_next_run_resumes(
    certificates, workspace
):
    slow = Reply(body=DATA, headers=(("ETag", TAG),), chunk_size=65536, chunk_delay=0.25)
    with Rig(certificates, workspace) as rig:
        rig.provider.script = [slow]
        process = popen(rig, certificates, command(rig, output="json"))
        try:
            end = time.monotonic() + 60
            while (
                time.monotonic() < end and not (rig.directory / download_names(NAME).stage).exists()
            ):
                time.sleep(0.05)
            time.sleep(1.0)  # some bytes are written and checkpointed or at least held
            process.send_signal(signal.SIGINT)
            stdout, stderr = process.communicate(timeout=60)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
        assert process.returncode == 6 and stdout == b""
        assert json.loads(stderr)["code"] == "request_cancelled"
        assert not rig.target.exists()
        assert_nothing_private(stdout, stderr, rig=rig)
        rig.provider.script = []
        finished = run(rig, certificates, command(rig, output="json"))
        assert finished.returncode == 0 and rig.target.read_bytes() == DATA


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal contract")
def test_a_closed_stdout_after_the_publication_is_exit_6_and_the_file_is_whole(rig, certificates):
    process = popen(rig, certificates, command(rig, output="json"))
    assert process.stdout is not None
    process.stdout.close()
    try:
        assert process.wait(timeout=120) == 6
        stderr = process.stderr.read()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stderr.close()
    assert json.loads(stderr)["code"] == "output_closed"
    assert rig.target.read_bytes() == DATA and rig.names() == [NAME]  # whole, and said so


# --- the progress line ----------------------------------------------------------------------------


class Terminal(io.StringIO):
    def isatty(self):
        return True


def test_progress_is_one_rewritten_line_on_a_terminal_and_ends_with_a_newline():
    stream = Terminal()
    progress = ProgressText(stream)
    assert progress.enabled
    progress(0, 1000)
    progress(500, 1000)
    progress(1000, 1000)
    progress.close()
    text = stream.getvalue()
    assert text.startswith("\rİndiriliyor: 0 / 1000 bayt (%0)") and text.endswith("(%100)\n")
    assert text.count("\r") == 3 and text.count("\n") == 1
    progress.close()
    assert stream.getvalue() == text  # closing twice adds nothing


def test_progress_without_a_total_shows_bytes_only_and_without_a_terminal_nothing():
    stream = Terminal()
    progress = ProgressText(stream)
    progress(4096, None)
    progress(8192, 0)
    assert "4096 bayt" in stream.getvalue() and "%" not in stream.getvalue()
    quiet = io.StringIO()  # not a terminal
    silent = ProgressText(quiet)
    silent(1, 2)
    silent.close()
    assert not silent.enabled and quiet.getvalue() == ""


def test_a_progress_line_that_cannot_be_written_silences_itself_and_never_raises():
    class Broken(Terminal):
        def write(self, text):
            raise OSError("closed")

    broken = Broken()
    progress = ProgressText(broken)
    progress(1, 2)  # the failure is swallowed ...
    assert progress.enabled is False  # ... and the line stays quiet from here on
    progress(2, 2)
    progress.close()


def test_the_progress_receiver_is_given_only_to_text_on_a_terminal(monkeypatch):
    from yorunge import api
    from yorunge.cli import main

    seen = []

    from yorunge.domain.errors import YorungeError

    def failing(*args, **kwargs):
        seen.append(kwargs["progress"])
        raise YorungeError("invalid_request")

    monkeypatch.setattr(api, "download_model_weights", failing)
    base = [
        "models",
        "download",
        "--version-id",
        VERSION,
        "--format",
        "onnx",
        "--weights-out",
        "/tmp/x.onnx",
    ]
    assert main([*base, "--output", "json"]) == 2 and seen == [None]  # machine output: never
    assert main(base) == 2 and seen == [None, None]  # text, but stderr is not a terminal here
    monkeypatch.setattr(sys, "stderr", Terminal())
    assert main(base) == 2 and isinstance(seen[-1], ProgressText)
