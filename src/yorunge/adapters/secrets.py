import os

from yorunge.domain.credentials import EnvReference, SecretValue
from yorunge.domain.errors import YorungeError


class EnvSecretReader:
    def read(self, reference: EnvReference) -> SecretValue:
        value = os.environ.get(reference.name)
        if value is None:
            raise YorungeError("credential_unavailable")
        return SecretValue(value)
