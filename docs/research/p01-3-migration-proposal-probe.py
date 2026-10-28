"""ADR-0015 research only: import-cache counterexample and fixed-vector preconditions."""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import os
import platform
import py_compile
import sqlite3
import sys
import tempfile
from pathlib import Path

from yorunge.adapters.capability_cache import decode_entry
from yorunge.adapters.expiry_fences import cache_expiries


def bytecode_probe() -> dict[str, object]:
    name = "_yorunge_adr0015_research_probe"
    if name in sys.modules:
        raise RuntimeError("research module name already in use")
    with tempfile.TemporaryDirectory(prefix="adr0015-") as folder:
        path = Path(folder) / "handler.py"
        path.write_bytes(b'VALUE = "old"\n')
        os.utime(path, (1700000000, 1700000000))
        py_compile.compile(
            str(path), doraise=True, invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP
        )
        verified = b'VALUE = "new"\n'
        path.write_bytes(verified)
        os.utime(path, (1700000000, 1700000000))
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError("research module loader unavailable")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
            imported = module.VALUE
            preloaded = importlib.import_module(name).VALUE
            namespace: dict[str, object] = {}
            exec(
                compile(
                    verified, "<verified-research-bytes>", "exec", dont_inherit=True, optimize=0
                ),
                namespace,
            )
            direct = namespace["VALUE"]
        finally:
            del sys.modules[name]
    if (imported, preloaded, direct) != ("old", "old", "new"):
        raise RuntimeError("bytecode counterexample did not reproduce")
    return {
        "source_value": "new",
        "source_sha256": hashlib.sha256(verified).hexdigest(),
        "timestamp_pyc_import": imported,
        "preloaded_module_import": preloaded,
        "compile_same_verified_buffer": direct,
        "v2_loader_exercised": False,
    }


def main() -> None:
    here = Path(__file__).resolve().parent
    root = here.parent.parent
    fixture = here / "p01-3-expiry-migration-vectors.json"
    raw = fixture.read_bytes()
    vectors = json.loads(raw)["vectors"]
    counts = {}
    for vector in vectors:
        row = vector["source_row"]
        record, _ = decode_entry(tuple(row))
        actual = [[row[0], date] for date in cache_expiries(record)]
        if actual != vector["expected_expiries"]:
            raise RuntimeError(f"literal expiry oracle mismatch: {vector['id']}")
        counts[vector["id"]] = len(actual)
    print(
        json.dumps(
            {
                "purpose": "Proposed ADR research; not V2 migration or warm-reader acceptance",
                "python": platform.python_version(),
                "platform": platform.system(),
                "sqlite": sqlite3.sqlite_version,
                "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "vectors_sha256": hashlib.sha256(raw).hexdigest(),
                "runtime_source_sha256": {
                    name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                    for name in (
                        "src/yorunge/adapters/capability_cache.py",
                        "src/yorunge/adapters/expiry_fences.py",
                        "src/yorunge/domain/capabilities.py",
                    )
                },
                "bytecode": bytecode_probe(),
                "canonical_decode_entry": "passed",
                "prototype_expiry_helper_matches_literal_rows": counts,
                "v2_implemented": False,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
