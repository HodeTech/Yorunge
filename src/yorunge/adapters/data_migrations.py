"""Execute a closed, verified source buffer inside the caller's migration transaction."""

from __future__ import annotations

import ast
import hashlib
import sqlite3
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from yorunge.adapters.local_files import Deadline
from yorunge.adapters.state_schema import DataTransform, Migration, MigrationV2
from yorunge.domain.errors import YorungeError

SOURCE = Path(__file__).with_name("migration_capability_expiries_v1.py")
MAX_SOURCE_BYTES = 65536
BUILTINS: dict[str, object] = {
    "ValueError": ValueError,
    "dict": dict,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "object": object,
    "set": set,
    "sorted": sorted,
    "str": str,
    "tuple": tuple,
    "type": type,
}
ATTRIBUTES = {
    "loads",
    "fullmatch",
    "ASCII",
    "fromisoformat",
    "get",
    "add",
    "encode",
    "source_rows",
    "insert_expiry",
}
NODES = (
    ast.Module,
    ast.Import,
    ast.ImportFrom,
    ast.alias,
    ast.FunctionDef,
    ast.arguments,
    ast.arg,
    ast.Assign,
    ast.AnnAssign,
    ast.AugAssign,
    ast.Name,
    ast.Constant,
    ast.Tuple,
    ast.List,
    ast.Set,
    ast.Dict,
    ast.For,
    ast.If,
    ast.Raise,
    ast.Return,
    ast.Expr,
    ast.Call,
    ast.Attribute,
    ast.Compare,
    ast.BoolOp,
    ast.UnaryOp,
    ast.Subscript,
    ast.keyword,
    ast.Load,
    ast.Store,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Eq,
    ast.NotEq,
    ast.Is,
    ast.IsNot,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Add,
)


def _imports(node: ast.Import | ast.ImportFrom) -> None:
    allowed = (
        isinstance(node, ast.Import)
        and all(a.name in {"json", "re"} and a.asname is None for a in node.names)
    ) or (
        isinstance(node, ast.ImportFrom)
        and node.level == 0
        and (
            (node.module == "datetime" and [a.name for a in node.names] == ["datetime"])
            or (node.module == "typing" and [a.name for a in node.names] == ["Any"])
        )
        and all(a.asname is None for a in node.names)
    )
    if not allowed:
        raise ValueError("closed standard imports required")


def _immutable(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) or (
        isinstance(node, ast.Tuple) and all(_immutable(item) for item in node.elts)
    )


def _module_item(node: ast.stmt) -> bool:
    if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)):
        return True
    if isinstance(node, ast.Expr):
        return isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
    return (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and _immutable(node.value)
    )


def _check_definition(node: ast.FunctionDef, functions: dict[str, ast.FunctionDef]) -> None:
    annotations = [a.annotation for a in (*node.args.args, *node.args.kwonlyargs)]
    annotations.append(node.returns)
    calls = any(isinstance(n, ast.Call) for a in annotations if a is not None for n in ast.walk(a))
    if (
        functions.get(node.name) is not node
        or node.decorator_list
        or node.args.defaults
        or any(value is not None for value in node.args.kw_defaults)
        or calls
    ):
        raise ValueError("pure function definitions required")


def _check_node(node: ast.AST, functions: dict[str, ast.FunctionDef]) -> None:
    if not isinstance(node, NODES):
        raise ValueError("source construct unsupported")
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        _imports(node)
    if isinstance(node, ast.FunctionDef):
        _check_definition(node, functions)
    if isinstance(node, ast.Name) and node.id.startswith("__"):
        raise ValueError("runtime namespace access forbidden")
    if isinstance(node, ast.Attribute) and (
        node.attr not in ATTRIBUTES or not isinstance(node.ctx, ast.Load)
    ):
        raise ValueError("runtime attribute forbidden")
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id not in BUILTINS and node.func.id not in functions:
            raise ValueError("runtime call forbidden")


def _check_recursion(functions: dict[str, ast.FunctionDef]) -> None:
    graph = {
        name: {
            n.func.id
            for n in ast.walk(definition)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in functions
        }
        for name, definition in functions.items()
    }
    completed: set[str] = set()

    def visit(name: str, seen: frozenset[str]) -> None:
        if name in completed:
            return
        if name in seen:
            raise ValueError("recursive handler forbidden")
        for other in graph[name]:
            visit(other, seen | {name})
        completed.add(name)

    for name in graph:
        visit(name, frozenset())


def _check_source(source: bytes) -> None:
    text = source.decode("utf-8")
    if "\r" in text or "\ufeff" in text:
        raise ValueError("UTF-8/LF source required")
    tree = ast.parse(source)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    if len(functions) != sum(isinstance(node, ast.FunctionDef) for node in tree.body):
        raise ValueError("unique helper names required")
    apply = functions.get("apply")
    if (
        apply is None
        or len(apply.args.args) != 1
        or apply.args.posonlyargs
        or apply.args.kwonlyargs
        or apply.args.vararg
        or apply.args.kwarg
    ):
        raise ValueError("single apply entry required")
    if not all(_module_item(node) for node in tree.body):
        raise ValueError("pure module definitions required")
    for node in ast.walk(tree):
        _check_node(node, functions)
    _check_recursion(functions)


def _import(
    name: str, globals: Any = None, locals: Any = None, fromlist: Any = (), level: int = 0
) -> object:
    if name not in {"json", "re", "datetime", "typing"} or level != 0:
        raise ImportError("closed standard imports required")
    return __import__(name, globals, locals, fromlist, level)


class MigrationConnection:
    """No cursor or raw connection escapes; only two fixed, parameterized operations."""

    __slots__ = ("_connection", "_deadline")

    def __init__(self, connection: sqlite3.Connection, deadline: Deadline) -> None:
        self._connection, self._deadline = connection, deadline

    def source_rows(self) -> Iterator[tuple[str, str]]:
        cursor = self._connection.execute(
            "SELECT cache_key,payload FROM capability_cache ORDER BY cache_key LIMIT 1025"
        )
        try:
            for key, payload in cursor:
                self._deadline.remaining()
                if not isinstance(key, str) or not isinstance(payload, str):
                    raise ValueError("source types required")
                yield key, payload
        finally:
            cursor.close()

    def insert_expiry(self, key: str, date: str) -> None:
        self._deadline.remaining()
        self._connection.execute("INSERT INTO capability_expiries VALUES(?,?)", (key, date))


def _authorize(
    action: int, first: str | None, second: str | None, database: str | None, trigger: str | None
) -> int:
    allowed = (
        database in (None, "main")
        and trigger is None
        and (
            action == sqlite3.SQLITE_SELECT
            or (
                action == sqlite3.SQLITE_READ
                and first == "capability_cache"
                and second in {"cache_key", "payload"}
            )
            or (action == sqlite3.SQLITE_INSERT and first == "capability_expiries")
            or (action == sqlite3.SQLITE_FUNCTION and second == "length")
        )
    )
    return sqlite3.SQLITE_OK if allowed else sqlite3.SQLITE_DENY


@dataclass(frozen=True)
class VerifiedTransform:
    descriptor: DataTransform
    apply: Callable[[MigrationConnection], None]

    def run(self, connection: sqlite3.Connection, deadline: Deadline) -> None:
        deadline.remaining()
        if not connection.in_transaction:
            raise YorungeError("state_invalid")
        connection.set_authorizer(_authorize)
        try:
            self.apply(MigrationConnection(connection, deadline))
            deadline.remaining()
            if not connection.in_transaction:
                raise YorungeError("state_invalid")
        except (ValueError, TypeError, AttributeError, KeyError, NameError, RecursionError):
            raise YorungeError("state_invalid") from None
        finally:
            connection.set_authorizer(None)


def prepare(step: Migration, deadline: Deadline) -> VerifiedTransform | None:
    """Only pending data migrations pay source/hash/compile cost; no import cache is used."""
    if not isinstance(step, MigrationV2) or step.data_transform is None:
        return None
    descriptor = step.data_transform
    deadline.remaining()
    try:
        with SOURCE.open("rb") as source:
            buffer = source.read(MAX_SOURCE_BYTES + 1)
        if (
            len(buffer) > MAX_SOURCE_BYTES
            or hashlib.sha256(buffer).hexdigest() != descriptor.code_sha256
        ):
            raise ValueError("source identity mismatch")
        _check_source(buffer)
        namespace: dict[str, Any] = {"__builtins__": {**BUILTINS, "__import__": _import}}
        code = compile(
            buffer,
            "<yorunge:capability-expiries-v1>",
            "exec",
            flags=0,
            dont_inherit=True,
            optimize=0,
        )
        exec(code, namespace)
        handler = namespace.get("apply")
        if not callable(handler):
            raise ValueError("handler missing")
        deadline.remaining()
        return VerifiedTransform(descriptor, handler)
    except FileNotFoundError:
        raise YorungeError("state_invalid") from None
    except OSError:
        raise YorungeError("state_write_failed") from None
    except (
        ValueError,
        TypeError,
        ImportError,
        SyntaxError,
        RecursionError,
        NameError,
        AttributeError,
        KeyError,
        OverflowError,
    ):
        raise YorungeError("state_invalid") from None
