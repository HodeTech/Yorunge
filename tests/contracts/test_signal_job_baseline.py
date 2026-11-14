"""A foreground test job normalizes inherited SIGINT once, then restores it."""

import signal
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TARGETS = (
    "tests/contracts/test_http_session.py::test_real_sigint_cleans_up_then_becomes_keyboard_interrupt_in_sync_caller",
    "tests/integration/test_upload_public_api.py::test_actual_sigint_after_coordinator_result_keeps_the_known_operation_id",
    "tests/integration/test_cli_signals.py::test_sigint_distinguishes_prepublication_uncertainty_and_confirmed_publication[init-stage-before-False-6-0-json]",
)


@pytest.mark.parametrize(
    "kind", ["handler", *(["mask"] if hasattr(signal, "pthread_sigmask") else [])]
)
def test_per_test_signal_check_detects_a_leak_without_resetting_it(kind):
    from tests.fixtures.signal_baseline import assert_foreground_signals

    handler = signal.getsignal(signal.SIGINT)
    mask = None
    try:
        if kind == "handler":
            signal.signal(signal.SIGINT, signal.SIG_IGN)
        else:
            mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT})
        with pytest.raises(AssertionError, match="leaked"):
            assert_foreground_signals()
        if kind == "handler":
            assert signal.getsignal(signal.SIGINT) == signal.SIG_IGN
        else:
            assert signal.SIGINT in signal.pthread_sigmask(signal.SIG_BLOCK, set())
    finally:
        signal.signal(signal.SIGINT, handler)
        if mask is not None:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)


@pytest.mark.parametrize(
    "mode", ["ignored", *(["blocked"] if hasattr(signal, "pthread_sigmask") else [])]
)
def test_nested_foreground_job_handles_real_sigint_and_restores_launcher_policy(mode):
    code = """
import signal, sys
import pytest
mode = sys.argv[1]
if mode == 'ignored':
    signal.signal(signal.SIGINT, signal.SIG_IGN)
else:
    signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT})
handler = signal.getsignal(signal.SIGINT)
mask = None
if hasattr(signal, 'pthread_sigmask'):
    mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
result = pytest.main(['-q', '--override-ini=addopts=', *sys.argv[2:]])
assert signal.getsignal(signal.SIGINT) == handler, 'launcher handler not restored'
if mask is not None:
    assert signal.pthread_sigmask(signal.SIG_BLOCK, set()) == mask, 'launcher mask not restored'
raise SystemExit(result)
"""
    found = subprocess.run(
        [sys.executable, "-c", code, mode, *TARGETS],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,  # a hang guard (the run takes seconds); 45 s was missed once under load
    )
    assert found.returncode == 0, found.stdout + found.stderr
    assert "3 passed" in found.stdout
