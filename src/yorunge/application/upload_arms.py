"""One immutable repository-issued arm; generic execution permits remain unchanged."""

from __future__ import annotations

import math
import os
import threading
from _thread import LockType
from collections.abc import Callable, Iterator
from threading import Lock
from typing import NoReturn

from yorunge.application.operations import DispatchPermit
from yorunge.application.upload_inputs import revalidate_input
from yorunge.domain.dataset_transfer import StageIntent
from yorunge.domain.errors import OperationError, YorungeError

_ISSUANCE = object()
ArmPart = StageIntent | DispatchPermit | float


class UploadArm:
    """Private composition capability, not a portable proof of a SQLite commit."""

    __slots__ = (
        "_snapshot",
        "_permit",
        "_deadline",
        "_clock",
        "_pid",
        "_thread",
        "_used",
        "_lock",
        "_operation_id",
    )
    _snapshot: bytes
    _permit: DispatchPermit
    _deadline: float
    _clock: Callable[[], float]
    _pid: int
    _thread: threading.Thread
    _used: bool
    _lock: LockType
    _operation_id: str

    def __init__(
        self, token: object, intent: StageIntent, deadline: float, clock: Callable[[], float]
    ) -> None:
        if token is not _ISSUANCE:
            raise YorungeError("invalid_request")
        intent = revalidate_input(StageIntent, intent)
        finite = type(deadline) in (int, float)
        try:
            finite = finite and math.isfinite(deadline)
        except OverflowError:
            finite = False
        if not finite:
            raise YorungeError("invalid_request")
        if clock() >= deadline:
            raise OperationError("execution_timeout", intent.operation_id)
        for key, value in (
            ("_snapshot", intent.encoded()),
            ("_permit", DispatchPermit(os.getpid)),
            ("_deadline", float(deadline)),
            ("_clock", clock),
            ("_pid", os.getpid()),
            ("_thread", threading.current_thread()),
            ("_used", False),
            ("_lock", Lock()),
            ("_operation_id", intent.operation_id),
        ):
            object.__setattr__(self, key, value)

    def __setattr__(self, name: str, value: object) -> NoReturn:
        raise AttributeError("upload arm is immutable")

    @property
    def intent(self) -> StageIntent:
        # Return a fresh decoded snapshot; a caller's model_copy or __dict__
        # mutation cannot rewrite the repository's captured intent.
        return StageIntent.model_validate_json(self._snapshot)

    @property
    def deadline(self) -> float:
        return self._deadline

    def claim(self) -> tuple[StageIntent, DispatchPermit, float]:
        if os.getpid() != self._pid or threading.current_thread() is not self._thread:
            raise OperationError("operation_conflict", self._operation_id)
        with self._lock:
            if self._used:
                raise OperationError("operation_conflict", self._operation_id)
            if self._clock() >= self._deadline:
                raise OperationError("execution_timeout", self._operation_id)
            object.__setattr__(self, "_used", True)
            return self.intent, self._permit, self._deadline

    def __iter__(self) -> Iterator[ArmPart]:
        """Historical private tuple access; new port accepts only the whole arm."""
        return iter((self.intent, self._permit, self._deadline))

    def __len__(self) -> int:
        return 3

    def __getitem__(self, index: int | slice) -> ArmPart | tuple[ArmPart, ...]:
        return (self.intent, self._permit, self._deadline)[index]

    def __repr__(self) -> str:
        return "<UploadArm redacted>"

    def __copy__(self) -> NoReturn:
        raise TypeError("upload arm cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        raise TypeError("upload arm cannot be copied")

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("upload arm cannot be serialized")


def _issue_upload_arm(
    intent: StageIntent, deadline: float, clock: Callable[[], float]
) -> UploadArm:
    """Only the trusted repository calls this after COMMIT and its final gate."""
    return UploadArm(_ISSUANCE, intent, deadline, clock)
