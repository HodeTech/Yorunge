"""The edges of the pure download contract: exact limits, whitespace, types, purity, ordering.

One test per boundary that a plausible slip would move: a limit off by one, a trimmed character
too many, a type check dropped, a decision that depends on the hash seed, an import that makes a
pure module read a clock. The tables themselves are in the neighbouring files.
"""

import ast
import dataclasses
import os
import subprocess
import sys
from pathlib import Path

import pytest

import yorunge.domain as domain
from tests.contracts.test_download_contract import code_of, partial, summary
from tests.contracts.test_download_state import decide, entry, record, sidecar, stage
from yorunge.domain.download import (
    EMPTY_SHA256,
    DownloadPartial,
    DownloadSource,
    Verification,
    download_names,
    validate_target_name,
)
from yorunge.domain.download_response import (
    ContentRange,
    DownloadResponse,
    ResumeAsk,
    disposition,
    parse_etag,
    parse_response,
)
from yorunge.domain.download_state import StartDecision, confirm_prefix, resumable
from yorunge.domain.errors import YorungeError

TAG = '"v1-3f9c"'


class Subclass(str):
    """A str subclass: refused wherever the contract says 'text'."""


# --- download.py ----------------------------------------------------------------------------------


def test_validate_target_name_returns_the_name_it_validated():
    assert validate_target_name("weights.onnx") == "weights.onnx"


def test_a_str_subclass_is_not_a_target_name():
    assert code_of(lambda: validate_target_name(Subclass("weights.onnx"))) == (
        "download_target_invalid"
    )


@pytest.mark.parametrize(
    "name",
    [".yorunge-download", ".yorunge-downloadx", ".yorunge", "a.yorunge-download-b", "x.YORUNGE-"],
)
def test_only_a_name_that_starts_with_the_whole_prefix_is_reserved(name):
    assert validate_target_name(name) == name


@pytest.mark.parametrize("etag", ['"a"b"', '"v1"x', '"v1" ', ' "v1"', '"v1"\n', '"a b"'])
def test_the_sidecar_etag_is_exactly_one_quoted_run_of_the_alphabet(etag):
    with pytest.raises(ValueError):
        partial(etag=etag)


@pytest.mark.parametrize("size,capped", [(4096, False), (4097, True)])
def test_the_sidecar_cap_is_exact_and_applied_before_parsing(size, capped, monkeypatch):
    # A record that is too long is refused for its length, not for what the parser makes of it.
    calls = []
    original = DownloadPartial.model_validate_json.__func__  # type: ignore[attr-defined]

    def spy(cls, data, *args, **kwargs):
        calls.append(len(data))
        return original(cls, data, *args, **kwargs)

    monkeypatch.setattr(DownloadPartial, "model_validate_json", classmethod(spy))
    with pytest.raises(ValueError):
        DownloadPartial.decode(b" " * size)
    assert (calls == []) is capped


def test_a_file_identity_of_zero_is_representable():
    found = partial(stage_device=0, stage_inode=0)
    assert (found.stage_device, found.stage_inode) == (0, 0)
    assert DownloadPartial.decode(found.encoded()) == found


def test_the_output_path_limits_are_exact_in_characters_and_in_bytes():
    assert summary(output_path="x").output_path == "x"
    assert len(summary(output_path="x" * 4096).output_path) == 4096
    with pytest.raises(ValueError):
        summary(output_path="x" * 4097)
    with pytest.raises(ValueError):
        summary(output_path="é" * 2048 + "a")  # 2049 characters, 4097 bytes
    with pytest.raises(ValueError):
        summary(output_path="")
    with pytest.raises(ValueError):
        summary(output_path="/tmp/\udcffname")  # the name of a file that is not UTF-8


def test_a_negative_fold_is_not_a_source():
    source = {
        "kind": "model_version",
        "version_id": "00000000-0000-4000-8000-000000000123",
        "format": "onnx",
        "fold": -1,
    }
    with pytest.raises(ValueError):
        DownloadSource.model_validate(source)


def test_a_download_resumed_from_one_byte_is_valid_and_from_more_than_it_has_is_not():
    assert summary(bytes=2, resumed=True, resumed_from_bytes=1).resumed_from_bytes == 1
    with pytest.raises(ValueError):
        summary(bytes=0, sha256=EMPTY_SHA256, resumed=True, resumed_from_bytes=1)


def test_the_small_result_types_are_frozen():
    for value, attribute in (
        (Verification("transfer_complete", "none"), "level"),
        (download_names("weights.onnx"), "stage"),
    ):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(value, attribute, "x")


# --- download_response.py -------------------------------------------------------------------------


def test_the_value_types_of_an_answer_and_a_request_are_frozen():
    for value, attribute in (
        (ResumeAsk(400, 1000, TAG), "prefix_bytes"),
        (ContentRange(0, 9, 10), "first"),
        (DownloadResponse(200, None, None, "length", 10), "status"),
    ):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(value, attribute, -1)


def test_a_resume_may_start_after_one_byte_and_asks_for_a_text_tag():
    assert ResumeAsk(1, 1000, TAG).prefix_bytes == 1
    with pytest.raises(ValueError):
        ResumeAsk(400, 1000, Subclass(TAG))


def test_an_empty_body_is_a_framed_body():
    found = parse_response(200, [("Content-Length", "0")])
    assert (found.framing, found.content_length) == ("length", 0)


def fields_for(name, value):
    if name in ("Content-Length", "Transfer-Encoding"):
        return [(name, value)]  # each of these is the framing
    return [(name, value), ("Content-Length", "10")]


FILLS = ["\n", "\r", "\x0b", "\x0c", "\xa0", "\u2003", "\x00"]


@pytest.mark.parametrize("fill", FILLS)
@pytest.mark.parametrize(
    "name,good",
    [("Content-Length", "10"), ("Transfer-Encoding", "chunked"), ("Content-Encoding", "identity")],
)
def test_optional_whitespace_is_exactly_space_and_tab(name, good, fill):
    assert parse_response(200, fields_for(name, " \t" + good + "\t ")).status == 200
    for value in (fill + good, good + fill):
        with pytest.raises(YorungeError):
            parse_response(200, fields_for(name, value))


@pytest.mark.parametrize("fill", FILLS)
def test_a_tag_has_no_whitespace_around_it_but_space_and_tab(fill):
    assert parse_etag([" \t" + TAG + "\t "]) == TAG
    assert parse_etag([fill + TAG]) is None and parse_etag([TAG + fill]) is None


def test_header_names_are_not_trimmed():
    with pytest.raises(YorungeError):  # " Content-Length" is not Content-Length: no framing at all
        parse_response(200, [(" Content-Length", "10")])


def test_a_content_encoding_is_identity_or_empty_not_a_piece_of_the_word():
    for odd in ("ident", "id", "entity", "identit"):
        with pytest.raises(YorungeError):
            parse_response(200, [("Content-Encoding", odd), ("Content-Length", "10")])


def test_header_fields_may_be_a_tuple_and_must_be_plain_text():
    assert parse_response(200, (("Content-Length", "10"),)).content_length == 10
    for fields in (
        [(Subclass("Content-Length"), "10")],
        [("Content-Length", Subclass("10"))],
    ):
        with pytest.raises(YorungeError):
            parse_response(200, fields)


def test_a_416_carries_nothing_even_when_it_has_a_tag_and_a_length():
    found = parse_response(
        416, [("ETag", TAG), ("Content-Length", "5"), ("Content-Range", "bytes */9")]
    )
    assert found == DownloadResponse(416, None, None, None, None)


def test_a_partial_answer_of_the_right_length_but_not_framed_by_one_is_not_a_continuation():
    # hand-built responses: parse_response never makes them, disposition still judges them
    ask = ResumeAsk(400, 1000, TAG)
    odd = DownloadResponse(206, ContentRange(400, 999, 1000), TAG, "chunked", 600)
    assert disposition(odd, ask) == "discard_and_retry"
    unframed = DownloadResponse(206, ContentRange(400, 999, 1000), TAG, None, 600)
    assert disposition(unframed, ask) == "discard_and_retry"


@pytest.mark.parametrize("status", [301, 401, 403, 429, 500])
def test_header_fields_that_are_not_text_pairs_are_refused_before_the_status_is_mapped(status):
    assert code_of(lambda: parse_response(status, {"Content-Length": "10"})) == "invalid_response"


# --- download_state.py ----------------------------------------------------------------------------


def test_one_committed_byte_is_worth_resuming():
    assert resumable(etag=TAG, total_size=1000, committed_bytes=1) is True
    found = decide(
        stage=stage(size=1),
        sidecar=sidecar(rec=record(committed_bytes=1, prefix_sha256="ef" * 32)),
    )
    assert found.action == "resume" and found.ask is not None and found.ask.prefix_bytes == 1


def test_the_start_table_values_are_frozen():
    for value, attribute in ((entry(), "size"), (sidecar(), "record")):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(value, attribute, None)


@pytest.mark.parametrize("which", ["identity_key", "target_hash"])
@pytest.mark.parametrize("bad", ["ab" * 32 + "0", "ab" * 32 + "\n", Subclass("ab" * 32)])
def test_a_digest_is_exactly_64_hex_digits_of_plain_text(which, bad):
    with pytest.raises(ValueError):
        decide(**{which: bad})


@pytest.mark.parametrize("lock", ["HELD", "locked", "", None, True])
def test_any_lock_value_but_held_fails_closed(lock):
    found = decide(lock=lock, stage=stage(), sidecar=sidecar(), no_resume=True)
    assert (found.action, found.remove) == ("unverified", ())


def test_the_resume_ask_carries_the_tag_exactly_as_the_record_has_it():
    tag = '"V1-3f9C~a"'
    found = decide(stage=stage(), sidecar=sidecar(rec=record(etag=tag)))
    assert found.action == "resume" and found.ask is not None and found.ask.etag == tag


@pytest.mark.parametrize(
    "action", ["reuse_empty_stage", "unverified", "output_exists", "start_clean", "busy"]
)
def test_a_decision_that_does_not_resume_is_not_changed_by_a_prefix(action):
    plan = StartDecision(action)
    assert confirm_prefix(plan, "00" * 32) is plan
    assert confirm_prefix(plan, None) is plan


def test_a_wrong_digest_is_a_programming_error_even_when_the_lock_is_busy():
    with pytest.raises(ValueError):
        decide(lock="busy", identity_key="not-a-digest")


def test_the_discard_order_does_not_depend_on_the_hash_seed():
    # A set would iterate in an order the hash seed decides; the order is the fixed one.
    code = (
        "from tests.contracts.test_download_state import decide, entry, sidecar, stage\n"
        "from yorunge.domain.download_state import confirm_prefix\n"
        "first = decide(stage=stage(), sidecar=sidecar(), sidecar_tmp=entry(inode=8))\n"
        "print(confirm_prefix(first, '00' * 32).remove)\n"
        "second = decide(stage=stage(), sidecar=sidecar())\n"
        "print(confirm_prefix(second, '00' * 32).remove)\n"
    )
    root = Path(__file__).parents[2]
    for seed in range(8):
        found = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            env={**os.environ, "PYTHONHASHSEED": str(seed)},
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split("\n")
        assert found[0] == "('stage', 'sidecar', 'sidecar_tmp')", seed
        assert found[1] == "('stage', 'sidecar')", seed


# --- purity: "no I/O, clock or randomness" is enforced, not only stated ---------------------------

DOMAIN = Path(domain.__file__).parent
PURE = ("download.py", "download_response.py", "download_state.py")
ALLOWED = {
    "__future__",
    "collections.abc",
    "dataclasses",
    "hashlib",
    "pydantic",
    "re",
    "typing",
    "unicodedata",
}


@pytest.mark.parametrize("module", PURE)
def test_the_pure_modules_import_nothing_that_could_do_io_or_read_a_clock(module):
    tree = ast.parse((DOMAIN / module).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        for name in names:
            assert name in ALLOWED or name.startswith("yorunge.domain."), (module, name)
