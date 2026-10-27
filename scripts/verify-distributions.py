"""Inspect allowlisted archives, then install and exercise each in a clean environment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ALLOWED_SDIST = {
    ".gitignore",
    ".github",
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


def inspect_archive(path: Path) -> list[str]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as wheel:
            members = wheel.namelist()
        for member in members:
            parts = PurePosixPath(member).parts
            if not parts or (parts[0] != "yorunge" and not parts[0].endswith(".dist-info")):
                raise ValueError("unexpected wheel member")
    else:
        with tarfile.open(path) as sdist:
            members = []
            for item in sdist.getmembers():
                if item.issym() or item.islnk():
                    raise ValueError("archive links are not permitted")
                parts = PurePosixPath(item.name).parts[1:]
                if not parts:
                    continue
                members.append("/".join(parts))
                if parts[0] not in ALLOWED_SDIST:
                    raise ValueError("unexpected sdist member")
                if parts[0] == ".github" and parts[1:] not in (
                    ("workflows", "checks.yml"),
                    ("workflows", "pr-policy.yml"),
                ):
                    raise ValueError("unexpected workflow member")
                if parts[0] == "docs" and not (
                    len(parts) >= 2
                    and (parts[1] in ALLOWED_DOCS or parts[1:] == ("analysis", "README.md"))
                ):
                    raise ValueError("unexpected documentation member")
    if any(
        PurePosixPath(member).is_absolute()
        or ".." in PurePosixPath(member).parts
        or "__pycache__" in PurePosixPath(member).parts
        for member in members
    ):
        raise ValueError("unsafe archive member")
    return members


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uv", required=True, type=Path)
    parser.add_argument("--dist", default=Path("dist"), type=Path)
    args = parser.parse_args()
    uv = str(args.uv.resolve())
    root = Path(__file__).resolve().parents[1]
    packages = sorted(args.dist.resolve().glob("yorunge-*.whl")) + sorted(
        args.dist.resolve().glob("yorunge-*.tar.gz")
    )
    if len(packages) != 2:
        raise ValueError("exactly one wheel and one sdist required")
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
