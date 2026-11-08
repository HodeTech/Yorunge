"""Readonly recovery algorithm; concrete state, credentials and HTTP stay outside.

The same four steps recover an original upload (v2) and a continuation (v3) that lack only their
metadata proof: the environment is told which it is by the record it holds.
"""

from typing import Protocol

from yorunge.domain.dataset_transfer_v2 import TransferRecordV2, TransferVerificationV2
from yorunge.domain.dataset_transfer_v3 import TransferRecordV3, TransferVerificationV3
from yorunge.domain.upload_checks import AuthorizationCheck


class ReadEnvironment(Protocol):
    async def current(self) -> AuthorizationCheck: ...
    def acquire(self, check: AuthorizationCheck) -> None: ...
    async def metadata(self) -> TransferVerificationV2 | TransferVerificationV3: ...
    def commit(
        self, proof: TransferVerificationV2 | TransferVerificationV3
    ) -> TransferRecordV2 | TransferRecordV3: ...


async def reconcile_read(environment: ReadEnvironment) -> TransferRecordV2 | TransferRecordV3:
    check = await environment.current()
    environment.acquire(check)
    proof = await environment.metadata()
    return environment.commit(proof)
