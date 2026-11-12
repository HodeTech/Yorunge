"""What the journal alone says of a source, and that nothing is asked of the provider then.

The histories are the stored ones of ``tests/fixtures/continuation_history.py`` in a real store; the
runtime is given a session factory that fails the test if it is ever called. A source that cannot be
continued is reported (exit 0) and refused by ``--prepare``, without a single request.
"""

import sqlite3

import pytest

from tests.fixtures.continuation_history import (
    BASELINE_DIGEST,
    DATASET_ID,
    FIRST,
    build,
    install,
)
from tests.fixtures.continuation_lifecycle import dump
from yorunge.adapters.capability_cache import StateCache
from yorunge.adapters.state import DB_NAME, open_store
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_resume import UploadResumeRuntime
from yorunge.adapters.upload_store import quota_used
from yorunge.domain.capabilities import instant
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.models import Profile
from yorunge.domain.upload_resume import ContinuationNotPossible
from yorunge.domain.upload_resume_report import continuation_added_payload_bytes


def root_of(lifecycle):
    return lifecycle.root["record"]["operation_id"]


def forbidden(key, budget):
    pytest.fail("the provider was asked although the journal blocks the source")


def runtime(lifecycle):
    return UploadResumeRuntime(
        lifecycle.bound.context,
        Profile(platform_key_env="TEST_PLATFORM_KEY"),
        lifecycle.root_dir,
        session_factory=forbidden,
        clock=lifecycle.clock,
    )


def resume(lifecycle, source, **flags):
    return runtime(lifecycle).resume(source, accept_unverified_read=True, **flags)


def state(lifecycle):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        return dump(store)


def clock_row(lifecycle):
    """The durable clock: high watermark, generation, anomaly (a read must not move any of them)."""
    with open_store(lifecycle.root_dir, timeout=60) as store:
        return store.connection.execute("SELECT * FROM cache_clock").fetchall()


# The sources: a name, how the store is made, who is reported on, and what the journal says.
def install_first(lifecycle, **spec):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        install(store, build(lifecycle.root, 1, **spec))


def sources():
    return {
        "an admitted continuation, its lease over": (
            {"status": "admitted"},
            True,
            ("source_ineligible",),
            "none",
        ),
        "a continuation that succeeded": (
            {"status": "succeeded"},
            False,
            ("source_terminal", "reconcile_available"),
            "none",
        ),
        "a continuation that failed": (
            {"status": "failed"},
            False,
            ("source_terminal", "known_negative"),  # a refused stage is a known negative
            "none",
        ),
        "a continuation that was cancelled": (
            {"status": "cancelled"},
            False,
            ("source_terminal",),
            "none",
        ),
        "a continuation that still runs": (
            {"status": "running"},
            False,
            ("source_active",),
            "wait",
        ),
    }


@pytest.mark.parametrize("case", sources().values(), ids=sources())
def test_a_source_the_journal_rules_out_is_reported_without_asking_the_provider(lifecycle, case):
    spec, after_the_lease, blockers, action = case
    install_first(lifecycle, **spec)
    if after_the_lease:
        lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")
    stored, clock = state(lifecycle), clock_row(lifecycle)
    report = resume(lifecycle, FIRST)
    assert report.blockers == blockers
    assert not report.eligible
    assert report.observation is None
    assert report.recommended_action == action
    assert report.dataset_id == DATASET_ID
    assert report.related_operation_id is None
    assert report.plan_id is None
    assert state(lifecycle) == stored  # a report writes nothing
    assert clock_row(lifecycle) == clock  # not even the clock's high watermark


def test_a_report_on_a_clock_that_went_backwards_does_not_move_the_generation_of_the_plans(
    lifecycle,
):
    """A durable stamp would record the step back and bump the generation of the plans."""
    install_first(lifecycle, status="succeeded")
    lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")
    resume(lifecycle, FIRST)
    lifecycle.clock.value = instant("2026-11-02T09:00:00.000000Z")  # two hours back
    clock = clock_row(lifecycle)
    report = resume(lifecycle, FIRST)
    assert report.blockers == ("source_terminal", "reconcile_available")
    assert clock_row(lifecycle) == clock


def test_a_clock_row_a_store_cannot_hold_is_an_invalid_store_to_the_report(lifecycle):
    install_first(lifecycle, status="succeeded")
    with open_store(lifecycle.root_dir, timeout=60) as store:
        store.connection.execute("UPDATE cache_clock SET high_watermark=?", ("x" * 27,))
        store.connection.commit()
    with pytest.raises(YorungeError) as error:
        resume(lifecycle, FIRST)
    assert error.value.code == "state_invalid"


def test_a_root_that_continued_into_an_unknown_one_is_superseded_by_it(lifecycle):
    install_first(lifecycle, status="unknown", intents=5, acknowledged=4)
    report = resume(lifecycle, root_of(lifecycle))
    assert report.blockers == ("source_superseded",)
    assert report.related_operation_id == FIRST
    assert report.recommended_action == "none"


def test_prepare_refuses_a_superseded_root_and_names_the_root_it_was_asked_about(lifecycle):
    install_first(lifecycle, status="unknown", intents=5, acknowledged=4)
    root = root_of(lifecycle)
    stored = state(lifecycle)
    with pytest.raises(ContinuationNotPossible) as error:
        resume(lifecycle, root, prepare=True)
    assert error.value.blockers == ("source_superseded",)
    assert error.value.operation_id == root
    assert state(lifecycle) == stored


def test_a_root_whose_continuation_still_runs_is_active_and_names_it(lifecycle):
    install_first(lifecycle, status="running")
    report = resume(lifecycle, root_of(lifecycle))
    assert report.blockers == ("source_active",)
    assert report.related_operation_id == FIRST
    assert report.recommended_action == "wait"


def test_a_root_whose_create_is_unknown_has_no_dataset_to_continue(lifecycle_without_baseline):
    lifecycle = lifecycle_without_baseline
    report = resume(lifecycle, root_of(lifecycle))
    assert "create_unknown" in report.blockers
    assert report.dataset_id is None


@pytest.mark.parametrize(
    "spec,code",
    [
        ({"status": "running"}, "operation_conflict"),  # active: the one error that names a wait
        ({"status": "succeeded"}, "continuation_not_possible"),
        ({"status": "cancelled"}, "continuation_not_possible"),
    ],
)
def test_prepare_refuses_a_source_the_journal_rules_out_and_leaves_the_store_alone(
    lifecycle, spec, code
):
    install_first(lifecycle, **spec)
    stored = state(lifecycle)
    with pytest.raises(OperationError) as error:
        resume(lifecycle, FIRST, prepare=True)
    assert error.value.code == code
    assert error.value.operation_id == FIRST
    if code == "continuation_not_possible":
        assert isinstance(error.value, ContinuationNotPossible)
        assert error.value.blockers[0] == "source_terminal"
    assert state(lifecycle) == stored


def test_prepare_names_the_descendant_that_keeps_a_source_active(lifecycle):
    install_first(lifecycle, status="running")
    root_of_value = root_of(lifecycle)
    with pytest.raises(OperationError) as error:
        resume(lifecycle, root_of_value, prepare=True)
    assert (error.value.code, error.value.operation_id) == ("operation_conflict", FIRST)


def test_a_lineage_that_cannot_be_merged_is_a_state_that_is_not_valid(lifecycle, monkeypatch):
    install_first(lifecycle, status="unknown", intents=5, acknowledged=4)

    def foreign(journals, manifest):
        raise ValueError("the journals of two lineages")

    monkeypatch.setattr("yorunge.adapters.upload_chain.merge_chain", foreign)
    for flags in ({}, {"prepare": True}):
        root_of_value = root_of(lifecycle)
        with pytest.raises(YorungeError) as error:
            resume(lifecycle, root_of_value, **flags)
        assert error.value.code == "state_invalid"


def test_an_unknown_operation_is_not_found(lifecycle):
    with pytest.raises(YorungeError) as error:
        resume(lifecycle, "00000000-0000-4000-8000-0000000000ee")
    assert error.value.code == "operation_not_found"


def test_an_operation_id_that_is_not_one_is_refused_before_anything_is_read(lifecycle, tmp_path):
    with pytest.raises(YorungeError) as error:
        resume(lifecycle, "not-an-id")
    assert error.value.code == "invalid_request"
    # Before the store is opened: a state directory that does not exist is not what is reported.
    missing = UploadResumeRuntime(
        lifecycle.bound.context,
        Profile(platform_key_env="TEST_PLATFORM_KEY"),
        tmp_path / "no-such-state",
        session_factory=forbidden,
        clock=lifecycle.clock,
    )
    with pytest.raises(YorungeError) as error:
        missing.resume("not-an-id", accept_unverified_read=True)
    assert error.value.code == "invalid_request"


@pytest.mark.parametrize(
    "flags",
    [
        {"accept_unverified_read": 1},
        {"accept_unverified_read": None},
        {"prepare": "yes"},
        {"prepare": True, "accept_unconfirmed_effects": 1},
        {"accept_unconfirmed_effects": True},  # belongs to --prepare alone
    ],
    ids=["int", "none", "string", "int acknowledgement", "acknowledgement without prepare"],
)
def test_the_flags_are_booleans_and_the_acknowledgement_belongs_to_prepare(lifecycle, flags):
    # A source the journal rules out would be reported (or refused) if the call were accepted.
    install_first(lifecycle, status="succeeded")
    runtime_value = runtime(lifecycle)
    with pytest.raises(YorungeError) as error:
        runtime_value.resume(FIRST, **{"accept_unverified_read": True, **flags})
    assert error.value.code == "invalid_request"


def test_what_a_report_needs_of_a_source_is_read_from_one_snapshot_of_its_lineage(lifecycle):
    install_first(lifecycle, status="unknown", intents=5, acknowledged=4)
    root = root_of(lifecycle)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = StateUploads(store, clock=lifecycle.clock)
        stamp = StateCache(store, lifecycle.clock).stamp()
        found = repository.resume_source(FIRST, stamp)
        # A continuation's baseline is its root's: the root's operation, dataset and intent digest.
        assert found.baseline_operation_id == root
        assert found.baseline is not None
        assert found.baseline_digest == BASELINE_DIGEST
        assert found.intent_digest == lifecycle.root["record"]["intent_digest"]
        assert len(found.chain.journals) == 2  # the root's journal, then the source's own
        assert found.plan.plan_id == build(lifecycle.root, 1).plan["plan_id"]
        assert found.manifest.digest == lifecycle.manifest.digest
        # What the store holds is read with them: the root's and the source's plan and operation.
        assert found.quota == quota_used(store.connection)
        assert (found.quota.plans, found.quota.operations) == (2, 2)
        # A root is its own baseline.
        top = repository.resume_source(root, stamp)
        assert top.baseline_operation_id == root
        assert len(top.chain.journals) == 1
        assert top.baseline == found.baseline
        assert top.chain.descendants[0].operation_id == FIRST


def test_the_chain_and_the_quota_are_read_from_one_snapshot(lifecycle):
    install_first(lifecycle, status="unknown", intents=5, acknowledged=4)
    tried: list[tuple[str, str]] = []
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = StateUploads(store, clock=lifecycle.clock)
        stamp = StateCache(store, lifecycle.clock).stamp()

        def competing_writer(statement):
            """Try to commit when the chain is first read and when the quota is first counted."""
            moment = "quota" if statement == "SELECT count(*) FROM upload_plans" else None
            if moment is None and "upload_plans" in statement and not tried:
                moment = "chain"
            if moment is None:
                return
            other = sqlite3.connect(lifecycle.root_dir / DB_NAME, timeout=0)
            try:
                other.execute("BEGIN IMMEDIATE")
                other.execute("UPDATE upload_plans SET prepared_at=prepared_at")
                other.execute("COMMIT")
                tried.append((moment, "committed"))
            except sqlite3.OperationalError:
                tried.append((moment, "blocked"))
            finally:
                other.close()

        store.connection.set_trace_callback(competing_writer)
        try:
            repository.resume_source(FIRST, stamp)
        finally:
            store.connection.set_trace_callback(None)
    assert tried == [("chain", "blocked"), ("quota", "blocked")]


def test_a_busy_store_is_a_closed_error_not_a_raw_sqlite_one(lifecycle):
    install_first(lifecycle, status="unknown", intents=5, acknowledged=4)
    with open_store(lifecycle.root_dir, timeout=0.2) as store:
        repository = StateUploads(store, clock=lifecycle.clock)
        stamp = StateCache(store, lifecycle.clock).stamp()
        other = sqlite3.connect(lifecycle.root_dir / DB_NAME, timeout=0)
        other.execute("BEGIN EXCLUSIVE")
        try:
            with pytest.raises(YorungeError) as error:
                repository.resume_source(FIRST, stamp)
        finally:
            other.execute("ROLLBACK")
            other.close()
    assert error.value.code == "state_busy"


def test_the_unverified_read_is_not_asked_for_when_nothing_would_be_read(lifecycle):
    install_first(lifecycle, status="succeeded")
    # The journal rules the source out: no provider read is made, so no choice about one is needed.
    report = runtime(lifecycle).resume(FIRST, accept_unverified_read=False)
    assert "source_terminal" in report.blockers
    assert report.observation is None
    # What the store would hold after an attempt is stated even then: for all N files.
    assert report.quota_added.payload_bytes == continuation_added_payload_bytes(
        lifecycle.manifest.file_count
    )
    runtime_value = runtime(lifecycle)
    with pytest.raises(OperationError) as error:
        runtime_value.resume(FIRST, accept_unverified_read=False, prepare=True)
    assert error.value.code == "continuation_not_possible"
