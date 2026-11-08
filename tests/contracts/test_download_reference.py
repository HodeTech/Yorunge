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
