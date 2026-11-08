"""The two stage environments share their failure path on purpose, and drift would be silent.

The environment of an original upload (v2) and that of a continuation (v3) are kept apart so that
the verified original path stays byte-identical, but what they do when a stage fails, how they
open the store and when they renew a lease is the same by design. Each shared method is compared
as a syntax tree, with the docstring dropped and the record type named alike, so that a change to
one of them without the other fails here instead of becoming two failure maps.

The failure path has exactly one deliberate difference, which the comparison names and removes
before it compares: a continuation that sends nothing (``M=0``) can never have sent anything, so a
stop that cannot be written leaves nothing uncertain for it. An original upload always creates
something, and there that same stop is uncertain.
"""

import ast
import inspect
import textwrap

import pytest

from yorunge.adapters.upload_continuation import ContinuationStages
from yorunge.adapters.upload_original import _Environment

SHARED = ("repository", "scope", "write_owned", "_renew_for_probe", "arm", "_stop")
CHECK_ONLY = "not graph_of(self.plan).files"


class WithoutCheckOnly(ast.NodeTransformer):
    """Removes the branch for a continuation that sends nothing, and counts what it removed."""

    def __init__(self) -> None:
        self.removed = 0

    def visit_If(self, node: ast.If) -> ast.AST | None:
        if ast.unparse(node.test) == CHECK_ONLY:
            self.removed += 1
            return None
        return self.generic_visit(node)


def normalised(method, *, without_check_only: WithoutCheckOnly | None = None) -> str:
    method = method.fget if isinstance(method, property) else method
    node = ast.parse(textwrap.dedent(inspect.getsource(method))).body[0]
    assert isinstance(node, ast.FunctionDef)
    first = node.body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
        node.body = node.body[1:] or [ast.Pass()]  # a docstring says, it does not do
    if without_check_only is not None:
        node = without_check_only.visit(node)
    return (
        ast.dump(node).replace("TransferRecordV2", "Record").replace("TransferRecordV3", "Record")
    )


@pytest.mark.parametrize("name", SHARED)
def test_the_two_environments_share_this_method_exactly(name):
    assert normalised(getattr(_Environment, name)) == normalised(getattr(ContinuationStages, name))


def test_the_failure_path_differs_only_by_the_branch_of_a_continuation_that_sends_nothing():
    removing = WithoutCheckOnly()
    continuation = normalised(ContinuationStages.failure, without_check_only=removing)
    assert removing.removed == 1  # the one difference exists, and is the one that is named
    assert normalised(_Environment.failure) == continuation
    # An original upload has no such branch to remove.
    untouched = WithoutCheckOnly()
    normalised(_Environment.failure, without_check_only=untouched)
    assert untouched.removed == 0


def test_the_comparison_sees_a_difference_when_there_is_one():
    # A guard against a comparison that would pass for any two methods.
    assert normalised(_Environment.admit) != normalised(ContinuationStages.admit)
    assert normalised(_Environment.prepare) != normalised(ContinuationStages.prepare)
