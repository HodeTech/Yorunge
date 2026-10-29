"""Repeated syntax checks retain Unicode byte limits and strict JSON semantics."""

import pytest

from yorunge.domain.capabilities import WireModel, canonical


class TextRecord(WireModel):
    text: str


@pytest.mark.parametrize(
    "value", ["a" * 128, "a" * 129, "a" * 2048, "é" * 1024, "😀" * 512, "a" * 2044 + "😀"]
)
def test_repeated_text_validation_preserves_exact_unicode_at_byte_limit(value):
    for _ in range(2):
        assert TextRecord(text=value).text == value


@pytest.mark.parametrize(
    "invalid", ["safe\x00", "safe\n", "safe\x7f", "é\x85", "a" * 2049, "é" * 1025, "\ud800"]
)
def test_warming_a_valid_text_does_not_accept_invalid_or_oversized_text(invalid):
    assert TextRecord(text="safe").text == "safe"
    for _ in range(2):
        with pytest.raises(ValueError):
            TextRecord(text=invalid)


@pytest.mark.parametrize(
    "payload", ['{"text":"same","text":"same"}', '{"text":"same","t\\u0065xt":"same"}']
)
def test_duplicate_names_are_rejected_even_when_values_match_or_key_is_escaped(payload):
    with pytest.raises(ValueError, match="duplicate wire key"):
        TextRecord.model_validate_json(payload)


class IntegerRecord(WireModel):
    text: str
    number: int
    flag: bool
    optional: str | None
    values: tuple[int, str, None]


@pytest.mark.parametrize("number", [-(2**63), 0, 2**63 - 1])
@pytest.mark.parametrize(
    "text", ['"\\/', "\u2028\u2029", "\u00a0e\u0301", "文😀", "a" * 2044 + "😀"]
)
def test_integer_wire_size_matches_canonical_ascii_bytes(number, text):
    model = IntegerRecord(
        text=text, number=number, flag=True, optional=None, values=(number, text, None)
    )
    expected = len(canonical(model.model_dump(mode="json")))
    assert model._integer_json_size() == expected


def test_plan_keeps_exact_canonical_boundary_with_a_valid_digest(tmp_path, execution_fixture):
    import hashlib

    from tests.fixtures.seed_migration_state import maximum_plan
    from yorunge import api
    from yorunge.domain.execution import ExecutionPlan

    base = api.prepare_execution_plan(task="llm.train", state_dir=tmp_path / "state").data.plan
    maximum = maximum_plan(base, tmp_path)
    assert maximum.computed_digest() == maximum.digest
    assert len(canonical(maximum.model_dump(mode="json"))) == 65536
    body = maximum.model_dump(mode="json", exclude={"digest"})
    assert body["inputs"][-1]["path"] == "p"
    body["inputs"][-1]["path"] += "a"
    body["digest"] = hashlib.sha256(canonical(body)).hexdigest()
    encoded = canonical(body)
    assert len(encoded) == 65537
    with pytest.raises(ValueError, match="plan digest or size invalid"):
        ExecutionPlan.model_validate_json(encoded)


@pytest.mark.parametrize("suffix", ["\x7f", "\ud800"])
def test_plan_size_preserves_legacy_nested_model_canonical_text(
    tmp_path, execution_fixture, suffix
):
    import hashlib

    from yorunge import api
    from yorunge.domain.execution import ExecutionPlan

    base = api.prepare_execution_plan(task="llm.train", state_dir=tmp_path / "state").data.plan
    body = base.model_dump(mode="python", exclude={"digest"})
    # Domain construction of legacy Context is broader than public UTF-8 file input.
    # The size optimization must preserve its existing canonical representation.
    body["context"]["platform_url"] = "https://example.test/path" + suffix
    body["digest"] = hashlib.sha256(canonical(body)).hexdigest()
    if suffix == "\x7f":
        with pytest.raises(ValueError, match="invalid service URL"):
            ExecutionPlan.model_validate(body)
        return
    plan = ExecutionPlan.model_validate(body)
    assert plan.computed_digest() == plan.digest
    assert canonical(plan.model_dump(mode="json")) == canonical(body)
