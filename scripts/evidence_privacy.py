"""Bounded known-provenance publication guard; not a general PII/secret detector."""

from __future__ import annotations

import argparse
import base64
import binascii
import gzip
import hashlib
import io
import json
import os
import pwd
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

MAX_FILE = 16 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024
MAX_MEMBERS = 512
MAX_DEPTH = 4
MAX_NODES = 200_000
ENCODED_MARKER = re.compile(
    rb"""(?m)(?:["'][A-Za-z_][A-Za-z0-9_]*_base64["']|^\s*[A-Za-z_][A-Za-z0-9_]*_base64)\s*:"""
)
CONTEXT_FIELDS = {
    "schema_version",
    "mode",
    "system_home",
    "effective_home",
    "source_root",
    "workspaces",
    "child_roots",
    "controller",
    "git_author_email",
    "runner",
}


def reject(reason: str) -> NoReturn:
    # Only closed reasons reach diagnostics. Never interpolate a path/value.
    raise ValueError(reason)


def absolute(value: object) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        reject("invalid_context")
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or str(path) != value or value == "/":
        reject("invalid_context")
    return value


def closed(value: object, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        reject("invalid_context")
    return value


def context(root: Path, workspaces: list[Path], children: list[Path], mode: str) -> dict[str, Any]:
    """Collect actual launcher inputs; this private declaration is not an attestation."""
    home = pwd.getpwuid(os.getuid()).pw_dir
    environment_home = os.environ.get("HOME")
    if not environment_home:
        reject("missing_context")
    author = subprocess.run(
        ["git", "-C", str(root), "config", "--get", "user.email"],
        capture_output=True,
        timeout=5,
        check=False,
    )
    if author.returncode not in (0, 1):
        reject("missing_context")
    email = author.stdout.decode("utf-8", "strict").strip() if author.returncode == 0 else None
    if email == "":
        reject("missing_context")
    runner = None
    if mode == "ci":
        if os.environ.get("GITHUB_ACTIONS") != "true":
            reject("invalid_context")
        runner = {
            "home": environment_home,
            "workspace": os.environ.get("GITHUB_WORKSPACE"),
            "temp": os.environ.get("RUNNER_TEMP"),
        }
    value = {
        "schema_version": 1,
        "mode": mode,
        "system_home": home,
        "effective_home": environment_home,
        "source_root": str(root.resolve()),
        "workspaces": [str(path.resolve()) for path in workspaces],
        "child_roots": [str(path.resolve()) for path in children],
        "controller": {
            "executable": str(Path(sys.executable).absolute()),
            "resolved_executable": str(Path(sys.executable).resolve()),
            "prefix": str(Path(sys.prefix).resolve()),
            "temp": tempfile.gettempdir(),
        },
        "git_author_email": {
            "status": "present" if email is not None else "absent",
            "value": email,
        },
        "runner": runner,
    }
    validate_context(value)
    return value


def validate_context(value: object) -> tuple[bytes, ...]:
    data = closed(value, CONTEXT_FIELDS)
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        reject("invalid_context")
    if data["mode"] not in ("local", "ci"):
        reject("invalid_context")
    controller = context_paths(data)
    email = context_email(data["git_author_email"])
    if data["mode"] == "ci":
        validate_runner(data)
        roots = []
    else:
        roots = personal_roots(data, controller)
    if email is not None:
        roots.append(email)
    return tuple(text.encode("utf-8", "strict") for text in sorted(set(roots)))


def context_paths(data: dict[str, Any]) -> dict[str, Any]:
    for name in ("system_home", "effective_home", "source_root"):
        absolute(data[name])
    for name in ("workspaces", "child_roots"):
        paths = data[name]
        if not isinstance(paths, list) or not 1 <= len(paths) <= 16:
            reject("missing_context")
        for path in paths:
            absolute(path)
    controller = closed(data["controller"], {"executable", "resolved_executable", "prefix", "temp"})
    for path in controller.values():
        absolute(path)
    return controller


def context_email(value: object) -> str | None:
    email = closed(value, {"status", "value"})
    address = email["value"]
    if email["status"] == "present":
        if not isinstance(address, str) or not address or len(address) > 1024:
            reject("invalid_context")
        return address
    if email != {"status": "absent", "value": None}:
        reject("invalid_context")
    return None


def validate_runner(data: dict[str, Any]) -> None:
    runner = closed(data["runner"], {"home", "workspace", "temp"})
    for path in runner.values():
        absolute(path)
    if data["system_home"] not in ("/home/runner", "/Users/runner") or (
        runner["home"] != data["effective_home"]
        or runner["home"] != data["system_home"]
        or runner["workspace"] != data["source_root"]
    ):
        reject("invalid_context")


def personal_roots(data: dict[str, Any], controller: dict[str, Any]) -> list[str]:
    if data["runner"] is not None:
        reject("invalid_context")
    roots = [data["system_home"]]
    temporary = controller["temp"]
    if temporary.startswith(("/var/folders/", "/private/var/folders/")):
        roots.append(temporary)
    effective = data["effective_home"]
    if effective != data["system_home"] and effective.startswith(("/Users/", "/home/")):
        roots.append(effective)
    return roots


def neutral_inputs(value: object) -> None:
    """Producer preflight, separate from later byte publication checking."""
    needles = validate_context(value)
    data = closed(value, CONTEXT_FIELDS)
    paths = [data["source_root"], *data["workspaces"], *data["child_roots"]]
    paths.extend(data["controller"].values())
    if any(needle in path.encode() for path in paths for needle in needles):
        reject("personal_runtime_input")


def read_file(path: Path, limit: int = MAX_FILE) -> bytes:
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        reject("unsafe_publication_file")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            reject("publication_limit")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
    finally:
        os.close(descriptor)
    if len(raw) > limit:
        reject("publication_limit")
    return raw


def load_context(path: Path | None) -> dict[str, Any]:
    if path is None:
        reject("missing_context")
    if path.stat().st_mode & 0o077:
        reject("context_not_private")
    value = closed(decode_json(read_file(path, 64 * 1024)), CONTEXT_FIELDS)
    validate_context(value)
    return value


def decode_json(raw: bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                reject("invalid_encoded_evidence")
            result[key] = value
        return result

    def constant(value: str) -> None:
        reject("invalid_encoded_evidence")

    return json.loads(
        raw.decode("utf-8", "strict"), object_pairs_hook=pairs, parse_constant=constant
    )


class Scanner:
    def __init__(self, value: object):
        self.needles = validate_context(value)
        self.total = self.members = self.nodes = 0

    def literal(self, raw: bytes) -> None:
        if any(needle in raw for needle in self.needles):
            reject("personal_provenance")

    def opaque_text(self, raw: bytes) -> None:
        raw.decode("utf-8", "strict")
        if ENCODED_MARKER.search(raw):
            reject("unsupported_encoded_evidence")

    def scan(self, raw: bytes, name: str, depth: int = 0) -> None:
        self.members += 1
        self.total += len(raw)
        if (
            len(raw) > MAX_FILE
            or self.total > MAX_TOTAL
            or self.members > MAX_MEMBERS
            or depth > MAX_DEPTH
        ):
            reject("publication_limit")
        self.literal(raw)
        self.literal(name.encode("utf-8", "strict"))
        if raw.startswith(b"\x1f\x8b"):
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                decoded = stream.read(MAX_FILE + 1)
            self.scan(decoded, name.removesuffix(".gz"), depth + 1)
        elif raw.startswith(b"PK"):
            self.zip(raw, depth)
        elif name.endswith(".jsonl"):
            self.json_lines(raw, depth)
        elif name.endswith(".json") or raw.lstrip().startswith((b"{", b"[")):
            self.tree(decode_json(raw), depth)
        elif name.endswith((".prof", ".pstats")):
            pass  # Opaque binary, scanned as bytes, never deserialized/executed.
        elif name.endswith((".txt", ".log", ".csv")):
            self.opaque_text(raw)
        else:
            reject("unsupported_encoded_evidence")

    def json_lines(self, raw: bytes, depth: int) -> None:
        for line in raw.splitlines():
            if line.strip():
                self.tree(decode_json(line), depth)

    def zip(self, raw: bytes, depth: int) -> None:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_MEMBERS or len({part.filename for part in entries}) != len(
                entries
            ):
                reject("publication_limit")
            for part in entries:
                path = PurePosixPath(part.filename)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or "\\" in part.filename
                    or part.flag_bits & 1
                    or part.file_size > MAX_FILE
                    or part.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                ):
                    reject("unsupported_encoded_evidence")
                if part.is_dir():
                    continue
                with archive.open(part) as stream:
                    content = stream.read(MAX_FILE + 1)
                self.scan(content, part.filename, depth + 1)

    def tree(self, value: Any, depth: int) -> None:
        pending = [(value, 0)]
        while pending:
            item, level = pending.pop()
            self.nodes += 1
            if self.nodes > MAX_NODES or level > 64:
                reject("publication_limit")
            if isinstance(item, str):
                self.literal(item.encode("utf-8", "strict"))
                self.opaque_text(item.encode("utf-8", "strict"))
            elif isinstance(item, list):
                pending.extend((child, level + 1) for child in item)
            elif isinstance(item, dict):
                self.object(item, depth)
                pending.extend((child, level + 1) for child in item.values())

    def object(self, item: dict[str, Any], depth: int) -> None:
        for key in item:
            self.literal(key.encode("utf-8", "strict"))
        encoded = [key for key in item if key.endswith("_base64")]
        if encoded:
            if len(encoded) != 1:
                reject("unsupported_encoded_evidence")
            self.attachment(item, encoded[0], depth)
        for key in ("author", "committer"):
            author = item.get(key)
            if isinstance(author, dict) and author.get("email"):
                reject("author_email_metadata")

    def attachment_fields(self, item: dict[str, Any], key: str) -> tuple[Any, Any, Any]:
        if key == "content_base64":
            if ("bytes" in item) == ("original_bytes" in item) or (
                ("sha256" in item) == ("original_sha256" in item)
            ):
                reject("invalid_encoded_evidence")
            size = item.get("bytes", item.get("original_bytes"))
            digest = item.get("sha256", item.get("original_sha256"))
            name = item.get("name", "original.json")
        elif key == "original_base64":
            size, digest = item.get("original_bytes"), item.get("original_sha256")
            name = item.get("original_filename")
        else:
            reject("unsupported_encoded_evidence")
        return size, digest, name

    def attachment(self, item: dict[str, Any], key: str, depth: int) -> None:
        size, digest, name = self.attachment_fields(item, key)
        text = item[key]
        if (
            type(size) is not int
            or not 0 <= size <= MAX_FILE
            or not isinstance(text, str)
            or len(text) > 4 * ((MAX_FILE + 2) // 3)
            or not isinstance(name, str)
        ):
            reject("invalid_encoded_evidence")
        content = base64.b64decode(text, validate=True)
        if len(content) != size or hashlib.sha256(content).hexdigest() != digest:
            reject("invalid_encoded_evidence")
        self.scan(content, name, depth + 1)


def check(raw: bytes, name: str, value: object) -> None:
    try:
        Scanner(value).scan(raw, name)
    except (
        UnicodeError,
        LookupError,
        RecursionError,
        binascii.Error,
        zipfile.BadZipFile,
        OSError,
        EOFError,
        NotImplementedError,
        zlib.error,
    ):
        raise ValueError("invalid_encoded_evidence") from None


def stage_ci(root: Path, destination: Path, patterns: Path, declaration: Path) -> None:
    """Validate all selected originals before creating any upload directory."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        reject("invalid_context")
    value = load_context(declaration)
    if value["mode"] != "ci":
        reject("invalid_context")
    if str(root.resolve()) != value["source_root"]:
        reject("invalid_context")
    if destination.exists() or destination.is_symlink():
        reject("existing_publication_stage")
    selected = selected_paths(root, patterns)
    scanner, fingerprints = Scanner(value), {}
    for path in sorted(selected):
        raw = read_file(path)
        scanner.scan(raw, path.name)
        fingerprints[path] = hashlib.sha256(raw).digest()
    copy_stage(root, destination, fingerprints)


def selected_paths(root: Path, patterns: Path) -> set[Path]:
    lines = read_file(patterns, 16 * 1024).decode("utf-8", "strict").splitlines()
    selected: set[Path] = set()
    for pattern in lines:
        if not pattern or pattern.startswith("#"):
            continue
        path = PurePosixPath(pattern)
        if path.is_absolute() or ".." in path.parts or "\\" in pattern:
            reject("unsafe_publication_file")
        selected.update(root.glob(pattern))
    if not selected or len(selected) > MAX_MEMBERS:
        reject("publication_limit")
    return selected


def copy_stage(root: Path, destination: Path, fingerprints: dict[Path, bytes]) -> None:
    destination.mkdir(mode=0o700, parents=True)
    try:
        for path, expected in fingerprints.items():
            raw = read_file(path)
            if hashlib.sha256(raw).digest() != expected:
                reject("publication_changed")
            target = destination / path.relative_to(root)
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(raw)
    except BaseException:
        shutil.rmtree(destination)
        raise


def private_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2)
        stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    collect = actions.add_parser("context")
    collect.add_argument("--source-root", type=Path, required=True)
    collect.add_argument("--workspace", type=Path, action="append", required=True)
    collect.add_argument("--child-root", type=Path, action="append", required=True)
    collect.add_argument("--mode", choices=("local", "ci"), required=True)
    collect.add_argument("--output", type=Path, required=True)
    collect.add_argument("--producer-preflight", action="store_true")
    scan = actions.add_parser("check")
    scan.add_argument("--context", type=Path, required=True)
    scan.add_argument("files", type=Path, nargs="+")
    stage = actions.add_parser("stage-ci")
    stage.add_argument("--context", type=Path, required=True)
    stage.add_argument("--source-root", type=Path, required=True)
    stage.add_argument("--patterns", type=Path, required=True)
    stage.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "context":
            value = context(args.source_root, args.workspace, args.child_root, args.mode)
            if args.producer_preflight:
                neutral_inputs(value)
            private_write(args.output, value)
        elif args.action == "stage-ci":
            stage_ci(args.source_root, args.destination, args.patterns, args.context)
        else:
            scanner = Scanner(load_context(args.context))
            for path in args.files:
                scanner.scan(read_file(path), path.name)
    except (
        ValueError,
        OSError,
        UnicodeError,
        LookupError,
        RecursionError,
        binascii.Error,
        zipfile.BadZipFile,
        EOFError,
        subprocess.SubprocessError,
        NotImplementedError,
        zlib.error,
    ):
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if args.action == "stage-ci" and summary:
            try:
                with Path(summary).open("a", encoding="utf-8") as stream:
                    stream.write(
                        "\nEvidence publication blocked. Permanent retention remains OPEN. "
                        "Original files were not uploaded or redacted; CI local files may be "
                        "lost when this ephemeral runner is released.\n"
                    )
            except OSError:
                pass
        print(
            "Evidence publication rejected; preserve originals privately and keep retention open.",
            file=sys.stderr,
        )
        return 1
    print("Known-provenance control passed; not a general PII/secret guarantee.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
