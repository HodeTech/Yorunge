from typing import Protocol

from yorunge.domain.credentials import (
    EnvReference,
    ResolvedCredential,
    SecretValue,
    ServiceId,
    normalize_target,
)
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Profile


class SecretReader(Protocol):
    def read(self, reference: EnvReference) -> SecretValue: ...


def resolve_credential(
    profile: Profile, service_id: ServiceId, reader: SecretReader
) -> ResolvedCredential:
    if service_id not in ("evren-platform", "evren-llm"):
        raise YorungeError("invalid_request")
    if service_id == "evren-platform":
        url, name = profile.platform_url, profile.platform_key_env
    else:
        url, name = profile.llm_url, profile.llm_key_env
    target = normalize_target(url)
    if name is None:
        raise YorungeError("credential_unavailable")
    reference = EnvReference(service_id=service_id, name=name)
    return ResolvedCredential(reference=reference, target=target, secret=reader.read(reference))
