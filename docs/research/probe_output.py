"""Restricted no-clobber output for the two disposable, stdlib-only research probes."""

import json
import os
import stat
from pathlib import Path

OUTPUT_NAMES = frozenset({"p01-2-decision-probe.json", "p01-2-review-probe.json"})


def write_report(filename: str, report: dict[str, object]) -> None:
    if filename not in OUTPUT_NAMES:
        raise ValueError("unsupported research report")
    root = Path(__file__).resolve().parents[2]
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        try:
            os.mkdir("dist", mode=0o700, dir_fd=root_fd)
        except FileExistsError:
            pass
        directory = os.open("dist", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
        try:
            info = os.fstat(directory)
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
                raise ValueError("owned non-writable-by-others output directory required")
            descriptor = os.open(
                filename,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory,
            )
            with os.fdopen(descriptor, "wb") as output:
                output.write(
                    (json.dumps(report, indent=2, ensure_ascii=True) + "\n").encode("utf-8")
                )
                output.flush()
                os.fsync(output.fileno())
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.close(root_fd)
