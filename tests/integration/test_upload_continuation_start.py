"""The start of a continuation, end to end: real files, store, TLS provider and the product's own
interrupted upload and plan.

``run_upload_continuation`` is the private composition the public ``start`` will call for a v3
plan. The approval is a step of its own (the public ``approve`` is P02-3i's), done here by a small
algorithm over the same stage environment.
"""

import asyncio
import logging
import traceback
from pathlib import Path
from uuid import uuid4

import pytest

from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.http_server import Reply, TlsServer
from tests.fixtures.upload_provider import DATASET, UploadProvider, reply
from tests.integration.test_upload_continuation_stages import (
    CONFIRM,
    Skewed,
    approved,
    five_of_eight,
    journal,
    operation_of,
    planned,
    start,
)
from tests.integration.test_upload_http_budget import SECRET
from tests.integration.test_upload_original import factory
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_resume_observation import (
    certificates as certificates,
)
from tests.integration.test_upload_resume_observation import (
    interrupted,
    lose_confirm_of,
)
from tests.integration.test_upload_resume_observation import (
    loopback_only as loopback_only,
)
from tests.integration.test_upload_resume_observation import world as three_files
from tests.integration.test_upload_resume_prepare import prepared, saved
from tests.integration.test_upload_workflow_kill import _files
from yorunge.adapters import upload_continuation_start as start_module
from yorunge.adapters.platform_upload_port import ObservedUploadPort
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_continuation import ContinuationStages
from yorunge.adapters.upload_continuation_start import run_upload_continuation
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_resume import UploadResumeRuntime
from yorunge.adapters.upload_store import validate_uploads
from yorunge.domain.dataset_transfer_v3 import TransferVerificationV3
from yorunge.domain.errors import OperationError, YorungeError


async def approve_only(environment):
    """The human's approval, which the public ``approve`` will give: nothing is admitted."""
    return await approved(environment)  # the look it was approved on


def approve(data, server, plan_id):
    start(data, server, plan_id, algorithm=approve_only)


async def admit_only(environment):
    """What an invocation does that is admitted and then stopped: the operation, nothing sent."""
    assert environment.admit(await environment.admission())  # the plan is approved already
    return environment.record


def go(data, server, plan_id, *, budgets=None, clock=None):
    return run_upload_continuation(
        plan_id,
        Path(data[0]),
        lambda plan: (data[3], data[4]),
        session_factory=factory(server, budgets),
        clock=clock,
    )


# --- from the approval to a verified dataset ------------------------------------------------------


def test_an_approved_continuation_sends_what_was_left_and_proves_the_whole_dataset(
    prepared_input, certificates
):
    data, provider = three_files(prepared_input)
    budgets = []
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        sends, requests = len(provider.events), len(server.requests)
        phase = go(data, server, report.plan_id, budgets=budgets)
        assert phase.existing is False
        record = phase.record
        assert (record.status, record.reason) == ("succeeded", "metadata_verified")
        assert record == operation_of(data, report.plan_id)
        # Only the file that was left is sent, and nothing is created or linked again.
        assert provider.events[sends:] == ["presign", "put", "confirm"]
        assert provider.create_calls == 1
        effects = [r for r in server.requests[requests:] if r.method in {"POST", "PUT"}]
        assert len(effects) == 3
        view = journal(data, report.plan_id)
        assert type(view.verification) is TransferVerificationV3
        assert len(view.verification.files) == 3  # the whole manifest, though one file was sent
        assert view.verification.authorization_policy == "explicit_read_attempt"
        assert view.verification.grant is None
        assert len(view.intents) == len(view.receipts) == 3
        with open_existing_store(data[0]) as store:
            validate_uploads(store.connection)
        # Two sessions: the look at the dataset before anything is admitted (it only reads) and the
        # stages, on the plan's own budget: three effects, nothing left pending.
        look, stages = budgets
        assert look.snapshot().effect_attempts == 0
        assert look.snapshot().read_requests > 0
        assert stages.snapshot().effect_attempts == 3
        assert stages.snapshot().response_pending == 0


def test_five_of_eight_files_are_sent_and_the_eight_are_proved(prepared_input, certificates):
    data, provider = five_of_eight(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        sends = len(provider.events)
        record = go(data, server, report.plan_id).record
        assert (record.status, record.reason) == ("succeeded", "metadata_verified")
        events = provider.events[sends:]  # every presign first, then the puts two at a time
        assert events[:5] == ["presign"] * 5
        assert sorted(events[5:]) == ["confirm"] * 5 + ["put"] * 5
        view = journal(data, report.plan_id)
        assert len(view.verification.files) == 8
        assert len(view.intents) == 15


# --- a continuation that sends nothing only proves the dataset -----------------------------------


def check_only_world(prepared_input):
    """Both files are on the provider (the second's confirm was lost): nothing is left to send."""
    data = _files(prepared_input, 2)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    lose_confirm_of(provider, "two.bin")
    return data, provider


def test_a_continuation_that_sends_nothing_only_reads_and_proves_the_dataset(
    prepared_input, certificates
):
    data, provider = check_only_world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        assert saved(data, report.plan_id).plan.continuation.file_indices == ()
        approve(data, server, report.plan_id)
        sends, requests = len(provider.events), len(server.requests)
        record = go(data, server, report.plan_id).record
        assert (record.status, record.reason) == ("succeeded", "metadata_verified")
        assert record.verification_only
        assert record.workflow_latched is False
        assert provider.events[sends:] == []  # nothing was created, linked, presigned or put
        assert all(r.method == "GET" for r in server.requests[requests:])
        view = journal(data, report.plan_id)
        assert view.intents == ()
        assert view.receipts == ()
        assert len(view.verification.files) == 2  # both files were already there


# --- an operation the plan already has ------------------------------------------------------------


def no_context(plan):
    pytest.fail("an operation the plan already has asks for no context")


def test_a_plan_that_has_its_operation_returns_it_without_a_network(prepared_input, certificates):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        first = go(data, server, report.plan_id)
        requests = len(server.requests)
        again = run_upload_continuation(
            report.plan_id, Path(data[0]), no_context, session_factory=factory(server)
        )
        assert again.existing is True
        assert again.record == first.record
        assert len(server.requests) == requests


def test_a_process_that_does_not_win_the_admission_sends_and_proves_nothing(
    prepared_input, certificates, monkeypatch
):
    data, provider = three_files(prepared_input)
    original = ContinuationStages.admission

    async def admitted_first(environment):
        check = await original(environment)
        with environment.repository() as repository:
            repository.admit(environment.plan.plan_id, check)  # another process admits first
        return check

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)  # the approval comes first, then the race
        monkeypatch.setattr(ContinuationStages, "admission", admitted_first)
        sends, requests = len(provider.events), len(server.requests)
        phase = go(data, server, report.plan_id)
        assert phase.existing is True
        assert phase.record.status == "admitted"
        assert provider.events[sends:] == []
        assert all(r.method == "GET" for r in server.requests[requests:])
        assert journal(data, report.plan_id).verification is None


def test_a_plan_that_another_invocation_admits_while_this_one_looks_is_found_not_a_conflict(
    prepared_input, certificates, monkeypatch
):
    # The look takes a while (the folder is hashed, the dataset listed). Another invocation admits
    # this very plan after the first lookup and before the journal is read: the journal then shows
    # that operation in the way, and it is this plan's own.
    data, provider = three_files(prepared_input)
    original = UploadResumeRuntime._read_source
    done = []

    def read_source(runtime, operation_id):
        if not done:
            done.append(1)
            start(data, server, report.plan_id, algorithm=admit_only)  # the other invocation
        return original(runtime, operation_id)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        monkeypatch.setattr(UploadResumeRuntime, "_read_source", read_source)
        sends, budgets = len(provider.events), []
        phase = go(data, server, report.plan_id, budgets=budgets)
        assert done
        assert phase.existing is True
        assert phase.record.status == "admitted"
        assert phase.record == operation_of(data, report.plan_id)
        assert provider.events[sends:] == []
        assert budgets == []  # this invocation asked nothing


def test_a_plan_whose_dataset_its_own_operation_changed_meanwhile_is_found_not_changed(
    prepared_input, certificates, monkeypatch
):
    # The other invocation does not stop at the admission: it sends the file that was left, so the
    # dataset this one then lists is no longer the one the plan was approved on. The operation that
    # changed it is this plan's own, and it is the answer.
    data, provider = three_files(prepared_input)
    original = UploadResumeRuntime._read_remote
    done = []

    def read_remote(runtime, *args, **kwargs):
        if not done:
            done.append(1)
            assert go(data, server, report.plan_id).existing is False  # the other invocation
        return original(runtime, *args, **kwargs)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        monkeypatch.setattr(UploadResumeRuntime, "_read_remote", read_remote)
        sends = len(provider.events)
        phase = go(data, server, report.plan_id)
        assert done
        assert phase.existing is True
        assert phase.record.status == "succeeded"
        assert phase.record == operation_of(data, report.plan_id)
        assert provider.events[sends:] == ["presign", "put", "confirm"]  # the one file, once


# --- the plan no longer stands: nothing is sent and nothing is written ----------------------------

DETAIL = "/api/v1/datasets/test-user/test-dataset"
ME = "/api/v1/auth/me"
ITEMS = f"/api/v1/datasets/{DATASET}/items?limit=128"


def item_of(name, size, sha256):
    return {
        "id": str(uuid4()),
        "dataset_id": DATASET,
        "original_filename": name,
        "file_size_bytes": size,
        "sha256_hash": sha256,
    }


def foreign_item(provider, manifest):
    provider.confirmed["foreign.bin"] = item_of("foreign.bin", 3, "a" * 64)


def the_file_that_was_left(provider, manifest):
    file = manifest.files[2]
    provider.confirmed[file.path] = item_of(file.path, file.size, file.sha256)


def a_confirmed_item_vanishes(provider, manifest):
    provider.confirmed.pop(manifest.files[0].path)


def an_item_changes(provider, manifest):
    provider.confirmed[manifest.files[0].path]["sha256_hash"] = "0" * 64


def an_item_without_a_hash(provider, manifest):
    provider.confirmed[manifest.files[0].path]["sha256_hash"] = None


def the_dataset_becomes_public(provider, manifest):
    original = provider.dataset
    provider.dataset = lambda: {**original(), "visibility": "public"}


def the_dataset_is_gone(provider, manifest):
    provider.route_table[DETAIL] = lambda request, count: reply({}, 404)


@pytest.mark.parametrize(
    "change",
    [
        foreign_item,
        the_file_that_was_left,
        a_confirmed_item_vanishes,
        an_item_changes,
        an_item_without_a_hash,
        the_dataset_becomes_public,
        the_dataset_is_gone,
    ],
    ids=lambda change: change.__name__,
)
def test_a_dataset_that_changed_since_the_plan_ends_the_start_before_anything_is_written(
    prepared_input, certificates, change
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        change(provider, data[2])
        sends, requests = len(provider.events), len(server.requests)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id)
        assert error.value.code == "continuation_remote_changed"
        assert not isinstance(error.value, OperationError)  # there is no operation to name
        assert operation_of(data, report.plan_id) is None
        assert journal(data, report.plan_id).intents == ()
        assert provider.events[sends:] == []
        assert all(r.method == "GET" for r in server.requests[requests:])
        with open_existing_store(data[0]) as store:
            validate_uploads(store.connection)


@pytest.mark.parametrize(
    "path,status,code",
    [
        (ME, 401, "remote_access_denied"),
        (ME, 429, "remote_rate_limited"),
        (ITEMS, 503, "remote_failed"),
    ],
)
def test_a_look_that_fails_before_the_start_is_that_failure_and_not_a_change(
    prepared_input, certificates, path, status, code
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        provider.route_table[path] = lambda request, count: reply({}, status)
        sends = len(provider.events)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id)
        assert error.value.code == code
        assert operation_of(data, report.plan_id) is None
        assert provider.events[sends:] == []


def test_an_admission_whose_closing_gate_fails_is_that_failure_and_not_a_found_operation(
    prepared_input, certificates, monkeypatch
):
    # The record is committed before the closing time gate runs. A gate that fails then (a store
    # kept busy by siblings that write at the same moment) leaves an operation this invocation
    # admitted: the start is that failure, and the operation it sent nothing for is cancelled
    # locally. It is not reported as "another process admitted it" with the operation left alone.
    data, provider = three_files(prepared_input)
    finish, admit = StateUploads._finish, StateUploads.admit
    admitting = []

    def failing_gate(self, stamp, gate, *, scope):
        if admitting:
            raise YorungeError("state_busy")
        return finish(self, stamp, gate, scope=scope)

    def marked_admit(self, plan_id, fresh):
        admitting.append(plan_id)
        try:
            return admit(self, plan_id, fresh)
        finally:
            admitting.pop()

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        monkeypatch.setattr(StateUploads, "_finish", failing_gate)
        monkeypatch.setattr(StateUploads, "admit", marked_admit)
        sends = len(provider.events)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id)
        assert error.value.code == "state_busy"
        stored = operation_of(data, report.plan_id)
        assert stored is not None
        assert (stored.status, stored.reason) == ("cancelled", "local_cancelled")
        assert provider.events[sends:] == []


# --- a dataset that changes while the files are sent ----------------------------------------------


@pytest.mark.parametrize(
    "change", [foreign_item, a_confirmed_item_vanishes, an_item_changes], ids=lambda c: c.__name__
)
def test_a_dataset_that_changes_during_the_stages_is_not_proved_and_not_sent_again(
    prepared_input, certificates, change
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        provider.after_put = lambda name: change(provider, data[2])
        sends = len(provider.events)
        with pytest.raises(OperationError) as error:
            go(data, server, report.plan_id)
        record = operation_of(data, report.plan_id)
        assert (error.value.code, error.value.reason_code) == (
            "operation_uncertain",
            "invalid_response",
        )
        assert error.value.operation_id == record.operation_id
        # Every stage is known to be done; only the proof is missing, and nothing is replayed.
        assert (record.status, record.reason) == ("unknown", "read_unavailable")
        view = journal(data, report.plan_id)
        assert view.verification is None
        assert len(view.intents) == len(view.receipts) == 3
        assert provider.events[sends:] == ["presign", "put", "confirm"]


# --- a closing read that fails --------------------------------------------------------------------


def flip_at_the_closing_read(monkeypatch, provider, path, status):
    """The provider fails ``path`` from the closing read on (the stages and the look were fine)."""
    original = ContinuationStages.verify

    async def verify(environment):
        provider.route_table[path] = lambda request, count: reply({}, status)
        return await original(environment)

    monkeypatch.setattr(ContinuationStages, "verify", verify)


FAILURES = [
    (401, "remote_access_denied"),
    (403, "remote_access_denied"),
    (429, "remote_rate_limited"),
    (503, "remote_failed"),
]


@pytest.mark.parametrize("path", [ME, ITEMS], ids=["the permission", "the listing"])
@pytest.mark.parametrize("status,code", FAILURES)
def test_a_closing_read_that_fails_after_files_were_sent_leaves_the_read_unavailable(
    prepared_input, certificates, monkeypatch, path, status, code
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        flip_at_the_closing_read(monkeypatch, provider, path, status)
        sends = len(provider.events)
        with pytest.raises(OperationError) as error:
            go(data, server, report.plan_id)
        record = operation_of(data, report.plan_id)
        assert (error.value.code, error.value.reason_code) == ("operation_uncertain", code)
        assert error.value.operation_id == record.operation_id
        assert (record.status, record.reason) == ("unknown", "read_unavailable")
        view = journal(data, report.plan_id)
        assert view.verification is None
        assert len(view.intents) == len(view.receipts) == 3
        assert provider.events[sends:] == ["presign", "put", "confirm"]  # nothing is replayed
        requests = len(server.requests)
        again = run_upload_continuation(
            report.plan_id, Path(data[0]), no_context, session_factory=factory(server)
        )
        assert again.existing is True
        assert len(server.requests) == requests


@pytest.mark.parametrize("path", [ME, ITEMS], ids=["the permission", "the listing"])
@pytest.mark.parametrize("status,code", FAILURES)
def test_a_closing_read_that_fails_for_a_check_only_continuation_cancels_it_with_its_own_error(
    prepared_input, certificates, monkeypatch, path, status, code
):
    data, provider = check_only_world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        flip_at_the_closing_read(monkeypatch, provider, path, status)
        sends = len(provider.events)
        with pytest.raises(OperationError) as error:
            go(data, server, report.plan_id)
        record = operation_of(data, report.plan_id)
        # The read's own error, never an uncertainty: nothing was sent.
        assert (error.value.code, error.value.reason_code) == (code, code)
        assert error.value.operation_id == record.operation_id
        assert (record.status, record.reason) == ("cancelled", "local_cancelled")
        assert record.workflow_latched is False
        assert journal(data, report.plan_id).intents == ()
        assert provider.events[sends:] == []
        # The plan cannot be started again: its operation is over, a new prepare is needed.
        requests = len(server.requests)
        again = run_upload_continuation(
            report.plan_id, Path(data[0]), no_context, session_factory=factory(server)
        )
        assert again.existing is True
        assert again.record.status == "cancelled"
        assert len(server.requests) == requests


# --- an interrupt in the closing read ------------------------------------------------------------


def interrupt_the_closing_read(monkeypatch, interruption):
    async def verify(environment):
        raise interruption

    monkeypatch.setattr(ContinuationStages, "verify", verify)


@pytest.mark.parametrize(
    "interruption,seen",
    [(asyncio.CancelledError, asyncio.CancelledError), (KeyboardInterrupt, OperationError)],
    ids=["a cancelled task", "an interrupt"],
)
def test_an_interrupt_in_the_closing_read_of_a_continuation_that_sent_files_is_uncertain(
    prepared_input, certificates, monkeypatch, interruption, seen
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        interrupt_the_closing_read(monkeypatch, interruption)
        with pytest.raises(seen) as error:
            go(data, server, report.plan_id)
        record = operation_of(data, report.plan_id)
        if seen is OperationError:
            assert error.value.code == "operation_uncertain"
            assert error.value.operation_id == record.operation_id
        assert (record.status, record.reason) == ("unknown", "request_uncertain")
        assert journal(data, report.plan_id).verification is None


@pytest.mark.parametrize(
    "interruption,seen,code",
    [
        (asyncio.CancelledError, asyncio.CancelledError, None),
        (KeyboardInterrupt, OperationError, "request_cancelled"),
    ],
    ids=["a cancelled task", "an interrupt"],
)
def test_an_interrupt_in_the_closing_read_of_a_check_only_continuation_cancels_it_locally(
    prepared_input, certificates, monkeypatch, interruption, seen, code
):
    data, provider = check_only_world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        interrupt_the_closing_read(monkeypatch, interruption)
        with pytest.raises(seen) as error:
            go(data, server, report.plan_id)
        record = operation_of(data, report.plan_id)
        if code is not None:
            assert error.value.code == code
            assert error.value.operation_id == record.operation_id
        assert (record.status, record.reason) == ("cancelled", "local_cancelled")
        assert journal(data, report.plan_id).intents == ()


# --- a closing read that is too slow ------------------------------------------------------------


def the_check_goes_stale(monkeypatch, clock, seconds):
    """The permission is looked at and the gate passed; then ``seconds`` go by before listing."""
    original = StateUploads.prepare_initial_read

    def gate(repository, operation_id, owner, *, authorization=None):
        access = original(repository, operation_id, owner, authorization=authorization)
        if authorization is not None:
            clock.skew += seconds
        return access

    monkeypatch.setattr(StateUploads, "prepare_initial_read", gate)


def the_listing_takes_too_long(monkeypatch, clock):
    """The listing is read, then the clock moves past what a proof of that look may be old."""
    original = ObservedUploadPort.items

    async def items(port, client, dataset_id, *, deadline):
        found = await original(port, client, dataset_id, deadline=deadline)
        clock.skew += 40
        return found

    monkeypatch.setattr(ObservedUploadPort, "items", items)


@pytest.mark.parametrize(
    "slow,code",
    [
        (the_check_goes_stale, "execution_timeout"),
        (the_listing_takes_too_long, "upload_plan_not_valid"),
    ],
    ids=["no time is left to list", "the proof outlives its permission"],
)
def test_a_closing_read_that_is_too_slow_cancels_a_check_only_continuation_locally(
    prepared_input, certificates, monkeypatch, slow, code
):
    data, provider = check_only_world(prepared_input)
    clock = Skewed()
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        slow(monkeypatch, clock, 31) if slow is the_check_goes_stale else slow(monkeypatch, clock)
        with pytest.raises(OperationError) as error:
            go(data, server, report.plan_id, clock=clock)
        record = operation_of(data, report.plan_id)
        # Nothing was sent, so a proof that is late is no uncertainty: the operation is cancelled.
        assert error.value.code == code
        assert error.value.operation_id == record.operation_id
        assert (record.status, record.reason) == ("cancelled", "local_cancelled")
        assert journal(data, report.plan_id).verification is None


@pytest.mark.parametrize(
    "slow",
    [the_check_goes_stale, the_listing_takes_too_long],
    ids=["no time is left to list", "the proof outlives its permission"],
)
def test_a_closing_read_that_is_too_slow_leaves_a_continuation_that_sent_files_uncertain(
    prepared_input, certificates, monkeypatch, slow
):
    data, provider = three_files(prepared_input)
    clock = Skewed()
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        slow(monkeypatch, clock, 31) if slow is the_check_goes_stale else slow(monkeypatch, clock)
        sends = len(provider.events)
        with pytest.raises(OperationError) as error:
            go(data, server, report.plan_id, clock=clock)
        record = operation_of(data, report.plan_id)
        assert error.value.code == "operation_uncertain"
        assert error.value.operation_id == record.operation_id
        assert (record.status, record.reason) == ("unknown", "request_uncertain")
        view = journal(data, report.plan_id)
        assert view.verification is None
        assert len(view.receipts) == 3
        assert provider.events[sends:] == ["presign", "put", "confirm"]  # nothing is replayed


@pytest.mark.parametrize(
    "seconds,closed_as",
    [(200, "lease_expired"), (1000, "approval_expired")],
    ids=["the lease lapsed", "the window is over"],
)
def test_a_check_only_continuation_that_cannot_write_its_stop_is_still_nothing_uncertain(
    prepared_input, certificates, monkeypatch, seconds, closed_as
):
    # The time that goes by costs the operation its lease (or the plan its window), so the stop of
    # the failed read cannot be written either. A continuation that sent nothing and never will has
    # nothing to be uncertain about: the caller gets the read's own failure, and the lease cleanup
    # closes the record.
    data, provider = check_only_world(prepared_input)
    clock = Skewed()
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        the_check_goes_stale(monkeypatch, clock, seconds)
        with pytest.raises(OperationError) as error:
            go(data, server, report.plan_id, clock=clock)
        record = operation_of(data, report.plan_id)
        assert error.value.code == "execution_timeout"
        assert error.value.reason_code == error.value.code
        assert error.value.operation_id == record.operation_id
        assert (record.status, record.workflow_latched) == ("admitted", False)
        assert journal(data, report.plan_id).verification is None
        with open_existing_store(data[0]) as store:
            cleaned = StateUploads(store, clock=clock).cleanup_expired(record.operation_id)
            assert (cleaned.operation.status, cleaned.operation.reason) == ("cancelled", closed_as)
            validate_uploads(store.connection)


@pytest.mark.parametrize("seconds", [200, 1000], ids=["the lease lapsed", "the window is over"])
def test_a_continuation_that_sent_files_and_cannot_write_its_stop_is_uncertain(
    prepared_input, certificates, monkeypatch, seconds
):
    data, provider = three_files(prepared_input)
    clock = Skewed()
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        the_check_goes_stale(monkeypatch, clock, seconds)
        with pytest.raises(OperationError) as error:
            go(data, server, report.plan_id, clock=clock)
        record = operation_of(data, report.plan_id)
        # The file was sent and its stop cannot be written: the operation is left as it stands.
        assert error.value.code == "operation_uncertain"
        assert error.value.operation_id == record.operation_id
        assert record.workflow_latched is True
        assert journal(data, report.plan_id).verification is None


# --- the source is no longer alone ----------------------------------------------------------------


def two_plans(data, server, provider):
    """Two continuations prepared from one interrupted upload, both approved."""
    source = interrupted(data, server)
    first, second = prepared(data, server, source), prepared(data, server, source)
    provider.represign = True
    approve(data, server, first.plan_id)
    approve(data, server, second.plan_id)
    return first, second


def test_a_source_that_was_continued_by_another_plan_is_a_conflict_with_that_operation(
    prepared_input, certificates, monkeypatch
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        first, second = two_plans(data, server, provider)
        winner = go(data, server, first.plan_id).record
        assert winner.status == "succeeded"
        requests = len(server.requests)

        def not_looked_at(*args, **kwargs):
            pytest.fail("a refusal the journal gives costs neither a key nor a hashed folder")

        monkeypatch.setattr(start_module, "capture_upload_input", not_looked_at)
        monkeypatch.setattr(UploadResumeRuntime, "_bind", not_looked_at)
        with pytest.raises(OperationError) as error:
            go(data, server, second.plan_id)
        # The journal says so before anything is asked of the folder or the provider.
        assert (error.value.code, error.value.operation_id) == (
            "operation_conflict",
            winner.operation_id,
        )
        assert len(server.requests) == requests
        assert operation_of(data, second.plan_id) is None


def test_a_source_that_another_plan_has_admitted_is_a_conflict_with_that_operation(
    prepared_input, certificates, monkeypatch
):
    data, provider = three_files(prepared_input)
    original = ContinuationStages.admission

    async def admitted_only(environment):
        check = await original(environment)
        with environment.repository() as repository:
            repository.admit(environment.plan.plan_id, check)
        return check

    with TlsServer(certificates, provider.routes()) as server:
        first, second = two_plans(data, server, provider)
        monkeypatch.setattr(ContinuationStages, "admission", admitted_only)
        holder = go(data, server, first.plan_id)  # admitted by "another process", not run by this
        assert holder.existing is True
        assert holder.record.status == "admitted"
        monkeypatch.setattr(ContinuationStages, "admission", original)
        requests, sends = len(server.requests), len(provider.events)
        with pytest.raises(OperationError) as error:
            go(data, server, second.plan_id)
        assert (error.value.code, error.value.operation_id) == (
            "operation_conflict",
            holder.record.operation_id,
        )
        assert len(server.requests) == requests
        assert len(provider.events) == sends


# --- the plan and what it stands on ---------------------------------------------------------------


def test_a_plan_that_was_not_approved_is_not_started(prepared_input, certificates):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        requests = len(server.requests)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id)
        assert error.value.code == "approval_required"
        assert len(server.requests) == requests
        assert operation_of(data, report.plan_id) is None


def test_a_plan_whose_window_has_passed_is_not_started(prepared_input, certificates):
    data, provider = three_files(prepared_input)
    clock = Skewed()
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        clock.skew = 1000  # the plan and its approval last fifteen minutes
        requests = len(server.requests)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id, clock=clock)
        assert error.value.code == "upload_plan_not_valid"
        assert len(server.requests) == requests


def test_the_plan_of_an_original_upload_is_not_a_continuation_to_start(
    prepared_input, certificates
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        with open_existing_store(data[0]) as store:
            original = StateUploads(store).show(operation_id=report.source_operation_id).plan
        requests = len(server.requests)
        with pytest.raises(YorungeError) as error:
            go(data, server, original.plan_id)
        assert error.value.code == "upload_plan_not_valid"
        assert len(server.requests) == requests


def test_a_folder_that_changed_since_the_plan_ends_the_start_before_a_request(
    prepared_input, certificates
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        (data[1] / "ölçüm.bin").write_bytes(b"changed after the plan")
        requests = len(server.requests)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id)
        assert error.value.code == "input_changed"
        assert len(server.requests) == requests
        assert operation_of(data, report.plan_id) is None


# --- what must never be written down or said ------------------------------------------------------

VOLATILE = ("objects/blob", "upload/put?key=", "created_dataset")


def stored_bytes(state):
    return b"".join(p.read_bytes() for p in sorted(Path(state).rglob("*")) if p.is_file())


def test_no_key_and_no_volatile_provider_value_reaches_the_journal_the_log_or_the_result(
    prepared_input, certificates, caplog
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        with caplog.at_level(logging.DEBUG):
            phase = go(data, server, report.plan_id)
        view = journal(data, report.plan_id)
        own = b"".join(x.encoded() for x in (*view.intents, *view.receipts)).decode()
        shown = own + repr(phase) + phase.record.model_dump_json() + caplog.text
        assert SECRET not in shown
        assert not any(marker in shown for marker in VOLATILE[:2])
        everything = stored_bytes(data[0])
        assert SECRET.encode() not in everything
        assert b"objects/blob" not in everything
        assert b"upload/put?key=" not in everything
        assert phase.record.model_dump_json().count("created_dataset") == 0


@pytest.mark.parametrize("path", [ME, ITEMS], ids=["the permission", "the listing"])
def test_a_closing_read_that_fails_says_nothing_of_what_the_provider_answered(
    prepared_input, certificates, monkeypatch, path
):
    data, provider = three_files(prepared_input)
    canary = "PRIVATE-PROVIDER-ANSWER-CANARY"
    original = ContinuationStages.verify

    async def verify(environment):
        provider.route_table[path] = lambda request, count: Reply(
            status=500, body=f'{{"detail":"{canary} {SECRET}"}}'.encode()
        )
        return await original(environment)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        monkeypatch.setattr(ContinuationStages, "verify", verify)
        with pytest.raises(OperationError) as error:
            go(data, server, report.plan_id)
        shown = "".join(traceback.format_exception(error.value)) + repr(error.value)
        assert canary not in shown
        assert SECRET not in shown
        assert error.value.__cause__ is None
        assert error.value.__context__ is None
        assert canary.encode() not in stored_bytes(data[0])
        assert SECRET.encode() not in stored_bytes(data[0])


# --- a file whose confirm had no answer -----------------------------------------------------------


def test_a_file_whose_confirm_had_no_answer_is_sent_again_and_the_whole_dataset_is_proved(
    prepared_input, certificates
):
    data = three_files(prepared_input)[0]
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    answering = provider.confirm
    lose_confirm_of(provider, "two.bin", remembered=False)  # the confirm never took effect
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider, accept_unconfirmed_effects=True)
        provider.route_table[CONFIRM] = answering  # the provider answers again
        plan = saved(data, report.plan_id).plan
        assert plan.continuation.uncertain_indices == (1,)
        assert plan.continuation.file_indices == (1, 2)
        approve(data, server, report.plan_id)  # with the acknowledgement the plan asks for
        sends = len(provider.events)
        record = go(data, server, report.plan_id).record
        assert (record.status, record.reason) == ("succeeded", "metadata_verified")
        events = provider.events[sends:]
        assert events[:2] == ["presign", "presign"]
        assert sorted(events[2:]) == [
            "confirm",
            "confirm",
            "put",
            "put",
        ]
        assert set(provider.confirmed) == {f.path for f in data[2].files}
        view = journal(data, report.plan_id)
        assert len(view.verification.files) == 3
        assert len(view.intents) == len(view.receipts) == 6


# --- what the journal says about the source, one blocker at a time --------------------------------


SUCCESSOR = "00000000-0000-4000-8000-0000000000aa"


@pytest.mark.parametrize(
    "blockers,related,code,operation",
    [
        (("source_terminal",), None, "operation_conflict", "source"),
        (("source_ineligible",), None, "operation_conflict", "source"),
        (("create_unknown",), None, "operation_conflict", "source"),
        (("source_active",), SUCCESSOR, "operation_conflict", "successor"),
        (("source_superseded",), SUCCESSOR, "operation_conflict", "successor"),
        (("reconcile_available",), None, "continuation_remote_changed", None),
        (("known_negative",), None, "continuation_remote_changed", None),
        (("reconcile_available", "known_negative"), None, "continuation_remote_changed", None),
    ],
)
def test_what_the_journal_rules_out_ends_the_start_before_the_provider_is_asked(
    prepared_input, certificates, monkeypatch, blockers, related, code, operation
):
    data, provider = three_files(prepared_input)
    original = UploadResumeRuntime._journal

    def journal_with(source):
        chain, _, _ = original(source)
        return chain, blockers, related

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        monkeypatch.setattr(UploadResumeRuntime, "_journal", staticmethod(journal_with))
        requests = len(server.requests)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id)
        assert error.value.code == code
        assert len(server.requests) == requests
        if operation is None:  # the plan is outlived: there is no operation to name
            assert not isinstance(error.value, OperationError)
        else:  # the operation in the way: the successor when there is one, else the source
            named = report.source_operation_id if operation == "source" else SUCCESSOR
            assert error.value.operation_id == named
        assert operation_of(data, report.plan_id) is None


def test_an_admission_that_the_repository_refuses_names_the_operation_in_the_way(
    prepared_input, certificates, monkeypatch
):
    data, provider = three_files(prepared_input)
    original = ContinuationStages.admission

    async def admitted_only(environment):
        check = await original(environment)
        with environment.repository() as repository:
            repository.admit(environment.plan.plan_id, check)
        return check

    with TlsServer(certificates, provider.routes()) as server:
        first, second = two_plans(data, server, provider)
        monkeypatch.setattr(ContinuationStages, "admission", admitted_only)
        holder = go(data, server, first.plan_id)
        monkeypatch.setattr(ContinuationStages, "admission", original)

        # The look at the journal is skipped, as if the other plan was admitted a moment later.
        def journal_clear(runtime, plan):
            source, _ = runtime._read_source(plan.continuation.source_operation_id)
            return source, runtime._journal(source)[0]

        monkeypatch.setattr(start_module, "_journal_clear", journal_clear)
        sends = len(provider.events)
        with pytest.raises(OperationError) as error:
            go(data, server, second.plan_id)
        assert (error.value.code, error.value.operation_id) == (
            "operation_conflict",
            holder.record.operation_id,
        )
        assert operation_of(data, second.plan_id) is None
        assert len(provider.events) == sends
