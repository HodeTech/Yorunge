"""Lossless bounded retention of a failed download measurement; never an acceptance receipt.

The workspace below is the layout one controller run leaves, each file filled with bytes of its own;
the decoys beside it (payloads, state, configuration, keys, another measurement's names) must never
be taken. Nothing here is observed performance.
"""

import base64
import copy
import gzip
import hashlib
import json
import runpy
import sys
from pathlib import Path

import pytest

from tests.fixtures.evidence_publication import synthetic_context

pytestmark = pytest.mark.usefixtures("evidence_publication_context")

ROOT = Path(__file__).resolve().parents[2]
COMMIT = "a" * 40
RUN_URL = "https://github.com/HodeTech/Yorunge/actions/runs/123"
LABELS = ("16", "256", "1024", "resume")
SERVERS = ("warm-server", "measured-server")
ROOT_NAMES = [
    "source-manifest.json",
    "source-before.json",
    "source-after.json",
    "controller-error.json",
    "metadata-stdout.json",
    "metadata-stderr.txt",
    "stdout.json",
    "stderr.txt",
]
DECOYS = [
    "credentials.json",
    "oracle.json",  # the upload measurement's file: the download oracle is arithmetic
    "source.json",
    "cert/ca.pem",
    "cert/key.pem",
    "warm-server/stdout.json",  # servers live inside a run directory only
    "measured-server/ready.json",
    "16-1/measured/config.toml",
    "16-1/measured/state/state.sqlite3",
    "16-1/measured/out/weights.onnx",
    "16-1/warm/config.toml",
    "16-1/client-stdout.json.bak",
    "16-1/extra/stdout.json",
    "16-1/warm-server/body.bin",
    "16-4/client-stdout.json",
    "capacity-1/client-stdout.json",
    "resume-1/measured-server/nested/stdout.json",
]


@pytest.fixture(scope="module")
def helper():
    return runpy.run_path(str(ROOT / "scripts/download_diagnostic.py"))


def run_names(label, sample):
    base = f"{label}-{sample}"
    names = [f"{base}/client-stdout.json", f"{base}/client-stderr.txt"]
    for server in SERVERS:
        names += [f"{base}/{server}/{leaf}" for leaf in ("stdout.json", "stderr.txt", "ready.json")]
    return names


def layout(labels=LABELS, samples=(1, 2, 3), root_names=ROOT_NAMES):
    return list(root_names) + [
        name for label in labels for sample in samples for name in run_names(label, sample)
    ]


def content(name):
    if name.endswith(".json"):
        return json.dumps({"file": name}).encode() + b"\n"
    return f"text of {name}\n".encode()


def write(workspace, name, data=None):
    path = workspace / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content(name) if data is None else data)
    return path


def make_workspace(tmp_path, names=None, decoys=True):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    for name in layout() if names is None else names:
        write(workspace, name)
    for name in DECOYS if decoys else ():
        write(workspace, name, b"must-not-archive\n")
    return workspace


def make_root(tmp_path):
    root = tmp_path / "repo"
    (root / "dist").mkdir(parents=True)
    (root / "docs/research").mkdir(parents=True)
    return root


def snapshot(directory):
    """Every regular file below ``directory`` by relative name; symlinks are not followed."""
    return {
        str(path.relative_to(directory)): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


def file_item(name, raw):
    return {
        "name": name,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "content_base64": base64.b64encode(raw).decode("ascii"),
    }


def value_of(name="stdout.json", raw=b"{}\n"):
    return {
        "schema_version": 1,
        "report_kind": "rejected_download_evidence_v1",
        "source_commit": COMMIT,
        "run_url": None,
        "rejection_reason": "invalid_evidence",
        "files": [file_item(name, raw)],
    }


def do_retain(helper, tmp_path, workspace, root=None, **extra):
    root = make_root(tmp_path) if root is None else root
    arguments = [root, workspace, "failed-download.json", COMMIT, "invalid_evidence"]
    return root, helper["retain"](*arguments, **extra)


# --- the allowlist is the layout the controller leaves --------------------------------------------


def test_every_name_of_the_layout_is_allowed_and_nothing_else_is(helper):
    names = layout()
    assert len(names) == 8 + 12 * 8
    assert all(helper["allowed"](name) for name in names)
    refused = [
        *DECOYS,
        "",
        ".",  # no parts at all: the only name that reaches the run-directory test without one
        "/",
        "/stdout.json",
        "./stdout.json",
        "stdout.json/",
        "../stdout.json",
        "16-1/../stdout.json",
        "16-1//client-stdout.json",
        "16-1/client-stdout.json/",
        "16-1/client-stdout.json/x",
        "16-1\\client-stdout.json",
        "16-1/warm-server",
        "16-1/warm-server/",
        "16-1/warm-server/stdout.json/x",
        "16-1/measured-server/../warm-server/stdout.json",
        "16-1/other-server/stdout.json",
        "16-1/server/stdout.json",
        "16-1/warm-server/client-stdout.json",
        "16-1/client-stdout.json.gz",
        "16-1/ready.json",
        "STDOUT.JSON",
        " stdout.json",
        "stdout.json ",
        "stdout.json\n",
        "16-0/client-stdout.json",
        "16-4/client-stdout.json",
        "16-01/client-stdout.json",
        "016-1/client-stdout.json",
        "16-10/client-stdout.json",
        "16-1 /client-stdout.json",
        "16-1\n/client-stdout.json",
        "１６-1/client-stdout.json",  # full-width digits
        "2048-1/client-stdout.json",
        "Resume-1/client-stdout.json",
        "capacity-1/client-stdout.json",
    ]
    assert not any(helper["allowed"](name) for name in refused)


def test_labels_samples_names_limits_and_reasons_are_the_harness_and_the_upload_ones(helper):
    evidence = runpy.run_path(str(ROOT / "scripts/download_evidence.py"))
    upload = runpy.run_path(str(ROOT / "scripts/upload_diagnostic.py"))
    assert helper["LABELS"] == evidence["LABELS"] == tuple(LABELS)
    assert helper["SAMPLES"] == tuple(range(1, evidence["SAMPLES"] + 1))
    assert all(
        helper["RUN_NAME"].fullmatch(f"{label}-{sample}")
        for label in helper["LABELS"]
        for sample in helper["SAMPLES"]
    )
    assert (helper["MAX_FILE"], helper["MAX_TOTAL"], helper["MAX_FILES"]) == (
        2_097_152,
        8_388_608,
        128,
    )
    for key in ("MAX_FILE", "MAX_TOTAL", "MAX_FILES", "REASONS", "CLIENT_FILES", "SERVER_FILES"):
        assert helper[key] == upload[key]
    assert helper["ROOT_FILES"] == tuple(ROOT_NAMES)
    assert helper["SERVERS"] == SERVERS


def test_the_allowlist_is_exactly_what_a_real_failed_worker_leaves(tmp_path, helper):
    """The development interpreter is no installed runtime: the worker fails before any network."""
    from tests.fixtures.http_server import certificate

    driver = runpy.run_path(str(ROOT / "scripts/benchmark-download.py"))
    certificates = certificate(tmp_path / "cert", names=("api.ssyz.org.tr",))
    receipt = tmp_path / "source-manifest.json"
    receipt.write_text(
        json.dumps({"source_sha256": {}, "locked_runtime": {}, "metadata_sha256": {}})
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    with pytest.raises(ValueError, match="worker failed"):
        driver["measure_one"](Path(sys.executable), workspace, receipt, certificates, "16", 1)
    payload = write(workspace, "16-1/measured/out/weights.onnx", b"a wrong payload kept on disk")
    on_disk = sorted(
        path.relative_to(workspace).as_posix()
        for path in workspace.rglob("*")
        if path.is_file() and path != payload
    )
    assert on_disk == sorted(run_names("16", 1))
    found = helper["paths"](workspace)
    assert [path.relative_to(workspace).as_posix() for path in found] == run_names("16", 1)
    # Every original of the real layout is attachable, and the closed report over them is valid.
    files = [helper["attachment"](path, workspace) for path in found]
    assert [item["name"] for item in files] == run_names("16", 1)
    value = {**value_of(), "files": files}
    assert helper["summarize"](value)["files"] == 8
    assert payload.read_bytes() == b"a wrong payload kept on disk"


# --- retention is lossless -----------------------------------------------------------------------


def test_a_complete_workspace_is_retained_losslessly_and_only_the_allowed_files(tmp_path, helper):
    workspace = make_workspace(tmp_path)
    before = snapshot(workspace)
    root, output = do_retain(helper, tmp_path, workspace, run_url=RUN_URL)
    assert output == root / "dist/failed-download.json"
    value = helper["CHECKS"]["decode"](output.read_bytes())
    assert output.read_bytes() == helper["CHECKS"]["encode"](value)  # canonical, newline included
    assert set(value) == {
        "schema_version",
        "report_kind",
        "source_commit",
        "run_url",
        "rejection_reason",
        "files",
    }
    assert (value["schema_version"], value["report_kind"]) == (1, "rejected_download_evidence_v1")
    assert (value["source_commit"], value["run_url"]) == (COMMIT, RUN_URL)
    assert value["rejection_reason"] == "invalid_evidence"
    # Root files first in their fixed order, then label by label and sample by sample.
    assert [item["name"] for item in value["files"]] == layout()
    for item in value["files"]:
        original = before[item["name"]]
        assert base64.b64decode(item["content_base64"], validate=True) == original
        assert item["bytes"] == len(original)
        assert item["sha256"] == hashlib.sha256(original).hexdigest()
    expected = {
        "kind": "rejected-download",
        "accepted": False,
        "diagnostic_only": True,
        "files": 104,
        "original_bytes": sum(len(before[name]) for name in layout()),
    }
    assert helper["summarize"](value) == expected
    assert helper["CHECKS"]["typed_summary"](value) == expected
    assert snapshot(workspace) == before  # nothing deleted, moved or rewritten
    assert helper["CHECKS"]["verify"](root) == 1
    catalog = json.loads((root / "docs/research/evidence-manifest.json").read_bytes())
    assert [item["name"] for item in catalog["entries"]] == ["failed-download.json"]
    assert catalog["entries"][0]["summary"] == {
        "source_commit": COMMIT,
        "diagnostic_only": True,
        **expected,
    }
    archived = gzip.decompress((root / "docs/research/raw/failed-download.json.gz").read_bytes())
    assert archived == output.read_bytes()


def test_a_smoke_workspace_keeps_only_what_exists_in_order(tmp_path, helper):
    names = ["source-before.json", "controller-error.json", *run_names("resume", 2)]
    workspace = make_workspace(tmp_path, names=names)
    _, output = do_retain(helper, tmp_path, workspace)
    stored = helper["CHECKS"]["decode"](output.read_bytes())["files"]
    assert [item["name"] for item in stored] == names
    assert helper["paths"](tmp_path / "nowhere") == []


def test_odd_but_legal_bytes_survive_the_round_trip_unchanged(tmp_path, helper):
    workspace = make_workspace(tmp_path, names=[], decoys=False)
    originals = {
        "stdout.json": b'{ "failed" : true }  \n\n',  # valid JSON that is not the canonical bytes
        "stderr.txt": "line\r\nçöğ \x00 \x1b[0m\n".encode(),  # CRLF, non-ASCII, NUL, a control code
        "16-1/client-stderr.txt": b"",  # empty
        "16-1/client-stdout.json": b'{"a":1e0}',
    }
    for name, raw in originals.items():
        write(workspace, name, raw)
    root, output = do_retain(helper, tmp_path, workspace)
    stored = helper["CHECKS"]["decode"](output.read_bytes())["files"]
    assert {item["name"]: base64.b64decode(item["content_base64"]) for item in stored} == originals
    directory = root / "docs/research"
    item = helper["CHECKS"]["catalog"](directory)[0]
    assert helper["CHECKS"]["unpack"](directory, item) == output.read_bytes()


def test_run_url_is_recorded_or_null_and_the_reasons_are_the_three_closed_ones(tmp_path, helper):
    workspace = make_workspace(tmp_path, names=["stdout.json"], decoys=False)
    root = make_root(tmp_path)
    for reason in helper["REASONS"]:
        name = reason.replace("_", "-") + ".json"
        output = helper["retain"](root, workspace, name, COMMIT, reason, None)
        assert helper["CHECKS"]["decode"](output.read_bytes())["run_url"] is None
        assert helper["CHECKS"]["decode"](output.read_bytes())["rejection_reason"] == reason
    assert helper["REASONS"] == (
        "invalid_evidence",
        "interrupted_measurement",
        "unverified_measurement",
    )
    assert helper["CHECKS"]["verify"](root) == 3


def test_the_exact_byte_limits_are_accepted(tmp_path, helper):
    limit, total = helper["MAX_FILE"], helper["MAX_TOTAL"]
    text_files = [
        "stderr.txt",
        "metadata-stderr.txt",
        "16-1/client-stderr.txt",
        "16-1/warm-server/stderr.txt",
    ]
    assert limit * len(text_files) == total
    workspace = make_workspace(tmp_path, names=[], decoys=False)
    for name in text_files:
        write(workspace, name, b"x" * limit)  # four files of exactly 2 MiB: exactly 8 MiB
    _, output = do_retain(helper, tmp_path, workspace)
    value = helper["CHECKS"]["decode"](output.read_bytes())
    assert helper["summarize"](value)["original_bytes"] == total
    assert len(value["files"][0]["content_base64"]) == 4 * ((limit + 2) // 3)


@pytest.mark.parametrize("failure", ["one_file", "total"])
def test_a_byte_beyond_the_limits_keeps_the_originals_and_writes_nothing(tmp_path, helper, failure):
    limit = helper["MAX_FILE"]
    workspace = make_workspace(tmp_path, names=[], decoys=False)
    if failure == "one_file":
        write(workspace, "stderr.txt", b"x" * (limit + 1))
        match = "size limit|evidence size"
    else:
        for name in ("stderr.txt", "metadata-stderr.txt", "16-1/client-stderr.txt"):
            write(workspace, name, b"x" * limit)
        write(workspace, "16-1/warm-server/stderr.txt", b"x" * limit)
        write(workspace, "16-1/measured-server/stderr.txt", b"y")
        match = "total limit"
    before = snapshot(workspace)
    root = make_root(tmp_path)
    with pytest.raises(ValueError, match=match):
        helper["retain"](root, workspace, "failed-download.json", COMMIT, "invalid_evidence")
    assert snapshot(workspace) == before
    assert list((root / "dist").iterdir()) == []
    assert list((root / "docs/research").iterdir()) == []


def test_the_file_count_limit_is_checked_before_any_file_is_read(tmp_path, helper, monkeypatch):
    names = ["source-before.json", "source-after.json", "stdout.json"]
    workspace = make_workspace(tmp_path, names=names, decoys=False)
    write(workspace, "stdout.json", b"x" * (helper["MAX_FILE"] + 1))  # unreadable if it were read
    monkeypatch.setitem(helper["retain"].__globals__, "MAX_FILES", 2)
    root = make_root(tmp_path)
    with pytest.raises(ValueError, match="too many"):
        helper["retain"](root, workspace, "failed-download.json", COMMIT, "invalid_evidence")
    assert list((root / "dist").iterdir()) == []
    (workspace / "stdout.json").unlink()  # exactly the limit: allowed
    output = helper["retain"](root, workspace, "failed-download.json", COMMIT, "invalid_evidence")
    assert len(helper["CHECKS"]["decode"](output.read_bytes())["files"]) == 2


def test_the_file_count_limit_is_checked_at_its_exact_boundary_by_the_validator(
    helper, monkeypatch
):
    monkeypatch.setitem(helper["summarize"].__globals__, "MAX_FILES", 2)
    value = value_of("source-before.json", b"1")
    value["files"].append(file_item("source-after.json", b"2"))
    assert helper["summarize"](value)["files"] == 2
    value["files"].append(file_item("stdout.json", b"3"))
    with pytest.raises(ValueError, match="bounded original files"):
        helper["summarize"](value)


def test_the_total_limit_is_checked_at_its_exact_boundary(helper, monkeypatch):
    monkeypatch.setitem(helper["summarize"].__globals__, "MAX_TOTAL", 10)
    both = value_of("source-before.json", b"12345")
    both["files"].append(file_item("source-after.json", b"67890"))
    assert helper["summarize"](both)["original_bytes"] == 10
    both["files"][1] = file_item("source-after.json", b"678901")
    with pytest.raises(ValueError, match="total byte limit"):
        helper["summarize"](both)


# --- a lie about the originals is refused ---------------------------------------------------------


def first(value):
    return value["files"][0]


LIES = {
    "schema_bool": (lambda v: v.update(schema_version=True), "schema version"),
    "schema_two": (lambda v: v.update(schema_version=2), "schema version"),
    "schema_text": (lambda v: v.update(schema_version="1"), "schema version"),
    "kind_upload": (lambda v: v.update(report_kind="rejected_upload_evidence_v1"), "kind/reason"),
    "kind_budget": (lambda v: v.update(report_kind="download_budget_v1"), "kind/reason"),
    "reason_unknown": (lambda v: v.update(rejection_reason="bogus"), "kind/reason"),
    "reason_blank": (lambda v: v.update(rejection_reason=""), "kind/reason"),
    "commit_short": (lambda v: v.update(source_commit="a" * 39), "digest or identifier"),
    "commit_upper": (lambda v: v.update(source_commit="A" * 40), "digest or identifier"),
    "commit_null": (lambda v: v.update(source_commit=None), "digest or identifier"),
    "url_http": (
        lambda v: v.update(run_url="http://github.com/o/r/actions/runs/1"),
        "digest or identifier",
    ),
    "url_zero": (
        lambda v: v.update(run_url="https://github.com/o/r/actions/runs/0"),
        "digest or identifier",
    ),
    "url_number": (lambda v: v.update(run_url=7), "digest or identifier"),
    "extra_field": (lambda v: v.update(passed=True), "invalid rejected download fields"),
    "missing_field": (lambda v: v.pop("run_url"), "invalid rejected download fields"),
    "files_empty": (lambda v: v.update(files=[]), "bounded original files"),
    "files_mapping": (lambda v: v.update(files={}), "bounded original files"),
    "files_tuple": (lambda v: v.update(files=tuple(v["files"])), "bounded original files"),
    "file_extra": (lambda v: first(v).update(extra=1), "download diagnostic file fields"),
    "file_missing": (lambda v: first(v).pop("sha256"), "download diagnostic file fields"),
    "file_not_object": (lambda v: v.update(files=["stdout.json"]), "download diagnostic file"),
    "name_unknown": (lambda v: first(v).update(name="credentials.json"), "unknown download"),
    "name_upload": (
        lambda v: first(v).update(name="capacity-1/client-stdout.json"),
        "unknown download",
    ),
    "name_blank": (lambda v: first(v).update(name=""), "nonempty evidence text"),
    "name_number": (lambda v: first(v).update(name=5), "nonempty evidence text"),
    "duplicate": (lambda v: v["files"].append(copy.deepcopy(first(v))), "duplicate"),
    "bytes_bool": (lambda v: first(v).update(bytes=True), "integer measurement"),
    "bytes_float": (lambda v: first(v).update(bytes=3.0), "integer measurement"),
    "bytes_negative": (lambda v: first(v).update(bytes=-1), "integer measurement"),
    "bytes_mismatch": (lambda v: first(v).update(bytes=4), "bytes/hash mismatch"),
    "bytes_over_limit": (lambda v: first(v).update(bytes=2_097_153), "size limit"),
    "base64_invalid": (lambda v: first(v).update(content_base64="!"), "invalid download.*base64"),
    "base64_padding_missing": (
        lambda v: first(v).update(content_base64="e30"),
        "invalid download.*base64",
    ),
    "base64_number": (lambda v: first(v).update(content_base64=5), "size limit"),
    "base64_overlong": (
        lambda v: first(v).update(content_base64="A" * (4 * ((2_097_152 + 2) // 3) + 4)),
        "size limit",
    ),
    "hash_upper": (lambda v: first(v).update(sha256="A" * 64), "digest or identifier"),
    "hash_number": (lambda v: first(v).update(sha256=5), "digest or identifier"),
    "hash_wrong": (lambda v: first(v).update(sha256="0" * 64), "bytes/hash mismatch"),
}


@pytest.mark.parametrize("lie", sorted(LIES))
def test_a_diagnostic_cannot_lie_about_its_original_bytes(helper, lie):
    change, message = LIES[lie]
    value = value_of()
    change(value)
    with pytest.raises(ValueError, match=message):
        helper["summarize"](value)


def test_the_honest_value_is_the_baseline_of_every_lie(helper):
    assert helper["summarize"](value_of()) == {
        "kind": "rejected-download",
        "accepted": False,
        "diagnostic_only": True,
        "files": 1,
        "original_bytes": 3,
    }
    at_limit = value_of("stderr.txt", b"x" * helper["MAX_FILE"])
    assert helper["summarize"](at_limit)["original_bytes"] == helper["MAX_FILE"]
    with_url = {**value_of(), "run_url": RUN_URL}
    assert helper["summarize"](with_url)["files"] == 1


@pytest.mark.parametrize("kind", ["workspace", "ancestor"])
def test_paths_refuses_a_symlinked_workspace_or_ancestor_on_its_own(tmp_path, helper, kind):
    real = tmp_path / "real"
    write(real / "workspace", "stdout.json")
    (tmp_path / "ancestor-link").symlink_to(real)
    (tmp_path / "workspace-link").symlink_to(real / "workspace")
    target = tmp_path / "workspace-link"
    if kind == "ancestor":
        target = tmp_path / "ancestor-link" / "workspace"
    with pytest.raises(ValueError, match="without symlinks"):
        helper["paths"](target)
    assert helper["paths"](real / "workspace") == [real / "workspace" / "stdout.json"]


def test_attachment_reads_at_most_the_file_limit_and_never_through_a_symlinked_ancestor(
    tmp_path, helper
):
    workspace = tmp_path / "workspace"
    exact = write(workspace, "stderr.txt", b"x" * helper["MAX_FILE"])
    assert helper["attachment"](exact, workspace)["bytes"] == helper["MAX_FILE"]
    over = write(workspace, "metadata-stderr.txt", b"x" * (helper["MAX_FILE"] + 1))
    with pytest.raises(ValueError, match="size limit"):
        helper["attachment"](over, workspace)
    (tmp_path / "linked").symlink_to(workspace)
    with pytest.raises(ValueError, match="ancestors must not be symlinks"):
        helper["attachment"](tmp_path / "linked" / "stderr.txt", tmp_path / "linked")


# --- what cannot be retained fails loudly and preserves the originals -----------------------------


def damage(tmp_path, kind):
    """A workspace with one damaged place; returns the workspace path to hand to ``retain``."""
    workspace = make_workspace(tmp_path, names=["source-before.json", "stdout.json"], decoys=False)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    write(elsewhere, "client-stdout.json", b"not-followed")
    write(elsewhere, "stdout.json", b"not-followed")
    if kind == "file_symlink":
        (workspace / "stderr.txt").symlink_to(elsewhere / "stdout.json")
    elif kind == "dangling_symlink":
        (workspace / "stderr.txt").symlink_to(elsewhere / "missing")
    elif kind == "run_symlink":
        (workspace / "16-1").symlink_to(elsewhere)
    elif kind == "server_symlink":
        write(workspace, "16-1/client-stdout.json")
        (workspace / "16-1/warm-server").symlink_to(elsewhere)
    elif kind == "directory_as_file":
        (workspace / "stderr.txt").mkdir()
    elif kind == "workspace_symlink":
        link = tmp_path / "linked-workspace"
        link.symlink_to(workspace)
        return link
    elif kind == "parent_symlink":
        (tmp_path / "linked-parent").symlink_to(tmp_path)
        return tmp_path / "linked-parent" / "workspace"
    return workspace


@pytest.mark.parametrize(
    "kind",
    [
        "file_symlink",
        "dangling_symlink",
        "run_symlink",
        "server_symlink",
        "directory_as_file",
        "workspace_symlink",
        "parent_symlink",
    ],
)
def test_unarchivable_workspaces_fail_and_preserve_every_original(tmp_path, helper, kind):
    workspace = damage(tmp_path, kind)
    before = snapshot(tmp_path)
    root = make_root(tmp_path)
    with pytest.raises(ValueError):
        helper["retain"](root, workspace, "failed-download.json", COMMIT, "invalid_evidence")
    assert snapshot(tmp_path) == before  # the root added only empty directories
    assert list((root / "dist").iterdir()) == []
    assert list((root / "docs/research").iterdir()) == []


def test_a_symlinked_dist_is_never_written_through(tmp_path, helper):
    workspace = make_workspace(tmp_path, names=["stdout.json"], decoys=False)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    root = tmp_path / "repo"
    (root / "docs/research").mkdir(parents=True)
    (root / "dist").symlink_to(elsewhere)
    with pytest.raises(ValueError, match="must not use a symlink"):
        helper["retain"](root, workspace, "failed-download.json", COMMIT, "invalid_evidence")
    assert list(elsewhere.iterdir()) == []
    assert list((root / "docs/research").iterdir()) == []


def test_nothing_is_retained_from_an_empty_or_missing_workspace(tmp_path, helper):
    root = make_root(tmp_path)
    (tmp_path / "empty").mkdir()
    for workspace in (tmp_path / "empty", tmp_path / "missing"):
        with pytest.raises(ValueError, match="bounded original files"):
            helper["retain"](root, workspace, "failed-download.json", COMMIT, "invalid_evidence")
    assert list((root / "dist").iterdir()) == []


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (("Failed.json", COMMIT, "invalid_evidence", None), "archive name"),
        (("failed download.json", COMMIT, "invalid_evidence", None), "archive name"),
        (("../failed.json", COMMIT, "invalid_evidence", None), "archive name"),
        (("failed.txt", COMMIT, "invalid_evidence", None), "archive name"),
        (("failed-download.json", "b" * 39, "invalid_evidence", None), "digest or identifier"),
        (("failed-download.json", COMMIT, "accepted", None), "kind/reason"),
        (("failed-download.json", COMMIT, "invalid_evidence", "https://x/y"), "identifier"),
    ],
)
def test_bad_names_commits_reasons_and_urls_are_refused_before_any_output(
    tmp_path, helper, arguments, message
):
    workspace = make_workspace(tmp_path, names=["stdout.json"], decoys=False)
    root = make_root(tmp_path)
    with pytest.raises(ValueError, match=message):
        helper["retain"](root, workspace, *arguments)
    assert list((root / "dist").iterdir()) == []
    assert (workspace / "stdout.json").read_bytes() == content("stdout.json")


def test_an_existing_output_is_never_overwritten(tmp_path, helper):
    workspace = make_workspace(tmp_path, names=["stdout.json"], decoys=False)
    root = make_root(tmp_path)
    (root / "dist/failed-download.json").write_bytes(b"previous evidence")
    with pytest.raises(FileExistsError):
        helper["retain"](root, workspace, "failed-download.json", COMMIT, "invalid_evidence")
    assert (root / "dist/failed-download.json").read_bytes() == b"previous evidence"
    assert list((root / "docs/research").iterdir()) == []


def test_a_name_that_is_already_archived_keeps_the_archived_bytes(tmp_path, helper):
    workspace = make_workspace(tmp_path, names=["stdout.json"], decoys=False)
    root = make_root(tmp_path)
    _, output = do_retain(helper, tmp_path, workspace, root=root)
    archived = (root / "docs/research/raw/failed-download.json.gz").read_bytes()
    output.unlink()  # the working copy is gone; the archive is not overwritten by a retry
    with pytest.raises(ValueError, match="already registered"):
        helper["retain"](root, workspace, "failed-download.json", COMMIT, "invalid_evidence")
    assert (root / "docs/research/raw/failed-download.json.gz").read_bytes() == archived


# --- the privacy gate stands between the originals and the archive ------------------------------


def test_a_personal_literal_in_an_original_is_never_archived_and_never_altered(tmp_path, helper):
    # The explicit declaration knows an operator that the environment's declaration does not.
    context = synthetic_context(tmp_path)
    context["system_home"] = context["effective_home"] = "/Users/explicit-operator"
    secret = (context["system_home"] + "/checkout/venv/bin/python").encode()
    workspace = make_workspace(tmp_path, names=["stdout.json"], decoys=False)
    write(workspace, "16-1/client-stderr.txt", b"Traceback: " + secret + b"\n")
    before = snapshot(workspace)
    root = make_root(tmp_path)
    with pytest.raises(ValueError, match="personal_provenance"):
        helper["retain"](
            root,
            workspace,
            "failed-download.json",
            COMMIT,
            "invalid_evidence",
            privacy_context=context,
        )
    assert snapshot(workspace) == before
    assert (root / "dist/failed-download.json").exists()  # kept privately, not published
    assert list((root / "docs/research").iterdir()) == []


@pytest.mark.parametrize("raw", [b"\xffnot-json\x00\n", b'{"content_base64":broken'])
def test_an_undecodable_original_is_preserved_privately_not_published(tmp_path, helper, raw):
    workspace = make_workspace(tmp_path, names=[], decoys=False)
    write(workspace, "stdout.json", raw)
    root = make_root(tmp_path)
    with pytest.raises(ValueError):
        helper["retain"](
            root,
            workspace,
            "failed.json",
            COMMIT,
            "invalid_evidence",
            privacy_context=synthetic_context(tmp_path),
        )
    assert (workspace / "stdout.json").read_bytes() == raw
    assert (root / "dist/failed.json").exists()
    assert list((root / "docs/research").iterdir()) == []


def test_no_declared_context_means_no_archive(tmp_path, helper, monkeypatch):
    monkeypatch.delenv("YORUNGE_EVIDENCE_CONTEXT")
    workspace = make_workspace(tmp_path, names=["stdout.json"], decoys=False)
    root = make_root(tmp_path)
    with pytest.raises(ValueError, match="missing_context"):
        helper["retain"](root, workspace, "failed-download.json", COMMIT, "invalid_evidence")
    assert (root / "dist/failed-download.json").exists()
    assert list((root / "docs/research").iterdir()) == []


def test_the_declared_ci_context_reaches_the_automatic_failure_retention(
    tmp_path, helper, monkeypatch
):
    guard = runpy.run_path(str(ROOT / "scripts/evidence_privacy.py"))
    declaration = tmp_path / ".local/evidence-privacy-context.json"
    guard["private_write"](declaration, synthetic_context(tmp_path, ci=True))
    monkeypatch.setenv("YORUNGE_EVIDENCE_CONTEXT", str(declaration))
    workspace = make_workspace(tmp_path, names=["stdout.json"], decoys=False)
    root, output = do_retain(helper, tmp_path, workspace)
    assert output.exists()
    assert (root / "docs/research/raw/failed-download.json.gz").exists()


# --- the command line ----------------------------------------------------------------------------


def command(monkeypatch, tmp_path, retained, *arguments, context="declared"):
    checks = runpy.run_path(str(ROOT / "scripts/research_evidence.py"))
    original = runpy.run_path

    def load(path, *args, **kwargs):
        if Path(path).name == "download_diagnostic.py":
            return {"retain": retained}
        return original(path, *args, **kwargs)

    monkeypatch.setattr(runpy, "run_path", load)
    if context == "declared":
        path = tmp_path / "declared-context.json"
        path.write_text(json.dumps(synthetic_context(tmp_path)))
        path.chmod(0o600)
        arguments = (*arguments, "--privacy-context", str(path))
    monkeypatch.setattr(sys, "argv", ["research_evidence.py", *arguments])
    return checks["main"]


def test_the_cli_action_passes_every_argument_and_the_declared_context_to_retain(
    tmp_path, monkeypatch, capsys
):
    calls = []
    main = command(
        monkeypatch,
        tmp_path,
        lambda *args, **kwargs: calls.append((args, kwargs)),
        "archive-rejected-download",
        str(tmp_path / "workspace"),
        "--name",
        "failed-download.json",
        "--source-commit",
        COMMIT,
        "--run-url",
        RUN_URL,
        "--reason",
        "interrupted_measurement",
    )
    monkeypatch.delenv("YORUNGE_EVIDENCE_CONTEXT")
    assert main() == 0
    assert calls == [
        (
            (
                ROOT,
                tmp_path / "workspace",
                "failed-download.json",
                COMMIT,
                "interrupted_measurement",
                RUN_URL,
            ),
            {"privacy_context": synthetic_context(tmp_path)},
        )
    ]
    assert capsys.readouterr().out == (
        "Archived original synthetic download diagnostics; not acceptance.\n"
    )


@pytest.mark.parametrize(
    "reason", ["invalid_evidence", "interrupted_measurement", "unverified_measurement"]
)
def test_the_cli_action_accepts_each_closed_reason(tmp_path, monkeypatch, reason):
    calls = []
    main = command(
        monkeypatch,
        tmp_path,
        lambda *args, **kwargs: calls.append(args),
        "archive-rejected-download",
        str(tmp_path / "workspace"),
        "--name",
        "failed-download.json",
        "--source-commit",
        COMMIT,
        "--reason",
        reason,
    )
    assert main() == 0
    assert [arguments[4] for arguments in calls] == [reason]


def test_the_cli_action_takes_the_context_from_the_environment_and_a_missing_run_url(
    tmp_path, monkeypatch
):
    calls = []
    main = command(
        monkeypatch,
        tmp_path,
        lambda *args, **kwargs: calls.append((args, kwargs)),
        "archive-rejected-download",
        str(tmp_path / "workspace"),
        "--name",
        "failed-download.json",
        "--source-commit",
        COMMIT,
        "--reason",
        "invalid_evidence",
        context="environment",
    )
    assert main() == 0
    ((arguments, keywords),) = calls
    assert arguments[-1] is None
    assert keywords["privacy_context"]["mode"] == "local"


def test_the_cli_action_without_any_declared_context_retains_nothing(tmp_path, monkeypatch):
    calls = []
    main = command(
        monkeypatch,
        tmp_path,
        lambda *args, **kwargs: calls.append(args),
        "archive-rejected-download",
        str(tmp_path / "workspace"),
        "--name",
        "failed-download.json",
        "--source-commit",
        COMMIT,
        "--reason",
        "invalid_evidence",
        context="environment",
    )
    monkeypatch.delenv("YORUNGE_EVIDENCE_CONTEXT")
    with pytest.raises(SystemExit) as stop:
        main()
    assert stop.value.code == 1
    assert calls == []


REQUIRED = {
    "--name": "failed-download.json",
    "--source-commit": COMMIT,
    "--reason": "invalid_evidence",
}


@pytest.mark.parametrize(
    "variant",
    ["unknown_reason", "no_name", "no_source_commit", "no_reason", "no_workspace", "bad_option"],
)
def test_the_cli_action_refuses_unknown_reasons_and_missing_arguments(
    tmp_path, monkeypatch, variant
):
    options = dict(REQUIRED)
    positional = [str(tmp_path / "workspace")]
    if variant == "unknown_reason":
        options["--reason"] = "accepted"
    elif variant == "no_workspace":
        positional = []
    elif variant == "bad_option":
        options["--unknown"] = "x"
    else:
        del options[
            {"no_name": "--name", "no_source_commit": "--source-commit"}.get(variant, "--reason")
        ]
    calls = []
    main = command(
        monkeypatch,
        tmp_path,
        lambda *args, **kwargs: calls.append(args),
        "archive-rejected-download",
        *positional,
        *[part for item in options.items() for part in item],
    )
    with pytest.raises(SystemExit) as stop:
        main()
    assert stop.value.code == 2
    assert calls == []


# --- the artifact patterns publish what the retention keeps ---------------------------------------


def test_the_artifact_patterns_select_the_ci_workspaces_originals_and_never_a_body(
    tmp_path, helper
):
    guard = runpy.run_path(str(ROOT / "scripts/evidence_privacy.py"))
    repository = tmp_path / "repository"
    workspace = repository / ".local/download-check"
    workspace.mkdir(parents=True)
    for name in layout():
        write(workspace, name)
    # The globs do not know run names: a misnamed run directory's client log would be published.
    decoys = [
        name
        for name in DECOYS
        if name not in {"16-4/client-stdout.json", "capacity-1/client-stdout.json"}
    ]
    for name in decoys:
        write(workspace, name, b"must-not-publish\n")
    # What the CI wrapper beside the workspace writes, and the report names it publishes.
    logs = [
        ".local/download-check-controller-stdout.txt",
        ".local/download-check-controller-stderr.txt",
    ]
    reports = ["dist/download.json", "dist/download-reference.txt"]
    rejected = ["dist/download-rejected.json", "dist/download-ci-rejected.json"]
    for name in (*logs, *reports, *rejected):
        write(repository, name)
    foreign = ["dist/downloaded.json", "dist/download.json.bak", "dist/downloads/report.json"]
    for name in foreign:
        write(repository, name, b"not this measurement\n")
    selected = guard["selected_paths"](repository, ROOT / "scripts/evidence-artifact-paths.txt")
    names = {path.relative_to(repository).as_posix() for path in selected}
    retained = {path.relative_to(workspace).as_posix() for path in helper["paths"](workspace)}
    # Everything the retention can take from the CI workspace is published too, except the two
    # files only the installation smoke's metadata probe writes.
    metadata = {"metadata-stdout.json", "metadata-stderr.txt"}
    assert {f".local/download-check/{name}" for name in retained - metadata} <= names
    assert not any(name.endswith(tuple(metadata)) for name in names)
    assert set(logs) | set(reports) | set(rejected) <= names
    assert names - set(logs) - set(reports) - set(rejected) == {
        f".local/download-check/{name}" for name in retained - metadata
    }
    assert not names & {f".local/download-check/{name}" for name in decoys}
    assert not names & set(foreign)
