"""Exercise repository guide checks with isolated synthetic trees, not real user settings."""

import runpy
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/check-agent-guides.py"
SKILL = """---
name: yorunge-example
description: Synthetic instruction-only workflow for a repository task.
---
# Synthetic skill
"""
CARD = """---
id: P01-2a
phase: P01
status: ready
size: S
depends_on: [P01-1]
capabilities: [C01]
---
# Synthetic task
"""


@pytest.fixture
def guide_tree(tmp_path):
    root = tmp_path / "repo"
    skill = root / ".agents/skills/yorunge-example"
    (skill / "agents").mkdir(parents=True)
    (skill / "SKILL.md").write_text(SKILL)
    (skill / "agents/openai.yaml").write_text(
        "interface:\n  default_prompt: Use $yorunge-example to inspect this task.\n"
    )
    aliases = root / ".claude/skills"
    aliases.mkdir(parents=True)
    (aliases / skill.name).symlink_to("../../.agents/skills/yorunge-example")
    (root / "docs/roadmap/tasks").mkdir(parents=True)
    (root / "docs/roadmap/phase-01-core.md").write_text(
        "# Phase\n\n| P01-1 | Package proof | `verified` |\n"
        "| P01-2a | Secret references | `ready` |\n"
    )
    (root / "docs/capability-matrix.md").write_text("# Capabilities\n\n| C01 | Context |\n")
    (root / "docs/roadmap/tasks/p01-2a-synthetic-task.md").write_text(CARD)
    return root


def invoke(root):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        text=True,
        capture_output=True,
        timeout=5,
    )


def test_valid_canonical_guide_alias_and_ready_card(guide_tree):
    result = invoke(guide_tree)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate-name",
        "wrong-name",
        "unsupported-field",
        "bad-ui",
        "missing-frontmatter",
        "unknown-dependency",
        "unverified-dependency",
        "unknown-capability",
        "partial-card",
        "state-drift",
        "large-ready-card",
        "copied-alias",
        "absolute-alias",
        "outside-alias",
    ],
)
def test_malformed_or_unready_guides_fail(guide_tree, mutation, tmp_path):
    skill = guide_tree / ".agents/skills/yorunge-example"
    card = guide_tree / "docs/roadmap/tasks/p01-2a-synthetic-task.md"
    alias = guide_tree / ".claude/skills/yorunge-example"
    if mutation == "duplicate-name":
        (skill / "SKILL.md").write_text(SKILL.replace("description:", "name: other\ndescription:"))
    elif mutation == "wrong-name":
        (skill / "SKILL.md").write_text(SKILL.replace("name: yorunge-example", "name: other"))
    elif mutation == "unsupported-field":
        (skill / "SKILL.md").write_text(
            SKILL.replace("description:", "when-to-use: all\ndescription:")
        )
    elif mutation == "bad-ui":
        (skill / "agents/openai.yaml").write_text("interface: {default_prompt: unrelated}")
    elif mutation == "missing-frontmatter":
        (skill / "SKILL.md").write_text("# No metadata\n")
    elif mutation == "unknown-dependency":
        card.write_text(CARD.replace("[P01-1]", "[P01-99]"))
    elif mutation == "unverified-dependency":
        phase = guide_tree / "docs/roadmap/phase-01-core.md"
        phase.write_text(phase.read_text().replace("verified", "draft"))
    elif mutation == "unknown-capability":
        card.write_text(CARD.replace("C01", "C99"))
    elif mutation == "partial-card":
        card.write_text(CARD.replace("status: ready", "status: partial"))
    elif mutation == "state-drift":
        card.write_text(CARD.replace("status: ready", "status: in_progress"))
    elif mutation == "large-ready-card":
        card.write_text(CARD.replace("size: S", "size: L"))
    else:
        alias.unlink()
        if mutation == "copied-alias":
            alias.mkdir()
            (alias / "SKILL.md").write_text(SKILL)
        elif mutation == "absolute-alias":
            alias.symlink_to(skill)
        else:
            alias.symlink_to(tmp_path)
    result = invoke(guide_tree)
    assert result.returncode == 1
    assert "Traceback" not in result.stdout + result.stderr


def test_canonical_source_directory_cannot_point_to_private_archive(guide_tree):
    skills = guide_tree / ".agents/skills"
    saved = guide_tree / "docs/analysis/private"
    saved.parent.mkdir(parents=True)
    skills.rename(saved)
    skills.symlink_to(saved)
    result = invoke(guide_tree)
    assert result.returncode == 1
    assert "Synthetic instruction" not in result.stdout + result.stderr


def test_code_samples_do_not_create_document_anchors():
    helpers = runpy.run_path(str(SCRIPT.with_name("check-docs.py")))
    anchors = helpers["anchors"](
        "---\nname: example\n---\n# Guide\n\n```md\n# Sample heading\n```\n\n## Actual section\n"
    )
    assert "guide" in anchors and "actual-section" in anchors
    assert "sample-heading" not in anchors
