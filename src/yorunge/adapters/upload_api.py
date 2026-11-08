"""Real public transfer use cases; dependencies are composed here, never caller supplied."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from yorunge.adapters.capability_cache import SystemClock
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_continuation_approval import approve_continuation_plan
from yorunge.adapters.upload_continuation_start import run_upload_continuation
from yorunge.adapters.upload_original import run_upload_original
from yorunge.adapters.upload_preparation import UploadPreparationRuntime, read_approval_input
from yorunge.adapters.upload_public import show_upload, validate_local
from yorunge.adapters.upload_reconciliation import reconcile_upload
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_resume import UploadResumeRuntime
from yorunge.application.upload_inputs import revalidate_input
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.dataset_upload import (
    UploadOwner,
    UploadParameters,
    UploadStoragePolicy,
    provider_uuid,
)
from yorunge.domain.dataset_upload_v2 import (
    AdmissionPolicy,
    CostPolicy,
    DatasetUploadPlanV2,
    validate_policy_choice,
)
from yorunge.domain.errors import ErrorCode, OperationError, YorungeError
from yorunge.domain.models import Context, Model, Profile, Result
from yorunge.domain.upload_public import DatasetUploadSummary, UploadSummary
from yorunge.domain.upload_resume_report import DatasetUploadResumeReport
from yorunge.domain.upload_versions import UploadPlan, UploadRecord

T = TypeVar("T", bound=Model)
ContextFactory = Callable[[], tuple[Context, Profile]]
# What the public layer hands every use case that starts from a saved plan: the context and the
# profile a plan of either family (an original upload or a continuation) was made under.
ContextLoader = Callable[[DatasetUploadPlanV2 | DatasetContinuationPlanV3], tuple[Context, Profile]]
_CR = re.compile(r"(?:0|[1-9]\d*)(?:\.\d{1,6})?", re.ASCII)
_DIGEST = re.compile(r"[a-f0-9]{64}", re.ASCII)


def credit_micros(value: str | None, unpriced: bool) -> tuple[CostPolicy, int | None]:
    if type(unpriced) is not bool or (value is None) != unpriced:
        raise YorungeError("invalid_request")
    if unpriced:
        return "unpriced_accepted", None
    if type(value) is not str or len(value) > 32 or _CR.fullmatch(value) is None:
        raise YorungeError("invalid_request")
    whole, _, fraction = value.partition(".")
    micros = int(whole) * 1_000_000 + int(fraction.ljust(6, "0"))
    if micros > 2**63 - 1:
        raise YorungeError("invalid_request")
    return "bounded_required", micros


def _bound(code: ErrorCode, identity: Callable[[], str | None] | None) -> YorungeError:
    operation_id = identity() if identity is not None else None
    return OperationError(code, operation_id) if operation_id is not None else YorungeError(code)


def _safe(
    action: Callable[[], Result[T]],
    *,
    identity: Callable[[], str | None] | None = None,
) -> Result[T]:
    failure: YorungeError
    try:
        return action()
    except YorungeError as error:
        if isinstance(error, OperationError):
            failure = OperationError(
                error.code,
                error.operation_id or (identity() if identity is not None else None),
                reason_code=error.reason_code,
                capacity_kind=error.capacity_kind,
                blockers=error.blockers,
            )
        else:
            failure = _bound(error.code, identity)
    except KeyboardInterrupt:
        failure = _bound("request_cancelled", identity)
    except OSError:
        failure = _bound("file_unreadable", identity)
    except (ValueError, TypeError):
        failure = _bound("invalid_request", identity)
    failure.__cause__ = failure.__context__ = None
    raise failure


def prepare_upload(
    root: Path,
    manifest: Path,
    owner: UploadOwner,
    parameters: UploadParameters,
    project: str,
    load_context: ContextFactory,
    state_dir: Path | None,
    *,
    budget_cr: str | None,
    unpriced: bool,
    admission_policy: AdmissionPolicy,
    storage_origin: str | None,
) -> Result[DatasetUploadSummary]:
    validate_local(state_dir)

    def prepare() -> Result[DatasetUploadSummary]:
        if not isinstance(root, Path) or not isinstance(manifest, Path) or type(project) is not str:
            raise YorungeError("invalid_request")
        provider_uuid(project)
        selected_owner = revalidate_input(UploadOwner, owner)
        selected_parameters = revalidate_input(UploadParameters, parameters)
        cost_policy, budget = credit_micros(budget_cr, unpriced)
        if type(admission_policy) is not str:
            raise YorungeError("invalid_request")
        validate_policy_choice(admission_policy, cost_policy, budget)
        storage = UploadStoragePolicy(
            mode="proxy" if storage_origin is None else "direct", origin=storage_origin
        )
        if storage.mode != "proxy":
            raise YorungeError("unsupported_combination")
        context, profile = load_context()
        runtime = UploadPreparationRuntime(context, profile, state_dir)
        plan = runtime.prepare(
            root,
            manifest,
            owner=selected_owner,
            parameters=selected_parameters,
            storage=storage,
            admission_policy=admission_policy,
            cost_policy=cost_policy,
            budget_micros=budget,
        )
        return show_upload(state_dir, plan_id=plan.plan_id)

    return _safe(prepare)


def _plan_of(
    state_dir: Path | None, *, plan_id: str | None = None, operation_id: str | None = None
) -> UploadPlan:
    """The stored plan, to see which family it is before the use case of that family is chosen."""
    with open_existing_store(state_dir) as store:
        repository = StateUploads(store)
        with repository.phase(operation_id):
            return repository.show(plan_id=plan_id, operation_id=operation_id).plan


def approve_upload(
    plan_id: str,
    confirmed_digest: str,
    load_context: ContextLoader,
    state_dir: Path | None,
    *,
    authority: bool,
    unpriced: bool,
    unconfirmed: bool = False,
) -> Result[UploadSummary]:
    validate_local(state_dir, plan_id)

    def approve() -> Result[UploadSummary]:
        if (
            plan_id is None
            or type(confirmed_digest) is not str
            or _DIGEST.fullmatch(confirmed_digest) is None
            or type(authority) is not bool
            or type(unpriced) is not bool
            or type(unconfirmed) is not bool
        ):
            raise YorungeError("invalid_request")
        if isinstance(_plan_of(state_dir, plan_id=plan_id), DatasetContinuationPlanV3):
            approve_continuation_plan(
                plan_id,
                confirmed_digest,
                load_context,
                state_dir,
                authority=authority,
                unpriced=unpriced,
                unconfirmed=unconfirmed,
            )
            return show_upload(state_dir, plan_id=plan_id)
        if unconfirmed:
            raise YorungeError("invalid_request")  # unconfirmed files exist only in a continuation
        plan, _ = read_approval_input(
            plan_id, confirmed_digest, authority, unpriced, state_dir, SystemClock()
        )
        context, profile = load_context(plan)
        runtime = UploadPreparationRuntime(context, profile, state_dir)
        runtime.approve(
            plan_id,
            confirmed_digest,
            acknowledge_unverified_authority=authority,
            acknowledge_unpriced_cost=unpriced,
        )
        return show_upload(state_dir, plan_id=plan_id)

    return _safe(approve)


def start_upload(
    plan_id: str,
    load_context: ContextLoader,
    state_dir: Path | None,
) -> Result[UploadSummary]:
    validate_local(state_dir, plan_id)
    if plan_id is None:
        raise YorungeError("invalid_request")

    record: UploadRecord | None = None

    def start() -> Result[UploadSummary]:
        nonlocal record
        if isinstance(_plan_of(state_dir, plan_id=plan_id), DatasetContinuationPlanV3):
            record = run_upload_continuation(plan_id, state_dir, load_context).record
        else:
            record = run_upload_original(plan_id, state_dir, load_context).record
        if record.status != "succeeded":
            code: ErrorCode = "operation_conflict"
            if record.workflow_latched and record.status in {"running", "unknown", "admitted"}:
                code = "operation_uncertain"
            raise OperationError(code, record.operation_id)
        return show_upload(state_dir, operation_id=record.operation_id)

    return _safe(start, identity=lambda: record.operation_id if record is not None else None)


def recover_upload(
    operation_id: str,
    load_context: ContextLoader,
    state_dir: Path | None,
    *,
    accepted: bool,
) -> Result[UploadSummary]:
    validate_local(state_dir, operation_id)
    if operation_id is None or type(accepted) is not bool:
        raise YorungeError("invalid_request")

    def recover() -> Result[UploadSummary]:
        phase = reconcile_upload(
            operation_id, state_dir, load_context, accept_unverified_read=accepted
        )
        return show_upload(state_dir, operation_id=phase.record.operation_id)

    return _safe(recover, identity=lambda: operation_id)


def resume_upload(
    operation_id: str,
    load_context: ContextLoader,
    state_dir: Path | None,
    *,
    prepare: bool,
    accept_unverified_read: bool,
    accept_unconfirmed_effects: bool,
) -> Result[DatasetUploadResumeReport]:
    """The report of what an interrupted upload still needs; with ``prepare``, the plan too."""
    validate_local(state_dir, operation_id)
    if operation_id is None:
        raise YorungeError("invalid_request")

    def resume() -> Result[DatasetUploadResumeReport]:
        # Judged before the store is touched, but inside `_safe`: the error names the source.
        flags = (prepare, accept_unverified_read, accept_unconfirmed_effects)
        if any(type(flag) is not bool for flag in flags):
            raise YorungeError("invalid_request")
        if accept_unconfirmed_effects and not prepare:
            raise YorungeError("invalid_request")  # a choice of the plan, asked for without a plan
        # The source's own plan names the scope (profile, project) the context is loaded under.
        plan = _plan_of(state_dir, operation_id=operation_id)
        if not isinstance(plan, DatasetUploadPlanV2 | DatasetContinuationPlanV3):
            raise YorungeError("state_invalid")  # a v1 source is history; it cannot be continued
        context, profile = load_context(plan)
        runtime = UploadResumeRuntime(context, profile, state_dir)
        report = runtime.resume(
            operation_id,
            accept_unverified_read=accept_unverified_read,
            prepare=prepare,
            accept_unconfirmed_effects=accept_unconfirmed_effects,
        )
        return Result[DatasetUploadResumeReport](data=report)

    return _safe(resume, identity=lambda: operation_id)
