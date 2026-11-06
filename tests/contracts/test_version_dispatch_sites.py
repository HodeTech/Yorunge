"""Every place that tells the plan families apart is listed, with the slice that must handle it.

A continuation (plan version 3) is not a subclass of the v2 types, so code that says "is it v2,
otherwise v1" or "is it v2, otherwise a continuation does not exist" silently misreads or ignores
it. The list in ``tests/fixtures/version-dispatch-sites.json`` is derived from the syntax tree of
the source, not its text: a site is its file, the function it is in, its kind and its normalized
expression, so reformatting or moving code changes nothing, and a new site fails this test until
it is assigned an owner and a reason. A slice that handles a site changes it to ``done`` in the
same commit.

Kinds: ``isinstance`` (isinstance or issubclass naming a family type), ``type_is`` (``type(x)`` or
``x.__class__`` compared with a family type), ``match`` (a class pattern naming one), ``version``
(any read of a ``schema_version``, wherever it stands: a module that reads another schema's own
version is listed as ``unrelated`` rather than guessed at), ``decode_versioned/2`` and ``/3`` (a
decode naming two types rejects a continuation payload, so it fails closed; one naming three reads
it), and ``direct_decode`` (a family type validating JSON itself).

What a syntax-tree reader cannot see, and why that is accepted: a family type reached through a
variable (``FAMILIES = (A, B)`` then ``isinstance(x, FAMILIES)``, ``t = A``, a dict keyed on
``type(x)``), through ``type(x).__name__``, or through ``hasattr``/``getattr`` of a field only some
families have. None of these exists in the source today; the one cheap, mechanical defence is
``test_no_family_type_or_decoder_is_imported_under_another_name``, which stops the usual way to
hide a name. Anything else is for review to catch, and the owner of the change to list.
"""

import ast
import json
from collections import Counter
from pathlib import Path
from typing import get_args

import pytest

from yorunge.domain import upload_versions

ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "src" / "yorunge"
LIST = json.loads((ROOT / "tests" / "fixtures" / "version-dispatch-sites.json").read_text())

# The closed families, straight from the code: each tuple is one kind of value in version order.
FAMILIES = tuple(
    tuple(cls.__name__ for cls in get_args(union))
    for union in (
        upload_versions.UploadPlan,
        upload_versions.UploadApproval,
        upload_versions.UploadRecord,
        upload_versions.UploadControl,
        upload_versions.UploadVerification,
        upload_versions.UploadReceipt,
    )
)
FAMILY_TYPES = frozenset(name for family in FAMILIES for name in family)
# The modules that define the families; their own rules are not dispatch between families.
DEFINING_MODULES = {
    "dataset_transfer.py",
    "dataset_transfer_v2.py",
    "dataset_transfer_v3.py",
    "dataset_upload.py",
    "dataset_upload_v2.py",
    "dataset_continuation.py",
    "create_receipt.py",
}
Site = tuple[str, str, str, str, int]  # file, function, kind, expression, occurrence


def _mentions(node: ast.AST) -> bool:
    return any(
        (isinstance(item, ast.Name) and item.id in FAMILY_TYPES)
        or (isinstance(item, ast.Attribute) and item.attr in FAMILY_TYPES)
        for item in ast.walk(node)
    )


def _called(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    return node.func.attr if isinstance(node.func, ast.Attribute) else None


def _class_of(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "type"
        and len(node.args) == 1
    ) or (isinstance(node, ast.Attribute) and node.attr == "__class__")


def _version_key(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value == "schema_version"


def _reads_version(node: ast.AST) -> bool:
    if isinstance(node, ast.Attribute):
        return node.attr == "schema_version" and isinstance(node.ctx, ast.Load)
    if isinstance(node, ast.Subscript):
        return _version_key(node.slice)
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get" and node.args:
            return _version_key(node.args[0])
        if isinstance(node.func, ast.Name) and node.func.id == "getattr" and len(node.args) > 1:
            return _version_key(node.args[1])
    return False


def _function(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str:
    names = []
    current = parents.get(node)
    while current is not None:
        if isinstance(current, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.append(current.name)
        current = parents.get(current)
    return ".".join(reversed(names)) or "<module>"


def _around(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> tuple[ast.AST, str]:
    """The smallest comparison, keyword, dictionary entry or statement a version read is part of."""
    child = node
    while (parent := parents.get(child)) is not None:
        if isinstance(parent, ast.Dict) and child in parent.values:
            key = parent.keys[parent.values.index(child)]
            return child, f"{ast.unparse(key) if key else '**'}: {ast.unparse(child)}"
        if isinstance(parent, ast.Compare | ast.keyword | ast.IfExp):
            return parent, ast.unparse(parent)
        if isinstance(parent, ast.stmt):
            return parent, ast.unparse(parent).splitlines()[0]
        child = parent
    return child, ast.unparse(child)


def _decode_types(node: ast.Call) -> list[ast.expr]:
    """The type arguments of a ``decode_versioned`` call: v1, v2 and the optional v3."""
    return [*node.args[:2], *node.args[3:], *(kw.value for kw in node.keywords if kw.arg == "v3")]


def _call_text(node: ast.Call, kind: str) -> str:
    """A call is told by what it decodes into; its payload argument is incidental."""
    if kind.startswith("decode_versioned"):
        return f"decode_versioned({', '.join(ast.unparse(t) for t in _decode_types(node))})"
    if kind == "direct_decode" and _called(node) == "decode":
        return f"decode({ast.unparse(node.args[0])}, ...)"
    if kind == "direct_decode":
        return f"{ast.unparse(node.func)}(...)"
    return ast.unparse(node)


def _call_kind(node: ast.Call) -> str | None:
    name = _called(node)
    if name in ("isinstance", "issubclass") and len(node.args) == 2 and _mentions(node.args[1]):
        return "isinstance"
    if name == "decode_versioned":
        return f"decode_versioned/{len(node.args) + len(node.keywords) - 1}"
    if name == "decode" and node.args and _mentions(node.args[0]):
        return "direct_decode"
    if (
        isinstance(node.func, ast.Attribute)
        and node.func.attr in ("model_validate_json", "model_validate")
        and _mentions(node.func.value)
    ):
        return "direct_decode"
    return None


Found = tuple[int, int, int, str, str, str]  # line, end line, column, function, kind, expression


def scan(source: str) -> list[Found]:
    """Where a module's source tells the families apart, in source order."""
    tree = ast.parse(source)
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    found: list[Found] = []
    covered: set[int] = set()
    for node in ast.walk(tree):
        kind = text = None
        anchor = node
        if isinstance(node, ast.Call) and (kind := _call_kind(node)):
            text = _call_text(node, kind)
        elif isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            if any(_class_of(o) for o in operands) and any(
                _mentions(o) for o in operands if not _class_of(o)
            ):
                kind, text = "type_is", ast.unparse(node)
        elif isinstance(node, ast.MatchClass) and _mentions(node.cls):
            kind, text = "match", ast.unparse(node)
        if kind is None and _reads_version(node):
            anchor, text = _around(node, parents)
            if id(anchor) not in covered:  # one site per comparison or entry, not per read
                covered.add(id(anchor))
                kind = "version"
        if kind is not None and text is not None:
            found.append(
                (
                    getattr(anchor, "lineno", 0),
                    getattr(anchor, "end_lineno", 0) or 0,
                    getattr(anchor, "col_offset", 0),
                    _function(node, parents),
                    kind,
                    text,
                )
            )
    return sorted(found)


def sites_in(source: str, relative: str) -> list[Site]:
    """The dispatch sites of one module's source, numbered where an expression repeats."""
    counter: Counter[tuple[str, str, str]] = Counter()
    sites = []
    for _, _, _, function, kind, text in scan(source):
        sites.append((relative, function, kind, text, counter[function, kind, text]))
        counter[function, kind, text] += 1
    return sites


def found_sites() -> list[Site]:
    sites = []
    for path in sorted(SOURCE.rglob("*.py")):
        if path.name not in DEFINING_MODULES:
            sites += sites_in(path.read_text(), str(path.relative_to(ROOT)))
    return sites


def listed_sites() -> list[Site]:
    return [
        (s["file"], s["function"], s["kind"], s["text"], s["occurrence"]) for s in LIST["sites"]
    ]


def entry(site: Site) -> str:
    keys = ("file", "function", "kind", "text", "occurrence")
    return json.dumps({**dict(zip(keys, site, strict=True)), "owner": "?", "note": "?"})


def test_the_list_equals_the_code_site_for_site():
    found, listed = found_sites(), listed_sites()
    assert sorted(found) == sorted(listed), (
        "a version-dispatch site changed: assign it in tests/fixtures/version-dispatch-sites.json"
        "\nnew in code:\n  "
        + "\n  ".join(entry(s) for s in sorted(set(found) - set(listed)))
        + f"\nlisted but gone or reworded: {sorted(set(listed) - set(found))}"
    )


def test_every_site_has_a_known_owner_and_says_why():
    owners = set(LIST["owners"])
    for site in LIST["sites"]:
        assert site["owner"] in owners, site
        assert site["note"].strip() and site["note"] != "?", site
    assert len(listed_sites()) == len(set(listed_sites()))


def test_only_the_slices_still_to_come_own_open_sites():
    # P02-3g has handled its own; v1-only and v2-only are deliberate, permanent families, and an
    # unrelated site reads the version of something that is not a family.
    closed = {"done", "v1-only", "v2-only", "unrelated"}
    open_owners = {site["owner"] for site in LIST["sites"]} - closed
    assert open_owners <= {"P02-3u", "P02-3v", "P02-3r", "P02-3h", "P02-3i"}
    assert "P02-3g" not in open_owners


def test_the_dispatch_helpers_of_the_versions_module_name_every_family():
    # A cheap guard on the done sites: the helpers that decide by family mention all three.
    text = (SOURCE / "domain" / "upload_versions.py").read_text()
    for name in ("DatasetContinuationPlanV3", "DatasetUploadApprovalV3", "TransferVerificationV3"):
        assert name in text


@pytest.mark.parametrize("owner", ["P02-3u", "P02-3v", "P02-3r", "P02-3h"])
def test_each_open_owner_names_a_card_that_exists(owner):
    cards = list((ROOT / "docs" / "roadmap" / "tasks").glob(f"{owner.lower()}-*.md"))
    assert len(cards) == 1, owner


def test_every_decode_names_the_members_of_one_family_in_version_order():
    # A decode that mixes columns (a control's type next to a proof's) only fails when the third
    # kind of payload first appears, so the pairing is checked statically.
    checked = 0
    for path in sorted(SOURCE.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Call) and _called(node) == "decode_versioned":
                types = tuple(ast.unparse(a) for a in _decode_types(node))
                assert any(types == family[: len(types)] for family in FAMILIES), (path, types)
                checked += 1
    assert checked >= 10


# --- the finder itself: a tripwire that cannot see a kind of site guards nothing ---

AWARE = "from yorunge.domain.dataset_transfer_v2 import TransferRecordV2\n"
OTHER = "from other import thing\n"


def kinds(source: str, header: str = AWARE) -> list[str]:
    return [site[2] for site in sites_in(header + source, "m.py")]


@pytest.mark.parametrize(
    "expression,kind",
    [
        ("isinstance(x, TransferRecordV2)", "isinstance"),
        ("isinstance(x, TransferRecord | TransferRecordV2)", "isinstance"),
        ("isinstance(x, (TransferRecord, TransferRecordV2))", "isinstance"),
        ("isinstance(x, models.TransferRecordV2)", "isinstance"),
        ("issubclass(type(x), TransferRecordV2)", "isinstance"),
        ("type(x) is TransferRecordV2", "type_is"),
        ("type(x) is not TransferRecordV3", "type_is"),
        ("TransferRecordV2 is type(x)", "type_is"),
        ("x.__class__ == TransferRecordV2", "type_is"),
        ("type(x) in (TransferRecord, TransferRecordV2)", "type_is"),
        ("decode_versioned(TransferRecord, TransferRecordV2, x)", "decode_versioned/2"),
        (
            "decode_versioned(TransferRecord, TransferRecordV2, x, TransferRecordV3)",
            "decode_versioned/3",
        ),
        (
            "decode_versioned(TransferRecord, TransferRecordV2, x, v3=TransferRecordV3)",
            "decode_versioned/3",
        ),
        ("store.decode_versioned(TransferRecord, TransferRecordV2, x)", "decode_versioned/2"),
        ("TransferRecordV2.model_validate_json(x)", "direct_decode"),
        ("models.TransferRecordV2.model_validate(x)", "direct_decode"),
        ("decode(TransferRecordV2, x)", "direct_decode"),
        ("x.schema_version == 2", "version"),
        ("x.operation.schema_version != y.schema_version", "version"),
        ("x['schema_version']", "version"),
        ("x.get('schema_version')", "version"),
        ("getattr(x, 'schema_version')", "version"),
        ("{'schema_version': x.schema_version}", "version"),
        ("dict(schema=x.schema_version)", "version"),
    ],
)
def test_the_finder_sees_each_way_a_family_can_be_told_apart(expression, kind):
    assert kinds(f"def f(x, y, models, store):\n    return {expression}\n") == [kind]


def test_the_finder_sees_a_match_on_a_family_type():
    source = "def f(x):\n    match x:\n        case TransferRecordV2():\n            return 1\n"
    assert kinds(source) == ["match"]


@pytest.mark.parametrize(
    "expression",
    [
        "isinstance(x, dict)",
        "isinstance(x, UploadRecord)",  # the closed union itself says "any family"
        "type(x) is int",
        "type(x) is dict and y",
        "decode(Other, x)",
        "Other.model_validate_json(x)",
        "x.schema",
        "x.version == 2",
    ],
)
def test_the_finder_ignores_what_does_not_tell_the_families_apart(expression):
    assert kinds(f"def f(x, y):\n    return {expression}\n") == []


def test_a_version_read_counts_wherever_it_stands():
    source = "def f(x):\n    return x.schema_version == 2\n"
    # No import of anything is needed: a module that gets a family value through a call (a
    # repository, a view) never has to name a family type to read its version.
    for header in (OTHER, AWARE, "", "import yorunge.adapters.upload_store as store\n"):
        assert kinds(source, header) == ["version"]
    assert kinds("def f(x):\n    return isinstance(x, TransferRecordV2)\n", OTHER) == ["isinstance"]


def test_a_keyword_third_type_is_read_into_the_site_and_the_pairing_check():
    source = AWARE + "def f(x):\n    return decode_versioned(A, B, x, v3=C)\n"
    assert [(s[2], s[3]) for s in sites_in(source, "m.py")] == [
        ("decode_versioned/3", "decode_versioned(A, B, C)")
    ]
    call = ast.parse("decode_versioned(A, B, payload, v3=C)").body[0].value  # type: ignore[attr-defined]
    assert [ast.unparse(t) for t in _decode_types(call)] == ["A", "B", "C"]


def renamed_imports(source: str) -> list[str]:
    """Family types and the versioned decoder imported under another name (``X as Y``)."""
    watched = FAMILY_TYPES | {"decode_versioned"}
    return [
        alias.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in node.names
        if alias.asname and alias.name.split(".")[-1] in watched
    ]


def test_the_guard_against_renamed_imports_sees_a_rename_and_only_a_rename():
    assert renamed_imports("from a import TransferRecordV2 as R2\n") == ["TransferRecordV2"]
    assert renamed_imports("from a import decode_versioned as dv\n") == ["decode_versioned"]
    assert renamed_imports("import a.TransferRecordV2 as R2\n") == ["a.TransferRecordV2"]
    assert renamed_imports("from a import TransferRecordV2\nfrom b import thing as other\n") == []


def test_no_family_type_or_decoder_is_imported_under_another_name():
    # An alias is the usual way a name escapes a reader that matches names.
    assert {
        str(path): found
        for path in sorted(SOURCE.rglob("*.py"))
        if (found := renamed_imports(path.read_text()))
    } == {}


def test_formatting_and_position_do_not_change_a_site():
    plain = "def f(x):\n    return isinstance(x, TransferRecordV2) and x.schema_version == 2\n"
    spread = (
        "\n\n# a comment\n\n\ndef f(x):\n    return (\n        isinstance(\n            x,\n"
        "            TransferRecordV2,\n        )\n        and x.schema_version\n"
        "        == 2  # trailing\n    )\n"
    )
    assert sites_in(AWARE + plain, "m.py") == sites_in(AWARE + spread, "m.py")
    assert len(sites_in(AWARE + plain, "m.py")) == 2


def test_the_same_expression_twice_in_one_function_is_two_numbered_sites():
    source = (
        "def f(x, y):\n    if isinstance(x, TransferRecordV2):\n        return 1\n"
        "    if isinstance(x, TransferRecordV2):\n        return 2\n"
    )
    assert [(s[1], s[4]) for s in sites_in(AWARE + source, "m.py")] == [("f", 0), ("f", 1)]
    # Nesting names the function: a method and a nested function are told apart from the module.
    nested = (
        "class C:\n    def m(self, x):\n        def inner():\n"
        "            return isinstance(x, TransferRecordV2)\n        return inner\n"
    )
    assert sites_in(AWARE + nested, "m.py")[0][1] == "C.m.inner"
    assert sites_in(AWARE + "isinstance(1, TransferRecordV2)\n", "m.py")[0][1] == "<module>"


def test_the_closed_families_are_what_the_unions_say():
    # Adding a member to a union extends the tripwire; a family cannot go unwatched.
    assert FAMILY_TYPES >= {
        "DatasetContinuationPlanV3",
        "TransferVerificationV3",
        "CreateReceiptV2",
    }
    assert all(2 <= len(family) <= 3 for family in FAMILIES)
