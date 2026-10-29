"""Archive public measurement reports losslessly and verify their reviewable index."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

MAX_REPORT_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_BYTES = 4 * 1024 * 1024
NAME = re.compile(r"[a-z0-9][a-z0-9-]*\.json")
COMMIT = re.compile(r"[0-9a-f]{40}")
MANIFEST = "evidence-manifest.json"
INDEX = "evidence.md"


def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate JSON key")
    return result


def reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON value: {value}")


def finite_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("non-finite JSON number")
    return result


def decode(content: bytes) -> dict[str, Any]:
    value = json.loads(
        content.decode("utf-8"),
        object_pairs_hook=object_pairs,
        parse_constant=reject_constant,
        parse_float=finite_float,
    )
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return dict(value)


def encode(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def read_bounded(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("expected a regular evidence file")
    with path.open("rb") as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError("evidence size limit exceeded")
    return content


def research_directory(root: Path) -> Path:
    path = root / "docs/research"
    for candidate in (root / "docs", path, path / "raw"):
        if candidate.is_symlink():
            raise ValueError("evidence directory must not be a symlink")
    return path


def number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("expected a finite measurement")
    return float(value)


def measurement(value: dict[str, Any], *, startup: bool, rounded: bool = False) -> dict[str, Any]:
    samples_key, p95_key = (
        ("warm_samples_ms", "warm_p95_ms") if startup else ("samples_ms", "p95_ms")
    )
    samples = [number(item) for item in value[samples_key]]
    if len(samples) < 30 or any(item < 0 for item in samples):
        raise ValueError("invalid measurement samples")
    p95 = sorted(samples)[math.ceil(0.95 * len(samples)) - 1]
    reported = number(value[p95_key])
    # Older v1 receipts rounded the percentile to three decimal places.
    tolerance = 0.000501 if rounded else 1e-9
    if not math.isclose(p95, reported, rel_tol=0, abs_tol=tolerance):
        raise ValueError("reported p95 does not match all samples")
    budget = number(value["target_ms" if startup else "budget_ms"])
    passed = value["passed"]
    if budget <= 0 or type(passed) is not bool or passed != (reported <= budget):
        raise ValueError("reported budget outcome does not match p95")
    return {"samples": len(samples), "p95_ms": reported, "budget_ms": budget, "passed": passed}


def summarize(report: dict[str, Any]) -> dict[str, Any]:
    runs = report.get("runs", [])
    summary: dict[str, Any] = {
        "source_commit": next(
            (
                report[key]
                for key in ("source_commit", "source_base_commit", "source_reference")
                if key in report
            ),
            None,
        ),
        "diagnostic_only": report.get("diagnostic_only", False),
    }
    if "measurements" in report:
        summary["kind"] = "startup"
        groups = {"candidate": report["measurements"]}
        baseline = report.get("comparison", {}).get("baseline_measurements")
        if baseline is not None:
            groups["baseline"] = baseline
        summary["measurements"] = {
            f"{group}/{key}": measurement(
                value, startup=True, rounded=report.get("schema_version") == 1
            )
            for group, entries in groups.items()
            for key, value in entries.items()
        }
    elif isinstance(runs, list) and runs and "samples_ms" in runs[0]:
        summary["kind"] = "jobs"
        metrics = {f"{r['layout']}/{r['action']}": measurement(r, startup=False) for r in runs}
        if len(metrics) != len(runs):
            raise ValueError("duplicate measurement group")
        summary["measurements"] = metrics
    elif "sources" in report and "unchanged" in report:
        summary.update(kind="comparison", cases=len(runs), diagnostic_only=True)
        summary["outcomes"] = dict(sorted(Counter(r["outcome"] for r in runs).items()))
    elif isinstance(runs, list) and runs and "outcome" in runs[0]:
        summary["kind"] = "migration" if "source_version" in runs[0] else "operation"
        summary["cases"] = len(runs)
        summary["outcomes"] = dict(sorted(Counter(r["outcome"] for r in runs).items()))
        elapsed = [number(r["elapsed_ms"]) for r in runs if "elapsed_ms" in r]
        if elapsed:
            summary["max_elapsed_ms"] = max(elapsed)
    elif "results" in report:
        summary.update(kind="installation", cases=len(report["results"]))
        summary["smoke"] = dict(Counter(r["smoke"] for r in report["results"]))
    elif "cases" in report:
        summary.update(kind="help-parity", cases=len(report["cases"]))
    elif "outcome" in report:
        summary.update(kind="diagnostic", outcome=report["outcome"])
        summary["diagnostic_only"] = True
    elif report.get("diagnostic_only") is True:
        summary.update(kind="diagnostic", cases=len(runs), diagnostic_only=True)
    else:
        raise ValueError("unsupported measurement report; test vectors are not raw receipts")
    return summary


def entry(name: str, content: bytes, archive: bytes, original_commit: str | None) -> dict[str, Any]:
    if NAME.fullmatch(name) is None or (
        original_commit is not None and COMMIT.fullmatch(original_commit) is None
    ):
        raise ValueError("invalid evidence name or original commit")
    return {
        "name": name,
        "archive": f"raw/{name}.gz",
        "original_commit": original_commit,
        "content_bytes": len(content),
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "archive_bytes": len(archive),
        "archive_sha256": hashlib.sha256(archive).hexdigest(),
        "summary": summarize(decode(content)),
    }


def catalog(directory: Path) -> list[dict[str, Any]]:
    data = decode(read_bounded(directory / MANIFEST, MAX_REPORT_BYTES))
    if set(data) != {"schema_version", "entries"} or type(data["schema_version"]) is not int:
        raise ValueError("invalid evidence manifest")
    entries = data["entries"]
    if data["schema_version"] != 1 or not isinstance(entries, list) or not 1 <= len(entries) <= 256:
        raise ValueError("invalid evidence manifest entries")
    if any(
        not isinstance(item, dict)
        or not isinstance(item.get("name"), str)
        or NAME.fullmatch(item["name"]) is None
        for item in entries
    ):
        raise ValueError("invalid evidence manifest entry")
    names = [item["name"] for item in entries]
    if names != sorted(set(names)):
        raise ValueError("evidence entries must be unique and sorted")
    return list(entries)


def index_text(entries: list[dict[str, Any]]) -> str:
    lines = [
        "# Ham ölçüm kanıtları",
        "",
        "Bu indeks manifest ve özgün JSON baytlarından üretilir.",
        "Arşiv biçimi ve sınırlar [kanıt standardındadır](../standards/research-evidence.md).",
        "Eski başarısız ölçümler ve tanılar korunur; güncel kabul ayrıca incelenir.",
        "Gzip dosyaları Git checkout'unda tutulur; sdist/wheel içine girmez.",
        "",
    ]
    for item in entries:
        name, summary = item["name"], item["summary"]
        lines += [f"## {name.removesuffix('.json')}", "", f"**Tür:** `{summary['kind']}`."]
        lines.append(f"**Özgün JSON SHA-256:** `{item['content_sha256']}`.")
        if item["original_commit"] is not None:
            url = (
                "https://github.com/HodeTech/Yorunge/blob/"
                f"{item['original_commit']}/docs/research/{name}"
            )
            lines.append(f"[İlk kayıt baytları]({url}); yerel arşiv `raw/{name}.gz`.")
        else:
            lines.append(f"**Yerel arşiv:** `raw/{name}.gz`.")
        lines.append("**Özet:** `" + json.dumps(summary, ensure_ascii=False, sort_keys=True) + "`.")
        lines.append("")
    return "\n".join(lines)


def unpack(directory: Path, item: dict[str, Any]) -> bytes:
    archive = read_bounded(directory / "raw" / f"{item['name']}.gz", MAX_ARCHIVE_BYTES)
    with gzip.GzipFile(fileobj=io.BytesIO(archive)) as stream:
        content = stream.read(MAX_REPORT_BYTES + 1)
    if len(content) > MAX_REPORT_BYTES:
        raise ValueError("decompressed evidence size limit exceeded")
    expected = entry(item["name"], content, archive, item.get("original_commit"))
    if json.dumps(expected, sort_keys=True) != json.dumps(item, sort_keys=True):
        raise ValueError(f"evidence hash or summary mismatch: {item['name']}")
    return content


def verify(root: Path) -> int:
    directory = research_directory(root)
    entries = catalog(directory)
    expected = {f"{item['name']}.gz" for item in entries}
    if {path.name for path in (directory / "raw").iterdir()} != expected:
        raise ValueError("unregistered or missing evidence archive")
    for item in entries:
        unpack(directory, item)
        if (directory / item["name"]).exists():
            raise ValueError("archived report must not also be committed as expanded JSON")
    if read_bounded(directory / INDEX, MAX_REPORT_BYTES) != index_text(entries).encode():
        raise ValueError("evidence index is stale")
    return len(entries)


def replace_metadata(path: Path, content: bytes) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("metadata target must be a regular file")
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.close()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def archive_report(root: Path, source: Path, original_commit: str | None) -> None:
    directory = research_directory(root)
    if not source.resolve().is_relative_to(root.resolve()) or source.resolve().is_relative_to(
        root / "docs/analysis/private"
    ):
        raise ValueError("only public checkout reports can be archived")
    content = read_bounded(source, MAX_REPORT_BYTES)
    archive = gzip.compress(content, mtime=0)
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise ValueError("compressed evidence size limit exceeded")
    item = entry(source.name, content, archive, original_commit)
    entries = catalog(directory) if (directory / MANIFEST).exists() else []
    if any(existing["name"] == source.name for existing in entries):
        raise ValueError("evidence already registered; existing bytes are preserved")
    entries = sorted([*entries, item], key=lambda value: value["name"])
    (directory / "raw").mkdir(exist_ok=True)
    with (directory / "raw" / f"{source.name}.gz").open("xb") as stream:
        stream.write(archive)
    replace_metadata(directory / MANIFEST, encode({"schema_version": 1, "entries": entries}))
    replace_metadata(directory / INDEX, index_text(entries).encode())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("verify")
    add = commands.add_parser("archive")
    add.add_argument("source", type=Path)
    add.add_argument("--original-commit")
    show = commands.add_parser("show")
    show.add_argument("name")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        if args.action == "archive":
            archive_report(root, args.source, args.original_commit)
            print("Archived original bytes; the input file was preserved.")
        elif args.action == "show":
            directory = research_directory(root)
            item = next((item for item in catalog(directory) if item["name"] == args.name), None)
            if item is None:
                raise ValueError("unknown evidence name")
            sys.stdout.buffer.write(unpack(directory, item))
        else:
            print(f"Verified {verify(root)} lossless evidence archives and their index.")
    except (OSError, ValueError, KeyError, TypeError, EOFError) as error:
        parser.exit(1, f"Evidence check failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
