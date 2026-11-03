"""Real descriptor byte-source ownership, mutation, deadline and cancellation tests."""

import asyncio
import copy
import hashlib
import os
import pickle
import time
from functools import partial

import pytest

from yorunge.adapters import storage_source
from yorunge.adapters.storage_source import DescriptorByteSource
from yorunge.domain.dataset_manifest import DatasetFile
from yorunge.domain.dataset_upload import UploadRoot
from yorunge.domain.errors import YorungeError

CHUNK = 1024 * 1024


@pytest.fixture
def source_file(tmp_path):
    root = (tmp_path / "root").resolve()
    root.mkdir()
    path = root / "payload.bin"
    data = b"a" * (2 * CHUNK + 31)
    path.write_bytes(data)
    info = root.stat()
    identity = UploadRoot(anchor=str(root), device=info.st_dev, inode=info.st_ino)
    entry = DatasetFile(path=path.name, size=len(data), sha256=hashlib.sha256(data).hexdigest())
    return root, path, data, identity, entry


def make_source(fixture, **changes):
    _, _, _, root, file = fixture
    return DescriptorByteSource(
        changes.get("root", root),
        changes.get("file", file),
        deadline=changes.get("deadline", time.monotonic() + 120),
    )


def test_construction_has_no_file_content_or_descriptor_io(source_file, monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail("descriptor source construction performed I/O")

    monkeypatch.setattr(storage_source, "directory_chain", denied)
    monkeypatch.setattr(storage_source.os, "read", denied)
    source = make_source(source_file)
    assert source.sent_bytes == 0 and source.sent_sha256 is None
    assert source._root_fd is source._file_fd is None
    assert source_file[1].name not in repr(source)


def test_stream_has_exact_blocks_counts_hash_and_no_worker_tasks(source_file):
    source = make_source(source_file)

    async def run():
        chunks = []
        async with source:
            async for chunk in source.chunks():
                assert 0 < len(chunk) <= CHUNK
                assert asyncio.all_tasks() == {asyncio.current_task()}
                chunks.append(chunk)
        return chunks

    chunks = asyncio.run(run())
    assert list(map(len, chunks)) == [CHUNK, CHUNK, 31]
    assert b"".join(chunks) == source_file[2]
    assert source.complete and source.sent_bytes == len(source_file[2])
    assert source.sent_sha256 == source_file[4].sha256
    assert source._file_fd is source._root_fd is None


@pytest.mark.parametrize(
    "kind",
    ["symlink", "ancestor-symlink", "fifo", "directory", "wrong-root", "wrong-size", "wrong-hash"],
)
def test_invalid_or_changed_binding_is_rejected_and_all_fds_close(source_file, kind):
    root, path, _, identity, entry = source_file
    if kind == "symlink":
        path.rename(root / "other.bin")
        path.symlink_to("other.bin")
    elif kind == "ancestor-symlink":
        (root / "alias").symlink_to(root, target_is_directory=True)
        entry = entry.model_copy(update={"path": "alias/payload.bin"})
    elif kind == "fifo":
        path.unlink()
        os.mkfifo(path)
    elif kind == "directory":
        path.unlink()
        path.mkdir()
    elif kind == "wrong-root":
        identity = identity.model_copy(update={"inode": identity.inode + 1})
    elif kind == "wrong-size":
        entry = entry.model_copy(update={"size": entry.size + 1})
    else:
        entry = entry.model_copy(update={"sha256": "0" * 64})
    source = make_source(source_file, root=identity, file=entry)

    async def run():
        async for _ in source.chunks():
            pass

    rejected_call = partial(asyncio.run, run())
    with pytest.raises(YorungeError) as failure:
        rejected_call()
    assert failure.value.code == "input_changed"
    assert not source.complete and source.sent_sha256 is None
    assert source._file_fd is source._root_fd is None


@pytest.mark.parametrize(
    "change", ["edit", "truncate", "grow", "replace", "rename-root", "replace-ancestor"]
)
def test_mutation_after_first_block_is_detected(source_file, change):
    root, path, data, _, _ = source_file
    source = make_source(source_file)

    async def run():
        stream = source.chunks()
        assert len(await anext(stream)) == CHUNK
        if change == "edit":
            with path.open("r+b") as file:
                file.seek(CHUNK)
                file.write(b"b")
        elif change == "truncate":
            path.write_bytes(b"short")
        elif change == "grow":
            with path.open("ab") as file:
                file.write(b"extra")
        elif change == "replace":
            path.unlink()
            path.write_bytes(data)
        elif change == "rename-root":
            root.rename(root.with_name("old-root"))
            root.mkdir()
        else:
            parent = root.parent
            moved = parent.with_name(parent.name + "-moved")
            parent.rename(moved)
            parent.mkdir()
            (moved / root.name).rename(root)
        async for _ in stream:
            pass

    rejected_call = partial(asyncio.run, run())
    with pytest.raises(YorungeError) as failure:
        rejected_call()
    assert failure.value.code == "input_changed"
    assert not source.complete and source._file_fd is source._root_fd is None


def test_early_close_is_normal_and_does_not_claim_complete_or_leave_fd(source_file):
    source = make_source(source_file)

    async def run():
        async with source:
            assert len(await anext(source.chunks())) == CHUNK
            descriptor = source._file_fd
        with pytest.raises(OSError):
            os.fstat(descriptor)
        await source.aclose()

    asyncio.run(run())
    assert source.sent_bytes == CHUNK and not source.complete
    assert source.sent_sha256 is None


def test_actual_task_cancellation_is_reraised_after_source_cleanup(source_file, monkeypatch):
    source = make_source(source_file)
    original = storage_source.os.read
    calls = 0

    def cancel_read(descriptor, length):
        nonlocal calls
        value = original(descriptor, length)
        if descriptor == source._file_fd:
            calls += 1
            asyncio.current_task().cancel()
        return value

    monkeypatch.setattr(storage_source.os, "read", cancel_read)

    async def consume():
        async with source:
            async for _ in source.chunks():
                pass

    async def run():
        task = asyncio.create_task(consume())
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())
    assert calls == 1 and source.sent_bytes == CHUNK
    assert not source.complete and source._file_fd is source._root_fd is None


def test_cross_task_use_and_close_cannot_steal_ownership(source_file):
    source = make_source(source_file)

    async def run():
        async with source:
            stream = source.chunks()
            await anext(stream)

            async def wrong_task():
                with pytest.raises(YorungeError):
                    await anext(stream)
                with pytest.raises(YorungeError):
                    await source.aclose()

            await asyncio.create_task(wrong_task())
            assert source._file_fd is not None
            async for _ in stream:
                pass

    asyncio.run(run())
    assert source.complete


@pytest.mark.parametrize("deadline", [float("nan"), float("inf"), float("-inf"), True, None])
def test_invalid_deadline_never_opens_source(source_file, deadline):
    with pytest.raises(YorungeError) as failure:
        make_source(source_file, deadline=deadline)
    assert failure.value.code == "invalid_request"


def test_expired_deadline_and_no_copy_or_serialization(source_file):
    source = make_source(source_file, deadline=time.monotonic() - 1)
    for invoke in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(TypeError):
            invoke(source)

    async def run():
        with pytest.raises(YorungeError) as failure:
            source.chunks()
        assert failure.value.code == "execution_timeout"
        await source.aclose()

    asyncio.run(run())
    assert source.sent_bytes == 0 and source._file_fd is source._root_fd is None


def test_empty_regular_file_has_empty_hash_and_successful_eof(source_file):
    root, path, _, identity, _ = source_file
    path.write_bytes(b"")
    entry = DatasetFile(path=path.name, size=0, sha256=hashlib.sha256(b"").hexdigest())
    source = make_source(source_file, file=entry)

    async def run():
        return [chunk async for chunk in source.chunks()]

    assert asyncio.run(run()) == []
    assert source.complete and source.sent_bytes == 0 and source.sent_sha256 == entry.sha256


def test_source_deadline_only_narrows_before_first_read(source_file):
    source = make_source(source_file)
    initial = source._end

    async def run():
        narrowed = time.monotonic() + 30
        source.restrict_deadline(narrowed)
        assert source._end == narrowed and source._file_fd is source._root_fd is None
        source.restrict_deadline(initial + 999)
        assert source._end == narrowed
        await anext(source.chunks())
        rejected_call = partial(source.restrict_deadline, time.monotonic() + 1)
        with pytest.raises(YorungeError) as raised:
            rejected_call()
        assert raised.value.code == "invalid_request" and source._end == narrowed
        await source.aclose()

    asyncio.run(run())
    assert source._file_fd is source._root_fd is None


@pytest.mark.parametrize("deadline", [True, None, float("nan"), float("inf"), 10**1000])
def test_source_rejects_invalid_arm_deadline_before_open(source_file, deadline):
    source = make_source(source_file)
    initial = source._end

    async def run():
        with pytest.raises(YorungeError) as raised:
            source.restrict_deadline(deadline)
        assert raised.value.code == "invalid_request" and source._end == initial
        assert source._file_fd is source._root_fd is None
        await source.aclose()

    asyncio.run(run())
