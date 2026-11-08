"""What every Platform command judges about where its caller stands, before any file or secret.

Two small rules the version commands and the weight download share: the state directory, if one is
given, is a path, and the synchronous bridge is not entered from a running event loop; and a path
the caller names is made absolute by one look at the working directory (no symlink is walked).
"""

from __future__ import annotations

from pathlib import Path

from yorunge.adapters.local_files import require_local_files
from yorunge.adapters.upload_sync import require_upload_sync_context
from yorunge.domain.errors import YorungeError


def judge_ground(state_dir: object) -> None:
    """The caller's footing: a state directory that is a path, a thread that may block."""
    if state_dir is not None and not isinstance(state_dir, Path):
        raise YorungeError("invalid_request")
    require_upload_sync_context()  # a running event loop is refused whatever the target says
    require_local_files()


def absolute(path: object) -> Path:
    """The path as one observation of the working directory makes it absolute."""
    if not isinstance(path, Path) or not path.name or path.name in (".", ".."):
        raise YorungeError("invalid_request")  # no name, or the name of a directory that exists
    if path.is_absolute():
        return path
    try:
        return Path.cwd() / path
    except OSError:
        raise YorungeError("input_invalid") from None
