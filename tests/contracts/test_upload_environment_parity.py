"""The two stage environments share their failure path on purpose, and drift would be silent.

The environment of an original upload (v2) and that of a continuation (v3) are kept apart so that
the verified original path stays byte-identical, but what they do when a stage fails, how they
open the store and when they renew a lease is the same by design. Each shared method is compared
as a syntax tree, with the docstring dropped and the record type named alike, so that a change to
one of them without the other fails here instead of becoming two failure maps.
"""

import ast
import inspect
import textwrap

import pytest

from yorunge.adapters.upload_continuation import ContinuationStages
from yorunge.adapters.upload_original import _Environment

SHARED = ("repository", "scope", "_renew_for_probe", "_stop", "failure")


def normalised(method) -> str:
    node = ast.parse(textwrap.dedent(inspect.getsource(method))).body[0]
    assert isinstance(node, ast.FunctionDef)
    first = node.body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
        node.body = node.body[1:] or [ast.Pass()]  # a docstring says, it does not do
    return (
        ast.dump(node).replace("TransferRecordV2", "Record").replace("TransferRecordV3", "Record")
    )


@pytest.mark.parametrize("name", SHARED)
def test_the_two_environments_share_this_method_exactly(name):
    assert normalised(getattr(_Environment, name)) == normalised(getattr(ContinuationStages, name))


def test_the_comparison_sees_a_difference_when_there_is_one():
    # A guard against a comparison that would pass for any two methods.
    assert normalised(_Environment.admit) != normalised(ContinuationStages.admit)
    assert normalised(_Environment.prepare) != normalised(ContinuationStages.prepare)
