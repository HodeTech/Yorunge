"""Offline research experiments in disposable directories; not a product store implementation."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import os
import platform
import secrets
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from pathlib import Path

WORKER = """
import hmac, sqlite3, sys
from pathlib import Path
key = Path(sys.argv[2]).read_bytes()
tag = hmac.digest(key, b'probe:v1\\x00synthetic-B', 'sha256')
con = sqlite3.connect(sys.argv[1], isolation_level=None, timeout=5)
con.execute('PRAGMA synchronous=EXTRA')
if sys.platform == 'darwin':
    con.execute('PRAGMA fullfsync=ON')
try:
    con.execute('BEGIN IMMEDIATE')
    previous, revision = con.execute('SELECT tag, revision FROM identity WHERE id=1').fetchone()
    if not hmac.compare_digest(previous, tag):
        con.execute('UPDATE identity SET tag=?, revision=? WHERE id=1', (tag, revision+1))
    con.execute('COMMIT')
finally:
    con.close()
"""
CRASH_WORKER = """
import os, sqlite3, sys
con = sqlite3.connect(sys.argv[1], isolation_level=None)
con.execute('PRAGMA synchronous=EXTRA')
if sys.platform == 'darwin':
    con.execute('PRAGMA fullfsync=ON')
con.execute('PRAGMA cache_size=10')
con.execute('BEGIN IMMEDIATE')
con.executemany('INSERT INTO crash_values(payload) VALUES (?)', [(b'x'*1024,)]*500)
if sys.argv[2] == 'commit':
    con.execute('COMMIT')
os._exit(23)
"""


def connect(path: Path, mode: str = "DELETE") -> sqlite3.Connection:
    connection = sqlite3.connect(path, isolation_level=None, timeout=0.1)
    actual = connection.execute(f"PRAGMA journal_mode={mode}").fetchone()[0]
    assert actual == mode.lower()
    connection.execute("PRAGMA synchronous=" + ("FULL" if mode == "WAL" else "EXTRA"))
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA trusted_schema=OFF")
    if sys.platform == "darwin":
        connection.execute("PRAGMA fullfsync=ON")
    return connection


def migration_probe(root: Path) -> dict[str, object]:
    with closing(connect(root / "migration.db")) as connection:
        connection.execute("PRAGMA user_version=1")
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute("CREATE TABLE pending(id INTEGER PRIMARY KEY) STRICT")
            connection.execute("PRAGMA user_version=2")
            connection.execute("INSERT INTO pending VALUES(1)")
            connection.execute("INSERT INTO pending VALUES(1)")
        except sqlite3.IntegrityError:
            connection.execute("ROLLBACK")
        else:
            raise AssertionError("constraint failure expected")
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        tables = connection.execute(
            "SELECT name FROM sqlite_schema WHERE name='pending'"
        ).fetchall()
        assert version == 1 and not tables
    with closing(connect(root / "executescript.db")) as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("CREATE TABLE prior(id INTEGER PRIMARY KEY)")
        try:
            connection.executescript("INSERT INTO prior VALUES(1); SELECT * FROM missing_table;")
        except sqlite3.OperationalError:
            pass
        else:
            raise AssertionError("missing table expected")
        split = not connection.in_transaction
        prior_persisted = connection.execute("SELECT count(*) FROM prior").fetchone()[0] == 1
        assert split and prior_persisted
    return {"ddl_and_version_rollback": True, "executescript_split_observed": True}


def locking_and_crash_probe(root: Path) -> dict[str, object]:
    path = root / "locking.db"
    with closing(connect(path)) as first, closing(connect(path)) as second:
        first.execute("BEGIN IMMEDIATE")
        started = time.monotonic()
        try:
            second.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as error:
            assert error.sqlite_errorcode == sqlite3.SQLITE_BUSY
        else:
            raise AssertionError("writer contention expected")
        elapsed = (time.monotonic() - started) * 1000
        first.execute("ROLLBACK")
    path = root / "crash.db"
    with closing(connect(path)) as connection:
        connection.execute("CREATE TABLE crash_values(payload BLOB) STRICT")
    counts = []
    for state in ("uncommitted", "commit"):
        result = subprocess.run(
            [sys.executable, "-c", CRASH_WORKER, str(path), state], check=False, timeout=10
        )
        assert result.returncode == 23
        with closing(connect(path)) as connection:
            counts.append(connection.execute("SELECT count(*) FROM crash_values").fetchone()[0])
            assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    assert counts == [0, 500]
    return {"busy_100ms_observed_ms": round(elapsed, 3), "process_exit_row_counts": counts}


def identity_probe(root: Path) -> dict[str, object]:
    vector = hmac.digest(b"\x0b" * 20, b"Hi There", "sha256")
    assert vector.hex() == "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"
    key = secrets.token_bytes(32)
    key_path = root / "comparison.key"
    descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as source:
        source.write(key)
        source.flush()
        os.fsync(source.fileno())
    path = root / "identity.db"
    original_tag = hmac.digest(key, b"probe:v1\x00synthetic-A", "sha256")
    with closing(connect(path)) as connection:
        connection.execute(
            "CREATE TABLE identity(id INTEGER PRIMARY KEY, tag BLOB NOT NULL, "
            "revision INTEGER NOT NULL CHECK(revision>0)) STRICT"
        )
        connection.execute("INSERT INTO identity VALUES(1, ?, 1)", (original_tag,))
    processes = [
        subprocess.Popen([sys.executable, "-c", WORKER, str(path), str(key_path)]) for _ in range(8)
    ]
    for process in processes:
        assert process.wait(timeout=10) == 0
    with closing(connect(path)) as connection:
        after_b = connection.execute("SELECT revision FROM identity").fetchone()[0]
        assert after_b == 2
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("UPDATE identity SET tag=?, revision=revision+1", (original_tag,))
        connection.execute("COMMIT")
        after_a = connection.execute("SELECT revision FROM identity").fetchone()[0]
        assert after_a == 3
    content = path.read_bytes()
    for secret in (b"synthetic-A", b"synthetic-B"):
        assert secret not in content and hashlib.sha256(secret).digest() not in content
    separation = hmac.digest(key, b"service-A\x00value", "sha256") != hmac.digest(
        key, b"service-B\x00value", "sha256"
    )
    assert separation
    return {
        "rfc4231_vector": True,
        "concurrent_workers": len(processes),
        "observed_revision_sequence": [1, after_b, after_a],
        "domain_separation": separation,
        "raw_values_and_plain_sha256_absent_from_db": True,
        "key_mode": oct(key_path.stat().st_mode & 0o777),
    }


def timing_probe(root: Path) -> dict[str, object]:
    report: dict[str, object] = {}
    for mode in ("DELETE", "WAL"):
        with closing(connect(root / (mode.lower() + ".db"), mode)) as connection:
            connection.execute("CREATE TABLE timing(id INTEGER PRIMARY KEY, value INTEGER) STRICT")
            connection.execute("INSERT INTO timing VALUES(1, 0)")
            samples = []
            for _ in range(100):
                started = time.perf_counter()
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("UPDATE timing SET value=value+1 WHERE id=1")
                connection.execute("COMMIT")
                samples.append((time.perf_counter() - started) * 1000)
            report[mode] = {
                "synchronous": connection.execute("PRAGMA synchronous").fetchone()[0],
                "samples": len(samples),
                "median_ms": round(statistics.median(samples), 3),
                "p95_ms": round(sorted(samples)[math.ceil(0.95 * len(samples)) - 1], 3),
            }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="yorunge-decision-probe-") as directory:
        root = Path(directory)
        with closing(sqlite3.connect(":memory:")) as connection:
            source_id = connection.execute("SELECT sqlite_source_id()").fetchone()[0]
            connection.execute("CREATE TABLE strict_probe(value INTEGER) STRICT")
            connection.execute("INSERT INTO strict_probe VALUES('1')")
            coerced = connection.execute("SELECT typeof(value) FROM strict_probe").fetchone()[0]
        assert coerced == "integer"
        report = {
            "status": "research_only_not_product_acceptance",
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "sqlite": sqlite3.sqlite_version,
            "sqlite_source_id": source_id,
            "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "sqlite_strict_still_coerces_numeric_text": True,
            "migration": migration_probe(root),
            "locking_and_process_exit": locking_and_crash_probe(root),
            "identity_prototype": identity_probe(root),
            "commit_microbenchmark": timing_probe(root),
            "limits": [
                "Single local host; no power-cut, hardware-fault, NFS or other OS verification.",
                "Prototype only; no product acceptance claim.",
                "Commit timings exclude startup/schema work; fsync counts differ by policy.",
            ],
        }
    arguments.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
