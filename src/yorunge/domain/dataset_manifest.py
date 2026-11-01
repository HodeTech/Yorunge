"""Portable file identities and bounded manifest integrity, never execution authority."""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from typing import Annotated, Any, Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic.config import ExtraValues

from yorunge.domain.models import Model, has_control_characters

MAX_FILES = 4096
MAX_DIRECTORIES = 4096
MAX_PATH_DEPTH = 32
MAX_COMPONENT_BYTES = 255
MAX_PATH_BYTES = 1024
MAX_ANCHOR_BYTES = 4096
MAX_CONTENT_BYTES = 1024**3
MAX_MANIFEST_BYTES = 8 * 1024**2
MAX_JSON_DEPTH = 8
MAX_JSON_NODES = 50_000
MAX_SUMMARY_BYTES = 16 * 1024
HASH_BLOCK_BYTES = 1024**2
DATASET_SECONDS = 30.0

Sha256 = Annotated[str, Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")]
FileSize = Annotated[int, Field(ge=0, le=MAX_CONTENT_BYTES)]
FileCount = Annotated[int, Field(ge=0, le=MAX_FILES)]
FORBIDDEN_NAME = frozenset('<>:"\\|?*')
RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)}
)


def safe_text(value: str) -> bytes:
    encoded = value.encode("utf-8", errors="strict")
    if has_control_characters(value) or any(
        "\u202a" <= char <= "\u202e" or "\u2066" <= char <= "\u2069" for char in value
    ):
        raise ValueError("control-free path required")
    return encoded


def validate_component(value: str) -> None:
    if (
        not value
        or value in (".", "..")
        or len(safe_text(value)) > MAX_COMPONENT_BYTES
        or any(char in FORBIDDEN_NAME or char == "/" for char in value)
        or value.endswith((" ", "."))
        or value.split(".", 1)[0].upper() in RESERVED_NAMES
    ):
        raise ValueError("portable path component required")


def file_parts(value: str) -> tuple[str, ...]:
    parts = tuple(value.split("/"))
    if len(safe_text(value)) > MAX_PATH_BYTES or len(parts) > MAX_PATH_DEPTH:
        raise ValueError("relative path limit exceeded")
    for part in parts:
        validate_component(part)
    return parts


def collision_key(value: str) -> str:
    return unicodedata.normalize("NFC", unicodedata.normalize("NFC", value).casefold())


class PathInventory:
    """Bound each original sibling identity, including empty directory observations."""

    def __init__(self) -> None:
        self.siblings: dict[tuple[str, ...], dict[str, str]] = {}
        self.kinds: dict[tuple[str, ...], bool] = {}
        self.directory_count = 1
        self.file_count = 0

    def add(self, path: str, *, is_file: bool) -> None:
        parts = file_parts(path)
        for index, name in enumerate(parts):
            parent, current = parts[:index], parts[: index + 1]
            self._claim(parent, current, name, is_file and index == len(parts) - 1)

    def _claim(
        self, parent: tuple[str, ...], current: tuple[str, ...], name: str, is_file: bool
    ) -> None:
        names = self.siblings.setdefault(parent, {})
        key = collision_key(name)
        if key in names and names[key] != name:
            raise ValueError("portable path collision")
        names[key] = name
        if current in self.kinds:
            if self.kinds[current] != is_file or is_file:
                raise ValueError("file and directory collision or duplicate file")
            return
        if is_file:
            self.file_count += 1
        else:
            self.directory_count += 1
        if self.file_count > MAX_FILES or self.directory_count > MAX_DIRECTORIES:
            raise ValueError("file or directory limit exceeded")
        self.kinds[current] = is_file


def validate_paths(paths: tuple[str, ...]) -> None:
    if tuple(sorted(set(paths), key=lambda path: path.encode("utf-8"))) != paths:
        raise ValueError("unique sorted file paths required")
    inventory = PathInventory()
    for path in paths:
        inventory.add(path, is_file=True)


def canonical_manifest(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _quoted_state(char: str, escaped: bool) -> tuple[bool, bool]:
    if escaped:
        return True, False
    if char == "\\":
        return True, True
    return char != '"', False


def _json_depth(text: str) -> None:
    depth, quoted, escaped = 0, False, False
    for char in text:
        if quoted:
            quoted, escaped = _quoted_state(char, escaped)
            continue
        if char == '"':
            quoted = True
            continue
        if char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
        if not 0 <= depth <= MAX_JSON_DEPTH:
            raise ValueError("manifest JSON depth limit exceeded")


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate manifest JSON key")
    return result


def _reject_constant(value: str) -> object:
    raise ValueError("finite manifest JSON required")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("finite manifest JSON required")
    return number


def decode_manifest_json(content: bytes) -> object:
    if type(content) is not bytes or not content or len(content) > MAX_MANIFEST_BYTES:
        raise ValueError("manifest byte limit exceeded")
    text = content.decode("utf-8", errors="strict")
    _json_depth(text)
    value: object = json.loads(
        text,
        object_pairs_hook=_unique_pairs,
        parse_constant=_reject_constant,
        parse_float=_finite_float,
    )
    pending, count = [value], 0
    while pending:
        item = pending.pop()
        count += 1
        if count > MAX_JSON_NODES:
            raise ValueError("manifest JSON node limit exceeded")
        if isinstance(item, str):
            item.encode("utf-8", errors="strict")
        elif isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return value


class DatasetFile(Model):
    path: str
    size: FileSize
    sha256: Sha256

    @field_validator("path")
    @classmethod
    def portable_path(cls, value: str) -> str:
        file_parts(value)
        return value


class DatasetManifest(Model):
    schema_version: Literal[1] = 1
    policy_version: Literal[1] = 1
    kind: Literal["dataset_manifest"] = "dataset_manifest"
    hash_algorithm: Literal["sha256"] = "sha256"
    files: Annotated[tuple[DatasetFile, ...], Field(max_length=MAX_FILES)]
    file_count: FileCount
    total_bytes: FileSize
    digest: Sha256

    @field_validator("policy_version", mode="before")
    @classmethod
    def integer_policy(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("integer policy version required")
        return value

    @model_validator(mode="after")
    def integrity(self) -> DatasetManifest:
        if self.file_count != len(self.files) or self.total_bytes != sum(
            f.size for f in self.files
        ):
            raise ValueError("manifest aggregate mismatch")
        validate_paths(tuple(file.path for file in self.files))
        if self.digest != self.computed_digest() or len(self.encoded()) > MAX_MANIFEST_BYTES:
            raise ValueError("manifest digest or byte limit mismatch")
        return self

    def computed_digest(self) -> str:
        return hashlib.sha256(
            canonical_manifest(self.model_dump(mode="json", exclude={"digest"}))
        ).hexdigest()

    def encoded(self) -> bytes:
        return canonical_manifest(self.model_dump(mode="json")) + b"\n"

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        content = json_data.encode("utf-8") if isinstance(json_data, str) else bytes(json_data)
        value = decode_manifest_json(content)
        # Defaults are useful to the producer; the persisted wire has no optional fields.
        if not isinstance(value, dict) or set(value) != set(cls.model_fields):
            raise ValueError("complete closed manifest required")
        return super().model_validate_json(
            content,
            strict=True,
            extra="forbid",
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )


def build_manifest(files: tuple[DatasetFile, ...]) -> DatasetManifest:
    ordered = tuple(sorted(files, key=lambda file: file.path.encode("utf-8")))
    body = {
        "schema_version": 1,
        "policy_version": 1,
        "kind": "dataset_manifest",
        "hash_algorithm": "sha256",
        "files": [file.model_dump(mode="json") for file in ordered],
        "file_count": len(ordered),
        "total_bytes": sum(file.size for file in ordered),
    }
    return DatasetManifest.model_validate(
        {**body, "files": ordered, "digest": hashlib.sha256(canonical_manifest(body)).hexdigest()}
    )
