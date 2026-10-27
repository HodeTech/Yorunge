"""Fail real configuration I/O boundaries only inside a disposable fixture."""

import errno
import os
import sys
from pathlib import Path

from yorunge import api
from yorunge.adapters import configuration
from yorunge.domain.errors import YorungeError

path, action, phase, mode = Path(sys.argv[1]), *sys.argv[2:]


def stop():
    if mode == "exit":
        os._exit(71)
    raise OSError(errno.EIO, "synthetic config I/O failure")


original_write = configuration.write_new


def write(target, content):
    kind = "backup" if target.suffix == ".toml" else "temporary"
    if phase == kind + "-before":
        stop()
    original_write(target, content)
    if phase == kind + "-after":
        stop()


configuration.write_new = write
original_replace = os.replace
original_link = os.link


def publication(original, *args, **kwargs):
    if phase == "publish-before":
        stop()
    value = original(*args, **kwargs)
    if phase == "publish-after":
        stop()
    return value


os.replace = lambda *args, **kwargs: publication(original_replace, *args, **kwargs)
os.link = lambda *args, **kwargs: publication(original_link, *args, **kwargs)
original_directory = configuration.sync_directory


def directory(target):
    if phase == "parent-sync-before":
        stop()
    original_directory(target)
    if phase == "parent-sync-after":
        stop()


configuration.sync_directory = directory
original_sync = configuration.sync_private


def sync(target):
    if phase == "final-sync-before":
        stop()
    original_sync(target)
    if phase == "final-sync-after":
        stop()


configuration.sync_private = sync
original_fsync = os.fsync


def fsync(descriptor):
    if phase != "temporary-fsync":
        return original_fsync(descriptor)
    held = os.fstat(descriptor)
    for target in path.parent.glob("." + path.name + ".*.tmp"):
        if target.stat().st_ino == held.st_ino:
            stop()
    return original_fsync(descriptor)


os.fsync = fsync
try:
    if action == "init":
        api.initialize_config(config=path, profile="created")
    else:
        api.set_project("changed", config=path)
except YorungeError as error:
    if mode != "error" or error.code not in ("config_write_failed", "config_write_uncertain"):
        raise
    sys.exit(75 if error.code == "config_write_uncertain" else 72)
raise AssertionError("requested config boundary not reached")
