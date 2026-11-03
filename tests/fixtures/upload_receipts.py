"""Synthetic strict create responses for repository tests; never a product producer."""

from yorunge.domain.create_receipt import CreateReceiptV2
from yorunge.domain.platform_upload import ProviderDataset

OTHER_USER = "00000000-0000-4000-8000-000000000777"


def accepted_create(plan, intent, recorded_at, dataset_id):
    owner = plan.scope.owner
    return CreateReceiptV2(
        schema_version=2,
        intent_id=intent.intent_id,
        recorded_at=recorded_at,
        result="accepted",
        dataset_id=dataset_id,
        object_key=None,
        sent_bytes=None,
        sent_sha256=None,
        created_dataset=ProviderDataset(
            id=dataset_id,
            name=plan.parameters.name,
            modality=plan.parameters.modality,
            visibility="private",
            contributions_enabled=False,
            owner_id=owner.id if owner.kind == "user" else OTHER_USER,
            org_id=owner.id if owner.kind == "organization" else None,
        ),
    )
