"""Short existing-store transactions around a lock-free remote observation."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from yorunge.adapters.capability_cache import Stamp, StateCache
from yorunge.adapters.identity import StateCredentialRegistry, credential_matches
from yorunge.adapters.state import open_existing_store
from yorunge.application.context_discovery import (
    DiscoverySnapshot,
    ObservationClock,
    remaining,
)
from yorunge.application.credentials import SecretReader, bind_credential, resolve_credential
from yorunge.domain.capabilities import timestamp
from yorunge.domain.discovery import DiscoveryBinding
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Context, Profile


class StateDiscovery:
    def __init__(
        self,
        state_dir: Path | None,
        context_loader: Callable[[], tuple[Context, Profile]],
        secret_reader: SecretReader,
        clock: ObservationClock,
    ) -> None:
        self.state_dir, self.context_loader = state_dir, context_loader
        self.secret_reader, self.clock = secret_reader, clock

    def capture(self, *, deadline: float) -> DiscoverySnapshot:
        seconds = min(5.0, remaining(deadline, self.clock))
        with open_existing_store(self.state_dir, timeout=seconds) as store:
            # Validate the existing store before resolving any secret reference.
            context, profile = self.context_loader()
            credential = resolve_credential(profile, "evren-llm", self.secret_reader)
            remaining(deadline, self.clock)
            identity = bind_credential(context, credential, StateCredentialRegistry(store)).identity
            cache = StateCache(store, self.clock, bindings=(identity,), budget_seconds=seconds)
            row = store.connection.execute(
                "SELECT clock_generation FROM cache_clock WHERE singleton=1"
            ).fetchone()
            if row is None or type(row[0]) is not int or not 1 <= row[0] <= 2**63 - 1:
                raise YorungeError("state_invalid")
            self._observed_clock(cache, row[0])
            captured = cache.stamp()
            if captured.anomaly or self.clock.regressed:
                raise YorungeError("state_changed")
            store.deadline.remaining()
            remaining(deadline, self.clock)
            return DiscoverySnapshot(
                context=context,
                credential=credential,
                identity=identity,
                binding=DiscoveryBinding(
                    store_id=captured.store_id,
                    identity_epoch=captured.identity_epoch,
                    clock_generation=captured.generation,
                    credential_id=identity.credential_id,
                    credential_revision=identity.credential_revision,
                ),
                captured_at=captured.now,
            )

    def finish(self, snapshot: DiscoverySnapshot, *, deadline: float) -> str:
        seconds = min(5.0, remaining(deadline, self.clock))
        with open_existing_store(self.state_dir, timeout=seconds) as store:
            binding = snapshot.binding
            expected = Stamp(
                binding.store_id,
                binding.identity_epoch,
                binding.clock_generation,
                snapshot.captured_at,
                False,
            )
            cache = StateCache(
                store, self.clock, bindings=(snapshot.identity,), budget_seconds=seconds
            )
            self._observed_clock(cache, binding.clock_generation)

            def same_target() -> None:
                target = snapshot.credential.target
                if not credential_matches(
                    store.connection,
                    binding.credential_id,
                    binding.identity_epoch,
                    binding.credential_revision,
                    service="evren-llm",
                    origin=target.service_origin,
                    base=target.api_base_path,
                ):
                    raise YorungeError("state_changed")

            cache.checks = (same_target,)
            with cache.transaction(expected, clock_error="state_changed") as gate:
                remaining(deadline, self.clock)
            # Reuse the global frontier/clock gate, including changes around COMMIT.
            final, within_budget = cache._finish(expected, checkpoint=gate.checkpoint)
            if final.anomaly or final.generation != binding.clock_generation:
                raise YorungeError("state_changed")
            if not within_budget:
                raise YorungeError("state_busy")
            store.deadline.remaining()
            remaining(deadline, self.clock)
            return timestamp(final.now)

    def _observed_clock(self, cache: StateCache, generation: int) -> None:
        cache.observation_high = self.clock.highest
        if self.clock.regressed:
            if generation == 2**63 - 1:
                raise YorungeError("state_invalid")
            cache.required_generation = generation + 1
