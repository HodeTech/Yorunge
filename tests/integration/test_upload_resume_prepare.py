"""``resume --prepare`` over a real interrupted upload: the plan it saves and what it refuses.

Like the report tests, the source is made by the product itself. A source SIGKILLed while it ran is
the one a freeze is for: its lease has to lapse (a clock a little ahead of the real one) before it
is found frozen. Whatever prepare refuses, it refuses before it freezes or writes.
"""

import multiprocessing
import os
import signal
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.http_server import TlsServer
from tests.fixtures.upload_provider import DATASET, UploadProvider
from tests.integration.test_upload_http_budget import SECRET
from tests.integration.test_upload_original import approved
from tests.integration.test_upload_preparation import ENV
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_resume_observation import (
    certificates as certificates,
)
from tests.integration.test_upload_resume_observation import (
    interrupted,
    item,
    lose_confirm_of,
    resume_runtime,
    rows,
    world,
)
from tests.integration.test_upload_resume_observation import (
    loopback_only as loopback_only,
)
from tests.integration.test_upload_workflow_kill import _child, _files, _settle
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import validate_uploads
from yorunge.domain.capabilities import instant
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_resume import ContinuationNotPossible


class Later:
    """A clock a little ahead of the real one: leases taken a moment ago have lapsed."""

    def __init__(self, seconds=151):
        self.seconds = seconds

    def now(self):
        return datetime.now(UTC) + timedelta(seconds=self.seconds)

    def monotonic(self):
        return time.monotonic() + self.seconds


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
        before = len(server.requests)
        report = prepared(data, server, source)
        assert report.eligible and report.plan_id is not None
        view = saved(data, report.plan_id)
        plan = view.plan
        assert isinstance(plan, DatasetContinuationPlanV3) and plan.digest == report.plan_digest
        binding = plan.continuation
        assert (binding.source_operation_id, binding.baseline_operation_id) == (source, source)
        assert (binding.dataset_id, binding.file_indices, binding.uncertain_indices) == (
            DATASET,
            (2,),
            (),
        )
        assert binding.remote_present_count == 2 and binding.observed_at == report.observed_at
        assert plan.request_limits.files == 1 and plan.status == "attempt_ready"
        assert plan.request_limits.max_upload_bytes == len(b"different")
        assert (plan.admission_policy, plan.grant, plan.cost_bound) == (
            "explicit_attempt",
            None,
            None,
        )
        assert view.operation is None and view.approval is None  # nothing is admitted or approved
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
        assert plan.continuation.file_indices == () and plan.request_limits.files == 0
        assert (
            plan.request_limits.max_upload_bytes == 0
            and plan.continuation.remote_present_count == 2
        )
        assert report.observation.send_files == 0 and report.observation.send_bytes == 0


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
        # The plan may be approved and started for a quarter of an hour from its preparation.
        prepared_at, expires_at = instant(plan.prepared_at), instant(plan.expires_at)
        assert timedelta(0) < expires_at - prepared_at <= timedelta(seconds=900)
        assert instant(plan.continuation.observed_at) <= prepared_at


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
    data = prepared_input
    from tests.integration.test_upload_file_workflow import many

    data = many(data)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    lose_confirm_of(
        provider, "two.bin", remembered=False
    )  # a confirm that may or may not have landed
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        refused(data, server, source, "approval_required")
        report = prepared(data, server, source, accept_unconfirmed_effects=True)
        plan = saved(data, report.plan_id).plan
        assert plan.continuation.uncertain_indices == (1,) and plan.continuation.file_indices == (
            1,
            2,
        )


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
        assert len(server.requests) == before and rows(data[0]) == stored


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
        assert isinstance(error, ContinuationNotPossible) and error.blockers == blockers
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
        assert report.quota_used.plans == 1 and report.quota_added.plans == 1


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
        assert report.eligible and rows(data[0]) == stored
        # The confirm that was about to be sent never was: it may be sent now, so it is uncertain.
        assert report.observation.unconfirmed_ack_required
        with pytest.raises(YorungeError) as error:
            later.resume(source, accept_unverified_read=True, prepare=True)
        assert error.value.code == "approval_required" and rows(data[0]) == stored
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
        assert frozen.fence == record.fence + 1 and done.plan_id is not None
