"""Normal installed CLI NDJSON and UTF-8 metadata under hostile stdio locales."""

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID

import pytest

from yorunge import __version__, api

ROOT = Path(__file__).resolve().parents[2]
CANARY = "synthetic-secret-NEVER-PRINT-48291"


def invoke(*args, metadata=False, blocked=(), ascii_locale=False):
    environment = dict(os.environ)
    environment.update(
        {
            "PYTHONPATH": str(ROOT / "tests" / "fixtures" / "guards"),
            "YORUNGE_TEST_METADATA": "1" if metadata else "0",
            "YORUNGE_TEST_CREDENTIAL": "0",
            "YORUNGE_TEST_STATE": "0",
        }
    )
    if ascii_locale:
        environment.update({"LC_ALL": "C", "PYTHONIOENCODING": "ascii", "PYTHONUTF8": "0"})
    if blocked:
        source = (
            "import sys\n"
            f"blocked = {tuple(blocked)!r}\n"
            "def guard(event, args):\n"
            "    if event == 'import' and any(\n"
            "        args[0] == name or args[0].startswith(name + '.') for name in blocked\n"
            "    ):\n"
            "        raise RuntimeError('forbidden eager output import')\n"
            "sys.addaudithook(guard)\n"
            "from yorunge.cli import main\n"
            "raise SystemExit(main())\n"
        )
        command = [sys.executable, "-c", source, *args]
    else:
        command = [str(Path(sys.executable).parent / "yorunge"), *args]
    return subprocess.run(command, env=environment, capture_output=True, timeout=10)


@pytest.mark.parametrize(
    "args, python",
    [
        (("context", "show"), lambda config: api.show_context(config=config)),
        (
            ("plan", "prepare", "--task", "llm.train"),
            lambda config: api.prepare_plan(task="llm.train", config=config),
        ),
        (("train", "plan"), lambda config: api.prepare_plan(task="llm.train", config=config)),
    ],
)
@pytest.mark.parametrize("option", [("--output", "ndjson"), ("--output=ndjson",)])
def test_installed_normal_command_emits_exactly_one_typed_result(config, args, python, option):
    expected = python(config).model_dump(mode="json")
    completed = invoke(*args, "--config", str(config), *option)
    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == b""
    assert completed.stdout.count(b"\n") == 1
    event = json.loads(completed.stdout)
    assert set(event) == {
        "schema_version",
        "stream_id",
        "sequence",
        "event",
        "operation_id",
        "payload",
    }
    assert event["schema_version"] == 1
    assert event["sequence"] == 1
    assert event["event"] == "result"
    assert event["operation_id"] is None
    identity = UUID(event["stream_id"])
    assert identity.version == 4
    assert str(identity) == event["stream_id"]
    assert event["payload"] == expected
    old_json = invoke(*args, "--config", str(config), "--output=json")
    assert old_json.returncode == 0
    assert json.loads(old_json.stdout) == expected


def test_each_invocation_has_a_fresh_stream_id():
    first = invoke("context", "show", "--output=ndjson")
    second = invoke("context", "show", "--output=ndjson")
    assert first.returncode == second.returncode == 0
    assert json.loads(first.stdout)["stream_id"] != json.loads(second.stdout)["stream_id"]


@pytest.mark.parametrize(
    "args",
    [
        ("--unknown", CANARY, "--output", "ndjson"),
        ("--unknown", CANARY, "--output=ndjson"),
        ("plan", "prepare", "--output=ndjson"),
        ("jobs", "--output=ndjson", "list", "--output=ndjson"),
        ("jobs", "list", "--output", "ndjson", "--config", CANARY),
    ],
)
def test_ndjson_parser_errors_are_plain_json_even_before_flag_is_parsed(args):
    completed = invoke(*args)
    assert completed.returncode == 2
    assert completed.stdout == b""
    error = json.loads(completed.stderr)
    assert set(error) == {
        "schema_version",
        "code",
        "message",
        "operation_id",
        "retryable",
        "details",
    }
    assert error["code"] == "invalid_request"
    assert error["operation_id"] is None
    assert error["details"] == {}
    assert error["retryable"] is False
    assert completed.stderr.count(b"\n") == 1
    assert CANARY.encode() not in completed.stderr
    assert b"Traceback" not in completed.stderr


@pytest.mark.parametrize("output", ["text", "json", "ndjson"])
def test_real_cli_non_ascii_success_and_error_are_utf8_despite_ascii_stdio(output, config):
    completed = invoke(
        "train", "plan", "--config", str(config), "--output", output, ascii_locale=True
    )
    assert completed.returncode == 0
    assert completed.stderr == b""
    text = completed.stdout.decode("utf-8", "strict")
    assert any(ord(character) > 127 for character in text)
    if output != "text":
        assert json.loads(text)["payload" if output == "ndjson" else "data"]
    failed = invoke("--invalid", "--output", output, ascii_locale=True)
    assert failed.returncode == 2
    assert failed.stdout == b""
    error = failed.stderr.decode("utf-8", "strict")
    assert "İstek geçersiz" in error
    assert "Traceback" not in error
    if output != "text":
        assert json.loads(error)["code"] == "invalid_request"


@pytest.mark.parametrize(
    "args",
    [
        ("--help",),
        ("--version",),
        ("train", "plan", "--help"),
        ("plan", "execution", "prepare", "--help"),
        ("jobs", "list", "--help"),
    ],
)
def test_metadata_remains_human_lazy_and_utf8_even_with_ndjson_selected(args):
    completed = invoke(
        "--output=ndjson",
        *args,
        metadata=True,
        ascii_locale=True,
        blocked=(
            "pydantic",
            "httpx",
            "uuid",
            "yorunge.domain.streams",
            "yorunge.application.stream_results",
        ),
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == b""
    assert completed.stdout
    text = completed.stdout.decode("utf-8", "strict")
    if args == ("--version",):
        assert text == f"yorunge {__version__}\n"
    else:
        assert "usage:" in text
        assert "{text,json,ndjson}" in text
    assert not text.startswith("{")
    assert "Traceback" not in text


@pytest.mark.parametrize("output", ["text", "json"])
def test_existing_local_output_does_not_load_stream_codec(output):
    completed = invoke(
        "context",
        "show",
        "--output",
        output,
        blocked=("yorunge.domain.streams", "yorunge.application.stream_results"),
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout
    assert completed.stderr == b""
