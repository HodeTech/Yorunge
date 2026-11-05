"""Transport-derived counters and bounded TTY rendering; neither is remote delivery evidence."""

import io
import threading
from itertools import pairwise
from uuid import uuid4

from yorunge.application.upload_progress import count_upload, observe_upload, source_chunk
from yorunge.cli.upload import ProgressText, _cost_text
from yorunge.domain.errors import YorungeError


class Terminal(io.StringIO):
    def isatty(self):
        return True


def test_counter_uses_actual_chunk_deltas_and_separate_durable_confirmation():
    updates, identity = [], str(uuid4())
    with observe_upload(updates.append), count_upload((3, 5)) as counter:
        counter.bind(identity)
        source_chunk(3)
        source_chunk(5)
        assert updates[-1].source_bytes == 8
        assert updates[-1].confirmed_files == 0
        counter.confirm(0)
        assert updates[-1].confirmed_files == 1
        assert updates[-1].confirmed_bytes == 3
        counter.confirm(1)
        counter.confirm(1)
    assert len(updates) == 5
    assert updates[-1].confirmed_bytes == 8
    assert {p.operation_id for p in updates} == {identity}
    source_chunk(999)
    assert len(updates) == 5
    assert not any("key" in field or "path" in field for field in type(updates[0]).__slots__)


def test_no_sink_means_no_counter_or_byte_cache():
    with count_upload((3,)) as counter:
        assert counter is None
        source_chunk(1)


def test_counter_rejects_cross_thread_use_without_increment():
    updates, errors = [], []
    with observe_upload(updates.append), count_upload((3,)) as counter:
        counter.bind(str(uuid4()))

        def worker():
            try:
                counter.source(1)
            except YorungeError as error:
                errors.append(error.code)

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(timeout=5)
    assert not thread.is_alive()
    assert errors == ["invalid_request"]
    assert updates[-1].source_bytes == 0


def test_progress_is_tty_only_coalesced_and_safe_when_the_sink_fails(monkeypatch):
    from yorunge.application.upload_progress import UploadProgress
    from yorunge.cli import upload

    clock = [0.0]

    # Replace this module's time reference, not the process-wide monotonic clock.
    class Time:
        @staticmethod
        def monotonic():
            return clock[0]

    monkeypatch.setattr(upload, "time", Time)
    emitted = []

    class TimedTerminal(Terminal):
        def write(self, value):
            emitted.append(clock[0])
            return super().write(value)

    sink, identity = TimedTerminal(), str(uuid4())
    progress = ProgressText(sink)
    for i in range(100):
        clock[0] = i / 100
        progress(UploadProgress(identity, i, 100, 0, 0, 1))
    assert 8 <= len(sink.getvalue().splitlines()) <= 10
    assert all(right - left >= 0.1 for left, right in pairwise(emitted))
    assert "Taşımaya verilen" in sink.getvalue()
    assert "Onaylı" in sink.getvalue()
    assert not ProgressText(io.StringIO()).enabled

    class Closed(Terminal):
        def write(self, value):
            raise BrokenPipeError("private sink error")

    failed = ProgressText(Closed())
    clock[0] += 1
    failed(UploadProgress(identity, 1, 100, 0, 0, 1))
    assert not failed.enabled


def test_price_text_uses_exact_integer_microcredits():
    import json
    from pathlib import Path

    from tests.integration.test_upload_journal import seal
    from yorunge.adapters.upload_projection import summary
    from yorunge.adapters.upload_store import VersionedTransferView

    path = Path(__file__).parents[1] / "fixtures" / "dataset-upload-approved-v2.json"
    body = json.loads(path.read_bytes())["plan"]
    body["budget_micros"] = body["cost_bound"]["maximum_micros"] = 2**63 - 1
    plan = seal(body)
    value = summary(VersionedTransferView(plan, None, None))
    assert "9223372036854.775807 CR" in "\n".join(_cost_text(value))


def test_text_error_keeps_known_operation_identity_without_changing_the_wire():
    from yorunge.cli.output import OutputRenderer
    from yorunge.domain.errors import OperationError

    identity, sink = str(uuid4()), io.StringIO()
    error = OperationError("operation_uncertain", identity)
    renderer = OutputRenderer("text", stdout=io.StringIO(), stderr=sink)
    assert renderer.error(error) == 5
    assert identity in sink.getvalue()
    assert error.message in sink.getvalue()
