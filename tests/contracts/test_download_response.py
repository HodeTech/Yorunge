"""The signed GET's answer: typed, and what the closed response table does with it.

Independent vectors: one case per row of the table, and the ways each field of an answer can lie.
No network; the transport's job is only to hand over a status and the raw header fields.
"""

import pytest

from yorunge.domain.download import MAX_DOWNLOAD_BYTES
from yorunge.domain.download_response import (
    ContentRange,
    DownloadResponse,
    ResumeAsk,
    body_failure,
    check_body_end,
    check_written,
    disposition,
    parse_content_range,
    parse_etag,
    parse_response,
    request_headers,
)
from yorunge.domain.errors import YorungeError

TAG = '"v1-3f9c"'


def code_of(action):
    with pytest.raises(YorungeError) as error:
        action()
    return error.value.code


def headers(**fields):
    return [(name.replace("_", "-"), value) for name, value in fields.items()]


# --- Content-Range --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        ("bytes 0-9/10", (0, 9, 10)),
        ("bytes 400-999/1000", (400, 999, 1000)),
        ("bytes 5-5/6", (5, 5, 6)),
        ("Bytes 0-9/10", (0, 9, 10)),  # the range unit is case-insensitive
        ("BYTES 0-9/10", (0, 9, 10)),
        (" bytes 0-9/10 ", (0, 9, 10)),  # the field's own outer whitespace is not part of its value
        ("\tbytes 0-9/10", (0, 9, 10)),
        ("bytes 0-9223372036854775806/9223372036854775807", (0, 2**63 - 2, 2**63 - 1)),
    ],
)
def test_a_content_range_with_a_known_total_is_parsed(value, expected):
    assert parse_content_range(value) == ContentRange(*expected)


@pytest.mark.parametrize(
    "value",
    [
        "bytes 0-9/*",  # the total is unknown: nothing can be verified against it
        "bytes */10",  # the unsatisfied form belongs to a 416
        "bytes 9-0/10",  # starts after it ends
        "bytes 0-10/10",  # ends at the total
        "bytes 0-11/10",
        "bytes 10-10/10",
        "bytes 0-9/0",
        "bytes  0-9/10",  # two spaces
        "bytes 0 -9/10",
        "bytes 0- 9/10",
        "bytes 0-9 /10",
        "bytes 0-9/ 10",
        "bytes=0-9/10",
        "bytes0-9/10",
        "items 0-9/10",
        "",
        "bytes",
        "bytes 0-9",
        "bytes 0-9/10, 20-29/30",  # several ranges
        "bytes 0-9/10;x=1",
        "bytes +0-9/10",
        "bytes -0-9/10",
        "bytes 00-9/10",  # a leading zero
        "bytes 0-09/10",
        "bytes 0x0-9/10",
        "bytes 1e1-9/10",
        "bytes ٠-9/10",  # a non-ASCII digit
        "bytes 0-9/10\n",
        "bytes 0-9/10\r\nX: y",
        "bytes 0-9223372036854775808/9223372036854775809",  # past 64 bits
        "bytes 0-99999999999999999999/100000000000000000000",
        None,
        10,
        b"bytes 0-9/10",
    ],
)
def test_a_content_range_that_is_not_one_exact_known_range_is_not_a_range(value):
    assert parse_content_range(value) is None


# --- the entity tag -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "values,expected",
    [
        ([TAG], TAG),
        ([' "v1-3f9c" '], TAG),
        (['"a"'], '"a"'),
        (['"' + "z" * 126 + '"'], '"' + "z" * 126 + '"'),
        (['W/"v1"'], None),  # weak: never a resumable identity
        (['w/"v1"'], None),
        (['""'], None),  # empty: it identifies nothing
        (["v1"], None),  # not quoted
        (['"v1'], None),
        (['"a"b"'], None),  # a quote inside
        (['"a b"'], None),  # a space is not an entity-tag character
        (['"a\tb"'], None),
        (['"' + "z" * 127 + '"'], None),  # too long
        (['"é"'], None),  # not ASCII
        ([], None),
        ([TAG, TAG], None),  # several fields: ambiguous
        ([TAG + "," + TAG], None),  # a list
        (['"a", "b"'], None),
        (["*"], None),
        ([5], None),
    ],
)
def test_only_a_single_well_formed_strong_tag_is_an_identity(values, expected):
    assert parse_etag(values) == expected


# --- the closed table: which answers are typed, which are refused ---------------------------------


def typed(status, **fields):
    fields.setdefault("Content_Length", "10")
    return parse_response(status, headers(**fields))


def test_a_full_answer_is_typed_with_its_length_and_its_tag():
    found = typed(200, ETag=TAG, Content_Length="1000")
    assert found == DownloadResponse(200, None, TAG, "length", 1000)


def test_a_partial_answer_is_typed_with_its_range():
    found = typed(206, Content_Range="bytes 400-999/1000", Content_Length="600", ETag=TAG)
    assert found == DownloadResponse(206, ContentRange(400, 999, 1000), TAG, "length", 600)


def test_a_chunked_answer_has_no_length():
    found = parse_response(200, [("Transfer-Encoding", "chunked")])
    assert found == DownloadResponse(200, None, None, "chunked", None)
    assert parse_response(200, [("transfer-encoding", " CHUNKED ")]).framing == "chunked"


def test_header_names_are_matched_without_regard_to_case():
    found = parse_response(
        206, [("CONTENT-RANGE", "bytes 0-9/10"), ("content-length", "10"), ("etag", TAG)]
    )
    assert found.content_range == ContentRange(0, 9, 10) and found.etag == TAG


def test_a_sixteen_four_one_six_carries_nothing_the_engine_reads():
    assert parse_response(416, []) == DownloadResponse(416, None, None, None, None)
    assert parse_response(416, [("Content-Range", "bytes */1000")]).status == 416


@pytest.mark.parametrize(
    "status,code",
    [
        (301, "remote_failed"),
        (302, "remote_failed"),
        (303, "remote_failed"),
        (304, "remote_failed"),
        (307, "remote_failed"),
        (308, "remote_failed"),
        (300, "remote_failed"),
        (399, "remote_failed"),
        (401, "remote_access_denied"),
        (403, "remote_access_denied"),
        (429, "remote_rate_limited"),
        (400, "remote_failed"),
        (402, "remote_failed"),
        (404, "remote_failed"),
        (405, "remote_failed"),
        (408, "remote_failed"),
        (409, "remote_failed"),
        (410, "remote_failed"),
        (412, "remote_failed"),
        (422, "remote_failed"),
        (451, "remote_failed"),
        (499, "remote_failed"),
        (500, "remote_failed"),
        (502, "remote_failed"),
        (503, "remote_failed"),
        (504, "remote_failed"),
        (599, "remote_failed"),
        (201, "invalid_response"),
        (202, "invalid_response"),
        (203, "invalid_response"),
        (204, "invalid_response"),
        (205, "invalid_response"),
        (207, "invalid_response"),
        (226, "invalid_response"),
        (299, "invalid_response"),
        (100, "invalid_response"),
        (101, "invalid_response"),
        (199, "invalid_response"),
        (99, "invalid_response"),
        (0, "invalid_response"),
        (600, "invalid_response"),
        (-1, "invalid_response"),
        (True, "invalid_response"),
        ("200", "invalid_response"),
        (200.0, "invalid_response"),
        (None, "invalid_response"),
    ],
)
def test_every_status_outside_200_206_416_falls_on_its_row_and_its_one_code(status, code):
    assert code_of(lambda: parse_response(status, [("Content-Length", "10")])) == code


@pytest.mark.parametrize(
    "encoding",
    ["gzip", "br", "deflate", "zstd", "compress", "identity, gzip", "gzip, identity", "x"],
)
@pytest.mark.parametrize("status", [200, 206])
def test_a_content_encoding_other_than_identity_is_refused_before_the_body_is_read(
    status, encoding
):
    fields = [("Content-Encoding", encoding), ("Content-Length", "10")]
    assert code_of(lambda: parse_response(status, fields)) == "invalid_response"


@pytest.mark.parametrize("encoding", ["identity", "IDENTITY", " identity ", ""])
def test_an_identity_encoding_is_no_encoding(encoding):
    fields = [("Content-Encoding", encoding), ("Content-Length", "10")]
    assert parse_response(200, fields).status == 200


UNFRAMED = [
    [],  # a body closed by the connection
    [("Content-Length", "")],
    [("Content-Length", "abc")],
    [("Content-Length", "-1")],
    [("Content-Length", "+10")],
    [("Content-Length", "10.0")],
    [("Content-Length", "010")],
    [("Content-Length", "1 0")],
    [("Content-Length", "1" + "0" * 64)],  # not a length: 65 digits
    [("Content-Length", "10"), ("Content-Length", "10")],  # a repeated field is not accepted
    [("Content-Length", "10, 10")],
    [("Transfer-Encoding", "gzip")],
    [("Transfer-Encoding", "gzip, chunked")],
    [("Transfer-Encoding", "chunked, chunked")],
    [("Transfer-Encoding", "chunked"), ("Transfer-Encoding", "chunked")],
    [("Transfer-Encoding", "chunked"), ("Content-Length", "10")],  # smuggling-shaped
    [("Transfer-Encoding", "identity")],
    [("Transfer-Encoding", "")],
]


@pytest.mark.parametrize("fields", UNFRAMED)
def test_a_full_body_without_exactly_one_framing_is_invalid(fields):
    assert code_of(lambda: parse_response(200, fields)) == "invalid_response"


@pytest.mark.parametrize("fields", UNFRAMED)
def test_a_partial_body_that_cannot_be_framed_is_not_a_continuation_and_the_stage_is_dropped(
    fields,
):
    # "206 ... Content-Length uyumsuz veya eksik": like any other unusable partial answer, it
    # calls for the stage to go and one Range-less request, not for a stop that repeats forever.
    found = parse_response(206, fields)
    assert (found.status, found.framing, found.content_length) == (206, None, None)
    ask = ResumeAsk(400, 1000, '"v1"')
    assert disposition(found, ask) == "discard_and_retry"
    assert code_of(lambda: disposition(found, None)) == "invalid_response"  # nobody asked for it


def test_a_length_past_the_limit_is_refused_before_a_byte_is_written():
    assert typed(200, Content_Length=str(MAX_DOWNLOAD_BYTES)).content_length == MAX_DOWNLOAD_BYTES
    for length in (MAX_DOWNLOAD_BYTES + 1, 2**63, 10**30, 10**63):
        assert (
            code_of(lambda length=length: typed(200, Content_Length=str(length)))
            == "download_limit_exceeded"
        )
    assert (
        code_of(lambda: typed(206, Content_Length=str(MAX_DOWNLOAD_BYTES + 1)))
        == "download_limit_exceeded"
    )


def test_unusable_range_or_tag_fields_are_not_errors_they_are_absent():
    found = typed(206, Content_Range="bytes 0-9/*", ETag='W/"x"')
    assert found.content_range is None and found.etag is None
    twice = parse_response(
        206,
        [
            ("Content-Range", "bytes 0-9/10"),
            ("Content-Range", "bytes 0-9/10"),
            ("Content-Length", "10"),
        ],
    )
    assert twice.content_range is None  # two fields are ambiguous
    plain = typed(200, Content_Range="bytes 0-9/10")
    assert plain.content_range is None  # a full answer has no range


# --- the request ----------------------------------------------------------------------------------


def test_the_conditional_request_names_the_prefix_and_the_strong_tag_and_nothing_else():
    ask = ResumeAsk(400, 1000, TAG)
    assert request_headers(ask) == (("Range", "bytes=400-"), ("If-Range", TAG))
    assert request_headers(None) == ()


@pytest.mark.parametrize(
    "prefix,total,etag",
    [
        (0, 1000, TAG),  # nothing to resume from
        (1000, 1000, TAG),  # nothing left to ask for
        (1001, 1000, TAG),
        (-1, 1000, TAG),
        (400, MAX_DOWNLOAD_BYTES + 1, TAG),
        (400, 1000, 'W/"x"'),
        (400, 1000, ""),
        (400, 1000, "x"),
        (True, 1000, TAG),
        (400, 1000.0, TAG),
        (400, 1000, None),
    ],
)
def test_a_resume_is_only_asked_for_a_real_prefix_of_a_known_total_with_a_strong_tag(
    prefix, total, etag
):
    with pytest.raises(ValueError):
        ResumeAsk(prefix, total, etag)


# --- what an answer calls for ---------------------------------------------------------------------

ASK = ResumeAsk(400, 1000, TAG)


def exact_partial(**changes):
    value = {
        "content_range": ContentRange(400, 999, 1000),
        "etag": TAG,
        "framing": "length",
        "content_length": 600,
        **changes,
    }
    return DownloadResponse(206, **value)


def test_a_plain_request_is_answered_by_a_full_body_or_by_nothing_in_the_protocol():
    assert disposition(DownloadResponse(200, None, None, "length", 10), None) == "full"
    assert disposition(DownloadResponse(200, None, TAG, "chunked", None), None) == "full"
    assert code_of(lambda: disposition(exact_partial(), None)) == "invalid_response"
    assert (
        code_of(lambda: disposition(DownloadResponse(416, None, None, None, None), None))
        == "invalid_response"
    )


def test_a_range_the_provider_ignored_restarts_from_the_start_of_this_answer():
    assert disposition(DownloadResponse(200, None, TAG, "length", 1000), ASK) == "restart"
    assert disposition(DownloadResponse(200, None, None, "chunked", None), ASK) == "restart"


def test_an_exact_continuation_continues():
    assert disposition(exact_partial(), ASK) == "continue"


@pytest.mark.parametrize(
    "changes",
    [
        {"content_range": ContentRange(399, 999, 1000)},  # another start
        {"content_range": ContentRange(401, 999, 1000)},
        {"content_range": ContentRange(400, 998, 1000)},  # another end
        {"content_range": ContentRange(400, 1000, 1001)},
        {"content_range": ContentRange(400, 999, 999)},  # another total
        {"content_range": ContentRange(400, 999, 1001)},
        {"content_range": None},  # absent or unusable
        {"etag": None},
        {"etag": '"other"'},
        {"etag": '"V1-3F9C"'},  # a tag is compared exactly
        {"framing": "chunked", "content_length": None},
        {"content_length": 599},
        {"content_length": 601},
        {"content_length": 1000},
    ],
)
def test_a_partial_answer_that_does_not_fit_exactly_discards_and_asks_once_without_a_range(changes):
    assert disposition(exact_partial(**changes), ASK) == "discard_and_retry"


def test_an_unsatisfiable_range_discards_and_asks_once_without_a_range():
    assert disposition(DownloadResponse(416, None, None, None, None), ASK) == "discard_and_retry"


# --- the body -------------------------------------------------------------------------------------


def test_the_running_counter_stops_at_the_limit_and_not_before():
    check_written(0)
    check_written(MAX_DOWNLOAD_BYTES)
    assert code_of(lambda: check_written(MAX_DOWNLOAD_BYTES + 1)) == "download_limit_exceeded"
    for bad in (-1, True, 1.5, None):
        with pytest.raises(ValueError):
            check_written(bad)


@pytest.mark.parametrize(
    "framing,length,written,terminated,code",
    [
        ("length", 10, 10, False, None),
        ("length", 10, 10, True, None),
        ("length", 0, 0, False, None),
        ("length", 10, 9, False, "download_incomplete"),
        ("length", 10, 0, False, "download_incomplete"),
        ("length", 10, 11, False, "invalid_response"),  # more than the answer promised
        ("length", None, 5, False, "invalid_response"),
        ("chunked", None, 5, True, None),
        ("chunked", None, 0, True, None),
        ("chunked", None, 5, False, "download_incomplete"),  # the terminating chunk never came
        ("chunked", None, MAX_DOWNLOAD_BYTES + 1, True, "download_limit_exceeded"),
        ("length", MAX_DOWNLOAD_BYTES, MAX_DOWNLOAD_BYTES + 1, False, "download_limit_exceeded"),
    ],
)
def test_a_body_that_ends_is_the_whole_of_what_its_framing_promised_or_incomplete(
    framing, length, written, terminated, code
):
    if code is None:
        check_body_end(framing, length, written, terminated=terminated)
    else:
        assert (
            code_of(lambda: check_body_end(framing, length, written, terminated=terminated)) == code
        )


@pytest.mark.parametrize(
    "code,expected",
    [
        ("transport_failed", "download_incomplete"),
        ("stream_interrupted", "download_incomplete"),
        ("invalid_response", "download_limit_exceeded"),  # the common transport's size cap
        ("transport_timeout", "transport_timeout"),  # a timeout keeps its priority
        ("request_cancelled", "request_cancelled"),
        ("execution_timeout", "execution_timeout"),
        ("download_write_failed", "download_write_failed"),
        ("remote_failed", "remote_failed"),
    ],
)
def test_a_failure_in_the_body_phase_is_a_cut_a_cap_or_keeps_its_own_code(code, expected):
    assert body_failure(code) == expected
