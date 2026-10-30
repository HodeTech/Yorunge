"""The installed-console verifier rejects incomplete or relabeled event output."""

import json
import runpy
from pathlib import Path

import pytest

CHECKS = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / "scripts/verify-distributions.py")
)
inspect_result = CHECKS["installed_ndjson_payload"]


def event():
    return {
        "schema_version": 1,
        "stream_id": "09507038-0ec3-47ca-a6a0-c1ee128cfbdc",
        "sequence": 1,
        "event": "result",
        "operation_id": None,
        "payload": {"data": {"text": "Türkçe"}},
    }


def test_installed_result_preserves_payload():
    expected = event()
    assert inspect_result(json.dumps(expected, ensure_ascii=False) + "\n") == expected["payload"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("sequence", True),
        ("sequence", 2),
        ("event", "error"),
        ("operation_id", "09507038-0ec3-47ca-a6a0-c1ee128cfbdc"),
        ("stream_id", "09507038-0ec3-17ca-a6a0-c1ee128cfbdc"),
        ("stream_id", "09507038-0EC3-47CA-A6A0-C1EE128CFBDC"),
        ("extra", "unexpected"),
    ],
)
def test_installed_event_wire_mismatch_is_rejected(field, value):
    raw = {**event(), field: value}
    encoded = json.dumps(raw) + "\n"
    with pytest.raises(ValueError):
        inspect_result(encoded)


@pytest.mark.parametrize("extra", ["", "\n\n", "\n{}\n"])
def test_installed_result_requires_exactly_one_complete_line(extra):
    encoded = json.dumps(event()) + extra
    with pytest.raises(ValueError):
        inspect_result(encoded)
