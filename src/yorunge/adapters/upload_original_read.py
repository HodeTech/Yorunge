"""Initial-owner metadata proof; no source files, caller proof or read takeover."""

from __future__ import annotations

import time
from datetime import timedelta
from typing import TYPE_CHECKING

from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.dataset_transfer_v2 import TransferRecordV2, TransferVerificationV2
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_checks import AuthorizationCheck

if TYPE_CHECKING:
    from yorunge.adapters.upload_original import _Environment
    from yorunge.adapters.upload_read_access import ReadAccess


def _deadline(environment: _Environment, check: AuthorizationCheck, access: ReadAccess) -> float:
    record = environment.record
    assert record is not None and record.lease is not None
    now = environment.runtime.clock.now()
    ends = [
        instant(record.lease.expires_at) - timedelta(seconds=5),
        instant(record.approval.expires_at) - timedelta(seconds=5),
        instant(environment.plan.expires_at) - timedelta(seconds=5),
        instant(check.checked_at) + timedelta(seconds=30),
    ]
    if access.grant is not None:
        ends.append(instant(access.grant.expires_at) - timedelta(seconds=5))
    remaining = min(30.0, (min(ends) - now).total_seconds())
    result = min(environment.end - 5, time.monotonic() + remaining)
    if remaining <= 0 or time.monotonic() >= result:
        raise YorungeError("execution_timeout")
    return result


async def verify_original(environment: _Environment) -> TransferRecordV2:
    record, baseline = environment.record, environment.baseline
    assert record is not None and record.lease is not None and baseline is not None
    with environment.repository() as repository:
        repository.prepare_initial_read(record.operation_id, record.lease)
    environment._renew_for_probe()
    check = await environment.reader.read_authorization(
        environment.client, baseline, environment.plan.parameters
    )
    record = environment.record
    assert record is not None and record.lease is not None
    with environment.repository() as repository:
        access = repository.prepare_initial_read(
            record.operation_id, record.lease, authorization=check
        )
    assert access is not None
    observed_at = timestamp(environment.runtime.clock.now())
    files = await environment.port.items(
        environment.client, baseline.id, deadline=_deadline(environment, check, access)
    )
    proof = TransferVerificationV2(
        schema_version=2,
        dataset_id=baseline.id,
        project_id=environment.plan.scope.project_id,
        scope=access.scope,
        authorization_policy=access.policy,
        grant=access.grant,
        observed_at=observed_at,
        files=files,
    )
    with environment.repository() as repository:
        view = repository.verified(record.operation_id, record.lease, proof, authorization=check)
        assert type(view.operation) is TransferRecordV2
        environment.record = view.operation
    return view.operation
