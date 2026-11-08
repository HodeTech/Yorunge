"""A real process that reconciles a continuation dies; the record is found as it was left (P02-3x).

The child is the v2 reconcile test's own (it pauses at a named boundary of the read and is killed
there); only the operation it reads is a continuation's. At each boundary the store validates, the
read lease the dead process took keeps others out while it lives, the proof is either whole or
absent, nothing is ever sent, and once the lease has lapsed the next reconcile proves the same
operation.
"""

import multiprocessing
import os
import signal
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.fixtures.http_server import TlsServer
from tests.integration.test_upload_continuation_reconcile import (
    left_unproved,
    reconcile,
    source_record,
    store_is_valid,
)
from tests.integration.test_upload_continuation_stages import (
    Skewed,
    journal,
    planned,
)
from tests.integration.test_upload_continuation_start import approve
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_reconciliation_kill import _child_read
from tests.integration.test_upload_resume_observation import (
    certificates as certificates,
)
from tests.integration.test_upload_resume_observation import (
    loopback_only as loopback_only,
)
from tests.integration.test_upload_resume_observation import world as three_files
from yorunge.domain.capabilities import timestamp
from yorunge.domain.dataset_transfer_v3 import TransferVerificationV3
from yorunge.domain.errors import OperationError


@pytest.mark.parametrize(
    "boundary,terminal",
    [
        ("read_acquire", False),
        ("metadata_received", False),
        ("proof_before_commit", False),
        ("proof_commit", True),
    ],
)
def test_sigkill_of_a_continuations_reconcile_leaves_it_unproved_or_proved_and_never_half(
    prepared_input, certificates, monkeypatch, boundary, terminal
):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    data, provider = three_files(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        report = planned(data, server, provider)
        approve(data, server, report.plan_id)
        operation_id = left_unproved(data, provider, server, report.plan_id, monkeypatch)
        before = source_record(data, operation_id)
        sends, count = len(provider.events), len(server.requests)
        spawned = multiprocessing.get_context("spawn")
        parent, child = spawned.Pipe()
        process = spawned.Process(
            target=_child_read,
            args=(
                str(data[0]),
                operation_id,
                data[3].model_dump(mode="json"),
                data[4].model_dump(mode="json"),
                server.port,
                str(certificates[0]),
                timestamp(datetime.now(UTC)),
                0.0,
                boundary,
                child,
            ),
        )
        process.start()
        child.close()
        try:
            assert parent.poll(60), "the reconcile child did not reach its crash window"
            assert parent.recv() == "paused"
            os.kill(process.pid, signal.SIGKILL)
            process.join(10)
            assert process.exitcode == -signal.SIGKILL
        finally:
            if process.is_alive():
                process.kill()
                process.join(10)
            parent.close()
            if not process.is_alive():
                process.close()  # lets go of the process sentinel (two descriptors per child)
        assert provider.events[sends:] == []  # a reconcile never sends
        assert all(r.method == "GET" for r in server.requests[count:])
        store_is_valid(data)
        mid, view = source_record(data, operation_id), journal(data, report.plan_id)
        if terminal:
            assert (mid.status, mid.reason) == ("succeeded", "metadata_verified")
            assert type(view.verification) is TransferVerificationV3
            assert len(view.verification.files) == 3
            with pytest.raises(OperationError) as finished:
                reconcile(data, server, operation_id)
            assert finished.value.code == "operation_conflict"
            return
        # The dead process holds a read lease: nobody else reads while it lives ...
        assert mid.status == "unknown"
        assert mid.lease is not None
        assert mid.lease.mode == "read"
        assert mid.fence == before.fence + 1
        assert view.verification is None
        assert len(view.intents) == len(view.receipts) == 3
        with pytest.raises(OperationError) as busy:
            reconcile(data, server, operation_id)
        assert busy.value.code == "operation_conflict"
        # ... and once it has lapsed the next reconcile proves the same operation.
        clock = Skewed()
        clock.skew += 200
        phase = reconcile(data, server, operation_id, clock=clock)
        assert (phase.record.operation_id, phase.record.status) == (operation_id, "succeeded")
        assert phase.record.fence > mid.fence
        assert phase.record.lease is None
        assert len(journal(data, report.plan_id).verification.files) == 3
        store_is_valid(data)
