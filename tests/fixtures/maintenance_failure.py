"""Process cuts and I/O failures in disposable reset/restore fixtures."""

import errno
import os
import sys
from pathlib import Path

from yorunge import api
from yorunge.adapters import local_files, maintenance, state_schema
from yorunge.domain.errors import YorungeError

# This fixture replays cuts in the historical restorable runtime.
state_schema.MIGRATIONS = state_schema.MIGRATIONS[:5]

root, source, action, phase, mode = Path(sys.argv[1]), Path(sys.argv[2]), *sys.argv[3:]
preview = (
    api.preview_identity_reset(state_dir=root)
    if action == "reset"
    else api.preview_state_restore(source, state_dir=root)
)


def stop():
    if mode == "exit":
        os._exit(71)
    raise OSError(errno.EIO, "synthetic maintenance I/O failure")


def wrap(name, label):
    original = getattr(maintenance, name)

    def call(*args, **kwargs):
        if phase == label + "-before":
            stop()
        value = original(*args, **kwargs)
        if phase == label + "-after":
            stop()
        return value

    setattr(maintenance, name, call)


for name, label in (
    ("new_key", "key"),
    ("write_new", "intent"),
    ("copy_snapshot", "copy"),
    ("stage_restore", "stage"),
    ("reset_connection", "reset"),
):
    wrap(name, label)

original_replace = os.replace


def replace(*args):
    if phase == "publish-before":
        stop()
    original_replace(*args)
    if phase == "publish-after":
        stop()


os.replace = replace
original_unlink = Path.unlink


def unlink(self, *args, **kwargs):
    if self.name == maintenance.INTENT_NAME and phase == "intent-remove-before":
        stop()
    original_unlink(self, *args, **kwargs)
    if self.name == maintenance.INTENT_NAME and phase == "intent-remove-after":
        stop()


Path.unlink = unlink
original_sync = maintenance.sync_private


def sync(path):
    if path == root / maintenance.DB_NAME and phase == "live-sync-before":
        stop()
    original_sync(path)
    if path == root / maintenance.DB_NAME and phase == "live-sync-after":
        stop()


maintenance.sync_private = sync
original_directory_sync = maintenance.sync_directory


def directory_sync(path):
    if path == root and not (root / maintenance.INTENT_NAME).exists():
        if phase == "intent-remove-sync-before":
            stop()
        original_directory_sync(path)
        if phase == "intent-remove-sync-after":
            stop()
    else:
        original_directory_sync(path)


maintenance.sync_directory = directory_sync
original_connect = maintenance.connect


class Connection:
    def __init__(self, connection):
        self.connection = connection

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def execute(self, statement, *args):
        if statement.startswith("UPDATE state_meta") and phase == "pointer-before":
            stop()
        if statement == "COMMIT" and phase == "commit-before":
            stop()
        result = self.connection.execute(statement, *args)
        if statement == "COMMIT" and phase == "commit-after":
            stop()
        return result


def connect(*args):
    return Connection(original_connect(*args))


maintenance.connect = connect
original_fullsync = local_files.full_sync
old_keys = set((root / "keys").glob("*.key"))


def fullsync(descriptor):
    held = os.fstat(descriptor)
    for path in (root / "keys").glob("*.key"):
        if path not in old_keys and path.stat().st_ino == held.st_ino:
            if phase == "key-sync-before":
                stop()
            original_fullsync(descriptor)
            if phase == "key-sync-after":
                stop()
            return
    original_fullsync(descriptor)


local_files.full_sync = fullsync
try:
    if action == "reset":
        api.reset_identity(preview.data.digest, state_dir=root)
    else:
        api.restore_state(source, preview.data.digest, state_dir=root)
except YorungeError as error:
    if mode != "error" or error.code != "state_write_failed":
        raise
    sys.exit(72)
raise AssertionError("maintenance boundary was not reached")
