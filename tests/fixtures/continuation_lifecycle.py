"""A real store with a registered credential and an interrupted root, to drive continuations.

The root is the partial v2 history of ``tests/fixtures/continuation_history.py`` re-addressed to a
credential that ``StateCredentialRegistry`` actually observed, so a repository holding that
credential accepts the plans built here. The clock is the ``execution_clock`` fixture, set after
the last event of the root. ``FixtureContinuations`` synthesizes the current-state proof that the
product's producer will later bring (``capture``); it is never a product producer.
"""

from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.fixtures.continuation_history import (
    BASE_PROOF,
    DATASET_ID,
    FILES,
    MANIFEST,
    Continuation,
    build,
    canon,
    install_root,
)
from yorunge.adapters.capability_cache import StateCache
from yorunge.adapters.identity import StateCredentialRegistry
from yorunge.adapters.state import open_store
from yorunge.adapters.upload_repository import StateUploads
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.credentials import (
    BoundCredential,
    EnvReference,
    ResolvedCredential,
    SecretValue,
    normalize_target,
)
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_transfer import StageReceipt
from yorunge.domain.dataset_transfer_v3 import TransferVerificationV3
from yorunge.domain.models import Context
from yorunge.domain.upload_checks import AuthorizationCheck, UploadCurrentCheck, UploadObservation

ACKNOWLEDGE_ALL = {
    "acknowledge_unverified_authority": True,
    "acknowledge_unpriced_cost": True,
    "acknowledge_unconfirmed_effects": True,
}


def first_action(plan):
    """What a continuation needs first: to upload, or (sending nothing) to read the dataset.

    Deliberately not the product's ``continuation_action``: the oracle must not share its code.
    """
    action = "upload_created_dataset" if plan.continuation.file_indices else "read_created_dataset"
    return action, plan.continuation.dataset_id


# The permission every stage of a continuation needs (it has no create and no link).
STAGE_ACTION = "upload_created_dataset"


class FixtureContinuations(StateUploads):
    """Synthetic proof capture for real repository tests; never a product producer."""

    def capture(self, fresh, action=None, dataset_id=None):
        if not isinstance(fresh, DatasetContinuationPlanV3):
            return fresh
        if action is None:
            action, dataset_id = first_action(fresh)
        now = timestamp(self.clock.value)
        allowed = fresh.grant is not None and action in fresh.grant.permissions
        authorization = AuthorizationCheck(
            consumer_profile="evren-platform-observed-upload-v2",
            policy_version=2,
            action=action,
            scope=fresh.scope,
            dataset_id=dataset_id,
            producer_id="fixture_only",
            producer_version="3",
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
            authorization=authorization,
            inputs_verified=fresh.inputs_verified,
            upload_observation=observation,
        )

    def approve_continuation(self, plan_id, digest, fresh, **kwargs):
        return super().approve_continuation(plan_id, digest, self.capture(fresh), **kwargs)

    def admit(self, plan_id, fresh):
        # An existing operation is found by the local lookup alone; no proof is built for it.
        if self.show(plan_id=plan_id).operation is not None:
            return super().admit(plan_id, fresh)
        return super().admit(plan_id, self.capture(fresh))

    def arm(self, operation_id, owner, fresh, kind, file_index, **kwargs):
        record = self.show(operation_id=operation_id).operation
        return super().arm(
            operation_id,
            owner,
            self.capture(fresh, STAGE_ACTION, record.dataset_id),
            kind,
            file_index,
            **kwargs,
        )


@dataclass
class Lifecycle:
    root_dir: Path
    bound: BoundCredential
    clock: object
    root: dict
    manifest: DatasetManifest
    access: object = None

    def repository(self, store):
        return FixtureContinuations(store, self.bound, clock=self.clock, write_access=self.access)

    def admitted(self, number=1, **spec):
        """Save, approve and admit a continuation; its repository keeps the write access."""
        plan = self.plan(number, **spec)
        with open_store(self.root_dir, timeout=60) as store:
            repository = self.repository(store)
            repository.save(plan, self.manifest)
            repository.approve_continuation(
                plan.plan_id,
                plan.digest,
                plan,
                acknowledge_unverified_authority=True,
                acknowledge_unpriced_cost=True,
                acknowledge_unconfirmed_effects=bool(plan.continuation.uncertain_indices),
            )
            record = repository.admit(plan.plan_id, plan)
            self.access = repository.write_access
        return plan, record

    def arm(self, plan, record, kind, index=None):
        with open_store(self.root_dir, timeout=60) as store:
            return self.repository(store).arm(
                record.operation_id,
                record.lease,
                plan,
                kind,
                index,
                total_end=self.clock.monotonic() + 900,
            )

    def accept(self, record, intent, *, rejected=False):
        """The receipt a provider answer would give for ``intent``."""
        with open_store(self.root_dir, timeout=60) as store:
            return self.repository(store).receipt(
                record.operation_id, record.lease, receipt_for(intent, self.clock, rejected)
            )

    def plan(self, number=1, **spec) -> DatasetContinuationPlanV3:
        """A sealed continuation plan of the root (or of ``source``), as the producer would save."""
        return plan_of(build(self.root, number, **spec))


def receipt_for(intent, clock, rejected=False) -> StageReceipt:
    file = FILES[intent.file_index]
    return StageReceipt(
        schema_version=1,
        intent_id=intent.intent_id,
        recorded_at=timestamp(clock.value),
        result="rejected" if rejected else "accepted",
        dataset_id=None if rejected else DATASET_ID,
        object_key=None if rejected else f"objects/{intent.file_index}",
        sent_bytes=file["size"] if not rejected and intent.kind == "put" else None,
        sent_sha256=file["sha256"] if not rejected and intent.kind == "put" else None,
    )


def read_check(plan, clock, *, error=None) -> AuthorizationCheck:
    """The current read authorization: not exposed by the provider, or a failed read."""
    return AuthorizationCheck(
        consumer_profile="evren-platform-observed-upload-v2",
        policy_version=2,
        action="read_created_dataset",
        scope=plan.scope,
        dataset_id=plan.continuation.dataset_id,
        producer_id="fixture_only",
        producer_version="3",
        checked_at=timestamp(clock.value),
        outcome="not_exposed" if error is None else "unavailable",
        grant=None,
        error_code=error,
    )


def proof_of(plan, observed_at) -> TransferVerificationV3:
    """What a closing read of the whole dataset observed (explicit attempt, no grant)."""
    return TransferVerificationV3.model_validate_json(
        canon(
            {
                **BASE_PROOF,
                "dataset_id": plan.continuation.dataset_id,
                "scope": plan.scope.model_dump(mode="json"),
                "observed_at": observed_at,
            }
        )
    )


def plan_of(item: Continuation) -> DatasetContinuationPlanV3:
    return DatasetContinuationPlanV3.model_validate_json(canon(item.plan))


@pytest.fixture
def lifecycle(tmp_path, execution_clock):
    clock = execution_clock
    clock.value = instant("2026-11-02T11:01:00.000000Z")  # after the root's last event
    root_dir = tmp_path / "state"
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
        SecretValue("synthetic-LIFECYCLE-key-DO-NOT-PUBLISH"),
    )
    with open_store(root_dir, timeout=60) as store:
        identity = StateCredentialRegistry(store).observe(credential)
        stamp = StateCache(store, clock).stamp()
        root = install_root(
            store,
            scope={
                "credential_id": identity.credential_id,
                "credential_revision": identity.credential_revision,
                "clock_generation": stamp.generation,
            },
        )
    manifest = DatasetManifest.model_validate_json(canon(MANIFEST))
    assert len(manifest.files) == len(FILES)
    return Lifecycle(
        root_dir, BoundCredential(context, credential, identity), clock, root, manifest
    )
