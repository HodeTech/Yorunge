"""What the second review round's mutation run left alive in the engine and its path judgement.

Each test names the survivor it kills: the first report comes before the first byte, no report is
made after the record it describes is written (so none can carry the whole body before the durable
mark), a job subclass is no job, the closed error of an ended resolver has no chain, the default
grace of the resolver, the progress throttle and the deadline at their exact boundaries, an integer
deadline, every bidirectional control of a reported path, a ``..`` target and a target that is not
a path.
"""

import threading
import time

import pytest

from tests.integration.test_download_engine import (
    DATA,
    DownloadJob,
    assert_whole,
    code_of,
    source,
)
from tests.integration.test_download_engine import (
    world as world,
)
from tests.integration.test_storage_transport import (
    certificates as certificates,
)
from tests.integration.test_storage_transport import (
    loopback_only as loopback_only,
)
from yorunge.adapters import download_engine
from yorunge.adapters.download_engine import _Limit, _Progress, run_download
from yorunge.adapters.download_sink import DownloadSink
from yorunge.domain.errors import YorungeError


# R01: the first report is made before the first byte of the body (Q4 says "before the first byte").
def test_the_first_report_is_made_before_the_first_byte_of_the_body_arrives(world):
    gate = threading.Event()

    class Held(bytes):
        def __getitem__(self, key):
            gate.wait(8)  # headers are on the wire; the body waits for the first report
            return bytes.__getitem__(self, key)

    world.provider.data = Held(DATA)
    seen = []

    def progress(held, total):
        seen.append((held, total))
        gate.set()

    assert_whole(world, world.run(progress=progress))
    assert seen[0] == (0, len(DATA))


# R02 / R13: with no throttle every record is due; none is reported after it is written, and
# the whole is reported only once the durable mark is made.
def test_no_report_before_the_mark_carries_the_whole_body(world, monkeypatch):
    monkeypatch.setattr(download_engine, "PROGRESS_SECONDS", 0.0)
    events = []
    real = DownloadSink.complete

    def complete(sink, **options):
        events.append("complete")
        real(sink, **options)

    monkeypatch.setattr(DownloadSink, "complete", complete)
    assert_whole(world, world.run(progress=lambda held, total: events.append(held)))
    mark = events.index("complete")
    assert len(events[:mark]) > 3
    assert all(held < len(DATA) for held in events[:mark])
    assert events[mark + 1 :] == [len(DATA)]


# E04: a subclass of the job is no job (its __post_init__ could be anything).
def test_a_subclass_of_the_job_is_no_job(world):
    class Spoof(DownloadJob):
        pass

    job = world.job()
    spoof = Spoof(
        target=job.target, source=source(), identity_key=job.identity_key, resolve=job.resolve
    )
    assert code_of(lambda: run_download(spoof, world.owned)) == "invalid_request"
    assert world.server.requests == []
    assert world.names() == []


# N09: the closed error of an ended resolver carries no chain.
def test_a_resolver_ended_at_its_budget_leaves_no_chain(world, monkeypatch):
    import asyncio

    monkeypatch.setattr(download_engine, "JSON_BUDGET_SECONDS", 0.3)
    monkeypatch.setattr(download_engine, "RESOLVE_GRACE_SECONDS", 0.1)

    async def hangs(transport, deadline):
        await asyncio.sleep(30)

    with pytest.raises(YorungeError) as error:
        world.run(resolve=hangs)
    assert error.value.code == "transport_timeout"
    assert error.value.__cause__ is None
    assert error.value.__suppress_context__ is True


# C02 / C03: the default grace is what the reference says.
def test_the_default_grace_of_the_resolver_is_one_second():
    assert download_engine.RESOLVE_GRACE_SECONDS == 1.0
    assert download_engine.JSON_BUDGET_SECONDS == 30.0


# P05: a report exactly one interval after the previous one is due.
def test_a_report_exactly_one_interval_later_is_made():
    seen, now = [], [0.0]
    meter = _Progress(lambda held, total: seen.append(held), clock=lambda: now[0])
    meter.update(1, None)
    now[0] = download_engine.PROGRESS_SECONDS
    meter.update(2, None)
    assert seen == [1, 2]


# L02: the deadline is reached when the clock says so.
def test_the_deadline_is_reached_at_the_instant(monkeypatch):
    monkeypatch.setattr(download_engine.time, "monotonic", lambda: 100.0)
    with pytest.raises(YorungeError) as error:
        _Limit(100.0).guard()
    assert error.value.code == "transport_timeout"


# E21: an integer deadline is a deadline.
def test_an_integer_deadline_is_accepted(world):
    assert_whole(world, run_download(world.job(), world.owned, deadline=int(time.monotonic()) + 60))


# M03 / M13: every bidirectional embedding, override and isolate is refused; its neighbours are not.
@pytest.mark.parametrize(
    "control",
    ["\u202a", "\u202b", "\u202c", "\u202d", "\u202e", "\u2066", "\u2067", "\u2068", "\u2069"],
)
def test_every_bidirectional_control_is_refused_in_a_reportable_path(control):
    from yorunge.domain.models import is_reportable_path

    assert not is_reportable_path(f"/tmp/a{control}b.json")


@pytest.mark.parametrize("plain", ["\u2029", "\u202f"])
def test_the_neighbours_of_the_bidirectional_controls_are_plain_characters(plain):
    from yorunge.domain.models import is_reportable_path

    assert is_reportable_path(f"/tmp/a{plain}b.json")


# D06: a dot-dot component is a target error (the chain refusal is mapped), before any request.
def test_a_target_with_a_dot_dot_component_is_a_target_error_before_any_request(world):
    code = code_of(lambda: world.run(target=world.directory / ".." / world.target.name))
    assert code == "download_target_invalid"
    assert world.server.requests == []
    assert world.names() == []


# D01: a target that is not a Path is the family's invalid code, not an AttributeError.
@pytest.mark.parametrize("bad", ["/tmp/a/b", b"/tmp/a/b", None, 5])
def test_a_target_that_is_not_a_path_is_the_invalid_code(bad):
    from yorunge.adapters.target_directory import open_target_directory

    with pytest.raises(YorungeError) as error:
        open_target_directory(bad)
    assert error.value.code == "download_target_invalid"
