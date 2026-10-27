"""Public maintenance effects; comparison tags and file hashes are never included."""

from typing import Literal

from yorunge.domain.models import Model


class IdentitySnapshot(Model):
    store_id: str
    identity_epoch: str
    store_schema_version: int
    binding_count: int
    binding_fingerprint: str


class MaintenancePreview(Model):
    action: Literal["reset", "restore", "recover"]
    current: IdentitySnapshot | None
    source: IdentitySnapshot | None
    history_may_be_lost: bool
    announced_epoch: str | None = None
    digest: str
