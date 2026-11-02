"""Real SQLite transfer isolation, durable authorization and crash/recovery boundaries."""

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import timedelta
from functools import partial
from pathlib import Path
from uuid import uuid4

import pytest

from yorunge import api
from yorunge.adapters.capability_cache import StateCache
from yorunge.adapters.identity import StateCredentialRegistry
from yorunge.adapters.state import open_store
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import capacity, read_manifest
from yorunge.adapters.upload_store import read_any_view as read_view
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.credentials import (
    BoundCredential,
    EnvReference,
    ResolvedCredential,
    SecretValue,
    normalize_target,
)
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_transfer import StageReceipt, VerifiedFile
from yorunge.domain.dataset_transfer_v2 import TransferVerificationV2 as TransferVerification
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2 as DatasetUploadPlan
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Context
from yorunge.domain.upload_checks import AuthorizationCheck, UploadCurrentCheck, UploadObservation
from yorunge.domain.upload_costs import UploadCostWork

FIXTURES = Path(__file__).parents[1] / "fixtures"
DATASET = "00000000-0000-4000-8000-000000000099"


def seal(body):
    body = {k: v for k, v in body.items() if k != "digest"}
    count, total = body["manifest"]["file_count"], body["manifest"]["total_bytes"]
    body["request_limits"] = {
        **body["request_limits"],
        "max_presign": count,
        "max_put": count,
        "max_confirm": count,
        "max_upload_bytes": total,
    }
    body["execution_window"] = {"not_before": body["prepared_at"], "not_after": body["expires_at"]}
    work = UploadCostWork.model_validate_json(
        json.dumps(
            {
                k: body[k]
                for k in (
                    "scope",
                    "root",
                    "manifest",
                    "parameters",
                    "storage",
                    "request_limits",
                    "execution_window",
                )
            }
        )
    )
    body["cost_bound"] = {
        **body["cost_bound"],
        "work_digest": work.digest(),
        "charge_period_start": body["prepared_at"],
        "charge_period_end": body["expires_at"],
    }
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return DatasetUploadPlan.model_validate_json(
        json.dumps({**body, "digest": hashlib.sha256(encoded).hexdigest()})
    )


class FixtureUploads(StateUploads):
    """Synthetic proof capture for real repository tests; never a product producer."""

    def capture(self, fresh, kind="create", dataset_id=None):
        if not isinstance(fresh, DatasetUploadPlan):
            return fresh
        action = "upload_created_dataset"
        if kind == "create":
            action = "create_private_dataset"
        elif kind == "project_link":
            action = "link_project"
        now = timestamp(self.clock.value)
        allowed = fresh.grant is not None and action in fresh.grant.permissions
        auth = AuthorizationCheck(
            consumer_profile="evren-platform-observed-upload-v2",
            policy_version=2,
            action=action,
            scope=fresh.scope,
            dataset_id=dataset_id,
            producer_id="fixture_only",
            producer_version="2",
            checked_at=now,
            outcome="allowed" if allowed else "not_exposed",
            grant=fresh.grant if allowed else None,
            error_code=None,
        )
        observation = None
        if action == "upload_created_dataset" and dataset_id is not None:
            observation = UploadObservation(
                consumer_profile="evren-platform-observed-upload-v2",
                policy_version=2,
                scope=fresh.scope,
                dataset_id=dataset_id,
                checked_at=now,
                has_upload=True,
            )
        return UploadCurrentCheck(
            saved_plan_id=fresh.plan_id,
            saved_plan_digest=fresh.digest,
            saved_binding_digest=fresh.binding_digest(),
            work_digest=fresh.cost_work().digest(),
            scope=fresh.scope,
            checked_at=now,
            baseline_grant=fresh.grant,
            baseline_cost_bound=fresh.cost_bound,
            supplemental_grant=None,
            supplemental_cost_bound=None,
            authorization=auth,
            inputs_verified=fresh.inputs_verified,
            upload_observation=observation,
        )

    def approve(self, plan_id, digest, fresh, **kwargs):
        return super().approve(plan_id, digest, self.capture(fresh), **kwargs)

    def admit(self, plan_id, fresh):
        # Existing local lookup needs no new proof construction.
        if self.show(plan_id=plan_id).operation is not None:
            return super().admit(plan_id, fresh)
        return super().admit(plan_id, self.capture(fresh))

    def arm(self, operation_id, owner, fresh, kind, file_index, **kwargs):
        record = self.show(operation_id=operation_id).operation
        return super().arm(
            operation_id,
            owner,
            self.capture(fresh, kind, record.dataset_id),
            kind,
            file_index,
            **kwargs,
        )


@dataclass
class Journal:
    root: Path
    bound: BoundCredential
    plan: DatasetUploadPlan
    manifest: DatasetManifest
    clock: object
    access: object = None

    def repository(self, store):
        return FixtureUploads(store, self.bound, clock=self.clock, write_access=self.access)

    def approved(self):
        with open_store(self.root) as store:
            repository = self.repository(store)
            repository.save(self.plan, self.manifest)
            repository.approve(self.plan.plan_id, self.plan.digest, self.plan)
            record = repository.admit(self.plan.plan_id, self.plan)
            self.access = repository.write_access
            return record

    def arm(self, record, kind="create", index=None):
        with open_store(self.root) as store:
            return self.repository(store).arm(
                record.operation_id,
                record.lease,
                self.plan,
                kind,
                index,
                total_end=self.clock.monotonic() + 900,
            )

    def accept(self, record, intent, *, rejected=False):
        file = self.manifest.files[intent.file_index] if intent.file_index is not None else None
        receipt = StageReceipt(
            schema_version=1,
            intent_id=intent.intent_id,
            recorded_at=timestamp(self.clock.value),
            result="rejected" if rejected else "accepted",
            dataset_id=None if rejected else DATASET,
            object_key=None
            if rejected or intent.kind in {"create", "project_link"}
            else f"objects/{intent.file_index}",
            sent_bytes=file.size if not rejected and intent.kind == "put" else None,
            sent_sha256=file.sha256 if not rejected and intent.kind == "put" else None,
        )
        with open_store(self.root) as store:
            return self.repository(store).receipt(record.operation_id, record.lease, receipt)


@pytest.fixture
def journal(tmp_path, execution_clock):
    clock = execution_clock
    clock.value = instant("2026-11-02T11:00:01.000000Z")
    root = tmp_path / "state"
    context = Context(
        profile="test",
        project_id=None,
        account_id=None,
        platform_url="https://api.ssyz.org.tr/api/v1",
        llm_url="https://api-llm.ssyz.org.tr/v1",
    )
    credential = ResolvedCredential(
        EnvReference(service_id="evren-platform", name="TEST_PLATFORM_KEY"),
        normalize_target(context.platform_url),
        SecretValue("synthetic-JOURNAL-key-DO-NOT-PUBLISH"),
    )
    with open_store(root) as store:
        identity = StateCredentialRegistry(store).observe(credential)
        stamp = StateCache(store, clock).stamp()
    bound = BoundCredential(context, credential, identity)
    body = json.loads((FIXTURES / "dataset-upload-approved-v2.json").read_bytes())["plan"]
    body["scope"].update(
        store_id=stamp.store_id,
        identity_epoch=stamp.identity_epoch,
        clock_generation=stamp.generation,
        credential_id=identity.credential_id,
        credential_revision=identity.credential_revision,
    )
    for field in ("grant", "cost_bound"):
        body[field]["scope"] = dict(body["scope"])
    plan = seal(body)
    manifest = DatasetManifest.model_validate_json(
        (FIXTURES / "dataset-manifest-v1.json").read_bytes()
    )
    return Journal(root, bound, plan, manifest, clock)


def test_exact_plan_lookup_and_idempotent_admission_after_lost_output(journal):
    record = journal.approved()
    with open_store(journal.root) as store:
        repo = StateUploads(store, clock=journal.clock)
        found = repo.show(plan_id=journal.plan.plan_id)
        assert found.operation == record
        assert repo.show(operation_id=record.operation_id) == found
        # No credential, approval, hash or effect is required to find the ID.
        assert repo.admit(journal.plan.plan_id, journal.plan) == record
        rows, cursor = repo.list()
        assert len(rows) == 1 and rows[0].operation_id == record.operation_id and cursor is None
        assert store.verify().store_schema_version == 7


def test_full_workflow_has_one_permit_per_stage_and_separate_read_verification(journal):
    record = journal.approved()
    for kind, index in [
        ("create", None),
        ("project_link", None),
        *[(kind, i) for i in range(3) for kind in ("presign", "put", "confirm")],
    ]:
        intent, permit, deadline = journal.arm(record, kind, index)
        assert deadline > journal.clock.monotonic()
        permit.consume()
        with pytest.raises(YorungeError) as failure:
            permit.consume()
        assert failure.value.code == "operation_conflict"
        record = journal.accept(record, intent).operation
    assert record.status == "running"
    proof = TransferVerification(
        schema_version=2,
        scope=journal.plan.scope,
        authorization_policy="verified_read",
        dataset_id=DATASET,
        project_id=journal.plan.scope.project_id,
        grant=journal.plan.grant,
        observed_at=timestamp(journal.clock.value),
        files=tuple(
            VerifiedFile(
                file_index=i,
                item_id=str(uuid4()),
                path_digest=hashlib.sha256(f.path.encode()).hexdigest(),
                size_bytes=f.size,
                sha256=f.sha256,
            )
            for i, f in enumerate(journal.manifest.files)
        ),
    )
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        view = repo.verified(record.operation_id, record.lease, proof)
        assert view.operation.status == "succeeded" and view.operation.lease is None
        assert len(view.intents) == 11 and len(view.receipts) == 11
        assert store.verify().store_schema_version == 7

        def invoke():
            return repo.arm(
                record.operation_id,
                record.lease,
                journal.plan,
                "create",
                None,
                total_end=time.monotonic() + 900,
            )

        with pytest.raises(YorungeError):
            invoke()


@pytest.mark.parametrize("boundary", ["before", "after"])
@pytest.mark.parametrize("change", ["revoke", "rotate"])
def test_changes_before_and_after_intent_have_distinct_guarantees(journal, boundary, change):
    record = journal.approved()
    if boundary == "after":
        _, permit, _ = journal.arm(record)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        if change == "revoke":
            repo.revoke(journal.plan.plan_id, journal.plan.digest)
        else:
            changed = ResolvedCredential(
                journal.bound.credential.reference,
                journal.bound.credential.target,
                SecretValue("synthetic-rotated-JOURNAL-key"),
            )
            StateCredentialRegistry(store).observe(changed)
    if boundary == "after":
        # A committed PID-local permit cannot be recalled by a later revoke.
        permit.consume()
    else:
        with pytest.raises(YorungeError) as failure:
            journal.arm(record)
        assert failure.value.code in {"approval_required", "state_changed"}
    with open_store(journal.root) as store:
        view = read_view(store.connection, journal.plan.plan_id)
        assert len(view.intents) == (boundary == "after")
        assert view.operation.workflow_latched == (boundary == "after")


def test_lost_receipt_never_reissues_stage_and_recovery_is_read_only(journal):
    record = journal.approved()
    journal.arm(record)[1].consume()
    journal.clock.value += timedelta(seconds=151)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        with pytest.raises(YorungeError) as missing_id:
            repo.acquire_read(record.operation_id, journal.plan.grant)
        assert missing_id.value.code == "operation_uncertain"
        lease = record.lease
        view = repo.show(operation_id=record.operation_id)
        assert view.operation.status == "unknown" and view.operation.dataset_id is None
        assert view.operation.lease is None and view.operation.fence == 2
        assert len(view.intents) == 1 and not view.receipts

        def invoke():
            return repo.arm(
                record.operation_id,
                lease,
                journal.plan,
                "create",
                None,
                total_end=journal.clock.monotonic() + 900,
            )

        with pytest.raises(YorungeError) as failure:
            invoke()
        assert failure.value.code == "operation_lease_lost"
        assert store.verify().store_schema_version == 7


def test_predispatch_owner_loss_can_be_closed_after_revoke(journal):
    record = journal.approved()
    with open_store(journal.root) as store:
        journal.repository(store).revoke(journal.plan.plan_id, journal.plan.digest)
    journal.clock.value += timedelta(seconds=151)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        with pytest.raises(YorungeError):
            repo.acquire_read(record.operation_id, journal.plan.grant)
        view = repo.show(operation_id=record.operation_id)
        assert view.operation.status == "cancelled"
        assert view.operation.reason == "approval_revoked"
        assert not view.intents and len(view.controls) == 1
        store.verify()


def test_heartbeat_does_not_change_reset_consent(journal):
    record = journal.approved()
    before = api.preview_identity_reset(state_dir=journal.root).data
    journal.clock.value += timedelta(seconds=1)
    with open_store(journal.root) as store:
        owner = journal.repository(store).renew(record.operation_id, record.lease)
        assert owner.expires_at != record.lease.expires_at
    after = api.preview_identity_reset(state_dir=journal.root).data
    assert before.schema_version == after.schema_version == 4
    assert before.digest == after.digest
    assert after.current.transfer_operation_count == 1


@pytest.mark.parametrize("armed", [False, True])
def test_reset_preserves_history_and_handles_future_year(journal, monkeypatch, armed):
    journal.clock.value += timedelta(days=366)
    # Rebase a valid plan to the erroneous future clock before admission.
    body = journal.plan.model_dump(mode="json")
    for value in (body, body["grant"], body["cost_bound"]):
        for key in ("prepared_at", "checked_at", "expires_at"):
            if key in value:
                value[key] = timestamp(instant(value[key]) + timedelta(days=366))
    journal.plan = seal(body)
    record = journal.approved()
    if armed:
        journal.arm(record)
    journal.clock.value -= timedelta(days=366)
    preview = api.preview_identity_reset(state_dir=journal.root).data
    result = api.reset_identity(preview.digest, state_dir=journal.root).data
    with open_store(journal.root) as store:
        view = StateUploads(store, clock=journal.clock).show(plan_id=journal.plan.plan_id)
        assert view.operation.status == ("unknown" if armed else "cancelled")
        assert view.operation.observed_identity_epoch == result.identity_epoch
        assert view.operation.clock_anomaly and view.operation.lease is None
        assert len(view.intents) == armed
        assert store.verify().store_schema_version == 7


@pytest.mark.parametrize(
    "damage",
    ["plan-index", "intent-index", "request-digest", "reservation", "receipt-body", "latch"],
)
@pytest.mark.parametrize("path", ["warm", "full"])
def test_corruption_is_rejected_at_both_read_boundaries(journal, damage, path):
    record = journal.approved()
    intent, _, _ = journal.arm(record)
    journal.accept(record, intent)
    with open_store(journal.root) as store:
        c = store.connection
        if damage == "plan-index":
            c.execute("UPDATE upload_plans SET expires_at='2027-01-01T00:00:00.000000Z'")
        elif damage == "intent-index":
            c.execute("UPDATE upload_stage_intents SET kind='project_link'")
        elif damage == "reservation":
            c.execute("UPDATE upload_operations SET reservation=1")
        else:
            table = {
                "request-digest": "upload_stage_intents",
                "receipt-body": "upload_stage_receipts",
                "latch": "upload_operations",
            }[damage]
            body = json.loads(c.execute(f"SELECT payload FROM {table}").fetchone()[0])
            if damage == "request-digest":
                body["request_digest"] = "0" * 64
            elif damage == "receipt-body":
                body["dataset_id"] = str(uuid4())
            else:
                body["workflow_latched"] = False
            c.execute(
                f"UPDATE {table} SET payload=?",
                (json.dumps(body, sort_keys=True, separators=(",", ":")),),
            )
        invoke = store.verify if path == "full" else lambda: read_view(c, journal.plan.plan_id)
        with pytest.raises(YorungeError) as failure:
            invoke()
        assert failure.value.code == "state_invalid"


def test_new_plan_or_reset_does_not_bypass_namespace(journal):
    record = journal.approved()
    journal.arm(record)
    body = journal.plan.model_dump(mode="json")
    body["plan_id"] = str(uuid4())
    body["root"]["inode"] += 1
    changed = seal(body)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        before = capacity(store.connection)
        with pytest.raises(YorungeError) as failure:
            repo.save(changed, journal.manifest)
        assert failure.value.code == "operation_conflict"
        assert failure.value.operation_id == record.operation_id
        assert capacity(store.connection) == before


def test_declared_payload_budget_rolls_back_before_effect_and_reserves_recovery(
    journal, monkeypatch
):
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        repo.save(journal.plan, journal.manifest)
        repo.approve(journal.plan.plan_id, journal.plan.digest, journal.plan)
        from yorunge.adapters import upload_store

        before = capacity(store.connection)
        monkeypatch.setattr(upload_store, "MAX_TRANSFER_PAYLOAD_BYTES", before[-1] + 1)
        with pytest.raises(YorungeError) as failure:
            repo.admit(journal.plan.plan_id, journal.plan)
        assert failure.value.code == "upload_capacity_exceeded"
        assert repo.show(plan_id=journal.plan.plan_id).operation is None
        assert capacity(store.connection) == before
        monkeypatch.undo()
        record = repo.admit(journal.plan.plan_id, journal.plan)
        reserved = capacity(store.connection)[-1]
        intent, _, _ = repo.arm(
            record.operation_id,
            record.lease,
            journal.plan,
            "create",
            None,
            total_end=journal.clock.monotonic() + 900,
        )
        assert capacity(store.connection)[-1] == reserved
        assert read_manifest(store.connection, journal.plan) == journal.manifest
        assert intent.kind == "create"
        repo.stop_local(record.operation_id, record.lease)
        assert capacity(store.connection)[-1] == reserved
        store.verify()


def _admit_then_pause(journal, committed):
    import signal

    with open_store(journal.root) as store:
        journal.repository(store).admit(journal.plan.plan_id, journal.plan)
        committed.set()  # No operation ID has been delivered to the caller.
        signal.pause()


def test_real_kill_after_admission_before_id_output_is_recoverable(journal):
    import multiprocessing

    with open_store(journal.root) as store:
        repo = journal.repository(store)
        repo.save(journal.plan, journal.manifest)
        repo.approve(journal.plan.plan_id, journal.plan.digest, journal.plan)
    context = multiprocessing.get_context("fork")
    committed = context.Event()
    process = context.Process(target=_admit_then_pause, args=(journal, committed))
    process.start()
    try:
        assert committed.wait(10), "child did not commit"
        process.kill()
        process.join(10)
        assert process.exitcode != 0 and not process.is_alive()
        with open_store(journal.root) as store:
            repo = StateUploads(store, clock=journal.clock)
            view = repo.show(plan_id=journal.plan.plan_id)
            assert view.operation is not None
            assert not view.intents and not view.operation.workflow_latched
            assert repo.admit(journal.plan.plan_id, journal.plan) == view.operation
            assert store.verify().store_schema_version == 7
    finally:
        if process.is_alive():
            process.kill()
            process.join(10)


def _race_arm(journal, barrier, result):
    try:
        with open_store(journal.root) as store:
            repo = journal.repository(store)
            record = repo.show(plan_id=journal.plan.plan_id).operation
            barrier.wait(timeout=10)
            intent, _, _ = repo.arm(
                record.operation_id,
                record.lease,
                journal.plan,
                "create",
                None,
                total_end=journal.clock.monotonic() + 900,
            )
            result.put(("armed", intent.intent_id))
    except YorungeError as error:
        result.put(("error", error.code))


def test_forked_processes_cannot_arm_from_a_durable_lease(journal):
    import multiprocessing

    record = journal.approved()
    context = multiprocessing.get_context("fork")
    barrier, results = context.Barrier(2), context.Queue()
    processes = [
        context.Process(target=_race_arm, args=(journal, barrier, results)) for _ in range(2)
    ]
    for process in processes:
        process.start()
    try:
        replies = [results.get(timeout=15) for _ in processes]
        assert all(r == ("error", "operation_lease_lost") for r in replies)
        with open_store(journal.root) as store:
            view = journal.repository(store).show(operation_id=record.operation_id)
            assert not view.intents and not view.operation.workflow_latched
            store.verify()
    finally:
        for process in processes:
            process.join(10)
            if process.is_alive():
                process.kill()
                process.join(10)


@pytest.mark.parametrize("consumer", ["plan", "approval", "lease"])
def test_other_stateful_call_observes_upload_frontier_before_clock_rollback(journal, consumer):
    record = journal.approved()
    if consumer == "lease":
        boundary = instant(record.lease.expires_at)
    else:
        boundary = instant(journal.plan.expires_at)
    journal.clock.value = boundary
    with open_store(journal.root) as store:
        observed = StateCache(store, journal.clock).stamp()
    journal.clock.value = boundary - timedelta(seconds=1)
    with open_store(journal.root) as store:
        after = StateCache(store, journal.clock).stamp()
        assert after.generation > observed.generation
        with pytest.raises(YorungeError):
            journal.repository(store).renew(record.operation_id, record.lease)
        assert not read_view(store.connection, journal.plan.plan_id).intents


def test_stage_deadline_crossed_before_commit_rolls_back_intent(journal):
    record = journal.approved()
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        original = repo._change

        def delay(*args, **kwargs):
            value = original(*args, **kwargs)
            journal.clock.value += timedelta(seconds=31)
            return value

        repo._change = delay
        with pytest.raises(YorungeError) as failure:
            repo.arm(
                record.operation_id,
                record.lease,
                journal.plan,
                "create",
                None,
                total_end=journal.clock.monotonic() + 900,
            )
        assert failure.value.code == "execution_timeout"
        assert not repo.show(operation_id=record.operation_id).intents
        assert not repo.show(operation_id=record.operation_id).operation.workflow_latched


def test_schema7_sql_failure_rolls_back_all_new_tables_and_preserves_old_rows(
    tmp_path, monkeypatch
):
    from yorunge.adapters import state, state_schema

    root = tmp_path / "migration"
    with monkeypatch.context() as old:
        old.setattr(state_schema, "MIGRATIONS", state_schema.MIGRATIONS[:6])
        with open_store(root) as store:
            old_rows = store.connection.execute(
                "SELECT * FROM schema_migrations ORDER BY version"
            ).fetchall()
            identity = store.info
    original = state.apply_migration

    def broken(connection, step, deadline, transform=None):
        if step.to_version == 7:
            connection.execute(step.statements[0])
            raise YorungeError("state_write_failed")
        return original(connection, step, deadline, transform)

    with monkeypatch.context() as failure:
        failure.setattr(state, "apply_migration", broken)
        with pytest.raises(YorungeError):
            with open_store(root):
                pass
    import sqlite3

    from yorunge.adapters.state import DB_NAME

    with sqlite3.connect(root / DB_NAME) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (6,)
        assert (
            connection.execute(
                "SELECT name FROM sqlite_schema WHERE name LIKE 'upload_%'"
            ).fetchall()
            == []
        )
        assert (
            connection.execute("SELECT * FROM schema_migrations ORDER BY version").fetchall()
            == old_rows
        )
    with open_store(root) as store:
        assert store.info.store_id == identity.store_id
        assert store.verify().store_schema_version == 7
        assert (
            store.connection.execute(
                "SELECT * FROM schema_migrations WHERE version<=6 ORDER BY version"
            ).fetchall()
            == old_rows
        )


def test_386_intents_have_independent_recovery_slots_and_bounded_full_validation(journal):
    from yorunge.adapters.upload_store import request_digest
    from yorunge.domain.dataset_manifest import DatasetFile, build_manifest
    from yorunge.domain.dataset_transfer import StageIntent
    from yorunge.domain.dataset_upload import manifest_reference

    # A large valid SQL fixture is not simulated remote acceptance. It isolates
    # the on-disk graph and the real read-only takeover at its maximum capacity.
    journal.manifest = build_manifest(
        tuple(
            DatasetFile(path=f"item-{i:03}.bin", size=0, sha256=hashlib.sha256(b"").hexdigest())
            for i in range(128)
        )
    )
    body = journal.plan.model_dump(mode="json")
    body["manifest"] = manifest_reference(journal.manifest).model_dump(mode="json")
    journal.plan = seal(body)
    record = journal.approved()
    accepted = {}
    stages = [
        ("create", None),
        ("project_link", None),
        *[(kind, i) for i in range(128) for kind in ("presign", "put", "confirm")],
    ]
    with open_store(journal.root) as store:
        c = store.connection
        c.execute("BEGIN IMMEDIATE")
        for sequence, (kind, index) in enumerate(stages, 1):
            intent = StageIntent(
                schema_version=1,
                intent_id=str(uuid4()),
                operation_id=record.operation_id,
                sequence=sequence,
                kind=kind,
                file_index=index,
                request_digest=request_digest(
                    journal.plan, journal.manifest, kind, index, accepted
                ),
                owner=record.lease,
                intended_at=record.created_at,
                expires_at=timestamp(instant(record.created_at) + timedelta(seconds=30)),
            )
            receipt = StageReceipt(
                schema_version=1,
                intent_id=intent.intent_id,
                recorded_at=record.created_at,
                result="accepted",
                dataset_id=DATASET,
                object_key=f"objects/{index}" if index is not None else None,
                sent_bytes=0 if kind == "put" else None,
                sent_sha256=hashlib.sha256(b"").hexdigest() if kind == "put" else None,
            )
            accepted[(kind, index)] = receipt
            c.execute(
                "INSERT INTO upload_stage_intents VALUES(?,?,?,?,?,?)",
                (
                    intent.intent_id,
                    record.operation_id,
                    sequence,
                    kind,
                    index if index is not None else -1,
                    intent.encoded().decode(),
                ),
            )
            c.execute(
                "INSERT INTO upload_stage_receipts VALUES(?,?)",
                (intent.intent_id, receipt.encoded().decode()),
            )
        changed = record.model_copy(
            update={
                "workflow_latched": True,
                "dataset_id": DATASET,
                "status": "running",
                "revision": 773,
            }
        )
        c.execute(
            "UPDATE upload_operations SET revision=?,payload=?",
            (changed.revision, changed.encoded().decode()),
        )
        c.execute(
            "UPDATE upload_namespaces SET create_operation_id=? WHERE intent_digest=?",
            (record.operation_id, record.intent_digest),
        )
        c.execute("COMMIT")
        before = capacity(c)
        assert len(read_view(c, journal.plan.plan_id).intents) == 386
        store.verify()
    journal.clock.value += timedelta(seconds=151)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        lease = repo.acquire_read(record.operation_id, journal.plan.grant)
        view = repo.show(operation_id=record.operation_id)
        assert lease.mode == "read" and len(view.intents) == 386
        assert len(view.controls) == 1 and view.controls[0].kind == "recovery"
        assert capacity(store.connection) == before
        repo.stop_local(record.operation_id, lease)
        assert len(repo.show(operation_id=record.operation_id).controls) == 1
        store.verify()


def test_known_rejection_does_not_hide_another_inflight_request(journal):
    record = journal.approved()
    for kind in ("create", "project_link"):
        intent, _, _ = journal.arm(record, kind)
        record = journal.accept(record, intent).operation
    first, _, _ = journal.arm(record, "presign", 0)
    second, _, _ = journal.arm(record, "presign", 1)
    view = journal.accept(record, first, rejected=True)
    assert view.operation.status == "unknown" and view.operation.reason == "provider_rejected"
    with pytest.raises(YorungeError):
        journal.arm(view.operation, "presign", 2)
    view = journal.accept(view.operation, second)
    assert view.operation.status == "failed" and view.operation.lease is None
    assert {c.kind for c in view.controls} == {"recovery", "terminal"}
    with open_store(journal.root) as store:
        store.verify()


def test_cancelled_preintent_does_not_burn_a_future_plan_namespace(journal):
    record = journal.approved()
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        repo.stop_local(record.operation_id, record.lease, "local_cancelled")
        body = journal.plan.model_dump(mode="json")
        body["plan_id"] = str(uuid4())
        renewed = seal(body)
        assert renewed.intent_digest() == journal.plan.intent_digest()
        repo.save(renewed, journal.manifest)
        repo.approve(renewed.plan_id, renewed.digest, renewed)
        next_record = repo.admit(renewed.plan_id, renewed)
        intent, permit, _ = repo.arm(
            next_record.operation_id,
            next_record.lease,
            renewed,
            "create",
            None,
            total_end=journal.clock.monotonic() + 900,
        )
        assert next_record.operation_id != record.operation_id and intent.kind == "create"
        permit.consume()
        store.verify()


@pytest.mark.parametrize("stage", ["admit", "arm"])
def test_rotation_committed_by_second_connection_before_begin_is_rechecked(
    journal, stage, monkeypatch
):
    from contextlib import contextmanager

    if stage == "arm":
        record = journal.approved()
    else:
        with open_store(journal.root) as store:
            repo = journal.repository(store)
            repo.save(journal.plan, journal.manifest)
            repo.approve(journal.plan.plan_id, journal.plan.digest, journal.plan)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        original = repo.cache.transaction

        @contextmanager
        def rotate_then_begin(*args, **kwargs):
            with open_store(journal.root) as other:
                changed = ResolvedCredential(
                    journal.bound.credential.reference,
                    journal.bound.credential.target,
                    SecretValue("changed-synthetic-key-from-second-connection"),
                )
                StateCredentialRegistry(other).observe(changed)
            with original(*args, **kwargs) as gate:
                yield gate

        monkeypatch.setattr(repo.cache, "transaction", rotate_then_begin)
        if stage == "arm":

            def invoke():
                return repo.arm(
                    record.operation_id,
                    record.lease,
                    journal.plan,
                    "create",
                    None,
                    total_end=journal.clock.monotonic() + 900,
                )
        else:

            def invoke():
                return repo.admit(journal.plan.plan_id, journal.plan)

        with pytest.raises(YorungeError) as failure:
            invoke()
        assert failure.value.code == "state_changed"
        view = read_view(store.connection, journal.plan.plan_id)
        assert not view.intents
        assert (view.operation is not None) == (stage == "arm")


def test_failure_after_intent_commit_preserves_unknown_id_and_blocks_replay(journal, monkeypatch):
    record = journal.approved()
    with open_store(journal.root) as store:
        repo = journal.repository(store)

        def changed(*args, **kwargs):
            raise YorungeError("state_changed")

        monkeypatch.setattr(repo, "_finish", changed)
        with pytest.raises(YorungeError) as failure:
            repo.arm(
                record.operation_id,
                record.lease,
                journal.plan,
                "create",
                None,
                total_end=journal.clock.monotonic() + 900,
            )
        assert failure.value.code == "operation_uncertain"
        assert failure.value.operation_id == record.operation_id
        view = repo.show(plan_id=journal.plan.plan_id)
        assert len(view.intents) == 1 and view.operation.workflow_latched
    with pytest.raises(YorungeError) as failure:
        journal.arm(record)
    assert failure.value.code == "operation_conflict"


@pytest.mark.parametrize("kind", ["plans", "files"])
def test_actual_global_cardinality_limits_preserve_all_existing_rows(journal, kind):
    from yorunge.adapters.upload_store import namespace
    from yorunge.domain.dataset_manifest import DatasetFile, build_manifest
    from yorunge.domain.dataset_upload import manifest_reference

    if kind == "files":
        journal.manifest = build_manifest(
            tuple(
                DatasetFile(path=f"empty-{i}", size=0, sha256=hashlib.sha256(b"").hexdigest())
                for i in range(128)
            )
        )
    count = 128 if kind == "plans" else 32
    base = journal.plan.model_dump(mode="json")
    base["manifest"] = manifest_reference(journal.manifest).model_dump(mode="json")
    with open_store(journal.root, timeout=30) as store:
        c = store.connection
        c.execute(
            "INSERT INTO upload_manifests VALUES(?,?)",
            (journal.manifest.digest, journal.manifest.encoded().decode()),
        )
        for index in range(count):
            body = dict(base)
            body["plan_id"] = str(uuid4())
            body["parameters"] = {**body["parameters"], "name": f"sample-{index}"}
            plan = seal(body)
            c.execute(
                "INSERT INTO upload_namespaces VALUES(?,?,NULL)",
                (plan.intent_digest(), namespace(plan).decode()),
            )
            c.execute(
                "INSERT INTO upload_plans VALUES(?,?,?,?,?,?)",
                (
                    plan.plan_id,
                    plan.intent_digest(),
                    plan.manifest.digest,
                    plan.prepared_at,
                    plan.expires_at,
                    plan.encoded().decode(),
                ),
            )
    # Fixture construction is not the action's five-second store phase.
    with open_store(journal.root) as store:
        c = store.connection
        before = capacity(c)
        assert before[0] == count
        if kind == "files":
            assert before[2] == 4096
        body["plan_id"] = str(uuid4())
        body["parameters"] = {**body["parameters"], "name": "one-too-many"}
        overflow = seal(body)
        with pytest.raises(YorungeError) as failure:
            journal.repository(store).save(overflow, journal.manifest)
        assert failure.value.code == "upload_capacity_exceeded"
        assert capacity(c) == before
        store.verify()


def test_approval_space_is_reserved_before_creation_and_revoke(journal, monkeypatch):
    from yorunge.adapters import upload_store

    with open_store(journal.root) as store:
        repo = journal.repository(store)
        repo.save(journal.plan, journal.manifest)
        reserved = capacity(store.connection)[-1]
        monkeypatch.setattr(upload_store, "MAX_TRANSFER_PAYLOAD_BYTES", reserved)
        repo.approve(journal.plan.plan_id, journal.plan.digest, journal.plan)
        payload_bytes = store.connection.execute(
            "SELECT length(CAST(payload AS BLOB)) FROM upload_approvals"
        ).fetchone()[0]
        assert capacity(store.connection)[-1] == reserved
        repo.revoke(journal.plan.plan_id, journal.plan.digest)
        larger = store.connection.execute(
            "SELECT length(CAST(payload AS BLOB)) FROM upload_approvals"
        ).fetchone()[0]
        assert larger > payload_bytes
        assert capacity(store.connection)[-1] == reserved
        store.verify()


@pytest.mark.parametrize("change", ["rotation", "reset"])
def test_current_read_grant_can_renew_after_identity_changes(journal, change):
    from yorunge.adapters.upload_maintenance import upload_snapshot

    record = journal.approved()
    intent, _, _ = journal.arm(record)
    record = journal.accept(record, intent).operation
    if change == "reset":
        preview = api.preview_identity_reset(state_dir=journal.root).data
        api.reset_identity(preview.digest, state_dir=journal.root)
    else:
        journal.clock.value += timedelta(seconds=151)
    with open_store(journal.root) as store:
        credential = ResolvedCredential(
            journal.bound.credential.reference,
            journal.bound.credential.target,
            SecretValue("renew-current-read-synthetic-value"),
        )
        identity = StateCredentialRegistry(store).observe(credential)
        stamp = StateCache(store, journal.clock).stamp()
        scope = journal.plan.scope.model_copy(
            update={
                "credential_id": identity.credential_id,
                "credential_revision": identity.credential_revision,
                "identity_epoch": stamp.identity_epoch,
                "clock_generation": stamp.generation,
            }
        )
        grant = journal.plan.grant.model_copy(update={"scope": scope})
        bound = BoundCredential(journal.bound.context, credential, identity)
        repo = StateUploads(store, bound, clock=journal.clock)
        lease = repo.acquire_read(record.operation_id, grant)
        before = upload_snapshot(store.connection, store.deadline)
        journal.clock.value += timedelta(seconds=1)
        with pytest.raises(YorungeError):
            repo.renew(record.operation_id, lease)
        changed = repo.renew(record.operation_id, lease, grant=grant)
        assert changed.owner_id == lease.owner_id and changed.fence == lease.fence
        assert instant(changed.expires_at) > instant(lease.expires_at)
        assert upload_snapshot(store.connection, store.deadline) == before
        with pytest.raises(YorungeError):
            repo.arm(
                record.operation_id,
                changed,
                journal.plan,
                "create",
                None,
                total_end=journal.clock.monotonic() + 900,
            )
        store.verify()


def test_arm_renews_same_write_owner_and_uses_current_db_lease(journal):
    record = journal.approved()
    journal.clock.value += timedelta(seconds=120)
    intent, _, deadline = journal.arm(record)
    assert intent.owner.owner_id == record.lease.owner_id
    assert intent.owner.fence == record.lease.fence
    assert instant(intent.owner.expires_at) == journal.clock.value + timedelta(seconds=150)
    assert deadline > journal.clock.monotonic() + 24
    journal.clock.value += timedelta(seconds=20)
    # The token's old expires_at is not the authority after a valid renewal;
    # the repository re-reads current owner/fence and current DB lease timing.
    view = journal.accept(record, intent)
    assert view.operation.dataset_id == DATASET


def test_reopened_repository_cannot_recreate_write_access_even_in_original_pid(journal):
    from yorunge.application.transfer_access import TransferWriteAccess

    record = journal.approved()
    first, _, _ = journal.arm(record)
    journal.accept(record, first)
    with open_store(journal.root) as store:
        repo = StateUploads(store, journal.bound, clock=journal.clock)
        historical = repo.show(plan_id=journal.plan.plan_id).operation
        assert repo.admit(journal.plan.plan_id, journal.plan) == historical
        assert repo.write_access is None
        for access in (
            None,
            TransferWriteAccess(
                record.operation_id, record.write_owner_id, journal.clock.monotonic() + 900
            ),
        ):
            repo.write_access = access
            with pytest.raises(YorungeError) as failure:
                repo.arm(
                    record.operation_id,
                    historical.lease,
                    journal.plan,
                    "project_link",
                    None,
                    total_end=journal.clock.monotonic() + 900,
                )
            assert failure.value.code == "operation_lease_lost"
        assert len(repo.show(plan_id=journal.plan.plan_id).intents) == 1
        store.verify()


def test_same_process_two_connections_with_original_access_have_one_stage_intent(journal):
    from concurrent.futures import ThreadPoolExecutor
    from queue import Queue
    from threading import Barrier

    record = journal.approved()
    barrier, results = Barrier(2), Queue()
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(_race_arm, journal, barrier, results) for _ in range(2)]
        for future in futures:
            future.result(timeout=15)
    replies = [results.get(timeout=1) for _ in futures]
    assert sorted(r[0] for r in replies) == ["armed", "error"]
    assert next(r[1] for r in replies if r[0] == "error") == "operation_conflict"
    with open_store(journal.root) as store:
        view = read_view(store.connection, journal.plan.plan_id)
        assert len(view.intents) == 1 and view.operation.operation_id == record.operation_id
        store.verify()


def test_write_access_cannot_be_copied_serialized_or_extend_original_deadline(journal):
    import copy
    import pickle

    record = journal.approved()
    access = journal.access
    for invoke in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(TypeError):
            invoke(access)
    with pytest.raises(AttributeError):
        access._end = float("inf")
    journal.clock.elapsed += 901
    with pytest.raises(YorungeError) as failure:
        journal.arm(record)
    assert failure.value.code == "operation_lease_lost"


def complete_metadata_fixture(journal):
    record = journal.approved()
    for kind, index in [
        ("create", None),
        ("project_link", None),
        *[(kind, i) for i in range(3) for kind in ("presign", "put", "confirm")],
    ]:
        intent, permit, _ = journal.arm(record, kind, index)
        permit.consume()
        record = journal.accept(record, intent).operation
        journal.clock.value += timedelta(seconds=1)
    proof = TransferVerification(
        schema_version=2,
        scope=journal.plan.scope,
        authorization_policy="verified_read",
        dataset_id=DATASET,
        project_id=journal.plan.scope.project_id,
        grant=journal.plan.grant,
        observed_at=timestamp(journal.clock.value),
        files=tuple(
            VerifiedFile(
                file_index=i,
                item_id=str(uuid4()),
                path_digest=hashlib.sha256(f.path.encode()).hexdigest(),
                size_bytes=f.size,
                sha256=f.sha256,
            )
            for i, f in enumerate(journal.manifest.files)
        ),
    )
    return record, proof


def test_metadata_observation_before_confirm_does_not_produce_success(journal):
    record, proof = complete_metadata_fixture(journal)
    old = proof.model_copy(update={"observed_at": record.created_at})
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        with pytest.raises(YorungeError) as failure:
            repo.verified(record.operation_id, record.lease, old)
        assert failure.value.code == "operation_uncertain"
        view = repo.show(operation_id=record.operation_id)
        assert view.operation.status == "unknown" and view.verification is None
        assert (
            repo.verified(record.operation_id, record.lease, proof).operation.status == "succeeded"
        )
        store.verify()


@pytest.mark.parametrize("boundary", ["warm", "full"])
def test_stale_observation_is_rejected_even_with_consistent_terminal_hash(journal, boundary):
    record, proof = complete_metadata_fixture(journal)
    with open_store(journal.root) as store:
        journal.repository(store).verified(record.operation_id, record.lease, proof)
        body = proof.model_copy(update={"observed_at": record.created_at}).encoded()
        c = store.connection
        c.execute("UPDATE upload_verifications SET payload=?", (body.decode(),))
        control = json.loads(
            c.execute("SELECT payload FROM upload_controls WHERE kind='terminal'").fetchone()[0]
        )
        control["verification_digest"] = hashlib.sha256(body).hexdigest()
        c.execute(
            "UPDATE upload_controls SET payload=? WHERE kind='terminal'",
            (json.dumps(control, sort_keys=True, separators=(",", ":")),),
        )
        invoke = store.verify if boundary == "full" else lambda: read_view(c, journal.plan.plan_id)
        with pytest.raises(YorungeError) as failure:
            invoke()
        assert failure.value.code == "state_invalid"


def test_fresh_recovery_verification_after_reset_does_not_compare_old_future_utc(journal):
    # Old clock was a year ahead. A reset's new epoch must allow fresh read
    # evidence without waiting for that mistaken calendar date to arrive.
    shift = timedelta(days=366)
    journal.clock.value += shift
    body = journal.plan.model_dump(mode="json")
    for value in (body, body["grant"], body["cost_bound"]):
        for key in ("prepared_at", "checked_at", "expires_at"):
            if key in value:
                value[key] = timestamp(instant(value[key]) + shift)
    journal.plan = seal(body)
    record, proof = complete_metadata_fixture(journal)
    journal.clock.value -= shift
    preview = api.preview_identity_reset(state_dir=journal.root).data
    api.reset_identity(preview.digest, state_dir=journal.root)
    with open_store(journal.root) as store:
        credential = journal.bound.credential
        identity = StateCredentialRegistry(store).observe(credential)
        stamp = StateCache(store, journal.clock).stamp()
        scope = journal.plan.scope.model_copy(
            update={
                "credential_id": identity.credential_id,
                "credential_revision": identity.credential_revision,
                "identity_epoch": stamp.identity_epoch,
                "clock_generation": stamp.generation,
            }
        )
        grant = journal.plan.grant.model_copy(
            update={
                "scope": scope,
                "checked_at": timestamp(stamp.now),
                "expires_at": timestamp(stamp.now + timedelta(seconds=900)),
            }
        )
        bound = BoundCredential(journal.bound.context, credential, identity)
        repo = StateUploads(store, bound, clock=journal.clock)
        owner = repo.acquire_read(record.operation_id, grant)
        journal.clock.value += timedelta(seconds=1)
        proof = proof.model_copy(
            update={"grant": grant, "scope": scope, "observed_at": timestamp(journal.clock.value)}
        )
        assert repo.verified(record.operation_id, owner, proof).operation.status == "succeeded"
        store.verify()


@pytest.mark.parametrize(
    "deadline",
    [float("nan"), float("inf"), float("-inf"), True, "900", None, 10**1000],
    ids=["nan", "positive-inf", "negative-inf", "bool", "string", "null", "overflow"],
)
def test_nonfinite_or_wrong_deadline_never_commits_stage_or_permit(journal, deadline):
    record = journal.approved()
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        with pytest.raises(YorungeError) as failure:
            repo.arm(
                record.operation_id, record.lease, journal.plan, "create", None, total_end=deadline
            )
        assert failure.value.code == "invalid_request"
        assert failure.value.operation_id == record.operation_id
        view = repo.show(operation_id=record.operation_id)
        assert not view.intents and not view.operation.workflow_latched
        store.verify()


def explicit_unpriced_plan(plan):
    body = plan.model_dump(mode="json", exclude={"digest"})
    body.update(
        admission_policy="explicit_attempt",
        cost_policy="unpriced_accepted",
        budget_micros=None,
        grant=None,
        cost_bound=None,
        risks=["authority_unverified", "cost_unverified"],
        blockers=[],
        status="attempt_ready",
    )
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return DatasetUploadPlan.model_validate_json(
        json.dumps({**body, "digest": hashlib.sha256(raw).hexdigest()})
    )


@pytest.mark.parametrize("authority,unpriced", [(False, False), (False, True), (True, False)])
def test_unverified_unpriced_approval_needs_both_explicit_acknowledgements(
    journal, authority, unpriced
):
    journal.plan = explicit_unpriced_plan(journal.plan)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        repo.save(journal.plan, journal.manifest)
        with pytest.raises(YorungeError) as error:
            repo.approve(
                journal.plan.plan_id,
                journal.plan.digest,
                journal.plan,
                acknowledge_unverified_authority=authority,
                acknowledge_unpriced_cost=unpriced,
            )
        assert error.value.code == "approval_required"
        assert repo.show(plan_id=journal.plan.plan_id).approval is None
        assert store.connection.execute("SELECT count(*) FROM upload_operations").fetchone() == (0,)


def test_explicit_unknown_proofs_can_arm_once_without_fabricated_expiry(journal):
    journal.plan = explicit_unpriced_plan(journal.plan)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        repo.save(journal.plan, journal.manifest)
        approval = repo.approve(
            journal.plan.plan_id,
            journal.plan.digest,
            journal.plan,
            acknowledge_unverified_authority=True,
            acknowledge_unpriced_cost=True,
        )
        record = repo.admit(journal.plan.plan_id, journal.plan)
        journal.access = repo.write_access
        intent, permit, deadline = repo.arm(
            record.operation_id,
            record.lease,
            journal.plan,
            "create",
            None,
            total_end=journal.clock.monotonic() + 900,
        )
        assert intent.schema_version == 1 and record.schema_version == approval.schema_version == 2
        assert deadline > journal.clock.monotonic()
        permit.consume()
        with pytest.raises(YorungeError):
            repo.arm(
                record.operation_id,
                record.lease,
                journal.plan,
                "create",
                None,
                total_end=journal.clock.monotonic() + 900,
            )
        saved = repo.show(plan_id=journal.plan.plan_id)
        assert len(saved.intents) == 1 and saved.plan.grant is saved.plan.cost_bound is None
        assert saved.plan.status == "attempt_ready" and saved.plan.risks == (
            "authority_unverified",
            "cost_unverified",
        )
        assert saved.plan.encoded() == journal.plan.encoded()
        store.verify()


@pytest.mark.parametrize(
    "outcome,code",
    [
        ("denied", "remote_access_denied"),
        ("unavailable", "remote_rate_limited"),
        ("unavailable", "transport_timeout"),
        ("invalid", "invalid_response"),
    ],
)
def test_explicit_policy_never_bypasses_current_known_negative_or_unavailable(
    journal, outcome, code
):
    journal.plan = explicit_unpriced_plan(journal.plan)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        repo.save(journal.plan, journal.manifest)
        repo.approve(
            journal.plan.plan_id,
            journal.plan.digest,
            journal.plan,
            acknowledge_unverified_authority=True,
            acknowledge_unpriced_cost=True,
        )
        record = repo.admit(journal.plan.plan_id, journal.plan)
        check = repo.capture(journal.plan)
        failed = check.authorization.model_copy(update={"outcome": outcome, "error_code": code})
        check = check.model_copy(update={"authorization": failed})
        with pytest.raises(YorungeError) as error:
            repo.arm(
                record.operation_id,
                record.lease,
                check,
                "create",
                None,
                total_end=journal.clock.monotonic() + 900,
            )
        assert error.value.code == code and error.value.operation_id == record.operation_id
        assert repo.show(operation_id=record.operation_id).intents == ()
        store.verify()


def test_legacy_scope_only_price_cannot_create_new_approval_or_admission(journal):
    from yorunge.domain.dataset_upload import DatasetUploadPlan as V1Plan

    body = json.loads((FIXTURES / "dataset-upload-approved-v1.json").read_bytes())["plan"]
    body["scope"] = journal.plan.scope.model_dump(mode="json")
    for field in ("grant", "cost_bound"):
        body[field]["scope"] = body["scope"]
    body.pop("digest")
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    legacy = V1Plan.model_validate_json(
        json.dumps({**body, "digest": hashlib.sha256(raw).hexdigest()})
    )
    with open_store(journal.root) as store:
        repo = StateUploads(store, journal.bound, clock=journal.clock)
        repo.save(legacy, journal.manifest)
        for invoke in (
            lambda: repo.approve(legacy.plan_id, legacy.digest, legacy),
            lambda: repo.admit(legacy.plan_id, legacy),
        ):
            with pytest.raises(YorungeError) as error:
                invoke()
            assert error.value.code == "upload_plan_not_valid"
        assert all(
            store.connection.execute(f"SELECT count(*) FROM {table}").fetchone() == (0,)
            for table in ("upload_approvals", "upload_operations", "upload_stage_intents")
        )
        assert repo.show(plan_id=legacy.plan_id).plan.encoded() == legacy.encoded()
        assert repo.show(plan_id=legacy.plan_id).operation is None
        store.verify()


def test_legacy_existing_lookup_and_inflight_receipt_survive_but_new_arm_is_closed(journal):
    from yorunge.adapters.upload_store import request_digest, write_record
    from yorunge.application.transfer_access import TransferWriteAccess
    from yorunge.domain.dataset_transfer import StageIntent, TransferRecord
    from yorunge.domain.dataset_upload import DatasetUploadApproval as V1Approval
    from yorunge.domain.dataset_upload import DatasetUploadPlan as V1Plan

    body = json.loads((FIXTURES / "dataset-upload-approved-v1.json").read_bytes())["plan"]
    body["scope"] = journal.plan.scope.model_dump(mode="json")
    for field in ("grant", "cost_bound"):
        body[field]["scope"] = body["scope"]
    body.pop("digest")
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    legacy = V1Plan.model_validate_json(
        json.dumps({**body, "digest": hashlib.sha256(raw).hexdigest()})
    )
    with open_store(journal.root) as store:
        repo = StateUploads(store, journal.bound, clock=journal.clock)
        repo.save(legacy, journal.manifest)
        stamp = repo.cache.stamp()
        lease = repo._lease(stamp, fence=1, mode="write")
        approval = V1Approval(
            schema_version=1,
            approval_id=str(uuid4()),
            plan_id=legacy.plan_id,
            plan_digest=legacy.digest,
            binding_digest=legacy.binding_digest(),
            store_id=legacy.scope.store_id,
            identity_epoch=legacy.scope.identity_epoch,
            clock_generation=legacy.scope.clock_generation,
            approved_at=timestamp(stamp.now),
            expires_at=legacy.expires_at,
            status="approved",
            revoked_at=None,
        )
        operation_id = str(uuid4())
        access = TransferWriteAccess(operation_id, lease.owner_id, journal.clock.monotonic() + 900)
        record = TransferRecord(
            schema_version=1,
            operation_id=operation_id,
            plan_id=legacy.plan_id,
            plan_digest=legacy.digest,
            intent_digest=legacy.intent_digest(),
            approval=approval,
            write_owner_id=lease.owner_id,
            write_access_digest=access.digest,
            created_at=timestamp(stamp.now),
            updated_at=timestamp(stamp.now),
            status="admitted",
            revision=1,
            fence=1,
            observed_identity_epoch=legacy.scope.identity_epoch,
            observed_clock_generation=legacy.scope.clock_generation,
            clock_anomaly=False,
            lease=lease,
            workflow_latched=False,
            dataset_id=None,
            reason=None,
        )
        store.connection.execute(
            "INSERT INTO upload_approvals VALUES(?,?,?,?)",
            (
                legacy.plan_id,
                approval.approval_id,
                approval.expires_at,
                approval.encoded().decode(),
            ),
        )
        write_record(store.connection, record, None)
        repo.write_access = access
        assert repo.admit(legacy.plan_id, None) == record
        total_end = journal.clock.monotonic() + 900
        with pytest.raises(YorungeError) as error:
            repo.arm(operation_id, lease, legacy, "create", None, total_end=total_end)
        assert error.value.code == "upload_plan_not_valid"
        assert repo.show(operation_id=operation_id).intents == ()

        # This is a fixture for an intent issued before upgrading the runtime.
        intent = StageIntent(
            schema_version=1,
            intent_id=str(uuid4()),
            operation_id=operation_id,
            sequence=1,
            kind="create",
            file_index=None,
            request_digest=request_digest(legacy, journal.manifest, "create", None, {}),
            owner=lease,
            intended_at=timestamp(stamp.now),
            expires_at=timestamp(stamp.now + timedelta(seconds=30)),
        )
        store.connection.execute(
            "INSERT INTO upload_stage_intents VALUES(?,?,?,?,?,?)",
            (intent.intent_id, operation_id, 1, "create", -1, intent.encoded().decode()),
        )
        store.connection.execute(
            "UPDATE upload_namespaces SET create_operation_id=?", (operation_id,)
        )
        armed = record.model_copy(
            update={"revision": 2, "status": "running", "workflow_latched": True}
        )
        write_record(store.connection, armed, record.revision)
        receipt = StageReceipt(
            schema_version=1,
            intent_id=intent.intent_id,
            recorded_at=timestamp(stamp.now),
            result="accepted",
            dataset_id=DATASET,
            object_key=None,
            sent_bytes=None,
            sent_sha256=None,
        )
        found = repo.receipt(operation_id, lease, receipt)
        assert found.operation.schema_version == 1 and found.operation.dataset_id == DATASET
        assert len(found.receipts) == 1
        store.verify()


@pytest.mark.parametrize("phase", ["approve", "admit"])
def test_current_evidence_expiry_crossing_commit_rolls_back_business(journal, monkeypatch, phase):
    import yorunge.adapters.upload_repository as module

    with open_store(journal.root) as store:
        repo = journal.repository(store)
        repo.save(journal.plan, journal.manifest)
        if phase == "admit":
            repo.approve(journal.plan.plan_id, journal.plan.digest, journal.plan)
        check = repo.capture(journal.plan)
        short = journal.plan.grant.model_copy(
            update={"expires_at": timestamp(journal.clock.value + timedelta(seconds=1))}
        )
        check = check.model_copy(
            update={
                "baseline_grant": short,
                "authorization": check.authorization.model_copy(update={"grant": short}),
            }
        )
        original = module.require_capacity

        def advance(*args, **kwargs):
            result = original(*args, **kwargs)
            journal.clock.value += timedelta(seconds=2)
            return result

        monkeypatch.setattr(module, "require_capacity", advance)
        if phase == "approve":
            invoke = partial(repo.approve, journal.plan.plan_id, journal.plan.digest, check)
        else:
            invoke = partial(repo.admit, journal.plan.plan_id, check)
        with pytest.raises(YorungeError) as error:
            invoke()
        assert error.value.code == "upload_plan_not_valid"
        view = repo.show(plan_id=journal.plan.plan_id)
        assert view.operation is None and repo.write_access is None
        if phase == "approve":
            assert view.approval is None
        store.verify()


@pytest.mark.parametrize("field", ["snapshot", "authorization", "observation"])
@pytest.mark.parametrize("boundary", ["before_commit", "after_commit"])
def test_each_current_freshness_range_is_checked_at_commit_and_permit_return(
    journal, monkeypatch, field, boundary
):
    record = journal.approved()
    if field == "observation":
        created, _, _ = journal.arm(record)
        record = journal.accept(record, created).operation
        linked, _, _ = journal.arm(record, "project_link")
        record = journal.accept(record, linked).operation
    journal.clock.value += timedelta(seconds=40)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        kind, index = ("presign", 0) if field == "observation" else ("create", None)
        check = repo.capture(journal.plan, kind, record.dataset_id)
        old = timestamp(journal.clock.value - timedelta(seconds=29))
        if field == "snapshot":
            check = check.model_copy(update={"checked_at": old})
        elif field == "authorization":
            check = check.model_copy(
                update={"authorization": check.authorization.model_copy(update={"checked_at": old})}
            )
        else:
            check = check.model_copy(
                update={
                    "upload_observation": check.upload_observation.model_copy(
                        update={"checked_at": old}
                    )
                }
            )
        original = repo._change if boundary == "before_commit" else repo._finish

        def advance(*args, **kwargs):
            if boundary == "after_commit":
                journal.clock.value += timedelta(seconds=2)
            result = original(*args, **kwargs)
            if boundary == "before_commit":
                journal.clock.value += timedelta(seconds=2)
            return result

        monkeypatch.setattr(repo, "_change" if boundary == "before_commit" else "_finish", advance)
        before = repo.show(operation_id=record.operation_id).intents
        total_end = journal.clock.monotonic() + 900
        with pytest.raises(YorungeError) as error:
            repo.arm(record.operation_id, record.lease, check, kind, index, total_end=total_end)
        assert error.value.code == (
            "upload_plan_not_valid" if boundary == "before_commit" else "operation_uncertain"
        )
        assert error.value.operation_id == record.operation_id
        found = repo.show(operation_id=record.operation_id)
        assert len(found.intents) == len(before) + (boundary == "after_commit")
        assert found.operation.workflow_latched == (bool(before) or boundary == "after_commit")
        store.verify()


def test_verification_freshness_crossing_commit_does_not_persist_success(journal, monkeypatch):
    record, proof = complete_metadata_fixture(journal)
    journal.clock.value = instant(proof.observed_at) + timedelta(seconds=29)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        original = repo._change

        def advance(*args, **kwargs):
            result = original(*args, **kwargs)
            journal.clock.value += timedelta(seconds=2)
            return result

        monkeypatch.setattr(repo, "_change", advance)
        with pytest.raises(YorungeError) as error:
            repo.verified(record.operation_id, record.lease, proof)
        assert error.value.code == "operation_uncertain"
        view = repo.show(operation_id=record.operation_id)
        assert view.operation.status == "unknown" and view.verification is None
        assert not any(c.kind == "terminal" for c in view.controls)
        store.verify()


def test_postcommit_ephemeral_expiry_is_durable_before_clock_rollback_and_reopen(
    journal, monkeypatch
):
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        repo.save(journal.plan, journal.manifest)
        check = repo.capture(journal.plan)
        short = journal.plan.grant.model_copy(
            update={"expires_at": timestamp(journal.clock.value + timedelta(seconds=1))}
        )
        check = check.model_copy(
            update={
                "baseline_grant": short,
                "authorization": check.authorization.model_copy(update={"grant": short}),
            }
        )
        original = repo._finish

        def advance(*args, **kwargs):
            journal.clock.value += timedelta(seconds=2)
            return original(*args, **kwargs)

        monkeypatch.setattr(repo, "_finish", advance)
        with pytest.raises(YorungeError) as error:
            repo.approve(journal.plan.plan_id, journal.plan.digest, check)
        assert error.value.code == "upload_plan_not_valid"
        # Approval COMMIT happened, but delivery rejected expired current evidence.
        assert repo.show(plan_id=journal.plan.plan_id).approval is not None
    journal.clock.value -= timedelta(seconds=1, microseconds=500_000)
    with open_store(journal.root) as store:
        reopened = journal.repository(store)
        with pytest.raises(YorungeError) as error:
            reopened.admit(journal.plan.plan_id, check)
        assert error.value.code == "state_changed"
        assert reopened.show(plan_id=journal.plan.plan_id).operation is None
        stamp = reopened.cache.stamp()
        assert stamp.anomaly and stamp.generation > journal.plan.scope.clock_generation
