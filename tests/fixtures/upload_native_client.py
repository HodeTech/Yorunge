"""Isolated runtime-only installed public API worker for synthetic upload RSS."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dataset_wheel import installed_metadata  # noqa: E402
from tests.fixtures.stream_budget import (  # noqa: E402
    installed_provenance,
    linux_rss_baseline,
    prepare_current_rss,
    rss_bounds,
    rss_bytes,
    self_peak_rss,
)
from tests.fixtures.upload_native_data import KEY, KEY_ENV, NAME, OWNER, PROJECT  # noqa: E402
from tests.fixtures.upload_network import Metrics, loopback_upload  # noqa: E402
from yorunge import api  # noqa: E402
from yorunge.adapters.state import open_existing_store  # noqa: E402
from yorunge.adapters.upload_repository import StateUploads  # noqa: E402
from yorunge.domain.dataset_upload import UploadOwner, UploadParameters  # noqa: E402


def flow(directory):
    """Exercise the same three public calls a caller uses; inject no proof or grant."""
    options = {"config": directory / "config.toml", "state_dir": directory / "state"}
    prepared = api.prepare_dataset_upload(
        directory / "source",
        manifest=directory / "manifest.json",
        owner=UploadOwner(kind="user", id=OWNER),
        parameters=UploadParameters(
            name=NAME,
            modality="VISION",
            visibility="private",
            contributions_enabled=False,
            license=None,
            tags=(),
        ),
        project=PROJECT,
        unpriced=True,
        admission_policy="explicit_attempt",
        **options,
    ).data
    api.approve_dataset_upload(
        prepared.plan_id,
        prepared.plan_digest,
        accept_unverified_authority=True,
        accept_unpriced_cost=True,
        **options,
    )
    return api.start_dataset_upload(prepared.plan_id, **options)


def provenance(expected, prefix):
    python_sources = {
        name: digest for name, digest in expected["source_sha256"].items() if name.endswith(".py")
    }
    value = installed_provenance(python_sources, prefix, expected["locked_runtime"])
    marker = Path(value["modules"]["yorunge"]).parent / "py.typed"
    value["type_marker_sha256"] = hashlib.sha256(marker.read_bytes()).hexdigest()
    if value["type_marker_sha256"] != expected["source_sha256"]["src/yorunge/py.typed"]:
        raise ValueError("installed upload type marker differs from source")
    value["metadata_sha256"] = installed_metadata(prefix, expected["locked_runtime"]["yorunge"])
    if value["metadata_sha256"] != expected["metadata_sha256"]:
        raise ValueError("installed upload metadata differs from wheel")
    return value


def identity(value):
    return {key: item for key, item in value.items() if key not in {"pid", "modules"}}


def graph(directory, operation_id):
    # Outside the native window. Export only synthetic byte/path/item evidence.
    with open_existing_store(directory / "state") as store:
        view = StateUploads(store).show(operation_id=operation_id)
        if view.verification is None:
            raise ValueError("upload produced no durable verification")
        return {
            "intent_count": len(view.intents),
            "receipt_count": len(view.receipts),
            "accepted_receipts": sum(receipt.result == "accepted" for receipt in view.receipts),
            "intents": [
                {"kind": intent.kind, "file_index": intent.file_index} for intent in view.intents
            ],
            "files": [file.model_dump(mode="json") for file in view.verification.files],
        }


def measured(args, expected):
    method, current_rss = prepare_current_rss()
    for directory in (args.warm, args.work):
        api.initialize_state(state_dir=directory / "state")
    warm_metrics = Metrics()
    with loopback_upload(args.ca, args.warm_port, warm_metrics):
        warm = flow(args.warm)
    if warm.data.operation_status != "succeeded":
        raise ValueError("full upload warmup did not succeed")
    before = provenance(expected, args.prefix)
    metrics = Metrics()
    with loopback_upload(args.ca, args.port, metrics):
        details = {}
        if platform.system() == "Linux":
            baseline_native, pages, page_bytes = linux_rss_baseline()
            details = {"baseline_rss_pages": pages, "rss_page_bytes": page_bytes}
        else:
            baseline_native = current_rss()
        baseline = rss_bytes(baseline_native, platform.system())
        h0_native, h0 = self_peak_rss()
        started = time.perf_counter()
        result = flow(args.work)
        elapsed = time.perf_counter() - started
        h1_native, h1 = self_peak_rss()
    lower, upper = rss_bounds(baseline, h0, h1)
    after = provenance(expected, args.prefix)
    if identity(before) != identity(after):
        raise ValueError("installed upload runtime changed during measurement")
    summary = result.data
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
        "warm_metrics": warm_metrics.summary(),
        "metrics": metrics.summary(),
        "graph": graph(args.work, summary.operation_id),
        "public": {
            "operation_status": summary.operation_status,
            "verification_level": summary.verification_level,
            "authority_verified": summary.authority_verified,
            "remote_bytes_verified": summary.remote_bytes_verified,
            "result_operation_id": result.operation_id,
        },
    }


def main():
    if not sys.flags.isolated:
        raise ValueError("upload native worker requires isolated Python")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ca", required=True, type=Path)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--warm-port", required=True, type=int)
    parser.add_argument("--prefix", required=True, type=Path)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--warm", required=True, type=Path)
    args = parser.parse_args()
    if args.port == args.warm_port or args.work.resolve() == args.warm.resolve():
        raise ValueError("warm and measured upload fixtures must be separate")
    expected = json.loads(args.provenance.read_bytes())
    # Fail before network if this is an editable, foreign or development install.
    provenance(expected, args.prefix)
    os.environ[KEY_ENV] = KEY
    print(json.dumps(measured(args, expected), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
