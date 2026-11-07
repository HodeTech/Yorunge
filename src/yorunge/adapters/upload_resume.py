"""Private resume composition: the report of one source operation and the plan that continues it.

The journal of the source's lineage is read first. Only when it blocks nothing is the dataset read
as the provider lists it, and the two are reduced by the pure classifier into one report. Nothing
but reads is sent to the provider. The local writes are those of ``--prepare`` alone: the freeze of
the source (a running one whose lease lapsed becomes unknown) and the plan that is saved.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from yorunge.adapters.capability_cache import StateCache
from yorunge.adapters.platform_upload_reader import BaselineCheck, ObservedUploadReader
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_chain import ResumeSource
from yorunge.adapters.upload_http import UploadHttpxTransport
from yorunge.adapters.upload_input_files import UploadInputObservation, capture_upload_input
from yorunge.adapters.upload_preparation import UploadPreparationRuntime, _limits
from yorunge.adapters.upload_repository import StateUploads
from yorunge.application.continuation_policy import (
    ContinuationPreparation,
    continuation_binding,
    continuation_limits,
    prepare_continuation_v3,
)
from yorunge.application.http_transport import HttpCredential
from yorunge.application.upload_budget import UploadBudget
from yorunge.application.upload_inputs import require_distinct_upload_content
from yorunge.domain.capabilities import timestamp
from yorunge.domain.credentials import BoundCredential, SecretValue
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.dataset_upload import (
    MAX_TRANSFER_FILES,
    MAX_TRANSFER_OPERATIONS,
    MAX_TRANSFER_PAYLOAD_BYTES,
    MAX_TRANSFER_PLANS,
    UploadScope,
    manifest_reference,
)
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.state import canonical_uuid
from yorunge.domain.upload_costs import ContinuationCostWork, UploadExecutionWindow
from yorunge.domain.upload_resume import (
    BLOCKERS,
    Blocker,
    ChainSummary,
    Classification,
    ContinuationNotPossible,
    RemoteInventory,
    chain_blockers,
    classify,
    descendant_verdict,
    merge_chain,
    source_blockers,
)
from yorunge.domain.upload_resume_report import (
    DatasetUploadResumeReport,
    QuotaCounters,
    continuation_added_payload_bytes,
    resume_report,
)

# One read budget for the whole observation: the context and the dataset (each at most thirty
# seconds, as everywhere) and then the listing of its items.
OBSERVATION_SECONDS = 75.0
LISTING_SECONDS = 30.0
# The window a prepared plan may be approved and started in, as for an original plan.
PLAN_WINDOW_SECONDS = 900


def _ordered(blockers: set[Blocker]) -> tuple[Blocker, ...]:
    return tuple(blocker for blocker in BLOCKERS if blocker in blockers)


def _refuse(blockers: tuple[Blocker, ...], source_id: str, related: str | None) -> YorungeError:
    """What ``--prepare`` says of a report with blockers (the report itself is never an error)."""
    if "source_active" in blockers:
        return OperationError("operation_conflict", related or source_id)
    return ContinuationNotPossible(blockers, source_id)


class UploadResumeRuntime(UploadPreparationRuntime):
    """Report and prepare over the seams of the original prepare: state, clock and session."""

    def resume(
        self,
        operation_id: str,
        *,
        accept_unverified_read: bool,
        prepare: bool = False,
        accept_unconfirmed_effects: bool = False,
    ) -> DatasetUploadResumeReport:
        """The report of ``operation_id`` and, with ``prepare``, the plan that continues it.

        ``accept_unverified_read`` is the human's choice to read the dataset on an explicit
        attempt; it is asked for only when a read would be made. ``accept_unconfirmed_effects``
        belongs to ``prepare`` and to files whose confirm was sent without an answer.
        """
        valid = True
        try:
            canonical_uuid(operation_id)
        except (ValueError, TypeError, AttributeError):
            valid = False
        flags = (accept_unverified_read, prepare, accept_unconfirmed_effects)
        if not valid or any(type(flag) is not bool for flag in flags):
            raise YorungeError("invalid_request")
        if accept_unconfirmed_effects and not prepare:
            raise YorungeError("invalid_request")
        with self._invocation() as end:
            return self._resume(
                operation_id, accept_unverified_read, prepare, accept_unconfirmed_effects, end
            )

    def _read_source(self, operation_id: str) -> tuple[ResumeSource, QuotaCounters, str]:
        with open_existing_store(self.state_dir) as store:
            repository = StateUploads(store, clock=self.clock)
            stamp = StateCache(store, self.clock).stamp()
            source = repository.resume_source(operation_id, stamp)
            return source, repository.quota(), timestamp(stamp.now)

    def _resume(
        self,
        operation_id: str,
        accept_unverified_read: bool,
        prepare: bool,
        accept_unconfirmed_effects: bool,
        end: float,
    ) -> DatasetUploadResumeReport:
        source, used, now = self._read_source(operation_id)
        try:
            chain = merge_chain(source.chain.journals, source.manifest)
        except ValueError:
            raise YorungeError("state_invalid") from None
        verdict = descendant_verdict(source.chain.descendants)
        journal = _ordered({*source_blockers(source.chain.source, verdict), *chain_blockers(chain)})
        count = len(source.manifest.files)
        dataset_id = None if source.baseline is None else source.baseline.id
        if journal:
            # Nothing is read from the provider, and nothing local but the journal.
            report = resume_report(
                source_operation_id=operation_id,
                dataset_id=dataset_id,
                manifest=source.manifest,
                classification=None,
                blockers=journal,
                related_operation_id=verdict.related_operation_id,
                quota_used=used,
                added_payload_bytes=continuation_added_payload_bytes(count),
                observed_at=now,
            )
            if prepare:
                raise _refuse(journal, operation_id, verdict.related_operation_id)
            return report
        if not accept_unverified_read:
            raise YorungeError("approval_required")
        assert source.baseline is not None and source.baseline_digest is not None
        plan = source.plan
        if not isinstance(plan, DatasetUploadPlanV2 | DatasetContinuationPlanV3):
            raise YorungeError("state_invalid")
        return self._observed(
            operation_id, source, plan, chain, used, prepare, accept_unconfirmed_effects, end
        )

    def _check_scope(self, bound: BoundCredential, scope: UploadScope) -> None:
        """The credential and the clock are still those the scope was taken under (no name)."""
        with open_existing_store(self.state_dir) as store:
            StateUploads(store, bound, clock=self.clock).check_scope(scope)

    def _locally(
        self,
        plan: DatasetUploadPlanV2 | DatasetContinuationPlanV3,
        source: ResumeSource,
        secret: SecretValue,
        end: float,
    ) -> tuple[UploadInputObservation | None, YorungeError | None]:
        """The source folder and manifest as they are now, or why they are not what was planned."""
        try:
            observed = capture_upload_input(
                Path(plan.root.anchor), source.manifest, secret, end=end, expected_root=plan.root
            )
        except YorungeError as error:
            if error.code not in {"input_changed", "input_invalid"}:
                raise
            return None, error
        return observed, None

    def _read_remote(
        self,
        bound: BoundCredential,
        scope: UploadScope,
        source: ResumeSource,
        plan: DatasetUploadPlanV2 | DatasetContinuationPlanV3,
        end: float,
    ) -> tuple[BaselineCheck, RemoteInventory | None]:
        """The dataset as the provider shows it: observed, then listed when it is the baseline."""
        baseline = source.baseline
        assert baseline is not None
        credential = HttpCredential(
            "X-API-Key",
            bound.credential.secret,
            target=bound.credential.target,
            service_id="evren-platform",
        )
        budget = UploadBudget(
            _limits(source.manifest),
            end=min(end, time.monotonic() + OBSERVATION_SECONDS),
            read_only=True,
        )
        reader = ObservedUploadReader(scope, credential, budget, utc_clock=self.clock.now)

        async def observe(
            client: UploadHttpxTransport,
        ) -> tuple[BaselineCheck, RemoteInventory | None]:
            found = await reader.baseline(client, baseline, plan.parameters)
            # An access, rate or transport failure is the failure of the report, not a blocker.
            found.authorization.require_current(
                scope, "upload_created_dataset", baseline.id, timestamp(self.clock.now())
            )
            if not found.dataset_observed:
                return found, None
            deadline = min(budget.end, time.monotonic() + LISTING_SECONDS)
            return found, await reader.inventory(client, baseline.id, deadline=deadline)

        session = self._session(credential, budget)
        with session:
            return session.exchange(observe)

    def _observed(
        self,
        operation_id: str,
        source: ResumeSource,
        plan: DatasetUploadPlanV2 | DatasetContinuationPlanV3,
        chain: ChainSummary,
        used: QuotaCounters,
        prepare: bool,
        accept_unconfirmed_effects: bool,
        end: float,
    ) -> DatasetUploadResumeReport:
        baseline = source.baseline
        assert baseline is not None and source.baseline_digest is not None
        start = self.clock.now()
        bound, scope = self._bind(plan.scope.owner)
        inputs, changed = self._locally(plan, source, bound.credential.secret, end)
        if changed is not None and prepare:
            raise changed  # nothing is planned on a folder that is not the one that was uploaded
        found, inventory = self._read_remote(bound, scope, source, plan, end)
        observed_at = timestamp(self.clock.now())
        extra: set[Blocker] = set()
        if changed is not None:
            extra.add("local_changed")
        count = len(source.manifest.files)
        if inventory is None:
            # The dataset is not shown to be the baseline: nothing is listed, nothing is classified.
            extra.add("membership_unobserved")
            report = resume_report(
                source_operation_id=operation_id,
                dataset_id=baseline.id,
                manifest=source.manifest,
                classification=None,
                blockers=_ordered(extra),
                quota_used=used,
                added_payload_bytes=continuation_added_payload_bytes(count),
                observed_at=observed_at,
            )
            if prepare:
                raise _refuse(report.blockers, operation_id, None)
            return report
        classification = classify(source.manifest, chain, inventory).with_blockers(sorted(extra))
        selection = classification.selection()
        selected = None if selection is None else len(selection.file_indices)

        def reported(
            sealed: DatasetContinuationPlanV3 | None = None,
        ) -> DatasetUploadResumeReport:
            return resume_report(
                source_operation_id=operation_id,
                dataset_id=baseline.id,
                manifest=source.manifest,
                classification=classification,
                quota_used=used,
                added_payload_bytes=continuation_added_payload_bytes(
                    count, selected, None if sealed is None else len(sealed.encoded())
                ),
                observed_at=observed_at,
                plan=sealed,
            )

        if selection is None or not prepare:
            report = reported()
            if prepare:
                raise _refuse(report.blockers, operation_id, None)
            return report
        uncertain = bool(selection.uncertain_indices)
        if accept_unconfirmed_effects and not uncertain:
            raise YorungeError("invalid_request")
        if uncertain and not accept_unconfirmed_effects:
            raise YorungeError("approval_required")
        assert inputs is not None
        require_distinct_upload_content(inputs.manifest)
        sealed = self._seal(
            operation_id,
            source,
            plan,
            classification,
            selection.file_indices,
            inputs,
            scope,
            start,
            observed_at,
        )
        self._fits(used, count, selected, sealed)
        # The observation took a while: the credential and the clock must still be the scope's.
        self._check_scope(bound, scope)
        with open_existing_store(self.state_dir) as store:
            StateUploads(store, bound, clock=self.clock).freeze_source(operation_id)
        inputs.recheck()
        with open_existing_store(self.state_dir) as store:
            StateUploads(store, bound, clock=self.clock).save(sealed, inputs.manifest)
        return reported(sealed)

    def _seal(
        self,
        operation_id: str,
        source: ResumeSource,
        plan: DatasetUploadPlanV2 | DatasetContinuationPlanV3,
        classification: Classification,
        file_indices: tuple[int, ...],
        inputs: UploadInputObservation,
        scope: UploadScope,
        start: datetime,
        observed_at: str,
    ) -> DatasetContinuationPlanV3:
        """The plan of exactly this observation: the source's parameters, the current scope."""
        assert source.baseline is not None and source.baseline_digest is not None
        sealed: DatasetContinuationPlanV3 | None = None
        try:
            work = ContinuationCostWork(
                scope=scope,
                root=inputs.root,
                manifest=manifest_reference(inputs.manifest),
                parameters=plan.parameters,
                storage=plan.storage,
                request_limits=continuation_limits(inputs.manifest, file_indices),
                execution_window=UploadExecutionWindow(
                    not_before=timestamp(start),
                    not_after=timestamp(start + timedelta(seconds=PLAN_WINDOW_SECONDS)),
                ),
            )
            sealed = prepare_continuation_v3(
                ContinuationPreparation(
                    plan_id=str(uuid4()),
                    work=work,
                    manifest=inputs.manifest,
                    binding=continuation_binding(
                        classification,
                        source_operation_id=operation_id,
                        baseline_operation_id=source.baseline_operation_id,
                        dataset_id=source.baseline.id,
                        baseline_digest=source.baseline_digest,
                        intent_digest=source.intent_digest,
                        observed_at=observed_at,
                    ),
                    admission_policy=plan.admission_policy,
                    cost_policy=plan.cost_policy,
                    budget_micros=plan.budget_micros,
                    inputs_verified=True,
                    grant=None,
                    cost_bound=None,
                    prepared_at=timestamp(self.clock.now()),
                )
            )
        except ValueError:
            pass
        if sealed is None:
            # The longest plan the wire allows is 16 KiB: a source too close to it cannot continue.
            raise YorungeError("invalid_request")
        return sealed

    @staticmethod
    def _fits(
        used: QuotaCounters, count: int, selected: int | None, sealed: DatasetContinuationPlanV3
    ) -> None:
        """Refuse an attempt the store cannot hold before anything is frozen or written."""
        added = continuation_added_payload_bytes(count, selected, len(sealed.encoded()))
        if (
            used.plans + 1 > MAX_TRANSFER_PLANS
            or used.operations + 1 > MAX_TRANSFER_OPERATIONS
            or used.files + count > MAX_TRANSFER_FILES
            or used.payload_bytes + added > MAX_TRANSFER_PAYLOAD_BYTES
        ):
            raise YorungeError("upload_capacity_exceeded")
