"""Independent public-address, mixed-DNS, pin and peer oracles without network."""

import asyncio
import ssl

import httpcore
import pytest

from yorunge.adapters.guarded_network import GuardedBackend, GuardedStream, public_address
from yorunge.domain.errors import YorungeError


@pytest.mark.parametrize(
    "ip",
    [
        "0.0.0.0",
        "10.0.0.1",
        "100.64.0.1",
        "127.0.0.1",
        "169.254.169.254",
        "172.16.2.1",
        "192.168.1.1",
        "192.0.0.8",
        "192.0.0.9",
        "192.0.2.1",
        "198.18.0.1",
        "198.51.100.1",
        "203.0.113.1",
        "224.0.0.1",
        "255.255.255.255",
        "::",
        "::1",
        "::ffff:127.0.0.1",
        "::ffff:10.0.0.1",
        "64:ff9b::a00:1",
        "64:ff9b:1::1",
        "100::1",
        "2001:db8::1",
        "2002:a00:1::1",
        "3fff::1",
        "fc00::1",
        "fe80::1",
        "fe80::1%en0",
        "fec0::1",
        "ff02::1",
        "not-an-ip",
    ],
)
def test_special_or_ambiguous_addresses_are_never_public(ip):
    assert public_address(ip) is False


@pytest.mark.parametrize(
    "ip",
    [
        "1.1.1.1",
        "8.8.8.8",
        "9.9.9.9",
        "172.64.0.1",
        "2001:4860:4860::8888",
        "2606:4700:4700::1111",
        "::ffff:8.8.8.8",
    ],
)
def test_common_public_unicast_and_mapped_public_addresses(ip):
    assert public_address(ip) is True


class Stream(httpcore.AsyncNetworkStream):
    def __init__(self, peer=("8.8.8.8", 443)):
        self.peer, self.closed, self.writes, self.sni = peer, False, [], None

    def get_extra_info(self, name):
        return self.peer if name == "server_addr" else None

    async def read(self, max_bytes, timeout=None):
        return b""

    async def write(self, buffer, timeout=None):
        self.writes.append(buffer)

    async def aclose(self):
        self.closed = True

    async def start_tls(self, context, server_hostname=None, timeout=None):
        self.sni = server_hostname
        return self


class Connector(httpcore.AsyncNetworkBackend):
    def __init__(self, stream):
        self.stream, self.calls = stream, []

    async def connect_tcp(self, host, port, **kwargs):
        self.calls.append((host, port))
        return self.stream


def test_dns_is_pinned_once_and_original_sni_is_preserved():
    stream, resolutions = Stream(), []
    connector = Connector(stream)

    async def resolve(host, port, timeout):
        resolutions.append((host, port))
        return ("8.8.8.8", "1.1.1.1")

    backend = GuardedBackend(resolver=resolve, backend=connector)

    async def run():
        connection = await backend.connect_tcp("storage.example", 443)
        tls = await connection.start_tls(ssl.create_default_context(), "storage.example")
        await tls.write(b"approved HTTP bytes")
        await tls.aclose()

    asyncio.run(run())
    assert resolutions == [("storage.example", 443)]
    assert connector.calls == [("8.8.8.8", 443)]
    assert stream.sni == "storage.example"
    assert stream.writes == [b"approved HTTP bytes"] and stream.closed


@pytest.mark.parametrize("changed_at", ["connect", "tls", "reuse"])
def test_another_public_dns_answer_cannot_replace_the_selected_peer(changed_at):
    stream = Stream()
    connector = Connector(stream)

    async def resolver(*args):
        return ("8.8.8.8", "1.1.1.1")

    backend = GuardedBackend(resolver=resolver, backend=connector)

    async def run():
        if changed_at == "connect":
            stream.peer = ("1.1.1.1", 443)
        connection = await backend.connect_tcp("storage.example", 443)
        if changed_at == "tls":
            original = stream.start_tls

            async def replaced_peer(context, server_hostname=None, timeout=None):
                result = await original(context, server_hostname, timeout)
                stream.peer = ("1.1.1.1", 443)
                return result

            stream.start_tls = replaced_peer
        tls = await connection.start_tls(ssl.create_default_context(), "storage.example")
        if changed_at == "reuse":
            stream.peer = ("1.1.1.1", 443)
        await tls.write(b"must never be sent")

    with pytest.raises(YorungeError) as failure:
        asyncio.run(run())
    assert failure.value.code == "invalid_service_target"
    assert connector.calls == [("8.8.8.8", 443)] and stream.closed
    assert stream.writes == []


@pytest.mark.parametrize(
    "answers",
    [
        ("8.8.8.8", "127.0.0.1"),
        ("8.8.8.8", "::ffff:169.254.169.254"),
        (),
        ("8.8.8.8",) * 17,
        ("bad",),
    ],
)
def test_mixed_private_or_unbounded_dns_is_rejected_before_tcp(answers):
    connector = Connector(Stream())

    async def resolver(*args):
        return answers

    async def run():
        await GuardedBackend(resolver=resolver, backend=connector).connect_tcp(
            "storage.example", 443
        )

    with pytest.raises(YorungeError) as failure:
        asyncio.run(run())
    assert failure.value.code == "invalid_service_target"
    assert connector.calls == []


@pytest.mark.parametrize("peer", [("127.0.0.1", 443), ("1.1.1.1", 443), None, ("bad", 443)])
def test_actual_unapproved_peer_closes_before_http_bytes(peer):
    stream = Stream(peer)
    connector = Connector(stream)

    async def resolver(*args):
        return ("8.8.8.8",)

    async def run():
        await GuardedBackend(resolver=resolver, backend=connector).connect_tcp(
            "storage.example", 443
        )

    with pytest.raises(YorungeError):
        asyncio.run(run())
    assert stream.closed and stream.writes == []


def test_peer_change_after_validation_is_rejected_on_pool_reuse_write():
    stream = Stream()
    guarded = GuardedStream(stream, "storage.example", frozenset({"8.8.8.8"}), public_address)
    stream.peer = ("127.0.0.1", 443)
    with pytest.raises(YorungeError):
        asyncio.run(guarded.write(b"must never reach peer"))
    assert stream.closed and stream.writes == []


@pytest.mark.parametrize("mode", ["wrong-sni", "tls-verification-disabled"])
def test_tls_original_host_and_certificate_verification_are_required(mode):
    stream = Stream()
    guarded = GuardedStream(stream, "storage.example", frozenset({"8.8.8.8"}), public_address)
    context = ssl.create_default_context()
    host = "storage.example"
    if mode == "wrong-sni":
        host = "other.example"
    else:
        context.check_hostname = False
    with pytest.raises(YorungeError):
        asyncio.run(guarded.start_tls(context, host))
    assert stream.closed and stream.sni is None and stream.writes == []


def test_dns_and_connect_share_one_phase_deadline():
    connector = Connector(Stream())

    async def slow(*args):
        await asyncio.sleep(0.03)
        return ("8.8.8.8",)

    async def run():
        await GuardedBackend(resolver=slow, backend=connector).connect_tcp(
            "storage.example", 443, timeout=0.01
        )

    with pytest.raises(httpcore.ConnectTimeout):
        asyncio.run(run())
    assert connector.calls == []


@pytest.mark.parametrize(
    "timeout", [float("nan"), float("inf"), float("-inf"), True, "5", 10**1000]
)
def test_invalid_connect_timeout_never_resolves_or_connects(timeout):
    called = []

    async def resolver(*args):
        called.append(True)
        return ("8.8.8.8",)

    async def run():
        await GuardedBackend(resolver=resolver).connect_tcp("storage.example", 443, timeout=timeout)

    with pytest.raises(YorungeError) as failure:
        asyncio.run(run())
    assert failure.value.code == "invalid_request" and not called
