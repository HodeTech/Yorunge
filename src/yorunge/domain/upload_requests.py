"""Secret-free semantic request bytes shared by the journal and real HTTP port."""

import hashlib

from yorunge.domain.capabilities import canonical
from yorunge.domain.dataset_manifest import DatasetFile
from yorunge.domain.dataset_transfer import StageKind


def upload_request_digest(
    plan_digest: str,
    kind: StageKind,
    file_index: int | None,
    file: DatasetFile | None,
    dataset_id: str | None,
    local_binding: str | None,
) -> str:
    """The historical object_key wire key holds a safe local file binding in v2."""
    return hashlib.sha256(
        canonical(
            {
                "plan_digest": plan_digest,
                "kind": kind,
                "file_index": file_index,
                "file": file.model_dump(mode="json") if file is not None else None,
                "dataset_id": dataset_id,
                "object_key": local_binding,
            }
        )
    ).hexdigest()
