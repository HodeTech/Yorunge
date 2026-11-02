"""Verify archived bytes and failure evidence without executing old measurements."""

import gzip
import io
import json
import runpy
from pathlib import Path

import pytest

CHECKS = runpy.run_path(str(Path(__file__).parents[2] / "scripts/research_evidence.py"))
archive_report = CHECKS["archive_report"]
verify = CHECKS["verify"]


def setup_archive(tmp_path, report=None):
    root = tmp_path / "repo"
    (root / "docs/research").mkdir(parents=True)
    (root / "dist").mkdir()
    source = root / "dist/operation-budget.json"
    if report is None:
        report = {
            "source_base_commit": "a" * 40,
            "runs": [
                {"outcome": "ok", "elapsed_ms": 4990.1},
                {"outcome": "state_busy", "elapsed_ms": 5001.3},
            ],
        }
    original = (json.dumps(report, indent=4) + "\n").encode()
    source.write_bytes(original)
    archive_report(root, source, None)
    return root, source, original


def test_archive_preserves_exact_input_bytes_failures_and_reproducible_gzip(tmp_path):
    root, source, original = setup_archive(tmp_path)
    directory = root / "docs/research"
    packed = (directory / "raw/operation-budget.json.gz").read_bytes()
    assert source.read_bytes() == original
    assert gzip.decompress(packed) == original
    assert packed == gzip.compress(original, mtime=0)
    assert verify(root) == 1
    manifest = json.loads((directory / "evidence-manifest.json").read_bytes())
    summary = manifest["entries"][0]["summary"]
    assert summary["outcomes"] == {"ok": 1, "state_busy": 1}
    assert summary["max_elapsed_ms"] == 5001.3
    assert summary["source_commit"] == "a" * 40


@pytest.mark.parametrize("failure", ["truncated", "altered-data", "summary", "index", "orphan"])
def test_verify_rejects_damaged_bytes_or_dishonest_summary(tmp_path, failure):
    root, source, original = setup_archive(tmp_path)
    directory = root / "docs/research"
    packed = directory / "raw/operation-budget.json.gz"
    if failure == "truncated":
        packed.write_bytes(packed.read_bytes()[:-8])
    elif failure == "altered-data":
        packed.write_bytes(gzip.compress(original.replace(b"state_busy", b"ok"), mtime=0))
    elif failure == "summary":
        manifest = directory / "evidence-manifest.json"
        data = json.loads(manifest.read_bytes())
        data["entries"][0]["summary"]["outcomes"] = {"ok": 2}
        manifest.write_text(json.dumps(data))
    elif failure == "index":
        (directory / "evidence.md").write_text("# stale\n")
    else:
        (directory / "raw/unregistered.json.gz").write_bytes(gzip.compress(b"{}"))
    with pytest.raises((ValueError, EOFError, OSError)):
        verify(root)
    assert source.read_bytes() == original


def test_archive_rejects_existing_receipt_and_preserves_both_versions(tmp_path):
    root, source, original = setup_archive(tmp_path)
    source.write_text('{"runs": [{"outcome": "ok"}]}')
    with pytest.raises(ValueError, match="already registered"):
        archive_report(root, source, None)
    assert verify(root) == 1
    packed = root / "docs/research/raw/operation-budget.json.gz"
    assert gzip.decompress(packed.read_bytes()) == original


@pytest.mark.parametrize("target", ["raw", "evidence-manifest.json", "evidence.md"])
def test_archive_does_not_follow_metadata_or_directory_symlinks(tmp_path, target):
    root = tmp_path / "repo"
    directory = root / "docs/research"
    directory.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "retained"
    sentinel.write_bytes(b"unchanged")
    (directory / target).symlink_to(outside if target == "raw" else sentinel)
    (root / "dist").mkdir()
    source = root / "dist/report.json"
    source.write_text('{"runs": [{"outcome": "ok", "elapsed_ms": 1}]}')
    with pytest.raises(ValueError):
        archive_report(root, source, None)
    assert sentinel.read_bytes() == b"unchanged"


@pytest.mark.parametrize(
    "content", [b'{"runs":[],"runs":[]}', b'{"value":NaN}', b'{"value":1e999}', b"[]"]
)
def test_receipt_json_rejects_ambiguous_or_nonfinite_data(content):
    with pytest.raises(ValueError):
        CHECKS["decode"](content)


def test_archive_does_not_classify_independent_test_vectors_as_measurements(tmp_path):
    with pytest.raises(ValueError, match="test vectors"):
        setup_archive(tmp_path, {"vectors": [{"expected": 1}]})


def test_nearest_rank_uses_all_samples_and_preserves_failed_budget():
    data = {"samples_ms": [1] * 28 + [201, 205], "p95_ms": 201, "budget_ms": 200, "passed": False}
    result = CHECKS["measurement"](data, startup=False)
    assert result["samples"] == 30
    assert result["p95_ms"] == 201
    assert result["passed"] is False
    data["p95_ms"] = 1
    data["passed"] = True
    with pytest.raises(ValueError, match="all samples"):
        CHECKS["measurement"](data, startup=False)


def test_verify_rejects_duplicate_catalog_name(tmp_path):
    root, _, _ = setup_archive(tmp_path)
    manifest = root / "docs/research/evidence-manifest.json"
    data = json.loads(manifest.read_bytes())
    data["entries"].append(data["entries"][0])
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="unique"):
        verify(root)


@pytest.mark.parametrize("attack", ["traversal", "bool-version", "unknown-field", "missing"])
def test_verify_rejects_invalid_catalog_or_missing_archive(tmp_path, attack):
    root, _, _ = setup_archive(tmp_path)
    manifest = root / "docs/research/evidence-manifest.json"
    data = json.loads(manifest.read_bytes())
    if attack == "traversal":
        data["entries"][0]["name"] = "../outside.json"
    elif attack == "bool-version":
        data["schema_version"] = True
    elif attack == "unknown-field":
        data["entries"][0]["unchecked"] = True
    else:
        (root / "docs/research/raw/operation-budget.json.gz").unlink()
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        verify(root)


def test_current_p95_cannot_borrow_the_legacy_rounding_tolerance():
    data = {
        "samples_ms": [200.0004] * 30,
        "p95_ms": 200,
        "budget_ms": 200,
        "passed": True,
    }
    with pytest.raises(ValueError, match="all samples"):
        CHECKS["measurement"](data, startup=False)


@pytest.mark.parametrize("passed", [True, False])
def test_legacy_rounded_boundary_preserves_original_uncertain_budget_decision(passed):
    data = {
        "warm_samples_ms": [200] * 30,
        "warm_p95_ms": 200,
        "target_ms": 200,
        "passed": passed,
    }
    result = CHECKS["measurement"](data, startup=True, rounded=True)
    assert result["passed"] is passed
    assert result["budget_decision_ambiguous_after_rounding"] is True
    data["warm_samples_ms"] = [201] * 30
    data["warm_p95_ms"] = 201
    data["passed"] = True
    with pytest.raises(ValueError, match="budget outcome"):
        CHECKS["measurement"](data, startup=True, rounded=True)


def test_manifest_summary_exposes_all_smoke_and_help_results():
    installation = CHECKS["summarize"](
        {"results": [{"smoke": "passed", "jobs_smoke": "failed", "origin_verified": False}]}
    )
    assert installation["checks"]["smoke"] == {"passed": 1}
    assert installation["checks"]["jobs_smoke"] == {"failed": 1}
    assert installation["checks"]["origin_verified"] == {"false": 1}
    assert installation["checks"]["cache_smoke"] == {"not_recorded": 1}
    help_result = CHECKS["summarize"](
        {"cases": [{"equal": False, "root_expected_jobs_addition": True}, {"equal": True}]}
    )
    assert help_result["checks"]["equal"] == {"false": 1, "true": 1}
    assert help_result["checks"]["root_expected_jobs_addition"] == {
        "true": 1,
        "not_recorded": 1,
    }
    later_help = CHECKS["summarize"]({"cases": [{"matches_initial_p014": False}]})
    assert later_help["checks"]["matches_initial_p014"] == {"false": 1}


@pytest.mark.parametrize("count", [256, 4096])
def test_catalog_extends_legacy_boundary_and_rejects_new_full_capacity(tmp_path, count):
    root, source, original = setup_archive(tmp_path)
    directory = root / "docs/research"
    packed = (directory / "raw/operation-budget.json.gz").read_bytes()
    data = json.loads((directory / "evidence-manifest.json").read_bytes())
    for index in range(1, count):
        name = f"sample-{index:04}.json"
        (directory / "raw" / (name + ".gz")).write_bytes(packed)
        data["entries"].append(CHECKS["entry"](name, original, packed, None))
    data["entries"].sort(key=lambda item: item["name"])
    (directory / "evidence-manifest.json").write_bytes(CHECKS["encode"](data))
    (directory / "evidence.md").write_text(CHECKS["index_text"](data["entries"]))
    assert verify(root) == count
    before = {p.relative_to(directory): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    new_source = source.with_name("next-budget.json")
    new_source.write_bytes(original)
    if count == 4096:
        with pytest.raises(ValueError, match="capacity"):
            archive_report(root, new_source, None)
        assert archive_bytes(root) == before
        assert verify(root) == count
    else:
        archive_report(root, new_source, None)
        assert verify(root) == 257
        current = CHECKS["catalog"](directory)
        assert [item for item in current if item["name"] != new_source.name] == data["entries"]
        for path, content in before.items():
            if path.parts[0] == "raw":
                assert (directory / path).read_bytes() == content
    assert new_source.read_bytes() == original


def archive_bytes(root):
    directory = root / "docs/research"
    return {p.relative_to(directory): p.read_bytes() for p in directory.rglob("*") if p.is_file()}


@pytest.mark.parametrize("delta", [-1, 0, 1])
@pytest.mark.parametrize(
    "budget", ["MAX_ENTRIES", "MAX_TOTAL_ARCHIVE_BYTES", "MAX_TOTAL_REPORT_BYTES", "metadata"]
)
def test_archive_budget_preflight_preserves_all_files_on_rejection(
    tmp_path, monkeypatch, budget, delta
):
    root, source, original = setup_archive(tmp_path)
    before = archive_bytes(root)
    new_source = source.with_name("next-budget.json")
    new_source.write_bytes(original)
    packed = gzip.compress(original, mtime=0)
    directory = root / "docs/research"
    entries = CHECKS["catalog"](directory)
    prospective = sorted(
        [*entries, CHECKS["entry"](new_source.name, original, packed, None)],
        key=lambda item: item["name"],
    )
    totals = {
        "MAX_ENTRIES": 2,
        "MAX_TOTAL_ARCHIVE_BYTES": len(packed) * 2,
        "MAX_TOTAL_REPORT_BYTES": len(original) * 2,
        "metadata": max(
            len(CHECKS["encode"]({"schema_version": 1, "entries": prospective})),
            len(CHECKS["index_text"](prospective).encode()),
        ),
    }
    setting = "MAX_REPORT_BYTES" if budget == "metadata" else budget
    monkeypatch.setitem(archive_report.__globals__, setting, totals[budget] + delta)
    if delta < 0:
        with pytest.raises(ValueError, match="capacity|limit"):
            archive_report(root, new_source, None)
        assert archive_bytes(root) == before
        assert verify(root) == 1
    else:
        archive_report(root, new_source, None)
        assert verify(root) == 2
        assert CHECKS["catalog"](directory)[0] == prospective[0]
        assert (directory / "raw/operation-budget.json.gz").read_bytes() == before[
            Path("raw/operation-budget.json.gz")
        ]
    assert new_source.read_bytes() == original


@pytest.mark.parametrize("field", ["content_bytes", "archive_bytes"])
@pytest.mark.parametrize("value", [True, 1.0, 0, -1, "1"])
def test_catalog_rejects_invalid_size_types_before_opening_archives(
    tmp_path, monkeypatch, field, value
):
    root, _, _ = setup_archive(tmp_path)
    path = root / "docs/research/evidence-manifest.json"
    data = json.loads(path.read_bytes())
    data["entries"][0][field] = value
    path.write_bytes(CHECKS["encode"](data))

    def forbidden(*args, **kwargs):
        pytest.fail("invalid catalogue size must be rejected before unpack")

    monkeypatch.setitem(verify.__globals__, "unpack", forbidden)
    with pytest.raises(ValueError, match="integer"):
        verify(root)


@pytest.mark.parametrize("field", ["content_bytes", "archive_bytes"])
def test_archive_rejects_a_catalogue_that_understates_actual_bytes(tmp_path, field):
    root, source, original = setup_archive(tmp_path)
    path = root / "docs/research/evidence-manifest.json"
    data = json.loads(path.read_bytes())
    data["entries"][0][field] = 1
    path.write_bytes(CHECKS["encode"](data))
    before = archive_bytes(root)
    new_source = source.with_name("next-budget.json")
    new_source.write_bytes(original)
    with pytest.raises(ValueError, match="hash or summary"):
        archive_report(root, new_source, None)
    assert archive_bytes(root) == before
    assert new_source.read_bytes() == original


@pytest.mark.parametrize("damage", ["orphan", "stale-index", "truncated", "missing-manifest"])
def test_archive_does_not_extend_a_broken_catalogue(tmp_path, damage):
    root, source, original = setup_archive(tmp_path)
    directory = root / "docs/research"
    if damage == "orphan":
        (directory / "raw/orphan.json.gz").write_bytes(gzip.compress(original))
    elif damage == "stale-index":
        (directory / "evidence.md").write_bytes(b"# stale\n")
    elif damage == "truncated":
        (directory / "raw/operation-budget.json.gz").write_bytes(b"bad gzip")
    else:
        (directory / "evidence-manifest.json").unlink()
    before = archive_bytes(root)
    new_source = source.with_name("next-budget.json")
    new_source.write_bytes(original)
    with pytest.raises((ValueError, OSError, EOFError)):
        archive_report(root, new_source, None)
    assert archive_bytes(root) == before
    assert new_source.read_bytes() == original


@pytest.mark.parametrize("replace_number", [1, 2])
def test_metadata_failure_preserves_source_and_rejects_partial_archive(
    tmp_path, monkeypatch, replace_number
):
    root, source, original = setup_archive(tmp_path)
    new_source = source.with_name("next-budget.json")
    new_source.write_bytes(original)
    replace = CHECKS["replace_metadata"]
    calls = 0

    def interrupted(path, content):
        nonlocal calls
        calls += 1
        if calls == replace_number:
            raise OSError("injected metadata failure")
        replace(path, content)

    monkeypatch.setitem(archive_report.__globals__, "replace_metadata", interrupted)
    with pytest.raises(OSError, match="injected"):
        archive_report(root, new_source, None)
    assert source.read_bytes() == original
    assert new_source.read_bytes() == original
    with pytest.raises(ValueError, match="unregistered|stale"):
        verify(root)


@pytest.mark.parametrize("budget", ["archive", "report"])
@pytest.mark.parametrize("remaining", [0, 1])
def test_unpack_respects_remaining_total_budget_even_if_metadata_understates_bytes(
    tmp_path, budget, remaining
):
    root, _, _ = setup_archive(tmp_path)
    directory = root / "docs/research"
    item = CHECKS["catalog"](directory)[0]
    options = {f"{budget}_budget": remaining}
    with pytest.raises(ValueError, match="size limit"):
        CHECKS["unpack"](directory, item, **options)


@pytest.mark.parametrize("remaining", [0, 1, 17, 8192, 16384])
def test_unpack_bounds_actual_gzip_decoding_to_remaining_budget_plus_one(
    tmp_path, monkeypatch, remaining
):
    root, _, _ = setup_archive(
        tmp_path,
        {"runs": [{"outcome": "ok", "elapsed_ms": 1}], "padding": "x" * 32768},
    )
    directory = root / "docs/research"
    item = CHECKS["catalog"](directory)[0]
    original_read = gzip._GzipReader.read
    produced = 0

    def measured_read(reader, size=-1):
        nonlocal produced
        block = original_read(reader, size)
        produced += len(block)
        return block

    monkeypatch.setattr(gzip._GzipReader, "read", measured_read)
    with pytest.raises(ValueError, match="decompressed evidence size limit"):
        CHECKS["unpack"](directory, item, report_budget=remaining)
    assert produced == remaining + 1


@pytest.mark.parametrize("remaining", [0, 1, 17, 4096, 8192])
def test_unpack_bounds_actual_file_reads_to_remaining_gzip_budget_plus_one(
    tmp_path, monkeypatch, remaining
):
    root, _, _ = setup_archive(tmp_path)
    directory = root / "docs/research"
    item = CHECKS["catalog"](directory)[0]
    packed = directory / "raw/operation-budget.json.gz"
    packed.write_bytes(bytes(range(256)) * 128)
    original_open = Path.open
    consumed = 0

    class MeasuredFile(io.FileIO):
        def read(self, size=-1):
            nonlocal consumed
            block = super().read(size)
            consumed += len(block)
            return block

    def measured_open(path, mode="r", *args, **kwargs):
        if path == packed and mode == "rb":
            raw = MeasuredFile(path, "rb")
            return raw if kwargs.get("buffering") == 0 else io.BufferedReader(raw)
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", measured_open)
    with pytest.raises(ValueError, match="evidence size limit"):
        CHECKS["unpack"](directory, item, archive_budget=remaining)
    assert consumed == remaining + 1


def test_bounded_file_reader_completes_valid_short_reads(tmp_path, monkeypatch):
    content = b'{"runs":[{"outcome":"ok"}]}'
    source = tmp_path / "report.json"
    source.write_bytes(content)

    class ShortFile(io.FileIO):
        def read(self, size=-1):
            return super().read(min(size, 3))

    def short_open(path, mode="r", *args, **kwargs):
        assert mode == "rb"
        assert kwargs == {"buffering": 0}
        return ShortFile(path, mode)

    monkeypatch.setattr(Path, "open", short_open)
    assert CHECKS["read_bounded"](source, len(content)) == content


def test_archive_gzip_write_failure_preserves_source_and_is_not_success(tmp_path, monkeypatch):
    root, source, original = setup_archive(tmp_path)
    new_source = source.with_name("next-budget.json")
    new_source.write_bytes(original)
    original_open = Path.open

    class FailedWrite:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def write(self, content):
            raise OSError("injected archive write failure")

    def failing_open(path, *args, **kwargs):
        if path.name == "next-budget.json.gz" and args == ("xb",):
            with original_open(path, "xb") as stream:
                stream.write(b"partial")
            return FailedWrite()
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)
    with pytest.raises(OSError, match="injected"):
        archive_report(root, new_source, None)
    assert new_source.read_bytes() == original
    assert source.read_bytes() == original
    with pytest.raises(ValueError, match="unregistered"):
        verify(root)


def test_archive_accepts_the_producers_standalone_startup_comparison_null(tmp_path):
    report = {
        "schema_version": 2,
        "comparison": None,
        "measurements": {
            "help": {
                "warm_samples_ms": [10] * 30,
                "warm_p95_ms": 10,
                "target_ms": 500,
                "passed": True,
            }
        },
    }
    root, _, original = setup_archive(tmp_path, report)
    assert verify(root) == 1
    manifest = json.loads((root / "docs/research/evidence-manifest.json").read_bytes())
    metrics = manifest["entries"][0]["summary"]["measurements"]
    assert list(metrics) == ["candidate/help"]
    assert metrics["candidate/help"]["passed"] is True
    packed = root / "docs/research/raw/operation-budget.json.gz"
    assert gzip.decompress(packed.read_bytes()) == original


@pytest.mark.parametrize(
    "location", [".local", "src", "docs/analysis/private", "docs/research", "outside"]
)
def test_archive_rejects_unrelated_inputs_before_creating_evidence(tmp_path, location):
    root = tmp_path / "repo"
    (root / "docs/research").mkdir(parents=True)
    parent = tmp_path / "outside" if location == "outside" else root / location
    parent.mkdir(parents=True, exist_ok=True)
    source = parent / "report.json"
    content = b'{"runs":[{"outcome":"ok","elapsed_ms":1}]}'
    source.write_bytes(content)
    with pytest.raises(ValueError, match="input must be directly inside"):
        archive_report(root, source, None)
    assert source.read_bytes() == content
    assert not (root / "docs/research/raw").exists()
    assert not (root / "docs/research/evidence-manifest.json").exists()


@pytest.mark.parametrize("kind", ["directory-link", "file-link", "traversal"])
def test_allowed_input_locations_do_not_allow_symlink_or_traversal_escape(tmp_path, kind):
    root = tmp_path / "repo"
    (root / "docs/research").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    retained = outside / "report.json"
    content = b'{"runs":[{"outcome":"ok","elapsed_ms":1}]}'
    retained.write_bytes(content)
    if kind == "directory-link":
        (root / "dist").symlink_to(outside)
        source = root / "dist/report.json"
    else:
        (root / "dist").mkdir()
        source = root / "dist/report.json"
        if kind == "file-link":
            source.symlink_to(retained)
        else:
            source = root / "dist/../../outside/report.json"
    with pytest.raises(ValueError):
        archive_report(root, source, None)
    assert retained.read_bytes() == content
    assert list((root / "docs/research").iterdir()) == []
