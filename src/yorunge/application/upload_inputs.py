"""Strict private input revalidation without emitting rejected values as warnings."""

from typing import TypeVar

from pydantic import BaseModel

from yorunge.domain.capabilities import canonical
from yorunge.domain.errors import YorungeError

T = TypeVar("T", bound=BaseModel)


def revalidate_input(kind: type[T], value: T) -> T:
    if type(value) is not kind:
        raise YorungeError("invalid_request")
    checked: T | None = None
    try:
        # Python mode preserves bool/int distinctions and recursively exposes
        # nested copied models. Rejected values must never enter warning repr.
        scalars = value.model_dump(mode="python", warnings=False)
        validated = kind.model_validate(scalars, strict=True)
        checked = kind.model_validate_json(
            canonical(validated.model_dump(mode="json")), strict=True
        )
    except (ValueError, YorungeError):
        pass
    if checked is None:
        raise YorungeError("invalid_request")
    return checked
