"""Read-only local state diagnostics; never opens or creates a key."""

from __future__ import annotations

import os
from pathlib import Path

from yorunge.domain.configuration import Diagnostic
from yorunge.domain.errors import YorungeError


def check_state(path: Path | None) -> tuple[Diagnostic, Diagnostic, Diagnostic]:
    # Keep SQLite lazy even for the common not-yet-installed case.
    root = path if path is not None else Path.home() / ".local/state/yorunge"
    if "\x00" in str(root):
        raise YorungeError("invalid_request")
    try:
        os.fsencode(root)
    except UnicodeError:
        raise YorungeError("invalid_request") from None
    unchecked = Diagnostic(name="key_check", status="not_checked")
    try:
        if not root.exists() and not root.is_symlink():
            return (
                Diagnostic(name="state", status="missing"),
                Diagnostic(name="key", status="not_checked"),
                unchecked,
            )
        return check_existing_state(path)
    except OSError:
        return (
            Diagnostic(name="state", status="invalid", code="state_invalid"),
            Diagnostic(name="key", status="not_checked"),
            unchecked,
        )


def check_existing_state(path: Path | None) -> tuple[Diagnostic, Diagnostic, Diagnostic]:
    import sqlite3

    from yorunge.adapters.local_files import Deadline, private_stat
    from yorunge.adapters.maintenance import (
        live_snapshot,
        no_intent,
        owned_directory,
        quiescent,
        target_lock,
    )
    from yorunge.adapters.state import (
        DB_NAME,
        connect_readonly,
        metadata,
        sqlite_error_code,
        state_directory,
    )

    unchecked = Diagnostic(name="key_check", status="not_checked")
    try:
        root, deadline = state_directory(path), Deadline()
        with target_lock(root, deadline, create=False):
            no_intent(root)
            if live_snapshot(root, deadline) is None:
                return (
                    Diagnostic(name="state", status="missing"),
                    Diagnostic(name="key", status="missing"),
                    unchecked,
                )
            quiescent(root / DB_NAME)
            connection = connect_readonly(root / DB_NAME, deadline)
            try:
                value = metadata(connection)
            finally:
                connection.close()
            try:
                owned_directory(root / "keys")
                key = private_stat(root / "keys" / (value.active_key_id + ".key"))
                if key.st_size != 32 or key.st_dev != root.stat().st_dev:
                    raise YorungeError("state_invalid")
                key_result = Diagnostic(name="key", status="ok")
            except FileNotFoundError:
                key_result = Diagnostic(name="key", status="missing", code="state_repair_required")
            except YorungeError as error:
                key_result = Diagnostic(name="key", status="invalid", code=error.code)
        return Diagnostic(name="state", status="ok"), key_result, unchecked
    except YorungeError as error:
        return (
            Diagnostic(
                name="state",
                status="busy" if error.code == "state_busy" else "invalid",
                code=error.code,
            ),
            Diagnostic(name="key", status="not_checked"),
            unchecked,
        )
    except OSError:
        return (
            Diagnostic(name="state", status="invalid", code="state_invalid"),
            Diagnostic(name="key", status="not_checked"),
            unchecked,
        )
    except sqlite3.Error as error:
        return (
            Diagnostic(name="state", status="invalid", code=sqlite_error_code(error)),
            Diagnostic(name="key", status="not_checked"),
            unchecked,
        )
