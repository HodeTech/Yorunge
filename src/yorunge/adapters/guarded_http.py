"""HTTPX transport over one public HTTPcore pool with a pinned network backend."""

from __future__ import annotations

import ssl
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from types import TracebackType

import httpcore
import httpx

from yorunge.adapters.guarded_network import GuardedBackend
from yorunge.domain.errors import YorungeError

_ERRORS: tuple[tuple[type[Exception], type[httpx.HTTPError]], ...] = (
    (httpcore.ConnectTimeout, httpx.ConnectTimeout),
    (httpcore.ReadTimeout, httpx.ReadTimeout),
    (httpcore.WriteTimeout, httpx.WriteTimeout),
    (httpcore.PoolTimeout, httpx.PoolTimeout),
    (httpcore.TimeoutException, httpx.TimeoutException),
    (httpcore.ConnectError, httpx.ConnectError),
    (httpcore.ReadError, httpx.ReadError),
    (httpcore.WriteError, httpx.WriteError),
    (httpcore.RemoteProtocolError, httpx.RemoteProtocolError),
    (httpcore.LocalProtocolError, httpx.LocalProtocolError),
    (httpcore.UnsupportedProtocol, httpx.UnsupportedProtocol),
    (httpcore.NetworkError, httpx.NetworkError),
    (httpcore.ProtocolError, httpx.ProtocolError),
)


@contextmanager
def core_errors() -> Iterator[None]:
    try:
        yield
    except (
        httpcore.TimeoutException,
        httpcore.NetworkError,
        httpcore.ProtocolError,
        httpcore.UnsupportedProtocol,
    ) as error:
        for original, mapped in _ERRORS:
            if isinstance(error, original):
                # Preserve the private SSL cause for the service retry gate. The
                # owned facade normalizes outside its exception handler, so no
                # raw target/body/exception text enters a public error.
                raise mapped("private network exchange failed") from error
        raise


class CoreResponseStream(httpx.AsyncByteStream):
    def __init__(self, response: httpcore.Response) -> None:
        self._response = response
        self._iterator = response.aiter_stream()

    def __aiter__(self) -> AsyncIterator[bytes]:
        return self

    async def __anext__(self) -> bytes:
        with core_errors():
            return await anext(self._iterator)

    async def aclose(self) -> None:
        with core_errors():
            await self._response.aclose()


class GuardedHttpTransport(httpx.AsyncBaseTransport):
    def __init__(
        self,
        *,
        backend: GuardedBackend | None = None,
        verify: ssl.SSLContext | None = None,
    ) -> None:
        context = verify or httpx.create_ssl_context(trust_env=False)
        if (
            not context.check_hostname
            or context.verify_mode != ssl.CERT_REQUIRED
            or (backend is not None and not isinstance(backend, GuardedBackend))
        ):
            raise YorungeError("invalid_request")
        # CPython accepts None; the bundled ssl typing stub declares only str.
        context.keylog_filename = None  # type: ignore[assignment]
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=context,
            max_connections=2,
            max_keepalive_connections=2,
            keepalive_expiry=5.0,
            http1=True,
            http2=False,
            retries=0,
            network_backend=backend or GuardedBackend(),
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.scheme != "https" or request.url.port not in (None, 443):
            raise YorungeError("invalid_service_target")
        if not isinstance(request.stream, httpx.AsyncByteStream):
            raise YorungeError("invalid_request")
        core = httpcore.Request(
            method=request.method,
            url=httpcore.URL(
                scheme=request.url.raw_scheme,
                host=request.url.raw_host,
                port=request.url.port,
                target=request.url.raw_path,
            ),
            headers=request.headers.raw,
            content=request.stream,
            extensions=request.extensions,
        )
        with core_errors():
            response = await self._pool.handle_async_request(core)
        return httpx.Response(
            status_code=response.status,
            headers=response.headers,
            stream=CoreResponseStream(response),
            extensions=response.extensions,
        )

    async def __aenter__(self) -> GuardedHttpTransport:
        with core_errors():
            await self._pool.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        with core_errors():
            await self._pool.__aexit__(exc_type, exc, traceback)

    async def aclose(self) -> None:
        with core_errors():
            await self._pool.aclose()
