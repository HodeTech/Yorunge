"""Git helpers for tests that build throw-away repositories.

Git must not see the caller's environment: a test run from a git hook (``GIT_DIR``,
``GIT_INDEX_FILE``...) would otherwise write its commits into the repository that is being
committed, and a user's global configuration (``diff.ignoreSubmodules``, hooks, signing) would
change the result.
"""

import os
import subprocess
from pathlib import Path


def clean_environment() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_TERMINAL_PROMPT="0",
    )
    return env


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env=clean_environment(),
    ).stdout


def write(repo: Path, name: str, content: str = "x\n") -> None:
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def isolate_git(monkeypatch) -> None:
    """Make the code under test (which runs ``git`` itself) see the same clean environment."""
    for key in [key for key in os.environ if key.startswith("GIT_")]:
        monkeypatch.delenv(key)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
