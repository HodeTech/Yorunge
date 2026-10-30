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
from uuid import UUID

GITHUB_DIRECTORY = ".github"
SDIST_SUFFIX = ".tar.gz"
EXAMPLE_PROFILE = "examples/profile.toml"
TRAIN_TASK = "llm.train"

ALLOWED_SDIST = {
    ".gitignore",
    GITHUB_DIRECTORY,
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


def run(
    command: list[str], *, cwd: Path, environment: dict[str, str], expected_code: int = 0
) -> str:
    result = subprocess.run(
        command, check=False, cwd=cwd, env=environment, text=True, capture_output=True, timeout=120
    )
    if result.returncode != expected_code:
        raise subprocess.CalledProcessError(
            result.returncode, command, result.stdout, result.stderr
        )
    return result.stderr if expected_code else result.stdout


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


def check_zip_extra(extra: bytes) -> None:
    offset = 0
    while offset < len(extra):
        if len(extra) - offset < 4:
            raise ValueError("malformed ZIP extra field")
        identifier = int.from_bytes(extra[offset : offset + 2], "little")
        size = int.from_bytes(extra[offset + 2 : offset + 4], "little")
        offset += 4
        if size > len(extra) - offset:
            raise ValueError("malformed ZIP extra field")
        # uv honors this alternate name whereas Python's zipfile exposes the base name.
        if identifier == 0x7075:
            raise ValueError("alternate ZIP member names are not permitted")
        offset += size


def _github_allowed(parts: tuple[str, ...], directory: bool) -> bool:
    files = (
        (GITHUB_DIRECTORY, "workflows", "checks.yml"),
        (GITHUB_DIRECTORY, "workflows", "pr-policy.yml"),
        (GITHUB_DIRECTORY, "pull_request_template.md"),
    )
    if directory:
        return any(len(parts) < len(item) and parts == item[: len(parts)] for item in files)
    return parts in files


def _agents_allowed(parts: tuple[str, ...], directory: bool) -> bool:
    tail = parts[1:]
    if directory:
        return (
            tail in ((), ("skills",))
            or (len(tail) == 2 and tail[0] == "skills")
            or (len(tail) == 3 and tail[0] == "skills" and tail[2] == "agents")
        )
    return tail == ("README.md",) or (
        len(tail) >= 3
        and tail[0] == "skills"
        and tail[2:] in (("SKILL.md",), ("agents", "openai.yaml"))
    )


def _docs_allowed(parts: tuple[str, ...], directory: bool) -> bool:
    if parts[:3] == ("docs", "research", "raw"):
        return False
    if directory:
        return (
            len(parts) == 1
            or (len(parts) >= 2 and parts[1] in ALLOWED_DOCS and not parts[1].endswith(".md"))
            or parts == ("docs", "analysis")
        )
    return len(parts) >= 2 and (
        (parts[1] in ALLOWED_DOCS and (len(parts) == 2 or not parts[1].endswith(".md")))
        or parts == ("docs", "analysis", "README.md")
    )


def check_sdist_path(parts: tuple[str, ...], *, directory: bool) -> None:
    if parts[0] not in ALLOWED_SDIST:
        raise ValueError("unexpected sdist member")
    if parts[0] == GITHUB_DIRECTORY:
        allowed = _github_allowed(parts, directory)
    elif parts[0] == ".agents":
        allowed = _agents_allowed(parts, directory)
    elif parts[0] == "docs":
        allowed = _docs_allowed(parts, directory)
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
                check_zip_extra(item.extra)
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
    elif path.name.endswith(SDIST_SUFFIX):
        root = path.name.removesuffix(SDIST_SUFFIX)
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
    sdists = sorted(directory.glob(f"yorunge-*{SDIST_SUFFIX}"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("exactly one wheel and one sdist required")
    if "-".join(wheels[0].name.split("-")[:2]) != sdists[0].name.removesuffix(SDIST_SUFFIX):
        raise ValueError("distribution versions must match")
    return wheels[0], sdists[0]


def _installed_execution_plan(data: object) -> dict[str, object]:
    if not isinstance(data, dict) or not isinstance(data.get("plan"), dict):
        raise ValueError("installed execution preparation failed")
    plan = data["plan"]
    if (
        plan["schema_version"] != 2
        or plan["mode"] != "execution"
        or plan["executable"]
        or plan["status"] != "draft"
    ):
        raise ValueError("installed execution boundary failed")
    return dict(plan)


def verify_installed_execution(
    console: Path, root: Path, scratch: Path, environment: dict[str, str]
) -> str:
    state_args = ["--state-dir", str(scratch / "state"), "--output", "json"]
    config_args = ["--config", str(root / EXAMPLE_PROFILE)]

    def invoke(action: str, *options: str, expected_code: int = 0) -> dict[str, object]:
        value = json.loads(
            run(
                [str(console), "plan", "execution", action, *options, *state_args],
                cwd=scratch,
                environment=environment,
                expected_code=expected_code,
            )
        )
        if not isinstance(value, dict):
            raise ValueError("installed execution envelope failed")
        return value

    prepared = invoke("prepare", "--task", TRAIN_TASK, *config_args)
    plan = _installed_execution_plan(prepared["data"])
    plan_id, digest = str(plan["plan_id"]), str(plan["digest"])
    listing = invoke("list")["data"]
    if not isinstance(listing, dict) or len(listing["plans"]) != 1:
        raise ValueError("installed execution list failed")
    shown = invoke("show", "--plan-id", plan_id)["data"]
    if not isinstance(shown, dict) or shown["plan"] != plan or shown["validity"] is not None:
        raise ValueError("installed immutable execution show failed")
    validity = invoke("validate", "--plan-id", plan_id, *config_args)["data"]
    if not isinstance(validity, dict) or validity["valid"]:
        raise ValueError("installed blocked execution validation failed")
    missing = invoke("approve", "--plan-id", plan_id, expected_code=4)
    blocked = invoke(
        "approve", "--plan-id", plan_id, "--confirm", digest, *config_args, expected_code=2
    )
    if missing["code"] != "approval_required" or blocked["code"] != "plan_not_valid":
        raise ValueError("installed execution approval errors failed")
    invoke("revoke", "--plan-id", plan_id)
    forgotten = invoke("forget", "--plan-id", plan_id, "--confirm", digest)["data"]
    if not isinstance(forgotten, dict) or not forgotten["forgotten"] or not forgotten["local_only"]:
        raise ValueError("installed execution forget failed")
    listing = invoke("list")["data"]
    if not isinstance(listing, dict) or listing["plans"]:
        raise ValueError("installed execution forget visibility failed")
    return "passed"


def verify_installed_cache(
    console: Path, root: Path, scratch: Path, environment: dict[str, str]
) -> None:
    for mode in ("--refresh", "--cached"):
        cached = json.loads(
            run(
                [
                    str(console),
                    "capabilities",
                    "--task",
                    TRAIN_TASK,
                    mode,
                    "--config",
                    str(root / EXAMPLE_PROFILE),
                    "--state-dir",
                    str(scratch / "state"),
                    "--output",
                    "json",
                ],
                cwd=scratch,
                environment=environment,
            )
        )
        records = cached["data"]["records"]
        if not records or not all(r["hit"] and r["freshness"] == "fresh" for r in records):
            raise ValueError("installed cache contract failed")


def verify_installed_jobs(
    console: Path, python: Path, root: Path, scratch: Path, environment: dict[str, str]
) -> str:
    fixture = scratch / "jobs-state"
    source = (
        "import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); "
        "from tests.fixtures.seed_jobs import seed; print(seed(Path(sys.argv[2]),dense=False))"
    )
    identifier = run(
        [sys.executable, "-c", source, str(root), str(fixture)],
        cwd=root,
        environment=environment,
    ).strip()
    from_source = [str(console), "jobs"]
    listed = json.loads(
        run(
            [*from_source, "list", "--state-dir", str(fixture), "--output", "json"],
            cwd=scratch,
            environment=environment,
        )
    )
    shown = json.loads(
        run(
            [
                *from_source,
                "show",
                "--operation-id",
                identifier,
                "--state-dir",
                str(fixture),
                "--output",
                "json",
            ],
            cwd=scratch,
            environment=environment,
        )
    )
    api_source = (
        "import sys; from pathlib import Path; from yorunge import api; "
        "print(api.show_job(sys.argv[2],state_dir=Path(sys.argv[1])).model_dump_json())"
    )
    api_result = json.loads(
        run(
            [str(python), "-I", "-c", api_source, str(fixture), identifier],
            cwd=scratch,
            environment=environment,
        )
    )
    if (
        shown != api_result
        or listed["data"]["jobs"] != [shown["data"]["operation"]]
        or shown["operation_id"] is not None
        or shown["status"] != "completed"
        or shown["warnings"] != ["local_history_only"]
        or shown["data"]["operation"]["operation_id"] != identifier
        or shown["data"]["operation"]["status"] != "running"
        or len(shown["data"]["attempts"]) != 1
        or shown["data"]["outcome"] is not None
    ):
        raise ValueError("installed jobs CLI/API contract failed")
    text = run(
        [*from_source, "show", "--operation-id", identifier, "--state-dir", str(fixture)],
        cwd=scratch,
        environment=environment,
    )
    if identifier not in text or "güncel uzak durumu yansıtmayabilir" not in text:
        raise ValueError("installed jobs text contract failed")
    return "passed"


def installed_ndjson_payload(output: str) -> object:
    if output.count("\n") != 1 or not output.endswith("\n"):
        raise ValueError("installed NDJSON must contain one complete event")
    event = json.loads(output)
    if not isinstance(event, dict) or set(event) != {
        "schema_version",
        "stream_id",
        "sequence",
        "event",
        "operation_id",
        "payload",
    }:
        raise ValueError("installed NDJSON event shape failed")
    if (
        type(event["schema_version"]) is not int
        or event["schema_version"] != 1
        or type(event["sequence"]) is not int
        or event["sequence"] != 1
        or event["event"] != "result"
        or event["operation_id"] is not None
    ):
        raise ValueError("installed NDJSON event contract failed")
    identifier = UUID(event["stream_id"])
    if identifier.version != 4 or str(identifier) != event["stream_id"]:
        raise ValueError("installed NDJSON stream identity failed")
    return event["payload"]


def verify_installed_ndjson(
    console: Path, root: Path, scratch: Path, environment: dict[str, str]
) -> str:
    command = [str(console), "context", "show", "--config", str(root / EXAMPLE_PROFILE)]
    expected = json.loads(run([*command, "--output=json"], cwd=scratch, environment=environment))
    for option in (["--output", "ndjson"], ["--output=ndjson"]):
        encoded = run([*command, *option], cwd=scratch, environment=environment)
        if installed_ndjson_payload(encoded) != expected:
            raise ValueError("installed NDJSON changed Result v1")
    return "passed"


def verify_installed_transport(
    python: Path, venv: Path, root: Path, scratch: Path, environment: dict[str, str]
) -> dict[str, str]:
    # The parent owns the test TLS server; the worker uses only the installed
    # runtime and asserts every product module/metadata origin in isolated Python.
    result = json.loads(
        run(
            [
                sys.executable,
                "-I",
                str(root / "tests/fixtures/installed_transport.py"),
                "--python",
                str(python),
                "--venv",
                str(venv),
                "--scratch",
                str(scratch),
            ],
            cwd=scratch,
            environment=environment,
        )
    )
    if result != {"http_smoke": "passed", "stream_smoke": "passed"}:
        raise ValueError("installed transport acceptance failed")
    return {"http_smoke": "passed", "stream_smoke": "passed"}


def verify_package(package: Path, uv: str, root: Path, environment: dict[str, str]) -> None:
    members = inspect_archive(package)
    with tempfile.TemporaryDirectory(prefix="yorunge-install-") as directory:
        scratch = Path(directory).resolve()
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
                TRAIN_TASK,
                "--config",
                str(root / EXAMPLE_PROFILE),
                "--output",
                "json",
            ],
            cwd=scratch,
            environment=environment,
        )
        plan = json.loads(output)
        if plan["data"]["executable"] or plan["data"]["selection"]["tool"] != "forgelm":
            raise ValueError("installed plan contract failed")
        ndjson_smoke = verify_installed_ndjson(console, root, scratch, environment)
        transport_smoke = verify_installed_transport(python, venv, root, scratch, environment)
        cache_smoke = "not_run_unsupported_platform"
        execution_smoke = "not_run_unsupported_platform"
        jobs_smoke = "not_run_unsupported_platform"
        if sys.platform in ("darwin", "linux"):
            verify_installed_cache(console, root, scratch, environment)
            cache_smoke = "passed"
            execution_smoke = verify_installed_execution(console, root, scratch, environment)
            jobs_smoke = verify_installed_jobs(console, python, root, scratch, environment)
        print(
            json.dumps(
                {
                    "archive": package.name,
                    "sha256": hashlib.sha256(package.read_bytes()).hexdigest(),
                    "members": len(members),
                    "origin_verified": True,
                    "smoke": "passed",
                    "ndjson_smoke": ndjson_smoke,
                    **transport_smoke,
                    "cache_smoke": cache_smoke,
                    "execution_smoke": execution_smoke,
                    "jobs_smoke": jobs_smoke,
                }
            )
        )


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
        verify_package(package, uv, root, environment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
