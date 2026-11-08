"""Source-bound download reference gate: accepted M5 evidence of the current bytes only.

The reports are the harness's own synthetic records turned into an Apple M5 Max record: they are
no observed performance, and the "current" source map and frozen lock are stand-ins the gate is
compared against. Every rejection below names the gate that must refuse it.
"""

import base64
import copy
import gzip
import hashlib
import json
import runpy
import sys
from functools import cache
from pathlib import Path

import pytest

from tests.contracts.test_download_evidence import LABELS, build, rss
from tests.contracts.test_installation_evidence import receipt as installation
from tests.fixtures.upload_report import report as upload_report

pytestmark = pytest.mark.usefixtures("evidence_publication_context")

ROOT = Path(__file__).resolve().parents[2]
RUN_PATH = runpy.run_path
NAME = "p02-3-reference-download-1.json"
M5 = {"cpu": "Apple M5 Max", "disk_type": "internal SSD/APFS"}
ACCEPTED = "requires an accepted run of twelve measurements"
CURRENT = "download reference differs from complete current source bytes"
LOCK = "download reference runtime differs from current frozen lock"
HOST = "download proof does not declare configured M5 reference runtime"


@pytest.fixture(scope="module")
def evidence():
    return runpy.run_path(str(ROOT / "scripts/download_evidence.py"))


@pytest.fixture(scope="module")
def checks():
    return runpy.run_path(str(ROOT / "scripts/research_evidence.py"))


def reference(evidence, labels=LABELS, samples=3, *, before=None, after=None):
    """A harness record as the M5 reference host would have written it.

    ``before`` edits the Linux-shaped record (whose helpers speak KiB) ahead of the conversion to
    Darwin units; ``after`` edits the converted record.
    """
    report = build(evidence, labels, samples)
    if before is not None:
        before(report)
    report["environment"] = dict(M5)
    for row in report["runs"]:
        client = row["client"]
        client["runtime"].update(os="macOS-27.0.1-synthetic", machine="arm64")
        client["rss_native_unit"] = "bytes"
        client["baseline_rss_method"] = "darwin.MACH_TASK_BASIC_INFO.resident_size"
        for prefix in ("baseline", "pretransfer_peak", "peak"):
            client[prefix + "_rss_native"] = client[prefix + "_rss_bytes"]
        del client["baseline_rss_pages"], client["rss_page_bytes"]
    if after is not None:
        after(report)
    return report


def not_accepted(evidence, report):
    """Settle the report's own flags the way an honest producer's recomputation would."""
    report["growth"] = evidence["growth"](report["runs"])
    report["passed"] = report["accepted"] = False


def slow_run(evidence):
    def edit(report):
        row = report["runs"][0]
        row["client"]["elapsed_seconds"] = 901  # past the 900 s window: a measured failure
        row["passed"] = False
        not_accepted(evidence, report)

    return edit


def growing(evidence):
    def edit(report):
        for row in report["runs"]:
            if row["label"] == "1024":
                rss(row["client"], 21)  # U = 21 MiB against L = 0 of the smaller sizes: G > 8 MiB
        not_accepted(evidence, report)

    return edit


def one_run_other_machine(evidence):
    def edit(report):
        report["runs"][5]["client"]["runtime"]["machine"] = "x86_64"
        not_accepted(evidence, report)

    return edit


def every_runtime(**fields):
    def edit(report):
        for row in report["runs"]:
            row["client"]["runtime"].update(fields)

    return edit


def environment(**fields):
    return lambda report: report["environment"].update(fields)


def archive(checks, root, report, name=NAME):
    (root / "dist").mkdir(parents=True, exist_ok=True)
    (root / "docs/research").mkdir(parents=True, exist_ok=True)
    source = root / "dist" / name
    source.write_bytes(checks["encode"](report))
    checks["archive_report"](root, source, None)
    return source


@cache
def loaded(path):
    return RUN_PATH(path)


def current_bytes(
    monkeypatch, report, *, source=None, lock=None, base="source_before", accept=False
):
    """Make the gate's idea of the current checkout the report's own, unless said otherwise.

    ``accept`` replaces the verifier's summary by an accepting one: the gate's own comparisons are
    then the only thing between a record and a reference.
    """
    current = copy.deepcopy(report["provenance"][base])
    locked = copy.deepcopy(report["provenance"]["locked_runtime"])
    if source is not None:
        source(current["source_sha256"])
    if lock is not None:
        lock(locked)

    def load(path, *args, **kwargs):
        result = dict(loaded(str(path)))
        if Path(path).name == "download_evidence.py":
            if accept:
                result["summarize_report"] = lambda value: {
                    "kind": "download-budget",
                    "passed": True,
                    "accepted": True,
                }
            result["source"] = lambda root: current
            result["STREAM"] = {**result["STREAM"], "locked_runtime": lambda root: locked}
        return result

    monkeypatch.setattr(runpy, "run_path", load)


def stale(key):
    return lambda current: current.update({key: "9" * 64})


def removed(key):
    return lambda current: current.pop(key)


def files_under(directory):
    return {
        str(path.relative_to(directory)): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def test_the_accepted_m5_record_of_the_current_bytes_is_the_only_reference(
    tmp_path, monkeypatch, checks, evidence
):
    report = reference(evidence)
    current_bytes(monkeypatch, report)
    archive(checks, tmp_path, report)
    before = files_under(tmp_path / "docs/research")
    assert checks["verify_download_reference"](tmp_path, NAME) == {
        "name": NAME,
        "source_commit": "a" * 40,
        "kind": "download-budget",
        "cases": 12,
        "partial": False,
        "passed": True,
        "accepted": True,
        "growth": {"span_upper_bound_bytes": 4_194_304, "passed": True},
        "max_elapsed_seconds": 10.0,
        "max_extra_rss_upper_bound_bytes": 4_194_304,
    }
    assert files_under(tmp_path / "docs/research") == before  # verification writes nothing


# (the record builder, an edit of the current source map, the gate that must refuse it)
DAMAGE = {
    # --- not an accepted run of twelve measurements ---
    "failed_run": (lambda e: reference(e, before=slow_run(e)), None, ACCEPTED),
    "failed_growth": (lambda e: reference(e, before=growing(e)), None, ACCEPTED),
    "one_run_other_machine": (
        lambda e: reference(e, after=one_run_other_machine(e)),
        None,
        ACCEPTED,
    ),
    "smoke_samples": (lambda e: reference(e, LABELS, 2), None, ACCEPTED),
    "smoke_labels": (lambda e: reference(e, ("16", "256", "1024")), None, ACCEPTED),
    "smoke_one_size": (lambda e: reference(e, ("16", "resume"), 1), None, ACCEPTED),
    # --- not the declared M5 reference ---
    "host": (lambda e: reference(e, after=environment(cpu="synthetic")), None, HOST),
    "disk": (lambda e: reference(e, after=environment(disk_type="SSD")), None, HOST),
    "machine": (lambda e: reference(e, after=every_runtime(machine="x86_64")), None, HOST),
    "os": (lambda e: reference(e, after=every_runtime(os="macOS-26.4-synthetic")), None, HOST),
    "os_near_miss": (
        lambda e: reference(e, after=every_runtime(os="macOS-27.0.10-synthetic")),
        None,
        HOST,
    ),
    "python": (
        lambda e: reference(e, after=every_runtime(python="3.12.1 synthetic fixture")),
        None,
        HOST,
    ),
    "python_near_miss": (
        lambda e: reference(e, after=every_runtime(python="3.110.2 synthetic")),
        None,
        HOST,
    ),
    # --- not the current checkout ---
    "stale_product": (reference, stale("src/yorunge/__init__.py"), CURRENT),
    "stale_controller": (reference, stale("scripts/benchmark-download.py"), CURRENT),
    "stale_fixture": (reference, stale("tests/fixtures/download_native_server.py"), CURRENT),
    "foreign_extra_file": (reference, stale("scripts/not-in-the-measured-checkout.py"), CURRENT),
    "foreign_missing_file": (reference, removed("tests/fixtures/model_network.py"), CURRENT),
}
LOCK_DAMAGE = {
    "lock_changed": lambda locked: locked.update({"httpx": "0.28.2"}),
    "lock_added": lambda locked: locked.update({"extra-package": "1.0"}),
    "lock_removed": lambda locked: locked.pop("httpx"),
}


@pytest.mark.parametrize("kind", sorted(DAMAGE))
def test_every_gate_refuses_what_it_is_there_for(tmp_path, monkeypatch, checks, evidence, kind):
    build_report, source, message = DAMAGE[kind]
    report = build_report(evidence)
    current_bytes(monkeypatch, report, source=source)
    archive(checks, tmp_path, report)
    with pytest.raises(ValueError, match=message):
        checks["verify_download_reference"](tmp_path, NAME)


def test_a_smoke_subset_that_passed_every_rule_it_has_is_still_no_reference(
    tmp_path, monkeypatch, checks, evidence
):
    report = reference(evidence, LABELS, 2)
    summary = evidence["summarize_report"](report)
    assert (summary["passed"], summary["partial"], summary["accepted"]) == (True, True, False)
    current_bytes(monkeypatch, report)
    archive(checks, tmp_path, report)
    with pytest.raises(ValueError, match=ACCEPTED):
        checks["verify_download_reference"](tmp_path, NAME)


@pytest.mark.parametrize("changed", ["source_before", "source_after"])
def test_both_source_snapshots_are_compared_even_if_the_verifier_would_accept(
    tmp_path, monkeypatch, checks, evidence, changed
):
    """The gate does not lean on the verifier's own before-equals-after rule."""
    report = reference(evidence)
    report["provenance"][changed]["source_sha256"]["src/yorunge/__init__.py"] = "9" * 64
    other = "source_after" if changed == "source_before" else "source_before"
    current_bytes(monkeypatch, report, base=other, accept=True)
    archive(checks, tmp_path, report)
    with pytest.raises(ValueError, match=CURRENT):
        checks["verify_download_reference"](tmp_path, NAME)


@pytest.mark.parametrize("kind", sorted(LOCK_DAMAGE))
def test_a_changed_frozen_lock_is_refused(tmp_path, monkeypatch, checks, evidence, kind):
    report = reference(evidence)
    current_bytes(monkeypatch, report, lock=LOCK_DAMAGE[kind])
    archive(checks, tmp_path, report)
    with pytest.raises(ValueError, match=LOCK):
        checks["verify_download_reference"](tmp_path, NAME)


def file_of(name, raw):
    return {
        "name": name,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "content_base64": base64.b64encode(raw).decode("ascii"),
    }


def rejected(kind):
    return {
        "schema_version": 1,
        "report_kind": f"rejected_{kind}_evidence_v1",
        "source_commit": "a" * 40,
        "run_url": None,
        "rejection_reason": "invalid_evidence",
        "files": [file_of("stdout.json", b"{}\n")],
    }


def foreign(kind, evidence):
    upload = runpy.run_path(str(ROOT / "scripts/upload_evidence.py"))
    return {
        "installation": installation,
        "upload": lambda: upload_report(upload["METHOD"], upload["LIMITS"]),
        "rejected_download": lambda: rejected("download"),
        "rejected_upload": lambda: rejected("upload"),
    }[kind]()


@pytest.mark.parametrize("kind", ["installation", "upload", "rejected_download", "rejected_upload"])
def test_another_kind_of_evidence_is_no_download_reference(
    tmp_path, monkeypatch, checks, evidence, kind
):
    current_bytes(monkeypatch, reference(evidence))
    archive(checks, tmp_path, foreign(kind, evidence))
    with pytest.raises(ValueError, match="invalid download measurement fields"):
        checks["verify_download_reference"](tmp_path, NAME)


def test_a_download_record_with_a_foreign_field_cannot_even_be_archived(tmp_path, checks, evidence):
    with pytest.raises(ValueError, match="invalid download measurement fields"):
        archive(checks, tmp_path, {**reference(evidence), "extra": "field"})
    assert list((tmp_path / "docs/research").iterdir()) == []


# --- the archive itself must verify, whatever else is true ---------------------------------------


@pytest.mark.parametrize(
    "tamper",
    [
        "summary_changed",
        "raw_replaced",
        "raw_missing",
        "raw_truncated",
        "index_stale",
        "unregistered_raw",
        "expanded_json",
        "other_entry_damaged",
    ],
)
def test_a_tampered_archive_is_never_a_reference(tmp_path, monkeypatch, checks, evidence, tamper):
    report = reference(evidence)
    current_bytes(monkeypatch, report)
    archive(checks, tmp_path, report)
    directory = tmp_path / "docs/research"
    raw = directory / "raw" / f"{NAME}.gz"
    if tamper == "summary_changed":
        manifest = json.loads((directory / "evidence-manifest.json").read_bytes())
        manifest["entries"][0]["summary"]["accepted"] = False
        (directory / "evidence-manifest.json").write_bytes(checks["encode"](manifest))
    elif tamper == "raw_replaced":
        other = copy.deepcopy(report)
        other["controller_pid"] += 1
        raw.write_bytes(gzip.compress(checks["encode"](other), mtime=0))
    elif tamper == "raw_missing":
        raw.unlink()
    elif tamper == "raw_truncated":
        raw.write_bytes(raw.read_bytes()[:-9])
    elif tamper == "index_stale":
        (directory / "evidence.md").write_text("# stale\n")
    elif tamper == "unregistered_raw":
        (directory / "raw/unregistered.json.gz").write_bytes(gzip.compress(b"{}", mtime=0))
    elif tamper == "expanded_json":
        (directory / NAME).write_bytes(checks["encode"](report))
    else:
        # The reference entry itself is intact; only a neighbour is damaged. Integrity is the
        # whole catalog's, so the reference must fail too.
        archive(checks, tmp_path, installation(), name="a-neighbour.json")
        (directory / "raw/a-neighbour.json.gz").write_bytes(b"not a gzip stream")
    with pytest.raises((ValueError, OSError, EOFError)):
        checks["verify_download_reference"](tmp_path, NAME)


def test_a_reference_is_found_among_other_entries_by_its_exact_name(
    tmp_path, monkeypatch, checks, evidence
):
    report = reference(evidence)
    current_bytes(monkeypatch, report)
    archive(checks, tmp_path, installation(), name="a-neighbour.json")
    archive(checks, tmp_path, report)
    archive(checks, tmp_path, installation(), name="z-neighbour.json")
    assert checks["verify_download_reference"](tmp_path, NAME)["accepted"] is True
    for name in ("a-neighbour.json", "z-neighbour.json"):
        with pytest.raises(ValueError, match="invalid download measurement fields"):
            checks["verify_download_reference"](tmp_path, name)
    for name in ("p02-3-reference-download-2.json", NAME.replace(".json", "-x.json")):
        with pytest.raises(ValueError, match="unknown download reference evidence name"):
            checks["verify_download_reference"](tmp_path, name)


@pytest.mark.parametrize(
    "name",
    ["", "../a.json", "A.json", "a/b.json", "a.JSON", "a.json\n", ".json", "-a.json", "a b.json"],
)
def test_an_invalid_name_is_refused_before_the_archive_is_read(tmp_path, checks, name):
    with pytest.raises(ValueError, match="invalid download reference evidence name"):
        checks["verify_download_reference"](tmp_path, name)  # nothing exists under tmp_path


def test_a_root_without_an_evidence_catalog_has_no_reference(tmp_path, checks):
    (tmp_path / "docs/research").mkdir(parents=True)
    with pytest.raises(ValueError, match="regular evidence file"):
        checks["verify_download_reference"](tmp_path, NAME)


# --- the real checkout ---------------------------------------------------------------------------


def test_the_current_source_map_binds_the_gate_the_retention_and_the_artifact_list(evidence):
    bound = evidence["source"](ROOT)["source_sha256"]
    for name in (
        "scripts/research_evidence.py",
        "scripts/download_evidence.py",
        "scripts/download_diagnostic.py",
        "scripts/benchmark-download.py",
        "scripts/evidence_privacy.py",
        "scripts/evidence-artifact-paths.txt",
        "tests/contracts/test_download_budget_reference.py",
        "tests/contracts/test_download_diagnostic.py",
        ".github/workflows/checks.yml",
    ):
        assert name in bound


# --- the command line ----------------------------------------------------------------------------


def cli(monkeypatch, checks, function, *arguments):
    monkeypatch.setitem(checks["main"].__globals__, "verify_download_reference", function)
    monkeypatch.setattr(sys, "argv", ["research_evidence.py", *arguments])
    return checks["main"]


def test_the_cli_action_prints_the_summary_of_the_named_reference(monkeypatch, checks, capsys):
    calls = []

    def verified(root, name):
        calls.append((root, name))
        return {"name": name, "accepted": True, "cases": 12}

    main = cli(monkeypatch, checks, verified, "verify-download-reference", NAME)
    assert main() == 0
    assert calls == [(ROOT, NAME)]
    assert json.loads(capsys.readouterr().out) == {"name": NAME, "accepted": True, "cases": 12}


def test_the_cli_action_fails_closed_on_a_refused_reference(monkeypatch, checks, capsys):
    def refused(root, name):
        raise ValueError(CURRENT)

    main = cli(monkeypatch, checks, refused, "verify-download-reference", NAME)
    with pytest.raises(SystemExit) as stop:
        main()
    printed = capsys.readouterr()
    assert stop.value.code == 1 and printed.out == ""
    assert "Evidence check failed" in printed.err
    assert "current source bytes" not in printed.err  # a closed message, no interpolated detail


def test_the_cli_action_needs_a_name(monkeypatch, checks):
    main = cli(monkeypatch, checks, lambda root, name: {}, "verify-download-reference")
    with pytest.raises(SystemExit) as stop:
        main()
    assert stop.value.code == 2
