"""Repeated syntax checks retain Unicode byte limits and strict JSON semantics."""

import pytest

from yorunge.domain.capabilities import WireModel


class TextRecord(WireModel):
    text: str


@pytest.mark.parametrize(
    "value", ["a" * 128, "a" * 129, "a" * 2048, "é" * 1024, "😀" * 512, "a" * 2044 + "😀"]
)
def test_repeated_text_validation_preserves_exact_unicode_at_byte_limit(value):
    for _ in range(2):
        assert TextRecord(text=value).text == value


@pytest.mark.parametrize(
    "invalid", ["safe\x00", "safe\n", "safe\x7f", "é\x85", "a" * 2049, "é" * 1025, "\ud800"]
)
def test_warming_a_valid_text_does_not_accept_invalid_or_oversized_text(invalid):
    assert TextRecord(text="safe").text == "safe"
    for _ in range(2):
        with pytest.raises(ValueError):
            TextRecord(text=invalid)


@pytest.mark.parametrize(
    "payload", ['{"text":"same","text":"same"}', '{"text":"same","t\\u0065xt":"same"}']
)
def test_duplicate_names_are_rejected_even_when_values_match_or_key_is_escaped(payload):
    with pytest.raises(ValueError, match="duplicate wire key"):
        TextRecord.model_validate_json(payload)
