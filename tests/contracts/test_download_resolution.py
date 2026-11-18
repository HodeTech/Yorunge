"""The catalog resolution as the download summary carries it (P02-4f)."""

import hashlib

import pytest
from pydantic import ValidationError

from yorunge.domain.download import DownloadResolution, DownloadSource, DownloadSummary

VERSION = "00000000-0000-4000-8000-000000000123"
OTHER = "00000000-0000-4000-8000-0000000000aa"
DATA = b"weights"


def resolution(**overrides):
    values = {
        "model_id": "model-uuid-1",
        "owner": "owner-1",
        "slug": "model-a",
        "version_tag": "1.1",
        "version_id": VERSION,
    }
    values.update(overrides)
    return DownloadResolution(**values)


def summary(resolved=None, version_id=VERSION):
    return DownloadSummary(
        schema_version=1,
        kind="download_summary",
        output_path="/tmp/out/weights.onnx",
        bytes=len(DATA),
        sha256=hashlib.sha256(DATA).hexdigest(),
        verification_level="transfer_complete",
        expectation_source="none",
        resumed=False,
        resumed_from_bytes=0,
        source=DownloadSource(
            kind="model_version", version_id=version_id, format="onnx", fold=None
        ),
        resolution=resolved,
    )


def test_a_resolution_with_plain_names_is_accepted_and_is_optional():
    assert resolution().version_tag == "1.1"
    assert summary().resolution is None
    assert summary(resolution()).resolution.version_id == VERSION


@pytest.mark.parametrize(
    "field,value",
    [
        ("owner", "own\x1ber"),
        ("slug", " model-a"),
        ("version_tag", "1.1‮"),
        ("model_id", "model​uuid"),
        ("version_tag", "1.1 "),
    ],
)
def test_a_resolution_name_with_control_format_or_edge_characters_is_refused(field, value):
    with pytest.raises(ValidationError):
        resolution(**{field: value})


def test_a_resolution_that_names_another_version_than_the_one_downloaded_is_refused():
    with pytest.raises(ValidationError):
        summary(resolution(version_id=OTHER), version_id=VERSION)
