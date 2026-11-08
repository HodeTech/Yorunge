"""The human's approval of a saved continuation plan: looked at first, then recorded.

Approving a continuation is not a copy of approving an original upload. The plan names a source
whose journal may have moved, a folder whose files must still be those that were planned, and a
dataset that must still classify as it did when the plan was prepared; and the approval is recorded
on the fresh check of what the plan does first (an upload to the baseline dataset, or a read of it
for a check-only continuation). All of that is looked at here exactly as the start looks at it,
before anything is written, and the approval is the only thing this module writes.
"""

from __future__ import annotations

import time
from pathlib import Path

from yorunge.adapters.capability_cache import Clock, SystemClock
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_continuation import ContinuationStages, run_stages
from yorunge.adapters.upload_continuation_start import ContinuationContextLoader, _looked_at
from yorunge.adapters.upload_http import UploadSession
from yorunge.adapters.upload_original import _plan_id
from yorunge.adapters.upload_preparation import SessionFactory, require_upload_sync_context
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_resume import UploadResumeRuntime
from yorunge.adapters.upload_store import read_manifest
from yorunge.application.upload_inputs import require_distinct_upload_content
from yorunge.domain.capabilities import instant
from yorunge.domain.dataset_continuation import (
    DatasetContinuationPlanV3,
    DatasetUploadApprovalV3,
    require_continuation_acknowledgements,
)
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.errors import YorungeError

_DIGEST_LENGTH = 64


def _approval_input(
    plan_id: str,
    confirmed_digest: str,
    flags: tuple[bool, bool, bool],
    state_dir: Path | None,
    clock: Clock,
) -> tuple[DatasetContinuationPlanV3, DatasetManifest]:
    """The local gate: a plan that can be approved at all, with the choices it needs and no others.

    The same order as an original upload's: the plan and its window, the digest the user confirmed,
    then the acknowledgements, and only then whether it already has an approval or an operation.
    """
    with open_existing_store(state_dir) as store:
        repository = StateUploads(store, clock=clock)
        view = repository.show(plan_id=plan_id)
        plan = view.plan
        if (
            type(plan) is not DatasetContinuationPlanV3
            or plan.status == "draft"
            or plan.digest != confirmed_digest
            or not instant(plan.prepared_at) <= clock.now() < instant(plan.expires_at)
        ):
            raise YorungeError("upload_plan_not_valid")
        authority, unpriced, unconfirmed = flags
        require_continuation_acknowledgements(
            plan, authority=authority, unpriced=unpriced, unconfirmed=unconfirmed
        )
        if view.approval is not None or view.operation is not None:
            raise YorungeError("operation_conflict")
        with repository.phase():
            manifest = read_manifest(store.connection, plan)
        require_distinct_upload_content(manifest)
        return plan, manifest


def approve_continuation_plan(
    plan_id: str,
    confirmed_digest: str,
    load_context: ContinuationContextLoader,
    state_dir: Path | None,
    *,
    authority: bool,
    unpriced: bool,
    unconfirmed: bool,
    session_factory: SessionFactory = UploadSession,
    clock: Clock | None = None,
) -> DatasetUploadApprovalV3:
    """Approve exactly the continuation plan whose digest the user confirmed.

    ``authority``, ``unpriced`` and ``unconfirmed`` are the user's acknowledgements of an
    unverified authority, an unpriced cost and files whose last confirm may or may not have landed:
    each is required exactly when the plan needs it. Nothing but the approval is written.
    """
    started = time.monotonic()
    require_upload_sync_context()
    _plan_id(plan_id)
    flags = (authority, unpriced, unconfirmed)
    if (
        type(confirmed_digest) is not str
        or len(confirmed_digest) != _DIGEST_LENGTH
        or any(type(flag) is not bool for flag in flags)
        or (state_dir is not None and not isinstance(state_dir, Path))
    ):
        raise YorungeError("invalid_request")
    clock = clock or SystemClock()
    plan, manifest = _approval_input(plan_id, confirmed_digest, flags, state_dir, clock)
    context, profile = load_context(plan)
    runtime = UploadResumeRuntime(
        context, profile, state_dir, session_factory=session_factory, clock=clock
    )

    async def approve(environment: ContinuationStages) -> DatasetUploadApprovalV3:
        check = await environment.admission()
        with environment.repository() as repository:
            return repository.approve_continuation(
                plan.plan_id,
                confirmed_digest,
                check,
                acknowledge_unverified_authority=authority,
                acknowledge_unpriced_cost=unpriced,
                acknowledge_unconfirmed_effects=unconfirmed,
            )

    with runtime._invocation() as invocation_end:
        end = min(started + 900, invocation_end)
        bound, inputs, baseline = _looked_at(runtime, plan, manifest, end)
        return run_stages(runtime, plan, bound, inputs, baseline, end, approve)
