"""One download scenario for the kill matrix: the engine's side of a conforming exchange.

The kill test runs ``main`` in a child process whose steps are announced (and, at a chosen one,
answered with SIGKILL), and runs ``engine_run`` and ``prepare`` in its own process to set up and
to recover. The server is emulated as a conforming one: it answers the plan the sink calls for.
"""

import os
import signal
import sys
from pathlib import Path

from yorunge.adapters import download_files, download_sink
from yorunge.domain.download_response import ContentRange, DownloadResponse
from yorunge.domain.errors import YorungeError

IDENTITY = "ab" * 32
NAME = "weights.onnx"
TAG = '"v1-3f9c"'
DATA = bytes(range(256)) * 80  # 20,480 bytes
SMALL_CHECKPOINT = 4096


def full(*, chunked=False):
    if chunked:
        return DownloadResponse(200, None, TAG, "chunked", None)
    return DownloadResponse(200, None, TAG, "length", len(DATA))


def partial(start):
    return DownloadResponse(
        206, ContentRange(start, len(DATA) - 1, len(DATA)), TAG, "length", len(DATA) - start
    )


def pieces(data, size):
    for offset in range(0, len(data), size):
        yield data[offset : offset + size]


def engine_run(directory, *, scenario="fresh", no_resume=False, expected=None):
    """A conforming engine, following whatever the plan calls for. Returns the Published."""
    if scenario == "checkpoints":
        download_sink.CHECKPOINT_BYTES = SMALL_CHECKPOINT
    chunked = scenario == "chunked"
    size = SMALL_CHECKPOINT if scenario == "checkpoints" else len(DATA)
    with download_sink.open_sink(
        Path(directory) / NAME, identity_key=IDENTITY, no_resume=no_resume
    ) as (sink, plan):
        if plan.action == "publish":
            return sink.publish(expected)
        body = DATA
        if plan.ask is not None and scenario == "discard":
            sink.discard()  # the 206 does not fit (or a 416): drop and ask again without a range
            sink.begin(full(), "full")
        elif plan.ask is not None and scenario == "restart":
            sink.begin(full(), "restart")  # the provider ignored the range
        elif plan.ask is not None:
            sink.begin(partial(plan.ask.prefix_bytes), "continue")
            body = DATA[plan.ask.prefix_bytes :]
        else:
            sink.begin(full(chunked=chunked), "full")
        for piece in pieces(body, size):
            sink.write(piece)
        sink.complete()
        return sink.publish(expected)


def prepare(directory, kind):
    """A directory as an earlier run left it: stopped cleanly, or complete but unpublished."""
    download_sink.CHECKPOINT_BYTES = SMALL_CHECKPOINT
    with download_sink.open_sink(Path(directory) / NAME, identity_key=IDENTITY) as (sink, _):
        sink.begin(full(), "full")
        if kind == "stopped":
            for piece in pieces(DATA[:9000], SMALL_CHECKPOINT):
                sink.write(piece)
            sink.stop()
        elif kind == "unpublished":
            for piece in pieces(DATA, SMALL_CHECKPOINT):
                sink.write(piece)
            sink.complete()
        else:
            raise ValueError(kind)


def main():
    """The child: ``main`` is called with the scenario in the environment."""
    directory = os.environ["SINK_DIRECTORY"]
    scenario = os.environ.get("SINK_SCENARIO", "fresh")
    kill = os.environ.get("SINK_KILL")
    record = os.environ.get("SINK_RECORD")
    if os.environ.get("SINK_UMASK"):
        os.umask(int(os.environ["SINK_UMASK"], 8))
    counts = {}

    def marker(name):
        counts[name] = counts.get(name, 0) + 1
        label = f"{name}#{counts[name]}"
        if record:
            with open(record, "a") as handle:
                handle.write(label + "\n")
        if kill == label:
            os.kill(os.getpid(), signal.SIGKILL)

    download_files._marker = marker
    try:
        engine_run(
            directory,
            scenario=scenario,
            no_resume=bool(os.environ.get("SINK_NO_RESUME")),
            expected=os.environ.get("SINK_EXPECTED") or None,
        )
    except YorungeError as error:
        sys.stdout.write(error.code)
        return
    sys.stdout.write("published")
