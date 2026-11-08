"""Fixed synthetic download data; never reads user files or credentials.

The object is a deterministic stream of 64 KiB blocks. Block ``b`` holds ``(i + 37 * b) % 256`` at
offset ``i``, so byte ``p`` of the object is ``(p + 37 * (p >> 16)) % 256``. The pattern repeats
only every 16 MiB, so a resume from a wrong offset changes the digest, also when it is a multiple
of the 8 MiB checkpoint interval; a wrong offset that is a multiple of 16 MiB repeats the same
bytes and is caught by the size and the byte accounting instead.

Three code paths derive these bytes by three different formulas and none of them allocates more than
one block, whatever the object size: the oracle below applies ``bytes.translate`` to one base block,
the measurement server rotates and repeats a 256-byte cycle, and the evidence verifier slides a
window over a periodic buffer. A test compares all of them with a naive in-memory formula.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[2]
MIB = 1_048_576
BLOCK_BYTES = 65_536  # the generation and oracle block: far below any object size
ROTATION = 37  # block ``b`` is the 256-byte cycle rotated by ``37 * b``
MAX_BYTES = 1_073_741_824  # the product's 1 GiB download limit
LABELS = ("16", "256", "1024", "resume")
WARM_LABELS = ("warm", "warm-resume")

VERSION = "00000000-0000-4000-8000-000000000d31"
API_BASE = "/api/v1"
PLATFORM_HOST = "api.ssyz.org.tr"
ORIGIN = f"https://{PLATFORM_HOST}"
FORMAT = "onnx"
FILENAME = "provider-native-name.onnx"  # the provider's name: validated by the product, then unused
TARGET_NAME = "weights.onnx"
OBJECT_NAME = "weights.onnx"
SIGNED_PREFIX = f"{API_BASE}/files/evren-models/"
SIGNED_PATH = SIGNED_PREFIX + OBJECT_NAME
SIGNED_QUERY = (
    "X-Amz-Algorithm=AWS4-HMAC-SHA256"
    "&X-Amz-Credential=synthetic%2F20261108%2Fnative%2Fs3%2Faws4_request"
    "&X-Amz-Signature=" + "5" * 64
)
SIGNED_TARGET = f"{SIGNED_PATH}?{SIGNED_QUERY}"
JSON_PATH = f"{API_BASE}/models/versions/{VERSION}/download"
JSON_TARGET = f"{JSON_PATH}?format={FORMAT}"
KEY_ENV = "YORUNGE_SYNTHETIC_DOWNLOAD_MEASUREMENT_KEY"
KEY = "synthetic-download-measurement-selected-key"

# The first signed GET of ``resume`` is cut after 3 * 8 MiB (the engine's three body checkpoints)
# plus a ragged 1_000_003 bytes: a clean stop then checkpoints that exact offset, so the second GET
# is a ``Range`` request at an offset that is no multiple of a block, a record or a checkpoint.
RESUME_CUT_AT = 3 * 8 * MIB + 1_000_003
WARM_CUT_AT = 524_289  # the 1 MiB warm object of the resume label is cut once, a byte past 512 KiB


@dataclass(frozen=True)
class Fixture:
    """One served object: its size, and where the first signed GET is cut (if it is)."""

    label: str
    size: int
    cut_at: int | None = None

    @property
    def etag(self) -> str:
        return f'"native-download-{self.label}"'


FIXTURES = {
    item.label: item
    for item in (
        Fixture("warm", MIB),
        Fixture("warm-resume", MIB, WARM_CUT_AT),
        Fixture("16", 16 * MIB),
        Fixture("256", 256 * MIB),
        Fixture("1024", 1024 * MIB),
        Fixture("resume", 256 * MIB, RESUME_CUT_AT),
    )
}
WARM_OF = {"16": "warm", "256": "warm", "1024": "warm", "resume": "warm-resume"}


class Paths(NamedTuple):
    config: Path
    state: Path
    out: Path
    target: Path


def fixture(label: str) -> Fixture:
    if label not in FIXTURES:
        raise ValueError("unknown download measurement fixture")
    return FIXTURES[label]


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def expected_sha256(size: int) -> str:
    """Independent bounded oracle: ``translate`` one 64 KiB base block into every object block.

    The server rotates and repeats a 256-byte cycle instead, and the evidence verifier slides a
    window over a periodic buffer. No side allocates a response-sized object or asks HTTP for the
    digest it expects.
    """
    if type(size) is not int or not 1 <= size <= MAX_BYTES:
        raise ValueError("expected size must be between 1 byte and 1 GiB")
    base = bytes(index % 256 for index in range(BLOCK_BYTES))
    tables: dict[int, bytes] = {}  # block ``b`` and ``b + 256`` rotate alike: at most 256 tables
    digest = hashlib.sha256()
    remaining, block = size, 0
    while remaining:
        used = min(remaining, BLOCK_BYTES)
        shift = (ROTATION * block) % 256
        if shift not in tables:
            tables[shift] = bytes((value + shift) % 256 for value in range(256))
        digest.update(memoryview(base.translate(tables[shift]))[:used])
        remaining -= used
        block += 1
    return digest.hexdigest()


def paths(directory: Path) -> Paths:
    """Where one worker keeps its config, its state store and the directory it downloads into."""
    out = directory / "out"
    return Paths(directory / "config.toml", directory / "state", out, out / TARGET_NAME)


def write_config(path: Path) -> None:
    with path.open("x", encoding="utf-8") as target:
        target.write(
            'schema_version = 1\nactive_profile = "native"\n[profiles.native]\n'
            f'platform_key_env = "{KEY_ENV}"\n'
        )
