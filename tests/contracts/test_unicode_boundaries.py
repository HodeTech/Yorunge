from pathlib import Path

import pytest

from yorunge.domain.models import (
    MAX_REPORTED_PATH_BYTES,
    has_control_characters,
    is_reportable_path,
)


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


def test_a_reportable_path_is_printable_strict_utf8_and_at_most_4096_bytes():
    assert MAX_REPORTED_PATH_BYTES == 4096
    for good in ("/", "/tmp/a.json", "/tmp/Yörünge/日本語 😀.json", "x" * 4096, "é" * 2048):
        assert is_reportable_path(good), good[:20]
    for bad in (
        "",
        "/tmp/a\nb",
        "/tmp/a\tb",
        "/tmp/a\x00b",
        "/tmp/\x7f",
        "/tmp/\x85",  # a control character, in the ASCII range and above it
        "/tmp/\udcff",
        "/tmp/\ud800x",  # the lone surrogates of a file name that is not UTF-8
        "x" * 4097,
        "é" * 2048 + "a",  # 2049 characters, 4097 bytes: the limit is in bytes
    ):
        assert not is_reportable_path(bad), repr(bad[:20])


@pytest.mark.parametrize("value", [None, b"/tmp/a", 3, ["/tmp/a"], Path("/tmp/a")])
def test_only_a_plain_string_can_be_a_reportable_path(value):
    assert not is_reportable_path(value)


def test_a_string_subclass_cannot_stand_in_for_a_reportable_path():
    class Spelled(str):
        pass

    assert not is_reportable_path(Spelled("/tmp/a"))
