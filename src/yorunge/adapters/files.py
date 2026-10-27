from __future__ import annotations

import json
import os
import stat
import tomllib
from collections.abc import Hashable
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import ValidationError
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode
from yaml.tokens import AliasToken, AnchorToken

from yorunge.domain.errors import ErrorCode, YorungeError
from yorunge.domain.models import Configuration, Model, Plan, Recipe

CONFIG_LIMIT = 65_536
PLAN_LIMIT = 262_144
MAX_DEPTH = 32
MAX_NODES = 2048
M = TypeVar("M", bound=Model)


def validate(model: type[M], value: object, code: ErrorCode) -> M:
    try:
        return model.model_validate(value)
    except (ValidationError, ValueError, RecursionError):
        raise YorungeError(code) from None


def read_text(path: Path, limit: int, code: ErrorCode) -> str:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise YorungeError(code)
            content = source.read(limit + 1)
        if len(content) > limit:
            raise YorungeError(code)
        return content.decode("utf-8")
    except (OSError, ValueError):
        raise YorungeError("file_unreadable") from None


class RecipeLoader(yaml.SafeLoader):
    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict[Hashable, object]:
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None, "mapping node required", node.start_mark)
        result: dict[Hashable, object] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in result:
                raise ValueError("duplicate or non-string key")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def bounded_tree(value: object, depth: int = 0, budget: list[int] | None = None) -> None:
    if budget is None:
        budget = [MAX_NODES]
    budget[0] -= 1
    if depth > MAX_DEPTH or budget[0] < 0:
        raise ValueError("document complexity limit")
    if isinstance(value, dict):
        for key, item in value.items():
            bounded_tree(key, depth + 1, budget)
            bounded_tree(item, depth + 1, budget)
    elif isinstance(value, list):
        for item in value:
            bounded_tree(item, depth + 1, budget)


def load_config(path: Path) -> Configuration:
    content = read_text(path, CONFIG_LIMIT, "invalid_config")
    try:
        value = tomllib.loads(content)
        bounded_tree(value)
    except (ValueError, RecursionError):
        raise YorungeError("invalid_config") from None
    return validate(Configuration, value, "invalid_config")


def load_recipe(path: Path) -> Recipe:
    content = read_text(path, CONFIG_LIMIT, "invalid_recipe")
    try:
        depth = 0
        count = 0
        for event in yaml.parse(content, Loader=RecipeLoader):
            count += 1
            if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent)):
                depth += 1
            elif isinstance(event, (yaml.MappingEndEvent, yaml.SequenceEndEvent)):
                depth -= 1
            if depth > MAX_DEPTH or count > MAX_NODES:
                raise ValueError("document complexity limit")
        if any(isinstance(token, (AliasToken, AnchorToken)) for token in yaml.scan(content)):
            raise ValueError("aliases and anchors are not allowed")
        value = yaml.load(content, Loader=RecipeLoader)
    # SafeLoader's scalar constructors can raise built-in errors for malformed literals.
    except (
        yaml.YAMLError,
        ValueError,
        RecursionError,
        KeyError,
        IndexError,
        AttributeError,
        OverflowError,
    ):
        raise YorungeError("invalid_recipe") from None
    return validate(Recipe, value, "invalid_recipe")


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise ValueError("non-finite JSON number")


def load_saved_plan(path: Path) -> Plan:
    content = read_text(path, PLAN_LIMIT, "invalid_plan")
    try:
        value = json.loads(content, object_pairs_hook=unique_object, parse_constant=reject_constant)
        bounded_tree(value)
        # JSON collections become the immutable tuple fields of the public model.
        encoded = json.dumps(value, allow_nan=False)
        plan = Plan.model_validate_json(encoded)
        if plan.digest != plan.computed_digest():
            raise ValueError("digest mismatch")
    except (ValueError, RecursionError):
        raise YorungeError("invalid_plan") from None
    return plan
