"""The four uses of dataset versions on one shared discovery exchange (ADR-0033).

``list``, ``show``, ``bind`` and ``check`` are read-only: each is one bounded exchange that captures
the local credential snapshot, makes its reads with the key of the snapshot and confirms, once the
reads are over, that the state they stood on did not change (``exchange``). Nothing is written,
approved or recorded as an operation here. The file a ``bind`` publishes and the files it and
``check`` read belong to the caller; this module sees only a binding, a Manifest, and the provider.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeVar

from yorunge.application.context_discovery import (
    DiscoveryClock,
    DiscoveryReader,
    DiscoverySnapshot,
    DiscoveryState,
    exchange,
)
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_version import (
    Absent,
    DatasetVersionBinding,
    DatasetVersionCheck,
    DatasetVersionList,
    DatasetVersionObservation,
    bind,
    require_same_service,
)

T = TypeVar("T")


class VersionPort(Protocol):
    """What a use of versions asks of the provider: one page, or one version (two reads)."""

    def versions(self, dataset_id: str, page: int, *, deadline: float) -> DatasetVersionList: ...

    def version(
        self, dataset_id: str, version_tag: str, *, deadline: float, absent: Absent
    ) -> DatasetVersionObservation: ...


Operation = Callable[[VersionPort, DiscoverySnapshot, float], T]


class Observers(Protocol):
    """Builds the exchange's reader for an operation: it owns the session and the credential."""

    def __call__(self, operation: Operation[T]) -> DiscoveryReader[T]: ...


def _observe(
    state: DiscoveryState,
    observers: Observers,
    clock: DiscoveryClock,
    operation: Operation[T],
    deadline: float,
) -> T:
    _, reply, _, _, _ = exchange(state, observers(operation), clock, deadline=deadline)
    return reply


def list_versions(
    state: DiscoveryState,
    observers: Observers,
    clock: DiscoveryClock,
    *,
    dataset_id: str,
    page: int,
    deadline: float,
) -> DatasetVersionList:
    """One page of the dataset's versions (one read; completeness is never claimed)."""

    def operation(
        reader: VersionPort, snapshot: DiscoverySnapshot, until: float
    ) -> DatasetVersionList:
        return reader.versions(dataset_id, page, deadline=until)

    return _observe(state, observers, clock, operation, deadline)


def show_version(
    state: DiscoveryState,
    observers: Observers,
    clock: DiscoveryClock,
    *,
    dataset_id: str,
    version_tag: str,
    deadline: float,
) -> DatasetVersionObservation:
    """One version, observed from its detail and its split counts, which must agree."""

    def operation(
        reader: VersionPort, snapshot: DiscoverySnapshot, until: float
    ) -> DatasetVersionObservation:
        return reader.version(
            dataset_id, version_tag, deadline=until, absent="dataset_version_not_found"
        )

    return _observe(state, observers, clock, operation, deadline)


def bind_version(
    state: DiscoveryState,
    observers: Observers,
    clock: DiscoveryClock,
    *,
    dataset_id: str,
    version_tag: str,
    manifest: DatasetManifest | None,
    deadline: float,
) -> DatasetVersionBinding:
    """The binding of a frozen version to the provider the credential targets, and optionally to
    a local Manifest v1 (its digest and its file count). Nothing is written."""

    def operation(
        reader: VersionPort, snapshot: DiscoverySnapshot, until: float
    ) -> tuple[DatasetVersionObservation, DiscoverySnapshot]:
        found = reader.version(
            dataset_id, version_tag, deadline=until, absent="dataset_version_not_found"
        )
        return found, snapshot

    observation, snapshot = _observe(state, observers, clock, operation, deadline)
    return bind(
        observation,
        snapshot.credential.target,
        manifest_digest=None if manifest is None else manifest.digest,
        manifest_file_count=None if manifest is None else manifest.file_count,
    )


def check_binding(
    state: DiscoveryState,
    observers: Observers,
    clock: DiscoveryClock,
    *,
    binding: DatasetVersionBinding,
    deadline: float,
) -> DatasetVersionCheck:
    """``unchanged`` if the provider still shows what the binding holds, else the error.

    The binding's provider is compared with the credential's before the first request: a binding
    for another provider is ``state_changed`` and nothing is read.
    """

    def operation(
        reader: VersionPort, snapshot: DiscoverySnapshot, until: float
    ) -> tuple[DatasetVersionObservation, DiscoverySnapshot]:
        require_same_service(binding, snapshot.credential.target)
        found = reader.version(
            binding.dataset_id,
            binding.version_tag,
            deadline=until,
            absent="dataset_version_missing",
        )
        return found, snapshot

    observation, snapshot = _observe(state, observers, clock, operation, deadline)
    return binding.check(observation, active=snapshot.credential.target)
