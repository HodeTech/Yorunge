"""Disposable, canonically valid historical stores for migration resource acceptance."""

from __future__ import annotations

import hashlib
import json
import runpy
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from yorunge import api
from yorunge.adapters import state_schema
from yorunge.adapters.capability_cache import ENTRY_FIELDS, decode_entry
from yorunge.adapters.expiry_fences import save_expiries
from yorunge.adapters.state import open_store
from yorunge.domain.capabilities import CapabilityRecord, canonical, instant, timestamp
from yorunge.domain.execution import ExecutionApproval, ExecutionPlan, binding_digest

PROJECT = Path(__file__).resolve().parents[2]


def fill_record(raw):
    """Fill only allowed constraint/message values; the current model is the authority."""
    raw["message"] = "fixture"
    for proof in raw["evidence"]:
        proof["constraints"] = []
    for proof in raw["evidence"]:
        for index in range(32):
            value = {"name": f"limit-{index}", "value": "x" * 256}
            proof["constraints"].append(value)
            excess = len(canonical(raw)) - 32768
            if excess <= 0:
                continue
            proof["constraints"].pop()
            remaining = 32768 - len(canonical(raw))
            value["value"] = "x"
            proof["constraints"].append(value)
            needed = 32768 - len(canonical(raw))
            if needed >= 0:
                value["value"] = "x" * (needed + 1)
            else:
                proof["constraints"].pop()
                raw["message"] += "x" * remaining
            record = CapabilityRecord.model_validate_json(canonical(raw))
            assert len(canonical(record.model_dump(mode="json"))) == 32768
            return record
    raise AssertionError("fixture constraints cannot reach the record limit")


def maximum_cache(store):
    rows = store.connection.execute(f"SELECT {ENTRY_FIELDS} FROM capability_cache").fetchall()
    template, _ = decode_entry(rows[0])
    now = instant(template.checked_at)
    proofs = []
    for index, seconds in enumerate((60, 90, 120, 150, 180, 210, 240, 300)):
        proof = template.evidence[0].model_dump(mode="json")
        proof.update(
            producer_id=f"fixture-limit-{index}",
            support="supported" if index % 2 else "unsupported",
            checked_at=timestamp(now),
            expires_at=timestamp(now + timedelta(seconds=seconds)),
        )
        proofs.append(proof)
    store.connection.execute("BEGIN IMMEDIATE")
    try:
        for row in rows:
            raw = json.loads(row[4])
            raw.update(
                support="unknown",
                reason_code="fixture_limits",
                evidence=deepcopy(proofs),
                checked_at=timestamp(now),
                expires_at=timestamp(now + timedelta(seconds=30)),
                conflict_until=timestamp(now + timedelta(seconds=270)),
            )
            record = fill_record(raw)
            store.connection.execute(
                "UPDATE capability_cache SET payload=?,checked_at=?,pinned_until=? "
                "WHERE cache_key=?",
                (
                    canonical(record.model_dump(mode="json")).decode("ascii"),
                    record.checked_at,
                    record.pinned_until(),
                    row[0],
                ),
            )
            save_expiries(store.connection, record)
        store.connection.execute("COMMIT")
    finally:
        if store.connection.in_transaction:
            store.connection.execute("ROLLBACK")


def relative_path(length):
    # All components are filesystem-sized, non-empty and non-special; no real input is read.
    chunks = []
    while length > 200:
        take = 199 if length == 201 else 200
        chunks.append("p" * take)
        length -= take + 1
    chunks.append("p" * length)
    return "/".join(chunks)


def maximum_plan(plan, root):
    body = plan.model_dump(mode="json", exclude={"digest"})
    # Archived bindings legitimately permit the largest generation; approval remains ineffective.
    body["identity_epoch"] = str(uuid4())
    body["clock_generation"] = 2**63 - 1
    for capability in body["assessment"]["capabilities"]:
        capability["key"]["scope"]["identity_epoch"] = body["identity_epoch"]
        capability["key"]["scope"]["clock_generation"] = body["clock_generation"]
    info = root.stat()
    body["input_root"] = {
        "anchor": str(root.resolve()),
        "device": info.st_dev,
        "inode": info.st_ino,
    }
    body["inputs"] = [
        {"role": f"fixture-{i:03d}", "path": "p", "size": 0, "digest": "0" * 64} for i in range(64)
    ]
    remaining = 65536 - len(canonical({**body, "digest": "0" * 64}))
    for item in body["inputs"]:
        extra = min(remaining, 1023)
        item["path"] = relative_path(extra + 1)
        remaining -= extra
    assert remaining == 0
    body["digest"] = hashlib.sha256(canonical(body)).hexdigest()
    result = ExecutionPlan.model_validate_json(canonical(body))
    assert len(canonical(result.model_dump(mode="json"))) == 65536
    return result


def plans(root, version, maximum, config):
    validator = runpy.run_path(str(PROJECT / "tests/conftest.py"))["execution_validator_fixture"]()
    with patch.object(api, "_execution_validator", return_value=validator):
        base = api.prepare_execution_plan(task="llm.train", config=config, state_dir=root).data.plan
        if version == 4:
            assert api.approve_execution_plan(
                base.plan_id, base.digest, config=config, state_dir=root
            ).data.effective
    if maximum:
        base = maximum_plan(base, root)
    with open_store(root, timeout=60) as store:
        store.connection.execute("BEGIN IMMEDIATE")
        try:
            store.connection.execute("DELETE FROM execution_approvals")
            store.connection.execute("DELETE FROM execution_plans")
            for _ in range(1024):
                body = base.model_dump(mode="json", exclude={"digest"})
                body["plan_id"] = str(uuid4())
                digest = hashlib.sha256(canonical(body)).hexdigest()
                copied = base.model_copy(update={"plan_id": body["plan_id"], "digest": digest})
                store.connection.execute(
                    "INSERT INTO execution_plans VALUES(?,?,?,?,?,?,?)",
                    (
                        copied.plan_id,
                        copied.digest,
                        copied.selection.task,
                        copied.prepared_at,
                        copied.expires_at,
                        copied.status,
                        canonical(copied.model_dump(mode="json")).decode("ascii"),
                    ),
                )
                if version == 4:
                    record = ExecutionApproval(
                        approval_id=str(uuid4()),
                        plan_id=copied.plan_id,
                        plan_digest=copied.digest,
                        binding_digest=binding_digest(copied),
                        store_id=copied.store_id,
                        identity_epoch=copied.identity_epoch,
                        clock_generation=copied.clock_generation,
                        approved_at=copied.prepared_at,
                        expires_at=copied.expires_at,
                        status="revoked" if maximum else "approved",
                        revoked_at=copied.prepared_at if maximum else None,
                    )
                    store.connection.execute(
                        "INSERT INTO execution_approvals VALUES(?,?,?,?,?,?,?)",
                        (
                            record.plan_id,
                            record.approval_id,
                            record.status,
                            record.approved_at,
                            record.expires_at,
                            record.revoked_at,
                            canonical(record.model_dump(mode="json")).decode("ascii"),
                        ),
                    )
            store.connection.execute("COMMIT")
        finally:
            if store.connection.in_transaction:
                store.connection.execute("ROLLBACK")
        store.verify()


def seed(root: Path, *, version: int, maximum: bool) -> None:
    # Historical rows are built by the delivered schema-5 runtime, not by
    # dropping unknown future consumer tables from the current schema.
    with patch.object(state_schema, "MIGRATIONS", state_schema.MIGRATIONS[:5]):
        _seed(root, version=version, maximum=maximum)


def _seed(root: Path, *, version: int, maximum: bool) -> None:
    if version not in (2, 3, 4):
        raise ValueError("historical schema 2, 3 or 4 required")
    config = PROJECT / "examples/profile.toml"
    runpy.run_path(str(PROJECT / "tests/fixtures/seed_capability_cache.py"))["seed"](
        root, config, evidence_count=8
    )
    if maximum:
        with open_store(root, timeout=60) as store:
            maximum_cache(store)
    if version >= 3:
        plans(root, version, maximum, config)
    with open_store(root, timeout=60) as store:
        store.verify()
        conn = store.connection
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DROP TABLE capability_expiries")
        conn.execute("DROP INDEX execution_plan_expiry")
        conn.execute("DROP INDEX execution_approval_expiry")
        if version < 4:
            conn.execute("DROP TABLE execution_approvals")
        if version < 3:
            conn.execute("DROP TABLE execution_plans")
        conn.execute("DELETE FROM schema_migrations WHERE version>?", (version,))
        conn.execute(f"PRAGMA user_version={version}")
        conn.execute("COMMIT")
    with patch.object(state_schema, "MIGRATIONS", state_schema.MIGRATIONS[:version]):
        with open_store(root, timeout=60) as store:
            store.verify()
