"""Validate canonical skills, Claude aliases and near-term task metadata in a checkout."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml
from markdown_prose import markdown_prose

STATUSES = {"draft", "ready", "in_progress", "in_review", "verified", "blocked", "deferred"}
WORK_ID = re.compile(r"P\d{2}-(?:\d+[a-z]?|R\d+)")
STARTABLE = {"ready", "in_progress", "in_review", "verified"}
CARD_SECTIONS = (
    "Kullanıcı sonucu ve mevcut eksik",
    "Giren ve girmeyen kapsam",
    "Bağımlılıklar ve kararlar",
    "Sözleşme ve uygulama sınırı",
    "Kabul",
    "Doğrulama",
    "Teslim kaydı",
)


def metadata(text: str, *, frontmatter: bool = True) -> dict[str, object]:
    if frontmatter:
        found = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
        if found is None:
            raise ValueError("missing frontmatter")
        text = found.group(1)
    if len(text) > 8192:
        raise ValueError("metadata too large")
    nodes = yaml.compose(text, Loader=yaml.SafeLoader)
    if not isinstance(nodes, yaml.MappingNode):
        raise ValueError("metadata must be a mapping")
    keys = [node.value for node, _ in nodes.value if isinstance(node, yaml.ScalarNode)]
    if len(keys) != len(nodes.value) or len(keys) != len(set(keys)):
        raise ValueError("duplicate or invalid metadata key")
    value: object = yaml.safe_load(text)
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("metadata keys must be strings")
    return {str(key): item for key, item in value.items()}


def trusted_file(path: Path, root: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(root) or resolved.is_relative_to(root / "docs/analysis/private"):
        raise ValueError("guide escapes the public checkout")
    if path.is_symlink():
        raise ValueError("canonical guide must be a regular source")
    return path.read_text(encoding="utf-8")


def check_card_body(text: str, status: object) -> None:
    """Check structure/evidence presence; acceptance quality still needs human review."""
    if status not in STARTABLE:
        return
    # Samples do not supply real card sections or delivery evidence.
    prose, unclosed_fence = markdown_prose(text)
    if unclosed_fence:
        raise ValueError("unclosed task sample fence")
    parts = re.split(r"(?m)^## (.+)\n", prose)
    sections = dict(zip(parts[1::2], parts[2::2], strict=True))
    if any(not sections.get(heading, "").strip() for heading in CARD_SECTIONS):
        raise ValueError("started task needs all nonempty card sections")
    if status == "verified":
        delivery = sections["Teslim kaydı"]
        if not re.search(
            r"(?m)^- PR/commit: .*https://github\.com/HodeTech/Yorunge/"
            r"(?:pull/[1-9]\d*|commit/[0-9a-f]{7,40})(?:[)\s]|$)",
            delivery,
        ) or any(
            not re.search(rf"(?m)^- {field}: \S.*$", delivery) for field in ("Sonuç", "Kalan sınır")
        ):
            raise ValueError("verified task needs delivery link, result and remaining limits")


def check(root: Path) -> tuple[list[str], int, int]:
    root = root.resolve()
    errors: list[str] = []
    for directory in (
        root / ".agents",
        root / ".agents/skills",
        root / ".claude",
        root / ".claude/skills",
        root / "docs/roadmap",
        root / "docs/roadmap/tasks",
    ):
        resolved = directory.resolve()
        if (
            directory.is_symlink()
            or not resolved.is_relative_to(root)
            or resolved.is_relative_to(root / "docs/analysis/private")
        ):
            raise ValueError("guide source directory escapes the public checkout")
    skills = sorted((root / ".agents/skills").glob("*/SKILL.md"))
    if not skills:
        errors.append("No canonical skills found.")
    aliases = root / ".claude/skills"
    if aliases.is_symlink():
        errors.append("Claude skills root must contain per-skill aliases.")
    for path in skills:
        name = path.parent.name
        try:
            spec = metadata(trusted_file(path, root))
            if set(spec) != {"name", "description"} or spec["name"] != name:
                raise ValueError("portable skill metadata mismatch")
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
                raise ValueError("invalid skill name")
            if not isinstance(spec["description"], str) or not spec["description"].strip():
                raise ValueError("missing skill description")
            interface = metadata(
                trusted_file(path.parent / "agents/openai.yaml", root), frontmatter=False
            ).get("interface")
            if not isinstance(interface, dict):
                raise ValueError("missing UI interface")
            prompt = interface.get("default_prompt")
            if not isinstance(prompt, str) or f"${name}" not in prompt:
                raise ValueError("default prompt must invoke its own skill")
            alias = aliases / name
            if not alias.is_symlink() or alias.resolve() != path.parent.resolve():
                raise ValueError("Claude alias does not point to canonical skill")
            if Path(alias.readlink()).is_absolute():
                raise ValueError("Claude alias must be relative")
        except (OSError, ValueError, yaml.YAMLError, RecursionError):
            errors.append(f"Invalid skill metadata, UI or alias: {name}")
    if {item.name for item in aliases.iterdir()} != {path.parent.name for path in skills}:
        errors.append("Claude alias inventory differs from canonical skills.")

    known: dict[str, str] = {}
    capability_ids = set(
        re.findall(
            r"^\| (C\d{2}) \|", trusted_file(root / "docs/capability-matrix.md", root), re.MULTILINE
        )
    )
    for phase in sorted((root / "docs/roadmap").glob("phase-*.md")):
        for line in trusted_file(phase, root).splitlines():
            cells = [cell.strip().strip("`") for cell in line.split("|")[1:-1]]
            if len(cells) >= 2 and WORK_ID.fullmatch(cells[0]):
                if cells[0] in known:
                    errors.append(f"Duplicate phase work id: {cells[0]}")
                else:
                    known[cells[0]] = cells[-1]
    cards = sorted((root / "docs/roadmap/tasks").glob("p*.md"))
    seen: set[str] = set()
    for path in cards:
        try:
            text = trusted_file(path, root)
            spec = metadata(text)
            if set(spec) != {"id", "phase", "status", "size", "depends_on", "capabilities"}:
                raise ValueError("task metadata fields mismatch")
            identifier = spec["id"]
            if not isinstance(identifier, str) or identifier not in known or identifier in seen:
                raise ValueError("unknown or duplicate task id")
            seen.add(identifier)
            if not path.stem.startswith(identifier.lower() + "-"):
                raise ValueError("task filename mismatch")
            if spec["phase"] != identifier.split("-")[0]:
                raise ValueError("task phase mismatch")
            if spec["status"] not in STATUSES or spec["size"] not in {"S", "M", "L"}:
                raise ValueError("invalid task state or size")
            if known[identifier] != spec["status"]:
                raise ValueError("task state differs from phase index")
            if spec["status"] in STARTABLE and spec["size"] == "L":
                raise ValueError("large task must be split before becoming ready")
            check_card_body(text, spec["status"])
            dependencies = spec["depends_on"]
            capabilities = spec["capabilities"]
            if not isinstance(dependencies, list) or not all(
                isinstance(item, str) and item in known for item in dependencies
            ):
                raise ValueError("unknown dependency")
            if (
                not isinstance(capabilities, list)
                or not capabilities
                or not all(
                    isinstance(item, str) and item in capability_ids for item in capabilities
                )
            ):
                raise ValueError("invalid capability id")
            if spec["status"] in STARTABLE and any(
                known[item] != "verified" for item in dependencies
            ):
                raise ValueError("started task has unverified prerequisite")
        except (OSError, ValueError, TypeError, yaml.YAMLError, RecursionError):
            errors.append(f"Invalid task metadata or readiness: {path.name}")
    return errors, len(skills), len(cards)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        errors, skills, cards = check(args.root)
    except (OSError, ValueError):
        print("Guide source inventory is missing or outside the public checkout.")
        return 1
    for error in errors:
        print(error)
    print(f"Checked {skills} skills and {cards} task cards; {len(errors)} problems.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
