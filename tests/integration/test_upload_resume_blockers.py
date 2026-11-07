"""What the journal alone says of a source, and that nothing is asked of the provider then.

The histories are the stored ones of ``tests/fixtures/continuation_history.py`` in a real store; the
runtime is given a session factory that fails the test if it is ever called. A source that cannot be
continued is reported (exit 0) and refused by ``--prepare``, without a single request.
"""

import pytest

from tests.fixtures.continuation_history import BASELINE_DIGEST, FIRST, build, install
from tests.fixtures.continuation_lifecycle import dump
from yorunge.adapters.capability_cache import StateCache
from yorunge.adapters.state import open_store
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_resume import UploadResumeRuntime
from yorunge.domain.capabilities import instant
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.models import Profile
from yorunge.domain.upload_resume import ContinuationNotPossible


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
    stored = state(lifecycle)
    report = resume(lifecycle, FIRST)
    assert report.blockers == blockers and not report.eligible and report.observation is None
    assert report.recommended_action == action
    assert report.related_operation_id is None and report.plan_id is None
    assert state(lifecycle) == stored  # a report writes nothing


def test_a_root_that_continued_into_an_unknown_one_is_superseded_by_it(lifecycle):
    install_first(lifecycle, status="unknown", intents=5, acknowledged=4)
    report = resume(lifecycle, root_of(lifecycle))
    assert report.blockers == ("source_superseded",) and report.related_operation_id == FIRST
    assert report.recommended_action == "none"


def test_a_root_whose_continuation_still_runs_is_active_and_names_it(lifecycle):
    install_first(lifecycle, status="running")
    report = resume(lifecycle, root_of(lifecycle))
    assert report.blockers == ("source_active",) and report.related_operation_id == FIRST
    assert report.recommended_action == "wait"


def test_a_root_whose_create_is_unknown_has_no_dataset_to_continue(lifecycle_without_baseline):
    lifecycle = lifecycle_without_baseline
    report = resume(lifecycle, root_of(lifecycle))
    assert "create_unknown" in report.blockers and report.dataset_id is None


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
    assert error.value.code == code and error.value.operation_id == FIRST
    if code == "continuation_not_possible":
        assert isinstance(error.value, ContinuationNotPossible)
        assert error.value.blockers[0] == "source_terminal"
    assert state(lifecycle) == stored


def test_prepare_names_the_descendant_that_keeps_a_source_active(lifecycle):
    install_first(lifecycle, status="running")
    with pytest.raises(OperationError) as error:
        resume(lifecycle, root_of(lifecycle), prepare=True)
    assert (error.value.code, error.value.operation_id) == ("operation_conflict", FIRST)


def test_an_unknown_operation_is_not_found(lifecycle):
    with pytest.raises(YorungeError) as error:
        resume(lifecycle, "00000000-0000-4000-8000-0000000000ee")
    assert error.value.code == "operation_not_found"


@pytest.mark.parametrize(
    "source,flags",
    [
        ("not-an-id", {}),
        ("root", {"accept_unconfirmed_effects": True}),  # only with --prepare
    ],
)
def test_a_call_that_is_not_well_formed_is_refused_before_anything_is_read(
    lifecycle, source, flags
):
    source = root_of(lifecycle) if source == "root" else source
    with pytest.raises(YorungeError) as error:
        resume(lifecycle, source, **flags)
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
        assert found.baseline is not None and found.baseline_digest == BASELINE_DIGEST
        assert found.intent_digest == lifecycle.root["record"]["intent_digest"]
        assert len(found.chain.journals) == 2  # the root's journal, then the source's own
        assert found.plan.plan_id == build(lifecycle.root, 1).plan["plan_id"]
        assert found.manifest.digest == lifecycle.manifest.digest
        # A root is its own baseline.
        top = repository.resume_source(root, stamp)
        assert top.baseline_operation_id == root and len(top.chain.journals) == 1
        assert top.baseline == found.baseline and top.chain.descendants[0].operation_id == FIRST


def test_the_unverified_read_is_not_asked_for_when_nothing_would_be_read(lifecycle):
    install_first(lifecycle, status="succeeded")
    # The journal rules the source out: no provider read is made, so no choice about one is needed.
    report = runtime(lifecycle).resume(FIRST, accept_unverified_read=False)
    assert "source_terminal" in report.blockers
    with pytest.raises(OperationError) as error:
        runtime(lifecycle).resume(FIRST, accept_unverified_read=False, prepare=True)
    assert error.value.code == "continuation_not_possible"
