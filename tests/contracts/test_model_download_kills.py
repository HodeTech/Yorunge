"""Mutants of the codec and the argument helpers that no test of the first suite killed (P02-3n R1).

Each test names the mutant it kills in its own words: a key hidden by percent-encoding, the
boundaries of a plain name, the literal limits, the base that keeps its own last character, the
8-byte rule of the key scan, a control character in an address and a lost working directory.
"""

import json

import pytest

from tests.contracts.test_model_download_codec import (
    ORIGIN,
    PREFIX,
    QUERY,
    SECRET,
    SIGNED,
    answer,
    code_of,
    parse,
)
from yorunge.application.model_download import weights_prefix
from yorunge.domain.errors import YorungeError


def pct(text):
    return "".join(f"%{ord(char):02X}" for char in text)


@pytest.mark.parametrize(
    "url",
    [
        ORIGIN + PREFIX + pct(SECRET) + ".onnx" + QUERY,  # whole key, encoded, in the path
        ORIGIN + PREFIX + "w.onnx?k=" + pct(SECRET),  # in a query value
        ORIGIN + PREFIX + "w.onnx?" + pct(SECRET) + "=1",  # in a query name
        ORIGIN + PREFIX + "x" + pct(SECRET[:9]) + SECRET[9:] + ".onnx",  # half and half
    ],
)
def test_a_percent_encoded_key_in_the_address_is_invalid(url):
    assert code_of(lambda: parse(answer(url=url))) == "invalid_response"


@pytest.mark.parametrize(
    "name", ["my model v2.onnx", "a b", " ", "~", "a b", "ağırlık.onnx", " ", "a" * 255]
)
def test_ordinary_names_are_plain(name):
    assert parse(answer(filename=name)).wire_url == SIGNED


@pytest.mark.parametrize("name", ["a\x1fb", "\x00", "a\x9fb", "a\x80b", "a" * 256, "ğ" * 128])
def test_control_characters_and_too_long_names_are_not(name):
    assert code_of(lambda: parse(answer(filename=name))) == "invalid_response"


def test_the_name_limit_is_255_bytes_by_the_literal():
    assert parse(answer(filename="x" * 255)).wire_url == SIGNED
    assert code_of(lambda: parse(answer(filename="x" * 256))) == "invalid_response"


@pytest.mark.parametrize("base", ["/api/vZ", "/api/vZ/", "/Z", "/aZ/"])
def test_the_prefix_keeps_the_characters_of_the_base(base):
    assert weights_prefix(base) == base.rstrip("/") + "/files/evren-models/"


def test_a_short_key_matches_only_whole_a_key_of_eight_bytes_matches_inside():
    from yorunge.application.response_json import scan_for_secret
    from yorunge.domain.credentials import SecretValue

    # 7 bytes: found as a whole value only, never inside another one
    scan_for_secret({"a": "x1234567y", "b": ["1234567x"]}, SecretValue("1234567"))
    with pytest.raises(YorungeError) as error:
        scan_for_secret({"a": "x12345678y"}, SecretValue("12345678"))  # 8 bytes: found inside
    assert error.value.code == "invalid_response"
    with pytest.raises(YorungeError):
        scan_for_secret({"a": "1234567"}, SecretValue("1234567"))  # whole is always found


@pytest.mark.parametrize(
    "url",
    [
        ORIGIN + PREFIX + "a\x7fb.onnx" + QUERY,
        ORIGIN + PREFIX + "w.onnx?a=\x7f",
        ORIGIN + PREFIX + "w.onnx?a=\x1f",
        ORIGIN + PREFIX + "w.onnx?a=\x00",
    ],
)
def test_a_control_character_in_the_address_is_invalid(url):
    assert code_of(lambda: parse(answer(url=url))) == "invalid_response"


def test_a_key_inside_an_object_key_name_is_invalid():
    data = json.dumps({"download_url": SIGNED, "filename": "a", "x" + SECRET + "y": 1}).encode()
    assert code_of(lambda: parse(data)) == "invalid_response"


@pytest.mark.parametrize(
    "url",
    [
        ORIGIN + PREFIX + "ağırlık.onnx" + QUERY,
        ORIGIN + PREFIX + "w.onnx?a=é",
        ORIGIN + PREFIX + "w.onnx?a= ",
        "https://api.ssyz.org.tr／" + PREFIX.lstrip("/") + "w.onnx",  # a full-width solidus
        ORIGIN + PREFIX + "w․onnx",
    ],
)
def test_a_non_ascii_address_is_invalid(url):
    assert code_of(lambda: parse(answer(url=url))) == "invalid_response"


def test_a_relative_path_with_a_lost_working_directory_is_input_invalid(monkeypatch):
    from pathlib import Path

    from yorunge.adapters.command_arguments import absolute

    def lost(cls):
        raise OSError("cwd is gone")

    monkeypatch.setattr(Path, "cwd", classmethod(lost))
    assert code_of(lambda: absolute(Path("w.onnx"))) == "input_invalid"
    assert absolute(Path("/abs/w.onnx")) == Path("/abs/w.onnx")  # an absolute path never asks


def test_a_key_in_a_later_list_element_is_invalid():
    data = json.dumps({"download_url": SIGNED, "filename": "a", "e": ["x", ["y", SECRET]]}).encode()
    assert code_of(lambda: parse(data)) == "invalid_response"
