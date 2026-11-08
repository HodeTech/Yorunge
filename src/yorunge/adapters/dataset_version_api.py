"""The composition of the four version uses: arguments, local files, the exchange, the result.

Everything the public API and the CLI share: the arguments are judged before any state or secret
is touched, the local files (a Manifest v1 for ``bind``, a binding for ``check``) are read first
and the target of ``bind`` is claimed before the provider is asked, the reads are one bounded
exchange on the captured credential snapshot, and the only write is the binding's no-clobber
publication.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from yorunge.adapters.binding_files import binding_target
from yorunge.adapters.capability_cache import SystemClock
from yorunge.adapters.context_state import StateDiscovery
from yorunge.adapters.dataset_version_exchange import VersionObserver
from yorunge.adapters.dataset_version_reader import VERSION_SECONDS
from yorunge.adapters.local_files import require_local_files
from yorunge.adapters.secrets import EnvSecretReader
from yorunge.adapters.small_files import read_regular_file
from yorunge.adapters.upload_sync import require_upload_sync_context
from yorunge.application.context_discovery import ObservationClock
from yorunge.application.dataset_versions import (
    Observers,
    Operation,
    bind_version,
    check_binding,
    list_versions,
    show_version,
)
from yorunge.application.datasets import DatasetBudget, decode_manifest
from yorunge.domain.dataset_manifest import MAX_MANIFEST_BYTES, DatasetManifest
from yorunge.domain.dataset_upload import provider_uuid
from yorunge.domain.dataset_version import (
    MAX_BINDING_BYTES,
    MAX_PAGE,
    MIN_PAGE,
    DatasetVersionBound,
    DatasetVersionCheck,
    DatasetVersionList,
    DatasetVersionObservation,
    bound_summary,
    decode_binding,
    validate_version_tag,
)
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Context, Profile, Result, ServiceId

T = TypeVar("T")
ContextLoader = Callable[[], tuple[Context, Profile]]
PLATFORM: ServiceId = "evren-platform"
METADATA_ONLY = ("provider_metadata_only",)  # what every success says: provider metadata, no bytes


def _identifier(dataset_id: object) -> str:
    if type(dataset_id) is not str:
        raise YorungeError("invalid_request")
    try:
        return provider_uuid(dataset_id)
    except ValueError:
        raise YorungeError("invalid_request") from None


def _tag(version_tag: object) -> str:
    try:
        return validate_version_tag(version_tag)
    except ValueError:
        raise YorungeError("invalid_request") from None


def _page(page: object) -> int:
    if type(page) is not int or not MIN_PAGE <= page <= MAX_PAGE:
        raise YorungeError("invalid_request")
    return page


def _absolute(path: object) -> Path:
    """The path as one observation of the working directory makes it absolute (no symlink walk)."""
    if not isinstance(path, Path) or not path.name:
        raise YorungeError("invalid_request")
    if path.is_absolute():
        return path
    try:
        return Path.cwd() / path
    except OSError:
        raise YorungeError("input_invalid") from None


def _local(state_dir: object) -> None:
    """Where the caller stands (a state directory that is a path, a thread that may block):
    judged with the other arguments, before any file or secret is touched."""
    if state_dir is not None and not isinstance(state_dir, Path):
        raise YorungeError("invalid_request")
    require_upload_sync_context()  # a running event loop is refused whatever the target says
    require_local_files()


class _Composition:
    """The state, the clock and the observers of one use; built after the arguments are judged."""

    def __init__(self, loader: ContextLoader, state_dir: Path | None) -> None:
        _local(state_dir)
        self.started = time.monotonic()
        self.clock = ObservationClock(SystemClock())
        self.state = StateDiscovery(
            state_dir, loader, EnvSecretReader(), self.clock, service_id=PLATFORM
        )
        self.deadline = self.started + VERSION_SECONDS

    def observers(self) -> Observers:
        clock = self.clock

        class Factory:
            def __call__(self, operation: Operation[T]) -> VersionObserver[T]:
                return VersionObserver(clock, operation)

        return Factory()


def list_dataset_versions(
    dataset_id: str, page: int, loader: ContextLoader, state_dir: Path | None
) -> Result[DatasetVersionList]:
    identifier, number = _identifier(dataset_id), _page(page)
    _local(state_dir)
    use = _Composition(loader, state_dir)
    listed = list_versions(
        use.state,
        use.observers(),
        use.clock,
        dataset_id=identifier,
        page=number,
        deadline=use.deadline,
    )
    return Result[DatasetVersionList](data=listed, warnings=METADATA_ONLY)


def show_dataset_version(
    dataset_id: str, version_tag: str, loader: ContextLoader, state_dir: Path | None
) -> Result[DatasetVersionObservation]:
    identifier, tag = _identifier(dataset_id), _tag(version_tag)
    _local(state_dir)
    use = _Composition(loader, state_dir)
    shown = show_version(
        use.state,
        use.observers(),
        use.clock,
        dataset_id=identifier,
        version_tag=tag,
        deadline=use.deadline,
    )
    return Result[DatasetVersionObservation](data=shown, warnings=METADATA_ONLY)


def _read_manifest(path: Path) -> DatasetManifest:
    content = read_regular_file(path, limit=MAX_MANIFEST_BYTES, oversize="manifest_invalid")
    return decode_manifest(content, DatasetBudget())


def bind_dataset_version(
    dataset_id: str,
    version_tag: str,
    binding_out: Path,
    manifest: Path | None,
    loader: ContextLoader,
    state_dir: Path | None,
) -> Result[DatasetVersionBound]:
    identifier, tag = _identifier(dataset_id), _tag(version_tag)
    _local(state_dir)
    target = _absolute(binding_out)
    chosen = None if manifest is None else _absolute(manifest)
    if chosen is not None and chosen == target:
        raise YorungeError("invalid_request")
    local = None if chosen is None else _read_manifest(chosen)
    use = _Composition(loader, state_dir)
    with binding_target(target) as destination:
        destination.require_absent()
        binding = None
        try:
            binding = bind_version(
                use.state,
                use.observers(),
                use.clock,
                dataset_id=identifier,
                version_tag=tag,
                manifest=local,
                deadline=use.deadline,
            )
        except (OSError, UnicodeError):
            pass  # the read phase's own failure (config, state, secret), not the write's
        if binding is None:
            raise YorungeError("file_unreadable")
        # Everything the command will say is made before the link, the one step that cannot be
        # taken back: nothing that can still be refused is left for after it.
        report = bound_summary(binding, str(target))
        warnings = (
            METADATA_ONLY
            if binding.split_total_matches_item_count
            else (*METADATA_ONLY, "split_total_differs")
        )
        destination.publish(binding)
    return Result[DatasetVersionBound](data=report, warnings=warnings)


def check_dataset_version(
    binding: Path, loader: ContextLoader, state_dir: Path | None
) -> Result[DatasetVersionCheck]:
    _local(state_dir)
    source = _absolute(binding)
    held = decode_binding(
        read_regular_file(source, limit=MAX_BINDING_BYTES, oversize="binding_invalid")
    )
    use = _Composition(loader, state_dir)
    checked = check_binding(
        use.state, use.observers(), use.clock, binding=held, deadline=use.deadline
    )
    return Result[DatasetVersionCheck](data=checked, warnings=METADATA_ONLY)
