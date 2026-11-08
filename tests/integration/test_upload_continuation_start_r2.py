"""The start of a continuation, second review: what is never uncertain, what a race may not say,
and the budgets and checks that no other test reached on its own.

ADR-0031 section 5: before its first intent a continuation has sent nothing, so nothing it fails
with is unknown or uncertain, whether the failure is a lease that lapsed, a window that closed, a
real SIGINT or a store that cannot write the stop. A late loser of a race for the SAME plan is told
the plan's own operation, never "your operation is in your way". The rest pins mutants that
survived the older tests: the guard of a running loop, the approval's lower bound, the invocation's
end, the second look at the scope, the listing margins of the closing read and the proof's
constructor.
"""

import asyncio
import hashlib
import os
import signal
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from tests.fixtures.http_server import TlsServer
from tests.fixtures.upload_provider import DATASET, reply
from tests.integration.test_upload_continuation_stages import (
    Skewed,
    journal,
    operation_of,
    planned,
    start,
)
from tests.integration.test_upload_continuation_start import (
    DETAIL,
    ITEMS,
    ME,
    admit_only,
    approve,
    check_only_world,
    go,
    no_context,
    two_plans,
)
from tests.integration.test_upload_original import factory
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_resume_observation import (
    certificates as certificates,
)
from tests.integration.test_upload_resume_observation import (
    loopback_only as loopback_only,
)
from tests.integration.test_upload_resume_observation import world as three_files
from yorunge import api
from yorunge.adapters import upload_continuation_start as start_module
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_continuation import ContinuationStages
from yorunge.adapters.upload_continuation_read import continuation_proof
from yorunge.adapters.upload_continuation_start import run_upload_continuation
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_resume import UploadResumeRuntime
from yorunge.adapters.upload_store import validate_uploads
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.errors import OperationError, YorungeError


def store_is_valid(data):
    with open_existing_store(data[0]) as store:
        validate_uploads(store.connection)


def world_of(name, prepared_input):
    return (three_files if name == "m1" else check_only_world)(prepared_input)


# --- before its first intent a continuation is never uncertain ------------------------------------


@pytest.mark.parametrize(
    "seconds,closed_as",
    [(200, "lease_expired"), (1000, "approval_expired")],
    ids=["the lease lapsed", "the window is over"],
)
def test_a_continuation_that_sends_files_and_fails_before_its_first_intent_is_not_uncertain(
    prepared_input, certificates, monkeypatch, seconds, closed_as
):
    # The time that goes by right after the admission costs the lease (or the window): the first
    # stage cannot be armed and the stop cannot be written either. Nothing was ever written.
    data, provider = three_files(prepared_input)
    clock = Skewed()
    original = ContinuationStages.admit

    def admit(environment, check):
        result = original(environment, check)
        clock.skew += seconds
        return result

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        monkeypatch.setattr(ContinuationStages, "admit", admit)
        sends = len(provider.events)
        with pytest.raises(OperationError) as error:
            go(data, server, report.plan_id, clock=clock)
        record = operation_of(data, report.plan_id)
        assert error.value.code != "operation_uncertain"
        assert error.value.operation_id == record.operation_id
        assert (record.status, record.workflow_latched) == ("admitted", False)
        assert journal(data, report.plan_id).intents == ()
        assert provider.events[sends:] == []
        with open_existing_store(data[0]) as store:  # the lease cleanup closes the record
            cleaned = StateUploads(store, clock=clock).cleanup_expired(record.operation_id)
        assert (cleaned.operation.status, cleaned.operation.reason) == ("cancelled", closed_as)
        store_is_valid(data)


def test_a_check_only_continuation_that_loses_its_lease_says_the_leases_own_code(
    prepared_input, certificates, monkeypatch
):
    data, provider = check_only_world(prepared_input)
    clock = Skewed()
    original = ContinuationStages.admit

    def admit(environment, check):
        result = original(environment, check)
        clock.skew += 200  # the lease (150 s) lapsed: nothing was sent and nothing will be
        return result

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        monkeypatch.setattr(ContinuationStages, "admit", admit)
        with pytest.raises(OperationError) as error:
            go(data, server, report.plan_id, clock=clock)
        assert (error.value.code, error.value.exit_code) == ("operation_lease_lost", 2)
        assert operation_of(data, report.plan_id).status == "admitted"


def test_a_real_sigint_right_after_the_operation_exists_cancels_it_before_any_permit(
    prepared_input, certificates, monkeypatch
):
    # asyncio delivers a cancellation at the next real suspension; the stage environment takes it
    # before it arms the first permit, so the interrupt that came after the admission is still one
    # that came before the first intent.
    data, provider = three_files(prepared_input)
    original = ContinuationStages.admit

    def admit(environment, check):
        result = original(environment, check)
        os.kill(os.getpid(), signal.SIGINT)  # delivered while the operation has just been made
        return result

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        monkeypatch.setattr(ContinuationStages, "admit", admit)
        sends = len(provider.events)
        with pytest.raises(OperationError) as error:
            go(data, server, report.plan_id)
        record = operation_of(data, report.plan_id)
        assert (error.value.code, error.value.exit_code) == ("request_cancelled", 6)
        assert (record.status, record.reason) == ("cancelled", "local_cancelled")
        assert journal(data, report.plan_id).intents == ()
        assert provider.events[sends:] == []
        store_is_valid(data)


# --- a late loser of a race for the same plan -----------------------------------------------------


def test_a_plan_admitted_between_the_two_reads_of_the_journal_returns_its_own_record(
    prepared_input, certificates, monkeypatch
):
    # The look fails (503); nobody has admitted the plan when the refusal is explained; another
    # invocation admits THIS plan right after the journal was read for a sibling in the way.
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        healthy = provider.route_table[DETAIL]
        provider.route_table[DETAIL] = lambda request, count: reply({}, 503)
        original, seen = start_module._explained, []

        def explained(runtime, plan, refusal):
            seen.append(refusal.code)
            answer = original(runtime, plan, refusal)
            provider.route_table[DETAIL] = healthy
            start(data, server, report.plan_id, algorithm=admit_only)  # the plan's own operation
            return answer

        monkeypatch.setattr(start_module, "_explained", explained)
        phase = go(data, server, report.plan_id)
        assert seen == ["remote_failed"]
        assert phase.existing is True
        assert phase.record == operation_of(data, report.plan_id)


@pytest.mark.parametrize("status", [503, 429])
def test_a_loser_whose_admission_probe_fails_after_the_winner_finished_returns_the_winners_record(
    prepared_input, certificates, monkeypatch, status
):
    data, provider = three_files(prepared_input)
    original, done = ContinuationStages.admission, []

    async def admission(environment):
        if not done:
            done.append(1)
            result = []
            thread = threading.Thread(target=lambda: result.append(go(data, server, plan_id)))
            thread.start()
            thread.join()
            assert result[0].existing is False
            assert result[0].record.status == "succeeded"
            provider.route_table[ME] = lambda request, count: reply({}, status)
        return await original(environment)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        plan_id = report.plan_id
        approve(data, server, plan_id)
        monkeypatch.setattr(ContinuationStages, "admission", admission)
        phase = go(data, server, plan_id)
        assert phase.existing is True
        assert phase.record.status == "succeeded"
        assert phase.record == operation_of(data, plan_id)


def test_a_store_that_is_busy_when_the_plans_operation_is_asked_for_is_said_not_hidden(
    prepared_input, certificates, monkeypatch
):
    # "No answer" is not "the plan has no operation": the busy store is what the caller is told,
    # not the look's refusal that the plan's operation (unseen) may have caused.
    data, provider = three_files(prepared_input)
    original, calls = start_module._initial, []

    def initial(plan_id, state_dir, clock):
        calls.append(plan_id)
        if len(calls) == 2:
            raise OperationError("state_busy")
        return original(plan_id, state_dir, clock)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        provider.route_table[DETAIL] = lambda request, count: reply({}, 503)
        monkeypatch.setattr(start_module, "_initial", initial)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id)
        assert error.value.code == "state_busy"
        assert len(calls) == 2


def _journal_that_cannot_explain(prepared_input, certificates, monkeypatch, second):
    data, provider = three_files(prepared_input)
    original, calls = UploadResumeRuntime._read_source, []

    def read_source(runtime, operation_id):
        calls.append(operation_id)
        if len(calls) == 2:
            raise second(operation_id)
        return original(runtime, operation_id)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        provider.route_table[DETAIL] = lambda request, count: reply({}, 503)
        monkeypatch.setattr(UploadResumeRuntime, "_read_source", read_source)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id)
        assert len(calls) == 2
        assert error.value.code == "remote_failed"


def test_an_operation_error_that_is_not_a_conflict_does_not_replace_the_refusal(
    prepared_input, certificates, monkeypatch
):
    _journal_that_cannot_explain(
        prepared_input,
        certificates,
        monkeypatch,
        lambda source: OperationError("state_busy", source),
    )


def test_a_plain_error_of_the_second_journal_read_does_not_replace_the_refusal(
    prepared_input, certificates, monkeypatch
):
    _journal_that_cannot_explain(
        prepared_input, certificates, monkeypatch, lambda source: YorungeError("state_invalid")
    )


def test_a_plan_that_stops_being_startable_during_the_look_leaves_the_looks_own_refusal(
    prepared_input, certificates, monkeypatch
):
    # The approval is revoked while the look is taken and the look fails: the plan has no operation
    # and cannot get one, so the look's refusal stands.
    data, provider = three_files(prepared_input)
    original = UploadResumeRuntime._read_remote

    def read_remote(runtime, *arguments, **keywords):
        with open_existing_store(data[0]) as store:
            repository = StateUploads(store)
            plan = repository.show(plan_id=report.plan_id).plan
            repository.revoke(plan.plan_id, plan.digest)
        return original(runtime, *arguments, **keywords)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        provider.route_table[DETAIL] = lambda request, count: reply({}, 503)
        monkeypatch.setattr(UploadResumeRuntime, "_read_remote", read_remote)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id)
        assert error.value.code == "remote_failed"


def test_the_refusal_of_a_look_is_raised_without_its_context(prepared_input, certificates):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        provider.route_table[DETAIL] = lambda request, count: reply({}, 503)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id)
        assert error.value.code == "remote_failed"
        assert error.value.__cause__ is None
        assert error.value.__suppress_context__ is True


def test_an_error_that_names_a_sibling_operation_leaves_run_stages_without_its_chain(
    prepared_input, certificates
):
    # ``failure`` returns the error itself when it names an operation of another plan; the chain it
    # carries (here a provider-derived canary) must not leave ``run_stages`` with it.
    data, provider = three_files(prepared_input)
    canary = "PRIVATE-CHAIN-CANARY"
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)

        async def boom(environment):
            try:
                raise ValueError(canary)
            except ValueError as inner:
                raise OperationError("operation_conflict", report.source_operation_id) from inner

        with pytest.raises(OperationError) as error:
            start(data, server, report.plan_id, algorithm=boom)
        assert error.value.code == "operation_conflict"
        assert error.value.__cause__ is None
        assert error.value.__context__ is None


def test_a_sibling_admitted_and_lapsed_does_not_block_the_next_plan(prepared_input, certificates):
    # P1 was admitted by a process that then died (its lease lapses, nothing was sent): P2 starts,
    # the admission cancels P1's record in its own transaction, and P2 succeeds.
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        first, second = two_plans(data, server, provider)
        start(data, server, first.plan_id, algorithm=admit_only)
        assert operation_of(data, first.plan_id).status == "admitted"
        late = Skewed()
        late.skew = 200  # the lease of P1 (150 s) has lapsed
        sends = len(provider.events)
        phase = go(data, server, second.plan_id, clock=late)
        assert phase.existing is False
        assert phase.record.status == "succeeded"
        assert provider.events[sends:] == ["presign", "put", "confirm"]
        cancelled = operation_of(data, first.plan_id)
        assert (cancelled.status, cancelled.reason) == ("cancelled", "lease_expired")
        store_is_valid(data)


def test_a_sibling_admitted_with_a_live_lease_blocks_the_next_plan_and_nothing_is_asked(
    prepared_input, certificates
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        first, second = two_plans(data, server, provider)
        start(data, server, first.plan_id, algorithm=admit_only)
        held = operation_of(data, first.plan_id)
        requests = len(server.requests)
        with pytest.raises(OperationError) as error:
            go(data, server, second.plan_id)
        assert (error.value.code, error.value.operation_id) == (
            "operation_conflict",
            held.operation_id,
        )
        assert len(server.requests) == requests


# --- the arguments, the budgets and the checks the older tests never reached on their own ---------


def test_an_existing_operation_is_not_returned_from_inside_a_running_loop(
    prepared_input, certificates
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        go(data, server, report.plan_id)

        async def inside():
            return run_upload_continuation(
                report.plan_id, Path(data[0]), no_context, session_factory=factory(server)
            )

        with pytest.raises(YorungeError) as error:
            asyncio.run(inside())
        assert error.value.code == "invalid_request"


def test_a_state_dir_that_is_not_a_path_is_invalid_request(prepared_input, certificates):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        with pytest.raises(YorungeError) as error:
            run_upload_continuation(
                report.plan_id, str(data[0]), no_context, session_factory=factory(server)
            )
        assert error.value.code == "invalid_request"


def test_a_clock_between_the_plan_and_its_approval_is_refused_before_one_request(
    prepared_input, certificates
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        view = journal(data, report.plan_id)
        prepared_at, approved_at = (
            instant(view.plan.prepared_at),
            instant(view.approval.approved_at),
        )
        assert approved_at > prepared_at
        clock = Skewed()
        clock.skew = (
            prepared_at + (approved_at - prepared_at) / 2 - datetime.now(UTC)
        ).total_seconds()
        requests = len(server.requests)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id, clock=clock)
        assert error.value.code == "upload_plan_not_valid"
        assert len(server.requests) == requests


def test_the_invocation_ends_fifteen_minutes_after_it_started(
    prepared_input, certificates, monkeypatch
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        real, first, ends = time.monotonic, [], []

        def monotonic():
            if not first:
                first.append(1)
                return real() - 100  # the invocation "started" 100 s ago
            return real()

        monkeypatch.setattr(start_module, "time", SimpleNamespace(monotonic=monotonic))
        original = start_module.run_stages

        def spy(runtime, plan, bound, inputs, baseline, end, algorithm):
            ends.append(end - real())
            return original(runtime, plan, bound, inputs, baseline, end, algorithm)

        monkeypatch.setattr(start_module, "run_stages", spy)
        assert go(data, server, report.plan_id).record.status == "succeeded"
        assert 797 < ends[0] < 801, ends


def test_the_look_and_the_stages_cannot_outlive_the_invocation(
    prepared_input, certificates, monkeypatch
):
    # The invocation "started" 870 s ago, so 30 s of it are left: the look (a listing may take up to
    # 60 s) and the stages end with the invocation, not a minute after they began.
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        real, first, ends, budgets = time.monotonic, [], [], []

        def monotonic():
            if not first:
                first.append(1)
                return real() - 870
            return real()

        monkeypatch.setattr(start_module, "time", SimpleNamespace(monotonic=monotonic))
        original = start_module.run_stages

        def spy(runtime, plan, bound, inputs, baseline, end, algorithm):
            ends.append(end)
            return original(runtime, plan, bound, inputs, baseline, end, algorithm)

        monkeypatch.setattr(start_module, "run_stages", spy)
        assert go(data, server, report.plan_id, budgets=budgets).record.status == "succeeded"
        look, stages = budgets
        assert look.end <= ends[0] + 0.5, (look.end, ends[0])
        assert stages.end <= ends[0] + 0.5, (look.end, ends[0])


def test_the_stage_budget_lasts_as_long_as_the_invocation(
    prepared_input, certificates, monkeypatch
):
    # With 800 s of the invocation left the stages may use 800 s, not a minute.
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        real, first, budgets = time.monotonic, [], []

        def monotonic():
            if not first:
                first.append(1)
                return real() - 100
            return real()

        monkeypatch.setattr(start_module, "time", SimpleNamespace(monotonic=monotonic))
        assert go(data, server, report.plan_id, budgets=budgets).record.status == "succeeded"
        assert 790 < budgets[1].end - real() < 801, budgets[1].end - real()


def test_an_identity_reset_during_the_folder_capture_ends_the_look_before_the_dataset_is_read(
    prepared_input, certificates, monkeypatch
):
    data, provider = three_files(prepared_input)
    original = start_module.capture_upload_input

    def capture(*arguments, **keywords):
        result = original(*arguments, **keywords)
        digest = api.preview_identity_reset(state_dir=data[0]).data.digest
        api.reset_identity(digest, state_dir=data[0])  # another process, while the folder is hashed
        return result

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        monkeypatch.setattr(start_module, "capture_upload_input", capture)
        requests = len(server.requests)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id)
        assert error.value.code == "state_changed"
        assert len(server.requests) == requests  # the dataset was not asked about


@pytest.mark.parametrize("world", ["m1", "m0"])
def test_an_identity_reset_between_the_look_and_the_admission_asks_nothing_more(
    prepared_input, certificates, monkeypatch, world
):
    data, provider = world_of(world, prepared_input)
    original = start_module.run_stages

    def run_stages(*arguments, **keywords):
        digest = api.preview_identity_reset(state_dir=data[0]).data.digest
        api.reset_identity(digest, state_dir=data[0])
        return original(*arguments, **keywords)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        monkeypatch.setattr(start_module, "run_stages", run_stages)
        requests = len(server.requests)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id)
        assert error.value.code == "state_changed"
        asked = [r.path for r in server.requests[requests:]]
        assert asked.count(ME) == 1
        assert len(asked) == 7  # the look only


@pytest.mark.parametrize("world", ["m1", "m0"])
def test_a_refused_admission_probe_is_the_providers_refusal(prepared_input, certificates, world):
    data, provider = world_of(world, prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        original, calls = server.routes[ME], []

        def refuse_the_second(request, count):
            calls.append(1)  # the look is the first read of the context, the probe the second
            return reply({}, 401) if len(calls) == 2 else original(request, count)

        server.routes[ME] = refuse_the_second
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id)
        assert error.value.code == "remote_access_denied"
        assert operation_of(data, report.plan_id) is None


# --- the closing read's margins -------------------------------------------------------------------


def _environment(which, *, end=600.0, checked_ago=0.0):
    now = datetime.now(UTC)
    far, soon = timestamp(now + timedelta(seconds=600)), timestamp(now + timedelta(seconds=3))
    return (
        SimpleNamespace(
            record=SimpleNamespace(
                lease=SimpleNamespace(expires_at=soon if which == "lease" else far),
                approval=SimpleNamespace(expires_at=soon if which == "approval" else far),
            ),
            plan=SimpleNamespace(expires_at=soon if which == "plan" else far),
            runtime=SimpleNamespace(clock=SimpleNamespace(now=lambda: now)),
            end=time.monotonic() + end,
        ),
        SimpleNamespace(checked_at=timestamp(now - timedelta(seconds=checked_ago))),
    )


def test_the_listing_deadline_is_the_time_left_of_the_freshness_not_thirty_seconds():
    from yorunge.adapters.upload_original_read import _deadline

    environment, check = _environment("none", checked_ago=25)
    left = _deadline(environment, check, SimpleNamespace(grant=None)) - time.monotonic()
    assert 4.0 < left < 5.2, left  # a check 25 s old has 5 s of its 30 left


@pytest.mark.parametrize("which", ["lease", "approval", "plan"])
def test_the_listing_needs_five_seconds_before_the_lease_the_approval_and_the_plan_end(which):
    from yorunge.adapters.upload_original_read import _deadline

    environment, check = _environment(which)
    with pytest.raises(YorungeError) as error:
        _deadline(environment, check, SimpleNamespace(grant=None))
    assert error.value.code == "execution_timeout"


@pytest.mark.parametrize("world", ["m1", "m0"])
def test_a_closing_read_in_the_last_seconds_of_the_plan_window_is_too_late_even_with_a_long_lease(
    prepared_input, certificates, monkeypatch, world
):
    # The lease (150 s) outlives the plan's window: the margin of the closing read is the plan's
    # and the approval's own end, whatever the lease says.
    data, provider = world_of(world, prepared_input)
    clock, original = Skewed(), ContinuationStages.verify

    async def verify(environment):
        plan_end = instant(environment.plan.expires_at)
        now = environment.runtime.clock.now()
        assert instant(environment.record.lease.expires_at) > plan_end
        clock.skew += (plan_end - now).total_seconds() - 3  # three seconds of the window are left
        return await original(environment)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        plan = journal(data, report.plan_id).plan
        clock.skew = (instant(plan.expires_at) - datetime.now(UTC)).total_seconds() - 100
        monkeypatch.setattr(ContinuationStages, "verify", verify)
        with pytest.raises(OperationError) as error:
            go(data, server, report.plan_id, clock=clock)
        reason = (
            error.value.reason_code
            if error.value.code == "operation_uncertain"
            else error.value.code
        )
        assert reason == "execution_timeout"


def test_the_proof_of_a_continuation_is_built_from_what_the_read_was_allowed_under(
    prepared_input, certificates
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        go(data, server, report.plan_id)
    view = journal(data, report.plan_id)
    stored = view.verification
    other_scope = stored.scope.model_copy(update={"credential_revision": 999})
    access = SimpleNamespace(scope=other_scope, policy=stored.authorization_policy, grant=None)
    built = continuation_proof(
        view.plan, stored.dataset_id, access, stored.observed_at, stored.files
    )
    # The scope and the policy are the access's own; the project is the plan's; the files, as given.
    assert built.scope == other_scope
    assert built.scope != stored.scope
    assert built.authorization_policy == stored.authorization_policy
    assert built.grant is None
    assert built.project_id == view.plan.scope.project_id == stored.project_id
    assert (built.dataset_id, built.observed_at, built.files) == (
        stored.dataset_id,
        stored.observed_at,
        stored.files,
    )
    rebuilt = continuation_proof(
        view.plan,
        stored.dataset_id,
        SimpleNamespace(scope=stored.scope, policy=stored.authorization_policy, grant=None),
        stored.observed_at,
        stored.files,
    )
    assert rebuilt == stored


# --- a hostile listing at the look and at the closing read ----------------------------------------


def _serve(provider, pages, totals=None, cursors=None):
    """One route per page of the item listing: ``pages[i]`` is the list of items of page i."""
    for number, found in enumerate(pages):
        path = ITEMS if number == 0 else f"{ITEMS}&cursor=c{number}"
        following = (
            cursors[number]
            if cursors is not None
            else (f"c{number + 1}" if number + 1 < len(pages) else None)
        )
        total = totals[number] if totals is not None else sum(len(page) for page in pages)
        provider.route_table[path] = (
            lambda request, count, found=found, following=following, total=total: reply(
                {"items": found, "total": total, "next_cursor": following}
            )
        )


def _foreign(i):
    return {
        "id": str(uuid4()),
        "dataset_id": DATASET,
        "original_filename": f"foreign-{i}.bin",
        "file_size_bytes": 1,
        "sha256_hash": hashlib.sha256(str(i).encode()).hexdigest(),
    }


def _hostile(provider, case):
    mine = [{**item} for item in provider.confirmed.values()]
    if case == "repeated_cursor":
        _serve(provider, [mine, mine], cursors=["c1", "c1"])
    elif case == "duplicate_id":
        _serve(provider, [[*mine, mine[0]]])
    elif case == "total_drift":
        _serve(provider, [mine[:1], mine[1:]], totals=[len(mine), len(mine) + 5])
    elif case == "foreign_only":
        _serve(provider, [[_foreign(0)]])
    elif case == "foreign_extra":
        _serve(provider, [[*mine, _foreign(1)]])
    else:
        _serve(provider, [mine[:-1]])  # one of the files is missing


@pytest.mark.parametrize("case", ["repeated_cursor", "duplicate_id", "total_drift", "foreign_only"])
def test_a_listing_that_is_not_the_datasets_at_the_look_ends_the_look_as_a_remote_change(
    prepared_input, certificates, case
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        _hostile(provider, case)
        sends = len(provider.events)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id)
        assert error.value.code == "continuation_remote_changed"
        assert operation_of(data, report.plan_id) is None
        assert provider.events[sends:] == []


@pytest.mark.parametrize("world", ["m1", "m0"])
@pytest.mark.parametrize("case", ["duplicate_id", "foreign_extra", "missing_item"])
def test_a_listing_that_is_not_the_datasets_at_the_closing_read_is_a_failed_read(
    prepared_input, certificates, monkeypatch, world, case
):
    data, provider = world_of(world, prepared_input)
    original = ContinuationStages.verify

    async def verify(environment):
        _hostile(provider, case)
        return await original(environment)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        monkeypatch.setattr(ContinuationStages, "verify", verify)
        with pytest.raises(OperationError) as error:
            go(data, server, report.plan_id)
        record, view = operation_of(data, report.plan_id), journal(data, report.plan_id)
        if world == "m1":
            assert (error.value.code, error.value.reason_code) == (
                "operation_uncertain",
                "invalid_response",
            )
            assert (record.status, record.reason) == ("unknown", "read_unavailable")
        else:
            assert error.value.code == "invalid_response"
            assert view.intents == ()
            assert (record.status, record.reason) == ("cancelled", "local_cancelled")
        assert view.verification is None
