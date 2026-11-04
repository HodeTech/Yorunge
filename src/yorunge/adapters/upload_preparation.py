"""Private real prepare/approve composition; no HTTP effects or user proof injection."""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from yorunge.adapters.capability_cache import Clock, StateCache, SystemClock
from yorunge.adapters.identity import StateCredentialRegistry
from yorunge.adapters.platform_upload_reader import ObservedUploadReader
from yorunge.adapters.secrets import EnvSecretReader
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_http import UploadSession
from yorunge.adapters.upload_input_files import UploadInputObservation, capture_upload_input
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import VersionedTransferView, read_manifest
from yorunge.adapters.upload_sync import (
    require_upload_sync_context as require_upload_sync_context,
)
from yorunge.application.credentials import bind_credential, resolve_credential
from yorunge.application.http_transport import HttpCredential
from yorunge.application.response_json import check_response_secrets
from yorunge.application.upload_budget import UploadBudget
from yorunge.application.upload_inputs import require_distinct_upload_content, revalidate_input
from yorunge.application.upload_policy import UploadPreparationV2, prepare_upload_v2
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.credentials import BoundCredential, normalize_target
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_upload import (
    UploadOwner,
    UploadParameters,
    UploadScope,
    UploadStoragePolicy,
    manifest_reference,
    provider_uuid,
)
from yorunge.domain.dataset_upload_v2 import (
    AdmissionPolicy,
    CostPolicy,
    DatasetUploadApprovalV2,
    DatasetUploadPlanV2,
    require_acknowledgements,
    validate_policy_choice,
)
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Context, Profile
from yorunge.domain.upload_costs import UploadCostWork, UploadExecutionWindow, UploadRequestLimits

SessionFactory = Callable[[HttpCredential, UploadBudget], UploadSession]


def revoke_upload_approval(plan_id: str, state_dir: Path | None) -> VersionedTransferView:
    """Local use case requiring neither configuration nor service credentials."""
    require_upload_sync_context()
    with open_existing_store(state_dir) as store:
        repository = StateUploads(store)
        plan = repository.show(plan_id=plan_id).plan
        return repository.revoke(plan_id, plan.digest)


def _limits(manifest: DatasetManifest) -> UploadRequestLimits:
    return UploadRequestLimits(
        max_create=1,
        max_project_link=1,
        max_presign=manifest.file_count,
        max_put=manifest.file_count,
        max_confirm=manifest.file_count,
        max_read_requests=512,
        max_read_attempts=1024,
        max_control_request_bytes=4194304,
        max_control_response_bytes=16777216,
        max_upload_bytes=manifest.total_bytes,
    )


def _work(
    scope: UploadScope,
    inputs: UploadInputObservation,
    parameters: UploadParameters,
    storage: UploadStoragePolicy,
    start: datetime,
) -> UploadCostWork:
    work: UploadCostWork | None = None
    try:
        work = UploadCostWork(
            scope=scope,
            root=inputs.root,
            manifest=manifest_reference(inputs.manifest),
            parameters=parameters,
            storage=storage,
            request_limits=_limits(inputs.manifest),
            execution_window=UploadExecutionWindow(
                not_before=timestamp(start), not_after=timestamp(start + timedelta(seconds=900))
            ),
        )
    except ValueError:
        pass
    if work is None:
        raise YorungeError("invalid_request")
    return work


def _seal(request: UploadPreparationV2) -> DatasetUploadPlanV2:
    plan: DatasetUploadPlanV2 | None = None
    try:
        plan = prepare_upload_v2(request)
    except ValueError:
        pass
    if plan is None:
        raise YorungeError("invalid_request")
    return plan


def read_approval_input(
    plan_id: str,
    digest: str,
    authority: bool,
    unpriced: bool,
    state_dir: Path | None,
    clock: Clock,
) -> tuple[DatasetUploadPlanV2, DatasetManifest]:
    """Local approval gate, reusable before deferred config/credential resolution."""
    with open_existing_store(state_dir) as store:
        repository = StateUploads(store, clock=clock)
        view = repository.show(plan_id=plan_id)
        plan = view.plan
        if (
            not isinstance(plan, DatasetUploadPlanV2)
            or plan.status == "draft"
            or plan.digest != digest
            or not instant(plan.prepared_at) <= clock.now() < instant(plan.expires_at)
        ):
            raise YorungeError("upload_plan_not_valid")
        require_acknowledgements(plan, authority=authority, unpriced=unpriced)
        if view.approval is not None or view.operation is not None:
            raise YorungeError("operation_conflict")
        with repository.phase():
            manifest = read_manifest(store.connection, plan)
        require_distinct_upload_content(manifest)
        return plan, manifest


class UploadPreparationRuntime:
    """Outer composition only; its session/clock seams are private test dependencies."""

    def __init__(
        self,
        context: Context,
        profile: Profile,
        state_dir: Path | None,
        *,
        session_factory: SessionFactory = UploadSession,
        clock: Clock | None = None,
    ) -> None:
        require_upload_sync_context()
        self.context = revalidate_input(Context, context)
        self.profile = revalidate_input(Profile, profile)
        if state_dir is not None and not isinstance(state_dir, Path):
            raise YorungeError("invalid_request")
        self.state_dir, self._session = state_dir, session_factory
        self.clock = clock or SystemClock()
        self._pid, self._thread, self._busy = os.getpid(), threading.current_thread(), False

    @contextmanager
    def _invocation(self) -> Iterator[float]:
        require_upload_sync_context()
        if self._busy or self._pid != os.getpid() or self._thread is not threading.current_thread():
            raise YorungeError("invalid_request")
        self._busy = True
        try:
            yield time.monotonic() + 900.0
        finally:
            self._busy = False

    def _target(self) -> str:
        target = normalize_target(self.context.platform_url)
        if target != normalize_target(self.profile.platform_url):
            raise YorungeError("state_changed")
        if (target.service_origin, target.api_base_path) != ("https://api.ssyz.org.tr", "/api/v1"):
            raise YorungeError("unsupported_combination")
        project_id = self.context.project_id
        if project_id is None:
            raise YorungeError("invalid_request")
        valid = True
        try:
            provider_uuid(project_id)
        except ValueError:
            valid = False
        if not valid:
            raise YorungeError("invalid_request")
        return project_id

    def _bind(self, owner: UploadOwner) -> tuple[BoundCredential, UploadScope]:
        project_id = self._target()
        resolved = resolve_credential(self.profile, "evren-platform", EnvSecretReader())
        with open_existing_store(self.state_dir) as store:
            repository = StateUploads(store, clock=self.clock)
            with repository.phase():
                bound = bind_credential(self.context, resolved, StateCredentialRegistry(store))
                self._local_values(bound, self.context, owner)
                stamp = StateCache(store, self.clock).stamp()
                scope = UploadScope(
                    store_id=stamp.store_id,
                    identity_epoch=stamp.identity_epoch,
                    clock_generation=stamp.generation,
                    service_id="evren-platform",
                    service_origin=resolved.target.service_origin,
                    api_base_path=resolved.target.api_base_path,
                    profile=self.context.profile,
                    owner=owner,
                    project_id=project_id,
                    credential_id=bound.identity.credential_id,
                    credential_revision=bound.identity.credential_revision,
                )
            StateUploads(store, bound, clock=self.clock).check_scope(scope)
        return bound, scope

    def _scope(self, bound: BoundCredential, scope: UploadScope, name: str) -> None:
        with open_existing_store(self.state_dir) as store:
            StateUploads(store, bound, clock=self.clock).check_scope(scope, name=name)

    def _http(
        self, bound: BoundCredential, scope: UploadScope, limits: UploadRequestLimits, end: float
    ) -> tuple[UploadSession, ObservedUploadReader]:
        credential = HttpCredential(
            "X-API-Key",
            bound.credential.secret,
            target=bound.credential.target,
            service_id="evren-platform",
        )
        budget = UploadBudget(limits, end=min(end, time.monotonic() + 30), read_only=True)
        return self._session(credential, budget), ObservedUploadReader(
            scope, credential, budget, utc_clock=self.clock.now
        )

    @staticmethod
    def _local_values(
        bound: BoundCredential,
        *values: Context | UploadOwner | UploadParameters | UploadStoragePolicy,
    ) -> None:
        valid = True
        try:
            for value in values:
                check_response_secrets(value, (bound.credential.secret,))
        except YorungeError:
            valid = False
        if not valid:
            raise YorungeError("invalid_request")

    def prepare(
        self,
        root: Path,
        manifest: Path | DatasetManifest,
        *,
        owner: UploadOwner,
        parameters: UploadParameters,
        storage: UploadStoragePolicy,
        admission_policy: AdmissionPolicy = "verified_only",
        cost_policy: CostPolicy = "bounded_required",
        budget_micros: int | None,
    ) -> DatasetUploadPlanV2:
        with self._invocation() as end:
            owner = revalidate_input(UploadOwner, owner)
            parameters = revalidate_input(UploadParameters, parameters)
            storage = revalidate_input(UploadStoragePolicy, storage)
            validate_policy_choice(admission_policy, cost_policy, budget_micros)
            self._target()
            if storage.mode != "proxy":
                raise YorungeError("unsupported_combination")
            bound, scope = self._bind(owner)
            self._local_values(bound, parameters, storage)
            self._scope(bound, scope, parameters.name)
            inputs = capture_upload_input(root, manifest, bound.credential.secret, end=end)
            self._scope(bound, scope, parameters.name)
            require_distinct_upload_content(inputs.manifest)
            start = self.clock.now()
            work = _work(scope, inputs, parameters, storage, start)
            preparation = UploadPreparationV2(
                plan_id=str(uuid4()),
                work=work,
                manifest=inputs.manifest,
                admission_policy=admission_policy,
                cost_policy=cost_policy,
                budget_micros=budget_micros,
                inputs_verified=True,
                grant=None,
                cost_bound=None,
                prepared_at=timestamp(start),
            )
            _seal(preparation)  # Entire plan wire must fit before even readonly HTTP.
            session, reader = self._http(bound, scope, work.request_limits, end)
            with session:
                check = session.exchange(reader.preparation)
            check.require_current(
                scope, "create_private_dataset", None, timestamp(self.clock.now())
            )
            inputs.recheck()
            self._scope(bound, scope, parameters.name)
            prepared_at = timestamp(self.clock.now())
            check.require_current(scope, "create_private_dataset", None, prepared_at)
            if not (
                instant(work.execution_window.not_before)
                <= instant(prepared_at)
                < instant(work.execution_window.not_after)
            ):
                raise YorungeError("upload_plan_not_valid")
            plan = _seal(replace(preparation, prepared_at=prepared_at))
            with open_existing_store(self.state_dir) as store:
                StateUploads(store, bound, clock=self.clock).save(
                    plan, inputs.manifest, authorization=check
                )
            return plan

    def _approval_input(
        self, plan_id: str, digest: str, authority: bool, unpriced: bool
    ) -> tuple[DatasetUploadPlanV2, DatasetManifest]:
        return read_approval_input(plan_id, digest, authority, unpriced, self.state_dir, self.clock)

    def approve(
        self,
        plan_id: str,
        confirmed_digest: str,
        *,
        acknowledge_unverified_authority: bool = False,
        acknowledge_unpriced_cost: bool = False,
    ) -> DatasetUploadApprovalV2:
        with self._invocation() as end:
            plan, manifest = self._approval_input(
                plan_id,
                confirmed_digest,
                acknowledge_unverified_authority,
                acknowledge_unpriced_cost,
            )
            bound, scope = self._bind(plan.scope.owner)
            if scope != plan.scope:
                raise YorungeError("state_changed")
            self._local_values(bound, self.context, plan.parameters, plan.storage)
            self._scope(bound, scope, plan.parameters.name)
            inputs = capture_upload_input(
                Path(plan.root.anchor),
                manifest,
                bound.credential.secret,
                end=end,
                expected_root=plan.root,
            )
            self._scope(bound, scope, plan.parameters.name)
            session, reader = self._http(bound, scope, plan.request_limits, end)
            with session:
                check = session.exchange(
                    lambda client: reader.current(
                        client, plan, inputs, action="create_private_dataset"
                    )
                )
            inputs.recheck()
            with open_existing_store(self.state_dir) as store:
                return StateUploads(store, bound, clock=self.clock).approve(
                    plan_id,
                    confirmed_digest,
                    check,
                    acknowledge_unverified_authority=acknowledge_unverified_authority,
                    acknowledge_unpriced_cost=acknowledge_unpriced_cost,
                )

    def revoke(self, plan_id: str) -> VersionedTransferView:
        with self._invocation(), open_existing_store(self.state_dir) as store:
            repository = StateUploads(store, clock=self.clock)
            plan = repository.show(plan_id=plan_id).plan
            return repository.revoke(plan_id, plan.digest)

    def __repr__(self) -> str:
        return "<upload preparation runtime private>"
