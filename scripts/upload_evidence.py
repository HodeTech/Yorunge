"""Independent closed upload-budget verifier; never trusts producer byte oracles."""

from __future__ import annotations

import hashlib
import json
import math
import re
import runpy
from collections import Counter
from functools import cache
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
CHECKS = runpy.run_path(str(ROOT / "scripts/research_evidence.py"))
STREAM = runpy.run_path(str(ROOT / "scripts/benchmark-stream.py"))
LABELS = ("16", "256", "1024", "capacity")
VECTOR_PATH = "tests/fixtures/upload-native-vectors-v1.json"
LIMITS = {
    "rss_upper_bytes": 67_108_864,
    "growth_upper_bytes": 8_388_608,
    "window_seconds": 900,
    "put_seconds": 120,
    "source_chunk_bytes": 1_048_576,
    "source_workers": 2,
    "connections": 2,
    "configured_buffer_bytes": 2_097_152,
    "server_read_bytes": 65_536,
}
METHOD = "separate TLS sink; full public prepare/approve/start; fixed 1 MiB/N3 warm; native B/H0/H1"
DATASET = "00000000-0000-4000-8000-000000000909"
CLIENT_FIELDS = (
    "runtime pid baseline_rss_native baseline_rss_method baseline_rss_bytes "
    "pretransfer_peak_rss_native pretransfer_peak_rss_bytes peak_rss_native peak_rss_bytes "
    "rss_native_unit extra_rss_lower_bound_bytes extra_rss_upper_bound_bytes elapsed_seconds "
    "warm_metrics metrics graph public"
)
METRIC_FIELDS = (
    "sessions connections open_connections peak_connections active_requests peak_requests "
    "active_puts peak_puts source_bytes source_chunks max_source_chunk_bytes confirmed_files "
    "confirmed_bytes peak_sources request_seconds put_seconds open_sources"
)
COUNTER_FIELDS = (
    "read_requests read_attempts create_requests project_link_requests presign_requests "
    "put_requests confirm_requests effect_attempts control_request_reserved upload_reserved "
    "response_pending control_request_bytes upload_bytes response_bytes"
)
SERVER_FIELDS = (
    "received items max_read_bytes create_calls link_calls presign_calls put_calls confirm_calls "
    "pid requests statuses connection_count active_requests peak_active_requests "
    "control_bytes errors"
)


def closed(value: object, fields: str) -> dict[str, Any]:
    return cast(dict[str, Any], CHECKS["closed"](value, fields, "upload measurement"))


def integer(value: object, minimum: int = 0) -> int:
    return cast(int, CHECKS["integer"](value, minimum=minimum))


def number(value: object) -> float:
    return cast(float, CHECKS["number"](value))


def equal(actual: object, expected: object, message: str) -> None:
    # Canonical JSON comparison also distinguishes bool/int and rejects NaN.
    if canonical(actual) != canonical(expected):
        raise ValueError(message)


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


@cache
def file_hash(index: int, size: int) -> str:
    # Arithmetic 64 KiB oracle; independent of controller's rotated 32 KiB writer.
    block = bytes((offset + 17 * index) % 256 for offset in range(65_536))
    digest = hashlib.sha256()
    while size:
        used = min(size, len(block))
        digest.update(memoryview(block)[:used])
        size -= used
    return digest.hexdigest()


def expected_manifest(label: str) -> dict[str, Any]:
    if label not in ("warm", *LABELS):
        raise ValueError("unknown upload fixture label")
    total = 128 if label == "capacity" else (1 if label == "warm" else int(label)) * 1_048_576
    count = 128 if label == "capacity" else 3
    base, remainder = divmod(total, count)
    files = [
        {
            "path": f"file-{index:03}.bin",
            "size": base + int(index < remainder),
            "sha256": file_hash(index, base + int(index < remainder)),
        }
        for index in range(count)
    ]
    body = {
        "schema_version": 1,
        "policy_version": 1,
        "kind": "dataset_manifest",
        "hash_algorithm": "sha256",
        "files": files,
        "file_count": count,
        "total_bytes": total,
    }
    return {**body, "digest": hashlib.sha256(canonical(body)).hexdigest()}


def validate_vectors(path: Path) -> None:
    value = CHECKS["decode"](CHECKS["read_bounded"](path, 262_144))
    equal(
        value,
        {
            "schema_version": 1,
            "kind": "upload_native_vectors",
            "fixtures": {label: expected_manifest(label) for label in ("warm", *LABELS)},
        },
        "upload fixture bytes differ from independent arithmetic oracle",
    )


def source(root: Path) -> dict[str, Any]:
    sources = runpy.run_path(str(ROOT / "scripts/startup_evidence.py"))
    value = cast(dict[str, Any], sources["source"](root))
    vector = root / VECTOR_PATH
    validate_vectors(vector)
    value["source_sha256"][VECTOR_PATH] = hashlib.sha256(vector.read_bytes()).hexdigest()
    return value


def provenance(value: object, commit: object) -> dict[str, Any]:
    item = closed(
        value,
        "source_before source_after locked_runtime wheel_before wheel_after "
        "wheel_product_sha256 wheel_metadata_sha256",
    )
    before = CHECKS["source_snapshot"](item["source_before"])
    CHECKS["source_snapshot"](item["source_after"])
    if commit != before["commit"] or VECTOR_PATH not in before["source_sha256"]:
        raise ValueError("upload source identity or oracle snapshot missing")
    CHECKS["package_versions"](item["locked_runtime"])
    for key in ("wheel_before", "wheel_after"):
        CHECKS["pattern_value"](item[key], CHECKS["SHA256"])
    product = {k: v for k, v in before["source_sha256"].items() if k.startswith("src/yorunge/")}
    equal(CHECKS["hash_map"](item["wheel_product_sha256"]), product, "upload wheel/source mismatch")
    metadata = closed(item["wheel_metadata_sha256"], "METADATA WHEEL entry_points.txt")
    CHECKS["hash_map"](metadata)
    if "src/yorunge/py.typed" not in product:
        raise ValueError("upload source type marker missing")
    return item


def runtime(value: object, proof: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("upload runtime must be an object")
    base = {
        key: item
        for key, item in value.items()
        if key not in {"type_marker_sha256", "metadata_sha256"}
    }
    sources = proof["source_before"]
    CHECKS["stream_runtime"](base, CHECKS["python_hashes"](sources))
    equal(
        value.get("type_marker_sha256"),
        sources["source_sha256"]["src/yorunge/py.typed"],
        "upload marker mismatch",
    )
    equal(value.get("metadata_sha256"), proof["wheel_metadata_sha256"], "upload metadata mismatch")
    equal(value["packages"], proof["locked_runtime"], "upload frozen runtime mismatch")
    CHECKS["flag"](value["isolated"], True)
    CHECKS["flag"](value["installed_source_matches"], True)
    return value


def counters(value: object, count: int, total: int, phase: int) -> dict[str, Any]:
    item = closed(value, COUNTER_FIELDS)
    for part in item.values():
        integer(part)
    logical, attempts = item["read_requests"], item["read_attempts"]
    if not logical <= attempts <= 2 * logical or logical > 512 or attempts > 1024:
        raise ValueError("invalid upload read/attempt counters")
    effects = (1, 1, count, count, count) if phase == 2 else (0, 0, 0, 0, 0)
    names = (
        "create_requests",
        "project_link_requests",
        "presign_requests",
        "put_requests",
        "confirm_requests",
    )
    equal([item[key] for key in names], list(effects), "upload effect graph counter mismatch")
    valid_reads = logical == 2 if phase < 2 else logical >= 18
    if item["effect_attempts"] != sum(effects) or not valid_reads:
        raise ValueError("upload effect attempt/preparation counter mismatch")
    expected_bytes = total if phase == 2 else 0
    if item["upload_reserved"] != expected_bytes or item["upload_bytes"] != expected_bytes:
        raise ValueError("upload reserved/sent byte mismatch")
    if (
        item["control_request_bytes"] != item["control_request_reserved"]
        or item["response_pending"]
    ):
        raise ValueError("unfinished upload control reservations")
    if item["control_request_bytes"] > 4_194_304 or item["response_bytes"] > 16_777_216:
        raise ValueError("upload control byte budget exceeded")
    return item


def metrics(value: object, expected: dict[str, Any]) -> dict[str, Any]:
    item = closed(value, METRIC_FIELDS)
    for key in set(item) - {"sessions", "request_seconds", "put_seconds"}:
        integer(item[key])
    sessions = item["sessions"]
    if not isinstance(sessions, list) or len(sessions) != 3:
        raise ValueError("upload requires three distinct API session counters")
    count, total = expected["file_count"], expected["total_bytes"]
    rows = [counters(row, count, total, phase) for phase, row in enumerate(sessions)]
    attempts = sum(row["read_attempts"] + row["effect_attempts"] for row in rows)
    for key, length in (("request_seconds", attempts), ("put_seconds", count)):
        values = item[key]
        if (
            not isinstance(values, list)
            or len(values) != length
            or any(number(v) <= 0 for v in values)
        ):
            raise ValueError("upload request timing counters differ")
    if Counter(item["put_seconds"]) - Counter(item["request_seconds"]):
        raise ValueError("upload PUT timings are not actual request observations")
    if not (
        item["open_connections"] <= item["peak_connections"] <= item["connections"]
        and item["active_requests"] <= item["peak_requests"] <= attempts
        and item["active_puts"] <= item["peak_puts"] <= count
        and item["open_sources"] <= item["peak_sources"]
    ):
        raise ValueError("upload observed resource counters inconsistent")
    if (
        item["source_bytes"] != total
        or item["confirmed_bytes"] != total
        or item["confirmed_files"] != count
    ):
        raise ValueError("upload source/confirmation counters differ")
    largest, chunks = item["max_source_chunk_bytes"], item["source_chunks"]
    if not 0 < largest <= total or not largest + chunks - 1 <= total <= chunks * largest:
        raise ValueError("upload source chunk counters inconsistent")
    return item


def metrics_passed(item: dict[str, Any]) -> bool:
    return bool(
        all(
            item[key] == 0
            for key in ("open_connections", "active_requests", "active_puts", "open_sources")
        )
        and all(
            1 <= item[key] <= 2
            for key in ("peak_connections", "peak_requests", "peak_puts", "peak_sources")
        )
        and item["max_source_chunk_bytes"] <= LIMITS["source_chunk_bytes"]
        and all(number(value) <= 120 for value in item["put_seconds"])
    )


def timing_window(item: dict[str, Any], elapsed: float) -> None:
    # These intervals start/end within the measured flow, on the same clock.
    # Peak concurrency bounds their total occupancy; warm is a separate flow.
    for key, peak in (("request_seconds", "peak_requests"), ("put_seconds", "peak_puts")):
        values = item[key]
        if max(values) > elapsed or math.fsum(values) > elapsed * item[peak]:
            raise ValueError("upload observed request durations contradict measured window")


def graph(value: object, expected: dict[str, Any], items: list[dict[str, Any]]) -> None:
    item = closed(value, "intent_count receipt_count accepted_receipts intents receipts files")
    count = expected["file_count"]
    total = 2 + 3 * count
    for key in ("intent_count", "receipt_count", "accepted_receipts"):
        if integer(item[key]) != total:
            raise ValueError("upload graph is not completely accepted")
    pairs: list[tuple[str, int | None]] = [("create", None), ("project_link", None)] + [
        (kind, index) for kind in ("presign", "put", "confirm") for index in range(count)
    ]
    for key in ("intents", "receipts"):
        journal_rows(item[key], key == "receipts", pairs)
    verified_files(item["files"], expected, items)


def journal_rows(value: object, receipts: bool, pairs: list[tuple[str, int | None]]) -> None:
    if not isinstance(value, list) or len(value) != len(pairs):
        raise ValueError("incomplete upload journal rows")
    seen = []
    fields = "kind file_index result" if receipts else "kind file_index"
    for row in value:
        part = closed(row, fields)
        if part["file_index"] is not None:
            integer(part["file_index"])
        if receipts and part["result"] != "accepted":
            raise ValueError("upload receipt rejected")
        seen.append((part["kind"], part["file_index"]))
    if sorted(seen, key=str) != sorted(pairs, key=str):
        raise ValueError("upload journal stage/index set differs")


def verified_files(files: object, expected: dict[str, Any], items: list[dict[str, Any]]) -> None:
    if not isinstance(files, list) or len(files) != expected["file_count"]:
        raise ValueError("upload proof file count differs")
    for index, (actual, file, remote) in enumerate(
        zip(files, expected["files"], items, strict=True)
    ):
        equal(
            actual,
            {
                "file_index": index,
                "item_id": remote["id"],
                "path_digest": hashlib.sha256(file["path"].encode("utf-8")).hexdigest(),
                "size_bytes": file["size"],
                "sha256": file["sha256"],
            },
            "upload ordered proof byte/path/item mismatch",
        )


def server(value: object, expected: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    item = closed(value, SERVER_FIELDS)
    for key in set(item) - {"received", "items", "requests", "statuses"}:
        integer(item[key])
    equal(
        item["received"], expected["files"], "upload received bytes differ from independent oracle"
    )
    count = expected["file_count"]
    if [
        item[key]
        for key in ("create_calls", "link_calls", "presign_calls", "put_calls", "confirm_calls")
    ] != [1, 1, count, count, count]:
        raise ValueError("upload sink effect count mismatch")
    requests = closed(item["requests"], "GET POST PUT")
    equal(
        requests,
        {
            "GET": sum(row["read_attempts"] for row in observed["sessions"]),
            "POST": 2 + 2 * count,
            "PUT": count,
        },
        "upload actual request/attempt mismatch",
    )
    total_requests = sum(requests.values())
    equal(item["statuses"], {"200": total_requests - 1, "201": 1}, "upload sink failed response")
    if (
        not 1 <= item["connection_count"] <= total_requests
        or item["connection_count"] != observed["connections"]
    ):
        raise ValueError("upload TCP connection counters differ")
    if item["control_bytes"] != sum(row["control_request_bytes"] for row in observed["sessions"]):
        raise ValueError("upload actual control request byte mismatch")
    items = item["items"]
    if not isinstance(items, list) or len(items) != count:
        raise ValueError("upload sink item count differs")
    ids = set()
    for actual, file in zip(items, expected["files"], strict=True):
        part = closed(actual, "id dataset_id original_filename file_size_bytes sha256_hash")
        CHECKS["pattern_value"](
            part["id"], re.compile(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}")
        )
        ids.add(part["id"])
        equal(
            {k: v for k, v in part.items() if k != "id"},
            {
                "dataset_id": DATASET,
                "original_filename": file["path"],
                "file_size_bytes": file["size"],
                "sha256_hash": file["sha256"],
            },
            "upload remote item bytes differ from independent oracle",
        )
    if len(ids) != count:
        raise ValueError("upload remote item IDs are not distinct")
    return item


def server_passed(item: dict[str, Any]) -> bool:
    return bool(
        0 < item["max_read_bytes"] <= 65_536
        and item["errors"] == item["active_requests"] == 0
        and 1 <= item["peak_active_requests"] <= 2
    )


RUN_FIELDS = (
    "label sample client server warm_server passed client_process_pid "
    "server_process_pid warm_server_process_pid"
)


def evaluate_run(value: object, proof: dict[str, Any], controller_pid: int) -> bool:
    row = closed(value, RUN_FIELDS)
    expected = expected_manifest(row["label"])
    if row["label"] not in LABELS or integer(row["sample"], 1) > 3:
        raise ValueError("unknown upload sample identity")
    raw = row["client"]
    if not isinstance(raw, dict) or not isinstance(raw.get("runtime"), dict):
        raise ValueError("upload client/runtime missing")
    os_name = CHECKS["text_value"](raw["runtime"].get("os"))
    extra = " baseline_rss_pages rss_page_bytes" if os_name.startswith("Linux") else ""
    client = closed(raw, CLIENT_FIELDS + extra)
    installed = runtime(client["runtime"], proof)
    if integer(client["pid"], 1) != installed["pid"]:
        raise ValueError("upload client PID mismatch")
    observed = metrics(client["metrics"], expected)
    warm_expected = expected_manifest("warm")
    warm_metrics = metrics(client["warm_metrics"], warm_expected)
    sink = server(row["server"], expected, observed)
    warm = server(row["warm_server"], warm_expected, warm_metrics)
    for field, actual in (
        ("client_process_pid", client["pid"]),
        ("server_process_pid", sink["pid"]),
        ("warm_server_process_pid", warm["pid"]),
    ):
        if integer(row[field], 1) != actual:
            raise ValueError("upload child PID differs from controller observation")
    pids = (controller_pid, client["pid"], integer(sink["pid"], 1), integer(warm["pid"], 1))
    if len(set(pids)) != 4:
        raise ValueError("upload controller/client/warm/server must be separate processes")
    graph(client["graph"], expected, sink["items"])
    equal(
        client["public"],
        {
            "operation_status": "succeeded",
            "verification_level": "metadata",
            "authority_verified": False,
            "remote_bytes_verified": False,
            "result_operation_id": None,
        },
        "upload public result overclaims verification",
    )
    upper = STREAM["rss_interval"](client)
    elapsed = number(client["elapsed_seconds"])
    if elapsed <= 0:
        raise ValueError("upload elapsed time must be positive")
    timing_window(observed, elapsed)
    return bool(
        upper <= LIMITS["rss_upper_bytes"]
        and elapsed <= LIMITS["window_seconds"]
        and metrics_passed(observed)
        and metrics_passed(warm_metrics)
        and server_passed(sink)
        and server_passed(warm)
    )


def validate_run(value: object, proof: dict[str, Any], controller_pid: int) -> dict[str, Any]:
    row = closed(value, RUN_FIELDS)
    CHECKS["flag"](row["passed"], evaluate_run(row, proof, controller_pid))
    return row


def growth(runs: list[dict[str, Any]]) -> dict[str, Any]:
    byte_runs = [row for row in runs if row["label"] != "capacity"]
    span = max(
        0,
        max(
            high["client"]["extra_rss_upper_bound_bytes"]
            - low["client"]["extra_rss_lower_bound_bytes"]
            for high in byte_runs
            for low in byte_runs
            if high["label"] != low["label"]
        ),
    )
    return {"span_upper_bound_bytes": span, "passed": span <= LIMITS["growth_upper_bytes"]}


def report_passed(
    proof: dict[str, Any], runs: list[dict[str, Any]], computed_growth: dict[str, Any]
) -> bool:
    identities = [
        {k: v for k, v in row["client"]["runtime"].items() if k not in {"pid", "modules"}}
        for row in runs
    ]
    return bool(
        proof["source_before"] == proof["source_after"]
        and proof["wheel_before"] == proof["wheel_after"]
        and all(identity == identities[0] for identity in identities)
        and all(row["passed"] for row in runs)
        and computed_growth["passed"]
    )


def summarize_report(value: object) -> dict[str, Any]:
    report = closed(
        value,
        "schema_version report_kind source_commit environment provenance method limits "
        "controller_pid runs growth passed",
    )
    equal(report["schema_version"], 1, "unknown upload report version")
    if report["report_kind"] != "upload_budget_v1" or report["method"] != METHOD:
        raise ValueError("unknown upload measurement kind/method")
    equal(report["limits"], LIMITS, "upload measurement limits changed")
    environment = closed(report["environment"], "cpu disk_type")
    for item in environment.values():
        CHECKS["text_value"](item)
    proof = provenance(report["provenance"], report["source_commit"])
    controller_pid = integer(report["controller_pid"], 1)
    if not isinstance(report["runs"], list) or len(report["runs"]) != 12:
        raise ValueError("upload report requires twelve fresh processes")
    runs = [validate_run(row, proof, controller_pid) for row in report["runs"]]
    equal(
        [(r["label"], r["sample"]) for r in runs],
        [(label, sample) for label in LABELS for sample in (1, 2, 3)],
        "upload samples missing/duplicate/out of order",
    )
    client_pids = [row["client"]["pid"] for row in runs]
    if len(set(client_pids)) != 12:
        raise ValueError("upload requires fresh client processes")
    computed_growth = growth(runs)
    equal(report["growth"], computed_growth, "upload growth decision differs")
    passed = report_passed(proof, runs, computed_growth)
    CHECKS["flag"](report["passed"], passed)
    return {
        "kind": "upload-budget",
        "cases": 12,
        "passed": passed,
        "growth": computed_growth,
        "max_elapsed_seconds": max(row["client"]["elapsed_seconds"] for row in runs),
        "max_extra_rss_upper_bound_bytes": max(
            row["client"]["extra_rss_upper_bound_bytes"] for row in runs
        ),
    }
