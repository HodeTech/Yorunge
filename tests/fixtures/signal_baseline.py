"""Controlled foreground test jobs; product code keeps the caller's signal policy."""

import signal
from contextlib import contextmanager


@contextmanager
def foreground_signals():
    handler = signal.getsignal(signal.SIGINT)
    mask = None
    signal.signal(signal.SIGINT, signal.default_int_handler)
    try:
        if hasattr(signal, "pthread_sigmask"):
            mask = signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGINT})
        yield
    finally:
        signal.signal(signal.SIGINT, handler)
        if mask is not None:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)


def assert_foreground_signals():
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler, "SIGINT handler leaked"
    if hasattr(signal, "pthread_sigmask"):
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        assert signal.SIGINT not in mask, "SIGINT mask leaked"
