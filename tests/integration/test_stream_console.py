"""Actual TLS messages reach the common renderer in a separate Python process."""

import json
import os
import selectors
import signal
import socket
import subprocess
import sys
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest

from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from tests.fixtures.stream_console import Value
from yorunge import api
from yorunge.application.stream_results import encode_event
from yorunge.domain.errors import OperationError
from yorunge.domain.models import Result
from yorunge.domain.streams import (
    ErrorEvent,
    ProgressEvent,
    ProgressPayload,
    error_payload,
    result_event,
)

CONNECT = socket.socket.connect
CONNECT_EX = socket.socket.connect_ex
GETADDRINFO = socket.getaddrinfo
STREAM = "1c9a96e8-a291-4646-be50-6929c9ce0bc6"
OPERATION = "03932442-5d7e-48c0-8aeb-0b0bcf7d8d3a"
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "stream_console.py"


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(tmp_path_factory.mktemp("stream-console-tls"))


@pytest.fixture(autouse=True)
def actual_loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


def progress(sequence=1, *, operation_id=OPERATION):
    return ProgressEvent(
        schema_version=1,
        stream_id=STREAM,
        sequence=sequence,
        event="progress",
        operation_id=operation_id,
        payload=ProgressPayload(stage="receiving", completed=1, total=2),
    )


def result(*, operation_id=OPERATION):
    return result_event(
        Result[Value](data=Value(text="Türkçe 🛰\nikinci satır"), warnings=("fixture-warning",)),
        stream_id=STREAM,
        sequence=2,
        operation_id=operation_id,
    )


@contextmanager
def console(server, *, operation_id=OPERATION):
    environment = dict(os.environ)
    environment.update({"LC_ALL": "C", "PYTHONIOENCODING": "ascii", "PYTHONUTF8": "0"})
    process = subprocess.Popen(
        [
            sys.executable,
            "-W",
            "error",
            str(FIXTURE),
            "--ca",
            str(server.certificates[0]),
            "--port",
            str(server.port),
            "--stream-id",
            STREAM,
            "--operation-id",
            operation_id,
        ],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        yield process
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=10)


def output_records(stdout):
    assert stdout.endswith(b"\n")
    return [json.loads(line.decode("utf-8", "strict")) for line in stdout.splitlines()]


def assert_events(events, kinds, *, operation_id=OPERATION):
    assert [event["event"] for event in events] == kinds
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    assert all(event["stream_id"] == STREAM for event in events)
    assert all(event["operation_id"] == operation_id for event in events)
    assert sum(kind in ("result", "error") for kind in kinds) == 1


@pytest.mark.parametrize("chunk_size", [1, 32_768])
def test_tls_progress_and_typed_result_use_the_same_renderer_in_a_subprocess(
    certificates, chunk_size
):
    body = encode_event(progress()) + encode_event(result())
    with TlsServer(certificates, {"/v1/events": Reply(body=body, chunk_size=chunk_size)}) as server:
        with console(server) as process:
            stdout, stderr = process.communicate(timeout=10)
            assert process.returncode == 0, stderr
        events = output_records(stdout)
        assert_events(events, ["progress", "result"])
        assert events[-1]["payload"] == result().payload.model_dump(mode="json")
        assert len(stdout.splitlines()) == 2
        assert stderr == b""
        assert len(server.requests) == 1
        assert server.requests[0].path == "/v1/events"


@pytest.mark.parametrize("trailing", [b" ", encode_event(progress(3))])
def test_tls_terminal_followed_by_data_emits_one_error_without_completed_summary(
    certificates, trailing
):
    body = encode_event(progress()) + encode_event(result()) + trailing
    with TlsServer(certificates, {"/v1/events": Reply(body=body, chunk_size=7)}) as server:
        with console(server) as process:
            stdout, stderr = process.communicate(timeout=10)
            assert process.returncode == 1, stderr
        events = output_records(stdout)
        assert_events(events, ["progress", "error"])
        assert events[-1]["payload"] == OperationError("invalid_response", OPERATION).envelope()
        assert stderr == b""
        assert b'"status":"completed"' not in stdout
        assert len(server.requests) == 1


def test_malformed_first_tls_record_has_empty_stdout_and_bound_plain_json_stderr(certificates):
    body = b'{"private-upstream-explanation":"never expose this"}\n'
    with TlsServer(certificates, {"/v1/events": Reply(body=body, chunk_size=3)}) as server:
        with console(server) as process:
            stdout, stderr = process.communicate(timeout=10)
            assert process.returncode == 1, stderr
        assert stdout == b""
        assert stderr.count(b"\n") == 1
        assert json.loads(stderr) == OperationError("invalid_response", OPERATION).envelope()
        assert b"private-upstream" not in stderr
        assert b"Traceback" not in stderr
        assert len(server.requests) == 1


def test_provider_terminal_error_rebuilds_local_message_and_finish_returns_its_exit(certificates):
    local = OperationError("invalid_request", OPERATION)
    event = ErrorEvent(
        schema_version=1,
        stream_id=STREAM,
        sequence=2,
        event="error",
        operation_id=OPERATION,
        payload=error_payload(local),
    ).model_dump(mode="json")
    event["payload"]["message"] = "private provider message must never be copied"
    provider = json.dumps(event, ensure_ascii=False, separators=(",", ":")).encode() + b"\n"
    body = encode_event(progress()) + provider
    with TlsServer(certificates, {"/v1/events": Reply(body=body, chunk_size=11)}) as server:
        with console(server) as process:
            stdout, stderr = process.communicate(timeout=10)
            assert process.returncode == 2, stderr
        events = output_records(stdout)
        assert_events(events, ["progress", "error"])
        assert events[-1]["payload"] == local.envelope()
        assert b"private provider" not in stdout
        assert stderr == b""
        assert len(server.requests) == 1


def test_actual_sigint_after_progress_closes_tls_without_job_mutation_or_resubscribe(
    certificates, admitted_operation
):
    state, _, operation, _, _ = admitted_operation
    operation_id = operation.admission.operation_id
    before = api.show_job(operation_id, state_dir=state).model_dump(mode="json")
    release, waiting = threading.Event(), threading.Event()
    first = encode_event(progress(operation_id=operation_id))

    def after_first():
        waiting.set()
        assert release.wait(10), "parent did not release the TLS fixture barrier"

    reply = Reply(
        body=first + encode_event(result(operation_id=operation_id)),
        chunk_size=len(first),
        after_first_chunk=after_first,
    )
    with TlsServer(certificates, {"/v1/events": reply}) as server:
        try:
            with console(server, operation_id=operation_id) as process:
                assert process.stdout is not None
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ)
                    assert selector.select(10), "child did not publish the first progress event"
                published = process.stdout.readline()
                assert output_records(published)[0]["event"] == "progress"
                assert waiting.wait(3), "server did not reach its first-chunk barrier"
                assert not release.is_set()
                process.send_signal(signal.SIGINT)
                stdout, stderr = process.communicate(timeout=10)
                assert process.returncode == 6, stderr
            events = output_records(published + stdout)
            assert_events(events, ["progress", "error"], operation_id=operation_id)
            assert (
                events[-1]["payload"]
                == OperationError("request_cancelled", operation_id).envelope()
            )
            assert stderr == b""
            assert b"Traceback" not in stdout
            assert len(server.requests) == 1
            assert api.show_job(operation_id, state_dir=state).model_dump(mode="json") == before
        finally:
            release.set()
