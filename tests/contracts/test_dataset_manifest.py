"""Independent manifest bytes, exact path identities and bounded strict parsing."""

import hashlib
import json
from pathlib import Path

import pytest

from yorunge.domain import dataset_manifest as module
from yorunge.domain.dataset_manifest import (
    DatasetFile,
    DatasetManifest,
    build_manifest,
    decode_manifest_json,
    file_parts,
)
from yorunge.domain.errors import YorungeError

GOLDEN = Path(__file__).parents[1] / "fixtures/dataset-manifest-v1.json"
EMPTY_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
EXPECTED_DIGEST = "3762e3eb601d18bcb87010ad6f92de3deff98099dc5302cc8ce8c73ec3d3210c"


def file(path, size=0, digest=EMPTY_HASH):
    return DatasetFile(path=path, size=size, sha256=digest)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False).encode()


def test_literal_golden_bytes_and_independent_file_hashes():
    contents = {"a.txt": b"abc", "empty.bin": b"", "ölçüm.txt": b"hello"}
    files = tuple(
        file(path, len(content), hashlib.sha256(content).hexdigest())
        for path, content in reversed(tuple(contents.items()))
    )
    actual = build_manifest(files)
    assert actual.digest == EXPECTED_DIGEST
    assert actual.encoded() == GOLDEN.read_bytes()
    assert actual.file_count == 3
    assert actual.total_bytes == 8
    assert DatasetManifest.model_validate_json(GOLDEN.read_bytes()) == actual
    assert "root" not in actual.model_dump()
    assert "timestamp" not in actual.model_dump()


def test_empty_manifest_and_each_distinct_name_are_preserved():
    empty = build_manifest(())
    assert empty.file_count == 0
    assert empty.total_bytes == 0
    assert DatasetManifest.model_validate_json(empty.encoded()) == empty
    two = build_manifest((file("b"), file("a")))
    assert tuple(item.path for item in two.files) == ("a", "b")
    assert two.file_count == 2
    assert two.files[0].sha256 == two.files[1].sha256
    assert two.digest != empty.digest


@pytest.mark.parametrize("name", ["schema_version", "policy_version"])
@pytest.mark.parametrize("value", [True, 1.0, "1", None, 2])
def test_versions_are_closed_strict_integers(name, value):
    payload = json.loads(GOLDEN.read_bytes())
    payload[name] = value
    content = encoded(payload)
    with pytest.raises(ValueError):
        DatasetManifest.model_validate_json(content)


@pytest.mark.parametrize(
    "path,replacement,remove",
    [
        (("extra",), 1, False),
        (("kind",), None, True),
        (("files", 0, "extra"), 1, False),
        (("files", 0, "size"), None, True),
        (("kind",), "plan", False),
        (("files", 0, "sha256"), "0" * 64, False),
        (("digest",), "0" * 64, False),
        (("file_count",), 2, False),
        (("total_bytes",), 9, False),
        (("files",), list(reversed(json.loads(GOLDEN.read_bytes())["files"])), False),
        (("files", 1, "path"), "a.txt", False),
        (("files", 0, "size"), True, False),
        (("files", 0, "size"), 3.0, False),
        (("file_count",), True, False),
        (("total_bytes",), 8.0, False),
        (("files", 0, "sha256"), "A" * 64, False),
        (("files", 0, "sha256"), "a" * 63, False),
        (("hash_algorithm",), "md5", False),
    ],
)
def test_wire_rejects_closed_schema_integrity_and_aggregate_attacks(path, replacement, remove):
    value = json.loads(GOLDEN.read_bytes())
    target = value
    for key in path[:-1]:
        target = target[key]
    if remove:
        del target[path[-1]]
    else:
        target[path[-1]] = replacement
    content = encoded(value)
    with pytest.raises(ValueError):
        DatasetManifest.model_validate_json(content)


@pytest.mark.parametrize(
    "content",
    [
        b'{"schema_version":1,"schema_version":1}',
        b'{"x":{"k":1,"k":2}}',
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b'{"x":1e999}',
        b'{"x":"\xff"}',
        b'{"x":"\\ud800"}',
        b"\xef\xbb\xbf{}",
        b"{} trailing",
        b"[1]",
        b"null",
        b"",
    ],
)
def test_invalid_raw_json_is_never_normalized_into_a_manifest(content):
    with pytest.raises(ValueError):
        DatasetManifest.model_validate_json(content)


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/a",
        "a/",
        "a//b",
        "./a",
        "a/../b",
        "a/./b",
        "a\\b",
        "a:b",
        "a?",
        "a*",
        "a|b",
        'a"b',
        "a<b",
        "a>b",
        "a.",
        "a ",
        "CON",
        "nul.txt",
        "COM1.bin",
        "lpt9",
        "a\x00",
        "a\n",
        "a\x7f",
        "a\x85",
        "a\udcff",
        "a\u202e",
        "a\u2066",
    ],
)
def test_path_policy_rejects_unsafe_or_nonportable_names(path):
    with pytest.raises(ValueError):
        file(path)


@pytest.mark.parametrize(
    "names",
    [
        ("a", "a"),
        ("A/x", "a/y"),
        ("a", "a/b"),
        ("a/b", "a"),
        ("é/x", "e\u0301/y"),
        ("STRASSE/x", "straße/y"),
        ("x/A", "x/a"),
    ],
)
def test_sibling_collision_and_file_ancestor_conflicts_are_not_deduplicated(names):
    files = tuple(file(name) for name in names)
    with pytest.raises(ValueError):
        build_manifest(files)


def test_original_unicode_spelling_is_preserved_without_renaming():
    spelling = "e\u0301/東京.txt"
    manifest = build_manifest((file(spelling),))
    assert manifest.files[0].path == spelling
    assert spelling.encode() in manifest.encoded()
    assert DatasetManifest.model_validate_json(manifest.encoded()).files[0].path == spelling


@pytest.mark.parametrize("count", [4095, 4096, 4097])
def test_real_file_count_boundary(count):
    files = tuple(file(f"f{index:04}") for index in range(count))
    if count > 4096:
        with pytest.raises(ValueError):
            build_manifest(files)
    else:
        assert build_manifest(files).file_count == count


@pytest.mark.parametrize("count", [4094, 4095, 4096])
def test_inferred_directory_count_includes_root(count):
    files = tuple(file(f"d{index:04}/x") for index in range(count))
    if count == 4096:
        with pytest.raises(ValueError, match="directory limit"):
            build_manifest(files)
    else:
        assert build_manifest(files).file_count == count


@pytest.mark.parametrize("size", [1024**3 - 1, 1024**3, 1024**3 + 1])
def test_content_size_boundary(size):
    if size > 1024**3:
        with pytest.raises(ValueError):
            file("a", size)
    else:
        assert build_manifest((file("a", size),)).total_bytes == size


def test_logical_bytes_count_duplicate_content_each_time():
    files = (file("a", 1024**3), file("b", 1))
    with pytest.raises(ValueError):
        build_manifest(files)


@pytest.mark.parametrize("count", [31, 32, 33])
def test_path_depth_boundary(count):
    path = "/".join(["d"] * (count - 1) + ["f"])
    if count > 32:
        with pytest.raises(ValueError):
            file(path)
    else:
        assert len(file_parts(path)) == count


@pytest.mark.parametrize("size", [254, 255, 256])
def test_component_byte_boundary_uses_utf8_not_characters(size):
    name = "é" * (size // 2) + ("x" if size % 2 else "")
    if size > 255:
        with pytest.raises(ValueError):
            file(name)
    else:
        assert file(name).path == name


@pytest.mark.parametrize("size", [1023, 1024, 1025])
def test_total_path_byte_boundary(size):
    prefix = "/".join(["a" * 255, "b" * 255, "c" * 255, "d" * 253]) + "/"
    path = prefix + "x" * (size - len(prefix))
    if size > 1024:
        with pytest.raises(ValueError):
            file(path)
    else:
        assert file(path).path == path


@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_manifest_raw_byte_limit(delta):
    original = GOLDEN.read_bytes()
    content = original + b" " * (8 * 1024**2 + delta - len(original))
    if delta > 0:
        with pytest.raises(ValueError, match="byte limit"):
            DatasetManifest.model_validate_json(content)
    else:
        assert DatasetManifest.model_validate_json(content).digest == EXPECTED_DIGEST


@pytest.mark.parametrize("depth", [7, 8, 9])
def test_preparse_depth_budget_and_string_escapes(depth):
    content = b"[" * depth + b'"{\\"["' + b"]" * depth
    if depth > 8:
        with pytest.raises(ValueError, match="depth"):
            decode_manifest_json(content)
    else:
        assert decode_manifest_json(content)


@pytest.mark.parametrize("nodes", [49999, 50000, 50001])
def test_actual_json_node_boundary(nodes):
    content = b"[" + b",".join([b"0"] * (nodes - 1)) + b"]"
    if nodes > 50000:
        with pytest.raises(ValueError, match="node"):
            decode_manifest_json(content)
    else:
        assert len(decode_manifest_json(content)) == nodes - 1


def test_keys_are_json_nodes_and_default_arguments_cannot_relax_wire(monkeypatch):
    monkeypatch.setattr(module, "MAX_JSON_NODES", 4)
    with pytest.raises(ValueError, match="node"):
        decode_manifest_json(b'{"k":[0,1]}')
    monkeypatch.setattr(module, "MAX_JSON_NODES", 5)
    assert decode_manifest_json(b'{"k":[0,1]}') == {"k": [0, 1]}
    monkeypatch.setattr(module, "MAX_JSON_NODES", 50_000)
    payload = json.loads(GOLDEN.read_bytes())
    payload["extra"] = 1
    content = encoded(payload)
    with pytest.raises(ValueError):
        DatasetManifest.model_validate_json(content, strict=False, extra="allow")


def test_explicit_non_strict_argument_cannot_coerce_wire_numbers():
    value = json.loads(GOLDEN.read_bytes())
    value["file_count"] = 3.0
    content = encoded(value)
    with pytest.raises(ValueError):
        DatasetManifest.model_validate_json(content, strict=False)


@pytest.mark.parametrize("code", ["input_invalid", "input_changed", "input_unsupported"])
def test_shared_input_messages_work_for_dataset_and_execution_callers(code):
    error = YorungeError(code)
    assert error.exit_code == 2
    assert "plan" not in error.message.casefold()
    assert error.envelope()["message"] == error.message
    assert error.envelope()["details"] == {}
    assert "dosya" in error.message.casefold()


@pytest.mark.parametrize("value", [None, True, 10**9, [65], memoryview(b"{}")])
def test_raw_manifest_input_type_is_checked_before_bytes_coercion(value):
    with pytest.raises(ValueError):
        DatasetManifest.model_validate_json(value)


@pytest.mark.parametrize("attack", ["file-count", "total", "unsorted", "duplicate-path"])
def test_independent_valid_digest_cannot_hide_invalid_aggregates_or_path_order(attack):
    value = json.loads(GOLDEN.read_bytes())
    if attack == "file-count":
        value["file_count"] = 2
    elif attack == "total":
        value["total_bytes"] = 9
    elif attack == "unsorted":
        value["files"].reverse()
    else:
        value["files"][1]["path"] = "a.txt"
    del value["digest"]
    # Independent wire signing: do not call the producer/model's digest helpers.
    body = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    value["digest"] = hashlib.sha256(body).hexdigest()
    content = encoded(value)
    with pytest.raises(ValueError):
        DatasetManifest.model_validate_json(content)


@pytest.mark.parametrize("scalar", [False, 0.0])
def test_strict_zero_size_rejects_values_that_would_coerce_to_valid_golden_digest(scalar):
    value = json.loads(GOLDEN.read_bytes())
    value["files"][1]["size"] = scalar
    content = encoded(value)
    with pytest.raises(ValueError):
        DatasetManifest.model_validate_json(content, strict=False)
