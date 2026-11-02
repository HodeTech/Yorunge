"""Isolated installed dataset worker; native RSS excludes the fixture controller."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import runpy
import sys
import time
from pathlib import Path
from typing import Any


def canonical_artifact(content: bytes, expected: dict[str, Any]) -> bool:
    encoded = (
        json.dumps(
            expected, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        + b"\n"
    )
    return content == encoded


def measure(args: argparse.Namespace) -> dict[str, Any]:
    if not sys.flags.isolated:
        raise ValueError("dataset worker requires isolated Python")
    native = runpy.run_path(str(Path(__file__).with_name("stream_budget.py")))
    wheel = runpy.run_path(str(Path(__file__).parents[2] / "scripts/dataset_wheel.py"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    from yorunge import api

    def provenance() -> dict[str, Any]:
        python_sources = {
            name: digest
            for name, digest in receipt["source_sha256"].items()
            if name.endswith(".py")
        }
        return native["installed_provenance"](
            python_sources, args.prefix, receipt["locked_runtime"]
        )

    def runtime_data(runtime: dict[str, Any]) -> dict[str, str]:
        marker = Path(runtime["modules"]["yorunge"]).parent / "py.typed"
        actual = {"src/yorunge/py.typed": hashlib.sha256(marker.read_bytes()).hexdigest()}
        if any(receipt["source_sha256"].get(name) != digest for name, digest in actual.items()):
            raise ValueError("installed type marker differs from measured source")
        return actual

    before = provenance()
    before_data = runtime_data(before)
    before_metadata = wheel["installed_metadata"](args.prefix, receipt["locked_runtime"]["yorunge"])
    method, current_rss = native["prepare_current_rss"]()
    # One fixed maximum hash block warms both APIs before B/H0 at every size.
    warm_root = args.work / "warm-source"
    warm_root.mkdir()
    (warm_root / "data.bin").write_bytes(b"w" * 1_048_576)
    warm_manifest = args.work / "warm-manifest.json"
    api.inspect_dataset(warm_root, manifest_out=warm_manifest)
    api.verify_dataset(warm_root, manifest=warm_manifest)
    baseline_details = {}
    if platform.system() == "Linux":
        baseline_native, pages, page_bytes = native["linux_rss_baseline"]()
        baseline_details = {"baseline_rss_pages": pages, "rss_page_bytes": page_bytes}
    else:
        baseline_native = current_rss()
    baseline = native["rss_bytes"](baseline_native, platform.system())
    started = time.perf_counter()
    h0_native, h0 = native["self_peak_rss"]()
    if args.action == "inspect":
        result = api.inspect_dataset(args.root, manifest_out=args.manifest)
    else:
        result = api.verify_dataset(args.root, manifest=args.manifest)
    h1_native, h1 = native["self_peak_rss"]()
    elapsed = time.perf_counter() - started
    lower, upper = native["rss_bounds"](baseline, h0, h1)
    # Validate the complete artifact outside the timed/native-RSS interval.
    with args.manifest.open("rb") as stream:
        artifact = stream.read(8 * 1024 * 1024 + 1)
    data = result.data.model_dump(mode="json")
    valid = (
        canonical_artifact(artifact, expected)
        and result.operation_id is None
        and result.status == "completed"
        and result.warnings == ("local_files_only",)
        and data["manifest_digest"] == expected["digest"]
        and data["file_count"] == expected["file_count"]
        and data["total_bytes"] == expected["total_bytes"]
        and (args.action == "inspect" or data["matches"] is True)
    )
    after = provenance()
    after_data = runtime_data(after)
    after_metadata = wheel["installed_metadata"](args.prefix, receipt["locked_runtime"]["yorunge"])

    def identity(value: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in value.items() if k not in {"pid", "modules"}}

    if (
        identity(before) != identity(after)
        or before_data != after_data
        or before_metadata != after_metadata
    ):
        raise ValueError("dataset runtime changed during measurement")
    return {
        "action": args.action,
        "manifest_digest": data["manifest_digest"],
        "file_count": data["file_count"],
        "total_bytes": data["total_bytes"],
        "result_valid": valid,
        "elapsed_seconds": elapsed,
        "baseline_rss_native": baseline_native,
        "baseline_rss_bytes": baseline,
        "baseline_rss_method": method,
        **baseline_details,
        "pretransfer_peak_rss_native": h0_native,
        "pretransfer_peak_rss_bytes": h0,
        "peak_rss_native": h1_native,
        "peak_rss_bytes": h1,
        "rss_native_unit": "KiB" if platform.system() == "Linux" else "bytes",
        "extra_rss_lower_bound_bytes": lower,
        "extra_rss_upper_bound_bytes": upper,
        "runtime": after,
        "runtime_data_sha256": after_data,
        "distribution_metadata_sha256": after_metadata,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("inspect", "verify"), required=True)
    for name in ("root", "manifest", "expected", "receipt", "prefix", "work"):
        parser.add_argument("--" + name, type=Path, required=True)
    print(json.dumps(measure(parser.parse_args()), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
