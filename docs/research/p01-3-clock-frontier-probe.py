"""Reproduce cross-record clock revival; exit 1 means the defect was observed."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from yorunge.adapters import capability_cache
from yorunge.adapters.capability_cache import Stamp, StateCache
from yorunge.adapters.state import open_store
from yorunge.application.capabilities import LocalPolicyProducer
from yorunge.domain.capabilities import (
    CapabilityKey,
    CapabilityScopeV2,
    ExecutionBinding,
    timestamp,
)


class Clock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value

    def monotonic(self) -> float:
        return 0.0


def key(stamp: Stamp, name: str) -> CapabilityKey:
    return CapabilityKey(
        capability_id=name,
        task="llm.train",
        scope=CapabilityScopeV2(
            schema_version=2,
            store_id=stamp.store_id,
            identity_epoch=stamp.identity_epoch,
            clock_generation=stamp.generation,
            service_id="local",
            service_origin=None,
            api_base_path=None,
            account_id=None,
            project_id=None,
            credential_id=None,
            credential_revision=None,
            authorization_scope=None,
            model=None,
            tool=None,
            execution=ExecutionBinding(
                backend="local", runtime_id=None, runtime_revision=None, environment_digest=None
            ),
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-reference", required=True, help="Declared runtime reference")
    parser.add_argument("--terminal-commit", type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    base = datetime(2026, 10, 28, tzinfo=UTC)
    clock = Clock(base - timedelta(seconds=240))
    Path(".local").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="clock-frontier-", dir=".local") as folder:
        root = Path(folder).resolve() / "state"
        with open_store(root) as store:
            cache = StateCache(store, clock)
            initial = cache.stamp()
            cache.refresh(
                key(initial, "fixture.short"),
                initial,
                LocalPolicyProducer("supported", "fixture_policy"),
            )
            clock.value = base
            stamp = cache.stamp()
            cache.refresh(
                key(stamp, "fixture.long"),
                stamp,
                LocalPolicyProducer("supported", "fixture_policy"),
            )
            commits = 0
            injected = False

            def advance(statement: str) -> None:
                nonlocal commits, injected
                if statement == "COMMIT":
                    commits += 1
                    if commits == args.terminal_commit:
                        injected = True
                        clock.value = base + timedelta(seconds=100)

            store.connection.set_trace_callback(advance)
            long = cache.query(key(stamp, "fixture.long"), stamp)
            store.connection.set_trace_callback(None)
            if not injected:
                raise RuntimeError("requested terminal COMMIT was not observed")
            durable_high = store.connection.execute(
                "SELECT high_watermark FROM cache_clock WHERE singleton=1"
            ).fetchone()[0]
        clock.value = base + timedelta(seconds=50)
        with open_store(root) as store:
            cache = StateCache(store, clock)
            reopened = cache.stamp()
            short = cache.query(key(reopened, "fixture.short"), reopened)
    revived = (
        long.checked_at > timestamp(base + timedelta(seconds=60))
        and short.effective_support == "supported"
        and short.freshness == "fresh"
    )
    print(
        json.dumps(
            {
                "purpose": "defect reproduction; not product acceptance",
                "declared_source_reference": args.source_reference,
                "capability_cache_source_sha256": hashlib.sha256(
                    Path(capability_cache.__file__).read_bytes()
                ).hexdigest(),
                "terminal_commit": args.terminal_commit,
                "long_checked_at": long.checked_at,
                "long_freshness": long.freshness,
                "durable_high_watermark": durable_high,
                "short_expired_at": timestamp(base + timedelta(seconds=60)),
                "reopened_generation": reopened.generation,
                "short_checked_at": short.checked_at,
                "short_freshness": short.freshness,
                "short_effective_support": short.effective_support,
                "revived_after_observed_expiry": revived,
            },
            indent=2,
        )
    )
    return 1 if revived else 0


if __name__ == "__main__":
    raise SystemExit(main())
