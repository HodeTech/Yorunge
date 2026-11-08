"""The reference is the canonical table of the version errors; the code must say the same."""

import re
from pathlib import Path

from yorunge.adapters.dataset_version_reader import VERSION_SECONDS
from yorunge.domain.credentials import ServiceTarget
from yorunge.domain.dataset_version import (
    MAX_BINDING_BYTES,
    MAX_CLASS_LABELS,
    MAX_LIST_ITEMS,
    MAX_PAGE,
    MIN_PAGE,
    DatasetVersionBinding,
    DatasetVersionBound,
    DatasetVersionCheck,
    DatasetVersionList,
    DatasetVersionListItem,
    DatasetVersionObservation,
    LocalManifestRelation,
)
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


def names(block):
    """The field names a sentence of the reference spells in backticks (name or name=value)."""
    return set(re.findall(r"`([a-z_0-9]+)(?:=[^`]*)?`", block))


def test_the_binding_fields_of_the_reference_are_the_fields_of_the_model():
    text = REFERENCE.read_text()
    start = text.index("`DatasetVersionBinding v1` alanları:")
    section = text[start : text.index("Digest, `digest` ve `observed_at` hariç", start)]
    top = re.sub(r"\([^)]*\)", "", section)  # the nested keys are checked below
    assert names(top) == set(DatasetVersionBinding.model_fields)
    service = re.search(r"`service` \(([^:)]*)", section)
    assert service is not None and names(service.group(1)) == set(ServiceTarget.model_fields)
    manifest = re.search(r"`local_manifest` \(([^)]*)\)", section)
    expected = set(LocalManifestRelation.model_fields)
    assert manifest is not None and names(manifest.group(1)) == expected


def test_the_observation_and_list_fields_of_the_reference_are_the_fields_of_the_models():
    text = REFERENCE.read_text()
    start = text.index("`DatasetVersionObservation v1`")
    section = text[start : text.index("Hepsi strict/frozen/extra-forbid", start)]
    listed = re.sub(r"\{[^}]*\}", "", section.split("alanları:", 1)[1])
    assert names(listed) == set(DatasetVersionObservation.model_fields)
    assert set(DatasetVersionListItem.model_fields) == set(
        DatasetVersionObservation.model_fields
    ) - {"class_count", "class_labels_sha256"}
    kind = "`kind=dataset_version_list_item`"
    assert kind in text and "`kind=dataset_version_list`" in text


def test_the_page_fields_of_the_reference_are_the_fields_of_the_page_model():
    text = REFERENCE.read_text()
    start = text.index("`DatasetVersionList v1` olarak verir (") + len(
        "`DatasetVersionList v1` olarak verir ("
    )
    section = text[start : text.index("satırlar sayfa boyutunu aşamaz", start)]
    assert names(section) == set(DatasetVersionList.model_fields)


def test_the_check_fields_of_the_reference_are_the_fields_of_the_check_model():
    text = REFERENCE.read_text()
    opening = "`DatasetVersionCheck v1` döndürür ("
    start = text.index(opening) + len(opening)
    section = text[start : text.index("); diğer sonuçlar hata zarfıdır", start)]
    assert names(section) == set(DatasetVersionCheck.model_fields)


def test_the_bound_fields_of_the_reference_are_the_fields_of_the_bound_model():
    text = REFERENCE.read_text()
    opening = "`bind` → `DatasetVersionBound` ("
    start = text.index(opening) + len(opening)
    section = text[start : text.index("; dosyanın kendisi değil özeti)", start)]
    assert names(section) == set(DatasetVersionBound.model_fields)


def test_the_numeric_limits_of_the_reference_are_the_limits_of_the_code():
    assert (MIN_PAGE, MAX_PAGE, MAX_LIST_ITEMS) == (1, 10_000, 100)
    assert (MAX_CLASS_LABELS, MAX_BINDING_BYTES, VERSION_SECONDS) == (4096, 16 * 1024, 30.0)
    text = REFERENCE.read_text()
    for phrase in (
        "`--page` 1–10 000",
        "`1 ≤ page_size ≤ 100`",
        "en çok 4096 etiket",
        "16 KiB üstü",
        "`monotonic() + VERSION_SECONDS`, 30 s",
        "1 MiB",
    ):
        assert phrase in text, phrase
