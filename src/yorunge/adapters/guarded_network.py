"""Transfer-only public-address resolution, pinned TCP and pre-HTTP peer verification."""

from __future__ import annotations

import asyncio
import ipaddress
import math
import socket
import ssl
import time
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, NoReturn

import httpcore

from yorunge.domain.errors import YorungeError

SocketOption = (
    tuple[int, int, int] | tuple[int, int, bytes | bytearray] | tuple[int, int, None, int]
)
Resolver = Callable[[str, int, float], Awaitable[tuple[str, ...]]]
MAX_DNS_ADDRESSES = 16


def _phase_timeout(value: float | None) -> float:
    if value is None:
        return 5.0
    valid = type(value) in (int, float)
    try:
        valid = valid and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise YorungeError("invalid_request")
    if value <= 0:
        raise httpcore.ConnectTimeout("connection deadline elapsed")
    return min(5.0, value)


_V4_SPECIAL = tuple(
    ipaddress.ip_network(net)
    for net in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/4",
        "240.0.0.0/4",
    )
)
_V6_SPECIAL = tuple(
    ipaddress.ip_network(net)
    for net in (
        "2001::/23",
        "2001:db8::/32",
        "2002::/16",
        "3fff::/20",
    )
)
_V6_UNICAST = ipaddress.ip_network("2000::/3")


def address(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    if type(value) is not str or "%" in value:
        raise ValueError("unscoped IP address required")
    result = ipaddress.ip_address(value)
    if isinstance(result, ipaddress.IPv6Address) and result.ipv4_mapped is not None:
        return result.ipv4_mapped
    return result


def public_address(value: str) -> bool:
    try:
        ip = address(value)
    except ValueError:
        return False
    if not ip.is_global or ip.is_multicast or ip.is_reserved:
        return False
    if isinstance(ip, ipaddress.IPv4Address):
        return not any(ip in network for network in _V4_SPECIAL)
    return ip in _V6_UNICAST and not any(ip in network for network in _V6_SPECIAL)


async def resolve(host: str, port: int, timeout: float) -> tuple[str, ...]:
    try:
        literal = address(host)
    except ValueError:
        literal = None
    if literal is not None:
        return (str(literal),)
    try:
        async with asyncio.timeout(timeout):
            rows = await asyncio.get_running_loop().getaddrinfo(
                host,
                port,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
            )
    except TimeoutError:
        raise httpcore.ConnectTimeout("bounded DNS resolution timed out") from None
    except OSError:
        raise httpcore.ConnectError("bounded DNS resolution failed") from None
    if not rows or len(rows) > MAX_DNS_ADDRESSES:
        raise YorungeError("invalid_service_target")
    try:
        return tuple(dict.fromkeys(str(address(str(row[4][0]))) for row in rows))
    except (ValueError, TypeError, IndexError):
        raise YorungeError("invalid_service_target") from None


class GuardedStream(httpcore.AsyncNetworkStream):
    def __init__(
        self,
        stream: httpcore.AsyncNetworkStream,
        host: str,
        approved: frozenset[str],
        allowed: Callable[[str], bool],
    ) -> None:
        self._stream, self._host = stream, host
        self._approved, self._allowed = approved, allowed

    def peer_valid(self) -> bool:
        try:
            peer = self._stream.get_extra_info("server_addr")
            if not isinstance(peer, tuple) or not peer or type(peer[0]) is not str:
                return False
            ip = str(address(peer[0]))
            return ip in self._approved and self._allowed(ip)
        except (ValueError, OSError):
            return False

    async def reject(self) -> NoReturn:
        try:
            await self._stream.aclose()
        except (OSError, httpcore.NetworkError, httpcore.TimeoutException):
            raise YorungeError("invalid_service_target") from None
        raise YorungeError("invalid_service_target")

    async def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        if not self.peer_valid():
            await self.reject()
        return await self._stream.read(max_bytes, timeout)

    async def write(self, buffer: bytes, timeout: float | None = None) -> None:
        if not self.peer_valid():
            await self.reject()
        await self._stream.write(buffer, timeout)

    async def aclose(self) -> None:
        await self._stream.aclose()

    async def start_tls(
        self,
        ssl_context: ssl.SSLContext,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> httpcore.AsyncNetworkStream:
        if (
            server_hostname != self._host
            or not ssl_context.check_hostname
            or ssl_context.verify_mode != ssl.CERT_REQUIRED
            or not self.peer_valid()
        ):
            await self.reject()
        encrypted = await self._stream.start_tls(ssl_context, server_hostname, timeout)
        result = GuardedStream(encrypted, self._host, self._approved, self._allowed)
        if not result.peer_valid():
            await result.reject()
        return result

    def get_extra_info(self, info: str) -> Any:
        return self._stream.get_extra_info(info)


class GuardedBackend(httpcore.AsyncNetworkBackend):
    """Injection seams are private test composition, never config or caller flags."""

    def __init__(
        self,
        *,
        resolver: Resolver = resolve,
        backend: httpcore.AsyncNetworkBackend | None = None,
        allowed: Callable[[str], bool] = public_address,
    ) -> None:
        self._resolver, self._backend, self._allowed = (
            resolver,
            backend or httpcore.AnyIOBackend(),
            allowed,
        )

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[SocketOption] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        if port != 443 or local_address is not None:
            raise YorungeError("invalid_service_target")
        timeout = _phase_timeout(timeout)
        end = time.monotonic() + timeout
        try:
            async with asyncio.timeout(timeout):
                addresses = await self._resolver(host, port, timeout)
                if type(addresses) is not tuple or not 1 <= len(addresses) <= MAX_DNS_ADDRESSES:
                    raise YorungeError("invalid_service_target")
                try:
                    pinned = tuple(str(address(item)) for item in addresses)
                except (ValueError, TypeError):
                    raise YorungeError("invalid_service_target") from None
                if not all(self._allowed(item) for item in pinned):
                    raise YorungeError("invalid_service_target")
                # A numeric IP is passed to the backend, never the original hostname.
                remaining = end - time.monotonic()
                if remaining <= 0:
                    raise httpcore.ConnectTimeout("connection deadline elapsed")
                stream = await self._connect(pinned[0], port, remaining, socket_options, host)
                guarded = GuardedStream(stream, host, frozenset({pinned[0]}), self._allowed)
                if not guarded.peer_valid():
                    await guarded.reject()
                return guarded
        except TimeoutError:
            raise httpcore.ConnectTimeout("connection deadline elapsed") from None

    async def _connect(
        self,
        pinned: str,
        port: int,
        timeout: float,
        options: Iterable[SocketOption] | None,
        original_host: str,
    ) -> httpcore.AsyncNetworkStream:
        return await self._backend.connect_tcp(
            pinned, port, timeout=timeout, socket_options=options
        )

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[SocketOption] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        raise YorungeError("invalid_service_target")

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)
