"""The reference is the canonical table of the version errors; the code must say the same."""

import re
from pathlib import Path

from yorunge.domain.errors import (
    MESSAGES,
    VERSION_ANNOTATION_FIELDS,
    VERSION_IDENTITY_FIELDS,
    YorungeError,
)

REFERENCE = Path(__file__).parents[2] / "docs" / "reference" / "dataset-versions.md"
OWN = ("dataset_version_", "binding_")


def test_the_error_table_is_the_eight_own_codes_and_state_changed_with_the_exits_the_code_gives():
    text = REFERENCE.read_text()
    rows = re.findall(r"^\| `([a-z_]+)` \| (\d) \|", text, re.MULTILINE)
    own = [(code, int(exit_code)) for code, exit_code in rows if code.startswith(OWN)]
    assert len(own) == len({code for code, _ in own}) == 8
    for code, exit_code in own:
        assert code in MESSAGES, code
        assert YorungeError(code).exit_code == exit_code, code  # type: ignore[arg-type]
    declared = {code for code in MESSAGES if code.startswith(OWN)}
    assert declared == {code for code, _ in own}
    assert ("state_changed", 2) in [(code, int(exit_code)) for code, exit_code in rows]


def test_the_changed_fields_of_the_reference_are_the_closed_sets_of_the_code():
    text = REFERENCE.read_text()
    start = text.index("`changed_fields` kapalı kümesi")
    section = text[start : text.index("`annotation_only=true`", start)]
    identity, annotation = section.split("açıklama alanları:")
    named = lambda block: set(re.findall(r"`([a-z0-9_]+)`", block)) - {"changed_fields"}  # noqa: E731
    assert named(identity) == set(VERSION_IDENTITY_FIELDS)
    assert named(annotation) == set(VERSION_ANNOTATION_FIELDS)
