"""Real read-process death and re-read; no second upload or source files are needed."""

import multiprocessing
import os
import signal
import ssl
import time
from datetime import timedelta
from functools import partial
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.http_server import TlsServer
from tests.fixtures.upload_provider import UploadProvider
from tests.integration.test_upload_file_workflow import certificates as certificates
from tests.integration.test_upload_file_workflow import loopback_only as loopback_only
from tests.integration.test_upload_original import denied, factory, loader
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_reconcile_probe import ready
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_reconciliation import reconcile_upload
from yorunge.adapters.upload_repository import StateUploads
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.errors import OperationError


def _child_read(state, operation_id, context, profile, port, ca, now, elapsed, boundary, pipe):
    from yorunge.adapters import capability_cache
    from yorunge.adapters.upload_reconciliation import _ReadEnvironment
    from yorunge.domain.models import Context, Profile

    class Clock:
        def now(self):
            return instant(now)

        def monotonic(self):
            return time.monotonic() + elapsed

    clock = Clock()
    capability_cache.SystemClock = lambda: clock
    endpoint = SimpleNamespace(
        port=port, client_context=lambda: ssl.create_default_context(cafile=ca)
    )
    original_acquire, original_metadata = _ReadEnvironment.acquire, _ReadEnvironment.metadata
    original_verified, original_control = StateUploads.verified, StateUploads._control

    def pause():
        pipe.send("paused")
        pipe.recv()
        raise AssertionError("killed read resumed")

    def acquire(environment, check):
        original_acquire(environment, check)
        if boundary == "read_acquire":
            pause()

    async def metadata(environment):
        result = await original_metadata(environment)
        if boundary == "metadata_received":
            pause()
        return result

    def control(repository, *args, **kwargs):
        original_control(repository, *args, **kwargs)
        if boundary == "proof_before_commit" and kwargs.get("proof") is not None:
            pause()

    def verified(repository, *args, **kwargs):
        result = original_verified(repository, *args, **kwargs)
        if boundary == "proof_commit":
            pause()
        return result

    _ReadEnvironment.acquire, _ReadEnvironment.metadata = acquire, metadata
    StateUploads._control, StateUploads.verified = control, verified
    reconcile_upload(
        operation_id,
        Path(state),
        lambda plan: (Context.model_validate(context), Profile.model_validate(profile)),
        accept_unverified_read=True,
        session_factory=factory(endpoint),
        clock=clock,
    )
    pipe.send("unexpected return")


@pytest.mark.parametrize(
    "boundary,terminal,reads",
    [
        ("read_acquire", False, 5),
        ("metadata_received", False, 6),
        ("proof_before_commit", False, 6),
        ("proof_commit", True, 6),
    ],
)
def test_sigkill_read_never_resumes_write_and_requires_valid_new_read_owner(
    prepared_input, certificates, execution_clock, monkeypatch, boundary, terminal, reads
):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        _, operation_id = ready(prepared_input, server, execution_clock)
        (prepared_input[1] / "one.bin").unlink()
        prepared_input[1].rmdir()
        count = len(server.requests)
        process_context = multiprocessing.get_context("spawn")
        parent, child = process_context.Pipe()
        process = process_context.Process(
            target=_child_read,
            args=(
                str(prepared_input[0]),
                operation_id,
                prepared_input[3].model_dump(mode="json"),
                prepared_input[4].model_dump(mode="json"),
                server.port,
                str(certificates[0]),
                timestamp(execution_clock.value),
                execution_clock.elapsed,
                boundary,
                child,
            ),
        )
        process.start()
        child.close()
        try:
            assert parent.poll(20), "read child did not reach crash window"
            assert parent.recv() == "paused"
            os.kill(process.pid, signal.SIGKILL)
            process.join(5)
            assert process.exitcode == -signal.SIGKILL
        finally:
            if process.is_alive():
                process.kill()
                process.join(5)
            parent.close()
        assert len(server.requests) == count + reads
        assert all(request.method == "GET" for request in server.requests[count:])
        count = len(server.requests)
        rejected = partial(
            reconcile_upload,
            operation_id,
            prepared_input[0],
            denied,
            accept_unverified_read=True,
            session_factory=denied,
            clock=execution_clock,
        )
        with pytest.raises(OperationError) as raised:
            rejected()
        assert raised.value.code == "operation_conflict"
        assert len(server.requests) == count
        with open_existing_store(prepared_input[0]) as store:
            view = StateUploads(store).show(operation_id=operation_id)
            assert view.operation.status == ("succeeded" if terminal else "unknown")
            assert (view.verification is not None) == terminal
            assert len(view.intents) == len(view.receipts) == 5
            if not terminal:
                assert view.operation.lease.mode == "read"
                fence = view.operation.fence
            assert store.verify().store_schema_version == 7
        if not terminal:
            execution_clock.value += timedelta(seconds=151)
            execution_clock.elapsed += 151
            result = reconcile_upload(
                operation_id,
                prepared_input[0],
                loader(prepared_input),
                accept_unverified_read=True,
                session_factory=factory(server),
                clock=execution_clock,
            )
            assert result.record.status == "succeeded"
            assert result.record.operation_id == operation_id
            assert result.record.fence > fence
            assert result.record.lease is None
            assert len(server.requests) == count + 6
            with open_existing_store(prepared_input[0]) as store:
                view = StateUploads(store).show(operation_id=operation_id)
                assert view.verification is not None
                assert len(view.receipts) == 5
                assert store.verify().store_schema_version == 7
        assert (
            provider.create_calls
            == provider.link_calls
            == provider.put_calls
            == provider.confirm_calls
            == 1
        )
