"""Fault injection protects the private exception and task ownership boundary."""

import asyncio
import logging
import time

import httpx
import pytest

from yorunge.adapters.http_transport import HttpxTransport
from yorunge.application.http_transport import HttpCredential, HttpRequest
from yorunge.domain.credentials import SecretValue, normalize_target
from yorunge.domain.errors import YorungeError

CANARY = "http-private-exception-chain-713621"
TARGET = normalize_target("https://example.test/v1")


def request(**changes):
    return HttpRequest(
        TARGET,
        "GET",
        "data",
        service_id="evren-platform",
        credential=HttpCredential(
            "Authorization", SecretValue(CANARY), target=TARGET, service_id="evren-platform"
        ),
        **changes,
    )


@pytest.mark.parametrize("fault", ["connect", "timeout", "read", "retry-close"])
def test_private_library_fault_chain_is_removed_not_only_hidden(fault):
    calls = []

    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            if fault == "read":
                raise httpx.ReadError(CANARY, request=calls[0])
            yield b"response"

        async def aclose(self):
            if fault == "retry-close":
                raise OSError(CANARY)

    async def handler(wire):
        calls.append(wire)
        if fault == "connect":
            raise httpx.ConnectError(CANARY, request=wire)
        if fault == "timeout":
            raise httpx.ReadTimeout(CANARY, request=wire)
        return httpx.Response(503 if fault == "retry-close" else 200, stream=Stream())

    async def run():
        async with HttpxTransport(transport=httpx.MockTransport(handler)) as transport:
            async with transport.open(
                request(read_only=fault == "retry-close"), deadline=time.monotonic() + 2
            ) as response:
                async for _ in response.chunks():
                    pass

    with pytest.raises(YorungeError) as caught:
        asyncio.run(run())
    error = caught.value
    assert error.code == ("transport_timeout" if fault == "timeout" else "transport_failed")
    assert error.__context__ is None
    assert error.__cause__ is None
    assert CANARY not in str(error.envelope())
    assert len(calls) == 1


@pytest.mark.parametrize("deadline", [10**1000, True, float("nan"), float("inf"), "30"])
def test_invalid_deadline_never_reaches_the_wire(deadline):
    calls = []

    async def handler(wire):
        calls.append(wire)
        return httpx.Response(200, content=b"ok")

    async def run():
        async with HttpxTransport(transport=httpx.MockTransport(handler)) as transport:
            async with transport.open(request(), deadline=deadline):
                pytest.fail("invalid deadline reached consumer")

    with pytest.raises(YorungeError) as caught:
        asyncio.run(run())
    assert caught.value.code == "invalid_request"
    assert caught.value.__context__ is None
    assert calls == []


def test_foreign_context_exit_is_rejected_before_it_changes_the_owner_context(caplog):
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"response"

    async def handler(wire):
        return httpx.Response(200, stream=Stream())

    async def run():
        async with HttpxTransport(transport=httpx.MockTransport(handler)) as transport:
            context = transport.open(request(), deadline=time.monotonic() + 2)
            response = await context.__aenter__()
            try:

                async def foreign_exit():
                    await context.__aexit__(None, None, None)

                with pytest.raises(YorungeError) as caught:
                    await asyncio.create_task(foreign_exit())
                assert caught.value.code == "invalid_request"
                logging.getLogger("httpx").info(CANARY)
                assert b"".join([chunk async for chunk in response.chunks()]) == b"response"
            finally:
                await context.__aexit__(None, None, None)
        logging.getLogger("httpx").info("owner-context-restored")

    with caplog.at_level(logging.INFO):
        asyncio.run(run())
    assert CANARY not in caplog.text
    assert "owner-context-restored" in caplog.text


def test_ownership_is_checked_on_every_next_and_foreign_next_preserves_iterator():
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"a" * 32_768
            yield b"b" * 32_768

    async def handler(wire):
        return httpx.Response(200, stream=Stream())

    async def run():
        async with HttpxTransport(transport=httpx.MockTransport(handler)) as transport:
            async with transport.open(request(), deadline=time.monotonic() + 2) as response:
                iterator = response.chunks()
                assert await anext(iterator) == b"a" * 32_768

                async def foreign_next():
                    return await anext(iterator)

                with pytest.raises(YorungeError) as caught:
                    await asyncio.create_task(foreign_next())
                assert caught.value.code == "invalid_request"
                assert await anext(iterator) == b"b" * 32_768
                with pytest.raises(StopAsyncIteration):
                    await anext(iterator)

    asyncio.run(run())


def test_client_construction_failure_has_no_private_exception_chain(monkeypatch):
    def unavailable(*args, **kwargs):
        raise OSError(CANARY)

    monkeypatch.setattr(httpx, "AsyncHTTPTransport", unavailable)

    async def run():
        async with HttpxTransport():
            pytest.fail("unavailable client entered")

    with pytest.raises(YorungeError) as caught:
        asyncio.run(run())
    assert caught.value.code == "transport_failed"
    assert caught.value.__context__ is None
    assert CANARY not in str(caught.value)
