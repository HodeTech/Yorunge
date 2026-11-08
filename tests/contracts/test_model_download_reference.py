"""The "Model ağırlığı yüzeyi (P02-3n)" section of the reference is what the code does.

The status table, the prefix, the filename and size limits and the exit codes of that section are
checked against the transport's own classification and the error catalog, so that an edit of the
prose (a different exit, a widened prefix, a dropped rule) fails here, not in a reader.
"""

import re
from pathlib import Path

from yorunge.adapters.http_transport import _TRANSIENT
from yorunge.application.http_transport import HttpStatusFailure
from yorunge.application.model_download import FORMATS, MAX_FILENAME_BYTES, MODEL_FILES_SEGMENT
from yorunge.application.response_json import JSON_LIMIT
from yorunge.domain.download import DEFAULT_TIMEOUT_SECONDS, MAX_FOLD
from yorunge.domain.errors import YorungeError

REFERENCE = Path(__file__).parents[2] / "docs" / "reference" / "download-engine.md"

# The row labels of the table and the statuses each of them stands for.
STATUSES = {
    "401, 403": (401, 403),
    "404": (404,),
    "429": (429,),
    "500 ve": (500, 400, 405, 409, 410, 413, 422, 451, 501, 507),
    "408, 502/503/504": (408, 502, 503, 504),
    "yönlendirme": (301, 302, 303, 307, 308),
}


def section() -> str:
    text = REFERENCE.read_text()
    start = text.index("## Model ağırlığı yüzeyi (P02-3n)")
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def test_the_json_table_is_what_the_transport_does_with_each_status():
    rows = re.findall(r"^\| ([^|]+) \| `([a-z_]+)` \| (\d) \| (\d) \|", section(), re.MULTILINE)
    seen = set()
    answers = 0
    for label, code, exit_code, attempts in rows:
        key = next((k for k in STATUSES if label.startswith(k)), None)
        if key is None:
            # the two answer rules: a success that is not a 200, and a 200 that breaks the codec
            assert label.startswith("200"), label
            assert (code, int(exit_code), int(attempts)) == ("invalid_response", 1, 1)
            assert YorungeError("invalid_response").exit_code == 1
            answers += 1
            continue
        seen.add(key)
        for status in STATUSES[key]:
            failure = HttpStatusFailure(status)
            assert (failure.code, failure.exit_code) == (code, int(exit_code)), (label, status)
            expected_attempts = 2 if status in _TRANSIENT else 1
            if key != "yönlendirme":
                assert expected_attempts == int(attempts), (label, status)
    assert seen == set(STATUSES) and answers == 2, (seen, answers)


def test_the_prefix_the_name_the_limits_and_the_exits_are_the_codes():
    text = section()
    assert "{api_base_path}" + MODEL_FILES_SEGMENT in text
    assert f"{MAX_FILENAME_BYTES} bayt" in text and JSON_LIMIT == 1 << 20 and "1 MiB" in text
    assert f"0–{MAX_FOLD}" in text and set(FORMATS) == {"onnx", "pt", "tflite"}
    assert DEFAULT_TIMEOUT_SECONDS == 900
    for code in ("download_integrity_mismatch", "download_write_uncertain"):
        assert f"`{code}` {YorungeError(code).exit_code}" in text, code
    assert (
        YorungeError("request_cancelled").exit_code == YorungeError("output_closed").exit_code == 6
    )
    assert "`request_cancelled` ve `output_closed` 6" in text


def test_what_was_not_observed_is_said_not_to_have_been():
    text = section()
    assert "canlı yoklamayla doğrulanmadı" in text and "yoklama yapılmadı" in text
    assert "canlı yoklamada gözlenen" not in REFERENCE.read_text()


def test_the_cases_the_code_decides_by_the_target_not_the_credential_are_written_so():
    text = section()
    assert "Anahtar **hedefe aittir, kimlik bilgisine değil**" in text
    assert "başka bir profil/hizmetten" not in text
