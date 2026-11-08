"""``resume --prepare`` over a real interrupted upload: the plan it saves and what it refuses.

Like the report tests, the source is made by the product itself. A source SIGKILLed while it ran is
the one a freeze is for: its lease has to lapse (a clock a little ahead of the real one) before it
is found frozen. A prepare refused for what it finds refuses before it freezes or writes; one
that fails after the freeze (the folder changed again, the store refused the plan) leaves the
source frozen.
"""

import multiprocessing
import os
import shutil
import signal
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import yorunge.adapters.upload_resume as resume_module
from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.continuation_lifecycle import FixtureContinuations
from tests.fixtures.http_server import Reply, TlsServer
from tests.fixtures.upload_provider import DATASET, UploadProvider
from tests.integration.test_upload_file_workflow import many
from tests.integration.test_upload_http_budget import SECRET
from tests.integration.test_upload_original import approved
from tests.integration.test_upload_preparation import ENV
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_resume_observation import (
    READS,
    interrupted,
    item,
    lose_confirm_of,
    reported,
    resume_runtime,
    rows,
    world,
)
from tests.integration.test_upload_resume_observation import (
    certificates as certificates,
)
from tests.integration.test_upload_resume_observation import (
    loopback_only as loopback_only,
)
from tests.integration.test_upload_workflow_kill import _child, _files, _settle
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_resume import UploadResumeRuntime
from yorunge.adapters.upload_store import read_any_view, read_manifest, validate_uploads
from yorunge.domain import dataset_manifest as limits
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.dataset_transfer import StageReceipt
from yorunge.domain.dataset_upload import TRANSFER_LEASE_SECONDS
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.upload_resume import ContinuationNotPossible


class Later:
    """A clock a little ahead of the real one: leases taken a moment ago have lapsed."""

    def __init__(self, seconds=TRANSFER_LEASE_SECONDS + 1):
        self.seconds = seconds

    def now(self):
        return datetime.now(UTC) + timedelta(seconds=self.seconds)

    def monotonic(self):
        return time.monotonic() + self.seconds

    @property
    def value(self):  # what the lifecycle fixtures ask a clock for
        return self.now()


def killed_while_running(data, server, provider, certificates, monkeypatch):
    """The original upload SIGKILLed right after the first confirm intent became durable."""
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    plan = approved(data, server)
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe()
    process = context.Process(
        target=_child,
        args=(
            str(data[0]),
            plan.plan_id,
            data[3].model_dump(mode="json"),
            data[4].model_dump(mode="json"),
            server.port,
            str(certificates[0]),
            "confirm_intent",
            child,
        ),
    )
    process.start()
    child.close()
    try:
        assert parent.poll(20), "the upload did not reach the boundary"
        assert parent.recv() == "paused"
        os.kill(process.pid, signal.SIGKILL)
        process.join(5)
    finally:
        if process.is_alive():
            process.kill()
            process.join(5)
        parent.close()
    _settle(server, provider)
    with open_existing_store(data[0]) as store:
        return StateUploads(store).show(plan_id=plan.plan_id).operation.operation_id


def prepared(data, server, source, **flags):
    return resume_runtime(data, server).resume(
        source, accept_unverified_read=True, prepare=True, **flags
    )


def saved(data, plan_id):
    with open_existing_store(data[0]) as store:
        return StateUploads(store).show(plan_id=plan_id)


def refused(data, server, source, code, **flags):
    stored = rows(data[0])
    with pytest.raises(YorungeError) as error:
        prepared(data, server, source, **flags)
    assert error.value.code == code
    assert rows(data[0]) == stored  # nothing was frozen or saved
    return error.value


# --- the plan -----------------------------------------------------------------------------------


def test_prepare_saves_the_plan_the_report_describes(prepared_input, certificates):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        described = reported(data, server, source)
        before = len(server.requests)
        report = prepared(data, server, source)
        assert report.eligible
        assert report.plan_id is not None
        # The report and the prepare that follows it observe the same: one computation.
        assert report.observation == described.observation
        assert (report.blockers, report.quota_used) == (described.blockers, described.quota_used)
        view = saved(data, report.plan_id)
        plan = view.plan
        assert isinstance(plan, DatasetContinuationPlanV3)
        assert plan.digest == report.plan_digest
        binding = plan.continuation
        assert (binding.source_operation_id, binding.baseline_operation_id) == (source, source)
        assert (binding.dataset_id, binding.file_indices, binding.uncertain_indices) == (
            DATASET,
            (2,),
            (),
        )
        assert binding.remote_present_count == 2
        assert binding.observed_at == report.observed_at
        assert plan.request_limits.files == 1
        assert plan.status == "attempt_ready"
        assert plan.request_limits.max_upload_bytes == len(b"different")
        assert (plan.admission_policy, plan.cost_policy) == (
            "explicit_attempt",
            "unpriced_accepted",
        )
        assert plan.grant is None
        assert plan.cost_bound is None
        assert plan.inputs_verified
        assert view.operation is None
        assert view.approval is None  # nothing is admitted or approved
        assert all(r.method == "GET" for r in server.requests[before:])
        with open_existing_store(data[0]) as store:
            validate_uploads(store.connection)
        # What the attempt will add is stated with the plan it was prepared as.
        assert report.quota_added.plans == report.quota_added.operations == 1


def test_a_check_only_continuation_is_prepared_when_nothing_is_left_to_send(
    prepared_input, certificates
):
    data = _files(prepared_input, 2)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    lose_confirm_of(provider, "two.bin")  # sent, kept by the provider, never answered
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        report = prepared(data, server, source)
        plan = saved(data, report.plan_id).plan
        assert plan.continuation.file_indices == ()
        assert plan.request_limits.files == 0
        assert plan.request_limits.max_upload_bytes == 0
        assert plan.continuation.remote_present_count == 2
        assert report.observation.send_files == 0
        assert report.observation.send_bytes == 0


def test_the_plan_is_taken_under_the_credential_of_today(prepared_input, certificates, monkeypatch):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        with open_existing_store(data[0]) as store:
            first = StateUploads(store).show(operation_id=source).plan.scope.credential_revision
        monkeypatch.setenv(ENV, "a-key-that-was-rotated-in-the-meantime")
        report = prepared(data, server, source)
        plan = saved(data, report.plan_id).plan
        assert plan.scope.credential_revision == first + 1  # the source's own scope is not reused


def test_a_source_that_is_frozen_already_is_not_touched_and_the_plan_holds_no_secret(
    prepared_input, certificates
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        with open_existing_store(data[0]) as store:
            before = StateUploads(store).show(operation_id=source).operation
        report = prepared(data, server, source)
        with open_existing_store(data[0]) as store:
            assert StateUploads(store).show(operation_id=source).operation == before
        plan = saved(data, report.plan_id).plan
        assert SECRET not in plan.encoded().decode()
        # The plan may be approved and started for a quarter of an hour from the moment the folder
        # was hashed; the dataset was observed after that and before the plan was sealed.
        window = plan.execution_window
        not_before, not_after = instant(window.not_before), instant(window.not_after)
        assert not_after - not_before == timedelta(seconds=900)
        assert plan.expires_at == window.not_after
        observed_at, prepared_at = instant(plan.continuation.observed_at), instant(plan.prepared_at)
        assert not_before < observed_at <= prepared_at < not_after


def test_a_plan_the_wire_cannot_carry_is_an_invalid_request_and_nothing_is_written(
    prepared_input, certificates, monkeypatch
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)

        def too_long(request):
            raise ValueError("the plan exceeds its wire limit")

        monkeypatch.setattr("yorunge.adapters.upload_resume.prepare_continuation_v3", too_long)
        refused(data, server, source, "invalid_request")


# --- what it must be told, and refuses before it writes -------------------------------------------


def test_unconfirmed_effects_must_be_acknowledged_before_anything_is_written(
    prepared_input, certificates
):
    data = many(prepared_input)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    lose_confirm_of(
        provider, "two.bin", remembered=False
    )  # a confirm that may or may not have landed
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        refused(data, server, source, "approval_required")
        report = prepared(data, server, source, accept_unconfirmed_effects=True)
        plan = saved(data, report.plan_id).plan
        assert plan.continuation.uncertain_indices == (1,)
        assert plan.continuation.file_indices == (
            1,
            2,
        )
        # It asks the provider for exactly the two files it will send, and for their bytes.
        sent = sum((data[1] / name).stat().st_size for name in ("two.bin", "ölçüm.bin"))
        assert (plan.request_limits.files, plan.request_limits.max_upload_bytes) == (2, sent)


def test_an_acknowledgement_nothing_needs_is_refused(prepared_input, certificates):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        refused(data, server, source, "invalid_request", accept_unconfirmed_effects=True)


def test_the_unverified_read_must_be_chosen_to_prepare(prepared_input, certificates):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        before, stored = len(server.requests), rows(data[0])
        with pytest.raises(YorungeError) as error:
            resume_runtime(data, server).resume(source, accept_unverified_read=False, prepare=True)
        assert error.value.code == "approval_required"
        assert len(server.requests) == before
        assert rows(data[0]) == stored


PROBLEMS = {
    "a confirmed file the provider no longer has": (
        lambda provider: provider.confirmed.pop("one.bin"),
        ("drift_missing",),
    ),
    "an item the manifest does not list": (
        lambda provider: provider.confirmed.update({"stray.bin": item("stray.bin")}),
        ("extra_remote",),
    ),
}


@pytest.mark.parametrize("problem", PROBLEMS.values(), ids=PROBLEMS)
def test_a_remote_state_that_blocks_is_not_possible_and_names_each_blocker(
    prepared_input, certificates, problem
):
    change, blockers = problem
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        change(provider)
        error = refused(data, server, source, "continuation_not_possible")
        assert isinstance(error, ContinuationNotPossible)
        assert error.blockers == blockers
        assert error.operation_id == source


def test_a_dataset_the_project_does_not_list_is_not_possible(prepared_input, certificates):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        provider.linked = False
        error = refused(data, server, source, "continuation_not_possible")
        assert error.blockers == ("membership_unobserved",)


def test_a_folder_that_changed_stops_prepare_before_the_provider_is_asked(
    prepared_input, certificates
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        (data[1] / "one.bin").write_bytes(b"changed after the interruption")
        before = len(server.requests)
        refused(data, server, source, "input_changed")
        assert len(server.requests) == before


def test_a_store_that_cannot_hold_the_attempt_refuses_it_before_it_freezes_anything(
    prepared_input, certificates, monkeypatch
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        monkeypatch.setattr("yorunge.adapters.upload_resume.MAX_TRANSFER_PLANS", 1)
        refused(data, server, source, "upload_capacity_exceeded")
        # The report is no error: it states what is used and what the attempt would add.
        report = resume_runtime(data, server).resume(source, accept_unverified_read=True)
        assert report.quota_used.plans == 1
        assert report.quota_added.plans == 1


# --- the freeze ---------------------------------------------------------------------------------


def test_prepare_freezes_a_source_that_was_killed_while_running(
    prepared_input, certificates, monkeypatch
):
    data = _files(prepared_input, 3)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        source = killed_while_running(data, server, provider, certificates, monkeypatch)
        with open_existing_store(data[0]) as store:
            record = StateUploads(store).show(operation_id=source).operation
        assert record.status == "running"
        later = resume_runtime(data, server, clock=Later())
        # The report finds it free and leaves it as it is.
        stored = rows(data[0])
        report = later.resume(source, accept_unverified_read=True)
        assert report.eligible
        assert rows(data[0]) == stored
        # The confirm that was about to be sent never was: it may be sent now, so it is uncertain.
        assert report.observation.unconfirmed_ack_required
        with pytest.raises(YorungeError) as error:
            later.resume(source, accept_unverified_read=True, prepare=True)
        assert error.value.code == "approval_required"
        assert rows(data[0]) == stored
        done = later.resume(
            source,
            accept_unverified_read=True,
            prepare=True,
            accept_unconfirmed_effects=True,
        )
        with open_existing_store(data[0]) as store:
            frozen = StateUploads(store).show(operation_id=source).operation
        assert (frozen.status, frozen.reason, frozen.lease) == (
            "unknown",
            "request_uncertain",
            None,
        )
        assert frozen.fence == record.fence + 1
        assert done.plan_id is not None


@pytest.mark.parametrize("read", ["me", "owned", "detail", "role", "items"])
def test_a_provider_that_fails_during_prepare_leaves_a_running_source_unfrozen(
    prepared_input, certificates, monkeypatch, read
):
    data = _files(prepared_input, 3)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        source = killed_while_running(data, server, provider, certificates, monkeypatch)
        provider.route_table[READS[read]] = Reply(status=500, body=b"{}")
        stored = rows(data[0])
        with pytest.raises(YorungeError) as error:
            resume_runtime(data, server, clock=Later()).resume(
                source, accept_unverified_read=True, prepare=True, accept_unconfirmed_effects=True
            )
        assert error.value.code == "remote_failed"
        assert rows(data[0]) == stored  # nothing was frozen or saved
        with open_existing_store(data[0]) as store:
            assert StateUploads(store).show(operation_id=source).operation.status == "running"


# Each bound is set where what is used still fits and the attempt added to it does not.
CAPACITIES = {
    "plans": ("MAX_TRANSFER_PLANS", lambda report: report.quota_used.plans),
    "operations": ("MAX_TRANSFER_OPERATIONS", lambda report: report.quota_used.operations),
    "files": ("MAX_TRANSFER_FILES", lambda report: report.quota_used.files + 2),
    "payload": ("MAX_TRANSFER_PAYLOAD_BYTES", lambda report: report.quota_used.payload_bytes + 1),
}


@pytest.mark.parametrize("limit", CAPACITIES.values(), ids=CAPACITIES)
def test_each_bound_of_the_store_refuses_an_attempt_before_a_source_is_frozen(
    prepared_input, certificates, monkeypatch, limit
):
    name, bound = limit
    data = _files(prepared_input, 3)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        source = killed_while_running(data, server, provider, certificates, monkeypatch)
        report = resume_runtime(data, server, clock=Later()).resume(
            source, accept_unverified_read=True
        )
        monkeypatch.setattr(f"yorunge.adapters.upload_resume.{name}", bound(report))
        stored = rows(data[0])
        with pytest.raises(YorungeError) as error:
            resume_runtime(data, server, clock=Later()).resume(
                source,
                accept_unverified_read=True,
                prepare=True,
                accept_unconfirmed_effects=True,
            )
        assert error.value.code == "upload_capacity_exceeded"
        assert rows(data[0]) == stored  # the source is still the running one it was


def test_content_that_cannot_be_uploaded_stops_prepare_before_it_freezes_anything(
    prepared_input, certificates, monkeypatch
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)

        def duplicated(manifest):
            raise YorungeError("upload_duplicate_content")

        monkeypatch.setattr(
            "yorunge.adapters.upload_resume.require_distinct_upload_content", duplicated
        )
        refused(data, server, source, "upload_duplicate_content")


def test_a_folder_that_changes_just_before_the_freeze_is_not_planned_and_freezes_nothing(
    prepared_input, certificates, monkeypatch
):
    data = _files(prepared_input, 3)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        source = killed_while_running(data, server, provider, certificates, monkeypatch)
        original = UploadResumeRuntime._check_scope

        def check_and_change(runtime, bound, scope):
            original(runtime, bound, scope)  # the last look before the freeze ...
            (data[1] / "one.bin").write_bytes(b"changed right after it")

        monkeypatch.setattr(UploadResumeRuntime, "_check_scope", check_and_change)
        stored = rows(data[0])
        with pytest.raises(YorungeError) as error:
            resume_runtime(data, server, clock=Later()).resume(
                source, accept_unverified_read=True, prepare=True, accept_unconfirmed_effects=True
            )
        assert error.value.code == "input_changed"
        assert rows(data[0]) == stored  # ... so the source is still the running one it was


def test_a_folder_that_changes_after_the_freeze_leaves_the_source_frozen_and_saves_no_plan(
    prepared_input, certificates, monkeypatch
):
    data = _files(prepared_input, 3)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        source = killed_while_running(data, server, provider, certificates, monkeypatch)
        original = StateUploads.freeze_source

        def freeze_and_change(repository, operation_id):
            found = original(repository, operation_id)
            (data[1] / "one.bin").write_bytes(b"changed once the source was frozen")
            return found

        monkeypatch.setattr(StateUploads, "freeze_source", freeze_and_change)
        with open_existing_store(data[0]) as store:
            plans = store.connection.execute("SELECT count(*) FROM upload_plans").fetchone()[0]
        with pytest.raises(YorungeError) as error:
            resume_runtime(data, server, clock=Later()).resume(
                source, accept_unverified_read=True, prepare=True, accept_unconfirmed_effects=True
            )
        assert error.value.code == "input_changed"
        with open_existing_store(data[0]) as store:
            frozen = StateUploads(store).show(operation_id=source).operation
            assert (frozen.status, frozen.reason) == ("unknown", "request_uncertain")
            assert (
                store.connection.execute("SELECT count(*) FROM upload_plans").fetchone()[0] == plans
            )


def test_a_credential_rotated_during_the_observation_stops_prepare_before_the_freeze(
    prepared_input, certificates, monkeypatch
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        frozen = []
        original = StateUploads.freeze_source
        monkeypatch.setattr(
            StateUploads,
            "freeze_source",
            lambda repository, operation_id: (
                frozen.append(operation_id) or original(repository, operation_id)
            ),
        )

        def rotate():
            if server.requests and server.requests[-1].path.endswith("/items?limit=128"):
                monkeypatch.setenv(ENV, "a-key-that-was-rotated-during-the-observation")
                state, _, _, context, profile = data
                UploadResumeRuntime(context, profile, state)._bind(SCOPE.owner)

        provider.on_request = rotate
        stored = rows(data[0])
        # The new key is registered once the listing was asked for; the plan is for the old one.
        with pytest.raises(YorungeError) as error:
            prepared(data, server, source)
        assert error.value.code == "state_changed"
        assert not frozen
        assert rows(data[0]) == stored


# --- a context that is not the source's, a slow hash, a second hop, two prepares at once ---------


def test_a_context_of_another_project_is_not_the_source_s_and_nothing_is_asked(
    prepared_input, certificates
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        state, folder, manifest, context, profile = data
        elsewhere = (
            state,
            folder,
            manifest,
            context.model_copy(update={"project_id": "00000000-0000-4000-8000-0000000000aa"}),
            profile,
        )
        before, stored = len(server.requests), rows(state)
        for prepare in (False, True):
            with pytest.raises(YorungeError) as error:
                resume_runtime(elsewhere, server).resume(
                    source, accept_unverified_read=True, prepare=prepare
                )
            assert error.value.code == "state_changed"  # the report and prepare say the same
        assert len(server.requests) == before
        assert rows(state) == stored


def test_the_plan_window_begins_once_the_folder_was_hashed(
    prepared_input, certificates, monkeypatch
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        clock = Later(0)
        hashed = []

        def slow(*arguments, **keywords):
            found = original(*arguments, **keywords)
            hashed.append(instant(timestamp(clock.now())))
            clock.seconds += 600
            return found

        original = resume_module.capture_upload_input  # the slow part: ten minutes here
        monkeypatch.setattr(resume_module, "capture_upload_input", slow)
        report = resume_runtime(data, server, clock=clock).resume(
            source, accept_unverified_read=True, prepare=True
        )
        plan = saved(data, report.plan_id).plan
        assert instant(plan.execution_window.not_before) >= hashed[0] + timedelta(seconds=600)
        assert instant(plan.expires_at) - instant(plan.prepared_at) > timedelta(seconds=850)


def test_the_plan_of_a_second_hop_extends_the_root_and_passes_the_next_gates(
    prepared_input, certificates
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        root = interrupted(data, server)
        runtime = resume_runtime(data, server)
        first = saved(data, runtime.resume(root, accept_unverified_read=True, prepare=True).plan_id)
        plan = first.plan
        bound, _ = runtime._bind(plan.scope.owner)
        now = Later(0)
        with open_existing_store(data[0]) as store:
            repository = FixtureContinuations(store, bound, clock=now)
            repository.approve_continuation(
                plan.plan_id,
                plan.digest,
                plan,
                acknowledge_unverified_authority=True,
                acknowledge_unpriced_cost=True,
            )
            record = repository.admit(plan.plan_id, plan)
            manifest = read_manifest(store.connection, plan)
            for kind in ("presign", "put"):  # the continuation sends the third file, then stops
                repository.arm(
                    record.operation_id,
                    record.lease,
                    plan,
                    kind,
                    2,
                    total_end=time.monotonic() + 900,
                )
                intent = read_any_view(store.connection, plan.plan_id).intents[-1]
                sent = manifest.files[2]
                repository.receipt(
                    record.operation_id,
                    record.lease,
                    StageReceipt(
                        schema_version=1,
                        intent_id=intent.intent_id,
                        recorded_at=timestamp(now.now()),
                        result="accepted",
                        dataset_id=plan.continuation.dataset_id,
                        object_key="objects/2",
                        sent_bytes=sent.size if kind == "put" else None,
                        sent_sha256=sent.sha256 if kind == "put" else None,
                    ),
                )
        continuation = record.operation_id
        later = resume_runtime(data, server, clock=Later())
        report = later.resume(continuation, accept_unverified_read=True)
        assert report.eligible
        assert report.observation.class_counts.pending_clean == 1
        made = later.resume(continuation, accept_unverified_read=True, prepare=True)
        second = saved(data, made.plan_id).plan
        binding, base = second.continuation, plan.continuation
        # The source is the continuation; the baseline is still what the root made.
        assert binding.source_operation_id == continuation
        assert binding.baseline_operation_id == root
        assert (binding.baseline_digest, binding.intent_digest) == (
            base.baseline_digest,
            base.intent_digest,
        )
        assert binding.file_indices == (2,)
        assert binding.remote_present_count == 2
        with open_existing_store(data[0]) as store:
            frozen = StateUploads(store).show(operation_id=continuation).operation
            assert (frozen.status, frozen.reason) == ("unknown", "request_uncertain")
            gates = FixtureContinuations(store, bound, clock=Later())
            gates.approve_continuation(
                second.plan_id,
                second.digest,
                second,
                acknowledge_unverified_authority=True,
                acknowledge_unpriced_cost=True,
            )
            assert gates.admit(second.plan_id, second).status == "admitted"
            validate_uploads(store.connection)


def test_two_prepares_at_once_freeze_a_source_once_and_each_save_a_plan(
    prepared_input, certificates, monkeypatch
):
    data = _files(prepared_input, 3)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        source = killed_while_running(data, server, provider, certificates, monkeypatch)
        with open_existing_store(data[0]) as store:
            before = StateUploads(store).show(operation_id=source).operation

        def prepare(_):
            return resume_runtime(data, server, clock=Later()).resume(
                source, accept_unverified_read=True, prepare=True, accept_unconfirmed_effects=True
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = pool.map(prepare, range(2))
        assert first.plan_id != second.plan_id
        with open_existing_store(data[0]) as store:
            frozen = StateUploads(store).show(operation_id=source).operation
            assert (frozen.status, frozen.fence) == ("unknown", before.fence + 1)  # frozen once
            validate_uploads(store.connection)


# --- the folder and the clock, as they are found ------------------------------------------------


def test_a_folder_replaced_by_an_identical_copy_is_a_changed_folder(prepared_input, certificates):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        folder = data[1]
        copy = folder.with_name("copy-of-the-source")
        shutil.copytree(folder, copy)
        shutil.rmtree(folder)
        copy.rename(folder)  # the same path and bytes, but not the folder that was planned
        assert "local_changed" in reported(data, server, source).blockers
        refused(data, server, source, "input_changed")


def test_a_symlink_in_the_folder_is_a_changed_folder_not_an_error_of_the_report(
    prepared_input, certificates
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        (data[1] / "one.bin").unlink()
        (data[1] / "one.bin").symlink_to(data[1] / "two.bin")
        assert "local_changed" in reported(data, server, source).blockers
        refused(data, server, source, "input_invalid")


class Stepping:
    """The real clock whose wall time can be stepped; the monotonic clock never steps."""

    def __init__(self):
        self.offset = 0.0

    def now(self):
        return datetime.now(UTC) + timedelta(seconds=self.offset)

    def monotonic(self):
        return time.monotonic()

    @property
    def value(self):
        return self.now()


def step_after_the_listing(server, provider, clock, seconds):
    """Step the clock once the provider has been asked for the items: while nothing is sealed."""
    listing = f"/api/v1/datasets/{DATASET}/items?limit=128"

    def step():
        if server.requests and server.requests[-1].path == listing:
            clock.offset = seconds

    provider.on_request = step


@pytest.mark.parametrize("seconds", [-2.0, -3600.0, 3600.0])
def test_a_clock_that_stepped_while_the_dataset_was_read_is_not_planned_on(
    prepared_input, certificates, seconds
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        clock = Stepping()
        step_after_the_listing(server, provider, clock, seconds)
        stored = rows(data[0])
        with pytest.raises(YorungeError) as error:
            resume_runtime(data, server, clock=clock).resume(
                source, accept_unverified_read=True, prepare=True
            )
        assert error.value.code == "upload_plan_not_valid"  # as for an original plan
        assert rows(data[0]) == stored  # nothing was frozen or saved


def test_a_clock_that_stepped_back_after_the_dataset_was_read_is_not_planned_on(
    prepared_input, certificates, monkeypatch
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        clock = Stepping()
        step_after_the_listing(server, provider, clock, 10.0)  # the provider took ten seconds

        def step_back(manifest):
            clock.offset -= 5.0  # still after the window opened, but before the observation

        monkeypatch.setattr(resume_module, "require_distinct_upload_content", step_back)
        stored = rows(data[0])
        with pytest.raises(YorungeError) as error:
            resume_runtime(data, server, clock=clock).resume(
                source, accept_unverified_read=True, prepare=True
            )
        assert error.value.code == "upload_plan_not_valid"
        assert rows(data[0]) == stored


def test_a_clock_that_stepped_a_little_does_not_stop_the_plan(prepared_input, certificates):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        clock = Stepping()
        step_after_the_listing(server, provider, clock, 200.0)
        done = resume_runtime(data, server, clock=clock).resume(
            source, accept_unverified_read=True, prepare=True
        )
        plan = saved(data, done.plan_id).plan
        assert instant(plan.continuation.observed_at) <= instant(plan.prepared_at)
        assert instant(plan.prepared_at) < instant(plan.expires_at)


def grown_by_files(folder):
    for number in range(limits.MAX_FILES + 4):
        (folder / f"extra-{number:05d}.txt").write_bytes(b"x")


def grown_by_bytes(folder):
    with (folder / "huge.bin").open("wb") as handle:
        handle.truncate(limits.MAX_CONTENT_BYTES + 1)  # sparse: the size alone is refused


@pytest.mark.parametrize(
    "grow,code",
    [(grown_by_files, "dataset_limit_exceeded"), (grown_by_bytes, "input_budget_exceeded")],
    ids=["more files than a dataset may hold", "more bytes than an upload may hold"],
)
def test_a_folder_that_grew_past_the_limits_is_a_changed_folder_to_the_report(
    prepared_input, certificates, grow, code
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        grow(data[1])
        assert "local_changed" in reported(data, server, source).blockers
        refused(data, server, source, code)  # the honest code, before the provider is asked


def approved_and_admitted(data, runtime, plan, clock):
    """The next two gates, driven as the user would: the approval, then the admission."""
    bound, _ = runtime._bind(plan.scope.owner)
    with open_existing_store(data[0]) as store:
        gates = FixtureContinuations(store, bound, clock=clock)
        gates.approve_continuation(
            plan.plan_id,
            plan.digest,
            plan,
            acknowledge_unverified_authority=True,
            acknowledge_unpriced_cost=True,
            acknowledge_unconfirmed_effects=bool(plan.continuation.uncertain_indices),
        )
        return gates.admit(plan.plan_id, plan)


def test_a_continuation_admitted_while_the_dataset_is_read_stops_the_next_prepare(
    prepared_input, certificates
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        runtime = resume_runtime(data, server)
        first = saved(
            data, runtime.resume(source, accept_unverified_read=True, prepare=True).plan_id
        )
        listing = f"/api/v1/datasets/{DATASET}/items?limit=128"
        admitted = []

        def another_process_admits():
            if server.requests and server.requests[-1].path == listing and not admitted:
                admitted.append(approved_and_admitted(data, runtime, first.plan, Later(0)))

        provider.on_request = another_process_admits
        with pytest.raises(OperationError) as error:
            runtime.resume(source, accept_unverified_read=True, prepare=True)
        provider.on_request = None
        # The command says what is true now: the source has a live continuation, which it names.
        assert error.value.code == "operation_conflict"
        assert error.value.operation_id == admitted[0].operation_id
        with open_existing_store(data[0]) as store:
            count = store.connection.execute("SELECT count(*) FROM upload_plans").fetchone()[0]
            assert count == 2  # the root's plan and the first one: no second plan was saved
            validate_uploads(store.connection)
        assert (
            "source_active"
            in resume_runtime(data, server).resume(source, accept_unverified_read=True).blockers
        )


def test_a_clock_that_stepped_past_the_window_after_the_seal_freezes_nothing(
    prepared_input, certificates, monkeypatch
):
    data = _files(prepared_input, 3)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        source = killed_while_running(data, server, provider, certificates, monkeypatch)
        clock = Stepping()
        clock.offset = TRANSFER_LEASE_SECONDS + 1.0  # the killed process's lease has lapsed
        fits = UploadResumeRuntime._fits

        def fits_then_step(used, count, selected, sealed):
            fits(used, count, selected, sealed)
            clock.offset += 1000.0  # a suspend, or a clock set far ahead, once the plan is sealed

        monkeypatch.setattr(UploadResumeRuntime, "_fits", staticmethod(fits_then_step))
        stored = rows(data[0])
        with pytest.raises(YorungeError) as error:
            resume_runtime(data, server, clock=clock).resume(
                source, accept_unverified_read=True, prepare=True, accept_unconfirmed_effects=True
            )
        assert error.value.code == "upload_plan_not_valid"
        assert rows(data[0]) == stored  # the source is still running: nothing was frozen
