"""Private staged manifest publication with an exclusive hardlink, never overwrite.

The publication itself is the common artifact publisher's; this module is the manifest's side of
it: its error family, its stage name and the seams its tests inject faults into
(``_check_stage``, ``_publish_link``, ``_check_target`` and this module's ``full_sync``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

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
    codes: ArtifactCodes = MANIFEST_CODES


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
