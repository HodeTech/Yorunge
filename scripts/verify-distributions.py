"""Inspect allowlisted archives, then install and exercise each in a clean environment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ALLOWED_SDIST = {
    ".gitignore",
    ".github",
    ".agents",
    "src",
    "tests",
    "scripts",
    "examples",
    "docs",
    "pyproject.toml",
    "uv.lock",
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "AGENTS.md",
    "CLAUDE.md",
    "CHANGELOG.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "PKG-INFO",
}
ALLOWED_DOCS = {
    "architecture",
    "decisions",
    "modules",
    "reference",
    "standards",
    "roadmap",
    "research",
    "README.md",
    "capability-matrix.md",
    "glossary.md",
    "product-scope.md",
    "project-structure.md",
    "tech-stack.md",
    "user-journeys.md",
    "vision.md",
}


def run(command: list[str], *, cwd: Path, environment: dict[str, str]) -> str:
    return subprocess.run(
        command,
        check=True,
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        timeout=120,
    ).stdout


def archive_parts(name: str, *, directory: bool) -> tuple[str, ...]:
    # Inspect raw segments before PurePosixPath could normalize an unsafe spelling.
    canonical = name[:-1] if directory and name.endswith("/") else name
    parts = tuple(canonical.split("/"))
    if (
        not canonical
        or any(part in ("", ".", "..", "__pycache__") for part in parts)
        or "\\" in name
        or ":" in name
        or any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in name)
    ):
        raise ValueError("unsafe archive member")
    return parts


def check_member_tree(entries: dict[tuple[str, ...], bool]) -> None:
    for parts in entries:
        if any(entries.get(parts[:index]) is False for index in range(1, len(parts))):
            raise ValueError("archive file used as a directory")


def check_sdist_path(parts: tuple[str, ...], *, directory: bool) -> None:
    if parts[0] not in ALLOWED_SDIST:
        raise ValueError("unexpected sdist member")
    if parts[0] == ".github":
        files = (
            (".github", "workflows", "checks.yml"),
            (".github", "workflows", "pr-policy.yml"),
            (".github", "pull_request_template.md"),
        )
        allowed = (
            any(len(parts) < len(item) and parts == item[: len(parts)] for item in files)
            if directory
            else parts in files
        )
    elif parts[0] == ".agents":
        tail = parts[1:]
        allowed = (
            (
                tail in ((), ("skills",))
                or (len(tail) == 2 and tail[0] == "skills")
                or (len(tail) == 3 and tail[0] == "skills" and tail[2] == "agents")
            )
            if directory
            else (
                tail == ("README.md",)
                or (
                    len(tail) >= 3
                    and tail[0] == "skills"
                    and tail[2:] in (("SKILL.md",), ("agents", "openai.yaml"))
                )
            )
        )
    elif parts[0] == "docs":
        allowed = (
            (
                len(parts) == 1
                or (len(parts) >= 2 and parts[1] in ALLOWED_DOCS and not parts[1].endswith(".md"))
                or parts == ("docs", "analysis")
            )
            if directory
            else (
                len(parts) >= 2
                and (
                    (parts[1] in ALLOWED_DOCS and (len(parts) == 2 or not parts[1].endswith(".md")))
                    or parts == ("docs", "analysis", "README.md")
                )
            )
        )
    else:
        tree = parts[0] in ("src", "tests", "scripts", "examples")
        allowed = (tree and (len(parts) > 1 or directory)) or (
            not tree and len(parts) == 1 and not directory
        )
    if not allowed:
        raise ValueError("unexpected sdist member")


def inspect_archive(path: Path) -> list[str]:
    entries: dict[tuple[str, ...], bool] = {}
    members: list[str] = []

    def record(name: str, directory: bool) -> tuple[str, ...]:
        parts = archive_parts(name, directory=directory)
        if parts in entries:
            raise ValueError("duplicate archive member")
        entries[parts] = directory
        return parts

    if path.suffix == ".whl":
        fields = path.name.split("-")
        if len(fields) not in (5, 6) or fields[0] != "yorunge" or not fields[1]:
            raise ValueError("unexpected wheel name")
        metadata = f"yorunge-{fields[1]}.dist-info"
        with zipfile.ZipFile(path) as wheel:
            for item in wheel.infolist():
                # ZipInfo.filename is truncated at NUL; retain the decoded original name.
                name = item.orig_filename
                directory = name.endswith("/")
                parts = record(name, directory)
                kind = stat.S_IFMT(item.external_attr >> 16)
                if kind not in (0, stat.S_IFDIR if directory else stat.S_IFREG) or (
                    item.external_attr & 0x10 and not directory
                ):
                    raise ValueError("archive links and special files are not permitted")
                if parts[0] not in ("yorunge", metadata) or (len(parts) == 1 and not directory):
                    raise ValueError("unexpected wheel member")
                members.append(name)
    elif path.name.endswith(".tar.gz"):
        root = path.name.removesuffix(".tar.gz")
        if not root.startswith("yorunge-") or root == "yorunge-":
            raise ValueError("unexpected sdist name")
        with tarfile.open(path) as sdist:
            for member in sdist.getmembers():
                if not (member.type in (tarfile.REGTYPE, tarfile.AREGTYPE) or member.isdir()):
                    raise ValueError("archive links and special files are not permitted")
                parts = record(member.name, member.isdir())
                if parts[0] != root or (len(parts) == 1 and not member.isdir()):
                    raise ValueError("unexpected sdist root")
                if len(parts) == 1:
                    continue
                relative = parts[1:]
                check_sdist_path(relative, directory=member.isdir())
                members.append("/".join(relative))
    else:
        raise ValueError("expected wheel or sdist")
    check_member_tree(entries)
    if not members or all(entries[parts] for parts in entries):
        raise ValueError("empty distribution")
    return members


def distribution_pair(directory: Path) -> tuple[Path, Path]:
    wheels = sorted(directory.glob("yorunge-*.whl"))
    sdists = sorted(directory.glob("yorunge-*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("exactly one wheel and one sdist required")
    if "-".join(wheels[0].name.split("-")[:2]) != sdists[0].name.removesuffix(".tar.gz"):
        raise ValueError("distribution versions must match")
    return wheels[0], sdists[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uv", required=True, type=Path)
    parser.add_argument("--dist", default=Path("dist"), type=Path)
    args = parser.parse_args()
    uv = str(args.uv.resolve())
    root = Path(__file__).resolve().parents[1]
    packages = distribution_pair(args.dist.resolve())
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["PYTHONNOUSERSITE"] = "1"
    for package in packages:
        members = inspect_archive(package)
        with tempfile.TemporaryDirectory(prefix="yorunge-install-") as directory:
            scratch = Path(directory)
            requirements = scratch / "runtime.txt"
            run(
                [
                    uv,
                    "export",
                    "--frozen",
                    "--no-dev",
                    "--no-emit-project",
                    "--output-file",
                    str(requirements),
                ],
                cwd=root,
                environment=environment,
            )
            venv = scratch / "env"
            run(
                [uv, "venv", str(venv), "--python", sys.executable],
                cwd=scratch,
                environment=environment,
            )
            binaries = venv / ("Scripts" if os.name == "nt" else "bin")
            python = binaries / ("python.exe" if os.name == "nt" else "python")
            console = binaries / ("yorunge.exe" if os.name == "nt" else "yorunge")
            run(
                [
                    uv,
                    "pip",
                    "install",
                    "--python",
                    str(python),
                    "--require-hashes",
                    "-r",
                    str(requirements),
                ],
                cwd=scratch,
                environment=environment,
            )
            run(
                [uv, "pip", "install", "--python", str(python), "--no-deps", str(package)],
                cwd=scratch,
                environment=environment,
            )
            origin = run(
                [str(python), "-I", "-c", "import yorunge; print(yorunge.__file__)"],
                cwd=scratch,
                environment=environment,
            ).strip()
            if not Path(origin).resolve().is_relative_to(venv.resolve()):
                raise ValueError("import did not come from clean environment")
            for option in ("--help", "--version"):
                run([str(console), option], cwd=scratch, environment=environment)
            output = run(
                [
                    str(console),
                    "plan",
                    "prepare",
                    "--task",
                    "llm.train",
                    "--config",
                    str(root / "examples/profile.toml"),
                    "--output",
                    "json",
                ],
                cwd=scratch,
                environment=environment,
            )
            plan = json.loads(output)
            if plan["data"]["executable"] or plan["data"]["selection"]["tool"] != "forgelm":
                raise ValueError("installed plan contract failed")
            print(
                json.dumps(
                    {
                        "archive": package.name,
                        "sha256": hashlib.sha256(package.read_bytes()).hexdigest(),
                        "members": len(members),
                        "origin_verified": True,
                        "smoke": "passed",
                    }
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
