"""Independent closed download-budget verifier; never trusts producer byte oracles.

Report kind ``download_budget_v1``: serial installed ``api.download_model_weights`` measurements
(labels 16/256/1024 MiB, and ``resume``: a 256 MiB object cut once and then resumed), each in a
fresh runtime-only ``-I`` client against a separate-process TLS object server. Native RSS follows
docs/standards/performance.md: instant baseline ``B``, lifetime peak ``H0`` before and ``H1`` after
the window, ``U = H1 - B``, ``L = U if H1 > H0 else 0``, and the cross-size ``G``.

Every verdict of one run is a named rule (:func:`judge_run`); a measured failure is a ``False`` rule
and the run stays in the report, while a malformed or self-contradicting record raises
``ValueError``. A partial report (a smoke subset of labels or samples) is valid but never accepted.
"""

from __future__ import annotations

import hashlib
import json
import math
import runpy
from functools import cache
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
CHECKS = runpy.run_path(str(ROOT / "scripts/research_evidence.py"))
STREAM = runpy.run_path(str(ROOT / "scripts/benchmark-stream.py"))
MIB = 1_048_576
LABELS = ("16", "256", "1024", "resume")
BYTE_LABELS = ("16", "256", "1024")  # only these three enter the cross-size growth
SAMPLES = 3
WARM = {"16": "warm", "256": "warm", "1024": "warm", "resume": "warm-resume"}
# An independent copy of the served objects: (size, offset where the first signed GET is cut).
OBJECTS: dict[str, tuple[int, int | None]] = {
    "warm": (MIB, None),
    "warm-resume": (MIB, 524_289),
    "16": (16 * MIB, None),
    "256": (256 * MIB, None),
    "1024": (1024 * MIB, None),
    "resume": (256 * MIB, 24 * 8 * MIB + 1_000_003),
}
LIMITS = {
    "rss_upper_bytes": 67_108_864,
    "growth_upper_bytes": 8_388_608,
    "window_seconds": 900,
    "write_block_bytes": 1_048_576,
    "checkpoint_bytes": 8_388_608,
    "server_block_bytes": 65_536,
}
METHOD = (
    "separate TLS object server; public download_model_weights with the independent sha256 "
    "expectation; fixed 1 MiB warm of the same path; native B/H0/H1; instrumented stage write, "
    "fsync and full-sync timers inside the window"
)
UPLOAD_VECTOR = "tests/fixtures/upload-native-vectors-v1.json"  # the one non-Python input of upload
REQUIRED_SOURCES = (
    UPLOAD_VECTOR,
    "scripts/benchmark-download.py",
    "scripts/benchmark-stream.py",
    "scripts/dataset_wheel.py",
    "scripts/download_evidence.py",
    "tests/fixtures/download_native_client.py",
    "tests/fixtures/download_native_control.py",
    "tests/fixtures/download_native_data.py",
    "tests/fixtures/download_native_server.py",
    "tests/fixtures/http_server.py",
    "tests/fixtures/model_network.py",
    "tests/fixtures/stream_budget.py",
)
TARGET_NAME = "weights.onnx"
SIGNED_HEADERS = ("accept-encoding", "host")  # plus range and if-range on a resumed request
CLIENT_FIELDS = (
    "runtime pid baseline_rss_native baseline_rss_method baseline_rss_bytes "
    "pretransfer_peak_rss_native pretransfer_peak_rss_bytes peak_rss_native peak_rss_bytes "
    "rss_native_unit extra_rss_lower_bound_bytes extra_rss_upper_bound_bytes elapsed_seconds "
    "window public written warm"
)
WINDOW_COUNTS = (
    "write_calls write_bytes max_write_bytes stage_fsync_calls other_fsync_calls full_sync_calls"
)
WINDOW_SECONDS = (
    "write_seconds max_write_seconds stage_fsync_seconds max_stage_fsync_seconds "
    "other_fsync_seconds full_sync_seconds"
)
OUTCOME_FIELDS = (
    "bytes sha256 verification_level expectation_source resumed resumed_from_bytes first_error"
)
WRITTEN_FIELDS = "file_bytes file_sha256 entries payload_removed"
SERVER_FIELDS = (
    "pid label size cut_at etag requests signed bytes_sent connection_count active_requests "
    "peak_active_requests credential_violations header_violations json_key_failures errors "
    "max_block_bytes json_header_names signed_header_names"
)
SIGNED_FIELDS = "range if_range status content_length content_range bytes_sent completed cut"
RUN_FIELDS = (
    "label sample client server warm_server passed client_process_pid "
    "server_process_pid warm_server_process_pid"
)
REPORT_FIELDS = (
    "schema_version report_kind source_commit environment provenance method limits scope "
    "controller_pid runs growth passed accepted"
)


def closed(value: object, fields: str) -> dict[str, Any]:
    return cast(dict[str, Any], CHECKS["closed"](value, fields, "download measurement"))


def integer(value: object, minimum: int = 0) -> int:
    return cast(int, CHECKS["integer"](value, minimum=minimum))


def number(value: object) -> float:
    return cast(float, CHECKS["number"](value))


def text(value: object) -> str:
    return cast(str, CHECKS["text_value"](value))


def boolean(value: object) -> bool:
    if type(value) is not bool:
        raise ValueError("download measurement flag must be boolean")
    return value


def optional(value: object, kind: type) -> Any:
    if value is not None and type(value) is not kind:
        raise ValueError("download measurement field has the wrong type")
    return value


def equal(actual: object, expected: object, message: str) -> None:
    # Canonical JSON comparison also distinguishes bool/int and rejects NaN.
    if canonical(actual) != canonical(expected):
        raise ValueError(message)


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


@cache
def object_sha256(size: int) -> str:
    """Independent oracle: block ``b`` is a 64 KiB window, ``37 * b`` bytes into a periodic buffer.

    The fixture module translates a base block and the server rotates and repeats a cycle; this is
    a third derivation of the same bytes and, like them, holds no more than one block at a time.
    """
    if type(size) is not int or not 1 <= size <= 1_073_741_824:
        raise ValueError("download object size must be between 1 byte and 1 GiB")
    periodic = bytes(range(256)) * 258
    digest = hashlib.sha256()
    remaining, block = size, 0
    while remaining:
        shift = (37 * block) % 256
        used = min(remaining, 65_536)
        digest.update(memoryview(periodic)[shift : shift + used])
        remaining -= used
        block += 1
    return digest.hexdigest()


def source(root: Path) -> dict[str, Any]:
    """Everything the upload map holds (the common startup map plus its vector file) and more.

    The download oracle is arithmetic and needs no vector file; the map keeps the upload one so
    that it is a superset of the upload map, and requires the measurement files to be in it.
    """
    sources = runpy.run_path(str(ROOT / "scripts/startup_evidence.py"))
    value = cast(dict[str, Any], sources["source"](root))
    vector = root / UPLOAD_VECTOR
    if vector.is_file() and not vector.is_symlink():
        value["source_sha256"][UPLOAD_VECTOR] = hashlib.sha256(vector.read_bytes()).hexdigest()
    missing = [name for name in REQUIRED_SOURCES if name not in value["source_sha256"]]
    if missing:
        raise ValueError("download measurement source map lacks: " + ", ".join(missing))
    return value


def provenance(value: object, commit: object) -> dict[str, Any]:
    item = closed(
        value,
        "source_before source_after locked_runtime wheel_before wheel_after "
        "wheel_product_sha256 wheel_metadata_sha256",
    )
    before = CHECKS["source_snapshot"](item["source_before"])
    CHECKS["source_snapshot"](item["source_after"])
    if commit != before["commit"] or any(
        name not in before["source_sha256"] for name in REQUIRED_SOURCES
    ):
        raise ValueError("download source identity or measurement files missing")
    CHECKS["package_versions"](item["locked_runtime"])
    for key in ("wheel_before", "wheel_after"):
        CHECKS["pattern_value"](item[key], CHECKS["SHA256"])
    product = {k: v for k, v in before["source_sha256"].items() if k.startswith("src/yorunge/")}
    equal(
        CHECKS["hash_map"](item["wheel_product_sha256"]), product, "download wheel/source mismatch"
    )
    metadata = closed(item["wheel_metadata_sha256"], "METADATA WHEEL entry_points.txt")
    CHECKS["hash_map"](metadata)
    if "src/yorunge/py.typed" not in product:
        raise ValueError("download source type marker missing")
    return item


def runtime(value: object, proof: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("download runtime must be an object")
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
        "download marker mismatch",
    )
    equal(
        value.get("metadata_sha256"), proof["wheel_metadata_sha256"], "download metadata mismatch"
    )
    equal(value["packages"], proof["locked_runtime"], "download frozen runtime mismatch")
    CHECKS["flag"](value["isolated"], True)
    CHECKS["flag"](value["installed_source_matches"], True)
    return value


def window(value: object) -> dict[str, Any]:
    """The instrumented counters of the window: internally consistent numbers, nothing more."""
    item = closed(value, "instrumented " + WINDOW_COUNTS + " " + WINDOW_SECONDS)
    CHECKS["flag"](item["instrumented"], True)
    for key in WINDOW_COUNTS.split():
        integer(item[key])
    for key in WINDOW_SECONDS.split():
        if number(item[key]) < 0:
            raise ValueError("download window durations cannot be negative")
    calls, size, largest = item["write_calls"], item["write_bytes"], item["max_write_bytes"]
    # No write at all, or each of calls <= bytes <= calls * largest with the largest within bytes.
    if (
        not largest <= size <= calls * largest
        or calls > size
        or item["max_write_seconds"] > item["write_seconds"]
    ):
        raise ValueError("download window write counters are inconsistent")
    if item["max_stage_fsync_seconds"] > item["stage_fsync_seconds"]:
        raise ValueError("download window stage fsync counters are inconsistent")
    for calls_key, seconds_key in (
        ("write_calls", "write_seconds"),
        ("stage_fsync_calls", "stage_fsync_seconds"),
        ("other_fsync_calls", "other_fsync_seconds"),
        ("full_sync_calls", "full_sync_seconds"),
    ):
        if item[calls_key] == 0 and item[seconds_key] != 0:
            raise ValueError("download window reports time without calls")
    return item


def timing_window(item: dict[str, Any], elapsed: float) -> None:
    # The four kinds of call never overlap and all lie inside the measured window.
    total = math.fsum(
        item[key]
        for key in (
            "write_seconds",
            "stage_fsync_seconds",
            "other_fsync_seconds",
            "full_sync_seconds",
        )
    )
    if total > elapsed:
        raise ValueError("download observed call durations contradict measured window")


def outcome(value: object) -> dict[str, Any]:
    item = closed(value, OUTCOME_FIELDS)
    integer(item["bytes"])
    integer(item["resumed_from_bytes"])
    CHECKS["pattern_value"](item["sha256"], CHECKS["SHA256"])
    text(item["verification_level"])
    text(item["expectation_source"])
    boolean(item["resumed"])
    if item["first_error"] is not None:
        text(item["first_error"])
    return item


def written(value: object) -> dict[str, Any]:
    item = closed(value, WRITTEN_FIELDS)
    integer(item["file_bytes"])
    CHECKS["pattern_value"](item["file_sha256"], CHECKS["SHA256"])
    names = item["entries"]
    if not isinstance(names, list) or any(type(name) is not str for name in names):
        raise ValueError("download directory entries must be a list of names")
    boolean(item["payload_removed"])
    return item


def signed_record(value: object) -> dict[str, Any]:
    item = closed(value, SIGNED_FIELDS)
    optional(item["range"], str)
    optional(item["if_range"], str)
    optional(item["content_range"], str)
    if item["content_length"] is not None:
        integer(item["content_length"])
    integer(item["status"])
    integer(item["bytes_sent"])
    boolean(item["completed"])
    boolean(item["cut"])
    return item


def server(value: object, label: str) -> dict[str, Any]:
    """The closed account of one object server, which must be the one this label was served by."""
    item = closed(value, SERVER_FIELDS)
    size, cut_at = OBJECTS[label]
    equal(
        [item["label"], item["size"], item["cut_at"], item["etag"]],
        [label, size, cut_at, f'"native-download-{label}"'],
        "download server served another fixture",
    )
    for key in (
        "pid connection_count active_requests peak_active_requests credential_violations "
        "header_violations json_key_failures errors max_block_bytes bytes_sent"
    ).split():
        integer(item[key])
    requests = closed(item["requests"], "json signed unexpected")
    for count in requests.values():
        integer(count)
    rows = item["signed"]
    if not isinstance(rows, list) or len(rows) != requests["signed"]:
        raise ValueError("download server signed request records differ from its counters")
    records = [signed_record(row) for row in rows]
    if item["bytes_sent"] != sum(row["bytes_sent"] for row in records):
        raise ValueError("download server byte counters differ")
    for key in ("json_header_names", "signed_header_names"):
        names = item[key]
        if not isinstance(names, list) or any(type(name) is not str for name in names):
            raise ValueError("download server header names must be a list of names")
    return item


def exchange(sink: dict[str, Any], label: str, resumed_from: int) -> dict[str, bool]:
    """What the server must have seen for this label, and what it must have refused to see."""
    size, cut_at = OBJECTS[label]
    etag = f'"native-download-{label}"'
    calls = 1 if cut_at is None else 2
    expected: list[dict[str, Any]]
    if cut_at is None:
        expected = [
            {
                "range": None,
                "if_range": None,
                "status": 200,
                "content_length": size,
                "content_range": None,
                "bytes_sent": size,
                "completed": True,
                "cut": False,
            }
        ]
        headers = list(SIGNED_HEADERS)
    else:
        expected = [
            {
                "range": None,
                "if_range": None,
                "status": 200,
                "content_length": size,
                "content_range": None,
                "bytes_sent": cut_at,
                "completed": False,
                "cut": True,
            },
            {
                "range": f"bytes={resumed_from}-",
                "if_range": etag,
                "status": 206,
                "content_length": size - resumed_from,
                "content_range": f"bytes {resumed_from}-{size - 1}/{size}",
                "bytes_sent": size - resumed_from,
                "completed": True,
                "cut": False,
            },
        ]
        headers = sorted((*SIGNED_HEADERS, "range", "if-range"))
    json_names = set(sink["json_header_names"])
    return {
        "requests": canonical(sink["requests"])
        == canonical({"json": calls, "signed": calls, "unexpected": 0}),
        "ranges": canonical(sink["signed"]) == canonical(expected),
        "credentials": sink["credential_violations"] == 0
        and sink["header_violations"] == 0
        and sink["json_key_failures"] == 0
        and {"host", "x-api-key"} <= json_names
        and not json_names & {"authorization", "cookie", "proxy-authorization"},
        "headers": sink["signed_header_names"] == headers,
        "health": sink["errors"] == 0
        and sink["active_requests"] == 0
        and 1 <= sink["peak_active_requests"] <= 2,
        "connections": sink["connection_count"] == calls,
        "blocks": 0 < sink["max_block_bytes"] <= LIMITS["server_block_bytes"],
    }


def settled(label: str, result: dict[str, Any]) -> dict[str, bool]:
    """The public result of one flow: right bytes, the right level, and the right resume state."""
    size, cut_at = OBJECTS[label]
    oracle = object_sha256(size)
    resumed_from = result["resumed_from_bytes"]
    if cut_at is None:
        resume_state = (
            result["resumed"] is False and resumed_from == 0 and result["first_error"] is None
        )
    else:
        resume_state = (
            result["resumed"] is True
            and resumed_from == cut_at  # a clean stop checkpoints exactly what was written
            and result["first_error"] == "download_incomplete"
        )
    return {
        "bytes": result["bytes"] == size,
        "sha256": result["sha256"] == oracle,
        "level": result["verification_level"] == "sha256_matched",
        "source": result["expectation_source"] == "user_supplied",
        "resume_state": resume_state,
    }


def checkpoints(label: str, item: dict[str, Any], resumed_from: int) -> bool:
    """Stage fsyncs lie between what the 8 MiB checkpoint rule allows and requires.

    A checkpoint follows the write that brings the unsynced bytes to 8 MiB, so it can overshoot by
    at most the largest write; each run adds the fsync of the completion checkpoint, and a cut run
    the one of the clean stop. A resumed run counts its two segments apart.
    """
    size, cut_at = OBJECTS[label]
    step, slack = LIMITS["checkpoint_bytes"], item["max_write_bytes"]
    segments = [size] if cut_at is None else [cut_at, size - resumed_from]
    fixed = (1, 1) if cut_at is None else (1, 2)
    lower = sum(segment // (step + slack) for segment in segments) + fixed[0]
    upper = sum(segment // step for segment in segments) + fixed[1]
    return bool(lower <= item["stage_fsync_calls"] <= upper)


def judge_run(value: object, proof: dict[str, Any], controller_pid: int) -> dict[str, bool]:
    """Every rule of one run by name; ``ValueError`` for a record that is not a valid record."""
    row = closed(value, RUN_FIELDS)
    if row["label"] not in LABELS or integer(row["sample"], 1) > SAMPLES:
        raise ValueError("unknown download sample identity")
    label = row["label"]
    size, _ = OBJECTS[label]
    raw = row["client"]
    if not isinstance(raw, dict) or not isinstance(raw.get("runtime"), dict):
        raise ValueError("download client/runtime missing")
    os_name = text(raw["runtime"].get("os"))
    extra = " baseline_rss_pages rss_page_bytes" if os_name.startswith("Linux") else ""
    client = closed(raw, CLIENT_FIELDS + extra)
    installed = runtime(client["runtime"], proof)
    if integer(client["pid"], 1) != installed["pid"]:
        raise ValueError("download client PID mismatch")
    counters = window(client["window"])
    result, disk, warm = (
        outcome(client["public"]),
        written(client["written"]),
        outcome(client["warm"]),
    )
    sink = server(row["server"], label)
    warm_sink = server(row["warm_server"], WARM[label])
    for field, actual in (
        ("client_process_pid", client["pid"]),
        ("server_process_pid", sink["pid"]),
        ("warm_server_process_pid", warm_sink["pid"]),
    ):
        if integer(row[field], 1) != actual:
            raise ValueError("download child PID differs from controller observation")
    pids = (controller_pid, client["pid"], integer(sink["pid"], 1), integer(warm_sink["pid"], 1))
    if len(set(pids)) != 4:
        raise ValueError("download controller/client/warm/server must be separate processes")
    upper = STREAM["rss_interval"](client)
    elapsed = number(client["elapsed_seconds"])
    if elapsed <= 0:
        raise ValueError("download elapsed time must be positive")
    timing_window(counters, elapsed)
    oracle = object_sha256(size)
    served = exchange(sink, label, result["resumed_from_bytes"])
    warmed = exchange(warm_sink, WARM[label], warm["resumed_from_bytes"])
    final = settled(label, result)
    warm_final = settled(WARM[label], warm)
    rules = {
        "rss_upper": upper <= LIMITS["rss_upper_bytes"],
        "window_seconds": elapsed <= LIMITS["window_seconds"],
        "result_bytes": final["bytes"] and disk["file_bytes"] == size,
        "result_sha256": final["sha256"] and disk["file_sha256"] == oracle,
        "result_level": final["level"],
        "result_source": final["source"],
        "result_resume": final["resume_state"],
        "directory_clean": disk["entries"] == [TARGET_NAME],
        "write_accounting": counters["write_bytes"] == sink["bytes_sent"],
        "write_block": counters["max_write_bytes"] <= LIMITS["write_block_bytes"],
        "checkpoint_fsyncs": checkpoints(label, counters, result["resumed_from_bytes"]),
        "full_sync": 1 <= counters["full_sync_calls"] <= 2,
        "warm_result": all(warm_final.values()),
    }
    rules.update({"server_" + name: ok for name, ok in served.items()})
    rules.update({"warm_server_" + name: ok for name, ok in warmed.items()})
    return rules


def evaluate_run(value: object, proof: dict[str, Any], controller_pid: int) -> bool:
    return all(judge_run(value, proof, controller_pid).values())


def validate_run(value: object, proof: dict[str, Any], controller_pid: int) -> dict[str, Any]:
    row = closed(value, RUN_FIELDS)
    CHECKS["flag"](row["passed"], evaluate_run(row, proof, controller_pid))
    return row


def growth(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """``G = max(0, U_i - L_j)`` over runs of different byte labels; ``resume`` is not in it."""
    byte_runs = [row for row in runs if row["label"] in BYTE_LABELS]
    spans = [
        high["client"]["extra_rss_upper_bound_bytes"] - low["client"]["extra_rss_lower_bound_bytes"]
        for high in byte_runs
        for low in byte_runs
        if high["label"] != low["label"]
    ]
    if not spans:
        # Fewer than two byte sizes: there is no cross-size evidence, and no acceptance.
        return {"span_upper_bound_bytes": None, "passed": False}
    span = max(0, max(spans))
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


def is_partial(labels: list[str], samples: int) -> bool:
    return labels != list(LABELS) or samples != SAMPLES


def scope(value: object) -> dict[str, Any]:
    item = closed(value, "labels samples partial")
    labels = item["labels"]
    if (
        not isinstance(labels, list)
        or not labels
        or labels != [label for label in LABELS if label in labels]
    ):
        raise ValueError("download labels must be a nonempty subset in canonical order")
    samples = integer(item["samples"], 1)
    if samples > SAMPLES:
        raise ValueError("download samples per label cannot exceed three")
    CHECKS["flag"](item["partial"], is_partial(labels, samples))
    return item


def summarize_report(value: object) -> dict[str, Any]:
    report = closed(value, REPORT_FIELDS)
    equal(report["schema_version"], 1, "unknown download report version")
    if report["report_kind"] != "download_budget_v1" or report["method"] != METHOD:
        raise ValueError("unknown download measurement kind/method")
    equal(report["limits"], LIMITS, "download measurement limits changed")
    environment = closed(report["environment"], "cpu disk_type")
    for item in environment.values():
        text(item)
    proof = provenance(report["provenance"], report["source_commit"])
    controller_pid = integer(report["controller_pid"], 1)
    chosen = scope(report["scope"])
    expected_runs = [
        (label, sample) for label in chosen["labels"] for sample in range(1, chosen["samples"] + 1)
    ]
    if not isinstance(report["runs"], list) or len(report["runs"]) != len(expected_runs):
        raise ValueError("download report requires every chosen label and sample")
    runs = [validate_run(row, proof, controller_pid) for row in report["runs"]]
    equal(
        [(r["label"], r["sample"]) for r in runs],
        expected_runs,
        "download samples missing/duplicate/out of order",
    )
    client_pids = [row["client"]["pid"] for row in runs]
    if len(set(client_pids)) != len(runs):
        raise ValueError("download requires fresh client processes")
    computed_growth = growth(runs)
    equal(report["growth"], computed_growth, "download growth decision differs")
    passed = report_passed(proof, runs, computed_growth)
    CHECKS["flag"](report["passed"], passed)
    # A smoke subset can pass every rule it has and still is no acceptance.
    CHECKS["flag"](report["accepted"], passed and not chosen["partial"])
    return {
        "kind": "download-budget",
        "cases": len(runs),
        "partial": chosen["partial"],
        "passed": passed,
        "accepted": report["accepted"],
        "growth": computed_growth,
        "max_elapsed_seconds": max(row["client"]["elapsed_seconds"] for row in runs),
        "max_extra_rss_upper_bound_bytes": max(
            row["client"]["extra_rss_upper_bound_bytes"] for row in runs
        ),
    }
