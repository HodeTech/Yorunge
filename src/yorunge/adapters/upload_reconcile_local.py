"""Local-only reconciliation selection; never read source files or mint write access.

What is reconciled is an original upload (v2) or a continuation (v3) whose every stage is
acknowledged and that lacks only its metadata proof. A source that already has a continuation is
history and is not reconciled: nothing local or remote touches it again.
"""

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
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_transfer import TERMINAL
from yorunge.domain.dataset_transfer_v2 import TransferRecordV2
from yorunge.domain.dataset_transfer_v3 import TransferRecordV3
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
    plan: DatasetUploadPlanV2 | DatasetContinuationPlanV3
    record: TransferRecordV2 | TransferRecordV3
    manifest: DatasetManifest
    baseline: ProviderDataset


def read_policy(plan: UploadPlan, accepted: bool) -> None:
    explicit = (
        isinstance(plan, DatasetUploadPlanV2 | DatasetContinuationPlanV3)
        and plan.admission_policy == "explicit_attempt"
    )
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
            # A source with a continuation is not reconciled, whatever consent or credential is
            # at hand: the successor is named and nothing is read or written.
            repository.require_no_successor(operation_id)
            required = repository.require_created_baseline(operation_id)
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
            plan = view.plan
            if isinstance(plan, DatasetContinuationPlanV3):
                # A continuation sent no create: the dataset is its root's, found as its lineage
                # was validated.
                baseline = required
                if baseline is None:
                    raise YorungeError("upload_plan_not_valid")
                if not isinstance(record, TransferRecordV3):
                    raise YorungeError("state_invalid")
            else:
                baseline = created_dataset(view)
                if baseline is None or not isinstance(plan, DatasetUploadPlanV2):
                    raise YorungeError("upload_plan_not_valid")
                if not isinstance(record, TransferRecordV2):
                    raise YorungeError("state_invalid")
            manifest = read_manifest(store.connection, plan)
            return ReadInput(plan, record, manifest, baseline)
