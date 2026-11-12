"""Metadata for an acquired read lease; expired write approvals are historical only.

The proof is the whole dataset, N files, whichever family the source is: an original upload's
(``TransferVerificationV2``) or a continuation's (``TransferVerificationV3``, built by the one
constructor the continuation's own closing read uses).
"""

from __future__ import annotations

import time
from datetime import timedelta
from typing import TYPE_CHECKING

from yorunge.adapters.platform_upload_port import ObservedUploadPort
from yorunge.adapters.upload_continuation_read import continuation_proof
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.dataset_transfer_v2 import TransferVerificationV2
from yorunge.domain.dataset_transfer_v3 import TransferVerificationV3
from yorunge.domain.errors import YorungeError

if TYPE_CHECKING:
    from yorunge.adapters.upload_read_access import ReadAccess
    from yorunge.adapters.upload_reconciliation import _ReadEnvironment


def _deadline(environment: _ReadEnvironment, access: ReadAccess) -> float:
    owner, check = environment.owner, environment.authorization
    assert owner is not None and check is not None
    ends = [
        instant(owner.expires_at) - timedelta(seconds=5),
        instant(check.checked_at) + timedelta(seconds=30),
    ]
    if access.grant is not None:
        ends.append(instant(access.grant.expires_at) - timedelta(seconds=5))
    remaining = min(30.0, (min(ends) - environment.runtime.clock.now()).total_seconds())
    result = min(environment.reader._budget.end - 5, time.monotonic() + remaining)
    if remaining <= 0 or time.monotonic() >= result:
        raise YorungeError("execution_timeout")
    return result


async def observe_metadata(
    environment: _ReadEnvironment,
) -> TransferVerificationV2 | TransferVerificationV3:
    owner, check = environment.owner, environment.authorization
    assert owner is not None and check is not None
    environment.require_current(check)
    with environment.repository() as repository:
        access = repository.prepare_recovery_read(
            environment.record.operation_id, owner, check, accept_unverified_read=True
        )
    environment.require_current(check)
    loaded, reader = environment.loaded, environment.reader
    port = ObservedUploadPort(
        loaded.plan,
        loaded.manifest,
        environment.scope,
        environment.bound,
        reader._credential,
        reader._budget,
        utc_clock=environment.runtime.clock.now,
    )
    observed_at = timestamp(environment.runtime.clock.now())
    files = await port.items(
        environment.client, loaded.baseline.id, deadline=_deadline(environment, access)
    )
    environment.require_current(check)
    if isinstance(loaded.plan, DatasetContinuationPlanV3):
        return continuation_proof(loaded.plan, loaded.baseline.id, access, observed_at, files)
    return TransferVerificationV2(
        schema_version=2,
        dataset_id=loaded.baseline.id,
        project_id=environment.scope.project_id,
        scope=access.scope,
        authorization_policy=access.policy,
        grant=access.grant,
        observed_at=observed_at,
        files=files,
    )
