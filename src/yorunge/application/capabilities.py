"""Capability evidence policy and producer boundary; no public evidence admission."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol

from pydantic import ValidationError

from yorunge.domain.capabilities import (
    TTL,
    CachedCapability,
    CapabilityKey,
    CapabilityRecord,
    Evidence,
    canonical,
    instant,
    timestamp,
)
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Support


class Producer(Protocol):
    def observe(self, key: CapabilityKey, now: datetime) -> tuple[Evidence, ...]: ...


class LocalPolicyProducer:
    SOURCE = ("yorunge-local-policy", "1")

    def __init__(self, support: Support, reason: str) -> None:
        self.support, self.reason = support, reason

    def observe(self, key: CapabilityKey, now: datetime) -> tuple[Evidence, ...]:
        return (
            Evidence(
                kind="local_policy"
                if self.support in ("supported", "unsupported")
                else "not_verified",
                producer_id=self.SOURCE[0],
                producer_version=self.SOURCE[1],
                provenance="offline-selection-policy",
                support=self.support,
                reason_code=self.reason,
                checked_at=timestamp(now),
                expires_at=timestamp(now + timedelta(seconds=TTL[self.support])),
            ),
        )


def current_policy_result(
    result: CachedCapability, sources: frozenset[tuple[str, str]]
) -> CachedCapability:
    """A persisted source/version is not the currently composed producer manifest."""
    if result.record and any(
        (proof.producer_id, proof.producer_version) not in sources
        for proof in result.record.evidence
    ):
        return result.model_copy(
            update={
                "effective_support": "unknown",
                "freshness": "stale",
                "valid_until": None,
                "reason_code": "evidence_source_changed",
                "message": "Kayıtlı üretici sürümü değişmiş; güncel doğrulama gerekiyor.",
            }
        )
    return result


def combine(
    key: CapabilityKey,
    previous: CapabilityRecord | None,
    incoming: tuple[Evidence, ...],
    now: datetime,
    *,
    replace_own: bool,
) -> CapabilityRecord:
    """Merge fresh observations; aggregate TTL never shortens proof retention."""
    moment = timestamp(now)
    if not incoming or any(
        instant(e.checked_at) > now or instant(e.expires_at) <= now for e in incoming
    ):
        raise YorungeError("capability_expired")
    sources = {(e.producer_id, e.producer_version) for e in incoming}
    old = previous.evidence if previous else ()
    observations = [
        e
        for e in old
        if e.expires_at > moment
        and (not replace_own or (e.producer_id, e.producer_version) not in sources)
    ]
    observations.extend(incoming)
    unique: dict[bytes, Evidence] = {}
    for evidence in observations:
        semantic = evidence.semantic_key()
        before = unique.get(semantic)
        if before is None or (evidence.checked_at, canonical(evidence.model_dump(mode="json"))) > (
            before.checked_at,
            canonical(before.model_dump(mode="json")),
        ):
            unique[semantic] = evidence
    proofs = tuple(unique[k] for k in sorted(unique))
    signatures = {
        (e.support, canonical([c.model_dump(mode="json") for c in e.constraints])) for e in proofs
    }
    blocker = (
        previous.conflict_until
        if previous and previous.conflict_until and previous.conflict_until > moment
        else None
    )
    conflict = len(signatures) > 1 or blocker is not None
    support: Support = "unknown" if conflict else proofs[0].support
    checked = max(e.checked_at for e in proofs)
    expires = min(
        min(e.expires_at for e in proofs),
        timestamp(instant(checked) + timedelta(seconds=TTL[support])),
    )
    reason = "evidence_conflict" if conflict else proofs[0].reason_code
    message = (
        "Güncel kanıtlar bu kapsamda çelişiyor; destek doğrulanmadı."
        if conflict
        else {
            "offline_planner_implemented": "Yerel plan destekleniyor; yürütme yetkisi vermez.",
            "adapter_not_implemented": "Seçilen araç adaptörü henüz uygulanmadı; yürütülemez.",
            "service_not_verified": "Uzak hizmet ve hesap desteği doğrulanmadı.",
            "authorization_not_verified": "Uzak izin kapsamı doğrulanmadı.",
        }.get(reason, "Kanıt sonucu yalnız kayıtlı kapsam ve süre için geçerlidir.")
    )
    payload = dict(
        key=key,
        support=support,
        reason_code=reason,
        message=message,
        evidence=proofs,
        checked_at=checked,
        expires_at=expires,
        conflict_until=blocker,
    )
    size = len(
        canonical(
            {
                **payload,
                "key": key.model_dump(mode="json"),
                "evidence": [e.model_dump(mode="json") for e in proofs],
                "schema_version": 2,
            }
        )
    )
    if len(proofs) > 8 or size > 32768:
        # Do not keep an old positive decision when the contrary evidence cannot fit.
        until = max([e.expires_at for e in proofs] + ([blocker] if blocker else []))
        return CapabilityRecord(
            key=key,
            support="unknown",
            reason_code="evidence_overflow",
            message="Kanıt sınırı aşıldı; taze karşı kanıt kaybedilmeden destek engellendi.",
            evidence=(),
            checked_at=moment,
            expires_at=timestamp(now + timedelta(seconds=30)),
            conflict_until=until,
        )
    try:
        return CapabilityRecord(
            key=key,
            support=support,
            reason_code=reason,
            message=message,
            evidence=proofs,
            checked_at=checked,
            expires_at=expires,
            conflict_until=blocker,
        )
    except ValidationError:
        raise YorungeError("invalid_request") from None
