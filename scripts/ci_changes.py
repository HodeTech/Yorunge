"""Classify a pull request's change set for the ``core-checks`` workflow.

A pull request that changes only documentation does not need the whole test suite, the native
budgets or the measurement evidence: those depend on code, tests, scripts, the workflow or the
lock file. It still needs everything that can *read* documentation, and this repository has many
such readers (reference contracts are tested against the documents). So the workflow keeps all
three compatibility cells and the required ``offline-core`` aggregate, runs the static checks and
the distribution verification as always, and runs only the tests that reference documentation
instead of the whole suite. Anything that is not provably documentation selects the full run.

    ci_changes.py classify            prints ``true`` or ``false`` (never anything else)
    ci_changes.py docs-tests [ROOT]   prints the test selection of the documentation lane

The workflow runs the copy of this file from the target branch (the first parent of the merge
checkout), never the pull request's own copy, so a pull request cannot classify itself.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

PROTECTED_BASE = "development"
ROOT_DOCUMENTS = frozenset(
    {
        "README.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "AGENTS.md",
        "CLAUDE.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
    }
)
DOCUMENT_TREES = ("docs", ".agents")
# A test that mentions any of these may read a document; selecting too many is safe, too few is not.
DOCUMENT_REFERENCE = re.compile(
    r"docs/|[\"']docs[\"']|README|CHANGELOG|CONTRIBUTING|AGENTS|\.agents|SECURITY|CODE_OF_CONDUCT|\.md\b"
)
RUN_EVERYTHING = "tests"
# The workflow hands the selection to pytest by word splitting: only plain names may be selected.
PLAIN_NAME = re.compile(r"[A-Za-z0-9_./-]+")


def is_documentation(path: str) -> bool:
    """True only for a normalised, repository-relative path that is a document by construction."""
    if not path or path != path.strip() or "\0" in path or "\\" in path or "\n" in path:
        return False
    pure = PurePosixPath(path)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in path.split("/")):
        return False
    if str(pure) != path:
        return False
    if len(pure.parts) == 1:
        return path in ROOT_DOCUMENTS
    return pure.parts[0] in DOCUMENT_TREES


def docs_only(paths: Iterable[str]) -> bool:
    """A non-empty change set made only of documents; an empty or unreadable one is not."""
    seen = list(paths)
    return bool(seen) and all(is_documentation(path) for path in seen)


def _git(*args: str, cwd: Path | None = None) -> bytes:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, cwd=cwd, timeout=60
    ).stdout


def changed_paths(root: Path | None = None) -> list[str]:
    """Paths the merge checkout adds to its first parent (the target branch tip).

    Renames are reported as a deletion and an addition, so a file moved out of the source tree
    still counts as a source change.
    """
    parents = _git("rev-list", "--parents", "-n", "1", "HEAD", cwd=root).split()
    if len(parents) != 3:  # the commit and exactly two parents: a real merge checkout
        raise ValueError("the checkout is not a pull request merge commit")
    raw = _git("diff", "--name-only", "-z", "--no-renames", parents[1].decode(), "HEAD", cwd=root)
    return [item.decode("utf-8", "surrogateescape") for item in raw.split(b"\0") if item]


def classify(environment: dict[str, str] | None = None, root: Path | None = None) -> bool:
    env = os.environ if environment is None else environment
    if env.get("EVENT_NAME") != "pull_request" or env.get("BASE_REF") != PROTECTED_BASE:
        return False
    try:
        return docs_only(changed_paths(root))
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def _code(path: Path) -> str:
    """The file without its full-line comments: a comment that names a document reads nothing."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(line for line in lines if not line.lstrip().startswith("#"))


def docs_tests(root: Path) -> list[str]:
    """The test files that may read a document, or the whole ``tests`` tree when unsure.

    A shared helper that mentions documents (a fixture, a ``conftest``) can be imported by any test,
    so the lane then falls back to everything instead of guessing which tests use it.
    """
    tests = root / "tests"
    selected: list[str] = []
    for path in sorted(tests.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        mentions = DOCUMENT_REFERENCE.search(_code(path))
        if path.name.startswith("test_"):
            if mentions:
                selected.append(path.relative_to(root).as_posix())
        elif mentions and path.name != "__init__.py":
            return [RUN_EVERYTHING]
    if not selected or not all(PLAIN_NAME.fullmatch(name) for name in selected):
        return [RUN_EVERYTHING]
    return selected


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("classify", "docs-tests") or len(argv) > 2:
        sys.stderr.write("usage: ci_changes.py classify | docs-tests [ROOT]\n")
        return 2
    if argv[0] == "classify":
        if len(argv) != 1:
            sys.stderr.write("usage: ci_changes.py classify\n")
            return 2
        sys.stdout.write("true\n" if classify() else "false\n")
        return 0
    root = Path(argv[1]) if len(argv) == 2 else Path.cwd()
    sys.stdout.write("\n".join(docs_tests(root)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
