import json
from copy import deepcopy
from dataclasses import fields

import pytest

from yorunge.adapters.state_schema import (
    MIGRATIONS,
    Migration,
    MigrationV2,
    migration_from_json,
    migration_from_manifest,
)
from yorunge.domain.errors import YorungeError


def test_published_v1_checksums_and_exact_manifest_fields_are_unchanged():
    assert {field.name for field in fields(Migration)} == {
        "from_version",
        "to_version",
        "statements",
    }
    assert [step.checksum for step in MIGRATIONS[:4]] == [
        "887949c2f732f93c49d9b80417ec0abaff3bdbb140c3a009159274963f624fa9",
        "a584fd902efdee8db7582f13134c39be43bf356f6a8819d0357ad3d9c99790ff",
        "7471804a4728134f2fea73cbbfe8a7bccfccd838c848094ebc005d60520ea6e9",
        "b33a7e2027d2c1e5f2d8e28fba7b89aee06e097dae458cb4dbf1fa9ac77c8dd8",
    ]
    for step in MIGRATIONS[:4]:
        assert set(step.manifest()) == {"from_version", "to_version", "statements"}
        assert migration_from_manifest(step.manifest()) == step


def test_data_v2_and_sql_only_v2_have_distinct_closed_shapes():
    step = MIGRATIONS[-1]
    assert isinstance(step, MigrationV2)
    assert step.from_version == 4
    assert step.to_version == 5
    assert step.data_transform.code_sha256 == (
        "b1ffc8e3ce1dc6fc04c2afe4c2aa50ed6cd2e26deaf0b07ef0caab6fc0c83d18"
    )
    assert step.checksum == "2f627c2b5ae872ca8f36d947e8ecad6e86e73d242dd1e712eb92abf0932b3b33"
    assert migration_from_manifest(step.manifest()) == step
    sql = MigrationV2(5, 6, ("CREATE TABLE next_consumer(value TEXT) STRICT",))
    assert set(sql.manifest()) == {"manifest_version", "from_version", "to_version", "statements"}
    assert migration_from_json(json.dumps(sql.manifest()).encode()) == sql
    assert sql.checksum != step.checksum
    assert sql.checksum == "5cdeec3dc9ad8f0e0019a12502b942a1615fbdad0ee0dbe5a4b7089410023218"


@pytest.mark.parametrize(
    "patch",
    [
        {"manifest_version": 1},
        {"manifest_version": 3},
        {"manifest_version": True},
        {"manifest_version": 2.0},
        {"from_version": True},
        {"from_version": 4.0},
        {"to_version": False},
        {"to_version": 5.0},
        {"to_version": 6},
        {"data_transform": None},
        {"data_transform": {}},
        {"data_transform": {"id": "unknown", "code_sha256": "0" * 64}},
        {"data_transform": {"id": "capability-expiries-v1", "code_sha256": "F" * 64}},
        {"data_transform": {"id": "capability-expiries-v1", "code_sha256": "0" * 63}},
        {"data_transform": {"id": "capability-expiries-v1", "code_sha256": None}},
        {"extra": None},
        {"statements": "SELECT 1"},
        {"statements": []},
        {"statements": [None]},
        {"statements": [""]},
        {"statements": ["SELECT 1\r\n"]},
        {"statements": ["\ufeffSELECT 1"]},
        {"statements": ["\ud800"]},
    ],
)
def test_malformed_v2_is_controlled(patch):
    manifest = deepcopy(MIGRATIONS[-1].manifest())
    manifest.update(patch)
    with pytest.raises(YorungeError) as failure:
        migration_from_manifest(manifest)
    assert failure.value.code == "state_invalid"


@pytest.mark.parametrize("extra", [{"data_transform": None}, {"extra": 1}, {"manifest_version": 1}])
def test_v1_does_not_ignore_optional_fields(extra):
    value = {**MIGRATIONS[0].manifest(), **extra}
    with pytest.raises(YorungeError) as failure:
        migration_from_manifest(value)
    assert failure.value.code == "state_invalid"


def test_data_v2_descriptor_cannot_be_removed_or_added_to_sql_only():
    value = MIGRATIONS[-1].manifest()
    del value["data_transform"]
    with pytest.raises(YorungeError) as failure:
        migration_from_manifest(value)
    assert failure.value.code == "state_invalid"
    value = MigrationV2(5, 6, ("SELECT 1",)).manifest()
    value["data_transform"] = MIGRATIONS[-1].manifest()["data_transform"]
    with pytest.raises(YorungeError) as failure:
        migration_from_manifest(value)
    assert failure.value.code == "state_invalid"


@pytest.mark.parametrize(
    "payload",
    [
        b'{"from_version":0,"from_version":0,"to_version":1,"statements":["SELECT 1"]}',
        b'{"from_version":0,"to_version":1,"statements":["SELECT 1"],"extra":NaN}',
        b"\xff",
        b"[]",
        b"null",
    ],
)
def test_internal_json_evidence_decoder_rejects_duplicate_nonfinite_and_bad_utf8(payload):
    with pytest.raises(YorungeError) as failure:
        migration_from_json(payload)
    assert failure.value.code == "state_invalid"
