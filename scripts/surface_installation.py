"""Installed offline smokes of the resume and versions surfaces; no network, no credential.

Both run against one clean installation (``python -I`` and the installed console) with a fresh
state directory. Every gate is asserted by its closed error (exit code, empty stdout, one JSON
envelope on stderr), and the gates run behind an audit hook that makes any connection or name
resolution fail: an installed command that reached for the network cannot pass by accident.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

OPERATION = "11111111-1111-4111-8111-111111111111"  # valid, and held by no store
PLAN = "22222222-2222-4222-8222-222222222222"
DATASET = "33333333-3333-4333-8333-333333333333"
DIGEST = "ab" * 32
UNSET_KEY = "YORUNGE_INSTALLED_SMOKE_UNSET_KEY"  # names no variable of any real environment
AMBIENT_SECRETS = ("EVREN_PLATFORM_API_KEY", "EVREN_LLM_API_KEY")
ENVELOPE = {"schema_version", "code", "message", "operation_id", "retryable", "details"}
GUARD = """
import sys

DENIED = frozenset(
    (
        "socket.connect",
        "socket.getaddrinfo",
        "socket.gethostbyname",
        "socket.gethostbyaddr",
        "socket.getnameinfo",
        "socket.sendto",
    )
)


def deny(event, arguments):
    if event in DENIED:
        # Refusing is not enough: a command that catches the OSError and goes on would pass. The
        # attempt leaves a line on stderr, which no closed gate and no help may have.
        sys.stderr.write("offline smoke: " + event + " attempted\\n")
        raise OSError("network access is forbidden in this offline installed smoke")


sys.addaudithook(deny)
"""
GUARDED_MAIN = GUARD + "from yorunge.cli import main\nraise SystemExit(main())\n"
PROFILE = (
    'schema_version = 1\nactive_profile = "smoke"\n[profiles.smoke]\n'
    f'platform_key_env = "{UNSET_KEY}"\n'
)
SHARED = ("--config", "--profile", "--state-dir")
UPLOAD_OPTIONS = {
    "resume": (
        "--operation-id",
        "--accept-unverified-read",
        "--prepare",
        "--accept-unconfirmed-effects",
        *SHARED,
    ),
    "approve": ("--plan-id", "--confirm", "--accept-unconfirmed-effects", *SHARED),
}
VERSION_OPTIONS = {
    "list": ("--dataset-id", "--page", *SHARED),
    "show": ("--dataset-id", "--version-tag", *SHARED),
    "bind": ("--dataset-id", "--version-tag", "--binding-out", "--manifest", *SHARED),
    "check": ("--binding", *SHARED),
}


def offline_environment(environment: dict[str, str]) -> dict[str, str]:
    """The caller's environment minus every credential variable a gate could be mistaken to use."""
    withheld = {*AMBIENT_SECRETS, UNSET_KEY}
    return {name: value for name, value in environment.items() if name not in withheld}


def execute(
    command: list[str], cwd: Path, environment: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )


def defined_options(text: str) -> set[str]:
    """The options a help DEFINES: the rows of its option list, never a mention in prose.

    An option that was renamed or dropped can still be named by the usage line, the epilog or the
    help of another option; only a row of the list (two-space indent, an optional short form) is a
    definition.
    """
    return set(re.findall(r"^  (?:-\w, )?(--[\w-]+)", text, flags=re.MULTILINE))


def mentions(text: str, name: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text) is not None


def check_help(
    result: subprocess.CompletedProcess[str], label: str, names: tuple[str, ...]
) -> None:
    """``--help`` ends 0 with nothing on stderr and defines every option the surface promises.

    An option (``--name``) must be a row of the option list; a command name (a subcommand of a
    group) is a word of the help, since the group lists its subcommands in prose-like rows.
    """
    defined = defined_options(result.stdout)
    missing = [
        name
        for name in names
        if (name not in defined if name.startswith("-") else not mentions(result.stdout, name))
    ]
    if result.returncode != 0 or result.stderr or missing:
        raise ValueError(
            f"installed {label} help failed: exit {result.returncode}, "
            f"stderr {result.stderr[:120]!r}, missing {missing}"
        )


def check_error(
    result: subprocess.CompletedProcess[str], label: str, code: str, exit_code: int
) -> dict[str, Any]:
    """A closed failure: the exit code, no stdout, and exactly one error envelope on stderr."""
    try:
        value = json.loads(result.stderr)
    except ValueError:
        value = None
    if (
        result.returncode != exit_code
        or result.stdout
        or not isinstance(value, dict)
        or set(value) != ENVELOPE
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["code"] != code
        or value["retryable"] is not False
    ):
        raise ValueError(
            f"installed {label} did not end closed as {code}/{exit_code}: exit "
            f"{result.returncode}, stdout {result.stdout[:80]!r}, stderr {result.stderr[:200]!r}"
        )
    return dict(value)


def initialise(console: Path, state: Path, scratch: Path, environment: dict[str, str]) -> Path:
    """A fresh state directory made by the installed console itself."""
    result = execute(
        [str(console), "state", "init", "--state-dir", str(state), "--output", "json"],
        scratch,
        environment,
    )
    try:
        value = json.loads(result.stdout)
    except ValueError:
        value = None
    if (
        result.returncode != 0
        or result.stderr
        or not isinstance(value, dict)
        or value.get("status") != "completed"
        or not (state / "state.sqlite3").is_file()
    ):
        raise ValueError(f"installed state init failed: exit {result.returncode}")
    return state


def guarded(
    python: Path, scratch: Path, environment: dict[str, str], arguments: list[str]
) -> subprocess.CompletedProcess[str]:
    """The installed CLI entry point under ``-I``, with the network made unreachable."""
    return execute([str(python), "-I", "-c", GUARDED_MAIN, *arguments], scratch, environment)


def verify_resume(console: Path, python: Path, scratch: Path, environment: dict[str, str]) -> str:
    """``datasets upload resume`` and ``approve``: their help and every local gate, offline."""
    env = offline_environment(environment)
    state = initialise(console, scratch / "resume-state", scratch, env)
    common = ["--state-dir", str(state), "--output", "json"]
    check_help(
        execute([str(console), "datasets", "upload", "--help"], scratch, env),
        "datasets upload",
        ("plan", "approve", "start", "reconcile", "resume"),
    )
    for action, names in UPLOAD_OPTIONS.items():
        check_help(
            execute([str(console), "datasets", "upload", action, "--help"], scratch, env),
            "datasets upload " + action,
            names,
        )

    def gate(label: str, arguments: list[str], code: str) -> dict[str, Any]:
        result = guarded(python, scratch, env, ["datasets", "upload", *arguments, *common])
        return check_error(result, label, code, 2)

    missing = gate(
        "resume of a missing operation",
        ["resume", "--operation-id", OPERATION],
        "operation_not_found",
    )
    if missing["operation_id"] != OPERATION:
        raise ValueError("installed resume did not name the operation it was asked about")
    gate(
        "approve of a missing plan",
        ["approve", "--plan-id", PLAN, "--confirm", DIGEST],
        "upload_plan_not_found",
    )
    gate("resume of a malformed operation", ["resume", "--operation-id", "no"], "invalid_request")
    gate(
        "approve of a malformed plan",
        ["approve", "--plan-id", "no", "--confirm", DIGEST],
        "invalid_request",
    )
    gate(
        "approve with a malformed digest",
        ["approve", "--plan-id", PLAN, "--confirm", DIGEST[:-1]],
        "invalid_request",
    )
    return "passed"


def verify_versions(console: Path, python: Path, scratch: Path, environment: dict[str, str]) -> str:
    """``datasets versions``: every action's help and its local gates, with no credential set."""
    env = offline_environment(environment)
    state = initialise(console, scratch / "versions-state", scratch, env)
    config = scratch / "versions-config.toml"
    config.write_text(PROFILE, encoding="utf-8")
    common = ["--config", str(config), "--state-dir", str(state), "--output", "json"]
    check_help(
        execute([str(console), "datasets", "versions", "--help"], scratch, env),
        "datasets versions",
        tuple(VERSION_OPTIONS),
    )
    for action, names in VERSION_OPTIONS.items():
        check_help(
            execute([str(console), "datasets", "versions", action, "--help"], scratch, env),
            "datasets versions " + action,
            names,
        )

    def gate(label: str, arguments: list[str], code: str, exit_code: int) -> None:
        result = guarded(python, scratch, env, ["datasets", "versions", *arguments, *common])
        check_error(result, label, code, exit_code)

    missing, taken = scratch / "missing-binding.json", scratch / "binding-directory"
    created = scratch / "new-binding.json"
    taken.mkdir()
    gate("check of a missing binding", ["check", "--binding", str(missing)], "file_unreadable", 2)
    tag = ["--version-tag", "v1"]
    for action, options in (
        ("list", ["--dataset-id", DATASET]),
        ("show", ["--dataset-id", DATASET, *tag]),
        ("bind", ["--dataset-id", DATASET, *tag, "--binding-out", str(created)]),
    ):
        gate(f"{action} without a key", [action, *options], "credential_unavailable", 3)
    gate(
        "bind onto a directory",
        ["bind", "--dataset-id", DATASET, *tag, "--binding-out", str(taken)],
        "binding_output_exists",
        2,
    )
    gate("list of a malformed dataset", ["list", "--dataset-id", "no"], "invalid_request", 2)
    gate(
        "bind of a malformed dataset",
        ["bind", "--dataset-id", "no", *tag, "--binding-out", str(created)],
        "invalid_request",
        2,
    )
    if created.exists() or missing.exists() or list(taken.iterdir()):
        raise ValueError("an installed versions gate wrote a file")
    return "passed"
