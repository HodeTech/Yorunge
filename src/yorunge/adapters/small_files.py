"""Read one small regular file by an absolute path, without following a link, in a bounded time.

For a local input of a single command (a Manifest v1 given to ``bind``, a binding given to
``check``): the parent is reached through no symlink, the file is a regular file no longer than the
caller's limit, it is opened ``O_NOFOLLOW|O_NONBLOCK`` (a FIFO or a device cannot block), read in
blocks under a deadline, and found unchanged (the same file, size and times) once it was read.
What the file is, a Manifest or a binding, is the caller's to judge; so is the limit's code.
"""

from __future__ import annotations

import errno
import os
import stat
import time
from pathlib import Path

from yorunge.adapters.input_files import (
    BLOCK_BYTES,
    directory_chain,
    identity,
    owned_descriptor,
    require_input_files,
    signature,
)
from yorunge.domain.errors import ErrorCode, YorungeError


def read_regular_file(
    path: Path, *, limit: int, oversize: ErrorCode, seconds: float = 5.0
) -> bytes:
    """The bytes of ``path`` (absolute), at most ``limit`` of them; else a closed error.

    ``input_invalid`` for a path that is not a regular file reached without a link,
    ``file_unreadable`` for an OS error, ``input_changed`` for a file that changed while it was
    read, ``oversize`` for a file longer than ``limit``; a read that outlasts ``seconds`` is
    ``file_unreadable`` too (the time budgets of the network are not a local file's).
    """
    if not isinstance(path, Path) or not path.is_absolute() or not path.name:
        raise YorungeError("invalid_request")
    require_input_files()
    if "\0" in path.name:
        raise YorungeError("input_invalid")  # the parents are judged by ``directory_chain``
    end = time.monotonic() + seconds
    try:
        descriptor, chain = directory_chain(str(path.parent))
    except YorungeError:
        raise
    except OSError as error:
        raise _unreadable(error) from None
    with owned_descriptor(descriptor):
        try:
            before = os.stat(path.name, dir_fd=descriptor, follow_symlinks=False)
            if not stat.S_ISREG(before.st_mode):
                raise YorungeError("input_invalid")
            if before.st_size > limit:
                raise YorungeError(oversize)
            opened = os.open(
                path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor
            )
            with owned_descriptor(opened):
                held = os.fstat(opened)
                if identity(held) != identity(before) or not stat.S_ISREG(held.st_mode):
                    raise YorungeError("input_changed")
                content = bytearray()
                while len(content) <= limit:
                    if time.monotonic() >= end:
                        raise YorungeError(
                            "file_unreadable"
                        )  # a local file that stalls is not read
                    block = os.read(opened, min(BLOCK_BYTES, limit + 1 - len(content)))
                    if not block:
                        break
                    content.extend(block)
                if len(content) > limit:
                    raise YorungeError(oversize)
                if signature(os.fstat(opened)) != signature(before):
                    raise YorungeError("input_changed")
            after = os.stat(path.name, dir_fd=descriptor, follow_symlinks=False)
            second, again = directory_chain(str(path.parent))
            with owned_descriptor(second):
                if signature(after) != signature(before) or again != chain:
                    raise YorungeError("input_changed")
        except OSError as error:
            raise _unreadable(error) from None
    return bytes(content)


def _unreadable(error: OSError) -> YorungeError:
    code: ErrorCode = (
        "input_invalid" if error.errno in (errno.ELOOP, errno.ENOTDIR) else "file_unreadable"
    )
    return YorungeError(code)
