import pytest

from yorunge.domain.models import has_control_characters


def test_control_character_rule_matches_previous_policy_for_every_unicode_codepoint():
    for codepoint in range(0x110000):
        assert has_control_characters(chr(codepoint)) == (codepoint < 32 or 127 <= codepoint <= 159)


@pytest.mark.parametrize("codepoint", [0, 9, 10, 31, 127, 128, 159])
@pytest.mark.parametrize("position", [0, 512, 1024])
def test_control_character_is_detected_at_every_part_of_a_long_string(codepoint, position):
    text = "p" * position + chr(codepoint) + "p" * (1024 - position)
    assert has_control_characters(text)


def test_empty_and_ordinary_multilingual_text_remain_allowed():
    assert not has_control_characters("")
    assert not has_control_characters("Yörünge 日本語 😀\u00a0\u200b")
