"""One UTF-8 renderer owns complete records, terminal state and output failures."""

import asyncio
import errno
import io
import json
import sys
import threading
from uuid import uuid4

import pytest

from yorunge import cli
from yorunge.cli.output import OutputRenderer, write_utf8
from yorunge.domain.errors import ApprovalNotEffective, OperationError, YorungeError
from yorunge.domain.models import Model, Result
from yorunge.domain.streams import ErrorEvent, ProgressEvent, error_payload, result_event

STREAM = "3ed067a1-72ea-4005-86a1-6c187eb56750"
OPERATION = "7f5d19a9-a95c-43f5-a05a-2be8b3f07d8b"


class Data(Model):
    value: str


def result(value="Türkçe\nikinci satır"):
    return Result[Data](data=Data(value=value))


def progress(sequence=1, *, stream_id=STREAM, operation_id=None):
    return ProgressEvent(
        schema_version=1,
        stream_id=stream_id,
        sequence=sequence,
        event="progress",
        operation_id=operation_id,
        payload={"stage": "receiving", "completed": sequence, "total": None},
    )


def renderer(*, operation_id=None, stdout=None):
    output, errors = io.StringIO() if stdout is None else stdout, io.StringIO()
    return (
        OutputRenderer(
            "ndjson", stdout=output, stderr=errors, stream_id=STREAM, operation_id=operation_id
        ),
        output,
        errors,
    )


class BinarySink:
    """A short-write/flush boundary independent of the text wrapper's encoding."""

    def __init__(self, *, step=None, failure=None, fail_at=None, flush_failure=None):
        self.data = bytearray()
        self.writes = 0
        self.flushes = 0
        self.step = step
        self.failure, self.fail_at, self.flush_failure = failure, fail_at, flush_failure

    def write(self, data):
        self.writes += 1
        if self.fail_at is not None and self.writes >= self.fail_at:
            raise self.failure
        amount = len(data) if self.step is None else min(self.step, len(data))
        self.data.extend(data[:amount])
        return amount

    def flush(self):
        self.flushes += 1
        if self.flush_failure is not None:
            raise self.flush_failure


class TextWrapper:
    encoding = "ascii"

    def __init__(self, buffer):
        self.buffer = buffer

    def write(self, data):
        pytest.fail("the ASCII text wrapper must not encode product output")


def records(output):
    return [json.loads(line) for line in output.getvalue().splitlines()]


def test_result_specialization_is_preserved_and_uses_the_same_codec(monkeypatch):
    from yorunge.application import stream_results

    expected = stream_results.encode_event(result_event(result(), stream_id=STREAM))
    calls = []
    original = stream_results.encode_event

    def encode(event):
        calls.append(event)
        return original(event)

    monkeypatch.setattr(stream_results, "encode_event", encode)
    rendered, output, errors = renderer()
    rendered.result(result())
    assert output.getvalue().encode() == expected
    assert len(calls) == 1
    assert type(calls[0].payload) is Result[Data]
    assert rendered.finish() == 0
    assert errors.getvalue() == ""


def test_progress_is_flushed_before_the_next_event_and_one_terminal_result():
    rendered, output, errors = renderer(operation_id=OPERATION)
    rendered.event(progress(operation_id=OPERATION))
    assert len(records(output)) == 1
    rendered.event(result_event(result(), stream_id=STREAM, sequence=2, operation_id=OPERATION))
    assert rendered.finish() == 0
    events = records(output)
    assert [event["event"] for event in events] == ["progress", "result"]
    assert [event["sequence"] for event in events] == [1, 2]
    assert all(event["operation_id"] == OPERATION for event in events)
    assert events[-1]["payload"] == result().model_dump(mode="json")
    assert errors.getvalue() == ""


@pytest.mark.parametrize("operation_id", [None, OPERATION])
@pytest.mark.parametrize("published", [False, True])
@pytest.mark.parametrize("code", ["transport_timeout", "invalid_response", "stream_interrupted"])
def test_failure_before_or_after_progress_uses_exactly_one_safe_channel(
    operation_id, published, code
):
    rendered, output, errors = renderer(operation_id=operation_id)
    if published:
        rendered.event(progress(operation_id=operation_id))
    error = YorungeError(code)
    assert rendered.error(error) == error.exit_code
    # Duplicate handler calls cannot generate a second terminal or diagnostic.
    assert rendered.error(error) == error.exit_code
    if published:
        events = records(output)
        assert [event["event"] for event in events] == ["progress", "error"]
        envelope = events[1]["payload"]
        assert events[1]["operation_id"] == operation_id
        assert events[1]["sequence"] == 2
        assert errors.getvalue() == ""
        assert rendered.finish() == 1
    else:
        assert output.getvalue() == ""
        envelope = json.loads(errors.getvalue())
        assert len(errors.getvalue().splitlines()) == 1
    assert envelope["code"] == code
    assert envelope["message"] == error.message
    assert envelope["operation_id"] == operation_id
    assert envelope["details"] == (
        {"reason_code": code, "capacity_kind": None} if operation_id else {}
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"sequence": 2},
        {"stream_id": str(uuid4())},
        {"operation_id": OPERATION},
        {"schema_version": True},
        {"sequence": True},
    ],
)
def test_renderer_revalidates_stream_binding_before_any_write(changes):
    rendered, output, errors = renderer()
    event = progress().model_copy(update=changes)
    with pytest.raises(YorungeError) as failure:
        rendered.event(event)
    assert failure.value.code == "invalid_response"
    assert output.getvalue() == ""
    assert errors.getvalue() == ""
    assert rendered.error(failure.value) == 1
    assert json.loads(errors.getvalue())["code"] == "invalid_response"


def test_trailing_local_event_is_rejected_without_a_second_terminal_or_stderr():
    rendered, output, errors = renderer()
    rendered.result(result())
    event = progress(2)
    with pytest.raises(YorungeError) as failure:
        rendered.event(event)
    assert failure.value.code == "invalid_response"
    assert rendered.error(failure.value) == 1
    assert [event["event"] for event in records(output)] == ["result"]
    assert errors.getvalue() == ""


@pytest.mark.parametrize("published", [False, True])
def test_missing_terminal_is_not_success(published):
    rendered, output, errors = renderer(operation_id=OPERATION)
    if published:
        rendered.event(progress(operation_id=OPERATION))
    with pytest.raises(OperationError) as failure:
        rendered.finish()
    assert failure.value.code == "stream_interrupted"
    assert failure.value.operation_id == OPERATION
    assert rendered.error(failure.value) == 1
    assert (records(output)[-1] if published else json.loads(errors.getvalue()))[
        "event" if published else "code"
    ] == ("error" if published else "stream_interrupted")


def test_terminal_provider_error_uses_local_message_and_its_exit_code():
    rendered, output, errors = renderer(operation_id=OPERATION)
    error = OperationError("operation_uncertain", OPERATION, reason_code="transport_timeout")
    payload = error_payload(error).model_copy(update={"message": "private provider explanation"})
    rendered.event(
        ErrorEvent.model_construct(
            schema_version=1,
            stream_id=STREAM,
            sequence=1,
            event="error",
            operation_id=OPERATION,
            payload=payload,
        )
    )
    assert rendered.finish() == 5
    assert records(output)[0]["payload"] == error.envelope()
    assert "private" not in output.getvalue()
    assert errors.getvalue() == ""


@pytest.mark.parametrize("published", [False, True])
def test_operation_reason_and_capacity_metadata_are_retained(published):
    rendered, output, errors = renderer(operation_id=OPERATION)
    if published:
        rendered.event(progress(operation_id=OPERATION))
    error = OperationError("operation_capacity_exceeded", OPERATION, capacity_kind="attempt")
    assert rendered.error(error) == 2
    envelope = records(output)[-1]["payload"] if published else json.loads(errors.getvalue())
    assert envelope == error.envelope()


def test_committed_approval_metadata_survives_pre_publish_error():
    rendered, output, errors = renderer()
    error = ApprovalNotEffective(str(uuid4()), str(uuid4()), "state_changed")
    assert rendered.error(error) == 2
    assert output.getvalue() == ""
    assert json.loads(errors.getvalue()) == error.envelope()


@pytest.mark.parametrize("output", ["json", "text"])
def test_existing_formats_have_no_new_stream_frame_limit(output):
    sink, errors = io.StringIO(), io.StringIO()
    rendered = OutputRenderer(output, stdout=sink, stderr=errors)
    value = "ğ" * (1024 * 1024)
    rendered.result(result(value), text=value)
    assert (
        sink.getvalue() == (result(value).model_dump_json() if output == "json" else value) + "\n"
    )
    assert errors.getvalue() == ""


def test_ndjson_oversize_is_rejected_before_first_publish():
    rendered, output, errors = renderer()
    outcome = result("x" * (1024 * 1024))
    with pytest.raises(YorungeError) as failure:
        rendered.result(outcome)
    assert failure.value.code == "output_write_failed"
    assert rendered.error(failure.value) == 1
    assert output.getvalue() == ""
    assert json.loads(errors.getvalue())["code"] == "output_write_failed"


@pytest.mark.parametrize("output", ["text", "json", "ndjson"])
def test_utf8_binary_writer_handles_short_writes_and_flushes_one_message(output):
    binary = BinarySink(step=1)
    errors = io.StringIO()
    rendered = OutputRenderer(output, stdout=TextWrapper(binary), stderr=errors, stream_id=STREAM)
    rendered.result(result(), text="Türkçe")
    value = binary.data.decode("utf-8")
    assert binary.flushes == 1
    assert binary.writes == len(binary.data)
    if output == "text":
        assert value == "Türkçe\n"
    elif output == "json":
        assert json.loads(value) == result().model_dump(mode="json")
    else:
        assert json.loads(value)["payload"] == result().model_dump(mode="json")
    assert errors.getvalue() == ""


@pytest.mark.parametrize("bad_count", [0, None, True, -1, 1000])
def test_invalid_write_counts_fail_without_busy_loop(bad_count):
    class Incomplete(BinarySink):
        def write(self, data):
            self.writes += 1
            return bad_count

    binary = Incomplete()
    rendered, _, errors = renderer(stdout=TextWrapper(binary))
    outcome = result()
    with pytest.raises(YorungeError) as failure:
        rendered.result(outcome)
    assert failure.value.code == "output_write_failed"
    assert rendered.error(failure.value) == 1
    assert binary.writes == 1
    assert json.loads(errors.getvalue())["code"] == "output_write_failed"


@pytest.mark.parametrize("published", [False, True])
@pytest.mark.parametrize("flush", [False, True])
@pytest.mark.parametrize(
    "io_error, code, exit_code",
    [
        (BrokenPipeError(errno.EPIPE, "private"), "output_closed", 6),
        (OSError(errno.EIO, "private"), "output_write_failed", 1),
    ],
)
def test_partial_or_flush_failure_never_retries_stdout(published, flush, io_error, code, exit_code):
    binary = BinarySink(step=7)
    rendered, _, errors = renderer(stdout=TextWrapper(binary), operation_id=OPERATION)
    if published:
        rendered.event(progress(operation_id=OPERATION))
    if flush:
        binary.flush_failure = io_error
    else:
        binary.failure, binary.fail_at = io_error, binary.writes + 2
    outcome = result()
    with pytest.raises(OperationError) as failure:
        rendered.result(outcome)
    writes = binary.writes
    assert failure.value.code == code
    assert failure.value.operation_id == OPERATION
    assert failure.value.__context__ is None
    assert failure.value.__cause__ is None
    assert rendered.error(failure.value) == exit_code
    assert rendered.error(failure.value) == exit_code
    assert binary.writes == writes
    error = json.loads(errors.getvalue())
    assert error["code"] == code
    assert error["operation_id"] == OPERATION
    assert error["details"] == {"reason_code": code, "capacity_kind": None}
    assert "private" not in errors.getvalue()


@pytest.mark.parametrize("code", ["config_write_uncertain", "operation_uncertain"])
@pytest.mark.parametrize("secondary", [BrokenPipeError(), OSError(errno.EIO, "private")])
def test_known_uncertainty_wins_when_terminal_error_output_also_fails(code, secondary):
    binary = BinarySink()
    rendered, _, errors = renderer(stdout=TextWrapper(binary), operation_id=OPERATION)
    rendered.event(progress(operation_id=OPERATION))
    binary.failure, binary.fail_at = secondary, binary.writes + 1
    error = OperationError(code, OPERATION, reason_code="transport_timeout")
    assert rendered.error(error) == 5
    assert json.loads(errors.getvalue()) == error.envelope()
    assert bytes(binary.data).count(b"\n") == 1


def test_closed_stderr_does_not_replace_primary_exit_or_retry_any_output():
    output = BinarySink(failure=BrokenPipeError(), fail_at=1)
    errors = BinarySink(failure=BrokenPipeError(), fail_at=1)
    rendered = OutputRenderer("json", stdout=TextWrapper(output), stderr=TextWrapper(errors))
    assert rendered.error(YorungeError("config_write_uncertain")) == 5
    assert rendered.error(YorungeError("config_write_uncertain")) == 5
    assert output.writes == 0
    assert errors.writes == 1


def test_slow_sink_applies_backpressure_without_background_queue():
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()

    class Slow(BinarySink):
        def flush(self):
            entered.set()
            assert release.wait(5)
            super().flush()

    binary = Slow()
    rendered, _, _ = renderer(stdout=TextWrapper(binary))

    def render():
        rendered.event(progress())
        finished.set()

    worker = threading.Thread(target=render)
    worker.start()
    try:
        assert entered.wait(5)
        assert not finished.is_set()
        assert binary.writes == 1
        assert binary.flushes == 0
    finally:
        release.set()
        worker.join(timeout=5)
    assert finished.is_set()
    assert binary.flushes == 1


def test_text_only_sink_handles_short_character_writes():
    class Short(io.StringIO):
        def write(self, value):
            return super().write(value[:1])

    sink = Short()
    write_utf8("ğüç\n".encode(), sink)
    assert sink.getvalue() == "ğüç\n"


@pytest.mark.parametrize("phase", ["parse", "dispatch"])
@pytest.mark.parametrize("output", ["text", "json", "ndjson"])
def test_cli_keyboard_interrupt_is_controlled_at_both_boundaries(
    monkeypatch, capsys, phase, output
):
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    if phase == "parse":
        monkeypatch.setattr(cli, "parser", interrupted)
    else:
        monkeypatch.setattr(cli, "dispatch", interrupted)
    assert cli.main(["context", "show", "--output", output]) == 6
    captured = capsys.readouterr()
    assert captured.out == ""
    if output == "text":
        assert captured.err == YorungeError("request_cancelled").message + "\n"
    else:
        assert json.loads(captured.err)["code"] == "request_cancelled"


def test_cli_does_not_swallow_library_task_cancellation(monkeypatch):
    def cancelled(*args, **kwargs):
        raise asyncio.CancelledError

    monkeypatch.setattr(cli, "dispatch", cancelled)
    with pytest.raises(asyncio.CancelledError):
        cli.main(["context", "show", "--output", "ndjson"])


@pytest.mark.parametrize("output", ["text", "json", "ndjson"])
@pytest.mark.parametrize(
    "failure", [OSError("private dispatch path"), UnicodeError("private input")]
)
def test_dispatch_io_failure_is_not_an_output_failure(monkeypatch, capsys, output, failure):
    def rejected(args):
        raise failure

    def output_failure(*args):
        pytest.fail("dispatch must not silence stdout or classify I/O as output failure")

    monkeypatch.setattr(cli, "dispatch", rejected)
    monkeypatch.setattr(OutputRenderer, "output_failure", output_failure)
    assert cli.main(["context", "show", "--output", output]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "private" not in captured.err
    assert "Traceback" not in captured.err
    if output == "text":
        assert captured.err == YorungeError("file_unreadable").message + "\n"
    else:
        assert json.loads(captured.err) == YorungeError("file_unreadable").envelope()


@pytest.mark.parametrize("output", ["json", "ndjson"])
def test_result_serialization_failure_is_safe_and_keeps_stdout_empty(monkeypatch, output):
    class Unsupported(Model):
        data: str

    failure = ValueError("private serializer failure")

    def rejected(*args, **kwargs):
        raise failure

    if output == "ndjson":
        monkeypatch.setattr("yorunge.domain.streams.result_event", rejected)
    else:
        monkeypatch.setattr(Result[Unsupported], "model_dump_json", rejected)
    stdout, stderr = io.StringIO(), io.StringIO()
    rendered = OutputRenderer(output, stdout=stdout, stderr=stderr)
    outcome = Result[Unsupported](data=Unsupported(data="value"))
    with pytest.raises(YorungeError) as error:
        rendered.result(outcome)
    assert error.value.code == "output_write_failed"
    assert error.value.__context__ is None
    assert error.value.__cause__ is None
    assert rendered.error(error.value) == 1
    assert stdout.getvalue() == ""
    assert "private" not in stderr.getvalue()
    assert json.loads(stderr.getvalue())["code"] == "output_write_failed"


@pytest.mark.parametrize("code, expected", [("config_write_uncertain", 5), ("invalid_request", 6)])
@pytest.mark.parametrize("published", [False, True])
def test_second_sigint_during_error_reporting_keeps_known_uncertainty(code, expected, published):
    class Interrupted(io.StringIO):
        def write(self, data):
            raise KeyboardInterrupt

    output = io.StringIO()
    rendered = OutputRenderer("ndjson", stdout=output, stderr=Interrupted(), stream_id=STREAM)
    if published:
        rendered.event(progress())
        rendered.stdout = Interrupted()
    assert rendered.error(YorungeError(code)) == expected
    assert rendered.error(YorungeError("output_write_failed")) == expected


@pytest.mark.parametrize("code,expected", [("operation_conflict", 2), ("remote_failed", 1)])
@pytest.mark.parametrize("published", [False, True])
def test_second_sigint_preserves_known_operation_failure(code, expected, published):
    class Interrupted(io.StringIO):
        calls = 0

        def write(self, data):
            self.calls += 1
            raise KeyboardInterrupt

    interrupted = Interrupted()
    output = io.StringIO()
    rendered = OutputRenderer(
        "ndjson", stdout=output, stderr=interrupted, stream_id=STREAM, operation_id=OPERATION
    )
    if published:
        rendered.event(progress(operation_id=OPERATION))
        rendered.stdout = interrupted
    assert rendered.error(OperationError(code, OPERATION)) == expected
    assert rendered.error(YorungeError("request_cancelled")) == expected
    assert interrupted.calls == 1


@pytest.mark.parametrize("arguments", [["--help"], ["--version"]])
def test_metadata_closed_python_stdout_is_controlled(monkeypatch, arguments):
    closed = io.TextIOWrapper(io.BytesIO())
    closed.close()
    errors = io.StringIO()
    monkeypatch.setattr(sys, "stdout", closed)
    monkeypatch.setattr(sys, "stderr", errors)
    assert cli.main([*arguments, "--output=json"]) == 1
    assert json.loads(errors.getvalue())["code"] == "output_write_failed"


def test_sigint_after_partial_record_disables_stdout_before_cancellation_reporting():
    binary = BinarySink(step=7)
    rendered, _, errors = renderer(stdout=TextWrapper(binary), operation_id=OPERATION)
    rendered.event(progress(operation_id=OPERATION))
    complete = bytes(binary.data)
    binary.failure, binary.fail_at = KeyboardInterrupt(), binary.writes + 2
    outcome = result()
    with pytest.raises(KeyboardInterrupt):
        rendered.result(outcome)
    partial = bytes(binary.data)
    assert partial.startswith(complete)
    assert len(partial) == len(complete) + 7
    writes = binary.writes
    assert rendered.error(YorungeError("request_cancelled")) == 6
    assert binary.writes == writes
    assert bytes(binary.data) == partial
    error = json.loads(errors.getvalue())
    assert error["code"] == "request_cancelled"
    assert error["operation_id"] == OPERATION
    assert error["details"] == {"reason_code": "request_cancelled", "capacity_kind": None}
