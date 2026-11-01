"""Local dataset budgets, structural decoding and complete byte-set comparison."""

from __future__ import annotations

import json
import time
import unicodedata
from collections.abc import Callable
from typing import Protocol

from yorunge.domain import dataset_manifest as policy
from yorunge.domain.dataset_manifest import (
    DATASET_SECONDS,
    DatasetInspection,
    DatasetManifest,
    DatasetVerification,
)
from yorunge.domain.errors import ManifestMismatch, YorungeError
from yorunge.domain.models import Result


class DatasetBudget:
    def __init__(
        self, clock: Callable[[], float] | None = None, *, started: float | None = None
    ) -> None:
        self.clock = time.monotonic if clock is None else clock
        self.end = (self.clock() if started is None else started) + DATASET_SECONDS

    def check(self) -> None:
        if self.clock() >= self.end:
            raise YorungeError("dataset_timeout")


def decode_manifest(content: bytes, budget: DatasetBudget) -> DatasetManifest:
    budget.check()
    try:
        manifest = DatasetManifest.model_validate_json(content)
    except (ValueError, RecursionError, OverflowError):
        raise YorungeError("manifest_invalid") from None
    budget.check()
    return manifest


def compare_manifests(
    expected: DatasetManifest, actual: DatasetManifest, budget: DatasetBudget
) -> DatasetVerification:
    budget.check()
    if expected.digest != actual.digest:
        previous = {file.path: (file.size, file.sha256) for file in expected.files}
        current = {file.path: (file.size, file.sha256) for file in actual.files}
        missing = len(previous.keys() - current.keys())
        unexpected = len(current.keys() - previous.keys())
        changed = sum(previous[path] != current[path] for path in previous.keys() & current.keys())
        budget.check()
        raise ManifestMismatch(expected.digest, actual.digest, missing, unexpected, changed)
    result = DatasetVerification(
        schema_version=1,
        manifest_digest=expected.digest,
        file_count=actual.file_count,
        total_bytes=actual.total_bytes,
        matches=True,
        unicode_version=unicodedata.unidata_version,
    )
    budget.check()
    return result


class DatasetSource(Protocol):
    def scan(self) -> DatasetManifest: ...


class ManifestWriter(Protocol):
    def ensure_absent(self) -> None: ...

    def publish(self, manifest: DatasetManifest) -> None: ...


def check_summary(result: Result[DatasetInspection] | Result[DatasetVerification]) -> None:
    encoded = (
        result.data.model_dump_json().encode("utf-8"),
        result.model_dump_json().encode("utf-8"),
        json.dumps(
            result.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8"),
    )
    if any(len(item) > policy.MAX_SUMMARY_BYTES for item in encoded):
        raise YorungeError("dataset_limit_exceeded")


def inspect_dataset_tree(
    source: DatasetSource, writer: ManifestWriter, manifest_path: str, budget: DatasetBudget
) -> Result[DatasetInspection]:
    writer.ensure_absent()
    manifest = source.scan()
    result = Result[DatasetInspection](
        data=DatasetInspection(
            schema_version=1,
            manifest_path=manifest_path,
            manifest_digest=manifest.digest,
            file_count=manifest.file_count,
            total_bytes=manifest.total_bytes,
            unicode_version=unicodedata.unidata_version,
        ),
        warnings=("local_files_only",),
    )
    check_summary(result)
    budget.check()
    writer.publish(manifest)
    budget.check()
    return result


def verify_dataset_tree(
    source: DatasetSource, expected: DatasetManifest, budget: DatasetBudget
) -> Result[DatasetVerification]:
    result = Result[DatasetVerification](
        data=compare_manifests(expected, source.scan(), budget), warnings=("local_files_only",)
    )
    check_summary(result)
    budget.check()
    return result
