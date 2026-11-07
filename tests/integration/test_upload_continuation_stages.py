"""A continuation's stages over a real interrupted upload: real files, store, TLS provider.

The source is made by the product itself (the original workflow stops at the provider's lost
answer), the plan by the producer of P02-3h, and the stages are run by the environment of P02-3w.
What the start of P02-3y will do around them (approve, admit) is done here by a small algorithm of
the test: it takes the stage's fresh check, approves and admits with it, and sends the files.
"""

import asyncio
import logging
import time
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.http_server import Reply, TlsServer
from tests.fixtures.upload_provider import DATASET, UploadProvider, reply
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
from yorunge.adapters.capability_cache import StateCache
from yorunge.adapters.dataset_files import open_dataset
from yorunge.adapters.identity import StateCredentialRegistry
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_continuation import ContinuationStages, run_stages
from yorunge.adapters.upload_input_files import capture_upload_input
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_resume import UploadResumeRuntime
from yorunge.adapters.upload_store import read_manifest, validate_uploads
from yorunge.application.datasets import DatasetBudget
from yorunge.application.upload_workflow import continue_files
from yorunge.domain.credentials import ResolvedCredential, SecretValue
from yorunge.domain.errors import OperationError, YorungeError

PRESIGN = f"/api/v1/datasets/{DATASET}/upload/presign"
CONFIRM = f"/api/v1/datasets/{DATASET}/upload/confirm"


def eight_files(data):
    """Eight files of distinct content: ``f01.bin`` to ``f07.bin`` and the fixture's ``one.bin``."""
    for number in range(1, 8):
        (data[1] / f"f{number:02d}.bin").write_bytes(f"distinct content of file {number}".encode())
    with open_dataset(data[1], DatasetBudget()) as tree:
        manifest = tree.scan()
    return (*data[:2], manifest, *data[3:])


def five_of_eight(prepared_input):
    """Files 0 and 1 are confirmed, file 2 took its confirm without an answer: 3 to 7 remain."""
    data = eight_files(prepared_input)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id, represign=True)
    lose_confirm_of(provider, "f03.bin")
    return data, provider


async def approve_admit_continue(environment):
    """The start of a continuation, as P02-3y will compose it, reduced to what the stages need."""
    check = await environment.current("presign")
    with environment.repository() as repository:
        repository.approve_continuation(
            environment.plan.plan_id,
            environment.plan.digest,
            check,
            acknowledge_unverified_authority=True,
            acknowledge_unpriced_cost=True,
            acknowledge_unconfirmed_effects=bool(environment.plan.continuation.uncertain_indices),
        )
    environment.admit(check)
    return await continue_files(environment)


def start(
    data,
    server,
    plan_id,
    *,
    budgets=None,
    clock=None,
    algorithm=approve_admit_continue,
    baseline=None,
    window=None,
    ends=None,
):
    """The stages of a saved continuation plan over TLS; the operation's record at the end.

    ``window`` gives the stages that many seconds instead of the invocation's, ``ends`` collects
    the end they were given."""
    state, _, _, context, profile = data
    runtime = UploadResumeRuntime(
        context, profile, state, session_factory=factory(server, budgets), clock=clock
    )
    with open_existing_store(state) as store:
        plan = StateUploads(store).show(plan_id=plan_id).plan
        manifest = read_manifest(store.connection, plan)
        stamp = StateCache(store, runtime.clock).stamp()
        source = StateUploads(store).resume_source(plan.continuation.source_operation_id, stamp)
    with runtime._invocation() as end:
        bound, scope = runtime._bind(plan.scope.owner)
        assert scope == plan.scope
        inputs = capture_upload_input(
            Path(plan.root.anchor),
            manifest,
            bound.credential.secret,
            end=end,
            expected_root=plan.root,
        )
        wanted = source.baseline if baseline is None else baseline
        stages_end = end if window is None else time.monotonic() + window
        if ends is not None:
            ends.append(stages_end)
        return run_stages(runtime, plan, bound, inputs, wanted, stages_end, algorithm)


def planned(data, server, provider, **flags):
    """An interrupted upload and the plan that continues it; the provider will presign again.

    The original upload presigned every file before it stopped, so a continuation presigns the
    files it sends a second time, as a new operation: the fixture provider must allow it.
    """
    source = interrupted(data, server)
    report = prepared(data, server, source, **flags)
    provider.represign = True
    return report


def operation_of(data, plan_id):
    with open_existing_store(data[0]) as store:
        return StateUploads(store).show(plan_id=plan_id).operation


def journal(data, plan_id):
    with open_existing_store(data[0]) as store:
        return StateUploads(store).show(plan_id=plan_id)


# --- what it sends ------------------------------------------------------------------------------


def test_a_continuation_sends_the_file_that_was_left_and_creates_and_links_nothing(
    prepared_input, certificates
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        events, created = list(provider.events), (provider.create_calls, provider.link_calls)
        before, budgets = len(server.requests), []
        record = start(data, server, report.plan_id, budgets=budgets)
        assert record.status == "running" and record.dataset_id == DATASET
        assert provider.events[len(events) :] == ["presign", "put", "confirm"]
        assert (provider.create_calls, provider.link_calls) == created  # the original's alone
        sent = [r for r in server.requests[before:] if r.method != "GET"]
        assert [r.method for r in sent] == ["POST", "PUT", "POST"]
        counters = budgets[0].snapshot()
        assert counters.effect_attempts == 3  # three per file, none for create or link
        assert (counters.create_requests, counters.project_link_requests) == (0, 0)
        assert (counters.presign_requests, counters.put_requests, counters.confirm_requests) == (
            1,
            1,
            1,
        )
        assert counters.upload_bytes == len(b"different") and counters.response_pending == 0
        # One fresh look at the dataset (context, dataset, membership, role) served all the stages.
        assert counters.read_requests == counters.read_attempts == 6
        view = journal(data, report.plan_id)
        assert len(view.intents) == len(view.receipts) == 3
        assert all(receipt.result == "accepted" for receipt in view.receipts)
        assert view.verification is None  # the closing read is another card's
        with open_existing_store(data[0]) as store:
            validate_uploads(store.connection)
        assert set(provider.confirmed) == {f.path for f in data[2].files}


@pytest.mark.parametrize("counts", ["the dataset", "the operation"])
def test_five_of_eight_files_are_presigned_first_put_two_at_a_time_and_confirmed_in_order(
    prepared_input, certificates, counts
):
    data, provider = five_of_eight(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        plan = saved(data, report.plan_id).plan
        assert plan.continuation.file_indices == (3, 4, 5, 6, 7)
        assert plan.continuation.remote_present_count == 3
        events, budgets = len(provider.events), []
        if counts == "the operation":
            provider.count_origin = provider.confirm_calls  # each confirm reports k + 1
        before = len(server.requests)
        record = start(data, server, report.plan_id, budgets=budgets)
        assert record.status == "running"
        assert provider.events[events:] == [
            *["presign"] * 5,
            *["put", "put", "confirm", "confirm"],
            *["put", "put", "confirm", "confirm"],
            *["put", "confirm"],
        ]
        names = [f.path for f in data[2].files]
        assert list(provider.confirmed)[3:] == [names[i] for i in (3, 4, 5, 6, 7)]  # in order
        counters = budgets[0].snapshot()
        assert counters.effect_attempts == 15 == 3 * len(plan.continuation.file_indices)
        assert counters.upload_bytes == sum(data[2].files[i].size for i in (3, 4, 5, 6, 7))
        assert (counters.create_requests, counters.project_link_requests) == (0, 0)
        sent = [r for r in server.requests[before:] if r.method != "GET"]
        assert len(sent) == 15 and not any(r.path.endswith("/datasets") for r in sent)
        view = journal(data, report.plan_id)
        assert len(view.intents) == len(view.receipts) == 15


def test_a_confirm_that_counts_neither_way_makes_the_operation_uncertain_and_is_not_repeated(
    prepared_input, certificates
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        provider.wrong_confirm_count = True
        with pytest.raises(OperationError) as error:
            start(data, server, report.plan_id)
        assert error.value.code == "operation_uncertain"
        assert provider.confirm_calls == 3  # the two of the original and this one: no replay
        record = operation_of(data, report.plan_id)
        assert error.value.operation_id == record.operation_id
        assert (record.status, record.reason) == ("unknown", "request_uncertain")
        view = journal(data, report.plan_id)
        confirm = [i for i in view.intents if i.kind == "confirm"]
        done = {r.intent_id for r in view.receipts if r.result == "accepted"}
        assert len(confirm) == 1 and confirm[0].intent_id not in done


def test_a_file_whose_confirm_had_no_answer_is_sent_again_and_presigned_again(
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
        assert plan.continuation.uncertain_indices == (1,) and plan.continuation.file_indices == (
            1,
            2,
        )
        presigns = provider.presign_calls
        record = start(data, server, report.plan_id)
        assert record.status == "running"
        assert provider.presign_calls == presigns + 2  # two.bin presigned a second time
        assert set(provider.confirmed) == {f.path for f in data[2].files}
        assert provider.confirm_calls == 3  # one.bin of the original, then two.bin and the last


# --- when a stage fails -------------------------------------------------------------------------

FAILURES = {
    "unauthorized": (401, "remote_access_denied"),
    "forbidden": (403, "remote_access_denied"),
    "rate limited": (429, "remote_rate_limited"),
    "server error": (500, "remote_failed"),
}


def break_stage(provider, stage, reply):
    """Make the provider answer ``stage`` of the last file with ``reply`` (its first request)."""
    if stage == "presign":
        provider.route_table[PRESIGN] = reply
    elif stage == "confirm":
        provider.route_table[CONFIRM] = reply
    else:

        def after(name):
            row = provider.presigns[name]
            provider.route_table["/api/v1" + row["upload_url"]] = reply

        provider.after_presign = after


@pytest.mark.parametrize("failure", [*FAILURES, "lost answer"])
@pytest.mark.parametrize("stage", ["presign", "put", "confirm"])
def test_a_stage_that_fails_leaves_the_operation_uncertain_and_is_sent_once(
    prepared_input, certificates, stage, failure
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        if failure == "lost answer":
            reply = Reply(status=200, body=b'{"ok":true}', truncate_at=3)
        else:
            reply = Reply(status=FAILURES[failure][0], body=b"{}")
        break_stage(provider, stage, reply)
        before = len(server.requests)
        with pytest.raises(OperationError) as error:
            start(data, server, report.plan_id)
        assert error.value.code == "operation_uncertain"
        record = operation_of(data, report.plan_id)
        assert error.value.operation_id == record.operation_id
        state = (record.status, record.reason, record.lease)
        assert state == ("unknown", "request_uncertain", None)
        kinds = [f"{r.method} {r.path.split('?')[0].rsplit('/', 1)[-1]}" for r in server.requests]
        sent = [k for k in kinds[before:] if k.split()[0] != "GET"]
        wanted = {"presign": ["POST presign"], "put": ["POST presign", "PUT put"]}
        assert sent == wanted.get(stage, ["POST presign", "PUT put", "POST confirm"])
        with open_existing_store(data[0]) as store:
            validate_uploads(store.connection)
        view = journal(data, report.plan_id)
        accepted = {r.intent_id for r in view.receipts if r.result == "accepted"}
        last = view.intents[-1]
        assert last.kind == stage and last.intent_id not in accepted  # armed, never claimed done


def test_a_fresh_check_that_fails_before_any_stage_is_a_local_cancellation_not_an_uncertainty(
    prepared_input, certificates
):
    data, provider = three_files(prepared_input)
    reads = "/api/v1/auth/me"

    async def admit_then_lose_the_provider(environment):
        check = await environment.current("presign")
        with environment.repository() as repository:
            repository.approve_continuation(
                environment.plan.plan_id,
                environment.plan.digest,
                check,
                acknowledge_unverified_authority=True,
                acknowledge_unpriced_cost=True,
                acknowledge_unconfirmed_effects=False,
            )
        environment.admit(check)
        environment.memo = None  # the next stage must look again
        provider.route_table[reads] = Reply(status=503, body=b"{}")
        return await continue_files(environment)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        sends = len(provider.events)
        with pytest.raises(OperationError) as error:
            start(data, server, report.plan_id, algorithm=admit_then_lose_the_provider)
        assert error.value.code == "remote_failed"  # the read's own code, not an uncertainty
        record = operation_of(data, report.plan_id)
        assert error.value.operation_id == record.operation_id
        assert (record.status, record.reason) == ("cancelled", "local_cancelled")
        assert len(provider.events) == sends  # nothing was sent
        assert journal(data, report.plan_id).intents == ()


def test_a_process_that_does_not_own_the_admission_sends_nothing(prepared_input, certificates):
    data, provider = three_files(prepared_input)

    async def lost_the_race(environment):
        check = await environment.current("presign")
        with environment.repository() as repository:
            repository.approve_continuation(
                environment.plan.plan_id,
                environment.plan.digest,
                check,
                acknowledge_unverified_authority=True,
                acknowledge_unpriced_cost=True,
                acknowledge_unconfirmed_effects=False,
            )
            repository.admit(environment.plan.plan_id, check)  # another process admits first
        assert environment.admit(check) is False  # its owner ids cannot make this one's access
        assert not environment.write_owned
        return await continue_files(environment)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        sends = len(provider.events)
        record = start(data, server, report.plan_id, algorithm=lost_the_race)
        assert record.status == "admitted" and len(provider.events) == sends
        assert journal(data, report.plan_id).intents == ()


def test_the_environment_refuses_a_create_a_link_and_a_stage_of_a_file_it_was_not_given(
    prepared_input, certificates
):
    data, provider = three_files(prepared_input)

    async def probe(environment):
        check = await environment.current("presign")
        for kind in ("create", "project_link"):
            with pytest.raises(YorungeError) as error:
                await environment.current(kind)
            assert error.value.code == "invalid_request"
        with environment.repository() as repository:
            repository.approve_continuation(
                environment.plan.plan_id,
                environment.plan.digest,
                check,
                acknowledge_unverified_authority=True,
                acknowledge_unpriced_cost=True,
                acknowledge_unconfirmed_effects=False,
            )
        environment.admit(check)
        for kind in ("create", "project_link"):
            with pytest.raises(YorungeError) as error:
                environment.prepare(kind)
            assert error.value.code == "invalid_request"
        for index in (0, 1, 7, None):  # only file 2 was selected
            with pytest.raises(YorungeError) as error:
                environment.prepare("presign", index)
            assert error.value.code == "invalid_request"
        with pytest.raises(YorungeError) as error:  # a put before its presign has no upload
            environment.prepare("put", 2)
        assert error.value.code == "invalid_response"
        with pytest.raises(YorungeError) as error:  # nothing was presigned: nothing to validate
            environment.validate_uploads()
        assert error.value.code == "invalid_response"
        return environment.record

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        sends = len(provider.events)
        record = start(data, server, report.plan_id, algorithm=probe)
        assert record.status == "admitted" and len(provider.events) == sends


# --- what must never be written down or said ----------------------------------------------------

VOLATILE = ("objects/blob", "upload/put?key=", "created_dataset")


def stored_bytes(state):
    return b"".join(p.read_bytes() for p in sorted(Path(state).rglob("*")) if p.is_file())


def test_no_key_and_no_volatile_provider_value_reaches_the_journal_the_log_or_the_result(
    prepared_input, certificates, caplog
):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        with caplog.at_level(logging.DEBUG):
            record = start(data, server, report.plan_id)
        view = journal(data, report.plan_id)
        # The continuation's own journal: intents and receipts name neither a provider's object
        # key, nor a signed URL, nor the dataset it was created as, nor the key it is sent with.
        own = b"".join(x.encoded() for x in (*view.intents, *view.receipts)).decode()
        assert not any(marker in own for marker in VOLATILE)
        shown = own + repr(record) + record.model_dump_json() + caplog.text
        assert SECRET not in shown and not any(marker in shown for marker in VOLATILE[:2])
        # The whole state directory: the key is never stored, and no provider object key is.
        everything = stored_bytes(data[0])
        assert SECRET.encode() not in everything
        assert b"objects/blob" not in everything and b"upload/put?key=" not in everything


@pytest.mark.parametrize("stage", ["presign", "put", "confirm"])
def test_a_failure_says_nothing_of_what_the_provider_answered(prepared_input, certificates, stage):
    data, provider = three_files(prepared_input)
    canary = "PRIVATE-PROVIDER-ANSWER-CANARY"
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        break_stage(
            provider, stage, Reply(status=500, body=f'{{"detail":"{canary} {SECRET}"}}'.encode())
        )
        with pytest.raises(OperationError) as error:
            start(data, server, report.plan_id)
        shown = "".join(traceback.format_exception(error.value)) + repr(error.value)
        assert canary not in shown and SECRET not in shown
        assert error.value.__cause__ is None and error.value.__context__ is None
        assert canary.encode() not in stored_bytes(data[0])


# --- when it is cancelled -----------------------------------------------------------------------


def test_a_cancellation_before_anything_was_armed_cancels_the_operation_locally(
    prepared_input, certificates
):
    data, provider = three_files(prepared_input)

    async def cancelled_after_admission(environment):
        check = await environment.current("presign")
        with environment.repository() as repository:
            repository.approve_continuation(
                environment.plan.plan_id,
                environment.plan.digest,
                check,
                acknowledge_unverified_authority=True,
                acknowledge_unpriced_cost=True,
                acknowledge_unconfirmed_effects=False,
            )
        environment.admit(check)
        raise asyncio.CancelledError

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        sends = len(provider.events)
        with pytest.raises(asyncio.CancelledError):  # a cancelled task stays cancelled
            start(data, server, report.plan_id, algorithm=cancelled_after_admission)
        record = operation_of(data, report.plan_id)
        assert (record.status, record.reason) == ("cancelled", "local_cancelled")
        assert len(provider.events) == sends and journal(data, report.plan_id).intents == ()


@pytest.mark.parametrize(
    "interruption,seen",
    [(asyncio.CancelledError, asyncio.CancelledError), (KeyboardInterrupt, OperationError)],
    ids=["a cancelled task", "an interrupt"],
)
def test_a_cancellation_after_a_permit_was_committed_leaves_the_operation_uncertain(
    prepared_input, certificates, monkeypatch, interruption, seen
):
    from yorunge.adapters.upload_continuation import ContinuationStages

    data, provider = three_files(prepared_input)
    original = ContinuationStages.arm

    def arm_then_stop(environment, check, kind, index=None):
        result = original(environment, check, kind, index)
        if kind == "presign":
            raise interruption  # the intent is durable; nothing has been sent
        return result

    monkeypatch.setattr(ContinuationStages, "arm", arm_then_stop)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        sends = len(provider.events)
        with pytest.raises(seen) as error:
            start(data, server, report.plan_id)
        if seen is OperationError:  # the interrupt is reported as the operation's uncertainty
            assert error.value.code == "operation_uncertain"
            assert error.value.operation_id == operation_of(data, report.plan_id).operation_id
        record = operation_of(data, report.plan_id)
        assert (record.status, record.reason) == ("unknown", "request_uncertain")
        assert len(provider.events) == sends  # the permit was never used: and never will be
        view = journal(data, report.plan_id)
        assert len(view.intents) == 1 and not view.receipts
        with open_existing_store(data[0]) as store:
            validate_uploads(store.connection)


# --- when the provider misbehaves around the stages ---------------------------------------------


def test_a_put_that_fails_ends_the_continuation_before_any_confirm_or_later_batch(
    prepared_input, certificates
):
    data, provider = five_of_eight(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        before = len(provider.events)
        provider.fail_put_name = "f04.bin"  # the first file of the first batch: 503 after storing
        with pytest.raises(OperationError) as error:
            start(data, server, report.plan_id)
        assert error.value.code == "operation_uncertain"
        events = provider.events[before:]
        assert events[:5] == ["presign"] * 5 and set(events[5:]) <= {"put"}
        assert 1 <= events.count("put") <= 2  # the batch's two workers, never a later batch
        assert "confirm" not in events
        record = operation_of(data, report.plan_id)
        assert (record.status, record.reason) == ("unknown", "request_uncertain")
        with open_existing_store(data[0]) as store:
            validate_uploads(store.connection)


def test_presigns_that_share_an_object_key_are_refused_before_any_put(prepared_input, certificates):
    data = three_files(prepared_input)[0]
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    lose_confirm_of(provider, "one.bin")  # the second and the third file remain
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        before = len(provider.events)
        provider.duplicate_keys = True  # two files presigned onto one object key
        with pytest.raises(OperationError) as error:
            start(data, server, report.plan_id)
        assert error.value.code == "operation_uncertain"
        assert error.value.reason_code == "invalid_response"
        assert provider.events[before:] == ["presign", "presign"]  # nothing was put
        record = operation_of(data, report.plan_id)
        assert (record.status, record.reason) == ("unknown", "request_uncertain")


def test_the_dataset_a_continuation_extends_is_its_plans_and_no_other(prepared_input, certificates):
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        view = saved(data, report.plan_id)
        with open_existing_store(data[0]) as store:
            stamp = StateCache(store, UploadResumeRuntime(*data[3:5], data[0]).clock).stamp()
            source = StateUploads(store).resume_source(
                view.plan.continuation.source_operation_id, stamp
            )
        other = source.baseline.model_copy(update={"id": "00000000-0000-4000-8000-0000000000bb"})
        before = len(server.requests)
        with pytest.raises(YorungeError) as error:
            start(data, server, report.plan_id, baseline=other)
        assert error.value.code == "invalid_request"
        assert len(server.requests) == before and operation_of(data, report.plan_id) is None


# --- the count a confirm reports keeps its meaning through the operation ------------------------


def count_by(provider, answers):
    """The provider takes each item as usual but reports the counts of ``answers`` in turn."""
    real, given = provider.route_table[CONFIRM], iter(answers)

    def confirm(request, count):
        real(request, count)
        return reply({"created": 1, "actual_count": next(given), "batch_duplicates": 0})

    provider.route_table[CONFIRM] = confirm


@pytest.mark.parametrize(
    "answers",
    [[1, 5], [4, 2]],
    ids=["an item came in after the first", "the total did not move after the first"],
)
def test_a_count_that_changes_its_meaning_stops_the_continuation_and_sends_no_more(
    prepared_input, certificates, answers
):
    # Five of eight files remain; the dataset held three. The first confirm reports 1 (the
    # operation's own) or 4 (the dataset's); the second reports a number of the other kind.
    data, provider = five_of_eight(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        confirms = provider.confirm_calls
        count_by(provider, answers)
        with pytest.raises(OperationError) as error:
            start(data, server, report.plan_id)
        assert error.value.code == "operation_uncertain"
        assert error.value.reason_code == "invalid_response"
        assert provider.confirm_calls == confirms + 2  # the second was sent, none after it
        record = operation_of(data, report.plan_id)
        assert (record.status, record.reason) == ("unknown", "request_uncertain")
        view = journal(data, report.plan_id)
        done = {r.intent_id for r in view.receipts if r.result == "accepted"}
        confirm = [i for i in view.intents if i.kind == "confirm"]
        assert [i.intent_id in done for i in confirm] == [True, False]
        with open_existing_store(data[0]) as store:
            validate_uploads(store.connection)


# --- time, deadlines and what changes between two stages ----------------------------------------


class Skewed:
    """A clock a test moves forward: the wall clock and the monotonic clock together."""

    def __init__(self):
        self.skew = 0.0

    def now(self):
        return datetime.now(UTC) + timedelta(seconds=self.skew)

    def monotonic(self):
        return time.monotonic() + self.skew


def after_presign(monkeypatch, act):
    """Run ``act(environment)`` once the first presign of the continuation has been published."""
    original = ContinuationStages.publish

    def publish(environment, outcome):
        original(environment, outcome)
        if outcome.upload is not None:
            act(environment)

    monkeypatch.setattr(ContinuationStages, "publish", publish)


@pytest.mark.parametrize(
    "seconds,reads",
    [(20, 6), (28, 12)],
    ids=["a check of 20 s serves the next stages", "a check of 28 s is looked at again"],
)
def test_one_fresh_check_serves_twenty_five_seconds_of_stages(
    prepared_input, certificates, monkeypatch, seconds, reads
):
    data, provider = three_files(prepared_input)
    clock, budgets = Skewed(), []

    def later(_):
        clock.skew += seconds

    after_presign(monkeypatch, later)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        record = start(data, server, report.plan_id, clock=clock, budgets=budgets)
        assert record.status == "running"
        # A look at the dataset is six reads: the context, the dataset, its membership and its role.
        assert budgets[0].snapshot().read_requests == reads


def test_every_permit_is_armed_within_the_end_of_the_run(prepared_input, certificates, monkeypatch):
    data, provider = three_files(prepared_input)
    seen, ends = [], []
    original = StateUploads.arm

    def arm(repository, *arguments, **keywords):
        seen.append(keywords["total_end"])
        return original(repository, *arguments, **keywords)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)  # the original upload armed its own permits
        monkeypatch.setattr(StateUploads, "arm", arm)
        start(data, server, report.plan_id, window=300, ends=ends)
    assert len(ends) == 1 and seen == ends * 3  # presign, put and confirm of the one file


def test_a_run_given_more_than_fifteen_minutes_is_held_to_fifteen(prepared_input, certificates):
    data, provider = three_files(prepared_input)

    async def nothing(environment):
        return "the budget was built"

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        answer = start(data, server, report.plan_id, window=1000, algorithm=nothing)
    assert answer == "the budget was built"


def test_a_lease_close_to_its_end_is_renewed_before_a_slow_look_at_the_dataset(
    prepared_input, certificates
):
    data, provider = three_files(prepared_input)
    clock = Skewed()

    async def aged_lease(environment):
        check = await environment.current("presign")
        with environment.repository() as repository:
            repository.approve_continuation(
                environment.plan.plan_id,
                environment.plan.digest,
                check,
                acknowledge_unverified_authority=True,
                acknowledge_unpriced_cost=True,
                acknowledge_unconfirmed_effects=False,
            )
        environment.admit(check)
        clock.skew += 128  # the 150 s lease has 22 s left, and the check is old
        slow = [True]

        def one_slow_request():
            if slow:
                slow.clear()
                clock.skew += 27  # the dataset is looked at for 27 s: longer than the lease had

        provider.on_request = one_slow_request
        return await continue_files(environment)

    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        sends = len(provider.events)
        record = start(data, server, report.plan_id, clock=clock, algorithm=aged_lease)
        assert record.status == "running"
        assert provider.events[sends:] == ["presign", "put", "confirm"]


@pytest.mark.parametrize("skew", [200, -10], ids=["the lease ran out", "the clock went back"])
def test_a_lease_that_is_lost_between_two_stages_stops_the_continuation_unsent(
    prepared_input, certificates, monkeypatch, skew
):
    data, provider = three_files(prepared_input)
    clock = Skewed()

    def move(_):
        clock.skew += skew

    after_presign(monkeypatch, move)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        sends = len(provider.events)
        with pytest.raises(OperationError) as error:
            start(data, server, report.plan_id, clock=clock)
        assert error.value.code == "operation_uncertain"
        assert error.value.reason_code == "operation_lease_lost"
        assert provider.events[sends:] == ["presign"]  # no put, no confirm


def test_a_key_rotated_between_two_stages_stops_the_continuation_before_the_next_send(
    prepared_input, certificates, monkeypatch
):
    data, provider = three_files(prepared_input)

    def rotate(environment):
        old = environment.bound.credential  # another process has seen the key change
        new = ResolvedCredential(old.reference, old.target, SecretValue("a-rotated-key-canary"))
        with open_existing_store(data[0]) as store:
            StateCredentialRegistry(store).observe(new)

    after_presign(monkeypatch, rotate)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        sends = len(provider.events)
        with pytest.raises(OperationError) as error:
            start(data, server, report.plan_id)
        assert error.value.code == "operation_uncertain"
        assert error.value.reason_code == "state_changed"
        assert provider.events[sends:] == ["presign"]


def test_a_folder_that_changes_between_two_stages_stops_the_continuation_before_the_next_send(
    prepared_input, certificates, monkeypatch
):
    data, provider = three_files(prepared_input)

    def change(_):
        (data[1] / "ölçüm.bin").write_bytes(b"changed after it was presigned")

    after_presign(monkeypatch, change)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        sends = len(provider.events)
        with pytest.raises(OperationError) as error:
            start(data, server, report.plan_id)
        assert error.value.code == "operation_uncertain"
        assert error.value.reason_code == "input_changed"
        assert provider.events[sends:] == ["presign"]
