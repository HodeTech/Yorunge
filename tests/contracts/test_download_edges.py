"""The edges of the download contract that the row tests do not reach, found by mutating it.

Each case pins a value or a refusal that a one-line change to the contract would otherwise leave
unnoticed: a time budget, a size at its limit, an alphabet's last character, a persisted key, the
text of a message. They were found by hostile review of the contract (mutants that survived the
first tests) and by fuzzing; the defects that review found are listed last, as regressions.
"""

import hashlib

import pytest

from tests.contracts.test_download_contract import HELLO, code_of, partial, summary
from tests.contracts.test_download_state import (
    decide,
    entry,
    record,
    sidecar,
    stage,
)
from yorunge.domain import download as download_module
from yorunge.domain.download import (
    EMPTY_SHA256,
    MAX_DOWNLOAD_BYTES,
    DownloadPartial,
    identity_key,
    parse_fold,
    parse_timeout,
    target_hash,
    validate_target_name,
    verify_expectation,
)
from yorunge.domain.download_response import (
    ResumeAsk,
    check_body_end,
    parse_content_range,
    parse_etag,
    parse_response,
)
from yorunge.domain.download_state import confirm_prefix
from yorunge.domain.errors import MESSAGES, DownloadIntegrityMismatch

TAG = '"v1-3f9c"'


# --- values that are pinned ----------------------------------------------------------------------


def test_the_phase_and_pool_budgets_are_pinned():
    assert (download_module.PHASE_SECONDS, download_module.POOL_SECONDS) == (5, 1)


@pytest.mark.parametrize("parse", [parse_fold, parse_timeout])
def test_an_absurdly_long_digit_string_is_a_closed_refusal_not_a_conversion_error(parse):
    assert code_of(lambda: parse("9" * 5000)) == "invalid_request"


def test_the_level_logic_accepts_the_size_edges():
    assert verify_expectation(EMPTY_SHA256, 0, None).level == "transfer_complete"
    assert verify_expectation(HELLO, MAX_DOWNLOAD_BYTES, None).level == "transfer_complete"


def test_a_full_stage_summary_resumes_from_all_of_its_bytes():
    found = summary(bytes=10, resumed=True, resumed_from_bytes=10)
    assert (found.resumed, found.resumed_from_bytes, found.bytes) == (True, 10, 10)


def test_the_output_path_limit_is_in_bytes_not_characters():
    assert summary(output_path="é" * 2048).output_path == "é" * 2048  # 4096 bytes
    with pytest.raises(ValueError):
        summary(output_path="é" * 2049)  # 2049 characters, 4098 bytes


@pytest.mark.parametrize("artifact_format", ["onnx", "pt", "tflite"])
@pytest.mark.parametrize("fold", [None, 0, 1, 1024])
def test_every_format_and_fold_edge_is_a_valid_source(artifact_format, fold):
    source = {
        "kind": "model_version",
        "version_id": "00000000-0000-4000-8000-000000000123",
        "format": artifact_format,
        "fold": fold,
    }
    assert summary(source=source).source.fold == fold


def test_oversize_input_is_refused_before_it_is_parsed():
    with pytest.raises(ValueError):
        DownloadPartial.decode(b"[" * 5000)  # past the cap: never reaches the JSON parser


def test_a_first_checkpoint_has_equal_creation_and_update_times():
    stamp = "2026-11-08T00:00:00.000000Z"
    assert partial(created_at=stamp, updated_at=stamp).created_at == stamp


def test_the_sidecar_etag_alphabet_ends_at_tilde():
    assert partial(etag='"~!#"').etag == '"~!#"'
    with pytest.raises(ValueError):
        partial(etag='"a\x7fb"')


def test_repeated_etag_fields_in_an_answer_are_ambiguous():
    twice = parse_response(200, [("ETag", TAG), ("ETag", TAG), ("Content-Length", "10")])
    assert twice.etag is None
    mixed = parse_response(200, [("ETag", 'W/"x"'), ("ETag", TAG), ("Content-Length", "10")])
    assert mixed.etag is None


def test_the_response_etag_alphabet_is_exactly_bang_and_hash_through_tilde():
    for good in ('"!"', '"#"', '"~"', '"!#~"', '"\\"'):
        assert parse_etag([good]) == good
    for bad in ('"a\x7fb"', '"a\x1fb"', '"a b"', '"\x80"', '"é"', '"a"b"'):
        assert parse_etag([bad]) is None


def test_a_content_range_total_of_two_to_the_63_is_not_a_range():
    assert parse_content_range("bytes 0-9223372036854775806/9223372036854775807") is not None
    assert parse_content_range("bytes 0-9223372036854775807/9223372036854775808") is None


@pytest.mark.parametrize("unit", ["byteſ", "BYTEſ", "bytesK"])
def test_the_range_unit_is_ascii_case_insensitive_only(unit):
    assert parse_content_range(unit + " 0-9/10") is None


def test_a_resume_may_ask_for_the_last_byte_of_a_whole_gibibyte():
    ask = ResumeAsk(MAX_DOWNLOAD_BYTES - 1, MAX_DOWNLOAD_BYTES, TAG)
    assert ask.total_size == MAX_DOWNLOAD_BYTES


def test_the_mismatch_detail_refuses_a_short_digest_and_accepts_a_whole_gibibyte():
    with pytest.raises(ValueError):
        DownloadIntegrityMismatch(HELLO[:-1], 5)
    assert DownloadIntegrityMismatch(HELLO, 1024**3).details["bytes"] == 1024**3


def test_both_unicode_line_and_paragraph_separators_are_refused_in_a_name():
    for char in ("\u2028", "\u2029", "\u0085", "\u200e"):
        assert code_of(lambda char=char: validate_target_name("a" + char + "b")) == (
            "download_target_invalid"
        )


# --- the state table ------------------------------------------------------------------------------


def test_a_one_byte_stage_without_a_sidecar_is_not_an_empty_stage():
    assert decide(stage=stage(size=1)).action == "unverified"


def test_every_discard_removes_the_leftover_temporary_copy_as_well():
    other = sidecar(rec=record(identity_key="12" * 32))
    found = decide(stage=stage(), sidecar=other, sidecar_tmp=entry(inode=8))
    assert (found.action, found.remove) == ("start_clean", ("stage", "sidecar", "sidecar_tmp"))


def test_no_resume_treats_an_unreadable_sidecar_alike_with_or_without_a_stage():
    with_stage = decide(stage=stage(), sidecar=sidecar(rec=None), no_resume=True)
    without_stage = decide(sidecar=sidecar(rec=None), no_resume=True)
    assert with_stage.action == without_stage.action == "start_clean"


def test_a_prefix_that_did_not_hash_keeps_the_leftover_copy_removal_of_the_first_phase():
    first = decide(stage=stage(), sidecar=sidecar(), sidecar_tmp=entry(inode=8))
    assert first.action == "resume" and first.remove == ("sidecar_tmp",)
    second = confirm_prefix(first, "00" * 32)
    assert second.action == "start_clean"
    assert second.remove == ("stage", "sidecar", "sidecar_tmp")


# --- the persisted identity -----------------------------------------------------------------------

BASE_KEY = {
    "origin": "https://api.ssyz.org.tr",
    "api_base_path": "/api/v1",
    "kind": "model_version",
    "resource_id": "00000000-0000-4000-8000-000000000123",
    "artifact_format": "onnx",
    "fold": None,
}


def test_the_identity_key_is_pinned_because_it_is_persisted_in_every_sidecar():
    # Derived by hand from the documented parts, not through the encoder that makes it.
    text = (
        '{"fold":null,"kind":"download_identity","parts":{"api_base_path":"/api/v1",'
        '"format":"onnx","kind":"model_version","origin":"https://api.ssyz.org.tr",'
        '"resource_id":"00000000-0000-4000-8000-000000000123"}}'
    )
    assert identity_key(**BASE_KEY) == hashlib.sha256(text.encode()).hexdigest()
    with_fold = text.replace('{"fold":null', '{"fold":7')
    assert identity_key(**{**BASE_KEY, "fold": 7}) == hashlib.sha256(with_fold.encode()).hexdigest()


@pytest.mark.parametrize(
    "part", ["origin", "api_base_path", "kind", "resource_id", "artifact_format"]
)
@pytest.mark.parametrize("value", [5, b"x", None, 1.5, ["a"]])
def test_identity_parts_must_be_text(part, value):
    assert code_of(lambda: identity_key(**{**BASE_KEY, part: value})) == "invalid_request"


@pytest.mark.parametrize("fold", ["5", "0", 5.0, -1, True])
def test_the_fold_of_an_identity_is_an_int(fold):
    assert code_of(lambda: identity_key(**{**BASE_KEY, "fold": fold})) == "invalid_request"


def test_an_identity_part_that_does_not_encode_is_refused_and_cannot_collide():
    # Lone surrogates would be written like the character they are the halves of.
    spelled = "\ud83d\ude00"  # two lone surrogates, not the character
    assert code_of(lambda: identity_key(**{**BASE_KEY, "origin": spelled})) == "invalid_request"
    real = identity_key(**{**BASE_KEY, "origin": "\U0001f600"})
    assert real != identity_key(**BASE_KEY)


# --- names ----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case", [str.upper, str.title, str.swapcase], ids=["upper", "title", "swapcase"]
)
def test_the_reserved_prefix_is_reserved_in_any_letter_case(case):
    # On a case-insensitive filesystem a differently cased name is the protocol's own file.
    alias = case(".yorunge-download-" + target_hash("weights.onnx")[:32] + ".part")
    assert code_of(lambda: validate_target_name(alias)) == "download_target_invalid"
    assert code_of(lambda: validate_target_name(case(".yorunge-download-"))) == (
        "download_target_invalid"
    )


# --- what the answer's fields may be --------------------------------------------------------------


@pytest.mark.parametrize(
    "fields",
    [
        [("Content-Length", b"10")],
        [("Content-Encoding", None), ("Content-Length", "10")],
        [("Transfer-Encoding", 5)],
        [(b"Content-Length", "10")],
        [("Content-Length", "10", "x")],
        [["Content-Length", "10"]],
        {"Content-Length": "10"},
        None,
    ],
    ids=["bytes", "none", "int", "bytes name", "triple", "list pair", "mapping", "nothing"],
)
@pytest.mark.parametrize("status", [200, 206, 416, 503])
def test_header_fields_that_are_not_pairs_of_text_are_a_closed_refusal(status, fields):
    assert code_of(lambda: parse_response(status, fields)) == "invalid_response"


def test_a_generator_of_fields_is_not_an_answer():
    fields = (item for item in [("Content-Length", "10")])
    assert code_of(lambda: parse_response(200, fields)) == "invalid_response"


@pytest.mark.parametrize("framing", ["bogus", None, ""])
def test_a_body_with_an_unknown_framing_does_not_end_well(framing):
    with pytest.raises(ValueError):
        check_body_end(framing, None, 5, terminated=True)  # type: ignore[arg-type]


def test_a_chunked_body_ends_well_only_when_it_was_terminated():
    check_body_end("chunked", None, 5, terminated=True)
    assert code_of(lambda: check_body_end("chunked", None, 5, terminated=False)) == (
        "download_incomplete"
    )


# --- the messages say what the reference says they mean -----------------------------------------


@pytest.mark.parametrize(
    "code,must_say",
    [
        ("download_write_uncertain", ["yayınlanmış olabilir", "otomatik tekrar yapmayın"]),
        ("download_integrity_mismatch", ["--sha256", "Hedef oluşturulmadı"]),
        ("download_limit_exceeded", ["1 GiB", "Hedef oluşturulmadı"]),
        ("download_partial_unverified", [".yorunge-download-", "Hiçbir dosyaya dokunulmadı"]),
        ("download_busy", ["Hiçbir dosyaya dokunulmadı", "bitmesini bekleyin"]),
        ("download_output_exists", ["Dosyaya dokunulmadı"]),
        ("download_incomplete", ["yeniden çalıştırın"]),
        ("download_write_failed", ["Hedef oluşturulmadı"]),
        ("download_target_invalid", ["hedef"]),
    ],
)
def test_each_message_says_what_the_reference_says_it_means(code, must_say):
    for fragment in must_say:
        assert fragment in MESSAGES[code], (code, fragment)
    assert "silindi" not in MESSAGES["download_limit_exceeded"]


def test_an_unverified_trace_is_never_described_as_deleted_or_published():
    assert "Hiçbir dosyaya dokunulmadı" in MESSAGES["download_partial_unverified"]
    assert "yayınlanmış olabilir" in MESSAGES["download_write_uncertain"]
