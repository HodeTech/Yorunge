"""Readonly recovery algorithm; concrete state, credentials and HTTP stay outside."""

from typing import Protocol

from yorunge.domain.dataset_transfer_v2 import TransferRecordV2, TransferVerificationV2
from yorunge.domain.upload_checks import AuthorizationCheck


class ReadEnvironment(Protocol):
    async def current(self) -> AuthorizationCheck: ...
    def acquire(self, check: AuthorizationCheck) -> None: ...
    async def metadata(self) -> TransferVerificationV2: ...
    def commit(self, proof: TransferVerificationV2) -> TransferRecordV2: ...


async def reconcile_read(environment: ReadEnvironment) -> TransferRecordV2:
    check = await environment.current()
    environment.acquire(check)
    proof = await environment.metadata()
    return environment.commit(proof)
