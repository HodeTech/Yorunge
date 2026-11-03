"""Fixed synthetic upload data; never reads user datasets or credentials."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VECTORS = ROOT / "tests/fixtures/upload-native-vectors-v1.json"
LABELS = ("16", "256", "1024", "capacity")
OWNER = "00000000-0000-4000-8000-000000000003"
PROJECT = "00000000-0000-4000-8000-000000000004"
KEY_ENV = "YORUNGE_SYNTHETIC_UPLOAD_MEASUREMENT_KEY"
KEY = "synthetic-upload-measurement-selected-key"
NAME = "native-upload"


def fixture(label: str) -> dict:
    if label not in ("warm", *LABELS):
        raise ValueError("unknown upload measurement fixture")
    value = json.loads(VECTORS.read_bytes())
    if value["schema_version"] != 1 or value["kind"] != "upload_native_vectors":
        raise ValueError("unknown upload fixture vectors")
    return value["fixtures"][label]


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def write_fixture(root: Path, manifest: Path, expected: dict) -> None:
    root.mkdir()
    cycle = bytes(range(256))
    for index, file in enumerate(expected["files"]):
        if file["path"] != f"file-{index:03}.bin":
            raise ValueError("measurement filenames must match the fixed vector")
        size = file["size"]
        if type(size) is not int or not 0 <= size <= 500_000_000:
            raise ValueError("invalid measurement file size")
        offset = (17 * index) % 256
        block = (cycle[offset:] + cycle[:offset]) * 128
        with (root / file["path"]).open("xb") as target:
            remaining = size
            while remaining:
                used = min(remaining, len(block))
                target.write(memoryview(block)[:used])
                remaining -= used
    with manifest.open("xb") as target:
        target.write(canonical(expected) + b"\n")


def write_config(path: Path) -> None:
    with path.open("x", encoding="utf-8") as target:
        target.write(
            'schema_version = 1\nactive_profile = "native"\n[profiles.native]\n'
            f'platform_key_env = "{KEY_ENV}"\nproject_id = "{PROJECT}"\n'
        )
