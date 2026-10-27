"""Transactional identity observations; secrets never enter SQL parameters."""

from __future__ import annotations

import hmac
from uuid import uuid4

from pydantic import ValidationError

from yorunge.adapters.state import Store, load_key, metadata, utc_now
from yorunge.domain.credentials import (
    TAG_FORMAT,
    CredentialBinding,
    CredentialIdentity,
    ResolvedCredential,
    observation_tag,
)
from yorunge.domain.errors import YorungeError

WHERE_BINDING = (
    "identity_epoch=? AND service_id=? AND service_origin=? AND api_base_path=? "
    "AND reference_type=? AND reference_name=?"
)


class StateCredentialRegistry:
    def __init__(self, store: Store) -> None:
        self.store = store

    def observe(self, credential: ResolvedCredential) -> CredentialIdentity:
        store = self.store
        before = metadata(store.connection)
        binding = CredentialBinding(
            identity_epoch=before.identity_epoch,
            service_id=credential.reference.service_id,
            **credential.target.model_dump(),
            reference_type=credential.reference.kind,
            reference_name=credential.reference.name,
        )
        tag = observation_tag(binding, load_key(store.root, before), credential.secret)
        connection = store.connection
        connection.execute("BEGIN IMMEDIATE")
        try:
            if metadata(connection) != before:
                raise YorungeError("state_changed")
            row = connection.execute(
                "SELECT credential_id,revision,observed_at,tag_format,tag "
                "FROM credential_bindings WHERE " + WHERE_BINDING,
                binding.as_key(),
            ).fetchone()
            if row is None:
                result = CredentialIdentity(
                    credential_id=str(uuid4()),
                    credential_revision=1,
                    identity_epoch=before.identity_epoch,
                    observed_at=utc_now(),
                )
                connection.execute(
                    "INSERT INTO credential_bindings VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        *binding.as_key(),
                        result.credential_id,
                        result.credential_revision,
                        TAG_FORMAT,
                        tag,
                        result.observed_at,
                    ),
                )
            else:
                identifier, revision, timestamp, fmt, previous = row
                try:
                    result = CredentialIdentity(
                        credential_id=identifier,
                        credential_revision=revision,
                        identity_epoch=before.identity_epoch,
                        observed_at=timestamp,
                    )
                except ValidationError:
                    raise YorungeError("state_invalid") from None
                if fmt != TAG_FORMAT or not isinstance(previous, bytes) or len(previous) != 32:
                    raise YorungeError("state_invalid")
                if not hmac.compare_digest(previous, tag):
                    if revision == 2**63 - 1:
                        raise YorungeError("credential_revision_exhausted")
                    result = CredentialIdentity(
                        credential_id=identifier,
                        credential_revision=revision + 1,
                        identity_epoch=before.identity_epoch,
                        observed_at=utc_now(),
                    )
                    connection.execute(
                        "UPDATE credential_bindings SET revision=?,tag=?,observed_at=? WHERE "
                        + WHERE_BINDING,
                        (result.credential_revision, tag, result.observed_at, *binding.as_key()),
                    )
            store.deadline.remaining()
            connection.execute("COMMIT")
            return result
        finally:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
