"""Isolated runtime-only installed public API worker for synthetic download RSS.

The worker runs from the installed wheel (``python -I``), warms the same real path on its own
server, takes the native baseline ``B`` and the lifetime peak ``H0``, calls the real
``api.download_model_weights`` through the product's guarded transport (the expected digest of the
independent oracle is passed as ``sha256=``), takes ``H1`` at once, and only then verifies and
hashes what was written. For the ``resume`` label the window covers two calls: the first must
fail with ``download_incomplete`` (the server cuts it), the second must resume.

Inside the window ``os.write`` on the stage, ``os.fsync`` and the sink's full-sync are wrapped by
timers (``"instrumented": true``): every wrapper adds a clock pair and an ``fstat`` to its call, so
the window measures the product with that overhead and the report says so.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import stat
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dataset_wheel import installed_metadata  # noqa: E402
from tests.fixtures.download_native_data import (  # noqa: E402
    FORMAT,
    KEY,
    KEY_ENV,
    LABELS,
    VERSION,
    WARM_OF,
    Fixture,
    canonical,
    expected_sha256,
    fixture,
    paths,
    write_config,
)
from tests.fixtures.model_network import loopback_models  # noqa: E402
from tests.fixtures.stream_budget import (  # noqa: E402
    installed_provenance,
    linux_rss_baseline,
    prepare_current_rss,
    rss_bounds,
    rss_bytes,
    self_peak_rss,
)
from yorunge import api  # noqa: E402
from yorunge.adapters import download_sink, local_files  # noqa: E402
from yorunge.domain.errors import YorungeError  # noqa: E402

READ_BLOCK = 1_048_576


def prepare(directory: Path) -> None:
    """The worker's own profile, state store and download directory; nothing is overwritten."""
    layout = paths(directory)
    directory.mkdir(parents=True, exist_ok=True)
    write_config(layout.config)
    layout.out.mkdir()
    api.initialize_state(state_dir=layout.state)


def call(directory: Path, digest: str) -> Any:
    """One public call, as a caller makes it; the independent digest is the expectation."""
    layout = paths(directory)
    return api.download_model_weights(
        VERSION,
        artifact_format=FORMAT,
        weights_out=layout.target,
        sha256=digest,
        config=layout.config,
        state_dir=layout.state,
    )


def flow(directory: Path, item: Fixture, digest: str) -> tuple[str | None, Any]:
    """The public calls of one measurement; a cut object needs two and the first one must fail."""
    first_error = None
    if item.cut_at is not None:
        try:
            call(directory, digest)
        except YorungeError as error:
            first_error = error.code
        else:
            raise ValueError("the cut download unexpectedly succeeded")
    return first_error, call(directory, digest)


def outcome(result: Any, first_error: str | None) -> dict[str, Any]:
    data = result.data
    return {
        "bytes": data.bytes,
        "sha256": data.sha256,
        "verification_level": data.verification_level,
        "expectation_source": data.expectation_source,
        "resumed": data.resumed,
        "resumed_from_bytes": data.resumed_from_bytes,
        "first_error": first_error,
    }


@contextmanager
def instruments(directory: Path) -> Iterator[dict[str, Any]]:
    """Count and time the stage writes, every ``os.fsync`` and the product's full-sync calls.

    ``directory`` is the one the stage lives in. A write or fsync on the stage is told from the
    others by the stage's device and inode (found by name once per descriptor identity); the fsync
    inside a full-sync belongs to the full-sync and is not counted twice. The full-sync is
    ``local_files.full_sync``, bound by name into the modules that call it (the sink before the
    link, the common publisher after it): every such binding is wrapped. Everything is restored on
    exit, and the totals are plain numbers: nothing grows with the number of calls.
    """
    real_full_sync = local_files.full_sync
    bound = [
        module
        for name, module in tuple(sys.modules.items())
        if name.startswith("yorunge.") and getattr(module, "full_sync", None) is real_full_sync
    ]
    if download_sink not in bound:
        raise ValueError("the download sink does not use local_files.full_sync")
    totals: dict[str, Any] = {
        "instrumented": True,
        "write_calls": 0,
        "write_bytes": 0,
        "write_seconds": 0.0,
        "max_write_bytes": 0,
        "max_write_seconds": 0.0,
        "stage_fsync_calls": 0,
        "stage_fsync_seconds": 0.0,
        "max_stage_fsync_seconds": 0.0,
        "other_fsync_calls": 0,
        "other_fsync_seconds": 0.0,
        "full_sync_calls": 0,
        "full_sync_seconds": 0.0,
    }
    identities: dict[tuple[int, int], bool] = {}
    inside = False  # a full-sync is running: its fsync is part of it
    clock = time.perf_counter
    real_write, real_fsync = os.write, os.fsync

    def is_stage(descriptor: int) -> bool:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            return False
        key = (info.st_dev, info.st_ino)
        known = identities.get(key)
        if known is None:
            with os.scandir(directory) as entries:
                known = any(
                    entry.name.endswith(".part")
                    and (entry.stat(follow_symlinks=False).st_dev, entry.inode()) == key
                    for entry in entries
                )
            identities[key] = known
        return known

    def write(descriptor: int, data: Any) -> int:
        started = clock()
        count = real_write(descriptor, data)
        elapsed = clock() - started
        if is_stage(descriptor):
            totals["write_calls"] += 1
            totals["write_bytes"] += count
            totals["write_seconds"] += elapsed
            totals["max_write_bytes"] = max(totals["max_write_bytes"], count)
            totals["max_write_seconds"] = max(totals["max_write_seconds"], elapsed)
        return count

    def fsync(descriptor: int) -> None:
        started = clock()
        real_fsync(descriptor)
        elapsed = clock() - started
        if inside:
            return
        kind = "stage" if is_stage(descriptor) else "other"
        totals[kind + "_fsync_calls"] += 1
        totals[kind + "_fsync_seconds"] += elapsed
        if kind == "stage":
            totals["max_stage_fsync_seconds"] = max(totals["max_stage_fsync_seconds"], elapsed)

    def full_sync(descriptor: int) -> None:
        nonlocal inside
        started = clock()
        inside = True
        try:
            real_full_sync(descriptor)
        finally:
            inside = False
        totals["full_sync_calls"] += 1
        totals["full_sync_seconds"] += clock() - started

    os.write, os.fsync = write, fsync
    for module in bound:
        module.full_sync = full_sync
    try:
        yield totals
    finally:
        os.write, os.fsync = real_write, real_fsync
        for module in bound:
            module.full_sync = real_full_sync


def verify_output(directory: Path, item: Fixture, digest: str) -> dict[str, Any]:
    """Outside the window: what is on disk, hashed independently of the product's own digest."""
    layout = paths(directory)
    with os.scandir(layout.out) as entries:
        names = sorted(entry.name for entry in entries)
    hasher, size = hashlib.sha256(), 0
    with layout.target.open("rb", buffering=0) as source:
        while block := source.read(READ_BLOCK):
            hasher.update(block)
            size += len(block)
    removed = False
    if size == item.size and hasher.hexdigest() == digest:
        # Verified bytes are fully determined by the oracle: keep only a payload that is wrong.
        layout.target.unlink()
        removed = True
    return {
        "file_bytes": size,
        "file_sha256": hasher.hexdigest(),
        "entries": names,
        "payload_removed": removed,
    }


def provenance(expected: dict[str, Any], prefix: Path) -> dict[str, Any]:
    python_sources = {
        name: digest for name, digest in expected["source_sha256"].items() if name.endswith(".py")
    }
    value = installed_provenance(python_sources, prefix, expected["locked_runtime"])
    marker = Path(value["modules"]["yorunge"]).parent / "py.typed"
    value["type_marker_sha256"] = hashlib.sha256(marker.read_bytes()).hexdigest()
    if value["type_marker_sha256"] != expected["source_sha256"]["src/yorunge/py.typed"]:
        raise ValueError("installed download type marker differs from source")
    value["metadata_sha256"] = installed_metadata(prefix, expected["locked_runtime"]["yorunge"])
    if value["metadata_sha256"] != expected["metadata_sha256"]:
        raise ValueError("installed download metadata differs from wheel")
    return value


def identity(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key not in {"pid", "modules"}}


def measured(args: argparse.Namespace, expected: dict[str, Any]) -> dict[str, Any]:
    item, warm_item = fixture(args.label), fixture(WARM_OF[args.label])
    method, current_rss = prepare_current_rss()
    # Bounded and outside the window: the oracle hashes 64 KiB blocks, never an object.
    digest, warm_digest = expected_sha256(item.size), expected_sha256(warm_item.size)
    for directory in (args.warm, args.work):
        prepare(directory)
    with loopback_models(args.ca, args.warm_port):
        warm_error, warm = flow(args.warm, warm_item, warm_digest)
    before = provenance(expected, args.prefix)
    with loopback_models(args.ca, args.port), instruments(paths(args.work).out) as window:
        details: dict[str, int] = {}
        if platform.system() == "Linux":
            baseline_native, pages, page_bytes = linux_rss_baseline()
            details = {"baseline_rss_pages": pages, "rss_page_bytes": page_bytes}
        else:
            baseline_native = current_rss()
        baseline = rss_bytes(baseline_native, platform.system())
        h0_native, h0 = self_peak_rss()
        started = time.perf_counter()
        first_error, result = flow(args.work, item, digest)
        elapsed = time.perf_counter() - started
        h1_native, h1 = self_peak_rss()
    lower, upper = rss_bounds(baseline, h0, h1)
    after = provenance(expected, args.prefix)
    if identity(before) != identity(after):
        raise ValueError("installed download runtime changed during measurement")
    return {
        "runtime": after,
        "pid": os.getpid(),
        "baseline_rss_native": baseline_native,
        "baseline_rss_method": method,
        "baseline_rss_bytes": baseline,
        **details,
        "pretransfer_peak_rss_native": h0_native,
        "pretransfer_peak_rss_bytes": h0,
        "peak_rss_native": h1_native,
        "peak_rss_bytes": h1,
        "rss_native_unit": "bytes" if platform.system() == "Darwin" else "KiB",
        "extra_rss_lower_bound_bytes": lower,
        "extra_rss_upper_bound_bytes": upper,
        "elapsed_seconds": elapsed,
        "window": window,
        "public": outcome(result, first_error),
        "written": verify_output(args.work, item, digest),
        "warm": outcome(warm, warm_error),
    }


def main() -> int:
    if not sys.flags.isolated:
        raise ValueError("download native worker requires isolated Python")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ca", required=True, type=Path)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--warm-port", required=True, type=int)
    parser.add_argument("--prefix", required=True, type=Path)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--warm", required=True, type=Path)
    parser.add_argument("--label", required=True, choices=LABELS)
    args = parser.parse_args()
    if args.port == args.warm_port or args.work.resolve() == args.warm.resolve():
        raise ValueError("warm and measured download fixtures must be separate")
    expected = json.loads(args.provenance.read_bytes())
    # Fail before network if this is an editable, foreign or development install.
    provenance(expected, args.prefix)
    os.environ[KEY_ENV] = KEY
    sys.stdout.write(canonical(measured(args, expected)).decode("utf-8") + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
