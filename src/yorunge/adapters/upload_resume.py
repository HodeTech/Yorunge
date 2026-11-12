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

from yorunge.adapters.capability_cache import read_stamp
from yorunge.adapters.platform_upload_reader import (
    PHASE_SECONDS,
    BaselineCheck,
)
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_chain import ResumeSource, source_journal
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
from yorunge.application.response_json import check_response_secrets
from yorunge.application.upload_inputs import require_distinct_upload_content
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.credentials import BoundCredential, SecretValue
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.dataset_manifest import DatasetManifest
from yorunge.domain.dataset_transfer import scope_target
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
from yorunge.domain.platform_upload import ProviderDataset
from yorunge.domain.state import canonical_uuid
from yorunge.domain.upload_costs import ContinuationCostWork, UploadExecutionWindow
from yorunge.domain.upload_resume import (
    BLOCKERS,
    Blocker,
    ChainSummary,
    Classification,
    ContinuationNotPossible,
    RemoteInventory,
    classify,
)
from yorunge.domain.upload_resume_report import (
    DatasetUploadResumeReport,
    QuotaCounters,
    continuation_added_payload_bytes,
    resume_report,
)

# One read budget for the whole observation: the context and the dataset (one phase, at most thirty
# seconds, as everywhere) and then the listing of its items (at most thirty more).
LISTING_SECONDS = 30.0
OBSERVATION_SECONDS = PHASE_SECONDS + LISTING_SECONDS
# The window a prepared plan may be approved and started in, as for an original plan.
PLAN_WINDOW_SECONDS = 900
# What the folder can answer when it is not the one that was uploaded: moved or unreadable, changed,
# or grown past what the product accepts (too many files, too many bytes).
LOCAL_CHANGES = frozenset(
    {
        "input_changed",
        "input_invalid",
        "file_unreadable",
        "dataset_limit_exceeded",
        "input_budget_exceeded",
    }
)


def _keyless(manifest: DatasetManifest, secret: SecretValue) -> None:
    """No path a report may show is the key in use, whatever the state of the folder."""
    leaked = False
    try:
        check_response_secrets(manifest, (secret,))
    except YorungeError:
        leaked = True  # not chained: the error must not carry the paths
    if leaked:
        raise YorungeError("invalid_request")


def _ordered(blockers: set[Blocker]) -> tuple[Blocker, ...]:
    return tuple(blocker for blocker in BLOCKERS if blocker in blockers)


def _refuse(blockers: tuple[Blocker, ...], source_id: str, related: str | None) -> YorungeError:
    """What ``--prepare`` says of a report with blockers (the report itself is never an error)."""
    if "source_active" in blockers:
        return OperationError("operation_conflict", related or source_id)
    return ContinuationNotPossible(blockers, source_id)


def _answered(
    report: DatasetUploadResumeReport, prepare: bool, operation_id: str
) -> DatasetUploadResumeReport:
    """A report is the answer of a look; a prepare that has no plan to make is refused with it."""
    if prepare:
        raise _refuse(report.blockers, operation_id, None)
    return report


def _require_acknowledgement(uncertain: bool, accepted: bool) -> None:
    """A selection with files whose effect is unconfirmed needs the acknowledgement, and only it."""
    if accepted and not uncertain:
        raise YorungeError("invalid_request")
    if uncertain and not accepted:
        raise YorungeError("approval_required")


class UploadResumeRuntime(UploadPreparationRuntime):
    """Report and prepare over the seams of the original prepare: state, clock and session.

    Only the seams are inherited; ``prepare`` and ``approve`` of the original upload are not used.
    """

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

    def _read_source(self, operation_id: str) -> tuple[ResumeSource, str]:
        """The source as the journal holds it now. A read: the clock is looked at, never written.

        The journal-only report (a source the journal rules out) writes nothing, not even the
        clock: a durable stamp here would record the clock's high watermark and could move the
        generation that plans are compared with. The report that reads the provider binds the
        credential and takes its clock point like every Platform command (``prepare`` saves its
        plan in a transaction of its own).
        """
        with open_existing_store(self.state_dir) as store:
            stamp = read_stamp(store, self.clock)
            if stamp is None:
                raise YorungeError("state_invalid")
            source = StateUploads(store, clock=self.clock).resume_source(operation_id, stamp)
            return source, timestamp(stamp.now)

    def _resume(
        self,
        operation_id: str,
        accept_unverified_read: bool,
        prepare: bool,
        accept_unconfirmed_effects: bool,
        end: float,
    ) -> DatasetUploadResumeReport:
        source, now = self._read_source(operation_id)
        used = source.quota
        chain, journal, related = self._journal(source)
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
                related_operation_id=related,
                quota_used=used,
                added_payload_bytes=continuation_added_payload_bytes(count),
                observed_at=now,
            )
            if prepare:
                raise _refuse(journal, operation_id, related)
            return report
        if not accept_unverified_read:
            raise YorungeError("approval_required")
        plan = source.plan
        if not isinstance(plan, DatasetUploadPlanV2 | DatasetContinuationPlanV3):
            raise YorungeError("state_invalid")
        return self._observed(
            operation_id, source, plan, chain, used, prepare, accept_unconfirmed_effects, end
        )

    @staticmethod
    def _journal(source: ResumeSource) -> tuple[ChainSummary, tuple[Blocker, ...], str | None]:
        """What the journal alone says: the lineage, what rules the source out, the successor."""
        return source_journal(source)

    def _still_open(self, operation_id: str) -> None:
        """Nothing was admitted or begun on the source while the dataset was being read."""
        source, _ = self._read_source(operation_id)
        _, blockers, related = self._journal(source)
        if blockers:
            raise _refuse(blockers, operation_id, related)

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
            if error.code not in LOCAL_CHANGES:
                raise
            return None, error
        return observed, None

    def _read_remote(
        self,
        bound: BoundCredential,
        scope: UploadScope,
        baseline: ProviderDataset,
        plan: DatasetUploadPlanV2 | DatasetContinuationPlanV3,
        manifest: DatasetManifest,
        end: float,
    ) -> tuple[BaselineCheck, RemoteInventory | None]:
        """The dataset as the provider shows it: observed, then listed when it is the baseline."""
        session, reader = self._http(
            bound, scope, _limits(manifest), end, seconds=OBSERVATION_SECONDS
        )

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
            # The reader holds the listing within the observation budget as well.
            deadline = time.monotonic() + LISTING_SECONDS
            return found, await reader.inventory(client, baseline.id, deadline=deadline)

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
        bound, scope = self._bind(plan.scope.owner)
        if scope_target(scope) != scope_target(plan.scope):
            # The context names another project, owner or service than the source was uploaded
            # under: what a continuation would be planned on is not this dataset's project.
            raise YorungeError("state_changed")
        _keyless(source.manifest, bound.credential.secret)
        inputs, changed = self._locally(plan, source, bound.credential.secret, end)
        if changed is not None and prepare:
            raise changed  # nothing is planned on a folder that is not the one that was uploaded
        # The plan's window starts once the folder was hashed, as an original plan's does.
        start = self.clock.now()
        _, inventory = self._read_remote(bound, scope, baseline, plan, source.manifest, end)
        observed_at = timestamp(self.clock.now())
        extra: set[Blocker] = set()
        if changed is not None:
            extra.add("local_changed")
        count = len(source.manifest.files)
        if inventory is None:
            return self._unobserved(
                operation_id, source, baseline, used, extra, observed_at, prepare
            )
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
            return _answered(reported(), prepare, operation_id)
        _require_acknowledgement(bool(selection.uncertain_indices), accept_unconfirmed_effects)
        assert inputs is not None
        sealed = self._prepared(
            operation_id,
            source,
            plan,
            classification,
            selection.file_indices,
            inputs,
            bound,
            scope,
            start,
            observed_at,
            used,
            selected,
        )
        return reported(sealed)

    def _unobserved(
        self,
        operation_id: str,
        source: ResumeSource,
        baseline: ProviderDataset,
        used: QuotaCounters,
        extra: set[Blocker],
        observed_at: str,
        prepare: bool,
    ) -> DatasetUploadResumeReport:
        """The dataset is not shown to be the baseline: nothing is listed, nothing is classified."""
        extra.add("membership_unobserved")
        report = resume_report(
            source_operation_id=operation_id,
            dataset_id=baseline.id,
            manifest=source.manifest,
            classification=None,
            blockers=_ordered(extra),
            quota_used=used,
            added_payload_bytes=continuation_added_payload_bytes(len(source.manifest.files)),
            observed_at=observed_at,
        )
        return _answered(report, prepare, operation_id)

    def _prepared(
        self,
        operation_id: str,
        source: ResumeSource,
        plan: DatasetUploadPlanV2 | DatasetContinuationPlanV3,
        classification: Classification,
        file_indices: tuple[int, ...],
        inputs: UploadInputObservation,
        bound: BoundCredential,
        scope: UploadScope,
        start: datetime,
        observed_at: str,
        used: QuotaCounters,
        selected: int | None,
    ) -> DatasetContinuationPlanV3:
        """Seal the plan of this observation, check nothing moved, freeze the source, save."""
        require_distinct_upload_content(inputs.manifest)
        sealed = self._seal(
            operation_id,
            source,
            plan,
            classification,
            file_indices,
            inputs,
            scope,
            start,
            observed_at,
        )
        self._fits(used, len(source.manifest.files), selected, sealed)
        # The observation took a while: the credential and the clock must still be the scope's, the
        # plan inside its window, the folder what it was, and nothing begun on the source. A prepare
        # refused for any of it freezes nothing; one that fails after the freeze leaves it frozen.
        self._check_scope(bound, scope)
        if self.clock.now() >= instant(sealed.expires_at):
            raise YorungeError("upload_plan_not_valid")
        inputs.recheck()
        self._still_open(operation_id)
        with open_existing_store(self.state_dir) as store:
            StateUploads(store, bound, clock=self.clock).freeze_source(operation_id)
        inputs.recheck()
        with open_existing_store(self.state_dir) as store:
            StateUploads(store, bound, clock=self.clock).save(sealed, inputs.manifest)
        return sealed

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
        prepared = self.clock.now()
        window_end = start + timedelta(seconds=PLAN_WINDOW_SECONDS)
        if not max(start, instant(observed_at)) <= prepared < window_end:
            # The clock moved (back, or far ahead) while the folder and the dataset were read.
            raise YorungeError("upload_plan_not_valid")
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
                    not_after=timestamp(window_end),
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
                    prepared_at=timestamp(prepared),
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
