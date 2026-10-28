"""Synthetic performance dataset, never a product discovery backend."""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

from yorunge import api
from yorunge.adapters.capability_cache import StateCache, group_key
from yorunge.adapters.expiry_fences import backfill_expiries
from yorunge.adapters.identity import StateCredentialRegistry
from yorunge.adapters.state import open_store
from yorunge.application.capabilities import LocalPolicyProducer, combine
from yorunge.domain.capabilities import (
    CapabilityKey,
    CapabilityScopeV2,
    ExecutionBinding,
    canonical,
    timestamp,
)
from yorunge.domain.credentials import (
    EnvReference,
    ResolvedCredential,
    SecretValue,
    normalize_target,
)


def seed(root: Path, config: Path, *, evidence_count: int = 1) -> None:
    if type(evidence_count) is not int or not 1 <= evidence_count <= 8:
        raise ValueError("one to eight synthetic proofs required")
    if root.exists() or root.is_symlink():
        raise ValueError("use a new synthetic state directory; existing data is preserved")
    api.query_capabilities(task="llm.train", config=config, state_dir=root, refresh=True)
    with open_store(root, timeout=30) as store:
        cache = StateCache(store)
        stamp = cache.stamp()
        registry = StateCredentialRegistry(store)
        target = normalize_target("https://fixture.example.test/v1")
        rows = []
        for group in range(8):
            identity = registry.observe(
                ResolvedCredential(
                    EnvReference(service_id="evren-platform", name=f"BENCH_{group}"),
                    target,
                    SecretValue("synthetic-performance-only"),
                )
            )
            for index in range(128 if group < 7 else 126):
                scope = CapabilityScopeV2(
                    schema_version=2,
                    store_id=stamp.store_id,
                    identity_epoch=stamp.identity_epoch,
                    clock_generation=stamp.generation,
                    service_id="evren-platform",
                    **target.model_dump(),
                    account_id="fixture",
                    project_id=f"p{index}",
                    credential_id=identity.credential_id,
                    credential_revision=identity.credential_revision,
                    authorization_scope=None,
                    model=None,
                    tool=None,
                    execution=ExecutionBinding(
                        backend="local",
                        runtime_id=None,
                        runtime_revision=None,
                        environment_digest=None,
                    ),
                )
                key = CapabilityKey(
                    capability_id="fixture.discovery", task="llm.train", scope=scope
                )
                proofs = LocalPolicyProducer("unknown", "not_verified").observe(key, stamp.now)
                if evidence_count > 1:
                    proofs = tuple(
                        proofs[0].model_copy(
                            update={
                                "producer_id": f"fixture-producer-{index}",
                                "support": "supported" if index % 2 else "unsupported",
                                "checked_at": timestamp(stamp.now - timedelta(microseconds=index)),
                                "expires_at": timestamp(
                                    stamp.now + timedelta(seconds=300, microseconds=-index)
                                ),
                            }
                        )
                        for index in range(evidence_count)
                    )
                record = combine(key, None, proofs, stamp.now, replace_own=True)
                rows.append(
                    (
                        key.digest(),
                        key.encoded().decode("ascii"),
                        key.projection(),
                        group_key(key),
                        canonical(record.model_dump(mode="json")).decode("ascii"),
                        len(rows) + 3,
                        record.checked_at,
                        record.pinned_until(),
                    )
                )
        store.connection.execute("BEGIN IMMEDIATE")
        try:
            store.connection.executemany(
                "INSERT INTO capability_cache VALUES(?,?,?,?,?,?,?,?)", rows
            )
            backfill_expiries(store.connection)
            store.connection.execute(
                "UPDATE cache_clock SET mutation_revision=? WHERE singleton=1", (len(rows) + 2,)
            )
            store.connection.execute("COMMIT")
        finally:
            if store.connection.in_transaction:
                store.connection.execute("ROLLBACK")
        assert store.verify().store_schema_version == len(store.migrations)
        assert store.connection.execute("SELECT count(*) FROM capability_cache").fetchone() == (
            1024,
        )


if __name__ == "__main__":
    seed(Path(sys.argv[1]), Path(sys.argv[2]))
