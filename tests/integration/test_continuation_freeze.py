"""Freezing the source of a continuation: what ``resume --prepare`` writes before it plans."""

from functools import partial

import pytest

from tests.fixtures.continuation_history import FIRST, build, install
from yorunge.adapters.state import open_store
from yorunge.adapters.upload_store import validate_uploads
from yorunge.domain.capabilities import instant
from yorunge.domain.dataset_transfer_v3 import TransferControlV3
from yorunge.domain.errors import YorungeError

TABLES = ("upload_operations", "upload_controls", "upload_stage_intents", "upload_stage_receipts")


def dump(store):
    return [store.connection.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in TABLES]


def code_of(call):
    with pytest.raises(YorungeError) as error:
        call()
    return error.value.code


def source_running(lifecycle, store, **spec):
    """The first continuation, still running with its lease (until 11:02:32)."""
    install(store, build(lifecycle.root, 1, status="running", **spec))
    return lifecycle.repository(store)


def test_a_running_source_whose_lease_lapsed_is_frozen_as_unknown(lifecycle):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = source_running(lifecycle, store)
        lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")
        view = repository.freeze_source(FIRST)
        record = view.operation
        assert (record.status, record.reason) == ("unknown", "request_uncertain")
        assert record.lease is None and record.fence == 2 and record.workflow_latched is True
        assert [(c.kind, type(c)) for c in view.controls] == [("recovery", TransferControlV3)]
        validate_uploads(store.connection)


def test_a_source_with_a_live_lease_is_not_frozen(lifecycle):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = source_running(lifecycle, store)
        before = dump(store)
        assert code_of(lambda: repository.freeze_source(FIRST)) == "operation_conflict"
        assert dump(store) == before


@pytest.mark.parametrize("reason", ["request_uncertain", "read_unavailable", "identity_reset"])
def test_a_source_that_is_already_unknown_is_left_exactly_as_it_is(lifecycle, reason):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        item = build(lifecycle.root, 1, status="unknown", intents=5, acknowledged=4)
        record = {**item.record, "reason": reason}
        item.record = record
        item.controls = [{**c, "reason": reason} for c in item.controls]
        install(store, item)
        repository = lifecycle.repository(store)
        lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")
        before = dump(store)
        first = repository.freeze_source(FIRST)
        second = repository.freeze_source(FIRST)  # a second prepare, after the first
        assert first == second and first.operation.reason == reason
        assert (
            first.operation.fence == record["fence"]
            and first.operation.revision == record["revision"]
        )
        assert dump(store) == before


def test_two_prepares_in_a_row_freeze_a_lapsed_source_once(lifecycle):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = source_running(lifecycle, store)
        lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")
        first = repository.freeze_source(FIRST)
        again = repository.freeze_source(FIRST)
        assert again.operation == first.operation
        assert (first.operation.fence, first.operation.revision) == (2, again.operation.revision)


def test_a_source_that_sent_nothing_or_is_over_is_not_a_source_to_freeze(lifecycle):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        repository = lifecycle.repository(store)
        install(store, build(lifecycle.root, 1, status="admitted"))
        install(store, build(lifecycle.root, 2, status="cancelled"))
        install(store, build(lifecycle.root, 3, status="succeeded"))
        before = dump(store)
        for number in (1, 2, 3):
            operation_id = f"00000000-0000-4000-8000-00000000030{number}"
            assert code_of(partial(repository.freeze_source, operation_id)) == "operation_conflict"
        assert dump(store) == before


def test_a_source_that_sent_nothing_is_not_frozen_even_when_its_lease_lapsed(lifecycle):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        install(store, build(lifecycle.root, 1, status="admitted"))  # lease until 11:02:32
        repository = lifecycle.repository(store)
        lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")
        before = dump(store)
        # Nothing was sent, so there is nothing to continue: it is cleaned up, never frozen.
        assert code_of(partial(repository.freeze_source, FIRST)) == "operation_conflict"
        assert dump(store) == before


def test_freezing_cancels_the_descendants_that_lapsed_before_they_sent_anything(lifecycle):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        # The root is the source: one descendant admitted and lapsed, one cancelled already.
        install(store, build(lifecycle.root, 1, status="admitted"))
        repository = lifecycle.repository(store)
        lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")
        root = lifecycle.root["record"]["operation_id"]
        view = repository.freeze_source(root)
        assert view.operation.status == "unknown"  # the root was frozen already: left as it is
        stale = repository.show(operation_id=FIRST)
        assert (stale.operation.status, stale.operation.reason) == ("cancelled", "lease_expired")
        validate_uploads(store.connection)


def test_freezing_leaves_a_descendant_whose_lease_lives(lifecycle):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        install(store, build(lifecycle.root, 1, status="admitted"))  # lease until 11:02:32
        repository = lifecycle.repository(store)
        before = dump(store)
        repository.freeze_source(lifecycle.root["record"]["operation_id"])
        assert dump(store) == before


@pytest.mark.parametrize("status", ["running", "unknown"])
def test_freezing_leaves_a_descendant_that_sent_something_alone_whatever_its_lease(
    lifecycle, status
):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        install(store, build(lifecycle.root, 1, status="unknown", intents=5, acknowledged=4))
        install(
            store,
            build(
                lifecycle.root, 2, source=FIRST, status=status,
                indices=(2,), uncertain=(), intents=3, acknowledged=2,
            ),
        )  # fmt: skip
        lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")  # every lease is over
        before = dump(store)
        # The source is unknown already: nothing is frozen, and a descendant that has sent
        # something is not an admitted one that never will, so it is not cancelled.
        lifecycle.repository(store).freeze_source(FIRST)
        assert dump(store) == before
        validate_uploads(store.connection)


@pytest.mark.parametrize("credential", ["rotated", "none"])
def test_a_source_is_frozen_without_the_credential_it_was_planned_with(lifecycle, credential):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        install(store, build(lifecycle.root, 1, status="running"))
        bound = lifecycle.rotated(store) if credential == "rotated" else None
    lifecycle.clock.value = instant("2026-11-02T11:05:00.000000Z")
    with open_store(lifecycle.root_dir, timeout=60) as store:
        # Like the cleanup of an expired operation: no credential check, and no error after the
        # commit. (Planning, approving and admitting are what need the current credential.)
        view = lifecycle.repository(store, bound).freeze_source(FIRST)
        assert (view.operation.status, view.operation.reason) == ("unknown", "request_uncertain")
        assert view.operation.lease is None and view.operation.fence == 2
        validate_uploads(store.connection)
