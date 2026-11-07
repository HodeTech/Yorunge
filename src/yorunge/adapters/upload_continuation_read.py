"""The closing read of a continuation: the whole dataset, read once more after the stages.

A continuation that sent files has every stage acknowledged; one that sent none (``M=0``, a check
only) is still admitted. Either ends the same way: the key's permission to read the dataset is
looked at, all N files of the manifest are listed as the provider holds them (the ones the
continuation sent and the ones that were already there) and the proof of that listing closes the
operation. A read that fails is not a failed upload: a check-only continuation is cancelled with the
read's own error (it sent nothing, so nothing is uncertain), one that sent files is left unknown
with every stage known to be done and only the proof missing.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from yorunge.adapters.upload_original_read import _deadline
from yorunge.adapters.upload_reconciliation import READ_FAILURES
from yorunge.domain.capabilities import timestamp
from yorunge.domain.dataset_transfer_v3 import TransferRecordV3, TransferVerificationV3
from yorunge.domain.errors import ErrorCode, YorungeError
from yorunge.domain.upload_checks import AuthorizationCheck, AuthorizationOutcome

if TYPE_CHECKING:
    from yorunge.adapters.upload_continuation import ContinuationStages


def _negative(environment: ContinuationStages, code: ErrorCode) -> AuthorizationCheck:
    """The failed read as the check ``read_failed`` takes: the read's own code, observed now."""
    outcome: AuthorizationOutcome = "unavailable"
    if code == "remote_access_denied":
        outcome = "denied"
    elif code == "invalid_response":
        outcome = "invalid"
    return environment.reader._check(
        "read_created_dataset",
        environment.baseline.id,
        timestamp(environment.runtime.clock.now()),
        outcome,
        code,
    )


@contextmanager
def _provider_read(environment: ContinuationStages) -> Iterator[None]:
    """What the provider answers to a read is the failure of the read, not of the upload.

    The repository records it (a check-only continuation is cancelled with the read's own error,
    one that sent files is left unknown with only its proof missing) and ends in the error that
    says so. Any other failure, and anything the repository itself says, is left to the
    environment.
    """
    try:
        yield
    except YorungeError as error:
        if error.code not in READ_FAILURES:
            raise
        record = environment.record
        assert record is not None and record.lease is not None
        with environment.repository() as repository:
            repository.read_failed(
                record.operation_id, record.lease, _negative(environment, error.code)
            )
        raise  # ``read_failed`` ends in an error of its own; else the read's error stands


async def verify_continuation(environment: ContinuationStages) -> TransferRecordV3:
    """The metadata proof of the whole dataset, N files, sent or already there."""
    record = environment.record
    assert record is not None and record.lease is not None
    with environment.repository() as repository:
        repository.prepare_initial_read(record.operation_id, record.lease)
    environment._renew_for_probe()
    with _provider_read(environment):
        check = await environment.reader.read_authorization(
            environment.client, environment.baseline, environment.plan.parameters
        )
        # A read the provider failed comes back as a check that names the failure.
        check.require_current(
            environment.plan.scope,
            "read_created_dataset",
            environment.baseline.id,
            timestamp(environment.runtime.clock.now()),
        )
    record = environment.record
    assert record is not None and record.lease is not None
    with environment.repository() as repository:
        access = repository.prepare_initial_read(
            record.operation_id, record.lease, authorization=check
        )
    assert access is not None
    observed_at = timestamp(environment.runtime.clock.now())
    with _provider_read(environment):
        files = await environment.port.items(
            environment.client,
            environment.baseline.id,
            deadline=_deadline(environment, check, access),
        )
    proof = TransferVerificationV3(
        schema_version=3,
        dataset_id=environment.baseline.id,
        project_id=environment.plan.scope.project_id,
        scope=access.scope,
        authorization_policy=access.policy,
        grant=access.grant,
        observed_at=observed_at,
        files=files,
    )
    with environment.repository() as repository:
        view = repository.verified(record.operation_id, record.lease, proof, authorization=check)
        assert type(view.operation) is TransferRecordV3
        environment.record = view.operation
    return view.operation
