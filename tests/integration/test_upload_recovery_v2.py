"""Explicit scoped read recovery on real state, without granting a second write."""

import hashlib
import json
from datetime import timedelta
from uuid import uuid4

import pytest

from tests.integration.test_upload_journal import (
    DATASET,
    explicit_unpriced_plan,
    seal,
)
from tests.integration.test_upload_journal import journal as journal
from yorunge import api
from yorunge.adapters.capability_cache import StateCache
from yorunge.adapters.identity import StateCredentialRegistry
from yorunge.adapters.state import open_store
from yorunge.adapters.upload_repository import StateUploads
from yorunge.domain.capabilities import timestamp
from yorunge.domain.credentials import BoundCredential
from yorunge.domain.dataset_transfer import VerifiedFile
from yorunge.domain.dataset_transfer_v2 import TransferVerificationV2
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_checks import AuthorizationCheck


def explicit_priced_plan(plan, *, unpriced=False):
    body = plan.model_dump(mode="json", exclude={"digest"})
    body["admission_policy"] = "explicit_attempt"
    if unpriced:
        body.update(cost_policy="unpriced_accepted", budget_micros=None, status="attempt_ready")
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return DatasetUploadPlanV2.model_validate_json(
        json.dumps({**body, "digest": hashlib.sha256(raw).hexdigest()})
    )


def admit(journal, *, unknown=False):
    if unknown:
        journal.plan = explicit_unpriced_plan(journal.plan)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        repo.save(journal.plan, journal.manifest)
        repo.approve(
            journal.plan.plan_id,
            journal.plan.digest,
            journal.plan,
            acknowledge_unverified_authority="authority_unverified" in journal.plan.risks,
            acknowledge_unpriced_cost=journal.plan.cost_policy == "unpriced_accepted",
        )
        record = repo.admit(journal.plan.plan_id, journal.plan)
        journal.access = repo.write_access
        return record


def read_check(journal, *, outcome="not_exposed", code=None, scope=None):
    return AuthorizationCheck(
        consumer_profile="evren-platform-observed-upload-v2",
        policy_version=2,
        action="read_created_dataset",
        scope=scope or journal.plan.scope,
        dataset_id=DATASET,
        producer_id="fixture_only",
        producer_version="2",
        checked_at=timestamp(journal.clock.value),
        outcome=outcome,
        grant=None,
        error_code=code,
    )


def created(journal, **kwargs):
    record = admit(journal, **kwargs)
    intent, _, _ = journal.arm(record)
    return journal.accept(record, intent).operation


def complete(journal, *, unknown=True, skip_last=False):
    record = admit(journal, unknown=unknown)
    stages = [
        ("create", None),
        ("project_link", None),
        *[(kind, i) for i in range(3) for kind in ("presign", "put", "confirm")],
    ]
    for kind, index in stages[:-1] if skip_last else stages:
        intent, _, _ = journal.arm(record, kind, index)
        record = journal.accept(record, intent).operation
    proof = TransferVerificationV2(
        schema_version=2,
        dataset_id=DATASET,
        project_id=journal.plan.scope.project_id,
        scope=journal.plan.scope,
        authorization_policy="explicit_read_attempt" if unknown else "verified_read",
        grant=None if unknown else journal.plan.grant,
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


@pytest.mark.parametrize(
    "explicit,grant,flag,error",
    [
        (False, True, False, None),
        (False, False, False, "upload_plan_not_valid"),
        (False, True, True, "invalid_request"),
        (False, False, True, "invalid_request"),
        (True, True, False, None),
        (True, True, True, None),
        (True, False, False, "approval_required"),
        (True, False, True, None),
    ],
)
def test_restart_flag_grant_policy_matrix_never_creates_write_access(
    journal, explicit, grant, flag, error
):
    if explicit:
        journal.plan = explicit_priced_plan(journal.plan)
    record = created(journal)
    journal.clock.value += timedelta(seconds=151)
    with open_store(journal.root) as store:
        repo = StateUploads(store, journal.bound, clock=journal.clock)
        before = repo.show(operation_id=record.operation_id)
        kwargs = dict(
            grant=journal.plan.grant if grant else None,
            authorization=None if grant else read_check(journal),
            accept_unverified_read=flag,
        )
        if error:
            with pytest.raises(YorungeError) as failed:
                repo.acquire_read(record.operation_id, **kwargs)
            assert failed.value.code == error
            assert repo.show(operation_id=record.operation_id) == before
        else:
            lease = repo.acquire_read(record.operation_id, **kwargs)
            assert lease.mode == "read" and lease.fence == 2
            assert repo.write_access is None
            total_end = journal.clock.monotonic() + 900
            with pytest.raises(YorungeError):
                repo.arm(
                    record.operation_id,
                    lease,
                    journal.plan,
                    "project_link",
                    None,
                    total_end=total_end,
                )
        store.verify()


def test_initial_acknowledged_owner_can_finish_only_metadata_without_authority_upgrade(journal):
    record, proof = complete(journal)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        result = repo.verified(
            record.operation_id, record.lease, proof, authorization=read_check(journal)
        )
        assert (
            result.operation.status == "succeeded"
            and result.operation.reason == "metadata_verified"
        )
        assert result.verification.grant is result.plan.grant is None
        assert result.plan.risks == ("authority_unverified", "cost_unverified")
        assert result.plan.encoded() == journal.plan.encoded()
        store.verify()


def test_restart_explicit_read_flag_is_required_again_for_renew_and_proof(journal):
    record, proof = complete(journal)
    journal.clock.value += timedelta(seconds=151)
    with open_store(journal.root) as store:
        repo = StateUploads(store, journal.bound, clock=journal.clock)
        check = read_check(journal)
        lease = repo.acquire_read(
            record.operation_id, authorization=check, accept_unverified_read=True
        )
        with pytest.raises(YorungeError) as missing:
            repo.renew(record.operation_id, lease, authorization=check)
        assert missing.value.code == "approval_required"
        renewed = repo.renew(
            record.operation_id, lease, authorization=check, accept_unverified_read=True
        )
        proof = proof.model_copy(update={"observed_at": timestamp(journal.clock.value)})
        with pytest.raises(YorungeError) as missing:
            repo.verified(record.operation_id, renewed, proof, authorization=check)
        assert missing.value.code == "approval_required"
        result = repo.verified(
            record.operation_id, renewed, proof, authorization=check, accept_unverified_read=True
        )
        assert result.operation.status == "succeeded" and result.verification.grant is None
        store.verify()


def test_initial_owner_with_no_authority_ack_cannot_infer_explicit_read_from_unpriced(journal):
    journal.plan = explicit_priced_plan(journal.plan, unpriced=True)
    record, proof = complete(journal, unknown=False)
    explicit = proof.model_copy(
        update={"grant": None, "authorization_policy": "explicit_read_attempt"}
    )
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        with pytest.raises(YorungeError) as error:
            repo.verified(
                record.operation_id, record.lease, explicit, authorization=read_check(journal)
            )
        assert error.value.code == "approval_required"
        assert repo.show(operation_id=record.operation_id).verification is None


def test_revoked_initial_approval_blocks_owner_but_not_new_explicit_read_takeover(journal):
    record, proof = complete(journal)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        repo.revoke(journal.plan.plan_id, journal.plan.digest)
        with pytest.raises(YorungeError) as error:
            repo.verified(
                record.operation_id, record.lease, proof, authorization=read_check(journal)
            )
        assert error.value.code == "approval_required"
    journal.clock.value += timedelta(seconds=151)
    with open_store(journal.root) as store:
        repo = StateUploads(store, journal.bound, clock=journal.clock)
        check = read_check(journal)
        lease = repo.acquire_read(
            record.operation_id, authorization=check, accept_unverified_read=True
        )
        proof = proof.model_copy(update={"observed_at": timestamp(journal.clock.value)})
        result = repo.verified(
            record.operation_id, lease, proof, authorization=check, accept_unverified_read=True
        )
        assert result.operation.status == "succeeded" and result.approval.status == "revoked"
        store.verify()


@pytest.mark.parametrize(
    "code,outcome,exit",
    [
        ("remote_access_denied", "denied", 3),
        ("remote_rate_limited", "unavailable", 1),
        ("remote_failed", "unavailable", 1),
        ("transport_timeout", "unavailable", 1),
        ("transport_failed", "unavailable", 1),
        ("invalid_response", "invalid", 1),
    ],
)
@pytest.mark.parametrize("actor", ["initial", "restart", "cleanup"])
def test_read_failure_code_actor_matrix_and_recovery_slot(journal, code, outcome, exit, actor):
    record = created(journal, unknown=True)
    if actor != "initial":
        journal.clock.value += timedelta(seconds=151)
    with open_store(journal.root) as store:
        repo = (
            journal.repository(store)
            if actor == "initial"
            else StateUploads(store, journal.bound, clock=journal.clock)
        )
        owner = record.lease if actor == "initial" else None
        if actor == "restart":
            owner = repo.acquire_read(
                record.operation_id, authorization=read_check(journal), accept_unverified_read=True
            )
        failed = read_check(journal, outcome=outcome, code=code)
        with pytest.raises(YorungeError) as error:
            repo.read_failed(record.operation_id, owner, failed)
        assert error.value.operation_id == record.operation_id
        assert error.value.code == ("operation_uncertain" if actor == "initial" else code)
        assert error.value.exit_code == (5 if actor == "initial" else exit)
        result = repo.show(operation_id=record.operation_id)
        assert (
            result.operation.status == "unknown" and result.operation.reason == "read_unavailable"
        )
        assert result.operation.lease is None and len(result.controls) == 1
        assert (
            result.controls[0].kind == "recovery" and result.controls[0].verification_digest is None
        )
        store.verify()


def test_partial_graph_with_all_existing_receipts_accepted_and_matching_metadata_stays_unknown(
    journal,
):
    record, proof = complete(journal, skip_last=True)
    with open_store(journal.root) as store:
        repo = journal.repository(store)
        with pytest.raises(YorungeError) as error:
            repo.verified(
                record.operation_id, record.lease, proof, authorization=read_check(journal)
            )
        assert error.value.code == "operation_uncertain"
        found = repo.show(operation_id=record.operation_id)
        assert len(found.intents) == 10 and all(r.result == "accepted" for r in found.receipts)
        assert found.operation.status == "unknown" and found.verification is None
        store.verify()


def test_terminal_read_calls_reject_before_clock_or_credential_mutation(journal):
    record, proof = complete(journal)
    check = read_check(journal)
    failed = read_check(journal, outcome="denied", code="remote_access_denied")
    with open_store(journal.root) as store:
        journal.repository(store).verified(
            record.operation_id, record.lease, proof, authorization=check
        )
        repo = StateUploads(store, clock=journal.clock)
        before = tuple(store.connection.iterdump())
        for invoke in (
            lambda: repo.acquire_read(record.operation_id),
            lambda: repo.renew(record.operation_id, record.lease),
            lambda: repo.cleanup_expired(record.operation_id),
            lambda: repo.verified(record.operation_id, record.lease, proof),
            lambda: repo.read_failed(record.operation_id, None, failed),
        ):
            with pytest.raises(YorungeError) as error:
                invoke()
            assert error.value.code == "operation_conflict"
            assert tuple(store.connection.iterdump()) == before


def test_local_unlatched_expired_cleanup_requires_no_credential_or_read_flag(journal):
    record = admit(journal, unknown=True)
    journal.clock.value += timedelta(seconds=151)
    with open_store(journal.root) as store:
        repo = StateUploads(store, clock=journal.clock)
        result = repo.cleanup_expired(record.operation_id)
        assert result.operation.status == "cancelled" and result.operation.reason == "lease_expired"
        assert result.intents == () and result.controls[0].kind == "terminal"
        assert repo.write_access is None
        store.verify()


@pytest.mark.parametrize("future", [False, True])
def test_explicit_read_after_reset_uses_new_scope_without_rewriting_history(journal, future):
    if future:
        shift = timedelta(days=366)
        journal.clock.value += shift
        body = journal.plan.model_dump(mode="json")
        from yorunge.domain.capabilities import instant

        for item in (body, body["grant"], body["cost_bound"]):
            for field in ("prepared_at", "checked_at", "expires_at"):
                if field in item:
                    item[field] = timestamp(instant(item[field]) + shift)
        journal.plan = seal(body)
    record, proof = complete(journal)
    if future:
        journal.clock.value -= shift
    preview = api.preview_identity_reset(state_dir=journal.root).data
    api.reset_identity(preview.digest, state_dir=journal.root)
    with open_store(journal.root) as store:
        identity = StateCredentialRegistry(store).observe(journal.bound.credential)
        stamp = StateCache(store, journal.clock).stamp()
        scope = journal.plan.scope.model_copy(
            update={
                "identity_epoch": stamp.identity_epoch,
                "clock_generation": stamp.generation,
                "credential_id": identity.credential_id,
                "credential_revision": identity.credential_revision,
            }
        )
        bound = BoundCredential(journal.bound.context, journal.bound.credential, identity)
        repo = StateUploads(store, bound, clock=journal.clock)
        before = repo.show(operation_id=record.operation_id)
        check = read_check(journal, scope=scope)
        lease = repo.acquire_read(
            record.operation_id, authorization=check, accept_unverified_read=True
        )
        proof = proof.model_copy(
            update={"scope": scope, "observed_at": timestamp(journal.clock.value)}
        )
        result = repo.verified(
            record.operation_id, lease, proof, authorization=check, accept_unverified_read=True
        )
        assert result.operation.status == "succeeded" and result.verification.scope == scope
        assert result.plan.encoded() == before.plan.encoded()
        assert result.operation.approval.encoded() == before.operation.approval.encoded()
        assert result.plan.scope.identity_epoch != result.verification.scope.identity_epoch
        assert result.plan.grant is None and result.verification.grant is None
        store.verify()
