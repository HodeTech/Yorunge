"""Guards of the installation_v4 reader and of the offline guard that no test pinned."""

import subprocess
import sys

import pytest

from tests.contracts.test_installation_evidence_v4 import CHECKS, receipt
from tests.contracts.test_surface_installation import HELPER

pytestmark = pytest.mark.usefixtures("evidence_publication_context")


def test_origin_verified_decides_the_overall_flag_of_a_v4_record():
    # mutant (operand 0 -> True): the other eleven checks are pinned one by one, this one was not
    value = receipt()
    value["results"][0]["origin_verified"] = False
    value["passed"] = False
    assert CHECKS["summarize"](value)["passed"] is False
    value["passed"] = True
    with pytest.raises(ValueError):
        CHECKS["summarize"](value)


@pytest.mark.parametrize("bad", [1, 0, "true", None])
def test_the_overall_flag_of_a_v4_record_is_a_boolean(bad):
    # mutant L872 (flag arguments swapped): 1 stands for True
    value = receipt()
    value["passed"] = bad
    with pytest.raises(ValueError):
        CHECKS["summarize"](value)
    value = receipt()
    value["results"][0]["download_smoke"] = "failed"
    value["passed"] = 0
    with pytest.raises(ValueError):
        CHECKS["summarize"](value)


@pytest.mark.parametrize("bad", [[], {}, ["passed"]])
def test_an_unhashable_smoke_status_is_a_refused_record_not_a_type_error(bad):
    # mutant L888 (isinstance operand dropped): `bad not in {...}` raises TypeError instead
    value = receipt()
    value["results"][0]["download_smoke"] = bad
    value["passed"] = False
    with pytest.raises(ValueError):
        CHECKS["installation_summary_v4"](value)


def test_a_float_schema_version_is_not_version_four():
    value = receipt()
    value["schema_version"] = 4.0  # mutant L854 (type operand dropped): 4.0 == 4
    with pytest.raises(ValueError):
        CHECKS["installation_summary_v4"](value)


# --- the offline guard's two events that no attempt exercises


def test_the_guard_also_refuses_forkpty():
    # removing "os.forkpty" from DENIED survives the existing 14-attempt pin ("os.spawn" is a
    # Windows-only event: os.spawnv on POSIX is os.py code that raises os.fork and os.exec)
    body = """
import os
for attempt in (lambda: os.forkpty(),):
    try:
        attempt()
    except OSError as error:
        assert "forbidden" in str(error), error
    else:
        raise SystemExit("an attempt was not refused")
print("refused")
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", HELPER["GUARD"] + body],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert (result.returncode, result.stdout.strip()) == (0, "refused")
    assert "os.forkpty attempted" in result.stderr
