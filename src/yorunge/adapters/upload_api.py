"""Real public transfer use cases; dependencies are composed here, never caller supplied."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from yorunge.adapters.capability_cache import SystemClock
from yorunge.adapters.upload_original import ContextLoader, run_upload_original
from yorunge.adapters.upload_preparation import UploadPreparationRuntime, read_approval_input
from yorunge.adapters.upload_public import show_upload, validate_local
from yorunge.adapters.upload_reconciliation import reconcile_upload
from yorunge.application.upload_inputs import revalidate_input
from yorunge.domain.dataset_upload import (
    UploadOwner,
    UploadParameters,
    UploadStoragePolicy,
    provider_uuid,
)
from yorunge.domain.dataset_upload_v2 import AdmissionPolicy, CostPolicy, validate_policy_choice
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.models import Context, Model, Profile, Result
from yorunge.domain.upload_public import DatasetUploadSummary

T = TypeVar("T", bound=Model)
ContextFactory = Callable[[], tuple[Context, Profile]]
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


def _safe(action: Callable[[], Result[T]]) -> Result[T]:
    failure: YorungeError
    try:
        return action()
    except YorungeError as error:
        if isinstance(error, OperationError):
            failure = OperationError(
                error.code,
                error.operation_id,
                reason_code=error.reason_code,
                capacity_kind=error.capacity_kind,
            )
        else:
            failure = YorungeError(error.code)
    except KeyboardInterrupt:
        failure = YorungeError("request_cancelled")
    except OSError:
        failure = YorungeError("file_unreadable")
    except (ValueError, TypeError):
        failure = YorungeError("invalid_request")
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


def approve_upload(
    plan_id: str,
    confirmed_digest: str,
    load_context: ContextLoader,
    state_dir: Path | None,
    *,
    authority: bool,
    unpriced: bool,
) -> Result[DatasetUploadSummary]:
    validate_local(state_dir, plan_id)

    def approve() -> Result[DatasetUploadSummary]:
        if (
            plan_id is None
            or type(confirmed_digest) is not str
            or _DIGEST.fullmatch(confirmed_digest) is None
            or type(authority) is not bool
            or type(unpriced) is not bool
        ):
            raise YorungeError("invalid_request")
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
) -> Result[DatasetUploadSummary]:
    validate_local(state_dir, plan_id)
    if plan_id is None:
        raise YorungeError("invalid_request")

    def start() -> Result[DatasetUploadSummary]:
        phase = run_upload_original(plan_id, state_dir, load_context)
        return show_upload(state_dir, operation_id=phase.record.operation_id)

    return _safe(start)


def recover_upload(
    operation_id: str,
    load_context: ContextLoader,
    state_dir: Path | None,
    *,
    accepted: bool,
) -> Result[DatasetUploadSummary]:
    validate_local(state_dir, operation_id)
    if operation_id is None or type(accepted) is not bool:
        raise YorungeError("invalid_request")

    def recover() -> Result[DatasetUploadSummary]:
        phase = reconcile_upload(
            operation_id, state_dir, load_context, accept_unverified_read=accepted
        )
        return show_upload(state_dir, operation_id=phase.record.operation_id)

    return _safe(recover)
