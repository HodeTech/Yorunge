"""Descriptor-owned local tree observation; no symlink-following or hash cache."""

from __future__ import annotations

import errno
import hashlib
import os
import stat
import sys
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path

from yorunge.adapters.input_files import (
    directory_chain,
    identity,
    relative_file,
    require_input_files,
    signature,
)
from yorunge.adapters.local_files import require_local_files
from yorunge.application.datasets import DatasetBudget
from yorunge.domain import dataset_manifest as policy
from yorunge.domain.dataset_manifest import (
    DatasetFile,
    DatasetLimit,
    DatasetManifest,
    PathInventory,
)
from yorunge.domain.errors import MESSAGES, ErrorCode, YorungeError

Chain = tuple[tuple[int, int], ...]


def close_descriptor(descriptor: int) -> None:
    active = sys.exception()
    try:
        os.close(descriptor)
    except OSError:
        if active is None:
            raise YorungeError("file_unreadable") from None
        # Preserve control flow, especially CancelledError; never retry an ambiguous close.
        BaseException.add_note(active, MESSAGES["file_unreadable"])


def require_dataset_files() -> None:
    require_input_files()
    if (
        os.scandir not in os.supports_fd
        or any(item not in os.supports_dir_fd for item in (os.stat, os.link, os.unlink))
        or any(item not in os.supports_follow_symlinks for item in (os.stat, os.link))
    ):
        raise YorungeError("input_unsupported")
    try:
        require_local_files()
    except YorungeError:
        raise YorungeError("input_unsupported") from None


def anchor_dataset_path(path: Path) -> Path:
    if not isinstance(path, Path):
        raise YorungeError("invalid_request")
    try:
        if ".." in path.parts:
            raise ValueError("parent traversal")
        anchor = path if path.is_absolute() else Path.cwd() / path
        policy.validate_anchor(str(anchor))
        return anchor
    except DatasetLimit:
        raise YorungeError("dataset_limit_exceeded") from None
    except (OSError, ValueError):
        raise YorungeError("input_invalid") from None


def _initial_io(error: OSError) -> YorungeError:
    code: ErrorCode = (
        "input_invalid" if error.errno in (errno.ELOOP, errno.ENOTDIR) else "file_unreadable"
    )
    return YorungeError(code)


def _observed_io(error: OSError) -> YorungeError:
    if error.errno in (errno.ENOENT, errno.ELOOP, errno.ENOTDIR):
        return YorungeError("input_changed")
    return YorungeError("file_unreadable")


@dataclass(frozen=True)
class FileObservation:
    path: str
    signature: tuple[int, ...]
    chain: Chain


@dataclass(frozen=True)
class DirectoryObservation:
    path: str
    signature: tuple[int, ...]
    chain: Chain
    names: tuple[str, ...]


@dataclass(frozen=True)
class DatasetLocation:
    anchor: Path
    descriptor: int
    chain: Chain
    budget: DatasetBudget

    @property
    def name(self) -> str:
        return self.anchor.name

    def recheck(self) -> None:
        self.budget.check()
        try:
            descriptor, chain = directory_chain(str(self.anchor.parent))
            try:
                if self.chain != chain:
                    raise YorungeError("input_changed")
            finally:
                close_descriptor(descriptor)
        except OSError as error:
            raise _observed_io(error) from None
        self.budget.check()


class DatasetTree:
    def __init__(self, anchor: Path, descriptor: int, chain: Chain, budget: DatasetBudget) -> None:
        self.anchor, self.descriptor, self.chain, self.budget = anchor, descriptor, chain, budget
        self.root_identity = identity(os.fstat(descriptor))
        self.inventory = PathInventory()
        self.files: list[FileObservation] = []
        self.directories: list[DirectoryObservation] = []
        self.total_bytes = 0
        self.scanned = False

    def check_root(self) -> None:
        self.budget.check()
        try:
            descriptor, chain = directory_chain(str(self.anchor))
            try:
                if self.chain != chain:
                    raise YorungeError("input_changed")
            finally:
                close_descriptor(descriptor)
        except OSError as error:
            raise _observed_io(error) from None

    @contextmanager
    def location(self, path: Path) -> Iterator[DatasetLocation]:
        self.budget.check()
        anchor = anchor_dataset_path(path)
        try:
            policy.validate_component(anchor.name)
            descriptor, chain = directory_chain(str(anchor.parent))
        except DatasetLimit:
            raise YorungeError("dataset_limit_exceeded") from None
        except ValueError:
            raise YorungeError("input_invalid") from None
        except OSError as error:
            raise _initial_io(error) from None
        try:
            # An ancestor identity check also catches a source reached through another spelling.
            if self.root_identity in chain:
                raise YorungeError("input_invalid")
            self.check_root()
            yield DatasetLocation(anchor, descriptor, chain, self.budget)
        finally:
            close_descriptor(descriptor)

    def scan(self) -> DatasetManifest:
        if self.scanned:
            raise YorungeError("invalid_request")
        self.scanned = True
        self.budget.check()
        try:
            files = self._walk(self.descriptor, "", (self.root_identity,))
            self.recheck()
            result = policy.build_manifest(tuple(files))
        except DatasetLimit:
            raise YorungeError("dataset_limit_exceeded") from None
        except ValueError:
            raise YorungeError("input_invalid") from None
        except OSError as error:
            raise _initial_io(error) from None
        self.budget.check()
        return result

    def _names(self, descriptor: int, *, rechecking: bool = False) -> tuple[str, ...]:
        names: list[str] = []
        with os.scandir(descriptor) as entries:
            for entry in entries:
                self.budget.check()
                names.append(entry.name)
                if len(names) > policy.MAX_FILES + policy.MAX_DIRECTORIES:
                    code: ErrorCode = "input_changed" if rechecking else "dataset_limit_exceeded"
                    raise YorungeError(code)
        try:
            ordered = tuple(sorted(names, key=lambda name: name.encode("utf-8")))
        except UnicodeError:
            raise YorungeError("input_changed" if rechecking else "input_invalid") from None
        if len(set(ordered)) != len(ordered):
            raise YorungeError("input_changed")
        return ordered

    def _walk(self, descriptor: int, path: str, chain: Chain) -> list[DatasetFile]:
        self.budget.check()
        before = os.fstat(descriptor)
        names = self._names(descriptor)
        self.directories.append(DirectoryObservation(path, signature(before), chain, names))
        files: list[DatasetFile] = []
        for name in names:
            self.budget.check()
            child = f"{path}/{name}" if path else name
            policy.file_parts(child)
            try:
                observed = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            except FileNotFoundError:
                raise YorungeError("input_changed") from None
            if observed.st_dev != self.root_identity[0]:
                raise YorungeError("input_invalid")
            if stat.S_ISDIR(observed.st_mode):
                self.inventory.add(child, is_file=False)
                files.extend(self._walk_child(descriptor, name, child, chain, observed))
            elif stat.S_ISREG(observed.st_mode):
                self.inventory.add(child, is_file=True)
                files.append(self._hash_file(descriptor, name, child, chain, observed))
            else:
                raise YorungeError("input_invalid")
        if signature(os.fstat(descriptor)) != signature(before):
            raise YorungeError("input_changed")
        return files

    def _walk_child(
        self, parent: int, name: str, path: str, chain: Chain, observed: os.stat_result
    ) -> list[DatasetFile]:
        descriptor = self._open_observed(parent, name, observed, directory=True)
        try:
            return self._walk(descriptor, path, (*chain, identity(observed)))
        finally:
            close_descriptor(descriptor)

    @staticmethod
    def _open_observed(
        parent: int, name: str, observed: os.stat_result, *, directory: bool = False
    ) -> int:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        if directory:
            flags |= os.O_DIRECTORY
        try:
            descriptor = os.open(name, flags, dir_fd=parent)
        except OSError as error:
            if error.errno in (errno.ENOENT, errno.ELOOP, errno.ENOTDIR):
                raise YorungeError("input_changed") from None
            raise
        try:
            if signature(os.fstat(descriptor)) != signature(observed):
                raise YorungeError("input_changed")
        except BaseException:
            close_descriptor(descriptor)
            raise
        return descriptor

    def _hash_file(
        self, parent: int, name: str, path: str, chain: Chain, observed: os.stat_result
    ) -> DatasetFile:
        if observed.st_size > policy.MAX_CONTENT_BYTES - self.total_bytes:
            raise YorungeError("input_budget_exceeded")
        descriptor = self._open_observed(parent, name, observed)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise YorungeError("input_invalid")
            digest, count = hashlib.sha256(), 0
            while count < observed.st_size:
                self.budget.check()
                block = os.read(descriptor, min(policy.HASH_BLOCK_BYTES, observed.st_size - count))
                if not block:
                    raise YorungeError("input_changed")
                digest.update(block)
                count += len(block)
            self.budget.check()
            if signature(os.fstat(descriptor)) != signature(observed):
                raise YorungeError("input_changed")
            self.files.append(FileObservation(path, signature(observed), chain))
            self.total_bytes += count
            return DatasetFile(path=path, size=count, sha256=digest.hexdigest())
        finally:
            close_descriptor(descriptor)

    def recheck(self) -> None:
        self.budget.check()
        if not self.scanned:
            raise YorungeError("invalid_request")
        try:
            for item in self.files:
                self._recheck_file(item)
            for directory in self.directories:
                self._recheck_directory(directory)
            self.check_root()
        except OSError as error:
            raise _observed_io(error) from None
        self.budget.check()

    def _recheck_file(self, item: FileObservation) -> None:
        self.budget.check()
        descriptor, chain = relative_file(self.descriptor, item.path)
        try:
            if chain != item.chain or signature(os.fstat(descriptor)) != item.signature:
                raise YorungeError("input_changed")
        finally:
            close_descriptor(descriptor)

    def _recheck_directory(self, item: DirectoryObservation) -> None:
        self.budget.check()
        with ExitStack() as stack:
            descriptor = os.dup(self.descriptor)
            stack.callback(close_descriptor, descriptor)
            chain = [identity(os.fstat(descriptor))]
            for name in item.path.split("/") if item.path else ():
                descriptor = os.open(
                    name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor
                )
                stack.callback(close_descriptor, descriptor)
                chain.append(identity(os.fstat(descriptor)))
            if (
                tuple(chain) != item.chain
                or signature(os.fstat(descriptor)) != item.signature
                or self._names(descriptor, rechecking=True) != item.names
                or signature(os.fstat(descriptor)) != item.signature
            ):
                raise YorungeError("input_changed")

    def read_manifest(self, path: Path) -> bytes:
        with self.location(path) as location:
            try:
                before = os.stat(location.name, dir_fd=location.descriptor, follow_symlinks=False)
                if not stat.S_ISREG(before.st_mode):
                    raise YorungeError("input_invalid")
                if before.st_size > policy.MAX_MANIFEST_BYTES:
                    raise YorungeError("manifest_invalid")
                descriptor = self._open_observed(location.descriptor, location.name, before)
                try:
                    content = self._read_manifest_bytes(descriptor, before.st_size)
                    if signature(os.fstat(descriptor)) != signature(before):
                        raise YorungeError("input_changed")
                finally:
                    close_descriptor(descriptor)
                location.recheck()
                try:
                    after = os.stat(
                        location.name, dir_fd=location.descriptor, follow_symlinks=False
                    )
                except OSError as error:
                    raise _observed_io(error) from None
                if signature(after) != signature(before):
                    raise YorungeError("input_changed")
            except OSError as error:
                raise _initial_io(error) from None
            self.budget.check()
            return content

    def _read_manifest_bytes(self, descriptor: int, size: int) -> bytes:
        content = bytearray()
        while len(content) < size:
            self.budget.check()
            block = os.read(descriptor, min(policy.HASH_BLOCK_BYTES, size - len(content)))
            if not block:
                raise YorungeError("input_changed")
            content.extend(block)
        self.budget.check()
        return bytes(content)


@contextmanager
def open_dataset(root: Path, budget: DatasetBudget) -> Iterator[DatasetTree]:
    require_dataset_files()
    anchor = anchor_dataset_path(root)
    budget.check()
    try:
        descriptor, chain = directory_chain(str(anchor))
    except OSError as error:
        raise _initial_io(error) from None
    try:
        try:
            tree = DatasetTree(anchor, descriptor, chain, budget)
        except OSError as error:
            raise _initial_io(error) from None
        yield tree
    finally:
        close_descriptor(descriptor)
