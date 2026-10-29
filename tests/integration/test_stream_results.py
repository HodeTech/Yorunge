"""Real TLS message/EOF, bounded NDJSON parsing and owned stream lifetime."""

import asyncio
import json
import socket
import threading
import time

import pytest

from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from yorunge.adapters.http_transport import HttpxTransport
from yorunge.application.http_transport import RAW_LIMIT, HttpRequest
from yorunge.application.stream_results import encode_event, open_stream
from yorunge.domain.credentials import SecretValue, normalize_target
from yorunge.domain.errors import MESSAGES, OperationError, YorungeError
from yorunge.domain.models import Model, Result
from yorunge.domain.streams import (
    ErrorEvent,
    ProgressEvent,
    ProgressPayload,
    ResultEvent,
    error_payload,
    result_event,
)

CONNECT = socket.socket.connect
CONNECT_EX = socket.socket.connect_ex
GETADDRINFO = socket.getaddrinfo
STREAM = "df15d9ec-9dd4-4d72-8186-9c29b4231c2e"
OTHER = "41d2de17-0241-49f9-8ac7-25416ff897c6"
OPERATION = "47c09643-13cc-40b3-9c25-88d00e96c0c7"
TARGET = normalize_target("https://localhost/v1")
SECRET = "stream-private-canary-781252"


class Value(Model):
    text: str


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(tmp_path_factory.mktemp("stream-tls"))


@pytest.fixture(autouse=True)
def actual_loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


def request():
    return HttpRequest(TARGET, "GET", "events", service_id="evren-platform", max_bytes=RAW_LIMIT)


def progress(sequence=1, *, operation_id=None):
    return ProgressEvent(
        schema_version=1,
        stream_id=STREAM,
        sequence=sequence,
        event="progress",
        operation_id=operation_id,
        payload=ProgressPayload(stage="receiving", completed=1, total=2),
    )


def result(sequence=2, *, text="Türkçe 🛰", operation_id=None):
    return result_event(
        Result[Value](data=Value(text=text), warnings=("fixture-warning",)),
        stream_id=STREAM,
        sequence=sequence,
        operation_id=operation_id,
    )


def record(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"


def collect(server, *, operation_id=None, secrets=(), timeout=3):
    async def run():
        async with HttpxTransport(transport=server.transport()) as transport:
            async with open_stream(
                transport,
                request(),
                Value,
                deadline=time.monotonic() + timeout,
                stream_id=STREAM,
                operation_id=operation_id,
                secrets=secrets,
            ) as stream:
                return [event async for event in stream]

    return asyncio.run(run())


def test_real_tls_split_utf8_crlf_and_keepalive_message_eof(certificates):
    body = (encode_event(progress()) + encode_event(result())).replace(b"\n", b"\r\n")
    with TlsServer(certificates, {"/v1/events": Reply(body=body, chunk_size=1)}) as server:

        async def run():
            all_events = []
            async with HttpxTransport(transport=server.transport()) as transport:
                for _ in range(2):
                    async with open_stream(
                        transport, request(), Value, deadline=time.monotonic() + 3, stream_id=STREAM
                    ) as stream:
                        all_events.append([event async for event in stream])
            return all_events

        first, second = asyncio.run(run())
        assert isinstance(first[0], ProgressEvent)
        assert isinstance(first[1], ResultEvent)
        assert first[1].payload == result().payload
        assert [item.sequence for item in first] == [1, 2]
        assert second == first
        # Message EOF was sufficient; the healthy HTTP/1.1 connection was reused.
        assert len({item.connection for item in server.requests}) == 1
        assert not server.disconnected.is_set()


def test_progress_delivered_before_second_chunk_and_terminal_held_to_eof(certificates):
    first, terminal = encode_event(progress()), encode_event(result())
    release = threading.Event()

    def after_first():
        assert release.wait(3), "consumer did not receive the first small progress chunk"

    with TlsServer(
        certificates,
        {
            "/v1/events": Reply(
                body=first + terminal, chunk_size=len(first), after_first_chunk=after_first
            )
        },
    ) as server:

        async def run():
            async with HttpxTransport(transport=server.transport()) as transport:
                async with open_stream(
                    transport, request(), Value, deadline=time.monotonic() + 3, stream_id=STREAM
                ) as stream:
                    event = await anext(stream)
                    assert isinstance(event, ProgressEvent)
                    assert not release.is_set()
                    release.set()
                    terminal_event = await anext(stream)
                    assert isinstance(terminal_event, ResultEvent)
                    with pytest.raises(StopAsyncIteration):
                        await anext(stream)

        try:
            asyncio.run(run())
        finally:
            release.set()


def test_terminal_is_not_delivered_before_rest_of_http_body(certificates):
    terminal = encode_event(result(1))
    release = threading.Event()
    callback_entered = threading.Event()

    def after_first():
        callback_entered.set()
        assert release.wait(3)

    body = terminal + b" "
    with TlsServer(
        certificates,
        {"/v1/events": Reply(body=body, chunk_size=len(terminal), after_first_chunk=after_first)},
    ) as server:

        async def reader():
            async with HttpxTransport(transport=server.transport()) as transport:
                async with open_stream(
                    transport, request(), Value, deadline=time.monotonic() + 3, stream_id=STREAM
                ) as stream:
                    with pytest.raises(YorungeError) as caught:
                        await anext(stream)
                    assert caught.value.code == "invalid_response"

        async def run():
            task = asyncio.create_task(reader())
            end = time.monotonic() + 2
            while not callback_entered.is_set():
                assert time.monotonic() < end
                await asyncio.sleep(0.005)
            await asyncio.sleep(0.02)
            assert not task.done(), "terminal escaped before its HTTP message completed"
            release.set()
            await task

        try:
            asyncio.run(run())
        finally:
            release.set()


@pytest.mark.parametrize(
    "body",
    [
        b"\n",
        b"\xef\xbb\xbf" + encode_event(result(1)),
        encode_event(result(1)).replace(b"\n", b"\r"),
        encode_event(result(1))[:-1],
        encode_event(result(1)) + b"\n",
        encode_event(result(1)) + encode_event(progress(2)),
        encode_event(progress()) + encode_event(result(1)),
        encode_event(result(1)).replace(STREAM.encode(), OTHER.encode()),
        encode_event(result(1)).replace(b'"schema_version":1', b'"schema_version":true', 1),
        encode_event(result(1)).replace(b'"sequence":1', b'"sequence":1,"sequence":1', 1),
        encode_event(result(1)).replace(b'"sequence":1', b'"sequence":NaN', 1),
        encode_event(result(1)).replace("Türkçe 🛰".encode(), b"\xff"),
    ],
    ids=[
        "blank",
        "bom",
        "lone-cr",
        "missing-last-lf",
        "trailing-blank",
        "trailing-event",
        "sequence-replay",
        "foreign-stream",
        "bool-version",
        "duplicate-key",
        "nonfinite",
        "invalid-utf8",
    ],
)
def test_protocol_faults_are_safe_invalid_response(certificates, body):
    with TlsServer(certificates, {"/v1/events": Reply(body=body, chunk_size=5)}) as server:
        with pytest.raises(YorungeError) as caught:
            collect(server)
        assert caught.value.code == "invalid_response"
        assert caught.value.__context__ is None
        assert caught.value.__cause__ is None
        assert len(server.requests) == 1


@pytest.mark.parametrize("body", [b"", encode_event(progress())])
def test_clean_message_eof_without_terminal_is_interrupted(certificates, body):
    with TlsServer(certificates, {"/v1/events": Reply(body=body)}) as server:
        with pytest.raises(YorungeError) as caught:
            collect(server)
        assert caught.value.code == "stream_interrupted"


@pytest.mark.parametrize(
    "prefix,expected",
    [
        (b"", "transport_failed"),
        (b'{"schema_version":', "invalid_response"),
        (encode_event(progress()), "stream_interrupted"),
        (encode_event(result(1)), "stream_interrupted"),
        (encode_event(progress()) + b'{"schema_version":', "invalid_response"),
    ],
    ids=["before-record", "partial-first", "after-progress", "after-terminal", "partial-last"],
)
def test_real_truncated_http_body_priority(certificates, prefix, expected):
    prefix = prefix.replace(
        b'"operation_id":null', b'"operation_id":"' + OPERATION.encode() + b'"', 1
    )
    body = prefix + b"missing-content-length-tail"
    with TlsServer(
        certificates,
        {"/v1/events": Reply(body=body, truncate_at=len(prefix), chunk_size=7)},
    ) as server:
        with pytest.raises(YorungeError) as caught:
            collect(server, operation_id=OPERATION)
        # Prefix IDs must bind for the intended transport-priority scenario.
        assert caught.value.code == expected
        assert isinstance(caught.value, OperationError)
        assert caught.value.envelope()["operation_id"] == OPERATION
        assert caught.value.__context__ is None
        assert caught.value.__cause__ is None
        assert len(server.requests) == 1


def test_terminal_wait_timeout_is_timeout_and_not_success(certificates):
    terminal = encode_event(result(1))
    with TlsServer(
        certificates,
        {"/v1/events": Reply(body=terminal + b" ", chunk_size=len(terminal), chunk_delay=0.3)},
    ) as server:
        with pytest.raises(YorungeError) as caught:
            collect(server, timeout=0.1)
        assert caught.value.code == "transport_timeout"
        assert len(server.requests) == 1


def test_provider_error_is_terminal_and_message_rebuilt_locally(certificates):
    original = ErrorEvent(
        schema_version=1,
        stream_id=STREAM,
        sequence=2,
        event="error",
        operation_id=OPERATION,
        payload=error_payload(YorungeError("remote_failed"), operation_id=OPERATION),
    )
    raw = original.model_dump(mode="json")
    raw["payload"]["message"] = SECRET
    body = encode_event(progress(operation_id=OPERATION)) + record(raw)
    with TlsServer(certificates, {"/v1/events": Reply(body=body, chunk_size=3)}) as server:
        events = collect(server, operation_id=OPERATION, secrets=(SecretValue(SECRET),))
        assert isinstance(events[-1], ErrorEvent)
        assert events[-1].payload.message == MESSAGES["remote_failed"]
        assert SECRET not in str(events[-1].model_dump(mode="json"))


def test_chunk_split_secret_never_becomes_a_result(certificates):
    body = encode_event(progress()) + encode_event(result(text="reflected " + SECRET))
    with TlsServer(certificates, {"/v1/events": Reply(body=body, chunk_size=2)}) as server:
        published = []

        async def run():
            async with HttpxTransport(transport=server.transport()) as transport:
                async with open_stream(
                    transport,
                    request(),
                    Value,
                    deadline=time.monotonic() + 3,
                    stream_id=STREAM,
                    secrets=(SecretValue(SECRET),),
                ) as stream:
                    with pytest.raises(YorungeError) as caught:
                        async for event in stream:
                            published.append(event)
                    assert caught.value.code == "invalid_response"

        asyncio.run(run())
        assert [item.event for item in published] == ["progress"]


@pytest.mark.parametrize("close_method", ["context", "aclose"])
def test_normal_early_close_closes_response_without_invented_cancellation(
    certificates, close_method
):
    first = encode_event(progress())
    body = first + encode_event(result(text="x" * 65_536))
    with TlsServer(
        certificates,
        {"/v1/events": Reply(body=body, chunk_size=len(first), chunk_delay=0.01)},
    ) as server:

        async def run():
            async with HttpxTransport(transport=server.transport()) as transport:
                async with open_stream(
                    transport, request(), Value, deadline=time.monotonic() + 3, stream_id=STREAM
                ) as stream:
                    assert isinstance(await anext(stream), ProgressEvent)
                    if close_method == "aclose":
                        await stream.aclose()
                        await stream.aclose()
                assert asyncio.current_task().cancelling() == 0
                with pytest.raises(YorungeError) as caught:
                    await anext(stream)
                assert caught.value.code == "invalid_request"

        asyncio.run(run())
        assert server.disconnected.wait(1)
        assert len(server.requests) == 1


def test_real_task_cancel_closes_response_and_propagates(certificates):
    first = encode_event(progress())
    release = threading.Event()

    def after_first():
        assert release.wait(3)

    with TlsServer(
        certificates,
        {
            "/v1/events": Reply(
                body=first + encode_event(result(text="x" * 65_536)),
                chunk_size=len(first),
                chunk_delay=0.01,
                after_first_chunk=after_first,
            )
        },
    ) as server:
        ready = asyncio.Event()

        async def run():
            async def reader():
                async with HttpxTransport(transport=server.transport()) as transport:
                    async with open_stream(
                        transport, request(), Value, deadline=time.monotonic() + 3, stream_id=STREAM
                    ) as stream:
                        assert isinstance(await anext(stream), ProgressEvent)
                        ready.set()
                        await anext(stream)

            task = asyncio.create_task(reader())
            await ready.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert task.cancelled()
            release.set()

        try:
            asyncio.run(run())
        finally:
            release.set()
        assert server.disconnected.wait(1)
        assert len(server.requests) == 1


def test_same_task_checks_every_resume_aclose_and_exit_before_http_context(certificates):
    body = encode_event(progress()) + encode_event(result())
    with TlsServer(certificates, {"/v1/events": Reply(body=body)}) as server:

        async def run():
            async with HttpxTransport(transport=server.transport()) as transport:
                context = open_stream(
                    transport, request(), Value, deadline=time.monotonic() + 3, stream_id=STREAM
                )
                async with context as stream:
                    assert isinstance(await anext(stream), ProgressEvent)

                    async def foreign(action):
                        with pytest.raises(YorungeError) as caught:
                            if action == "next":
                                await anext(stream)
                            elif action == "close":
                                await stream.aclose()
                            else:
                                await context.__aexit__(None, None, None)
                        assert caught.value.code == "invalid_request"

                    for action in ("next", "close", "exit"):
                        await asyncio.create_task(foreign(action))
                    assert isinstance(await anext(stream), ResultEvent)
                    assert asyncio.current_task().cancelling() == 0

        asyncio.run(run())


def test_invalid_composition_is_rejected_before_http(certificates):
    with TlsServer(certificates, {"/v1/events": Reply()}) as server:

        async def run():
            async with HttpxTransport(transport=server.transport()) as transport:
                with pytest.raises(YorungeError) as caught:
                    open_stream(
                        transport, request(), Value, deadline=time.monotonic() + 3, stream_id="bad"
                    )
                assert caught.value.code == "invalid_request"

        asyncio.run(run())
        assert server.requests == []


def test_consumer_backpressure_remains_inside_total_deadline(certificates):
    body = encode_event(progress(operation_id=OPERATION)) + encode_event(
        result(operation_id=OPERATION)
    )
    with TlsServer(certificates, {"/v1/events": Reply(body=body)}) as server:
        published = []

        async def run():
            async with HttpxTransport(transport=server.transport()) as transport:
                async with open_stream(
                    transport,
                    request(),
                    Value,
                    deadline=time.monotonic() + 0.15,
                    stream_id=STREAM,
                    operation_id=OPERATION,
                ) as stream:
                    published.append(await anext(stream))
                    await asyncio.sleep(1)
                    pytest.fail("slow consumer escaped the shared total deadline")

        with pytest.raises(OperationError) as caught:
            asyncio.run(run())
        assert caught.value.code == "transport_timeout"
        assert caught.value.operation_id == OPERATION
        assert [item.event for item in published] == ["progress"]
        assert caught.value.__context__ is None


def test_response_context_is_closed_if_chunk_iterator_cannot_be_opened():
    from contextlib import asynccontextmanager

    closed = []

    class Response:
        def chunks(self):
            raise YorungeError("invalid_response")

    class Transport:
        @asynccontextmanager
        async def open(self, wanted, *, deadline):
            try:
                yield Response()
            finally:
                closed.append(True)

    async def run():
        async with open_stream(
            Transport(), request(), Value, deadline=time.monotonic() + 1, stream_id=STREAM
        ):
            pytest.fail("broken chunk iterator entered the consumer context")

    with pytest.raises(YorungeError) as caught:
        asyncio.run(run())
    assert caught.value.code == "invalid_response"
    assert caught.value.__context__ is None
    assert closed == [True]
