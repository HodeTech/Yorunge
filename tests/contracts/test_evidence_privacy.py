"""Known provenance, declared runtime inputs, nested limits and first public boundary."""

import base64
import gzip
import hashlib
import io
import json
import os
import runpy
import struct
import subprocess
import zipfile
import zlib
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from tests.fixtures.evidence_publication import synthetic_context

ROOT = Path(__file__).resolve().parents[2]
GUARD = runpy.run_path(str(ROOT / "scripts/evidence_privacy.py"))


def encode(value):
    return json.dumps(value).encode()


def part(raw, name="stderr.txt", key="content_base64"):
    size, digest = len(raw), hashlib.sha256(raw).hexdigest()
    text = base64.b64encode(raw).decode()
    if key == "original_base64":
        return {
            key: text,
            "original_bytes": size,
            "original_sha256": digest,
            "original_filename": name,
        }
    return {key: text, "bytes": size, "sha256": digest, "name": name}


@pytest.mark.parametrize("field", sorted(GUARD["CONTEXT_FIELDS"]))
def test_missing_context_field_never_passes(field, tmp_path):
    value = synthetic_context(tmp_path)
    del value[field]
    with pytest.raises(ValueError):
        GUARD["check"](b"{}", "report.json", value)


@pytest.mark.parametrize("field", ["workspaces", "child_roots", "system_home", "controller"])
def test_empty_required_context_is_not_a_clean_scan(field, tmp_path):
    value = synthetic_context(tmp_path)
    value[field] = [] if field.endswith("s") else ""
    with pytest.raises(ValueError):
        GUARD["check"](b"{}", "report.json", value)


@pytest.mark.parametrize("kind", ["plain", "escaped", "base64", "gzip", "zip", "binary", "email"])
def test_known_personal_value_in_supported_layers_rejects(kind, tmp_path):
    value = synthetic_context(tmp_path)
    raw = (value["system_home"] + "/checkout/venv/bin/python").encode()
    name = "report.json"
    if kind == "plain":
        raw = encode({"executable": raw.decode()})
    elif kind == "escaped":
        raw = encode({"executable": raw.decode()}).replace(b"/", b"\\u002f")
    elif kind == "base64":
        raw = encode({"files": [part(raw)]})
    elif kind == "gzip":
        raw = encode(part(gzip.compress(raw), "trace.txt.gz"))
    elif kind == "zip":
        zipped = io.BytesIO()
        with zipfile.ZipFile(zipped, "w") as archive:
            archive.writestr("trace.txt", raw)
        raw = encode(part(zipped.getvalue(), "trace.zip"))
    elif kind == "binary":
        raw = encode(part(gzip.compress(b"\x00\xff" + raw), "profile.prof.gz", "original_base64"))
    else:
        raw = encode({"files": [part(value["git_author_email"]["value"].encode())]})
    with pytest.raises(ValueError, match="personal_provenance"):
        GUARD["check"](raw, name, value)


@pytest.mark.parametrize("wrapper", ["trace", "json-string"])
def test_encoded_object_inside_opaque_text_is_uninspectable_not_clean(wrapper, tmp_path):
    value = synthetic_context(tmp_path)
    embedded = encode(part(value["system_home"].encode()))
    raw, name = b"Traceback prefix\n" + embedded, "stderr.txt"
    if wrapper == "json-string":
        raw, name = encode({"message": raw.decode()}), "report.json"
    with pytest.raises(ValueError, match="unsupported_encoded_evidence"):
        GUARD["check"](raw, name, value)


@pytest.mark.parametrize(
    "change", ["hash", "size", "base64", "unknown", "ambiguous", "format", "compressed"]
)
def test_unverifiable_or_unsupported_attachment_is_not_clean(change, tmp_path):
    value = synthetic_context(tmp_path)
    item = part(b"safe")
    if change == "hash":
        item["sha256"] = "0" * 64
    elif change == "size":
        item["bytes"] += 1
    elif change == "base64":
        item["content_base64"] = "invalid$"
    elif change == "unknown":
        item["payload_base64"] = item.pop("content_base64")
    elif change == "ambiguous":
        item["original_bytes"] = item["bytes"]
    elif change == "format":
        item["name"] = "opaque.unknown"
    else:
        item = part(b"\x1f\x8bcorrupt", "broken.txt.gz")
    raw = encode(item)
    with pytest.raises(ValueError):
        GUARD["check"](raw, "report.json", value)


@pytest.mark.parametrize("raw", [b"\xffnot-json\x00\n", b'{"content_base64":broken'])
def test_undecodable_diagnostic_original_is_preserved_privately_not_published(raw, tmp_path):
    diagnostic = runpy.run_path(str(ROOT / "scripts/upload_diagnostic.py"))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "stdout.json").write_bytes(raw)
    (tmp_path / "dist").mkdir()
    (tmp_path / "docs/research").mkdir(parents=True)
    value = synthetic_context(tmp_path)
    with pytest.raises(ValueError):
        diagnostic["retain"](
            tmp_path,
            workspace,
            "failed.json",
            "a" * 40,
            "invalid_evidence",
            privacy_context=value,
        )
    assert (workspace / "stdout.json").read_bytes() == raw
    assert (tmp_path / "dist/failed.json").exists()
    assert list((tmp_path / "docs/research").iterdir()) == []


@pytest.mark.parametrize(
    "guard", ["MAX_FILE", "MAX_TOTAL", "MAX_MEMBERS", "MAX_DEPTH", "MAX_NODES"]
)
def test_bounded_nested_scan_never_ignores_an_over_limit_member(guard, tmp_path, monkeypatch):
    namespace = GUARD["check"].__globals__
    monkeypatch.setitem(namespace, guard, 1)
    raw, value = encode(part(encode(part(b"safe")))), synthetic_context(tmp_path)
    with pytest.raises(ValueError, match="publication_limit"):
        GUARD["check"](raw, "report.json", value)


def test_gzip_expansion_reads_only_the_limit_plus_one(tmp_path, monkeypatch):
    monkeypatch.setitem(GUARD["Scanner"].scan.__globals__, "MAX_FILE", 64)
    raw = gzip.compress(b"x" * 10_000)
    assert len(raw) < 64
    scanner = GUARD["Scanner"](synthetic_context(tmp_path))
    with pytest.raises(ValueError, match="publication_limit"):
        scanner.scan(raw, "large.txt.gz")
    assert scanner.total == len(raw) + 65


def test_zip_oversize_member_rejects_before_opening_member(tmp_path, monkeypatch):
    zipped = io.BytesIO()
    with zipfile.ZipFile(zipped, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("large.txt", b"x" * 10_000)
    raw = zipped.getvalue()
    assert len(raw) < 256
    monkeypatch.setitem(GUARD["Scanner"].scan.__globals__, "MAX_FILE", 256)

    def forbidden(*args, **kwargs):
        raise AssertionError("oversize member was opened")

    monkeypatch.setattr(zlib, "decompressobj", forbidden)
    value = synthetic_context(tmp_path)
    with pytest.raises(ValueError, match="unsupported_encoded_evidence"):
        GUARD["check"](raw, "archive.zip", value)


def test_unknown_zip_compression_and_corrupt_deflate_are_controlled_rejections(tmp_path):
    zipped = io.BytesIO()
    with zipfile.ZipFile(zipped, "w", compression=zipfile.ZIP_BZIP2) as archive:
        archive.writestr("safe.txt", b"safe")
    raw, value = zipped.getvalue(), synthetic_context(tmp_path)
    with pytest.raises(ValueError, match="unsupported_encoded_evidence"):
        GUARD["check"](raw, "archive.zip", value)
    corrupt = b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03\x06" + b"\x00" * 8
    with pytest.raises(ValueError, match="invalid_encoded_evidence"):
        GUARD["check"](corrupt, "bad.txt.gz", value)


@pytest.mark.parametrize("nonempty", [False, True])
def test_zip_directory_cannot_hide_compressed_personal_payload(nonempty, tmp_path):
    value = synthetic_context(tmp_path)
    zipped = io.BytesIO()
    with zipfile.ZipFile(zipped, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("trace/", value["system_home"].encode() if nonempty else b"")
    raw = encode(part(zipped.getvalue(), "trace.zip"))
    if nonempty:
        with pytest.raises(ValueError, match="unsupported_encoded_evidence"):
            GUARD["check"](raw, "report.json", value)
    else:
        GUARD["check"](raw, "report.json", value)


def test_ci_profile_rejects_a_personal_interpreter_even_with_generic_runner_home(tmp_path):
    value = synthetic_context(tmp_path, ci=True)
    value["controller"]["executable"] = "/Users/synthetic-private-operator/venv/bin/python"
    with pytest.raises(ValueError, match="personal_runtime_input"):
        GUARD["neutral_inputs"](value)


def test_empty_zip_directories_still_consume_the_global_member_budget(tmp_path, monkeypatch):
    zipped = io.BytesIO()
    with zipfile.ZipFile(zipped, "w") as archive:
        archive.writestr("first/", b"")
        archive.writestr("second/", b"")
    raw, value = zipped.getvalue(), synthetic_context(tmp_path)
    monkeypatch.setitem(GUARD["Scanner"].scan.__globals__, "MAX_MEMBERS", 2)
    with pytest.raises(ValueError, match="publication_limit"):
        GUARD["check"](raw, "directories.zip", value)


def zip_fixture(name="trace.txt", content=b"safe", compression=zipfile.ZIP_DEFLATED):
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", compression=compression) as archive:
        archive.writestr(name, content)
    return target.getvalue()


@pytest.mark.parametrize("name", ["trace/", "trace.txt"])
@pytest.mark.parametrize("forged", ["size_crc", "compressed_size", "crc"])
def test_zip_stream_cannot_be_hidden_by_consistent_but_false_metadata(name, forged, tmp_path):
    value = synthetic_context(tmp_path)
    content = value["system_home"].encode()
    raw = bytearray(zip_fixture(name, content))
    central = struct.unpack_from("<I", raw, len(raw) - 6)[0]
    if forged == "size_crc":
        for offset in (14, 22, central + 16, central + 24):
            struct.pack_into("<I", raw, offset, 0)
        # This is the demonstrated bypass in metadata-trusting readers.
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            assert archive.read(name) == b""
    elif forged == "compressed_size":
        for offset in (18, central + 20):
            struct.pack_into("<I", raw, offset, 0)
    else:
        for offset in (14, central + 16):
            struct.pack_into("<I", raw, offset, 0)
    assert content not in raw
    report = encode(part(bytes(raw), "trace.zip"))
    with pytest.raises(ValueError, match="invalid_encoded_evidence"):
        GUARD["check"](report, "report.json", value)


@pytest.mark.parametrize("variant", ["gap", "unused_deflate", "truncated_deflate"])
def test_zip_local_extent_and_deflate_full_consumption_are_checked(variant, tmp_path):
    original = zip_fixture()
    central = struct.unpack_from("<I", original, len(original) - 6)[0]
    size = struct.unpack_from("<I", original, 18)[0]
    if variant == "truncated_deflate":
        raw, change = bytearray(original[: central - 1] + original[central:]), -1
    else:
        raw, change = bytearray(original[:central] + b"extra" + original[central:]), 5
    new_central = central + change
    struct.pack_into("<I", raw, len(raw) - 6, new_central)
    if variant != "gap":
        struct.pack_into("<I", raw, 18, size + change)
        struct.pack_into("<I", raw, new_central + 20, size + change)
    value, wire = synthetic_context(tmp_path), bytes(raw)
    with pytest.raises(ValueError, match="invalid_encoded_evidence"):
        GUARD["check"](wire, "trace.zip", value)


@pytest.mark.parametrize(
    "variant", ["comment", "extra", "member_comment", "descriptor", "zip64", "prefix"]
)
def test_unsupported_zip_variants_are_explicitly_rejected(variant, tmp_path):
    class Unseekable(io.BytesIO):
        def seek(self, *args):
            raise io.UnsupportedOperation("synthetic unseekable writer")

    target = Unseekable() if variant == "descriptor" else io.BytesIO()
    member = zipfile.ZipInfo("trace.txt")
    if variant == "extra":
        member.extra = b"\xfe\xca\x00\x00"
    elif variant == "member_comment":
        member.comment = b"comment"
    with zipfile.ZipFile(target, "w") as archive:
        if variant == "comment":
            archive.comment = b"comment"
        if variant == "zip64":
            with archive.open(member, "w", force_zip64=True) as output:
                output.write(b"safe")
        else:
            archive.writestr(member, b"safe")
    raw = target.getvalue()
    if variant == "prefix":
        raw = b"prefix" + raw
    value = synthetic_context(tmp_path)
    with pytest.raises(ValueError):
        GUARD["check"](raw, "trace.zip", value)


@pytest.mark.parametrize("compression", [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED])
@pytest.mark.parametrize("name", ["trace.txt", "öğe.txt"])
def test_supported_zip_member_streams_preserve_safe_ascii_and_utf8_names(
    compression, name, tmp_path
):
    GUARD["check"](
        zip_fixture(name, compression=compression), "trace.zip", synthetic_context(tmp_path)
    )


def test_supported_cp437_zip_name_is_decoded_before_literal_scan(tmp_path):
    raw = bytearray(zip_fixture("a.txt"))
    central = struct.unpack_from("<I", raw, len(raw) - 6)[0]
    raw[30:35] = raw[central + 46 : central + 51] = b"\x82.txt"
    GUARD["check"](bytes(raw), "trace.zip", synthetic_context(tmp_path))


@pytest.mark.parametrize("kind", ["fifo", "symlink", "directory"])
def test_private_context_and_publication_never_follow_or_block_on_special_file(
    kind, tmp_path, monkeypatch
):
    path = tmp_path / "input.json"
    if kind == "fifo":
        os.mkfifo(path)
    elif kind == "directory":
        path.mkdir()
    else:
        target = tmp_path / "target.json"
        target.write_bytes(b"{}")
        path.symlink_to(target)
    descriptors = []
    original = os.open

    def opened(*args, **kwargs):
        descriptor = original(*args, **kwargs)
        descriptors.append(descriptor)
        return descriptor

    monkeypatch.setattr(os, "open", opened)
    with pytest.raises(ValueError):
        GUARD["read_file"](path)
    for descriptor in descriptors:
        with pytest.raises(OSError):
            os.fstat(descriptor)


@pytest.mark.parametrize("field", ["executable", "resolved_executable", "prefix", "temp"])
def test_neutral_checkout_does_not_hide_personal_controller_or_temporary_root(field, tmp_path):
    value = synthetic_context(tmp_path)
    value["controller"][field] = value["system_home"] + "/private-input"
    with pytest.raises(ValueError, match="personal_runtime_input"):
        GUARD["neutral_inputs"](value)


def test_neutral_context_and_multirow_jsonl_and_safe_encoded_profile_pass(tmp_path):
    value = synthetic_context(tmp_path)
    GUARD["neutral_inputs"](value)
    GUARD["check"](b'{"ok":true}\n{"ok":false}\n', "install.jsonl", value)
    GUARD["check"](
        encode(part(gzip.compress(b"\x00\xffbinary"), "a.prof.gz", "original_base64")),
        "report.json",
        value,
    )
    # No general email detector claim: only known literal / author metadata policy.
    GUARD["check"](encode({"message": "unclassified@example.invalid"}), "report.json", value)
    raw = encode({"author": {"email": "other@example.invalid"}})
    with pytest.raises(ValueError, match="author_email_metadata"):
        GUARD["check"](raw, "report.json", value)


def test_collector_captures_actual_interpreter_prefix_temp_and_explicit_absent_email(
    tmp_path, monkeypatch
):
    namespace = GUARD["context"].__globals__
    monkeypatch.setenv("HOME", "/Users/synthetic-private-operator")
    monkeypatch.setattr(
        namespace["pwd"],
        "getpwuid",
        lambda uid: SimpleNamespace(pw_dir="/Users/synthetic-private-operator"),
    )
    monkeypatch.setattr(
        namespace["subprocess"], "run", lambda *a, **kw: SimpleNamespace(returncode=1, stdout=b"")
    )
    value = GUARD["context"](tmp_path, [tmp_path / "work"], [tmp_path / "children"], "local")
    assert value["controller"]["executable"] == str(Path(namespace["sys"].executable).absolute())
    assert value["controller"]["prefix"] == str(Path(namespace["sys"].prefix).resolve())
    assert value["controller"]["temp"] == namespace["tempfile"].gettempdir()
    assert value["git_author_email"] == {"status": "absent", "value": None}
    monkeypatch.delenv("HOME")
    with pytest.raises(ValueError, match="missing_context"):
        GUARD["context"](tmp_path, [tmp_path], [tmp_path], "local")


@pytest.mark.parametrize("fail", [False, True])
def test_ci_stages_original_bytes_only_after_all_checks_and_never_stages_context(
    fail, tmp_path, monkeypatch
):
    root = tmp_path / "repo"
    value = synthetic_context(root, ci=True)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    declaration = tmp_path / "private-context.json"
    GUARD["private_write"](declaration, value)
    (root / "dist").mkdir(parents=True)
    original = encode(
        {"value": value["git_author_email"]["value"] if fail else "/home/runner/work/neutral"}
    )
    (root / "dist/report.json").write_bytes(original)
    patterns = tmp_path / "paths.txt"
    patterns.write_text("dist/*.json\n")
    destination = tmp_path / "public"
    if fail:
        with pytest.raises(ValueError, match="personal_provenance"):
            GUARD["stage_ci"](root, destination, patterns, declaration)
        assert not destination.exists()
    else:
        GUARD["stage_ci"](root, destination, patterns, declaration)
        assert (destination / "dist/report.json").read_bytes() == original
        assert sorted(
            p.relative_to(destination).as_posix() for p in destination.rglob("*") if p.is_file()
        ) == ["dist/report.json"]
    assert (root / "dist/report.json").read_bytes() == original


def test_ci_context_cannot_omit_the_actual_publication_source(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    value = synthetic_context(tmp_path / "other-source", ci=True)
    declaration = tmp_path / "context.json"
    GUARD["private_write"](declaration, value)
    with pytest.raises(ValueError, match="invalid_context"):
        GUARD["stage_ci"](tmp_path, tmp_path / "public", tmp_path / "missing.txt", declaration)
    assert not (tmp_path / "public").exists()


def test_ci_source_change_after_scan_removes_entire_stage(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "dist").mkdir(parents=True)
    source = root / "dist/report.json"
    source.write_bytes(b'{"before":true}')
    declaration, patterns = tmp_path / "context.json", tmp_path / "patterns.txt"
    GUARD["private_write"](declaration, synthetic_context(root, ci=True))
    patterns.write_text("dist/*.json\n")
    original = GUARD["copy_stage"]

    def changed(*args):
        source.write_bytes(b'{"after":true}')
        original(*args)

    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setitem(GUARD["stage_ci"].__globals__, "copy_stage", changed)
    with pytest.raises(ValueError, match="publication_changed"):
        GUARD["stage_ci"](root, tmp_path / "public", patterns, declaration)
    assert not (tmp_path / "public").exists()
    assert source.read_bytes() == b'{"after":true}'


def test_archive_missing_or_rejected_context_has_zero_public_writes(tmp_path, monkeypatch):
    checks = runpy.run_path(str(ROOT / "scripts/research_evidence.py"))
    (tmp_path / "dist").mkdir()
    (tmp_path / "docs/research").mkdir(parents=True)
    source = tmp_path / "dist/rejected.json"
    source.write_bytes(encode({"value": "/Users/synthetic-private-operator/a"}))
    monkeypatch.delenv("YORUNGE_EVIDENCE_CONTEXT", raising=False)
    with pytest.raises(ValueError, match="missing_context"):
        checks["archive_report"](tmp_path, source, None)
    value = synthetic_context(tmp_path)
    with pytest.raises(ValueError, match="personal_provenance"):
        checks["archive_report"](tmp_path, source, None, privacy_context=value)
    assert list((tmp_path / "docs/research").iterdir()) == []
    assert source.exists()


def test_ci_privacy_failure_records_open_retention_without_exposing_exception_or_upload(
    tmp_path, monkeypatch, capsys
):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(
        GUARD["main"].__globals__["sys"],
        "argv",
        [
            "privacy",
            "stage-ci",
            "--context",
            str(tmp_path / "private-canary-missing.json"),
            "--source-root",
            str(tmp_path),
            "--patterns",
            str(tmp_path / "paths.txt"),
            "--destination",
            str(tmp_path / "public"),
        ],
    )
    assert GUARD["main"]() == 1
    output = capsys.readouterr()
    assert "private-canary" not in output.err
    assert not (tmp_path / "public").exists()
    assert "Permanent retention remains OPEN" in summary.read_text()
    assert "ephemeral runner" in summary.read_text()


def test_ci_declared_context_reaches_automatic_failure_retention_without_private_argument(
    tmp_path, monkeypatch
):
    workflow = yaml.load(
        (ROOT / ".github/workflows/checks.yml").read_text(), Loader=yaml.BaseLoader
    )
    step = next(
        s for s in workflow["jobs"]["linux311"]["steps"] if s.get("id") == "evidence-context"
    )
    exported = next(
        line
        for line in step["run"].splitlines()
        if line.startswith('echo "YORUNGE_EVIDENCE_CONTEXT=')
    )
    context_path = tmp_path / ".local/evidence-privacy-context.json"
    GUARD["private_write"](context_path, synthetic_context(tmp_path, ci=True))
    environment = dict(os.environ, GITHUB_WORKSPACE=str(tmp_path), GITHUB_ENV=str(tmp_path / "env"))
    subprocess.run(["bash", "-e", "-c", exported], env=environment, check=True, timeout=5)
    name, value = (tmp_path / "env").read_text().strip().split("=", 1)
    assert name == "YORUNGE_EVIDENCE_CONTEXT"
    assert value == str(context_path)
    monkeypatch.setenv(name, value)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    raw = b'{ "failed": true }\n'
    (workspace / "stdout.json").write_bytes(raw)
    (tmp_path / "dist").mkdir()
    (tmp_path / "docs/research").mkdir(parents=True)
    diagnostic = runpy.run_path(str(ROOT / "scripts/upload_diagnostic.py"))
    report = diagnostic["retain"](
        tmp_path, workspace, "ci-failure.json", "a" * 40, "invalid_evidence"
    )
    assert report.exists()
    assert (tmp_path / "docs/research/raw/ci-failure.json.gz").exists()
    assert (workspace / "stdout.json").read_bytes() == raw


def test_original_commit_means_first_matching_bytes_not_first_path_or_later_copy(tmp_path):
    checks = runpy.run_path(str(ROOT / "scripts/research_evidence.py"))

    def git(*args):
        return (
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(tmp_path),
                    "-c",
                    "user.name=Synthetic Test",
                    "-c",
                    "user.email=synthetic@example.invalid",
                    "-c",
                    "commit.gpgsign=false",
                    "-c",
                    "core.hooksPath=/dev/null",
                    *args,
                ],
                capture_output=True,
                check=True,
                timeout=5,
            )
            .stdout.decode()
            .strip()
        )

    git("init", "-q")
    original = tmp_path / "docs/research/example.json"
    original.parent.mkdir(parents=True)
    original.write_bytes(b"old different bytes")
    git("add", ".")
    git("commit", "-qm", "first path, different report")
    first_path = git("rev-parse", "HEAD")
    original.write_bytes(
        encode({"source_base_commit": "a" * 40, "runs": [{"outcome": "ok", "elapsed_ms": 3.0}]})
    )
    git("add", ".")
    git("commit", "-qm", "first matching report")
    first_match = git("rev-parse", "HEAD")
    git("commit", "--allow-empty", "-qm", "later snapshot with identical blob")
    later = git("rev-parse", "HEAD")
    verify = checks["original_commit_for"]
    raw = original.read_bytes()
    assert verify(tmp_path, original.name, raw, first_match) == first_match
    assert verify(tmp_path, original.name, raw, None) == first_match
    for rejected in (first_path, later):
        with pytest.raises(ValueError, match="first exact archived bytes"):
            verify(tmp_path, original.name, raw, rejected)
    with pytest.raises(ValueError, match="first exact archived bytes"):
        verify(tmp_path, "missing.json", raw, first_match)
    assert verify(tmp_path, "missing.json", raw, None) is None
    original.unlink()
    (tmp_path / "dist").mkdir()
    source = tmp_path / "dist/example.json"
    source.write_bytes(raw)
    checks["archive_report"](tmp_path, source, None, privacy_context=synthetic_context(tmp_path))
    catalog = json.loads((tmp_path / "docs/research/evidence-manifest.json").read_bytes())
    assert catalog["entries"][0]["original_commit"] == first_match
    assert checks["verify"](tmp_path) == 1
    (tmp_path / ".git/shallow").write_text(later + "\n")
    with pytest.raises(ValueError, match="full Git history"):
        verify(tmp_path, "missing.json", raw, None)
