"""Bind dataset measurements to wheel product bytes and installed metadata."""

from __future__ import annotations

import configparser
import hashlib
import importlib.metadata
import os
import re
import runpy
import stat
import zipfile
from email import policy
from email.parser import BytesParser
from pathlib import Path

METADATA_FILES = ("METADATA", "WHEEL", "entry_points.txt")
PRODUCT_NAME = "yorunge"
MAX_WHEEL_BYTES = 64 * 1024 * 1024
MAX_MEMBER_BYTES = 8 * 1024 * 1024


def state(info: os.stat_result) -> tuple[int, ...]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def installed_metadata(prefix: Path, version: str) -> dict[str, str]:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+!-]{0,127}", version, flags=re.ASCII) is None:
        raise ValueError("invalid installed distribution version")
    distribution = importlib.metadata.distribution(PRODUCT_NAME)
    if distribution.version != version:
        raise ValueError("installed dataset distribution differs from frozen version")
    hashes = {}
    for name in METADATA_FILES:
        path = Path(str(distribution.locate_file(f"yorunge-{version}.dist-info/{name}")))
        if path.is_symlink() or not path.resolve().is_relative_to(prefix.resolve()):
            raise ValueError("dataset metadata escaped the installed environment")
        with path.open("rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise ValueError("installed dataset metadata is not a regular file")
            content = source.read(MAX_MEMBER_BYTES + 1)
        if len(content) > MAX_MEMBER_BYTES:
            raise ValueError("installed dataset metadata exceeded its bound")
        hashes[name] = hashlib.sha256(content).hexdigest()
    return hashes


class EntryPoints(configparser.ConfigParser):
    def optionxform(self, optionstr: str) -> str:
        return optionstr


def validate_metadata(contents: dict[str, bytes], version: str) -> None:
    metadata = BytesParser(policy=policy.default).parsebytes(contents["METADATA"])
    if metadata.get_all("Name") != [PRODUCT_NAME] or metadata.get_all("Version") != [version]:
        raise ValueError("wheel metadata does not match the frozen product")
    wheel = BytesParser(policy=policy.default).parsebytes(contents["WHEEL"])
    if (
        wheel.get_all("Wheel-Version") != ["1.0"]
        or wheel.get_all("Root-Is-Purelib") != ["true"]
        or wheel.get_all("Tag") != ["py3-none-any"]
    ):
        raise ValueError("measurement requires the supported pure Python wheel format")
    points = EntryPoints(interpolation=None)
    points.read_string(contents["entry_points.txt"].decode("utf-8", "strict"))
    if points.sections() != ["console_scripts"] or dict(points["console_scripts"]) != {
        PRODUCT_NAME: "yorunge.cli:main"
    }:
        raise ValueError("wheel console entry point differs from the measured product")


def contents_snapshot(
    archive: zipfile.ZipFile, expected: dict[str, str], version: str
) -> tuple[dict[str, str], dict[str, str]]:
    product, metadata = {}, {}
    prefix = f"yorunge-{version}.dist-info/"
    for item in archive.infolist():
        if item.is_dir():
            continue
        if item.file_size > MAX_MEMBER_BYTES:
            raise ValueError("wheel member exceeded the measurement bound")
        if item.filename.startswith("yorunge/"):
            name = "src/" + item.filename
            content = archive.read(item)
            product[name] = hashlib.sha256(content).hexdigest()
        elif item.filename in {prefix + name for name in METADATA_FILES}:
            metadata[item.filename.removeprefix(prefix)] = archive.read(item)
    if product != expected or set(metadata) != set(METADATA_FILES):
        raise ValueError("wheel bytes differ from the complete measured product")
    validate_metadata(metadata, version)
    return product, {
        name: hashlib.sha256(content).hexdigest() for name, content in metadata.items()
    }


def snapshot(path: Path, source: dict[str, str], version: str) -> dict[str, object]:
    expected = {name: digest for name, digest in source.items() if name.startswith("src/yorunge/")}
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_WHEEL_BYTES:
        raise ValueError("measurement wheel must be a bounded regular archive")
    guard = runpy.run_path(str(Path(__file__).with_name("verify-distributions.py")))
    try:
        guard["inspect_archive"](path)
        with path.open("rb") as stream:
            if state(os.fstat(stream.fileno())) != state(before):
                raise ValueError("measurement wheel changed before inspection")
            with zipfile.ZipFile(stream) as archive:
                product, metadata = contents_snapshot(archive, expected, version)
            stream.seek(0)
            digest = hashlib.sha256()
            remaining = before.st_size
            while remaining:
                block = stream.read(min(1_048_576, remaining))
                if not block:
                    raise ValueError("measurement wheel became shorter")
                digest.update(block)
                remaining -= len(block)
            if state(os.fstat(stream.fileno())) != state(before):
                raise ValueError("measurement wheel changed during inspection")
        if state(path.lstat()) != state(before):
            raise ValueError("measurement wheel path changed during inspection")
    except (zipfile.BadZipFile, configparser.Error, KeyError):
        raise ValueError("invalid measurement wheel contents") from None
    return {"sha256": digest.hexdigest(), "product_sha256": product, "metadata_sha256": metadata}
