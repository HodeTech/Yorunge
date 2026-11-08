"""The download contract: closed levels, argument values, the partial-download record, its names.

ADR-0032 and ``docs/reference/download-engine.md``. Pure: no I/O, clock or randomness. What is
here decides what a download *means* (the level its bytes earn, the shape of what is kept between
runs, the names it is kept under) before any code moves a byte.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Annotated, ClassVar, Final, Literal, Self

from pydantic import Field, field_validator, model_validator

from yorunge.domain.capabilities import JsonWireModel, canonical, instant
from yorunge.domain.dataset_upload import provider_uuid
from yorunge.domain.errors import DownloadIntegrityMismatch, YorungeError
from yorunge.domain.models import Model, has_control_characters

# --- limits and times (ADR-0032 §1-§3) ------------------------------------------------------------

MAX_DOWNLOAD_BYTES: Final = 1024**3  # the common raw HTTP limit; raising it is a measured decision
DEFAULT_TIMEOUT_SECONDS: Final = 900
MIN_TIMEOUT_SECONDS: Final = 30
MAX_TIMEOUT_SECONDS: Final = 3600
MAX_FOLD: Final = 1024
CONTROL_CALL_SECONDS: Final = 30  # the JSON call that resolves the signed address
PHASE_SECONDS: Final = 5  # connect, write and read of the signed GET
POOL_SECONDS: Final = 1
BLOCK_BYTES: Final = 1024 * 1024  # one write
CHECKPOINT_BYTES: Final = 8 * 1024 * 1024  # fsync and sidecar checkpoint interval
MAX_SIDECAR_BYTES: Final = 4096
MAX_URL_BYTES: Final = 16 * 1024
MAX_TARGET_NAME_BYTES: Final = 255
RESERVED_PREFIX: Final = ".yorunge-download-"
EMPTY_SHA256: Final = hashlib.sha256(b"").hexdigest()

Sha256 = Annotated[str, Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")]
# A strong entity tag: quoted, printable ASCII, at least one character (an empty tag identifies
# nothing). ``W/`` (weak) tags never match.
StrongEtag = Annotated[str, Field(pattern=r'^"[\x21\x23-\x7e]{1,126}"$')]
ByteCount = Annotated[int, Field(ge=0, le=MAX_DOWNLOAD_BYTES)]
FileId = Annotated[int, Field(ge=0, lt=2**64)]

_INTEGER = re.compile(r"(0|[1-9][0-9]{0,18})", re.ASCII)
_SHA256 = re.compile(r"[a-f0-9]{64}", re.ASCII)


# --- argument values ------------------------------------------------------------------------------


def _bounded_integer(value: object, low: int, high: int) -> int:
    """An exact decimal integer (or int) in range: no sign, space, decimal point or leading zero."""
    number: int | None = None
    if type(value) is int:
        number = value
    elif type(value) is str and _INTEGER.fullmatch(value) is not None:
        number = int(value)
    if number is None or not low <= number <= high:
        raise YorungeError("invalid_request")
    return number


def parse_fold(value: object) -> int:
    """``--fold``: 0 to 1024, an exact integer."""
    return _bounded_integer(value, 0, MAX_FOLD)


def parse_timeout(value: object) -> int:
    """``--timeout``: 30 to 3600 whole seconds."""
    return _bounded_integer(value, MIN_TIMEOUT_SECONDS, MAX_TIMEOUT_SECONDS)


def parse_sha256(value: object) -> str:
    """``--sha256``: 64 lowercase hexadecimal digits, the user's own expectation."""
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise YorungeError("invalid_request")
    return value


# --- verification levels (ADR-0032 §5) ------------------------------------------------------------

VerificationLevel = Literal["transfer_complete", "sha256_matched"]
# ``size_matched`` and the ``provider_metadata``/``local_manifest`` sources are added by a consumer
# that can produce them; today the expectation is the user's or there is none.
ExpectationSource = Literal["none", "user_supplied"]


@dataclass(frozen=True, slots=True)
class Verification:
    level: VerificationLevel
    expectation_source: ExpectationSource


def verify_expectation(
    computed_sha256: str, size: int, expected_sha256: str | None
) -> Verification:
    """What the written bytes earn against what the user expects; a mismatch is refused.

    The level says how the written bytes relate to an expectation, never that the object stored
    by the provider is authentic. Without an expectation the bytes are only a complete transfer: a
    computed digest is not a verification of itself.
    """
    if (
        type(computed_sha256) is not str
        or _SHA256.fullmatch(computed_sha256) is None
        or type(size) is not int
        or not 0 <= size <= MAX_DOWNLOAD_BYTES
        or (expected_sha256 is not None and parse_sha256(expected_sha256) != expected_sha256)
    ):
        raise YorungeError("invalid_request")
    if expected_sha256 is None:
        return Verification("transfer_complete", "none")
    if computed_sha256 != expected_sha256:
        raise DownloadIntegrityMismatch(computed_sha256, size)
    return Verification("sha256_matched", "user_supplied")


# --- the result -----------------------------------------------------------------------------------


class DownloadSource(Model):
    """What was downloaded: today an exact model version, in a format, with an optional fold."""

    kind: Literal["model_version"]
    version_id: str
    format: Literal["onnx", "pt", "tflite"]
    fold: Annotated[int, Field(ge=0, le=MAX_FOLD)] | None

    @field_validator("version_id")
    @classmethod
    def canonical_identifier(cls, value: str) -> str:
        return provider_uuid(value)


class DownloadSummary(Model):
    schema_version: Literal[1]
    kind: Literal["download_summary"]
    output_path: Annotated[str, Field(min_length=1, max_length=4096)]
    bytes: ByteCount
    sha256: Sha256
    verification_level: VerificationLevel
    expectation_source: ExpectationSource
    resumed: bool
    resumed_from_bytes: ByteCount
    source: DownloadSource

    @field_validator("output_path")
    @classmethod
    def printable_path(cls, value: str) -> str:
        if has_control_characters(value) or len(value.encode("utf-8", errors="strict")) > 4096:
            raise ValueError("bounded printable path required")
        return value

    @model_validator(mode="after")
    def consistent(self) -> Self:
        level_source = (self.verification_level, self.expectation_source)
        if level_source not in {("transfer_complete", "none"), ("sha256_matched", "user_supplied")}:
            raise ValueError("a level is earned against its own kind of expectation")
        if self.resumed:
            # From part of its bytes, or all of them: a complete stage is published without a
            # request. A complete stage of no bytes is the one case of nothing from nothing.
            empty = self.bytes == self.resumed_from_bytes == 0
            if not (0 < self.resumed_from_bytes <= self.bytes or empty):
                raise ValueError("a resumed download resumes from part of its bytes")
        elif self.resumed_from_bytes != 0:
            raise ValueError("a download that did not resume resumed from nothing")
        return self


# --- the partial-download record (the sidecar) ----------------------------------------------------


class DownloadWire(JsonWireModel):
    """A record that is kept between runs: canonical bytes, bounded, exactly as written."""

    max_wire_bytes: ClassVar[int] = MAX_SIDECAR_BYTES

    def encoded(self) -> bytes:
        content = canonical(self.model_dump(mode="json"))
        if len(content) > self.max_wire_bytes:
            raise ValueError("download wire byte limit exceeded")
        return content

    @classmethod
    def decode(cls, data: bytes) -> Self:
        """The record a stored copy says: nothing but the exact canonical bytes of a valid one."""
        if type(data) is not bytes or len(data) > cls.max_wire_bytes:
            raise ValueError("bounded download wire required")
        try:
            record = cls.model_validate_json(data)
        except RecursionError:
            raise ValueError("bounded download wire required") from None  # deep nesting, <4 KiB
        if record.encoded() != data:
            raise ValueError("canonical download wire required")
        return record


class DownloadPartial(DownloadWire):
    """What survives between runs of one download: enough to resume it, or to know it cannot.

    ``committed_bytes`` are fsynced and ``prefix_sha256`` is the digest of exactly those bytes.
    ``etag`` is a strong tag or ``None``; ``total_size`` is ``None`` while the length is unknown
    (a chunked body fixes it only at the completion checkpoint). ``identity_key`` binds the record
    to the service target and the thing downloaded; a record of another identity resumes nothing.
    """

    schema_version: Literal[1]
    kind: Literal["download_partial"]
    identity_key: Sha256
    target_hash: Sha256
    etag: StrongEtag | None
    total_size: ByteCount | None
    committed_bytes: ByteCount
    prefix_sha256: Sha256
    stage_device: FileId
    stage_inode: FileId
    created_at: str
    updated_at: str

    @field_validator("created_at", "updated_at")
    @classmethod
    def canonical_time(cls, value: str) -> str:
        instant(value)
        return value

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if instant(self.updated_at) < instant(self.created_at):
            raise ValueError("a record is not updated before it is created")
        if self.total_size is not None and self.committed_bytes > self.total_size:
            raise ValueError("more bytes committed than the total")
        if self.committed_bytes == 0 and self.prefix_sha256 != EMPTY_SHA256:
            raise ValueError("the prefix of no bytes has the digest of no bytes")
        return self

    @property
    def complete(self) -> bool:
        """The whole body is committed (a length known, or fixed at the completion checkpoint)."""
        return self.total_size is not None and self.committed_bytes == self.total_size


# --- identity and names ---------------------------------------------------------------------------


def identity_key(
    *,
    origin: str,
    api_base_path: str,
    kind: str,
    resource_id: str,
    artifact_format: str,
    fold: int | None,
) -> str:
    """The key a partial download resumes under: the service target AND what is downloaded.

    The same version identifier, format and file name behind another service target is another
    key. The parts are not interpreted here; a consumer passes its normalized values.
    """
    parts = {"origin": origin, "api_base_path": api_base_path, "kind": kind}
    parts.update({"resource_id": resource_id, "format": artifact_format})
    for value in parts.values():
        if type(value) is not str or not value or has_control_characters(value):
            raise YorungeError("invalid_request")
        try:
            value.encode("utf-8")  # lone surrogates would collide with the character they spell
        except UnicodeError:
            raise YorungeError("invalid_request") from None
    if fold is not None and parse_fold(fold) != fold:
        raise YorungeError("invalid_request")
    body = {"kind": "download_identity", "parts": parts, "fold": fold}
    return hashlib.sha256(canonical(body)).hexdigest()


_REFUSED_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Zl", "Zp", "Cn"})


def validate_target_name(name: object) -> str:
    """The final component of the target: one printable name that is not the protocol's own.

    Refused: an empty name, ``.`` and ``..``, ``/`` and NUL, more than 255 UTF-8 bytes, a name that
    does not encode, control, format, surrogate, line and paragraph separator characters and
    characters the Unicode database of the running interpreter does not assign (so a very new
    character is accepted by a newer Python than an older one), and the protocol's own prefix in
    any letter case.
    """
    if type(name) is not str or not name or name in {".", ".."} or "/" in name or "\x00" in name:
        raise YorungeError("download_target_invalid")
    try:
        size = len(name.encode("utf-8", errors="strict"))
    except UnicodeError:
        raise YorungeError("download_target_invalid") from None
    if (
        size > MAX_TARGET_NAME_BYTES
        or has_control_characters(name)
        or any(unicodedata.category(char) in _REFUSED_CATEGORIES for char in name)
        or name.lower().startswith(RESERVED_PREFIX)  # a case-insensitive filesystem aliases it
    ):
        raise YorungeError("download_target_invalid")
    return name


def target_hash(name: str) -> str:
    """Digest of the target's name, byte for byte (no case or normalization folding)."""
    validate_target_name(name)
    return hashlib.sha256(b"yorunge-download-target-v1\x00" + name.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class DownloadNames:
    """The four names one target's download lives under, next to the target."""

    lock: str
    stage: str
    sidecar: str
    sidecar_tmp: str


def download_names(name: str) -> DownloadNames:
    """Fixed-length names derived from the target name and nothing else.

    They carry no provider URL, version or path. Two targets of one directory share a name only
    by a collision of a 128-bit digest prefix. Two spellings of one file on a case- or
    normalization-insensitive filesystem are two names here; the exclusive link of the target
    still lets one of them win.
    """
    stem = f"{RESERVED_PREFIX}{target_hash(name)[:32]}"
    return DownloadNames(
        lock=f"{stem}.lock",
        stage=f"{stem}.part",
        sidecar=f"{stem}.json",
        sidecar_tmp=f"{stem}.json.tmp",
    )
