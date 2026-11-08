"""The start of a continuation: what it refuses, what it never writes, and the chain of resumes.

Each test pins a choice the main file leaves to the reader's trust: an approval or a key that
changed is refused before one request; a lease about to end is renewed for the closing read; a
check-only continuation never says "uncertain" (it wrote no intent); the late loser of a race for
the same plan returns the winner's record; a folder replaced by an identical copy is not the
planned folder; a failed look writes nothing to the upload journal; a continuation can be resumed
in turn (a source that is itself a continuation).
"""

import asyncio
import json
import pickle
import shutil
import time
from types import SimpleNamespace

import pytest

from tests.fixtures.http_server import Reply, TlsServer
from tests.fixtures.upload_provider import reply
from tests.integration.test_upload_continuation_stages import (
    CONFIRM,
    Skewed,
    five_of_eight,
    journal,
    operation_of,
    planned,
)
from tests.integration.test_upload_continuation_start import approve, check_only_world, go
from tests.integration.test_upload_http_budget import SECRET
from tests.integration.test_upload_preparation import ENV
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_resume_observation import (
    certificates as certificates,
)
from tests.integration.test_upload_resume_observation import (
    item,
    rows,
)
from tests.integration.test_upload_resume_observation import (
    loopback_only as loopback_only,
)
from tests.integration.test_upload_resume_observation import world as three_files
from tests.integration.test_upload_resume_prepare import prepared, saved
from yorunge.adapters import upload_continuation_start as start_module
from yorunge.adapters import upload_original_read
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_continuation import ContinuationStages
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import validate_uploads
from yorunge.domain.errors import OperationError, YorungeError

# --- refused before one request, and what the closing read needs ---------------------------------


def test_a_revoked_approval_is_refused_before_any_request(prepared_input, certificates):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        with open_existing_store(data[0]) as store:
            repository = StateUploads(store)
            plan = repository.show(plan_id=report.plan_id).plan
            repository.revoke(plan.plan_id, plan.digest)
        requests = len(server.requests)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id)
        assert error.value.code == "approval_required"
        assert len(server.requests) == requests
        assert operation_of(data, report.plan_id) is None


def test_a_key_rotated_since_the_plan_is_state_changed_before_any_request(
    prepared_input, certificates, monkeypatch
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        monkeypatch.setenv(ENV, SECRET + "-rotated")
        requests = len(server.requests)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id)
        assert error.value.code == "state_changed"
        assert len(server.requests) == requests
        assert operation_of(data, report.plan_id) is None


def test_it_cannot_be_called_from_a_running_event_loop(prepared_input, certificates):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        requests = len(server.requests)

        async def inside():
            return go(data, server, report.plan_id)

        with pytest.raises(YorungeError) as error:
            asyncio.run(inside())
        assert error.value.code == "invalid_request"
        assert len(server.requests) == requests
        assert operation_of(data, report.plan_id) is None


@pytest.mark.parametrize("plan_id", ["not-a-uuid", "", "00000000-0000-4000-8000-00000000zzzz"])
def test_a_plan_id_that_is_not_a_uuid_is_invalid_request(prepared_input, certificates, plan_id):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        with pytest.raises(YorungeError) as error:
            go(data, server, plan_id)
        assert error.value.code == "invalid_request"
        assert not server.requests


@pytest.mark.parametrize("world", ["m1", "m0"])
def test_a_lease_about_to_end_is_renewed_for_the_closing_read(
    prepared_input, certificates, monkeypatch, world
):
    data, provider = (three_files if world == "m1" else check_only_world)(prepared_input)
    clock = Skewed()
    original = ContinuationStages.verify

    async def verify(environment):
        clock.skew += 145  # the 150 s lease has 5 s left
        return await original(environment)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        monkeypatch.setattr(ContinuationStages, "verify", verify)
        phase = go(data, server, report.plan_id, clock=clock)
        assert (phase.record.status, phase.record.reason) == ("succeeded", "metadata_verified")


def test_a_check_only_continuation_that_loses_its_lease_never_says_uncertain(
    prepared_input, certificates, monkeypatch
):
    data, provider = check_only_world(prepared_input)
    clock = Skewed()
    original = ContinuationStages.verify

    async def verify(environment):
        clock.skew += 200  # the lease is gone
        return await original(environment)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        monkeypatch.setattr(ContinuationStages, "verify", verify)
        with pytest.raises(OperationError) as error:
            go(data, server, report.plan_id, clock=clock)
        record = operation_of(data, report.plan_id)
        assert record.workflow_latched is False
        assert journal(data, report.plan_id).intents == ()
        # it wrote no intent: nothing it did is uncertain, whatever stopped it
        assert error.value.code != "operation_uncertain", (
            error.value.code,
            error.value.reason_code,
            record.status,
        )


def test_a_late_loser_of_the_same_plan_returns_the_record_as_it_stands(
    prepared_input, certificates, monkeypatch
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        original = start_module.capture_upload_input
        winner, entered = [], []

        def capture(*arguments, **keywords):
            result = original(*arguments, **keywords)
            if not entered:
                entered.append(1)
                winner.append(go(data, server, report.plan_id))
            return result

        monkeypatch.setattr(start_module, "capture_upload_input", capture)
        phase = go(data, server, report.plan_id)
        assert phase.existing is True
        assert phase.record.operation_id == winner[0].record.operation_id


def test_a_sibling_plan_that_wins_while_the_look_is_taken_is_the_conflict_not_a_remote_change(
    prepared_input, certificates, monkeypatch
):
    # The dataset the loser looks at later differs from what it was approved on, because the
    # winner sent its files; the cause is the winner's operation, and the error names it.
    from tests.integration.test_upload_continuation_start import two_plans

    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        first, second = two_plans(data, server, provider)
        original = start_module.capture_upload_input
        winner, entered = [], []

        def capture(*arguments, **keywords):
            result = original(*arguments, **keywords)
            if not entered:
                entered.append(1)
                winner.append(go(data, server, first.plan_id).record)
            return result

        monkeypatch.setattr(start_module, "capture_upload_input", capture)
        sent = len(provider.events)
        with pytest.raises(OperationError) as error:
            go(data, server, second.plan_id)
        assert error.value.code == "operation_conflict"
        assert error.value.operation_id == winner[0].operation_id
        assert len(provider.events) - sent == 3  # the winner's presign, put and confirm, only
        assert operation_of(data, second.plan_id) is None


def test_a_folder_replaced_by_an_identical_copy_is_not_the_planned_folder(
    prepared_input, certificates, tmp_path
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        root = data[1]
        copy = tmp_path / "copy-of-source"
        shutil.copytree(root, copy)
        shutil.rmtree(root)
        copy.rename(root)  # same path, same bytes, another directory identity
        requests = len(server.requests)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id)
        assert error.value.code == "input_changed"
        assert len(server.requests) == requests


def test_the_clock_before_the_approval_is_not_a_started_plan(prepared_input, certificates):
    data, provider = three_files(prepared_input)
    clock = Skewed()
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        clock.skew = -3600  # long before the plan was prepared
        requests = len(server.requests)
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id, clock=clock)
        assert error.value.code == "upload_plan_not_valid"
        assert len(server.requests) == requests


def _journal_tables(state):
    return rows(state)  # every upload table (the clock watermark moves with any store open)


@pytest.mark.parametrize("failure", ["gone", "public", "extra"])
def test_a_failed_look_writes_nothing_at_all_to_the_store(prepared_input, certificates, failure):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        if failure == "gone":
            provider.route_table["/api/v1/datasets/test-user/test-dataset"] = lambda r, c: reply(
                {}, 404
            )
        elif failure == "public":
            original = provider.dataset
            provider.dataset = lambda: {**original(), "visibility": "public"}
        else:
            provider.confirmed["foreign.bin"] = item("foreign.bin", size=3, sha="a" * 64)
        before = _journal_tables(data[0])
        with pytest.raises(YorungeError) as error:
            go(data, server, report.plan_id)
        assert error.value.code == "continuation_remote_changed"
        assert before == _journal_tables(data[0])


def test_an_unknown_plan_is_a_closed_error(prepared_input, certificates):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        with pytest.raises(YorungeError) as error:
            go(data, server, "00000000-0000-4000-8000-0000000000ab")
        assert error.value.code == "upload_plan_not_found"
        assert not server.requests


def test_the_phase_is_private_in_repr_and_cannot_be_pickled(prepared_input, certificates):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        phase = go(data, server, report.plan_id)
        assert repr(phase) == "<continuation phase private>"
        with pytest.raises(TypeError):
            pickle.dumps(phase)


@pytest.mark.parametrize("world", ["m1", "m0"])
def test_no_listing_is_started_when_the_invocation_end_is_within_five_seconds(
    prepared_input, certificates, monkeypatch, world
):
    data, provider = (three_files if world == "m1" else check_only_world)(prepared_input)
    real, offset = time.monotonic, [0.0]
    original = ContinuationStages.verify

    async def verify(environment):
        offset[0] = environment.end - real() - 3  # three seconds of the fifteen minutes are left
        return await original(environment)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        monkeypatch.setattr(ContinuationStages, "verify", verify)
        monkeypatch.setattr(
            upload_original_read, "time", SimpleNamespace(monotonic=lambda: real() + offset[0])
        )
        with pytest.raises(OperationError) as error:
            go(data, server, report.plan_id)
        reason = (
            error.value.reason_code
            if error.value.code == "operation_uncertain"
            else error.value.code
        )
        assert reason == "execution_timeout", (error.value.code, error.value.reason_code)


# --- a continuation whose source is itself a continuation ---------------------------------------


def lose_confirm(provider, name, *, remembered):
    original = provider.route_table[CONFIRM]

    def lose(request, count):
        if json.loads(request.body)["items"][0]["filename"] != name:
            return original(request, count)
        if remembered:
            answer = original(request, count)
            return Reply(status=answer.status, body=answer.body, truncate_at=3)
        return Reply(status=201, body=b'{"private":"response-lost"}', truncate_at=3)

    provider.route_table[CONFIRM] = lose
    return original


@pytest.mark.parametrize("remembered", [True, False], ids=["kept", "not kept"])
def test_a_continuation_is_resumed_in_turn_when_it_is_interrupted_too(
    prepared_input, certificates, remembered
):
    data, provider = five_of_eight(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report1 = planned(data, server, provider)
        plan1 = saved(data, report1.plan_id).plan
        approve(data, server, report1.plan_id)
        original = lose_confirm(provider, "f06.bin", remembered=remembered)
        with pytest.raises(OperationError) as stopped:
            go(data, server, report1.plan_id)
        assert stopped.value.code == "operation_uncertain"
        provider.route_table[CONFIRM] = original
        c1 = operation_of(data, report1.plan_id)
        assert (c1.status, c1.reason) == ("unknown", "request_uncertain")
        # the second interruption: resume the continuation itself
        report2 = prepared(data, server, c1.operation_id, accept_unconfirmed_effects=not remembered)
        binding = saved(data, report2.plan_id).plan.continuation
        # the source is the continuation that was cut short; the baseline stays the dataset's root
        assert binding.source_operation_id == c1.operation_id
        assert binding.baseline_operation_id == plan1.continuation.baseline_operation_id
        assert binding.remote_present_count == (6 if remembered else 5)
        approve(data, server, report2.plan_id)
        sent = len(provider.events)
        phase = go(data, server, report2.plan_id)
        view = journal(data, report2.plan_id)
        assert len(provider.events) - sent == 3 * len(binding.file_indices)  # presign, put, confirm
        with open_existing_store(data[0]) as store:
            validate_uploads(store.connection)
        # the whole chain is over: a third start of the same plan finds its operation
        requests = len(server.requests)
        again = go(data, server, report2.plan_id)
        assert again.existing is True
        assert len(server.requests) == requests
    assert phase.record.status == "succeeded"
    assert len(view.verification.files) == len(data[2].files)
