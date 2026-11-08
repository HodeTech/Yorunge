"""The reference is the canonical table of the download errors; the code must say the same."""

import re
from pathlib import Path

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
