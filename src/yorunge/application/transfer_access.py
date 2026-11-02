"""Volatile admission capability; durable ownership identifiers cannot recreate it."""

import hashlib
import hmac
import os
import secrets
from typing import NoReturn

from yorunge.domain.dataset_transfer import TransferRecord
from yorunge.domain.errors import YorungeError


class TransferWriteAccess:
    __slots__ = ("_operation_id", "_owner_id", "_nonce", "_issuer", "_end")
    _operation_id: str
    _owner_id: str
    _nonce: bytes
    _issuer: int
    _end: float

    def __init__(self, operation_id: str, owner_id: str, end: float) -> None:
        object.__setattr__(self, "_operation_id", operation_id)
        object.__setattr__(self, "_owner_id", owner_id)
        object.__setattr__(self, "_nonce", secrets.token_bytes(32))
        object.__setattr__(self, "_issuer", os.getpid())
        object.__setattr__(self, "_end", end)

    def __setattr__(self, name: str, value: object) -> NoReturn:
        raise AttributeError("transfer write access is immutable")

    @property
    def digest(self) -> str:
        return hashlib.sha256(
            b"yorunge:upload-write-access:v1\0"
            + self._operation_id.encode("ascii")
            + self._owner_id.encode("ascii")
            + self._nonce
        ).hexdigest()

    @property
    def end(self) -> float:
        return self._end

    def require(self, record: TransferRecord, now: float) -> None:
        if (
            os.getpid() != self._issuer
            or self._operation_id != record.operation_id
            or self._owner_id != record.write_owner_id
            or not hmac.compare_digest(self.digest, record.write_access_digest)
            or not now < self._end
        ):
            raise YorungeError("operation_lease_lost")

    def __repr__(self) -> str:
        return "<TransferWriteAccess redacted>"

    def __copy__(self) -> NoReturn:
        raise TypeError("transfer write access cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        raise TypeError("transfer write access cannot be copied")

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("transfer write access cannot be serialized")
