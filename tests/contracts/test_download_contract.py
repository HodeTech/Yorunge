"""The download contract: levels, values, the result, the partial-download record, names, errors.

Pure vectors, written independently of the code under test: no network, no file system.
"""

import hashlib
import json
import random
from pathlib import Path

import pytest

from yorunge.domain.download import (
    BLOCK_BYTES,
    CHECKPOINT_BYTES,
    CONTROL_CALL_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    EMPTY_SHA256,
    MAX_DOWNLOAD_BYTES,
    MAX_FOLD,
    MAX_SIDECAR_BYTES,
    MAX_TIMEOUT_SECONDS,
    MAX_URL_BYTES,
    MIN_TIMEOUT_SECONDS,
    DownloadPartial,
    DownloadSummary,
    download_names,
    identity_key,
    parse_fold,
    parse_sha256,
    parse_timeout,
    target_hash,
    validate_target_name,
    verify_expectation,
)
from yorunge.domain.errors import MESSAGES, DownloadIntegrityMismatch, YorungeError

FIXTURES = Path(__file__).parents[1] / "fixtures"
ZEROS, ONES = "0" * 64, "1" * 64
HELLO = hashlib.sha256(b"hello").hexdigest()


def code_of(action):
    with pytest.raises(YorungeError) as error:
        action()
    return error.value.code


# --- the numbers of the contract ------------------------------------------------------------------


def test_the_limits_and_times_are_the_documented_ones():
    assert MAX_DOWNLOAD_BYTES == 1_073_741_824  # 1 GiB
    assert (MIN_TIMEOUT_SECONDS, DEFAULT_TIMEOUT_SECONDS, MAX_TIMEOUT_SECONDS) == (30, 900, 3600)
    assert MAX_FOLD == 1024 and CONTROL_CALL_SECONDS == 30
    assert BLOCK_BYTES == 1_048_576 and CHECKPOINT_BYTES == 8 * 1_048_576
    assert MAX_SIDECAR_BYTES == 4096 and MAX_URL_BYTES == 16_384
    assert EMPTY_SHA256 == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


# --- the values of the arguments ------------------------------------------------------------------


@pytest.mark.parametrize("value,expected", [(0, 0), ("0", 0), (7, 7), ("1024", 1024), (1024, 1024)])
def test_a_fold_is_an_exact_integer_from_zero_to_1024(value, expected):
    assert parse_fold(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "+1",
        " 1",
        "1 ",
        "01",
        "1.0",
        "1e2",
        "-1",
        "",
        "١",
        "0x10",
        "1025",
        1025,
        -1,
        True,
        False,
        1.0,
        None,
        b"1",
    ],
)
def test_a_fold_that_is_not_an_exact_integer_in_range_is_refused(value):
    assert code_of(lambda: parse_fold(value)) == "invalid_request"


@pytest.mark.parametrize("value,expected", [(30, 30), ("30", 30), ("900", 900), (3600, 3600)])
def test_a_timeout_is_a_whole_number_of_seconds_from_30_to_3600(value, expected):
    assert parse_timeout(value) == expected


@pytest.mark.parametrize("value", [29, "29", 3601, "3601", "030", "+30", "30.0", "", True, 30.0])
def test_a_timeout_out_of_range_or_not_exact_is_refused(value):
    assert code_of(lambda: parse_timeout(value)) == "invalid_request"


def test_an_expected_digest_is_sixty_four_lowercase_hexadecimal_digits():
    assert parse_sha256(HELLO) == HELLO
    for bad in (
        HELLO.upper(),
        HELLO[:-1],
        HELLO + "0",
        "g" * 64,
        " " + HELLO,
        "",
        None,
        5,
        b"0" * 64,
    ):
        assert code_of(lambda bad=bad: parse_sha256(bad)) == "invalid_request"


# --- the levels (ADR-0032 §5) ---------------------------------------------------------------------


def test_bytes_without_an_expectation_are_only_a_complete_transfer():
    result = verify_expectation(HELLO, 5, None)
    assert (result.level, result.expectation_source) == ("transfer_complete", "none")


def test_bytes_that_match_the_users_digest_earn_the_sha256_level_from_that_source():
    result = verify_expectation(HELLO, 5, HELLO)
    assert (result.level, result.expectation_source) == ("sha256_matched", "user_supplied")


def test_a_digest_that_does_not_match_is_the_mismatch_with_the_computed_digest_and_nothing_else():
    with pytest.raises(DownloadIntegrityMismatch) as error:
        verify_expectation(HELLO, 5, ZEROS)
    assert error.value.code == "download_integrity_mismatch" and error.value.exit_code == 7
    assert error.value.details == {"computed_sha256": HELLO, "bytes": 5}
    assert error.value.envelope()["details"] == {"computed_sha256": HELLO, "bytes": 5}
    assert ZEROS not in json.dumps(error.value.envelope())  # the expectation is not echoed


@pytest.mark.parametrize(
    "computed,size,expected",
    [
        (HELLO.upper(), 5, None),
        (HELLO[:-1], 5, None),
        (HELLO, -1, None),
        (HELLO, MAX_DOWNLOAD_BYTES + 1, None),
        (HELLO, True, None),
        (HELLO, 5, HELLO.upper()),
        (HELLO, 5, "short"),
        (None, 5, None),
    ],
)
def test_malformed_inputs_to_the_level_logic_are_refused_not_judged(computed, size, expected):
    assert code_of(lambda: verify_expectation(computed, size, expected)) == "invalid_request"


# --- the result -----------------------------------------------------------------------------------


def summary(**changes):
    value = {
        "schema_version": 1,
        "kind": "download_summary",
        "output_path": "/tmp/weights.onnx",
        "bytes": 5,
        "sha256": HELLO,
        "verification_level": "transfer_complete",
        "expectation_source": "none",
        "resumed": False,
        "resumed_from_bytes": 0,
        "source": {
            "kind": "model_version",
            "version_id": "00000000-0000-4000-8000-000000000123",
            "format": "onnx",
            "fold": None,
        },
        **changes,
    }
    return DownloadSummary.model_validate(value)


def test_a_summary_carries_what_was_written_and_what_it_earned():
    found = summary()
    assert (found.bytes, found.sha256, found.verification_level) == (5, HELLO, "transfer_complete")
    assert json.loads(found.model_dump_json())["source"]["fold"] is None
    matched = summary(verification_level="sha256_matched", expectation_source="user_supplied")
    assert matched.expectation_source == "user_supplied"
    resumed = summary(bytes=10, resumed=True, resumed_from_bytes=4)
    assert (resumed.resumed, resumed.resumed_from_bytes) == (True, 4)
    nothing = summary(bytes=0, sha256=EMPTY_SHA256, resumed=True, resumed_from_bytes=0)
    assert (nothing.bytes, nothing.resumed) == (0, True)  # a complete stage of no bytes


@pytest.mark.parametrize(
    "changes",
    [
        {"verification_level": "sha256_matched", "expectation_source": "none"},
        {"verification_level": "transfer_complete", "expectation_source": "user_supplied"},
        {"resumed": True, "resumed_from_bytes": 0},
        {"resumed": True, "resumed_from_bytes": 6},
        {"resumed": False, "resumed_from_bytes": 1},
        {"bytes": 0},  # the digest of no bytes belongs to no bytes, and only to them
        {"bytes": 0, "sha256": "ab" * 32},
        {"bytes": 5, "sha256": EMPTY_SHA256},
        {"bytes": 0, "sha256": "ab" * 32, "resumed": True, "resumed_from_bytes": 5},
        {"bytes": 0, "sha256": EMPTY_SHA256, "resumed": True, "resumed_from_bytes": 5},
        {"output_path": ""},
        {"output_path": "/tmp/a\nb"},
        {"output_path": "x" * 4097},
        {"bytes": MAX_DOWNLOAD_BYTES + 1},
        {"bytes": -1},
        {"bytes": True},
        {"resumed": 1},
        {"sha256": HELLO.upper()},
        {"schema_version": 2},
        {"kind": "download_partial"},
        {"verification_level": "size_matched"},
        {"expectation_source": "provider_metadata"},
        {"extra": 1},
        {"source": {"kind": "dataset", "version_id": "x", "format": "onnx", "fold": None}},
        {
            "source": {
                "kind": "model_version",
                "version_id": "00000000-0000-4000-8000-000000000123",
                "format": "zip",
                "fold": None,
            }
        },
        {
            "source": {
                "kind": "model_version",
                "version_id": "00000000-0000-4000-8000-000000000123",
                "format": "pt",
                "fold": 1025,
            }
        },
        {
            "source": {
                "kind": "model_version",
                "version_id": "NOT-A-UUID",
                "format": "pt",
                "fold": 0,
            }
        },
    ],
)
def test_a_summary_that_overclaims_or_is_malformed_is_refused(changes):
    with pytest.raises(ValueError):
        summary(**changes)


# --- the partial-download record ------------------------------------------------------------------


def partial(**changes):
    value = {
        "schema_version": 1,
        "kind": "download_partial",
        "identity_key": "ab" * 32,
        "target_hash": "cd" * 32,
        "etag": '"v1-3f9c"',
        "total_size": 1000,
        "committed_bytes": 400,
        "prefix_sha256": "ef" * 32,
        "stage_device": 16777230,
        "stage_inode": 123456,
        "created_at": "2026-11-08T00:00:00.000000Z",
        "updated_at": "2026-11-08T00:05:00.000000Z",
        **changes,
    }
    return DownloadPartial.model_validate(value)


def test_the_record_encodes_to_the_canonical_bytes_written_by_hand():
    golden = (FIXTURES / "download-partial-v1.json").read_bytes()
    assert partial().encoded() == golden
    assert DownloadPartial.decode(golden) == partial()
    assert len(golden) < MAX_SIDECAR_BYTES


def test_the_longest_record_still_fits_the_sidecar_limit():
    longest = partial(
        etag='"' + "~" * 126 + '"',
        total_size=MAX_DOWNLOAD_BYTES,
        committed_bytes=MAX_DOWNLOAD_BYTES,
        stage_device=2**64 - 1,
        stage_inode=2**64 - 1,
    )
    assert len(longest.encoded()) <= MAX_SIDECAR_BYTES
    assert DownloadPartial.decode(longest.encoded()) == longest


def test_a_record_without_a_tag_or_a_total_is_valid_while_the_download_runs():
    chunked = partial(etag=None, total_size=None)
    assert not chunked.complete and DownloadPartial.decode(chunked.encoded()) == chunked
    assert partial(committed_bytes=1000).complete is True
    assert partial(total_size=None, committed_bytes=1000).complete is False  # length not fixed yet


def test_a_record_of_nothing_committed_has_the_digest_of_nothing():
    assert partial(committed_bytes=0, prefix_sha256=EMPTY_SHA256).committed_bytes == 0
    with pytest.raises(ValueError):
        partial(committed_bytes=0, prefix_sha256="ef" * 32)


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": 2},
        {"schema_version": True},
        {"kind": "download_summary"},
        {"identity_key": "AB" * 32},
        {"identity_key": "ab" * 31},
        {"target_hash": "x" * 64},
        {"etag": 'W/"v1"'},
        {"etag": '""'},
        {"etag": "v1"},
        {"etag": '"' + "a" * 127 + '"'},
        {"etag": '"a\tb"'},
        {"total_size": MAX_DOWNLOAD_BYTES + 1},
        {"total_size": -1},
        {"total_size": 399},
        {"committed_bytes": 1001},
        {"committed_bytes": True},
        {"committed_bytes": 400.0},
        {"committed_bytes": "400"},
        {"prefix_sha256": ""},
        {"stage_device": -1},
        {"stage_inode": 2**64},
        {"stage_device": True},
        {"created_at": "2026-11-08T00:00:00Z"},
        {"created_at": "2026-11-08 00:00:00.000000"},
        {"updated_at": "2026-11-07T23:59:59.999999Z"},
        {"extra": 1},
    ],
)
def test_a_record_that_is_not_strictly_valid_is_refused(changes):
    with pytest.raises(ValueError):
        partial(**changes)


def test_a_stored_copy_is_read_only_as_the_exact_canonical_bytes_of_a_valid_record():
    golden = (FIXTURES / "download-partial-v1.json").read_bytes()
    value = json.loads(golden)
    variants = {
        "spaces": json.dumps(value, sort_keys=True).encode(),
        "key order": json.dumps(
            dict(reversed(list(value.items()))), separators=(",", ":")
        ).encode(),
        "trailing newline": golden + b"\n",
        "missing field": json.dumps(
            {k: v for k, v in value.items() if k != "etag"}, sort_keys=True, separators=(",", ":")
        ).encode(),
        "extra field": json.dumps(
            {**value, "extra": 1}, sort_keys=True, separators=(",", ":")
        ).encode(),
        "duplicate key": golden[:-1] + b',"total_size":1000}',
        "not json": b"{",
        "empty": b"",
        "a list": b"[]",
        "oversize": golden + b" " * MAX_SIDECAR_BYTES,
        "not utf-8": b"\xff\xfe",
        "nan": golden.replace(b"1000", b"NaN"),
        "string where an integer is": golden.replace(b'"total_size":1000', b'"total_size":"1000"'),
        "bool where an integer is": golden.replace(b'"stage_inode":123456', b'"stage_inode":true'),
        "float where an integer is": golden.replace(b'"total_size":1000', b'"total_size":1000.0'),
    }
    for name, data in variants.items():
        with pytest.raises(ValueError):
            DownloadPartial.decode(data)
        assert name  # every variant is its own case
    with pytest.raises(ValueError):
        DownloadPartial.decode(bytearray(golden))  # only bytes, exactly as read


def test_the_record_is_frozen_and_hashable_by_value():
    first, second = partial(), partial()
    assert first == second
    with pytest.raises(ValueError):
        first.committed_bytes = 1  # type: ignore[misc]


# --- names ----------------------------------------------------------------------------------------


def test_the_target_hash_is_the_documented_domain_separated_digest_of_the_name():
    expected = hashlib.sha256(b"yorunge-download-target-v1\x00" + b"weights.onnx").hexdigest()
    assert target_hash("weights.onnx") == expected


def test_the_four_names_are_derived_from_the_hash_alone_and_have_a_fixed_length():
    names = download_names("weights.onnx")
    stem = ".yorunge-download-" + target_hash("weights.onnx")[:32]
    assert names.lock == stem + ".lock" and names.stage == stem + ".part"
    assert names.sidecar == stem + ".json" and names.sidecar_tmp == stem + ".json.tmp"
    for name in (names.lock, names.stage, names.sidecar, names.sidecar_tmp):
        assert "weights" not in name and "/" not in name and len(name) <= 59


@pytest.mark.parametrize(
    "name",
    [
        "a",
        "ağırlık.onnx",
        "é" * 127,
        "x" * 255,
        "weights.onnx.part",
        "weights.onnx.lock",
        "A.bin",
        "a.bin",
        "a b",
        "-rf",
        "~",
        "CON",
        "nul",
        "name.",
        " x",
        "x ",
    ],
)
def test_every_valid_name_gets_names_of_one_length_and_no_other_shape(name):
    names = download_names(name)
    prefix = len(".yorunge-download-") + 32
    assert [len(names.lock), len(names.stage), len(names.sidecar)] == [prefix + 5] * 3
    assert len(names.sidecar_tmp) == prefix + len(".json.tmp")
    for item in (names.lock, names.stage, names.sidecar, names.sidecar_tmp):
        assert item.startswith(".yorunge-download-") and "/" not in item


def test_different_names_never_share_a_file_name_and_a_name_is_stable():
    rng = random.Random(7)
    seen: dict[str, str] = {}
    for _ in range(20000):
        name = "".join(
            rng.choice("abcdefghijklmnopqrstuvwxyzğüşıöçÇ0123456789._-")
            for _ in range(rng.randint(1, 40))
        )
        if name in {".", ".."} or name.startswith(".yorunge-download-"):
            continue
        stem = download_names(name).stage
        assert seen.setdefault(stem, name) == name  # one stem, one name: no collision
        assert download_names(name) == download_names(name)
    assert len(seen) > 19000


def test_spellings_that_a_filesystem_may_fold_are_different_names_here():
    assert download_names("Weights.onnx").stage != download_names("weights.onnx").stage
    assert download_names("é").stage != download_names("é").stage  # NFC vs NFD bytes


@pytest.mark.parametrize(
    "name",
    [
        "",
        ".",
        "..",
        "a/b",
        "/",
        "a\x00b",
        "a\nb",
        "a\tb",
        "a\x7fb",
        "a\x85b",
        "x" * 256,
        "é" * 128,
        "a\u202eb",
        "a\u200fb",
        "a\u2066b",
        "a\u200bb",
        "a\ufeffb",
        "a\u2028b",
        "a\ud800b",
        "\u0378",  # unassigned in every Unicode version this project can run on
        ".yorunge-download-abc.part",
        ".yorunge-download-",
        None,
        5,
        b"x",
    ],
)
def test_a_target_name_that_is_not_one_printable_ordinary_name_is_refused(name):
    assert code_of(lambda: validate_target_name(name)) == "download_target_invalid"
    assert code_of(lambda: download_names(name)) == "download_target_invalid"


def test_the_identity_key_is_bound_to_the_service_target_the_thing_and_the_fold():
    base = {
        "origin": "https://api.ssyz.org.tr",
        "api_base_path": "/api/v1",
        "kind": "model_version",
        "resource_id": "00000000-0000-4000-8000-000000000123",
        "artifact_format": "onnx",
        "fold": None,
    }
    key = identity_key(**base)
    assert len(key) == 64 and key == identity_key(**base)
    for field, value in {
        "origin": "https://staging.ssyz.org.tr",
        "api_base_path": "/api/v2",
        "kind": "dataset",
        "resource_id": "00000000-0000-4000-8000-000000000124",
        "artifact_format": "pt",
        "fold": 0,
    }.items():
        assert identity_key(**{**base, field: value}) != key, field
    assert identity_key(**{**base, "fold": 1}) != identity_key(**{**base, "fold": 0})
    for field in ("origin", "api_base_path", "kind", "resource_id", "artifact_format"):
        assert code_of(lambda field=field: identity_key(**{**base, field: ""})) == "invalid_request"
        assert (
            code_of(lambda field=field: identity_key(**{**base, field: "a\nb"}))
            == "invalid_request"
        )
    assert code_of(lambda: identity_key(**{**base, "fold": 1025})) == "invalid_request"
    assert code_of(lambda: identity_key(**{**base, "fold": True})) == "invalid_request"


# --- the nine codes -------------------------------------------------------------------------------

CODES = {
    "download_target_invalid": 2,
    "download_output_exists": 2,
    "download_partial_unverified": 2,
    "download_busy": 2,
    "download_limit_exceeded": 2,
    "download_integrity_mismatch": 7,
    "download_incomplete": 1,
    "download_write_failed": 2,
    "download_write_uncertain": 5,
}


@pytest.mark.parametrize("code,exit_code", CODES.items())
def test_each_download_code_has_its_exit_a_fixed_message_and_an_empty_detail(code, exit_code):
    error = YorungeError(code)
    assert error.exit_code == exit_code and error.message == MESSAGES[code]
    envelope = error.envelope()
    assert (
        envelope["code"] == code and envelope["details"] == {} and envelope["operation_id"] is None
    )
    # A fixed message names no file, path, address, tag or provider text, and takes no value.
    assert (
        "{" not in error.message and "%" not in error.message and error.message.endswith((".", ";"))
    )


def test_the_download_messages_are_distinct_and_never_the_manifests():
    messages = [MESSAGES[code] for code in CODES]
    assert len(set(messages)) == len(messages)
    assert not set(messages) & {
        MESSAGES["manifest_output_exists"],
        MESSAGES["manifest_write_failed"],
    }


def test_the_mismatch_detail_is_closed_and_refuses_what_is_not_a_digest_and_a_count():
    for digest, size in (
        (HELLO.upper(), 5),
        ("x" * 64, 5),
        (HELLO, -1),
        (HELLO, MAX_DOWNLOAD_BYTES + 1),
        (HELLO, True),
        (None, 5),
    ):
        with pytest.raises(ValueError):
            DownloadIntegrityMismatch(digest, size)
    assert set(DownloadIntegrityMismatch(HELLO, 0).details) == {"computed_sha256", "bytes"}


def test_a_download_limit_is_the_transports_raw_limit():
    # ``body_failure`` reads the transport's size cap as the download's limit on this premise.
    from yorunge.application.http_transport import RAW_LIMIT

    assert MAX_DOWNLOAD_BYTES == RAW_LIMIT


def test_a_complete_stage_of_no_bytes_publishes_as_a_resumed_download_of_no_bytes():
    summary = {
        "schema_version": 1,
        "kind": "download_summary",
        "output_path": "/tmp/weights.onnx",
        "bytes": 0,
        "sha256": EMPTY_SHA256,
        "verification_level": "transfer_complete",
        "expectation_source": "none",
        "resumed": True,
        "resumed_from_bytes": 0,
        "source": {
            "kind": "model_version",
            "version_id": "11111111-1111-4111-8111-111111111111",
            "format": "onnx",
            "fold": None,
        },
    }
    assert DownloadSummary.model_validate(summary).resumed is True
    # Resuming from nothing is still not resuming a download that has bytes.
    with pytest.raises(ValueError):
        DownloadSummary.model_validate({**summary, "bytes": 10})


@pytest.mark.parametrize(
    "wire",
    [b"[" * 4000, b"[" * 2000 + b"]" * 2000, b'{"a":' * 700, b"[" * 600 + b"]" * 600],
    ids=["open brackets", "balanced brackets", "nested objects", "moderate nesting"],
)
def test_a_deeply_nested_stored_record_is_a_value_error_and_never_a_crash(wire):
    # The sidecar is read from a directory the user can write: it is "unverified", not a traceback.
    with pytest.raises(ValueError):
        DownloadPartial.decode(wire)
