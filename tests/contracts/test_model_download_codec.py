"""The one JSON call of ``models download`` and what its answer may be (ADR-0032 §1).

The call asks for an exact model version in an explicit format (and a fold only if the user gave
one). The answer names a signed address; the address is trusted for nothing but being downloaded
from, so it must sit below the registered Platform origin and below exactly
``{api_base_path}/files/evren-models/`` (the answer cannot widen the prefix, and the dataset
bucket's ``{api_base_path}/files/`` is not it). The provider's file name is checked and forgotten.
"""

import json

import pytest

from yorunge.application.download_transport import DownloadTarget
from yorunge.application.model_download import (
    FORMATS,
    MAX_FILENAME_BYTES,
    parse_weights_answer,
    weights_endpoint,
    weights_prefix,
    weights_query,
)
from yorunge.domain.credentials import SecretValue
from yorunge.domain.errors import YorungeError

SECRET = "synthetic-codec-key-7731"
KEY = SecretValue(SECRET)
ORIGIN, BASE = "https://api.ssyz.org.tr", "/api/v1"
PREFIX = BASE + "/files/evren-models/"
QUERY = "?X-Amz-Credential=scope%2Fpart&signature=Zm9v%2BYg%3D&x=1&x=2"
SIGNED = ORIGIN + PREFIX + "weights.onnx" + QUERY
VERSION = "00000000-0000-4000-8000-000000000123"


def answer(url=SIGNED, filename="provider-name.onnx", **extra):
    return json.dumps({"download_url": url, "filename": filename, **extra}).encode()


def code_of(action):
    with pytest.raises(YorungeError) as error:
        action()
    return error.value.code


def parse(data, **changes):
    values = {"secret": KEY, "origin": ORIGIN, "api_base_path": BASE, **changes}
    return parse_weights_answer(data, **values)


# --- what is asked -----------------------------------------------------------------------------


def test_the_route_is_the_versions_download_below_the_api_base():
    assert weights_endpoint(VERSION) == f"models/versions/{VERSION}/download"


@pytest.mark.parametrize("artifact_format", FORMATS)
def test_the_format_is_always_asked_for_and_a_fold_only_if_it_was_given(artifact_format):
    assert weights_query(artifact_format, None) == (("format", artifact_format),)
    assert weights_query(artifact_format, 0) == (("format", artifact_format), ("fold", "0"))
    assert weights_query(artifact_format, 1024) == (("format", artifact_format), ("fold", "1024"))


@pytest.mark.parametrize("artifact_format", ["gguf", "ONNX", "", None, 1, "onnx "])
def test_a_format_that_is_not_one_of_the_three_is_refused(artifact_format):
    assert code_of(lambda: weights_query(artifact_format, None)) == "invalid_request"


@pytest.mark.parametrize("fold", [-1, 1025, True, False, "03", " 3", "+3", "3.0", 1.0, 2**64])
def test_a_fold_that_is_not_an_exact_integer_in_range_is_refused(fold):
    assert code_of(lambda: weights_query("onnx", fold)) == "invalid_request"


@pytest.mark.parametrize(
    "base,prefix",
    [
        ("/api/v1", PREFIX),
        ("/api/v1/", PREFIX),
        ("/", "/files/evren-models/"),
        ("/a/b/c", "/a/b/c/files/evren-models/"),
    ],
)
def test_the_prefix_is_the_model_bucket_below_the_api_base(base, prefix):
    assert weights_prefix(base) == prefix


@pytest.mark.parametrize("base", ["api/v1", "//x", "/a//b", "", None, 5])
def test_a_base_that_is_not_a_canonical_path_has_no_prefix(base):
    assert code_of(lambda: weights_prefix(base)) == "invalid_service_target"


# --- what the answer may be --------------------------------------------------------------------


def test_a_good_answer_is_the_signed_address_with_its_query_untouched():
    target = parse(answer())
    assert type(target) is DownloadTarget
    assert target.wire_url == SIGNED  # the signature's bytes are never re-encoded
    assert (target.origin, target.prefix) == (ORIGIN, PREFIX)


def test_fields_the_codec_does_not_know_are_dropped_not_reflected():
    target = parse(answer(extra={"nested": [1, 2, {"a": "b"}]}, size=123))
    assert target.wire_url == SIGNED


def test_a_provider_name_is_validated_and_then_forgotten():
    # nothing of ``filename`` is in what comes back: only the address is
    target = parse(answer(filename="évren-ağırlık.onnx"))
    assert "ağırlık" not in target.wire_url and "provider" not in repr(target)


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"null",
        b"[]",
        b'"text"',
        b"{}",
        b"{not json",
        b'{"download_url":"x","download_url":"y","filename":"a"}',  # a duplicate key
        b'{"download_url":NaN,"filename":"a"}',
        json.dumps({"download_url": SIGNED}).encode(),
        json.dumps({"filename": "a.onnx"}).encode(),
        json.dumps({"download_url": None, "filename": "a.onnx"}).encode(),
        json.dumps({"download_url": 5, "filename": "a.onnx"}).encode(),
        json.dumps({"download_url": [SIGNED], "filename": "a.onnx"}).encode(),
        json.dumps({"download_url": {"u": SIGNED}, "filename": "a.onnx"}).encode(),
        json.dumps({"download_url": SIGNED, "filename": None}).encode(),
        json.dumps({"download_url": SIGNED, "filename": 5}).encode(),
        json.dumps({"download_url": SIGNED, "filename": ["a.onnx"]}).encode(),
    ],
)
def test_an_answer_that_is_not_the_two_strings_is_invalid_not_guessed_at(data):
    assert code_of(lambda: parse(data)) == "invalid_response"


@pytest.mark.parametrize(
    "name",
    [
        "",
        ".",
        "..",
        "a/b.onnx",
        "../b.onnx",
        "a\\b.onnx",
        "a\x00b",
        "a\nb",
        "a\tb",
        "a\x7fb",
        "a\x85b",
        "x" * (MAX_FILENAME_BYTES + 1),
        "ğ" * 128,  # 256 bytes
    ],
)
def test_a_provider_name_that_is_not_a_plain_name_is_invalid_though_it_is_never_used(name):
    assert code_of(lambda: parse(answer(filename=name))) == "invalid_response"


def test_a_name_of_the_longest_plain_size_is_fine():
    assert parse(answer(filename="x" * MAX_FILENAME_BYTES)).wire_url == SIGNED
    assert parse(answer(filename="ğ" * 127)).wire_url == SIGNED  # 254 bytes


@pytest.mark.parametrize(
    "url",
    [
        "http://api.ssyz.org.tr" + PREFIX + "w.onnx" + QUERY,  # not https
        "https://other.ssyz.org.tr" + PREFIX + "w.onnx" + QUERY,  # another origin
        "https://api.ssyz.org.tr:8443" + PREFIX + "w.onnx" + QUERY,  # another port
        "https://user:pass@api.ssyz.org.tr" + PREFIX + "w.onnx" + QUERY,  # userinfo
        ORIGIN + PREFIX + "w.onnx" + QUERY + "#fragment",  # a fragment
        ORIGIN + PREFIX + "../w.onnx" + QUERY,  # a dot segment
        ORIGIN + PREFIX + "%2e%2e/w.onnx" + QUERY,  # an encoded one
        ORIGIN + PREFIX + "a%2Fb.onnx" + QUERY,  # an encoded separator in the path
        ORIGIN + BASE + "/files/w.onnx" + QUERY,  # the DATASET bucket, not the model bucket
        ORIGIN + BASE + "/files/other-bucket/w.onnx" + QUERY,  # another bucket
        ORIGIN + "/files/evren-models/w.onnx" + QUERY,  # the right bucket, not below the API base
        ORIGIN + BASE + "/files/evren-modelsX/w.onnx" + QUERY,  # a longer first segment
        ORIGIN + BASE + "/files/evren-models" + QUERY,  # no slash after the bucket
        ORIGIN + BASE + "/other/files/evren-models/w.onnx" + QUERY,  # the prefix, not at the start
        "ftp://api.ssyz.org.tr" + PREFIX + "w.onnx",
        "//api.ssyz.org.tr" + PREFIX + "w.onnx",
        PREFIX + "w.onnx" + QUERY,  # relative
        "",
        " " + SIGNED,
        SIGNED + " ",
        SIGNED.replace("weights", "we ights"),
        ORIGIN + PREFIX + "w.onnx?" + "a" * (16 * 1024),  # an address over 16 KiB
    ],
)
def test_an_address_that_is_not_below_the_model_prefix_of_the_platform_is_invalid(url):
    assert code_of(lambda: parse(answer(url=url))) == "invalid_response"


@pytest.mark.parametrize(
    "url",
    [
        # bytes the HTTP client rewrites on its way to the wire: the address would not be the one
        # that was signed (a quote, angle brackets, a brace or a backtick, a mixed-case scheme)
        ORIGIN + PREFIX + 'w".onnx' + QUERY,
        ORIGIN + PREFIX + "w<.onnx" + QUERY,
        ORIGIN + PREFIX + "w>.onnx" + QUERY,
        ORIGIN + PREFIX + "w`.onnx" + QUERY,
        ORIGIN + PREFIX + "w{.onnx" + QUERY,
        ORIGIN + PREFIX + "w}.onnx" + QUERY,
        ORIGIN + PREFIX + "w.onnx?a=" + '"b"',
        ORIGIN + PREFIX + "w.onnx?a=<b>",
        ORIGIN + PREFIX + "w.onnx?a=b|c",
        ORIGIN + PREFIX + "w.onnx?a=b^c",
        ORIGIN + PREFIX + "w.onnx?a=[b]",
        ORIGIN + PREFIX + "w.onnx?a=b\\c",
        "HTTPS://api.ssyz.org.tr" + PREFIX + "w.onnx" + QUERY,
        "Https://api.ssyz.org.tr" + PREFIX + "w.onnx" + QUERY,
        "https://[::1]" + PREFIX + "w.onnx" + QUERY,
        "https://api.ssyz.org.tr:443" + PREFIX + "w.onnx" + QUERY,  # the origin is not spelled so
        "https://api.ssyz.org.tr\uff0f" + PREFIX + "w.onnx",  # a fullwidth solidus in the host
    ],
)
def test_an_address_the_client_would_rewrite_is_invalid_not_a_target_the_user_must_fix(url):
    assert code_of(lambda: parse(answer(url=url))) == "invalid_response"


@pytest.mark.parametrize(
    "url",
    [
        ORIGIN + PREFIX,  # the prefix itself names no object
        ORIGIN + PREFIX + QUERY,
        ORIGIN + PREFIX + "?sig=abc",
        ORIGIN + PREFIX + "sub/",  # a directory
        ORIGIN + PREFIX + "sub/" + QUERY,
        ORIGIN + PREFIX + "..;/b.onnx" + QUERY,  # a dot segment to a servlet container
        ORIGIN + PREFIX + "a/..;x/b.onnx" + QUERY,
        ORIGIN + PREFIX + ".;/b.onnx" + QUERY,
        ORIGIN + PREFIX + "a/.;p=1/b.onnx" + QUERY,
    ],
)
def test_an_address_that_names_no_single_object_is_invalid(url):
    assert code_of(lambda: parse(answer(url=url))) == "invalid_response"


@pytest.mark.parametrize(
    "url",
    [
        SIGNED,
        ORIGIN + PREFIX + "a/b/c.onnx" + QUERY,
        ORIGIN + PREFIX + "w.onnx",  # no query at all
        ORIGIN + PREFIX + "w.onnx?",  # an empty one
        ORIGIN + PREFIX + "w;v=1.onnx" + QUERY,  # a semicolon that is not a dot segment
        ORIGIN + PREFIX + "w~(1)'!*$,=:@.onnx" + QUERY,  # every sub-delimiter RFC 3986 allows
        ORIGIN + PREFIX + "%C3%A9vren.onnx" + QUERY,  # percent-encoded UTF-8
        ORIGIN + PREFIX + "w.onnx?x=a/b?c:d@e;f,g'h(i)j*k!l$m~n.o_p-q%2Br",
    ],
)
def test_an_address_made_of_what_a_signature_is_made_of_stays_exactly_as_it_was_signed(url):
    assert parse(answer(url=url)).wire_url == url


def test_a_key_in_the_address_in_any_encoding_the_wire_would_carry_is_refused():
    encoded = SECRET.replace("-", "%2D")  # the same bytes once the wire's percent-escapes are read
    for url in (
        ORIGIN + PREFIX + "w.onnx?k=" + encoded,
        ORIGIN + PREFIX + encoded + ".onnx?x=1",
    ):
        assert code_of(lambda url=url: parse(answer(url=url))) == "invalid_response"


@pytest.mark.parametrize(
    "data",
    [
        answer(url=SIGNED + "&key=" + SECRET),  # the key in the address
        answer(url=ORIGIN + PREFIX + SECRET + ".onnx" + QUERY),
        answer(filename=SECRET),
        answer(filename="x" + SECRET + "y"),
        answer(echo=SECRET),  # in a field nothing reads
        answer(nested={"deep": [SECRET]}),
        json.dumps({"download_url": SIGNED, "filename": "a", SECRET: 1}).encode(),  # as a key
    ],
)
def test_an_answer_that_echoes_the_key_anywhere_is_invalid_even_where_it_would_be_dropped(data):
    assert code_of(lambda: parse(data)) == "invalid_response"


@pytest.mark.parametrize("base,origin", [("/", ORIGIN), ("/api/v1", ORIGIN), ("/x/y", ORIGIN)])
def test_the_prefix_follows_the_registered_target_not_the_answer(base, origin):
    url = origin + weights_prefix(base) + "w.onnx" + QUERY
    assert parse(answer(url=url), api_base_path=base, origin=origin).wire_url == url
    # ... and the same address is not below a different registered base
    other = "/other" if base != "/other" else "/another"
    assert code_of(lambda: parse(answer(url=url), api_base_path=other)) == "invalid_response"


def test_a_secret_of_the_wrong_type_is_a_programming_error_not_a_pass():
    assert code_of(lambda: parse(answer(), secret=SECRET)) == "invalid_request"
