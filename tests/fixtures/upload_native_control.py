"""Bounded process lifecycle used by upload measurement and its offline tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def environment():
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("PYTHON") and key != "VIRTUAL_ENV"
    }


@contextmanager
def server(directory, certificates, label):
    directory.mkdir()
    ready = directory / "ready.json"
    with (
        (directory / "stdout.json").open("xb") as stdout,
        (directory / "stderr.txt").open("xb") as stderr,
    ):
        process = subprocess.Popen(
            [
                sys.executable,
                "-I",
                str(ROOT / "tests/fixtures/upload_native_server.py"),
                "--ca",
                str(certificates[0]),
                "--key",
                str(certificates[1]),
                "--ready",
                str(ready),
                "--label",
                label,
            ],
            stdout=stdout,
            stderr=stderr,
            env=environment(),
        )
        try:
            end = time.monotonic() + 10
            while not ready.is_file():
                if process.poll() is not None or time.monotonic() >= end:
                    raise ValueError("upload TLS sink did not become ready")
                time.sleep(0.01)
            value = json.loads(ready.read_bytes())
            if value["pid"] != process.pid:
                raise ValueError("upload TLS sink identity differs from readiness")
            yield value
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
                raise
        if process.returncode != 0:
            raise ValueError("upload TLS sink failed; original output retained")
