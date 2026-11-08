"""The public commands carry a continuation from its saved plan to a proved dataset (P02-3i).

Real files, a real store, a real TLS provider and the product's own interrupted upload: a source
that stopped uncertain is continued by a plan the resume report prepared. From there every step is a
public call (``show``, ``review``, ``list``, ``approve``, ``start``, ``reconcile``, ``revoke``) that
answers with a summary of the continuation and, where it is told to, hears nothing but the user's
own words: the digest they confirmed and the acknowledgements the plan asks for.
"""

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial

import pytest

from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.http_server import TlsServer
from tests.fixtures.upload_provider import UploadProvider
from tests.integration.test_upload_file_workflow import many
from tests.integration.test_upload_original import factory
from tests.integration.test_upload_preparation import certificates as certificates
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_public_api import public_inputs as public_inputs
from tests.integration.test_upload_resume_observation import interrupted, lose_confirm_of
from tests.integration.test_upload_resume_prepare import prepared
from yorunge import api
from yorunge.adapters import upload_api
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_continuation_approval import approve_continuation_plan
from yorunge.adapters.upload_continuation_start import run_upload_continuation
from yorunge.adapters.upload_public import resume_hint
from yorunge.adapters.upload_reconciliation import reconcile_upload
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_resume import UploadResumeRuntime
from yorunge.application.upload_progress import UploadProgress, observe_upload
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.upload_public import DatasetUploadSummaryV3


@dataclass
class Rig:
    data: tuple
    config: object
    provider: UploadProvider
    server: TlsServer
    source: str
    report: object
    budgets: list

    @property
    def state(self):
        return self.data[0]

    @property
    def plan_id(self):
        return self.report.plan_id

    @property
    def digest(self):
        return self.report.plan_digest

    def approve(self, **changes):
        options = dict(
            config=self.config,
            state_dir=self.state,
            accept_unverified_authority=True,
            accept_unpriced_cost=True,
        )
        return api.approve_dataset_upload(self.plan_id, self.digest, **(options | changes))

    def start(self):
        return api.start_dataset_upload(self.plan_id, config=self.config, state_dir=self.state)

    def show(self):
        return api.show_dataset_upload(plan_id=self.plan_id, state_dir=self.state).data


@contextmanager
def interrupted_world(
    public_inputs, certificates, monkeypatch, *, remembered=True, prepare=True, **flags
):
    """An upload that stopped after two of three files, and the plan that continues it."""
    inputs, _, config = public_inputs
    data = many(inputs)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    lose_confirm_of(provider, "two.bin", remembered=remembered)
    budgets: list = []
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        report = prepared(data, server, source, **flags) if prepare else None
        provider.represign = True
        build = factory(server, budgets)
        monkeypatch.setattr(
            upload_api,
            "UploadResumeRuntime",
            lambda context, profile, state_dir: UploadResumeRuntime(
                context, profile, state_dir, session_factory=build
            ),
        )
        monkeypatch.setattr(
            upload_api,
            "approve_continuation_plan",
            partial(approve_continuation_plan, session_factory=build),
        )
        monkeypatch.setattr(
            upload_api,
            "run_upload_continuation",
            partial(run_upload_continuation, session_factory=build),
        )
        monkeypatch.setattr(
            upload_api, "reconcile_upload", partial(reconcile_upload, session_factory=build)
        )
        yield Rig(data, config, provider, server, source, report, budgets)


def code_of(action):
    with pytest.raises(YorungeError) as error:
        action()
    return error.value.code


# --- the plan is a continuation, in every read ----------------------------------------------------


def test_a_prepared_continuation_is_shown_reviewed_and_listed_as_one(
    public_inputs, certificates, monkeypatch
):
    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        shown = rig.show()
        assert type(shown) is DatasetUploadSummaryV3 and shown.plan_status != "draft"
        assert (shown.continuation_of, shown.operation_id, shown.approval_status) == (
            rig.source,
            None,
            None,
        )
        assert (shown.continuation_files, shown.remote_present_files, shown.uncertain_files) == (
            1,
            2,
            0,
        )
        review = api.review_dataset_upload(rig.plan_id, state_dir=rig.state).data
        assert review.summary == shown and review.manifest.file_count == 3
        assert review.request_limits.files == 1 and review.request_limits.max_create == 0
        page = api.list_dataset_uploads(state_dir=rig.state).data
        assert shown in page.uploads and len(page.uploads) == 2  # the source's plan, and this one
        with open_existing_store(rig.state) as store:
            assert StateUploads(store).show(plan_id=rig.plan_id).operation is None  # reads only


# --- approve --------------------------------------------------------------------------------------


def test_approve_records_the_digest_and_the_acknowledgements_the_plan_asked_for(
    public_inputs, certificates, monkeypatch
):
    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        sent = len(rig.provider.events)
        approved = rig.approve().data
        assert type(approved) is DatasetUploadSummaryV3
        assert (approved.approval_status, approved.operation_id) == ("approved", None)
        assert len(rig.provider.events) == sent  # an approval sends nothing of the upload
        # approving again is a conflict, and so is starting nothing: the first approval stands
        assert code_of(rig.approve) == "operation_conflict"


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"accept_unverified_authority": False}, "approval_required"),
        ({"accept_unpriced_cost": False}, "approval_required"),
        ({"accept_unconfirmed_effects": True}, "invalid_request"),  # this plan has none
    ],
    ids=["authority", "cost", "unneeded effects flag"],
)
def test_approve_asks_for_exactly_the_acknowledgements_the_plan_needs(
    public_inputs, certificates, monkeypatch, changes, code
):
    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        requests = len(rig.server.requests)
        assert code_of(lambda: rig.approve(**changes)) == code
        assert len(rig.server.requests) == requests  # refused before the provider was asked
        assert rig.show().approval_status is None


def test_approve_refuses_another_digest_than_the_one_that_was_reviewed(
    public_inputs, certificates, monkeypatch
):
    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        wrong = "0" * 64
        assert (
            code_of(
                lambda: api.approve_dataset_upload(
                    rig.plan_id,
                    wrong,
                    accept_unverified_authority=True,
                    accept_unpriced_cost=True,
                    config=rig.config,
                    state_dir=rig.state,
                )
            )
            == "upload_plan_not_valid"
        )
        assert rig.show().approval_status is None


def test_an_original_plan_has_no_unconfirmed_files_to_acknowledge(
    public_inputs, certificates, monkeypatch
):
    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        original = api.show_dataset_upload(operation_id=rig.source, state_dir=rig.state).data
        before = len(rig.server.requests)
        refused = code_of(
            lambda: api.approve_dataset_upload(
                original.plan_id,
                original.plan_digest,
                accept_unverified_authority=True,
                accept_unpriced_cost=True,
                accept_unconfirmed_effects=True,
                config=rig.config,
                state_dir=rig.state,
            )
        )
        # a choice that exists only in a continuation is a bad request, whatever else is true of
        # the plan, and nothing is asked of the provider
        assert refused == "invalid_request" and len(rig.server.requests) == before


def test_a_continuation_whose_files_include_unconfirmed_ones_needs_its_own_acknowledgement(
    public_inputs, certificates, monkeypatch
):
    with interrupted_world(
        public_inputs, certificates, monkeypatch, remembered=False, accept_unconfirmed_effects=True
    ) as rig:
        assert rig.show().uncertain_files == 1
        assert code_of(rig.approve) == "approval_required"
        assert rig.show().approval_status is None
        approved = rig.approve(accept_unconfirmed_effects=True).data
        assert approved.approval_status == "approved"


# --- start ----------------------------------------------------------------------------------------


def test_start_sends_only_what_was_left_and_the_summary_names_the_proof(
    public_inputs, certificates, monkeypatch
):
    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        rig.approve()
        sent = len(rig.provider.events)
        seen: list[UploadProgress] = []
        with observe_upload(seen.append):
            started = rig.start().data
        assert type(started) is DatasetUploadSummaryV3
        assert (started.operation_status, started.verification_level) == ("succeeded", "metadata")
        assert started.operation_id is not None and started.plan_id == rig.plan_id
        assert rig.provider.events[sent:] == ["presign", "put", "confirm"]  # one file, nothing else
        assert rig.provider.create_calls == 1  # the root's create is the only one there ever was
        # the counter counts the one file the continuation sends, not the manifest's three
        assert seen and seen[-1].total_files == 1 and seen[-1].confirmed_files == 1
        assert seen[-1].total_bytes == seen[-1].confirmed_bytes == seen[-1].source_bytes
        again = rig.start().data  # a started plan is a local lookup: nothing is sent twice
        assert again == started and rig.provider.events[sent:] == ["presign", "put", "confirm"]


def test_start_without_an_approval_is_refused_and_sends_nothing(
    public_inputs, certificates, monkeypatch
):
    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        sent, requests = len(rig.provider.events), len(rig.server.requests)
        assert code_of(rig.start) == "approval_required"
        assert (len(rig.provider.events), len(rig.server.requests)) == (sent, requests)


def test_revoke_takes_the_approval_back_and_a_revoked_plan_does_not_start(
    public_inputs, certificates, monkeypatch
):
    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        rig.approve()
        revoked = api.revoke_dataset_upload(rig.plan_id, state_dir=rig.state).data
        assert type(revoked) is DatasetUploadSummaryV3 and revoked.approval_status == "revoked"
        assert code_of(rig.start) == "approval_required"


# --- reconcile ------------------------------------------------------------------------------------


def test_reconcile_of_a_continuation_that_left_no_proof_proves_it_in_the_same_operation(
    public_inputs, certificates, monkeypatch
):
    from yorunge.adapters.upload_continuation import ContinuationStages

    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        rig.approve()
        real = ContinuationStages.verify

        async def fails(self):
            raise OperationError("operation_uncertain", self.record.operation_id)

        monkeypatch.setattr(ContinuationStages, "verify", fails)
        with pytest.raises(OperationError) as stopped:
            rig.start()
        monkeypatch.setattr(ContinuationStages, "verify", real)
        operation = stopped.value.operation_id
        assert stopped.value.code == "operation_uncertain"
        unknown = api.show_dataset_upload(operation_id=operation, state_dir=rig.state).data
        assert type(unknown) is DatasetUploadSummaryV3 and unknown.operation_status != "succeeded"
        proved = api.reconcile_dataset_upload(
            operation, accept_unverified_read=True, config=rig.config, state_dir=rig.state
        ).data
        assert type(proved) is DatasetUploadSummaryV3
        assert (proved.operation_id, proved.operation_status) == (operation, "succeeded")
        assert proved.verification_level == "metadata"


# --- resume ---------------------------------------------------------------------------------------


def rows(state):
    tables = ("upload_plans", "upload_approvals", "upload_operations", "upload_controls")
    tables += ("upload_stage_intents", "upload_stage_receipts", "upload_verifications")
    with open_existing_store(state) as store:
        return [
            store.connection.execute(f"SELECT * FROM {t} ORDER BY 1,2").fetchall() for t in tables
        ]


def test_the_default_resume_is_a_read_only_report_of_what_is_left(
    public_inputs, certificates, monkeypatch
):
    with interrupted_world(public_inputs, certificates, monkeypatch, prepare=False) as rig:
        stored, requests = rows(rig.state), len(rig.server.requests)
        result = api.resume_dataset_upload(
            rig.source, accept_unverified_read=True, config=rig.config, state_dir=rig.state
        )
        report = result.data
        assert report.kind == "dataset_upload_resume_report" and report.eligible
        assert (report.blockers, report.recommended_action) == ((), "prepare")
        counts = report.observation.class_counts
        assert (counts.confirmed, counts.observed, counts.pending_clean) == (1, 1, 1)
        assert (report.observation.send_files, report.plan_id) == (1, None)
        assert all(r.method == "GET" for r in rig.server.requests[requests:])
        assert rows(rig.state) == stored  # nothing was saved, frozen or admitted


def test_a_resume_that_would_read_the_dataset_needs_the_humans_choice_first(
    public_inputs, certificates, monkeypatch
):
    with interrupted_world(public_inputs, certificates, monkeypatch, prepare=False) as rig:
        requests = len(rig.server.requests)
        with pytest.raises(OperationError) as refused:
            api.resume_dataset_upload(rig.source, config=rig.config, state_dir=rig.state)
        assert (
            refused.value.code == "approval_required" and refused.value.operation_id == rig.source
        )
        assert len(rig.server.requests) == requests  # not one request without the choice


def test_prepare_saves_the_plan_and_the_commands_that_follow_find_it(
    public_inputs, certificates, monkeypatch
):
    with interrupted_world(public_inputs, certificates, monkeypatch, prepare=False) as rig:
        result = api.resume_dataset_upload(
            rig.source,
            prepare=True,
            accept_unverified_read=True,
            config=rig.config,
            state_dir=rig.state,
        )
        plan_id = result.data.plan_id
        assert plan_id is not None and result.data.eligible
        shown = api.show_dataset_upload(plan_id=plan_id, state_dir=rig.state).data
        assert type(shown) is DatasetUploadSummaryV3 and shown.continuation_of == rig.source


def test_a_source_that_cannot_be_continued_is_a_report_and_a_refusal_naming_why(
    public_inputs, certificates, monkeypatch
):
    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        rig.approve()
        started = rig.start().data  # the continuation finishes: its source is history now
        assert started.operation_status == "succeeded"
        stored = rows(rig.state)
        report = api.resume_dataset_upload(
            rig.source, accept_unverified_read=True, config=rig.config, state_dir=rig.state
        ).data
        assert not report.eligible and "source_superseded" in report.blockers
        assert report.related_operation_id == started.operation_id  # the one a person looks at
        assert report.observation is None  # nothing was read of the provider
        with pytest.raises(OperationError) as refused:
            api.resume_dataset_upload(
                rig.source,
                prepare=True,
                accept_unverified_read=True,
                config=rig.config,
                state_dir=rig.state,
            )
        assert refused.value.code == "continuation_not_possible"
        assert refused.value.operation_id == rig.source
        assert refused.value.blockers == tuple(report.blockers)  # the refusal says the same
        assert refused.value.envelope()["details"]["blockers"] == list(report.blockers)
        assert rows(rig.state) == stored


@pytest.mark.parametrize(
    "changes",
    [
        {"prepare": 1},
        {"accept_unverified_read": None},
        {"accept_unconfirmed_effects": True},  # only with prepare
        {"state_dir": "not-a-path"},
        {"config": "not-a-path"},
    ],
)
def test_resume_judges_its_arguments_before_anything_is_read(
    public_inputs, certificates, monkeypatch, changes
):
    with interrupted_world(public_inputs, certificates, monkeypatch, prepare=False) as rig:
        requests = len(rig.server.requests)
        options = (
            dict(accept_unverified_read=True, config=rig.config, state_dir=rig.state) | changes
        )
        assert (
            code_of(lambda: api.resume_dataset_upload(rig.source, **options)) == "invalid_request"
        )
        assert len(rig.server.requests) == requests


def test_resume_of_an_operation_that_does_not_exist_is_not_found_and_names_it(
    public_inputs, certificates, monkeypatch
):
    unknown = "00000000-0000-4000-8000-0000000000aa"
    with interrupted_world(public_inputs, certificates, monkeypatch, prepare=False) as rig:
        with pytest.raises(OperationError) as refused:
            api.resume_dataset_upload(
                unknown, accept_unverified_read=True, config=rig.config, state_dir=rig.state
            )
        assert refused.value.code == "operation_not_found" and refused.value.operation_id == unknown


# --- show tells an unknown operation what to do next, from its own journal ------------------------


def cli_show(capsys, state, operation_id, *extra):
    from yorunge.cli import main

    code = main(
        ["datasets", "upload", "show", "--operation-id", operation_id, "--state-dir", str(state)]
        + list(extra)
    )
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_show_of_an_unknown_source_points_at_the_resume_report(
    public_inputs, certificates, monkeypatch, capsys
):
    with interrupted_world(public_inputs, certificates, monkeypatch, prepare=False) as rig:
        stored, requests = rows(rig.state), len(rig.server.requests)
        code, out, err = cli_show(capsys, rig.state, rig.source)
        assert code == 0 and err == ""
        assert (
            f"Devam için: yorunge datasets upload resume --operation-id {rig.source} "
            "--accept-unverified-read"
        ) in out
        assert "salt okuma raporudur" in out and "Devam şu an mümkün değil" not in out
        assert len(rig.server.requests) == requests  # the hint is the journal's, not the provider's
        assert rows(rig.state) == stored


@pytest.mark.parametrize(
    "failure",
    [
        TypeError("PRIVATE"),
        KeyError("PRIVATE"),
        RuntimeError("PRIVATE"),
        sqlite3.DatabaseError("x"),
    ],
    ids=["type", "key", "runtime", "sqlite"],
)
def test_the_hint_of_show_is_silence_for_anything_a_hostile_row_can_raise(
    public_inputs, certificates, monkeypatch, capsys, failure
):
    """The hint is advice added to a summary that was already made: it never fails `show`."""

    def broken(*arguments, **keywords):
        raise failure

    with interrupted_world(public_inputs, certificates, monkeypatch, prepare=False) as rig:
        monkeypatch.setattr(StateUploads, "resume_source", broken)
        assert resume_hint(rig.state, rig.source) is None
        code, out, err = cli_show(capsys, rig.state, rig.source)
        assert code == 0 and err == "" and "Devam için" not in out and "PRIVATE" not in out
        assert f"İş: {rig.source}" in out  # the summary itself is there, as it always was


def clock_row(state):
    with open_existing_store(state) as store:
        return store.connection.execute(
            "SELECT identity_epoch,clock_generation,high_watermark,anomaly_active,"
            "mutation_revision FROM cache_clock WHERE singleton=1"
        ).fetchone()


def dump(state):
    with open_existing_store(state) as store:
        return list(store.connection.iterdump())


def test_the_hint_of_show_reads_and_writes_nothing_even_on_a_clock_that_ran_ahead(
    public_inputs, certificates, monkeypatch, capsys
):
    """`show` is a local read: the hint added to its text must not record the clock (a later
    `approve` or `start` compares plans with the generation a write of the clock could bump)."""
    import time
    from datetime import UTC, datetime, timedelta

    from yorunge.adapters import upload_public

    class Clock:
        def __init__(self, hours):
            self.hours = hours

        def now(self):
            return datetime.now(UTC) + timedelta(hours=self.hours)

        def monotonic(self):
            return time.monotonic()

    with interrupted_world(public_inputs, certificates, monkeypatch, prepare=False) as rig:
        before, stored = clock_row(rig.state), dump(rig.state)
        for hours in (0, 1, -1):  # now, an hour ahead, and behind what the store has seen
            monkeypatch.setattr(upload_public, "SystemClock", lambda hours=hours: Clock(hours))
            code, out, _ = cli_show(capsys, rig.state, rig.source)
            assert code == 0 and "Devam için:" in out
            assert clock_row(rig.state) == before and dump(rig.state) == stored


def test_the_json_of_show_is_the_summary_and_nothing_added(
    public_inputs, certificates, monkeypatch, capsys
):
    import json

    with interrupted_world(public_inputs, certificates, monkeypatch, prepare=False) as rig:
        code, out, _ = cli_show(capsys, rig.state, rig.source, "--output", "json")
        shown = api.show_dataset_upload(operation_id=rig.source, state_dir=rig.state)
        assert code == 0 and json.loads(out)["data"] == json.loads(shown.data.encoded())
        assert "resume" not in out  # machine output has no advice in it


def test_show_of_a_source_with_a_continuation_names_the_continuation(
    public_inputs, certificates, monkeypatch, capsys
):
    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        rig.approve()
        started = rig.start().data
        code, out, _ = cli_show(capsys, rig.state, rig.source)
        assert code == 0 and "Devam şu an mümkün değil (yerel kayda göre):" in out
        assert "- source_superseded:" in out
        assert f"Devamı: {started.operation_id}" in out
        assert f"show --operation-id {started.operation_id}" in out
