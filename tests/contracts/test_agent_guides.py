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

## Kullanıcı sonucu ve mevcut eksik
Resolve only the selected synthetic service credential.

## Giren ve girmeyen kapsam
Explicit env lookup; no network or persistence.

## Bağımlılıklar ve kararlar
P01-1 is verified by the phase's historical evidence.

## Sözleşme ve uygulama sınırı
Keep local context independent from credential lookup.

## Kabul
Selected env value is read only on request; missing values fail without leaks.

## Doğrulama
Exercise the real resolver with synthetic env values and a local-context read guard.

## Teslim kaydı
No implementation or delivery evidence yet.
"""
DELIVERY = """- PR/commit: [Synthetic PR](https://github.com/HodeTech/Yorunge/pull/1)
- Sonuç: Synthetic resolver checks passed in the isolated test fixture.
- Kalan sınır: No live service verification.
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
        (skill / "SKILL.md").write_text(
            SKILL.replace("description:", "name: yorunge-example\ndescription:")
        )
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
        phase = guide_tree / "docs/roadmap/phase-01-core.md"
        phase.write_text(phase.read_text().replace("`ready`", "`partial`"))
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
            alias.symlink_to("../../../")
            assert alias.resolve() == tmp_path
    result = invoke(guide_tree)
    assert result.returncode == 1
    assert "Traceback" not in result.stdout + result.stderr


@pytest.mark.parametrize("status", ["in_progress", "in_review", "verified"])
def test_unverified_dependencies_block_started_states(guide_tree, status):
    phase = guide_tree / "docs/roadmap/phase-01-core.md"
    phase.write_text(phase.read_text().replace("verified", "draft").replace("ready", status))
    card = guide_tree / "docs/roadmap/tasks/p01-2a-synthetic-task.md"
    card.write_text(
        CARD.replace("status: ready", f"status: {status}").replace(
            "No implementation or delivery evidence yet.", DELIVERY
        )
    )
    assert invoke(guide_tree).returncode == 1


@pytest.mark.parametrize("field", ["PR/commit", "Sonuç", "Kalan sınır"])
def test_verified_card_requires_each_delivery_field(guide_tree, field):
    phase = guide_tree / "docs/roadmap/phase-01-core.md"
    phase.write_text(phase.read_text().replace("ready", "verified"))
    card = guide_tree / "docs/roadmap/tasks/p01-2a-synthetic-task.md"
    delivery = "\n".join(
        line for line in DELIVERY.splitlines() if not line.startswith(f"- {field}:")
    )
    card.write_text(
        CARD.replace("status: ready", "status: verified").replace(
            "No implementation or delivery evidence yet.", delivery
        )
    )
    assert invoke(guide_tree).returncode == 1


def test_verified_card_with_delivery_record(guide_tree):
    phase = guide_tree / "docs/roadmap/phase-01-core.md"
    phase.write_text(phase.read_text().replace("ready", "verified"))
    card = guide_tree / "docs/roadmap/tasks/p01-2a-synthetic-task.md"
    card.write_text(
        CARD.replace("status: ready", "status: verified").replace(
            "No implementation or delivery evidence yet.", DELIVERY
        )
    )
    result = invoke(guide_tree)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("replacement", ["", "## Kabul\n\n"])
def test_ready_card_requires_nonempty_body_sections(guide_tree, replacement):
    card = guide_tree / "docs/roadmap/tasks/p01-2a-synthetic-task.md"
    card.write_text(
        CARD.replace(
            "## Kabul\nSelected env value is read only on request; "
            "missing values fail without leaks.\n",
            replacement,
        )
    )
    assert invoke(guide_tree).returncode == 1


def test_duplicate_phase_work_ids_fail(guide_tree):
    phase = guide_tree / "docs/roadmap/phase-01-core.md"
    phase.write_text(phase.read_text() + "| P01-1 | Conflicting duplicate | `draft` |\n")
    result = invoke(guide_tree)
    assert result.returncode == 1
    assert "Duplicate phase work id: P01-1" in result.stdout


def test_draft_card_can_have_an_incomplete_body(guide_tree):
    phase = guide_tree / "docs/roadmap/phase-01-core.md"
    phase.write_text(phase.read_text().replace("ready", "draft"))
    card = guide_tree / "docs/roadmap/tasks/p01-2a-synthetic-task.md"
    card.write_text(CARD.split("## Kullanıcı sonucu")[0].replace("status: ready", "status: draft"))
    assert invoke(guide_tree).returncode == 0


def test_canonical_source_directory_cannot_point_to_private_archive(guide_tree):
    skills = guide_tree / ".agents/skills"
    saved = guide_tree / "docs/analysis/private"
    saved.parent.mkdir(parents=True)
    skills.rename(saved)
    skills.symlink_to(saved)
    result = invoke(guide_tree)
    assert result.returncode == 1
    assert "Synthetic instruction" not in result.stdout + result.stderr


def test_code_samples_do_not_create_document_anchors(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    helpers = runpy.run_path(str(SCRIPT.with_name("check-docs.py")))
    anchors = helpers["anchors"](
        "---\nname: example\n---\n# Guide\n\n```md\n# Sample heading\n```\n\n## Actual section\n"
    )
    assert "guide" in anchors and "actual-section" in anchors
    assert "sample-heading" not in anchors


@pytest.mark.parametrize("fence", ["`", "~"])
def test_nested_shorter_fences_and_info_suffix_do_not_close_samples(monkeypatch, fence):
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    helpers = runpy.run_path(str(SCRIPT.with_name("check-docs.py")))
    sample = (
        f"# Guide\n\n{fence * 4}markdown\n{fence * 3}\n# Nested sample\n"
        f"{fence * 4}not-a-closing-fence\n# Still a sample\n"
        f"{fence * 5}\n\n## Actual section\n"
    )
    anchors = helpers["anchors"](sample)
    assert anchors == {"guide", "actual-section"}
    assert helpers["markdown_prose"](sample)[1] is False


def test_unclosed_tilde_fence_is_reported(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    helpers = runpy.run_path(str(SCRIPT.with_name("check-docs.py")))
    assert helpers["markdown_prose"]("# Guide\n\n~~~md\n# Sample\n")[1] is True
