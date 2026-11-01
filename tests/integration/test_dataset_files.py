"""Real local trees, descriptor races and complete bounded byte comparison."""

import asyncio
import errno
import hashlib
import os
import socket
import stat
import unicodedata
from pathlib import Path

import pytest

from yorunge.adapters import dataset_files as module
from yorunge.adapters.dataset_files import open_dataset
from yorunge.application.datasets import DatasetBudget, compare_manifests, decode_manifest
from yorunge.domain import dataset_manifest as policy
from yorunge.domain.errors import MESSAGES, ManifestMismatch, YorungeError


class Clock:
    value = 0.0

    def now(self):
        return self.value


def scan(root, budget=None):
    current = DatasetBudget() if budget is None else budget
    with open_dataset(root, current) as tree:
        return tree.scan()


def track_descriptors(monkeypatch):
    live = set()
    peak = [0]
    original_open, original_close, original_dup = os.open, os.close, os.dup

    def opening(*args, **kwargs):
        fd = original_open(*args, **kwargs)
        live.add(fd)
        peak[0] = max(peak[0], len(live))
        return fd

    def closing(fd):
        original_close(fd)
        live.remove(fd)

    def duplicate(fd):
        result = original_dup(fd)
        live.add(result)
        peak[0] = max(peak[0], len(live))
        return result

    monkeypatch.setattr(os, "open", opening)
    monkeypatch.setattr(os, "close", closing)
    monkeypatch.setattr(os, "dup", duplicate)
    monkeypatch.setattr(os, "supports_dir_fd", {*os.supports_dir_fd, opening})
    return live, peak


def test_complete_tree_hashes_names_hidden_files_hardlinks_and_empty_directories(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "a").write_bytes(b"abc")
    os.link(root / "a", root / "b")
    (root / "c").write_bytes(b"abc")
    (root / "empty").mkdir()
    (root / "nested").mkdir()
    (root / "nested/.hidden").write_bytes(b"")
    manifest = scan(root)
    assert manifest.file_count == 4
    assert manifest.total_bytes == 9
    assert [file.path for file in manifest.files] == ["a", "b", "c", "nested/.hidden"]
    assert [file.sha256 for file in manifest.files[:3]] == [hashlib.sha256(b"abc").hexdigest()] * 3
    assert manifest.files[-1].sha256 == hashlib.sha256(b"").hexdigest()
    clone = tmp_path / "clone"
    clone.mkdir()
    for file in manifest.files:
        destination = clone / file.path
        destination.parent.mkdir(exist_ok=True)
        destination.write_bytes(b"" if file.size == 0 else b"abc")
    assert scan(clone) == manifest
    result = compare_manifests(manifest, scan(clone), DatasetBudget())
    assert result.matches is True
    assert result.unicode_version == unicodedata.unidata_version


def test_empty_tree_and_added_empty_directory_have_same_content_identity(tmp_path):
    before = scan(tmp_path)
    (tmp_path / "empty").mkdir()
    assert scan(tmp_path) == before


def test_inside_name_linked_to_outside_regular_inode_is_its_own_file_identity(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.write_bytes(b"abc")
    os.link(outside, root / "inside")
    manifest = scan(root)
    assert [(item.path, item.size) for item in manifest.files] == [("inside", 3)]


def test_same_size_modification_missing_and_unexpected_have_independent_counts(tmp_path):
    (tmp_path / "changed").write_bytes(b"abc")
    (tmp_path / "missing").write_bytes(b"x")
    expected = scan(tmp_path)
    (tmp_path / "changed").write_bytes(b"xyz")
    (tmp_path / "missing").unlink()
    (tmp_path / "unexpected").write_bytes(b"new")
    actual = scan(tmp_path)
    budget = DatasetBudget()
    with pytest.raises(ManifestMismatch) as failure:
        compare_manifests(expected, actual, budget)
    assert failure.value.exit_code == 7
    assert failure.value.envelope()["details"] == {
        "expected_digest": expected.digest,
        "actual_digest": actual.digest,
        "missing_file_count": 1,
        "unexpected_file_count": 1,
        "changed_file_count": 1,
    }
    assert str(tmp_path) not in str(failure.value.envelope())


@pytest.mark.parametrize("kind", ["root", "ancestor", "leaf", "dangling", "fifo", "socket"])
def test_symlink_and_special_files_are_rejected_without_content_reads(tmp_path, monkeypatch, kind):
    root = tmp_path / "source"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "data").write_bytes(b"sentinel")
    local_socket = None
    if kind == "root":
        root.rmdir()
        root.symlink_to(outside, target_is_directory=True)
    elif kind == "ancestor":
        (tmp_path / "alias").symlink_to(outside, target_is_directory=True)
        (outside / "child").mkdir()
        root = tmp_path / "alias/child"
    elif kind in ("leaf", "dangling"):
        (root / "data").symlink_to(outside / ("data" if kind == "leaf" else "missing"))
    elif kind == "fifo":
        os.mkfifo(root / "pipe")
    else:
        local_socket = socket.socket(socket.AF_UNIX)
        monkeypatch.chdir(root)
        local_socket.bind("socket")
    monkeypatch.setattr(os, "read", lambda *args: pytest.fail("special content read"))
    try:
        with pytest.raises(YorungeError) as failure:
            scan(root)
        assert failure.value.code == "input_invalid"
    finally:
        if local_socket is not None:
            local_socket.close()


@pytest.mark.parametrize("mode", ["different-device", "character-device"])
def test_observed_device_boundary_and_device_type_are_checked_before_open(
    tmp_path, monkeypatch, mode
):
    (tmp_path / "data").write_bytes(b"not-read")
    original = os.stat

    def stating(path, *args, **kwargs):
        info = original(path, *args, **kwargs)
        if path == "data" and "dir_fd" in kwargs:
            values = list(info)
            if mode == "different-device":
                values[2] += 1
            else:
                values[0] = stat.S_IFCHR | 0o600
            return os.stat_result(values)
        return info

    monkeypatch.setattr(os, "stat", stating)
    monkeypatch.setattr(os, "supports_dir_fd", {*os.supports_dir_fd, stating})
    monkeypatch.setattr(os, "supports_follow_symlinks", {*os.supports_follow_symlinks, stating})
    monkeypatch.setattr(os, "read", lambda *args: pytest.fail("device content read"))
    with pytest.raises(YorungeError) as failure:
        scan(tmp_path)
    assert failure.value.code == "input_invalid"


@pytest.mark.parametrize(
    "mutation", ["same-size", "grow", "truncate", "replace", "root", "add-name"]
)
def test_changes_during_hash_reject_complete_manifest_and_close_fds(
    tmp_path, monkeypatch, mutation
):
    root = tmp_path / "source"
    root.mkdir()
    item = root / "data"
    item.write_bytes(b"a" * (policy.HASH_BLOCK_BYTES + 1))
    live, peak = track_descriptors(monkeypatch)
    original_read = os.read
    changed = False

    def reading(fd, size):
        nonlocal changed
        block = original_read(fd, size)
        if not changed:
            changed = True
            mutate = {
                "same-size": lambda: item.write_bytes(b"b" * (policy.HASH_BLOCK_BYTES + 1)),
                "grow": lambda: item.write_bytes(b"a" * (policy.HASH_BLOCK_BYTES + 2)),
                "truncate": lambda: item.write_bytes(b"a"),
                "replace": lambda: replace_file(item),
                "root": lambda: root.rename(tmp_path / "moved"),
                "add-name": lambda: (root / "new").write_bytes(b""),
            }
            mutate[mutation]()
        return block

    monkeypatch.setattr(os, "read", reading)
    with pytest.raises(YorungeError) as failure:
        scan(root)
    assert failure.value.code == "input_changed"
    assert live == set()
    assert peak[0] <= 64


def replace_file(path):
    path.unlink()
    path.write_bytes(b"replacement")


def test_final_pass_detects_first_file_changed_while_later_file_is_read(tmp_path, monkeypatch):
    first, last = tmp_path / "a", tmp_path / "b"
    first.write_bytes(b"first")
    last.write_bytes(b"last")
    original = os.read
    reads = 0

    def reading(fd, size):
        nonlocal reads
        result = original(fd, size)
        reads += 1
        if reads == 2:
            first.write_bytes(b"other")
        return result

    monkeypatch.setattr(os, "read", reading)
    with pytest.raises(YorungeError) as failure:
        scan(tmp_path)
    assert failure.value.code == "input_changed"


@pytest.mark.parametrize("point", ["before-open", "during-fstat", "during-read", "cancel"])
def test_io_failure_and_real_cancellation_close_all_owned_descriptors(tmp_path, monkeypatch, point):
    (tmp_path / "data").write_bytes(b"abc")
    live, peak = track_descriptors(monkeypatch)
    original_open, original_fstat, original_read = os.open, os.fstat, os.read
    cancellation = asyncio.CancelledError()

    def opening(path, *args, **kwargs):
        if point == "before-open" and path == "data":
            raise PermissionError(errno.EACCES, "not public")
        return original_open(path, *args, **kwargs)

    def stating(fd):
        if point == "during-fstat":
            raise OSError(errno.EIO, "not public")
        return original_fstat(fd)

    def reading(fd, size):
        if point == "cancel":
            raise cancellation
        if point == "during-read":
            raise OSError(errno.EIO, "not public")
        return original_read(fd, size)

    monkeypatch.setattr(os, "open", opening)
    monkeypatch.setattr(os, "supports_dir_fd", {*os.supports_dir_fd, opening})
    monkeypatch.setattr(os, "fstat", stating)
    monkeypatch.setattr(os, "read", reading)
    if point == "cancel":
        with pytest.raises(asyncio.CancelledError) as failure:
            scan(tmp_path)
        assert failure.value is cancellation
    else:
        with pytest.raises(YorungeError) as failure:
            scan(tmp_path)
        assert failure.value.code == "file_unreadable"
        assert "not public" not in str(failure.value.envelope())
    assert live == set()
    assert peak[0] <= 64


def test_cleanup_error_does_not_replace_real_cancelled_error(tmp_path, monkeypatch):
    (tmp_path / "data").write_bytes(b"abc")
    original_close = os.close
    cancellation = asyncio.CancelledError()

    def closing(fd):
        original_close(fd)
        raise OSError(errno.EIO, "not public")

    def reading(fd, size):
        monkeypatch.setattr(os, "close", closing)
        raise cancellation

    monkeypatch.setattr(os, "read", reading)
    with pytest.raises(asyncio.CancelledError) as failure:
        scan(tmp_path)
    assert failure.value is cancellation
    assert failure.value.__notes__ == [MESSAGES["file_unreadable"]] * 2


def test_exact_content_limit_reads_no_sentinel_and_hardlinks_count_twice(tmp_path, monkeypatch):
    (tmp_path / "a").write_bytes(b"abc")
    monkeypatch.setattr(policy, "MAX_CONTENT_BYTES", 3)
    original = os.read
    requests = []

    def reading(fd, size):
        requests.append(size)
        return original(fd, size)

    monkeypatch.setattr(os, "read", reading)
    assert scan(tmp_path).total_bytes == 3
    assert requests == [3]
    os.link(tmp_path / "a", tmp_path / "b")
    requests.clear()
    with pytest.raises(YorungeError) as failure:
        scan(tmp_path)
    assert failure.value.code == "input_budget_exceeded"
    assert requests == [3]


def test_real_oversized_sparse_file_is_rejected_before_read(tmp_path, monkeypatch):
    with (tmp_path / "large").open("wb") as stream:
        stream.truncate(1024**3 + 1)
    monkeypatch.setattr(os, "read", lambda *args: pytest.fail("over-budget read"))
    with pytest.raises(YorungeError) as failure:
        scan(tmp_path)
    assert failure.value.code == "input_budget_exceeded"


@pytest.mark.parametrize("kind", ["files", "directories"])
def test_count_limits_include_empty_directories_and_stop_before_unbounded_inventory(
    tmp_path, monkeypatch, kind
):
    if kind == "files":
        monkeypatch.setattr(policy, "MAX_FILES", 2)
        for name in ("a", "b", "c"):
            (tmp_path / name).write_bytes(b"")
    else:
        monkeypatch.setattr(policy, "MAX_DIRECTORIES", 2)
        for name in ("a", "b"):
            (tmp_path / name).mkdir()
    with pytest.raises(YorungeError) as failure:
        scan(tmp_path)
    assert failure.value.code == "dataset_limit_exceeded"


def test_maximum_depth_observation_keeps_fewer_than_64_descriptors(tmp_path, monkeypatch):
    parent = tmp_path
    for _ in range(31):
        parent /= "d"
        parent.mkdir()
    (parent / "file").write_bytes(b"abc")
    live, peak = track_descriptors(monkeypatch)
    assert scan(tmp_path).file_count == 1
    assert live == set()
    assert peak[0] <= 64


def test_monotonic_deadline_includes_hash_and_final_empty_tree_gate(tmp_path, monkeypatch):
    (tmp_path / "data").write_bytes(b"abc")
    clock = Clock()
    budget = DatasetBudget(clock.now)
    original = os.read

    def reading(fd, size):
        block = original(fd, size)
        clock.value = 30
        return block

    monkeypatch.setattr(os, "read", reading)
    with pytest.raises(YorungeError) as failure:
        scan(tmp_path, budget)
    assert failure.value.code == "dataset_timeout"


def test_missing_descriptor_support_precedes_even_cwd_and_root_io(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "supports_fd", set())
    monkeypatch.setattr(os, "open", lambda *args, **kwargs: pytest.fail("unsupported open"))
    monkeypatch.setattr(Path, "cwd", lambda: pytest.fail("unsupported cwd"))
    budget = DatasetBudget()
    with pytest.raises(YorungeError) as failure:
        scan(Path("relative"), budget)
    assert failure.value.code == "input_unsupported"


def test_manifest_read_is_external_strict_and_unchanged(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "a").write_bytes(b"abc")
    expected = scan(root)
    target = tmp_path / "manifest.json"
    target.write_bytes(expected.encoded())
    budget = DatasetBudget()
    with open_dataset(root, budget) as tree:
        saved = decode_manifest(tree.read_manifest(target), budget)
        result = compare_manifests(saved, tree.scan(), budget)
    assert result.manifest_digest == expected.digest
    assert target.read_bytes() == expected.encoded()


@pytest.mark.parametrize("kind", ["inside", "symlink", "fifo", "parent-symlink", "oversize"])
def test_invalid_manifest_location_never_becomes_hash_input(tmp_path, monkeypatch, kind):
    root = tmp_path / "source"
    root.mkdir()
    target = tmp_path / "manifest.json"
    if kind == "inside":
        target = root / "manifest.json"
        target.write_bytes(b"{}")
    elif kind == "symlink":
        outside = tmp_path / "outside"
        outside.write_bytes(b"{}")
        target.symlink_to(outside)
    elif kind == "fifo":
        os.mkfifo(target)
    elif kind == "parent-symlink":
        (tmp_path / "alias").symlink_to(root, target_is_directory=True)
        target = tmp_path / "alias/manifest.json"
    else:
        with target.open("wb") as stream:
            stream.truncate(policy.MAX_MANIFEST_BYTES + 1)
    monkeypatch.setattr(os, "read", lambda *args: pytest.fail("invalid manifest read"))
    budget = DatasetBudget()
    with open_dataset(root, budget) as tree:
        with pytest.raises(YorungeError) as failure:
            tree.read_manifest(target)
    assert failure.value.code == ("manifest_invalid" if kind == "oversize" else "input_invalid")


@pytest.mark.parametrize("point", ["root", "parent", "leaf", "fifo"])
def test_component_swap_between_observation_and_open_never_reads_outside(
    tmp_path, monkeypatch, point
):
    root = tmp_path / "source"
    root.mkdir()
    parent = root / "nested"
    parent.mkdir()
    item = parent / "data"
    item.write_bytes(b"safe")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "data").write_bytes(b"sentinel")
    live, peak = track_descriptors(monkeypatch)
    original = os.open
    swapped = False

    def swap():
        if point == "root":
            root.rename(tmp_path / "moved")
            root.symlink_to(outside, target_is_directory=True)
        elif point == "parent":
            parent.rename(root / "moved")
            parent.symlink_to(outside, target_is_directory=True)
        else:
            item.unlink()
            if point == "fifo":
                os.mkfifo(item)
            else:
                item.symlink_to(outside / "data")

    def opening(path, *args, **kwargs):
        nonlocal swapped
        trigger = {"root": "source", "parent": "nested", "leaf": "data", "fifo": "data"}[point]
        if path == trigger and not swapped:
            swapped = True
            swap()
        return original(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", opening)
    monkeypatch.setattr(os, "supports_dir_fd", {*os.supports_dir_fd, opening})
    monkeypatch.setattr(os, "read", lambda *args: pytest.fail("outside/FIFO content read"))
    with pytest.raises(YorungeError) as failure:
        scan(root)
    assert failure.value.code == ("input_invalid" if point == "root" else "input_changed")
    assert swapped
    assert live == set()
    assert peak[0] <= 64


@pytest.mark.parametrize("change", ["empty-membership", "ancestor"])
def test_final_observation_rejects_changes_after_walk_before_return(tmp_path, monkeypatch, change):
    ancestor = tmp_path / "parent"
    ancestor.mkdir()
    root = ancestor / "source"
    root.mkdir()
    (root / "data").write_bytes(b"abc")
    (root / "empty").mkdir()
    original = module.DatasetTree.recheck

    def checking(tree):
        if change == "empty-membership":
            (root / "empty/new").mkdir()
        else:
            ancestor.rename(tmp_path / "moved")
            ancestor.mkdir()
            root.mkdir()
            (root / "data").write_bytes(b"abc")
            (root / "empty").mkdir()
        original(tree)

    live, peak = track_descriptors(monkeypatch)
    monkeypatch.setattr(module.DatasetTree, "recheck", checking)
    with pytest.raises(YorungeError) as failure:
        scan(root)
    assert failure.value.code == "input_changed"
    assert live == set()
    assert peak[0] <= 64


@pytest.mark.parametrize("change", ["content", "remove", "parent", "truncate"])
def test_manifest_read_rejects_observed_leaf_and_parent_changes(tmp_path, monkeypatch, change):
    root = tmp_path / "source"
    root.mkdir()
    output_parent = tmp_path / "reports"
    output_parent.mkdir()
    target = output_parent / "manifest.json"
    original_bytes = scan(root).encoded()
    target.write_bytes(original_bytes)
    original = os.read
    changed = False

    def reading(fd, size):
        nonlocal changed
        result = original(fd, size)
        if not changed:
            changed = True
            if change == "content":
                target.write_bytes(original_bytes.replace(b"sha256", b"SHA256"))
            elif change == "remove":
                target.unlink()
            elif change == "parent":
                output_parent.rename(tmp_path / "moved")
                output_parent.mkdir()
                target.write_bytes(original_bytes)
            else:
                target.write_bytes(b"")
        return result

    monkeypatch.setattr(os, "read", reading)
    budget = DatasetBudget()
    with open_dataset(root, budget) as tree:
        with pytest.raises(YorungeError) as failure:
            tree.read_manifest(target)
    assert changed
    assert failure.value.code == "input_changed"


def test_different_outside_parent_with_same_string_prefix_is_allowed(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    sibling = tmp_path / "source-reports"
    sibling.mkdir()
    target = sibling / "manifest.json"
    expected = scan(root)
    target.write_bytes(expected.encoded())
    budget = DatasetBudget()
    with open_dataset(root, budget) as tree:
        assert decode_manifest(tree.read_manifest(target), budget) == expected


def test_decode_and_compare_have_their_own_final_deadline_gates(tmp_path):
    manifest = scan(tmp_path)
    clock = Clock()
    budget = DatasetBudget(clock.now)
    clock.value = 30
    content = manifest.encoded()
    with pytest.raises(YorungeError) as decoding:
        decode_manifest(content, budget)
    assert decoding.value.code == "dataset_timeout"
    with pytest.raises(YorungeError) as comparing:
        compare_manifests(manifest, manifest, budget)
    assert comparing.value.code == "dataset_timeout"


@pytest.mark.parametrize("kind", ["files", "directories"])
def test_real_inventory_capacity_minus_one_exact_and_plus_one(tmp_path, kind):
    count = 4095 if kind == "files" else 4094

    def create(index):
        path = tmp_path / f"n{index:04}"
        if kind == "files":
            path.write_bytes(b"")
        else:
            path.mkdir()

    for index in range(count):
        create(index)
    budget = DatasetBudget()
    with open_dataset(tmp_path, budget) as tree:
        assert tree.scan().file_count == (count if kind == "files" else 0)
        assert tree.inventory.directory_count == (1 if kind == "files" else 4095)
    create(count)
    budget = DatasetBudget()
    with open_dataset(tmp_path, budget) as tree:
        assert tree.scan().file_count == (4096 if kind == "files" else 0)
        assert tree.inventory.directory_count == (1 if kind == "files" else 4096)
    create(count + 1)
    with pytest.raises(YorungeError) as failure:
        scan(tmp_path)
    assert failure.value.code == "dataset_limit_exceeded"


@pytest.mark.parametrize(
    "code,exit_code",
    [
        ("dataset_limit_exceeded", 2),
        ("dataset_timeout", 2),
        ("manifest_invalid", 2),
        ("manifest_output_exists", 2),
        ("manifest_write_failed", 2),
        ("manifest_write_uncertain", 5),
        ("manifest_mismatch", 7),
    ],
)
def test_dataset_error_catalog_has_fixed_messages_exits_and_safe_general_envelope(code, exit_code):
    error = YorungeError(code)
    assert error.exit_code == exit_code
    assert error.envelope()["message"] == MESSAGES[code]
    assert error.envelope()["operation_id"] is None
    assert error.envelope()["retryable"] is False
    assert error.envelope()["details"] == {}


@pytest.mark.parametrize("count", [True, -1, 4097, 1.0])
def test_mismatch_never_accepts_unbounded_or_coerced_details(count):
    with pytest.raises(ValueError):
        ManifestMismatch("a" * 64, "b" * 64, count, 0, 0)


@pytest.mark.parametrize("point", ["initial-chain", "final-relative"])
def test_shared_walk_cleanup_preserves_active_cancelled_error(tmp_path, monkeypatch, point):
    (tmp_path / "data").write_bytes(b"abc")
    live, peak = track_descriptors(monkeypatch)
    original_stat, original_close = os.fstat, os.close
    original_recheck = module.DatasetTree._recheck_file
    cancellation = asyncio.CancelledError()
    enabled = point == "initial-chain"
    raised = False

    def stating(fd):
        nonlocal raised
        if enabled and not raised:
            raised = True
            raise cancellation
        return original_stat(fd)

    def closing(fd):
        original_close(fd)
        if raised:
            raise OSError(errno.EIO, "not public")

    def rechecking(tree, item):
        nonlocal enabled
        enabled = True
        original_recheck(tree, item)

    monkeypatch.setattr(os, "fstat", stating)
    monkeypatch.setattr(os, "close", closing)
    monkeypatch.setattr(module.DatasetTree, "_recheck_file", rechecking)
    with pytest.raises(asyncio.CancelledError) as failure:
        scan(tmp_path)
    assert failure.value is cancellation
    assert raised
    assert all(note == MESSAGES["file_unreadable"] for note in cancellation.__notes__)
    assert live == set()
    assert peak[0] <= 64


@pytest.mark.parametrize("point", ["initial-chain", "relative-directory", "relative-leaf"])
def test_shared_walk_parent_close_failure_cannot_orphan_child_or_leaf(tmp_path, monkeypatch, point):
    root = tmp_path / "source"
    root.mkdir()
    nested = root / "nested"
    nested.mkdir()
    (nested / "data").write_bytes(b"abc")
    live, peak = track_descriptors(monkeypatch)
    original_close = os.close
    original_recheck = module.DatasetTree._recheck_file
    enabled = point == "initial-chain"
    injected = False
    close_calls = 0

    def closing(fd):
        nonlocal injected, close_calls
        original_close(fd)
        if enabled:
            close_calls += 1
            trigger = 2 if point == "relative-leaf" else 1
            if close_calls == trigger and not injected:
                injected = True
                raise OSError(errno.EIO, "not public")

    def rechecking(tree, item):
        nonlocal enabled
        enabled = True
        original_recheck(tree, item)

    monkeypatch.setattr(os, "close", closing)
    monkeypatch.setattr(module.DatasetTree, "_recheck_file", rechecking)
    with pytest.raises(YorungeError) as failure:
        scan(root)
    assert failure.value.code == "file_unreadable"
    assert injected
    assert live == set()
    assert peak[0] <= 64


@pytest.mark.parametrize("point", ["initial-chain", "file", "final-relative"])
def test_unrelated_caller_exception_cannot_hide_normal_close_failure(tmp_path, monkeypatch, point):
    (tmp_path / "data").write_bytes(b"abc")
    live, peak = track_descriptors(monkeypatch)
    original_close, original_read = os.close, os.read
    original_recheck = module.DatasetTree._recheck_file
    enabled = point == "initial-chain"
    injected = False

    def closing(fd):
        nonlocal injected
        original_close(fd)
        if enabled and not injected:
            injected = True
            raise OSError(errno.EIO, "not public")

    def reading(fd, size):
        nonlocal enabled
        result = original_read(fd, size)
        if point == "file":
            enabled = True
        return result

    def rechecking(tree, item):
        nonlocal enabled
        if point == "final-relative":
            enabled = True
        original_recheck(tree, item)

    monkeypatch.setattr(os, "close", closing)
    monkeypatch.setattr(os, "read", reading)
    monkeypatch.setattr(module.DatasetTree, "_recheck_file", rechecking)
    try:
        raise ValueError("unrelated caller failure")
    except ValueError as previous:
        with pytest.raises(YorungeError) as failure:
            scan(tmp_path)
        assert failure.value.code == "file_unreadable"
        assert not hasattr(previous, "__notes__")
    assert injected
    assert live == set()
    assert peak[0] <= 64
