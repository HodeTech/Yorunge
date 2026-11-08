"""The version reader as the reader of a shared discovery exchange (ADR-0033).

The exchange captures the local credential snapshot inside the reader's own block; the reader that
reads versions needs that credential, so it is built from the snapshot, on the session this observer
owns (entered with the exchange, closed before the exchange confirms its state).
"""

from __future__ import annotations

from types import TracebackType
from typing import Generic, Self, TypeVar

from yorunge.adapters.dataset_version_reader import VersionReader
from yorunge.adapters.http_session import HttpSession
from yorunge.application.context_discovery import DiscoveryClock, DiscoverySnapshot
from yorunge.application.dataset_versions import Operation

ReplyT = TypeVar("ReplyT")


class VersionObserver(Generic[ReplyT]):
    def __init__(self, clock: DiscoveryClock, operation: Operation[ReplyT]) -> None:
        self.clock, self.operation = clock, operation
        self.session = HttpSession()

    def __enter__(self) -> Self:
        self.session.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.session.__exit__(exc_type, exc, traceback)

    def observe(self, snapshot: DiscoverySnapshot, *, deadline: float) -> ReplyT:
        reader = VersionReader(snapshot.credential, self.clock, session=self.session)
        return self.operation(reader, snapshot, deadline)
