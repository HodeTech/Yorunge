"""The installed resume and versions smokes: real commands, closed gates and an unreachable network.

The two smokes run here against the development interpreter exactly as ``verify-distributions``
runs them against a clean installation, so the expected exit codes and error codes are asserted
against the real CLI. The primitives that judge a command are exercised with every kind of damage.
"""

import json
import os
import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
HELPER = runpy.run_path(str(ROOT / "scripts/surface_installation.py"))
SECRET = "synthetic-secret-NEVER-PRINT-48291"
ENVELOPE = {
    "schema_version": 1,
    "code": "invalid_request",
    "message": "synthetic",
    "operation_id": None,
    "retryable": False,
    "details": {},
}


def completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(["synthetic"], returncode, stdout, stderr)


def failure(**changes):
    return completed(2, "", json.dumps({**ENVELOPE, **changes}) + "\n")


def installed_console(directory, environment):
    """The development interpreter and a console that starts it the way the entry point does."""
    python = Path(sys.executable)
    console = directory / "yorunge"
    console.write_text(
        f'#!/bin/sh\nexec "{python}" -I -c "from yorunge.cli import main; '
        'raise SystemExit(main())" "$@"\n'
    )
    console.chmod(0o755)
    scratch = directory / "scratch"
    scratch.mkdir()
    return console, python, scratch, environment


def clean_environment(home):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("PYTHON")}
    environment.update(PYTHONNOUSERSITE="1", HOME=str(home))
    return environment


@pytest.fixture
def installed(tmp_path):
    return installed_console(tmp_path, clean_environment(tmp_path))


@pytest.fixture(scope="module")
def both(tmp_path_factory):
    """Both smokes once, while the caller holds every credential variable; each command is kept."""
    directory = tmp_path_factory.mktemp("surface")
    environment = clean_environment(directory)
    environment |= {name: SECRET for name in (*HELPER["AMBIENT_SECRETS"], HELPER["UNSET_KEY"])}
    console, python, scratch, environment = installed_console(directory, environment)
    namespace = HELPER["verify_resume"].__globals__
    real, issued = namespace["execute"], []

    def record(command, cwd, issued_environment):
        issued.append((command, dict(issued_environment)))
        return real(command, cwd, issued_environment)

    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(namespace, "execute", record)
        results = [
            HELPER["verify_resume"](console, python, scratch, environment),
            HELPER["verify_versions"](console, python, scratch, environment),
        ]
    split = next(
        index for index, (command, _) in enumerate(issued) if "versions-state" in " ".join(command)
    )
    return SimpleNamespace(results=results, resume=issued[:split], versions=issued[split:])


def shape(command):
    """A command without the paths and the guard source: what it asks the product to do."""
    words = [word for word in command[1:] if not word.startswith("/")]
    return " ".join("<guard>" if word.startswith("\nimport sys") else word for word in words)


# --- the real smokes -------------------------------------------------------------------------


def test_both_smokes_pass_against_the_real_cli(both):
    assert both.results == ["passed", "passed"]


def test_the_resume_smoke_asks_what_it_promises(both):
    guard = "-I -c <guard> datasets upload "
    assert [shape(command) for command, _ in both.resume] == [
        "state init --state-dir --output json",
        "datasets upload --help",
        "datasets upload resume --help",
        "datasets upload approve --help",
        *[
            guard + arguments + " --state-dir --output json"
            for arguments in (
                "resume --operation-id " + HELPER["OPERATION"],
                f"approve --plan-id {HELPER['PLAN']} --confirm {HELPER['DIGEST']}",
                "resume --operation-id no",
                f"approve --plan-id no --confirm {HELPER['DIGEST']}",
                f"approve --plan-id {HELPER['PLAN']} --confirm {HELPER['DIGEST'][:-1]}",
            )
        ],
    ]


def test_the_versions_smoke_asks_what_it_promises(both):
    shapes = [shape(command) for command, _ in both.versions]
    assert shapes[:6] == [
        "state init --state-dir --output json",
        "datasets versions --help",
        "datasets versions list --help",
        "datasets versions show --help",
        "datasets versions bind --help",
        "datasets versions check --help",
    ]
    gates = shapes[6:]
    assert all(item.startswith("-I -c <guard> datasets versions ") for item in gates)
    assert [item.split()[5] for item in gates] == [
        "check",
        "list",
        "show",
        "bind",
        "bind",
        "list",
        "bind",
    ]
    assert [command for command, _ in both.versions if "--binding-out" in command]


def test_no_credential_reaches_a_smoke_command_even_when_the_caller_holds_one(both):
    withheld = {*HELPER["AMBIENT_SECRETS"], HELPER["UNSET_KEY"]}
    for command, issued in [*both.resume, *both.versions]:
        assert SECRET not in "".join(issued.values()) + "".join(command)
        assert not withheld & issued.keys()
        assert issued["PYTHONNOUSERSITE"] == "1"


# --- the network is unreachable, not merely unused -----------------------------------------


def test_the_guard_refuses_connections_and_lookups_but_not_sockets_that_stay_local(tmp_path):
    body = """
import os
import socket
import subprocess
import sys

local, other = socket.socketpair()  # the event loop's own wakeup pair stays possible
local.close()
other.close()
plain = socket.socket()
attempts = (
    lambda: plain.connect(("127.0.0.1", 9)),
    lambda: plain.connect_ex(("127.0.0.1", 9)),
    lambda: socket.create_connection(("127.0.0.1", 9)),
    lambda: socket.getaddrinfo("example.invalid", 80),
    lambda: socket.gethostbyname("example.invalid"),
    lambda: socket.gethostbyaddr("127.0.0.1"),
    lambda: socket.getnameinfo(("127.0.0.1", 9), 0),
    lambda: plain.sendto(b"x", ("127.0.0.1", 9)),
    lambda: plain.sendmsg([b"x"], [], 0, ("127.0.0.1", 9)),
    # a child process could reach the network on the command's behalf: it is refused as well
    lambda: subprocess.run([sys.executable, "-c", "pass"]),
    lambda: os.system("true"),
    lambda: os.fork(),
    lambda: os.forkpty(),
    lambda: os.posix_spawn("/usr/bin/true", ["true"], {}),
    lambda: os.execv("/usr/bin/true", ["true"]),
)
for attempt in attempts:
    try:
        attempt()
    except OSError as error:
        assert "forbidden" in str(error), error
    else:
        raise SystemExit("an attempt was not refused")
print("refused")
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", HELPER["GUARD"] + body],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert (result.returncode, result.stdout.strip()) == (0, "refused")
    assert result.stderr.count("attempted") == 15  # every refusal leaves its trace on stderr


def test_an_attempt_the_command_swallows_still_fails_the_smoke(tmp_path):
    body = """
import socket

try:
    socket.getaddrinfo("example.invalid", 80)
except OSError:
    pass  # a command that hides the refusal and goes on
print("carried on")
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", HELPER["GUARD"] + body],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "socket.getaddrinfo attempted" in result.stderr
    # what the gates then see is not a help with an empty stderr, nor one closed envelope
    with pytest.raises(ValueError, match="help failed"):
        HELPER["check_help"](
            completed(0, "options:\n  --one\n", result.stderr), "synthetic", ("--one",)
        )
    with pytest.raises(ValueError):
        HELPER["check_error"](
            completed(2, "", result.stderr + json.dumps(ENVELOPE)),
            "synthetic",
            "invalid_request",
            2,
        )


def test_a_gate_that_reaches_for_the_network_fails_the_smoke_instead_of_passing(installed):
    console, python, scratch, environment = installed
    state = HELPER["initialise"](console, scratch / "state", scratch, environment)
    config = scratch / "config.toml"
    config.write_text(HELPER["PROFILE"], encoding="utf-8")
    keyed = {**environment, HELPER["UNSET_KEY"]: "synthetic-key"}  # now the command has a reason
    listing = ["datasets", "versions", "list", "--dataset-id", HELPER["DATASET"]]
    result = HELPER["guarded"](
        python,
        scratch,
        keyed,
        [*listing, "--config", str(config), "--state-dir", str(state), "--output", "json"],
    )
    # The guard refused the connection (and left its trace), and the product reported it: a closed,
    # different error, as the last line.
    assert "offline smoke: socket." in result.stderr
    assert json.loads(result.stderr.strip().splitlines()[-1])["code"] != "credential_unavailable"
    assert result.returncode not in (0, 3)
    assert result.stdout == ""
    with pytest.raises(ValueError, match="credential_unavailable/3"):
        HELPER["check_error"](result, "list", "credential_unavailable", 3)


def test_the_guard_is_in_front_of_the_real_entry_point(installed):
    _, python, scratch, environment = installed
    result = HELPER["guarded"](python, scratch, environment, ["--version"])
    assert result.returncode == 0
    assert result.stdout.strip()
    assert result.stderr == ""


# --- the primitives that judge a command -----------------------------------------------------


ROWS = "usage: x [--one] [--two]\n\noptions:\n  -h, --help  show this\n  --one ONE   the first\n"


@pytest.mark.parametrize(
    "result,names",
    [
        (completed(0, ROWS + "  --two\n"), ("--one", "--two")),
        (
            completed(0, ROWS + "  -t, --two TWO\n  --three-way\n"),
            ("--one", "--two", "--three-way"),
        ),
        # argparse prints the metavar after the short form too
        (completed(0, ROWS + "  -t TWO, --two TWO\n"), ("--one", "--two")),
    ],
)
def test_a_help_that_defines_every_option_passes(result, names):
    HELPER["check_help"](result, "synthetic", names)


@pytest.mark.parametrize(
    "result,names",
    [
        (completed(1, "  --one\n"), ("--one",)),
        (completed(2, "  --one\n"), ("--one",)),
        (completed(0, "  --one\n", "warning\n"), ("--one",)),
        (completed(0, "  --one\n"), ("--one", "--two")),
        (completed(0, ""), ("--one",)),
        (completed(0, "  --one-more\n"), ("--one",)),
        (completed(0, "  --prefix--one\n"), ("--one",)),
        (completed(0, "x  --one\n"), ("--one",)),
        (completed(0, "  --one\n"), ("--on",)),
        # a mention is not a definition: the usage line, an epilog and another option's help
        (completed(0, "usage: x [--one]\n"), ("--one",)),
        (completed(0, "options:\n  --two  like --one\n\nSee --one.\n"), ("--one",)),
        (completed(0, "options:\n    --one  indented as a continuation\n"), ("--one",)),
    ],
)
def test_a_help_that_fails_is_refused(result, names):
    with pytest.raises(ValueError, match="help failed"):
        HELPER["check_help"](result, "synthetic", names)


def test_the_options_the_surface_promises_are_these():
    # pinned: the tuples are what an installed help is held to
    assert HELPER["UPLOAD_OPTIONS"]["resume"] == (
        "--operation-id",
        "--accept-unverified-read",
        "--prepare",
        "--accept-unconfirmed-effects",
        "--config",
        "--profile",
        "--state-dir",
    )
    assert HELPER["UPLOAD_OPTIONS"]["approve"] == (
        "--plan-id",
        "--confirm",
        "--accept-unconfirmed-effects",
        "--config",
        "--profile",
        "--state-dir",
    )
    shared = ("--config", "--profile", "--state-dir")
    assert HELPER["VERSION_OPTIONS"] == {
        "list": ("--dataset-id", "--page", *shared),
        "show": ("--dataset-id", "--version-tag", *shared),
        "bind": ("--dataset-id", "--version-tag", "--binding-out", "--manifest", *shared),
        "check": ("--binding", *shared),
    }


def test_a_closed_error_passes_and_is_returned():
    value = HELPER["check_error"](failure(), "synthetic", "invalid_request", 2)
    assert value == ENVELOPE


def test_the_envelope_needs_no_trailing_newline():
    HELPER["check_error"](completed(2, "", json.dumps(ENVELOPE)), "synthetic", "invalid_request", 2)


@pytest.mark.parametrize(
    "result",
    [
        failure(code="other_code"),
        failure(schema_version=2),
        failure(schema_version=True),
        failure(schema_version=1.0),
        failure(retryable=True),
        failure(retryable=0),
        failure(retryable=None),
        subprocess.CompletedProcess(["synthetic"], 3, "", json.dumps(ENVELOPE)),
        subprocess.CompletedProcess(["synthetic"], 0, "", json.dumps(ENVELOPE)),
        subprocess.CompletedProcess(["synthetic"], 2, "data\n", json.dumps(ENVELOPE)),
        completed(2, "", ""),
        completed(2, "", "not json"),
        completed(2, "", "[]"),
        completed(2, "", "null"),
        completed(2, "", json.dumps(ENVELOPE) + "\n" + json.dumps(ENVELOPE)),
        completed(2, "", "warning\n" + json.dumps(ENVELOPE)),
        completed(2, "", json.dumps({**ENVELOPE, "extra": 1})),
        completed(2, "", json.dumps({k: v for k, v in ENVELOPE.items() if k != "details"})),
        completed(2, "", json.dumps({k: v for k, v in ENVELOPE.items() if k != "message"})),
    ],
)
def test_anything_but_a_closed_error_is_refused(result):
    with pytest.raises(ValueError, match="did not end closed as invalid_request/2"):
        HELPER["check_error"](result, "synthetic", "invalid_request", 2)


def test_the_error_code_and_the_exit_code_are_both_part_of_the_gate():
    result = failure()
    with pytest.raises(ValueError):
        HELPER["check_error"](result, "synthetic", "invalid_request", 3)
    with pytest.raises(ValueError):
        HELPER["check_error"](result, "synthetic", "credential_unavailable", 2)


@pytest.mark.parametrize(
    "damage", ["exit", "stderr", "not_json", "wrong_status", "no_database", "list"]
)
def test_a_state_directory_that_the_console_did_not_make_is_refused(tmp_path, monkeypatch, damage):
    state = tmp_path / "state"
    ok = json.dumps({"status": "completed"})

    def execute(command, cwd, environment):
        state.mkdir(exist_ok=True)
        if damage != "no_database":
            (state / "state.sqlite3").write_bytes(b"")
        return {
            "exit": completed(1, ok),
            "stderr": completed(0, ok, "warning"),
            "not_json": completed(0, "state ready"),
            "wrong_status": completed(0, json.dumps({"status": "failed"})),
            "no_database": completed(0, ok),
            "list": completed(0, "[]"),
        }[damage]

    monkeypatch.setitem(HELPER["initialise"].__globals__, "execute", execute)
    with pytest.raises(ValueError, match="state init failed"):
        HELPER["initialise"](tmp_path / "console", state, tmp_path, {})


def test_the_environment_loses_exactly_the_credential_variables():
    environment = {
        "PATH": "/bin",
        "EVREN_PLATFORM_API_KEY": "a",
        "EVREN_LLM_API_KEY": "b",
        HELPER["UNSET_KEY"]: "c",
        "EVREN_OTHER": "kept",
    }
    assert HELPER["offline_environment"](environment) == {
        "PATH": "/bin",
        "EVREN_OTHER": "kept",
        "NO_COLOR": "1",  # the one thing it adds: plain help rows on every Python
    }
    assert "EVREN_PLATFORM_API_KEY" in environment  # the caller's own mapping is untouched


# --- defects injected into real runs: the smokes must refuse them ------------------------------


def altered(monkeypatch, edit):
    """Hand each real command's result to ``edit(command, result)`` before the smoke sees it."""
    namespace = HELPER["verify_resume"].__globals__
    real = namespace["execute"]
    monkeypatch.setitem(
        namespace,
        "execute",
        lambda command, cwd, environment: edit(command, real(command, cwd, environment)),
    )


def with_envelope(result, **changes):
    value = json.loads(result.stderr) | changes
    return subprocess.CompletedProcess(result.args, result.returncode, "", json.dumps(value))


def test_a_resume_that_names_another_operation_is_refused(installed, monkeypatch):
    def edit(command, result):
        if HELPER["OPERATION"] in command:
            return with_envelope(result, operation_id=None)
        return result

    altered(monkeypatch, edit)
    with pytest.raises(ValueError, match="did not name the operation"):
        HELPER["verify_resume"](*installed)


@pytest.mark.parametrize("word", ["missing-binding.json", "new-binding.json", "binding-directory"])
def test_a_versions_gate_that_wrote_a_file_is_refused(installed, monkeypatch, word):
    scratch = installed[2]

    def edit(command, result):
        # The product "wrote" where the named gate pointed it: onto the directory, or the new path.
        if any(item.endswith(word) for item in command):
            target = scratch / word
            (target / "stray.json" if target.is_dir() else target).write_text("{}")
        return result

    altered(monkeypatch, edit)
    with pytest.raises(ValueError, match="gate wrote a file"):
        HELPER["verify_versions"](*installed)


@pytest.mark.parametrize("damage", ["code", "exit"])
def test_the_gate_codes_of_the_real_cli_are_what_the_smokes_pin(installed, monkeypatch, damage):
    def edit(command, result):
        if "--operation-id" in command and HELPER["OPERATION"] in command:
            value = json.loads(result.stderr)
            if damage == "code":
                value["code"] = "plan_not_found"
            return subprocess.CompletedProcess(
                result.args,
                0 if damage == "exit" else result.returncode,
                "",
                json.dumps(value),
            )
        return result

    altered(monkeypatch, edit)
    with pytest.raises(ValueError, match="operation_not_found/2"):
        HELPER["verify_resume"](*installed)


def test_the_offline_environment_has_no_secret_and_no_colour():
    environment = HELPER["offline_environment"](
        {
            "PATH": "/bin",
            "EVREN_PLATFORM_API_KEY": "secret",
            "EVREN_LLM_API_KEY": "secret",
            HELPER["UNSET_KEY"]: "x",
            "FORCE_COLOR": "1",
            "NO_COLOR": "0",
        }
    )
    assert environment == {"PATH": "/bin", "NO_COLOR": "1"}  # plain help rows on every Python
