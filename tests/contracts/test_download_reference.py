"""The reference is the canonical table of the download errors; the code must say the same.

It is also the oracle of the wire table, the limits, the names and the closed order of the local
protocol: each of those is pinned here to the behaviour it describes, so that a reference edited
away from the code (or a code edited away from the reference) is caught by a test, not by a reader.
"""

import re
from pathlib import Path

import pytest

from yorunge.domain.download import (
    BLOCK_BYTES,
    CHECKPOINT_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_DOWNLOAD_BYTES,
    MAX_SIDECAR_BYTES,
    download_names,
    parse_timeout,
    validate_target_name,
)
from yorunge.domain.download_response import ResumeAsk, disposition, parse_response
from yorunge.domain.download_state import REMOVAL_ORDER
from yorunge.domain.errors import MESSAGES, YorungeError

REFERENCE = Path(__file__).parents[2] / "docs" / "reference" / "download-engine.md"


def table(section):
    text = REFERENCE.read_text()
    start = text.index(f"## {section}")
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def test_the_errors_table_is_the_nine_codes_with_the_exits_the_code_gives_them():
    rows = re.findall(
        r"^\| `(download_[a-z_]+)` \| (\d) \|", table("Sonuç ve hatalar"), re.MULTILINE
    )
    assert len(rows) == len({code for code, _ in rows}) == 9
    for code, exit_code in rows:
        assert code in MESSAGES, code
        assert YorungeError(code).exit_code == int(exit_code), code  # type: ignore[arg-type]
    declared = {code for code in MESSAGES if code.startswith("download_")}
    assert declared == {code for code, _ in rows}


def test_the_wire_table_names_only_codes_that_exist():
    wire = table("Yanıt işleme (kapalı tablo)")
    mentioned = set(re.findall(r"`([a-z]+_[a-z_]+)(?:/\d)?`", wire))
    codes = {name for name in mentioned if name in MESSAGES}
    # Every closed code the table sends an answer to is a real code of the catalogue.
    assert {
        "invalid_response",
        "remote_failed",
        "remote_access_denied",
        "remote_rate_limited",
    } <= codes
    assert "download_incomplete" in codes
    # Every code the table writes with an exit status is that code with that status.
    for code, status in re.findall(r"`([a-z]+(?:_[a-z]+)+)`/(\d)", wire):
        assert code in MESSAGES, code
        assert YorungeError(code).exit_code == int(status), code  # type: ignore[arg-type]


def test_the_wire_table_sends_each_status_where_the_parser_sends_it():
    from yorunge.domain.download_response import parse_response

    wire = table("Yanıt işleme (kapalı tablo)")
    rows = {
        cells[0].strip(): cells[1]
        for cells in (
            line.strip("| ").split("|", 1) for line in wire.splitlines() if line.startswith("| ")
        )
        if len(cells) == 2
    }
    for label, status in {"3xx": 302, "401/403": 401, "429": 429, "5xx": 503}.items():
        code = re.search(r"`([a-z_]+)`", next(v for k, v in rows.items() if k.startswith(label)))
        assert code is not None, label
        try:
            parse_response(status, [("Content-Length", "0")])
        except YorungeError as error:
            assert error.code == code.group(1), (label, error.code)
        else:
            raise AssertionError(f"{status} is not refused")
    other_4xx = next(v for k, v in rows.items() if k.startswith("404 ve diğer 4xx"))
    try:
        parse_response(404, [("Content-Length", "0")])
    except YorungeError as error:
        assert f"`{error.code}`" in other_4xx
    other_2xx = next(v for k, v in rows.items() if k.startswith("Diğer 2xx"))
    try:
        parse_response(201, [("Content-Length", "0")])
    except YorungeError as error:
        assert f"`{error.code}`" in other_2xx


# --- the wire table, row by row, against the behaviour it describes -------------------------------

APOS = "\u2019"  # the reference writes its apostrophes as U+2019
TAG = '"v1-3f9c"'
ASK = ResumeAsk(400, 1000, TAG)  # a prefix of 400 of 1000: the tail is 600


def wire_rows():
    text = table("Yanıt işleme (kapalı tablo)")
    rows = []
    for line in text.splitlines():
        if line.startswith("| ") and not line.startswith("| Durum") and not line.startswith("|---"):
            label, _, result = line.strip("| ").partition("|")
            rows.append((label.strip(), result.strip()))
    return rows


def row(prefix):
    found = [result for label, result in wire_rows() if label.startswith(prefix)]
    assert len(found) == 1, prefix
    return found[0]


def answer(status, **fields):
    fields.setdefault("Content_Length", "10")
    return parse_response(status, [(k.replace("_", "-"), v) for k, v in fields.items()])


def test_the_full_answer_rows_are_what_the_contract_does():
    plain = row(f"`200`, Range{APOS}siz istek")
    assert "Tam gövde" in plain
    assert "`invalid_response`" in plain
    assert disposition(answer(200), None) == "full"

    ignored = row(f"`200`, Range{APOS}li istek (`Content-Range` yok")
    assert "`ftruncate(0)`" in ignored
    assert "ek istek yok" in ignored
    assert disposition(answer(200, Content_Length="1000"), ASK) == "restart"

    tail = row(f"`200`, Range{APOS}li istek, `Content-Length` tam olarak")
    assert f"Range{APOS}siz istek" in tail
    assert "T−N" in tail
    assert disposition(answer(200, Content_Length="600"), ASK) == "discard_and_retry"

    mislabelled = row("`200` + `Content-Range`")
    assert f"Range{APOS}siz istek" in mislabelled
    assert "`invalid_response`/1" in mislabelled
    labelled = answer(200, Content_Range="bytes 400-999/1000", Content_Length="600")
    assert disposition(labelled, ASK) == "discard_and_retry"
    with pytest.raises(YorungeError) as error:
        disposition(labelled, None)
    assert error.value.code == "invalid_response"


def test_the_partial_answer_rows_are_what_the_contract_does():
    exact = answer(206, Content_Range="bytes 400-999/1000", Content_Length="600", ETag=TAG)
    assert row("`206` + tam `Content-Range") == "Devam"
    assert disposition(exact, ASK) == "continue"

    dropped = row("`206` ETag/`Content-Range`/`Content-Length` uyumsuz")
    assert f"Range{APOS}siz istekten **önce** atılır (stage, sonra sidecar)" in dropped
    for changed in (
        answer(206, Content_Range="bytes 400-999/1000", Content_Length="600", ETag='"other"'),
        answer(206, Content_Range="bytes 399-999/1000", Content_Length="601", ETag=TAG),
        answer(206, Content_Range="bytes 400-999/1000", Content_Length="599", ETag=TAG),
        answer(206, Content_Range="bytes 400-999/1000", ETag=TAG, Transfer_Encoding="chunked"),
        parse_response(206, []),  # no framing at all
        parse_response(416, []),
    ):
        assert disposition(changed, ASK) == "discard_and_retry"

    refused = row("`206`, Range göndermeyen isteğe")
    assert "`invalid_response`/1" in refused
    for unasked in (exact, parse_response(416, [])):
        with pytest.raises(YorungeError) as error:
            disposition(unasked, None)
        assert error.value.code == "invalid_response"


def test_the_rows_of_the_wire_table_are_all_present():
    labels = [label for label, _ in wire_rows()]
    assert len(labels) == 15
    assert labels[0].startswith("Sidecar+stage tamam")  # the offline row comes first
    assert labels[-1].startswith("Gövde fazında kopma")  # and the body-phase row last


# --- the limits, against the constants ------------------------------------------------------------


def test_the_limits_of_the_reference_are_the_limits_of_the_code():
    limits = table("Motor sınırı")
    assert MAX_DOWNLOAD_BYTES == 1 << 30
    assert "1 GiB" in limits
    assert BLOCK_BYTES == 1 << 20
    assert "1 MiB" in limits
    assert MAX_SIDECAR_BYTES == 4096
    assert "≤4 KiB" in limits
    assert CHECKPOINT_BYTES == 8 << 20
    assert "8 MiB" in table("Stage ve sidecar protokolü")
    assert DEFAULT_TIMEOUT_SECONDS == 900
    assert "varsayılan 900 s" in limits
    assert "30–3600" in limits
    assert parse_timeout(30) == 30
    assert parse_timeout(3600) == 3600
    for outside in (29, 3601):
        with pytest.raises(YorungeError):
            parse_timeout(outside)
    assert "koşunun başında" in limits
    assert "düşülmez" in limits  # the deadline's own start


def test_the_names_of_the_reference_are_the_names_of_the_code():
    names = download_names("weights.onnx")
    assert (len(names.lock), len(names.stage), len(names.sidecar)) == (55, 55, 55)
    assert len(names.sidecar_tmp) == 59
    text = table("Saf sözleşme (P02-3j)")
    assert "55" in text
    assert "59" in text
    assert "ilk 32 hex" in text
    for spelling in (".yorunge-download-x", ".YORUNGE-DOWNLOAD-x", ".Yorunge-Download-"):
        with pytest.raises(YorungeError):
            validate_target_name(spelling)
    assert "herhangi bir harf büyüklüğünde" in text


# --- the closed order of the local protocol -------------------------------------------------------

STEPS = [
    ("parent", "`download_target_invalid`"),
    ("Kilit nesnesi", "`O_CREAT|O_EXCL|O_NOFOLLOW|O_RDWR`", "`fchmod(0600)`", "`umask`"),
    ("`flock(LOCK_EX|LOCK_NB)`", "`download_busy`"),
    ("Kilit altında", "`download_output_exists`"),
    ("Gözlem ve karar", "`lstat`", "yaratmaz", "`decide_start`"),
    (
        "Karar uygulanır",
        "Silme listesi sırayla (stage → sidecar → tmp;",
        "`confirm_prefix`",
        "en çok bir kez",
    ),
    ("Tam-stage", "11. adıma", "JSON çağrısı"),
    ("başlık checkpoint", "ilk gövde baytından önce"),
    ("1 MiB", "8 MiB", "Temiz durma"),
    ("tamamlanma checkpoint", "`committed_bytes == total_size`"),
    ("Beklenti karşılaştırması", "`download_integrity_mismatch`"),
    ("`full_sync`", "exclusive `link()`", "`download_write_uncertain`"),
    ("Stage `unlink`", "sidecar `unlink`", "**kilit nesnesi `unlink`**", "en son"),
]


def steps():
    text = table("Stage ve sidecar protokolü")
    found = re.findall(r"^(\d+)\. (.*)$", text, re.MULTILINE)
    return [(int(number), body) for number, body in found]


def test_the_closed_order_has_thirteen_steps_in_order_with_their_marks():
    found = steps()
    assert [number for number, _ in found] == list(range(1, 14))
    for (number, body), marks in zip(found, STEPS, strict=True):
        for mark in marks:
            assert mark in body, (number, mark)


def test_the_cleanup_order_is_stage_then_sidecar_then_tmp_then_the_lock_object_last():
    assert REMOVAL_ORDER == ("stage", "sidecar", "sidecar_tmp")
    last = steps()[12][1]
    positions = [last.index(mark) for mark in ("Stage `unlink`", "sidecar `unlink`", "tmp")]
    assert positions == sorted(positions)
    assert last.index("tmp") < last.index("**kilit nesnesi `unlink`**")
    # the local state is looked at (5) before anything is created, the decision is carried out (6)
    # before the network (7), and the whole of it before the answer is written (8-10)
    observe, apply = steps()[4][1], steps()[5][1]
    assert "bu koşu henüz hiçbirini yaratmaz" in observe
    assert "kararın silmeleri" in apply or "Silme listesi" in apply
    # the prefix is hashed and confirmed BEFORE the removals the decision lists are carried out
    assert apply.index("confirm_prefix") < apply.index("Silme listesi")


def test_the_engine_section_states_the_constants_and_the_order_of_the_engine():
    from yorunge.adapters.download_engine import (
        JSON_BUDGET_SECONDS,
        PROGRESS_SECONDS,
        RESOLVE_GRACE_SECONDS,
    )
    from yorunge.domain.models import MAX_REPORTED_PATH_BYTES

    section = table("Motor (P02-3m)")
    assert JSON_BUDGET_SECONDS == 30.0
    assert "30 sn" in section
    assert "düşülmez" in section
    assert RESOLVE_GRACE_SECONDS == 1.0
    assert "bütçe + 1 sn" in section
    assert PROGRESS_SECONDS == 0.1
    assert "saniyede en çok on" in section
    assert "en çok iki GET" in section
    assert "tamponlamaz" in section
    assert "yerel durumu her istekten önce" in section
    assert "`complete(terminated=True)`" in section
    assert section.index("Tam-stage ise ağ koşusu yoktur") < section.index("en çok iki GET")
    # the framing ends, the whole-body mark is written, THEN the last report
    assert section.index("`complete(terminated=True)` yazılır") < section.index("sonra son rapor")
    assert MAX_REPORTED_PATH_BYTES == 4096
    assert "4096 bayt" in section
    assert "≤16 KiB" in section  # the size of one TLS record, which is what is written at a time
