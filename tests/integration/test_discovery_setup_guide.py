"""Execute the documented preparation/launcher with synthetic keys and real TLS CLI."""

import getpass
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from yorunge import api

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs/p02-account-setup.md"
KEYS = {
    "PILOT_LLM_KEY": "synthetic-guide-llm-secret",
    "PILOT_PLATFORM_KEY": "synthetic-guide-plt-secret",
}


def guide_blocks():
    return re.findall(r"(?:python3|\.venv/bin/python) - <<'PY'\n(.*?)\nPY", GUIDE.read_text(), re.S)


def prepare(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in KEYS:
        monkeypatch.delenv(name, raising=False)
    answers = iter([*KEYS.values(), "known-account", "selected-project"])
    monkeypatch.setattr(getpass, "getpass", lambda prompt: next(answers))
    old_umask = os.umask(0o077)
    try:
        exec(compile(guide_blocks()[0], str(GUIDE), "exec"), {})
    finally:
        os.umask(old_umask)
    root = tmp_path / ".local/p02-pilot"
    config = root / "config.toml"
    profile = tomllib.loads(config.read_text())["profiles"]["pilot"]
    assert profile["account_id"] == "known-account"
    assert profile["project_id"] == "selected-project"
    assert json.loads((root / "scope.json").read_text()) == {
        "account_id": "known-account",
        "project_id": "selected-project",
    }
    assert config.stat().st_mode & 0o777 == 0o600
    assert (root / "credentials.json").stat().st_mode & 0o777 == 0o600
    assert root.stat().st_mode & 0o777 == 0o700
    assert not any(key in config.read_text() for key in KEYS.values())
    api.initialize_state(state_dir=root / "state")
    return root


@pytest.mark.parametrize("service", ["evren-llm", "evren-platform"])
def test_documented_first_use_carries_only_selected_key_and_profile_preferences(
    tmp_path, monkeypatch, service, capsys
):
    root = prepare(tmp_path, monkeypatch)
    config = root / "config.toml"
    # Only the TLS target/CA composition changes; the guide's launcher runs unchanged.
    config.write_text(
        config.read_text()
        .replace("evren-llmapi.ssyz.org.tr", "localhost")
        .replace("api.ssyz.org.tr", "localhost")
    )
    cert = certificate(tmp_path / "tls")
    replies = {
        "/v1/terms/status": Reply(
            body=b'{"accepted":false,"current_version":1,"is_material":true,"doc_path":"terms/v1.md"}'
        ),
        "/api/v1/auth/me": Reply(body=b'{"success":true,"data":{"id":"reported-user"}}'),
        "/api/v1/organizations": Reply(body=b'{"items":[],"total":0}'),
        "/api/v1/projects": Reply(body=b'[{"id":"selected-project"}]'),
        "/api/v1/projects/selected-project": Reply(body=b'{"id":"selected-project"}'),
    }
    children = []
    original_run = subprocess.run
    with TlsServer(cert, replies) as server:

        def run(command, *, env, check):
            assert command[:3] == [sys.executable, "-m", "yorunge"]
            assert check is False
            selected = "PILOT_LLM_KEY" if service == "evren-llm" else "PILOT_PLATFORM_KEY"
            assert env[selected] == KEYS[selected]
            assert all(name not in env for name in KEYS if name != selected)
            assert all(key not in " ".join(command) for key in KEYS.values())
            args = command[3:]
            for option in ("--config", "--state-dir"):
                index = args.index(option) + 1
                args[index] = str(Path(args[index]).resolve())
            result = original_run(
                [
                    sys.executable,
                    "-m",
                    "tests.fixtures.discovery_cli",
                    str(server.port),
                    str(cert[0]),
                    *args,
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                timeout=10,
            )
            children.append(result)
            return result

        monkeypatch.setattr(subprocess, "run", run)
        code = guide_blocks()[1].replace('service = "evren-llm"', f'service = "{service}"')
        with loopback_sockets(socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo):
            with pytest.raises(SystemExit) as stopped:
                exec(compile(code, str(GUIDE), "exec"), {})
    assert stopped.value.code == 0, children[0].stderr
    assert len(children) == 1
    child = children[0]
    assert child.stderr == b""
    data = json.loads(child.stdout)["data"]
    assert data["profile_preference"]["account_id"] == "known-account"
    assert data["profile_preference"]["project_id"] == "selected-project"
    assert data["selected"]["project_id"] == (
        "selected-project" if service == "evren-platform" else None
    )
    assert len(server.requests) == (4 if service == "evren-platform" else 1)
    assert all(name not in os.environ for name in KEYS)
    captured = capsys.readouterr()
    assert all(
        key not in captured.out + captured.err + child.stdout.decode() + child.stderr.decode()
        for key in KEYS.values()
    )


def test_documented_launcher_missing_selected_key_stops_before_subprocess(tmp_path, monkeypatch):
    root = prepare(tmp_path, monkeypatch)
    (root / "credentials.json").write_text(
        json.dumps({"PILOT_PLATFORM_KEY": KEYS["PILOT_PLATFORM_KEY"]})
    )

    def forbidden(*args, **kwargs):
        pytest.fail("missing selected key must not launch a child")

    monkeypatch.setattr(subprocess, "run", forbidden)
    with pytest.raises(SystemExit) as stopped:
        exec(compile(guide_blocks()[1], str(GUIDE), "exec"), {})
    assert "hazırlanmamış" in str(stopped.value)
    assert all(key not in str(stopped.value) for key in KEYS.values())


def test_documented_existing_setup_project_migration_uses_real_cli(tmp_path, monkeypatch):
    root = prepare(tmp_path, monkeypatch)
    config = root / "config.toml"
    config.write_text(config.read_text().replace('project_id = "selected-project"\n', ""))
    command = re.search(r"`(\.venv/bin/yorunge context set-project[^`]+)`", GUIDE.read_text())
    assert command is not None
    args = shlex.split(command[1])
    args[0] = str(ROOT / args[0])
    args = ["migrated-project" if value == "PROJECT_ID" else value for value in args]
    result = subprocess.run(args, capture_output=True, timeout=8)
    assert result.returncode == 0, result.stderr
    assert (
        tomllib.loads(config.read_text())["profiles"]["pilot"]["project_id"] == "migrated-project"
    )
    assert json.loads((root / "scope.json").read_text())["project_id"] == "selected-project"
    assert all(key.encode() not in result.stdout + result.stderr for key in KEYS.values())
