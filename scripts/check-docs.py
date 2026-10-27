"""Check explicitly selected public Markdown sources, without scanning local archives."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ("standards", "architecture", "decisions", "modules", "reference", "roadmap", "research")


def prose(text: str) -> str:
    text = re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)
    return re.sub(r"^(```|~~~).*?^\1[^\n]*$", "", text, flags=re.MULTILINE | re.DOTALL)


def anchors(text: str) -> set[str]:
    result = set()
    counts: dict[str, int] = {}
    for title in re.findall(r"^#{1,6}\s+(.+)$", prose(text), re.MULTILINE):
        slug = re.sub(r"[^\w\s-]", "", title.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(f"{slug}-{count}" if count else slug)
    return result


def main() -> int:
    files = sorted(ROOT.glob("*.md")) + sorted((ROOT / "docs").glob("*.md"))
    files.append(ROOT / "docs" / "analysis" / "README.md")
    for directory in PUBLIC:
        files.extend(sorted((ROOT / "docs" / directory).glob("*.md")))
    files.extend(sorted((ROOT / "docs/roadmap/tasks").glob("*.md")))
    files.extend(sorted((ROOT / ".agents/skills").glob("*/SKILL.md")))
    files.extend([ROOT / ".agents/README.md", ROOT / ".github/pull_request_template.md"])
    problems: list[str] = []
    for path in files:
        resolved = path.resolve()
        if (
            path.is_symlink()
            or not resolved.is_relative_to(ROOT)
            or resolved.is_relative_to(ROOT / "docs/analysis/private")
        ):
            problems.append("public Markdown source escapes its allowed boundary")
            continue
        text = path.read_text()
        name = str(path.relative_to(ROOT))
        body = prose(text).lstrip()
        if not body.startswith("# ") or len(re.findall(r"^# ", body, re.MULTILINE)) != 1:
            problems.append(f"{name}: expected one initial H1")
        if len(re.findall(r"^```", text, re.MULTILINE)) % 2:
            problems.append(f"{name}: unbalanced code fence")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if "://" in target or target.startswith("mailto:"):
                continue
            filename, _, anchor = target.partition("#")
            linked = (path.parent / filename).resolve() if filename else path
            if linked.is_relative_to(ROOT / "docs" / "analysis" / "private"):
                problems.append(f"{name}: link outside public document boundary")
            elif not linked.is_relative_to(ROOT) or not linked.is_file():
                problems.append(f"{name}: missing local link {target}")
            elif anchor and anchor not in anchors(linked.read_text()):
                problems.append(f"{name}: missing anchor {target}")
    for problem in problems:
        print(problem)
    print(f"Checked {len(files)} public Markdown files; {len(problems)} problems.")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
