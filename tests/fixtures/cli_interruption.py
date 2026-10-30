"""Gate actual CLI I/O in a disposable process; SIGINT comes from the parent."""

import os
import socket
import sys
from pathlib import Path

from yorunge import cli
from yorunge.adapters import configuration

control = socket.socket(fileno=int(sys.argv[1]))
phase = sys.argv[2]
target = Path(sys.argv[3])
arguments = sys.argv[4:]
publication_calls = 0


def gate(point):
    if phase == point:
        control.sendall(b"ready\n")
        if control.recv(1) != b"r":
            raise AssertionError("test barrier was not released")


original_stage = configuration.stage


def stage(*args, **kwargs):
    gate("stage-before")
    return original_stage(*args, **kwargs)


configuration.stage = stage
original_snapshot = configuration.read_snapshot


def snapshot(*args, **kwargs):
    gate("snapshot-before")
    return original_snapshot(*args, **kwargs)


configuration.read_snapshot = snapshot
original_publish = configuration.publish


def publish(*args, **kwargs):
    gate("publish-before")
    result = original_publish(*args, **kwargs)
    gate("confirmed")
    return result


configuration.publish = publish
original_link, original_replace = os.link, os.replace


def publication(original, name, source, destination, **kwargs):
    global publication_calls
    if Path(destination) == target:
        publication_calls += 1
        gate(name + "-before")
    result = original(source, destination, **kwargs)
    if Path(destination) == target:
        gate(name + "-after")
    return result


os.link = lambda source, destination, **kwargs: publication(
    original_link, "link", source, destination, **kwargs
)
os.replace = lambda source, destination, **kwargs: publication(
    original_replace, "replace", source, destination, **kwargs
)
original_directory = configuration.sync_directory


def directory(path):
    gate("parent-sync-before")
    original_directory(path)
    gate("parent-sync-after")


configuration.sync_directory = directory
original_sync = configuration.sync_private


def sync(path):
    gate("file-sync-before")
    original_sync(path)
    gate("file-sync-after")


configuration.sync_private = sync
original_fsync = os.fsync


def fsync(descriptor):
    if phase == "temporary-fsync":
        held = os.fstat(descriptor)
        for path in target.parent.glob("." + target.name + ".*.tmp"):
            if path.stat().st_ino == held.st_ino:
                gate("temporary-fsync")
    return original_fsync(descriptor)


os.fsync = fsync
original_open = os.open


def open_file(path, *args, **kwargs):
    if Path(path) == target:
        gate("read-before")
    return original_open(path, *args, **kwargs)


os.open = open_file
original_dispatch = cli.dispatch


def dispatch(args):
    result = original_dispatch(args)
    gate("result-ready")
    gate("pipe-closed")
    gate("output-ebadf")
    if phase == "output-ebadf":
        # Retain the real stdout wrapper but make its OS descriptor unwritable.
        descriptor = original_open(os.devnull, os.O_RDONLY)
        try:
            os.dup2(descriptor, sys.stdout.fileno())
        finally:
            os.close(descriptor)
    return result


cli.dispatch = dispatch
try:
    raise SystemExit(cli.main(arguments))
finally:
    control.sendall(f"publication={publication_calls}\n".encode("ascii"))
    control.close()
