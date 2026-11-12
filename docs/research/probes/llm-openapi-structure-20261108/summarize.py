#!/usr/bin/env python3
"""Deterministic, network-free structural summary of an OpenAPI 3.x JSON document.

Usage: summarize.py OPENAPI_JSON > summary.json

The summary keeps what is needed to *diff* two readings of a provider schema without storing the
document itself: source identity, every operation (method, path, parameters, bodies, response
codes), every component schema (property names, compact types incl. nullability, required set) and
a short digest of each description so that a semantic text change is visible without the text.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate JSON object key")
    return dict(pairs)


def _digest(text: object) -> str:
    if not isinstance(text, str) or not text:
        return "-"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _type(schema: object) -> str:
    """Compact, order-independent type signature (nullability is visible as `|null`)."""
    if not isinstance(schema, dict):
        return "?"
    ref = schema.get("$ref")
    if isinstance(ref, str):
        return "ref:" + ref.rsplit("/", 1)[-1]
    for key, joiner in (("anyOf", "|"), ("oneOf", "|"), ("allOf", "&")):
        members = schema.get(key)
        if isinstance(members, list):
            return joiner.join(sorted({_type(member) for member in members}))
    kind = schema.get("type")
    if kind == "array":
        return "array<" + _type(schema.get("items")) + ">"
    text = kind if isinstance(kind, str) else "?"
    if isinstance(schema.get("format"), str):
        text += ":" + schema["format"]
    enum = schema.get("enum")
    if isinstance(enum, list):
        text += "{" + ",".join(sorted(json.dumps(item, sort_keys=True) for item in enum)) + "}"
    return text


def _content(content: object) -> dict[str, str]:
    if not isinstance(content, dict):
        return {}
    return {str(name): _type(entry.get("schema")) for name, entry in sorted(content.items())}


def _operation(operation: dict[str, Any]) -> dict[str, Any]:
    parameters = sorted(
        f"{item.get('name')}:{item.get('in')}:{'req' if item.get('required') else 'opt'}"
        f":{_type(item.get('schema'))}"
        for item in operation.get("parameters", [])
        if isinstance(item, dict)
    )
    body = operation.get("requestBody")
    responses = operation.get("responses", {})
    return {
        "parameters": parameters,
        "request_body": _content(body.get("content")) if isinstance(body, dict) else {},
        "responses": {
            str(code): _content(entry.get("content") if isinstance(entry, dict) else None)
            for code, entry in sorted(responses.items())
        },
        "security_declared": bool(operation.get("security")),
        "text": _digest(f"{operation.get('summary', '')}\n{operation.get('description', '')}"),
    }


def _property(entry: object) -> str:
    description = entry.get("description") if isinstance(entry, dict) else None
    return f"{_type(entry)}#{_digest(description)}"


def _schema(schema: dict[str, Any]) -> dict[str, Any]:
    properties = schema.get("properties")
    required = schema.get("required")
    result: dict[str, Any] = {"type": _type(schema), "text": _digest(schema.get("description"))}
    if isinstance(properties, dict):
        result["properties"] = {
            str(name): _property(entry) for name, entry in sorted(properties.items())
        }
    if isinstance(required, list):
        result["required"] = sorted(str(item) for item in required)
    return result


def summarize(raw: bytes) -> dict[str, Any]:
    document = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    if not isinstance(document, dict) or not isinstance(document.get("paths"), dict):
        raise ValueError("OpenAPI object with paths required")
    info = document.get("info") if isinstance(document.get("info"), dict) else {}
    operations = {
        f"{method.upper()} {path}": _operation(operation)
        for path, item in sorted(document["paths"].items())
        if isinstance(item, dict)
        for method, operation in sorted(item.items())
        if method in HTTP_METHODS and isinstance(operation, dict)
    }
    components = document.get("components")
    schemas = components.get("schemas") if isinstance(components, dict) else None
    return {
        "source": {
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "openapi": document.get("openapi"),
            "info_title": info.get("title"),
            "info_version": info.get("version"),
            "path_count": len(document["paths"]),
            "security_schemes_declared": bool(
                isinstance(components, dict) and components.get("securitySchemes")
            ),
        },
        "operations": operations,
        "schemas": {
            str(name): _schema(entry)
            for name, entry in sorted((schemas or {}).items())
            if isinstance(entry, dict)
        },
    }


def render(summary: dict[str, Any]) -> str:
    return json.dumps(summary, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write("usage: summarize.py OPENAPI_JSON\n")
        return 2
    sys.stdout.write(render(summarize(Path(argv[1]).read_bytes())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
