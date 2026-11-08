"""What round two of P02-3n pinned about the signed address of a model's weights.

A segment that a server may read as a dot segment is not an object, however it is spelled
(percent-encoded dots, a path parameter, an encoded semicolon); legitimate names that merely look
like one stay; and the pattern of a signed address accepts the plain host and query characters it
names, whatever the registered host looks like.
"""

import pytest

from tests.contracts.test_model_download_codec import (
    ORIGIN,
    PREFIX,
    QUERY,
    answer,
    code_of,
    parse,
)


@pytest.mark.parametrize(
    "tail",
    [
        "%2e%2e;x/b.onnx",
        "%2E%2E;x",
        ".%2e;x",
        "%2e;x",
        "a/%2e%2e;x/b.onnx",
        "..%3Bx/b.onnx",  # the semicolon encoded: decoded first, then the parameter is cut
        "%2e%2e%3Bx",
        "..;x/b.onnx",
        ".;x/b.onnx",
        "a/..;x/b.onnx",
        "%2e.;x/w.onnx",
        "%252e%252e;x/w.onnx",  # one more layer of encoding
        "w.onnx/%2e%2e;/x",
        ";x",  # reads as the prefix itself
        ";",
        "a/b.onnx/;x",  # reads as a directory
        "a/;x/b.onnx",  # an empty segment between two names
    ],
)
def test_a_dot_segment_is_not_an_object_whatever_its_spelling(tail):
    assert code_of(lambda: parse(answer(url=ORIGIN + PREFIX + tail + QUERY))) == "invalid_response"


@pytest.mark.parametrize(
    "tail",
    [
        "w;v=1.onnx",
        "..foo",
        ".hidden",
        "w.",
        "%C3%A9vren.onnx",
        "a;b/c.onnx",
        "a%2eb.onnx",  # a dot inside a name is a name
        "...",  # three dots are a plain name, not a dot segment
    ],
)
def test_names_that_only_look_like_a_dot_segment_stay_objects(tail):
    assert parse(answer(url=ORIGIN + PREFIX + tail + QUERY)).wire_url.endswith(tail + QUERY)


@pytest.mark.parametrize(
    "host",
    [
        "models-1.example.org",
        "a1.b2.c3.example",
        "x-y.example",
        "1.example",
        "api-2.ssyz.org.tr",
        "xn--vren-pta.ssyz.org.tr",
        "203.0.113.7",
    ],
)
def test_the_host_class_takes_hyphens_and_digits(host):
    origin = f"https://{host}"
    url = origin + PREFIX + "w.onnx" + QUERY
    assert parse(answer(url=url), origin=origin).wire_url == url


@pytest.mark.parametrize(
    "query",
    ["?sig=a+b", "?sig=a%2Bb", "?sig=a~b.c_d-e", "?a=1&a=2;b=3", "?sig=Zm9v/Yg==", "?x=!$'()*,:@"],
)
def test_a_signed_query_may_use_every_plain_character_of_rfc3986(query):
    url = ORIGIN + PREFIX + "w.onnx" + query
    assert parse(answer(url=url)).wire_url == url


def test_a_plus_sign_in_the_path_is_part_of_what_was_signed():
    url = ORIGIN + PREFIX + "w+1.onnx" + QUERY
    assert parse(answer(url=url)).wire_url == url


@pytest.mark.parametrize(
    "url",
    [
        ORIGIN
        + PREFIX
        + "w.onnx?a=[b",  # one bracket alone: DownloadTarget takes it, only the pattern
        ORIGIN + PREFIX + "w.onnx?a=b]",  # refuses it
        ORIGIN + PREFIX + "w[.onnx",
        ORIGIN + PREFIX + "w].onnx",
    ],
)
def test_each_bracket_alone_is_refused(url):
    assert code_of(lambda: parse(answer(url=url))) == "invalid_response"


@pytest.mark.parametrize("path", [PREFIX, PREFIX + "?x=1", PREFIX + "dir/", PREFIX + "dir/?x=1"])
def test_the_prefix_and_a_directory_below_it_are_not_objects(path):
    assert code_of(lambda: parse(answer(url=ORIGIN + path))) == "invalid_response"
