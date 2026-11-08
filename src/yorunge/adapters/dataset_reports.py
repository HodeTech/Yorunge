"""Private staged manifest publication with an exclusive hardlink, never overwrite.

The publication itself is the common artifact publisher's; this module is the manifest's side of
it: its error family, its stage name prefix and the file sync (``full_sync``, which its tests
replace). The steps the tests inject faults into are the publisher's overridable methods.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from yorunge.adapters import artifact_publisher
from yorunge.adapters.artifact_publisher import ArtifactCodes, ArtifactPublisher
from yorunge.adapters.dataset_files import DatasetLocation
from yorunge.adapters.local_files import full_sync
from yorunge.domain.dataset_manifest import DatasetManifest

MANIFEST_CODES = ArtifactCodes(
    failed="manifest_write_failed",
    exists="manifest_output_exists",
    uncertain="manifest_write_uncertain",
    changed="input_changed",
    unreadable="file_unreadable",
)


@dataclass
class PublicationState(artifact_publisher.PublicationState):
    # Keyword-only, so that the positional order stays the base's (``PublicationState(True)``
    # still means that the link was attempted).
    codes: ArtifactCodes = field(default=MANIFEST_CODES, kw_only=True)


class DatasetManifestWriter(ArtifactPublisher):
    def __init__(
        self,
        location: DatasetLocation,
        state: PublicationState,
        check_source: Callable[[], None],
    ) -> None:
        super().__init__(location, state, check_source, prefix=".yorunge-manifest-")

    def publish(self, manifest: DatasetManifest) -> None:
        self.publish_bytes(manifest.encoded())

    def _sync(self, descriptor: int) -> None:
        full_sync(descriptor)
