"""Local-only reconciliation selection; never read source files or mint write access."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from yorunge.adapters.capability_cache import Clock
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import (
    VersionedTransferView,
    acknowledged_stages,
    created_dataset,
    read_manifest,
)
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_transfer import TERMINAL
from yorunge.domain.dataset_transfer_v2 import TransferRecordV2
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.platform_upload import ProviderDataset
from yorunge.domain.upload_checks import AuthorizationCheck
from yorunge.domain.upload_versions import UploadPlan, UploadRecord


class _PrivateRead:
    def __repr__(self) -> str:
        return "<upload read phase private>"

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("private upload read cannot be serialized")


@dataclass(frozen=True, slots=True, repr=False)
class ReadPhase(_PrivateRead):
    plan: UploadPlan
    record: UploadRecord
    authorization: AuthorizationCheck | None


@dataclass(frozen=True, slots=True, repr=False)
class ReadInput(_PrivateRead):
    plan: DatasetUploadPlanV2
    record: TransferRecordV2
    manifest: DatasetManifest
    baseline: ProviderDataset


def read_policy(plan: UploadPlan, accepted: bool) -> None:
    explicit = type(plan) is DatasetUploadPlanV2 and plan.admission_policy == "explicit_attempt"
    if not explicit:
        raise YorungeError("invalid_request" if accepted else "upload_plan_not_valid")
    if not accepted:
        raise YorungeError("approval_required")


def _stop_unreadable(repository: StateUploads, view: VersionedTransferView) -> ReadPhase | None:
    record = view.operation
    assert record is not None
    if record.workflow_latched and record.dataset_id is not None:
        return None
    stopped = repository.cleanup_expired(record.operation_id)
    assert stopped.operation is not None
    if stopped.operation.workflow_latched:
        raise OperationError("operation_uncertain", record.operation_id)
    return ReadPhase(stopped.plan, stopped.operation, None)


def load_read_input(
    operation_id: str, state_dir: Path | None, accepted: bool, clock: Clock
) -> ReadInput | ReadPhase:
    with open_existing_store(state_dir) as store:
        repository = StateUploads(store, clock=clock)
        with repository.phase(operation_id):
            view = repository.show(operation_id=operation_id)
            record = view.operation
            assert record is not None
            if record.status in TERMINAL:
                raise YorungeError("operation_conflict")
            repository.require_created_baseline(operation_id)
            # Missing response and unlatched expiry cleanup are deliberately
            # independent of read consent/config/credential availability.
            local = _stop_unreadable(repository, view)
            if local is not None:
                return local
            stamp = repository.cache.stamp()
            repository._takeover_allowed(record, stamp)
            read_policy(view.plan, accepted)
            if not acknowledged_stages(view):
                repository.cleanup_expired(operation_id)
                raise YorungeError("operation_uncertain")
            baseline = created_dataset(view)
            if baseline is None or type(view.plan) is not DatasetUploadPlanV2:
                raise YorungeError("upload_plan_not_valid")
            if type(record) is not TransferRecordV2:
                raise YorungeError("state_invalid")
            manifest = read_manifest(store.connection, view.plan)
            return ReadInput(view.plan, record, manifest, baseline)
