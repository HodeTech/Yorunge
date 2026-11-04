"""Standard Python DNS/datagram entry points fail before sending offline traffic.

This fixture is an accidental-I/O guard, not a sandbox for native extensions.
"""

import socket

import pytest


@pytest.mark.parametrize(
    "method,args",
    [
        ("getaddrinfo", ("external.invalid", 443)),
        ("gethostbyname", ("external.invalid",)),
        ("gethostbyname_ex", ("external.invalid",)),
        ("gethostbyaddr", ("203.0.113.1",)),
        ("getnameinfo", (("203.0.113.1", 443), 0)),
    ],
)
def test_offline_standard_dns_entry_points_are_blocked(method, args):
    invoke = getattr(socket, method)
    with pytest.raises(AssertionError, match="network is forbidden"):
        invoke(*args)


@pytest.mark.parametrize(
    "method,args",
    [
        ("connect", (("203.0.113.1", 443),)),
        ("connect_ex", (("203.0.113.1", 443),)),
        ("sendto", (b"synthetic", ("203.0.113.1", 443))),
        *(
            [("sendmsg", ([b"synthetic"], [], 0, ("203.0.113.1", 443)))]
            if hasattr(socket.socket, "sendmsg")
            else []
        ),
    ],
)
def test_offline_datagram_and_connect_entry_points_are_blocked(method, args):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as channel:
        invoke = getattr(channel, method)
        with pytest.raises(AssertionError, match="network is forbidden"):
            invoke(*args)
