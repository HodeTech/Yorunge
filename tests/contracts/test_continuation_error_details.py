"""A refused continuation names why in closed blockers, and nothing re-wrapping it loses them.

``--prepare`` is refused with ``continuation_not_possible`` when the report has blockers. The names
are the whole of the explanation in a machine's hands, so every place that rebuilds an operation
error (the public layer, the local reads, the stream results, the CLI renderer) keeps them, the
NDJSON error event carries them in a closed details type, and an error that names none, or names
something the report does not know, cannot exist.
"""

import json

import pytest

from yorunge.adapters.upload_api import _safe
from yorunge.adapters.upload_public import _safe_local
from yorunge.application.stream_results import _bound
from yorunge.cli.output import OutputRenderer
from yorunge.domain.errors import MESSAGES, OperationError, YorungeError
from yorunge.domain.streams import (
    ContinuationErrorDetails,
    EmptyErrorDetails,
    ErrorEnvelope,
    OperationErrorDetails,
    error_payload,
)
from yorunge.domain.upload_resume import BLOCKERS, ContinuationNotPossible

SOURCE = "00000000-0000-4000-8000-000000000009"
STREAM = "00000000-0000-4000-8000-0000000000e1"
NAMED = ("source_terminal", "reconcile_available", "local_changed")


def refusal():
    return ContinuationNotPossible(NAMED, SOURCE)


def test_the_envelope_of_the_error_lists_the_blockers_in_the_closed_order():
    value = refusal().envelope()
    assert value["code"] == "continuation_not_possible" and value["operation_id"] == SOURCE
    assert value["details"] == {
        "reason_code": "continuation_not_possible",
        "capacity_kind": None,
        "blockers": list(NAMED),
    }
    assert [b for b in BLOCKERS if b in NAMED] == list(NAMED)  # the order the report uses


def test_only_a_refused_continuation_has_blockers_and_it_always_has_them():
    assert OperationError("operation_conflict", SOURCE).blockers is None
    assert "blockers" not in OperationError("operation_conflict", SOURCE).envelope()["details"]
    with pytest.raises(ValueError):
        OperationError("continuation_not_possible", SOURCE)  # a refusal that says nothing
    with pytest.raises(ValueError):
        OperationError("operation_conflict", SOURCE, blockers=("source_terminal",))


@pytest.mark.parametrize(
    "bad",
    [(), ("local_changed", "source_terminal"), ("source_terminal", "source_terminal"), ("nope",)],
    ids=["none", "out of order", "repeated", "unknown"],
)
def test_the_blockers_of_a_refusal_are_closed_ordered_and_distinct(bad):
    with pytest.raises(ValueError):
        ContinuationNotPossible(bad, SOURCE)


def test_an_active_source_is_never_a_refusal_with_blockers():
    with pytest.raises(ValueError):
        ContinuationNotPossible(("source_active",), SOURCE)  # it is operation_conflict


def test_the_stream_error_carries_the_blockers_in_a_closed_details_type():
    payload = error_payload(refusal())
    assert type(payload.details) is ContinuationErrorDetails
    assert payload.details.blockers == NAMED and payload.operation_id == SOURCE
    assert json.loads(payload.model_dump_json())["details"]["blockers"] == list(NAMED)


def test_the_error_event_cannot_name_blockers_for_another_code_or_omit_them_for_this_one():
    kwargs = dict(schema_version=1, operation_id=SOURCE, retryable=False)
    named = ContinuationErrorDetails(
        reason_code="continuation_not_possible", capacity_kind=None, blockers=NAMED
    )
    plain = OperationErrorDetails(reason_code="operation_conflict", capacity_kind=None)
    with pytest.raises(ValueError):
        ErrorEnvelope(code="operation_conflict", message="x", details=named, **kwargs)
    with pytest.raises(ValueError):
        ErrorEnvelope(
            code="continuation_not_possible",
            message="x",
            details=OperationErrorDetails(
                reason_code="continuation_not_possible", capacity_kind=None
            ),
            **kwargs,
        )
    with pytest.raises(ValueError):
        ErrorEnvelope(
            code="continuation_not_possible", message="x", details=EmptyErrorDetails(), **kwargs
        )
    ok = ErrorEnvelope(code="continuation_not_possible", message="x", details=named, **kwargs)
    assert ok.message == MESSAGES["continuation_not_possible"]  # rebuilt from trusted text
    assert ErrorEnvelope(code="operation_conflict", message="x", details=plain, **kwargs)


def test_the_closed_details_refuse_unknown_unordered_or_empty_blockers():
    for bad in ((), ("nope",), ("local_changed", "source_terminal")):
        with pytest.raises(ValueError):
            ContinuationErrorDetails(
                reason_code="continuation_not_possible", capacity_kind=None, blockers=bad
            )


def test_the_public_layer_keeps_the_blockers_when_it_binds_the_error_to_its_operation():
    def refuse():
        raise ContinuationNotPossible(NAMED, None)

    with pytest.raises(OperationError) as bound:
        _safe(refuse, identity=lambda: SOURCE)
    assert bound.value.blockers == NAMED and bound.value.operation_id == SOURCE


def test_the_local_reads_keep_the_blockers_too():
    def refuse(store):
        raise refusal()

    from yorunge.adapters import upload_public

    class Store:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    original = upload_public.open_existing_store
    upload_public.open_existing_store = lambda state_dir: Store()
    try:
        with pytest.raises(OperationError) as bound:
            _safe_local(None, SOURCE, refuse)
    finally:
        upload_public.open_existing_store = original
    assert bound.value.blockers == NAMED


def test_the_stream_results_keep_the_blockers_when_they_bind_the_error():
    bound = _bound(refusal(), SOURCE)
    assert isinstance(bound, OperationError) and bound.blockers == NAMED
    assert not isinstance(_bound(YorungeError("invalid_request"), SOURCE), ContinuationNotPossible)


def test_the_cli_renderer_keeps_the_blockers_when_it_binds_the_error_to_its_stream():
    renderer = OutputRenderer("ndjson", operation_id=SOURCE)
    bound = renderer._bound_error(refusal())
    assert isinstance(bound, OperationError) and bound.blockers == NAMED
    assert bound.operation_id == SOURCE


@pytest.mark.parametrize(
    "bad",
    [
        (),
        ("nope",),
        ("source_terminal", "source_terminal"),
        ("local_changed", "source_active"),
        "abc",
    ],
    ids=["none", "unknown", "duplicate", "out of order", "a string"],
)
def test_an_error_cannot_carry_blockers_the_report_does_not_know_or_in_another_order(bad):
    with pytest.raises(ValueError):
        OperationError("continuation_not_possible", SOURCE, blockers=bad)
    # (the same names, closed and in the reporting order, are what the refusal itself builds)
    assert OperationError(
        "continuation_not_possible", SOURCE, blockers=("source_active", "local_changed")
    ).blockers == ("source_active", "local_changed")
