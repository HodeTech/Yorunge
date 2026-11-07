"""Current read-only authority selection; fallback never creates write authority."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Literal

from yorunge.adapters.capability_cache import Stamp, TimeGate
from yorunge.adapters.upload_store import VersionedTransferView, decode
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3, DatasetUploadApprovalV3
from yorunge.domain.dataset_upload import UploadGrant, UploadScope
from yorunge.domain.dataset_upload_v2 import DatasetUploadApprovalV2, DatasetUploadPlanV2
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_checks import AuthorizationCheck

if TYPE_CHECKING:
    from yorunge.adapters.upload_repository import StateUploads


@dataclass(frozen=True)
class ReadAccess:
    scope: UploadScope
    policy: Literal["verified_read", "explicit_read_attempt"]
    grant: UploadGrant | None


def authorize_read(
    repository: StateUploads,
    view: VersionedTransferView,
    stamp: Stamp,
    gate: TimeGate,
    *,
    grant: UploadGrant | None,
    authorization: AuthorizationCheck | None,
    accept_unverified_read: bool,
    initial_owner: bool,
) -> ReadAccess:
    record = view.operation
    assert record is not None
    explicit = (
        isinstance(view.plan, DatasetUploadPlanV2 | DatasetContinuationPlanV3)
        and view.plan.admission_policy == "explicit_attempt"
    )
    _flags(explicit, initial_owner, accept_unverified_read)
    if initial_owner and explicit:
        _initial_approval(view, stamp, gate)
    check = _current_check(repository, view, stamp, gate, authorization)
    grant = _selected_grant(grant, check)
    if grant is not None:
        repository._read_grant(view, grant, stamp, gate)
        return ReadAccess(grant.scope, "verified_read", grant)
    if not explicit:
        raise YorungeError("upload_plan_not_valid")
    _fallback_consent(view, initial_owner, accept_unverified_read)
    if check is None or check.outcome != "not_exposed":
        raise YorungeError("upload_plan_not_valid")
    return ReadAccess(check.scope, "explicit_read_attempt", None)


def _flags(explicit: bool, initial: bool, accepted: bool) -> None:
    if type(accepted) is not bool or (accepted and (not explicit or initial)):
        raise YorungeError("invalid_request")


def _initial_approval(view: VersionedTransferView, stamp: Stamp, gate: TimeGate) -> None:
    approval = view.approval
    if (
        approval is None
        or approval.status != "approved"
        or not instant(approval.approved_at) <= stamp.now < instant(approval.expires_at)
    ):
        raise YorungeError("approval_required")
    gate.require_range(
        instant(approval.approved_at), instant(approval.expires_at), error="approval_required"
    )


def initial_read_consent(view: VersionedTransferView, stamp: Stamp, gate: TimeGate) -> None:
    """Before network: actual saved read authority or the initial fallback consent."""
    _initial_approval(view, stamp, gate)
    grant = view.plan.grant
    if grant is not None and "read_created_dataset" in grant.permissions:
        gate.require_range(
            instant(grant.checked_at), instant(grant.expires_at), error="upload_plan_not_valid"
        )
        return
    if (
        not isinstance(view.plan, DatasetUploadPlanV2 | DatasetContinuationPlanV3)
        or view.plan.admission_policy != "explicit_attempt"
    ):
        raise YorungeError("upload_plan_not_valid")
    _fallback_consent(view, True, False)


def _selected_grant(
    grant: UploadGrant | None, check: AuthorizationCheck | None
) -> UploadGrant | None:
    if check is None:
        return grant
    if grant is not None and grant != check.grant:
        raise YorungeError("upload_plan_not_valid")
    return check.grant


def _fallback_consent(view: VersionedTransferView, initial: bool, accepted: bool) -> None:
    record = view.operation
    assert record is not None
    if initial:
        approval = record.approval
        if (
            not isinstance(approval, DatasetUploadApprovalV2 | DatasetUploadApprovalV3)
            or not approval.acknowledge_unverified_authority
        ):
            raise YorungeError("approval_required")
    elif not accepted:
        raise YorungeError("approval_required")


def _current_check(
    repository: StateUploads,
    view: VersionedTransferView,
    stamp: Stamp,
    gate: TimeGate,
    authorization: AuthorizationCheck | None,
) -> AuthorizationCheck | None:
    if authorization is None:
        return None
    record = view.operation
    assert record is not None
    check = decode(AuthorizationCheck, authorization.encoded().decode("ascii"))
    repository._credential(check.scope, stamp)
    # Scope excludes only the historical credential/epoch/generation dimensions.
    from yorunge.domain.dataset_transfer import scope_target

    if scope_target(check.scope) != scope_target(view.plan.scope):
        raise YorungeError("state_changed")
    check.require_current(
        check.scope, "read_created_dataset", record.dataset_id, timestamp(stamp.now)
    )
    checked = instant(check.checked_at)
    gate.require_range(
        checked, checked + timedelta(seconds=30, microseconds=1), error="upload_plan_not_valid"
    )
    return check
