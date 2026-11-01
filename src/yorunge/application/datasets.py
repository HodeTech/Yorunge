"""Local dataset budgets, structural decoding and complete byte-set comparison."""

from __future__ import annotations

import time
import unicodedata
from collections.abc import Callable

from yorunge.domain.dataset_manifest import DATASET_SECONDS, DatasetManifest, DatasetVerification
from yorunge.domain.errors import ManifestMismatch, YorungeError


class DatasetBudget:
    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self.clock = time.monotonic if clock is None else clock
        self.end = self.clock() + DATASET_SECONDS

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
