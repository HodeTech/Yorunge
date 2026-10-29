"""Transactional cache and durable clock fencing on the shared local store."""

from __future__ import annotations

import hashlib
import sqlite3
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, cast

from pydantic import ValidationError

from yorunge.adapters.expiry_fences import (
    MAX_STATE_EXPIRIES,
    cache_expiries,
    check_expiries,
    check_expiry_dates,
    next_expiry,
    save_expiries,
)
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
from yorunge.domain.errors import ErrorCode, YorungeError
from yorunge.domain.models import Support
from yorunge.domain.state import canonical_uuid

MIN_TIME = "0001-01-01T00:00:00.000000Z"
ENTRY_FIELDS = (
    "cache_key,key_json,projection_key,group_key,payload,mutation_revision,checked_at,pinned_until"
)
SELECT_ENTRY = f"SELECT {ENTRY_FIELDS} FROM capability_cache WHERE cache_key=?"
SELECT_CLOCK = (
    "SELECT identity_epoch,clock_generation,high_watermark,anomaly_active,"
    "mutation_revision FROM cache_clock WHERE singleton=1"
)
ClockRow = tuple[str, int, str, int, int]


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


@dataclass(frozen=True)
class ClockCheckpoint:
    stamp: Stamp
    row: ClockRow


@dataclass(frozen=True)
class TerminalPoint:
    row: ClockRow | None
    now: datetime
    frontier: datetime | None
    expiries: tuple[datetime, ...]
    within_budget: bool


@dataclass
class TimeGate:
    intervals: list[tuple[datetime, datetime, ErrorCode]] = field(default_factory=list)
    clocks: list[tuple[str, int, ErrorCode]] = field(default_factory=list)
    checkpoint: ClockCheckpoint | None = None

    def require(self, record: CapabilityRecord) -> None:
        self.require_range(instant(record.checked_at), instant(record.expires_at))

    def require_range(
        self, start: datetime, end: datetime, *, error: ErrorCode = "capability_expired"
    ) -> None:
        self.intervals.append((start, end, error))

    def require_clock(self, stamp: Stamp, *, error: ErrorCode) -> None:
        self.clocks.append((stamp.identity_epoch, stamp.generation, error))

    def check_clock(self, stamp: Stamp) -> None:
        for epoch, generation, error in self.clocks:
            if stamp.anomaly or (epoch, generation) != (stamp.identity_epoch, stamp.generation):
                raise YorungeError(error)

    def check(self, now: datetime) -> None:
        for start, end, error in self.intervals:
            if not start <= now < end:
                raise YorungeError(error)


def decode_record(payload: object) -> CapabilityRecord:
    try:
        if not isinstance(payload, str) or len(payload.encode("utf-8")) > MAX_RECORD_BYTES:
            raise ValueError("bounded record required")
        record = CapabilityRecord.model_validate_json(payload)
        if "schema_version" not in record.model_fields_set:
            raise ValueError("explicit record version required")
        return record
    except (ValueError, ValidationError, RecursionError, YorungeError):
        raise YorungeError("state_invalid") from None


def decode_entry(row: tuple[object, ...]) -> tuple[CapabilityRecord, int]:
    digest, encoded, projection, group, payload, revision, checked, pinned = row
    record = decode_record(payload)
    key_bytes = record.key.encoded()
    if (
        (digest, encoded, projection, group, checked, pinned)
        != (
            hashlib.sha256(key_bytes).hexdigest(),
            key_bytes.decode("ascii"),
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


@dataclass(frozen=True)
class CacheValidation:
    key: str
    store_id: str
    identity_epoch: str
    clock_generation: int
    revision: int
    expiries: tuple[str, ...]


def cache_validation(row: tuple[object, ...]) -> CacheValidation:
    from yorunge.adapters.validation_memo import validated

    def build() -> CacheValidation:
        record, version = decode_entry(row)
        scope = record.key.scope
        return CacheValidation(
            cast(str, row[0]),  # decode_entry just matched this same row against the key digest.
            scope.store_id,
            scope.identity_epoch,
            scope.clock_generation,
            version,
            cache_expiries(record),
        )

    return validated(CacheValidation, row, build)


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
    indexed = connection.execute(
        "SELECT 1 FROM sqlite_schema WHERE type='table' AND name='capability_expiries'"
    ).fetchone()
    for row in connection.execute(f"SELECT {ENTRY_FIELDS} FROM capability_cache"):
        record = cache_validation(row)
        if indexed:
            check_expiry_dates(connection, record.key, record.expiries)
        if (
            record.store_id != value.store_id
            or record.identity_epoch != value.identity_epoch
            or record.clock_generation > generation
            or record.revision > revision
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
        budget_seconds: float = 5.0,
    ) -> None:
        self.store, self.connection = store, store.connection
        self.clock = clock or SystemClock()
        self.end = self.clock.monotonic() + budget_seconds
        self.bindings = bindings
        self.observation_high: datetime | None = None
        self.observation_anomaly = False
        self.required_generation = 0
        self.generation = 0
        self.checks: tuple[Callable[[], None], ...] = ()
        self.additional_expiries: Callable[[], tuple[datetime, ...]] = lambda: ()
        self._checkpoint: ClockCheckpoint | None = None

    def now(self) -> datetime:
        self.observed = self.clock.now()
        if self.observation_high is not None and self.observed < self.observation_high:
            if not self.observation_anomaly:
                self.required_generation = max(self.required_generation, self.generation + 1)
            self.observation_anomaly = True
        else:
            self.observation_high = self.observed
            self.observation_anomaly = False
        return self.observed

    def _tick(self, now: datetime) -> Stamp:
        self.observed = now
        value = metadata(self.connection)
        row = self.connection.execute(SELECT_CLOCK).fetchone()
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
        if self.observation_high is not None:
            high = max(high, timestamp(self.observation_high))
        if moment < high:
            if not anomaly:
                if generation == 2**63 - 1:
                    raise YorungeError("state_invalid")
                generation += 1
            anomaly = 1
        else:
            high, anomaly = moment, 0
        generation = max(generation, self.required_generation)
        if generation > 2**63 - 1:
            raise YorungeError("state_invalid")
        self.generation = generation
        self.observation_high = instant(high)
        self.observation_anomaly = bool(anomaly)
        self.connection.execute(
            "UPDATE cache_clock SET clock_generation=?,high_watermark=?,anomaly_active=? "
            "WHERE singleton=1",
            (generation, high, anomaly),
        )
        return Stamp(value.store_id, epoch, generation, now, bool(anomaly))

    def _save_stamp(self, rollback: datetime | None = None) -> Stamp:
        self._checkpoint = None
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            if rollback is not None:
                self._tick(rollback)
            result = self._tick(self.now())
            row = self.connection.execute(SELECT_CLOCK).fetchone()
            self.connection.execute("COMMIT")
            self._checkpoint = ClockCheckpoint(result, row)
            return result
        finally:
            if self.connection.in_transaction:
                self.connection.execute("ROLLBACK")

    def stamp(self) -> Stamp:
        """Durable clock point; consumers obtain a terminal point through _finish."""
        return self._save_stamp()

    def _durable_checkpoint(self, observed: datetime | None = None) -> ClockCheckpoint:
        if observed is None:
            self.stamp()
        else:
            self._save_stamp(observed)
        if self._checkpoint is None:
            raise YorungeError("state_invalid")
        return self._checkpoint

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

        for check in self.checks:
            check()

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
    def transaction(
        self, stamp: Stamp, *, clock_error: ErrorCode | None = None
    ) -> Iterator[TimeGate]:
        """Clock changes survive a business rollback, including the final time gate."""
        connection = self.connection
        connection.execute("BEGIN IMMEDIATE")
        observed = self.now()
        gate = TimeGate()
        if clock_error is not None:
            gate.require_clock(stamp, error=clock_error)
        try:
            self._tick(observed)
            connection.execute("SAVEPOINT business")
            try:
                current = self._tick(self.now())
                gate.check_clock(current)
                self._same(stamp, current)
                yield gate
                observed = self.now()
                final = self._tick(observed)
                gate.check_clock(final)
                self._same(stamp, final)
                gate.check(observed)
                clock_row = self.connection.execute(SELECT_CLOCK).fetchone()
            except BaseException:
                observed = self.observed
                connection.execute("ROLLBACK TO business")
                self._tick(observed)
                connection.execute("RELEASE business")
                connection.execute("COMMIT")
                raise
            connection.execute("RELEASE business")
            connection.execute("COMMIT")
            gate.checkpoint = ClockCheckpoint(final, clock_row)
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
        check_expiries(self.connection, record)
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
        observed = self.stamp()
        self._same(stamp, observed)
        try:
            incoming = producer.observe(key, observed.now)
        finally:
            # A failed producer cannot discard a clock observation or revive old proof.
            self._same(stamp, self.stamp())
        with self.transaction(stamp) as gate:
            previous, current = self._read(key)
            now = self.now()
            record = combine(key, previous, incoming, now, replace_own=current == token)
            gate.require(record)
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
            save_expiries(self.connection, record)
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
            obsolete = self._obsolete(record, key, moment)
            if digest != key.digest() and obsolete:
                self.connection.execute("DELETE FROM capability_cache WHERE cache_key=?", (digest,))
            else:
                survivors.append((digest, group, checked, record.pinned_until(moment)))
        self._reserve(key, survivors, moment)

    def _obsolete(self, record: CapabilityRecord, key: CapabilityKey, moment: str) -> bool:
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
        return stale or dead

    def _reserve(
        self,
        key: CapabilityKey,
        survivors: list[tuple[str, str, str, str | None]],
        moment: str,
    ) -> None:
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
        return self.query_many((key,), stamp)[0]

    def query_many(
        self, keys: tuple[CapabilityKey, ...], stamp: Stamp
    ) -> tuple[CachedCapability, ...]:
        rows: list[tuple[CapabilityRecord | None, tuple[CapabilityRecord, ...]]] = [
            (None, ()) for _ in keys
        ]
        checkpoint = None
        try:
            with self.transaction(stamp) as gate:
                for index, key in enumerate(keys):
                    record, _ = self._read(key)
                    candidates: tuple[CapabilityRecord, ...] = ()
                    if record is None and key.scope.authorization_scope is None:
                        candidates = tuple(
                            decode_entry(row)[0]
                            for row in self.connection.execute(
                                f"SELECT {ENTRY_FIELDS} FROM capability_cache "
                                "WHERE projection_key=? "
                                "ORDER BY checked_at DESC,cache_key LIMIT 4",
                                (key.projection(),),
                            )
                        )
                    rows[index] = record, candidates
            checkpoint = gate.checkpoint
        except YorungeError as error:
            if error.code == "state_changed":
                self._bindings(stamp)
            elif error.code != "capability_expired":
                raise
        final, within_budget = self._finish(
            stamp,
            tuple(instant(record.expires_at) for record, _ in rows if record is not None),
            checkpoint=checkpoint,
        )
        return tuple(
            self._present(key, record, candidates, stamp, final, within_budget)
            for key, (record, candidates) in zip(keys, rows, strict=True)
        )

    def _finish(
        self,
        stamp: Stamp,
        expires: tuple[datetime, ...] = (),
        *,
        checkpoint: ClockCheckpoint | None = None,
    ) -> tuple[Stamp, bool]:
        checkpoint = checkpoint or self._durable_checkpoint()
        # The hard cap also bounds concurrent writers replacing expiry dates.
        # Every continuation persists the observed UTC before the next sample.
        for _ in range(MAX_STATE_EXPIRIES + 1):
            current = checkpoint.stamp
            point = self._terminal_point(stamp, checkpoint)
            if point.row != checkpoint.row:
                checkpoint = self._durable_checkpoint(point.now)
                continue
            if point.now < current.now or self.required_generation > current.generation:
                return self._save_stamp(point.now), point.within_budget
            if self._crossed_expiry(current, point, expires):
                checkpoint = self._durable_checkpoint(point.now)
                continue
            if current.anomaly or current.generation != stamp.generation:
                return current, point.within_budget
            return Stamp(
                current.store_id,
                current.identity_epoch,
                current.generation,
                point.now,
                current.anomaly,
            ), point.within_budget
        raise YorungeError("state_busy")

    def _terminal_point(self, stamp: Stamp, checkpoint: ClockCheckpoint) -> TerminalPoint:
        self.connection.execute("BEGIN")
        try:
            # Hold the read snapshot through the UTC sample and frontier lookup:
            # a writer cannot commit a newly expiring record between them.
            self._bindings(stamp)
            self.store.deadline.remaining()
            observed = self.now()
            row = self.connection.execute(SELECT_CLOCK).fetchone()
            frontier = (
                next_expiry(self.connection, checkpoint.row[2]) if row == checkpoint.row else None
            )
            expiries = self.additional_expiries()
        finally:
            self.connection.execute("ROLLBACK")
        return TerminalPoint(row, observed, frontier, expiries, self.clock.monotonic() < self.end)

    @staticmethod
    def _crossed_expiry(
        current: Stamp, point: TerminalPoint, expires: tuple[datetime, ...]
    ) -> bool:
        return (point.frontier is not None and point.frontier <= point.now) or any(
            current.now < boundary <= point.now for boundary in (*expires, *point.expiries)
        )

    def _present(
        self,
        key: CapabilityKey,
        record: CapabilityRecord | None,
        candidates: tuple[CapabilityRecord, ...],
        stamp: Stamp,
        final: Stamp,
        within_budget: bool,
    ) -> CachedCapability:
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
            and within_budget
        )
        freshness = self._freshness(fresh, final, stamp, record, candidates)
        support: Support
        support, reason, message, valid_until = (
            "unknown",
            "cache_" + freshness,
            "Güncel geçerli cache kararı yok; açık yenileme veya doğrulama gerekiyor.",
            None,
        )
        if fresh and record:
            support, reason, message, valid_until = (
                record.support,
                record.reason_code,
                record.message,
                record.expires_at,
            )
        elif candidates:
            reason = "authorization_scope_unverified"
            message = "İzin kapsamı bilinmiyor; aday kayıt yalnız tarihsel bilgidir."
        return CachedCapability(
            key=key,
            hit=record is not None,
            freshness=freshness,
            effective_support=support,
            reason_code=reason,
            checked_at=now,
            message=message,
            valid_until=valid_until,
            record=record,
            historical_candidates=candidates,
        )

    @staticmethod
    def _freshness(
        fresh: bool,
        final: Stamp,
        stamp: Stamp,
        record: CapabilityRecord | None,
        candidates: tuple[CapabilityRecord, ...],
    ) -> Freshness:
        if fresh:
            return "fresh"
        if final.anomaly or final.generation != stamp.generation:
            return "clock_anomaly"
        if record:
            return "stale"
        if candidates:
            return "historical_only"
        return "miss"
