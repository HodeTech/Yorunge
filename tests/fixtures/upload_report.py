"""Synthetic closed report vectors; these are not observed performance evidence."""

import copy
import hashlib
import json
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
VECTORS = json.loads((ROOT / "tests/fixtures/upload-native-vectors-v1.json").read_bytes())[
    "fixtures"
]
DATASET = "00000000-0000-4000-8000-000000000909"
LABELS = ("16", "256", "1024", "capacity")


def counters(count, size, phase):
    return {
        "read_requests": 18 if phase == 2 else 2,
        "read_attempts": 18 if phase == 2 else 2,
        "create_requests": int(phase == 2),
        "project_link_requests": int(phase == 2),
        "presign_requests": count if phase == 2 else 0,
        "put_requests": count if phase == 2 else 0,
        "confirm_requests": count if phase == 2 else 0,
        "effect_attempts": 2 + 3 * count if phase == 2 else 0,
        "control_request_reserved": 1000 if phase == 2 else 0,
        "upload_reserved": size if phase == 2 else 0,
        "response_pending": 0,
        "control_request_bytes": 1000 if phase == 2 else 0,
        "upload_bytes": size if phase == 2 else 0,
        "response_bytes": 1000,
    }


def metrics(expected):
    count, size = expected["file_count"], expected["total_bytes"]
    return {
        "sessions": [counters(count, size, phase) for phase in range(3)],
        "connections": 4,
        "open_connections": 0,
        "peak_connections": 2,
        "active_requests": 0,
        "peak_requests": 2,
        "active_puts": 0,
        "peak_puts": 2,
        "source_bytes": size,
        "source_chunks": sum((file["size"] + 1_048_575) // 1_048_576 for file in expected["files"]),
        "max_source_chunk_bytes": min(1_048_576, max(file["size"] for file in expected["files"])),
        "confirmed_files": count,
        "confirmed_bytes": size,
        "peak_sources": 2,
        "open_sources": 0,
        "request_seconds": [0.001] * (22 + 2 + 3 * count),
        "put_seconds": [0.001] * count,
    }


def server(expected, pid):
    count = expected["file_count"]
    requests = {"GET": 22, "POST": 2 + 2 * count, "PUT": count}
    return {
        "received": copy.deepcopy(expected["files"]),
        "items": [
            {
                "id": str(UUID(int=index + 10)),
                "dataset_id": DATASET,
                "original_filename": file["path"],
                "file_size_bytes": file["size"],
                "sha256_hash": file["sha256"],
            }
            for index, file in enumerate(expected["files"])
        ],
        "max_read_bytes": min(65_536, max(file["size"] for file in expected["files"])),
        "create_calls": 1,
        "link_calls": 1,
        "presign_calls": count,
        "put_calls": count,
        "confirm_calls": count,
        "pid": pid,
        "requests": requests,
        "statuses": {"200": sum(requests.values()) - 1, "201": 1},
        "connection_count": 4,
        "active_requests": 0,
        "peak_active_requests": 2,
        "control_bytes": 1000,
        "errors": 0,
    }


def graph(expected, sink):
    rows = [
        {"kind": "create", "file_index": None},
        {"kind": "project_link", "file_index": None},
    ] + [
        {"kind": kind, "file_index": index}
        for kind in ("presign", "put", "confirm")
        for index in range(expected["file_count"])
    ]
    return {
        "intent_count": len(rows),
        "receipt_count": len(rows),
        "accepted_receipts": len(rows),
        "intents": rows,
        "receipts": [{**row, "result": "accepted"} for row in rows],
        "files": [
            {
                "file_index": index,
                "item_id": item["id"],
                "path_digest": hashlib.sha256(file["path"].encode()).hexdigest(),
                "size_bytes": file["size"],
                "sha256": file["sha256"],
            }
            for index, (file, item) in enumerate(zip(expected["files"], sink["items"], strict=True))
        ],
    }


def proof():
    source = {
        "commit": "a" * 40,
        "source_sha256": {
            "src/yorunge/__init__.py": "1" * 64,
            "src/yorunge/py.typed": "2" * 64,
            "tests/fixtures/upload-native-vectors-v1.json": "3" * 64,
        },
    }
    return {
        "source_before": source,
        "source_after": copy.deepcopy(source),
        "locked_runtime": {"yorunge": "0.1.0.dev0", "httpx": "0.28.1"},
        "wheel_before": "4" * 64,
        "wheel_after": "4" * 64,
        "wheel_product_sha256": {
            key: value for key, value in source["source_sha256"].items() if key.startswith("src/")
        },
        "wheel_metadata_sha256": {
            name: "5" * 64 for name in ("METADATA", "WHEEL", "entry_points.txt")
        },
    }


def runtime(pid):
    return {
        "prefix": "/synthetic/env",
        "pid": pid,
        "modules": {"yorunge": "/synthetic/env/lib/yorunge/__init__.py"},
        "installed_source_sha256": {"__init__.py": "1" * 64},
        "installed_source_matches": True,
        "metadata": "/synthetic/env/lib",
        "packages": {"yorunge": "0.1.0.dev0", "httpx": "0.28.1"},
        "python": "3.11.18 synthetic fixture",
        "python_executable": "/synthetic/env/bin/python",
        "isolated": True,
        "sqlite": "3.45.0",
        "os": "Linux-synthetic",
        "machine": "x86_64",
        "type_marker_sha256": "2" * 64,
        "metadata_sha256": {name: "5" * 64 for name in ("METADATA", "WHEEL", "entry_points.txt")},
    }


def row(label, sample, ordinal):
    expected = VECTORS[label]
    sink, warm = server(expected, 300 + 2 * ordinal), server(VECTORS["warm"], 301 + 2 * ordinal)
    baseline, peak = 41_943_040, 46_137_344
    client = {
        "runtime": runtime(100 + ordinal),
        "pid": 100 + ordinal,
        "baseline_rss_native": baseline // 1024,
        "baseline_rss_method": "linux.proc_self_stat.rss_pages",
        "baseline_rss_bytes": baseline,
        "baseline_rss_pages": 10_240,
        "rss_page_bytes": 4096,
        "pretransfer_peak_rss_native": peak // 1024,
        "pretransfer_peak_rss_bytes": peak,
        "peak_rss_native": peak // 1024,
        "peak_rss_bytes": peak,
        "rss_native_unit": "KiB",
        "extra_rss_lower_bound_bytes": 0,
        "extra_rss_upper_bound_bytes": peak - baseline,
        "elapsed_seconds": 1.0,
        "warm_metrics": metrics(VECTORS["warm"]),
        "metrics": metrics(expected),
        "graph": graph(expected, sink),
        "public": {
            "operation_status": "succeeded",
            "verification_level": "metadata",
            "authority_verified": False,
            "remote_bytes_verified": False,
            "result_operation_id": None,
        },
    }
    return {
        "label": label,
        "sample": sample,
        "client": client,
        "server": sink,
        "warm_server": warm,
        "passed": True,
        "client_process_pid": client["pid"],
        "server_process_pid": sink["pid"],
        "warm_server_process_pid": warm["pid"],
    }


def report(method, limits):
    return {
        "schema_version": 1,
        "report_kind": "upload_budget_v1",
        "source_commit": "a" * 40,
        "environment": {"cpu": "synthetic", "disk_type": "synthetic"},
        "provenance": proof(),
        "method": method,
        "limits": copy.deepcopy(limits),
        "controller_pid": 999,
        "runs": [
            row(label, sample, ordinal)
            for ordinal, (label, sample) in enumerate(
                (label, sample) for label in LABELS for sample in (1, 2, 3)
            )
        ],
        "growth": {"span_upper_bound_bytes": 4_194_304, "passed": True},
        "passed": True,
    }
