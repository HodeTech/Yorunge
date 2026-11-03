"""Closed projections and literal wire; selected intent is not a provider receipt."""

import io
import json
from dataclasses import replace
from functools import partial
from pathlib import Path

import pytest

from tests.contracts.test_upload_versions import graph
from tests.fixtures.upload_receipts import accepted_create
from yorunge.adapters.upload_projection import review, summary
from yorunge.adapters.upload_store import VersionedTransferView
from yorunge.cli.output import OutputRenderer
from yorunge.domain.dataset_upload import DatasetUploadApproval, DatasetUploadPlan
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.models import Result
from yorunge.domain.upload_public import DatasetUploadSummary, UploadIntentReview

FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_literal_public_summary_preserves_result_v1_and_metadata_level():
    value = summary(graph())
    expected = (FIXTURES / "dataset-upload-summary-v2.json").read_bytes()
    assert value.encoded() == expected
    assert DatasetUploadSummary.model_validate_json(expected) == value
    assert value.verification_level == "metadata"
    assert not value.authority_verified
    assert not value.remote_bytes_verified
    assert Result[DatasetUploadSummary](data=value).operation_id is None
    assert value.dataset_id == graph().operation.dataset_id


def test_nonnull_cost_summary_and_requested_review_never_include_private_scope():
    data = json.loads((FIXTURES / "dataset-upload-approved-v2.json").read_bytes())
    plan = DatasetUploadPlanV2.model_validate_json(json.dumps(data["plan"]))
    view = VersionedTransferView(plan, None, None)
    for projection in (summary(view), review(view)):
        content = projection.encoded().decode()
        for key in ("credential_id", "credential_revision", "identity_epoch", "clock_generation"):
            assert key not in content
        for value in (plan.scope.credential_id, plan.scope.identity_epoch, plan.scope.store_id):
            assert value not in content
        cost = (
            projection.summary.cost_bound
            if isinstance(projection, UploadIntentReview)
            else (projection.cost_bound)
        )
        assert cost.maximum_micros == plan.cost_bound.maximum_micros
        assert cost.work_digest == plan.cost_bound.work_digest
        assert cost.post_period_storage == plan.cost_bound.post_period_storage
    requested = review(view)
    assert requested.parameters == plan.parameters
    assert requested.selected_owner == plan.scope.owner
    assert requested.root == plan.root.anchor
    assert requested.manifest == plan.manifest
    assert requested.target.profile == plan.scope.profile


@pytest.mark.parametrize("output", ["text", "json", "ndjson"])
def test_provider_receipt_sentinels_are_absent_from_public_summary(output):
    view = graph()
    baseline = accepted_create(
        view.plan, view.intents[0], view.receipts[0].recorded_at, view.operation.dataset_id
    )
    reported = baseline.created_dataset.model_copy(
        update={
            "name": "PRIVATE-REPORTED-NAME",
            "owner_id": "00000000-0000-4000-8000-000000000880",
            "org_id": "00000000-0000-4000-8000-000000000881",
        }
    )
    # Projection must not consult this value at all; graph validation is a
    # separate repository gate, not a reason to serialize a rejected baseline.
    private = baseline.model_copy(update={"created_dataset": reported})
    value = summary(replace(view, receipts=(private, *view.receipts[1:])))
    stdout, stderr = io.StringIO(), io.StringIO()
    renderer = OutputRenderer(output, stdout=stdout, stderr=stderr, operation_id=value.operation_id)
    renderer.result(Result[DatasetUploadSummary](data=value), text="metadata verified")
    content = stdout.getvalue() + stderr.getvalue()
    for sentinel in (reported.name, reported.owner_id, reported.org_id):
        assert sentinel not in content
    assert "created_dataset" not in content
    assert "receipts" not in content
    if output == "ndjson":
        event = json.loads(stdout.getvalue())
        assert event["operation_id"] == value.operation_id
        assert event["payload"]["operation_id"] is None


def test_legacy_plan_review_does_not_upgrade_scope_only_price():
    data = json.loads((FIXTURES / "dataset-upload-approved-v1.json").read_bytes())
    plan = DatasetUploadPlan.model_validate_json(json.dumps(data["plan"]))
    approval = DatasetUploadApproval.model_validate_json(json.dumps(data["approval"]))
    value = review(VersionedTransferView(plan, approval, None))
    assert value.summary.source_plan_schema == 1
    assert value.summary.legacy_history_only
    assert value.summary.cost_bound is None
    assert value.summary.cost_scope == "legacy_unknown"
    assert value.summary.plan_status == "prepared"
    assert value.request_limits is None
    assert value.summary.approval_status == "approved"
    assert not value.summary.authority_verified


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("source_plan_schema", True),
        ("source_plan_schema", 1),
        ("remote_bytes_verified", 0),
        ("remote_bytes_verified", True),
        ("authority_verified", 1),
        ("legacy_history_only", 0),
        ("operation_id", None),
        ("approval_expires_at", None),
        ("verification_level", "none"),
        ("operation_status", "running"),
        ("extra", "PRIVATE"),
    ],
)
def test_summary_rejects_wrong_types_family_pairs_and_false_success(field, value):
    body = summary(graph()).model_dump(mode="json")
    body[field] = value
    decode = partial(DatasetUploadSummary.model_validate_json, json.dumps(body))
    with pytest.raises(ValueError):
        decode()


def test_public_review_and_max_page_fit_existing_ndjson_depth_and_byte_limits():
    from yorunge.domain.upload_public import DatasetUploadsPage

    view = graph()
    value = review(view)
    for data in (
        value,
        DatasetUploadsPage(schema_version=1, uploads=(summary(view),) * 100, next_cursor=None),
    ):
        stdout = io.StringIO()
        renderer = OutputRenderer("ndjson", stdout=stdout)
        renderer.result(Result.__class_getitem__(type(data))(data=data))
        assert len(stdout.getvalue().encode()) < 512 * 1024
        assert json.loads(stdout.getvalue())["event"] == "result"


def test_nonnull_cost_review_and_hundred_maximum_price_summaries_fit_ndjson():
    from tests.integration.test_upload_journal import seal
    from yorunge.domain.upload_public import DatasetUploadsPage

    body = json.loads((FIXTURES / "dataset-upload-approved-v2.json").read_bytes())["plan"]
    body["budget_micros"] = body["cost_bound"]["maximum_micros"] = 2**63 - 1
    body["cost_bound"]["source_id"] = "s" * 128
    body["cost_bound"]["source_version"] = "v" * 128
    plan = seal(body)
    view = VersionedTransferView(plan, None, None)
    for data in (
        review(view),
        DatasetUploadsPage(schema_version=1, uploads=(summary(view),) * 100, next_cursor=None),
    ):
        stream = io.StringIO()
        result = Result.__class_getitem__(type(data))(data=data)
        OutputRenderer("ndjson", stdout=stream).result(result)
        assert len(stream.getvalue().encode()) < 512 * 1024
        assert "credential_id" not in stream.getvalue()
        assert "identity_epoch" not in stream.getvalue()
        assert json.loads(stream.getvalue())["event"] == "result"
