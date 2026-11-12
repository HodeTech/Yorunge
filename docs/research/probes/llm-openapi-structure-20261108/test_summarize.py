"""Network-free checks for the OpenAPI structure summarizer (synthetic documents only)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "summarize", Path(__file__).with_name("summarize.py")
)
assert _SPEC is not None
assert _SPEC.loader is not None
summarize_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(summarize_module)

DOCUMENT = {
    "openapi": "3.1.0",
    "info": {"title": "Synthetic", "version": "0.0.1"},
    "paths": {
        "/v1/quota": {
            "get": {
                "summary": "Quota",
                "parameters": [
                    {"name": "model", "in": "query", "schema": {"type": "string"}},
                ],
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/Quota"}}
                        }
                    }
                },
            }
        },
        "/healthz": {"get": {"responses": {"200": {}}}},
    },
    "components": {
        "schemas": {
            "Quota": {
                "type": "object",
                "required": ["held", "used"],
                "properties": {
                    "used": {"anyOf": [{"type": "integer"}, {"type": "null"}], "description": "a"},
                    "held": {"type": "string"},
                    "level": {"type": "string", "enum": ["warn", "ok"]},
                },
            }
        }
    },
}


def raw(document: dict[str, object]) -> bytes:
    return json.dumps(document).encode("utf-8")


def test_summary_lists_operations_nullable_types_and_required_sorted() -> None:
    summary = summarize_module.summarize(raw(DOCUMENT))

    assert list(summary["operations"]) == ["GET /healthz", "GET /v1/quota"]
    assert summary["operations"]["GET /v1/quota"]["parameters"] == ["model:query:opt:string"]
    assert summary["operations"]["GET /v1/quota"]["responses"]["200"] == {
        "application/json": "ref:Quota"
    }
    quota = summary["schemas"]["Quota"]
    assert quota["required"] == ["held", "used"]
    assert quota["properties"]["used"].startswith("integer|null#")
    assert quota["properties"]["level"] == 'string{"ok","warn"}#-'
    assert summary["source"]["path_count"] == 2
    assert summary["source"]["security_schemes_declared"] is False


def test_output_is_independent_of_input_key_order() -> None:
    reordered = json.loads(json.dumps(DOCUMENT))
    reordered["paths"] = dict(reversed(list(reordered["paths"].items())))
    reordered["components"]["schemas"]["Quota"]["properties"] = dict(
        reversed(list(reordered["components"]["schemas"]["Quota"]["properties"].items()))
    )

    first = summarize_module.summarize(raw(DOCUMENT))
    second = summarize_module.summarize(raw(reordered))
    first["source"].pop("sha256"), second["source"].pop("sha256")
    first["source"].pop("bytes"), second["source"].pop("bytes")

    assert summarize_module.render(first) == summarize_module.render(second)


def test_nullability_and_description_changes_are_visible_without_storing_text() -> None:
    changed = json.loads(json.dumps(DOCUMENT))
    props = changed["components"]["schemas"]["Quota"]["properties"]
    props["held"] = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    props["used"]["description"] = "b"

    before = summarize_module.summarize(raw(DOCUMENT))["schemas"]["Quota"]["properties"]
    after = summarize_module.summarize(raw(changed))["schemas"]["Quota"]["properties"]

    assert before["held"] == "string#-"
    assert after["held"] == "null|string#-"
    assert before["used"] != after["used"]
    assert before["used"].split("#")[0] == after["used"].split("#")[0]


@pytest.mark.parametrize(
    "payload",
    [b'{"paths": {}, "paths": {}}', b"[]", b'{"openapi": "3.1.0"}', b"\xff"],
)
def test_malformed_or_ambiguous_documents_are_rejected(payload: bytes) -> None:
    with pytest.raises(ValueError):
        summarize_module.summarize(payload)
