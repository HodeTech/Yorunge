"""Bounded descriptor-only input binding, with no symlink-following fallback."""

from __future__ import annotations

import hashlib
import os
import stat
import sys
from contextlib import ExitStack
from pathlib import Path
from typing import Protocol

from yorunge.domain.errors import YorungeError
from yorunge.domain.execution import InputBinding, InputRoot

BLOCK_BYTES = 1024 * 1024
MAX_INPUT_BYTES = 1024 * 1024 * 1024


class Budget(Protocol):
    def check(self) -> None: ...


def require_input_files() -> None:
    if (
        sys.platform not in ("darwin", "linux")
        or os.open not in os.supports_dir_fd
        or any(not hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK"))
    ):
        raise YorungeError("input_unsupported")


def identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def signature(info: os.stat_result) -> tuple[int, ...]:
    return (*identity(info), info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def directory_chain(anchor: str) -> tuple[int, tuple[tuple[int, int], ...]]:
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    chain = [identity(os.fstat(descriptor))]
    try:
        for part in anchor.split("/")[1:]:
            if not part:
                continue
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            chain.append(identity(os.fstat(descriptor)))
        return descriptor, tuple(chain)
    except BaseException:
        os.close(descriptor)
        raise


def relative_file(root: int, path: str) -> tuple[int, tuple[tuple[int, int], ...]]:
    descriptor = os.dup(root)
    chain = [identity(os.fstat(descriptor))]
    try:
        parts = path.split("/")
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            chain.append(identity(os.fstat(descriptor)))
        file = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
        return file, tuple(chain)
    finally:
        os.close(descriptor)


class DescriptorInputs:
    def bind(
        self,
        root: Path | InputRoot | None,
        references: tuple[tuple[str, str], ...],
        budget: Budget,
    ) -> tuple[InputRoot | None, tuple[InputBinding, ...]]:
        require_input_files()
        if root is None:
            if references:
                raise YorungeError("input_invalid")
            return None, ()
        if not isinstance(root, (Path, InputRoot)) or len(references) > 128:
            raise YorungeError("input_invalid")
        try:
            if isinstance(root, InputRoot):
                anchor = root.anchor
            else:
                if ".." in root.parts:
                    raise YorungeError("input_invalid")
                anchor = str(root if root.is_absolute() else Path.cwd() / root)
            # Validate raw input spelling before any Path normalization or open.
            for role, path in references:
                InputBinding(role=role, path=path, size=0, digest="0" * 64)
            InputRoot(anchor=anchor, device=0, inode=1)
            return self._bind(anchor, root, references, budget)
        except (OSError, ValueError, UnicodeError):
            raise YorungeError("input_invalid") from None

    def _bind(
        self,
        anchor: str,
        expected: Path | InputRoot,
        references: tuple[tuple[str, str], ...],
        budget: Budget,
    ) -> tuple[InputRoot, tuple[InputBinding, ...]]:
        budget.check()
        with ExitStack() as stack:
            root_fd, root_chain = directory_chain(anchor)
            stack.callback(os.close, root_fd)
            dev, ino = identity(os.fstat(root_fd))
            bound_root = InputRoot(anchor=anchor, device=dev, inode=ino)
            if isinstance(expected, InputRoot) and bound_root != expected:
                raise YorungeError("input_changed")
            total = 0
            inputs = []
            for role, path in sorted(references):
                budget.check()
                with ExitStack() as opened:
                    descriptor, path_chain = relative_file(root_fd, path)
                    opened.callback(os.close, descriptor)
                    before = os.fstat(descriptor)
                    if not stat.S_ISREG(before.st_mode):
                        raise YorungeError("input_invalid")
                    if total + before.st_size > MAX_INPUT_BYTES:
                        raise YorungeError("input_budget_exceeded")
                    digest, count = hashlib.sha256(), 0
                    while True:
                        budget.check()
                        block = os.read(descriptor, BLOCK_BYTES)
                        if not block:
                            break
                        count += len(block)
                        total += len(block)
                        if total > MAX_INPUT_BYTES:
                            raise YorungeError("input_budget_exceeded")
                        digest.update(block)
                    if count != before.st_size or signature(os.fstat(descriptor)) != signature(
                        before
                    ):
                        raise YorungeError("input_changed")
                    check_root, check_chain = directory_chain(anchor)
                    opened.callback(os.close, check_root)
                    check_file, check_path_chain = relative_file(check_root, path)
                    opened.callback(os.close, check_file)
                    if (
                        root_chain != check_chain
                        or path_chain != check_path_chain
                        or (
                            signature(os.fstat(check_file)) != signature(before)
                            or signature(os.fstat(descriptor)) != signature(before)
                        )
                    ):
                        raise YorungeError("input_changed")
                    inputs.append(
                        InputBinding(role=role, path=path, size=count, digest=digest.hexdigest())
                    )
            # Also bind/recheck roots when no input references exist.
            check_root, check_chain = directory_chain(anchor)
            stack.callback(os.close, check_root)
            if root_chain != check_chain:
                raise YorungeError("input_changed")
            budget.check()
            return bound_root, tuple(inputs)
