import os
import tracemalloc

import pytest

from yorunge.adapters.input_files import BLOCK_BYTES, MAX_INPUT_BYTES, DescriptorInputs
from yorunge.application.execution import ExecutionBudget
from yorunge.domain.errors import YorungeError


class Clock:
    elapsed = 0

    def monotonic(self):
        return self.elapsed


def budget():
    return ExecutionBudget(Clock(), 0)


@pytest.mark.parametrize(
    "path", ["/outside", "../x", "a/../x", "a//x", "./x", "a/./x", "a/", "", "a\\x"]
)
def test_raw_unsafe_input_reference_rejected_before_read(tmp_path, monkeypatch, path):
    monkeypatch.setattr(os, "read", lambda *args: pytest.fail("unsafe content read"))
    with pytest.raises(YorungeError) as failure:
        DescriptorInputs().bind(tmp_path, (("manifest", path),), budget())
    assert failure.value.code == "input_invalid"


@pytest.mark.parametrize("target", ["root", "parent", "leaf", "fifo"])
def test_component_swap_before_open_never_reads_external_content_and_closes_descriptors(
    tmp_path,
    monkeypatch,
    target,
):
    root = tmp_path / "inputs"
    root.mkdir()
    middle = root / "nested"
    middle.mkdir()
    leaf = middle / "data"
    leaf.write_bytes(b"safe")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "data").write_bytes(b"sentinel")
    live = set()
    original_open, original_close, original_dup = os.open, os.close, os.dup
    swapped = False

    def opening(path, flags, *args, **kwargs):
        nonlocal swapped
        name = {"root": "inputs", "parent": "nested", "leaf": "data", "fifo": "data"}[target]
        if path == name and not swapped:
            swapped = True
            if target == "root":
                root.rename(tmp_path / "original")
                root.symlink_to(outside, target_is_directory=True)
            elif target == "parent":
                middle.rename(root / "original")
                middle.symlink_to(outside, target_is_directory=True)
            else:
                leaf.unlink()
                if target == "fifo":
                    os.mkfifo(leaf)
                else:
                    leaf.symlink_to(outside / "data")
        result = original_open(path, flags, *args, **kwargs)
        live.add(result)
        return result

    def closing(fd):
        original_close(fd)
        live.discard(fd)

    def duplicate(fd):
        result = original_dup(fd)
        live.add(result)
        return result

    monkeypatch.setattr(os, "open", opening)
    monkeypatch.setattr(os, "close", closing)
    monkeypatch.setattr(os, "dup", duplicate)
    monkeypatch.setattr(os, "supports_dir_fd", {*os.supports_dir_fd, opening})
    monkeypatch.setattr(os, "read", lambda *args: pytest.fail("sentinel/FIFO read"))
    with pytest.raises(YorungeError):
        DescriptorInputs().bind(root, (("manifest", "nested/data"),), budget())
    assert swapped
    assert live == set()


@pytest.mark.parametrize("change", ["content", "root"])
def test_change_during_hash_is_rejected(tmp_path, monkeypatch, change):
    root = tmp_path / "inputs"
    root.mkdir()
    file = root / "data"
    file.write_bytes(b"a" * (BLOCK_BYTES + 1))
    original = os.read
    moved = False

    def reading(fd, size):
        nonlocal moved
        result = original(fd, size)
        if not moved:
            moved = True
            if change == "content":
                file.write_bytes(b"b" * (BLOCK_BYTES + 1))
            else:
                root.rename(tmp_path / "original")
                root.mkdir()
                (root / "data").write_bytes(b"a" * (BLOCK_BYTES + 1))
        return result

    monkeypatch.setattr(os, "read", reading)
    with pytest.raises(YorungeError) as failure:
        DescriptorInputs().bind(root, (("manifest", "data"),), budget())
    assert failure.value.code == "input_changed"


def test_size_and_total_time_budget_are_enforced_without_partial_hash(tmp_path, monkeypatch):
    file = tmp_path / "data"
    with file.open("wb") as stream:
        stream.truncate(MAX_INPUT_BYTES + 1)
    with pytest.raises(YorungeError) as failure:
        DescriptorInputs().bind(tmp_path, (("data", "data"),), budget())
    assert failure.value.code == "input_budget_exceeded"
    file.write_bytes(b"a" * (BLOCK_BYTES + 1))
    clock = Clock()
    current_budget = ExecutionBudget(clock, 0)
    original = os.read

    def slow(fd, size):
        result = original(fd, size)
        clock.elapsed = 30
        return result

    monkeypatch.setattr(os, "read", slow)
    with pytest.raises(YorungeError) as failure:
        DescriptorInputs().bind(tmp_path, (("data", "data"),), current_budget)
    assert failure.value.code == "execution_timeout"


@pytest.mark.parametrize("size", [16, 256, 1024])
def test_large_hash_uses_bounded_memory_and_complete_content(tmp_path, size):
    file = tmp_path / "data"
    with file.open("wb") as stream:
        stream.truncate(size * 1024 * 1024)
    tracemalloc.start()
    try:
        _, inputs = DescriptorInputs().bind(tmp_path, (("data", "data"),), budget())
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert inputs[0].size == size * 1024 * 1024
    assert peak < 8 * 1024 * 1024


def test_missing_safe_open_support_fails_before_io(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "supports_dir_fd", set())
    monkeypatch.setattr(os, "read", lambda *args: pytest.fail("unsupported read"))
    with pytest.raises(YorungeError) as failure:
        DescriptorInputs().bind(tmp_path, (), budget())
    assert failure.value.code == "input_unsupported"


@pytest.mark.parametrize("point", ["root", "dup-root"])
def test_initial_stat_io_failure_closes_the_opened_descriptor(tmp_path, monkeypatch, point):
    import errno

    (tmp_path / "data").write_bytes(b"data")
    original_open, original_dup, original_close, original_stat = os.open, os.dup, os.close, os.fstat
    live, duplicated = set(), set()
    injected = False

    def opening(*args, **kwargs):
        result = original_open(*args, **kwargs)
        live.add(result)
        return result

    def duplicate(fd):
        result = original_dup(fd)
        live.add(result)
        duplicated.add(result)
        return result

    def closing(fd):
        original_close(fd)
        live.discard(fd)

    def stating(fd):
        nonlocal injected
        if not injected and (point == "root" or fd in duplicated):
            injected = True
            raise OSError(errno.EIO, "fixture stat failure")
        return original_stat(fd)

    monkeypatch.setattr(os, "open", opening)
    monkeypatch.setattr(os, "dup", duplicate)
    monkeypatch.setattr(os, "close", closing)
    monkeypatch.setattr(os, "fstat", stating)
    monkeypatch.setattr(os, "supports_dir_fd", {*os.supports_dir_fd, opening})
    try:
        with pytest.raises(YorungeError) as failure:
            DescriptorInputs().bind(tmp_path, (("data", "data"),), budget())
        assert failure.value.code == "input_invalid"
        assert injected
        assert live == set()
    finally:
        for fd in tuple(live):
            original_close(fd)
