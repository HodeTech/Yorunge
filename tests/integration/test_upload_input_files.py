"""Full current hashing and subsequent descriptor observation before upload effects."""

import copy
import hashlib
import os
import pickle
import shutil
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from yorunge.adapters import dataset_files
from yorunge.adapters import upload_input_files as module
from yorunge.adapters.dataset_files import open_dataset
from yorunge.adapters.upload_input_files import capture_upload_input
from yorunge.application.datasets import DatasetBudget
from yorunge.domain.credentials import SecretValue
from yorunge.domain.dataset_manifest import build_manifest
from yorunge.domain.errors import YorungeError

SECRET = SecretValue("synthetic-input-secret-canary")


def fixture(tmp_path, files=None):
    root = tmp_path / "outer" / "root"
    root.mkdir(parents=True)
    for name, data in (files or {"file.bin": b"content"}).items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    with open_dataset(root, DatasetBudget()) as tree:
        manifest = tree.scan()
    artifact = tmp_path / "manifest.json"
    artifact.write_bytes(manifest.encoded())
    return root, manifest, artifact


def capture(root, manifest, **changes):
    return capture_upload_input(root, manifest, SECRET, end=time.monotonic() + 900, **changes)


def rejected(code, callback):
    with pytest.raises(YorungeError) as failure:
        callback()
    assert failure.value.code == code


def test_both_manifest_sources_hash_all_names_and_retain_no_descriptors(tmp_path, monkeypatch):
    root, manifest, artifact = fixture(tmp_path, {"a.bin": b"equal", "nested/b.bin": b"equal"})
    os.link(root / "a.bin", root / "hardlink.bin")
    with open_dataset(root, DatasetBudget()) as tree:
        manifest = tree.scan()
    artifact.write_bytes(manifest.encoded())
    opened = set()
    original_open, original_dup, original_close = os.open, os.dup, os.close

    def tracking_open(*args, **kwargs):
        descriptor = original_open(*args, **kwargs)
        opened.add(descriptor)
        return descriptor

    def tracking_dup(*args):
        descriptor = original_dup(*args)
        opened.add(descriptor)
        return descriptor

    def tracking_close(descriptor):
        original_close(descriptor)
        opened.discard(descriptor)

    monkeypatch.setattr(os, "open", tracking_open)
    monkeypatch.setattr(os, "dup", tracking_dup)
    monkeypatch.setattr(os, "close", tracking_close)
    # The wrapper forwards the original proven dir_fd primitive unchanged.
    monkeypatch.setattr(
        os,
        "supports_dir_fd",
        {tracking_open if item is original_open else item for item in os.supports_dir_fd},
    )
    first = capture(root, artifact)
    assert first.manifest == manifest and first.manifest.file_count == 3
    assert len({file.sha256 for file in manifest.files}) == 1
    assert opened == set()
    first.recheck()
    assert opened == set()
    second = capture(root, manifest, expected_root=first.root)
    second.recheck()
    assert second.root == first.root and opened == set()
    assert first.root.anchor == str(root)


def test_recheck_reads_metadata_and_membership_without_rehashing_content(tmp_path, monkeypatch):
    root, manifest, _ = fixture(tmp_path)
    observation = capture(root, manifest)

    def no_content_read(*args):
        pytest.fail("metadata recheck must not call os.read")

    monkeypatch.setattr(os, "read", no_content_read)
    observation.recheck()


@pytest.mark.parametrize(
    "change",
    [
        "content",
        "add_file",
        "remove_file",
        "rename",
        "add_empty_directory",
        "replace_inode",
        "leaf_symlink",
        "root",
        "ancestor",
        "remove_root",
        "remove_ancestor",
        "root_file",
        "root_symlink",
        "ancestor_symlink",
    ],
)
def test_observed_tree_mutations_reject_before_next_effect(tmp_path, change):
    root, manifest, _ = fixture(tmp_path)
    observation = capture(root, manifest)
    path = root / "file.bin"
    if change == "content":
        path.write_bytes(b"CONTENT")
    elif change == "add_file":
        (root / "new.bin").write_bytes(b"new")
    elif change == "remove_file":
        path.unlink()
    elif change == "rename":
        path.rename(root / "renamed.bin")
    elif change == "add_empty_directory":
        (root / "empty").mkdir()
    elif change == "replace_inode":
        path.unlink()
        path.write_bytes(b"content")
    elif change == "leaf_symlink":
        path.unlink()
        path.symlink_to(tmp_path / "outside.bin")
    elif change == "root":
        root.rename(root.with_name("old"))
        root.mkdir()
        path.write_bytes(b"content")
    elif change == "ancestor":
        root.parent.rename(tmp_path / "previous-ancestor")
        root.mkdir(parents=True)
        path.write_bytes(b"content")
    elif change == "remove_root":
        shutil.rmtree(root)
    elif change == "remove_ancestor":
        shutil.rmtree(root.parent)
    elif change == "root_file":
        root.rename(root.with_name("old"))
        root.write_bytes(b"not-a-directory")
    elif change == "root_symlink":
        old = root.with_name("old")
        root.rename(old)
        root.symlink_to(old, target_is_directory=True)
    else:
        old = tmp_path / "previous-ancestor"
        root.parent.rename(old)
        root.parent.symlink_to(old, target_is_directory=True)
    rejected("input_changed", observation.recheck)


def test_fresh_capture_detects_same_size_content_change_with_preserved_mtime(tmp_path):
    root, manifest, artifact = fixture(tmp_path)
    path = root / "file.bin"
    before = path.stat()
    path.write_bytes(b"CONTENT")
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert path.stat().st_size == before.st_size
    assert path.stat().st_mtime_ns == before.st_mtime_ns
    for expected in (manifest, artifact):
        rejected("input_changed", lambda expected=expected: capture(root, expected))


def test_empty_directory_difference_before_hash_is_not_content_mismatch(tmp_path):
    root, manifest, _ = fixture(tmp_path)
    (root / "empty").mkdir()
    assert capture(root, manifest).manifest == manifest


def test_wrong_saved_root_identity_and_malformed_manifest_are_controlled(tmp_path):
    root, manifest, artifact = fixture(tmp_path)
    captured = capture(root, manifest)
    bad_root = captured.root.model_copy(update={"inode": captured.root.inode + 1})
    rejected("input_changed", lambda: capture(root, manifest, expected_root=bad_root))
    artifact.write_bytes(b'{"schema_version":1,"schema_version":1}')
    rejected("manifest_invalid", lambda: capture(root, artifact))


@pytest.mark.parametrize(
    "name", ["synthetic-input-secret-canary", "prefix-synthetic-input-secret-canary.bin"]
)
def test_selected_literal_in_manifest_name_never_becomes_input_proof(tmp_path, name):
    root, _, artifact = fixture(tmp_path, {name: b"content"})
    rejected("invalid_request", lambda: capture(root, artifact))


def test_fixed_manifest_protocol_does_not_reject_short_credential(tmp_path):
    root, manifest, _ = fixture(tmp_path)
    result = capture_upload_input(root, manifest, SecretValue("files"), end=time.monotonic() + 30)
    assert result.manifest == manifest


def test_empty_and_129_file_manifests_reject_before_hash(tmp_path, monkeypatch):
    root, manifest, _ = fixture(tmp_path)
    empty = build_manifest(())
    from yorunge.domain.dataset_manifest import DatasetFile

    large = build_manifest(
        tuple(
            DatasetFile(path=f"item{i:03}.bin", size=0, sha256=hashlib.sha256(b"").hexdigest())
            for i in range(129)
        )
    )

    def no_scan(self):
        pytest.fail("invalid upload subset must reject before source scan")

    monkeypatch.setattr(dataset_files.DatasetTree, "scan", no_scan)
    rejected("input_invalid", lambda: capture(root, empty))
    rejected("input_budget_exceeded", lambda: capture(root, large))


@pytest.mark.parametrize("end", [True, None, "future", float("nan"), float("inf"), 10**1000])
def test_deadline_is_strict_before_filesystem_io(tmp_path, monkeypatch, end):
    def no_io(*args, **kwargs):
        pytest.fail("bad deadline cannot reach filesystem")

    monkeypatch.setattr(module, "open_dataset", no_io)
    rejected(
        "invalid_request",
        lambda: capture_upload_input(tmp_path, tmp_path / "manifest", SECRET, end=end),
    )


def test_expired_or_oversized_deadline_and_snapshot_expiry_are_controlled(tmp_path, monkeypatch):
    root, manifest, _ = fixture(tmp_path)
    now = time.monotonic()
    rejected("execution_timeout", lambda: capture_upload_input(root, manifest, SECRET, end=now - 1))
    rejected("invalid_request", lambda: capture_upload_input(root, manifest, SECRET, end=now + 901))
    captured = capture_upload_input(root, manifest, SECRET, end=now + 30)
    monkeypatch.setattr(module.time, "monotonic", lambda: now + 31)
    rejected("execution_timeout", captured.recheck)


def test_snapshot_pid_thread_and_serialization_cannot_be_reused(tmp_path, monkeypatch):
    root, manifest, _ = fixture(tmp_path)
    captured = capture(root, manifest)
    issuer = os.getpid()
    monkeypatch.setattr(module.os, "getpid", lambda: issuer + 1)
    rejected("invalid_request", captured.recheck)
    monkeypatch.setattr(module.os, "getpid", lambda: issuer)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(rejected, "invalid_request", captured.recheck).result()
    for callback in (
        lambda: copy.copy(captured),
        lambda: copy.deepcopy(captured),
        lambda: pickle.dumps(captured),
    ):
        with pytest.raises(TypeError):
            callback()
    assert repr(captured) == "<upload input observation private>"
    assert str(root) not in repr(captured)


def test_upload_file_size_limit_rejects_before_full_hash(tmp_path, monkeypatch):
    from yorunge.domain.dataset_manifest import DatasetFile

    root, _, _ = fixture(tmp_path)
    large = build_manifest((DatasetFile(path="oversize.bin", size=500_000_001, sha256="0" * 64),))

    def no_scan(self):
        pytest.fail("oversize file must reject before hash")

    monkeypatch.setattr(dataset_files.DatasetTree, "scan", no_scan)
    rejected("input_budget_exceeded", lambda: capture(root, large))


def test_selected_secret_in_root_anchor_rejects_before_hash(tmp_path, monkeypatch):
    root, manifest, _ = fixture(tmp_path / "synthetic-input-secret-canary")

    def no_scan(self):
        pytest.fail("secret-bearing anchor must reject before hash")

    monkeypatch.setattr(dataset_files.DatasetTree, "scan", no_scan)
    rejected("invalid_request", lambda: capture(root, manifest))


def test_unsupported_primitive_precedes_even_relative_path_cwd_io(tmp_path, monkeypatch):
    from pathlib import Path

    def no_cwd(cls):
        pytest.fail("primitive guard must precede relative path I/O")

    monkeypatch.setattr(Path, "cwd", classmethod(no_cwd))
    monkeypatch.delattr(os, "O_NOFOLLOW")
    rejected(
        "input_unsupported",
        lambda: capture_upload_input(
            Path("relative"), Path("manifest"), SECRET, end=time.monotonic() + 30
        ),
    )


def test_observed_open_does_not_relabel_real_permission_failure(tmp_path, monkeypatch):
    import errno

    root, manifest, _ = fixture(tmp_path)
    observation = capture(root, manifest)

    def permission_denied(path):
        raise OSError(errno.EACCES, "synthetic permission denial")

    monkeypatch.setattr(dataset_files, "directory_chain", permission_denied)
    rejected("file_unreadable", observation.recheck)
