"""The start of a continuation: from an approved plan to a verified dataset.

What decides whether the plan still stands is looked at before the operation exists: the plan and
its approval, the source's journal, the folder and the dataset as the provider lists it now. The
journal comes first, because it needs nothing from the folder or the provider: a source that is no
longer alone is refused at once. The plan carries the classification it was approved on; a dataset
that no longer classifies the same way, whatever the cause, ends the start before a request that
changes anything is sent or a line is written (``continuation_remote_changed``: prepare the
continuation again). The stages and the closing read are those of ``upload_continuation``; this
module only composes them, once, in one invocation.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from yorunge.adapters.capability_cache import Clock, SystemClock
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_chain import ResumeSource
from yorunge.adapters.upload_continuation import ContinuationStages, run_stages
from yorunge.adapters.upload_http import UploadSession
from yorunge.adapters.upload_input_files import UploadInputObservation, capture_upload_input
from yorunge.adapters.upload_original import _plan_id
from yorunge.adapters.upload_preparation import SessionFactory, require_upload_sync_context
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_resume import UploadResumeRuntime
from yorunge.adapters.upload_store import read_manifest
from yorunge.application.upload_inputs import require_distinct_upload_content
from yorunge.application.upload_workflow import complete_continuation
from yorunge.domain.capabilities import instant
from yorunge.domain.credentials import BoundCredential
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3, binding_matches
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_transfer_v3 import TransferRecordV3
from yorunge.domain.dataset_upload import UploadScope
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.models import Context, Profile
from yorunge.domain.platform_upload import ProviderDataset
from yorunge.domain.upload_resume import ChainSummary, classify

ContinuationContextLoader = Callable[[DatasetContinuationPlanV3], tuple[Context, Profile]]

# What the source's own record and its descendants say. The admission refuses on these, naming the
# operation that stands in the way; the start says the same before it asks the provider anything.
_CONFLICTS = frozenset(
    {"source_terminal", "source_active", "source_superseded", "source_ineligible", "create_unknown"}
)


@dataclass(frozen=True, slots=True, repr=False)
class ContinuationPhase:
    """The operation of a plan and whether this invocation only found it (it sent nothing)."""

    plan: DatasetContinuationPlanV3
    record: TransferRecordV3
    existing: bool

    def __repr__(self) -> str:
        return "<continuation phase private>"

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("private continuation phase cannot be serialized")


def _initial(
    plan_id: str, state_dir: Path | None, clock: Clock
) -> ContinuationPhase | tuple[DatasetContinuationPlanV3, DatasetManifest]:
    """The operation the plan already has, found without a network; else the plan to start."""
    with open_existing_store(state_dir) as store:
        view = StateUploads(store, clock=clock).show(plan_id=plan_id)
        plan, approval = view.plan, view.approval
        if type(plan) is not DatasetContinuationPlanV3:
            raise YorungeError("upload_plan_not_valid")
        if view.operation is not None:
            # It may have been cancelled: the caller looks at its status.
            assert type(view.operation) is TransferRecordV3
            return ContinuationPhase(plan, view.operation, True)
        if plan.status == "draft":
            raise YorungeError("upload_plan_not_valid")
        if approval is None or approval.status != "approved":
            raise YorungeError("approval_required")
        now = clock.now()
        if not (instant(plan.prepared_at) <= now < instant(plan.expires_at)) or not (
            instant(approval.approved_at) <= now < instant(approval.expires_at)
        ):
            raise YorungeError("upload_plan_not_valid")
        manifest = read_manifest(store.connection, plan)
        require_distinct_upload_content(manifest)
        return plan, manifest


def _journal_clear(
    runtime: UploadResumeRuntime, plan: DatasetContinuationPlanV3
) -> tuple[ResumeSource, ChainSummary]:
    """The source and its lineage, if what the journal alone says leaves the plan standing.

    Nothing is asked of the folder or the provider: a source that is no longer alone is a conflict
    with the operation in the way, and one the journal rules out otherwise is a plan that has been
    outlived. The admission refuses on the same facts, so this only says so sooner and cheaper.
    """
    source_id = plan.continuation.source_operation_id
    source, _ = runtime._read_source(source_id)
    chain, blockers, related = runtime._journal(source)
    if _CONFLICTS.intersection(blockers):
        raise OperationError("operation_conflict", related or source_id)
    if blockers:
        raise YorungeError("continuation_remote_changed")
    return source, chain


def _dataset_stands(
    runtime: UploadResumeRuntime,
    plan: DatasetContinuationPlanV3,
    bound: BoundCredential,
    scope: UploadScope,
    source: ResumeSource,
    chain: ChainSummary,
    end: float,
) -> ProviderDataset:
    """The dataset the plan extends, if the provider still shows what the plan was approved on.

    It is listed and classified as ``resume`` classifies it; the plan stands only if the selection,
    the files it is unsure of and both digests are those it was prepared with. A failure to look
    (access, rate, transport) is that failure, not a change.
    """
    baseline = source.baseline
    assert baseline is not None  # a source whose create is unknown is a conflict above
    _, inventory = runtime._read_remote(bound, scope, baseline, plan, source.manifest, end)
    binding = plan.continuation
    if inventory is None or not binding_matches(
        binding, classify(source.manifest, chain, inventory)
    ):
        # The dataset is no longer shown to be the baseline, or no longer classifies as approved.
        raise YorungeError("continuation_remote_changed")
    return baseline


def _looked_at(
    runtime: UploadResumeRuntime,
    plan: DatasetContinuationPlanV3,
    manifest: DatasetManifest,
    end: float,
) -> tuple[BoundCredential, UploadInputObservation, ProviderDataset]:
    """Everything the start stands on, looked at before the operation exists; nothing is written."""
    source, chain = _journal_clear(runtime, plan)
    bound, scope = runtime._bind(plan.scope.owner)
    if scope != plan.scope:
        raise YorungeError("state_changed")
    runtime._check_scope(bound, scope)
    inputs = capture_upload_input(
        Path(plan.root.anchor),
        manifest,
        bound.credential.secret,
        end=end,
        expected_root=plan.root,
    )
    runtime._check_scope(bound, scope)
    baseline = _dataset_stands(runtime, plan, bound, scope, source, chain, end)
    return bound, inputs, baseline


def _admitted_meanwhile(
    plan_id: str, state_dir: Path | None, clock: Clock
) -> ContinuationPhase | None:
    """The operation the plan got while this invocation was looking, if it got one (no request)."""
    try:
        found = _initial(plan_id, state_dir, clock)
    except YorungeError:
        return None
    return found if isinstance(found, ContinuationPhase) else None


def _explained(
    runtime: UploadResumeRuntime, plan: DatasetContinuationPlanV3, refusal: YorungeError
) -> YorungeError:
    """The refusal of a look, or the sibling operation that is the reason for it.

    The look takes a while, and a sibling plan of the same source may have been admitted and have
    sent its files meanwhile: the dataset then differs from what this plan was approved on, and the
    cause is that operation, which the journal names. Neither the folder nor the provider is asked.
    """
    try:
        _journal_clear(runtime, plan)
    except OperationError as conflict:
        if conflict.code == "operation_conflict":
            return conflict
    except YorungeError:
        pass
    return refusal


def run_upload_continuation(
    plan_id: str,
    state_dir: Path | None,
    load_context: ContinuationContextLoader,
    *,
    session_factory: SessionFactory = UploadSession,
    clock: Clock | None = None,
) -> ContinuationPhase:
    """Start the approved continuation ``plan_id``; private, the public layer shows a summary.

    An operation the plan already has is returned without a network (it may be cancelled). Else the
    plan, its approval, the folder and the dataset are checked, and the operation is admitted, the
    selected files are sent and the dataset is proved. A process that does not own the operation
    (another admitted it first) sends nothing and returns the record as it stands.
    """
    started = time.monotonic()
    require_upload_sync_context()
    _plan_id(plan_id)
    if state_dir is not None and not isinstance(state_dir, Path):
        raise YorungeError("invalid_request")
    clock = clock or SystemClock()
    loaded = _initial(plan_id, state_dir, clock)
    if isinstance(loaded, ContinuationPhase):
        return loaded
    plan, manifest = loaded
    context, profile = load_context(plan)
    runtime = UploadResumeRuntime(
        context, profile, state_dir, session_factory=session_factory, clock=clock
    )
    owned = False

    async def start(environment: ContinuationStages) -> TransferRecordV3:
        nonlocal owned
        record = await complete_continuation(environment)
        owned = environment.write_owned
        return record

    with runtime._invocation() as invocation_end:
        end = min(started + 900, invocation_end)
        try:
            bound, inputs, baseline = _looked_at(runtime, plan, manifest, end)
        except YorungeError as refusal:
            # The look takes a while (the folder is hashed, the dataset listed), and another
            # invocation may have admitted this very plan meanwhile: its operation is the answer,
            # found without a request, whatever the look has to say of a journal or a dataset that
            # operation changed. A refusal stands only while the plan has no operation of its own;
            # if a sibling plan of the source has one, that conflict is what is reported.
            found = _admitted_meanwhile(plan_id, state_dir, clock)
            if found is None:
                raise _explained(runtime, plan, refusal) from None
            return found
        record = run_stages(runtime, plan, bound, inputs, baseline, end, start)
    return ContinuationPhase(plan, record, not owned)
