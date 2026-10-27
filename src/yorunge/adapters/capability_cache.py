"""Transactional cache and durable clock fencing on the shared local store."""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from pydantic import ValidationError

from yorunge.adapters.files import reject_constant, unique_object
from yorunge.adapters.identity import credential_matches
from yorunge.adapters.state import Store, metadata
from yorunge.application.capabilities import Producer, combine
from yorunge.domain.capabilities import (
    MAX_RECORD_BYTES,
    CachedCapability,
    CapabilityKey,
    CapabilityRecord,
    Freshness,
    canonical,
    instant,
    timestamp,
)
from yorunge.domain.credentials import CredentialIdentity
from yorunge.domain.errors import YorungeError
from yorunge.domain.state import canonical_uuid

MIN_TIME = "0001-01-01T00:00:00.000000Z"
ENTRY_FIELDS = (
    "cache_key,key_json,projection_key,group_key,payload,mutation_revision,checked_at,pinned_until"
)
SELECT_ENTRY = f"SELECT {ENTRY_FIELDS} FROM capability_cache WHERE cache_key=?"


class Clock(Protocol):
    def now(self) -> datetime: ...
    def monotonic(self) -> float: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        return time.monotonic()


@dataclass(frozen=True)
class Stamp:
    store_id: str
    identity_epoch: str
    generation: int
    now: datetime
    anomaly: bool


@dataclass(frozen=True)
class Token:
    present: bool
    revision: int


def decode_record(payload: object) -> CapabilityRecord:
    try:
        if not isinstance(payload, str) or len(payload.encode("utf-8")) > MAX_RECORD_BYTES:
            raise ValueError("bounded record required")
        raw = json.loads(payload, object_pairs_hook=unique_object, parse_constant=reject_constant)
        if not isinstance(raw, dict) or type(raw.get("schema_version")) is not int:
            raise ValueError("explicit record version required")
        return CapabilityRecord.model_validate_json(payload)
    except (ValueError, ValidationError, RecursionError, YorungeError):
        raise YorungeError("state_invalid") from None


def decode_entry(row: tuple[object, ...]) -> tuple[CapabilityRecord, int]:
    digest, encoded, projection, group, payload, revision, checked, pinned = row
    record = decode_record(payload)
    if (
        (digest, encoded, projection, group, checked, pinned)
        != (
            record.key.digest(),
            record.key.encoded().decode("ascii"),
            record.key.projection(),
            group_key(record.key),
            record.checked_at,
            record.pinned_until(),
        )
        or type(revision) is not int
        or not 1 <= revision <= 2**63 - 1
    ):
        raise YorungeError("state_invalid")
    return record, revision


def validate_cache(connection: sqlite3.Connection) -> None:
    # Called only for schema versions that own these tables; no adapters at domain import.
    row = connection.execute(
        "SELECT identity_epoch,clock_generation,high_watermark,anomaly_active,"
        "mutation_revision FROM cache_clock WHERE singleton=1"
    ).fetchone()
    try:
        if row is None:
            raise ValueError("clock missing")
        epoch, generation, high, anomaly, revision = row
        canonical_uuid(epoch)
        instant(high)
        if (
            epoch != metadata(connection).identity_epoch
            or type(generation) is not int
            or not 1 <= generation <= 2**63 - 1
            or anomaly not in (0, 1)
            or type(revision) is not int
            or not 0 <= revision <= 2**63 - 1
        ):
            raise ValueError("clock invalid")
    except (ValueError, TypeError):
        raise YorungeError("state_invalid") from None
    count = 0
    value = metadata(connection)
    for row in connection.execute(f"SELECT {ENTRY_FIELDS} FROM capability_cache"):
        record, version = decode_entry(row)
        if (
            record.key.scope.store_id != value.store_id
            or record.key.scope.identity_epoch != value.identity_epoch
            or record.key.scope.clock_generation > generation
            or version > revision
        ):
            raise YorungeError("state_invalid")
        count += 1
        if count > 1024:
            raise YorungeError("state_invalid")
    if connection.execute(
        "SELECT group_key FROM capability_cache GROUP BY group_key HAVING count(*)>128 LIMIT 1"
    ).fetchone():
        raise YorungeError("state_invalid")


def group_key(key: CapabilityKey) -> str:
    scope = key.scope
    return (
        f"{scope.identity_epoch}:{scope.credential_id or 'local'}:{scope.credential_revision or 0}"
    )


class StateCache:
    def __init__(
        self,
        store: Store,
        clock: Clock | None = None,
        *,
        bindings: tuple[CredentialIdentity, ...] = (),
    ) -> None:
        self.store, self.connection = store, store.connection
        self.clock = clock or SystemClock()
        self.end = self.clock.monotonic() + 5.0
        self.bindings = bindings

    def now(self) -> datetime:
        self.observed = self.clock.now()
        return self.observed

    def _tick(self, now: datetime) -> Stamp:
        self.observed = now
        value = metadata(self.connection)
        row = self.connection.execute(
            "SELECT identity_epoch,clock_generation,high_watermark,anomaly_active,"
            "mutation_revision FROM cache_clock WHERE singleton=1"
        ).fetchone()
        if row is None or row[0] != value.identity_epoch:
            raise YorungeError("state_invalid")
        epoch, generation, high, anomaly, revision = row
        try:
            canonical_uuid(epoch)
            instant(high)
            if (
                type(generation) is not int
                or not 1 <= generation <= 2**63 - 1
                or anomaly not in (0, 1)
                or type(revision) is not int
                or not 0 <= revision <= 2**63 - 1
            ):
                raise ValueError("invalid clock")
        except (ValueError, TypeError):
            raise YorungeError("state_invalid") from None
        moment = timestamp(now)
        if moment < high:
            if not anomaly:
                if generation == 2**63 - 1:
                    raise YorungeError("state_invalid")
                generation += 1
            anomaly = 1
        else:
            high, anomaly = moment, 0
        self.connection.execute(
            "UPDATE cache_clock SET clock_generation=?,high_watermark=?,anomaly_active=? "
            "WHERE singleton=1",
            (generation, high, anomaly),
        )
        return Stamp(value.store_id, epoch, generation, now, bool(anomaly))

    def stamp(self) -> Stamp:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            result = self._tick(self.now())
            self.connection.execute("COMMIT")
            return result
        finally:
            if self.connection.in_transaction:
                self.connection.execute("ROLLBACK")

    def _bindings(self, stamp: Stamp) -> None:
        value = metadata(self.connection)
        if (value.store_id, value.identity_epoch) != (stamp.store_id, stamp.identity_epoch):
            raise YorungeError("state_changed")
        for identity in self.bindings:
            if identity.identity_epoch != stamp.identity_epoch or not credential_matches(
                self.connection,
                identity.credential_id,
                stamp.identity_epoch,
                identity.credential_revision,
            ):
                raise YorungeError("state_changed")

    def _same(self, expected: Stamp, found: Stamp) -> None:
        self._bindings(expected)
        if (
            found.generation != expected.generation
            or found.anomaly
            or self.clock.monotonic() >= self.end
        ):
            raise YorungeError(
                "state_changed" if found.generation != expected.generation else "capability_expired"
            )
        self.store.deadline.remaining()

    @contextmanager
    def transaction(self, stamp: Stamp) -> Iterator[None]:
        """Clock changes survive a business rollback, including the final time gate."""
        connection = self.connection
        connection.execute("BEGIN IMMEDIATE")
        observed = self.now()
        try:
            self._tick(observed)
            connection.execute("SAVEPOINT business")
            try:
                self._same(stamp, self._tick(self.now()))
                yield
                observed = self.now()
                self._same(stamp, self._tick(observed))
            except BaseException:
                observed = self.observed
                connection.execute("ROLLBACK TO business")
                self._tick(observed)
                connection.execute("RELEASE business")
                connection.execute("COMMIT")
                raise
            connection.execute("RELEASE business")
            connection.execute("COMMIT")
        finally:
            if connection.in_transaction:
                connection.execute("ROLLBACK")

    def _read(self, key: CapabilityKey) -> tuple[CapabilityRecord | None, Token]:
        self._key_guard(key)
        row = self.connection.execute(SELECT_ENTRY, (key.digest(),)).fetchone()
        mutation = self.connection.execute(
            "SELECT mutation_revision FROM cache_clock WHERE singleton=1"
        ).fetchone()[0]
        if row is None:
            return None, Token(False, mutation)
        record, revision = decode_entry(row)
        if record.key != key or revision > mutation:
            raise YorungeError("state_invalid")
        return record, Token(True, revision)

    def _key_guard(self, key: CapabilityKey) -> None:
        scope, value = key.scope, metadata(self.connection)
        row = self.connection.execute(
            "SELECT clock_generation FROM cache_clock WHERE singleton=1"
        ).fetchone()
        if (scope.store_id, scope.identity_epoch, scope.clock_generation) != (
            value.store_id,
            value.identity_epoch,
            row[0],
        ):
            raise YorungeError("state_changed")
        if scope.credential_id is not None and not credential_matches(
            self.connection,
            scope.credential_id,
            scope.identity_epoch,
            scope.credential_revision or 0,
            service=scope.service_id,
            origin=scope.service_origin,
            base=scope.api_base_path,
        ):
            raise YorungeError("state_changed")

    def refresh(self, key: CapabilityKey, stamp: Stamp, producer: Producer) -> None:
        with self.transaction(stamp):
            _, token = self._read(key)
        incoming = producer.observe(key, self.now())
        with self.transaction(stamp):
            previous, current = self._read(key)
            now = self.now()
            record = combine(key, previous, incoming, now, replace_own=current == token)
            self._prune_and_reserve(key, now)
            self._same(stamp, self._tick(self.now()))
            if not instant(record.checked_at) <= self.now() < instant(record.expires_at):
                raise YorungeError("capability_expired")
            revision = self.connection.execute(
                "SELECT mutation_revision FROM cache_clock WHERE singleton=1"
            ).fetchone()[0]
            if revision == 2**63 - 1:
                raise YorungeError("state_invalid")
            revision += 1
            self.connection.execute(
                "UPDATE cache_clock SET mutation_revision=? WHERE singleton=1", (revision,)
            )
            self.connection.execute(
                "INSERT OR REPLACE INTO capability_cache VALUES(?,?,?,?,?,?,?,?)",
                (
                    key.digest(),
                    key.encoded().decode("ascii"),
                    key.projection(),
                    group_key(key),
                    canonical(record.model_dump(mode="json")).decode("ascii"),
                    revision,
                    record.checked_at,
                    record.pinned_until(),
                ),
            )
            if not instant(record.checked_at) <= self.now() < instant(record.expires_at):
                raise YorungeError("capability_expired")

    def _prune_and_reserve(self, key: CapabilityKey, now: datetime) -> None:
        moment = timestamp(now)
        rows = self.connection.execute(
            f"SELECT {ENTRY_FIELDS} FROM capability_cache ORDER BY checked_at,cache_key"
        ).fetchall()
        survivors: list[tuple[str, str, str, str | None]] = []
        for row in rows:
            self.store.deadline.remaining()
            record, _ = decode_entry(row)
            digest, group, checked = record.key.digest(), group_key(record.key), record.checked_at
            if record.key.scope.store_id != key.scope.store_id:
                raise YorungeError("state_invalid")
            scope = record.key.scope
            stale = (scope.identity_epoch, scope.clock_generation) != (
                key.scope.identity_epoch,
                key.scope.clock_generation,
            )
            if scope.credential_id is not None:
                stale = stale or not credential_matches(
                    self.connection,
                    scope.credential_id,
                    scope.identity_epoch,
                    scope.credential_revision or 0,
                    service=scope.service_id,
                    origin=scope.service_origin,
                    base=scope.api_base_path,
                )
            dead = not any(e.expires_at > moment for e in record.evidence) and not (
                record.conflict_until and record.conflict_until > moment
            )
            if digest != key.digest() and (stale or dead):
                self.connection.execute("DELETE FROM capability_cache WHERE cache_key=?", (digest,))
            else:
                survivors.append((digest, group, checked, record.pinned_until(moment)))
        # Reserve one slot for an upsert, respecting pinned conflicts in either quota.
        others = [r for r in survivors if r[0] != key.digest()]
        while len(others) >= 1024 or sum(r[1] == group_key(key) for r in others) >= 128:
            group_full = sum(r[1] == group_key(key) for r in others) >= 128
            victim = next(
                (
                    r
                    for r in others
                    if (not group_full or r[1] == group_key(key))
                    and (r[3] is None or r[3] <= moment)
                ),
                None,
            )
            if victim is None:
                raise YorungeError("capability_capacity_exceeded")
            self.connection.execute("DELETE FROM capability_cache WHERE cache_key=?", (victim[0],))
            others.remove(victim)

    def query(self, key: CapabilityKey, stamp: Stamp) -> CachedCapability:
        record = None
        candidates: tuple[CapabilityRecord, ...] = ()
        try:
            with self.transaction(stamp):
                record, _ = self._read(key)
                if record is None and key.scope.authorization_scope is None:
                    candidates = tuple(
                        decode_entry(row)[0]
                        for row in self.connection.execute(
                            f"SELECT {ENTRY_FIELDS} FROM capability_cache WHERE projection_key=? "
                            "ORDER BY checked_at DESC,cache_key LIMIT 4",
                            (key.projection(),),
                        )
                    )
        except YorungeError as error:
            if error.code == "state_changed":
                self._bindings(stamp)
            elif error.code != "capability_expired":
                raise
        final = self.stamp()
        self._bindings(stamp)
        if final.generation == stamp.generation:
            self._key_guard(key)
        if any(candidate.key.projection() != key.projection() for candidate in candidates):
            raise YorungeError("state_invalid")
        now = timestamp(final.now)
        fresh = (
            record is not None
            and not final.anomaly
            and final.generation == stamp.generation
            and record.checked_at <= now < record.expires_at
            and self.clock.monotonic() < self.end
        )
        freshness: Freshness = (
            "fresh"
            if fresh
            else "clock_anomaly"
            if final.anomaly or final.generation != stamp.generation
            else "stale"
            if record
            else "historical_only"
            if candidates
            else "miss"
        )
        return CachedCapability(
            key=key,
            hit=record is not None,
            freshness=freshness,
            effective_support=record.support if fresh and record else "unknown",
            reason_code=record.reason_code
            if fresh and record
            else "authorization_scope_unverified"
            if candidates
            else "cache_" + freshness,
            checked_at=now,
            message=record.message
            if fresh and record
            else (
                "İzin kapsamı bilinmiyor; aday kayıt yalnız tarihsel bilgidir."
                if candidates
                else "Güncel geçerli cache kararı yok; açık yenileme veya doğrulama gerekiyor."
            ),
            valid_until=record.expires_at if fresh and record else None,
            record=record,
            historical_candidates=candidates,
        )
