"""A download killed in another process, and the next call: the engine over a real SIGKILL.

The child runs the engine against the parent's loopback TLS server, which sends the object slowly;
the parent waits for what it needs to see on disk, kills the child with SIGKILL (no cleanup of any
kind runs) and runs the engine again, in this process. After the first checkpoint the next call
continues from it with one ranged request; before it, there is nothing to continue and the next
call starts over with a plain one. Either way the file is the object, byte for byte, and nothing
else is left in the directory.
"""

import multiprocessing
import random
import signal
import ssl
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.fixtures.http_server import Reply
from tests.integration.test_download_engine import (
    NAME,
    ORIGIN,
    World,
    assert_whole,
    identity,
    source,
)
from tests.integration.test_download_engine import Provider as Provider
from tests.integration.test_download_transport import TAG
from tests.integration.test_storage_transport import (
    certificates as certificates,
)
from tests.integration.test_storage_transport import (
    credential,
    session,
)
from tests.integration.test_storage_transport import (
    loopback_only as loopback_only,
)
from yorunge.adapters.download_engine import DownloadJob, run_download
from yorunge.domain.download import CHECKPOINT_BYTES, DownloadPartial, download_names

BIG = random.Random(5).randbytes(12 * 1024 * 1024 + 77)  # one checkpoint, and a ragged end
NAMES = download_names(NAME)


def engine_child(directory, port, certificate):
    """What the killed process does: one download of the whole object, slowly delivered."""
    from tests.integration.test_download_engine import Resolver

    endpoint = SimpleNamespace(
        port=port, client_context=lambda: ssl.create_default_context(cafile=certificate)
    )
    key = credential()
    owned, _, _ = session(key, None, {"api.localhost": endpoint}, origins=(ORIGIN,))
    job = DownloadJob(
        target=Path(directory) / NAME,
        source=source(),
        identity_key=identity(),
        resolve=Resolver(key),
    )
    with owned:
        run_download(job, owned, deadline=time.monotonic() + 300)


def committed(directory):
    """The bytes the sidecar commits to, or None while there is no readable record."""
    try:
        return DownloadPartial.decode((directory / NAMES.sidecar).read_bytes()).committed_bytes
    except (OSError, ValueError):
        return None


def stage_size(directory):
    try:
        return (directory / NAMES.stage).stat().st_size
    except OSError:
        return 0


def killed_when(world, ready):
    """Start the child, wait until ``ready()`` holds on disk, SIGKILL it, and wait for its end."""
    world.provider.script = [
        Reply(
            body=BIG,
            headers=world.provider.headers(),
            chunk_size=65_536,
            chunk_delay=0.01,
        )
    ]
    context = multiprocessing.get_context("spawn")
    child = context.Process(
        target=engine_child,
        args=(str(world.directory), world.server.port, str(world.certificates[0])),
    )
    child.start()
    try:
        deadline = time.monotonic() + 90
        while not ready():
            assert child.is_alive(), "the child ended before the moment it was to be killed at"
            assert time.monotonic() < deadline, "the moment never came"
            time.sleep(0.02)
        child.kill()
    finally:
        child.join(30)
        if child.is_alive():
            child.kill()
            child.join(30)
    assert child.exitcode == -signal.SIGKILL


@pytest.fixture
def world(certificates, tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    provider = Provider(BIG, TAG)
    with World(certificates, tmp_path, provider) as held:
        yield held


def test_a_download_killed_after_a_checkpoint_is_continued_from_it_by_the_next_process(world):
    killed_when(world, lambda: (committed(world.directory) or 0) >= CHECKPOINT_BYTES)
    kept = committed(world.directory)
    assert kept is not None and kept >= CHECKPOINT_BYTES
    # SIGKILL ran no cleanup: the stage, its record and the lock object are all still there
    assert world.names() == sorted([NAMES.lock, NAMES.stage, NAMES.sidecar])
    assert stage_size(world.directory) >= kept  # beyond the checkpoint is cut back, never trusted
    summary = world.run()
    assert_whole(world, summary, BIG, resumed=True, resumed_from=kept)
    assert world.provider.seen[-1] == (f"bytes={kept}-", TAG)  # one ranged request
    assert len(world.signed()) == 2  # the killed process's GET and this one, no more


def test_a_download_killed_before_its_first_checkpoint_has_nothing_to_continue(world):
    # The header checkpoint is written (0 bytes) and the body has begun: nothing is committed.
    killed_when(world, lambda: committed(world.directory) == 0 and stage_size(world.directory) > 0)
    assert (committed(world.directory) or 0) < CHECKPOINT_BYTES
    summary = world.run()
    assert_whole(world, summary, BIG)  # started over: a plain request, not resumed
    assert world.provider.seen[-1] == (None, None)
