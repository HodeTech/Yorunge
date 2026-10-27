"""Cut only a disposable bootstrap at named real I/O/commit boundaries."""

import errno
import os
import stat
import sys
from pathlib import Path

from yorunge import api
from yorunge.adapters import local_files, state
from yorunge.domain.errors import YorungeError

root, phase, mode = Path(sys.argv[1]), sys.argv[2], sys.argv[3]


def stop():
    if mode == "exit":
        os._exit(71)
    raise OSError(errno.EIO, "synthetic bootstrap I/O failure")


def fd_kind(descriptor):
    info = os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode):
        return None
    candidates = [(root / state.DB_NAME, "db"), (root / "store.lock", "lock")]
    if (root / "keys").exists():
        candidates.extend((path, "key") for path in (root / "keys").glob("*.key"))
    for path, kind in candidates:
        if path.exists() and (path.stat().st_dev, path.stat().st_ino) == (info.st_dev, info.st_ino):
            return kind
    return None


original_new_key = state.new_key


def new_key(*args):
    if phase == "before-key":
        stop()
    return original_new_key(*args)


state.new_key = new_key
original_fsync = os.fsync


def fsync(descriptor):
    kind = fd_kind(descriptor)
    if kind and phase == kind + "-before-fsync":
        stop()
    return original_fsync(descriptor)


os.fsync = fsync
original_directory_sync = local_files.sync_directory


def directory_sync(path):
    if phase == "root-before-sync" and path == root:
        stop()
    if phase == "root-parent-before-sync" and path == root.parent and root.exists():
        stop()
    if phase == "keys-dir-before-sync" and path == root / "keys":
        stop()
    if phase == "keys-parent-before-sync" and path == root and (root / "keys").exists():
        if not list((root / "keys").glob("*.key")):
            stop()
    if phase == "lock-before-dir-sync" and path == root and (root / "store.lock").exists():
        if not (root / "keys").exists():
            stop()
    if phase == "key-before-dir-sync" and path == root / "keys":
        if list((root / "keys").glob("*.key")):
            stop()
    if phase == "db-before-dir-sync" and path == root:
        if (root / state.DB_NAME).exists() and (root / state.DB_NAME).stat().st_size == 0:
            stop()
    return original_directory_sync(path)


local_files.sync_directory = directory_sync
original_full_sync = local_files.full_sync


def full_sync(descriptor):
    kind = fd_kind(descriptor)
    if kind and phase == kind + "-before-fullsync":
        stop()
    original_full_sync(descriptor)
    if kind and phase == kind + "-after-fullsync":
        stop()


local_files.full_sync = full_sync
original_sync_private = state.sync_private


def sync_private(path):
    if path.name == state.DB_NAME and phase == "db-final-before-sync":
        stop()
    original_sync_private(path)
    if path.name == state.DB_NAME and phase == "db-final-after-sync":
        stop()


state.sync_private = sync_private
original_connect = state.connect


class Connection:
    def __init__(self, connection):
        self.connection = connection

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def execute(self, statement, *args):
        if phase == "metadata-before-insert" and statement.startswith("INSERT INTO state_meta"):
            stop()
        if phase == "metadata-before-commit" and statement == "COMMIT":
            stop()
        result = self.connection.execute(statement, *args)
        if phase == "after-commit" and statement == "COMMIT":
            stop()
        return result


def connect(*args):
    return Connection(original_connect(*args))


state.connect = connect
try:
    api.initialize_state(state_dir=root)
except YorungeError as error:
    if mode != "error" or error.code != "state_write_failed":
        raise
    sys.exit(72)
raise AssertionError("requested bootstrap boundary was not reached")
