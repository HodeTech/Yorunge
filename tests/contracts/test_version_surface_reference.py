"""The numbers and lists the version reference states are the ones the code uses (P02-3q R2).

The reference says how long a manifest may be, how long a read may take, which errnos of a refused
`link()` are definite and what each result of `check` exits with. An edit of the prose that no test
noticed (a limit, an errno, an exit) would mislead a reader, so each is compared with its constant.
"""

import errno
import inspect
import re
from pathlib import Path

from yorunge.adapters.artifact_publisher import LINK_REFUSED
from yorunge.adapters.small_files import read_regular_file
from yorunge.domain.dataset_manifest import MAX_MANIFEST_BYTES
from yorunge.domain.dataset_version import (
    _TAG,
    MAX_BINDING_BYTES,
    MAX_LIST_ITEMS,
    MAX_PAGE,
    MIN_PAGE,
)
from yorunge.domain.errors import YorungeError

DOCS = Path(__file__).parents[2] / "docs" / "reference"
VERSIONS = (DOCS / "dataset-versions.md").read_text()
ENGINE = (DOCS / "download-engine.md").read_text()


def errnos_of(sentence: str) -> set[int]:
    """The errno constants a sentence names between backticks (a number, not a spelling)."""
    return {
        getattr(errno, name)
        for name in re.findall(r"`(E[A-Z0-9]+)`", sentence)
        if hasattr(errno, name)
    }


def test_the_errnos_of_a_refused_link_in_both_references_are_the_codes_definite_ones():
    engine = next(line for line in ENGINE.splitlines() if line.startswith("- **Dosya sistemi.**"))
    versions = next(
        line for line in VERSIONS.splitlines() if line.startswith("| `binding_write_uncertain`")
    )
    refused = re.search(r"`link\(\)` \(([^)]*)\)", engine)  # the list, not the EIO that follows
    assert refused is not None and errnos_of(refused.group(1)) == set(LINK_REFUSED)
    assert "`EIO`" in engine and errno.EIO not in LINK_REFUSED
    # the table names the first eight and says "…": it may not name one the code does not refuse
    assert errnos_of(versions) <= set(LINK_REFUSED) and len(errnos_of(versions)) >= 8


def test_the_results_of_check_exit_with_the_codes_the_table_says():
    rows = re.findall(r"^\| `([a-z ]+)` \|[^|]*\| (\d+|mevcut) \|$", VERSIONS, re.MULTILINE)
    named = {name: exit_code for name, exit_code in rows}
    assert named["unchanged"] == "0"
    assert int(named["changed"]) == YorungeError("dataset_version_changed").exit_code == 7
    assert int(named["missing"]) == YorungeError("dataset_version_missing").exit_code == 7
    rows = re.findall(r"^\| hedef uyuşmazlığı \|[^|]*\| (\d+) \|$", VERSIONS, re.MULTILINE)
    assert [int(r) for r in rows] == [YorungeError("state_changed").exit_code]


def test_the_closed_error_table_exits_are_the_catalogs():
    rows = re.findall(r"^\| `([a-z_]+)` \| (\d) \|", VERSIONS, re.MULTILINE)
    assert len(rows) >= 8
    for code, exit_code in rows:
        assert YorungeError(code).exit_code == int(exit_code), code


def test_the_limits_the_reference_states_are_the_constants():
    assert MAX_LIST_ITEMS == 100 and "en çok 100 kayıt" in VERSIONS
    assert (MIN_PAGE, MAX_PAGE) == (1, 10_000) and "1–10 000" in VERSIONS
    assert _TAG.pattern == "[A-Za-z0-9._-]{1,128}" and "{1,128}" in VERSIONS
    assert MAX_MANIFEST_BYTES == 8 * 1024 * 1024 and "en çok 8 MiB" in VERSIONS
    assert MAX_BINDING_BYTES == 16 * 1024 and "en çok 16 KiB" in VERSIONS
    seconds = inspect.signature(read_regular_file).parameters["seconds"].default
    assert seconds == 5.0 and "5 sn’lik okuma bütçesini" in VERSIONS


def test_the_exits_of_a_signal_and_a_closed_stdout_are_the_ones_the_reference_says():
    for code in ("request_cancelled", "output_closed"):
        assert YorungeError(code).exit_code == 6
        assert f"`{code}`/6" in VERSIONS
    assert YorungeError("binding_write_uncertain").exit_code == 5
    assert "`binding_write_uncertain`/5" in VERSIONS
