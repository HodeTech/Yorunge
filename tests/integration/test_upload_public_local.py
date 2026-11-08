"""Public local upload history is usable without config, secrets, source files or network."""

import asyncio
import json
from dataclasses import replace
from functools import partial
from uuid import uuid4

import pytest

from tests.fixtures.upload_history import install_fixture
from tests.integration.test_upload_journal import journal as journal
from tests.integration.test_upload_journal import seal
from yorunge import api
from yorunge.adapters.state import open_existing_store, open_store
from yorunge.adapters.upload_repository import StateUploads
from yorunge.domain.errors import YorungeError


def test_public_local_history_review_and_revoke_need_no_external_dependencies(journal, monkeypatch):
    record = journal.approved()

    def denied(*args, **kwargs):
        raise AssertionError("local history must not resolve config or secrets")

    monkeypatch.setattr(api, "_configuration", denied)
    monkeypatch.setenv("TEST_PLATFORM_KEY", "DIFFERENT-CREDENTIAL")
    before = api.show_dataset_upload(plan_id=journal.plan.plan_id, state_dir=journal.root)
    value = api.show_dataset_upload(operation_id=record.operation_id, state_dir=journal.root)
    assert value == before
    assert value.operation_id is None
    assert value.data.operation_id == record.operation_id
    assert value.data.approval_status == "approved"
    assert value.data.dataset_id is None
    selected = api.review_dataset_upload(journal.plan.plan_id, state_dir=journal.root).data
    assert selected.parameters == journal.plan.parameters
    assert selected.selected_owner == journal.plan.scope.owner
    assert selected.summary == value.data
    page = api.list_dataset_uploads(state_dir=journal.root)
    assert page.data.uploads == (value.data,)
    assert page.operation_id is None
    changed = api.revoke_dataset_upload(journal.plan.plan_id, state_dir=journal.root).data
    assert changed.approval_status == "revoked"
    assert changed.operation_id == record.operation_id
    assert changed.operation_status == value.data.operation_status
    assert api.revoke_dataset_upload(journal.plan.plan_id, state_dir=journal.root).data == changed
    with open_existing_store(journal.root) as store:
        assert store.verify().store_schema_version == 7


def test_terminal_legacy_receipt_history_is_public_without_rewriting(tmp_path):
    root = tmp_path / "state"
    with open_store(root) as store:
        data = install_fixture(store)
        before = StateUploads(store).show(plan_id=data["plan"]["plan_id"])
    value = api.show_dataset_upload(plan_id=data["plan"]["plan_id"], state_dir=root).data
    assert value.verification_level == "metadata"
    assert not value.authority_verified
    assert value.dataset_id == before.operation.dataset_id
    with open_existing_store(root) as store:
        assert StateUploads(store).show(plan_id=data["plan"]["plan_id"]) == before
        assert store.verify().store_schema_version == 7


def seed(journal, count):
    result = []
    for i in range(count):
        body = journal.plan.model_dump(mode="json")
        body["plan_id"] = str(uuid4())
        body["parameters"]["name"] = f"local-data-{i}"
        candidate = replace(journal, plan=seal(body))
        with open_existing_store(journal.root) as store:
            candidate.repository(store).save(candidate.plan, candidate.manifest)
        result.append(candidate.plan)
    return sorted(result, key=lambda p: (p.prepared_at, p.plan_id))


def test_keyset_limit_byte_boundary_and_exact_filter_skip_no_plan(journal, monkeypatch):
    from yorunge.adapters import upload_public

    plans = seed(journal, 7)
    first = api.list_dataset_uploads(limit=2, state_dir=journal.root).data
    assert [p.plan_id for p in first.uploads] == [p.plan_id for p in plans[:2]]
    # Tighten the same production byte gate to exercise an early boundary.
    content = api.list_dataset_uploads(limit=1, state_dir=journal.root).model_dump(mode="json")
    cap = len(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()) + 5
    monkeypatch.setattr(upload_public, "MAX_PAGE_RESULT_BYTES", cap)
    cursor, found = None, []
    while True:
        page = api.list_dataset_uploads(limit=6, cursor=cursor, state_dir=journal.root).data
        assert len(page.uploads) == 1
        found.extend(x.plan_id for x in page.uploads)
        cursor = page.next_cursor
        if cursor is None:
            break
    assert found == [p.plan_id for p in plans]
    filtered = api.list_dataset_uploads(plan_id=plans[3].plan_id, state_dir=journal.root).data
    assert [p.plan_id for p in filtered.uploads] == [plans[3].plan_id]
    absent = api.list_dataset_uploads(plan_id=str(uuid4()), state_dir=journal.root).data
    assert not absent.uploads
    assert absent.next_cursor is None


@pytest.mark.parametrize(
    "options",
    [
        {"limit": True},
        {"limit": 0},
        {"limit": 101},
        {"limit": 1.0},
        {"cursor": "bad"},
        {"cursor": b"bad"},
        {"plan_id": "bad"},
    ],
)
def test_local_request_rejection_precedes_state_access(tmp_path, options):
    root = tmp_path / "absent"
    invoke = partial(api.list_dataset_uploads, state_dir=root, **options)
    with pytest.raises(YorungeError) as raised:
        invoke()
    assert raised.value.code == "invalid_request"
    assert not root.exists()


@pytest.mark.parametrize(
    "options",
    [
        {},
        {"plan_id": "bad"},
        {"operation_id": "bad"},
        {"plan_id": str(uuid4()), "operation_id": str(uuid4())},
    ],
)
def test_show_exactly_one_valid_identity_before_store(tmp_path, options):
    root = tmp_path / "absent"
    invoke = partial(api.show_dataset_upload, state_dir=root, **options)
    with pytest.raises(YorungeError) as raised:
        invoke()
    assert raised.value.code == "invalid_request"
    assert not root.exists()


def test_missing_store_and_unknown_record_preserve_closed_error(tmp_path):
    root, identity = tmp_path / "state", str(uuid4())
    invoke = partial(api.show_dataset_upload, operation_id=identity, state_dir=root)
    with pytest.raises(YorungeError) as raised:
        invoke()
    assert raised.value.code == "state_invalid"
    assert not root.exists()
    assert raised.value.operation_id == identity
    assert raised.value.__cause__ is raised.value.__context__ is None
    api.initialize_state(state_dir=root)
    with pytest.raises(YorungeError) as raised:
        invoke()
    assert raised.value.code == "operation_not_found"
    assert raised.value.operation_id == identity
    assert raised.value.__cause__ is raised.value.__context__ is None


def test_active_loop_gate_before_state_for_all_local_entrypoints(tmp_path):
    root = tmp_path / "absent"
    identity = str(uuid4())
    calls = (
        partial(api.show_dataset_upload, plan_id=identity, state_dir=root),
        partial(api.review_dataset_upload, identity, state_dir=root),
        partial(api.list_dataset_uploads, state_dir=root),
        partial(api.revoke_dataset_upload, identity, state_dir=root),
    )

    async def run():
        for invoke in calls:
            with pytest.raises(YorungeError) as raised:
                invoke()
            assert raised.value.code == "invalid_request"

    asyncio.run(run())
    assert not root.exists()


@pytest.mark.parametrize("output", ["json", "ndjson"])
def test_real_local_api_results_have_concrete_public_output_types(journal, output):
    import io

    from yorunge.cli.output import OutputRenderer

    record = journal.approved()
    results = (
        api.show_dataset_upload(operation_id=record.operation_id, state_dir=journal.root),
        api.review_dataset_upload(journal.plan.plan_id, state_dir=journal.root),
        api.list_dataset_uploads(state_dir=journal.root),
        api.revoke_dataset_upload(journal.plan.plan_id, state_dir=journal.root),
    )
    for result in results:
        stream = io.StringIO()
        OutputRenderer(output, stdout=stream).result(result)
        assert json.loads(stream.getvalue())["schema_version"] == 1
        for field in ("created_dataset", "credential_id", "identity_epoch", "write_access_digest"):
            assert field not in stream.getvalue()


def test_page_snapshot_prevents_another_writer_from_committing_between_rows(journal, monkeypatch):
    from yorunge.adapters import upload_public

    plans = seed(journal, 2)
    with open_existing_store(journal.root) as store:
        for plan in plans:
            journal.repository(store).approve(plan.plan_id, plan.digest, plan)
    original, invoked = upload_public.summary, []

    def project(view):
        if not invoked:
            invoked.append(True)
            import sqlite3

            # The real store uses DELETE journaling and an owned local lock.
            # A raw independent connection cannot COMMIT through its snapshot.
            with sqlite3.connect(journal.root / "state.sqlite3", timeout=0) as other:
                other.execute("BEGIN IMMEDIATE")
                other.execute("UPDATE upload_approvals SET payload=payload")
                commit = other.commit
                with pytest.raises(sqlite3.OperationalError):
                    commit()
                other.rollback()
        return original(view)

    monkeypatch.setattr(upload_public, "summary", project)
    result = api.list_dataset_uploads(state_dir=journal.root).data
    assert len(result.uploads) == 2
    assert all(p.approval_status == "approved" for p in result.uploads)
    after = api.revoke_dataset_upload(plans[1].plan_id, state_dir=journal.root).data
    assert after.approval_status == "revoked"


def test_real_store_projection_does_not_publish_create_baseline_or_invalid_payload(tmp_path):
    from tests.fixtures.upload_receipts import accepted_create
    from yorunge.adapters.upload_store import read_any_view

    root, sentinel = tmp_path / "state", "00000000-0000-4000-8000-000000000881"
    with open_store(root) as store:
        data = install_fixture(store)
        view = read_any_view(store.connection, data["plan"]["plan_id"])
        receipt = accepted_create(
            view.plan, view.intents[0], view.receipts[0].recorded_at, view.operation.dataset_id
        )
        baseline = receipt.created_dataset.model_copy(update={"org_id": sentinel})
        receipt = receipt.model_copy(update={"created_dataset": baseline})
        store.connection.execute(
            "UPDATE upload_stage_receipts SET payload=? WHERE intent_id=?",
            (receipt.encoded().decode(), receipt.intent_id),
        )
        assert store.verify().store_schema_version == 7
    value = api.show_dataset_upload(plan_id=view.plan.plan_id, state_dir=root)
    content = value.model_dump_json()
    assert sentinel not in content
    assert view.plan.parameters.name not in content
    assert view.plan.scope.owner.id not in content
    requested = api.review_dataset_upload(view.plan.plan_id, state_dir=root)
    assert sentinel not in requested.model_dump_json()
    assert requested.data.parameters.name == view.plan.parameters.name
    bad = baseline.model_copy(update={"name": "PRIVATE-CORRUPTED-BASELINE"})
    corrupt = receipt.model_copy(update={"created_dataset": bad})
    with open_existing_store(root) as store:
        store.connection.execute(
            "UPDATE upload_stage_receipts SET payload=? WHERE intent_id=?",
            (corrupt.encoded().decode(), receipt.intent_id),
        )
    invoke = partial(api.show_dataset_upload, plan_id=view.plan.plan_id, state_dir=root)
    with pytest.raises(YorungeError) as raised:
        invoke()
    assert raised.value.code == "state_invalid"
    assert "PRIVATE-CORRUPTED-BASELINE" not in str(raised.value)
    assert raised.value.__cause__ is raised.value.__context__ is None


@pytest.mark.parametrize("cursor", ["bad", b"bad", "PRIVATE-SENTINEL-秘密"])
def test_invalid_cursor_never_retains_raw_decoder_exception_chain(tmp_path, cursor):
    root = tmp_path / "absent"
    invoke = partial(api.list_dataset_uploads, state_dir=root, cursor=cursor)
    with pytest.raises(YorungeError) as raised:
        invoke()
    assert raised.value.code == "invalid_request"
    assert not root.exists()
    assert raised.value.__cause__ is raised.value.__context__ is None


@pytest.mark.parametrize("policy", ["verified_only", "explicit_attempt"])
def test_authority_summary_is_historical_full_grant_only_after_durable_success(journal, policy):
    from tests.integration.test_upload_recovery_v2 import complete

    body = journal.plan.model_dump(mode="json")
    body["admission_policy"] = policy
    journal.plan = seal(body)
    record, proof = complete(journal, unknown=False)
    before = api.show_dataset_upload(operation_id=record.operation_id, state_dir=journal.root).data
    assert not before.authority_verified
    assert before.verification_level == "none"
    with open_existing_store(journal.root) as store:
        journal.repository(store).verified(record.operation_id, record.lease, proof)
        assert store.verify().store_schema_version == 7
    after = api.show_dataset_upload(operation_id=record.operation_id, state_dir=journal.root).data
    assert after.authority_verified
    assert after.verification_level == "metadata"
    assert not after.remote_bytes_verified
    assert after.cost_bound is not None
    assert "scope" not in type(after.cost_bound).model_fields
