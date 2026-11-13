"""The documentation lane's classifier: what counts as a document, and when to run everything.

The classifier decides which tests a pull request may skip, so every doubt must end in ``false``
(the full run). The workflow runs the target branch's copy of the script; these tests pin the
script itself against hostile paths, odd git states and the repository's own documentation readers.
"""

import ast
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ci_changes.py"
spec = importlib.util.spec_from_file_location("ci_changes", SCRIPT)
assert spec is not None and spec.loader is not None
ci_changes = importlib.util.module_from_spec(spec)
sys.modules["ci_changes"] = ci_changes
spec.loader.exec_module(ci_changes)

PR = {"EVENT_NAME": "pull_request", "BASE_REF": "development"}


@pytest.mark.parametrize(
    "path",
    [
        "README.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "AGENTS.md",
        "CLAUDE.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "docs/roadmap/current.md",
        "docs/research/raw/p02-3-ci1-linux311-startup.json.gz",
        "docs/research/evidence-manifest.json",
        "docs/a/b/c/d.md",
        ".agents/skills/yorunge-pr/SKILL.md",
    ],
)
def test_documents_are_documents(path):
    assert ci_changes.is_documentation(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "src/yorunge/api.py",
        "tests/contracts/test_ci_changes.py",
        "scripts/ci_changes.py",
        ".github/workflows/checks.yml",
        ".github/workflows/pr-policy.yml",
        "pyproject.toml",
        "uv.lock",
        "examples/profile.toml",
        "LICENSE",
        ".gitignore",
        ".gitattributes",
        ".coderabbit.yaml",
        ".claude/skills/yorunge-pr",
        "README",  # not the document
        "readme.md",  # case-sensitive: a case-insensitive checkout would alias it
        "DOCS/a.md",
        "docs",  # a bare name is a file, not the tree
        ".agents",
        "docs.md",
        "docs-extra/a.md",
        ".agentsx/a.md",
        "src/docs/a.md",  # a nested ``docs`` is source
        "docs/research/probes/x/pilot.py",  # a test runs it (hash pinned): code, not documentation
        "docs/a.py",
        "docs/a.PY",
        "docs/run.sh",
        ".agents/skills/x/run.py",
        "tests/docs/a.md",
        "ROOT/README.md",
    ],
)
def test_everything_else_is_not_a_document(path):
    assert ci_changes.is_documentation(path) is False


@pytest.mark.parametrize(
    "path",
    [
        "",
        " ",
        " docs/a.md",
        "docs/a.md ",
        "docs/a.md\n",
        "docs/\0a.md",
        "docs/a\\b.md",  # a backslash inside a path
        "docs/a\nb.md",  # a newline inside a path
        "docs/a\rb.md",
        "docs\\a.md",
        "/docs/a.md",
        "docs/../src/a.py",
        "docs/./a.md",
        "docs//a.md",
        "docs/a.md/",
        "./docs/a.md",
        "docs/..",
        "../docs/a.md",
        "docs/a/../../src/a.py",
        "docs/a.md\r",
        "docs\\..\\src\\a.py",
    ],
)
def test_odd_spellings_are_never_documents(path):
    assert ci_changes.is_documentation(path) is False


def test_a_change_set_is_documentation_only_when_every_path_is_and_it_is_not_empty():
    assert ci_changes.docs_only(["docs/a.md", "README.md"]) is True
    assert ci_changes.docs_only(path for path in ["docs/a.md"]) is True  # any iterable
    assert ci_changes.docs_only([]) is False
    assert ci_changes.docs_only(["docs/a.md", "src/x.py"]) is False
    assert ci_changes.docs_only(["src/x.py", "docs/a.md"]) is False
    assert ci_changes.docs_only(["docs/a.md", "docs/../src/x.py"]) is False


# --- a real merge checkout --------------------------------------------------------------------


def git(repo, *args):
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def write(repo, name, content="x\n"):
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def merge_checkout(tmp_path, change):
    """A repository whose HEAD is a merge of a feature branch into ``development``."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "development")
    write(repo, "src/a.py", "a\n")
    write(repo, "docs/a.md", "a\n")
    write(repo, "README.md", "a\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    git(repo, "switch", "-q", "-c", "feature")
    change(repo)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", "feature")
    git(repo, "switch", "-q", "development")
    write(repo, "docs/later.md", "the target moved on\n")  # the base is not the merge base
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "moved")
    git(repo, "merge", "-q", "--no-ff", "-m", "merge", "feature")
    return repo


def test_a_documentation_only_merge_is_classified_as_documentation(tmp_path):
    def change(repo):
        write(repo, "docs/a.md", "changed\n")
        write(repo, "docs/new/b.md", "new\n")
        write(repo, "README.md", "changed\n")

    repo = merge_checkout(tmp_path, change)
    # What the pull request adds, not what the target branch moved: ``docs/later.md`` is not in it.
    assert sorted(ci_changes.changed_paths(repo)) == ["README.md", "docs/a.md", "docs/new/b.md"]
    assert ci_changes.classify(PR, repo) is True


@pytest.mark.parametrize(
    "change",
    [
        lambda repo: (write(repo, "docs/a.md", "c\n"), write(repo, "src/a.py", "changed\n")),
        lambda repo: write(repo, "tests/test_new.py", "def test_a(): pass\n"),
        lambda repo: write(repo, ".github/workflows/checks.yml", "name: x\n"),
        lambda repo: write(
            repo, "scripts/ci_changes.py", "# a pull request cannot classify itself\n"
        ),
        lambda repo: write(repo, "pyproject.toml", "[project]\n"),
        lambda repo: (repo / "src/a.py").unlink(),  # a deletion of source
    ],
    ids=["mixed", "test", "workflow", "classifier", "lock", "deleted-source"],
)
def test_anything_that_touches_more_than_documents_runs_the_full_suite(tmp_path, change):
    repo = merge_checkout(tmp_path, change)
    assert not all(ci_changes.is_documentation(path) for path in ci_changes.changed_paths(repo))
    assert ci_changes.classify(PR, repo) is False


def test_moving_a_document_inside_documentation_is_still_documentation(tmp_path):
    repo = merge_checkout(tmp_path, lambda repo: (repo / "docs/a.md").rename(repo / "docs/b.md"))
    assert sorted(ci_changes.changed_paths(repo)) == ["docs/a.md", "docs/b.md"]
    assert ci_changes.classify(PR, repo) is True


def test_a_source_file_moved_into_documentation_is_still_a_source_change(tmp_path):
    def change(repo):
        (repo / "docs/moved.md").parent.mkdir(exist_ok=True)
        (repo / "src/a.py").rename(repo / "docs/moved.md")

    repo = merge_checkout(tmp_path, change)
    # Without rename detection the old path shows up as a deletion of ``src/a.py``.
    assert "src/a.py" in ci_changes.changed_paths(repo)
    assert ci_changes.classify(PR, repo) is False


def test_an_empty_change_set_is_not_documentation(tmp_path):
    repo = merge_checkout(tmp_path, lambda repo: None)  # a feature branch that changes nothing
    assert ci_changes.changed_paths(repo) == []
    assert ci_changes.classify(PR, repo) is False


@pytest.mark.parametrize(
    "environment",
    [
        {},
        {"EVENT_NAME": "push", "BASE_REF": "development"},
        {"EVENT_NAME": "workflow_dispatch", "BASE_REF": "development"},
        {
            "EVENT_NAME": "pull_request",
            "BASE_REF": "Master",
        },  # release aggregation always runs it all
        {"EVENT_NAME": "pull_request", "BASE_REF": ""},
        {"EVENT_NAME": "pull_request"},
        {"BASE_REF": "development"},
        {"EVENT_NAME": "pull_request_target", "BASE_REF": "development"},
        {"EVENT_NAME": "Pull_Request", "BASE_REF": "development"},
    ],
)
def test_only_a_pull_request_into_development_can_be_documentation_only(tmp_path, environment):
    repo = merge_checkout(tmp_path, lambda repo: write(repo, "docs/a.md", "changed\n"))
    assert ci_changes.classify(environment, repo) is False
    assert ci_changes.classify(PR, repo) is True


def test_a_checkout_that_is_not_a_merge_commit_is_never_documentation(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "development")
    write(repo, "docs/a.md", "a\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "one")
    write(repo, "docs/a.md", "b\n")
    git(repo, "add", "-A")
    git(
        repo, "commit", "-q", "-m", "two"
    )  # one parent: the diff is a documentation file, still false
    assert ci_changes.classify(PR, repo) is False


def test_a_directory_that_is_not_a_repository_is_never_documentation(tmp_path):
    assert ci_changes.classify(PR, tmp_path) is False
    assert ci_changes.classify(PR, tmp_path / "missing") is False


def test_the_command_prints_exactly_true_or_false(tmp_path):
    repo = merge_checkout(tmp_path, lambda repo: write(repo, "docs/a.md", "changed\n"))

    def run(environment):
        return subprocess.run(
            [sys.executable, "-I", str(SCRIPT), "classify"],
            cwd=repo,
            env={"PATH": "/usr/bin:/bin:/usr/local/bin", **environment},
            capture_output=True,
            text=True,
        )

    assert run(PR).stdout == "true\n"
    assert run({"EVENT_NAME": "push", "BASE_REF": "development"}).stdout == "false\n"
    assert run({}).stdout == "false\n"
    for arguments in ([], ["other"], ["classify", "extra"], ["docs-tests", "a", "b"]):
        result = subprocess.run(
            [sys.executable, "-I", str(SCRIPT), *arguments], capture_output=True, text=True
        )
        assert result.returncode == 2 and result.stdout == ""


# --- which tests the lane runs ----------------------------------------------------------------


def tree(tmp_path, files):
    for name, content in files.items():
        write(tmp_path, name, content)
    return tmp_path


def test_the_lane_selects_the_tests_that_mention_a_document(tmp_path):
    root = tree(
        tmp_path,
        {
            "tests/contracts/test_a.py": "open('docs/reference/x.md')\n",
            "tests/contracts/test_b.py": "x = 1\n",
            "tests/integration/test_c.py": "p = ROOT / 'README.md'\n",
            "tests/unit/test_d.py": "# docs/reference/x.md is only named in a comment\nx = 1\n",
            "tests/unit/test_e.py": "text = path.read_text()  # changelog entry\nCHANGELOG = 1\n",
            "tests/contracts/__pycache__/test_f.py": "docs/\n",
        },
    )
    assert ci_changes.docs_tests(root) == [
        "tests/contracts/test_a.py",
        "tests/integration/test_c.py",
        "tests/unit/test_e.py",
    ]


@pytest.mark.parametrize(
    "helper",
    ["tests/fixtures/helper.py", "tests/conftest.py", "tests/integration/conftest.py"],
)
def test_a_shared_helper_that_reads_a_document_selects_every_test(tmp_path, helper):
    root = tree(
        tmp_path,
        {
            "tests/contracts/test_a.py": "docs/\n",
            "tests/contracts/test_b.py": "x = 1\n",
            helper: "TEXT = (ROOT / 'docs' / 'a.md').read_text()\n",
        },
    )
    assert ci_changes.docs_tests(root) == ["tests"]


def test_a_comment_in_a_helper_does_not_widen_the_selection(tmp_path):
    root = tree(
        tmp_path,
        {
            "tests/contracts/test_a.py": "docs/\n",
            "tests/fixtures/helper.py": "# see docs/reference/x.md\nX = 1\n",
        },
    )
    assert ci_changes.docs_tests(root) == ["tests/contracts/test_a.py"]


def test_when_nothing_mentions_a_document_the_lane_does_not_guess(tmp_path):
    root = tree(tmp_path, {"tests/contracts/test_a.py": "x = 1\n"})
    assert ci_changes.docs_tests(root) == ["tests"]
    assert ci_changes.docs_tests(tmp_path / "empty") == ["tests"]


def literal_paths(source):
    """String constants that look like a document path, found by the syntax tree (not a regex)."""
    found = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if value.startswith(("docs/", "docs\\")) or value in ("docs", ".agents"):
                found.add(value)
            elif value.endswith(".md") and "/" not in value and value[:1].isupper():
                found.add(value)
    return found


def test_every_test_that_reads_a_document_in_this_repository_is_in_the_lane():
    selection = ci_changes.docs_tests(ROOT)
    assert selection != ["tests"], "the repository's helpers must not force the full run"
    readers = []
    for path in sorted((ROOT / "tests").rglob("test_*.py")):
        if "__pycache__" in path.parts or path == Path(__file__):
            continue
        if literal_paths(path.read_text(encoding="utf-8")):
            readers.append(path.relative_to(ROOT).as_posix())
    assert readers, "the repository really has tests that read documents"
    assert set(readers) <= set(selection), sorted(set(readers) - set(selection))
    # The documents the lane exists for are covered by name as well.
    for name in (
        "tests/integration/test_download_sink_kill.py",
        "tests/contracts/test_agent_guides.py",
    ):
        assert name in selection


# --- merge shapes git can produce that the classifier must not trust --------------------------


def test_an_octopus_merge_is_never_classified_as_documentation(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "development")
    write(repo, "docs/a.md")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    for name in ("one", "two"):
        git(repo, "switch", "-q", "-c", name, "development")
        write(repo, f"docs/{name}.md")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", name)
        git(repo, "switch", "-q", "development")
    git(repo, "merge", "-q", "--no-ff", "-m", "octopus", "one", "two")
    parents = git(repo, "rev-list", "--parents", "-n", "1", "HEAD").split()
    assert len(parents) == 4  # the commit and three parents
    assert ci_changes.classify(PR, repo) is False


def test_a_submodule_change_is_seen_even_when_the_diff_is_told_to_ignore_submodules(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "development")
    write(repo, "docs/a.md")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    git(repo, "switch", "-q", "-c", "feature")
    inner = repo / "src" / "sub"  # a repository inside the work tree is committed as a gitlink
    inner.mkdir(parents=True)
    git(inner, "init", "-q")
    write(inner, "f")
    git(inner, "add", "-A")
    git(inner, "commit", "-q", "-m", "inner")
    git(repo, "add", "src/sub")
    git(repo, "commit", "-q", "-m", "feature")
    git(repo, "switch", "-q", "development")
    shutil.rmtree(inner)  # development must not pick the nested repository up as well
    write(repo, "docs/later.md")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "moved")
    git(repo, "merge", "-q", "--no-ff", "-m", "merge", "feature")
    git(repo, "config", "diff.ignoreSubmodules", "all")
    (repo / ".gitmodules").write_text('[submodule "src/sub"]\n\tpath = src/sub\n\tignore = all\n')
    assert git(repo, "diff", "--name-only", "HEAD^1", "HEAD").strip() == ""  # plain git hides it
    assert ci_changes.changed_paths(repo) == ["src/sub"]
    assert ci_changes.classify(PR, repo) is False


# --- the selection: every form of reference, every kind of reader -----------------------------


@pytest.mark.parametrize(
    "content",
    [
        "open('docs/reference/x.md')",
        "p = ROOT / 'docs'",
        'p = ROOT / "docs"',
        "text = 'README'",
        "text = 'CHANGELOG'",
        "text = 'CONTRIBUTING'",
        "text = 'AGENTS'",
        "text = '.agents'",
        "text = 'SECURITY'",
        "text = 'CODE_OF_CONDUCT'",
        "name = 'guide.md'",
    ],
)
def test_every_form_of_reference_selects_the_test(tmp_path, content):
    root = tree(
        tmp_path,
        {"tests/contracts/test_a.py": content + "\n", "tests/contracts/test_b.py": "x = 1\n"},
    )
    assert ci_changes.docs_tests(root) == ["tests/contracts/test_a.py"]


def test_a_file_name_the_shell_would_split_runs_everything(tmp_path):
    root = tree(
        tmp_path,
        {"tests/contracts/test_a b.py": "docs/\n", "tests/contracts/test_c.py": "docs/\n"},
    )
    assert ci_changes.docs_tests(root) == ["tests"]


def test_a_package_initialiser_that_reads_a_document_runs_everything(tmp_path):
    root = tree(
        tmp_path,
        {
            "tests/contracts/test_a.py": "docs/\n",
            "tests/contracts/__init__.py": "TEXT = open('docs/a.md').read()\n",
        },
    )
    assert ci_changes.docs_tests(root) == ["tests"]


def test_a_test_that_runs_a_script_that_reads_documents_is_selected(tmp_path):
    root = tree(
        tmp_path,
        {
            "scripts/check-things.py": "text = open('docs/a.md').read()\n",
            "scripts/plain_tool.py": "x = 1\n",
            "tests/contracts/test_runs_reader.py": "run('scripts/check-things.py')\n",
            "tests/contracts/test_runs_reader_module.py": "import check_things\n",
            "tests/contracts/test_runs_plain.py": "run('scripts/plain_tool.py')\n",
            "tests/contracts/test_unrelated.py": "x = 1\n",
        },
    )
    assert ci_changes.docs_tests(root) == [
        "tests/contracts/test_runs_reader.py",
        "tests/contracts/test_runs_reader_module.py",
    ]
