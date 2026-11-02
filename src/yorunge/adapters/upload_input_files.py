"""Fresh full hash plus same-invocation descriptor observation, with no retained FDs."""

from __future__ import annotations

import math
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn

from yorunge.adapters.dataset_files import (
    TreeObservation,
    anchor_dataset_path,
    anchor_dataset_paths,
    open_dataset,
    require_dataset_files,
)
from yorunge.application.datasets import DatasetBudget, decode_manifest
from yorunge.application.response_json import check_response_secrets
from yorunge.application.upload_inputs import revalidate_input
from yorunge.domain.credentials import SecretValue
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_upload import UploadRoot, manifest_reference
from yorunge.domain.errors import YorungeError


class _InputBudget(DatasetBudget):
    def __init__(self, end: float) -> None:
        super().__init__()
        self.end = min(self.end, end)

    def check(self) -> None:
        if self.clock() >= self.end:
            raise YorungeError("execution_timeout")


def _deadline(end: float) -> None:
    valid = type(end) in (int, float)
    try:
        valid = valid and math.isfinite(end)
    except OverflowError:
        valid = False
    if not valid:
        raise YorungeError("invalid_request")
    remaining = end - time.monotonic()
    if remaining <= 0:
        raise YorungeError("execution_timeout")
    if remaining > 900.0:
        raise YorungeError("invalid_request")


def _secret(value: UploadRoot | DatasetManifest, secret: SecretValue) -> None:
    valid = True
    try:
        check_response_secrets(value, (secret,))
    except YorungeError:
        valid = False
    if not valid:
        raise YorungeError("invalid_request")


def _manifest(value: DatasetManifest, secret: SecretValue) -> DatasetManifest:
    result = revalidate_input(DatasetManifest, value)
    if result.file_count == 0:
        raise YorungeError("input_invalid")
    within_limits = True
    try:
        manifest_reference(result)
    except ValueError:
        within_limits = False
    if not within_limits:
        raise YorungeError("input_budget_exceeded")
    _secret(result, secret)
    return result


@dataclass(frozen=True, slots=True, repr=False)
class UploadInputObservation:
    root: UploadRoot
    manifest: DatasetManifest
    _tree: TreeObservation = field(repr=False)
    _end: float = field(repr=False)
    _pid: int = field(repr=False)
    _thread: int = field(repr=False)

    def recheck(self) -> None:
        if os.getpid() != self._pid or threading.get_ident() != self._thread:
            raise YorungeError("invalid_request")
        _deadline(self._end)
        budget = _InputBudget(self._end)
        with open_dataset(Path(self.root.anchor), budget) as tree:
            current = UploadRoot(
                anchor=str(tree.anchor), device=tree.root_identity[0], inode=tree.root_identity[1]
            )
            if current != self.root:
                raise YorungeError("input_changed")
            tree.recheck_observation(self._tree)
        budget.check()

    def __repr__(self) -> str:
        return "<upload input observation private>"

    def __copy__(self) -> NoReturn:
        raise TypeError("upload input observation cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        raise TypeError("upload input observation cannot be copied")

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("upload input observation cannot be serialized")


def capture_upload_input(
    root: Path,
    manifest: Path | DatasetManifest,
    secret: SecretValue,
    *,
    end: float,
    expected_root: UploadRoot | None = None,
) -> UploadInputObservation:
    _deadline(end)
    if (
        not isinstance(root, Path)
        or type(secret) is not SecretValue
        or not (isinstance(manifest, Path) or type(manifest) is DatasetManifest)
    ):
        raise YorungeError("invalid_request")
    require_dataset_files()
    budget = _InputBudget(end)
    if isinstance(manifest, Path):
        root, manifest = anchor_dataset_paths(root, manifest)
    else:
        root = anchor_dataset_path(root)
    expected_root = None if expected_root is None else revalidate_input(UploadRoot, expected_root)
    with open_dataset(root, budget) as tree:
        captured_root = UploadRoot(
            anchor=str(tree.anchor), device=tree.root_identity[0], inode=tree.root_identity[1]
        )
        _secret(captured_root, secret)
        if expected_root is not None and expected_root != captured_root:
            raise YorungeError("input_changed")
        expected = (
            decode_manifest(tree.read_manifest(manifest), budget)
            if isinstance(manifest, Path)
            else manifest
        )
        expected = _manifest(expected, secret)
        observed = tree.scan()
        if observed != expected:
            raise YorungeError("input_changed")
        snapshot = tree.observation()
    budget.check()
    return UploadInputObservation(
        captured_root, expected, snapshot, float(end), os.getpid(), threading.get_ident()
    )
